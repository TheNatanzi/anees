"""Amal's secret-token links (no login). Creates amal_links rows and prints the URL. NEVER sends anything to Amal.

  python scripts/amal_links.py create --kind before --date 2026-09-05      # planner link
  python scripts/amal_links.py create --kind after  --date 2026-09-04      # after-lesson questions for that lesson
  python scripts/amal_links.py list
The payload (questions / suggestions) is built by scripts/suggest.py (before) and scripts/after_questions.py (after)."""
import argparse, datetime, io, json, secrets, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

ROOT = Path(__file__).resolve().parent.parent
PAGES = 'https://thenatanzi.github.io/anees/'
PAGE = {'before': 'amal/plan.html', 'after': 'amal/after.html'}
DAYS = 7


def url(kind, token):
    return f'{PAGES}{PAGE[kind]}?t={token}'


def create(kind, lesson_date, payload):
    token = secrets.token_urlsafe(24)
    now = datetime.datetime.now(datetime.timezone.utc)
    row = {'token': token, 'kind': kind, 'lesson_date': lesson_date, 'created_at': now.isoformat(),
           'expires_at': (now + datetime.timedelta(days=DAYS)).isoformat(), 'payload': payload}
    db.upsert('amal_links', [row], on='token')
    if kind == 'after' and payload.get('prompts'):                       # M10c: the prompt lines live in homework_items, bound to this token
        import homework
        stored = homework.mint_items(lesson_date, token, payload['prompts'])
        if stored:
            payload = {**payload, 'prompts': [{'id': r['id'], 'n': r['n'], 'english': r['english'], 'keys': r['keys']} for r in stored]}
            db.rest('PATCH', 'amal_links', params={'token': f'eq.{token}'}, body={'payload': payload}, prefer='return=minimal')
    out = ROOT / 'data' / 'amal_links.json'
    hist = json.load(io.open(out, encoding='utf-8')) if out.exists() else []
    hist.append({'kind': kind, 'lesson_date': lesson_date, 'created_at': row['created_at'], 'expires_at': row['expires_at'], 'url': url(kind, token)})
    io.open(out, 'w', encoding='utf-8').write(json.dumps(hist, ensure_ascii=False, indent=1))
    return token, url(kind, token)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    c = sub.add_parser('create'); c.add_argument('--kind', choices=['before', 'after'], required=True); c.add_argument('--date', required=True)
    c.add_argument('--payload', help='JSON file (default: build it)')
    sub.add_parser('list')
    a = ap.parse_args()
    if a.cmd == 'list':
        for r in db.select('amal_links', {'select': 'token,kind,lesson_date,created_at,expires_at,opened_at,done_at', 'order': 'created_at.desc'}):
            print(r['kind'], r['lesson_date'], 'done' if r['done_at'] else ('opened' if r['opened_at'] else 'new'), url(r['kind'], r['token']))
        return
    if a.payload:
        payload = json.load(io.open(a.payload, encoding='utf-8'))
    elif a.kind == 'before':
        import suggest
        payload = suggest.planner_payload(a.date)
    else:
        import after_questions
        payload = after_questions.payload(a.date)
    token, u = create(a.kind, a.date, payload)
    print(u)


if __name__ == '__main__':
    main()
