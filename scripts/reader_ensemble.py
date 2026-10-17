"""Overnight 2026-10-17 (Medi: "loop it overnight til you can find a 90% score"): ensemble methods over slip-reader runs,
always scored leave-one-lesson-out (tune on 2 lessons, score the 3rd) with scripts/reader_tiers.py's own matcher.

Candidates = clusters of flags from all readers (same family vocab/grammar, within MATCH_S of the cluster's first flag).
Each cluster carries features (which readers flagged it, how many, kinds, signal words) and a label (matches a key slip).

    python -I scripts/reader_ensemble.py vote   --readers a,b,c        # every k-of-n, LOLO picks k
    python -I scripts/reader_ensemble.py search --pool a,b,c,d,e,f     # LOLO over reader subsets x k
    python -I scripts/reader_ensemble.py stack  --pool a,b,c,d,e,f     # logistic regression on cluster features, LOLO
"""
import argparse, itertools, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(REPO)
import reader_tiers as R

LESSONS = list(R.LESSONS)
OUT = os.path.join(REPO, 'data', 'lesson-work', 'reader-tiers', 'overnight-2026-10-17')
os.makedirs(OUT, exist_ok=True)


def rows(tag, d):
    r = R.load_run(d, tag, 1)
    return (r or {}).get('rows') or []


DROP = set(filter(None, os.environ.get('RE_DROP', '').split(',')))   # tutor-signal types never scored as a slip by the grade book


def sig(r):
    return (str(r.get('signal') or 'none').split() or ['none'])[0].strip(',;').lower()


def flags(tag, d):
    out = []
    for r in rows(tag, d):
        if sig(r) in DROP:
            continue
        f = R.family(r.get('kind'), r.get('tier'))
        try:
            t = float(R.sec(r.get('t')))
        except Exception:
            continue
        if f:
            out.append({'fam': f, 't': t, 'tag': tag, 'row': r})
    return out


def clusters(tags, d):
    """Greedy time clustering per family: a flag joins a cluster when within MATCH_S of its anchor."""
    allf = sorted((x for t in tags for x in flags(t, d)), key=lambda x: (x['fam'], x['t']))
    cl = []
    for x in allf:
        c = next((c for c in cl if c['fam'] == x['fam'] and abs(c['t'] - x['t']) <= R.MATCH_S), None)
        if c is None:
            cl.append({'fam': x['fam'], 't': x['t'], 'members': [x], 'tags': {x['tag']}})
        else:
            c['members'].append(x); c['tags'].add(x['tag'])
    return cl


def score_pred(preds_by_lesson, lessons):
    m = p = k = 0
    for d in lessons:
        ks = R.key_slips(d); pr = preds_by_lesson[d]
        m += R.match(pr, ks); p += len(pr); k += len(ks)
    return R.prf(m, p, k)


def pred_of(cl):
    return [(c['fam'], c['t']) for c in cl]


def vote_pred(tags, k, d):
    return pred_of([c for c in clusters(tags, d) if len(c['tags']) >= k])


def lolo(choose, apply):
    """choose(train_lessons) -> params ; apply(params, lesson) -> preds. Returns held-out pooled score + per-fold."""
    preds, folds = {}, []
    for test in LESSONS:
        train = [d for d in LESSONS if d != test]
        params = choose(train)
        preds[test] = apply(params, test)
        folds.append({'test': test, 'params': params, 'f05': R.prf(R.match(preds[test], R.key_slips(test)), len(preds[test]), len(R.key_slips(test)))['f05']})
    return score_pred(preds, LESSONS), folds


