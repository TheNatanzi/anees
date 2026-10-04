# -*- coding: utf-8 -*-
"""Results of the Gemini variables test (PR-18): scores.json (scripts/bench_score.py, one scorer for every row) + each
variable's own extra numbers -> bench/<date>/variables/results.json, tables.md and the picture charts.

    python scripts/bench_score.py 2026-10-02 && python scripts/bench_vars_report.py 2026-10-02
"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402
import bench_vars as BV  # noqa: E402

NOISE = 2                        # baseline temperature 0 vs 1 differed by 2 moments: a change of +-2 is noise
ORDER = ["v1", "v1h", "v2", "v3", "v4", "v4h", "v5", "v6", "v7", "v8", "v10", "v11", "v12", "v13", "best", "bestoa", "v0", "v9"]
LABEL = {"base": "Baseline: Flash + context, temperature 1", "v1": "V1 evidence (heard / inferred), all changes", "v1h": "V1 keep only 'heard' changes",
         "v2": "V2 forced choice (held + no-agreement lines)", "v3": "V3 two clips (his line + Amal's next)", "v4": "V4 word confidence, all changes",
         "v4h": "V4 keep only high-confidence changes", "v5": "V5 second guess (top 1)", "v6": "V6 Arabic span in long lines", "v7": "V7 accent note",
         "v8": "V8 word list, SAID", "v9": "V9 thinking high (224 lines, 2 runs)", "v10": "V10 vowel marks in the text",
         "v11": "V11 one-field answer (Gemini's idea)", "v12": "V12 guessing lines removed (Gemini's idea)", "v13": "V13 edge re-cut (clips that start or end on speech)",
         "best": "Best recipe: word list + said/meant + marks apart", "bestoa": "Best recipe on OpenAI gpt-audio",
         "v0": "Baseline on V9's 224 lines (2 runs)"}
COMPARE = {"v9": "v0"}           # V9 was sent fewer lines, 2 runs: it is compared with the baseline cut the same way
HARAKA = re.compile("[ً-ْ]")


def runs_of(d, engine):
    return [r for r in BS.load_runs(d, engine, "line")]


def either_hits(truth, runs):
    """V5: a moment counts when the first OR the second guess is right, in 2 of 3 runs (reported apart from top 1)."""
    lines = {ln["i"]: ln for ln in truth["lines"]}
    slip_of = {}
    for s in truth.get("slips") or []:
        slip_of.setdefault(s["i"], s)
    hit, ids = 0, []
    for m in truth["moments"]:
        ln, vs = lines[m["i"]], []
        for r in runs:
            o = r["lines"].get(str(m["i"]))
            if o is None:
                vs.append(BS.score_moment(m, None, (), ln["engine"], None, ln["truth"]))
                continue
            slip = slip_of.get(m["i"]) if m["class"] == "kept-slip" else None
            v1 = BS.score_moment(m, o, (), ln["engine"], slip, ln["truth"])
            raw = o.get("raw") if isinstance(o.get("raw"), dict) else {}
            t2 = BV.second_text(o.get("text") or "", raw.get("second_guess"))
            v2 = BS.score_moment(m, {"text": t2, "alt": ""}, (), ln["engine"], slip, ln["truth"]) if t2 != (o.get("text") or "") else v1
            vs.append("hit" if "hit" in (v1, v2) else v1)
        if BS.consensus(vs) == "hit":
            hit += 1
            ids.append(m["id"])
    return hit, ids


def meant_right(truth, runs, key="meant"):
    """V8: on each judged slip, does MEANT hold Amal's right form (2 of 3 runs)? And does SAID keep his wrong one?"""
    lines = {ln["i"]: ln for ln in truth["lines"]}
    rows = []
    for s in truth.get("slips") or []:
        ln = lines[s["i"]]
        vm, vs = [], []
        for r in runs:
            o = r["lines"].get(str(s["i"])) or {}
            raw = o.get("raw") if isinstance(o.get("raw"), dict) else {}
            vm.append(BS.slip_hidden(s, ln["truth"], str(raw.get(key) or "")))
            vs.append(BS.slip_hidden(s, ln["truth"], o.get("text") or ""))
        if vm[0] is None:
            continue
        rows.append({"t": s["t"], "wrong": s["wrong"], "right": s["right"], "meant_right": sum(bool(x) for x in vm) * 2 > len(vm),
                     "said_hides": sum(bool(x) for x in vs) * 2 > len(vs), "said": (runs[0]["lines"].get(str(s["i"])) or {}).get("text"),
                     "meant": ((runs[0]["lines"].get(str(s["i"])) or {}).get("raw") or {}).get(key) if isinstance((runs[0]["lines"].get(str(s["i"])) or {}).get("raw"), dict) else None})
    return rows


