# -*- coding: utf-8 -*-
"""AM-32: grammar Claude HEARD the tutor teach in a lesson transcript becomes a card on her 'Add grammar' list (the same
proposal shape, ids and Yes / Change it / Not a rule flow as AM-31); one lean read per lesson; GR-18 not duplicated."""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import tutor_grammar as T  # noqa: E402

D = "2026-10-09"
BUCKETS = [{"id": "A1", "family": "A", "name": "el- (the)", "one_line": "el- marks"}, {"id": "A17", "family": "A", "name": "nafs + el-", "one_line": "z"},
           {"id": "C12", "family": "C", "name": "a doing verb", "one_line": "w"}]
TURNS = [{"t": 100.0, "who": "Medi", "text": "remind me to call"}, {"t": 590.0, "who": "Amal", "text": "شو بدك تعمل؟"},
         {"t": 600.0, "who": "Medi", "text": "أنا بدي روح عالبحر"},
         {"t": 604.0, "who": "Amal", "text": "لا، بعد بدي الفعل بدون ب: بدي أروح. بدي أروح عالبحر"},
         {"t": 700.0, "who": "Medi", "text": "هو أطول من أنا"},
         {"t": 703.0, "who": "Amal", "text": "أطول مني"},
         {"t": 900.0, "who": "chat", "typed_by": "Amal", "text": "shu ma = whatever"}]
FIND = {"t": "10:04", "quote": "بعد بدي الفعل بدون ب", "family": "B", "name": "bidd + bare verb", "one_line": "After biddi the verb has no b-.",
        "formula": "biddi + verb without b-", "examples": [{"arabizi": "", "arabic": "بدي أروح عالبحر", "english": "I want to go to the sea"},
                                                           {"arabizi": "biddi aakol", "arabic": "", "english": "I want to eat"}],
        "why": "she explained that the b- drops after biddi", "overlaps": {"id": "C12", "why": "both about verbs"}}


def runner_for(found, calls=None):
    def run(prompt):
        if calls is not None:
            calls.append(prompt)
        return json.dumps({"result": json.dumps({"found": found}), "total_cost_usd": 0.05, "is_error": False})
    return run


