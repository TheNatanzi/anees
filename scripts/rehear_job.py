# -*- coding: utf-8 -*-
"""Money and Batch plumbing for the Gemini re-hear backfill of the lessons (TR-22 / PR-18; overnight spec 2026-10-04).

One allowance for the whole job, in Medi's words (grill, 2026-10-04, decision 4): "Batch, Gemini limit $45 for this
job, finish when it finishes" - "Stop and report if the limit would be passed; never raise a cap yourself."
It is its own named allowance (as bench_run.BENCH_EXTRA was for the benchmark): the pipeline's cap
(pipeline_ext.CAPS) and the benchmark's allowance are not touched and not drawn on.

Every paid request of the job goes through Google's Batch mode (scripts/batch_jobs.py: half price). A stage of a lesson
is one job `<stage>-run<n>` in data/lesson-work/rehear/<date>/jobs/ (git-ignored: request files hold base64 audio); its
answers are stored in a run file that IS kept (raw answers, never hand-edited). Rules kept:
  - the allowance is checked BEFORE a job is submitted: dollars of every collected answer + the estimate of every job
    submitted and not collected yet + this job's estimate must stay inside the limit;
  - every collected answer writes a run line (bench_run.paid) with Google's real price (bench_run.PRICE, Batch = half);
  - an answer that never reached the engine (no credit, daily limit, 429) is never stored: it is not the engine's miss
    and is sent again by `missing_part` without paying twice for the others;
  - collect is idempotent: a line already stored is skipped (the PC may sleep; credit may run out mid-job).
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import batch_jobs as BJ  # noqa: E402

MODEL = BV.MODEL                                  # gemini-3.8-flash
PRICE_FACTOR = 0.5                                # Google's Batch mode
BACKFILL_LIMIT_USD = 45.0                         # Medi 2026-10-04: "Gemini limit $45 for this job"
RESERVE = 1.15                                    # an estimate is a reservation: held 15 % high until the job's real dollars are in
REHEAR = os.path.join(BC.REPO, "data", "lesson-work", "rehear")
LOCK = os.path.join(REHEAR, ".submit.lock")       # one submit at a time, any lesson: two processes never both pass the allowance check


def jobs_dir(date):
    return os.path.join(REHEAR, date, "jobs")


def all_jobs():
    """Every job file of the backfill, any lesson: [(path, record)]."""
    out = []
    if not os.path.isdir(REHEAR):
        return out
    for date in sorted(os.listdir(REHEAR)):
        d = os.path.join(REHEAR, date, "jobs")
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".job.json"):
                    out.append((os.path.join(d, f), BC.J(os.path.join(d, f)) or {}))
    return out


SPEND_P = os.path.join(REHEAR, "spend.json")       # TR-29: the committed money record (job files are git-ignored)
BACKFILL_LAST = "2026-10-02"                      # the backfill job's lessons; later lessons draw on Medi's new-lessons allowance


def spend_doc():
    return BC.J(SPEND_P) or {}


def spent(but=None):
    """The backfill's dollars: this checkout's job files, never less than the committed record (the backfill ran in
    another checkout, C:/dev/anees-wt-bench - from here its $43.99 was invisible and the allowance looked untouched)."""
    local = _spent_local(but, lambda d: d <= BACKFILL_LAST)
    return round(max(local, float(((spend_doc().get("backfill") or {}).get("spent_usd")) or 0.0)), 4)


def new_lessons_spent(month, but=None):
    """Dollars of the new-lessons allowance in one month (YYYY-MM, by the lesson date): committed jobs of every checkout
    + this checkout's job files not yet recorded."""
    rec = ((spend_doc().get("new_lessons") or {}).get("jobs")) or {}
    usd = {k: float(v.get("usd") or 0.0) for k, v in rec.items() if str(v.get("date", ""))[:7] == month}
    for p, j in all_jobs():
        d = os.path.basename(os.path.dirname(os.path.dirname(p)))
        if d <= BACKFILL_LAST or d[:7] != month or (but and os.path.abspath(p) == os.path.abspath(but)):
            continue
        k = d + "/" + os.path.basename(p)
        if j.get("collected_complete"):
            usd[k] = j.get("usd") or 0.0
        elif j.get("job") or j.get("create_attempted"):
            usd[k] = max(j.get("est_usd") or 0.0, j.get("usd") or 0.0, usd.get(k, 0.0))
    return round(sum(usd.values()), 4)


def new_lessons_limit():
    return float(((spend_doc().get("new_lessons") or {}).get("monthly_usd")) or 0.0)


