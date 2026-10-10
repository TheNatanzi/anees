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
