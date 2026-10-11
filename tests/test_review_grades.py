# -*- coding: utf-8 -*-
"""PG-46: the grade book of the pipeline against Medi's full manual reviews (scripts/review_grades.py)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import review_grades as RG  # noqa: E402


def _w(i, word, cat):
    return {"i": i, "t": "00:0%s" % i[0], "word": word, "cat": cat, "why": ""}


def test_pg_46_grade_book_counts_arabic_words_and_four_mistake_types():
    key = {"lines": {"1.00": "غير.", "2.00": "مرحبا كيفك", "3.00": "سما"},
           "words": [_w("1.00", "غير", "credit"), _w("2.00", "مرحبا", "credit"), _w("2.00", "كيفك", "repeat"),
                     _w("3.00", "سما", "slip")],
           "slips": [{"i": "3.00", "t": "00:03", "k": "vocab", "rule": None, "said": "سما", "ar": "عصافير"}]}
    ver = {"lines": {"1.00": "بيد.", "2.00": "مرحبا كيفك", "3.00": "سما"},
           "words": [_w("1.00", "بيد", "credit"), _w("2.00", "مرحبا", "credit"), _w("2.00", "كيفك", "credit"),
                     _w("3.00", "سما", "credit")],
           "slips": [{"i": "2.00", "t": "00:02", "k": "grammar", "rule": "A1", "said": "مرحبا", "ar": ""}]}
    g = RG.grade(ver, key)
    assert g["words"] == 4 and g["tracked"] == 1 and g["tracked_pct"] == 25.0
    assert g["mistakes"] == {"missed_slip": 1, "fake_slip": 1, "untracked": 1, "misheard": 1}
    assert g["per_100"] == 100.0
    assert RG.grade(key, key)["mistakes_total"] == 0


def test_pg_46_his_latin_word_the_reader_missed_is_untracked_not_misheard():
    assert RG.latin_unread("Ayan, Ayan is sick.", "عيان") == "Ayan"
    assert RG.latin_unread("Defect.", "كيفك") is None


def test_pg_46_only_full_reviews_are_graded_and_10_08_has_a_frozen_key():
    rv = {r["date"]: r for r in json.load(open(RG.REVIEWS_P, encoding="utf-8"))["reviews"]}
    assert rv["2026-10-08"]["full"] is True
    assert rv["2026-10-02"]["full"] is False
    assert sum(1 for r in rv.values() if not r["full"] and r["date"].startswith("2026-09")) == 1
    snap = json.load(open(RG.snap_path("2026-10-08"), encoding="utf-8"))
    assert snap["before"]["words"] and snap["key"]["words"]
    out = RG.build()
    by = {r["date"]: r for r in out["lessons"]}
    assert by["2026-10-02"]["status"] == "partial review, not graded" and "before" not in by["2026-10-02"]
    g = by["2026-10-08"]
    assert g["status"] == "graded" and g["before"]["tracked_pct"] < g["now"]["tracked_pct"]
    assert any(e["type"] == "misheard" and e["t"] == "32:05" and e["word"] == "غير" for e in g["before"]["list"])


def test_pg_46_grades_tab_on_ai_reports():
    html = open(os.path.join(REPO, "docs", "ai-reports.html"), encoding="utf-8").read()
    js = open(os.path.join(REPO, "docs", "js", "ai-reports-tabs.js"), encoding="utf-8").read()
    assert 'data-artab="grades"' in html and 'id="air-grades"' in html
    assert "'grades'" in js and "js/review-grades.js" in js


def test_first_publish_freeze_is_the_before_when_present(tmp_path, monkeypatch):
    """Protocol §2.1: data/lesson-work/review-grades/<date>.first.json (the hourly job's first publish, page + SHA) is the
    exam's "before"; git (before_commit) only when there is none."""
    monkeypatch.setattr(RG, "DIR", str(tmp_path))
    monkeypatch.setattr(RG, "REVIEWS_P", str(tmp_path / "reviews.json"))
    (tmp_path / "reviews.json").write_text(json.dumps({"reviews": [
        {"date": "2026-10-11", "full": True, "before_commit": "gitsha1", "key_commit": None}]}), encoding="utf-8")
    pages = []
    monkeypatch.setattr(RG, "page_at", lambda commit, date, repo=RG.REPO: (pages.append(commit), {"tag": "git:%s" % commit})[1])
    monkeypatch.setattr(RG, "snapshot", lambda d, date: {"from": d.get("tag")})
    RG.freeze("2026-10-11", log=lambda *a: None)                 # no first-publish file: before from git
    snap = json.load(open(RG.snap_path("2026-10-11"), encoding="utf-8"))
    assert snap["before"] == {"from": "git:gitsha1"} and snap["before_commit"] == "gitsha1"
    (tmp_path / "2026-10-11.first.json").write_text(json.dumps({"date": "2026-10-11", "sha": "firstsha", "page": {"tag": "first"}}), encoding="utf-8")
    pages.clear()
    RG.freeze("2026-10-11", log=lambda *a: None)
    snap = json.load(open(RG.snap_path("2026-10-11"), encoding="utf-8"))
    assert snap["before"] == {"from": "first"} and snap["before_commit"] == "firstsha"
    assert "gitsha1" not in pages                                # the before was not rebuilt from git
    assert snap["key"] == {"from": "git:None"}                   # the key is still today's page (key_commit null)


def test_10_09_first_publish_is_backfilled_from_the_hourly_commit():
    f = json.load(open(RG.first_path("2026-10-09"), encoding="utf-8"))
    assert f["sha"].startswith("aace7c9") and f["date"] == "2026-10-09"   # "Lessons 2026-10-09 loaded by the hourly job"
    assert f["page"]["turns"] and RG.first_publish("2026-10-09")[1] == f["sha"]


def _fast(date, t, secs, kind="rule-answer", mode="fast"):
    return {"id": "%s-%s" % (date, t), "lesson_date": date, "turn_t": t, "kind": kind, "proposal": "review:fast" if kind == "rule-answer" else None,
            "payload": {"review_mode": mode, "secs": secs}}


def test_minutes_and_coverage_of_a_fast_review(tmp_path, monkeypatch):
    """Protocol §4 (time is measured, not guessed) + council 2026-10-10: minutes_medi = the fast-mode rows' seconds per
    lesson; a fast review is graded only when every Arabic line of his has an answer (coverage_medi 1.0)."""
    monkeypatch.setattr(RG, "DIR", str(tmp_path))
    pick = tmp_path / "pick"
    pick.mkdir()
    (pick / "2026-10-12.json").write_text(json.dumps({"lines": [{"t": 10.0, "end": 14.0}, {"t": 20.0, "end": 21.0}, {"t": 30.0, "end": 30.5}]}), encoding="utf-8")
    (pick / "2026-10-13.json").write_text(json.dumps({"lines": [{"t": 5.0, "end": 6.0}, {"t": 8.0, "end": 9.0}]}), encoding="utf-8")
    rows = [_fast("2026-10-12", 10.0, 30), _fast("2026-10-12", 12.5, 18, kind="text"),   # a joined line counts once
            _fast("2026-10-12", 20.0, 42),
            _fast("2026-10-13", 5.0, 60), _fast("2026-10-13", 8.0, 60, kind="vocab"),
            {"id": "old", "lesson_date": "2026-10-08", "turn_t": 1.0, "kind": "text", "payload": {"text": "x"}}]   # the old way
    reviews = [{"date": "2026-10-08", "full": False, "note": "old way"}]
    out = RG.build(corrections=rows, reviews=reviews, pick_dir=str(pick))
    by = {r["date"]: r for r in out["lessons"]}
    assert by["2026-10-08"]["minutes_medi"] is None and by["2026-10-08"]["coverage_medi"] is None
    assert by["2026-10-08"]["status"] == "partial review, not graded"                      # unchanged
    a = by["2026-10-12"]
    assert a["minutes_medi"] == 1.5 and a["lines_checked"] == 2 and a["lines_total"] == 3 and a["coverage_medi"] == 0.667
    assert a["status"] == "partial review, not graded (2 of 3 lines)" and "before" not in a
    b = by["2026-10-13"]
    assert b["minutes_medi"] == 2.0 and b["coverage_medi"] == 1.0
    assert b["status"] == "no answer key frozen yet"             # full coverage: graded once its key is frozen
    assert RG.minutes_of([]) is None and RG.is_fast(_fast("x", 1, 1, kind="text")) and not RG.is_fast(rows[-1])


def test_a_complete_fast_review_freezes_its_own_key(tmp_path, monkeypatch):
    """Codex review 2026-10-11: a fast review that reached every line (coverage 1.0) is graded without a hand step: the
    build freezes its key (before = the first publish, key = today's page with his rows), instead of 'no answer key'."""
    monkeypatch.setattr(RG, "DIR", str(tmp_path))
    monkeypatch.setattr(RG, "REVIEWS_P", str(tmp_path / "reviews.json"))
    pick = tmp_path / "pick"
    pick.mkdir()
    (pick / "2026-10-13.json").write_text(json.dumps({"lines": [{"t": 5.0, "end": 6.0}, {"t": 8.0, "end": 9.0}]}), encoding="utf-8")
    (tmp_path / "2026-10-13.first.json").write_text(json.dumps({"date": "2026-10-13", "sha": "firstsha", "page": {"tag": "first"}}), encoding="utf-8")
    monkeypatch.setattr(RG, "page_at", lambda commit, date, repo=RG.REPO: {"tag": "today"})
    monkeypatch.setattr(RG, "snapshot", lambda d, date: {"from": d.get("tag")})
    monkeypatch.setattr(RG, "grade", lambda ver, key: {"from": ver.get("from"), "tracked_pct": 100.0, "per_100": 0.0, "list": []})
    rows = [_fast("2026-10-13", 5.0, 60), _fast("2026-10-13", 8.0, 60, kind="vocab")]
    out = RG.build(corrections=rows, reviews=[], pick_dir=str(pick))
    snap = json.load(open(RG.snap_path("2026-10-13"), encoding="utf-8"))
    assert snap["before"] == {"from": "first"} and snap["before_commit"] == "firstsha" and snap["key"] == {"from": "today"}
    row = {r["date"]: r for r in out["lessons"]}["2026-10-13"]
    assert row["status"] == "graded" and row["coverage_medi"] == 1.0 and row["before"]["from"] == "first"


def test_grades_tab_says_drift_and_shows_minutes_and_coverage():
    js = open(os.path.join(REPO, "docs", "js", "review-grades.js"), encoding="utf-8").read()
    assert "today's page vs the key: a regression check only, never an accuracy score" in js
    assert ">Today<" not in js and "Words tracked today" not in js and "Drift" in js
    assert "minutes_medi" in js and "coverage_medi" in js
    assert "Medi's time" not in js and "the student's time" in js        # PG-33: the student, never his name, on screen
    built = json.load(open(RG.OUT_P, encoding="utf-8"))
    assert all("minutes_medi" in r and "coverage_medi" in r for r in built["lessons"])
