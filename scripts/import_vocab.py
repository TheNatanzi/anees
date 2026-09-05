"""Import Amal's Google Doc ("Arabic Full Vocabulary list") into the Supabase `words` table. ONE WAY: the Doc is never written.

Sources, in order of preference:
  --file X          a saved export: markdown (Drive connector read_file_content) or Google-Docs HTML (export / publish-to-web)
  ANEES_DOC_PUBLISHED_URL   env var with the Doc's "publish to web" URL -> fetched unattended (hourly Task Scheduler job)
  otherwise         the newest data/vocab/doc_*.md snapshot (no network; logs that no live source exists)

Idempotent: rows are keyed by Amal's Arabizi (loose form); unchanged rows are not rewritten, missing rows are deactivated.
Usage:  python scripts/import_vocab.py [--file PATH] [--dry] [--json-only]
"""
import argparse, datetime, hashlib, io, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import loose, skeleton, arabic_norm, arabic_core, ARABIC
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
VOCAB = ROOT / 'data' / 'vocab'
DOCS_DATA = ROOT / 'docs' / 'data'
DOC_ID = '1inA6ZeETtqJZHQYiZxtubWytsN5xh8_klQH50yRyrjw'
MIN_WORDS = 1500          # below this the fetch is broken (the Doc has ~2,100 words); never mass-deactivate
HEAD_RE = re.compile(r'^\s*(?:\d+\.\s+)?(#{1,3})\s+(.*?)\s*$')
SEP_RE = re.compile(r'^\|\s*:?-')


def clean(c):
    c = c.replace('\\*', '').replace('**', '').replace('\\', '')
    c = re.sub(r'[​‌‍﻿]', '', c)
    return re.sub(r'\s+', ' ', c).strip()


def roles_from_header(cells):
    roles = []
    for c in cells:
        l = c.lower()
        if 'translit' in l:
            roles.append('arabizi')
        elif 'plural' in l or 'forms' in l:
            roles.append('plural')
        elif 'arabic' in l:
            roles.append('arabic')
        elif 'english' in l:
            roles.append('english')
        else:
            roles.append('')
    return roles if 'arabic' in roles and ('arabizi' in roles or 'english' in roles) else None


def roles_by_content(cells):
    """Fallback when a table has no header row: the Arabic-script cell is Arabic; first Latin cell is Arabizi; last is English."""
    n = len(cells)
    ar = [i for i, c in enumerate(cells) if ARABIC.search(c)]
    if not ar:
        return None
    a = ar[0]
    roles = [''] * n
    roles[a] = 'arabic'
    latin = [i for i in range(n) if i != a]
    if not latin:
        return None
    if n == 4 and a == 2:
        roles[0], roles[1], roles[3] = 'arabizi', 'plural', 'english'
    else:
        roles[latin[0]] = 'arabizi'
        if len(latin) > 1:
            roles[latin[-1]] = 'english'
    return roles


def split_slash(s):
    parts = [p.strip() for p in re.split(r'\s*/\s*', s) if p.strip()]
    return parts or [s]


def arabizi_forms(s):
    """'Mu7aadase/a' -> ['Mu7aadase', 'Mu7aadasa']; 'Babse6 / Btebse6' -> both; plain -> [s]."""
    parts = split_slash(s)
    if len(parts) == 1:
        return parts
    base = parts[0]
    out = [base]
    for p in parts[1:]:
        if len(p) <= 2 and len(base) > 3:          # feminine / short suffix variant
            out.append(re.sub(r'[aeiou]?$', '', base) + p if base[-1:] in 'aeiou' else base + p)
        else:
            out.append(p)
    return out


def parse_markdown(text):
    lines = text.split('\n')
    tab = topic = sub = ''
    last_h1_had_rows = True
    roles = None
    rows, order = [], 0
    for line in lines:
        m = HEAD_RE.match(line)
        if m:
            level, title = len(m.group(1)), clean(m.group(2))
            if level == 1:
                if not last_h1_had_rows and topic:
                    tab = topic                       # previous H1 was only a tab name
                else:
                    tab = title
                topic, sub = title, ''
                last_h1_had_rows = False
            else:
                sub = title
            roles = None
            continue
        if not line.startswith('|'):
            if not line.strip():
                pass
            continue
        if SEP_RE.match(line):
            continue
        cells = [clean(c) for c in line.strip().strip('|').split('|')]
        if all(c == '' for c in cells):
            continue
        r = roles_from_header(cells)
        if r:
            roles = r
            continue
        rr = roles if roles and len(roles) == len(cells) else roles_by_content(cells)
        if not rr:
            continue
        rec = {k: '' for k in ('arabizi', 'arabic', 'english', 'plural')}
        for role, c in zip(rr, cells):
            if role:
                rec[role] = (rec[role] + ' / ' + c) if rec[role] and c else (rec[role] or c)
        rec = fix_swapped(rec)
        if not rec['arabizi'] or rec['arabizi'] in ('—', '-', '–') or not rec['arabic']:
            continue
        order += 1
        rows.append({**rec, 'topic': topic or tab, 'subtopic': sub or topic or tab, 'tab': tab or topic, 'doc_order': order})
        last_h1_had_rows = True
    return rows


