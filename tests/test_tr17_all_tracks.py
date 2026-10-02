# -*- coding: utf-8 -*-
"""Rule TR-17 (Medi 2026-10-02 "fix"): every recording of each person is transcribed and placed on the lesson clock by its
own start offset, merged per speaker, overlaps counted once; never only the longest recording.

The moment: 2026-10-01 Amal reconnected to the Meet, so she has two recordings (00:01-20:38 and 23:12-1:06:03). Only the
longest was transcribed, and her first 20 minutes - where she taught mitshajje3 (06:29) - never reached the transcript."""
import hashlib, json
from pathlib import Path

import hourly_lessons as H
import load_lesson as L
import fill_meet_gaps as F

DATE = '2026-10-01'


def _w(text, start, end=None, spk='speaker_0'):
    return {'type': 'word', 'text': text, 'start': start, 'end': end if end is not None else start + 0.4, 'speaker_id': spk}


def _resp(words, duration):
    items = []
    for i, w in enumerate(words):
        if i:
            items.append({'type': 'spacing', 'text': ' ', 'start': w['start'], 'end': w['start'], 'speaker_id': w['speaker_id']})
        items.append(w)
    return {'language_code': 'ara', 'audio_duration_secs': duration, 'words': items}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plant(raw, amal_first=(1.0, 100.0), amal_second=(150.0, 200.0), seg_words=None, main_words=None):
    """A planted multi-track lesson: Amal reconnected (two recordings), Medi one, the host's silent track."""
    tr = raw / 'tracks'
    tr.mkdir(parents=True)
    files = {}
    for name, body in (('Amal-first.mp3', b'amal one'), ('Amal-second.mp3', b'amal two'), ('Medi_Natanzi-1.mp3', b'medi'),
                       ('Ray_Adib-1.mp3', b'host')):
        (tr / name).write_bytes(body)
        files[name] = str(tr / name)
    tracks = [
        {'participant': 'Ray Adib', 'start': {'relative': 0.2}, 'duration_s': 15.0, 'file': files['Ray_Adib-1.mp3']},
        {'participant': 'Amal', 'start': {'relative': amal_first[0]}, 'duration_s': amal_first[1], 'file': files['Amal-first.mp3']},
        {'participant': 'Amal', 'start': {'relative': amal_second[0]}, 'duration_s': amal_second[1], 'file': files['Amal-second.mp3']},
        {'participant': 'Medi Natanzi', 'start': {'relative': 0.5}, 'duration_s': 400.0, 'file': files['Medi_Natanzi-1.mp3']},
    ]
    (tr / 'tracks.json').write_text(json.dumps({'tracks': tracks}), encoding='utf-8')
    (raw / 'scribe_Amal.json').write_text(json.dumps(_resp(main_words or [_w('marhaba', 1.0)], amal_second[1])), encoding='utf-8')
    (raw / 'scribe_Medi.json').write_text(json.dumps(_resp([_w('ana', 5.0), _w('mshajje3', 30.0)], 400.0)), encoding='utf-8')
    seg = raw / f'scribe_Amal_seg{int(amal_first[0])}.json'
    seg.write_text(json.dumps(_resp(seg_words or [_w('mitshajje3', 28.0)], amal_first[1])), encoding='utf-8')
    seg.with_name(seg.stem + '.provenance.json').write_text(json.dumps(
        {'source_file': files['Amal-first.mp3'], 'source_sha256': _sha(files['Amal-first.mp3'])}), encoding='utf-8')
    return tracks


def test_tr_17_every_recording_of_each_person_is_transcribed_not_only_the_longest(tmp_path):
    tracks = plant(tmp_path)
    tracks.append({'participant': 'Amal', 'start': {'relative': 360.0}, 'duration_s': 1.5, 'file': 'blip.mp3'})   # a 1.5 s blip
    jobs = {p.name: (t['file'], who) for p, t, who in H.track_transcripts(tmp_path, tracks)}
    assert jobs == {
        'scribe_Amal.json': (str(tmp_path / 'tracks' / 'Amal-second.mp3'), 'Amal'),          # the longest, as before
        'scribe_Amal_seg1.json': (str(tmp_path / 'tracks' / 'Amal-first.mp3'), 'Amal'),      # her reconnect: no longer dropped
        'scribe_Medi.json': (str(tmp_path / 'tracks' / 'Medi_Natanzi-1.mp3'), 'Medi'),
    }                                                                                         # host skipped, blip skipped
    assert {w: [t['file'] for t in ts] for w, ts in H.person_tracks(tracks).items()}['Amal'][:2] == [
        str(tmp_path / 'tracks' / 'Amal-second.mp3'), str(tmp_path / 'tracks' / 'Amal-first.mp3')]


def test_tr_17_hourly_job_uses_every_track_for_a_new_lesson():
    src = Path(H.__file__).read_text(encoding='utf-8')
    body = src[src.index("elif t['kind'] == 'tracks':"):src.index("import lesson_pipeline as lp\n                src")]
    assert 'track_transcripts(' in body and 'longest_tracks(' not in body


def test_tr_17_reconnect_recording_is_placed_on_the_lesson_clock_by_its_own_start(tmp_path):
    raw, work = tmp_path / 'raw', tmp_path / 'work'
    plant(raw)
    data, info = L.build_tracks(DATE, raw, work)
    amal = [(r['source_id'], round(r['timeline_start'], 2), r['text'].strip()) for r in data['rows'] if r['speaker_label'] == 'Amal']
    # her first recording starts at 1.0 s: its word at 28.0 s lands at 29.0 s; her second starts at 150 s
    assert amal == [('anees-20261001-recall-amal-seg1', 29.0, 'mitshajje3'), ('anees-20261001-recall-amal', 151.0, 'marhaba')]
    assert info['omitted'] == []                                # nothing left "Not transcribed" on the page note
    assert info['ranges']['Amal'] == (1.0, 350.0)              # Amal's interval covers both recordings


