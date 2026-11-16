# -*- coding: utf-8 -*-
"""The self-repair step of the hourly job (Medi 2026-11-16: "bro how the f do we fix this once and for all"; 1,006 blocked
pushes since 2026-09-29, the 11-10/11/12 lessons waited 5 days, and the alarms only showed on the site the block froze).

Run at the end of every hourly run, INSIDE the job's lock (scripts/hourly_lessons.py). Two parts:

  1 fix    when the last guard check was blocked (a hard check) or left soft failures (published anyway, see
           scripts/publish_guard_config.json "soft"), one `claude -p` run on Medi's Claude plan ($0) gets the failing
           checks and fixes the real cause in this checkout (commit, never push - the next guarded push publishes it).
           At most MAX_TRIES a day and never twice within GAP_H hours, so a fix that cannot land does not loop.
  2 alarm  a lesson recorded more than ALARM_H hours ago that is still not on the live site -> ONE email to Medi
           (scripts/send_lesson_email.mjs, Medi only) per lesson. Never contacts Amal.

    python scripts/auto_fix_guard.py            # what the hourly job runs
    python scripts/auto_fix_guard.py --dry-run  # say what it would do, run nothing
"""
import datetime, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
STATE = ROOT / 'data' / 'publish-guard' / 'autofix.json'          # local only, like state.json
MAX_TRIES, GAP_H, ALARM_H, TIMEOUT_S = 2, 3, 12, 45 * 60
CLAUDE = os.environ.get('ANEES_CLAUDE') or shutil.which('claude') or str(Path.home() / '.local' / 'bin' / 'claude.exe')

PROMPT = """You are fixing the Anees hourly lesson job's publish guard in the repository at {root}. The guard just reported:

{failures}

Fix the REAL cause so these checks pass, in this checkout only:
- Read the failing check / test, find why it fails NOW (usually new lesson data the code or a test did not expect), fix the
  code or the stale expectation. Never delete or weaken a test just to make it pass; if a test asserts an old fact about data
  that legitimately changed, update it and say why in a comment.
- Re-run the failing check(s) to prove they pass (python -m pytest <file>::<test>, or the check's script).
- Commit your changes: git commit --no-verify -m "auto-fix: <what>" -- <files>. Do NOT push. Do not touch research/.
- Never contact anyone, never spend money (no paid API keys), never change accounts or logins.
- Environment: ANEES_RAW={raw}, PYTHONIOENCODING=utf-8.
End with one line per failure: FIXED <check>: <cause> -> <fix>, or NOT FIXED <check>: <why>."""


def now():
    return datetime.datetime.now().astimezone()


def load():
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')


def failures_now(gst):
    """The failing checks of the last guard run: hard (blocked) first, then soft (published anyway)."""
    lc = gst.get('last_check') or {}
    out = []
    if lc.get('outcome') in ('blocked',):
        hard = [c for c in lc.get('checks') or [] if c.get('required') and not c.get('ok') and not c.get('soft')]
        if hard:                              # one entry per failed check (a detail can itself hold '; ')
            out += [f"{c['id']}: {c.get('detail') or ''}" for c in hard]
        elif lc.get('reason'):
            out += [x.strip() for x in re.split(r'; (?=[a-z_]+: )', str(lc['reason'])) if x.strip()]
    out += list((gst.get('soft_failures') or {}).get('failures') or [])
    seen, uniq = set(), []
    for f in out:
        k = f.split(':', 1)[0]
        if k not in seen:
            seen.add(k)
            uniq.append(f[:700])
    return uniq


def may_try(st, t=None):
    t = t or now()
    tries = [datetime.datetime.fromisoformat(x).astimezone() for x in st.get('tries') or []]
    today = [x for x in tries if x.date() == t.date()]
    if len(today) >= MAX_TRIES:
        return False, f'{len(today)} tries today already (max {MAX_TRIES})'
    if tries and (t - max(tries)).total_seconds() < GAP_H * 3600:
        return False, f'last try {max(tries):%H:%M}, next after {GAP_H} h'
    return True, ''


