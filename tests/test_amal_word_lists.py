# -*- coding: utf-8 -*-
"""Amal's word lists (planted-mistake tests, run by the publish guard).

WS-15 (Medi 2026-09-23: "we dont need to add proper nouns like kabaab and ma2loobe and cake and countries"): dish names,
foods, brands, loan words and countries never go on Amal's 'not on sheet' list (build_amal_review.py) or the Tutor hub
'New words' task (amal_new_words.py, both the string candidates and a reader's 'new' verdict).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import loanwords as LW
import amal_new_words as N
import build_amal_review as BR


def _card(arabic, t, english="x"):
    return {"arabic": arabic, "on_sheet": False, "t": t, "mmss": "00:01", "english": english, "said": None, "fix": None}


def test_WS_15_dishes_foods_loanwords_countries_never_on_amals_not_on_sheet_list(tmp_path):
    # the 7 real moments the rule removes today + words that must stay
    planted = ["مقلوبة", "كعكة / بسكوتة", "cash (بدفع cash)", "أمريكا", "الزعفران", "ماكينة الرز", "الـ air conditioning تبعي", "كباب"]
    kept = ["دكتور عام", "بلد (one) / بلاد (countries)", "عرس", "تبعي", "متشجع"]
    lesson = {"vocab_errors": [_card(a, i) for i, a in enumerate(planted + kept)]
              + [{"arabic": "شنطة", "on_sheet": True, "t": 99}]}
    (tmp_path / "2026-10-01.json").write_text(json.dumps(lesson, ensure_ascii=False), encoding="utf-8")
    cards, skipped = BR.sheet_new_words(str(tmp_path), clips=False)
    assert sorted(c["arabic"] for c in cards) == sorted(kept)
    assert skipped == set(planted)


def test_WS_15_loan_tokens_arabic_and_arabizi():
    for w in ("كباب", "بالكباب", "المقلوبة", "kabaab", "ma2loobe", "cake", "pizza", "il-kabab", "بيتزا"):
        assert LW.loan_token(w), w
    for w in ("ممتاز", "لفة", "بجرب", "mitshajje3", "حلو", "عرس"):
        assert not LW.loan_token(w), w
    assert LW.loan_entry("في لبنان") and LW.loan_entry("Lebanon")      # countries (scripts/names.py)
    assert not LW.loan_entry("countries")                             # the word 'country' itself is vocabulary


def test_WS_15_new_words_task_drops_loanwords_at_both_stages():
    idx = N.doc_index({"items": [{"key": "shanta", "arabizi": "Shanta", "arabic": "شنطة", "english": "bag"}]})
    lesson = {"turns": [{"t": 1.0, "who": "Amal", "text": "بنطبخ مقلوبة وكباب"},
                        {"t": 2.0, "who": "chat", "typed_by": "Amal", "text": "ma2loobe pizza mitshajje3"}]}
    C = N.candidates("2026-10-01", lesson=lesson, index=idx, spans=[])
    keys = {c["key"] for c in C["candidates"]}
    assert not keys & {"مقلوبه", "وكباب", "ma2loobe", "pizza"}
    assert "mitshajje3" in keys and C["excluded_by_string_check"]["loanword"] >= 4
    # a reader that still says 'new' on a dish is overruled; nothing reaches Amal
    V = [{"date": "2026-10-01", "key": "مقلوبه", "verdict": "new", "arabic": "مقلوبة", "t": 1.0},
         {"date": "2026-10-01", "key": "kabaab", "verdict": "new", "arabizi": "kabaab", "t": 1.5},
         {"date": "2026-10-01", "key": "mitshajje3", "verdict": "new", "arabizi": "mitshajje3", "t": 2.0},
         {"date": "2026-10-01", "key": "pizza", "verdict": "loanword", "t": 2.0}]
    out = N.build(V, taps={}, today="x")
    assert [i["key"] for i in out["items"]] == ["mitshajje3"]
    assert out["excluded"]["2026-10-01"]["loanword"] == 3
