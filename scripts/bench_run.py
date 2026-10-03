# -*- coding: utf-8 -*-
"""Paid engines for the speech-engine benchmark (PR-18). Every engine gets the same frozen clips; outputs are kept raw.

    python scripts/bench_run.py 2026-10-02 <engine> [runs=3] [--mode line|whole] [--limit N]

Plain transcribers (audio only; no keyterms / vocabulary prompt - TR-03):
    eleven            ElevenLabs scribe_v2, production settings          line + whole
    openai-stt        gpt-transcribe (newest /v1/audio/transcriptions)   line
    openai-4o         gpt-4o-transcribe                                  line
    speechmatics      ar_en bilingual, enhanced                          line + whole
    deepgram-ar       nova-3, language=ar                                line + whole
    deepgram-multi    nova-3, language=multi                             line + whole
    cohere-api        cohere-transcribe-03-2026, language=ar             line
    gemini-transcribe gemini-3.5-transcribe, audio only                  line
Listeners (his clip + the frozen prompt; arm "ctx" = +-40 s around the line, arm "before" = only what came before):
    gemini-flash[-before]   gemini-3.8-flash
    gemini-pro[-before]     newest Gemini pro id on the key (3.1-pro-preview on 2026-10-03; there is no 3.8-pro)
    openai-audio[-before]   gpt-audio-1.5

Rules kept: a failed call is tried 3 times, then recorded as a miss with the error; every paid call writes a run line
(scripts/track.py); its dollars are kept in the run file and checked against the budget caps
(pipeline_ext.budget_ok, PR-10) before each call; one Gemini job at a time (a lock file).
"""
import base64, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

_lock = threading.Lock()
TRIES = 3

# USD list prices used for the cost column (estimates where the provider bills by token; tokens are kept in the run file).
PRICE = {
    "eleven": 0.22 / 3600, "openai-stt": 0.006 / 60, "openai-4o": 0.006 / 60, "speechmatics": 0.40 / 3600,
    "deepgram-ar": 0.0043 / 60, "deepgram-multi": 0.0052 / 60, "cohere-api": 0.0,               # per audio second
    "gemini-3.8-flash": (0.30, 1.00, 2.50), "gemini-3.1-pro-preview": (2.00, 2.00, 12.00), "gemini-3.5-transcribe": (0.30, 1.00, 2.50),
    "gpt-audio-1.5": (2.50, 32.00, 10.00),                                                      # per 1M: text in, audio in, out
}
SERVICE = {"eleven": "elevenlabs", "openai-stt": "openai", "openai-4o": "openai", "openai-audio": "openai",
           "gemini-flash": "gemini", "gemini-pro": "gemini", "gemini-transcribe": "gemini"}
LISTENERS = {"gemini-flash": "gemini-3.8-flash", "gemini-pro": "gemini-3.1-pro-preview", "openai-audio": "gpt-audio-1.5"}
def key(name):
    k = os.environ.get(name)
    if not k:
        import winreg
        k = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment"), name)[0]
    return k


def wav_seconds(path):
    return max(0.0, (os.path.getsize(path) - 44) / 32000.0)


# ------------------------------------------------------------------ money: bench ledger + run line + cap

_mine = {"usd": 0.0}


def spent(date, service=None):
    """{engine|mode|run: {usd, calls, model}} from the run files (each engine's process writes only its own files, so
    nothing is shared between the parallel jobs). service: only engines billed to that budget service."""
    d, out = BC.bench_dir(date), {}
    for e in sorted(os.listdir(d)):
        if not os.path.isdir(os.path.join(d, e)) or (service and SERVICE.get(e.replace("-before", "")) != service):
            continue
        for f in sorted(os.listdir(os.path.join(d, e))):
            m = re.match(r"(line|whole)-run(\d)\.json$", f)
            if not m:
                continue
            try:
                r = BC.J(os.path.join(d, e, f)) or {}
            except Exception:  # noqa: BLE001 - being rewritten right now by its own job
                continue
            calls = 1 if m.group(1) == "whole" else sum(1 for v in r.get("lines", {}).values() if not v.get("error") or v.get("usd"))
            out["%s|%s|%s" % (e, m.group(1), m.group(2))] = {"usd": round(r.get("cost_usd") or 0.0, 6), "calls": calls, "model": r.get("model")}
    return out


