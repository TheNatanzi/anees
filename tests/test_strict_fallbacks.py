"""Eng audit 2026-09-29 (area 4): build_lessons_page_data._confirmed_new silently fell back to a hard-coded 09-25 list
when the database call failed. The hourly job now sets ANEES_STRICT=1, and then the failure must surface."""
import ast, os, sys, types
from pathlib import Path
import pytest

SRC = Path(__file__).resolve().parents[1] / "scripts" / "build_lessons_page_data.py"


def _load_fn():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_confirmed_new")
    ns = {"os": os, "sys": sys}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SRC), "exec"), ns)
    return ns["_confirmed_new"]


def test_strict_mode_raises_when_the_database_fails(monkeypatch):
    bad = types.ModuleType("db")
    def select(*a, **k): raise ConnectionError("down")
    bad.select = select
    monkeypatch.setitem(sys.modules, "db", bad)
    monkeypatch.setenv("ANEES_STRICT", "1")
    with pytest.raises(ConnectionError):
        _load_fn()()


def test_offline_build_still_works_but_says_so(monkeypatch, capsys):
    bad = types.ModuleType("db")
    def select(*a, **k): raise ConnectionError("down")
    bad.select = select
    monkeypatch.setitem(sys.modules, "db", bad)
    monkeypatch.delenv("ANEES_STRICT", raising=False)
    assert _load_fn()()
    assert "database unreachable" in capsys.readouterr().err


def test_hourly_job_turns_strict_on():
    assert "setdefault('ANEES_STRICT', '1')" in (SRC.parent / "hourly_lessons.py").read_text(encoding="utf-8")
