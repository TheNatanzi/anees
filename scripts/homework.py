"""M10c - the text homework loop (Medi grill 2026-09-05: Anees suggests, Amal dictates and may type her own; Medi answers
TYPED Arabizi on docs/homework.html; the `grade` edge function pre-grades on the spot and Amal sees the grade too; her
verdict on the next after-link is what scores the word).

  suggest_prompts(words, stats, rules)   -> English prompt lines in Amal's own style (few-shot from her real WhatsApp prompts),
                                            each with a Doc-only model answer, validated by suggest.validate (0 untaught words)
  mint_items(date, token, items)         -> rows in homework_items bound to the after link
  apply_verdicts()                       -> Amal's right / fix verdicts become word_events rows (her choice wins over the grade)
  style_examples()                       -> her real prompt lines (private export; fixture fallback so tests run anywhere)"""
import datetime, io, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import Matcher, PRONOUNS
import anees_env as E
import suggest

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / 'data' / 'whatsapp' / 'homework_episodes.json'
PAIRS = ROOT / 'tests' / 'fixtures' / 'homework_pairs.json'
HOUSE = ROOT / 'data' / 'vocab' / 'house_spelling.json'
MODEL = suggest.MODEL
N_PROMPTS = 8
MISS_KINDS = {'word': 'word', 'choice': 'choice', 'article': 'article', 'gender': 'gender', 'tense': 'tense', 'mood': 'tense', 'command': 'tense', 'plural': 'plural',
              'prefix': 'tense', 'suffix': 'gender', 'pronoun': 'gender', 'order': 'choice', 'preposition': 'choice', 'spelling': None, 'negation': 'tense'}


def style_examples(n=40):
    """Her real English prompt lines, newest first, de-duplicated, 15-110 chars. Falls back to the public fixture."""
    lines = []
    if EPISODES.exists():
        for ep in reversed(json.load(io.open(EPISODES, encoding='utf-8'))):
            lines.extend(ep['prompts'])
    else:
        lines = [p['english'] for p in json.load(io.open(PAIRS, encoding='utf-8'))]
    out, seen = [], set()
    for ln in lines:
        t = re.sub(r'\s+', ' ', ln).strip()
        k = t.lower()
        if 15 <= len(t) <= 110 and k not in seen and 'lol' not in k:
            seen.add(k); out.append(t)
        if len(out) >= n:
            break
    return out


def house():
    if HOUSE.exists():
        return {k: v['house'] for k, v in json.load(io.open(HOUSE, encoding='utf-8'))['items'].items()}
    return {}


def dropped_prompts(rules):
    """English lines Amal dropped on a sheet (never suggested again)."""
    out = set()
    for r in rules:
        p = r.get('payload') or {}
        if r['kind'] == 'drop' and p.get('source') == 'homework_prompt' and p.get('english'):
            out.add(p['english'].strip().lower())
    return out


