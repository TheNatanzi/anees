Read `C:\dev\anees-hourly\RULES.md` first, then `plan/GRAMMAR-CORRECTION-SWEEP-2026-09-24.md` (how the last sweep worked),
`docs/word-bank-review-rules.md` (the 13 vocab review rules) and `docs/data/grammar-buckets.json` (57 rules, A1–F3 + B18/E5).

GOAL (Medi 2026-09-25, in his words): "I am SURE I have made WAY more vocab errors." Re-read every recorded lesson (13:
08-25, 09-04, 09-05, 09-10, 09-11, 09-14, 09-15, 09-16, 09-17, 09-18, 09-19, 09-21, 09-23) in CONTEXT and catch every
vocab error and every grammar error, loop until two independent readers agree, feed the results into the pages, build
Amal's review page in the Tutor Hub, and audit the process itself so the next lesson is reviewed the same day without
her hand-holding. Convert every transcript display to Arabizi-on-top, Arabic-small-under (decision b).

## Decisions already made (do not re-ask)
- **A counts, for sure**: every vocab fix Amal said out loud (the sweep found 147; the lesson pages show 23). Vocab error
  = (1) wrong word / non-word, (2) wrong form of a word he knows, (3) an English word dropped into an Arabic sentence
  when the Arabic word is on Amal's sheet — but NOT when he is plainly switching to English to make a point.
- **B = Amal let it pass**: tiers 1–3 judged from context WITHOUT her signal. B items are NOT scored until Amal confirms.
  They go to her page. When she says "correction is correct" the item becomes a scored error right away (clip, underline,
  % drops — same as her voice). When she gives a reason not to correct, the item is dropped and her reason becomes a rule
  so the same pattern is never asked again.
- **Amal's page = patterns with examples (decision C)**: one row per pattern, her ruling once, ALL examples folded under
  it ("show examples"). Same format for the 13-lesson backfill and for every future lesson review ("ALways examples even
  on the new immediate lesson reviews").
- **Answers go straight to the database (decision a)**: a secret link like her after-lesson link (`docs/amal/after.html`
  pattern: `api('POST','amal_rules',…)`), living in the **Tutor Hub** (`docs/amal/hub.html`, to be built — today her 5
  pages after.html / grammar-rules.html / plan.html / verb-check.html / word-review.html have no home).
- **Arabizi everywhere = decision b**: Arabizi big, Arabic small underneath, on every Medi-facing transcript view
  (single-lesson pages docs/lessons/<date>.html, lessons.html, word-bank, grammar, slips, speaking pages). Amal's pages
  stay Arabic-first. Spellings: her Doc + docs/data/arabizi-extra.json (rule S1); fragments stay Arabic.
- Standing rules S1–S5 hold. Rule from 2026-09-25: a machine flag (15 s rule, echo match, cue word) is only a CLUE;
  a context read decides (memory anees-15s-rule-is-a-clue). Never re-transcribe; never pay for audio APIs; nothing is
  emailed or sent to Amal — Medi sends her the link himself.

## Method — the loop
1. **Two independent readers per lesson** (agents that have not seen each other's output), every Amal turn after a Medi
   turn AND every Medi Arabic turn (for B). Each writes rows: date, t, Medi said (Arabic), Amal said, wrong → right,
   kind (vocab-A | vocab-B | grammar), tier (1/2/3 for vocab), bucket (grammar), confidence, signal, why.
2. **Compare**: rows that match (same t ±5 s, same wrong piece) are agreed. Disagreements + rows only one reader found go
   to a **third reader** who rules with the transcript open. Then re-run readers 1+2 on any lesson where >15% of rows
   were disputed, until two consecutive passes agree on ≥95% of rows. Log every pass's counts.
3. **Reconcile with what exists**: `data/grammar-sweep-2026-09-24.json` (309 grammar + 147 vocab), Word Bank evidence
   (`docs/data/word-bank-evidence.json` + `word-bank-review.json` patches). Nothing already verified is dropped without
   a stated reason; everything new is added. Output: `data/full-audit-2026-09-26.json` (rows, per-pass counts, per-lesson
   agreement %, machine-caught / missed) and `plan/FULL-AUDIT-2026-09-26.md` (per-lesson tables + totals).
4. **Feed the pages**: A + agreed grammar → lesson pages (vocab errors / grammar errors / transcript marks + clips),
   Word Bank overlay (rule S2: patches, never the raw), Grammar console, Amal's grammar-rules page. Rebuild
   `scripts/build_lessons_page_data.py`, `build_grammar_console.py`, `build_amal_grammar_rules.py`. Hand-check 20 random
   new rows against the transcript; report the score.
5. **Amal's B page** — `docs/amal/review.html` (+ hub): group every B row into patterns (e.g. "qalat used for 'wrong'",
   "English 'customers' inside an Arabic sentence", "ajait for ijeet"). Per pattern: her spelling of the fix, one
   sentence of why, count, "show N examples" fold-out with clip + time. Two buttons: **"Correction is correct"** /
   **"Reason not to correct"** + a text box (required for the second). Saves to `amal_rules` (kind `audit_confirm` /
   `audit_skip`, pattern id, her text) via the after.html pattern. A **Tutor Hub** page lists all her links with a
   one-line "what this is / how long it takes". A morning script (`scripts/apply_amal_audit_rulings.py`) turns her
   answers into scored errors or into rules in `docs/data/ai_rules.json` (kind `amal-ruling`) — idempotent, rerunnable.
6. **Arabizi everywhere (b)**: audit every page that prints a transcript line; make each show Arabizi on top, Arabic
   small underneath, one shared renderer (`docs/js/word-bank-arabizi.js`). Fragments stay Arabic with the "Unverified
   spelling stays in Arabic" note. Random 100-line hand check ≥ 95.
7. **Process audit** — read the audit rows for *why each miss was missed* and write `plan/PROCESS-AUDIT-2026-09-26.md`:
   which detector gaps (e.g. English-in-Arabic, wrong-form-of-known-word, corrections spread over 3+ turns, chat lines
   that lag the voice by 30–120 s, untranscribed Medi stretches) caused how many misses; a proposed rule for each with
   a one-line test; which patterns Amal will have to rule on ONCE and which the system can settle alone from her Doc.
   Goal named by Medi: "a system that doesn't need her hand holding" — every ruling she gives must become a reusable
   rule, never a one-off.
8. **Same-day lesson review**: write `scripts/review_lesson.py <date>` that runs steps 1–5 for ONE new lesson (two
   readers → compare → third reader → pages → Amal's line items with examples), and wire it into the hourly job so a
   new recording produces Medi's page + Amal's link the same day. Dry-run it on 09-23 and show the output.

## Report to Medi (his format)
One line, a picture (bucket-count + vocab-tier chart, before/after per lesson), short bullets, one bold action:
the Tutor Hub link for him to send Amal. List every new rule proposed, one at a time, for his yes/no. Note anything
that could not be verified (transcript holes) rather than guessing. Commit + push after each step (`git push origin
HEAD:master`), commit messages ending "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>".
