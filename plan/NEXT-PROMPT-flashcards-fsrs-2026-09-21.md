# NEXT PROMPT — Flashcards engine (FSRS) then the Flashcards stats tab

Approved by Medi 2026-09-21 ("go"). Paste the block below into a fresh Claude chat.

---

You are continuing the Anees application (https://github.com/TheNatanzi/anees, live at https://thenatanzi.github.io/anees/). Read first: README.md, plan/SESSION-DECISIONS-2026-09-21.md, plan/word-bank-specification.md (flashcard sections), plan/PROGRESS-STATS-VOCAB-SPEC-2026-09-21.md, this file. The local clone C:\dev\anees is stale with uncommitted files: do NOT touch it. Work in a fresh worktree from origin/master.

## Decisions already made (do not re-ask)

- Scheduler = **FSRS with the published default weights**, binary grades **Again / Good** only. Label everywhere: "default parameters, not fitted to you" until ~1,000 reviews exist. Desired retention default **90%**, selectable 80 / 85 / 90 / 95.
- Flashcards are a separate track from spoken vocabulary. Card *grade* (Good / Mastered by the agreed attempt rules) stays separate from card *scheduling* (FSRS state), the same split spoken vocabulary uses. Spoken memory keeps its conservative heuristic; it is not FSRS.
- Phases: New = never reviewed; Learning = interval under 21 days; Mature = interval 21 days or more. Leech = 8 lapses (Anki default).
- Anki features to include: daily new-card limit (default 20), bury sibling forms (tenses/plural of one word not on the same day), undo last answer. Skip Hard / Easy and ease factor.
- Retrieval must be real: never show the English beside the Arabic before grading. Reveal, then Again / Good.
- Two grading surfaces (cards.html and the future stats-tab queue) must write the same event log.
- Root tags (ك-ت-ب) are parked: no root field exists on words. Do not invent roots.
- Never restate the scoring rules to Medi; ask the question with a recommendation and a number.

## Build order

1. `docs/js/cards-core.js` (or a new `docs/js/fsrs.js`, UMD like vocabulary-memory.js): FSRS state per card (stability, difficulty, due, interval, lapses, reps, last review), `schedule(card, grade, now, desiredRetention)`, `retrievability(card, now)`, forecast(days), leech detection. Unit tests in `tests/test_fsrs.cjs`.
2. Durable storage: a `card_reviews` table (Supabase project yljcbdxvnkfrwvelypfu, anon key in docs/js/config.js, RLS as the other tables) holding every answer; keep the localStorage queue as the offline buffer that flushes to it. Check `word_events` first: the existing card answers may already be there.
3. `docs/cards.html` on the scheduler: due queue (learning first, then due reviews, then new up to the daily limit), Again / Good, undo, sibling burying, counts "N due · N new · N learning".
4. Backfill: replay the existing card log (localStorage `anees-card-log`, last 2,000, plus any DB rows) through FSRS in date order so history is kept.
5. Only then: the Flashcards tab on progress.html from Medi's STARRED Stitch flashcards screen (project 7225636314948596133; open the project, Ctrl+K "Go to …" — direct screen URLs 404). One question per message, visual order, recommendation + number, recap every few questions, final spec for approval before code. Medi's written spec for the tab is in the 2026-09-21 chat and summarised in memory: retention toggle, weekly/monthly goals, reviews needed + required passes, true retention (mature), leeches; forgetting curve + 7-day forecast; New / Learning / Mature block; review-queue table with inline ✗ / ✓ (Arabic shown, gloss hidden until reveal).

## Validation before publish

node --check on every changed JS; node tests/test_fsrs.cjs; node tests/test_vocabulary_memory.cjs; node tests/test_word_bank.cjs; node tests/test_word_bank_reliability.cjs; node tests/test_context_review.cjs; node tests/test_vocabulary_stats.cjs; node tests/test_transcript_player.cjs docs/js/transcript-player.js; node scripts/audit_word_bank_reliability.cjs docs/data/word-bank-evidence.json; git diff --check; python scripts/write_build.py; then push, wait for the Pages deploy, verify the live page.

Begin with exactly one question: "Do the existing card answers live in the `word_events` table, or only in the browser? My recommendation: I check the table first and report what I find before writing any schema."
