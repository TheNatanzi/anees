# Handoff - load today's lesson (2026-09-26) all the way in + Amal's "After the lesson" questions

Paste into a fresh chat: **"Read C:\dev\anees-hourly\plan\HANDOFF-LESSON-2026-09-26-AFTER-LESSON.md and do it."**

## Goal (Medi 2026-09-26)
Upload the new lesson from today (2026-09-26) fully, and put what Amal needs for "After the lesson" on her pages,
reachable from the app menu (sidebar: Tutor -> After the lesson). Nothing is sent to Amal - Medi sends links himself.

## Read first
1. Memory: `anees-full-audit-2026-09-26` (the audit pipeline, pages, links) and `anees-full-audit-decisions-2026-09-26`.
2. `C:\dev\anees-hourly\RULES.md` (S1 Amal's spelling, S2 raw transcripts never edited, S3-S5).
3. `scripts/review_lesson.py` docstring (the same-day loop, steps 1-8) and `plan/PROCESS-AUDIT-2026-09-26.md` section 5
   (18 proposed rules - NOT approved yet; do not apply any of them).

## Where today's lesson stands (checked 2026-09-26 22:20)
| step | state |
|---|---|
| Recorded + transcribed (C:\dev\anees\data\lessons\2026-09-26: scribe_Amal/Medi.json + tracks) | done |
| Transcript page `docs/lessons/2026-09-26.html` (Arabizi on top) | live, commit 5180009 |
| Lessons page (`docs/data/lessons.json`, `docs/data/lessons/2026-09-26.json`) | **missing** |
| Audit rows (two readers + third reader) in `data/full-audit-2026-09-26.json` | **missing** |
| Amal's slip patterns for this lesson on `amal/review.html` | **missing** |
| After-lesson link (3-5 questions + clips) on the Tutor page | **missing** |

**Why it stopped:** three scripts carry a hard-coded list of the 13 old lesson dates, so a new lesson never gets its
per-lesson JSON, and `review_lesson.py` (called by the hourly job) has nothing to read:
- `scripts/build_lessons_page_data.py` line ~57 `DATES = [...]` (also `LESSON_TYPES` ~348 and `TAUGHT` ~46 dicts)
- `scripts/full_audit_prep.py` line ~14 `DATES`
- `scripts/full_audit_build.py` line ~22 `DATES`
- `scripts/arabizi_check.cjs` line ~13 (hand-check sampler only)

## Do, in order
1. **Make the date lists automatic** (the real fix, so every future lesson flows by itself): derive `DATES` from the
   published pages `docs/lessons/20??-??-??.html` (sorted) in all four files. `build_lessons_page_data.py` must not crash
   on a date missing from `LESSON_TYPES` / `TAUGHT`: default type = Claude's read of the lesson (mark `type_source`
   "claude-read"), taught = []. Then add a real `LESSON_TYPES["2026-09-26"]` entry and the verb pairs Amal taught
   today to `TAUGHT` (read the transcript; spell them as her Doc's "Ana ba-" forms - memory `anees-new-verbs-are-new-words`).
2. Run `python scripts/build_lessons_page_data.py` -> check `docs/data/lessons.json` lists 14 lessons incl. 2026-09-26.
3. Run the same-day review: `python scripts/review_lesson.py 2026-09-26 --no-push`. It runs two independent readers,
   compares, a third reader, settles, rebuilds the audit + pages, places this lesson's B rows into patterns, mints the
   After-lesson link (`scripts/after_from_audit.py`), refreshes Amal's hub payload and `docs/data/tutor.json`.
   - It calls the Claude CLI headlessly (`claude -p`). If that fails in this session, do the same by hand with the
     Agent tool: two reader agents on `data/lesson-work/full-audit/READER-BRIEF.md` (files `2026-09-26.r1.json` /
     `.r2.json`), `python scripts/full_audit_compare.py compare 2026-09-26`, a third reader on `THIRD-READER-BRIEF.md`
     (`2026-09-26.r3.json`), `... settle 2026-09-26`, then re-run `review_lesson.py 2026-09-26 --no-push` (it reuses
     every file that exists and continues from there).
4. **After-lesson questions check:** `docs/data/tutor.json` has an open card "After the lesson · Sep 26"; the menu address
   `go.html?to=after` opens `amal/after.html?t=...&from=app` for 2026-09-26 (newest lesson wins); each of the 3-5
   questions has a clip that plays. If fewer than 3 questions came out, say so - never pad with guesses.
5. **Amal's slip patterns:** any new B rows of 09-26 sit in `data/lesson-work/full-audit/patterns.json` (existing
   pattern or new one; `unplaced` empty) and `docs/data/amal-review.json` count went up accordingly.
6. Hand check 5 random scored rows of 09-26 against the transcript (report n/5). Note transcript holes, never guess.
7. Preview locally (launch config `anees-docs-audit`, port 8097): Lessons page shows Sep 26 with its vocab/grammar
   errors; Tutor page shows the new card; no console errors. Then commit + push (`git push origin HEAD:master`), commit
   messages end with the Co-Authored-By line from the system reminder.
8. Update memory `anees-full-audit-2026-09-26` with the new state (one line).

## Do not
- Do not send anything to Amal. Do not approve or apply any of the 18 proposed rules. Do not re-transcribe or pay for audio.
- Do not edit raw transcripts (S2). Readers never open each other's files or the 09-24 sweep.

## Report to Medi (his format)
One line first; a small table (lesson loaded / errors found / questions for Amal / patterns added); short one-line
bullets; one bold action. The After-lesson link reaches Amal through her hub link he already has
(`https://thenatanzi.github.io/anees/amal/hub.html?t=WcvsRL9kmF8fNKQx76LvDkdA9EXFPt_4`) - say that, do not re-send.
