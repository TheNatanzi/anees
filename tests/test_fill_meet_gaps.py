# -*- coding: utf-8 -*-
"""Meet gap filler (scripts/fill_meet_gaps.py): offset refinement, speaker choice, window clipping, queue idempotency,
rule S2 (raw files untouched), the builders' merge points and the hourly hook. No paid call is ever made: every test
uses a stub Scribe response built here."""
import hashlib, importlib, json, random, sys, types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fill_meet_gaps as F  # noqa: E402

POOL = ['كيفك', 'تمام', 'بدي', 'روح', 'عالشغل', 'اليوم', 'مبارح', 'كتير', 'حلو', 'شو', 'عملت', 'بالبيت', 'ركبتي', 'بتوجعني',
        'الدكتور', 'دوا', 'راسي', 'عيوني', 'إيدي', 'رجلي', 'بدلة', 'قميص', 'صباط', 'لون', 'أزرق', 'أحمر', 'عرس', 'بنطلون',
        'كنت', 'رحت', 'شفت', 'حكيت', 'بعرف', 'مش', 'هلق', 'بكرا', 'السوق', 'غالي', 'رخيص', 'okay', 'yeah', 'doctor', 'wedding',
        'suit', 'shoes', 'because', 'really', 'maybe', 'نشوف', 'غلطاتي', 'مساعدة', 'بعت', 'يوم', 'واحد', 'تعبان', 'نمت', 'منيح']
WINDOW = {'from_s': 0.0, 'to_s': 1217.0, 'from': '00:00', 'to': '20:17'}
MEET_NAME = 'rvn-mpoe-zat (2026-09-26 14 33 GMT-7)'
START = '2026-09-26T14:35:19-07:00'           # lesson clock 0 -> initial offset 139 s after the Meet file's 14:33
TRUE_OFF = 116.4                               # the Meet recording really started at 14:33:22.6


def w(text, s, spk, lp=-0.05):
    return {'text': text, 'start': round(s, 3), 'end': round(s + 0.3, 3), 'type': 'word', 'speaker_id': spk, 'logprob': lp}


def synth(seed=1, true_off=TRUE_OFF, clip_start=19.0, clip_end=1416.0, present='Medi', swap=False, mislabel=0.05, jitter=0.05):
    """(lesson doc turns, stub Scribe response on the CLIP clock, [(lesson_t, text)] of the missing side inside the window)."""
    rnd = random.Random(seed)
    missing = 'Amal' if present == 'Medi' else 'Medi'
    ps, ms = ('speaker_1', 'speaker_0') if swap else ('speaker_0', 'speaker_1')
    turns, words, truth = [], [], []
    t = 4.0
    while t < WINDOW['to_s'] + 300:
        k = rnd.randint(2, 6)
        toks = [rnd.choice(POOL) for _ in range(k)]
        total = sum(len(x) for x in toks)
        dur = 0.4 * k
        turns.append({'t': round(t, 2), 'end': round(t + dur, 2), 'who': present, 'text': ' '.join(toks)})
        acc = 0
        for x in toks:                             # the Meet engine hears the same words, on its own clock
            s = t + dur * acc / total + true_off - clip_start + rnd.gauss(0, jitter)
            acc += len(x)
            words += [w(x, s, ms if rnd.random() < mislabel else ps), {'text': ' ', 'type': 'spacing'}]
        t += dur + rnd.uniform(1.5, 4.0)
        k = rnd.randint(2, 7)
        toks = [rnd.choice(POOL) for _ in range(k)]
        for i, x in enumerate(toks):
            s = t + 0.35 * i
            words += [w(x, s + true_off - clip_start, ms), {'text': ' ', 'type': 'spacing'}]
            if WINDOW['from_s'] <= s < WINDOW['to_s']:
                truth.append((round(s, 3), x))
        if t >= WINDOW['to_s']:                    # after the gap both tracks exist: her lines are on the page too
            turns.append({'t': round(t, 2), 'end': round(t + 0.35 * k, 2), 'who': missing, 'text': ' '.join(toks)})
        t += 0.35 * k + rnd.uniform(1.5, 4.0)
    words = [x for x in words if x['type'] != 'word' or 0 <= x['start'] <= clip_end - clip_start]
    return turns, {'language_code': 'ara', 'language_probability': 0.9, 'text': '...', 'words': words}, truth


