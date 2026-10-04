# -*- coding: utf-8 -*-
"""Spot check of the applied re-hear against the AUDIO (overnight backfill spec 2026-10-04, Phase 5: "Spot-read 20
changed lines per lesson against the audio for 3 lessons").

No person listens at night, so the check is a BLIND forced choice by the audio model, a different question from the
one that made the change: his clip for the line + two transcripts in random order (the engine's line, the re-heard
line), no context, no hint which is which - "which ONE is closest to what he ACTUALLY says?" (bench_vars.V2_PROMPT, the
frozen forced-choice prompt of the variables test). 3 runs per line, instant calls. It is a model's ear, not Medi's: it
is reported as such, and it decides nothing.

    python scripts/rehear_spot.py 2026-09-11 2026-09-21 2026-10-01      # PAID (about $0.15 a lesson): rehear/<date>/spot.json

The lines are drawn by a fixed seed from the lesson's applied WORD changes (never alphabet-only ones). Every call's
dollars go against the backfill allowance (a job record `spot` in the lesson's jobs folder) and get a run line.
"""
import json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import rehear_job as RJ  # noqa: E402
import rehear_lesson as RL  # noqa: E402

N, RUNS, EST = 20, 3, 0.004


def spot(date):
    d, man, lines, amal, prompts = RL.load(date)
    plan = BC.J(os.path.join(d, "apply-plan.json"))
    out_p = os.path.join(d, "spot.json")
    done = BC.J(out_p) or {"date": date, "rule": "blind forced choice, %d runs, bench_vars.V2_PROMPT (sha %s)" % (RUNS, BC.sha_text(BV.V2_PROMPT)[:16]), "lines": {}, "cost_usd": 0.0}
    pool = sorted((x for x in plan["lines_changed"] if x["kind"] == "words"), key=lambda x: x["i"])
    pick = random.Random("spot-" + date).sample(pool, min(N, len(pool)))
    by_i = {ln["i"]: ln for ln in lines}
    job_p = os.path.join(RJ.jobs_dir(date), "spot.job.json")
    os.makedirs(RJ.jobs_dir(date), exist_ok=True)
    todo = [x for x in pick if str(x["i"]) not in done["lines"]]
    est = EST * RUNS * len(todo)
    if RJ.spent(but=job_p) + (BC.J(job_p) or {}).get("usd", 0.0) + est > RJ.BACKFILL_LIMIT_USD:
        raise SystemExit("backfill allowance: the spot check of %s would pass $%.0f - not run" % (date, RJ.BACKFILL_LIMIT_USD))
    os.environ["ANEES_RUNS_DIR"] = os.path.join(RJ.REHEAR, date, "runs")

    def one(x):
        cands = [x["engine"], x["heard"]]
        random.Random("spot-%s-%d" % (date, x["i"])).shuffle(cands)
        opts = {"A": cands[0], "B": cands[1]}
        prompt = BV.V2_PROMPT.format(n=2, options="\n".join("%s) %s" % kv for kv in opts.items()))
        clip = os.path.join(d, by_i[x["i"]]["clip"])
        votes, usd = [], 0.0
        for _ in range(RUNS):
            o = BR.tried(lambda: BR.gemini(BV.MODEL, clip, prompt, temp=1))
            usd += o.get("usd") or 0.0
            if BV.unreached(o.get("error")):
                return x, None, usd
            ch = str((o.get("raw") or {}).get("choice") or "").strip().upper()[:1] if isinstance(o.get("raw"), dict) else ""
            votes.append("gemini" if opts.get(ch) == x["heard"] else "engine" if opts.get(ch) == x["engine"] else None)
        return x, votes, usd

    with ThreadPoolExecutor(6) as ex:
        for x, votes, usd in ex.map(one, todo):
            done["cost_usd"] = round(done["cost_usd"] + usd, 6)
            if usd:
                RJ._run_line(date, "rehear.spot", "spot", x["i"], usd, BR.wav_seconds(os.path.join(d, by_i[x["i"]]["clip"])))
            if votes is None:
                continue                                          # never reached the engine: not a verdict
            g = sum(1 for v in votes if v == "gemini")
            done["lines"][str(x["i"])] = {"mmss": x["mmss"], "engine": x["engine"], "heard": x["heard"], "votes": votes,
                                          "verdict": "new text" if g * 2 > RUNS else "old text" if sum(1 for v in votes if v == "engine") * 2 > RUNS else "split"}
    c = {k: sum(1 for v in done["lines"].values() if v["verdict"] == k) for k in ("new text", "old text", "split")}
    done.update(checked=len(done["lines"]), drawn=len(pick), word_changes_in_lesson=len(pool), prefers=c, built=time.strftime("%Y-%m-%dT%H:%M:%S"))
    BC.W(out_p, done)
    BC.W(job_p, {"name": "spot", "job": "instant calls", "state": "JOB_STATE_SUCCEEDED", "usd": done["cost_usd"], "est_usd": done["cost_usd"], "collected_complete": True, "requests": RUNS * len(done["lines"])})
    print("%s spot check: %d lines - the blind listen prefers the new text on %d, the old text on %d, split on %d ($%.2f)" % (date, done["checked"], c["new text"], c["old text"], c["split"], done["cost_usd"]), flush=True)
    return done


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for dt in sys.argv[1:]:
        spot(dt)
