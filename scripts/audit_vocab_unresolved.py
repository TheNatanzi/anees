# -*- coding: utf-8 -*-
"""Audit of Medi's unresolved / on-hold word events (Medi 2026-09-28: "can you do a full audit of these unresolved and
make sure they are being marked correctly so they aren't showing up in the reporting here?").

    python scripts/audit_vocab_unresolved.py            # rebuild the audit patches in docs/data/word-bank-review.json
    python scripts/audit_vocab_unresolved.py --dry-run  # print the counts, write nothing

Every Medi word event that is unresolved or on hold gets exactly one bin (written as additive overlay fields):

  audit_bin = not_counted  left out of the score on purpose, never "unresolved":
              echo | repeat | grammar | clarification | quote | not_this_word | form_not_on_list | filler | farsi
            = no_evidence  nothing in the recording can settle it: tutor_audio_missing | transcript_unclear
            = settled      a verdict (independent | helped | incorrect | recall_failure) under docs/word-bank-review-rules.md
            = open         needs Medi or Amal; audit_question says what to answer

Three rules also run over ALL of Medi's events, scored ones included (Medi 2026-09-28):
  farsi    a turn with >= 2 Persian signals (letters پ چ ژ گ ی ک, ZWNJ, Persian-only words / می+verb) is a side
           conversation, not the lesson ("this is farsi talking to my dad"). Turns with 1 signal are only listed.
  filler   و / u counts as "and" only when it joins two words; alone, turn-final, followed by uh/um/آآ, a cut-off or a
           restart it is a filler ("U means 'and' and I am using it as a filler").
  restart  the same word said again within 20 s with only a bare prompt from Amal in between (shu? / mm / aha / هاه؟)
           is one attempt: the later, fuller one is kept, the other is "Not counted: repeat".

Hand verdicts (read in full context, one line of evidence each) live in
data/lesson-work/vocab-unresolved-audit-2026-09-28.json. The raw evidence is never touched (S2): patches are
source-bound (`expected`), carry reviewer "Claude audit 2026-09-28", keep what they overwrote in `audit_prior`, and are
removed/restored on a re-run, so the script is idempotent and every verdict can be overturned.
Each verdict is also logged with scripts/decisions.py (who "Claude audit", channel "audit"), the run with scripts/track.py.
"""
import collections, copy, glob, hashlib, json, os, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
REVIEWER = 'Claude audit 2026-09-28'
VERSION = '2026-09-28-vocab-unresolved-audit'
EVIDENCE = ROOT / 'docs/data/word-bank-evidence.json'
REVIEW = ROOT / 'docs/data/word-bank-review.json'
VERDICTS = ROOT / 'data/lesson-work/vocab-unresolved-audit-2026-09-28.json'
SUMMARY = ROOT / 'data/lesson-work/vocab-unresolved-audit-2026-09-28.summary.json'
LESSONS = ROOT / 'docs/data/lessons'
KEYS = ['source_sha256', 'row_id', 'word_key', 'text', 't_start', 't_end']
ABSENT = '__absent__'
AUDIT_FIELDS = ('audit_by', 'audit_bin', 'audit_kind', 'audit_note', 'audit_question', 'audit_prior', 'audit_created', 'audit_run')
NOT_COUNTED = ('echo', 'repeat', 'duplicate', 'grammar', 'clarification', 'quote', 'not_this_word', 'form_not_on_list', 'filler', 'farsi')
SCORE = {'independent': 1, 'helped': .5, 'incorrect': 0, 'recall_failure': 0}
PREPOSITIONS = {'fi', 'ma3', 'min', '3an', '3ala', 'la', 'bi', 'bidUn', 'zaI', '3end', '2udAm', 'wara', 'bein', 'janb', 'foa2',
                'ta7t', 'bilnos', '2bAl', '7awalain', '7awAlain', '7awAli', 'juwa', 'bara', '2abel', 'ba3ed', 'beini u beinak',
                '3ala alyamIn'}                                   # word-bank-core.js PREPOSITIONS (grammar, not vocab)


