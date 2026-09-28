"""Farsi side conversation (Medi 2026-09-28: "this is farsi talking to my dad") is never scored as Arabic."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import farsi  # noqa: E402

DATA = os.path.join(HERE, "..", "docs", "data")


def test_detector_needs_two_signals():
    assert farsi.is_farsi("این روشنه پنجره رو ببند")
    assert farsi.is_farsi("بابا جان ميرم")
    assert not farsi.is_farsi("أنا صحيت بدري الصباح")
    assert not farsi.is_farsi("بدي روح عالبيت")
    assert not farsi.is_farsi("")


def test_ladder_does_not_score_farsi_turns():
    for date in ("2026-08-25", "2026-09-26"):
        doc = json.load(open(os.path.join(DATA, "sentence-ladder", date + ".json"), encoding="utf-8"))
        for u in doc.get("speak", []):
            if u.get("scored"):
                assert not farsi.is_farsi(u.get("text")), (date, u["id"])


def test_grammar_uses_have_no_farsi():
    g = json.load(open(os.path.join(DATA, "grammar-usage.json"), encoding="utf-8"))
    for rid, uses in g["uses"].items():
        for x in uses:
            assert not farsi.is_farsi(x.get("said")), (rid, x["date"], x["mmss"])
