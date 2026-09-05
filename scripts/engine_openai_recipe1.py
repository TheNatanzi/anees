"""Codex RECIPE #1 (wiki/15): slice each Check 02 clip by ElevenLabs speaker timings ->
gpt-transcribe per speaker-homogeneous slice (languages ar+en, verbatim prompt) -> reassemble with ElevenLabs labels.
Writes data/aug25/openai_recipe1.json = {clip_index: [{'spk','s','e','text','n_ele'}]}.
Usage: python engine_openai_recipe1.py [--segments-from data/aug25/eleven_scribe_auto.json] [--only 0,1]"""
import json, io, os, sys, time, re, subprocess, argparse, tempfile, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / 'data' / 'aug25'
AUDIO = R / 'audio' / 'aug25.mp3'
ap = argparse.ArgumentParser()
ap.add_argument('--segments-from', default='data/aug25/eleven_scribe_auto.json')
ap.add_argument('--out', default='openai_recipe1.json')
ap.add_argument('--only', default='')
ap.add_argument('--model', default=os.environ.get('OPENAI_STT_MODEL', 'gpt-transcribe'))
a = ap.parse_args()

def user_key():
    k = os.environ.get('OPENAI_API_KEY')
    if k: return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
            return winreg.QueryValueEx(h, 'OPENAI_API_KEY')[0]
    except Exception:
        sys.exit('MISSING OPENAI_API_KEY')
KEY = user_key()
PROMPT = os.environ.get('OPENAI_PROMPT', 'Verbatim Palestinian Arabic lesson; preserve fillers, false starts and mistakes; Arabic script, English as English.')
AR = re.compile(r'[؀-ۿ]')
PAD_IN, PAD_OUT = 0.15, 0.25

wins = json.load(io.open(R / 'check02_windows.json', encoding='utf-8'))
words = [w for w in json.load(io.open(ROOT / a.segments_from, encoding='utf-8'))['words'] if w['type'] == 'word']
# Amal = speaker with the higher Arabic share inside the lesson (same rule as lesson_pipeline)
share = {}
for w in words:
    if w['start'] < 173: continue
    s = share.setdefault(w['speaker_id'], [0, 0]); s[0] += 1; s[1] += bool(AR.search(w['text']))
amal = max(share, key=lambda k: share[k][1] / share[k][0])
NAME = {k: ('Amal' if k == amal else 'Medi') for k in share}
print('speaker map', NAME)

def slices(st, en):
    """Consecutive same-speaker ElevenLabs words inside the window (>=60% of the word inside)."""
    out = []
    for w in words:
        dur = max(0.05, w['end'] - w['start']); ins = min(w['end'], en) - max(w['start'], st)
        if ins / dur < 0.6: continue
        if out and out[-1]['spk_id'] == w['speaker_id'] and w['start'] - out[-1]['e'] < 1.5:
            out[-1]['e'] = max(out[-1]['e'], w['end']); out[-1]['n'] += 1; out[-1]['ref'].append(w['text'])
        else:
            out.append({'spk_id': w['speaker_id'], 's': w['start'], 'e': max(w['end'], w['start'] + 0.3), 'n': 1, 'ref': [w['text']]})
    for i, s in enumerate(out):   # pad, but never into the neighbour slice
        lo = out[i - 1]['e'] if i else st; hi = out[i + 1]['s'] if i + 1 < len(out) else en
        s['cs'] = max(lo, s['s'] - PAD_IN, st); s['ce'] = min(hi, s['e'] + PAD_OUT, en)
    return out

def cut(s, e, path):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s:.3f}', '-to', f'{e:.3f}', '-i', str(AUDIO), '-ac', '1', '-ar', '16000', str(path)], check=True)

def transcribe(path):
    for attempt in range(3):
        with open(path, 'rb') as f:
            r = requests.post('https://api.openai.com/v1/audio/transcriptions', headers={'Authorization': f'Bearer {KEY}'},
                              data=[('model', a.model), ('response_format', 'json'), ('prompt', PROMPT), ('languages[]', 'ar'), ('languages[]', 'en')],
                              files={'file': (path.name, f, 'audio/wav')}, timeout=300)
        if r.status_code == 200:
            return r.json().get('text', '').strip(), r.status_code
        print('   http', r.status_code, r.text[:200])
        if r.status_code in (401, 402): sys.exit(1)
        time.sleep(2)
    return '', r.status_code

only = {int(x) for x in a.only.split(',') if x}
out = {}
tmp = Path(tempfile.mkdtemp(prefix='recipe1_'))
for w in wins:
    if only and w['i'] not in only: continue
    t0 = time.time(); segs = []
    for j, s in enumerate(slices(w['start'], w['end'])):
        p = tmp / f"{w['i']:02d}_{j:02d}.wav"; cut(s['cs'], s['ce'], p)
        text, code = transcribe(p)
        segs.append({'spk': NAME[s['spk_id']], 's': round(s['cs'], 2), 'e': round(s['ce'], 2), 'text': text, 'n_ele': s['n'], 'ele': ' '.join(s['ref'])})
    out[str(w['i'])] = segs
    print(w['i'], f'{time.time() - t0:.0f}s', len(segs), 'slices', sum(len(x['text'].split()) for x in segs), 'words vs eleven', sum(x['n_ele'] for x in segs))
    io.open(R / a.out, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
print('saved', len(out), 'clips ->', a.out)
