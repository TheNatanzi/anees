# Anees transcription-first tools

Additive takeover work for the Sep 5, 2026 lesson. These commands do not call the old lesson ingest, downstream analysis, publishing, email, or Amal-link flows. Existing raw transcripts remain untouched.

## Review first

The generated `review.html` is a **private, self-contained file with embedded lesson audio**, not a public GitHub Pages asset. Medi can pass that one file to Amal. Each chooses their own reviewer name. Use the separate-track audio when attribution is unclear. Download review JSON before closing, especially on Android/local-file browsers where browser storage may not persist. Import both reviewers' JSON files to preserve their separate answers. No auto-submit or external backend is used.

The interface retains raw fillers, malformed words and model event tags. It does not guess Arabic-to-Arabizi spelling or silently correct learner attempts. Medi may leave unreadable Arabic pending; Amal can supply Arabic wording. Source-track names identify the participant channel, not biometric certainty about every sound. Boundary-crossing spans remain provisional.

There are twenty 25-second windows: eight candidate tutor recasts, four explicit recall/word questions, four false starts, four seeded Arabic-script-heavy random windows. These were selected after inspecting cached baselines and frozen before fresh experiment responses. This is a deliberately difficult diagnostic set, not an unbiased or unseen estimate of whole-lesson accuracy. A/B order is randomized, but speaker labels can reveal source type; this is not a strictly blinded trial.

Twenty windows contain 8 minutes 20 seconds of audio before replaying or editing. The first careful review is not promised to fit in five minutes; subset review and resume are supported.

## Rebuild without paid calls

```powershell
python scripts/transcription_first/transcription_review.py --repo C:/dev/anees --output C:/dev/anees/data/lessons/2026-09-05/transcription-first/review
```

Existing raw evidence, clip hashes and window manifest must match. If a developer intentionally changes derived run segmentation before collecting reviews, `--rebuild-derived` saves the previous derived JSON and updates the page. Never use it casually after reviews exist: run identity changes require explicit migration; imported mismatched records are rejected.

## Score submitted human reviews

```powershell
python scripts/transcription_first/transcription_score.py --data C:/dev/anees/data/lessons/2026-09-05/transcription-first/review/review-data.json --output C:/dev/anees/data/lessons/2026-09-05/transcription-first/review/scored --reviews C:/path/to/Medi-review.json C:/path/to/Amal-review.json
```

With no `--reviews`, the output is explicitly pending with null accuracy and zero gold references. Outputs are `score.json` and `candidate-gold.json`. Confirmed wording is a reviewer assertion, not automatically adjudicated truth. Conflicts, incomplete spans, unsupported speaker identity and uncertain text remain visible. A/B candidates do not become a consensus by agreeing.

## Paid experiments

See `EXPERIMENT-RUNNER.md`. Execution is not automatic. It requires a fresh account-matched no-training attestation, credentials from the environment, budget reservation and the explicit `--execute` flag. Existing batch artifacts prevent blind repeat calls. Historical raw baselines and the budget ledger are never replaced by experiment results.

The archived Sep 7 execution manifest retains the original output paths in the Codex workspace for provenance. To inspect the archived results, use the analysis script. Do not start another paid batch in a relocated directory merely to reproduce a report; changing output directories can invalidate the original request manifest and requires deliberate reconciliation.

## Tests

```powershell
python -m unittest discover -s scripts/transcription_first -p "test*.py" -v
```

Tests use synthetic fixtures and mocks, never paid calls or human approval. The complete existing application suite is not invoked by these tools; some legacy tests write shared timing data, and downstream features are out of scope.

## Boundaries

No provider choice is promoted based on text agreement alone. No phonetic accuracy, dialect correctness, learner-error preservation or speaker accuracy is claimed without audio-linked human confirmation. No downstream reports, flashcards, homework, pause scoring, or messages to Amal are triggered. The original displayed lesson remains available; this separate review page is the evidence-preserving working surface for this milestone.
