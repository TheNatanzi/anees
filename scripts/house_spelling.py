"""M10a - house spelling: Amal's own Arabizi form of every Doc word, mined from her typed WhatsApp lines.

Her form becomes the DISPLAY spelling wherever Anees prints a word (Words tab, cards, reports); the Doc key stays the match
key. Only exact / fold / short tiers of the loose matcher are trusted (no skeleton or fuzzy guesses); a Doc word gets a house
spelling only when one of her forms is seen >= MIN_SEEN times, and the most frequent form wins. Ties are never guessed: the
most recent of the tied forms wins and both are listed in `forms`.

  python scripts/house_spelling.py            -> data/vocab/house_spelling.json + docs/data/house_spelling.json (+ Supabase words.house_spelling)
  python scripts/house_spelling.py --sample   -> prints 30 random rows for Medi's hand check (also written to data/whatsapp/house_sample_30.json)"""
import collections, io, json, random, re, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import Matcher, loose, fold, short, strip_pronoun, PRONOUNS
import whatsapp_chat as W

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'vocab' / 'house_spelling.json'
PUB = ROOT / 'docs' / 'data' / 'house_spelling.json'
MIN_SEEN = 2
TRUSTED = ('exact', 'fold', 'short')
_TOK = re.compile(r"[A-Za-z0-9'’]+(?:-[A-Za-z0-9'’]+)*")
GLUE = set(PRONOUNS) | {'u', 'w', 'wa', 'ya', 'el', 'al', 'il', 'fi', 'bi', 'min', 'ma3', '3ala', 'mish', 'mesh', 'ma', 'la', 'bas', 'aw', 'iza', 'lamma', 'lama', 'enno', 'inno', 'shu', 'ah', 'yes', 'no', 'or', 'not', 'a', 'the', 'and', 'p', 'f', 'm'}


def load_words():
    return json.load(io.open(ROOT / 'data' / 'vocab' / 'words.json', encoding='utf-8'))['items']


def tokens(line):
    """Her line -> candidate spans (1-3 tokens, longest first at each position). Keeps her exact letters (case folded only)."""
    toks = [t.strip("'’") for t in _TOK.findall(line)]
    toks = [t for t in toks if t and not re.fullmatch(r'\d+', t)]
    return toks


def _safe(form, tier, w):
    """A fold/short match is trusted only for forms of >= 4 letters whose length is within 1 of a Doc form ('oh' must never
    become the Doc word 'U'; 'a5u' (his brother) is not the Doc word 'A5'). Exact matches are always safe."""
    f = strip_pronoun(form)
    d = strip_pronoun(w['arabizi'])
    # the HEADWORD only: an alias (a feminine / plural / merged-duplicate form such as '5adra' under 'A5dar') is a real form of
    # the entry for matching, but it is not the entry's spelling
    if not (loose(f) == loose(d) or fold(f) == fold(d) or short(f) == short(d)):
        return False
    if tier == 'exact':
        return True
    return len(f) >= 4 and abs(len(d) - len(f)) <= 1


def _display(form, doc):
    """Her form, dressed like the Doc entry: the Doc's leading pronoun is kept when she dropped it; first letter follows the Doc."""
    d = doc.split()
    if len(d) > 1 and d[0].lower() in PRONOUNS and form.split()[0].lower() not in PRONOUNS:
        form = d[0] + ' ' + form
    if doc[:1].isupper() and form[:1].islower():
        form = form[0].upper() + form[1:]
    elif doc[:1].islower() and form[:1].isupper():
        form = form[0].lower() + form[1:]
    return form


