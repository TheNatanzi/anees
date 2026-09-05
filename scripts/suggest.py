"""Sentence suggestions for Amal's planner (M3) and the homework sheet (M6).

Every suggested sentence uses ONLY Doc words (checked by script, 0 violations) and carries >= 1 Missed/new word (list A)
and >= 1 Cold word (list B). Amal's rules change the next set: a word she dropped twice never comes back; kept sentences are
reused first; her edits are stored verbatim as rules. OpenAI (gpt-5.4-mini) writes candidates; the validator decides.
Budget: one call ≈ 3k tokens ≈ $0.01; logged to plan/OVERNIGHT-LOG.md by the caller."""
import collections, io, json, re, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import Matcher, loose, strip_pronoun, PRONOUNS, ARABIC
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
MODEL = 'gpt-5.5'          # mini produced word salad; 5.5 costs ~2 cents per call
N_SENTENCES = 8
GLUE = {'shu', 'bas', 'ai', 'aw', 'em', 'u', 'fi', 'bi', 'min', 'ya3ni', 'iza', 'lama', 'hala', 'ah', 'aha', 'tayeb', 'tamam', '5alas', 'sa7', 'mashi',
        'wala', 'wla', 'ma', 'ma3', 'la', 'mish', 'mesh', 'w', 'wa', 'ya', 'el', 'al', 'hai', 'hada', 'hadi', 'kul', 'ktIr', 'kaman', 'halla', 'alyom', 'hon', 'honak', 'nafs'}
FUNCTION_TOKENS = set(PRONOUNS) | {'u', 'w', 'wa', 'ya', 'la', 'el', 'al', 'fi', 'bi', 'min', '3ala', '3an', 'ma3', 'mish', 'mesh', 'ma', 'bas', 'shu', 'kteer',
                                   'kaman', 'hon', 'honak', 'hala2', 'halla', 'elyom', 'el-yom', 'bukra', 'embare7', 'lama', 'iza', 'aw', 'ya3ni', 'kul', 'hada', 'hadi',
                                   'hai', 'hadol', 'hay', 'esh', 'wein', 'keef', 'leish', 'meen', 'ana', 'inta', 'inti', 'i7na', 'e7na', 'hu', 'hi', 'huwe', 'hiye', 'hume', 'intu'}


def load_words():
    return json.load(io.open(ROOT / 'data' / 'vocab' / 'words.json', encoding='utf-8'))['items']


def candidate_lists(words, stats, rules, n_a=10, n_b=14):
    """A = missed + recent (learned in the last 3 lessons) words; B = cold / ice_cold words. Dropped-twice words are excluded."""
    dropped = collections.Counter(r['word_key'] for r in rules if r['kind'] == 'drop' and r.get('word_key'))
    banned = {k for k, n in dropped.items() if n >= 2} | GLUE
    wmap = {w['key']: w for w in words}
    st = {s['word_key']: s for s in stats}
    ok = lambda k: k in wmap and k not in banned and len(strip_pronoun(wmap[k]['arabizi'])) >= 3 and not wmap[k]['arabizi'].endswith('?')
    rank = {'missed': 0, 'new': 0, 'shaky': 1, 'never': 2}
    A = [k for k, s in sorted(st.items(), key=lambda kv: (-(kv[1].get('weight') or 1), rank.get(kv[1]['bucket'], 9), -kv[1]['times_missed'], -kv[1]['times_seen']))
         if ok(k) and (s['bucket'] in ('missed', 'new', 'shaky') or (s['bucket'] == 'never' and s['recent']))][:n_a]
    B = [k for k, s in sorted(st.items(), key=lambda kv: (-kv[1]['times_seen'])) if ok(k) and s['bucket'] in ('cold', 'ice_cold') and k not in A][:n_b]
    return A, B, wmap


def tokens(arabizi_sentence):
    return [t for t in re.split(r'[\s,.!?…]+', arabizi_sentence) if t]


_FN_CACHE = {}


def function_tokens(matcher):
    """Pronouns (taught in the Introductions tab) + only those glue tokens that ARE Doc words. Anything else is untaught."""
    k = id(matcher)
    if k not in _FN_CACHE:
        _FN_CACHE[k] = set(PRONOUNS) | {'u', 'w', 'ya', 'el', 'al'} | {t for t in FUNCTION_TOKENS if matcher.match(t, fuzzy=False)}
    return _FN_CACHE[k]


