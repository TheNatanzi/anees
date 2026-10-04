# -*- coding: utf-8 -*-
"""The overnight Gemini re-hear of every published lesson (TR-22 / PR-18; spec ANEES-GEMINI-BACKFILL-OVERNIGHT-SPEC-2026-10-04).
Drives scripts/rehear_lesson.py over all lessons and can be stopped and started again at any point without paying
twice: a frozen lesson is not frozen again, a submitted job is never created twice, collect skips stored answers.

    python scripts/rehear_backfill.py freeze [dates]     # clips + prompts + hashes per lesson (no network)
    python scripts/rehear_backfill.py submit [dates]     # PAID: the 3 base runs of each lesson (allowance checked per job)
    python scripts/rehear_backfill.py pump [dates]       # collect what is done; piles; PAID two-clip runs; proposals. Run until "all done"
    python scripts/rehear_backfill.py table              # where every lesson stands + dollars

Nothing here changes a lesson's transcript (scripts/rehear_apply.py). The status mark of a lesson (PG-27,
data/lesson-work/rehear-status.json) moves pending -> submitted when its first job is sent and -> proposed when its
proposals are written; `applied` is set only by the apply step.
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_vars as BV  # noqa: E402
import batch_jobs as BJ  # noqa: E402
import rehear_audio as RA  # noqa: E402
import rehear_job as RJ  # noqa: E402
import rehear_lesson as RL  # noqa: E402
import rehear_status as RS  # noqa: E402



def dates(argv):
    return argv or RS.published()


def set_status(date, status, note):
    """One lesson's second-listen mark, moved forward only (never back), with the lesson page re-stamped."""
    order = ["pending", "submitted", "proposed", "applied"]
    doc = RS.load()
    row = doc["lessons"].get(date) or {"status": "pending", "since": RS.today(), "note": ""}
    if order.index(status) <= order.index(row["status"]):
        return
    doc["lessons"][date] = {"status": status, "since": RS.today(), "note": note}
    RS.stamp_pages(RS.save(doc))


def freeze(ds):
    for d in ds:
        if os.path.exists(os.path.join(RL.ldir(d), "manifest.json")):
            print(d, "already frozen")
            continue
        RL.freeze(d)


def jobs_of(date, stage):
    return [(n, RJ.state(date, "%s-run%d" % (stage, n))) for n in (1, 2, 3)]


def run_done(date, stage, n):
    return bool((BC.J(RL.run_path(RL.ldir(date), stage, n)) or {}).get("complete"))


def submit(ds):
    for d in ds:
        for n in (1, 2, 3):
            if run_done(d, "base", n) or RJ.state(d, "base-run%d" % n) not in ("none", "built"):
                continue
            RL.base_stage(d, n, "build")
            if not run_done(d, "base", n):
                RL.base_stage(d, n, "submit")
        if all(run_done(d, "base", n) or RJ.state(d, "base-run%d" % n) not in ("none", "built") for n in (1, 2, 3)):
            set_status(d, "submitted", "Sent to Gemini (Batch) on %s; not all of its answers are back yet." % RS.today())


def stage_of(date):
    d = RL.ldir(date)
    if not os.path.exists(os.path.join(d, "manifest.json")):
        return "not frozen"
    if os.path.exists(os.path.join(d, "proposals.json")):
        return "proposed"
    if all(run_done(date, "base", n) for n in (1, 2, 3)):
        man = BC.J(os.path.join(d, "manifest.json"))
        return "two-clip" if man.get("v3_prompts_sha256") else "piles"
    return "base"


def settle(date, name, collect):
    """One job and its retry parts, one step: submit a part that is built and unsent; while any part is still with
    Google do nothing (never a second part for lines that are already bought - Codex audit 2026-10-04); when every part
    is finished, collect; lines still without an answer go into ONE more part (3 parts at most, then the lesson stops)."""
    folder = RJ.jobs_dir(date)
    parts = BJ.parts(folder, name)
    states = [RJ.state(date, nm) for _, nm in parts]
    for (k, nm), s in zip(parts, states):
        if s == "built" and k > 1:
            full = BC.J(BJ.paths(folder, name)["job"]) or {}
            n_req = (BC.J(BJ.paths(folder, nm)["build"]) or {}).get("requests") or 0
            RJ.submit(date, nm, round((full.get("est_usd") or 0.0) * n_req / max(1, full.get("requests") or n_req), 4))
            return
    if any(s not in BJ.DONE for s in states):
        return                                                    # still running (or part 1 not submitted: `submit` does that)
    rec, missing = collect()
    if not missing:
        return
    if len(parts) >= 3:
        raise SystemExit("%s %s: %d lines still have no answer after 3 parts" % (date, name, len(missing)))
    BJ.missing_part(folder, name, missing, len(parts) + 1)        # sent on the next step (it is "built")