def test_tr_17_medi_is_not_withheld_where_amal_reconnect_recording_exists(tmp_path):
    raw, work = tmp_path / 'raw', tmp_path / 'work'
    plant(raw)
    data, info = L.build_tracks(DATE, raw, work)
    medi = next(r for r in data['rows'] if r['speaker_label'] == 'Medi' and 'mshajje3' in r['text'])
    lo, hi = info['ranges']['Amal']
    assert lo <= medi['timeline_start'] <= hi                  # guard_events no longer says "Tutor recording context unavailable"


def test_tr_17_overlapping_recordings_of_one_person_are_counted_once(tmp_path):
    raw, work = tmp_path / 'raw', tmp_path / 'work'
    # first recording 1-101 s, second from 90 s: both hold 'yalla' at lesson 96 s (the old connection still open)
    plant(raw, amal_first=(1.0, 100.0), amal_second=(90.0, 300.0),
          seg_words=[_w('kifak', 20.0), _w('yalla', 95.0)], main_words=[_w('yalla', 6.2), _w('khalas', 50.0)])
    data, info = L.build_tracks(DATE, raw, work)
    amal = [(r['source_id'].rsplit('-', 1)[-1], round(r['timeline_start'], 1), r['text'].strip()) for r in data['rows'] if r['speaker_label'] == 'Amal']
    assert amal == [('seg1', 21.0, 'kifak'), ('amal', 96.2, 'yalla'), ('amal', 140.0, 'khalas')]
    assert data['sources']['anees-20261001-recall-amal-seg1']['overlap_rows_dropped'] == ['anees-20261001-recall-amal-seg1:row:2']


def test_tr_17_dedupe_keeps_different_words_at_the_same_time(tmp_path):
    raw, work = tmp_path / 'raw', tmp_path / 'work'
    plant(raw, amal_first=(1.0, 100.0), amal_second=(90.0, 300.0),
          seg_words=[_w('shu', 95.0)], main_words=[_w('yalla', 6.2)])
    data, _ = L.build_tracks(DATE, raw, work)
    assert sorted(r['text'].strip() for r in data['rows'] if r['speaker_label'] == 'Amal') == ['shu', 'yalla']


def test_tr_17_gap_filler_does_not_pay_again_for_a_recording_the_load_already_has(tmp_path):
    plant(tmp_path / DATE)
    entry = {'date': DATE, 'missing': 'amal', 'window': {'from_s': 0.0, 'to_s': 120.0, 'from': '00:00', 'to': '02:00'}}
    trk, why = F.find_own_track(entry, raw=tmp_path)
    assert trk is None and 'no untranscribed Amal track' in why


def _ev(i, reason=L.WITHHELD, assessment='unresolved', **kw):
    e = {'id': i, 'speaker': 'Medi', 'item_ids': [i + ':item:0'], 'original_text': 'x', 'source_sha256': 's', 'row_id': 'r',
         'word_key': 'bas', 'text': 'x', 't_start': 1.0, 't_end': 2.0, 'assessment': assessment, 'reason': reason,
         'needs_review': True, 'spoken': False, 'context': []}
    e.update(kw)
    return e


def test_tr_17_backfill_inserts_new_events_and_overlays_only_the_withheld_ones():
    current = {'a': _ev('a'), 'b': _ev('b'), 'c': _ev('c', reason='other', assessment='independent')}
    rebuilt = [_ev('a', reason='heard', assessment='independent', needs_review=False, spoken=True, context=[{'who': 'Amal'}]),
               dict(current['b']), dict(current['c']), _ev('n', reason='new')]
    review = {'patches': {'a': {'expected': {}, 'changes': {'audit_created': True, 'audit_kind': 'tutor_audio_missing',
                                                             'audit_by': 'Claude audit 2026-09-28', 'ignored': True}}}}
    new, fixes = L.reconcile_tracks(rebuilt, current, review)
    assert [e['id'] for e in new] == ['n'] and list(fixes) == ['a']
    ch = review['patches']['a']['changes']
    assert ch['assessment'] == 'independent' and ch['auto_rule'] == 'TR-17' and 'ignored' not in ch   # missing-audio bin replaced
    assert review['patches']['a']['expected']['reason'] == L.WITHHELD                                  # source-bound (S2)
    import pytest
    with pytest.raises(ValueError):                         # any other difference is not a missing-track change
        L.reconcile_tracks([_ev('c', reason='other', assessment='helped')], current, {'patches': {}})


def test_tr_17_same_day_rules_stack_on_the_re_read_event_and_undo_cleanly():
    import review_new_lessons as R
    review = {'patches': {'a': {'expected': {'assessment': 'unresolved'},
                                'changes': {'auto_rule': 'TR-17', 'assessment': 'independent', 'needs_review': False}}}}
    R.layer(review, 'a', {'expected': {}, 'changes': {'auto_rule': R.TAG, 'scored_in_event': True, 'needs_review': True}})
    c = review['patches']['a']['changes']
    assert c['auto_rule'] == 'TR-17' and c['scored_in_event'] is True and c['needs_review'] is True
    R.unlayer(review, ['a'])                                   # a re-run starts from the TR-17 patch alone
    assert review['patches']['a']['changes'] == {'auto_rule': 'TR-17', 'assessment': 'independent', 'needs_review': False}
