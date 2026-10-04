# -*- coding: utf-8 -*-
"""Google Gemini Batch mode for ANY job: a folder, a job name, a list of (key, request). No benchmark knowledge here.

One job `<name>` is four files in one folder:
    <name>.jsonl          one line per request: {"key": "<key>", "request": <GenerateContentRequest>}   (build)
    <name>.build.json     what was built: model, number of requests, bytes, the JSONL's hash             (build)
    <name>.job.json       the job record: display_name, est_usd, file, job ("batches/..."), state        (submit / recover / status)
    <name>.results.jsonl  Google's answers, one line per request                                         (fetch)
A later part of the same job (the lines that got no answer) is the job `<name>.p2`, `<name>.p3`, ... (missing_part).

REST shapes from https://ai.google.dev/gemini-api/docs/batch-api (read 2026-10-04), file-based input:
    upload       POST {API}/upload/v1beta/files   (resumable: start, then upload+finalize)
    create       POST {API}/v1beta/models/<model>:batchGenerateContent
                 {"batch": {"display_name": ..., "input_config": {"file_name": "files/..."}}}   -> {"name": "batches/..."}
    status       GET  {API}/v1beta/batches/...
    list         GET  {API}/v1beta/batches?pageSize=..&pageToken=..
    results      GET  {API}/download/v1beta/<responses file>:download?alt=media
Every network call is one of the five small functions below (upload_file, create_batch, get_batch, download_file,
list_batches). submit / recover / status / fetch take `net`: any object with those five names (default: this module),
so a caller's tests replace them without touching this file.

Rules kept:
  * Creating a job is NOT idempotent and costs money, so a job that has a job id is never submitted twice.
  * The job file is written with a unique display_name and the estimate BEFORE the upload and before the create. A
    crash between Google creating the job and this PC saving its id therefore leaves a record that can find the job
    again: submit first asks Google for a job with that display name (recover) and only creates one when there is none.
  * The JSONL that is uploaded is the one that was built (its hash is checked first).
"""
import hashlib, json, os, sys, time

API = "https://generativelanguage.googleapis.com"
KEY_NAME = "GEMINI_API_KEY"
DONE = ("JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED")
# google.rpc codes a failed request may carry -> the HTTP status the instant call would have shown
RPC_HTTP = {8: 429, 14: 503, 4: 504, 13: 500, 3: 400, 7: 403, 5: 404, 9: 400}


# ------------------------------------------------------------------ small file helpers (same behaviour as bench_common's)

def _J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def _W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    for _ in range(40):                           # Windows: a reader may hold the file for a moment
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.25)
    os.replace(tmp, p)


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _net(net):
    return net if net is not None else sys.modules[__name__]


# ------------------------------------------------------------------ the files of one job

def paths(folder, name):
    """The four files of job `name` in `folder`: {"jsonl", "build", "job", "results"}."""
    return {"jsonl": os.path.join(folder, name + ".jsonl"), "build": os.path.join(folder, name + ".build.json"),
            "job": os.path.join(folder, name + ".job.json"), "results": os.path.join(folder, name + ".results.jsonl")}


def part_name(name, part):
    """Part 1 is the job itself; part 2, 3, ... (the lines that got no answer) are `<name>.p2`, `<name>.p3`, ..."""
    return name if part == 1 else "%s.p%d" % (name, part)


def parts(folder, name):
    """[(part, job name)] of the job and every later part that was built or submitted, in order. Part 1 is always listed."""
    out, k = [(1, name)], 2
    while any(os.path.exists(paths(folder, part_name(name, k))[f]) for f in ("build", "job")):
        out.append((k, part_name(name, k)))
        k += 1
    return out


# ------------------------------------------------------------------ build (no network)

def _info(P, name, model, keys, meta):
    info = dict(meta or {})
    info.update(name=name, model=model, requests=len(keys), bytes=os.path.getsize(P["jsonl"]), jsonl_sha256=_sha_file(P["jsonl"]),
                keys_sha256=hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest(), built=_now())
    _W(P["build"], info)
    return info


