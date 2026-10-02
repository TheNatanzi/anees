# -*- coding: utf-8 -*-
"""Gap filler: recover a MISSING speaker's side of a lesson from Google Meet's own mixed recording (Medi 2026-09-28: "do it").

    python scripts/fill_meet_gaps.py                 -> process every pending entry of data/backfill/meet_gaps.json
    python scripts/fill_meet_gaps.py --list          -> show the queue
    python scripts/fill_meet_gaps.py --plan          -> show what would be cut / paid for, make no call

Lessons are transcribed from the recording bot's two per-person tracks. Sometimes one track is empty for a stretch
(2026-09-26: Amal 00:00-20:17; 2026-09-23: Medi 00:00-23:45). Meet's host recording is ONE file with both voices, so:

  1. Clock map. Meet start = its file name (minute precision), lesson start = docs/data/lessons.json start_local, so
     meet_t ~= lesson_t + initial_offset. The true offset is up to 60 s smaller (the name drops the seconds), so the clip
     is cut to the gap window + that minute + MARGIN_S (60 s) each side:
       - ffmpeg on PATH -> mode 'ffmpeg_cut': only the clip is sent (the normal case, on the hourly machine);
       - no ffmpeg     -> mode 'whole_file': the Meet file is sent whole and the window is selected afterwards
                          (costs the full recording; logged as such in the layer and the run log).
     Then REFINED by alignment: the PRESENT side's words (its turns in docs/data/lessons/<date>.json, lesson clock) are
     matched to the Meet transcript's timed words; the densest cluster of (meet_t - lesson_t) over same-word pairs gives
     the offset, and the median of the exact anchors (the first word of each turn) near it is the fitted offset. The layer
     reports that offset, its residual (median |error|, p90) and the anchor count; a residual over MAX_RESIDUAL_S or too
     few anchors fails the entry (nothing is written).
  2. Scribe v2 on the clip, diarize=true, num_speakers=2, word timestamps: pipeline_ext.transcribe_with_retry (the same
     call shape, retries, 90 % budget stop and paid-call ledger as every lesson). A saved response is never paid twice.
  3. Speaker choice: the diarized speaker whose words match the present side's aligned words is the PRESENT person;
     the other speaker (most words in the gap) is the MISSING one. confidence = present speaker's share of the matches.
  4. Output = a new SOURCE LAYER, never an edit of a raw transcript (RULES.md S2):
       data/backfill/gapfill/<date>/gapfill_<side>.json   (committed) lines + words of the missing side inside the gap,
                                                           each tagged source 'meet_mixed', from_meet true, confidence;
                                                           provenance: Meet file name + sha256, offsets, residual,
                                                           diarization, clip, run_id, raw response sha256
       <ANEES_RAW>/<date>/gapfill_<side>.scribe.json      the raw Scribe response (raw archive, never committed, like
                                                           every scribe*.json) + gapfill_<side>.clip.mp3
  5. build_lessons_page_data.py merges the layer into the lesson turns / talk window / coverage note; the sentence
     ladder carries from_meet through to its sentences.

Own track first (entry 'prefer': 'own_track', 2026-09-23): when the missing person's OWN Recall recording exists but was
never transcribed (<ANEES_RAW>/<date>/tracks/tracks.json; 09-23: Medi's first recording 0:00-22:37), that single-voice
file is transcribed instead (same Scribe path + budget check, run step track_gap_fill), placed by its start.relative;
whatever of the window it does not cover (09-23: 22:37-23:45) comes from a Meet clip (step meet_gap_fill). No such file
on the machine -> the whole window comes from Meet. Lines carry source 'own_track' or 'meet_mixed' (+ from_meet).

The hourly job (scripts/hourly_lessons.py -> gap_fill_refresh) runs process_queue() once per hour on the machine that
has the ElevenLabs key and ffmpeg. Without a key nothing is paid and the queue is left untouched.
Queue entries: pending -> done | failed. Transient problems (no key, Meet file not synced, budget) leave an entry pending
and untouched; a failed paid call or a failed alignment counts an attempt; MAX_ATTEMPTS attempts -> failed.
"""
from __future__ import annotations

import argparse, bisect, datetime as dt, hashlib, json, math, os, re, shutil, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

QUEUE = ROOT / 'data' / 'backfill' / 'meet_gaps.json'
LAYERS = ROOT / 'data' / 'backfill' / 'gapfill'
LESSONS_JSON = ROOT / 'docs' / 'data' / 'lessons.json'
LESSON_DOCS = ROOT / 'docs' / 'data' / 'lessons'
DRIVE = Path(os.environ.get('ANEES_DRIVE', 'G:/My Drive'))
RAW = Path(os.environ.get('ANEES_RAW', str(ROOT / 'data' / 'lessons')))

MEET_NAME = re.compile(r'([a-z]{3}-[a-z]{4}-[a-z]{3}) \((\d{4}-\d{2}-\d{2}) (\d{2})[ :](\d{2}) GMT([-+]\d+)\)')
MARGIN_S = 60.0          # s of audio kept on each side of the gap window (beyond the name's 60 s uncertainty)
NAME_SLACK_S = 60.0      # the Meet file name has minutes only: the true offset is up to this much smaller
SEARCH_S = 150.0         # s searched around the initial offset
MATCH_TOL = 0.75         # s: a present word and a Meet word with the same text this close = the same spoken word
CLUSTER_W = 1.5          # s: width of the densest-offset window
MIN_ANCHORS = 8
MAX_RESIDUAL_S = 1.0     # median |anchor error| above this = the clocks do not line up: fail, write nothing
MIN_DIAR_CONF = 0.6      # present speaker's share of the matched words below this = speakers not separable
OVERLAP_DROP_S = 0.4     # a missing-side word with the same text as a present word within this = one word, mislabelled
GLUE = 1.2               # s: words closer than this are one line (same as build_lessons_page_data.GLUE)
MAX_ATTEMPTS = 3
SIDES = {'amal': 'Amal', 'medi': 'Medi'}
OTHER = {'Amal': 'Medi', 'Medi': 'Amal'}


