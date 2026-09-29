import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import hourly_lessons as H
import load_lesson as L

DONE = [{'code': 'joining_call'}, {'code': 'done'}]


def bot(i, date=None, join='2026-09-21T20:35:16Z', status=DONE):
    return {'id': i, 'join_at': join, 'meeting_url': {'meeting_id': 'kht-vfaq-bxh', 'platform': 'google_meet'},
            'metadata': {'anees_lesson': date} if date else {}, 'status_changes': status}


def test_api_discovers_bots_missing_from_the_ledger():
    ledger = [{'bot_id': 'a', 'date': '2026-09-19', 't': '2026-09-19T14:15:55'}]
    new = H.merge_bots(ledger, [bot('a', '2026-09-19'), bot('b', '2026-09-21')])
    assert [(r['bot_id'], r['date'], r['meeting_url']) for r in new] == [('b', '2026-09-21', 'https://meet.google.com/kht-vfaq-bxh')]


def test_bot_date_falls_back_to_pacific_join_day():
    assert H.bot_date(bot('x', join='2026-09-22T03:10:00Z')) == '2026-09-21'


def touch(p, size=H.MIN_BYTES):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'wb') as f:
        f.truncate(size)
    return p


def test_both_drive_folder_styles_are_scanned(tmp_path):
    touch(tmp_path / 'Meet Recordings' / 'vzq-tryv-mdw (2026-08-25 14 27 GMT-7)')
    touch(tmp_path / 'Google Meet' / 'pki-dqkp-kyn - 2026 09 18 14 08 PDT' / 'pki-dqkp-kyn (2026-09-18 14 08 GMT-7)')
    touch(tmp_path / 'Google Meet' / 'pki-dqkp-kyn - 2026 09 18 14 08 PDT' / 'pki-dqkp-kyn (2026-09-18 14 08 GMT-7) - Chat Transcript', 10)
    touch(tmp_path / 'Google Meet' / 'x - 2026 09 19' / 'cuv-feor-sou (2026-09-19 14 08 GMT-7)', 10)      # too small
    found = [(c, d, h) for _, c, d, h in H.meet_recordings(tmp_path)]
    assert found == [('vzq-tryv-mdw', '2026-08-25', '1427'), ('pki-dqkp-kyn', '2026-09-18', '1408')]


def test_plan_tracks_beat_meet_loaded_dates_untouched_and_unfinished_bots_wait(tmp_path):
    ledger = [{'bot_id': 'old', 'date': '2026-09-19', 't': 'x'}]
    bots = [bot('old', '2026-09-19'), bot('new', '2026-09-21'), bot('live', '2026-09-23', status=[{'code': 'in_call_recording'}])]
    rec = lambda code, d: (tmp_path / f'{code} ({d} 14 08 GMT-7)', code, d, '1408')
    recordings = [rec('kht-vfaq-bxh', '2026-09-21'), rec('pki-dqkp-kyn', '2026-09-18'), rec('mqp-zwfh-wby', '2026-09-22'), rec('ctn-wxzy-oms', '2026-06-17')]
    new_rows, todo = H.plan(ledger, bots, recordings, loaded_dates={'2026-09-19'}, raw=tmp_path,
                            decided={'mqp-zwfh-wby (2026-09-22 14 08 GMT-7)': 'not a lesson'})
    assert {r['bot_id'] for r in new_rows} == {'new', 'live'}
    assert [(t['kind'], t['date']) for t in todo] == [('tracks', '2026-09-21'), ('meet', '2026-09-18')]


def test_host_account_is_never_a_speaker():
    assert L._person('Ray Adib') is None and L._person('Amal Abusrour') == 'Amal' and L._person('Medi Natanzi') == 'Medi'


