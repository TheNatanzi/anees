# -*- coding: utf-8 -*-
"""Do the numbers add up across pages?  (eng audit 2026-09-29, areas 1 + 2; Medi's decisions 4 and 6)

    python scripts/check_numbers.py            -> one line: "numbers: OK <n> checks"  or  "numbers: FAIL <reason> (+k more)"
    python scripts/check_numbers.py -v         -> every failed check, one per line, then the summary line
    python scripts/check_numbers.py --json F   -> also write every check (name, ok, detail) to F

Offline, read-only, deterministic, well under 60 s. Exit 0 = every check holds, 1 = at least one fails, 2 = a file is
missing or unreadable. The publish guard runs it before every publish; a FAIL means "do not publish, keep the last
good version live".

What it checks (each number is recomputed here from the stored rows, and the pages' own code is run in node on the
published data, then the two are compared):
  1. lesson words:   right + partial + wrong = scored; Vocab % = (right + ½ partial) ÷ scored; the lesson file's cards
                     add up to the summary; the Word Bank (with the lesson audit's word slips) scores exactly the same
                     attempts per lesson; Progress › Vocab's per-lesson series equals them; "N words" = distinct forms.
  2. lesson grammar: slips = the full audit's counted rows (minus Amal's rulings, minus duplicates); uses and the % =
                     scripts/grammar_math.py recomputed from grammar-usage.json + the audit; Σ over lessons = Σ over
                     rules on the Grammar Console; slips never exceed uses; console statuses sit in their stated bands.
  3. one slip, one row: no two counted audit rows share lesson + second + wrong piece + kind.
  4. averages:       the pooled Words / Grammar averages the Lessons page and the Overview show (docs/js/lesson-math.js,
                     run in node) equal this file's recompute; both pages use that one function.
  5. Word Bank:      headline accuracy = status points ÷ (tested × 10); Words known = Good + Mastered; every form with
                     10+ attempts sits in the band its latest-10 score gives.
  6. verified marks: every lesson carries release.status + reasons; a lesson that is not verified shows no verified %
                     and is marked "≈" by the pages' own function (decision 4).
"""
import argparse, collections, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "ok": bool(ok), "detail": "" if ok else detail})
    return ok


def J(*p):
    with open(os.path.join(REPO, *p), encoding="utf-8") as f:
        return json.load(f)


def node_bin():
    for c in (os.environ.get("ANEES_NODE"), r"C:/dev/tools/node-v24.18.0-win-x64/node.exe", "node"):
        if c and (os.path.exists(c) or c == "node"):
            return c
    return "node"


