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


def _ruling(r):
    if r.get("source") == "review":
        return r.get("kind") in ("audit_confirm", "audit_skip")
    # after-lesson taps on audit rows (scripts/after_from_audit.py): Right = not an error, Wrong = confirmed, Not Medi = drop
    return r.get("source") == "after" and bool((r.get("payload") or {}).get("audit_uid")) and r.get("kind") in ("right", "wrong", "not_medi")


def load_all():
    """-> (rulings that count, [(undone tap, its undo row)]). AM-17: the raw history is read (undo rows included) and the
    latest action per item wins (scripts/amal_undo.py), so a confirmed-then-undone slip stops counting."""
    import db, amal_undo
    raw = [dict(r, source=r.get("source") or "review") for r in db.select("amal_rules", {"select": "*", "source": "eq.review", "order": "created_at.asc"}, undo=False)]
    raw += [dict(r, source=r.get("source") or "after") for r in db.select("amal_rules", {"select": "*", "source": "eq.after", "order": "created_at.asc"}, undo=False)]
    res = amal_undo.resolve(raw)
    kept = [r for r in res.kept if r.get("kind") != amal_undo.UNDO and _ruling(r)]
    undone = [(r, res.undone[r.get("id")]) for r in raw if r.get("kind") != amal_undo.UNDO and r.get("id") in res.undone and _ruling(r)]
    return kept, undone


def load_rulings():
    return load_all()[0]


def revert_row(r, undo_row, now):
    """AM-17: put one audit row back to how it was before an undone ruling (the ruling moves to amal_ruling_undone, kept)."""
    ar = r.pop("amal_ruling", None) or {}
    before = ar.get("before") or {}
    if before:
        for k in ("kind", "signal", "confidence"):
            if before.get(k) is None:
                r.pop(k, None)
            else:
                r[k] = before[k]
    elif r.get("kind") == "rejected" and r.get("kind_before_rejection"):
        r["kind"] = r.pop("kind_before_rejection")
    elif r.get("kind") == "dropped-by-amal":
        r["kind"] = "grammar-B" if r.get("bucket") else "vocab-B"
    elif ar.get("kind") == "confirm" and ar.get("pattern"):
        r["kind"] = {"vocab-A": "vocab-B", "grammar": "grammar-B"}.get(r.get("kind"), r.get("kind"))
        if r.get("signal") == "amal-ruling":
            r.pop("signal", None)
    if ar.get("kind") in ("drop", "skip"):
        r.pop("rejected_why", None)
        if before:
            r.pop("kind_before_rejection", None)
    r.setdefault("amal_ruling_undone", []).append({**ar, "undone_at": undo_row.get("created_at") or now, "undo_rule_id": undo_row.get("id")})


def _before(r):
    return {"kind": r.get("kind"), "signal": r.get("signal"), "confidence": r.get("confidence")}


def confirm_scored_row(r, ru, pid):
    """Council 5 / Codex 6 (2026-10-05): Amal confirmed a pattern row that the readers now score THEMSELVES (after the
    re-read she voiced the fix, so the row is grammar / vocab-A, not a B row waiting for her). Before, her tap only
    flipped B rows, so her confirmation vanished from such a row ('ruling not back': 09-23 25:24 FA-cca6494e). The row
    keeps its kind and the readers' signal (her voice); it now also carries her ruling as provenance (amal_ruling
    kind confirm, on_scored_row) - undo puts it back through "before", like any other ruling. True when recorded."""
    if not r or r.get("kind") not in ("vocab-A", "grammar") or r.get("amal_ruling"):
        return False
    r["amal_ruling"] = {"kind": "confirm", "pattern": pid, "at": ru.get("created_at"), "rule_id": ru.get("id"), "before": _before(r),
                        "on_scored_row": True}
    return True


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


def withdrawn_records(undone, ledger):
    """AM-17: an undone "check these moments" tap -> one 'withdrawn' human record (append-only). accuracy_gates.ledger_state
    lets the latest human record settle a row, and a withdrawn one settles nothing: the row waits for Amal again."""
    recs = ledger.get("records", [])
    done = {r.get("undo_rule_id") for r in recs if r.get("verdict") == "withdrawn"}
    out = []
    for tap, u in undone:
        wk = str(tap.get("word_key") or "")
        prev = next((r for r in recs if r.get("rule_id") == tap.get("id")), None)
        if not wk.startswith("verify:") or u.get("id") in done or prev is None:
            continue
        out.append({"uid": wk.split(":", 1)[1], "date": prev.get("date"), "kind": prev.get("kind"), "method": "human", "role": "human",
                    "method_detail": "Amal tapped Undo on the Tutor page", "reviewer": "Amal", "verdict": "withdrawn",
                    "confidence": "high", "reason": "Amal undid her answer", "evidence": prev.get("evidence"),
                    "at": u.get("created_at"), "rule_id": u.get("id"), "undo_rule_id": u.get("id"), "undoes_rule_id": tap.get("id"),
                    "source": "amal_rules review (Tutor page, undo)"})
        done.add(u.get("id"))
    return out


