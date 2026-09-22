"""Amal's check list for guessed verb forms. NEVER sends anything to Amal.

  python scripts/verb_check_links.py create      # mint a private link from the catalog's unchecked guesses
  python scripts/verb_check_links.py pull        # her answers -> data/vocab/amal_verb_checks.json
  python scripts/verb_check_links.py list
After pull, rebuild the catalog (build_word_bank_catalog.py) so her answers overwrite the guesses."""
import argparse, datetime, io, json, secrets, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

ROOT = Path(__file__).resolve().parent.parent
PAGES = 'https://thenatanzi.github.io/anees/'
PAGE = 'amal/verb-check.html'
DAYS = 30
CHECKS = ROOT / 'data' / 'vocab' / 'amal_verb_checks.json'
TENSES = ['Present', 'Past', 'Command']


def url(token):
    return f'{PAGES}{PAGE}#t={token}'


def payload(catalog):
    """Every unchecked guess, grouped by verb in catalog order."""
    items, verbs = {}, []
    for g in catalog['groups']:
        if g['type'] != 'Verb':
            continue
        ids = []
        for f in g['entries']:
            if f['label'] not in TENSES:
                continue
            for p in f['persons']:
                if p.get('provenance') == 'inferred' and p.get('checked') is False:
                    items[p['id']] = {'tense': f['label'], 'person': p['person'], 'word': p['word'], 'arabic': p['arabic']}
                    ids.append(p['id'])
        if ids:
            verbs.append({'key': g['key'], 'name': g['name'], 'arabic': g['arabic'], 'english': g['english'], 'ids': ids})
    return {'schema_version': 1, 'kind': 'verb-forms', 'items': items, 'verbs': verbs}


def create():
    catalog = json.loads((ROOT / 'docs/data/word-bank-catalog.json').read_text(encoding='utf-8'))
    body = payload(catalog)
    token = secrets.token_urlsafe(32)[:43]
    now = datetime.datetime.now(datetime.timezone.utc)
    row = {'token': token, 'created_at': now.isoformat(), 'expires_at': (now + datetime.timedelta(days=DAYS)).isoformat(),
           'payload': body, 'answers': {'schema_version': 1, 'revision': 0, 'answers': {}}}
    db.upsert('verb_check_links', [row], on='token')
    out = ROOT / 'data' / 'amal_links.json'
    hist = json.load(io.open(out, encoding='utf-8')) if out.exists() else []
    hist.append({'kind': 'verb-check', 'created_at': row['created_at'], 'expires_at': row['expires_at'], 'url': url(token), 'items': len(body['items'])})
    io.open(out, 'w', encoding='utf-8').write(json.dumps(hist, ensure_ascii=False, indent=1))
    return url(token), len(body['items']), len(body['verbs'])


def pull():
    """Merge every link's answers; the newest answer per form wins."""
    old = json.loads(CHECKS.read_text(encoding='utf-8')) if CHECKS.exists() else {'answers': {}}
    merged = dict(old.get('answers', {}))
    for r in db.select('verb_check_links', {'select': 'payload,answers,created_at', 'order': 'created_at.asc'}):
        for item_id, a in (r['answers'] or {}).get('answers', {}).items():
            guess = r['payload']['items'].get(item_id, {})
            if item_id in merged and merged[item_id].get('updated_at', '') > a.get('updated_at', ''):
                continue
            merged[item_id] = {'choice': a['choice'], 'word': a['word'].strip(), 'arabic': a['arabic'].strip(),
                               'guess': guess.get('word', ''), 'tense': guess.get('tense', ''), 'updated_at': a['updated_at']}
    CHECKS.write_text(json.dumps({'answers': dict(sorted(merged.items()))}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['create', 'pull', 'list'])
    a = ap.parse_args()
    if a.cmd == 'create':
        u, n, v = create()
        print(f'{n} forms across {v} verbs')
        print(u)
    elif a.cmd == 'pull':
        m = pull()
        print(f"{sum(x['choice'] == 'yes' for x in m.values())} right, {sum(x['choice'] == 'fix' for x in m.values())} fixed -> {CHECKS}")
    else:
        for r in db.select('verb_check_links', {'select': 'token,created_at,expires_at,opened_at,done_at,answers', 'order': 'created_at.desc'}):
            n = len((r['answers'] or {}).get('answers', {}))
            print(r['created_at'][:10], f'{n} answered', 'opened' if r['opened_at'] else 'new', url(r['token']))


if __name__ == '__main__':
    main()
