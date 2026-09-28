# -*- coding: utf-8 -*-
"""Run log: one JSON line per AI, scorer or build call -> data/runs/YYYY-MM.jsonl (plan/AI-ENGINEERING-REVIEW-2026-09-27.md,
"Tracking design" 1). Append-only: a line is never edited; a correction is a new line.

    import track
    with track.run("full_audit.reader", lesson_date="2026-09-23", kind="inference", role="r1",
                   provider="anthropic", prompt_file="data/lesson-work/full-audit/READER-BRIEF.md",
                   inputs=[transcript_path], outputs=[reader_json]) as r:
        ...call the model...
        r.set(status="empty_output")                  # optional: anything the call learned
    # the line is written when the block ends (also on an exception, which is re-raised untouched)

The repo is PUBLIC: only hashes, paths, counts, model ids, tokens and dollars are logged - never prompt or transcript
text. Every string value passes safe(): Arabic letters or more than 200 characters become "sha256:<16 hex>".
Logging never raises and never blocks the caller (any failure here is swallowed). Field names follow the OpenTelemetry
GenAI conventions (gen_ai.provider.name, gen_ai.request.model, gen_ai.response.model, usage.input_tokens ...).

Env:
  ANEES_RUNS_DIR       write here instead of data/runs (tests). Under pytest nothing is written unless this is set.
  ANEES_TRIGGER        hourly | manual | overnight:<prompt file>   (default manual; hourly_lessons.py sets hourly)
  ANEES_PARENT_RUN_ID  parent_id for every run of this process
  ANEES_TRACE_ID       trace_id override (default "<lesson_date>|<trigger>")
  ANEES_CLAUDE_MODEL   pin `claude -p` to this model (unset = the CLI default, today's behaviour). The model the CLI
                       actually used is always logged from its JSON output (gen_ai.response.model).
"""
import datetime, hashlib, json, os, platform, re, subprocess, sys, threading, time, uuid
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCHEMA = 1
MAX_TEXT = 200
ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
KINDS = ("inference", "eval", "build", "ingest")
STATUSES = ("ok", "error", "timeout", "empty_output", "skipped_budget")
CLAUDE_MODEL = os.environ.get("ANEES_CLAUDE_MODEL") or None
_lock = threading.Lock()
_cache = {}


# ------------------------------------------------------------------ helpers (all failure-tolerant)

def sha256_text(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def safe(v):
    """A value that may go into the public log: Arabic or long text -> 'sha256:<16 hex>'. Recurses into lists/dicts."""
    if isinstance(v, str):
        if ARABIC.search(v) or len(v) > MAX_TEXT:
            return "sha256:" + sha256_text(v)[:16]
        return v
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe(x) for x in v]
    if v is None or isinstance(v, (bool, int, float)):
        return v
    return safe(str(v))


def rel(path):
    """Repo-relative path with forward slashes (absolute when outside the repo)."""
    try:
        p = os.path.abspath(str(path))
        r = os.path.relpath(p, REPO)
        return (p if r.startswith("..") else r).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def file_sha(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def count_rows(path):
    """Rows in an output file: JSON list length, the first list under a usual key, or JSONL line count."""
    try:
        p = str(path)
        if p.endswith(".jsonl"):
            with open(p, "rb") as f:
                return sum(1 for line in f if line.strip())
        if p.endswith(".json"):
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, list):
                return len(d)
            if isinstance(d, dict):
                for k in ("rows", "events", "patterns", "words", "items", "listen", "sentences", "lessons"):
                    if isinstance(d.get(k), list):
                        return len(d[k])
    except Exception:
        pass
    return None


def ref(path, rows=None, with_rows=False):
    """{path, sha256[, rows]} for input_refs / output_refs. A missing file has sha256 null."""
    out = {"path": rel(path), "sha256": file_sha(path)}
    if rows is not None:
        out["rows"] = rows
    elif with_rows and out["sha256"]:
        out["rows"] = count_rows(path)
    return out


def code_sha():
    """(HEAD sha, dirty) of the repo, cached per process; (None, None) without git."""
    if "code" not in _cache:
        try:
            h = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
            s = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, timeout=20)
            _cache["code"] = (h or None, bool(s.stdout.strip()) if s.returncode == 0 else None)
        except Exception:
            _cache["code"] = (None, None)
    return _cache["code"]


