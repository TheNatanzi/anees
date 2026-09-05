"""M1 gate: topics (Sep 4 = babse6 family top-2; Aug 25 top topic stated), >= 90% of Amal's typed words located within +-120 s,
every event has a browser clip <= 25 s whose ffprobe duration matches clip_end - clip_start +- 0.5 s, speaker-label floor."""
import io, json, random, subprocess
from pathlib import Path
import pytest

import understand_lesson as ul

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / 'data' / 'lessons'
DATES = ['2026-08-25', '2026-09-04']


def load(date):
    p = LESSONS / date / 'understanding.json'
    if not p.exists():
        pytest.skip(f'{p} not built')
    return json.load(io.open(p, encoding='utf-8'))


def test_sep4_babse6_family_in_top2():
    u = load('2026-09-04')
    top2 = [t['topic'].lower() for t in u['topics'][:2]]
    assert any(('babse6' in t or 'banbese6' in t or 'basa6' in t) for t in top2), top2


def test_aug25_top_topic_is_stated_with_reason():
    u = load('2026-08-25')
    t = u['topics'][0]
    assert t['score'] > 0 and t['distinct_words'] >= 3 and t['top_words'], t
    assert not t['glue'], 'top topic must be a content topic, not glue words'


def test_sep4_typed_words_found_within_120s():
    u = load('2026-09-04')
    rows = u['chat']
    assert len(rows) == 47
    found = [r for r in rows if r['found']]
    assert len(found) >= 0.9 * len(rows), f'{len(found)}/{len(rows)}'
    assert all(abs(r['delta']) <= ul.CHAT_WINDOW for r in found)


@pytest.mark.parametrize('date', DATES)
def test_every_event_has_a_clip_file(date):
    u = load(date)
    assert u['events'], 'no events'
    for e in u['events']:
        assert e.get('clip'), e
        assert (ROOT / 'docs' / 'lessons' / date / 'clips' / e['clip']).exists(), e['clip']
        assert e['clip_end'] - e['clip_start'] <= ul.CLIP_MAX + 0.01
        assert 0 <= e['offset'] <= e['clip_end'] - e['clip_start']


def test_20_random_clips_match_ffprobe():
    evs = []
    for date in DATES:
        u = load(date)
        evs += [(date, e) for e in u['events']]
    rng = random.Random(20260905)
    sample = rng.sample(evs, 20)
    for date, e in sample:
        p = ROOT / 'docs' / 'lessons' / date / 'clips' / e['clip']
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)],
                                   capture_output=True, text=True).stdout.strip())
        want = e['clip_end'] - e['clip_start']
        assert abs(dur - want) <= 0.5, (e['clip'], dur, want)
        assert dur <= ul.CLIP_MAX + 0.5
        # the event sits inside the clip at its recorded offset
        assert e['clip_start'] + e['offset'] == pytest.approx(e['t_start'], abs=0.01)


def test_label_floor_forced_one_voice():
    """A transcript whose speaker split failed and stayed > 15% unlabeled publishes NO per-speaker fields."""
    words = [{'s': i * 1.0, 'e': i * 1.0 + 0.5, 'spk': '?' if i % 3 else 'Medi', 'w': 'كتير'} for i in range(30)]
    conf = ul.label_confidence(words, {'speaker_split': 'failed: one voice'})
    assert conf['per_speaker_ok'] is False and conf['unlabeled_share'] > ul.MAX_UNLABELED and conf['reason']
    evs = ul.apply_floor([{'speaker': 'Medi', 'prompted': True, 'correction': False, 'uptake': False, 'word_key': 'ktIr'}], conf)
    assert evs[0]['speaker'] == '?' and evs[0]['prompted'] is None and evs[0]['correction'] is None and evs[0]['uptake'] is None
    # and the opposite: a clean split keeps them
    conf_ok = ul.label_confidence([{'spk': 'Medi'}] * 10, {'speaker_split': 'ok'})
    assert conf_ok['per_speaker_ok'] is True


def test_label_floor_pitch_fallback_under_15pct_is_published():
    words = [{'spk': '?' if i % 10 == 0 else 'Amal'} for i in range(100)]
    conf = ul.label_confidence(words, {'speaker_split': 'from voice pitch'})
    assert conf['per_speaker_ok'] is True and conf['unlabeled_share'] == 0.1


def test_arabizi_skeleton_bridge():
    assert ul.arabizi_to_ar_skel('Babse6') == ul.ar_skel('ببسط')
    assert ul.family_key('Btenbese6i') == ul.family_key('Banbese6') == ul.family_key('Enbasa6u')


def test_empty_transcript_is_loud(tmp_path):
    """An empty ElevenLabs response must raise, never produce a report with zeros."""
    p = tmp_path / 'scribe.json'
    p.write_text('{"words": []}', encoding='utf-8')
    with pytest.raises(RuntimeError):
        ul.labeled_words('2099-01-01', p, tmp_path / 'missing.mp3', 'x')
