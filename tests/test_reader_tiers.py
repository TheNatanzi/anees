# -*- coding: utf-8 -*-
"""The slip-reader tier test (scripts/reader_tiers.py): set up only - a paid read refuses without --yes; the score
(precision / recall / F0.5, one-to-one nearest match by family within 15 s) and the Haiku x3 vote."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import reader_tiers as RT  # noqa: E402


def test_paid_read_needs_yes():
    try:
        RT.run("haiku", 1, lesson="2026-10-10")
        raise AssertionError("ran")
    except SystemExit as e:
        assert "Medi's yes" in str(e)


def test_four_tiers_same_effort():
    assert RT.MODELS == {"fable": "claude-fable-5-1", "opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
    assert RT.EFFORT == "high" and RT.RUNS == 3 and RT.LESSONS == ("2026-10-08", "2026-10-09", "2026-10-10")


def test_family_and_predicted():
    assert RT.family("vocab-A") == RT.family("vocab-B", 1) == "vocab"
    assert RT.family("vocab-B", 3) is None                                   # switching to English: never a ✗
    assert RT.family("grammar") == RT.family("grammar-B") == "grammar"
    rows = [{"t": "00:17", "kind": "grammar-B"}, {"t": "06:43", "kind": "vocab-A", "tier": 1}, {"t": "bad", "kind": "grammar"},
            {"t": "1:00:01", "kind": "grammar"}]
    assert RT.predicted(rows) == [("grammar", 17.0), ("vocab", 403.0), ("grammar", 3601.0)]
    assert RT.predicted(rows, until=400) == [("grammar", 17.0)]


def test_match_is_one_to_one_nearest_same_family():
    key = [("grammar", 100.0), ("grammar", 110.0), ("vocab", 200.0)]
    pred = [("grammar", 104.0), ("grammar", 105.0), ("grammar", 140.0), ("vocab", 230.0), ("grammar", 200.0)]
    assert RT.match(pred, key) == 2                       # 104->100, 105->110; 140 too far; vocab 230 > 15 s; family differs
    s = RT.prf(2, 5, 3)
    assert (s["precision"], s["recall"]) == (40.0, 66.7) and abs(s["f05"] - 43.5) < 0.1


def test_haiku_vote_two_of_three():
    a = [("grammar", 100.0), ("vocab", 300.0)]
    b = [("grammar", 108.0)]
    c = [("vocab", 500.0)]
    assert RT.vote([a, b, c]) == [("grammar", 100.0)]


def test_no_limit_no_read(tmp_path, monkeypatch):
    monkeypatch.setattr(RT, "DIR", str(tmp_path))
    try:
        RT.run("haiku", 1, lesson="2026-10-10", yes=True)
        raise AssertionError("ran")
    except SystemExit as e:
        assert "no limit" in str(e)
