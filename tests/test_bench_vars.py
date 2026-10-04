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
    for e in ("gemini-flash-v1-t1", "gemini-flash-v4h-t1", "gemini-flash-v10-t1", "gemini-flash-v13-t1", "gemini-flash-best-t1"):
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


# ---- v13, the edge re-cut (review experiment 3): the clips are chosen by audio alone

def _track():
    """8 s at 16 kHz: digital silence with three stretches of 'speech' (a loud tone): 1.0-2.0, 3.0-4.5 and 6.0-6.3 s."""
    import numpy as np
    sr = 16000
    x = np.zeros(8 * sr, dtype="<i2")
    t = np.arange(8 * sr) / sr
    tone = (6000 * np.sin(2 * np.pi * 220 * t)).astype("<i2")
    for a, b in ((1.0, 2.0), (3.0, 4.5), (6.0, 6.3)):
        x[int(a * sr):int(b * sr)] = tone[int(a * sr):int(b * sr)]
    return x, sr


def test_v13_selector_takes_audio_only():
    import inspect
    for f in (BV.edge_lines, BV.edge_speech, BV.extend_to_silence, BV.speech_level):
        names = set(inspect.signature(f).parameters)
        assert not names & {"truth", "moments", "slips", "lines", "date", "text", "prompts"}, f.__name__
        src = inspect.getsource(f)
        for w in ("truth", "moment", "slip", "engine", "want", "BC.J", "open("):
            assert w not in src.replace("no answer key, no moment", ""), "%s mentions %s" % (f.__name__, w)
    assert list(inspect.signature(BV.edge_lines).parameters) == ["windows", "clips", "track", "sr", "rule"]
    # the caller hands it times and clip names only: no moment, slip or text is read on the way
    src = inspect.getsource(BV.v13_rows)
    for w in ('"moments"', '"slips"', '"truth"]', '"engine"', '"fixes"', '"should_stay"', '"corrected"', '"has_arabic"'):
        assert w not in src, w


def test_v13_edges_and_the_cut_to_the_nearest_silence():
    x, sr = _track()
    cut = lambda a, b: x[int(a * sr):int(b * sr)]  # noqa: E731
    windows = {1: (0.4, 2.6),     # clean: silence at both ends
               2: (3.2, 5.1),     # starts inside the speech that began at 3.0
               3: (2.4, 4.0),     # ends inside the speech that runs to 4.5
               4: (3.5, 4.2),     # both ends inside speech
               5: (5.0, 5.9)}     # silent clip
    sel, level = BV.edge_lines(windows, {i: cut(a, b) for i, (a, b) in windows.items()}, x, sr)
    assert sorted(sel) == [2, 3, 4]
    assert (sel[2]["edge"], sel[3]["edge"], sel[4]["edge"]) == ("start", "end", "both")
    assert sel[2]["new_window"] == [2.8, 5.1] and sel[2]["extended_s"] == [0.4, 0.0]      # back over the speech + 0.2 s of silence; the end untouched
    assert sel[3]["new_window"] == [2.4, 4.7] and sel[3]["extended_s"] == [0.0, 0.7]
    assert sel[4]["new_window"] == [2.8, 4.7]
    assert not any(sel[i]["capped"][0] or sel[i]["capped"][1] for i in sel)
    # a quiet edge (40 dB under his speech level) is not speech
    quiet = (cut(3.2, 5.1) // 100)
    assert BV.edge_speech(quiet, sr, level)[0] == ""


def test_v13_extension_is_capped():
    import numpy as np
    sr = 16000
    t = np.arange(10 * sr) / sr
    x = (6000 * np.sin(2 * np.pi * 220 * t)).astype("<i2")
    x[: sr // 2] = 0                                       # he talks without a break from 0.5 s on
    level = BV.speech_level(x, sr)
    assert BV.extend_to_silence(x, sr, 6.0, -1, level) == (2.0, True)      # no silence within 2.0 s: the cap is the cut
    assert BV.extend_to_silence(x, sr, 1.0, -1, level) == (0.7, False)     # 0.5 s of speech back + 0.2 s of silence
    assert BV.extend_to_silence(x, sr, 9.9, +1, level) == (0.3, False)     # the end of the recording counts as silence
    sel, _ = BV.edge_lines({1: (5.0, 7.0)}, {1: x[5 * sr:7 * sr]}, x, sr)
    assert sel[1]["new_window"] == [3.0, 9.0] and sel[1]["capped"] == [True, True]


def test_v13_is_a_subset_variable_with_the_unchanged_prompt():
    v = BV.variables("2026-10-02")["v13"]
    assert v["kind"] == "subset" and not any(k in v for k in ("insert", "pre_answer", "answer", "replace", "cfg"))
    assert BV.V13["max_extend_s"] == 2.0 and BV.V13["edge_ms"] == 150
