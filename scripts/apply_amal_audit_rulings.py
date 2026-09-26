# -*- coding: utf-8 -*-
"""Morning script (step 5 of the full audit): turn Amal's answers on her review page into scored errors or rules.

  python scripts/apply_amal_audit_rulings.py            # apply every unapplied ruling, rebuild the pages that changed
  python scripts/apply_amal_audit_rulings.py --dry-run  # say what would change

Her taps land in amal_rules (source 'review'): kind 'audit_confirm' (the correction is correct) or 'audit_skip'
(a reason not to correct, payload.reason), word_key = the pattern id, payload.rows = the audit row uids.
- audit_confirm -> every row of that pattern in data/full-audit-2026-09-26.json flips from vocab-B / grammar-B to
  vocab-A / grammar-A with signal 'amal-ruling' (scored: clip, underline, % - same as her voice). Pages are rebuilt.
- audit_skip    -> the rows are marked dropped (kind 'dropped-by-amal', her reason kept) AND her reason becomes a
  rule in docs/data/ai_rules.json (kind 'amal-ruling') so the same pattern is never asked again.
Idempotent: a ruling is applied once (payload.applied stamped on the amal_rules row through the service key) and the
audit JSON carries the ruling on every row it touched; re-running changes nothing.
"""
import datetime, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
AUDIT = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
RULES = os.path.join(REPO, "docs", "data", "ai_rules.json")
REVIEW = os.path.join(REPO, "docs", "data", "amal-review.json")


def load_rulings():
    import db
    return [r for r in db.select("amal_rules", {"select": "*", "source": "eq.review", "order": "created_at.asc"})
            if r.get("kind") in ("audit_confirm", "audit_skip")]


def apply(dry=False):
    A = json.load(open(AUDIT, encoding="utf-8"))
    rows = {r["uid"]: r for r in A["rows"]}
    R = json.load(open(RULES, encoding="utf-8")) if os.path.exists(RULES) else {}
    R.setdefault("groups", [])
    grp = next((g for g in R["groups"] if g.get("title") == "Amal's rulings"), None)
    if not grp:
        grp = {"title": "Amal's rulings", "rules": []}
        R["groups"].append(grp)
    known = {x.get("pattern") for x in grp["rules"]}
    rulings = load_rulings()
    changed, flipped, dropped, new_rules = [], 0, 0, 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for ru in rulings:
        p = ru.get("payload") or {}
        if p.get("applied"):
            continue
        uids = p.get("rows") or []
        pid = ru.get("word_key")
        if ru["kind"] == "audit_confirm":
            for u in uids:
                r = rows.get(u)
                if not r or r.get("kind") not in ("vocab-B", "grammar-B"):
                    continue
                r["kind"] = "vocab-A" if r["kind"] == "vocab-B" else "grammar"
                r["signal"] = "amal-ruling"
                r["confidence"] = "high"
                r["amal_ruling"] = {"kind": "confirm", "pattern": pid, "at": ru.get("created_at"), "rule_id": ru.get("id")}
                flipped += 1
        else:
            for u in uids:
                r = rows.get(u)
                if not r or r.get("kind") not in ("vocab-B", "grammar-B"):
                    continue
                r["kind"] = "dropped-by-amal"
                r["amal_ruling"] = {"kind": "skip", "pattern": pid, "reason": p.get("reason"), "at": ru.get("created_at"), "rule_id": ru.get("id")}
                dropped += 1
            if pid not in known:
                grp["rules"].append({"id": f"AR-{ru.get('id')}", "kind": "amal-ruling", "pattern": pid,
                                     "rule": f"Do not correct: {p.get('pattern') or pid}", "why": p.get("reason") or "",
                                     "where": "scripts/apply_amal_audit_rulings.py marks the pattern's rows dropped; the review page never lists it again",
                                     "status": "enforced", "created": (ru.get("created_at") or now)[:10], "rows": uids})
                known.add(pid)
                new_rules += 1
        changed.append(ru["id"])
    print(f"rulings {len(rulings)} new {len(changed)} | rows scored {flipped} dropped {dropped} | new rules {new_rules}")
    if dry or not changed:
        return
    A["rulings_applied"] = (A.get("rulings_applied") or []) + [{"at": now, "rules": changed}]
    json.dump(A, open(AUDIT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(R, open(RULES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import db
    for rid in changed:
        ru = next(x for x in rulings if x["id"] == rid)
        db.rest("PATCH", "amal_rules", params={"id": f"eq.{rid}"}, body={"payload": {**(ru.get("payload") or {}), "applied": now}}, prefer="return=minimal")
    # rebuild everything that reads the audit
    for cmd in (["build_amal_review.py"], ["build_lessons_page_data.py"], ["build_grammar_console.py"], ["build_amal_grammar_rules.py"]):
        subprocess.run([sys.executable, os.path.join(HERE, *cmd)], cwd=REPO, check=False)


if __name__ == "__main__":
    apply(dry="--dry-run" in sys.argv)
