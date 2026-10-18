# Codex task (Medi 2026-10-16: "Ask codex 6 to do the same")

Goal: find a way to combine the EXISTING slip-reader outputs that scores higher than 80.6 held-out F0.5. Target 90.

Rules (non-negotiable):
- NO network, NO API keys, NO new model calls. Work only with files already in this repo.
- Score ONLY with scripts/reader_tiers.py (key_slips, predicted, match, prf). Never edit the answer keys
  (data/lesson-work/review-grades/*.json).
- Leave-one-lesson-out: tune on 2 of the 3 lessons (2026-10-08, 10-09, 10-10), score the 3rd, rotate. The pooled held-out
  number is THE score. A number tuned and scored on the same lesson does not count.
- Grade-book rule (PR-27): slips whose signal is "asked", and A-kind slips with signal "none", never count (set RE_DROP=asked,none).

What exists:
- Reader runs: data/lesson-work/reader-tiers/runs/<date>.<tag>-run1.json (Claude, Gemini, OpenAI; some with -r2..-r5 repeats).
- Judge verdicts on every candidate: data/lesson-work/reader-tiers/overnight-2026-10-17/judge/<date>.<model>.<variant>.json
- Tools: scripts/reader_ensemble.py (clusters, vote, stack, lolo, log), scripts/reader_judge.py (candidates, score, stack).
- Results so far: overnight-2026-10-17/attempts.jsonl. Best: judge panel Opus + Gemini 3.7 Flash, plain, mean = 80.6.
- Research memo: overnight-2026-10-17/research-memo.md.

Do: try at least 8 new combination ideas of your own (e.g. per-signal thresholds, per-family models, judge-reason features,
reader-reliability weights learned per signal, abstain bands, rank fusion, small decision trees). Log each to attempts.jsonl
with "method": "codex: ...". Write your findings to overnight-2026-10-17/CODEX-FINDINGS.md: a table of every idea, its
held-out F0.5, precision, recall, and one line on why it helped or not. Be honest if nothing beats 80.6.
