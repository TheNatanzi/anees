# -*- coding: utf-8 -*-
"""Amal's lines re-heard by Gemini (TR-22; overnight backfill spec 2026-10-04, Phase 2: "Amal's lines: re-hear them too
(her track), with a prompt written for a native teacher - but first measure it on the 6 Amal moments of the 10-02 key;
if it does not beat ElevenLabs there, leave her lines as they are"). Measured 2026-10-04 in the Gemini-only test: the
teacher prompt heard 2 of her 6 corrected moments, ElevenLabs 0 - so her lines are re-heard (Medi 2026-10-04, when the
agent had left them: "dude you overrode our decision").

The recipe is the one that was measured: rehear_gonly.P1_AMAL (no context, no word list), thinking low, temperature 1,
3 runs by Batch - here on the clip of each of her page lines (her own track; the engine's line times). A change is
PROPOSED when 2 of 3 runs wrote the same line or the same changed span (bench_piles.decide with spans; there is no
hold: nobody corrects her in the next 15 s). On a lesson with no own track her clip holds his voice too: a change of
words there is never applied (held-mix, listed).

    python scripts/rehear_amal.py <date> freeze
    python scripts/rehear_amal.py <date> run <n> build|submit|collect
    python scripts/rehear_amal.py <date> propose          # rehear/<date>/amal/proposals.json
    python scripts/rehear_amal.py pump [dates]            # every lesson: freeze, submit, collect, propose (resumable)
    python scripts/rehear_amal.py check10                 # 10-02 only: her 6 corrected moments + how many untouched lines change
"""
import collections, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import bench_piles as PL  # noqa: E402
import batch_jobs as BJ  # noqa: E402
import rehear_audio as RA  # noqa: E402
import rehear_gonly as RG  # noqa: E402
import rehear_job as RJ  # noqa: E402
import rehear_lesson as RL  # noqa: E402
import rehear_status as RS  # noqa: E402

LABEL = "rehear.amal.gemini-flash-batch-t1"


def adir(date):
    return os.path.join(RA.rdir(date), "amal")


def freeze(date):
    d = adir(date)
    mp = os.path.join(d, "manifest.json")
    if os.path.exists(mp):
        return BC.J(mp)
    turns, his, amal, chat = RL.build_lines(date)
    srcs = RA.sources(date)
    lines = []
    for a in amal:
        win = [round(max(0.0, a["t"] - RA.PAD), 3), round(a["end"] + RA.PAD, 3)]
        lines.append({"i": a["i"], "t": a["t"], "end": a["end"], "engine": a["text"], "window": win, "clip": "clips/amal-%04d.wav" % a["i"],
                      "src": "own" if RA.source_at(srcs, "Amal", *win) else "mix"})
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda ln: RA.clip(date, "Amal", ln["window"][0], ln["window"][1], os.path.join(d, ln["clip"]), srcs), lines))
    clips = {ln["clip"]: BC.sha_file(os.path.join(d, ln["clip"])) for ln in lines}
    BC.W(os.path.join(d, "lines.json"), {"date": date, "lines": lines})
    man = {"date": date, "label": LABEL, "frozen": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": BV.MODEL, "temperature": 1, "runs": 3, "cfg": RG.P1_CFG,
           "prompt_sha256": BC.sha_text(RG.P1_AMAL), "prompt": "rehear_gonly.P1_AMAL (the teacher prompt measured on her 6 moments: 2 of 6, ElevenLabs 0)",
           "lines_sha256": BC.sha_file(os.path.join(d, "lines.json")), "clips_sha256": BV.sha_obj(clips), "clips": clips,
           "counts": {"lines": len(lines), "own_track": sum(1 for x in lines if x["src"] == "own"), "mix": sum(1 for x in lines if x["src"] == "mix")}}
    BC.W(mp, man)
    print("%s Amal frozen: %s" % (date, json.dumps(man["counts"])), flush=True)
    return man


