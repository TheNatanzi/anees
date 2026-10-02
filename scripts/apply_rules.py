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


def revert_undone(now, changed):
    """AM-17 (Medi 2026-10-02 "can you add an undo button to all these tutor hub stuff"): a tap Amal undid stops counting.
    db.select already leaves undone taps out; a tap that was APPLIED before her undo is put back here: word_events get the
    values stored in payload.before when it was applied, an alias she typed leaves the word, a homework line goes back to
    'suggested'. A tap applied before AM-17 has no stored values: it is marked, reported, and left as it is."""
    import amal_undo
    raw = db.select('amal_rules', {'select': '*', 'order': 'id.asc'}, undo=False)
    res = amal_undo.resolve(raw)
    for r in raw:
        if r.get('kind') == amal_undo.UNDO or r.get('id') not in res.undone:
            continue
        p = r.get('payload') or {}
        if p.get('reverted'):
            continue
        note, rows = None, 0
        if p.get('source') == 'homework_prompt' and p.get('item_id'):
            hit = db.rest('PATCH', 'homework_items', params={'id': f"eq.{p['item_id']}", 'status': 'in.(keep,drop,edit)'},
                          body={'status': 'suggested', 'decided_at': None, 'edited_english': None}, prefer='return=representation') or []
            rows = len(hit)
        elif p.get('applied') and r['kind'] in VERDICT:
            if p.get('before') and p.get('before_params'):
                for b in p['before']:
                    hit = db.rest('PATCH', 'word_events', params={'id': f"eq.{b['id']}"}, body={k: v for k, v in b.items() if k != 'id'}, prefer='return=representation') or []
                    rows += len(hit)
            else:
                note = 'applied before Undo existed (AM-17): the old values were not stored, the word event stays as Amal first ruled'
        elif p.get('applied') and r['kind'] == 'alias' and p.get('alias') and (r.get('word_key') or p.get('word_key')):
            key = r.get('word_key') or p.get('word_key')
            w = db.select('words', {'key': f'eq.{key}', 'select': 'key,aliases'})
            if w and p['alias'] in (w[0].get('aliases') or []):
                db.rest('PATCH', 'words', params={'key': f'eq.{key}'}, body={'aliases': [a for a in w[0]['aliases'] if a != p['alias']], 'updated_at': now}, prefer='return=minimal')
                rows = 1
        if not p.get('applied') and not (p.get('source') == 'homework_prompt' and p.get('item_id')):
            continue                                   # never applied: leaving it out (db.select) is the whole undo
        db.rest('PATCH', 'amal_rules', params={'id': f"eq.{r['id']}"}, body={'payload': {**p, 'reverted': now, **({'revert_note': note} if note else {})}}, prefer='return=minimal')
        changed.append({'rule': r['id'], 'kind': 'undo:' + r['kind'], 'word_key': r.get('word_key'), 'rows': rows, **({'note': note} if note else {})})
    # Medi's typed answer whose verdict she undid on the after-lesson list (amal_verdict cleared): its homework word events go
    for a in db.select('homework_answers', {'amal_verdict': 'is.null', 'applied': 'not.is.null', 'select': 'id,answer,lesson_date,item_id'}):
        it = db.select('homework_items', {'id': f"eq.{a['item_id']}", 'select': 'lesson_date'})
        if it:
            db.rest('DELETE', 'word_events', params={'lesson_date': f"eq.{it[0]['lesson_date']}", 'text': f"eq.homework: {a['answer'][:160]}"}, prefer='return=minimal')
        db.rest('PATCH', 'homework_answers', params={'id': f"eq.{a['id']}"}, body={'applied': None}, prefer='return=minimal')
        changed.append({'rule': None, 'kind': 'undo:homework_verdict', 'word_key': None, 'rows': 1})


def apply(limit=500):
    rules = db.select('amal_rules', {'select': '*', 'order': 'created_at.asc', 'limit': limit})
    changed = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    revert_undone(now, changed)
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
                # AM-17: keep what the rows said before her tap, so an Undo can put them back
                cols = 'id,' + ','.join(patch)
                prior = db.select('word_events', {**params, 'select': cols})
                if not prior and q.get('event_id'):     # the lesson was rebuilt after the link was minted: fall back to the exact word + time
                    params = {'lesson_date': f"eq.{r['lesson_date']}", 'word_key': f'eq.{key}', 't_start': f"eq.{q['t']}"}
                    prior = db.select('word_events', {**params, 'select': cols})
                hit = db.rest('PATCH', 'word_events', params=params, body=patch, prefer='return=representation') or []
                p = {**p, 'before': prior, 'before_params': params}
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
