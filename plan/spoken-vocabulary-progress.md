# Spoken Vocabulary progress — September 21, 2026

> **Status: superseded as a screen specification.** The calculations below remain useful implementation history, but they do not define the approved Progress & Stats layout. On September 21, Medi rejected the interpreted dashboard and directed: reproduce Stitch screen `d36a5029632e4f8fa37eb6378f590acf` exactly, after a one-question-at-a-time interview about every box. Do not simplify, substitute, or remove sections based on the phrase “broad aggregate data.” See `plan/SESSION-DECISIONS-2026-09-21.md`.

The Word Bank specification and September 21 review rules remain authoritative for demonstrated grades, eligibility, scored forms, and correction handling. This page does not introduce a replacement grade or combine flashcards with speaking.

## Confirmed product decisions

- Scope correction: Progress & Stats contains broad aggregate totals and charts only. No individual vocabulary lists, searches, or word drilldowns. Specific words, history, and per-word decay belong exclusively in the Word Bank.

- Focus on vocabulary growth and retention. Timing belongs in Fluency; practice recommendations belong in Tutor Hub.
- Existing document vocabulary has been studied. New means newly added by Amal, never newly observed by the transcript pipeline.
- Dashboard counts use the existing scored-entry unit: verb tenses separately, singular/plural separately, masculine/feminine together. Prepositions and grammar are excluded.
- Six cards: words known (Good + Mastered), Mastered, unique entries practised in the selected period, newly added entries, memory at risk, and not yet checked.
- Growth replays the corrected original attempt histories. Do not fabricate progress before the earliest available scored evidence. Missing lessons do not count as failures.
- Demonstrated knowledge and predicted memory stay separate. Existing Overall Accuracy and 30-Day Memory formulas remain unchanged in the Word Bank.
- Starting memory bands: Strong under 14 days, Fading 14–20, At risk 21–34, High risk 35+.
- Only full-credit recall restarts the clock, including self-correction before help. Hints, misses, tutor speech, and echoes do not restart it.
- Display levels and time since successful recall, not an uncalibrated recall probability.
- Show the same spoken memory estimate beside each scored Word Bank form. Any flashcard memory is calculated from its separate history.
- No qualifying attempts: Not yet checked. Attempts but no full-credit answer: No successful recall. The latter is not falsely classified as untested or assigned an invented success date.
- Missing document-addition dates display a dash and an explanation, not zero or a fabricated new-word count.

## Initial adaptive heuristic — implementation choice, not validated research

The exact coefficients below were not individually approved in the planning conversation. They are an explicit conservative starting implementation of the approved adaptive-window goal; they require calibration against later recall results.

1. Replay only eligible scored attempts chronologically in one track.
2. After a full-credit answer, record the positive calendar-day gap from the preceding full-credit answer only if they belong to different lessons (review days for cards) and no hint or miss intervened.
3. Let G be the second-largest qualifying gap since the latest miss. Fewer than two qualifying gaps means G = 0. Two gaps prevent a single lucky recall or repetitions in one lesson from stretching a window.
4. Multiplier m = min(2, max(1, G / 14)). Thresholds are round(14m), round(21m), and round(35m). The upper bound is an engineering guard, not a scientific constant.
5. A miss clears the extension and applies an At risk floor. A hint applies a Fading floor; it cannot erase a prior miss. Full-credit recall clears these floors and restarts the clock. This changes only the memory estimate, never the agreed spoken grade.
6. Always preserve the actual date and age of the last full-credit recall. Apply the worse of elapsed-time band and the outstanding outcome floor. An existing High risk label cannot improve after a miss.

Examples: one success 20 days ago → Fading. A miss today leaves that date intact and shows At risk. Two successful 21-day gaps produce thresholds of 21 / 32 / 53 days. A subsequent miss removes that extension immediately. A nine-correct, one-wrong latest-10 history can still be Mastered under the agreed grading rules while its separate memory estimate reads At risk.

## Limits and verification

These are transcript-based estimates over published evidence. No claim of listening to every recording or of calibrated memory probabilities is made. Longer windows are a heuristic, not FSRS or a fitted half-life regression model. Keep outcome floors and window parameters visible in method details for review.

The unit suite checks exact boundaries, hint/miss behavior, self-corrections, grammar/repetition exclusion, track separation, two-gap extension, failure reset, historical replay, invalid dates, and agreement with Word Bank counts. Browser QA covers loaded evidence, aggregate-only dashboard content, activity period, Word Bank memory labels, and desktop/mobile layout.
