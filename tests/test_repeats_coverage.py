# -*- coding: utf-8 -*-
"""WS-30 / WS-31 / GR-32 / GR-33 / PG-39 / AZ-14 / PG-40 / WS-32 (Medi 2026-10-09 on the 10-08 lesson: "any time I speak ANY arabic word that you are giving me
credit or marking as incorrect. Mark as repeat if I am repeating one of amals corrections and dont give me credit for it
... for grammar errors that I am being corrected and repeating the correctiong. THese should also be marked as repeat
and uncounted")."""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import word_coverage as WC  # noqa: E402
import detect_grammar_usage as D  # noqa: E402

# 10-08 03:55-04:06, as the page shows it after the second listen
TURNS = [
    {"t": 230.4, "end": 231.0, "who": "Medi", "text": "بيوجع"},
    {"t": 235.8, "end": 237.0, "who": "Medi", "text": "هي بيوجع"},
    {"t": 238.8, "end": 239.5, "who": "Medi", "text": "راسها"},
    {"t": 240.6, "end": 242.0, "who": "Amal", "text": "هي راسها بيوجع."},
    {"t": 243.6, "end": 244.0, "who": "Medi", "text": "Huh?"},
    {"t": 244.8, "end": 246.0, "who": "Amal", "text": "راسها بيوجع."},
    {"t": 246.6, "end": 248.0, "who": "Medi", "text": "هي راسها بيوجع"},
    {"t": 298.8, "end": 300.0, "who": "Amal", "text": "لا. طيب. شو اليوم؟"},
    {"t": 313.7, "end": 316.0, "who": "Medi", "text": "Uh, يوم الخميس"},
]
FAKE_KEY = {"بيوجع": "bawaje3", "راسها": "rAs", "راس": "rAs", "يوم": "yoam"}.get


def test_scope_is_every_lesson_past_and_future():
    # Medi 2026-10-09 "you are making rules for all these right? to solve in the future and past"
    assert WC.in_scope("2026-08-25") and WC.in_scope("2026-10-06") and WC.in_scope("2026-10-08") and WC.in_scope("2026-10-12")


def test_ws_31_her_recast_is_a_supply_and_her_question_is_not():
    sup = WC.supplies(TURNS)
    assert 3 in sup and 5 in sup                 # her recasts of his هي بيوجع / راسها
    assert 7 not in sup                          # 'شو اليوم؟' asks him; it gives him nothing to repeat


def test_ws_31_a_word_said_after_her_fix_is_a_repeat_not_a_credit():
    sup = WC.supplies(TURNS)
    state, why, j = WC.judge_word(TURNS, 6, "راسها", "rAs", FAKE_KEY, sup)
    assert state == "repeat" and j == 5 and "WS-31" in why
    # the same word before her fix is his own: credited (WS-30)
    assert WC.judge_word(TURNS, 2, "راسها", "rAs", FAKE_KEY, sup)[0] == "independent"
    # her question's word in his own new answer of 2 words is half credit, as before (not a repeat)
    assert WC.judge_word(TURNS, 8, "يوم", "yoam", FAKE_KEY, sup)[0] in ("helped", "independent")


def test_ws_30_a_word_said_alone_is_judged_not_left_unresolved():
    turns = [{"t": 9.3, "who": "Amal", "text": "Hello."}, {"t": 10.4, "end": 10.7, "who": "Medi", "text": "مرحبا."}]
    assert WC.judge_word(turns, 1, "مرحبا", "marhaba", lambda w: None, {})[0] == "independent"


def test_gr_32_the_grammar_use_in_the_repeat_is_not_a_use_but_his_own_first_try_is():
    T = [{"speaker": u["who"], "start": u["t"], "end": u["end"], "text": u["text"]} for u in TURNS]
    TW = D.as_turns(T)
    sup = WC.supplies(TW)
    assert D.grammar_repeat(TW, 6, "بيوجع", sup) == 5          # 04:06 B1 بيوجع: her 04:04 line gave it
    assert D.grammar_repeat(TW, 0, "بيوجع", sup) is None       # 03:50: his own
    row = D.repeat_row("2026-10-08", 246.6, TW[5], "B1", "بيوجع", TURNS[6]["text"])
    assert row["repeat"] is True and row["rule"] == "GR-32" and "04:04" in row["why"]


