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
