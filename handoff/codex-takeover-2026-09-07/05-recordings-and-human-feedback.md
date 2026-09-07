# 05 — Recordings, tracks, chats, snapshots and human feedback (exact paths; nothing duplicated)

## A. Lesson recordings

| Lesson | Source and path | Layout | Duration | Status |
|---|---|---|---|---|
| **2026-09-05 (latest; only two-track lesson)** | Recall bot: `C:\dev\anees\data\lessons\2026-09-05\tracks\Medi_Natanzi.mp3`, `Amal.mp3`, manifest `tracks.json` (offsets 0.429 / 0.613 s, absolute UTC starts 21:19:53) | one mp3 per participant, mp3 24 kHz **2 ch** 64 kbps (Recall output; content is one voice) | 3763.7 s / 3738.5 s | processed (Path A); mixed `audio.mp3` 3764.1 s 24 kHz mono for clips |
| 2026-09-05 (same lesson, host recording) | `G:\My Drive\Meet Recordings\mcy-upvb-dfn (2026-09-05 14 18 GMT-7)` (133 MB mp4) + ` - Chat Transcript` (55 lines typed by Amal) | mixed, 1 track | ≈ 63 min | processed by the hourly job at 16:15 (raw kept as `data/lessons/2026-09-05/scribe_meet_mixed_1615.json`, `summary_meet_mixed_1615.json`) |
| **2026-09-04 (most representative difficult recording)** | `G:\My Drive\Meet Recordings\jir-hcex-xzd (2026-09-04 14 03 GMT-7)` (+ chat sidecar, 47 typed forms) → `data/lessons/2026-09-04/audio.mp3` (16 kHz mono 48 kbps, 3876 s), `sample.mp3` (3 min pre-check), raw `scribe.json` | mixed; ElevenLabs merged the voices → pitch labels, 13.6 % unlabeled | 64:36 | processed; 210 published clips |
| 2026-08-25 (the "trust test" lesson) | `G:\My Drive\Meet Recordings\vzq-tryv-mdw (2026-08-25 14 27 GMT-7)` (127 MB) → `data/aug25/audio/aug25.mp3` (30 MB); raw ElevenLabs runs `data/aug25/eleven_scribe_auto.json` / `eleven_scribe_ara.json` (the pipeline reused `auto`); no `audio.mp3` under `data/lessons/2026-08-25/` | mixed; diarization worked (`split ok`, 0 % unlabeled) | 62 min (57.0 in lesson window) | processed; 267 clips; all engine experiments ran on this file |
| 2026-09-01 | `G:\My Drive\Meet Recordings\vbu-dzsj-bpy (2026-09-01 14 05 GMT-7)` (290 MB) → `data/lessons/2026-09-01/audio.mp3` 3516 s + `scribe.json` | mixed | 58.6 min | pre-check said "not arabic" → skipped (a full Scribe run was still saved: 1.7 MB scribe.json) — **check: may be a real lesson wrongly skipped** |
| 2026-08-23 | `asj-zoww-pjq (2026-08-23 14 02 GMT-7)` → `data/lessons/2026-08-23/audio.mp3` 3459 s + `scribe.json` | mixed | 57.7 min | skipped "not arabic" (same caveat) |
| 2026-08-22 | `szh-hwnn-vxj (2026-08-22 16 21 GMT-7)` (85 MB) → `data/lessons/2026-08-22/audio.mp3` 1518 s + `scribe.json` | mixed | 25 min | skipped "not arabic" |
| 2026-06-17, 06-26, 07-01, 07-06, 07-23, 08-03 (×2), 08-19 | `G:\My Drive\Meet Recordings\…` (65–224 MB each; 07-06 = 223 MB, 07-23 = 203 MB) | mixed | unknown | marked "before pipeline (run on request)" in `processed.json`; never transcribed |

Everything under `G:\My Drive` is the host account's Google Drive synced to this PC (wc@adibs.com). Recall keeps the 2026-09-05 tracks on its servers for 7 days from 2026-09-05 (bot id `0a24c69c-…`, ledger `data/lessons/recall_bots.json`); local copies are the only long-term copy.

## B. Lesson chats and captions

