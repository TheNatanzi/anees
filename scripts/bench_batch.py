# -*- coding: utf-8 -*-
"""The baseline listener through Google's Batch mode (PR-18). Engine id `gemini-flash-batch-t1`.

Medi 2026-10-04: "A: 3 runs by Batch, about $1.67 a lesson, after one check run on 10-02 that it scores the same".
The ONLY difference from gemini-flash-t1 is the transport: the same clips, the same frozen prompts (prompts.json
arms.ctx, re-hashed against the manifest), the same request body (bench_run.gemini_body: his wav inline, then the
text, temperature 1, responseMimeType application/json) and the same answer parsing (bench_run.gemini_parse), priced
at HALF of bench_run.PRICE (Google: Batch is 50 % of the standard price).

    python scripts/bench_batch.py 2026-10-02 build <run n>     # the JSONL on this PC only (no network)
    python scripts/bench_batch.py 2026-10-02 submit <run n>    # PAID: upload the JSONL + create the batch job
    python scripts/bench_batch.py 2026-10-02 status            # the state of every submitted run
    python scripts/bench_batch.py 2026-10-02 collect <run n>   # download the answers -> gemini-flash-batch-t1/line-run<n>.json
    python scripts/bench_batch.py 2026-10-02 submit-missing <run n>   # PAID: after a collect, the lines with no answer as part 2, 3, ..
    python scripts/bench_batch.py 2026-10-02 recover <run n>   # a job Google created but this PC never saved: find it by its display name
    python scripts/bench_batch.py 2026-10-02 compare           # baseline vs batch, from scores.json (after bench_score.py)

The transport itself (the JSONL, the job file, upload / create / status / list / download, the two shapes of Google's
answers) is scripts/batch_jobs.py, which knows nothing about the benchmark; this file is the benchmark's side: which
lines, which prompts, the money cap, the run file. Every network call is one of the five functions of batch_jobs
(upload_file, create_batch, get_batch, download_file, list_batches); this module keeps its own names for them and
hands THOSE to batch_jobs (_net), so the tests replace them here; nothing else in this file touches the network.

Rules kept: creating a job is not idempotent, so a run that already has a job file is never submitted twice; the money
cap (PR-10: pipeline cap + the benchmark allowance) is checked BEFORE submit with the run's cost estimated from the
baseline's token counts; every collected answer writes a run line (bench_run.paid); a request that failed for quota /
no credit is never stored as the engine's miss (bench_vars.unreached). Such lines (and lines absent from the results)
are sent again as a later PART of the same run (submit-missing: bench/<date>/batch/run<n>.p2.jsonl, .p3, ..), built
from the original JSONL line for line; collect reads every part, and a line already stored is never paid twice.
"""
import json, os, sys, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import batch_jobs as BJ  # noqa: E402

ENGINE = "gemini-flash-batch-t1"
BASE = BV.BASE                    # gemini-flash-t1, the instant baseline
MODEL = BV.MODEL                  # gemini-3.8-flash
ARM = "ctx"
TEMP = 1
PRICE_FACTOR = 0.5                # Google's Batch mode: half the standard price
API, DONE, RPC_HTTP = BJ.API, BJ.DONE, BJ.RPC_HTTP
job_state, responses_file, err_text = BJ.job_state, BJ.responses_file, BJ.err_text      # moved to batch_jobs, same behaviour
# the network: batch_jobs' five functions under this module's own names (the tests replace them here)
upload_file, create_batch, get_batch, download_file, list_batches = BJ.upload_file, BJ.create_batch, BJ.get_batch, BJ.download_file, BJ.list_batches


def _net():
    """The five network functions as this module holds them NOW (a test's replacement included), for batch_jobs."""
    return types.SimpleNamespace(upload_file=upload_file, create_batch=create_batch, get_batch=get_batch, download_file=download_file, list_batches=list_batches)


def bdir(date):
    return os.path.join(BC.bench_dir(date), "batch")


def jname(n, part=1):
    """The job's name in batch_jobs: run<n>, and run<n>.p2, .p3, .. for the later parts (the lines that got no answer)."""
    return BJ.part_name("run%d" % n, part)


def paths(date, n, part=1):
    P = BJ.paths(bdir(date), jname(n, part))
    P["run"] = os.path.join(BC.bench_dir(date), ENGINE, "line-run%d.json" % n)
    return P


