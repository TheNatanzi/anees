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


def test_real_git_a_block_leaves_the_remote_untouched_and_a_pass_publishes(tmp_path):
    """End to end with real git (a local bare repo stands in for GitHub): blocked = master keeps the last good commit and
    the local commit waits; the next passing run publishes both, with the last block in docs/data/publish-guard.json."""
    import shutil
    if not shutil.which('git'):
        pytest.skip('git not on PATH')
    g = lambda cwd, *a: subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    remote, work = tmp_path / 'remote.git', tmp_path / 'work'
    g(tmp_path, 'init', '-q', '--bare', '-b', 'master', str(remote))
    g(tmp_path, 'clone', '-q', str(remote), str(work))
    for k, v in (('user.email', 't@example.com'), ('user.name', 'test'), ('core.hooksPath', 'no-hooks')):
        g(work, 'config', k, v)
    write(work / G.CONFIG, {'required': ['json_data', 'numbers'], 'advisory': [], 'total_timeout_s': 60,
                            'commands': {'numbers': {'cmd': ['{python}', 'scripts/numbers.py'], 'timeout_s': 30}}})
    write(work / 'scripts' / 'numbers.py', "import pathlib, sys\nok = pathlib.Path('ok.flag').exists()\n"
                                           "print('numbers add up' if ok else 'Word Bank 312 != Lessons 309')\nsys.exit(0 if ok else 1)\n")
    write(work / '.gitignore', 'ok.flag\ndata/publish-guard/\n')
    write(work / 'docs' / 'data' / 'lessons.json', {'lessons': []})
    g(work, 'add', '-A'); g(work, 'commit', '-q', '-m', 'last good'); g(work, 'push', '-q', 'origin', 'HEAD:master')
    good = g(remote, 'rev-parse', 'master')
    write(work / 'docs' / 'data' / 'lessons.json', {'lessons': [{'date': '2026-09-30'}]})
    g(work, 'add', '-A'); g(work, 'commit', '-q', '-m', 'lesson 2026-09-30')
    lines = []
    res = G.guarded_push(work, source='hourly: lessons 2026-09-30', log=lambda *p: lines.append(' '.join(map(str, p))))
    assert res['outcome'] == 'blocked' and '312 != Lessons 309' in res['reason']
    assert g(remote, 'rev-parse', 'master') == good                                  # the live site keeps the last good version
    assert g(work, 'rev-list', '--count', 'origin/master..HEAD') == '1'              # the lesson commit waits, not lost
    assert any('PUBLISH BLOCKED' in l and '1 local commit(s) wait' in l for l in lines)
    (work / 'ok.flag').write_text('', encoding='utf-8')
    res = G.guarded_push(work, source='hourly: 1 local commit(s)', log=lambda *p: None)
    assert res['pushed']
    assert g(remote, 'rev-parse', 'master') == g(work, 'rev-parse', 'HEAD')
    pub = json.loads(g(remote, 'show', 'master:docs/data/publish-guard.json'))
    assert pub['result'] == 'pass' and '312 != Lessons 309' in pub['last_block']['reason']
    assert json.loads(g(remote, 'show', 'master:docs/data/lessons.json'))['lessons'] == [{'date': '2026-09-30'}]


def test_short_reason_names_the_failing_test():
    """Eng audit 2026-09-29: a node failure used to read "operator: '==', | diff: 'simple' | }"; it must name the test."""
    import publish_guard as G
    out = ("\u2716 golden: Amal's 25 (0.9ms)\n\u2139 fail 1\n\u2716 failing tests:\n\n\u2716 golden: Amal's 25 (0.9ms)\n  AssertionError\n"
           "      at async startSubtestAfterBootstrap {\n    code: 'ERR_ASSERTION',\n    operator: '==',\n    diff: 'simple'\n  }")
    r = G._short(out)
    assert "golden: Amal's 25" in r and "operator" not in r


