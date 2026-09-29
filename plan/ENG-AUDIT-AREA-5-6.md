# Engineering audit 2026-09-29 - areas 5 (standing rules vs code) and 6 (AI steps)

Worker D, branch `eng-audit-d` (from `eng-audit-2026-09-29` @ 3c2835c). Nothing published. Medi's 8 decisions not re-asked.

**Scorecard**
- Area 5 rules vs code: ⚠ - 35 rules checked: 27 enforced in code, 26 tested, 21 fully obeyed by the live data. 9 conflicts need Medi. There is now a guard: `scripts/check_rules.py`, 20 checks.
- Area 6 AI steps: ⚠ - the run log and decisions log exist and work. Every paid call since 09-28 is logged (5/5), and so is every Claude review call (5/5). Claude is now pinned. Only 1 step, the grammar detector, has an accuracy measured against a human-labelled gold set.

**Terms**
- **BLOCK** = a rule the data obeys today. The guard fails if it breaks.
- **REPORT** = a rule the data does not obey yet. The guard counts and lists it on every run but never fails on it, because the fix waits on Medi or on a file this worker does not own.
- **Pinned** = the exact model is named in code, so a vendor default change cannot swap it silently.
- **Gold set** = a frozen answer key labelled by a person.

---

## 1. Rules table

Enforced: Y = code does it · P = partly · N = no code. Obeyed: checked against the live data on 2026-09-29.

