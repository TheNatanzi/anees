"""Load one lesson end to end from its SAVED transcripts (no provider call here, ever).

  python scripts/load_lesson.py 2026-09-21 --raw C:/dev/anees/data/lessons/2026-09-21 --work <scratch dir> [--meet "<Meet recording file>"] [--apply] [--page-only]

Two shapes of raw lesson folder:
  tracks  tracks/tracks.json + scribe_Amal.json + scribe_Medi.json   (Recall bot, one file per person)
  mixed   audio.mp3 + scribe.json                                     (host's Meet recording only; speakers ESTIMATED)

Steps: transcript rows (sync_speaking_lesson.source_rows) -> detected Word Bank events -> guard flags -> lesson audio mix ->
public page with Amal's typed chat lines (build_lesson_page) -> with --apply: insert-only events + lessons row.
Existing events are never changed (sync_word_bank_evidence.sync_events refuses). Nothing is emailed or sent.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_lesson_page as page  # noqa: E402

ROOT = HERE.parent
PAGES_DIR = ROOT / 'docs' / 'lessons'


def ffprobe_duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def select_tracks(manifest, raw):
    """One track per person: the one whose saved transcript has the same length. Others are listed as not transcribed."""
    import sync_speaking_lesson as S
    stitched = raw / 'tracks' / 'stitched.json'
    chosen, omitted = {}, []
    for who in ('Amal', 'Medi'):
        resp = S.read(raw / f'scribe_{who}.json')
        options = [t for t in manifest['tracks'] if _person(t['participant']) == who]
        if who == 'Medi' and stitched.exists():
            st = S.read(stitched)
            t = {'participant': 'Medi Natanzi', 'start': st['stitched']['start'], 'duration_s': st['stitched']['duration_s'],
                 'file': str(raw / 'tracks' / 'Medi_Natanzi-stitched.mp3'), 'gap_s': st.get('gap_s')}
            chosen[who] = t
            continue
        match = [t for t in options if abs((t.get('duration_s') or 0) - resp['audio_duration_secs']) < 2]
        if len(match) != 1:
            raise ValueError(f'{who}: {len(match)} tracks match the saved transcript length')
        t = dict(match[0]); t['file'] = str(raw / 'tracks' / Path(match[0]['file']).name)
        chosen[who] = t
        omitted += [o for o in options if o is not match[0]]
    return chosen, omitted


def _clock(seconds):
    s = int(round(seconds))
    return f'{s // 60}:{s % 60:02d}'


def _person(name):
    low = str(name).lower()
    if 'amal' in low:
        return 'Amal'
    if any(n in low for n in ('medi', 'mahdi', 'natanzi')):
        return 'Medi'
    return None          # the host account (e.g. 'Ray Adib' = wc@adibs.com) records silence; never a speaker


def build_tracks(date, raw, work):
    import sync_speaking_lesson as S
    manifest = S.read(raw / 'tracks' / 'tracks.json')
    chosen, omitted = select_tracks(manifest, raw)
    (work / 'tracks').mkdir(parents=True, exist_ok=True)
    for who in chosen:
        shutil.copy2(raw / f'scribe_{who}.json', work / f'scribe_{who}.json')
    S.save(work / 'tracks' / 'tracks.json', {**manifest, 'tracks': [chosen['Amal'], chosen['Medi']]})
    data = S.build_transcript(date, lesson_dir=work, write=True)
    ranges = {who: (t['start']['relative'], t['start']['relative'] + t['duration_s']) for who, t in chosen.items()}
    audio = [(Path(t['file']), t['start']['relative']) for t in chosen.values()]
    extra = add_segments(date, raw, data, omitted)
    audio += [(Path(s['file']), s['start']['relative']) for s in extra]
    for s in extra:
        who = _person(s['participant']); lo, hi = ranges[who]
        ranges[who] = (min(lo, s['start']['relative']), max(hi, s['start']['relative'] + s['duration_s']))
    omitted = [o for o in omitted if not any(abs(o['start']['relative'] - s['start']['relative']) < 1 and _person(o['participant']) == _person(s['participant']) for s in extra)]
    return data, {'kind': 'tracks', 'ranges': ranges, 'omitted': omitted, 'audio': audio, 'chosen': chosen, 'extra_segments': extra}


OVERLAP_TOL_S = 0.8     # a segment word with the same text as the same person's word this close = one spoken word
DUP_SHARE = 0.5         # a segment row whose words are at least this share duplicates is the same speech, heard twice


def _norm_word(t):
    import re
    return re.sub(r'[^\w]', '', str(t or '').lower())


def dedupe_rows(rows, existing):
    """Rule TR-17: two recordings of one person can overlap for a moment (the old connection still open while the new
    one starts). A segment row whose words are mostly the same words at the same lesson time as that person's rows
    already in the transcript is the same speech heard twice: it is dropped (returned second). Rows are kept whole, so
    every item id still points at its raw response index (RULES.md S2)."""
    import bisect, collections
    have = collections.defaultdict(list)
    for r in existing:
        for i in r['items']:
            if i.get('type') == 'word' and i.get('timeline_start') is not None:
                have[(r['speaker_label'], _norm_word(i['text']))].append(i['timeline_start'])
    for v in have.values():
        v.sort()

    def dup(r, i):
        ts = have.get((r['speaker_label'], _norm_word(i['text'])))
        if not ts:
            return False
        k = bisect.bisect_left(ts, i['timeline_start'] - OVERLAP_TOL_S)
        return k < len(ts) and ts[k] <= i['timeline_start'] + OVERLAP_TOL_S

    keep, dropped = [], []
    for r in rows:
        words = [i for i in r['items'] if i.get('type') == 'word' and i.get('timeline_start') is not None]
        n = sum(dup(r, i) for i in words)
        (dropped if words and n / len(words) >= DUP_SHARE else keep).append(r)
    return keep, dropped


def segment_tracks(raw, manifest=None):
    """{file name: track entry} of every recording a segment transcript may come from: the reconnect recordings recovered
    by hand (tracks/recovered/recovery.json, 09-15..09-17) and every recording in tracks/tracks.json (rule TR-17: the
    hourly job transcribes each person's other recordings as scribe_<who>_seg<start>.json)."""
    import sync_speaking_lesson as S
    out = {}
    tj = raw / 'tracks' / 'tracks.json'
    for t in (manifest or (S.read(tj) if tj.exists() else {})).get('tracks') or []:
        f = raw / 'tracks' / Path(t['file']).name
        out[f.name] = {**t, 'file': str(f)}
    rec = raw / 'tracks' / 'recovered' / 'recovery.json'
    for t in (S.read(rec)['recovered'] if rec.exists() else []):
        f = raw / 'tracks' / 'recovered' / Path(t['file']).name
        out[f.name] = {**t, 'file': str(f)}
    return out


def add_segments(date, raw, data, omitted):
    """Every other recording of a person (a reconnect: rule TR-17), transcribed as scribe_<who>_seg<start>.json, joins the
    transcript as its own source (page + events), placed on the lesson clock by its OWN start offset (tracks.json
    start.relative). Rows that repeat speech already in the transcript (overlapping recordings) are dropped
    (dedupe_rows). Returns the segment track entries used."""
    import sync_speaking_lesson as S
    tracks = segment_tracks(raw)
    used = []
    for resp_path in sorted(raw.glob('scribe_*_seg*.json')):
        if resp_path.name.endswith('.provenance.json'):
            continue
        prov = S.read(resp_path.with_name(resp_path.stem + '.provenance.json'))
        seg = tracks.get(Path(prov['source_file']).name)
        if seg is None:
            raise ValueError(f'{resp_path.name}: its recording {Path(prov["source_file"]).name} is in neither tracks.json nor recovery.json')
        sha = S.filehash(seg['file'])
        assert sha == prov['source_sha256'] and seg.get('sha256', sha) == sha, f'{resp_path.name}: recording changed since it was transcribed'
        seg = {**seg, 'sha256': sha}
        who = _person(seg['participant'])
        sid = f'anees-{date.replace("-", "")}-recall-{who.lower()}-seg{int(seg["start"]["relative"])}'
        response = S.read(resp_path)
        offset = seg['start']['relative']
        if not any(w.get('type') == 'word' for w in response.get('words') or []):
            used.append(seg)                 # transcribed, silent: nothing to add, but no longer "not transcribed"
            continue
        data['sources'][sid] = {'id': sid, 'speaker_label': who, 'speaker_basis': 'participant_track_not_voice_verified',
                                'source_sha256': sha, 'response_sha256': S.filehash(resp_path), 'input_path': seg['file'],
                                'file_uri': Path(seg['file']).as_uri(), 'bytes': Path(seg['file']).stat().st_size,
                                'track_offset_s': offset, 'duration_s': response.get('audio_duration_secs'),
                                'language_code': response.get('language_code'), 'response_path': str(resp_path),
                                'asr_mode': {'model': 'scribe_v2', 'requested_language': response.get('language_code') or 'auto', 'keyterms_count': 0}}
        keep, dropped = dedupe_rows(S.source_rows(sid, who, offset, response), data['rows'])
        if dropped:
            data['sources'][sid]['overlap_rows_dropped'] = [r['id'] for r in dropped]
        data['rows'].extend(keep)
        used.append(seg)
    data['rows'].sort(key=lambda r: (r['timeline_start'] is None, r['timeline_start'] or 0, r['source_id'], r['items'][0]['index']))
    return used


def name_clusters(clusters, pitch, min_share=0.75):
    """Name the speech engine's voice clusters by VOICE PITCH (Medi low, Amal high), not by who speaks more Arabic.
    2026-09-18: the Arabic-share rule swapped the two voices (pitch agreed on 8.7% of words). A cluster whose pitched words
    are >= min_share one person gets that name; otherwise it returns no name and each word keeps its own pitch label."""
    votes = collections.defaultdict(collections.Counter)
    for c, p in zip(clusters, pitch):
        if p in ('Medi', 'Amal'):
            votes[c][p] += 1
    names = {}
    for c, v in votes.items():
        who, n = v.most_common(1)[0]
        if n / sum(v.values()) >= min_share:
            names[c] = who
    if len(set(names.values())) == 2 and len(names) == len(set(clusters)):
        return names, 'diarization_named_by_pitch'
    return {c: names[c] for c in names if list(names.values()).count(names[c]) == 1}, 'pitch_estimate'


def build_mixed(date, raw, work):
    """Host's Meet recording: one audio file, voices told apart by Scribe's diarization or, if that failed, voice pitch."""
    import lesson_pipeline as lp
    import sync_speaking_lesson as S
    res = S.read(raw / 'scribe.json')
    mp3 = raw / 'audio.mp3'
    words = [{'s': w.get('start', 0), 'e': w.get('end', 0), 'spk': w.get('speaker_id', '?'), 'w': w['text']}
             for w in res['words'] if w.get('type') == 'word']
    clusters = [w['spk'] for w in words]
    lp.pitch_labels(words, mp3)                        # words[i]['spk'] is now 'Medi' | 'Amal' | '?' by voice pitch
    lab, basis = name_clusters(clusters, [w['spk'] for w in words])
    word_labels = iter(lab.get(c) or p for c, p in zip(clusters, (w['spk'] for w in words)))
    labels = [next(word_labels) if w.get('type') == 'word' else None for w in res['words']]
    # spacing/audio events take the label of the nearest word before them
    last = '?'
    for i, l in enumerate(labels):
        if l is None:
            labels[i] = last
        else:
            last = l
    duration = ffprobe_duration(mp3)
    sources, rows = {}, []
    for who in ('Amal', 'Medi', 'Unknown'):
        want = {'Unknown': '?'}.get(who, who)
        part = {**{k: v for k, v in res.items() if k != 'words'}, 'words': [w for w, l in zip(res['words'], labels) if l == want],
                'derived_from': 'scribe.json', 'speaker_basis': basis}
        if not any(w.get('type') == 'word' for w in part['words']):
            continue
        path = work / f'scribe_{who}.json'
        S.save(path, part)
        sid = f'anees-{date.replace("-", "")}-meet-{who.lower()}'
        sources[sid] = {'id': sid, 'speaker_label': who, 'speaker_basis': basis, 'source_sha256': S.filehash(mp3),
                        'response_sha256': S.filehash(path), 'input_path': str(mp3), 'file_uri': mp3.as_uri(), 'bytes': mp3.stat().st_size,
                        'track_offset_s': 0.0, 'duration_s': duration, 'language_code': res.get('language_code'), 'response_path': str(path),
                        'asr_mode': {'model': 'scribe_v2', 'requested_language': res.get('language_code') or 'auto', 'keyterms_count': 0}}
        new = S.source_rows(sid, who, 0.0, part)
        for r in new:
            r['speaker_basis'] = basis
        rows += new
    rows.sort(key=lambda r: (r['timeline_start'] is None, r['timeline_start'] or 0, r['source_id']))
    data = {'schema_version': 1, 'kind': 'anees-working-transcript', 'lesson': date,
            'built_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'unreviewed_asr',
            'sources': sources, 'rows': rows, 'context_findings': None,
            'policy': {'raw_evidence_unchanged': True, 'automatic_translation': False, 'automatic_transliteration': False,
                       'human_confirmed': False, 'timeline': 'Meet recording clock; speakers estimated (' + basis + ')'}}
    S.save(work / 'speaking-evidence.json', data)
    counts = collections.Counter(l for l, w in zip(labels, res['words']) if w.get('type') == 'word')
    unlabeled = counts.get('?', 0) / max(1, sum(counts.values()))
    amal_rows = [r for r in rows if r['speaker_label'] == 'Amal' and r['timeline_start'] is not None]
    ranges = {'Amal': (amal_rows[0]['timeline_start'], amal_rows[-1]['timeline_end'])} if amal_rows else {'Amal': (0, 0)}
    return data, {'kind': 'mixed', 'ranges': ranges, 'omitted': [], 'audio': [(mp3, 0.0)], 'basis': basis,
                  'word_labels': dict(counts), 'unlabeled_share': round(unlabeled, 3)}


def guard_events(events, data, info):
    """Same guards as the 09-14/09-19 loads: Medi evidence outside Amal's recorded interval, or inside a learner audio gap,
    is kept but withheld (unresolved) -- never credited."""
    lookup = {i['id']: (r, i) for r in data['rows'] for i in r['items']}
    flagged = 0
    amal = info['ranges']['Amal']
    gap = None
    medi = info.get('chosen', {}).get('Medi') or {}
    if medi.get('gap_s'):
        st = json.loads((Path(medi['file']).parent / 'stitched.json').read_text(encoding='utf-8'))
        a, b = st['segments'][0], st['segments'][1]
        gap = (a['start']['relative'] + a['duration_s'], b['start']['relative'])
    for e in events:
        bound = [lookup[i] for i in e['item_ids']]
        assert all(r['source_id'] == e['source_id'] and r['speaker_label'] == e['speaker'] for r, _ in bound)
        assert ' '.join(i['text'] for _, i in bound) == e['original_text']
        if e['speaker'] != 'Medi':
            continue
        if not (amal[0] <= e['t_start'] and e['t_end'] <= amal[1]):
            e.update(assessment='unresolved', needs_review=True, spoken=False,
                     reason='Tutor recording context unavailable for this interval; vocabulary assessment withheld'); flagged += 1
        elif gap and gap[0] - 2 <= e['t_start'] <= gap[1] + 2:
            e.update(assessment='unresolved', needs_review=True, spoken=False,
                     reason='Learner microphone reconnecting in this interval (audio gap); vocabulary assessment withheld'); flagged += 1
        elif info['kind'] == 'mixed' and e.get('assessment') not in ('unresolved',):
            e['needs_review'] = True
    assert len({e['id'] for e in events}) == len(events)
    return flagged


WITHHELD = 'Tutor recording context unavailable for this interval; vocabulary assessment withheld'
EVENT_KEYS = ['source_sha256', 'row_id', 'word_key', 'text', 't_start', 't_end']
REVIEW = ROOT / 'docs' / 'data' / 'word-bank-review.json'
TR17_TAG = 'TR-17'
AUDIT_REVIEWER = 'Claude audit 2026-09-28'      # scripts/audit_vocab_unresolved.py REVIEWER


def reconcile_tracks(events, current, review, kept=None):
    """Rule TR-17 backfill of a lesson loaded before its reconnect recordings were transcribed. The saved events are
    insert-only raw evidence, so nothing in the database is changed:
      - events of a recording that has NO saved event yet (the newly transcribed one) are NEW ids -> returned for the
        insert-only install;
      - a saved Medi event the old load WITHHELD only because the tutor's recording was missing (the guard_events reason)
        and that the fuller transcript now assesses gets an overlay patch (docs/data/word-bank-review.json, RULES.md S2)
        with the rebuilt fields, source-bound by `expected`, tagged auto_rule 'TR-17'. A 'Claude audit 2026-09-28' bin
        made from the missing audio is undone; any other patch keeps its own fields.
    Everything else stays exactly as saved and is only counted in `kept` (dict): a saved event that later audits changed
    in place (09-16/17 'kul-sense', 'zero-said'), one whose context now also shows the new recording's lines, and new
    ids today's word matcher would find in recordings that were already loaded (matcher drift, not a missing recording).
    A withheld event whose source words changed raises: that needs a person.
    Returns (new events, {event id: patch changes})."""
    kept = {} if kept is None else kept
    loaded_sources = {o.get('source_id') for o in current.values()}
    new, fixes = [], {}
    for e in events:
        old = current.get(e['id'])
        if old is None:
            if e.get('source_id') in loaded_sources:
                kept['matcher_drift'] = kept.get('matcher_drift', 0) + 1
            else:
                new.append(e)
            continue
        if old == e:
            continue
        if old.get('reason') != WITHHELD:
            k = 'context_only' if {k for k in set(e) | set(old) if e.get(k) != old.get(k)} == {'context'} else 'saved_audit_kept'
            kept[k] = kept.get(k, 0) + 1
            continue
        if any(old.get(k) != e.get(k) for k in EVENT_KEYS + ['speaker', 'item_ids', 'original_text']):
            raise ValueError(f'{e["id"]}: withheld event changed its source words; needs a person')
        fix = {k: e.get(k) for k in set(e) | set(old) if e.get(k) != old.get(k)}
        fix.update(auto_rule=TR17_TAG, tr17_note='Re-read with every recording of the lesson (rule TR-17): the tutor recording of a reconnect '
                   'now covers this moment.')
        p = review['patches'].get(e['id'])
        exp = {k: old.get(k) for k in EVENT_KEYS + ['assessment', 'reason']}
        if p is not None and p['changes'].get('auto_rule') == TR17_TAG:
            fixes[e['id']] = fix                      # already reconciled (a re-run): its stacked fields stay
            continue
        if p is not None and p['changes'].get('audit_by') == AUDIT_REVIEWER:
            # the unresolved-word audit's bin was made on the withheld event: take it out (its re-run re-bins the
            # re-read event on top of this patch). A bin it created is dropped; a bin on another patch is undone.
            if p['changes'].get('audit_created'):
                p = None
            else:
                c = p['changes']
                prior = c.get('audit_prior') or {}
                for k in [k for k in c if k.startswith('audit_')]:
                    c.pop(k, None)
                for k, v in prior.items():
                    if v == '__absent__':
                        c.pop(k, None)
                    else:
                        c[k] = v
        if p is None:
            review['patches'][e['id']] = {'expected': exp, 'changes': fix}
        else:
            p['changes'].update(fix)
        fixes[e['id']] = fix
    return new, fixes


def envelope(path, seconds=900, rate=20):
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-t', str(seconds), '-i', str(path), '-f', 's16le', '-ac', '1', '-ar', '8000', '-'],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    hop = 8000 // rate
    n = len(x) // hop
    env = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-9)
    env = np.log(env)
    return (env - env.mean()) / (env.std() + 1e-9)


