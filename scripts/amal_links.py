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


def answered(r):
    """An after/before link Amal answered: she finished it, or tapped at least one step."""
    a = r.get('answers') or {}
    return bool(r.get('done_at') or a.get('done') or any(a.get(k) for k in ('q', 'hw', 'v', 'pr', 'topic', 'sentences')))


def reuse_for(rows, kind, lesson_date, now_iso):
    """AM-18 (Medi 2026-10-02 "close, but I want accordians to see the results and what you are asking"): a lesson gets ONE
    after (or before) link. The hourly re-review re-runs review_lesson.py step 7b on a lesson whose transcript grew, and
    every run minted a fresh link - on 2026-10-02 that re-opened Oct 1, Sep 26 and Sep 23, which Amal had already answered.
    -> the existing link to keep (answered, or still open), or None when a new one may be made (none yet, or only expired
    links she never touched)."""
    mine = [r for r in rows if r.get('kind') == kind and r.get('lesson_date') == lesson_date]
    done = [r for r in mine if answered(r)]
    if done:
        return max(done, key=lambda r: r.get('created_at') or '')
    live = [r for r in mine if (r.get('expires_at') or '') > now_iso]
    return max(live, key=lambda r: r.get('created_at') or '') if live else None


def create(kind, lesson_date, payload, force=False):
    now = datetime.datetime.now(datetime.timezone.utc)
    if not force:
        rows = db.select('amal_links', {'select': 'token,kind,lesson_date,created_at,expires_at,done_at,answers', 'kind': f'eq.{kind}', 'lesson_date': f'eq.{lesson_date}'})
        keep = reuse_for(rows, kind, lesson_date, now.isoformat())
        if keep:
            print(f'{kind} link for {lesson_date} kept (already {"answered" if answered(keep) else "open"}); no new link (AM-18)')
            return keep['token'], url(kind, keep['token'])
    token = secrets.token_urlsafe(24)
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