def load(date):
    d = adir(date)
    man = BC.J(os.path.join(d, "manifest.json"))
    if not man:
        raise SystemExit("%s: Amal's lines are not frozen" % date)
    if BC.sha_file(os.path.join(d, "lines.json")) != man["lines_sha256"] or BC.sha_text(RG.P1_AMAL) != man["prompt_sha256"] or man["model"] != BV.MODEL or man["cfg"] != RG.P1_CFG:
        raise SystemExit("%s: Amal's frozen lines or prompt changed" % date)
    return d, man, BC.J(os.path.join(d, "lines.json"))["lines"]


def run_path(d, n):
    return os.path.join(d, "run%d.json" % n)


def stage(date, n, cmd):
    d, man, lines = load(date)
    name = "amal-run%d" % n
    clip = {str(ln["i"]): os.path.join(d, ln["clip"]) for ln in lines}
    if cmd == "build":
        bad = [c for c in man["clips"] if BC.sha_file(os.path.join(d, c)) != man["clips"][c]]
        if bad:
            raise SystemExit("clips changed since the freeze: %s" % bad[:3])
        info = BJ.build(RJ.jobs_dir(date), name, BV.MODEL, ((k, BR.gemini_body(BV.MODEL, clip[k], RG.P1_AMAL, as_json=True, temp=1, cfg_extra=RG.P1_CFG)) for k in sorted(clip, key=int)),
                        meta={"keys": sorted(clip, key=int), "stage": "amal", "run": n})
        print("built %s %s: %d requests, %.1f MB" % (date, name, info["requests"], info["bytes"] / 1e6), flush=True)
    elif cmd == "submit":
        RJ.submit(date, name, RJ.estimate([(len(RG.P1_AMAL), BR.wav_seconds(c)) for c in clip.values()], out_tokens=60))
    elif cmd == "collect":
        return RJ.collect(date, name, run_path(d, n), LABEL, seconds_of=lambda k: BR.wav_seconds(clip[k]), wanted=sorted(clip, key=int))


def done(date, n):
    return bool((BC.J(run_path(adir(date), n)) or {}).get("complete"))


