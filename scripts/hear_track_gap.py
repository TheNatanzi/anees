# -*- coding: utf-8 -*-
"""Hear a stretch of one person's OWN track that the transcription engine left empty, on the Gemini plan ($0).

    python scripts/hear_track_gap.py 2026-10-28 medi 44:40 47:20          -> writes the gap-fill layer
    python scripts/hear_track_gap.py 2026-10-28 medi 44:40 47:20 --plan   -> shows the speech bursts, makes no call

Why (Medi 2026-10-29, "(a) Recover first"): on 2026-10-28 Scribe wrote no words for Medi's own track 44:40-47:20 although
his microphone is loud there (he was talking), so a counted grammar slip at 45:15 had no line of his to sit on and the
header counted one more slip than the transcript showed (check_numbers blocked the site). The ElevenLabs path of
fill_meet_gaps.py is a paid call; this one is free:

  1. Timing from the audio itself: ffmpeg silencedetect on his own track finds every speech burst in the window; bursts
     closer than GLUE_S are one line (the same glue as lesson_turns.turns_from_scribe). Line times are therefore real
     onsets on the track clock (lesson_t = track_t + tracks.json start.relative), never a model's guess.
  2. Words, engine 'plan' (default): Gemini on Medi's AI Pro plan (Antigravity CLI `agy -p`, file viewing only, no shell): each burst is cut to
     its own small clip and the model writes what HE says in each one, verbatim, mistakes kept, or "" when the clip holds
     no words of his (her voice through his speaker, a cough). API keys are stripped from the child's environment.
     Engine 'api' (only with Medi's yes + a --cap): the agreed best listener of the hearing test (way A, 2026-10-14):
     Gemini 3.8 Flash on the paid key, 3 listens per burst, vote. 2026-10-28 was heard this way: the plan's weekly quota
     ran out mid-read (Medi 2026-10-29: "use the method that we agreed on is the best", cap $1).
  3. Output = the same SOURCE LAYER as fill_meet_gaps.py (data/backfill/gapfill/<date>/gapfill_<side>.json, RULES.md S2:
     the raw transcripts are untouched), source 'own_track', engine named, line-level only (no per-word times: the
     model gives none worth keeping). build_lessons_page_data.py merges it like any gap fill. It is NOT an entry of
     data/backfill/meet_gaps.json: that queue is the Meet filler's (a pending entry there would be sent to paid Scribe).
"""
from __future__ import annotations

import argparse, datetime as dt, hashlib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    import track
except Exception:  # logging must never stop the hearing
    track = None

AGY = os.path.expandvars(r'%LOCALAPPDATA%\agy\bin\agy.exe')
MODEL = 'gemini-3.8-flash-high'
KEYS = ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'ANTHROPIC_API_KEY', 'ELEVENLABS_API_KEY')
NOISE_DB, MIN_SIL_S = -38, 0.7    # a pause of 0.7 s under -38 dB ends a burst
GLUE_S, MIN_BURST_S, PAD_S = 1.2, 0.3, 0.25
LAYERS = ROOT / 'data' / 'backfill' / 'gapfill'

PROMPT = """Use your file viewing tool (never a shell command) to open each audio clip listed below and listen to it.
Each clip is a few seconds of ONE learner's own microphone during an online Levantine (Jordanian) Arabic lesson with his
tutor Amal. He mixes English and Arabic. The tutor's voice may leak in faintly through his speaker.
For each clip write exactly what HE says: Arabic words in Arabic script, English words in English, word for word.
Keep his mistakes and false starts (e.g. a wrong verb form stays wrong); never fix or translate. Write "" when the clip
holds no words of his (silence, a cough, only the tutor's voice).
Clips: {clips}
Reply with ONLY this JSON object, one key per clip name, nothing else: {{"u01": "...", "u02": "..."}}"""

LISTENS = 3
API_PROMPT = """Audio of ONE speaker's own microphone: Medi, an American learner of Levantine (Jordanian) Arabic in an online
lesson with his tutor Amal. He mixes English and Arabic and makes learner mistakes. Amal's voice may leak in faintly
through his speaker: leave her words out. Write exactly what HE says, word for word: Arabic words in Arabic script,
English words in English. Keep his mistakes, wrong forms and false starts (never correct or translate). If the clip holds
no words of his (silence, a cough, only Amal), "said" is "".
Answer JSON only: {"said": "his words"}"""


