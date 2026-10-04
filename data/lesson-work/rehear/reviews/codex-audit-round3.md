Read-only, offline audit complete. No files changed; targeted checks ran in memory.

- **A-chat — FIXED.** Distinct-line votes, ≥3 anchors, ≥60% non-adjacent rival rejection, winning-bin-only median. [rehear_gonly.py:83](C:/dev/anees-wt-bench/scripts/rehear_gonly.py:83)
- **A-log — FIXED.** Answers persist before logging; folder lookup prevents repeat logging after interruption; failed writes remain retryable; completion requires every build key stored. [rehear_job.py:158](C:/dev/anees-wt-bench/scripts/rehear_job.py:158), [rehear_job.py:185](C:/dev/anees-wt-bench/scripts/rehear_job.py:185)
- **A-create — FIXED.** Unresolved attempts block automatic recreation, retain their marker, and remain reserved. [batch_jobs.py:329](C:/dev/anees-wt-bench/scripts/batch_jobs.py:329), [batch_jobs.py:338](C:/dev/anees-wt-bench/scripts/batch_jobs.py:338), [rehear_job.py:64](C:/dev/anees-wt-bench/scripts/rehear_job.py:64)
- **A-gate — FIXED.** Requires three complete runs, evaluates the specified score/slip/timing checks, and saves the verdict. [rehear_gonly.py:307](C:/dev/anees-wt-bench/scripts/rehear_gonly.py:307), [rehear_gonly.py:322](C:/dev/anees-wt-bench/scripts/rehear_gonly.py:322)
- **B-b — FIXED.** Context includes every non-chat speaker. [rehear_lesson.py:78](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:78)
- **B-c — FIXED.** Guard preserves both standard-window boundaries. Intentional standard-clip overlap is accepted per your clarification. [rehear_lesson.py:93](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:93)
- **B-d — FIXED.** Every asked word must be covered and every returned `same` must be true; incomplete-subset check rejected in memory. [rehear_lesson.py:215](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:215)
- **B-e — STILL OPEN.** `content_change()` misses English word changes. Reproduced: mixed-source **“I like tea” → “I hate tea”** remains `proposed` with three agreeing runs. This violates alphabet-only proposals; use a comparison covering all words. [rehear_lesson.py:236](C:/dev/anees-wt-bench/scripts/rehear_lesson.py:236), [bench_score.py:157](C:/dev/anees-wt-bench/scripts/bench_score.py:157)
- **B-f — FIXED.** Whole-window containment replaces midpoint selection, with 50 ms tolerance; uncovered windows fall back to `mix`. [rehear_audio.py:80](C:/dev/anees-wt-bench/scripts/rehear_audio.py:80), [rehear_audio.py:93](C:/dev/anees-wt-bench/scripts/rehear_audio.py:93)

**NEW blockers:** None beyond the B-e bypass above.

**VERDICT A: OK TO RUN**  
**VERDICT B: BLOCKED**