def log(*parts):
    print(dt.datetime.now().strftime('%H:%M:%S'), 'gapfill:', *parts, flush=True)


def J(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save(p, obj, indent=1):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding='utf-8')
    os.replace(tmp, p)


def mmss(t):
    t = int(round(t))
    return f'{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}' if t >= 3600 else f'{t // 60:02d}:{t % 60:02d}'


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ queue

def load_queue(path=QUEUE):
    return J(path) if Path(path).exists() else {'entries': []}


def entry_id(date, missing):
    return f'{date}-{missing}'


def ensure_entry(queue, date, missing, from_s, to_s, meet_file, note=None):
    """Add a pending entry unless one with the same id exists (idempotent seeding). Returns (entry, added)."""
    eid = entry_id(date, missing)
    for e in queue['entries']:
        if e['id'] == eid:
            return e, False
    e = {'id': eid, 'date': date, 'missing': missing, 'window': {'from_s': float(from_s), 'to_s': float(to_s),
         'from': mmss(from_s), 'to': mmss(to_s), 'clock': 'lesson clock (docs/lessons/<date>/audio)'},
         'meet_file': meet_file.replace('\\', '/'), 'status': 'pending', 'attempts': 0, 'run_ids': [], 'last_error': None,
         'result': None, **({'note': note} if note else {})}
    queue['entries'].append(e)
    return e, True


# ------------------------------------------------------------------ clocks

def meet_start(meet_name):
    """Local start of a Meet recording from its file name ('code (YYYY-MM-DD HH MM GMT-7)') as an aware datetime."""
    m = MEET_NAME.search(Path(meet_name).name)
    if not m:
        raise ValueError(f'not a Meet recording name: {meet_name}')
    tz = dt.timezone(dt.timedelta(hours=int(m.group(5))))
    return dt.datetime.fromisoformat(f'{m.group(2)}T{m.group(3)}:{m.group(4)}:00').replace(tzinfo=tz)


def lesson_start(date, lessons_json=LESSONS_JSON):
    row = next((L for L in J(lessons_json)['lessons'] if L['date'] == date), None)
    if not row or not row.get('start_local'):
        raise ValueError(f'{date}: no start_local in docs/data/lessons.json')
    return dt.datetime.fromisoformat(row['start_local']), row.get('start_source'), row.get('duration_min')


def initial_offset(meet_name, lesson_start_dt):
    """meet_t = lesson_t + offset (seconds). The name drops seconds, so the true value is in (offset - 60, offset]."""
    return (lesson_start_dt - meet_start(meet_name)).total_seconds()


def clip_bounds(window, offset0, margin=MARGIN_S):
    """Meet-clock [from, to] covering the gap window whatever the true offset in (offset0 - NAME_SLACK_S, offset0]."""
    a = max(0.0, window['from_s'] + offset0 - NAME_SLACK_S - margin)
    b = window['to_s'] + offset0 + margin
    return round(a, 2), round(b, 2)


# ------------------------------------------------------------------ text

_DIAC = re.compile(r'[\u064B-\u0670\u06DF-\u06ED\u0640]')


def norm(tok):
    s = _DIAC.sub('', str(tok or '')).lower()
    s = re.sub('[أإآٱ]', 'ا', s).replace('ى', 'ي').replace('ة', 'ه').replace('ؤ', 'و').replace('ئ', 'ي')
    return re.sub(r'[^\w\u0600-\u06FF]+', '', s)


def present_tokens(turns, side):
    """[(lesson_t, norm_token, exact)] of one side's own lines (chat and earlier gap-fill lines excluded). The first token
    of a line sits at the line's start (exact); the rest are spread over the line by character length (approximate)."""
    out = []
    for t in turns:
        if t.get('who') != side or t.get('from_meet') or t.get('chat'):
            continue
        toks = [x for x in re.split(r'\s+', t.get('text') or '') if x]
        toks = [(x, norm(x)) for x in toks]
        if not toks:
            continue
        t0 = float(t['t'])
        t1 = t.get('end')
        t1 = float(t1) if t1 is not None and float(t1) > t0 else t0 + 0.35 * len(toks)
        total = sum(max(1, len(x)) for x, _ in toks)
        acc = 0
        for i, (x, n) in enumerate(toks):
            if len(n) >= 2:
                out.append((t0 + (t1 - t0) * acc / total, n, i == 0))
            acc += max(1, len(x))
    out.sort()
    return out


def meet_words(scribe, clip_start):
    """[{s, e, text, n, spk, lp}] of the Scribe response, on the MEET clock (clip time + clip start)."""
    out = []
    for w in scribe.get('words') or []:
        if w.get('type') != 'word' or w.get('start') is None:
            continue
        out.append({'s': float(w['start']) + clip_start, 'e': float(w.get('end') or w['start']) + clip_start,
                    'text': (w.get('text') or '').strip(), 'n': norm(w.get('text')), 'spk': w.get('speaker_id') or '?',
                    'lp': w.get('logprob')})
    out.sort(key=lambda w: w['s'])
    return out


