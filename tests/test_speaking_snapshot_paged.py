# -*- coding: utf-8 -*-
"""Rule P1 (freshness audit 2026-10-02): a snapshot that grows with every lesson is never read in one request.
rpc/speaking_snapshot hit the statement timeout on every try once lesson 2026-10-01 was loaded, so the hourly job could
not refresh the Word Bank evidence and the lesson stayed blocked. Offline: the database is a fake."""
import re, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import speaking_snapshot as S


class FakeDb:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def select(self, table, params=None, **kw):
        self.calls.append((table, dict(params or {})))
        return list(self.rows)


def test_events_are_the_data_column_in_rpc_order():
    rows = [{'id': 'a', 'data': {'id': 'a', 'lesson_date': '2026-09-30'}}, {'id': 'b', 'data': {'id': 'b', 'lesson_date': '2026-10-01'}}]
    fake = FakeDb(rows)
    assert S.events(db=fake) == [r['data'] for r in rows]
    table, params = fake.calls[0]
    assert table == 'speaking_events' and params['order'] == 'lesson_date.asc,id.asc'


def test_a_row_read_twice_while_paging_fails_closed():
    rows = [{'id': 'a', 'data': {}}, {'id': 'a', 'data': {}}]
    with pytest.raises(RuntimeError):
        S.events(db=FakeDb(rows))


def test_the_scheduled_jobs_never_read_the_snapshot_in_one_call():
    for name in ('hourly_lessons.py', 'review_lesson.py', 'amal_trigger.py', 'audit_lessons.py'):
        src = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        code = '\n'.join(l for l in src.splitlines() if not l.strip().startswith('#'))
        assert not re.search(r"rest\(\s*'GET',\s*'rpc/speaking_snapshot'", code), name
