# -*- coding: utf-8 -*-
"""The secondary reference lexicon (rule AM-25, Medi 2026-10-06: "Lets spin up a new agent to do deep research on
different levantine arabic curriculum that you can create an index for yourself to use as a secondary data source, it may
be useful to amal to help her" ... "ingest").

    python scripts/build_reference_lexicon.py                 # data/reference/raw/* -> docs/data/reference-lexicon.json
    python scripts/build_reference_lexicon.py --raw D --out F --words W --max-bytes N

What it is NOT (RULES.md S1): a spelling, or a score. Amal's Doc (docs/data/words.json) stays the only word truth and
her spelling the only spelling. The reference is read for glosses, roots, plurals, example sentences and
verb-preposition hints only, keyed by NORMALISED Arabic so a Doc word can be looked up; nothing here is ever written
into her data and nothing here changes what a word scores.

Sources (raw dumps live in data/reference/raw/, git-ignored; data/reference/README.md has the URLs, dates, licenses):
  kaikki-ajp.jsonl      Wiktionary South Levantine Arabic via kaikki.org   CC BY-SA 3.0
  kaikki-apc.jsonl      Wiktionary North Levantine Arabic via kaikki.org   CC BY-SA 3.0
  maknuune-*.tsv        Maknuune Palestinian Arabic lexicon (CAMeL Lab)    CC BY-SA 4.0

Output: {"about", "built", "sources": {...counts}, "records": {norm: record}, "index": {norm(form): norm(lemma)}}
  record = {arabic, pos, gloss[], root, plural, forms{past, present}, examples[{ar, en}] (max 3),
            preps[] (prepositions seen right after the verb: ل على عن مع ب في من إلى), sources[{src, license}]}
The file stays under --max-bytes (6 MB): examples are dropped first (most-populated records first), then the
form index, and the builder says what it dropped. The coverage report (Amal's Doc words found, by part of speech)
is printed at the end and returned by build() for the test.

Normalisation (the same in docs/js/reference-lexicon.js, tested against the same fixture): strip diacritics and
tatweel, أ إ آ -> ا, ى -> ي, ة -> ه, collapse spaces.
"""
from __future__ import annotations

import argparse, csv, io, json, os, re, sys, time
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'reference' / 'raw'
OUT = ROOT / 'docs' / 'data' / 'reference-lexicon.json'
WORDS = ROOT / 'docs' / 'data' / 'words.json'
MAX_BYTES = 6_000_000
MAX_EXAMPLES = 3
MAX_GLOSSES = 6

LICENSES = {'kaikki-ajp': 'CC BY-SA 3.0', 'kaikki-apc': 'CC BY-SA 3.0', 'maknuune': 'CC BY-SA 4.0'}

_DIAC = re.compile(r'[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]')     # harakat, shadda, sukun, tatweel
_PUNCT = re.compile(r'[\u061f\u060c\u061b?!.,;:"\'()\[\]\u00ab\u00bb]')     # ? , ; (Arabic and Latin marks)
PREPS = ('علي', 'عن', 'مع', 'في', 'من', 'الي', 'ل', 'ب')                            # as norm() writes them (على -> علي)
PREP_OUT = {'علي': 'على', 'عن': 'عن', 'مع': 'مع', 'في': 'في', 'من': 'من', 'الي': 'إلى', 'ل': 'ل', 'ب': 'ب'}
PRON_SUFFIX = ('ي', 'ني', 'ك', 'كي', 'ه', 'ها', 'نا', 'كم', 'كو', 'هم', 'هن')
# a leading subject pronoun on a Doc word ("أنا بخاف") is not part of the lemma (scripts/arabizi.py arabic_core does the same)
PRONOUNS = ('انا', 'انت', 'انتي', 'هو', 'هي', 'احنا', 'نحنا', 'انتو', 'انتم', 'هم', 'هني', 'هنه', 'همه')


def norm(s):
    """Normalised Arabic: the lookup key (mirrors normalise() in docs/js/reference-lexicon.js)."""
    s = _PUNCT.sub(' ', _DIAC.sub('', str(s or '')))
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٱ', 'ا').replace('ى', 'ي').replace('ة', 'ه')
    s = re.sub(r'[\s ]+', ' ', s).strip()
    return s


