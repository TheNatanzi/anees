# -*- coding: utf-8 -*-
"""AM-20 (Medi 2026-10-02: "DUDE FUCKING FIX THE ISSUE WITH HER DOCUMENT. YOU HAVE A DIRECT GOOGLE CONNECTION TO THE DOC
WHY IS THIS SO FUCKING HARD"): the hourly import reads the Doc export that the Apps Script "Anees doc sync" writes to
G:/My Drive every hour; an export older than 2 h is never imported and puts one line on Progress + Lessons.
Temp folders only: no network, no Supabase."""
import datetime as dt, json
import doc_sync, import_vocab as IV, lesson_alerts as A


def _export(folder, age_h, error=None, now=None):
    now = now or dt.datetime.now().astimezone()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / doc_sync.MD_NAME).write_text('# Latest Topic\n\n| a | b |\n', encoding='utf-8')
    st = {'ok_at': (now - dt.timedelta(hours=age_h)).isoformat(timespec='seconds'), 'tried_at': now.isoformat(), 'error': error}
    (folder / doc_sync.STATUS_NAME).write_text(json.dumps(st), encoding='utf-8')
    return now


def test_AM_20_the_import_picks_the_synced_doc_export(tmp_path, monkeypatch):
    _export(tmp_path, 0.5)
    monkeypatch.setenv('ANEES_DOC_SYNC_DIR', str(tmp_path))
    monkeypatch.setattr(IV.E, 'env', lambda k, *a, **kw: None)
    text, kind, label = IV.load_source()
    assert text.startswith('# Latest Topic') and kind == 'md'
    assert str(tmp_path / doc_sync.MD_NAME) in label and '(synced Doc export ' in label
    assert IV.live_source(label, None)                              # a fresh export may sync Supabase


def test_AM_20_a_stale_export_is_never_imported(tmp_path, monkeypatch, capsys):
    _export(tmp_path, 5)
    monkeypatch.setenv('ANEES_DOC_SYNC_DIR', str(tmp_path))
    monkeypatch.setattr(IV.E, 'env', lambda k, *a, **kw: None)
    _, _, label = IV.load_source()
    assert not IV.live_source(label, None)                          # falls back to the snapshot: nothing written
    assert 'synced Doc export not used' in capsys.readouterr().out


def test_AM_20_a_stale_export_raises_the_banner_line_with_time_and_reason(tmp_path):
    now = _export(tmp_path / 'doc', 3, error='export HTTP 403: insufficient permission')
    p = doc_sync.stale_problem(tmp_path / 'doc', now)
    assert p['kind'] == 'doc-stale' and 'export HTTP 403' in p['cause']
    doc, changed, new = A.update(tmp_path, [p])
    line = doc['problems'][0]
    assert changed and new == ['doc-sync']
    assert line['text'].startswith("Amal's word Doc not synced since {since}: the Google export failed: export HTTP 403")
    assert line['since'] == p['since']                              # the last good export, not the hour it was noticed
    assert doc_sync.stale_problem(tmp_path / 'doc', now - dt.timedelta(hours=2)) is None    # fresh = no line
    gone = doc_sync.stale_problem(tmp_path / 'missing', now)
    assert gone['since'] is None and A.line_for(gone).startswith("Amal's word Doc never synced on this PC: no export file")


def test_AM_20_an_unchanged_export_is_remembered_by_its_sha(tmp_path):
    p = tmp_path / 'last.json'
    assert IV.last_synced(path=p) is None
    IV.last_synced('abc123', 'G:/x.md', path=p)
    assert IV.last_synced(path=p) == 'abc123'
