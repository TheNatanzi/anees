# -*- coding: utf-8 -*-
"""Guards the 2026-09-28 audit of Medi's unresolved word events (scripts/audit_vocab_unresolved.py).

Medi: "can you do a full audit of these unresolved and make sure they are being marked correctly so they aren't showing
up in the reporting here?" - an exact echo of Amal (Aug 25 5:15, kaan laazem ashtghel ktiir) was shown as "Unresolved".
The contract with the report: an event whose overlay says audit_bin = not_counted / no_evidence is never "unresolved".
"""
import copy, json, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_vocab_unresolved as A  # noqa: E402


@pytest.fixture(scope='module')
def committed():
    raw = A.J(A.EVIDENCE)
    review = A.J(A.REVIEW)
    return raw, review, A.view(raw['events'], review)


def reported_unresolved(e):
    """What the report may list as unresolved once it honours audit_bin (the display change asked of vocab-unknowns.js)."""
    return A.unknown(e) and e.get('audit_bin') not in ('not_counted', 'no_evidence')


def test_no_repeat_in_the_same_exchange_is_reported_unresolved(committed):
    _, _, V = committed
    bad = [e['id'][:10] for e in V.values() if e['speaker'] == 'Medi' and A.unknown(e) and A.bucket(e) in ('repeat', 'grammar')
           and reported_unresolved(e)]
    assert not bad, f'{len(bad)} echo/repeat/grammar events still read as unresolved: {bad[:10]}'


def test_medis_example_is_a_not_counted_echo(committed):
    _, _, V = committed
    e = next(x for i, x in V.items() if i.startswith('0ca24e0b16'))       # Aug 25 5:15 kaan, echo of Amal's full sentence
    assert e['audit_bin'] == 'not_counted' and e['audit_kind'] == 'echo' and A.points(e) is None


def test_every_unresolved_event_has_a_bin_and_open_ones_have_a_question(committed):
    _, _, V = committed
    medi = [e for e in V.values() if A.unknown(e)]
    assert all(e.get('audit_bin') for e in medi), [e['id'][:10] for e in medi if not e.get('audit_bin')][:10]
    opened = [e for e in medi if e['audit_bin'] == 'open']
    assert all(e.get('audit_question') for e in opened)
    assert len(opened) <= 40, f'{len(opened)} open events: the audit should leave only genuine questions'


def test_machine_verdicts_are_marked_and_reversible(committed):
    raw, review, _ = committed
    mine = [p for p in review['patches'].values() if p['changes'].get('audit_by') == A.REVIEWER]
    assert mine and all(p['changes'].get('reviewer') == A.REVIEWER for p in mine)
    again = copy.deepcopy(review)
    A.reset(again)
    assert not any(p['changes'].get('audit_by') for p in again['patches'].values())
    # a rebuild from the reset overlay gives exactly the committed patches (idempotent)
    A.audit(raw, again, A.J(A.VERDICTS), A.page_turns())
    assert again['patches'] == review['patches']


def test_no_vocab_event_inside_a_farsi_turn_is_unresolved_or_counted(committed):
    raw, _, V = committed
    hits, _, ev_hits = A.farsi_turns(A.page_turns(), raw['events'])
    assert any(h['date'] == '2026-09-26' and 1050 < h['t'] < 1070 for h in hits), 'Sep 26 17:31 Farsi turn not detected'
    inside = [e for e in V.values() if e['speaker'] == 'Medi' and A.in_farsi(e, hits, ev_hits)]
    assert inside, 'the Sep 26 17:46 و event should sit inside a Farsi turn'
    for e in inside:
        assert A.points(e) is None and e.get('audit_kind') == 'farsi' and not reported_unresolved(e), e['id'][:10]


def test_farsi_needs_two_signals():
    assert len(A.farsi_signals('وجان، پنجره رو می بندی؟ Air conditioning روشنه.')) >= 2
    for arabic in ('مع مي.', 'ده رجعت الـ cards؟', 'أنا من امريكا', 'الكل- Hold on'):
        assert len(A.farsi_signals(arabic)) < 2, arabic


