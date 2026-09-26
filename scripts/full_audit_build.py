# -*- coding: utf-8 -*-
"""Step 3 of the full audit: reconcile the settled reader rows of all 13 lessons with what already exists
(data/grammar-sweep-2026-09-24.json: 302 grammar rows + 31 unfiled + 147 vocab fixes) and write

    data/full-audit-2026-09-26.json     rows (every error, one source of truth), per-pass counts, per-lesson agreement,
                                        machine-caught / missed, sweep reconciliation
    plan/FULL-AUDIT-2026-09-26.md       per-lesson tables + totals (Medi's reading copy)

Rules: nothing the sweep verified is dropped without a stated reason (a sweep row the readers did not find is KEPT,
tagged source "sweep-2026-09-24", and listed under "sweep rows the readers missed"); everything new is added.
Vocab-B and grammar-B rows are never scored here: they go to Amal's review page (step 5).

    python scripts/full_audit_build.py
"""
import collections, datetime as dt, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from full_audit_compare import sec, same_moment, same_piece, kind_class, norm  # noqa: E402
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
OUT_JSON = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
OUT_MD = os.path.join(REPO, "plan", "FULL-AUDIT-2026-09-26.md")
DATES = ["2026-08-25", "2026-09-04", "2026-09-05", "2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15",
         "2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-21", "2026-09-23"]
NOT_COUNTED = ("rejected_on_hand_check", "pron_from_sweep")


def load_settled(date):
    """The lesson's final rows: pass-1 settled rows plus what pass 2 settled and pass 1 did not have (full_audit_compare.union_rows)."""
    from full_audit_compare import union_rows
    return union_rows(date)


def pass_log(date):
    log = []
    for pas, tag in ((1, ""), (2, ".p2")):
        c = os.path.join(WORK, f"{date}{tag}.compare.json")
        s = os.path.join(WORK, f"{date}{tag}.settled.json")
        if os.path.exists(c):
            C = json.load(open(c, encoding="utf-8"))["counts"]
            S = json.load(open(s, encoding="utf-8"))["counts"] if os.path.exists(s) else {}
            log.append({"pass": pas, **C, "r3_kept": S.get("r3_kept"), "r3_dropped": S.get("r3_dropped"), "final": S.get("final")})
    p = os.path.join(WORK, f"{date}.passes.json")
    if os.path.exists(p):
        log.append({"pass": "1 vs 2", **json.load(open(p, encoding="utf-8"))})
    return log


def sweep_rows(sweep):
    """Every sweep row as an audit-shaped row (grammar rows + unfiled + vocab), with what the sweep already knew."""
    dropped = {x["id"] for k in NOT_COUNTED for x in sweep.get(k, [])}
    out = []
    for r in sweep["rows"] + sweep.get("unfiled", []):
        if r["id"] in dropped:
            continue
        b = r.get("bucket") or {"NEW-B18": "B18"}.get(r.get("new_bucket_group") or "")
        out.append({"sweep_id": r["id"], "date": r["date"], "t": r.get("t"), "t_amal": r.get("t_amal"), "medi_said": r.get("medi_said"),
                    "amal_said": r.get("amal_said"), "chat": r.get("chat"), "wrong": r.get("wrong"), "right": r.get("right"),
                    "kind": "grammar", "tier": None, "bucket": b, "bucket2": r.get("bucket2"), "mode": r.get("mode", "speaking"),
                    "signal": r.get("signal"), "confidence": r.get("confidence"), "why": r.get("mistake"),
                    "machine_had": bool(r.get("machine_audit")), "new_bucket_group": r.get("new_bucket_group")})
    for i, v in enumerate(sweep.get("vocab", [])):
        out.append({"sweep_id": f"V{v['date'][5:7]}{v['date'][8:10]}-{i:03d}", "date": v["date"], "t": v.get("t"), "t_amal": None,
                    "medi_said": v.get("medi_said"), "amal_said": v.get("amal_gave"), "chat": None,
                    "wrong": None if v.get("kind") == "didn't-know" else v.get("medi_said"), "right": v.get("amal_gave"),
                    "kind": "vocab-A", "tier": 0 if v.get("kind") == "didn't-know" else 1, "bucket": None, "bucket2": None,
                    "mode": "speaking", "signal": "asked" if v.get("kind") == "didn't-know" else "recast", "confidence": "medium",
                    "why": v.get("english"), "english": v.get("english"), "machine_had": False})
    return out


