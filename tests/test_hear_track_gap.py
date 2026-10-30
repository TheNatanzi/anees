# -*- coding: utf-8 -*-
"""scripts/hear_track_gap.py (Medi 2026-10-29 "(a) Recover first"): a stretch of his own track the engine left empty is
heard again; line times come from the audio's speech bursts, words from the listens' vote, nothing is invented."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import hear_track_gap as H  # noqa: E402


def test_vote_keeps_the_listen_the_others_agree_with():
    assert H.vote(['So روحي بيت', 'so روحي بيت', 'روحي من بيت'])[0].lower() == 'so روحي بيت'


def test_vote_invents_nothing():
    assert H.vote(['', '', 'Yeah'])[0] == ''                     # two listens heard no words of his
    assert H.vote(['banana split', 'go home', 'red car'])[0] == ''  # no two listens agree


def test_the_2026_10_28_layer_is_line_level_on_the_track_clock():
    p = os.path.join(ROOT, 'data', 'backfill', 'gapfill', '2026-10-28', 'gapfill_medi.json')
    g = json.load(open(p, encoding='utf-8'))
    w = g['window']
    assert g['source'] == 'own_track' and g['words'] == []       # no made-up word times
    assert all(w['from_s'] - 1 <= L['t'] <= L['end'] <= w['to_s'] + 1 and L['who'] == 'Medi' for L in g['lines'])
    assert g['summary']['est_cost_usd'] <= 1.0                    # Medi's cap for this run
