# -*- coding: utf-8 -*-
"""PG-17 - Medi 2026-10-02: "can we have everything on the tutor hub do what the new words is doing where you dont
have to go to an external page".  PG-18 - Medi 2026-10-02: "can you make these into accodrians so I can see what you
are asking" (the Tutor hub's Done tab).

Every item on the Tutor hub (To do, Grammar, Materials, Done) opens and is answered INSIDE the hub with the same module
its old address mounts; long lists come 20 at a time; Done rows are accordions that show every question asked and
Amal's answer, read from the stored questions when the link has expired. Offline: no network, no writes."""
import json, re, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TUTOR_JS = (DOCS / "js" / "tutor.js").read_text(encoding="utf-8")
TUTOR_HTML = (DOCS / "tutor.html").read_text(encoding="utf-8")
HUB = DOCS / "js" / "hub"


def kinds_built():
    """Every item kind scripts/build_tutor_data.py can put on the hub."""
    src = (ROOT / "scripts" / "build_tutor_data.py").read_text(encoding="utf-8")
    ks = set(re.findall(r'"kind": "([a-z_]+)"', src)) | {"after", "before", "verb_check", "word_review"}
    return ks | {"verify", "newwords", "ledger", "proposals", "attention"}   # the lists tutor.js adds itself (ledger: LS-12; proposals: GR-29)


def test_PG_17_no_hub_item_links_to_another_page():
    # no hand-off to another page anywhere in the hub: no go.html / amal/*.html links, no frames, no navigation away
    for name, src in (("docs/js/tutor.js", TUTOR_JS), ("docs/tutor.html", TUTOR_HTML)):
        assert "go.html" not in src, f"{name} sends Amal to go.html (PG-17)"
        assert not re.search(r'href=["\']?(\.\./)?amal/', src), f"{name} links to an amal/ page instead of opening it in the panel (PG-17)"
        assert "<iframe" not in src and "location.href =" not in src and "window.open(" not in src, f"{name} leaves the hub (PG-17)"
    # nor inside any module the hub mounts
    for f in list(HUB.glob("*.js")) + [DOCS / "js" / "tutor-verify.js", DOCS / "js" / "amal-grammar-notes.js"]:
        if f.name == "solo.js":
            continue                                  # the shell of the OLD addresses: its link goes back to the hub
        for href in re.findall(r'href=\\?"([^"$]*)', f.read_text(encoding="utf-8")):
            ok = href.startswith("#") or (f.name == "amal-grammar-notes.js" and href == "materials.html")   # that one only on the old page
            assert ok, f"{f.name} links to {href!r}: hub items must open in the panel (PG-17)"
    g = (DOCS / "js" / "amal-grammar-notes.js").read_text(encoding="utf-8")
    assert "SCOPE === document ? '<a href=\"materials.html\">" in g and "'<a href=\"#materials\">" in g


def test_PG_17_every_item_kind_opens_in_the_panel_with_the_shared_module():
    mount = TUTOR_JS[TUTOR_JS.index("const MOUNT = {"):TUTOR_JS.index("};", TUTOR_JS.index("const MOUNT = {"))]
    have = set(re.findall(r"^\s+([a-z_]+): ", mount, re.M))
    tabs = {"grammar_notes": "AneesGrammarNotes.start(", "materials": "AneesDoc.materials("}   # PG-30: Grammar = his weakest rules with her note box; Materials = route only
    for k in sorted(kinds_built()):
        if k in tabs:
            assert tabs[k] in TUTOR_JS, f"{k} must open inside the hub (PG-17)"
        else:
            assert k in have, f"item kind {k!r} has no in-panel module in tutor.js MOUNT (PG-17: {k} would need another page)"
    # each module is loaded by the hub AND by its old address, so both show the same thing
    old = {"after": "amal/after.html", "before": "amal/plan.html", "review": "amal/review.html", "verb_check": "amal/verb-check.html",
           "word_review": "amal/word-review.html"}
    for k, page in old.items():
        mod = {"after": "after-task.js", "before": "plan-task.js", "review": "review-task.js", "verb_check": "verb-check-task.js", "word_review": "word-review-task.js"}[k]
        assert f"js/hub/{mod}" in TUTOR_HTML, f"tutor.html does not load {mod}"
        assert f"js/hub/{mod}" in (DOCS / page).read_text(encoding="utf-8"), f"{page} does not render the shared {mod}"
    for mod in ("doc-task.js", "amal-grammar-notes.js"):
        assert mod in TUTOR_HTML
    # the reading pages are read from the same files the old addresses serve
    d = (HUB / "doc-task.js").read_text(encoding="utf-8")
    assert "'amal/grammar-rules.html'" in d and "'amal/materials.html'" in d


