"""Apply Amal's answers (amal_rules) to the data: right/wrong/not_medi re-score word_events, 'alias' adds her spelling to the
matcher aliases, then buckets are recomputed. Idempotent: rules carry an 'applied' marker in payload.

  python scripts/apply_rules.py            # apply every unapplied rule
Returns/prints what changed so the after-link test can assert 'every answer produces a visible rule row and a re-scored word'."""
import datetime, io, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db, buckets

ROOT = Path(__file__).resolve().parent.parent
VERDICT = {'right': {'correction': False, 'asked': False}, 'wrong': {'correction': True}, 'not_medi': {'speaker': 'Amal', 'correction': False, 'prompted': False, 'asked': False}}


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
            # Codex P0: a verdict is applied only when the link's own payload asked exactly this question (word + time)
            link = db.select('amal_links', {'token': f"eq.{r['token']}", 'select': 'lesson_date,payload'}) if r.get('token') else []
            qs = ((link[0].get('payload') or {}).get('questions') or []) if link else []
            q = next((x for x in qs if x.get('word_key') == key and abs(float(x.get('t', -9)) - float(p.get('t', -1))) < 0.01), None)
            if not link or link[0]['lesson_date'] != r['lesson_date'] or not q:
                changed.append({'rule': r['id'], 'kind': k, 'word_key': key, 'rows': 0, 'refused': 'rule does not match a question of its link'})
            else:
                patch = dict(VERDICT[k]); patch['confidence'] = 1.0
                if p.get('who') and k in ('right', 'wrong'):
                    patch['speaker'] = 'Medi'
                if k == 'wrong' and p.get('miss_kind'):
                    sub = q.get('miss_kind')
                    patch['miss_kind'] = (sub if (p['miss_kind'] == 'grammar' and sub in ('article', 'gender', 'tense', 'plural')) else p['miss_kind'])
                    patch['miss_why'] = 'Amal tapped ' + ('Wrong grammar' if p['miss_kind'] == 'grammar' else 'Wrong word')
                if k == 'right':
                    patch['miss_kind'] = None
                if q.get('event_id'):
                    params = {'id': f"eq.{q['event_id']}"}
                else:
                    params = {'lesson_date': f"eq.{r['lesson_date']}", 'word_key': f'eq.{key}', 't_start': f"eq.{q['t']}"}
                hit = db.rest('PATCH', 'word_events', params=params, body=patch, prefer='return=representation') or []
                if not hit and q.get('event_id'):        # the lesson was rebuilt after the link was minted: fall back to the exact word + time
                    params = {'lesson_date': f"eq.{r['lesson_date']}", 'word_key': f'eq.{key}', 't_start': f"eq.{q['t']}"}
                    hit = db.rest('PATCH', 'word_events', params=params, body=patch, prefer='return=representation') or []
                changed.append({'rule': r['id'], 'kind': k, 'word_key': key, 'patched': patch, 'rows': len(hit)})
        elif k == 'alias' and p.get('alias'):
            key = key or p.get('word_key')
            if not key:
                changed.append({'rule': r['id'], 'kind': 'alias', 'word_key': None, 'rows': 0, 'note': 'new word typed by Amal; kept as a rule for the Words tab (the Doc stays the truth)'})
            if key:
                w = db.select('words', {'key': f'eq.{key}', 'select': 'key,aliases'})
                if w:
                    al = list(w[0].get('aliases') or [])
                    if p['alias'] not in al:
                        al.append(p['alias'])
                        db.rest('PATCH', 'words', params={'key': f'eq.{key}'}, body={'aliases': al, 'updated_at': now}, prefer='return=minimal')
                        changed.append({'rule': r['id'], 'kind': 'alias', 'word_key': key, 'alias': p['alias']})
        db.rest('PATCH', 'amal_rules', params={'id': f"eq.{r['id']}"}, body={'payload': {**p, 'applied': now}}, prefer='return=minimal')
    try:
        import homework                                       # M10c: Amal's verdicts on Medi's typed answers score the words too
        hw = homework.apply_verdicts(log=lambda *a: None)
        changed.extend({'rule': None, 'kind': 'homework_' + c['verdict'], 'word_key': ','.join(c['keys']), 'rows': len(c['keys']), 'wrong': c['wrong']} for c in hw)
    except Exception as e:
        changed.append({'rule': None, 'kind': 'homework_error', 'word_key': None, 'rows': 0, 'refused': str(e)[:160]})
    stats = buckets.recompute_and_store() if changed else {}
    for c in changed:
        if c.get('word_key') in stats:
            c['bucket_now'] = stats[c['word_key']]['bucket']
    return changed


if __name__ == '__main__':
    print(json.dumps(apply(), ensure_ascii=False, indent=1))
