# -*- coding: utf-8 -*-
"""The Gemini-only test (overnight backfill spec 2026-10-04, Phase 1; Medi: "why not have gemini do it all since its
more accurate?" - "lets test this first and make sure gemini can do it. We have seperate recordings for it no?").

Gemini does ALL of it on the benchmark lesson: no ElevenLabs text and no ElevenLabs timing go in.
  1. each speaker's own track is cut into segments by SILENCE ALONE (scripts/rehear_audio.py);
  2. pass 1: Gemini writes every segment of both speakers with no context (one prompt per speaker);
  3. pass 2: each of Medi's segments again, with pass 1's own text of the 40 s around it (both speakers) and Amal's
     typed chat as context - the frozen listener prompt (context_transcribe.PROMPT), its "engine text" now Gemini's own;
  4. 3 runs by Batch (run n's pass 2 reads run n's pass 1), scored by bench_score in whole-file mode: the words of a
     segment are laid over its voiced frames (audio alone) and bench_common.align_words puts them on the key's lines.

Pass rule (decision 1, written before the run): at least 54 of 63 on key v2, no more hidden slips than today's way,
and line times good enough for the page clips (TIMING below). The key is read by `score` only.

    python scripts/rehear_gonly.py 2026-10-02 freeze                 # segments + clips + prompt templates, hashed
    python scripts/rehear_gonly.py 2026-10-02 p1 <n> build|submit|collect
    python scripts/rehear_gonly.py 2026-10-02 p2 <n> build|submit|collect
    python scripts/rehear_gonly.py 2026-10-02 score                  # -> bench/<date>/gemini-only-batch-t1/whole-run<n>.json + timing.json
"""
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import context_transcribe as CT  # noqa: E402
import rehear_audio as RA  # noqa: E402

ENGINE = "gemini-only-batch-t1"
CTX_S, CHAT_S = 40.0, 60.0
SHORT_WORDS = 6                    # pass 2 is sent his segments with Arabic in pass 1's text, or this short (the listener's production rule)
P1_CFG = {"thinkingConfig": {"thinkingLevel": "low"}, "maxOutputTokens": 2048}     # a plain write-down: little thinking, a capped answer
# Timing, fixed before the run: a line of the key is "found" when one of his segments starts within 1.0 s of the line's
# start (THE GATE: 95 % of his lines); also shown: the line's start is inside one of his segments (0.5 s of slack).
TIMING = {"start_within_s": 1.0, "inside_slack_s": 0.5, "pass_start_within_pct": 95.0}     # the gate is the stricter measure (starts within 1.0 s)

P1_MEDI = """Audio of ONE speaker in an online Arabic lesson: Medi, an American learner of Levantine (Palestinian/Jordanian)
Arabic. He mixes English and Arabic and makes learner mistakes. Write exactly what he says, keeping his mistakes, wrong
words, wrong endings and false starts (do not correct his Arabic). If he speaks English, write the English. If the clip
has no speech (noise, breathing, a click), answer with empty strings.
Answer JSON only: {"arabic": "his words in Arabic script (English words stay English)", "arabizi": "his words in Latin letters with 2 3 5 6 7 8 9 for ء ع خ ط ح غ ص"}"""

P1_AMAL = """Audio of ONE speaker in an online Arabic lesson: Amal, a native Levantine (Palestinian/Jordanian) Arabic teacher
teaching an American learner. She speaks Levantine Arabic and English, and often says a sentence slowly for the learner
to repeat. Write exactly what she says, in her dialect as she says it (do not turn it into Modern Standard Arabic). If
she speaks English, write the English. If the clip has no speech (noise, breathing, a click), answer with empty strings.
Answer JSON only: {"arabic": "her words in Arabic script (English words stay English)", "arabizi": "her words in Latin letters with 2 3 5 6 7 8 9 for ء ع خ ط ح غ ص"}"""


def gdir(date):
    return os.path.join(RA.rdir(date), "gonly")


def chat_raw(date):
    """Amal's typed chat lines with their stamps on the CHAT clock (the Meet chat file; typed by her, no engine)."""
    import lesson_turns as LT
    return [{"start": c["start"], "text": c["text"]} for c in LT.chat_lines(date)]


