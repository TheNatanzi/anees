# -*- coding: utf-8 -*-
"""Medi's picture for the full audit: (1) grammar fixes per bucket, (2) vocab by tier, (3) before / after per lesson.
    python scripts/full_audit_chart.py  -> C:/Claude/reports/FULL-AUDIT-CHART-2026-09-26.png
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
A = json.load(open(os.path.join(REPO, "data", "full-audit-2026-09-26.json"), encoding="utf-8"))
OUT = "C:/Claude/reports/FULL-AUDIT-CHART-2026-09-26.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
T, BL = A["totals"], A["by_lesson"]
fig, ax = plt.subplots(1, 3, figsize=(17, 6.2), gridspec_kw={"width_ratios": [1.5, 0.8, 1.6]})
fig.patch.set_facecolor("#F5F6F2")
# 1 buckets
bk = list(A["by_bucket"].items())[:18]
ax[0].barh([b for b, _ in bk][::-1], [n for _, n in bk][::-1], color="#2E6A4E")
ax[0].set_title("Grammar fixes Amal voiced, by rule (top 18)", fontsize=11)
for i, (b, n) in enumerate(bk[::-1]):
    ax[0].text(n + 0.5, i, str(n), va="center", fontsize=9)
# 2 vocab tiers
tiers = ["0", "1", "2", "3"]
labels = ["asked her\n(tier 0)", "wrong word\n(1)", "wrong form\n(2)", "English\ninstead (3)"]
a = [T["vocab_A_by_tier"].get(t, 0) for t in tiers]
b = [T["vocab_B_by_tier"].get(t, 0) for t in tiers]
ax[1].bar(labels, a, color="#2E6A4E", label="A: she fixed it (scored)")
ax[1].bar(labels, b, bottom=a, color="#B26A1F", label="B: she let it pass (to Amal)")
for i in range(4):
    ax[1].text(i, a[i] + b[i] + 1, str(a[i] + b[i]), ha="center", fontsize=9)
ax[1].set_title("Vocab errors by tier", fontsize=11); ax[1].legend(fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.82)); ax[1].tick_params(axis="x", labelsize=8)
# 3 before / after per lesson
dates = list(BL.keys()); x = range(len(dates)); w = 0.2
ax[2].bar([i - 1.5 * w for i in x], [BL[d]["sweep_grammar_before"] for d in dates], w, color="#A9C4B4", label="grammar before (09-24 sweep)")
ax[2].bar([i - 0.5 * w for i in x], [BL[d]["grammar_A"] for d in dates], w, color="#2E6A4E", label="grammar now (A)")
ax[2].bar([i + 0.5 * w for i in x], [BL[d]["sweep_vocab_before"] for d in dates], w, color="#E6C9A8", label="vocab before")
ax[2].bar([i + 1.5 * w for i in x], [BL[d]["vocab_A"] + BL[d]["vocab_B"] for d in dates], w, color="#B26A1F", label="vocab now (A+B)")
ax[2].set_xticks(list(x)); ax[2].set_xticklabels([d[5:] for d in dates], rotation=45, fontsize=8)
ax[2].set_title("Per lesson: before the audit vs now", fontsize=11); ax[2].legend(fontsize=8)
for s in ax:
    s.set_facecolor("#FFFFFF"); s.spines[["top", "right"]].set_visible(False)
fig.suptitle(f"Full audit 2026-09-26 - grammar A {T['grammar_A']} (was {T['sweep_before']['grammar']}) - vocab A {T['vocab_A']} (was {T['sweep_before']['vocab']}; pages showed 23) - B for Amal: {T['vocab_B']} words + {T['grammar_B']} grammar", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT, dpi=150)
print("wrote", OUT)
