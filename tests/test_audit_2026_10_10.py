# -*- coding: utf-8 -*-
"""The 2026-10-10 audit of 10-08 from Medi's own notes (Medi 2026-10-10: "do a full audit of the lesson and use the
corrections I made to make final rule adjustments and corrections"). PG-44, PG-45, WS-36, TR-30."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import medi_corrections as MC          # noqa: E402
import transcript_fixes as TF          # noqa: E402
import transcript_marks as TM          # noqa: E402
import word_coverage as WC             # noqa: E402


def lesson(date="2026-10-08"):
    return json.load(open(os.path.join(ROOT, "docs", "data", "lessons", date + ".json"), encoding="utf-8"))


def chips_at(d, t, who="Medi"):
    i = next(k for k, u in enumerate(d["turns"]) if u["who"] == who and abs(u["t"] - t) < 0.5)
    return d["turns"][i], (d["tmarks"].get(str(i)) or {}).get("c", [])


# ---------------------------------------------------------------- PG-44 a grey chip names its word
def test_pg_44_a_grey_chip_names_its_word_and_an_asked_word_names_what_she_gave():
    """Medi 2026-10-10: 'why are there pill boxes still not showing arabizi as well'."""
    d = lesson()
    grey = [c for v in d["tmarks"].values() for c in v["c"] if c.get("s") == "na" and not c.get("hide") and c.get("label") == "vocab"]
    named = [c for c in grey if c.get("ar")]
    assert len(named) >= 0.5 * len(grey)
    turn, cs = chips_at(d, 550.48)                                   # 09:10 'how do I say taking care'
    asked = [c for c in cs if c.get("s") == "na" and c.get("ar")]
    assert asked and "ديرت بالي" in asked[0]["ar"] and "asked the tutor" in asked[0]["why"]
    js = open(os.path.join(ROOT, "docs", "js", "transcript-marks.js"), encoding="utf-8").read()
    assert "PG-44" in js and "c.s === 'na' && isArabic(c.ar)" in js


# ---------------------------------------------------------------- PG-45 her مهم is mm-hmm
def test_pg_45_the_tutors_mhm_is_mm_hmm_not_important():
    """Medi 2026-10-09 on 10-08 24:45: 'MHM (confirmation)'."""
    t = [{"t": 1.0, "who": "Amal", "text": "مهم."}, {"t": 2.0, "who": "Amal", "text": "هاد مهم كتير"}, {"t": 3.0, "who": "Medi", "text": "مهم."}]
    out = TF.tutor_nod([dict(u) for u in t], "2026-10-08")
    assert out[0]["text"] == "Mm-hmm." and out[0]["engine"] == "مهم." and out[1]["text"] == "هاد مهم كتير" and out[2]["text"] == "مهم."
    assert TF.tutor_nod([dict(u) for u in t], "2026-10-06")[0]["text"] == "مهم."        # earlier lessons wait for his yes
    d = lesson()
    assert chips_at(d, 1485.44, "Amal")[0]["text"] == "Mm-hmm." or any(u["who"] == "Amal" and u["text"] == "Mm-hmm." for u in d["turns"])


# ---------------------------------------------------------------- WS-36 said twice in a row = one try
def test_ws_36_the_same_word_twice_in_a_row_is_one_try():
    """Medi 2026-10-09 on 10-08 22:01: 'dont double count 2amar'; 47:07 'dont double count'."""
    d = lesson()
    rows = {(r["t"], r["word"]): r for r in WC.report("2026-10-08")}
    assert rows[("22:03", "قمر")]["state"] == "correct"
    assert rows[("47:07", "شجر")]["state"] == "correct" and rows[("47:09", "شجر")]["state"] == "na"
    assert "said again" in rows[("47:09", "شجر")]["why"]
    # another form of the word is another try (38:43 غيوم then 38:46 غيم)
    assert rows[("38:46", "غيم")]["state"] == "correct"
    # his line ending on راح goes on in his next line: ra7 'will' (15:30 'أنا راح،' / 15:33 'أعمله')
    turns = [{"t": 1.0, "end": 2.0, "who": "Medi", "text": "أنا راح،"}, {"t": 3.0, "end": 4.0, "who": "Medi", "text": "أعمله"}]
    assert WC.next_his_word(turns, 0) == "أعمله"
    turns.insert(1, {"t": 2.5, "end": 2.8, "who": "Amal", "text": "شو؟"})
    assert WC.next_his_word(turns, 0) == ""
    assert any(c.get("key") == "ra7" or c.get("w") == "ra7" for c in chips_at(d, 930.17)[1])


def test_ws_36_a_fix_belongs_to_her_one_line_nearest_its_time():
    """10-08 09:48: her 'بال مين؟' sat 2.5 s before her 09:51 fix and took its words, so his خطيبتي (said before) read as a repeat."""
    turns = [{"t": 588.5, "who": "Amal", "text": "بال مين؟"}, {"t": 588.8, "who": "Medi", "text": "خطيبتي."},
             {"t": 590.6, "who": "Amal", "text": "بالي على خطيبتي."}]
    sup = WC.supplies(turns, [(591.0, "بالي على خطيبتي")], "2026-10-08")
    assert 0 not in sup.given and sup.given.get(2)
    old = WC.supplies(turns, [(591.0, "بالي على خطيبتي")], "2026-10-06")
    assert old.given.get(0)                                          # earlier lessons unchanged until his yes


# ---------------------------------------------------------------- TR-30 the note reader's rows
def test_tr_30_the_note_readers_rows_never_undo_the_second_listen_or_put_latin_on_arabic():
    assert not MC.ai_text_ok({"engine_wrote": "اليوم talvez", "heard": "اليوم talvez", "line": "اليوم talvez"})
    assert MC.ai_text_ok({"engine_wrote": "مرحبا", "heard": "مرحبا", "credit": "independent"})        # his credit note stays
    assert not MC.ai_text_ok({"engine_wrote": "به", "heard": "bye7re2*", "line": "به."})
    assert not MC.ai_text_ok({"engine_wrote": "زعلتكش عن", "heard": "8eir 3an", "line": "مم. زعلتكش عن."})
    assert MC.ai_text_ok({"engine_wrote": "Defect", "heard": "keefak", "line": "Defect."})
    assert not TF._lands({"who": "Medi", "t": 1.0, "engine_wrote": "bara", "heard": "bara", "ai": True}, {"who": "Medi", "t": 1.0, "text": "Um, bara."})
    assert TF._lands({"who": "Medi", "t": 1.0, "engine_wrote": "bara", "heard": "bara"}, {"who": "Medi", "t": 1.0, "text": "Um, bara."})
    p = open(os.path.join(ROOT, "scripts", "correction_parse_prompt.md"), encoding="utf-8").read()
    assert "TR-30" in p and '"X*"' in p


# ---------------------------------------------------------------- the 10-08 moments of his notes
def test_10_08_moments_from_his_notes():
    d = lesson()
    T = {round(u["t"], 2): u for u in d["turns"]}
    assert "غير" in T[1920.22]["text"] and "بعيد" not in T[1925.86]["text"]          # '8eir* (not ba3eed)'
    assert T[2988.22]["text"].startswith("أرض")                                       # 'not w-Rudd, ardd'
    assert T[1269.28]["text"] == "شو جمع طيارة؟"                                       # 'shu jam3a tayara*'
    w = lambda t, s: [c for c in chips_at(d, t)[1] if c.get("k") == "vocab" and c.get("s") == s]
    assert w(973.57, "wrong")                                                          # 16:13 عصافير for sky
    assert w(2162.66, "wrong")                                                         # 36:02 الماضي for قبل
    assert w(2424.45, "wrong")                                                         # 40:24 أجو for قوي
    assert w(1205.24, "correct")                                                       # 20:05 his غيوم counts
    assert any(c.get("k") == "grammar" and c.get("s") == "wrong" and c.get("rule") == "A1" for c in chips_at(d, 1325.36)[1])
    assert not any(c.get("s") == "wrong" for c in chips_at(d, 729.62)[1])              # 12:09 'this wasnt a mistake'


def test_ws_36_his_question_about_her_words_quotes_them():
    """Medi 2026-10-09 on 10-08 59:29: 'these are all repeats'; 59:44 'all repeates'."""
    turns = [{"t": 3566.5, "end": 3568.0, "who": "Amal", "text": "هاد الدرس المفضل عندي."},
             {"t": 3569.1, "end": 3572.2, "who": "Medi", "text": "Okay, so it is il mufaddal, but why is it il here?"},
             {"t": 3600.0, "end": 3601.0, "who": "Medi", "text": "الدرس المفضل عندي"}]
    assert WC.question_about(turns, 1) == [0] and WC.question_about(turns, 2) == []
    d = lesson()
    for t in (3569.13, 3579.11, 3587.11):
        cs = chips_at(d, t)[1]
        assert not any(c.get("s") == "correct" for c in cs) and any(c.get("s") == "repeat" and c.get("k") == "vocab" for c in cs)


# ---------------------------------------------------------------- WS-37 his sounds (10-08 / 10-09)
def test_ws_37_his_sounds_find_her_word():
    """His ق / غ / ء are one sound (Farsi; her 2 is ق), the engine's ذ / ظ and ت / ط swap, a long a written in."""
    words = json.load(open(os.path.join(ROOT, "docs", "data", "words.json"), encoding="utf-8"))["items"]
    K = WC.Keys(words)
    K.sound = True
    for w, k in (("أوي", "2awi"), ("بوذة", "buzah"), ("بوذتي", "buzah"), ("مابسوت", "mabsU6"), ("ماي", "maI"), ("أكلب", "a8lab"), ("الشاطئ", "sha6")):
        assert K.lookup(w)[0] == k, (w, K.lookup(w))
    K.sound = False
    assert K.lookup("أوي")[0] is None                                   # earlier lessons wait for Medi's yes
    assert WC.taught_match("غابة", "قبه", 1600.0, 1630.0, sounds=True) and WC.taught_match("نعنع", "نانا", 255.0, 260.0, sounds=True)
    assert not WC.taught_match("نعنع", "نانا", 255.0, 260.0)
    assert WC.is_pronoun("أنااا")
    d = lesson("2026-10-09")
    rows = {(r["t"], r["word"]): r for r in WC.report("2026-10-09")}
    assert rows[("11:13", "إيران")]["why"].startswith("إيران: a name")       # a place name is a name, not 'not on her list'
    assert not [r for r in rows.values() if not r["cut"] and not r["state"]]  # WS-30 still holds


