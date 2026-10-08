# -*- coding: utf-8 -*-
"""AM-27 (Medi 2026-10-07 "lets add a place for notes for amal always")."""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def test_AM_27_every_tutor_screen_loads_the_note_box_and_the_builder_mirrors_notes():
    pages = [os.path.join(ROOT, "docs", "tutor.html")] + [p for p in glob.glob(os.path.join(ROOT, "docs", "amal", "*.html"))
                                                           if "amal-undo.js" in open(p, encoding="utf-8").read()]
    assert len(pages) >= 8
    for p in pages:
        assert "amal-note.js" in open(p, encoding="utf-8").read(), os.path.basename(p)
    js = open(os.path.join(ROOT, "docs", "js", "amal-note.js"), encoding="utf-8").read()
    assert "Note for the student" in js and "source: SOURCE" in js and "'undo'" in js and "MutationObserver" in js
    hub = open(os.path.join(ROOT, "docs", "js", "tutor.js"), encoding="utf-8").read()
    assert hub.count("noteBox(") >= 4                      # the open panel, the Completed rows (two paths) and the helper itself
    solo = open(os.path.join(ROOT, "docs", "js", "hub", "solo.js"), encoding="utf-8").read()
    assert "AneesNote.attach(el" in solo
    st = open(os.path.join(ROOT, "docs", "js", "student.js"), encoding="utf-8").read()
    assert "tutor-notes.json" in st and "Notes from the tutor" in st
    assert 'id="st-notes"' in open(os.path.join(ROOT, "docs", "student.html"), encoding="utf-8").read()
    import build_tutor_data as B
    rows = [{"kind": "note", "word_key": "note:check-slip-check-2-1:2026-09-05:112", "payload": {"note": "he said it right", "list": "check-slip-check-2-1", "item": "2026-09-05:112", "context": "07:34"}, "created_at": "2026-10-07T20:00:00Z"},
            {"kind": "note", "word_key": "note:check-slip-check-2-1:2026-09-05:112", "payload": {"note": "actually wrong", "list": "check-slip-check-2-1", "item": "2026-09-05:112"}, "created_at": "2026-10-07T20:05:00Z"},
            {"kind": "note", "word_key": "note:after-2026-10-06:list", "payload": {"note": "good lesson", "list": "after-2026-10-06", "item": "list"}, "created_at": "2026-10-07T20:06:00Z"},
            {"kind": "undo", "word_key": "note:after-2026-10-06:list", "payload": {"note": "", "list": "after-2026-10-06", "item": "list"}, "created_at": "2026-10-07T20:07:00Z"}]
    L = B.latest_notes(rows)
    assert list(L) == ["note:check-slip-check-2-1:2026-09-05:112"] and L["note:check-slip-check-2-1:2026-09-05:112"][0]["note"] == "actually wrong"   # latest wins; the undo wiped the list note
    import tempfile
    B.NOTES_OUT = os.path.join(tempfile.mkdtemp(), "tutor-notes.json")
    doc = B.write_notes(rows, [{"id": "check-slip-check-2-1", "title": "Listen: what did the student say? - part 2 - part 1 of 5"}])
    assert doc["count"] == 1 and doc["notes"][0]["list_title"].startswith("Listen: what did the student say?") and doc["notes"][0]["note"] == "actually wrong"
    assert json.load(open(B.NOTES_OUT, encoding="utf-8"))["count"] == 1
    import amal_trigger as T
    assert "note" in T.KNOWN_RULE_SOURCES
    src = open(os.path.join(ROOT, "scripts", "amal_trigger.py"), encoding="utf-8").read()     # the sandbox fixture empties SOURCES
    assert '"id": "tutor_notes"' in src and '"fetch": fetch_notes' in src
