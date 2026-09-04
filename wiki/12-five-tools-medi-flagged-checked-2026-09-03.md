# 12 — Five Tools Medi Flagged (checked 2026-09-03)
| Tool | Stars / license / last push | Arabic | Transcript in | Results out | Verdict |
|---|---|---|---|---|---|
| [LinguaCafe](https://github.com/simjanos-dev/LinguaCafe) | 1,445 / GPL-3 / 2026-08 | **No** (27 langs, no RTL) | yes, text/subs | Anki export, no API; Leitner not FSRS | **Skip** |
| [asbplayer](https://github.com/asbplayer/asbplayer) | 1,427 / MIT / 2026-09 | untested, no RTL work ([#775](https://github.com/asbplayer/asbplayer/issues/775)) | subtitle + media only | reads Anki status in, no export | **Copy the card shape**: sentence + clipped audio + timestamp + source |
| [Yomitan](https://github.com/yomidevs/yomitan) | 2,805 / GPL-3 / 2026-08 | **best of the five**: MSA deinflection + dialect preprocessor ([PR 1958](https://github.com/yomidevs/yomitan/pull/1958)), hamza/alif/diacritic normalisation; hit rate 35%→89%; no Levantine rules, no Arabizi | no (hover only) | duplicate check only | **Copy the matching logic** (re-type, GPL) |
| [OpenLingo](https://github.com/pretzelai/openlingo) | 64 / MIT / 2026-05 (quiet 3 mo) | `ar` with MSA frequency dict; no RTL/dialect/Arabizi | via chat/unit [unverified] | Postgres tables | **Copy the pattern (MIT)** |
| [Immersion Suite](https://github.com/Mezuna-dev/Immersion-Suite) | 0 / GPL-3 / 2026-06 | none (Japanese) | no | local SQLite | **Skip** (FSRS-6 port + heatmap worth a glance) |

### OpenLingo, closer (deepest overlap)
- Modules: AI chat tutor with memory; 9 exercise types incl. speaking (Whisper STT → compare → grade) and listening (gpt-4o-mini-tts); SM-2; AI-generated units; article translator; streaks.
- Schema (`lib/db/schema.ts`, Drizzle + Postgres): `srsCard` (word, translation, cefr, pos, gender, examples, status, SM-2 fields; **no audio, no second script**), `dictionaryWord`, `wordCache`, `unit`, `course`, `lessonCompletion`, **`exerciseAttempt`** (type, correct, userAnswer), `dailyActivity`, `userStats`, **`userMemory`** (key/value notes), `chatConversation`, `audioCache`.
- LLM/ASR: Vercel AI SDK, Anthropic/OpenAI/Google; Whisper + OpenAI TTS; no local option. AI tools: readMemory/addMemory, **`srs` = the AI runs SQL against the learner's card table**, presentExercise, createUnit, addWordsToSrs.
- **Tutor-facing: none.** No teacher role, no confirm queue.
- Lift (MIT): `srsCard` + `exerciseAttempt` + `userMemory` shapes; the "AI can SQL the cards" tool ("what did Medi miss twice this month"); the speaking-exercise flow. Keep FSRS, drop its SM-2.

### What changes in our plan
- Nothing runs as-is; the blueprint stands. No open-source tool has a tutor role → Amal's confirm queue stays our own build.
- Add Yomitan-style Arabic normaliser (diacritics, hamza/alif, prefix/suffix peeling) to the miss-finder's matching step (Phase 2).
- Miss-card = asbplayer shape: sentence + clipped audio around the timestamp + source line.
- Adopt OpenLingo's `userMemory` idea as "notes Amal has made about Medi" and its SQL-over-cards tool for suggestions (Phase 5).
