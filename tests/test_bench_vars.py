# -*- coding: utf-8 -*-
"""The pure pieces of the Gemini variables test (scripts/bench_vars.py, PR-18): no network, no files."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402

BASE = "intro\n\n" + BV.WRITE_MARK + "\n- keep his mistakes\n" + 'Answer JSON only: {"arabic": "x", "arabizi": "y"}'


def test_build_puts_each_piece_in_its_place():
    p = BV.build(BASE, {"insert": "NOTE", "pre_answer": "PRE", "answer": 'Answer JSON only: {"said": "s"}'})
    assert p.index("NOTE") < p.index(BV.WRITE_MARK) < p.index("PRE") < p.index('{"said"')
    assert '"arabic": "x"' not in p
    assert BV.build(BASE, {}) == BASE


def test_build_refuses_a_changed_base():
    try:
        BV.build("no marks here", {"insert": "x"})
    except ValueError:
        return
    raise AssertionError("a base prompt without the marks must be refused")


def test_drop_changes():
    heard = lambda c: c.get("evidence") == "heard"  # noqa: E731
    # every change inferred -> the engine's line
    assert BV.drop_changes("انا متشجع", "انا شجاع", [{"engine": "شجاع", "said": "متشجع", "evidence": "inferred"}], heard) == ("انا شجاع", 1, 0)
    # one of two dropped -> only that word goes back
    t, n, miss = BV.drop_changes("لسه مش متشجع", "This مش شجاع", [{"engine": "This", "said": "لسه", "evidence": "heard"}, {"engine": "شجاع", "said": "متشجع", "evidence": "inferred"}], heard)
    assert (t, n, miss) == ("لسه مش شجاع", 1, 0)
    # nothing to drop -> untouched
    assert BV.drop_changes("a b", "a c", [{"engine": "c", "said": "b", "evidence": "heard"}], heard) == ("a b", 0, 0)
    # a changed line with no itemised change, or a dropped change that cannot be found, goes back to the engine's line
    assert BV.drop_changes("انا رحت", "انا صرت", None, heard) == ("انا صرت", 0, 1)
    # ... but a change of alphabet only (his Arabic was in English letters) is not a word change and stays
    assert BV.drop_changes("ghayr", "ghayr.", None, heard)[1:] == (0, 0)
    assert BV.drop_changes("a c", "a c", None, heard) == ("a c", 0, 0)
    assert BV.drop_changes("x y", "a c", [{"engine": "a", "said": "x", "evidence": "heard"}, {"engine": "c", "said": "zzz", "evidence": "inferred"}], heard) == ("a c", 1, 1)


def test_limit_answers_are_never_the_engines_miss():
    assert BV.unreached("429 You exceeded your current quota ... generate_requests_per_model_per_day")
    assert BV.unreached("429 rate limit") and BV.unreached("ConnectionError: reset")
    assert not BV.unreached("bad json") and not BV.unreached(None)


def test_second_text_and_merge_span_and_take():
    assert BV.second_text("على عشا", [{"said": "عشا", "second": "عشرة"}]) == "على عشرة"
    assert BV.second_text("على عشا", []) == "على عشا"
    assert BV.merge_span("I said this suck today", "this suck", "لسه") == "I said لسه today"
    assert BV.merge_span("I said hello", "not there", "لسه") is None
    # the padded clip repeats the words around the stretch: they are not written twice
    import bench_common as BC
    tk = lambda x: BC.tokens(x)  # noqa: E731
    assert tk(BV.merge_span("only the I form for أنا برسم. Claude guesses", "أنا برسم", "form for أنا برسم")) == tk("only the I form for أنا برسم. Claude guesses")
    assert tk(BV.merge_span("So like أنا برسم لها...", "أنا برسم لها", "So like أنا برسم إلها")) == tk("So like أنا برسم إلها")
    assert tk(BV.v6_text("you get أنا برسم لها, I drive", [{"piece": "أنا برسم لها", "said": "get أنا برسم إلها, I dr-"}])) == tk("you get أنا برسم إلها, I dr- I drive")
    assert BV.v3_take({"words": [{"word": "x", "same": True}]}) is True
    assert BV.v3_take({"words": [{"word": "x", "same": True}, {"word": "y", "same": False}]}) is False
    assert BV.v3_take({"words": []}) is False and BV.v3_take(None) is False


def test_variable_engines_are_billed_to_gemini():
    for e in ("gemini-flash-v1-t1", "gemini-flash-v4h-t1", "gemini-flash-v10-t1", "gemini-flash-best-t1"):
        assert BR.SERVICE.get(BR.root(e)) == "gemini", e
    assert BR.root("openai-audio-best") == "openai-audio"
    assert BR.root("gemini-flash-before-t1") == "gemini-flash"


def test_build_replace_rewords_or_removes_one_sentence():
    base = "a\n- one line.\n- two line.\n" + BASE
    assert BV.build(base, {"replace": [["- one line.\n", ""], ["- two line.", "- 2."]]}) == "a\n- 2.\n" + BASE
    try:
        BV.build(base, {"replace": [["- not there", ""]]})
    except ValueError:
        return
    raise AssertionError("a sentence that is not in the base prompt must be refused")
