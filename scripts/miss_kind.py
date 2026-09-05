"""Miss classifier (M9): was a possible miss a WORD problem or a GRAMMAR slip (article el / gender / tense / plural) or pronunciation?

Three signals, in order of trust:
  3. Amal's own tap on the after-lesson link ("Wrong word" / "Wrong grammar") -> stored by apply_rules, always wins
  2. the form Medi said vs the Doc form (الأكتر vs أكتر = extra ال -> article; ة/ه ending swap -> gender; plural suffix -> plural)
  1. Amal's words in the 8 s after (No أل / "the" -> article; feminine / masculine -> gender; past / present -> tense; plural -> plural;
     pronounce / say it -> pronunciation; means / how do you say -> word)
When the rules stay 'unclear' and Amal explained in English (>= 8 English words), an optional model call (gpt-5.5, through the
budget ledger, <= 10 per lesson) decides; otherwise the kind stays 'unclear' and the page says so (never a guessed tag)."""
import io, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import ARABIC, arabic_norm

GRAMMAR_KINDS = ('article', 'gender', 'tense', 'plural')
KINDS = ('word', 'article', 'gender', 'tense', 'plural', 'pronunciation', 'unclear')
CUES = {
    'article': ('أل', 'ال ', 'الـ', ' el ', ' el-', ' al ', 'the el', 'article', 'definite', 'no al', 'no el', 'without el', 'without al', 'بدون ال'),
    'gender': ('feminine', 'masculine', 'female', 'male', 'for a girl', 'for a boy', 'مؤنث', 'مذكر', 'تاء', 'she is', 'he is'),
    'tense': ('past', 'present', 'future', 'tense', 'command', 'ماضي', 'مضارع', 'أمر', 'conjugat', 'i did', 'you did'),
    'plural': ('plural', 'singular', 'جمع', 'مفرد', 'one of them', 'many of them'),
    'pronunciation': ('pronounc', 'pronunciation', 'say it like', 'the sound', 'heavy', 'soft', 'from the throat', 'ط', 'ح', 'ع', 'ق', 'صوت'),
    'word': ('means', 'meaning', 'how do you say', 'what is', "what's", 'in arabic', 'the word', 'vocab', 'يعني', 'شو معنى', 'الكلمة', 'different word', 'another word'),
}
MAX_LLM_PER_LESSON = 10


def _strip_al(s):
    return s[2:] if s.startswith('ال') and len(s) > 3 else s


def form_diff(said, doc_arabic, doc_plural=''):
    """Compare Medi's spoken Arabic form with the Doc form. Returns (kind or None, why)."""
    said_ar = [t for t in re.findall(r'[؀-ۿ]+', said or '')]
    if not said_ar or not doc_arabic:
        return None, ''
    doc = arabic_norm(doc_arabic.split('/')[0])
    for tok in said_ar:
        s = arabic_norm(tok)
        if s == doc:
            return 'same', 'same form as the Doc'
        if s.startswith('ال') and _strip_al(s) == _strip_al(doc) and not doc.startswith('ال'):
            return 'article', f'said {tok}, Doc has {doc_arabic} (extra ال)'
        if doc.startswith('ال') and s == _strip_al(doc):
            return 'article', f'said {tok}, Doc has {doc_arabic} (missing ال)'
        if s.rstrip('هة') == doc.rstrip('هة') and s != doc and (s.endswith(('ه', 'ة')) != doc.endswith(('ه', 'ة'))):
            return 'gender', f'said {tok}, Doc has {doc_arabic} (feminine ending)'
        if doc_plural and s == arabic_norm(doc_plural.split('/')[0]):
            return 'plural', f'said the plural {tok}, Doc singular {doc_arabic}'
        if s.endswith(('ات', 'ين', 'ون')) and doc == s[:-2]:
            return 'plural', f'said {tok}, Doc singular {doc_arabic}'
        if doc.endswith(('ات', 'ين', 'ون')) and s == doc[:-2]:
            return 'plural', f'said singular {tok}, Doc plural {doc_arabic}'
    return 'other', f'said {said_ar[0]}, Doc has {doc_arabic}'


def cue_kind(tutor_text):
    """Grammar / word cue in what Amal said right after. Returns (kind or None, matched cue)."""
    t = ' ' + (tutor_text or '').lower() + ' '
    for kind in ('article', 'gender', 'tense', 'plural', 'pronunciation', 'word'):
        for c in CUES[kind]:
            if c in t:
                if kind == 'pronunciation' and len(c) == 1 and not re.search(r'(sound|letter|حرف|pronounc)', t):
                    continue                    # a lone Arabic letter only counts next to a pronunciation word
                return kind, c.strip()
    return None, ''


