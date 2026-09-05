"""Anees lesson pipeline: new Meet recording -> ElevenLabs Scribe v2 -> readable transcript page -> email Medi.

Usage:
  python lesson_pipeline.py                 # process every new recording in the Meet Recordings folder
  python lesson_pipeline.py --reuse data/aug25/eleven_scribe_auto.json --file "G:/My Drive/Meet Recordings/vzq-tryv-mdw (2026-08-25 14 27 GMT-7)"
Needs ELEVENLABS_API_KEY in the environment (User env on Medi's PC)."""
import argparse, io, json, os, re, subprocess, sys, time, html, datetime
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lesson_text import runs_from_words, run_text, ARABIC, is_confirm

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(os.environ.get('MEET_RECORDINGS', 'G:/My Drive/Meet Recordings'))
LESSONS = ROOT / 'data' / 'lessons'
DOCS = ROOT / 'docs' / 'lessons'
STATE = LESSONS / 'processed.json'
PAGES = 'https://thenatanzi.github.io/anees/lessons/'
NAME_RE = re.compile(r'^[a-z]{3}-[a-z]{4}-[a-z]{3} \((\d{4}-\d{2}-\d{2}) (\d{2}) (\d{2}) GMT[-+]\d+\)( \(\d+\))?$')
MIN_BYTES = 20_000_000
MIN_ARABIC_SHARE = 0.12      # below this it was not an Arabic lesson


def log(*a):
    print(datetime.datetime.now().strftime('%H:%M:%S'), *a, flush=True)


def new_recordings(state):
    out = []
    for p in sorted(SRC.iterdir()):
        m = NAME_RE.match(p.name)
        if not m or p.stat().st_size < MIN_BYTES or p.name in state:
            continue
        out.append((p, m.group(1), f'{m.group(2)}{m.group(3)}'))
    return out


def extract_audio(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vn', '-ac', '1', '-ar', '16000', '-b:a', '48k', str(dst)], check=True)
    return dst


def is_arabic_lesson(mp3, d):
    """5-cent pre-check: transcribe minutes 3-6 only; skip the $1.50 full run when there is no Arabic."""
    sample = d / 'sample.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '180', '-t', '180', '-i', str(mp3), '-ac', '1', '-ar', '16000', '-b:a', '48k', str(sample)], check=True)
    res = transcribe(sample)
    ws = [w['text'] for w in res.get('words', []) if w.get('type') == 'word']
    share = sum(1 for w in ws if ARABIC.search(w)) / max(1, len(ws))
    log('pre-check', f'{len(ws)} words, arabic share {share:.2f}, language {res.get("language_code")}')
    return share >= MIN_ARABIC_SHARE or res.get('language_code') == 'ara'


def transcribe(mp3):
    key = os.environ.get('ELEVENLABS_API_KEY') or sys.exit('MISSING ELEVENLABS_API_KEY')
    with open(mp3, 'rb') as f:
        r = requests.post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key': key},
                          data={'model_id': 'scribe_v2', 'diarize': 'true', 'num_speakers': '2',
                                'timestamps_granularity': 'word', 'tag_audio_events': 'true'},
                          files={'file': (mp3.name, f, 'audio/mpeg')}, timeout=1800)
    if r.status_code != 200:
        raise RuntimeError(f'ElevenLabs {r.status_code}: {r.text[:300]}')
    return r.json()


CHAT_LINE = re.compile(r'^([A-Za-z][\w .-]{0,40}):\s?(.*)$')
MIN_MINORITY_SHARE = 0.05    # below this ElevenLabs put (nearly) everything on one voice = speaker split failed


def chat_sidecar(src):
    """Google Meet writes '<name> - Chat Transcript' next to the recording. Returns [(hh:mm:ss, name, text)]."""
    p = src.parent / (src.name + ' - Chat Transcript')
    if not p.exists():
        return []
    out, t, who = [], '', None
    for line in io.open(p, encoding='utf-8', errors='replace'):
        line = line.rstrip('\n')
        if re.match(r'^\d\d:\d\d:\d\d', line):
            t = line[:8]; who = None; continue
        m = CHAT_LINE.match(line)
        if m:
            who = m.group(1).strip(); out.append((t, who, m.group(2).strip()))
        elif line.strip() and who:
            out.append((t, who, line.strip()))
    return out


