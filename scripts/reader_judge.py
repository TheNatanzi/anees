"""Union-then-judge (overnight 2026-10-17). Every candidate slip from the reader pool (clusters, reader_ensemble.clusters,
'asked' / no-reaction signals dropped) goes to cross-family judges with the lesson transcript. A judge returns, per
candidate id, {"verdict": "slip"|"not", "confidence": 0-100, "why": ...}. Variants:
  plain    - the grade book's definition of a slip only
  fewshot  - plus worked examples (real / not real) taken ONLY from the OTHER two lessons' keys (leave-one-lesson-out)
  defend   - the judge is told to argue the defence: reject unless the tutor clearly corrected it
Writes overnight-2026-10-17/judge/<date>.<judge>.<variant>.json

    python -I scripts/reader_judge.py run --judges claude:claude-opus-5-5,openai:gpt-5.5,gemini:gemini-3.7-flash --variant fewshot
    python -I scripts/reader_judge.py score --judges ... --variant fewshot
"""
import argparse, concurrent.futures as cf, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(REPO)
os.environ.setdefault('RE_DROP', 'asked,none')
import reader_ensemble as E, reader_tiers as R, vendor_read as V

POOL = 'opus,sonnet,openai-gpt-5.5,gemini-gemini-3.7-flash,openai-gpt-5.6-terra,openai-gpt-6-sol,openai-gpt-5.6-sol,gemini-gemini-3.1-pro-preview'.split(',')
JD = os.path.join(E.OUT, 'judge')
os.makedirs(JD, exist_ok=True)

DEF_V2 = """WHAT COUNTS AS A SLIP (the grade book's rule; this is what you are judging):
- A slip = Medi PRODUCED a wrong Arabic word or form (even said as a guess, a question like "is it X?", half a sentence,
  or while asking about a rule) AND the tutor Amal then gave or confirmed a different, right form (recast, "no", named the
  rule, prompted until he fixed it, finished the sentence for him, or typed it in chat).
- Each time he says it wrong and is corrected counts again (the same mistake at 01:57 and 02:21 = two slips).
- NOT a slip: he asked how to say something WITHOUT trying an Arabic form himself; he switched to English with no Arabic
  attempt; he fixed it himself before she reacted; the speech-to-text engine misheard him; a correct Levantine form that
  differs from MSA; anything she let pass with no reaction; he misunderstood HER (comprehension, no wrong form of his).
- If two candidates describe the same moment, mark the better one slip and the copy not."""

DEF = """WHAT COUNTS AS A SLIP (the grade book's rule; this is what you are judging):
- A slip is a mistake Medi (the student) made in Arabic that the tutor Amal CORRECTED or REJECTED: she recast it in the right
  form, said no, named the rule, prompted until he fixed it, or typed the fix in chat.
- NOT a slip: Medi asking for a word he does not know, switching to English, a word he did not know yet ("how do you say"),
  a self-fix before she reacts, a stutter or cut-off, a speech-to-text error (the engine misheard him), a question about a rule,
  a correct Levantine form that is just different from MSA, or anything Amal let pass with no reaction.
- One slip per corrected moment: if several candidates describe the same moment, only the best one is a slip."""


def candidates(d):
    cl = E.clusters(POOL, d)
    out = []
    for i, c in enumerate(sorted(cl, key=lambda c: c['t'])):
        reps = sorted(c['members'], key=lambda m: -len(str(m['row'].get('why') or '')))[:3]
        out.append({'id': f'C{i + 1}', 't': R.mmss(c['t']), 'family': c['fam'], 'readers': len(c['tags']),
                    'claims': [{'wrong': m['row'].get('wrong'), 'right': m['row'].get('right'), 'kind': m['row'].get('kind'),
                                'signal': m['row'].get('signal'), 'why': str(m['row'].get('why') or '')[:300]} for m in reps],
                    '_t': c['t']})
    return out