def test_gr_32_his_wrong_form_again_is_not_a_repeat_of_her_right_one():
    # 10-08 02:00 Amal عيانة؟ (her fix of his عيان) then 02:21 his خطيبتي شوي عيان: the slip again, never 'her word'
    T = [{"speaker": "Medi", "start": 117.1, "end": 119, "text": "عيان، عيان is sick."},
         {"speaker": "Amal", "start": 120.5, "end": 121, "text": "عيانة؟"},
         {"speaker": "Medi", "start": 141.1, "end": 143, "text": "uh, خطيبتي شوي عيان"}]
    TW = D.as_turns(T)
    sup = WC.supplies(TW, [120.0])
    assert 1 in sup
    assert D.grammar_repeat(TW, 2, "عيان", sup) is None


def test_latin_words_in_an_english_sentence_are_not_his_arabic():
    assert WC.word_tokens("also a name.") == []
    got = [(x["ar"], x["shown"]) for x in WC.word_tokens("Mish awal wa-wahad? Would you say that?")]
    assert ("مش", "Mish") in got


def test_a_pronoun_is_never_keyed_to_a_list_phrase_it_only_starts():
    words = [{"key": "ana batbu5", "arabic": "أنا بطبخ", "arabizi": "Ana batbu5", "topic": "Verbs List"}]
    keys = WC.Keys(words, sheet={WC.norm("أنا"): {"on_sheet": True, "key": "ana batbu5", "match": "part"}}, catalog={"groups": []})
    assert keys.lookup("أنا")[1] == "part"


def test_every_arabic_word_of_his_on_10_08_carries_a_mark():
    rows = WC.report("2026-10-08")
    assert rows, "10-08 page data missing"
    missing = [r for r in rows if not r["cut"] and not r["state"]]
    assert not missing, "Arabic words with no mark (WS-30): %s" % missing[:5]


def test_10_08_his_answer_key_moments():
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-08.json"), encoding="utf-8"))
    T, tm = d["turns"], d["tmarks"]

    def chips(t, who="Medi"):
        i = next(k for k, u in enumerate(T) if u["who"] == who and abs(u["t"] - t) < 0.3)
        return (tm.get(str(i)) or {}).get("c", [])
    # 04:06 "shouldnt count as correct it was a repeat. Lets mark repeats as repeats"
    c = chips(246.6)
    assert any(x["k"] == "grammar" and x["s"] == "repeat" for x in c)
    assert any(x["k"] == "vocab" and x["s"] == "repeat" for x in c)
    assert not any(x["s"] == "correct" for x in c)
    # 00:10 "merhaba vocab should count"
    assert any(x["k"] == "vocab" and x["s"] == "correct" for x in chips(10.4))
    # 02:25 he says عيانة after her 02:22 recast: a repeat
    assert any(x["k"] == "vocab" and x["s"] == "repeat" for x in chips(145.6))


def test_the_page_draws_a_repeat_chip():
    node = os.environ.get("ANEES_NODE") or r"C:\dev\tools\node-v24.18.0-win-x64\node.exe"
    js = ("const T=require(%s);const m=T.chipModel({k:'vocab',s:'repeat',ar:'راسها',amal_t:244.8,amal_line:'راسها بيوجع.'},null);"
          "console.log(JSON.stringify([m.sign,m.word,T.LEGEND.some(g=>g[0]==='repeat')]))") % json.dumps(os.path.join(ROOT, "docs", "js", "transcript-marks.js"))
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip()
    assert json.loads(out) == ["↻", "Repeat", True]


def test_gr_33_her_praise_right_after_means_he_said_it_right():
    import full_audit_build as F
    turns = [{"t": 1430.7, "end": 1432.7, "who": "Medi", "text": "واحدة شمس."},
             {"t": 1432.4, "end": 1435.3, "who": "Amal", "text": "Mm. Mm-hmm. واحدة."},
             {"t": 1438.0, "end": 1438.5, "who": "Amal", "text": "Great job."}]
    row = {"date": "2026-10-08", "t": "23:51", "kind": "grammar-B", "wrong": "واحدة شمس", "right": "شمس وحدة"}
    assert F.apply_praise([row], lessons={"2026-10-08": turns}) == 1 and row["rejected_rule"] == "GR-33"
    # praise with a fix in it, or a new word of hers first, is no praise of his line
    fixed = [turns[0], {"t": 1433, "end": 1434, "who": "Amal", "text": "شمس وحدة."}, turns[2]]
    row2 = {"date": "2026-10-08", "t": "23:51", "kind": "grammar", "wrong": "واحدة شمس", "right": "شمس وحدة"}
    assert F.apply_praise([row2], lessons={"2026-10-08": fixed}) == 0
    but = [turns[0], {"t": 1433, "end": 1434, "who": "Amal", "text": "Great job, but say وحدة."}]
    assert F.apply_praise([dict(row2)], lessons={"2026-10-08": but}) == 0
    # every lesson, past ones too
    old = dict(row, date="2026-09-30", kind="grammar")
    assert F.apply_praise([old], lessons={"2026-09-30": turns}) == 1


