"""Automatically add a completed Recall lesson to the unified Speaking ledger.

This uses the already-saved participant-track Scribe responses.  It makes no
provider call, never edits raw evidence, and never changes Flashcard results.
Uncertain assessments are included as provisional evidence and placed behind a
private, separate review link instead of a draft panel on the Words screen.
"""
from __future__ import annotations

import argparse
import base64
import copy
import datetime
import hashlib
import json
import math
import re
import secrets
import subprocess
from collections import Counter
from pathlib import Path

import db
import speaking_evidence as se

ROOT = Path(__file__).resolve().parents[1]
LESSONS = ROOT / 'data' / 'lessons'
PAGES = 'https://thenatanzi.github.io/anees/'
MAX_GAP = 1.2
MAX_SPAN = 12.0


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def filehash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def person(name):
    value = str(name).lower()
    if 'amal' in value:
        return 'Amal'
    if 'medi' in value or 'mahdi' in value or 'natanzi' in value:
        return 'Medi'
    raise ValueError(f'Unknown participant {name!r}')


def number(value, label, nullable=False):
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'Invalid {label}')
    return float(value)


def source_rows(source_id, speaker, offset, response):
    raw_items = response.get('words')
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(f'{source_id}: response has no evidence items')
    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict) or not isinstance(raw.get('text'), str):
            raise ValueError(f'{source_id}: invalid evidence item {index}')
        start = number(raw.get('start'), 'item start', nullable=True)
        end = number(raw.get('end'), 'item end', nullable=True)
        if (start is None) != (end is None) or (start is not None and end < start):
            raise ValueError(f'{source_id}: invalid item timestamp {index}')
        items.append({'id': f'{source_id}:item:{index}', 'index': index,
                      'type': raw.get('type', 'unknown'), 'text': raw['text'],
                      'local_start': start, 'local_end': end,
                      'timeline_start': None if start is None else start + offset,
                      'timeline_end': None if end is None else end + offset,
                      'speaker_id': raw.get('speaker_id'), 'logprob': raw.get('logprob'),
                      'raw': copy.deepcopy(raw)})
    groups, group, cluster, first, last = [], [], None, None, None
    for item in items:
        timed = item['type'] != 'spacing' and item['local_start'] is not None
        if timed:
            start, end, item_cluster = item['local_start'], item['local_end'], item['speaker_id']
            split = first is not None and (item_cluster != cluster or start - last > MAX_GAP or max(end, last) - first > MAX_SPAN)
            if split:
                groups.append(group); group, first, last = [], None, None
            if first is None:
                first, last, cluster = start, end, item_cluster
            else:
                first, last = min(first, start), max(last, end)
        group.append(item)
    if group:
        groups.append(group)
    rows = []
    for group in groups:
        timed = [item for item in group if item['local_start'] is not None and item['type'] != 'spacing']
        if not timed:
            timed = [item for item in group if item['local_start'] is not None]
        start = min((item['local_start'] for item in timed), default=None)
        end = max((item['local_end'] for item in timed), default=None)
        clusters = list(dict.fromkeys(item['speaker_id'] for item in group if item['type'] != 'spacing'))
        separator = '' if any(item['type'] == 'spacing' for item in group) else ' '
        rows.append({'id': f'{source_id}:row:{group[0]["index"]}', 'source_id': source_id,
                     'speaker_label': speaker, 'speaker_basis': 'participant_track_not_voice_verified',
                     'cluster_id': clusters[0] if len(clusters) == 1 else None,
                     'local_start': start, 'local_end': end,
                     'timeline_start': None if start is None else start + offset,
                     'timeline_end': None if end is None else end + offset,
                     'items': group, 'text': separator.join(item['text'] for item in group),
                     'raw_status': 'unreviewed_asr', 'warnings': []})
    return rows


