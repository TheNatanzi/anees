# -*- coding: utf-8 -*-
"""The slip-reader model-tier test (plan/PIPELINE-TEST-PROTOCOL.md section 4, "Readers: tier x effort"). SET UP ONLY:
`run` needs Medi's yes on the estimate (Medi 2026-10-14: "...then set up the Fable/Opus/Sonnet/Haiku test").

Same frozen reader prompt (data/lesson-work/full-audit/READER-BRIEF.md + the production reader instruction), same pinned
effort, four Claude tiers, 3 runs each, on the 3 keyed lessons (10-08, 10-09, 10-10); plus a Haiku x3 vote built from
the three Haiku runs (no extra call). Hearing is taken out: every reader gets the KEY transcript (Medi's lines as his
review left them; the tutor's and chat lines from the page), so only the reader differs.

    python scripts/reader_tiers.py prep                       # transcripts + freeze (hashes of brief, prompt, transcripts)
    python scripts/reader_tiers.py estimate                   # dollars per model, from the production readers' token use
    python scripts/reader_tiers.py run <model> <n> [--lesson D] [--turns N] [--yes]   # one claude -p read (PAID)
    python scripts/reader_tiers.py score [--json]             # precision / recall / F0.5 per model, + Haiku x3 vote

Scoring: a reader's predicted slips = its rows of every kind that can become a ✗ (vocab-A / grammar, voiced; vocab-B /
grammar-B, let pass, which become a ✗ when the tutor rules on them; never a tier-3 vocab row); the key's slips = the ✗ chips of the frozen grade-book key (review-grades/<date>.json).
A prediction matches a key slip of the same family (vocab / grammar) whose line starts within 15 s; one-to-one, nearest
first. precision = matched / predicted, recall = matched / key slips, F0.5 = 1.25PR / (0.25P + R) (precision weighs
double: a fake slip costs Medi more than a missed one). Per the protocol, tiers are compared only on all 3 lessons pooled.
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

DIR = os.path.join(REPO, "data", "lesson-work", "reader-tiers")
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
LESSONS = ("2026-10-08", "2026-10-09", "2026-10-10")
MODELS = {"fable": "claude-fable-5-1", "opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
EFFORT = "high"                      # pinned for every tier (the CLI's --effort)
RUNS = 3
MATCH_S = 15.0
# $ per 1M tokens: input, output, cache read, cache write (5 min = 1.25 x input). Anthropic list prices, claude-api skill
# table cached 2026-10-06; Haiku 5.5's cache read is not in that table: its input price is used (an over-estimate).
PRICE = {"claude-fable-5-1": (10.0, 50.0, 0.25, 12.5), "claude-opus-5-5": (4.0, 20.0, 0.20, 5.0),
         "claude-sonnet-5-5": (2.0, 10.0, 0.20, 2.5), "claude-haiku-5-5": (0.10, 0.50, 0.10, 0.125)}
CLAUDE = os.environ.get("ANEES_CLAUDE", "claude")


def mmss(t):
    t = int(round(float(t)))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)


def key_of(date):
    g = BC.J(os.path.join(REPO, "data", "lesson-work", "review-grades", date + ".json"))
    if not g:
        raise SystemExit("no frozen key for %s" % date)
    return g["key"]


def transcript(date, turns=None):
    """The key transcript: the page's turns, Medi's lines replaced by the key's text (his review)."""
    page = BC.J(os.path.join(REPO, "docs", "data", "lessons", date + ".json")) or {}
    key = key_of(date)["lines"]
    T = page.get("turns") or []
    if turns:
        T = T[:turns]
    out = ["# Lesson %s - %d turns on the lesson clock (mm:ss = seconds on the page audio)" % (date, len(T)), ""]
    for u in T:
        who = u.get("who")
        tag = ("CHAT %s" % u.get("typed_by", "")).strip() if who == "chat" else who
        text = key.get("%.2f" % float(u["t"]), u.get("text") or "") if who == "Medi" else (u.get("engine") or u.get("text") or "")
        out.append("[%s] %s: %s" % (mmss(u["t"]), tag, text))
    return "\n".join(out) + "\n", (float(T[-1]["t"]) if T else 0.0)


