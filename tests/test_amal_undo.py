# -*- coding: utf-8 -*-
"""AM-17 - Medi 2026-10-02: "can you add an undo button to all these tutor hub stuff".

Undo never deletes: it is a new amal_rules row (kind 'undo') and the latest action per item wins (tap -> undo -> tap).
Every consumer honours it: scripts/db.py on every amal_rules select, the slip rulings (apply_amal_audit_rulings + the
pages' sweep_compat copy), the Tutor-page checks (verification ledger), the new-words builder and its promised list,
verb checks. Offline: every read is a stub and nothing is written to Supabase (FC-08)."""
import json, os, re, sys, types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
import amal_undo  # noqa: E402

QUOTE = "can you add an undo button to all these tutor hub stuff"


def tap(i, kind, wk, source="review", **pl):
    return {"id": i, "token": "T", "source": source, "lesson_date": None, "kind": kind, "word_key": wk, "payload": pl,
            "created_at": f"2026-10-02T12:00:{i:02d}Z"}


def undo(i, of, match=None, token="T"):
    return {"id": i, "token": token, "source": of["source"], "lesson_date": of.get("lesson_date"), "kind": "undo", "word_key": of["word_key"],
            "payload": {"undoes": of["kind"], "match": match}, "created_at": f"2026-10-02T12:00:{i:02d}Z"}


# ---- the rule itself ------------------------------------------------------------------------------------------------
def test_AM_17_undo_is_a_new_row_and_the_latest_action_wins_tap_undo_tap():
    a = tap(1, "audit_confirm", "P-x")
    res = amal_undo.resolve([a, undo(2, a)])
    assert res.kept == [] and res.undone == {1: undo(2, a)}             # undone, nothing deleted: both rows still exist
    b = tap(3, "audit_skip", "P-x", reason="both are fine")
    assert amal_undo.honour([a, undo(2, a), b]) == [b]                   # re-tap after undo counts
    other = tap(4, "audit_confirm", "P-y")
    assert amal_undo.honour([a, other, undo(5, a)]) == [other]           # only the same item is undone
    # her link changes, the item does not: an undo from a newer link cancels the old link's tap
    assert amal_undo.honour([a, undo(6, a, token="NEW")]) == []
    # an undo with no key and no match never guesses
    nokey = tap(7, "keep", None, source="after", arabizi="x")
    assert amal_undo.honour([nokey, {**undo(8, nokey), "payload": {"undoes": "keep"}}]) == [nokey]
    assert amal_undo.honour([nokey, undo(9, nokey, match={"arabizi": "x"})]) == []


def test_AM_17_every_amal_rules_select_honours_undo(monkeypatch):
    import db
    a, b = tap(1, "newword_forget", "newword:2026-10-01:x"), tap(2, "newword_add_new", "newword:2026-10-01:y")
    rows = [a, b, undo(3, a)]
    seen = []

    def fake(table, params=None, **kw):
        seen.append(dict(params or {}))
        want = (params or {}).get("kind")
        return [r for r in rows if want != "eq.undo" or r["kind"] == "undo"]
    monkeypatch.setattr(db, "_select", fake)
    got = db.select("amal_rules", {"select": "kind,word_key", "source": "eq.review"})
    assert got == [{"kind": "newword_add_new", "word_key": "newword:2026-10-01:y"}]
    assert len(db.select("amal_rules", {"source": "eq.review"}, undo=False)) == 3      # the raw history for the trigger


# ---- slips: an undone confirm stops counting -----------------------------------------------------------------------
@pytest.fixture
def audit_env(tmp_path, monkeypatch):
    import apply_amal_audit_rulings as aar
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"rows": [
        {"uid": "FA-b1", "kind": "grammar-B", "signal": "none", "confidence": "low", "date": "2026-10-01", "t": "01:02", "bucket": "B5"},
        {"uid": "FA-b3", "kind": "grammar-B", "signal": "none", "confidence": "low", "date": "2026-10-01", "t": "02:00", "bucket": "B5"}]}), encoding="utf-8")
    rules = tmp_path / "ai_rules.json"
    rules.write_text(json.dumps({"groups": []}), encoding="utf-8")
    monkeypatch.setattr(aar, "AUDIT", str(audit))
    monkeypatch.setattr(aar, "RULES", str(rules))
    monkeypatch.setattr(aar, "LEDGER", str(tmp_path / "ledger.json"))
    monkeypatch.setattr(aar.subprocess, "run", lambda *a, **k: None)
    raw = []

    def select(table, params=None, **kw):
        src = (params or {}).get("source", "").replace("eq.", "")
        return [r for r in raw if r["source"] == src]
    monkeypatch.setitem(sys.modules, "db", types.SimpleNamespace(select=select, rest=lambda *a, **k: None))
    return aar, audit, rules, raw


