# -*- coding: utf-8 -*-
"""Decisions log (scripts/decisions.py) and the read-only pull (scripts/pull_decisions.py): append-only, every field
present, idempotent by source row, a changed verdict supersedes instead of editing, a missing table is fine, strict
git parsing, and no transcript text (Arabic or long free text) ever reaches the public log. No network: fetch is a stub."""
import json, re
from pathlib import Path

import pytest

import decisions
import pull_decisions as P

ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
AR = "بدي روح"


@pytest.fixture
def ddir(tmp_path, monkeypatch):
    d = tmp_path / "decisions"
    monkeypatch.setenv("ANEES_DECISIONS_DIR", str(d))
    return d


def lines(d):
    return [json.loads(l) for p in sorted(Path(d).glob("*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


def assert_clean(rec):
    def walk(o):
        if isinstance(o, str):
            assert not ARABIC.search(o), f"Arabic in the public log: {o!r}"
            assert len(o) <= 200, "free text over 200 chars in the public log"
        elif isinstance(o, dict):
            [walk(v) for v in o.values()]
        elif isinstance(o, list):
            [walk(v) for v in o]
    walk(rec)


def test_record_has_every_field_and_month_file(ddir):
    decisions.record(who="Amal", channel="tutor_page", about_type="pattern", about_id="P1", answer="audit_confirm",
                     ts="2026-09-27T16:17:50.44+00:00", source_row={"table": "amal_rules", "id": 1})
    decisions.record(who="Medi", channel="swipe", about_type="label", about_id="2026-10-01:L:123", answer="understood",
                     ts="2026-10-01T10:00:00Z", ai_value="breakdown", latency_ms=2100, sampling="random")
    assert sorted(p.name for p in ddir.glob("*.jsonl")) == ["2026-09.jsonl", "2026-10.jsonl"]
    for rec in lines(ddir):
        assert list(rec) == list(decisions.FIELDS)
    assert lines(ddir)[0]["ts"] == "2026-09-27T16:17:50Z"


def test_bad_enums_are_refused(ddir):
    with pytest.raises(ValueError):
        decisions.record(who="Codex", channel="chat", about_type="rule", about_id="x", answer="yes")
    with pytest.raises(ValueError):
        decisions.record(who="Medi", channel="email", about_type="rule", about_id="x", answer="yes")
    with pytest.raises(ValueError):
        decisions.record(who="Medi", channel="chat", about_type="rule", about_id="x", answer="")
    assert not ddir.exists() or lines(ddir) == []


def test_append_only(ddir):
    decisions.record(who="Medi", channel="chat", about_type="rule", about_id="R17", answer="no", ts="2026-09-27T00:00:00Z")
    (p,) = list(ddir.glob("*.jsonl"))
    before = p.read_bytes()
    decisions.record(who="Medi", channel="chat", about_type="rule", about_id="R17", answer="yes", ts="2026-09-27T01:00:00Z")
    assert p.read_bytes().startswith(before) and len(lines(ddir)) == 2


def test_no_transcript_text_leaks(ddir):
    rec = decisions.record(who="Amal", channel="tutor_page", about_type="word", about_id=AR, answer="edit",
                           corrected_value=AR + " fixed", reason="x" * 500, ts="2026-09-27T00:00:00Z")
    assert_clean(lines(ddir)[0])
    assert rec["about_id"].startswith("sha256:") and rec["reason"].startswith("sha256:")


ROWS = {
    "amal_rules_public": [
        {"id": 1, "created_at": "2026-09-26T10:00:00+00:00", "source": "flashcards", "lesson_date": None, "kind": "flag", "word_key": "7mAr", "text": ""},
        {"id": 2, "created_at": "2026-09-26T11:00:00+00:00", "source": "review", "lesson_date": None, "kind": "audit_confirm", "word_key": "P12", "text": AR},
        {"id": 3, "created_at": "2026-09-26T12:00:00+00:00", "source": "after", "lesson_date": "2026-09-23", "kind": "edit", "word_key": None, "text": "bnebse6 hon " + AR},
        {"id": 4, "created_at": "2026-09-26T13:00:00+00:00", "source": "planner", "lesson_date": "2026-09-24", "kind": "topic", "word_key": None, "text": "Food"},
        {"id": 5, "created_at": "2026-09-26T14:00:00+00:00", "source": "review", "lesson_date": None, "kind": "audit_skip", "word_key": "P12", "text": ""},
    ],
    "draft_word_reviews": [{"id": "2026-09-11|kelme|r1", "lesson_date": "2026-09-11", "word_key": "kelme", "verdict": "correct",
                            "reviewed_at": "2026-09-12T20:41:50.336+00:00"}],
}
GIT = "\n".join([
    "92f901736d57092385eb39f4858761b1c3d8379c\x1f2026-09-27T09:11:33-07:00\x1fTwo doubled slips counted once - Medi 2026-09-27: yes",
    "aaaaaaaaaaaa11112222333344445555666677778\x1f2026-09-27T08:00:00-07:00\x1fLadder spec (Medi 2026-09-27 grill: \"let's do all of these\")",
    "bbbbbbbbbbbb11112222333344445555666677778\x1f2026-09-22T08:00:00-07:00\x1fMedi 2026-09-22: the whole app follows the brand",
    "cccccccccccc11112222333344445555666677778\x1f2026-09-20T08:00:00-07:00\x1fDrop the old tab (Amal 2026-09-20: No)",
])


def stub(rows):
    def fetch(table, select, order):
        if table == "sentence_labels":
            return None                                    # table not applied yet: 404
        return [dict(r) for r in rows.get(table, [])]
    return fetch


def test_pull_maps_sources_and_is_idempotent(ddir):
    rep = P.pull(fetch=stub(ROWS), git_log=GIT)
    assert rep["amal_rules_public"] == {"fetched": 5, "new": 4, "skipped": 1}          # the automatic flashcard flag is not a verdict
    assert rep["sentence_labels"]["error"] == "table missing (404)"
    assert rep["draft_word_reviews"]["new"] == 1 and rep["git"] == {"fetched": 2, "new": 2, "skipped": 0}
    got = {x["decision_id"]: x for x in lines(ddir)}
    assert got["amal_rules:2"]["about_type"] == "pattern" and got["amal_rules:2"]["who"] == "Amal"
    assert got["amal_rules:3"]["about_type"] == "homework" and got["amal_rules:3"]["corrected_value"].startswith("sha256:")
    assert got["amal_rules:4"]["about_type"] == "plan"
    assert got["amal_rules:5"]["supersedes"] == "amal_rules:2"                        # a re-tap on the same pattern
    c = got["commit:92f901736d57"]
    assert (c["who"], c["answer"], c["channel"], c["reason"]) == ("Medi", "yes", "commit", "Two doubled slips counted once")
    assert got["commit:cccccccccccc"]["answer"] == "no" and got["commit:cccccccccccc"]["who"] == "Amal"
    for rec in got.values():
        assert list(rec) == list(decisions.FIELDS)
        assert_clean(rec)
    n = len(lines(ddir))
    again = P.pull(fetch=stub(ROWS), git_log=GIT)
    assert len(lines(ddir)) == n and all(v.get("new", 0) == 0 for v in again.values())


def test_changed_verdict_supersedes_instead_of_editing(ddir):
    P.pull(fetch=stub(ROWS), use_git=False)
    first = P.from_draft_review(ROWS["draft_word_reviews"][0])["decision_id"]
    changed = {**ROWS, "draft_word_reviews": [{**ROWS["draft_word_reviews"][0], "verdict": "incorrect",
                                                "reviewed_at": "2026-09-13T08:00:00+00:00"}]}
    P.pull(fetch=stub(changed), use_git=False)
    drafts = [x for x in lines(ddir) if x["decision_id"].startswith("draft_word_reviews:")]
    assert [x["answer"] for x in drafts] == ["correct", "incorrect"] and drafts[1]["supersedes"] == first
    assert first not in decisions.latest(str(ddir))


def test_sentence_labels_map_to_swipes(ddir):
    rows = {"sentence_labels": [{"id": "u1", "sentence_id": "2026-09-23:L:1234", "lesson_date": "2026-09-23", "side": "listen",
                                 "label": "breakdown", "machine_label": "understood", "machine_version": "2026-09-27",
                                 "n_words": 6, "ts": "2026-09-27T20:00:00Z", "answer_ms": 3100, "played": True}]}

    def fetch(table, select, order):
        return rows.get(table, [])
    P.pull(fetch=fetch, use_git=False)
    (x,) = lines(ddir)
    assert (x["who"], x["channel"], x["about_type"], x["ai_value"], x["answer"], x["latency_ms"]) == \
        ("Medi", "swipe", "label", "understood", "breakdown", 3100)
    assert x["ai_run_id"] == "sentence-ladder@2026-09-27"


def test_a_failing_source_does_not_stop_the_others(ddir):
    def fetch(table, select, order):
        if table == "amal_rules_public":
            raise ConnectionError("offline")
        return stub(ROWS)(table, select, order)
    rep = P.pull(fetch=fetch, use_git=False)
    assert rep["amal_rules_public"]["error"] == "ConnectionError" and rep["draft_word_reviews"]["new"] == 1
