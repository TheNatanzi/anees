# Offline combination experiments

**Best: 82.1 pooled held-out F0.5, versus the reproduced 80.6 baseline. Target 90 was not reached.**

The best method matched 68 of 102 key slips with 78 predictions: precision 87.2%, recall 66.7%. The baseline also matched 68, but made 80 predictions. This is a 1.5-point exploratory gain, not proof of improvement on a new lesson.

## Every experiment

All numbers are percentages, pooled across held-out predictions for October 8, 9 and 10. Explanations describe observed changes versus the baseline; they are not causal findings.

| Idea | Held-out F0.5 | Precision | Recall | What happened |
|---|---:|---:|---:|---|
| Baseline: Opus + Flash plain mean | 80.6 | 85.0 | 66.7 | Reproduced the task's baseline exactly: 68 matches, 80 predictions, 102 key slips. |
| Signal-specific panel thresholds | 77.8 | 82.3 | 63.7 | Separate offsets for recasts and explicit correction signals lost three matches and added two false positives. |
| Family-specific panel thresholds | 78.0 | 83.1 | 62.7 | Separate vocab/grammar cutoffs lost four matches, mostly on October 8. |
| Judge disagreement penalty | 80.1 | 84.8 | 65.7 | Penalizing disagreement lost one match; two folds selected no penalty. |
| Reader support rescues abstain band | 81.3 | 86.8 | 64.7 | Four fewer predictions improved precision, but October 10 recall fell to 48%. |
| Judge reason penalty and correction bonus | 79.7 | 84.6 | 64.7 | Fixed English reason keywords lost two matches; two folds selected no adjustment. |
| Repeat stability blended with panel | 75.9 | 81.3 | 59.8 | Five cached Flash repeats lost seven matches when blended into the panel score. |
| Robust median across four plain judges | 76.9 | 80.0 | 66.7 | Same match count, five more false positives; extra judges did not help. |
| Plain and defence geometric fusion | 79.2 | 82.4 | 68.6 | Gained two matches but added three false positives. |
| Four-judge percentile rank fusion | 78.2 | 84.7 | 59.8 | Ranking within each lesson lost seven matches without a precision gain. |
| Signal-conditioned reader reliability blend | 79.1 | 85.1 | 61.8 | Training-only smoothed reader weights lost five matches; precision barely changed. |
| Compact regularized reason and repeat stack | 80.2 | 88.2 | 58.8 | Better precision cost eight matches, leaving F0.5 below baseline. |
| **Family regularized reason and repeat stack** | **82.1** | **87.2** | **66.7** | Family interactions retained the baseline's total matches with two fewer false positives. |

## Best method

Logistic regression uses nine features, including the intercept:

1. Intercept.
2. Mean Opus/Flash plain judge probability.
3. Fraction of the eight original readers supporting the candidate.
4. Fraction of five cached Flash runs flagging the same family within the existing 15-second window.
5. Grammar-family indicator.
6. Negative reason-keyword indicator.
7. Correction reason-keyword indicator.
8. Panel mean multiplied by the grammar indicator.
9. Reader support multiplied by the grammar indicator.

Weights, L2 strength and threshold are fitted/selected using only the other two lessons. L2 candidates are 1, 10 and 100; all folds selected 1. Threshold candidates are 0.10 through 0.95 in steps of 0.05. All fits use the existing `reader_ensemble.fit` implementation, 400 iterations and learning rate 0.3.

| Held-out lesson | Training lessons | Selected threshold | Matched / predicted / key | F0.5 | Baseline F0.5 |
|---|---|---:|---|---:|---:|
| 2026-10-08 | 10-09, 10-10 | 0.65 | 23 / 24 / 34 | 88.5 | 88.0 |
| 2026-10-09 | 10-08, 10-10 | 0.60 | 29 / 33 / 43 | 82.9 | 78.9 |
| 2026-10-10 | 10-08, 10-09 | 0.65 | 16 / 21 / 25 | 73.4 | 73.4 |
| **Pooled** | | | **68 / 78 / 102** | **82.1** | **80.6** |

There is no single independently validated deployment threshold or weight vector here: these are three different training fits. Most of the gain came from October 9. October 10 remains weak.

## Evaluation and safeguards

- The complete menu of 12 new ideas and parameter grids was implemented before any new experiment result was observed. All 12 are reported, including failures; the baseline is an additional row.
- Each fold tunes on two lessons, generates predictions for the third, and only then accesses that third lesson's key. The final score pools counts, rather than averaging lesson F0.5 values. Training selection uses the scorer's rounded F0.5 with a deterministic first-in-grid tie break.
- `reader_tiers.key_slips`, `predicted`, `match` and `prf` provide all conversion and scoring. The matcher, answer keys, timestamps and families were not changed.
- `RE_DROP=asked,none` is set before importing the ensemble. Candidate membership follows the supplied ensemble's exact filter, including its exclusion of every `none` signal. Cached judge IDs retain the original eight-reader clustering and ordering. There are 55, 69 and 43 candidates respectively.
- Supervised candidate labels use the official matcher on individual candidates from training lessons only. Individual labels can overlap the same key moment; threshold selection and all reported metrics use full one-to-one matching. This is a limitation of the training surrogate, not relaxed evaluation.
- All models are combined from existing local files. No network, API keys, subprocess model calls or new model inference were used. The runner does not import the vendor or judge execution modules. Every Python invocation used `python -I`.
- `codex-results.json` records input SHA-256 hashes, every fold's parameters, predictions and metrics. The runner verifies all input hashes again before saving. All review-grade JSON files were included in that check and remained unchanged.
- The attempts log contains an older 105-key result as well as the 102-key baseline. This experiment uses the untouched current 102-key set and reproduces 80.6; the 105-key entry was not used as a comparator.
- Repeatedly comparing methods on these same three held-out lessons creates selection optimism. The best-of-12 result is exploratory even though each individual method obeys LOLO. Validate this fixed feature recipe on a new untouched lesson before adopting it. No claim of statistical significance or a 90-point result is made.

## Reproduce and inspect

Run from the repository:

```powershell
python -I scripts/reader_codex_combinations.py
```

This overwrites `codex-results.json` and appends another complete run to `attempts.jsonl`; it never edits keys. Every appended method starts with `codex: `. The source defines the exact grids and reason-keyword lists. The manifest includes hashes for all inputs, including unused cached judge variants loaded for integrity checks.

Deliverables: this report, `codex-results.json`, 13 appended log rows (12 new ideas plus baseline), and `scripts/reader_codex_combinations.py`.

## Task completion and validation

- [x] Read CODEX-TASK.md and followed its offline scope.
- [x] Tried at least eight original combinations: twelve completed.
- [x] Rotated training on two lessons and scoring the third; pooled the held-out counts.
- [x] Applied `RE_DROP=asked,none`, used only the existing scorer, and preserved all answer keys.
- [x] Logged every idea with `method: codex: ...` and reported F0.5, precision, recall and an explanation.
- [x] Used `python -I` for scripts; no network or paid runs.

This is the manual Codex checklist permitted by `scripts/session_asks.py`, whose transcript reader supports Claude Code sessions only. There were no new moment corrections to register; this request is an offline experiment, not a ruling change.

Post-run validation passed: independently rescored all 39 saved folds and their pooled metrics with `reader_tiers`, checked all 13 records appear in the log, verified each fold's training/test separation, and rechecked SHA-256 hashes for 104 input files including the answer keys.

Repository-wide `python -I -X utf8 scripts/rule_registry.py check` failed on existing missing entries AM-33 and PR-27. Neither the registry nor its baseline was changed in this task. No push or publish was attempted; network access was prohibited.
