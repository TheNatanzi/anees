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
Idempotent: a ruling is applied once - its id is listed in the audit JSON's rulings_applied (nothing is written back to
Supabase any more, 2026-09-29); the audit JSON carries the ruling on every row it touched; re-running changes nothing.
"""
import datetime, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
AUDIT = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
RULES = os.path.join(REPO, "docs", "data", "ai_rules.json")
REVIEW = os.path.join(REPO, "docs", "data", "amal-review.json")


def load_rulings():
    import db
    rows = [r for r in db.select("amal_rules", {"select": "*", "source": "eq.review", "order": "created_at.asc"})
            if r.get("kind") in ("audit_confirm", "audit_skip")]
    # after-lesson taps on audit rows (scripts/after_from_audit.py): Right = not an error, Wrong = confirmed, Not Medi = drop
    rows += [r for r in db.select("amal_rules", {"select": "*", "source": "eq.after", "order": "created_at.asc"})
             if (r.get("payload") or {}).get("audit_uid") and r.get("kind") in ("right", "wrong", "not_medi")]
    return rows


LEDGER = os.path.join(REPO, "data", "accuracy", "verifications.json")


def verify_records(rulings, audit_rows, ledger):
    """Her answers on the Tutor page's "check these moments" list (word_key 'verify:<uid>', Medi's decision 5, 2026-09-29)
    -> new human records for the verification ledger. 'Correction is correct' = confirmed (the row is scored);
    'Reason not to correct' = rejected (dropped from every total, her reason kept). One record per tap (rule id), so
    re-running adds nothing and a later tap on the same row supersedes the earlier one."""
    have = {r.get("rule_id") for r in ledger.get("records", []) if r.get("rule_id") is not None}
    out = []
    for ru in rulings:
        wk = str(ru.get("word_key") or "")
        if not wk.startswith("verify:") or ru.get("kind") not in ("audit_confirm", "audit_skip") or ru.get("id") in have:
            continue
        uid = wk.split(":", 1)[1]
        row = audit_rows.get(uid) or {}
        p = ru.get("payload") or {}
        t = _sec(row.get("t")) if _sec(row.get("t")) is not None else _sec(row.get("t_amal"))
        ta = _sec(row.get("t_amal")) if _sec(row.get("t_amal")) is not None else t
        out.append({"uid": uid, "date": row.get("date") or p.get("date"), "kind": row.get("kind"), "method": "human", "role": "human",
                    "method_detail": "Amal on the Tutor page (listened to the moment; the two AIs had disagreed)",
                    "reviewer": "Amal", "verdict": "confirmed" if ru["kind"] == "audit_confirm" else "rejected", "confidence": "high",
                    "reason": p.get("reason") or ("Correction is correct" if ru["kind"] == "audit_confirm" else None),
                    "evidence": {"t_start": max(0.0, (t or 0) - 10), "t_end": (ta or t or 0) + 20,
                                 "quote": p.get("reason") or "Correction is correct"},
                    "at": ru.get("created_at"), "rule_id": ru.get("id"), "source": "amal_rules review (Tutor page)"})
    return out


def _sec(s):
    if s in (None, ""):
        return None
    try:
        return float(sum(float(x) * 60 ** i for i, x in enumerate(reversed(str(s).split(":")))))
    except ValueError:
        return None


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
    # which taps are already applied is kept HERE (the audit JSON), not written back into her Supabase rows
    # (plan/AI-ENGINEERING-REVIEW-2026-09-27.md: stop PATCHing payload.applied). Old rows may still carry payload.applied.
    done_ids = {i for x in A.get("rulings_applied") or [] for i in x.get("rules") or []}
    changed, flipped, dropped, new_rules = [], 0, 0, 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Tutor-page checks of single rows go to the verification ledger, not to the pattern logic below
    L = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {"records": []}
    vrec = verify_records(rulings, rows, L)
    for ru in rulings:
        p = ru.get("payload") or {}
        if str(ru.get("word_key") or "").startswith("verify:"):
            if not p.get("applied") and any(v["rule_id"] == ru.get("id") for v in vrec):
                changed.append(ru["id"])
            continue
        if p.get("applied") or ru.get("id") in done_ids:
            continue
        uids = p.get("rows") or []
        pid = ru.get("word_key")
        if p.get("audit_uid"):                                   # one after-lesson question = one row
            r = rows.get(p["audit_uid"])
            if r:
                if ru["kind"] == "wrong":
                    r["confidence"] = "high"
                    r["signal"] = r.get("signal") or "amal-ruling"
                    r["amal_ruling"] = {"kind": "confirm", "at": ru.get("created_at"), "rule_id": ru.get("id"), "label": p.get("label"), "alias": p.get("alias")}
                    flipped += 1
                else:
                    r["kind_before_rejection"] = r["kind"]
                    r["kind"] = "rejected"
                    r["rejected_why"] = "Amal tapped " + str(p.get("label")) + " on the after-lesson link " + str(ru.get("created_at"))[:10]
                    r["amal_ruling"] = {"kind": "drop", "at": ru.get("created_at"), "rule_id": ru.get("id"), "label": p.get("label")}
                    dropped += 1
            changed.append(ru["id"])
            continue
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
    print(f"rulings {len(rulings)} new {len(changed)} | rows scored {flipped} dropped {dropped} | new rules {new_rules} | "
          f"Tutor-page checks {len(vrec)} ({sum(v['verdict'] == 'confirmed' for v in vrec)} confirmed)")
    if dry or not changed:
        return
    if vrec:
        L.setdefault("records", []).extend(vrec)
        json.dump(L, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    A["rulings_applied"] = (A.get("rulings_applied") or []) + [{"at": now, "rules": changed}]
    json.dump(A, open(AUDIT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(R, open(RULES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # rebuild everything that reads the audit
    for cmd in (["build_amal_review.py"], ["build_lessons_page_data.py"], ["build_grammar_console.py"], ["build_amal_grammar_rules.py"],
                ["codex_rejudge.py", "--list"]):
        subprocess.run([sys.executable, os.path.join(HERE, cmd[0]), *cmd[1:]], cwd=REPO, check=False)


if __name__ == "__main__":
    apply(dry="--dry-run" in sys.argv)
