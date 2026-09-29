# -*- coding: utf-8 -*-
"""The publish guard (Medi decision 7, 2026-09-29): nothing reaches master (= the live site) unless every required check
passes; a block keeps the last good version live and tells Medi why (hourly log line + local state; the published status
carries the last block once a later run passes). Offline: git and the check commands are fakes."""
import json, os, re, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import publish_guard as G

DATES = ['2026-09-26', '2026-09-28']


class FakeRun:
    """git + check commands. rc/out per check script name; git answers from a small table."""
    def __init__(self, checks=None, pull_rc=0, push_rc=0, dirty='', timeout=()):
        self.checks, self.pull_rc, self.push_rc, self.dirty, self.timeout = checks or {}, pull_rc, push_rc, dirty, set(timeout)
        self.calls = []

    def __call__(self, cmd, *a, **k):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        if cmd[0] == 'git':
            sub = cmd[1]
            if sub == 'rev-parse':
                return subprocess.CompletedProcess(cmd, 0, 'a' * 40 + '\n', '')
            if sub == 'status':
                return subprocess.CompletedProcess(cmd, 0, self.dirty, '')
            if sub == 'ls-files':
                return subprocess.CompletedProcess(cmd, 0, '\n'.join(f'docs/lessons/{d}/audio/lesson.mp3' for d in DATES), '')
            if sub == 'pull':
                return subprocess.CompletedProcess(cmd, self.pull_rc, '', 'CONFLICT (content): docs/data/lessons.json' if self.pull_rc else '')
            if sub == 'rev-list':
                return subprocess.CompletedProcess(cmd, 0, '2\n', '')
            if sub == 'push':
                return subprocess.CompletedProcess(cmd, self.push_rc, '', 'rejected' if self.push_rc else '')
            return subprocess.CompletedProcess(cmd, 0, '', '')
        name = next((Path(c).name for c in cmd[1:] if c.endswith(('.py', '.cjs'))), cmd[-1])
        if name in self.timeout:
            raise subprocess.TimeoutExpired(cmd, k.get('timeout'))
        rc, out = self.checks.get(name, (0, 'ok'))
        return subprocess.CompletedProcess(cmd, rc, out, '')

    def pushes(self):
        return [c for c in self.calls if c[:2] == ['git', 'push']]


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding='utf-8')


@pytest.fixture
def repo(tmp_path):
    cfg = {'required': ['step_failures', 'clean_tree', 'json_data', 'lesson_coverage', 'accuracy_gates', 'check_numbers', 'arabizi_gaps'],
           'advisory': ['lesson_type_read'], 'total_timeout_s': 300, 'clean_paths': ['docs'],
           'commands': {'accuracy_gates': {'cmd': ['{python}', 'scripts/accuracy_gates.py', 'check'], 'timeout_s': 60},
                        'check_numbers': {'cmd': ['{python}', 'scripts/check_numbers.py'], 'timeout_s': 60},
                        'arabizi_gaps': {'cmd': ['{node}', 'scripts/arabizi_gaps.cjs'], 'timeout_s': 60, 'stdout_must_match': '\\b0 words\\b'}}}
    write(tmp_path / G.CONFIG, cfg)
    for s in ('accuracy_gates.py', 'check_numbers.py', 'arabizi_gaps.cjs'):
        write(tmp_path / 'scripts' / s, '# stub for the fake runner')
    dd = tmp_path / 'docs' / 'data'
    write(dd / 'lessons.json', {'lessons': [{'date': d, 'type_why': 'read'} for d in DATES]})
    for d in DATES:
        write(tmp_path / 'docs' / 'lessons' / f'{d}.html', 'page')
        write(dd / 'lessons' / f'{d}.json', {'turns': [{'t': 1, 'who': 'Amal', 'text': 'x'}]})
        write(dd / 'sentence-ladder' / f'{d}.json', {'units': []})
    write(dd / 'sentence-ladder.json', {'lessons': [{'date': d} for d in DATES]})
    write(dd / 'grammar-console.json', {'lessons': [{'date': d} for d in DATES], 'rules': []})
    write(dd / 'grammar-usage.json', {'lessons': {d: {} for d in DATES}})
    write(dd / 'accuracy-release.json', {'lessons': [{'date': d} for d in DATES], 'totals': {}})
    write(dd / 'word-bank-evidence.json', {'events': [{'lesson_date': d} for d in DATES]})
    write(dd / 'word-bank-audit.json', {'events': [{'date': d} for d in DATES]})
    write(dd / 'build.json', {'build': 'x'})
    return tmp_path


