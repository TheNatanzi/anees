# -*- coding: utf-8 -*-
"""Score the grammar auditor against the hand-labelled gold set.

    python scripts/score_grammar_detector.py            # re-run the auditor, then score
    python scripts/score_grammar_detector.py --no-run   # score the audit file as it is

recall     = gold grammar corrections the auditor found / all gold grammar corrections
precision  = auditor events that sit on a real correction (any kind) / auditor events
bucket acc = found gold grammar corrections filed under the same bucket

A match is one auditor event and one gold row on the same date, the event
inside the gold row's span (his first wrong try .. her fix) give or take TOL
seconds, about at least one of the same words of his. Paired one-to-one:
same bucket first, then nearest.
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


def same_words(g, d):
    """The detection is about the words the gold row is about (not just the same minute)."""
    if g.get("medi_text_missing") or d.get("match") == "english":
        return True  # an English rule-name is tied to the moment, not to one word
    sys.path.insert(0, HERE)
    from xscript import tokens, bare, is_english
    gs = {bare(w) for w in tokens(g["said"]) if not is_english(w) and len(bare(w)) >= 1}
    ds = {bare(w) for w in tokens(d.get("said", "")) if not is_english(w) and len(bare(w)) >= 1}
    return bool(gs & ds)


def match(gold, det):
    """One-to-one, nearest first. Same words, same span."""
    pairs = []
    for gi, g in enumerate(gold):
        lo, hi = g.get("t_from", g["t"]) - TOL, max(g.get("t_to", g["t"]), g["t"]) + TOL
        for di, d in enumerate(det):
            if g["date"] == d["date"] and lo <= d["t"] <= hi and same_words(g, d):
                dt = 0 if g.get("t_from", g["t"]) <= d["t"] <= g.get("t_to", g["t"]) else abs(g["t"] - d["t"])
                # a same-bucket pairing wins over a nearer wrong-bucket one
                pairs.append((d.get("bucket") != g["bucket"], dt, gi, di))
    pairs.sort()
    pairs = [(dt, gi, di) for _, dt, gi, di in pairs]
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


def score(verbose=True, split=None, tiers=None, gold=None):
    """split: 'tuned' | 'heldout' | None (all). tiers: confidence levels to count (None = all).
    gold: a frozen gold id from gold/manifest.json (e.g. 'grammar@v1-heldout'); None = the live docs file."""
    gold_all = load_gold(gold) if gold else \
        json.load(open(os.path.join(DOCS, "grammar-goldset.json"), encoding="utf-8"))["events"]
    if split:
        gold_all = [g for g in gold_all if g.get("split", "tuned") == split]
    audit = json.load(open(os.path.join(DOCS, "grammar-audit.json"), encoding="utf-8"))
    dates = sorted({g["date"] for g in gold_all})
    det = [dict(e) for e in audit["events"] if e["date"] in dates and (not tiers or e.get("confidence") in tiers)]
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


def found_keys():
    gold_all = json.load(open(os.path.join(DOCS, "grammar-goldset.json"), encoding="utf-8"))["events"]
    audit = json.load(open(os.path.join(DOCS, "grammar-audit.json"), encoding="utf-8"))
    det = [e for e in audit["events"] if e["date"] in {g["date"] for g in gold_all}]
    m = match(gold_all, det)
    return {"%s %s %s" % (g["date"][5:], g["mmss"], g["bucket"]) for i, g in enumerate(gold_all)
            if g["kind"] == "grammar" and i in m}


# ---------------------------------------------------------------- frozen gold sets + gold/history.jsonl
GOLD = os.path.join(HERE, "..", "gold")
GOLD_IDS = ("grammar@v1-tuned", "grammar@v1-heldout", "grammar@v2-audit")


def _sha(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def gold_entry(gold_id):
    man = json.load(open(os.path.join(GOLD, "manifest.json"), encoding="utf-8"))
    e = next((x for x in man["sets"] if x["id"] == gold_id), None)
    if not e or e.get("status") != "frozen":
        raise KeyError("%s is not a frozen set in gold/manifest.json" % gold_id)
    p = os.path.join(GOLD, e["path"])
    if _sha(p) != e["sha256"]:
        raise ValueError("%s changed since it was frozen (sha mismatch) - make a new version instead" % gold_id)
    return e, p


def _sec(s):
    v = 0.0
    for x in str(s).split(":"):
        v = v * 60 + float(x)
    return v


def load_gold(gold_id):
    """Events in the scorer's shape. grammar@v1-* are already that shape; grammar@v2-audit rows are adapted:
    his line at t, her fix at t_amal (span t..t_amal), words = what he said (or the wrong piece)."""
    e, p = gold_entry(gold_id)
    if p.endswith(".jsonl"):
        out = []
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if not r.get("t"):
                continue
            t = _sec(r["t"])
            ta = _sec(r["t_amal"]) if r.get("t_amal") else t
            out.append({"date": r["date"], "t": t, "t_from": t, "t_to": max(t, ta), "mmss": r["t"],
                        "bucket": r.get("bucket"), "kind": r.get("kind"), "channel": "chat" if r.get("chat") else "voice",
                        "said": r.get("medi_said") or r.get("wrong") or "", "correction": r.get("right") or "",
                        "medi_text_missing": False, "latin_script": False, "uid": r.get("uid")})
        return out
    return json.load(open(p, encoding="utf-8"))["events"]


def code_sha():
    """git HEAD + '-dirty' when this scorer or the detector output differ from HEAD."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", os.path.abspath(__file__),
                                os.path.join(DOCS, "grammar-audit.json")], cwd=HERE, capture_output=True, text=True).stdout.strip()
        return head + ("-dirty" if dirty else "")
    except Exception:
        return None