# ------------------------------------------------------------------ alignment

def _index(mw):
    idx = defaultdict(list)
    for i, w in enumerate(mw):
        if len(w['n']) >= 2:
            idx[w['n']].append((w['s'], i))
    return idx


def fit_offset(present, mw, offset0, search=SEARCH_S, tol=MATCH_TOL):
    """Refine meet_t = lesson_t + offset. Returns {offset_s, residual_s, residual_p90_s, anchors, pairs, basis,
    drift_s_per_hour, ok, why}. Pure: synthetic tests drive it directly."""
    idx = _index(mw)
    lo, hi = offset0 - NAME_SLACK_S - search, offset0 + search
    diffs = []
    for t, n, _ in present:
        for s, _i in idx.get(n, ()):
            d = s - t
            if lo <= d <= hi:
                diffs.append(d)
    out = {'initial_offset_s': round(offset0, 2), 'search_s': [round(lo, 1), round(hi, 1)], 'pairs': len(diffs)}
    if not diffs:
        return {**out, 'ok': False, 'why': 'no word of the present side appears in the Meet transcript'}
    diffs.sort()
    best, j, mode = 0, 0, diffs[0]
    for i in range(len(diffs)):                         # densest CLUSTER_W window of offsets
        while diffs[i] - diffs[j] > CLUSTER_W:
            j += 1
        if i - j + 1 > best:
            best, mode = i - j + 1, (diffs[i] + diffs[j]) / 2
    exact, loose = [], []
    for t, n, is_first in present:
        cand = [s - t for s, _ in idx.get(n, ()) if abs(s - t - mode) <= tol + CLUSTER_W / 2]
        if not cand:
            continue
        d = min(cand, key=lambda x: abs(x - mode))
        (exact if is_first else loose).append((t, d))
    use, basis = (exact, 'first word of each line') if len(exact) >= MIN_ANCHORS else (exact + loose, 'all matched words')
    if len(use) < MIN_ANCHORS:
        return {**out, 'ok': False, 'anchors': len(use), 'why': f'only {len(use)} anchor words matched (need {MIN_ANCHORS})'}
    off = median(d for _, d in use)
    err = sorted(abs(d - off) for _, d in use)
    kept = [(t, d) for t, d in use if abs(d - off) <= max(3 * err[len(err) // 2], 0.3)]
    off = median(d for _, d in kept)
    err = sorted(abs(d - off) for _, d in kept)
    res, p90 = median(err), err[min(len(err) - 1, int(0.9 * len(err)))]
    drift = None
    if len(kept) >= 20:
        mt = sum(t for t, _ in kept) / len(kept)
        vt = sum((t - mt) ** 2 for t, _ in kept)
        if vt > 0:
            drift = sum((t - mt) * (d - off) for t, d in kept) / vt * 3600
    ok = res <= MAX_RESIDUAL_S
    return {**out, 'ok': ok, 'why': None if ok else f'residual {res:.2f} s > {MAX_RESIDUAL_S} s',
            'offset_s': round(off, 3), 'residual_s': round(res, 3), 'residual_p90_s': round(p90, 3),
            'anchors': len(kept), 'anchors_dropped': len(use) - len(kept), 'basis': basis, 'cluster_votes': best,
            'drift_s_per_hour': round(drift, 3) if drift is not None else None}


def choose_speakers(present, mw, offset, window, tol=MATCH_TOL):
    """Credit each present word to the diarized speaker of its matching Meet word. present speaker = most credits;
    missing speaker = the other speaker with the most words inside the gap. Returns a dict (ok False when unclear)."""
    idx = _index(mw)
    credit = Counter()
    for t, n, _ in present:
        cand = [(abs(s - t - offset), i) for s, i in idx.get(n, ()) if abs(s - t - offset) <= tol]
        if cand:
            credit[mw[min(cand)[1]]['spk']] += 1
    in_gap = Counter(w['spk'] for w in mw if window['from_s'] <= w['s'] - offset < window['to_s'])
    total = Counter(w['spk'] for w in mw)
    out = {'speakers': {k: {'words': total[k], 'words_in_gap': in_gap[k], 'present_matches': credit[k]} for k in sorted(total)}}
    if not credit:
        return {**out, 'ok': False, 'why': 'no present word matched any diarized speaker'}
    present_spk = credit.most_common(1)[0][0]
    others = [k for k in total if k != present_spk]
    if not others:
        return {**out, 'ok': False, 'present_speaker': present_spk, 'why': 'diarization found one speaker only'}
    missing_spk = max(others, key=lambda k: (in_gap[k], total[k]))
    conf = credit[present_spk] / sum(credit.values())
    ok = conf >= MIN_DIAR_CONF and in_gap[missing_spk] > 0
    return {**out, 'ok': ok, 'present_speaker': present_spk, 'missing_speaker': missing_spk, 'confidence': round(conf, 3),
            'why': None if ok else (f'speaker split unclear (present share {conf:.2f})' if conf < MIN_DIAR_CONF else 'the missing speaker has no words in the gap')}


def group_lines(words, side, base_conf, source):
    """Words (lesson clock) -> lines: a new line after a GLUE s pause or a sentence end. confidence = base_conf x the
    mean word confidence (exp logprob) when the engine gave one."""
    lines, cur = [], None
    for w in words:
        if cur and w['s'] - cur['end'] < GLUE and not re.search(r'[.?!؟]$', cur['words'][-1]['text']):
            cur['words'].append(w); cur['end'] = max(cur['end'], w['e'])
        else:
            if cur:
                lines.append(cur)
            cur = {'t': w['s'], 'end': w['e'], 'words': [w]}
    if cur:
        lines.append(cur)
    out = []
    for L in lines:
        wc = [w['conf'] for w in L['words'] if w['conf'] is not None]
        conf = base_conf * (sum(wc) / len(wc)) if wc else base_conf
        out.append({'t': round(L['t'], 2), 'end': round(L['end'], 2), 'who': side,
                    'text': ' '.join(w['text'] for w in L['words']), 'source': source, 'from_meet': source == 'meet_mixed',
                    'confidence': round(conf, 2), 'n_words': len(L['words'])})
    return out


def _conf(lp):
    return round(math.exp(lp), 3) if isinstance(lp, (int, float)) else None


def select_missing(mw, present, offset, window, missing_spk, side, diar_conf):
    """The missing speaker's words inside the gap, on the LESSON clock, minus words that coincide with the same present
    word (one spoken word labelled twice). Returns (words, lines, dropped)."""
    pres = defaultdict(list)
    for t, n, _ in present:
        pres[n].append(t)
    words, dropped = [], 0
    for w in mw:
        if w['spk'] != missing_spk:
            continue
        s, e = w['s'] - offset, w['e'] - offset
        if not (window['from_s'] <= s < window['to_s']):
            continue
        if any(abs(s - t) <= OVERLAP_DROP_S for t in pres.get(w['n'], ())):
            dropped += 1
            continue
        words.append({'s': round(s, 3), 'e': round(max(e, s), 3), 'text': w['text'], 'who': side, 'conf': _conf(w.get('lp')),
                      'source': 'meet_mixed'})
    return words, group_lines(words, side, diar_conf, 'meet_mixed'), dropped


def track_words(scribe, track_offset, window, side):
    """Every word of a ONE-PERSON track inside the window, on the lesson clock (lesson_t = track_t + track_offset, the
    tracks.json start.relative - the same placement as the lesson's own tracks). No speaker choice: it is his microphone."""
    out = []
    for w in scribe.get('words') or []:
        if w.get('type') != 'word' or w.get('start') is None:
            continue
        s = float(w['start']) + track_offset
        if window['from_s'] <= s < window['to_s']:
            e = float(w.get('end') or w['start']) + track_offset
            out.append({'s': round(s, 3), 'e': round(max(e, s), 3), 'text': (w.get('text') or '').strip(), 'who': side,
                        'conf': _conf(w.get('logprob')), 'source': 'own_track'})
    return out


# ------------------------------------------------------------------ audio + paid call (injectable for tests)

class Transient(RuntimeError):
    """Leave the entry pending and untouched (retry next hour, no attempt counted)."""


class NoKey(Transient):
    pass


class FitError(RuntimeError):
    """Alignment / speaker choice / empty selection (not a paid-call failure)."""


def have_ffmpeg():
    return bool(shutil.which('ffmpeg'))


def ffprobe_minutes(path):
    if not shutil.which('ffprobe'):
        return None
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip()) / 60
    except ValueError:
        return None


def cut_clip(src, dst, a, b):
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.2f}', '-t', f'{b - a:.2f}', '-i', str(src), '-vn', '-ac', '1',
                    '-ar', '16000', '-b:a', '48k', str(dst)], check=True, timeout=900)
    return dst