def parts(date, n):
    """[part] of run n that were built or submitted (1 always)."""
    return [k for k, _ in BJ.parts(bdir(date), "run%d" % n)]


# ------------------------------------------------------------------ the requests (no network)

def items(date):
    """[(line i, clip path, prompt)] - exactly the lines and prompts bench_run.run_engine sends for gemini-flash-t1.
    The frozen prompts are re-hashed against the manifest first: a prompt changed after the freeze never runs."""
    d = BC.bench_dir(date)
    man = BC.J(os.path.join(d, "manifest.json"))
    if BC.sha_file(os.path.join(d, "prompts.json")) != man["prompts_sha256"]:
        raise SystemExit("prompts.json does not match the manifest (prompts_sha256): not building")
    if BC.sha_file(os.path.join(d, "truth.json")) != man["truth_sha256"]:
        raise SystemExit("truth.json does not match the manifest: not building")
    truth = BC.J(os.path.join(d, "truth.json"))
    prompts = BC.J(os.path.join(d, "prompts.json"))["arms"][ARM]
    out = []
    for ln in truth["lines"]:
        if not ln["listen"]:
            continue
        clip = os.path.join(d, ln["clip"])
        want = (man.get("clips") or {}).get(ln["clip"].replace("\\", "/"))
        if want and BC.sha_file(clip) != want:
            raise SystemExit("clip %s does not match its frozen hash: not building" % ln["clip"])
        out.append((str(ln["i"]), clip, prompts[str(ln["i"])]))
    return out


def request_line(i, clip, prompt):
    """One JSONL line: the instant call's own body plus its key."""
    return {"key": str(i), "request": BR.gemini_body(MODEL, clip, prompt, as_json=True, temp=TEMP)}


def build(date, n):
    P = paths(date, n)
    its = items(date)
    info = BJ.build(bdir(date), jname(n), MODEL, ((i, request_line(i, clip, prompt)["request"]) for i, clip, prompt in its),
                    meta={"engine": ENGINE, "run": n, "prompts_sha256": BC.sha_file(os.path.join(BC.bench_dir(date), "prompts.json"))})
    print("built %s: %d requests, %d bytes (%.1f MB), sha %s" % (P["jsonl"], info["requests"], info["bytes"], info["bytes"] / 1e6, info["jsonl_sha256"][:16]))
    return info


# ------------------------------------------------------------------ money (PR-10), before submit

def estimate(date, n, part=1):
    """This JOB's cost at the Batch price: the baseline's average cost of one line x the number of requests in the
    job's build (a part holds only the missing lines, so it is priced pro rata; the whole lesson when nothing is built).
    Only a COMPLETE baseline run is used - rec["complete"] true AND every listen line there, with token counts on
    every line that is not a stored error - because an average over half a run prices the wrong lines. Run n when it
    is complete, else any complete one, else None (submit refuses on None)."""
    d = BC.bench_dir(date)
    p = BR.PRICE[MODEL]
    want = [i for i, _, _ in items(date)]
    for k in [n] + [x for x in (1, 2, 3) if x != n]:
        r = BC.J(os.path.join(d, BASE, "line-run%d.json" % k)) or {}
        L = r.get("lines") or {}
        if not r.get("complete") or any(i not in L or not (L[i].get("error") or L[i].get("tokens")) for i in want):
            continue
        tk = [L[i]["tokens"] for i in want if L[i].get("tokens")]
        if tk:
            tin, aud, tout = (sum(x[c] for x in tk) for c in range(3))
            per_line = ((tin - aud) * p[0] + aud * p[1] + tout * p[2]) / 1e6 / len(tk)
            return round(per_line * ((BC.J(paths(date, n, part)["build"]) or {}).get("requests") or len(want)) * PRICE_FACTOR, 4)
    return None


def outstanding(date, but=None):
    """Dollars of batch jobs already submitted whose answers are not collected yet (they are owed, not yet in a run
    file). Every part of a run counts; a job whose answers were collected, or that failed / was cancelled / expired,
    owes nothing more."""
    usd = 0.0
    for k in (1, 2, 3):
        if k == but or (BC.J(paths(date, k)["run"]) or {}).get("complete"):
            continue
        for part in parts(date, k):
            job = BC.J(paths(date, k, part)["job"])
            if job and not job.get("collected") and job.get("state") not in DONE[1:]:
                usd += job.get("est_usd") or 0.0
    return usd