# ---------------------------------------------------------------- generated files are rebuilt, never merged (2026-10-02)

def _two_clones(tmp_path, required=('json_data',)):
    """A bare 'GitHub' + the hourly clone (work) + another writer (other). Returns (g, remote, work, other)."""
    import shutil
    if not shutil.which('git'):
        pytest.skip('git not on PATH')
    g = lambda cwd, *a: subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    remote, work, other = tmp_path / 'remote.git', tmp_path / 'work', tmp_path / 'other'
    g(tmp_path, 'init', '-q', '--bare', '-b', 'master', str(remote))
    g(tmp_path, 'clone', '-q', str(remote), str(work))
    for k, v in (('user.email', 't@example.com'), ('user.name', 'test'), ('core.hooksPath', 'no-hooks')):
        g(work, 'config', k, v)
    write(work / G.CONFIG, {'required': list(required), 'advisory': [], 'total_timeout_s': 60, 'commands': {}})
    write(work / 'scripts' / 'write_build.py', (ROOT / 'scripts' / 'write_build.py').read_text(encoding='utf-8'))
    write(work / 'scripts' / 'tool.py', 'x = 1\n')
    write(work / '.gitignore', 'data/publish-guard/\n')
    write(work / 'data' / 'runs' / '.gitattributes', '*.jsonl merge=union\n')
    write(work / 'docs' / 'data' / 'lessons.json', {'lessons': []})
    write(work / 'docs' / 'data' / 'build.json', {'build': 'start'})
    write(work / 'docs' / 'data' / 'tutor.json', {'updated': 'start'})
    write(work / 'data' / 'runs' / '2026-10.jsonl', '{"id": 1}\n')
    g(work, 'add', '-A'); g(work, 'commit', '-q', '-m', 'start'); g(work, 'push', '-q', 'origin', 'HEAD:master')
    g(tmp_path, 'clone', '-q', str(remote), str(other))
    for k, v in (('user.email', 'o@example.com'), ('user.name', 'other'), ('core.hooksPath', 'no-hooks')):
        g(other, 'config', k, v)
    return g, remote, work, other


def test_real_git_a_build_stamp_conflict_no_longer_stops_publishing(tmp_path):
    """Rule PR-13 (RULES.md S7 G1). 2026-09-30 17:23 -> 2026-10-02: every hourly push stopped at 'a person merges' over two build stamps (69 commits
    stuck). A stamp conflict is now resolved (master's copy, then re-stamped) and the push goes through."""
    g, remote, work, other = _two_clones(tmp_path)
    write(other / 'docs' / 'data' / 'build.json', {'build': 'master-stamp'})
    write(other / 'data' / 'runs' / '2026-10.jsonl', '{"id": 1}\n{"id": "master"}\n')
    g(other, 'commit', '-qam', 'master moved'); g(other, 'push', '-q', 'origin', 'HEAD:master')
    write(work / 'docs' / 'data' / 'build.json', {'build': 'hourly-stamp'})
    write(work / 'data' / 'runs' / '2026-10.jsonl', '{"id": 1}\n{"id": "hourly"}\n')
    write(work / 'docs' / 'data' / 'lessons.json', {'lessons': [{'date': '2026-10-01'}]})
    g(work, 'commit', '-qam', 'hourly lesson')
    lines = []
    res = G.guarded_push(work, source='hourly', log=lambda *p: lines.append(' '.join(map(str, p))))
    assert res['pushed'], res
    assert json.loads(g(remote, 'show', 'master:docs/data/lessons.json'))['lessons'] == [{'date': '2026-10-01'}]
    stamp = json.loads(g(remote, 'show', 'master:docs/data/build.json'))['build']
    assert stamp not in ('master-stamp', 'hourly-stamp')                        # re-stamped after the rebase
    runs = g(remote, 'show', 'master:data/runs/2026-10.jsonl')
    assert '"master"' in runs and '"hourly"' in runs                            # append-only log keeps both sides
    assert 'tutor' not in G.open_failures(work)                                 # a stamp needs no rebuild
    assert any("kept master's copy" in l for l in lines)