LEDGER_AMAL = os.path.join(REPO, "data", "lesson-work", "ledger-amal.json")


def ledger_answers(rows):
    """LS-12: Amal's taps on the "Which word was wrong?" cards (amal_rules source 'review', word_key 'ledger:<question id>',
    kind 'ledger_pick', payload.answer). rows = amal_rules rows with undone taps already left out (scripts/db.py, AM-17);
    the latest tap per question wins. -> the rows of data/lesson-work/ledger-amal.json (her ruling, rule LS-12)."""
    last = {}
    for r in sorted(rows or [], key=lambda r: (str(r.get("created_at") or ""), r.get("id") or 0)):
        wk = str(r.get("word_key") or "")
        if not wk.startswith("ledger:") or r.get("kind") != "ledger_pick" or str(r.get("source") or "review").startswith("test"):
            continue
        p = r.get("payload") or {}
        ans = p.get("answer")
        if ans:
            last[wk] = {"conflict": wk[len("ledger:"):], "answer": ans, "by": "amal", "at": r.get("created_at"),
                        "rule_id": r.get("id"), "rule": "LS-12",
                        # 2026-10-06: "Another word" (answer other) carries what Medi said + the right word; any answer may carry a note
                        **{k: p[k] for k in ("said", "right", "note") if p.get(k)}}
    return [last[k] for k in sorted(last)]


