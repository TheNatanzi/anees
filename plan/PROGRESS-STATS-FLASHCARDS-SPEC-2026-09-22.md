# Progress & Stats — Flashcards tab specification (Medi, 2026-09-22)

Build contract for TAB 2 **Flashcards** on `docs/progress.html` (today dimmed "planning").
Source: Medi's written layout pasted 2026-09-22, plus his rulings below. Same look as the
Vocab tab (vp-card, serif numerals, Sabz skin, transcript colours). Data = `card_results`
replayed through `docs/js/fsrs.js` (nothing else stores FSRS state). Never browse Stitch.

## Rulings (final)

- **Goals:** weekly goal **50 words**; monthly goal **200 words** (4 × weekly; editable later).
  "Words" = distinct cards answered in the calendar week / month (Mon–Sun, local time).
- **Root tags: removed.** No root column, no root text anywhere.
- Grades stay binary (Know / Still learning). No Hard / Easy, no ease factor.
- Empty data → "—" + a one-line reason. Never invented history.

## 1 · Top row — goals & workload

| Box | Value | Sub-line |
|---|---|---|
| Target retention | segmented [80 · 85 · 90 · 95%], shared with cards.html (`anees-cards-pref.retention`) | drives every number marked *(ret)* |
| Weekly goal | N of 50 words + bar | "% met" |
| Monthly goal | N of 200 words + bar | "% met" |
| Reviews needed *(ret)* | reviewed cards due by end of today at the selected retention (+ learning cards due) | "Total reviews required today to maintain target curve." |
| Required passes *(ret)* | ceil(reviews needed × target retention) | "Cards you must answer correctly to stay ahead of the curve." |
| True retention | pass rate on answers to mature cards (interval ≥ 21 d at answer time), all time | "Actual historical performance on mature cards." "—" until one mature answer exists |
| Leech words | cards with ≥ 8 lapses | "Chronically failed cards requiring intervention." Click → queue filtered to leeches |

## 2 · Charts

- **A · Forgetting curve & retention threshold** — average retrievability of all reviewed cards,
  from the first answer to today + 30 days, computed with FSRS (current params, selected retention).
  Dotted horizontal line at the target. A marker on each day with a correct review ("memory bumped").
  "—" chart state until 1 review exists.
- **B · Review forecast (next 7 days)** *(ret)* — bars = cards due per day (`F.forecast`), x = day names, y = cards.

## 3 · Memory segmentation (New vs Old)

| Column | Count | Second number |
|---|---|---|
| New (unseen / just added) | cards never answered | Pass rate = % correct on each card's first answer |
| Learning (interval < 21 d) | reviewed, not mature | Pass rate = % correct on answers while learning |
| Mature / old (interval ≥ 21 d) | mature cards | Total lapses (times forgotten) |

## 4 · Review queue table

Columns: Arabic word (Arabizi + Arabic) · English (hidden until tapped) · Phase badge (New / Learning / Mature)
· Current interval (e.g. 14 days, "—" new) · Lapses · inline **✗ Don't know** / **✓ Know it**.
Rows = today's queue (`AneesCards.queue`), same order as cards.html. A grade writes the same
`card_results` row (+ flip_ms null, answer_ms from row reveal) and the row leaves the table; undo last.
English is never shown before grading unless tapped (tap = reveal, still gradeable).

## Validation

As in plan/NEXT-PROMPT-flashcards-selection-2026-09-21.md; browser checks with writes stubbed;
`card_results` count unchanged (7 on 2026-09-22); check the live page.
