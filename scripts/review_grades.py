# -*- coding: utf-8 -*-
"""The grade book (PG-46): how well the pipeline did on a lesson Medi reviewed IN FULL, graded against his review.

Medi 2026-10-10: "We need to start keeping a grading system for these manual reviews that I've been doing ... make a tab
in the AI reports area for the grades ... only counting the Arabic and sorting out the English ... a tally of all the
Arabic words being said and how many mistakes it made ... How much of the vocab it keeps track of; How many mistakes it
made ... so that we can see if our process is actually improving". "10-8 should get a grade, the 2 previous should not
they were partial."

    python scripts/review_grades.py                 # build docs/data/review-grades.json
    python scripts/review_grades.py --check         # exit 1 when the built file is stale or a full review has no key
    python scripts/review_grades.py freeze <date>   # freeze the answer key + the pipeline's version for a new full review

The list of reviews is hand-made: data/lesson-work/review-grades/reviews.json ({date, full, note, before_commit,
key_commit}); a new full review is one line there + `freeze`. Only full reviews are graded; a partial one is listed as
'partial review, not graded'.

The exam, per graded lesson (frozen in data/lesson-work/review-grades/<date>.json so a later rebuild never moves it):
  before = the pipeline's own version of the lesson page before his first note (git: before_commit)
  key    = the lesson page after his review and the audit that applied his notes (git: key_commit) = the answer key
  now    = today's published page, graded against the same key (a rebuild that breaks his fixes shows here). Shown as
           "drift" (overnight brief 2026-10-10): today's page vs the key, a regression check only, never an accuracy
           score. The JSON key stays "now".
  The "before" page: data/lesson-work/review-grades/<date>.first.json when present (the page the hourly job FIRST
  published, frozen at that publish with its SHA by scripts/hourly_lessons.py freeze_first, protocol §2.1), else the
  page at before_commit in git.

Time and coverage of a fast review (PG-50, protocol §4 "time is measured, not guessed"), per lesson, from
data/lesson-work/medi-corrections.json (the mirror of Supabase transcript_corrections; every row there is his):
  minutes_medi  = sum of payload.secs of the fast-mode rows / 60 (null when the lesson has none)
  coverage_medi = share of his Arabic lines (docs/data/review-pick/<date>.json "lines", else his page lines with an
                  Arabic word by word_coverage word_tokens) that carry at least one fast-mode row (any kind, also the
                  inert "heard right" trace), matched by the row's turn_t (or payload.t) inside the line; null = no fast rows
  A fast-mode lesson is graded only when coverage_medi == 1.0, else "partial review, not graded (N of M lines)".
  A fast-mode row: payload.review_mode == "fast", or a review trace row (kind rule-answer, proposal "review:fast").
  Lessons reviewed the old way (10-08) are unchanged.
Only Arabic words of HIS lines count (scripts/word_coverage.py word_tokens: English, fillers, sound tags and subject
pronouns out; his Latin Arabizi the reader reads counts). Cut-off words and prepositions (scored as grammar, PG-43) are
not in the tally.
  Report 1 tracked  = words whose mark matches the key (credit, half, repeat, new, the same grey reason) / words said
  Report 2 mistakes = (a) missed slip   the key has a ✗ (the tutor corrected him), the version has none
                      (b) fake slip     the version has a ✗ the key does not
                      (c) untracked / wrong credit   no mark, or a different mark (credit vs repeat, another grey reason)
                      (d) misheard word the line's Arabic word is not the word he said
                      per 100 Arabic words.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DIR = os.path.join(REPO, "data", "lesson-work", "review-grades")
REVIEWS_P = os.path.join(DIR, "reviews.json")
OUT_P = os.path.join(REPO, "docs", "data", "review-grades.json")
TYPES = {"missed_slip": "missed slip: the tutor corrected him, no mistake marked",
         "fake_slip": "fake slip: a mistake marked that was not one",
         "untracked": "untracked or wrong credit: no mark, a wrong credit or a wrong grey reason",
         "misheard": "misheard word: the transcript had the wrong Arabic word"}
CAT = {"correct": "credit", "partial": "half", "asked": "half", "repeat": "repeat", "new": "new", "wrong": "slip"}


def J(p, d=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def page_at(commit, date, repo=REPO):
    """The published lesson page at a commit (None = the working tree)."""
    if not commit:
        return J(os.path.join(repo, "docs", "data", "lessons", date + ".json"), {}) or {}
    raw = subprocess.run(["git", "show", "%s:docs/data/lessons/%s.json" % (commit, date)], cwd=repo,
                         capture_output=True, check=True).stdout
    return json.loads(raw.decode("utf-8-sig"))


def reason(why, word):
    why = str(why or "")
    if word and why.startswith(word + ":"):
        why = why[len(word) + 1:]
    return re.sub(r"\s*\(.*$", "", why).strip().lower()[:80]


def cat(r):
    s = r.get("state")
    if not s:
        return None
    if s == "na":
        return "grey: " + reason(r.get("why"), r.get("word"))
    return CAT.get(s, s)


def snapshot(d, date):
    """The parts of a lesson page the grade reads: his Arabic words with their mark, his lines, the ✗ chips. A line is
    named by its start time ("i": "85.25"), never its index, so chat lines added later never shift the exam."""
    import word_coverage as WC
    turns, tm = d.get("turns") or [], d.get("tmarks") or {}
    words = []
    for r in WC.report(date, d=d):
        if r["cut"] or (r.get("quiet") and r.get("state") == "na"):
            continue                                  # cut-off words; prepositions are graded as grammar (PG-43)
        words.append({"i": "%.2f" % float(turns[r["i"]]["t"]), "t": r["t"], "word": r["word"], "cat": cat(r), "why": (r.get("why") or "")[:160]})
    lines = {"%.2f" % float(u["t"]): u.get("text") or "" for u in turns if u.get("who") == "Medi"}
    slips = []
    for k, v in tm.items():
        u = turns[int(k)] if int(k) < len(turns) else {}
        if u.get("who") != "Medi":
            continue
        for c in v.get("c", []):
            if c.get("s") == "wrong" and c.get("k") in ("vocab", "grammar"):
                slips.append({"i": "%.2f" % float(u["t"]), "t": WC.mmss(u["t"]), "k": c["k"], "rule": c.get("rule"),
                              "said": str(c.get("said") or c.get("tok") or "")[:60], "ar": str(c.get("ar") or "")[:60]})
    return {"words": words, "lines": lines, "slips": sorted(slips, key=lambda x: (x["i"], x["k"], x["rule"] or ""))}


def _same_slip(a, b):
    """The same ✗: same line and kind (a grammar ✗ also when the same rule sits on a line within 10 s: it moved)."""
    import word_coverage as WC
    if a["k"] != b["k"]:
        return False
    if a["i"] != b["i"]:
        return a["k"] == "grammar" and a.get("rule") == b.get("rule") and abs(WC._sec(a["t"]) - WC._sec(b["t"])) <= 10
    if a["k"] == "grammar":
        return a.get("rule") == b.get("rule")
    wa = {WC.core(x) for x in re.split(r"[\s،,.؟?/=()]+", a["said"] + " " + a["ar"]) if x}
    wb = {WC.core(x) for x in re.split(r"[\s،,.؟?/=()]+", b["said"] + " " + b["ar"]) if x}
    return bool(wa & wb) or not (wa and wb)


def _dist1(a, b):
    """True when a and b differ by at most one letter (one added, dropped or changed)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 2:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    lo, hi = sorted((a, b), key=len)
    return any(hi[:k] + hi[k + 1:] == lo for k in range(len(hi)))


