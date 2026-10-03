# -*- coding: utf-8 -*-
"""AM-19 (Medi 2026-10-02: "we have a process already for words like metshaje3. We need to ask amal if she wants to add
them in the tutor hub and then make sure that she adds them."): every word the lesson-type reader found Amal taught (all
lessons) that is not in her Doc goes onto her Tutor hub New words card (one card per word, by meaning, citing the lesson
and time); a word in her Doc only shows as taught on the lesson page; the lesson page shows every taught word with its
status; a promised word not in the Doc after 7 days is marked "still waiting". Pure builds, no live reads or writes."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import amal_new_words as N

DOC = {"items": [
    {"key": "safar", "arabizi": "Safar", "arabic": "السفر", "english": "travel", "plural": "", "aliases": []},
    {"key": "ana_bakser", "arabizi": "Ana bakser", "arabic": "أنا بكسر", "english": "I break", "plural": "", "aliases": []},
]}
E = lambda d, ar, lat=None, en=None, t=None, kind="word": {"date": d, "kind": kind, "latin": lat, "arabic": ar, "english": en,
                                                           "t": t, "review": False, "by": "reader"}
ENTRIES = [
    E("2026-09-16", "السفر", "el-safar", "travel", 1262.0),                 # in her Doc -> lesson page only
    E("2026-09-16", "بالتوفيق", None, "good luck", 420.0),                  # new -> a card
    E("2026-09-26", "دماغ", "el-dmaa8", "brain", 1589.0),                   # new -> a card
    E("2026-09-28", "دماغ", None, "brain", 600.0),                          # same word again -> the same card, cited
    E("2026-09-26", "كيك", "cake", "cake", 700.0),                          # a 'new' verdict on a loan word: never asked
    E("2026-09-16", "بكمّل / نكمّل", None, "I continue", 1536.0),            # already on her card from 10-02
    E("2026-09-17", "غبرة", None, "dust", 748.0),                           # no verdict yet -> unjudged, not asked
    E("2026-09-10", "أنا بكسر / أنا بنكسر", "Ana bakser / Ana bankeser", None, None, "verb"),   # hand verb pair in the Doc
]
TV = [
    {"date": "2026-09-16", "arabic": "السفر", "verdict": "on_doc", "reason": "on the Doc"},
    {"date": "2026-09-16", "arabic": "بالتوفيق", "verdict": "new", "reason": "not on the Doc"},
    {"date": "2026-09-26", "arabic": "دماغ", "verdict": "new", "reason": "not on the Doc"},
    {"date": "2026-09-28", "arabic": "دماغ", "verdict": "new", "reason": "not on the Doc"},
    {"date": "2026-09-26", "arabic": "كيك", "verdict": "new", "reason": "x"},
    {"date": "2026-09-16", "arabic": "بكمّل / نكمّل", "verdict": "on_card", "card": {"date": "2026-10-02", "key": "كمل"}, "reason": "on her card"},
]
READER_NEW = [{"date": "2026-10-02", "key": "كمل", "verdict": "new", "arabic": "كمّل", "arabizi": None, "english": "go on", "t": 508.7}]


def _build(taps=None, today="2026-10-02", doc=DOC, entries=ENTRIES):
    return N.build(READER_NEW, taps=taps if taps is not None else {}, today=today, marks={"marks": []}, doc=doc,
                   taught=entries, taught_verdicts=TV, turns_for=lambda d: [])


def by_ar(out, d):
    return {r["arabic"]: r for r in out["taught"][d]}


def test_AM_19_taught_words_not_in_her_doc_become_one_card_each_citing_lesson_and_time():
    out = _build()
    cards = [i for i in out["items"] if i.get("source") == "taught"]
    assert sorted(i["arabic"] for i in cards) == ["بالتوفيق", "دماغ"]
    brain = next(i for i in cards if i["arabic"] == "دماغ")
    assert brain["date"] == "2026-09-26" and brain["mmss"] == "26:29" and brain["arabizi"] == "el-dmaa8"
    assert brain["clip"]["src"] == "lessons/2026-09-26/audio/lesson.mp3" and brain["status"] == "open"
    assert brain["also"] == [{"date": "2026-09-28", "mmss": "10:00"}]          # dedupe by meaning across lessons
    assert out["taught_counts"]["new_cards"] == 2 and out["taught_counts"]["loanword"] == 1   # WS-15
    assert not any(i["arabic"] == "كيك" for i in out["items"])


def test_AM_19_words_in_her_doc_only_show_as_taught_and_a_card_already_asking_is_not_repeated():
    out = _build()
    d16 = by_ar(out, "2026-09-16")
    assert d16["السفر"]["status"] == "in_doc" and d16["السفر"]["card"] is None
    assert d16["بكمّل / نكمّل"]["status"] == "waiting_amal" and d16["بكمّل / نكمّل"]["card"] == N.item_id("2026-10-02", "كمل")
    assert sum(1 for i in out["items"] if i["arabic"] in ("كمّل", "بكمّل / نكمّل")) == 1
    assert by_ar(out, "2026-09-10")["أنا بكسر / أنا بنكسر"]["status"] == "in_doc"          # hand verb pair, union
    assert by_ar(out, "2026-09-17")["غبرة"]["status"] == "unjudged"                     # no read: never asked
    assert not any(i["arabic"] == "غبرة" for i in out["items"])


def test_AM_19_lesson_page_status_follows_her_answer_and_the_doc():
    iid = N.item_id("2026-09-16", "taught:" + N._tkey("بالتوفيق"))
    brain = N.item_id("2026-09-26", "taught:" + N._tkey("دماغ"))
    out = _build(taps={iid: ("newword_add_new", "2026-10-02T10:00:00Z"), brain: ("newword_forget", "t")})
    assert by_ar(out, "2026-09-16")["بالتوفيق"]["status"] == "promised"
    assert by_ar(out, "2026-09-26")["دماغ"]["status"] == "forgotten" and by_ar(out, "2026-09-28")["دماغ"]["status"] == "forgotten"
    assert any(p["id"] == iid and p["state"] == "waiting" for p in out["promised"])
    doc = {"items": DOC["items"] + [{"key": "bil", "arabizi": "Bil-tawfee2", "arabic": "بالتوفيق", "english": "good luck"}]}
    later = _build(taps={iid: ("newword_add_new", "2026-10-02T10:00:00Z")}, doc=doc)
    assert by_ar(later, "2026-09-16")["بالتوفيق"]["status"] == "in_doc"
    assert next(p for p in later["promised"] if p["id"] == iid)["state"] == "in_doc"


def test_AM_19_a_promised_word_not_in_the_doc_after_7_days_is_still_waiting_and_nothing_is_sent():
    iid = N.item_id("2026-09-16", "taught:" + N._tkey("بالتوفيق"))
    taps = {iid: ("newword_add_old", "2026-10-02T10:00:00Z")}
    p = lambda out: next(x for x in out["promised"] if x["id"] == iid)
    assert p(_build(taps=taps, today="2026-10-05"))["still_waiting"] is False
    late = _build(taps=taps, today="2026-10-09")
    assert p(late)["still_waiting"] is True and p(late)["waiting_days"] == 7 and late["counts"]["promised_still_waiting"] == 1
    assert by_ar(late, "2026-09-16")["بالتوفيق"].get("still_waiting") is True
    src = open(os.path.join(REPO, "scripts", "amal_new_words.py"), encoding="utf-8").read()
    assert "send_email" not in src and "gmail" not in src.lower()                         # ai_rules A1: no message by code


def test_AM_19_a_word_in_her_doc_and_never_answered_gets_no_card():
    doc = {"items": DOC["items"] + [{"key": "dmaa8", "arabizi": "Dmaa8", "arabic": "دماغ", "english": "brain"}]}
    out = _build(doc=doc)
    assert not any(i["arabic"] == "دماغ" for i in out["items"])
    assert by_ar(out, "2026-09-26")["دماغ"]["status"] == "in_doc"


def test_AM_19_older_cards_fold_only_past_the_limit():
    L = "بتثجحخدذرزسشصضطظعغفقكلمنهوي"
    many = [E("2026-09-1%d" % (i % 9 + 1), L[i] + L[(i * 7 + 3) % len(L)] + L[(i * 5 + 1) % len(L)], None, "w", float(i))
            for i in range(N.OLDER_FOLD + 1)]
    tv = [{"date": e["date"], "arabic": e["arabic"], "verdict": "new"} for e in many]
    out = N.build([], taps={}, today="2026-10-02", marks={"marks": []}, doc=DOC, taught=many, taught_verdicts=tv, turns_for=lambda d: [])
    assert out["counts"]["older_open"] == N.OLDER_FOLD + 1 and out["older_fold"] == N.OLDER_FOLD and out["older_before"] == N.START


def test_AM_19_taught_entries_union_reader_and_hand_pairs():
    reads = {"2026-09-16": {"taught": [{"latin": "Ana ba7ammes", "arabic": "أنا بحمّس", "review": True}],
                            "taught_words": [{"latin": None, "arabic": "بالتوفيق", "english": "good luck", "t": "07:00"}]}}
    lessons = [{"date": "2026-09-16", "taught": [{"latin": "Ana ba7ammes", "arabic": "أنا بحمّس", "review": True}]},
               {"date": "2026-09-04", "taught": [{"latin": "Ana babse6", "arabic": "أنا ببسط", "review": False}]}]
    got = N.taught_entries(reads, lessons)
    assert [(e["date"], e["arabic"], e["by"]) for e in got] == [("2026-09-04", "أنا ببسط", "hand"), ("2026-09-16", "بالتوفيق", "reader"),
                                                               ("2026-09-16", "أنا بحمّس", "hand")]
    assert got[1]["t"] == 420.0
    src = open(os.path.join(REPO, "scripts", "build_lessons_page_data.py"), encoding="utf-8").read()
    assert "taught_words = list(rd.get(\"taught_words\") or []) if rd else []" in src      # hand dates no longer hide them


def test_AM_19_every_reader_taught_word_in_the_repo_is_judged():
    """The committed reads all have a by-meaning row (or are plainly in the Doc): nothing silently unasked."""
    import lesson_type_read as LTR
    tv = json.load(open(N.TAUGHT_VERDICTS, encoding="utf-8"))
    assert all(v["verdict"] in ("on_doc", "new", "on_card") and v.get("reason") for v in tv)
    for d in LTR.load_all(REPO):
        assert N.taught_unjudged(d) == [], d