def test_real_git_a_generated_data_conflict_keeps_master_and_queues_the_rebuild(tmp_path):
    g, remote, work, other = _two_clones(tmp_path, required=('step_failures', 'json_data'))
    write(other / 'docs' / 'data' / 'tutor.json', {'updated': 'master'})
    g(other, 'commit', '-qam', 'master rebuilt the Tutor page'); g(other, 'push', '-q', 'origin', 'HEAD:master')
    write(work / 'docs' / 'data' / 'tutor.json', {'updated': 'hourly'})
    g(work, 'commit', '-qam', 'hourly rebuilt the Tutor page')
    res = G.guarded_push(work, source='hourly', log=lambda *p: None)
    assert res['outcome'] == 'blocked' and 'rebuild pending' in res['reason']   # not "a person merges"
    assert 'tutor' in G.open_failures(work)                                     # the next hourly run rebuilds it
    assert not G._rebasing(work, subprocess.run)
    assert json.loads((work / 'docs' / 'data' / 'tutor.json').read_text(encoding='utf-8'))['updated'] == 'master'
    subprocess.run(['git', 'merge-base', '--is-ancestor', 'origin/master', 'HEAD'], cwd=work, check=True)   # rebased


def test_real_git_a_hand_made_conflict_still_stops_for_a_person(tmp_path):
    g, remote, work, other = _two_clones(tmp_path)
    write(other / 'scripts' / 'tool.py', 'x = 2\n')
    g(other, 'commit', '-qam', 'master edit'); g(other, 'push', '-q', 'origin', 'HEAD:master')
    write(work / 'scripts' / 'tool.py', 'x = 3\n')
    g(work, 'commit', '-qam', 'local edit')
    head = g(work, 'rev-parse', 'HEAD')
    res = G.guarded_push(work, source='hourly', log=lambda *p: None)
    assert res['outcome'] == 'rebase_failed' and 'scripts/tool.py' in res['reason']
    assert g(work, 'rev-parse', 'HEAD') == head and not G._rebasing(work, subprocess.run)   # aborted, nothing lost


def test_generated_paths_cover_the_stamp_and_never_code():
    for p in ('docs/data/build.json', 'docs/js/build.js', 'docs/data/lessons/2026-10-01.json', 'docs/data/tutor.json',
              'data/accuracy/verification-queue.json', 'data/runs/2026-10.jsonl', 'docs/lessons/2026-09-23/clips/gc-1.mp3'):
        assert G.is_generated(p), p
    for p in ('scripts/publish_guard.py', 'docs/js/app.js', 'docs/progress.html', 'RULES.md',
              'data/lesson-work/full-audit/2026-10-01.r1.json'):
        assert not G.is_generated(p), p


def test_data_freshness_names_a_transcribed_lesson_that_is_not_on_the_site(repo, tmp_path):
    """Rule PG-15 (RULES.md S7 F1). Rule F1 (2026-10-02): 10-01 sat transcribed in the raw archive 11+ hours while every page ended at 09-30."""
    raw = tmp_path / 'raw'
    write(raw / '2026-10-01' / 'scribe_Medi.json', '{}')
    write(raw / DATES[0] / 'scribe_Medi.json', '{}')                       # on the site: fine
    write(raw / '2026-09-01' / 'scribe.json', '{}')                          # before automatic loading: ignored
    import datetime as dt
    now = dt.datetime.now().astimezone()
    write(repo / 'data' / 'amal-trigger' / 'state.json', {'checked': now.isoformat()})
    ok, detail = G.check_data_freshness(repo, raw=raw, now=now)
    assert not ok and 'lesson 2026-10-01 transcribed' in detail and DATES[0] not in detail and '2026-09-01' not in detail