def latin_unread(text, word):
    """The line has his word in Latin letters the Arabizi reader did not read (10-08 01:57 'Ayan' = عيان): the right
    word, never tracked - an untracked word, not a misheard one."""
    import word_coverage as WC
    loose = lambda s: re.sub(r"[23Awyh7]", "", s)
    k = loose(WC.skel_ar(word))
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9']{2,}", text or ""):
        if _dist1(loose(WC.skel_lat(tok)), k) and k:
            return tok
    return None


def grade(ver, key):
    """Grade one version of the lesson against the answer key."""
    import word_coverage as WC
    errs, tracked = [], 0
    for w in key["words"]:
        i = w["i"]
        vtext, ktext = ver["lines"].get(i), key["lines"].get(i, "")
        mine = [x for x in ver["words"] if x["i"] == w["i"]]
        if vtext != ktext:
            have = [t["ar"] for t in WC.word_tokens(vtext or "")]
            if not any(WC.similar(x, w["word"]) or WC.core(x) == WC.core(w["word"]) for x in have):
                lat = latin_unread(vtext, w["word"])
                if lat:
                    errs.append({"type": "untracked", "t": w["t"], "word": w["word"], "was": "no mark (written in Latin "
                                 "letters the reader did not read: %s)" % lat, "is": w["cat"], "why": w["why"]})
                    continue
                errs.append({"type": "misheard", "t": w["t"], "word": w["word"], "was": (vtext or "")[:80], "is": ktext[:80]})
                continue
        m = next((x for x in mine if WC.core(x["word"]) == WC.core(w["word"])), None) or next(
            (x for x in mine if WC.similar(x["word"], w["word"])), None)
        got = m["cat"] if m else None
        if got == w["cat"]:
            tracked += 1
            continue
        if "slip" in (got, w["cat"]):
            continue                                  # counted once, on the ✗ chips below
        errs.append({"type": "untracked", "t": w["t"], "word": w["word"], "was": got or "no mark", "is": w["cat"],
                     "why": w["why"]})
    for s in key["slips"]:
        if not any(_same_slip(s, x) for x in ver["slips"]):
            errs.append({"type": "missed_slip", "t": s["t"], "word": s["said"] or s["ar"], "was": "no mistake marked",
                         "is": "%s %s%s" % (s["k"], s.get("rule") or "", (" → " + s["ar"]) if s["ar"] else "")})
    for s in ver["slips"]:
        if not any(_same_slip(s, x) for x in key["slips"]):
            errs.append({"type": "fake_slip", "t": s["t"], "word": s["said"] or s["ar"],
                         "was": "%s %s%s" % (s["k"], s.get("rule") or "", (" → " + s["ar"]) if s["ar"] else ""),
                         "is": "not a mistake"})
    n = len(key["words"])
    by = {t: sum(1 for e in errs if e["type"] == t) for t in TYPES}
    errs.sort(key=lambda e: (WC._sec(e["t"]), e["type"]))
    return {"words": n, "tracked": tracked, "tracked_pct": round(100.0 * tracked / n, 1) if n else None,
            "mistakes": by, "mistakes_total": len(errs),
            "per_100": round(100.0 * len(errs) / n, 1) if n else None, "list": errs}


