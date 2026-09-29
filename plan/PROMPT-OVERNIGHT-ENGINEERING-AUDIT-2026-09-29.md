# Overnight engineering audit: everything adds up (Medi, 2026-09-29) - branch work, NOTHING published

Medi's ask, verbatim: "run a full overnight audit report to make everything is engineered correctly. That all the logics
are formulaically adding up. Make sure all reports are correct."

He was grilled on 2026-09-29. His 8 answers are below and are FINAL: do not re-ask them.

## Where to work
- Live repo: C:\dev\anees-hourly (branch `hourly` tracks origin/master = live GitHub Pages; an hourly job commits there).
  Never edit, commit or merge in that checkout. Never push master.
- Make a worktree: `git -C C:\dev\anees-hourly worktree add C:\dev\anees-eng-audit -b eng-audit-2026-09-29 origin/master`.
  Before starting, confirm that every builder you run writes into YOUR checkout and not C:\dev\anees-hourly (commit
  278753d found builders with hard-coded paths into the live repo). Fix any such paths first.
- Merge in two unmerged branches first, and say so in the report:
  1. `accuracy-gates` (C:\dev\anees-accuracy; scripts/accuracy_gates.py plus uncommitted work there. Commit that work on
     accuracy-gates before merging it).
  2. `amal-grammar-notes-2026-09-29` (Amal's rule notes; if it isn't pushed yet, note it and continue without it).
- Tools: python (PYTHONIOENCODING=utf-8), node at C:/dev/tools/node-v24.18.0-win-x64/node.exe, ffmpeg. Codex is
  available through the codex plugin (codex:rescue / codex-companion) as the NON-Claude second judge.
- Raw data is read-only: C:\dev\anees\data\lessons\<date>\. Raw transcripts are immutable (RULES.md S2).
- Commit messages end with: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push the BRANCH only.
- Never contact Amal. Nothing is sent to anyone.

## Read first
RULES.md · plan/SESSION-DECISIONS-2026-09-21.md · plan/PROCESS-AUDIT-2026-09-26.md · plan/FULL-AUDIT-2026-09-26.md ·
plan/AI-ENGINEERING-REVIEW-2026-09-27.md · plan/PROMPT-SYSTEMIC-ACCURACY-AUDIT-2026-09-27.md (its 8 items are part of
tonight) · plan/SENTENCE-LADDER-SPEC-2026-09-27.md · scripts/review_lesson.py · scripts/hourly_lessons.py.
Anees memory notes in C:\Users\Mahdi\.claude\projects\C--Claude\memory\ (all files starting `anees-`): these are Medi's
standing rules. Where a rule and the code disagree, list it. Where two rules disagree with each other, list the conflict
and ask Medi in the report. Never pick a side silently.

## Medi's 8 decisions (grilled 2026-09-29)
1. Scope: ALL 9 areas below.
2. On a problem: fix it on this branch, with a test that fails before the fix and passes after. Nothing goes live until
   Medi approves in the morning.
3. The half-built accuracy check (accuracy-gates): FINISH it tonight as part of this audit, covering all 8 items of the
   09-27 prompt: tests, the publish block, and the before/after table.
4. A score from an unverified lesson SHOWS with a ≈ mark (e.g. "Words ≈74%"). A hover or tap says why it isn't verified.
   Averages still include it (also marked ≈ if any input is ≈). Never hide it, and never show it as exact.
5. Uncertain rows: first Codex (not Claude) re-judges each one against the AUDIO clip plus the transcript. Rows Codex and
   the Claude readers still disagree on go to a review list on the Tutor page (docs/tutor.html) for Amal to check,
   using the same "Correction is correct / Reason not to correct + box" pattern already used for her. Note: Medi
   REMOVED the separate "Amal's Tutor Hub" page and every "Amal's hub" button on 2026-09-28 ("this shouldnt exist"). Do
   NOT bring either back; the list lives on tutor.html. Her answers are stored and her "yes" makes a row scored.
6. Truth: when two pages disagree, NEITHER is trusted. Recompute every number from raw (transcripts plus the stored
   verdicts of Medi and Amal), then make every page read that one number.
7. Leave a permanent guard: every hourly run re-checks the math BEFORE publishing. If anything doesn't add up, it
   doesn't publish, it keeps the last good version live, and it tells Medi why (a short line in the hourly log and on
   System Settings). Find out how publishing actually works today (the hourly job, the Pages branch, any GitHub Actions)
   and put the guard in front of it.