def test_data_freshness_names_a_silent_amal_trigger_and_a_long_publish_block(repo, tmp_path):
    import datetime as dt
    now = dt.datetime.now().astimezone()
    write(repo / 'data' / 'amal-trigger' / 'state.json', {'checked': (now - dt.timedelta(hours=35)).isoformat()})
    old = (now - dt.timedelta(hours=32)).isoformat()
    write(repo / G.STATE, {'blocks_since_last_pass': 35, 'last_block': {'reason': 'pull --rebase failed'},
                           'history': [{'at': old, 'outcome': 'rebase_failed'}]})
    ok, detail = G.check_data_freshness(repo, raw=tmp_path / 'none', now=now)
    assert not ok and "last checked 35 h ago" in detail and 'nothing published for 32 h' in detail


def test_data_freshness_passes_when_current_and_is_advisory(repo, tmp_path):
    import datetime as dt
    now = dt.datetime.now().astimezone()
    write(repo / 'data' / 'amal-trigger' / 'state.json', {'checked': now.isoformat()})
    write(tmp_path / 'doc' / 'amal-vocab-doc.md', '# words')
    write(tmp_path / 'doc' / 'amal-vocab-doc.status.json', {'ok_at': now.isoformat()})
    assert G.check_data_freshness(repo, raw=tmp_path / 'none', now=now, doc_dir=tmp_path / 'doc')[0]
    cfg = json.loads((ROOT / G.CONFIG).read_text(encoding='utf-8'))
    assert 'data_freshness' in cfg['advisory'] and 'data_freshness' not in cfg['required']   # a stale source never blocks a fresh publish


def test_ls_01_lesson_type_read_is_required_and_blocks_a_default_type(repo):
    """LS-01 (Medi 2026-10-02 "This was clearly a grammar review for 'el' im shocked you didnt detect that"): the live
    config makes lesson_type_read REQUIRED, and a lesson still showing the builder's default type blocks the push."""
    live = json.loads((ROOT / G.CONFIG).read_text(encoding='utf-8'))
    assert 'lesson_type_read' in live['required'] and 'lesson_type_read' not in live.get('advisory', [])
    cfg = json.loads((repo / G.CONFIG).read_text(encoding='utf-8'))
    cfg['required'].append('lesson_type_read')
    cfg['advisory'] = []
    write(repo / G.CONFIG, cfg)
    lj = json.loads((repo / 'docs/data/lessons.json').read_text(encoding='utf-8'))
    for x in lj['lessons']:
        x['type'] = 'review-grammar'
    lj['lessons'][1].update(type='free-speak', type_why='Not read yet: default until the same-day reader reads this lesson.')
    write(repo / 'docs/data/lessons.json', lj)
    run = FakeRun(PASSING)
    res, _ = push(repo, run)
    assert res['pushed'] is False and 'lesson_type_read' in res['reason'] and '2026-09-28' in res['reason']
    assert not run.pushes()
    lj['lessons'][1].update(type='grammar', type_why='16:52 she says we review el')     # not one of the five types
    write(repo / 'docs/data/lessons.json', lj)
    assert G.check_lesson_type_read(repo)[0] is False
    lj['lessons'][1].update(type='review-grammar')
    write(repo / 'docs/data/lessons.json', lj)
    assert G.check_lesson_type_read(repo)[0] is True


def test_AM_20_a_stale_amal_doc_export_warns_in_data_freshness(repo, tmp_path):
    """AM-20 (Medi 2026-10-02 "DUDE FUCKING FIX THE ISSUE WITH HER DOCUMENT"): the hourly Doc export older than 2 h is a
    data_freshness warning with its time and reason; a missing export says so too."""
    import datetime as dt
    now = dt.datetime.now().astimezone()
    write(repo / 'data' / 'amal-trigger' / 'state.json', {'checked': now.isoformat()})
    write(tmp_path / 'doc' / 'amal-vocab-doc.md', '# words')
    write(tmp_path / 'doc' / 'amal-vocab-doc.status.json', {'ok_at': (now - dt.timedelta(hours=5)).isoformat(),
                                                           'tried_at': now.isoformat(), 'error': 'export HTTP 403'})
    ok, detail = G.check_data_freshness(repo, raw=tmp_path / 'none', now=now, doc_dir=tmp_path / 'doc')
    assert not ok and "Amal's word Doc not synced since" in detail and 'export HTTP 403' in detail
    ok, detail = G.check_data_freshness(repo, raw=tmp_path / 'none', now=now, doc_dir=tmp_path / 'empty')
    assert not ok and "Amal's word Doc not synced on this PC" in detail


