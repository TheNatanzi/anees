Read-only, offline audit; no edits. Targeted checks ran in memory.

- **B-e: STILL OPEN.** English substitution is fixed, but cross-alphabet comparison permits different words: test token `"katab" → "كذب"` returns `True`. `same_sound()` accepts a one-consonant difference, so alphabet-only protection remains bypassable. [rehear_lesson.py:235](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:235), [bench_common.py:155](C:/dev/anees-wt-bench/scripts/bench_common.py:155)

- **Seed: sound before submission**, given unchanged benchmark provenance: matching clip hashes and prompt text, with the same model/settings. Reused answers carry `$0` and `logged=True`; build excludes their keys. No duplicate charge/log from reuse itself. [rehear_backfill.py:61](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:61), [rehear_lesson.py:190](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:190)

- **Seed edge cases:** nothing prevents seeding after submission, when those requests are already purchased. Fully seeded runs remain incomplete and build an empty batch instead of completing locally. [rehear_backfill.py:65](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:65), [rehear_lesson.py:192](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:192)

- **Duplicate purchases: BLOCKER.** Same-name creation is guarded, but V3 retries use new names without waiting for existing parts. Mock reproduced `.p2`, `.p3`, `.p4` buying identical missing keys while all remained running. The allowance check still runs; it does not prevent this waste. [batch_jobs.py:315](C:/dev/anees-wt-bench/scripts/batch_jobs.py:315), [rehear_backfill.py:136](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:136)

- **Retry recovery/termination: BLOCKER.** A built-but-unsent base retry stalls because the “all DONE” condition never passes; V3 skips it by allocating another part. Exhaustion only prints “stopped,” leaving `pump()` looping indefinitely. [rehear_backfill.py:116](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:116), [rehear_backfill.py:154](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:154), [rehear_backfill.py:185](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:185)

- **Incomplete-run gate: passes.** Base collection requires every listen key, and proposal generation checks all base/V3 completion flags. Stored engine errors count as answers but cannot supply agreement. [rehear_lesson.py:201](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:201), [rehear_lesson.py:208](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:208), [rehear_lesson.py:335](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:335)

- **Cleanup: premature with outstanding retries.** Runs can complete while duplicate parts remain running; proposals then stop further collection and delete request JSONLs. Those parts’ eventual costs remain unreconciled. `missing_part()` also becomes unusable after deletion; retain originals until every part is terminal and collected. [rehear_backfill.py:140](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:140), [batch_jobs.py:133](C:/dev/anees-wt-bench/scripts/batch_jobs.py:133)

- **Status: PG-27’s applied boundary passes, wording does not.** “Sent … 3 runs” is stamped after only the first submission; “answers not back yet” is false for seeded answers. `proposed` follows proposal writing and explicitly says nothing is applied. [rehear_backfill.py:90](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:90), [rehear_backfill.py:142](C:/dev/anees-wt-bench/scripts/rehear_backfill.py:142)

**VERDICT B: BLOCKED — alphabet-only bypass, duplicate retry purchases, and retry recovery/termination failures.**