def ask_openai(A, B, wmap, examples, n=N_PROMPTS, hs=None):
    import requests, pipeline_ext as px
    if not E.OPENAI_KEY:
        raise RuntimeError('OPENAI_API_KEY missing')
    hs = hs or {}
    fmt = lambda k: f"{hs.get(k, wmap[k]['arabizi'])} | {wmap[k]['arabic']} | {wmap[k]['english'][:50]}"
    glue = 'u, w, fi, bi, min, 3ala, ma3, mish, ma, bas, kteer, kamaan, ya3ni, lamma, iza, hon, enno, illi, laazem, mumken, bidd-'
    prompt = f"""You are Amal, a Palestinian Arabic tutor. After each lesson you post ENGLISH sentences in WhatsApp for your adult student
Medi to translate into spoken Palestinian Arabic (Arabizi). Here are {len(examples)} of your real prompt lines - copy this voice exactly
(short, everyday, sometimes a question, sometimes a command, a hint in brackets when the Arabic needs a gender or plural):
{chr(10).join('- ' + x for x in examples)}

Write {n + 4} NEW prompt lines for tonight. Hard rules:
1. Each line's Arabic answer must use >= 1 word from LIST A and >= 1 word from LIST B (below). Use every LIST A word at least once across the set.
2. Give the model answer in Arabizi (6=ط 7=ح 3=ع 2=ء/ق 5=خ 9=ص 8=غ, spelled EXACTLY as the lists spell it), plus Arabic script.
3. The model answer's content words come ONLY from LIST A and LIST B; you may add pronouns (ana, inta, inti, i7na, huwwe, heyye, humme) and only this glue: {glue}.
4. Vary the shape: 3 questions, 3 commands (with (m) / (f) / (p) hints like you do), the rest statements. 5-12 English words each.
LIST A (words Medi must practise):
{chr(10).join(fmt(k) for k in A)}
LIST B (words Medi already knows):
{chr(10).join(fmt(k) for k in B)}
Return ONLY a JSON array: [{{"english": "...", "arabizi": "...", "arabic": "..."}}, ...]"""
    if not px.budget_ok('openai', 0.15):
        raise px.BudgetStop(f"OpenAI budget: {px.ledger().get('openai', 0):.2f} USD spent; a 0.15 USD call would pass 90 % of the cap")
    r = requests.post('https://api.openai.com/v1/chat/completions', headers={'Authorization': f'Bearer {E.OPENAI_KEY}', 'Content-Type': 'application/json'},
                      json={'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}]}, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f'OpenAI {r.status_code}: {r.text[:200]}')
    j = r.json(); usage = j.get('usage', {})
    px.spend('openai', suggest.cost_usd(usage), f'{MODEL} homework prompts ({usage.get("total_tokens", 0)} tokens)')
    m = re.search(r'\[.*\]', j['choices'][0]['message']['content'], re.S)
    return (json.loads(m.group(0)) if m else []), usage


def suggest_prompts(words, stats, rules, n=N_PROMPTS, use_openai=True, candidates=None):
    """Validated prompt items: [{'n', 'english', 'model_arabizi', 'model_arabic', 'keys'}]. `candidates` lets tests skip OpenAI."""
    A, B, wmap = suggest.candidate_lists(words, stats, rules)
    m = Matcher(words)
    banned = dropped_prompts(rules)
    usage, items, rejected = {}, [], []
    if candidates is None:
        if not use_openai:
            return {'items': [], 'rejected': [], 'usage': {}, 'cost_usd': 0.0, 'model': None, 'list_a': A, 'list_b': B}
        candidates, usage = ask_openai(A, B, wmap, style_examples(), n=n, hs=house())
    for c in candidates:
        if not isinstance(c, dict) or not c.get('english') or not c.get('arabizi'):
            continue
        en = re.sub(r'\s+', ' ', c['english']).strip()
        if en.lower() in banned or en.lower() in {x['english'].lower() for x in items}:
            rejected.append({'english': en, 'why': 'dropped by Amal before' if en.lower() in banned else 'duplicate'}); continue
        v = suggest.validate({'arabizi': c['arabizi']}, m, A, B, wmap)
        if v['ok']:
            items.append({'n': len(items) + 1, 'english': en, 'model_arabizi': c['arabizi'], 'model_arabic': c.get('arabic', ''), 'keys': v['keys']})
        else:
            rejected.append({'english': en, 'arabizi': c['arabizi'], 'why': v['bad_tokens'] or ('no A word' if not v['a'] else 'no B word')})
        if len(items) >= n:
            break
    return {'items': items, 'rejected': rejected, 'usage': usage, 'cost_usd': suggest.cost_usd(usage), 'model': MODEL if usage else None, 'list_a': A, 'list_b': B}


def mint_items(date, token, items):
    """Insert the suggested items for this after link. Returns the stored rows (with ids)."""
    import db
    rows = [{'lesson_date': date, 'token': token, 'n': it['n'], 'english': it['english'], 'model_arabizi': it['model_arabizi'],
             'model_arabic': it.get('model_arabic', ''), 'keys': it['keys'], 'status': 'suggested'} for it in items]
    if not rows:
        return []
    return db.rest('POST', 'homework_items', body=rows, prefer='return=representation') or []


def apply_verdicts(log=print):
    """Amal's verdicts on Medi's typed answers -> word_events rows (speaker Medi, typed, unprompted: translating from English is
    production without hearing the word). 'right' clears every target word; 'fix' marks the words the grade named wrong
    (all target words when the grade named none). Idempotent: rows carry `applied`."""
    import db, buckets
    pend = db.select('homework_answers', {'amal_verdict': 'in.(right,fix)', 'applied': 'is.null', 'select': '*'})
    changed = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for a in pend:
        it = db.select('homework_items', {'id': f"eq.{a['item_id']}", 'select': 'id,lesson_date,keys,english'})
        if not it:
            continue
        it = it[0]
        g = a.get('grade') or {}
        wrong = set(g.get('keys_wrong') or []) & set(it['keys']) if a['amal_verdict'] == 'fix' else set()
        if a['amal_verdict'] == 'fix' and not wrong:
            wrong = set(it['keys'])
        kind = None
        for note in (g.get('notes') or []):
            kind = MISS_KINDS.get((note.get('kind') or '').lower())
            if kind:
                break
        rows = []
        for k in it['keys']:
            bad = k in wrong
            rows.append({'lesson_date': it['lesson_date'], 'word_key': k, 't_start': None, 't_end': None, 'speaker': 'Medi', 'prompted': False,
                         'correction': bad, 'uptake': False, 'asked': False, 'confidence': 1.0, 'clip': None,
                         'text': f"homework: {a['answer'][:160]}", 'miss_kind': (kind or 'unclear') if bad else None,
                         'miss_why': (f"Amal: {a.get('amal_fix') or 'fix'}"[:200] if bad else None)})
        if rows:
            db.upsert('word_events', rows)
        db.rest('PATCH', 'homework_answers', params={'id': f"eq.{a['id']}"}, body={'applied': now}, prefer='return=minimal')
        changed.append({'answer': a['id'], 'verdict': a['amal_verdict'], 'keys': it['keys'], 'wrong': sorted(wrong)})
        log('homework verdict applied', a['id'], a['amal_verdict'], sorted(wrong))
    if changed:
        buckets.recompute_and_store()
    return changed


if __name__ == '__main__':
    if '--apply' in sys.argv:
        print(json.dumps(apply_verdicts(), ensure_ascii=False, indent=1))
    else:
        import db
        words = suggest.load_words()
        stats = db.select('word_stats'); rules = db.select('amal_rules', {'select': 'kind,word_key,payload,source,lesson_date', 'order': 'created_at.asc'})
        out = suggest_prompts(words, stats, rules, use_openai='--no-openai' not in sys.argv)
        print(json.dumps({'items': out['items'], 'rejected': out['rejected'][:6], 'cost_usd': out['cost_usd']}, ensure_ascii=False, indent=1))