def J(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------------ the overlay, exactly as word-bank-review.js applies it
def _js(v):
    """JSON.stringify equality: 237 == 237.0 (Python's json would print them differently)."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, dict):
        return {k: _js(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_js(x) for x in v]
    return v


def matches(e, expected):
    return all(json.dumps(_js(e.get(k)), ensure_ascii=False) == json.dumps(_js(v), ensure_ascii=False) for k, v in (expected or {}).items())


def reset(review):
    """Remove every patch this audit made (and restore the fields it overwrote), so a re-run starts clean."""
    removed = restored = 0
    for eid in list(review['patches']):
        c = review['patches'][eid]['changes']
        if c.get('audit_by') != REVIEWER:
            continue
        if c.get('audit_created'):
            del review['patches'][eid]
            removed += 1
            continue
        prior = c.get('audit_prior') or {}
        for k in AUDIT_FIELDS:
            c.pop(k, None)
        for k, v in prior.items():
            if v == ABSENT:
                c.pop(k, None)
            else:
                c[k] = v
        restored += 1
    return removed, restored


def view(raw, review):
    """{id: event as the Word Bank sees it} (patches applied when their source still matches)."""
    out = {}
    for e in raw:
        p = review['patches'].get(e['id'])
        out[e['id']] = {**e, **p['changes']} if p and matches(e, p['expected']) else dict(e)
    return out


def points(e):
    """word-bank-core.js points() for the speaking lane."""
    if e.get('word_key') in PREPOSITIONS:
        return None
    if any(e.get(k) for k in ('scored_in_event', 'observation_only', 'ignored', 'immediate_repeat', 'is_echo', 'grammar_only')):
        return None
    if e.get('classification') in ('grammar', 'ignored') or e.get('speaker') != 'Medi':
        return None
    if e.get('assessment') == 'unresolved' or e.get('needs_review') or e.get('wording_status') == 'unresolved':
        return None
    if e.get('vocab_points') in (0, .5, 1):
        return e['vocab_points']
    if (e.get('correction') or e.get('human_correction')) and not e.get('classification'):
        return None
    return SCORE.get(e.get('assessment'))


def unknown(e):
    """vocab-unknowns.js: an event the report lists as unresolved / on hold."""
    return e.get('speaker') == 'Medi' and e.get('word_key') not in PREPOSITIONS and (e.get('assessment') == 'unresolved' or bool(e.get('needs_review')))


def bucket(e):
    """Python twin of vocab-unknowns.js bucket(): the report's reason group."""
    r = str(e.get('reason') or '')
    if e.get('needs_review') and e.get('assessment') != 'unresolved':
        return 'hold'
    for pat, b in ((r'^Isolated production', 'isolated'), (r'^Tutor cue/repetition', 'cue'), (r'^Source-bound historical', 'old'),
                   (r'^Legacy match', 'legacy'), (r'^Ambiguous vocabulary', 'wording')):
        if re.search(pat, r, re.I):
            return b
    if re.search(r'tutor (recording|track|transcript)[^.]*(unavailable|missing)|missing tutor|lacks the tutor recording|tutor context (is |for the interval is )?(unavailable|missing)|microphone', r, re.I):
        return 'noamal'
    if e.get('immediate_repeat') or e.get('is_echo') or e.get('scored_in_event') or re.search(r'\b(repeat|repeats|repeated|repetition|restates?|restart|rehears|continuation|echo)', r, re.I):
        return 'repeat'
    if re.search(r'homograph|false (binding|start|lexical|noun)|wrong catalog meaning|different meaning|not the |rebind|detach|\bASR\b|hallucinat|fragment|transcri', r, re.I):
        return 'wrongword'
    if re.search(r'clarification', r, re.I):
        return 'clar'
    if re.search(r'grammar|agreement|conjugat|tense|person|pronoun|possessive|morpholog|null', r, re.I):
        return 'grammar'
    if re.search(r'wording|ambiguous|unclear', r, re.I):
        return 'wording'
    return 'other'


# ------------------------------------------------------------------ text helpers
AR = re.compile(r'[؀-ۿ]')
HES = {'uh', 'um', 'umm', 'uhm', 'hmm', 'hm', 'mm', 'mmm', 'er', 'erm', 'eh', 'ah', 'oh', 'آ', 'آآ', 'آآآ', 'اه', 'آه', 'أه', 'ااا',
       'مم', 'ممم', 'أمم', 'امم', 'آمم', 'آآمم', 'آآآم', 'آآآمم', 'اممم', 'أممم', 'um-', 'uh-'}
AND = {'و', 'u', 'w', 'wa'}
AND_LONG = re.compile(r'^و{2,}$|^u{2,}$', re.I)


def fold(s):
    s = unicodedata.normalize('NFKC', str(s or ''))
    s = re.sub(r'[ً-ٰٟـ]', '', s)
    return s.replace('ی', 'ي').replace('ک', 'ك').replace('ى', 'ي').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').lower()


def bare(tok):
    return re.sub(r'^[\s"“”«»()\[\].,،؛;:!?؟…-]+|[\s"“”«»()\[\].,،؛;:!?؟…-]+$', '', tok)


def hesitation(tok):
    b = bare(tok).lower()
    return (not b) or b in HES or bool(re.fullmatch(r'[آا]+[مه]*|م{2,}|u+h+|u+m+|h+m+|a+h+', b))


def own_row(e):
    return next((r for r in e.get('context') or [] if r['row_id'] == e['row_id'] and r['speaker'] == e['speaker']), None)


def merged_turn(e, gap=2.5):
    """Medi's contiguous rows around the event (evidence context), as (tokens, index of the own row's first token)."""
    rows = sorted((r for r in e.get('context') or [] if r.get('timeline_start') is not None), key=lambda r: r['timeline_start'])
    i = next((k for k, r in enumerate(rows) if r['row_id'] == e['row_id'] and r['speaker'] == e['speaker']), None)
    if i is None:
        r = own_row(e)
        return (r['text'].split() if r else str(e.get('text') or '').split()), 0
    a = i
    while a > 0 and rows[a - 1]['speaker'] == e['speaker'] and rows[a]['timeline_start'] - (rows[a - 1].get('timeline_end') or rows[a - 1]['timeline_start']) <= gap:
        a -= 1
    b = i
    while b + 1 < len(rows) and rows[b + 1]['speaker'] == e['speaker'] and rows[b + 1]['timeline_start'] - (rows[b].get('timeline_end') or rows[b]['timeline_start']) <= gap:
        b += 1
    toks, start = [], 0
    for k in range(a, b + 1):
        if k == i:
            start = len(toks)
        toks += str(rows[k].get('text') or '').split()
    return toks, start


# ------------------------------------------------------------------ rule 1: Farsi side conversation
FA_LETTERS = {'پ': 'pe', 'چ': 'che', 'ژ': 'zhe', 'گ': 'gaf', 'ی': 'fa_ye', 'ک': 'fa_kaf', '‌': 'zwnj'}
# Persian-only function words and verb forms. Words that are also everyday Levantine/MSA (من ما هم با به تو ده الان خوب مي ...)
# are deliberately left out so an Arabic line never scores on them.
FA_WORDS = {fold(w) for w in (
    'رو', 'است', 'هست', 'نیست', 'این', 'اون', 'بیرون', 'پنجره', 'خیلی', 'چی', 'کجا', 'چرا', 'چطور', 'روشنه', 'خاموش',
    'دارم', 'داری', 'برو', 'بیا', 'بکن', 'باشه', 'چیه', 'کیه', 'اینجا', 'اونجا', 'دیروز', 'فردا', 'بابا', 'مامان', 'ولی',
    'چون', 'خوبه', 'رسیده', 'بندی', 'ببند', 'جان', 'جون', 'میرم', 'میری', 'میره', 'میام', 'میاد', 'میخوام', 'میخوای', 'میکنم',
    'میکنی', 'میکنه', 'میگم', 'میگی', 'میگه', 'میدونم', 'نمیدونم', 'میشه', 'نمیشه', 'بشین', 'بخور', 'بریم', 'کردم', 'کردی',
    'رفتم', 'اومدم', 'بگو', 'ببین', 'نکن', 'خونه', 'یکی', 'هفتاد')}
MI_VERB = re.compile(r'(?:^|[\s،,.])ن?مي[\s‌][؀-ۿ]{2,}')


def farsi_signals(text):
    t = str(text or '')
    sig = {n for ch, n in FA_LETTERS.items() if ch in t}
    for w in re.findall(r'[؀-ۿ‌]+', t):
        if fold(w) in FA_WORDS:
            sig.add('w:' + fold(w))
    if MI_VERB.search(fold(t)):
        sig.add('mi+verb')
    return sig


def page_turns():
    out = {}
    for f in sorted(glob.glob(str(LESSONS / '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].json'))):
        d = os.path.basename(f)[:10]
        T = J(f)['turns']
        for k, t in enumerate(T):
            t['_end'] = t.get('end') or (T[k + 1]['t'] if k + 1 < len(T) else t['t'] + 5)
        out[d] = T
    return out


def farsi_turns(pages, raw):
    """Page turns and evidence turns with >= 2 Persian signals, plus the 1-signal borderline ones (listed, not used)."""
    hits, border = [], []
    for d, T in pages.items():
        for t in T:
            s = farsi_signals(t.get('text'))
            row = {'date': d, 'who': t.get('who'), 't': round(t['t'], 2), 'end': round(t['_end'], 2), 'signals': sorted(s), 'source': 'lesson page'}
            (hits if len(s) >= 2 else border if len(s) == 1 else [None]).append(row) if s else None
    rows = {}
    for e in raw:
        for r in e.get('context') or []:
            rows.setdefault((e['lesson_date'], r['row_id']), {**r, 'date': e['lesson_date']})
    by = collections.defaultdict(list)
    for r in rows.values():
        by[r['date']].append(r)
    ev_hits = []
    for d, rs in by.items():
        rs.sort(key=lambda r: r.get('timeline_start') or 0)
        cur = None
        turns = []
        for r in rs:
            if cur and cur['who'] == r['speaker'] and (r.get('timeline_start') or 0) - cur['end'] <= 2.5:
                cur['text'] += ' ' + r['text']
                cur['end'] = r.get('timeline_end') or cur['end']
                cur['rows'].append(r['row_id'])
            else:
                cur = {'date': d, 'who': r['speaker'], 't': r.get('timeline_start') or 0, 'end': r.get('timeline_end') or 0,
                       'text': r['text'], 'rows': [r['row_id']]}
                turns.append(cur)
        for t in turns:
            s = farsi_signals(t['text'])
            if len(s) >= 2:
                ev_hits.append({**t, 'signals': sorted(s)})
    return hits, border, ev_hits


def in_farsi(e, hits, ev_hits):
    for h in hits:
        if h['date'] == e['lesson_date'] and h['who'] == e['speaker'] and h['t'] - .3 <= (e.get('t_start') or -1) <= h['end'] + .3:
            return h
    for h in ev_hits:
        if h['date'] == e['lesson_date'] and e['row_id'] in h['rows']:
            return h
    return None


# ------------------------------------------------------------------ rule 2: و / u as a filler
def and_occurrence(e, siblings):
    """(tokens, index) of the و this event stands for inside Medi's merged turn, or (tokens, None)."""
    toks, start = merged_turn(e)
    r = own_row(e)
    own = str(r['text'] if r else e.get('text') or '').split()
    idx = [k for k, t in enumerate(own) if bare(t).lower() in AND or AND_LONG.match(bare(t))]
    if not idx:
        return toks, None
    rank = [s['id'] for s in sorted(siblings, key=lambda s: (s.get('t_start') or 0, s['id']))].index(e['id'])
    return toks, start + idx[min(rank, len(idx) - 1)]


def filler_and(toks, j):
    """True when the و at toks[j] does not join two words (Medi's rule); None when it cannot be located."""
    if j is None:
        return None
    tok = toks[j]
    if AND_LONG.match(bare(tok)):
        return True                                            # a drawn-out ووو / uuu is hesitation
    if re.search(r'[،,.…?؟!]|-$', tok.replace(bare(tok), '', 1)) or tok.endswith('-'):
        return True                                            # و، / و. / و-- : a pause or cut-off right after it
    if j + 1 >= len(toks):
        return True                                            # ends the turn
    nxt = toks[j + 1]
    if hesitation(nxt) or nxt.endswith('-') or bare(nxt).lower() in AND:
        return True                                            # followed by uh/um/آآ, a cut-off word or a restart و
    return False


# ------------------------------------------------------------------ rule 3: restart across a bare prompt
BARE = re.compile(r'^(?:(?:shu|what|huh|ha|hah|mm+|mhm|mm-hmm|mhmm|uh-huh|aha|ah|oh|yes|yeah|yep|aywa|na3am|okay|ok|sorry|شو|هاه|ها|هه|مم+|ممم|أمم|امم|اه|آه|أه|أها|اها|أيوه|ايوه|أيوا|ايوا|نعم|أوكي|اوكي|صح)[\s?.!،,؟…]*)+$', re.I)


def bare_prompt(text):
    t = re.sub(r'\[[^\]]*\]', ' ', str(text or '')).strip()
    return bool(t) and bool(BARE.match(t))


def arabic_len(e):
    r = own_row(e)
    return len([w for w in str(r['text'] if r else e.get('text') or '').split() if AR.search(w) or re.match(r'^[a-z0-9\']{2,}$', bare(w).lower())])


# ------------------------------------------------------------------ rule 4: one attempt per word per utterance; rule 5: duplicate records
def utterances(pages, gap=3.0):
    """{date: [(start, end, chain id)]}: Medi's lesson-page segments chained while the pause is <= gap s and nobody else speaks."""
    out = {}
    for d, T in pages.items():
        segs, cid, last = [], -1, None
        for t in T:
            who = t.get('who')
            if who == 'chat':
                continue
            if who != 'Medi':
                last = None
                continue
            if last is None or t['t'] - last > gap:
                cid += 1
            segs.append((t['t'], t['_end'], f'{d}#{cid}'))
            last = t['_end']
        out[d] = segs
    return out


def utterance_of(e, utt):
    ts = e.get('t_start')
    for a, b, cid in utt.get(e['lesson_date'], []):
        if a - 1.0 <= ts <= b + 1.0:
            return cid
    return 'row:' + str(e.get('row_id'))


def overlapping(a, b):
    ea, eb = a.get('t_end') or a['t_start'], b.get('t_end') or b['t_start']
    return a['t_start'] < eb - 0.05 and b['t_start'] < ea - 0.05 and a['row_id'] != b['row_id']


def _group(view_):
    g = collections.defaultdict(list)
    for e in view_.values():
        if e['speaker'] == 'Medi' and e.get('word_key') and e['word_key'] not in PREPOSITIONS and e.get('t_start') is not None:
            g[(e['lesson_date'], e['word_key'])].append(e)
    for L in g.values():
        L.sort(key=lambda e: (e['t_start'], e['id']))
    return g


def mmss(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'


# ------------------------------------------------------------------ patch building
def fields_for(bin_, kind, e, note, extra=None, question=None):
    c = {'audit_by': REVIEWER, 'reviewer': REVIEWER, 'audit_run': VERSION, 'audit_bin': bin_, 'audit_kind': kind,
         'audit_note': note, 'contextual_audit': True, 'review_locked': True}
    if bin_ == 'settled':
        c.update(assessment=kind, vocab_points=SCORE[kind], ignored=False, needs_review=False, immediate_repeat=False,
                 is_echo=False, grammar_only=False, observation_only=False, scored_in_event=None, classification='lexical',
                 reason=f'{REVIEWER}: {note}')
        if e.get('wording_status') == 'unresolved':
            c['wording_status'] = 'context_reviewed'
        if kind in ('incorrect', 'recall_failure'):
            c['wrong_parts'] = [bare(str(e.get('text') or ''))]
    elif bin_ == 'not_counted':
        c.update(assessment='unresolved', vocab_points=None, needs_review=False, reason=f'{REVIEWER}: {note}')
        if kind == 'form_not_on_list':
            c.update(observation_only=True, ignored=False, classification='lexical')
        else:
            c.update(ignored=True)
            if kind == 'echo':
                c.update(is_echo=True, immediate_repeat=True, classification='ignored')
            elif kind in ('repeat', 'duplicate'):
                c.update(immediate_repeat=True, classification='ignored')
            elif kind == 'grammar':
                c.update(grammar_only=True, classification='grammar')
            else:
                c.update(classification='ignored')
    elif bin_ == 'no_evidence':
        c.update(assessment='unresolved', vocab_points=None, needs_review=False, ignored=True, classification='ignored',
                 reason=f'{REVIEWER}: {note}')
    elif bin_ == 'open':
        c.update(audit_question=question)
        c.pop('review_locked')
    for k, v in (extra or {}).items():
        c[k] = v
    return c


def put(review, raw_e, changes):
    p = review['patches'].get(raw_e['id'])
    if p is None:
        exp = {k: raw_e.get(k) for k in KEYS + ['assessment', 'reason']}
        review['patches'][raw_e['id']] = {'expected': exp, 'changes': {**changes, 'audit_created': True}}
        return
    c = p['changes']
    prior = {k: (c[k] if k in c else ABSENT) for k in changes if k not in AUDIT_FIELDS}
    c.update(changes)
    c['audit_prior'] = prior


# ------------------------------------------------------------------ main
def audit(raw_doc, review, verdicts, pages):
    raw = raw_doc['events']
    by_id = {e['id']: e for e in raw}
    removed, restored = reset(review)
    V0 = view(raw, review)                                        # the Word Bank before this audit
    medi = [e for e in V0.values() if e['speaker'] == 'Medi']
    plan = {}                                                     # id -> (bin, kind, note, extra, question, source)
    log = collections.Counter()

    # rule 1 - Farsi turns
    hits, border, ev_hits = farsi_turns(pages, raw)
    for e in medi:
        h = in_farsi(e, hits, ev_hits)
        if h:
            plan[e['id']] = ('not_counted', 'farsi', 'Farsi side conversation (not the lesson).', None, None, 'rule:farsi')

    # rule 2 - و as a filler (every و event, scored or not)
    by_row = collections.defaultdict(list)
    for e in medi:
        if e.get('word_key') == 'u':
            by_row[(e['lesson_date'], e['row_id'])].append(e)
    and_stats = collections.Counter()
    filler_list = []
    for e in medi:
        if e.get('word_key') != 'u' or e['id'] in plan:
            continue
        toks, j = and_occurrence(e, by_row[(e['lesson_date'], e['row_id'])])
        f = filler_and(toks, j)
        and_stats['located' if f is not None else 'not_located'] += 1
        if f:
            ctx = ' '.join(toks[max(0, j - 3):j + 3])
            plan[e['id']] = ('not_counted', 'filler', f'«{ctx}»: و here holds the floor (alone, turn-final, or before uh/um/a cut-off/restart); it does not join two words.', None, None, 'rule:filler')
            filler_list.append((e['id'], points(e)))
            and_stats['filler'] += 1
        elif f is False:
            and_stats['real_and'] += 1

    # hand verdicts (read in context)
    for eid, v in verdicts['verdicts'].items():
        if eid in plan:
            log['hand_verdict_overridden_by_' + plan[eid][5]] += 1
            continue
        plan[eid] = (v['bin'], v['kind'], v.get('note'), v.get('set'), v.get('question'), 'hand')

    # mechanical bins for the rest of the unresolved / on-hold events
    SEP18 = ('Sep 18 was recorded as one mixed track and its speakers are machine-estimated; the standing rule holds every '
             'Sep 18 score until a person confirms the speaker. Is this line Medi\'s?')
    for e in medi:
        if e['id'] in plan or not unknown(e):
            continue
        b = bucket(e)
        r = str(e.get('reason') or '')
        flagged = any(e.get(k) for k in ('immediate_repeat', 'is_echo', 'scored_in_event', 'grammar_only', 'observation_only', 'ignored'))
        if e.get('needs_review') and ('-meet-' in str(e.get('source_id')) or 'estimate' in str(e.get('speaker_basis'))):
            plan[e['id']] = ('open', 'question', None, None, SEP18, 'mech:sep18')
        elif e.get('needs_review') and r.startswith('Heard form does not match any form'):
            plan[e['id']] = ('not_counted', 'form_not_on_list', 'The form he said (e.g. the I-form after بدي/لازم) is not one of the forms on Amal\'s list for this word; kept as an observation, not scored.', None, None, 'mech:form')
        elif b == 'noamal' and not any(t.get('who') == 'Amal' and e['t_start'] - 60 <= t['t'] <= e['t_start'] + 10 for t in pages.get(e['lesson_date'], [])):
            plan[e['id']] = ('no_evidence', 'tutor_audio_missing', 'Amal\'s track is missing for this stretch, so nobody can tell whether she prompted him (rule 11).', None, None, 'mech:noamal')
        elif flagged and not e.get('needs_review'):
            kind = {'grammar': 'grammar', 'clar': 'clarification', 'wrongword': 'not_this_word'}.get(b)
            if b == 'repeat' or kind is None:
                if e.get('grammar_only'):
                    kind = 'grammar'
                elif e.get('observation_only'):
                    kind = 'form_not_on_list'
                elif re.search(r'\bquot|reading|reads? |explain|discuss', r, re.I) and not re.search(r'repeat|echo', r, re.I):
                    kind = 'quote'
                elif e.get('is_echo') or re.search(r'\b(tutor|amal|supplied|echo|model)', r, re.I):
                    kind = 'echo'
                elif b == 'repeat' or e.get('immediate_repeat') or e.get('scored_in_event') or re.search(r'repeat|restart|same (sentence|utterance)|false start|abandon', r, re.I):
                    kind = 'repeat'
                elif re.search(r'grammar|agreement|tense|person|preposition|construction', r, re.I):
                    kind = 'grammar'
                else:
                    kind = 'not_this_word'
            plan[e['id']] = ('not_counted', kind, 'Already left out by an earlier review: ' + r, None, None, 'mech:flagged')
        else:
            plan[e['id']] = ('open', 'question', None, None, 'Not classified by the audit: ' + r, 'mech:unclassified')
            log['unclassified'] += 1

    # rule 3 - restart across a bare prompt (over the view after the plan)
    def planned(e):
        p = plan.get(e['id'])
        if not p:
            return e
        c = fields_for(p[0], p[1], by_id.get(e['id'], e), p[2] or '', p[3], p[4])
        return {**e, **c}
    V1 = {i: planned(e) for i, e in V0.items()}
    restarts = []
    groups = collections.defaultdict(list)
    for e in V1.values():
        if e['speaker'] == 'Medi' and e.get('word_key') and points(e) is not None:
            groups[(e['lesson_date'], e['word_key'])].append(e)
    for (d, k), L in groups.items():
        L.sort(key=lambda e: e['t_start'])
        for a, b in zip(L, L[1:]):
            if a['row_id'] == b['row_id'] or not (0 < b['t_start'] - a['t_start'] <= 20):
                continue
            between = [t for t in pages.get(d, []) if t.get('who') == 'Amal' and (a.get('t_end') or a['t_start']) < t['t'] < b['t_start']]
            if not between or not all(bare_prompt(t['text']) for t in between):
                continue
            keep, drop = (b, a) if arabic_len(b) >= arabic_len(a) else (a, b)
            if drop['id'] in plan and plan[drop['id']][5] == 'hand' and plan[drop['id']][0] == 'settled':
                log['restart_overrode_hand_settled'] += 1
            prompt = ' / '.join(t['text'] for t in between)
            plan[drop['id']] = ('not_counted', 'repeat', f'Said again at {int(keep["t_start"]//60)}:{int(keep["t_start"]%60):02d} after only «{prompt}» from Amal: one attempt, the fuller one is kept.', None, None, 'rule:restart')
            restarts.append((drop['id'], keep['id'], points(V0[drop['id']])))

    # rule 5 - duplicate records: same word, overlapping time windows, different source rows (two evidence passes).
    # Keep the most specific one (a hand verdict, else a scored one, else the one with the longer reason).
    V1 = {i: planned(e) for i, e in V0.items()}
    dups = []
    for (d, k), L in _group(V1).items():
        for i, a in enumerate(L):
            for b in L[i + 1:]:
                if b['t_start'] - a['t_start'] > 3:
                    break
                if not overlapping(a, b):
                    continue
                rank = lambda x: (plan.get(x['id'], (0,) * 6)[5] == 'hand', points(x) is not None, len(str(x.get('reason') or '')))
                keep, drop = (a, b) if rank(a) >= rank(b) else (b, a)
                plan[drop['id']] = ('not_counted', 'duplicate', f'Duplicate record of the same spoken word; judged once on the {mmss(keep["t_start"])} record.', None, None, 'rule:duplicate')
                dups.append((drop['id'], keep['id']))

    # rule 4 - the same word again inside one Medi utterance (stutter / self-restart: "shu. uh, shu", "X-- X") = one attempt.
    # Occurrences <= 10 s apart in one utterance form a cluster; the last scored one is kept (else the last one).
    V1 = {i: planned(e) for i, e in V0.items()}
    utt = utterances(pages)
    stutters = []
    for (d, k), L in _group(V1).items():
        L = [e for e in L if not (plan.get(e['id']) and plan[e['id']][1] in ('farsi', 'filler', 'duplicate'))]
        clusters, cur = [], []
        for e in L:
            if cur and (utterance_of(e, utt) != utterance_of(cur[-1], utt) or e['t_start'] - cur[-1]['t_start'] > 10):
                clusters.append(cur)
                cur = []
            cur.append(e)
        if cur:
            clusters.append(cur)
        for c in clusters:
            if len(c) < 2:
                continue
            scored = [e for e in c if points(e) is not None]
            keep = scored[-1] if scored else c[-1]
            for e in c:
                if e is keep:
                    continue
                p = plan.get(e['id'])
                if p and p[0] == 'not_counted' and p[1] != 'repeat' and points(e) is None:
                    continue                                   # already out for its own reason (echo, grammar, ...)
                if points(e) is None and not unknown(V0[e['id']]) and not p:
                    continue                                   # an older review already left it out; nothing to change
                if p and p[5] == 'hand' and p[0] == 'settled':
                    log['stutter_overrode_hand_settled'] += 1
                plan[e['id']] = ('not_counted', 'repeat', f'Same word again in one utterance (stutter or restart); one attempt, kept at {mmss(keep["t_start"])}.', None, None, 'rule:stutter')
                stutters.append((e['id'], keep['id'], points(e)))

    # write the patches
    for eid, (bin_, kind, note, extra, question, src) in plan.items():
        raw_e = by_id.get(eid)
        if raw_e is None:
            log['skipped_not_in_evidence'] += 1
            continue
        put(review, raw_e, fields_for(bin_, kind, raw_e, note or '', extra, question))
    V2 = view(raw, review)
    return {'plan': plan, 'V0': V0, 'V2': V2, 'reset': (removed, restored), 'log': log, 'farsi': (hits, border, ev_hits),
            'and_stats': and_stats, 'filler_list': filler_list, 'restarts': restarts, 'stutters': stutters, 'dups': dups}


def leaks(hits):
    """Where the Farsi turns also leak (reported, not edited): ladder units, grammar uses, lessons.json minutes."""
    out = []
    G = J(ROOT / 'docs/data/grammar-usage.json')
    for h in hits:
        d, a, b = h['date'], h['t'] - 1, h['end'] + 1
        lad = ROOT / f'docs/data/sentence-ladder/{d}.json'
        speak = listen = []
        if lad.exists():
            L = J(lad)
            speak = [u['id'] for u in L.get('speak', []) if u['t'] <= b and (u.get('end') or u['t']) >= a]
            listen = [u['id'] for u in L.get('listen', []) if u['t'] <= b + 15 and (u.get('end') or u['t']) >= a - 15 and u.get('reply') and farsi_signals(json.dumps(u.get('reply'), ensure_ascii=False))]
        g = [f"{k}@{u['mmss']}" for k, L in G['uses'].items() for u in L if u.get('date') == d and a - 1 <= u.get('t', -1) <= b + 1]
        out.append({'date': d, 'from': round(h['t'], 1), 'to': round(h['end'], 1), 'who': h['who'], 'secs': round(h['end'] - h['t'], 1),
                    'ladder_speak': speak, 'ladder_listen': listen, 'grammar_uses': g})
    return out


def clip_check():
    """Which recording each Medi event would play on the report (the word-bank.js / vocab-unknowns.js clip binding), and
    whether that file exists under docs/. Reported only; nothing is re-cut."""
    ev = J(EVIDENCE)['events']
    clips = J(ROOT / 'docs/data/word-bank-clips.json')['clips']
    fin = lambda x: isinstance(x, (int, float))
    per = collections.defaultdict(collections.Counter)
    missing = []
    for e in ev:
        if e['speaker'] != 'Medi':
            continue
        c = clips.get(e['id'])
        bound = bool(c) and c['source_sha256'] == e['source_sha256'] and c['lesson'] == e['lesson_date'] and c['start'] <= e['t_start'] \
            and c['end'] >= e['t_end'] and all(fin(r.get('timeline_start')) and fin(r.get('timeline_end')) and r['timeline_start'] >= c['start']
                                               and r['timeline_end'] <= c['end'] for r in e.get('context') or [])
        src = c['sentence_audio_url'] if bound else e.get('audio_url')
        ok = bool(src) and bool(re.match(r'^lessons/\d{4}-\d{2}-\d{2}/(?:audio/(?:Medi|Amal)\.mp3|clips/[A-Za-z0-9_.-]+\.mp3)$', src)) \
            and (ROOT / 'docs' / src).exists()
        k = 'clip ok' if bound and ok else 'track ok' if ok else 'no file' if src else 'no recording'
        per[e['lesson_date']][k] += 1
        if k in ('no file', 'no recording'):
            missing.append({'id': e['id'], 'date': e['lesson_date'], 't': round(e['t_start'], 1), 'word_key': e.get('word_key'),
                            'src': src, 'clip_in_index': bool(c), 'clip_bound': bound})
    return {'per_lesson': {d: dict(v) for d, v in sorted(per.items())}, 'missing': missing}


def main(argv):
    dry = '--dry-run' in argv
    raw_doc, review, verdicts = J(EVIDENCE), J(REVIEW), J(VERDICTS)
    pages = page_turns()
    R = audit(raw_doc, review, verdicts, pages)
    plan, V0, V2 = R['plan'], R['V0'], R['V2']
    before = [e for e in V0.values() if unknown(e)]
    bins = collections.Counter((p[0], p[1]) for i, p in plan.items() if V0.get(i, {}).get('speaker') == 'Medi')
    moved_scored = [i for i, p in plan.items() if points(V0[i]) is not None and points(V2[i]) is None]
    newly_scored = [i for i, p in plan.items() if points(V0[i]) is None and points(V2[i]) is not None]
    hits, border, ev_hits = R['farsi']
    summary = {
        'reviewer': REVIEWER, 'version': VERSION,
        'before': {'medi_events_report': sum(1 for e in V0.values() if e['speaker'] == 'Medi' and e.get('word_key') not in PREPOSITIONS),
                   'unresolved_or_on_hold': len(before),
                   'by_report_group': dict(collections.Counter(bucket(e) for e in before))},
        'after': {'still_unresolved_or_on_hold_raw_flag': sum(1 for e in V2.values() if unknown(e)),
                  'genuinely_open': sum(1 for e in V2.values() if unknown(e) and e.get('audit_bin') not in ('not_counted', 'no_evidence', 'settled')),
                  'bins': {f'{a}:{b}': n for (a, b), n in sorted(bins.items())}},
        'audited_events': len(plan), 'sources': dict(collections.Counter(p[5] for p in plan.values())),
        'scored_events_now_not_counted': len(moved_scored), 'unscored_events_now_scored': len(newly_scored),
        'rules': {'farsi_turns': [{k: h[k] for k in ('date', 't', 'end', 'who', 'signals')} for h in hits],
                  'farsi_evidence_turns': [{'date': h['date'], 't': round(h['t'], 2), 'who': h['who'], 'signals': h['signals']} for h in ev_hits],
                  'farsi_borderline_turns_not_used': border,
                  'farsi_events': sum(1 for p in plan.values() if p[1] == 'farsi'),
                  'and_events': dict(R['and_stats']), 'and_fillers_that_were_scored': sum(1 for _, p in R['filler_list'] if p is not None),
                  'restart_pairs': len(R['restarts']), 'restart_drops_that_were_scored': sum(1 for *_, p in R['restarts'] if p is not None),
                  'stutter_events_collapsed': len(R['stutters']), 'stutter_drops_that_were_scored': sum(1 for *_, p in R['stutters'] if p is not None),
                  'duplicate_records': len(R['dups'])},
        'clips': clip_check(),
        'farsi_leaks': leaks(hits), 'log': dict(R['log']), 'reset': {'removed': R['reset'][0], 'restored': R['reset'][1]},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if dry:
        return summary
    import track, decisions
    with track.run('vocab_unresolved_audit', kind='build', inputs=[str(EVIDENCE), str(REVIEW), str(VERDICTS)],
                   outputs=[str(REVIEW), str(SUMMARY)], params={'reviewer': REVIEWER, 'version': VERSION}) as run:
        review['version'] = re.sub(r'\+vocab-unresolved-audit-0928$', '', review.get('version', '')) + '+vocab-unresolved-audit-0928'
        REVIEW.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        known = decisions.known_ids()
        n = 0
        for eid, (bin_, kind, note, extra, question, src) in plan.items():
            e0 = V0.get(eid)
            if not e0:
                continue
            did = 'd-audit0928-' + hashlib.sha256(f'{eid}|{bin_}|{kind}'.encode()).hexdigest()[:20]
            if did in known:
                continue
            decisions.record(who='Claude audit', channel='audit', about_type='word', about_id=eid, decision_id=did,
                             ts='2026-09-28T12:00:00Z', ai_value=e0.get('assessment'), answer=bin_, corrected_value=kind,
                             reason=src, source_row={'table': 'docs/data/word-bank-review.json', 'id': eid})
            n += 1
        run.set(metrics={'audited': len(plan), 'decisions_written': n, 'before_unresolved': len(before),
                         'after_open': summary['after']['genuinely_open']})
    return summary


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
