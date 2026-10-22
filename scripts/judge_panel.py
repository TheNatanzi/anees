# -*- coding: utf-8 -*-
"""PR-29 - the mistake finder is a judge panel (Medi 2026-10-21: "Switch now", after the key v4 re-score: Opus + Argon
F0.5 87.9 vs 76.3 for the two-reader rule, better in 100 % of bootstrap resamples; research/evidence/r90-43fa688/replay_v4.py).

The tested setup, run on one lesson after the production readers:
  1 pool    six readers, the same READER-BRIEF: the lesson's own r1 (Claude Opus) and r2 (Claude Sonnet) rows, plus
            Codex gpt-5.6-terra and gpt-6-astra (ChatGPT plan) and Gemini 3.7 Flash and 3.1 Pro (paid Gemini key)
  2 group   every vocab / grammar flag (an 'asked' or no-reaction signal is never a slip) joins the cluster of its family
            whose first flag is within 15 s; one candidate per cluster
  3 judge   Claude Opus (Claude plan) and Gemini 4 Argon (paid Gemini key, thinking high) each rule on EVERY candidate
            with the transcript ('plain' brief: the grade book's definition of a slip); p = confidence for 'slip',
            100 - confidence for 'not'; the panel's p = the mean of the two
  4 keep    p >= THRESHOLD (0.60: the best pooled cut on key v4, and the leave-one-lesson-out pick in all 3 folds)
  5 write   <date>.settled.json: its vocab / grammar slip rows are replaced by the kept candidates (the readers' own row,
            r1/r2 first); every other row stays as it was. The readers' version is kept as <date>.settled.readers.json and
            every candidate with both verdicts in data/lesson-work/judge-panel/<date>.json.
Money (Medi 2026-10-21: "use the paid Gemini key for Argon with a 20 dollar per month cap"): every paid call is priced from
its own token counts into data/lesson-work/judge-panel/spend.json; a call that would take the month past 90 % of
CAP_USD is not made and the lesson keeps the readers' rows (the run says so and fails closed).

    python scripts/judge_panel.py <date>            # run (reuses any reader / judge file already written for the date)
    python scripts/judge_panel.py <date> --dry-run  # the candidates only, no model call
"""
import argparse, datetime, json, os, re, subprocess, sys, tempfile, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import anees_env as AE  # noqa: E402

WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
OUT = os.path.join(REPO, "data", "lesson-work", "judge-panel")
SPEND = os.path.join(OUT, "spend.json")
RULE = "PR-29"
THRESHOLD = 0.60
MATCH_S = 15.0
CAP_USD = 20.0                       # per calendar month, paid Gemini calls of this step only
STOP_AT = 0.90
DROP_SIGNALS = {"asked", "none"}
READERS = [("r1", None, None), ("r2", None, None),
           ("codex-gpt-5.6-terra", "codex", "gpt-5.6-terra"), ("codex-gpt-6-astra", "codex", "gpt-6-astra"),
           ("gemini-3.7-flash", "gemini", "gemini-3.7-flash"), ("gemini-3.1-pro-preview", "gemini", "gemini-3.1-pro-preview")]
JUDGES = [("claude-opus-5-5", "claude", "claude-opus-5-5"), ("gemini-4-argon", "gemini", "gemini-4-argon")]
# $ per 1M tokens: input, output (thinking counts as output). Google price page, through 2026-11-30.
PRICE = {"gemini-4-argon": (2.00, 10.00), "gemini-3.1-pro-preview": (2.00, 12.00), "gemini-3.7-flash": (0.75, 3.75)}
EST_TOKENS = (45000, 16000)          # a whole-lesson read or judge call, before it is made (measured 39k in / 8-11k out)

