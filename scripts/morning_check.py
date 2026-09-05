"""Morning checklist, automated part. Prints PASS/FAIL per step with what to do on FAIL. Read-only except the test run.
  python scripts/morning_check.py            (~3-5 min; the pytest step is the slow one; add --quick to skip it)"""
import datetime, io, json, subprocess, sys, time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
PAGES = 'https://thenatanzi.github.io/anees/'
results = []


def step(name, ok, detail, if_fail):
    results.append((name, ok, detail, if_fail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}" + ('' if ok else f'\n      → {if_fail}'))


def main(quick=False):
    print('Anees morning check', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    # 1 Supabase reachable
    try:
        r = requests.get(f'{E.SUPABASE_URL}/rest/v1/words?select=key&limit=1', headers={'apikey': E.ANON_KEY, 'Authorization': f'Bearer {E.ANON_KEY}'}, timeout=15)
        step('Supabase', r.status_code == 200, f'HTTP {r.status_code}', 'open supabase.com → project anees → check it is not paused; the site still works from cache but Amal\'s links need it: do NOT send the link')
    except Exception as e:
        step('Supabase', False, str(e)[:80], 'network? open supabase.com; do NOT send the link until this passes')
    # 2 Pages live
    for p in ('index.html', 'amal/plan.html', 'amal/after.html', 'cards.html', 'lessons/2026-09-04-report.html'):
        try:
            t = time.time(); r = requests.get(PAGES + p, timeout=15); dt = time.time() - t
            step(f'Pages {p}', r.status_code == 200 and dt < 3, f'HTTP {r.status_code} in {dt:.1f}s', 'github.com/TheNatanzi/anees → Settings → Pages; re-push with: git push')
        except Exception as e:
            step(f'Pages {p}', False, str(e)[:80], 'check the internet connection, then git push')
    # 3 Amal links exist, fresh, not opened
    try:
        import db
        links = db.select('amal_links', {'select': 'token,kind,lesson_date,created_at,expires_at,opened_at,done_at', 'order': 'created_at.desc', 'limit': 6})
        before = [l for l in links if l['kind'] == 'before' and not l['done_at']]
        after = [l for l in links if l['kind'] == 'after' and not l['done_at']]
        step('Planner link', bool(before) and before[0]['expires_at'] > datetime.datetime.now(datetime.timezone.utc).isoformat(), f"{len(before)} open planner link(s); newest lesson_date {before[0]['lesson_date'] if before else '–'}",
             'python scripts/amal_links.py create --kind before --date <today> --payload data/planner_payload_2026-09-05.json')
        step('After-lesson link', bool(after), f"{len(after)} open after-lesson link(s) for {after[0]['lesson_date'] if after else '–'}", 'python scripts/amal_links.py create --kind after --date 2026-09-04 --payload data/lessons/2026-09-04/after_payload.json')
        step('Payload has 8 sentences', bool(before) and len((db.select('amal_links', {'token': f"eq.{before[0]['token']}", 'select': 'payload'})[0]['payload'] or {}).get('sentences', [])) == 8 if before else False, '8 Doc-checked sentences', 'python scripts/suggest.py (needs OpenAI, ~0.10 USD) then recreate the link')
    except Exception as e:
        step('Amal links', False, str(e)[:80], 'do NOT send anything; check Supabase first')
    # 4 Scheduler tasks
    for task in ('Anees lesson pipeline', 'Anees vocab import'):
        r = subprocess.run(['powershell', '-NoProfile', '-Command', f"(Get-ScheduledTask -TaskName '{task}').State"], capture_output=True, text=True)
        st = r.stdout.strip()
        step(f'Task "{task}"', st in ('Ready', 'Running'), st or r.stderr.strip()[:60], f'Task Scheduler → enable "{task}" (right-click → Enable)')
    # 5 Budget
    try:
        import pipeline_ext as px
        L = px.ledger()
        step('Budget', L.get('elevenlabs', 0) < 9 and L.get('openai', 0) < 9, f"ElevenLabs {L.get('elevenlabs', 0):.2f} / 10 USD, OpenAI {L.get('openai', 0):.2f} / 10 USD (ledger)", 'stop paid runs; edit data/budget.json only if you added credit')
    except Exception as e:
        step('Budget', False, str(e)[:80], 'check data/budget.json')
    # 6 Recording folder
    src = Path('G:/My Drive/Meet Recordings')
    step('Meet folder', src.exists(), 'G:/My Drive/Meet Recordings ' + ('found' if src.exists() else 'MISSING'), 'is Google Drive for Desktop running? the pipeline reads the recording from there')
    # 7 Email path
    env = Path('C:/Claude/Personal/Project Alchemy/alchemy-lock/.env')
    step('Gmail sender', env.exists() and 'GMAIL_APP_PASSWORD' in env.read_text(encoding='utf-8', errors='ignore'), 'alchemy-lock/.env present', 'emails will not send: check the Gmail app password in alchemy-lock/.env')
    # 8 Tests
    if not quick:
        r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-x', '--ignore=tests/test_m4_after.py', '--ignore=tests/test_m3_planner.py'], capture_output=True, text=True, cwd=str(ROOT), timeout=1500)
        last = (r.stdout.strip().splitlines() or [''])[-1]
        step('Tests', r.returncode == 0, last, 'read the failing test name; if it is a live-network test, re-run once; otherwise do NOT push and do NOT send the link')
    n_fail = sum(1 for x in results if not x[1])
    print(f"\n{'ALL GOOD' if not n_fail else str(n_fail) + ' FAIL'} — {len(results) - n_fail}/{len(results)} checks passed")
    if n_fail:
        print('Rule: with any FAIL above, do NOT send Amal the link. Fix first or ask.')
    return n_fail == 0


if __name__ == '__main__':
    sys.exit(0 if main(quick='--quick' in sys.argv) else 1)