# ------------------------------------------------------------------ pure pieces

def test_initial_offset_and_clip_bounds_from_names():
    ls = F.dt.datetime.fromisoformat(START)
    off0 = F.initial_offset(MEET_NAME, ls)
    assert off0 == 139.0
    assert F.clip_bounds(WINDOW, off0) == (19.0, 1416.0)       # gap + the name's 60 s uncertainty + 60 s margin each side
    ls23 = F.dt.datetime.fromisoformat('2026-09-23T14:36:12-07:00')
    off23 = F.initial_offset('qxg-xokk-ufg (2026-09-23 14 35 GMT-7)', ls23)
    assert off23 == 72.0 and F.clip_bounds({'from_s': 0, 'to_s': 1425}, off23) == (0.0, 1557.0)


def test_offset_refinement_recovers_the_true_offset():
    turns, scribe, _ = synth()
    fit = F.fit_offset(F.present_tokens(turns, 'Medi'), F.meet_words(scribe, 19.0), 139.0)
    assert fit['ok'], fit
    assert abs(fit['offset_s'] - TRUE_OFF) < 0.1
    assert fit['residual_s'] < 0.15 and fit['anchors'] >= 50 and fit['basis'] == 'first word of each line'


def test_offset_refinement_refuses_an_unrelated_recording():
    turns, _, _ = synth(seed=1)
    _, other, _ = synth(seed=99, true_off=40.0)                # another lesson's words: nothing lines up
    other['words'] = [x for x in other['words'] if x['type'] != 'word' or x['text'] not in {'okay', 'yeah'}][:40]
    fit = F.fit_offset(F.present_tokens(turns, 'Medi'), F.meet_words(other, 19.0), 139.0)
    assert not fit['ok']


@pytest.mark.parametrize('swap', [False, True])
def test_speaker_selection_picks_the_speaker_who_does_not_match(swap):
    turns, scribe, _ = synth(swap=swap)
    present, mw = F.present_tokens(turns, 'Medi'), F.meet_words(scribe, 19.0)
    fit = F.fit_offset(present, mw, 139.0)
    spk = F.choose_speakers(present, mw, fit['offset_s'], WINDOW)
    assert spk['ok']
    assert spk['present_speaker'] == ('speaker_1' if swap else 'speaker_0')
    assert spk['missing_speaker'] == ('speaker_0' if swap else 'speaker_1')
    assert spk['confidence'] > 0.85                              # 5 % of his words were mislabelled on purpose


def test_window_clipping_keeps_only_the_missing_side_inside_the_gap():
    turns, scribe, truth = synth(mislabel=0.0)
    present, mw = F.present_tokens(turns, 'Medi'), F.meet_words(scribe, 19.0)
    fit = F.fit_offset(present, mw, 139.0)
    words, lines, dropped = F.select_missing(mw, present, fit['offset_s'], WINDOW, 'speaker_1', 'Amal', 0.95)
    assert all(WINDOW['from_s'] <= x['s'] < WINDOW['to_s'] for x in words)
    assert len(words) + dropped == len(truth) and dropped <= 2
    got = {(round(x['s'], 1), x['text']) for x in words}
    assert sum(1 for s, t in truth if (round(s, 1), t) in got or (round(s + 0.1, 1), t) in got or (round(s - 0.1, 1), t) in got) >= len(truth) - 2
    assert lines and all(L['who'] == 'Amal' and L['from_meet'] and L['source'] == 'meet_mixed' for L in lines)
    assert all(0 < L['confidence'] <= 1 for L in lines)
    assert sum(L['n_words'] for L in lines) == len(words)


def test_a_word_heard_on_both_labels_at_once_is_dropped():
    present = [(100.0, F.norm('تمام'), True)]
    mw = [{'s': 100.1 + 50, 'e': 100.4 + 50, 'text': 'تمام', 'n': F.norm('تمام'), 'spk': 'B', 'lp': None},
          {'s': 103.0 + 50, 'e': 103.3 + 50, 'text': 'تمام', 'n': F.norm('تمام'), 'spk': 'B', 'lp': None}]
    words, lines, dropped = F.select_missing(mw, present, 50.0, WINDOW, 'B', 'Amal', 0.9)
    assert dropped == 1 and [x['s'] for x in words] == [103.0]    # her real echo 3 s later is kept