def test_and_as_filler():
    f = A.filler_and
    assert f('شوب و uh, شوي مغيمة.'.split(), 1) is True           # Medi's example: و then "uh"
    assert f(['و'], 0) is True                                         # alone
    assert f('الولاد عطلوا و، uh,'.split(), 2) is True                 # pause right after
    assert f('قهوة كتير و أنا جاهز'.split(), 2) is False               # joins two words: a real "and"
    assert f('و، و أخ-- آآآ،'.split(), 0) is True                      # restart


def test_and_fillers_are_not_counted_in_data(committed):
    _, _, V = committed
    for prefix in ('c08eb0d7f8', '7cd8f17691'):                          # Sep 26 21:36 "u" and 21:45 "Shoab u uh, shwai"
        e = next(x for i, x in V.items() if i.startswith(prefix))
        assert e['audit_kind'] == 'filler' and A.points(e) is None


# ---------------------------------------------------------------- tiny fixtures for the one-attempt rules
def ev(i, t, word='shu', text='شو', row=None, assessment='independent', reason='x'):
    row = row or f'r{i}'
    return {'id': i, 'speaker': 'Medi', 'lesson_date': '2099-01-01', 't_start': t, 't_end': t + .4, 'row_id': row, 'word_key': word,
            'text': text, 'assessment': assessment, 'reason': reason, 'source_sha256': 's', 'source_id': 'x-recall-medi',
            'context': [{'row_id': row, 'speaker': 'Medi', 'text': text, 'timeline_start': t, 'timeline_end': t + .4}]}


def run(events, turns):
    for k, t in enumerate(turns):
        t['_end'] = t.get('end') or t['t'] + 1
    review = {'patches': {}, 'additions': [], 'transcript_rows': {}}
    R = A.audit({'events': events}, review, {'verdicts': {}}, {'2099-01-01': turns})
    return R['V2']


def test_stutter_in_one_turn_is_one_attempt():
    events = [ev('a', 10.0, text='شو،'), ev('b', 11.5, text='شو ركبتك؟')]
    V = run(events, [{'t': 9.8, 'end': 10.5, 'who': 'Medi', 'text': 'شو، uh,'}, {'t': 11.2, 'end': 12.5, 'who': 'Medi', 'text': 'شو ركبتك؟'}])
    counted = [i for i, e in V.items() if A.points(e) is not None]
    assert counted == ['b'] and V['a']['audit_kind'] == 'repeat'


def test_restart_across_a_bare_prompt_is_one_attempt():
    events = [ev('a', 20.0, text='كيفك؟'), ev('b', 26.0, text='كيفك؟')]
    turns = [{'t': 19.8, 'end': 20.6, 'who': 'Medi', 'text': 'كيفك؟'}, {'t': 22.0, 'end': 22.5, 'who': 'Amal', 'text': 'هاه؟'},
             {'t': 25.8, 'end': 26.6, 'who': 'Medi', 'text': 'كيفك؟'}]
    V = run([dict(e, word_key='kIfek') for e in events], turns)
    assert [i for i, e in V.items() if A.points(e) is not None] == ['b']
    assert V['a']['audit_kind'] == 'repeat'
    # a real Amal line in between keeps two attempts
    turns[1]['text'] = 'أنا تمام، إنت كيفك؟'
    V = run([dict(e, word_key='kIfek') for e in events], turns)
    assert sorted(i for i, e in V.items() if A.points(e) is not None) == ['a', 'b']


def test_duplicate_records_collapse_to_one_with_one_reason():
    a = ev('a', 30.0, row='pass1', assessment='unresolved', reason='Tutor recording context unavailable for this interval')
    b = ev('b', 30.1, row='pass2', assessment='unresolved', reason='Clarification request, not failed recall of shu')
    b['ignored'] = True
    V = run([a, b], [{'t': 29.9, 'end': 31.0, 'who': 'Medi', 'text': 'شو؟'}])
    kinds = sorted((V[i].get('audit_kind') or '') for i in 'ab')
    assert 'duplicate' in kinds, kinds
    survivor = next(V[i] for i in 'ab' if V[i].get('audit_kind') != 'duplicate')
    assert survivor['reason'] and isinstance(survivor['reason'], str)
