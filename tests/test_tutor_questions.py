# -*- coding: utf-8 -*-
"""AM-34: plain questions for the tutor (Medi 2026-10-18)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import build_tutor_questions as TQ


def test_am_34_pleasantries_questions_one_card_each_with_a_box_for_her_words():
    D = json.load(open(TQ.out_path('pleasantries'), encoding='utf-8'))
    assert D['kind'] == 'tutor_question' and D['prefix'] == 'tutorq-pleasantries'
    assert D['n'] == len(D['items']) == 5 and all(x['ask'] for x in D['items'])
    opts = D['questions'][0]['options']
    assert [o['v'] for o in opts] == ['yes', 'no', 'depends'] and all(o.get('box') for o in opts)
    q3 = [x for x in D['items'] if x['id'] == 'q3'][0]
    assert q3['clips'] and '2026-10-10/audio/lesson.mp3' in q3['clips'][0]['src']