def cap_ok(date, engine, usd, _cache={}):
    """PR-10: stop before a service passes 90 % of its cap (budget.json so far + this benchmark's spend on the service)."""
    svc = SERVICE.get(engine.replace("-before", ""))
    if not svc:
        return True
    import pipeline_ext as PE
    now = time.time()
    if now - _cache.get("t", 0) > 60:                       # the other jobs' files, re-read once a minute
        _cache.update(t=now, others=sum(v["usd"] for k, v in spent(date, svc).items() if k.split("|")[0] != engine), base=_mine["usd"])
    mine_since = _mine["usd"] - _cache["base"]
    own = sum(v["usd"] for k, v in spent(date, svc).items() if k.split("|")[0] == engine) if "own" not in _cache else _cache["own"]
    _cache.setdefault("own", own)
    return PE.ledger().get(svc, 0.0) + _cache["others"] + _cache["own"] + _mine["usd"] + usd <= PE.CAPS[svc] * PE.STOP_AT


def paid(date, engine, mode, run, model, usd, seconds=None, provider=None):
    """One paid call: a run line (never text). Never raises: logging must not lose an answer already paid for."""
    with _lock:
        _mine["usd"] += usd
    try:
        import track
        os.environ.setdefault("ANEES_RUNS_DIR", os.path.join(BC.bench_dir(date), "runs", engine))
        track.log_run("bench." + engine, date, kind="eval", provider=provider or engine.split("-")[0], request_model=model, response_model=model,
                      cost_usd=round(usd, 6), params={"rule": "PR-18", "mode": mode, "run": run, "audio_s": seconds})
    except Exception:  # noqa: BLE001
        pass


TRANSPORT = ("SSLError", "ConnectionError", "ConnectTimeout", "ReadTimeout", "Timeout", "ChunkedEncodingError", "ProxyError")


def transport(err):
    """The request never reached the engine (this PC's connection dropped): not the engine's failure."""
    return bool(err) and str(err).startswith(TRANSPORT)


def tried(fn):
    """fn() -> dict. The ENGINE gets 3 tries, then {'text': '', 'error': ...} (a miss, never a 4th try). A request that
    never reached it (connection error on this PC) is re-sent, up to 8 times, and does not use up a try."""
    err, real, net = None, 0, 0
    while real < TRIES and net < 8:
        try:
            out = fn()
            if out is not None and not out.get("retry"):
                return out
            err = (out or {}).get("error") or "empty"
            real += 1
            time.sleep(4 * real)
        except Exception as e:  # noqa: BLE001
            err = "%s: %s" % (type(e).__name__, str(e)[:160])
            if transport(err):
                net += 1
                time.sleep(min(60, 8 * net))
            else:
                real += 1
                time.sleep(4 * real)
    return {"text": "", "error": err}


# ------------------------------------------------------------------ plain transcribers

def eleven(path, whole=False):
    import requests
    data = {"model_id": "scribe_v2", "diarize": "true", "num_speakers": "2", "timestamps_granularity": "word", "tag_audio_events": "true"}
    with open(path, "rb") as f:
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": key("ELEVENLABS_API_KEY")}, data=data,
                          files={"file": (os.path.basename(path), f, "audio/wav")}, timeout=1800)
    if r.status_code != 200:
        return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120])}
    j = r.json()
    out = {"text": j.get("text") or "", "language": j.get("language_code")}
    if whole:
        out["words"] = [{"text": w["text"], "start": w.get("start"), "end": w.get("end")} for w in j.get("words", []) if w.get("type") == "word"]
    return out


def openai_stt(model):
    def call(path, whole=False):
        import requests
        with open(path, "rb") as f:
            r = requests.post("https://api.openai.com/v1/audio/transcriptions", headers={"Authorization": "Bearer " + key("OPENAI_API_KEY")},
                              data={"model": model, "response_format": "json", "temperature": "0"},
                              files={"file": (os.path.basename(path), f, "audio/wav")}, timeout=300)
        if r.status_code != 200:
            return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120])}
        return {"text": r.json().get("text") or ""}
    return call


