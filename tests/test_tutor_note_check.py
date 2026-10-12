# -*- coding: utf-8 -*-
"""AM-30 - the tutor checks the student's notes on a lesson before it is graded (Medi 2026-10-12: "wait I want amal to look
at my notes on 10-9 before grading and clearing it", then "go"). scripts/build_tutor_note_check.py: one card per distinct
live note of his on the lesson (undone / edited ones collapsed), her four plain answers saved like her other checking
lists, read-only into data/, and the lesson held - neither frozen nor graded - while a note is unanswered."""
import json, os, re, shutil, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "scripts"))
import build_tutor_note_check as NC  # noqa: E402

DATE = "2026-10-09"
DATA = json.loads((DOCS / "data" / ("amal-check-note-check-%s.json" % DATE)).read_text(encoding="utf-8"))


def _row(i, t, kind, raw, ts, **kw):
    r = {"id": "r%02d" % i, "lesson_date": DATE, "turn_t": t, "turn_who": "Medi", "kind": kind, "payload": {"raw": raw},
         "ts": "2026-10-11T18:%02d:00Z" % ts, "created_at": "2026-10-11T18:%02d:00Z" % ts}
    r.update(kw)
    return r


def test_am_30_one_card_per_distinct_live_note():
    rows = [
        _row(1, 100.0, "note", "tomi should be marked incorrect", 1),
        _row(2, 100.0, "add", "tomi should be marked incorrect", 2),                 # the parser's row of the same note
        _row(3, 100.0, "note", "tomi should be marked incorrect", 3),                 # its done marker
        _row(4, 200.0, "note", "first wording", 4),
        _row(5, 200.0, "undo", "", 5, undoes="r04"),                                  # edited: the old words are undone ...
        _row(6, 200.0, "note", "second wording", 6),                                  # ... and the new ones stand
        _row(7, 300.0, "text", "amal not aman", 7),
        _row(8, 303.0, "text", "amal not aman", 8),                                   # the same words on the next line: one note
        _row(9, 400.0, "not-use", "we arent counting names", 9),
        _row(10, 500.0, "missing", "a word is missing", 10),
        _row(11, 600.0, "not-slip", "she said both are fine", 11),
        _row(12, 700.0, "note", "undone and gone", 12),
        _row(13, 700.0, "undo", "", 13, undoes="r12"),
        _row(14, 800.0, "rule-answer", "", 14, proposal="review:fast", answer="one"),  # a fast-review trace: never a note
        _row(15, 900.0, "note", "another lesson", 15, lesson_date="2026-10-08"),
    ]
    got = NC.notes(DATE, rows)
    assert [(n["t"], n["raw"]) for n in got] == [(100.0, "tomi should be marked incorrect"), (200.0, "second wording"),
                                                 (300.0, "amal not aman"), (400.0, "we arent counting names"),
                                                 (500.0, "a word is missing"), (600.0, "she said both are fine")]
    assert got[0]["kinds"] == ["add", "note"] and len(got[0]["ids"]) == 3
    assert got[2]["kinds"] == ["text"] and got[2]["ids"] == ["r07", "r08"]
    assert NC.item_id(DATE, got[0]) != NC.item_id(DATE, got[1])


def test_am_30_the_10_09_list_is_every_distinct_note_in_the_mirror():
    found = NC.notes(DATE)
    assert DATA["date"] == DATE and DATA["kind"] == "note_check" and DATA["prefix"] == "notecheck" and DATA["list"] == "note-check-" + DATE
    assert DATA["n"] == len(DATA["items"]) == len(found) >= 60
    assert [x["id"] for x in DATA["items"]] == [NC.item_id(DATE, n) for n in found]
    assert len({x["id"] for x in DATA["items"]}) == DATA["n"]
    assert [x["t"] for x in DATA["items"]] == sorted(x["t"] for x in DATA["items"])
    assert DATA["title"] == "Check the student's notes on Oct 9 (about %d min)" % DATA["mins"]
    assert DATA["mins"] == round(DATA["n"] * NC.SECS_EACH / 60)


