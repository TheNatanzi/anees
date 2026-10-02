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
    return ks | {"verify", "newwords"}          # the two lists tutor.js adds itself


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
    tabs = {"grammar_notes": "AneesDoc.grammar(", "materials": "AneesDoc.materials("}
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
    assert "<i>not answered</i>" in TUTOR_JS and "Find a question or answer" in TUTOR_JS
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