def snap_path(date):
    return os.path.join(DIR, date + ".json")


def first_path(date):
    return os.path.join(DIR, date + ".first.json")


def first_publish(date):
    """(page, sha) of the lesson's first publish (the hourly auto-freeze), or (None, None)."""
    f = J(first_path(date))
    if isinstance(f, dict) and isinstance(f.get("page"), dict) and f.get("sha"):
        return f["page"], f["sha"]
    return None, None


# ------------------------------------------------------------------ fast review mode: minutes + coverage (PG-50)

CORR_P = os.path.join(REPO, "data", "lesson-work", "medi-corrections.json")
PICK_DIR = os.path.join(REPO, "docs", "data", "review-pick")


def _payload(r):
    return r.get("payload") if isinstance(r.get("payload"), dict) else {}


def is_fast(r):
    return _payload(r).get("review_mode") == "fast" or (r.get("kind") == "rule-answer" and r.get("proposal") == "review:fast")


def fast_rows(rows=None):
    """{date: [fast-mode rows]} from the corrections mirror (an undone row still took his time: it counts)."""
    if rows is None:
        rows = (J(CORR_P, {}) or {}).get("rows") or []
    out = {}
    for r in rows:
        if isinstance(r, dict) and r.get("lesson_date") and is_fast(r):
            out.setdefault(str(r["lesson_date"]), []).append(r)
    return out


def minutes_of(rows):
    if not rows:
        return None
    secs = 0.0
    for r in rows:
        try:
            secs += float(_payload(r).get("secs") or 0)
        except (TypeError, ValueError):
            pass
    return round(secs / 60.0, 1)


def his_lines(date, repo=REPO, page=None, pick_dir=None):
    """[(start, end)] of his Arabic lines: the review picker's lines when built, else his page lines with Arabic."""
    pick = J(os.path.join(pick_dir or os.path.join(repo, "docs", "data", "review-pick"), date + ".json"))
    if isinstance(pick, dict) and isinstance(pick.get("lines"), list):
        return [(float(x["t"]), float(x.get("end") or x["t"])) for x in pick["lines"] if x.get("t") is not None]
    import word_coverage as WC
    d = page if page is not None else page_at(None, date, repo)
    return [(float(u["t"]), float(u["t"])) for u in d.get("turns") or []
            if u.get("who") == "Medi" and WC.word_tokens(u.get("text") or "")]


