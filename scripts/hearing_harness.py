# -*- coding: utf-8 -*-
"""The hearing harness, SKELETON ONLY (plan/PIPELINE-TEST-PROTOCOL.md section 5; overnight brief 2026-10-10 section 5).

One script, the protocol's switches as flags, Medi's named setups A-F as presets. Every setup is scored the same way
against the same frozen key. This skeleton has NO paid path at all: it reads cached engine outputs, estimates what a
missing output would cost, scores versions that already exist, and builds the blind judge prompt. `run` refuses.

    python scripts/hearing_harness.py dry-run [2026-10-08] [--cell A | --proposer gemini --listens 1 ...] [--json]
    python scripts/hearing_harness.py score 2026-10-08 --version <file|@engine|@before> [--version ...] [--fallback engine]
    python scripts/hearing_harness.py judge-prompt --a "text" --b "text" [--context "..."] [--seed 7] [--item 85.25]
    python scripts/hearing_harness.py judge-prompt 2026-10-08 --line 85.25 [--seed 7]    # ElevenLabs raw vs Gemini run 1, blind
    python scripts/hearing_harness.py run ...          # refuses: "not built: paid runs need Medi's yes" (exit 2)

Switches (protocol section 5):
    --proposer  eleven | gemini | deepgram | cohere, comma list for several (who proposes the words)
    --cutter    eleven | align           (ElevenLabs word times / whole track + forced alignment)
    --settle    none | majority | second-listen | judge
    --judge     none | gemini | other    (always blind: version X / version Y, coin-swapped, no engine names)
    --context   none | his | full | masked   (what the Gemini line listener is given; masked = tutor's form hidden)
    --listens   0 | 1 | 2 | 3            (Gemini re-listens of his lines cut by the cutter; 2 = keep what both agree on,
                                         3 = 2-of-3; 0 = no line re-listen)

Scores (protocol sections 0 and 3), paired word by word against the frozen key:
    hit rate  of the Arabic words Medi really said in the key, the share the version wrote right
    FCR       of the key's real slips (a right form known), the share the version wrote in the tutor's correct form
The key: data/lesson-work/bench/<date>/truth.json (bench_freeze; scored with bench_score.score itself) when it exists,
else the grade book's freeze data/lesson-work/review-grades/<date>.json (key = the page after Medi's full review).

Engine outputs are cached by (audio hash, engine, model, prompt hash): cache_key().
"""
import argparse, ast, glob, hashlib, json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402  (pure: normaliser + file helpers, no network)

DEFAULT_DATE = "2026-10-08"
NOT_BUILT = "not built: paid runs need Medi's yes"

# ------------------------------------------------------------------ switches and cells

SWITCHES = {
    "proposer": ("eleven", "gemini", "deepgram", "cohere"),
    "cutter": ("eleven", "align"),
    "settle": ("none", "majority", "second-listen", "judge"),
    "judge": ("none", "gemini", "other"),
    "context": ("none", "his", "full", "masked"),
    "listens": (0, 1, 2, 3),
}

# Medi's named cells (protocol section 5, 2026-10-10). proposer is a tuple: several = they vote.
CELLS = {
    "A": {"proposer": ("eleven",), "cutter": "eleven", "settle": "majority", "judge": "none", "context": "full", "listens": 3,
          "about": "today: ElevenLabs proposes + cuts; Gemini re-hears his lines x3; 2-of-3; full context"},
    "B": {"proposer": ("gemini",), "cutter": "eleven", "settle": "none", "judge": "none", "context": "full", "listens": 0,
          "about": "Gemini proposes on the whole track; ElevenLabs only for timing"},
    "C": {"proposer": ("eleven", "deepgram"), "cutter": "eleven", "settle": "judge", "judge": "gemini", "context": "full", "listens": 1,
          "about": "ElevenLabs + Deepgram + Gemini vote; Gemini rules only where they disagree"},
    "D": {"proposer": ("gemini", "eleven"), "cutter": "align", "settle": "second-listen", "judge": "none", "context": "full", "listens": 0,
          "about": "Gemini first, ElevenLabs second opinion, a third listen breaks ties"},
    "E": {"proposer": ("eleven",), "cutter": "eleven", "settle": "none", "judge": "none", "context": "full", "listens": 2,
          "about": "Gemini 2 listens (keep words both agree on); pair with --listens 1"},
    "F": {"proposer": ("gemini", "eleven"), "cutter": "eleven", "settle": "second-listen", "judge": "gemini", "context": "full", "listens": 0,
          "about": "both do the whole lesson; disputed clips: BOTH listen again, then Gemini decides blind with both versions + reasons"},
}


