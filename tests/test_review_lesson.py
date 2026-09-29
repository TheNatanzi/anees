# -*- coding: utf-8 -*-
"""review_lesson.py (same-day review) must fail CLOSED (engineering audit 2026-09-29, area 4):
- reader files are reused only while their inputs (transcript, briefs, rules, vocabulary) are unchanged - 09-23 and 09-26
  grew by 266 / 149 transcript lines (Meet gap fill) AFTER their readers ran and were never re-read;
- a page builder that fails stops the push and makes the run exit non-zero;
- the push goes through the publish guard, never straight to master.
Offline: claude, the builders and git are replaced by fakes; nothing touches the real repo."""
import hashlib, json, os, subprocess, sys, types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import review_lesson as RL
import full_audit_prep as P

D = '2026-09-30'


def turns(n):
    return [{'t': 10.0 * i, 'end': 10.0 * i + 5, 'who': 'Medi' if i % 2 else 'Amal', 'text': f'jumla {i}'} for i in range(n)]


def fresh_text(n):
    lines = [f"# Lesson {D} - {n} turns on the lesson clock (mm:ss = seconds on the page audio)", ""]
    for t in turns(n):
        lines.append(f"[{P.mmss(t['t'])}] {t['who']}: {t['text']}")
    return "\n".join(lines) + "\n"


class Fake:
    """Stands in for claude, the builders (py) and subprocess.run."""
    def __init__(self, fail_builders=(), gaps=0):
        self.claude_calls, self.py_calls, self.cmds, self.fail_builders, self.gaps = [], [], [], set(fail_builders), gaps

    def claude(self, prompt, label, **kw):
        self.claude_calls.append(label)
        for out in kw.get('outputs') or []:
            if out.endswith(('.r1.json', '.r2.json', '.r3.json')):
                Path(out).write_text(json.dumps({'date': D, 'reader': label.split()[-1], 'rows': []}), encoding='utf-8')

    def py(self, *args, check=True):
        name = os.path.basename(args[0])
        self.py_calls.append((name,) + tuple(args[1:]))
        rc = 1 if name in self.fail_builders else 0
        if name == 'full_audit_compare.py' and args[1] == 'settle':
            Path(RL.WORK, f'{D}.settled.json').write_text(json.dumps({'counts': {'final': 0, 'agreement_pct': 100.0}}), encoding='utf-8')
        if check and rc:
            raise subprocess.CalledProcessError(rc, args)
        return subprocess.CompletedProcess(args, rc, '', '')

    def run(self, cmd, *a, **k):
        self.cmds.append([str(c) for c in cmd])
        if any('arabizi_gaps' in str(c) for c in cmd):
            return subprocess.CompletedProcess(cmd, 1 if self.gaps else 0, f'arabizi gaps on error cards: {self.gaps} words, 0 uses', '')
        return subprocess.CompletedProcess(cmd, 0, '', '')


