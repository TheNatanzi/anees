# -*- coding: utf-8 -*-
"""Eng audit 2026-09-29 (area 1/2): one slip must never be counted twice.

Root cause found: full_audit_compare.union_rows() let a pass-2 row that repeats a pass-1 row (same moment, same wrong
piece, same rule) through as a "pass-2 only" extra whenever pass 1 had already been paired with ANOTHER pass-2 row at
that moment; full_audit_build.py then saw two rows with the same stable uid (date + second + wrong piece + kind) and
renamed the second one "<uid>x" instead of merging it. Result: 8 slips counted twice (e.g. 09-15 1:02:41 A1 Asayam =
FA-950701c8 + FA-950701c8x, whose own note says "One error").
"""
import json, os, sys
from pathlib import Path

import full_audit_compare as FC
import full_audit_build as FB

ROOT = Path(__file__).resolve().parent.parent


def _row(t, wrong, right, bucket="A1", kind="grammar", conf="high", fid=None):
    return {"t": t, "t_amal": None, "wrong": wrong, "right": right, "kind": kind, "bucket": bucket,
            "confidence": conf, "fid": fid}


def test_union_rows_does_not_add_a_pass2_repeat_of_a_pass1_row(tmp_path, monkeypatch):
    d = "2026-01-01"
    p1 = {"rows": [_row("1:02:41", "Asayam", "el-asmaa2", fid="p1-1")], "counts": {"final": 1}}
    # pass 2 found the same slip twice (two readers picked different lines of one moment)
    p2 = {"rows": [_row("1:02:41", "Asayam", "el-asmaa2", fid="p2-1"),
                   _row("1:02:41", "Asayam", "الأسماء (el-asmaa2)", conf="medium", fid="p2-2")], "counts": {"final": 2}}
    (tmp_path / f"{d}.settled.json").write_text(json.dumps(p1), encoding="utf-8")
    (tmp_path / f"{d}.p2.settled.json").write_text(json.dumps(p2), encoding="utf-8")
    monkeypatch.setattr(FC, "WORK", str(tmp_path))
    out = FC.union_rows(d)
    assert len(out["rows"]) == 1, [r["fid"] for r in out["rows"]]
    assert out["rows"][0]["passes"] == [1, 2]


def test_union_rows_keeps_a_different_rule_at_the_same_moment(tmp_path, monkeypatch):
    d = "2026-01-02"
    p1 = {"rows": [_row("32:18", "آخر الواحدة", "آخر واحد", bucket="A1")], "counts": {"final": 1}}
    p2 = {"rows": [_row("32:18", "آخر الواحدة", "آخر واحد", bucket="A1"),
                   _row("32:18", "آخر واحدة", "آخر واحد", bucket="A8")], "counts": {"final": 2}}
    (tmp_path / f"{d}.settled.json").write_text(json.dumps(p1), encoding="utf-8")
    (tmp_path / f"{d}.p2.settled.json").write_text(json.dumps(p2), encoding="utf-8")
    monkeypatch.setattr(FC, "WORK", str(tmp_path))
    out = FC.union_rows(d)
    assert sorted(r["bucket"] for r in out["rows"]) == ["A1", "A8"]


def test_same_uid_twice_is_one_slip():
    rows = [dict(date="2026-09-15", t="1:02:41", wrong="Asayam", kind="grammar", bucket="A1", passes=[1, 2]),
            dict(date="2026-09-15", t="1:02:41", wrong="Asayam", kind="grammar", bucket="A1", passes=[2])]
    FB.assign_uids(rows)
    FB.mark_duplicates(rows, hand=[])
    counted = [r for r in rows if r["kind"] == "grammar"]
    assert len(counted) == 1
    dup = next(r for r in rows if r["kind"] == "rejected")
    assert dup["duplicate_of"] == counted[0]["uid"]
    assert counted[0]["passes"] == [1, 2]


def test_published_audit_has_no_double_counted_slip():
    """The built file: no two counted rows share a lesson, second, wrong piece and kind (the uid base)."""
    a = json.load(open(ROOT / "data" / "full-audit-2026-09-26.json", encoding="utf-8"))
    counted = [r for r in a["rows"] if r["kind"] in ("grammar", "grammar-B", "vocab-A", "vocab-B")]
    seen, dups = {}, []
    for r in counted:
        k = FB.uid_base(r)
        if k in seen:
            dups.append((seen[k], r["uid"]))
        seen[k] = r["uid"]
    assert not dups, dups
    assert not [r["uid"] for r in counted if r["uid"].endswith("x")]
