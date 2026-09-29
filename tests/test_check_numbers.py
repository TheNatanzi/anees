# -*- coding: utf-8 -*-
"""Eng audit 2026-09-29: scripts/check_numbers.py is the publish guard's math check.
It must FAIL on the data as it was (commit 3c2835c: double-counted slip, two grammar formulas, Word Bank without the
audit's word slips, no "≈") and pass on data built by this branch's builders. Offline, one summary line, < 60 s."""
import os, subprocess, sys, tarfile, io, time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
BEFORE = "3c2835c"


def _run(*args):
    t = time.time()
    p = subprocess.run([PY, str(ROOT / "scripts" / "check_numbers.py"), *args], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120)
    return p, time.time() - t


def test_fails_on_the_data_before_the_audit(tmp_path):
    try:
        blob = subprocess.run(["git", "-C", str(ROOT), "archive", BEFORE, "docs/data", "docs/js", "data/full-audit-2026-09-26.json"],
                              capture_output=True, check=True, timeout=120).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("git history for " + BEFORE + " not available")
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(tmp_path)
    p, _ = _run("--repo", str(tmp_path))
    lines = p.stdout.strip().splitlines()
    assert p.returncode == 1, p.stdout + p.stderr
    assert len(lines) == 1 and lines[0].startswith("numbers: FAIL "), lines
    assert "counted twice" in lines[0]


def test_passes_on_this_checkout_once_rebuilt():
    """Needs the data rebuilt by this branch (build_grammar_console.py then build_lessons_page_data.py)."""
    p, secs = _run()
    lines = p.stdout.strip().splitlines()
    assert len(lines) == 1, lines
    assert p.returncode == 0 and lines[0].startswith("numbers: OK "), lines[0] + "  (rebuild: python scripts/full_audit_build.py && python scripts/build_grammar_console.py && python scripts/build_lessons_page_data.py)"
    assert secs < 60