def scribe_call(path, minutes, who='mixed'):
    """The one paid call: Scribe v2 through pipeline_ext.transcribe_with_retry (diarize, 2 speakers, word timestamps,
    3 retries, 90 % budget stop, ledger). Only reached with a key on this machine. who = 'mixed' for the Meet file,
    the person for his own track (pipeline_ext picks that track's name keyterms when it supports them)."""
    import requests, pipeline_ext as px
    from anees_env import env
    import inspect
    key = env('ELEVENLABS_API_KEY')
    if not key:
        raise NoKey('no ELEVENLABS_API_KEY on this machine')
    extra = {'who': who} if 'who' in inspect.signature(px.transcribe_with_retry).parameters else {}
    return px.transcribe_with_retry(requests.post, path, key, minutes, **extra)


def paid_call_possible():
    try:
        from anees_env import env
        return bool(env('ELEVENLABS_API_KEY'))
    except Exception:
        return False


def _call(transcribe, path, minutes, who, run_id):
    """transcribe(path, minutes[, who=]) with ANEES_PARENT_RUN_ID set so the scribe.transcribe run line links to ours."""
    prev = os.environ.get('ANEES_PARENT_RUN_ID')
    if run_id:
        os.environ['ANEES_PARENT_RUN_ID'] = run_id
    try:
        try:
            return transcribe(path, minutes, who=who)
        except TypeError as e:
            if 'who' not in str(e):
                raise
            return transcribe(path, minutes)
    finally:
        if prev is None:
            os.environ.pop('ANEES_PARENT_RUN_ID', None)
        else:
            os.environ['ANEES_PARENT_RUN_ID'] = prev