def history_line(gold_id, r, tiers=None, accepted=False):
    import datetime
    e, _ = gold_entry(gold_id)
    p_, r_ = r["precision"], r["recall"]
    return {"dataset": e["name"], "version": e["version"], "gold": gold_id, "sha": e["sha256"], "n": e["n"],
            "n_scored": r["gold_grammar"], "recall": r_, "precision": p_,
            "f1": round(2 * p_ * r_ / (p_ + r_), 3) if p_ + r_ else 0.0, "bucket_accuracy": r["bucket_accuracy"],
            "found": r["found"], "detected": r["detected"], "tiers": tiers,
            "detector_file": "docs/data/grammar-audit.json", "detector_sha": _sha(os.path.join(DOCS, "grammar-audit.json")),
            "scorer_sha": _sha(os.path.abspath(__file__)), "code_sha": code_sha(), "accepted": bool(accepted),
            "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}


def append_history(line):
    with open(os.path.join(GOLD, "history.jsonl"), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n")


def last_accepted(gold_id):
    """The last history line for this gold id marked accepted (the eval floor's baseline), or None."""
    p = os.path.join(GOLD, "history.jsonl")
    best = None
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                x = json.loads(line)
                if x.get("gold") == gold_id and x.get("accepted"):
                    best = x
    return best


def log_score(r, splits, tiers=None, ran_auditor=False):
    """One eval line in data/runs (scripts/track.py): dataset name/version/sha, n, recall, precision, f1 per split.
    Never raises."""
    try:
        import track
        gold_p, audit_p = os.path.join(DOCS, "grammar-goldset.json"), os.path.join(DOCS, "grammar-audit.json")
        gold = json.load(open(gold_p, encoding="utf-8"))
        f1 = lambda x: round(2 * x["precision"] * x["recall"] / (x["precision"] + x["recall"]), 3) if (x["precision"] + x["recall"]) else 0.0
        m = {"dataset": "grammar-goldset", "version": gold.get("updated"), "sha": track.file_sha(gold_p),
             "n": r["gold_grammar"], "recall": r["recall"], "precision": r["precision"], "f1": f1(r),
             "bucket_accuracy": r["bucket_accuracy"], "found": r["found"], "detected": r["detected"],
             "splits": {sp: {"n": x["gold_grammar"], "recall": x["recall"], "precision": x["precision"], "f1": f1(x),
                             "bucket_accuracy": x["bucket_accuracy"]} for sp, x in splits.items()}}
        track.log_run("grammar_detector.score", kind="eval", tool="scripts/score_grammar_detector.py",
                      inputs=[gold_p, audit_p], metrics=m,
                      params={"tolerance_s": TOL, "tiers": tiers, "ran_auditor": ran_auditor})
    except Exception:
        pass


if __name__ == "__main__":
    if "--no-run" not in sys.argv:
        run_auditor()
    tiers = None
    for a_ in sys.argv:
        if a_.startswith("--tiers="):
            tiers = a_.split("=", 1)[1].split(",")
    r = score(verbose="--quiet" not in sys.argv, tiers=tiers)
    print("\n" + json.dumps(r))
    splits = {sp: score(verbose=False, split=sp, tiers=tiers) for sp in ("tuned", "heldout")}
    for sp in ("tuned", "heldout"):
        print("%-8s %s" % (sp, json.dumps(splits[sp])))
    log_score(r, splits, tiers, ran_auditor="--no-run" not in sys.argv)      # data/runs eval line (never raises)
    # frozen gold versions -> gold/history.jsonl (--gold=ID[,ID] picks; --no-history skips; --accept = new floor baseline)
    golds = GOLD_IDS
    for a_ in sys.argv:
        if a_.startswith("--gold="):
            golds = a_.split("=", 1)[1].split(",")
    print()
    for gid in golds:
        h = history_line(gid, score(verbose=False, gold=gid, tiers=tiers), tiers, accepted="--accept" in sys.argv)
        print("%-20s recall %.3f  precision %.3f  f1 %.3f  (n %d)" % (gid, h["recall"], h["precision"], h["f1"], h["n_scored"]))
        if "--no-history" not in sys.argv:
            append_history(h)
    # what changed since the last run (scratch file, not committed)
    last = os.path.join(HERE, "_backups", "score_last_found.json")
    os.makedirs(os.path.dirname(last), exist_ok=True)
    now = sorted(found_keys())
    try:
        prev = set(json.load(open(last, encoding="utf-8")))
        gained, lost = sorted(set(now) - prev), sorted(prev - set(now))
        if gained or lost:
            print("since last run  + %s   - %s" % (gained, lost))
    except Exception:
        pass
    json.dump(now, open(last, "w", encoding="utf-8"))
