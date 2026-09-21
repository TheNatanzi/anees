"""Offline, evidence-preserving Sep 5 review builder. No provider or publish calls.

python transcription_review.py --repo C:/dev/anees --output PATH
The frozen selection is based on inspected cached baselines, BEFORE new experiments.
It is a diagnostic set, not an unseen test set or an existing human gold set.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import random
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

LESSON = '2026-09-05'
SEED = 20260905

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_once(path, obj):
    path = Path(path)
    payload = json.dumps(obj, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        if read_json(path) != obj:
            raise ValueError(f'Refusing to overwrite different frozen artifact: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(payload)

def who(track):
    name = track['participant'].lower()
    if name == 'amal':
        return 'Amal'
    if name in ('medi natanzi', 'medi', 'mahdi natanzi'):
        return 'Medi'
    raise ValueError(f'Unknown track participant: {name}')

def evidence_stream(raw, source, speaker=None, offset=0):
    """Keep EVERY provider item and payload; never equate track with biometric ID."""
    result = []
    for i, item in enumerate(raw.get('words', [])):
        a, b = item.get('start'), item.get('end')
        result.append({
            'id': f'{source}:{i}', 'source': source, 'source_index': i,
            'speaker': speaker or f"Unknown ({item.get('speaker_id') or 'unlabeled'})",
            'speaker_basis': 'participant_track_not_voice_verified' if speaker else 'model_cluster_unverified',
            'start': round(float(a) + offset, 6) if a is not None else None,
            'end': round(float(b) + offset, 6) if b is not None else None,
            'type': item.get('type', 'unknown'), 'text': item.get('text', ''),
            'provider_item': item,
        })
    return result

def window_runs(items, start, end, prefix):
    """Short word runs; fillers remain text, events remain explicitly unverified."""
    # Carry in an item whose provider span overlaps the start. Do not hide a
    # long audio event or word simply because its onset predates this clip.
    # Such spans may be erroneous; preserve the claim and warn the reviewer.
    chosen = [i for i in items if i['start'] is not None and i['start'] < end
              and (i['start'] >= start or (i['end'] is not None and i['end'] > start))
              and i['type'] != 'spacing']
    chosen.sort(key=lambda i: (i['start'], i['end'] or i['start'], i['id']))
    runs = []
    for item in chosen:
        event = item['type'] != 'word'
        a, b = item['start'], item['end'] or item['start']
        if (not event and runs and not runs[-1]['events']
                and runs[-1]['speaker'] == item['speaker']
                and a - runs[-1]['end'] <= 1.0 and b - runs[-1]['start'] <= 6.0):
            r = runs[-1]
            r['text'] += ' ' + item['text']
            r['end'] = max(b, r['end'])
            r['evidence_ids'].append(item['id'])
        else:
            runs.append({'id': f'{prefix}-r{len(runs)+1:03}', 'speaker': item['speaker'],
                         'speaker_basis': item['speaker_basis'], 'start': a, 'end': b,
                         'text': item['text'], 'evidence_ids': [item['id']],
                         'events': [{'text': item['text'], 'start': a, 'end': b,
                                     'status': 'model_tag_not_human_verified'}] if event else []})
    for r in runs:
        r['crosses_window_boundary'] = r['start'] < start or r['end'] > end
        r['carry_in'] = r['start'] < start
        r['timing_warning'] = r['end']-r['start'] > 5 or r['crosses_window_boundary']
        r['timing_warning_text'] = (
            'This provider span extends outside the audio window. The clip cannot confirm the whole run; leave uncertain wording pending.'
            if r['crosses_window_boundary'] else
            'Long provider timing span; verify the actual sound. Its duration is not a measured silence.'
            if r['timing_warning'] else None)
    return runs

def selection(items):
    selected = []
    recasts = [(575, 'khalee / tutor explains not happy'),
               (1130, 'anbisti haflatik / tutor says forgot something, fee'),
               (1410, 'maz3ooj: feeling versus causing; candidate explanation'),
               (2035, 'binizaj / tutor pronunciation model'),
               (3060, 'matanzajini / stress on ayn and pronunciation question'),
               (3236, 'iza akoon / tutor contrasts iza bakoon'),
               (3325, 'shab3an / tutor says full, not hot'),
               (3659, 'za3lan / za3let contrast')]
    gaps = [(405, 'explicit forgot fee (grammar/recall, not proven vocabulary gap)'),
            (450, 'explicit forgot double T (form recall, not proven vocabulary gap)'),
            (1218, 'does not know how to say too much'),
            (1626, 'asks what the other verb is')]
    repairs = [(1347, 'candidate maz3ooj false start; F1 source attribution disputed'),
               (1653, 'candidate zaaj false start (F2)'),
               (2113, 'candidate bizajni self-repair (F3)'),
               (2875, 'm-m-ma tanzaj false start and tutor model')]
    for category, vals in [('candidate_tutor_recast', recasts), ('explicit_recall_or_word_question', gaps),
                           ('candidate_self_repair', repairs)]:
        for center, reason in vals:
            selected.append({'category': category, 'start': center-12, 'end': center+13,
                             'selection_reason': reason})
    pool = []
    for a in range(75, 3700, 25):
        b = a + 25
        if any(a < w['end'] and b > w['start'] for w in selected):
            continue
        words = [i for i in items if i['type'] == 'word' and i['start'] is not None and a <= i['start'] < b]
        arabic = sum(bool(re.search('[\u0600-\u06ff]', i['text'])) for i in words)
        if len(words) >= 8 and arabic / len(words) >= .5:
            pool.append((a, b))
    if len(pool) < 4:
        raise ValueError('Insufficient Arabic-script-heavy sampling pool')
    for a, b in random.Random(SEED).sample(pool, 4):
        selected.append({'category': 'random_arabic_script_heavy', 'start': a, 'end': b,
                         'selection_reason': f'Seed {SEED}; >=8 baseline words; >=50% Arabic-script words; script-based proxy, not acoustic language truth'})
    for i, w in enumerate(selected):
        w['id'] = f'w{i+1:02}'
    return selected, pool

def clip(source, target, start, duration):
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-ss', str(start), '-i', str(source),
                    '-t', str(duration), '-ac', '1', '-ar', '24000', '-b:a', '32k', str(target)], check=True)

def build(repo, output, template, rebuild_derived=False):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    lesson = repo / 'data' / 'lessons' / LESSON
    tracks = read_json(lesson / 'tracks' / 'tracks.json')['tracks']
    sources, stream, paths = {}, [], {}
    for track in tracks:
        person = who(track)
        raw_path = lesson / f'scribe_{person}.json'
        audio_path = lesson / 'tracks' / Path(track['file']).name
        paths[person] = (audio_path, float(track['start']['relative']))
        sources[person] = {'raw_file': str(raw_path.relative_to(repo)), 'raw_sha256': digest(raw_path),
                           'audio_file': str(audio_path.relative_to(repo)), 'audio_sha256': digest(audio_path),
                           'offset': paths[person][1], 'participant': track['participant']}
        stream.extend(evidence_stream(read_json(raw_path), person, person, paths[person][1]))
    stream.sort(key=lambda x: (x['start'] is None, x['start'] or 0, x['id']))
    mixed_path = lesson / 'scribe_meet_mixed_1615.json'
    mixed = evidence_stream(read_json(mixed_path), 'cached_mixed')
    sources['cached_mixed'] = {'raw_file': str(mixed_path.relative_to(repo)), 'raw_sha256': digest(mixed_path),
                               'clock': 'bot common time: ngram alignment median delta 0.001s',
                               'audio_origin': 'inferred same bot mix, not verified independent Meet recording'}
    write_once(output / 'evidence-transcript.json', {'schema_version':'1.0','lesson':LESSON,
               'sources': sources, 'items': stream, 'status':'unreviewed_machine_evidence'})
    frozen = output / 'review-manifest.json'
    if frozen.exists():
        manifest = read_json(frozen)
        if manifest['sources'] != sources:
            raise ValueError('Source changed since manifest freeze')
    else:
        windows, pool = selection(stream)
        manifest = {'schema_version':'1.0','lesson':LESSON,'review_set_id':'sep05-diagnostic20-v1',
                    'created_at':datetime.now(timezone.utc).isoformat(),'seed':SEED,'sources':sources,
                    'selection_scope':'Cached baselines inspected to select diagnostic windows; frozen before new experiment outputs. Not an unseen evaluation set.',
                    'random_pool':pool,'windows':windows,'human_gold_status':'pending_human_review'}
        for w in windows:
            w['clips'] = {}
            for person, (path, offset) in paths.items():
                target = output / 'clips' / f"{w['id']}_{person}.mp3"
                clip(path, target, w['start']-offset, w['end']-w['start'])
                w['clips'][person] = {'file':str(target.relative_to(output)), 'sha256':digest(target),
                                      'source_start': w['start']-offset}
            target = output / 'clips' / f"{w['id']}_mixed.mp3"
            if not target.exists():
                subprocess.run(['ffmpeg','-nostdin','-v','error','-n',
                    '-i',str(output / w['clips']['Medi']['file']), '-i',str(output / w['clips']['Amal']['file']),
                    '-filter_complex','amix=inputs=2:normalize=0','-ac','1','-b:a','32k',str(target)],check=True)
            w['clips']['mixed'] = {'file':str(target.relative_to(output)),'sha256':digest(target),
                                    'source':'Aligned separate-track clips mixed locally; not an independent recording'}
        write_once(frozen, manifest)
    review = {'schema_version':'1.0','lesson':LESSON,'manifest_sha256':digest(frozen),
              'review_set_id':manifest['review_set_id'],'windows':[]}
    for w in manifest['windows']:
        audio = {}
        for person, c in w['clips'].items():
            path = output / c['file']
            if digest(path) != c['sha256']:
                raise ValueError(f'Clip changed: {path}')
            audio[person] = 'data:audio/mpeg;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')
        options = [
            {'source_kind':'separate_tracks','label':'Separate participant tracks (account identity, not voice verification)', 'items':stream},
            {'source_kind':'mixed_recording','label':'Cached mixed rerun (same-clock; bot mix origin inferred)', 'items':mixed}]
        random.Random(f'{SEED}:{w["id"]}').shuffle(options)
        candidates = []
        for letter, option in zip(('A','B'),options):
            candidates.append({'id':letter,'source_kind':option['source_kind'],'label':option['label'],
                               'runs':window_runs(option['items'],w['start'],w['end'],w['id']+'-'+letter)})
        review['windows'].append({k:w[k] for k in ('id','category','start','end','selection_reason')} |
                                  {'audio':audio,'candidates':candidates})
    # Payload sidecar has no embedded audio: suitable for scorer/provenance, not web-fetch input.
    compact = json.loads(json.dumps(review))
    for w in compact['windows']:
        w['audio'] = manifest['windows'][int(w['id'][1:])-1]['clips']
    data_path = output / 'review-data.json'
    if data_path.exists() and read_json(data_path) != compact and rebuild_derived:
        history = output / '_derived-history' / f'review-data.{digest(data_path)}.json'
        history.parent.mkdir(exist_ok=True)
        if not history.exists():
            with history.open('xb') as f:
                f.write(data_path.read_bytes())
        data_path.write_text(json.dumps(compact, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        write_once(data_path, compact)
    if not template.exists():
        print(json.dumps({'frozen':str(frozen),'status':'template_pending'}))
        return
    html = template.read_text(encoding='utf-8')
    if html.count('__REVIEW_DATA_JSON__') != 1:
        raise ValueError('Expected exactly one template placeholder')
    comparison_marker = '/* __REVIEW_COMPARISON_JS__ */'
    if comparison_marker in html:
        comparison_path = template.with_name('review_comparison.js')
        comparison_code = comparison_path.read_text(encoding='utf-8')
        if '</script' in comparison_code.lower():
            raise ValueError('Unsafe closing script tag in comparison helper')
        html = html.replace(comparison_marker, comparison_code)
    safe_json = json.dumps(review,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (output / 'review.html').write_text(html.replace('__REVIEW_DATA_JSON__',safe_json),encoding='utf-8')
    print(json.dumps({'review':str(output/'review.html'),'windows':len(review['windows']),
                      'manifest_sha256':review['manifest_sha256'],'gold':'pending'},indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--template',type=Path,default=Path(__file__).with_name('review_template.html'))
    parser.add_argument('--rebuild-derived',action='store_true',help='Rebuild changed run display data with a saved copy; never replaces raw evidence or frozen selection. Old review exports may require manual migration.')
    args = parser.parse_args()
    build(args.repo,args.output,args.template,args.rebuild_derived)
