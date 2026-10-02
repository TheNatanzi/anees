# -*- coding: utf-8 -*-
"""Publish guard (Medi decision 7, 2026-09-29): "every hourly run re-checks the math BEFORE publishing. If anything doesn't
add up, it doesn't publish, it keeps the last good version live, and it tells Medi why."

How publishing works: GitHub Pages builds the live site from master:/docs (a "legacy" Pages build, no workflow file), so
EVERY `git push origin HEAD:master` publishes. This module is the one door to that push. Every pusher calls
`guarded_push()` instead of `git push`:

    hourly_lessons.publish / tutor_refresh / decisions_refresh / gap_fill_refresh / the stranded-commit push in main(),
    review_lesson.py step 8, lesson_pipeline.git_publish / publish (retired job, still importable)

guarded_push(): pull --rebase (a conflict in GENERATED files only: master's copy is kept and the rebuild is queued,
see resolve_generated_conflicts; any other conflict: abort + stop) -> run_checks() on exactly what would be pushed -> on any failed
REQUIRED check: no push (the live site keeps the last good version; the local commits are KEPT, so nothing is lost and the
next hour re-checks them), one line in the hourly log, the reason in data/publish-guard/state.json (local, never pushed)
-> on a pass: docs/data/publish-guard.json (System Settings reads it; it also carries the last block, so a block that
could not be published at the time shows once the next run passes) is committed and the push runs.

Checks and what blocks are in scripts/publish_guard_config.json ("required" blocks, "advisory" only reports). A required
check that fails, times out, crashes or whose script is missing blocks (fail closed).

    python scripts/publish_guard.py check            # run every check, print, record the result locally; exit 0 = publishable
    python scripts/publish_guard.py push --source X  # guarded push of HEAD to origin/master
    python scripts/publish_guard.py status           # the local state (last check, last block)
    python scripts/publish_guard.py hook             # git pre-push hook body (see plan/ENG-AUDIT-AREA-4-GUARD.md)
"""
from __future__ import annotations

import argparse, datetime, fnmatch, glob, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = 'scripts/publish_guard_config.json'
STATE = 'data/publish-guard/state.json'            # local only (.gitignore): what happened on THIS PC, incl. blocks
PUBLISHED = 'docs/data/publish-guard.json'         # published with each passing push; System Settings reads it
NODE_DEFAULT = r'C:\dev\tools\node-v24.18.0-win-x64\node.exe'
BUILTINS = ('step_failures', 'clean_tree', 'json_data', 'lesson_coverage', 'review_done', 'review_freshness', 'lesson_type_read',
            'data_freshness')
DATE_RE = re.compile(r'^20\d\d-\d\d-\d\d$')
OK_ENV = 'ANEES_PUBLISH_GUARD_OK'                  # set on the guard's own `git push` so the pre-push hook does not re-run


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def _log(*parts):
    print(datetime.datetime.now().strftime('%H:%M:%S'), *parts, flush=True)


