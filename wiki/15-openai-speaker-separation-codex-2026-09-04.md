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

## Recipe 1 RUN 2026-09-04 (scripts/engine_openai_recipe1.py -> data/aug25/openai_recipe1.json)
- 20 clips -> 129 speaker slices (ElevenLabs auto timings, same-speaker words <1.5 s apart merged, pad 0.15/0.25 s, never into the neighbour) -> gpt-transcribe, `languages[]=ar,en`, verbatim prompt, wav 16 kHz mono. ~7 s/clip, 1 empty slice of 129 (clip 6, Medi "ما،" 1.2 s).
- Words: ElevenLabs 420 (397 without fillers) vs Recipe 1 333 (327 without fillers) vs plain gpt-transcribe run 303. Recipe 1 = 82% of ElevenLabs, +10% over the plain run, now WITH speaker labels.
- Loss sits on Medi: his slices 201 vs 273 (74%); Amal's 132 vs 147 (90%). gpt-transcribe keeps 6 fillers vs ElevenLabs 23.
- It kept at least one learner form ElevenLabs corrected (clip 1: "اشتغلات كتير" vs "اشتغلت كتير") -> a possible LearnerVoice signal worth checking on the 20 corrections.
- Page: docs/recipe1.html (GitHub Pages) + artifact ee328d55. Verdict: works as designed but still fewer words than ElevenLabs alone; useful only as a second opinion on Medi's slices, not as the engine.
