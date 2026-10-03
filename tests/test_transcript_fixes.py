# -*- coding: utf-8 -*-
"""TR-18 heard-word overlay (raw never edited) and GR-25 (Amal's whole reply 'el' = an A1 el- slip, not vocab)."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import transcript_fixes as TFX  # noqa: E402
import full_audit_build as FAB  # noqa: E402

ROW = {"date": "2026-10-02", "t": 454.02, "who": "Medi", "engine_wrote": "العشاء", "heard": "عشرة", "rule": "TR-18"}


def test_tr_18_overlay_shows_the_heard_word_and_keeps_the_engine_text():
    turns = [{"t": 454.02, "who": "Medi", "text": "آآآ على العشاء."}, {"t": 456.65, "who": "Amal", "text": "الـ."}]
    out = TFX.apply("2026-10-02", turns, [ROW])
    assert out[0]["text"] == "آآآ على عشرة." and out[0]["engine"] == "آآآ على العشاء."
    assert turns[0]["text"] == "آآآ على العشاء."          # the input (raw) is not touched
    assert "engine" not in out[1]
    assert TFX.unmatched("2026-10-02", out, [ROW]) == []


def test_tr_18_a_fix_that_matches_no_line_is_reported():
    assert TFX.unmatched("2026-10-02", [{"t": 10, "who": "Medi", "text": "x"}], [ROW]) == [ROW]


def test_gr_25_her_whole_reply_el_is_an_a1_slip_not_a_wrong_word():
    rows = [{"date": "2026-10-02", "t": "07:34", "amal_said": "الـ.", "kind": "vocab-B", "wrong": "العشاء", "right": "العشرة (el-3ashara)", "signal": "none"},
            {"date": "2026-10-02", "t": "15:40", "amal_said": "عشاء. What's عشاء؟", "kind": "vocab-A", "wrong": "Asha", "right": "3ashara"}]
    assert FAB.apply_el_prompt(rows) == 1
    assert rows[0]["kind"] == "grammar" and rows[0]["bucket"] == "A1" and rows[0]["signal"] == "prompt-then-fix"
    assert rows[0]["wrong"] == "عشرة" and rows[0]["right"] == "العشرة" and rows[0]["rule"] == "GR-25"
    assert rows[1]["kind"] == "vocab-A"                     # she named the wrong word: a real vocab slip stays
