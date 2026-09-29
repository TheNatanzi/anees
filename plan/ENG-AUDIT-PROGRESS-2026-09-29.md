# Engineering audit 2026-09-29 - running notes (crash-safe log)

Prompt: plan/PROMPT-OVERNIGHT-ENGINEERING-AUDIT-2026-09-29.md. Branch `eng-audit-2026-09-29`, worktree C:\dev\anees-eng-audit.
Base = origin/master 39aecc0 ("before" numbers = that commit; a clean copy sits in the scratchpad worktree anees-base-0929).

## Setup (done)
- accuracy-gates: uncommitted WIP (accuracy_gates.py, policy, release, verification queue, build_lessons_page_data hook)
  committed as 936a2ed on accuracy-gates and pushed; merged (9d29638). Conflicts: detect_grammar_usage.py took the
  own-checkout path; generated data took master (rebuilt).
- amal-grammar-notes-2026-09-29 (79fde02) merged (e7d88e3): scripts took the branch copy (same own-checkout fix),
  data rebuilt in the order its worker gave: buckets -> usage -> amal notes -> console -> amal rules -> lessons -> ladder -> arabizi.
- Live-repo path check: no builder in scripts/ writes to C:\dev\anees-hourly any more (only switch_hourly_job.ps1 names
  it, on purpose). Old C:\dev\anees paths remain in run_lesson_pipeline.ps1 / run_paid_engines.ps1 / run_sm_ar.ps1
  (retired jobs) and verify_speaking_release.py (reads C:/dev/anees/docs) - listed in area 4.
- Publishing today: GitHub Pages "legacy" build from master:/docs (no workflow file in the repo; the only Action is
  GitHub's own pages-build-deployment). So EVERY push to master publishes. Pushers: hourly_lessons.publish,
  tutor_refresh, decisions_refresh, gap_fill_refresh, the "ahead" push in main, review_lesson.py step 8.
  Scheduled task "Anees lesson pipeline" runs C:\dev\anees-hourly\scripts\run_hourly_lessons.ps1 hourly at :15.
- Codex: `codex exec -m gpt-5.5` works (the config default gpt-6-sol is refused on this ChatGPT account).
  Local faster-whisper large-v3 is cached (independent, non-Claude ASR for clip re-listening).
- Baseline tests (clean master + merges): pytest -x stopped at tests/test_m3_planner.py (9 buttons > 4). Coordinator:
  8 py + 1 node tests fail on clean master.

## Areas
| # | Area | Owner | State |
|---|---|---|---|
| 1 | Numbers add up across pages | worker A, C:\devnees-eng-a, branch eng-audit-a (+ ≈ marks, one truth, check_numbers.py) | running |
| 2 | Score formulas | worker A | running |
| 3 | Source audio + transcripts | worker B, C:\devnees-eng-b, eng-audit-b (+ accuracy gates 8 items, Codex re-judge, Tutor list) | running |
| 4 | Hourly job end to end | worker C, C:\devnees-eng-c, eng-audit-c (+ publish guard) | running |
| 5 | Rules vs code | worker D, C:\devnees-eng-d, eng-audit-d | running |
| 6 | AI steps | worker D | running |
| 7 | Flashcards | worker E, C:\devnees-eng-e, eng-audit-e | running |
| 8 | Amal's inputs | worker E | running |
| 9 | Page health | worker F, C:\devnees-eng-f, eng-audit-f (+ failing tests, check_pages.py) | running |

Workers launched ~02:40 from 8328f80 (after rebuild commit 3c2835c). Each keeps plan/ENG-AUDIT-AREA-*.md in its worktree.
If a worker dies: its branch eng-audit-<x> has whatever it committed.
