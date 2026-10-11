# -*- coding: utf-8 -*-
"""PR-24: the one command that clears a stuck hourly checkout keeps everything paid for (a backup branch, the
data/lesson-work files master lacks, the run-log lines) and lands on origin/master."""
import os, shutil, subprocess, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import reset_hourly_checkout as RH  # noqa: E402


def g(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def w(root, p, text):
    p = os.path.join(root, p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(text)


def test_pr_24_reset_keeps_paid_files_and_run_lines_and_lands_on_master(tmp_path):
    if not shutil.which("git"):
        pytest.skip("git not on PATH")
    remote, a, b = str(tmp_path / "r.git"), str(tmp_path / "a"), str(tmp_path / "hourly")
    g(str(tmp_path), "init", "-q", "--bare", "-b", "master", remote)
    g(str(tmp_path), "clone", "-q", remote, a)
    for k, v in (("user.email", "t@e"), ("user.name", "t"), ("core.hooksPath", "no-hooks")):
        g(a, "config", k, v)
    w(a, "data/runs/2026-10.jsonl", '{"run": 1}\n')
    w(a, "data/budget.json", '{"calls": []}\n')
    w(a, "docs/page.json", "v1\n")
    g(a, "add", "-A"); g(a, "commit", "-qm", "base"); g(a, "push", "-q", "origin", "HEAD:master")
    g(str(tmp_path), "clone", "-q", remote, b)
    for k, v in (("user.email", "t@e"), ("user.name", "t"), ("core.hooksPath", "no-hooks")):
        g(b, "config", k, v)
    # the stuck hourly: paid files + run lines + a generated page, committed and not
    w(b, "data/lesson-work/rehear/2026-10-10/base-run1.json", "paid\n")
    w(b, "data/runs/2026-10.jsonl", '{"run": 1}\n{"run": 2}\n')
    w(b, "docs/page.json", "hourly-old\n")
    g(b, "add", "-A"); g(b, "commit", "-qm", "hourly local")
    w(b, "data/lesson-work/full-audit/2026-10-10.r1.json", "reader\n")          # uncommitted
    # master moves on meanwhile (and has the page newer)
    w(a, "docs/page.json", "v2\n"); w(a, "data/runs/2026-10.jsonl", '{"run": 1}\n{"run": 3}\n')
    g(a, "add", "-A"); g(a, "commit", "-qm", "master newer"); g(a, "push", "-q", "origin", "HEAD:master")
    assert RH.main(["x", b, "--dry-run"]) == 0
    assert open(os.path.join(b, "docs/page.json"), encoding="utf-8").read() == "hourly-old\n"   # dry run: nothing changed
    assert RH.main(["x", b]) == 0
    assert open(os.path.join(b, "docs/page.json"), encoding="utf-8").read() == "v2\n"           # master's generated page
    assert open(os.path.join(b, "data/lesson-work/rehear/2026-10-10/base-run1.json"), encoding="utf-8").read() == "paid\n"
    assert os.path.exists(os.path.join(b, "data/lesson-work/full-audit/2026-10-10.r1.json"))   # the uncommitted file too
    runs = open(os.path.join(b, "data/runs/2026-10.jsonl"), encoding="utf-8").read().splitlines()
    assert runs == ['{"run": 1}', '{"run": 3}', '{"run": 2}']                                   # master's + the backup's
    branches = g(b, "branch", "--list", "hourly-backup-*")
    assert "hourly-backup-" in branches                                                          # everything kept
    assert g(b, "merge-base", "--is-ancestor", "origin/master", "HEAD") == ""                    # on master (+ one commit)
    assert g(b, "status", "--porcelain") == ""
