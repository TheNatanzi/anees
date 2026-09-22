"""Scorecard for every lesson: coverage, speakers, page+audio, database, Word Bank binding, chat, reliability audit.

  python scripts/audit_lessons.py --raw C:/dev/anees/data/lessons --work <scratch> [--out plan/LESSON-AUDIT-2026-09-23.md]

Read-only except the scratch folder and the report. Lessons whose saved transcripts are on this PC are rebuilt with
scripts/load_lesson.py (no provider call) so the database can be compared event by event; older lessons are checked
from their published page and evidence.
"""
from __future__ import annotations

import argparse, collections, json, random, re, subprocess, sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
SITE = 'https://thenatanzi.github.io/anees/'
SILENT_DB = -45.0


def loudness(path, start, end):
    """Max 1-second RMS (dBFS) of an audio file between start and end."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(max(0, start)), '-t', str(max(0.5, end - start)), '-i', str(path),
                          '-f', 's16le', '-ac', '1', '-ar', '8000', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(x) < 800:
        return -120.0
    n = max(1, len(x) // 8000)
    chunks = [x[i * 8000:(i + 1) * 8000] for i in range(n)] or [x]
    return max(20 * np.log10(np.sqrt(np.mean(c ** 2)) + 1e-9) for c in chunks if len(c))


def envelope_db(path, rate=10):
    """Whole-file loudness at `rate` frames/s (dBFS), for quick lookups."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le', '-ac', '1', '-ar', '8000', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = 8000 // rate; n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)


def silent_credits(events, sources, rate=10, floor=-70.0):
    """Scored Medi events whose OWN source audio is silent (< floor dBFS) for the whole event = words credited but not heard."""
    env, bad = {}, []
    for e in events:
        if e['speaker'] != 'Medi' or not e.get('spoken') or e.get('ignored'):
            continue
        src = sources.get(e['source_id'])
        if not src:
            continue
        if src['input_path'] not in env:
            env[src['input_path']] = envelope_db(src['input_path'], rate)
        a, b = int(e['local_start'] * rate), int(e['local_end'] * rate) + 1
        seg = env[src['input_path']][a:b]
        if len(seg) and float(seg.max()) < floor:
            bad.append((round(e['t_start'], 1), e.get('word_key'), round(float(seg.max()), 1)))
    return bad


def coverage(intervals, duration, audio):
    iv = sorted((s, e) for s, e in intervals if s is not None and e is not None)
    merged = []
    for s, e in iv:
        if merged and s <= merged[-1][1] + 60:        # talk with pauses under a minute counts as covered
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    first, last = (merged[0][0], merged[-1][1]) if merged else (0, 0)
    gaps = [(a[1], b[0]) for a, b in zip(merged, merged[1:])]
    loud_gaps = [(round(a), round(b), round(loudness(audio, a, b), 1)) for a, b in gaps if b - a > 60]
    loud_gaps = [g for g in loud_gaps if g[2] > SILENT_DB]
    span = sum(e - s for s, e in merged)
    return {'covered_min': round(span / 60, 1), 'audio_min': round(duration / 60, 1), 'share': round(span / duration, 3) if duration else 0,
            'lesson_window_share': round(span / (last - first), 3) if last > first else 0, 'speech_gaps_over_60s': loud_gaps}


