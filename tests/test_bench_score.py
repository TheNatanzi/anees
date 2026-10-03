# -*- coding: utf-8 -*-
"""PR-18: the benchmark scorer on planted cases (hit / miss / hidden slip / false change / unstable / language switch)."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402

LATIN = {"ghayr": "غير", "lissa": "لسه"}


def conv(text):
    """A fixed stand-in for arabizi_reader (the scorer is pure: the reader is injected)."""
    return " ".join(LATIN.get(w.lower().strip(".,"), w) for w in (text or "").split())


def line(i, t, engine, truth, stay=True):
    return {"i": i, "who": "Medi", "t": t, "end": t + 2, "engine": engine, "truth": truth, "should_stay": stay, "corrected": not stay}


TRUTH = {
    "lines": [
        line(1, 10, "أنا صرت متأخر.", "أنا صحيت متأخر.", stay=False),      # engine misheard صحيت as صرت
        line(2, 20, "أنا سمعت متأخر", "أنا سمعت متأخر"),                    # his slip سمعت (Amal: صحيت), kept
        line(3, 30, "This suck.", "لسه.", stay=False),                      # English look-alikes for his لسه
        line(4, 40, "بدي أروح على البيت", "بدي أروح على البيت"),            # untouched: must stay
        line(5, 50, "Okay, so what is it?", "Okay, so what is it?"),        # untouched English
        line(6, 60, "qayr", "غير", stay=False),
    ],
    "moments": [
        {"id": "M0", "i": 1, "t": 10, "want": ["صحيت"], "gone": ["صرت"], "class": "wrong-arabic-word"},
        {"id": "M1", "i": 2, "t": 20, "want": ["سمعت"], "gone": [], "class": "kept-slip"},
        {"id": "M2", "i": 3, "t": 30, "want": ["لسه", "لسا"], "gone": ["suck"], "class": "short-repeat-english"},
        {"id": "M3", "i": 6, "t": 60, "want": ["غير"], "gone": ["qayr"], "class": "latin-arabic"},
    ],
    "slips": [{"i": 2, "t": 20, "kind": "vocab", "wrong": "سمعت", "right": "صحيت"}],
    "amal_all": [{"t": 41, "end": 43, "text": "ممتاز يا مهدي"}],
}


def run(**over):
    base = {"1": {"text": "أنا صحيت متأخر"}, "2": {"text": "أنا سمعت متأخر"}, "3": {"text": "لسّه"},
            "4": {"text": "بدّي أروح على البيت"}, "5": {"text": "Okay so what is it"}, "6": {"text": "غير"}}
    base.update({k.lstrip("L"): v for k, v in over.items()})
    return base


def test_normaliser_is_orthography_only():
    assert BC.tokens("أَنا صَحيتْ، مُتأخِّر!") == BC.tokens("انا صحيت متاخر")
    assert BC.tokens("لسه") == BC.tokens("لسة") == BC.tokens("لسا")
    assert BC.tokens("الثاني") == BC.tokens("التاني")
    assert BC.tokens("آآآ um على") == ["علي"]                       # fillers are pauses (TR-07)
    assert BC.tokens("صحيت") != BC.tokens("صرت")
    assert BC.tok_eq("10", BC.tokens("عشرة")[0]) and BC.tokens("عشر") != BC.tokens("عشرة")


def test_perfect_engine_hits_everything():
    s = BS.score(TRUTH, [run()], conv=conv)
    assert (s["hit"], s["moments"]) == (4, 4) and s["hidden_slips"] == 0 and s["false_changes"] == 0
    assert s["all_lines_pct"] == 100.0 and s["language_switch_lines"] == 0


def test_same_wrong_word_is_miss_engine_and_other_wrong_word_is_miss_other():
    s = BS.score(TRUTH, [run(L1={"text": "أنا صرت متأخر"}, L3={"text": "This sucks"})], conv=conv)
    v = {p["id"]: p["final"] for p in s["per_moment"]}
    assert v["M0"] == "miss-engine" and v["M2"] == "miss-other"
    s = BS.score(TRUTH, [run(L1={"text": "أنا صحيت صرت"})], conv=conv)        # the rejected word still there = not a hit
    assert s["per_moment"][0]["final"] == "miss-engine"


def test_hidden_slip_is_counted_apart():
    s = BS.score(TRUTH, [run(L2={"text": "أنا صحيت متأخر"})], conv=conv)      # the engine 'fixed' his سمعت to her صحيت
    assert s["per_moment"][1]["final"] == "hidden-slip" and s["hidden_slips"] == 1 and s["slips_judged"] == 1
    assert s["hit"] == 3


def test_false_change_on_should_stay_lines():
    s = BS.score(TRUTH, [run(L4={"text": "بدي أروح على المدرسة"})], conv=conv)
    assert s["false_changes"] == 1 and s["false_change_rows"][0]["extra"] == BC.tokens("المدرسة")
    s = BS.score(TRUTH, [run(L5={"text": "أوكي سو وات إز إت"})], conv=conv)   # his English written in Arabic letters
    assert s["false_changes"] == 1
    s = BS.score(TRUTH, [run(L5={"text": "okay. So, what is it??"})], conv=conv)
    assert s["false_changes"] == 0                                           # English wording is not a content change


def test_two_of_three_and_unstable():
    good, bad, other = run(), run(L1={"text": "أنا صرت متأخر"}), run(L1={"text": "أنا رحت متأخر"})
    assert BS.score(TRUTH, [good, good, bad], conv=conv)["per_moment"][0]["final"] == "hit"
    assert BS.score(TRUTH, [good, bad, bad], conv=conv)["per_moment"][0]["final"] == "miss-engine"
    s = BS.score(TRUTH, [good, bad, other], conv=conv)
    assert s["per_moment"][0]["final"] == "unstable" and s["hit"] == 3 and s["stable_pct"] == 75.0


def test_language_switch_error_and_unsent_lines():
    s = BS.score(TRUTH, [run(L6={"text": "他人"})], conv=conv)
    assert s["language_switch_lines"] == 1 and s["per_moment"][3]["final"] == "miss-other"
    s = BS.score(TRUTH, [run(L6={"text": "", "error": "429"})], conv=conv)
    assert s["per_moment"][3]["final"] == "error" and s["call_errors"] == 1
    r = run()
    del r["6"], r["4"]                                                        # not sent: the raw engine text stands
    s = BS.score(TRUTH, [r], conv=conv)
    assert s["per_moment"][3]["final"] == "miss-engine" and s["false_changes"] == 0 and s["lines_sent"] == 4


def test_latin_letters_read_as_arabic_but_the_rejected_spelling_is_not():
    assert BS.score(TRUTH, [run(L6={"text": "ghayr"})], conv=conv)["per_moment"][3]["final"] == "hit"
    assert BS.score(TRUTH, [run(L6={"text": "qayr"})], conv=conv)["per_moment"][3]["final"] == "miss-engine"
    assert BS.score(TRUTH, [run(L3={"text": "lissa"})], conv=conv)["per_moment"][2]["final"] == "hit"


def test_whole_file_mode_accepts_the_neighbour_line():
    r = run(L1={"text": "أنا"}, L2={"text": "صحيت متأخر أنا سمعت متأخر"})
    assert BS.score(TRUTH, [r], conv=conv)["per_moment"][0]["final"] == "miss-other"
    assert BS.score(TRUTH, [r], whole_file=True, conv=conv)["per_moment"][0]["final"] == "hit"


def test_alignment_puts_words_on_the_nearest_line():
    lines = [{"i": 1, "t": 10.0, "end": 12.0}, {"i": 2, "t": 12.5, "end": 14.0}]
    words = [{"text": "a", "start": 9.9, "end": 10.2}, {"text": "b", "start": 12.3, "end": 12.6}, {"text": "c", "start": 30, "end": 31}]
    assert BC.align_words(words, lines, offset=0.2) == {1: "a", 2: "b"}


def test_bleed_counts_amals_words_on_his_line():
    s = BS.score(TRUTH, [run(L4={"text": "بدي أروح على البيت ممتاز"})], conv=conv)
    assert s["bleed_words"] == 1


def test_whole_words_only_no_substring_credit():           # Codex audit 2026-10-03
    m = {"want": ["عشر", "عشرة"], "gone": []}
    assert not BS.has_want(m, "عشرين", conv=conv) and BS.has_want(m, "على عشرة", conv=conv)
    assert not BS.has_want({"want": ["عطلة"], "gone": []}, "تعطل", conv=conv)


def test_second_field_cannot_dodge_the_veto_or_earn_an_arabic_word():
    m = TRUTH["moments"][3]                                 # want غير, rejected spelling qayr
    assert BS.score_moment(m, {"text": "", "alt": "qayr"}, conv=conv) == "miss-engine"
    assert BS.score_moment(m, {"text": "", "alt": "ghayr"}, engine_line="qayr", conv=conv) == "miss-other"   # Arabic truth: the text field only
    assert BS.score_moment({"want": ["5otatet"], "gone": []}, {"text": "خططت", "alt": "5otatet"}, conv=conv) == "hit"


def test_all_lines_uses_every_run_and_counts_each_word_once():
    r1, r23 = run(), run(L4={"text": "غلط"})
    del r1["4"]
    s = BS.score(TRUTH, [r1, r23, r23], conv=conv)
    assert s["false_changes"] == 1 and s["lines_sent"] == 6
    assert BS.line_words("غير غير", "غير", conv)[:2] == (2, 1)
    assert BS.line_words("غير", "غير غير", conv) == (1, 1, BC.tokens("غير"))