def build_transcript(date, lesson_dir=None, write=True):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        raise ValueError('Lesson date must be YYYY-MM-DD')
    lesson = Path(lesson_dir or (LESSONS / date)).resolve()
    manifest_path = lesson / 'tracks' / 'tracks.json'
    manifest = read(manifest_path)
    sources, rows, provenance = {}, [], []
    seen = set()
    for track in manifest.get('tracks', []):
        speaker = person(track.get('participant'))
        if speaker in seen:
            raise ValueError(f'Duplicate {speaker} track')
        seen.add(speaker)
        source_id = f'anees-{date.replace("-", "")}-recall-{speaker.lower()}'
        audio = Path(track['file']).resolve()
        response_path = lesson / f'scribe_{speaker}.json'
        response = read(response_path)
        offset = number(track['start']['relative'], 'track offset')
        duration = number(response.get('audio_duration_secs', track.get('duration_s')), 'audio duration')
        source = {'id': source_id, 'speaker_label': speaker,
                  'speaker_basis': 'participant_track_not_voice_verified',
                  'source_sha256': filehash(audio), 'response_sha256': filehash(response_path),
                  'input_path': str(audio), 'file_uri': audio.as_uri(), 'bytes': audio.stat().st_size,
                  'track_offset_s': offset, 'duration_s': duration,
                  'language_code': response.get('language_code'), 'response_path': str(response_path),
                  'asr_mode': {'model': 'scribe_v2', 'requested_language': response.get('language_code') or 'auto',
                               'keyterms_count': 0}}
        sources[source_id] = source
        rows.extend(source_rows(source_id, speaker, offset, response))
        provenance.append({k: source[k] for k in ('id', 'source_sha256', 'response_sha256', 'track_offset_s')})
    if seen != {'Amal', 'Medi'}:
        raise ValueError('A completed Recall lesson needs one Amal track and one Medi track')
    rows.sort(key=lambda row: (row['timeline_start'] is None, row['timeline_start'] or 0, row['source_id'], row['items'][0]['index']))
    data = {'schema_version': 1, 'kind': 'anees-working-transcript', 'lesson': date,
            'built_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'manifest_sha256': canonical_hash(provenance), 'status': 'unreviewed_asr',
            'sources': sources, 'rows': rows, 'context_findings': None,
            'policy': {'raw_evidence_unchanged': True, 'automatic_translation': False,
                       'automatic_transliteration': False, 'human_confirmed': False,
                       'timeline': 'track-local timestamp plus Recall manifest offset'}}
    if write:
        save(lesson / 'speaking-evidence.json', data)
    return data


def preserve_contextual_reviews(events, prior_events):
    """Do not let an automatic rerun replace source-bound contextual corrections."""
    generated = {event['id']: event for event in events}
    for prior in prior_events:
        if not any(prior.get(k) for k in ('contextual_audit', 'adjudication', 'match_correction')):
            continue
        event = generated.get(prior['id'])
        if (not event or event.get('source_sha256') != prior.get('source_sha256')
                or event.get('original_text') != prior.get('original_text')
                or se.sha(event.get('context', [])) != se.sha(prior.get('context', []))):
            raise RuntimeError('Contextually reviewed evidence changed; explicit reconciliation is required')
        event.clear()
        event.update(copy.deepcopy(prior))
    return events


def detected_events(date, data=None, words=None):
    data = data or build_transcript(date)
    words = words or db.select('words', {'select': 'key,arabizi,arabic,plural,aliases,active', 'active': 'eq.true'})
    events = se.assess(se.candidates(data, se.StrictMatcher(words)))
    for event in events:
        # The public lesson transcript has different row IDs. Review audio is
        # supplied through the private review link, so do not invent a deep link.
        event['transcript_url'] = None
        event['audio_url'] = None
    return events


def lesson_summaries(events):
    result = []
    for date in sorted({event['lesson_date'] for event in events}):
        medi = [event for event in events if event['lesson_date'] == date and event['speaker'] == 'Medi']
        spoken = [event for event in medi if event['spoken']]
        result.append({'date': date, 'practice_occurrences': len(spoken),
                       'vocabulary_entries': len({event['word_key'] for event in spoken}),
                       'independent_successes': sum(event['assessment'] == 'independent' for event in spoken),
                       'helped_uses': sum(event['assessment'] == 'helped' for event in spoken),
                       'recall_failures': sum(event['assessment'] == 'recall_failure' for event in medi),
                       'incorrect_attempts': sum(event['assessment'] == 'incorrect' for event in medi),
                       'unresolved': sum(event['assessment'] == 'unresolved' for event in medi),
                       'review_queue': se.review_queue(medi),
                       'coverage': 'partial; unmatched words are not evidence of absence'})
    return result