def test_pg_39_one_chip_per_word_the_strongest_shown_the_rest_kept_hidden():
    import transcript_marks as TM
    turns = [{"t": 449.3, "who": "Medi", "text": "من نار."}]
    tm = {"0": {"c": [{"id": "r1", "k": "grammar", "s": "repeat", "rule": "D1", "said": "من نار"},
                      {"id": "n1", "k": "na", "s": "na", "label": "vocab", "ar": "من", "why": "من: a preposition: scored as grammar, not as a word"},
                      {"id": "n2", "k": "na", "s": "na", "label": "vocab", "ar": "نار", "why": "نار: on her list"}], "u": []}}
    out = TM.one_per_word(tm, turns)["0"]["c"]
    shown = [c for c in out if not c.get("hide")]
    assert [c["id"] for c in shown] == ["r1"] and len(shown[0]["also"]) == 2
    # a wrong beats everything on the same word
    tm = {"0": {"c": [{"id": "v1", "k": "vocab", "s": "correct", "ar": "عيان"}, {"id": "x1", "k": "grammar", "s": "wrong", "said": "عيان"}], "u": []}}
    turns = [{"t": 141.1, "who": "Medi", "text": "خطيبتي شوي عيان"}]
    assert [c["id"] for c in TM.one_per_word(tm, turns)["0"]["c"] if not c.get("hide")] == ["x1"]


def test_pg_39_a_word_taught_this_lesson_and_not_on_her_list_is_a_new_word():
    assert WC.taught_match("مطر", "مطرت") and WC.taught_match("حجر", "حجري")
    assert not WC.taught_match("بيدير", "بيد")          # his بعيد misheard, not her بيدير
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-08.json"), encoding="utf-8"))
    new = [c for v in d["tmarks"].values() for c in v["c"] if c["s"] == "new"]
    assert new and all("not scored" in c["why"] for c in new)


def test_pg_39_the_page_key_has_one_colour_per_meaning():
    css = open(os.path.join(ROOT, "docs", "css", "lessons.css"), encoding="utf-8").read()
    for s in ("correct", "partial", "wrong", "repeat", "new", "fix", "na"):
        assert "#anees-bank .tm-%s{" % s in css or ".tm-%s," % s in css, s


def test_ws_30_10_08_08_36_every_word_of_his_outfit_line_is_credited():
    """Medi 2026-10-09: 'I wear a black shirt and light blue pants.. I should get credit for all of thse.'"""
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-08.json"), encoding="utf-8"))
    T, tm = d["turns"], d["tmarks"]
    ok = set()
    for k, v in tm.items():
        if 515 < T[int(k)]["t"] < 530:
            for c in v["c"]:
                if c["k"] == "vocab" and c["s"] == "correct":
                    ok |= {WC.core(w) for x in [c] + (c.get("words") or []) for w in re.split(r"[\s/]+", str(x.get("ar") or "")) if w}
    for w in ("اليوم", "بلبس", "بلوزة", "سودة", "بنطلون", "أزرق", "فاتح"):
        assert WC.core(w) in ok, w


def test_az_14_her_one_word_row_spells_the_word():
    """AZ-14 (Medi 2026-10-09 "are we using amals arabizi? I dont see 3ala for the preposition"): على is her 3ala, not the
    'ala of her phrase 'tesbah 'ala kheir'; من stays her Min (from), never her chat's Meen (who)."""
    node = os.environ.get("ANEES_NODE") or r"C:\dev\tools\node-v24.18.0-win-x64\node.exe"
    js = r"""const path=require('path'),fs=require('fs');const R=%s;const J=f=>JSON.parse(fs.readFileSync(path.join(R,'data',f),'utf8'));
const h=J('house_spelling.json').items||{};const w=(J('words.json').items||[]).map(x=>{const y=h[x.match_loose];return y&&y.house?{...x,house_spelling:y.house}:x;});
const r=require(path.join(R,'js','word-bank-arabizi.js')).create(w,J('word-bank-catalog.json'),J('arabizi-extra.json'),{scope:'lessons',snap:true});
console.log(JSON.stringify(['على. بدير بالي takes على.','من','مع','تسعة'].map(s=>r(s).text)));""" % json.dumps(os.path.join(ROOT, "docs"))
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip()
    assert json.loads(out) == ["3ala. badir baali takes 3ala.", "min", "Ma3", "tes3ah"]


