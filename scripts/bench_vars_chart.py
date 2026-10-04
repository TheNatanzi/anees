# -*- coding: utf-8 -*-
"""Picture charts of the Gemini variables test (PR-18) from bench/<date>/variables/results.json.

    python scripts/bench_vars_chart.py 2026-10-02 [out_dir]      # variables/chart-heard.png, chart-harm.png, chart-cost.png
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_vars as BV  # noqa: E402

BLUE, GREY, INK, MUTED, GRID, SURF = "#2a78d6", "#8a8984", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
GOOD, BAD = "#008300", "#e34948"


def _ax(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", length=0, colors=MUTED, labelsize=9)
    ax.set_facecolor(SURF)


def charts(date, out_dir=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401
    R = BC.J(os.path.join(BV.vdir(date), "results.json"))
    out_dir = out_dir or BV.vdir(date)
    b, V = R["baseline"], [r for r in R["variables"] if not r["engine"].startswith("openai")]      # OpenAI (21 of 63, 223 lines changed) would flatten the scale
    rows = [b] + V
    names = [r["name"] for r in rows]
    y = list(range(len(rows)))[::-1]
    paths = []

    # 1. heard right, with the noise band around the baseline
    fig, ax = plt.subplots(figsize=(11, 0.5 * len(rows) + 1.8), facecolor=SURF)
    _ax(ax)
    ax.axvspan(b["heard_right"] - R["noise_moments"], b["heard_right"] + R["noise_moments"], color=GRID, alpha=0.7, lw=0)
    ax.axvline(b["heard_right"], color=GREY, lw=1, ls=(0, (3, 3)))
    ax.barh(y, [r["heard_right"] for r in rows], height=0.62, color=[GREY if r is b else BLUE for r in rows])
    for k, r in zip(y, rows):
        d = "" if (r is b or r["id"] == "v0") else "   %+d vs %s%s" % (r["delta"], "the row above" if r.get("compared_with") == "v0" else "baseline", " (noise)" if r["noise"] else "")
        ax.text(r["heard_right"] + 0.5, k, "%d%s" % (r["heard_right"], d), va="center", fontsize=9, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9, color=INK)
    ax.set_xlim(0, 80)
    ax.set_xlabel("Medi's corrected moments heard right (of 63). Grey band = run-to-run noise (+-%d)" % R["noise_moments"], fontsize=9, color=MUTED)
    ax.set_title("Each idea tried alone on the 10-02 lesson: did Gemini hear more of what you said?", fontsize=11, color=INK, loc="left")
    fig.tight_layout()
    p = os.path.join(out_dir, "chart-heard.png")
    fig.savefig(p, dpi=150, facecolor=SURF)
    plt.close(fig)
    paths.append(p)

    # 2. the two harms, side by side (two panels, one measure each)
    fig, axs = plt.subplots(1, 2, figsize=(12, 0.5 * len(rows) + 1.8), facecolor=SURF, sharey=True)
    for ax, key, title, mx in ((axs[0], "hidden_slips", "Your slips hidden (of %d) - lower is better" % b["slips_judged"], None),
                               (axs[1], "lines_words_changed", "Untouched lines changed (of 519) - lower is better", None)):
        _ax(ax)
        vals = [r[key] for r in rows]
        ax.axvline(b[key], color=GREY, lw=1, ls=(0, (3, 3)))
        ax.barh(y, vals, height=0.62, color=[GREY if r is b else BLUE for r in rows])
        for k, r in zip(y, rows):
            ax.text(r[key] + max(vals) * 0.02 + 0.05, k, str(r[key]), va="center", fontsize=9, color=INK)
        ax.set_xlim(0, max(vals) * 1.18 + 1)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.set_title(title, fontsize=10, color=INK, loc="left")
    axs[0].set_yticks(y)
    axs[0].set_yticklabels(names, fontsize=9, color=INK)
    fig.tight_layout()
    p = os.path.join(out_dir, "chart-harm.png")
    fig.savefig(p, dpi=150, facecolor=SURF)
    plt.close(fig)
    paths.append(p)

    # 3. dollars per variable (all 3 runs)
    S = [(r["name"], r["cost_usd"]) for r in R["variables"] if r["cost_usd"]]
    fig, ax = plt.subplots(figsize=(10, 0.45 * len(S) + 1.6), facecolor=SURF)
    _ax(ax)
    yy = list(range(len(S)))[::-1]
    ax.barh(yy, [v for _, v in S], height=0.62, color=BLUE)
    for k, (_, v) in zip(yy, S):
        ax.text(v + 0.03, k, "$%.2f" % v, va="center", fontsize=9, color=INK)
    ax.set_yticks(yy)
    ax.set_yticklabels([n for n, _ in S], fontsize=9, color=INK)
    ax.set_xlim(0, max(v for _, v in S) * 1.2)
    ax.set_title("Spend per idea, all runs, at list prices. Gemini $%.2f + OpenAI $%.2f" % (R["spend_gemini_usd"], R["spend_openai_usd"]), fontsize=11, color=INK, loc="left")
    fig.tight_layout()
    p = os.path.join(out_dir, "chart-cost.png")
    fig.savefig(p, dpi=150, facecolor=SURF)
    plt.close(fig)
    paths.append(p)
    return paths


if __name__ == "__main__":
    for p in charts(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(p)