def _preflight(transcribe, src, minutes, budget_ok, step, date, params):
    """Nothing is paid and no attempt counted when the key, the file or the budget is missing (Transient)."""
    if not Path(src).exists():
        raise Transient(f'source audio not on this machine: {src}')
    transcribe = transcribe or scribe_call
    if transcribe is scribe_call and not paid_call_possible():
        raise Transient('no ELEVENLABS_API_KEY on this machine: nothing paid, entry left pending')
    import pipeline_ext as px
    est = minutes * px.ELEVEN_USD_PER_MIN
    if not (budget_ok or px.budget_ok)('elevenlabs', est):
        import track
        track.log_run(step, date, kind='ingest', provider='elevenlabs', request_model='scribe_v2', status='skipped_budget',
                      params=params, usage={'audio_min': round(minutes, 3)})
        raise Transient(f'ElevenLabs budget: {est:.3f} USD would pass 90 % of the cap')
    return transcribe, est


# ------------------------------------------------------------------ one entry

def layer_path(entry, layers=LAYERS):
    return Path(layers) / entry['date'] / f"gapfill_{entry['missing']}.json"


def _is_person(participant, side):
    p = (participant or '').lower()
    return p.startswith(side.lower()) or (side == 'Medi' and ('natanzi' in p or 'mahdi' in p))


def find_own_track(entry, raw=RAW):
    """The missing person's OWN Recall recording that covers the gap start but was never transcribed (09-23: Medi's first
    recording 0:00-22:37). Read from <raw>/<date>/tracks/tracks.json. Returns (track dict with a resolved 'path', why)."""
    side, win = SIDES[entry['missing']], entry['window']
    tj = Path(raw) / entry['date'] / 'tracks' / 'tracks.json'
    if not tj.exists():
        return None, f'no tracks.json at {tj}'
    used = None
    pv = Path(raw) / entry['date'] / f'scribe_{side}.provenance.json'
    if pv.exists():
        try:
            used = Path(J(pv).get('source_file') or '').name or None
        except Exception:
            used = None
    cands = []
    for t in J(tj).get('tracks') or []:
        if not _is_person(t.get('participant'), side):
            continue
        rel0 = float((t.get('start') or {}).get('relative') or 0.0)
        dur = float(t.get('duration_s') or 0.0)
        if dur <= 0 or rel0 > win['from_s'] + 60 or rel0 + dur <= win['from_s']:
            continue
        f = Path(t.get('file') or '')
        path = f if f.exists() else Path(raw) / entry['date'] / 'tracks' / f.name
        if used and path.name == used:
            continue                                     # that one is already transcribed: not the gap's cause
        if (Path(raw) / entry['date'] / f'scribe_{side}_seg{int(rel0)}.json').exists():
            continue                                     # the lesson load already has it as a segment (rule TR-17)
        cands.append({**t, 'path': str(path), 'offset_s': rel0, 'duration_s': dur})
    if not cands:
        return None, f'no untranscribed {side} track covering {win["from"]} in tracks.json'
    best = min(cands, key=lambda t: t['offset_s'])
    if not Path(best['path']).exists():
        return None, f'{side} track file missing on this machine: {best["path"]}'
    return best, None


