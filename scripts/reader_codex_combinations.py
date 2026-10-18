"""Offline, frozen-menu LOLO experiments. Run: python -I scripts/reader_codex_combinations.py

No vendor module, model process, network client, or API key is used. The existing
reader_tiers scorer is the sole source of prediction conversion and metrics.
Results are exploratory: selecting a winner from this menu needs a fresh lesson.
"""
import hashlib
import itertools
import json
import os
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ['RE_DROP'] = 'asked,none'
import reader_ensemble as E
import reader_tiers as R

ROOT = Path(R.REPO)
OUT = Path(E.OUT)
POOL = 'opus,sonnet,openai-gpt-5.5,gemini-gemini-3.7-flash,openai-gpt-5.6-terra,openai-gpt-6-sol,openai-gpt-5.6-sol,gemini-gemini-3.1-pro-preview'.split(',')
MODELS = ['claude-opus-5-5', 'gemini-3.7-flash', 'claude-sonnet-5-5', 'gemini-3.1-pro-preview']
TH = [i / 20 for i in range(2, 20)]
SIGS = ['recast', 'explicit-no', 'named-rule', 'prompt-then-fix', 'finished-sentence']
NEG = ['self-correct', 'self-repair', 'stt', 'mishear', 'duplicate', 'same moment', 'acceptable', 'no correction', 'no clear', 'asking for', 'cut-off']
POS = ['recast', 'explicitly', 'reject', 'corrected', 'prompt', 'wrong form']
INPUTS = {}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def track(p):
    INPUTS[str(p.relative_to(ROOT)).replace('\\', '/')] = sha(p)


def probability(v):
    confidence = float(v.get('confidence') or 50) / 100
    return confidence if str(v.get('verdict')).lower().startswith('slip') else 1 - confidence


def data():
    """Use precisely reader_judge.candidates ordering; preserve cached judge IDs."""
    all_data = {}
    for d in R.LESSONS:
        for tag in POOL:
            track(Path(R.DIR) / 'runs' / f'{d}.{tag}-run1.json')
        judges = {}
        for variant in ['plain', 'defend', 'fewshot', 'v2', 'win']:
            for model in MODELS:
                p = OUT / 'judge' / f'{d}.{model}.{variant}.json'
                if p.exists():
                    track(p)
                    judges[(model, variant)] = json.loads(p.read_text(encoding='utf-8'))['verdicts']
        repeats = []
        for n in range(1, 6):
            tag = 'gemini-gemini-3.7-flash' + (f'-r{n}' if n > 1 else '')
            p = Path(R.DIR) / 'runs' / f'{d}.{tag}-run1.json'
            track(p)
            repeats.append(E.flags(tag, d))
        candidates = []
        for i, c in enumerate(sorted(E.clusters(POOL, d), key=lambda c: c['t'])):
            cid = f'C{i+1}'
            assert all(cid in v for v in judges.values()), (d, cid, 'missing verdict')
            ps = {f'{m}:{v}': probability(j[cid]) for (m, v), j in judges.items()}
            signals = [E.sig(m['row']) for m in c['members']]
            assert not (set(signals) & {'asked', 'none'})
            signal = max(sorted(set(signals)), key=signals.count)
            texts = ' '.join(judges[(m, 'plain')][cid].get('why', '').lower() for m in MODELS[:2])
            base = statistics.mean(ps[f'{m}:plain'] for m in MODELS[:2])
            repeat = statistics.mean(any(f['fam'] == c['fam'] and abs(f['t']-c['t']) <= R.MATCH_S for f in fs) for fs in repeats)
            candidates.append(dict(id=cid, fam=c['fam'], t=c['t'], signal=signal,
                votes=len(c['tags']) / len(POOL), tags=sorted(c['tags']), ps=ps, base=base,
                negative=float(any(w in texts for w in NEG)), positive=float(any(w in texts for w in POS)),
                repeat=repeat))
        all_data[d] = candidates
    return all_data


def predictions(cs):
    return R.predicted([{'kind': c['fam']+'-A', 't': R.mmss(c['t'])} for c in cs])


def score(pred, keys, lessons):
    return R.prf(sum(R.match(pred[d], keys[d]) for d in lessons),
                 sum(len(pred[d]) for d in lessons), sum(len(keys[d]) for d in lessons))


def best(configs, apply, train, keys):
    # Stable first-in-grid tie break, exactly the existing scorer's rounded F0.5.
    return max(configs, key=lambda q: score({d: apply(q, d) for d in train}, keys, train)['f05'])


