"""ChatGPT's transcriber (OpenAI gpt-4o-transcribe-diarize) on the 20 Check 02 clips only.
Writes data/aug25/openai_clips.json = {clip_index: [{'spk','s','e','text'}]} with times relative to the lesson file.
Usage: python engine_openai_clips.py            (needs OPENAI_API_KEY in env)"""
import json, io, os, sys, time, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / 'data' / 'aug25'
key = os.environ.get('OPENAI_API_KEY') or sys.exit('MISSING OPENAI_API_KEY')
MODEL = os.environ.get('OPENAI_STT_MODEL', 'gpt-4o-transcribe-diarize')
wins = json.load(io.open(R / 'check02_windows.json', encoding='utf-8'))   # [{'i','start','end','clip'}]
out = {}
for w in wins:
    t0 = time.time()
    with open(ROOT / w['clip'], 'rb') as f:
        r = requests.post('https://api.openai.com/v1/audio/transcriptions',
                          headers={'Authorization': f'Bearer {key}'},
                          data={'model': MODEL, 'response_format': 'diarized_json', 'chunking_strategy': 'auto'},
                          files={'file': (os.path.basename(w['clip']), f, 'audio/mpeg')}, timeout=300)
    if r.status_code != 200:
        print(w['i'], r.status_code, r.text[:300])
        if r.status_code in (401, 402, 429):
            sys.exit(1)
        continue
    d = r.json()
    segs = d.get('segments') or []
    out[str(w['i'])] = [{'spk': s.get('speaker', '?'), 's': w['start'] + float(s.get('start', 0)),
                         'e': w['start'] + float(s.get('end', 0)), 'text': s.get('text', '').strip()} for s in segs]
    if not segs and d.get('text'):
        out[str(w['i'])] = [{'spk': '?', 's': w['start'], 'e': w['end'], 'text': d['text'].strip()}]
    print(w['i'], f'{time.time() - t0:.0f}s', len(segs), 'segments')
io.open(R / 'openai_clips.json', 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
print('saved', len(out), 'clips')