8. Report: on the AI Reports page as the next report (after #7, the 09-26 process audit; data in
   docs/data/ai_reports.json), written as a CURRICULUM: short lessons that teach Medi what is wrong and what needs to be
   done, in order. Use pictures, diagrams and charts. Use bullets. NO walls of text: no paragraph over 3 lines, and
   define every term in plain words. NO quizzes. Medi has severe ADD. Also save a copy to C:\Claude\reports and send
   it to him.

## The 9 areas
For each: reproduce, rank by harm, fix on the branch, and test.
1. **Numbers add up across pages.** Every number shown on any page (22 pages in docs/*.html; 31 files in docs/data/) is
   traced to its formula and inputs. The same quantity must be identical everywhere (Lessons, Word Bank, Grammar, Progress
   & Stats, Flashcards, AI Reports, Tutor, Big Picture, System Settings). Build a reconciliation table:
   quantity → every page that shows it → value → match?
2. **Score formulas.** Write each formula out: numerator, denominator, what's excluded and why (e.g. Words % = right ÷
   tried; grammar % = uses right ÷ uses). Check part-counts sum to totals (per lesson → per week → overall; per rule →
   family → overall; on-list + new + not-an-error = cards checked). Check status bands (Mastered/Good/Shaky/Wrong/Untested)
   match their stated cut-offs. Check the date ranges (1M/3M/YTD etc.) and "latest lesson" logic. Check rounding. Check
   that averages are weighted the way the page says.
3. **Source audio and transcripts.** Per lesson and per person: is audio present for the whole lesson, are there
   untranscribed holes, are the speakers swapped (09-18 was once), was the ASR (speech-to-text) reviewed. This feeds the
   ≈ marks.
4. **Hourly job end to end.** A new lesson must reach every page with no hand edits (09-26 once stopped at the
   transcript page because of hard-coded date lists). Look for hard-coded dates or counts, silently ignored failures,
   cached reader files reused only because they exist, and stale outputs. Everything must fail closed.
5. **Standing rules versus code.** Take every rule in RULES.md and the anees-* memory notes. Is it enforced in code, is
   it tested, and does the live data obey it? Output a table: rule → where enforced → test → obeyed yes/no → examples.
6. **AI steps.** For each AI step (transcribe, speaker split, grammar detector, word readers, grammar readers, third
   reader, sheet match), give: model and version pinned or not, whether calls are logged, the gold set if any, and the
   measured accuracy. Build the run log and the decisions log from the 09-27 AI engineering review if they're small; list
   them otherwise. Do not replace a measured number with a guess.
7. **Flashcards.** Check the FSRS (the spaced-review scheduler) math and due dates, and that the 107+ set counts match the
   JSON. Check the review history is kept, and that flashcard stats on Progress & Stats match the card data.
8. **Amal's inputs.** Is every answer she has given in the app? Verb check list 1 (her 09-25 answers: 688 were not pulled,
   only 41 were), verb check list 2, the slips-by-pattern review, word review, and her grammar-rule notes. Count given vs
   stored vs shown for each.
9. **Page health.** Broken links, dead audio clips (clip-fallback exists; check it works), blank cards and dashes where a
   number belongs, the Arabizi guard (`node scripts/arabizi_gaps.cjs` must print 0), and mobile width. Check both light
   and dark mode.

## Rules for the audit itself
- Never lower a threshold (the 95% agreement bar) to make something pass. Never count uncertain evidence as right.
- Machine flags are clues. Context decides (memory: anees-15s-rule-is-a-clue, anees-list-by-meaning).
- Amal's spelling is the rule (anees-amal-spelling-rule). Spelling is not a focus (anees-spelling-not-a-focus).
- Every number you change: list the old value, the new value and why. Nothing is removed silently.
- Hand-check a random 20 of your own findings before reporting, and report how many held up.
- If you run out of time, say exactly what is not done. Never say "complete" when audio, agreement or validation is still
  open.

## The report (curriculum on AI Reports)
Lessons, in this order:
1. **The big picture:** one diagram of how a lesson becomes numbers, marking where it broke.
2. **Scorecard:** each of the 9 areas as ✅ / ⚠ / ❌ with one line each.
3. **One lesson per problem found:** what it is (a picture), why it matters, what was fixed, and what's still needed.
4. **Before/after table:** every number that changed.
5. **The permanent guard:** what it checks every hour, shown as a diagram.
6. **Decisions for Medi**, and separately **for Amal**: each is one line with a yes/no.
7. **Not done yet:** an honest list.
Also give Medi a one-screen summary in chat, plus the merge command to run when he approves.