def match_sweep(row, cands, used):
    for i, s in enumerate(cands):
        if i in used or not same_moment(row, s):
            continue
        if kind_class(row.get("kind")) != kind_class(s.get("kind")):
            continue
        if same_piece(row.get("wrong"), s.get("wrong")) or same_piece(row.get("right"), s.get("right")) \
                or (s.get("kind") == "vocab-A" and same_piece(row.get("right"), s.get("amal_said"))):
            used.add(i)
            return s
    return None


def build():
    sweep = json.load(open(os.path.join(REPO, "data", "grammar-sweep-2026-09-24.json"), encoding="utf-8"))
    buckets = {b["id"]: b for b in json.load(open(os.path.join(REPO, "docs", "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]}
    S = sweep_rows(sweep)
    by_date = collections.defaultdict(list)
    for s in S:
        by_date[s["date"]].append(s)
    rows, per_lesson, missing = [], [], []
    sweep_missed_by_readers = []
    for d in DATES:
        st = load_settled(d)
        if not st:
            missing.append(d)
            continue
        used = set()
        n_new = n_both = 0
        for r in st["rows"]:
            r = dict(r)
            r["date"] = d
            r["source"] = "audit-2026-09-26"
            s = match_sweep(r, by_date[d], used)
            if s:
                r["sweep_id"] = s["sweep_id"]
                r["machine_had"] = s.get("machine_had", False)
                if kind_class(r["kind"]) == "grammar" and not r.get("bucket") and s.get("bucket"):
                    r["bucket"] = s["bucket"]
                n_both += 1
            else:
                r["machine_had"] = False
                n_new += 1
            rows.append(r)
        kept = 0
        for i, s in enumerate(by_date[d]):
            if i in used:
                continue
            s = dict(s)
            s["source"] = "sweep-2026-09-24"
            s["agreed_by"] = "sweep (readers did not list it - kept, per the rule that nothing verified is dropped without a reason)"
            s["fid"] = s["sweep_id"]
            rows.append(s)
            sweep_missed_by_readers.append({"date": d, "sweep_id": s["sweep_id"], "kind": s["kind"], "wrong": s.get("wrong"), "right": s.get("right"), "t": s.get("t")})
            kept += 1
        c = st["counts"]
        per_lesson.append({"date": d, "coverage": st.get("coverage"), "r3_note": st.get("r3_note"), "passes": pass_log(d),
                           "agreement_pct": c.get("agreement_pct"), "readers_rows": c.get("final"),
                           "in_sweep_too": n_both, "new_vs_sweep": n_new, "sweep_only_kept": kept})
    # per-row bucket names + a stable order
    for r in rows:
        if r.get("bucket") in buckets:
            r["bucket_name"] = buckets[r["bucket"]]["name"]
    rows.sort(key=lambda r: (r["date"], sec(r.get("t")) if sec(r.get("t")) is not None else 1e9))
    for i, r in enumerate(rows, 1):
        r["uid"] = f"FA-{i:04d}"

    def cnt(pred):
        return sum(1 for r in rows if pred(r))
    scored = [r for r in rows if r.get("mode", "speaking") == "speaking" and r.get("kind") in ("grammar", "vocab-A")]
    totals = {
        "rows": len(rows),
        "grammar_A": cnt(lambda r: r["kind"] == "grammar" and r.get("mode", "speaking") == "speaking"),
        "grammar_B": cnt(lambda r: r["kind"] == "grammar-B"),
        "vocab_A": cnt(lambda r: r["kind"] == "vocab-A" and r.get("mode", "speaking") == "speaking"),
        "vocab_A_by_tier": dict(collections.Counter(str(r.get("tier")) for r in rows if r["kind"] == "vocab-A")),
        "vocab_B": cnt(lambda r: r["kind"] == "vocab-B"),
        "vocab_B_by_tier": dict(collections.Counter(str(r.get("tier")) for r in rows if r["kind"] == "vocab-B")),
        "listening": cnt(lambda r: r.get("mode") == "listening"),
        "from_readers": cnt(lambda r: r["source"] == "audit-2026-09-26"),
        "readers_also_in_sweep": cnt(lambda r: r["source"] == "audit-2026-09-26" and r.get("sweep_id")),
        "readers_new": cnt(lambda r: r["source"] == "audit-2026-09-26" and not r.get("sweep_id")),
        "sweep_only_kept": cnt(lambda r: r["source"] == "sweep-2026-09-24"),
        "machine_had": cnt(lambda r: r.get("machine_had")),
        "sweep_before": {"grammar": sweep["totals"].get("speaking_grammar"), "vocab": sweep["totals"].get("vocab")},
        "lesson_pages_before": {"vocab_errors_shown": 23},
    }
    by_bucket = collections.Counter(r.get("bucket") for r in rows if kind_class(r["kind"]) == "grammar" and r.get("mode", "speaking") == "speaking" and r.get("bucket"))
    by_lesson = {}
    for d in DATES:
        L = [r for r in rows if r["date"] == d]
        by_lesson[d] = {"grammar_A": sum(1 for r in L if r["kind"] == "grammar" and r.get("mode", "speaking") == "speaking"),
                        "grammar_B": sum(1 for r in L if r["kind"] == "grammar-B"),
                        "vocab_A": sum(1 for r in L if r["kind"] == "vocab-A" and r.get("mode", "speaking") == "speaking"),
                        "vocab_B": sum(1 for r in L if r["kind"] == "vocab-B"),
                        "listening": sum(1 for r in L if r.get("mode") == "listening"),
                        "sweep_grammar_before": sum(1 for p in sweep["per_lesson"] if p["date"] == d and (p.get("grammar") or 0)) and next(p.get("grammar", 0) + p.get("unfiled", 0) for p in sweep["per_lesson"] if p["date"] == d),
                        "sweep_vocab_before": next((p.get("vocab", 0) for p in sweep["per_lesson"] if p["date"] == d), 0)}
    # sweep-shaped view: scripts/build_lessons_page_data.py and build_grammar_console.py read this instead of the 09-24
    # sweep, so every page shows the audit without changing how the pages are built. Only A rows (Amal's voice / chat)
    # are here; B rows wait for Amal's ruling (scripts/apply_amal_audit_rulings.py flips them).
    compat_rows, compat_vocab = [], []
    for r in rows:
        base = {"id": r["uid"], "date": r["date"], "t": r.get("t"), "t_amal": r.get("t_amal"), "medi_said": r.get("medi_said"),
                "amal_said": r.get("amal_said"), "chat": r.get("chat"), "wrong": r.get("wrong"), "right": r.get("right"),
                "confidence": r.get("confidence") or "medium", "confidence_why": r.get("r3_why") or r.get("agreed_by"),
                "signal": r.get("signal"), "machine_audit": bool(r.get("machine_had")), "mode": r.get("mode", "speaking"),
                "source": r.get("source"), "uid": r["uid"], "sweep_id": r.get("sweep_id")}
        if r["kind"] == "grammar":
            compat_rows.append({**base, "mistake": r.get("why"), "bucket": r.get("bucket"), "bucket2": r.get("bucket2"), "new_bucket_group": r.get("new_bucket_group")})
        elif r["kind"] == "vocab-A":
            compat_vocab.append({**base, "amal_gave": r.get("right"), "english": r.get("english") or r.get("why"), "why": r.get("why"),
                                 "kind": "didn't-know" if r.get("tier") == 0 else "wrong-word", "tier": r.get("tier"),
                                 "amal_gave_arabizi": r.get("right_arabizi")})
    sweep_compat = {"built": "2026-09-26", "method": "full audit 2026-09-26 (two readers + third reader per lesson, reconciled with the 09-24 sweep)",
                    "rows": compat_rows, "unfiled": [], "vocab": compat_vocab,
                    "per_lesson": [{"date": p["date"], "coverage": " / ".join(x for x in [(p.get("coverage") or {}).get("r1"), (p.get("coverage") or {}).get("r2")] if x)} for p in per_lesson],
                    "rejected_on_hand_check": [], "pron_from_sweep": [], "hand_check": {},
                    "totals": {"speaking_grammar": totals["grammar_A"], "vocab": totals["vocab_A"], "machine_caught_speaking": totals["machine_had"]}}
    out = {"built": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "method": __doc__.strip(), "sweep_compat": sweep_compat,
           "decisions": "A counts (every fix Amal voiced or typed); B (she let it pass) is unscored until she rules on Amal's review page; "
                        "tiers 1-3 vocab, tier 0 = she supplied a word he asked for; grammar filed by bucket; listening rows kept apart.",
           "lessons_missing": missing, "totals": totals, "by_bucket": dict(by_bucket.most_common()), "by_lesson": by_lesson,
           "per_lesson": per_lesson, "sweep_rows_readers_missed": sweep_missed_by_readers, "rows": rows}
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(out, buckets)
    print("rows", len(rows), "| grammar A", totals["grammar_A"], "B", totals["grammar_B"], "| vocab A", totals["vocab_A"], "B", totals["vocab_B"],
          "| readers new vs sweep", totals["readers_new"], "| sweep-only kept", totals["sweep_only_kept"], "| missing lessons", missing)
    return out


def az(s):
    return s or ""


def write_md(out, buckets):
    T = out["totals"]
    L = [f"# Full vocab + grammar audit - {out['built'][:10]}", "",
         "Two independent readers per lesson, a third settles disagreements, reconciled with the 2026-09-24 hand sweep. "
         "A = Amal fixed it out loud or in chat (scored). B = she let it pass (unscored until she rules on her review page). "
         "Tier 0 = she supplied a word he asked for. Nothing the sweep verified was dropped.", "",
         "## Totals", "", "| | count |", "|---|---|",
         f"| Grammar fixes Amal voiced (A) | **{T['grammar_A']}** (sweep had {T['sweep_before']['grammar']}) |",
         f"| Grammar she let pass (B, to Amal) | {T['grammar_B']} |",
         f"| Vocab fixes Amal voiced (A) | **{T['vocab_A']}** (sweep had {T['sweep_before']['vocab']}; lesson pages showed 23) |",
         f"| - by tier (0 asked / 1 wrong word / 2 wrong form / 3 English-in-Arabic) | {T['vocab_A_by_tier']} |",
         f"| Vocab she let pass (B, to Amal) | **{T['vocab_B']}** by tier {T['vocab_B_by_tier']} |",
         f"| Listening-drill misreads (kept apart) | {T['listening']} |",
         f"| Rows the readers found that the sweep did not have | {T['readers_new']} |",
         f"| Sweep rows the readers did not list (kept) | {T['sweep_only_kept']} |",
         f"| Machine audit already had | {T['machine_had']} |", ""]
    if out["lessons_missing"]:
        L += [f"**Not settled yet:** {', '.join(out['lessons_missing'])}", ""]
    L += ["## Per lesson", "", "| lesson | grammar A | grammar B | vocab A | vocab B | listening | sweep grammar before | sweep vocab before | reader agreement |", "|---|---|---|---|---|---|---|---|---|"]
    pl = {p["date"]: p for p in out["per_lesson"]}
    for d, c in out["by_lesson"].items():
        p = pl.get(d, {})
        L.append(f"| {d} | {c['grammar_A']} | {c['grammar_B']} | {c['vocab_A']} | {c['vocab_B']} | {c['listening']} | {c['sweep_grammar_before']} | {c['sweep_vocab_before']} | {p.get('agreement_pct', '-')} % |")
    L += ["", "## Reader passes (the loop)", ""]
    for p in out["per_lesson"]:
        L.append(f"- **{p['date']}**: " + "; ".join(
            (f"pass {x['pass']}: r1 {x.get('r1')} r2 {x.get('r2')} agreed {x.get('agreed')} disputed {x.get('disputed')} ({x.get('agreement_pct')} %), r3 kept {x.get('r3_kept')} dropped {x.get('r3_dropped')} -> {x.get('final')} rows"
             if x["pass"] in (1, 2) else f"pass 1 vs pass 2: {x.get('agreement_pct')} % of rows in both") for x in p["passes"]))
    L += ["", "## Grammar by bucket (A, speaking)", "", "| bucket | name | fixes |", "|---|---|---|"]
    for b, n in out["by_bucket"].items():
        L.append(f"| {b} | {buckets.get(b, {}).get('name', '?')} | {n} |")
    L += ["", "## Sweep rows the readers did not list (kept, not dropped)", ""]
    for s in out["sweep_rows_readers_missed"][:400]:
        L.append(f"- {s['date']} {s['t']} {s['kind']} {s['sweep_id']}: {az(s.get('wrong'))} -> {az(s.get('right'))}")
    for d in DATES:
        rows = [r for r in out["rows"] if r["date"] == d]
        if not rows:
            continue
        p = pl.get(d, {})
        L += ["", f"### {d}", ""]
        cov = p.get("coverage") or {}
        if cov:
            L.append("_" + (cov.get("r1") or "") + " / " + (cov.get("r2") or "") + "_")
            L.append("")
        L += ["| id | time | kind | tier/bucket | Medi said | Amal said | wrong -> right | why | conf | source |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            tb = r.get("bucket") or (f"tier {r.get('tier')}" if r.get("tier") is not None else "")
            L.append(f"| {r['uid']} | {az(r.get('t'))} | {r['kind']}{' (listening)' if r.get('mode') == 'listening' else ''} | {tb} | {az(r.get('medi_said')).replace('|', '/')} | {az(r.get('amal_said')).replace('|', '/')} | {az(r.get('wrong')).replace('|', '/')} -> {az(r.get('right')).replace('|', '/')} | {az(r.get('why')).replace('|', '/')} | {az(r.get('confidence'))} | {r.get('agreed_by') or r.get('source')} |")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    build()
