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
    python scripts/bench_batch.py 2026-10-02 compare           # baseline vs batch, from scores.json (after bench_score.py)

REST shapes from https://ai.google.dev/gemini-api/docs/batch-api (read 2026-10-04), file-based input:
    JSONL line   {"key": "<line i>", "request": <GenerateContentRequest>}
    upload       POST https://generativelanguage.googleapis.com/upload/v1beta/files   (resumable: start, then upload+finalize)
    create       POST https://generativelanguage.googleapis.com/v1beta/models/<model>:batchGenerateContent
                 {"batch": {"display_name": ..., "input_config": {"file_name": "files/..."}}}   -> {"name": "batches/..."}
    status       GET  https://generativelanguage.googleapis.com/v1beta/batches/...
    results      GET  https://generativelanguage.googleapis.com/download/v1beta/<responses file>:download?alt=media
Every network call is one of the four small functions below (upload_file, create_batch, get_batch, download_file) so
the tests replace them; nothing else in this file touches the network.

Rules kept: creating a job is not idempotent, so a run that already has a job file is never submitted twice; the money
cap (PR-10: pipeline cap + the benchmark allowance) is checked BEFORE submit with the run's cost estimated from the
baseline's token counts; every collected answer writes a run line (bench_run.paid); a request that failed for quota /
no credit is never stored as the engine's miss (bench_vars.unreached).
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402

ENGINE = "gemini-flash-batch-t1"
BASE = BV.BASE                    # gemini-flash-t1, the instant baseline
MODEL = BV.MODEL                  # gemini-3.8-flash
ARM = "ctx"
TEMP = 1
PRICE_FACTOR = 0.5                # Google's Batch mode: half the standard price
API = "https://generativelanguage.googleapis.com"
DONE = ("JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED")
# google.rpc codes a failed request may carry -> the HTTP status the instant call would have shown
RPC_HTTP = {8: 429, 14: 503, 4: 504, 13: 500, 3: 400, 7: 403, 5: 404, 9: 400}


def bdir(date):
    return os.path.join(BC.bench_dir(date), "batch")


def paths(date, n):
    b = bdir(date)
    return {"jsonl": os.path.join(b, "run%d.jsonl" % n), "build": os.path.join(b, "run%d.build.json" % n),
            "job": os.path.join(b, "run%d.job.json" % n), "results": os.path.join(b, "run%d.results.jsonl" % n),
            "run": os.path.join(BC.bench_dir(date), ENGINE, "line-run%d.json" % n)}


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
    os.makedirs(bdir(date), exist_ok=True)
    with open(P["jsonl"], "w", encoding="utf-8", newline="\n") as f:
        for i, clip, prompt in its:
            f.write(json.dumps(request_line(i, clip, prompt), ensure_ascii=False) + "\n")
    info = {"engine": ENGINE, "run": n, "model": MODEL, "requests": len(its), "bytes": os.path.getsize(P["jsonl"]),
            "jsonl_sha256": BC.sha_file(P["jsonl"]), "prompts_sha256": BC.sha_file(os.path.join(BC.bench_dir(date), "prompts.json")),
            "built": time.strftime("%Y-%m-%dT%H:%M:%S")}
    BC.W(P["build"], info)
    print("built %s: %d requests, %d bytes (%.1f MB), sha %s" % (P["jsonl"], info["requests"], info["bytes"], info["bytes"] / 1e6, info["jsonl_sha256"][:16]))
    return info


# ------------------------------------------------------------------ money (PR-10), before submit

def estimate(date, n):
    """The run's cost at the Batch price, from the token counts of the baseline's run n (any complete baseline run
    when run n is missing). None when no baseline run has token counts."""
    d = BC.bench_dir(date)
    p = BR.PRICE[MODEL]
    for k in [n] + [x for x in (1, 2, 3) if x != n]:
        r = BC.J(os.path.join(d, BASE, "line-run%d.json" % k)) or {}
        tk = [v["tokens"] for v in (r.get("lines") or {}).values() if v.get("tokens")]
        if tk:
            tin, aud, tout = (sum(x[c] for x in tk) for c in range(3))
            per_line = ((tin - aud) * p[0] + aud * p[1] + tout * p[2]) / 1e6 / len(tk)
            return round(per_line * len(r["lines"]) * PRICE_FACTOR, 4)
    return None


def outstanding(date, but=None):
    """Dollars of batch runs already submitted whose answers are not collected yet (they are owed, not yet in a run file)."""
    usd = 0.0
    for k in (1, 2, 3):
        if k == but:
            continue
        P = paths(date, k)
        job = BC.J(P["job"])
        if job and not (BC.J(P["run"]) or {}).get("complete"):
            usd += job.get("est_usd") or 0.0
    return usd


def cap_room(date, n):
    """(spent so far incl. submitted-but-uncollected runs, this run's estimate, the limit). Same sums as bench_vars.run()."""
    spent, limit = BV.money_base(date, paths(date, n)["run"])
    return spent + outstanding(date, but=n), estimate(date, n), limit