def tool_version(cmd):
    """`<cmd> --version`, first line, cached per process; None when it cannot run."""
    key = "ver:" + str(cmd)
    if key not in _cache:
        try:
            r = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=20)
            _cache[key] = ((r.stdout or "").strip().splitlines() or [None])[0] if r.returncode == 0 else None
        except Exception:
            _cache[key] = None
    return _cache[key]


def host():
    """Short stable id for the machine (a hash, not the hostname); ANEES_HOST overrides."""
    if os.environ.get("ANEES_HOST"):
        return os.environ["ANEES_HOST"]
    return "h-" + sha256_text(platform.node())[:8]


def trigger():
    return os.environ.get("ANEES_TRIGGER") or "manual"


def runs_dir():
    """Where lines go; None = do not write (under pytest without ANEES_RUNS_DIR, so tests never touch data/runs)."""
    if os.environ.get("ANEES_RUNS_DIR"):
        return os.environ["ANEES_RUNS_DIR"]
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return None
    return os.path.join(REPO, "data", "runs")


def append_line(directory, month, obj):
    """Append one JSON line to <directory>/<month>.jsonl. Never rewrites the file. Returns the path or None."""
    if not directory:
        return None
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, month + ".jsonl")
    line = json.dumps(obj, ensure_ascii=True, sort_keys=False, separators=(",", ":")) + "\n"
    with _lock:
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)
    return path


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


# ------------------------------------------------------------------ claude -p --output-format json

def claude_model_args():
    """['--model', <id>] when ANEES_CLAUDE_MODEL is set, else [] (today's behaviour: the CLI default)."""
    return ["--model", CLAUDE_MODEL] if CLAUDE_MODEL else []


def parse_claude_output(stdout):
    """Parse `claude -p --output-format json`. Returns {text, is_json, is_error, usage, cost_usd, response_model, models,
    num_turns}. text is exactly what the old text output would have been: the JSON's `result` when present, else the
    raw stdout (older CLI, text output, or a JSON without `result`)."""
    out = {"text": stdout or "", "is_json": False, "is_error": None, "usage": None, "cost_usd": None,
           "response_model": None, "models": None, "num_turns": None, "subtype": None}
    try:
        d = json.loads(stdout) if stdout and stdout.strip()[:1] in "[{" else None
    except Exception:
        d = None
    if isinstance(d, list):                     # --verbose json: an array of messages; the last "result" one is the summary
        d = next((x for x in reversed(d) if isinstance(x, dict) and x.get("type") == "result"), None)
    if not isinstance(d, dict):
        return out
    out["is_json"] = True
    if isinstance(d.get("result"), str):
        out["text"] = d["result"]
    out["is_error"] = d.get("is_error")
    out["subtype"] = d.get("subtype")
    out["num_turns"] = d.get("num_turns")
    if isinstance(d.get("total_cost_usd"), (int, float)):
        out["cost_usd"] = round(float(d["total_cost_usd"]), 6)
    u = d.get("usage") or {}
    if isinstance(u, dict) and u:
        out["usage"] = {k: u.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                              "cache_creation_input_tokens") if isinstance(u.get(k), (int, float))}
    mu = d.get("modelUsage") or {}
    if isinstance(mu, dict) and mu:
        models = {}
        for name, m in mu.items():
            if isinstance(m, dict):
                models[str(name)] = {"input_tokens": m.get("inputTokens"), "output_tokens": m.get("outputTokens"),
                                     "cache_read_input_tokens": m.get("cacheReadInputTokens"),
                                     "cache_creation_input_tokens": m.get("cacheCreationInputTokens"),
                                     "cost_usd": m.get("costUSD")}
        out["models"] = models
        # the model that did the work = the one that cost the most (helper models such as a small one may also appear)
        out["response_model"] = max(models, key=lambda k: (models[k].get("cost_usd") or 0, models[k].get("output_tokens") or 0)) if models else None
    elif d.get("model"):
        out["response_model"] = d.get("model")
    return out


# ------------------------------------------------------------------ the run record

class Run(dict):
    """One run line under construction. set(**fields) merges; outputs listed in `outputs` are hashed at the end."""

    def set(self, **kw):
        try:
            for k, v in kw.items():
                if k in ("usage", "metrics", "agreement", "params") and isinstance(v, dict):
                    if not isinstance(self.get(k), dict):
                        self[k] = {}
                    self[k].update(v)
                else:
                    self[k] = v
        except Exception:
            pass
        return self

    def claude(self, parsed):
        """Fill usage / cost / response model from parse_claude_output()."""
        try:
            self.set(**{"gen_ai.response.model": parsed.get("response_model")})
            if parsed.get("usage"):
                self.set(usage=parsed["usage"])
            if parsed.get("models"):
                self.set(usage={"models": parsed["models"]})
            if parsed.get("cost_usd") is not None:
                self.set(cost_usd=parsed["cost_usd"], cost_basis="estimate")
            if parsed.get("num_turns") is not None:
                self.set(params={"num_turns": parsed["num_turns"]})
            if not parsed.get("is_json"):
                self.set(params={"output": "not json"})
        except Exception:
            pass
        return self