def meet_fill(entry, window, suffix, drive, raw, lessons_json, lesson_docs, transcribe, cutter, ffmpeg, budget_ok):
    """Meet mixed-recording method for one lesson-clock window. Returns {'lines', 'words', 'provenance', 'run_id'}.
    Raises Transient (nothing paid), FitError (alignment / speakers / empty), or a paid-call error."""
    import track
    side = SIDES[entry['missing']]
    present_side = OTHER[side]
    date = entry['date']
    src = Path(drive) / entry['meet_file']
    raw_dir = Path(raw) / date
    raw_json = raw_dir / f"gapfill_{entry['missing']}{suffix}.scribe.json"
    clip = raw_dir / f"gapfill_{entry['missing']}{suffix}.clip.mp3"
    ls, ls_src, dur_min = lesson_start(date, lessons_json)
    off0 = initial_offset(src.name, ls)
    a, b = clip_bounds(window, off0)
    turns = J(Path(lesson_docs) / f'{date}.json')['turns']
    present = present_tokens(turns, present_side)
    if not present:
        raise FitError(f'{date}: no {present_side} lines to align on')
    reused = raw_json.exists()
    mode, minutes, est = None, None, 0.0
    if not reused:
        ffmpeg = have_ffmpeg() if ffmpeg is None else ffmpeg
        if ffmpeg:
            mode, minutes = 'ffmpeg_cut', (b - a) / 60
        else:
            # no ffmpeg: the whole Meet file goes to Scribe and the window is selected afterwards (full-length cost)
            mode, a, b = 'whole_file', 0.0, None
            minutes = (ffprobe_minutes(src) if src.exists() else None) or ((dur_min or 75) + max(off0, 0) / 60 + 10)
        transcribe, est = _preflight(transcribe, src, minutes, budget_ok, 'meet_gap_fill', date, {'missing': side, 'clip_mode': mode})
    with track.run('meet_gap_fill', date, kind='ingest', provider='elevenlabs', request_model='scribe_v2',
                   inputs=[raw_json] if reused else [], outputs=[raw_json],
                   params={'missing': side, 'source': 'meet_mixed', 'window_s': [window['from_s'], window['to_s']],
                           'margin_s': MARGIN_S, 'diarize': True, 'num_speakers': 2, 'timestamps_granularity': 'word'}) as rec:
        run_id = rec.get('run_id')
        if reused:                                   # never pay twice for the same clip
            scribe = J(raw_json)
            meta = scribe.get('_anees_clip') or {}
            mode, a, b = meta.get('mode', 'ffmpeg_cut'), meta.get('meet_from_s', a), meta.get('meet_to_s', b)
            minutes, meet_sha = meta.get('minutes'), meta.get('meet_sha256')
            rec.set(params={'reused_response': True})
        else:
            if mode == 'ffmpeg_cut':
                (cutter or cut_clip)(src, clip, a, b)
                send = clip
                minutes = ffprobe_minutes(clip) or minutes
                import pipeline_ext as px
                est = minutes * px.ELEVEN_USD_PER_MIN
            else:
                send = src
            rec.set(params={'clip_mode': mode})
            log(entry['id'], 'meet', mode, f'meet {mmss(a)}-{mmss(b) if b else "end"}', f'{minutes:.1f} min', f'~{est:.3f} USD')
            meet_sha = sha256_file(src)
            scribe = _call(transcribe, send, minutes, 'mixed', run_id)
            if not isinstance(scribe, dict) or not scribe.get('words'):
                raise RuntimeError('Scribe returned no words')
            scribe = {**scribe, '_anees_clip': {'mode': mode, 'meet_from_s': a, 'meet_to_s': b, 'minutes': round(minutes, 3),
                                                'meet_file': src.name, 'meet_sha256': meet_sha, 'est_usd': round(est, 4)}}
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_json.write_text(json.dumps(scribe, ensure_ascii=False), encoding='utf-8')
        mw = meet_words(scribe, a if mode == 'ffmpeg_cut' else 0.0)
        fit = fit_offset(present, mw, off0)
        rec.set(metrics={k: fit.get(k) for k in ('offset_s', 'residual_s', 'residual_p90_s', 'anchors', 'drift_s_per_hour')},
                usage={'audio_min': minutes})
        if not fit['ok']:
            raise FitError('alignment failed: ' + fit['why'])
        spk = choose_speakers(present, mw, fit['offset_s'], window)
        rec.set(metrics={'diarization_confidence': spk.get('confidence')})
        if not spk['ok']:
            raise FitError('speaker choice failed: ' + spk['why'])
        words, lines, dropped = select_missing(mw, present, fit['offset_s'], window, spk['missing_speaker'], side, spk['confidence'])
        if not lines:
            raise FitError(f'no {side} words inside the gap after selection')
        rec.set(metrics={'lines': len(lines), 'words': len(words)})
        prov = {
            'source': 'meet_mixed', 'window': window,
            'meet_file': entry['meet_file'], 'meet_file_name': src.name, 'meet_sha256': meet_sha,
            'meet_start_local': meet_start(src.name).isoformat(), 'lesson_start_local': ls.isoformat(), 'lesson_start_source': ls_src,
            'clock_map': 'lesson_t = meet_t - offset_s',
            'initial_offset_s': round(off0, 2), 'offset_s': fit['offset_s'], 'residual_s': fit['residual_s'],
            'residual_p90_s': fit['residual_p90_s'], 'anchors': fit['anchors'], 'anchor_basis': fit['basis'],
            'drift_s_per_hour': fit['drift_s_per_hour'], 'alignment_side': present_side,
            'clip': {'mode': mode, 'meet_from_s': a, 'meet_to_s': b, 'minutes': minutes, 'margin_s': MARGIN_S},
            'scribe_raw': {'path': f'<ANEES_RAW>/{date}/{raw_json.name}', 'sha256': sha256_file(raw_json), 'reused': reused,
                           'request': {'model_id': 'scribe_v2', 'diarize': True, 'num_speakers': 2,
                                       'timestamps_granularity': 'word', 'tag_audio_events': True},
                           'language_code': scribe.get('language_code')},
            'diarization': {**spk, 'overlap_dropped': dropped}, 'run_id': run_id, 'est_cost_usd': round(est, 4)}
    return {'lines': lines, 'words': words, 'provenance': prov, 'run_id': run_id}


