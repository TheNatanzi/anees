"""ChatGPT the way people use it: the chat model with audio attached + a full instruction (gpt-4o-audio-preview).
Writes data/aug25/openai_chat_clips.json {clip_index: [{'spk','s','e','text'}]}"""
import json, io, os, sys, base64, time, requests
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; R = ROOT / 'data' / 'aug25'
key = os.environ.get('OPENAI_API_KEY') or sys.exit('MISSING OPENAI_API_KEY')
MODEL = os.environ.get('OPENAI_CHAT_AUDIO_MODEL', 'gpt-4o-audio-preview')
SYS = ("You are a verbatim transcriber for a Palestinian (Levantine) Arabic lesson. Two speakers: a learner (adult man, non-native, "
       "makes mistakes) and a tutor (native Palestinian woman). They mix Levantine Arabic and English mid-sentence. "
       "Rules: write Arabic in Arabic script exactly as pronounced (dialect, not Modern Standard Arabic), English in English. "
       "Never translate. Never fix the learner's mistakes. Keep fillers (um, uh, آآآ, أمم), repetitions and false starts. "
       "Output one line per turn as 'Learner:' or 'Tutor:' followed by the words. No commentary.")
SYS = os.environ.get('OPENAI_SYS') or (SYS + " You MUST always output the words you hear; an empty answer is never acceptable. If unsure of a word, write your best guess followed by (?).")
RETRIES = int(os.environ.get('OPENAI_RETRIES', '3'))
FMT = os.environ.get('OPENAI_AUDIO_FMT', 'mp3')   # mp3 or wav
wins = json.load(io.open(R / 'check02_windows.json', encoding='utf-8'))
ONLY = os.environ.get('ONLY_CLIPS')
if ONLY:
    keep = {int(x) for x in ONLY.split(',')}
    wins = [w for w in wins if w['i'] in keep]
raw = {}
out = {}
for w in wins:
    t0 = time.time()
    src = ROOT / w['clip']
    if FMT == 'wav':
        import subprocess, tempfile
        wav = Path(tempfile.gettempdir()) / (src.stem + '.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-ac', '1', '-ar', '24000', '-sample_fmt', 's16', str(wav)], check=True)
        src = wav
    b64 = base64.b64encode(open(src, 'rb').read()).decode()
    body = {'model': MODEL, 'modalities': ['text'], 'temperature': 0,
            'messages': [{'role': 'system', 'content': SYS},
                         {'role': 'user', 'content': [{'type': 'text', 'text': 'Transcribe this clip verbatim.'},
                                                      {'type': 'input_audio', 'input_audio': {'data': b64, 'format': FMT}}]}]}
    txt = ''
    for attempt in range(RETRIES):
        r = requests.post('https://api.openai.com/v1/chat/completions', headers={'Authorization': f'Bearer {key}'}, json=body, timeout=300)
        if r.status_code != 200:
            print(w['i'], r.status_code, r.text[:300])
            if r.status_code in (401, 402, 429): sys.exit(1)
            break
        j = r.json(); ch = j['choices'][0]
        txt = (ch['message'].get('content') or '').strip()
        raw[str(w['i'])] = {'finish_reason': ch.get('finish_reason'), 'refusal': ch['message'].get('refusal'), 'content': txt[:600], 'usage': j.get('usage'), 'attempts': attempt + 1}
        if txt:
            break
        body['temperature'] = 0.4   # nudge: identical retries tend to blank again
    segs = []
    for line in txt.splitlines():
        line = line.strip()
        if not line: continue
        spk, _, rest = line.partition(':')
        segs.append({'spk': spk.strip() if rest else '?', 's': w['start'], 'e': w['end'], 'text': (rest or line).strip()})
    out[str(w['i'])] = segs
    print(w['i'], f'{time.time()-t0:.0f}s', len(txt.split()), 'words')
OUT = os.environ.get('OPENAI_OUT', 'openai_chat_clips.json')
io.open(R / OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
io.open(R / (OUT.replace('.json', '_raw.json')), 'w', encoding='utf-8').write(json.dumps(raw, ensure_ascii=False, indent=1))
print('saved', len(out))
