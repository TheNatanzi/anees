# Backfill inventory - what must be rebuilt after `transcript-fixes.json` changes (2026-10-04)

Scope: worktree `C:\dev\anees-wt-bench`, 18 lessons (08-25, 09-04, 09-05, 09-10, 09-11, 09-14 .. 09-19, 09-21, 09-23, 09-26,
09-28, 09-30, 10-01, 10-02). Read-only research; nothing was built, no network call, no commit.
Raw archive (never edited): `C:\dev\anees\data\lessons\<date>\` (hard-coded in `lesson_turns.py`, `build_lessons_page_data.py`,
`self_fix_timing.py`, `build_grammar_console.py`, `detect_grammar_usage.py`).

## 0. The five things to know first

1. **There are two different "transcripts" in the code, and the overlay reaches them differently.**
   - **Page turns**: `build_lessons_page_data.page_turns(date)` parses `docs/lessons/<date>.html` (the static lesson page made
     once by `load_lesson.py`), merges gap-fill layers, then `transcript_fixes.apply(date, turns)`. Result is written to
     `docs/data/lessons/<date>.json` `turns` (`text` = heard, `engine` = engine text, `heard` = list). Almost everything
     downstream reads these turns.
   - **Track turns**: `lesson_turns.lesson_turns(date)` reads the RAW folder (`transcript.txt`, else `scribe_Medi.json` +
     `scribe_Amal.json` glued on a 1.2 s gap, else the page) and then `transcript_fixes.apply_tracks`. Used by
     `detect_grammar_usage.py` (the Grammar % denominator), `build_grammar_console.py`, `audit_grammar_lessons.py`.
     Its turns have **different boundaries and start times** from the page turns, it does not read the reconnect files
     (`scribe_<who>_seg*.json`) or gap fills, and a fix row that matches no track turn is **skipped silently** (no
     `unmatched` check on this path).
     Measured today (read-only): of the 121 existing fix rows, all 121 land on page turns but only 109 land on track turns
     (09-15 2 of 4, 09-19 1 of 4, 09-21 8 of 9, 09-23 2 of 5, 10-02 66 of 69). Turn counts differ a lot (09-23: 798 track
     turns vs 1,113 page turns; 09-04: 1,046 vs 1,395). A whole-transcript replacement keyed to page lines will reach the
     use counter only partly unless this is fixed or checked.
2. **Word events are stored, not re-read.** `load_lesson.py` detects Word Bank events from the raw Scribe words at load time
   and inserts them into Supabase `speaking_events` (insert-only; `sync_word_bank_evidence.sync_events` refuses a changed
   event). Event id = `sha(lesson, source_sha256, [local_start, local_end])`. No builder re-detects events from overlay text.
3. **Reader rows (slips) are AI output, cached per transcript hash.** A changed `<date>.txt` makes r1/r2/r3 stale; re-reading
   costs 3 `claude -p` runs per lesson (plus up to 5 more `claude -p` steps inside `review_lesson.py`).
4. **Row identity is time + text.** `uid = "FA-" + sha1(date | int(sec(t)) | norm(wrong) | kind_class)[:8]`
   (`full_audit_build.uid_base`). Amal's 117 ruled rows, 356 verification records, 90 patterns and Medi's corrections hang
   on that uid. A re-read that moves `t` by one second or rewrites `wrong` makes a new uid and the reference is lost
   **without an error** (see section 4).
5. **`build_lessons_page_data.py` stops the whole build** when a non-pattern fix row matches no page line:
   `raise SystemExit("transcript-fixes.json: {d} {t} {who} '{engine_wrote}' matches no line (the transcript changed?)")`.
   Match rule (`transcript_fixes._hit`): `r.who == u.who and abs(r.t - u.t) <= 1.0`, then `engine_wrote in u.text` and
   `text.replace(engine_wrote, heard, 1)`. Rows on one turn are applied in file order to the already-changed text, so a
   second row's `engine_wrote` must still be present after the first replacement.

---

## 1. Inventory table

Legend for "reads the transcript through": **PT** = page turns with `transcript_fixes.apply` (docs/lessons html -> overlay);
**LJ** = `docs/data/lessons/<date>.json` turns (already overlaid, so second-hand PT); **TT** = `lesson_turns()` +
`apply_tracks` (raw folder, own boundaries); **RAW** = raw Scribe / audio files directly, no overlay; **DB** = Supabase rows;
**AI** = reader output files.

| Generated file / page | Builder (command) | Transcript-derived content | Reads transcript through | Re-computable offline from files? |
|---|---|---|---|---|
| `docs/lessons/<date>.html` (static lesson transcript page) + `docs/lessons/<date>/audio/lesson.mp3` | `scripts/load_lesson.py <date> --raw .. --work .. [--page-only]` -> `build_lesson_page.write_page` | Every line as the ENGINE wrote it, `data-t`, `data-row` | RAW (`sync_speaking_lesson.source_rows`); **no overlay** | Yes, but it is an INPUT of everything else (PT parses it; `data-row` calibrates word times). Do not rebuild. It will keep showing engine text -> needs a label. Only `rehear_status.stamp_pages` touches it. |
| `docs/data/lessons/<date>.json` (`turns`, `vocab_errors`, `vocab_correct`, `grammar_errors`, `grammar_not_counted`, `not_errors`, `marks`, `tmarks`, `marks_report`) | `python scripts/build_lessons_page_data.py` (`build()`) | Line text (heard + engine), line end times, every card, underlines | PT for turns; RAW Scribe words for `end`/timing (`words_for`); DB events via `docs/data/word-bank-evidence.json`; AI rows via `data/full-audit-2026-09-26.json` `sweep_compat` | Mostly. Needs a Supabase READ (`_confirmed_new()` -> `amal_rules kind=new`; offline it falls back to the 2026-09-25 list with a warning, and raises under `ANEES_STRICT=1`). Needs ffmpeg/ffprobe + node. |
| `docs/data/lessons.json` (Lessons page rows, Progress Overview hourly series, Lessons averages) | same build | Words %, right/partial/wrong/scored, unique words; Grammar %, uses, mistakes; talk %, wpm, fillers, latency, flow; counts.turns / chat_lines; coverage, notes, release | Words: DB events + review overlay + AI vocab-A rows + sheet verdicts + ledger. Grammar: AI rows + `grammar-usage.json` (TT). Timing: RAW words (not overlay). Counts: PT | Words: no (stored events + Amal taps). Grammar slips: no (AI rows). Grammar uses: yes. Timing: yes (unchanged by the overlay). |
| `docs/data/word-bank-audit-slips.json`, `docs/data/amal-ledger.json` | same build | Reader word slips placed on Word Bank forms; Amal "which word was wrong" cards | AI rows + ledger | With the audit JSON, yes |
| `data/lesson-work/ledger/<date>.json` + `_diff.md`, `data/lesson-work/rehear-status.json` | same build (`lesson_ledger.build/write/write_diff`, `rehear_status.build`) | One mark per judgment on a turn; before -> after table vs `origin/master:docs/data/lessons.json` | PT + everything above. `input_files()` hashes include `docs/lessons/<date>.html` and `transcript-fixes.json` | Yes (derived) |
| `docs/data/accuracy-release.json`, `data/accuracy/verification-queue.json`, `release` fields in lessons.json | `python scripts/accuracy_gates.py annotate` (also called at the end of the lesson-data build) | Verified / not verified per lesson, coverage by person, rows needing a check | LJ turns (`participant_coverage`), audit rows, `<date>.compare.json`, `.p2.*`, `.passes.json`, `data/accuracy/verifications.json`, `source-audit.json` | Yes from files; depends on stored verification records keyed by uid |
| `docs/data/grammar-usage.json` (uses per rule, `ruled_out`, `not_uses_auto`, per-lesson counts) | `python scripts/detect_grammar_usage.py` | Every right use of a grammar rule (Grammar % denominator), with `t`, `hit`, `said` | **TT** (overlay via `apply_tracks`, silent misses) | Yes, pure local |
| `docs/data/grammar-console.json` + `docs/lessons/<date>/clips/gc-*.mp3` | `python scripts/build_grammar_console.py` | Per-rule uses, slips, %, status; slip cards; clips | AI rows (`sweep_compat`), `grammar-usage.json`, `tally.json`, TT for `medi_sentences`, ledger folds | Yes (ffmpeg). Slips are AI rows. |
| `docs/amal/grammar-rules.html` | `python scripts/build_amal_grammar_rules.py` | Status pill, % and use count per rule | grammar-console.json | Yes. Amal-facing page: numbers change, nothing is sent |
| `data/lesson-work/full-audit/<date>.txt`, `amal-sheet.txt`, `buckets.md` | `python scripts/full_audit_prep.py` (all dates) or `review_lesson.py` step 1 (one date) | The reader input: `[mm:ss] Who: text` per turn | LJ `turns[].text` (heard text) | Yes |
| `data/lesson-work/echo-candidates/<date>.json` | `python scripts/echo_candidates.py <date>` | Short English-looking replies, take_verb, laazem_noun, chat_pairs | LJ (skips turns that already have `engine`) | Yes |
| `data/lesson-work/full-audit/<date>.r1.json`, `.r2.json` (+ `.inputs.json`) | `claude -p` x2 via `review_lesson.py` step 2 | Reader slip rows | AI reading `<date>.txt` | **No - paid AI** |
| `data/lesson-work/lesson-types/<date>.json` | `claude -p` via `review_lesson.py` step 2b (only 8 lessons have one; the 10 older use hand `LESSON_TYPES` / `TAUGHT`) | Lesson type, taught words, off-lesson windows (times) | AI reading `<date>.txt` | No - paid AI. For a lesson with no file `review_lesson.py` WILL call it. |
| `<date>.compare.json`, `<date>.disputes.md` | `python scripts/full_audit_compare.py compare <date>` | Agreed / disputed rows, agreement % | r1 + r2 | Yes |
| `<date>.r3.json` | `claude -p` via `review_lesson.py` step 4 | Third-reader rulings | AI reading disputes + `<date>.txt` | No - paid AI |
| `<date>.settled.json` | `python scripts/full_audit_compare.py settle <date>` | Final pass-1 rows, `fid` | compare + r3; GR-24 check reads RAW Scribe word times (`self_fix_timing.words`) + LJ turns; `self-fix-rulings.json` | Yes |
| `<date>.p2.r1/r2/r3/compare/settled.json`, `<date>.passes.json` (13 lessons, 08-25 .. 09-23) | by hand in the 09-26 backfill (`full_audit_compare.py ... --pass 2`, `passes`) | Second pass rows | AI reading the OLD `<date>.txt` | **No, and nothing re-runs them.** `full_audit_compare.union_rows` still merges the old pass-2 rows into the new pass-1 rows; `accuracy_gates` compares the two passes. |
| `data/full-audit-2026-09-26.json` (1,161 rows today), `plan/FULL-AUDIT-2026-09-26.md`, `docs/data/grammar-proposals.json`, `data/lesson-work/medi-corrections-report.json` | `python scripts/full_audit_build.py` then **always** `python scripts/apply_amal_audit_rulings.py` | Every slip row, uid, kind, bucket; `sweep_compat` (what the pages read) | settled rows (AI) + `data/grammar-sweep-2026-09-24.json` + ruling files (section 4) + `transcript_fixes.load()` (TR-24 `apply_misheard`) | Build: yes. Amal's rulings: **Supabase READ required** (`amal_rules` source review / after). The build wipes her rulings; the second script puts them back by uid. |
| `docs/data/ai_rules.json` (Amal's rulings group), `data/lesson-work/ledger-amal.json`, `data/accuracy/verifications.json` (appends) | `python scripts/apply_amal_audit_rulings.py` | Her confirm / skip per pattern, Tutor-page checks | DB `amal_rules` | No - her taps in the database |
| `docs/data/amal-review.json` + clips | `python scripts/build_amal_review.py` | B rows grouped by pattern for Amal | audit rows + `patterns.json` (uids) | Yes (ffmpeg). Amal-facing data |
| `data/lesson-work/full-audit/patterns.json` | `claude -p` pattern reader (`review_lesson.py` step 7) | Pattern -> row uids | AI | No - paid AI; keyed by uid |
| `data/accuracy/source-audit.json`, `docs/data/word-bank-transcription-checks.json` | `python scripts/source_audit.py [date]` | Holes, speaker swaps, coverage by person | RAW audio + `page_turns` (no overlay) | Yes; not changed by a text overlay (changed by `set_who` / `set_t` rows only through LJ in accuracy_gates) |
| `docs/data/amal-verify.json` | `python scripts/codex_rejudge.py --list` | Amal's "check these moments" list | verification queue + `verifications.json` (uid) | Yes for `--list`. Without `--list` it calls Codex (gpt-5.5) + local whisper: AI, must be flagged |
| `docs/data/sentence-ladder.json`, `docs/data/sentence-ladder/<date>.json` | `python scripts/build_sentence_ladder.py` | Sentence lengths understood / spoken, tags, sentence ids `"<date>:L|S:<int(t*10)>"` | LJ turns + LJ error cards + grammar-console.json + `words_labeled.json` (3 early lessons) | Yes, pure local. Medi's swipes (`sentence_labels`, keyed by sentence id) are overlaid in the browser. |
| `docs/data/word-bank-evidence.json` | `hourly_lessons.refresh_published` (`speaking_snapshot.events()`) | Every stored word event: `text`, `original_text`, `context` rows, `t_start` | **DB** `speaking_events` (made from RAW at load) | **No** - stored events. Overlay never changes it. |
| `docs/data/word-bank-review.json` (1,823 patches, 5 additions) | `review_new_lessons.py <dates>`, `review_silent_credits.py`, `audit_vocab_unresolved.py`, `load_lesson.py --reconcile-tracks` | Overlay verdicts on stored events (`expected` = source_sha256, row_id, word_key, text, t_start) | evidence file (stored events); `audit_vocab_unresolved` also reads raw page turns (no overlay) | Yes from the evidence file; bound to stored events, not to line text |
| `docs/data/word-bank-audit.json`, `word-bank-audit-checks.json` | `node scripts/audit_word_bank_reliability.cjs docs/data/word-bank-evidence.json` | Word Bank reliability counts (applies ledger overrides) | evidence + review + ledger overrides | Yes |
| `docs/data/word-bank-clips.json`, `docs/lessons/<date>/clips/context-*.mp3` | `hourly_lessons.build_clips` -> `build_audit_audio.py` | Clip per stored event | stored events + raw audio map | Yes (local audio); unchanged by the overlay |
| Word Bank page (`docs/word-bank.html`, `js/word-bank.js`), Progress > Vocab (`js/vocabulary-progress.js`), Flashcards boost (`cards.html`) | none (browser) | Word accuracy, words known, per-word status, unique words per lesson | evidence + review + audit-slips files, `rest/v1/words` | Stored events (see section 5) |
| Lessons page (`docs/lessons.html`, `js/lessons-page.js`), Progress Overview (`js/lesson-overview.js`, `js/overview-angles.js`), Grammar console (`js/grammar-console.js`), Progress > Grammar (`js/grammar-progress.js`), Fluency ladder (`js/fluency-ladder.js`) | none (browser) | Whatever the JSON above holds | lessons.json, lessons/<date>.json, grammar-console.json, grammar-usage.json, sentence-ladder.json | follows the builders |
| `docs/data/amal-new-words.json`, `data/lesson-work/amal-new-words/<date>.candidates.json`, `amal-new-words-verdicts.json`, `taught-words-verdicts.json` | `python scripts/amal_new_words.py [--candidates <date>]` + `claude -p` by-meaning reader | Words Amal used that are not on her Doc (only lessons >= 2026-10-01) | LJ turns (Amal + chat lines) + AI verdicts keyed by `(date, key)` + DB taps | Candidates: yes. Verdicts: paid AI. Taps: DB read. Amal-facing (Tutor hub cards) |
| `docs/data/tutor.json` | `python scripts/build_tutor_data.py` | Open links for Amal with totals | DB (`amal_links`, `verb_check_links`, `transcript_review_links`, `amal_rules`) | No - DB read |
| After-lesson link payload (DB row in `amal_links`) | `python scripts/after_from_audit.py <date>` | 3-5 "was he right here?" questions with clips, `audit_uid` | audit rows | **Writes Supabase and adds a card to Amal's hub. Must not run in a backfill.** |
| Review link payload (DB `amal_links` PATCH) | `python scripts/amal_review_link.py` | Her open links | DB | **Writes Supabase (PATCH / mints a link). Must not run.** |
| `docs/data/correction-proposals.json`, `data/lesson-work/correction-rules.json` | `python scripts/medi_corrections.py propose` | Pattern proposals from Medi's corrections, counted on LJ turns | LJ turns + audit rows + usage | Yes. `pull` needs network (fail-open, keeps the mirror) |
| `docs/data/lesson-names/<date>.json` (5 files, last built 2026-09-28), `docs/data/possible-names.json` | `python scripts/names.py layer [dates]` / `possible` | Name spans as **character offsets into `turns[i].text`** | LJ turns | Yes. Not in any chain; already stale; only `tests/test_names.py` reads the layer files |
| `docs/data/grammar-audit.json` (machine candidates, never scored) | `python scripts/audit_grammar_lessons.py` | Candidate corrections | TT (+ chat) | Yes; not in the hourly chain |
| `docs/data/tally.json` (Slips page) | `python scripts/build_tally.py` | Hand-curated slips verified against raw `transcript.txt` | RAW `data/lessons/<date>/transcript.txt`, no overlay | Yes; legacy, not in the chain |
| `docs/data/rule-book.json`, `docs/rules.html`, `RULE-BOOK.md` | `python scripts/build_rule_book.py` | Rules only (examples quote moments) | `rules/registry.json` | Yes; does not read the transcript |
| `docs/reports/<slug>.html`, `docs/ai-reports.html` cards | `python scripts/build_ai_reports.py` | Numbers frozen inside each report's source .md (benchmark, process audit) | none (static text) | Yes, but the numbers are snapshots of the day written -> label, do not "refresh" |
| `data/lesson-work/bench/2026-10-02/**` | `bench_*.py` | Frozen benchmark key and runs | frozen copies | Frozen on purpose; do not rebuild |
| `docs/js/build.js`, `docs/data/build.json` | `python scripts/write_build.py` | Build stamp | none | Yes |

---

## 2. Ordered rebuild after `transcript-fixes.json` changes (all 18 lessons)

### 2a. What the existing entry points do (and why neither can be run as-is tonight)

**`scripts/hourly_lessons.py`** (`_main`): Supabase read (`lessons`), Recall API list, Drive scan -> `tutor_refresh`
(apply_amal_audit_rulings, rebuilds, **commit + guarded push**) -> `amal_trigger.run` -> ElevenLabs credit GET ->
load new lessons (`transcribe_once` = **paid ElevenLabs**) -> `fill_missing_recordings` (**paid ElevenLabs**) ->
`refresh_published(dates)` -> one `review_lesson.py <date> --no-push` per hour for `pending_reviews()` ->
`gap_fill_refresh` (**paid Scribe call per pending gap**) -> `decisions_refresh` -> commit -> **guarded push**.
Do not run it: it transcribes, commits and pushes. Its `pending_reviews()` only covers lessons >= `AUTO_START`
(2026-09-10), so 08-25, 09-04 and 09-05 are never re-reviewed by the hourly job.

`refresh_published(dates, raw, work)` order (the per-lesson feed): `speaking_snapshot.events()` (Supabase read) ->
`review_new_lessons.py <dates>` -> `build_clips` (`build_audit_audio.py`) -> `review_silent_credits.py` ->
`audit_vocab_unresolved.py` -> `audit_word_bank_reliability.cjs` -> `medi_corrections.py pull` (network, fail-open) ->
`detect_grammar_usage.py` -> `build_lessons_page_data.py` -> `build_sentence_ladder.py` -> `write_build.py` ->
`review_lesson.py <d> --no-push` per date.

**`scripts/review_lesson.py <date>`** steps: 1 prep (`full_audit_prep` for the one date) -> 2 r1 + r2 (`claude -p` x2,
parallel) -> 2b lesson type (`claude -p` when no valid `lesson-types/<date>.json`) -> 3 `echo_candidates.py`,
`full_audit_compare.py compare` -> 4 r3 (`claude -p`), `settle` -> 5 `full_audit_build.py`, `apply_amal_audit_rulings.py`
(Supabase read) -> 6 `build_lessons_page_data.py`, `build_grammar_console.py`, `build_amal_grammar_rules.py`,
`arabizi_everywhere.py` -> 6c `source_audit.py <date>`, `accuracy_gates.py annotate`, **`codex_rejudge.py` (Codex gpt-5.5 +
local whisper)**, `codex_rejudge.py --list`, annotate -> 6b `arabizi_gaps.cjs` (+ `claude -p` to fill gaps) -> 7 pattern
reader (`claude -p`) -> `build_amal_review.py` -> **`after_from_audit.py <date>` (mints an `amal_links` row: a new card on
Amal's hub)** -> **`amal_review_link.py` (PATCHes her review link)** -> 7d `amal_new_words.py` (+ `claude -p`) -> 7e type
reconcile (`claude -p`) -> 7c `build_tutor_data.py` -> 8 **`git add -A` + `git commit`** (always, unless `--dry-run`),
push through the guard unless `--no-push`.
`--dry-run` stops at the first stale or missing reader file (exit 2), so it cannot do a re-read. `--no-push` still commits,
still writes Amal's hub rows, still runs Codex. So `review_lesson.py` must not be run for the backfill either.

### 2b. The command list (run from the repo root; nothing here commits or pushes)

Tags: [L] pure local, [N] needs a Supabase READ (no write), [AI] paid AI, [X] must not run.

Stage A - text layer (no AI)
1. [L] `python -m pytest -q tests/test_transcript_fixes.py tests/test_medi_corrections.py tests/test_correction_mode.py`
2. [L] `python scripts/detect_grammar_usage.py` - Grammar uses on the new text (TT path; check the silent misses, item 1 of section 0).
3. [L/N] `python scripts/build_lessons_page_data.py` - rewrites `docs/data/lessons/<date>.json` turns for all 18, stops on an
   unmatched fix row. [N] for `_confirmed_new()`; offline it silently uses the 09-25 new-word list (do not run offline
   and compare numbers). At this point the slip rows are still the OLD readers' rows.
4. [L] `python scripts/full_audit_prep.py` - all 18 `<date>.txt` + `amal-sheet.txt` + `buckets.md`.
5. [L] for each date: `python scripts/echo_candidates.py <date>` (the reader brief tells readers to open it).
6. [L] proof of what is stale, per lesson (None = readers read the current text):
   `python -c "import sys,glob,os; sys.path.insert(0,'scripts'); import review_lesson as R; [print(d, R.readers_read_current(d)) for d in sorted(os.path.basename(p)[:10] for p in glob.glob('docs/lessons/20??-??-??.html'))]"`
   (run it BEFORE step 4: for the 10 lessons without a reader manifest it compares against the old `<date>.txt`, which step 4 overwrites).

Stage B - readers (the only paid part that is needed)
7. [AI] r1 + r2 per lesson (36 runs), each given the prompt of `review_lesson.reader_prompt(date, "r1"|"r2")`.
8. [L] `python scripts/full_audit_compare.py compare <date>` per lesson.
9. [AI] r3 per lesson (18 runs), prompt `review_lesson.third_prompt(date)`.
10. [L] `python scripts/full_audit_compare.py settle <date>` per lesson.
    Decide first what happens to the 13 old pass-2 files (`<date>.p2.*`, `<date>.passes.json`): left in place they are
    merged in by `union_rows` and compared by `accuracy_gates`; they read the old text.
    [AI, optional] lesson type re-read (`lesson_type_read.prompt`) only if off-lesson windows or taught words must follow
    the new text; the 10 older lessons have no file and use the hand dicts.

Stage C - merge and pages (no AI)
11. [L] `python scripts/full_audit_build.py` - stops with `SystemExit` if a `proposed-buckets.json` row or a
    `duplicates.json` keep-uid no longer resolves.
12. [N] `python scripts/apply_amal_audit_rulings.py` - mandatory right after 11 (the build wipes her rulings). It also runs
    `build_amal_review.py`, `build_lessons_page_data.py`, `build_grammar_console.py`, `build_amal_grammar_rules.py`,
    `codex_rejudge.py --list` itself when anything changed. Reads `amal_rules`; writes nothing to Supabase.
13. [L] `python scripts/amal_grammar_notes.py` (as in `amal_trigger.STEPS`).
14. [L] `python scripts/detect_grammar_usage.py` again only if `medi_corrections` rows changed; else skip.
15. [L/N] `python scripts/build_lessons_page_data.py` (ledger, marks, audit slips, accuracy annotate inside).
16. [L] `python scripts/build_grammar_console.py` ; `python scripts/build_amal_grammar_rules.py` ; `python scripts/build_amal_review.py`
17. [L] `python scripts/arabizi_everywhere.py` ; `node scripts/arabizi_gaps.cjs --json data/lesson-work/arabizi-gaps.json`
    (must print `0 words`; filling gaps in `review_lesson.py` is a `claude -p` run - do it by hand instead).
18. [L] `python scripts/source_audit.py` ; `python scripts/accuracy_gates.py annotate` ; `python scripts/codex_rejudge.py --list` ;
    `python scripts/accuracy_gates.py annotate`
19. [L] `python scripts/build_sentence_ladder.py`
20. [L/N] `python scripts/amal_new_words.py` (taps read from Supabase; candidates only for 10-01 and 10-02)
21. [L] `python scripts/medi_corrections.py propose`
22. [L] `python scripts/build_rule_book.py` ; `python scripts/write_build.py`

Stage D - proof (all local, read-only except the guard's status file)
23. `python scripts/lesson_ledger.py check` (a ledger older than `transcript-fixes.json` or the page fails here)
24. `python scripts/check_numbers.py -v` ; `python scripts/accuracy_gates.py check` ; `python scripts/check_rules.py` ; `python scripts/check_pages.py`
25. `python scripts/rule_registry.py check`
26. `python scripts/publish_guard.py check` - `review_freshness` (advisory) names every lesson whose readers read another
    transcript than the pages show; `medi_corrections` (advisory) names orphaned corrections.
27. Read `data/lesson-work/ledger/_diff.md` (before = `origin/master:docs/data/lessons.json`, after = this build) and
    `data/lesson-work/medi-corrections-report.json` (`orphaned`).

Must NOT run in the backfill:
- [X] `scripts/hourly_lessons.py`, `run_hourly_lessons.ps1`, `amal_trigger.py --publish`, `run_amal_trigger.ps1` (commit + push; paid transcription).
- [X] `scripts/review_lesson.py <date>` without `--dry-run` (commits; Codex; Amal hub rows).
- [X] `scripts/after_from_audit.py <date>` (new after-lesson card for Amal), `scripts/amal_review_link.py`, `scripts/amal_links.py create`.
- [X] `scripts/codex_rejudge.py` without `--list` (Codex gpt-5.5 judging; not Claude, still an AI run that appends to `verifications.json`).
- [X] `scripts/load_lesson.py --apply` (inserts events), `lesson_pipeline.py`, `build_report.py`, `pipeline_ext.py` failure mail
  (these three call `scripts/send_lesson_email.mjs`, mail to Medi), `fill_meet_gaps.py` queue (paid Scribe).
- Nothing in the chain messages Amal directly; the risk is new cards / changed lists on her Tutor hub (`after_from_audit`,
  `amal_review_link`, and the published `amal-review.json`, `amal-verify.json`, `amal-new-words.json`, `amal-ledger.json`
  once pushed).

---

## 3. How the three AI readers run today

**Input preparation.** `scripts/full_audit_prep.py` (`main()`; `review_lesson.py` sets `P.DATES = [d]`) reads
`docs/data/lessons/<date>.json` and writes `data/lesson-work/full-audit/<date>.txt`:
header `# Lesson <date> - <n> turns on the lesson clock (mm:ss = seconds on the page audio)`, a blank line, then one line
per turn `[mm:ss] Medi|Amal|CHAT <typed_by>: <turn.text>` (hours as `h:mm:ss`). `turn.text` is the heard text, so readers
see the overlay, not the engine. It also rewrites `amal-sheet.txt` (from `docs/data/words.json`) and `buckets.md` (from
`docs/data/grammar-buckets.json`). `review_lesson.transcript_text(date)` rebuilds the same string for freshness checks.
Note: the file is written in text mode (CRLF on Windows); `readers_read_current` accepts both hashes.

**Reader 1 and reader 2** (`review_lesson.reader_prompt(date, reader)`), two parallel `claude -p <prompt> --output-format json
--permission-mode bypassPermissions --add-dir <repo> --model claude-opus-5-5` runs (model pinned in `scripts/track.py`):
"Repo: ... Read `data/lesson-work/full-audit/READER-BRIEF.md` first and follow it exactly. You are reader r1 for lesson
<date>. Transcript: data/lesson-work/full-audit/<date>.txt. Read the WHOLE file in order. Write your JSON to
`...\full-audit\<date>.r1.json` (reader "r1"). Do not open any other reader's file, the grammar-sweep JSON, or the sweep plan.
Reply with only your counts line." + `names_note(date)` (the names glossary from `scripts/names.py`, prompt only).
The brief lets them read only `<date>.txt`, `buckets.md`, `amal-sheet.txt`, `RULES.md`, plus
`data/lesson-work/echo-candidates/<date>.json` (echo check section).
Output shape (`<date>.r1.json` / `.r2.json`):
`{"date", "reader": "r1|r2", "read", "coverage_note", "counts": {"medi_turns", "rows"}, "rows": [ {"id": "<mmdd>-<n>", "t":
"mm:ss", "t_amal", "medi_said", "amal_said", "chat", "wrong", "right", "kind": "vocab-A|vocab-B|grammar|grammar-B", "tier",
"bucket", "bucket2", "proposed_rule", "mode", "signal", "confidence", "why", "english"} ]}`.

**Reader 3** (`review_lesson.third_prompt(date)`): reads `THIRD-READER-BRIEF.md`, `<date>.disputes.md`, `<date>.txt`; writes
`<date>.r3.json`: `{"date", "reader": "r3", "note", "rulings": [{"id": "D1", "verdict": "keep|drop", "row": {...}, "why"}],
"added": [...], "challenges": [{"id": "A3", "why"}]}`. Every D-id must have one ruling.

**Validity** (`review_lesson.valid_reader_file(out, date, kind)`): the file parses as a JSON object, `date` is absent or
equals the lesson, and `READER_SHAPES = {"reader": ("rows",), "third": ("rulings",)}` - the named key must be a list; for
`third`, `added` and `challenges` must be lists when present. A failing file is renamed `*.invalid.json` and the run stops.

**Cache** (`cache_decision`, `pin`, `accuracy_gates.cache_state / write_manifest`): `<file>.inputs.json` holds sha256 of the
output and of each input - r1/r2: `<date>.txt`, `READER-BRIEF.md`, `amal-sheet.txt`, `buckets.md`, `RULES.md`,
`docs/data/names.json`, plus `prompt_sha`; r3 adds `<date>.disputes.md`, `.r1.json`, `.r2.json`, `THIRD-READER-BRIEF.md`.
Any changed input = stale = dropped and re-read. Only 8 lessons have manifests (09-16, 09-17, 09-23, 09-26, 09-28, 09-30,
10-01, 10-02); the other 10 are "legacy" and are adopted only when `<date>.txt` is byte-identical to before.
After tonight every lesson's `.txt` changes, so every reader file is stale.

**Compare** (`full_audit_compare.compare`): rows pair when `same_moment` (any of `t` / `t_amal` within `TOL = 5.0` s) AND
(`same_piece(wrong)` or `same_piece(right)`); `same_piece` = normalised strings equal, one contains the other, or at least
half the tokens of the shorter are shared. Same moment + same kind class but different piece = dispute; label
differences (kind, A/B, bucket, tier, mode) = dispute. Writes `<date>.compare.json` and `<date>.disputes.md` (D-rows, then
the agreed rows A1..An for challenges).

**Settle** (`full_audit_compare.settle`): agreed rows kept (challenged ones flagged `r3_challenge`); `keep` rulings add the
r3 row; `drop` rulings with a self-fix reason are re-checked by engine word times (`self_fix_timing`, raw Scribe) or by
`self-fix-rulings.json` keyed `(date, "p<pass>", "D<n>")` - **a D-number, which changes on every re-read**; `added` rows
join unless they repeat a kept row. Rows get `fid = <mmdd>-<nnn>` by time order.

**Merge with the human rulings** (`full_audit_build.build`, all lessons at once): `union_rows(date)` (pass 1 + pass 2) ->
pair with the 09-24 sweep (`match_sweep`) -> `rejected.json` -> `apply_chat_rule` + `signal-rulings.json` (GR-19) ->
`apply_el_prompt` (GR-25) -> `apply_demonstrative` (GR-26) -> `apply_misheard` (TR-24, Medi's overlay rows) ->
`medi_corrections.apply_rows` -> `assign_uids` -> `mark_duplicates` + `duplicates.json` -> `apply_proposals` +
`proposed-buckets.json` -> `sweep_compat` (only `grammar` and `vocab-A` rows reach the pages).
**Amal's confirmed / rejected rows are not in a repo file of their own.** They live in Supabase `amal_rules`
(source `review`: kind `audit_confirm` / `audit_skip`, `word_key` = pattern id, `payload.rows` = audit uids; `word_key`
`verify:<uid>`; source `after`: `payload.audit_uid`, kind `right|wrong|not_medi`). `apply_amal_audit_rulings.apply()` reads
them and stamps `amal_ruling` on the audit rows **by uid** (`rows.get(u)`), then `full_audit_build.sync_compat`. Copies in
the repo: the `amal_ruling` field on 117 rows of `data/full-audit-2026-09-26.json` (lost on the next build until re-applied),
`rulings_applied`, `docs/data/ai_rules.json` (AR-nnn rules with `rows` uids), `data/accuracy/verifications.json` (42 Amal
records, by uid), `data/lesson-work/ledger-amal.json` (by conflict id). Matching is by uid only: not by time, not by text.

**The 10-02 scratch run** (`scripts/bench_readers.py`, folder `data/lesson-work/bench/2026-10-02/readers/flash/`):
- `python scripts/bench_readers.py 2026-10-02 prep <engine> <tag>` wrote `readers/<tag>/2026-10-02.txt` in the same format
  as `full_audit_prep`, from `docs/data/lessons/2026-10-02.json` turns: Medi's lines replaced by the re-hear text
  (`rehear/<engine>.transcript.json`, keyed by turn index), every other line `t.get("engine") or t["text"]` (raw engine
  text, not the overlay), `newline="\n"`.
- r1 / r2 / r3 were not started by the script: agents were given READER-BRIEF.md / THIRD-READER-BRIEF.md with the scratch
  `.txt` and wrote `readers/flash/2026-10-02.r1.json`, `.r2.json`, `.r3.json` there (no `.inputs.json` manifests).
- `compare <tag>` / `settle <tag>` set `full_audit_compare.WORK = sdir(date, tag)` so compare.json, disputes.md and
  settled.json land in the scratch folder. `settle` then pairs scratch rows with the published
  `data/lesson-work/full-audit/2026-10-02.settled.json` (`kind_class` + `same_moment`, then `same_moment` alone) and writes
  `compare-with-published.json` (`in_both`, `only_here`, `only_published`).
- Nothing published: `full_audit_build.py` was never run on it, no ledger, no database. Two leaks to know: `settle` still
  reads `docs/data/lessons/<date>.json` and raw Scribe for GR-24 from the real repo, and looks for `self-fix-rulings.json`
  in the scratch folder (absent there).
This is the pattern to reuse for a no-publish re-read of all 18: one scratch `WORK` per lesson, readers pointed at it.

---

## 4. Everything attached to a transcript line by time or by text

| What | File | Key / matching rule | What breaks when a line's text or time changes |
|---|---|---|---|
| Heard-word overlay rows (121; 65 by Medi) | `data/lesson-work/transcript-fixes.json` `rows` | `date`, `who`, `t` (page line start, +-1.0 s), `engine_wrote` substring -> `heard`; `set_who`, `set_t`, `insert_after` variants | Page path: `SystemExit` in the lesson-data build. Track path: silently not applied. `unmatched()` tests the engine text; `apply()` replaces in the current text, in row order. |
| Medi's page corrections | Supabase `transcript_corrections` -> `data/lesson-work/medi-corrections.json` (+ `medi-corrections-hand.json`) | `lesson_date`, `turn_t`, `turn_who`; `target.src` = producer id (`FA-uid`, Word Bank event id, use bucket + t); fallback `medi_corrections.matches`: `turn_t - 3 <= sec(row.t) <= turn_end + 3`, same kind class, `_piece(wrong)` contained either way, or same bucket. More than one fingerprint hit = orphaned. | Orphaned (listed in `medi-corrections-report.json`, advisory only, never a failed build) - the correction silently stops applying. |
| Medi's standing text rules | `data/lesson-work/correction-rules.json` (0 today) | `pattern`: same speaker, `engine_wrote` in the line, same 3-word context `_ctx` | Context word changes -> rule no longer fires |
| TR-24 misheard drop | `full_audit_build.apply_misheard` | Medi's overlay row within 4 s of the slip `t` and `norm(engine_wrote) == norm(row.wrong)` | New readers read heard text, so `wrong` no longer equals the engine word (harmless: the false slip should not be written at all) |
| GR-11 kaman marra | `transcript_fixes.kaman_marra` | his line is only "كم مرة؟" within 15 s after Amal, and she repeats | Recomputed each build |
| Reader rows across readers / passes / sweep | `<date>.r1/r2/r3`, `.settled.json`, `.p2.settled.json`, `data/grammar-sweep-2026-09-24.json` | `same_moment` (5 s on `t` / `t_amal`) + `same_piece(wrong|right)` | Old pass-2 and sweep rows may stop pairing -> kept as extra rows (double count risk) or "sweep-only kept" |
| Audit row uid | `data/full-audit-2026-09-26.json` | `"FA-" + sha1(f"{date}|{int(sec(t))}|{norm(wrong)}|{kind_class}")[:8]`, `x` suffix on a repeat | New uid whenever `t` moves a second, `wrong` is re-worded, or vocab <-> grammar flips |
| Amal's rulings (117 rows carry one) | Supabase `amal_rules`; copies: `amal_ruling` on audit rows, `docs/data/ai_rules.json` | uid list in `payload.rows`, `payload.audit_uid`, `verify:<uid>` | Ruling not re-applied, no error: a slip she confirmed goes back to B (unscored) or disappears; a slip she rejected comes back as counted |
| Patterns for Amal's review (90) | `data/lesson-work/full-audit/patterns.json` | `rows`: uids | Row leaves its pattern, shows as a one-row pattern again |
| Verification records (356: 314 Codex, 42 Amal) | `data/accuracy/verifications.json` | `uid` | Row loses its check -> "pending", lesson may drop out of verified, Amal's verify list regrows |
| Hand rejections (54) | `full-audit/rejected.json` | `date` + `same_moment(t)` + `same_piece(wrong)` (+ kind class) | A rejected slip is scored again if its `wrong` is re-worded |
| Hand duplicate pairs (7) | `full-audit/duplicates.json` | `keep` / `drop` uids | `SystemExit` when keep is missing and drop exists; silently skipped when both are gone |
| Signal re-rulings (4) | `full-audit/signal-rulings.json` | date + `same_moment` + `same_piece(wrong)` + `signal == "chat-fix"` | Row rejected as chat-only again |
| Proposed buckets (3) | `full-audit/proposed-buckets.json` `rows` | date + `same_moment` + `same_piece(wrong)` | `SystemExit("no audit row at ...")` |
| Self-fix rulings (4) | `full-audit/self-fix-rulings.json` | `(date, "p1|p2", "D<n>")` dispute number | Any re-read renumbers disputes -> ruling points at the wrong dispute or none |
| Sheet verdicts (302) | `data/lesson-work/sheet-verdicts.json` | `(date, mmss, arabic)` exact; else the one verdict at the same `mmss`; else same `word_core` within `VERDICT_DRIFT_S = 120` s | Beyond that: card falls back to the automatic sheet match ("Not on sheet" flips, Words % moves) |
| Grammar use rulings (8) | `data/grammar-usage-rulings.json`; Medi's "not a use" taps | `date` + `bucket` + `abs(t - use.t) <= 3.0` (use `t` = track-turn start) | A ruled-out use counts again if the turn start moves |
| Grammar use <-> slip pairing | `scripts/grammar_math.py`, `build_grammar_console.use_verdict` | same date, `abs(int(slip.t) - int(use.t)) <= 2` | Use and slip of one moment both count |
| Lesson ledger marks / conflicts | `data/lesson-work/ledger/<date>.json` | mark ids `wb:<event id>`, `ra:<uid>`, `rg:<uid>`; conflict id `"<kind>-" + sha1(date|kind|markA|markB)[:10]` | Medi's / Amal's ledger answers (`ledger-rulings.json`, `ledger-amal.json`; both empty today) key on conflict id |
| TR-18 Word Bank override | `lesson_ledger.build` | a Word Bank event on a turn whose `heard[].engine_wrote` equals / contains the event token -> not scored | Recomputed; this is the only way the overlay changes a stored word event's score |
| Transcript chips and underlines | `scripts/transcript_marks.py` -> `tmarks` | item time inside a Medi turn's `[t, end]` +- `SLACK = 2.0` s; underline = `wrong` / `right` found in the turn text after normalising, else "closest" | Recomputed; watch `marks_report` (placed %, `ul_closest`, `ul_none`) |
| Word Bank miss -> line text on the card | `build_lessons_page_data.build` | `bisect` on Medi turn starts, `t_start - turn.t < 60`, token must be in the line | Falls back to the event's own `said` |
| Reader word slip folded into a Word Bank miss | same | `abs(e.t - tv) <= 5` and `lesson_ledger.same_word` | Recomputed |
| Stored word events | Supabase `speaking_events` / `docs/data/word-bank-evidence.json` | `id = sha(lesson, source_sha256, [local_start, local_end])`, `item_ids`, `row_id`, `t_start` on the raw track | Not affected by the overlay at all (that is the problem in section 5) |
| Word Bank review patches (1,823) | `docs/data/word-bank-review.json` | event id + `expected` {source_sha256, row_id, word_key, text, t_start, ...} | Bound to stored events; unaffected |
| Word Bank clips | `docs/data/word-bank-clips.json`, `clips/context-*.mp3` | event id | Unaffected |
| Grammar console / Amal review clips | `clips/gc-<sha1(date|"a-b" seconds)>.mp3` (`cut_clip`) | slip `t` and `t_amal` in seconds | New times cut new files; old files stay behind unreferenced |
| Fluency sentences + Medi's swipes | `docs/data/sentence-ladder/<date>.json`; Supabase `sentence_labels` | `sid = f"{date}:{L|S}:{int(round(t*10))}"` | Text-only changes keep ids; `set_t` or a re-split sentence orphans his swipe |
| Names layer | `docs/data/lesson-names/<date>.json` | turn index + character offsets into `turns[i].text` | Offsets wrong after any text change; rebuild with `names.py layer` (only tests read it) |
| Lesson type read | `data/lesson-work/lesson-types/<date>.json` | `off_lesson` from / to `mm:ss`, `taught_words[].t` | Text-only: fine; cross-check (LS-09 / LS-10) re-runs on LJ turns |
| New-word verdicts (187) / taught-word verdicts (85) | `amal-new-words-verdicts.json`, `taught-words-verdicts.json` | `(date, key)` / `(date, arabic)` | Candidate keys come from Amal's words; change only if her lines change |
| After-lesson question taps | Supabase `amal_rules` source `after` | `payload.audit_uid` | Same as Amal's rulings |
| Reader cache | `<reader file>.inputs.json` | sha256 of `<date>.txt` etc. | Stale -> re-read needed (the freshness proof) |

---

## 5. Numbers that do NOT re-read the transcript (need a label)

| Number / page | Where it comes from | Why the overlay does not move it |
|---|---|---|
| **Words %**, right / partial / wrong / scored, "N words", `vocab_correct` and the Word Bank-miss cards (Lessons page, Progress Overview) | `speaking_events` (via `docs/data/word-bank-evidence.json`) + `word-bank-review.json` patches, scored by `lessons_page_node.cjs` | Events were detected once from the raw engine words at load. A word the overlay now says he said gets **no new event**; a word the engine misheard loses its score only through the ledger's TR-18 override (exact token match with `engine_wrote` on that turn). So Words % can lose credits / misses but never gain the corrected word. |
| Word Bank page: accuracy, words known, per-word status and streaks; Progress > Vocab series; Flashcards "boost" selection | same stored events + overlay + `word-bank-audit-slips.json` | Same. Only the reader word slips (`audit-slips`) follow a re-read. |
| Word event `text`, `original_text`, `context` shown on Word Bank evidence rows and the speaking-review pages | stored event JSON | Engine text frozen in the database row |
| Static lesson pages `docs/lessons/<date>.html` | written at load from raw Scribe | Always engine text (and they are the input of the page-turn parser, so they must not be rewritten) |
| Talk %, words per minute, fillers, wait time, flow | raw Scribe word timings in `build_lessons_page_data.metrics` | Raw words, not overlay text (correct to leave; `fillers.in_turns` does read overlay text) |
| Grammar slips, vocab slip cards, Grammar % numerator | reader files r1 / r2 / r3 (AI) -> audit JSON | Stay as the old readers wrote them until the readers re-read. `review_freshness` reports this but is **advisory**, so the guard will not block a publish with old slips on new text. |
| Pass-2 rows and the "verified" mark of the 13 older lessons | `<date>.p2.*`, `<date>.passes.json` | Nothing regenerates pass 2; agreement between a new pass 1 and an old pass 2 decides `release.status` |
| Amal-confirmed / rejected slips, Tutor "check these moments", verified counts | `amal_rules` taps + `verifications.json`, by uid | Stored against old uids |
| Grammar uses on lines where the fix row did not land on a track turn | `detect_grammar_usage.py` through `lesson_turns` | Silent miss on the TT path (12 of 121 rows today) |
| Slips page (`docs/data/tally.json`), machine grammar candidates (`docs/data/grammar-audit.json`) | raw `transcript.txt` / TT, not in any chain | Legacy, frozen |
| AI Reports pages (`docs/reports/*.html`: benchmark, process audit report #7, etc.) | numbers typed into the report sources | Snapshots of the day they were written |
| Flashcard results, verb checks, homework | `card_results`, `verb_check_links`, `homework_answers` | Not transcript-derived |

Smallest honest label set: (a) "Word scores are from the first listen (stored events)" on Words % everywhere it shows,
(b) "slips read on <date of reader run>" per lesson until its readers re-read (the data is `readers_read_current(date)`),
(c) the static lesson page says it shows the engine's text (it already carries the PG-27 second-listen block).