def chat_lines(date, said):
    """The chat lines on the lesson clock, placed with GEMINI'S OWN pass-1 text only (Codex audit 2026-10-04: the lesson
    page's chat times were aligned on the old transcript, so they are not used). The chat clock differs from the
    recording clock by one unknown offset: every pair (typed line, a pass-1 segment that shares at least 60 % of its
    word skeletons, 3 or more) votes for an offset; the fullest 10-second bin wins and its median is the offset.
    said = [(segment, text)]. Returns ([{"t", "text"}], offset or None); no clear offset -> no chat lines at all."""
    import statistics
    import xscript as X
    raw = chat_raw(date)
    sk = lambda t: {X.skel(w) for w in X.tokens(t) if not X.is_english(w) and len(X.skel(w)) >= 2}  # noqa: E731
    vs = [(g["speech_a"], sk(t)) for g, t in said]
    vs = [(t0, k) for t0, k in vs if k]
    gaps = []                                                   # (chat line, the offset it votes for)
    for n, c in enumerate(raw):
        cs = sk(c["text"])
        if len(cs) < 3:
            continue
        for t0, k in vs:
            if len(cs & k) / float(len(cs)) >= 0.6:
                gaps.append((n, t0 - c["start"]))
    import collections
    votes = collections.defaultdict(set)                        # 10-second bin -> the DISTINCT chat lines voting for it
    for n, g in gaps:
        votes[int(g // 10)].add(n)
    if not votes:
        return [], None
    ranked = sorted(votes.items(), key=lambda kv: -len(kv[1]))
    b, lines = ranked[0]
    rival = max([len(v) for k, v in ranked[1:] if abs(k - b) > 1] or [0])
    if len(lines) < 3 or rival * 5 >= len(lines) * 3:          # fewer than 3 independent anchors, or a rival bin with 60 % as many: no chat
        return [], None
    off = float(statistics.median(g for n, g in gaps if int(g // 10) == b))
    return [{"t": c["start"] + off, "text": c["text"]} for c in raw], round(off, 1)


def freeze(date):
    d = gdir(date)
    mp = os.path.join(d, "manifest.json")
    if os.path.exists(mp):
        raise SystemExit("already frozen (%s)" % mp)
    segs, meta = RA.lesson_segments(date)
    srcs = RA.sources(date)
    clips = {}
    for g in segs:
        out = os.path.join(d, "clips", g["id"] + ".wav")
        s = srcs[g["who"]][g["k"]]
        RA.cut(s["file"], g["track_a"], g["track_b"], out)
        clips[g["id"]] = BC.sha_file(out)
    BC.W(os.path.join(d, "segments.json"), {"date": date, "rule": RA.SEG, "tracks": meta, "segments": segs})
    man = {"date": date, "engine": ENGINE, "frozen": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": BV.MODEL, "temperature": 1,
           "segments": len(segs), "segments_sha256": BC.sha_file(os.path.join(d, "segments.json")), "clips_sha256": BV.sha_obj(clips), "clips": clips,
           "p1_medi_sha256": BC.sha_text(P1_MEDI), "p1_amal_sha256": BC.sha_text(P1_AMAL), "p1_cfg": P1_CFG,
           "p2_template_sha256": BC.sha_text(CT.PROMPT), "p2_context_s": CTX_S, "p2_chat_s": CHAT_S, "p2_short_words": SHORT_WORDS,
           "timing_rule": TIMING, "seg_rule": RA.SEG,
           "inputs": "audio of each speaker's own track + Amal's typed chat lines; no ElevenLabs text, no ElevenLabs timing, no answer key",
           "p2_prompts_sha256": {}}
    BC.W(mp, man)
    print("frozen: %d segments (%s), clips %s" % (len(segs), ", ".join("%s %d" % (k, v["segments"]) for k, v in meta.items()), man["clips_sha256"][:16]))


def load(date):
    d = gdir(date)
    man = BC.J(os.path.join(d, "manifest.json"))
    if not man:
        raise SystemExit("not frozen")
    if BC.sha_file(os.path.join(d, "segments.json")) != man["segments_sha256"]:
        raise SystemExit("segments.json changed since the freeze")
    if (BC.sha_text(P1_MEDI), BC.sha_text(P1_AMAL), BC.sha_text(CT.PROMPT)) != (man["p1_medi_sha256"], man["p1_amal_sha256"], man["p2_template_sha256"]):
        raise SystemExit("a prompt changed since the freeze")
    segs = BC.J(os.path.join(d, "segments.json"))["segments"]
    return d, man, segs


def clip_path(d, g):
    return os.path.join(d, "clips", g["id"] + ".wav")


def check_clips(d, man, segs):
    bad = [g["id"] for g in segs if BC.sha_file(clip_path(d, g)) != man["clips"][g["id"]]]
    if bad:
        raise SystemExit("clips changed since the freeze: %s" % bad[:5])


def text_of(o):
    return ((o or {}).get("text") or "").strip()


def needs_p2(text):
    return bool(text) and (bool(BC.AR_LETTER.search(text)) or len(text.split()) <= SHORT_WORDS)


def p2_prompts(date, segs, p1):
    """{segment id: prompt} for his segments that get the second listen, from ONE pass-1 run (never the key, never the
    engine's transcript)."""
    rows = [(g, text_of(p1.get(g["id"]))) for g in segs]
    said = [(g, t) for g, t in rows if t]
    chat, off = chat_lines(date, said)
    p2_prompts.chat_offset = off
    out = {}
    for g, t in rows:
        if g["who"] != "Medi" or not needs_p2(t):
            continue
        t0 = g["speech_a"]
        ctx = "\n".join("%+.1f s %s: %s" % (v["speech_a"] - t0, v["who"], vt) for v, vt in said if v is not g and t0 - CTX_S <= v["speech_a"] <= t0 + CTX_S)
        ch = " | ".join(c["text"] for c in chat if t0 - CHAT_S <= c["t"] <= t0 + CHAT_S) or "(none)"
        out[g["id"]] = CT.PROMPT.format(context=ctx, chat=ch, target=t)
    return out


def run_paths(d, n):
    return {"p1": os.path.join(d, "p1-run%d.json" % n), "p2": os.path.join(d, "p2-run%d.json" % n), "p2p": os.path.join(d, "p2-prompts-run%d.json" % n)}


def stage(date, which, n, cmd):
    import batch_jobs as BJ
    import rehear_job as RJ
    d, man, segs = load(date)
    R = run_paths(d, n)
    name = "gonly-%s-run%d" % (which, n)
    by_id = {g["id"]: g for g in segs}
    secs = lambda k: BR.wav_seconds(clip_path(d, by_id[k]))  # noqa: E731
    if which == "p1":
        reqs = [(g["id"], clip_path(d, g), P1_MEDI if g["who"] == "Medi" else P1_AMAL, P1_CFG) for g in segs]
    else:
        p1 = BC.J(R["p1"])
        if not p1 or not p1.get("complete"):
            raise SystemExit("pass 1 run %d is not complete" % n)
        P = BC.J(R["p2p"])
        if cmd == "build":
            if P is None:
                P = p2_prompts(date, segs, p1["lines"])
                BC.W(R["p2p"], P)
                man["p2_prompts_sha256"][str(n)] = BV.sha_obj(P)        # frozen before its first call
                man.setdefault("p2_chat_offset_s", {})[str(n)] = p2_prompts.chat_offset
                BC.W(os.path.join(d, "manifest.json"), man)
        if P is None or BV.sha_obj(P) != man["p2_prompts_sha256"].get(str(n)):
            raise SystemExit("pass 2 run %d: prompts are not the frozen ones" % n)
        reqs = [(k, clip_path(d, by_id[k]), P[k], None) for k in sorted(P)]
    if cmd == "build":
        check_clips(d, man, segs)
        info = BJ.build(RJ.jobs_dir(date), name, BV.MODEL, ((k, BR.gemini_body(BV.MODEL, c, p, as_json=True, temp=1, cfg_extra=cfg)) for k, c, p, cfg in reqs),
                        meta={"keys": [k for k, *_ in reqs], "stage": which, "run": n})
        print("built %s: %d requests, %.1f MB" % (name, info["requests"], info["bytes"] / 1e6))
    elif cmd == "submit":
        est = RJ.estimate([(len(p), BR.wav_seconds(c)) for _, c, p, _ in reqs], out_tokens=150 if which == "p1" else 350)
        RJ.submit(date, name, est)
    elif cmd == "collect":
        RJ.collect(date, name, R[which], ENGINE + "." + which, seconds_of=secs)
    else:
        raise SystemExit(__doc__)


# ------------------------------------------------------------------ the score (the only place the key is read)

def final_text(g, p1, p2):
    """(arabic, arabizi) of a segment: the second listen when it was sent and answered, else the first."""
    o2 = (p2 or {}).get(g["id"])
    if o2 is not None and not o2.get("error"):
        return text_of(o2), (o2.get("alt") or "").strip()
    o1 = (p1 or {}).get(g["id"]) or {}
    return text_of(o1), (o1.get("alt") or "").strip()


def words_on_track(date, segs, p1, p2, who):
    """([{"text", "start", "end"}], the same for the Arabizi view) on the LESSON clock for one speaker: each segment's
    Arabic-script words are laid over its voiced frames; its Arabizi words take the times of the Arabic words at the
    same relative place (one time base for both views - Codex audit 2026-10-04)."""
    srcs = RA.sources(date)
    out, alt, cache = [], [], {}
    for g in segs:
        if g["who"] != who:
            continue
        ar, az = final_text(g, p1, p2)
        ws, zs = ar.split(), az.split()
        if not ws:
            continue
        if g["k"] not in cache:
            x, sr = BV.wav_samples(RA.whole_wav(date, who, g["k"], srcs[who][g["k"]]))
            cache[g["k"]] = (x, sr, RA.silent_frames(x, sr)[0])
        x, sr, quiet = cache[g["k"]]
        st = srcs[who][g["k"]]["start"]
        times = RA.voiced_times(x, sr, g["speech_a"] - st, g["speech_b"] - st, len(ws), quiet=quiet)
        for w, (a, b) in zip(ws, times):
            out.append({"text": w, "start": a + st, "end": b + st})
        for j, z in enumerate(zs):
            a, b = times[min(len(ws) - 1, int(j * len(ws) / float(len(zs))))]
            alt.append({"text": z, "start": a + st, "end": b + st})
    return out, alt


def timing(truth, segs):
    """Audio-only segments against the key's line times (his lines): found = a segment starts within 1.0 s of the
    line's start; inside = the line's start is inside one of his segments (the page's clip lands on his speech)."""
    mine = [g for g in segs if g["who"] == "Medi"]
    lines = truth["lines"]
    found = sum(1 for ln in lines if any(abs(g["speech_a"] - ln["t"]) <= TIMING["start_within_s"] for g in mine))
    inside = sum(1 for ln in lines if any(g["a"] - TIMING["inside_slack_s"] <= ln["t"] <= g["b"] + TIMING["inside_slack_s"] for g in mine))
    ar = [ln for ln in lines if ln["has_arabic"]]
    found_ar = sum(1 for ln in ar if any(abs(g["speech_a"] - ln["t"]) <= TIMING["start_within_s"] for g in mine))
    inside_ar = sum(1 for ln in ar if any(g["a"] - TIMING["inside_slack_s"] <= ln["t"] <= g["b"] + TIMING["inside_slack_s"] for g in mine))
    return {"his_lines": len(lines), "segment_start_within_1s": found, "start_within_1s_pct": round(100.0 * found / len(lines), 1),
            "line_start_inside_a_segment": inside, "inside_pct": round(100.0 * inside / len(lines), 1),
            "arabic_lines": len(ar), "arabic_start_within_1s_pct": round(100.0 * found_ar / len(ar), 1), "arabic_inside_pct": round(100.0 * inside_ar / len(ar), 1),
            "his_segments": len(mine), "rule": TIMING}


def score(date):
    d, man, segs = load(date)
    bd = BC.bench_dir(date)
    truth = BC.J(os.path.join(bd, "truth.json"))
    done = []
    for n in (1, 2, 3):
        R = run_paths(d, n)
        p1, p2 = BC.J(R["p1"]), BC.J(R["p2"])
        if not (p1 and p1.get("complete") and p2 and p2.get("complete")):
            continue
        lines = {}
        W, Z = words_on_track(date, segs, p1["lines"], p2["lines"], "Medi")
        for words, key in ((W, "text"), (Z, "alt")):
            for i, t in BC.align_words(words, truth["lines"], 0.0).items():      # the words are already on the lesson clock
                lines.setdefault(str(i), {})[key] = t
        WA, _ = words_on_track(date, segs, p1["lines"], p2["lines"], "Amal")
        for i, t in BC.align_words(WA, truth["amal_lines"], 0.0).items():
            lines["A%d" % i] = {"text": t}
        BC.W(os.path.join(bd, ENGINE, "whole-run%d.json" % n),
             {"engine": ENGINE, "mode": "whole", "run": n, "model": BV.MODEL, "transport": "batch", "complete": True, "seconds": 0.0,
              "cost_usd": round((p1.get("cost_usd") or 0) + (p2.get("cost_usd") or 0), 6),
              "how": "Gemini-only: silence segments of each speaker's own track, pass 1 no context, pass 2 his segments with pass 1's text around; words laid over voiced frames, bench_common.align_words",
              "segments": len(segs), "p2_sent": len(p2["lines"]), "lines": lines})
        done.append(n)
    T = timing(truth, segs)
    BC.W(os.path.join(d, "timing.json"), T)
    print("runs written:", done)
    print(json.dumps({k: v for k, v in T.items() if k != "rule"}))


PASS = {"key": "v2", "min_hit": 54, "today": "gemini-flash-t1"}      # decision 1: >= 54 of 63 on key v2, hidden slips <= today's way (the instant baseline)


def verdict(date):
    """The pass rule of decision 1, enforced: needs 3 complete runs, both keys scored, the timing gate. Writes
    gonly/verdict.json; changes no shared score file (bench_score.score is called in memory)."""
    import bench_score as BS
    d, man, segs = load(date)
    bd = BC.bench_dir(date)
    runs = BS.load_runs(bd, ENGINE, "whole")
    if len(runs) != 3:
        raise SystemExit("the verdict needs 3 complete runs (found %d)" % len(runs))
    out = {"date": date, "engine": ENGINE, "rule": dict(PASS, timing=man["timing_rule"]), "keys": {}}
    for key, f in (("v1", "truth.json"), ("v2", "truth-v2.json")):
        truth = BC.J(os.path.join(bd, f))
        mine = BS.score(truth, [r["lines"] for r in runs], whole_file=True)
        today = BS.score(truth, [r["lines"] for r in BS.load_runs(bd, PASS["today"], "line")])
        batch = BS.score(truth, [r["lines"] for r in BS.load_runs(bd, "gemini-flash-batch-t1", "line")])
        amal = BS.score_amal(truth, [r["lines"] for r in runs])
        row = lambda s: {k: s[k] for k in ("hit", "moments", "hidden_slips", "slips_judged", "content_changes", "should_stay", "stable_pct", "all_lines_pct", "language_switch_lines")}  # noqa: E731
        out["keys"][key] = {"gemini_only": row(mine), "today_instant": row(today), "today_batch": row(batch), "amal_moments": {"hit": amal["hit"], "of": amal["moments"]},
                            "per_moment": [{"id": m["id"], "final": m["final"]} for m in mine["per_moment"]]}
    T = timing(BC.J(os.path.join(bd, "truth.json")), segs)
    k2 = out["keys"][PASS["key"]]
    checks = {"heard_at_least_54_of_63_key_v2": k2["gemini_only"]["hit"] >= PASS["min_hit"],
              "no_more_hidden_slips_than_today": k2["gemini_only"]["hidden_slips"] <= k2["today_instant"]["hidden_slips"],
              "line_times_good_for_clips": T["start_within_1s_pct"] >= man["timing_rule"]["pass_start_within_pct"]}
    out.update(timing={k: v for k, v in T.items() if k != "rule"}, checks=checks, passed=all(checks.values()),
               cost_usd=round(sum(r.get("cost_usd") or 0 for r in runs), 4), decided=time.strftime("%Y-%m-%dT%H:%M:%S"))
    BC.W(os.path.join(d, "verdict.json"), out)
    print(json.dumps({"passed": out["passed"], "checks": checks, "v2": k2["gemini_only"], "today_v2": k2["today_instant"], "batch_v2": k2["today_batch"],
                      "v1": out["keys"]["v1"]["gemini_only"], "amal_v1": out["keys"]["v1"]["amal_moments"], "timing_pct": T["start_within_1s_pct"], "cost": out["cost_usd"]}, indent=1))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if len(argv) < 2:
        raise SystemExit(__doc__)
    if argv[1] == "freeze":
        freeze(argv[0])
    elif argv[1] in ("p1", "p2"):
        stage(argv[0], argv[1], int(argv[2]), argv[3])
    elif argv[1] == "score":
        score(argv[0])
    elif argv[1] == "verdict":
        verdict(argv[0])
    elif argv[1] == "timing":
        d, man, segs = load(argv[0])
        print(json.dumps(timing(BC.J(os.path.join(BC.bench_dir(argv[0]), "truth.json")), segs), indent=1))
    else:
        raise SystemExit(__doc__)