def strip_pronoun(key):
    toks = key.split(' ')
    while len(toks) > 1 and toks[0] in PRONOUNS:
        toks = toks[1:]
    return ' '.join(toks)


def prep_after(tokens, verb_forms):
    """The prepositions that follow a verb form inside a token list (normalised), in order of appearance.
    'فتح على' -> على; 'فتحت عليه' -> على; 'كتب بالقلم' -> ب; 'كتبت للمدير' / 'كتبت لأهلي' -> ل; 'حكى إلها' -> ل.
    A ب or ل that is simply the first letter of a noun (بيت, لون) is not a preposition: only the article, a pronoun
    suffix, or (for ل) an assimilated لل / a hamza word (لا... of 5+ letters) count."""
    out = []
    for i, t in enumerate(tokens[:-1]):
        if t not in verb_forms:
            continue
        nxt = tokens[i + 1]
        hit = None
        for p in PREPS:
            if nxt == p:
                hit = p; break
            if len(p) > 1 and nxt.startswith(p) and nxt[len(p):] in PRON_SUFFIX:
                hit = p; break
            if p in ('ل', 'ب') and nxt.startswith(p + 'ال') and len(nxt) > 4:
                hit = p; break
            if p in ('ل', 'ب') and len(nxt) > 2 and nxt[0] == p and nxt[1:] in PRON_SUFFIX:
                hit = p; break
            if p == 'ل' and nxt.startswith('لل') and len(nxt) > 3:
                hit = p; break
            if p == 'ل' and nxt.startswith('لا') and len(nxt) >= 5:
                hit = p; break
            if p == 'ل' and nxt.startswith('ال') and nxt[2:] in PRON_SUFFIX:        # إله / إلها
                hit = p; break
        if hit:
            out.append(PREP_OUT[hit])
    return out


def _tokens(text):
    return [t for t in norm(re.sub(r'[^؀-ۿ\s]+', ' ', text or '')).split(' ') if t]


# ---- records -------------------------------------------------------------------------------------------------------

def new_record(arabic, pos):
    return OrderedDict(arabic=arabic, pos=pos, gloss=[], root='', plural='', forms={}, examples=[], preps=[], sources=[])


def merge(rec, arabic, pos, gloss, root, plural, forms, examples, preps, src):
    if not rec['arabic']:
        rec['arabic'] = arabic
    if pos and pos not in (rec['pos'] or '').split('/'):
        rec['pos'] = (rec['pos'] + '/' + pos) if rec['pos'] else pos
    for g in gloss:
        if g and g not in rec['gloss'] and len(rec['gloss']) < MAX_GLOSSES:
            rec['gloss'].append(g)
    if root and not rec['root']:
        rec['root'] = root
    if plural and not rec['plural']:
        rec['plural'] = plural
    for k, v in (forms or {}).items():
        if v and k not in rec['forms']:
            rec['forms'][k] = v
    for e in examples:
        if e and e not in rec['examples'] and len(rec['examples']) < MAX_EXAMPLES:
            rec['examples'].append(e)
    for p in preps:
        if p and p not in rec['preps']:
            rec['preps'].append(p)
    if not any(s['src'] == src for s in rec['sources']):
        rec['sources'].append({'src': src, 'license': LICENSES[src]})


# ---- kaikki (Wiktionary via kaikki.org) -----------------------------------------------------------------------------

KAIKKI_POS = {'intj': 'intj', 'name': 'name', 'num': 'num', 'det': 'det', 'phrase': 'phrase', 'suffix': 'suffix',
              'particle': 'particle', 'proverb': 'proverb', 'article': 'article', 'character': 'character'}


