# -*- coding: utf-8 -*-
"""PG-27: every lesson says whether the second AI listen (Gemini re-hear) is still pending (scripts/rehear_status.py).
Medi 2026-10-04: "just make sure to mark that its bending still on the lessons". No network."""
import json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import rehear_status as RH  # noqa: E402

PAGE = '<!doctype html><title>x</title><main><h1>Lesson · %s</h1><div class="note">Unreviewed speech recognition.</div><p dir="auto" class="turn"><button class="t" data-t="2.46" data-row="a:row:0"><small>00:02</small></button><b>Medi</b>: <span class="words">مرحبا.</span></p></main>'


def _repo(tmp_path, dates):
    d = tmp_path / "docs" / "lessons"
    d.mkdir(parents=True)
    for x in dates:
        (d / (x + ".html")).write_text(PAGE % x, encoding="utf-8")
    (d / "2026-09-11-report.html").write_text("<h1>a report, not a lesson</h1>", encoding="utf-8")
    return str(tmp_path)


def _read(root, date):
    return open(os.path.join(root, "docs", "lessons", date + ".html"), encoding="utf-8").read()


def test_pg27_a_new_lesson_joins_as_pending_and_existing_rows_are_never_touched(tmp_path):
    root = _repo(tmp_path, ["2026-09-11", "2026-10-02"])
    added, stamped = RH.build(root)
    assert added == ["2026-09-11", "2026-10-02"] and stamped == added
    doc = RH.load(root)
    assert sorted(doc["lessons"]) == added and "2026-09-11-report" not in doc["lessons"]
    assert all(r["status"] == "pending" and re.fullmatch(r"\d{4}-\d\d-\d\d", r["since"]) for r in doc["lessons"].values())
    # a person moves one lesson on; the next build keeps that row as it is and only adds the new lesson
    doc["lessons"]["2026-09-11"] = {"status": "applied", "since": "2026-11-01", "note": "reviewed by Medi"}
    RH.save(doc, root)
    open(os.path.join(root, "docs", "lessons", "2026-10-09.html"), "w", encoding="utf-8").write(PAGE % "2026-10-09")
    added, stamped = RH.build(root)
    assert added == ["2026-10-09"] and stamped == ["2026-09-11", "2026-10-09"]
    doc = RH.load(root)
    assert doc["lessons"]["2026-09-11"] == {"status": "applied", "since": "2026-11-01", "note": "reviewed by Medi"}
    assert doc["lessons"]["2026-10-09"]["status"] == "pending"
    assert RH.build(root) == ([], []) and RH.check(root) == []          # nothing new: nothing written
    assert "Second listen: applied" in _read(root, "2026-09-11") and "Second listen: pending" in _read(root, "2026-10-09")


def test_pg27_the_page_mark_is_one_block_under_the_title_and_leaves_the_transcript_alone(tmp_path):
    root = _repo(tmp_path, ["2026-10-02"])
    RH.build(root)
    page = _read(root, "2026-10-02")
    assert page.count(RH.START) == 1 and page.index("</h1>") < page.index(RH.START) < page.index('<div class="note">')
    assert page.replace(RH.BLOCK_RE.search(page).group(0), "") == PAGE % "2026-10-02"      # nothing else changed
    assert RH.stamp(page, RH.chip("2026-10-02", RH.load(root))) == page                   # stamping twice changes nothing
    c = RH.chip("2026-10-02", RH.load(root))
    assert c["label"] == "Second listen: pending" and c["tip"] in page and 'data-rehear="pending"' in page
    # a changed status replaces the block, never adds a second one
    again = RH.stamp(page, RH.chip("x", {"lessons": {"x": {"status": "proposed"}}}))
    assert again.count(RH.START) == 1 and "Second listen: changes to review" in again and "Second listen: pending" not in again


def test_pg27_no_status_claims_more_than_is_true():
    assert list(RH.STATUS) == ["pending", "submitted", "proposed", "applied"]
    for st in ("pending", "submitted", "proposed"):                       # nothing of Gemini's is in the transcript yet
        label, tip = RH.STATUS[st]
        assert "ElevenLabs only" in tip and "applied" not in label and "in the transcript" not in tip, st
    assert "has not been run" in RH.STATUS["pending"][1] and "Gemini" in RH.STATUS["pending"][1]
    assert "not reviewed" in RH.STATUS["proposed"][1] and "none is applied" in RH.STATUS["proposed"][1]
    # a missing row or a status nobody defined is shown as pending, never as more
    assert RH.chip("2030-01-01", {"lessons": {}})["status"] == "pending"
    assert RH.chip("d", {"lessons": {"d": {"status": "done!"}}})["label"] == "Second listen: pending"


def test_pg27_check_names_an_unmarked_page_and_a_bad_status(tmp_path):
    root = _repo(tmp_path, ["2026-10-02", "2026-10-03"])
    assert len(RH.check(root)) == 2                                        # no rows yet
    RH.build(root)
    open(os.path.join(root, "docs", "lessons", "2026-10-03.html"), "w", encoding="utf-8").write(PAGE % "2026-10-03")   # the page was re-made
    doc = RH.load(root)
    doc["lessons"]["2026-10-02"]["status"] = "finished"
    RH.save(doc, root)
    bad = RH.check(root)
    assert len(bad) == 2 and "2026-10-02: status 'finished'" in bad[0] and "2026-10-03: the lesson page does not carry its mark" in bad[1]


def test_pg27_every_published_lesson_is_marked_on_its_page_and_on_the_list():
    assert RH.check(ROOT) == []
    doc = RH.load(ROOT)
    rows = {L["date"]: L for L in json.load(open(os.path.join(ROOT, "docs", "data", "lessons.json"), encoding="utf-8"))["lessons"]}
    dates = RH.published(ROOT)
    assert dates and set(dates) == set(rows)
    for d in dates:
        c = RH.chip(d, doc)
        assert rows[d].get("rehear") == c, d                               # the list shows exactly what the source says
        assert c["label"] in _read(ROOT, d) and c["tip"] in _read(ROOT, d), d


def test_pg27_the_list_draws_the_chip_and_the_builders_keep_it_up():
    js = open(os.path.join(ROOT, "docs", "js", "lessons-page.js"), encoding="utf-8").read()
    assert "function rehearChip(L)" in js and "box.appendChild(rh)" in js and "ls-rehearnote" in js
    assert "L.rehear.label" in js and "Second listen" not in js            # the words come from the data, not the page code
    css = open(os.path.join(ROOT, "docs", "css", "lessons.css"), encoding="utf-8").read()
    assert "#anees-bank .ls-rehear{" in css and "var(--ab-muted)" in css.split("#anees-bank .ls-rehear{")[1].split("}")[0]
    b = open(os.path.join(ROOT, "scripts", "build_lessons_page_data.py"), encoding="utf-8").read()
    assert "RH.build(REPO)" in b and '"rehear": RH.chip(date, rehear_doc)' in b
    h = open(os.path.join(ROOT, "scripts", "hourly_lessons.py"), encoding="utf-8").read()
    assert h.count("data/lesson-work/rehear-status.json") >= 2             # committed with the lesson and with the run's built files
    src = open(os.path.join(ROOT, "scripts", "rehear_status.py"), encoding="utf-8").read()
    assert "requests" not in src and "urllib" not in src and "http" not in src.replace("html", "")     # no network, no paid call
