# -*- coding: utf-8 -*-
"""The second listen runs by itself on every new lesson (TR-29, Medi 2026-10-09: "why the fuck wasnt it applied?" ...
"go and fix it permanently").

Why this exists: the Gemini re-hear (TR-22 / PR-18) was built as a one-time backfill (scripts/rehear_backfill.py, run by
hand 2026-10-04..07 over the 18 lessons up to 10-02). Nothing ran it on a lesson published after that: 10-05, 10-06 and
10-08 sat "Second listen: pending" with an ElevenLabs-only transcript, and the backfill's money lived in another
checkout's git-ignored job files, so from the hourly checkout the $45 allowance looked untouched.

Every hour (scripts/hourly_lessons.py calls step()), for each published lesson after the backfill that is not applied,
oldest first, ONE step forward - the same recipe, files and rules as the backfill (nothing new is decided here):
  not frozen      -> freeze (free: clips, prompts)
  base not sent   -> the 3 base runs, PAID, only inside Medi's new-lessons allowance (data/lesson-work/rehear/spend.json
                     new_lessons.monthly_usd; never raised by code); no room = the lesson waits with the reason on its
                     page chip and one LS-04 line ("10-08: second listen waiting - Google allowance $0 of $0 this month")
  answers out     -> collect / piles / two-clip runs / proposals (rehear_backfill.pump_one)
  proposed        -> rehear_apply plan + apply (2 of 3 runs agree; TR-27 holds for the tutor; his own corrections stay)
                     -> status applied -> the lesson joins the re-read queue (the three readers read the new text;
                     scripts/hourly_lessons.py runs review_lesson.py on it, one lesson an hour)
Never raises: a failed step is one problem line and the lesson tries again next hour.

    python scripts/rehear_auto.py            # one step for every lesson that needs one (what the hourly job runs)
    python scripts/rehear_auto.py show       # where each lesson after the backfill stands, and the money
"""
import datetime, json, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
REREAD_P = os.path.join(REPO, "data", "lesson-work", "rehear", "reread-queue.json")
WAIT = "Waiting for the Google allowance"


