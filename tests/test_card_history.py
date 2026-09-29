"""Medi's flashcard history (card_results) is kept and is his (engineering audit 2026-09-29, area 7).

- Nothing can delete it through the app: RLS is on and there is no DELETE policy (the one UPDATE policy only
  sets undone_at, once, within an hour).
- No automated test run is left in it. Real answers take seconds; the e2e tests answer in ~0.2 s. On 2026-09-29
  09:14-09:43 UTC tests/test_m5_cards.py left 81 rows (9 rounds, Animals, median 237 ms) because its cleanup only
  ran when every in-browser assertion passed. Those rows made two test-made leeches (bese, na7el), used up the
  day's 8 new cards and moved every Progress & Stats card number. This test FAILS until they are removed (needs
  Medi's OK: nothing is deleted without it)."""
import statistics
import pytest
import anees_env as E

NET = bool(E.ACCESS_TOKEN and E.SERVICE_KEY)
pytestmark = pytest.mark.skipif(not NET, reason='needs Supabase')


def test_history_cannot_be_deleted_from_the_app():
    import db
    rls = db.sql("select relrowsecurity from pg_class where relname='card_results'")[0]['relrowsecurity']
    assert rls is True
    cmds = {r['polcmd'] for r in db.sql("select polcmd from pg_policy where polrelid='card_results'::regclass")}
    assert 'd' not in cmds and '*' not in cmds, cmds       # no DELETE (or ALL) policy for the page's key
    cols = {r['column_name'] for r in db.sql("select column_name from information_schema.column_privileges where table_name='card_results' and grantee='anon' and privilege_type='UPDATE'")}
    assert cols <= {'undone_at'}, cols


def test_no_machine_speed_test_rounds_in_medis_history():
    import db
    rows = db.select('card_results', {'select': 'round_id,answer_ms,created_at,subject'})
    by = {}
    for r in rows:
        if r['answer_ms'] is not None:
            by.setdefault(r['round_id'], []).append(r['answer_ms'])
    bots = {rid: (len(v), statistics.median(v)) for rid, v in by.items() if len(v) >= 5 and statistics.median(v) < 400}
    assert not bots, f'{sum(n for n, _ in bots.values())} answers in {len(bots)} rounds answered at machine speed: {sorted(bots)[:5]}'
