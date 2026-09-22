# NEXT PROMPT — Flashcards selection screen

Approved by Medi 2026-09-21 ("go"). Paste the block below into a fresh Claude chat.

---

You are continuing the Anees application (https://github.com/TheNatanzi/anees, live at https://thenatanzi.github.io/anees/). The local clone C:\dev\anees is stale with uncommitted files: do NOT touch it. Work in a fresh git worktree from origin/master.

Read first: `plan/FLASHCARDS-SELECTION-SPEC-2026-09-21.md` (the approved build contract), `plan/SESSION-DECISIONS-2026-09-21.md` (Flashcards section at the end), then `docs/cards.html`, `docs/js/cards-core.js`, `docs/js/fsrs.js`, `docs/js/word-bank-core.js`, `docs/data/quizlet/amal-quizlet-sets.json`.

Job: build the labelled selection screen as the first screen of cards.html, exactly as the spec's 9 sections. Keep the Quizlet-style swipe card, Sabz skin, FSRS queue, undo and timing as they are.

Rules:
- Decisions in the spec are final. Ask Medi only what the spec leaves open: one question per message, recommendation + number, no rule recaps.
- Never browse Stitch. Quizlet only through Medi's Chrome, never solve a bot check.
- Tests: add queue/selection tests to `tests/test_fsrs.cjs` (or a new `tests/test_cards_selection.cjs`). Browser-check with writes stubbed (`window.fetch` POST/PATCH → fake 201) so no test answers land in `card_results`.
- Validation before every push: node --check on changed JS and the inline script of cards.html; node tests/test_fsrs.cjs; node tests/test_vocabulary_memory.cjs; node tests/test_word_bank.cjs; node tests/test_word_bank_reliability.cjs; node tests/test_context_review.cjs; node tests/test_vocabulary_stats.cjs; node tests/test_transcript_player.cjs docs/js/transcript-player.js; python -m pytest -q tests/test_m5_cards.py (hits the live DB and cleans up; confirm card_results count is unchanged after); git diff --check; python scripts/write_build.py; push; wait for Pages; check the live page.
- `node scripts/audit_word_bank_reliability.cjs` rewrites docs/data/word-bank-audit*.json; revert those unless that is the job.

Format for Medi: one line answer first, then a table for anything with numbers, then short bullets, then one bold action. Never walls of text.

Begin by building; the first message to Medi is the finished screen (screenshot + counts per section), or one question if the spec truly leaves something open.
