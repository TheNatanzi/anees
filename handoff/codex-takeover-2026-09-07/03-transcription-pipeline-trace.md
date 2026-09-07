# 03 — Transcription pipeline: every transformation, traced on lesson 2026-09-05

Two paths exist. **Path A (bot tracks)** produced the published 2026-09-05 pages. **Path B (Meet recording)** produced every earlier lesson and, by accident, a second 2026-09-05 run at 16:15 (kept as `scribe_meet_mixed_1615.json`).

## Stage 0 — Capture

| | Path A: Recall.ai bot | Path B: Google Meet host recording |
|---|---|---|
| Code | `scripts/recall_bot.py join/fetch` (manual, before/after the call) | Meet records to the host's Drive; `run_lesson_pipeline.ps1` hourly |
| Output | `data/lessons/2026-09-05/tracks/Medi_Natanzi.mp3` 3763.68 s, `Amal.mp3` 3738.53 s; both **mp3 24 kHz, 2 ch, 64 kbps** (Recall "audio_separate" manifest); `tracks.json` with `start.relative` offsets 0.429 s (Medi) / 0.613 s (Amal) from the bot's own clock, `start.absolute` UTC | `G:\My Drive\Meet Recordings\mcy-upvb-dfn (2026-09-05 14 18 GMT-7)` 133 MB mp4 (mixed, one channel of everyone) + `… - Chat Transcript` (2 KB, 55 typed lines by Amal) |
| Known issues | Medi's track has `[audio cuts out]` 36.6–62.4 s (26 s, one word "Uh-oh" in that span; the mixed file has one word "make…" there too → probably real silence, unverified by ear). Tracks are per *participant login*: the host account wc@adibs.com produced no track (silent). | one channel: speakers must be inferred (Stage 3) |

## Stage 1 — Audio preparation

- Path A: **no resampling, trimming, denoising, VAD or segmentation** before ASR; each mp3 is posted whole (`ingest_tracks.transcribe_track` → `lesson_pipeline.transcribe`). Duration measured with `ffprobe` only for the budget estimate. After ASR, `mix_audio()` builds `audio.mp3` = `ffmpeg adelay(offset ms) + amix normalize=0 → mono 64 kbps` (24 kHz) for clip cutting only.
- Path B: `extract_audio()` = `ffmpeg -vn -ac 1 -ar 16000 -b:a 48k` → `audio.mp3` (16 kHz mono); `is_arabic_lesson()` cuts minutes 3–6 to `sample.mp3` and transcribes it first ($0.01) unless the chat sidecar shows a tutor typing (2026-09-05: sidecar present → pre-check skipped). Lesson audio never deleted (rule).

## Stage 2 — Recognition (ElevenLabs Scribe v2)