def run(name, choose, apply, dataset, results):
    pred, folds = {}, []
    for test in R.LESSONS:
        train = [d for d in R.LESSONS if d != test]
        keys = {d: R.key_slips(d) for d in train}
        params = choose(train, keys)
        # Test key is first accessed only after training and predictions finish.
        pred[test] = apply(params, test)
        held_key = R.key_slips(test)
        metric = R.prf(R.match(pred[test], held_key), len(pred[test]), len(held_key))
        folds.append(dict(test=test, train=train, params=params, f05=metric['f05'], metrics=metric,
                          predictions=pred[test]))
    metrics = score(pred, {d: R.key_slips(d) for d in R.LESSONS}, R.LESSONS)
    record = dict(method='codex: '+name, heldout=metrics, folds=folds)
    results.append(record)
    print(f"{name}: F0.5 {metrics['f05']}, P {metrics['precision']}, R {metrics['recall']}", flush=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for p in (ROOT / 'data/lesson-work/review-grades').glob('*.json'):
        track(p)
    for script in ['reader_tiers.py', 'reader_ensemble.py', 'reader_codex_combinations.py', 'reader_judge.py']:
        track(ROOT / 'scripts' / script)
    dataset = data()
    results = []

    def grid(name, configs, value):
        def apply(q, d):
            return predictions([c for c in dataset[d] if value(c, q)])
        run(name, lambda tr, k: best(configs, apply, tr, k), apply, dataset, results)

    grid('baseline reproduction (Opus + Flash plain mean)', TH, lambda c, t: c['base'] >= t)
    grid('signal-specific panel thresholds', list(itertools.product(TH, [-.15, 0, .15], [-.15, 0, .15])),
         lambda c, q: c['base'] >= q[0] + (q[1] if c['signal'] == 'recast' else q[2] if c['signal'] in ['explicit-no', 'named-rule'] else 0))
    grid('family-specific panel thresholds', list(itertools.product(TH, TH)),
         lambda c, q: c['base'] >= q[c['fam'] == 'grammar'])
    grid('judge disagreement penalty', list(itertools.product([0, .25, .5, 1], TH)),
         lambda c, q: c['base'] - q[0]*abs(c['ps'][MODELS[0]+':plain']-c['ps'][MODELS[1]+':plain']) >= q[1])
    grid('reader support rescues abstain band', list(itertools.product(TH, [.05, .1, .2], [.25, .5, .75])),
         lambda c, q: c['base'] >= q[0]+q[1] or (c['base'] >= q[0]-q[1] and c['votes'] >= q[2]))
    grid('judge reason penalty and correction bonus', list(itertools.product([0, .1, .25, .5], [0, .1, .25], TH)),
         lambda c, q: c['base']-q[0]*c['negative']+q[1]*c['positive'] >= q[2])
    grid('repeat stability blended with panel', list(itertools.product([.2, .4, .6, .8], TH)),
         lambda c, q: (1-q[0])*c['base']+q[0]*c['repeat'] >= q[1])
    grid('robust median across four plain judges', TH,
         lambda c, t: statistics.median(c['ps'][m+':plain'] for m in MODELS) >= t)
    grid('plain and defence geometric fusion', list(itertools.product([.25, .5, .75], TH)),
         lambda c, q: c['base']**q[0] * statistics.mean(c['ps'][m+':defend'] for m in MODELS[:2])**(1-q[0]) >= q[1])

    # Rank by confidence within an unlabeled lesson; ties share the same midrank.
    ranks = {}
    for d, cs in dataset.items():
        for c in cs:
            ranks[(d, c['id'])] = statistics.mean(
                sum((x['ps'][m+':plain'] < c['ps'][m+':plain']) + .5*(x['ps'][m+':plain'] == c['ps'][m+':plain']) for x in cs)/len(cs)
                for m in MODELS)
    def rank_apply(t, d):
        return predictions([c for c in dataset[d] if ranks[(d,c['id'])] >= t])
    run('four-judge percentile rank fusion', lambda tr,k: best(TH,rank_apply,tr,k), rank_apply,dataset,results)

    def reliability_apply(q, d):
        selected = []
        for c in dataset[d]:
            weights = q['weights'][c['signal']]
            total = sum(weights.values())
            support = sum(weights[t] for t in c['tags']) / total if total else c['votes']
            if .5*c['base']+.5*support >= q['threshold']:
                selected.append(c)
        return predictions(selected)

    def reliability_choose(train, keys):
        all_signals = sorted({c['signal'] for cs in dataset.values() for c in cs})
        weights = {}
        for sig in all_signals:
            weights[sig] = {}
            for tag in POOL:
                cs = [(d,c) for d in train for c in dataset[d] if c['signal']==sig and tag in c['tags']]
                # Beta(2,2) smoothing prevents tiny signal groups from dominating.
                weights[sig][tag] = (2 + sum(R.match(predictions([c]),keys[d]) for d,c in cs))/(4+len(cs))
        configs = [dict(weights=weights,threshold=t) for t in TH]
        return best(configs,reliability_apply,train,keys)
    run('signal-conditioned reader reliability blend',reliability_choose,reliability_apply,dataset,results)

    def features(c, kind):
        x = [1., c['base'], c['votes'], c['repeat'], float(c['fam']=='grammar'), c['negative'], c['positive']]
        if kind == 'family':
            x += [c['base']*float(c['fam']=='grammar'), c['votes']*float(c['fam']=='grammar')]
        return x

    for kind in ['compact', 'family']:
        def apply(q,d,kind=kind):
            return predictions([c for c in dataset[d] if E.prob(q['weights'],features(c,kind)) >= q['threshold']])
        def choose(train,keys,kind=kind,apply=apply):
            X = [features(c,kind) for d in train for c in dataset[d]]
            Y = [float(R.match(predictions([c]),keys[d])) for d in train for c in dataset[d]]
            configs = []
            for l2 in [1.,10.,100.]:
                weights = E.fit(X,Y,l2=l2)
                configs.extend(dict(weights=weights,threshold=t,l2=l2) for t in TH)
            return best(configs,apply,train,keys)
        run(f'{kind} regularized reason and repeat stack',choose,apply,dataset,results)

    # Input drift invalidates the experiment rather than quietly changing its target.
    assert all(sha(ROOT/p) == digest for p,digest in INPUTS.items()), 'Input changed during experiment'
    manifest = dict(protocol='LOLO; train on two lessons; pooled one-to-one reader_tiers scoring',
                    drop='asked,none', input_sha256=INPUTS,
                    candidate_counts={d:len(cs) for d,cs in dataset.items()}, results=results)
    (OUT/'codex-results.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    with (OUT/'attempts.jsonl').open('a',encoding='utf-8') as f:
        for record in results:
            f.write(json.dumps(record)+'\n')
    print('Saved codex-results.json; appended all experiments to attempts.jsonl.',flush=True)


if __name__ == '__main__':
    main()