# ---------------------------------------------------------------- the silent-stall system (overnight brief 2026-10-10 §3)
# Medi 2026-10-10: "MAKE A SYSTEM" - the hourly job sat blocked for ~29 h on a data/budget.json rebase conflict, unseen.

def test_budget_json_is_a_generated_file_rebuilt_inline():
    assert G.is_generated('data/budget.json')
    assert 'data/budget.json' in G.regenerate_rules()['rebuild_inline']


def _run_line(step, provider, usd, started, run_id):
    return json.dumps({'schema': 1, 'run_id': run_id, 'step': step, 'gen_ai.provider.name': provider, 'cost_usd': usd,
                       'started_at': started, 'status': 'ok'})


def test_budget_rebuild_recomputes_the_totals_from_the_run_log():
    import budget_rebuild as B
    base = {'elevenlabs': 1.0, 'openai': 0.0, 'gemini': 9.99, 'anthropic': 0.0,   # a wrong gemini total: recomputed
            'calls': [{'t': '2026-10-09T10:00:00', 'service': 'gemini', 'usd': 0.5, 'what': 'context listen'},
                      {'t': '2026-09-05T01:29:22', 'service': 'elevenlabs', 'usd': 1.0, 'what': 'before the run log'}]}
    runs = [json.loads(_run_line('context.listen', 'google', 0.5, '2026-10-09T17:00:01Z', 'a1')),         # = the ledger call
            json.loads(_run_line('context.listen', 'google', 0.25, '2026-10-10T17:00:00Z', 'b2')),        # missing: added
            json.loads(_run_line('correction_parse.read_note', 'anthropic', 0.3, '2026-10-10T18:00:00Z', 'c3')),
            json.loads(_run_line('full_audit.reader', 'anthropic', 2.0, '2026-10-10T18:00:00Z', 'd4')),   # CLI reader: not a ledger call
            json.loads(_run_line('scribe.transcribe', 'elevenlabs', 0, '2026-10-10T18:00:00Z', 'e5'))]    # free: nothing
    out = B.rebuild(base, runs)
    assert len(out['calls']) == 4
    assert out['gemini'] == 0.75 and out['anthropic'] == 0.3 and out['elevenlabs'] == 1.0 and out['openai'] == 0.0
    assert any('b2' in c['what'] for c in out['calls'])
    assert B.rebuild(out, runs) == out                                         # idempotent
    # Codex review 2026-10-11: a call of ANOTHER service with the same cost and time never stands in for a run line
    other = B.rebuild({'calls': [{'t': '2026-10-10T10:00:00', 'service': 'elevenlabs', 'usd': 0.4, 'what': 'scribe'}]},
                      [json.loads(_run_line('context.listen', 'google', 0.4, '2026-10-10T17:00:00Z', 'f6'))])
    assert other['gemini'] == 0.4 and other['elevenlabs'] == 0.4 and len(other['calls']) == 2