def estimate_offset(meet_media, lesson_mix, max_lag=900, rate=20):
    """Seconds to ADD to a Meet-recording time to get the lesson-timeline time (cross-correlation of loudness envelopes).
    max_lag was 240 s until 2026-10-02: that day the host pressed record ~6.5 min after the Recall bot joined (true offset
    +389.2 s, peak 0.73), so the search could not reach it and returned -231.5 s (peak 0.10) - all 44 of Amal's chat lines
    landed ~10 min early on the page and in the readers' transcript."""
    import numpy as np
    a = envelope(meet_media, rate=rate); b = envelope(lesson_mix, rate=rate)
    n = min(len(a), len(b))
    best, lag_best = -1e9, 0
    for lag in range(-max_lag * rate, max_lag * rate + 1):
        # lesson(t) ~ meet(t - lag)
        if lag >= 0:
            x, y = a[:n - lag], b[lag:n]
        else:
            x, y = a[-lag:n], b[:n + lag]
        if len(x) < 60 * rate:
            continue
        c = float(np.dot(x, y) / len(x))
        if c > best:
            best, lag_best = c, lag
    return lag_best / rate, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--raw', required=True); ap.add_argument('--work', required=True)
    ap.add_argument('--meet', help='host Meet recording file; its "- Chat Transcript" sidecar is merged')
    ap.add_argument('--chat-offset', type=float, help='skip the audio alignment and use this offset (seconds)')
    ap.add_argument('--apply', action='store_true'); ap.add_argument('--page-only', action='store_true')
    ap.add_argument('--note-extra', default='')
    ap.add_argument('--reconcile-tracks', action='store_true',
                    help='rule TR-17: a lesson re-loaded with its reconnect recordings (insert new events, overlay the withheld ones)')
    a = ap.parse_args()
    import db
    import sync_speaking_lesson as S
    from sync_word_bank_evidence import sync_events, digest
    date, raw, work = a.date, Path(a.raw), Path(a.work) / a.date
    work.mkdir(parents=True, exist_ok=True)
    data, info = (build_tracks if (raw / 'tracks' / 'tracks.json').exists() and (raw / 'scribe_Amal.json').exists() else build_mixed)(date, raw, work)

    audio_rel = f'{date}/audio/lesson.mp3'
    mix = PAGES_DIR / audio_rel
    if not mix.exists():
        if info['kind'] == 'mixed':
            page.mix_tracks(info['audio'], mix)            # same file, re-encoded small
        else:
            # every recording, transcribed or not: an untranscribed one (app reconnect) must still be HEARD on the
            # page and in the clips (Medi 2026-09-26: "we need the conversation with both of us")
            page.mix_tracks(info['audio'] + [(raw / 'tracks' / Path(o['file']).name, o['start']['relative']) for o in info['omitted']], mix)
    chat, offset, corr = [], 0.0, None
    if a.meet:
        side = Path(a.meet).parent / (Path(a.meet).name + ' - Chat Transcript')
        if side.exists():
            shutil.copy2(side, raw / 'meet-chat-transcript.txt')
            chat = page.parse_chat(side.read_text(encoding='utf-8', errors='replace'))
        if info['kind'] == 'tracks' and chat:
            if a.chat_offset is not None:
                offset = a.chat_offset
            else:
                offset, corr = estimate_offset(Path(a.meet), mix)
    ends = [r['timeline_end'] for r in data['rows'] if r.get('timeline_end') is not None]
    minutes = round(max(ends) / 60, 1)
    words = sum(i.get('type') == 'word' for r in data['rows'] for i in r['items'])
    if info['kind'] == 'tracks':
        note = ('Unreviewed speech recognition. Speakers are identified by recording track (one audio file per person). '
                + ('Not transcribed: ' + '; '.join(f'{_person(o["participant"])}\'s other recording at {_clock(o["start"]["relative"])}'
                                                   f'-{_clock(o["start"]["relative"] + (o["duration_s"] or 0))} ({round((o["duration_s"] or 0) / 60, 1)} min)'
                                                   for o in info['omitted']) + '. '
                   if info['omitted'] else ('Every recording of both people is transcribed, each placed at its own start '
                                            f'({len(info["extra_segments"])} reconnect recording(s) included). '
                                            if info.get('extra_segments') else 'Both participant tracks are transcribed. '))
                + ('Amal\'s typed chat lines are placed by matching the host recording to this audio. ' if chat else '')
                + 'Tap a time to play that line.')
    else:
        note = ('Unreviewed speech recognition from the host\'s single Meet recording: speakers are ESTIMATED '
                + ('from voice pitch, word by word' if info['basis'] == 'pitch_estimate' else "from the speech engine's two voice groups, named by voice pitch (Medi lower, Amal higher)")
                + f' ({round(info["unlabeled_share"] * 100, 1)}% of words could not be labeled and show as "Unknown"). '
                'Amal\'s typed chat lines use the same recording clock. Tap a time to play that line.')
    note = (note + ' ' + a.note_extra).strip()
    result = page.write_page(date, data, chat=chat, chat_offset=offset, note=note, audio_rel=audio_rel, minutes=minutes)
    receipt = {'date': date, 'kind': info['kind'], 'minutes': minutes, 'words': words, 'rows': len(data['rows']),
               'chat_lines': result['chat_lines'], 'chat_offset_s': offset, 'chat_offset_corr': corr,
               'omitted_segments': [(o['participant'], round(o['start']['relative'], 1), round(o['duration_s'] or 0, 1)) for o in info['omitted']],
               'unlabeled_share': info.get('unlabeled_share'), 'audio_bytes': mix.stat().st_size}
    if not a.page_only:
        events = S.detected_events(date, data=data)
        receipt['flagged'] = guard_events(events, data, info)
        receipt['events'] = len(events)
        receipt['assessments'] = dict(collections.Counter(e['assessment'] for e in events if e['speaker'] == 'Medi'))
        (work / 'events.json').write_text(json.dumps(events, ensure_ascii=False), encoding='utf-8')
        if a.reconcile_tracks:              # rule TR-17 backfill: new events inserted, withheld ones fixed in the overlay
            current = {r['id']: r['data'] for r in db.select('speaking_events', {'lesson_date': f'eq.{date}'}, retries=2)}
            review = json.loads(REVIEW.read_text(encoding='utf-8'))
            kept = {}
            new, fixes = reconcile_tracks(events, current, review, kept)
            receipt['tr17_kept_as_saved'] = kept
            receipt['evidence'] = sync_events(new, digest(new), a.apply) if new else {'new_events': 0}
            receipt['tr17_overlay_patches'] = len(fixes)
            receipt['tr17_assessments'] = dict(collections.Counter(f.get('assessment', current[i].get('assessment')) for i, f in fixes.items()))
            if a.apply and fixes:
                REVIEW.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        else:
            receipt['evidence'] = sync_events(events, digest(events), a.apply)
        row = {'date': date, 'source': 'Recall participant recordings' if info['kind'] == 'tracks' else 'Meet recording (host, mixed audio)',
               'minutes': minutes, 'words': words,
               'speaker_split': 'participant_tracks' if info['kind'] == 'tracks' else info['basis'],
               'split_ok': info['kind'] == 'tracks' or info.get('unlabeled_share', 1) < 0.05,
               'unlabeled_share': info.get('unlabeled_share') if info['kind'] == 'mixed' else 0,
               'topics': [], 'report_url': None,
               'summary': {'status': 'transcript_only', 'transcript_url': f'lessons/{date}.html', 'transcript_status': 'unreviewed_asr',
                           'human_confirmed': False,
                           'speaker_basis': 'participant_track_not_voice_verified' if info['kind'] == 'tracks' else info['basis'],
                           'missing_recording_segments': len(info['omitted']), 'chat_lines': result['chat_lines'],
                           'coverage_note': note, 'vocabulary_evidence_loaded': True}}
        receipt['lesson_row'] = row
        if a.apply:
            if not db.select('lessons', {'date': f'eq.{date}'}, retries=1):
                db.rest('POST', 'lessons', params={'on_conflict': 'date'}, body=[row], prefer='resolution=ignore-duplicates,return=representation', retries=1)
                receipt['lesson_row_inserted'] = True
            receipt['db_events'] = len(db.select('speaking_events', {'lesson_date': f'eq.{date}', 'select': 'id'}, retries=1))
    (work / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'lesson_row'}, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()
