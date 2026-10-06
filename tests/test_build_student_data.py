# -*- coding: utf-8 -*-
"""scripts/build_student_data.py (Medi 2026-10-05): the Student tab's data - her uploads as sets, the homework score (Amal's
verdicts only, PG-29), her overrules as rules (S6), and the Shaky words of the last 2 lessons (FC-13). Offline: no database."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_student_data as B


def T(id, kind, **k):
    return {"id": id, "kind": kind, "created_at": "2026-10-05T10:00:00Z", "prompt": "p", **k}


def R(id, task, ai=None):
    return {"id": id, "task_id": task, "answer": "ana bas7a", "ai": ai, "created_at": "2026-10-05T11:00:00Z"}


def V(id, reply, verdict, agrees, **k):
    return {"id": id, "reply_id": reply, "kind": "verdict", "verdict": verdict, "agrees": agrees, "created_at": "2026-10-05T12:00:00Z", **k}


def test_PG_29_homework_score_is_amals_verdicts_only_right_1_close_half_wrong_0():
    tasks = [T("t1", "translate"), T("t2", "create", words=["Jumle"]), T("t3", "question"), T("t4", "cards", set_ref="q:1", n_cards=10)]
    ai = {"verdict": "right"}
    replies = [R("r1", "t1", ai), R("r2", "t2", ai), R("r3", "t3", ai)]
    assert B.score(tasks, replies, [])["pct"] is None                       # the AI alone never makes a number
    sc = B.score(tasks, replies, [V("v1", "r1", "right", True), V("v2", "r2", "close", False), V("v3", "r3", "wrong", False)])
    assert (sc["done"], sc["pct"], sc["total"], sc["overruled"]) == (3, 50.0, 3, 2)
    # an undone verdict puts the answer back to waiting
    sc2 = B.score(tasks, replies, [V("v1", "r1", "right", True), {"id": "x", "reply_id": "r1", "kind": "undo", "undoes": "v1", "created_at": "2026-10-05T12:05:00Z"}])
    assert sc2["done"] == 0 and sc2["waiting"] == 3


def test_S6_every_overrule_is_listed_as_a_correction_rule_with_her_note_and_fix():
    tasks = [T("t1", "translate", direction="en_ar", prompt="I woke up late")]
    replies = [R("r1", "t1", {"verdict": "wrong", "reason": "x"})]
    out = B.overrules(tasks, replies, [V("v1", "r1", "close", False, note="bas7a is fine here", fix="ana s7eet met2a55er")])
    assert len(out) == 1 and out[0]["ai_said"] == "wrong" and out[0]["amal_says"] == "close" and out[0]["fix"] == "ana s7eet met2a55er"
    assert B.overrules(tasks, replies, [V("v1", "r1", "wrong", True)]) == []    # a confirm is not a rule


def test_FC_13_uploads_become_sets_keyed_by_upload_and_row_with_her_text_as_written():
    up = {"id": "abcdefgh", "kind": "upload", "title": "Function words", "keep": "permanent", "created_at": "2026-10-05T09:00:00Z",
          "rows": [{"arabizi": "Awal", "arabic": "أول", "english": "First / beginning"}, {"arabizi": "", "arabic": "", "english": "nothing"}]}
    sets = B.upload_sets([up])
    assert len(sets) == 1 and sets[0]["id"] == "u:abcdefgh" and sets[0]["n"] == 1 and sets[0]["cards"][0]["key"] == "u:abcdefgh:1"
    assert sets[0]["cards"][0]["english"] == "First / beginning"
    assert B.upload_sets([up, {"id": "undo1234", "kind": "undo", "undoes": "abcdefgh", "created_at": "2026-10-05T09:30:00Z"}]) == []


def test_FC_13_shaky_words_come_from_the_last_2_lessons_wrong_and_asked_only(tmp_path):
    d = tmp_path / "lessons"; d.mkdir()
    def lesson(date, errs):
        (d / f"{date}.json").write_text(json.dumps({"vocab_errors": errs}, ensure_ascii=False), encoding="utf-8")
    lesson("2026-09-30", [{"kind": "wrong", "t": 1, "arabic": "موعد", "sheet_key": "maw3ed", "english": "appointment"}])        # third lesson back: left out
    lesson("2026-10-01", [{"kind": "asked", "t": 375, "arabic": "متشجع", "english": "motivated"}, {"kind": "wrong", "t": 3556, "arabic": "the second thing", "english": "x"}])
    lesson("2026-10-02", [{"kind": "wrong", "t": 422, "fix": "صحيت", "sheet_key": "ana bas7a", "english": "I woke up late today", "on_sheet": True},
                          {"kind": "correct", "t": 500, "arabic": "بيت"}])
    S = B.shaky_words(lessons_dir=str(d))
    assert S["lessons"] == ["2026-10-01", "2026-10-02"]
    keys = [w["key"] for w in S["words"]]
    assert keys == ["sh:2026-10-01:375", "ana bas7a"]            # the English-only audit row and the 'correct' row are not cards
    assert S["words"][1]["arabic"] == "صحيت" and S["words"][1]["kind"] == "wrong"


def test_the_committed_shaky_words_file_matches_the_last_two_lessons_on_disk():
    p = os.path.join(REPO, "docs", "data", "shaky-words.json")
    S = json.load(open(p, encoding="utf-8"))
    assert S["lessons"] == B.lesson_dates()[-2:]
    fresh = B.shaky_words()
    assert [w["key"] for w in S["words"]] == [w["key"] for w in fresh["words"]]


def test_build_writes_the_score_and_the_cards_assignments():
    up, hw = B.build([], [T("t4", "cards", set_ref="q:1", set_title="Introductions", n_cards=33, lesson_date="2026-10-07")], [], [], now="2026-10-05T12:00:00-07:00")
    assert up["sets"] == [] and hw["score"]["total"] == 0 and hw["score"]["pct"] is None
    assert hw["cards"][0]["set_ref"] == "q:1" and hw["cards"][0]["lesson_date"] == "2026-10-07"


def test_PG_28_student_is_in_every_menu_right_under_tutor():
    """Medi 2026-10-05: "create a new tab 'student' below tutor"."""
    import glob, re
    pages = [p for p in glob.glob(os.path.join(REPO, "docs", "*.html")) if 'class="ab-nav"' in open(p, encoding="utf-8").read() and 'href="tutor.html">Tutor</a>' in open(p, encoding="utf-8").read()]
    assert len(pages) >= 10
    for p in pages:
        src = open(p, encoding="utf-8").read()
        assert re.search(r'href="tutor.html">Tutor</a><a class="ab-nav"( aria-current="page")? href="student.html">Student</a>', src), os.path.basename(p)
    assert os.path.exists(os.path.join(REPO, "docs", "student.html")) and os.path.exists(os.path.join(REPO, "docs", "js", "student.js"))