- Meet chat sidecars (Amal types drill sentences during the lesson): 2026-09-04 (47 forms, located in the transcript by family/skeleton, 41 exact), 2026-09-05 (55 lines). Path: next to the recording, file name `<recording> - Chat Transcript`. Parsed by `lesson_pipeline.chat_sidecar`, stored in `summary.json.chat_lines` and Supabase `chat_lines`.
- WhatsApp chat with Amal (full export, private, git-ignored): `C:\dev\anees\data\whatsapp\raw\` + `export.zip`; 5,030 lines mined for house spelling (`docs/data/house_spelling.json`) and for typed lines during lessons (`chat_ground_truth.merged_lines`). Contains her real corrections of Medi's typed homework (12 pairs used in `supabase/functions/grade/pairs.ts` and `tests/fixtures/homework_pairs.json` — Codex flagged these as private; Medi kept them).
- Google Meet's own captions/transcript: not usable (no Arabic); not stored.

## C. Vocabulary and grammar snapshots

- Vocabulary Doc (Amal's, id `1inA6ZeETtqJZHQYiZxtubWytsN5xh8_klQH50yRyrjw`): snapshots `data/vocab/doc_markdown_2026-09-04.md` → `data/vocab/words.json` (2,206 rows, 2,120 words after merging 86 duplicates; 20 topics; export stamp 2026-09-07 14:35 from the same snapshot). Live hourly fetch needs `ANEES_DOC_PUBLISHED_URL` (never set).
- Grammar Doc "Arabic Materials" (id `1gStzPV90qvCFYzysgrMT6KOoOU4R4d0v4G8R648w8O0`): `data/vocab/grammar_materials_2026-09-05.md`.
- Subsequent additions: none captured (the Doc diff feature waits on the live fetch). The Sep 4/5 verb families (babse6…, baz3ej…) are **not** in the snapshot; this is why Sep 5 stumbles matched neighbours.

## D. Human feedback that exists

| What | Who / when | Path | What it is |
|---|---|---|---|
| **Check 02 blind engine vote** | Amal, 2026-09-04 (entered by Medi) | `data/aug25/check02_results_amal.json`, scoring rule `check02_scoring.md` (pre-registered 2026-09-03 23:58), key `check02_key.json`, windows `check02_windows.json`, page `docs/check02-amal.html` | 20 clips × 4 anonymised transcripts (local dialect Whisper, Speechmatics ar_en, ElevenLabs auto, ElevenLabs ara); she tapped the best letter(s) per clip. Result ElevenLabs family 15, Speechmatics 5, local 2; head-to-head ElevenLabs vs Speechmatics 11–1, vs local 13–0; 3 rows "none", 2 "tie". **A preference vote, not a word-error measure.** |
| Check 03 (ElevenLabs vs two ChatGPT models) | built 2026-09-04; **no ratings file exists** (`check03_key.json` only) | `docs/check03.html`, `data/aug25/check03_key.json` | unrated |
| Recipe 1 side-by-side | none rated | `docs/recipe1.html` | 333 vs 420 words, machine counts only |
| Gold selections (chunks chosen for review) | Claude, 2026-09-03/04 | `data/aug25/gold_selection.json` (50: 20 corrections, 10 gaps, 10 hesitations, 10 random), `gold_selection_v2.json` | selection by the local dialect transcript, before engine results |
| Medi's corrections | Medi, 2026-09-05, in chat | recorded in `data/tally.json` (rules R1–R10) and `docs/data/ai_rules.json` M6–M11; this handoff §04 | "that was a pause, I meant maz3ooj" (×3), "heyye not 7ayye", "ba6lub min = preposition error", "only count the words I say" |
| Amal's after-link verdicts | **none** — links minted 2026-09-04/05, never sent | `data/amal_links.json`, `data/lessons/pipeline.log` | — |
| Human-approved verbatim reference | **none for any lesson** | — | the central gap |

## E. Known offset / synchronisation facts

- 2026-09-05 tracks: bot-relative starts 0.429 s (Medi) and 0.613 s (Amal); durations differ by 25 s (Amal left/joined later); merge and mix use the offsets; `understanding.json` clip offsets were verified on a sample (report ▶ buttons play the right moment after the force-add fix).
- Aug 25 dialect-Whisper chunk times run 0.5–2 s late vs ElevenLabs (wiki 15); gold chunk boundaries are approximate.
- Sep 4 chat sidecar times are Meet wall-clock; matched to transcript tokens within ±120 s by word family (`understand_lesson.locate_chat`).
- Mixed `audio.mp3` for 09-05 is 24 kHz (tracks) while earlier lessons are 16 kHz — harmless, but note when comparing.

## F. Which to inspect first

- Latest: 2026-09-05 (tracks + mixed re-run of the same audio = a free A/B on script choice).
- Most representative difficult: 2026-09-04 (merged voices, chat anchoring, "Nahl", "nitla").
- Possibly mis-skipped: 2026-09-01, 08-23, 08-22 (raw scribe.json exists; check whether they contain Arabic).
