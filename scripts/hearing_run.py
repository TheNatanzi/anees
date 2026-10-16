# -*- coding: utf-8 -*-
"""The PAID run step of the hearing harness (plan/PIPELINE-TEST-PROTOCOL.md section 5): cells B, C and F on a lesson
with a frozen answer key. Medi 2026-10-14: "Yes. Start a session: save the 10-09 and 10-10 keys, build the harness run
step, fix the hidden-mistake score, run B, C and F on both lessons (about $7), then set up the Fable/Opus/Sonnet/Haiku
test." Hard stop: $9 for the whole test (data/lesson-work/harness/spend.json, Medi's number; code never raises it).

    python scripts/hearing_run.py plan <date> [--cell B,C,F]          # what would be paid, estimated; spends nothing
    python scripts/hearing_run.py run <date> --cell B,C,F [--instant]  # PAID (Batch by default; waits for Google)
    python scripts/hearing_run.py cached <date>                        # the free versions: A, E, Gemini run 1, ElevenLabs
    python scripts/hearing_run.py report <date> [<date> ...] [--json]  # every version scored on the key, paired

Cells (protocol section 5; the switches are hearing_harness.CELLS):
  B  Gemini proposes on the whole track: each speaker's own track cut by silence alone, pass 1 (no context) on every
     segment, pass 2 on his segments with pass 1's text around (scripts/rehear_gonly.py, the Gemini-only test); its
     words are laid over the voiced frames and put on the key's lines by ElevenLabs' line times (the only use of it).
  C  ElevenLabs raw + Deepgram nova-3 (his whole tracks, words with times put on the same lines) + Gemini's first line
     listen (cached rehear base-run1). Any two the same = that line. Where all three differ on a line Gemini listened to,
     a blind Gemini judge hears his clip and picks among version X / Y / Z.
  F  B's whole-lesson text vs ElevenLabs raw. Where they differ on a line Gemini listened to: BOTH listen again to his
     clip (Gemini with its own text around + gives reasons; ElevenLabs on the clip alone, which writes no reasons), then a
     blind Gemini judge hears the clip with both second-listen versions (+ Gemini's reasons) and picks.
  D  NOT RUN: needs forced alignment of whole-track text to line times, which is not built (protocol section 4).

Blind always: the judge sees "version X / Y (/ Z)", seeded coin-swapped order, every engine name scrubbed
(hearing_harness.judge_prompt / judge_prompt_n). The judge's context is the tutor's lines around the clip (her speech,
never a version of his line).

Every engine output is cached by (audio hash, engine, model, prompt hash) in data/lesson-work/harness/<date>/cache.json
(text only; kept): a rerun pays nothing for an answer it has. Every paid answer writes a run line in data/runs (track.py)
and its dollars into data/lesson-work/harness/spend.json; the allowance is checked BEFORE every paid step (an estimate is
a reservation, held 30 % high, until the real dollars are in). Gemini goes through Google's Batch mode (half price;
scripts/batch_jobs.py; job files in harness/<date>/jobs/, git-ignored). Production's own allowance
(data/lesson-work/rehear/spend.json) is neither used nor touched. ANEES_REHEAR_AUTO=off is set for the run.
"""
import argparse, collections, hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import hearing_harness as HH  # noqa: E402

HDIR = os.path.join(REPO, "data", "lesson-work", "harness")
MODEL = "gemini-3.8-flash"                      # bench_vars.MODEL, the production listener
BATCH_FACTOR = 0.5                              # Google's Batch mode
RESERVE = 1.3                                   # Batch dollars came in 10-23 % over rehear_job.estimate on 10-09..10-12
CTX_S, AMAL_CTX_S = 40.0, 30.0
RUN_CELLS = ("B", "C", "F")
TEMP = 1                                        # the production listener's temperature, pinned for every Gemini call here
POLL_S, MAX_WAIT_S = 60, 8 * 3600


class BudgetStop(SystemExit):
    pass


# ------------------------------------------------------------------ money (its own allowance, Medi's number)

def spend_path(root=None):
    return os.path.join(root or HDIR, "spend.json")


def spend_doc(root=None):
    return BC.J(spend_path(root)) or {}


def spent(root=None):
    """Dollars used or owed: a paid item's real dollars; an item sent and not yet collected counts at its estimate."""
    tot = 0.0
    for it in (spend_doc(root).get("items") or {}).values():
        tot += it["usd"] if it.get("state") == "paid" else max(it.get("est_usd") or 0.0, it.get("usd") or 0.0)
    return round(tot, 4)


def limit(root=None):
    v = spend_doc(root).get("limit_usd")
    return None if v is None else float(v)


def check_budget(est, what, root=None):
    """Raises BudgetStop when this step would pass Medi's limit (or when he set none)."""
    lim = limit(root)
    if lim is None:
        raise BudgetStop("no harness limit in %s - stopped, nothing sent" % spend_path(root))
    s = spent(root)
    if s + est > lim:
        raise BudgetStop("harness limit (Medi's, %s): $%.2f used or owed + $%.2f for %s > $%.2f - stopped, nothing sent" % (
            os.path.relpath(spend_path(root), REPO), s, est, what, lim))