def _spent_local(but=None, keep=lambda d: True):
    """Dollars against the allowance: a collected job's real dollars; a job submitted and not (fully) collected counts at
    its estimate or its collected dollars, whichever is more - also a job whose create was attempted and whose answer
    was lost (it may exist at Google). A job file that never reached create is $0."""
    usd = 0.0
    for p, j in all_jobs():
        if but and os.path.abspath(p) == os.path.abspath(but):
            continue
        if not keep(os.path.basename(os.path.dirname(os.path.dirname(p)))):
            continue
        if j.get("collected_complete"):
            usd += j.get("usd") or 0.0
        elif j.get("job") or j.get("create_attempted"):          # submitted, or a create whose answer was lost (unresolved)
            usd += max(j.get("est_usd") or 0.0, j.get("usd") or 0.0)
    return round(usd, 4)


def room():
    return round(BACKFILL_LIMIT_USD - spent(), 4)


def estimate(requests, out_tokens=350):
    """A job's dollars before it runs, at the Batch price: text at ~2.5 characters a token, audio at 32 tokens a second,
    `out_tokens` answer + thinking tokens a call (the baseline on 10-02: $1.64 for 1,416 calls = $0.00116 a call)."""
    p = BR.PRICE[MODEL]
    usd = 0.0
    for chars, secs in requests:
        usd += (chars / 2.5 * p[0] + secs * 32 * p[1] + out_tokens * p[2]) / 1e6
    return round(usd * PRICE_FACTOR * RESERVE, 4)


def submit(date, name, est_usd):
    """PAID. Submits the built job `name` of this lesson after the allowance check. Returns the job record."""
    folder = jobs_dir(date)
    P = BJ.paths(folder, name)

    def cap(est):
        if date > BACKFILL_LAST:                  # TR-29: a lesson after the backfill draws on Medi's new-lessons allowance only
            m, lim = date[:7], new_lessons_limit()
            s = new_lessons_spent(m, but=P["job"])
            if s + est > lim:
                return "new-lessons allowance (Medi's, data/lesson-work/rehear/spend.json): $%.2f spent or owed in %s + $%.2f for %s %s > $%.2f - stopped, nothing sent" % (
                    s, m, est, date, name, lim)
            return None
        s = spent(but=P["job"])
        if s + est > BACKFILL_LIMIT_USD:
            return "backfill allowance (Medi 2026-10-04: $%.0f for this job): $%.2f spent or owed + $%.2f for %s %s > $%.2f - stopped, nothing sent" % (
                BACKFILL_LIMIT_USD, s, est, date, name, BACKFILL_LIMIT_USD)
        return None
    os.makedirs(REHEAR, exist_ok=True)
    t0 = time.time()
    while True:
        try:
            os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            if time.time() - os.path.getmtime(LOCK) > 3600:      # a lock left by a killed process
                os.unlink(LOCK)
            elif time.time() - t0 > 1800:
                raise SystemExit("another submit holds %s" % LOCK)
            else:
                time.sleep(2)
    try:
        rec = BJ.submit(folder, name, est_usd, cap_check=cap)
    finally:
        if os.path.exists(LOCK):
            os.unlink(LOCK)
    print("submitted %s %s: %s (about $%.2f; $%.2f of $%.0f used or owed)" % (date, name, rec.get("job"), est_usd, spent(), BACKFILL_LIMIT_USD), flush=True)
    return rec