def examples(test):
    """Worked examples from the other lessons' keys: up to 8 real and 8 not-real candidates, fixed seed."""
    ex = []
    for d in E.LESSONS:
        if d == test:
            continue
        ks = R.key_slips(d)
        for c in candidates(d):
            real = any(k[0] == c['family'] and abs(k[1] - c['_t']) <= R.MATCH_S for k in ks)
            ex.append((real, d, c))
    rnd = random.Random(17)
    real = [e for e in ex if e[0]]; fake = [e for e in ex if not e[0]]
    rnd.shuffle(real); rnd.shuffle(fake)
    pick = real[:8] + fake[:8]
    rnd.shuffle(pick)
    lines = []
    for real, d, c in pick:
        cl = c['claims'][0]
        lines.append(f"- [{c['t']}] {c['family']}: '{cl['wrong']}' -> '{cl['right']}' (signal {cl['signal']}) => {'SLIP' if real else 'NOT a slip'}")
    return "WORKED EXAMPLES from other lessons, judged by Medi's own full review:\n" + '\n'.join(lines)


def prompt(d, variant):
    brief_rules = V.read(REPO, 'data/lesson-work/full-audit/buckets.md')
    stance = {'plain': 'Judge each candidate fairly.',
              'fewshot': 'Judge each candidate fairly, calibrated on the worked examples.',
              'v2': 'Judge each candidate fairly.',
              'defend': 'You are the DEFENCE: Medi is innocent unless the transcript shows the tutor clearly corrected or rejected '
                        'what he said. Reject anything doubtful.'}[variant]
    system = ("You judge candidate mistakes found by other readers in one Arabic lesson transcript (Medi = student, "
              "Amal = Levantine Arabic tutor). Readers are anonymous; how many flagged a candidate is NOT evidence. "
              + stance + "\n\n" + DEF + "\n\n<file path=\"buckets.md\">\n" + brief_rules + "\n</file>")
    if variant == 'fewshot':
        system += "\n\n" + examples(d)
    cands = [{k: v for k, v in c.items() if not k.startswith('_') and k != 'readers'} for c in candidates(d)]
    user = (f"Lesson {d}. Read the transcript, then judge EVERY candidate. Return ONE JSON object: "
            "{\"verdicts\": {\"C1\": {\"verdict\": \"slip\" or \"not\", \"confidence\": 0-100, \"why\": \"one short sentence\"}, ...}}\n\n"
            "<candidates>\n" + json.dumps(cands, ensure_ascii=False, indent=0) + "\n</candidates>\n\n"
            f"<transcript>\n" + V.read(REPO, f'data/lesson-work/reader-tiers/{d}.txt') + "\n</transcript>")
    return system, user


def run_one(judge, variant, d):
    vendor, model = judge.split(':', 1)
    out = os.path.join(JD, f'{d}.{model}.{variant}.json')
    if os.path.exists(out):
        return out, 'cached'
    system, user = prompt(d, variant)
    try:
        text, usage = {'openai': V.call_openai, 'gemini': V.call_gemini, 'claude': V.call_claude, 'codex': V.call_codex}[vendor](model, system, user)
        j = V.parse(text)
        json.dump({'judge': judge, 'variant': variant, 'date': d, 'usage': usage, 'verdicts': j.get('verdicts', j)},
                  open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return out, f"ok {len(j.get('verdicts', j))} verdicts {usage}"
    except Exception as e:
        return out, f'ERROR {type(e).__name__}: {str(e)[:200]}'


def load(judge, variant, d):
    p = os.path.join(JD, f"{d}.{judge.split(':', 1)[1]}.{variant}.json")
    return json.load(open(p, encoding='utf-8'))['verdicts'] if os.path.exists(p) else None


def p_slip(v):
    if not isinstance(v, dict):
        return 0.0
    c = float(v.get('confidence') or 50) / 100
    return c if str(v.get('verdict')).lower().startswith('slip') else 1 - c


def score(judges, variant, mode='mean'):
    cands = {d: candidates(d) for d in E.LESSONS}
    J = {d: [load(j, variant, d) for j in judges] for d in E.LESSONS}
    if any(v is None for d in E.LESSONS for v in J[d]):
        print('missing judge files'); return

    def s(c, d):
        ps = [p_slip(v.get(c['id'])) for v in J[d]]
        return min(ps) if mode == 'min' else sum(ps) / len(ps)

    def preds(th, d):
        return [(c['family'], c['_t']) for c in cands[d] if s(c, d) >= th]

    def choose(train):
        return max((t / 20 for t in range(2, 20)), key=lambda th: E.score_pred({d: preds(th, d) for d in train}, train)['f05'])
    res, folds = E.lolo(choose, preds)
    E.log(f"judge[{variant},{mode}] {'+'.join(j.split(':')[1] for j in judges)} over union of {len(POOL)}", res, folds)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'score', 'count'])
    ap.add_argument('--judges', default='claude:claude-opus-5-5,openai:gpt-5.5,gemini:gemini-3.7-flash')
    ap.add_argument('--variant', default='fewshot'); ap.add_argument('--mode', default='mean')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    judges = a.judges.split(',')
    if a.cmd == 'count':
        for d in E.LESSONS:
            print(d, len(candidates(d)))
    elif a.cmd == 'run':
        jobs = [(j, a.variant, d) for j in judges for d in E.LESSONS]
        with cf.ThreadPoolExecutor(9) as ex:
            for (j, v, d), (out, st) in zip(jobs, ex.map(lambda x: run_one(*x), jobs)):
                print(d, j, v, st, flush=True)
    else:
        for j in judges:
            score([j], a.variant)
        score(judges, a.variant, 'mean'); score(judges, a.variant, 'min')