def spot_check(rows, audio, who='Medi', n=5, seed=7):
    pick = [r for r in rows if r['speaker_label'] == who and r.get('timeline_start') is not None and r['timeline_end'] - r['timeline_start'] > 0.6]
    random.Random(seed).shuffle(pick)
    out = []
    for r in pick[:n]:
        db_level = loudness(audio, r['timeline_start'], r['timeline_end'])
        out.append((round(r['timeline_start'], 1), round(float(db_level), 1), db_level > SILENT_DB))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--raw', required=True); ap.add_argument('--work', required=True)
    ap.add_argument('--out', default=str(ROOT / 'plan' / 'LESSON-AUDIT-2026-09-23.md'))
    ap.add_argument('--meet-root', default='G:/My Drive')
    a = ap.parse_args()
    import db, load_lesson as L, sync_speaking_lesson as S, build_lesson_page as P
    raw_root, work = Path(a.raw), Path(a.work)
    lessons = sorted(db.select('lessons', {'select': 'date,source,speaker_split,unlabeled_share,summary'}, retries=1), key=lambda r: r['date'])
    live_events = db.rest('GET', 'rpc/speaking_snapshot', retries=1)['events']
    patches = json.loads((ROOT / 'docs/data/word-bank-review.json').read_text(encoding='utf-8'))['patches']
    raw_by_id = {e['id']: e for e in live_events}                                                # source binding is checked on the raw event
    live_events = [{**e, **patches.get(e['id'], {}).get('changes', {})} for e in live_events]     # judged as the Word Bank shows them
    by_date = collections.defaultdict(list)
    for e in live_events:
        by_date[e['lesson_date']].append(e)
    published = json.loads((ROOT / 'docs/data/word-bank-evidence.json').read_text(encoding='utf-8'))['events']
    pub_by_date = collections.Counter(e['lesson_date'] for e in published)
    checks = json.loads((ROOT / 'docs/data/word-bank-audit-checks.json').read_text(encoding='utf-8'))['ledger']
    rel = collections.Counter(r['date'] for r in checks if any(v is False for c in r['passes'].values() for v in c.values()))
    meet_dirs = list(Path(a.meet_root, 'Google Meet').glob('*')) + [Path(a.meet_root, 'Meet Recordings')]
    rows_out, notes = [], {}
    for les in lessons:
        d = les['date']; raw = raw_root / d; res = {'date': d}
        page = requests.get(f'{SITE}lessons/{d}.html', timeout=60)
        html = page.text if page.ok else ''
        m = re.search(r'id="(?:lesson-audio|hosted-audio)"[^>]*src="([^"]+)"', html)
        audio_ok = False
        if m:
            h = requests.head(f'{SITE}lessons/{m.group(1)}', timeout=60); audio_ok = h.ok and int(h.headers.get('content-length', 0)) > 1_000_000
        elif d == '2026-09-10':
            h = requests.head(f'{SITE}lessons/2026-09-10/audio/Amal.mp3', timeout=60); audio_ok = h.ok
        res['page'] = page.ok and audio_ok
        res['page_note'] = ('opens + audio' if res['page'] else ('opens, no playable audio' if page.ok else f'HTTP {page.status_code}'))
        res['db_events'] = len(by_date.get(d, [])); res['published_events'] = pub_by_date.get(d, 0)
        res['lesson_row'] = True
        res['reliability_failures'] = rel.get(d, 0)
        chat_page = html.count('class="chat"') or len(re.findall(r'<li><span class="t">', html))
        side = None
        for folder in meet_dirs:
            for f in folder.glob(f'*({d} * - Chat Transcript'):
                if any(c['who'] == 'Amal' for c in P.parse_chat(f.read_text(encoding='utf-8', errors='replace'))):
                    side = f
        side_lines = len(P.parse_chat(side.read_text(encoding='utf-8', errors='replace'))) if side else 0
        res['chat'] = f'{chat_page}/{side_lines}' if side else 'no chat file'
        res['chat_ok'] = (not side) or chat_page >= side_lines * 0.9
        built = None
        try:
            if (raw / 'tracks' / 'tracks.json').exists() and (raw / 'scribe_Amal.json').exists():
                built = L.build_tracks(d, raw, work / 'audit' / d)
            elif (raw / 'scribe.json').exists() and (raw / 'audio.mp3').exists() and d >= '2026-09-18':
                built = L.build_mixed(d, raw, (work / 'audit' / d))
        except Exception as ex:
            notes[d] = f'rebuild failed: {ex}'
        if built:
            data, info = built
            audio = ROOT / 'docs' / 'lessons' / d / 'audio' / 'lesson.mp3'
            dur = L.ffprobe_duration(audio)
            res['coverage'] = coverage([(r['timeline_start'], r['timeline_end']) for r in data['rows']], dur, audio)
            res['speakers'] = 'tracks' if info['kind'] == 'tracks' else f"estimated, {round(info['unlabeled_share'] * 100, 1)}% unlabeled"
            res['speakers_ok'] = info['kind'] == 'tracks' or info['unlabeled_share'] < 0.05
            share = collections.Counter(r['speaker_label'] for r in data['rows'])
            res['row_share'] = {k: round(v / sum(share.values()), 2) for k, v in share.items()}
            res['spot'] = spot_check(data['rows'], audio)
            res['spot_ok'] = all(s[2] for s in res['spot'])
            events = S.detected_events(d, data=data)
            L.guard_events(events, data, info)
            rebuilt = {e['id'] for e in events if e['speaker'] == 'Medi'}
            live = {e['id'] for e in by_date.get(d, []) if e['speaker'] == 'Medi'}
            res['medi_uncredited'] = len(rebuilt - live); res['medi_not_rebuilt'] = len(live - rebuilt)
            items = {i['id']: (r, i) for r in data['rows'] for i in r['items']}
            scored = [e for e in by_date.get(d, []) if e['speaker'] == 'Medi' and e.get('spoken')]
            sample = scored if len(scored) < 20 else random.Random(3).sample(scored, 20)
            bad = []
            for e in (raw_by_id[x['id']] for x in sample):
                bound = [items.get(i) for i in e.get('item_ids') or []]
                if not bound or any(b is None for b in bound) or ' '.join(i['text'] for _, i in bound) != e['original_text'] or any(r['speaker_label'] != 'Medi' for r, _ in bound):
                    bad.append(e['id'][:8])
            same_build = {e['source_id'] for e in by_date.get(d, [])} <= set(data['sources'])
            silent = silent_credits(by_date.get(d, []), data['sources']) if same_build else []
            res['silent_credits'] = silent
            if same_build:
                res['wordbank_sample'] = f"{len(sample) - len(bad)}/{len(sample)} bound to Medi's own words, {len(silent)} credited over silence"
                res['wordbank_ok'] = not bad and res['medi_uncredited'] == 0 and not silent
            else:
                res['medi_uncredited'] = 0
                res['wordbank_sample'] = 'events built from an older transcript of this lesson; published = live: ' + str(res['published_events'] == res['db_events'])
                res['wordbank_ok'] = res['published_events'] == res['db_events']
        else:
            res['speakers'] = les.get('speaker_split'); res['speakers_ok'] = None
            res['wordbank_sample'] = 'transcript source not on this PC; published = live: ' + str(res['published_events'] == res['db_events'])
            res['wordbank_ok'] = res['published_events'] == res['db_events']
        res['db_ok'] = res['db_events'] > 0 and res['published_events'] == res['db_events']
        rows_out.append(res); print(json.dumps(res, default=str)[:400], flush=True)
    write_report(a.out, rows_out, notes)