def _new(step, lesson_date=None, kind="inference", provider=None, request_model=None, response_model=None, tool=None,
         prompt_file=None, prompt_sha=None, inputs=(), outputs=(), parent_id=None, pass_=None, role=None, params=None,
         **extra):
    trig = trigger()
    sha, dirty = code_sha()
    r = Run({
        "schema": SCHEMA, "run_id": uuid.uuid4().hex, "parent_id": parent_id or os.environ.get("ANEES_PARENT_RUN_ID"),
        "trace_id": os.environ.get("ANEES_TRACE_ID") or f"{lesson_date or '-'}|{trig}",
        "kind": kind if kind in KINDS else "inference", "step": step, "lesson_date": lesson_date,
        "pass": pass_, "role": role, "trigger": trig, "host": host(),
        "gen_ai.provider.name": provider, "gen_ai.request.model": request_model, "gen_ai.response.model": response_model,
        "tool_version": tool, "params": dict(params or {}),
        "prompt_file": rel(prompt_file) if prompt_file else None,
        "prompt_sha": prompt_sha or (file_sha(prompt_file) if prompt_file else None),
        "code_sha": sha, "code_dirty": dirty,
        "input_refs": [ref(p) for p in inputs or ()], "output_refs": [],
        "status": None, "error_type": None, "retries": 0,
        "started_at": now_utc().isoformat(timespec="seconds").replace("+00:00", "Z"), "duration_ms": None,
        "usage": {}, "cost_usd": None, "cost_basis": None, "metrics": {}, "agreement": {},
    })
    r["_outputs"] = list(outputs or ())
    r["_t0"] = time.monotonic()
    r.update(extra)
    return r


def _finish(r, exc=None):
    try:
        if r.get("duration_ms") is None:
            r["duration_ms"] = int((time.monotonic() - r.get("_t0", time.monotonic())) * 1000)
        if exc is not None:
            if not r.get("status") or r.get("status") == "ok":
                timeout = isinstance(exc, (subprocess.TimeoutExpired, TimeoutError))
                r["status"] = "timeout" if timeout else "error"
            r["error_type"] = r.get("error_type") or type(exc).__name__
        outs = r.pop("_outputs", [])
        r.pop("_t0", None)
        if outs and not r.get("output_refs"):
            r["output_refs"] = [ref(p, with_rows=True) for p in outs]
        if not r.get("status"):
            missing = [o for o in r.get("output_refs", []) if not o.get("sha256")]
            r["status"] = "empty_output" if missing else "ok"
        if r["status"] not in STATUSES:
            r["status"] = "error"
        rec = safe({k: v for k, v in r.items() if not str(k).startswith("_")})
        append_line(runs_dir(), rec["started_at"][:7], rec)
        return rec
    except Exception:
        return None


@contextmanager
def run(step, lesson_date=None, **fields):
    """Context manager: yields a Run; writes one line when the block ends. The caller's exception is re-raised as is."""
    try:
        r = _new(step, lesson_date, **fields)
    except Exception:
        r = Run()
    try:
        yield r
    except BaseException as e:
        if r:
            _finish(r, e)
        raise
    else:
        if r:
            _finish(r)


def log_run(step, lesson_date=None, **fields):
    """One-shot: write a finished run line now (status defaults to ok). Returns the written record or None."""
    try:
        status = fields.pop("status", None)
        dur = fields.pop("duration_ms", None)
        r = _new(step, lesson_date, **fields)
        if status:
            r["status"] = status
        if dur is not None:
            r["duration_ms"] = dur
        return _finish(r)
    except Exception:
        return None


def read(month=None, directory=None):
    """All lines of one month (or every month) as dicts; unreadable lines are skipped."""
    d = directory or runs_dir() or os.path.join(REPO, "data", "runs")
    names = [month + ".jsonl"] if month else sorted(n for n in os.listdir(d) if n.endswith(".jsonl")) if os.path.isdir(d) else []
    out = []
    for n in names:
        p = os.path.join(d, n)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
    return out
