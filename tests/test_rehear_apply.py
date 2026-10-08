# -*- coding: utf-8 -*-
"""Whole-line overlay rows of the Gemini re-hear (TR-22; scripts/rehear_apply.py, scripts/transcript_fixes.py).
Every case here is a counterexample from the Codex audits of 2026-10-04: a row must change its own line and nothing else."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import rehear_apply as A  # noqa: E402
import transcript_fixes as TF  # noqa: E402

D = "2026-01-01"


def row(t, line, heard, who="Medi"):
    new, sp = A.spans(line, heard)
    return {"date": D, "t": t, "who": who, "line": line, "heard_line": new, "spans": sp, "engine_wrote": line, "heard": new, "by": A.BY, "rule": A.RULE}


def test_spans_build_the_line_at_exact_places():
    assert A.spans("I want to go this suck today", "I want to go لسه today") == ("I want to go لسه today", [{"engine_wrote": "this suck", "heard": "لسه"}])
    assert A.spans("red red", "red blue")[0] == "red blue"                       # the SECOND red, not the first
    assert A.spans("the the cat", "the cat")[0] == "the cat"
    assert A.spans("red cat", "cat")[0] == "cat"                                 # no stray space
    assert A.spans("Yeah, I like it.", "yeah أنا بحب I like it")[0] == "Yeah, أنا بحب I like it."      # the engine's punctuation stays
    assert A.spans("a b", "x a y b z")[0] == "x a y b z"
    assert A.spans("Hello, cat!", "hello cat") == (None, [])                     # no word differs: no row


def test_a_row_changes_only_its_own_line():
    turns = [{"t": 10.0, "who": "Medi", "text": "blue cat"}, {"t": 10.5, "who": "Medi", "text": "blue"}, {"t": 10.2, "who": "Amal", "text": "blue cat"},
             {"t": 10.1, "who": "Medi", "text": "blue cat", "chat": True}]
    out = TF.apply(D, turns, rows=[row(10.0, "blue cat", "green cat")], sort=False)
    assert [u["text"] for u in out] == ["green cat", "blue", "blue cat", "blue cat"]
    assert out[0]["engine"] == "blue cat" and out[0]["heard"][0]["engine_wrote"] == "blue"


def test_two_identical_lines_at_one_moment_get_nothing_and_near_ones_the_nearest():
    turns = [{"t": 10.0, "who": "Medi", "text": "blue"}, {"t": 10.005, "who": "Medi", "text": "blue"}]
    assert [u["text"] for u in TF.apply(D, turns, rows=[row(10.0, "blue", "green")], sort=False)] == ["blue", "blue"]
    turns = [{"t": 10.0, "who": "Medi", "text": "blue"}, {"t": 10.5, "who": "Medi", "text": "blue"}]
    assert [u["text"] for u in TF.apply(D, turns, rows=[row(10.0, "blue", "green")], sort=False)] == ["green", "blue"]


def test_his_correction_wins_also_one_made_later():
    turns = [{"t": 10.0, "who": "Medi", "text": "blue cat"}]
    his = {"date": D, "t": 10.0, "who": "Medi", "engine_wrote": "blue", "heard": "red", "by": "medi", "rule": "TR-18"}
    for rows in ([his, row(10.0, "blue cat", "green cat")], [row(10.0, "blue cat", "green cat"), his]):
        out = TF.apply(D, turns, rows=rows, sort=False)
        assert out[0]["text"] == "red cat" and len(out[0]["heard"]) == 1


def test_unmatched_reports_a_row_whose_line_is_gone():
    r = row(10.0, "blue cat", "green cat")
    assert TF.unmatched(D, TF.apply(D, [{"t": 10.0, "who": "Medi", "text": "blue cat"}], rows=[r]), rows=[r]) == []
    assert TF.unmatched(D, TF.apply(D, [{"t": 10.0, "who": "Medi", "text": "blue dog"}], rows=[r]), rows=[r]) == [r]


def test_track_turns_one_owner_whole_words_only():
    r = row(10.75, "cat", "dog")
    T = [{"speaker": "Medi", "start": 0.0, "end": 10.0, "text": "blue scatter"}, {"speaker": "Medi", "start": 10.5, "end": 13.0, "text": "my cat sat"}]
    out = TF.apply_tracks(D, T, rows=[r])
    assert [u["text"] for u in out] == ["blue scatter", "my dog sat"]            # never inside another word
    T = [{"speaker": "Medi", "start": 9.0, "end": 10.9, "text": "a cat"}, {"speaker": "Medi", "start": 10.5, "end": 13.0, "text": "my cat sat"}]
    assert [u["text"] for u in TF.apply_tracks(D, T, rows=[r])] == ["a cat", "my cat sat"]      # two possible owners: none
    T = [{"speaker": "Medi", "start": 10.5, "end": 13.0, "text": "cat my cat"}]
    assert TF.apply_tracks(D, T, rows=[r])[0]["text"] == "cat my cat"            # twice in one turn: not applied
    T = [{"speaker": "Medi", "start": 10.5, "end": 13.0, "text": "my cat sat"}]
    assert TF.apply_tracks(D, T, rows=[row(10.0, "cat", "dog")])[0]["text"] == "my cat sat"     # the row's time is outside the turn
    T = [{"speaker": "Medi", "start": 10.0, "end": 13.0, "text": "cat"}]
    assert TF.apply_tracks(D, T, rows=[row(10.0, "cat", "dog"), row(11.0, "dog", "fox")])[0]["text"] == "dog"   # never on words another row wrote
    T = [{"speaker": "Medi", "start": 10.0, "end": 13.0, "text": "intro cat"}]            # a time fix of his on the turn: the turn is his
    moved = {"date": D, "t": 10.0, "who": "Medi", "engine_wrote": "", "heard": "", "set_t": 10.2, "by": "medi"}
    assert TF.apply_tracks(D, T, rows=[moved, row(13.4, "cat", "dog")])[0]["text"] == "intro cat"
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "my cat sat on a mat"}]
    assert TF.apply_tracks(D, T, rows=[row(10.0, "my cat", "my dog"), row(12.0, "on a mat", "on a hat")])[0]["text"] == "my dog sat on a hat"


def test_heard_his_counts_at_the_correction():
    f = {"engine_wrote": "red", "heard": "blue"}
    assert not A.heard_his(f, "blue red", {"text": "blue"})                      # his line has blue twice
    assert A.heard_his(f, "blue red", {"text": "blue blue"})
    assert not A.heard_his(f, "blue red", {"text": "blue blue red"})             # the engine's word must be gone
    assert not A.heard_his({"engine_wrote": "مرحبا", "heard": ""}, "مرحبا يا", {"text": "mar7aba ya"})
    assert A.heard_his({"engine_wrote": "red", "heard": ""}, "red red", {"text": "red"})
    assert not A.heard_his(f, "blue red", {"text": "", "error": "x"})
    assert not A.heard_his({"engine_wrote": "red", "heard": "red blue"}, "red", {"text": "red blue red"})
    assert A.heard_his({"engine_wrote": "red", "heard": "red blue"}, "red", {"text": "red blue"})
    assert not A.heard_his({"engine_wrote": "mar7aba", "heard": ""}, "mar7aba ya", {"text": "مرحبا يا"})


def test_ledger_override_sees_spans_not_the_whole_line():
    out = TF.apply(D, [{"t": 10.0, "who": "Medi", "text": "ana biddi this suck"}], rows=[row(10.0, "ana biddi this suck", "ana biddi لسه")], sort=False)
    assert [h["engine_wrote"] for h in out[0]["heard"]] == ["this suck"]         # biddi's stored score is not named, so it stays


def _stamps(*turns):
    return [{"speaker": w, "start": float(t), "end": float(t), "text": x} for t, w, x in turns]


def test_track_turns_from_stamps_run_to_the_speakers_next_stamp():
    # transcript.txt lessons: [mm:ss] only - whole seconds, end == start on every turn
    T = _stamps((60, "Medi", "hello there my cat sat"), (65, "Amal", "a cat"), (80, "Medi", "next thing"))
    out = TF.apply_tracks(D, T, rows=[row(72.4, "my cat", "my dog")])
    assert [u["text"] for u in out] == ["hello there my dog sat", "a cat", "next thing"]      # 12 s in, her stamp between: still his turn
    assert out[0]["engine"] == "hello there my cat sat" and out[0]["heard"][0]["by"] == A.BY
    assert TF.apply_tracks(D, T, rows=[row(80.9, "my cat", "my dog")])[0]["text"] == "hello there my dog sat"   # the second the next stamp cut off
    assert TF.apply_tracks(D, T, rows=[row(81.5, "my cat", "my dog")])[0]["text"] == "hello there my cat sat"   # past his next stamp
    assert TF.apply_tracks(D, T, rows=[row(59.0, "my cat", "my dog")])[0]["text"] == "hello there my cat sat"   # before the turn
    T = _stamps((60, "Medi", "my cat"), (60, "Medi", "and my cat"), (80, "Medi", "next"))
    assert [u["text"] for u in TF.apply_tracks(D, T, rows=[row(60.5, "my cat", "my dog")])] == ["my cat", "and my cat", "next"]   # two turns hold it: none
    T = _stamps((60, "Medi", "white white grey white"), (80, "Medi", "next"))            # two rows want overlapping words: none
    assert TF.apply_tracks(D, T, rows=[row(61.0, "white grey", "white gray"), row(63.0, "grey white", "gray white")])[0]["text"] == "white white grey white"
    # one turn with a real end: the lesson is not read from stamps, an end == start turn stays one moment
    T = [{"speaker": "Medi", "start": 60.0, "end": 60.0, "text": "my cat sat"}, {"speaker": "Medi", "start": 80.0, "end": 82.0, "text": "next thing"}]
    assert TF.apply_tracks(D, T, rows=[row(72.4, "my cat", "my dog")])[0]["text"] == "my cat sat"
    assert TF.apply_tracks(D, T, rows=[row(60.2, "my cat", "my dog")])[0]["text"] == "my dog sat"


def test_track_turns_same_words_punctuation_and_sound_tags_aside():
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "well my cat  sat، now"}]
    out = TF.apply_tracks(D, T, rows=[row(10.5, "my cat, sat.", "my dog, sat.")])
    assert out[0]["text"] == "well my dog, sat. now" and out[0]["engine"] == "well my cat  sat، now"      # replaced at the true places
    assert [(h["engine_wrote"], h["heard"]) for h in out[0]["heard"]] == [("cat,", "dog,")]
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "so my cat sat"}]                       # track turns carry no sound tags
    out = TF.apply_tracks(D, T, rows=[row(10.5, "my [laughs] cat sat", "my [laughs] dog sat")])
    assert out[0]["text"] == "so my dog sat" and len(out[0]["heard"]) == 1
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "my cats sat"}]
    assert TF.apply_tracks(D, T, rows=[row(10.5, "my cat, sat", "my dog, sat")])[0]["text"] == "my cats sat"    # whole words only
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "my cat my cat"}]
    assert TF.apply_tracks(D, T, rows=[row(10.5, "my cat.", "my dog.")])[0]["text"] == "my cat my cat"         # the words stand twice: none
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "cat, cat."}]
    assert TF.apply_tracks(D, T, rows=[row(10.5, "cat.", "dog.")])[0]["text"] == "cat, dog."                   # letter for letter goes first
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "my Cat sat"}]
    assert TF.apply_tracks(D, T, rows=[row(10.5, "my cat, sat", "my dog, sat")])[0]["text"] == "my Cat sat"     # another letter is another word
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "so okay"}]                                  # a line that is only a sound tag has no words
    r = {"date": D, "t": 10.5, "who": "Medi", "line": "[laughs]", "heard_line": "okay", "spans": [{"engine_wrote": "[laughs]", "heard": "okay"}], "by": A.BY}
    assert TF.apply_tracks(D, T, rows=[r])[0]["text"] == "so okay"
    r = {"date": D, "t": 10.5, "who": "Medi", "line": "so [laughs] okay", "heard_line": "so okay", "spans": [{"engine_wrote": "[laughs]", "heard": ""}], "by": A.BY}
    out = TF.apply_tracks(D, T, rows=[r])
    assert out[0]["text"] == "so okay" and not out[0].get("heard") and not out[0].get("engine")               # only the tag differed: untouched
    T = [{"speaker": "Medi", "start": 10.0, "end": 14.0, "text": "my cat, sat"}]                             # another correction on the turn: his
    his = {"date": D, "t": 10.0, "who": "Medi", "engine_wrote": "sat", "heard": "sad", "by": "medi"}
    assert TF.apply_tracks(D, T, rows=[his, row(10.5, "my cat sat", "my dog sat")])[0]["text"] == "my cat, sad"


def test_track_turns_a_typed_chat_line_takes_no_row():
    T = [{"speaker": "Medi", "start": 10.0, "end": 10.0, "text": "my cat sat", "chat": True}, {"speaker": "Medi", "start": 30.0, "end": 33.0, "text": "later"}]
    assert TF.apply_tracks(D, T, rows=[row(10.0, "my cat sat", "my dog sat")])[0]["text"] == "my cat sat"
    T = _stamps((60, "Medi", "my cat sat"), (80, "Medi", "next")) + [{"speaker": "Medi", "start": 61.4, "end": 61.4, "text": "my cat sat", "chat": True}]
    out = TF.apply_tracks(D, T, rows=[row(61.0, "my cat sat", "my dog sat")])            # chat lines do not hide that the lesson is stamps
    assert [u["text"] for u in out] == ["my dog sat", "next", "my cat sat"]
