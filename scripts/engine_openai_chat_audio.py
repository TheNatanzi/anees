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
wins = json.load(io.open(R / 'check02_windows.json', encoding='utf-8'))
out = {}
for w in wins:
    t0 = time.time()
    b64 = base64.b64encode(open(ROOT / w['clip'], 'rb').read()).decode()
    body = {'model': MODEL, 'modalities': ['text'], 'temperature': 0,
            'messages': [{'role': 'system', 'content': SYS},
                         {'role': 'user', 'content': [{'type': 'text', 'text': 'Transcribe this clip verbatim.'},
                                                      {'type': 'input_audio', 'input_audio': {'data': b64, 'format': 'mp3'}}]}]}
    r = requests.post('https://api.openai.com/v1/chat/completions', headers={'Authorization': f'Bearer {key}'}, json=body, timeout=300)
    if r.status_code != 200:
        print(w['i'], r.status_code, r.text[:300]); 
        if r.status_code in (401, 402, 429): sys.exit(1)
        continue
    txt = r.json()['choices'][0]['message']['content'].strip()
    segs = []
    for line in txt.splitlines():
        line = line.strip()
        if not line: continue
        spk, _, rest = line.partition(':')
        segs.append({'spk': spk.strip() if rest else '?', 's': w['start'], 'e': w['end'], 'text': (rest or line).strip()})
    out[str(w['i'])] = segs
    print(w['i'], f'{time.time()-t0:.0f}s', len(txt.split()), 'words')
io.open(R / 'openai_chat_clips.json', 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
print('saved', len(out))