def mine(words=None, lines=None, log=print):
    words = words or load_words()
    m = Matcher(words)
    wmap = {w['key']: w for w in words}
    if lines is None:
        lines = [(x['ts'], x['text']) for x in W.messages() if x['who'] == 'Amal' and x['kind'] in ('arabizi', 'gloss') and not x['deleted']]
    seen = collections.defaultdict(collections.Counter)      # key -> Counter(form)
    last = {}                                                # (key, form) -> last ts
    tiers = collections.Counter()
    unmatched = collections.Counter()
    n_tokens = 0
    for ts, text in lines:
        for piece in W._split_gloss(text):
            toks = tokens(piece)
            i = 0
            while i < len(toks):
                hit = None
                for span in (3, 2, 1):
                    if i + span > len(toks):
                        continue
                    form = ' '.join(toks[i:i + span])
                    if span == 1 and (form.lower() in GLUE or len(form) < 2):
                        break
                    mt = m.match_tier(form, fuzzy=False)
                    if mt and mt[1] in TRUSTED and _safe(form, mt[1], wmap[mt[0]]):
                        hit = (mt[0], form, span, mt[1]); break
                if hit:
                    k, form, span, tier = hit
                    seen[k][form] += 1; last[(k, form)] = ts; tiers[tier] += 1
                    i += span
                else:
                    if toks[i].lower() not in GLUE:
                        unmatched[toks[i]] += 1
                    i += 1
                n_tokens += 1
    table = {}
    for k, c in seen.items():
        top = c.most_common()
        n = top[0][1]
        if n < MIN_SEEN:
            continue
        tied = [f for f, cnt in top if cnt == n]
        best_raw = max(tied, key=lambda f: str(last[(k, f)])) if len(tied) > 1 else tied[0]
        best = _display(best_raw, wmap[k]['arabizi'])
        table[k] = {'house': best, 'n': sum(c.values()), 'forms': [{'form': f, 'n': cnt} for f, cnt in top[:4]],
                    'doc': wmap[k]['arabizi'], 'same_as_doc': best == wmap[k]['arabizi'],
                    'last_seen': str(last[(k, best_raw)])[:10]}
    stats = {'lines': len(lines), 'tokens': n_tokens, 'matched_spans': sum(tiers.values()), 'tiers': dict(tiers), 'words_with_house': len(table),
             'words_seen_once': sum(1 for c in seen.values() if sum(c.values()) < MIN_SEEN), 'doc_words': len(words),
             'differs_from_doc': sum(1 for v in table.values() if not v['same_as_doc']), 'unmatched_top': unmatched.most_common(40)}
    log(json.dumps({k: v for k, v in stats.items() if k != 'unmatched_top'}, ensure_ascii=False))
    return table, stats


def write(table, stats, to_db=True):
    OUT.parent.mkdir(parents=True, exist_ok=True); PUB.parent.mkdir(parents=True, exist_ok=True)
    doc = {'built': datetime.datetime.now().isoformat(timespec='seconds'), 'source': 'WhatsApp chat with Amal (private export, never published)',
           'rule': 'display = her most frequent form when seen >= 2 times; Doc spelling otherwise', 'stats': {k: v for k, v in stats.items() if k != 'unmatched_top'}, 'items': table}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({**doc, 'unmatched_top': stats['unmatched_top']}, ensure_ascii=False, indent=1))
    io.open(PUB, 'w', encoding='utf-8').write(json.dumps({**doc, 'items': {k: {'house': v['house'], 'n': v['n']} for k, v in table.items()}}, ensure_ascii=False))
    if to_db:
        import db
        rows = [{'key': k, 'house_spelling': v['house'], 'house_n': v['n']} for k, v in table.items()]
        for i in range(0, len(rows), 200):
            for r in rows[i:i + 200]:
                db.rest('PATCH', 'words', params={'key': f"eq.{r['key']}"}, body={'house_spelling': r['house_spelling'], 'house_n': r['house_n']}, prefer='return=minimal')
        return len(rows)
    return 0


def sample(table, n=30, seed=None):
    rng = random.Random(seed)
    keys = sorted(table)
    pick = rng.sample(keys, min(n, len(keys)))
    rows = [{'key': k, 'doc': table[k]['doc'], 'house': table[k]['house'], 'n': table[k]['n'], 'differs': not table[k]['same_as_doc']} for k in pick]
    io.open(ROOT / 'data' / 'whatsapp' / 'house_sample_30.json', 'w', encoding='utf-8').write(json.dumps(rows, ensure_ascii=False, indent=1))
    return rows


if __name__ == '__main__':
    table, stats = mine()
    if '--sample' in sys.argv:
        for r in sample(table, seed=int(datetime.date.today().strftime('%Y%m%d'))):
            print(f"{r['doc']:32} -> {r['house']:32} x{r['n']}  {'DIFF' if r['differs'] else ''}")
    else:
        n = write(table, stats, to_db='--no-db' not in sys.argv)
        print('wrote', len(table), 'house spellings; db rows', n)
        print('unmatched top:', stats['unmatched_top'][:25])
