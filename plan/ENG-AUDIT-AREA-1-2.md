# Eng audit 2026-09-29 — areas 1 (numbers add up across pages) + 2 (score formulas), decisions 4 (≈) + 6 (one truth)

Worker A, branch `eng-audit-a` (from `eng-audit-2026-09-29` @ 3c2835c). Nothing published.
"Before" = the data and code at 3c2835c (= live master 39aecc0 + the two merged branches), rendered offline in
Chromium with every network request blocked (pages fall back to the published JSON; the live Supabase speaking
evidence was checked equal to `docs/data/word-bank-evidence.json`: 5,336 = 5,336 events, 0 differ).
"After" = this branch, data rebuilt locally (`full_audit_build.py` → `build_grammar_console.py` →
`build_lessons_page_data.py`); regenerated data files are NOT committed (coordinator rebuilds).

Machine table: `data/eng-audit/reconciliation.json` (25 quantities). Checker: `python scripts/check_numbers.py` →
before: `numbers: FAIL … (+105 more)` (106 of 554 checks failed, `data/eng-audit/check-numbers-before.json`);
after: `numbers: OK 555 checks` (`data/eng-audit/check-numbers-after.json`).

## Scorecard
- Area 1 ⚠ → fixed on branch: 14 of 25 cross-page quantities disagreed before; 1 residual after: 19 word slips count on
  the Lessons page but not in the Word Bank (10 wait for a reader to name the list word, 7 are prepositions = a rule
  conflict for Medi, 2 have no Word Bank row) — listed in the slips file and reconciled exactly by the checker.
- Area 2 ⚠ → fixed on branch: two grammar formulas, two averaging methods, three filled-pause tests, a double-counted
  audit, status cut-offs written nowhere. Now one formula per number, each checked every run.

## Reconciliation table (quantity → pages → before → after)
| quantity | pages | before | after | match before / after |
|---|---|---|---|---|
| Lessons loaded | Progress header, Overview, Lessons, Grammar Console, Progress›Grammar | 15 everywhere | 15 | ✅ / ✅ |
| Lesson hours | Progress header, Overview, Lessons | 16.3 | 16.3 | ✅ / ✅ |
| Words right, all lessons | Lessons "Avg words right" / Overview pooled | **76 %** (plain mean) / **80.0 %** | ≈80 % / ≈80.0 % | ❌ / ✅ |
| Grammar right, all lessons | Lessons / Overview / Console (implied) | **63 %** (mean) / **72.0 %** (13 of 15: the two weakest left out) / 75 % | ≈77 % / ≈77.3 % (15 of 15) / 77.3 % | ❌ / ✅ |
| Grammar uses, all lessons | Σ Lessons rows / Σ Console scored rules | **1,712 / 2,178** | 2,170 / 2,170 | ❌ / ✅ |
| Grammar slips counted | Lessons Σ, Console, Progress›Grammar | 560 (incl. 9 double counts) | 551 | ✅(wrong) / ✅ |
| Rule A1 mistakes | Console | 19 (09-15 1:02:41 twice) | 18 | ❌ / ✅ |
| Grammar % 09-04 | Lessons / Overview / Console formula | 40 % / 40.0 / 66.0 | ≈67 % / ≈66.7 / 66.7 | ❌ / ✅ |
| Grammar % 09-18 | Lessons / Overview | ≈34 % "45 slips / 23 uses", left out of the average | ≈35 %, 40 slips / 62 uses (+5 in unscored rules), in the average | ❌ / ✅ |
| Word uses 09-18 | Lessons / Progress›Vocab chart | 2·3·7 (29 %) / 2·0·0 (100 %) | 2·3·7 / 2·3·7 | ❌ / ✅ |
| Word uses 09-28 | Lessons / Word Bank / Progress›Vocab | 82·14·15 / 82·10·0 / 82·10·0 | 82·14·15 / 82·11·9 (+9 listed: 8 wait for a reader, 1 preposition) | ❌ / ⚠ residual, reconciled |
| Correct vs slips (Month) | Progress›Vocab | 93.9 % (audit slips missing) | ≈78.1 % | ❌ / ✅ same attempts |
| "N words" per lesson 09-10 | Lessons (rows) / Progress›Vocab (forms) | 63 / 64 | 71 / 71 | ❌ / ✅ |
| Words known | Progress header, Word Bank | 274 / 274 | 246 / 246 | ✅ / ✅ |
| Mastered | Progress›Vocab, Word Bank, header | 110 | 88 | ✅ / ✅ |
| Word ratings on lesson cards vs Word Bank | Lessons cards / Word Bank | 249 words rated by a private rule | Word Bank's own status | ❌ / ✅ |
| Fillers in 25 Aug turns | lessons.json / Overview angle H note | 16 / **24** | 16 / 16 | ❌ / ✅ |
| Filled pauses / min, all | Lessons (mean, 15) / Overview (pooled, 12 comparable) | 9.5 / 10.1 | 10.1 / 10.1 | ❌ / ✅ |
| Speaking share, all | Lessons (mean) / Progress (pooled) | 57 % / 56.9 % | 57 % / 56.9 % (one formula) | ❌ / ✅ |
| Rule statuses | Console chips / Progress›Grammar | 5·12·16·14 | 5·13·15·14 | ✅ / ✅ |
| Verb corrections | Progress›Lexicon / Σ B rules | 243 | 242 | ✅ / ✅ |
| Verified lessons vs marks | accuracy-release (0 verified) / every lesson score | shown exact | ≈ on every lesson-derived score | ❌ / ✅ |
| AI reports count | Settings / AI Reports | 10 / 10 | 10 | ✅ / ✅ |
| Rules total | Settings | 39 = 29+7+3 | 39 | ✅ / ✅ |

