"""The Speaking snapshot's events, read in pages of 1,000 rows (same order as rpc/speaking_snapshot: lesson_date, id).

Why (freshness audit 2026-10-02): the hourly job read the whole snapshot in ONE rpc/speaking_snapshot call. Once lesson
2026-10-01 was loaded the call passed the database statement timeout ("57014 canceling statement due to statement
timeout") on every try, so the Word Bank evidence could not be refreshed and the lesson stayed blocked. The browser has
read it in pages since 2026-09-23 (docs/js/speaking-snapshot.js); scripts now do the same. Rule: a snapshot that grows
with every lesson is never read in one request.

    python scripts/speaking_snapshot.py            # print how many events the paged read returns
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def events(db=None, retries=4):
    """Every speaking event (the `data` column), ordered like the RPC. Raises if the table changed while paging."""
    if db is None:
        import db as _db
        db = _db
    rows = db.select('speaking_events', {'select': 'id,data', 'order': 'lesson_date.asc,id.asc'}, retries=retries)
    ids = [r.get('id') for r in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError('speaking_events changed while paging (a row was read twice); retry')
    return [r['data'] for r in rows]


if __name__ == '__main__':
    print(len(events()), 'events')