def cap_room(date, n, part=1):
    """(spent so far incl. submitted-but-uncollected runs, this job's estimate, the limit). Same sums as bench_vars.run().
    money_base leaves this run file's own cost out (a fresh run has none); a later part adds it back: it was paid."""
    spent, limit = BV.money_base(date, paths(date, n)["run"])
    if part > 1:
        spent += (BC.J(paths(date, n)["run"]) or {}).get("cost_usd") or 0.0
    return spent + outstanding(date, but=n), estimate(date, n, part), limit


# ------------------------------------------------------------------ submit / status / collect

def label(n, part=1):
    return "run %d" % n if part == 1 else "run %d part %d" % (n, part)


def submit(date, n, part=1):
    """PAID. The benchmark's checks (built, not collected, the lesson's lines unchanged, the cap), then batch_jobs.submit,
    which writes the job file with its display name BEFORE the upload and, when an earlier submit crashed between
    Google creating the job and this PC saving it, attaches that job instead of creating a second one."""
    P = paths(date, n, part)
    info = BC.J(P["build"])
    if not info or not os.path.exists(P["jsonl"]):
        raise SystemExit("run %d is not built: python scripts/bench_batch.py %s build %d" % (n, date, n))
    job = BC.J(P["job"])
    if job and (job.get("job") or not job.get("display_name")):
        raise SystemExit("%s was already submitted (%s): a batch job is never created twice. Delete %s only if that job is gone." % (label(n, part), job.get("job"), P["job"]))
    if (BC.J(P["run"]) or {}).get("complete"):
        raise SystemExit("run %d is already collected" % n)
    if BC.sha_file(P["jsonl"]) != info["jsonl_sha256"] or (part == 1 and len(items(date)) != info["requests"]):
        raise SystemExit("%s: the JSONL changed since it was built - build it again" % label(n, part))
    spent, est, limit = cap_room(date, n, part)
    if est is None:
        raise SystemExit("no baseline token counts to estimate the cost from: not submitting")
    cap = lambda e: None if spent + e <= limit else "budget cap (PR-10) for %s: $%.2f spent or owed + $%.2f for this run > $%.2f" % (ENGINE, spent, e, limit)  # noqa: E731
    rec = BJ.submit(bdir(date), jname(n, part), est, cap_check=cap, net=_net())
    if rec.get("recovered"):
        print("recovered %s: %s was created by an earlier submit and is attached, not created again (%s)" % (label(n, part), rec["job"], rec.get("state")))
    else:
        print("submitted %s: %s (%d requests, about $%.2f at the Batch price)" % (label(n, part), rec["job"], info["requests"], est))
    return rec


def recover(date, n):
    """Every part of run n whose job file has no job id: look the job up at Google by its display name and attach it.
    Free (one list call). Returns the job records that were attached."""
    out, pending = [], 0
    for part in parts(date, n):
        job = BC.J(paths(date, n, part)["job"])
        if not job or job.get("job"):
            continue
        pending += 1
        rec = BJ.recover(bdir(date), jname(n, part), net=_net())
        print("%s: %s" % (label(n, part), ("attached %s (%s)" % (rec["job"], rec.get("state"))) if rec else
                          "no job at Google carries the display name %s - nothing was created; submit it again" % job.get("display_name")))
        out += [rec] if rec else []
    if not pending:
        print("run %d: nothing to recover (no job file is waiting for its job id)" % n)
    return out


def status(date):
    seen = 0
    for n in (1, 2, 3):
        for part in parts(date, n):
            P = paths(date, n, part)
            job = BC.J(P["job"])
            if not job:
                continue
            seen += 1
            if not job.get("job"):
                print("%s: the file was uploaded (%s) but no job was created" % (label(n, part), job.get("file")))
                continue
            job = BJ.status(bdir(date), jname(n, part), net=_net())
            print("%s: %s %s %s%s" % (label(n, part), job["job"], job["state"], json.dumps(job["stats"]) if job["stats"] else "",
                                      "  (collected)" if (BC.J(P["run"]) or {}).get("complete") else ""))
    if not seen:
        print("no batch run was submitted yet")