def sec(s):
    m = re.fullmatch(r'(\d+):(\d\d)(?::(\d\d))?', s)
    if not m:
        return float(s)
    a, b, c = m.groups()
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def mmss(t):
    return '%d:%02d' % (int(t) // 60, int(t) % 60)


def own_track(date, side):
    meta = json.loads((ROOT / 'data' / 'lesson-work' / date / 'tracks' / 'tracks.json').read_text(encoding='utf-8'))
    want = {'medi': 'Medi', 'amal': 'Amal'}[side]
    for tr in meta['tracks']:
        if tr['participant'].split()[0] != want:
            continue
        f = Path(tr['file'])
        for p in (f, ROOT / 'data' / 'lessons' / date / 'tracks' / f.name,
                  Path(os.environ.get('ANEES_RAW') or ROOT / 'data' / 'lessons') / date / 'tracks' / f.name):
            if p.exists():
                return p, float(tr['start']['relative']), float(tr['duration_s'])
    raise SystemExit(f'{want} has no own track file for {date} on this machine')


def bursts(path, a, b):
    """[(from, to)] speech on the track clock inside [a, b] (silencedetect), glued over pauses <= GLUE_S."""
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-ss', str(a), '-t', str(b - a), '-i', str(path),
                          '-af', f'silencedetect=noise={NOISE_DB}dB:d={MIN_SIL_S}', '-f', 'null', '-'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    sil, cur = [], None
    for k, v in re.findall(r'silence_(start|end): ([0-9.]+)', out):
        if k == 'start':
            cur = a + float(v)
        else:
            sil.append((cur if cur is not None else a, a + float(v)))
            cur = None
    if cur is not None:
        sil.append((cur, b))
    speech, t = [], a
    for s, e in sil:
        if s > t:
            speech.append((t, s))
        t = max(t, e)
    if t < b:
        speech.append((t, b))
    glued = []
    for s, e in speech:
        if glued and s - glued[-1][1] <= GLUE_S:
            glued[-1] = (glued[-1][0], e)
        else:
            glued.append((s, e))
    return [(round(s, 2), round(e, 2)) for s, e in glued if e - s >= MIN_BURST_S]


def cut(path, spans, workdir):
    names = []
    for i, (s, e) in enumerate(spans, 1):
        n = 'u%02d' % i
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(max(0, s - PAD_S)), '-t',
                        str(e - s + 2 * PAD_S), '-i', str(path), '-ac', '1', '-b:a', '64k', str(Path(workdir) / f'{n}.mp3')],
                       check=True)
        names.append(n)
    return names


def _toks(x):
    return [w for w in re.sub(r'[^\w\s]', ' ', x or '').lower().split() if w]


def vote(listens):
    """Way A's 2-of-3 rule at line level: the listen sharing the most words with the other two stands for the burst, kept
    only when at least one other listen agrees with it on half its words or more (else "", nothing is invented).
    Returns (text, agreement 0-1)."""
    best, score = '', 0.0
    for i, x in enumerate(listens):
        tx = set(_toks(x))
        if not tx:
            continue
        agree = max((len(tx & set(_toks(y))) / len(tx) for j, y in enumerate(listens) if j != i), default=0.0)
        if agree > score:
            best, score = x, agree
    if not any(_toks(x) for x in listens) or sum(1 for x in listens if not _toks(x)) >= 2:
        return '', 1.0           # two or more listens heard no words of his: the burst is not his speech
    return (best, round(score, 2)) if score >= 0.5 else ('', round(score, 2))


def hear_api(path, spans, workdir, cap_usd):
    """The agreed best listener (hearing test 2026-10-14, way A): Gemini 3.8 Flash on the paid key, 3 listens per burst,
    vote. Each call goes through context_transcribe._gem (data/budget.json gemini cap + a run line per paid call);
    this run also stops itself before cap_usd (Medi 2026-10-29 "Yes, cap $1")."""
    import context_transcribe as CT
    names = cut(path, spans, workdir)
    spent, out, raw = 0.0, [], []
    for n in names:
        audio = (Path(workdir) / f'{n}.mp3').read_bytes()
        listens = []
        for _ in range(LISTENS):
            if spent + CT.USD_PER_CALL > cap_usd:
                raise SystemExit(f'stopped at ${spent:.3f}: the next listen would pass this run\'s ${cap_usd} cap')
            r = CT._gem(CT.MODEL, audio, API_PROMPT)
            spent += CT.USD_PER_CALL
            listens.append('' if r.get('error') else str(r.get('said') or '').strip())
            raw.append({'clip': n, 'answer': r})
        out.append((vote(listens), listens))
    return out, API_PROMPT, json.dumps(raw, ensure_ascii=False), CT.MODEL, round(spent, 4)