Pages with no lesson-derived score (nothing to mark ≈): Tutor (Amal's open lists — area 8), Big Picture (ideas),
System Settings (rule counts), AI Reports (dated report snapshots — see "not done").

## Formula sheet (the one definition each number now has)
- **Words % (a lesson)** = (right + ½ partial) ÷ scored. Scored = Word Bank attempts that day (1 / 0.5 / 0) + the full
  audit's word slips on his list (tier 1–3 wrong = 0, "asked Amal" = 0.5), minus hand verdicts not_an_error / duplicate,
  minus words not on his list (sent to Amal). Excluded: repeats/echoes, grammar-only, unresolved (Word Bank rules).
- **Words right, all lessons** = Σ(right + ½ partial) ÷ Σ scored (pooled; `lesson-math.pooledWords`).
- **Correct vs slips (Progress›Vocab)** = full-credit ÷ all scored, hints count as slips (approved spec 09-21). Same
  attempts as the Lessons page now; only the weighting of a hint differs, and the card says so.
- **Grammar uses (rule r, lesson d)** = detected uses + fixes of r no detected use within ±2 s pairs with.
  **Grammar mistakes** = full-audit speaking rows in an approved rule (Amal voiced or typed), minus Amal's rulings, minus
  duplicates. **Scored rule** = has a usage counter that fired at least once, is taught, is not a sound (F).
- **Grammar % (rule)** = (uses − mistakes) ÷ uses, rounded (Python round). **Grammar % (lesson)** = 1 − Σ scored-rule
  mistakes ÷ Σ scored-rule uses. **All lessons** = pooled the same way. Σ over lessons = Σ over rules (checked).
  Slips in unscored rules (B18, A5, B7, B17: 58 slips) are listed and counted as slips, not in any % (as the Console
  always did). Mistakes ≤ uses by construction; no "estimate" any more.
- **Grammar status bands** (now written on the page): Mastered 95 %+ on 10+ uses · Good 85 %+ · Shaky 65 %+ · Wrong <65 %.
- **Word status bands** (now written on the page): from 10 scored uses, latest 10 decide: Mastered 90 %+ with full
  marks in 2 lessons · Good 75 %+ · Shaky 50 %+ · Wrong <50 %; before 10, the streak rules (spec §4). Checked for every
  form with 10+ attempts: 0 out of band.
- **Word Bank Overall Accuracy** = Σ status points (10/8/5/0) ÷ (tested forms × 10); **Words known** = Good + Mastered.
- **Speaking share, all** = Σ his seconds ÷ Σ all talk. **Filled pauses/min, all** = Σ count ÷ Σ his minutes over
  comparable lessons (page turns keep ≥ half the fillers). One filled-pause test (`lesson-math.countFillers` =
  `build_lessons_page_data.is_filler`).
- **Periods**: Progress pills Week/Month/All = the last 7/30 days ending today (inclusive) or everything; "latest lesson"
  = max date; retention "Current" = latest lesson with ≥ 5 known words tested (stated on the chart). Rounding: stored
  1 decimal, Lessons rounds to whole %, Overview shows 1 decimal (same number).
- **≈ (decision 4)**: a score is "≈" when its lesson's `release.status` is not "verified" (or unknown); an average is
  "≈" when any input is; hover or tap shows the reasons from `release.reasons`. Today 0 of 15 lessons are verified, so
  every lesson-derived % carries ≈. Counts (lessons, slips, words known) are not marked.

## Problems found (ranked by harm), fixes, commits
1. **Word Bank and Progress ignored 219 on-list word slips the Lessons page counts** (decision A, 09-25/26). 09-28:
   Lessons 15 wrong, Word Bank 0. Lesson cards re-rated 249 words with a private rule (bands without the streak rules),
   so a word could read Mastered on the Word Bank and Wrong on a lesson card. Fix: slips join the Word Bank evidence
   (`docs/data/word-bank-audit-slips.json`, one file every page loads; ratings = Word Bank status). Slips whose list
   word is only a partial automatic match wait for a reader (10), 7 are prepositions (rule conflict below) and 2 have
   no Word Bank row: listed, counted on Lessons only (200 of 219 placed). 536e46e, 3999062. **Biggest number change** (see before/after).
2. **Two grammar formulas.** Lessons: uses = detected only, "estimate" when slips > uses; the Overview then dropped the
   two weakest lessons (09-16, 09-18) from its average. Console: fixes with no detected use are uses. Σ uses 1,712 vs
   2,178. Fix: `scripts/grammar_math.py`, used by both builders. 536e46e.
3. **Double count in the full audit** (the lead): 09-15 1:02:41 A1 = FA-950701c8 + FA-950701c8x. Root cause:
   `full_audit_compare.union_rows` let a pass-2 repeat of a pass-1 slip through as "pass-2 only", then
   `full_audit_build` renamed the colliding uid `…x` instead of merging it; a sweep row paired with that repeat was then
   re-added as "missed by the readers". Found 8 `x` rows + 6 more repeats by hand read
   (`data/lesson-work/full-audit/duplicates.json`). Speaking grammar A 582 → 573 in the audit, counted slips 560 → 551,
   vocab A 285 → 282. dd4eedc.
4. **No ≈ anywhere** although 0 of 15 lessons are verified (decision 4). Now on Lessons (rows + cards), Overview (cards
   + table), Progress›Vocab (Correct vs slips, retention, ratio foot), Word Bank headline (Overall Accuracy, 30-Day
   Memory), Grammar Console rule scores, Overview angle B. 536e46e.
5. **Lessons page averages were plain means** (76 % / 63 %, speaking 57 %, fillers 9.5) while the Overview showed pooled
   80.0 % / 72.0 % / 56.9 % / 10.1. One function (`docs/js/lesson-math.js`). 536e46e, 0994fb3.
6. **Three filled-pause tests** (builder, Overview card, angle H regex): 25 Aug turns 16 vs 24. 3999062.
7. **"N words"**: Lessons counted Word Bank rows, Progress counted forms (09-10 63 vs 64). Now distinct forms incl. slips.
8. **Stale explanations**: Console note said "the 09-24 sweep … 312 fixes" (counts come from the full audit);
   lessons.json definitions (grammar.mistakes "hand sweep 09-24"; words.unique); angle B "the table's average 75.5 %".
9. **Cut-offs written nowhere**: Grammar Console (95/85/65 + 10 uses) and Word Bank (latest-10 90/75/50). Now on the
   pages; `check_numbers.py` checks every rule and every 10+ form against them. 0994fb3.

## Tests (fail before → pass after; runs in data/eng-audit/test-runs-*.txt)
| test | before (3c2835c) | after |
|---|---|---|
| tests/test_audit_duplicates.py (4) | 3 FAIL (`assert 2 == 1` pass-2 repeat; no merge; 8 double counts) | 4 pass |
| tests/test_grammar_math.py (4) | FAIL (no one formula) | 4 pass |
| tests/test_check_numbers.py (2) | FAIL | pass (before-data → `numbers: FAIL … counted twice`; this checkout → OK) |
| tests/test_lesson_math.cjs | FAIL (no lesson-math.js) | ok |
| tests/test_word_slips.cjs | FAIL (no withSlips: pages cannot load the slips) | ok |
Whole suite on this branch (`pytest -k "not m5_cards and not m4_after"`): 7 fail, all pre-existing on 3c2835c
(test_vocab_audit ×3, test_stale_banner, test_m3_planner, + the 2 test_invariants sheet tests that my first preposition
change broke and the final version passes). All 21 node tests pass.

## Before / after numbers (every number that changed)
Per lesson (Words % unchanged on every lesson):

| lesson | Grammar % | grammar slips | grammar uses | slips in unscored rules | "N words" |
|---|---|---|---|---|---|
| 08-25 | 87.0 → 90.1 | 28 | 215 → 233 | 5 | 53 → 67 |
| 09-04 | 40.0 → 66.7 | 42 → 41 | 70 → 105 | 6 | 13 → 22 |
| 09-05 | 53.8 → 71.6 | 36 → 35 | 78 → 109 | 4 | 29 → 33 |
| 09-10 | 84.2 → 88.9 | 35 → 34 | 222 → 244 | 7 | 63 → 71 |
| 09-11 | 64.9 → 76.6 | 34 | 97 → 124 | 5 | 47 → 52 |
| 09-14 | 55.7 → 70.3 | 47 | 106 → 148 | 3 | 49 → 59 |
| 09-15 | 46.7 → 68.4 | 49 → 48 | 92 → 133 | 6 | 38 → 46 |
| 09-16 | ≈47.7 → 50.0 | 57 | 52 → 104 | 5 | 33 → 42 |
| 09-17 | 41.4 → 65.0 | 41 → 40 | 70 → 103 | 4 | 36 → 45 |
| 09-18 | ≈33.8 → 35.5 | 45 | 23 → 62 | 5 | 2 → 11 |
| 09-19 | 82.6 → 85.2 | 4 | 23 → 27 | 0 | 20 → 31 |
| 09-21 | 68.4 → 77.8 | 68 → 65 | 215 → 266 | 6 | 89 → 110 |
| 09-23 | 70.5 → 78.0 | 31 | 105 → 132 | 2 | 45 → 63 |
| 09-26 | 88.9 → 89.9 | 21 | 190 → 207 | 0 | 68 → 82 |
| 09-28 | 85.7 → 87.9 | 22 → 21 | 154 → 173 | 0 | 40 → 46 |

Why: grammar % = one formula (a fixed slip is a use; unscored-rule slips out of the %); slips −9 = duplicates;
"N words" = distinct forms incl. the audit's word slips.
Headline: Words right all 76 % (Lessons) / 80.0 % (Overview) → ≈80 % / ≈80.0 %; Grammar right all 63 % / 72.0 % →
≈77 % / ≈77.3 %; Grammar slips 560 → 551; statuses Good 12 → 13, Shaky 16 → 15 (A8 84 % → 86 %); verb corrections 243 →
242; Words known 274 → 246; Mastered 110 → 88; Good 164 → 158; Shaky 33 → 132; Wrong 1 → 18; Word Bank Overall Accuracy
83.7 % → ≈70.8 %; 30-Day Memory 84.2 % → ≈71.0 %; 30-Day Words 293 → 378; Correct vs slips (Month) 93.9 % → ≈78.1 %;
Words per lesson (Month) 41.4 → 50.9; Progress›Lexicon verb×tense pairs said 54 → 77 (mastered 17 → 12); Lessons
"Filled pauses / min" 9.5 → 10.1; angle H 25 Aug turn fillers 24 → 16.
Why the word numbers fall: the audit's Amal-signalled word slips now reach the Word Bank (decision A + decision 6).

## Hand check of my own findings (5 random)
5 of 5 held: (1) 09-15 1:02:41 transcript: one bare "asma", one supply "Il asma" — one slip, counted twice. (2) 09-28
Word Bank had 0 wrong while Lessons listed 15 audit slips (e.g. 29:14 محمد for محامي). (3) 25 Aug turn fillers: 16 by
the builder test, 24 by the angle-H regex. (4) 09-10 rows 63 vs forms 64. (5) three random 09-04 slips with no detected
use (51:42 B5, 32:00 B12, 55:09 D2) are all in Latin-letter turns the detector cannot read — each is a real use.

## Decisions (one line each)
For Medi:
- Grammar % counts every slip Amal fixed as a use of its rule (Grammar Console formula) and leaves the 58 slips in the
  4 rules with no counter out of the % (listed): yes / no?
- Word Bank counts the lesson audit's word slips (Known 274 → 246, Mastered 110 → 88, Accuracy 83.7 → ≈70.8): yes / no?
- Rule conflict: 7 slips on a preposition (مع, عند, قبل, زي, فوق) count in the Lessons Words % (decision A + on-list
  verdicts) but the Word Bank never scores prepositions (SESSION-DECISIONS 09-21). Count them as word slips: yes / no?
- Rule conflict (for area 5): the Grammar Console counts 39 fixes Amal only typed in chat; memory note 09-23 (5dc85b8)
  said chat-only fixes are dropped, decision A (09-25) says "voiced or typed" counts. Keep counting typed fixes: yes / no?
- "≈" marks percentages only, not counts (lessons, slips, words known): yes / no?
For Amal: none from this area (nothing here needs her).

## For the coordinator (files I do not own)
- **Rebuild order must include `python scripts/full_audit_build.py` first**, then build_grammar_console.py, then
  build_lessons_page_data.py (it now also writes the NEW file `docs/data/word-bank-audit-slips.json` — `git add` it;
  every page that scores words loads it). Then `python scripts/check_numbers.py` must print `numbers: OK`.
- `scripts/accuracy_gates.py` validate(): 11 lessons fail "grammar.mistakes N != M speaking grammar rows" because
  `a_rows` does not drop the rows Amal's notes rule out. Fix: in the `a_rows` filter add
  `and not amal_grammar_notes.ruling(dict(r, bucket=r.get("bucket") or "B18"))` (same as build_lessons_page_data).
  Pre-existing on 3c2835c, not caused here.
- `scripts/accuracy_gates.py` annotate(): `totals.*.unverified_avg_pct` is a plain mean of lesson % (like the old
  Lessons page); per decision 6 it should be pooled (Σ(right + ½ partial) ÷ Σ scored; Σ(uses − scored_mistakes) ÷ Σ
  uses). `verified_avg_pct` excludes unverified lessons while the pages' averages include them with ≈ (decision 4):
  not shown on any page today, so no visible conflict; say so if it is ever shown.
- Grammar `verified_pct` in annotate uses `len(gitems)` (all slips) over `den["uses"]` (its own denominator); with
  grammar_math the lesson has `grammar.uses` and `grammar.scored_mistakes` — use those so a verified grammar % equals
  the page's number.
- Flashcards (not mine): cards-core / cards-selection / flashcard-progress do not load
  `word-bank-audit-slips.json`, so the Flashcards "Shaky / Wrong from lessons" tiles still use the Word Bank without the
  slips. Load it and pass the events through `AneesWordBankReview.withSlips(events, doc)` before `apply()`.
- The publish guard: `python scripts/check_numbers.py` (offline, ~2 s, needs node at C:/dev/tools/… or on PATH;
  `ANEES_NODE` overrides). Exit 0 = OK, 1 = FAIL (one line reason), 2 = data unreadable.

## Not done
- 09-28 has no reader sheet-verdict pass (memory rule anees-list-by-meaning): 18 on-list slips were keyed by string
  match; 8 partial matches are held out of the Word Bank until a reader names the word (e.g. عالمة matched 3Alam
  "world"). Needs the reader pass (area 5/8).
- 15 near pairs remain in the audit (same moment, overlapping wrong piece). 13 are two different rules at one moment
  (e.g. 09-28 32:18 A1 el- + A8 gender) = two slips, kept. 2 are candidates for "one episode, one result" and were NOT
  merged (a human or Codex rules): 08-25 08:50/08:54 مغني (cloudy → singer, then the gloss of مغني), 09-21 14:43/14:46
  B18 دلوا then دل (plural, then masculine, for one pizza). The union fix also merged 09-21 48:38 الـ آخر تاني into
  48:02 الـ تحت تاني (two wrong tries at عكس in one episode) — reversible in `duplicates.json` logic if Medi disagrees.
- AI Reports cards are dated snapshots (e.g. report #7 "961 rows"; the audit now has 1,065) — not re-derived here.
- Tutor / Flashcards / Fluency-ladder percentages not marked ≈ (Fluency ladder "7 words at 90 %" is lesson-derived);
  Progress›Grammar "1 in 4 sentences corrected" and statuses not marked (statuses are bands of ≈ scores).
- Python `round()` is half-to-even (Console rule 62.5 % shows 62, JS would show 63); status uses the same rounded
  number, so no band disagrees today.
