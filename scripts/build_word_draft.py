"""Draft vocabulary evidence only: no providers, grading, or database writes."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attach_clips(result, clips_dir):
    """Attach the shortest published clip containing each draft timestamp."""
    clips = []
    for path in Path(clips_dir).glob('*.mp3'):
        match = re.search(r'_(\d{6})_(\d{6})\.mp3$', path.name, re.I)
        if match:
            clips.append((int(match.group(1)) / 10, int(match.group(2)) / 10, path.name))
    for word in result['words'].values():
        for event in word['events']:
            t = event['timeline_start']
            choices = [clip for clip in clips if clip[0] <= t <= clip[1]]
            if choices:
                start, _, name = min(choices, key=lambda clip: (clip[1] - clip[0], clip[0]))
                event['clip'] = name
                event['clip_offset'] = round(max(0, t - start), 6)
    return result


def norm(text):
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn' and c != 'ـ')
    return text.translate(str.maketrans('أإآٱ', 'اااا'))


def arabic_tokens(text):
    if re.search(r'[A-Za-z0-9]', text) or text.rstrip().endswith(('-', '–', '—', '…')):
        return None
    letters = [c for c in text if unicodedata.category(c).startswith('L')]
    if not letters or any(not ('\u0600' <= c <= '\u06ff') for c in letters):
        return None
    clean = ''.join(c if unicodedata.category(c).startswith('L') or unicodedata.category(c) == 'Mn' else ' ' for c in text)
    return tuple(norm(clean).split())


def build(data, words):
    assert data['status'] == 'unreviewed_asr'
    index = defaultdict(set)
    for word in words:
        for form in re.split(r'[/|]', word.get('arabic') or ''):
            tokens = arabic_tokens(form)
            if tokens and len(''.join(tokens)) >= 2:
                index[tokens].add(word['key'])
    lengths = sorted({len(k) for k in index}, reverse=True)
    evidence, seen = defaultdict(list), set()
    ambiguous = 0
    for row in data['rows']:
        source = data['sources'][row['source_id']]
        if source['speaker_label'] != 'Medi' or row['speaker_label'] != 'Medi':
            continue
        items = [i for i in row['items'] if i['type'] != 'spacing']
        pos = 0
        while pos < len(items):
            matched = None
            for length in lengths:
                if pos + length > len(items):
                    continue
                part = items[pos:pos + length]
                if any(i['type'] != 'word' for i in part):
                    continue
                if any(not isinstance(i.get('local_start'), (int, float)) or not isinstance(i.get('local_end'), (int, float)) for i in part):
                    continue
                if any(not (0 <= i['local_start'] <= i['local_end'] <= source['duration_s']) for i in part):
                    continue
                if any(b['local_start'] - a['local_end'] > 1.2 for a, b in zip(part, part[1:])):
                    continue
                tokens = [arabic_tokens(i['text']) for i in part]
                if any(t is None or len(t) != 1 for t in tokens):
                    continue
                keyset = index.get(tuple(t[0] for t in tokens))
                if not keyset:
                    continue
                if len(keyset) != 1:
                    ambiguous += 1
                    matched = (None, length, part)
                else:
                    matched = (next(iter(keyset)), length, part)
                break
            if matched:
                key, length, part = matched
                identity = (source['source_sha256'], key, tuple(i['id'] for i in part))
                if key and identity not in seen:
                    seen.add(identity)
                    evidence[key].append({'row_id': row['id'], 'source_id': row['source_id'],
                        'item_ids': [i['id'] for i in part], 'local_start': part[0]['local_start'],
                        'timeline_start': part[0]['timeline_start'], 'text': ' '.join(i['text'] for i in part),
                        'match': 'unique_arabic_spelling', 'status': 'unreviewed'})
                pos += length
            else:
                pos += 1
    return {'date': data['lesson'], 'status': 'draft', 'transcript_url': f'lessons/{data["lesson"]}.html',
            'speaker_basis': 'named_Medi_track_not_voice_verified', 'word_count': len(evidence),
            'occurrence_count': sum(map(len, evidence.values())), 'ambiguous_spans_omitted': ambiguous,
            'policy': 'Arabic-only unique spelling matches. No English, article stripping, root, conjugation or fuzzy inference. Possible uses, not correct-use or mastery evidence. Inflections and Latin-rendered Arabic may be missed.',
            'words': {key: {'count': len(events), 'events': events} for key, events in sorted(evidence.items())}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--transcript', type=Path, required=True)
    parser.add_argument('--vocab', type=Path, required=True)
    parser.add_argument('--fetch-vocab', action='store_true', help='Read active database vocabulary into a new private snapshot')
    parser.add_argument('--clips', type=Path, help='Published lesson clip directory for inline draft playback')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.fetch_vocab:
        assert not args.vocab.exists(), 'Snapshot exists; omit --fetch-vocab to reuse it'
        import db
        words = db.select('words', {'select': 'key,arabic,arabizi,english,topic,active', 'active': 'eq.true', 'order': 'key.asc'}, retries=1)
        args.vocab.parent.mkdir(parents=True, exist_ok=True)
        args.vocab.write_text(json.dumps(words, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    data = json.loads(args.transcript.read_text(encoding='utf-8'))
    words = json.loads(args.vocab.read_text(encoding='utf-8'))
    if isinstance(words, dict):
        words = words['items']
    result = build(data, words)
    if args.clips:
        attach_clips(result, args.clips)
    result['source_sha256'] = digest(args.transcript)
    result['vocab_sha256'] = digest(args.vocab)
    artifact = {'schema_version': 1, 'updated_at': datetime.now(timezone.utc).isoformat(), 'lessons': [result]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('date', 'word_count', 'occurrence_count', 'ambiguous_spans_omitted')}))
