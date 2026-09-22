# NEXT PROMPT — Verb drills

Paste the block below into a fresh Claude chat.

---

You are continuing the Anees application (https://github.com/TheNatanzi/anees, live at https://thenatanzi.github.io/anees/). The local clone C:\dev\anees is stale with uncommitted files: do NOT touch it. Work in a fresh git worktree from origin/master.

Read first: `plan/VERB-DRILLS-SPEC-2026-09-22.md` (Medi's rulings, final), then `docs/data/word-bank-catalog.json`, `scripts/build_word_bank_catalog.py`, `docs/js/cards-selection.js`, `docs/cards.html`, `docs/js/word-bank-core.js`, `docs/data/quizlet/amal-quizlet-sets.json`.

Job: build the spec in its order. Step 1 ends with the hold-one-out hit rate shown to Medi before any guessed form ships.

Rules:
- Rulings in the spec are final. Ask Medi only what it leaves open: one question per message, recommendation + number, no rule recaps.
- Never browse Stitch. Quizlet only through Medi's Chrome, never solve a bot check. Send nothing to Amal without Medi's yes.
- Browser checks with writes stubbed (`window.fetch` POST/PATCH → fake 201); `card_results` count must be unchanged after tests (7 on 2026-09-22).
- Validation before every push: node --check on changed JS and the inline script of cards.html; every `node tests/*.cjs` listed in plan/NEXT-PROMPT-flashcards-selection-2026-09-21.md plus tests/test_cards_selection.cjs; python -m pytest -q tests/test_m5_cards.py; git diff --check; python scripts/write_build.py; push; wait for Pages; check the live page.

Format for Medi: one line answer first, then a table for anything with numbers, then short bullets, then one bold action. Never walls of text.
