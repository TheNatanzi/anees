# 13 — Live transcribers, note-takers, and the two-channel fix (researched 2026-09-03)

## Verdicts
| Tool | Live on Meet | Arabic dialect | Speaker labels | Verbatim | Export/API | Price | Verdict |
|---|---|---|---|---|---|---|---|
| **Speechmatics** (Arabic-English bilingual, Mar 2026) | yes, own audio feed | Levantine incl. **Palestinian named**; mid-sentence Ar/En | real-time speaker + **channel** diarization | disfluencies kept by default, tagged in Arabic | JSON, word times | $100 credit; ~$0.24-1.35/hr (unverified) | **best fit** |
| **Soniox v5** | yes | "Arabic", language-ID + switching | real-time | none documented | JSON | $0.12/hr | cheapest control |
| AssemblyAI U-3.5 streaming | yes | `ar` generic, code-switch | +$0.12/hr | `disfluencies:true` (async confirmed) | JSON | $0.57/hr | solid #3 |
| Deepgram Nova-3 | yes | **`ar-PS`** (Jan 2026) | yes | filler_words English-only | JSON | $0.46/hr | good tag, weak verbatim |
| ElevenLabs Scribe v2 | batch only (realtime has no diarization) | Arabic "Good" tier | batch: yes | verbatim by default (`no_verbatim` opt-in) | JSON | ~$0.25/hr | post-lesson fallback |
| Azure Speech | yes (preview) | `ar-PS` | preview | lexical raw text | JSON | ~$1/hr | ok |
| Munsit (Arabic-native) | unverified | Levantine incl. Palestinian | unverified | unverified | API | $0.15-0.21/hr | test a file |
| Fireflies / tl;dv / Tactiq / MeetGeek | bot / extension | generic Arabic (tl;dv: no PS) | yes | **no, Whisper-cleaned** | some | $10-22/mo | rejected: auto-corrects learner |
| Lesson Transcriber / LessonScriptor / Notah | extension | unstated / Levantine (Notah) | tutor/student | unstated | TXT | $7-30/mo | test only |
| Granola, Fathom, Read.ai, Circleback, Avoma, Plaud | — | generic or none | yes | no | limited | — | no |
| Otter, Krisp, Notion AI, Supernormal, Meet Gemini | — | **no Arabic** | — | — | — | — | eliminated |
| **Wispr Flow** | Notetaker Aug 2026: **Mac-only, English at launch**, cleans transcripts; dictation deletes fillers/false starts; API sunset | — | none | no | GDPR dump only | $12/mo | **no** |

## What changes in the plan
1. Drop the note-taker category: cleaning models (mostly Whisper) correct learners' errors ("not suitable for error analysis", L2 studies 2025).
2. **Two-channel recording**: Medi's mic = channel 1, Windows WASAPI loopback (Meet output = Amal) = channel 2 → deterministic speaker labels via channel diarization; a tray script that starts with Meet = the one click. No bot, no AI guessing.
3. Verbatim ≠ error-preserving: disfluency flags keep um/uh only. For Medi's wrong forms run a no-LM CTC pass on the learner channel: `elgeish/wav2vec2-large-xlsr-53-levantine-arabic` (free); diff vs the clean transcript; mismatch + Amal restating = correction event.
4. Budget is trivial: $2.40-21/month for 20 lesson-hours.
5. Bench on Aug 25: Speechmatics, Soniox, Deepgram ar-PS, Munsit; score Palestinian vocab, English kept in Latin script, Medi's known mistakes surviving.

Sources in the research log (Speechmatics docs, Soniox, AssemblyAI, Deepgram changelog 2026-01-27, ElevenLabs docs, Wispr docs + TechCrunch 2026-08-05, HF elgeish model, arXiv 2503.06924).