def test_real_git_a_budget_json_conflict_keeps_master_and_rebuilds_from_the_run_logs(tmp_path, monkeypatch):
    """PR-24 (G1): 2026-10-09 11:34 -> 10-11: 'conflict in a hand-made file (a person merges): data/budget.json' on every hourly push.
    Now master's copy is kept, the ledger is rebuilt from the run logs (both sides' lines, union-merged) and it publishes."""
    monkeypatch.setenv('ANEES_HOURLY_ROOT', str(tmp_path / 'no-hourly'))
    monkeypatch.setenv('ANEES_RAW', str(tmp_path / 'no-raw'))
    g, remote, work, other = _two_clones(tmp_path, required=('step_failures', 'json_data'))
    base = {'elevenlabs': 0.0, 'openai': 0.0, 'gemini': 0.0, 'anthropic': 0.0, 'calls': []}
    write(work / 'data' / 'budget.json', base)
    g(work, 'add', '-A'); g(work, 'commit', '-qm', 'ledger'); g(work, 'push', '-q', 'origin', 'HEAD:master'); g(other, 'pull', '-q')
    m = {'t': '2026-10-10T09:00:00', 'service': 'anthropic', 'usd': 0.26, 'what': 'parse-correction note (master)'}
    write(other / 'data' / 'budget.json', {**base, 'anthropic': 0.26, 'calls': [m]})
    write(other / 'data' / 'runs' / '2026-10.jsonl', '{"id": 1}\n' + _run_line('correction_parse.read_note', 'anthropic', 0.26, '2026-10-10T16:00:00Z', 'mmmm') + '\n')
    g(other, 'commit', '-qam', 'master spent'); g(other, 'push', '-q', 'origin', 'HEAD:master')
    h = {'t': '2026-10-10T10:00:00', 'service': 'gemini', 'usd': 0.4, 'what': 'second listen (hourly)'}
    write(work / 'data' / 'budget.json', {**base, 'gemini': 0.4, 'calls': [h]})
    write(work / 'data' / 'runs' / '2026-10.jsonl', '{"id": 1}\n' + _run_line('context.listen', 'google', 0.4, '2026-10-10T17:00:00Z', 'hhhh') + '\n')
    g(work, 'commit', '-qam', 'hourly spent')
    lines = []
    res = G.guarded_push(work, source='hourly', log=lambda *p: lines.append(' '.join(map(str, p))))
    assert res['pushed'], res                                                  # not "a person merges"
    led = json.loads(g(remote, 'show', 'master:data/budget.json'))
    assert sorted(c['usd'] for c in led['calls']) == [0.26, 0.4]               # master's call kept, the hourly's rebuilt from its run line
    assert led['anthropic'] == 0.26 and led['gemini'] == 0.4
    assert 'tutor' not in G.open_failures(work)                                # rebuilt inline: no hourly rebuild queued
    health = json.loads(g(remote, 'show', 'master:docs/data/pipeline-health.json'))
    assert health['stalled'] is False and health['last_publish_utc']           # an hourly pass is a publish


def _stall_state(hours, reason='pull --rebase failed: conflict in a hand-made file (a person merges): data/budget.json'):
    import datetime as dt
    now = dt.datetime(2026, 10, 11, 7, 0, tzinfo=dt.timezone.utc)
    last = now - dt.timedelta(hours=hours)
    st = {'history': [{'at': (last + dt.timedelta(minutes=10)).isoformat(), 'outcome': 'rebase_failed', 'reason': reason},
                      {'at': (last - dt.timedelta(hours=1)).isoformat(), 'outcome': 'blocked', 'reason': 'older, fixed'}],
          'open_failures': {}}
    return now, last, st


def _log_run(*entries):
    out = '\n'.join(sha + '\x1f' + t.isoformat() + '\x1f' + subj for sha, t, subj in entries)
    return lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, out, '')