def propose(date):
    d, man, lines = load(date)
    runs = []
    for n in (1, 2, 3):
        r = BC.J(run_path(d, n))
        if not r or not r.get("complete"):
            raise SystemExit("%s Amal run %d is not complete" % (date, n))
        runs.append({i: o for i, o in r["lines"].items() if not o.get("error")})
    runs = RL.valid_first(runs)
    rows = PL.decide(PL.bare(lines), runs, [], spans=True, v3_took=None)
    by_i = {ln["i"]: ln for ln in lines}
    for r in rows:
        r.update(mmss="%02d:%02d" % (int(r["t"]) // 60, int(r["t"]) % 60), src=by_i[r["i"]]["src"], who="Amal")
        if r["heard"] is not None:
            r["kind"] = "alphabet" if RL.script_only(r["engine"], r["heard"]) else "words"       # an English word changed is a word change too
            if by_i[r["i"]]["src"] == "mix" and not RL.script_only(r["engine"], r["heard"]):
                r["status"] = "held-mix"
    c = collections.Counter(r["status"] for r in rows)
    summary = {"lines": len(lines), "changed": len(rows), "proposed": c["proposed"], "proposed_words": sum(1 for r in rows if r["status"] == "proposed" and r.get("kind") == "words"),
               "proposed_alphabet": sum(1 for r in rows if r["status"] == "proposed" and r.get("kind") == "alphabet"), "held_mix": c["held-mix"], "no_agreement": c["no-agreement"],
               "cost_usd": round(sum((BC.J(run_path(d, n)) or {}).get("cost_usd") or 0.0 for n in (1, 2, 3)), 4)}
    BC.W(os.path.join(d, "proposals.json"), {"date": date, "label": LABEL, "who": "Amal", "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "summary": summary, "rows": rows})
    print("%s Amal proposals: %s" % (date, json.dumps(summary)), flush=True)
    return summary


def pump(ds, every=90):
    import rehear_backfill as RB
    fails = {}
    while True:
        left = []
        for d in ds:
            try:
                if os.path.exists(os.path.join(adir(d), "proposals.json")):
                    continue
                freeze(d)
                for n in (1, 2, 3):
                    if done(d, n):
                        continue
                    s = RJ.state(d, "amal-run%d" % n)
                    if s == "none":
                        stage(d, n, "build")
                        s = "built"
                    if s == "built":
                        stage(d, n, "submit")
                    else:
                        RB.settle(d, "amal-run%d" % n, lambda n=n, d=d: stage(d, n, "collect"))
                if all(done(d, n) for n in (1, 2, 3)):
                    propose(d)
                else:
                    left.append(d)
            except SystemExit as e:
                msg = str(e)
                waiting = "allowance" in msg and any(j.get("job") and not j.get("collected_complete") and j.get("state") not in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED") for _, j in RJ.all_jobs())
                if waiting or (any(k in msg for k in ("batch status", "results download", "file upload")) and not any(k in msg for k in ("402", "429", "allowance"))):
                    left.append(d)
                else:
                    print("STOPPED %s: %s" % (d, msg[:300]), flush=True)
                    return 1
            except Exception as e:  # noqa: BLE001
                left.append(d)
                fails[d] = fails.get(d, 0) + 1
                print("retry %s: %s" % (d, str(e)[:120]), flush=True)
                if fails[d] > 20:                                 # the same lesson failing 20 rounds is not a dropped connection
                    print("STOPPED %s: failing every round" % d, flush=True)
                    return 1
        print(time.strftime("%H:%M:%S"), "Amal: %d of %d lessons proposed; waiting: %s" % (len(ds) - len(left), len(ds), " ".join(x[5:] for x in left) or "none"), flush=True)
        if not left:
            return 0
        time.sleep(every)


def check10(date="2026-10-02"):
    """Her 6 corrected moments on the benchmark key, by line clips (the key is read here only), and how many of her
    uncorrected lines get a word changed."""
    import bench_score as BS
    d, man, lines = load(date)
    truth = BC.J(os.path.join(BC.bench_dir(date), "truth.json"))
    runs = [{("A" + i): o for i, o in BC.J(run_path(d, n))["lines"].items()} for n in (1, 2, 3)]
    s = BS.score_amal(truth, runs)
    P = BC.J(os.path.join(d, "proposals.json"))
    corrected = {m["i"] for m in truth["amal_moments"]}
    words = [r for r in P["rows"] if r["status"] == "proposed" and r.get("kind") == "words" and r["i"] not in corrected]
    out = {"her_corrected_moments_heard": s["hit"], "of": s["moments"], "per_moment": [(m["id"], m["final"]) for m in s["per_moment"]],
           "her_lines": len(lines), "uncorrected_lines_with_a_word_changed": len(words), "alphabet_only": P["summary"]["proposed_alphabet"], "no_agreement": P["summary"]["no_agreement"]}
    BC.W(os.path.join(d, "check10.json"), dict(out, sample=[{"mmss": r["mmss"], "engine": r["engine"], "heard": r["heard"]} for r in words[:40]]))
    print(json.dumps(out, ensure_ascii=False))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if argv and argv[0] == "pump":
        sys.exit(pump(argv[1:] or RS.published()))
    elif argv and argv[0] == "check10":
        check10()
    elif len(argv) >= 2 and argv[1] == "freeze":
        freeze(argv[0])
    elif len(argv) >= 4 and argv[1] == "run":
        stage(argv[0], int(argv[2]), argv[3])
    elif len(argv) >= 2 and argv[1] == "propose":
        propose(argv[0])
    else:
        raise SystemExit(__doc__)