# ------------------------------------------------------------------ one entry end to end (stub transcript)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture
def world(tmp_path):
    turns, scribe, truth = synth()
    drive = tmp_path / 'drive'
    meet = drive / 'Google Meet' / 'rvn-mpoe-zat - 2026 09 26 14 33 PDT' / MEET_NAME
    meet.parent.mkdir(parents=True)
    meet.write_bytes(b'not really an mp4')
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / '2026-09-26.json').write_text(json.dumps({'turns': turns}, ensure_ascii=False), encoding='utf-8')
    lj = tmp_path / 'lessons.json'
    lj.write_text(json.dumps({'lessons': [{'date': '2026-09-26', 'start_local': START, 'start_source': 'tracks.json', 'duration_min': 69.8}]}), encoding='utf-8')
    raw = tmp_path / 'raw'
    (raw / '2026-09-26').mkdir(parents=True)
    for who in ('Medi', 'Amal'):                                   # the raw per-person transcripts (rule S2: never touched)
        (raw / '2026-09-26' / f'scribe_{who}.json').write_text(json.dumps({'words': [w('x', 1, 'speaker_0')]}), encoding='utf-8')
    q = tmp_path / 'meet_gaps.json'
    queue = {'entries': []}
    F.ensure_entry(queue, '2026-09-26', 'amal', 0, 1217, 'Google Meet/rvn-mpoe-zat - 2026 09 26 14 33 PDT/' + MEET_NAME)
    F.ensure_entry(queue, '2026-09-26', 'amal', 0, 1217, 'dup')   # seeding twice adds nothing
    assert len(queue['entries']) == 1
    F.save(q, queue)
    calls = []

    def transcribe(path, minutes, who=None):
        calls.append((Path(path).name, round(minutes, 2)))
        return json.loads(json.dumps(scribe))

    def cutter(src, dst, a, b):
        calls.append(('cut', a, b))
        Path(dst).write_bytes(b'clip')

    kw = dict(drive=drive, raw=raw, layers=tmp_path / 'gapfill', lessons_json=lj, lesson_docs=docs, transcribe=transcribe,
              cutter=cutter, ffmpeg=True, budget_ok=lambda s, usd: True)
    return types.SimpleNamespace(q=q, kw=kw, calls=calls, raw=raw, docs=docs, truth=truth, tmp=tmp_path, scribe=scribe, meet=meet)


def test_process_queue_fills_once_and_is_idempotent(world):
    r1 = F.process_queue(world.q, **world.kw)
    assert r1['done'] == ['2026-09-26-amal'] and r1['changed']
    assert world.calls[0] == ('cut', 19.0, 1416.0) and world.calls[1][0] == 'gapfill_amal.clip.mp3'
    e = json.loads(world.q.read_text(encoding='utf-8'))['entries'][0]
    assert e['status'] == 'done' and abs(e['result']['offset_s'] - TRUE_OFF) < 0.1 and e['result']['clip_mode'] == 'ffmpeg_cut'
    layer = json.loads((world.tmp / 'gapfill' / '2026-09-26' / 'gapfill_amal.json').read_text(encoding='utf-8'))
    pv = layer['provenance']
    assert layer['side'] == 'Amal' and layer['source'] == 'meet_mixed' and len(pv['parts']) == 1
    assert pv['meet_file_name'] == MEET_NAME and pv['meet_sha256'] == sha(world.meet)
    assert pv['parts'][0]['scribe_raw']['sha256'] == sha(world.raw / '2026-09-26' / 'gapfill_amal.scribe.json')
    assert pv['diarization']['missing_speaker'] == 'speaker_1' and pv['residual_s'] < 0.15
    assert all(L['from_meet'] and L['source'] == 'meet_mixed' and 'confidence' in L for L in layer['lines'])
    assert all(0 <= x['s'] < 1217 for x in layer['words'])
    before = world.q.read_bytes()
    r2 = F.process_queue(world.q, **world.kw)                       # the next hour: nothing pending, nothing paid
    assert r2 == {'done': [], 'failed': [], 'pending': [], 'changed': False}
    assert world.q.read_bytes() == before and len([c for c in world.calls if c[0] != 'cut']) == 1