def clean(date):
    """The request files (base64 audio) of a finished lesson go only when every job of it is finished and collected."""
    folder = RJ.jobs_dir(date)
    jobs = [BC.J(os.path.join(folder, f)) or {} for f in os.listdir(folder) if f.endswith(".job.json")]
    if jobs and all(j.get("state") == "JOB_STATE_SUCCEEDED" and j.get("collected_complete") for j in jobs):     # a failed / expired / half-collected job keeps every request file
        for f in os.listdir(folder):
            if f.endswith(".jsonl") and not f.endswith(".results.jsonl"):
                os.unlink(os.path.join(folder, f))


def pump_one(date):
    """One step forward for one lesson. Returns its stage after the step."""
    st = stage_of(date)
    if st == "base":
        for n in (1, 2, 3):
            if not run_done(date, "base", n) and RJ.state(date, "base-run%d" % n) not in ("none", "built"):
                settle(date, "base-run%d" % n, lambda n=n: RL.base_stage(date, n, "collect"))
        st = stage_of(date)
    if st == "piles":
        RL.piles(date)
        st = stage_of(date)
    if st == "two-clip":
        for n in (1, 2, 3):
            if run_done(date, "v3", n):
                continue
            s = RJ.state(date, "v3-run%d" % n)
            if s == "none":
                RL.v3_stage(date, n, "build")                     # (no held line -> an empty complete run, no job)
                s = "built" if not run_done(date, "v3", n) else "done"
            if s == "built":
                RL.v3_stage(date, n, "submit")
            elif s != "done":
                settle(date, "v3-run%d" % n, lambda n=n: RL.v3_stage(date, n, "collect"))
        if all(run_done(date, "v3", n) for n in (1, 2, 3)):
            RL.propose(date)
            set_status(date, "proposed", "Gemini's second listen ran on %s (3 runs); its changes are being checked and none is in the transcript yet." % RS.today())
            clean(date)
            st = "proposed"
    return st


def table(ds):
    print("%-11s %-10s %6s %5s %5s %8s %5s %5s %5s %8s" % ("lesson", "stage", "listen", "own", "mix", "proposed", "held", "mix-h", "none", "$"))
    for d in ds:
        st = stage_of(d)
        man = BC.J(os.path.join(RL.ldir(d), "manifest.json")) or {}
        c = man.get("counts") or {}
        s = (BC.J(os.path.join(RL.ldir(d), "proposals.json")) or {}).get("summary") or {}
        usd = sum((BC.J(RL.run_path(RL.ldir(d), stg, n)) or {}).get("cost_usd") or 0.0 for stg in ("base", "v3") for n in (1, 2, 3))
        print("%-11s %-10s %6s %5s %5s %8s %5s %5s %5s %8.2f" % (d, st, c.get("listen", ""), c.get("own_track", ""), c.get("mix", ""), s.get("proposed", ""), s.get("held", ""), s.get("held_mix", ""), s.get("no_agreement", ""), usd))
    print("allowance: $%.2f used or owed of $%.0f" % (RJ.spent(), RJ.BACKFILL_LIMIT_USD))


def pump(ds, every=90):
    while True:
        st = {}
        for d in ds:
            try:
                st[d] = pump_one(d)
            except SystemExit as e:                               # one lesson's refusal (allowance, credit) never hides the others
                st[d] = "STOPPED: %s" % str(e)[:200]
        left = [d for d, s in st.items() if s != "proposed"]
        print(time.strftime("%H:%M:%S"), "proposed %d of %d; waiting: %s" % (len(ds) - len(left), len(ds), ", ".join("%s (%s)" % (d[5:], st[d][:30]) for d in left) or "none"), flush=True)
        if not left:
            print("all done")
            return 0
        if any(s.startswith("STOPPED") for s in st.values()):
            return 1
        time.sleep(every)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)
    cmd, rest = argv[0], argv[1:]
    if cmd == "freeze":
        freeze(dates(rest))
    elif cmd == "submit":
        submit(dates(rest))
    elif cmd == "pump":
        sys.exit(pump(dates(rest)))
    elif cmd == "table":
        table(dates(rest))
    else:
        raise SystemExit(__doc__)