def compat_ids(audit):
    A = json.loads(audit.read_text(encoding="utf-8"))
    return {x["uid"] for x in A.get("sweep_compat", {}).get("rows", [])}, {r["uid"]: r for r in A["rows"]}


def test_AM_17_undone_confirm_removes_the_slip_and_a_re_tap_counts_again(audit_env):
    aar, audit, rules, raw = audit_env
    confirm = tap(10, "audit_confirm", "P-b5", rows=["FA-b1"])
    raw.append(confirm)
    aar.apply()
    ids, rows = compat_ids(audit)
    assert rows["FA-b1"]["kind"] == "grammar" and "FA-b1" in ids                # her confirm scores the slip
    raw.append(undo(11, confirm))
    aar.apply()
    ids, rows = compat_ids(audit)
    assert rows["FA-b1"]["kind"] == "grammar-B" and "FA-b1" not in ids          # undone: back to unanswered, off the pages
    assert rows["FA-b1"]["amal_ruling_undone"][0]["undo_rule_id"] == 11        # history kept on the row
    raw.append(tap(12, "audit_confirm", "P-b5", rows=["FA-b1"]))
    aar.apply()
    ids, rows = compat_ids(audit)
    assert rows["FA-b1"]["kind"] == "grammar" and "FA-b1" in ids                # tap -> undo -> tap counts


def test_AM_17_undone_reason_takes_her_rule_back(audit_env):
    aar, audit, rules, raw = audit_env
    skip = tap(20, "audit_skip", "P-sun", rows=["FA-b3"], reason="not a priority")
    raw.append(skip)
    aar.apply()
    assert compat_ids(audit)[1]["FA-b3"]["kind"] == "dropped-by-amal"
    raw.append(undo(21, skip))
    aar.apply()
    assert compat_ids(audit)[1]["FA-b3"]["kind"] == "grammar-B"
    grp = next(g for g in json.loads(rules.read_text(encoding="utf-8"))["groups"] if g["title"] == "Amal's rulings")
    assert [(x["id"], x["status"]) for x in grp["rules"]] == [("AR-20", "undone")]   # kept, marked undone, never asked-once


def test_AM_17_undone_tutor_page_check_is_withdrawn_in_the_ledger(audit_env):
    import accuracy_gates as G
    aar, audit, rules, raw = audit_env
    v = tap(30, "audit_confirm", "verify:FA-b1", rows=["FA-b1"])
    raw.append(v)
    aar.apply()
    L = json.load(open(aar.LEDGER, encoding="utf-8"))
    assert G.ledger_state(L)["FA-b1"]["human"]["verdict"] == "confirmed"
    raw.append(undo(31, v))
    aar.apply()
    L = json.load(open(aar.LEDGER, encoding="utf-8"))
    assert [r["verdict"] for r in L["records"]] == ["confirmed", "withdrawn"]   # append-only
    assert G.ledger_state(L)["FA-b1"]["human"] is None                         # back on her list
    raw.append(tap(32, "audit_skip", "verify:FA-b1", rows=["FA-b1"], reason="he said it right"))
    aar.apply()
    L = json.load(open(aar.LEDGER, encoding="utf-8"))
    assert G.ledger_state(L)["FA-b1"]["human"]["verdict"] == "rejected"        # her new answer counts


# ---- new words: an undone "Add as OLD" leaves the promised list; Medi's own mark stays -----------------------------
def test_AM_17_undone_add_removes_the_promised_entry_and_medi_marks_stay(monkeypatch):
    import db, amal_new_words as N
    V = [{"date": "2026-10-01", "key": "mumtaz", "verdict": "new", "arabic": "ممتاز", "arabizi": "mumtaz", "english": "excellent", "t": 10.0},
         {"date": "2026-10-01", "key": "laffe", "verdict": "new", "arabic": "لفة", "arabizi": None, "english": "a wrap", "t": 20.0}]
    iid = {v["key"]: N.item_id("2026-10-01", v["key"]) for v in V}
    marks = {"marks": [{"arabic": "ممتاز", "arabizi": "mumtaz", "mark": "old", "by": "medi"}]}
    a1, a2 = tap(40, "newword_add_old", iid["mumtaz"]), tap(41, "newword_add_new", iid["laffe"])
    rows = [a1, a2, undo(42, a1), undo(43, a2)]
    monkeypatch.setattr(db, "_select", lambda table, params=None, **kw: [r for r in rows if (params or {}).get("kind") != "eq.undo" or r["kind"] == "undo"])
    taps = N.load_taps()
    assert taps == {}                                                          # both undone
    out = N.build(V, taps, None, today="2026-10-02", marks=marks, doc={"items": []})
    st = {x["id"]: x for x in out["items"]}
    assert st[iid["mumtaz"]]["status"] == "open" and st[iid["laffe"]]["status"] == "open"
    P = {p["id"]: p for p in out["promised"]}
    assert iid["laffe"] not in P                                               # her undone add left the promised list
    assert P[iid["mumtaz"]]["state"] == "awaiting_amal" and P[iid["mumtaz"]]["marks"]["medi"] == "old"   # Medi's mark stays
    rows.append(tap(44, "newword_add_new", iid["laffe"]))                       # re-tap after undo
    out = N.build(V, N.load_taps(), None, today="2026-10-02", marks=marks, doc={"items": []})
    assert {p["id"]: p["state"] for p in out["promised"]}[iid["laffe"]] == "waiting"
    assert {x["id"]: x["tap_token"] for x in out["items"]}[iid["laffe"]] == "T"    # the hub trusts its live read of this link


