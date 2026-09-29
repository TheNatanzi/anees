# Engineering audit 2026-09-29 · Area 3 (source audio + transcripts) · accuracy gates (09-27 items 1-8) · decision 5 (Codex second judge)

Worker B, branch `eng-audit-b` (from `eng-audit-2026-09-29` @ 8328f80). Nothing published, nothing sent to anyone.
This file is also the 09-27 deliverable (plan/PROMPT-SYSTEMIC-ACCURACY-AUDIT-2026-09-27.md).

## Scorecard
- Area 3 (source audio + transcripts): ⚠ every lesson audited from the raw recordings; 3 untranscribed stretches found (09-28 Medi 00:42-06:42 new, 09-16 Medi 26:49-28:13, 09-26 Amal 00:04-01:06); 09-23 Medi hole confirmed FIXED by the gap filler; no swapped speakers; nobody has listened (ASR never human-reviewed)
- Accuracy gates (09-27 items 1-8): ⚠ all 8 items built + 41 offline tests; `check` passes on this branch and fails closed; 0 of 15 lessons verified (reader agreement 48-81 %, no human ASR review) - honest, not a bug
- Decision 5 (Codex re-judges uncertain rows, disagreements to Amal on the Tutor page): ✅ Codex gpt-5.5 re-judged 213 of 213 rows on independent ASR of the raw clips: 173 agree (161 confirmed + 12 changed), 40 disagree (38 rejected + 2 unsure) -> 40 rows on the Tutor page for Amal; $0 API spend

## Ranked failures (reproduced)
1. **`accuracy_gates.py check` failed on 11 of 15 lessons for a wrong reason** (would have blocked every hourly publish once
   the guard is wired). Root cause: it compared `grammar.mistakes` with the count of audit rows, but Amal's grammar-rule
   notes (merged 2026-09-29) set 1-5 rows per lesson apart as `grammar_not_counted` (e.g. 09-04 بتحمس → متحمس "not taught
   yet"). Fix: reconcile by uid — every speaking grammar row of the audit is on the page exactly once (counted card or
   set-apart card). Now also catches a row that is missing, extra or shown twice.
2. **09-28: Medi's first 6 minutes were never transcribed** (new, not in the known list). Raw: his first Recall track
   (0:00-6:43, `Medi_Natanzi-13029…mp3`) holds 174 s of speech 00:42-06:42; the transcript starts at 07:30. Hand check:
   dialect whisper on 01:00-02:00 hears him ("شو رأيك؟ … What do you mean?"). Same failure as 09-23 before the gap filler.
3. **Nothing re-checked uncertain rows against audio.** 213 scored rows (166 grammar, 47 words) needed a check; the only
   "check" was a third Claude reading the same transcript. Fixed with the Codex second judge (below).
4. **A single "rejected" in the ledger dropped a row, whoever wrote it** — one AI could silently delete a scored mistake.
   Now: a human (Amal/Medi) settles; the second judge alone can only confirm; its "rejected/unsure" keeps the row pending
   for Amal. A Claude model can never be recorded as the second judge (check fails).
5. **The release layer could go stale silently**: `check` never recomputed it, so after a new ledger record or audit
   the pages could show an old status. Now `check` recomputes and fails with "stale (run annotate)".
6. **`check` did not fail closed on its own crash** and printed no single reason line. Now any exception = exit 1, and
   the last line is always one plain sentence for the hourly log / System Settings.
7. **The third reader never saw the agreed rows** (item 3): two readers of one transcript can share a mistake. Now the
   disputes file lists agreed rows A1..An; the third reader can challenge one; a challenged row needs an audio/human check.
8. **Untranscribed stretches the transcript can't reveal**: 09-16 Medi 26:49-28:13 (24 s; hand check: "لازم بتمرن … لما
   عندي وقت" — real learner Arabic) and 09-26 Amal 00:04-01:06 (21 s on her "silent" track; hand check: "كيف صارت …").
   Rows there are now unscoreable.
9. **Estimated timings (09-10) and the Word Bank's headline were not flagged**: 09-10 now carries the reason; the Word
   Bank block (eligible / excluded / pending / lessons left out) is in `accuracy-release.json` totals.
10. **Tutor page said 41 verb answers pulled** (hand-kept number; 729 are pulled on eng-audit-e). Now computed.

