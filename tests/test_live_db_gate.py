"""The live-database gate (tests/conftest.py, audit 2026-09-29): tests that write to Medi's live Supabase data are
skipped unless ANEES_E2E_LIVE=1. Before the gate, test_m5_cards / test_m4_after ran in every full pytest run."""
import importlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


def _fn(mod, name):
    return getattr(importlib.import_module(mod), name)


def test_known_live_writers_are_gated():
    import conftest
    for mod, name in [("test_m4_after", "test_stand_in_answers_5_questions_and_homework_under_5_min"),
                      ("test_m4_after", "test_link_expires_after_7_days"),
                      ("test_m3_planner", "test_stand_in_completes_planner_on_phone_under_2_min")]:
        assert conftest.live_writer(_fn(mod, name)), (mod, name)


def test_offline_tests_are_not_gated():
    import conftest
    for mod, name in [("test_m5_cards", "test_scheduler_missed_3x_cold_over_300_draws"),
                      ("test_m5_cards", "test_js_buckets_parity_with_python"),
                      ("test_m4_after", "test_questions_bounded_and_audio_short")]:
        assert not conftest.live_writer(_fn(mod, name)), (mod, name)


# ---- FC-08 (Medi 2026-09-29 "delete", again 2026-10-02): test runs never write to Medi's card history -------------------
import ast, inspect, os, re
import pytest

TESTS = ROOT / "tests"


def _test_functions():
    """(file, name, source) for every test function in tests/test_*.py (backups excluded)."""
    for f in sorted(TESTS.glob("test_*.py")):
        src = f.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                yield f.name, node.name, ast.get_source_segment(src, node) or ""


PW, CR = "sync_" + "playwright", "card_" + "results"      # split so this guard's own source is not taken for a live writer
DEL_CR = "delete from " + CR


def test_fc_08_every_card_grading_browser_test_uses_the_stub():
    """A Playwright test that opens the Flashcards page (or reads the card table) must send its answers into rest_stub,
    never read them back from - or clean them out of - the live table."""
    import conftest
    bad = []
    readback = re.compile(r"db\.(select|sql|rest)\([^)]*" + CR)
    for f, name, src in _test_functions():
        if PW not in src or not ("cards.html" in src or CR in src):
            continue
        if "rest_stub" not in src or readback.search(src) or DEL_CR in src:
            bad.append(f"{f}::{name}")
        elif conftest.live_writer(getattr(__import__(f[:-3]), name)):
            bad.append(f"{f}::{name} (still counted as a live writer)")
    assert not bad, "FC-08: these browser tests can write to Medi's live card table: " + ", ".join(bad)
    assert sum(1 for f, n, s in _test_functions() if PW in s and "cards.html" in s) >= 2   # the m5 tests are seen


def test_fc_08_no_unstubbed_test_can_write_live():
    """Every other test whose source writes to the live database is skipped unless the run points at a non-Medi project."""
    import conftest
    writers = []
    for f, name, src in _test_functions():
        fn = getattr(__import__(f[:-3]), name, None)
        if fn is not None and conftest.live_writer(fn):
            writers.append(f"{f}::{name}")
            assert not conftest.live_target_ok()            # so the collection hook skips each of them in this run
    assert "test_m4_after.py::test_stand_in_answers_5_questions_and_homework_under_5_min" in writers


def test_fc_08_live_flag_alone_is_not_enough(monkeypatch):
    import conftest, anees_env as E
    monkeypatch.setenv("ANEES_E2E_LIVE", "1")
    monkeypatch.setattr(E, "SUPABASE_REF", conftest.MEDI_REF)
    assert not conftest.live_target_ok(), "ANEES_E2E_LIVE=1 against Medi's own project must still refuse"
    monkeypatch.setattr(E, "SUPABASE_REF", "some-test-project")
    assert conftest.live_target_ok()
    monkeypatch.delenv("ANEES_E2E_LIVE")
    assert not conftest.live_target_ok()


def test_fc_08_write_classifier():
    import conftest as C
    rest = f"https://{C.MEDI_HOST}/rest/v1/card_results"
    q = f"https://api.supabase.com/v1/projects/{C.MEDI_REF}/database/query"
    for m in ("POST", "PATCH", "PUT", "DELETE", "post"):
        assert C.is_live_write(m, rest), m
    assert not C.is_live_write("GET", rest + "?select=id")
    assert C.is_live_write("POST", q, {"query": "delete from card_results where round_id like 'r%'"})
    assert C.is_live_write("POST", q, {"query": "UPDATE word_stats set card_right=0"})
    assert C.is_live_write("POST", q, {"query": "insert into card_results values (1)"})
    assert not C.is_live_write("POST", q, {"query": "select id, created_at, updated_at from card_results"})
    assert not C.is_live_write("POST", "https://other.supabase.co/rest/v1/card_results")


def test_fc_08_python_write_to_medi_project_is_blocked():
    """The runtime net is on in every test: a write to Medi's project raises before a byte is sent.
    (Sent without keys and matching no row, so even a broken net could not change anything.)"""
    import requests, conftest as C
    with pytest.raises(C.LiveWriteBlocked):
        requests.patch(f"https://{C.MEDI_HOST}/rest/v1/card_results", params={"id": "eq.__fc08_never__"}, json={})
    with pytest.raises(C.LiveWriteBlocked):
        requests.post(f"https://api.supabase.com/v1/projects/{C.MEDI_REF}/database/query",
                      json={"query": "delete from card_results where id = '__fc08_never__'"})


def test_fc_08_browser_write_never_leaves_the_page(rest_stub):
    """Any Playwright page a test opens answers writes to Medi's host locally; rest_stub sees exactly what was sent."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("playwright not installed")
    import conftest as C
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:
            pytest.skip(f"no chromium: {e}")
        ctx = b.new_context(); rest_stub.attach(ctx); pg = ctx.new_page(); pg.goto("about:blank")
        status = pg.evaluate("""async u => (await fetch(u, {method:'POST', headers:{'Content-Type':'application/json',
            Prefer:'resolution=ignore-duplicates'}, body: JSON.stringify([{id:'fc08-x', word_key:'kalb', result:'got'}])})).status""",
                             f"https://{C.MEDI_HOST}/rest/v1/card_results?on_conflict=id")
        plain = b.new_page(); plain.goto("about:blank")            # no explicit stub: the autouse net still answers locally
        status2 = plain.evaluate("async u => (await fetch(u, {method:'PATCH', body:'{}'})).status",
                                 f"https://{C.MEDI_HOST}/rest/v1/card_results?id=eq.__fc08_never__")
        b.close()
    assert status == 201 and status2 == 204
    assert [r["id"] for r in rest_stub.rows("card_results")] == ["fc08-x"]
