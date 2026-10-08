# Re-judge all 18 lessons on the re-heard transcript - runbook (2026-10-04)

Worktree `C:\dev\anees-wt-bench`, branch `engine-bench`. Every command from the repo root with `PYTHONIOENCODING=utf-8`.
Nothing here commits, pushes, calls a paid AI or writes to Supabase. Tool: `scripts/rehear_rejudge.py`
(tests: `tests/test_rehear_rejudge.py`). Background: `plan/BACKFILL-INVENTORY-2026-10-04.md` sections 0, 3, 4.

Tags: [L] local, [N] needs a Supabase READ, [A] a Claude agent writes one file, [ME] the coordinator's own step.

## What changed in the code

| File | Change |
|---|---|
| `scripts/full_audit_build.py` | `build()` split into `gather()` (all rows, all rulings, nothing written when `write_report=False`) + the rest. `assign_uids(rows, carry)` gives a row named in `full-audit/uid-carry.json` its OLD uid (`uid_carried_from` = the hash it would have had). Rows in `full-audit/preserved-rows.json` are merged in under their old uid, marked `kept`. Medi's corrections find a carried row by its old uid. No carry file and no preserved file = byte-identical uids to before (checked: 1,161 of 1,161). |
| `scripts/full_audit_compare.py` | `hand_self_fix()`: a `self-fix-rulings.json` ruling follows its MOMENT (his_t / her_t within 10 s of the dispute row) when the dispute number moved or its pass was retired; a ruling whose number still fits applies to that dispute only. |
| `scripts/rehear_rejudge.py` | new: `snapshot`, `retire-pass2`, `prompts`, `accept`, `carry`, `kept`, `preflight`, `hold`, `report`, `amal-diff`. |
| `scripts/amal_hold.py` | new: reads `full-audit/hold-from-amal.json`. No file = nothing is blocked. |
| `scripts/build_amal_review.py`, `scripts/codex_rejudge.py` (`amal_list`), `scripts/build_lessons_page_data.py` (Amal's ledger cards) | skip a held row, and (for the re-read lessons) anything that was not on her list before. With no hold file the output is unchanged. |
| `scripts/publish_guard_config.json` | `tests/test_rehear_rejudge.py` added to `tests_py`. |

## Order (one deviation from the brief: `kept` runs BEFORE `full_audit_build`, because the build is what keeps the rows)

### Stage 0 - before anything is re-read
1. [L] `python scripts/rehear_rejudge.py snapshot`
   Writes `data/lesson-work/rehear/rejudge/before.json` (every audit row with its uid, state, Amal ruling, his line's
   text, every reference to it, the page numbers per lesson, sha of every reader file). Refuses to overwrite.
   It also pins a `legacy` manifest (`<date>.r?.json.inputs.json`) for the reader files that have none, recording the
   `.txt` they read - step 4 overwrites that `.txt`, and without the manifest the freshness evidence is gone.
   Take it while `data/full-audit-2026-09-26.json` still carries Amal's rulings (it does now: 117 rows + 42 Tutor checks
   = 138 rows with her word). If a build ran without `apply_amal_audit_rulings.py` after it, run that first.
   Known before tonight: 91 references already point at no row (`already_orphaned` in the snapshot); they are not
   counted as tonight's orphans.
2. [L] `python scripts/rehear_rejudge.py retire-pass2` (lists 91 files) then `... retire-pass2 --apply`
   Moves `<date>.p2.*` and `<date>.passes.json` of the 13 older lessons to `full-audit/superseded-2026-10-04/`. See
   "Pass 2" below.

### Stage A - text ([ME]: your steps, listed for order only)
3. [ME] apply the `gemini-rehear` overlay rows; `python scripts/detect_grammar_usage.py`;
   [N] `python scripts/build_lessons_page_data.py` (reads `amal_rules kind=new`; offline it silently falls back to the
   09-25 list - do not run it offline). It stops on an overlay row that matches no line.