def speechmatics(path, whole=False):
    import requests
    H = {"Authorization": "Bearer " + key("SPEECHMATICS_API_KEY")}
    base = "https://asr.api.speechmatics.com/v2"
    cfg = {"type": "transcription", "transcription_config": {"language": "ar_en", "operating_point": "enhanced", "enable_entities": False}}
    with open(path, "rb") as f:
        r = requests.post(base + "/jobs", headers=H, data={"config": json.dumps(cfg)}, files={"data_file": (os.path.basename(path), f, "audio/wav")}, timeout=900)
    if r.status_code not in (200, 201):
        return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120])}
    job = r.json()["id"]
    t0 = time.time()
    while time.time() - t0 < (3600 if whole else 600):
        time.sleep(10 if whole else 3)
        g = requests.get("%s/jobs/%s" % (base, job), headers=H, timeout=60)
        if g.status_code != 200:
            continue
        st = g.json()["job"]["status"]
        if st == "done":
            break
        if st in ("rejected", "deleted", "expired"):
            return {"text": "", "error": "job " + st}
    else:
        return {"text": "", "error": "job timeout"}
    r = requests.get("%s/jobs/%s/transcript" % (base, job), headers=H, params={"format": "json-v2"}, timeout=120)
    if r.status_code != 200:
        return {"retry": True, "error": "transcript %d" % r.status_code}
    words = [{"text": it["alternatives"][0]["content"], "start": it["start_time"], "end": it["end_time"]} for it in r.json().get("results", []) if it.get("type") == "word"]
    out = {"text": " ".join(w["text"] for w in words)}
    if whole:
        out["words"] = words
    return out


def deepgram(lang):
    def call(path, whole=False):
        import requests
        with open(path, "rb") as f:
            r = requests.post("https://api.deepgram.com/v1/listen", params={"model": "nova-3", "language": lang, "punctuate": "true"},
                              headers={"Authorization": "Token " + key("DEEPGRAM_API_KEY"), "Content-Type": "audio/wav"}, data=f, timeout=1800)
        if r.status_code != 200:
            return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120])}
        alt = r.json()["results"]["channels"][0]["alternatives"][0]
        out = {"text": alt.get("transcript") or ""}
        if whole:
            out["words"] = [{"text": w.get("punctuated_word") or w["word"], "start": w["start"], "end": w["end"]} for w in alt.get("words", [])]
        return out
    return call


def cohere_api(path, whole=False):
    import requests
    with open(path, "rb") as f:
        r = requests.post("https://api.cohere.com/v2/audio/transcriptions", headers={"Authorization": "Bearer " + key("COHERE_API_KEY")},
                          data={"model": "cohere-transcribe-03-2026", "language": "ar"}, files={"file": (os.path.basename(path), f, "audio/wav")}, timeout=300)
    if r.status_code == 429:
        time.sleep(20)
        return {"retry": True, "error": "429"}
    if r.status_code != 200:
        return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120])}
    return {"text": r.json().get("text") or ""}


# ------------------------------------------------------------------ audio LLMs (listeners + the bare Gemini transcriber)

def _json(txt):
    try:
        return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception:  # noqa: BLE001
        return None


def gemini(model, path, prompt, as_json=True):
    import requests
    audio = base64.b64encode(open(path, "rb").read()).decode()
    cfg = {"temperature": 0}
    if as_json:
        cfg["responseMimeType"] = "application/json"
    parts = [{"inline_data": {"mime_type": "audio/wav", "data": audio}}] + ([{"text": prompt}] if prompt else [])
    body = {"contents": [{"parts": parts}], "generationConfig": cfg}
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model, params={"key": key("GEMINI_API_KEY")}, json=body, timeout=420)
    if r.status_code != 200:
        if r.status_code == 429:
            time.sleep(15)
        return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120].replace(key("GEMINI_API_KEY"), "***"))}
    j = r.json()
    u = j.get("usageMetadata") or {}
    aud = sum(d.get("tokenCount", 0) for d in u.get("promptTokensDetails") or [] if d.get("modality") == "AUDIO")
    tin, tout = u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    p = PRICE[model]
    usd = ((tin - aud) * p[0] + aud * p[1] + tout * p[2]) / 1e6
    try:
        part = j["candidates"][0]["content"]["parts"][0]
        txt = part["text"] if "text" in part else part["audioTranscription"]["text"]     # gemini-3.5-transcribe answers in audioTranscription
    except Exception:  # noqa: BLE001
        return {"text": "", "error": "no text (%s)" % ((j.get("candidates") or [{}])[0].get("finishReason")), "usd": usd, "tokens": [tin, aud, tout]}
    if not as_json:
        return {"text": txt.strip(), "usd": usd, "tokens": [tin, aud, tout]}
    d = _json(txt)
    if d is None:
        return {"text": "", "error": "bad json", "raw": txt[:300], "usd": usd, "tokens": [tin, aud, tout]}
    return {"text": d.get("arabic") or "", "alt": d.get("arabizi") or "", "raw": d, "usd": usd, "tokens": [tin, aud, tout]}


