# Systemic accuracy audit + fixes (Medi, 2026-09-27) - branch work, NOTHING published

## Where to work
- Repo: C:\dev\anees-hourly (master is live: GitHub Pages + an hourly job commits to it). Do NOT work on master.
- Create a separate worktree + branch: `git -C C:\dev\anees-hourly worktree add C:\dev\anees-accuracy -b accuracy-gates`
  and do all work in C:\dev\anees-accuracy. Commit on the branch. You may `git push origin accuracy-gates` (a branch push
  does not publish Pages); never merge to master, never push master, never change the Pages workflow's trigger branch.
- Tools: python (set PYTHONIOENCODING=utf-8), node at C:/dev/tools/node-v24.18.0-win-x64/node.exe, ffmpeg on PATH,
  `claude -p` works headless again (re-logged 2026-09-27). Raw data (read-only): C:\dev\anees\data\lessons\<date>\.
- Commit messages end with: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- Never contact Amal. Keep raw transcripts immutable (RULES.md S2).

## Medi's request, verbatim

Audit and fix Anees's SYSTEMIC accuracy problems. Prioritize changes that make every future lesson and every progress
score more trustworthy, rather than correcting isolated words.

Start by reading RULES.md, plan/SESSION-DECISIONS-2026-09-21.md, plan/PROMPT-OVERNIGHT-FULL-AUDIT-2026-09-26.md,
plan/PROCESS-AUDIT-2026-09-26.md, and scripts/review_lesson.py. Preserve Medi's standing decisions. Where those documents
conflict, identify the conflict and ask Medi before changing the rule.

The urgent problems to investigate and fix:

1. The audit required two consecutive reader passes at >=95% agreement, but the process audit reports 61.5%, and
   review_lesson.py still builds and publishes scores. Enforce the agreed release threshold in code.
2. Lessons with unreviewed speech recognition or missing participant audio receive precise vocabulary, grammar, and
   speaking scores. Track source coverage by participant and time interval. Mark affected results provisional or
   unscoreable; exclude them from verified mastery and accuracy totals.
3. The two readers and adjudicator are all Claude reading the same transcript. Improve adjudication so the third reviewer
   sees both agreed and disputed rows, and require independent audio or human checks for uncertain, consequential cases.
4. review_lesson.py ignores several builder failures, can continue despite Arabizi gaps, and reuses reader files based
   only on existence. Fail closed and invalidate cached outputs when transcript hashes, rules, or vocabulary data change.
5. GitHub Actions appears to run only Pages deployment. Add a test gate before publication: schema checks, source
   coverage, agreement, scoring invariants, golden difficult cases, and reconciliation of totals across Word Bank,
   Grammar, Lessons, and Progress.
6. The Word Bank audit's later "passes" record existing outcomes and metadata; they do not independently verify the
   linguistic judgment. Separate integrity checks from actual adjudication, with evidence spans, reviewer identity,
   confidence, and revision history.
7. The grammar score uses human-labeled corrections over machine-counted uses, while the process audit says Latin-script
   ASR turns are skipped by the usage counter. Validate that denominator before displaying mastery percentages.
8. The Word Bank audit excludes September 14 and 18 and has 350 pending learner occurrences. Show eligible, excluded,
   and pending counts beside headline accuracy figures.

Work on a branch. First reproduce and rank the failures. Then implement the smallest coherent system changes with
meaningful regression tests using real difficult examples. Do not "fix" low agreement by relaxing the threshold or
silently counting uncertain evidence as correct. Keep raw transcripts immutable.

Before publishing anything, give me:
- the root cause and fix for each item;
- tests run and their results;
- a before/after coverage and agreement table;
- examples of scores that changed and why;
- any decisions that still require Medi or Amal.

Do not claim the audit is complete if source audio, reader agreement, or validation remains unresolved.

## Context from the 2026-09-26/27 session (read, verify, do not trust blindly)
- Same-day loop: scripts/review_lesson.py (readers r1/r2 -> full_audit_compare.py compare -> r3 -> settle ->
  full_audit_build.py -> pages -> patterns -> after_from_audit.py -> build_tutor_data.py -> git). Hourly caller:
  scripts/hourly_lessons.py.
- Hand verdicts per word card (on_list / new / not_an_error / duplicate, by meaning) live in
  data/lesson-work/sheet-verdicts.json and are applied by scripts/build_lessons_page_data.py. The automatic string
  sheet-match (scripts/lessons_page_node.cjs) was wrong often - verdicts by meaning are the standing rule
  (memory: judge list membership by meaning, both ways Arabic and English).
- Arabizi guard: scripts/arabizi_gaps.cjs (exit 1 on any gap); review_lesson.py step 6b currently only logs when gaps remain.
- Known coverage holes: 09-23 Medi 0:00-22:37 untranscribed; 09-26 Amal 0:00-18:33 untranscribed (audio now mixed in
  by scripts/remix_lesson_audio.py); 09-10 has no engine word timings (timings estimated from per-person audio by
  silence detection, flagged talk.estimate); 09-18 is one mixed recording with speakers guessed by pitch; 09-16 and
  09-18 grammar % are estimates (grammar.estimate) because slips > machine-counted uses.
- Engine can mishear: when Amal echoes what he said, her words win (reader briefs updated 09-26).
- Standing: Words % counts audit slips (tier 1-3 wrong, asked = partial); not-on-sheet words unscored and sent to Amal;
  B rows unscored until Amal rules; nothing sent to Amal by the app. 18 proposed rules in PROCESS-AUDIT section 5 are
  NOT approved - do not apply them.

## Conflicts
You cannot ask Medi mid-run. When a rule conflicts, do NOT change it: implement everything else, and list each conflict
(where, the two readings, your recommendation) under "Decisions for Medi / Amal" in the report.

## Deliverable
1. Branch `accuracy-gates` with commits + tests (pytest or plain python test runner; tests must run offline).
2. plan/ACCURACY-AUDIT-2026-09-27.md in the branch with: ranked failures (reproduced, with evidence), per item root
   cause + fix, tests run + results (paste the summary), before/after coverage and agreement table per lesson, examples
   of scores that changed and why, decisions still needing Medi or Amal, and an explicit "NOT complete because ..." list
   for anything unresolved (source audio, agreement, validation).
3. Reply with a short summary in Medi's format: one line, one table, one-line bullets, one bold action. Do not publish.
