Read `C:\dev\anees-hourly\RULES.md` first, then `wiki/18-grammar-buckets.md` and `docs/data/grammar-buckets.json` (56 buckets, A1–F3 + E5).

GOAL: find EVERY time Amal corrected Medi on something that is NOT vocabulary, in all 11 recorded lessons
(08-25, 09-04, 09-05, 09-10, 09-11, 09-14, 09-15, 09-16, 09-17, 09-18/19, 09-21, 09-23), name the grammar mistake
he made, and file it in a bucket. No correction may be left unaccounted for. If one fits no bucket, propose a new bucket.

Before starting, ask Medi ONE question to confirm scope (e.g. "Pronunciation corrections: skip them or list them
separately?"), then work without further questions until the report.

## What counts
- A correction = Amal says the fixed form OUT LOUD in the voice lesson after Medi said something wrong (recast, "no, X",
  finishing his sentence the right way, naming the rule: "it's feminine", "which preposition?").
- NOT a correction: vocabulary (he didn't know or picked the wrong word -> that is the Word Bank's job; list these
  separately, don't bucket them), pronunciation only (F-family, rule S4), his own self-corrections before she speaks,
  her just repeating a correct answer, pauses (S5).
- Meet chat: context only (Medi 2026-09-23). A fix Amal ONLY typed in the chat never counts on its own; use chat to
  understand what was said in the voice lesson.

## Where the data is
- Transcripts: `C:/dev/anees/data/lessons/<date>/` (transcript.txt or scribe per-speaker files) and lesson pages
  `docs/lessons/<date>.html`. Lesson clock = the page audio. `scripts/lesson_turns.py` gives speaker turns on one clock.
- Machine audit already done: `docs/data/grammar-audit.json` (from `scripts/audit_grammar_lessons.py`; ~85% precision,
  recall only ~40-77% -> it MISSES many corrections; this sweep is to close that gap). Hand-verified tally:
  `docs/data/tally.json`. Gold sets: `docs/data/grammar-goldset.json` (09-17, 09-21 tuned; 09-11 held-out).
- Arabizi display: always Amal's spelling (S1 + 2026-09-23 amendment), converter `docs/js/word-bank-arabizi.js`
  + `docs/data/arabizi-extra.json`. Amal writes ص as "s", not "9".

## Method
1. Go lesson by lesson, EVERY Amal turn that follows a Medi turn. Read the exchange in context (a few turns either side).
2. For each real correction record: date, time, Medi said (Arabic + Arabizi), Amal said, the exact change
   (wrong -> right), grammar mistake in plain words, bucket id, confidence, and whether the machine audit already has it.
3. Vocabulary corrections -> separate list (word, date) for the Word Bank; not bucketed.
4. Anything that fits no bucket -> group similar ones; for each group propose a bucket (id in the right family, name,
   one_line, 2-3 examples in her spelling, why, detail) - same shape as grammar-buckets.json. Do NOT add it yet.
5. Hand-check yourself: re-read a random 20 of your own rows against the audio/transcript; report the score.

## Output
- `plan/GRAMMAR-CORRECTION-SWEEP-2026-09-24.md`: per-lesson table + totals per bucket + "machine audit caught / missed"
  + vocab list + proposed new buckets.
- `data/grammar-sweep-2026-09-24.json`: the rows (machine-readable) so a later step can feed them into the console as
  verified slips.
- Don't change scores, buckets, the console or the Word Bank in this pass. Transcription costs money: never
  re-transcribe (09-23 Medi's first 22.6 min is untranscribed; note the gap, don't pay for it). Nothing is emailed or sent.

Report to Medi in his format (one line, a picture - a bucket-count chart, short bullets, one bold action) and ask him
to approve each proposed new bucket one at a time.
