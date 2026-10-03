# -*- coding: utf-8 -*-
"""Scoreboard B of the engine benchmark (PR-18): how close would the lesson's Words % and Grammar % be if this engine's
transcript had been the lesson's transcript? Scratch mode only (ANEES_BENCH=1): everything in memory, one output file
under data/lesson-work/bench/<date>/b/ - no publish, no Supabase, no ledger write, no network.

    set ANEES_BENCH=1 && python scripts/bench_b.py 2026-10-02

What can be re-scored without re-running the paid AI readers (found 2026-10-03: the page's Words % is built from stored
word events and reader rows, which do not re-read a new transcript):
  uses    scripts/detect_grammar_usage.py's own detectors, run on the engine's text (the real counter, in memory)
  slips   the lesson's published grammar slips that are still visible in the engine's text (the wrong piece is on the
          line); a slip the engine hides or garbles would never have been found by the readers
  words   the lesson's published word rows (right / partial / wrong) whose word is still on the line in the engine's text
The same code scores Medi's corrected truth; the distance |engine - truth| is the scoreboard. It cannot see NEW false
slips an engine's mishearings would add (10-02: المال for his المصاري became a false slip) - said in the report.
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402


def uses(date, turns, text_of):
    """Grammar rule uses on a transcript: the loop of detect_grammar_usage.__main__ for one lesson, in memory."""
    import detect_grammar_usage as D
    T = [{"speaker": u["who"], "start": u["t"], "end": u.get("end") or u["t"] + 2, "text": text_of(k, u)} for k, u in enumerate(turns) if u["who"] != "chat"]
    rulings = D.load_rulings()
    seen, read = collections.Counter(), {}

    def add(t, bid, hit, back):
        if back:
            hit = D.unmask(hit, back)
        if not D.ruled(rulings, date, bid, t["start"], hit):
            seen[bid] += 1

    for i, t in enumerate(T):
        if t["speaker"] != "Medi":
            continue
        txt, back, read_as = D.read_turn(t)
        if txt is None:
            continue
        read[i] = (txt, back, read_as)
        if D.asks_about_rule(t["text"]):
            continue
        found = D.detect(txt)
        if "E5" in found and D.asks_again(T, i, txt):
            del found["E5"]
        for bid, hit in found.items():
            add(t, bid, hit, back)
    for run in D.stretches(T):
        run = [i for i in run if not D._is_farsi(T[i]["text"])]
        if len(run) < 2 or not any(i in read for i in run):
            continue
        raw, back = D.mask_names(" , ".join(T[i]["text"] for i in run))
        joined = D.to_arabic(raw)
        singles = [read[i][0] for i in run if i in read]
        for bid, hit in D.detect(joined, only=D.JOIN_RULES).items():
            if any(hit in s_ for s_ in singles):
                continue
            first = hit.split()[0]
            at = next((i for i in run if i in read and first in read[i][0]), run[0])
            add(T[at], bid, hit, back)
    return dict(seen)


def on_line(piece, t, medi, text_of_line):
    """Is the piece (word or phrase) still in the engine's text of his line(s) at t (+-3 s)?"""
    want = set(BC.tokens(piece.split("(")[0])) | set(BC.tokens(BC.latin_to_arabic(piece.split("(")[0])))
    want = {w for w in want if w}
    if not want:
        return True
    have = set()
    for ln in medi:
        if abs(ln["t"] - t) <= 3.0 or (ln["t"] <= t <= ln["end"]):
            r, c = BS.views(text_of_line(ln["i"]))
            have |= set(r) | set(c)
    ar = {w for w in want if BC.is_ar(w)} or want
    return ar <= have


def board(date, page, truth, text_of_line):
    medi = truth["lines"]
    by_i = {ln["i"]: ln for ln in medi}
    u = uses(date, page["turns"], lambda k, t: text_of_line(k) if k in by_i else (t.get("engine") or t["text"]))
    kinds = collections.Counter()
    for r in page.get("vocab_correct", []) + page.get("vocab_errors", []):
        if r["kind"] == "asked":
            kinds["asked"] += 1                                    # he asked Amal for the word: not read off his words
        elif on_line(r.get("wrong") if r["kind"] == "wrong" else (r.get("arabic") or ""), r["t"], medi, text_of_line):
            kinds[r["kind"]] += 1
    scored = sum(kinds.values())
    slips = sum(1 for g in page.get("grammar_errors", []) if on_line(g.get("wrong") or g.get("said") or "", g["t"], medi, text_of_line))
    n_uses = max(sum(u.values()), slips)
    return {"words_pct": round(100.0 * (kinds["correct"] + 0.5 * (kinds["partial"] + kinds["asked"])) / scored, 1) if scored else None,
            "words_right": kinds["correct"], "words_partial": kinds["partial"] + kinds["asked"], "words_wrong": kinds["wrong"],
            "grammar_pct": round(100.0 * (n_uses - slips) / n_uses, 1) if n_uses else None,
            "uses": sum(u.values()), "grammar_slips": slips, "slips": slips + kinds["wrong"], "by_bucket": u}


def main(argv):
    if os.environ.get("ANEES_BENCH") != "1":
        raise SystemExit("scratch mode only: set ANEES_BENCH=1 (no publish, no Supabase, no ledger writes)")
    date = argv[0]
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    page = BC.J(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json"))
    lines = {ln["i"]: ln for ln in truth["lines"]}
    out = {"truth": board(date, page, truth, lambda i: lines[i]["truth"])}
    T = out["truth"]
    print("%-28s words %5.1f%%  grammar %5.1f%%  slips %2d  uses %3d" % ("TRUTH (his corrections)", T["words_pct"], T["grammar_pct"], T["slips"], T["uses"]))
    for e in sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and x not in ("clips", "runs", "b", "vowel", "spend")):
        for mode in ("line", "whole"):
            runs = [r for r in BS.load_runs(d, e, mode) if r.get("complete", True)]
            if not runs:
                continue

            def text_of_line(i, runs=runs):
                outs = [r["lines"].get(str(i)) for r in runs]
                if all(o is None for o in outs):
                    return lines[i]["engine"]
                o, _ = BS.majority_text([x if x is not None else {"text": lines[i]["engine"]} for x in outs])
                return o.get("text") or ""
            b = board(date, page, truth, text_of_line)
            b["d_words"], b["d_grammar"] = round(abs(b["words_pct"] - T["words_pct"]), 1), round(abs(b["grammar_pct"] - T["grammar_pct"]), 1)
            b["d_slips"], b["d_uses"], b["runs"] = abs(b["slips"] - T["slips"]), abs(b["uses"] - T["uses"]), len(runs)
            out["%s|%s" % (e, mode)] = b
            print("%-22s %-5s words %5.1f%% (d %4.1f)  grammar %5.1f%% (d %4.1f)  slips %2d  uses %3d" % (e, mode, b["words_pct"], b["d_words"], b["grammar_pct"], b["d_grammar"], b["slips"], b["uses"]))
    BC.W(os.path.join(d, "b", "scoreboard-b.json"), out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