def build(folder, name, model, requests, meta=None):
    """Writes the JSONL (one {"key", "request"} line per (key, body) of `requests`, utf-8, "\\n") and build.json. No network.
    A job that already has a job file is never rebuilt: the file Google was sent must stay the file on this PC."""
    P = paths(folder, name)
    if (_J(P["job"]) or {}).get("job"):
        raise SystemExit("%s was already submitted (%s): not building over it" % (name, _J(P["job"])["job"]))
    os.makedirs(folder, exist_ok=True)
    keys = []
    with open(P["jsonl"], "w", encoding="utf-8", newline="\n") as f:
        for key, body in requests:
            keys.append(str(key))
            f.write(json.dumps({"key": str(key), "request": body}, ensure_ascii=False) + "\n")
    if len(set(keys)) != len(keys):
        raise SystemExit("%s: two requests carry the same key - an answer could not be mapped back" % name)
    return _info(P, name, model, keys, meta)


def missing_part(folder, name, missing_keys, part):
    """Builds the job `<name>.p<part>` (part = 2, 3, ...) from the ORIGINAL JSONL: only the lines whose key is in
    missing_keys, copied byte for byte (the same request, never rebuilt). Returns its build info; it is then
    submitted / fetched like any job. Refuses when a key is not in the original or the part was already submitted."""
    if part < 2:
        raise SystemExit("%s: a missing-lines part is numbered 2, 3, ... (got %r)" % (name, part))
    src, orig = paths(folder, name), _J(paths(folder, name)["build"])
    if not orig or not os.path.exists(src["jsonl"]):
        raise SystemExit("%s is not built: there is no original JSONL to take the missing lines from" % name)
    if _sha_file(src["jsonl"]) != orig["jsonl_sha256"]:
        raise SystemExit("%s: the JSONL changed since it was built - the missing lines would not be the requests that were sent" % name)
    pn = part_name(name, part)
    P = paths(folder, pn)
    if _J(P["job"]):
        raise SystemExit("%s was already submitted (%s): not building over it" % (pn, _J(P["job"]).get("job") or _J(P["job"]).get("display_name")))
    want, keys = {str(k) for k in missing_keys}, []
    if not want:
        raise SystemExit("%s: no missing line - nothing to build" % name)
    with open(src["jsonl"], "rb") as f, open(P["jsonl"], "wb") as out:
        for raw in f:
            if not raw.strip():
                continue
            k = str(json.loads(raw.decode("utf-8")).get("key"))
            if k in want:
                keys.append(k)
                out.write(raw.rstrip(b"\r\n") + b"\n")
    if set(keys) != want:
        os.remove(P["jsonl"])
        raise SystemExit("%s: %d missing keys are not in the original JSONL: %s" % (name, len(want - set(keys)), ", ".join(sorted(want - set(keys))[:12])))
    meta = {k: v for k, v in orig.items() if k not in ("name", "requests", "bytes", "jsonl_sha256", "keys_sha256", "built")}
    meta.update(part_of=name, part=part)
    return _info(P, pn, orig["model"], keys, meta)


# ------------------------------------------------------------------ the network (5 small functions; tests replace them)

def api_key():
    k = os.environ.get(KEY_NAME)
    if not k:
        import winreg
        k = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment"), KEY_NAME)[0]
    return k


def _headers(extra=None):
    h = {"x-goog-api-key": api_key()}
    h.update(extra or {})
    return h


def _fail(r, what):
    raise SystemExit("%s: %d %s" % (what, r.status_code, r.text[:400].replace(api_key(), "***")))


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
    """One job's status answer (GET {API}/v1beta/batches/...)."""
    import requests
    r = requests.get("%s/v1beta/%s" % (API, name), timeout=120, headers=_headers())
    if r.status_code != 200:
        _fail(r, "batch status")
    return r.json()


def download_file(name, out):
    """Downloads the results file `name` to the path `out`."""
    import requests
    with requests.get("%s/download/v1beta/%s:download" % (API, name), params={"alt": "media"}, timeout=3600, headers=_headers(), stream=True) as r:
        if r.status_code != 200:
            _fail(r, "results download")
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return out


def list_batches():
    """Every batch job of this API key (GET {API}/v1beta/batches, paged with pageToken) as a list of batch objects. Each
    has "name"; its display name is read by display_name(). The list key is "operations" in the long-running-operation
    shape and "batches" in the flat one: both are read."""
    import requests
    out, token = [], None
    for _ in range(200):                          # a page token that never ends must not loop for ever
        r = requests.get(API + "/v1beta/batches", timeout=120, headers=_headers(), params=dict({"pageSize": 100}, **({"pageToken": token} if token else {})))
        if r.status_code != 200:
            _fail(r, "batch list")
        j = r.json()
        out += j.get("operations") or j.get("batches") or []
        token = j.get("nextPageToken") or j.get("next_page_token")
        if not token:
            break
    return out