PASSING = {'arabizi_gaps.cjs': (0, 'arabizi gaps on error cards: 0 words, 0 uses')}


def push(repo, run, **kw):
    lines = []
    res = G.guarded_push(repo, source='test', run=run, log=lambda *p: lines.append(' '.join(str(x) for x in p)), **kw)
    return res, lines


def test_a_failing_required_check_blocks_the_push(repo):
    run = FakeRun({**PASSING, 'accuracy_gates.py': (1, 'PROBLEM 2026-09-28: grammar.mistakes 4 != 5\naccuracy check: 1 problem(s) - do not publish')})
    res, lines = push(repo, run)
    assert res['pushed'] is False and res['outcome'] == 'blocked'
    assert not run.pushes()
    assert 'accuracy_gates' in res['reason'] and '4 != 5' in res['reason']
    assert not (repo / G.PUBLISHED).exists()                       # nothing new for the live site
    assert not [c for c in run.calls if c[:2] in (['git', 'reset'], ['git', 'revert'])]    # the local commits are kept


def test_all_checks_passing_pushes(repo):
    run = FakeRun(PASSING)
    res, lines = push(repo, run)
    assert res['pushed'] is True
    assert run.pushes() == [['git', 'push', 'origin', 'HEAD:master']]
    pub = json.loads((repo / G.PUBLISHED).read_text(encoding='utf-8'))
    assert pub['result'] == 'pass' and all(c['ok'] for c in pub['checks'] if c['required'])
    # the status file is committed BEFORE the push, so it rides along
    i_commit = next(i for i, c in enumerate(run.calls) if c[:2] == ['git', 'commit'])
    i_push = next(i for i, c in enumerate(run.calls) if c[:2] == ['git', 'push'])
    assert i_commit < i_push
    assert any('publish guard passed' in l for l in lines)


def test_a_missing_required_check_blocks(repo):
    (repo / 'scripts' / 'check_numbers.py').unlink()
    run = FakeRun(PASSING)
    res, _ = push(repo, run)
    assert res['pushed'] is False and 'check_numbers: missing: scripts/check_numbers.py' in res['reason']
    assert not run.pushes()


def test_the_block_reason_reaches_the_log_and_the_local_status_then_the_published_status(repo):
    run = FakeRun({**PASSING, 'check_numbers.py': (1, 'Word Bank 312 != Lessons 309')})
    res, lines = push(repo, run)
    line = next(l for l in lines if 'PUBLISH BLOCKED' in l)
    assert 'check_numbers' in line and '312 != Lessons 309' in line and 'live site keeps the last good version' in line
    assert '2 local commit(s) wait' in line
    st = json.loads((repo / G.STATE).read_text(encoding='utf-8'))
    assert st['last_block']['outcome'] == 'blocked' and '312 != Lessons 309' in st['last_block']['reason']
    assert st['blocks_since_last_pass'] == 1
    # next hour the numbers add up: the push goes out and the published status still shows the block Medi missed
    res2, _ = push(repo, FakeRun(PASSING))
    assert res2['pushed']
    pub = json.loads((repo / G.PUBLISHED).read_text(encoding='utf-8'))
    assert '312 != Lessons 309' in pub['last_block']['reason'] and pub['blocks_before_this_pass'] == 1
    assert json.loads((repo / G.STATE).read_text(encoding='utf-8'))['blocks_since_last_pass'] == 0