def collect_file(date, n, results_path, job=None, part=1):
    """The results JSONL -> gemini-flash-batch-t1/line-run<n>.json. Each line of the file is {"key", "response"} (a
    GenerateContentResponse) or {"key", "error"/"status"}. Run again on the same file it changes nothing: a line
    already stored is skipped, so no answer is paid or logged twice. The results of a later part (submit-missing) go
    through this same function into the same run file: only the lines still missing are added."""
    P = paths(date, n)
    want = [i for i, _, _ in items(date)]
    clip = {i: c for i, c, _ in items(date)}
    rec = BC.J(P["run"]) or {"engine": ENGINE, "mode": "line", "run": n, "lines": {}, "cost_usd": 0.0, "seconds": 0.0, "model": MODEL,
                             "transport": "batch", "price_factor": PRICE_FACTOR}
    rec["lines"] = {i: o for i, o in rec["lines"].items() if not BV.unreached(o.get("error"))}
    rec["complete"] = False
    os.environ["ANEES_RUNS_DIR"] = os.path.join(BC.bench_dir(date), "runs", ENGINE)
    skipped, unknown = [], []
    for i, resp, err in BJ.rows(results_path):
        if i not in clip:
            unknown.append(i)
            continue
        if i in rec["lines"]:
            continue
        out = BR.gemini_parse(MODEL, resp, as_json=True, price_factor=PRICE_FACTOR) if resp is not None else {"text": "", "error": err}
        if BV.unreached(out.get("error")):              # quota / no credit / rate limit: never the engine's miss
            skipped.append(i)
            continue
        usd = out.pop("usd", 0.0)
        if usd:
            BR.paid(date, ENGINE, "line", n, MODEL, usd, BR.wav_seconds(clip[i]), provider="google")
        out["usd"] = round(usd, 6)
        rec["lines"][i] = out
        rec["cost_usd"] = round(rec["cost_usd"] + usd, 6)
    if job and part == 1:
        rec.update(job=job.get("job"), submitted=job.get("submitted"))
    elif job:
        rec.setdefault("parts", {})[str(part)] = job.get("job")
    rec["collected"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    missing = [i for i in want if i not in rec["lines"]]
    rec["complete"] = not missing
    BC.W(P["run"], rec)
    errs = sum(1 for v in rec["lines"].values() if v.get("error"))
    print("%s run %d: %d of %d lines, %d stored errors, $%.3f%s" % (ENGINE, n, len(rec["lines"]), len(want), errs, rec["cost_usd"], "" if rec["complete"] else "  NOT complete"))
    if skipped:
        print("  %d requests never reached the engine (quota / credit / rate limit) and are not stored: %s" % (len(skipped), ", ".join(skipped[:12])))
    if missing:
        print("  %d lines have no answer: %s" % (len(missing), ", ".join(missing[:12])))
    if unknown:
        print("  %d result rows carry a key that is not a line: %s" % (len(unknown), ", ".join(unknown[:6])))
    return rec


def collect(date, n):
    """Downloads and stores the answers of run n: part 1, then every later part that exists (submit-missing). Safe to
    run again: collect_file skips a line already stored. A later part that is not finished yet is said and skipped, so
    the answers that are there are still stored."""
    job = BC.J(paths(date, n)["job"])
    if not job or not job.get("job"):
        raise SystemExit("run %d was not submitted" % n)
    rec = None
    for part in parts(date, n):
        P = paths(date, n, part)
        job = BC.J(P["job"])
        if not job or not job.get("job"):
            print("  %s was built but has no job: not collected" % label(n, part))
            continue
        try:
            res = BJ.fetch(bdir(date), jname(n, part), net=_net(), label=label(n, part))
        except SystemExit as e:
            if part == 1:
                raise
            print("  %s" % e)
            continue
        rec = collect_file(date, n, res, BC.J(P["job"]), part)
        job = BC.J(P["job"])
        job["collected"] = rec["collected"]             # its answers are in the run file: no longer owed (outstanding)
        BC.W(P["job"], job)
    return rec


def missing(date, n):
    """The listen lines of run n with no stored answer (never reached the engine, or absent from the results)."""
    L = (BC.J(paths(date, n)["run"]) or {}).get("lines") or {}
    return [i for i, _, _ in items(date) if i not in L or BV.unreached(L[i].get("error"))]


def submit_missing(date, n):
    """PAID. After a collect that left lines with no answer: builds the next part (run<n>.p2.jsonl, .p3, ..) from the
    ORIGINAL JSONL with exactly those lines and submits it, cap-checked with a pro-rata estimate. Refuses while an
    earlier part's answers are still out (they may hold these very lines: sending them again would pay twice)."""
    run = BC.J(paths(date, n)["run"])
    if not run:
        raise SystemExit("run %d has no collected answers yet: python scripts/bench_batch.py %s collect %d" % (n, date, n))
    miss = missing(date, n)
    if run.get("complete") or not miss:
        raise SystemExit("run %d has an answer for every line: nothing to send again" % n)
    last = parts(date, n)[-1]
    for part in parts(date, n)[1:]:
        job = BC.J(paths(date, n, part)["job"])
        if not job:                                   # built, never submitted: built again below from today's missing lines
            continue
        if not job.get("job"):                        # a submit that crashed: attach the job or create it, never a new part
            return submit(date, n, part)
        if not job.get("collected"):
            st = BJ.status(bdir(date), jname(n, part), net=_net())["state"]
            if st == "JOB_STATE_SUCCEEDED" or st not in DONE:
                raise SystemExit("%s (%s) is %s and its answers are not collected: python scripts/bench_batch.py %s collect %d first" % (label(n, part), job["job"], st, date, n))
    part = last if last > 1 and not BC.J(paths(date, n, last)["job"]) else last + 1
    info = BJ.missing_part(bdir(date), jname(n), miss, part)
    print("built %s: %d requests (the lines with no answer), %d bytes, sha %s" % (paths(date, n, part)["jsonl"], info["requests"], info["bytes"], info["jsonl_sha256"][:16]))
    return submit(date, n, part)


# ------------------------------------------------------------------ compare (reads scores.json; no call)

ROWS = (("heard right (of %(moments)s)", "hit"), ("your slips hidden (of %(slips_judged)s)", "hidden_slips"),
        ("untouched lines with a word changed (of %(should_stay)s)", "content_changes"), ("same answer in 3 of 3 runs, %%", "stable_pct"),
        ("runs scored", "runs"), ("cost, $", "cost_usd"))


def compare(date):
    """Baseline vs Batch from scores.json. Says plainly when the Batch runs are not there yet. Returns 0 when printed."""
    d = BC.bench_dir(date)
    done = [n for n in (1, 2, 3) if (BC.J(paths(date, n)["run"]) or {}).get("complete")]
    S = BC.J(os.path.join(d, "scores.json")) or {}
    a, b = S.get(BASE + "|line"), S.get(ENGINE + "|line")
    if not b:
        print("Nothing to compare yet: the Batch engine (%s) has not been run and scored." % ENGINE)
        print("  collected runs: %s of 3" % (", ".join(map(str, done)) or "none"))
        print("  to get there: build / submit / collect each run, then `python scripts/bench_score.py %s`, then this command again." % date)
        return 1
    if not a:
        print("scores.json has no baseline row (%s): run `python scripts/bench_score.py %s`." % (BASE, date))
        return 1
    print("%-52s %12s %12s" % ("lesson %s" % date, "instant", "batch"))
    for label, k in ROWS:
        print("%-52s %12s %12s" % (label % a, a.get(k), b.get(k)))
    if b.get("runs") != a.get("runs"):
        print("NOTE: the Batch engine has %s scored run(s), the baseline %s: the two columns are not like for like yet." % (b.get("runs"), a.get("runs")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if len(argv) < 2 or argv[1] not in ("build", "submit", "status", "collect", "compare", "submit-missing", "recover") or (argv[1] in ("build", "submit", "collect", "submit-missing", "recover") and len(argv) < 3):
        raise SystemExit(__doc__)
    date, cmd = argv[0], argv[1]
    if cmd == "build":
        build(date, int(argv[2]))
    elif cmd == "submit":
        submit(date, int(argv[2]))
    elif cmd == "status":
        status(date)
    elif cmd == "collect":
        collect(date, int(argv[2]))
    elif cmd == "submit-missing":
        submit_missing(date, int(argv[2]))
    elif cmd == "recover":
        recover(date, int(argv[2]))
    else:
        sys.exit(compare(date))