def _J(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def _W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def todo(published=None, status=None):
    """Published lessons after the backfill whose second listen is not applied, oldest first."""
    import rehear_job as RJ
    import rehear_status as RS
    doc = status if status is not None else RS.load()
    rows = doc.get("lessons") or {}
    return [d for d in (published if published is not None else RS.published())
            if d > RJ.BACKFILL_LAST and (rows.get(d) or {}).get("status") not in RS.APPLIED]


def base_estimate(date):
    """Dollars for the 3 base runs + the two-clip runs of one lesson, before anything is sent: the backfill's real
    cost per listened line (its 18 lessons) times this lesson's listened lines; else $3."""
    import rehear_job as RJ
    import rehear_lesson as RL
    import bench_common as BC
    man = BC.J(os.path.join(RL.ldir(date), "manifest.json")) or {}
    n = ((man.get("counts") or {}).get("listen")) or 0
    per_line = 0.0045                       # 2026-10-02: $4.45 for its whole run over ~470 listened lines x 2 (his + checks)
    return round(max(1.0, n * per_line), 2) if n else 3.0


def note_wait(date, msg):
    """The lesson stays pending; its chip sentence says why (rehear_status shows the note)."""
    import rehear_status as RS
    doc = RS.load()
    row = doc["lessons"].get(date) or {"status": "pending", "since": RS.today(), "note": ""}
    if row.get("status") == "pending" and row.get("note") != msg:
        row["note"] = msg
        doc["lessons"][date] = row
        RS.stamp_pages(RS.save(doc))
        return True
    return False


def record_spend():
    """The committed money record: every job of a lesson after the backfill in this checkout, real dollars when
    collected, else the estimate (a job sent and not back yet is money owed)."""
    import rehear_job as RJ
    p = RJ.SPEND_P
    doc = _J(p) or {}
    nl = doc.setdefault("new_lessons", {"monthly_usd": 0.0, "set_by": None, "jobs": {}})
    jobs = nl.setdefault("jobs", {})
    before = json.dumps(jobs, sort_keys=True)
    for path, j in RJ.all_jobs():
        d = os.path.basename(os.path.dirname(os.path.dirname(path)))
        if d <= RJ.BACKFILL_LAST or not (j.get("job") or j.get("create_attempted")):
            continue
        k = d + "/" + os.path.basename(path)
        jobs[k] = {"date": d, "usd": round(j.get("usd") if j.get("collected_complete") else max(j.get("est_usd") or 0.0, j.get("usd") or 0.0), 4),
                   "state": j.get("state"), "collected": bool(j.get("collected_complete")), "sent": j.get("create_attempted") or j.get("submitted")}
    if json.dumps(jobs, sort_keys=True) != before:
        _W(p, doc)
        return True
    return False


def queue_reread(date):
    q = _J(REREAD_P) or {"about": "Lessons whose transcript changed by the second listen (TR-29): the three readers read each again "
                                  "(review_lesson.py, run by the hourly job one lesson an hour); a lesson leaves when its review passes.",
                         "lessons": []}
    if date not in q["lessons"]:
        q["lessons"].append(date)
        _W(REREAD_P, q)


def reread_next():
    q = _J(REREAD_P) or {}
    return (q.get("lessons") or [None])[0]


def reread_done(date):
    q = _J(REREAD_P) or {}
    if date in (q.get("lessons") or []):
        q["lessons"].remove(date)
        _W(REREAD_P, q)


def step_one(date, log=print):
    """One step forward for one lesson. Returns (stage after, problem line or None)."""
    import rehear_backfill as RB
    import rehear_job as RJ
    import rehear_apply as RA
    st = RB.stage_of(date)
    if st == "not frozen":
        RB.freeze([date])
        st = RB.stage_of(date)
    if st != "not frozen":
        import rehear_lesson as RL
        n = RL.restore_clips(date)           # frozen elsewhere: the git-ignored clips are cut again, hash-checked
        if n:
            log("second listen: %s - %d clips cut again from the frozen windows (hashes match)" % (date, n))
    if st == "base":
        unsent = [n for n in (1, 2, 3) if not RB.run_done(date, "base", n) and RJ.state(date, "base-run%d" % n) in ("none", "built")]
        if unsent:
            pl, ml = RJ.per_lesson_limit(), RJ.new_lessons_limit()
            est = round(base_estimate(date) * len(unsent) / 3, 2)
            used = RJ.lesson_spent(date) if pl is not None else RJ.new_lessons_spent(date[:7])
            lim = pl if pl is not None else ml
            if lim is None or used + est > lim:
                what = "per lesson" if pl is not None else "for %s" % date[:7]
                msg = ("%s: $%.2f used of $%.2f %s, the next runs need about $%.2f. The transcript stays ElevenLabs only until "
                       "Medi changes the limit (data/lesson-work/rehear/spend.json)." % (WAIT, used, lim or 0.0, what, est))
                note_wait(date, msg)
                return st, "%s: second listen waiting - Google limit $%.2f %s, $%.2f used, needs about $%.2f" % (date[5:], lim or 0.0, what, used, est)
            note_wait(date, "")
            RB.submit([date])
        RB.pump_one(date)
        st = RB.stage_of(date)
    elif st in ("piles", "two-clip"):
        st = RB.pump_one(date)
    if st == "proposed":
        RA.plan(date)
        RA.apply([date])
        queue_reread(date)
        log("second listen applied:", date)
        st = "applied"
    return st, None


def step(log=print, dates=None):
    """Every lesson that needs one, one step. Never raises. -> {"stages": {date: stage}, "problems": [LS-04 rows], "changed": bool}"""
    out = {"stages": {}, "problems": [], "changed": False}
    if os.environ.get("ANEES_REHEAR_AUTO") == "off":           # kill switch (and tests: never a paid call)
        return out
    try:
        ds = todo() if dates is None else dates
    except Exception as e:  # noqa: BLE001
        out["problems"].append({"key": "rehear:scan", "kind": "rehear", "cause": "second listen scan failed: %s" % type(e).__name__})
        return out
    for d in ds:
        try:
            st, prob = step_one(d, log=log)
            out["stages"][d] = st
            if prob:
                out["problems"].append({"key": "rehear:" + d, "kind": "rehear", "date": d, "cause": prob})
        except SystemExit as e:
            out["problems"].append({"key": "rehear:" + d, "kind": "rehear", "date": d, "cause": "second listen step stopped: %s" % str(e)[:200]})
        except Exception as e:  # noqa: BLE001 - a failed lesson waits for the next hour
            log("rehear_auto", d, "failed:", "".join(traceback.format_exception_only(type(e), e)).strip()[:300])
            out["problems"].append({"key": "rehear:" + d, "kind": "rehear", "date": d, "cause": "second listen step failed: %s" % type(e).__name__})
    try:
        out["changed"] = record_spend() or out["changed"]
    except Exception as e:  # noqa: BLE001
        log("rehear_auto: spend record not written:", e)
    return out


def show():
    import rehear_backfill as RB
    import rehear_job as RJ
    import rehear_status as RS
    doc = RS.load()
    for d in todo():
        print(d, RB.stage_of(d), "|", RS.chip(d, doc)["label"], "|", (doc["lessons"].get(d) or {}).get("note", "")[:120])
    m = datetime.date.today().isoformat()[:7]
    for d in todo():
        print("  %s: $%.2f spent or owed" % (d, RJ.lesson_spent(d)))
    print("limits: per lesson %s, monthly %s ($%.2f in %s); backfill: $%.2f of $%.0f" % (
        RJ.per_lesson_limit(), RJ.new_lessons_limit(), RJ.new_lessons_spent(m), m, RJ.spent(), RJ.BACKFILL_LIMIT_USD))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if (sys.argv[1:] or ["step"])[0] == "show":
        show()
    else:
        res = step()
        print(json.dumps({k: v for k, v in res.items() if k != "changed"}, ensure_ascii=False))
