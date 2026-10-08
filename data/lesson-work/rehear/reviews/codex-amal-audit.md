Read-only audit completed; no edits or network. Six checks covered, with in-memory reproductions.

**BLOCKERS**

- **Proposal results depend on which run errors.** With run 1 errored and runs 2–3 agreeing on a changed span but differing elsewhere, `decide()` returns no proposal. Moving the error to run 3 produces the proposal. Missing answers become engine text, then an engine-first tie skips span voting. Fix that early exit. [rehear_amal.py:110](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:110), [bench_piles.py:166](/C:/dev/anees-wt-bench/scripts/bench_piles.py:166)

**SHOULD-FIX**

- `pump()` can retry permanent exceptions forever; persistent file/JSON errors have no retry limit. [rehear_amal.py:160](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:160)
- Frozen model/config are recorded but not validated; subsequent builds use live `BV.MODEL` and `P1_CFG`. Compare these with the manifest before building. [rehear_amal.py:73](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:73), [rehear_amal.py:90](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:90)
- English word changes are mislabeled “alphabet,” understating `check10()`’s changes. Reproduced with “I like it” → “I hate it.” The stricter mixed-recording hold still works. [rehear_amal.py:117](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:117), [bench_score.py:157](/C:/dev/anees-wt-bench/scripts/bench_score.py:157)

**CHECKED**

- **Model input:** only audio and fixed prompt; no engine text, benchmark answer key, correction, or contextual text. Batch line IDs sit outside the model request. [bench_run.py:281](/C:/dev/anees-wt-bench/scripts/bench_run.py:281), [batch_jobs.py:120](/C:/dev/anees-wt-bench/scripts/batch_jobs.py:120)
- **Money:** serialized allowance check before each new submission; unresolved creates cannot automatically purchase again; sequential recollection skips stored answers. [rehear_job.py:88](/C:/dev/anees-wt-bench/scripts/rehear_job.py:88), [batch_jobs.py:329](/C:/dev/anees-wt-bench/scripts/batch_jobs.py:329), [rehear_job.py:146](/C:/dev/anees-wt-bench/scripts/rehear_job.py:146)
- **Estimate:** 60 output tokens plus 15% reserve is reasonable against the verified ~22-token/$0.148 baseline; it remains an estimate, not a guaranteed spending ceiling. [rehear_amal.py:94](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:94), [rehear_job.py:73](/C:/dev/anees-wt-bench/scripts/rehear_job.py:73)
- **Pump/completion:** waits for purchased parts, limits retries to three parts, and requires all three runs complete before proposing. Stored engine errors count as completed responses, then are excluded from voting. [rehear_backfill.py:84](/C:/dev/anees-wt-bench/scripts/rehear_backfill.py:84), [rehear_amal.py:108](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:108)
- **IDs/mix/check10:** integer page IDs and string run keys align; all six benchmark IDs/times match. `A<i>` is correct; truth is read only for scoring. Mixed word changes are held. [bench_piles.py:163](/C:/dev/anees-wt-bench/scripts/bench_piles.py:163), [rehear_amal.py:118](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:118), [bench_score.py:289](/C:/dev/anees-wt-bench/scripts/bench_score.py:289)
- **Clips:** page timings use bounded fallback ends, padded ±0.6 seconds; own track requires full-window coverage, otherwise mix. Track offsets are subtracted correctly. [rehear_lesson.py:65](/C:/dev/anees-wt-bench/scripts/rehear_lesson.py:65), [rehear_amal.py:49](/C:/dev/anees-wt-bench/scripts/rehear_amal.py:49), [rehear_audio.py:80](/C:/dev/anees-wt-bench/scripts/rehear_audio.py:80)

VERDICT AMAL RUN: BLOCKED