def test_pg_40_every_arabic_line_of_10_08_has_its_english_under_it():
    """PG-40 (Medi 2026-10-09 "Lets add all the english transaltions below the arabic writing" -> whole sentence)."""
    import translate_lines as TRL
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-08.json"), encoding="utf-8"))
    want = [u for u in d["turns"] if TRL.wants(u)]
    have = [u for u in want if u.get("en")]
    assert want and len(have) >= 0.97 * len(want), (len(have), len(want))
    assert not any(u.get("en") for u in d["turns"] if not TRL.wants(u))     # English lines get none
    # the English is all English (Medi 2026-10-09 "just put the full english sentence for the translatuion")
    assert not [u["en"] for u in d["turns"] if re.search(r"[ء-ي]", u.get("en") or "")]
    js = open(os.path.join(ROOT, "docs", "js", "lessons-page.js"), encoding="utf-8").read()
    assert "en: [last.turn.en, t.en].filter(Boolean).join(' ')" in js
    js = open(os.path.join(ROOT, "docs", "js", "lessons-page.js"), encoding="utf-8").read()
    assert "if (t.en) main.appendChild(el('div', 'ls-line-en', t.en));" in js
    os.environ["ANEES_TRANSLATE"] = "off"
    try:
        assert TRL.run("2026-10-08", log=lambda *a: None) == 0              # the kill switch calls no model
    finally:
        os.environ.pop("ANEES_TRANSLATE", None)


def test_ws_32_pronouns_are_never_judged_and_ra7_is_read_from_the_next_word():
    """WS-32 (Medi 2026-10-09 "Lets leave out all the anna inti inta heyya huwwe humme e7na we can assume I know these
    always"); راح before a verb is her ra7 (will), else raa7 (he went)."""
    assert [t["ar"] for t in WC.word_tokens("Uh, yes, أنا راح، um, أعمله، uh، غلط كتير بس.")] == ["راح", "أعمله", "غلط", "كتير", "بس"]
    assert all(WC.is_pronoun(w) for w in ("أنا", "إنتي", "هي", "هو", "هم", "إحنا", "وأنا"))
    words = [{"key": "ra7", "arabic": "رح", "arabizi": "ra7"}, {"key": "rA7", "arabic": "راح", "arabizi": "raa7", "topic": "Past Tense"},
             {"key": "8ala6", "arabic": "غلط", "arabizi": "8ala6", "topic": "Adjectives"}]
    keys = WC.Keys(words, catalog={"groups": []})
    assert keys.lookup("راح")[1] == "unclear"          # the matcher alone cannot tell will from went
    detail = {"turns": [{"t": 930.0, "end": 935.0, "who": "Medi", "text": "أنا راح أعمله غلط"}], "grammar_errors": [], "vocab_errors": []}
    anchor = {"id": "a", "lesson_date": "2026-10-09", "speaker": "Medi", "t_start": 1, "local_start": 1, "source_sha256": "h"}
    adds, _, rows = WC.plan("2026-10-09", detail, [anchor], keys, rulings=[])
    assert all(not WC.is_pronoun(r["word"]) for r in rows)
    assert next(r for r in rows if r["word"] == "راح")["key"] == "ra7"
    detail["turns"][0]["text"] = "أمس هو راح"
    _, _, rows = WC.plan("2026-10-09", detail, [anchor], keys, rulings=[])
    assert next(r for r in rows if r["word"] == "راح")["key"] == "rA7"


def test_ws_33_marra_is_her_one_time_row_and_a_word_she_typed_in_chat_is_new():
    """WS-33 (Medi 2026-10-09 "are you not following amals spelling for the corrections?", 10-08 35:20 مرة. Um, تلجت):
    مرة is her 'one time' row (Marra), never 'Bitter (F)' (Murra); تلجت is her chat's tallajat, a new word."""
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-08.json"), encoding="utf-8"))
    T, tm = d["turns"], d["tmarks"]
    i = next(k for k, u in enumerate(T) if u["who"] == "Medi" and abs(u["t"] - 2119.6) < 0.3)
    cs = [c for c in (tm.get(str(i)) or {}).get("c", []) if c["k"] == "vocab" and not c.get("hide")]
    assert cs and all("مر /" not in (c.get("ar") or "") for c in cs), cs
    j = next(k for k, u in enumerate(T) if u["who"] == "Medi" and abs(u["t"] - 2125.1) < 0.3)
    assert any(c["s"] == "new" for c in (tm.get(str(j)) or {}).get("c", [])), tm.get(str(j))


