"""Apply Amal's answers (amal_rules) to the data: right/wrong/not_medi re-score word_events, 'alias' adds her spelling to the
matcher aliases, then buckets are recomputed. Idempotent: rules carry an 'applied' marker in payload.

  python scripts/apply_rules.py            # apply every unapplied rule
Returns/prints what changed so the after-link test can assert 'every answer produces a visible rule row and a re-scored word'."""
import datetime, io, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db, buckets

ROOT = Path(__file__).resolve().parent.parent
VERDICT = {'right': {'correction': False, 'prompted': False}, 'wrong': {'correction': True}, 'not_medi': {'speaker': 'Amal', 'correction': False, 'prompted': False}}


def apply(limit=500):
    rules = db.select('amal_rules', {'select': '*', 'order': 'created_at.asc', 'limit': limit})
    changed = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for r in rules:
        p = r.get('payload') or {}
        if p.get('applied'):
            continue
        k, key = r['kind'], r.get('word_key')
        if k in VERDICT and key and r.get('lesson_date'):
            t = p.get('t')
            params = {'lesson_date': f"eq.{r['lesson_date']}", 'word_key': f'eq.{key}'}
            if t is not None:
                params['and'] = f'(t_start.gte.{float(t) - 1.0},t_start.lte.{float(t) + 1.0})'
            patch = dict(VERDICT[k]); patch['confidence'] = 1.0
            hit = db.rest('PATCH', 'word_events', params=params, body=patch, prefer='return=representation') or []
            changed.append({'rule': r['id'], 'kind': k, 'word_key': key, 'patched': patch, 'rows': len(hit)})
        elif k == 'alias' and p.get('alias'):
            key = key or p.get('word_key')
            if key:
                w = db.select('words', {'key': f'eq.{key}', 'select': 'key,aliases'})
                if w:
                    al = list(w[0].get('aliases') or [])
                    if p['alias'] not in al:
                        al.append(p['alias'])
                        db.rest('PATCH', 'words', params={'key': f'eq.{key}'}, body={'aliases': al, 'updated_at': now}, prefer='return=minimal')
                        changed.append({'rule': r['id'], 'kind': 'alias', 'word_key': key, 'alias': p['alias']})
        db.rest('PATCH', 'amal_rules', params={'id': f"eq.{r['id']}"}, body={'payload': {**p, 'applied': now}}, prefer='return=minimal')
    stats = buckets.recompute_and_store() if changed else {}
    for c in changed:
        if c.get('word_key') in stats:
            c['bucket_now'] = stats[c['word_key']]['bucket']
    return changed


if __name__ == '__main__':
    print(json.dumps(apply(), ensure_ascii=False, indent=1))