# ------------------------------------------------------------------ job state (Google's docs show two shapes)

def job_state(j):
    """The job's state from a status answer: the long-running-operation shape ({"metadata": {"state"}}) or the flat one."""
    st = (j.get("metadata") or {}).get("state") or j.get("state") or ("JOB_STATE_UNKNOWN" if not j.get("error") else "JOB_STATE_FAILED")
    return st.replace("BATCH_STATE_", "JOB_STATE_")     # the live API answers BATCH_STATE_* (first real run, 2026-10-04); the docs show JOB_STATE_*


def responses_file(j):
    """The results file's name: {"response": {"responsesFile"}} or {"dest": {"fileName"}} (both are in the docs)."""
    return ((j.get("response") or {}).get("responsesFile") or (j.get("dest") or {}).get("fileName")
            or (j.get("dest") or {}).get("file_name") or ((j.get("metadata") or {}).get("output") or {}).get("responsesFile"))


def display_name(j):
    """A batch object's display name: metadata.displayName, displayName or display_name (all three are tolerated)."""
    m = j.get("metadata") or {}
    return m.get("displayName") or m.get("display_name") or j.get("displayName") or j.get("display_name")


def _created(j):
    m = j.get("metadata") or {}
    return str(m.get("createTime") or m.get("create_time") or j.get("createTime") or j.get("create_time") or "")


def err_text(e):
    """A failed request's status object -> the text the instant call would have stored ("429 ..." for a quota failure)."""
    if not isinstance(e, dict):
        return str(e)[:400]
    code, msg = e.get("code"), str(e.get("message") or e.get("status") or "")
    if e.get("status") == "RESOURCE_EXHAUSTED" or "RESOURCE_EXHAUSTED" in msg:
        code = 429
    code = RPC_HTTP.get(code, code)
    return ("%s %s" % (code if code is not None else "error", msg))[:400]


# ------------------------------------------------------------------ submit / recover / status / fetch

def recover(folder, name, net=None):
    """Attaches a job that Google created but this PC never saved (a crash between create and save): finds the remote
    batch whose display name equals the job file's display_name (the newest when there are several) and stores its
    name and state. Returns the job record, or None when there is no job file / no display name / no such remote job.
    A record that already has its job id is returned as it is. Free: one list call, nothing is created."""
    P = paths(folder, name)
    job = _J(P["job"])
    if not job or not job.get("display_name"):
        return None
    if job.get("job"):
        return job
    hits = sorted((b for b in _net(net).list_batches() if display_name(b) == job["display_name"] and b.get("name")), key=_created, reverse=True)
    if not hits:
        return None
    job.update(job=hits[0]["name"], state=job_state(hits[0]), recovered=_now())
    job.setdefault("submitted", _created(hits[0]) or job["recovered"])
    _W(P["job"], job)
    return job