def test_tr_31_the_tutors_words_fix_a_misheard_word_of_his():
    """10-09: the engine's تيني (fig) was his أعطيني, بيتي (my house) his بدي, أعلم his أغلب - her chat line says so."""
    d = lesson("2026-10-09")
    T = {round(u["t"], 2): u for u in d["turns"]}
    assert T[2887.6]["text"] == "أعطيني" and "بدي" in T[3750.2]["text"] and T[3123.02]["text"].startswith("أغلب")
    fx = json.load(open(os.path.join(ROOT, "data", "lesson-work", "transcript-fixes.json"), encoding="utf-8"))["rows"]
    mine = [r for r in fx if r.get("rule") == "TR-31"]
    assert mine and all(r.get("why") and "tutor" in r["why"] for r in mine)
    assert not any(c.get("w") == "Teen" for c in chips_at(d, 2887.6)[1])


# ---------------------------------------------------------------- GR-35 the counter reads like a teacher (10-08 / 10-09)
def test_gr_35_teacher_read():
    import detect_grammar_usage as D
    r = lambda t: D.teacher_read(D.detect(D.teacher_text(t)), D.teacher_text(t))
    assert "A1" not in r("اليوم") and "A2" not in r("شوي أقل شوب اليوم") and not r("نار والله")
    assert "A10" not in r("هذا") and {"A10", "A10b"} <= set(r("هذه القبة")) and "B2" in r("بنقدر نروح")
    assert {"D1", "D5"} <= set(r("في الـ صيف،")) and "E4" not in r("عشرة ألفين وستة عشر")
    assert D.asks_more("Would it be مفضلة؟") and D.asks_more("So there's no الـ... Uh, no هذي القبة.") and not D.asks_more("هذا الشاطئ")
    u = json.load(open(os.path.join(ROOT, "docs", "data", "grammar-usage.json"), encoding="utf-8"))
    assert not any(x["date"] == "2026-10-09" and x["mmss"] == "06:36" for x in u["uses"].get("A1", []))   # اليوم today


