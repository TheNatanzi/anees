# -*- coding: utf-8 -*-
"""Publish guard (Medi decision 7, 2026-09-29): "every hourly run re-checks the math BEFORE publishing. If anything doesn't
add up, it doesn't publish, it keeps the last good version live, and it tells Medi why."

How publishing works: GitHub Pages builds the live site from master:/docs (a "legacy" Pages build, no workflow file), so
EVERY `git push origin HEAD:master` publishes. This module is the one door to that push. Every pusher calls
`guarded_push()` instead of `git push`:

    hourly_lessons.publish / tutor_refresh / decisions_refresh / gap_fill_refresh / the stranded-commit push in main(),
    review_lesson.py step 8, lesson_pipeline.git_publish / publish (retired job, still importable)

guarded_push(): pull --rebase (abort + stop on conflict) -> run_checks() on exactly what would be pushed -> on any failed
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

import argparse, datetime, glob, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = 'scripts/publish_guard_config.json'
STATE = 'data/publish-guard/state.json'            # local only (.gitignore): what happened on THIS PC, incl. blocks
PUBLISHED = 'docs/data/publish-guard.json'         # published with each passing push; System Settings reads it
NODE_DEFAULT = r'C:\dev\tools\node-v24.18.0-win-x64\node.exe'
BUILTINS = ('step_failures', 'clean_tree', 'json_data', 'lesson_coverage', 'review_freshness', 'lesson_type_read')
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
    s = ' | '.join(lines[-3:])
    return s if len(s) <= n else '...' + s[-n:]


# ---------------------------------------------------------------- built-in checks (read the working tree, no network)

def check_step_failures(root, failures, **_):
    """Steps of THIS run that failed (a builder crashed, a reader wrote nothing): their outputs may be stale."""
    failures = list(failures or [])
    return (not failures, '; '.join(str(f) for f in failures)[:600] if failures else 'no step failed in this run')


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
               'review_freshness': lambda: check_review_freshness(root),
               'lesson_type_read': lambda: check_lesson_type_read(root)}
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
         'review_freshness': 'the two readers read the transcript the pages show now',
         'lesson_type_read': 'no default lesson type shown as a reading'}


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


def guarded_push(root=ROOT, source='?', step_failures=(), run=subprocess.run, log=_log, remote='origin', branch='master',
                 pull=True, config=None):
    """Rebase on origin, check, then push HEAD:master only if every required check passes. Never raises for a block; returns
    {'pushed': bool, 'outcome': ..., 'reason': ...}. The local commits are kept on a block (nothing lost; the next hour
    re-checks and pushes them once the numbers add up)."""
    root = Path(root)
    ahead = lambda: (getattr(_git(run, root, 'rev-list', '--count', f'{remote}/{branch}..HEAD'), 'stdout', '') or '').strip()
    if pull:
        r = _git(run, root, 'pull', '--rebase', '--autostash', remote, branch)
        if getattr(r, 'returncode', 0):
            _git(run, root, 'rebase', '--abort')
            reason = 'pull --rebase failed (a conflict with master; a person merges): ' + _short(getattr(r, 'stderr', ''), 200)
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