def row_t(r):
    p = _payload(r)
    for v in (r.get("turn_t"), p.get("t"), p.get("turn_t")):
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def coverage_of(lines, rows):
    """(checked, total): his lines with at least one row whose time falls inside the line (0.6 s slack, the review mode's own)."""
    ts = [t for t in (row_t(r) for r in rows or []) if t is not None]
    return sum(1 for a, b in lines if any(a - 0.6 <= t <= b + 0.6 for t in ts)), len(lines)


def freeze(date, repo=REPO, log=print, rv=None):
    rv = rv or next((r for r in J(REVIEWS_P, {}).get("reviews", []) if r["date"] == date), None)
    first, first_sha = first_publish(date)            # protocol §2.1: the page as first published, frozen at that publish
    if not rv and first is not None and date in fast_rows():
        rv = {"date": date, "full": True, "before_commit": None, "key_commit": None}   # a fast review lists itself
    if not rv or not rv.get("full"):
        raise SystemExit("%s is not a full review in %s" % (date, REVIEWS_P))
    if first is None and not rv.get("before_commit"):
        raise SystemExit("%s has no first-publish freeze and no before_commit" % date)
    if first is not None:
        before, before_commit, src = first, first_sha, "the first publish, %s.first.json" % date
    else:
        before, before_commit, src = page_at(rv["before_commit"], date, repo), rv["before_commit"], "git"
    key = page_at(rv.get("key_commit"), date, repo)
    W(snap_path(date), {"about": "Frozen exam for the grade book (PG-46, scripts/review_grades.py). before = the pipeline's "
                        "page at %s (from %s); key = the page after Medi's review at %s. Re-freeze only on purpose." %
                        (before_commit, src, rv.get("key_commit") or "the working tree"),
                        "date": date, "before_commit": before_commit, "key_commit": rv.get("key_commit"),
                        "before": snapshot(before, date), "key": snapshot(key, date)})
    log("froze %s" % date)


def arabizi_of(repo=REPO):
    """Arabic word -> her spelling (RULES.md S1: her Doc, then arabizi-extra); a word with neither stays Arabic."""
    import word_coverage as WC
    m = {WC.jsnorm(k): v["latin"] for k, v in WC.EXTRA.items() if v.get("latin")}
    for it in (J(os.path.join(repo, "docs", "data", "words.json"), {}) or {}).get("items") or []:
        if it.get("arabic") and it.get("arabizi"):
            m[WC.jsnorm(it["arabic"])] = it.get("house_spelling") or it["arabizi"]
    return m


def tutor_check(date, his_rows, repo=REPO, tutor_rows=None):
    """AM-29 (Medi 2026-10-11 "mix 30-20"): the tutor's blind key check of an exam lesson against the student's fast-review
    answer on the same line -> {answered, agree_with_student_n, compared_n, agreement_pct, total}, or None when the lesson
    has no key check. A measurement only: it never changes a page or a grade."""
    import build_tutor_key_check as TK
    key = J(TK.key_path(date, repo))
    if not key or not key.get("items"):
        return None
    if tutor_rows is None:
        tutor_rows = (J(os.path.join(repo, "data", "lesson-work", "review-grades", "tutor-check-answers.json"), {}) or {}).get("rows") or []
    return TK.agreement(key["items"], tutor_rows, his_rows)