def collect(date, name, run_path, label, seconds_of=None, parse=None, wanted=None):
    """The answers of job `name` (and of its `.p2`, `.p3` parts) -> the run file (kept). Returns (record, missing keys).
    parse(response) -> row; default bench_run.gemini_parse (JSON answer {"arabic", "arabizi"} -> text / alt / raw)."""
    folder = jobs_dir(date)
    parse = parse or (lambda resp: BR.gemini_parse(MODEL, resp, as_json=True, price_factor=PRICE_FACTOR))
    rec = BC.J(run_path) or {"label": label, "job": name, "model": MODEL, "transport": "batch", "price_factor": PRICE_FACTOR, "lines": {}, "cost_usd": 0.0}
    rec["lines"] = {i: o for i, o in rec["lines"].items() if not BV.unreached(o.get("error"))}
    os.environ["ANEES_RUNS_DIR"] = os.path.join(REHEAR, date, "runs")
    names = [name] + [f[:-len(".job.json")] for f in sorted(os.listdir(folder)) if f.startswith(name + ".p") and f.endswith(".job.json")]
    skipped = []
    for nm in names:
        P = BJ.paths(folder, nm)
        job = BC.J(P["job"]) or {}
        if not job.get("job"):
            continue
        st = BJ.status(folder, nm)
        if st.get("state") != "JOB_STATE_SUCCEEDED":
            print("  %s %s: %s - not collected yet" % (date, nm, st.get("state")), flush=True)
            continue
        path = BJ.fetch(folder, nm)
        usd_job, seen = 0.0, set()
        for key, resp, err in BJ.rows(path):
            if key in seen:                                        # a key twice in one results file: the first answer stands
                continue
            seen.add(key)
            if resp is not None and isinstance(resp.get("error"), dict) and not resp.get("candidates"):
                resp, err = None, BJ.err_text(resp["error"])       # an error nested inside the response object
            out = parse(resp) if resp is not None else {"text": "", "error": err}
            usd = out.pop("usd", 0.0) or 0.0
            usd_job += usd
            if key in rec["lines"]:
                continue
            if BV.unreached(out.get("error")):
                skipped.append(key)
                continue
            out.update(usd=round(usd, 6), job=nm, logged=False)
            rec["lines"][key] = out
            rec["cost_usd"] = round(rec["cost_usd"] + usd, 6)
        # Order (Codex audit 2026-10-04): the answers are SAVED first; then each gets its run line once - a line already in
        # the run-lines folder for this (job, key) is never written again, and an answer is marked logged only when its
        # line was really written; only then is the job marked collected, and only when every key it was sent has a
        # stored answer (else its reservation stays).
        BC.W(run_path, rec)
        have = _logged(os.environ["ANEES_RUNS_DIR"])
        n_log = 0
        for key, out in rec["lines"].items():
            if out.get("logged") is False:
                if not out.get("usd") or (out.get("job"), key) in have or _run_line(date, label, out.get("job"), key, out["usd"], seconds_of(key) if seconds_of else None):
                    out["logged"] = True
                n_log += 1
                if n_log % 200 == 0:
                    BC.W(run_path, rec)
        BC.W(run_path, rec)
        sent = (BC.J(P["build"]) or {}).get("keys") or []
        job = BC.J(P["job"]) or {}
        job.update(usd=round(usd_job, 6), collected=time.strftime("%Y-%m-%dT%H:%M:%S"),
                   collected_complete=bool(sent) and all(k in rec["lines"] for k in sent))
        BC.W(P["job"], job)
    build = BC.J(BJ.paths(folder, name)["build"]) or {}
    want = list(wanted) if wanted is not None else (build.get("keys") or [])
    missing = [k for k in want if k not in rec["lines"]]
    rec["complete"] = bool(want) and not missing
    rec["collected"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    BC.W(run_path, rec)
    errs = sum(1 for v in rec["lines"].values() if v.get("error"))
    print("%s %s: %d of %d answers, %d stored errors, $%.3f%s" % (date, name, len(rec["lines"]), len(want), errs, rec["cost_usd"], "" if rec["complete"] else "  NOT complete (%d missing, %d never reached the engine)" % (len(missing), len(skipped))), flush=True)
    return rec, missing


def _logged(runs_dir):
    """{(job, key)} of the answers that already have a run line in this folder."""
    have = set()
    if os.path.isdir(runs_dir):
        for f in os.listdir(runs_dir):
            if f.endswith(".jsonl"):
                with open(os.path.join(runs_dir, f), encoding="utf-8") as fh:
                    for raw in fh:
                        try:
                            p = (json.loads(raw).get("params") or {})
                        except ValueError:
                            continue
                        if p.get("job") and p.get("key") is not None:
                            have.add((p["job"], str(p["key"])))
    return have


def _run_line(date, label, job, key, usd, seconds):
    """One paid answer = one run line (never text), findable by its job and request key. True when it was written."""
    import track
    return bool(track.log_run(label, date, kind="eval", provider="google", request_model=MODEL, response_model=MODEL, cost_usd=round(usd, 6),
                              params={"rule": "TR-22", "mode": "batch", "job": job, "key": str(key), "audio_s": seconds, "price_factor": PRICE_FACTOR}))


def state(date, name):
    """'none' / 'built' / the remote job state (refreshed)."""
    folder = jobs_dir(date)
    P = BJ.paths(folder, name)
    job = BC.J(P["job"])
    if not job or not job.get("job"):
        return "built" if os.path.exists(P["build"]) else "none"
    return BJ.status(folder, name).get("state")


def wait(pairs, every=60, max_s=6 * 3600):
    """Blocks until every (date, name) job is done (any end state). Returns {(date, name): state}."""
    t0, out = time.time(), {}
    while True:
        out = {(d, n): state(d, n) for d, n in pairs}
        if all(s in BJ.DONE for s in out.values()) or time.time() - t0 > max_s:
            return out
        time.sleep(every)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("backfill allowance: $%.2f used or owed of $%.0f (room $%.2f)" % (spent(), BACKFILL_LIMIT_USD, room()))
    for p, j in all_jobs():
        print("  %-70s %-22s est $%-7s real $%s" % (os.path.relpath(p, REHEAR), j.get("state"), j.get("est_usd"), j.get("usd")))
