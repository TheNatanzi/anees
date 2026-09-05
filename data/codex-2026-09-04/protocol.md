# Anees independent engine test - preregistration

Registered: 2026-09-04, before inspecting any OpenAI output or the existing ElevenLabs transcript for this lesson.

## Purpose

Test whether a stronger OpenAI prompt constrained to Palestinian Arabic, English, and Medi's learned/topic vocabulary materially improves transcription behavior on a new lesson, and compare that behavior with ElevenLabs Scribe v2 on exactly the same audio windows.

This is independent of the conclusions and sample selection in the existing `engine-report.html`. Existing Anees code is used only to locate the already-paid ElevenLabs raw response; its conclusions are not inherited.

## Frozen source inputs

- Recording: `G:\My Drive\Meet Recordings\jir-hcex-xzd (2026-09-04 14 03 GMT-7)`
- Recording SHA-256: `248EE52C3D0FD02A62AB72518B34B381A4F26CA75BB8A088D93DF10CA4CA1576`
- Duration: 3,876.083333 seconds (64m 36.1s)
- Streams: H.264 video, one stereo AAC audio stream, one timed-text stream. The stereo stream is treated as mixed audio unless channel analysis proves otherwise.
- Meet chat transcript SHA-256: `CB8A8F3380792FE71AA8E26771C9A91636B521BF22459C5974A51175418345BE`
- Existing ElevenLabs response: `C:\dev\anees\data\lessons\2026-09-04\scribe.json`
- Existing ElevenLabs response SHA-256: `A94C9E18376E95B0A96A51F4F289F3680A6000B0CC004C7F9137D48B9DBCFD6E`
- Google vocabulary document: `Arabic Full Vocabulary list`. The current lesson's `Latest Topic`, the visible `Animals` tab, and the Meet chat are used to build the topic vocabulary. Other tabs may be archived for reproducibility but do not determine the initial topic list.

## Sample selection

The chat contains 21 timestamped messages from Amal. Each is an independently recorded, lesson-time lexical anchor. The evaluation uses exactly 20, honoring Medi's requested per-lesson review size.

Selection rule:

1. Number chat messages 1-21 chronologically.
2. Draw 20 without replacement using Python `random.Random(20260904).sample(range(1, 22), 20)`.
3. Sort the selected indexes chronologically.
4. Frozen selected indexes: 1-19 and 21. Frozen excluded index: 20.
5. For each selected anchor at time `t`, cut `[t - 15.0s, t + 10.0s]`, clipped to the recording bounds. This yields 25-second windows and captures speech immediately before and after the chat post.
6. Do not move a window after seeing any engine output. Overlap between nearby windows is retained and reported.

The sample is not a representative random sample of the whole lesson. It is an intentionally high-value lexical-anchor sample, suitable for measuring topic-term recovery and failure behavior but not whole-lesson WER.

## Systems under test

### E - ElevenLabs baseline

- Existing full-lesson Scribe v2 result, generated before this test.
- Use all word tokens whose midpoint falls inside each frozen window.
- Preserve original speaker IDs, word times, and confidence.
- No new ElevenLabs call is made.

### O1 - OpenAI strict bilingual/verbatim prompt

- Model: `gpt-transcribe`.
- Endpoint: `/v1/audio/transcriptions`.
- Response format: JSON.
- Language hints: Arabic and English.
- No learned vocabulary list.
- Prompt frozen below.

> This is a one-to-one Palestinian Arabic lesson between a male learner, Medi, and his female tutor, Amal. The only languages spoken are Palestinian Arabic and English. Transcribe exactly what is audible. Write Arabic speech in Arabic script and English speech in Latin script. Never translate. Never output German, Japanese, Chinese, Azerbaijani, Spanish, or any other language. Preserve fillers, repetitions, false starts, cut-off words, wrong grammar, learner mistakes, and uncertain pronunciations. Do not silently repair Medi's speech into a fluent or correct sentence. If a sound cannot be identified, write [غير واضح] or a brief phonetic approximation instead of inventing a plausible word. Do not add explanations or speaker labels.

### O2 - OpenAI learned-vocabulary prompt

- Same model, endpoint, response format, and language hints as O1.
- Same core behavioral instructions.
- Adds a topic lexicon derived only from the lesson chat and the user's vocabulary document.
- Prompt frozen below; the generated lexicon block is stored verbatim in `manifest.json`.

