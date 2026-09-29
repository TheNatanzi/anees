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
| 1 | Numbers add up across pages | worker A, C:/dev/anees-eng-a, branch eng-audit-a (+ ≈ marks, one truth, check_numbers.py) | running |
| 2 | Score formulas | worker A | running |
| 3 | Source audio + transcripts | worker B, C:/dev/anees-eng-b, eng-audit-b (+ accuracy gates 8 items, Codex re-judge, Tutor list) | running |
| 4 | Hourly job end to end | worker C, C:/dev/anees-eng-c, eng-audit-c (+ publish guard) | running |
| 5 | Rules vs code | worker D, C:/dev/anees-eng-d, eng-audit-d | running |
| 6 | AI steps | worker D | running |
| 7 | Flashcards | worker E, C:/dev/anees-eng-e, eng-audit-e | running |
| 8 | Amal's inputs | worker E | running |
| 9 | Page health | worker F, C:/dev/anees-eng-f, eng-audit-f (+ failing tests, check_pages.py) | running |

Workers launched ~02:40 from 8328f80 (after rebuild commit 3c2835c). Each keeps plan/ENG-AUDIT-AREA-*.md in its worktree.
If a worker dies: its branch eng-audit-<x> has whatever it committed.

## Merged so far
- D (areas 5+6) merged 64467f3: check_rules.py (20 checks: 14 pass, 6 open report-only), Claude pinned to claude-opus-5-5,
  standing-rules.json rebuilt, 36/36 raw transcript hashes, 9 rule conflicts for Medi (C1-C9). Findings plan/ENG-AUDIT-AREA-5-6.md.
- E (areas 7+8) merged cb0364d: 688 verb answers pulled (41 -> 729), list-2 pull saved, Amal's approved form wins,
  fsrs.replay ignores undone rows, 19 Quizlet sets (107 -> 126 sets, 2,406 -> 2,841 terms). Findings plan/ENG-AUDIT-AREA-7-8.md.
- INCIDENT: tests/test_m5_cards.py + test_m4_after.py run against the LIVE Supabase DB. Tonight's full-suite runs (the
  coordinator's baseline at ~02:17 PDT and workers' runs) left 90 fake rows in card_results (Animals, 09:14-09:55 UTC),
  2 fake leeches, used today's new cards. Nothing deleted (needs Medi's yes). All workers told to deselect them.
- Relayed: build_tutor_data pulled-count + payload.applied -> B; review_lesson docstring, transcribe run-line, check_rules
  in guard -> C; test_invariants fixes + test side effects -> F.
- F merged (test_m5_cards took F's copy: sizes rounds from the 8-new-a-day cap + cleanup in finally), C merged (publish
  guard, fail-closed hourly, reader manifests), A merged (duplicates, one grammar formula, slips into Word Bank, ≈ marks,
  check_numbers.py). Coordinator fixes: live-DB test gate (conftest, ANEES_E2E_LIVE=1), audit_vocab_unresolved in hourly,
  AI Reports 961-row cards as_of, Flashcards read audit slips, new-words fallback strict in hourly.
- Worker G (C:/dev/anees-eng-g) launched 03:37 for the 09-28 hand reads: 121 open vocab events + 0 sheet verdicts.
- B (gates + Codex) still running; did accuracy_gates pooled averages + duplicate/Amal-ruling filter (44e0e56).
- Known guard blocker after merge: tests/test_verb_addons.cjs golden (Amal's check-list form vs her Quizlet card).
