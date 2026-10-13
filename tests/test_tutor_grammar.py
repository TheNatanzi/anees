# -*- coding: utf-8 -*-
"""AM-31 'Add grammar' on the Tutor page: rule ids, the proposal shape, approve / change / undo, the no-detector path."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import tutor_grammar as T  # noqa: E402

BUCKETS = [{"id": "A1", "family": "A", "name": "el- (the)", "one_line": "el- marks"}, {"id": "A10b", "family": "A", "name": "x", "one_line": "y"},
           {"id": "A17", "family": "A", "name": "nafs + el-", "one_line": "z"}, {"id": "B18", "family": "B", "name": "v", "one_line": "w"},
           {"id": "D6", "family": "D", "name": "iyyaa", "one_line": "q"}]
AI = {"grammar": True, "family": "B", "name": "laazem + bare verb", "one_line": "After laazem the verb has no b-.",
      "formula": "laazem + verb without b-", "why": "English says must + verb.",
      "examples": [{"arabizi": "laazem aroo7", "arabic": "لازم اروح", "english": "I must go"},
                   {"arabizi": "laazem nakul", "arabic": "", "english": "we must eat"}],
      "overlaps": {"id": "B18", "why": "both about the verb"}}


def sub_row(sid, text="after laazem no b-: laazem aroo7", example="", t="2026-10-12T10:00:00Z", i=1):
    return {"id": i, "created_at": t, "source": "tutor_grammar", "kind": T.SUBMIT, "word_key": "tgram:" + sid, "payload": {"text": text, "example": example}}


def ans_row(sid, kind, v, t, i, what=""):
    return {"id": i, "created_at": t, "source": "tutor_grammar", "kind": kind, "word_key": "tgram:%s:answer" % sid, "payload": {"v": v, "what": what}}


def fake_runner(ai):
    return lambda prompt: json.dumps({"result": json.dumps(ai), "total_cost_usd": 0.004, "is_error": False})


def test_am_31_next_id_is_one_more_than_the_highest_in_the_letter_group_and_never_fills_a_gap():
    taken = {"A1", "A10b", "A17", "B18", "D6", "P-C12"}
    assert T.next_id("A", taken) == "A18"
    assert T.next_id("b", taken) == "B19"
    assert T.next_id("C", taken) == "C13"
    assert T.next_id("E", taken) == "E1"
    assert T.next_id("A", {"A1", "A5"}) == "A6"          # A2-A4 may be retired: never reused


def test_am_31_a_retired_id_stays_taken_through_ids_given(tmp_path):
    os.makedirs(tmp_path / "docs" / "data")
    (tmp_path / "docs" / "data" / "grammar-buckets.json").write_text(json.dumps({"buckets": BUCKETS}), encoding="utf-8")
    taken = T.taken_ids(str(tmp_path), {"ids_given": ["A18"]})     # A18 was handed out, then she said no: still taken
    assert T.next_id("A", taken) == "A19"


def test_am_31_the_real_files_give_the_next_free_ids():
    taken = T.taken_ids(REPO)
    for fam in T.FAMILIES:
        rid = T.next_id(fam, taken)
        assert rid not in taken and rid.startswith(fam)


def test_am_31_proposal_shape_her_examples_are_hers_and_anything_else_is_unverified():
    sub = {"sid": "sub1", "text": "after laazem the verb has no b-", "example": "laazem aroo7"}
    p = T.clean(AI, sub, BUCKETS, {"A1", "B18"})
    assert p["id"] == "B19" and p["family"] == "B" and p["name"] and p["one_line"] and p["formula"]
    assert [e["hers"] for e in p["examples"]] == [True, False]       # 'nakul' is not in her words (S1)
    assert p["overlaps"] == {"id": "B18", "name": "v", "why": "both about the verb"}
    assert T.clean(dict(AI, overlaps={"id": "Z9", "why": "x"}), sub, BUCKETS, set())["overlaps"] is None   # only a real rule
    assert T.clean(dict(AI, family="F"), sub, BUCKETS, set()) is None                                       # A-E only
    assert T.clean({"grammar": False, "why": "a single word"}, sub, BUCKETS, set()) == {"grammar": False, "why": "a single word"}


def test_am_31_pull_proposes_once_logs_the_cost_and_the_card_waits_for_her(tmp_path):
    os.makedirs(tmp_path / "docs" / "data")
    (tmp_path / "docs" / "data" / "grammar-buckets.json").write_text(json.dumps({"buckets": BUCKETS}), encoding="utf-8")
    spent = []
    rows = [sub_row("sub1")]
    out = T.pull(str(tmp_path), fetch=lambda: rows, runner=fake_runner(AI), log=lambda *a: None, spend=lambda *a: spent.append(a))
    assert out["proposed"] == ["sub1"] and out["waiting_for_tutor"] == 1 and out["approved"] == []
    assert spent and spent[0][0] == "anthropic"                       # PR-10: every paid call reaches the budget
    page = json.loads((tmp_path / "docs" / "data" / "tutor-grammar.json").read_text(encoding="utf-8"))
    assert page["items"][0]["state"] == "proposed" and page["items"][0]["versions"][0]["id"] == "B19"
    again = T.pull(str(tmp_path), fetch=lambda: rows, runner=lambda p: (_ for _ in ()).throw(AssertionError("no second read")), log=lambda *a: None)
    assert again["proposed"] == []                                    # never re-read


def test_am_31_change_makes_a_new_version_yes_adds_it_undo_takes_it_back(tmp_path):
    os.makedirs(tmp_path / "docs" / "data")
    (tmp_path / "docs" / "data" / "grammar-buckets.json").write_text(json.dumps({"buckets": BUCKETS}), encoding="utf-8")
    rows = [sub_row("sub1")]
    q = lambda: rows  # noqa: E731
    T.pull(str(tmp_path), fetch=q, runner=fake_runner(AI), log=lambda *a: None, spend=lambda *a: None)
    rows.append(ans_row("sub1", T.CHANGE, 1, "2026-10-12T11:00:00Z", 2, what="call it laazem + verb"))
    seen = []
    T.pull(str(tmp_path), fetch=q, runner=lambda p: (seen.append(p), fake_runner(dict(AI, name="laazem + verb"))(p))[1], log=lambda *a: None, spend=lambda *a: None)
    assert "call it laazem + verb" in seen[0]                          # her change goes to Claude with the card she saw
    store = json.loads((tmp_path / T.STORE_REL).read_text(encoding="utf-8"))
    vs = store["subs"]["sub1"]
    assert [v["v"] for v in vs] == [1, 2] and vs[1]["id"] == vs[0]["id"] == "B19" and vs[1]["name"] == "laazem + verb"
    # a yes on the OLD version does not add it; a yes on the current one does
    rows.append(ans_row("sub1", T.YES, 1, "2026-10-12T12:00:00Z", 3))
    T.pull(str(tmp_path), fetch=q, runner=fake_runner(AI), log=lambda *a: None, spend=lambda *a: None)
    assert T.approved_buckets(str(tmp_path)) == []
    rows.append(ans_row("sub1", T.YES, 2, "2026-10-12T12:05:00Z", 4))
    T.pull(str(tmp_path), fetch=q, runner=fake_runner(AI), log=lambda *a: None, spend=lambda *a: None)
    b = T.approved_buckets(str(tmp_path))
    assert [x["id"] for x in b] == ["B19"] and b[0]["added_by"] == "tutor" and b[0]["detector"] is None
    assert b[0]["examples"][1][1].endswith("spelling unverified)")    # S1
    rows.append({"id": 5, "created_at": "2026-10-12T12:06:00Z", "source": "tutor_grammar", "kind": "undo", "word_key": "tgram:sub1:answer", "payload": {"undoes": T.YES}})
    T.pull(str(tmp_path), fetch=q, runner=fake_runner(AI), log=lambda *a: None, spend=lambda *a: None)
    assert T.approved_buckets(str(tmp_path)) == []                     # AM-17: the latest action wins
    assert "B19" in json.loads((tmp_path / T.STORE_REL).read_text(encoding="utf-8"))["ids_given"]   # and B19 is never reused


def test_am_31_not_a_rule_and_withdraw_add_nothing():
    rows = [sub_row("sub1"), ans_row("sub1", T.NO, 1, "2026-10-12T11:00:00Z", 2), sub_row("sub2", i=3, t="2026-10-12T10:01:00Z"),
            {"id": 4, "created_at": "2026-10-12T10:02:00Z", "source": "tutor_grammar", "kind": "undo", "word_key": "tgram:sub2", "payload": {}}]
    store = {"subs": {"sub1": [dict(T.clean(AI, {"text": "x"}, BUCKETS, set()), v=1)]}}
    subs = T.reduce_rows(rows)
    assert T.state(subs["sub1"], store["subs"]["sub1"]) == "not_rule" and T.state(subs["sub2"], []) == "withdrawn"
    assert T.approved(rows, store) == [] and not T.needs_proposal(subs["sub2"], [])


def test_am_31_a_rule_with_no_detector_is_listed_as_no_automatic_detection_yet():
    import importlib
    src = open(os.path.join(REPO, "scripts", "detect_grammar_usage.py"), encoding="utf-8").read()
    assert "def no_detector(bs=None):" in src and '"no_automatic_detection": no_detector(),' in src
    # the function itself, without running the whole counter
    ns = {}
    start = src.index("def no_detector(bs=None):")
    exec(src[start:src.index("\ndef detect(", start)], {"P": {"A13": ["x"]}, "buckets": []}, ns)
    out = ns["no_detector"]([{"id": "B19", "name": "laazem", "added_by": "tutor", "added_on": "2026-10-12"}, {"id": "A13", "added_by": "tutor"}, {"id": "A1"}])
    assert [x["id"] for x in out] == ["B19"] and "no automatic detection yet" in out[0]["why"]
    con = open(os.path.join(REPO, "scripts", "build_grammar_console.py"), encoding="utf-8").read()
    assert '"no_detector": b["id"] in NO_DETECTOR,' in con
    assert "No automatic detection yet" in open(os.path.join(REPO, "docs", "js", "grammar-console.js"), encoding="utf-8").read()
    importlib.invalidate_caches()


def test_am_31_the_tutor_page_has_the_add_grammar_tab_and_the_jobs_run_it():
    html = open(os.path.join(REPO, "docs", "tutor.html"), encoding="utf-8").read()
    assert 'data-tab="add-grammar">Add grammar' in html and "js/hub/grammar-add-task.js" in html
    trig = open(os.path.join(REPO, "scripts", "amal_trigger.py"), encoding="utf-8").read()
    assert '("tutor_grammar_pull", [sys.executable, "scripts/tutor_grammar.py", "pull"]),' in trig and '"tutor_grammar")' in trig
    assert "'tutor_grammar.py pull'" in open(os.path.join(REPO, "scripts", "hourly_lessons.py"), encoding="utf-8").read()
    assert "tutor_grammar\\." in open(os.path.join(REPO, "scripts", "budget_rebuild.py"), encoding="utf-8").read()
    assert T.check(REPO) == []
