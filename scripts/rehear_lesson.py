# -*- coding: utf-8 -*-
"""The Gemini re-hear of one lesson (TR-22 / PR-18; overnight backfill spec 2026-10-04, Phase 2): the benchmark's best
recipe, for any lesson date, by Google's Batch mode. Nothing here is applied to a lesson (scripts/rehear_apply.py does
that, after the audit); nothing reads an answer key.

The recipe = the plain baseline that heard 53 of 63 (instant) / 56 (Batch) of Medi's corrections on 10-02: Gemini 3.8
Flash, his own microphone clip per line, the frozen context prompt (context_transcribe.PROMPT; the raw engine text of
+-40 s of both speakers + Amal's chat +-60 s), temperature 1, 3 runs. Then, from the saved runs (scripts/bench_piles.py):
  - a change is PROPOSED when 2 of 3 runs wrote the same line, or the same changed span (word / span agreement);
  - a proposed change is HELD when a word it adds is a word Amal says in the next 15 s (it may be her correction written
    into his line), and RELEASED only when the two-clip check (his clip + hers, "did he say her word himself?",
    bench_vars.V3_PROMPT) says yes in 2 of 3 runs (Medi's decision 3); otherwise the line keeps its old text and is listed;
  - edge re-cut: a clip that starts or ends on speech (audio alone) is cut out to the nearest silence, never past his
    own previous / next line (the guard: the un-guarded re-cut pulled the next sentence into 3 of 16 lines on 10-02).

    python scripts/rehear_lesson.py <date> freeze
    python scripts/rehear_lesson.py <date> base <n> build|submit|collect
    python scripts/rehear_lesson.py <date> piles                       # from the 3 runs: piles + the two-clip prompts of the held lines
    python scripts/rehear_lesson.py <date> v3 <n> build|submit|collect
    python scripts/rehear_lesson.py <date> propose                     # proposals.json (final piles)
"""
import collections, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import bench_piles as PL  # noqa: E402
import context_transcribe as CT  # noqa: E402
import rehear_audio as RA  # noqa: E402

LABEL = "rehear.gemini-flash-batch-t1"
CTX_S, CHAT_S = 40.0, 60.0
SHORT_WORDS = 6
MAX_CLIP_S = 60.0                 # a line with a broken end time never sends more than a minute of audio
GUARD_S = 0.1                     # the re-cut stops this far from his previous / next line
RECUT_MAX_SHARE = 0.15            # on 10-02 the edge rule picked 16 of 472 clips (3 %); a track where it picks more than this is not noise-gated


def raw(u):
    return u.get("engine") or u["text"]


def ldir(date):
    return RA.rdir(date)