def openai_audio(model, path, prompt):
    import requests
    audio = base64.b64encode(open(path, "rb").read()).decode()
    body = {"model": model, "modalities": ["text"], "temperature": 0,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "input_audio", "input_audio": {"data": audio, "format": "wav"}}]}]}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": "Bearer " + key("OPENAI_API_KEY")}, json=body, timeout=300)
    if r.status_code != 200:
        if r.status_code == 429:
            time.sleep(15)
        return {"retry": True, "error": "%d %s" % (r.status_code, r.text[:120])}
    j = r.json()
    u = j.get("usage") or {}
    aud = (u.get("prompt_tokens_details") or {}).get("audio_tokens", 0)
    tin, tout = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
    p = PRICE[model]
    usd = ((tin - aud) * p[0] + aud * p[1] + tout * p[2]) / 1e6
    d = _json(j["choices"][0]["message"]["content"] or "")
    if d is None:
        return {"text": "", "error": "bad json", "raw": (j["choices"][0]["message"]["content"] or "")[:300], "usd": usd, "tokens": [tin, aud, tout]}
    return {"text": d.get("arabic") or "", "alt": d.get("arabizi") or "", "raw": d, "usd": usd, "tokens": [tin, aud, tout]}


# ------------------------------------------------------------------ the runner

PLAIN = {"eleven": (eleven, 6, "scribe_v2"), "openai-stt": (openai_stt("gpt-transcribe"), 6, "gpt-transcribe"),
         "openai-4o": (openai_stt("gpt-4o-transcribe"), 6, "gpt-4o-transcribe"), "speechmatics": (speechmatics, 8, "ar_en enhanced"),
         "deepgram-ar": (deepgram("ar"), 8, "nova-3 language=ar"), "deepgram-multi": (deepgram("multi"), 8, "nova-3 language=multi"),
         "cohere-api": (cohere_api, 2, "cohere-transcribe-03-2026 language=ar")}
WHOLE_OK = ("eleven", "speechmatics", "deepgram-ar", "deepgram-multi")