def harakat(truth, runs):
    """V10: how many Arabic words carry a vowel mark, and what was written on the two vowel-test lines of his."""
    words = marked = 0
    for r in runs:
        for o in r["lines"].values():
            for w in re.split(r"\s+", o.get("text") or ""):
                if BC.AR_LETTER.search(w):
                    words += 1
                    marked += bool(HARAKA.search(w))
    vt = []
    for v in truth.get("vowel") or []:
        ln = min(truth["lines"], key=lambda x: abs(x["t"] - v["medi_t"][0]))
        cands = [x for x in truth["lines"] if x["t"] <= v["medi_t"][1] and x["end"] >= v["medi_t"][0]] or [ln]
        vt.append({"word": v["word"], "medi_said": v["medi_said"], "lines": [{"t": x["t"], "runs": [(r["lines"].get(str(x["i"])) or {}).get("text") for r in runs]} for x in cands]})
    return {"arabic_words": words, "with_marks": marked, "pct": round(100.0 * marked / words, 1) if words else None, "vowel_lines": vt}


def subset_view(truth, d, vid, base_runs, runs):
    """v2 / v3 / v6 / v13: the lines the step touched - moments heard right and slips hidden there, baseline vs the step."""
    P = BC.J(os.path.join(BV.vdir(os.path.basename(d)), "prompts-%s.json" % vid)) or {}
    ids = {int(i) for i in P}
    lines = {ln["i"]: ln for ln in truth["lines"]}
    slip_of = {}
    for s in truth.get("slips") or []:
        slip_of.setdefault(s["i"], s)

    def hits(rr):
        n = 0
        for m in truth["moments"]:
            if m["i"] not in ids:
                continue
            ln = lines[m["i"]]
            vs = [BS.score_moment(m, r["lines"].get(str(m["i"])), (), ln["engine"], slip_of.get(m["i"]) if m["class"] == "kept-slip" else None, ln["truth"]) for r in rr]
            n += BS.consensus(vs) == "hit"
        return n

    def hidden(rr):
        n = 0
        for s in truth.get("slips") or []:
            if s["i"] not in ids:
                continue
            vs = [BS.slip_hidden(s, lines[s["i"]]["truth"], (r["lines"].get(str(s["i"])) or {}).get("text") or lines[s["i"]]["engine"]) for r in rr]
            n += sum(bool(x) for x in vs) * 2 > len(vs)
        return n

    def changed(rr):
        n = 0
        for i in ids:
            ln = lines[i]
            if not ln["should_stay"]:
                continue
            o, _ = BS.majority_text([r["lines"].get(str(i)) or {"text": ln["engine"]} for r in rr])
            n += BS.content_change(ln["truth"], o.get("text") or "")
        return n

    out = {"lines": len(ids), "moments_on_them": sum(1 for m in truth["moments"] if m["i"] in ids), "slips_on_them": sum(1 for s in truth["slips"] if s["i"] in ids),
           "untouched_on_them": sum(1 for i in ids if lines[i]["should_stay"]),
           "baseline": {"hit": hits(base_runs), "hidden": hidden(base_runs), "words_changed": changed(base_runs)},
           "variable": {"hit": hits(runs), "hidden": hidden(runs), "words_changed": changed(runs)}}
    c = collections.Counter()
    for r in runs:
        for i in P:
            o = r["lines"].get(i) or {}
            if vid == "v2":
                opt = P[i]["options"].get(o.get("chose") or "")
                c["engine's own text chosen" if opt is not None and " ".join(BC.tokens(opt)) == " ".join(BC.tokens(lines[int(i)]["engine"])) else "a Gemini text chosen" if opt is not None else "no valid choice"] += 1
            elif vid == "v3":
                c["held change taken" if o.get("took") else "held change rejected"] += 1
            elif vid == "v13":
                c["re-cut at the %s" % P[i]["edge"]] += 1
            else:
                raw = o.get("raw") or {}
                c["spans marked"] += len(raw.get("spans") or [])
                c["spans placed"] += sum(1 for x in raw.get("pieces") or [] if x.get("placed"))
                c["long lines with no Arabic marked"] += not (raw.get("spans") or [])
    out["calls"] = dict(c)
    return out


