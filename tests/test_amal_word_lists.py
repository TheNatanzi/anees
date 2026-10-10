# -*- coding: utf-8 -*-
"""Amal's word lists (planted-mistake tests, run by the publish guard).

WS-15 (Medi 2026-09-23: "we dont need to add proper nouns like kabaab and ma2loobe and cake and countries"): dish names,
foods, brands, loan words and countries never go on Amal's 'not on sheet' list (build_amal_review.py) or the Tutor hub
'New words' task (amal_new_words.py, both the string candidates and a reader's 'new' verdict).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import loanwords as LW
import amal_new_words as N
import build_amal_review as BR


def _card(arabic, t, english="x"):
    return {"arabic": arabic, "on_sheet": False, "t": t, "mmss": "00:01", "english": english, "said": None, "fix": None}


def test_WS_15_dishes_foods_loanwords_countries_never_on_amals_not_on_sheet_list(tmp_path):
    # the 7 real moments the rule removes today + words that must stay
    planted = ["مقلوبة", "كعكة / بسكوتة", "cash (بدفع cash)", "أمريكا", "الزعفران", "ماكينة الرز", "الـ air conditioning تبعي", "كباب"]
    kept = ["دكتور عام", "بلد (one) / بلاد (countries)", "عرس", "تبعي", "متشجع"]
    lesson = {"vocab_errors": [_card(a, i) for i, a in enumerate(planted + kept)]
              + [{"arabic": "شنطة", "on_sheet": True, "t": 99}]}
    (tmp_path / "2026-10-01.json").write_text(json.dumps(lesson, ensure_ascii=False), encoding="utf-8")
    cards, skipped = BR.sheet_new_words(str(tmp_path), clips=False)
    assert sorted(c["arabic"] for c in cards) == sorted(kept)
    assert skipped == set(planted)


def test_WS_15_loan_tokens_arabic_and_arabizi():
    for w in ("كباب", "بالكباب", "المقلوبة", "kabaab", "ma2loobe", "cake", "pizza", "il-kabab", "بيتزا"):
        assert LW.loan_token(w), w
    for w in ("ممتاز", "لفة", "بجرب", "mitshajje3", "حلو", "عرس"):
        assert not LW.loan_token(w), w
    assert LW.loan_entry("في لبنان") and LW.loan_entry("Lebanon")      # countries (scripts/names.py)
    assert not LW.loan_entry("countries")                             # the word 'country' itself is vocabulary


def test_WS_15_new_words_task_drops_loanwords_at_both_stages():
    idx = N.doc_index({"items": [{"key": "shanta", "arabizi": "Shanta", "arabic": "شنطة", "english": "bag"}]})
    lesson = {"turns": [{"t": 1.0, "who": "Amal", "text": "بنطبخ مقلوبة وكباب"},
                        {"t": 2.0, "who": "chat", "typed_by": "Amal", "text": "ma2loobe pizza mitshajje3"}]}
    C = N.candidates("2026-10-01", lesson=lesson, index=idx, spans=[])
    keys = {c["key"] for c in C["candidates"]}
    assert not keys & {"مقلوبه", "وكباب", "ma2loobe", "pizza"}
    assert "mitshajje3" in keys and C["excluded_by_string_check"]["loanword"] >= 4
    # a reader that still says 'new' on a dish is overruled; nothing reaches Amal
    V = [{"date": "2026-10-01", "key": "مقلوبه", "verdict": "new", "arabic": "مقلوبة", "t": 1.0},
         {"date": "2026-10-01", "key": "kabaab", "verdict": "new", "arabizi": "kabaab", "t": 1.5},
         {"date": "2026-10-01", "key": "mitshajje3", "verdict": "new", "arabizi": "mitshajje3", "t": 2.0},
         {"date": "2026-10-01", "key": "pizza", "verdict": "loanword", "t": 2.0}]
    out = N.build(V, taps={}, today="x")
    assert [i["key"] for i in out["items"]] == ["mitshajje3"]
    assert out["excluded"]["2026-10-01"]["loanword"] == 3


# AM-11 (Medi 2026-10-02: "bring it to her attention if she wants to add it to the document, save it for a future
# lesson, or forget it" + "we should be doing this for all new lessons"): the hourly job's same-day review runs the
# new-words step for EVERY new lesson, a reader that leaves candidates unjudged fails the lesson (no silent skip), and
# the Tutor hub card offers the three choices.
import subprocess, types
import review_lesson as RL


def _repo(tmp_path, d, cands):
    w = tmp_path / "data" / "lesson-work" / "amal-new-words"; w.mkdir(parents=True)
    (w / f"{d}.candidates.json").write_text(json.dumps({"date": d, "candidates": [{"key": k, "t": 1.0} for k in cands]}), encoding="utf-8")
    return tmp_path


def _run(*args):
    return subprocess.CompletedProcess(args, 0)


def test_AM_11_a_reader_that_leaves_words_unjudged_fails_the_lesson(tmp_path):
    repo, failures, calls = _repo(tmp_path, "2026-10-08", ["bajarreb", "laffe"]), [], []
    left = RL.new_words_step("2026-10-08", False, failures, repo=str(repo), reader=lambda *a, **k: calls.append(a[1]), run=_run)
    assert calls == ["2026-10-08 new words"] and len(left) == 2
    assert any("2 candidate(s) of 2026-10-08 not judged" in f for f in failures)


def test_AM_11_every_candidate_judged_passes_and_new_ones_reach_the_tutor_card(tmp_path):
    d = "2026-10-08"
    repo, failures = _repo(tmp_path, d, ["bajarreb", "كتير"]), []
    vp = repo / "data" / "lesson-work" / "amal-new-words-verdicts.json"
    rows = [{"date": d, "key": "bajarreb", "verdict": "new", "arabizi": "bajarreb", "english": "I try", "t": 1.0},
            {"date": d, "key": "كتير", "verdict": "function", "t": 1.0}]
    reader = lambda *a, **k: vp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    assert RL.new_words_step(d, False, failures, repo=str(repo), reader=reader, run=_run) == [] and failures == []
    out = N.build(rows, taps={}, today="x")
    assert [(i["key"], i["status"]) for i in out["items"]] == [("bajarreb", "open")]
    js = open(os.path.join(REPO, "docs", "js", "hub", "new-words-task.js"), encoding="utf-8").read()
    for kind in ("newword_add_new", "newword_add_old", "newword_later", "newword_forget"):
        assert f"['{kind}'," in js
    # lessons before the start date are never asked (and never cost a reader)
    assert RL.new_words_step("2026-09-30", False, failures, repo=str(repo), reader=lambda *a, **k: 1 / 0, run=_run) == []


def test_AM_11_the_hourly_job_reviews_every_new_lesson_and_the_review_runs_the_step(tmp_path, monkeypatch):
    import hourly_lessons as H
    root = tmp_path / "repo"; (root / "docs" / "data").mkdir(parents=True)
    monkeypatch.setattr(H, "ROOT", root)
    fdb = types.ModuleType("db"); fdb.rest = lambda *a, **k: {"events": []}; fdb.select = lambda *a, **k: []
    monkeypatch.setitem(sys.modules, "db", fdb)
    monkeypatch.setattr(H, "build_clips", lambda *a, **k: None)
    seen = []
    monkeypatch.setattr(H.subprocess, "run", lambda cmd, *a, **k: seen.append([str(c) for c in cmd]) or subprocess.CompletedProcess(cmd, 0, "", ""))
    H.refresh_published(["2026-10-05", "2026-10-06"], tmp_path / "raw", tmp_path / "work")
    reviewed = [c[2] for c in seen if len(c) > 2 and c[1].endswith("review_lesson.py")]
    assert reviewed == ["2026-10-05", "2026-10-06"]
    src = open(os.path.join(REPO, "scripts", "review_lesson.py"), encoding="utf-8").read()
    main_src = src[src.index("def main():"):]
    assert "new_words_step(d, a.dry_run, failures)" in main_src
    assert main_src.index("new_words_step(") < main_src.index('"build_tutor_data.py"')


# WS-19 (Medi 2026-10-02: "the glue words should be added to the doc, bring to her attention" + "the glue words are likely
# going to be old words she forgot to add"): every glue word not on her Doc is a card on her New words task with the hint,
# nothing pre-selected, and Anees marks it old (by Medi) so it never counts as NEW on Flashcards once she adds it.
def test_WS_19_glue_words_not_on_her_doc_go_on_her_card_marked_old_by_medi():
    import glue_words as G, word_marks as WM, check_rules as CR
    assert set(G.GLUE_WORDS) == CR.GLUE
    doc = {"items": [{"key": "bas", "arabizi": "Bas", "arabic": "بس"}, {"key": "la", "arabizi": "la", "arabic": "لَ"},
                     {"key": "mAshi", "arabizi": "Maashi", "arabic": "ماشي"}]}
    missing = {k for k, _, _ in G.not_on_doc(doc)}
    assert "bas" not in missing and "mashi" not in missing                   # on her Doc (by meaning: Maashi)
    assert {"la", "tamam", "tayeb", "shu"} <= missing                        # لا 'no' is not her لَ 'for/to'
    marks = WM.load()
    out = N.build([], taps={}, today="x", marks=marks, doc=doc, glue=True)
    cards = {i["key"]: i for i in out["items"] if i.get("source") == "glue"}
    assert set(cards) == {"glue:" + k for k in missing}
    t = cards["glue:tamam"]
    assert t["status"] == "open" and t["tap"] is None and t["hint"] == G.HINT and t["arabizi"] is None
    # every glue word missing from her REAL Doc today carries Medi's old mark in data/word-marks.json
    real_missing = {k for k, _, _ in G.not_on_doc()}
    marked = {m.get("glue") for m in marks["marks"] if m.get("mark") == "old" and m.get("by") == "medi"}
    assert real_missing <= marked
    ages = WM.resolved_ages(marks, {"items": []})
    assert WM.old_doc_words([{"key": "tamAm", "arabizi": "Tamaam", "arabic": "تمام"}], ages)    # old when it reaches her Doc
