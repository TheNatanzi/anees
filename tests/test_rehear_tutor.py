# -*- coding: utf-8 -*-
"""TR-27: the tutor's ear decides a second-listen change that could hide a mistake (2026-10-07)."""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import rehear_tutor as RT  # noqa: E402
import transcript_fixes as TF  # noqa: E402

LINE = {"i": 7, "t": 100.0, "end": 103.0}
HERS = [{"t": 110.0, "end": 112.0, "text": "انزعجتوا. انزعجتوا"}, {"t": 150.0, "end": 151.0, "text": "الولد بيكون ولد", "chat": True}]
EMPTY = {"slip": {}, "wordsaid": {}, "oldnew": {}, "ownfix": {}, "wordthere": {}, "oneortwo": {}}


def test_TR_27_a_change_toward_the_tutors_own_word_within_30_s_is_held_spoken_or_typed():
    """Council final approval 2026-10-05 ('widen the hold rule to cover swaps toward the teacher's form'); Medi 2026-10-07
    'run the changes'. انزعجتم -> انزعجتوا when she says انزعجتوا 10 s later: held. The typed chat counts too (الولد ... 50 s
    later is outside the window; at 20 s it is inside)."""
    r = {"i": 7, "t": 100.0, "engine": "انزعجتم كتير", "heard": "انزعجتوا كتير", "kind": "words"}
    v = RT.verdict("2026-09-10", r, LINE, HERS, {}, EMPTY)
    assert v["status"] == "held" and v["toward"] == ["انزعجتوا"] and "tutor's own word" in v["why"]
    chat = [{"t": 120.0, "end": 120.0, "text": "الولد بيكون ولد", "chat": True}]
    r2 = {"i": 7, "t": 100.0, "engine": "الولاد بيكون ولاد", "heard": "الولد بيكون ولد", "kind": "words"}
    assert RT.verdict("2026-09-28", r2, LINE, chat, {}, EMPTY)["status"] == "held"
    assert RT.verdict("2026-09-28", r2, LINE, [dict(chat[0], t=140.0)], {}, EMPTY)["status"] == "apply"    # 40 s later: not her echo


def test_TR_27_an_alphabet_only_change_or_an_unrelated_word_is_applied():
    r = {"i": 7, "t": 100.0, "engine": "enza3ajtu kteer", "heard": "انزعجتوا كتير", "kind": "alphabet"}
    assert RT.verdict("2026-09-10", r, LINE, HERS, {}, EMPTY)["status"] == "apply"
    r = {"i": 7, "t": 100.0, "engine": "بدي روح", "heard": "بدي أروح", "kind": "words"}
    assert RT.verdict("2026-09-10", r, LINE, HERS, {}, EMPTY)["status"] == "apply"
    # the same word in the other alphabet is not an added word (enza3ajtu / انزعجتوا); a different Arabic word with the same consonants is
    assert RT.added_words("enza3ajtu kteer", "انزعجتوا كتير") == [] and RT.added_words("الولاد بيكون ولاد", "الولد بيكون ولد") == ["الولد", "ولد"]


def test_TR_27_a_line_on_a_mistake_the_tutor_confirmed_is_held():
    r = {"i": 7, "t": 100.0, "engine": "ما يقدر أكتب", "heard": "ما بيقدر يكتب", "kind": "words"}
    conf = {"2026-08-25": [(101.5, "FA-72ad65fd")]}
    v = RT.verdict("2026-08-25", r, LINE, [], conf, EMPTY)
    assert v["status"] == "held" and v["confirmed"] == ["FA-72ad65fd"]
    assert RT.verdict("2026-08-25", r, LINE, [], {"2026-08-25": [(130.0, "FA-x")]}, EMPTY)["status"] == "apply"


def test_TR_27_only_the_tutors_own_listen_releases_or_takes_out_a_line():
    """Her 27-line gate (12 'he said it wrong' -> the engine's text stays; 15 'right' -> applied), the 84 'did he say the
    word' lines (yes / no), the 11 old-or-new lines. 'Not sure' stays held; 'something else' keeps the engine's text."""
    r = {"i": 7, "t": 100.0, "engine": "انزعجتم كتير", "heard": "انزعجتوا كتير", "kind": "words"}
    K = dict(EMPTY, slip={("2026-09-10", 7): {"uid": "FA-cb7be627", "mistake": "yes", "choice": "new", "at": "2026-10-06"}})
    v = RT.verdict("2026-09-10", r, LINE, HERS, {}, K)
    assert v["status"] == "out" and v["list"] == "slip-check" and "said it wrong" in v["why"]
    K["slip"][("2026-09-10", 7)]["mistake"] = "no"
    assert RT.verdict("2026-09-10", r, LINE, HERS, {}, K)["status"] == "apply"          # her word beats the hold
    K["slip"][("2026-09-10", 7)]["mistake"] = "not_sure"
    assert RT.verdict("2026-09-10", r, LINE, HERS, {}, K)["status"] == "held"
    K = dict(EMPTY, wordsaid={("2026-09-10", 7): {"said": "yes", "word": "انزعجتوا", "at": "2026-10-07"}})
    assert RT.verdict("2026-09-10", r, LINE, HERS, {}, K)["status"] == "apply"
    K["wordsaid"][("2026-09-10", 7)]["said"] = "no"
    assert RT.verdict("2026-09-10", r, LINE, HERS, {}, K)["status"] == "out"
    K = dict(EMPTY, oldnew={("2026-09-10", 7): {"choice": "old", "at": "2026-10-07"}})
    assert RT.verdict("2026-09-10", r, LINE, [], {}, K)["status"] == "out"
    K["oldnew"][("2026-09-10", 7)]["choice"] = "new"
    assert RT.verdict("2026-09-10", r, LINE, [], {}, K)["status"] == "apply"
    K["oldnew"][("2026-09-10", 7)]["choice"] = "other"
    assert RT.verdict("2026-09-10", r, LINE, [], {}, K)["status"] == "out"