def page_turns(date):
    return BC.J(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json"))["turns"]


def build_lines(date):
    """(his lines, Amal's lines, chat) from the lesson page data. The engine's RAW text is used everywhere (never the
    overlay, a correction row or a ruling), as in the benchmark's freeze."""
    turns = page_turns(date)
    nxt = {}
    for k, u in enumerate(turns):
        later = [v["t"] for v in turns[k + 1:k + 8] if v["who"] in ("Medi", "Amal") and v["t"] > u["t"]]
        nxt[k] = min(later) if later else None
    lines, amal = [], []
    for i, u in enumerate(turns):
        if u["who"] not in ("Medi", "Amal"):
            continue
        end = u.get("end") or (min(nxt[i], u["t"] + 15.0) if nxt[i] else u["t"] + 2.0)
        end = min(max(end, u["t"] + 0.3), u["t"] + MAX_CLIP_S)
        if u["who"] == "Amal":
            amal.append({"i": i, "t": u["t"], "end": end, "text": raw(u)})
            continue
        e = raw(u)
        has_ar = bool(BC.AR_LETTER.search(e) or BC.AR_LETTER.search(u["text"]))
        lines.append({"i": i, "t": u["t"], "end": end, "engine": e, "has_arabic": has_ar,
                      "listen": bool(has_ar or BC.has_foreign(e) or len(e.split()) <= SHORT_WORDS)})
    chat = [{"t": u["t"], "text": u["text"]} for u in turns if u["who"] == "chat"]
    return turns, lines, amal, chat


def prompt_for(turns, ln, chat):
    ctx = "\n".join("%+.1f s %s: %s" % (v["t"] - ln["t"], v["who"], raw(v)) for k, v in enumerate(turns)
                    if v["who"] != "chat" and k != ln["i"] and ln["t"] - CTX_S <= v["t"] <= ln["t"] + CTX_S)     # as bench_freeze: every spoken turn (09-04 has a "?" speaker)
    ch = " | ".join(c["text"] for c in chat if ln["t"] - CHAT_S <= c["t"] <= ln["t"] + CHAT_S) or "(none)"
    return CT.PROMPT.format(context=ctx, chat=ch, target=ln["engine"])


def guard(window, prev_end, next_start, old):
    """The re-cut window, stopped at his own previous / next line (lesson clock). A side that the guard would push
    inside the old clip keeps the old clip's side. Returns ([a, b], [guarded start, guarded end])."""
    a, b = window
    ga = gb = False
    if prev_end is not None and a < prev_end + GUARD_S:
        a, ga = min(old[0], prev_end + GUARD_S), True
    if next_start is not None and b > next_start - GUARD_S:
        b, gb = max(old[1], next_start - GUARD_S), True
    a, b = min(a, old[0]), max(b, old[1])                     # never shorter than the standard clip on either side
    return [round(a, 3), round(b, 3)], [ga, gb]


def freeze(date):
    d = ldir(date)
    mp = os.path.join(d, "manifest.json")
    if os.path.exists(mp):
        raise SystemExit("already frozen (%s)" % mp)
    turns, lines, amal, chat = build_lines(date)
    srcs = RA.sources(date)
    listen = [ln for ln in lines if ln["listen"]]
    # 1. the standard clip of every listen line (lesson clock window t - PAD .. end + PAD), from his own track or the mix
    for ln in listen:
        ln["window"] = [round(max(0.0, ln["t"] - RA.PAD), 3), round(ln["end"] + RA.PAD, 3)]
        s = RA.source_at(srcs, "Medi", *ln["window"])
        ln["src"] = "own" if s else "mix"
        ln["k"] = (srcs["Medi"].index(s) if s else None)
        ln["clip"] = "clips/medi-%04d.wav" % ln["i"]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:                         # ffmpeg per clip: 8 at a time
        list(ex.map(lambda ln: RA.clip(date, "Medi", ln["window"][0], ln["window"][1], os.path.join(d, ln["clip"]), srcs), listen))
    # 2. edge re-cut (own track only; audio alone picks the lines), guarded by his own previous / next line
    recut, not_gated = 0, []
    for k, s in enumerate(srcs.get("Medi") or []):
        mine = [ln for ln in listen if ln["src"] == "own" and ln["k"] == k]
        if not mine:
            continue
        track, sr = BV.wav_samples(RA.whole_wav(date, "Medi", k, s))
        windows = {ln["i"]: (ln["window"][0] - s["start"], ln["window"][1] - s["start"]) for ln in mine}
        clips = {ln["i"]: BV.wav_samples(os.path.join(d, ln["clip"]))[0] for ln in mine}
        sel, level = BV.edge_lines(windows, clips, track, sr)
        if len(sel) > RECUT_MAX_SHARE * len(mine):            # the edge rule assumes digital silence between his turns (a noise-gated
            not_gated.append({"track": k, "lines": len(mine), "edge_lines": len(sel)})   # track); here most clips "start on speech": the rule does not hold, no re-cut
            continue
        order = sorted(lines, key=lambda x: x["t"])
        pos = {ln["i"]: n for n, ln in enumerate(order)}
        for ln in mine:
            r = sel.get(ln["i"])
            if not r:
                continue
            n = pos[ln["i"]]
            prev_end = order[n - 1]["end"] if n > 0 else None
            next_start = order[n + 1]["t"] if n + 1 < len(order) else None
            new = [r["new_window"][0] + s["start"], r["new_window"][1] + s["start"]]
            win, g = guard(new, prev_end, next_start, ln["window"])
            if win == ln["window"]:
                continue
            ln["recut"] = {"edge": r["edge"], "edge_db": r["edge_db"], "old_window": ln["window"], "guarded": g, "capped": r["capped"], "speech_level_db": level}
            ln["window"] = win
            RA.cut(s["file"], win[0] - s["start"], win[1] - s["start"], os.path.join(d, ln["clip"]))
            recut += 1
    prompts = {str(ln["i"]): prompt_for(turns, ln, chat) for ln in listen}
    clips = {ln["clip"]: BC.sha_file(os.path.join(d, ln["clip"])) for ln in listen}
    BC.W(os.path.join(d, "lines.json"), {"date": date, "lines": lines, "amal_all": [{"t": a["t"], "end": a["end"], "text": a["text"]} for a in amal]})
    BC.W(os.path.join(d, "prompts.json"), {"template_sha256": BC.sha_text(CT.PROMPT), "context_s": CTX_S, "chat_s": CHAT_S, "prompts": prompts})
    man = {"date": date, "label": LABEL, "frozen": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": BV.MODEL, "temperature": 1, "runs": 3,
           "page_data_sha256": BC.sha_file(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json")),
           "lines_sha256": BC.sha_file(os.path.join(d, "lines.json")), "prompts_sha256": BC.sha_file(os.path.join(d, "prompts.json")),
           "template_sha256": BC.sha_text(CT.PROMPT), "clips_sha256": BV.sha_obj(clips), "clips": clips,
           "counts": {"his_lines": len(lines), "listen": len(listen), "own_track": sum(1 for ln in listen if ln["src"] == "own"),
                      "mix": sum(1 for ln in listen if ln["src"] == "mix"), "recut": recut, "amal_lines": len(amal)},
           "recut_skipped_tracks": not_gated,
           "sources": {who: [{"file": os.path.basename(s["file"]), "start": s["start"], "dur": s["dur"]} for s in ss] for who, ss in srcs.items()},
           "v3_prompts_sha256": None}
    BC.W(mp, man)
    print("%s frozen: %s" % (date, json.dumps(man["counts"])))
    return man


def load(date, calling=False):
    """The frozen lesson. calling=True (a stage that SENDS prompts) also requires today's prompt template to be the frozen
    one; reading the saved runs back (piles, plan, spot, listen pages) needs only the frozen files themselves - the
    prompts.json they were made from is pinned by its own sha (2026-10-07: master's TR-26 cue changed the template after
    the 18 lessons were run)."""
    d = ldir(date)
    man = BC.J(os.path.join(d, "manifest.json"))
    if not man:
        raise SystemExit("%s is not frozen" % date)
    for f, k in (("lines.json", "lines_sha256"), ("prompts.json", "prompts_sha256")):
        if BC.sha_file(os.path.join(d, f)) != man[k]:
            raise SystemExit("%s: %s changed since the freeze" % (date, f))
    if calling and BC.sha_text(CT.PROMPT) != man["template_sha256"]:
        raise SystemExit("the prompt template changed since the freeze")
    L = BC.J(os.path.join(d, "lines.json"))
    return d, man, L["lines"], L["amal_all"], BC.J(os.path.join(d, "prompts.json"))["prompts"]


def check_clips(d, man, names):
    bad = [c for c in names if not os.path.exists(os.path.join(d, c)) or BC.sha_file(os.path.join(d, c)) != man["clips"].get(c)]
    if bad:
        raise SystemExit("clips missing or changed since the freeze: %s" % bad[:5])


def run_path(d, stage, n):
    return os.path.join(d, "%s-run%d.json" % (stage, n))


def base_stage(date, n, cmd):
    import batch_jobs as BJ
    import rehear_job as RJ
    d, man, lines, amal, prompts = load(date, calling=True)
    listen = [ln for ln in lines if ln["listen"]]
    name = "base-run%d" % n
    clip = {str(ln["i"]): os.path.join(d, ln["clip"]) for ln in listen}
    have = (BC.J(run_path(d, "base", n)) or {}).get("lines") or {}       # answers already stored (a seeded or half-collected run) are not sent
    if cmd == "build":
        todo = [str(ln["i"]) for ln in listen if str(ln["i"]) not in have]
        if not todo:                                              # every answer is already stored (a fully seeded run): no job
            rec = BC.J(run_path(d, "base", n))
            rec["complete"] = True
            BC.W(run_path(d, "base", n), rec)
            print("%s %s: every answer is already stored, nothing to send" % (date, name), flush=True)
            return
        check_clips(d, man, [ln["clip"] for ln in listen])
        info = BJ.build(RJ.jobs_dir(date), name, BV.MODEL, ((k, BR.gemini_body(BV.MODEL, clip[k], prompts[k], as_json=True, temp=1)) for k in todo),
                        meta={"keys": todo, "stage": "base", "run": n})
        print("built %s %s: %d requests, %.1f MB" % (date, name, info["requests"], info["bytes"] / 1e6), flush=True)
    elif cmd == "submit":
        keys = (BC.J(BJ.paths(RJ.jobs_dir(date), name)["build"]) or {}).get("keys") or []
        RJ.submit(date, name, RJ.estimate([(len(prompts[k]), BR.wav_seconds(clip[k])) for k in keys]))
    elif cmd == "collect":
        return RJ.collect(date, name, run_path(d, "base", n), LABEL, seconds_of=lambda k: BR.wav_seconds(clip[k]), wanted=sorted(clip, key=int))
    else:
        raise SystemExit(__doc__)


# ------------------------------------------------------------------ piles (bench_piles.decide: never a key)

def valid_first(runs):
    """The same answers with, per line, the runs that answered put first. bench_piles.decide reads a missing answer as
    the engine's text and breaks a tie by run order, so WHICH run failed could decide a line (Codex audit 2026-10-04);
    with the answered runs first the result is the same whichever run failed."""
    keys = set().union(*[set(r) for r in runs]) if runs else set()
    out = [dict() for _ in runs]
    for k in keys:
        for n, o in enumerate([r[k] for r in runs if k in r]):
            out[n][k] = o
    return out


def base_runs(d):
    runs = []
    for n in (1, 2, 3):
        r = BC.J(run_path(d, "base", n))
        if not r or not r.get("complete"):
            raise SystemExit("base run %d is not complete" % n)
        runs.append({i: o for i, o in r["lines"].items() if not o.get("error")})      # a failed call changes nothing: the engine's text stands for that run
    return valid_first(runs)


def took(raw_answer, asked):
    """The two-clip verdict of one run: True only when the answer covers EVERY word that was asked about and says the
    learner said each of them himself (an answer about some of the words releases nothing - Codex audit 2026-10-04)."""
    w = (raw_answer or {}).get("words") if isinstance(raw_answer, dict) else None
    if not w or not all(isinstance(x, dict) for x in w):
        return False
    said = {BC.norm_token(str(x.get("word") or "")) for x in w if x.get("same") is True}
    return all(BC.norm_token(a) in said for a in asked) and all(x.get("same") is True for x in w)


def script_only(engine, heard):
    """True when `heard` is the engine's line with NO word changed: the same number of words, each one equal after the
    normaliser, or the same word in the other alphabet (one side Arabic script, the other Latin, the SAME consonant skeleton -
    not bench_common.same_sound, which lets one consonant differ: katab / كذب).
    English "like" -> "hate" is a word change (Codex audit 2026-10-04: bench_score.content_change looks at Arabic words only)."""
    a, b = BC.tokens(engine, fillers=True), BC.tokens(heard, fillers=True)
    if len(a) != len(b):
        return False
    return all(BC.tok_eq(x, y) or (BC.is_ar(x) != BC.is_ar(y) and BC.skel(x) != "" and BC.skel(x) == BC.skel(y)) for x, y in zip(a, b))


def decide(date):
    d, man, lines, amal, prompts = load(date)
    runs = base_runs(d)
    bare = PL.bare([ln for ln in lines if ln["listen"]])
    rows = PL.decide(bare, runs, amal, spans=True, v3_took=None)
    mix = {ln["i"] for ln in lines if ln.get("src") == "mix"}
    for r in rows:
        # A line cut from the MIXED recording has Amal's voice in it: a change of WORDS there is never proposed or
        # released by a check (the two-clip check would hear her too). It is listed for Medi (status held-mix). A change
        # of alphabet only (his Arabic written in English letters) adds no word and may be proposed.
        if r["i"] in mix and r["heard"] is not None and not script_only(r["engine"], r["heard"]):
            r.update(status="held-mix")
    return d, man, lines, amal, rows


def v3_rows(date, d, lines, amal, rows):
    """The two-clip check of every held line: her lines after his that carry the added word(s), cut from her own track."""
    by_i = {ln["i"]: ln for ln in lines}
    srcs = RA.sources(date)
    out = {}
    for r in rows:
        if r["status"] != "held":
            continue
        ln = by_i[r["i"]]
        hers = [a for a in amal if ln["t"] < a["t"] <= ln["end"] + PL.AMAL_NEXT_S and set(r["amal_next"]) & set(BC.tokens(a["text"]))]
        if not hers:
            continue
        words = []
        for a in hers:
            for w in re.split(r"[^ء-ْA-Za-z']+", a["text"]):
                if w and BC.norm_token(w) in r["amal_next"] and w not in words:
                    words.append(w)
        if not words:
            continue
        span = [min(a["t"] for a in hers), min(max(a["end"] for a in hers), min(a["t"] for a in hers) + 30.0)]
        clip = "clips/v3-amal-%04d.wav" % r["i"]
        src = RA.clip(date, "Amal", max(0.0, span[0] - RA.PAD), span[1] + RA.PAD, os.path.join(d, clip), srcs)
        out[str(r["i"])] = {"amal_words": words, "amal_span": span, "amal_clip": clip, "amal_src": src, "amal_clip_sha256": BC.sha_file(os.path.join(d, clip)),
                            "prompt": BV.V3_PROMPT.format(words=", ".join("«%s»" % w for w in words))}
    return out


def piles(date):
    d, man, lines, amal, rows = decide(date)
    vp = os.path.join(d, "v3-prompts.json")
    if man.get("v3_prompts_sha256") is None:
        P = v3_rows(date, d, lines, amal, rows)
        BC.W(vp, P)
        man["v3_prompts_sha256"] = BV.sha_obj(P)               # frozen before its first call
        man["v3_template_sha256"] = BC.sha_text(BV.V3_PROMPT)
        BC.W(os.path.join(d, "manifest.json"), man)
    c = collections.Counter(r["status"] for r in rows)
    print("%s piles: %d lines changed - proposed %d, held %d (two-clip check on %d), held on a mixed recording %d, no agreement %d" % (date, len(rows), c["proposed"], c["held"], len(BC.J(vp)), c["held-mix"], c["no-agreement"]), flush=True)
    return rows


def v3_load(d, man):
    P = BC.J(os.path.join(d, "v3-prompts.json"))
    if P is None or BV.sha_obj(P) != man.get("v3_prompts_sha256") or BC.sha_text(BV.V3_PROMPT) != man.get("v3_template_sha256"):
        raise SystemExit("the two-clip prompts are not the frozen ones (run `piles` first)")
    return P


def v3_stage(date, n, cmd):
    import batch_jobs as BJ
    import rehear_job as RJ
    d, man, lines, amal, prompts = load(date, calling=True)
    P = v3_load(d, man)
    by_i = {str(ln["i"]): ln for ln in lines}
    name = "v3-run%d" % n
    if not P:
        BC.W(run_path(d, "v3", n), {"label": LABEL + ".v3", "lines": {}, "cost_usd": 0.0, "complete": True, "note": "no held line"})
        print("%s %s: no held line, nothing to send" % (date, name))
        return
    if cmd == "build":
        bad = [i for i, row in P.items() if BC.sha_file(os.path.join(d, row["amal_clip"])) != row["amal_clip_sha256"]]
        if bad:
            raise SystemExit("two-clip clips changed since the freeze: %s" % bad[:5])
        check_clips(d, man, [by_i[i]["clip"] for i in P])
        info = BJ.build(RJ.jobs_dir(date), name, BV.MODEL,
                        ((i, BR.gemini_body(BV.MODEL, os.path.join(d, by_i[i]["clip"]), P[i]["prompt"], as_json=True, temp=1, more_audio=[os.path.join(d, P[i]["amal_clip"])])) for i in sorted(P, key=int)),
                        meta={"keys": sorted(P, key=int), "stage": "v3", "run": n})
        print("built %s %s: %d requests" % (date, name, info["requests"]), flush=True)
    elif cmd == "submit":
        RJ.submit(date, name, RJ.estimate([(len(P[i]["prompt"]), BR.wav_seconds(os.path.join(d, by_i[i]["clip"])) + BR.wav_seconds(os.path.join(d, P[i]["amal_clip"]))) for i in P]))
    elif cmd == "collect":
        return RJ.collect(date, name, run_path(d, "v3", n), LABEL + ".v3", seconds_of=lambda k: BR.wav_seconds(os.path.join(d, by_i[k]["clip"])))
    else:
        raise SystemExit(__doc__)


def propose(date):
    """The final piles: held lines released by the two-clip check (2 of 3 runs: he says every one of her words himself)."""
    d, man, lines, amal, rows = decide(date)
    P = v3_load(d, man)
    verdicts = collections.defaultdict(list)
    for n in (1, 2, 3):
        r = BC.J(run_path(d, "v3", n))
        if not r or not r.get("complete"):
            raise SystemExit("two-clip run %d is not complete" % n)
        for i in P:
            o = r["lines"].get(i) or {}
            verdicts[i].append(None if o.get("error") else took(o.get("raw"), P[i]["amal_words"]))
    by_i = {ln["i"]: ln for ln in lines}
    for r in rows:
        ln = by_i[r["i"]]
        r.update(mmss="%02d:%02d" % (int(r["t"]) // 60, int(r["t"]) % 60), src=ln.get("src"), recut=bool(ln.get("recut")))
        if r["heard"] is not None:
            import bench_score as BS
            r["kind"] = "words" if BS.content_change(r["engine"], r["heard"]) else "alphabet"
        if r["status"] == "held":
            v = verdicts.get(str(r["i"]))
            r["two_clip"] = v
            if v and sum(1 for x in v if x is True) * 2 > len(v):
                r.update(status="proposed", released=True)
    c = collections.Counter(r["status"] for r in rows)
    summary = {"lines": len(lines), "listened": sum(1 for ln in lines if ln["listen"]), "changed": len(rows), "proposed": c["proposed"],
               "proposed_words": sum(1 for r in rows if r["status"] == "proposed" and r.get("kind") == "words"),
               "proposed_alphabet": sum(1 for r in rows if r["status"] == "proposed" and r.get("kind") == "alphabet"),
               "by_spans": sum(1 for r in rows if r["status"] == "proposed" and r["how"] == "spans"),
               "released_by_two_clip": sum(1 for r in rows if r.get("released")), "held": c["held"], "held_mix": c["held-mix"], "no_agreement": c["no-agreement"],
               "mix_lines": sum(1 for ln in lines if ln.get("src") == "mix"), "recut_lines": sum(1 for ln in lines if ln.get("recut")),
               "cost_usd": round(sum((BC.J(run_path(d, s, n)) or {}).get("cost_usd") or 0.0 for s in ("base", "v3") for n in (1, 2, 3)), 4)}
    BC.W(os.path.join(d, "proposals.json"), {"date": date, "label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "manifest_frozen": man["frozen"],
                                             "summary": summary, "rows": rows})
    print("%s proposals: %s" % (date, json.dumps(summary)), flush=True)
    return summary


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if len(argv) < 2:
        raise SystemExit(__doc__)
    date, cmd = argv[0], argv[1]
    if cmd == "freeze":
        freeze(date)
    elif cmd == "base":
        base_stage(date, int(argv[2]), argv[3])
    elif cmd == "piles":
        piles(date)
    elif cmd == "v3":
        v3_stage(date, int(argv[2]), argv[3])
    elif cmd == "propose":
        propose(date)
    else:
        raise SystemExit(__doc__)
