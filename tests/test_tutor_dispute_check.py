# -*- coding: utf-8 -*-
"""AM-33: the tutor's dispute-check list (Medi 2026-10-17)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import build_tutor_dispute_check as DC


def test_am_33_list_is_blind_has_a_why_box_on_every_answer_and_its_own_prefix():
    D = json.load(open(DC.OUT, encoding='utf-8'))
    assert D['kind'] == 'dispute_check' and D['prefix'] == 'disputecheck'      # never shares a key with the AM-29 key check
    assert all(o.get('box') for o in D['questions'][0]['options'])            # her reason is the point
    assert D['n'] == len(D['items']) == 14
    blob = json.dumps(D['items'], ensure_ascii=False).lower()
    for leak in ('ai says', 'key says', 'readers', 'tier', 'chip'):            # blind: which side said what is never shown
        assert leak not in blob, leak
    assert all(x['clips'] and x['line']['ar'] for x in D['items'])
