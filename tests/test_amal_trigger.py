"""Amal trigger (Medi M3, 2026-09-29): anything Amal does -> detect, re-pull, recalc, log; the publish guard decides."""
import json, sys, types
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import amal_trigger as T


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "STATE_P", tmp_path / "state.json")
    monkeypatch.setattr(T, "LOG_P", tmp_path / "log.jsonl")
    monkeypatch.setattr(T, "PAGE_P", tmp_path / "amal-trigger.json")
    vals = {"answers": {"hash": "h1", "n": 1, "newest": "t1"}}
    nums = {"now": {"Words % (all lessons)": 80.8}}
    monkeypatch.setattr(T, "numbers", lambda root=None: dict(nums["now"]))
    calls, fail = [], []

    def runner(cmd, **k):
        calls.append(cmd)
        name = next((n for n, c in T.STEPS if c == cmd), None)
        if name == "build_tutor_data":
            nums["now"] = {"Words % (all lessons)": 81.2}
        return types.SimpleNamespace(returncode=fail.pop(0) if fail else 0, stdout="", stderr="boom")

    src = [{"id": "tutor_verify", "label": "Tutor", "fetch": lambda: dict(vals["answers"]), "steps": ["build_tutor_data", "apply_amal_audit_rulings"]},
           {"id": "grammar_doc", "label": "Doc", "fetch": lambda: (_ for _ in ()).throw(T.Unreadable("private: HTTP 401")), "steps": []}]
    return types.SimpleNamespace(vals=vals, calls=calls, runner=runner, src=src, tmp=tmp_path, fail=fail)


def test_first_sight_is_a_baseline_not_a_firing(world):
    r = T.run(runner=world.runner, sources=world.src, log=lambda *a: None)
    assert not r["fired"] and world.calls == []
    assert json.loads(T.STATE_P.read_text())["sources"]["tutor_verify"]["fp"]["hash"] == "h1"


def test_a_new_answer_fires_reruns_builders_in_order_and_logs_numbers(world):
    T.run(runner=world.runner, sources=world.src, log=lambda *a: None)
    world.vals["answers"] = {"hash": "h2", "n": 2, "newest": "t2"}
    r = T.run(runner=world.runner, sources=world.src, log=lambda *a: None)
    assert r["fired"] and r["changed"] == ["tutor_verify"]
    order = [n for n, c in T.STEPS]
    ran = r["firing"]["steps"]
    assert ran == sorted(ran, key=order.index) == ["apply_amal_audit_rulings", "build_tutor_data"]
    assert r["firing"]["numbers_moved"] == [{"what": "Words % (all lessons)", "from": 80.8, "to": 81.2}]
    assert json.loads(T.LOG_P.read_text().splitlines()[-1])["changed"][0]["source"] == "tutor_verify"
    page = json.loads(T.PAGE_P.read_text())
    assert page["firings"][0]["numbers_moved"] and any(s["id"] == "grammar_doc" and not s["readable"] and "401" in s["why"] for s in page["sources"])
    assert not T.run(runner=world.runner, sources=world.src, log=lambda *a: None)["fired"]   # unchanged -> quiet


def test_a_failed_step_keeps_the_old_fingerprint_so_the_next_run_retries(world):
    T.run(runner=world.runner, sources=world.src, log=lambda *a: None)
    world.vals["answers"] = {"hash": "h2", "n": 2, "newest": "t2"}
    world.fail[:] = [1]
    r = T.run(runner=world.runner, sources=world.src, log=lambda *a: None)
    assert r["firing"]["failures"]
    assert T.run(runner=world.runner, sources=world.src, log=lambda *a: None)["fired"]


def test_publish_goes_through_the_guard(world, monkeypatch):
    got = {}
    fake = types.ModuleType("publish_guard")
    fake.guarded_push = lambda root, source, step_failures, log: got.update(source=source, failures=step_failures) or {"outcome": "blocked"}
    monkeypatch.setitem(sys.modules, "publish_guard", fake)
    T.run(runner=world.runner, sources=world.src, log=lambda *a: None)
    world.vals["answers"] = {"hash": "h3", "n": 3, "newest": "t3"}
    r = T.run(publish=True, runner=world.runner, sources=world.src, log=lambda *a: None)
    assert got["source"] == "amal trigger" and r["firing"]["published"] == "blocked"


def test_machine_flags_and_medis_marks_are_not_amal():
    assert "flashcards" in T.NOT_AMAL_SOURCES and "medi" in T.NOT_AMAL_SOURCES


def test_every_amal_input_named_by_medi_has_a_source():
    ids = {s["id"] for s in T.SOURCES}
    assert {"tutor_verify", "verb_checks", "word_review", "pattern_review", "grammar_doc", "quizlet"} <= ids
    steps = {n for n, _ in T.STEPS}
    assert all(set(s["steps"]) <= steps for s in T.SOURCES)


def test_private_doc_says_exactly_why(monkeypatch):
    monkeypatch.delenv("ANEES_GRAMMAR_DOC_URL", raising=False)
    with pytest.raises(T.Unreadable, match="401"):
        T.fetch_grammar_doc()


def test_hourly_job_runs_the_trigger():
    src = (ROOT / "scripts" / "hourly_lessons.py").read_text(encoding="utf-8")
    assert "amal_trigger" in src
    assert (ROOT / "scripts" / "run_amal_trigger.ps1").exists()
