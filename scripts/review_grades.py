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
  now    = today's published page, graded against the same key (a rebuild that breaks his fixes shows here)
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


def freeze(date, repo=REPO, log=print):
    rv = next((r for r in J(REVIEWS_P, {}).get("reviews", []) if r["date"] == date), None)
    if not rv or not rv.get("full"):
        raise SystemExit("%s is not a full review in %s" % (date, REVIEWS_P))
    before, key = page_at(rv["before_commit"], date, repo), page_at(rv.get("key_commit"), date, repo)
    W(snap_path(date), {"about": "Frozen exam for the grade book (PG-46, scripts/review_grades.py). before = the pipeline's "
                        "page at %s; key = the page after Medi's review at %s. Re-freeze only on purpose." %
                        (rv["before_commit"], rv.get("key_commit") or "the working tree"),
                        "date": date, "before_commit": rv["before_commit"], "key_commit": rv.get("key_commit"),
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


def build(repo=REPO):
    reviews = sorted(J(REVIEWS_P, {}).get("reviews", []), key=lambda r: r["date"])
    rows = []
    for rv in reviews:
        row = {"date": rv["date"], "full": bool(rv.get("full")), "note": rv.get("note") or ""}
        if rv.get("full"):
            snap = J(snap_path(rv["date"]))
            if not snap:
                row["status"] = "no answer key frozen yet"
            else:
                now = snapshot(page_at(None, rv["date"], repo), rv["date"])
                row.update({"status": "graded", "before_commit": snap["before_commit"], "key_commit": snap["key_commit"],
                            "before": grade(snap["before"], snap["key"]), "now": grade(now, snap["key"])})
        else:
            row["status"] = "partial review, not graded"
        rows.append(row)
    import word_coverage as WC
    az = arabizi_of(repo)
    for r in rows:
        for side in ("before", "now"):
            for e in (r.get(side) or {}).get("list", []):
                e["az"] = " ".join(az.get(WC.jsnorm(x), x) for x in str(e["word"]).split())
    graded = [r for r in rows if r.get("status") == "graded"]
    trend = [{"date": r["date"], "tracked_pct": r["before"]["tracked_pct"], "per_100": r["before"]["per_100"]} for r in graded]
    return {"about": "Grade book (PG-46): the pipeline's first version of each lesson Medi reviewed in full, graded "
                     "against his review (the answer key); Arabic words of his lines only. Built by scripts/review_grades.py.",
            "types": TYPES, "lessons": rows, "trend": trend}


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] == ["freeze"]:
        freeze(argv[1])
        argv = []
    out = build()
    if "--check" in argv:
        old = J(OUT_P)
        bad = [r["date"] for r in out["lessons"] if r["full"] and r["status"] != "graded"]
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
            print("%s  before: %s%% tracked, %d mistakes (%s / 100 words)  now: %s%%, %d" % (
                r["date"], b["tracked_pct"], b["mistakes_total"], b["per_100"], n["tracked_pct"], n["mistakes_total"]))
            print("    by type before: %s" % b["mistakes"])
        else:
            print("%s  %s" % (r["date"], r["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
