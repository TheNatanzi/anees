# Eng audit 2026-09-29: area 4 (hourly job end to end) + decision 7 (publish guard)

Worker C · branch `eng-audit-c` (merged `eng-audit-2026-09-29` at c137a17) · worktree C:\dev\anees-eng-c. Nothing was pushed to master.

**Scorecard**
- Area 4 (hourly job): ⚠ The failures are fixed on the branch. Two old lessons (09-23, 09-26) still need re-reading, and a few problems sit in files I don't own.
- Guard (decision 7): ✅ Built and tested. It **blocks today**, because other workers' checks are failing or not merged yet (see "At merge").

## 1. How publishing works today (checked with `gh api repos/TheNatanzi/anees/pages`)
1. GitHub Pages uses a `legacy` build from `master:/docs`. There is no workflow file; the only Action is GitHub's own `pages-build-deployment`. So **every push to master is live within a minute.**
2. Scheduled task "Anees lesson pipeline" runs hourly at :15: `powershell ... C:\dev\anees-hourly\scripts\run_hourly_lessons.ps1`.
3. That script runs `git pull --ff-only origin master`, then `python scripts/hourly_lessons.py`, and logs to `C:\dev\anees\data\lessons\hourly.log`.
4. `hourly_lessons.main` steps:
   - `tutor_refresh` (commit, then PUSH)
   - plan new lessons (Recall API + Drive) and load them
   - `refresh_published`: Word Bank, clips, ladder, and `review_lesson --no-push`, which commits
   - `publish` (commit, then PUSH)
   - or, if nothing is new: PUSH the "stranded" commits
   - `gap_fill_refresh` (commit, then PUSH)
   - `decisions_refresh` (commit, then PUSH)
5. Other pushers:
   - `review_lesson.py` step 8, when run by hand
   - `lesson_pipeline.git_publish` / `publish` (a retired job, still importable)
6. None of the pushers above checked any number before pushing.
7. Other scheduled task: "Anees vocab import" runs from `C:\dev\anees`. It writes only to Supabase and a local log, and does not push.

**After this branch:** every pusher calls `publish_guard.guarded_push()`, which does:
1. `pull --rebase`
2. the required checks
3. the push, only if every required check passed

A test (`test_no_script_pushes_around_the_guard`) fails if any script in `scripts/` pushes any other way.

## 2. Issues, ranked by harm (evidence → fix → commit)

