# -*- coding: utf-8 -*-
"""scripts/amal_new_words.py (Medi 2026-10-02): words Amal used that are not on her Doc -> Tutor hub item with
add / later / forget. Candidates exclude Doc words (any common form), names, function words and English; only a 'new'
verdict reaches Amal; her taps set the status; 'add' items are pending Doc additions; nothing edits the Doc."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import amal_new_words as N

WORDS = {"items": [
    {"key": "shanta", "arabizi": "Shanta", "arabic": "شنطة", "english": "bag", "plural": "shanaat / شنط", "aliases": []},
    {"key": "a7mar", "arabizi": "A7mar", "arabic": "أحمر", "english": "red", "plural": "", "aliases": ["7amra"]},
    {"key": "shu8ul", "arabizi": "Shu8ul", "arabic": "شغل", "english": "work", "plural": "", "aliases": []},
]}
LESSON = {"turns": [
    {"t": 10.0, "who": "Medi", "text": "مشجع"},                                   # Medi's words are never candidates
    {"t": 20.0, "who": "Amal", "text": "وشنطتك الحمرا وين؟ هاي شنطة"},              # on the Doc (prefix/suffix/plural forms)
    {"t": 30.0, "who": "Amal", "text": "انا متحمسة كتير"},                           # متحمسة, كتير: not on this Doc
    {"t": 40.0, "who": "chat", "typed_by": "Amal", "text": "mitshajje3 = motivated"},  # typed Arabizi + English gloss
    {"t": 50.0, "who": "chat", "typed_by": "Amal", "text": "shantet shu8li el-7amra"},  # all on the Doc
]}


def test_candidates_exclude_doc_forms_function_words_english_and_medi():
    idx = N.doc_index(WORDS)
    C = N.candidates("2026-10-01", lesson=LESSON, index=idx, spans=[])
    keys = {c["key"] for c in C["candidates"]}
    assert "مشجع" not in keys                         # Medi said it
    assert not keys & {"وشنطتك", "شنطه", "shantet"}   # Doc forms (prefix + suffix, ta marbuta, Arabizi ending)
    assert "انا" not in keys                          # function word
    assert "متحمسه" in keys and "mitshajje3" in keys
    assert C["candidates"][0]["lines"][0]["who"] == "Amal"
    assert C["excluded_by_string_check"]["on_doc"] >= 3


def test_names_are_excluded():
    idx = N.doc_index(WORDS)
    C = N.candidates("2026-10-01", lesson={"turns": [{"t": 1.0, "who": "Amal", "text": "رحت على ماليه"}]}, index=idx, spans=[(0, 9, 13)])
    assert [c["key"] for c in C["candidates"]] == ["رحت"]
    assert C["excluded_by_string_check"]["name"] == 1


VERDICTS = [
    {"date": "2026-10-01", "key": "mitshajje3", "verdict": "new", "arabic": None, "arabizi": "mitshajje3", "english": "motivated", "t": 40.0, "line": "mitshajje3 = motivated", "typed": True},
    {"date": "2026-10-01", "key": "متحمسه", "verdict": "new", "arabic": "متحمسة", "arabizi": None, "english": "excited", "t": 30.0},
    {"date": "2026-10-01", "key": "متحمس", "verdict": "new", "dup_of": "متحمسه", "t": 31.0},
    {"date": "2026-10-01", "key": "كتير", "verdict": "function", "t": 30.0},
    {"date": "2026-10-01", "key": "اوكي", "verdict": "english", "t": 30.0},
    {"date": "2026-09-30", "key": "old", "verdict": "new", "t": 5.0},           # before the start date: never asked
]


def test_only_new_words_reach_amal_and_taps_set_status():
    a = N.build(VERDICTS, taps={}, today="x")
    assert [i["key"] for i in a["items"]] == ["متحمسه", "mitshajje3"]
    assert all(i["status"] == "open" for i in a["items"])
    assert a["excluded"]["2026-10-01"]["function"] == 1 and a["excluded"]["2026-10-01"]["english"] == 1
    assert a["excluded"]["2026-10-01"]["duplicate"] == 1
    it = a["items"][1]
    assert it["arabizi"] == "mitshajje3" and it["clip"]["src"] == "lessons/2026-10-01/audio/lesson.mp3" and it["clip"]["start"] == 38.0
    taps = {it["id"]: ("newword_add", "2026-10-02T10:00:00Z"), a["items"][0]["id"]: ("newword_forget", "t")}
    b = N.build(VERDICTS, taps=taps, today="x")
    assert {i["key"]: i["status"] for i in b["items"]} == {"mitshajje3": "add", "متحمسه": "forget"}
    assert [p["arabizi"] for p in b["pending_doc_additions"]] == ["mitshajje3"]
    assert b["counts"]["open"] == 0


def test_offline_build_keeps_the_last_read_statuses():
    first = N.build(VERDICTS, taps={N.item_id("2026-10-01", "mitshajje3"): ("newword_later", "t")}, today="x")
    again = N.build(VERDICTS, taps=None, previous=first, today="y")
    assert {i["key"]: i["status"] for i in again["items"]} == {"mitshajje3": "later", "متحمسه": "open"}


def test_ids_are_stable_and_never_touch_the_doc():
    assert N.item_id("2026-10-01", "x") == N.item_id("2026-10-01", "x") and N.item_id("2026-10-01", "x").startswith("newword:")
    src = open(os.path.join(REPO, "scripts", "amal_new_words.py"), encoding="utf-8").read()
    assert "open(WORDS, \"w\"" not in src and "open(WORDS, 'w'" not in src


def test_step_runs_for_every_lesson():
    import amal_trigger as T, review_lesson as R
    assert "amal_new_words" in T.AUDIT_CHAIN and T.AUDIT_CHAIN.index("amal_new_words") < T.AUDIT_CHAIN.index("build_tutor_data")
    assert "amal_new_words" in [s for s, _ in T.STEPS]
    assert "amal_new_words.py" in open(os.path.join(REPO, "scripts", "review_lesson.py"), encoding="utf-8").read()
    assert "{date}" not in R.new_words_prompt("2026-10-01") and "2026-10-01" in R.new_words_prompt("2026-10-01")