- Code: `scripts/pipeline_ext.py:42 transcribe_with_retry` (`POST https://api.elevenlabs.io/v1/speech-to-text`, header `xi-api-key`, multipart file).
- Request settings (in code, identical on both paths): `model_id=scribe_v2`, `diarize=true`, `num_speakers=2`, `timestamps_granularity=word`, `tag_audio_events=true`. **No** `language_code`, **no** keyterms, **no** `no_verbatim` flag (provider default; Codex's reports assume default = verbatim), no prompt. Timeout 1800 s; retries 3× on 429/5xx (5/20/60 s). Budget stop at 90 % of $10 (`CAPS`), price assumed $0.22/h (`ELEVEN_USD_PER_MIN`).
- Note: on a **single-person track** `num_speakers=2` is still sent; the engine's `speaker_id` values are then discarded by the merge (Stage 3). Whether diarization changes recognition on a single-voice file is untested.
- Raw response (saved verbatim): `language_code`, `language_probability`, `text`, `words[]`, `transcription_id`, `audio_duration_secs`. `words[]` items: `{"text","start","end","type": word|spacing|audio_event,"speaker_id","logprob"}`. 2026-09-05 Medi track: 2,691 words, 2,717 spacing, 31 audio events (`[laughs]` 12, `[background noise]` 7, `[audio cuts out]` 1, `[foreign language]` 1, `[ضحك]` 3, `[حديث متقاطع]` 1 …), `language_code=eng` (0.978). Amal track: 1,781 words, events `[تضحك]` 16, `[laughs]` 5 (one 33 s long at 27:31–28:04, 4 words inside), `[يضحك]` 3.
- **Script choice is the engine's**: with track language detected as `eng`, Medi's Arabic is mostly written in Latin letters ("anbisti fi laylak", "Lamma akon shaban", "za'aj", "biz'ajni"); on the mixed file (language `ara` on earlier lessons) the same utterances come out in Arabic script ("انبسطي بـ ليلك", "لما أكون شبعان"). Compare `scribe_Medi.json` vs `scribe_meet_mixed_1615.json` at 1229–1243 s and 3316 s. **This is the single biggest untested knob** (`language_code=ara` per track, or per-segment).
- Files: `scribe_Medi.json` (720 KB), `scribe_Amal.json` (485 KB), written once (E1).

## Stage 3 — Speaker attribution and merge

- Path A: `ingest_tracks.merge()` — for each track, keep `type=="word"` items, add the track's `start.relative` offset, set `speaker_id` = "Medi"/"Amal" from the participant name (`person()`), sort by start. Output `scribe.json` = `{words, language_code (Amal's), language_by_track, speaker_source:"tracks", tracks[]}`. `lesson_pipeline.build()` sees `speaker_source=="tracks"` and keeps the labels (`speaker_split = "ok: one audio track per person (Recall bot)"`). No overlap handling: simultaneous words interleave by time.
- Path B: `build()` → `label_speakers()` = the ElevenLabs `speaker_id` with the higher Arabic share becomes "Amal" (**heuristic**); if one speaker holds < 5 % of words the split "failed" → `pitch_labels()` (librosa YIN, 50 ms hops, < 155 Hz = Medi, > 180 Hz = Amal, else "?" unless both neighbours agree). Sep 4 went this way: 13.6 % unlabeled. `understand_lesson.label_confidence` publishes per-speaker numbers only if unlabeled ≤ `MAX_UNLABELED` (15 %).

## Stage 4 — Word stream → runs → transcript text

- `build()`: `words = [{s,e,spk,w: text.replace('\ufffd','')}]` for `type=="word"` only → **spacing and audio_event items are dropped here** (so `[laughs]`, `[audio cuts out]` never reach the page). Lesson window = first to last Amal word.
- `lesson_text.runs_from_words(words, tutor='Amal', gap=1.0)`: groups consecutive same-speaker words into runs; a token matching `FILLER` (`um, uh, hm, mm, er, ah, أمم, آآ, ا+م+ …`) becomes `{'pause': seconds}` (merged with adjacent fillers of the same speaker within 1 s; minimum shown 0.3 s); a token matching `CONFIRM` (`mhm, yes, yeah, exactly, ممتاز, أيوه, صح, مظبوط, برافو …`) that opens Amal's reply after Medi's Arabic gets `ok: True` → rendered as ✓. **These are the only rewrites**: no translation, no normalisation, no LLM, no Arabizi conversion, no spelling change. The filler *text* is lost on the page (kept in `scribe*.json`).
- `transcript.txt` line = `[mm:ss] Speaker: run_text` with `(pause 0.7s)` inline; `transcript.html` = same runs, ✓ marks, Amal's typed chat lines section, stats (minutes, words, Arabic words by Medi, confirmations, pauses).
- Timestamps: word `start` from the engine, offset-shifted on Path A; mm:ss on the page = run start. No chunk stitching on either path (whole file per request).

## Stage 5 — Downstream (not transcription; documented so nothing is mistaken for ASR output)

- `understand_lesson.py`: Doc-word events (n-grams 3→1 over same-speaker tokens; matcher tiers `exact loose > fold > short > skeleton(≥3 consonants) > fuzzy`; English stop list; glue keys; false-start rule; pronoun shapes), flags `prompted / correction / uptake / asked / elicited`, chat-typed anchoring (Meet sidecar + WhatsApp lines), clips (`ffmpeg -ss … -t …` from `audio.mp3`, ≤ 25 s, 3 s lead), topics. Output `understanding.json`, `words_labeled.json`.
- `miss_kind.py`: kind per event from (1) Amal's tap, (2) Medi's form vs Doc form, (3) Amal's words in the next 8 s; optional gpt-5.5 fallback (off by default, ≤ 10/lesson).
- `build_report.py`: rows (missed / grammar / nailed / new / reused / heard / typed / moment) → Supabase + page + email JSON. **Only Medi's events count** (M11).
- Words Codex should not confuse with transcript text: the report's "text" column is the event's token(s) from `words_labeled.json` (raw), the "Doc word" column is the vocabulary entry it was matched to.

## Where original words can be omitted, inserted, merged, translated or "fixed"

| Point | What can happen | Path |
|---|---|---|
| Engine | audio events replace speech (`[laughs]` 33 s, `[foreign language]`); Latin vs Arabic script choice; provider-side normalisation unknown (no `no_verbatim` control set) | A, B |
| Engine diarization | on mixed audio, both voices on one `speaker_id` (Sep 4) | B |
| `build()` | drops `spacing` and `audio_event` items; strips U+FFFD | A, B |
| `runs_from_words` | fillers → `(pause)`; confirmations → ✓ (text kept) | A, B |
| Lesson window | words before the first / after the last Amal word are excluded from counts (not from the page) | A, B |
| Merge | interleaving by time only; no overlap marking | A |
| Matcher | a token is *linked* to a Doc word (never rewritten on the transcript page); the report shows the Doc spelling next to the raw token | downstream |

Answer to "is the displayed transcript raw ASR or a rewrite?": **raw ASR words in engine order, with two display substitutions (fillers → pause, confirmations → ✓) and audio-event tags removed.** Code: `scripts/lesson_pipeline.py build/render`, `scripts/lesson_text.py`.