| # | Issue | Evidence | Fix (commit) |
|---|---|---|---|
| 1 | Every push published unchecked (8 pushers) | grep: hourly_lessons ×5, review_lesson ×1, lesson_pipeline ×2 | All go through the guard (ba07725, 2f2eba7, a5fdb9d) |
| 2 | Reader files reused because they exist | 09-23's transcript grew by **266 lines** and 09-26's by **149 lines** (Meet gap fill, 09-27 01:15) after their readers ran (commits 7b3cfda, 402714c). Those lines were never audited. | Input manifest per reader file: transcript, briefs, amal-sheet, buckets, RULES.md, names.json, prompt. Prep always runs. Old files are kept only if their transcript is unchanged (a5fdb9d, 7521b3d). |
| 3 | A review failure was never retried; the comment said "the next hour retries" | 09-26: `=== review_lesson` at 16:17:18, then `published` at 16:17:35. `plan()` never re-plans a published date. | Failed steps are stored as **open failures**. They block every push and are retried every hour. `pending_reviews()` re-reviews one lesson per hour (2f2eba7). |
| 4 | Build failures ignored (`check=False` / "never blocks") | Ladder, review, gap-fill rebuilds, tutor apply/builds, and review_lesson step 6/7 builders. Arabizi gaps still let the push happen. | `run_step()` records every failure. The push is blocked and the run exits 1 (2f2eba7, a5fdb9d). |
| 5 | **A new lesson missed the Grammar % page** | Live master: 09-28 has `grammar.uses = None`, `pct = None`, and grammar-usage.json stops at 09-26 (09-26 was added by a hand commit). `detect_grammar_usage.py` was never in the hourly path. | Added to `refresh_published` (cf8c24a). The guard's `lesson_coverage` check, run on live master, reports exactly this gap. |
| 6 | 515 of the 1,240 Grammar console clips linked on master were never committed | `*.mp3` is gitignored; only new-lesson clip folders were force-added. The page falls back to seeking the full lesson audio. | Built clip folders are force-added before the push (eeda5bf, f05103c) |
| 7 | `data/accuracy/verification-queue.json` is rewritten on every build and never committed | Every hour's clean-tree check would block | A final commit of everything the run built (ded32d1) |
| 8 | Hard-coded per-lesson data (**not my file**: build_lessons_page_data.py) | `LESSON_TYPES` stops at 09-26, so 09-28 shows "free-speak" marked `type_source: claude-read` with "Not read yet". `TAUGHT` stops at 09-18, so a new lesson shows 0 new verbs. `if date == "2026-09-23"` special case. `_confirmed_new()` silently falls back to a hard-coded 2-word list if the DB is down. lessons-page.js has a hard-coded 09-10 audio case. | The guard reports "lesson type not read" as a warning. **Owner:** set `type_source: "default"` when a date is missing, and raise instead of falling back. |
| 9 | Stale outputs not rebuilt by the hourly job | `grammar-audit.json` (machine candidates, read by the Grammar console) stops at 09-23. `grammar-usage.json` `"updated": "2026-09-23"` and `grammar-console.json` `"updated": "2026-09-29"` are hard-coded strings. `tally.json` (Slips page) is frozen at 09-05, but it is hand-curated and only linked from legacy-words.html. | Reported (not my files) |
| 10 | `apply_amal_audit_rulings.py` marks rulings applied in the DB, **then** rebuilds with `check=False` | If a rebuild fails, the next hour sees nothing new and the pages stay stale | The hourly job now rebuilds everything after a failed tutor hour (`rebuild_all`). **Owner:** make the rebuilds `check=True` before the DB PATCH. |
| 11 | `build_tutor_data.py` silently skips a DB table on error | `except Exception: print("skip", table)`: Amal's open verb-check / word-review links disappear from tutor.json | Reported (not my file) |
| 12 | hourly.log was unreadable | PowerShell `*>>` wrote UTF-16 plus NativeCommandError records around git's progress text. The exit code was never logged. | `run_hourly_lessons.ps1`: UTF-8 lines, plain stderr, pull failure and exit code logged, exit code passed to Task Scheduler (67765a4). Checked with a stub run. |
| 13 | The review link was always "None" | review_lesson parsed `HUB`, but amal_review_link.py prints `REVIEW` | Fixed (a5fdb9d) |
| 14 | Old paths | `run_lesson_pipeline.ps1`, `run_paid_engines.ps1`, `run_sm_ar.ps1` point at `C:\dev\anees` (not scheduled). `verify_speaking_release.py` reads `C:/dev/anees/docs`. **The "Anees vocab import" task runs code in `C:\dev\anees`, which is 204 commits behind master.** | Reported; decision for Medi |
| 15 | Writes outside the checkout | Raw archive only, by design: transcripts, tracks, `meet_decisions.json`, `hourly.log`, gap-fill Scribe JSON. `build_clips` **rewrites `raw/audio-source-map.json` every run**. Builders read raw from a hard-coded `C:\dev\anees\data\lessons` and ignore `--raw`. | Reported |
| 16 | A saved Scribe transcript had no run-log line with its hash or model | Worker D's request | `scribe.saved` line: path, sha256, model (falls back to scribe_v2) (e59f9be) |

