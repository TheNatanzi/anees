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


def test_am_35_judge_list_is_blind_and_leaves_out_moments_she_already_ruled_on():
    """Medi 2026-10-18 'Yes, build them and give to amal': every AI-judge slip not in key v3, same blind card."""
    D = json.load(open(DC.JUDGE_OUT, encoding='utf-8'))
    assert D['list'] == 'key-check-judges' and D['rule'] == 'AM-35' and D['kind'] == 'dispute_check'
    assert D['n'] == len(D['items']) == 49 and all(o.get('box') for o in D['questions'][0]['options'])
    blob = json.dumps(D['items'], ensure_ascii=False).lower()
    for leak in ('opus', 'sonnet', 'astra', 'gemini', 'argon', 'gpt', 'flagged_by', 'ai says', 'key says'):
        assert leak not in blob, leak
    old = {x['id'] for x in json.load(open(DC.OUT, encoding='utf-8'))['items']}
    assert not old & {x['id'] for x in D['items']}                            # never asks her the same moment twice


def test_am_35_every_card_shows_the_line_that_holds_the_flagged_words_and_argons_key_additions_ride_blind():
    """2026-10-19 (Medi: 'make sure everything is clear for her'): 7 cards showed a nearby line, not the one with the words
    the card says he said; 'at' pins them. Argon's 20 key-v3 additions ride in the same blind list (one shares the 10-10
    21:44 card) so she confirms them before key v4."""
    import re
    norm = lambda s: re.sub(r'[ً-ْٰـ?؟,،.()…-]', ' ', s).replace('أ', 'ا').replace('إ', 'ا').replace('ٱ', 'ا').lower()
    D = json.load(open(DC.JUDGE_OUT, encoding='utf-8'))
    for x in D['items']:
        said = [w for w in norm(x['rows'][0]['ar']).split() if len(w) >= 2 and w not in ('is', 'it', 'um', 'this', 'the')]
        assert x['rows'][0]['label'].startswith('The possible mistake') and any(w in norm(x['line']['ar']) for w in said), (x['id'], said)
    M = json.load(open(DC.JUDGE_MOMENTS, encoding='utf-8'))['moments']
    assert sum(m.get('set') == 'argon-key-v3' for m in M) == 19 and any(m.get('also') for m in M)


def test_am_36_too_short_cards_go_back_to_her_and_wait():
    """AM-36 (Medi 2026-10-20: 'when she's asking for more info like adding more recording send it back to her before
    grading'): a 'clip too short' answer sends the card back with more audio, and grading waits for her second answer."""
    import build_tutor_more_check as MC
    assert MC.needs_more({"answer": "cant_tell", "typed": "The clip is too short to decide"})
    assert MC.needs_more({"answer": "right", "typed": "Clip is not sufficient to decide."})
    assert not MC.needs_more({"answer": "right", "typed": "He's not answering in the clip, I am helping him."})
    assert not MC.needs_more({"answer": "mistake"})
    ans = {"disputecheck:A": {"answer": "right", "typed": "too short"}, "disputecheck:B": {"answer": "mistake"},
           "disputecheck:C": {"answer": "cant_tell", "typed": "Clip too short"}, "disputecheck:C-more": {"answer": "mistake"}}
    assert MC.final_answer("A", ans) is None                      # asked for more, not answered again: pending
    assert MC.final_answer("B", ans)["answer"] == "mistake"
    assert MC.final_answer("C", ans)["answer"] == "mistake"       # her second answer, with more audio, is the one used
    rows = [{"id": 1, "kind": "dispute_check", "word_key": "disputecheck:A", "payload": {"answer": "right", "typed": "x"}},
            {"id": 2, "kind": "undo", "word_key": "disputecheck:A"}]
    assert MC.latest(rows) == {}
    D = json.load(open(MC.OUT, encoding='utf-8'))
    assert D['list'] == 'key-check-more' and D['rule'] == 'AM-36' and D['n'] == len(D['items']) >= 1
    for x in D['items']:
        assert x['id'].endswith('-more') and x['rows'][0]['label'] == 'Your note last time'
        a, b = [float(v) for v in x['clips'][0]['src'].split('#t=')[1].split(',')]
        assert b - a >= 30                                          # about 40 s of the lesson, not the short clip again
