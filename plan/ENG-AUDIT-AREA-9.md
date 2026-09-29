# Engineering audit 2026-09-29 - Area 9: page health (worker F, branch eng-audit-f)

**Scorecard: ⚠.**

Clean on every page:
- 0 broken links and 0 failed data fetches.
- 0 NaN / undefined / null.
- 0 remnants of Amal's hub.
- The Arabizi guard prints 0.

Before this branch:
- 19 pages had hard-to-read or invisible text in dark and/or light mode.
- 1 page scrolled sideways at 375 px.
- The clip fallback had 2 bugs.

All of those are fixed on this branch.

Still open:
- 780 short clips are unpublished. 676 of them sit on this PC. They play from the full lesson recording instead.
- 3 vocab-audit tests fail because the 09-28 lesson was never audited.
- One AI Reports number is stale.

## How it was checked
- **Headless sweep:** `data/eng-audit/render_pages.py` renders all 56 pages in Chromium at 375 px.
  - Pages: 22 docs/*.html, 19 lessons, 9 reports, 6 amal.
  - 4 theme set-ups: OS light, OS dark, the Dark switch on a light OS, and the Light switch on a dark OS.
  - Recorded per page:
    - failed requests
    - console errors
    - sideways scroll
    - NaN / undefined / null
    - bare dashes
    - text contrast under 3:1 ("invisible" = under 1.5:1)
    - every `<audio>` src, and the fallback it switches to
  - Raw results (from BEFORE the fixes): `data/eng-audit/page-health.json`.
- **Publish-guard check:** `scripts/check_pages.py`.
  - Offline and static; takes about 5 s.
  - Exits 1 with a one-line plain reason.
  - `--verbose` lists every problem. `--arabizi` also runs the Arabizi guard.
- **Tests:**
  - `tests/test_page_health.py`: 16 offline tests.
  - `tests/test_page_health_render.py`: 58 tests. They use headless Chromium and a local server on a random port.
- **Screenshots:** `data/eng-audit/screens/`.
  - Before/after: flashcard set counts, the speaking-audit status box, the word-bank-audit totals.
  - Progress and Grammar at 375 px, light and dark.

## Per-page table
- Light / Dark columns = number of text items under 3:1, BEFORE the fixes.
- Light = OS light + the Light switch. Dark = OS dark + the Dark switch.
- Status = the state after this branch.

| Page | Links/data | Clips | Blanks (NaN/undefined/null) | Mobile 375 | Light | Dark | Status |
|---|---|---|---|---|---|---|---|
| ai-reports.html | ok (Supabase name_labels 404: migration 021 not applied; the page says so) | - | 0 | ok | ok | 14 low | fixed |
| big-picture.html | ok | - | 0 | ok | ok | ok | ok |
| cards.html | ok | - | 0 | ok | 12 low | 4 low (2 invisible) | fixed |
| check02-amal.html | ok | - | 0 | ok | ok | 4 low | fixed |
| check03.html | ok | - | 0 | ok | ok | 4 low | fixed |
| engine-report.html | ok | - | 0 | ok | ok | ok | ok |
| go.html | ok | - | 0 | ok | ok | ok | ok |
| grammar.html | ok | lazy (see Clips) | 0 | ok | ok | ok | ok |
| homework.html | ok | - | 0 | ok | ok | 16 low | fixed |
| index.html (= Progress) | ok | - | 0 | ok | 28 low | ok | fixed |
| legacy-words.html | ok | - | 0 | ok | ok | 2 low | fixed |
| lessons.html | ok | - | 0 | ok | ok | ok | ok |
| notes.html | ok | - | 0 | ok | ok | ok | ok |
| progress.html | ok | - | 0 | ok | 28 low | ok | fixed |
| recipe1.html | ok | - | 0 | ok | ok | ok | ok |
| settings.html | ok | - | 0 | ok | ok | ok | ok |
| slips.html | ok | - | 0 | ok | ok | 18 low | fixed |
| speaking-audit.html | ok | - | 0 | was 386 px | ok | 50 low (2 invisible) | fixed |
| speaking-review.html | ok | - | 0 | ok | ok | ok | ok |
| tutor.html | ok | - | 0 | ok | ok | ok | ok |
| word-bank-audit.html | ok | 50 checked, 0 dead | 0 | ok | ok | 4 low (1 invisible) | fixed |
| word-bank.html | ok | - | 0 | ok | ok | ok | ok |
| lessons/2026-08-25-report.html | ok | - | 0 | ok | 232 low (OS dark) | 232 low | fixed |
| lessons/2026-08-25.html | ok | 1 checked, 0 dead | 0 | ok | 2 low (OS dark) | 2 low | fixed |
| lessons/2026-09-04-report.html | ok | - | 0 | ok | 155 low (OS dark) | 155 low | fixed |
| lessons/2026-09-04.html | ok | 1 checked, 0 dead | 0 | ok | 2 low (OS dark) | 2 low | fixed |
| lessons/2026-09-05-report.html | ok | - | 0 | ok | 142 low (OS dark) | 142 low | fixed |
| lessons/2026-09-05.html | ok | 1 checked, 0 dead | 0 | ok | 2 low (OS dark) | 2 low | fixed |
| lessons/2026-09-10.html | ok | - | 0 | ok | ok | ok | ok |
| lessons/2026-09-11-report.html | ok | - | 0 | ok | 175 low (OS dark) | 175 low | fixed |
| lessons/2026-09-11 .. 09-28 (11 pages) | ok | 1 checked each, 0 dead | 0 | ok | ok | ok | ok |
| reports/ai-process-review-2026-09-27.html | ok | - | 0 | ok | 7 low | 7 low | fixed |
| reports/ (other 8) | ok | - | 0 | ok | ok | ok | ok |
| amal/ (6 pages; no link token, so only the "link not valid" screen) | ok | - | 0 | ok | ok | ok | partly checked |

The old-look lesson and report pages (08-25, 09-04, 09-05, 09-11) do not load theme.js. They follow the OS setting
only, so "Light switch on a dark OS" shows them dark.

**Bare dashes:** every one was read by hand.
- Counts per page:
  - grammar 73
  - claude-audit report 27
  - ai-process-review 10
  - others 1 to 5 each
- All of them are deliberate "not measured" marks with the reason next to them. Examples: "— collecting, 11 of 30", Untested rows, "not tracked".
- None is a blank where a number belongs.
- The one real gap is on AI Reports: "— Amal's word-review answers saved per private link; not readable here". That belongs to Area 8 (her answers are not pulled), not to page health.

**Amal's hub:** no page, link or button remains. What is left:
- go.html quietly sends old `?to=hub` links to the review page.
- reports/process-audit-2026-09-26.html mentions "the Tutor Hub page" once, as plain text in a historical recommendation.

## Clips (dead audio)
**Unpublished clips.** `*.mp3` is git-ignored, so 780 unique clips named in docs/data were never published:

| Source | Unpublished clips |
|---|---|
| grammar-console | 617 |
| amal-review | 160 |
| sentence-ladder | 2 |
| 09-21 context clip | 1 |

**Fallback bug 1: the two-channel lesson hit a 404.** 2026-09-10 has Medi.mp3 and Amal.mp3 but no lesson.mp3.
- Every missing 09-10 clip ended on a 404: 23 on Amal's review list and 28 in the Grammar Console.
- Fix: js/clip-fallback.js now tries lesson.mp3, then Medi.mp3, then Amal.mp3. amal/review.html asks for the next one in that order.
- Proven in real Chromium: the test failed on the old code and passes now.

**Fallback bug 2: the note under the player was wrong.** On every fallback it said "No recording is available for this moment", even when the full recording played.
- Cause: the old code added its give-up listener during the same error event, so that listener fired at once.
- Proven in real Chromium on 09-26: readyState 4 (audio loaded) with the wrong note. Fixed.

**09-21 context clip.** context-4cf34015509cfc24.mp3 is used by the 09-21 lesson page, the Word Bank audit and word-bank-clips.json.
- Those players have no fallback, so the clip was silent.
- The file was in the live checkout but never force-added. Its sha256 (ab179063...) matches the manifest.
- Now published.

## Failing tests on clean master: cause and fix
**Before** (clean master, 3c2835c):
- pytest: 8 failed / 303 passed / 3 skipped / 9 xfailed.
- node: 1 of 20 failed.

**After** (this branch):
- pytest: 4 failed / 369 passed / 3 skipped / 8 xfailed, with 14 deselected. The deselected ones are the live-database e2e tests, per the coordinator.
- node: 20 of 20 pass.
- The 4 remaining failures are real findings:
  - 3 vocab audit tests
  - 1 stale AI Reports card

| Test | Cause | Fix | Commit |
|---|---|---|---|
| test_transcript_player.cjs | The default path `./transcript-player.js` never existed (MODULE_NOT_FOUND). | Load docs/js/transcript-player.js. | d30aecd |
| test_m3_planner::stand_in (9 buttons > 4) | Stale test: it still drove the 3-screen planner. Medi approved the 2-screen topic + word menu on 09-05 (2db5204, e157aae, 9d930dc). | The loop follows the 2 screens. The "at most 4 buttons, nothing below the fold" rule now applies to sentence screens only. Buttons of at least 48 px and no sideways scroll are still checked on every screen. | 79c4833 |
| test_stale_banner::banner | Stale test: it waited for #start. The Flashcards home became the category menu in 4facdef (Medi 09-22). | Wait for the category menu. | e073d61 |
| test_m5_cards (3 cases) | Stale test: it assumed 20-card rounds. Medi's 09-27 "fix the bugs" (af4d629) caps new cards at 8 a day, so the Animals round dealt 9. | Rounds are sized from what the page deals. Cleanup now runs in `finally` (a failed run used to leave its rows in live card_results). | cbcc012 |
| test_vocab_audit (3) | NOT stale. The 09-28 lesson added 104 unresolved Medi events that nobody audited. scripts/audit_vocab_unresolved.py is not in the hourly job. | Not fixed here; see "For the coordinator". | - |
| (hidden) test_invariants Arabizi guard | Skipped on this PC because node is not on PATH. | Falls back to the portable node. It now runs: 0 gaps. | 211ac15 |
| (hidden) test_invariants audit cards | Ran 0 cases once the audit reached 1,074 rows (the cards' 961 is outside the ±10% window). | New test fails and names the 2 stale cards (both say 961). | 211ac15 (left failing: real finding) |
| (hidden) test_speakers_not_swapped | Read the frozen gold set, which stops at 09-26, so 09-28 was checked on 0 rows. | Reads the live full audit (09-28 = 69/70 agree). A lesson with 10 or more audit rows must match at least 10. The 80% bar is unchanged; the docstring said ">= 92%", but 09-23 is 91.5%. | 211ac15 |
| (hygiene) m8 / m3 / m4 | A pytest run rewrote the tracked docs/data/build.json, docs/js/build.js and data/m*_stand_in_timing.json. | These tests write to temp now. | 211ac15 |

## Colour changes (old -> new, and why)

Contrast ratios below are text against its background.

**Flashcards set counts (06533f0)**
- Only the numbers under each set change colour; the bar colours stay.
- Light mode:
  - Good: 1.48 -> 4.58
  - Shaky: 1.51 -> 4.76
  - Untested: 1.50 -> 4.90
  - Wrong: 4.16 -> 5.67
- Dark mode, Untested: 2.05 -> 4.61.

**Progress / Lessons 80-89% band (f7cedf7)**
- Green #4f9a2e -> #447f26, same hue: 2.67 -> 3.71.
- Medi chose these band colours on 09-27, so there is a decision for him below.

**Text on solid fills (f7cedf7)**
- White text on teal / mute / red / amber fills in dark measured 2.3 to 2.9.
- New token `--on-fill` in css/anees-page.css: white in light, ink #141D1A in dark.
- Pages: homework, slips, check02-amal, check03, legacy-words, amal/after, amal/plan, amal/review.

**Old-look lesson and report pages in OS dark (f7cedf7)**
- White on light teal measured 2.15; the default blue links measured 1.95.
- Fixed with the same `--on-fill` idea and teal links.
- Also fixed in the generators, scripts/build_report.py and scripts/lesson_pipeline.py, so a rebuild keeps it.

**speaking-audit.html in dark (f7cedf7)**
- Status box: 1.16 (invisible) -> fixed.
- Metric numbers: 2.45 -> fixed.
- A 40-character commit hash made the page 386 px wide at 375 px. It wraps now.

**word-bank-audit.html in dark (f7cedf7)**
- The totals line: 1.05 (invisible) -> fixed.
- "Wrong" headings now use the page's red token.

**AI Reports and the 09-27 process review (f7cedf7)**
- AI Reports keys V1 / G1 / N1 in dark: #B9631F -> #E09A6B (2.91 -> 6+).
- Process-review warn pills in light: text #C98A3E -> #8A5A1E (2.39 -> fixed).

## Commits on eng-audit-f
- d30aecd, 79c4833, e073d61, cbcc012: the stale tests in the table above.
- 8bed36e: scripts/check_pages.py, the clip fallback chain, the 09-21 clip published, and tests/test_page_health.py.
- 06533f0: flashcard set counts.
- f7cedf7: dark/light readability on 19 pages, plus the speaking-audit width fix. tests/test_page_health_render.py went from 28 of 56 failing to 56 of 56 passing.
- 16eadc9: real-browser clip fallback test. It failed 2 of 2 on the old code and passes 2 of 2 now.
- 211ac15: test hygiene and the invariants fixes.

## Decisions for Medi (one line each, yes/no)
- Publish the 676 short clips that are on this PC but were never pushed (40 MB), so they play as the real short clip instead of the full-lesson moment? yes/no
- Apply Supabase migration 021 (name_labels), so the "Possible names" taps on AI Reports sync (today they stay on the device)? yes/no
- The 80-89% band green was darkened from #4f9a2e to #447f26 so it can be read on the light page. Keep it? yes/no
- The speaker-swap check bar is 80%; the lowest real lesson is 09-23 at 91.5%. Keep 80%? yes/no

## For the coordinator (files I don't own)
1. **Vocab audit (3 failing tests).** After merging, run `python scripts/audit_vocab_unresolved.py`. The committed overlay is stale for 09-28; a local run fixed 2 of the 3 tests.
   - After that run, 153 events stay "open": 32 from before plus 121 from 09-28.
   - The third test allows at most 40 open, so it fails until someone judges the 09-28 events by hand.
   - Also wire the script into scripts/hourly_lessons.py after the word-bank build, so new lessons are binned automatically.
2. **Stale AI Reports number.** In docs/data/ai_reports.json, cards process-audit-2026-09-26 and ai-process-review-2026-09-27 say "961 rows"; the audit now has 1,074.
   - Add "as_of" or update the number.
   - Then remove those slugs from KNOWN_STALE in tests/test_invariants.py.
3. **Hard-coded date (Area 4).** docs/js/lessons-page.js `lessonAudio()` hard-codes '2026-09-10' for two-channel audio. It should read the lesson's own audio list.
4. **Live-database tests.**
   - Gating the e2e tests behind ANEES_E2E_LIVE is NOT done: my merge and the conftest read were blocked by my permissions.
   - card_results holds 81 leaked test rows from today, in 9 Animals rounds: rmumgm1ta, rmumgm92v, rmumgo7k9, rmumgoeyw, rmumhk00k, rmumhk6os, rmumhlj49, rmumhlq6w, rmumhnijx.
   - Those rows also used up today's 8-new-card room.
   - Nothing was deleted.
5. **Merge.** My test_m5_cards change (cbcc012) overlaps worker E's f27764d. Where they conflict, keep E's cleanup.

## Hand check of 5 random findings: 5 of 5 held
1. 2026-09-10 has no audio/lesson.mp3 (checked with git ls-files).
2. word-bank-audit totals are invisible in dark (screenshot, before and after).
3. speaking-audit's 386 px width comes from an unbreakable commit hash in a list item (element probe).
4. The old fallback always showed "No recording" (real browser, 09-26: loaded with the wrong note).
5. The Progress 80-89% green measures 2.67:1 (recomputed with the WCAG formula).

## Not done
- **Amal's pages.** amal/*.html were rendered without a link token, so only the "link not valid" screen was checked. Her full screens were not checked in dark (the same `--on-fill` fix is applied to them).
- **Lazy clips.** Clips that only render inside accordions were checked through the data and with one real-browser test per recording kind, not by opening every row.
- **Check-page generators.** build_check_02 / 03 / page.py do not add the Sabz skin, so rebuilding check02/03 would drop it. This was already true before the audit.
- **E2E gate.** There is no ANEES_E2E_LIVE gate on the live-database tests.