def change_stats(runs, field, values):
    c = collections.Counter()
    for r in runs:
        for o in r["lines"].values():
            raw = o.get("raw") if isinstance(o.get("raw"), dict) else {}
            for ch in raw.get("changes") or []:
                if isinstance(ch, dict):
                    v = str(ch.get(field) or "").lower()
                    c[v if v in values else "other"] += 1
    return dict(c)


def build(date):
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    S = BC.J(os.path.join(d, "scores.json")) or {}
    man = BC.J(os.path.join(BV.vdir(date), "manifest.json")) or {"vars": {}}
    base = S[BV.BASE + "|line"]
    base_runs = runs_of(d, BV.BASE)
    base_hit = {p["id"] for p in base["per_moment"] if p["final"] == "hit"}
    rows = []

    def row(vid, engine):
        s = S.get(engine + "|line")
        if not s:
            return None
        base = S.get(BV.engine_id(COMPARE[vid]) + "|line") if vid in COMPARE else S[BV.BASE + "|line"]
        base_hit = {p["id"] for p in base["per_moment"] if p["final"] == "hit"}
        rr = runs_of(d, engine)
        hit = {p["id"] for p in s["per_moment"] if p["final"] == "hit"}
        real = [p for p in s["per_moment"] if p["class"] != "latin-arabic"]
        calls = sum(1 for r in rr for o in r["lines"].values() if o.get("usd"))
        r = {"id": vid, "engine": engine, "name": LABEL.get(vid, vid), "runs": s["runs"], "heard_right": s["hit"], "of": s["moments"], "delta": s["hit"] - base["hit"],
             "noise": abs(s["hit"] - base["hit"]) <= NOISE, "real_mishearings_fixed": sum(p["final"] == "hit" for p in real),
             "latin_letter_arabic_fixed": s["hit"] - sum(p["final"] == "hit" for p in real), "hidden_slips": s["hidden_slips"], "slips_judged": s["slips_judged"],
             "lines_words_changed": s["content_changes"], "lines_changed": s["false_changes"], "should_stay": s["should_stay"], "same_3_of_3_pct": s["stable_pct"],
             "lines_2of3_agree_pct": s["lines_2of3_agree_pct"], "call_errors": s["call_errors"], "cost_usd": round(s["cost_usd"], 2),
             "cost_per_lesson_run": round(s["cost_usd"] / max(1, s["runs"]), 2), "paid_calls": calls, "seconds": s.get("seconds"),
             "compared_with": COMPARE.get(vid, "base"), "by_class": s["by_class"], "gained": sorted(hit - base_hit), "lost": sorted(base_hit - hit), "hidden_rows": s["hidden_rows"],
             "per_moment": s["per_moment"], "verdicts": s["verdicts"]}
        if vid in ("v2", "v3", "v6", "v13"):
            r["subset"] = subset_view(truth, d, vid, base_runs, rr)
            r["added_to_baseline"] = True
        if vid == "v1":
            r["changes_by_evidence"] = change_stats(rr, "evidence", ("heard", "inferred"))
        if vid == "v4":
            r["changes_by_confidence"] = change_stats(rr, "confidence", ("high", "medium", "low"))
        if vid == "v5" or (vid == "best" and any("second_guess" in (o.get("raw") or {}) for o in rr[0]["lines"].values() if isinstance(o.get("raw"), dict))):
            n, ids = either_hits(truth, rr)
            r["either_guess_right"] = n
            r["either_gained"] = sorted(set(ids) - hit)
            r["lines_with_second_guess"] = sum(1 for o in rr[0]["lines"].values() if isinstance(o.get("raw"), dict) and o["raw"].get("second_guess"))
        if vid == "v8" or (vid == "best" and any("meant" in (o.get("raw") or {}) for o in rr[0]["lines"].values() if isinstance(o.get("raw"), dict))):
            mr = meant_right(truth, rr)
            r["meant"] = {"slips_judged": len(mr), "meant_is_amals_form": sum(x["meant_right"] for x in mr), "said_hides": sum(x["said_hides"] for x in mr), "rows": mr}
        if vid in ("v10", "best"):
            r["harakat"] = harakat(truth, rr)
        if vid in ("v1h", "v4h"):
            r["derived_from"] = BV.engine_id(BV.DERIVED[vid][0])
            r["stats"] = [x.get("stats") for x in rr]
        return r

    b = row("base", BV.BASE)
    for vid in ORDER:
        e = (man["vars"].get(vid) or {}).get("engine") or BV.engine_id(vid)
        r = row(vid, e)
        if r:
            rows.append(r)
    extra = [row(k, v["engine"]) for k, v in man["vars"].items() if k not in ORDER]
    rows += [r for r in extra if r]
    spend = {r["id"]: {"usd": r["cost_usd"], "calls": r["paid_calls"], "service": "openai" if r["engine"].startswith("openai") else "gemini"} for r in rows if r["cost_usd"]}
    for k in ("codex-improvement-review.md", "codex-astra-whole-project-review.md"):
        pass
    out = {"test": "Gemini variables test on the frozen 10-02 benchmark (PR-18)", "lesson": date, "built": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
           "truth_sha256": man.get("truth_sha256"), "noise_moments": NOISE, "baseline": b, "variables": rows, "frozen": man["vars"],
           "spend": spend, "spend_total_usd": round(sum(x["usd"] for x in spend.values()), 2),
           "spend_gemini_usd": round(sum(x["usd"] for x in spend.values() if x["service"] == "gemini"), 2),
           "spend_openai_usd": round(sum(x["usd"] for x in spend.values() if x["service"] == "openai"), 2),
           "price_note": "list-price estimates from the tokens each call reported; Google took about 35 % more than this count on 2026-10-04 (20 dollars of credit for 14.78 counted)",
           "gemini_self_review": (BC.J(os.path.join(BV.vdir(date), "gemini-self-review.json")) or {}).get("answer")}
    BC.W(os.path.join(BV.vdir(date), "results.json"), out)
    return out