def fix_swapped(rec):
    """Some Doc tables put Arabic under the Transliteration header and vice versa: trust the script, not the header."""
    if ARABIC.search(rec['arabizi']) and not ARABIC.search(rec['arabic']):
        rec['arabizi'], rec['arabic'] = rec['arabic'], rec['arabizi']
    return rec


def parse_html(html_text):
    """Google Docs HTML (export or publish-to-web): headings h1/h2/h3 + tables. Same row logic as markdown."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, 'html.parser')
    body = soup.body or soup
    tab = topic = sub = ''
    last_h1_had_rows = True
    rows, order = [], 0
    for el in body.find_all(['h1', 'h2', 'h3', 'table', 'p']):
        if el.name in ('h1', 'h2', 'h3'):
            title = clean(el.get_text(' '))
            if not title:
                continue
            if el.name == 'h1':
                tab = topic if (not last_h1_had_rows and topic) else title
                topic, sub, last_h1_had_rows = title, '', False
            else:
                sub = title
        elif el.name == 'p' and el.get('class') and any('title' in c for c in el.get('class')):
            # tab titles in publish-to-web are plain paragraphs with a title class
            tab, topic, sub, last_h1_had_rows = clean(el.get_text(' ')), clean(el.get_text(' ')), '', False
        elif el.name == 'table':
            roles = None
            for tr in el.find_all('tr'):
                cells = [clean(td.get_text(' ')) for td in tr.find_all(['td', 'th'])]
                if not cells or all(c == '' for c in cells):
                    continue
                r = roles_from_header(cells)
                if r:
                    roles = r; continue
                rr = roles if roles and len(roles) == len(cells) else roles_by_content(cells)
                if not rr:
                    continue
                rec = {k: '' for k in ('arabizi', 'arabic', 'english', 'plural')}
                for role, c in zip(rr, cells):
                    if role:
                        rec[role] = (rec[role] + ' / ' + c) if rec[role] and c else (rec[role] or c)
                rec = fix_swapped(rec)
                if not rec['arabizi'] or rec['arabizi'] in ('—', '-', '–') or not rec['arabic']:
                    continue
                order += 1
                rows.append({**rec, 'topic': topic or tab, 'subtopic': sub or topic or tab, 'tab': tab or topic, 'doc_order': order})
                last_h1_had_rows = True
    return rows


def same_word(a, b):
    """Same Arabic word? Pronoun prefixes and bracketed extras are ignored ('أنا بخاف' == 'بخاف'; 'ساعة (ساعتين)' == 'ساعة');
    a Doc typo that truncates a word ('م' for 'ممكن') counts as the same word."""
    ca, cb = arabic_core(a), arabic_core(b)
    if ca == cb:
        return True
    lo, hi = sorted((ca, cb), key=len)
    return len(lo) >= 1 and hi.startswith(lo) and len(lo) * 2 < len(hi)


def to_words(rows):
    """Rows -> unique word records keyed by loose(Arabizi). Same key + same Arabic = merged; same key + other Arabic = key~2."""
    words, by_key = [], {}
    dup_merged = 0
    for r in rows:
        forms = arabizi_forms(r['arabizi'])
        key0 = loose(forms[0])
        if not key0:
            continue
        ar_parts = split_slash(r['arabic'])
        arabic, arabic_plural = ar_parts[0], (ar_parts[1] if len(ar_parts) > 1 else '')
        an = arabic_norm(arabic)
        key, n = key0, 1
        while key in by_key and not same_word(by_key[key]['arabic_norm'], an):
            n += 1; key = f'{key0}~{n}'
        if key in by_key:
            w = by_key[key]; dup_merged += 1
            if r['english'] and r['english'].lower() not in w['english'].lower():
                w['english'] = (w['english'] + ' / ' + r['english']) if w['english'] else r['english']
            for f in forms[1:]:
                if f not in w['aliases'] and f != w['arabizi']:
                    w['aliases'].append(f)
            continue
        plural = r.get('plural', '')
        if plural in ('—', '-', '–'):
            plural = ''
        w = {'key': key, 'arabizi': forms[0], 'arabic': arabic, 'english': r['english'], 'plural': plural, 'arabic_plural': arabic_plural,
             'topic': r['topic'], 'subtopic': r['subtopic'], 'tab': r['tab'], 'doc_order': r['doc_order'],
             'match_loose': key0, 'match_skeleton': skeleton(forms[0]), 'arabic_norm': an, 'aliases': forms[1:]}
        by_key[key] = w; words.append(w)
    for w in words:
        h = hashlib.sha1('|'.join([w['arabizi'], w['arabic'], w['english'], w['plural'], w['topic'], w['subtopic'], ','.join(w['aliases'])]).encode('utf-8')).hexdigest()[:16]
        w['row_hash'] = h
    return words, dup_merged


def load_source(path=None):
    """Returns (text, kind, label). kind = 'md' | 'html'."""
    if path:
        p = Path(path); t = io.open(p, encoding='utf-8').read()
        return t, ('html' if p.suffix.lower() in ('.html', '.htm') else 'md'), str(p)
    url = E.env('ANEES_DOC_PUBLISHED_URL')
    if url:
        import requests
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f'published Doc fetch failed: HTTP {r.status_code}')
        return r.text, 'html', url
    snaps = sorted(VOCAB.glob('doc_markdown_*.md'))
    if not snaps:
        raise RuntimeError('no Doc source: pass --file or set ANEES_DOC_PUBLISHED_URL')
    return io.open(snaps[-1], encoding='utf-8').read(), 'md', f'{snaps[-1]} (snapshot; no live source configured)'


def sync(words, dry=False):
    """Upsert changed rows only; deactivate rows that left the Doc. Returns counts."""
    import db
    existing = {r['key']: r for r in db.select('words', {'select': 'key,row_hash,active'})}
    active_n = sum(1 for r in existing.values() if r['active'])
    if len(words) < MIN_WORDS or (active_n and len(words) < 0.8 * active_n):
        # a broken/empty fetch must never wipe the table (mass-deactivate). Fail loudly instead.
        raise RuntimeError(f'refusing to sync: only {len(words)} words parsed (table has {active_n} active, floor {MIN_WORDS})')
    changed = [w for w in words if existing.get(w['key'], {}).get('row_hash') != w['row_hash'] or not existing.get(w['key'], {}).get('active', True)]
    gone = [k for k, r in existing.items() if r['active'] and k not in {w['key'] for w in words}]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not dry:
        payload = [{**w, 'active': True, 'updated_at': now} for w in changed]
        db.upsert('words', payload, on='key')
        for k in gone:
            db.rest('PATCH', 'words', params={'key': f'eq.{k}'}, body={'active': False, 'updated_at': now}, prefer='return=minimal')
    return {'total': len(words), 'inserted': sum(1 for w in changed if w['key'] not in existing), 'updated': sum(1 for w in changed if w['key'] in existing),
            'deactivated': len(gone), 'unchanged': len(words) - len(changed)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file'); ap.add_argument('--dry', action='store_true'); ap.add_argument('--json-only', action='store_true')
    a = ap.parse_args()
    text, kind, label = load_source(a.file)
    rows = parse_html(text) if kind == 'html' else parse_markdown(text)
    words, merged = to_words(rows)
    VOCAB.mkdir(parents=True, exist_ok=True); DOCS_DATA.mkdir(parents=True, exist_ok=True)
    snap = {'doc_id': DOC_ID, 'source': label, 'exported': datetime.datetime.now().isoformat(timespec='seconds'), 'rows': len(rows), 'words': len(words), 'merged_duplicates': merged, 'items': words}
    io.open(VOCAB / 'words.json', 'w', encoding='utf-8').write(json.dumps(snap, ensure_ascii=False, indent=0))
    io.open(DOCS_DATA / 'words.json', 'w', encoding='utf-8').write(json.dumps({k: v for k, v in snap.items() if k != 'items'} | {'items': [{k: w[k] for k in ('key', 'arabizi', 'arabic', 'english', 'plural', 'topic', 'subtopic', 'match_loose', 'match_skeleton', 'arabic_norm', 'aliases')} for w in words]}, ensure_ascii=False))
    print(f'source: {label}\nrows: {len(rows)}  words: {len(words)}  merged duplicates: {merged}  topics: {len({w["topic"] for w in words})}  subtopics: {len({(w["topic"], w["subtopic"]) for w in words})}')
    if a.json_only:
        return
    res = sync(words, dry=a.dry)
    print('supabase:', json.dumps(res))


if __name__ == '__main__':
    main()
