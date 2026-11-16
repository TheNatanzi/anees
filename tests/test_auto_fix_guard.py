# -*- coding: utf-8 -*-
"""Self-repair (Medi 2026-11-16 "fix this once and for all"): soft checks never block a lesson, the fixer is rate-limited,
the 12 h alarm names exactly the lessons that are late and not live."""
import datetime, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import auto_fix_guard as AF  # noqa: E402
import publish_guard as G  # noqa: E402


def T(s):
    return datetime.datetime.fromisoformat(s).astimezone()


def test_fixer_runs_at_most_twice_a_day_and_not_within_three_hours():
    t = T('2026-11-16T15:00:00')
    assert AF.may_try({}, t)[0]
    assert not AF.may_try({'tries': ['2026-11-16T13:30:00']}, t)[0]                       # 1.5 h ago
    assert AF.may_try({'tries': ['2026-11-16T11:00:00']}, t)[0]                           # 4 h ago
    assert not AF.may_try({'tries': ['2026-11-16T08:00:00', '2026-11-16T11:00:00']}, t)[0]  # 2 today
    assert AF.may_try({'tries': ['2026-11-15T20:00:00', '2026-11-15T21:00:00']}, t)[0]      # yesterday's do not count


def test_failures_now_takes_hard_then_soft_once_each():
    st = {'last_check': {'outcome': 'blocked', 'reason': 'check_numbers: FAIL x; tests_py: exit 1: a'},
          'soft_failures': {'failures': ['tests_py: exit 1: a', 'rehear_rows: 1 problem']}}
    assert [f.split(':')[0] for f in AF.failures_now(st)] == ['check_numbers', 'tests_py', 'rehear_rows']
    assert AF.failures_now({'last_check': {'outcome': 'pushed', 'reason': ''}}) == []
    # a check's detail can hold '; ' itself (lesson_coverage: '09-04 missing from ...; 09-05 missing from ...')
    st = {'last_check': {'outcome': 'blocked', 'reason': 'lesson_coverage: 09-04 missing; 09-05 missing; tests_py: exit 1'}}
    assert [f.split(':')[0] for f in AF.failures_now(st)] == ['lesson_coverage', 'tests_py']
    st['last_check']['checks'] = [{'id': 'lesson_coverage', 'required': True, 'ok': False, 'detail': 'a; b'},
                                  {'id': 'tests_py', 'required': True, 'ok': False, 'soft': True, 'detail': 'x'}]
    assert AF.failures_now(st) == ['lesson_coverage: a; b']


def test_late_lessons_are_recorded_over_12h_ago_and_not_live(tmp_path):
    for d in ('2026-11-10', '2026-11-15', '2026-11-16'):
        (tmp_path / d / 'tracks').mkdir(parents=True)
        (tmp_path / d / 'tracks' / 'Medi.mp3').write_bytes(b'x')
    t = T('2026-11-16T15:00:00').timestamp()
    os.utime(tmp_path / '2026-11-10' / 'tracks' / 'Medi.mp3', (t - 6 * 86400, t - 6 * 86400))
    os.utime(tmp_path / '2026-11-15' / 'tracks' / 'Medi.mp3', (t - 24 * 3600, t - 24 * 3600))
    os.utime(tmp_path / '2026-11-16' / 'tracks' / 'Medi.mp3', (t - 2 * 3600, t - 2 * 3600))
    late = [d for d, _ in AF.late_lessons(tmp_path, live={'2026-11-10'}, t=T('2026-11-16T15:00:00'))]
    assert late == ['2026-11-15']          # 11-10 is live, 11-16 is only 2 h old


def test_a_soft_check_failing_does_not_block_but_is_reported(tmp_path):
    cfg = {'required': ['json_data', 'tests_py'], 'soft': ['tests_py'], 'advisory': [],
           'commands': {'tests_py': {'cmd': ['{python}', '-c', 'import sys; sys.exit(1)']}}}
    (tmp_path / 'docs' / 'data').mkdir(parents=True)
    (tmp_path / 'docs' / 'data' / 'x.json').write_text('{}', encoding='utf-8')
    res = G.run_checks(tmp_path, config=cfg)
    assert res['ok'], res['reason']
    assert [x.split(':')[0] for x in res['soft_failed']] == ['tests_py']
    cfg['soft'] = []
    assert not G.run_checks(tmp_path, config=cfg)['ok']


def test_hard_checks_stay_hard_in_the_live_config():
    soft = set(G.load_config(G.ROOT).get('soft') or [])
    for hard in ('json_data', 'check_numbers', 'check_rules', 'check_pages', 'lesson_ledger', 'review_done', 'clean_tree',
                 'recordings_complete'):
        assert hard not in soft, hard