def track_fill(entry, trk, raw, transcribe, budget_ok):
    """Own-track method: Scribe on the missing person's own untranscribed Recall recording (single voice), placed on the
    lesson clock by its tracks.json start.relative. Returns {'lines', 'words', 'provenance', 'run_id', 'covered'}."""
    import track
    side, win, date = SIDES[entry['missing']], entry['window'], entry['date']
    src = Path(trk['path'])
    raw_json = Path(raw) / date / f"gapfill_{entry['missing']}.track.scribe.json"
    off, dur = trk['offset_s'], trk['duration_s']
    covered = {'from_s': max(win['from_s'], off), 'to_s': min(win['to_s'], off + dur)}
    reused = raw_json.exists()
    minutes, est = dur / 60, 0.0
    if not reused:
        minutes = ffprobe_minutes(src) or minutes
        transcribe, est = _preflight(transcribe, src, minutes, budget_ok, 'track_gap_fill', date, {'missing': side, 'source': 'own_track'})
    with track.run('track_gap_fill', date, kind='ingest', provider='elevenlabs', request_model='scribe_v2',
                   inputs=[src], outputs=[raw_json],
                   params={'missing': side, 'source': 'own_track', 'window_s': [win['from_s'], win['to_s']],
                           'diarize': True, 'num_speakers': 2, 'timestamps_granularity': 'word'}) as rec:
        run_id = rec.get('run_id')
        if reused:
            scribe = J(raw_json)
            rec.set(params={'reused_response': True})
        else:
            log(entry['id'], 'own track', src.name, f'{minutes:.1f} min', f'~{est:.3f} USD')
            scribe = _call(transcribe, src, minutes, side, run_id)
            if not isinstance(scribe, dict) or not scribe.get('words'):
                raise RuntimeError('Scribe returned no words')
            scribe = {**scribe, '_anees_track': {'file': src.name, 'sha256': sha256_file(src), 'offset_s': off,
                                                 'minutes': round(minutes, 3), 'est_usd': round(est, 4)}}
            raw_json.parent.mkdir(parents=True, exist_ok=True)
            raw_json.write_text(json.dumps(scribe, ensure_ascii=False), encoding='utf-8')
        words = track_words(scribe, off, covered, side)
        rec.set(usage={'audio_min': minutes}, metrics={'words': len(words)})
        if not words:
            raise FitError(f'{side} own track has no words in {mmss(covered["from_s"])}-{mmss(covered["to_s"])}')
        lines = group_lines(words, side, 1.0, 'own_track')
        rec.set(metrics={'lines': len(lines)})
        meta = scribe.get('_anees_track') or {}
        prov = {'source': 'own_track', 'window': {**covered, 'from': mmss(covered['from_s']), 'to': mmss(covered['to_s'])},
                'track_file': src.name, 'track_sha256': meta.get('sha256') or sha256_file(src), 'participant': trk.get('participant'),
                'clock_map': 'lesson_t = track_t + offset_s (tracks.json start.relative, the placement of the lesson\'s own tracks)',
                'offset_s': off, 'duration_s': dur,
                'scribe_raw': {'path': f'<ANEES_RAW>/{date}/{raw_json.name}', 'sha256': sha256_file(raw_json), 'reused': reused,
                               'request': {'model_id': 'scribe_v2', 'diarize': True, 'num_speakers': 2,
                                           'timestamps_granularity': 'word', 'tag_audio_events': True},
                               'language_code': scribe.get('language_code')},
                'run_id': run_id, 'est_cost_usd': round(est, 4)}
    return {'lines': lines, 'words': words, 'provenance': prov, 'run_id': run_id, 'covered': covered}


REST_MIN_S = 5.0     # an uncovered rest of the window shorter than this is left alone


def process_entry(entry, drive=DRIVE, raw=RAW, layers=LAYERS, lessons_json=LESSONS_JSON, lesson_docs=LESSON_DOCS,
                  transcribe=None, cutter=None, ffmpeg=None, budget_ok=None, now=None):
    """Fill one gap and write its layer. Returns the layer dict. Raises Transient (leave pending; nothing paid, no attempt
    counted), or any other exception (counts an attempt).

    prefer 'own_track' (09-23): the missing person's own untranscribed Recall recording is transcribed first; whatever of
    the window it does not cover (09-23: 22:37-23:45) is filled from the Meet clip. No such file on this machine -> the
    whole window comes from the Meet clip (the fallback is written into the layer)."""
    side, win, date = SIDES[entry['missing']], entry['window'], entry['date']
    mk = dict(drive=drive, raw=raw, lessons_json=lessons_json, lesson_docs=lesson_docs, transcribe=transcribe,
              cutter=cutter, ffmpeg=ffmpeg, budget_ok=budget_ok)
    parts, fallback, rests = [], None, []
    if entry.get('prefer') == 'own_track':
        trk, why = find_own_track(entry, raw)
        if trk:
            part = track_fill(entry, trk, raw, transcribe, budget_ok)
            parts.append(part)
            cov = part['covered']
            rests = [r for r in ({'from_s': win['from_s'], 'to_s': cov['from_s']}, {'from_s': cov['to_s'], 'to_s': win['to_s']})
                     if r['to_s'] - r['from_s'] >= REST_MIN_S]
        else:
            fallback = why
            log(entry['id'], 'own track not usable, Meet clip instead:', why)
    if not parts:
        parts.append(meet_fill(entry, win, '', **mk))
    for r in rests:
        r = {**r, 'from': mmss(r['from_s']), 'to': mmss(r['to_s'])}
        try:
            parts.append(meet_fill(entry, r, f".meet_{int(r['from_s'])}-{int(r['to_s'])}", **mk))
        except FitError as ex:                        # e.g. he was not in the call at all while his mic reconnected
            parts.append({'lines': [], 'words': [], 'run_id': None,
                          'provenance': {'source': 'meet_mixed', 'window': r, 'status': 'nothing_filled', 'why': str(ex)[:300]}})
            log(entry['id'], 'Meet rest', r['from'], '-', r['to'], 'not filled:', str(ex)[:200])
    lines = sorted((L for p in parts for L in p['lines']), key=lambda L: L['t'])
    words = sorted((w for p in parts for w in p['words']), key=lambda w: w['s'])
    first = parts[0]['provenance']
    meet = next((p['provenance'] for p in parts if p['provenance'].get('source') == 'meet_mixed' and 'offset_s' in p['provenance']), None)
    by = Counter(L['source'] for L in lines)
    summary = {'lines': len(lines), 'words': len(words), 'lines_by_source': dict(by), 'primary_source': first['source'],
               'offset_s': first.get('offset_s'), 'residual_s': (meet or {}).get('residual_s'), 'anchors': (meet or {}).get('anchors'),
               'diarization_confidence': ((meet or {}).get('diarization') or {}).get('confidence'),
               'clip_mode': ((meet or {}).get('clip') or {}).get('mode'),
               'est_cost_usd': round(sum(p['provenance'].get('est_cost_usd') or 0 for p in parts), 4),
               **({'own_track_fallback': fallback} if fallback else {})}
    src_words = {'own_track': "his/her own untranscribed recording", 'meet_mixed': "Google Meet's mixed recording"}
    layer = {
        'schema': 2, 'kind': 'anees-gapfill-layer', 'date': date, 'side': side, 'missing': entry['missing'],
        'source': first['source'], 'status': 'machine_transcribed',
        'about': f"{side}'s side of {win['from']}-{win['to']} (lesson clock), recovered from "
                 + ' + '.join(src_words[p['provenance']['source']] + f" ({p['provenance']['window'].get('from', mmss(p['provenance']['window']['from_s']))}-"
                              f"{p['provenance']['window'].get('to', mmss(p['provenance']['window']['to_s']))})" for p in parts)
                 + '. A source layer: the raw per-person transcripts are unchanged (RULES.md S2).',
        'window': win, 'summary': summary,
        'provenance': {'parts': [p['provenance'] for p in parts],
                       'run_ids': [p['run_id'] for p in parts if p.get('run_id')],
                       'built_at': (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec='seconds'),
                       **({'own_track_fallback': fallback} if fallback else {}),
                       # the Meet part's fields at the top too (the builders + older readers read these)
                       **({k: meet.get(k) for k in ('meet_file_name', 'meet_sha256', 'offset_s', 'residual_s', 'anchors', 'diarization', 'clip')} if meet else {})},
        'lines': lines, 'words': words,
    }
    save(layer_path(entry, layers), layer)
    return layer


