# -*- coding: utf-8 -*-
"""GR-24: a self-fix needs his right word before hers by word time (10-02 07:02 سمعت -> صحيت)."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import self_fix_timing as SFT  # noqa: E402


def _case(his_word_t, her_word_t):
    # tracks on the lesson clock: Medi's track +0.2 s, Amal's +2.3 s (each recording has its own start offset)
    turns = [{"t": 421.64, "who": "Medi", "text": "أنا سمعت"}, {"t": 423.8, "who": "Medi", "text": "متأخر اليوم. صحيت. That's right."},
             {"t": 425.75, "who": "Amal", "text": "صحيت."}, {"t": 429.61, "who": "Amal", "text": "What's مت؟"}]
    W = {"Medi": [("انا", 421.42), ("سمعت", 421.7), ("متاخر", 423.6), ("اليوم", 425.7), ("صحيت", his_word_t - 0.2)],
         "Amal": [("صحيت", her_word_t - 2.3), ("what's", 427.3), ("مت", 427.66)]}
    row = {"t": "07:02", "wrong": "سمعت", "right": "صحيت"}
    off = SFT.offsets(turns, W)
    return SFT.check("2026-10-02", row, turns, W, off)


def test_gr_24_his_line_starts_first_but_her_word_came_first_is_not_a_self_fix():
    r = _case(his_word_t=427.42, her_word_t=425.75)
    assert r["verdict"] == "her-first", r


def test_gr_24_his_right_word_before_hers_is_a_self_fix():
    r = _case(his_word_t=424.0, her_word_t=425.75)
    assert r["verdict"] == "his-first", r


def test_gr_24_settle_puts_the_slip_back_on_the_real_lesson():
    import json
    p = os.path.join(SFT.WORK, "2026-10-02.settled.json")
    rows = json.load(open(p, encoding="utf-8"))["rows"]
    hit = [r for r in rows if r.get("rule") == "GR-24" and r.get("wrong") == "سمعت"]
    assert hit and hit[0]["right"] == "صحيت" and hit[0]["gr24"]["verdict"] == "her-first"