def cell(name):
    """A copy of a named cell's switches."""
    c = CELLS[name.upper()]
    return {k: (tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in c.items()}


def validate(cfg):
    """Raise ValueError on a switch value the protocol does not name."""
    for p in cfg["proposer"]:
        if p not in SWITCHES["proposer"]:
            raise ValueError("proposer %r not in %s" % (p, SWITCHES["proposer"]))
    for k in ("cutter", "settle", "judge", "context", "listens"):
        if cfg[k] not in SWITCHES[k]:
            raise ValueError("%s %r not in %s" % (k, cfg[k], SWITCHES[k]))
    if cfg["settle"] == "judge" and cfg["judge"] == "none":
        raise ValueError("settle=judge needs --judge gemini|other")
    return cfg


def config_from_args(a):
    """--cell preset first, then any switch flag overrides it (an override makes the setup 'custom')."""
    cfg = cell(a.cell) if a.cell else cell("A")
    name = a.cell.upper() if a.cell else None
    over = False
    if a.proposer:
        cfg["proposer"] = tuple(x.strip() for x in a.proposer.split(",") if x.strip())
        over = True
    for k in ("cutter", "settle", "judge", "context", "listens"):
        v = getattr(a, k)
        if v is not None:
            cfg[k] = v
            over = True
    if over or not name:
        cfg["about"] = "custom setup" + (" (from cell %s)" % name if name else "")
        name = "custom" if (over or not name) else name
    return name, validate(cfg)


def describe(cfg):
    return "proposer=%s cutter=%s settle=%s judge=%s context=%s listens=%d" % (
        "+".join(cfg["proposer"]), cfg["cutter"], cfg["settle"], cfg["judge"], cfg["context"], cfg["listens"])


# ------------------------------------------------------------------ cache key

def audio_hash(path):
    """sha256 of the audio file's bytes (the clip or track that was sent)."""
    return BC.sha_file(path)


def prompt_hash(prompt_text):
    return BC.sha_text(prompt_text or "")


def cache_key(audio_sha256, engine, model, prompt_sha256=""):
    """The cache key of one engine output: (audio hash, engine, model, prompt hash). An engine with no prompt (a plain
    transcriber) passes ''. Same four parts = the same output may be reused; any part changed = a new paid call."""
    for name, v in (("audio_sha256", audio_sha256), ("engine", engine), ("model", model)):
        if not v:
            raise ValueError("cache_key needs %s" % name)
    blob = json.dumps({"audio": audio_sha256, "engine": engine, "model": model, "prompt": prompt_sha256 or ""},
                      sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ prices (read from the repo, never typed here)

def _consts(path, names):
    """Module-level constants of a script, evaluated from its source with no builtins (the paid module is never
    imported: this skeleton has no path that could call an engine)."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n in names:
                out[n] = eval(compile(ast.Expression(node.value), path, "eval"), {"__builtins__": {}}, dict(out))  # noqa: S307 - literal arithmetic
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def lesson_minutes(date, data_root, raw_root):
    """{'Medi': min, 'Amal': min} from the ElevenLabs provenance (audio_duration_secs), else the rehear manifest."""
    out = {}
    for who in ("Medi", "Amal"):
        p = BC.J(os.path.join(raw_root, date, "scribe_%s.provenance.json" % who)) or {}
        if p.get("audio_duration_secs"):
            out[who] = p["audio_duration_secs"] / 60.0
    if not out:
        man = BC.J(os.path.join(data_root, "lesson-work", "rehear", date, "manifest.json")) or {}
        for who, srcs in (man.get("sources") or {}).items():
            out[who] = sum(s.get("dur") or 0 for s in srcs) / 60.0
    return out


def prices(data_root, raw_root, date=None, scripts_dir=HERE):
    """Every unit price the dry-run uses, each with where it came from."""
    br = _consts(os.path.join(scripts_dir, "bench_run.py"), {"PRICE"}).get("PRICE", {})
    pe = _consts(os.path.join(scripts_dir, "pipeline_ext.py"), {"ELEVEN_USD_PER_MIN", "KEYTERM_USD_PER_MIN"})
    P = {}
    if "ELEVEN_USD_PER_MIN" in pe:
        v = pe["ELEVEN_USD_PER_MIN"] + pe.get("KEYTERM_USD_PER_MIN", 0)
        P["eleven_whole_per_min"] = (v, "scripts/pipeline_ext.py ELEVEN_USD_PER_MIN + KEYTERM_USD_PER_MIN (production sends keyterms)")
    obs = []
    for f in sorted(glob.glob(os.path.join(data_root, "runs", "*.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                m = (d.get("usage") or {}).get("audio_min")
                if d.get("step") == "scribe.transcribe" and d.get("cost_usd") and m:
                    obs.append(d["cost_usd"] / m)
    if obs:
        P["eleven_whole_per_min_observed"] = (_mean(obs), "data/runs/*.jsonl scribe.transcribe cost_usd / usage.audio_min, mean of %d calls" % len(obs))
    if "eleven" in br:
        P["eleven_line_per_s"] = (br["eleven"], "scripts/bench_run.py PRICE['eleven'] (per audio second)")
    if "deepgram-ar" in br:
        P["deepgram_per_min"] = (br["deepgram-ar"] * 60, "scripts/bench_run.py PRICE['deepgram-ar'] (nova-3 ar, x60 per minute)")
    # Gemini line listen (rehear, Batch): dollars of every complete base run / lines it answered; this lesson's own
    # runs when it has them, else every lesson's
    def line_price(pattern):
        tot, n, runs, dates = 0.0, 0, 0, set()
        for f in sorted(glob.glob(pattern)):
            r = BC.J(f) or {}
            if r.get("complete") and r.get("cost_usd") and r.get("lines"):
                tot, n, runs = tot + r["cost_usd"], n + len(r["lines"]), runs + 1
                dates.add(os.path.basename(os.path.dirname(f)))
        return (tot / n, runs, sorted(dates)) if n else None
    rh = os.path.join(data_root, "lesson-work", "rehear")
    lp = (date and line_price(os.path.join(rh, date, "base-run*.json"))) or line_price(os.path.join(rh, "*", "base-run*.json"))
    if lp:
        P["gemini_line_call"] = (lp[0], "data/lesson-work/rehear/<date>/base-run*.json cost_usd / lines answered (Batch, context=full), "
                                 "%d runs on %s" % (lp[1], lp[2][0] if len(lp[2]) == 1 else "%d lessons %s..%s" % (len(lp[2]), lp[2][0], lp[2][-1])))
    # Gemini whole track (the Gemini-only test, Batch): dollars per lesson minute
    per_min, src = [], []
    for f in sorted(glob.glob(os.path.join(data_root, "lesson-work", "bench", "*", "gemini-only-batch-t1", "whole-run*.json"))):
        r = BC.J(f) or {}
        d = os.path.basename(os.path.dirname(os.path.dirname(f)))
        mins = lesson_minutes(d, data_root, raw_root).get("Medi")
        if r.get("complete") and r.get("cost_usd") and mins:
            per_min.append(r["cost_usd"] / mins)
            src.append(d)
    if per_min:
        P["gemini_whole_per_min"] = (_mean(per_min), "data/lesson-work/bench/<date>/gemini-only-batch-t1/whole-run*.json cost_usd / lesson minutes "
                                     "(both tracks, pass 1 + pass 2, Batch), %d runs on %s" % (len(per_min), ", ".join(sorted(set(src)))))
    sp = BC.J(os.path.join(data_root, "lesson-work", "rehear", "spend.json")) or {}
    if (sp.get("new_lessons") or {}).get("per_lesson_usd") is not None:
        P["allowance_per_lesson"] = (sp["new_lessons"]["per_lesson_usd"], "data/lesson-work/rehear/spend.json new_lessons.per_lesson_usd (%s)" % sp["new_lessons"].get("set_by", ""))
    return P


# ------------------------------------------------------------------ what is cached

def inventory(date, data_root, raw_root):
    """{engine: [{what, path, model, runs/lines/cost, complete}]} - every cached engine output for the lesson."""
    inv = {}
    add = lambda e, row: inv.setdefault(e, []).append(row)  # noqa: E731
    for who in ("Medi", "Amal"):
        p = os.path.join(raw_root, date, "scribe_%s.json" % who)
        if os.path.exists(p):
            prov = BC.J(os.path.join(raw_root, date, "scribe_%s.provenance.json" % who)) or {}
            add("elevenlabs", {"what": "whole track %s (scribe_v2)" % who, "path": p, "model": "scribe_v2",
                               "minutes": round((prov.get("audio_duration_secs") or 0) / 60.0, 1), "audio_sha256": prov.get("source_sha256")})
    rd = os.path.join(data_root, "lesson-work", "rehear", date)
    lines = BC.J(os.path.join(rd, "lines.json"))
    if lines:
        add("elevenlabs", {"what": "his lines, raw text per line (rehear lines.json)", "path": os.path.join(rd, "lines.json"),
                           "model": "scribe_v2", "lines": len(lines.get("lines") or [])})
    man = BC.J(os.path.join(rd, "manifest.json")) or {}
    for stage in ("base", "v3"):
        for f in sorted(glob.glob(os.path.join(rd, "%s-run*.json" % stage))):
            r = BC.J(f) or {}
            add("gemini", {"what": "line listen %s (%s, context=full)" % (os.path.basename(f)[:-5], r.get("transport") or "instant"),
                           "path": f, "model": r.get("model") or man.get("model"), "lines": len(r.get("lines") or {}),
                           "cost_usd": r.get("cost_usd"), "complete": bool(r.get("complete")),
                           "prompt_sha256": man.get("prompts_sha256" if stage == "base" else "v3_prompts_sha256")})
    bd = os.path.join(data_root, "lesson-work", "bench", date)
    if os.path.isdir(bd):
        for e in sorted(os.listdir(bd)):
            for f in sorted(glob.glob(os.path.join(bd, e, "*-run*.json"))):
                r = BC.J(f) or {}
                fam = ("deepgram" if e.startswith("deepgram") else "gemini" if e.startswith("gemini") else
                       "elevenlabs" if e.startswith("eleven") else e.split("-")[0])
                add(fam, {"what": "bench %s %s" % (e, os.path.basename(f)[:-5]), "path": f, "model": r.get("model"),
                          "lines": len(r.get("lines") or {}), "cost_usd": r.get("cost_usd"), "complete": bool(r.get("complete"))})
        if os.path.exists(os.path.join(bd, "truth.json")):
            add("key", {"what": "bench frozen key truth.json", "path": os.path.join(bd, "truth.json")})
    rg = os.path.join(data_root, "lesson-work", "review-grades", date + ".json")
    if os.path.exists(rg):
        add("key", {"what": "grade-book frozen key (review-grades)", "path": rg})
    return inv


def _complete(inv, fam, pred):
    return [r for r in inv.get(fam, []) if pred(r)]


def disputed_lines(date, data_root):
    """Lines where ElevenLabs' raw text and Gemini's first cached line listen differ (normalised words): the clips a
    second listen / judge would get. None when either cache is missing (then every listen line is the upper bound)."""
    rd = os.path.join(data_root, "lesson-work", "rehear", date)
    lines = (BC.J(os.path.join(rd, "lines.json")) or {}).get("lines") or []
    run = BC.J(os.path.join(rd, "base-run1.json")) or {}
    listen = [ln for ln in lines if ln.get("listen")]
    if not lines or not run.get("lines"):
        return None, listen
    out = []
    for ln in listen:
        g = run["lines"].get(str(ln["i"]))
        if g is None:
            continue
        if BC.tokens(g.get("text") or "") != BC.tokens(ln.get("engine") or ""):
            out.append(ln)
    return out, listen


def _secs(lns):
    return sum(max(0.0, (ln.get("window") or [ln.get("t", 0), ln.get("end", 0)])[1] - (ln.get("window") or [ln.get("t", 0), ln.get("end", 0)])[0]) for ln in lns)


def plan_cell(cfg, date, data_root, raw_root, inv=None, P=None):
    """[{need, cached, usd, how}] for one setup: what it reads from the cache and what would be a paid call."""
    inv = inventory(date, data_root, raw_root) if inv is None else inv
    P = prices(data_root, raw_root, date) if P is None else P
    mins = lesson_minutes(date, data_root, raw_root)
    med, both = mins.get("Medi") or 0.0, sum(mins.values())
    disp, listen = disputed_lines(date, data_root)
    n_disp = len(disp) if disp is not None else len(listen)
    disp_note = ("%d of %d listen lines where ElevenLabs raw and Gemini run 1 differ (cached)" % (n_disp, len(listen))
                 if disp is not None else "upper bound: every listen line (%d), no cached Gemini run to count disputes" % len(listen))
    disp_s = _secs(disp if disp is not None else listen)
    pr = lambda k: ((P[k][0], "[%s]" % k) if k in P else (None, "[%s: no price found in the repo]" % k))  # noqa: E731
    rows = []

    def row(need, cached, usd, how):
        rows.append({"need": need, "cached": cached, "usd": None if cached else usd, "how": how})

    # 1. ElevenLabs words + times: every cell (proposer, cutter, or the line list a listener hears)
    ev = _complete(inv, "elevenlabs", lambda r: r["what"].startswith("whole track"))
    p, src = pr("eleven_whole_per_min")
    row("ElevenLabs whole lesson, both tracks (words + times)", len(ev) >= 2,
        None if p is None else p * both, "%.1f min x $%s/min - %s" % (both, _f(p), src))
    # 2. Gemini proposes on the whole track
    if "gemini" in cfg["proposer"]:
        have = _complete(inv, "gemini", lambda r: "gemini-only" in r["what"] and r.get("complete"))
        p, src = pr("gemini_whole_per_min")
        row("Gemini whole-track proposal (silence cut, pass 1 + pass 2)", bool(have),
            None if p is None else p * med, "%.1f lesson min x $%s/min - %s" % (med, _f(p), src))
    # 3. Deepgram proposes / votes
    if "deepgram" in cfg["proposer"]:
        have = _complete(inv, "deepgram", lambda r: "whole" in r["what"] and r.get("complete"))
        p, src = pr("deepgram_per_min")
        row("Deepgram nova-3 whole track (his)", bool(have), None if p is None else p * med,
            "%.1f min x $%s/min - %s" % (med, _f(p), src))
    if "cohere" in cfg["proposer"]:
        have = _complete(inv, "cohere", lambda r: r.get("lines"))
        row("Cohere Transcribe Arabic (local open model)", bool(have), 0.0, "local GPU run, $0 (bench 2026-10-02 cohere-open); not wired for whole tracks")
    # 4. Gemini line listens (re-hear his lines cut by the cutter)
    p, src = pr("gemini_line_call")
    for n in range(1, cfg["listens"] + 1):
        have = cfg["context"] == "full" and cfg["cutter"] == "eleven" and _complete(
            inv, "gemini", lambda r, n=n: r["what"].startswith("line listen base-run%d " % n) and r.get("complete"))
        row("Gemini line listen %d of %d, context=%s" % (n, cfg["listens"], cfg["context"]), bool(have),
            None if p is None else p * len(listen),
            "%d listen lines x $%s/call - %s%s" % (len(listen), _f(p), src,
                                                   "" if cfg["context"] == "full" else "; the cache holds context=full only (other context = new prompt hash)"))
    # 5. forced alignment of a whole-track text
    if cfg["cutter"] == "align":
        row("Forced alignment (whole track -> line times)", False, 0.0, "local, $0; NOT BUILT (protocol section 4 timing test: 30-50 hand-marked lines first)")
    # 6. second listen on disputed clips, by each proposer
    if cfg["settle"] == "second-listen":
        for who in cfg["proposer"]:
            if who == "gemini":
                row("Second listen on disputed clips: Gemini", False, None if p is None else p * n_disp, "%s x $%s/call - %s" % (disp_note, _f(p), src))
            elif who == "eleven":
                q, qs = pr("eleven_line_per_s")
                row("Second listen on disputed clips: ElevenLabs", False, None if q is None else q * disp_s,
                    "%.0f s of clip audio x $%s/s - %s" % (disp_s, _f(q), qs))
            elif who == "deepgram":
                q, qs = pr("deepgram_per_min")
                row("Second listen on disputed clips: Deepgram", False, None if q is None else q * disp_s / 60.0,
                    "%.0f s x $%s/min - %s" % (disp_s, _f(q), qs))
    # 7. the judge on disputed clips (always blind)
    if cfg["judge"] != "none" and cfg["settle"] in ("judge", "second-listen"):
        if cfg["judge"] == "gemini":
            row("Blind judge on disputed clips: Gemini (version X / Y + reasons)", False, None if p is None else p * n_disp,
                "%s x $%s/call (line-listen price as proxy; a judge prompt is a new prompt hash) - %s" % (disp_note, _f(p), src))
        else:
            row("Blind judge on disputed clips: another family", False, None, "no price for another family in the repo's spend logs: not estimated")
    return rows


def _f(x):
    if x is None:
        return "?"
    return ("%.6f" % x).rstrip("0").rstrip(".") if x < 0.01 else "%.4f" % x


def dry_run(date, data_root, raw_root, cells=None, out=print):
    """Lists the cache per engine and, per setup, what is cached vs a paid call and its cost. Spends nothing."""
    inv = inventory(date, data_root, raw_root)
    P = prices(data_root, raw_root, date)
    mins = lesson_minutes(date, data_root, raw_root)
    out("Hearing harness dry-run %s (spends nothing; `run` is not built)" % date)
    out("Lesson minutes: " + (", ".join("%s %.1f" % kv for kv in sorted(mins.items())) or "unknown"))
    out("")
    out("Cached engine outputs:")
    if not inv:
        out("  (none)")
    for fam in sorted(inv):
        for r in inv[fam]:
            bits = [r["what"]]
            if r.get("model"):
                bits.append(str(r["model"]))
            if r.get("lines") is not None:
                bits.append("%d lines" % r["lines"])
            if r.get("minutes"):
                bits.append("%.1f min" % r["minutes"])
            if r.get("cost_usd") is not None:
                bits.append("$%.4f" % r["cost_usd"])
            if r.get("complete") is False:
                bits.append("INCOMPLETE")
            out("  %-10s %s" % (fam, " | ".join(bits)))
    out("")
    out("Unit prices (where each number came from):")
    for k in sorted(P):
        out("  %-30s %-10s %s" % (k, _f(P[k][0]), P[k][1]))
    out("")
    cells = cells or [(k, cell(k)) for k in sorted(CELLS)]
    res = {}
    out("%-6s %-9s %-10s %s" % ("cell", "cached", "paid est.", "setup"))
    plans = []
    for name, cfg in cells:
        rows = plan_cell(cfg, date, data_root, raw_root, inv, P)
        paid = [r for r in rows if not r["cached"]]
        usd = sum(r["usd"] or 0 for r in paid)
        unknown = any(r["usd"] is None for r in paid)
        res[name] = {"switches": describe(cfg), "about": cfg.get("about"), "rows": rows, "paid_usd": round(usd, 4),
                     "has_unpriced": unknown, "cached_all": not paid}
        out("%-6s %-9s %-10s %s" % (name, "%d/%d" % (len(rows) - len(paid), len(rows)), "$%.2f%s" % (usd, "+?" if unknown else ""), describe(cfg)))
        plans.append((name, cfg, rows))
    for name, cfg, rows in plans:
        out("")
        out("Cell %s: %s" % (name, cfg.get("about", "")))
        for r in rows:
            out("  [%s] %-58s %s  %s" % ("cached" if r["cached"] else "PAID  ", r["need"],
                                       "" if r["cached"] else ("$%.2f" % r["usd"] if r["usd"] is not None else "$?"), r["how"]))
    return {"date": date, "minutes": mins, "inventory": inv, "prices": {k: {"usd": v[0], "source": v[1]} for k, v in P.items()}, "cells": res}


# ------------------------------------------------------------------ the frozen key + versions

def load_key(date, data_root):
    """The frozen answer key, as {source, ids: [line id], text: {id: key text}, words: [(id, word)], slips: [...],
    engine: {id: ElevenLabs raw}, before: {id: pipeline page before review}, rehear_ids: {rehear i: id}, bench: truth}."""
    bd = os.path.join(data_root, "lesson-work", "bench", date)
    rd = os.path.join(data_root, "lesson-work", "rehear", date)
    rlines = (BC.J(os.path.join(rd, "lines.json")) or {}).get("lines") or []
    tp = os.path.join(bd, "truth.json")
    if os.path.exists(tp):
        man = BC.J(os.path.join(bd, "manifest.json")) or {}
        if man.get("truth_sha256") and BC.sha_file(tp) != man["truth_sha256"]:
            raise SystemExit("truth.json does not match the manifest: the key was edited after the freeze")
        truth = BC.J(tp)
        ids = [str(ln["i"]) for ln in truth["lines"]]
        return {"source": os.path.relpath(tp, data_root), "kind": "bench", "bench": truth, "ids": ids,
                "text": {str(ln["i"]): ln["truth"] for ln in truth["lines"]},
                "engine": {str(ln["i"]): ln["engine"] for ln in truth["lines"]}, "before": {}, "rehear_ids": {}}
    gp = os.path.join(data_root, "lesson-work", "review-grades", date + ".json")
    g = BC.J(gp)
    if not g:
        raise SystemExit("no frozen key for %s: neither bench/%s/truth.json nor review-grades/%s.json" % (date, date, date))
    key = g["key"]
    slips = []
    for s in key.get("slips") or []:
        right = re.split(r"\s=\s|\s\(", s.get("ar") or "")[0].strip()
        slips.append({"id": s["i"], "t": s.get("t"), "kind": s.get("k"), "wrong": s.get("said") or "", "right": right})
    engine = {"%.2f" % float(ln["t"]): ln.get("engine") or "" for ln in rlines}
    return {"source": os.path.relpath(gp, data_root), "kind": "grades", "ids": sorted(key["lines"], key=float),
            "text": dict(key["lines"]), "words": [(w["i"], w["word"]) for w in key["words"]], "slips": slips,
            "engine": engine, "before": dict((g.get("before") or {}).get("lines") or {}),
            "rehear_ids": {str(ln["i"]): "%.2f" % float(ln["t"]) for ln in rlines}}


def load_version(spec, key, fallback="engine"):
    """A version = {line id: text}. spec: a JSON file ({"lines": {id: text | {"text", "error"?}}}; ids are the key's
    line ids, or rehear line numbers which are mapped through rehear lines.json), or @engine / @before. Lines the
    version does not hold take the fallback text (engine = ElevenLabs raw, before = the page before review, empty).
    Returns (texts, info)."""
    if spec in ("@engine", "@before"):
        src = key["engine"] if spec == "@engine" else key["before"]
        return {i: src.get(i, "") for i in key["ids"]}, {"name": spec, "from_version": len([i for i in key["ids"] if i in src]),
                                                         "from_fallback": 0, "errors": 0, "unmapped": 0}
    j = BC.J(spec)
    if j is None:
        raise SystemExit("version file not found: %s" % spec)
    raw = j.get("lines", j) if isinstance(j, dict) else j
    if isinstance(raw, list):
        raw = {str(x.get("id", x.get("i"))): x for x in raw}
    idset = set(key["ids"])
    got, errors, unmapped = {}, 0, 0
    for k, v in raw.items():
        k = str(k)
        kid = k if k in idset else key["rehear_ids"].get(k)
        if kid is None:
            try:
                kid = "%.2f" % float(k) if key["kind"] == "grades" and "%.2f" % float(k) in idset else None
            except ValueError:
                kid = None
        if kid is None:
            unmapped += 1
            continue
        if isinstance(v, dict):
            if v.get("error") and not v.get("text"):
                errors += 1
            v = v.get("text") or ""
        got[kid] = v or ""
    fb = {"engine": key["engine"], "before": key["before"], "empty": {}}[fallback]
    texts = {i: got[i] if i in got else fb.get(i, "") for i in key["ids"]}
    if j.get("complete") is False:
        print("NOTE: %s is marked incomplete (a run in progress)" % spec)
    return texts, {"name": os.path.basename(spec), "from_version": len(got), "from_fallback": len(idset) - len(got),
                   "errors": errors, "unmapped": unmapped}


# ------------------------------------------------------------------ scorer

def _match_words(want, have):
    """Greedy one-use matching of key words to the version's Arabic words (word_coverage.core, then .similar, the
    grade book's own test for 'the line has his word'). Returns [bool] per wanted word."""
    import word_coverage as WC
    pool = list(have)
    out = []
    for w in want:
        k = next((n for n, h in enumerate(pool) if WC.core(h) == WC.core(w)), None)
        if k is None:
            k = next((n for n, h in enumerate(pool) if WC.similar(h, w)), None)
        if k is not None:
            pool.pop(k)
        out.append(k is not None)
    return out


def word_hits(key, texts):
    """[(line id, word, hit)] over every Arabic word Medi said in the key, paired by line."""
    out = []
    if key["kind"] == "bench":
        import bench_score as BS
        for i in key["ids"]:
            want = [t for t in BC.tokens(key["text"][i]) if BC.is_ar(t)]
            raw, cv = BS.views(texts.get(i, ""))
            pool = list(raw) + [x for x in cv if x not in raw]
            for w in want:
                k = next((n for n, h in enumerate(pool) if BC.tok_eq(w, h)), None)
                if k is not None:
                    pool.pop(k)
                out.append((i, w, k is not None))
        return out
    import word_coverage as WC
    by = {}
    for i, w in key["words"]:
        by.setdefault(i, []).append(w)
    for i in sorted(by, key=float):
        vt, kt = texts.get(i, ""), key["text"].get(i, "")
        if vt == kt:
            out.extend((i, w, True) for w in by[i])
            continue
        hits = _match_words(by[i], [t["ar"] for t in WC.word_tokens(vt or "") if not t.get("cut")])
        out.extend((i, w, h) for w, h in zip(by[i], hits))
    return out


def slip_results(key, texts):
    """[(slip, hidden: True/False/None)] - None = cannot be judged from text (no right form, or it adds no word)."""
    import bench_score as BS
    out = []
    if key["kind"] == "bench":
        for s in key["bench"].get("slips") or []:
            i = str(s["i"])
            out.append((dict(s, id=i), BS.slip_hidden(s, key["text"][i], texts.get(i, ""))))
        return out
    for s in key["slips"]:
        if not s["right"] or not s["wrong"]:
            out.append((s, None))
            continue
        out.append((s, BS.slip_hidden({"wrong": s["wrong"], "right": s["right"]}, key["text"].get(s["id"], ""), texts.get(s["id"], ""))))
    return out


def score_version(key, texts):
    """Hit rate + FCR of one version against the key."""
    hits = word_hits(key, texts)
    sl = slip_results(key, texts)
    judged = [x for x in sl if x[1] is not None]
    hidden = [x for x in judged if x[1]]
    n, h = len(hits), sum(1 for x in hits if x[2])
    return {"words": n, "hit": h, "hit_rate": round(100.0 * h / n, 1) if n else None,
            "slips": len(sl), "slips_judged": len(judged), "hidden": len(hidden),
            "fcr": round(100.0 * len(hidden) / len(judged), 1) if judged else None,
            "hidden_rows": [{"id": s["id"], "wrong": s["wrong"], "right": s["right"], "heard": texts.get(s["id"], "")} for s, _ in hidden],
            "per_word": hits}


def sign_test(b, c):
    """Exact two-sided sign test (McNemar exact) on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, j) for j in range(k + 1)) / 2.0 ** n
    return min(1.0, 2 * p)


def paired(s1, s2):
    """Word-by-word pairing of two versions on the same key words: both right / only first / only second / both wrong."""
    a = [x[2] for x in s1["per_word"]]
    b = [x[2] for x in s2["per_word"]]
    assert len(a) == len(b)
    only1 = sum(1 for x, y in zip(a, b) if x and not y)
    only2 = sum(1 for x, y in zip(a, b) if y and not x)
    return {"both": sum(1 for x, y in zip(a, b) if x and y), "only_first": only1, "only_second": only2,
            "neither": sum(1 for x, y in zip(a, b) if not x and not y), "p_sign": round(sign_test(only1, only2), 4)}


# ------------------------------------------------------------------ the blind judge prompt

# Vendor / engine / model names. Plain English words that are also model names ("eleven", "flash", "sonnet") are left
# out on purpose: Medi says them in lessons, and scrubbing them would change what the version wrote.
ENGINE_NAMES = ("elevenlabs", "eleven labs", "scribe_v2", "scribe", "gemini", "google", "deepgram", "nova-3", "cohere",
                "audar", "openai", "gpt", "whisper", "speechmatics", "claude", "anthropic", "codex")
_NAME_RE = re.compile(r"(?i)(?<![a-z])(%s)(?![a-z])" % "|".join(re.escape(n) for n in sorted(ENGINE_NAMES, key=len, reverse=True)))

JUDGE_TEMPLATE = """You are judging two written versions of ONE short clip from an online Arabic lesson. The speaker is
Medi, an American learner of Levantine Arabic who mixes English and Arabic and makes learner mistakes. You hear the clip.

Write down what HE really said, word for word, KEEPING his mistakes: never correct his Arabic to the form the tutor would
use. If the tutor says or types a word near this moment, that is NOT evidence that he said it.

Version X:
{x}
{x_reasons}
Version Y:
{y}
{y_reasons}
{context}Answer as JSON only: {{"pick": "X" | "Y" | "neither", "heard": "<what he said>", "why": "<one sentence>"}}
"""


def scrub(text):
    """Remove every engine / model / vendor name from text that goes to the judge."""
    return _NAME_RE.sub("[name removed]", text or "")


def leaks(text):
    """The engine names found in a text (empty = blind)."""
    return sorted({m.group(1).lower() for m in _NAME_RE.finditer(text or "")})


def coin(seed, item):
    """The seeded coin: True = swap (version b shown as X)."""
    return random.Random("%s|%s" % (seed, item)).random() < 0.5


def judge_prompt(a, b, seed=0, item="", context="", reasons_a="", reasons_b=""):
    """The blind prompt for one disputed clip. a / b = the two versions (the caller knows which engine wrote which;
    the prompt never does). Returns {prompt, swapped, key: {"X": "a"|"b", "Y": ...}}."""
    swapped = coin(seed, item)
    (x, xr), (y, yr) = ((b, reasons_b), (a, reasons_a)) if swapped else ((a, reasons_a), (b, reasons_b))
    fmt = lambda r: ("Reasons given with it: %s\n" % scrub(r)) if r else ""  # noqa: E731
    prompt = JUDGE_TEMPLATE.format(x=scrub(x) or "(nothing written)", y=scrub(y) or "(nothing written)",
                                   x_reasons=fmt(xr), y_reasons=fmt(yr),
                                   context=("\nContext (the lesson around the clip, for meaning only):\n%s\n\n" % scrub(context)) if context else "\n")
    bad = leaks(prompt)
    if bad:                                          # never reached: scrub() removed them; a guard for template edits
        raise AssertionError("engine name in the judge prompt: %s" % bad)
    return {"prompt": prompt, "swapped": swapped, "key": {"X": "b" if swapped else "a", "Y": "a" if swapped else "b"}}


# ------------------------------------------------------------------ CLI

def _switch_flags(p):
    p.add_argument("--cell", choices=sorted(CELLS) + [c.lower() for c in CELLS])
    p.add_argument("--proposer", help="comma list of: " + ", ".join(SWITCHES["proposer"]))
    p.add_argument("--cutter", choices=SWITCHES["cutter"])
    p.add_argument("--settle", choices=SWITCHES["settle"])
    p.add_argument("--judge", choices=SWITCHES["judge"])
    p.add_argument("--context", choices=SWITCHES["context"])
    p.add_argument("--listens", type=int, choices=SWITCHES["listens"])


def build_parser():
    ap = argparse.ArgumentParser(prog="hearing_harness.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=os.path.join(REPO, "data"), help="data root (default: repo data/)")
    ap.add_argument("--raw", default=BC.RAW, help="raw lessons root (ElevenLabs transcripts, tracks)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run", help="what is cached, what each cell would cost (spends nothing)")
    d.add_argument("date", nargs="?", default=DEFAULT_DATE)
    d.add_argument("--json", action="store_true")
    _switch_flags(d)
    s = sub.add_parser("score", help="hit rate + FCR of versions against the frozen key")
    s.add_argument("date")
    s.add_argument("--version", action="append", required=True, help="JSON file, @engine (ElevenLabs raw) or @before")
    s.add_argument("--fallback", choices=("engine", "before", "empty"), default="engine")
    s.add_argument("--json", action="store_true")
    j = sub.add_parser("judge-prompt", help="the blind judge prompt for one clip")
    j.add_argument("date", nargs="?")
    j.add_argument("--line", help="key line id (start time) to pull ElevenLabs raw vs Gemini run 1 from the cache")
    j.add_argument("--a", default="")
    j.add_argument("--b", default="")
    j.add_argument("--reasons-a", default="")
    j.add_argument("--reasons-b", default="")
    j.add_argument("--context", default="")
    j.add_argument("--seed", default="0")
    j.add_argument("--item", default="")
    j.add_argument("--json", action="store_true")
    sub.add_parser("run", help="NOT BUILT: paid runs need Medi's yes")
    return ap


def main(argv=None):
    ap = build_parser()
    a, unknown = ap.parse_known_args(argv)
    if a.cmd == "run":                               # whatever flags follow: there is no paid path in this skeleton
        print(NOT_BUILT)
        return 2
    if unknown:
        ap.error("unrecognized arguments: %s" % " ".join(unknown))
    if a.cmd == "dry-run":
        explicit = a.cell or a.proposer or any(getattr(a, k) is not None for k in ("cutter", "settle", "judge", "context", "listens"))
        cells = [config_from_args(a)] if explicit else None
        res = dry_run(a.date, a.data, a.raw, cells, out=(lambda *_: None) if a.json else print)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0
    if a.cmd == "score":
        key = load_key(a.date, a.data)
        rows = []
        for spec in a.version:
            texts, info = load_version(spec, key, a.fallback)
            s = score_version(key, texts)
            rows.append((info, s))
        if a.json:
            print(json.dumps([{"version": i, **{k: v for k, v in s.items() if k != "per_word"}} for i, s in rows], ensure_ascii=False, indent=1))
            return 0
        print("Key: %s (%s)" % (key["source"], key["kind"]))
        print("%-28s %-22s %-20s %s" % ("version", "hit rate", "FCR", "lines (version / fallback=%s)" % a.fallback))
        for info, s in rows:
            print("%-28s %-22s %-20s %d / %d%s" % (info["name"][:28], "%d/%d (%s%%)" % (s["hit"], s["words"], s["hit_rate"]),
                                                  "%d/%d (%s%%)" % (s["hidden"], s["slips_judged"], s["fcr"]),
                                                  info["from_version"], info["from_fallback"],
                                                  ("  errors %d" % info["errors"]) if info["errors"] else ""))
            for h in s["hidden_rows"]:
                print("    erased slip at %s: he said %s, tutor's form %s, version wrote: %s" % (h["id"], h["wrong"], h["right"], h["heard"]))
        print("FCR counts only slips with a known right form that adds a word (%d of %d key slips judged)." % (rows[0][1]["slips_judged"], rows[0][1]["slips"]))
        for k in range(1, len(rows)):
            pr = paired(rows[0][1], rows[k][1])
            print("paired %s vs %s: both %d, only first %d, only second %d, neither %d, exact sign p=%s" % (
                rows[0][0]["name"], rows[k][0]["name"], pr["both"], pr["only_first"], pr["only_second"], pr["neither"], pr["p_sign"]))
        return 0
    if a.cmd == "judge-prompt":
        A, B, ctx, item = a.a, a.b, a.context, a.item
        if a.line:
            if not a.date:
                raise SystemExit("--line needs a date")
            key = load_key(a.date, a.data)
            g, _ = load_version(os.path.join(a.data, "lesson-work", "rehear", a.date, "base-run1.json"), key, "empty")
            A, B, item = key["engine"].get(a.line, ""), g.get(a.line, ""), item or a.line
        res = judge_prompt(A, B, seed=a.seed, item=item, context=ctx, reasons_a=a.reasons_a, reasons_b=a.reasons_b)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print(res["prompt"])
            print("(answer key, never shown to the judge: X = %s, Y = %s)" % (res["key"]["X"], res["key"]["Y"]), file=sys.stderr)
        return 0
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