4. [L] `python scripts/full_audit_prep.py` (all 18 `<date>.txt`, `amal-sheet.txt`, `buckets.md`).
5. [L] per date: `python scripts/echo_candidates.py <date>` - BEFORE the readers (the brief sends them to that file).

### Stage B - readers, per lesson
6. [L] `python scripts/rehear_rejudge.py prompts <date>` -> `rehear/rejudge/prompts/<date>.r1.txt`, `.r2.txt`, `.r3.txt`
   (= `review_lesson.reader_prompt` / `third_prompt` with absolute paths + "write only this one file").
   The r1 / r2 prompts are final now; the r3 prompt text does not depend on the disputes, so it can be made here too.
7. [A] two separate agents: one gets `<date>.r1.txt`, one gets `<date>.r2.txt`. Each writes only
   `full-audit/<date>.r1.json` / `.r2.json`. They must not see each other's file.
8. [L] `python scripts/rehear_rejudge.py accept <date> r1` and `... accept <date> r2`
   Exit 0 = valid shape, manifest pinned exactly as `review_lesson.py` pins it, `cache_decision` = fresh,
   `readers_read_current(<date>)` = None. Exit 1 = not accepted (file missing / cut off / wrong reader / still the
   pre-re-read bytes / `.txt` is not what the pages show). Nothing is renamed or deleted.
9. [L] `python scripts/full_audit_compare.py compare <date>`
10. [A] one agent gets `<date>.r3.txt`, writes only `full-audit/<date>.r3.json`.
11. [L] `python scripts/rehear_rejudge.py accept <date> r3` (refuses when compare.json is older than r1 / r2, or when a
    ruling names a dispute that does not exist; warns on a dispute without a ruling).
12. [L] `python scripts/full_audit_compare.py settle <date>`

### Stage C - keep everything attached (all lessons at once, after every lesson is settled; safe to re-run)
13. [L] `python scripts/rehear_rejudge.py carry` -> `full-audit/uid-carry.json`
    Old row -> new row, in this order: exact uid; same 09-24 sweep row; same moment (5 s) + same wrong / right piece +
    same kind class (closest wins); same wrong piece + class within 30 s, one candidate each side; same moment + same
    class, one candidate each side. A vocab <-> grammar flip is NOT carried (the uid means the class).