def test_am_30_each_card_clip_line_context_and_his_quoted_note():
    for x in DATA["items"]:
        assert set(x) <= {"id", "date", "mmss", "t", "end", "clips", "line", "rows"}
        c = x["clips"][0]
        assert c["fallback"].startswith(DATE + "/audio/lesson.mp3#t=")
        assert c["src"].startswith(DATE + "/clips/") or c["src"] == c["fallback"]
        assert re.match(r"(The student|You) · (\d:)?\d\d:\d\d$", x["line"]["label"])
        *ctx, note = x["rows"]
        for r in ctx:
            assert re.match(r"(You|The student), just (before|after) · (\d:)?\d\d:\d\d$", r["label"]) and "ar" in r
        assert note["label"] == "The student's note" and note["text"].startswith("The student wrote: «") and note["text"].endswith("»")
    # his own words, the names as PG-33 has them on screen ('amals correction' -> "the tutor's correction")
    notes = [x["rows"][-1]["text"] for x in DATA["items"]]
    assert any("the tutor's correction" in n for n in notes)
    assert NC.screen_quote("amal not aman, Medi's line, amals fix") == "the tutor not aman, the student's line, the tutor's fix"
    # S1 / PG-44 / PG-48: Arabizi first, the Arabic small after, the English under
    assert sum(1 for x in DATA["items"] if x["line"].get("az")) >= 40
    assert sum(1 for x in DATA["items"] if x["line"].get("en")) >= 50


def test_am_30_her_four_plain_sentences_and_no_names():
    (q,) = DATA["questions"]
    assert [(o["v"], o["label"]) for o in q["options"]] == [
        ("right", "The student is right"), ("partly", "The student is partly right"),
        ("wrong", "The student is wrong"), ("not_sure", "Not sure")]
    box = {o["v"]: o.get("box") for o in q["options"]}
    assert box["partly"] == "What is right?" and box["wrong"] == "Why? (optional)" and not box["right"] and not box["not_sure"]
    visible = [DATA["title"], DATA["intro"], DATA["what"], q["ask"]] + [o["label"] for o in q["options"]] \
        + [r.get("label", "") + " " + r.get("text", "") for x in DATA["items"] for r in x["rows"]] + [x["line"]["label"] for x in DATA["items"]]
    for s in visible:
        assert not re.search(r"\bMedi\b|\bAmal\b|\bslips?\b", s), s                 # PG-33, AM-24


def test_am_30_one_row_on_her_to_do_with_her_review_token():
    T = json.loads((DOCS / "data" / "tutor.json").read_text(encoding="utf-8"))
    row = next(x for x in T["open"] if x["id"] == "check-note-check-" + DATE)
    assert row["kind"] == "check" and row["list"] == "note-check-" + DATE and row["total"] == DATA["n"] and row["unit"] == "notes"
    assert row["title"] == DATA["title"] and row["lesson_date"] == DATE
    rv = next(x for x in T["open"] if x["kind"] == "review")
    assert row["token"] == rv["token"]
    src = (ROOT / "scripts" / "build_tutor_data.py").read_text(encoding="utf-8")
    assert "build_tutor_note_check.build_all()" in src and "NOTE_CHECKS" in src


def _her(word_key, answer, i, kind="note_check"):
    return {"id": i, "kind": kind, "word_key": word_key, "payload": {"answer": answer} if answer else {}, "created_at": "2026-10-12T00:00:%02d" % i}


def test_am_30_her_answers_latest_wins_undo_reopens():
    rows = [_her("notecheck:a", "right", 1), _her("notecheck:a", "partly", 2), _her("notecheck:b", "wrong", 3),
            _her("notecheck:b", None, 4, kind="undo"), _her("notecheck:c", "not_sure", 5), _her("notecheck:d", "bogus", 6)]
    assert NC.her_answers(rows) == {"notecheck:a": "partly", "notecheck:c": "not_sure"}


def _tmp_repo(tmp_path, items):
    repo = tmp_path / "repo"
    (repo / "docs" / "data").mkdir(parents=True)
    (repo / "data" / "lesson-work" / "review-grades").mkdir(parents=True)
    (repo / "docs" / "data" / ("amal-check-note-check-%s.json" % DATE)).write_text(
        json.dumps({"date": DATE, "prefix": "notecheck", "items": [{"id": i} for i in items]}), encoding="utf-8")
    return repo