def test_PG_17_long_lists_come_20_at_a_time_with_an_honest_time():
    assert re.search(r"const PAGE = 20\b", TUTOR_JS) and "Next ${Math.min(PAGE" in TUTOR_JS
    v = (HUB / "verb-check-task.js").read_text(encoding="utf-8")
    assert re.search(r"const PAGE = 20, SECONDS_EACH = 6", v) and "Next ${Math.min(PAGE" in v and "min left" in v
    r = (HUB / "review-task.js").read_text(encoding="utf-8")
    assert "shown = 20" in r and "Show the next" in r
    assert "about ${mins(t)} min" in TUTOR_JS                # every row says the minutes it takes
    assert "verb_check: 0.1" in TUTOR_JS                     # 6 s a form: 402 forms ~ 40 min, as Medi saw


def test_PG_18_done_rows_are_accordions_that_show_what_was_asked():
    assert '<details class="hb-acc"' in TUTOR_JS and "function doneView()" in TUTOR_JS
    dv = TUTOR_JS[TUTOR_JS.index("function doneView()"):TUTOR_JS.index("function count()")]
    assert "location.hash" not in dv, "a Done row must open in place, not change the page"
    assert "x.result || 'not answered'" in TUTOR_JS and "Find a question or answer" in TUTOR_JS
    assert "MOUNT[t.kind](body, t.item, () => {}, { view: 'done' })" in TUTOR_JS   # a list still open: live, with Undo


