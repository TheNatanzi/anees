"""Amal's Tutor Hub link (never sent by the app - Medi sends it). Creates ONE amal_links row of kind 'review' whose payload
carries her other open links, and prints the hub URL. Re-running reuses an open, unexpired review link.

  python scripts/amal_review_link.py            -> prints hub + review URLs
  python scripts/amal_review_link.py --new      -> mints a fresh token even if one is open
  python scripts/amal_review_link.py --days 30  -> validity (default 30 days: the backfill review is long)
"""
import argparse, datetime, io, json, secrets, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

ROOT = Path(__file__).resolve().parent.parent
PAGES = 'https://thenatanzi.github.io/anees/'


def open_links():
    """Her newest unexpired link of each kind, as URLs, for the hub tiles."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    links = {}
    for r in db.select('amal_links', {'select': 'token,kind,lesson_date,created_at,expires_at,done_at', 'expires_at': f'gt.{now}', 'order': 'created_at.desc'}):
        if r['kind'] in ('before', 'after') and r['kind'] not in links and not r.get('done_at'):
            links['plan' if r['kind'] == 'before' else 'after'] = f"{PAGES}amal/{'plan' if r['kind'] == 'before' else 'after'}.html?t={r['token']}"
    for table, key, page in (('verb_check_links', 'verb_check', 'verb-check'), ('transcript_review_links', 'word_review', 'word-review')):
        try:
            rows = db.select(table, {'select': 'token,created_at,expires_at,done_at', 'expires_at': f'gt.{now}', 'order': 'created_at.desc', 'limit': 5})
        except Exception:
            rows = []
        for r in rows:
            if not r.get('done_at'):
                links[key] = f"{PAGES}amal/{page}.html?t={r['token']}"
                break
    links['grammar_rules'] = f"{PAGES}amal/grammar-rules.html"
    return links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--new', action='store_true')
    ap.add_argument('--days', type=int, default=30)
    a = ap.parse_args()
    now = datetime.datetime.now(datetime.timezone.utc)
    links = open_links()
    existing = [] if a.new else db.select('amal_links', {'select': 'token,expires_at', 'kind': 'eq.review', 'expires_at': f'gt.{now.isoformat()}', 'order': 'created_at.desc', 'limit': 1})
    if existing:
        token = existing[0]['token']
        db.rest('PATCH', 'amal_links', params={'token': f'eq.{token}'}, body={'payload': {'links': links, 'refreshed': now.isoformat()}}, prefer='return=minimal')
    else:
        token = secrets.token_urlsafe(24)
        db.upsert('amal_links', [{'token': token, 'kind': 'review', 'lesson_date': None, 'created_at': now.isoformat(),
                                  'expires_at': (now + datetime.timedelta(days=a.days)).isoformat(), 'payload': {'links': links}}], on='token')
    hub, review = f'{PAGES}amal/hub.html?t={token}', f'{PAGES}amal/review.html?t={token}'
    out = ROOT / 'data' / 'amal_links.json'
    hist = json.load(io.open(out, encoding='utf-8')) if out.exists() else []
    if not any(h.get('url') == hub for h in hist):
        hist.append({'kind': 'review', 'lesson_date': None, 'created_at': now.isoformat(), 'expires_at': (now + datetime.timedelta(days=a.days)).isoformat(), 'url': hub})
        io.open(out, 'w', encoding='utf-8').write(json.dumps(hist, ensure_ascii=False, indent=1))
    print('HUB   ', hub)
    print('REVIEW', review)
    for k, v in links.items():
        print(f'{k:14}', v)


if __name__ == '__main__':
    main()