def test_ws_33_a_sound_swapped_letter_still_finds_her_word():
    """Medi 2026-10-09 "for hadaak? its on the list?" (10-08 1:03:37 هذاك = her هداك Hadaak 'That (M)')."""
    words = [{"key": "hadAk", "arabic": "هداك", "arabizi": "Hadaak", "english": "That (M)"},
             {"key": "hAda hu", "arabic": "هذا هو", "arabizi": "Haada hu", "english": "That's it"}]
    assert WC.Keys(words, catalog={"groups": []}).lookup("هذاك") == ("hadAk", "one")


# ---------------------------------------------------------------- WS-34 (Medi 2026-10-09 "– Not scored · vocab · حجار: one word
# of a longer list phrase (7ajar), not a list word by itself ... can you give me a list of these from 10-8 not scored" then
# "fix in a new chip")
WS34_WORDS = [
    {"key": "7ajar", "arabic": "حجر", "arabizi": "7ajar", "english": "Stone", "plural": "7jaar"},
    {"key": "nejme", "arabic": "نجمة", "arabizi": "Nejme", "english": "Star", "plural": "Nujoom"},
    {"key": "6aiyAra", "arabic": "طيارة", "arabizi": "6ayyaara", "english": "Airplane / flight", "plural": "6ayyaaraat (طيارات)"},
    {"key": "fus6An", "arabic": "فستان", "arabizi": "Fustaan", "english": "Dress", "plural": "Fasateen"},
    {"key": "hadIye", "arabic": "هدية", "arabizi": "Hadiyye", "english": "Gift", "plural": "Hadaya"},
    {"key": "betalej", "arabic": "بتتلج", "arabizi": "Betetlej", "english": "It's snowing"},
    {"key": "talj", "arabic": "تلج", "arabizi": "Talj", "english": "Snow"},
    {"key": "eno", "arabic": "أنو", "arabizi": "Enno", "english": "That (Connector)"},
    {"key": "3eshrIn", "arabic": "عشرين", "arabizi": "3eshreen", "english": "twenty"},
    {"key": "shams", "arabic": "شمس", "arabizi": "Shams", "english": "Sun"},
    {"key": "shurU2 el shams", "arabic": "شروق الشمس", "arabizi": "ShurU2 el shams", "english": "Sunrise"},
    {"key": "mbAre7", "arabic": "مبارح", "arabizi": "Mbaare7", "english": "Yesterday"},
    {"key": "ahla u sahla", "arabic": "أهلاً و سهلاً", "arabizi": "Ahla w sahla", "english": "Welcome"},
    {"key": "hala", "arabic": "هلا", "arabizi": "Hala", "english": "Now"},
    {"key": "hada", "arabic": "هادا", "arabizi": "Hada", "english": "This (M)"},
    {"key": "hAda hu", "arabic": "هذا هو", "arabizi": "Haada hu", "english": "That's it"},
    {"key": "bilail", "arabic": "بالليل", "arabizi": "Billail", "english": "At night"},
    {"key": "aldenia lail", "arabic": "الدنيا ليل", "arabizi": "El-denia lail", "english": "It's night time"},
    {"key": "mesh zAki", "arabic": "مش زاكي", "arabizi": "Mesh zaaki", "english": "Not delicious"},
    {"key": "law samaht", "arabic": "لو سمحت", "arabizi": "Law samaht", "english": "Please (m)"},
    {"key": "alsA3a", "arabic": "الساعة 3لا3ة وثلث", "arabizi": "", "english": "It's 3:20"},
    {"key": "yoam al5amIs", "arabic": "يوم الخميس", "arabizi": "Yoam el-5amees", "english": "Thursday"},
    {"key": "ma6Ar", "arabic": "مطار", "arabizi": "Ma6aar", "english": "Airport", "plural": "Ma6araat"},
]


def _keys(sheet=None):
    return WC.Keys(WS34_WORDS, sheet={WC.norm(k): v for k, v in (sheet or {}).items()}, catalog={"groups": []})


