"""M9 gate: possible misses get a kind (word / article / gender / tense / plural / pronunciation / unclear), never guessed:
the real Sep 4 moment 61:23 (Aktar, 'No أل just أكتر إشي') = article; a grammar-only slip does not push the word into the
Missed bucket (it counts as a grammar slip instead); Amal's tap overrides; the model fallback is capped and never runs in tests."""
import io, json
from pathlib import Path
import pytest

import miss_kind as mk
import buckets

ROOT = Path(__file__).resolve().parent.parent


def test_form_diff_rules():
    assert mk.form_diff('So الأكتر', 'أكتر')[0] == 'article'
    assert mk.form_diff('الكلمة.', 'كلمة')[0] == 'article'
    assert mk.form_diff('كتير', 'كتير')[0] == 'same'
    assert mk.form_diff('مبسوطة', 'مبسوط')[0] == 'gender'
    assert mk.form_diff('طلاب', 'طالب', 'طلاب')[0] == 'plural'
    assert mk.form_diff('معلمين', 'معلم')[0] == 'plural'
    assert mk.form_diff('شوب', 'حر')[0] == 'other'


def test_cue_rules():
    assert mk.cue_kind('No أل just أكتر إشي')[0] == 'article'
    assert mk.cue_kind('it is feminine, so مبسوطة')[0] == 'gender'
    assert mk.cue_kind('that is the past, we want present')[0] == 'tense'
    assert mk.cue_kind('this is plural')[0] == 'plural'
    assert mk.cue_kind('pronounce the ط from the throat')[0] == 'pronunciation'
    assert mk.cue_kind('مغني means singer')[0] == 'word'
    assert mk.cue_kind('طيب، حلو')[0] is None


def test_classify_priority_and_unclear():
    doc = {'arabic': 'أكتر', 'arabizi': 'Aktar', 'english': 'More'}
    r = mk.classify({'text': 'So الأكتر', 'correction': True}, 'No أل just أكتر إشي.', doc)
    assert r['miss_kind'] == 'article' and 'أل' in r['miss_why']
    r = mk.classify({'text': 'أكتر', 'correction': True}, 'مغني means singer. حلو', {'arabic': 'مغني'})
    assert r['miss_kind'] == 'word'
    r = mk.classify({'text': 'كتير', 'correction': True}, 'لا وقت طويل. Mm.', {'arabic': 'كتير'})
    assert r['miss_kind'] == 'unclear'
    r = mk.classify({'text': 'كتير', 'correction': False, 'asked': True}, '', {'arabic': 'كتير'})
    assert r['miss_kind'] == 'word'
    assert mk.classify({'text': 'كتير', 'correction': False}, 'anything', {'arabic': 'كتير'})['miss_kind'] is None


def test_real_sep4_aktar_is_article():
    u = json.load(io.open(ROOT / 'data' / 'lessons' / '2026-09-04' / 'understanding.json', encoding='utf-8'))
    e = next(e for e in u['events'] if e['word_key'] == 'aktar' and abs(e['t_start'] - 3683.25) < 0.5)
    assert e.get('miss_kind') == 'article', e
    a = next(e for e in u['events'] if e['word_key'] == 'a7san' and abs(e['t_start'] - 135.18) < 0.5)
    assert a.get('miss_kind') == 'article'          # الأحسن vs أحسن
    assert all(e.get('miss_kind') in mk.KINDS for e in u['events'] if e['speaker'] == 'Medi' and (e['correction'] or e.get('asked')))


def test_grammar_slip_does_not_bucket_the_word_as_missed():
    D = ['2026-06-01', '2026-07-01', '2026-08-01', '2026-09-04']
    ev = [{'lesson_date': '2026-06-01', 'word_key': 'aktar', 'speaker': 'Medi', 'prompted': False, 'correction': True, 'miss_kind': 'article', 't_start': 1}]
    st = buckets.compute(ev, [], D)['aktar']
    assert st['bucket'] == 'cold' and st['grammar_misses'] == 1 and st['grammar_kinds'] == ['article']
    ev[0]['miss_kind'] = 'word'
    assert buckets.compute(ev, [], D)['aktar']['bucket'] == 'missed'
    ev[0]['miss_kind'] = 'unclear'
    assert buckets.compute(ev, [], D)['aktar']['bucket'] == 'missed'   # unclear stays a possible miss