## Items 1-8 (09-27 prompt): root cause → fix → test
| # | Item | Root cause | Fix (this branch) | Tests |
|---|---|---|---|---|
| 1 | 95 % release threshold | review_lesson.py builds and shows scores regardless | `release_decision`: two latest consecutive passes each ≥ 95 % AND ≥ 95 % with each other; policy < 95 blocks `check`. Scores stay shown with ≈ (decision 4), never "verified" | test_release_decision (real 08-25 numbers), test_lowered_threshold_blocks_publishing, test_policy_threshold |
| 2 | Source coverage | coverage was inferred from the transcript only (a hole is invisible when nobody talks back) | `scripts/source_audit.py` reads the RAW tracks: audio present, speech on each person's own track, untranscribed speech, lost segments, independent speaker-label check; flags → reasons + unscoreable intervals | test_untranscribed_speech_makes_rows_unscoreable (09-28), test_missing_source_audit…, test_segments_lost_and_recovered (09-16), test_holes…, test_caption_speaker_in_parentheses (09-18) |
| 3 | Adjudication / independent checks | r3 saw disputes only; checks were Claude-on-transcript | r3 sees agreed rows + `challenges`; uncertain rows re-judged by Codex gpt-5.5 on independent ASR of the raw clip; disagreements to Amal | test_third_reader_sees_agreed_rows…, test_codex_*, test_amal_settles_a_disagreement |
| 4 | Fail closed / cache invalidation | review_lesson.py reuses reader files by existence, ignores builder exit codes | `cache_state` / `write_manifest` (hash manifests) exist and are tested; **review_lesson.py must call them — not my file (see coordinator list)** | test_cache_state |
| 5 | Test gate before publishing | only Pages deploy | `accuracy_gates.py check`: schema, coverage, agreement, invariants, reconciliation (Lessons = detail = Word Bank = audit = Grammar console), stale layer, ledger rules; exit 0/1 + one-line reason | test_grammar_cards_set_apart…, test_stale_release_layer…, test_check_fails_closed…, test_check_last_line… |
| 6 | Integrity vs adjudication | Word Bank passes re-recorded outcomes | append-only ledger: uid, method, reviewer, role, verdict, confidence, evidence (window, clip hashes, independent ASR, quote), at; latest human wins; revision history | test_ledger_rejects_a_claude_second_judge…, test_ledger_revision_history… |
| 7 | Grammar denominator | Latin-script turns skipped by the usage counter | `grammar_denominator` invalidates; verified grammar % only with a valid denominator (0 of 15 lessons today) | test_grammar_denominator_* (09-04 "M-mitruj?") |
| 8 | Eligible / excluded / pending beside headlines | not shown | per lesson in lessons.json words/grammar, totals + Word Bank block in accuracy-release.json; `check` blocks a Word Bank audit that leaves out a lesson (09-14 and 09-18 are now IN: 150 + 49 events) | test_word_bank_headline…, test_release_totals… |

### Area 3 table