def test_ws_34_a_plural_of_her_word_is_that_word():
    """10-08 50:27 حجار is her 7ajar's plural 7jaar (her Doc's plural column); نجوم = Nujoom, طيارات = her (طيارات),
    فساتين = Fasateen (a long a written single). Three short letters never match (هذي is not Hadaya 'gifts'), and a word
    with no long a in it never matches a plural that has one (مطرت 'it rained' is not Ma6araat 'airports')."""
    k = _keys({"حجار": {"on_sheet": True, "key": "7ajar"}})
    assert k.lookup("حجار") == ("7ajar", "one")
    assert k.lookup("نجوم") == ("nejme", "one") and k.lookup("طيارات") == ("6aiyAra", "one") and k.lookup("فساتين") == ("fus6An", "one")
    assert k.lookup("هذي")[0] != "hadIye" and k.lookup("مطرت")[1] == "none"
    assert k.is_plural("حجار") and not k.is_plural("حجر")


def test_ws_34_a_verb_form_of_her_verb_is_that_verb():
    """10-08 34:15 بتلج = her بتتلج 'It's snowing' (one letter off), not 'one word of a longer list phrase'."""
    assert _keys({"بتلج": {"on_sheet": True, "key": "betalej"}}).lookup("بتلج") == ("betalej", "one")


def test_ws_34_her_one_word_row_wins_over_a_phrase_that_holds_it():
    k = _keys({"إنه": {"on_sheet": True, "key": "eno"}, "ليل": {"on_sheet": True, "key": "aldenia lail"},
               "مش": {"on_sheet": True, "key": "mesh zAki"}, "لا": {"on_sheet": True, "key": "alsA3a"},
               "امبارح": {"on_sheet": True, "key": "mbAre7"}})
    assert k.lookup("إنه") == ("eno", "one")             # her أنو: the -o ending written ـه
    assert k.lookup("ليل") == ("bilail", "one")          # her بالليل 'At night'
    assert k.lookup("امبارح") == ("mbAre7", "one")       # an extra ا / إ in front
    assert k.lookup("أهلا")[0] != "hala"                 # but أهلا is never her هلا 'Now'
    assert k.lookup("هذا") == ("hada", "one")            # the engine's MSA spelling of her هادا
    assert k.lookup("الخميس") == ("yoam al5amIs", "one") # a day name without يوم
    assert k.lookup("مش") == ("mesh zAki", "part")       # no row for مش alone: stays grey, says which phrase
    assert k.lookup("لا") == (None, "none")              # لا is not a word of '3لا3ة': simply not on her list


def test_ws_34_a_wa_prefix_is_stripped():
    k = _keys()
    assert k.lookup("وعشرين") == ("3eshrIn", "one") and k.lookup("والشمس") == ("shams", "one")


def test_ws_34_her_whole_phrase_is_the_word_and_the_grey_text_names_the_phrase():
    k = _keys({"لو": {"on_sheet": True, "key": "law samaht"}, "سمحت": {"on_sheet": True, "key": "law samaht"},
               "مش": {"on_sheet": True, "key": "mesh zAki"}})
    anchor = {"id": "a", "lesson_date": "2026-10-09", "speaker": "Medi", "t_start": 1, "local_start": 1, "source_sha256": "h"}
    detail = {"turns": [{"t": 900.0, "end": 902.0, "who": "Medi", "text": "لو سمحت"},
                        {"t": 960.0, "end": 962.0, "who": "Medi", "text": "مش"}], "grammar_errors": [], "vocab_errors": []}
    adds, _, rows = WC.plan("2026-10-09", detail, [anchor], k, rulings=[])
    assert [a["event"]["word_key"] for a in adds] == ["law samaht"] and adds[0]["event"]["text"] == "لو سمحت"
    assert next(r for r in rows if r["word"] == "سمحت").get("covered")
    grey = next(r for r in rows if r["word"] == "مش")
    assert grey["state"] == "na" and "only inside her phrase مش زاكي 'Not delicious'" in grey["why"]


def test_ws_34_the_article_alone_is_not_a_word():
    assert WC.arabic_tokens("ال، أل، إل الشمس") == [("الشمس", False)]


def test_ws_34_the_plural_he_finds_after_her_singular_is_his_own():
    """10-08 50:16 she gives حجر, 50:20 asks 'شو plural حجر؟', 50:27 he says حجار: his own answer, not a repeat."""
    k = _keys()
    turns = [{"t": 3016.17, "end": 3017.0, "who": "Amal", "text": "حجر."},
             {"t": 3020.83, "end": 3026.0, "who": "Amal", "text": "شجر وحجر، صح. إيه شو plural حجر؟ Do you remember؟"},
             {"t": 3027.18, "end": 3028.0, "who": "Medi", "text": "حجار."}]
    sup = WC.supplies(turns, [(3016.5, "حجر")])
    assert WC.judge_word(turns, 2, "حجار", "7ajar", k.of, sup, k.is_plural)[0] == "independent"
    assert WC.judge_word(turns, 2, "حجار", "7ajar", k.of, sup)[0] == "repeat"      # without the rule: wrongly a repeat