def review_link(date, data, events):
    queue = se.review_queue([event for event in events if event['speaker'] == 'Medi'])
    private_path = LESSONS / date / 'speaking-review.json'
    previous = read(private_path) if private_path.exists() else {}
    token = previous.get('token') if previous.get('event_ids') == queue else None
    token = token if isinstance(token, str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', token) else secrets.token_urlsafe(32)
    expires = previous.get('expires_at') if previous.get('token') == token else None
    if not expires or datetime.datetime.fromisoformat(expires).astimezone(datetime.timezone.utc) <= datetime.datetime.now(datetime.timezone.utc):
        expires = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)).isoformat()
    by_id = {event['id']: event for event in events}
    clips = {}
    clip_dir = LESSONS / date / 'speaking-review-clips'; clip_dir.mkdir(parents=True, exist_ok=True)
    for ident in queue:
        event = by_id[ident]; source = data['sources'][event['source_id']]
        start = max(0, float(event['local_start']) - 6)
        duration = min(25, max(8, float(event['local_end']) - start + 6))
        target = clip_dir / f'{ident}.mp3'
        if not target.exists():
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(start),
                            '-i', source['input_path'], '-t', str(duration), '-vn', '-codec:a', 'libmp3lame',
                            '-b:a', '48k', str(target)], check=True, capture_output=True)
        clips[ident] = 'data:audio/mpeg;base64,' + base64.b64encode(target.read_bytes()).decode('ascii')
    payload = {'token': token, 'lesson_date': date, 'expires_at': expires,
               'event_ids': queue, 'clips': clips}
    save(private_path, {'token': token, 'lesson_date': date, 'expires_at': expires,
                        'event_ids': queue, 'url': f'{PAGES}speaking-review.html#{token}'})
    return payload


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def active():
    installed = db.sql("select to_regclass('public.speaking_release') is not null as installed", retries=1)[0]['installed']
    return installed and bool(db.select('speaking_release', {'select': 'id', 'limit': '1'}, retries=1))