def test_raw_transcripts_and_page_data_are_never_edited(world):
    watched = [world.raw / '2026-09-26' / 'scribe_Medi.json', world.raw / '2026-09-26' / 'scribe_Amal.json',
               world.docs / '2026-09-26.json']
    before = {p: sha(p) for p in watched}
    F.process_queue(world.q, **world.kw)
    assert {p: sha(p) for p in watched} == before
    new = sorted(p.name for p in (world.raw / '2026-09-26').iterdir())
    assert new == ['gapfill_amal.clip.mp3', 'gapfill_amal.scribe.json', 'scribe_Amal.json', 'scribe_Medi.json']


def test_saved_response_is_reused_never_paid_twice(world):
    F.process_queue(world.q, **world.kw)
    q = json.loads(world.q.read_text(encoding='utf-8'))
    q['entries'][0]['status'] = 'pending'                          # e.g. a person re-queues it after a builder fix
    F.save(world.q, q)
    r = F.process_queue(world.q, **world.kw)
    assert r['done'] == ['2026-09-26-amal']
    assert len([c for c in world.calls if c[0] != 'cut']) == 1


def test_whole_file_mode_without_ffmpeg(world):
    turns, scribe0, _ = synth(clip_start=0.0, clip_end=5000.0)
    world.kw['transcribe'] = lambda path, minutes, who=None: (world.calls.append((Path(path).name, minutes)), scribe0)[1]
    world.kw['ffmpeg'] = False
    r = F.process_queue(world.q, **world.kw)
    assert r['done']
    layer = json.loads((world.tmp / 'gapfill' / '2026-09-26' / 'gapfill_amal.json').read_text(encoding='utf-8'))
    assert layer['provenance']['clip']['mode'] == 'whole_file' and abs(layer['provenance']['offset_s'] - TRUE_OFF) < 0.1
    assert world.calls[-1][0] == MEET_NAME                          # the Meet file itself went to Scribe


def test_no_key_budget_or_missing_file_leave_the_entry_pending_and_untouched(world, monkeypatch):
    before = world.q.read_bytes()
    kw = dict(world.kw)
    kw.pop('transcribe')
    monkeypatch.setattr(F, 'paid_call_possible', lambda: False)
    monkeypatch.setattr(F, 'scribe_call', lambda *a, **k: pytest.fail('a paid call was attempted'))
    assert F.process_queue(world.q, **kw) == {'done': [], 'failed': [], 'pending': ['2026-09-26-amal'], 'changed': False}
    assert F.process_queue(world.q, **{**world.kw, 'budget_ok': lambda s, usd: False})['pending'] == ['2026-09-26-amal']
    world.meet.unlink()
    assert F.process_queue(world.q, **world.kw)['pending'] == ['2026-09-26-amal']
    assert world.q.read_bytes() == before and not [c for c in world.calls if c[0] != 'cut']


def test_a_bad_alignment_counts_attempts_then_fails_without_paying_again(world):
    junk = {'words': [w('zzz', 10 + i, 'speaker_0') for i in range(30)]}
    world.kw['transcribe'] = lambda path, minutes, who=None: (world.calls.append(('paid',)), junk)[1]
    for i in range(F.MAX_ATTEMPTS):
        F.process_queue(world.q, **world.kw)
    e = json.loads(world.q.read_text(encoding='utf-8'))['entries'][0]
    assert e['status'] == 'failed' and e['attempts'] == F.MAX_ATTEMPTS and 'alignment failed' in e['last_error']
    assert world.calls.count(('paid',)) == 1
    assert not (world.tmp / 'gapfill' / '2026-09-26' / 'gapfill_amal.json').exists()


def test_the_seeded_queue_names_both_known_gaps():
    q = F.load_queue()
    got = {e['id']: (e['missing'], e['window']['from_s'], e['window']['to_s']) for e in q['entries']}
    assert got['2026-09-26-amal'] == ('amal', 0.0, 1217.0) and got['2026-09-23-medi'] == ('medi', 0.0, 1425.0)
    assert all(F.MEET_NAME.search(e['meet_file']) for e in q['entries'])
    pref = {e['id']: e.get('prefer') for e in q['entries']}
    assert pref == {'2026-09-26-amal': None, '2026-09-23-medi': 'own_track'}   # Sep 23: his own first recording first


# ------------------------------------------------------------------ own track first (Sep 23 shape), Meet for the rest

TRACK_OFF, TRACK_DUR = 0.5, 1100.0            # his first recording covers 0:00.5-18:20.5; 18:20.5-20:17 is left for Meet