def test_ws_34_10_08_moments():
    rows = {(r["t"], r["word"]): r for r in WC.report("2026-10-08")}
    assert rows[("50:27", "حجار")]["state"] == "correct"
    assert rows[("50:27", "حجور")]["state"] == "new"           # his own tries keep their own marks (WS-35: her حجر of 50:16)
    assert rows[("34:15", "بتلج")]["state"] == "correct"
    for t, w in (("05:24", "وعشرين"), ("16:55", "والشمس"), ("14:41", "إنه"), ("21:17", "طيارات"), ("22:19", "نجوم")):
        assert rows[(t, w)]["state"] == "correct", (t, w, rows[(t, w)])
    assert all("one word of a longer list phrase" not in (r["why"] or "") for r in rows.values())


# ---------------------------------------------------------------- WS-35 (Medi 2026-10-09 "fix all": the 10-08 words still grey that
# were her words - taught that day, spelled by the engine with swapped letters, غير by meaning, the bare verb after رح / بدي)
def test_ws_35_a_word_she_taught_that_day_in_another_form_is_new():
    assert WC.taught_match("بدير", "ديرت") and WC.taught_match("بدير", "ديري")      # her verb, his past / to a woman
    assert WC.taught_match("مطرت", "بمطر")                                            # 29:40 before her 30:16
    assert WC.taught_match("خطيبتي", "ختيفتي")                                        # the engine's ت / ف for her ط / ب
    assert WC.taught_match("حجر", "حجور")                                             # a long vowel added
    assert WC.taught_match("فجر", "سجر", 1116, 1126) and not WC.taught_match("فجر", "سجر", 1116, 1500)
    assert not WC.taught_match("حجر", "حجار", loose=False)                            # her list word keeps its list match


def test_ws_35_a_word_she_says_back_is_new_and_a_short_word_never_is():
    turns = [{"t": 3079.0, "end": 3080.0, "who": "Medi", "text": "إدام؟"},
             {"t": 3080.5, "end": 3081.5, "who": "Amal", "text": "أها، الإدام."},
             {"t": 3082.0, "end": 3083.0, "who": "Medi", "text": "لا"},
             {"t": 3083.5, "end": 3084.0, "who": "Amal", "text": "لا."}]
    assert WC.said_back(turns, 0, "إدام") == "51:20"
    assert WC.said_back(turns, 2, "لا") is None


def test_ws_35_ghair_is_other_by_meaning_and_the_bare_verb_is_her_verb():
    words = [{"key": "8air", "arabic": "غير", "arabizi": "8eir", "english": "other/different/else"},
             {"key": "8aiyer", "arabic": "غيّر", "arabizi": "8ayyer", "english": "Change"},
             {"key": "hawa", "arabic": "هوا", "arabizi": "Hawa", "english": "Air"}]
    k = WC.Keys(words, catalog={"groups": []})
    assert k.lookup("غير")[1] == "unclear"
    anchor = {"id": "a", "lesson_date": "2026-10-09", "speaker": "Medi", "t_start": 1, "local_start": 1, "source_sha256": "h"}
    detail = {"turns": [{"t": 1972.0, "end": 1975.0, "who": "Medi", "text": "الهواء هون غير عن الهواء هناك"}], "grammar_errors": [], "vocab_errors": []}
    _, _, rows = WC.plan("2026-10-09", detail, [anchor], k, rulings=[])
    assert next(r for r in rows if r["word"] == "غير")["key"] == "8air"
    assert k.lookup("الهواء") == ("hawa", "one") and k.lookup("الهاوا") == ("hawa", "one")
    cat = {"groups": [{"key": "ana ba3mal", "type": "Verb", "keys": ["ana ba3mal"], "entries": [
        {"id": "p", "label": "Present", "word": "ba3mal", "arabic": "بعمل", "persons": [{"word": "Ana ba3mal", "arabic": "أنا بعمل"},
                                                                                     {"word": "i7na bne3mal", "arabic": "إحنا بنعمل"}]},
        {"id": "f", "label": "Future", "word": "ra7 a3mal", "arabic": "", "persons": []}]}]}
    kv = WC.Keys([{"key": "ana ba3mal", "arabic": "أنا بعمل", "arabizi": "Ana ba3mal", "english": "I do"}], catalog=cat)
    assert kv.lookup("نعمل") == ("ana ba3mal", "one") and kv.entry("ana ba3mal", "نعمل") == "f"
    assert kv.entry("ana ba3mal", "أعمله") == "f"