def test_an_advisory_check_only_warns(repo):
    lj = json.loads((repo / 'docs/data/lessons.json').read_text(encoding='utf-8'))
    lj['lessons'][1]['type_why'] = 'Not read yet: default until Claude reads this lesson'
    write(repo / 'docs/data/lessons.json', lj)
    res, lines = push(repo, FakeRun(PASSING))
    assert res['pushed'] is True
    assert any('publish guard warning' in l and '2026-09-28' in l for l in lines)


def test_unknown_or_empty_required_list_blocks(repo):
    cfg = json.loads((repo / G.CONFIG).read_text(encoding='utf-8'))
    cfg['required'] = cfg['required'] + ['numbers_v2']
    write(repo / G.CONFIG, cfg)
    res, _ = push(repo, FakeRun(PASSING))
    assert not res['pushed'] and 'numbers_v2: unknown check id' in res['reason']
    cfg['required'] = []
    write(repo / G.CONFIG, cfg)
    res, _ = push(repo, FakeRun(PASSING))
    assert not res['pushed'] and 'no required checks' in res['reason']


def test_an_unreadable_config_blocks(repo):
    write(repo / G.CONFIG, '{ not json')
    res, _ = push(repo, FakeRun(PASSING))
    assert not res['pushed'] and 'config' in res['reason']


def test_a_check_that_times_out_blocks(repo):
    run = FakeRun(PASSING, timeout={'accuracy_gates.py'})
    res, _ = push(repo, run)
    assert not res['pushed'] and 'accuracy_gates: timed out' in res['reason']


def test_the_time_budget_fails_closed(repo):
    cfg = json.loads((repo / G.CONFIG).read_text(encoding='utf-8'))
    cfg['total_timeout_s'] = 5
    t = iter(range(0, 1000, 3))                       # each clock read = +3 s
    res = G.run_checks(repo, config=cfg, run=FakeRun(PASSING), clock=lambda: next(t))
    assert not res['ok'] and 'budget' in res['reason']


def test_arabizi_must_print_zero(repo):
    run = FakeRun({'arabizi_gaps.cjs': (0, 'arabizi gaps on error cards: 7 words, 12 uses')})
    res, _ = push(repo, run)
    assert not res['pushed'] and 'arabizi_gaps' in res['reason']


def test_a_step_that_failed_this_run_blocks(repo):
    run = FakeRun(PASSING)
    res, _ = push(repo, run, step_failures=['build_sentence_ladder.py exit 1'])
    assert not res['pushed'] and 'build_sentence_ladder.py exit 1' in res['reason']


def test_a_rebase_conflict_aborts_and_does_not_push(repo):
    run = FakeRun(PASSING, pull_rc=1)
    res, lines = push(repo, run)
    assert res['outcome'] == 'rebase_failed' and not run.pushes()
    assert ['git', 'rebase', '--abort'] in run.calls
    assert any('PUBLISH BLOCKED' in l and 'pull --rebase failed' in l for l in lines)


def test_a_rejected_push_is_recorded(repo):
    res, lines = push(repo, FakeRun(PASSING, push_rc=1))
    assert res['outcome'] == 'push_failed'
    assert json.loads((repo / G.STATE).read_text(encoding='utf-8'))['last_block']['outcome'] == 'push_failed'


def test_broken_page_data_blocks(repo):
    write(repo / 'docs/data/grammar-console.json', '{"lessons": [')
    res, _ = push(repo, FakeRun(PASSING))
    assert not res['pushed'] and 'grammar-console.json does not parse' in res['reason']