def tpath(date, suffix=""):
    return os.path.join(DIR, date + suffix + ".txt")


def prompt_for(date, model, n, suffix=""):
    out = os.path.join(DIR, "runs", "%s%s.%s-run%d.json" % (date, suffix, model, n))
    return (f"Repo: {REPO}. Read {WORK}\\READER-BRIEF.md first and follow it exactly. You are reader r1 for lesson {date}. "
            f"Transcript: {os.path.relpath(tpath(date, suffix), REPO)}. Read the WHOLE file in order. Write your JSON to "
            f"{out} (reader \"r1\"). Do not open any other reader's file, any file under data/lesson-work/full-audit other "
            f"than the brief and the files it names, any review-grades file, or the sweep plan. Reply with only your counts line."), out


def prep():
    man = {"frozen": time.strftime("%Y-%m-%dT%H:%M:%S"), "effort": EFFORT, "models": MODELS, "runs": RUNS, "match_s": MATCH_S,
           "brief_sha256": BC.sha_file(os.path.join(WORK, "READER-BRIEF.md")),
           "prompt_template_sha256": BC.sha_text(prompt_for("D", "m", 1)[0]), "lessons": {}}
    for d in LESSONS:
        txt, _ = transcript(d)
        os.makedirs(DIR, exist_ok=True)
        with open(tpath(d), "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        man["lessons"][d] = {"transcript_sha256": BC.sha_file(tpath(d)), "key_slips": len(key_of(d)["slips"])}
    BC.W(os.path.join(DIR, "manifest.json"), man)
    print(json.dumps(man["lessons"]))


def check_frozen():
    man = BC.J(os.path.join(DIR, "manifest.json"))
    if not man:
        raise SystemExit("run `prep` first")
    if BC.sha_file(os.path.join(WORK, "READER-BRIEF.md")) != man["brief_sha256"]:
        raise SystemExit("READER-BRIEF.md changed since the freeze: re-prep (and every earlier run is void)")
    for d, v in man["lessons"].items():
        if BC.sha_file(tpath(d)) != v["transcript_sha256"]:
            raise SystemExit("%s transcript changed since the freeze" % d)
    return man


# ------------------------------------------------------------------ money

PROFILE = None


def token_profile():
    """Mean tokens of one production reader read (data/runs full_audit.reader, Opus): output, cache read, cache write."""
    global PROFILE
    if PROFILE:
        return PROFILE
    rows = []
    for f in sorted(os.listdir(os.path.join(REPO, "data", "runs"))):
        if not f.endswith(".jsonl"):
            continue
        for line in open(os.path.join(REPO, "data", "runs", f), encoding="utf-8"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            u = d.get("usage") or {}
            if d.get("step") == "full_audit.reader" and u.get("output_tokens"):
                rows.append((u.get("input_tokens") or 0, u["output_tokens"], u.get("cache_read_input_tokens") or 0,
                             u.get("cache_creation_input_tokens") or 0, d.get("cost_usd") or 0))
    rows = rows[-24:]
    if not rows:
        PROFILE = (100, 26000, 900000, 100000, 1.5, 0)
    else:
        PROFILE = tuple(sum(r[k] for r in rows) / len(rows) for k in range(5)) + (len(rows),)
    return PROFILE


def per_read(model):
    i, o, cr, cw, _, _ = token_profile()
    p = PRICE[model]
    return (i * p[0] + o * p[1] + cr * p[2] + cw * p[3]) / 1e6


def measured():
    """[(model, turns, $)] of the reads already run (data/runs reader_tiers.read, the CLI's own cost)."""
    out = []
    p = os.path.join(REPO, "data", "runs")
    for f in sorted(os.listdir(p)):
        if f.endswith(".jsonl"):
            for line in open(os.path.join(p, f), encoding="utf-8"):
                if '"reader_tiers.read"' in line:
                    d = json.loads(line)
                    out.append((d.get("gen_ai.request.model"), (d.get("params") or {}).get("turns") or "all", d.get("cost_usd") or 0.0))
    return out


def estimate(out=print):
    i, o, cr, cw, usd, n = token_profile()
    out("Token use of one production read (mean of %d Opus reads): %.0f output, %.0f cache read, %.0f cache write (measured $%.2f)" % (n, o, cr, cw, usd))
    tot = 0.0
    rows = {}
    for name, m in MODELS.items():
        one = per_read(m)
        k = one * RUNS * len(LESSONS)
        rows[name] = {"per_read": round(one, 3), "reads": RUNS * len(LESSONS), "usd": round(k, 2)}
        tot += k
        out("  %-7s %-18s $%.2f a read x %d reads = $%.2f" % (name, m, one, RUNS * len(LESSONS), k))
    out("  Haiku x3 vote: built from the 3 Haiku runs, $0 more")
    out("Total about $%.2f at list prices (same token use for every tier: a higher tier that thinks longer costs more)" % tot)
    smoke = measured()
    if smoke:
        out("MEASURED: %s - the CLI's own cost runs far above the list-price figure; calibrate first (1 full read per tier on one "
            "lesson) before the 36-read run" % "; ".join("%s %s turns $%.2f" % x for x in smoke))
    return {"rows": rows, "total_usd": round(tot, 2)}


# ------------------------------------------------------------------ one read

def spent_reads():
    return round(sum(c for _, _, c in measured()), 4)


def run(model, n, lesson=None, turns=None, yes=False, log=print):
    if not yes:
        raise SystemExit("paid: needs Medi's yes on the estimate (`estimate`); pass --yes only after he said yes")
    lim = (BC.J(os.path.join(DIR, "spend.json")) or {}).get("limit_usd")
    if lim is None:
        raise SystemExit("no limit in data/lesson-work/reader-tiers/spend.json (Medi's number) - nothing run")
    mid = MODELS[model]
    dates = [lesson] if lesson else list(LESSONS)
    for d in dates:
        suffix = ""
        if turns:                                          # the smoke test: a short excerpt, its own file, never scored with the rest
            suffix = ".smoke%d" % turns
            txt, _ = transcript(d, turns)
            with open(tpath(d, suffix), "w", encoding="utf-8", newline="\n") as f:
                f.write(txt)
        else:
            check_frozen()
        if spent_reads() + per_read(mid) > float(lim):
            raise SystemExit("reader-tier limit $%.2f: $%.2f spent + ~$%.2f for this read - stopped" % (float(lim), spent_reads(), per_read(mid)))
        prompt, out = prompt_for(d, model, n, suffix)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cmd = [CLAUDE, "-p", prompt, "--output-format", "json", "--permission-mode", "bypassPermissions", "--add-dir", REPO,
               "--model", mid, "--effort", EFFORT]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=3600)
        import track
        parsed = track.parse_claude_output(r.stdout)
        track.log_run("reader_tiers.read", d, kind="eval", provider="anthropic", request_model=mid,
                      response_model=parsed.get("response_model") or mid, cost_usd=parsed.get("cost_usd"),
                      params={"rule": "PR-23", "effort": EFFORT, "run": n, "turns": turns, "usage": parsed.get("usage"),
                              "models": parsed.get("models"),
                              "prompt_sha": BC.sha_text(prompt)})
        log("%s %s run %d: exit %d, %.0f s, $%s, %s" % (d, model, n, r.returncode, time.time() - t0, parsed.get("cost_usd"),
                                                      "wrote" if os.path.exists(out) else "NO OUTPUT FILE"))


# ------------------------------------------------------------------ the score

def family(kind, tier=None):
    """vocab / grammar for every row that could become a ✗: voiced fixes (A) and let-pass rows (B), which become a ✗
    when the tutor rules on them (10-10 00:17 'amal-ruling'). A tier-3 vocab row (switching to English) never does."""
    k = str(kind or "")
    if k.startswith("vocab") and tier != 3:
        return "vocab"
    return "grammar" if k.startswith("grammar") else None


def sec(mm):
    p = [int(x) for x in str(mm).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def predicted(rows, until=None):
    out = []
    for r in rows or []:
        f = family(r.get("kind"), r.get("tier"))
        try:
            t = sec(r.get("t"))
        except (ValueError, TypeError, IndexError):
            continue
        if f and (until is None or t <= until):
            out.append((f, float(t)))
    return out


def key_slips(date, until=None):
    return [(s["k"], float(s["i"])) for s in key_of(date)["slips"] if until is None or float(s["i"]) <= until]


def match(pred, key):
    """One-to-one, nearest first, same family within MATCH_S."""
    pairs = sorted((abs(p[1] - k[1]), a, b) for a, p in enumerate(pred) for b, k in enumerate(key)
                   if p[0] == k[0] and abs(p[1] - k[1]) <= MATCH_S)
    used_p, used_k = set(), set()
    for _, a, b in pairs:
        if a not in used_p and b not in used_k:
            used_p.add(a)
            used_k.add(b)
    return len(used_p)


def prf(m, npred, nkey):
    P = m / npred if npred else 0.0
    R = m / nkey if nkey else 0.0
    F = 1.25 * P * R / (0.25 * P + R) if (P + R) else 0.0
    return {"matched": m, "predicted": npred, "key": nkey, "precision": round(100 * P, 1), "recall": round(100 * R, 1), "f05": round(100 * F, 1)}


def vote(runs):
    """Haiku x3: a predicted slip kept when 2 of the 3 runs have one of the same family within MATCH_S (one per cluster)."""
    flat = sorted((p for r in runs for p in r), key=lambda x: x[1])
    kept = []
    for p in flat:
        n = sum(1 for r in runs if any(q[0] == p[0] and abs(q[1] - p[1]) <= MATCH_S for q in r))
        if n * 2 > len(runs) and not any(k[0] == p[0] and abs(k[1] - p[1]) <= MATCH_S for k in kept):
            kept.append(p)
    return kept


def load_run(date, model, n, suffix=""):
    return BC.J(os.path.join(DIR, "runs", "%s%s.%s-run%d.json" % (date, suffix, model, n)))


def score(suffix="", until=None):
    res = {}
    for model in list(MODELS) + ["haiku-x3"]:
        tot = {"matched": 0, "predicted": 0, "key": 0}
        per = {}
        for d in LESSONS:
            ks = key_slips(d, until.get(d) if until else None)
            if model == "haiku-x3":
                runs = [load_run(d, "haiku", n, suffix) for n in range(1, RUNS + 1)]
                if not all(runs):
                    continue
                preds = [vote([predicted(r.get("rows"), until.get(d) if until else None) for r in runs])]
            else:
                preds = [predicted(r.get("rows"), until.get(d) if until else None) for r in
                         (load_run(d, model, n, suffix) for n in range(1, RUNS + 1)) if r]
            if len(preds) < (1 if model == "haiku-x3" else RUNS):   # a tier is compared only on all runs of all 3 lessons
                per = {}
                break
            for p in preds:
                m = match(p, ks)
                tot["matched"] += m
                tot["predicted"] += len(p)
                tot["key"] += len(ks)
            per[d] = len(preds)
        if per:
            res[model] = dict(prf(tot["matched"], tot["predicted"], tot["key"]), runs=per)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reader_tiers.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    sub.add_parser("estimate")
    r = sub.add_parser("run")
    r.add_argument("model", choices=sorted(MODELS))
    r.add_argument("n", type=int)
    r.add_argument("--lesson")
    r.add_argument("--turns", type=int)
    r.add_argument("--yes", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "prep":
        prep()
    elif a.cmd == "estimate":
        estimate()
    elif a.cmd == "run":
        run(a.model, a.n, a.lesson, a.turns, a.yes)
    elif a.cmd == "score":
        res = score()
        if a.json:
            print(json.dumps(res, indent=1))
        else:
            for m, v in res.items():
                print("%-9s precision %5.1f  recall %5.1f  F0.5 %5.1f  (%d matched of %d predicted, %d key slips; runs %s)" % (
                    m, v["precision"], v["recall"], v["f05"], v["matched"], v["predicted"], v["key"], v["runs"]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