def pitch_labels(words, mp3):
    """Fallback when ElevenLabs merged the voices: label each word by voice pitch.
    Medi (man) speaks around 130 Hz, Amal (woman) around 215 Hz. Validated on Aug 25: 93% agreement with ElevenLabs.
    Words with no clear pitch stay '?' unless both neighbours agree."""
    import numpy as np, librosa
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp3), '-f', 's16le', '-ac', '1', '-ar', '16000', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = 800   # 50 ms
    f0 = librosa.yin(x, fmin=70, fmax=400, sr=16000, frame_length=1024, hop_length=hop)
    rms = librosa.feature.rms(y=x, frame_length=1024, hop_length=hop)[0]
    ok = rms > np.percentile(rms, 40)
    for w in words:
        a = int(w['s'] / 0.05); b = max(int(w['e'] / 0.05) + 1, a + 2)
        v = f0[a:b][ok[a:b]]
        if len(v) == 0:
            w['spk'] = '?'
        else:
            m = float(np.median(v)); w['spk'] = 'Medi' if m < 155 else ('Amal' if m > 180 else '?')
    for i, w in enumerate(words):
        if w['spk'] == '?' and 0 < i < len(words) - 1 and words[i - 1]['spk'] == words[i + 1]['spk'] != '?':
            w['spk'] = words[i - 1]['spk']
    return words


def label_speakers(words):
    """Amal = the speaker with the higher share of Arabic words (she teaches in Arabic; Medi mixes).
    If one voice got <5% of the words the split failed: label everyone 'Both' (never guess)."""
    stats = {}
    for w in words:
        s = stats.setdefault(w['spk'], [0, 0])
        s[0] += 1
        s[1] += 1 if ARABIC.search(w['w']) else 0
    if len(stats) < 2 or min(v[0] for v in stats.values()) / len(words) < MIN_MINORITY_SHARE:
        return {k: 'Both' for k in stats}
    ranked = sorted(stats, key=lambda k: stats[k][1] / max(1, stats[k][0]), reverse=True)
    return {ranked[0]: 'Amal', **{k: 'Medi' for k in ranked[1:]}}


def build(res, date, hhmm, src_name, mp3=None):
    words = [{'s': w.get('start', 0), 'e': w.get('end', 0), 'spk': w.get('speaker_id', '?'), 'w': w['text'].replace('\ufffd', '')}
             for w in res.get('words', []) if w.get('type') == 'word']
    if not words:
        raise RuntimeError('no words')
    arabic_share = sum(1 for w in words if ARABIC.search(w['w'])) / len(words)
    lab = label_speakers(words)
    for w in words:
        w['spk'] = lab.get(w['spk'], w['spk'])
    split_note = 'ok'
    if not any(v == 'Medi' for v in lab.values()):
        if mp3 and Path(mp3).exists():
            try:
                pitch_labels(words, mp3)
                split_note = 'from voice pitch: ElevenLabs merged the two voices, so each word was labeled by pitch (Medi low, Amal high); ? = unclear'
                log('speaker split failed -> pitch labels', {k: sum(1 for w in words if w['spk'] == k) for k in ('Medi', 'Amal', '?')})
            except Exception as e:
                log('pitch fallback failed', e)
                split_note = 'failed: ElevenLabs put almost every word on one voice, so nobody is labeled'
        else:
            split_note = 'failed: ElevenLabs put almost every word on one voice, so nobody is labeled'
    tutor_words = [w for w in words if w['spk'] == 'Amal']
    start = tutor_words[0]['s'] if tutor_words else words[0]['s']
    end = tutor_words[-1]['e'] if tutor_words else words[-1]['e']
    lesson = [w for w in words if start <= w['s'] <= end]
    runs = runs_from_words(lesson, tutor='Amal')
    split_ok = any(w['spk'] == 'Medi' for w in words)
    medi_ar = [w for w in lesson if (w['spk'] == 'Medi' or not split_ok) and ARABIC.search(w['w'])]
    confirms = sum(1 for r in runs for it in r['items'] if it.get('ok'))
    pauses = [it['pause'] for r in runs if r['spk'] == 'Medi' for it in r['items'] if 'pause' in it]
    summary = {'date': date, 'time': hhmm, 'source': src_name, 'lesson_start': round(start, 1), 'lesson_end': round(end, 1),
               'minutes': round((end - start) / 60, 1), 'words': len(lesson), 'arabic_share': round(arabic_share, 2),
               'medi_arabic_words': len(medi_ar), 'confirmations': confirms, 'medi_pauses': len(pauses),
               'medi_pause_seconds': round(sum(pauses), 1), 'language': res.get('language_code'),
               'language_probability': res.get('language_probability'), 'engine': 'elevenlabs scribe_v2',
               'speaker_split': split_note}
    return words, runs, summary