def validate(sentence, matcher, allowed_a, allowed_b, wmap):
    """A sentence is valid when every token is a Doc word / pronoun / glue and it uses >= 1 A word and >= 1 B word.
    Multi-word Doc entries (e.g. 'Ana ba7ki') are matched as 1-3-token n-grams first."""
    toks = tokens(sentence['arabizi'])
    keys, i, bad = [], 0, []
    while i < len(toks):
        hit = None
        for span in (3, 2, 1):
            if i + span <= len(toks):
                k = matcher.match(' '.join(toks[i:i + span]), fuzzy=False)
                if k:
                    hit = (k, span); break
        if hit:
            keys.append(hit[0]); i += hit[1]; continue
        t = loose(toks[i]); fn = function_tokens(matcher)
        if t in fn or toks[i].lower().strip('-') in fn or len(t) <= 1:
            i += 1; continue
        bad.append(toks[i]); i += 1
    fam = lambda k: loose(strip_pronoun(wmap[k]['arabizi'])) if k in wmap else k
    a_hit = [k for k in keys if k in allowed_a or fam(k) in {fam(x) for x in allowed_a}]
    b_hit = [k for k in keys if k in allowed_b or fam(k) in {fam(x) for x in allowed_b}]
    return {'ok': not bad and bool(a_hit) and bool(b_hit), 'bad_tokens': bad, 'keys': keys, 'a': a_hit, 'b': b_hit}


def ask_openai(A, B, wmap, n=N_SENTENCES, extra='', glue=None):
    import requests
    if not E.OPENAI_KEY:
        raise RuntimeError('OPENAI_API_KEY missing')
    fmt = lambda k: f"{wmap[k]['arabizi']} | {wmap[k]['arabic']} | {wmap[k]['english'][:50]}"
    glue_list = ', '.join(sorted(glue)) if glue else 'u, w, fi, bi, min, 3ala, ma3, mish, bas, kteer, kaman, ya3ni, lama, iza, hon'
    prompt = f"""You are a Palestinian Arabic tutor writing practice sentences for an adult learner (Medi). Spell the Arabic in the tutor's Arabizi
(6=ط 7=ح 3=ع 2=ء/ق 5=خ 9=ص 8=غ) exactly as the word lists spell it, and give the Arabic script and the English meaning.
Write {n + 4} DIFFERENT, natural, grammatical, everyday spoken sentences of 4-9 words that a tutor would actually say or ask.
Hard rules:
1. Content words come ONLY from LIST A and LIST B below (copy the Arabizi exactly; a leading "Ana " may be dropped when a pronoun is present).
2. You may add pronouns (ana, inta, inti, i7na, huwwe, heyye, humme) and ONLY these glue words: {glue_list}.
3. Every sentence has >= 1 word from LIST A and >= 1 word from LIST B. Use each LIST A word at least once across the set.
4. No English words inside the Arabizi. No vocabulary outside the lists (no other nouns, verbs or adjectives).
{extra}
LIST A (words Medi must practise):
{chr(10).join(fmt(k) for k in A)}
LIST B (words Medi already knows):
{chr(10).join(fmt(k) for k in B)}
Return ONLY a JSON array: [{{"arabizi": "...", "arabic": "...", "english": "..."}}, ...]"""
    import pipeline_ext as px
    if not px.budget_ok('openai', 0.15):                     # the plan's hard limit: stop paid calls at 90 % of 10 USD
        raise px.BudgetStop(f"OpenAI budget: {px.ledger().get('openai', 0):.2f} USD spent; a 0.15 USD call would pass 90 % of the cap")
    r = requests.post('https://api.openai.com/v1/chat/completions', headers={'Authorization': f'Bearer {E.OPENAI_KEY}', 'Content-Type': 'application/json'},
                      json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f'OpenAI {r.status_code}: {r.text[:200]}')
    j = r.json()
    text = j['choices'][0]['message']['content']
    usage = j.get('usage', {})
    px.spend('openai', cost_usd(usage), f'{MODEL} sentences ({usage.get("total_tokens", 0)} tokens)')
    m = re.search(r'\[.*\]', text, re.S)
    items = json.loads(m.group(0)) if m else []
    return items, usage


