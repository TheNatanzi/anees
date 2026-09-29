# -*- coding: utf-8 -*-
"""Remove the 108 fake flashcard answers that test runs left in Medi's LIVE card_results table on 2026-09-29
(09:14-09:57 UTC, subject sel:all:topic:Animals). Medi M2 "delete" (2026-09-29). Committed UNRUN.

    python scripts/delete_test_card_rows_2026_09_29.py            # dry run: fetch + check + write the backup, delete nothing
    python scripts/delete_test_card_rows_2026_09_29.py --apply    # the same, then delete exactly those IDs and verify

Safety: only the exact IDs frozen in data/cleanup/card-results-test-rows-2026-09-29.json. Every row must still match the
subject and time window; the count must be exactly 108; a JSON backup of the full rows is written first
(data/cleanup/card-results-test-rows-2026-09-29.backup.json). Anything unexpected -> exit 1, nothing deleted.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
IDS_P = os.path.join(REPO, "data", "cleanup", "card-results-test-rows-2026-09-29.json")
BACKUP_P = os.path.join(REPO, "data", "cleanup", "card-results-test-rows-2026-09-29.backup.json")
EXPECTED = 108


def check_rows(spec, rows):
    """Problems (list of strings) with the fetched rows against the frozen spec; [] = safe to delete."""
    ids, got = set(spec["ids"]), {r["id"]: r for r in rows}
    p = []
    if len(ids) != EXPECTED:
        p.append(f"frozen list has {len(ids)} ids, expected {EXPECTED}")
    if set(got) != ids:
        p.append(f"{len(ids - set(got))} frozen ids not found, {len(set(got) - ids)} unexpected rows")
    lo, hi = spec["window_utc"]
    for r in rows:
        if r.get("subject") != spec["subject"] or not (lo[:19] <= str(r.get("created_at"))[:19] < hi[:19]) or r.get("round_id") not in spec["round_ids"]:
            p.append(f"row {r['id']} does not match subject/window/round"); break
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args(argv)
    import db
    spec = json.load(open(IDS_P, encoding="utf-8"))
    idlist = "(" + ",".join(str(i) for i in spec["ids"]) + ")"
    rows = db.select("card_results", {"select": "*", "id": f"in.{idlist}"})
    probs = check_rows(spec, rows)
    if probs:
        print("STOP, nothing deleted:", "; ".join(probs)); return 1
    with open(BACKUP_P, "w", encoding="utf-8") as f:
        json.dump({"backed_up_from": "card_results", "rows": rows}, f, ensure_ascii=False, indent=1)
    print(f"backup: {len(rows)} rows -> {BACKUP_P}")
    if not a.apply:
        print(f"dry run: would delete {len(rows)} rows. Re-run with --apply."); return 0
    db.rest("DELETE", "card_results", params={"id": f"in.{idlist}"}, prefer="return=minimal")
    left = db.select("card_results", {"select": "id", "id": f"in.{idlist}"})
    if left:
        print(f"FAILED: {len(left)} of {EXPECTED} rows still there"); return 1
    print(f"deleted {EXPECTED} rows; 0 left; backup kept at {BACKUP_P}"); return 0


if __name__ == "__main__":
    sys.exit(main())