14. [L] `python scripts/rehear_rejudge.py kept` -> `full-audit/preserved-rows.json` (build input) +
    `rehear/rejudge/kept-rows.json` (the list): `kept_confirmed` (Amal confirmed, no new row: the old row stays, marked
    `kept`), `listed_rejected` (she rejected it, no new row: nothing to reject), `listed_human_ruling` (a hand ruling
    pointed at a row that is gone), `line_changed` (ruled row carried, his line's text changed: old and new line).
15. [L] `python scripts/rehear_rejudge.py preflight` -> `rehear/rejudge/preflight.json`; exit 1 when something must be
    fixed first. It runs the build in memory (writes nothing) and lists: rulings that WOULD STOP THE BUILD
    (`proposed-buckets.json` row with no audit row; `duplicates.json` keep gone, drop present), rulings TO DECIDE
    (`rejected.json` / `signal-rulings.json` whose row is still there under another wording - add a row to the file with
    the printed new t / wrong, keep the old row), self-fix rulings and which dispute each now lands on, Medi corrections
    orphaned, uid references orphaned tonight, Amal-confirmed rows with no row (= run `kept`), stale carry entries
    (= re-run `carry`), pass-2 files still in place, lessons whose readers are not on the current text.
    Fix data, re-run 13-15 until it exits 0.
15b. [L] `python scripts/rehear_rejudge.py hold` -> `full-audit/hold-from-amal.json` - BEFORE the build, so no builder
    ever writes a new question. Held = every row the build would write whose uid is not in `before.json` (carried and
    kept rows are not held). The file also records what was on her lists on `origin/master` (review rows, sheet-word
    cards, check moments, ledger cards) and the 18 re-read dates: while the file exists, for those lessons her lists
    show only what they showed before - so a carried row that turned A -> B, or was re-worded into a new sheet-word
    card, is not asked either. A held row counts on Medi's pages exactly as the build decides. Re-run after any new
    settle / carry. Release = Medi's OK = delete the file and rebuild.
16. [L] `python scripts/full_audit_build.py`
17. [N] `python scripts/apply_amal_audit_rulings.py` - mandatory right after 16 (the build wipes her rulings; this reads
    `amal_rules` and puts them back by uid; writes nothing to Supabase). It also runs `build_amal_review.py`,
    `build_lessons_page_data.py`, `build_grammar_console.py`, `build_amal_grammar_rules.py`, `codex_rejudge.py --list`.
18. [L] `python scripts/rehear_rejudge.py report` -> `rehear/rejudge/report.md` + `report.json`: per lesson rows before
    -> after, scored before -> after, same uid, moved, added, removed, kept, Amal-ruled rows (on a row / kept / no row /
    ruling not back), verification records and patterns orphaned, Words % and Grammar % before -> after.
    `kept` may be re-run here to refresh the list; it gives the same result.
19. [L/N] the builders, inventory section 2b steps 13-22 (`amal_grammar_notes.py`, `build_lessons_page_data.py`,
    `build_grammar_console.py`, `build_amal_grammar_rules.py`, `build_amal_review.py`, `arabizi_everywhere.py`,
    `arabizi_gaps.cjs`, `source_audit.py`, `accuracy_gates.py annotate`, `codex_rejudge.py --list`,
    `build_sentence_ladder.py`, `amal_new_words.py`, `medi_corrections.py propose`, `build_rule_book.py`,
    `write_build.py`), then the proofs (steps 23-27).
20. [L] `python scripts/rehear_rejudge.py amal-diff` - ~~must print `ADDED for Amal 0` (exit 0) before any push~~ **a report, not a
    gate (owner's override, below).**

    > **Owner's override of step 20 - Medi, 2026-10-04:** "put anything that needs to be checked in the tutor portal, i will
    > have her check". So items ADDED for Amal are expected after the re-read (142 added / 128 removed in
    > `rehear/rejudge/amal-diff.json` of 2026-10-05): every check that needs a person goes to Amal's Tutor portal, or to a
    > listen page for Medi. Keep running the command and read its list before a push - it shows what her portal gains and
    > loses - but its exit code no longer blocks one. Recorded 2026-10-05 (council final approval, condition 4). Nothing
    > here sends Amal anything: Medi sends her links (AGENTS.md rule 6).
    >
    > The same decision retires step 15b: **do not run `hold`** on a rebuild. `full-audit/hold-from-amal.json` must not
    > exist (commit 9662fa7: "no hold, by Medi's decision"); if it does, delete it and re-run `build_amal_review.py`,
    > `build_lessons_page_data.py`, `codex_rejudge.py --list` before anything is committed - with the file in place her
    > lists are frozen to what they showed before the re-read.

    What the command does (unchanged):
    Compares `docs/data/amal-review.json`, `amal-verify.json`, `amal-ledger.json`, `amal-new-words.json`, `tutor.json`
    and `docs/amal/*.html` with `origin/master`. ADDED (new pattern, new row in a pattern, new sheet-word card or
    moment, new check moment, new ledger card, new open new-word, new open link) = exit 1. Removed items (their row is
    gone or no longer asked) are listed, not an error. A changed `docs/amal/*.html` is listed for reading. Also written
    to `rehear/rejudge/amal-diff.json`. `report` separately warns when a created row is missing from the hold file.

## Pass 2 (decision)

The 13 lessons 08-25 .. 09-23 have a second reader pass that read the text of 2026-09-26. Today
`full_audit_compare.union_rows` adds its rows to the audit and `accuracy_gates` compares it with pass 1.
Decision: moved, not deleted, to `full-audit/superseded-2026-10-04/` (`retire-pass2 --apply`, with a README.json).
No code path needed changing: with the files gone `union_rows`, `full_audit_build.pass_log` and
`accuracy_gates.pass_numbers` see one pass.
- No "verified" mark is lost: all 18 lessons are "not verified" today (agreement 48-81 % within a pass, 52-80 %
  between passes; 95 % needed). The reason text changes from two pass numbers to
  "pass 1 n %; 2 consecutive passes at >= 95 % are needed". No lesson can become verified on one pass.
- Rows only pass 2 had leave the audit unless the new readers write them. Each shows as `removed` in the report; any
  that Amal confirmed is kept by step 14.
- The row check "found in pass n only" goes away (there is one pass); "decided by the third reader alone" stays.
- Two `self-fix-rulings.json` rows are keyed to pass 2 (09-16 D4, 09-21 D39): `settle` now applies them to the pass-1
  dispute at the same moment, if the re-read has one; `preflight` says which.
- A real second pass on the new text would be 36 more reader runs + 18 third readers, written to `<date>.p2.*`.

## Caveats

- **No new question for Amal** is enforced by the hold (step 15b) and proven by `amal-diff` (step 20). Not gated by
  the hold, only caught by `amal-diff`: `docs/data/amal-new-words.json` (built from Amal's own lines, lessons >= 10-01;
  it moves only if her lines change), Medi's "my Arabic was right" cards in `amal-ledger.json` (they come from his own
  corrections), `docs/data/tutor.json` (built from Supabase link rows by `build_tutor_data.py`, [N]; its review total
  follows `amal-review.json`), and `docs/amal/grammar-rules.html` (status and % per rule: numbers, not questions - they
  WILL change with the re-read and show as a changed page). Never run `after_from_audit.py`, `amal_review_link.py`,
  `review_lesson.py`, `hourly_lessons.py`, `codex_rejudge.py` without `--list`.