def log(method, s, folds, extra=None):
    rec = {'method': method, 'heldout': s, 'folds': folds, **(extra or {})}
    with open(os.path.join(OUT, 'attempts.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + '\n')
    print(f"{method:60s} held-out F0.5 {s['f05']:5.1f}  P {s['precision']:5.1f}  R {s['recall']:5.1f}  "
          f"({s['matched']}/{s['key']}, {s['predicted']} flags)  folds {[round(f['f05'], 1) for f in folds]}")


def cmd_vote(readers):
    def choose(train):
        return max(range(1, len(readers) + 1), key=lambda k: score_pred({d: vote_pred(readers, k, d) for d in train}, train)['f05'])
    s, folds = lolo(choose, lambda k, d: vote_pred(readers, k, d))
    log('vote k-of-n [' + ','.join(readers) + ']', s, folds)


def cmd_search(pool, max_size=5):
    subsets = [list(c) for n in range(1, max_size + 1) for c in itertools.combinations(pool, n)]
    cache = {}

    def P(sub, k, d):
        key = (tuple(sub), k, d)
        if key not in cache:
            cache[key] = vote_pred(sub, k, d)
        return cache[key]

    def choose(train):
        best = max(((sub, k) for sub in subsets for k in range(1, len(sub) + 1)),
                   key=lambda sk: score_pred({d: P(sk[0], sk[1], d) for d in train}, train)['f05'])
        return best
    s, folds = lolo(choose, lambda sk, d: P(sk[0], sk[1], d))
    log('search subset x k over pool [' + ','.join(pool) + ']', s, folds)


# ------------------------------------------------------------------ stacking (logistic regression, no numpy needed)
SIGNAL_WORDS = ('recast', 'corrected', 'amal', 'fix', 'said', 'no', 'repeat', 'chat')


def feats(c, pool):
    x = [1.0, len(c['tags']) / len(pool)] + [1.0 if t in c['tags'] else 0.0 for t in pool]
    x.append(1.0 if c['fam'] == 'grammar' else 0.0)
    sig = ' '.join(str(m['row'].get('signal') or '') + ' ' + str(m['row'].get('kind') or '') for m in c['members']).lower()
    x.append(1.0 if any(m['row'].get('kind', '').endswith('-B') or m['row'].get('kind') == 'grammar-B' for m in c['members']) else 0.0)
    x.append(1.0 if 'none' in sig else 0.0)
    conf = [str(m['row'].get('confidence') or '').lower() for m in c['members']]
    x.append(sum(1 for v in conf if v == 'high') / max(1, len(conf)))
    x.append(sum(1 for v in conf if v == 'low') / max(1, len(conf)))
    return x


def labelled(pool, d):
    cl = clusters(pool, d)
    ks = R.key_slips(d)
    used, out = set(), []
    for c in sorted(cl, key=lambda c: -len(c['tags'])):
        j = next((i for i, k in enumerate(ks) if i not in used and k[0] == c['fam'] and abs(k[1] - c['t']) <= R.MATCH_S), None)
        y = 0.0
        if j is not None:
            used.add(j); y = 1.0
        out.append((c, feats(c, pool), y))
    return out


def fit(X, Y, l2=1.0, iters=400, lr=0.3):
    w = [0.0] * len(X[0])
    for _ in range(iters):
        g = [l2 * wi / len(X) for wi in w]; g[0] = 0.0
        for x, y in zip(X, Y):
            p = 1 / (1 + math.exp(-sum(a * b for a, b in zip(w, x))))
            for i, xi in enumerate(x):
                g[i] += (p - y) * xi / len(X)
        w = [wi - lr * gi for wi, gi in zip(w, g)]
    return w


def prob(w, x):
    return 1 / (1 + math.exp(-sum(a * b for a, b in zip(w, x))))


def cmd_stack(pool):
    data = {d: labelled(pool, d) for d in LESSONS}

    def choose(train):
        X = [x for d in train for _, x, _ in data[d]]; Y = [y for d in train for _, _, y in data[d]]
        w = fit(X, Y)
        best = max((t / 20 for t in range(4, 19)), key=lambda th: score_pred(
            {d: [(c['fam'], c['t']) for c, x, _ in data[d] if prob(w, x) >= th] for d in train}, train)['f05'])
        return (w, best)
    s, folds = lolo(choose, lambda wt, d: [(c['fam'], c['t']) for c, x, _ in data[d] if prob(wt[0], x) >= wt[1]])
    for f in folds:
        f['params'] = {'threshold': f['params'][1]}
    log('stack logistic [' + ','.join(pool) + ']', s, folds)


def cmd_ceiling(pool):
    """Best possible from these readers' candidates: every matched cluster kept, nothing else (an oracle)."""
    pr = {d: [(c['fam'], c['t']) for c, x, y in labelled(pool, d) if y] for d in LESSONS}
    s = score_pred(pr, LESSONS)
    print(f"oracle on the union of [{','.join(pool)}]: recall {s['recall']:.1f} ({s['matched']}/{s['key']}) - the most any filter could catch")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['vote', 'search', 'stack', 'ceiling'])
    ap.add_argument('--readers', default=''); ap.add_argument('--pool', default=''); ap.add_argument('--max-size', type=int, default=5)
    a = ap.parse_args()
    if a.cmd == 'vote':
        cmd_vote(a.readers.split(','))
    elif a.cmd == 'search':
        cmd_search(a.pool.split(','), a.max_size)
    elif a.cmd == 'stack':
        cmd_stack(a.pool.split(','))
    else:
        cmd_ceiling(a.pool.split(','))
