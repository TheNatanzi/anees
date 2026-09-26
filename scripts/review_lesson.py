# -*- coding: utf-8 -*-
"""Step 8 of the full audit: same-day review of ONE new lesson, the same loop as the 13-lesson backfill.

    python scripts/review_lesson.py 2026-09-23              # full run: readers -> compare -> third reader -> pages -> Amal's items
    python scripts/review_lesson.py 2026-09-23 --dry-run    # reuse reader files that already exist, run no claude, no git
    python scripts/review_lesson.py 2026-09-23 --no-push    # everything but the push

Steps (each idempotent - an existing output file is reused, so a crash resumes where it stopped):
  1 prep      docs/data/lessons/<date>.json -> data/lesson-work/full-audit/<date>.txt (needs build_lessons_page_data first)
  2 readers   two independent `claude -p` runs (READER-BRIEF.md) -> <date>.r1.json / <date>.r2.json   (parallel)
  3 compare   scripts/full_audit_compare.py compare -> <date>.compare.json + <date>.disputes.md
  4 third     one `claude -p` run (THIRD-READER-BRIEF.md) -> <date>.r3.json ; settle -> <date>.settled.json
  5 build     scripts/full_audit_build.py (all lessons) -> data/full-audit-2026-09-26.json + plan/FULL-AUDIT-2026-09-26.md
  6 pages     build_lessons_page_data.py, build_grammar_console.py, build_amal_grammar_rules.py, arabizi_everywhere.py
  7 Amal      `claude -p` pattern reader for this lesson's B rows (PATTERN-BRIEF.md, appends to patterns.json)
              -> build_amal_review.py -> amal_review_link.py (refreshes her hub payload) -> prints the hub link
  8 git       commit + push (unless --no-push / --dry-run)
Never sends anything to Amal. Never re-transcribes. `claude` = the Claude Code CLI on PATH (2.1+).
"""
import argparse, datetime, json, os, subprocess, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
LOG = os.path.join(WORK, "review_lesson.log")
CLAUDE = os.environ.get("ANEES_CLAUDE", "claude")