**Simulated new lesson:** 09-28 is a real example (loaded by the hourly job on 09-28).
- It reached: the lesson page, lessons.json, the detail file, the ladder, the Word Bank evidence and audit, the Grammar console, the Tutor page and amal-review.
- It missed: Grammar % (#5), a real lesson type (#8), new verbs (#8), and clips (#6).
- A guard run on a checkout of live master blocks with `2026-09-28 missing from: grammar-usage.json`.
- `hourly_lessons.py --dry-run`, run against the live DB, Recall and Drive (read-only), shows nothing new, no open failures, and pending reviews for 09-23 and 09-26.
- `review_lesson.py 2026-09-23 --dry-run` on real data stops with "stale: inputs changed".

## 3. Tests (offline; before = the old code)

| File | Before | After |
|---|---|---|
| tests/test_review_lesson.py (new) | 8 failed | 9 passed. The ninth (stop-early evidence) was written later and failed against the pre-fix script. |
| tests/test_hourly_lessons.py | 7 new tests failed, plus 3 added later that each failed first | 19 passed |
| tests/test_publish_guard.py (new) | no-bypass scan failed (9 bare pushes) | 20 passed, including a real-git bare-remote end-to-end test |
| tests/test_publish_guard_status.cjs (new) | n/a | 4 passed |
| tests/test_m8_pipeline.py | the liveness test would now hit the guard | isolated, plus a new guard test: 16 passed |

The guard's own test subset was run with sockets blocked: 215 passed in about 13 s. It never includes `test_m4_after` or `test_m5_cards` (they write to the live DB), and a test enforces that.

## 4. What the guard checks every hour (scripts/publish_guard_config.json)
**Required** (a fail, timeout, crash, missing script or unknown id blocks):
- `step_failures`: this run's failed steps, plus open failures from earlier hours
- `clean_tree`: what gets checked is exactly what gets published
- `json_data`: all 79 docs/data JSON files parse, and the key files have the right shape
- `lesson_coverage`: every lesson reaches lessons.json, the lesson page and detail, the ladder, Grammar console and usage, accuracy-release, Word Bank evidence and audit, and committed audio
- `review_done`: every lesson has a settled audit
- `accuracy_gates`, `check_numbers`, `check_rules`, `check_pages`
- `arabizi_gaps`: must print "0 words"
- `tests_py`: 18 offline files
- `tests_node`: 19 files

**Advisory** (warn only): `review_freshness`, `lesson_type_read`.

**Budget:** 300 s total. It takes about 22 s today.

**On a block:**
- No push, so the live site keeps the last good version.
- **The local commits are kept.** Reverting would re-trigger the half-done republish and paid reader runs every hour; keeping them loses nothing, and the next hour re-checks them.
- One `PUBLISH BLOCKED (<source>): <reason> -- ... N local commit(s) wait` line in hourly.log.
- The reason goes to `data/publish-guard/state.json` (gitignored, local).
- The run exits 1.

**On a pass:** `docs/data/publish-guard.json` is committed, then the push runs. It holds the checks, the warnings and the **last block**, so a block Medi could not see live appears on System Settings after the next pass. The System Settings line was checked at 375 px in dark mode.

**Optional belt:** `publish_guard.py hook` works as a git pre-push hook, so manual pushes are checked too. **Not installed** (it would affect the live checkout tonight).

## 5. Decisions for Medi (yes/no)
1. After merge, re-read 09-23 and 09-26 automatically (their transcripts grew after their readers ran; their audit numbers will change)? yes/no
2. If a new lesson's review fails (for example, the Claude login expires), hold **all** publishing until it passes? (Current setting: yes.) yes/no
3. When blocked, also publish a status-only commit, so the live Settings page shows the block right away (the data stays on the last good version)? yes/no
4. Install the pre-push hook, so manual pushes to master are checked too? yes/no
5. Point "Anees vocab import" at the hourly checkout (C:\dev\anees is 204 commits behind master)? yes/no
6. Make `review_freshness` required (block while any lesson's readers are stale)? yes/no

## 6. At merge (coordinator)
- With today's data the guard **blocks**:
  - accuracy_gates: 11 problems (grammar.mistakes ≠ audit rows)
  - `scripts/check_numbers.py` and `scripts/check_pages.py` are missing
  - `tests/test_verb_addons.cjs` has failed since merging eng-audit-2026-09-29
- Run `python scripts/publish_guard.py check`: it must say `OK - publishable` before the merged branch reaches the hourly checkout. Otherwise nothing will publish (that is by design).
- The required list lives in `scripts/publish_guard_config.json`. Add or remove checks there; never move one to advisory to make a push go through.
- Optional: rename the old mixed UTF-16 `C:\dev\anees\data\lessons\hourly.log` once, so the new UTF-8 log starts clean.

## 7. Not done
- Re-reading 09-23 and 09-26 (waits for decision 1).
- Changes in files I don't own: #8 build_lessons_page_data, #9 audit_grammar_lessons / detect_grammar_usage / build_grammar_console, #10 apply_amal_audit_rulings, #11 build_tutor_data, #14 verify_speaking_release, and the old .ps1 scripts. I also did not move the `scribe_v2` fallback into `pipeline_ext.transcribe_with_retry`.
- Worker D's review gaps. They are not in review_lesson:
  - a by-meaning sheet reader (09-28 has 31 vocab rows and 0 sheet verdicts). Where it would go: after step 4 "settle", before step 5 `full_audit_build`.
  - a context read of 15-s flags / same-episode pairs, in the same spot.
  - The guard does not detect either yet.
- The hook is not installed. The guard has not run in the live checkout (by rule).

## 8. Hand check (5 random findings)
- #5 held: live master 09-28 has grammar uses/pct = None.
- #8 held: live 09-28 shows the default type labelled claude-read.
- #9 held in part: the grammar-audit and "updated" strings hold; tally.json is a hand-curated legacy page.
- #14 held and was worse than written: 204 commits behind.
- #11 held: code read.

**4 of 5 fully held, 1 in part.**