def read_kaikki(path, src, records, index, counts):
    n = 0
    with io.open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            word = d.get('word') or ''
            key = norm(word)
            if not key or not re.search('[؀-ۿ]', key):
                continue
            n += 1
            pos = KAIKKI_POS.get(d.get('pos'), d.get('pos') or '')
            gloss, examples = [], []
            for s in d.get('senses') or []:
                for g in s.get('glosses') or []:
                    g = re.sub(r'\s+', ' ', g).strip()
                    if g and g not in gloss:
                        gloss.append(g)
                for e in s.get('examples') or []:
                    ar, en = (e.get('text') or '').strip(), (e.get('english') or e.get('translation') or '').strip()
                    if ar and en and not ar.startswith('Audio'):
                        examples.append({'ar': ar, 'en': en})
            root = ''
            for t in d.get('etymology_templates') or []:
                if t.get('name') in ('ajp-root', 'apc-root', 'ar-root') and (t.get('args') or {}).get('1'):
                    root = t['args']['1']; break
            if not root:
                for c in (d.get('categories') or []) + [c for s in d.get('senses') or [] for c in s.get('categories') or []]:
                    m = re.search(r'belonging to the root (.+)$', c.get('name') or '')
                    if m:
                        root = m.group(1); break
            root = '.'.join(root.split()) if root else ''
            plural, forms, verb_forms, conj = '', {}, set(), set()
            for fm in d.get('forms') or []:
                tags, form = set(fm.get('tags') or []), (fm.get('form') or '').strip()
                if not form or not re.search('[؀-ۿ]', form):
                    continue
                if tags <= {'plural', 'common', 'canonical', 'masculine', 'feminine'} and 'plural' in tags and not plural \
                        and pos != 'verb':
                    plural = form
                if pos == 'verb':
                    if tags == {'present'} or tags == {'masculine', 'present', 'singular', 'third-person'}:
                        forms.setdefault('present', form)
                    if tags == {'masculine', 'past', 'singular', 'third-person'}:
                        forms.setdefault('past', form)
                    if {'present', 'past', 'subjunctive', 'imperative'} & tags:
                        verb_forms.add(norm(form))
                    if {'present', 'past'} & tags and fm.get('source') == 'conjugation':
                        conj.add(form)                                # every person: Amal's Doc lists "أنا أكلت", "هم أكلوا"
            if pos == 'verb':
                forms.setdefault('past', word)
                for h in d.get('head_templates') or []:
                    pres = (h.get('args') or {}).get('pres')
                    if pres and 'present' not in forms:
                        forms['present'] = pres
                verb_forms.add(key)
                if forms.get('present'):
                    verb_forms.add(norm(forms['present']))
            preps = []
            if pos == 'verb':
                for e in examples:
                    preps += prep_after(_tokens(e['ar']), verb_forms)
            rec = records.get(key)
            if rec is None:
                rec = records[key] = new_record(word, pos)
            merge(rec, word, pos, gloss[:MAX_GLOSSES], root, plural, forms, examples, preps, src)
            for fv in list(forms.values()) + ([plural] if plural else []) + sorted(conj):
                fk = norm(fv)
                if fk and fk != key and fk not in records:
                    index.setdefault(fk, key)
    counts[src] = n
    return n


# ---- Maknuune (CAMeL Lab) -------------------------------------------------------------------------------------------

MAK_POS = {'VERB': 'verb', 'NOUN': 'noun', 'ADJ': 'adj', 'ADV': 'adv', 'PRON': 'pron', 'PREP': 'prep', 'CONJ': 'conj',
           'INTERJ': 'intj', 'NUM': 'num', 'PART': 'particle', 'ABBREV': 'abbrev'}


def mak_pos(analysis):
    head = (analysis or '').split(':')[0]
    base = head.split('_')[0].split('/')[0]
    pos = MAK_POS.get(base, base.lower())
    if head in ('NOUN_ACT', 'NOUN_PASS'):
        pos = 'participle'
    elif head == 'NOUN_PROP':
        pos = 'name'
    elif head in ('NOUN_NUM', 'ADJ_NUM'):
        pos = 'num'
    elif head == 'VERB_PSEUDO':
        pos = 'pseudo-verb'
    return pos


