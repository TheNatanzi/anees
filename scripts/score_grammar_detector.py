# -*- coding: utf-8 -*-
"""Score the grammar auditor against the hand-labelled gold set.

    python scripts/score_grammar_detector.py            # re-run the auditor, then score
    python scripts/score_grammar_detector.py --no-run   # score the audit file as it is

recall     = gold grammar corrections the auditor found / all gold grammar corrections
precision  = auditor events that sit on a real correction (any kind) / auditor events
bucket acc = found gold grammar corrections filed under the same bucket

A match is one auditor event and one gold row on the same date within
TOL seconds of each other, paired one-to-one nearest first.
"""
import json, os, subprocess, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs", "data")
TOL = 20.0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def track_offset(date, who):
    sys.path.insert(0, HERE)
    from lesson_turns import track_offset as f
    return f(date, who)


def run_auditor():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(HERE, "audit_grammar_lessons.py")],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-4000:])
        sys.exit("auditor failed")


def match(gold, det):
    """One-to-one, nearest first."""
    pairs = []
    for gi, g in enumerate(gold):
        for di, d in enumerate(det):
            if g["date"] == d["date"]:
                dt = abs(g["t"] - d["t"])
                if dt <= TOL:
                    pairs.append((dt, gi, di))
    pairs.sort()
    used_g, used_d, out = set(), set(), {}
    for dt, gi, di in pairs:
        if gi in used_g or di in used_d:
            continue
        used_g.add(gi)
        used_d.add(di)
        out[gi] = di
    return out


def why_missed(g):
    if g.get("medi_text_missing"):
        return "his words never reached the transcript"
    if g.get("latin_script"):
        return "transcript wrote his Arabic in Latin letters"
    ch = g["channel"]
    if ch == "chat":
        return "she fixed it only in the Meet chat"
    if ch.startswith("english"):
        return "she explained it in English"
    return "Arabic voice correction the auditor did not pair"


def score(verbose=True):
    gold_all = json.load(open(os.path.join(DOCS, "grammar-goldset.json"), encoding="utf-8"))["events"]
    audit = json.load(open(os.path.join(DOCS, "grammar-audit.json"), encoding="utf-8"))
    dates = sorted({g["date"] for g in gold_all})
    det = [dict(e) for e in audit["events"] if e["date"] in dates]
    for e in det:
        # Older audit files kept each speaker on its own track clock.
        if not audit.get("aligned") and e.get("source", "").startswith("scribe"):
            e["t"] += track_offset(e["date"], "Medi")
    m = match(gold_all, det)
    grammar = [i for i, g in enumerate(gold_all) if g["kind"] == "grammar"]
    found = [i for i in grammar if i in m]
    right_bucket = [i for i in found if det[m[i]]["bucket"] == gold_all[i]["bucket"]]
    matched_det = set(m.values())
    recall = len(found) / len(grammar) if grammar else 0
    precision = len(matched_det) / len(det) if det else 0
    bacc = len(right_bucket) / len(found) if found else 0
    res = {"gold_grammar": len(grammar), "found": len(found), "detected": len(det),
           "detected_on_real": len(matched_det), "recall": round(recall, 3),
           "precision": round(precision, 3), "bucket_accuracy": round(bacc, 3)}
    if verbose:
        print("gold grammar corrections : %d" % len(grammar))
        for d in dates:
            gd = [i for i in grammar if gold_all[i]["date"] == d]
            fd = [i for i in gd if i in m]
            dd = [x for x in det if x["date"] == d]
            print("  %s  gold %2d  found %2d  auditor events %2d" % (d, len(gd), len(fd), len(dd)))
        print("RECALL     %.0f%%  (%d / %d)" % (100 * recall, len(found), len(grammar)))
        print("PRECISION  %.0f%%  (%d of %d auditor events sit on a real correction)"
              % (100 * precision, len(matched_det), len(det)))
        print("BUCKET ACC %.0f%%  (%d of %d found are in the right bucket)"
              % (100 * bacc, len(right_bucket), len(found)))
        kinds = Counter(gold_all[i]["kind"] for i in m if gold_all[i]["kind"] != "grammar")
        if kinds:
            print("  auditor events that were really:", dict(kinds))
        print("\nMISSED, by why:")
        by = defaultdict(list)
        for i in grammar:
            if i not in m:
                by[why_missed(gold_all[i])].append(gold_all[i])
        for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
            print("  %2d  %s" % (len(v), k))
            for g in v:
                print("        %s %s %-7s %s  =>  %s" % (g["date"][5:], g["mmss"], g["bucket"], g["said"][:40], g["correction"][:40]))
        wrong = [(gold_all[i], det[m[i]]) for i in found if i not in right_bucket]
        if wrong:
            print("\nFOUND, WRONG BUCKET:")
            for g, d in wrong:
                print("  %s %s gold %-7s auditor %-7s %s" % (g["date"][5:], g["mmss"], g["bucket"], d["bucket"], g["said"][:40]))
        fp = [d for i, d in enumerate(det) if i not in matched_det]
        if fp:
            print("\nAUDITOR EVENTS WITH NO REAL CORRECTION (%d):" % len(fp))
            for d in fp:
                print("  %s %s %-7s %s  =>  %s" % (d["date"][5:], d["mmss"], d["bucket"], d["said"][:40], d["recast"][:40]))
    return res


if __name__ == "__main__":
    if "--no-run" not in sys.argv:
        run_auditor()
    r = score()
    print("\n" + json.dumps(r))