@pytest.fixture
def world23(tmp_path):
    turns, _, truth = synth(present='Amal')
    drive = tmp_path / 'drive'
    meet = drive / 'Google Meet' / 'x' / MEET_NAME
    meet.parent.mkdir(parents=True)
    meet.write_bytes(b'mp4')
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / '2026-09-26.json').write_text(json.dumps({'turns': turns}, ensure_ascii=False), encoding='utf-8')
    lj = tmp_path / 'lessons.json'
    lj.write_text(json.dumps({'lessons': [{'date': '2026-09-26', 'start_local': START, 'duration_min': 69.8}]}), encoding='utf-8')
    raw = tmp_path / 'raw'
    tdir = raw / '2026-09-26' / 'tracks'
    tdir.mkdir(parents=True)
    for name in ('Medi_Natanzi.mp3', 'Medi_Natanzi_2.mp3', 'Amal.mp3'):
        (tdir / name).write_bytes(b'mp3')
    tracks = [{'participant': 'Amal', 'start': {'relative': 0.3}, 'duration_s': 4000, 'file': 'C:/elsewhere/Amal.mp3'},
              {'participant': 'Medi Natanzi', 'start': {'relative': TRACK_OFF}, 'duration_s': TRACK_DUR, 'file': 'C:/elsewhere/Medi_Natanzi.mp3'},
              {'participant': 'Medi Natanzi', 'start': {'relative': 1423.4}, 'duration_s': 2500, 'file': 'C:/elsewhere/Medi_Natanzi_2.mp3'}]
    (tdir / 'tracks.json').write_text(json.dumps({'tracks': tracks}), encoding='utf-8')
    (raw / '2026-09-26' / 'scribe_Medi.provenance.json').write_text(json.dumps({'source_file': 'C:/elsewhere/Medi_Natanzi_2.mp3'}), encoding='utf-8')
    q = tmp_path / 'meet_gaps.json'
    queue = {'entries': []}
    e, _ = F.ensure_entry(queue, '2026-09-26', 'medi', 0, 1217, 'Google Meet/x/' + MEET_NAME)
    e['prefer'] = 'own_track'
    F.save(q, queue)
    calls, cut = [], {}
    own = {'words': [w(x, s - TRACK_OFF, 'speaker_0') for s, x in truth if s < TRACK_OFF + TRACK_DUR]}

    def transcribe(path, minutes, who=None):
        calls.append((Path(path).name, who))
        if who == 'Medi':
            return json.loads(json.dumps(own))
        return synth(present='Amal', clip_start=cut['a'], clip_end=cut['b'])[1]

    def cutter(src, dst, a, b):
        cut.update(a=a, b=b)
        calls.append(('cut', a, b))
        Path(dst).write_bytes(b'clip')

    kw = dict(drive=drive, raw=raw, layers=tmp_path / 'gapfill', lessons_json=lj, lesson_docs=docs, transcribe=transcribe,
              cutter=cutter, ffmpeg=True, budget_ok=lambda s, usd: True)
    return types.SimpleNamespace(q=q, kw=kw, calls=calls, raw=raw, tdir=tdir, truth=truth, tmp=tmp_path)


def test_find_own_track_skips_the_track_already_transcribed(world23):
    e = json.loads(world23.q.read_text(encoding='utf-8'))['entries'][0]
    trk, why = F.find_own_track(e, world23.raw)
    assert why is None and Path(trk['path']).name == 'Medi_Natanzi.mp3' and trk['offset_s'] == TRACK_OFF
    assert Path(trk['path']).parent == world23.tdir                  # tracks.json's absolute path is not on this machine