@pytest.fixture
def repo(tmp_path, monkeypatch):
    work = tmp_path / 'data' / 'lesson-work' / 'full-audit'
    work.mkdir(parents=True)
    (tmp_path / 'docs' / 'data' / 'lessons').mkdir(parents=True)
    (tmp_path / 'docs' / 'lessons').mkdir(parents=True)
    (tmp_path / 'docs' / 'lessons' / f'{D}.html').write_text('x', encoding='utf-8')
    (tmp_path / 'docs' / 'data' / 'lessons' / f'{D}.json').write_text(json.dumps({'turns': turns(12)}), encoding='utf-8')
    (tmp_path / 'docs' / 'data' / 'words.json').write_text(json.dumps({'items': [{'key': 'k', 'english': 'car', 'arabizi': 'sayyara', 'arabic': 'سيارة'}]}), encoding='utf-8')
    (tmp_path / 'docs' / 'data' / 'grammar-buckets.json').write_text(json.dumps({'families': {'B': 'verbs'}, 'buckets': [{'id': 'B1', 'name': 'x'}]}), encoding='utf-8')
    (tmp_path / 'docs' / 'data' / 'names.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'RULES.md').write_text('rules', encoding='utf-8')
    (tmp_path / 'data' / 'full-audit-2026-09-26.json').write_text(json.dumps({'rows': []}), encoding='utf-8')
    for b in ('READER-BRIEF.md', 'THIRD-READER-BRIEF.md', 'PATTERN-BRIEF.md'):
        (work / b).write_text(b, encoding='utf-8')
    monkeypatch.setattr(RL, 'REPO', str(tmp_path))
    monkeypatch.setattr(RL, 'WORK', str(work))
    monkeypatch.setattr(RL, 'LOG', str(work / 'review_lesson.log'))
    monkeypatch.setattr(RL, 'names_note', lambda date: '')
    monkeypatch.setattr(P, 'REPO', str(tmp_path), raising=False)
    monkeypatch.setattr(P, 'OUT', str(work), raising=False)
    return tmp_path


def install(monkeypatch, fake, pushes):
    monkeypatch.setattr(RL, 'claude', fake.claude)
    monkeypatch.setattr(RL, 'py', fake.py)
    monkeypatch.setattr(RL.subprocess, 'run', fake.run)
    import publish_guard
    monkeypatch.setattr(publish_guard, 'guarded_push', lambda *a, **k: pushes.append(k.get('source')) or {'pushed': True, 'outcome': 'pushed', 'reason': ''})


def old_readers(work, text):
    """Reader files from an earlier run: they read `text`."""
    (work / f'{D}.txt').write_text(text, encoding='utf-8')
    for r in ('r1', 'r2', 'r3'):
        (work / f'{D}.{r}.json').write_text(json.dumps({'date': D, 'reader': r, 'rows': [{'uid': 'old'}]}), encoding='utf-8')


def git_pushes(fake):
    return [c for c in fake.cmds if c[:2] == ['git', 'push']]


def test_readers_rerun_when_the_transcript_grew_after_they_read_it(repo, monkeypatch):
    """09-23 / 09-26: the gap fill added lines after the readers ran; reuse-by-existence kept the old readers."""
    work = Path(RL.WORK)
    old_readers(work, fresh_text(8))                  # they read 8 turns; the page now has 12
    fake, pushes = Fake(), []
    install(monkeypatch, fake, pushes)
    rc = _run_main(monkeypatch, [D, '--no-push'])
    assert sorted(fake.claude_calls)[:3] == sorted([f'{D} r1', f'{D} r2', f'{D} r3'])
    assert rc == 0


def test_unchanged_legacy_readers_are_adopted_not_rerun(repo, monkeypatch):
    work = Path(RL.WORK)
    old_readers(work, fresh_text(12))                 # read exactly what the page shows now
    fake, pushes = Fake(), []
    install(monkeypatch, fake, pushes)
    rc = _run_main(monkeypatch, [D, '--no-push'])
    assert not [c for c in fake.claude_calls if c.endswith(('r1', 'r2', 'r3'))]
    assert rc == 0
    # adopted: from now on the manifest pins what they read
    assert (work / f'{D}.r1.json.inputs.json').exists()


def test_reader_rerun_when_the_reader_brief_changes(repo, monkeypatch):
    work = Path(RL.WORK)
    old_readers(work, fresh_text(12))
    fake, pushes = Fake(), []
    install(monkeypatch, fake, pushes)
    assert _run_main(monkeypatch, [D, '--no-push']) == 0          # adopt
    (work / 'READER-BRIEF.md').write_text('a new rule for readers', encoding='utf-8')
    fake2 = Fake(); install(monkeypatch, fake2, pushes)
    assert _run_main(monkeypatch, [D, '--no-push']) == 0
    assert {f'{D} r1', f'{D} r2'} <= set(fake2.claude_calls)


def test_a_failing_page_builder_stops_the_push_and_fails_the_run(repo, monkeypatch):
    work = Path(RL.WORK)
    old_readers(work, fresh_text(12))
    fake, pushes = Fake(fail_builders={'build_grammar_console.py'}), []
    install(monkeypatch, fake, pushes)
    rc = _run_main(monkeypatch, [D])
    assert rc != 0
    assert not pushes and not git_pushes(fake)


def test_arabizi_gaps_left_stop_the_push(repo, monkeypatch):
    work = Path(RL.WORK)
    old_readers(work, fresh_text(12))
    fake, pushes = Fake(gaps=3), []
    install(monkeypatch, fake, pushes)
    rc = _run_main(monkeypatch, [D])
    assert rc != 0
    assert not pushes and not git_pushes(fake)


def test_the_push_goes_through_the_publish_guard(repo, monkeypatch):
    work = Path(RL.WORK)
    old_readers(work, fresh_text(12))
    fake, pushes = Fake(), []
    install(monkeypatch, fake, pushes)
    assert _run_main(monkeypatch, [D]) == 0
    assert not git_pushes(fake)                       # never a bare `git push`
    assert pushes == [f'review_lesson {D}']


def test_a_reader_file_that_is_not_valid_json_fails_closed(repo, monkeypatch):
    work = Path(RL.WORK)
    (work / f'{D}.txt').write_text(fresh_text(12), encoding='utf-8')
    fake, pushes = Fake(), []

    def bad_claude(prompt, label, **kw):
        fake.claude_calls.append(label)
        for out in kw.get('outputs') or []:
            Path(out).write_text('{"date": "2026-09-30", "rows": [', encoding='utf-8')     # cut off mid-write
    install(monkeypatch, fake, pushes)
    monkeypatch.setattr(RL, 'claude', bad_claude)
    assert _run_main(monkeypatch, [D, '--no-push']) != 0


def test_transcript_text_matches_full_audit_prep(repo, monkeypatch):
    """The freshness check compares against exactly what full_audit_prep writes for the readers."""
    monkeypatch.setattr(P, 'DATES', [D])
    P.main()
    assert Path(RL.WORK, f'{D}.txt').read_text(encoding='utf-8') == RL.transcript_text(D)


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, 'argv', ['review_lesson.py', *argv])
    return RL.main()