- **The hold file must not outlive the decision.** For the 18 re-read lessons it freezes her lists to what they showed
  before; lessons taught later are not affected. A held B row is still unscored and simply waits.
- **Her ruling can fail to land on a carried row**: a row she said "do not correct" that the readers now file as an A
  slip (she voiced a fix on the new text), or a row a rule now rejects. `apply_amal_audit_rulings.py` only flips B rows.
  The report lists each under "ruling not back"; it is not forced.
- **A carried uid is the old slip by moment, not by wording** (owner's decision). `uid-carry.json` holds the old and
  new t / wrong for every carried row, and the report's `moved_rows` lists them; read the `moment` ones.
- **A vocab <-> grammar flip is a new uid.** Its verification record or pattern shows under orphaned in the report.
- `rejected.json`, `signal-rulings.json`, `proposed-buckets.json` still match by moment + wrong piece. They are not
  re-pointed automatically: a different wording at the same moment may be a different slip, so a person decides
  (preflight prints the candidate).
- `uid-carry.json` and `preserved-rows.json` are derived from the settled files: after ANY new settle, re-run 13-15.
  A stale carry entry is ignored by the build (the row gets its own hash) and reported by preflight.
- `full_audit_prep.py` writes `.txt` in text mode (CRLF here); `readers_read_current` accepts both hashes.
- Lesson type files: 10 lessons have none and use the hand dicts; the 8 that exist were read on the old text
  (off-lesson windows are times, so they hold). Nothing here re-reads them. `review_lesson.py` would call `claude -p`
  for a missing one - another reason not to run it.
- `accept` pins the manifest with the ORIGINAL `review_lesson` prompt hash, so a later `review_lesson.py` run sees the
  file as fresh and does not pay for a re-read. The manifest says `written_by: a Claude agent ...`.
- GR-24 in `settle` reads raw Scribe word times from `C:\dev\anees\data\lessons` (read-only) and
  `docs/data/lessons/<date>.json`; the word-time check is on the engine's words, not the re-heard text.
- Old clip files (`clips/gc-*.mp3`) of moved rows stay behind unreferenced.
- The 09-24 sweep rows (115 kept today) come back by themselves each build; one the new readers now find is merged into
  the reader row and keeps the old uid through the `sweep` step of the carry.