def test_am_30_the_lesson_is_held_while_a_note_is_unanswered(tmp_path):
    import review_grades as RG
    repo = _tmp_repo(tmp_path, ["a", "b"])
    one = [_her("notecheck:a", "right", 1)]
    assert NC.status(DATE, str(repo), one) == {"total": 2, "answered": 1, "waiting": True}
    assert NC.waiting(DATE, str(repo), one)
    both = one + [_her("notecheck:b", "not_sure", 2)]
    assert not NC.waiting(DATE, str(repo), both)
    assert NC.waiting(DATE, str(repo), both + [_her("notecheck:b", None, 3, kind="undo")])          # an undo reopens it
    assert NC.status("2026-10-08", str(repo), []) is None                             # no note card: nothing held
    # the grade book: the row says why, nothing is frozen or graded
    out = RG.build(str(repo), corrections=[], reviews=[{"date": DATE, "full": True, "exam": True}], note_rows=one)
    row = out["lessons"][0]
    assert row["status"] == "%s (1 of 2 answered)" % NC.WAITING and row["waiting_for_tutor"] and "before" not in row
    assert row["notes_check"] == {"total": 2, "answered": 1}
    assert not os.path.exists(os.path.join(str(repo), "data", "lesson-work", "review-grades", DATE + ".json"))
    assert NC.WAITING == RG.WAITING == "waiting for the tutor to check the student's notes"


def test_am_30_freeze_refuses_while_held(monkeypatch):
    import review_grades as RG
    monkeypatch.setattr(RG, "notes_hold", lambda date, repo=None, rows=None: {"total": 80, "answered": 3, "waiting": True})
    with pytest.raises(SystemExit) as e:
        RG.freeze(DATE, log=lambda *a: None)
    assert "not frozen (AM-30)" in str(e.value)


def test_am_30_the_real_10_09_grade_book_row_waits():
    G = json.loads((DOCS / "data" / "review-grades.json").read_text(encoding="utf-8"))
    row = next(r for r in G["lessons"] if r["date"] == DATE)
    st = NC.status(DATE)
    if st and st["waiting"]:
        assert row["status"].startswith(NC.WAITING) and "before" not in row
        assert not (ROOT / "data" / "lesson-work" / "review-grades" / (DATE + ".json")).exists()


def test_am_30_nothing_clears_his_notes():
    # the only code that writes his table appends (correction_parse: parsed rows + a done marker, never an undo); no script
    # or page deletes or patches a row of it, and the note list reads only
    for p in list((ROOT / "scripts").glob("*.py")) + list((DOCS / "js").rglob("*.js")):
        src = p.read_text(encoding="utf-8", errors="replace")
        for ln in src.splitlines():
            if "transcript_corrections" in ln:
                assert not re.search(r"\b(DELETE|PATCH)\b", ln), (p.name, ln)
    cp = (ROOT / "scripts" / "correction_parse.py").read_text(encoding="utf-8")
    assert '"kind": "undo"' not in cp and "'kind': 'undo'" not in cp
    nc = (ROOT / "scripts" / "build_tutor_note_check.py").read_text(encoding="utf-8")
    assert "db.rest(" not in nc and "transcript_corrections" not in nc.split('"""', 2)[2]


def test_am_30_refresh_pulls_her_answers_before_the_grade_book():
    import amal_trigger as T
    names = [n for n, _ in T.STEPS]
    assert names.index("build_tutor_data") < names.index("tutor_note_check_pull") < names.index("review_grades")
    hourly = (ROOT / "scripts" / "hourly_lessons.py").read_text(encoding="utf-8")
    assert hourly.index("'build_tutor_note_check.py pull'") < hourly.index("run_step('review_grades.py'")


def test_am_30_pull_writes_only_when_rows_change(tmp_path):
    p = str(tmp_path / "answers.json")
    rows = [_her("notecheck:a", "right", 1)]
    NC.pull(p, fetch=lambda: rows, log=lambda *a: None)
    first = Path(p).read_text(encoding="utf-8")
    NC.pull(p, fetch=lambda: rows, log=lambda *a: None)
    assert Path(p).read_text(encoding="utf-8") == first
    assert json.loads(first)["rows"] == rows
