# -*- coding: utf-8 -*-
"""PR-15 Medi's corrections (undo, classify), GR-26 (a demonstrative slip is A10 grammar), WS-28 (a word taught in an
earlier lesson is scored). No live writes: fixtures only."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import medi_corrections as MC  # noqa: E402
import full_audit_build as FAB  # noqa: E402

C = {"id": "c1", "lesson_date": "2026-10-02", "turn_t": 502.9, "turn_who": "Medi", "kind": "classify",
     "target": {"k": "vocab", "wrong": "عادي الصباح"}, "payload": {"to": "grammar", "rule": "A10", "wrong": "هادي الصباح", "turn_end": 504},
     "note": "this should be a grammar error", "ts": "2026-10-02T23:40:00-07:00"}


def _row():
    return {"date": "2026-10-02", "t": "08:23", "kind": "vocab-A", "wrong": "عادي الصباح", "right": "الصبح", "signal": "explicit-no"}


def test_pr_15_classify_refiles_the_reader_row_as_grammar_with_his_words():
    rows = [_row()]
    rep = MC.apply_rows(rows, [C])
    assert rep["applied"] == ["c1"] and rows[0]["kind"] == "grammar" and rows[0]["bucket"] == "A10"
    assert rows[0]["wrong"] == "هادي الصباح" and "grammar error" in rows[0]["why"]


def test_pr_15_undo_takes_a_correction_back_and_undoing_the_undo_restores_it():
    u1 = {"id": "u1", "kind": "undo", "undoes": "c1", "ts": "2026-10-02T23:41:00-07:00", "lesson_date": "2026-10-02", "turn_t": 0, "turn_who": "Medi"}
    assert MC.effective([C, u1]) == []
    rows = [_row()]
    MC.apply_rows(rows, [C, u1])
    assert rows[0]["kind"] == "vocab-A"
    u2 = dict(u1, id="u2", undoes="u1", ts="2026-10-02T23:42:00-07:00")
    assert [r["id"] for r in MC.effective([C, u1, u2])] == ["c1"]


def test_pr_15_amal_ruled_row_is_never_changed_by_medi():
    rows = [dict(_row(), signal="amal-ruling")]
    rep = MC.apply_rows(rows, [dict(C, kind="not-slip")])
    assert rows[0]["kind"] == "vocab-A" and rep["waiting_for_amal"]


def test_gr_26_a_demonstrative_amal_takes_out_is_an_a10_grammar_slip():
    rows = [{"kind": "vocab-A", "wrong": "هادي الصباح", "right": "الصبح / بالصباح"},
            {"kind": "vocab-A", "wrong": "هادي الطاولة", "right": "الكرسي"}]
    assert FAB.apply_demonstrative(rows) == 1
    assert rows[0]["kind"] == "grammar" and rows[0]["bucket"] == "A10" and rows[1]["kind"] == "vocab-A"


def test_ws_28_a_word_taught_in_an_earlier_lesson_is_scored():
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-02.json"), encoding="utf-8"))
    hit = [e for e in d["vocab_errors"] if "متشجع" in str(e.get("fix") or e.get("arabic"))]
    # 2026-10-06: Amal has since added متشجع to her Doc, so the row is keyed by the Doc ("auto-word") and scored that way;
    # WS-28 (taught earlier) is the reason only while the word is not on the Doc yet. Either way it is scored.
    assert hit and hit[0]["on_sheet"] is True, hit
    if hit[0].get("keyed_by") == "taught-earlier":
        assert "WS-28" in hit[0]["sheet_reason"]