def rel(p):
    p = Path(p).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


# ------------------------------------------------------------------ queue runner (the hourly hook calls this)

def process_queue(queue_path=QUEUE, **kw):
    """Process every pending entry once. Returns {'done': [ids], 'failed': [ids], 'pending': [ids], 'changed': bool}.
    Writes the queue only when an entry changed. Never raises for one entry's failure."""
    q = load_queue(queue_path)
    out = {'done': [], 'failed': [], 'pending': [], 'changed': False}
    for e in q['entries']:
        if e.get('status') != 'pending':
            continue
        try:
            layer = process_entry(e, **kw)
            s, p = layer['summary'], layer['provenance']
            e.update(status='done', last_error=None, result={'layer': rel(layer_path(e, kw.get('layers', LAYERS))), **s,
                                                            'done_at': p['built_at']})
            for rid in p.get('run_ids') or []:
                e.setdefault('run_ids', []).append(rid)
            out['done'].append(e['id']); out['changed'] = True
            log(e['id'], 'done', s['lines'], 'lines', s['lines_by_source'], f"offset {s['offset_s']} s, residual {s['residual_s']} s")
        except Transient as ex:
            out['pending'].append(e['id'])
            log(e['id'], 'left pending:', str(ex)[:200])
        except Exception as ex:
            e['attempts'] = e.get('attempts', 0) + 1
            e['last_error'] = f'{type(ex).__name__}: {str(ex)[:300]}'
            e['status'] = 'failed' if e['attempts'] >= MAX_ATTEMPTS else 'pending'
            (out['failed'] if e['status'] == 'failed' else out['pending']).append(e['id'])
            out['changed'] = True
            log(e['id'], 'attempt', e['attempts'], 'failed:', e['last_error'][:200])
    if out['changed']:
        q['updated'] = dt.datetime.now().astimezone().isoformat(timespec='seconds')
        save(queue_path, q)
    return out


# ------------------------------------------------------------------ what the builders read

def layers_for(date, layers=LAYERS):
    """Every finished gap-fill layer of a lesson (build_lessons_page_data.py reads these)."""
    d = Path(layers) / date
    return [J(p) for p in sorted(d.glob('gapfill_*.json'))] if d.exists() else []


def plan_entry(entry, drive=DRIVE, lessons_json=LESSONS_JSON):
    src = Path(drive) / entry['meet_file']
    ls, _, dur = lesson_start(entry['date'], lessons_json)
    off0 = initial_offset(src.name, ls)
    a, b = clip_bounds(entry['window'], off0)
    import pipeline_ext as px
    trk, why = find_own_track(entry) if entry.get('prefer') == 'own_track' else (None, None)
    return {'id': entry['id'], 'status': entry['status'], 'prefer': entry.get('prefer'),
            'own_track': ({'file': Path(trk['path']).name, 'covers_s': [trk['offset_s'], trk['offset_s'] + trk['duration_s']],
                           'est_usd': round(trk['duration_s'] / 60 * px.ELEVEN_USD_PER_MIN, 3)} if trk else why),
            'meet_file_found': src.exists(), 'initial_offset_s': off0,
            'clip_meet_s': [a, b], 'clip_min': round((b - a) / 60, 1), 'est_usd_clip': round((b - a) / 60 * px.ELEVEN_USD_PER_MIN, 3),
            'est_usd_whole_file': round(((dur or 70) + off0 / 60) * px.ELEVEN_USD_PER_MIN, 3), 'ffmpeg': have_ffmpeg(),
            'key_on_this_machine': paid_call_possible()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--plan', action='store_true')
    a = ap.parse_args()
    q = load_queue()
    if a.list:
        for e in q['entries']:
            print(e['id'], e['status'], e['window']['from'], '-', e['window']['to'], e.get('last_error') or '')
        return 0
    if a.plan:
        for e in q['entries']:
            print(json.dumps(plan_entry(e), indent=1))
        return 0
    r = process_queue()
    print(json.dumps(r, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
