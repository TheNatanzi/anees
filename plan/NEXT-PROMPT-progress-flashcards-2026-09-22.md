# NEXT PROMPT — Progress & Stats: Flashcards tab

Paste the block below into a fresh Claude chat.

---

You are continuing the Anees application (https://github.com/TheNatanzi/anees, live at https://thenatanzi.github.io/anees/). The local clone C:\dev\anees is stale with uncommitted files: do NOT touch it. Work in a fresh git worktree from origin/master. Another chat may be building verb drills (plan/VERB-DRILLS-SPEC-2026-09-22.md) at the same time: pull/rebase before every push and do not edit its files.

Read first: `plan/PROGRESS-STATS-FLASHCARDS-SPEC-2026-09-22.md` (Medi's approved layout and rulings, final), then `docs/progress.html`, `docs/js/vocabulary-progress.js`, `docs/css/vocabulary-progress.css`, `docs/js/fsrs.js`, `docs/js/cards-core.js`, `docs/cards.html`, `plan/PROGRESS-STATS-VOCAB-SPEC-2026-09-21.md` (the Vocab tab's look to match).

Job: make TAB 2 Flashcards live on progress.html exactly as the spec. Root tags are removed. Weekly goal 50 words, monthly 200.

Rules:
- Rulings are final. Ask Medi only what the spec leaves open: one question per message, recommendation + number, no rule recaps.
- Never browse Stitch.
- Pure logic in a testable module (e.g. docs/js/flashcard-stats.js) with tests in tests/test_flashcard_stats.cjs.
- Browser checks with writes stubbed (`window.fetch` POST/PATCH → fake 201); `card_results` count must stay 7 after tests.
- Validation before every push: node --check on changed JS and inline scripts; every `node tests/*.cjs` listed in plan/NEXT-PROMPT-flashcards-selection-2026-09-21.md plus tests/test_cards_selection.cjs and the new test; python -m pytest -q tests/test_m5_cards.py; git diff --check; python scripts/write_build.py; push; wait for Pages; check the live page on phone width too.

Format for Medi: one line answer first, then a table for anything with numbers, then short bullets, then one bold action. Never walls of text.

Begin by building; the first message to Medi is the finished tab (screenshot + the numbers in each box).
