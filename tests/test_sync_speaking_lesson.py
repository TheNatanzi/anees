import json
from pathlib import Path

import sync_speaking_lesson as sync
import pytest


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_recall_tracks_become_stable_source_bound_transcript(tmp_path):
    lesson = tmp_path / '2026-09-12'
    tracks = []
    for name, filename, offset, word in [('Amal', 'Amal.mp3', .5, 'مرحبا'),
                                         ('Medi Natanzi', 'Medi_Natanzi.mp3', .1, 'كلمة')]:
        audio = lesson / 'tracks' / filename
        audio.parent.mkdir(parents=True, exist_ok=True); audio.write_bytes(name.encode())
        tracks.append({'participant': name, 'file': str(audio), 'start': {'relative': offset}, 'duration_s': 10})
        who = 'Amal' if name == 'Amal' else 'Medi'
        write(lesson / f'scribe_{who}.json', {'language_code': 'ara', 'audio_duration_secs': 10,
              'words': [{'text': word, 'start': 1, 'end': 1.4, 'type': 'word', 'speaker_id': 'speaker_0'},
                        {'text': ' ', 'start': 1.4, 'end': 1.5, 'type': 'spacing', 'speaker_id': 'speaker_0'},
                        {'text': word, 'start': 1.5, 'end': 1.9, 'type': 'word', 'speaker_id': 'speaker_0'}]})
    write(lesson / 'tracks' / 'tracks.json', {'tracks': tracks})
    first = sync.build_transcript('2026-09-12', lesson, write=False)
    second = sync.build_transcript('2026-09-12', lesson, write=False)
    assert first['manifest_sha256'] == second['manifest_sha256']
    assert {source['speaker_label'] for source in first['sources'].values()} == {'Amal', 'Medi'}
    medi = next(row for row in first['rows'] if row['speaker_label'] == 'Medi')
    assert medi['timeline_start'] == 1.1 and medi['items'][0]['local_start'] == 1
    assert medi['text'] == 'كلمة كلمة'


def test_recent_word_order_uses_last_occurrence_not_document_order():
    js = Path(sync.ROOT / 'docs/js/speaking.js').read_text(encoding='utf-8')
    assert 'recentByWord' in js and "rank[1]>current[1]" in js


def test_contextual_audit_survives_rerun_and_rejects_source_drift():
    old = {'id': 'x', 'source_sha256': 'source', 'original_text': 'word',
           'context': [], 'assessment': 'independent', 'vocab_points': 1,
           'tense': 'present', 'contextual_audit': {'reason': 'Reviewed clause'}}
    generated = {**old, 'assessment': 'unresolved'}
    generated.pop('contextual_audit')
    assert sync.preserve_contextual_reviews([generated], [old]) == [old]
    for changed in ([], [{**generated, 'source_sha256': 'different'}],
                    [{**generated, 'context': [{'text': 'changed'}]}]):
        with pytest.raises(RuntimeError, match='explicit reconciliation'):
            sync.preserve_contextual_reviews(changed, [old])