# ------------------------------------------------------------------ stack: judges + reader votes + signal, LOLO logistic
SIGS = ('named-rule', 'recast', 'prompt-then-fix', 'explicit-no', 'finished-sentence')


def stack(judge_specs, extra_pool=None, l2=1.0, tag=''):
    """judge_specs: ['claude-opus-5-5:plain', ...]. Features per candidate: bias, readers/n, family, signal one-hots
    (majority over members), each judge's p(slip), mean judge p. LOLO: fit on 2 lessons, pick a threshold there, score the 3rd."""
    cands = {d: candidates(d) for d in E.LESSONS}
    jv = {}
    for spec in judge_specs:
        m, v = spec.split(':')
        for d in E.LESSONS:
            p = os.path.join(JD, f'{d}.{m}.{v}.json')
            if not os.path.exists(p):
                print('missing', p); return
            jv[(spec, d)] = json.load(open(p, encoding='utf-8'))['verdicts']

    def fx(c, d):
        sigs = [E.sig({'signal': cl['signal']}) for cl in c['claims']]
        ps = [p_slip(jv[(s, d)].get(c['id'])) for s in judge_specs]
        return [1.0, c['readers'] / len(POOL), 1.0 if c['family'] == 'grammar' else 0.0] + \
               [sum(1 for s in sigs if s == k) / len(sigs) for k in SIGS] + ps + [sum(ps) / len(ps)]
    ks = {d: R.key_slips(d) for d in E.LESSONS}
    data = {d: [(c, fx(c, d), 1.0 if any(k[0] == c['family'] and abs(k[1] - c['_t']) <= R.MATCH_S for k in ks[d]) else 0.0)
                for c in cands[d]] for d in E.LESSONS}

    def preds(wt, d):
        return [(c['family'], c['_t']) for c, x, _ in data[d] if E.prob(wt[0], x) >= wt[1]]

    def choose(train):
        X = [x for d in train for _, x, _ in data[d]]; Y = [y for d in train for _, _, y in data[d]]
        w = E.fit(X, Y, l2=l2)
        th = max((t / 20 for t in range(4, 19)), key=lambda th: E.score_pred({d: preds((w, th), d) for d in train}, train)['f05'])
        return (w, th)
    res, folds = E.lolo(choose, preds)
    for f in folds:
        f['params'] = {'threshold': f['params'][1]}
    E.log(f"stack judges[{','.join(judge_specs)}] + votes + signal{tag}", res, folds)


