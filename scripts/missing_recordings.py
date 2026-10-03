# -*- coding: utf-8 -*-
"""Every recording of every lesson is transcribed (rule TR-17; Medi 2026-10-02: "fill always fill and be complete").

    python scripts/missing_recordings.py [--raw <ANEES_RAW>]      # list untranscribed recordings; exit 1 when any

A recording (tracks/tracks.json, one per person per connection; the host's silent track is not a person) counts as
transcribed when any of these holds:
  - a saved transcript's provenance names it (scribe_<who>.json / scribe_<who>_seg<start>.json .provenance.json);
  - it is the one recording of that person whose length matches scribe_<who>.json (older lessons without provenance);
  - the gap filler transcribed it (gapfill_<side>.track.scribe.json, _anees_track.file);
  - it is a segment of a stitched recording that was transcribed (tracks/stitched.json, 09-14).
Recordings shorter than MIN_S hold no speech worth a call (the same floor as hourly_lessons.MIN_EXTRA_S).

The hourly job transcribes every one this finds (hourly_lessons.fill_missing_recordings, no per-lesson approval; the
project's spending cap is the only stop) and says so on Progress + Lessons when it cannot (rule LS-04). The publish
guard's `recordings_complete` check fails while any is left.
"""
from __future__ import annotations

import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
MIN_S = 3.0
ARCHIVE = Path('C:/dev/anees/data/lessons')     # the raw archive the hourly job uses (scripts/run_hourly_lessons.ps1 default)


def default_raw():
    """ANEES_RAW, else the hourly job's archive when this machine has it, else the repo's data/lessons. 2026-10-02: the
    guard ran without ANEES_RAW, read the repo's data/lessons - where git keeps only 09-05's tracks.json (audio and
    transcripts are gitignored) - and called 09-05's two fully transcribed recordings (125 min) missing."""
    if os.environ.get('ANEES_RAW'):
        return os.environ['ANEES_RAW']
    return str(ARCHIVE) if ARCHIVE.is_dir() else str(ROOT / 'data' / 'lessons')


def _j(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def _person(name):
    import load_lesson as L
    return L._person(name)


def _key(t):
    return (Path(t.get('file') or '').name, int(float((t.get('start') or {}).get('relative') or 0)))


def covered(lesson_dir):
    """Keys (file name, whole-second start) of this lesson's recordings that already have a transcript. Older lessons
    (09-14..09-17) reuse one file name for all of a person's recordings, so a recording is told apart by its start."""
    d = Path(lesson_dir)
    tracks = _j(d / 'tracks' / 'tracks.json').get('tracks') or []
    mine = lambda who: [t for t in tracks if _person(t.get('participant')) == who]
    done = set()
    for sp in d.glob('scribe_*.json'):
        if sp.name.endswith('.provenance.json'):
            continue
        parts = sp.stem.split('_')                      # scribe_<who>[_seg<start>]
        who = parts[1] if len(parts) > 1 else None
        if who not in ('Amal', 'Medi'):
            continue
        if len(parts) > 2 and parts[2].startswith('seg'):
            start = int(parts[2][3:])
            done |= {_key(t) for t in mine(who) if _key(t)[1] == start}
            continue
        try:
            dur = _j(sp).get('audio_duration_secs') or 0
        except Exception:
            continue
        pv = sp.with_name(sp.stem + '.provenance.json')
        name = Path(_j(pv).get('source_file') or '').name if pv.exists() else ''
        m = [t for t in mine(who) if abs((t.get('duration_s') or 0) - dur) < 2 and (not name or _key(t)[0] == name)]
        if len(m) == 1:
            done.add(_key(m[0]))
    for g in d.glob('gapfill_*.track.scribe.json'):
        try:
            meta = _j(g).get('_anees_track') or {}
            done |= {_key(t) for t in tracks if _key(t)[0] == Path(meta.get('file') or '').name
                     and abs(float((t.get('start') or {}).get('relative') or 0) - float(meta.get('offset_s') or 0)) < 1}
        except Exception:
            pass
    st = d / 'tracks' / 'stitched.json'
    if st.exists() and (d / 'scribe_Medi.json').exists():
        for s in _j(st).get('segments') or []:
            done |= {_key(t) for t in mine('Medi') if abs(float(t['start']['relative']) - float(s['start']['relative'])) < 1}
    return done


def missing(raw, min_s=MIN_S):
    """[{date, who, file, start_s, duration_s, minutes}] of every person's recording with no transcript."""
    out = []
    for d in sorted(p for p in Path(raw).iterdir() if p.is_dir() and (p / 'tracks' / 'tracks.json').exists()):
        if not any((d / 'tracks').glob('*.mp3')) and not any(d.glob('scribe*.json')):
            continue                                    # only the manifest is here (a repo copy): no archive to judge
        done = covered(d)
        for t in _j(d / 'tracks' / 'tracks.json').get('tracks') or []:
            who = _person(t.get('participant'))
            dur = float(t.get('duration_s') or 0)
            if who and dur >= min_s and _key(t) not in done:
                out.append({'date': d.name, 'who': who, 'file': _key(t)[0], 'start_s': float((t.get('start') or {}).get('relative') or 0),
                            'duration_s': dur, 'minutes': round(dur / 60, 1)})
    return out


def summary(items):
    """One line per lesson: '2026-09-26: Amal 18.6 min'."""
    by = {}
    for m in items:
        by.setdefault(m['date'], []).append(f"{m['who']} {m['minutes']} min")
    return [f'{d}: ' + ', '.join(v) for d, v in sorted(by.items())]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=default_raw())
    a = ap.parse_args(argv)
    if not Path(a.raw).is_dir():
        print(f'recordings: raw archive {a.raw} not on this machine - nothing to check')
        return 0
    items = missing(a.raw)
    if items:
        print(f'recordings: {len(items)} untranscribed ({round(sum(m["duration_s"] for m in items) / 60, 1)} min) - '
              + '; '.join(summary(items)))
        return 1
    print('recordings: every recording of every lesson is transcribed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
