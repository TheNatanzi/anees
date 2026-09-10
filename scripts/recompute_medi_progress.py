"""Preview/apply a derived-only progress backfill. Never rewrite raw lesson or card evidence."""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path

import buckets
import db

ROOT = Path(__file__).resolve().parent.parent
MODEL_FILES = ('scripts/buckets.py', 'docs/js/buckets.js', 'docs/js/cards-core.js', 'docs/js/progress.js')
NEW_FIELDS = ('independent_uses', 'mastery_streak', 'mastery_days', 'progress_context', 'progress_scores')
SOURCES = {'word_events': 'id', 'card_results': 'id', 'amal_rules': 'id', 'lessons': 'date', 'words': 'key', 'word_stats': 'word_key'}


def compact(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def model_hash():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in MODEL_FILES}


def fingerprint_sql():
    parts = []
    for table, key in SOURCES.items():
        value = 'to_jsonb(t)'
        if table == 'word_stats':
            value += ''.join(' - ' + literal(k) for k in NEW_FIELDS)
        parts += [literal(table), f"(select md5(coalesce(jsonb_agg({value} order by t.{key}), '[]'::jsonb)::text) from public.{table} t)"]
    return 'select jsonb_build_object(' + ','.join(parts) + ') as fingerprints'


def fingerprints():
    return db.sql(fingerprint_sql())[0]['fingerprints']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def preview(folder):
    folder.mkdir(parents=True, exist_ok=True)
    snapshot_path = folder / 'snapshot.json'
    if snapshot_path.exists():
        raise RuntimeError('Snapshot exists; use its apply/verify command or choose a new output folder.')
    before = fingerprints()
    sources = {
        'events': db.select('word_events', {'select': 'id,lesson_date,word_key,speaker,prompted,correction,asked,miss_kind,t_start,text', 'order': 'id.asc'}),
        'cards': db.select('card_results', {'select': 'id,word_key,ts,result,attempt', 'order': 'id.asc'}),
        'lessons': db.select('lessons', {'select': 'date', 'order': 'date.asc'}),
        'marks': db.select('amal_rules', {'select': 'lesson_date,word_key,kind', 'kind': 'eq.new', 'order': 'id.asc'}),
        'word_keys': [r['key'] for r in db.select('words', {'select': 'key', 'order': 'key.asc'})],
        'old_stats': db.select('word_stats', {'order': 'word_key.asc'})}
    if fingerprints() != before:
        raise RuntimeError('Sources changed during snapshot; no database writes made. Preview again.')
    confirmed = {(str(r['lesson_date']), r['word_key']) for r in sources['marks'] if r.get('word_key')}
    stats = buckets.compute(sources['events'], sources['cards'], [r['date'] for r in sources['lessons']], confirmed_new=confirmed)
    known = set(sources['word_keys'])
    rows = []
    for key, s in sorted(stats.items()):
        if key not in known:
            continue
        row = dict(s)
        row.pop('new_candidate', None)
        if row['last_reviewed'] and len(row['last_reviewed']) == 10:
            row['last_reviewed'] += 'T00:00:00+00:00'
        rows.append(row)
    snapshot = dict(sources=sources, fingerprints=before, model_hash=model_hash(), expected=rows)
    save(snapshot_path, snapshot)
    old = {s['word_key']: s for s in sources['old_stats']}
    sample_keys = ['jumle', 'mAdi', 'shukran', 'hada', 'za3lAn', 'beida7ek', 'tAni']
    summary = {'rows': len(rows), 'excluded_nonvocabulary_keys': sorted(set(stats) - known),
               'changed_buckets': sum(old.get(r['word_key'], {}).get('bucket') != r['bucket'] for r in rows),
               'old_total_seen': sum(r.get('times_seen', 0) for r in sources['old_stats']),
               'new_total_medi_uses': sum(r['times_seen'] for r in rows),
               'independent_uses': sum(r['independent_uses'] for r in rows),
               'speaking_buckets': dict(collections.Counter(r['bucket'] for r in rows)),
               'flashcard_buckets': dict(collections.Counter(r['progress_scores']['flashcards']['bucket'] for r in rows)),
               'speaking_intro_targets': [{'word_key': r['word_key'], 'uses': r['progress_scores']['speaking']['intro_uses']} for r in rows if r['progress_scores']['speaking']['intro_target'] and r['progress_scores']['speaking']['intro_uses'] < 5],
               'samples': [{k: r[k] for k in ('word_key', 'bucket', 'times_seen', 'independent_uses', 'seen_lessons', 'last_lesson', 'mastery_streak')} for r in rows if r['word_key'] in sample_keys]}
    save(folder / 'preview.json', summary)
    print(compact(summary))