def mak_gloss(g):
    out = []
    for part in (g or '').split(';'):
        part = part.replace('_[auto]', '').replace('_', ' ').strip()
        if part and part != 'see phrase' and part not in out:
            out.append(part)
    return out


def read_maknuune(path, src, records, index, counts):
    with io.open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f, delimiter='\t'))
    if not rows:
        counts[src] = 0
        return 0
    h = rows[0]
    col = {name: h.index(name) for name in ('ROOT', 'LEMMA', 'FORM', 'ANALYSIS', 'GLOSS', 'EXAMPLE_USAGE') if name in h}
    if len(col) < 6:
        raise SystemExit(f'{path}: not a Maknuune TSV (columns {h[:6]})')
    groups = OrderedDict()                                            # (lemma, pos) -> rows
    n = 0
    for r in rows[1:]:
        if len(r) <= max(col.values()):
            continue
        n += 1
        lemma, analysis = r[col['LEMMA']].strip(), r[col['ANALYSIS']].strip()
        groups.setdefault((lemma, mak_pos(analysis)), []).append(r)
    for (lemma, pos), grp in groups.items():
        key = norm(lemma)
        if not key:
            continue
        gloss, examples, plural, forms, preps, root = [], [], '', {}, [], ''
        verb_forms = {key}
        phrase_rows, lemma_rows = [], []
        for r in grp:
            analysis, form = r[col['ANALYSIS']], r[col['FORM']].strip()
            kind = analysis.split(':')[1] if ':' in analysis else ''
            rt = r[col['ROOT']].strip()
            if rt and rt != 'NTWS' and not root:
                root = rt
            if kind == 'PHRASE':
                phrase_rows.append(r); continue
            lemma_rows.append(r)
            if pos == 'verb':
                if kind == 'P':
                    forms.setdefault('past', form)
                elif kind == 'I':
                    forms.setdefault('present', form)
                verb_forms.add(norm(form))
            elif kind in ('P', 'FP', 'MP') and norm(form) != key and not plural:
                plural = form
        for r in lemma_rows:
            for g in mak_gloss(r[col['GLOSS']]):
                if g not in gloss:
                    gloss.append(g)
            for ex in (r[col['EXAMPLE_USAGE']] or '').split('#'):
                ex = ex.strip()
                if ex and all(ex != e['ar'] for e in examples):
                    examples.append({'ar': ex, 'en': ''})
        if pos == 'verb':
            for e in examples:
                preps += prep_after(_tokens(e['ar']), verb_forms)
            for r in phrase_rows:                                     # "فتح على" style phrase heads
                preps += prep_after(_tokens(r[col['FORM']]), verb_forms)
        rec = records.get(key)
        if rec is None:
            rec = records[key] = new_record(lemma, pos)
        merge(rec, lemma, pos, gloss[:MAX_GLOSSES], root, plural, forms, examples, preps, src)
        keys = [norm(fv) for fv in list(forms.values()) + ([plural] if plural else [])]
        pres = norm(forms.get('present', ''))
        if pres.startswith('ي') and len(pres) > 2:
            keys.append('ب' + pres[1:])          # Maknuune writes the bare imperfective (يخاف); Amal's Doc the b-form (بخاف)
        for fk in keys:                           # an index KEY only - never shown, never a spelling (S1)
            if fk and fk != key and fk not in records:
                index.setdefault(fk, key)
    counts[src] = n
    return n


# ---- coverage (Amal's Doc words) ------------------------------------------------------------------------------------

def lookup(records, index, arabic):
    """The record for a Doc word, or None: exact key, then a listed form, then without a leading pronoun / ال."""
    key = norm(arabic)
    tries = [key]
    sp = strip_pronoun(key)
    if sp != key:
        tries.append(sp)
    for t in list(tries):
        if t.startswith('ال') and len(t) > 4:
            tries.append(t[2:])
    for t in tries:
        if t in records:
            return records[t], t
        if t in index and index[t] in records:
            return records[index[t]], index[t]
    return None, None