def test_own_track_first_then_meet_for_the_rest(world23):
    r = F.process_queue(world23.q, **world23.kw)
    assert r['done'] == ['2026-09-26-medi']
    rest_from = TRACK_OFF + TRACK_DUR
    assert world23.calls[0] == ('Medi_Natanzi.mp3', 'Medi')          # his own single-voice track, first
    assert world23.calls[1] == ('cut',) + F.clip_bounds({'from_s': rest_from, 'to_s': 1217.0}, 139.0)
    assert world23.calls[2][1] == 'mixed' and len(world23.calls) == 3
    layer = json.loads((world23.tmp / 'gapfill' / '2026-09-26' / 'gapfill_medi.json').read_text(encoding='utf-8'))
    own = [L for L in layer['lines'] if L['source'] == 'own_track']
    meet = [L for L in layer['lines'] if L['source'] == 'meet_mixed']
    assert own and meet and all(not L['from_meet'] and L['t'] < rest_from for L in own)
    assert all(L['from_meet'] and rest_from <= L['t'] < 1217 for L in meet)
    got = {(round(x['s'], 2), x['text']) for x in layer['words'] if x['source'] == 'own_track'}
    assert got == {(round(s, 2), x) for s, x in world23.truth if s < rest_from}     # on the lesson clock, nothing lost
    assert [p['source'] for p in layer['provenance']['parts']] == ['own_track', 'meet_mixed']
    assert abs(layer['provenance']['parts'][1]['offset_s'] - TRUE_OFF) < 0.1
    assert layer['summary']['primary_source'] == 'own_track' and layer['summary']['offset_s'] == TRACK_OFF
    e = json.loads(world23.q.read_text(encoding='utf-8'))['entries'][0]
    assert e['status'] == 'done' and len(e['run_ids']) == 2
    assert sorted(p.name for p in (world23.raw / '2026-09-26').glob('gapfill_*')) == [
        'gapfill_medi.meet_1100-1217.clip.mp3', 'gapfill_medi.meet_1100-1217.scribe.json', 'gapfill_medi.track.scribe.json']


def test_own_track_missing_falls_back_to_the_meet_clip(world23):
    (world23.tdir / 'Medi_Natanzi.mp3').unlink()
    r = F.process_queue(world23.q, **world23.kw)
    assert r['done'] == ['2026-09-26-medi']
    assert world23.calls[0] == ('cut', 19.0, 1416.0) and all(c[1] != 'Medi' for c in world23.calls)
    layer = json.loads((world23.tmp / 'gapfill' / '2026-09-26' / 'gapfill_medi.json').read_text(encoding='utf-8'))
    assert {L['source'] for L in layer['lines']} == {'meet_mixed'}
    assert 'missing on this machine' in layer['provenance']['own_track_fallback']


def test_meet_rest_with_no_speech_is_recorded_not_failed(world23):
    tr = world23.kw['transcribe']

    def no_medi_on_meet(path, minutes, who=None):
        if who == 'Medi':
            return tr(path, minutes, who)
        res = tr(path, minutes, who)
        return {'words': [x for x in res['words'] if x.get('speaker_id') != 'speaker_1']}
    world23.kw['transcribe'] = no_medi_on_meet
    r = F.process_queue(world23.q, **world23.kw)
    assert r['done'] == ['2026-09-26-medi']
    layer = json.loads((world23.tmp / 'gapfill' / '2026-09-26' / 'gapfill_medi.json').read_text(encoding='utf-8'))
    assert {L['source'] for L in layer['lines']} == {'own_track'}
    assert layer['provenance']['parts'][1]['status'] == 'nothing_filled'


def test_own_track_is_never_paid_twice(world23):
    F.process_queue(world23.q, **world23.kw)
    q = json.loads(world23.q.read_text(encoding='utf-8'))
    q['entries'][0]['status'] = 'pending'
    F.save(world23.q, q)
    F.process_queue(world23.q, **world23.kw)
    assert sum(1 for c in world23.calls if c[0] != 'cut') == 2


# ------------------------------------------------------------------ builders + hourly hook

@pytest.fixture
def page_builder(monkeypatch):
    fake_db = types.ModuleType('db')
    fake_db.select = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('offline test'))
    monkeypatch.setitem(sys.modules, 'db', fake_db)
    sys.modules.pop('build_lessons_page_data', None)
    mod = importlib.import_module('build_lessons_page_data')
    yield mod
    sys.modules.pop('build_lessons_page_data', None)


def layer_fixture():
    return {'side': 'Amal', 'window': WINDOW, 'provenance': {'offset_s': 116.4, 'residual_s': 0.05, 'meet_file_name': MEET_NAME,
                                                             'diarization': {'confidence': 0.93}},
            'lines': [{'t': 12.0, 'end': 13.1, 'who': 'Amal', 'text': 'كيفك اليوم', 'source': 'meet_mixed', 'from_meet': True, 'confidence': 0.9}],
            'words': [{'s': 12.0, 'e': 12.4, 'who': 'Amal', 'text': 'كيفك'}, {'s': 12.6, 'e': 13.1, 'who': 'Amal', 'text': 'اليوم'}]}


