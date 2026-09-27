# -*- coding: utf-8 -*-
"""Sentence-length ladder (plan/SENTENCE-LADDER-SPEC-2026-09-27.md): the unit rule, look-back, 'aywa = unknown',
clitics staying inside their word, the mostly-English skip and the 80% / last-20 / 2-lesson ladder rule."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_sentence_ladder as B  # noqa: E402

META = {"duration_min": 20, "talk": {"window": [0.0, 1200.0]}, "start_local": "2026-09-27T14:00:00-07:00"}


def T(t, end, who, text):
    return {"t": t, "end": end, "who": who, "text": text}


def run(turns):
    doc = {"turns": turns, "vocab_errors": [], "grammar_errors": []}
    listen, speak, miss, _ = B.lesson_units("2026-09-27", META, B.bank(), [], doc, None)
    return listen, speak


# ---------------------------------------------------------------- counting Arabic words
def test_prefixes_and_clitics_stay_inside_their_word():
    assert B.count_words("بيتي بالبيت وبيتك")[0] == 3            # بيتي = 1, بالبيت = 1, وبيتك = 1
    assert B.count_words("و بيتي")[0] == 1                        # a lone و joins the next word
    assert B.count_words("حكيتلك إنو بحبها")[0] == 3               # verb + 2 endings is still one word
    assert B.count_words("إحنا، إحنا بيهمنا")[0] == 2               # a stutter repeat counts once
    assert B.count_words("شك-شكلو رخيص")[0] == 2                   # the broken-off first go is dropped
    ar, en, _ = B.count_words("الـ project")
    assert (ar, en) == (0, 1)                                      # الـ before an English word is not an Arabic word


def test_clitic_count_per_word():
    tags, tok, _ = B.sentence_tags(B.tokenize("بحكيلك"), "بحكيلك", B.bank())
    assert tags["cl_max"] >= 2                                     # b- + -lak
    tags, tok, _ = B.sentence_tags(B.tokenize("بيت"), "بيت", B.bank())
    assert tags["cl_max"] == 0


def test_mostly_english_is_skipped():
    ar, en, _ = B.count_words("What does بسيط mean?")
    assert (ar, en) == (1, 3) and B.mostly_english(ar, en)
    ar, en, _ = B.count_words("شو يعني for free؟")
    assert (ar, en) == (2, 2) and not B.mostly_english(ar, en)     # exactly half English is kept (threshold is > 50%)
    ls, _ = run([T(0, 2, "Amal", "What does بسيط mean in English?"), T(4, 5, "Medi", "Simple.")])
    assert ls == []


# ---------------------------------------------------------------- labels
def test_bare_aywa_is_unknown_not_understood():
    for r in ("aywa", "Mm-hmm.", "Okay.", "yes", "أيوه", "Yeah yeah."):
        assert B.is_bare(r), r
    assert not B.is_bare("اليوم بلبس بلوزة سودا")
    ls, _ = run([T(0, 2, "Amal", "بتحب القهوة الصبح؟"), T(4, 4.5, "Medi", "aywa.")])
    assert len(ls) == 1 and ls[0]["label"] == "unknown"
    ls, _ = run([T(0, 2, "Amal", "شو أكلت اليوم؟"), T(4, 6, "Medi", "اليوم أكلت رز ودجاج.")])
    assert ls[0]["label"] == "understood"


def test_unit_is_her_last_arabic_sentence_before_his_reply():
    ls, _ = run([T(0, 1, "Amal", "كيفك؟"), T(10, 12, "Amal", "شو أكلت اليوم؟"),
                 T(12.5, 14, "Amal", "What did you eat today?"), T(16, 18, "Medi", "أكلت رز.")])
    assert [u["text"] for u in ls] == ["شو أكلت اليوم؟"]           # the English sentence is skipped, كيفك got no reply
    assert ls[0]["n"] == 3 and ls[0]["reply"]["text"] == "أكلت رز."


def test_repeat_request_is_a_breakdown():
    ls, _ = run([T(0, 2, "Amal", "بتحب نحكي بس؟"), T(3, 3.5, "Medi", "Huh?")])
    assert ls[0]["label"] == "breakdown" and "repeat_request" in ls[0]["signals"]


def test_lookback_charges_the_earlier_sentence():
    ls, _ = run([T(0, 2.5, "Amal", "بدي أشتري بندورة كتير."), T(4, 6, "Amal", "وبعدين بروح عالبيت."),
                 T(8, 10, "Medi", "shu ya3ni بندورة?")])
    by = {u["text"]: u for u in ls}
    first, last = by["بدي أشتري بندورة كتير."], by["وبعدين بروح عالبيت."]
    assert first["label"] == "breakdown" and first["lookback"]["from"] == last["id"]
    assert "meaning_question" in first["signals"]
    assert last["label"] == "unknown" and last["lookback"]["to"] == first["id"]


def test_lookback_stays_on_the_last_sentence_when_the_word_is_there():
    ls, _ = run([T(0, 2.5, "Amal", "بدي أروح عالسوق."), T(4, 6, "Amal", "بدي أشتري بندورة."),
                 T(8, 10, "Medi", "shu ya3ni بندورة?")])
    assert [u["text"] for u in ls if u["label"] == "breakdown"] == ["بدي أشتري بندورة."]


# ---------------------------------------------------------------- the ladder rule
def units(n, ok, dates, label_ok="understood", label_bad="breakdown"):
    out = []
    for i in range(sum(c for _, c in dates)):
        pass
    k = 0
    for d, c in dates:
        for j in range(c):
            out.append({"n": n, "date": d, "t": float(j), "scored": True, "label": label_ok if k < ok else label_bad})
            k += 1
    return out


def rung(lad, n):
    return next(r for r in lad["rungs"] if r["len"] == n)


def test_ladder_80pct_of_last_20_over_2_lessons():
    good = units(3, 16, [("2026-09-01", 10), ("2026-09-02", 10)])
    assert rung(B.ladder(good, "understood", "breakdown"), 3)["status"] == "good"
    short = units(3, 15, [("2026-09-01", 10), ("2026-09-02", 10)])
    assert rung(B.ladder(short, "understood", "breakdown"), 3)["status"] == "not yet"
    one = units(3, 20, [("2026-09-02", 25)])                      # one lesson: at most 10 of the 20 from it
    r = rung(B.ladder(one, "understood", "breakdown"), 3)
    assert r["n_last"] == 10 and r["status"] == "not enough data"
    few = units(3, 12, [("2026-09-01", 6), ("2026-09-02", 6)])
    assert rung(B.ladder(few, "understood", "breakdown"), 3)["status"] == "not enough data"


def test_ladder_takes_the_last_20_only():
    old_bad = units(4, 0, [("2026-08-01", 10), ("2026-08-02", 10)])
    new_good = units(4, 20, [("2026-09-01", 10), ("2026-09-02", 10)])
    assert rung(B.ladder(old_bad + new_good, "understood", "breakdown"), 4)["pct"] == 100.0


def test_current_n_and_target():
    two = [("2026-09-01", 10), ("2026-09-02", 10)]
    u = units(1, 20, two) + units(2, 18, two) + units(3, 10, two) + units(4, 20, two)
    lad = B.ladder(u, "understood", "breakdown")
    assert (lad["N"], lad["target"]) == (2, 3)                    # a failed length 3 stops the climb even if 4 is good
    u = units(1, 20, two) + units(2, 5, [("2026-09-01", 3), ("2026-09-02", 3)]) + units(3, 17, two)
    lad = B.ladder(u, "understood", "breakdown")
    assert (lad["N"], lad["target"]) == (3, 4)                    # too little data at 2 does not block


def test_speaking_ladder_uses_success_and_corrected():
    two = [("2026-09-01", 10), ("2026-09-02", 10)]
    u = units(2, 17, two, "success", "corrected")
    lad = B.ladder(u, "success", "corrected")
    assert lad["N"] == 2 and rung(lad, 2)["pct"] == 85.0
