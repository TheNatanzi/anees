# Run log: `data/runs/YYYY-MM.jsonl`

One JSON line per AI, scorer or build call. Written by `scripts/track.py`. Design: [AI engineering review, Tracking design §1](../../plan/AI-ENGINEERING-REVIEW-2026-09-27.md#tracking-design-three-append-only-logs-feed-one-dashboard-file).

**Rules**
- Append-only. A line is never edited; a correction is a new line.
- The repo is public: hashes, paths, counts, model ids, tokens and dollars only. Any string with Arabic letters or over 200 characters is stored as `sha256:<16 hex>`.
- Logging never blocks or fails a lesson publish.
- Two machines append here. `.gitattributes` sets `merge=union`, so a merge keeps both sides. `run_id` is unique per line.

**Who writes a line**

| step | kind | where |
|---|---|---|
| `full_audit.reader` (r1, r2), `full_audit.third_reader` (r3), `arabizi.fill_gaps`, `amal.patterns` | inference | `scripts/review_lesson.py` `claude()` |
| `scribe.transcribe` | ingest | `scripts/pipeline_ext.py` `transcribe_with_retry()` |
| `grammar_detector.score` | eval | `scripts/score_grammar_detector.py` |
| `sentence_ladder.build` | build | `scripts/build_sentence_ladder.py` |

**Fields**

| group | fields |
|---|---|
| identity | `schema`, `run_id`, `parent_id`, `trace_id` (`<lesson_date>\|<trigger>`), `kind` (inference/eval/build/ingest), `step`, `lesson_date`, `pass`, `role`, `trigger` (hourly/manual/overnight:<prompt file>), `host` (hash of the machine name) |
| what ran | `gen_ai.provider.name`, `gen_ai.request.model` (null = the CLI default), `gen_ai.response.model` (what the CLI reported), `tool_version`, `params`, `prompt_file`, `prompt_sha`, `code_sha`, `code_dirty` |
| data | `input_refs[{path,sha256}]`, `output_refs[{path,sha256,rows}]` |
| outcome | `status` (ok/error/timeout/empty_output/skipped_budget), `error_type`, `retries`, `started_at` (UTC), `duration_ms` |
| cost | `usage{input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens, audio_min, models{}}`, `cost_usd`, `cost_basis` (estimate = the CLI's own figure / list_price) |
| quality | `metrics{dataset, version, sha, n, recall, precision, f1, ...}`, `agreement{...}` |

**Env**: `ANEES_CLAUDE_MODEL` pins `claude -p --model` (unset = today's behaviour). `ANEES_TRIGGER`, `ANEES_PARENT_RUN_ID`, `ANEES_TRACE_ID`, `ANEES_HOST`. `ANEES_RUNS_DIR` redirects the log (tests; under pytest nothing is written without it).