def hear(path, spans, workdir):
    names = cut(path, spans, workdir)
    prompt = PROMPT.format(clips=', '.join(str(Path(workdir) / f'{n}.mp3') for n in names))
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    t0, raw, got = time.time(), '', None
    for _ in range(3):   # agy sometimes answers empty or wraps the JSON: retry
        p = subprocess.run([AGY, '-p', prompt, '--add-dir', str(workdir), '--mode', 'plan', '--model', MODEL,
                            '--settings', json.dumps({'permissions': {'allow': ['read_file']}}), '--output-format', 'json'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=1200)
        raw = p.stdout
        try:
            resp = json.loads(raw[raw.index('{'):].split('\n')[0]).get('response') or ''
            got = json.loads(resp[resp.index('{'):resp.rindex('}') + 1])
            if all(n in got for n in names):
                break
        except Exception:
            got = None
    ms = int((time.time() - t0) * 1000)
    if track:
        track.log_run('track_gap_hear', None, provider='google-plan', request_model=MODEL,
                      status='ok' if got else 'error', duration_ms=ms, params={'clips': len(names)})
    if not got:
        raise SystemExit('Gemini gave no usable answer: ' + raw[-600:])
    return [str(got.get(n) or '').strip() for n in names], prompt, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('side', choices=('medi', 'amal'))
    ap.add_argument('frm'); ap.add_argument('to')
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--engine', choices=('plan', 'api'), default='plan',
                    help="plan = one agy read on the Gemini plan ($0); api = 3 paid listens + vote (needs Medi's yes + cap)")
    ap.add_argument('--cap', type=float, default=0.0, help='USD this run may spend (engine api)')
    a = ap.parse_args()
    lo, hi = sec(a.frm), sec(a.to)
    path, off, _dur = own_track(a.date, a.side)
    spans = bursts(path, lo - off, hi - off)
    print(f'{len(spans)} speech bursts on {path.name} {mmss(lo)}-{mmss(hi)}:',
          ' '.join('%s+%.1f' % (mmss(s + off), e - s) for s, e in spans))
    if a.plan or not spans:
        return
    with tempfile.TemporaryDirectory(prefix='anees-hear-') as wd:
        if a.engine == 'api':
            if a.cap <= 0:
                raise SystemExit('--engine api needs --cap (the dollars Medi said yes to)')
            got, prompt, raw, model, cost = hear_api(path, spans, wd, a.cap)
            texts, confs, listens = [g[0][0] for g in got], [g[0][1] for g in got], [g[1] for g in got]
            how = f'{model} on the paid Gemini key, {LISTENS} listens per burst, vote (context_transcribe._gem)'
        else:
            texts, prompt, raw = hear(path, spans, wd)
            confs, listens, model, cost = [None] * len(texts), [None] * len(texts), MODEL, 0.0
            how = f'{MODEL} on the Gemini plan (agy -p), one read of every burst'
    who = {'medi': 'Medi', 'amal': 'Amal'}[a.side]
    lines = [{'t': round(s + off, 2), 'end': round(e + off, 2), 'who': who, 'text': x, 'source': 'own_track',
              'from_meet': False, 'confidence': c, 'engine': model, 'n_words': len(x.split())}
             for (s, e), x, c in zip(spans, texts, confs) if x]
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    win = {'from_s': float(lo), 'to_s': float(hi), 'from': mmss(lo), 'to': mmss(hi), 'clock': 'lesson clock (docs/lessons/<date>/audio)'}
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    layer = {
        'schema': 2, 'kind': 'anees-gapfill-layer', 'date': a.date, 'side': who, 'missing': a.side, 'source': 'own_track',
        'status': 'machine_heard',
        'about': (f"{who}'s side of {mmss(lo)}-{mmss(hi)} (lesson clock): his own recording is loud there but the engine "
                  f"wrote no words. Line times are the speech bursts of the track (silencedetect); the words were heard by "
                  f"{how} (scripts/hear_track_gap.py). A source layer: the raw per-person transcripts are unchanged "
                  f"(RULES.md S2)."),
        'window': win,
        'summary': {'lines': len(lines), 'words': sum(L['n_words'] for L in lines), 'lines_by_source': {'own_track': len(lines)},
                    'primary_source': 'own_track', 'offset_s': off, 'residual_s': None, 'anchors': None,
                    'diarization_confidence': None, 'clip_mode': 'ffmpeg_cut', 'est_cost_usd': cost},
        'provenance': {'parts': [{'source': 'own_track', 'window': win, 'track_file': path.name, 'track_sha256': sha,
                                  'participant': who, 'offset_s': off,
                                  'clock_map': "lesson_t = track_t + offset_s (tracks.json start.relative)",
                                  'timing': f'silencedetect noise={NOISE_DB}dB d={MIN_SIL_S}s, glue {GLUE_S}s',
                                  'engine': {'how': how, 'model': model,
                                             'prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                                             'response_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest()},
                                  'bursts': [{'t': round(s + off, 2), 'end': round(e + off, 2), 'heard': x, 'agreement': c,
                                              **({'listens': ls} if ls else {})}
                                             for (s, e), x, c, ls in zip(spans, texts, confs, listens)],
                                  'est_cost_usd': cost}],
                       'built_at': now},
        'lines': lines, 'words': [],
    }
    out = LAYERS / a.date / f'gapfill_{a.side}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(layer, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'wrote {out.relative_to(ROOT).as_posix()}: {len(lines)} lines')
    for L in lines:
        print(' ', mmss(L['t']), L['text'])


if __name__ == '__main__':
    main()
