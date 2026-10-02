# -*- coding: utf-8 -*-
"""AM-16 (Medi 2026-10-02: "keep it on your system that mumtaz is an old word and wait for her to add it to the doc.
Keep a tab of what she said shes going to add" + "yes have her tap that its old"): an Anees-side old/new mark (never the
Doc), Amal's Add as NEW / Add as OLD choice on the Tutor hub card, the promised list (Waiting -> In the Doc), and
Flashcards never counting an OLD word as NEW when the Doc import first sees it. Fake Doc + fake database only."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import amal_new_words as N
import import_vocab as IV
import word_marks as WM

MARKS = {"marks": [{"arabic": "ممتاز", "arabizi": "mumtaz", "mark": "old", "by": "medi", "date": "2026-10-02", "lesson": "2026-10-01"}]}
V = [{"date": "2026-10-01", "key": "ممتاز", "verdict": "new", "arabic": "ممتاز", "english": "excellent", "t": 100.0},
     {"date": "2026-10-01", "key": "laffe", "verdict": "new", "arabic": "لفة", "arabizi": "laffe", "english": "a drive", "t": 200.0}]
NO_DOC = {"items": [{"key": "shanta", "arabizi": "Shanta", "arabic": "شنطة", "aliases": []},
                    {"key": "malaf", "arabizi": "Malaf", "arabic": "ملف", "aliases": []}]}       # لف is a stem here, not her word
DOC_WITH = {"items": NO_DOC["items"] + [{"key": "mumtAz", "arabizi": "Mumtaaz", "arabic": "ممتاز", "aliases": []}]}
ID = N.item_id("2026-10-01", "ممتاز")
LAFFE = N.item_id("2026-10-01", "laffe")


def test_AM_16_mumtaz_marked_old_by_medi_is_a_hint_not_a_choice_for_amal():
    out = N.build(V, taps={}, today="2026-10-02T09:00", marks=MARKS, doc=NO_DOC)
    it = next(i for i in out["items"] if i["key"] == "ممتاز")
    assert it["status"] == "open" and it["tap"] is None                     # nothing pre-selected
    assert it["hint"] == "Medi already knows this — old word" and it["medi_mark"] == "old"
    p = next(p for p in out["promised"] if p["id"] == ID)
    assert p["state"] == "awaiting_amal" and p["marks"] == {"medi": "old", "amal": None}
    assert not any(p["id"] == LAFFE for p in out["promised"])              # no tap, no mark: not on the promised list


def test_AM_16_her_old_tap_puts_it_on_the_promised_list_and_the_doc_import_moves_it_to_in_the_doc():
    taps = {ID: ("newword_add_old", "2026-10-02T12:00:00Z"), LAFFE: ("newword_add_new", "2026-10-02T12:01:00Z")}
    a = N.build(V, taps=taps, today="2026-10-02T13:00", marks=MARKS, doc=NO_DOC)
    p = next(p for p in a["promised"] if p["id"] == ID)
    assert (p["state"], p["age"], p["age_by"], p["marks"]) == ("waiting", "old", "amal", {"medi": "old", "amal": "old"})
    assert next(p for p in a["promised"] if p["id"] == LAFFE)["state"] == "waiting"      # a stem (ملف) is not her word
    b = N.build(V, taps=taps, previous=a, today="2026-10-05T13:00", marks=MARKS, doc=DOC_WITH)   # she added it to the Doc
    p = next(p for p in b["promised"] if p["id"] == ID)
    assert p["state"] == "in_doc" and p["in_doc_since"] == "2026-10-05"
    c = N.build(V, taps=None, previous=b, today="2026-10-09T13:00", marks=MARKS, doc=DOC_WITH)   # offline rebuild keeps all
    p = next(p for p in c["promised"] if p["id"] == ID)
    assert p["state"] == "in_doc" and p["in_doc_since"] == "2026-10-05" and p["age"] == "old"
    # her NEW tap beats Medi's old mark (ai_rules A2); both are kept
    n = N.build(V, taps={ID: ("newword_add_new", "t")}, today="x", marks=MARKS, doc=NO_DOC)
    p = next(p for p in n["promised"] if p["id"] == ID)
    assert (p["age"], p["age_by"], p["marks"]) == ("new", "amal", {"medi": "old", "amal": "new"})


class FakeDb:
    def __init__(self, rows):
        self.rows = {r["key"]: dict(r) for r in rows}
        self.patches = []

    def select(self, table, params=None, **kw):
        return [{"key": k, "row_hash": r.get("row_hash"), "active": r["active"], "first_seen": r.get("first_seen")} for k, r in self.rows.items()]

    def upsert(self, table, rows, on="", **kw):
        for r in rows:
            self.rows.setdefault(r["key"], {"first_seen": "2026-10-05T17:00:00+00:00"}).update(r)

    def rest(self, method, table, params=None, body=None, **kw):
        assert method == "PATCH"
        self.patches.append((params["key"][3:], body))
        self.rows[params["key"][3:]].update(body)


DOC_MD = ("# Latest Topic\n\n|  |  |  |  |\n| :-: | :-: | :-: | :-: |\n| **Transliteration** | **Plural** | **Arabic** | **English** |\n"
          "| Shanta | shanaat | شنطة | Bag |\n" + "".join("| Raqam%d | — | رقم%s | Number %d |\n" % (i, "ا" * i, i) for i in range(1, 9)))


def test_AM_16_mumtaz_marked_old_arriving_in_the_doc_is_not_new_on_flashcards(tmp_path):
    before, _ = IV.to_words(IV.parse_markdown(DOC_MD))
    fake = FakeDb([{**w, "active": True, "first_seen": "2026-09-05T10:00:00+00:00"} for w in before])
    built = N.build(V, taps={ID: ("newword_add_old", "t")}, today="x", marks=MARKS, doc=NO_DOC)
    ages = WM.resolved_ages(MARKS, built)
    after, _ = IV.to_words(IV.parse_markdown(DOC_MD + "| Mumtaaz | — | ممتاز | Excellent |\n| Jdeed | — | جديد | New |\n"))
    res = IV.sync(after, db=fake, min_words=1, ages=ages)
    mk = next(w["key"] for w in after if w["arabic"] == "ممتاز")
    jd = next(w["key"] for w in after if w["arabic"] == "جديد")
    assert res["inserted"] == 2 and res["old_marked"] == [{"key": mk, "by": "amal"}]
    assert fake.rows[mk]["first_seen"] == WM.OLD_FIRST_SEEN                  # old: on the NEW_SINCE day
    assert fake.rows[jd]["first_seen"] == "2026-10-05T17:00:00+00:00"        # every other word untouched
    assert all(k == mk for k, _ in fake.patches)
    # Flashcards' rule (docs/js/cards-core.js curriculum): NEW = first_seen day after NEW_SINCE
    core = open(os.path.join(REPO, "docs", "js", "cards-core.js"), encoding="utf-8").read()
    assert re.search(r"const NEW_SINCE = '(\d{4}-\d\d-\d\d)'", core).group(1) == WM.NEW_SINCE
    is_new = lambda fs: fs[:10] > WM.NEW_SINCE
    assert not is_new(fake.rows[mk]["first_seen"]) and is_new(fake.rows[jd]["first_seen"])
    # Medi's mark alone (no tap of hers yet) also keeps it old; a second import changes nothing more
    res2 = IV.sync(after, db=fake, min_words=1, ages=WM.resolved_ages(MARKS, {"items": []}))
    assert res2["old_marked"] == []
    # the import writes the event next to the mark (append-only), never into her Doc
    p = tmp_path / "marks.json"
    p.write_text(json.dumps(MARKS, ensure_ascii=False), encoding="utf-8")
    IV.record_old(after, res["old_marked"], path=str(p))
    M = json.loads(p.read_text(encoding="utf-8"))
    assert M["marks"] == MARKS["marks"] and M["doc_events"][0]["key"] == mk and M["doc_events"][0]["first_seen_set_to"] == WM.OLD_FIRST_SEEN


def test_AM_16_the_tutor_card_offers_add_as_old_and_medi_sees_the_promised_list():
    js = open(os.path.join(REPO, "docs", "js", "hub", "new-words-task.js"), encoding="utf-8").read()
    for kind, label in (("newword_add_new", "Add to the Doc as NEW"), ("newword_add_old", "Add to the Doc as OLD"),
                        ("newword_later", "Save it for a future lesson"), ("newword_forget", "Forget it")):
        assert f"['{kind}', '{label}'" in js
    assert "it.hint" in js and "data-promised" in js
    assert "newword_add_new" in N.KINDS and "newword_add_old" in N.KINDS and N.KINDS["newword_add"] == "add"
    wb = open(os.path.join(REPO, "docs", "word-bank.html"), encoding="utf-8").read()
    assert 'id="ab-promised"' in wb and "js/promised-words.js" in wb
    real = json.load(open(os.path.join(REPO, "data", "word-marks.json"), encoding="utf-8"))
    assert any(m["arabic"] == "ممتاز" and m["mark"] == "old" and m["by"] == "medi" for m in real["marks"])