# ---- verb checks: an undone form leaves the merged answers ---------------------------------------------------------
def test_AM_17_undone_verb_form_leaves_the_pulled_answers(tmp_path, monkeypatch):
    import verb_check_links as VL
    monkeypatch.setattr(VL, "CHECKS", tmp_path / "checks.json")
    monkeypatch.setattr(VL, "ADDON_CHECKS", tmp_path / "addons.json")
    (tmp_path / "checks.json").write_text(json.dumps({"answers": {"v1": {"choice": "yes", "word": "baktob", "arabic": "", "updated_at": "2026-10-01T10:00:00Z"}}}), encoding="utf-8")
    link = {"payload": {"kind": "verb-forms", "items": {"v1": {"word": "baktob", "tense": "Present"}, "v2": {"word": "katab", "tense": "Past"}}},
            "answers": {"answers": {"v2": {"choice": "yes", "word": "katab", "arabic": "", "updated_at": "2026-10-02T10:00:00Z"}},
                        "undone": [{"key": "v1", "was": {"choice": "yes"}, "at": "2026-10-02T11:00:00Z"}]}, "created_at": "2026-10-01"}
    monkeypatch.setattr(VL.db, "select", lambda *a, **k: [link])
    assert sorted(VL.pull()) == ["v2"]


# ---- every Tutor-reachable page with a choice renders the one shared Undo ------------------------------------------
CHOICE_PAGES = {   # page -> the module that draws its choices
    "tutor.html": ["js/hub/new-words-task.js", "js/tutor-verify.js", "js/hub/after-task.js", "js/hub/listen-check-task.js"],
    "amal/after.html": ["js/hub/after-task.js"],
    "amal/plan.html": ["js/hub/plan-task.js"],
    "amal/review.html": ["js/hub/review-task.js"],
    "amal/verb-check.html": ["js/hub/verb-check-task.js"],
    "amal/word-review.html": ["js/hub/word-review-task.js"],
    "amal/grammar-rules.html": ["js/amal-grammar-notes.js"],
    "amal/listen-check.html": ["js/hub/listen-check-task.js"],
}


def test_AM_17_every_tutor_page_with_a_choice_renders_undo():
    for page, mods in CHOICE_PAGES.items():
        html = (DOCS / page).read_text(encoding="utf-8")
        assert "js/amal-undo.js" in html, f"{page} does not load the shared Undo (AM-17: {QUOTE})"
        tag = lambda m: re.search(r'<script src="[^"]*' + re.escape(m), html)
        for m in mods:
            assert tag(m), f"{page} does not draw its choices with {m}"
            assert tag("js/amal-undo.js").start() < tag(m).start(), f"{page}: amal-undo.js must load before {m}"
            js = (DOCS / m).read_text(encoding="utf-8")
            assert re.search(r"AneesUndo\.(button|answered)\(", js), f"{m} has choices but no Undo"
            assert "kind: 'undo'" in js or "AneesUndo.row(" in js or "AneesUndo.log(" in js or "VC.answer(payload, answers, id, null)" in js, f"{m}: Undo must record, never delete"
    # every module in the hub folder that draws a choice button has Undo too (a new list cannot ship without it)
    for f in (DOCS / "js" / "hub").glob("*-task.js"):
        js = f.read_text(encoding="utf-8")
        if re.search(r"class=\"hb-ans|data-choice=", js):
            assert "AneesUndo." in js, f"{f.name} draws choices without the shared Undo"
    # one helper, one look
    u = (DOCS / "js" / "amal-undo.js").read_text(encoding="utf-8")
    assert "class=\"an-undo\"" in u and "kind: 'undo'" in u
    for f in list((DOCS / "js" / "hub").glob("*.js")) + [DOCS / "js" / "tutor-verify.js", DOCS / "js" / "amal-grammar-notes.js"]:
        assert "an-undo\">" not in f.read_text(encoding="utf-8").replace("AneesUndo", ""), f"{f.name} draws its own Undo button"
