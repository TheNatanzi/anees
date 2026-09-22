"""Rule 4: a learner word recognized while Medi's OWN recording track is silent was never said (speech-engine
hallucination). Such events are excluded (ignored), never scored. Additive patches in docs/data/word-bank-review.json.

  python scripts/review_silent_credits.py --raw C:/dev/anees/data/lessons --work <scratch> 2026-09-11 2026-09-14 ...

Only lessons with one track per person (the silence of Medi's own track is measurable). Existing patches untouched.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--raw', required=True); ap.add_argument('--work', required=True); ap.add_argument('dates', nargs='+')
    a = ap.parse_args()
    import load_lesson as L, audit_lessons as A
    snap = json.loads((ROOT / 'docs/data/word-bank-evidence.json').read_text(encoding='utf-8'))['events']
    path = ROOT / 'docs/data/word-bank-review.json'
    review = json.loads(path.read_text(encoding='utf-8'))
    found = {}
    for d in a.dates:
        data, info = L.build_tracks(d, Path(a.raw) / d, Path(a.work) / 'silence' / d)
        events = [e for e in snap if e['lesson_date'] == d]
        assert {e['source_id'] for e in events} <= set(data['sources']), f'{d}: events come from another transcript build'
        shown = [{**e, **review['patches'].get(e['id'], {}).get('changes', {})} for e in events]
        by_t = {(round(e['t_start'], 1), e.get('word_key')): e for e in events if e['speaker'] == 'Medi' and e.get('spoken')}
        for t, key, level in A.silent_credits(shown, data['sources']):
            e = by_t[(t, key)]
            why = f"Recognized while Medi's own recording was silent ({level} dBFS): speech-engine hallucination, not counted."
            p = review['patches'].setdefault(e['id'], {'expected': {k: e.get(k) for k in ['source_sha256', 'row_id', 'word_key', 'text', 't_start', 't_end']}, 'changes': {}})
            # Silence wins over any other patch (Codex 2026-09-23): an earlier review never proves Medi spoke.
            p['changes'].update(ignored=True, needs_review=False, silence_rule=True, reason=why + (' Earlier review: ' + p['changes']['reason'] if p['changes'].get('reason') and 'silent' not in p['changes']['reason'] else ''))
            found.setdefault(d, []).append((t, key, level))
    if found:
        review['version'] = review['version'] + '+silence'
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(found, ensure_ascii=False))


if __name__ == '__main__':
    main()