def sync(date):
    if not active():
        raise RuntimeError('Unified Speaking ledger is not active')
    data = build_transcript(date)
    events = detected_events(date, data=data)
    old_rows = db.select('speaking_events', {'lesson_date': f'eq.{date}'}, retries=1)
    old = {row['id']: row['data'] for row in old_rows}
    preserve_contextual_reviews(events, old.values())
    generated = {event['id']: event for event in events}
    for ident, prior in old.items():
        if prior.get('assessment_status') != 'human_reviewed':
            continue
        event = generated.get(ident)
        if not event or event['original_text'] != prior['original_text'] or se.sha(event['context']) != se.sha(prior['context']):
            raise RuntimeError('A human-reviewed event changed; explicit source correction is required')
        for field in ('word_key', 'spoken', 'assessment', 'assessment_status', 'reason', 'human_correction'):
            event[field] = prior[field]
    all_live = [row['data'] for row in db.select('speaking_events', retries=1)]
    combined = [event for event in all_live if event['lesson_date'] != date] + events
    combined.sort(key=lambda event: (event['lesson_date'], event['t_start'] if event['t_start'] is not None else -1, event['id']))
    current_release = db.select('speaking_release', retries=1)[0]['data']
    release = {**current_release, 'revision': se.sha(combined), 'lessons': lesson_summaries(combined),
               'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    review = review_link(date, data, events)
    affected = sorted({event.get('word_key') for event in list(old.values()) + events if event.get('word_key')})
    stats_before = {row['word_key']: row['progress_scores']['flashcards'] for row in db.select('word_stats', retries=1)
                    if row['word_key'] in affected}
    rows = [{'id': event['id'], 'lesson_date': event['lesson_date'], 'word_key': event['word_key'], 'data': event}
            for event in events]
    ids = [event['id'] for event in events]
    statements = ['begin;', 'lock table public.speaking_events,public.word_stats,public.speaking_release,public.speaking_review_links in share row exclusive mode;']
    statements.append("do $guard$ begin if exists(select 1 from public.speaking_events where lesson_date=" + literal(date) +
                      " and data->>'assessment_status'='human_reviewed' and not (id=any(" + literal(compact(ids)) +
                      "::jsonb #>> '{}')::text[])) then raise exception 'Human review would be removed'; end if; end $guard$;")
    if rows:
        statements.append("insert into public.speaking_events(id,lesson_date,word_key,data) select id,lesson_date,word_key,data from jsonb_populate_recordset(null::public.speaking_events," +
                          literal(compact(rows)) + "::jsonb) on conflict(id) do update set lesson_date=excluded.lesson_date,word_key=excluded.word_key,data=excluded.data where speaking_events.data is distinct from excluded.data;")
        statements.append("delete from public.speaking_events where lesson_date=" + literal(date) + " and not (id in (select jsonb_array_elements_text(" + literal(compact(ids)) + "::jsonb)));")
    else:
        statements.append("delete from public.speaking_events where lesson_date=" + literal(date) + ";")
    if affected:
        statements.append("select public.refresh_speaking_word(value) from jsonb_array_elements_text(" + literal(compact(affected)) + "::jsonb);")
    statements.append("update public.speaking_review_links set expires_at=now() where lesson_date=" + literal(date) + " and token<>" + literal(review['token']) + ";")
    statements.append("insert into public.speaking_review_links(token,lesson_date,expires_at,event_ids,clips) select token,lesson_date,expires_at,event_ids,clips from jsonb_populate_record(null::public.speaking_review_links," + literal(compact(review)) + "::jsonb) on conflict(token) do update set expires_at=excluded.expires_at,event_ids=excluded.event_ids,clips=excluded.clips;")
    statements.append("update public.speaking_release set data=" + literal(compact(release)) + "::jsonb where id;")
    statements.append('commit;')
    # PostgreSQL's JSON-to-array coercion is intentionally avoided in the final
    # transaction. Replace the guard with a simple, quoted ID list.
    quoted_ids = ','.join(literal(ident) for ident in ids) or "''"
    statements[2] = ("do $guard$ begin if exists(select 1 from public.speaking_events where lesson_date=" + literal(date) +
                     " and data->>'assessment_status'='human_reviewed' and id not in (" + quoted_ids +
                     ")) then raise exception 'Human review would be removed'; end if; end $guard$;")
    db.sql('\n'.join(statements), retries=1)
    after = {row['word_key']: row['progress_scores']['flashcards'] for row in db.select('word_stats', retries=1)
             if row['word_key'] in affected}
    if any(after.get(key) != score for key, score in stats_before.items()):
        raise RuntimeError('Flashcard score changed during Speaking sync')
    for key in set(affected) - set(stats_before):
        if after.get(key, {}).get('bucket') != 'never' or after[key].get('attempts') != 0:
            raise RuntimeError('A new Speaking row received non-empty Flashcard progress')
    live_ids = {row['id'] for row in db.select('speaking_events', {'lesson_date': f'eq.{date}', 'select': 'id'}, retries=1)}
    if live_ids != set(ids):
        raise RuntimeError('Speaking event readback differs')
    return {'status': 'synced', 'date': date, 'events': len(events),
            'recorded_uses': sum(event['speaker'] == 'Medi' and event['spoken'] for event in events),
            'vocabulary_entries': len({event['word_key'] for event in events if event['speaker'] == 'Medi' and event['spoken']}),
            'review_items': len(review['event_ids']), 'review_url': f'{PAGES}speaking-review.html#{review["token"]}'}


def sync_if_active(date):
    return sync(date) if active() else {'status': 'inactive', 'date': date}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('date'); parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    if args.build_only:
        transcript = build_transcript(args.date)
        print(json.dumps({'date': args.date, 'rows': len(transcript['rows']),
                          'sources': len(transcript['sources'])}))
    else:
        print(json.dumps(sync(args.date), ensure_ascii=False, indent=2))