# ------------------------------------------------------------------ window judge: 5-minute slices, focused (research memo #5)
def seg_prompts(d, variant='win'):
    lines = V.read(REPO, f'data/lesson-work/reader-tiers/{d}.txt').splitlines()

    def t_of(l):
        import re
        m = re.match(r'\[(\d+):(\d+)(?::(\d+))?\]', l)
        if not m:
            return None
        a = [int(x) for x in m.groups() if x is not None]
        return a[0] * 3600 + a[1] * 60 + a[2] if len(a) == 3 else a[0] * 60 + a[1]
    timed = [(t_of(l), l) for l in lines]
    C = candidates(d)
    segs = {}
    for c in C:
        segs.setdefault(int(c['_t'] // 300), []).append(c)
    out = []
    for s, cs in sorted(segs.items()):
        lo, hi = s * 300 - 60, (s + 1) * 300 + 60
        window = '\n'.join(l for t, l in timed if t is not None and lo <= t <= hi)
        system = ("You judge candidate mistakes in a short slice of an Arabic lesson (Medi = student, Amal = Levantine tutor). "
                  "Judge each candidate fairly from the slice; readers are anonymous.\n\n" + DEF + "\n\n<file path=\"buckets.md\">\n"
                  + V.read(REPO, 'data/lesson-work/full-audit/buckets.md') + "\n</file>")
        cands = [{k: v for k, v in c.items() if not k.startswith('_') and k != 'readers'} for c in cs]
        user = ("Return ONE JSON object: {\"verdicts\": {\"C1\": {\"verdict\": \"slip\" or \"not\", \"confidence\": 0-100, \"why\": \"...\"}}} "
                "for exactly these candidates.\n<candidates>\n" + json.dumps(cands, ensure_ascii=False) + "\n</candidates>\n<slice>\n" + window + "\n</slice>")
        out.append((s, system, user))
    return out


def run_window(judge, d):
    vendor, model = judge.split(':', 1)
    out = os.path.join(JD, f'{d}.{model}.win.json')
    if os.path.exists(out):
        return 'cached'
    call = {'openai': V.call_openai, 'gemini': V.call_gemini, 'claude': V.call_claude, 'codex': V.call_codex}[vendor]
    verdicts, errs = {}, 0

    def one(sp):
        s, system, user = sp
        for _ in range(2):
            try:
                text, _u = call(model, system, user)
                j = V.parse(text)
                return j.get('verdicts', j)
            except Exception:
                continue
        return None
    with cf.ThreadPoolExecutor(6) as ex:
        for v in ex.map(one, seg_prompts(d)):
            if v is None:
                errs += 1
            else:
                verdicts.update(v)
    json.dump({'judge': judge, 'variant': 'win', 'date': d, 'errors': errs, 'verdicts': verdicts}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return f'ok {len(verdicts)} verdicts, {errs} failed slices'


# ------------------------------------------------------------------ council on the unsure candidates (Medi: "using a /council method")
LENSES = {
    'teacher': 'a strict Arabic GRAMMAR TEACHER: did he produce a wrong form that the tutor fixed?',
    'native': 'a LEVANTINE NATIVE SPEAKER: is his form actually acceptable spoken Levantine (then not a slip), or really wrong?',
    'tutor': "the TUTOR'S OWN RULES (buckets.md): does her correction match one of her rules or a clear word fix?",
    'noise': 'a SPEECH-TO-TEXT SKEPTIC: could the "mistake" be the engine mishearing him, a cut-off, or a stutter?',
    'learner': 'a LEARNER-PSYCHOLOGY expert: was he trying a form (slip) or only asking / searching for a word (not a slip)?',
}
BAND = (0.3, 0.7)


def unsure(d, specs=('claude-opus-5-5:plain', 'gemini-3.7-flash:plain')):
    jv = [json.load(open(os.path.join(JD, f"{d}.{s.split(':')[0]}.{s.split(':')[1]}.json"), encoding='utf-8'))['verdicts'] for s in specs]
    out = []
    for c in candidates(d):
        p = sum(p_slip(v.get(c['id'])) for v in jv) / len(jv)
        c['_p'] = p
        if BAND[0] <= p <= BAND[1]:
            out.append(c)
    return out


def council(d, advisor='gemini:gemini-3.7-flash', chair='claude:claude-opus-5-5'):
    out = os.path.join(JD, f'{d}.council.json')
    if os.path.exists(out):
        return 'cached'
    U = unsure(d)
    if not U:
        json.dump({'verdicts': {}}, open(out, 'w', encoding='utf-8')); return 'none unsure'
    tr = V.read(REPO, f'data/lesson-work/reader-tiers/{d}.txt')
    cands = json.dumps([{k: v for k, v in c.items() if not k.startswith('_') and k != 'readers'} for c in U], ensure_ascii=False)
    av, am = advisor.split(':', 1)
    call = {'openai': V.call_openai, 'gemini': V.call_gemini, 'claude': V.call_claude, 'codex': V.call_codex}

    def adv(lens):
        system = (f"You are one advisor on a council judging candidate mistakes in an Arabic lesson. Your lens: {LENSES[lens]}\n\n"
                  + DEF_V2 + "\n\n<file path=\"buckets.md\">\n" + V.read(REPO, 'data/lesson-work/full-audit/buckets.md') + "\n</file>")
        user = ("For EVERY candidate return {\"verdicts\": {\"C1\": {\"verdict\": \"slip\"|\"not\", \"argument\": \"2 sentences, quote the transcript\"}}}"
                f"\n<candidates>{cands}</candidates>\n<transcript>\n{tr}\n</transcript>")
        for _ in range(2):
            try:
                return V.parse(call[av](am, system, user)[0]).get('verdicts', {})
            except Exception:
                continue
        return {}
    with cf.ThreadPoolExecutor(5) as ex:
        advice = dict(zip(LENSES, ex.map(adv, LENSES)))
    letters = dict(zip(LENSES, 'ABCDE'))
    brief = {c['id']: {f'Advisor {letters[l]}': advice[l].get(c['id']) for l in LENSES} for c in U}
    cv, cm = chair.split(':', 1)
    system = ("You chair a council. Five anonymous advisors argued each candidate. First critique the weakest argument, then decide. "
              "Weigh evidence quoted from the transcript, not the head count.\n\n" + DEF_V2)
    user = ("Return {\"verdicts\": {\"C1\": {\"verdict\": \"slip\"|\"not\", \"confidence\": 0-100, \"why\": \"...\"}}} for every candidate."
            f"\n<candidates>{cands}</candidates>\n<advisors>{json.dumps(brief, ensure_ascii=False)}</advisors>\n<transcript>\n{tr}\n</transcript>")
    v = {}
    for _ in range(2):
        try:
            v = V.parse(call[cv](cm, system, user)[0]).get('verdicts', {}); break
        except Exception:
            continue
    json.dump({'advice': advice, 'verdicts': v, 'unsure': [c['id'] for c in U]}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return f'{len(U)} unsure, chair ruled {len(v)}'


def score_council():
    cands = {d: candidates(d) for d in E.LESSONS}
    for d in E.LESSONS:
        unsure(d)  # sets _p on fresh candidate dicts
    base = {}
    for d in E.LESSONS:
        jv = [json.load(open(os.path.join(JD, f"{d}.{m}.plain.json"), encoding='utf-8'))['verdicts'] for m in ('claude-opus-5-5', 'gemini-3.7-flash')]
        base[d] = {c['id']: sum(p_slip(v.get(c['id'])) for v in jv) / 2 for c in cands[d]}
    CV = {d: json.load(open(os.path.join(JD, f'{d}.council.json'), encoding='utf-8'))['verdicts'] for d in E.LESSONS}

    def s(c, d):
        p = base[d][c['id']]
        if BAND[0] <= p <= BAND[1] and c['id'] in CV[d]:
            return p_slip(CV[d][c['id']])
        return p

    def preds(th, d):
        return [(c['family'], c['_t']) for c in cands[d] if s(c, d) >= th]

    def choose(train):
        return max((t / 20 for t in range(2, 20)), key=lambda th: E.score_pred({d: preds(th, d) for d in train}, train)['f05'])
    res, folds = E.lolo(choose, preds)
    E.log('council (5 lenses, Gemini Flash advisors, Opus chair) on unsure + Opus/Flash panel', res, folds)
