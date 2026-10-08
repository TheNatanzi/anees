# -*- coding: utf-8 -*-
"""The audit of the Gemini backfill (overnight spec 2026-10-04, Phase 5): per lesson, before vs after, from the files -
nothing is called, nothing is changed. It is what Codex and the council read before anything is published.

    python scripts/rehear_audit.py            # data/lesson-work/rehear/audit.json + audit.md

Sections: the Gemini-only verdict; the recipe on Medi's own key (10-02); per lesson what changed; his corrections;
what was NOT applied; integrity (raw files, other people's rows, row targets); the grammar-use counter's reach; the
re-judge (slips, Amal's rulings, page numbers) when its report exists; the blind spot check; money.
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_piles as PL  # noqa: E402
import rehear_apply as RA  # noqa: E402
import rehear_job as RJ  # noqa: E402
import rehear_lesson as RL  # noqa: E402
import rehear_status as RS  # noqa: E402
import transcript_fixes as TF  # noqa: E402

REJ = os.path.join(RJ.REHEAR, "rejudge")


def key_check(date="2026-10-02"):
    """Tonight's piles for the benchmark lesson, scored on Medi's key v2 by bench_piles.measure (the key decides nothing)."""
    bd = BC.bench_dir(date)
    truth = BC.J(os.path.join(bd, "truth-v2.json"))
    P = BC.J(os.path.join(RL.ldir(date), "proposals.json"))
    if not truth or not P:
        return None
    rows = [dict(r, status="held" if r["status"] == "held-mix" else r["status"]) for r in P["rows"] if r["i"] in {ln["i"] for ln in truth["lines"]}]
    m = PL.measure(truth, rows)
    out = {k: m[k] for k in ("moments", "moments_right_in_delivered_transcript", "moments_fixed_by_proposed", "moments_fixed_with_held", "slips_hidden_by_proposed",
                             "slips_hidden_with_held", "untouched_lines_word_changed_proposed", "proposed", "held", "no_agreement", "slips_hidden_rows")}
    # 2026-10-05 (Codex final approval, blocker 2): the numbers above are the PILE (what Gemini's rows would do on the
    # engine's lines). A line Medi corrected himself keeps his correction and never takes the pile's row, so what counts
    # for a hidden slip is the transcript the pages DELIVER: his slips whose wrong piece is no longer on the delivered line.
    import bench_score as BS
    turns = (BC.J(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json")) or {}).get("turns") or []
    lines = {ln["i"]: ln for ln in truth["lines"]}
    hidden = [s for s in truth["slips"] if s["i"] < len(turns) and BS.slip_hidden(s, lines[s["i"]]["truth"], turns[s["i"]]["text"])]
    out["slips_hidden_in_delivered_transcript"] = len(hidden)
    out["slips_hidden_in_delivered_rows"] = [{"t": s["t"], "wrong": s["wrong"], "right": s["right"], "delivered_line": turns[s["i"]]["text"]} for s in hidden]
    out["pile_rows_not_delivered_because_medi_corrected_the_line"] = [
        {"t": s["t"], "wrong": s["wrong"], "delivered_line": turns[s["i"]]["text"]} for s in truth["slips"]
        if s not in hidden and any(x["t"] == s["t"] for x in m["slips_hidden_rows"]) and s["i"] < len(turns)]
    return out


def track_reach(date, rows):
    """How many of the lesson's Gemini spans reach the lines the grammar-use counter reads. Since 2026-10-05 the counter
    reads the lines the pages show (lesson_turns.page_lines: Codex final approval, blocker 1), so every span that is on
    the page is on the counter's lines; before, it read track turns (09-10: 8 of 253)."""
    import lesson_turns as LT
    T, src = LT.page_lines(date)
    landed = sum(1 for u in T for h in (u.get("heard") or []) if h.get("by") == RA.BY)
    return {"source": src, "spans": sum(len(r["spans"]) for r in rows), "spans_reaching_track_turns": landed}


def integrity():
    before = BC.J(os.path.join(REJ, "raw-hashes-before.json"))
    changed, missing = [], []
    for d, files in before["lessons"].items():
        root = os.path.join(BC.RAW, d)
        for rel, sha in files.items():
            p = os.path.join(root, rel)
            if not os.path.exists(p):
                missing.append(d + "/" + rel)
            elif BC.sha_file(p) != sha:
                changed.append(d + "/" + rel)
    old = BC.J(os.path.join(REJ, "transcript-fixes-before.json"))["rows"]
    now = BC.J(TF.FIXES_P)["rows"]
    others = [r for r in now if r.get("by") != RA.BY]
    it = iter(others)
    kept_in_order = all(any(o == r for r in it) for o in old)            # every row of before is still there, unchanged, in order
    added = [r for r in others if r not in old]
    return {"raw_files_hashed_before": sum(len(v) for v in before["lessons"].values()), "raw_files_changed": changed, "raw_files_missing": missing,
            "overlay_rows_before": len(old), "overlay_rows_of_others_now": len(others), "others_rows_identical_and_in_order": kept_in_order,
            "others_rows_added_since": [{"date": r.get("date"), "t": r.get("t"), "by": r.get("by"), "on": r.get("on"), "quote": r.get("quote")} for r in added],
            "gemini_rows_now": len(now) - len(others), "row_check_problems": RA.check()}


