# 15 — Can OpenAI separate Medi and Amal? (Codex research, 2026-09-04)

**Findings**
- `gpt-4o-transcribe-diarize` accepts `known_speaker_names` + `known_speaker_references` (2–10 s reference audio per speaker, data-URL base64, up to 4 speakers, positional). No `prompt`; `keywords` and plural `languages` are `gpt-transcribe`-only. Model is deprecated, shutdown 2027-02-26.
- No alignment endpoint joins diarizer timings with `gpt-transcribe` words; word timestamps are `whisper-1`-only. Slicing by speaker (ElevenLabs / diarizer / pyannote) and transcribing each slice is application-level but sound.
- Realtime models (`gpt-realtime-*`, `gpt-live-transcribe`) give no speaker labels; server VAD splits on silence, not voice.
- `gpt-audio-1.5` zero-token replies (`finish_reason: stop`) have no documented cause or fix; use `gpt-transcribe`.

**Ranked recipes**
1. **ElevenLabs timings → gpt-transcribe per speaker slice** — `{"model":"gpt-transcribe","languages":["ar","en"],"prompt":"Verbatim Palestinian Arabic lesson; preserve fillers, false starts and mistakes; Arabic script, English as English."}` on each speaker-homogeneous slice; reassemble with ElevenLabs labels/times. Highest reliability. ≈ $0.27/hr OpenAI (+ ElevenLabs $0.22/hr).
2. **Known-voice diarizer → gpt-transcribe** — diarize with references, then re-transcribe each segment as in 1. ≈ $0.63/hr.
3. **Known-voice diarizer alone** — identity improves, German risk remains. ≈ $0.36/hr.

**Next experiment:** add `--segments-from data/aug25/eleven_scribe_auto.json` to `scripts/engine_openai_clips.py` (slice → transcribe → reassemble) and compare against ElevenLabs on the 20 clips.