def test_ws_35_10_08_moments():
    rows = {(r["t"], r["word"]): r for r in WC.report("2026-10-08")}
    for t, w in (("09:44", "ديرت"), ("12:09", "ديري"), ("18:46", "سجر"), ("29:40", "بمطر"),
                 ("50:27", "حجور"), ("51:19", "إدام"), ("51:22", "الإدام"), ("03:24", "مالها")):
        assert rows[(t, w)]["state"] == "new", (t, w, rows[(t, w)])
    assert rows[("31:34", "الهاوا")]["state"] == "correct" and rows[("52:50", "غير")]["state"] == "correct"
    assert rows[("15:33", "أعمله")]["state"] == "correct" and rows[("50:27", "حجار")]["state"] == "correct"


# ---------------------------------------------------------------- GR-34 (Medi 2026-10-09 "I feel like you arent catching a lot of
# the correct grammar. Just for 10-8 go line by line for me and challenge every single grammar rule for each sentence." / "fix")
def test_gr_34_the_counter_reads_her_grammar_the_way_a_teacher_does():
    got = lambda txt: D.detect(txt)
    assert "A8" not in got("تاني") and "A8" not in got("مفضل")                  # a lone adjective agrees with nothing
    assert "B1" not in got("ديري باليك")                                        # بال 'mind' + your, not a b- verb
    assert "B5" not in got("خلينا نروح")                                        # 'let's' is a command
    assert "C3" not in got("أول يوم")                                           # أول is A13, not a comparative
    assert "D1" not in got("في عصافير") and "D1" in got("بنام في البيت")         # 'there is' vs 'in'
    assert "E3" not in got("يوم الخميس") and got("يوم الخميس").get("A2")       # a bare يوم; day + Thursday is possession
    assert got("يومي منيح").get("A4") == "يومي" and got("يومي منيح").get("C1")   # 'my day' + no word for 'is'
    assert "A4" not in got("طيارة") and "A4" not in got("ستة")                  # ة is not 'his'
    assert got("بلوزة سودا").get("A7") and got("الشارع قديمة").get("C1")
    assert "A7" not in got("الدرس مفضّل")                                        # el- on one side only: a sentence
    assert got("و بنطلون").get("C5") and got("والشمس").get("A1")
    assert got("نجوم").get("A9") and "A9" not in got("ثلاث")                    # her plural, never a number


def test_gr_34_a_reply_in_kind_is_his_own_and_an_echo_is_letter_for_letter():
    """Medi 2026-10-10 on 66:56 'شكراً. بشوفك. Bye.': "this isnt a repeat ... I replied to see you, with see you"."""
    turns = [{"t": 4013.0, "end": 4015.0, "who": "Amal", "text": "يلا بشوفك."},
             {"t": 4016.0, "end": 4018.0, "who": "Medi", "text": "شكراً. بشوفك. Bye."}]
    assert not WC.echo_of(turns, 1, 0)
    assert WC.judge_word(turns, 1, "بشوفك", "bashufak", lambda w: "bashufak", {})[0] == "independent"
    tw = [{"t": 3020.8, "end": 3026.0, "who": "Amal", "text": "شجر وحجر، صح. إيه شو plural حجر؟"},
          {"t": 3027.2, "end": 3028.0, "who": "Medi", "text": "حجار."}]
    assert not D._same_words(tw, 1, 0)                                            # his حجار is not her حجر


def test_gr_34_10_08_moments():
    u = json.load(open(os.path.join(ROOT, "docs", "data", "grammar-usage.json"), encoding="utf-8"))
    at = lambda b, t: any(x["date"] == "2026-10-08" and abs(x["t"] - t) < 1.5 for x in u["uses"].get(b, []))
    assert at("A4", 138.4) or at("A4", 138.0)                                   # 02:18 يومي منيح
    assert at("A9", 1281.7) or at("A9", 1282.0) or any(x["date"] == "2026-10-08" and x["mmss"] == "21:17" for x in u["uses"].get("A9", []))
    assert not any(x["date"] == "2026-10-08" and x["mmss"] in ("14:36", "14:47") for x in u["uses"].get("B5", []))   # خلينا
    assert any(x["date"] == "2026-10-08" and x["mmss"] == "66:56" for x in u["uses"].get("B1", []))                  # his بشوفك counts