def test_TR_27_the_tutors_pick_of_an_ai_run_wins_over_his_own_correction_on_the_line():
    """own-fix (AM-06: her answer wins): a whole-line row by tutor-listen with wins replaces the line even though his
    correction lands on it; his row stays in the file and is recorded as superseded."""
    turns = [{"t": 932.0, "who": "Medi", "text": "Or was it Juma?"}, {"t": 940.0, "who": "Amal", "text": "الجمعة."}]
    his = {"date": "2026-10-02", "t": 932.0, "who": "Medi", "engine_wrote": "Juma", "heard": "جمعة", "rule": "PR-15", "by": "medi"}
    hers = {"date": "2026-10-02", "t": 932.0, "who": "Medi", "line": "Or was it Juma?", "heard_line": "الجمعة", "engine_wrote": "Or was it Juma?", "heard": "الجمعة",
            "spans": [{"engine_wrote": "Or was it Juma?", "heard": "الجمعة"}], "rule": "TR-27", "by": "tutor-listen", "wins": True}
    out = TF.apply("2026-10-02", turns, rows=[his, hers])
    assert out[0]["text"] == "الجمعة" and out[0]["engine"] == "Or was it Juma?"
    assert any(h.get("superseded") and h.get("by") == "medi" for h in out[0]["heard"])
    out = TF.apply("2026-10-02", turns, rows=[his, dict(hers, wins=False)])           # without wins his correction stays (decision 2)
    assert out[0]["text"] == "Or was it جمعة?"
    K = dict(EMPTY, ownfix={("2026-10-02", 251): [{"item": "2026-10-02:251", "pick": "ai run 2,3", "runs": ["Or is it Juma?", "الجمعة", "الجمعة"], "his": "جمعة",
                                                  "engine_wrote": "Juma", "engine_line": "Or was it Juma?", "t": 932.02, "at": "2026-10-07"}],
                            ("2026-10-02", 119): [{"item": "2026-10-02:119", "pick": "medi", "runs": ["هاد الصبح"], "his": "هادي", "engine_wrote": "عادي",
                                                  "engine_line": "عادي الصباح.", "t": 533.84, "at": "2026-10-07"}]})
    rows, listed = RT.own_fix_rows(K)
    assert len(rows) == 1 and rows[0]["heard_line"] == "الجمعة" and rows[0]["wins"] and rows[0]["by"] == "tutor-listen" and rows[0]["line"] == "Or was it Juma?"
    assert listed == [{"date": "2026-10-02", "i": 119, "picks": ["medi"], "why": "the tutor kept the student's own correction"}]


def test_TR_27_word_there_and_one_or_two_answers_become_rulings_never_deleted_rows():
    K = dict(EMPTY, wordthere={"wb:abc": {"said": "no", "word": "جو", "date": "2026-09-10", "event_id": "abc", "at": "2026-10-07"}},
             oneortwo={"2026-08-25:FA-1+FA-2": {"same": "same", "ids": ["FA-1", "FA-2"], "first_read": [True, False], "date": "2026-08-25", "slips": [], "at": "2026-10-07"},
                       "2026-09-04:FA-3+FA-4": {"same": "different", "ids": ["FA-3", "FA-4"], "first_read": [False, True], "date": "2026-09-04", "slips": [], "at": "2026-10-07"}})
    r = RT.word_there_rulings(K)
    assert r == [{"conflict": "wb:abc", "answer": "no", "by": "amal", "rule": "TR-27", "list": "word-there", "date": "2026-09-10", "word": "جو", "event_id": "abc",
                  "at": "2026-10-07", "why": "the tutor listened: the word is not there - the credit is removed"}]
    import tempfile
    d = tempfile.mkdtemp()
    RT.DUPES_P, RT.ONE_OR_TWO_P = os.path.join(d, "duplicates.json"), os.path.join(d, "one-or-two-tutor.json")
    json.dump({"pairs": []}, open(RT.DUPES_P, "w", encoding="utf-8"))
    added, listed = RT.one_or_two(K)
    assert [(a["keep"], a["drop"], a["rule"]) for a in added] == [("FA-1", "FA-2", "LS-16")]
    assert [x["same"] for x in listed] == ["same", "different"] and listed[1]["ids"] == ["FA-3", "FA-4"]
    added2, _ = RT.one_or_two(K)
    assert added2 == []                                                                  # the second run adds no pair twice


def test_TR_27_the_plan_lists_held_taken_out_and_applied_lines_and_the_chip_counts_them():
    import rehear_apply as A
    P = {"summary": {"lines_changed": 10, "word_changes": 4, "alphabet_only": 6, "his_corrections_all_3_runs_disagree": 0, "held": 0, "held_mix": 0,
                     "no_agreement": 1, "withheld_by_spot_check": 0, "held_tutor": 3, "taken_out_by_tutor": 2, "applied_by_tutor": 1, "amal_lines_changed": 0},
         "lines_changed": []}
    A.limited = lambda date: False
    row = A.status_row("2026-09-21", P, since="2026-10-07")
    assert row["status"] == "applied" and row["tutor_wait"] == 3
    assert "3 lines wait for the tutor's ear" in row["note"] and "2 changes taken out on the tutor's word" in row["note"] and "1 applied on the tutor's word" in row["note"]
