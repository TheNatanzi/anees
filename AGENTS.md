# Anees - read this first (every agent: Claude, Codex)

1. `RULES.md` (S1-S6) binds everything. Only Medi changes it, in writing.
2. Before building in an area, run `python scripts/rule_registry.py show <scope>` (transcription, arabizi, word-scoring,
   grammar-scoring, lessons, amal-data, pages, audio, flashcards, process) and follow every live rule it prints.
3. Every correction from Medi or Amal (RULES.md S6): fix the moment through the ruling files (never delete a row), add
   one entry to `rules/registry.json` with his or her exact words, and enforce it - code + a test the publish guard
   runs, or a READER-BRIEF line + the real moment as `example`. A new row in `rejected.json`, `duplicates.json` or
   `grammar-usage-rulings.json` carries `"rule": "<id>"` (or `"one-off: <reason>"`).
4. `python scripts/rule_registry.py check` must print OK before any push (the publish guard runs it).
5. Tell Medi one line: "Added GR-14 (code + test); changed 3 past moments." Never recap rules to him.
6. Amal is never asked anything by code or by an agent; Medi sends her links.

## Agent-process rules (registry ids; Codex cannot read Claude's memory notes, so they live here)

- TR-05 lesson window: the lesson runs from Amal's first word to her last; off-lesson talk is not scored.
- TR-06 no silent clips: never make Medi judge a silent or empty clip.
- PR-07 transcript first: a trustworthy transcript comes before everything built on it.
- PG-03 new pages copy the Anees shell (header, tabs, Sabz skin) and follow the same pattern as existing pages.
- PR-02 low security: no passwords or security friction on Anees; lesson audio and transcripts are public by choice.
- PR-03 grill Medi with one question at a time before a big task.
- PR-04 never recap rules to Medi or ask him to review them.
- PR-05 flag conflicts first: when an ask conflicts with what exists, ask ONE question before building.
- PR-06 push guarded master yourself: `python scripts/publish_guard.py check` OK and a fast-forward of origin/master;
  never force; rebase and re-run generated builders instead of hand-merging generated JSON.
- PR-08 every ask ticked: keep a checklist of every ask in the session (including messages typed mid-run) and tick
  each one before reporting done; at the end, map each of Medi's corrections to a registry id or a one-off reason.
  The list comes from the transcript, not memory: `python scripts/session_asks.py list --session <id>` shows every
  message Medi typed (mid-run ones included), `tick <n> --note "..."` / `--not-done "why"` closes each, and
  `check --session <id>` must print OK before the final report (name every NOT DONE line in it).