def write_ledger_answers(rulings, path=LEDGER_AMAL):
    """Writes ledger-amal.json; True when it changed (then the lesson data is rebuilt: her tap settles the ledger)."""
    doc = {"about": "Amal's answers on her Tutor hub 'Which word was wrong?' cards (LS-12). Generated from amal_rules by "
                    "scripts/apply_amal_audit_rulings.py every hour; never edit by hand (Undo on the hub takes one back).",
           "rulings": rulings}
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    if old == doc:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return True


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
    grp["tab"] = "words"   # her rulings say what counts as a mistake (the AI Rules page only shows System / Word groups)
    rulings, undone = load_all()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # AM-17 undo: every audit row an undone ruling touched goes back (history kept on the row), her AR rule is marked
    # undone (kept), and an undone Tutor-page check gets a 'withdrawn' ledger record (the latest human record wins)
    undone_ids = {t.get("id"): u for t, u in undone}
    reverted = 0
    for r in rows.values():
        ar = r.get("amal_ruling") or {}
        if ar.get("rule_id") in undone_ids:
            revert_row(r, undone_ids[ar["rule_id"]], now)
            reverted += 1
    for x in grp["rules"]:
        rid = str(x.get("id") or "")
        if rid.startswith("AR-") and rid[3:].isdigit() and int(rid[3:]) in undone_ids and x.get("status") != "undone":
            x["status_before_undo"], x["status"] = x.get("status"), "undone"
            x["undone_at"] = undone_ids[int(rid[3:])].get("created_at") or now
            reverted += 1
    known = {x.get("pattern") for x in grp["rules"] if x.get("status") != "undone"}
    # which taps are already applied is kept HERE (the audit JSON), not written back into her Supabase rows
    # (plan/AI-ENGINEERING-REVIEW-2026-09-27.md: stop PATCHing payload.applied). Old rows may still carry payload.applied.
    done_ids = {i for x in A.get("rulings_applied") or [] for i in x.get("rules") or []}
    changed, flipped, dropped, new_rules, confirmed_scored = [], 0, 0, 0, 0
    # Tutor-page checks of single rows go to the verification ledger, not to the pattern logic below
    L = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {"records": []}
    vrec = verify_records(rulings, rows, L) + withdrawn_records(undone, L)
    for ru in rulings:
        p = ru.get("payload") or {}
        if str(ru.get("word_key") or "").startswith("verify:"):
            if not p.get("applied") and any(v["rule_id"] == ru.get("id") for v in vrec):
                changed.append(ru["id"])
            continue
        uids = p.get("rows") or []
        # "applied" (old Supabase flag) / rulings_applied only mean it was applied ONCE; full_audit_build rewrites the
        # audit JSON without her rulings, so skip only when every row she ruled on still carries this ruling (2026-09-30)
        live = [rows[u] for u in uids if u in rows]
        # re-apply only when the build wiped it (no ruling of hers on any of its rows, none later rejected) - a newer
        # decision on a row (another ruling, a Tutor-page "right") always wins over an old one
        wiped = bool(live) and all(not r.get("amal_ruling") and r.get("kind") != "rejected" for r in live)
        if (p.get("applied") or ru.get("id") in done_ids) and not wiped:
            continue
        pid = ru.get("word_key")
        if p.get("audit_uid"):                                   # one after-lesson question = one row
            r = rows.get(p["audit_uid"])
            if r:
                b = _before(r)
                if ru["kind"] == "wrong":
                    r["confidence"] = "high"
                    r["signal"] = r.get("signal") or "amal-ruling"
                    r["amal_ruling"] = {"kind": "confirm", "at": ru.get("created_at"), "rule_id": ru.get("id"), "label": p.get("label"), "alias": p.get("alias"), "before": b}
                    flipped += 1
                else:
                    r["kind_before_rejection"] = r["kind"]
                    r["kind"] = "rejected"
                    r["rejected_why"] = "Amal tapped " + str(p.get("label")) + " on the after-lesson link " + str(ru.get("created_at"))[:10]
                    r["amal_ruling"] = {"kind": "drop", "at": ru.get("created_at"), "rule_id": ru.get("id"), "label": p.get("label"), "before": b}
                    dropped += 1
            changed.append(ru["id"])
            continue
        if ru["kind"] == "audit_confirm":
            for u in uids:
                r = rows.get(u)
                if confirm_scored_row(r, ru, pid):
                    confirmed_scored += 1
                    continue
                if not r or r.get("kind") not in ("vocab-B", "grammar-B"):
                    continue
                b = _before(r)
                r["kind"] = "vocab-A" if r["kind"] == "vocab-B" else "grammar"
                r["signal"] = "amal-ruling"
                r["confidence"] = "high"
                r["amal_ruling"] = {"kind": "confirm", "pattern": pid, "at": ru.get("created_at"), "rule_id": ru.get("id"), "before": b}
                flipped += 1
        else:
            for u in uids:
                r = rows.get(u)
                if not r or r.get("kind") not in ("vocab-B", "grammar-B"):
                    continue
                b = _before(r)
                r["kind"] = "dropped-by-amal"
                r["amal_ruling"] = {"kind": "skip", "pattern": pid, "reason": p.get("reason"), "at": ru.get("created_at"), "rule_id": ru.get("id"), "before": b}
                dropped += 1
            if pid not in known:
                grp["rules"].append({"id": f"AR-{ru.get('id')}", "kind": "amal-ruling", "pattern": pid,
                                     "rule": f"Do not correct: {p.get('pattern') or pid}", "why": p.get("reason") or "",
                                     "where": "scripts/apply_amal_audit_rulings.py marks the pattern's rows dropped; the review page never lists it again",
                                     "status": "enforced", "created": (ru.get("created_at") or now)[:10], "rows": uids})
                known.add(pid)
                new_rules += 1
        changed.append(ru["id"])
    print(f"rulings {len(rulings)} new {len(changed)} | undone {len(undone)} (put back {reverted}) | rows scored {flipped} (+{confirmed_scored} already scored, her confirmation recorded) dropped {dropped} | new rules {new_rules} | "
          f"Tutor-page checks {len(vrec)} ({sum(v['verdict'] == 'confirmed' for v in vrec)} confirmed)")
    # GR-21: a confirm must reach the copy the pages read (sweep_compat), every run - not only when a ruling is new
    import full_audit_build as FAB
    if dry:
        return
    try:      # LS-12: her "which word was wrong" taps (db.select leaves undone taps out)
        import db
        led_changed = write_ledger_answers(ledger_answers(db.select("amal_rules", {"select": "*", "source": "eq.review",
                                                                                   "word_key": "like.ledger:*", "order": "created_at.asc"})))
    except Exception as e:
        led_changed = False
        print("ledger answers not read:", type(e).__name__, str(e)[:200])
    added, removed, same = FAB.sync_compat(A)
    print(f"sweep_compat: +{added} confirmed rows, -{removed} ruled-out rows, {len(same)} same-moment twins left out {same}")
    if not changed and not added and not removed and not reverted and not vrec and not led_changed:
        return
    if vrec:
        L.setdefault("records", []).extend(vrec)
        json.dump(L, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if changed:
        A["rulings_applied"] = (A.get("rulings_applied") or []) + [{"at": now, "rules": changed}]
    # the pages read sweep_compat (built by full_audit_build.py BEFORE her rulings): a row she ruled out (Right / Not Medi /
    # a reason not to correct) must leave it too, or the lesson page keeps a card the audit no longer counts (2026-10-02,
    # 09-30 09:07 D2 FA-a0a76d00 - the publish guard caught it)
    json.dump(A, open(AUDIT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(R, open(RULES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # rebuild everything that reads the audit
    for cmd in (["build_amal_review.py"], ["build_lessons_page_data.py"], ["build_grammar_console.py"], ["build_amal_grammar_rules.py"],
                ["codex_rejudge.py", "--list"]):
        subprocess.run([sys.executable, os.path.join(HERE, cmd[0]), *cmd[1:]], cwd=REPO, check=False)


if __name__ == "__main__":
    apply(dry="--dry-run" in sys.argv)