def test_each_person_longest_track_is_transcribed_and_host_skipped():
    tracks = [{'participant': 'Ray Adib', 'duration_s': 5000}, {'participant': 'Amal', 'duration_s': 59, 'file': 'a1'},
              {'participant': 'Amal', 'duration_s': 4056, 'file': 'a2'}, {'participant': 'Medi Natanzi', 'duration_s': 4108, 'file': 'm'}]
    best = H.longest_tracks(tracks)
    assert {k: v['file'] for k, v in best.items()} == {'Amal': 'a2', 'Medi': 'm'}


def test_half_done_dates_are_republished_not_forgotten(tmp_path):
    new_rows, todo = H.plan([], [], [], loaded_dates=set(), raw=tmp_path, half_done={'2026-09-24'})
    assert todo == [{'kind': 'republish', 'date': '2026-09-24'}]


def test_winter_join_uses_pacific_standard_time():
    assert H.bot_date(bot('w', join='2026-12-01T07:30:00Z')) == '2026-11-30'


# ---------------------------------------------------------------- engineering audit 2026-09-29, area 4 + decision 7
# The hourly job must fail CLOSED: every push goes through scripts/publish_guard.py, a failed build step blocks the push
# and is retried next hour, and a lesson's review is retried until it finishes.
import json, subprocess, types
import pytest
import publish_guard as G


class Git:
    """Fake subprocess.run: records every command; rc per script name; `check=True` raises like the real one."""
    def __init__(self, fail=(), ahead='2'):
        self.calls, self.fail, self.ahead = [], set(fail), ahead

    def __call__(self, cmd, *a, **k):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        out = self.ahead + '\n' if cmd[:2] == ['git', 'rev-list'] else ' M docs/data/tutor.json\n' if cmd[:2] == ['git', 'status'] else ''
        rc = 1 if any(Path(c).name in self.fail for c in cmd) else 0
        if rc and k.get('check'):
            raise subprocess.CalledProcessError(rc, cmd, '', 'boom')
        return subprocess.CompletedProcess(cmd, rc, out, 'boom' if rc else '')

    def pushes(self):
        return [c for c in self.calls if c[:2] == ['git', 'push']]


@pytest.fixture
def job(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    for p in ('docs/lessons', 'docs/data', 'data/lessons', 'data/lesson-work/full-audit'):
        (root / p).mkdir(parents=True)
    raw = tmp_path / 'raw'
    raw.mkdir()
    monkeypatch.setattr(H, 'ROOT', root)
    monkeypatch.setenv('ANEES_TRIGGER', 'hourly')      # main() setdefaults it; keep it from leaking into other tests
    state = types.SimpleNamespace(in_db=set(), guard=[], guard_ok=False, refresh=[], refresh_fail=[], git=Git())
    fdb = types.ModuleType('db')
    fdb.select = lambda *a, **k: [{'date': d} for d in state.in_db]
    fdb.rest = lambda *a, **k: {'events': []}
    fR = types.ModuleType('recall_bot'); fR.LESSONS = raw; fR.fetch = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, 'db', fdb)
    monkeypatch.setitem(sys.modules, 'recall_bot', fR)
    monkeypatch.setattr(H, 'recall_bots', lambda: [])
    monkeypatch.setattr(H, 'meet_recordings', lambda drive: [])
    monkeypatch.setattr(H, 'meet_for', lambda d, recs: None)
    monkeypatch.setattr(H, 'load', lambda *a, **k: {'events': 3})
    monkeypatch.setattr(H, 'tutor_refresh', lambda *a, **k: [])
    monkeypatch.setattr(H, 'gap_fill_refresh', lambda *a, **k: {'failures': []})
    monkeypatch.setattr(H, 'decisions_refresh', lambda *a, **k: None)
    monkeypatch.setattr(H, 'pending_reviews', lambda *a, **k: [], raising=False)

    def refresh(dates, raw_, work):
        state.refresh.append(list(dates))
        return list(state.refresh_fail)
    monkeypatch.setattr(H, 'refresh_published', refresh)
    monkeypatch.setattr(H.subprocess, 'run', state.git)

    def guarded(root_=None, source='?', step_failures=(), **k):
        state.guard.append({'source': source, 'step_failures': list(step_failures)})
        ok = state.guard_ok and not list(step_failures) and not G.open_failures(root)
        return {'pushed': ok, 'outcome': 'pushed' if ok else 'blocked', 'reason': '' if ok else 'test block'}
    monkeypatch.setattr(G, 'guarded_push', guarded)
    monkeypatch.setattr(sys, 'argv', ['hourly_lessons.py', '--raw', str(raw), '--work', str(tmp_path / 'work')])
    state.root, state.raw = root, raw
    return state


