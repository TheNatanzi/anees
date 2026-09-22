"""Hold-one-out report for scripts/verb_forms.py.

Golden forms = every documented verb form in the Word Bank catalog plus Amal's
Quizlet "Verbs (Present tense)" set. Two tests:
  hold-one-out: hide one documented form, give the engine the rest, compare.
  cold:         give the engine only the present "I" form (how most guesses are made).
A hit = same word after arabizi.fold (house spelling: e/i, o/u, doubled letters, 2/3 ignored).
Arabic hit = same letters after removing diacritics and hamza seat differences.
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verb_forms as vf
from arabizi import fold

SKIP = {'beddi', 'ba2addi wa2et', 'badir baali', 'bajahhez 7aali'}
QUIZLET_PERSON = {'ana': 'I', 'enta': 'You (m)', 'enti': 'You (f)', 'entu': 'You (pl)', 'huwwe': 'He',
                  'heyye': 'She', 'humme': 'They', 'e7na': 'We'}


def ar_norm(a):
    a = vf.AR_DIACRITICS.sub('', a or '')
    a = re.sub('[أإآ]', 'ا', a).replace('ى', 'ي').replace('ة', 'ه').replace('ذ', 'ز').replace('ظ', 'ض')
    return re.sub(r'وا$', 'و', a.strip())


def load(catalog_path=None, quizlet_path=None):
    catalog = json.loads(Path(catalog_path or ROOT / 'docs/data/word-bank-catalog.json').read_text(encoding='utf-8'))
    verbs = {}
    for g in catalog['groups']:
        if g['type'] != 'Verb' or g['name'].lower() in SKIP:
            continue
        forms = defaultdict(dict)
        for e in g['entries']:
            if e['label'] not in vf.TENSES:
                continue
            for p in e['persons']:
                if p['provenance'] != 'document':
                    continue
                word = vf.strip_pronoun(p['word'])
                if ' / ' in word and not (e['label'] == 'Present' and p['person'] == 'I'):
                    continue
                ar = vf.strip_ar_pronoun(p.get('arabic', ''))
                m = re.fullmatch(r'(\S+?)/ي/وا', vf.AR_DIACRITICS.sub('', e.get('arabic', '')).strip())
                if e['label'] == 'Command' and not ar and m:
                    body = m[1][:-1] if m[1].endswith(('ي', 'ى')) else m[1]
                    ar = {'You (m)': m[1], 'You (f)': body + 'ي', 'You (pl)': body + 'وا'}[p['person']]
                forms[e['label']][p['person']] = (word, ar)
        if not forms['Present'].get('I'):
            continue
        verbs[g['key']] = {'name': g['name'], 'forms': dict(forms), 'quizlet': {}}
    by_fold = {fold(v['forms']['Present']['I'][0]): k for k, v in verbs.items()}
    qz = json.loads(Path(quizlet_path or ROOT / 'docs/data/quizlet/amal-quizlet-sets.json').read_text(encoding='utf-8'))
    present_set = next(s for s in qz['sets'] if s['title'] == 'Verbs (Present tense)')
    current = None
    for term in present_set['terms']:
        parts = [x.strip() for x in ' | '.join(term).split('|') if x.strip()]
        ar = next((x for x in parts if re.search('[؀-ۿ]', x)), '')
        rz = next((x for x in parts if re.match(r'^[A-Za-z]+\s+\S+$', x) and x.split()[0].lower() in QUIZLET_PERSON), '')
        m = re.match(r'^(\w+)\s+(\S+)$', rz)
        if not m or m[1].lower() not in QUIZLET_PERSON:
            continue
        person = QUIZLET_PERSON[m[1].lower()]
        word = m[2].lower()
        if person == 'I':
            current = by_fold.get(fold('b' + word[1:] if word.startswith('b') else word))
            continue
        if current:
            verbs[current]['quizlet'][person] = (word, vf.strip_ar_pronoun(ar))
    return verbs


def score(verbs):
    rows = []
    for key, v in verbs.items():
        forms = v['forms']
        golden = [(t, p, f, 'doc') for t in vf.TENSES for p, f in forms.get(t, {}).items() if not (t == 'Present' and p == 'I')]
        golden += [('Present', p, f, 'quizlet') for p, f in v['quizlet'].items()]
        cold_in = {'Present': {'I': forms['Present']['I']}}
        cold = vf.conjugate(cold_in)
        for t, p, (word, ar), src in golden:
            held = {tt: {pp: ff for pp, ff in fs.items() if not (tt == t and pp == p)} for tt, fs in forms.items()}
            got = vf.conjugate(held).get(t, {}).get(p)
            gc = cold.get(t, {}).get(p)
            rows.append({'verb': v['name'], 'tense': t, 'person': p, 'source': src, 'want': word, 'want_ar': ar,
                         'hold': got['word'] if got else '', 'hold_ar': got['arabic'] if got else '',
                         'cold': gc['word'] if gc else '', 'cold_ar': gc['arabic'] if gc else ''})
    for r in rows:
        r['hold_hit'] = bool(r['hold']) and fold(r['hold']) == fold(r['want'])
        r['cold_hit'] = bool(r['cold']) and fold(r['cold']) == fold(r['want'])
        r['has_ar'] = bool(r['want_ar'])
        r['hold_ar_hit'] = r['has_ar'] and ar_norm(r['hold_ar']) == ar_norm(r['want_ar'])
        r['cold_ar_hit'] = r['has_ar'] and ar_norm(r['cold_ar']) == ar_norm(r['want_ar'])
    return rows


def summary(rows):
    out = {}
    for t in vf.TENSES:
        rs = [r for r in rows if r['tense'] == t]
        ar = [r for r in rs if r['has_ar']]
        out[t] = {'forms': len(rs),
                  'hold': sum(r['hold_hit'] for r in rs), 'cold': sum(r['cold_hit'] for r in rs),
                  'arabic_forms': len(ar),
                  'hold_ar': sum(r['hold_ar_hit'] for r in ar), 'cold_ar': sum(r['cold_ar_hit'] for r in ar)}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--misses', choices=['hold', 'cold', 'hold_ar', 'cold_ar']); ap.add_argument('--tense'); ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    rows = score(load())
    s = summary(rows)
    for t, x in s.items():
        pct = lambda n, d: f'{n}/{d} = {100 * n / d:.0f}%' if d else '-'
        print(f"{t:8} hold-one-out {pct(x['hold'], x['forms'])} | cold {pct(x['cold'], x['forms'])} | "
              f"Arabic hold {pct(x['hold_ar'], x['arabic_forms'])} | Arabic cold {pct(x['cold_ar'], x['arabic_forms'])}")
    if a.misses:
        field = a.misses + '_hit'
        want = 'want_ar' if a.misses.endswith('_ar') else 'want'
        got = a.misses
        for r in rows:
            if (not a.tense or r['tense'] == a.tense) and not r[field] and (r['has_ar'] or not a.misses.endswith('_ar')):
                print(f"  {r['verb']:12} {r['tense']:8} {r['person']:9} want {r[want]:14} got {r[got]:14} [{r['source']}]")
    if a.json:
        a.json.write_text(json.dumps({'summary': s, 'rows': rows}, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