def log(*a):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def py(*args, check=True):
    return subprocess.run([sys.executable, *args], cwd=REPO, check=check, env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def claude(prompt, label, timeout=3600):
    """One headless reader. The prompt says which file to write; we only check that it appeared."""
    log("claude start", label)
    cmd = [CLAUDE, "-p", prompt, "--output-format", "text", "--permission-mode", "bypassPermissions", "--add-dir", REPO]
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        log("claude done", label, (r.stdout or "").strip()[-200:].replace("\n", " "))
        if r.returncode:
            log("claude stderr", label, (r.stderr or "")[-400:])
    except Exception as e:
        log("claude failed", label, e)


def reader_prompt(date, reader, tag=""):
    return (f"Repo: {REPO}. Read {WORK}\\READER-BRIEF.md first and follow it exactly. You are reader {reader} for lesson {date}. "
            f"Transcript: data/lesson-work/full-audit/{date}.txt. Read the WHOLE file in order. Write your JSON to "
            f"{WORK}\\{date}{tag}.{reader}.json (reader \"{reader}\"). Do not open any other reader's file, the grammar-sweep JSON, "
            f"or the sweep plan. Reply with only your counts line.")


def third_prompt(date, tag=""):
    return (f"Repo: {REPO}. Read {WORK}\\THIRD-READER-BRIEF.md and follow it exactly. You are the third reader for lesson {date}. "
            f"Disputes: data/lesson-work/full-audit/{date}{tag}.disputes.md. Transcript: data/lesson-work/full-audit/{date}.txt. "
            f"Write your JSON to {WORK}\\{date}{tag}.r3.json. Reply with one line: kept n, dropped n, added n.")


def pattern_prompt(date):
    return (f"Repo: {REPO}. Read {WORK}\\PATTERN-BRIEF.md and follow it exactly, with ONE change: only the B rows of lesson {date} "
            f"(rows in data/full-audit-2026-09-26.json with date {date} and kind vocab-B or grammar-B). First read the existing "
            f"{WORK}\\patterns.json: if a row fits one of its patterns, add the row's uid to that pattern's rows; otherwise add a "
            f"new pattern. Write the whole updated file back to {WORK}\\patterns.json (keep every existing pattern and row). "
            f"Reply with one line: n rows placed, n new patterns.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--dry-run", action="store_true", help="reuse existing reader files, never call claude, no git")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    d = a.date
    os.makedirs(WORK, exist_ok=True)
    f = lambda name: os.path.join(WORK, f"{d}{name}")
    log("=== review_lesson", d, "dry-run" if a.dry_run else "")
    # 1 prep (one lesson): reuse full_audit_prep's dump for this date only
    if not os.path.exists(f(".txt")):
        sys.path.insert(0, HERE)
        import full_audit_prep as P
        P.DATES = [d]
        P.main()
    # 2 readers
    jobs = [(r, f(f".{r}.json")) for r in ("r1", "r2") if not os.path.exists(f(f".{r}.json"))]
    if jobs and a.dry_run:
        log("dry-run: reader files missing, stopping:", [j[1] for j in jobs]); return 2
    ts = [threading.Thread(target=claude, args=(reader_prompt(d, r), f"{d} {r}")) for r, _ in jobs]
    [t.start() for t in ts]; [t.join() for t in ts]
    if not all(os.path.exists(f(f".{r}.json")) for r in ("r1", "r2")):
        log("a reader wrote nothing; stopping"); return 1
    # 3 compare
    py(os.path.join(HERE, "full_audit_compare.py"), "compare", d)
    # 4 third reader + settle
    if not os.path.exists(f(".r3.json")):
        if a.dry_run:
            log("dry-run: r3 missing, stopping"); return 2
        claude(third_prompt(d), f"{d} r3")
    if not os.path.exists(f(".r3.json")):
        log("third reader wrote nothing; stopping"); return 1
    py(os.path.join(HERE, "full_audit_compare.py"), "settle", d)
    # 5 build the audit (all lessons) + 6 pages
    py(os.path.join(HERE, "full_audit_build.py"))
    for s in ("build_lessons_page_data.py", "build_grammar_console.py", "build_amal_grammar_rules.py", "arabizi_everywhere.py"):
        py(os.path.join(HERE, s), check=False)
    # 7 Amal's items: patterns for this lesson's B rows -> review data -> hub link refreshed
    A = json.load(open(os.path.join(REPO, "data", "full-audit-2026-09-26.json"), encoding="utf-8"))
    b_rows = [r["uid"] for r in A["rows"] if r["date"] == d and r.get("kind") in ("vocab-B", "grammar-B")]
    pats = json.load(open(os.path.join(WORK, "patterns.json"), encoding="utf-8")) if os.path.exists(os.path.join(WORK, "patterns.json")) else {"patterns": []}
    placed = {u for p in pats["patterns"] for u in p.get("rows", [])}
    if [u for u in b_rows if u not in placed]:
        if a.dry_run:
            log("dry-run: %d B rows of %s not yet in patterns.json; they would be grouped by claude, then shown as one-row patterns until then" % (len([u for u in b_rows if u not in placed]), d))
        else:
            claude(pattern_prompt(d), f"{d} patterns")
    py(os.path.join(HERE, "build_amal_review.py"), check=False)
    link = None
    if not a.dry_run:
        r = subprocess.run([sys.executable, os.path.join(HERE, "amal_review_link.py")], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
        link = next((l.split(None, 1)[1] for l in (r.stdout or "").splitlines() if l.startswith("HUB")), None)
        log("hub link", link)
    # 8 git
    if not a.dry_run:
        subprocess.run(["git", "add", "-A", "data/full-audit-2026-09-26.json", "plan/FULL-AUDIT-2026-09-26.md", "docs", "data/lesson-work/full-audit"], cwd=REPO)
        subprocess.run(["git", "commit", "-q", "-m", f"Same-day review {d}: two readers + third reader, pages fed, Amal's items\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"], cwd=REPO)
        if not a.no_push:
            subprocess.run(["git", "push", "-q", "origin", "HEAD:master"], cwd=REPO)
    S = json.load(open(f(".settled.json"), encoding="utf-8"))["counts"]
    log("DONE", d, "rows", S.get("final"), "agreement", S.get("agreement_pct"), "B rows for Amal", len(b_rows), "hub", link or "(dry-run: not minted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