def test_llm_fallback_is_capped_and_mockable(monkeypatch):
    calls = []
    monkeypatch.setattr(mk, 'llm_classify', lambda e, ctx, d: calls.append(1) or 'tense')
    words, events = [], []
    for i in range(12):                                   # 12 separate slips, each followed by an English explanation from Amal
        t = 100.0 * i
        words.append({'s': t, 'e': t + 0.5, 'spk': 'Medi', 'w': 'كتير'})
        words += [{'s': t + 1 + k * 0.4, 'e': t + 1.3 + k * 0.4, 'spk': 'Amal', 'w': w} for k, w in enumerate('so here you need the other form because we are talking about yesterday okay'.split())]
        events.append({'speaker': 'Medi', 'word_key': 'ktIr', 'text': 'كتير', 't_start': t, 't_end': t + 0.5, 'correction': True})
    counts = mk.classify_all(events, words, {'ktIr': {'arabic': 'كتير'}}, use_llm=True)
    assert len(calls) == mk.MAX_LLM_PER_LESSON and counts['tense'] == 10 and counts['unclear'] == 2


def test_phrase_slip_sits_on_the_head_word_not_the_tail():
    """Sep 4 61:23-61:29: 'الأكتر إشي' -> ONE slip on aktar (phrase 'aktar eshi', superlative pattern); eshi is not blamed."""
    u = json.load(io.open(ROOT / 'data' / 'lessons' / '2026-09-04' / 'understanding.json', encoding='utf-8'))
    head = next(e for e in u['events'] if e['word_key'] == 'aktar' and abs(e['t_start'] - 3683.25) < 0.5)
    tail = next(e for e in u['events'] if e['word_key'] == 'eshi' and abs(e['t_start'] - 3684.41) < 0.5)
    assert head['miss_kind'] == 'article' and head.get('pattern') == 'superlative' and 'the most' in head['miss_why']
    assert head.get('phrase', '').startswith('aktar eshi')
    assert not tail['correction'] and tail.get('part_of') == 'aktar' and tail.get('miss_kind') is None


def test_word_choice_is_shaky_not_missed():
    """61:07 'a7san right?' -> Amal: 'No. The best thing is … أكتر' = word choice: Medi knows a7san, aktar fits 'the most'."""
    u = json.load(io.open(ROOT / 'data' / 'lessons' / '2026-09-04' / 'understanding.json', encoding='utf-8'))
    e = next(e for e in u['events'] if e['word_key'] == 'a7san' and abs(e['t_start'] - 3668.0) < 0.6)
    assert e['miss_kind'] == 'choice' and e.get('wanted') == 'aktar', e
    ev = [{'lesson_date': '2026-06-01', 'word_key': 'a7san', 'speaker': 'Medi', 'prompted': False, 'correction': False, 'asked': True, 'miss_kind': 'choice', 't_start': 1}]
    assert buckets.compute(ev, [], ['2026-06-01', '2026-07-01', '2026-08-01', '2026-09-04'])['a7san']['bucket'] == 'shaky'


def test_dangling_el_is_an_article_slip():
    """08:37-08:40: 'بعيد الـ نفس مشكلة' -> Amal 'نفس المشكلة': the loose الـ before nafs is the el- slip (Ba3eed and Nafs both)."""
    u = json.load(io.open(ROOT / 'data' / 'lessons' / '2026-09-04' / 'understanding.json', encoding='utf-8'))
    for key, t in (('ba3Id', 517.57), ('nafs', 530.6)):
        e = next(e for e in u['events'] if e['word_key'] == key and abs(e['t_start'] - t) < 0.6)
        assert e['miss_kind'] == 'article' and ('el-' in e['miss_why'] or 'الـ' in e['miss_why']), (key, e.get('miss_kind'), e.get('miss_why'))