def render(runs, summary):
    def item_html(it):
        if 'pause' in it:
            return f'<span class="pz">(pause {it["pause"]}s)</span>'
        t = html.escape(it['w'])
        return f'<span class="ok">&#10003; {t}</span>' if it.get('ok') else t
    rows = []
    for r in runs:
        m, s = int(r['s'] // 60), int(r['s'] % 60)
        rows.append(f'<p class="ar {"unk" if r["spk"] == "?" else r["spk"].lower()}" dir="auto"><span class="t">{m:02d}:{s:02d}</span><b class="spk">{r["spk"]}:</b> '
                    + ' '.join(item_html(it) for it in r['items']) + '</p>')
    S = summary
    stats = ''.join(f'<div class="stat"><div class="n">{v}</div><div class="l">{k}</div></div>' for k, v in [
        ('minutes', S['minutes']), ('words', S['words']), ('Arabic words by Medi', S['medi_arabic_words']),
        ('Amal said "right"', S['confirmations']), ('Medi pauses', S['medi_pauses'])])
    warn = '' if S.get('speaker_split', 'ok') == 'ok' else f'<p class="warn">Speaker split {html.escape(S["speaker_split"])}. Counts below cover both voices.</p>'
    typed = ''
    if S.get('chat_lines'):
        items = ''.join(f'<li><span class="t">{html.escape(t)}</span><span dir="auto">{html.escape(txt)}</span></li>' for t, who, txt in S['chat_lines'])
        typed = f'<h2>Amal typed in the Meet chat</h2><p class="lead">Words she wrote for Medi during the call, in her own spelling (numbers stand for Arabic letters: 6 = ط, 7 = ح, 3 = ع).</p><ul class="typed">{items}</ul>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anees lesson {S['date']}</title>
<style>
:root{{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:16px}} h1{{font-size:24px;margin:8px 0 2px}} .lead{{color:var(--mute);margin:0 0 14px;font-size:14px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:0 0 18px}}
.stat{{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:10px 12px}} .n{{font-size:24px;font-weight:700}} .l{{font-size:12px;color:var(--mute)}}
.ar{{margin:8px 0;line-height:1.7;padding:6px 10px;border-radius:10px}} .medi{{background:var(--bg2);border:1px solid var(--line)}} .amal{{background:transparent}}
.spk{{font-size:13px;color:var(--teal);margin-inline-end:8px}} .t{{font-size:11px;color:var(--mute);margin-inline-end:8px;font-variant-numeric:tabular-nums}}
.pz{{color:var(--amber);font-size:13px;border:1px dashed var(--amber);border-radius:999px;padding:0 8px;white-space:nowrap}}
.ok{{color:var(--teal);font-size:13px;border:1px solid var(--teal);border-radius:999px;padding:0 8px;white-space:nowrap}}
.warn{{background:var(--bg2);border-left:4px solid var(--amber);padding:8px 12px;margin:0 0 14px}} h2{{font-size:19px;margin:22px 0 4px}}
.typed{{list-style:none;padding:0;margin:0 0 18px;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:6px}} .typed li{{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:6px 10px;font-size:18px}} .both,.unk{{background:var(--bg2);border:1px dashed var(--line)}}
</style></head><body><main>
<h1>Anees lesson, {S['date']}</h1>
<p class="lead">Transcribed by ElevenLabs Scribe v2. Fillers show as (pause), Amal's confirmations right after Medi's Arabic show as a green check. Lesson window {int(S['lesson_start']//60)}:{int(S['lesson_start']%60):02d} to {int(S['lesson_end']//60)}:{int(S['lesson_end']%60):02d}.</p>
{warn}<div class="stats">{stats}</div>
{typed}{''.join(rows)}
</main></body></html>'''


def email(summary, link):
    payload = {'headline': f"Lesson {summary['date']} is transcribed", 'sub': f"{summary['minutes']} minutes, {summary['words']} words. ElevenLabs Scribe v2.",
               'link': link, 'footer': 'Anees, automatic after every recorded lesson. Only Medi gets this email.',
               'rows': [{'tag': 'Arabic', 'name': f"{summary['medi_arabic_words']} Arabic words by Medi", 'detail': f"{int(summary['arabic_share']*100)}% of all words were Arabic"},
                        {'tag': 'Right', 'name': f"{summary['confirmations']} confirmations from Amal", 'detail': 'mhm / aha / ممتاز right after Medi spoke Arabic'},
                        {'tag': 'Pauses', 'name': f"{summary['medi_pauses']} pauses by Medi", 'detail': f"{summary['medi_pause_seconds']} seconds of um and uh"}],
               'text': f"Lesson {summary['date']} transcribed: {link}"}
    if summary.get('chat_lines'):
        payload['rows'].append({'tag': 'Typed', 'name': f"{len(summary['chat_lines'])} words Amal typed in the Meet chat", 'detail': ', '.join(txt for _, _, txt in summary['chat_lines'][:8])})
    if summary.get('speaker_split', 'ok') != 'ok':
        payload['rows'].append({'tag': 'Note', 'name': 'Speaker labels from voice pitch this time', 'detail': summary['speaker_split']})
    pf = LESSONS / summary['date'] / 'email.json'
    pf.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    subprocess.run(['node', str(ROOT / 'scripts' / 'send_lesson_email.mjs'), f"Anees: lesson {summary['date']} transcribed", str(pf)], check=True)


def publish(date, page_html):
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / f'{date}.html').write_text(page_html, encoding='utf-8')
    paths = [DOCS / f'{date}.html', STATE, LESSONS / date / 'summary.json', LESSONS / date / 'transcript.txt', ROOT / '.gitignore']
    subprocess.run(['git', '-C', str(ROOT), 'add'] + [str(x) for x in paths if x.exists()], check=True)
    subprocess.run(['git', '-C', str(ROOT), 'commit', '-q', '-m', f'Lesson {date}: transcript page\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'], check=False)
    subprocess.run(['git', '-C', str(ROOT), 'push', '-q'], check=False)
    return PAGES + f'{date}.html'


def process(src, date, hhmm, reuse=None, send=True, force=False):
    d = LESSONS / date
    d.mkdir(parents=True, exist_ok=True)
    if reuse:
        res = json.load(io.open(reuse, encoding='utf-8'))
    else:
        mp3 = extract_audio(src, d / 'audio.mp3')
        if not is_arabic_lesson(mp3, d):
            log('not an Arabic lesson (pre-check) -> skipped')
            return {'skipped': 'not arabic (pre-check)', 'date': date, 'source': src.name}
        log('transcribing', mp3.name)
        res = transcribe(mp3)
        (d / 'scribe.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    words, runs, summary = build(res, date, hhmm, src.name, mp3=d / 'audio.mp3')
    chat = chat_sidecar(src)
    tutor_typed = [(t, who, txt) for t, who, txt in chat if who.lower() != 'medi' and not who.lower().startswith('mahdi')]
    summary['chat_lines'] = tutor_typed
    if tutor_typed:
        log('Meet chat sidecar:', len(tutor_typed), 'lines typed by', sorted({who for _, who, _ in tutor_typed}))
    if summary['arabic_share'] < MIN_ARABIC_SHARE and not tutor_typed and not force:
        log('not an Arabic lesson (arabic share', summary['arabic_share'], ') -> skipped')
        return {'skipped': 'not arabic', **summary}
    (d / 'transcript.txt').write_text('\n'.join(f"[{int(r['s']//60):02d}:{int(r['s']%60):02d}] {r['spk']}: {run_text(r)}" for r in runs), encoding='utf-8')
    (d / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    page = render(runs, summary)
    (d / 'transcript.html').write_text(page, encoding='utf-8')
    link = publish(date, page)
    summary['link'] = link
    if send:
        email(summary, link)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file'); ap.add_argument('--reuse'); ap.add_argument('--no-email', action='store_true')
    ap.add_argument('--force', action='store_true', help='process even when the Arabic share is below the cut')
    a = ap.parse_args()
    LESSONS.mkdir(parents=True, exist_ok=True)
    state = json.load(io.open(STATE, encoding='utf-8')) if STATE.exists() else {}
    if a.file:
        p = Path(a.file); m = NAME_RE.match(p.name)
        todo = [(p, m.group(1), f'{m.group(2)}{m.group(3)}')] if m else [(p, datetime.date.today().isoformat(), '0000')]
    else:
        todo = new_recordings(state)
    if not todo:
        log('nothing new'); return
    for src, date, hhmm in todo:
        try:
            s = process(src, date, hhmm, reuse=a.reuse, send=not a.no_email, force=a.force)
            state[src.name] = {'date': date, 'done': datetime.datetime.now().isoformat(timespec='seconds'), **{k: s.get(k) for k in ('skipped', 'link', 'words')}}
            log('done', src.name, s.get('link') or s.get('skipped'))
        except Exception as e:
            log('FAILED', src.name, e)
            state[src.name] = {'date': date, 'failed': str(e)[:200], 'done': datetime.datetime.now().isoformat(timespec='seconds')}
        STATE.write_text(json.dumps(state, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
