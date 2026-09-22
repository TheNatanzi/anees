# Progress & Stats — Vocab page specification (interview of 2026-09-21)

Status: **approved by Medi 2026-09-21 ("go")**. This file is the build
contract for `docs/progress.html`. It supersedes `plan/spoken-vocabulary-progress.md`
as the screen definition. Scoring, memory and transcript rules stay in
`plan/SESSION-DECISIONS-2026-09-21.md` and `plan/word-bank-specification.md`;
nothing here changes them.

## Blueprint and skin

- Layout: Stitch project 7225636314948596133, **starred** screen
  "Arabic Dashboard – Vocab Macro-Overview". Only starred Stitch screens are
  approved; the unstarred "Progress & Stats" screen (FSR-4, Ebbinghaus,
  register, radar) is planning phase and is not built.
- Skin: Sabz brand book (`C:\dev\ganjsta-ui\docs\BRAND-SABZ.md`,
  `docs/brand/sabz-tokens.css`): paper background, serif numerals, hairline
  cards, washes never under data. **Medi removed the "no red / no blue"
  rule for this page**: chart colours follow the transcript convention
  (green correct, orange hinted, red wrong, blue learning/accent).
- Nav: the existing Anees sidebar. The mock's search box, top nav, "Sync
  Telemetry" and "Start SRS Session" buttons are dropped.

## Header

- Title: **Progress & Stats**.
- Time Horizon pills: **Week · Month · All time**, default Month. "Day"
  dropped. The pills drive every card and chart marked *period*.

## Top row — 4 cards

| # | Label | Value | Sub-line | Period | Trend | Click | Empty |
|---|---|---|---|---|---|---|---|
| 1 | Lessons | count of loaded lessons (distinct lesson dates in evidence) | "N recordings waiting to load" when the queue is non-empty | pill | +N this week vs previous week | Lessons & Audio | "0 lessons · no recordings yet" |
| 2 | Lesson hours | sum of recording lengths, hours, 1 decimal | average minutes per lesson | pill | +N h this week | Lessons & Audio | "0 h · no recordings yet" |
| 3 | Words known | forms with status Good or Mastered (today 158 of 1,994) | "% of studied forms · Mastered: N" | All time | +N this week newly Good/Mastered | Word Bank, filter Good+Mastered | "0 known · no scored lessons yet" |
| 4 | Talk time | **PARKED** with the lesson work. Slot stays, dimmed, "after lessons load". | — | — | — | — | — |

No targets or benchmarks on any card (the mock's 115% pace, 1,428 target,
top quartile are placeholders and are not shown).

## Tab row

Vocab · Flashcards · Verbal Lexicon · Fluency & Complexity · Grammar, kept as
drawn. Only **Vocab** is live. The other four render dimmed with "planning"
and do nothing on click. The Flashcards "N due" badge comes later from the
cards track.

## Vocab row — 4 cards

| # | Label | Value | Sub-line | Period | Trend | Click | Empty |
|---|---|---|---|---|---|---|---|
| 1 | Studied forms | count of active scored forms (verb tenses separate, singular/plural separate, grammar and prepositions excluded); today 1,994 | "N words in Amal's list" (document rows, today 2,136) | All time | "+N added" from document add dates; "—" until dates exist | Word Bank, no filter | "0 · vocabulary list not synced" |
| 2 | Mastered | forms with status Mastered; today 63 | "% of studied forms · Good N · Shaky N · Wrong N" (today 95 · 18 · 2) | All time | +N newly Mastered in period | Word Bank, filter Mastered | "0 · no form has two-lesson evidence yet" |
| 3 | Words per lesson | distinct scored forms attempted ÷ loaded lessons in period (today ≈ 48) | "Peak: N on <date>" | pill | vs previous period | Word Bank sorted by last said | "— · no scored lessons in this period" |
| 4 | Correct vs slips | full-credit attempts ÷ all scored attempts; **hints count as slips**; today 407 of 436 = 93% | "N correct · N hinted · N wrong" + green/red bar | pill | vs previous period | Word Bank, filter Shaky+Wrong | "— · no scored attempts in this period" |

## Charts (2 × 3 grid, as drawn)

1. **Vocabulary Funnel & Momentum** — stacked area, one point per loaded
   lesson. Four bands bottom→top: Mastered · Good · Shaky+Wrong · Not yet
   checked. Legend shows today's counts. X = lesson dates, Y = forms.
   Period: pill. Hover: counts for that lesson. Empty: "chart appears after
   the first scored lesson".
2. **Vocab Retention Over Time** — one line, one dot per lesson. Value = of
   the forms already Good/Mastered *before* that lesson that came up in it,
   the share given full credit. First appearances never count. No benchmark
   line. Caption: "N known words tested this lesson". Period: pill. Empty:
   "—" until a known word is tested in a later lesson.
3. **Incorrect vs Correct Ratio Over Time** — one 100% bar per lesson,
   three stacks: green correct · orange hinted · red wrong. Correct % on top.
   **Dashed average line** of correct % across shown lessons. Captions:
   "Baseline: first lesson %" and "Best: N% on <date>". Period: pill. Hover:
   the three counts. Empty: as chart 1.
4. **Unique Words Per Lesson** — line with dots, one per lesson = distinct
   scored forms said. Dashed average line. Peak dot labelled "Peak: N". Date
   + count under each dot. Period: pill. Empty: as chart 1.
5. **Sections** (mock: Part-of-Speech Distribution) — horizontal bars grouped
   by **Amal's section headings** (no part-of-speech tag exists), largest
   first, top 8 with "show all". Filled = known forms, grey = not known,
   "N known / N total" at right, Arabic label beside the heading. Period: All
   time. Click: Word Bank filtered to that section. Empty: "sections appear
   after the vocabulary list syncs".
6. **New Words Learned Over Time** — bars = forms Amal added per week, line =
   cumulative. Pills Weekly · Monthly · Cumulative kept. Sub-stats: Total
   added · Per week · Peak week · Still known %. Source: document sync add
   dates only. Today none exist → "no add dates yet, starts at next sync",
   empty bars, no fabricated history. Click: Word Bank sorted newest added.

## Footer

Muted provenance line: "N lessons loaded · last lesson <date> · N recordings
waiting". No pace, no target.

## Global rules

- Every number comes from the same reviewed evidence the Word Bank uses
  (`word-bank-core` models + `vocabulary-memory`), live Supabase first,
  published JSON fallback, as today.
- Aggregates only: no word lists, no per-word rows on this page. Clicks go to
  the Word Bank.
- Nothing invented: unknown = "—" with a one-line reason.
- Mobile: single column, same order.

## Validation before publish

```
node --check docs/js/vocabulary-progress.js
node tests/test_vocabulary_memory.cjs
node tests/test_word_bank.cjs
node tests/test_word_bank_reliability.cjs
node tests/test_context_review.cjs
node tests/test_transcript_player.cjs docs/js/transcript-player.js
node scripts/audit_word_bank_reliability.cjs docs/data/word-bank-evidence.json
git diff --check
```
Then confirm the GitHub Pages deploy and check the live page.
