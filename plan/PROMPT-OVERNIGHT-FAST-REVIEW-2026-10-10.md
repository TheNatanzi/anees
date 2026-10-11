# Overnight brief: fast review mode + lean test protocol (2026-10-10 night)

Medi 2026-10-10 (exact words, for the registry): "It takes a lot of time to review in its current state, its gonna take
longer in this metod" · "Is there anyway we can simplify this so that it doesnt take as much time for amal and i" ·
"build in a new chip do it overnight loop and improve test and make sure council approves and make sure codex approves".

Earlier the same day: "DUDE WHAT THE ACTUAL FUCK ... A COMEPLETE GUIDE SYSTEM AND FOLLOW IT EVERY FUCKING TIME. MAKE A
SYSTEM" (the hourly job had been silently blocked for 29 h on data/budget.json; nobody was told).

## Ground rules (every one binds)

- Read AGENTS.md, RULES.md, `python scripts/rule_registry.py show pages / process / transcription / amal-data`,
  plan/PIPELINE-TEST-PROTOCOL.md, plan/LESSON-AUDIT-RUNBOOK.md, reports/Lesson pipeline testing methods.md.
- Windows: `set PYTHONIOENCODING=utf-8`; `ANEES_REHEAR_AUTO=off ANEES_TRANSLATE=off` on every local build/test.
- Fresh worktree from origin/master. NEVER edit C:\dev\anees-hourly (reading its files is allowed). Never contact Amal.
- Push ONLY through `python scripts/publish_guard.py push --source "overnight: <what>"`; `git checkout --
  docs/data/tutor-notes.json` right before; `git add -f` any new clip mp3 the clip files reference.
- Commit trailer: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Full rebuild order: full_audit_build -> apply_amal_audit_rulings -> detect_grammar_usage -> build_lessons_page_data x2
  -> build_grammar_console, build_amal_grammar_rules, build_amal_review, build_tutor_data, build_student_data,
  build_tutor_weak, review_grades -> accuracy_gates annotate -> lesson_ledger check OK -> rule_registry check OK ->
  build_rule_book.
- Every correction of Medi's = a registry entry with his exact words + code + a test in the guard's tests_py (S6).
- PR-08: `python scripts/session_asks.py` checklist; `check` OK before the final report.
- Loop until BOTH approvals are recorded and the guard pushes clean. Do not stop at the first green run.

## Deliverables

### 1. Fast review mode on the Lessons page (new rule PG-50, Medi's words above)

A "Review" button on a lesson's transcript opens review mode:
- Shows ONLY Medi's lines that hold Arabic (word_coverage.word_tokens), in order, one at a time, with a progress bar
  ("37 of 104") and a running timer; minutes are logged with the rows (see below) so the next estimate is measured.
- "Unsure only" filter ON by default: a line is unsure when (a) the second listen's runs disagreed or changed it
  (data/lesson-work/rehear/<date> run files / `heard` on the turn), or (b) the two readers disagreed on it
  (data/lesson-work/full-audit/<date>.compare.json), or (c) a ✗ chip sits on it, or (d) it is one of 5 random
  confident lines (seeded by date so the set is stable). A toggle shows all lines. Built by a new
  `scripts/review_picker.py <date>` -> `docs/data/review-pick/<date>.json` (run in build_lessons_page_data or right
  after it; add to the hourly order and amal_trigger's builder list).
- Each line: its clip auto-plays (the existing play-bar / clip code; fall back to the lesson mp3 at t-1 s), the Arabic,
  the Arabizi, the English under it (PG-40), the chips. Keys and big buttons, no free text required:
  `1` heard right (no row written, counted as reviewed) · `2` wrong word -> one box for the word he said (Arabizi or
  Arabic), writes a `text` correction row like today's `heard` rows · `3` mistake -> writes an `add` row (vocab or
  grammar; the robot proposes which, he can flip it with one key, never asked for the rule id) ·
  `4` not a mistake -> `not-slip` row (reason: one of the four existing buttons) · `space` replay · `enter`/`→` next ·
  `←` back · `u` undo (an undo row, AM-17 style, never a delete). The "✎ more" panel stays available but optional.
