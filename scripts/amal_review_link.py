"""Amal's review link (never sent by the app - Medi sends it). Creates ONE amal_links row of kind 'review' whose payload
carries her other open links, and prints the review URL (the Tutor Hub page was removed 2026-09-28). Re-running reuses an open, unexpired review link.

  python scripts/amal_review_link.py            -> prints the review URL
  python scripts/amal_review_link.py --new      -> mints a fresh token even if one is open
  python scripts/amal_review_link.py --days 30  -> validity (default 30 days: the backfill review is long)
  python scripts/amal_review_link.py --renew    -> keep her newest review link alive (run by the Amal trigger)

Medi 2026-10-26 ("fix so I never get these"): the review link minted 09-26 ran out on 10-26 12:15; her Tutor page lost 17
of 18 lists and the hourly publish stalled 10 h on the tests that expect them. --renew moves the newest review link's
expiry to 30 days from now whenever it has 7 days or less left (or ran out in the last 14 days), keeping the same token,
so her page and her saved answers carry on with no new URL.
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


RENEW_WHEN_DAYS, RENEW_GRACE_DAYS, RENEW_TO_DAYS = 7, 14, 30


def renew(now=None, select=None, patch=None):
    """Extend the newest review link (same token) when it is close to running out. Returns the new expiry or None."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    select = select or db.select
    patch = patch or (lambda token, body: db.rest('PATCH', 'amal_links', params={'token': f'eq.{token}'}, body=body, prefer='return=minimal'))
    rows = select('amal_links', {'select': 'token,expires_at,done_at', 'kind': 'eq.review', 'order': 'created_at.desc', 'limit': 1})
    if not rows or rows[0].get('done_at'):
        return None
    exp = datetime.datetime.fromisoformat(str(rows[0]['expires_at']).replace('Z', '+00:00'))
    if exp - now > datetime.timedelta(days=RENEW_WHEN_DAYS) or now - exp > datetime.timedelta(days=RENEW_GRACE_DAYS):
        return None
    new = (now + datetime.timedelta(days=RENEW_TO_DAYS)).isoformat()
    patch(rows[0]['token'], {'expires_at': new})
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--renew', action='store_true')
    ap.add_argument('--new', action='store_true')
    ap.add_argument('--days', type=int, default=30)
    a = ap.parse_args()
    if a.renew:
        new = renew()
        print('review link renewed to ' + new if new else 'review link: nothing to renew')
        return
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
    review = f'{PAGES}amal/review.html?t={token}'
    out = ROOT / 'data' / 'amal_links.json'
    hist = json.load(io.open(out, encoding='utf-8')) if out.exists() else []
    if not any(h.get('url') == review for h in hist):
        hist.append({'kind': 'review', 'lesson_date': None, 'created_at': now.isoformat(), 'expires_at': (now + datetime.timedelta(days=a.days)).isoformat(), 'url': review})
        io.open(out, 'w', encoding='utf-8').write(json.dumps(hist, ensure_ascii=False, indent=1))
    print('REVIEW', review)
    for k, v in links.items():
        print(f'{k:14}', v)


if __name__ == '__main__':
    main()