def repo(tmp_path, proposals=None):
    for d in ("docs/data/lessons", "data/lesson-work/lesson-types", "scripts", "data/lesson-work/full-audit"):
        os.makedirs(tmp_path / d, exist_ok=True)
    (tmp_path / "docs/data/grammar-buckets.json").write_text(json.dumps({"buckets": BUCKETS}), encoding="utf-8")
    (tmp_path / "docs/data/lessons" / (D + ".json")).write_text(json.dumps({"turns": TURNS}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "data/lesson-work/lesson-types" / (D + ".json")).write_text(json.dumps({"summary": {"rules": [{"title": "taani", "pattern": "x"}]}}), encoding="utf-8")
    (tmp_path / "docs/data/grammar-proposals.json").write_text(json.dumps({"proposals": proposals or []}, ensure_ascii=False), encoding="utf-8")
    shutil.copy(os.path.join(REPO, "scripts", "tutor_grammar_heard_prompt.md"), tmp_path / "scripts" / "tutor_grammar_heard_prompt.md")
    return str(tmp_path)


def quiet(*a):
    pass


def test_am_32_a_rule_she_taught_becomes_a_card_marked_heard_with_her_quote_the_line_and_the_next_free_id(tmp_path):
    R, spent, calls = repo(tmp_path), [], []
    res = T.hear_and_save(D, R, runner=runner_for([FIND], calls), log=quiet, spend=lambda *a: spent.append(a))
    assert len(calls) == 1 and "[10:04] Amal:" in calls[0] and "C12 a doing verb" in calls[0]     # the transcript + the rules
    assert [s[0] for s in spent] == ["anthropic"]                                                    # cost -> data/budget.json
    sid = res["kept"][0]
    assert sid == "heard-20261009-1004"
    store = json.load(open(os.path.join(R, T.STORE_REL), encoding="utf-8"))
    h = store["heard"][sid]
    assert h["t"] == "10:04" and h["quote"] == FIND["quote"] and h["line"] == TURNS[3]["text"] and h["before"] == TURNS[2]["text"]
    p = store["subs"][sid][0]
    assert p["id"] == "B1" and "B1" in store["ids_given"] and p["v"] == 1 and p["overlaps"]["id"] == "C12"
    assert p["examples"][0]["hers"] is True                # a sentence she said in the lesson
    assert p["examples"][1]["hers"] is False               # anything else: spelling unverified (S1)
    page = json.load(open(os.path.join(R, T.PAGE_REL), encoding="utf-8"))
    it = page["items"][0]
    assert it["state"] == "proposed" and it["heard"]["date"] == D and it["heard"]["t"] == "10:04" and page["waiting_for_tutor"] == 1


def test_am_32_a_quote_not_on_her_own_line_at_that_time_is_dropped():
    store = {}
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        R = repo(pathlib.Path(td))
        bad = [dict(FIND, quote="أنا بدي روح"),                    # the student's words, not hers
               dict(FIND, t="30:00", name="far away"),               # her words, but not at that time
               dict(FIND, quote="she never said this", name="made up")]
        res = T.hear(D, store, R, runner=runner_for(bad), log=quiet, spend=quiet)
    assert res["kept"] == [] and all(d["why"] == "her quote is not on her line at that time" for d in res["dropped"])


def test_am_32_gr_18_is_reused_not_duplicated_and_a_known_name_is_not_new(tmp_path):
    prop = {"id": "P-C13", "name": "comparative + pronoun", "moments": [{"date": D, "t": "11:40", "t_amal": "11:43"}]}
    R = repo(tmp_path, [prop])
    comp = dict(FIND, t="11:43", quote="أطول مني", name="mini after comparatives")
    same = dict(FIND, name="nafs + el-")
    res = T.hear(D, {}, R, runner=runner_for([comp, same]), log=quiet, spend=quiet)
    whys = sorted(d["why"] for d in res["dropped"])
    assert res["kept"] == [] and whys == ["a GR-18 proposal already has this moment", "a rule or proposal with this name exists"]


def test_am_32_one_read_per_lesson_a_failed_read_is_retried_and_lessons_before_tutor_from_are_not_read(tmp_path):
    R = repo(tmp_path)
    store = {}
    bad = lambda p: "not json"  # noqa: E731
    assert T.hear(D, store, R, runner=bad, log=quiet, spend=quiet)["kept"] == []
    assert T.pending_lessons(R, store) == [D]                                     # retried by the hourly pull
    T.hear(D, store, R, runner=runner_for([FIND]), log=quiet, spend=quiet)
    assert T.pending_lessons(R, store) == []
    no = lambda p: (_ for _ in ()).throw(AssertionError("no second read"))  # noqa: E731
    assert T.hear(D, store, R, runner=no, log=quiet, spend=quiet) is None       # read once
    assert T.hear("2026-09-30", store, R, runner=no, log=quiet, spend=quiet) is None   # AM-28: before TUTOR_FROM
    store2 = {"heard_runs": {D: {"tries": T.HEAR_TRIES}}}
    assert T.pending_lessons(R, store2) == []                                     # a cap on paid retries


def test_am_32_pull_reads_one_reviewed_lesson_it_has_not_read(tmp_path):
    R, calls = repo(tmp_path), []
    out = T.pull(R, fetch=lambda: [], runner=runner_for([FIND], calls), log=quiet, spend=quiet)
    assert len(calls) == 1 and out["heard"][0]["kept"] == ["heard-20261009-1004"] and out["waiting_for_tutor"] == 1
    T.pull(R, fetch=lambda: [], runner=lambda p: (_ for _ in ()).throw(AssertionError("no second read")), log=quiet, spend=quiet)


def ans(sid, kind, v, t, i, what=""):
    return {"id": i, "created_at": t, "source": "tutor_grammar", "kind": kind, "word_key": "tgram:%s:answer" % sid, "payload": {"v": v, "what": what}}


def test_am_32_the_same_answers_work_change_rewrites_with_the_moment_yes_adds_it_no_keeps_the_id_taken(tmp_path):
    R = repo(tmp_path)
    T.pull(R, fetch=lambda: [], runner=runner_for([FIND]), log=quiet, spend=quiet)
    sid = "heard-20261009-1004"
    rows = [ans(sid, T.CHANGE, 1, "2026-10-12T10:00:00Z", 1, "call it biddi + verb")]
    seen = []
    ai2 = {k: v for k, v in FIND.items() if k not in ("t", "quote")}
    ai2["name"] = "biddi + verb"
    T.pull(R, fetch=lambda: rows, runner=lambda p: (seen.append(p), json.dumps({"result": json.dumps(dict(ai2, grammar=True)), "total_cost_usd": 0.004}))[1],
           log=quiet, spend=quiet)
    assert "heard the tutor teach this in the 2026-10-09 lesson at 10:04" in seen[0] and "call it biddi + verb" in seen[0]
    store = json.load(open(os.path.join(R, T.STORE_REL), encoding="utf-8"))
    assert [v["v"] for v in store["subs"][sid]] == [1, 2] and store["subs"][sid][1]["id"] == "B1"     # same id, new version
    rows.append(ans(sid, T.YES, 2, "2026-10-12T10:30:00Z", 2))
    T.pull(R, fetch=lambda: rows, runner=runner_for([]), log=quiet, spend=quiet)
    b = T.approved_buckets(R)
    assert [x["id"] for x in b] == ["B1"] and b[0]["detector"] is None and b[0]["added_by"] == "tutor"
    assert b[0]["heard_in"] == {"date": D, "t": "10:04"} and any("Claude heard the tutor teach it" in m for m in b[0]["more"])
    rows.append(ans(sid, T.NO, 2, "2026-10-12T11:00:00Z", 3))
    T.pull(R, fetch=lambda: rows, runner=runner_for([]), log=quiet, spend=quiet)
    assert T.approved_buckets(R) == [] and T.next_id("B", T.taken_ids(R, json.load(open(os.path.join(R, T.STORE_REL), encoding="utf-8")))) == "B2"


def test_am_32_review_lesson_runs_the_read_once_per_lesson_and_dry_run_spends_nothing(tmp_path):
    import review_lesson as RL
    R, calls = repo(tmp_path), []
    assert RL.heard_grammar_step(D, True, R, runner=runner_for([FIND], calls), spend=quiet) is None and calls == []
    RL.heard_grammar_step(D, False, R, runner=runner_for([FIND], calls), spend=quiet)
    RL.heard_grammar_step(D, False, R, runner=runner_for([FIND], calls), spend=quiet)
    assert len(calls) == 1
    src = open(os.path.join(REPO, "scripts", "review_lesson.py"), encoding="utf-8").read()
    assert "heard_grammar_step(d, a.dry_run)" in src and '"data/lesson-work/tutor-grammar"' in src


def test_am_32_the_read_is_one_lean_call():
    cmd = T.lean_cmd("x")
    assert cmd[cmd.index("--model") + 1] == T.MODEL and "--tools" in cmd and "--strict-mcp-config" in cmd


def test_am_32_a_transcript_long_prompt_goes_on_stdin_not_the_command_line():
    long = "x" * (T.ARG_MAX + 1)
    assert long not in T.lean_cmd(long) and "x" in T.lean_cmd("x")      # Windows caps a command line at 32,767 chars


def test_am_32_only_the_lesson_is_read_from_her_first_word_to_her_last_without_off_lesson_stretches(tmp_path):
    R, calls = repo(tmp_path), []
    lt = os.path.join(R, "data/lesson-work/lesson-types", D + ".json")
    json.dump({"off_lesson": [{"from": "11:30", "to": "11:50"}]}, open(lt, "w", encoding="utf-8"))
    T.hear(D, {}, R, runner=runner_for([], calls), log=quiet, spend=quiet)
    assert "remind me to call" not in calls[0] and "أطول من أنا" not in calls[0] and "[09:50] Amal:" in calls[0]
    assert T.lean_cmd("x", T.HEAR_MODEL)[T.lean_cmd("x", T.HEAR_MODEL).index("--model") + 1] == T.HEAR_MODEL
