Read-only, offline; targeted checks ran in memory. No files changed.

1. **B-e: FIXED.** Cross-alphabet pairs require identical, non-empty skeletons; `katab / كذب` returns False. [rehear_lesson.py:247](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:247).
2. **Retries: FIXED.** Built retries submit; unfinished parts prevent new builds; collection precedes one missing-only retry; three exhausted parts raise. Both stages use `settle()`; `pump()` reports STOPPED and returns 1. [settle:114](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:114), [base:146](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:146), [two-clip:162](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:162), [termination:189](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:189).
3. **Cleanup: STILL OPEN.** Failed/cancelled/expired jobs bypass the collection requirement. Mocked `JOB_STATE_FAILED` without any collection marker still deletes requests; collection skips these states. [cleanup:134](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:134), [collect:132](C:/dev/anees-wt-bench/scripts/rehear_job.py:132).
4. **Seed: STILL OPEN, narrow edge.** Normal existing runs/jobs are refused, but an existing `{}` run file is overwritten because the guard checks truthiness, not existence. Fully stored runs correctly complete without a job; independently confirmed zero identical 10-02 requests. [guard:65](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:65), [local completion:198](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:198), [matching:61](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:61).
5. **Status: FIXED.** All three base runs must be submitted or stored before stamping the requested wording. [rehear_backfill.py:91](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:91).
6. **Re-cut gate: FIXED.** More than 15% skips the entire track. Current 09-10 manifest records **419/551**, not 393/551, and zero re-cuts. [gate:126](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:126), [manifest:571](C:/dev/anees-wt-bench/data/lesson-work/rehear/2026-09-10/manifest.json:571).

**NEW blocker:** None beyond the remaining gaps above.

**VERDICT B: BLOCKED.**
