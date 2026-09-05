"""Two clean tracks (Recall bot, one mp3 per person) -> one lesson, with speakers known for certain.

python scripts/ingest_tracks.py 2026-09-05 [--hhmm 1419] [--send] [--no-openai]

1. transcribes each track once with ElevenLabs Scribe v2 (full track, no keyterms; E1: scribe_<Name>.json is written once and reused)
2. merges the two word streams on the tracks' start offsets, speaker = the track's person (rule S1: speaker = recording channel)
3. mixes the two tracks into audio.mp3 (offsets kept) so clips can be cut
4. hands the merged scribe.json to lesson_pipeline.process (transcript page, summary, publish, understanding, report, after link)
"""
from __future__ import annotations
import argparse, io, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lesson_pipeline as lp  # noqa: E402

LESSONS = ROOT / 'data' / 'lessons'


def person(name: str) -> str:
    n = name.lower()
    if 'amal' in n:
        return 'Amal'
    if 'medi' in n or 'mahdi' in n or 'natanzi' in n:
        return 'Medi'
    raise SystemExit(f'unknown participant {name!r}: add the mapping in ingest_tracks.person()')


def transcribe_track(d: Path, who: str, mp3: Path) -> dict:
    out = d / f'scribe_{who}.json'
    if out.exists():
        lp.log('reusing', out.name)
        return json.load(io.open(out, encoding='utf-8'))
    lp.log('transcribing track', who, mp3.name)
    res = lp.transcribe(mp3)
    out.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    return res


def merge(tracks: list[dict], per_track: dict[str, dict]) -> dict:
    words = []
    for t in tracks:
        who = person(t['participant'])
        off = float(t['start']['relative'])
        for w in per_track[who].get('words', []):
            if w.get('type') != 'word':
                continue
            words.append({**w, 'start': round(w.get('start', 0) + off, 3), 'end': round(w.get('end', 0) + off, 3), 'speaker_id': who})
    words.sort(key=lambda w: (w['start'], w['end']))
    langs = {person(t['participant']): per_track[person(t['participant'])].get('language_code') for t in tracks}
    return {'words': words, 'language_code': langs.get('Amal') or next(iter(langs.values())), 'language_by_track': langs,
            'speaker_source': 'tracks', 'tracks': [{'who': person(t['participant']), 'offset': t['start']['relative'], 'duration_s': t['duration_s'],
                                                     'file': Path(t['file']).name} for t in tracks]}


def mix_audio(d: Path, tracks: list[dict]) -> Path:
    out = d / 'audio.mp3'
    if out.exists():
        return out
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for t in tracks:
        cmd += ['-i', str(t['file'])]
    delays = '; '.join(f'[{i}:a]adelay={int(round(float(t["start"]["relative"]) * 1000))}:all=1[a{i}]' for i, t in enumerate(tracks))
    ins = ''.join(f'[a{i}]' for i in range(len(tracks)))
    cmd += ['-filter_complex', f'{delays}; {ins}amix=inputs={len(tracks)}:normalize=0[out]', '-map', '[out]', '-ac', '1', '-b:a', '64k', str(out)]
    subprocess.run(cmd, check=True)
    lp.log('mixed audio.mp3 from', len(tracks), 'tracks')
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--hhmm', default='0000'); ap.add_argument('--send', action='store_true')
    ap.add_argument('--force', action='store_true', help='skip the Arabic-share check')
    a = ap.parse_args()
    d = LESSONS / a.date
    manifest = json.load(io.open(d / 'tracks' / 'tracks.json', encoding='utf-8'))
    tracks = manifest['tracks']
    per_track = {person(t['participant']): transcribe_track(d, person(t['participant']), Path(t['file'])) for t in tracks}
    merged_path = d / 'scribe.json'
    if merged_path.exists():
        lp.log('scribe.json exists, keeping it (E1)')
    else:
        merged_path.write_text(json.dumps(merge(tracks, per_track), ensure_ascii=False), encoding='utf-8')
        lp.log('merged', merged_path.name)
    mix_audio(d, tracks)
    src = Path(tracks[0]['file'])                      # only used for its name and the (absent) Meet chat sidecar
    summary = lp.process(src, a.date, a.hhmm, reuse=merged_path, send=a.send, force=a.force)
    print(json.dumps({k: summary.get(k) for k in ('date', 'minutes', 'words', 'arabic_share', 'medi_arabic_words', 'speaker_split', 'link', 'post', 'skipped')},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