def test_a_new_lesson_that_misses_a_page_blocks(repo):
    """09-26 once stopped at the transcript page: a lesson page exists, but the Grammar and ladder data never got it."""
    d = '2026-09-30'
    write(repo / 'docs' / 'lessons' / f'{d}.html', 'page')
    lj = json.loads((repo / 'docs/data/lessons.json').read_text(encoding='utf-8'))
    lj['lessons'].append({'date': d})
    write(repo / 'docs/data/lessons.json', lj)
    write(repo / 'docs/data/lessons' / f'{d}.json', {'turns': []})
    res, _ = push(repo, FakeRun(PASSING))
    assert not res['pushed']
    for page in ('sentence-ladder.json', 'grammar-console.json', 'grammar-usage.json', 'accuracy-release.json',
                 'word-bank-evidence.json', 'word-bank-audit.json', f'sentence-ladder/{d}.json', 'lesson audio'):
        assert page in res['reason'], page


def test_uncommitted_published_files_block(repo):
    res, _ = push(repo, FakeRun(PASSING, dirty=' M docs/data/lessons.json\n?? docs/lessons/2026-09-30.html\n'))
    assert not res['pushed'] and 'uncommitted' in res['reason'] and 'docs/data/lessons.json' in res['reason']


def test_pre_push_hook(repo, monkeypatch):
    run = FakeRun(PASSING)
    head = 'a' * 40
    other = 'b' * 40
    monkeypatch.delenv(G.OK_ENV, raising=False)
    assert G.hook([f'refs/heads/x {other} refs/heads/feature {"0" * 40}'], repo, run=run, log=lambda *a: None) == 0
    assert G.hook([f'refs/heads/x {other} refs/heads/master {"0" * 40}'], repo, run=run, log=lambda *a: None) == 1
    assert G.hook([f'refs/heads/hourly {head} refs/heads/master {"0" * 40}'], repo, run=run, log=lambda *a: None) == 0
    bad = FakeRun({**PASSING, 'accuracy_gates.py': (1, 'x')})
    assert G.hook([f'refs/heads/hourly {head} refs/heads/master {"0" * 40}'], repo, run=bad, log=lambda *a: None) == 1
    monkeypatch.setenv(G.OK_ENV, other)                # the guard's own push of a commit it just checked
    assert G.hook([f'refs/heads/x {other} refs/heads/master {"0" * 40}'], repo, run=bad, log=lambda *a: None) == 0


def test_no_script_pushes_around_the_guard():
    """Every `git push` in scripts/ is publish_guard's own. Pages builds master:/docs, so any other push publishes unchecked."""
    offenders = []
    for p in sorted((ROOT / 'scripts').glob('*.py')):
        if p.name == 'publish_guard.py':
            continue
        for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            code = line.split('#')[0]
            if re.search(r"""['"]push['"]|['"]git\s+push\s+(-|origin|HEAD)""", code):
                offenders.append(f'{p.name}:{i}: {line.strip()[:100]}')
    for p in sorted((ROOT / 'scripts').glob('*.ps1')):
        for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if re.search(r'git(\.exe)?\s+(-C\s+\S+\s+)?push', line.split('#')[0]):
                offenders.append(f'{p.name}:{i}: {line.strip()[:100]}')
    assert offenders == []


def test_the_live_config_carries_decision_7():
    cfg = json.loads((ROOT / G.CONFIG).read_text(encoding='utf-8'))
    for must in ('accuracy_gates', 'check_numbers', 'check_rules', 'check_pages', 'arabizi_gaps', 'json_data', 'lesson_coverage', 'review_done', 'tests_py', 'tests_node',
                 'step_failures', 'clean_tree'):
        assert must in cfg['required'], must
    assert cfg['total_timeout_s'] <= 300
    tests = [a for spec in cfg['commands'].values() for a in spec['cmd'] if a.startswith('tests/')]
    for live_db in ('test_m4_after', 'test_m5_cards'):          # they write into Medi's live database
        assert not [t for t in tests if live_db in t]
    for cid, spec in cfg['commands'].items():
        for a in spec['cmd']:
            if a.startswith('tests/'):
                assert (ROOT / a).exists(), f'{cid}: {a} missing'