| Lesson | Recording | Medi audio | Medi speech transcribed | Amal audio | Amal speech transcribed | Labels check | Timing | ASR reviewed | Holes / flags |
|---|---|---|---|---|---|---|---|---|---|
| 2026-08-25 | one mixed recording | n/a (mixed) | n/a (mixed) | n/a (mixed) | n/a (mixed) | 90.4% of 612 (voice pitch per line) | engine | no human; 2nd model 0 s (Word Bank) + 8 Codex clips | none |
| 2026-09-04 | one mixed recording | n/a (mixed) | n/a (mixed) | n/a (mixed) | n/a (mixed) | 86.7% of 875 (voice pitch per line) | engine | no human; 2nd model 0 s (Word Bank) + 18 Codex clips | speaker labels agree with an independent check on only 86.7 % of 875 lines (voice pitch per line (Medi < 155 Hz, Amal > 180 Hz) vs the engine's diarization labels) |
| 2026-09-05 | one mixed recording | 100.0% | n/a (mixed) | 99.4% | n/a (mixed) | 89.8% of 659 (own-track loudness) | engine | no human; 2nd model 241 s (Word Bank) + 13 Codex clips | speaker labels agree with an independent check on only 89.8 % of 659 lines (own-track loudness (each labelled line: is the labelled person's own track >= 6 dB louder?)) |
| 2026-09-10 | per-person tracks | 100.0% | 96.2% | 100.0% | 92.5% | 94.7% of 862 (own-track loudness) | estimated | no human; 2nd model 519 s (Word Bank) + 14 Codex clips | none |
| 2026-09-11 | per-person tracks | 100.0% | 94.8% | 100.0% | 98.5% | 91.4% of 810 (own-track loudness) | engine | no human; 2nd model 0 s (Word Bank) + 8 Codex clips | none |
| 2026-09-14 | per-person tracks | 97.4% | 97.6% | 99.9% | 99.0% | 94.2% of 889 (own-track loudness); captions 59.7% | engine | no human; 2nd model 0 s (Word Bank) + 14 Codex clips | none |
| 2026-09-15 | per-person tracks | 100.0% | 97.3% | 99.1% | 98.5% | 93.9% of 899 (own-track loudness) | engine | no human; 2nd model 0 s (Word Bank) + 20 Codex clips | none |
| 2026-09-16 | per-person tracks | 99.1% | 92.8% | 98.4% | 96.6% | 95.9% of 861 (own-track loudness); captions 68.0% | engine | no human; 2nd model 0 s (Word Bank) + 23 Codex clips | Medi talks 26:49-28:13 (24 s of speech on their own track) with no transcript line |
| 2026-09-17 | per-person tracks | 98.6% | 97.2% | 99.3% | 98.7% | 94.9% of 844 (own-track loudness) | engine | no human; 2nd model 0 s (Word Bank) + 14 Codex clips | none |
| 2026-09-18 | one mixed recording | n/a (mixed) | n/a (mixed) | n/a (mixed) | n/a (mixed) | 69.3% of 880 (Meet caption track) | engine | no human; 2nd model 0 s (Word Bank) + 26 Codex clips | none |
| 2026-09-19 | per-person tracks | 100.0% | 91.8% | 100.0% | 98.2% | 94.1% of 762 (own-track loudness); captions 67.0% | engine | no human; 2nd model 0 s (Word Bank) + 1 Codex clips | none |
| 2026-09-21 | per-person tracks | 100.0% | 99.1% | 99.8% | 98.9% | 94.0% of 1109 (own-track loudness); captions 68.4% | engine | no human; 2nd model 0 s (Word Bank) + 28 Codex clips | none |
| 2026-09-23 | per-person tracks | 98.3% | 95.8% | 98.6% | 98.2% | 94.8% of 904 (own-track loudness) | engine | no human; 2nd model 0 s (Word Bank) + 7 Codex clips | none |
| 2026-09-26 | per-person tracks | 100.0% | 97.4% | 97.5% | 96.5% | 94.7% of 1059 (own-track loudness) | engine | no human; 2nd model 0 s (Word Bank) + 8 Codex clips | Amal talks 00:04-01:06 (21 s of speech on their own track) with no transcript line; Amal 00:00-20:17 comes from the mixed Meet recording, speakers split by diarization (their own track is silent there) |
| 2026-09-28 | per-person tracks | 98.9% | 84.4% | 99.7% | 98.1% | 90.9% of 864 (own-track loudness); captions 62.6% | engine | no human; 2nd model 0 s (Word Bank) + 11 Codex clips | Medi talks 00:42-06:42 (174 s of speech on their own track) with no transcript line |

### Before / after (before = 3c2835c release layer, after = this branch)

| Lesson | Release | Reader agreement p1 / p2 / between (>= 95 needed) | Medi covered % | Amal covered % | Words eligible / excluded / pending | Grammar eligible / excluded / pending | Reasons |
|---|---|---|---|---|---|---|---|
| 2026-08-25 | not verified | 61.8 / 80.9 / 78.9 | 100.0 | 100.0 | 96/0/4 → **96/0/0** | 28/0/4 → **28/0/0** | 6 → 5 |
| 2026-09-04 | not verified | 63.2 / 48.5 / 74.6 | 100.0 | 100.0 | 23/0/0 | 42/0/18 → **42/0/1** | 6 → 7 |
| 2026-09-05 | not verified | 64.6 / 61.5 / 80.0 | 100.0 | 100.0 | 46/0/3 → **46/0/1** | 36/0/10 → **36/0/4** | 6 → 7 |
| 2026-09-10 | not verified | 61.8 / 66.2 / 77.9 | 100.0 | 100.0 | 115/0/1 | 35/0/13 → **35/0/1** | 5 → 6 |
| 2026-09-11 | not verified | 58.5 / 55.0 / 67.8 | 100.0 | 100.0 | 71/0/0 | 27/7/8 → **27/7/2** | 7 → 7 |
| 2026-09-14 | not verified | 69.7 / 61.9 / 77.3 | 100.0 | 100.0 | 85/0/2 → **85/0/1** | 47/0/12 → **47/0/4** | 5 → 5 |
| 2026-09-15 | not verified | 57.9 / 54.8 / 76.7 | 100.0 | 100.0 | 57/0/4 → **57/0/0** | 49/0/16 → **49/0/4** | 5 → 5 |
| 2026-09-16 | not verified | 50.0 / 63.3 / 79.6 | 100.0 → **98.0** | 100.0 | 45/2/1 → **45/2/0** | 48/9/22 → **48/9/3** | 6 → 7 |
| 2026-09-17 | not verified | 72.4 / 62.1 / 69.2 | 100.0 | 100.0 | 62/1/4 → **62/1/1** | 36/5/10 → **36/5/1** | 6 → 6 |
| 2026-09-18 | not verified | 58.7 / 70.5 / 80.0 | 100.0 | 100.0 | 12/0/4 → **12/0/0** | 45/0/22 → **45/0/4** | 6 → 6 |
| 2026-09-19 | not verified | 58.3 / 70.0 / 76.9 | 100.0 | 100.0 | 35/0/1 → **35/0/0** | 4/0/0 | 7 → 6 |
| 2026-09-21 | not verified | 58.7 / 50.0 / 75.8 | 100.0 | 100.0 | 204/0/6 → **204/0/3** | 68/0/22 → **68/0/6** | 5 → 5 |
| 2026-09-23 | not verified | 64.3 / 68.7 / 79.7 | 100.0 | 100.0 | 79/20/3 → **79/20/1** | 22/9/4 → **22/9/0** | 6 → 6 |
| 2026-09-26 | not verified | 62.1 /  | 100.0 | 96.0 → **94.5** | 129/0/7 → **128/1/2** | 21/0/1 → **21/0/0** | 4 → 6 |
| 2026-09-28 | not verified | 61.0 /  | 88.6 | 100.0 | 111/0/7 → **111/0/0** | 20/2/4 → **20/2/0** | 5 → 5 |

Totals: words eligible/excluded/pending 1170/23/47 → 1169/24/10; grammar 528/32/166 → 528/32/30; verification queue 213 → 40; verified lessons 0 → 0
word bank: {"occurrences": 2255, "eligible": 968, "excluded_not_scored": 1172, "pending_needs_review": 115, "other": 0, "pct": 95.9, "lessons_in_audit": 15, "lessons_missing": [], "note": "pct = (Correct + half Partial) / (Correct + Partial + Wrong); 'Needs review' is pending and counts nowhere; 'Not scored' is excluded by rule (English, names, glue words...)."}


Changed numbers (release layer only; the page % shown with ≈ are the builder's):
- Verification queue 213 -> 40 (Codex agreed on 173). Words pending 47 -> 10; grammar pending 166 -> 30.
- Words excluded 23 -> 24 (09-26: one word inside Amal's untranscribed 00:04-01:06). Coverage: 09-16 Medi 100 -> 98.0 %,
  09-26 Amal 96.0 -> 94.5 %, 09-28 Medi 88.6 % (hole already counted from the transcript, now also proven from audio).
- Totals `unverified_avg_pct`: words 75.5 -> 80.0, grammar 63.4 -> 67.3. Not a change in skill: the old number was a plain
  mean of lesson %s, the new one is pooled (sum right / sum tried), decision 6. After the coordinator merges worker A's
  grammar_math the grammar figure moves again (it reads `uses` and `scored_mistakes`).
- `check`: 11 false problems -> 0 (reconciliation by uid). Tutor "verb answers pulled": 41 hand-kept -> computed (729 after merge).

Examples of scores that changed and why:
- 09-04 grammar pending 18 -> 1: Codex confirmed 17 of its 18 uncertain rows (e.g. FA-7fdfc2e7 51:37 انبسطتت -> انبسطت:
  both independent transcriptions carry her recast); the one it did not confirm goes to Amal.
- 09-26 words excluded 0 -> 1: a word card inside Amal's 21-s untranscribed stretch; her reaction cannot be read.
- 09-05 FA-ab15e48a (شبعان, vocab tier 1) stays pending: Codex reads "Full، مش hot" as a sound slip (S4), not a word -> Amal.

## Decision 5 · Codex second judge (how it works)
- `scripts/codex_rejudge.py` (resumable: skips uids that already have a Codex record). Per row: a clip listen_from..listen_to
  (max 60 s) cut from each person's RAW own track + the mixed recording -> local faster-whisper large-v3 AND the Levantine
  dialect whisper (no prompt, language ar) -> `codex exec -m gpt-5.5` with the Claude readers' claim, the transcript
  lines, both independent transcriptions, and a brief that warns ASR auto-corrects learners and that the readers can be
  wrong -> confirmed / changed / rejected / unsure + reason + quote. 36 Codex calls (6 rows each), 0 failures.
- Ledger `data/accuracy/verifications.json`: 213 records, reviewer `codex gpt-5.5`, role second-judge, method audio,
  evidence = window, clip paths + sha256, large-v3 text, quote. Clip mp3s are git-ignored (hashes kept);
  `data/accuracy/asr-evidence.json` keeps every independent transcription.
- Gate rule: Codex confirmed/changed -> eligible; rejected/unsure -> pending "waiting for Amal". Only a human settles a
  disagreement; a Claude model recorded as second judge fails `check`.
- Tutor page (docs/tutor.html + docs/js/tutor-verify.js): section "For Amal · check these moments" (40 cards from
  docs/data/amal-verify.json; 2 without a playable recording: 09-10 has no lesson.mp3 on the site). Per card: date/time,
  wrong -> right, Medi / Amal lines, "Reader AI says" / "Listening AI says", play (lesson.mp3#t=window),
  **Correction is correct** / **Reason not to correct** + box. Stored in Supabase `amal_rules` (source review, kind
  audit_confirm / audit_skip, word_key `verify:<uid>`) with the open review link's token; queued in localStorage first.
  No hub page, no hub button.
- `scripts/apply_amal_audit_rulings.py` (hourly via tutor_refresh) turns each tap into a human ledger record (reviewer
  Amal): yes = confirmed = scored; reason = rejected = dropped, reason kept; then rebuilds + `codex_rejudge.py --list`.
- Spend: $0 in API fees (local ASR on the GPU; Codex on the ChatGPT plan, logged in data/runs with cost 0). OpenAI and
  ElevenLabs APIs not used; nothing added to data/budget.json.

## Hand check (5 random findings)
1. 09-28 Medi untranscribed 00:42-06:42: dialect whisper on his raw track 01:00-02:00 hears "شو رأيك؟ … What do you mean?" - held.
2. 09-16 Medi 26:49-28:13: raw track "لازم بتمرن … لما عندي وقت … I don't know how to say it" - held (real learner Arabic, no line).
3. 09-26 Amal 00:04-01:06 on her "silent" track: "كيف صارت … this doesn't have an equivalent" - held.
4. 5 random Codex rulings (3 rejected, 2 confirmed) read against their evidence: both confirms are clear recasts; the 3
   rejects are defensible readings (09-05 شبعان as a sound slip; 09-14 basa6tuh accepted with mm-hmm; 09-21 الرز as a
   recast of the whole phrase) and genuinely disputable, which is why they go to Amal - held.
5. The 11 grammar "problems" on 3c2835c: in all 15 lessons the audit uids = counted cards + set-apart cards exactly - held.
Result: 5 of 5 held.

## Tests
`python -m pytest -q tests/test_accuracy_gates.py tests/test_accuracy_gates_sources.py` -> 41 passed.
Fail-before: the first 25 tests on the previous accuracy_gates.py = 11 failed / 14 passed; each later fix was shown failing
first (third reader 1, pooled / ruled / missing 2, pulled count = AttributeError, caption parser read 0 blocks).
Whole suite (`-k "not m5_cards and not m4_after"`): 332 passed, 5 failed - all 5 outside my files and failing before
(test_m3_planner, test_stale_banner, 3 x test_vocab_audit).

## Decisions for Medi (one line each, yes/no)
- "Verified" needs a human listening pass (asr_review_required_for_verified), so no lesson can be verified today. Keep? (yes/no)
- Both agreement readings (within each pass AND between passes >= 95 %) stay enforced (09-27 open question). Keep both? (yes/no)
- Transcribe Medi's first 09-28 recording (0:00-6:43, about $0.03 ElevenLabs) like the 09-23 gap fill? (yes/no; not done: spend + raw layer)

## Decisions for Amal
- 40 moments on the Tutor page: "Correction is correct" or a reason. (Medi sends her the Tutor link; the app sends nothing.)

## NOT complete because
- Reader agreement is 48-81 % per pass (95 % needed): no lesson is verified.
- ASR has never been reviewed by a person; Codex judged through ASR text, not ears.
- 40 rows wait for Amal; 09-10 has no lesson.mp3 on the site, so 2 of her cards cannot play.
- review_lesson.py / hourly_lessons.py (not mine) still need: run `source_audit.py <date>` and `codex_rejudge.py` for each
  new lesson, use `cache_state` / `write_manifest` instead of `os.path.exists` for reader files, `check=True` on builders,
  stop on Arabizi gaps, publish only when `accuracy_gates.py check` exits 0.
- Word Bank: 115 "Needs review" occurrences still pending (was 350); 09-14 and 09-18 are now in its audit.



