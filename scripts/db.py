"""Anees database helpers.

sql(q)            -> run SQL through the Supabase management API (needs SUPABASE_ACCESS_TOKEN). Returns rows (list of dicts).
rest(...)         -> PostgREST calls with the service key (scripts) or the anon key + Amal token (tests that imitate a link).
Both raise on HTTP errors (PostgREST never throws on 4xx by itself, so we check status ourselves)."""
import json, sys, time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anees_env as E


class DbError(RuntimeError):
    pass


def sql(query, retries=3):
    if not E.ACCESS_TOKEN:
        raise DbError('SUPABASE_ACCESS_TOKEN missing')
    url = f'https://api.supabase.com/v1/projects/{E.SUPABASE_REF}/database/query'
    for i in range(retries):
        r = requests.post(url, headers={'Authorization': f'Bearer {E.ACCESS_TOKEN}', 'Content-Type': 'application/json'},
                          json={'query': query}, timeout=120)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (i + 1)); continue
        if r.status_code >= 400:
            raise DbError(f'SQL {r.status_code}: {r.text[:500]}')
        return r.json()
    raise DbError(f'SQL failed after {retries} tries: {r.status_code} {r.text[:200]}')


def rest(method, table, *, params=None, body=None, key=None, token=None, prefer=None, retries=3):
    key = key or E.SERVICE_KEY
    if not key:
        raise DbError('no Supabase key')
    h = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    if token:
        h['X-Anees-Token'] = token
    url = f'{E.SUPABASE_URL}/rest/v1/{table}'
    for i in range(retries):
        r = requests.request(method, url, headers=h, params=params, data=json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (i + 1)); continue
        if r.status_code >= 400:
            raise DbError(f'{method} {table} {r.status_code}: {r.text[:500]}')
        return r.json() if r.text else None
    raise DbError(f'{method} {table} failed after {retries} tries')


UNDO_TABLES = ('amal_rules', 'amal_rules_public')


def select(table, params=None, undo=True, **kw):
    """Paged select (PostgREST caps at 1000 rows per call).
    AM-17: on Amal's answer tables an undone tap is left out (scripts/amal_undo.py: latest action per item wins) and the
    undo rows themselves are not returned; undo=False gives the raw history."""
    if table in UNDO_TABLES and undo:
        return _select_honouring_undo(table, params, **kw)
    return _select(table, params, **kw)


def _select_honouring_undo(table, params, **kw):
    import amal_undo
    p = dict(params or {})
    want = [c.strip() for c in str(p.get('select', '*')).split(',') if c.strip()]
    full = '*'
    rows = _select(table, {**p, 'select': full}, **kw)
    # the undo rows of the same items: every filter but the kind (an undo row has kind 'undo')
    q = {k: v for k, v in p.items() if k not in ('select', 'kind', 'order', 'limit', 'offset')}
    q.update({'select': full, 'kind': 'eq.undo', 'order': 'id.asc'})
    undos = _select(table, q, **kw) if str(p.get('kind', '')) != 'eq.undo' else []
    have = {r.get('id') for r in rows}
    res = amal_undo.resolve(rows + [u for u in undos if u.get('id') not in have])
    kept = {id(r) for r in res.kept}
    out = [r for r in rows if id(r) in kept and r.get('kind') != amal_undo.UNDO]
    if want != ['*']:
        out = [{c: r.get(c) for c in want} for r in out]
    return out


def _select(table, params=None, **kw):
    out, off = [], 0
    while True:
        p = dict(params or {}); p.setdefault('select', '*'); p['offset'] = off; p['limit'] = 1000
        rows = rest('GET', table, params=p, **kw) or []
        out.extend(rows)
        if len(rows) < 1000:
            return out
        off += 1000


def upsert(table, rows, on='', chunk=500, **kw):
    """Same-shape rows only (PostgREST rejects mixed-key batches wholesale)."""
    if not rows:
        return 0
    keys = sorted(rows[0].keys())
    for r in rows:
        if sorted(r.keys()) != keys:
            raise DbError('upsert rows must share the same keys')
    n = 0
    for i in range(0, len(rows), chunk):
        rest('POST', table, params={'on_conflict': on} if on else None, body=rows[i:i + chunk],
             prefer='resolution=merge-duplicates,return=minimal', **kw)
        n += len(rows[i:i + chunk])
    return n