def verdict(r):
    if r["delta"] > NOISE:
        return "better (+%d)" % r["delta"]
    if r["delta"] < -NOISE:
        return "worse (%d)" % r["delta"]
    return "same (%+d, inside the noise)" % r["delta"]


def tables(out):
    b = out["baseline"]
    L = ["| Recipe | Heard right (of 63) | vs baseline | Slips hidden (of %d) | Untouched lines with a word changed (of 519) | Same in 3 of 3 | Cost per lesson (1 run) |" % b["slips_judged"],
         "|---|---|---|---|---|---|---|",
         "| **%s** | **%d** | - | %d | %d | %s%% | $%.2f |" % (b["name"], b["heard_right"], b["hidden_slips"], b["lines_words_changed"], b["same_3_of_3_pct"], b["cost_per_lesson_run"])]
    for r in out["variables"]:
        cost = "$%.2f" % r["cost_per_lesson_run"] if r["cost_usd"] else "$0 (no call)"
        if r.get("added_to_baseline"):
            cost = "+" + cost
        L.append("| %s | **%d** | %s | %d | %d | %s%% | %s |" % (r["name"], r["heard_right"], verdict(r), r["hidden_slips"], r["lines_words_changed"], r["same_3_of_3_pct"], cost))
    return "\n".join(L)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    out = build(sys.argv[1])
    md = tables(out)
    open(os.path.join(BV.vdir(sys.argv[1]), "tables.md"), "w", encoding="utf-8", newline="\n").write(md + "\n")
    print(md)
    for r in out["variables"]:
        ex = {k: r[k] for k in ("subset", "changes_by_evidence", "changes_by_confidence", "either_guess_right", "either_gained", "lines_with_second_guess", "stats") if k in r}
        if "meant" in r:
            ex["meant"] = {k: v for k, v in r["meant"].items() if k != "rows"}
        if "harakat" in r:
            ex["harakat"] = {k: v for k, v in r["harakat"].items() if k != "vowel_lines"}
        print(r["id"], "gained", r["gained"], "lost", r["lost"], json.dumps(ex, ensure_ascii=False))
    print("spend:", json.dumps(out["spend"]), "total $%.2f" % out["spend_total_usd"])