def cost_usd(usage):
    # ceiling price used for the budget log: $5 / M input, $20 / M output (never guessed lower)
    return round(usage.get('prompt_tokens', 0) * 5.0 / 1e6 + usage.get('completion_tokens', 0) * 20.0 / 1e6, 4)


def suggest_sentences(words, stats, rules, n=N_SENTENCES, use_openai=True, kept_first=True):
    A, B, wmap = candidate_lists(words, stats, rules)
    m = Matcher(words)
    out, rejected = [], []
    if kept_first:
        for r in rules:
            pl = r.get('payload') or {}
            if r['kind'] in ('keep', 'edit') and (pl.get('edited') or pl.get('arabizi')):
                s = {'arabizi': pl.get('edited') or pl['arabizi'], 'arabic': '' if pl.get('edited') else pl.get('arabic', ''), 'english': pl.get('english', ''),
                     'source': 'edited by Amal' if pl.get('edited') else 'kept by Amal'}
                v = validate(s, m, A, B, wmap)
                if v['ok'] and s['arabizi'] not in {x['arabizi'] for x in out}:
                    out.append({**s, 'keys': v['keys']})
    usage = {}
    if use_openai and len(out) < n:
        items, usage = ask_openai(A, B, wmap, n=n, glue=function_tokens(m) - set(PRONOUNS))
        for it in items:
            if not isinstance(it, dict) or not it.get('arabizi'):
                continue
            v = validate(it, m, A, B, wmap)
            if v['ok'] and it['arabizi'] not in {x['arabizi'] for x in out}:
                out.append({'arabizi': it['arabizi'], 'arabic': it.get('arabic', ''), 'english': it.get('english', ''), 'keys': v['keys'], 'source': 'suggested'})
            else:
                rejected.append({'arabizi': it.get('arabizi'), 'why': v['bad_tokens'] or ('no A word' if not v['a'] else 'no B word')})
            if len(out) >= n:
                break
    return {'sentences': out[:n], 'rejected': rejected, 'list_a': A, 'list_b': B, 'usage': usage, 'cost_usd': cost_usd(usage), 'model': MODEL if usage else None}


def planner_payload(lesson_date, use_openai=True):
    """Everything the planner page needs: topic suggestions, repeat candidates, sentences (all Doc-checked)."""
    import db
    words = load_words(); wmap = {w['key']: w for w in words}
    stats = db.select('word_stats')
    rules = db.select('amal_rules', {'select': 'kind,word_key,payload,source,lesson_date', 'order': 'created_at.asc'})
    lessons = db.select('lessons', {'select': 'date,topics', 'order': 'date.desc', 'limit': 1})
    last_topic = None
    if lessons and lessons[0].get('topics'):
        t = [x for x in lessons[0]['topics'] if not x.get('glue')]
        last_topic = (t or lessons[0]['topics'])[0]['topic']
    tabs = list(dict.fromkeys(w['topic'] for w in words))
    topic_rules = [r for r in rules if r['kind'] == 'topic']
    if last_topic and last_topic.startswith('typed family: '):
        last_topic = ' / '.join(last_topic[len('typed family: '):].split(' / ')[:3]) + " (last lesson's words)"
    topics = [x for x in [last_topic, (topic_rules[-1]['payload'] or {}).get('topic') if topic_rules else None] if x]
    for tb in tabs:
        if len(topics) >= 3:
            break
        if tb not in topics:
            topics.append(tb)
    sug = suggest_sentences(words, stats, rules, use_openai=use_openai)
    cell = lambda k: {'key': k, 'arabizi': wmap[k]['arabizi'], 'arabic': wmap[k]['arabic'], 'english': wmap[k]['english'][:60]} if k in wmap else {'key': k}
    return {'lesson_date': lesson_date, 'built': datetime.datetime.now().isoformat(timespec='seconds'), 'topics': topics[:3],
            'repeat': [cell(k) for k in sug['list_a'][:3]], 'sentences': [{**s, 'words': [cell(k) for k in s['keys']]} for s in sug['sentences']],
            'meta': {'list_a': sug['list_a'], 'list_b': sug['list_b'], 'rejected': sug['rejected'], 'model': sug['model'], 'cost_usd': sug['cost_usd'], 'usage': sug['usage']}}
