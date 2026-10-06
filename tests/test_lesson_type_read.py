# -*- coding: utf-8 -*-
"""LS-08 / LS-09 / LS-10 (Medi 2026-10-02: "there was a new word from the lesson yesterday... you didnt catch it it was
like sheja3a or something for "motivation". why didnt you catch this").

10-01: Amal typed "mitshajje3 = motivated" at 06:52; the Tutor new-words list had it, but the lesson type read listed only
oola and called 07:00-15:20 "off-lesson (a customer call)". These tests plant that mistake and prove each rule catches it.
Offline: a temp repo, no claude call."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import lesson_type_read as LTR
import publish_guard as G
import review_lesson as RL

D = '2026-10-01'
GOOD = {'date': D, 'type': 'review-grammar', 'review_mode': 'speaking',
        'why': '15:22-1:04:50 is the el- review (15:34 sayyaaret el-BM); 10:00-13:48 off-lesson: Medi on a customer call.',
        'taught': [], 'read_by': 'test', 'at': '2026-10-02T13:00:00-07:00',
        'taught_words': [{'latin': 'mitshajje3', 'arabic': 'متشجع', 'english': 'motivated', 't': '06:52'},
                         {'latin': 'oola', 'arabic': 'أولى', 'english': 'first (f)', 't': '55:26'}],
        'not_taught': [{'key': 'ممتاز', 'reason': 'her praise word at 43:53, not taught'}],
        'off_lesson': [{'from': '10:00', 'to': '13:48', 'who': 'Medi', 'what': 'customer call (booking a pickup)'}]}
TURNS = [{'t': 396.0, 'who': 'Medi', 'text': 'مشجع.'},
         {'t': 412.3, 'who': 'chat', 'text': 'mitshajje3 = motivated'},
         {'t': 627.0, 'who': 'Medi', 'text': "Okay, uh, Ms. Gantz, one moment."},
         {'t': 700.0, 'who': 'Amal', 'text': 'Okay.'},
         {'t': 966.3, 'who': 'chat', 'text': 'sayyaaret el-BM illi'}]
VERDICTS = [{'date': D, 'key': 'mitshajje3', 'verdict': 'new', 'arabic': 'متشجع', 'arabizi': 'mitshajje3', 'english': 'motivated'},
            {'date': D, 'key': 'ممتاز', 'verdict': 'new', 'arabic': 'ممتاز', 'arabizi': None, 'english': 'excellent'},
            {'date': D, 'key': 'mitshajje', 'verdict': 'new', 'dup_of': 'mitshajje3', 'arabic': 'متشجع'},
            {'date': D, 'key': 'taman', 'verdict': 'on_doc', 'arabic': 'تمن'}]


def make(tmp, read=None, turns=None, verdicts=None):
    for p in ('data/lesson-work/lesson-types', 'docs/data/lessons'):
        (tmp / p).mkdir(parents=True, exist_ok=True)
    (tmp / LTR.REL_DIR / f'{D}.json').write_text(json.dumps(read or GOOD, ensure_ascii=False), encoding='utf-8')
    (tmp / 'docs/data/lessons' / f'{D}.json').write_text(json.dumps({'turns': turns or TURNS}, ensure_ascii=False), encoding='utf-8')
    (tmp / LTR.VERDICTS).write_text(json.dumps(VERDICTS if verdicts is None else verdicts, ensure_ascii=False), encoding='utf-8')
    (tmp / LTR.NEW_WORDS).write_text(json.dumps({'items': [{'date': D, 'key': 'glue:la', 'source': 'glue', 'arabic': 'لا'}]}),
                                     encoding='utf-8')
    return tmp


def test_ls_08_reader_prompt_lists_every_word_amal_gives_with_the_real_moment():
    p = LTR.prompt(D, 'R')
    assert 'LS-08' in p and "how do you say" in p and 'mitshajje3' in p and '06:52' in p
    assert 'never words Medi already used himself' not in p      # the old wording that let a repeated word drop out


def test_ls_09_tutor_new_word_missing_from_taught_words_fails(tmp_path):
    repo = make(tmp_path)
    assert LTR.cross_check(D, str(repo)) == []                    # good read: the glue word and the dup are not asked for
    bad = dict(GOOD, taught_words=[GOOD['taught_words'][1]])      # the real 10-01 miss: only oola
    make(tmp_path, read=bad)
    issues = LTR.cross_check(D, str(repo))
    assert len(issues) == 1 and issues[0].startswith('LS-09: mitshajje3')
    assert LTR.check([D], str(repo)) == {D: issues}
    ok, detail = G.check_taught_words_cross_check(repo)
    assert ok is False and 'mitshajje3' in detail
    no_reason = dict(GOOD, not_taught=[{'key': 'ممتاز', 'reason': ''}])
    make(tmp_path, read=no_reason)
    assert LTR.load(D, str(repo))[0] is None                      # not_taught without a reason is not a valid read


def test_ls_09_guard_check_is_required_and_review_step_fails_closed(tmp_path):
    live = json.loads((G.ROOT / G.CONFIG).read_text(encoding='utf-8'))
    assert 'taught_words_cross_check' in live['required'] and 'tests/test_lesson_type_read.py' in live['commands']['tests_py']['cmd']
    bad = dict(GOOD, taught_words=[GOOD['taught_words'][1]])
    repo = make(tmp_path, read=bad)
    calls, failures = [], []
    RL.taught_cross_step(D, False, failures, repo=str(repo), reader=lambda *a, **k: calls.append(k.get('step')))
    assert calls == ['lesson.type_reconcile'] and failures and 'LS-09' in failures[0]

    def fixing_reader(prompt, label, **k):                        # the reconcile reader adds the word -> passes
        assert 'mitshajje3' in prompt
        (repo / LTR.REL_DIR / f'{D}.json').write_text(json.dumps(GOOD, ensure_ascii=False), encoding='utf-8')
    failures = []
    assert RL.taught_cross_step(D, False, failures, repo=str(repo), reader=fixing_reader) == [] and failures == []


def test_ls_10_off_lesson_window_needs_who_what_times_and_fails_on_amal_teaching(tmp_path):
    no_window = dict(GOOD, off_lesson=[])
    repo = make(tmp_path, read=no_window)
    r, why = LTR.load(D, str(repo))
    assert r is None and any('LS-10' in w for w in why)          # "off-lesson" in why with no window = not a valid read
    vague = dict(GOOD, off_lesson=[{'from': '07:00', 'to': '15:20', 'who': '', 'what': ''}])
    make(tmp_path, read=vague)
    assert LTR.load(D, str(repo))[0] is None
    wide = dict(GOOD, off_lesson=[{'from': '07:00', 'to': '16:20', 'who': 'Medi', 'what': 'a customer call'}])
    make(tmp_path, read=wide)
    issues = LTR.cross_check(D, str(repo))
    assert len(issues) == 1 and issues[0].startswith('LS-10: off-lesson 07:00-16:20') and 'sayyaaret' in issues[0]
    amal_voice = TURNS + [{'t': 650.0, 'who': 'Amal', 'text': 'لا، بنقول أنا على الـ Wi-Fi'}]
    make(tmp_path, read=GOOD, turns=amal_voice)
    issues = LTR.cross_check(D, str(repo))
    assert len(issues) == 1 and issues[0].startswith('LS-10: off-lesson 10:00-13:48')
    make(tmp_path)                                               # her "Okay." (no Arabic) inside the call is not teaching
    assert LTR.cross_check(D, str(repo)) == []


def test_ls_13_summary_is_a_headline_rules_with_bullets_and_examples_and_required_for_new_reads():
    """LS-13 (Medi 2026-10-05: "This is way to wordy. Please simplify it..."): the page shows a structured reading, not prose."""
    good = {'headline': 'Tool words before and after a noun: awal, aa5er, taani, 8eir, nafs, kul',
            'rules': [{'title': 'nafs always takes el-: nafs el-ishi', 'pattern': 'nafs + el- + noun',
                       'bullets': ['nafs = the same', 'the noun after it always has el-'],
                       'examples': [{'t': '49:59', 'line': 'نفس الإشي - the same thing'}]}],
            'also': ['Review of awal / taani from 10-01 (16:54-29:37)']}
    assert LTR.summary_problems(good) == []
    assert LTR.summary_problems(None) == [] and LTR.summary_problems(None, required=True)      # old reads may lack it; new reads may not
    assert LTR.summary_problems({**good, 'headline': 'at 16:54 she taught awal'})               # a headline is one plain line without times
    assert LTR.summary_problems({**good, 'rules': [{**good['rules'][0], 'bullets': []}]})       # a rule explains itself in 1-4 bullets
    assert LTR.summary_problems({**good, 'rules': [{**good['rules'][0], 'examples': [{'t': 'noon', 'line': 'x'}]}]})   # examples are real moments
    # a read stamped from 2026-10-05 noon on must carry the summary
    d = dict(GOOD, at='2026-10-05T18:00:00-07:00')
    assert any('summary missing' in x for x in LTR.problems(d, D))
    assert LTR.problems({**d, 'summary': good}, D) == []
    assert LTR.problems(GOOD, D) == []                                                          # the 10-02 read (no summary) still passes