def submit(folder, name, est_usd, cap_check=None, net=None, recreate=False):
    """PAID: uploads the built JSONL and creates the batch job. Returns the job record.
    Refuses (SystemExit) when the job is not built, the JSONL changed since the build, the job already has a job id,
    or cap_check(est_usd) returns a message. The job file is written with its display_name and est_usd BEFORE the
    upload; a job file left with a display_name but no job id is first looked up at Google (recover) and only when no
    remote job carries that name is one uploaded + created (under the SAME display name, so a late one is still found)."""
    n, P = _net(net), paths(folder, name)
    info = _J(P["build"])
    if not info or not os.path.exists(P["jsonl"]):
        raise SystemExit("%s is not built" % name)
    job = _J(P["job"])
    if job and job.get("job"):
        raise SystemExit("%s was already submitted (%s): a batch job is never created twice. Delete %s only if that job is gone." % (name, job["job"], P["job"]))
    if job and not job.get("display_name"):
        raise SystemExit("%s has a job file with no job id and no display name (%s): it cannot be looked up. Delete it only if no job was created." % (name, P["job"]))
    if _sha_file(P["jsonl"]) != info["jsonl_sha256"]:
        raise SystemExit("%s: the JSONL changed since it was built - build it again" % name)
    if job:
        # A create whose answer was lost may still exist at Google. It is looked up by its display name. When the job
        # file says a create WAS attempted and no remote job is found, nothing is created again automatically (an empty
        # listing is not proof: a new job can lag the list) - the job stays unresolved and reserved until `recover`
        # finds it or a person passes recreate=True (Codex audit 2026-10-04: never a second purchase).
        rec = recover(folder, name, net)
        if rec:
            return rec
        if job.get("create_attempted") and not recreate:
            raise SystemExit("%s: a create was attempted (%s) and no job named %s is listed yet - unresolved. Run recover again later; "
                             "re-create only on purpose (recreate=True)." % (name, job["create_attempted"], job.get("display_name")))
    msg = cap_check(est_usd) if cap_check else None
    if msg:
        raise SystemExit(msg)
    rec = {k: v for k, v in info.items() if k not in ("bytes", "built", "keys_sha256")}
    rec.update(name=name, display_name=(job or {}).get("display_name") or "anees-%s-%s-%s" % (name, info["jsonl_sha256"][:8], time.strftime("%Y%m%d%H%M%S")),
               est_usd=est_usd, file=None, job=None, started=(job or {}).get("started") or _now())
    if (job or {}).get("create_attempted"):                      # an earlier attempt stays on the record (and reserved)
        rec["create_attempted"] = job["create_attempted"]
    _W(P["job"], rec)                                             # before any paid step: the name that finds the job again
    rec.update(file=n.upload_file(P["jsonl"], rec["display_name"]), uploaded=_now())
    _W(P["job"], rec)
    rec.update(create_attempted=_now())                           # from here on a lost answer may have left a job at Google
    _W(P["job"], rec)
    made = n.create_batch(info["model"], rec["file"], rec["display_name"])
    rec.update(job=made.get("name"), state=job_state(made), submitted=_now(), submitted_unix=round(time.time(), 1))
    _W(P["job"], rec)
    return rec


def _refresh(folder, name, net):
    P = paths(folder, name)
    job = _J(P["job"])
    if not job or not job.get("job"):
        raise SystemExit("%s was not submitted" % name)
    j = _net(net).get_batch(job["job"])
    job.update(state=job_state(j), checked=_now(), stats=(j.get("metadata") or {}).get("batchStats") or j.get("batchStats"))
    _W(P["job"], job)
    return job, j, P


def status(folder, name, net=None):
    """Asks Google for the job's state and stores it. Returns the job record (state, checked, stats refreshed)."""
    return _refresh(folder, name, net)[0]


def fetch(folder, name, net=None, label=None):
    """Downloads the answers to <name>.results.jsonl and returns that path. SystemExit unless the job is
    JOB_STATE_SUCCEEDED. Idempotent: the results file may be downloaded again. `label` names the job in a refusal."""
    job, j, P = _refresh(folder, name, net)
    label, state = label or name, job["state"]
    if state != "JOB_STATE_SUCCEEDED":
        raise SystemExit("%s: %s is %s%s" % (label, job["job"], state, (" - " + json.dumps(j.get("error"))[:300]) if j.get("error") else " - nothing to collect yet" if state not in DONE else ""))
    src = responses_file(j)
    if not src:
        raise SystemExit("%s: the job succeeded but its answer names no results file: %s" % (label, json.dumps(j)[:400]))
    _net(net).download_file(src, P["results"])
    return P["results"]


def rows(results_path):
    """The results JSONL, one (key, response, error_text) per line: (key, <GenerateContentResponse dict>, None) for an
    answer, (key, None, "<code> <message>") for a failed request. The key is row["key"] or row["metadata"]["key"]."""
    with open(results_path, encoding="utf-8") as f:
        for raw in f:
            if not raw.strip():
                continue
            row = json.loads(raw)
            key = str(row.get("key") if row.get("key") is not None else (row.get("metadata") or {}).get("key"))
            if isinstance(row.get("response"), dict):
                yield key, row["response"], None
            else:
                yield key, None, err_text(row.get("error") or row.get("status") or "no response")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if len(a) != 3 or a[0] not in ("status", "recover", "fetch"):
        raise SystemExit("python scripts/batch_jobs.py status|recover|fetch <folder> <job name>     (none of the three creates a job or costs money)")
    r = {"status": status, "recover": recover, "fetch": fetch}[a[0]](a[1], a[2])
    print(json.dumps(r, ensure_ascii=False, indent=1) if r else "no remote job carries this job file's display name")