# ------------------------------------------------------------------ the network (4 small functions; tests replace them)

def _headers(extra=None):
    h = {"x-goog-api-key": BR.key("GEMINI_API_KEY")}
    h.update(extra or {})
    return h


def _fail(r, what):
    raise SystemExit("%s: %d %s" % (what, r.status_code, r.text[:400].replace(BR.key("GEMINI_API_KEY"), "***")))


def upload_file(path, display_name):
    """The Files API resumable upload. Returns the file's name ("files/...")."""
    import requests
    size = os.path.getsize(path)
    r = requests.post(API + "/upload/v1beta/files", timeout=120, json={"file": {"display_name": display_name}},
                      headers=_headers({"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                        "X-Goog-Upload-Header-Content-Length": str(size), "X-Goog-Upload-Header-Content-Type": "application/jsonl"}))
    url = r.headers.get("x-goog-upload-url")
    if r.status_code != 200 or not url:
        _fail(r, "file upload (start)")
    with open(path, "rb") as f:
        r = requests.post(url, data=f, timeout=3600, headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"})
    if r.status_code != 200:
        _fail(r, "file upload (bytes)")
    return r.json()["file"]["name"]


def create_batch(model, file_name, display_name):
    """Creates the batch job (NOT idempotent). Returns Google's answer; its "name" is the job ("batches/...")."""
    import requests
    r = requests.post("%s/v1beta/models/%s:batchGenerateContent" % (API, model), timeout=120, headers=_headers({"Content-Type": "application/json"}),
                      json={"batch": {"display_name": display_name, "input_config": {"file_name": file_name}}})
    if r.status_code != 200:
        _fail(r, "batch create")
    return r.json()


def get_batch(name):
    import requests
    r = requests.get("%s/v1beta/%s" % (API, name), timeout=120, headers=_headers())
    if r.status_code != 200:
        _fail(r, "batch status")
    return r.json()


def download_file(name, out):
    import requests
    with requests.get("%s/download/v1beta/%s:download" % (API, name), params={"alt": "media"}, timeout=3600, headers=_headers(), stream=True) as r:
        if r.status_code != 200:
            _fail(r, "results download")
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return out


# ------------------------------------------------------------------ job state (Google's docs show two shapes)

def job_state(j):
    """The job's state from a status answer: the long-running-operation shape ({"metadata": {"state"}}) or the flat one."""
    return (j.get("metadata") or {}).get("state") or j.get("state") or ("JOB_STATE_UNKNOWN" if not j.get("error") else "JOB_STATE_FAILED")


def responses_file(j):
    """The results file's name: {"response": {"responsesFile"}} or {"dest": {"fileName"}} (both are in the docs)."""
    return ((j.get("response") or {}).get("responsesFile") or (j.get("dest") or {}).get("fileName")
            or (j.get("dest") or {}).get("file_name") or ((j.get("metadata") or {}).get("output") or {}).get("responsesFile"))


# ------------------------------------------------------------------ submit / status / collect

def submit(date, n):
    P = paths(date, n)
    info = BC.J(P["build"])
    if not info or not os.path.exists(P["jsonl"]):
        raise SystemExit("run %d is not built: python scripts/bench_batch.py %s build %d" % (n, date, n))
    if BC.J(P["job"]):
        raise SystemExit("run %d was already submitted (%s): a batch job is never created twice. Delete %s only if that job is gone." % (n, BC.J(P["job"]).get("job"), P["job"]))
    if (BC.J(P["run"]) or {}).get("complete"):
        raise SystemExit("run %d is already collected" % n)
    if BC.sha_file(P["jsonl"]) != info["jsonl_sha256"] or len(items(date)) != info["requests"]:
        raise SystemExit("run %d: the JSONL changed since it was built - build it again" % n)
    spent, est, limit = cap_room(date, n)
    if est is None:
        raise SystemExit("no baseline token counts to estimate the cost from: not submitting")
    if spent + est > limit:
        raise SystemExit("budget cap (PR-10) for %s: $%.2f spent or owed + $%.2f for this run > $%.2f" % (ENGINE, spent, est, limit))
    name = "anees-bench-%s-%s-run%d" % (date, ENGINE, n)
    file_name = upload_file(P["jsonl"], name)
    BC.W(P["job"], {"engine": ENGINE, "run": n, "model": MODEL, "file": file_name, "job": None, "est_usd": est, "requests": info["requests"],
                    "jsonl_sha256": info["jsonl_sha256"], "uploaded": time.strftime("%Y-%m-%dT%H:%M:%S")})      # kept even if create fails
    job = create_batch(MODEL, file_name, name)
    rec = BC.J(P["job"])
    rec.update(job=job.get("name"), state=job_state(job), submitted=time.strftime("%Y-%m-%dT%H:%M:%S"), submitted_unix=round(time.time(), 1))
    BC.W(P["job"], rec)
    print("submitted run %d: %s (%d requests, about $%.2f at the Batch price)" % (n, rec["job"], info["requests"], est))
    return rec


def status(date):
    seen = 0
    for n in (1, 2, 3):
        P = paths(date, n)
        job = BC.J(P["job"])
        if not job:
            continue
        seen += 1
        if not job.get("job"):
            print("run %d: the file was uploaded (%s) but no job was created" % (n, job.get("file")))
            continue
        j = get_batch(job["job"])
        job.update(state=job_state(j), checked=time.strftime("%Y-%m-%dT%H:%M:%S"), stats=(j.get("metadata") or {}).get("batchStats") or j.get("batchStats"))
        BC.W(P["job"], job)
        print("run %d: %s %s %s%s" % (n, job["job"], job["state"], json.dumps(job["stats"]) if job["stats"] else "",
                                      "  (collected)" if (BC.J(P["run"]) or {}).get("complete") else ""))
    if not seen:
        print("no batch run was submitted yet")


def err_text(e):
    """A failed request's status object -> the text the instant call would have stored ("429 ..." for a quota failure)."""
    if not isinstance(e, dict):
        return str(e)[:400]
    code, msg = e.get("code"), str(e.get("message") or e.get("status") or "")
    if e.get("status") == "RESOURCE_EXHAUSTED" or "RESOURCE_EXHAUSTED" in msg:
        code = 429
    code = RPC_HTTP.get(code, code)
    return ("%s %s" % (code if code is not None else "error", msg))[:400]


def collect_file(date, n, results_path, job=None):
    """The results JSONL -> gemini-flash-batch-t1/line-run<n>.json. Each line of the file is {"key", "response"} (a
    GenerateContentResponse) or {"key", "error"/"status"}. Run again on the same file it changes nothing: a line
    already stored is skipped, so no answer is paid or logged twice."""
    P = paths(date, n)
    want = [i for i, _, _ in items(date)]
    clip = {i: c for i, c, _ in items(date)}
    rec = BC.J(P["run"]) or {"engine": ENGINE, "mode": "line", "run": n, "lines": {}, "cost_usd": 0.0, "seconds": 0.0, "model": MODEL,
                             "transport": "batch", "price_factor": PRICE_FACTOR}
    rec["lines"] = {i: o for i, o in rec["lines"].items() if not BV.unreached(o.get("error"))}
    rec["complete"] = False
    os.environ["ANEES_RUNS_DIR"] = os.path.join(BC.bench_dir(date), "runs", ENGINE)
    skipped, unknown = [], []
    with open(results_path, encoding="utf-8") as f:
        for raw in f:
            if not raw.strip():
                continue
            row = json.loads(raw)
            i = str(row.get("key") if row.get("key") is not None else (row.get("metadata") or {}).get("key"))
            if i not in clip:
                unknown.append(i)
                continue
            if i in rec["lines"]:
                continue
            if isinstance(row.get("response"), dict):
                out = BR.gemini_parse(MODEL, row["response"], as_json=True, price_factor=PRICE_FACTOR)
            else:
                out = {"text": "", "error": err_text(row.get("error") or row.get("status") or "no response")}
            if BV.unreached(out.get("error")):          # quota / no credit / rate limit: never the engine's miss
                skipped.append(i)
                continue
            usd = out.pop("usd", 0.0)
            if usd:
                BR.paid(date, ENGINE, "line", n, MODEL, usd, BR.wav_seconds(clip[i]), provider="google")
            out["usd"] = round(usd, 6)
            rec["lines"][i] = out
            rec["cost_usd"] = round(rec["cost_usd"] + usd, 6)
    if job:
        rec.update(job=job.get("job"), submitted=job.get("submitted"))
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
    P = paths(date, n)
    job = BC.J(P["job"])
    if not job or not job.get("job"):
        raise SystemExit("run %d was not submitted" % n)
    j = get_batch(job["job"])
    state = job_state(j)
    job.update(state=state, checked=time.strftime("%Y-%m-%dT%H:%M:%S"))
    BC.W(P["job"], job)
    if state != "JOB_STATE_SUCCEEDED":
        raise SystemExit("run %d: %s is %s%s" % (n, job["job"], state, (" - " + json.dumps(j.get("error"))[:300]) if j.get("error") else " - nothing to collect yet" if state not in DONE else ""))
    name = responses_file(j)
    if not name:
        raise SystemExit("run %d: the job succeeded but its answer names no results file: %s" % (n, json.dumps(j)[:400]))
    download_file(name, P["results"])
    return collect_file(date, n, P["results"], job)


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
    if len(argv) < 2 or argv[1] not in ("build", "submit", "status", "collect", "compare") or (argv[1] in ("build", "submit", "collect") and len(argv) < 3):
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
    else:
        sys.exit(compare(date))
