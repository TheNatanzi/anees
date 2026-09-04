# 07 — Transcription Engines for Levantine Arabic (from first research batch, 2026-09-03)
| Engine | WER on Levantine | Palestinian named? | Speaker labels | AR-EN mix | Cost | Verdict |
|---|---|---|---|---|---|---|
| Google Meet Gemini notes/transcript | no Arabic at all | — | — | — | Workspace | ✗ (Aug 25 proof: Arabic → gibberish) |
| Whisper large-v3 stock | ~58% | no | no | poor | free | ✗ |
| WhisperLevantine fine-tune | ~33% (Israeli-Arabic skew) | partly | no | ? | free | fallback |
| oddadmix whisper-turbo dialectal | 34% vs 59% base | Levantine | no | ? | free | fallback |
| Cohere Transcribe Arabic 07-2026 | ~40% | dialects | **no** | inconsistent | free, Apache-2 | second opinion |
| Deepgram Nova-3 Arabic | ? | **yes** | unverified | unverified | ~$0.29/hr | cheap fallback |
| Speechmatics Ursa 2 | 6.3% code-switch (self-reported) | Levantine | yes | claimed | ~$0.13/hr | test if Scribe fails |
| **ElevenLabs Scribe v2** | 10-25% | marketing page yes / docs unclear (conflict) | **yes** | **best independent AR-EN score** (arXiv 2605.19069) | $0.40/hr | **primary; verify in Phase 0** |
| Gemini 3.5 Transcribe | ar-EG only listed | no | ≤8 speakers, 30-min cap | ? | token-priced | no |
Benchmark reality: no Palestinian test set exists anywhere. Assume 25-35% WER on real tutoring audio; hand-check a 50-utterance sample. Diarization is mandatory (tutor vs learner turns). LearnerVoice 2024: stock ASR deletes fillers and self-repairs — use verbatim prompting.
