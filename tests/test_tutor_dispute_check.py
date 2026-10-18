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


def test_am_33_her_answers_rule_on_their_audit_rows():
    """Medi 2026-10-18 'Apply': 'right' drops the mapped row, 'mistake' confirms it (a PROPOSE row becomes scored grammar)."""
    import apply_amal_audit_rulings as A
    M = {"items": {"2026-10-10:t74889": {"uid": "FA-1", "bucket": "B6"}, "2026-10-08:t97357": {"uid": "FA-2"}}}
    rows = [{"id": 1, "kind": "dispute_check", "word_key": "disputecheck:2026-10-10:t74889", "payload": {"answer": "mistake", "typed": "Should be kaanat"}},
            {"id": 2, "kind": "dispute_check", "word_key": "disputecheck:2026-10-08:t97357", "payload": {"answer": "right"}},
            {"id": 3, "kind": "dispute_check", "word_key": "disputecheck:2026-10-09:t111635", "payload": {"answer": "cant_tell"}}]
    out = A.dispute_rulings(rows, M)
    assert [(r["kind"], r["payload"]["audit_uid"], r["payload"].get("bucket")) for r in out] == [("wrong", "FA-1", "B6"), ("right", "FA-2", None)]
    assert all(r["source"] == "after" for r in out)