def classify(event, tutor_after, doc_word):
    """event: {'text','correction','asked','cue'}; tutor_after: Amal's words within 8 s after; doc_word: words row."""
    if not (event.get('correction') or event.get('asked')):
        return {'miss_kind': None, 'miss_why': ''}
    fk, fwhy = form_diff(event.get('text', ''), (doc_word or {}).get('arabic', ''), (doc_word or {}).get('arabic_plural', ''))
    ck, cwhy = cue_kind(tutor_after)
    if fk in GRAMMAR_KINDS:                                     # the diff is the strongest cheap signal
        kind, why = fk, fwhy + (f'; Amal: "{cwhy}"' if ck == fk else '')
    elif ck in GRAMMAR_KINDS or ck == 'pronunciation':
        kind, why = ck, f'Amal said "{cwhy}"'
    elif event.get('asked'):
        kind, why = 'word', 'Medi asked for the word'
    elif ck == 'word' or fk == 'other':
        kind, why = 'word', (f'Amal said "{cwhy}"' if ck == 'word' else fwhy)
    else:
        kind, why = 'unclear', 'same form as the Doc and no grammar cue in Amal\'s reply'
    return {'miss_kind': kind, 'miss_why': why, 'form_diff': fk, 'cue': ck}


def llm_classify(event, context_text, doc_word, model='gpt-5.5'):
    """Optional fallback through the budget ledger. Returns kind or None. Never called by tests without a mock."""
    import requests, pipeline_ext as px, anees_env as E
    if not E.OPENAI_KEY or not px.budget_ok('openai', 0.02):
        return None
    prompt = (f"A Palestinian Arabic tutor (Amal) reacted to her learner (Medi) saying '{event.get('text')}' for the Doc word "
              f"'{(doc_word or {}).get('arabizi')}' ({(doc_word or {}).get('arabic')} = {(doc_word or {}).get('english')}). Transcript of the next seconds:\n{context_text}\n"
              "Answer with ONE word: word (he did not know / misused the word), article (the el- prefix), gender, tense, plural, pronunciation, none (it was not a correction).")
    r = requests.post('https://api.openai.com/v1/chat/completions', headers={'Authorization': f'Bearer {E.OPENAI_KEY}', 'Content-Type': 'application/json'},
                      json={'model': model, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=60)
    if r.status_code != 200:
        return None
    j = r.json(); px.spend('openai', px.cost_usd(j.get('usage', {})) if hasattr(px, 'cost_usd') else 0.01, f'miss kind {event.get("word_key")}')
    ans = j['choices'][0]['message']['content'].strip().lower().split()[0].strip('.,')
    return ans if ans in KINDS + ('none',) else None


def classify_all(events, words, wmap, use_llm=False, log=None):
    """Annotate every possible-miss event in place with miss_kind / miss_why. Returns counts per kind."""
    starts = [w['s'] for w in words]
    import bisect, collections
    counts = collections.Counter(); llm_calls = 0
    for e in events:
        if e.get('speaker') != 'Medi' or not (e.get('correction') or e.get('asked')):
            continue
        a, b = bisect.bisect_left(starts, e['t_end']), bisect.bisect_right(starts, e['t_end'] + 8)
        after = ' '.join(words[j]['w'] for j in range(a, b) if words[j]['spk'] == 'Amal')
        r = classify(e, after, wmap.get(e['word_key']))
        if r['miss_kind'] == 'unclear' and use_llm and llm_calls < MAX_LLM_PER_LESSON and len(re.findall(r'[A-Za-z]+', after)) >= 8:
            ctx = ' '.join(words[j]['spk'] + ': ' + words[j]['w'] for j in range(max(0, a - 12), b))
            k = llm_classify(e, ctx, wmap.get(e['word_key'])); llm_calls += 1
            if k and k != 'none':
                r = {'miss_kind': k, 'miss_why': 'model read Amal\'s explanation', 'source': 'llm'}
        e['miss_kind'], e['miss_why'] = r['miss_kind'], r['miss_why']
        counts[r['miss_kind']] += 1
    if log:
        log('miss kinds', dict(counts), 'llm calls', llm_calls)
    return counts
