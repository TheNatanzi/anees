# -*- coding: utf-8 -*-
"""AM-18 (Medi 2026-10-02: "close, but I want accordians to see the results and what you are asking"): close the after-lesson
links the hourly re-review minted again for lessons Amal had already answered (2026-10-02: Oct 1, Sep 26, Sep 23).

For each lesson with an answered link, every LATER unanswered link of that lesson is closed: its answers carry over the
answer she gave on the answered link to the same moment (same audit row, or the same second of the lesson +-3 s), the
rest are marked "not asked - she had answered this lesson already", and done_at is set. Nothing is deleted and no
amal_rules row is written (her taps on the earlier link stay the answers of record). Amal is never asked anything.

    python scripts/close_reasked_after_links.py            # dry run: prints what it would do
    python scripts/close_reasked_after_links.py --apply
"""
import argparse, datetime, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amal_links  # noqa: E402

NOT_ASKED = "not asked - she had answered this lesson already"


def carry(old, new):
    """-> the answers object for the re-minted link `new`, from the answered link `old` (pure)."""
    oq, oa = (old.get("payload") or {}).get("questions") or [], ((old.get("answers") or {}).get("q") or {})
    q, map_ = {}, {}
    for i, x in enumerate((new.get("payload") or {}).get("questions") or []):
        for j, y in enumerate(oq):
            same = (x.get("audit_uid") and x.get("audit_uid") == y.get("audit_uid")) or \
                   (x.get("t") is not None and y.get("t") is not None and abs(float(x["t"]) - float(y["t"])) <= 3)
            ans = oa.get(str(j), oa.get(j))
            if same and ans:
                q[str(i)] = ans
                map_[str(i)] = j
                break
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {"q": q, "done": True, "updated": now,
            "carried_from": {"token": old["token"], "created_at": old.get("created_at"), "questions": map_, "at": now,
                             "why": "AM-18: this link was made again by the hourly re-review after Amal had answered the lesson; "
                                    "her answers on the earlier link are the answers of record"},
            "not_asked": {str(i): NOT_ASKED for i in range(len((new.get("payload") or {}).get("questions") or [])) if str(i) not in q}}


def plan(rows, now_iso=None):
    """Only links still open are closed; an old expired one is history and stays as it is."""
    now_iso = now_iso or datetime.datetime.now(datetime.timezone.utc).isoformat()
    out = []
    by = {}
    for r in rows:
        by.setdefault(r["lesson_date"], []).append(r)
    for d, L in sorted(by.items()):
        done = [r for r in L if amal_links.answered(r)]
        if not done:
            continue
        first = min(done, key=lambda r: r["created_at"])
        for r in L:
            if r["created_at"] > first["created_at"] and not amal_links.answered(r) and (r.get("expires_at") or "") > now_iso:
                src = max([x for x in done if x["created_at"] < r["created_at"]], key=lambda x: x["created_at"])
                out.append((r, src, carry(src, r)))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    import db
    rows = db.select("amal_links", {"select": "token,kind,lesson_date,created_at,expires_at,done_at,answers,payload", "kind": "eq.after", "order": "created_at.asc"})
    for r, src, ans in plan(rows):
        print(r["lesson_date"], r["token"][:8], "<-", src["token"][:8], "carried", len(ans["q"]), "not asked", len(ans["not_asked"]))
        if a.apply:
            db.rest("PATCH", "amal_links", params={"token": f"eq.{r['token']}"}, body={"answers": ans, "done_at": ans["updated"]}, prefer="return=minimal")
    print("applied" if a.apply else "dry run")


if __name__ == "__main__":
    main()
