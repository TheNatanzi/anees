# -*- coding: utf-8 -*-
"""Eval floors for deterministic scorers, against frozen gold versions (gold/manifest.json).

The grammar detector's recall on grammar@v1-heldout must not fall more than 2 points below the last
ACCEPTED score in gold/history.jsonl. To accept a new baseline on purpose (a better detector, or a
known trade-off Medi said yes to):

    python scripts/score_grammar_detector.py --no-run --gold=grammar@v1-heldout --accept

This scores the committed detector output (docs/data/grammar-audit.json); it does not re-run the auditor,
which needs the raw lesson tracks that are not in the repo. Nothing here costs money.
"""
import pytest

import score_grammar_detector as S

FLOOR_PTS = 0.02


def _baseline(gold_id):
    b = S.last_accepted(gold_id)
    if not b:
        pytest.fail(f"no accepted line for {gold_id} in gold/history.jsonl - run the scorer with --accept once")
    return b


@pytest.mark.parametrize("gold_id", ["grammar@v1-heldout"])
def test_detector_recall_floor(gold_id):
    b = _baseline(gold_id)
    r = S.score(verbose=False, gold=gold_id)
    assert r["recall"] >= b["recall"] - FLOOR_PTS, (
        f"{gold_id} recall {r['recall']:.3f} < last accepted {b['recall']:.3f} - {FLOOR_PTS} "
        f"(accepted {b['ts']}, code {b.get('code_sha')})")


@pytest.mark.parametrize("gold_id", ["grammar@v1-heldout", "grammar@v1-tuned", "grammar@v2-audit"])
def test_history_baseline_is_for_the_frozen_version(gold_id):
    """A baseline scored on another version of the set is not a baseline: sha must match the manifest."""
    b = _baseline(gold_id)
    e, _ = S.gold_entry(gold_id)
    assert b["sha"] == e["sha256"] and b["n"] == e["n"]


def test_frozen_v1_splits_score_like_the_live_goldset():
    """The frozen copies are the same rows the scorer used before freezing (no drift at freeze time)."""
    for sp in ("tuned", "heldout"):
        live, frozen = S.score(verbose=False, split=sp), S.score(verbose=False, gold=f"grammar@v1-{sp}")
        if live["gold_grammar"] != frozen["gold_grammar"]:
            pytest.skip("docs/data/grammar-goldset.json moved on since the freeze; the frozen copy is the reference now")
        assert live == frozen, sp
