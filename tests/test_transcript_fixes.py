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


def test_az_10_every_transcript_line_has_arabizi():
    """AZ-10: no Arabic word on any transcript line without Arabizi."""
    import subprocess, shutil
    node = shutil.which("node") or "node"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([node, os.path.join(root, "scripts", "arabizi_gaps.cjs")], capture_output=True, text=True, encoding="utf-8")
    assert "transcript lines" in r.stdout and r.returncode == 0, r.stdout


def test_tr_19_a_short_english_reply_right_after_her_short_arabic_word_is_an_echo_candidate():
    """TR-19: her لسه؟ then his 'This suck.' within 5 s is listed for the echo check; a filler 'Okay.' is not."""
    import echo_candidates as EC
    T = [{"t": 568.95, "who": "Amal", "text": "لسه؟"}, {"t": 570.62, "who": "Medi", "text": "This suck."},
         {"t": 600.0, "who": "Amal", "text": "طيب."}, {"t": 601.0, "who": "Medi", "text": "Okay."}]
    C = EC.candidates(T)
    assert [c["engine_wrote"] for c in C] == ["This suck."]


def test_tr_20_a_verb_right_after_take_is_flagged():
    """TR-20: 'أخد أطلع' (take go-out) is flagged; 'أخد عطلة' (take a holiday) and an overlaid line are not."""
    import echo_candidates as EC
    T = [{"t": 584.14, "who": "Medi", "text": "أنا لازم أخد أطلع وسفر"}, {"t": 600, "who": "Medi", "text": "لازم آخد عطلة"},
         {"t": 610, "who": "Medi", "text": "أخد أطلع", "engine": "x"}]
    assert [c["engine_wrote"] for c in EC.take_verb(T)] == ["أطلع"]
