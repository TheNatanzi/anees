# -*- coding: utf-8 -*-
"""The benchmark's tables (PR-18): scores.json + scoreboard-b.json + the run files' dollars -> markdown tables and a chart.

    python scripts/bench_report.py 2026-10-02            # prints the tables; writes bench/<date>/tables.md and chart.png
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

LISTEN = ("gemini-flash", "gemini-pro", "openai-audio")
NAMES = {"eleven-raw": "ElevenLabs Scribe v2 (today's transcript)", "eleven": "ElevenLabs Scribe v2 (fresh runs)", "openai-stt": "OpenAI gpt-transcribe",
         "openai-4o": "OpenAI gpt-4o-transcribe", "speechmatics": "Speechmatics ar_en enhanced", "deepgram-ar": "Deepgram nova-3 (ar)",
         "deepgram-multi": "Deepgram nova-3 (multi)", "cohere-api": "Cohere transcribe-03-2026 (API, ar)", "cohere-open": "Cohere transcribe-arabic-07-2026 (local, ar)",
         "audar-open": "Audar ASR V1 Turbo (local, auto)", "audar-open-ar": "Audar ASR V1 Turbo (local, forced ar)", "gemini-transcribe": "Gemini 3.5 Transcribe",
         "gemini-flash": "Gemini 3.8 Flash + context", "gemini-flash-before": "Gemini 3.8 Flash, context before only",
         "gemini-pro": "Gemini 3.1 Pro + context", "gemini-pro-before": "Gemini 3.1 Pro, context before only",
         "gemini-flash-t1": "Gemini 3.8 Flash + context, temperature 1", "gemini-flash-batch-t1": "Gemini 3.8 Flash + context, temperature 1, Batch mode (half price)",
         "gemini-pro-t0": "Gemini 3.1 Pro + context, temperature 0",
         "openai-audio": "OpenAI gpt-audio-1.5 + context", "openai-audio-before": "OpenAI gpt-audio-1.5, context before only",
         # the variables test of 2026-10-04 (scripts/bench_vars.py): Flash + context, temperature 1, one idea changed
         "gemini-flash-v1-t1": "Flash V1 evidence (heard / inferred)", "gemini-flash-v1h-t1": "Flash V1, only 'heard' changes kept",
         "gemini-flash-v2-t1": "Flash V2 forced choice", "gemini-flash-v3-t1": "Flash V3 two clips", "gemini-flash-v4-t1": "Flash V4 word confidence",
         "gemini-flash-v4h-t1": "Flash V4, only high-confidence changes kept", "gemini-flash-v5-t1": "Flash V5 second guess",
         "gemini-flash-v6-t1": "Flash V6 Arabic span in long lines", "gemini-flash-v7-t1": "Flash V7 accent note", "gemini-flash-v8-t1": "Flash V8 word list, said + meant",
         "gemini-flash-v9-t1": "Flash V9 thinking high (224 lines, 2 runs)", "gemini-flash-v0-t1": "Flash baseline on V9's 224 lines (2 runs)",
         "gemini-flash-v10-t1": "Flash V10 vowel marks in the text", "gemini-flash-v11-t1": "Flash V11 one-field answer", "gemini-flash-v12-t1": "Flash V12 guessing lines removed",
         "gemini-flash-best-t1": "Flash best recipe (word list + said/meant + marks apart)", "openai-audio-best": "OpenAI gpt-audio-1.5, best recipe"}
SCRIPT_ONLY = ("latin-arabic",)                      # the engine wrote his Arabic in English letters: a script fault, not a mishearing


def rows(date):
    d = BC.bench_dir(date)
    S = BC.J(os.path.join(d, "scores.json")) or {}
    B = BC.J(os.path.join(d, "b", "scoreboard-b.json")) or {}
    out = []
    for k, s in S.items():
        e, mode = k.split("|")
        real = [p for p in s["per_moment"] if p["class"] not in SCRIPT_ONLY]
        lat = [p for p in s["per_moment"] if p["class"] in SCRIPT_ONLY]
        out.append({"key": k, "engine": e, "mode": mode, "name": NAMES.get(e, e), "listener": re.sub(r"(-before|-t0|-t1|-v\d+h?|-best|-batch)+$", "", e) in LISTEN, "s": s, "b": B.get(k),
                    "real": (sum(p["final"] == "hit" for p in real), len(real)), "latin": (sum(p["final"] == "hit" for p in lat), len(lat))})
    out.sort(key=lambda r: (r["listener"], -r["s"]["hit"], r["s"]["false_changes"]))
    return out, B.get("truth")


def tables(date):
    R, T = rows(date)
    L = []
    for title, pick in (("Plain transcribers (audio only)", False), ("Listeners (audio + lesson context)", True)):
        L += ["", "### A - %s" % title, "",
              "| Engine | Mode | Heard right (of 63) | Real mishearings fixed (of 32) | English-letter Arabic fixed (of 31) | Slips hidden (of 24) | Lines changed of 519 (words changed, not just the alphabet) | All Arabic words right | Wrong alphabet lines | Same answer 3 of 3 | Runs | Sec / lesson | Cost |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in R:
            if r["listener"] != pick:
                continue
            s = r["s"]
            secs = sum(s.get("seconds") or [0]) / max(1, len(s.get("seconds") or [1]))
            L.append("| %s | %s | **%d** (%s%%) | %d | %d | %d | %d (%s%%) | %s%% | %d | %s%% | %d | %.0f | $%.2f |" % (
                r["name"], "per line" if r["mode"] == "line" else "whole file", s["hit"], s["hit_pct"], r["real"][0], r["latin"][0], s["hidden_slips"],
                s["false_changes"], s["false_change_pct"], s["all_lines_pct"], s["language_switch_lines"], s["stable_pct"], s["runs"], secs, s["cost_usd"]))
            L[-1] = L[-1].replace("| %d (%s%%) | %s%% |" % (s["false_changes"], s["false_change_pct"], s["all_lines_pct"]), "| %d (words: %d) | %s%% |" % (s["false_changes"], s["content_changes"], s["all_lines_pct"]))
    L += ["", "### B - score closeness (truth: Words %s%%, Grammar %s%%, %s slips, %s uses)" % (T["words_pct"], T["grammar_pct"], T["slips"], T["uses"]) if T else "", "",
          "| Engine | Mode | Words % | off by | Grammar % | off by | Slips still visible | Uses counted |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted((r for r in R if r["b"]), key=lambda r: r["b"]["d_words"] + r["b"]["d_grammar"]):
        b = r["b"]
        L.append("| %s | %s | %s | %s | %s | %s | %d | %d |" % (r["name"], "per line" if r["mode"] == "line" else "whole file", b["words_pct"], b["d_words"], b["grammar_pct"], b["d_grammar"], b["slips"], b["uses"]))
    classes = sorted({p["class"] for r in R for p in r["s"]["per_moment"]})
    L += ["", "### A by kind of mistake (moments heard right)", "", "| Engine | Mode | " + " | ".join(classes) + " |", "|---|---|" + "---|" * len(classes)]
    for r in R:
        bc = r["s"]["by_class"]
        L.append("| %s | %s | %s |" % (r["name"], "line" if r["mode"] == "line" else "whole", " | ".join("%d/%d" % tuple(bc.get(c, [0, 0])) for c in classes)))
    L += ["", "### Amal's 6 corrected lines (plain transcribers on her clips)", "", "| Engine | Heard right (of 6) |", "|---|---|"]
    for r in R:
        if r["mode"] == "line" and not r["listener"] and r["s"].get("amal"):
            L.append("| %s | %d |" % (r["name"], r["s"]["amal"]["hit"]))
    return "\n".join(L), R


def chart(date, R):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return None
    best = {}
    for r in R:                                                    # one bar per engine: its better mode
        if r["engine"] not in best or r["s"]["hit"] > best[r["engine"]]["s"]["hit"]:
            best[r["engine"]] = r
    X = sorted(best.values(), key=lambda r: r["s"]["hit"])
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(X) + 1.6))
    y = range(len(X))
    ax.barh(y, [r["real"][0] for r in X], color="#2a78d6", label="real mishearings fixed (of 32)")
    ax.barh(y, [r["latin"][0] for r in X], left=[r["real"][0] for r in X], color="#9ec5f4", label="English-letter Arabic fixed (of 31)")
    for k, r in enumerate(X):
        ax.text(r["s"]["hit"] + 0.6, k, "%d  |  %d untouched lines with a word changed, %d slips hidden" % (r["s"]["hit"], r["s"]["content_changes"], r["s"]["hidden_slips"]), va="center", fontsize=8, color="#333")
    ax.set_yticks(list(y))
    ax.set_yticklabels([r["name"] + (" [whole]" if r["mode"] == "whole" else "") for r in X], fontsize=8)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Medi's corrected moments heard right (of 63), lesson 2026-10-02")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    p = os.path.join(BC.bench_dir(date), "chart.png")
    fig.savefig(p, dpi=150)
    return p


def spend(date):
    """Real dollars per engine from the per-call run lines (includes calls whose answer was lost when a job was stopped)."""
    import collections, glob, gzip
    d = os.path.join(BC.bench_dir(date), "runs")
    usd, calls = collections.Counter(), collections.Counter()
    files = glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True)
    gz = os.path.join(BC.bench_dir(date), "runs.jsonl.gz")           # the first benchmark's run lines, packed; later jobs add runs/
    if os.path.exists(gz):
        files.append(gz)
    for f in files:
        with (gzip.open if f.endswith(".gz") else open)(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                k = (r.get("step") or "").replace("bench.", "")
                usd[k] += r.get("cost_usd") or 0
                calls[k] += 1
    return {k: {"usd": round(usd[k], 2), "calls": calls[k]} for k in sorted(usd)}


def results(date, R, T):
    """One file for the AI Reports page: every engine, every number, every moment's verdict per run."""
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    man = BC.J(os.path.join(d, "manifest.json"))
    vowel = {}
    vd = os.path.join(d, "vowel")
    for f in sorted(os.listdir(vd)) if os.path.isdir(vd) else []:
        if f.endswith(".json"):
            v = BC.J(os.path.join(vd, f))
            vowel[v["model"]] = [{k: r.get(k) for k in ("word", "who", "run", "ok", "error")} | {"heard": (r.get("answer") or {}).get("word_as_pronounced"), "first_vowel": (r.get("answer") or {}).get("first_vowel")} for r in v["rows"]]
    out = {"benchmark": "PR-18 speech-engine benchmark", "lesson": date, "built": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
           "truth_sha256": man["truth_sha256"], "clips_sha256": man["clips_sha256"], "prompts_sha256": man["prompts_sha256"], "counts": truth["counts"],
           "moments": [{k: m[k] for k in ("id", "t", "class", "want", "gone", "note")} for m in truth["moments"]],
           "truth_board_b": T, "spend": spend(date), "vowel": vowel,
           "gemini_pro_partial": BC.J(os.path.join(d, "gemini-pro", "partial-compare.json")),
           "engines": [{"id": r["engine"], "mode": r["mode"], "name": r["name"], "class": "listener" if r["listener"] else "plain", "model": r["s"].get("model"),
                        "runs": r["s"]["runs"], "heard_right": r["s"]["hit"], "of": r["s"]["moments"], "real_mishearings_fixed": list(r["real"]), "latin_letter_arabic_fixed": list(r["latin"]),
                        "verdicts": r["s"]["verdicts"], "by_class": r["s"]["by_class"], "hidden_slips": r["s"]["hidden_slips"], "slips_judged": r["s"]["slips_judged"],
                        "lines_changed": r["s"]["false_changes"], "lines_words_changed": r["s"]["content_changes"], "should_stay": r["s"]["should_stay"],
                        "all_lines_pct": r["s"]["all_lines_pct"], "wrong_alphabet_lines": r["s"]["language_switch_lines"], "bleed_words": r["s"]["bleed_words"],
                        "same_3_of_3_pct": r["s"]["stable_pct"], "lines_2of3_agree_pct": r["s"]["lines_2of3_agree_pct"], "call_errors": r["s"]["call_errors"],
                        "lines_sent": r["s"]["lines_sent"], "seconds": r["s"].get("seconds"), "amal_lines_right": (r["s"].get("amal") or {}).get("hit"),
                        "board_b": r["b"], "per_moment": r["s"]["per_moment"], "hidden_rows": r["s"]["hidden_rows"]} for r in R]}
    BC.W(os.path.join(d, "results.json"), out)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    md, R = tables(sys.argv[1])
    open(os.path.join(BC.bench_dir(sys.argv[1]), "tables.md"), "w", encoding="utf-8", newline="\n").write(md + "\n")
    print(md)
    print(chart(sys.argv[1], R))
    res = results(sys.argv[1], R, rows(sys.argv[1])[1])
    print("spend:", json.dumps(res["spend"]))
