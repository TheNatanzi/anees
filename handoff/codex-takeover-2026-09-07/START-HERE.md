# START HERE — Anees takeover for Codex (prepared 2026-09-07 by Claude)

**Repo:** `C:\dev\anees` · branch `master` · HEAD `22a14a4` (2026-09-05) · remote `https://github.com/TheNatanzi/anees.git` (public) · site `https://thenatanzi.github.io/anees/`
**Owner:** Medi (learner, thenatanzi@gmail.com, Android phone). **Tutor:** Amal (Palestinian Arabic, reads Arabic; Medi reads Arabizi).

## 1. What Medi wants now (his words, 2026-09-07)

> The current system makes too many errors. I want the immediate work focused on transcription quality. Anees must accurately capture our Palestinian Arabic and English tutoring conversations, including my imperfect speech. It must preserve incorrect attempts, repetitions, false starts, and uncertainty rather than quietly replacing them with the correct word. The immediate milestone is a trustworthy, audio-linked transcript that Amal and I can inspect and correct. Everything else (error diagnosis, pronunciation grading, cards, spaced repetition, dashboards, pause analysis) comes later. "Perfecting transcription" means measuring and reducing actual errors against human-reviewed audio.

Hard requirements he stated (full list in `01-history-and-decisions.md` §3): his attempted form stays distinguishable from the intended form; "I forgot" / "what does X mean" utterances survive; the vocabulary Doc is context, never a whitelist that forces unknown speech into a known word; ordinary English, names, fillers and real Palestinian morphology are allowed; capture must be central and easy (Amal never uploads anything); separate named tracks preferred; ≈ $3 per lesson; later ≈ 20 review items per lesson and ≤ 3–5 min of Amal's time.

## 2. What the project does today (one paragraph)

A Recall.ai bot joins the Google Meet lesson and records **one mp3 per person** (works since 2026-09-05). Each track is sent whole to **ElevenLabs Scribe v2** (no keyterms, no language hint), the two word streams are merged on the tracks' start offsets with speaker = track, a mixed `audio.mp3` is made for clips, and a transcript page is published (runs per speaker, fillers shown as `(pause Ns)`, Amal's "yes/ممتاز" shown as ✓). Downstream (built, working, but **not the priority now**): Doc-word matching → "possible miss" events with clips → miss-kind classifier → after-lesson report page + email → Amal's tap links (before/after lesson) → flashcards, buckets, homework, a Slips tally page, a Supabase database, a public site with 10 tabs. The older path (hourly Task Scheduler job watching the host's Google Drive "Meet Recordings" folder, one mixed recording, speaker labels by diarization/pitch) still exists and **fired on 2026-09-05 on top of the bot result** (see §4).

## 3. Why it is not yet reliable (the honest list; details in `04-failure-inventory.md`)

1. **No human-verified verbatim transcript exists for any lesson.** Every "accuracy" number in the repo is either token counts, filler counts, a 20-clip preference vote, or machine agreement. Amal's blind vote (15/20 for ElevenLabs) ranked engines; it did not measure word errors.
2. **Medi's Arabic on his own track comes out in Latin letters** (Scribe detects the Medi track as `eng` 0.978 and writes "anbisti fi laylak", "Lamma akon shaban"); on a mixed recording the same engine writes Arabic script. Untested: forcing `language_code=ara` on his track. This affects every downstream matcher.
3. **Stumbles were being turned into vocabulary words** by the matcher ("موز-" → Moz banana, "biz'a-" → Besse cat, "za'aj" → Joaz husband, "heyye" → 7ayye snake) — fixed 2026-09-05 by rules, not by a better transcript; the transcript itself kept the stumbles correctly.
4. **Long `[laughs]` / `[audio cuts out]` audio-event spans** (33 s on Amal's track at 27:31, 26 s on Medi's track at 0:36) may hide speech; not verified by ear.
5. **Two capture paths for one lesson**: the bot tracks and the host's Meet recording. On 2026-09-05 the hourly job re-transcribed the mixed recording at 16:15, overwrote the two-track result, emailed Medi twice more, and published a worse page. Guarded since (`process()` reuses an existing `scribe.json`), but the job still watches the folder.
6. **Speaker labels on older lessons are inferred** (Sep 4: ElevenLabs merged the voices; 13.6 % of words labeled by pitch or unlabeled). Only 2026-09-05 has certain speakers.
7. **The displayed transcript is raw ASR words** (good) but fillers are collapsed into `(pause)` and tutor confirmations into ✓; the raw filler text is only in `scribe*.json`.

## 4. How to run it (details and every command in `02-current-implementation.md`)

