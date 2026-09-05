"""Build the Slips page data: data/tally.json (hand-curated, wiki/17 section K) -> docs/data/tally.json.

- verifies every slip against the lesson transcript (the [mm:ss] line and the quoted words must be there)
- finds an existing clip that covers the moment, or cuts one from data/lessons/<date>/audio.mp3 with ffmpeg
- counts per rule / per kind / per lesson; no number is guessed (a moment without audio says so)
"""
from __future__ import annotations
import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'tally.json'
OUT = ROOT / 'docs' / 'data' / 'tally.json'
LESSONS = ROOT / 'data' / 'lessons'
DOCS_LESSONS = ROOT / 'docs' / 'lessons'
PRE, POST = 3.0, 12.0          # seconds of audio before / after the moment


def mmss(t: float) -> str:
    t = int(round(t)); return f'{t // 60:02d}:{t % 60:02d}'


def transcript_lines(date: str) -> list[str]:
    p = LESSONS / date / 'transcript.txt'
    return p.read_text(encoding='utf-8').splitlines() if p.exists() else []


def verify(date: str, m: dict) -> tuple[bool, str]:
    """True when the transcript has the [mm:ss] tag within 60 s of t AND the 'match' text within 4 lines of it."""
    lines = transcript_lines(date)
    if not lines:
        return False, 'no transcript'
    tag = f'[{m["mmss"]}]'
    idx = [i for i, l in enumerate(lines) if l.startswith(tag)]
    if not idx:
        return False, f'no line {tag}'
    lo, hi = max(0, idx[0] - 4), min(len(lines), idx[-1] + 5)
    window = '\n'.join(lines[lo:hi])
    return (m['match'] in window), ('' if m['match'] in window else f'"{m["match"]}" not near {tag}')


def clips_index(date: str) -> list[dict]:
    p = LESSONS / date / 'understanding.json'
    return json.loads(p.read_text(encoding='utf-8')).get('clips', []) if p.exists() else []


def find_or_cut_clip(date: str, t: float) -> tuple[str | None, float | None, str]:
    """Return (clip path relative to docs/lessons, offset seconds, how)."""
    for c in clips_index(date):
        if c['start'] - 1 <= t <= c['end'] - 1:
            f = DOCS_LESSONS / date / 'clips' / c['file']
            if f.exists():
                return f'{date}/clips/{c["file"]}', max(0.0, t - c['start']), 'existing clip'
    audio = LESSONS / date / 'audio.mp3'
    if not audio.exists() or not shutil.which('ffmpeg'):
        return None, None, 'no lesson audio on this PC' if not audio.exists() else 'ffmpeg missing'
    name = f'tally_{date}_{int(round(t))}.mp3'
    out = DOCS_LESSONS / date / 'clips' / name
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        start = max(0.0, t - PRE)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.2f}', '-t', f'{PRE + POST:.2f}', '-i', str(audio),
                        '-ac', '1', '-b:a', '48k', str(out)], check=True)
    return f'{date}/clips/{name}', PRE if t >= PRE else t, 'cut from lesson audio'


def build(cut_clips: bool = True) -> dict:
    src = json.loads(SRC.read_text(encoding='utf-8'))
    problems: list[str] = []
    out_rules = []
    kinds: dict[str, int] = {}
    per_lesson: dict[str, int] = {d: 0 for d in src['lessons']}
    for r in src['rules']:
        rr = {k: v for k, v in r.items() if k not in ('slips', 'asks')}
        rr['slips'], rr['asks'] = [], []
        for bucket in ('slips', 'asks'):
            for m in r.get(bucket, []):
                ok, why = verify(m['date'], m)
                if not ok:
                    problems.append(f'{r["id"]} {m["date"]} {m["mmss"]}: {why}')
                clip, off, how = find_or_cut_clip(m['date'], m['t']) if cut_clips else (None, None, 'skipped')
                rr[bucket].append({**m, 'verified': ok, 'clip': clip, 'offset': off, 'audio': how})
        rr['count'] = len(rr['slips'])
        rr['ask_count'] = len(rr['asks'])
        if not r.get('candidate'):
            kinds[r['kind']] = kinds.get(r['kind'], 0) + rr['count']
            for m in rr['slips']:
                per_lesson[m['date']] = per_lesson.get(m['date'], 0) + 1
        out_rules.append(rr)
    grammar_rules = [r for r in out_rules if not r.get('candidate')]
    totals = {
        'slips': sum(r['count'] for r in grammar_rules),
        'rules_with_slips': sum(1 for r in grammar_rules if r['count']),
        'asks': sum(r['ask_count'] for r in out_rules),
        'pronunciation_candidates': sum(r['count'] for r in out_rules if r.get('candidate')),
        'review_due': sum(1 for r in out_rules if r.get('review_due')),
        'lessons': len(src['lessons']),
        'per_lesson': per_lesson,
        'by_kind': kinds,
    }
    doc = {'updated': src['updated'], 'lessons': src['lessons'], 'note': src['note'], 'totals': totals,
           'rules': out_rules, 'machine_only': src.get('machine_only', {}), 'problems': problems}
    return doc


def main() -> int:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    t = doc['totals']
    print(f"tally: {t['slips']} slips on {t['rules_with_slips']} rules, {t['asks']} asks, "
          f"{t['pronunciation_candidates']} pronunciation candidates, {t['review_due']} rules review-due; "
          f"{len(doc['problems'])} problems")
    for p in doc['problems']:
        print('  !', p)
    return 1 if doc['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
