# -*- coding: utf-8 -*-
"""Rule PG-16 (Medi 2026-10-02: "Lets keep a parrallel document of the rules ... so I can read it and follow it"):
the rule book (docs/rules.html reads docs/data/rule-book.json; RULE-BOOK.md on GitHub) is built from rules/registry.json
+ RULES.md by scripts/build_rule_book.py and is never older than them. A stale book blocks the publish."""
import json
from pathlib import Path

import build_rule_book as B
import rule_registry as RR

ROOT = Path(__file__).resolve().parent.parent


def test_published_rule_book_matches_the_registry():
    """PG-16: the committed book is exactly what the registry builds now (run scripts/build_rule_book.py)."""
    bad = B.stale(ROOT)
    assert not bad, "rule book out of date (PG-16) - run: python scripts/build_rule_book.py  (stale: " + ", ".join(bad) + ")"


def test_every_rule_is_in_the_book_exactly_once():
    reg = RR.load(ROOT)
    book = B.build_book(ROOT)
    shown = [x["id"] for g in book["groups"] for s in g["sections"] for x in s["rules"]]
    old = [x["id"] for g in book["groups"] for x in g["old"]]
    ids = [r["id"] for r in reg["rules"]]
    assert sorted(shown + old) == sorted(ids)
    assert sorted(old) == sorted(r["id"] for r in reg["rules"] if r["status"] == "superseded")
    assert [g["title"] for g in book["groups"]][0] == "Recording & transcript" and len(book["groups"]) == 8


def test_big_rules_come_from_rules_md_with_plain_words():
    book = B.build_book(ROOT)
    titles = B.big_rule_titles(ROOT)
    assert [b["id"] for b in book["big_rules"]] == sorted(titles, key=lambda s: int(s[1:]))
    assert all(b["text"] and b["rule"] for b in book["big_rules"])


def test_plain_wins_and_claude_words_are_never_shown_as_medis(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "RULES.md").write_text("# R\n\n---\n\n## S1 — One rule (Medi 2026-10-02)\n\nbody\n", encoding="utf-8")
    rules = [
        {"id": "GR-01", "kind": "error", "scope": "grammar-scoring", "status": "enforced", "statement": "tech words",
         "plain": "plain words", "plain_for": RR.plain_hash("tech words"), "topic": "b", "aliases": ["RULES:S1"],
         "source": [{"by": "claude", "date": "2026-09-05", "quote": "plan"}, {"by": "medi", "date": "2026-10-01", "quote": "do it"}]},
        {"id": "GR-02", "kind": "not-error", "scope": "grammar-scoring", "status": "written", "statement": "only claude",
         "topic": "a", "source": [{"by": "claude", "date": "2026-09-05", "quote": "plan"}]},
        {"id": "GR-03", "kind": "not-error", "scope": "grammar-scoring", "status": "superseded", "statement": "old one",
         "superseded_by": "GR-02", "source": [{"by": "medi", "date": "2026-09-01", "quote": "old"}]},
        {"id": "LS-07", "kind": "process", "scope": "lessons", "status": "needs-medi", "statement": "reader shapes",
         "question": {"ask": "yes or no?", "options": ["yes", "no"]}, "source": [{"by": "medi", "date": "2026-10-02", "quote": "q"}]},
    ]
    (tmp_path / "rules" / "registry.json").write_text(json.dumps({"rules": rules}), encoding="utf-8")
    book = B.build_book(tmp_path)
    g = {x["key"]: x for x in book["groups"]}
    counts = g["grammar"]["sections"][0]["rules"][0]
    assert counts["text"] == "plain words" and counts["badge"] == "Automatic"
    assert counts["said"] == [{"who": "Medi", "date": "2026-10-01", "quote": "do it"}]       # Claude's line is dropped
    claude_only = g["grammar"]["sections"][1]["rules"][0]
    assert "said" not in claude_only and claude_only["claude"] == "2026-09-05"
    assert g["grammar"]["old"][0]["replaced_by"] == {"id": "GR-02", "text": "only claude"}
    assert g["process"]["sections"][0]["rules"][0]["badge"] == "Waiting on you"          # LS-07 -> how the AI works
    assert book["big_rules"] == [{"id": "S1", "title": "One rule", "text": "plain words", "rule": "GR-01"}]
    assert book["updated"] == "2026-10-02"
    md = B.to_markdown(book)
    assert "Written by Claude, 2026-09-05" in md and "Old rules (replaced)" in md
    md_before = md
    rules[0]["statement"] = "changed meaning"                                         # plain not re-read -> statement
    (tmp_path / "rules" / "registry.json").write_text(json.dumps({"rules": rules}), encoding="utf-8")
    assert B.build_book(tmp_path)["big_rules"][0]["text"] == "changed meaning" and md_before
    # stale until built, then clean
    assert B.stale(tmp_path) == [B.OUT_JSON, B.OUT_MD]
    assert B.main(["--root", str(tmp_path)]) == 0 and B.stale(tmp_path) == []