def sec(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        p = [float(x) for x in str(v).split(":")]
    except ValueError:
        return None
    return sum(x * 60 ** i for i, x in enumerate(reversed(p)))


def pct1(num, den):
    return round(100 * num / den, 1) if den else None


def run(repo=REPO):
    global REPO
    REPO = repo
    import grammar_math, amal_grammar_notes as AMAL
    from full_audit_build import uid_base
    L = J("docs", "data", "lessons.json")["lessons"]
    dates = [x["date"] for x in L]
    D = {d: J("docs", "data", "lessons", d + ".json") for d in dates}
    audit = J("data", "full-audit-2026-09-26.json")
    usage = J("docs", "data", "grammar-usage.json")
    console = J("docs", "data", "grammar-console.json")
    buckets = {b["id"]: b for b in J("docs", "data", "grammar-buckets.json")["buckets"]}
    slips_p = os.path.join(REPO, "docs", "data", "word-bank-audit-slips.json")
    slips_doc = J("docs", "data", "word-bank-audit-slips.json") if os.path.exists(slips_p) else None

    # ---------------- 3. one slip, one row
    counted = [r for r in audit["rows"] if r["kind"] in ("grammar", "grammar-B", "vocab-A", "vocab-B")]
    seen, dups = {}, []
    for r in counted:
        k = uid_base(r)
        if k in seen:
            dups.append(f"{seen[k]}+{r['uid']}")
        seen[k] = r["uid"]
    check("audit: each slip counted once", not dups, f"the same slip is counted twice in the full audit: {', '.join(dups[:4])}")

    # ---------------- 2. grammar, recomputed from raw rows
    G = collections.defaultdict(list)
    for r in audit["sweep_compat"]["rows"]:
        b = r.get("bucket") or ("B18" if r.get("new_bucket_group") == "NEW-B18" else None)
        if r.get("mode") != "speaking" or b not in buckets:
            continue
        rr = dict(r, bucket=b)
        if AMAL.ruling(rr):
            continue
        G[r["date"]].append({"bucket": b, "date": r["date"], "t": sec(r.get("t")) if r.get("t") else sec(r.get("t_amal"))})
    T = grammar_math.table(usage.get("uses", {}), [s for v in G.values() for s in v], list(buckets), AMAL.not_taught)
    rules = {r["id"]: r for r in console["rules"]}
    cl = {x["date"]: x for x in console.get("lessons", [])}
    for x in L:
        d, g = x["date"], x["grammar"]
        det = D[d]
        check(f"{d} grammar slips = the audit's counted rows", g["mistakes"] == len(G.get(d, [])),
              f"{d}: the Lessons page shows {g['mistakes']} grammar slips, the full audit has {len(G.get(d, []))} counted rows")
        check(f"{d} grammar slips = grammar cards", g["mistakes"] == len(det.get("grammar_errors", [])),
              f"{d}: grammar.mistakes {g['mistakes']} but the lesson page lists {len(det.get('grammar_errors', []))} grammar cards")
        want = grammar_math.lesson(T, d) if d in (usage.get("lessons") or {}) else None
        if want:
            check(f"{d} grammar uses (one formula)", g.get("uses") == want["uses"],
                  f"{d}: the Lessons page counts {g.get('uses')} grammar uses, the Grammar Console's formula gives {want['uses']}")
            check(f"{d} grammar % (one formula)", g.get("pct") == want["pct"],
                  f"{d}: Grammar % is {g.get('pct')} on the Lessons page, {want['pct']} by the Grammar Console's formula")
            sm = g.get("scored_mistakes", g["mistakes"])
            check(f"{d} grammar slips <= uses", g.get("uses") is None or sm <= g["uses"],
                  f"{d}: {sm} scored grammar slips but only {g.get('uses')} uses")
            check(f"{d} grammar no estimate", not g.get("estimate"), f"{d}: Grammar % is still an estimate (uses undercounted)")
        c = cl.get(d)
        check(f"{d} on the Grammar Console", c is not None, f"{d}: lesson missing from the Grammar Console")
        if c:
            check(f"{d} console slips = lessons slips", c.get("slips_counted") == g["mistakes"],
                  f"{d}: the Grammar Console counts {c.get('slips_counted')} slips, the Lessons page {g['mistakes']}")
    for b, r in T.items():
        cr = rules.get(b)
        if not cr:
            check(f"rule {b} on console", False, f"rule {b} missing from the Grammar Console")
            continue
        check(f"rule {b} uses", cr["uses"] == r["uses"], f"rule {b}: console shows {cr['uses']} uses, recompute from the audit + usage gives {r['uses']}")
        check(f"rule {b} mistakes", cr["mistakes"] == r["mistakes"], f"rule {b}: console shows {cr['mistakes']} mistakes, recompute gives {r['mistakes']}")
        if cr.get("pct") is not None:
            check(f"rule {b} score", cr["pct"] == grammar_math.pct(cr["uses"], cr["mistakes"], None),
                  f"rule {b}: score {cr['pct']}% but (uses − mistakes) ÷ uses = {grammar_math.pct(cr['uses'], cr['mistakes'], None)}%")
        if cr["status"] in ("Mastered", "Good", "Shaky", "Wrong"):
            p = round(100 * (cr["uses"] - cr["mistakes"]) / cr["uses"]) if cr["uses"] else None
            band = None if p is None else "Mastered" if cr["uses"] >= 10 and p >= 95 else "Good" if p >= 85 else "Shaky" if p >= 65 else "Wrong"
            check(f"rule {b} band", band == cr["status"], f"rule {b}: status {cr['status']} but {p}% on {cr['uses']} uses is {band} by the stated cut-offs (Mastered 95+ on 10+ uses, Good 85+, Shaky 65+)")
    scored_rules = [r for r in console["rules"] if r["status"] in ("Mastered", "Good", "Shaky", "Wrong")]
    su, sm_ = sum(r["uses"] for r in scored_rules), sum(r["mistakes"] for r in scored_rules)
    lu = sum(x["grammar"].get("uses") or 0 for x in L)
    lm = sum(x["grammar"].get("scored_mistakes", x["grammar"]["mistakes"]) for x in L)
    check("grammar uses: lessons = rules", lu == su, f"grammar uses add up to {lu} over the lessons but {su} over the Grammar Console's scored rules")
    check("grammar slips in the %: lessons = rules", lm == sm_, f"scored grammar slips add up to {lm} over the lessons but {sm_} over the console's scored rules")
    check("grammar slips: lessons = console", sum(x["grammar"]["mistakes"] for x in L) == sum(r["mistakes"] for r in console["rules"]),
          f"the Lessons page counts {sum(x['grammar']['mistakes'] for x in L)} grammar slips, the Grammar Console {sum(r['mistakes'] for r in console['rules'])}")
    fam = collections.Counter()
    for r in console["rules"]:
        fam[r["family"]] += r["mistakes"]
    check("grammar families add up", sum(fam.values()) == sum(r["mistakes"] for r in console["rules"]), "family totals do not add up to the rule total")

    # ---------------- 1. lesson words
    unplaced = collections.Counter()
    counted_unplaced = [u for u in (slips_doc or {}).get("unplaced", []) if u.get("counted") is not False]
    for u in counted_unplaced:   # on-list slips the Word Bank has no form for: they count on the Lessons page only
        unplaced[(u["date"], "wrong" if u["kind"] == "wrong" else "asked")] += 1
    for x in L:
        d, w = x["date"], x["words"]
        check(f"{d} words add up", w["right"] + w["partial"] + w["wrong"] == w["scored"],
              f"{d}: words right {w['right']} + partial {w['partial']} + wrong {w['wrong']} is not scored {w['scored']}")
        check(f"{d} words %", w.get("pct") == (round(100 * (w["right"] + .5 * w["partial"]) / w["scored"], 1) if w["scored"] else None),
              f"{d}: Words % {w.get('pct')} is not (right + half partial) ÷ scored")
        ve = [e for e in D[d].get("vocab_errors", []) if e.get("on_sheet") is not False]
        vc = D[d].get("vocab_correct", [])
        calc = {"right": sum(1 for e in vc if e["kind"] == "correct"),
                "partial": sum(1 for e in vc if e["kind"] == "partial") + sum(1 for e in ve if e["kind"] in ("asked", "partial")),
                "wrong": sum(1 for e in ve if e["kind"] == "wrong")}
        for k, v in calc.items():
            check(f"{d} words.{k} = cards", w[k] == v, f"{d}: the Lessons summary says {w[k]} {k}, its cards add up to {v}")
    check("word slips file present", slips_doc is not None,
          "docs/data/word-bank-audit-slips.json is missing: the Word Bank and Progress do not count the lesson audit's word slips the Lessons page counts")
    try:
        out = os.path.join(REPO, "data", "eng-audit", ".numbers-node.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run([node_bin(), os.path.join(HERE, "numbers_node.cjs"), os.path.join(REPO, "docs"), out], check=True,
                       capture_output=True, timeout=50)
        N = json.load(open(out, encoding="utf-8"))
    except Exception as e:  # node missing or a page script broke: that is a failure, not a pass
        check("pages' own code runs", False, f"could not run the pages' own code in node ({type(e).__name__}: {str(e)[:120]})")
        N = None
    if N:
        series = {s["date"]: s for s in N["vocab_series"]}
        for x in L:
            d, w = x["date"], x["words"]
            b = N["wb_by_date"].get(d, {"p1": 0, "p05": 0, "p0": 0, "unique_forms": 0})
            wb = {"right": b["p1"], "partial": b["p05"] + unplaced[(d, "asked")], "wrong": b["p0"] + unplaced[(d, "wrong")]}
            for k in ("right", "partial", "wrong"):
                check(f"{d} Word Bank = Lessons ({k})", wb[k] == w[k],
                      f"{d}: the Word Bank scores {wb[k]} {k} word uses, the Lessons page {w[k]}")
            s = series.get(d)
            if s:
                check(f"{d} Progress Vocab = Word Bank", (s["correct"], s["hinted"], s["wrong"]) == (b["p1"], b["p05"], b["p0"]),
                      f"{d}: Progress › Vocab shows {s['correct']}/{s['hinted']}/{s['wrong']} correct/hinted/wrong, the Word Bank {b['p1']}/{b['p05']}/{b['p0']}")
                check(f"{d} unique words", s["unique"] == w.get("unique"),
                      f"{d}: Progress › Vocab counts {s['unique']} different words, the Lessons page {w.get('unique')}")
        # 4. averages: the pages' function vs a recompute
        W = [x for x in L if x["words"].get("scored")]
        pw = 100 * sum(x["words"]["right"] + x["words"]["partial"] / 2 for x in W) / sum(x["words"]["scored"] for x in W)
        check("pooled words average", abs((N["pooled_words"]["pct"] or 0) - pw) < 1e-9, f"pooled Words % {N['pooled_words']['pct']} vs recompute {pw}")
        GG = [x for x in L if (x["grammar"].get("uses") or 0) > 0 and not x["grammar"].get("estimate")
              and x["grammar"].get("scored_mistakes", x["grammar"]["mistakes"]) <= x["grammar"]["uses"]]
        gu = sum(x["grammar"]["uses"] for x in GG)
        gp = 100 * (gu - sum(x["grammar"].get("scored_mistakes", x["grammar"]["mistakes"]) for x in GG)) / gu if gu else None
        check("pooled grammar average", gp is not None and abs((N["pooled_grammar"]["pct"] or 0) - gp) < 1e-9, f"pooled Grammar % {N['pooled_grammar']['pct']} vs recompute {gp}")
        check("pooled grammar covers every lesson", N["pooled_grammar"]["n"] == sum(1 for x in L if (x["grammar"].get("uses") or 0) > 0),
              f"the pooled Grammar average leaves out {sum(1 for x in L if (x['grammar'].get('uses') or 0) > 0) - N['pooled_grammar']['n']} lesson(s)")
        # 5. Word Bank headline + bands
        tested = sum(v for k, v in N["status"].items() if k != "Untested")
        check("Word Bank accuracy = status points", N["wb_accuracy"] is None or abs(N["wb_accuracy"] - N["wb_points_accuracy"]) < 1e-9,
              f"Overall Accuracy {N['wb_accuracy']} vs status points ÷ (tested × 10) {N['wb_points_accuracy']}")
        check("Words known = Good + Mastered", N["wb_known"] == N["status"].get("Good", 0) + N["status"].get("Mastered", 0),
              f"Words known {N['wb_known']} but Good {N['status'].get('Good', 0)} + Mastered {N['status'].get('Mastered', 0)}")
        check("word statuses in their bands", N["band_problem_count"] == 0, f"{N['band_problem_count']} forms sit outside the band their latest-10 score gives (e.g. {N['band_problems'][:1]})")
        if slips_doc:
            n_cards = sum(1 for x in L for e in D[x["date"]].get("vocab_errors", []) if e.get("source") == "audit-2026-09-26" and e.get("on_sheet"))
            check("every on-list word slip is in the Word Bank or listed", N["slips_in_models"] + len(counted_unplaced) == n_cards,
                  f"{n_cards} on-list word slips on the Lessons page, {N['slips_in_models']} scored in the Word Bank + {len(counted_unplaced)} listed as not placed")
        # 6. decision 4
        ax = {a["date"]: a["approx"] for a in N["approx"]}
        for x in L:
            rel = x.get("release") or {}
            ver = rel.get("status") == "verified"
            check(f"{x['date']} has a release state", rel.get("status") in ("verified", "not verified") and (ver or rel.get("reasons")),
                  f"{x['date']}: no verified / not verified state with reasons (scripts/accuracy_gates.py annotate)")
            check(f"{x['date']} ≈ when not verified", ax.get(x["date"]) == (not ver),
                  f"{x['date']}: {'not verified' if not ver else 'verified'} but the pages {'do not show' if not ver else 'show'} ≈")
            check(f"{x['date']} no verified % when not verified", ver or (x["words"].get("verified_pct") is None and x["grammar"].get("verified_pct") is None),
                  f"{x['date']}: a verified % is stored for a lesson that is not verified")
    # both pages use the one averaging function
    for f in ("lessons-page.js", "lesson-overview.js"):
        src = open(os.path.join(REPO, "docs", "js", f), encoding="utf-8").read()
        check(f"{f} uses lesson-math", "pooledWords(" in src and "pooledGrammar(" in src,
              f"docs/js/{f} computes its own lesson averages instead of docs/js/lesson-math.js")
    return CHECKS


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--repo", default=REPO)
    a = ap.parse_args(argv)
    try:
        res = run(a.repo)
    except (OSError, ValueError, KeyError) as e:
        print(f"numbers: FAIL could not read the data ({type(e).__name__}: {str(e)[:160]})")
        return 2
    bad = [c for c in res if not c["ok"]]
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"checks": len(res), "failed": len(bad), "results": res}, f, ensure_ascii=False, indent=1)
    if a.verbose:
        for c in bad:
            print("  FAIL", c["detail"])
    print(f"numbers: OK {len(res)} checks" if not bad else f"numbers: FAIL {bad[0]['detail']}" + (f" (+{len(bad) - 1} more)" if len(bad) > 1 else ""))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