> This is a one-to-one Palestinian Arabic lesson between a male learner, Medi, and his female tutor, Amal. The only languages spoken are Palestinian Arabic and English. Transcribe exactly what is audible. Write Arabic speech in Arabic script and English speech in Latin script. Never translate. Never output German, Japanese, Chinese, Azerbaijani, Spanish, or any other language. Preserve fillers, repetitions, false starts, cut-off words, wrong grammar, learner mistakes, and uncertain pronunciations. Do not silently repair Medi's speech into a fluent or correct sentence. The approved vocabulary below is context, not a correction key: prefer one of its words or an ordinary Palestinian inflection only when the audio supports it. If Medi mispronounces a listed word or produces a nonword, preserve the closest phonetic form rather than replacing it with the approved word. If a sound does not fit the list, write [غير واضح] or a brief phonetic approximation; do not invent a different Arabic word. Do not add explanations or speaker labels. APPROVED TOPIC VOCABULARY: {generated lexicon block}

## Topic lexicon construction

Include unique, non-empty vocabulary values from:

1. every selected Meet chat message;
2. the `Latest Topic` Google Doc tab;
3. the `Animals` Google Doc tab because the lesson explicitly uses `Na7el` / bees.

Keep both Arabizi and Arabic forms when available. Remove Markdown syntax and English definitions. Deduplicate case-insensitively while preserving first occurrence. Do not add words based on any ASR output.

## Call and retry policy

- Each 25-second clip is sent once to O1 and once to O2.
- To reduce time/order bias, odd-numbered clips call O1 then O2; even-numbered clips call O2 then O1.
- Retry only HTTP 429 or 5xx, at most two additional attempts with deterministic backoff of 2s then 5s.
- Do not retry or manually edit a successful but empty, wrong-language, or poor transcript; those are outcomes.
- Persist status code, elapsed time, raw JSON, returned text, prompt ID, clip hash, model name, and estimated audio cost.
- Maximum planned OpenAI audio: 20 clips x 25s x 2 arms = 1,000s = 16.67 minutes.
- Cost ceiling at the current official price of $0.0045/minute: approximately $0.075, excluding negligible non-audio charges if any. Abort before $3.

## Frozen metrics

### Operational validity

For every arm and clip:

- successful HTTP response;
- non-empty transcript;
- no runaway output, defined as more than 4x the ElevenLabs token count for the same window or a repeated sequence that occupies at least half of the output;
- no foreign-script hallucination outside Arabic and Latin scripts;
- manual wrong-language flag for Latin text that is neither plausible English nor a phonetic learner form;
- elapsed time and estimated cost.

### Coverage

- token count by arm and clip;
- O1/O2 token-count ratio to ElevenLabs, reported but never treated as accuracy by itself;
- selected chat-anchor recovery: exact form, same lexical root/family, not recovered, or unscorable;
- Arabic/English preservation on clips containing both languages;
- filler/false-start markers retained relative to the union of engine hypotheses.

### Learner-error preservation

- every place where an OpenAI output retains a nonstandard, cut-off, or phonetic form that ElevenLabs renders as a fluent approved form;
- every place where the vocabulary prompt appears to overwrite a nonstandard learner form;
- every explicit Amal correction visible in the local context;
- classification is `supported`, `possible`, or `not assessable` unless the chat/audio supplies gold evidence.

### Prompt-effect comparison

Compare O2 directly with O1 on identical clips:

- chat-anchor recovery delta;
- blank/wrong-language/runaway delta;
- filler and false-start delta;
- number of changed outputs;
- helpful changes versus suspicious vocabulary-induced substitutions.

## Decision rule

1. ElevenLabs remains the operational primary if OpenAI has materially worse completeness, reliability, or timing/speaker functionality.
2. O2 is adopted over O1 for targeted second-pass use only if it improves anchor recovery or language fidelity without increasing suspicious normalization of learner forms.
3. No engine is declared more accurate from token count or preference alone.
4. No claim of near-perfect transcription or WER is allowed because the sample lacks a complete human verbatim gold transcript.
5. If evidence is mixed, the report must say so and prescribe the smallest next human-labeling step.

## Deliverables

- `manifest.json`: immutable source metadata, selections, prompts, hashes, and costs.
- `clips/`: 20 frozen MP3 clips.
- `results-elevenlabs.json`: identical-window extraction from the existing response.
- `results-openai-strict.json`: O1 raw results.
- `results-openai-vocab.json`: O2 raw results.
- `comparison.json`: mechanical metrics and clip-level differences.
- `anees-independent-test-report.md`: complete narrative report for Claude review.

## Known limitations registered in advance

- one mixed recording channel means no deterministic Medi/Amal separation;
- Meet chat is an authoritative topic/correction hint, not a complete verbatim transcript;
- chat-anchor sampling over-represents typed vocabulary and one lesson topic;
- adjacent windows can overlap and are not statistically independent;
- morphology/root scoring requires human judgment for some forms;
- neither Medi nor Amal is providing new blinded ratings during this automated pass;
- OpenAI receives two prompt conditions, while ElevenLabs is reused from its existing full-lesson call;
- the experiment can rank operational behavior and prompt effects, but not establish true whole-lesson WER.
