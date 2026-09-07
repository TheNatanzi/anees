# 09 — Known uncertainties and corrections (candor section)

## Claims made earlier by Claude that are now doubtful or wrong

1. **"ElevenLabs Scribe v2 is the engine — confirmed by Amal's Check 02 (15/20)."** True as a preference vote on 20 Aug-25 clips vs Speechmatics and a local Whisper. It says nothing about word accuracy or about keeping Medi's mistakes; the scoring doc excluded that question. ChatGPT/OpenAI was not in the vote.
2. **"0 % unlabeled, speaker split certain" (2026-09-05).** Certain per *track*, yes. But the same lesson's Arabic came out in Latin letters on Medi's track, which no earlier lesson did; per-track ASR may trade one problem for another (F5). Untested.
3. **The Slips tally (14 slips on 7 rules).** Curated by Claude from transcripts nobody has verified by ear; each row cites a transcript line, not a human-checked one. Treat as hypotheses until the gold set exists.
4. **"13 verified grammar slips"** in wiki 17 §K — "verified" meant "the transcript line exists", not "Amal or Medi confirmed it". Medi confirmed the four false words, the preposition kind and the pause rule; he has not confirmed the tally rows.
5. **Sep 4 per-speaker numbers** are published with 13.6 % of words labeled by pitch or unlabeled; the ≤ 15 % floor was set by Claude, not by evidence.
6. **"Lesson audio never deleted" / retention 90 days.** Both are written down; only the first is true in practice.
7. **Cost per lesson "$0.46 Scribe".** For one lesson; the hourly job's re-run doubled it, and the after-link OpenAI calls (~$0.30) and Recall (~$0.65) are separate.
8. **"77 tests / 104 tests green".** 104 collected; one fails since the M10 planner change (screen with 9 buttons). Some tests use stand-ins (Playwright fake Amal) whose timings are recorded in `data/m*_stand_in_timing.json` and rewritten on every run.
9. **Wiki 17 sources.** Several are search-snippet citations of pages that returned 403 (Routledge, ResearchGate, Al-Thubaiti via lingref); marked in the ledger, but do not cite them onward without opening them.
10. **"House spelling" and "chat ground truth" (M10)** were built by a parallel session; Claude in this session did not verify their matching quality beyond the tests passing.

## Stale documentation

- `README.md` says "Status 2026-09-03: nothing built yet" and points to a claude.ai artifact.
- `plan/constants.md`: two-channel PC recording, Speechmatics/Soniox "clean words" engine, wav2vec2 raw-form pass, FSRS statuses and caps — designed 2026-09-03, superseded or never built.
- `plan/blueprint.md` milestones M1–M8 (visual plan era) ≠ the overnight build's M0–M8 (`plan/OVERNIGHT-BUILD-2026-09-05.md`); same labels, different content.
- `wiki/07` prices and verdicts are from 2026-09-03 documentation research; the engine report page (`docs/engine-report.html`) is the later, tested view.
- `plan/HANDOFF-2026-09-05.md` predates the bot, the Slips page, M10/M11 and the 16:15 incident; `plan/AUDIT-STREAMLINE-2026-09-05.md` proposes `check.html` and Amal notes that were not built.
- `docs/data/ai_rules.json` statuses: several "enforced" rows are enforced by code paths that only the tracks path or only the Meet path exercises.

## Metrics that overstate what was measured

- "Words you nailed" = Medi said a Doc word before Amal did and she did not react within 5 s — a heuristic, not knowledge.
- "Possible misses" precision ≈ 50 % by Claude's own estimate (rule M5); nobody has measured it.
- Codex's token/filler counts (725 vs 590, 22 vs 0) are counts, not accuracy; the ES anchor number was copied from E.
- "Chat found (family) 50/55" = typed forms located in the transcript by consonant family, not exact matches (exact 39).
- Engine report's "~200 fillers kept" counts regex hits in the ASR text; whether they correspond to real fillers is unmeasured.

## Missing files or inaccessible history

- Chat transcripts of the 2026-09-03/04 sessions, the overnight build session and the parallel M10 session: not accessible from this session; their decisions survive only in memory notes, plan files, commit messages and `plan/OVERNIGHT-LOG.md`.
- Raw ElevenLabs outputs for 2026-08-25 through the pipeline: the pipeline reused `data/aug25/eleven_scribe_auto.json`; no `data/lessons/2026-08-25/scribe.json` exists.
- Codex's UI/UX audit `task-mtokizrg-aqwvt5` result was never read (`node "%USERPROFILE%\.claude\plugins\cache\openai-codex\codex\1.0.6\scripts\codex-companion.mjs" result task-mtokizrg-aqwvt5`).
- The 2026-06 → 08-19 Meet recordings were never transcribed; whether they are lessons is unknown.
- The live plan artifact on claude.ai (README link) is in Medi's account only.

## Integration behaviour not verified by Claude

- Recall.ai: only one bot run; whether tracks always come as 2-channel 24 kHz mp3, whether the host's silence is always a missing track, and the 7-day deletion.
- ElevenLabs defaults for `no_verbatim`, and the behaviour of `diarize=true, num_speakers=2` on single-voice audio.
- Supabase RLS on `card_results` (P1 open by design), `amal_links` expiry (tested with stand-ins only), the `grade` edge function under load.
- Gmail sending from the shared app password after the 16:15 duplicates (rate limits unknown).
- Google Drive desktop sync timing (how long after a lesson the recording appears; the hourly job assumes "within the hour").
- Task Scheduler tasks run under Medi's user with the User env; if the PC sleeps, runs are skipped, not queued.

## Check before relying on it

- Every number in `docs/engine-report.html` and `docs/reports/*.html` (rebuilt from markdown; some are Codex's, some Claude's; none are human-verified accuracy).
- `data/lessons/2026-09-01`, `2026-08-23`, `2026-08-22`: "not arabic" pre-check may have skipped real lessons (each has a saved full `scribe.json` to inspect for free).
- `data/tally.json` timestamps (they pass a transcript-line check, nothing more).
- The `*.mp3` ignore rule: any new clips need `git add -f` (now in `git_publish`, but manual scripts must do it themselves).
