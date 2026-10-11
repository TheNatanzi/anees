# -*- coding: utf-8 -*-
"""Clear a stuck hourly checkout (PR-24; overnight brief 2026-10-10 section 3): bring it to origin/master WITHOUT losing
anything paid for. Medi runs it once, by hand; no code ever runs it by itself.

    git -C C:\\dev\\anees-hourly fetch origin
    git -C C:\\dev\\anees-hourly show origin/master:scripts/reset_hourly_checkout.py | python - C:\\dev\\anees-hourly

What it does, in order (stops at the first failure, nothing is deleted):
  1 commits whatever is uncommitted, then keeps ALL of it on a backup branch hourly-backup-<date>
  2 git reset --hard origin/master (the generated pages and data are dropped: the next hourly run rebuilds them)
  3 puts back every file under data/lesson-work/ that the backup has and master does not (the paid second-listen runs,
    the reader files, lesson types, new-word candidates of a lesson master never got - e.g. 2026-10-10)
  4 data/runs/*.jsonl: adds the backup's run-log lines master does not have (the money record), then rebuilds
    data/budget.json from the run logs (scripts/budget_rebuild.py)
  5 one commit; the next hourly run publishes it through the publish guard
    python scripts/reset_hourly_checkout.py <checkout> --dry-run     # says what it would do, changes nothing
"""
import datetime, os, subprocess, sys

KEEP_UNDER = "data/lesson-work/"
RUNS = "data/runs/"


def git(root, *a, check=True):
    r = subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(a), (r.stderr or r.stdout).strip()[:400]))
    return r.stdout


def files(root, ref, prefix):
    return {x for x in git(root, "ls-tree", "-r", "--name-only", ref, "--", prefix).splitlines() if x}


def plan(root, backup="HEAD", target="origin/master"):
    """(files to put back, {run log: [lines to add]}) - what the backup has that the target lacks."""
    keep = sorted(files(root, backup, KEEP_UNDER) - files(root, target, KEEP_UNDER))
    runs = {}
    for p in sorted(files(root, backup, RUNS)):
        if not p.endswith(".jsonl"):
            continue
        mine = git(root, "show", "%s:%s" % (backup, p)).splitlines()
        theirs = set(git(root, "show", "%s:%s" % (target, p), check=False).splitlines())
        add = [l for l in mine if l.strip() and l not in theirs]
        if add:
            runs[p] = add
    return keep, runs


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in argv
    root = os.path.abspath(args[0] if args else ".")
    git(root, "fetch", "origin")
    if git(root, "status", "--porcelain").strip() and not dry:
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "Hourly checkout before the reset (kept on the backup branch)")
    name = "hourly-backup-" + datetime.date.today().isoformat()
    while not dry and git(root, "branch", "--list", name).strip():
        name += "b"
    keep, runs = plan(root)
    print("backup branch: %s (everything the checkout had)" % name)
    print("files master lacks, put back: %d" % len(keep))
    for p in keep[:40]:
        print("   ", p)
    if len(keep) > 40:
        print("    ... and %d more" % (len(keep) - 40))
    print("run-log lines master lacks, added: %d" % sum(len(v) for v in runs.values()))
    if dry:
        print("dry run: nothing changed")
        return 0
    git(root, "branch", name, "HEAD")
    git(root, "reset", "-q", "--hard", "origin/master")
    for i in range(0, len(keep), 100):
        git(root, "checkout", name, "--", *keep[i:i + 100])
    for p, add in runs.items():
        path = os.path.join(root, p)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(old.rstrip("\n") + ("\n" if old.strip() else "") + "\n".join(add) + "\n")
    if os.path.exists(os.path.join(root, "scripts", "budget_rebuild.py")):
        subprocess.run([sys.executable, os.path.join(root, "scripts", "budget_rebuild.py")], cwd=root)
    git(root, "add", "-A", "--", "data/lesson-work", "data/runs", "data/budget.json")
    if git(root, "diff", "--cached", "--name-only").strip():
        git(root, "commit", "-q", "-m", "Hourly checkout reset to master; its paid outputs and run-log lines kept (%s)" % name)
    print("done: on origin/master + %d kept files; the next hourly run publishes through the guard" % len(keep))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
