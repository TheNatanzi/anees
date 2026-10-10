# -*- coding: utf-8 -*-
"""AM-28 (Medi 2026-10-10: "For now, I know we've only done 10, 8, and 10-9. Let's put a pause on everything before
that until we can get the process honed down a little bit, and then we'll go back and clean everything up"):
the Tutor page asks only about lessons on/after scripts/tutor_scope.py TUTOR_FROM. Older open questions are paused
(kept in the file's paused block, never deleted); answered ones stay in her history; the hourly job makes no new
question for an older lesson."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import tutor_scope as TS  # noqa: E402


def _src(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def test_am_28_one_constant_mirrored_into_the_page_data():
    assert TS.TUTOR_FROM == "2026-10-08"
    assert '"tutor_from": tutor_scope.TUTOR_FROM' in _src("scripts", "build_tutor_data.py")
    js = _src("docs", "js", "tutor.js")
    assert "T.tutor_from" in js and "'2026-10-08'" not in js          # the page reads the date, never hard-codes it
    T = json.loads(_src("docs", "data", "tutor.json"))
    assert T.get("tutor_from") == TS.TUTOR_FROM


def test_am_28_old_open_item_paused_new_kept_answered_kept_in_history():
    doc = {"items": [{"id": "a", "date": "2026-10-02"}, {"id": "b", "date": "2026-10-08"}, {"id": "c", "date": "2026-10-02"},
                     {"id": "d"}]}
    n = TS.scope_doc(doc, "items", answered=lambda x: x["id"] == "c")
    assert n == 1
    assert [x["id"] for x in doc["items"]] == ["b", "c", "d"]        # 10-08 kept, answered 10-02 kept, undated kept
    assert [x["id"] for x in doc["paused"]["lists"]["items"]] == ["a"]
    assert doc["tutor_from"] == "2026-10-08"
    assert sorted(x["id"] for x in TS.all_items(doc)) == ["a", "b", "c", "d"]     # nothing deleted
    TS.scope_doc(doc, "items", start="")                              # lifting the pause brings it back
    assert sorted(x["id"] for x in doc["items"]) == ["a", "b", "c", "d"] and "paused" not in doc


def test_am_28_scope_file_review_patterns_by_newest_example(tmp_path):
    p = tmp_path / "amal-review.json"
    old = {"id": "p-old", "kind": "grammar", "examples": [{"uid": "FA-1", "date": "2026-09-16"}]}
    mixed = {"id": "p-mixed", "kind": "vocab", "examples": [{"uid": "FA-2", "date": "2026-09-16"}, {"uid": "FA-3", "date": "2026-10-09"}]}
    tapped = {"id": "p-tapped", "kind": "grammar", "examples": [{"uid": "FA-4", "date": "2026-10-02"}]}
    done = {"id": "p-done", "kind": "grammar", "examples": [{"uid": "FA-5", "date": "2026-09-04"}], "answered": {"kind": "audit_confirm"}}
    p.write_text(json.dumps({"patterns": [old, mixed, tapped], "answered": [done], "new_words": [], "counts": {}}), encoding="utf-8")
    TS.scope_file(str(p), answers={"p-tapped"})
    D = json.loads(p.read_text(encoding="utf-8"))
    assert [x["id"] for x in D["patterns"]] == ["p-mixed", "p-tapped"]
    assert [x["id"] for x in D["paused"]["lists"]["patterns"]] == ["p-old"]
    assert [x["id"] for x in D["answered"]] == ["p-done"]               # her history is untouched
    assert D["counts"]["patterns"] == 2 and D["counts"]["paused_patterns"] == 1


def test_am_28_hourly_job_makes_no_new_question_for_an_older_lesson(monkeypatch):
    import amal_links, db
    monkeypatch.setattr(db, "select", lambda *a, **k: [])          # no link yet for that lesson (AM-18 would keep one)
    monkeypatch.setattr(db, "upsert", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no link written")))
    make = amal_links.create          # (called through a name: the guard refuses before anything is written)
    assert make("after", "2026-10-02", {"questions": []}) == (None, None)
    import review_lesson as RL
    assert RL.new_words_step("2026-10-05", False, [], repo=ROOT, reader=lambda *a, **k: 1 / 0, run=lambda *a: 1 / 0) == []
    assert "tutor_scope.in_scope(d)" in _src("scripts", "review_lesson.py")
    assert 'tutor_scope.link_paused("after", a.date)' in _src("scripts", "after_from_audit.py")
    for f in ("build_amal_review.py", "amal_new_words.py", "codex_rejudge.py", "build_lessons_page_data.py"):
        assert "tutor_scope.scope_file(" in _src("scripts", f), f


def test_am_28_built_files_pause_only_open_items_of_older_lessons():
    d = os.path.join(ROOT, "docs", "data")
    for n in ("amal-review.json", "amal-verify.json", "amal-ledger.json", "amal-new-words.json", "amal-listen.json"):
        D = json.loads(_src("docs", "data", n))
        assert D.get("tutor_from") == TS.TUTOR_FROM, n
        for key, items in ((D.get("paused") or {}).get("lists") or {}).items():
            for x in items:
                date = TS.pattern_date(x) if n == "amal-review.json" else x.get("date")
                assert date and date < TS.TUTOR_FROM, (n, key, x.get("id"))
                assert x.get("status") in (None, "open"), (n, x.get("id"))      # an answered card is never paused
    assert os.path.isdir(d)