def test_lessons_builder_merges_the_layer_as_tagged_lines(page_builder, tmp_path):
    B = page_builder
    d = tmp_path / '2026-09-26'
    d.mkdir()
    (d / 'gapfill_amal.json').write_text(json.dumps(layer_fixture(), ensure_ascii=False), encoding='utf-8')
    layers = B.gapfill_layers('2026-09-26', root=str(tmp_path))
    P = [{'t': 10.0, 'who': 'Medi', 'text': 'مرحبا', 'row': 'r:row:0', 'chat': False},
         {'t': 14.0, 'who': 'Medi', 'text': 'تمام', 'row': 'r:row:1', 'chat': False}]
    M = B.with_gapfill(P, layers)
    assert [p['t'] for p in M] == [10.0, 12.0, 14.0] and M[0] is P[0] and M[2] is P[1]
    assert M[1]['from_meet'] and M[1]['source'] == 'meet_mixed' and M[1]['who'] == 'Amal' and M[1]['row'] is None
    W = B.gapfill_words(layers)
    assert [x['kind'] for x in W] == ['word', 'word'] and all(x['from_meet'] for x in W)
    fills = B.gapfill_summary(layers)
    assert fills[0]['side'] == 'Amal' and fills[0]['lines'] == 1 and fills[0]['diarization_confidence'] == 0.93
    assert 'filled from the Meet recording' in B.gapfill_note(fills)
    assert B.with_gapfill(P, []) is P                               # no layer -> the page lines exactly as before
    two = {**layer_fixture(), 'side': 'Medi', 'window': {'from_s': 0, 'to_s': 1425, 'from': '00:00', 'to': '23:45'},
           'summary': {'diarization_confidence': 0.9},
           'provenance': {'parts': [{'source': 'own_track', 'window': {'from_s': 0.5, 'to_s': 1357, 'from': '00:00', 'to': '22:37'}},
                                    {'source': 'meet_mixed', 'window': {'from_s': 1357, 'to_s': 1425, 'from': '22:37', 'to': '23:45'}}]},
           'lines': [{'t': 5.0, 'who': 'Medi', 'text': 'a', 'source': 'own_track', 'from_meet': False, 'confidence': 0.9},
                     {'t': 1400.0, 'who': 'Medi', 'text': 'b', 'source': 'meet_mixed', 'from_meet': True, 'confidence': 0.8}]}
    M = B.with_gapfill([], [two])
    assert [(p['source'], p['from_meet'], p['gap_fill']) for p in M] == [('own_track', False, True), ('meet_mixed', True, True)]
    note = B.gapfill_note(B.gapfill_summary([two]))
    assert '00:00-22:37 filled from own recording' in note and '22:37-23:45 filled from the Meet recording (1 lines' in note


def test_sentence_ladder_carries_from_meet_to_its_sentences():
    L = importlib.import_module('build_sentence_ladder')
    turns = [{'t': 1.0, 'end': 3.0, 'who': 'Amal', 'text': 'كيفك اليوم؟', 'from_meet': True},
             {'t': 5.0, 'end': 7.0, 'who': 'Medi', 'text': 'أنا تمام كتير.'}]
    S = L.build_sentences(turns)
    assert [bool(s.get('from_meet')) for s in S] == [True, False]


def test_hourly_hook_never_raises(monkeypatch, tmp_path):
    import hourly_lessons as H
    monkeypatch.setattr(F, 'process_queue', lambda **k: (_ for _ in ()).throw(RuntimeError('boom')))
    assert H.gap_fill_refresh(tmp_path, no_push=True) is None
    monkeypatch.setattr(F, 'process_queue', lambda **k: {'done': [], 'failed': [], 'pending': ['x'], 'changed': False})
    monkeypatch.setattr(H.subprocess, 'run', lambda *a, **k: pytest.fail('nothing changed: no build, no git'))
    assert H.gap_fill_refresh(tmp_path, no_push=True)['pending'] == ['x']
    monkeypatch.setattr(F, 'process_queue', lambda **k: {'done': ['d'], 'failed': [], 'pending': [], 'changed': True})
    monkeypatch.setattr(H.subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(OSError('no git')))
    assert H.gap_fill_refresh(tmp_path, no_push=True) is None