def build(repo=REPO, corrections=None, reviews=None, pick_dir=None, tutor_rows=None):
    reviews = [dict(r) for r in (reviews if reviews is not None else J(REVIEWS_P, {}).get("reviews", []))]
    fast = fast_rows(corrections)                      # minutes: every fast row (an undone answer still took his time)
    try:                                               # coverage: only answers still standing (an undo takes one back)
        import medi_corrections as MC
        allrows = corrections if corrections is not None else (J(CORR_P, {}) or {}).get("rows") or []
        live = fast_rows(MC.effective([r for r in allrows if isinstance(r, dict) and r.get("id")]))
    except Exception:
        live = fast
    listed = {r["date"] for r in reviews}
    for d in sorted(set(fast) - listed):                # a fast review lists itself (its rows say it happened)
        reviews.append({"date": d, "full": True, "note": "fast review mode (PG-50)"})
    reviews.sort(key=lambda r: r["date"])
    rows = []
    for rv in reviews:
        row = {"date": rv["date"], "full": bool(rv.get("full")), "note": rv.get("note") or "",
               "minutes_medi": minutes_of(fast.get(rv["date"])), "coverage_medi": None, "exam": bool(rv.get("exam"))}
        if rv["date"] in fast:
            n, m = coverage_of(his_lines(rv["date"], repo, pick_dir=pick_dir), live.get(rv["date"]) or [])
            row.update({"coverage_medi": round(float(n) / m, 3) if m else None, "lines_checked": n, "lines_total": m})
            if not m or n < m:
                row["full"] = False
                row["status"] = "partial review, not graded (%d of %d lines)" % (n, m)
                rows.append(row)
                continue
        if rv.get("full"):
            snap = J(snap_path(rv["date"]))
            if not snap and rv["date"] in fast and first_publish(rv["date"])[0] is not None:
                # a fast review that reached every line freezes its own key (Codex review 2026-10-11): before = the first
                # publish, key = today's page with his rows applied; an audit after it is re-frozen on purpose (freeze)
                try:
                    freeze(rv["date"], repo, log=lambda *a: None,
                           rv={"date": rv["date"], "full": True, "before_commit": None, "key_commit": None})
                    snap = J(snap_path(rv["date"]))
                except SystemExit:
                    snap = None
            if not snap:
                row["status"] = "exam: review in progress" if rv.get("exam") else "no answer key frozen yet"
            else:
                now = snapshot(page_at(None, rv["date"], repo), rv["date"])
                row.update({"status": "graded", "before_commit": snap["before_commit"], "key_commit": snap["key_commit"],
                            "before": grade(snap["before"], snap["key"]), "now": grade(now, snap["key"])})
        else:
            row["status"] = "partial review, not graded"
        rows.append(row)
    for r in rows:                                       # AM-29: the tutor's key check, next to his own answers
        try:
            ac = tutor_check(r["date"], live.get(r["date"]) or [], repo, tutor_rows)
        except Exception:  # noqa: BLE001 - the grade book never waits on it
            ac = None
        if ac is not None:
            r["amal_check"] = ac
    import word_coverage as WC
    az = arabizi_of(repo)
    for r in rows:
        for side in ("before", "now"):
            for e in (r.get(side) or {}).get("list", []):
                e["az"] = " ".join(az.get(WC.jsnorm(x), x) for x in str(e["word"]).split())
    graded = [r for r in rows if r.get("status") == "graded"]
    trend = [{"date": r["date"], "tracked_pct": r["before"]["tracked_pct"], "per_100": r["before"]["per_100"]} for r in graded]
    return {"about": "Grade book (PG-46): the pipeline's first version of each lesson Medi reviewed in full, graded "
                     "against his review (the answer key); Arabic words of his lines only. 'now' is shown as drift: today's "
                     "page vs the key, a regression check only, never an accuracy score. minutes_medi / coverage_medi: his "
                     "fast-review minutes and the share of his Arabic lines he answered in fast mode (null = no fast "
                     "review). amal_check (AM-29): the tutor's blind check of the exam's moments - how many she answered and on how many lines her answer and his fast-review key (1 right, 2 wrong word, 3 mistake) say the same; a measurement only. Built by scripts/review_grades.py.",
            "types": TYPES, "lessons": rows, "trend": trend}


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] == ["freeze"]:
        freeze(argv[1])
        argv = []
    out = build()
    if "--check" in argv:
        old = J(OUT_P)
        # an exam whose review is still going (PR-23: the key freezes itself at full coverage) is not a missing key
        bad = [r["date"] for r in out["lessons"] if r["full"] and r["status"] != "graded" and not r.get("exam")]
        if bad:
            print("review_grades: full review with no frozen answer key: " + ", ".join(bad))
            return 1
        if old != out:
            print("review_grades: docs/data/review-grades.json is stale - run python scripts/review_grades.py")
            return 1
        print("review_grades: OK (%d graded)" % len(out["trend"]))
        return 0
    W(OUT_P, out)
    for r in out["lessons"]:
        if r.get("status") == "graded":
            b, n = r["before"], r["now"]
            print("%s  before: %s%% tracked, %d mistakes (%s / 100 words)  drift: %s%%, %d" % (
                r["date"], b["tracked_pct"], b["mistakes_total"], b["per_100"], n["tracked_pct"], n["mistakes_total"]))
            print("    by type before: %s" % b["mistakes"])
        else:
            print("%s  %s" % (r["date"], r["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