def build():
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "gemini_only_test": None, "recipe_on_medis_key_10_02": key_check(), "lessons": {}, "totals": {}}
    v = BC.J(os.path.join(RL.ldir("2026-10-02"), "gonly", "verdict.json"))
    if v:
        k2 = v["keys"]["v2"]
        doc["gemini_only_test"] = {"passed": v["passed"], "checks": v["checks"], "key_v2": k2["gemini_only"], "todays_way_instant": k2["today_instant"],
                                   "todays_way_batch": k2["today_batch"], "amal_moments_v1": v["keys"]["v1"]["amal_moments"], "timing": v["timing"], "cost_usd": v["cost_usd"],
                                   "caveat": "pass 2 ran without Amal's typed chat (the chat clock could not be placed without the old transcript)"}
    status = RS.load()["lessons"]
    tot = {}
    for d in RS.published():
        ld = RL.ldir(d)
        man, P, plan = BC.J(os.path.join(ld, "manifest.json")), BC.J(os.path.join(ld, "proposals.json")), BC.J(os.path.join(ld, "apply-plan.json"))
        row = {"status": (status.get(d) or {}).get("status"), "frozen": bool(man)}
        if man:
            row.update(counts=man["counts"], recut_skipped=man.get("recut_skipped_tracks") or [])
        if P:
            row["piles"] = P["summary"]
        if plan:
            row["apply"] = plan["summary"]
            row["track_reach"] = track_reach(d, plan["rows"])
            row["his_corrections_not_heard"] = [{"mmss": x["mmss"], "engine": x["engine_wrote"], "his": x["his"], "runs": x["runs"]} for x in plan["listen"]]
        sp = BC.J(os.path.join(ld, "spot.json"))
        if sp:
            row["spot_check"] = {"checked": sp["checked"], "prefers": sp["prefers"], "cost_usd": sp["cost_usd"]}
        doc["lessons"][d] = row
        for k, val in (row.get("apply") or {}).items():
            tot[k] = tot.get(k, 0) + val
        tot["listen_lines"] = tot.get("listen_lines", 0) + ((man or {}).get("counts") or {}).get("listen", 0)
        tot["cost_usd"] = round(tot.get("cost_usd", 0) + ((P or {}).get("summary") or {}).get("cost_usd", 0), 4)
    doc["totals"] = tot
    doc["integrity"] = integrity()
    rep = BC.J(os.path.join(REJ, "report.json"))
    if rep:
        doc["rejudge"] = {"made": rep.get("made"), "amal_rulings_reapplied": rep.get("amal_rulings_reapplied"), "totals_before": rep.get("totals_before"), "totals_after": rep.get("totals_after"),
                          "orphaned": rep.get("orphaned"),
                          "lessons": {d: {k: x.get(k) for k in ("rows_before", "rows_after", "scored_before", "scored_after", "same_uid", "moved", "added", "removed", "kept", "amal", "verification_records", "patterns", "headline")}
                                      for d, x in (rep.get("lessons") or {}).items()}} if isinstance(rep.get("lessons"), dict) else rep
    doc["money"] = {"limit_usd": RJ.BACKFILL_LIMIT_USD, "spent_or_owed_usd": RJ.spent(),
                    "jobs": sum(1 for _ in RJ.all_jobs()), "by_lesson_usd": {d: round(sum((j.get("usd") or 0.0) for p, j in RJ.all_jobs() if os.sep + d + os.sep in p), 4) for d in RS.published()}}
    BC.W(os.path.join(RJ.REHEAR, "audit.json"), doc)
    md = ["# Audit of the Gemini backfill (%s)" % doc["built"], ""]
    g = doc["gemini_only_test"]
    if g:
        md += ["## 1. Gemini-only test on 10-02: %s" % ("PASSED" if g["passed"] else "NOT PASSED"), "",
               "| | Gemini-only | Today's way (instant) | Today's way (Batch) |", "|---|---|---|---|",
               "| Heard right of 63 (key v2; pass mark 54) | %d | %d | %d |" % (g["key_v2"]["hit"], g["todays_way_instant"]["hit"], g["todays_way_batch"]["hit"]),
               "| His slips hidden | %d | %d | %d |" % (g["key_v2"]["hidden_slips"], g["todays_way_instant"]["hidden_slips"], g["todays_way_batch"]["hidden_slips"]),
               "| Untouched lines with a word changed (of 519) | %d | %d | %d |" % (g["key_v2"]["content_changes"], g["todays_way_instant"]["content_changes"], g["todays_way_batch"]["content_changes"]),
               "", "- His lines whose segment starts within 1 s: %s %%. Amal's 6 corrected moments: %d heard (ElevenLabs 0). Cost $%.2f." % (g["timing"]["start_within_1s_pct"], g["amal_moments_v1"]["hit"], g["cost_usd"]),
               "- Caveat: %s." % g["caveat"], ""]
    k = doc["recipe_on_medis_key_10_02"]
    if k:
        md += ["## 2. Tonight's recipe on Medi's own key (10-02, key v2)", "",
               "- Corrections right in the transcript the proposed pile delivers: **%d of %d** (the engine alone: 4). Fixed by the proposed pile: %d; with the held lines: %d." % (
                   k["moments_right_in_delivered_transcript"], k["moments"], k["moments_fixed_by_proposed"], k["moments_fixed_with_held"]),
               "- His slips hidden by the proposed pile: %d (%s). Untouched lines with a word changed: %d." % (
                   k["slips_hidden_by_proposed"], "; ".join("%02d:%02d %s -> %s" % (int(s["t"]) // 60, int(s["t"]) % 60, s["wrong"], s["right"]) for s in k["slips_hidden_rows"]) or "none", k["untouched_lines_word_changed_proposed"]),
               "- **His slips hidden in the delivered transcript: %d.**%s" % (
                   k.get("slips_hidden_in_delivered_transcript", 0),
                   (" The pile's row at %s is not delivered: Medi's own correction is on that line (he re-listened on 2026-10-04 and confirmed the word), so the line reads '%s' and the slip stands." % (
                       ", ".join("%02d:%02d" % (int(x["t"]) // 60, int(x["t"]) % 60) for x in k["pile_rows_not_delivered_because_medi_corrected_the_line"]),
                       k["pile_rows_not_delivered_because_medi_corrected_the_line"][0]["delivered_line"])) if k.get("pile_rows_not_delivered_because_medi_corrected_the_line") else ""), ""]
    md += ["## 3. Per lesson", "", "| Lesson | Status | Lines heard | Own mic / mix | Lines changed | words / alphabet | Kept (already corrected) | His corrections: heard by 2 of 3 / 1 / 0 (of listened) | Held | Held (mix) | No agreement | Spans on the use counter's lines | Blind check: new / old / split | $ |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, r in doc["lessons"].items():
        c, a, p = r.get("counts") or {}, r.get("apply") or {}, r.get("piles") or {}
        tr, sp = r.get("track_reach") or {}, (r.get("spot_check") or {}).get("prefers") or {}
        md.append("| %s | %s | %s | %s / %s | %s | %s / %s | %s | %s / %s / %s (of %s) | %s | %s | %s | %s of %s | %s | %s |" % (
            d, r.get("status"), c.get("listen", ""), c.get("own_track", ""), c.get("mix", ""), a.get("lines_changed", ""), a.get("word_changes", ""), a.get("alphabet_only", ""),
            a.get("lines_kept_because_already_corrected", ""), a.get("his_corrections_heard_by_2_of_3", ""), a.get("his_corrections_heard_by_1_of_3", ""), a.get("his_corrections_all_3_runs_disagree", ""),
            a.get("his_corrections_listened", ""), a.get("held", ""), a.get("held_mix", ""), a.get("no_agreement", ""), tr.get("spans_reaching_track_turns", ""), tr.get("spans", ""),
            ("%s / %s / %s" % (sp.get("new text"), sp.get("old text"), sp.get("split"))) if sp else "", p.get("cost_usd", "")))
    i = doc["integrity"]
    md += ["", "## 4. Integrity", "",
           "- Raw archive: %d files hashed before; changed %d, missing %d." % (i["raw_files_hashed_before"], len(i["raw_files_changed"]), len(i["raw_files_missing"])),
           "- Overlay file: %d rows before; other people's rows now %d; every row of before still there, identical and in order: %s; added since: %s; Gemini rows %d." % (
               i["overlay_rows_before"], i["overlay_rows_of_others_now"], i["others_rows_identical_and_in_order"],
               "; ".join("%s %s by %s (%s) '%s'" % (x["date"], x["t"], x["by"], x["on"], x["quote"]) for x in i["others_rows_added_since"]) or "none", i["gemini_rows_now"]),
           "- Row check (each Gemini row changes exactly its own line, on the page builder's lines): %s." % ("OK" if not i["row_check_problems"] else "%d problem(s)" % len(i["row_check_problems"])), ""]
    if doc.get("rejudge"):
        md += ["## 5. Re-judge: see data/lesson-work/rehear/rejudge/report.md (slips before / after, Amal's rulings, page numbers)", ""]
    m = doc["money"]
    md += ["## 6. Money", "", "- Gemini for this job: $%.2f spent or owed of the $%.0f limit, %d jobs." % (m["spent_or_owed_usd"], m["limit_usd"], m["jobs"]), ""]
    with open(os.path.join(RJ.REHEAR, "audit.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    return doc


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