def new_lesson(job, d='2026-09-30'):
    job.in_db = {d}
    (job.raw / d / 'tracks').mkdir(parents=True)
    (job.raw / d / 'tracks' / 'tracks.json').write_text('{"tracks": []}', encoding='utf-8')
    return d


def test_stranded_commits_are_pushed_only_through_the_guard(job):
    job.git.ahead = '2'
    rc = H.main()
    assert not job.git.pushes()                        # before: a bare `git push origin HEAD:master`
    assert len(job.guard) == 1
    assert rc == 1                                     # blocked = the scheduled task shows a failure


def test_a_failed_build_step_blocks_the_lesson_push(job):
    d = new_lesson(job)
    job.refresh_fail = ['build_sentence_ladder.py exit 1']
    job.guard_ok = True
    rc = H.main()
    assert job.refresh == [[d]]
    assert not job.git.pushes()
    assert job.guard and job.guard[-1]['step_failures'] == ['build_sentence_ladder.py exit 1']
    assert rc == 1


def test_a_failed_step_is_retried_next_hour_and_blocks_until_it_passes(job):
    d = new_lesson(job)
    job.refresh_fail = ['review_lesson.py 2026-09-30 exit 1']
    job.guard_ok = True
    assert H.main() == 1
    (job.root / 'docs' / 'lessons' / f'{d}.html').write_text('page', encoding='utf-8')   # loaded + committed locally
    job.refresh.clear(); job.guard.clear()
    assert H.main() == 1                                                                 # still failing
    assert job.refresh == [[d]]                                                          # retried, not forgotten
    job.refresh.clear(); job.refresh_fail = []
    assert H.main() == 0                                                                 # passes -> cleared -> pushed
    assert job.refresh == [[d]] and G.open_failures(job.root) == {}