- Blind block: the first 50 lines of a lesson show WITHOUT chips (the key's anchoring test, protocol §2.2); a small note
  says why; after line 50 the chips appear. Rows written in the blind block carry `payload.blind: true`.
- Rows go to the SAME Supabase table `transcript_corrections` through the same queue in
  docs/js/transcript-corrections.js (append-only; same `kind`s), plus `payload.review_mode: "fast"`,
  `payload.secs` (seconds spent on that line). Nothing new to parse: medi_corrections.py already applies these kinds.
- Phone: works one-handed (680 px and under: buttons bottom-fixed, PG-31 bar hidden in review mode).
- Tests: a node test like tests/test_transcript_corrections.cjs for the key -> row mapping, the blind block, the undo;
  a pytest for review_picker (unsure set from fixture files; the 5 random lines are stable per date).
- PG-33 names (Tutor / Student) on every visible string; Arabizi first on every word (PG-44, S1).

### 2. 10-09's second listen goes live WITHOUT touching the hourly checkout

The hourly checkout already paid for and applied 10-09's Gemini runs but could not publish (blocked since 10-09 11:34
on a data/budget.json conflict). Copy, read-only, `C:\dev\anees-hourly\data\lesson-work\rehear\2026-10-09\` (runs,
apply-plan, proposals) and its `rehear-status.json` entry into the worktree, verify the hashes against lines.json,
apply with the normal path (rehear_apply, TR-27 holds kept, status "applied"), queue the re-read, rebuild, push.
Then run `python scripts/lesson_audit.py 2026-10-09` and fix what the runbook §C says, as a normal lesson audit.
Do NOT re-send Gemini jobs for 10-09 (money). If the copied files are incomplete, say so and stop that item.

### 3. The silent-stall system (Medi: "MAKE A SYSTEM")

- `data/budget.json` becomes a GENERATED file for the guard's rule G1 (rebuilt from the run logs, master's copy kept
  on conflict) so it can never block a push again. Prove it with a test in tests/test_publish_guard.py.
- Stall alarm: when origin/master's last hourly publish is older than 2 h during a day with a lesson or any pending
  work, (a) the publish guard prints a WARNING line naming the hours and the first blocked reason, (b) every page's
  stale banner (PG-01 docs/js/stale.js) shows "The hourly robot has not published for N h: <reason>", (c) a line in
  the lesson ledger (LS-04 style). Source of truth: a small `docs/data/pipeline-health.json` written by the guard and
  the hourly job (last publish, last block reason, open failures). Test it.
- Auto-freeze (protocol §2.1): on a lesson's FIRST publish, the hourly job snapshots
  `data/lesson-work/review-grades/<date>.first.json` (page + SHA) so the grade book never reconstructs "before" from
  git. review_grades.py reads it when present. Rename the grade book's "now" column to "drift" everywhere (JSON key
  may stay; the label and the tooltip change; PG-46 statement updated).
- Leave ONE command for Medi in the report to clear the hourly checkout's own stuck state (you may not run it):
  exactly what to type, what it keeps, what it drops (nothing of value: the hourly's local commits are generated
  files that master already has newer copies of, EXCEPT anything under data/lesson-work/rehear/ or data/runs you
  did not already copy; list those).

### 4. Lean protocol (update plan/PIPELINE-TEST-PROTOCOL.md and PR-23)

- Medi reviews 1 lesson in 3 (the exam), his Arabic lines only, unsure-first, keys not notes; blind block = the first
  50; re-listen = 15 moments, exam lessons only, through the same review mode (a "re-listen" filter that hides his
  earlier answer). The other 2 lessons: 0 minutes from him; Amal's 10 min unchanged; her protocol moments ride inside
  her existing cards (no new card type).
- Grammar rules: nobody validates rule by rule; the robot assigns, Amal confirms patterns (one tap covers many
  instances). Write that down.
- Time is measured, not guessed: the review mode's seconds roll up per lesson into review-grades.json
  (`minutes_medi`), shown on the Grades tab.
- Run-log row for tonight.

### 5. Hearing harness: the skeleton only (no paid runs tonight)

`scripts/hearing_harness.py` with the five switches from protocol §5 as flags, a dry-run that lists which cached
engine outputs exist for 10-08 and what each cell A–F would cost, a scorer that reports hit rate + FCR (false-correction
rate) against the frozen key, and a blind judge prompt (version X / version Y, order swapped, no engine names). Tests on
fixtures. No Gemini/Deepgram money spent; `ANEES_REHEAR_AUTO=off` stays on.

### 6. Approvals (both required, loop until green)

- Council: run the `anthropic-skills:council` skill on the design of §1 and §4 ("does this cut Medi's time below
  today's and keep the tests valid?"). Record the verdict + confidence + each advisor's objection in
  plan/OVERNIGHT-LOG.md. An objection that names a real flaw = fix it and re-run.
- Codex: run `codex exec -m gpt-5.5` (through codex:rescue / scripts the repo already uses) as a reviewer of the full
  diff against this brief and RULES.md; loop until Codex's review has no blocking finding. Record each round.
- The publish guard's 18 checks + the full test suite green; `rule_registry.py check` OK; `lesson_ledger.py check` OK.

## Report to Medi (one line, a table, short bullets, his one action in bold; never recap rules)

Table: minutes measured on the review mode (your own dry run on 10-08), 10-09 second listen live yes/no, stall alarm
live yes/no, council verdict + confidence, Codex rounds, tests added, rules added. His one action: the one command for
the hourly checkout, or "review 10-09 in the new mode".