def test_ws_37_merhaba_counts_and_hadi_is_this():
    """Medi 2026-10-09 on 10-08 00:10 'merhaba vocab should count': the second listen's مرحبا for his Latin 'Marhaba' is the
    same word of hers (10-09 01:34 too); هادي is her 'This (F)' unless the line is about calm."""
    for date, t in (("2026-10-08", 10.37), ("2026-10-09", 94.5)):
        assert any(c.get("k") == "vocab" and c.get("s") == "correct" for c in chips_at(lesson(date), t)[1]), date
    assert any(c.get("w") == "Hadi" for c in chips_at(lesson("2026-10-09"), 4084.3)[1] + chips_at(lesson("2026-10-09"), 4090.3)[1])


def test_gr_36_her_mm_hmm_with_no_fix_after_says_he_said_it_right():
    """GR-36, Medi 2026-10-10: 'mmhhmm can be a signal for "correct" like mumtaz'."""
    import full_audit_build as F
    T = [{"t": 10.0, "end": 12.0, "who": "Medi", "text": "على اثنتين."}, {"t": 12.2, "end": 12.6, "who": "Amal", "text": "Mm-hmm."}]
    assert F.praised(T, 10.0, "على التنتين", "2026-10-09") is not None
    assert F.praised(T, 10.0, "على التنتين", "2026-10-06") is None                       # earlier lessons wait for his yes
    fixed = T + [{"t": 13.0, "end": 15.0, "who": "Amal", "text": "قلت انتين، بس very good."}]
    assert F.praised(fixed, 10.0, "على التنتين", "2026-10-09") is None                    # a fix after the nod: not 'correct'
    before = [{"t": 9.0, "end": 9.4, "who": "Amal", "text": "Mm-hmm."}] + T[:1]
    assert F.praised(before, 10.0, None, "2026-10-09") is None                            # her nod before his line answers something else