def test_refresh_published_reports_failed_steps(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    (root / 'docs' / 'data').mkdir(parents=True)
    monkeypatch.setattr(H, 'ROOT', root)
    fdb = types.ModuleType('db'); fdb.rest = lambda *a, **k: {'events': []}
    monkeypatch.setitem(sys.modules, 'db', fdb)
    monkeypatch.setattr(H, 'build_clips', lambda *a, **k: None)
    monkeypatch.setattr(H.subprocess, 'run', Git(fail={'build_sentence_ladder.py', 'review_lesson.py'}))
    fails = H.refresh_published(['2026-09-30'], tmp_path / 'raw', tmp_path / 'work')
    assert fails and any('build_sentence_ladder.py' in f for f in fails)
    assert any('review_lesson.py' in f and '2026-09-30' in f for f in fails)


def test_gap_fill_rebuild_failure_is_reported(tmp_path, monkeypatch):
    import fill_meet_gaps as F
    monkeypatch.setattr(H, 'ROOT', tmp_path)
    monkeypatch.setattr(F, 'process_queue', lambda **k: {'done': ['2026-09-26-amal'], 'failed': [], 'pending': [], 'changed': True})
    monkeypatch.setattr(H.subprocess, 'run', Git(fail={'build_lessons_page_data.py'}))
    r = H.gap_fill_refresh(tmp_path, no_push=True)
    assert r and any('build_lessons_page_data.py' in f for f in r.get('failures', []))


def test_tutor_refresh_reports_a_failed_apply(tmp_path, monkeypatch):
    monkeypatch.setattr(H, 'ROOT', tmp_path)
    monkeypatch.setattr(H.subprocess, 'run', Git(fail={'apply_amal_audit_rulings.py'}))
    monkeypatch.setattr(G, 'guarded_push', lambda *a, **k: {'pushed': False, 'outcome': 'blocked', 'reason': 'x'})
    fails = H.tutor_refresh(no_push=True)
    assert fails and 'apply_amal_audit_rulings.py' in fails[0]


def test_pending_reviews_finds_unfinished_and_outdated_reviews(tmp_path, monkeypatch):
    import review_lesson as RL
    work = tmp_path / 'data' / 'lesson-work' / 'full-audit'
    work.mkdir(parents=True)
    (tmp_path / 'docs' / 'lessons').mkdir(parents=True)
    for d in ('2026-09-05', '2026-09-26', '2026-09-28', '2026-09-30'):
        (tmp_path / 'docs' / 'lessons' / f'{d}.html').write_text('p', encoding='utf-8')
    for d in ('2026-09-05', '2026-09-26', '2026-09-28'):
        (work / f'{d}.settled.json').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(RL, 'readers_read_current', lambda d, repo=None: 'transcript changed after the readers read it' if d == '2026-09-26' else None)
    got = H.pending_reviews(tmp_path)
    assert [d for d, _ in got] == ['2026-09-30', '2026-09-26']        # never finished first; 09-05 is before AUTO_START
    assert 'never finished' in got[0][1] and 'transcript changed' in got[1][1]


def test_a_new_transcript_is_logged_with_its_hash_and_model(tmp_path, monkeypatch):
    """AI review 09-27 / worker D: the saved Scribe JSON (path + sha256) and the model that answered go in the run log."""
    import lesson_pipeline as lp, track
    monkeypatch.setattr(lp, 'transcribe', lambda mp3: {'words': [{'type': 'word', 'text': 'marhaba'}], 'language_code': 'ara'})
    lines = []
    monkeypatch.setattr(track, 'log_run', lambda step, date=None, **k: lines.append((step, date, k)))
    mp3 = tmp_path / '2026-09-30' / 'tracks' / 'Amal.mp3'
    mp3.parent.mkdir(parents=True); mp3.write_bytes(b'audio')
    out = tmp_path / '2026-09-30' / 'scribe_Amal.json'
    H.transcribe_once(out, mp3, 'Amal')
    step, date, k = lines[-1]
    assert step == 'scribe.saved' and date == '2026-09-30'
    assert k['outputs'] == [out] and k['response_model'] == 'scribe_v2' and k['inputs'] == [mp3]


def test_a_new_lesson_gets_its_grammar_uses_counted(tmp_path, monkeypatch):
    """09-28 was loaded by the hourly job on live master with grammar uses = None and pct = None: detect_grammar_usage.py
    (the Grammar % denominator, docs/data/grammar-usage.json) was never in the hourly path (09-26 was counted by hand)."""
    root = tmp_path / 'repo'
    (root / 'docs' / 'data').mkdir(parents=True)
    monkeypatch.setattr(H, 'ROOT', root)
    fdb = types.ModuleType('db'); fdb.rest = lambda *a, **k: {'events': []}
    monkeypatch.setitem(sys.modules, 'db', fdb)
    monkeypatch.setattr(H, 'build_clips', lambda *a, **k: None)
    git = Git()
    monkeypatch.setattr(H.subprocess, 'run', git)
    assert H.refresh_published(['2026-09-30'], tmp_path / 'raw', tmp_path / 'work') == []
    order = [Path(x).name for c in git.calls for x in c if str(x).endswith(('.py', '.cjs'))]
    assert 'detect_grammar_usage.py' in order
    assert order.index('detect_grammar_usage.py') < order.index('build_lessons_page_data.py')