def J(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def load_config(root=ROOT):
    return J(Path(root) / CONFIG)


def _node():
    return os.environ.get('ANEES_NODE') or (NODE_DEFAULT if os.path.exists(NODE_DEFAULT) else 'node')


def _short(text, n=300):
    lines = [l.strip() for l in str(text or '').strip().splitlines() if l.strip()]
    # name the failing test when there is one (node: "✖ <name>" / "not ok N - <name>"; pytest: "FAILED <id>"), so the
    # line Medi reads says WHAT failed, not the tail of an assertion dump (eng audit 2026-09-29)
    named = list(dict.fromkeys(l for l in lines if l.startswith(('✖ ', 'not ok ', 'FAILED ', 'ERROR '))
                                and 'failing tests' not in l))
    s = ' | '.join(named[:3] + [lines[-1]] if named else lines[-3:])
    return s if len(s) <= n else '...' + s[-n:]


# ---------------------------------------------------------------- built-in checks (read the working tree, no network)

def check_step_failures(root, failures, **_):
    """Steps that failed in THIS run, plus failed steps of earlier hours not yet fixed (data/publish-guard/state.json
    "open_failures": a lesson whose feeding or review failed stays blocked until a later hour re-runs it cleanly)."""
    items = list(dict.fromkeys(str(f) for f in (failures or [])))
    for key, v in sorted(open_failures(root).items()):
        for f in v.get('failures') or []:
            s = f'{f} (open since {str(v.get("at"))[:16]}, {key})'
            if str(f) not in items:
                items.append(s)
    return (not items, '; '.join(items)[:800] if items else 'no build step failed (this run or an earlier one)')


def check_review_done(root, **_):
    """Every lesson's same-day review (two readers + third reader) finished: a lesson whose review failed is not published
    with an audit that silently lacks it."""
    work = Path(root) / 'data/lesson-work/full-audit'
    pages, _ = _lesson_dates(root)
    missing = [d for d in sorted(pages) if not (work / f'{d}.settled.json').exists()]
    return (not missing, ('no finished review (settled audit) for ' + ', '.join(missing)) if missing else f'all {len(pages)} lessons reviewed')


def check_clean_tree(root, config, run, **_):
    """The checks read the working tree but the push publishes HEAD: they only mean something when the published paths
    have no uncommitted or unadded changes."""
    paths = config.get('clean_paths') or ['docs']
    r = run(['git', 'status', '--porcelain', '--', *paths], cwd=str(root), capture_output=True, text=True, encoding='utf-8')
    if getattr(r, 'returncode', 0):
        return False, 'git status failed: ' + _short(getattr(r, 'stderr', ''))
    dirty = [l for l in (r.stdout or '').splitlines() if l.strip()]
    if dirty:
        return False, f'{len(dirty)} uncommitted change(s) in what would be published, e.g. ' + ', '.join(l[3:] for l in dirty[:4])
    return True, 'nothing uncommitted under ' + ', '.join(paths)


def check_json_data(root, **_):
    """Every docs/data JSON file parses; the files the pages lean on have their top-level shape."""
    shapes = {'lessons.json': {'lessons': list}, 'accuracy-release.json': {'lessons': list, 'totals': dict},
              'grammar-console.json': {'lessons': list, 'rules': list}, 'grammar-usage.json': {'lessons': dict},
              'sentence-ladder.json': {'lessons': list}, 'word-bank-evidence.json': {'events': list},
              'word-bank-audit.json': {'events': list}, 'tutor.json': {}, 'ai_reports.json': {'reports': list},
              'standing-rules.json': {}, 'build.json': {'build': str}}
    bad, n = [], 0
    for p in sorted(glob.glob(os.path.join(str(root), 'docs', 'data', '**', '*.json'), recursive=True)):
        n += 1
        rel = os.path.relpath(p, str(root)).replace('\\', '/')
        try:
            d = J(p)
        except Exception as e:
            bad.append(f'{rel} does not parse ({type(e).__name__}: {str(e)[:80]})'); continue
        want = shapes.get(os.path.basename(p)) if os.path.dirname(rel) == 'docs/data' else None
        for k, typ in (want or {}).items():
            if not isinstance(d, dict) or not isinstance(d.get(k), typ):
                bad.append(f'{rel}: "{k}" missing or not a {typ.__name__}')
    if not n:
        return False, 'no docs/data/*.json found'
    return (not bad, '; '.join(bad[:6]) + (f' (+{len(bad) - 6} more)' if len(bad) > 6 else '') if bad else f'{n} JSON files parse')


def _lesson_dates(root):
    pages = {Path(p).stem for p in glob.glob(os.path.join(str(root), 'docs', 'lessons', '20??-??-??.html'))}
    try:
        listed = {L['date'] for L in J(Path(root) / 'docs/data/lessons.json')['lessons']}
    except Exception:
        listed = set()
    return pages, listed


def check_lesson_coverage(root, run, **_):
    """Area 4: a new lesson must reach EVERY page with no hand edits (09-26 once stopped at the transcript page). Each
    lesson date with a page must be in every data file a page reads per lesson."""
    root = Path(root)
    pages, listed = _lesson_dates(root)
    probs = [f'{d}: lesson page but not in lessons.json (Lessons, Progress)' for d in sorted(pages - listed)]
    probs += [f'{d}: in lessons.json but no lesson page docs/lessons/{d}.html' for d in sorted(listed - pages)]

    def dates_of(rel, pick):
        try:
            return set(pick(J(root / rel)))
        except Exception as e:
            probs.append(f'{rel} unreadable ({type(e).__name__})'); return None
    sources = {
        'sentence-ladder.json (Progress fluency ladder)': dates_of('docs/data/sentence-ladder.json', lambda d: (x['date'] for x in d['lessons'])),
        'grammar-console.json (Grammar)': dates_of('docs/data/grammar-console.json', lambda d: (x['date'] for x in d['lessons'])),
        'grammar-usage.json (Grammar %)': dates_of('docs/data/grammar-usage.json', lambda d: d['lessons'].keys()),
        'accuracy-release.json (verified / ≈ marks)': dates_of('docs/data/accuracy-release.json', lambda d: (x['date'] for x in d['lessons'])),
        'word-bank-evidence.json (Word Bank)': dates_of('docs/data/word-bank-evidence.json', lambda d: (e.get('lesson_date') for e in d['events'])),
        'word-bank-audit.json (Word Bank audit)': dates_of('docs/data/word-bank-audit.json', lambda d: (e.get('date') for e in d['events'])),
    }
    tracked = run(['git', 'ls-files', '--', 'docs/lessons'], cwd=str(root), capture_output=True, text=True, encoding='utf-8')
    tracked = set((getattr(tracked, 'stdout', '') or '').splitlines())
    for d in sorted(pages | listed):
        miss = []
        if not (root / 'docs/data/lessons' / f'{d}.json').exists():
            miss.append(f'lesson detail docs/data/lessons/{d}.json')
        if not (root / 'docs/data/sentence-ladder' / f'{d}.json').exists():
            miss.append(f'docs/data/sentence-ladder/{d}.json')
        if not any(t.startswith(f'docs/lessons/{d}/audio/') and t.endswith('.mp3') for t in tracked):
            miss.append('lesson audio (nothing committed under docs/lessons/<date>/audio/)')
        miss += [name for name, ds in sources.items() if ds is not None and d not in ds]
        if miss:
            probs.append(f'{d} missing from: ' + ', '.join(miss))
    if probs:
        return False, f'{len(probs)} gap(s): ' + '; '.join(probs[:6]) + (f' (+{len(probs) - 6} more)' if len(probs) > 6 else '')
    return True, f'all {len(pages)} lessons reach every page'


def check_review_freshness(root, **_):
    """The same-day review (two readers + third) must have read the transcript the pages show now. A transcript that grew
    after the readers ran (a Meet gap fill: 09-23 +266 lines, 09-26 +149 lines) leaves those lines unaudited."""
    root = Path(root)
    work = root / 'data/lesson-work/full-audit'
    pages, _ = _lesson_dates(root)
    probs = []
    try:
        sys.path.insert(0, str(root / 'scripts'))
        import review_lesson as RL
    except Exception as e:
        return False, f'review_lesson.py not importable ({e})'
    for d in sorted(pages):
        if not (work / f'{d}.settled.json').exists():
            probs.append(f'{d}: no settled audit (the review never finished)'); continue
        try:
            why = RL.readers_read_current(d, str(root))
        except Exception as e:
            why = f'transcript unreadable ({type(e).__name__})'
        if why:
            probs.append(f'{d}: {why}')
    return (not probs, '; '.join(probs) if probs else f'{len(pages)} lessons audited on their current transcript')


def check_lesson_type_read(root, **_):
    """A lesson type that is only the builder's default ("Not read yet") must not be shown as Claude's reading."""
    try:
        L = J(Path(root) / 'docs/data/lessons.json')['lessons']
    except Exception as e:
        return False, f'lessons.json unreadable ({type(e).__name__})'
    unread = [x['date'] for x in L if str(x.get('type_why') or '').startswith('Not read yet')]
    return (not unread, ('type not read yet (default "free-speak" shown as Claude\'s reading): ' + ', '.join(unread)) if unread else 'every lesson type was read')


FRESH_RAW_DEFAULT = r'C:\dev\anees\data\lessons'
FRESH_FROM = '2026-09-10'                 # hourly_lessons.AUTO_START: earlier recordings were decided by hand
FRESH_TRIGGER_MAX_H = 2                   # the Amal trigger runs every 15 min (fallback: every hour)
FRESH_PUBLISH_MAX_H = 6                   # blocks for longer than this = the live site is falling behind


def _age_h(stamp, now=None):
    try:
        t = datetime.datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
        if t.tzinfo is None:
            t = t.astimezone()
        return ((now or datetime.datetime.now().astimezone()) - t).total_seconds() / 3600
    except Exception:
        return None


def check_data_freshness(root, raw=None, now=None, **_):
    """Rule F1 (freshness audit 2026-10-02): the pages must not be older than their newest source. Warns when
    (1) a lesson is transcribed in the raw archive but missing from lessons.json (10-01 sat transcribed 11+ hours),
    (2) the Amal trigger has not checked her answers for FRESH_TRIGGER_MAX_H hours (its 15-minute task never existed),
    (3) nothing was published for FRESH_PUBLISH_MAX_H hours while pushes were blocked (09-30 17:23 -> 10-02: 32 h unseen)."""
    root = Path(root)
    probs = []
    raw = Path(raw or os.environ.get('ANEES_RAW') or FRESH_RAW_DEFAULT)
    _, listed = _lesson_dates(root)
    if raw.is_dir():
        for d in sorted(x.name for x in raw.iterdir() if x.is_dir() and DATE_RE.match(x.name) and x.name >= FRESH_FROM):
            scribes = list((raw / d).glob('scribe*.json')) + list((raw / d).glob('meet-*/scribe.json'))
            if scribes and d not in listed:
                newest = max(f.stat().st_mtime for f in scribes)
                at = datetime.datetime.fromtimestamp(newest).astimezone()
                probs.append(f'lesson {d} transcribed {at:%m-%d %H:%M} but not on the site (not in lessons.json)')
    st = _load_json(root / 'data/amal-trigger/state.json') or {}
    age = _age_h(st.get('checked'), now)
    if age is None or age > FRESH_TRIGGER_MAX_H:
        probs.append("Amal's answers last checked " + (f'{age:.0f} h ago' if age is not None else 'never on this PC')
                     + ' (scripts/amal_trigger.py: neither its 15-minute task nor the hourly fallback ran)')
    gs = read_state(root)
    last = (gs.get('last_pass') or {}).get('at')
    blocks = int(gs.get('blocks_since_last_pass') or 0)
    stuck = [h.get('at') for h in gs.get('history') or [] if h.get('outcome') in ('blocked', 'rebase_failed', 'push_failed')
             and (not last or str(h.get('at')) > str(last))]
    age = _age_h(stuck[0], now) if stuck else (_age_h(last, now) if last else None)   # blocked since the first block after the last pass
    if blocks and (age is None or age > FRESH_PUBLISH_MAX_H):
        probs.append('nothing published for ' + (f'{age:.0f} h' if age is not None else 'a long time')
                     + f' ({blocks} blocked pushes; last: {str((gs.get("last_block") or {}).get("reason") or "")[:120]})')
    return (not probs, '; '.join(probs) if probs else 'every lesson in the raw archive is on the site; Amal trigger and publishing are current')


def _load_json(p):
    try:
        return J(p)
    except Exception:
        return None


# ---------------------------------------------------------------- command checks

def _missing_files(root, cmd):
    return [a for a in cmd[1:] if re.search(r'\.(py|cjs|js)$', a) and '/' in a and not (Path(root) / a).exists()]


def run_command_check(root, spec, run, budget_s):
    cmd = [sys.executable if a == '{python}' else _node() if a == '{node}' else a for a in spec['cmd']]
    missing = _missing_files(root, spec['cmd'])
    if missing:
        return False, 'missing: ' + ', '.join(missing) + ' (a required check that does not exist counts as a fail)'
    timeout = max(1, min(float(spec.get('timeout_s', 120)), budget_s))
    try:
        r = run(cmd, cwd=str(root), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    except subprocess.TimeoutExpired:
        return False, f'timed out after {timeout:.0f} s'
    except Exception as e:
        return False, f'could not run ({type(e).__name__}: {e})'
    out = (r.stdout or '') + ('\n' + r.stderr if r.stderr else '')
    if r.returncode:
        return False, f'exit {r.returncode}: ' + _short(out)
    pat = spec.get('stdout_must_match')
    if pat and not re.search(pat, r.stdout or ''):
        return False, f'output does not show /{pat}/: ' + _short(r.stdout)
    return True, _short(r.stdout, 160) or 'ok'


# ---------------------------------------------------------------- the check list

def run_checks(root=ROOT, config=None, step_failures=(), run=subprocess.run, clock=time.monotonic):
    """Run every configured check. Returns {ok, at, sha, checks: [...], reason, warnings}. ok is False when any REQUIRED
    check fails, errors, times out, is missing or is unknown (fail closed)."""
    root = Path(root)
    try:
        config = config or load_config(root)
    except Exception as e:
        return {'ok': False, 'at': now_iso(), 'sha': None, 'checks': [], 'warnings': [],
                'reason': f'config {CONFIG} unreadable ({type(e).__name__}: {e})'}
    required, advisory = list(config.get('required') or []), list(config.get('advisory') or [])
    total = float(config.get('total_timeout_s', 300))
    sha = getattr(run(['git', 'rev-parse', 'HEAD'], cwd=str(root), capture_output=True, text=True), 'stdout', '') or ''
    t0, checks = clock(), []
    builtin = {'step_failures': lambda: check_step_failures(root, step_failures),
               'clean_tree': lambda: check_clean_tree(root, config, run),
               'json_data': lambda: check_json_data(root),
               'lesson_coverage': lambda: check_lesson_coverage(root, run),
               'review_done': lambda: check_review_done(root),
               'review_freshness': lambda: check_review_freshness(root),
               'lesson_type_read': lambda: check_lesson_type_read(root),
               'data_freshness': lambda: check_data_freshness(root)}
    if not required:
        checks.append({'id': 'config', 'required': True, 'ok': False, 'secs': 0, 'detail': 'no required checks configured'})
    for cid in required + [a for a in advisory if a not in required]:
        s0 = clock()
        left = total - (s0 - t0)
        spec = (config.get('commands') or {}).get(cid)
        if left <= 0:
            ok, detail = False, f'not run: the guard used its {total:.0f} s budget'
        elif cid in builtin:
            try:
                ok, detail = builtin[cid]()
            except Exception as e:
                ok, detail = False, f'check crashed ({type(e).__name__}: {e})'
        elif spec:
            ok, detail = run_command_check(root, spec, run, left)
        else:
            ok, detail = False, 'unknown check id (not built in, not in "commands")'
        checks.append({'id': cid, 'required': cid in required, 'ok': bool(ok), 'secs': round(clock() - s0, 1),
                       'what': (spec or {}).get('what') or _WHAT.get(cid, ''), 'detail': detail})
    failed = [c for c in checks if c['required'] and not c['ok']]
    return {'ok': not failed, 'at': now_iso(), 'sha': sha.strip()[:40] or None, 'secs': round(clock() - t0, 1), 'checks': checks,
            'reason': '; '.join(f"{c['id']}: {c['detail']}" for c in failed)[:1500],
            'warnings': [f"{c['id']}: {c['detail']}" for c in checks if not c['required'] and not c['ok']]}


_WHAT = {'step_failures': 'no build step failed in this run', 'clean_tree': 'what is checked is exactly what gets published',
         'json_data': 'every docs/data JSON file parses and has its shape',
         'lesson_coverage': 'every lesson reaches every page (Lessons, Word Bank, Grammar, Progress, audio)',
         'review_done': 'every lesson has a finished same-day review',
         'review_freshness': 'the two readers read the transcript the pages show now',
         'lesson_type_read': 'no default lesson type shown as a reading',
         'data_freshness': 'the pages are not older than their newest source (raw lessons, Amal trigger, last publish)'}


# ---------------------------------------------------------------- local state + published status

def read_state(root=ROOT):
    p = Path(root) / STATE
    try:
        return J(p)
    except Exception:
        return {}


def _write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, p)


def record(root, result, source, outcome, reason=None, waiting=None):
    """outcome: pushed | blocked | rebase_failed | push_failed | checked. Local only; kept for Medi and the next pass."""
    st = read_state(root)
    entry = {'at': result.get('at') or now_iso(), 'source': source, 'outcome': outcome, 'sha': result.get('sha'),
             'reason': reason if reason is not None else result.get('reason') or '', 'secs': result.get('secs'),
             'commits_waiting': waiting}
    st['last_check'] = {**entry, 'checks': result.get('checks', []), 'warnings': result.get('warnings', [])}
    if outcome in ('blocked', 'rebase_failed', 'push_failed'):
        st['last_block'] = entry
        st['blocks_since_last_pass'] = int(st.get('blocks_since_last_pass') or 0) + 1
    elif outcome == 'pushed':
        st['last_pass'] = entry
        st['blocks_since_last_pass'] = 0
    st['history'] = ((st.get('history') or []) + [entry])[-100:]
    _write_json(Path(root) / STATE, st)
    return st


def open_failures(root=ROOT):
    """{key: {at, failures}} - failed steps of earlier hours (e.g. 'refresh:2026-09-30', 'tutor', 'gapfill', 'review:<date>')."""
    return dict(read_state(root).get('open_failures') or {})


def set_open_failures(root, key, failures):
    """Record (non-empty) or clear (empty) the failed steps under `key`. Keeps the first time it failed."""
    st = read_state(root)
    of = dict(st.get('open_failures') or {})
    if failures:
        of[key] = {'at': (of.get(key) or {}).get('at') or now_iso(), 'last': now_iso(), 'failures': [str(f) for f in failures]}
    elif key in of:
        of.pop(key)
    else:
        return
    st['open_failures'] = of
    _write_json(Path(root) / STATE, st)


def published_status(result, state, source):
    return {'updated': result.get('at'), 'result': 'pass', 'source': source, 'checked_commit': (result.get('sha') or '')[:12],
            'secs': result.get('secs'),
            'checks': [{k: c.get(k) for k in ('id', 'required', 'ok', 'secs', 'what', 'detail')} for c in result.get('checks', [])],
            'warnings': result.get('warnings', []),
            'last_block': state.get('last_block'), 'blocks_before_this_pass': int(state.get('blocks_since_last_pass') or 0),
            'note': 'Written only when every required check passed, right before the push. When a check fails the hourly job '
                    'does not publish, so this page keeps showing the last pass until the next one; the reason for a block is '
                    'in the hourly log (C:/dev/anees/data/lessons/hourly.log) and in data/publish-guard/state.json on the PC, '
                    'and appears here as "last block" once a later run passes.'}


def block_line(source, reason, waiting):
    w = f'; {waiting} local commit(s) wait' if waiting not in (None, '', '0', 0) else ''
    return f'PUBLISH BLOCKED ({source}): {reason} -- nothing pushed, the live site keeps the last good version{w}'


# ---------------------------------------------------------------- the one door to master

def _git(run, root, *args, env=None):
    kw = dict(cwd=str(root), capture_output=True, text=True, encoding='utf-8', errors='replace')
    if env:
        kw['env'] = env
    return run(['git', *args], **kw)


# ---------------------------------------------------------------- generated files are rebuilt, never merged

# What a rebase may resolve by itself (scripts/publish_guard_config.json "regenerate_on_conflict" overrides it). Rule
# (2026-10-02 freshness audit): two build stamps (docs/data/build.json, docs/js/build.js) written a minute apart made
# EVERY hourly push stop at "a person merges" from 2026-09-30 17:23 on: 69 local commits, lesson 2026-10-01 and Amal's
# answers stuck off the live site for 30+ hours. A generated file is never hand-merged: master's copy is kept, the stamp
# is re-written, and every other generated file is queued for a rebuild (open failure 'tutor' + 'refresh:<date>' for a
# lesson missing from a page), which blocks this push and makes the next hourly run rebuild and publish.
REGENERATE_DEFAULT = {
    'stamp': ['docs/data/build.json', 'docs/js/build.js'],
    'paths': ['docs/data/*', 'docs/js/build.js', 'docs/amal/*.html', 'docs/lessons/*/clips/*', 'data/accuracy/*',
              'data/full-audit-2026-09-26.json', 'data/lesson-work/full-audit/patterns.json', 'data/amal-trigger/*',
              'data/vocab/amal_verb_checks.json', 'data/runs/*.jsonl', 'data/decisions/*.jsonl', 'plan/FULL-AUDIT-2026-09-26.md'],
}


def regenerate_rules(config=None):
    r = dict(REGENERATE_DEFAULT)
    r.update((config or {}).get('regenerate_on_conflict') or {})
    return r


def is_generated(path, rules=None):
    rules = rules or REGENERATE_DEFAULT
    path = path.replace('\\', '/')
    return any(fnmatch.fnmatchcase(path, pat) for pat in list(rules.get('paths') or []) + list(rules.get('stamp') or []))


def _rebasing(root, run):
    for name in ('rebase-merge', 'rebase-apply'):
        p = (getattr(_git(run, root, 'rev-parse', '--git-path', name), 'stdout', '') or '').strip()
        if p and (Path(p) if os.path.isabs(p) else Path(root) / p).is_dir():
            return True
    return False


def _unmerged(root, run):
    out = getattr(_git(run, root, 'diff', '--name-only', '--diff-filter=U'), 'stdout', '') or ''
    return [l.strip() for l in out.splitlines() if l.strip()]


def resolve_generated_conflicts(root, run=subprocess.run, config=None, max_steps=2000):
    """Called while a `pull --rebase` is stopped on a conflict. If EVERY conflicted file is generated, keep master's copy
    (during a rebase "ours" = the commit being rebased onto) and continue, step by step. Returns (True, {'resolved':
    [...]}) when the rebase finished, or (False, {'reason': ...}) - the caller aborts; a hand-made file always stops here."""
    rules = regenerate_rules(config)
    if not _rebasing(root, run):
        return False, {'reason': 'not stopped on a rebase conflict'}
    env = {**os.environ, 'GIT_EDITOR': 'true'}
    resolved = []
    for _ in range(max_steps):
        if not _rebasing(root, run):
            return True, {'resolved': sorted(set(resolved))}
        u = _unmerged(root, run)
        if not u:
            # stopped without a conflict (e.g. the commit became empty once master's copies were kept): go on or skip it
            c = _git(run, root, 'rebase', '--continue', env=env)
            if getattr(c, 'returncode', 0) and _rebasing(root, run) and not _unmerged(root, run):
                if getattr(_git(run, root, 'rebase', '--skip'), 'returncode', 0) and _rebasing(root, run) and not _unmerged(root, run):
                    return False, {'reason': 'the rebase stopped and could not continue: ' + _short(getattr(c, 'stderr', ''), 160)}
            continue
        hand = [p for p in u if not is_generated(p, rules)]
        if hand:
            return False, {'reason': 'conflict in a hand-made file (a person merges): ' + ', '.join(hand[:5]), 'files': hand}
        for p in u:
            if getattr(_git(run, root, 'checkout', '--ours', '--', p), 'returncode', 0):
                _git(run, root, 'rm', '-q', '--', p)                 # master deleted it: keep it deleted
            else:
                _git(run, root, 'add', '--', p)
            resolved.append(p)
        _git(run, root, 'rebase', '--continue', env=env)            # the next stop (if any) is handled by the loop
    return False, {'reason': f'the rebase needed more than {max_steps} steps'}


def after_generated_rebase(root, resolved, run=subprocess.run, config=None, log=_log):
    """Master's copies were kept: re-stamp the build, and queue a rebuild of every other generated file (open failures
    the hourly job retries: 'tutor' rebuilds the audit pages + Tutor page, 'refresh:<date>' re-feeds a lesson that is now
    missing from a page). Append-only logs (*.jsonl) need nothing. Returns the queued keys."""
    rules = regenerate_rules(config)
    stamps = list(rules.get('stamp') or [])
    rebuild = [p for p in resolved if p not in stamps and not p.endswith('.jsonl')]
    if any(p in stamps for p in resolved) and (Path(root) / 'scripts/write_build.py').exists():
        run([sys.executable, 'scripts/write_build.py'], cwd=str(root), capture_output=True, text=True)
        _git(run, root, 'add', '--', *[p for p in stamps if (Path(root) / p).exists()])
        _git(run, root, 'commit', '-q', '-m', 'Build stamp re-written after rebasing onto master (publish guard)\n\n'
                                              'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
    queued = []
    if rebuild:
        why = (f"{len(rebuild)} generated file(s) took master's copy after a rebase (rebuilt, never merged), e.g. "
               + ', '.join(rebuild[:4]) + ': rebuild pending')
        set_open_failures(root, 'tutor', [why]); queued.append('tutor')
        try:
            ok, detail = check_lesson_coverage(root, run)
        except Exception:
            ok, detail = True, ''
        for d in sorted(set(re.findall(r'(20\d\d-\d\d-\d\d)(?: missing from|: lesson page but not)', detail or ''))):
            set_open_failures(root, 'refresh:' + d, [f'lesson {d} lost page data in a rebase onto master: re-feed pending'])
            queued.append('refresh:' + d)
    log(f"publish guard: rebased onto master; {len(resolved)} generated file(s) kept master's copy"
        + (f"; rebuild queued ({', '.join(queued)})" if queued else ''))
    return queued


def guarded_push(root=ROOT, source='?', step_failures=(), run=subprocess.run, log=_log, remote='origin', branch='master',
                 pull=True, config=None):
    """Rebase on origin, check, then push HEAD:master only if every required check passes. Never raises for a block; returns
    {'pushed': bool, 'outcome': ..., 'reason': ...}. The local commits are kept on a block (nothing lost; the next hour
    re-checks and pushes them once the numbers add up)."""
    root = Path(root)
    ahead = lambda: (getattr(_git(run, root, 'rev-list', '--count', f'{remote}/{branch}..HEAD'), 'stdout', '') or '').strip()
    if pull:
        r = _git(run, root, 'pull', '--rebase', '--autostash', remote, branch)
        fixed, info = False, {}
        if getattr(r, 'returncode', 0):
            try:
                cfg = config or load_config(root)
            except Exception:
                cfg = {}
            fixed, info = resolve_generated_conflicts(root, run=run, config=cfg)
            if fixed:
                after_generated_rebase(root, info.get('resolved') or [], run=run, config=cfg, log=log)
        if getattr(r, 'returncode', 0) and not fixed:
            _git(run, root, 'rebase', '--abort')
            why = info.get('reason') if info.get('files') else None
            reason = 'pull --rebase failed (a conflict with master; a person merges): ' + (why or _short(getattr(r, 'stderr', ''), 200))
            res = {'at': now_iso(), 'sha': None, 'checks': []}
            record(root, res, source, 'rebase_failed', reason, ahead())
            log(block_line(source, reason, ahead()))
            return {'pushed': False, 'outcome': 'rebase_failed', 'reason': reason}
    res = run_checks(root, config=config, step_failures=step_failures, run=run)
    if not res['ok']:
        waiting = ahead()
        record(root, res, source, 'blocked', waiting=waiting)
        log(block_line(source, res['reason'], waiting))
        for w in res.get('warnings', []):
            log('publish guard warning:', w[:300])
        return {'pushed': False, 'outcome': 'blocked', 'reason': res['reason'], 'result': res}
    st = read_state(root)
    try:
        _write_json(root / PUBLISHED, published_status(res, st, source))
        _git(run, root, 'add', PUBLISHED)
        _git(run, root, 'commit', '-q', '-m', f'Publish guard: all required checks passed ({source})\n\n'
                                              'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
    except Exception as e:                       # the checks passed; a status-file hiccup must not hold the data back
        log('publish guard: status file not written', e)
    head = (getattr(_git(run, root, 'rev-parse', 'HEAD'), 'stdout', '') or '').strip()
    p = _git(run, root, 'push', remote, f'HEAD:{branch}', env={**os.environ, OK_ENV: head})
    if getattr(p, 'returncode', 0):
        reason = 'git push failed: ' + _short(getattr(p, 'stderr', ''), 200)
        record(root, res, source, 'push_failed', reason, ahead())
        log(block_line(source, reason, ahead()))
        return {'pushed': False, 'outcome': 'push_failed', 'reason': reason, 'result': res}
    record(root, res, source, 'pushed')
    log(f"publish guard passed ({sum(1 for c in res['checks'] if c['required'])} required checks, {res.get('secs')} s) -> pushed ({source})")
    for w in res.get('warnings', []):
        log('publish guard warning:', w[:300])
    return {'pushed': True, 'outcome': 'pushed', 'reason': '', 'result': res}


# ---------------------------------------------------------------- pre-push hook (optional belt: manual pushes too)

def hook(stdin_lines, root=ROOT, run=subprocess.run, log=_log):
    """git pre-push: a push to master passes when the guard itself is pushing that exact commit, or when the checks pass on
    a checkout whose HEAD is the commit being pushed. Other branches are never touched."""
    ok_sha = os.environ.get(OK_ENV)
    head = (getattr(_git(run, root, 'rev-parse', 'HEAD'), 'stdout', '') or '').strip()
    for line in stdin_lines:
        parts = line.split()
        if len(parts) < 4 or parts[2] != 'refs/heads/master' or set(parts[1]) == {'0'}:
            continue
        if ok_sha and parts[1] == ok_sha:
            continue
        if parts[1] != head:
            log('PUBLISH BLOCKED (manual push): pushing a commit that is not checked out here; use scripts/publish_guard.py push')
            return 1
        res = run_checks(root, run=run)
        record(root, res, 'manual push', 'checked' if res['ok'] else 'blocked')
        if not res['ok']:
            log(block_line('manual push', res['reason'], None)); return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['check', 'push', 'status', 'hook'])
    ap.add_argument('--source', default='manual')
    ap.add_argument('--root', default=str(ROOT))
    a, _rest = ap.parse_known_args(argv)
    root = Path(a.root)
    if a.cmd == 'status':
        print(json.dumps(read_state(root), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'hook':
        return hook(sys.stdin.read().splitlines(), root)
    if a.cmd == 'push':
        return 0 if guarded_push(root, a.source)['pushed'] else 1
    res = run_checks(root)
    for c in res['checks']:
        print(f"{'PASS' if c['ok'] else ('FAIL' if c['required'] else 'warn')} {c['id']:<17} {c['secs']:>6} s  {c['detail']}")
    print('publish guard:', 'OK - publishable' if res['ok'] else 'BLOCKED - ' + res['reason'][:400])
    record(root, res, a.source, 'checked')
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    sys.exit(main())
