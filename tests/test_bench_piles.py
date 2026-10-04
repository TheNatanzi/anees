# -*- coding: utf-8 -*-
"""The pile rules replayed on saved runs (scripts/bench_piles.py, PR-18): planted cases, no network, no files."""
import inspect, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import bench_common as BC  # noqa: E402
import bench_piles as BP  # noqa: E402

DECIDERS = (BP.bare, BP.words, BP._blocks, BP.run_changes, BP.split_on_others, BP.span_vote, BP.amal_words_next, BP.added_words, BP.decide, BP.v3_verdicts)
KEY_WORDS = ("truth", "moments", "slips", "should_stay", "want", "gone", "corrected", "overlay", "fixes", "has_want", "slip_hidden", "content_change", "BS.")


def test_the_answer_key_never_reaches_a_pile_decision():
    for f in DECIDERS:
        assert "truth" not in inspect.signature(f).parameters, f.__name__
        src = inspect.getsource(f)
        for w in KEY_WORDS:
            assert w not in src, "%s mentions %s" % (f.__name__, w)
    assert list(inspect.signature(BP.decide).parameters) == ["lines", "runs", "amal_all", "spans", "v3_took"]
    # only measure() takes the key, and it decides nothing: it returns numbers for rows that are already final
    assert "truth" in inspect.signature(BP.measure).parameters
    full = [{"i": 1, "t": 1.0, "end": 2.0, "engine": "x", "truth": "KEY", "fixes": [1], "should_stay": False, "corrected": True}]
    assert BP.bare(full) == [{"i": 1, "t": 1.0, "end": 2.0, "engine": "x"}]
    try:
        BP.decide(full, [{"1": {"text": "y"}}], [])                # a line that still carries the key is refused
    except AssertionError:
        pass
    else:
        raise AssertionError("decide must refuse a line that carries more than the bare fields")
    # the main program builds every pile before it opens the key
    src = inspect.getsource(BP.main)
    assert src.index("piles = {") < src.index("measure(truth")


def L(i, engine, t=10.0, end=12.0):
    return {"i": i, "t": t, "end": end, "engine": engine}


def runs_of(i, *texts):
    return [{str(i): {"text": t}} for t in texts]


def test_old_rule_needs_the_whole_line_twice():
    rows = BP.decide([L(1, "ana ro7t el beit")], runs_of(1, "أنا رحت البيت", "أنا رحت البيت.", "انا رحت عالبيت"), [])
    assert (rows[0]["status"], rows[0]["heard"], rows[0]["how"]) == ("proposed", "أنا رحت البيت", "whole-line")
    rows = BP.decide([L(1, "ana ro7t el beit today")], runs_of(1, "أنا رحت البيت today", "أنا رحت البيت tonight", "أنا رحت البيت"), [])
    assert (rows[0]["status"], rows[0]["heard"]) == ("no-agreement", None)
    assert BP.decide([L(1, "same words")], runs_of(1, "Same words.", "same words", "other"), []) == []      # the listener agrees with the engine


def test_span_vote_keeps_the_agreed_span_when_the_rest_differs():
    line = L(1, "I said this suck today um maybe")
    runs = runs_of(1, "I said لسه today surely", "I said لسه tonight maybe", "I told لسه today perhaps")
    assert BP.decide([line], runs, [])[0]["status"] == "no-agreement"
    r = BP.decide([line], runs, [], spans=True)[0]
    assert (r["status"], r["how"]) == ("proposed", "spans")
    assert r["heard"] == "I said لسه today um maybe"               # the agreed span in; one-run words out; the engine's filler stays
    assert [(s["engine"], s["said"], s["runs"]) for s in r["spans"]] == [("this suck", "لسه", 3)]
    # when the agreed spans add up to one run's own line, that run's text and Arabizi are the proposal
    runs = [{"1": {"text": "I said لسه today maybe.", "alt": "I said lissa today maybe"}}] + runs_of(1, "I said لسه tonight maybe", "I told لسه today perhaps")
    r = BP.decide([line], runs, [], spans=True)[0]
    assert (r["how"], r["heard"], r["alt"]) == ("spans", "I said لسه today maybe.", "I said lissa today maybe")


