"""M8 gate: pipeline hardening — failed speaker split, missing chat sidecar, git push failure, ElevenLabs 429 with 3 retries +
failure email to Medi, empty transcript, English-only call, budget guards. All with mocks: no paid call, no email actually sent."""
import io, json
from pathlib import Path
import pytest

import pipeline_ext as px
import lesson_pipeline as lp
import understand_lesson as ul

ROOT = Path(__file__).resolve().parent.parent


class R:
    def __init__(self, code, text='', body=None): self.status_code, self.text, self._b = code, text, body or {}
    def json(self): return self._b


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(px, 'LEDGER', tmp_path / 'budget.json')
    return tmp_path / 'budget.json'


def test_429_retries_three_times_then_fails(tmp_path, ledger):
    mp3 = tmp_path / 'a.mp3'; mp3.write_bytes(b'x')
    calls, sleeps = [], []
    def post(url, headers, data, files, timeout): calls.append(url); return R(429, 'quota')
    with pytest.raises(RuntimeError) as e:
        px.transcribe_with_retry(post, mp3, 'k', minutes=60, sleep=sleeps.append)
    assert len(calls) == 3 and sleeps == [5, 20, 60] and '429' in str(e.value)
    assert not ledger.exists() or px.ledger()['elevenlabs'] == 0.0, 'a failed call must not be charged to the ledger'


def test_429_then_success_is_charged_once(tmp_path, ledger):
    mp3 = tmp_path / 'a.mp3'; mp3.write_bytes(b'x')
    seq = [R(429), R(503), R(200, body={'words': [{'type': 'word', 'text': 'x'}]})]
    def post(*a, **k): return seq.pop(0)
    out = px.transcribe_with_retry(post, mp3, 'k', minutes=60, sleep=lambda s: None)
    assert out['words'] and abs(px.ledger()['elevenlabs'] - 0.22) < 0.001


def test_other_4xx_does_not_retry(tmp_path, ledger):
    mp3 = tmp_path / 'a.mp3'; mp3.write_bytes(b'x')
    calls = []
    def post(*a, **k): calls.append(1); return R(401, 'bad key')
    with pytest.raises(RuntimeError):
        px.transcribe_with_retry(post, mp3, 'k', minutes=60, sleep=lambda s: None)
    assert len(calls) == 1


def test_budget_guard_stops_at_90_percent(tmp_path, ledger):
    px.spend('elevenlabs', 8.9, 'earlier lessons')
    mp3 = tmp_path / 'a.mp3'; mp3.write_bytes(b'x')
    with pytest.raises(px.BudgetStop):
        px.transcribe_with_retry(lambda *a, **k: R(200, body={'words': []}), mp3, 'k', minutes=60)
    assert px.budget_ok('openai', 0.15) and not px.budget_ok('openai', 9.5)


def test_failure_email_is_rich_and_medi_only(tmp_path, monkeypatch):
    monkeypatch.setattr(px, 'ROOT', tmp_path)
    ran = []
    ok = px.failure_email('Anees: pipeline failed', 'ElevenLabs failed after 3 tries: 429', '2026-09-05', run=lambda cmd, **k: ran.append(cmd))
    assert ok and ran and ran[0][0] == 'node' and ran[0][1].endswith('send_lesson_email.mjs')
    p = json.load(io.open(tmp_path / 'data' / 'lessons' / 'last_failure_email.json', encoding='utf-8'))
    assert p['chart'] and p['log'] and 'Medi' in p['footer']
    mjs = (ROOT / 'scripts' / 'send_lesson_email.mjs').read_text(encoding='utf-8')
    assert "const TO = 'thenatanzi@gmail.com'" in mjs and 'amalabusrour' not in mjs


def test_failure_email_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(px, 'ROOT', tmp_path)
    def boom(cmd, **k): raise OSError('no node')
    assert px.failure_email('x', 'y', run=boom) is False


def test_empty_transcript_and_english_only_call():
    with pytest.raises(RuntimeError):
        lp.build({'words': []}, '2099-01-01', '0000', 'x')
    words = [{'type': 'word', 'text': t, 'start': i, 'end': i + 0.4, 'speaker_id': 'speaker_0' if i % 2 else 'speaker_1'} for i, t in enumerate('this is an english only call about nothing at all'.split())]
    w, runs, summary = lp.build({'words': words}, '2099-01-01', '0000', 'x')
    assert summary['arabic_share'] == 0.0 and summary['arabic_share'] < lp.MIN_ARABIC_SHARE


def test_failed_speaker_split_publishes_dashes():
    words = [{'type': 'word', 'text': 'كتير', 'start': i, 'end': i + 0.4, 'speaker_id': 'speaker_0'} for i in range(40)] + \
            [{'type': 'word', 'text': 'ok', 'start': 50, 'end': 50.3, 'speaker_id': 'speaker_1'}]
    w, runs, summary = lp.build({'words': words}, '2099-01-01', '0000', 'x', mp3=None)
    assert summary['medi_arabic_words'] is None and summary['confirmations'] is None and summary['speaker_split'].startswith('failed')
    conf = ul.label_confidence([{'spk': 'Both'}] * 41, summary)
    assert conf['per_speaker_ok'] is False


def test_missing_chat_sidecar_is_empty_not_error(tmp_path):
    assert lp.chat_sidecar(tmp_path / 'no-such-recording') == []


def test_git_push_failure_raises_before_email(monkeypatch, tmp_path):
    import subprocess
    calls = []
    class P:  # fake CompletedProcess
        def __init__(self, rc): self.returncode, self.stderr, self.stdout = rc, 'remote: rejected', ''
    def fake_run(cmd, **k):
        calls.append(cmd)
        return P(1 if 'push' in cmd else 0)
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(lp, 'DOCS', tmp_path / 'docs'); monkeypatch.setattr(lp, 'STATE', tmp_path / 'state.json'); monkeypatch.setattr(lp, 'LESSONS', tmp_path / 'lessons')
    with pytest.raises(RuntimeError) as e:
        lp.publish('2099-01-01', '<html></html>')
    assert 'git push failed' in str(e.value)