def run_engine(date, engine, runs=3, mode="line", limit=None):
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    prompts = BC.J(os.path.join(d, "prompts.json"))["arms"]
    base = engine.replace("-before", "")
    arm = "before" if engine.endswith("-before") else "ctx"
    gem_lock = None
    if SERVICE.get(base) == "gemini":
        gem_lock = os.path.join(d, ".gemini.lock")                 # never two Gemini jobs at once
        try:
            os.close(os.open(gem_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            raise SystemExit("another Gemini job is running (%s)" % gem_lock)
    try:
        for n in range(1, runs + 1):
            p = os.path.join(d, engine, "%s-run%d.json" % (mode, n))
            rec = BC.J(p) or {"engine": engine, "mode": mode, "run": n, "lines": {}, "cost_usd": 0.0, "seconds": 0.0}
            if rec.get("complete") and not any(transport(v.get("error")) for v in rec["lines"].values()):
                continue
            rec["complete"] = False
            t0 = time.time()
            if mode == "whole":
                fn, _, model = PLAIN[base]
                path = os.path.join(d, "clips", "medi-whole.wav")
                secs = wav_seconds(path)
                usd = PRICE[base] * secs
                if not cap_ok(date, engine, usd):
                    raise SystemExit("budget cap (PR-10) for " + engine)
                out = tried(lambda: fn(path, whole=True))
                if not out.get("error"):
                    paid(date, engine, mode, n, model, usd, secs)
                    rec["cost_usd"] = usd
                rec.update(model=model, words=out.get("words") or [], error=out.get("error"), language=out.get("language"))
                al = BC.align_words(rec["words"], truth["lines"], truth["offsets"]["Medi"])
                rec["lines"] = {str(i): {"text": t} for i, t in al.items()} if rec["words"] else {str(ln["i"]): {"text": "", "error": out.get("error") or "no words"} for ln in truth["lines"]}
            else:
                if base in PLAIN:
                    fn, threads, model = PLAIN[base]
                    items = [(str(ln["i"]), os.path.join(d, ln["clip"]), None) for ln in truth["lines"]] + \
                            [("A%d" % ln["i"], os.path.join(d, ln["clip"]), None) for ln in truth["amal_lines"]]
                elif base == "gemini-transcribe":
                    model, threads = "gemini-3.5-transcribe", 4
                    items = [(str(ln["i"]), os.path.join(d, ln["clip"]), None) for ln in truth["lines"]] + \
                            [("A%d" % ln["i"], os.path.join(d, ln["clip"]), None) for ln in truth["amal_lines"]]
                else:
                    model, threads = LISTENERS[base], (4 if base.startswith("gemini") else 6)
                    items = [(str(ln["i"]), os.path.join(d, ln["clip"]), prompts[arm][str(ln["i"])]) for ln in truth["lines"] if ln["listen"]]
                rec["model"] = model
                todo = [it for it in items if it[0] not in rec["lines"] or transport(rec["lines"][it[0]].get("error"))]   # unreached lines are re-sent
                if limit:
                    todo = todo[:limit]
                stop = []

                def one(it):
                    i, path, prompt = it
                    if stop:
                        return i, None
                    secs = wav_seconds(path)
                    est = PRICE[base] * secs if base in PLAIN else 0.03
                    if not cap_ok(date, engine, est):
                        stop.append(1)
                        return i, None
                    if base in PLAIN:
                        out = tried(lambda: fn(path))
                        usd = est if not out.get("error") else 0.0
                    elif base == "openai-audio":
                        out = tried(lambda: openai_audio(model, path, prompt))
                        usd = out.pop("usd", 0.0)
                    else:
                        out = tried(lambda: gemini(model, path, prompt, as_json=(base != "gemini-transcribe")))
                        usd = out.pop("usd", 0.0)
                    if usd or base == "cohere-api":
                        paid(date, engine, mode, n, model, usd, secs, provider={"gemini": "google", "openai": "openai"}.get(SERVICE.get(base)))
                    out["usd"] = round(usd, 6)
                    return i, out

                done = 0
                try:
                    with ThreadPoolExecutor(threads) as ex:
                        for i, out in ex.map(one, todo):
                            if out is None:
                                continue
                            rec["lines"][i] = out
                            rec["cost_usd"] = round(rec["cost_usd"] + out.get("usd", 0.0), 6)
                            done += 1
                            if done % 40 == 0:
                                rec["seconds"] += time.time() - t0
                                t0 = time.time()
                                BC.W(p, rec)
                                print(engine, mode, "run", n, len(rec["lines"]), "/", len(items), "$%.3f" % rec["cost_usd"], flush=True)
                finally:
                    BC.W(p, rec)
                if stop:
                    BC.W(p, rec)
                    raise SystemExit("budget cap (PR-10) reached for %s: stopped at %d lines" % (engine, len(rec["lines"])))
                rec["complete"] = len(rec["lines"]) >= len(items) and not any(transport(v.get("error")) for v in rec["lines"].values())
            rec["seconds"] += time.time() - t0
            if mode == "whole":
                rec["complete"] = True
            BC.W(p, rec)
            errs = sum(1 for v in rec["lines"].values() if v.get("error"))
            print("%s %s run %d: %d lines, %d errors, %.0f s, $%.3f" % (engine, mode, n, len(rec["lines"]), errs, rec["seconds"], rec["cost_usd"]), flush=True)
    finally:
        if gem_lock and os.path.exists(gem_lock):
            os.unlink(gem_lock)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv, opt = sys.argv[1:], {}
    for flag in ("--mode", "--limit"):
        if flag in argv:
            k = argv.index(flag)
            opt[flag] = argv[k + 1]
            del argv[k:k + 2]
    run_engine(argv[0], argv[1], int(argv[2]) if len(argv) > 2 else 3, opt.get("--mode", "line"), int(opt["--limit"]) if "--limit" in opt else None)