def test_PG_18_expired_links_keep_their_questions_and_one_lesson_is_one_row(tmp_path, monkeypatch):
    import build_tutor_data as B
    now = "2026-10-02T20:00:00+00:00"
    q = [{"ask": "Was Medi right here?", "arabizi": "kalb", "arabic": "كلب", "english": "dog", "word_key": "kalb", "t": 60}]
    links = [   # newest first, as the builder reads them
        {"token": "NEW", "kind": "after", "lesson_date": "2026-10-01", "created_at": "2026-10-02T10:00:00Z", "expires_at": "2026-10-09T00:00:00Z",
         "opened_at": None, "done_at": None, "payload": {"questions": q}, "answers": {}},
        {"token": "OLD", "kind": "after", "lesson_date": "2026-10-01", "created_at": "2026-10-01T10:00:00Z", "expires_at": "2026-10-02T00:00:00Z",
         "opened_at": None, "done_at": None, "payload": {"questions": q + [{"ask": "Did Medi say this word?", "arabizi": "bet", "word_key": "bet"}]},
         "answers": {"q": {"0": "Wrong word"}}},
        {"token": "S11", "kind": "after", "lesson_date": "2026-09-30", "created_at": "2026-09-30T10:00:00Z", "expires_at": "2026-10-01T00:00:00Z",
         "opened_at": None, "done_at": None, "payload": {"questions": q}, "answers": {}}]
    rules = [{"token": "OLD", "kind": "wrong", "word_key": "kalb", "payload": {}, "created_at": "2026-10-01T18:00:00Z"}]

    def select(table, params=None, **kw):
        return {"amal_links": links, "amal_rules": rules}.get(table, [])
    monkeypatch.setitem(sys.modules, "db", types.SimpleNamespace(select=select))
    monkeypatch.setattr(B, "OUT", str(tmp_path / "tutor.json"))
    import datetime as _dt

    class FakeDT(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime.fromisoformat(now)
    monkeypatch.setattr(B.datetime, "datetime", FakeDT)
    B.main()
    out = json.load(open(tmp_path / "tutor.json", encoding="utf-8"))
    titles = [x["title"] for x in out["open"] + out["closed"]]
    assert titles.count("After the lesson · Oct 1") == 1                     # the duplicate Oct 1 row is merged
    oct1 = next(x for x in out["open"] if x["title"] == "After the lesson · Oct 1")
    e = oct1["earlier"][0]
    assert e["why"] == "link expired 2026-10-02" and e["token"] == "OLD"
    asked = e["detail"]["asked"]
    assert [(a["word"], a["answer"], a["at"]) for a in asked] == [("kalb", "Wrong word", "2026-10-01"), ("bet", None, None)]   # not answered stays visible
    sep30 = next(x for x in out["closed"] if x["title"] == "After the lesson · Sep 30")
    assert sep30["detail"]["total"] == 1 and sep30["detail"]["asked"][0]["ask"] == "Was Medi right here?"


# ---- AM-18: one after link per lesson; a re-review never re-opens a lesson Amal answered -----------------------------
QUOTE_AM18 = "close, but I want accordians to see the results and what you are asking"


def test_AM_18_a_re_review_does_not_make_a_new_link_for_an_answered_lesson(monkeypatch):
    import amal_links as L
    answered = {"token": "OLD", "kind": "after", "lesson_date": "2026-10-01", "created_at": "2026-10-02T08:54:00Z", "expires_at": "2026-10-09T00:00:00Z",
                "done_at": "2026-10-02T12:10:00Z", "answers": {"q": {"0": "Right"}, "done": True}}
    made = []
    monkeypatch.setattr(L.db, "select", lambda *a, **k: [answered])
    monkeypatch.setattr(L.db, "upsert", lambda *a, **k: made.append(a))
    tok, url = L.create("after", "2026-10-01", {"questions": [{"ask": "x"}]})
    assert tok == "OLD" and made == []                                           # the answered link is kept, nothing minted
    # an open link she has not touched yet is kept too (one link per lesson); only expired untouched links allow a new one
    open_ = {**answered, "token": "OPEN", "done_at": None, "answers": {}}
    assert L.reuse_for([open_], "after", "2026-10-01", "2026-10-02T20:00:00Z")["token"] == "OPEN"
    expired = {**open_, "expires_at": "2026-10-02T00:00:00Z"}
    assert L.reuse_for([expired], "after", "2026-10-01", "2026-10-02T20:00:00Z") is None
    assert L.reuse_for([expired, answered], "after", "2026-10-01", "2026-10-02T20:00:00Z")["token"] == "OLD"
    # the path the hourly re-review takes goes through this guard
    src = (ROOT / "scripts" / "after_from_audit.py").read_text(encoding="utf-8")
    assert "amal_links" + '.create("after", a.date, p)' in src    # (split: the FC-08 scan reads test sources)


def test_AM_18_re_made_links_are_closed_with_her_earlier_answers():
    import close_reasked_after_links as C
    old = {"token": "OLD", "kind": "after", "lesson_date": "2026-10-01", "created_at": "2026-10-02T08:54:00Z", "expires_at": "2026-10-09T00:00:00Z",
           "done_at": "2026-10-02T12:10:00Z", "answers": {"q": {"0": "Right", "1": "Wrong word"}, "done": True},
           "payload": {"questions": [{"audit_uid": "FA-1", "t": 396.0}, {"audit_uid": "FA-2", "t": 861.0}]}}
    new = {"token": "NEW", "kind": "after", "lesson_date": "2026-10-01", "created_at": "2026-10-02T18:27:00Z", "expires_at": "2026-10-09T00:00:00Z",
           "done_at": None, "answers": None, "payload": {"questions": [{"audit_uid": "FA-9", "t": 862.5}, {"audit_uid": "FA-7", "t": 2711.0}]}}
    (r, src, ans), = C.plan([old, new], "2026-10-02T20:00:00Z")
    assert r["token"] == "NEW" and src["token"] == "OLD"
    assert ans["q"] == {"0": "Wrong word"} and ans["done"] is True                # same moment (861 ~ 862.5 s) carries her answer
    assert ans["not_asked"] == {"1": C.NOT_ASKED} and ans["carried_from"]["token"] == "OLD"
    assert C.plan([old], "2026-10-02T20:00:00Z") == []                           # nothing to close: nothing written


def test_PG_18_done_rows_show_the_moment_and_the_result():
    import build_tutor_data as B
    link = {"kind": "after", "token": "T", "lesson_date": "2026-10-01", "done_at": "2026-10-02T12:10:00Z",
            "payload": {"questions": [{"ask": "Was Medi right here?", "audit_uid": "FA-x", "t": 396.0, "arabizi": "mitshajje3"},
                                      {"ask": "Was Medi right here?", "audit_uid": "FA-y", "t": 900.0}]},
            "answers": {"q": {"0": "Wrong word"}, "updated": "2026-10-02T12:10:00Z", "not_asked": {"1": "not asked - she had answered this lesson already"}}}
    B._AUDIT.clear(); B._AUDIT.update({"FA-x": {"uid": "FA-x", "kind": "vocab-A", "medi_said": "ana mshajje3"}})
    d = B.link_detail(link, {})
    a, b = d["asked"]
    assert (a["t"], a["medi"], a["answer"], a["at"], a["result"]) == ("6:36", "ana mshajje3", "Wrong word", "2026-10-02", "slip counted for Medi")
    assert a["clip"].startswith("lessons/2026-10-01/audio/lesson.mp3#t=393,")
    assert b["answer"] is None and b["result"].startswith("not asked")
    B._AUDIT.clear()
    js = TUTOR_JS
    assert "Result: ${esc(x.result)}" in js and "Medi: <span lang=\"ar\">${esc(x.medi)}</span>" in js and "AneesClip.bar(" in js
    assert "<b>Change an answer</b>" in js                                       # Undo one tap below the results while live


def test_AM_21_AM_22_the_two_tools_have_their_own_strip_not_rows_in_her_checking_list():
    """Medi 2026-10-05: "Separate the upload flash cards and assign homework from the other modules"."""
    assert 'href="#upload" data-tab="upload"' in TUTOR_HTML and 'href="#homework" data-tab="homework"' in TUTOR_HTML
    assert "if (tab === 'upload' || tab === 'homework') return tool(tab);" in TUTOR_JS
    assert "kind: 'upload'" not in TUTOR_JS and "kind: 'homework'" not in TUTOR_JS      # never a task row


def test_AM_23_every_tutor_choice_is_a_plain_sentence_about_medi():
    """AM-23 (Medi 2026-10-06: "all the verbiage in the tutor section is confusing. label it Medi got it right / Medi got the wrong
    word / Medi had wrong grammar. Please revisit all of them")."""
    after = (HUB / "after-task.js").read_text(encoding="utf-8")
    for label in ("'Right': 'Medi got it right'", "'Wrong word': 'Medi got the wrong word'", "'Wrong grammar': 'Medi had wrong grammar'", "'Not Medi': 'That was not Medi speaking'"):
        assert label in after
    assert "esc(show(b))" in after and "Listen, then tap. Your tap sets the score for this word." in after
    assert "the readers were not sure" not in after and "${esc(q.why)}" not in after      # no machine reason under the question
    for f in (HUB / "review-task.js", DOCS / "js" / "tutor-verify.js"):
        js = f.read_text(encoding="utf-8")
        assert "Yes, Medi was wrong" in js and "No, Medi was fine" in js and "Correction is correct<" not in js, f.name
    assert "Right as written" in (HUB / "verb-check-task.js").read_text(encoding="utf-8")
    assert "right: 'Medi got it right', close: 'Medi was close', wrong: 'Medi got it wrong'" in (HUB / "homework-task.js").read_text(encoding="utf-8")