| # | Rule (source) | Where enforced | Test | Obeyed | Examples / numbers |
|---|---|---|---|---|---|
| 1 | Her spelling source order: house → Doc Arabizi → Doc Arabic → stay Arabic (RULES S1) | `docs/js/word-bank-arabizi.js` create(); `scripts/house_spelling.py` | test_word_bank_arabizi.cjs; test_m10_whatsapp::test_house_spelling_* | ✅ | arabizi_gaps.cjs = 0 |
| 2 | Built spellings name their method and source (S1 amendment 09-23) | none before tonight → `check_rules.py` S1-extra | test_rules_check::test_s1_extra_* | ✅ | 1,598 rows. 16 `guess` rows have no source, which is allowed. Methods `her-list` (6) and `filler` (31) are in the file but not in RULES.md |
| 3 | Nothing Arabic-only on error cards (S1 09-26; anees-arabizi-guard) | `scripts/arabizi_gaps.cjs`; review_lesson step 6b | test_invariants::test_every_error_card_word_has_arabizi **skips when node is not on PATH, which is the case on this PC**; check_rules S1-guard finds node at C:/dev/tools | ✅ | 0 gaps |
| 4 | Her letters: 2 3 5 6 7 8 9, with ص = 9 (S1) | S1-extra checks the digits only | test_rules_check | ⚠ conflict | ص is written `s` in 77 of 81 built rows. Amal writes s 109/120 (memory 09-23). Question C4 |
| 5 | Medi never reviews spellings; spelling is not a focus (S1, memory) | process rule (agent behaviour) | - | ✅ as far as seen | no spelling queue for Medi in tutor.json |
| 6 | Raw transcripts are never edited (S2, E1) | hourly_lessons.transcribe_once reuses the file; overlays live in word-bank-review.json | test_invariants::test_pipeline_never_retranscribes…, …transcribe_once_reuses…; **check S2-raw** | ✅ | 16/16 provenance hashes and 3/3 gap-fill run hashes match. 17 files had no hash; a baseline was logged tonight, so 36/36 are covered |
| 7 | A slip needs Amal's signal (S3, M1) | reader briefs; full_audit_build; apply_amal_audit_rulings | **check S3-signal**; test_rules_amal_rulings | ✅ | 0 of 942 A rows lack a signal |
| 8 | Pronunciation is never a missed word (S4) | reader brief; word-bank rules | test_word_bank_reliability.cjs (kmy) | ❌ conflict | 09-19 8Ame2 is scored Wrong for pronunciation (SESSION-DECISIONS 09-21 says so). 3 scored audit rows say in their own note "may be only pronunciation": FA-d3f04bd5, FA-e6e6f5cb, FA-bc203430 |
| 9 | Pauses are not errors (S5, M7) | transcript display; buckets | test_transcript_display::…pauses…; **check S5-pause** | ✅ | 0 |
| 10 | One retrieval episode, one result (09-21) | speaking_evidence immediate_repeat; review_new_lessons.py; overlays | test_speaking_evidence::test_long_tutor_end…; test_word_bank.cjs | ❌ | 7 pairs where the later event's own note says "same episode / repetition" but both are scored: 09-15 wa7ad 27:33 + 27:38 (note: "count once"); 09-26 akId, badle, lama; 09-28 eben, wa7ad, zbUn. Plus 35 same-word pairs ≤10 s apart as clues |
| 11 | The 15-s rule is a clue: no score without a context read (memory 09-25). An immediate repeat of the supplied answer is excluded (09-21) | speaking_evidence 15-s rule; context review done by hand up to 09-23 | **check 15S-clue** | ❌ | 22 Partial scores (0.5 each) come straight from the machine flag on 09-26 (12) and 09-28 (10). Their note reads "repetition is practice, not independent credit", yet each still earns half credit |
| 12 | Grammar-only events are null for vocab (09-21) | word-bank-core.js | test_word_bank.cjs; test_context_review.cjs | ⚠ | 2 events are flagged grammar_only but a later review scored them Correct: 7afle 09-05, ana bakser 09-10. Both look like mixed incidents with a stale flag |
| 13 | Prepositions are grammar, not vocab (09-21) | word-bank context review | test_context_review.cjs | ✅ | fi/min/bi/ma3 scored 0 times |
| 14 | Only Medi's own speech counts (M11; anees-only-medi-words-count) | build_report.classify; speaking_evidence; word-bank-core | test_word_bank.cjs "Last said…"; **check M11** | ✅ | 0 of 1,053 scored uses fall on Amal's lines |
| 15 | Mastered cut-off | word-bank-core.js:60 (≥90% of last 10, ≥2 lessons, per 09-21) **and** buckets.js/py (5 successes on ≥3 dates, per N7) | test_word_bank.cjs; test_m5_cards | ❌ conflict | two definitions are live, so pages can disagree. Question C3 |
| 16 | Glue words are never graded (M3) | understand_lesson.GLUE_KEYS (old path only) | none | ❌ conflict | the Word Bank scores 158 glue-word uses (153 Correct): bas 45, u 30, aw 24, shu 21, lama 12. Question C2. ai_rules M3 status changed enforced → partly |
| 17 | No vocabulary list in the recognizer's ear (E3) | pipeline_ext.keyterms_for: names only | test_names::test_keyterms_are_names_only… | ✅ letter / ⚠ spirit | 1,000 name keyterms go on every track, including Medi's ("places"). Question C5 |
| 18 | Transcribe the whole track (E2) | hourly_lessons.transcribe_once | test_invariants two-track test | ✅ | only the gap filler sends windows, by design |
| 19 | Every reported miss carries audio (E5) | Lessons page plays from the card time | - | ⚠ | 30 of 858 cards have their own clip (area 9) |
| 20 | Never write Amal a lesson plan or send her grammar questions (M9; memory teacher-brain) | - | - | ⚠ conflict | the review list on tutor.html asks her about grammar patterns. Medi's 09-25 decisions and 09-29 decision 5 approve that list. Question C6 |
| 21 | "New" = only Amal's or Medi's mark (N1; anees-new-bucket-definition) | buckets.compute(confirmed_new); lessons.json new_words | test_medi_progress; **check NEW-amal-signal** | ✅ | new = ana babse6, banbese6 (both Medi's marks, 09-05) |
| 22 | New verbs = the pairs she taught, shown apart (memory 09-25/26) | `TAUGHT` constant in build_lessons_page_data.py | - | ✅ | `taught` never feeds the New bucket (cards-selection.js uses the bucket). It is a hard-coded per-lesson list (area 4) |
| 23 | The app never writes the Doc (N2) | no Docs API write anywhere in scripts/ | none | ✅ code / ⚠ agent | on 09-23 an agent typed 18 words into her Doc by hand. Question C7 |
| 24 | List membership by meaning; hand verdicts win (memory 09-27) | build_lessons_page_data applies sheet-verdicts.json | test_invariants::test_sheet_v1…, test_sheet_v2…; **check SHEET-meaning** | ❌ | 09-28 has 31 vocab rows and 0 by-meaning verdicts, because the hourly review has no sheet-reader step |
| 25 | A = scored, B = unscored until Amal rules; her yes scores, her reason becomes a rule (09-25 decisions) | apply_amal_audit_rulings.py | **test_rules_amal_rulings (new; the script had no test)** | ✅ | 0 rulings applied yet (Amal answered 0 of 68 patterns) |
| 26 | Amal's tap beats any machine label (A2) | apply_amal_audit_rulings.py | test_rules_amal_rulings::test_her_tap_beats… | ✅ | - |
| 27 | Code never contacts Amal (A1; PROMPT 09-29) | send_lesson_email.mjs hard-codes Medi | test_m8_pipeline::test_failure_email…; **check A1-medi-only** | ✅ | only one mail sender exists |
| 28 | At most 5 after-questions (A3) | after_from_audit.MAX_Q = 5 | none for the live path (test_m4_after covers only the dead after_questions.py) | ✅ | MAX_Q 5, MIN_Q 3 in code |
| 29 | Paid calls stop at 90% of the cap (H4) | pipeline_ext.budget_ok | test_m8::test_budget_guard…; **check H4-budget** | ✅ | ElevenLabs 3.39/10, OpenAI 2.21/10 |
| 30 | Amal's Tutor Hub page and "Amal's hub" buttons stay gone (Medi 09-28) | 17f2e97 | **check HUB-removed** | ✅ | go.html keeps a comment only |
| 31 | System Settings shows RULES.md (RULES header) | build_standing_rules.py | **check RULES-json-sync; test_live_rules_json_matches_rules_md** | ❌ → ✅ fixed | standing-rules.json was the 09-23 build and was missing the 09-26 S1 extension |
| 32 | Every AI call is logged (AI review #1) | track.py in review_lesson, pipeline_ext, fill_meet_gaps, score_grammar_detector, build_sentence_ladder, audit_vocab_unresolved | test_track; **check AI-logged, AI-paid-logged** | ✅ since 09-28 | 5/5 paid calls, 5/5 claude calls. The untracked manual or retired files are listed with reasons |
| 33 | The AI model is pinned (AI review #1) | track.CLAUDE_MODEL | test_track::test_claude_is_pinned_by_default | ❌ → ✅ fixed | request model was null in 5/5 lines; now claude-opus-5-5 |
| 34 | Arabizi big with Arabic small on Medi's pages; Amal's pages Arabic-first (09-25) | transcript-arabizi.js; arabizi_everywhere.py | - | not checked | area 9 |
| 35 | ykun/akun is a grammar slip (M6) | planned | - | n/a | still planned |

Counts: 35 rules · 27 enforced in code (Y) · 26 tested · **21 fully obeyed** (counting the 2 fixed tonight) · 9 not obeyed or in conflict (4, 8, 10, 11, 12, 15, 16, 20, 24) · 3 partly (17, 19, 23) · 2 not checked or n/a (34, 35).

## 2. Where a rule and the code disagree (not a question; listed)
- The `where` text in ai_rules.json was stale for E1/E2 (it named the retired lesson_pipeline), E3 ("no keyterms"; code sends names) and M3 (GLUE_KEYS; the Word Bank ignores it). Notes were appended tonight and the old text kept (commit e312ad9).
- Memory note anees-full-audit-decisions-2026-09-26 still sends B rows to "Amal's Tutor Hub page". That page was removed 09-28 and the list now lives on tutor.html (decision 5). The note is stale, not a conflict.
- test_invariants::test_speakers_not_swapped says "every lesson ≥ 92%", but 09-23 is at 91.5% (65/71). 09-28 has 0 matched rows, so the test cannot see a swap there. Medi's 09-28 track came back in Latin letters (language eng).
- test_invariants::test_ai_report_cards_match_the_audit_file runs 0 cases. The AI Reports cards say 961 rows, the audit has 1,074, and 961 falls outside the test's ±10% window. So the stale cards are no longer caught.
- apply_amal_audit_rulings.py still PATCHes `payload.applied` on Supabase. The AI review (#2) said to stop.
- Test side effects: a pytest run rewrites docs/data/build.json, docs/js/build.js and data/m4_stand_in_timing.json.

## 3. Conflicts between rules - questions for Medi (never picked a side)
- **C1** S4 says pronunciation never lowers a score. SESSION-DECISIONS 09-21 says a confirmed wrong pronunciation scores 0 (8amee2). Which wins? This affects 1 Word Bank row and 3 audit rows.
- **C2** M3 says glue words are never graded, but the Word Bank grades them: 158 uses, 153 Correct. Should bas/u/aw/shu/lama/iza count toward Words %?
- **C3** Mastered has two definitions: "≥90% of the last 10 over ≥2 lessons" (Word Bank, 09-21) and "5 successes on ≥3 dates" (Flashcards/buckets, N7). Should there be one definition?
- **C4** The RULES S1 chart says ص = 9, but Amal writes s (109/120). Change the chart to "ص = s (9 rare)"?
- **C5** Name keyterms (places) go on Medi's own track. The AI review warns this could hide his slips. Should they go on Amal's track only?
- **C6** M9 says never send Amal grammar questions, but the tutor.html review list does. Retire the M9 clause?
- **C7** N2 says the app never writes her Doc, yet an agent typed 18 words into it on 09-23. May an agent type into her Doc? Today's practice sends Not-on-sheet words to her review page instead.
- **C8** R17 (PROCESS-AUDIT 09-26): score a grammar-B row when she fixed the same bucket aloud in that lesson? This is still unanswered, along with R1-R18.
- **C9** The 15-s rule gives 0.5 to a repeat of her word, while 09-21 says an immediate supplied-answer repeat is excluded. Which is right? This affects 22 events.

## 4. AI steps

| Step | Model / pinned? | Logged in data/runs? | Gold set | Measured accuracy (source) |
|---|---|---|---|---|
| Transcribe | ElevenLabs `scribe_v2` alias, pinned by name in pipeline_ext.py:131 and fill_meet_gaps.py. There is no dated version and the response model is not captured | ✅ `scribe.transcribe` since 09-28 (5 lines). ⚠ output_refs is empty; the sha is only in the provenance.json | asr@v1 **to label** | WER/CER **not measured**. 15/20 blind preference, Amal 09-04 (data/aug25/check02_results_amal.json) |
| Speaker split | tracks = channel (Recall bot). Mixed lessons (08-25, 09-04, 09-18) use Scribe diarize plus pitch fallback | ❌ no step line | speaker@v1 **to label** | proxy only: audit-row placement agreement 91.5-100% per lesson (test_invariants _speaker_agreement, recomputed tonight); 09-28 not measured (0 rows). 09-18 was swapped once |
| Grammar detector | rule code (`audit_grammar_lessons.py`); version = detector sha in history | ✅ `grammar_detector.score` (eval). Reproduced tonight in a scratch dir | grammar@v1-heldout 29 (20 scored); v1-tuned 105 (79); v2-audit 1,018 (592, AI-labelled silver) | held-out recall **0.40**, precision 0.889. Tuned 0.759 / 0.859. v2-audit 0.203 / 0.842, bucket 0.517 (gold/history.jsonl; reproduced exactly 2026-09-29) |
| Word + grammar readers r1/r2 (one brief covers both) | `claude -p`. Was **unpinned** (request null), answered by claude-opus-5-5; **pinned tonight** | ✅ `full_audit.reader` (09-28: 2 lines, $1.42 + $1.40). 09-26 and earlier ran through the Agent tool and were not logged | reader@v1 **to label** | AI vs AI only: 61.5% Jaccard (PROCESS-AUDIT §4), 71.4% pairwise F1 (AI review). Human hand check 17/20 scored rows (memory note 09-26, no file) |
| Third reader | same | ✅ `full_audit.third_reader` | none | not measured (it dropped 186/644 disputes, PROCESS-AUDIT) |
| Sheet match | string match (lessons_page_node.cjs) plus a by-meaning agent read by hand | ❌ (manual agent) | sheet@v1 98, sheet@v2 273 | string "new" was right for 42/98 (56 were on the list). The by-meaning reader is not measured against Amal. **09-28 not read at all** |
| Arabizi gap filler | `claude -p`, now pinned | ✅ `arabizi.fill_gaps` | arabizi@v1 100 | 96/100, Claude-graded, not Amal (gold/README). Earlier sets 99/100 (09-23), 93 → 92 → 97 (09-25), from the arabizi-extra rule text |
| Pattern reader | `claude -p`, now pinned | ✅ `amal.patterns` | none | **not measured** (Amal has ruled on 0 of 68) |
| After-questions | none (after_from_audit.py picks the least-sure rows). The old OpenAI path has been dead since 09-11 | n/a | none | not measured |
| Meet/track gap filler | Scribe v2 | ✅ `meet_gap_fill` / `track_gap_fill` (3 lines, 1 error on 09-23) | none | alignment residual 0.073 s, diarization confidence 0.992 (09-26 run line). Word accuracy not measured |
| Homework grader (Supabase `grade`) | OpenAI `gpt-5.5` alias | ❌ Supabase `api_spend` only | 12 real pairs | 12/12 vs Amal's fixes (data/whatsapp/m10c_grader_check.json, OVERNIGHT-LOG) |
| Planner/homework suggestions | OpenAI `gpt-5.5` alias (suggest.py, homework.py) | ❌ budget.json ledger only; manual; last call 09-05 | none | validator: 0 untaught words. "Sounds like Amal" is pending |
| Vocab unresolved audit (09-28) | Claude session (model not recorded) | ✅ build line + 1,015 decisions (who = Claude audit) | none | not measured against a human |
| Lesson type, TAUGHT pairs | Claude read (hand) | ❌ | none | not measured |

**Run log** (`data/runs`, `scripts/track.py`) is built and works. The 09-28 lines cover 5/5 paid Scribe calls, matched by cost against data/budget.json, and 5/5 claude calls for the 09-28 review. The eval line was checked tonight in a scratch dir.

**Decisions log** (`data/decisions`, `scripts/pull_decisions.py`) is built and works: a dry run tonight fetched 145 rows, 0 new and 130 skipped (the flashcards source), and the file has 1,032 lines. Missing:
- Amal's verb-check answers (729 answered, only 41 in the app). Their tables are token-gated, and the anon key cannot read them.
- Her grammar-Doc edits.
- `payload.reason`.

Not built (roadmap items #4 and #5):
- GitHub Actions test floors (there is no .github folder).
- `build_ai_health.py` and the health panel.
- Gold sets asr, speaker, reader and gloss.
- `card_results` grades 1-4.

## 5. Fixes and commits (branch eng-audit-d)
| Commit | What | Old → new (why) |
|---|---|---|
| 467ba72 | `scripts/check_rules.py` (19 checks then); track pin; standing-rules.json rebuilt; tests | claude model null → claude-opus-5-5, which is what 5/5 runs already used, so behaviour is unchanged. standing-rules.json S1 text 09-23 → 09-26 (it was missing the extension) |
| 66ae0e5 | tests/test_rules_amal_rulings.py (A2 / 09-25 decisions) | the script had 0 tests; now 5 |
| 0bff511 | check AI-paid-logged | - |
| 3cea8ad | data/runs: `raw_transcript.baseline` for 17 unhashed raw transcripts | S2 coverage 19 → 36 files. The hash was taken tonight, not at engine time |
| e312ad9 | ai_rules.json notes (old text kept) | M3 status enforced → partly (158 glue uses are scored) |

Tests added: tests/test_rules_check.py (18 tests: a planted violation fails and its clean twin passes, for every BLOCK check; the live repo breaks no BLOCK rule; the first CLI line gives the reason), tests/test_rules_amal_rulings.py (5), tests/test_track.py::test_claude_is_pinned_by_default.
- Failed before the fix, pass after: test_claude_is_pinned_by_default, test_live_rules_json_matches_rules_md, test_live_repo_breaks_no_block_rule.
- Full suite: 373 passed, 8 failed. All 8 are pre-existing: m3 planner, m5 cards ×3, stale banner, vocab_audit ×3.

`check_rules.py` today: **OK - 14 pass, 6 open (report only), 0 skip.** The open ones: S4-pron 4, EP-one-episode 7, GO-grammar-null 2, 15S-clue 22, M3-glue 158, SHEET-meaning 1.

## 6. Decisions (one line each)
**Medi**
- Keep `claude -p` pinned to claude-opus-5-5? yes/no
- C1 S4 wins over "8amee2 = 0"? yes/no
- C2 Glue words stay unscored (drop the 158)? yes/no
- C3 One Mastered definition = the Word Bank's (≥90% of last 10, ≥2 lessons)? yes/no
- C4 RULES S1 chart: ص = s? yes/no
- C5 Name keyterms on Amal's track only? yes/no
- C6 Retire M9's "never send her grammar questions"? yes/no
- C7 Agents may type into Amal's Doc? yes/no
- C8 (R17) Score grammar-B rows she fixed aloud in the same lesson? yes/no
- C9 A repeat of her word within 15 s scores nothing (not 0.5)? yes/no
- Wire check_rules.py (BLOCK level) into the hourly publish guard? yes/no

**Amal**
- Do you write ص as s (not 9)? yes/no
- Is a wrong vowel like 8amee2 for 8aame2 only pronunciation (not a wrong word)? yes/no

## 7. Not done
- No context read of the 7 episode pairs, the 22 15-s partials or the 2 grammar-only flags. Those are word-bank-review.json patches (another owner).
- No sheet verdicts for 09-28. data/lesson-work is not this worker's.
- Rule 34 (Arabizi big / Arabic small) and rule 19 (clips) were not checked (areas 9 and 3).
- No WER/CER, speaker or reader gold set was labelled; each needs a human.
- No health panel and no GitHub Actions.
- The Codex re-judge path (decision 5) is not in code, so it is not logged by track.

## 7b. Hand check of 5 random findings (seed 20260929, from 20 findings)
- #5 episode doubles: **held**. I re-read all 7. wa7ad 09-15 carries the note "count once" and is still scored twice. akId, badle and eben are clear repeats.
- #10 vacuous AI-report test: **held**. Cards say 961, the audit has 1,074, and the test runs 0 cases.
- #13 speaker test blind on 09-28, 09-23 at 91.5%: **held**. Recomputed with the test's own function.
- #15 raw-transcript hashes: **partly held**. 16/16 match, but the count of unhashed files was **17, not 13**. My first count went per folder; 09-15 has one hashed segment and 3 unhashed files. Corrected, then fixed (3cea8ad).
- #17 A1 (only Medi is emailed): **held**.
- Result: **4 of 5 held**, 1 corrected.

## 8. Changes the coordinator must make (files this worker does not own)
1. **Publish guard** (hourly_lessons.py, before every push):
   - Run `python scripts/check_rules.py`.
   - On exit 1, do not push and keep the last good version live.
   - Write the first stdout line to the hourly log and to System Settings.
2. **scripts/review_lesson.py**
   - Line 57 docstring: "unset = the CLI default" → "unset = track.DEFAULT_CLAUDE_MODEL (claude-opus-5-5); ANEES_CLAUDE_MODEL=cli-default unpins".
   - Add a sheet-reader step (by meaning → data/lesson-work/sheet-verdicts.json) for each new lesson. This fixes SHEET-meaning.
   - Add a Word Bank context-read step for 15-s flags and same-episode pairs (writes word-bank-review.json patches). This fixes 15S-clue and EP-one-episode.
3. **scripts/hourly_lessons.py transcribe_once / pipeline_ext.transcribe_with_retry**:
   - Put the written scribe json in the run line's `output_refs` (path + sha256).
   - Set `gen_ai.response.model` to the model the response reports, falling back to the requested `scribe_v2`.
4. **tests/test_invariants.py**
   - test_every_error_card_word_has_arabizi: fall back to `C:/dev/tools/node-v24.18.0-win-x64/node.exe` (or reuse `check_rules.node_bin`) instead of skipping.
   - test_ai_report_cards_match_the_audit_file: fail when 0 cards are found, or match "961" explicitly. The stale cards are otherwise invisible.
   - test_speakers_not_swapped: fail when a lesson that has audit rows matches fewer than 10 of them (09-28 matches 0). Fix the "≥ 92%" docstring (09-23 = 91.5%).
5. **scripts/apply_amal_audit_rulings.py**: stop PATCHing `payload.applied` (AI review #2). Idempotency already lives in the audit JSON's `amal_ruling`.
6. **Word bank owner**:
   - Patch the 7 episode pairs and the 22 machine-only partials after a context read.
   - Clear or honour the 2 stale grammar_only flags.
   - Pending Medi's answers on C1, C2, C3, C9.
7. **Test side effects**: make the tests that rewrite docs/data/build.json, docs/js/build.js and data/m4_stand_in_timing.json write to tmp instead.
