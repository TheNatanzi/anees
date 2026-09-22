# OVERNIGHT PROMPT — Finish verb drills + every lesson in + full audit (2026-09-22)

Paste everything below the line into a fresh Claude Code chat (Opus, high effort) and leave it running.

---

You are finishing the Anees application overnight while Medi sleeps: https://github.com/TheNatanzi/anees,
live at https://thenatanzi.github.io/anees/. Work alone until every part below is done or truly blocked.
Nobody will answer questions tonight: when something is open, pick the safest choice, write it down in
the report, and keep going.

## 0 · Set-up (do first)

- **Never work in `C:\dev\anees`.** That clone is stale and has uncommitted files. Make a fresh git worktree from
  `origin/master` in your scratchpad. The raw lesson archive `C:\dev\anees\data\lessons\` (git-ignored) is the
  one exception: read it, and add new raw lesson folders there.
- Read first, in this order: `plan/VERB-DRILLS-SPEC-2026-09-22.md` (rulings are final),
  `plan/NEXT-PROMPT-verb-drills-2026-09-22.md`, `plan/NEXT-PROMPT-flashcards-selection-2026-09-21.md`
  (validation list), `docs/word-bank-review-rules.md`, and your memory notes on Anees lessons (Recall bot,
  Meet accounts, lesson-ingest recipe of 2026-09-21).
- Before you start, record: `card_results` row count (7 on 2026-09-22), `origin/master` hash, ElevenLabs
  spend in `data/budget.json`.

## Hard rules (break none)

1. **Send nothing to Amal and email nobody.** Minting a link is fine; sending is Medi's job. Pipelines run with
   send/email switched off.
2. **Browser checks stub every write**: `window.fetch` POST/PATCH/DELETE → fake 201. `card_results` count must
   end the night where it started.
3. **Never re-transcribe a lesson that already has a `scribe*.json`.** Reuse it. (On 2026-09-05 a re-run on the mixed
   Meet audio overwrote clean per-person tracks and made things worse.)
4. **Per-person tracks beat the mixed Meet recording.** Use the mixed recording only when no tracks exist, and
   always merge the Meet chat sidecar (Amal's typed lines).
5. **Spending cap $10 total** (ElevenLabs Scribe + Recall). Log every cent in `data/budget.json`.
6. **Never browse Stitch. Quizlet only through Medi's Chrome and never solve a bot check.** You shouldn't need either tonight.
7. **Guesses stay tagged.** A guessed form never becomes `provenance: document`. Amal's answer always wins.
8. **A step only counts as done when it's live.** That means: push to `master` → GitHub Pages rebuilt → live page checked.
   Run the full validation list before every push (section 5).
9. A test that already fails on `origin/master` is not yours to fix tonight. List it and move on. The 14 that failed on
   2026-09-22 are in m3_planner, m4_after, m7_index, stale_banner, tally and ai_sections. A test that *your* change
   breaks must be fixed, or the test updated with a written reason tied to a Medi ruling.
10. Commit small, one topic per commit. Pull and rebase before each push, because another chat may push the same night.
    Build-stamp conflicts (`docs/data/build.json`, `docs/js/build.js`): take theirs, and `write_build.py` restamps.
    Migrations: take the next free number (017 is taken twice; `verb_check_links` is `018`).

## Part A · Every lesson in (do this first — Recall keeps audio only 7 days)

**Goal:** every lesson Medi ever had with Amal has a transcript page, speaking events in the database, and
correct Word Bank evidence. Check **all** sources, not just the Recall bots.

A1 · Build one inventory table (`plan/LESSON-INVENTORY-2026-09-23.md`): one row per date, a column per source,
and a verdict (lesson / not a lesson / duplicate).
- **Recall.ai**: list every bot through the API (`RECALL_API_KEY`, region `us-west-2`), not just
  `data/lessons/recall_bots.json`. Unledgered bots exist; 2026-09-14 was one. Download media for any bot still inside
  its 7-day window **first**.
- **Google Drive `G:/My Drive/Meet Recordings`** (host account wc@adibs.com): every video, every
  "Chat Transcript", every "Notes by Gemini" doc. On 2026-09-22 it held June 17, June 26, July 1, July 6, July 23,
  Aug 3, Aug 19, Aug 22, Aug 23, Aug 25, Sep 1, Sep 4 and Sep 5 recordings. Decide from the content (Amal's voice,
  Arabic being taught) which of these are Amal lessons. Some June and July calls may be other meetings. Also search
  Drive (MCP) for other recording folders or shared files.
- **Google Calendar** (MCP): lesson events with Amal, so dates with no recording show up as "missing".
- **Local archive** `C:\dev\anees\data\lessons\*` and `data/lessons/processed.json`.
- **Site**: `docs/lessons/*.html` and the `lessons` table in Supabase.

Known state on 2026-09-22:

| Date | Raw audio | On site |
|---|---|---|
| 08-22, 08-23, 09-01 | `audio.mp3` + `scribe.json` (mixed Meet) | **no** |
| 09-14 | Recall tracks + scribe per person | DB yes. Page is on branch `lesson-2026-09-14` (commit 3964568), **never pushed** |
| 09-18 | none anywhere (Recall, Drive) | no. Confirm it's still absent, then list it as "no recording" |
| 08-25, 09-04, 09-05, 09-10, 09-11, 09-15, 09-16, 09-17, 09-19 | yes | yes |

A2 · Load every missing lesson using the recipe in your 2026-09-21 lesson-ingest memory (one track per person →
`sync_speaking_lesson.build_transcript` → detected events → `sync_events` → `lessons` row →
`docs/lessons/<date>.html` → regenerate `docs/data/word-bank-evidence.json` from the `speaking_snapshot` RPC →
additive review patches with generic rules only → `build_audit_audio.py` → `audit_word_bank_reliability.cjs` →
`write_build.py`). For mixed-audio lessons, use the pitch-label speaker split (commit 6eb7a4d) and mark the page
"speakers estimated". Bring 09-14 onto master by rebasing its commit, not by force-pushing.
Add every new bot to `recall_bots.json` so the hourly job stops missing them.

A3 · **Audit every lesson, old and new.** Produce one scorecard row per lesson in
`plan/LESSON-AUDIT-2026-09-23.md`:

| Check | Pass when |
|---|---|
| Coverage | transcript time ≥ 90% of audio time, no gap > 60 s that isn't silence |
| Speakers | per-person tracks, or pitch split with < 5% unlabeled. Medi vs Amal share looks like a lesson |
| Transcript page | opens live, audio plays at the right line (spot-check 5 lines per lesson against the audio) |
| Database | `speaking_events` count for the date = events in the transcript build; `lessons` row present |
| Word Bank | every Doc word Medi said is credited to that lesson; zero credits for words not said (sample 20 per lesson against the transcript text, all for lessons < 20 events) |
| Amal's chat lines | Meet chat sidecar merged where one exists |
| Reliability script | `audit_word_bank_reliability.cjs` clean for the date |

Fix what fails when the fix is generic (a rule or a parser fix). Never hand-edit one lesson's numbers. Anything you
can't fix goes in the report with its date, line and timestamp.

A4 · Make it stay fixed: the hourly job (`process_recall_queue` / pipeline) must (a) discover bots from the Recall API,
not only the ledger, and (b) pick up new Drive Meet recordings without re-transcribing lessons that already have
tracks. Add a test for each.

## Part B · Finish verb drills (spec steps 3 and 4)

State: step 1 (engine, 88ec6a6 / 0fe40df) and step 2 (catalog guesses + Amal check list, ed85b2b) are live. Medi sent
Amal the check link on 2026-09-22.

B0 · Amal's answers: run `python scripts/verb_check_links.py pull`. If she answered anything, rebuild the catalog
(`python scripts/build_word_bank_catalog.py --document data/vocab/word_bank_source.md`), check that her fixes show as
"Checked by Amal", and add her fixes as golden forms in `tests/test_verb_forms.py`. If a fix reveals a rule the
engine got wrong, fix the rule and rerun `scripts/verb_forms_holdout.py`. The hit rates may not drop. Pull again at
the end of the night.

B1 · **Step 3: Verb drills section** on the Flashcards home screen (`docs/cards.html`, logic in a pure module with tests
like `docs/js/cards-selection.js`):
- **20 verbs, random**: tense All / Past / Present / Command. 20 different verbs, each once, random tense (from the
  option) + random person.
- **5 or 10 verbs, full**: every person of the chosen tense(s) for those verbs.
- **Direction both ways (Medi ruling 6)**: English front ("she · knew") or Arabic front
  ("heyye 3irfat · هي عرفت"), using the existing "Front of the card" switch (`pref.mode`).
- Same swipe cards, same `card_results` row, same FSRS. Guessed forms carry a small "not checked by Amal" tag;
  checked ones don't.
- Card key: the documented word key when the form is in the Doc, else `form:<entry id>:<person>`. Map `form:` keys back
  in `word-bank-core.js` so Word Bank and Progress count them.
- Tenses in drills: Present, Past, Command only (Future stays out).

B2 · **Step 4: Level 2** (spec section 4). Verb tags (`object: yes/no`, `preps: [...]`) seeded from Amal's Quizlet
sets "verb + preposition collocations" (36) and "Pronoun Objects With Verbs" (25); tag the rest yourself. Add-on
engine for endings (-ni, -ak/-ik, -o, -ha, -na, -kom, -hom with the stem changes: 3ata → 3atani, akhad → akhadtak) and
preposition + person (ma3, la, min, 3an, 3ala, forms as in Amal's sets "Ma3 + pronouns", "La + Pronouns", "Other
Prepositions + Pronouns"). Golden-test the add-ons against every example in those Quizlet sets and report the hit
rate. Level toggle on the Verb drills section. Card key `form:<entry id>:<person>:<add-on>`.
Put the level-2 tags on Amal's check list as a **second, new link** (mint it, don't send it). Her tags win.

## Part C · Full audit (after A and B are live)

C1 · Tests: the whole validation list (section 5) plus `python -m pytest -q tests/`. Compare the failure list with
`origin/master` from the start of the night: no new failures.

C2 · Browser pass on the **live** site, desktop and phone width (375 px), light and dark, writes stubbed:
index, lessons (every lesson page: opens, audio plays), Word Bank (a verb with guesses, a checked form, a phrase verb
like "dir baalak"), Progress (all tabs), Flashcards (every section incl. Verb drills L1/L2 both directions, one full
round of swipes), homework, Amal pages (verb-check, word-review, after/plan open with a test token only). No console
errors, no sideways scroll.

C3 · Data audit: every Word Bank verb has all 8 / 8 / 3 persons in Present / Past / Command. No `form:` key without a
catalog entry. Word Bank counts = Progress counts = Flashcards counts for the same filter. Evidence JSON matches the
`speaking_snapshot` RPC.

C4 · Adversarial self-review. Re-read every diff from tonight as a hostile reviewer: wrong-key risks, double-counted
events, lesson-date mix-ups, anything that could credit a word Medi never said. Fix what you find. If the Codex CLI
works, get a second opinion on the lesson audit. If it's broken, say so.

## Part D · Morning report for Medi

Write `plan/OVERNIGHT-REPORT-2026-09-23.md` **and** publish it as a private Artifact page. Medi has severe ADD, so:
one line first, then a scorecard table, then short one-line bullets, then **one bold action**. No paragraphs over
3 lines. Plain words, define any term. Contents:
- Lessons: table of every date → source → on site? → audit pass/fail. Dates with no recording.
- Verb drills: what's live, hit rates (engine + add-ons), Amal's answers so far, the level-2 check link (not sent).
- Audit: tests before/after, browser pass, anything still broken with date/line.
- Money spent tonight vs the $10 cap. `card_results` count start vs end.
- The single thing Medi must do next.

Update your memory notes (lesson inventory, verb drills status) so the next chat starts from the truth.

## 5 · Validation before every push

`node --check` on changed JS and on cards.html's inline script · `node tests/test_fsrs.cjs` ·
`test_vocabulary_memory.cjs` · `test_word_bank.cjs` · `test_word_bank_reliability.cjs` · `test_context_review.cjs` ·
`test_vocabulary_stats.cjs` · `test_cards_selection.cjs` · `test_verb_check.cjs` ·
`node tests/test_transcript_player.cjs docs/js/transcript-player.js` · any new test you wrote ·
`python -m pytest -q tests/test_m5_cards.py tests/test_verb_forms.py tests/test_catalog_gloss.py` (m5 hits the live DB
and cleans up; confirm `card_results` count unchanged) · `git diff --check` · `python scripts/write_build.py` · push ·
wait for Pages · check the live page.

## Order and time

A1 → A2 (anything inside Recall's 7-day window first) → A3 → A4 → B0 → B1 → B2 → C → D.
If time runs short, finish what you started and make it live. A half-built step stays on a branch, never on master.
Write the report in every case.