def test_span_vote_never_builds_a_span_no_run_wrote():
    text, kept = BP.span_vote("a b c", ["x b c", "a y c", "a b z"])           # three different changes, each written once
    assert text is None and kept == []
    text, kept = BP.span_vote("a b c", ["x b c", "x b z", "a b z"])           # two spans, each written by 2 runs
    assert text == "x b z" and all(s["runs"] == 2 for s in kept)
    for s in kept:                                                            # every kept span is some run's own words
        assert any(s["said"] in t for t in ["x b c", "x b z", "a b z"])
    text, kept = BP.span_vote("a b", ["a b", "a b", "q r"])                   # the engine's line agreed: nothing to build
    assert text is None
    # an uneven replacement is one span: half of it is never taken
    text, kept = BP.span_vote("tinte nu ro", ["تنتين وربع", "تنتين و ربع", "تنتين"])
    assert text is not None and BC.tokens(text) == BC.tokens("تنتين وربع")    # a lone و joins its word, as in the normaliser


def test_hold_rule_and_release_by_the_two_clip_check():
    line = L(7, "ana sme3t", t=100.0, end=101.0)
    amal = [{"t": 103.0, "end": 104.0, "text": "صحيت"}, {"t": 130.0, "end": 131.0, "text": "رحت"}]
    runs = runs_of(7, "أنا صحيت", "أنا صحيت", "أنا صحيت")
    r = BP.decide([line], runs, amal)[0]
    assert (r["status"], r["amal_next"], r["released"]) == ("held", ["صحيت"], False)
    assert BP.decide([line], runs_of(7, "أنا رحت", "أنا رحت", "أنا رحت"), amal)[0]["status"] == "proposed"     # her word 29 s later: not held
    for took, want in (([True, True, False], "proposed"), ([True, False, False], "held"), ([True, True, None], "proposed"),
                       ([False, False, False], "held"), ([None, None, True], "held")):
        r = BP.decide([line], runs, amal, v3_took={"7": took})[0]
        assert (r["status"], r["released"]) == (want, want == "proposed"), took
    assert BP.decide([line], runs, amal, v3_took={"8": [True, True, True]})[0]["status"] == "held"           # no check on this line: stays held
    # a span-vote line was never the subject of a two-clip check: it is not released by one
    runs = runs_of(7, "أنا صحيت", "أنا صحيت امبارح", "هو صحيت بكرا")
    r = BP.decide([line], runs, amal, spans=True, v3_took={"7": [True, True, True]})[0]
    assert (r["how"], r["status"], r["released"]) == ("spans", "held", False)


def test_v3_verdicts_reads_only_the_called_lines():
    v3 = [{"called": ["7"], "lines": {"7": {"took": True}, "9": {"text": "from the baseline"}}},
          {"called": ["7"], "lines": {"7": {"took": False}}}, {"called": ["7"], "lines": {"7": {"error": "x", "took": False}}}]
    assert BP.v3_verdicts(v3) == {"7": [True, False, False]}


def test_measure_scores_the_final_piles_only():
    truth = {"lines": [{"i": 1, "t": 10.0, "end": 12.0, "engine": "but المال okay", "truth": "but المصاري okay", "should_stay": False},
                       {"i": 2, "t": 20.0, "end": 22.0, "engine": "hello there", "truth": "hello there", "should_stay": True},
                       {"i": 3, "t": 30.0, "end": 31.0, "engine": "انا سمعت", "truth": "انا سمعت", "should_stay": False}],
             "moments": [{"id": "M0", "i": 1, "t": 10.0, "want": ["المصاري"], "gone": ["المال"], "class": "wrong-arabic-word"}],
             "slips": [{"i": 3, "t": 30.0, "kind": "vocab", "wrong": "سمعت", "right": "صحيت"}], "amal_all": [{"t": 32.0, "end": 33.0, "text": "صحيت"}]}
    runs = [{"1": {"text": "but المصاري okay"}, "2": {"text": "hello كتاب"}, "3": {"text": "انا صحيت"}}] * 3
    rows = BP.decide(BP.bare(truth["lines"]), runs, truth["amal_all"])
    m = BP.measure(truth, rows)
    assert (m["proposed"], m["held"], m["no_agreement"]) == (2, 1, 0)
    assert (m["moments_fixed_by_proposed"], m["moment_ids_proposed"]) == (1, ["M0"])
    assert (m["slips_hidden_by_proposed"], m["slips_hidden_with_held"]) == (0, 1)        # the hold keeps Amal's word out of his line
    assert (m["untouched_lines_word_changed_proposed"], m["untouched_proposed_i"]) == (1, [2])
    rel = BP.measure(truth, BP.decide(BP.bare(truth["lines"]), runs, truth["amal_all"], v3_took={"3": [True, True, True]}))
    assert (rel["released_by_v3"], rel["held"], rel["slips_hidden_by_proposed"]) == (1, 0, 1)   # a wrong release shows up as a hidden slip
