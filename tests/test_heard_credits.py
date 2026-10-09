# -*- coding: utf-8 -*-
"""WS-29 (Medi 2026-10-09 "I should get credit for knowing 'alayhi salmik'", "Merhaba should count as a vocab"): the Doc
words of his own corrections are Word Bank events; his "should count" rules on an event the matcher already had.
PR-22 (his 10-08 notes): the note reader sees the lines around and puts each fix on the line it changes."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import heard_credits as HC  # noqa: E402
import correction_parse as CP  # noqa: E402

WORDS = [{"key": "kIfek", "arabic": "كيفك؟", "arabizi": "keefek?"}, {"key": "kIfak", "arabic": "كيفك؟", "arabizi": "keefak?"},
         {"key": "alah isalmek", "arabic": "الله يسلمك", "arabizi": "Allah ysalmek"}, {"key": "mnIh", "arabic": "منيح", "arabizi": "mneeh"},
         {"key": "marhaba", "arabic": "مرحبا", "arabizi": "marhaba"}]
ANCHOR = {"id": "a1", "lesson_date": "2026-10-08", "speaker": "Medi", "source_id": "s", "source_sha256": "h", "version": "v"}
TURNS = [{"t": 14.6, "who": "Amal", "text": "أهلًا. كيفك؟"}, {"t": 42.69, "who": "Medi", "text": "Defect."}, {"t": 45.5, "who": "Amal", "text": "أه، تمام. أنت كيفك؟"}]


def row(**k):
    r = {"date": "2026-10-08", "t": 104.15, "who": "Medi", "by": "medi", "engine_wrote": "Yomi, me", "heard": "يومي منيح", "turn_end": 105.25, "correction": "c1"}
    r.update(k)
    return r


def test_ws_29_his_heard_doc_word_is_credited_and_an_engine_word_is_not_credited_twice():
    out = HC.build(rows=[row()], words=WORDS, evidence=[ANCHOR], lessons={"2026-10-08": TURNS})
    assert [(x["event"]["word_key"], x["event"]["assessment"]) for x in out] == [("mnIh", "independent")]
    assert out[0]["anchor_id"] == "a1" and out[0]["event"]["heard_credit"] is True
    # a machine listen (the Gemini re-hear) never adds a credit; the tutor's lines neither
    assert HC.build(rows=[row(by="gemini-rehear"), row(who="Amal")], words=WORDS, evidence=[ANCHOR], lessons={"2026-10-08": TURNS}) == []


def test_ws_29_a_word_she_said_in_the_15_s_before_is_practice_and_his_row_names_the_gendered_form():
    r = row(t=42.69, turn_end=43.25, engine_wrote="Defect", heard="كيفِك", word_key="kIfek")
    out = HC.build(rows=[r], words=WORDS, evidence=[ANCHOR], lessons={"2026-10-08": TURNS})
    assert [(x["event"]["word_key"], x["event"]["assessment"]) for x in out] == [("kIfek", "independent")]   # her كيفك was 28 s before
    near = [{"t": 35.0, "who": "Amal", "text": "كيفك؟"}]
    out = HC.build(rows=[r], words=WORDS, evidence=[ANCHOR], lessons={"2026-10-08": near})
    assert out[0]["event"]["assessment"] == "helped"
    # without his word_key the gendered form is ambiguous: no credit (his self-fixed keefak to a woman got none)
    assert HC.build(rows=[row(t=42.69, engine_wrote="Defect", heard="كيفك")], words=WORDS, evidence=[ANCHOR], lessons={"2026-10-08": TURNS}) == []


def test_ws_29_should_count_on_a_word_the_matcher_had_patches_that_event():
    ev = dict(ANCHOR, id="e-marhaba", word_key="marhaba", text="مرحبا.", t_start=10.37, t_end=10.71, assessment="unresolved",
              reason="Isolated production; insufficient evidence of independent contextual success", row_id="r0")
    r = row(t=10.37, turn_end=10.71, engine_wrote="مرحبا", heard="مرحبا", credit="independent", word_key="marhaba", quote="Merhaba should count as a vocab")
    P = HC.patches(rows=[r], evidence=[ev])
    assert P["e-marhaba"]["changes"]["assessment"] == "independent" and P["e-marhaba"]["expected"]["assessment"] == "unresolved"
    assert HC.build(rows=[r], words=WORDS, evidence=[ANCHOR, ev], lessons={"2026-10-08": TURNS}) == []   # no second event


def test_pr_22_the_note_reader_puts_each_fix_on_the_line_it_changes_and_reads_credit_and_not_use():
    turns = [{"t": 308.73, "who": "Medi", "text": "Elion,"}, {"t": 311.35, "who": "Medi", "text": "ion el,"}, {"t": 313.71, "who": "Medi", "text": "ion el khamis,"}]
    note = {"id": "n1", "lesson_date": "2026-10-08", "turn_t": 308.73, "turn_who": "Medi", "payload": {"line": "Elion,", "turn_end": 309.27}}
    ans = {"items": [{"kind": "text", "engine_wrote": "Elion", "heard": "Elyoam", "at": "5:08"},
                     {"kind": "text", "engine_wrote": "ion el khamis", "heard": "yoam el 5amees", "at": "5:13"},
                     {"kind": "text", "engine_wrote": "not on that line", "heard": "x", "at": "5:11"}]}
    items = CP.items_from_ai(ans, note, turns=turns)
    assert [(p["engine_wrote"], p.get("at")) for k, t, p in items] == [("Elion", 308.73), ("ion el khamis", 313.71)]
    rows = CP.rows_from_items(note, items)
    assert [r["turn_t"] for r in rows] == [308.73, 313.71] and all("at" not in r["payload"] for r in rows)
    ctx = CP.context_lines(note, turns=turns)
    assert ctx.splitlines()[0] == "[5:08 Medi] Elion," and len(ctx.splitlines()) == 3
    credit = CP.items_from_ai({"items": [{"kind": "credit", "word": "Merhaba"}]},
                              {"lesson_date": "2026-10-08", "turn_t": 10.37, "turn_who": "Medi", "payload": {"line": "مرحبا."}}, turns=[])
    assert credit == [("text", {"word": "مرحبا"}, {"engine_wrote": "مرحبا", "heard": "مرحبا", "credit": "independent", "from": "ai"})]
    prompt = open(os.path.join(ROOT, "scripts", "correction_parse_prompt.md"), encoding="utf-8").read()
    assert "{context}" in prompt and '"kind": "credit"' in prompt and 'never "add"' in prompt
