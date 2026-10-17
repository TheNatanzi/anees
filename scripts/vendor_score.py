"""Score vendor + Claude reader runs against the frozen grade-book keys (reader_tiers.match: same family, 15 s).
    python -I vendor_score.py --repo <worktree> --dates 2026-10-10 [--pairs]"""
import argparse, glob, json, os, sys, collections

ap = argparse.ArgumentParser()
ap.add_argument('--repo', required=True); ap.add_argument('--dates', required=True); ap.add_argument('--pairs', action='store_true')
ap.add_argument('--only', default='')
a = ap.parse_args()
sys.path.insert(0, os.path.join(a.repo, 'scripts'))
os.chdir(a.repo)
import reader_tiers as R

dates = a.dates.split(',')
RUNS = os.path.join('data', 'lesson-work', 'reader-tiers', 'runs')
tags = collections.defaultdict(dict)
for f in glob.glob(os.path.join(RUNS, '*-run1.json')):
    b = os.path.basename(f)
    d, rest = b.split('.', 1)
    tag = rest[:-len('-run1.json')]
    if d in dates and not tag.startswith('smoke'):
        tags[tag][d] = R.load_run(d, tag, 1)
tags = {t: v for t, v in tags.items() if all(d in v for d in dates)}
if a.only:
    tags = {t: v for t, v in tags.items() if t in a.only.split(',')}
keys = {d: R.key_slips(d) for d in dates}


def score(rows_by_date):
    m = p = k = 0
    per = {}
    for d in dates:
        pr = R.predicted(rows_by_date[d]); mm = R.match(pr, keys[d])
        m += mm; p += len(pr); k += len(keys[d]); per[d] = R.prf(mm, len(pr), len(keys[d]))['f05']
    return dict(R.prf(m, p, k), per=per)


def agree(r1, r2):
    """Rows of r1 that r2 also flagged (same family, within 15 s): the both-agree gate (PR-25)."""
    p2 = R.predicted(r2)
    out = []
    for r in r1 or []:
        f = R.family(r.get('kind'), r.get('tier'))
        try:
            t = R.sec(r.get('t'))
        except Exception:
            continue
        if f and any(q[0] == f and abs(q[1] - t) <= R.MATCH_S for q in p2):
            out.append(r)
    return out


res = {t: score({d: v[d]['rows'] for d in dates}) for t, v in tags.items()}
print('key slips', sum(len(keys[d]) for d in dates))
for t, s in sorted(res.items(), key=lambda x: -x[1]['f05']):
    print(f"{t:38s} F0.5 {s['f05']:5.1f}  P {s['precision']:5.1f}  R {s['recall']:5.1f}  caught {s['matched']:3d}/{s['key']}  flags {s['predicted']}")
if a.pairs:
    print('\nPAIRS (both agree)')
    pr = {}
    ts = sorted(tags)
    for i, x in enumerate(ts):
        for y in ts[i + 1:]:
            pr[(x, y)] = score({d: agree(tags[x][d]['rows'], tags[y][d]['rows']) for d in dates})
    for (x, y), s in sorted(pr.items(), key=lambda kv: -kv[1]['f05'])[:15]:
        print(f"{x} + {y}: F0.5 {s['f05']:.1f} P {s['precision']:.1f} R {s['recall']:.1f} caught {s['matched']}/{s['key']} flags {s['predicted']} per {s['per']}")
json.dump({'dates': dates, 'single': res}, open(os.path.join(RUNS, 'vendor-score-' + '_'.join(dates) + '.json'), 'w', encoding='utf-8'), indent=1)
