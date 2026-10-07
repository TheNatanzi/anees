"""Amal's check list for guessed verb forms. NEVER sends anything to Amal.

  python scripts/verb_check_links.py create      # mint a private link from the catalog's unchecked guesses
  python scripts/verb_check_links.py create-addons   # level 2 (endings / prepositions): a second, separate link
  python scripts/verb_check_links.py create-addons-short   # AM-26: level 2 cut to the 44 verbs where the preposition
        matters (data/vocab/verb-short-list.json); closes the older open level-2 link, her answers on it stay the answers
        of record (pull() reads every link), nothing deleted
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
# Level 2 (endings / prepositions): read by scripts/build_verb_addon_tags.cjs (Amal wins). Before 2026-09-29 pull()
# built this dict and never wrote it, so her level-2 answers would have been lost.
ADDON_CHECKS = ROOT / 'data' / 'vocab' / 'amal_addon_checks.json'
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


def create(kind='verb-forms'):
    if kind == 'verb-addons-short':   # AM-26: only the verbs where the preposition matters
        import subprocess
        body = json.loads(subprocess.run(['node', str(ROOT / 'scripts' / 'verb_addon_short_payload.cjs')], capture_output=True, text=True, check=True, encoding='utf-8').stdout)
        if body.get('missing'):
            raise SystemExit(f"verbs not in the catalog: {body['missing']}")
    elif kind == 'verb-addons':      # level 2: endings / prepositions per verb, built by the same JS engine the cards use
        import subprocess
        body = json.loads(subprocess.run(['node', str(ROOT / 'scripts' / 'verb_addon_payload.cjs')], capture_output=True, text=True, check=True, encoding='utf-8').stdout)
    else:
        catalog = json.loads((ROOT / 'docs/data/word-bank-catalog.json').read_text(encoding='utf-8'))
        body = payload(catalog)
    token = secrets.token_urlsafe(32)[:43]
    now = datetime.datetime.now(datetime.timezone.utc)
    row = {'token': token, 'created_at': now.isoformat(), 'expires_at': (now + datetime.timedelta(days=DAYS)).isoformat(),
           'payload': body, 'answers': {'schema_version': 1, 'revision': 0, 'answers': {}}}
    db.upsert('verb_check_links', [row], on='token')
    if kind == 'verb-addons-short':   # AM-26: the long level-2 link closes; her answers on it are kept and still pulled
        for r in db.select('verb_check_links', {'select': 'token,payload,done_at', 'order': 'created_at.asc'}):
            if r['token'] != token and (r.get('payload') or {}).get('kind') == 'verb-addons' and not (r['payload'] or {}).get('short') and not r.get('done_at'):
                db.rest('PATCH', 'verb_check_links', params={'token': f"eq.{r['token']}"}, body={'done_at': now.isoformat()}, prefer='return=minimal')
    out = ROOT / 'data' / 'amal_links.json'
    hist = json.load(io.open(out, encoding='utf-8')) if out.exists() else []
    hist.append({'kind': {'verb-forms': 'verb-check', 'verb-addons': 'verb-addon-check'}.get(kind, 'verb-addon-check-short'), 'created_at': row['created_at'], 'expires_at': row['expires_at'], 'url': url(token), 'items': len(body['items'])})
    io.open(out, 'w', encoding='utf-8').write(json.dumps(hist, ensure_ascii=False, indent=1))
    return url(token), len(body['items']), len(body['verbs'])


def pull():
    """Merge every link's answers; the newest answer per form wins."""
    old = json.loads(CHECKS.read_text(encoding='utf-8')) if CHECKS.exists() else {'answers': {}}
    merged = dict(old.get('answers', {}))
    addon = {}
    for r in db.select('verb_check_links', {'select': 'payload,answers,created_at', 'order': 'created_at.asc'}):
        if r['payload'].get('kind') == 'verb-addons':
            for item_id, a in (r['answers'] or {}).get('answers', {}).items():
                verb, _, k = item_id.rpartition(':addon:')
                entry = addon.setdefault(verb, {})
                off = a['choice'] == 'fix' and a['word'].strip().lower() in ('no', 'x', '-', 'none')
                if k == 'obj':
                    entry['object'] = not off
                else:
                    entry.setdefault('preps_off' if off else 'preps_ok', []).append(k)
                if a['choice'] == 'fix' and not off:
                    entry.setdefault('forms', {})[k] = {'word': a['word'].strip(), 'arabic': a['arabic'].strip()}
            continue
        for item_id, a in (r['answers'] or {}).get('answers', {}).items():
            guess = r['payload']['items'].get(item_id, {})
            if item_id in merged and merged[item_id].get('updated_at', '') > a.get('updated_at', ''):
                continue
            merged[item_id] = {'choice': a['choice'], 'word': a['word'].strip(), 'arabic': a['arabic'].strip(),
                               'guess': guess.get('word', ''), 'tense': guess.get('tense', ''), 'updated_at': a['updated_at']}
        # AM-17: an Undo she tapped drops the form from the link's answers and logs it in answers.undone; an answer kept
        # in the merged file from an earlier pull leaves too unless she answered it again after the undo
        for u in (r['answers'] or {}).get('undone', []) or []:
            k = str(u.get('key') or '')
            if k in merged and merged[k].get('updated_at', '') <= str(u.get('at') or '') and k not in (r['answers'] or {}).get('answers', {}):
                del merged[k]
    CHECKS.write_text(json.dumps({'answers': dict(sorted(merged.items()))}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if addon or ADDON_CHECKS.exists():
        ADDON_CHECKS.write_text(json.dumps(dict(sorted(addon.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['create', 'create-addons', 'create-addons-short', 'pull', 'list'])
    a = ap.parse_args()
    if a.cmd in ('create', 'create-addons', 'create-addons-short'):
        u, n, v = create({'create': 'verb-forms', 'create-addons': 'verb-addons', 'create-addons-short': 'verb-addons-short'}[a.cmd])
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
