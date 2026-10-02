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


def test_same_wrong_phrase_repeated_within_30_s_is_one_slip():
    """Medi 2026-10-01 (registry GR-16): عشرين سجاد at 09:49 and again 16 s later is ONE slip; at 31 s apart it is two."""
    rows = [dict(date="2026-09-30", t="09:49", wrong="عشرين سجاد", kind="grammar", bucket="E1", passes=[1]),
            dict(date="2026-09-30", t="10:05", wrong="عشرين سجاد", kind="grammar", bucket="E1", passes=[1]),
            dict(date="2026-09-30", t="10:37", wrong="عشرين سجاد", kind="grammar", bucket="E1", passes=[1])]
    FB.assign_uids(rows)
    FB.mark_duplicates(rows, hand=[])
    assert FB.REPEAT_S == 30
    assert [r["kind"] for r in rows] == ["grammar", "rejected", "grammar"]
    assert rows[1]["duplicate_of"] == rows[0]["uid"]


# ---------------------------------------------------------------- GR-18: a fix that fits no bucket is proposed, never dropped
def test_gr_18_a_correction_that_fits_no_bucket_becomes_a_proposal_not_a_drop():
    """GR-18 (Medi 2026-09-25 "if it doesnt fall into a bucket lets figure out to make one"). Planted: a reader row filed
    PROPOSE, a grammar row with no bucket, a row rejected only because no bucket fits (FA-0075 on 08-25), and a moment the
    readers already counted under D2. The first three become kind grammar-propose (listed, unscored, never in the pages'
    sweep_compat); the counted one stays counted."""
    buckets = {"A1": {}, "D2": {}}
    rows = [
        {"uid": "FA-1", "date": "2026-10-01", "t": "1:00:03", "kind": "grammar", "bucket": "PROPOSE", "wrong": "nafs ishi",
         "right": "nafs el-ishi", "proposed_rule": "nafs takes el: nafs el-ishi", "mode": "speaking"},
        {"uid": "FA-2", "date": "2026-09-21", "t": "38:10", "kind": "grammar", "bucket": None, "wrong": "بـ أطبخ",
         "right": "بالطبخ", "why": "verb after a preposition", "mode": "speaking", "source": "sweep-2026-09-24"},
        {"uid": "FA-3", "date": "2026-09-21", "t": "38:10", "kind": "grammar", "bucket": "D2", "wrong": "bi atbuk",
         "right": "bi el-tabe5", "mode": "speaking"},
        {"uid": "FA-4", "date": "2026-08-25", "t": "59:04", "kind": "rejected", "kind_before_rejection": "grammar", "bucket": "C9",
         "wrong": "عملنا كتير", "right": "عملنا تمرين كتير", "rejected_why": "plain conversation, no correction and no bucket fits"},
    ]
    hand = [{"id": "P-OBJ", "name": "a doing verb says what was done", "proposed_rule": "3amal names what was done",
             "rows": [{"date": "2026-08-25", "t": "59:04", "wrong": "عملنا كتير", "rule": "GR-18"}]}]
    P = FB.apply_proposals(rows, hand, buckets)
    kinds = {r["uid"]: r["kind"] for r in rows}
    assert kinds == {"FA-1": "grammar-propose", "FA-2": "grammar-propose", "FA-3": "grammar", "FA-4": "grammar-propose"}
    assert rows[3]["was_rejected_why"].endswith("no bucket fits") and rows[3]["proposal"] == "P-OBJ"
    ids = {p["id"]: p for p in P}
    assert set(ids) == {"P-OBJ", "P-FA-1", "P-FA-2"}
    assert ids["P-FA-1"]["proposed_rule"] == "nafs takes el: nafs el-ishi"
    assert ids["P-FA-2"]["moments"][0]["also_counted_as"] == [{"uid": "FA-3", "kind": "grammar", "bucket": "D2"}]


def test_gr_18_the_live_audit_drops_no_correction_for_no_bucket():
    """GR-18 on the committed data: no live grammar row sits outside an approved bucket (it is a proposal instead), every
    proposal is published for the Grammar Console, and no proposal row reaches the scored copy the pages read."""
    A = json.loads((ROOT / "data" / "full-audit-2026-09-26.json").read_text(encoding="utf-8"))
    buckets = {b["id"] for b in json.loads((ROOT / "docs" / "data" / "grammar-buckets.json").read_text(encoding="utf-8"))["buckets"]}
    loose = [r["uid"] for r in A["rows"] if r["kind"] in ("grammar", "grammar-B") and r.get("mode", "speaking") == "speaking"
             and r.get("bucket") not in buckets and r.get("new_bucket_group") != "NEW-B18"]
    assert not loose, loose
    prop = {r["uid"] for r in A["rows"] if r["kind"] == "grammar-propose"}
    assert not prop & {x["uid"] for x in A["sweep_compat"]["rows"]}
    pub = json.loads((ROOT / "docs" / "data" / "grammar-proposals.json").read_text(encoding="utf-8"))
    assert prop <= {m["uid"] for p in pub["proposals"] for m in p["moments"]}