def fix(fails, log, dry=False):
    st = load()
    ok, why = may_try(st)
    if not ok:
        log('auto-fix: skipped -', why)
        return None
    raw = os.environ.get('ANEES_RAW', str(ROOT / 'data' / 'lessons'))
    prompt = PROMPT.format(root=ROOT, raw=raw, failures='\n'.join('- ' + f for f in fails))
    if dry:
        log('auto-fix: would run claude -p on', len(fails), 'failure(s):', '; '.join(f.split(':', 1)[0] for f in fails))
        return None
    st.setdefault('tries', []).append(now().isoformat(timespec='seconds'))
    st['tries'] = st['tries'][-20:]
    save(st)
    log('auto-fix: claude -p on', '; '.join(f.split(':', 1)[0] for f in fails))
    t0 = time.time()
    import track                              # rule AI-logged: every AI call path logs a run (data/runs); $0 on the plan
    cmd = [CLAUDE, '-p', '--output-format', 'json', '--permission-mode', 'bypassPermissions', '--add-dir', str(ROOT)] + track.claude_model_args()
    try:
        with track.run('auto_fix_guard', None, kind='inference', provider='anthropic', request_model=track.CLAUDE_MODEL,
                       params={'failures': len(fails), 'prompt_arg_sha': track.sha256_text(prompt), 'timeout_s': TIMEOUT_S}) as run:
            r = subprocess.run(cmd, input=prompt, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace',
                               timeout=TIMEOUT_S, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'ANEES_RAW': raw})
            parsed = track.parse_claude_output(r.stdout)
            run.claude(parsed)
            out = (parsed.get('text') or r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        out = 'timed out after %d min' % (TIMEOUT_S // 60)
    except Exception as e:  # noqa: BLE001
        out = 'claude -p failed: %s %s' % (type(e).__name__, str(e)[:200])
    lines = [x for x in out.splitlines() if re.match(r'\s*(NOT )?FIXED\b', x)] or [out.strip()[-300:]]
    for x in lines:
        log('auto-fix:', x.strip()[:300])
    st = load()
    st['last'] = {'at': now().isoformat(timespec='seconds'), 'secs': int(time.time() - t0), 'failures': fails, 'result': lines}
    save(st)
    return lines


# ---------------------------------------------------------------- alarm: a lesson not live ALARM_H hours after it was recorded
def recorded_at(raw, date):
    fs = [p for p in Path(raw, date).glob('tracks/*.mp3')] + [p for p in Path(raw, date).glob('meet-*/audio.mp3')]
    return min((datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone() for p in fs), default=None)


def late_lessons(raw, live, t=None):
    t = t or now()
    out = []
    for d in sorted(x.name for x in Path(raw).glob('20??-??-??') if x.is_dir()):
        if d in live:
            continue
        at = recorded_at(raw, d)
        if at and (t - at).total_seconds() > ALARM_H * 3600 and (t - at).days < 14:
            out.append((d, at))
    return out


def alarm(log, reason, dry=False):
    import hourly_lessons as HL
    raw = os.environ.get('ANEES_RAW', str(ROOT / 'data' / 'lessons'))
    st = load()
    sent = set(st.get('alarmed') or [])
    late = [(d, at) for d, at in late_lessons(raw, HL.published_dates(ROOT)) if d not in sent]
    if not late:
        return []
    dates = [d for d, _ in late]
    hours = {d: int((now() - at).total_seconds() // 3600) for d, at in late}
    log('ALARM lesson(s) not live after %d h: %s' % (ALARM_H, ', '.join(f'{d} ({hours[d]} h)' for d in dates)))
    if dry:
        return dates
    payload = {'headline': f"{len(dates)} lesson{'s' if len(dates) > 1 else ''} not live yet",
               'sub': f"Recorded more than {ALARM_H} hours ago and still not on the site. The job is trying to fix it itself.",
               'rows': [{'tag': 'late', 'name': d, 'detail': f'{hours[d]} h since the recording'} for d in dates]
                       + [{'tag': 'why', 'name': 'blocked by', 'detail': (reason or 'see data/publish-guard/state.json')[:300]}],
               'link': 'https://thenatanzi.github.io/anees/', 'footer': 'Anees hourly job - auto_fix_guard.py',
               'text': f"Not live yet: {', '.join(dates)}. Blocked by: {(reason or '?')[:300]}",
               'chart': {'title': 'Hours since recording', 'bars': [{'label': d, 'value': hours[d]} for d in dates]},
               'log': [{'t': now().strftime('%H:%M'), 'text': 'alarm sent'}]}
    p = STATE.parent / 'alarm_email.json'
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    node = os.environ.get('ANEES_NODE') or (r'C:\dev\tools\node-v24.18.0-win-x64\node.exe'
                                           if os.path.exists(r'C:\dev\tools\node-v24.18.0-win-x64\node.exe') else 'node')
    r = subprocess.run([node, str(HERE / 'send_lesson_email.mjs'), 'Anees: lesson not live yet - ' + ', '.join(dates), str(p)],
                       cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode == 0:
        st['alarmed'] = sorted(sent | set(dates))[-60:]
        save(st)
        log('ALARM email sent to Medi')
    else:
        log('ALARM email failed:', (r.stderr or r.stdout)[-200:])
    return dates


def step(log=print, dry=False):
    """The hourly job's last step. Never raises."""
    try:
        import publish_guard as G
        gst = G.read_state(ROOT)
        fails = failures_now(gst)
        lines = fix(fails, log, dry) if fails else None
        reason = (gst.get('last_check') or {}).get('reason') if (gst.get('last_check') or {}).get('outcome') == 'blocked' else ''
        alarm(log, reason, dry)
        return bool(lines and any(x.strip().startswith('FIXED') for x in lines))
    except Exception as e:  # noqa: BLE001
        log('auto-fix step crashed:', type(e).__name__, str(e)[:200])
        return False


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    step(dry='--dry-run' in sys.argv)
