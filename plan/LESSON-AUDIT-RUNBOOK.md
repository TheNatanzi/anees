# Lesson audit runbook (2026-10-10)

Medi 2026-10-10: "do a full audit of the lesson and use the corrections I made to make final rule adjustments and
corrections. Then apply it to 10-9. Audit 10-9 at least 4-5 times until you are sure that you can replicate all the
steps ALL THE STEPS we took to fix 10-8."

Every step that fixed 10-08, in order. 10-09 went through all of them on 2026-10-10 (5 audit passes).
Windows: `set PYTHONIOENCODING=utf-8`, `ANEES_REHEAR_AUTO=off`, `ANEES_TRANSLATE=off` for builds.

## A. The lesson is loaded (the hourly job / another session)
1. Transcription, both tracks; page data built (`build_lessons_page_data.py`).
2. Same-day review: `python scripts/review_lesson.py <date>` (two readers, third reader, pages, Arabizi gaps, Amal's items).
3. Second listen (TR-22 / TR-29), applied; the tutor-listen cases wait for Amal.
4. English under every line: `python scripts/translate_lines.py <date>` (PG-40; run again after any text fix).

## B. Medi's own notes on the page (when he has graded the lesson)
5. `python scripts/medi_corrections.py pull` (his rows + the note reader's rows).
6. `python scripts/lesson_audit.py <date> --notes` lists every note with today's chips. Read EACH one:
   - his `X*` = the right form, `(not Y)` = what the line wrongly shows (TR-30). A transcript fix, never a slip.
   - the note reader's misreads (Latin onto an Arabic line, an 'add' made of a transcript note, a confirming row
     that drops the second listen) are undone with an `undo` row and re-written in her letters in
     `data/lesson-work/medi-corrections-hand.json` (his corrections, append-only).
   - a slip he names: an `add` row (her voiced fix in the 15 s after = tier A, else tier B on her page).
   - 'this wasn't a mistake, I was asking': a `not-slip` row, reason `asking`.
7. Each note that is a pattern becomes a rule in `rules/registry.json` (S6) with code + a test.

## C. The audit (no notes needed: what Medi's notes taught us to look for)
8. `python scripts/lesson_audit.py <date>` and read every section:
   1. coverage: every Arabic word of his has a mark (WS-30) - must be 0 missing.
   2. grey chips by reason: a reason that only restates a standing rule is hidden (PG-43); every grey chip names its
      word in Arabizi (PG-44).
   3. 'not on her word list': read each against her lines and her chat. His sounds (WS-37: ق / غ / ء one sound,
      ذ / ظ, ت / ط, a long a); place names; a misheard word the TUTOR's line or chat proves -> a TR-31 row in
      `data/lesson-work/transcript-fixes.json` (rule TR-31, by claude-audit-<date>, the evidence in 'why'). No evidence
      from her, no fix.
   4. Latin / * on an Arabic line (TR-30).
   5. her مهم still a word (PG-45).
   6. the same word credited twice in a row (WS-36).
   7. a ✓ on his English question about her words (WS-36).
   8. lines with no English (PG-40) - fillers may stay empty.
   9. her lines whose English reads wrong ('A flying tree') - her line misheard: fix only with evidence.
   10. every ✗ with her next line: is there a signal (S3)? his question is not a slip.
9. Grammar, line by line (GR-34): four readers check every rule on every line; general patterns go into
   `scripts/detect_grammar_usage.py` (GR-34 / GR-35); the moments left go into `data/grammar-usage-additions.json`
   (missed uses) and `data/grammar-usage-rulings.json` (false uses), rule GR-34, each read against her words first.
10. Arabizi: `node scripts/arabizi_gaps.cjs` must say 0; fill `docs/data/arabizi-extra.json` (scope 'lessons').

## D. Build, check, publish
11. The hourly job's order:
    `full_audit_build.py` -> `apply_amal_audit_rulings.py` (her answers, read-only) -> `detect_grammar_usage.py` ->
    `build_lessons_page_data.py` TWICE -> `build_grammar_console.py`, `build_amal_grammar_rules.py`,
    `build_amal_review.py`, `build_tutor_data.py`, `build_student_data.py`, `build_tutor_weak.py` ->
    `accuracy_gates.py annotate` -> `lesson_ledger.py check` (OK) -> `rule_registry.py check` (OK) ->
    `build_rule_book.py`.
12. `git add -f` the new clips `docs/data/word-bank-clips.json` names; `git checkout -- docs/data/tutor-notes.json`.
13. Push only through `python scripts/publish_guard.py push --source "manual: <what>"`.
14. Re-run step 8 after the push: the audit must come back clean (coverage 0, no Latin, no nod, no twice, no question ✓).