def test_post_process_guards_each_step(monkeypatch, tmp_path):
    import types, sys
    monkeypatch.setattr(px, 'ROOT', tmp_path)
    emails = []
    monkeypatch.setattr(px, 'failure_email', lambda s, r, d=None, **k: emails.append((s, r)) or True)
    fake = types.ModuleType('understand_lesson'); fake.understand = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('no words'))
    monkeypatch.setitem(sys.modules, 'understand_lesson', fake)
    out = px.post_process('2099-01-01', send_email=False, log=lambda *a: None)
    assert 'report_error' in out and emails and 'report for 2099-01-01 failed' in emails[0][0]
    assert 'after_link' not in out


# ---- 2026-09-05 audit fixes: post-transcription gate + report pushed and live BEFORE its email ----

def test_post_transcription_gate_keeps_code_switched_lesson():
    # Sep 4 measured 0.11 after a pre-check of 0.49 and was wrongly skipped; the paid transcript must be kept
    assert not lp.should_skip_after_transcription(0.11, tutor_typed=False)
    assert lp.should_skip_after_transcription(0.03, tutor_typed=False)
    assert not lp.should_skip_after_transcription(0.03, tutor_typed=True)       # Amal typed -> it is a lesson
    assert not lp.should_skip_after_transcription(0.03, tutor_typed=False, force=True)
    assert lp.MIN_ARABIC_SHARE_POST < lp.MIN_ARABIC_SHARE


def test_verify_live_waits_then_succeeds_or_fails():
    class G:
        def __init__(self, code): self.status_code = code
    seq = [G(404), G(404), G(200)]
    sleeps = []
    assert lp.verify_live('u', get=lambda url, timeout: seq.pop(0), tries=5, wait=7, sleep=sleeps.append)
    assert sleeps == [7, 7]
    assert not lp.verify_live('u', get=lambda url, timeout: G(404), tries=3, wait=1, sleep=lambda s: None)


def test_publish_report_push_failure_raises(monkeypatch, tmp_path):
    class P:
        def __init__(self, rc): self.returncode, self.stderr, self.stdout = rc, 'remote: rejected', ''
    monkeypatch.setattr(lp, 'DOCS', tmp_path / 'docs'); monkeypatch.setattr(lp, 'LESSONS', tmp_path / 'lessons')
    gets = []
    with pytest.raises(RuntimeError) as e:
        lp.publish_report('2099-01-01', run=lambda cmd, **k: P(1 if 'push' in cmd else 0), get=lambda *a, **k: gets.append(1), sleep=lambda s: None)
    assert 'git push failed' in str(e.value) and not gets, 'no liveness check and no link when the push failed'


def test_publish_report_not_live_raises(monkeypatch, tmp_path):
    class P:
        def __init__(self, rc): self.returncode, self.stderr, self.stdout = rc, '', ''
    class G:
        status_code = 404
    monkeypatch.setattr(lp, 'DOCS', tmp_path / 'docs'); monkeypatch.setattr(lp, 'LESSONS', tmp_path / 'lessons')
    monkeypatch.setattr(lp, 'LIVE_TRIES', 2)
    with pytest.raises(RuntimeError) as e:
        lp.publish_report('2099-01-01', run=lambda cmd, **k: P(0), get=lambda *a, **k: G(), sleep=lambda s: None)
    assert 'not live' in str(e.value)


def test_report_email_only_after_push_and_live(monkeypatch, tmp_path):
    """post_process order must be: understand -> build (send=False) -> publish_report -> email. A failed publish = no email."""
    import types, sys, subprocess
    monkeypatch.setattr(px, 'ROOT', tmp_path)
    order, emails = [], []
    monkeypatch.setattr(px, 'failure_email', lambda s, r, d=None, **k: emails.append(s) or True)
    fu = types.ModuleType('understand_lesson'); fu.understand = lambda *a, **k: order.append('understand')
    fb = types.ModuleType('build_report')
    def build(date, use_db=True, send=False, u=None):
        assert send is False, 'build must never send the email itself any more'
        order.append('build'); return {'rows': 0}
    fb.build = build
    fl = types.ModuleType('lesson_pipeline'); fl.publish_report = lambda date: order.append('publish') or 'https://x/report'
    for name, mod in (('understand_lesson', fu), ('build_report', fb), ('lesson_pipeline', fl)):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **k: order.append('email:' + cmd[2][:16]))
    fa = types.ModuleType('after_questions'); fa.payload = lambda *a, **k: {}
    fk = types.ModuleType('amal_links'); fk.create = lambda *a, **k: ('t', 'https://x/after')
    monkeypatch.setitem(sys.modules, 'after_questions', fa); monkeypatch.setitem(sys.modules, 'amal_links', fk)
    out = px.post_process('2099-01-01', send_email=True, use_openai=False, log=lambda *a: None)
    assert order == ['understand', 'build', 'publish', 'email:Anees: lesson re'] and out['report']['url'] == 'https://x/report' and out['report']['emailed']
    # now the push fails: build happens, email never does, Medi gets the failure email
    order.clear(); emails.clear()
    fl.publish_report = lambda date: (_ for _ in ()).throw(RuntimeError('git push failed: rejected'))
    out = px.post_process('2099-01-01', send_email=True, use_openai=False, log=lambda *a: None)
    assert order == ['understand', 'build'] and 'report_error' in out and emails and 'report for 2099-01-01 failed' in emails[0]