DEF = """WHAT COUNTS AS A SLIP (the grade book's rule; this is what you are judging):
- A slip is a mistake Medi (the student) made in Arabic that the tutor Amal CORRECTED or REJECTED: she recast it in the right
  form, said no, named the rule, prompted until he fixed it, or typed the fix in chat.
- NOT a slip: Medi asking for a word he does not know, switching to English, a word he did not know yet ("how do you say"),
  a self-fix before she reacts, a stutter or cut-off, a speech-to-text error (the engine misheard him), a question about a rule,
  a correct Levantine form that is just different from MSA, or anything Amal let pass with no reaction.
- One slip per corrected moment: if several candidates describe the same moment, only the best one is a slip."""


def J(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def read(rel):
    return open(os.path.join(REPO, rel), encoding="utf-8").read()


def sec(mm):
    p = [int(x) for x in str(mm).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def mmss(t):
    t = int(round(float(t)))
    return "%d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60) if t >= 3600 else "%02d:%02d" % (t // 60, t % 60)


def family(kind, tier=None):
    """vocab / grammar for every row that could become a slip; a tier-3 vocab row (switching to English) never does."""
    k = str(kind or "")
    if k.startswith("vocab") and tier != 3:
        return "vocab"
    return "grammar" if k.startswith("grammar") else None


def signal(r):
    return (str(r.get("signal") or "none").split() or ["none"])[0].strip(",;").lower()


# ------------------------------------------------------------------------------------------------ money
def month():
    return datetime.date.today().strftime("%Y-%m")


def spent():
    return float((J(SPEND, {}) or {}).get("months", {}).get(month(), 0.0))


def price(model, usage):
    pin, pout = PRICE[model]
    tin = float(usage.get("in") or 0); tout = float(usage.get("out") or 0) + float(usage.get("reasoning") or 0)
    return round((tin * pin + tout * pout) / 1e6, 6)


def can_spend(model):
    est = (EST_TOKENS[0] * PRICE[model][0] + EST_TOKENS[1] * PRICE[model][1]) / 1e6
    return spent() + est <= CAP_USD * STOP_AT


def record(model, usd, date, what):
    S = J(SPEND, {}) or {}
    S.setdefault("about", "PR-29 paid Gemini calls of the judge panel; cap %.0f USD per month, calls stop at %d %%." % (CAP_USD, STOP_AT * 100))
    S.setdefault("cap_usd_month", CAP_USD)
    M = S.setdefault("months", {})
    M[month()] = round(M.get(month(), 0.0) + usd, 6)
    S.setdefault("calls", []).append({"at": datetime.datetime.now().isoformat(timespec="seconds"), "date": date, "model": model, "what": what, "usd": usd})
    W(SPEND, S)


class CapReached(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ model calls
def call_gemini(model, system, user, thinking=None):
    if not can_spend(model):
        raise CapReached("the judge panel's Gemini spend this month (%.2f USD) would pass %d %% of the %.0f USD cap" % (spent(), STOP_AT * 100, CAP_USD))
    key = AE.env("GEMINI_API_KEY") or AE.env("GOOGLE_API_KEY")
    gc = {"responseMimeType": "application/json", "maxOutputTokens": 60000}
    if thinking:
        gc["thinkingConfig"] = {"thinkingLevel": thinking}
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": gc}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model,
                                 data=json.dumps(body).encode("utf-8"), headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError("Gemini HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
    cand = (d.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []) if not p.get("thought"))
    u = d.get("usageMetadata") or {}
    usage = {"in": u.get("promptTokenCount"), "out": u.get("candidatesTokenCount"), "reasoning": u.get("thoughtsTokenCount"), "finish": cand.get("finishReason")}
    usage["usd"] = price(model, usage)
    return text, usage


def call_claude(model, system, user):
    sf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8"); sf.write(system); sf.close()
    r = subprocess.run(["claude", "-p", "--model", model, "--output-format", "json", "--system-prompt-file", sf.name,
                        "--disallowedTools", "Bash,Read,Write,Edit,MultiEdit,Glob,Grep,WebFetch,WebSearch,Task,NotebookEdit,TodoWrite"],
                       input=user, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600, shell=(os.name == "nt"))
    try:
        d = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        raise RuntimeError("claude -p: " + (r.stdout or r.stderr)[:300])
    if d.get("is_error"):
        raise RuntimeError("claude -p error: " + str(d.get("result"))[:300])
    return d.get("result") or "", {"via": "claude-plan"}


def call_codex(model, system, user):
    out = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False); out.close()
    exe = "codex.cmd" if os.name == "nt" else "codex"
    r = subprocess.run([exe, "exec", "--skip-git-repo-check", "-s", "read-only", "-m", model, "--output-last-message", out.name, "-"],
                       input=system + "\n\n" + user, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400,
                       cwd=tempfile.gettempdir())
    text = open(out.name, encoding="utf-8", errors="replace").read()
    if not text.strip():
        raise RuntimeError("codex: no answer " + (r.stderr or r.stdout)[-300:])
    return text, {"via": "codex-plan"}


def parse(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        return json.loads(t)
    except ValueError:
        return json.loads(t[t.find("{"):t.rfind("}") + 1])


def call(vendor, model, system, user, thinking=None, date=None, what="judge"):
    """One model call, with its run line (check_rules AI-logged / AI-paid-logged: scripts/track.py)."""
    import track
    t0 = time.time()
    try:
        if vendor == "gemini":
            text, usage = call_gemini(model, system, user, thinking)
        else:
            text, usage = {"claude": call_claude, "codex": call_codex}[vendor](model, system, user)
    except Exception as e:
        track.log_run("judge_panel." + what, date, kind="inference", provider={"gemini": "google", "claude": "anthropic", "codex": "openai"}[vendor],
                      request_model=model, response_model=model, status="error", duration_ms=int((time.time() - t0) * 1000),
                      params={"rule": RULE, "error": str(e)[:200]})
        raise
    track.log_run("judge_panel." + what, date, kind="inference", provider={"gemini": "google", "claude": "anthropic", "codex": "openai"}[vendor],
                  request_model=model, response_model=model, cost_usd=usage.get("usd") or 0.0, duration_ms=int((time.time() - t0) * 1000),
                  params={"rule": RULE, "via": usage.get("via") or "paid Gemini key", "tokens_in": usage.get("in"), "tokens_out": usage.get("out")})
    return text, usage


# ------------------------------------------------------------------------------------------------ 1 pool
def reader_prompt(date):
    files = [("data/lesson-work/full-audit/READER-BRIEF.md", None), ("data/lesson-work/full-audit/buckets.md", None), ("RULES.md", None),
             ("data/lesson-work/full-audit/amal-sheet.txt", None)]
    system = ("You are a reader. The brief below tells you to read files; they are all given to you inline instead, in <file> "
              "blocks, so you cannot and need not open anything. Follow the brief exactly. Where it says to write a file, return "
              "that ONE JSON object as your whole reply (no prose, no code fence). Use reader \"r1\".\n\n" +
              "\n\n".join('<file path="%s">\n%s\n</file>' % (p, read(p)) for p, _ in files if os.path.exists(os.path.join(REPO, p))))
    user = ("You are reader r1 for lesson %s. The transcript is below. Read the WHOLE transcript in order, then return the JSON "
            "object (date, reader, read, coverage_note, counts, rows).\n\n<file path=\"data/lesson-work/full-audit/%s.txt\">\n%s\n</file>"
            % (date, date, read("data/lesson-work/full-audit/%s.txt" % date)))
    return system, user


def pool_rows(date, dry=False, log=print):
    """{reader tag: rows}. r1 / r2 are the lesson's own production reads; the other four are read once and kept."""
    out = {}
    for tag, vendor, model in READERS:
        if vendor is None:
            out[tag] = (J(os.path.join(WORK, "%s.%s.json" % (date, tag)), {}) or {}).get("rows") or []
            continue
        p = os.path.join(OUT, "%s.read.%s.json" % (date, tag))
        if not os.path.exists(p) and not dry:
            system, user = reader_prompt(date)
            try:
                text, usage = call(vendor, model, system, user, date=date, what="reader")
                rows = parse(text).get("rows") or []
                W(p, {"date": date, "reader": tag, "model": model, "usage": usage, "rows": rows})
                if usage.get("usd"):
                    record(model, usage["usd"], date, "reader")
                log("  read %s: %d rows %s" % (tag, len(rows), usage))
            except CapReached:
                raise
            except Exception as e:                                  # a reader that fails is left out; the panel still judges
                log("  read %s FAILED: %s" % (tag, str(e)[:200]))
        out[tag] = (J(p, {}) or {}).get("rows") or []
    return out


# ------------------------------------------------------------------------------------------------ 2 group
def candidates(pool):
    flags = []
    for tag, rows in pool.items():
        for r in rows:
            if signal(r) in DROP_SIGNALS:
                continue
            f = family(r.get("kind"), r.get("tier"))
            try:
                t = float(sec(r.get("t")))
            except (TypeError, ValueError, IndexError):
                continue
            if f:
                flags.append({"fam": f, "t": t, "tag": tag, "row": r})
    flags.sort(key=lambda x: (x["fam"], x["t"]))
    cl = []
    for x in flags:
        c = next((c for c in cl if c["fam"] == x["fam"] and abs(c["t"] - x["t"]) <= MATCH_S), None)
        if c is None:
            cl.append({"fam": x["fam"], "t": x["t"], "members": [x], "tags": {x["tag"]}})
        else:
            c["members"].append(x); c["tags"].add(x["tag"])
    out = []
    for i, c in enumerate(sorted(cl, key=lambda c: c["t"])):
        reps = sorted(c["members"], key=lambda m: -len(str(m["row"].get("why") or "")))[:3]
        out.append({"id": "C%d" % (i + 1), "t": mmss(c["t"]), "family": c["fam"], "_t": c["t"], "_members": c["members"], "readers": sorted(c["tags"]),
                    "claims": [{"wrong": m["row"].get("wrong"), "right": m["row"].get("right"), "kind": m["row"].get("kind"),
                                "signal": m["row"].get("signal"), "why": str(m["row"].get("why") or "")[:300]} for m in reps]})
    return out


# ------------------------------------------------------------------------------------------------ 3 judge
def judge_prompt(date, cands):
    system = ("You judge candidate mistakes found by other readers in one Arabic lesson transcript (Medi = student, Amal = "
              "Levantine Arabic tutor). Readers are anonymous; how many flagged a candidate is NOT evidence. Judge each candidate "
              "fairly.\n\n" + DEF + "\n\n<file path=\"buckets.md\">\n" + read("data/lesson-work/full-audit/buckets.md") + "\n</file>")
    show = [{k: v for k, v in c.items() if not k.startswith("_") and k != "readers"} for c in cands]
    user = ("Lesson %s. Read the transcript, then judge EVERY candidate. Return ONE JSON object: {\"verdicts\": {\"C1\": {\"verdict\": "
            "\"slip\" or \"not\", \"confidence\": 0-100, \"why\": \"one short sentence\"}, ...}}\n\n<candidates>\n%s\n</candidates>\n\n"
            "<transcript>\n%s\n</transcript>" % (date, json.dumps(show, ensure_ascii=False, indent=0), read("data/lesson-work/full-audit/%s.txt" % date)))
    return system, user


def p_slip(v):
    if not isinstance(v, dict):
        return 0.0
    c = float(v.get("confidence") or 50) / 100
    return c if str(v.get("verdict")).lower().startswith("slip") else 1 - c


def judge(date, cands, sig, log=print):
    """{judge tag: verdicts}; a judge file is reused while the candidate list it judged is the same (sig)."""
    out = {}
    system, user = judge_prompt(date, cands)
    for tag, vendor, model in JUDGES:
        p = os.path.join(OUT, "%s.judge.%s.json" % (date, tag))
        J0 = J(p, {}) or {}
        if J0.get("candidates_sig") != sig:
            text, usage = call(vendor, model, system, user, thinking="high" if vendor == "gemini" else None, date=date, what="judge")
            v = parse(text)
            J0 = {"date": date, "judge": tag, "model": model, "usage": usage, "candidates_sig": sig, "verdicts": v.get("verdicts", v)}
            W(p, J0)
            if usage.get("usd"):
                record(model, usage["usd"], date, "judge")
            log("  judge %s: %d verdicts %s" % (tag, len(J0["verdicts"]), usage))
        out[tag] = J0["verdicts"]
    return out


# ------------------------------------------------------------------------------------------------ 4 keep + 5 write
def best_row(c):
    """The row a kept candidate is written as: a production reader's own row first (r1, then r2), else the most explained."""
    order = {"r1": 0, "r2": 1}
    m = sorted(c["_members"], key=lambda m: (order.get(m["tag"], 2), -len(str(m["row"].get("why") or ""))))[0]
    return dict(m["row"])


def apply(date, cands, verdicts, log=print):
    sp = os.path.join(WORK, "%s.settled.json" % date)
    S = J(sp)
    if S is None:
        raise SystemExit("%s: no settled file to judge" % date)
    bp = os.path.join(WORK, "%s.settled.readers.json" % date)
    if not os.path.exists(bp) or (J(bp, {}) or {}).get("rows") != S.get("rows") and S.get("judged_by") != RULE:
        W(bp, S)                                               # the readers' own settle, kept as it was
    base = J(bp)
    keep_other = [r for r in base["rows"] if not family(r.get("kind"), r.get("tier"))]
    kept, record_ = [], []
    for c in cands:
        ps = {tag: p_slip((verdicts.get(tag) or {}).get(c["id"])) for tag, _, _ in JUDGES}
        p = sum(ps.values()) / len(ps)
        why = {tag: ((verdicts.get(tag) or {}).get(c["id"]) or {}).get("why") for tag, _, _ in JUDGES}
        record_.append({"id": c["id"], "t": c["t"], "family": c["family"], "readers": c["readers"], "p": round(p, 3), "p_by_judge": ps,
                        "kept": p >= THRESHOLD, "why": why, "claims": c["claims"]})
        if p >= THRESHOLD:
            r = best_row(c)
            r.update({"agreed_by": "judge panel (Opus + Argon, p %.2f)" % p, "judge_p": round(p, 3), "judge_why": why,
                      "readers": c["readers"], "confidence": "high" if p >= 0.8 else "medium", "rule": RULE})
            kept.append(r)
    S2 = dict(base)
    S2["rows"] = sorted(keep_other + kept, key=lambda r: sec(r.get("t") or "0:00") if re.match(r"^\d", str(r.get("t") or "")) else 0)
    S2["judged_by"] = RULE
    S2["judge_panel"] = {"threshold": THRESHOLD, "candidates": len(cands), "kept": len(kept), "readers_slip_rows": len(base["rows"]) - len(keep_other)}
    W(sp, S2)
    W(os.path.join(OUT, "%s.json" % date), {"date": date, "rule": RULE, "threshold": THRESHOLD, "judges": [j[0] for j in JUDGES],
                                             "readers": [r[0] for r in READERS], "candidates": record_})
    log("%s: %d candidates -> %d kept (the readers had %d slip rows)" % (date, len(cands), len(kept), S2["judge_panel"]["readers_slip_rows"]))
    return S2


def run(date, dry=False, log=print):
    pool = pool_rows(date, dry, log)
    cands = candidates(pool)
    log("%s: %d candidates from %s" % (date, len(cands), ", ".join("%s %d" % (k, len(v)) for k, v in pool.items())))
    if dry:
        return cands
    import hashlib
    sig = hashlib.sha256(json.dumps([c["claims"] for c in cands], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    verdicts = judge(date, cands, sig, log)
    return apply(date, cands, verdicts, log)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        run(a.date, a.dry_run)
    except CapReached as e:
        print("judge panel NOT run for %s: %s - the lesson keeps the readers' rows" % (a.date, e))
        sys.exit(3)