def coverage(records, index, words):
    items = words.get('items') if isinstance(words, dict) else words
    by_pos, miss_topic, found = Counter(), Counter(), 0
    total = 0
    for it in items or []:
        ar = (it.get('arabic') or '').strip()
        if not ar:
            continue
        total += 1
        rec, _ = lookup(records, index, ar)
        if rec:
            found += 1
            by_pos[(rec['pos'] or '?').split('/')[0]] += 1          # the first-seen part of speech
        else:
            miss_topic[it.get('topic') or '?'] += 1
    return {'total': total, 'found': found, 'by_pos': dict(by_pos.most_common()), 'missed_by_topic': dict(miss_topic.most_common())}


# ---- build ---------------------------------------------------------------------------------------------------------

def _dump(doc):
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':'))


def build(raw=RAW, out=OUT, words_path=WORDS, max_bytes=MAX_BYTES, log=print):
    raw = Path(raw)
    records, index, counts = OrderedDict(), {}, OrderedDict()
    files = []
    for name in ('kaikki-ajp.jsonl', 'kaikki-apc.jsonl'):
        p = raw / name
        if p.is_file():
            files.append((name, p))
    maks = sorted(raw.glob('maknuune*.tsv'))
    if not files and not maks:
        raise SystemExit(f'no raw files in {raw} (see data/reference/README.md for the downloads)')
    for name, p in files:
        src = 'kaikki-ajp' if 'ajp' in name else 'kaikki-apc'
        log(f'{src}: {read_kaikki(p, src, records, index, counts)} entries read from {p.name}')
    for p in maks[-1:]:                                                 # the newest TSV only
        log(f'maknuune: {read_maknuune(p, "maknuune", records, index, counts)} rows read from {p.name}')
    index = {k: v for k, v in index.items() if k not in records}
    doc = OrderedDict(about='Secondary reference lexicon (AM-25): glosses, roots, plurals, examples and verb-preposition '
                            'hints from open Levantine sources. Never a spelling (RULES.md S1), never a score. '
                            'Amal\'s Doc (words.json) is the only word truth.',
                      built=time.strftime('%Y-%m-%d'), licenses=LICENSES, sources=counts, record_count=len(records),
                      records=records, index=index)
    dropped = []
    body = _dump(doc)
    size = len(body.encode('utf-8'))
    if size > max_bytes:                                                # examples go first, fattest records first
        weight = {k: len(_dump(r['examples']).encode('utf-8')) - 2 for k, r in records.items() if r['examples']}
        for k in sorted(weight, key=lambda k: -weight[k]):
            if size <= max_bytes:
                break
            records[k]['examples'] = []
            size -= weight[k]
            dropped.append('examples')
        body = _dump(doc)
    if len(body.encode('utf-8')) > max_bytes:
        doc['index'] = {}
        dropped.append('index')
        body = _dump(doc)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, 'w', encoding='utf-8', newline='\n').write(body)
    size = len(body.encode('utf-8'))
    log(f'wrote {out} ({size / 1e6:.2f} MB, {len(records)} records, {len(doc["index"])} form index rows)'
        + (f'; dropped examples from {dropped.count("examples")} records' if 'examples' in dropped else '')
        + ('; dropped the form index' if 'index' in dropped else ''))
    cov = None
    words_path = Path(words_path) if words_path else None
    if words_path and words_path.is_file():
        cov = coverage(records, doc['index'], json.load(io.open(words_path, encoding='utf-8')))
        log(f'coverage: {cov["found"]} of {cov["total"]} Doc words found in the reference '
            f'({100.0 * cov["found"] / max(1, cov["total"]):.1f}%)')
        for pos, n in cov['by_pos'].items():
            log(f'  found as {pos}: {n}')
        log('  not found, by Doc topic: ' + ', '.join(f'{t} {n}' for t, n in list(cov['missed_by_topic'].items())[:12]))
    return {'records': len(records), 'sources': dict(counts), 'bytes': size, 'dropped': dropped, 'coverage': cov}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--raw', default=str(RAW))
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--words', default=str(WORDS))
    ap.add_argument('--max-bytes', type=int, default=MAX_BYTES)
    a = ap.parse_args(argv)
    build(a.raw, a.out, a.words, a.max_bytes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