```powershell
cd C:\dev\anees
python -m pytest -q                                  # 104 tests; 1 known failure in test_m3_planner (planner screen has 9 buttons, limit 4)
python scripts\ingest_tracks.py 2026-09-05 --hhmm 1419 --src "G:/My Drive/Meet Recordings/mcy-upvb-dfn (2026-09-05 14 18 GMT-7)"   # reuses scribe_*.json: no paid call
python scripts\understand_lesson.py 2026-09-05       # events + clips from the merged scribe.json (no paid call)
python -c "import sys; sys.path.insert(0,'scripts'); import build_report; print(build_report.build('2026-09-05', use_db=True, send=False))"
```
Secrets: Windows **User** environment variables (`ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `RECALL_API_KEY`, `RECALL_REGION`, `ANEES_SUPABASE_*`, `SUPABASE_ACCESS_TOKEN`), read by `scripts/anees_env.py`; never in the repo. Nothing paid runs on the commands above except a **fresh** date with no `scribe_*.json`.

## 5. Inspect first (in this order)

1. `data/lessons/2026-09-05/` — the latest and only two-track lesson: `tracks/Medi_Natanzi.mp3`, `tracks/Amal.mp3`, `tracks/tracks.json` (offsets), `scribe_Medi.json`, `scribe_Amal.json` (raw), `scribe.json` (merged), `transcript.txt`, `scribe_meet_mixed_1615.json` (the same lesson from the mixed Meet recording, same engine: compare scripts and words).
2. `03-transcription-pipeline-trace.md` — every transformation from mp3 to the page, with code lines.
3. `04-failure-inventory.md` — 14 concrete failures with timestamps, raw vs displayed, cause status.
4. `data/lessons/2026-09-04/` — the most representative *difficult* recording (mixed audio, merged voices, pitch fallback, 47 chat-typed forms).
5. `06-experiments-and-benchmarks.md` — what was actually run, and what the "15/20" means.

## 6. Unfinished work (do not lose)

- Untracked in the working tree: `data/lessons/2026-09-05/scribe_Amal.json`, `scribe_Medi.json`, `scribe_meet_mixed_1615.json`, `summary_meet_mixed_1615.json`, `email.json` (raw engine outputs; `*.json` under `data/lessons` for raw scribe were never committed for any lesson — keep them, they are the evidence). Modified: `data/vocab/words.json`, `docs/data/words.json` (hourly Doc import re-exported 2026-09-07 14:35), `data/m4_stand_in_timing.json` (test residue).
- Amal's after-lesson link for 2026-09-05 was minted twice and never sent; the planner link for 2026-09-05 was never sent. Her verdicts do not exist for any lesson.
- Codex's own last two tasks: UI/UX audit `task-mtokizrg-aqwvt5` (never read), M10 privacy audit (NO-GO on publishing verbatim WhatsApp lines; Medi kept them public by choice).
- Planned-not-built: calendar auto-join for the bot; Medi's correction page (`check.html`); Amal's notes box; classifier rows G1–G15 (wiki 17).

## 7. The next milestone should produce

**A verbatim, speaker-certain, audio-linked transcript of one full lesson (2026-09-05), reviewed by Amal and Medi, with a measured error count** — see `08-transcription-first-plan.md` for the reproduction steps, the 20-example review protocol, the acceptance criteria and which existing pieces to reuse. Park everything under `docs/` except `lessons/<date>.html` until that exists.

## Manifest

| File | Purpose |
|---|---|
| `START-HERE.md` | this page |
| `01-history-and-decisions.md` | problem, evolution, Medi's requirements verbatim, approved vs inferred vs unresolved, abandoned approaches, diagrams |
| `02-current-implementation.md` | repo state, tree, feature → file map, commands, jobs, storage, local vs deployed |
| `03-transcription-pipeline-trace.md` | lesson 2026-09-05 traced stage by stage with code locations and request settings |
| `04-failure-inventory.md` | 14 concrete failures with timestamps and cause status |
| `05-recordings-and-human-feedback.md` | every recording, track, chat, snapshot and human rating, with exact paths |
| `06-experiments-and-benchmarks.md` | every engine test: what ran, how judged, what it supports; the 15/20 explained |
| `07-configuration-and-access.md` | env-var names, sanitized config, accounts, consent and retention decisions |
| `08-transcription-first-plan.md` | reproduce the worst problems, review protocol, acceptance criteria, reuse map |
| `09-uncertainties-and-corrections.md` | claims now doubtful, stale docs, unverified integrations |
| `evidence/` | small copies: tracks.json, summaries, tally.json, ai_rules.json, Amal's Check-02 results and scoring rule, Codex reports and Claude's audit (markdown), lesson transcripts |
| `MANIFEST.md` | file list with sizes |

Paste for Codex: see the end of `08-transcription-first-plan.md`.