def same(field, actual, expected):
    if field == 'last_reviewed' and actual and expected:
        return datetime.datetime.fromisoformat(actual.replace('Z', '+00:00')) == datetime.datetime.fromisoformat(expected.replace('Z', '+00:00'))
    return actual == expected


def check_expected(snapshot):
    actual = {r['word_key']: r for r in db.select('word_stats', {'order': 'word_key.asc'})}
    for expected in snapshot['expected']:
        row = actual.get(expected['word_key'], {})
        for field, value in expected.items():
            if not same(field, row.get(field), value):
                raise RuntimeError(f'Readback mismatch: {expected["word_key"]}.{field}')
    now = fingerprints()
    if any(now[k] != snapshot['fingerprints'][k] for k in SOURCES if k != 'word_stats'):
        raise RuntimeError('Raw sources changed; do not claim an unchanged-source verification.')
    return {'rows_verified': len(snapshot['expected']), 'raw_sources_unchanged': True}


def apply(folder):
    snapshot = read(folder / 'snapshot.json')
    if snapshot['model_hash'] != model_hash():
        raise RuntimeError('Calculation code changed after preview; create a new preview.')
    if (folder / 'applied.json').exists():
        print(compact(check_expected(snapshot)))
        return
    # Reconcile a previous successful transaction whose client lost its acknowledgement.
    if fingerprints() != snapshot['fingerprints']:
        receipt = check_expected(snapshot)
        save(folder / 'applied.json', receipt)
        print(compact(receipt))
        return
    db.sql((ROOT / 'supabase/migrations/012_medi_progress.sql').read_text(encoding='utf-8'))
    db.sql((ROOT / 'supabase/migrations/013_separate_progress.sql').read_text(encoding='utf-8'))
    rows = snapshot['expected']
    if not rows:
        raise RuntimeError('Refusing an empty backfill.')
    columns = sorted(rows[0])
    if any(sorted(r) != columns for r in rows):
        raise RuntimeError('Inconsistent row fields.')
    names = ','.join(columns)
    updates = ','.join(f'{c}=excluded.{c}' for c in columns if c != 'word_key') + ',updated_at=now()'
    guard = fingerprint_sql().replace('select jsonb_build_object(', 'select jsonb_build_object(', 1)
    sql = ('begin; lock table ' + ','.join('public.' + t for t in SOURCES) + ' in share row exclusive mode; '
           'do $progress_guard$ begin if (' + guard.replace(' as fingerprints', '') + ') <> '
           + literal(compact(snapshot['fingerprints'])) + '::jsonb then raise exception \'Progress sources changed after preview\'; end if; end $progress_guard$; '
           + f'insert into public.word_stats ({names}) select {names} from jsonb_populate_recordset(null::public.word_stats, '
           + literal(compact(rows)) + '::jsonb) on conflict (word_key) do update set ' + updates + '; commit;')
    db.sql(sql, retries=1)
    receipt = check_expected(snapshot)
    save(folder / 'applied.json', receipt)
    print(compact(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['preview', 'apply', 'verify'])
    parser.add_argument('--output', type=Path, required=True, help='Private local artifact directory, never public docs/')
    args = parser.parse_args()
    folder = args.output.resolve()
    if folder == ROOT / 'docs' or ROOT / 'docs' in folder.parents:
        raise SystemExit('Private snapshot must not be in public docs/.')
    if args.mode == 'preview':
        preview(folder)
    elif args.mode == 'apply':
        apply(folder)
    else:
        print(compact(check_expected(read(folder / 'snapshot.json'))))