class _Lock:
    """One writer of the spend file at a time (both lessons run in parallel processes)."""

    def __init__(self, root=None):
        self.p = spend_path(root) + ".lock"

    def __enter__(self):
        t0 = time.time()
        while True:
            try:
                os.close(os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                if time.time() - os.path.getmtime(self.p) > 120:      # left by a killed process
                    os.unlink(self.p)
                elif time.time() - t0 > 300:
                    raise SystemExit("another run holds %s" % self.p)
                else:
                    time.sleep(0.2)

    def __exit__(self, *a):
        if os.path.exists(self.p):
            os.unlink(self.p)


def reserve(item, est, root=None, **fields):
    """Check the allowance and book the estimate as owed, as one step under the lock (no two runs pass on the same room).
    An item already in the file (an earlier attempt of the same step: its money is kept) gets a new name. Returns it."""
    with _Lock(root):
        check_budget(est, item, root)
        items = spend_doc(root).get("items") or {}
        name, n = item, 2
        while name in items:
            name, n = "%s#%d" % (item, n), n + 1
        _record(name, root, state="owed", est_usd=est, usd=0.0, **fields)
        return name


def record(item, root=None, **fields):
    with _Lock(root):
        _record(item, root, **fields)


def _record(item, root=None, **fields):
    """One spend item (a Batch job or an instant call group): {date, what, state owed|paid, est_usd, usd, when}."""
    doc = spend_doc(root)
    doc.setdefault("items", {})
    doc["items"].setdefault(item, {}).update(fields, when=time.strftime("%Y-%m-%dT%H:%M:%S"))
    doc["spent_usd"] = 0.0
    BC.W(spend_path(root), doc)
    doc["spent_usd"] = spent(root)
    BC.W(spend_path(root), doc)


def log_paid(step, date, provider, model, usd, params):
    """One paid answer = one run line in data/runs (never text). Never raises: an answer already paid is kept."""
    try:
        import track
        track.log_run("harness." + step, date, kind="eval", provider=provider, request_model=model, response_model=model,
                      cost_usd=round(usd, 6), params=dict(params, rule="PR-23"))
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ the cache

class Cache:
    """{cache_key: {"engine", "model", "audio", "prompt", "out"}} for one lesson, kept in harness/<date>/cache.json."""

    def __init__(self, path):
        self.path = path
        self.d = BC.J(path) or {}

    @staticmethod
    def key(audio_sha, engine, model, prompt=""):
        return HH.cache_key(audio_sha, engine, model, HH.prompt_hash(prompt) if prompt else "")

    def get(self, k):
        e = self.d.get(k)
        return e["out"] if e else None

    def put(self, k, out, engine, model, audio, prompt=""):
        self.d[k] = {"engine": engine, "model": model, "audio": audio, "prompt": HH.prompt_hash(prompt) if prompt else "", "out": out}

    def save(self):
        BC.W(self.path, self.d)


# ------------------------------------------------------------------ the lesson: key lines, windows, clips

class Lesson:
    def __init__(self, date, data_root=None, root=None):
        self.date = date
        self.data_root = data_root or os.path.join(REPO, "data")
        self.root = root or HDIR
        self.dir = os.path.join(self.root, date)
        self.key = HH.load_key(date, self.data_root)
        rl = BC.J(os.path.join(self.data_root, "lesson-work", "rehear", date, "lines.json")) or {}
        self.rlines = {"%.2f" % float(ln["t"]): ln for ln in rl.get("lines") or []}
        self.amal = rl.get("amal_all") or []
        self.cache = Cache(os.path.join(self.dir, "cache.json"))
        ids = self.key["ids"]
        self.windows = {}
        for n, i in enumerate(ids):
            ln = self.rlines.get(i)
            if ln:
                self.windows[i] = (float(ln["t"]), float(ln.get("end") or ln["t"]), tuple(ln.get("window") or (ln["t"], ln.get("end") or ln["t"])))
            else:
                nxt = float(ids[n + 1]) if n + 1 < len(ids) else float(i) + 3.0
                self.windows[i] = (float(i), min(float(i) + 3.0, nxt), (float(i), min(float(i) + 3.0, nxt)))
        self.listen = [i for i in ids if (self.rlines.get(i) or {}).get("listen")]

    def key_lines(self):
        """The key's lines with ElevenLabs' times, for bench_common.align_words."""
        return [{"i": i, "t": w[0], "end": max(w[0], w[1])} for i, w in self.windows.items()]

    def clip(self, i):
        """His microphone for key line i (the rehear window: guarded edge re-cut), cut bit-exact -> (path, sha256)."""
        import rehear_audio as RA
        out = os.path.join(self.dir, "clips", "%s.wav" % i.replace(".", "_"))
        if not os.path.exists(out):
            a, b = self.windows[i][2]
            RA.clip(self.date, "Medi", float(a), float(b), out)
        return out, BC.sha_file(out)

    def amal_context(self, i, span=AMAL_CTX_S):
        """The tutor's lines around line i (ElevenLabs text of HER track): what the judge may read for meaning."""
        t = float(i)
        rows = ["%+.1f s Amal: %s" % (float(a["t"]) - t, a.get("text") or a.get("engine") or "") for a in self.amal
                if abs(float(a["t"]) - t) <= span and (a.get("text") or a.get("engine"))]
        return "\n".join(rows)


# ------------------------------------------------------------------ Gemini: Batch or instant, through the cache

def _gemini_out(resp, factor):
    import bench_run as BR
    return BR.gemini_parse(MODEL, resp, as_json=True, price_factor=factor)


def estimate(reqs, out_tokens=350):
    """Dollars of Gemini requests [(clip, prompt)] at the Batch price, reserved 30 % high (rehear_job.estimate's rule)."""
    import bench_run as BR
    p = BR.PRICE[MODEL]
    usd = sum((len(pr) / 2.5 * p[0] + BR.wav_seconds(c) * 32 * p[1] + out_tokens * p[2]) / 1e6 for c, pr in reqs)
    return round(usd * BATCH_FACTOR * RESERVE, 4)


class Gemini:
    """ask(stage, [(cache_key, clip, prompt, cfg)]) -> {cache_key: out}. Answers already cached are not sent again."""

    def __init__(self, L, instant=False, net=None, log=print, out_tokens=350):
        self.L, self.instant, self.log = L, instant, log
        self.net = net                                   # tests: {"batch": fn(stage, reqs) -> {key: resp}} or {"instant": fn}
        self.out_tokens = out_tokens

    def ask(self, stage, reqs, out_tokens=None):
        C = self.L.cache
        todo = [r for r in reqs if C.get(r[0]) is None]
        if todo:
            est = estimate([(c, p) for _, c, p, _ in todo], out_tokens or self.out_tokens) * (2 if self.instant else 1)
            item = "%s/%s-%s" % (self.L.date, stage, hashlib.sha256("\n".join(k for k, *_ in todo).encode()).hexdigest()[:8])
            item = reserve(item, est, self.L.root, date=self.L.date, what="gemini " + stage, requests=len(todo))
            self.log("%s %s: %d Gemini requests (%s), about $%.2f" % (self.L.date, stage, len(todo), "instant" if self.instant else "Batch", est))
            factor = 1.0 if self.instant else BATCH_FACTOR
            answers = (self._instant if self.instant else self._batch)(stage, item, todo)
            usd = 0.0
            for k, clip, prompt, _ in todo:
                resp = answers.get(k)
                if resp is None:
                    continue
                out = resp if "text" in resp and "candidates" not in resp else _gemini_out(resp, factor)
                u = out.pop("usd", 0.0) or 0.0
                usd += u
                log_paid(stage, self.L.date, "google", MODEL, u, {"key": k, "transport": "instant" if self.instant else "batch"})
                if out.get("error") and not out.get("text") and not out.get("raw"):
                    continue                                   # an error is never cached: missing, sent again next run
                C.put(k, out, "gemini", MODEL, os.path.basename(clip), prompt)
            C.save()
            missing = [k for k, *_ in todo if C.get(k) is None]
            record(item, self.L.root, state="paid" if not missing else "owed", usd=round(usd, 6), missing=len(missing))
            self.log("%s %s: $%.3f, %d answers, %d missing" % (self.L.date, stage, usd, len(todo) - len(missing), len(missing)))
        return {k: C.get(k) for k, *_ in reqs}

    def _instant(self, stage, item, todo):
        import bench_run as BR
        fn = (self.net or {}).get("instant") or (lambda c, p, cfg: BR.tried(lambda: BR.gemini(MODEL, c, p, as_json=True, temp=TEMP, cfg_extra=cfg)))
        out = {}
        for k, c, p, cfg in todo:
            o = fn(c, p, cfg)
            if o is not None:
                out[k] = o
        return out

    def _batch(self, stage, item, todo):
        if self.net and self.net.get("batch"):
            return self.net["batch"](stage, todo)
        import batch_jobs as BJ
        import bench_run as BR
        folder = os.path.join(self.L.dir, "jobs")
        name = item.split("/", 1)[1].split("#")[0]
        P = BJ.paths(folder, name)
        if not (BC.J(P["job"]) or {}).get("job"):
            BJ.build(folder, name, MODEL, ((k, BR.gemini_body(MODEL, c, p, as_json=True, temp=TEMP, cfg_extra=cfg)) for k, c, p, cfg in todo),
                     meta={"keys": [k for k, *_ in todo], "stage": stage})
            est = ((spend_doc(self.L.root).get("items") or {}).get(item) or {}).get("est_usd") or estimate([(c, p) for _, c, p, _ in todo])
            BJ.submit(folder, name, est, cap_check=lambda e: None)      # the allowance was checked (and reserved) by ask()
        t0 = time.time()
        while True:
            st = BJ.status(folder, name).get("state")
            if st in BJ.DONE or time.time() - t0 > MAX_WAIT_S:
                break
            time.sleep(POLL_S)
        if st != "JOB_STATE_SUCCEEDED":
            self.log("%s %s: Batch job ended %s - nothing collected" % (self.L.date, stage, st))
            return {}
        out = {}
        for key, resp, err in BJ.rows(BJ.fetch(folder, name)):
            if key in out:
                continue
            if resp is not None and isinstance(resp.get("error"), dict) and not resp.get("candidates"):
                resp, err = None, BJ.err_text(resp["error"])
            out[key] = resp if resp is not None else {"text": "", "error": err, "usd": 0.0}
        return out


# ------------------------------------------------------------------ cell B: Gemini on the whole track

def whole_track(L, G, log=print):
    """(his text per key line, her text per amal line i) from Gemini's whole-track pass 1 + pass 2 (one run)."""
    import rehear_audio as RA
    import rehear_gonly as RG
    segs, meta = RA.lesson_segments(L.date)
    if not segs:
        raise SystemExit("%s: no own tracks to cut by silence" % L.date)
    srcs = RA.sources(L.date)
    reqs, by = [], {}
    for g in segs:
        out = os.path.join(L.dir, "gonly", "clips", g["id"] + ".wav")
        if not os.path.exists(out):
            RA.cut(srcs[g["who"]][g["k"]]["file"], g["track_a"], g["track_b"], out)
        prompt = RG.P1_MEDI if g["who"] == "Medi" else RG.P1_AMAL
        k = Cache.key(BC.sha_file(out), "gemini-p1", MODEL, prompt + json.dumps(RG.P1_CFG, sort_keys=True))
        reqs.append((k, out, prompt, RG.P1_CFG))
        by[g["id"]] = k
    A1 = G.ask("p1", reqs, out_tokens=150)
    p1 = {gid: A1.get(k) for gid, k in by.items() if A1.get(k) is not None}
    P2 = RG.p2_prompts(L.date, segs, p1)
    reqs2, by2 = [], {}
    for gid, prompt in sorted(P2.items()):
        clip = os.path.join(L.dir, "gonly", "clips", gid + ".wav")
        k = Cache.key(BC.sha_file(clip), "gemini-p2", MODEL, prompt)
        reqs2.append((k, clip, prompt, None))
        by2[gid] = k
    A2 = G.ask("p2", reqs2)
    p2 = {gid: A2.get(k) for gid, k in by2.items() if A2.get(k) is not None}
    W, Z = RG.words_on_track(L.date, segs, p1, p2, "Medi")
    his = BC.align_words(W, L.key_lines(), 0.0)
    WA, _ = RG.words_on_track(L.date, segs, p1, p2, "Amal")
    amal_lines = [{"i": n, "t": float(a["t"]), "end": float(a.get("end") or a["t"])} for n, a in enumerate(L.amal)]
    hers = BC.align_words(WA, amal_lines, 0.0) if amal_lines else {}
    BC.W(os.path.join(L.dir, "gonly", "segments.json"), {"date": L.date, "rule": RA.SEG, "tracks": meta, "segments": segs,
                                                          "p2_sent": len(P2), "p2_chat_offset_s": getattr(RG.p2_prompts, "chat_offset", None)})
    log("%s whole track: %d segments, %d pass-2" % (L.date, len(segs), len(P2)))
    return his, hers


# ------------------------------------------------------------------ the blind judge

JUDGE_CFG = None


def judge(L, G, stage, items, log=print):
    """items = [(line id, [(text, reasons)] 2-3 versions)] -> {line id: (index of the picked version or None, heard)}.
    The judge hears his clip; it is told nothing about who wrote which version."""
    reqs, meta = [], {}
    for i, versions in items:
        clip, sha = L.clip(i)
        ctx = L.amal_context(i)
        if len(versions) == 2:
            jp = HH.judge_prompt(versions[0][0], versions[1][0], seed=L.date, item=i, context=ctx,
                                 reasons_a=versions[0][1], reasons_b=versions[1][1])
            key = {"X": 1 if jp["swapped"] else 0, "Y": 0 if jp["swapped"] else 1}
        else:
            jp = HH.judge_prompt_n(versions, seed=L.date, item=i, context=ctx)
            key = jp["key"]
        k = Cache.key(sha, "gemini-judge", MODEL, jp["prompt"])
        reqs.append((k, clip, jp["prompt"], JUDGE_CFG))
        meta[i] = (k, key)
    A = G.ask(stage, reqs, out_tokens=300)
    out = {}
    for i, (k, key) in meta.items():
        o = A.get(k) or {}
        raw = o.get("raw") if isinstance(o.get("raw"), dict) else {}
        m = re.match(r"\s*(?:VERSION\s+)?([XYZ])\b", str(raw.get("pick") or "").upper())
        pick = m.group(1) if m else ""
        out[i] = (key.get(pick), str(raw.get("heard") or "").strip(), str(raw.get("why") or "")[:200])
    return out


def _same(a, b):
    return BC.tokens(a or "") == BC.tokens(b or "")


# ------------------------------------------------------------------ the cells

def cell_B(L, G, log=print):
    his, hers = whole_track(L, G, log)
    lines = {i: his.get(i, "") for i in L.key["ids"]}
    return lines, {"how": "Gemini whole track (pass 1 + pass 2), words on ElevenLabs' line times"}, hers


def deepgram_lines(L, log=print, net=None):
    """Deepgram nova-3 (language ar, bench_run's settings) on each of his whole tracks -> text per key line."""
    import bench_run as BR
    import rehear_audio as RA
    srcs = RA.sources(L.date).get("Medi") or []
    words = []
    for k, s in enumerate(srcs):
        wav = RA.whole_wav(L.date, "Medi", k, s)
        sha = BC.sha_file(wav)
        ck = Cache.key(sha, "deepgram", "nova-3-ar")
        out = L.cache.get(ck)
        if out is None:
            secs = BR.wav_seconds(wav)
            usd = BR.PRICE["deepgram-ar"] * secs
            item = "%s/deepgram-%d" % (L.date, k)
            item = reserve(item, round(usd, 4), L.root, date=L.date, what="deepgram nova-3 his track %d" % k)
            call = (net or {}).get("deepgram") or (lambda p: BR.tried(lambda: BR.deepgram("ar")(p, whole=True)))
            out = call(wav)
            if out.get("error") and not out.get("words"):
                raise SystemExit("%s: Deepgram failed on track %d: %s" % (L.date, k, out["error"]))
            L.cache.put(ck, out, "deepgram", "nova-3-ar", os.path.basename(wav))
            L.cache.save()
            log_paid("deepgram", L.date, "deepgram", "nova-3", usd, {"track": k, "audio_s": round(secs, 1)})
            record(item, L.root, state="paid", usd=round(usd, 6))
            log("%s Deepgram track %d: %.0f s, $%.3f" % (L.date, k, secs, usd))
        words += [dict(w, start=float(w["start"]) + s["start"], end=float(w["end"]) + s["start"]) for w in out.get("words") or []]
    return BC.align_words(words, L.key_lines(), 0.0)


def cell_C(L, G, log=print, net=None):
    E = {i: L.key["engine"].get(i, "") for i in L.key["ids"]}
    D = deepgram_lines(L, log, net)
    g1, _ = HH.load_version(os.path.join(L.data_root, "lesson-work", "rehear", L.date, "base-run1.json"), L.key, "engine")
    lines, todo, n_vote = {}, [], collections.Counter()
    for i in L.key["ids"]:
        g, e, d = g1.get(i, ""), E[i], D.get(i, "")
        if i not in L.listen or _same(g, e) or _same(g, d):
            lines[i] = g
            n_vote["gemini with one other" if i in L.listen else "not a listen line (ElevenLabs)"] += 1
        elif _same(e, d):
            lines[i] = e
            n_vote["ElevenLabs + Deepgram"] += 1
        else:
            todo.append(i)
    J = judge(L, G, "judge-C", [(i, [(g1.get(i, ""), ""), (E[i], ""), (D.get(i, ""), "")]) for i in todo], log)
    for i in todo:
        pick, heard, _ = J.get(i, (None, "", ""))
        vs = [g1.get(i, ""), E[i], D.get(i, "")]
        lines[i] = vs[pick] if pick is not None else (heard or g1.get(i, ""))
        n_vote["judge: " + (["Gemini", "ElevenLabs", "Deepgram"][pick] if pick is not None else "neither")] += 1
    BC.W(os.path.join(L.dir, "versions", "deepgram.json"), {"lines": D, "how": "Deepgram nova-3 ar, his whole tracks, on ElevenLabs' line times"})
    return lines, {"how": "vote of ElevenLabs raw, Deepgram nova-3, Gemini line listen 1; blind Gemini judge where all three differ",
                   "votes": dict(n_vote), "judged": len(todo)}


def cell_F(L, G, log=print, net=None, whole=None):
    import bench_run as BR
    import context_transcribe as CT
    his, hers = whole if whole is not None else whole_track(L, G, log)
    E = {i: L.key["engine"].get(i, "") for i in L.key["ids"]}
    disputed = [i for i in L.listen if not _same(his.get(i, ""), E[i])]
    # 1. Gemini listens again: its own whole-track text around (both speakers), the production listener prompt (reasons)
    reqs, gk = [], {}
    for i in disputed:
        clip, sha = L.clip(i)
        t0 = float(i)
        ctx = [(float(j) - t0, "Medi", his.get(j, "")) for j in L.key["ids"] if j != i and abs(float(j) - t0) <= CTX_S and his.get(j)]
        ctx += [(float(a["t"]) - t0, "Amal", hers.get(n, "")) for n, a in enumerate(L.amal) if abs(float(a["t"]) - t0) <= CTX_S and hers.get(n)]
        prompt = CT.PROMPT.format(context="\n".join("%+.1f s %s: %s" % x for x in sorted(ctx)), chat="(none)", target=his.get(i, "") or "(nothing)")
        k = Cache.key(sha, "gemini-relisten", MODEL, prompt)
        reqs.append((k, clip, prompt, None))
        gk[i] = k
    A = G.ask("relisten-F", reqs)
    # 2. ElevenLabs listens again: the clip alone (a plain transcriber, no reasons)
    el = {}
    eleven = (net or {}).get("eleven") or (lambda p: BR.tried(lambda: BR.eleven(p)))
    todo = []
    for i in disputed:
        clip, sha = L.clip(i)
        ck = Cache.key(sha, "elevenlabs-line", "scribe_v2")
        if L.cache.get(ck) is None:
            todo.append((i, clip, ck))
        el[i] = ck
    if todo:
        secs = sum(BR.wav_seconds(c) for _, c, _ in todo)
        usd_est = BR.PRICE["eleven"] * secs
        item = "%s/eleven-relisten-F" % L.date
        item = reserve(item, round(usd_est, 4), L.root, date=L.date, what="ElevenLabs second listen, F", requests=len(todo))
        usd, failed = 0.0, collections.Counter()
        try:
            for n, (i, clip, ck) in enumerate(todo):
                o = eleven(clip)
                if o.get("error") and not o.get("text"):
                    failed[str(o["error"])[:60]] += 1           # never cached: no answer, sent again next run
                    continue
                u = BR.PRICE["eleven"] * BR.wav_seconds(clip)
                usd += u
                L.cache.put(ck, {"text": o.get("text") or ""}, "elevenlabs", "scribe_v2", os.path.basename(clip))
                log_paid("eleven-relisten", L.date, "elevenlabs", "scribe_v2", u, {"line": i})
                if n % 25 == 24:
                    L.cache.save()
        finally:
            L.cache.save()
            record(item, L.root, state="paid", usd=round(usd, 6), missing=sum(failed.values()))
        log("%s ElevenLabs second listen: %d clips, $%.3f, %d failed %s" % (L.date, len(todo), usd, sum(failed.values()), dict(failed)))
    # 3. the blind judge, both second-listen versions (+ Gemini's reasons)
    items, no_el = [], 0
    for i in disputed:
        g = A.get(gk[i]) or {}
        raw = g.get("raw") if isinstance(g.get("raw"), dict) else {}
        reasons = "; ".join(x for x in [str(raw.get("why") or "")] + ["%s -> %s" % (c.get("engine"), c.get("said")) for c in raw.get("changes") or [] if isinstance(c, dict)] if x)
        gtext = g.get("text") or his.get(i, "")
        eo = L.cache.get(el[i])
        if not eo or eo.get("error"):
            no_el += 1                                # no second listen (an engine error): its first version stands
        etext = (eo or {}).get("text") or E[i]
        items.append((i, [(gtext, reasons), (etext, "")]))
    J = judge(L, G, "judge-F", items, log)
    lines, n = {}, collections.Counter()
    for i in L.key["ids"]:
        lines[i] = his.get(i, "") if i in L.listen or his.get(i) else E[i]
    for i, versions in items:
        pick, heard, _ = J.get(i, (None, "", ""))
        lines[i] = versions[pick][0] if pick is not None else (heard or versions[0][0])
        n["Gemini second listen" if pick == 0 else "ElevenLabs second listen" if pick == 1 else "neither"] += 1
    return lines, {"how": "Gemini whole track vs ElevenLabs raw; disputed listen lines: both listen again, blind Gemini judge",
                   "disputed": len(disputed), "picks": dict(n), "eleven_second_listen_missing": no_el}


def write_version(L, cell, lines, info):
    p = os.path.join(L.dir, "versions", "%s.json" % cell)
    BC.W(p, dict(info, cell=cell, date=L.date, model=MODEL, built=time.strftime("%Y-%m-%dT%H:%M:%S"), lines=lines))
    return p


def run(date, cells, instant=False, log=print, net=None, data_root=None, root=None):
    os.environ["ANEES_REHEAR_AUTO"] = "off"
    cells = [c.upper() for c in cells]
    for c in cells:
        if c == "D":
            raise SystemExit("cell D needs forced alignment (whole-track text -> line times), which is not built: skipped")
        if c not in RUN_CELLS:
            raise SystemExit("cell %s: the run step builds %s (A and E come from the cache: `cached`)" % (c, ", ".join(RUN_CELLS)))
    L = Lesson(date, data_root, root)
    G = Gemini(L, instant=instant, net=net, log=log)
    whole = None
    out = {}
    for c in cells:
        if c == "B" or (c == "F" and whole is None):
            whole = whole_track(L, G, log)
        if c == "B":
            lines = {i: whole[0].get(i, "") for i in L.key["ids"]}
            out[c] = write_version(L, "B", lines, {"how": "Gemini whole track (pass 1 + pass 2), words on ElevenLabs' line times"})
        elif c == "C":
            lines, info = cell_C(L, G, log, net)
            out[c] = write_version(L, "C", lines, info)
        elif c == "F":
            lines, info = cell_F(L, G, log, net, whole)
            out[c] = write_version(L, "F", lines, info)
        log("%s cell %s written: %s (harness spend $%.2f of $%.2f)" % (date, c, os.path.relpath(out[c], REPO), spent(L.root), limit(L.root) or 0))
    return out


# ------------------------------------------------------------------ the free versions (cached runs)

def cached_versions(date, data_root=None, root=None, log=print):
    """A (production: 3 listens, word/span vote, two-clip release - rehear proposals.json), E (2 listens, the same
    production vote on runs 1+2, nothing released), Gemini run 1 alone, ElevenLabs raw. Spends nothing."""
    import bench_piles as PL
    import rehear_lesson as RL
    L = Lesson(date, data_root, root)
    rd = os.path.join(L.data_root, "lesson-work", "rehear", date)
    E = {i: L.key["engine"].get(i, "") for i in L.key["ids"]}
    by_i = {str(ln["i"]): "%.2f" % float(ln["t"]) for ln in L.rlines.values()}
    out = {}
    prop = BC.J(os.path.join(rd, "proposals.json")) or {}
    A = dict(E)
    for r in prop.get("rows") or []:
        kid = by_i.get(str(r["i"]))
        if kid and r.get("status") == "proposed" and r.get("heard") is not None:
            A[kid] = r["heard"]
    out["A"] = write_version(L, "A", A, {"how": "production: ElevenLabs cut + Gemini 3 listens, word/span vote 2-of-3, two-clip release (rehear proposals.json)"})
    runs = []
    for n in (1, 2):
        r = BC.J(os.path.join(rd, "base-run%d.json" % n)) or {}
        runs.append({i: o for i, o in (r.get("lines") or {}).items() if not o.get("error")})
    lines = [ln for ln in L.rlines.values() if ln.get("listen")]
    rows = PL.decide(PL.bare(lines), RL.valid_first(runs), L.amal, spans=True, v3_took=None)
    E2 = dict(E)
    for r in rows:
        kid = by_i.get(str(r["i"]))
        if kid and r.get("status") == "proposed" and r.get("heard") is not None:
            E2[kid] = r["heard"]
    out["E2"] = write_version(L, "E2", E2, {"how": "Gemini 2 listens, the production word/span vote (both must agree), nothing released"})
    g1, _ = HH.load_version(os.path.join(rd, "base-run1.json"), L.key, "engine")
    out["E1"] = write_version(L, "E1", g1, {"how": "Gemini 1 listen (rehear base-run1), ElevenLabs raw where not sent"})
    return out


# ------------------------------------------------------------------ the report

def versions_of(date, root=None):
    """[(name, label, path or @spec)] in table order; only what exists."""
    d = os.path.join(root or HDIR, date, "versions")
    rows = [("eleven", "ElevenLabs alone (raw)", "@engine")]
    for c, lab in (("E1", "Gemini 1 listen"), ("E2", "E: Gemini 2 listens (word vote)"), ("A", "A: today (3 listens, word vote)"),
                   ("B", "B: Gemini whole track"), ("C", "C: 3-engine vote + judge"), ("F", "F: both whole + relisten + judge")):
        p = os.path.join(d, c + ".json")
        if os.path.exists(p):
            rows.append((c, lab, p))
    rows.append(("page", "published page before review*", "@before"))
    return rows


CELL_STAGES = {"B": ("p1", "p2"), "C": ("deepgram", "judge-C"), "F": ("p1", "p2", "relisten-F", "eleven-relisten-F", "judge-F")}


def cell_cost(date, cell, root=None):
    """Dollars a cell's own calls cost on a lesson, from the spend file (B's whole-track text is shared with F: both
    count it). None for the free versions."""
    stages = CELL_STAGES.get(cell)
    if not stages:
        return None
    tot = 0.0
    for k, it in (spend_doc(root).get("items") or {}).items():
        d, _, rest = k.partition("/")
        rest = rest.split("#")[0]
        if d == date and any(rest == st or rest.startswith(st + "-") for st in stages):
            tot += it.get("usd") or 0.0
    return round(tot, 4)


def report(dates, data_root=None, root=None):
    out = {}
    for date in dates:
        key = HH.load_key(date, data_root or os.path.join(REPO, "data"))
        scored = []
        for name, lab, spec in versions_of(date, root):
            texts, info = HH.load_version(spec, key, "engine")
            s = HH.score_version(key, texts)
            scored.append((name, lab, s))
        base = next(s for n, _, s in scored if n == "A")
        rows = []
        for name, lab, s in scored:
            pr = HH.paired(s, base) if name != "A" else None
            cost = cell_cost(date, name, root)
            rows.append({"version": name, "label": lab, "hit": s["hit"], "words": s["words"], "hit_rate": s["hit_rate"],
                         "hidden": s["hidden"], "slips_judged": s["slips_judged"], "fcr": s["fcr"],
                         "vs_A": None if pr is None else {"only_this": pr["only_first"], "only_A": pr["only_second"], "p_sign": pr["p_sign"]},
                         "cost_usd": cost})
        out[date] = {"key": key["source"], "rows": rows}
    return out


def decide(res, first, second, base="A", alpha=0.05):
    """Protocol section 6 on two exam lessons: a version is a candidate when it beats today's way (A) on the first lesson
    (more words right, paired sign p < alpha) without a higher FCR; it is confirmed when the same holds on the second.
    Cost / human minutes and the key's own error rate (not measured yet) are left to Medi."""
    def wins(date, v):
        rows = {x["version"]: x for x in res[date]["rows"]}
        x, a = rows.get(v), rows[base]
        if not x or x["vs_A"] is None:
            return False
        return (x["vs_A"]["only_this"] > x["vs_A"]["only_A"] and x["vs_A"]["p_sign"] < alpha
                and (x["fcr"] or 0) <= (a["fcr"] or 0))
    out = []
    for x in res[first]["rows"]:
        v = x["version"]
        if v in (base, "page"):
            continue
        c1, c2 = wins(first, v), wins(second, v)
        out.append({"version": v, "wins_first": c1, "wins_second": c2, "adopt_candidate": c1 and c2})
    return out


def write_experiments(res, first, second, note="", path=None):
    """Append (or replace, same date + lessons) this run in data/lesson-work/harness/experiments.json: the Grades tab's
    `experiments` (docs/data/review-grades.json, built by review_grades.py)."""
    path = path or os.path.join(HDIR, "experiments.json")
    doc = BC.J(path) or {"about": "Pipeline tests on exam lessons (protocol sections 5-7), written by scripts/hearing_run.py "
                                  "report --write; read into docs/data/review-grades.json `experiments` by review_grades.py.", "runs": []}
    dec = decide(res, first, second)
    winners = [d["version"] for d in dec if d["adopt_candidate"]]
    run = {"date": time.strftime("%Y-%m-%d"), "lessons": [first, second], "base": "A",
           "scores": {d: [{k: x[k] for k in ("version", "label", "hit_rate", "hidden", "slips_judged", "fcr", "vs_A", "cost_usd")}
                          for x in r["rows"]] for d, r in res.items()},
           "decision": dec, "winner": winners or None, "adopted": False, "note": note}
    doc["runs"] = [r for r in doc["runs"] if (r["date"], r["lessons"]) != (run["date"], run["lessons"])] + [run]
    BC.W(path, doc)
    return run


def print_report(res):
    for date, r in res.items():
        print("%s (key %s)" % (date, r["key"]))
        print("  %-36s %-18s %-12s %s" % ("version", "hit rate", "FCR", "vs A: words only it / only A, sign p"))
        for x in r["rows"]:
            v = x["vs_A"]
            print("  %-36s %-18s %-12s %s" % (x["label"], "%d/%d %.1f%%" % (x["hit"], x["words"], x["hit_rate"]),
                                            "%d/%d" % (x["hidden"], x["slips_judged"]),
                                            "-" if v is None else "+%d / -%d  p=%s" % (v["only_this"], v["only_A"], v["p_sign"])))
        print("  * the page Medi corrected: advantaged (his review fixed this very page's lines)")


# ------------------------------------------------------------------ plan (no money)

def plan(date, cells, log=print):
    rows = HH.dry_run(date, os.path.join(REPO, "data"), BC.RAW, [(c, HH.cell(c)) for c in cells], out=lambda *_: None)["cells"]
    tot = 0.0
    for c in cells:
        log("%s cell %s: about $%.2f%s" % (date, c, rows[c]["paid_usd"], " (+ unpriced)" if rows[c]["has_unpriced"] else ""))
        tot += rows[c]["paid_usd"]
    log("%s total about $%.2f; harness spend so far $%.2f of $%s" % (date, tot, spent(), limit()))
    return tot


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hearing_run.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("date")
    p.add_argument("--cell", default="B,C,F")
    r = sub.add_parser("run")
    r.add_argument("date")
    r.add_argument("--cell", required=True)
    r.add_argument("--instant", action="store_true", help="instant Gemini calls (twice the price) instead of Batch")
    c = sub.add_parser("cached")
    c.add_argument("date")
    rp = sub.add_parser("report")
    rp.add_argument("dates", nargs="+")
    rp.add_argument("--json", action="store_true")
    rp.add_argument("--write", action="store_true", help="two lessons: the decision (protocol section 6) -> harness/experiments.json")
    rp.add_argument("--note", default="")
    a = ap.parse_args(argv)
    cells = [x.strip().upper() for x in getattr(a, "cell", "").split(",") if x.strip()] if hasattr(a, "cell") else []
    if a.cmd == "plan":
        plan(a.date, cells)
    elif a.cmd == "run":
        run(a.date, cells, instant=a.instant)
    elif a.cmd == "cached":
        for k, v in cached_versions(a.date).items():
            print(k, os.path.relpath(v, REPO))
    elif a.cmd == "report":
        res = report(a.dates)
        if a.write:
            if len(a.dates) != 2:
                raise SystemExit("--write needs the two exam lessons, first then second")
            print(json.dumps(write_experiments(res, a.dates[0], a.dates[1], a.note)["decision"]))
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print_report(res)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
