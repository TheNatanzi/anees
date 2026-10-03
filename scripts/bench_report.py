# -*- coding: utf-8 -*-
"""The benchmark's tables (PR-18): scores.json + scoreboard-b.json + the run files' dollars -> markdown tables and a chart.

    python scripts/bench_report.py 2026-10-02            # prints the tables; writes bench/<date>/tables.md and chart.png
"""
import os, sys

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
         "openai-audio": "OpenAI gpt-audio-1.5 + context", "openai-audio-before": "OpenAI gpt-audio-1.5, context before only"}
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
        out.append({"key": k, "engine": e, "mode": mode, "name": NAMES.get(e, e), "listener": e.replace("-before", "") in LISTEN, "s": s, "b": B.get(k),
                    "real": (sum(p["final"] == "hit" for p in real), len(real)), "latin": (sum(p["final"] == "hit" for p in lat), len(lat))})
    out.sort(key=lambda r: (r["listener"], -r["s"]["hit"], r["s"]["false_changes"]))
    return out, B.get("truth")


def tables(date):
    R, T = rows(date)
    L = []
    for title, pick in (("Plain transcribers (audio only)", False), ("Listeners (audio + lesson context)", True)):
        L += ["", "### A - %s" % title, "",
              "| Engine | Mode | Heard right (of 63) | Real mishearings fixed (of 32) | English-letter Arabic fixed (of 31) | Slips hidden (of 24) | Lines wrongly changed (of 519) | All Arabic words right | Wrong alphabet lines | Same answer 3 of 3 | Runs | Sec / lesson | Cost |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in R:
            if r["listener"] != pick:
                continue
            s = r["s"]
            secs = sum(s.get("seconds") or [0]) / max(1, len(s.get("seconds") or [1]))
            L.append("| %s | %s | **%d** (%s%%) | %d | %d | %d | %d (%s%%) | %s%% | %d | %s%% | %d | %.0f | $%.2f |" % (
                r["name"], "per line" if r["mode"] == "line" else "whole file", s["hit"], s["hit_pct"], r["real"][0], r["latin"][0], s["hidden_slips"],
                s["false_changes"], s["false_change_pct"], s["all_lines_pct"], s["language_switch_lines"], s["stable_pct"], s["runs"], secs, s["cost_usd"]))
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
        ax.text(r["s"]["hit"] + 0.6, k, "%d  |  %d lines wrongly changed, %d slips hidden" % (r["s"]["hit"], r["s"]["false_changes"], r["s"]["hidden_slips"]), va="center", fontsize=8, color="#333")
    ax.set_yticks(list(y))
    ax.set_yticklabels([r["name"] + (" [whole]" if r["mode"] == "whole" else "") for r in X], fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Medi's corrected moments heard right (of 63), lesson 2026-10-02")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    p = os.path.join(BC.bench_dir(date), "chart.png")
    fig.savefig(p, dpi=150)
    return p


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    md, R = tables(sys.argv[1])
    open(os.path.join(BC.bench_dir(sys.argv[1]), "tables.md"), "w", encoding="utf-8", newline="\n").write(md + "\n")
    print(md)
    print(chart(sys.argv[1], R))
