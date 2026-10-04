# -*- coding: utf-8 -*-
"""The side columns of scoreboard A (scripts/bench_side.py, PR-18): planted cases, no network, no files."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402
import bench_side as SD  # noqa: E402

SAME = lambda t: t  # noqa: E731  (no Arabizi reader in the tests)
M_MONEY = {"id": "M0", "i": 1, "t": 10.0, "want": ["المصاري"], "gone": ["المال"], "class": "wrong-arabic-word"}
M_BIDDO = {"id": "M1", "i": 2, "t": 20.0, "want": ["هو بدو"], "gone": ["Huwa bido"], "class": "latin-arabic"}
M_FRAG = {"id": "M2", "i": 3, "t": 1.0, "want": ["تنتين و ro--"], "gone": ["tinte nu ro"], "class": "number-time"}


def side(m, text, cut=False, sp=False):
    return SD.has_want_side(m, text, cut, sp, SAME)


def test_prefix_counts_only_with_a_break_mark():
    for text in ("Okay, but المصـ-- okay", "but المص-- okay", "but المص- okay", "but المصـ okay", "but المص… okay", "but المص... okay"):
        assert side(M_MONEY, text, cut=True), text
        assert not side(M_MONEY, text), text                       # strict is unchanged
        assert not side(M_MONEY, text, sp=True), text              # the ending column never accepts a cut-off
    assert not side(M_MONEY, "but المص okay", cut=True)            # no break mark: just another word
    assert not side(M_MONEY, "but المص. okay", cut=True)           # a full stop is not a break mark
    assert not side(M_MONEY, "but المال-- okay", cut=True)         # not a prefix (and the rejected word)
    assert not side(M_MONEY, "but المصـ-- المال", cut=True)        # the rejected word still vetoes
    assert not side(M_MONEY, "but مصـ-- okay", cut=True)           # the article is never relaxed
    assert not side(M_MONEY, "but الم-- okay", cut=True)           # ال + one letter says nothing about the word
    assert not side(M_MONEY, "but ال-- okay", cut=True)
    assert not side(M_MONEY, "but المصاريف-- okay", cut=True)      # longer than the word is not its prefix
    assert side(M_MONEY, "but المصاري okay") and side(M_MONEY, "but المصاري okay", cut=True, sp=True)


def test_ending_is_only_final_h_or_w_of_the_same_word():
    assert side(M_BIDDO, "I can say هو بده", sp=True)
    assert not side(M_BIDDO, "I can say هو بده")                   # strict: a miss, as bench_score says
    assert not side(M_BIDDO, "I can say هو بده", cut=True)
    assert not side(M_BIDDO, "I can say هو بدي", sp=True)          # any other letter: no
    assert not side(M_BIDDO, "I can say هو بدا", sp=True)          # a real ا is not the enclitic ه
    assert not side(M_BIDDO, "I can say هو بدة", sp=True)          # nor is ة
    assert not side(M_BIDDO, "I can say هو البده", sp=True)        # the article is never relaxed
    assert not side(M_BIDDO, "I can say هو بدهم", sp=True)         # only at the END of the word
    assert not side(M_BIDDO, "I can say هه بدو", sp=True)          # two-letter words are left alone (هو is not هه)
    m = {"id": "M", "i": 1, "want": ["بده"], "gone": []}
    assert side(m, "هو بدو", sp=True) and not side(m, "هو بدو")    # the equivalence runs both ways
    m = {"id": "M", "i": 1, "want": ["بدهم"], "gone": []}
    assert not side(m, "بدوم", sp=True)                            # never inside a word


def test_wanted_fragment_must_stay_a_fragment():
    assert not BS.has_want(M_FRAG, "تنتين و رو--", "", SAME)        # the scorer trap: a faithful Arabic cut-off is a strict miss
    assert side(M_FRAG, "تنتين و رو--", cut=True)                   # ... the cut-off column takes it
    assert side(M_FRAG, "تنتين و ro--", cut=True) and side(M_FRAG, "تنتين و ro--")
    assert not side(M_FRAG, "تنتين وربع", cut=True)                 # finished into a word: no
    assert not side(M_FRAG, "تنتين و ربع", cut=True)
    assert not side(M_FRAG, "تنتين و ربـ--", cut=True)              # a different, longer fragment: no
    assert not side(M_FRAG, "تنتين و رو", cut=True)                 # no break mark: no
    assert not side(M_FRAG, "تلاتة و رو--", cut=True)               # the Arabic words must be there


def test_strict_is_bench_scores_own_answer():
    texts = ["Okay, but المصـ-- okay", "but المصاري", "هو بده", "هو بدو", "تنتين و رو--", "تنتين و ro--", "تنتين وربع", "", "um آآآ", "but المال و المصاري"]
    for m in (M_MONEY, M_BIDDO, M_FRAG):
        for t in texts:
            assert side(m, t) == BS.has_want(m, t, "", SAME), (m["id"], t)
    for t in texts + ["تنتين و تلت", "و", "قال و ـ راح"]:
        assert [p["tok"] for p in SD.glued(SD.pieces(t))] == BC.tokens(t), t


def _truth():
    lines = [{"i": 1, "t": 10.0, "end": 12.0, "engine": "but المال okay", "truth": "but المصاري-- okay", "should_stay": False},
             {"i": 2, "t": 20.0, "end": 22.0, "engine": "Huwa bido", "truth": "هو بدو", "should_stay": False}]
    return {"lines": lines, "moments": [M_MONEY, M_BIDDO], "slips": [], "amal_all": []}


def test_side_keeps_the_two_of_three_rule_and_the_strict_count():
    truth = _truth()
    runs = [{"1": {"text": "but المصـ-- okay"}, "2": {"text": "هو بده"}},
            {"1": {"text": "but المصـ-- okay"}, "2": {"text": "هو بدي"}},
            {"1": {"text": "but المال okay"}, "2": {"text": "هو بدو"}}]
    r = SD.side(truth, runs, SAME)
    assert r["strict"] == BS.score(truth, runs, conv=SAME)["hit"] == 0
    assert (r["cutoff_ok"], r["cutoff_ok_adds"]) == (1, ["M0"])           # 2 of 3 runs wrote the cut-off
    assert (r["spelling_ok"], r["spelling_ok_adds"]) == (1, ["M1"])       # 1 strict hit + 1 ending = 2 of 3
    assert r["both"] == 2 and r["at_least_once"] == 1
    one = [runs[0], runs[2], runs[2]]                                     # only 1 of 3 runs wrote the cut-off: still a miss
    assert SD.side(truth, one, SAME)["cutoff_ok_adds"] == []
    assert SD.strict_agrees(truth, runs, SAME) == []


def test_a_hidden_slip_is_never_made_a_hit():
    truth = _truth()
    truth["moments"] = [dict(M_BIDDO, **{"class": "kept-slip"})]
    truth["slips"] = [{"i": 2, "t": 20.0, "kind": "grammar", "wrong": "بدو", "right": "بده"}]
    runs = [{"2": {"text": "هو بده"}}] * 3                                # the engine wrote Amal's form: bench_score says hidden-slip
    assert BS.score(truth, runs, conv=SAME)["per_moment"][0]["final"] == "hidden-slip"
    assert SD.side(truth, runs, SAME)["spelling_ok"] == 0


def test_trap_note_reports_without_patching():
    truth = {"lines": [{"i": 3, "t": 1.0, "end": 2.0, "engine": "tinte nu ro", "truth": "تنتين و ro--.", "should_stay": False}],
             "moments": [M_FRAG], "slips": [], "amal_all": []}
    n = SD.trap_note(truth, {"e": [{"3": {"text": "تنتين وربع"}}, {"3": {"text": "تنتين و رو--"}}]}, SAME)
    assert len(n) == 1 and n[0]["moment"] == "M2"
    assert n[0]["strict_scores_it"] is False and n[0]["cutoff_column_scores_it"] is True and n[0]["strict_scores_finished"] is True
    assert (n[0]["runs_that_kept_the_fragment"], n[0]["runs_looked_at"]) == (1, 2)
