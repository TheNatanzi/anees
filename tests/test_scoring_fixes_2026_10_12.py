# -*- coding: utf-8 -*-
"""The 2026-10-11 audit of pills, English, transcript and math (plan/AUDIT-PILLS-ENGLISH-TRANSCRIPT-MATH-2026-10-11.md),
Medi 2026-10-11/12: "e5 should be added", "so please add to the work flow that anytime a correction is made it should
reevaluate the scoring", "the math seems off to me, the vocab and grammar correct", "fix all".

GR-37 grammar reads the line the page shows; every correction re-scores the lesson
WS-39 one judgment per word: hide only under the same word, never ✓ and ✗ at once, a word said twice in a line counts
      once, 'is it X?' is no use, no counted item without a pill, and the guard recomputes the header from the chips
PG-51 a grammar repeat pill is never empty
PG-52 the Vocab list's 'Errors' label splits the way the header counts
GR-38 D2 verb + its fixed preposition from her answers and her Doc
GR-39 his own mark that a line has a grammar mistake is the signal
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import transcript_marks as TM  # noqa: E402
import word_coverage as WC  # noqa: E402
import detect_grammar_usage as D  # noqa: E402
import medi_corrections as MC  # noqa: E402
import check_numbers as CN  # noqa: E402
import lesson_ledger as LL  # noqa: E402


def J(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return json.load(f)


def node(js):
    nb = CN.node_bin()
    return subprocess.run([nb, "-e", js], capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=True).stdout.strip()


# ------------------------------------------------------------------ GR-37
def test_gr_37_a_hand_added_use_lands_on_the_line_holding_its_words_as_the_page_shows_them():
    # 10-09 19:41 'Um, كم جبل' then 19:44 'في كاليفورنيا' (the engine wrote بي, TR-31): the D1 use written 'بي كاليفورنيا'
    # used to sit on 19:41 (the first line within 3 s); it belongs to 19:44
    T = [{"speaker": "Medi", "start": 1181.13, "end": 1182.76, "text": "Um, كم جبل", "engine": "Um, جبال",
          "heard": [{"engine_wrote": "جبال", "heard": "كم جبل"}]},
         {"speaker": "Medi", "start": 1184.77, "end": 1186.2, "text": "في كاليفورنيا.", "engine": "بي كاليفورنيا.",
          "heard": [{"engine_wrote": "بي", "heard": "في"}]}]
    at, hit = D.addition_line(T, {"t": "19:44", "bucket": "D1", "hit": "بي كاليفورنيا"})
    assert at is T[1] and hit == "في كاليفورنيا"
    at, hit = D.addition_line(T, {"t": 1181.13, "bucket": "E5", "hit": "كم جبل"})
    assert at is T[0] and hit == "كم جبل"


def test_gr_37_his_rule_should_be_added_is_a_right_use_never_a_slip():
    rows = [{"id": "u1", "lesson_date": "2026-10-09", "turn_t": 1181.13, "kind": "add", "target": {"k": "use", "rule": "e5", "said": "كم جبل"},
             "payload": {"k": "use", "use": True, "rule": "e5", "said": "كم جبل", "raw": "e5 should be added"}, "ts": "2026-10-11T21:00:00Z"}]
    assert MC.is_use_row(rows[0])
    adds = MC.use_additions(rows)
    assert adds and adds[0]["bucket"] == "E5" and adds[0]["rule"] == "GR-37"
    audit = []
    MC.apply_rows(audit, rows, answers={}, turns=[], rules=[])
    assert audit == []                                    # never a slip row
    out = json.loads(node("const P=require('./docs/js/correction-parse.js');console.log(JSON.stringify(P.parse('e5 should be added',{who:'Medi'}).items))"))
    assert out and out[0]["kind"] == "add" and out[0]["payload"]["use"] is True and out[0]["payload"]["rule"] == "E5"


def test_gr_37_every_correction_rescores_the_lesson_from_the_corrected_line():
    import importlib
    import amal_trigger as AT
    AT = importlib.reload(AT)            # tests/conftest.py empties SOURCES for other files
    order = [n for n, _ in AT.STEPS]
    # the use counter reads the corrected audit: after the audit build and Amal's rulings, before the lesson data
    assert order.index("full_audit_build") < order.index("apply_amal_audit_rulings") < order.index("detect_grammar_usage") < order.index("build_lessons_page_data")
    src = {s["id"]: s for s in AT.SOURCES}
    for sid in ("medi_corrections", "tutor_verify", "after_links", "pattern_review", "amal_rules_other"):
        steps = src[sid]["steps"]
        assert "detect_grammar_usage" in steps and "build_lessons_page_data" in steps, sid
    assert src["medi_corrections"]["steps"][0] == "pull_medi_corrections"
    # build_lessons_page_data rebuilds word coverage, the chips, the ledger and the review picker from the page's lines
    b = open(os.path.join(ROOT, "scripts", "build_lessons_page_data.py"), encoding="utf-8").read()
    for piece in ("WC.refresh(", "TM.build(", "LL.build(", "review_picker.run_all()"):
        assert piece in b
    h = open(os.path.join(ROOT, "scripts", "hourly_lessons.py"), encoding="utf-8").read()
    assert "('detect_grammar_usage.py', 'build_amal_review.py', 'build_lessons_page_data.py'" in h


def test_gr_37_end_to_end_10_09_19_41_shows_e5_and_no_d1():
    d = J("docs", "data", "lessons", "2026-10-09.json")
    i = next(k for k, u in enumerate(d["turns"]) if abs(u["t"] - 1181.13) < 0.05)
    assert "كم جبل" in d["turns"][i]["text"]
    shown = [c for c in d["tmarks"][str(i)]["c"] if not c.get("hide")]
    assert any(c.get("k") == "grammar" and c.get("rule") == "E5" and c.get("s") == "correct" for c in shown)
    assert not any(c.get("rule") == "D1" for c in d["tmarks"][str(i)]["c"])
    # the D1 use sits on 19:44 'في كاليفورنيا' and reads the shown text
    j = next(k for k, u in enumerate(d["turns"]) if abs(u["t"] - 1184.77) < 0.05)
    d1 = [c for c in d["tmarks"].get(str(j), {}).get("c", []) if c.get("rule") == "D1"]
    assert d1 and all("بي" not in (c.get("said") or "") for c in d1)
    # his note row 'e5' is no vocab slip on any page
    assert not any((e.get("wrong") or "") == "e5" for e in d.get("vocab_errors") or [])


# ------------------------------------------------------------------ WS-39
def test_ws_39_a_chip_hides_only_under_a_chip_about_the_same_words():
    turns = [{"t": 1181.1, "who": "Medi", "text": "Um, كم جبل"}]
    tm = {"0": {"c": [{"id": "r1", "k": "grammar", "s": "correct", "rule": "E5", "said": "كم جبل"},
                      {"id": "n1", "k": "na", "s": "na", "label": "vocab", "ar": "كم", "why": "كم: unclear"},
                      {"id": "w1", "k": "vocab", "s": "repeat", "ar": "جبل", "why": "repeat"}], "u": []}}
    out = TM.one_per_word(tm, turns)["0"]["c"]
    shown = {c["id"] for c in out if not c.get("hide")}
    assert "r1" in shown and "w1" in shown                         # E5 ✓ is about كم جبل, not only جبل
    assert next(c for c in out if c["id"] == "n1")["hide"] == "r1"  # the grey كم is about a word of E5
    # 10-08 13:19 'لازم أدير': the ✓ on لازم never hides under ★ أدير (two words joined by a two-word grammar chip)
    turns = [{"t": 799.0, "who": "Medi", "text": "لازم أدير"}]
    tm = {"0": {"c": [{"id": "v1", "k": "vocab", "s": "correct", "ar": "لازم", "tok": "لازم"},
                      {"id": "x1", "k": "vocab", "s": "new", "ar": "أدير"},
                      {"id": "r1", "k": "grammar", "s": "correct", "rule": "B2", "said": "لازم أدير"}], "u": []}}
    out = TM.one_per_word(tm, turns)["0"]["c"]
    assert not next(c for c in out if c["id"] == "v1").get("hide")
    # a wrong still beats a right on the same word, and the hidden one is listed on it
    tm = {"0": {"c": [{"id": "v1", "k": "vocab", "s": "correct", "ar": "عيان"}, {"id": "x1", "k": "grammar", "s": "wrong", "said": "عيان"}], "u": []}}
    out = TM.one_per_word(tm, [{"t": 1, "who": "Medi", "text": "خطيبتي شوي عيان"}])["0"]["c"]
    assert [c["id"] for c in out if not c.get("hide")] == ["x1"] and out[1]["also"][0]["k"] == "vocab"


def test_ws_39_a_line_with_no_end_runs_to_the_next_line():
    turns = [{"t": 28.38, "who": "Medi", "text": "عالي كتير so..."}, {"t": 29.78, "end": 30.28, "who": "Amal", "text": "علي."},
             {"t": 34.88, "end": 36.32, "who": "Medi", "text": "Um,"}]
    assert TM.place(turns, 30.66, "Medi", "عالي / عالية")[0] == 0     # 10-10 00:31: counted with no pill before


def test_ws_39_one_utterance_is_never_right_and_wrong():
    turns = [{"t": 1625.0, "end": 1627.0, "who": "Medi", "text": "غادة؟"}]
    detail = {"turns": turns,
              "vocab_correct": [{"event_id": "e1", "kind": "correct", "t": 1625.5, "word_key": "bukra", "arabic": "غدا", "tok": "غادة"}],
              "vocab_errors": [{"event_id": "e2", "kind": "wrong", "t": 1625.6, "word_key": "8Abe", "arabic": "غابة", "wrong": "غادة"}],
              "not_errors": [], "grammar_errors": [], "grammar_not_counted": []}
    led, act = LL.build("2026-10-09", detail, {}, {}, set(), lambda b: False)
    v = {m["id"]: m["verdict"] for m in led["marks"]}
    assert v["wb:e1"] == "folded" and v["wb:e2"] == "wrong"
    assert led["counts"]["words"]["right"] == 0 and led["counts"]["words"]["wrong"] == 1
    assert any(c["kind"] == "C5" for c in led["conflicts"]) and ("vocab_correct", "wb:e1") in [(a, b) for a, b, _, _ in act["move"]]
    # the readers' slip (one reader, so the tutor is asked yes/no, LS-11): while her answer is open it counts ONCE, as the slip
    rd = {"source": "audit-2026-09-26", "audit_uid": "FA-743054ec", "t": 1625, "kind": "wrong", "wrong": "غادة", "fix": "غابة", "tier": 1,
          "confidence": "medium", "signal": "prompt-then-fix", "on_sheet": True, "sheet_key": "8Abe", "arabic": "غابة"}
    d2 = dict(detail, vocab_errors=[rd])
    led, act = LL.build("2026-10-09", d2, {}, {}, set(), lambda b: False)
    c = next(c for c in led["conflicts"] if c["kind"] == "C1q")
    assert c["id"] in led["needs_medi"] and c.get("one_judgment")                    # still her question
    assert led["counts"]["words"]["right"] == 0 and led["counts"]["words"]["wrong"] == 1
    # her 'nothing was wrong' drops the slip and gives the right back
    led, act = LL.build("2026-10-09", d2, {}, {}, set(), lambda b: False, rulings={c["id"]: {"conflict": c["id"], "answer": "none", "by": "amal"}})
    assert led["counts"]["words"]["right"] == 1 and led["counts"]["words"]["wrong"] == 0


def test_ws_39_a_scored_word_on_no_line_is_not_counted():
    detail = {"turns": [{"t": 10.0, "end": 11.0, "who": "Medi", "text": "مرحبا"}],
              "vocab_correct": [{"event_id": "e1", "kind": "correct", "t": 500.0, "word_key": "nafs", "arabic": "نفس", "tok": "nafs"}],
              "vocab_errors": [], "not_errors": [], "grammar_errors": [], "grammar_not_counted": []}
    led, act = LL.build("2026-10-10", detail, {}, {}, set(), lambda b: False)
    assert led["marks"][0]["verdict"] == "not-scored" and led["counts"]["words"]["right"] == 0


def test_ws_39_the_same_word_twice_in_one_line_counts_once_and_asking_is_no_use():
    turns = [{"t": 832.0, "end": 835.0, "who": "Medi", "text": "تلاقت؟ تلاقت؟"},
             {"t": 2936.18, "end": 2938.0, "who": "Medi", "text": "So is it اكتبي؟ اكتبي؟"}]
    ev = lambda i, t, w, k: {"id": i, "t_start": t, "text": w, "word_key": k, "assessment": "independent", "speaker": "Medi"}   # noqa: E731
    evs = [ev("a", 832.2, "تلاقت", "talAt"), ev("b", 833.4, "تلاقت", "talAt"), ev("c", 2937.0, "اكتبي", "ektebi"), ev("d", 2937.6, "اكتبي", "ektebi")]
    patches = {}
    WC.asked_events("2026-10-10", turns, [], [], patches, evs)
    WC.said_twice("2026-10-10", turns, [], [], patches, evs)
    assert set(patches) == {"b", "c", "d"}
    assert "same line" in patches["b"]["changes"]["reason"] and patches["c"]["changes"]["rule"] == "WS-39"
    assert WC.asked_forms("Is it فجر or سجر؟") == {WC.core("فجر"), WC.core("سجر")}
    assert WC.asked_forms("من أول اللعبة. Or would it be أولى؟") == {WC.core("أولى")}
    assert not WC.asked_forms("تلاقت؟ تلاقت؟")


def test_ws_39_the_guard_recomputes_the_header_from_the_chips():
    lesson = {"date": "D", "words": {"right": 2, "partial": 0, "wrong": 1}, "grammar": {"mistakes": 1, "uses": 3}}
    detail = {"turns": [{"t": 1, "who": "Medi", "text": "x"}],
              "tmarks": {"0": {"c": [{"id": "v1", "k": "vocab", "s": "correct", "ar": "a", "words": [{"ar": "a"}, {"ar": "b"}]},
                                     {"id": "v2", "k": "vocab", "s": "correct", "ar": "b", "hide": "v1"},
                                     {"id": "v3", "k": "vocab", "s": "wrong", "ar": "c"},
                                     {"id": "r1", "k": "grammar", "s": "correct", "rule": "A1", "also": [{"k": "grammar", "s": "correct", "rule": "A1"}]},
                                     {"id": "r2", "k": "grammar", "s": "correct", "rule": "A1", "hide": "r1"},
                                     {"id": "x1", "k": "grammar", "s": "wrong", "rule": "A1"}]}}}
    res = CN.chip_checks(lesson, detail, {"A1": {"scored": True}})
    assert all(ok for _, ok, _ in res), [x for x in res if not x[1]]
    detail["tmarks"]["0"]["c"][4]["hide"] = "nope"                  # a counted chip hidden under no pill
    res = dict((n, ok) for n, ok, _ in CN.chip_checks(lesson, detail, {"A1": {"scored": True}}))
    assert res["D chips: every counted item has a pill"] is False
    lesson["words"]["right"] = 3                                     # the header drifts from the chips
    res = dict((n, ok) for n, ok, _ in CN.chip_checks(lesson, detail, {"A1": {"scored": True}}))
    assert res["D chips: words right"] is False


def test_ws_39_every_lesson_header_equals_its_chips():
    L = J("docs", "data", "lessons.json")["lessons"]
    bad = []
    for x in L:
        led = J("data", "lesson-work", "ledger", x["date"] + ".json")
        for name, ok, detail in CN.chip_checks(x, J("docs", "data", "lessons", x["date"] + ".json"), led["counts"]["grammar"]["by_rule"]):
            if not ok:
                bad.append(detail)
    assert not bad, bad[:5]


def test_ws_39_a_merged_grammar_pill_says_how_many_uses_it_stands_for():
    src = open(os.path.join(ROOT, "docs", "js", "lessons-page.js"), encoding="utf-8").read()
    body = src[src.index("function mergeCorrect("):src.index("function sentences(")]
    js = ("const mergeCorrect=new Function(%s+'; return mergeCorrect;')();const T=require('./docs/js/transcript-marks.js');"
          "const out=mergeCorrect([{id:'a',k:'grammar',s:'correct',rule:'A1',name:'el- (the)'},{id:'b',k:'grammar',s:'correct',rule:'A1',name:'el- (the)'}]);"
          "const shown=out.filter(c=>!c.hide);console.log(JSON.stringify([shown.length,shown[0].n,T.chipModel(shown[0],null).main]))") % json.dumps(body)
    n, cnt, main = json.loads(node(js))
    assert n == 1 and cnt == 2 and main.endswith("×2")


# ------------------------------------------------------------------ PG-51
def test_pg_51_a_grammar_repeat_pill_is_never_empty():
    r = {"t": 1224.2, "said": "غير الشمس?", "repeat": True, "rule": "GR-28",
         "why": "repeat of the line Amal just fixed (20:02): one moment with the slip, not a new use (GR-28, Medi 2026-10-05)"}
    assert TM.repeated_rule(r, [{"t": 1203.0, "bucket": "A16"}, {"t": 1300.0, "bucket": "A1"}]) == "A16"
    assert TM._his_words("Oh, is it, is it، is it عصافير؟") == "عصافير"
    m = json.loads(node("const T=require('./docs/js/transcript-marks.js');console.log(JSON.stringify(["
                        "T.chipModel({k:'grammar',s:'repeat',rule:null,said:'',why:'he quotes the tutor'},null).main,"
                        "T.chipModel({k:'grammar',s:'repeat',rule:'A16',name:'8eir',said:'غير الشمس'},null).main]))"))
    assert m[0] == "he quotes the tutor" and m[1] == "A16 8eir · غير الشمس"
    for date in ("2026-10-08", "2026-10-09", "2026-10-10"):
        d = J("docs", "data", "lessons", date + ".json")
        empty = [c for v in d["tmarks"].values() for c in v["c"] if c.get("k") == "grammar" and c.get("s") == "repeat"
                 and not c.get("rule") and not c.get("said") and not c.get("why")]
        assert not empty, (date, empty[:2])


# ------------------------------------------------------------------ PG-52
def test_pg_52_the_errors_label_splits_like_the_header():
    src = open(os.path.join(ROOT, "docs", "js", "lessons-page.js"), encoding="utf-8").read()
    body = src[src.index("function errorsSplit("):src.index("// Medi 2026-09-26: a switch next to")]
    out = node("const f=new Function(%s+'; return errorsSplit;')();console.log(f({vocab_errors_split:{wrong:4,half:4,off_list:3}}))" % json.dumps(body))
    assert out == "4 ✗ · 4 ◐ asked · 3 not on her list"
    for x in J("docs", "data", "lessons.json")["lessons"]:
        s, c = x["counts"].get("vocab_errors_split"), x["counts"]
        if s is None:
            continue
        assert s["wrong"] + s["half"] + s["off_list"] == c["vocab_errors"]
        assert s["wrong"] == x["words"]["wrong"], x["date"]


# ------------------------------------------------------------------ GR-38
def test_gr_38_verb_and_its_fixed_preposition_from_her_answers_and_her_doc():
    vp = D.VERB_PREPS
    assert {"fi", "bi"} <= vp[D._vstem("أنا بنبسط")]          # her answer fi + his 'Banbese6 always takes bi'
    assert "min" in vp[D._vstem("أنا بطلب")]                  # her Doc 'Ana ba6lub (min)'
    hit = lambda t: D.detect(t).get("D2")                        # noqa: E731
    assert hit("أنا بنبسط بالشاطئ.") == "بنبسط بالشاطئ"           # 10-09 21:34
    assert hit("أنا راح أطلب، إلها") == "أطلب إلها"                # 10-09 05:09: the attempt the D2 slip pairs with
    assert hit("انبسطت في الصيف") and hit("بخاف من الكلب")
    assert not hit("أنا بنبسط بحب") and not hit("أنا بحب كاليفورنيا")


# ------------------------------------------------------------------ GR-39
def test_gr_39_his_own_grammar_mark_is_the_signal_and_one_moment_is_one_slip():
    add = {"id": "g1", "lesson_date": "2026-10-09", "turn_t": 3517.23, "kind": "add", "ts": "2026-10-12T19:00:00Z",
           "target": {"k": "grammar", "said": "سؤالي آخر", "rule": "A15"},
           "payload": {"k": "grammar", "wrong": "سؤالي آخر", "right": "سؤالي الأخير", "rule": "A15", "turn_end": 3531.62}}
    rows = []
    rep = MC.apply_rows(rows, [add], answers={}, turns=[], rules=[])
    assert rows[0]["kind"] == "grammar" and rows[0]["bucket"] == "A15" and rows[0]["rule"] == "GR-39" and not rep["tier_b"]
    # the same moment already counted (her fix at 05:10, his note at 05:00): his row confirms it, never a second slip
    rows = [{"uid": "FA-cc5d35a6", "date": "2026-10-09", "t": "05:10", "kind": "grammar", "bucket": "D2", "wrong": "أطلب إلها"}]
    d2 = dict(add, id="g2", turn_t=300.0, target={"k": "grammar", "said": "أطلب إلها", "rule": "D2"},
              payload={"k": "grammar", "wrong": "أطلب إلها", "right": "أطلب منها", "rule": "D2", "turn_end": 313.38})
    MC.apply_rows(rows, [d2], answers={}, turns=[], rules=[])
    assert len(rows) == 1 and rows[0]["medi_corrections"] == ["g2"]
    # a note written on one line about another: the slip sits on the line it names (payload.at), the row keeps his line
    rows = []
    MC.apply_rows(rows, [dict(add, id="g4", turn_t=3503.51, payload=dict(add["payload"], at=3517.23, at_end=3531.62, turn_end=None))],
                  answers={}, turns=[], rules=[])
    assert rows[0]["t"] == "58:37" and rows[0]["kind"] == "grammar"
    # without a rule it waits (a proposed rule, GR-18); a vocab mark keeps the tier-B path (PR-17)
    rows = []
    rep = MC.apply_rows(rows, [dict(add, id="g3", target={"k": "grammar", "said": "x"}, payload={"k": "grammar", "wrong": "x"})], answers={}, turns=[], rules=[])
    assert rows[0]["kind"] == "grammar-B" and rep["tier_b"] == ["g3"]


def test_gr_39_10_09_his_marks_are_counted_slips():
    a = J("data", "full-audit-2026-09-26.json")
    mine = [r for r in a["sweep_compat"]["rows"] if r.get("date") == "2026-10-09" and str(r.get("correction") or "").startswith("chat-20261012-")]
    assert {r.get("bucket") for r in mine} >= {"A15", "A10", "D1"}


def test_pg_53_research_papers_section_shows_the_public_case_study():
    """PG-53 (Medi 2026-10-19): 'For ai reports we need to start building out a section for our experiments and results like a
    research paper'. The featured paper is the PUBLIC version: roles, no lesson excerpts (the tutor's consent is pending)."""
    import io, json, os, re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = json.load(io.open(os.path.join(root, 'docs', 'data', 'ai_reports.json'), encoding='utf-8'))
    papers = [r for r in d['reports'] if r.get('featured')]
    assert papers and all(os.path.exists(os.path.join(root, 'docs', l['url'])) for p in papers for l in p['links'])
    html = io.open(os.path.join(root, 'docs', 'ai-reports.html'), encoding='utf-8').read()
    assert 'id="ar-papers"' in html and 'Research papers' in html
    md = io.open(os.path.join(root, 'plan', 'ANEES-CASE-STUDY-2026-10-19.md'), encoding='utf-8').read()
    assert not re.search(r'\b(Medi|Amal)\b', md)
    assert not re.search(r'[؀-ۿ]{3,}', md)                       # no Arabic lesson words


def test_pg_54_theme_switch_keeps_its_shape_when_its_stylesheet_fails():
    """PG-54 (Medi 2026-10-19, screenshot of three big grey Light / Dark / Phone boxes): theme.js injects a minimal inline
    style before css/theme-switch.css, so the slider never renders as bare buttons with their labels showing."""
    import io, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js = io.open(os.path.join(root, 'docs', 'js', 'theme.js'), encoding='utf-8').read()
    assert "fb.setAttribute('data-sabz-theme-fallback', '')" in js
    assert '.sabz-theme-name{position:absolute;width:1px;height:1px;overflow:hidden' in js           # labels stay hidden
    assert js.index('data-sabz-theme-fallback') < js.index("link.href = base + 'css/theme-switch.css'")


def test_pg_55_research_paper_opens_with_app_styled_pictures():
    """PG-55 (Medi 2026-10-19: 'match the infographics to the studies ... flows naturally into the app'): the case study opens with
    picture chapters in the app's own colours (CSS variables, no fixed hex in the story), each linking into the app and the
    paper; every in-page link lands; the public story names no one and holds no Arabic lesson words."""
    import io, json, os, re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    story = io.open(os.path.join(root, 'plan', 'ANEES-CASE-STUDY-2026-10-19.story.html'), encoding='utf-8').read()
    assert not re.search(r'\b(Medi|Amal)\b', story) and not re.search(r'[؀-ۿ]{3,}', story)
    assert not re.search(r'#[0-9A-Fa-f]{6}', story)                               # colours come from the app's theme
    page = io.open(os.path.join(root, 'docs', 'reports', 'anees-case-study-2026-10-19.html'), encoding='utf-8').read()
    assert page.count('class="rs-ch"') >= 10 and 'id="paper"' in page and 'In the app:' in page
    ids = set(re.findall(r'id="([^"]+)"', page))
    assert all(a in ids for a in re.findall(r'href="#([^"]+)"', page))
    d = json.load(io.open(os.path.join(root, 'docs', 'data', 'ai_reports.json'), encoding='utf-8'))
    paper = [r for r in d['reports'] if r.get('featured')][0]
    assert paper['story_html'] and paper['bars'] and all(c['url'].split('#')[1] in ids for c in paper['chapters'])



def test_pr_29_judge_panel_decides_the_slips(tmp_path, monkeypatch):
    """PR-29 (Medi 2026-10-21 'Switch now'; paid Gemini key with a 20 USD a month cap): the judge panel groups the readers'
    flags, keeps a candidate at mean p(slip) >= 0.60 of Opus + Argon, and never calls Gemini past 90 % of the cap."""
    import json, os, sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "scripts"))
    import judge_panel as JP
    assert JP.THRESHOLD == 0.60 and JP.CAP_USD == 20.0 and [j[2] for j in JP.JUDGES] == ["claude-opus-5-5", "gemini-4-argon"]
    pool = {"r1": [{"t": "01:00", "kind": "grammar", "signal": "recast", "wrong": "a", "right": "b"},
                   {"t": "02:00", "kind": "vocab-A", "signal": "asked", "wrong": "c", "right": "d"}],
            "r2": [{"t": "01:10", "kind": "grammar", "signal": "explicit-no", "wrong": "a", "right": "b", "why": "longer reason"}]}
    c = JP.candidates(pool)
    assert len(c) == 1 and c[0]["readers"] == ["r1", "r2"]                 # same family within 15 s = one candidate; 'asked' is dropped
    assert JP.p_slip({"verdict": "slip", "confidence": 70}) == 0.7 and JP.p_slip({"verdict": "not", "confidence": 70}) == 0.30000000000000004
    monkeypatch.setattr(JP, "SPEND", str(tmp_path / "spend.json"))
    json.dump({"months": {JP.month(): 17.9}}, open(JP.SPEND, "w"))
    assert not JP.can_spend("gemini-4-argon")                               # 17.9 + ~0.25 would pass 18 (90 % of 20)
    json.dump({"months": {JP.month(): 5.0}}, open(JP.SPEND, "w"))
    assert JP.can_spend("gemini-4-argon")
    src = open(os.path.join(root, "scripts", "review_lesson.py"), encoding="utf-8").read()
    assert src.index('"settle", d)') < src.index("judge_panel.py") < src.index('full_audit_build.py")')