def mark(ok):
    return '✅' if ok else ('—' if ok is None else '❌')


def write_report(out, rows, notes):
    lines = ['# Lesson audit — every lesson, 2026-09-23', '',
             'Built by `scripts/audit_lessons.py` (re-runnable). ✅ pass · ❌ fail · — cannot be measured here.', '',
             '| Lesson | Coverage | Speakers | Page + audio | 5 lines vs audio | Database | Word Bank | Chat merged | Reliability |',
             '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        cov = r.get('coverage')
        cov_ok = cov and cov['lesson_window_share'] >= 0.9 and not cov['speech_gaps_over_60s']
        cov_txt = (f"{mark(cov_ok)} {cov['covered_min']}/{cov['audio_min']} min" + (f", {len(cov['speech_gaps_over_60s'])} speech gaps" if cov['speech_gaps_over_60s'] else '')) if cov else '—'
        spot = r.get('spot')
        lines.append(f"| {r['date']} | {cov_txt} | {mark(r.get('speakers_ok'))} {r.get('speakers')} | {mark(r['page'])} {r['page_note']} | "
                     f"{(mark(r['spot_ok']) + ' ' + str(sum(s[2] for s in spot)) + '/5') if spot else '—'} | {mark(r['db_ok'])} {r['db_events']} events | "
                     f"{mark(r['wordbank_ok'])} {r['wordbank_sample']}" + (f"; {r['medi_uncredited']} uncredited" if r.get('medi_uncredited') else '') +
                     f" | {mark(r['chat_ok'])} {r['chat']} | {mark(r['reliability_failures'] == 0)} {r['reliability_failures']} |")
    lines += ['', '## Details', '']
    for r in rows:
        extra = []
        if r.get('coverage', {}).get('speech_gaps_over_60s'):
            extra.append('speech gaps (start s, end s, loudest dBFS): ' + str(r['coverage']['speech_gaps_over_60s']))
        if r.get('spot'):
            extra.append('spot checks (row start s, dBFS, speech): ' + str(r['spot']))
        if r.get('row_share'):
            extra.append('row share: ' + str(r['row_share']))
        if r.get('silent_credits'):
            extra.append('credited over silence (t, word, dBFS): ' + str(r['silent_credits']))
        if r.get('medi_not_rebuilt') and 'older transcript' not in r.get('wordbank_sample', ''):
            extra.append(f"{r['medi_not_rebuilt']} live Medi events not produced by today's matcher (older build or reviewed additions; kept)")
        if r['date'] in notes:
            extra.append(notes[r['date']])
        if extra:
            lines.append(f"- **{r['date']}**: " + ' · '.join(extra))
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
