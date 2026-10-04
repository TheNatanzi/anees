# -*- coding: utf-8 -*-
"""Amal's listening check (Medi 2026-10-04 "make it for amal"): docs/amal/listen-check.html + docs/data/amal-listen.json.
The page data is blind (no engine names), every clip it names is published, the key stays out of docs/, the page saves
the way her other pages save (amal_rules + her link token), links nowhere off Anees, and is not on the Tutor hub."""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "scripts"))
import amal_listen_results as R
import build_amal_listen as B

DATA = json.loads((DOCS / "data" / "amal-listen.json").read_text(encoding="utf-8"))
KEY = json.loads((ROOT / "data" / "lesson-work" / "amal-listen-key.json").read_text(encoding="utf-8"))


def test_sample_is_40_lines_split_evenly():
    items, key = DATA["items"], KEY["items"]
    assert len(items) == 40 == len(key) and [x["id"] for x in items] == [k["id"] for k in key]
    assert len({x["id"] for x in items}) == 40
    assert KEY["counts"] == {"2026-09-28 agree 3": 10, "2026-09-28 agree 2": 10, "2026-10-02 agree 3": 10, "2026-10-02 agree 2": 10}
    for x, k in zip(items, key):
        assert set(x) == {"id", "date", "mmss", "clip", "a", "b"}
        assert len(x["a"]) <= 140 and len(x["b"]) <= 140 and B.bare(x["a"]) != B.bare(x["b"])
        assert k["clip_secs"] <= 15 and {k["a"], k["b"]} == {"elevenlabs", "gemini"}
        assert x["a"] == k[k["a"]] and x["b"] == k[k["b"]]
        assert x["clip"] == f"{x['date']}/clips/{B.clip_name(x['date'], k['i'])}"


def test_page_data_is_blind():
    raw = (DOCS / "data" / "amal-listen.json").read_text(encoding="utf-8").lower()
    js = (DOCS / "js" / "hub" / "listen-check-task.js").read_text(encoding="utf-8")
    code = re.sub(r"/\*[\s\S]*?\*/", "", js).lower()
    for word in ("elevenlabs", "gemini", "scribe", "agree", "engine"):
        assert word not in raw, word
        assert word not in code, word
    assert "amal-listen-key" not in js
    assert not list(DOCS.rglob("amal-listen-key*"))


def test_every_clip_is_published():
    for x in DATA["items"]:
        p = DOCS / "lessons" / x["clip"]
        assert p.exists() and p.stat().st_size > 1000, x["clip"]
    try:
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "docs/lessons/*/clips/al-*.mp3"], capture_output=True, text=True, check=True).stdout.split()
    except Exception:
        return
    if tracked:      # *.mp3 is git-ignored: the clips ship only when force-added
        assert {"docs/lessons/" + x["clip"] for x in DATA["items"]} <= set(tracked)


def test_page_saves_like_her_other_pages_and_stays_on_anees():
    html = (DOCS / "amal" / "listen-check.html").read_text(encoding="utf-8")
    js = (DOCS / "js" / "hub" / "listen-check-task.js").read_text(encoding="utf-8")
    assert "These are your own lines from two lessons. Two versions of what you said - which is right?" in html
    for need in ("js/config.js", "js/amal-undo.js", "js/play-bar.js", "js/hub/clip-player.js", "js/hub/solo.js", "css/sabz-tokens.css", "css/tutor-hub.css"):
        assert need in html, need
    assert "'X-Anees-Token': TOKEN" in js and "api('POST', 'amal_rules'" in js
    assert "SOURCE = 'listen-check'" in js and "'listen:' + x.id" in js and "payload: { choice, typed" in js
    assert "Both wrong" in js and "Same / can" in js and 'dir="auto"' in js and "AneesUndo.row(" in js
    links = re.findall(r"https?://[^\s\"'<>)]+", html + js)
    assert all(u.startswith(("https://yljcbdxvnkfrwvelypfu.supabase.co", "https://thenatanzi.github.io")) for u in links), links
    assert "<a " not in html and "<a " not in js


def test_not_on_the_tutor_hub():
    assert "listen-check" not in (DOCS / "data" / "tutor.json").read_text(encoding="utf-8")
    assert "listen-check" not in (DOCS / "tutor.html").read_text(encoding="utf-8")
    assert "listen-check" not in (DOCS / "js" / "tutor.js").read_text(encoding="utf-8")


def test_results_tally_against_the_key():
    key = [{"id": "d:1", "word_key": "listen:d:1", "agree": 3, "a": "elevenlabs", "b": "gemini", "elevenlabs": "x", "gemini": "y"},
           {"id": "d:2", "word_key": "listen:d:2", "agree": 3, "a": "gemini", "b": "elevenlabs", "elevenlabs": "x", "gemini": "y"},
           {"id": "d:3", "word_key": "listen:d:3", "agree": 2, "a": "gemini", "b": "elevenlabs", "elevenlabs": "x", "gemini": "y"},
           {"id": "d:4", "word_key": "listen:d:4", "agree": 2, "a": "gemini", "b": "elevenlabs", "elevenlabs": "x", "gemini": "y"},
           {"id": "d:5", "word_key": "listen:d:5", "agree": 2, "a": "gemini", "b": "elevenlabs", "elevenlabs": "x", "gemini": "y"}]
    rows = [{"id": 1, "kind": "listen_pick", "word_key": "listen:d:1", "payload": {"choice": "b"}},
            {"id": 2, "kind": "listen_pick", "word_key": "listen:d:1", "payload": {"choice": "a"}},      # she changed her answer: latest wins
            {"id": 3, "kind": "listen_pick", "word_key": "listen:d:2", "payload": {"choice": "a"}},
            {"id": 4, "kind": "listen_pick", "word_key": "listen:d:3", "payload": {"choice": "both_wrong", "typed": "z"}},
            {"id": 5, "kind": "listen_pick", "word_key": "listen:d:4", "payload": {"choice": "same"}}]
    table, lines = R.tally(key, rows)
    assert table[3] == {"elevenlabs": 1, "gemini": 1, "both_wrong": 0, "same": 0, "unanswered": 0}
    assert table[2] == {"elevenlabs": 0, "gemini": 0, "both_wrong": 1, "same": 1, "unanswered": 1}
    assert lines[2]["typed"] == "z"