def test_stall_is_computed_from_the_last_hourly_publish_and_pending_work(tmp_path):
    import datetime as dt
    import pipeline_health as PH
    import lesson_alerts as A
    now, last, st = _stall_state(29)
    hourly = tmp_path / 'hourly'
    write(hourly / 'data' / 'publish-guard' / 'state.json', st)
    root = tmp_path / 'repo'
    write(root / 'docs' / 'data' / 'lessons.json', {'lessons': [{'date': '2026-10-09'}]})
    run = _log_run(('f' * 40, last + dt.timedelta(hours=1), "Lesson 2026-10-09: English lines, the hourly job's leftover data"),   # manual
                   ('a' * 40, last, 'Publish guard: all required checks passed (hourly: tutor refresh)'))
    h = PH.compute(root, run=run, now=now, hourly_root=hourly, raw=tmp_path / 'raw', prev={})
    assert h['last_publish_sha'] == 'a' * 40 and h['hours_since_publish'] == 29.0
    assert h['stalled'] is True and 'budget.json' in h['first_block_reason'] and h['blocked_since_utc']
    assert '1 blocked push(es) since the last publish' in h['pending']        # the older, fixed block is not counted
    w = PH.warning_line(h)
    assert w.startswith('WARNING: the hourly robot has not published for 29 h: ') and 'budget.json' in w
    p = PH.alert_problem(h)                                                     # the LS-04 line on Progress + Lessons
    assert A.line_for(p).startswith('The hourly robot has not published since {since}: ') and p['since'] == h['last_publish_utc']
    # 1 h since the last publish: not stalled, whatever waits
    now2, last2, _ = _stall_state(1)
    h2 = PH.compute(root, run=_log_run(('b' * 40, last2, 'Publish guard: all required checks passed (hourly: x)')), now=now2,
                    hourly_root=hourly, raw=tmp_path / 'raw', prev={})
    assert h2['stalled'] is False and PH.warning_line(h2) is None
    # 29 h but nothing waits (no lesson today, no block, no failure, nothing pending): not stalled
    write(hourly / 'data' / 'publish-guard' / 'state.json', {'history': [], 'open_failures': {}})
    h3 = PH.compute(root, run=run, now=now, hourly_root=hourly, raw=tmp_path / 'raw', prev={})
    assert h3['pending'] == [] and h3['stalled'] is False
    # a lesson today is pending work on its own
    write(root / 'docs' / 'data' / 'lessons.json', {'lessons': [{'date': now.astimezone().date().isoformat()}]})
    assert PH.compute(root, run=run, now=now, hourly_root=hourly, raw=tmp_path / 'raw', prev={})['stalled'] is True


def test_guard_check_and_push_print_the_stall_warning_and_never_block_on_it(repo, monkeypatch, capsys):
    import pipeline_health as PH
    stalled = {'stalled': True, 'hours_since_publish': 29.4, 'first_block_reason': 'conflict in a hand-made file: data/budget.json',
               'last_publish_utc': '2026-10-09T18:16:25Z', 'pending': ['x']}
    monkeypatch.setattr(PH, 'compute', lambda *a, **k: dict(stalled))
    real_checks = G.run_checks
    monkeypatch.setattr(G, 'run_checks', lambda *a, **k: {'ok': True, 'at': G.now_iso(), 'sha': 'a' * 40, 'checks': [], 'reason': '', 'warnings': []})
    assert G.main(['check', '--root', str(repo)]) == 0                         # advisory: the exit code is the checks' own
    out = capsys.readouterr().out
    assert 'WARNING: the hourly robot has not published for 29 h: conflict in a hand-made file: data/budget.json' in out
    monkeypatch.setattr(G, 'run_checks', real_checks)
    res, lines = push(repo, FakeRun({**PASSING, 'check_numbers.py': (1, 'Word Bank 312 != Lessons 309')}))
    assert res['outcome'] == 'blocked'
    assert any(l.startswith('WARNING: the hourly robot has not published for 29 h') for l in lines)
    assert json.loads((repo / G.HEALTH).read_text(encoding='utf-8'))['stalled'] is True   # a block rewrites the health file
    ok, _ = G.check_clean_tree(repo, {'clean_paths': ['docs']}, FakeRun(dirty=' M docs/data/pipeline-health.json\n'))
    assert ok                                                                   # it never makes the tree "dirty" for the next check
