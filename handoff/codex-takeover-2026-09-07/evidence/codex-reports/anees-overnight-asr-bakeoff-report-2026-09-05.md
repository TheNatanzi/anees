# Anees overnight ASR bake-off: full findings and recommendation

**Prepared:** 2026-09-05  
**For:** Medi, Amal, Claude, and the engineer who will build Anees  
**Question:** Can Gemini, xAI, Inworld, Fish Audio, StepAudio, Cartesia, or a newly found local model produce a better evidence transcript than ElevenLabs for English–Palestinian-Arabic tutoring?  
**Priority:** Preserve what Medi actually said—including mistakes, hesitations, repetitions, false starts, and uncertain pronunciations—rather than silently repairing it.  
**Status:** Independent overnight extension to the 2026-09-04 full project analysis. All accessible and ethically authorized runs are complete. Missing-provider outputs are explicitly marked missing; none were invented.

## Executive verdict

**Do not replace ElevenLabs Scribe v2 as Anees’s primary evidence transcriber yet.**

The overnight work produced two genuinely new direct tests:

1. **Gemini 3.5 Transcribe:** 80 successful calls—four configurations across the same twenty frozen 25-second lesson clips. Its dedicated `verbatim` mode and multilingual documentation looked unusually well matched to Anees. It still produced substantially less learner evidence than ElevenLabs. The best vocabulary-biased arm recovered 14/20 credible chat-anchor families, versus 16/20 for ElevenLabs, and also inserted at least one target form at a time where the audio window did not support it. The diarization arm returned no machine-readable word/speaker annotations in this run.
2. **CrisperWhisper 2.0 Medium:** 40 successful local calls—automatic and Arabic-forced configurations—on an RTX 4070 Ti. It explicitly emits fillers, sounds, repetitions, and fragments and keeps audio local. It recovered only 7/20 and 8/20 anchor families, emitted almost no Arabic script, and produced pathological repetition loops on one automatic clip and three Arabic-forced clips.

The advertisement that triggered this review compares **text-to-speech (TTS)** prices. Anees needs **speech-to-text (STT)**. I researched the corresponding STT offerings rather than treating a speech-generation price chart as an accuracy benchmark.

The full provider verdict is:

- **ElevenLabs Scribe v2:** keep as the primary raw-evidence pass.
- **xAI Speech-to-Text:** highest-priority commercial challenger not yet run. Its explicit filler switch, optional formatting, keyterms, word confidence/timing, Arabic support, and low price make it more relevant than Fish. No authorized xAI credential exists in the available project, so a complete runner was prepared but not executed.
- **Inworld STT 1:** technically interesting because it scores well on an open English verbatim benchmark, but Arabic is experimental and its voice/content data terms are a concern. No available credential.
- **Fish Audio `transcribe-1`:** included in full. Its public controls and outside evidence make it unlikely to beat Scribe on learner-error preservation. Its terms also permit uploaded Content to train or enhance Fish and third-party models. No Fish key exists, and Amal has not knowingly accepted that specific use, so her lesson audio was not uploaded. The frozen Fish runner is ready if consent or a no-training agreement clears that gate.
- **StepAudio 2.5 ASR:** eliminated before upload; official support is Chinese and English, not Arabic.
- **Cartesia:** Sonic 3.5 in the advertisement is TTS. Current Ink 2/preview STT does not support Arabic. Legacy Ink-Whisper accepts generic Arabic but performed extremely poorly for verbatim English in the open comparison and exposes no compelling Anees-specific controls.
- **CrisperWhisper 2.0:** useful research component, not a production replacement on the observed Palestinian lesson behavior.

The strongest system remains:

> Android-compatible separate named tracks + chat → ElevenLabs Scribe v2 per track, no keyterms, verbatim enabled → immutable raw evidence → interaction-driven top-20 candidate detector → optional disagreement/phonetic evidence → Amal approval in Arabic → Medi review in Arabizi.

“Nearly perfect” is not yet a defensible claim for any engine. The missing ingredient is not another provider name; it is a small, human-labeled, genuinely verbatim Palestinian learner benchmark made from Medi and Amal’s own lessons.

## What was actually tested, researched, or eliminated

| Candidate | Direct Anees test? | Why this status is honest |
|---|---:|---|
| ElevenLabs Scribe v2 | Yes | Existing full lesson plus frozen segmented/keyterm controls |
| OpenAI `gpt-transcribe` | Yes | Two strict prompt configurations on the frozen clips |
| Speechmatics Melia 1 | Yes | Two frozen short-clip arms plus one full-lesson call |
| Gemini 3.5 Transcribe | **Yes, overnight** | Four preregistered arms × 20 clips; 80 successful calls |
| CrisperWhisper 2.0 Medium | **Yes, overnight** | Two preregistered local arms × 20 clips; 40 successful calls |
| xAI Speech-to-Text | No | No `XAI_API_KEY`; exact runner prepared |
| Inworld STT 1 | No | No `INWORLD_API_KEY`; exact runner prepared |
| Fish Audio `transcribe-1` | No lesson upload | No key; model-training-use consent gate not cleared; frozen kit prepared |
| StepAudio 2.5 ASR | No | Arabic unsupported; testing would not answer the question |
| Cartesia current Ink | No | Arabic unsupported in current Ink 2/preview |
| Cartesia legacy Ink-Whisper | No | Generic Arabic only, weak verbatim evidence, no credential, low expected value |

This distinction matters. Product documentation establishes what controls are offered; an English benchmark establishes directional verbatim behavior; only a test on Medi and Amal’s audio establishes behavior on this lesson; and only a human verbatim reference can establish accuracy.

## Combined direct result

All rows use the same twenty frozen 25-second mixed-audio windows. “Anchor” is the manual surface presence of the lesson-chat target or its lexical family. Chat is not perfectly time-aligned ground truth. Token/filler/cutoff counts are evidence-density proxies, not WER.

| System / arm | Tokens | Arabic-script tokens | Counted fillers | Cutoff markers | Anchor-family surface | Flagged runaway loops |
|---|---:|---:|---:|---:|---:|---:|
| **ElevenLabs Scribe v2 — segmented, no keyterms** | **725** | **123** | 22 | 25 | **16/20** | 0 |
| OpenAI strict prompt | 590 | 98 | 0 | 12 | 14/20 | 0 |
| Speechmatics Melia 1 automatic | 511 | 102 | 2 | 0 | 14/20 | 0 |
| Gemini automatic verbatim | 429 | 52 | 7 | 0 | 5/20 | 0 |
| Gemini `ar-EG` + `en-US` verbatim | 367 | 90 | 7 | 0 | 9/20 | 0 |
| Gemini local-vocabulary verbatim | 489 | 93 | 2 | 0 | 14/20 credible; 15/20 including one suspicious | 0 |
| Gemini diarization requested | 226 | 75 | 5 | 0 | 9/20 | 0 |
| CrisperWhisper automatic | 849; **718 excluding loop** | 0 | 47 | 150; **30 excluding loop** | 7/20 | 1 |
| CrisperWhisper forced Arabic | 997; **608 excluding loops** | 2 | 239; **40 excluding loops** | 225; **49 excluding loops** | 8/20 | 3 |

### What this table does and does not prove

It supports ElevenLabs as the best **operational evidence pass** among the directly tested configurations. It does not prove that every ElevenLabs word is correct or that Scribe has the lowest Palestinian-Arabic WER. More text can be hallucination; a vocabulary-supplied word can be a biased insertion; a cutoff count can be inflated by a decoder loop. That is why the report keeps each failure mode separate.

The comparison is nevertheless consequential:

- ElevenLabs preserves more of the conjugation drill without a runaway loop.
- The strict OpenAI pass controls output language better than earlier unprompted behavior but silently removes fillers.
- Melia produces a clean, compressed transcript and loses most explicit hesitation/cutoff evidence.
- Gemini’s explicit verbatim switch did not behave like an exact learner-evidence transcript on these clips.
- CrisperWhisper’s explicit verbatim switch preserves the *type* of signal Anees wants, but its lexical recognition and loop stability are currently unacceptable here.

## Experimental design and integrity

### Frozen source material

The overnight tests reuse the twenty 25-second MP3 windows chosen from the 2026-09-04 lesson before the prior OpenAI/ElevenLabs outputs were inspected. Selection was based on timestamped lesson-chat anchors. The windows did not move for Gemini or CrisperWhisper.

- Frozen manifest SHA-256: `D1139A06263D9A254762710BBC8D9187AC3193CD4C91AB349EAEF9E33A6CA7A4`
- Gemini protocol SHA-256: `520EE762CD84876F38DB2F08EBEE204B976BF0AFDCC859FAC7D8A0AC102C89F3`
- CrisperWhisper additive protocol SHA-256: `610DDF9E4EE7F64276D47818DAAEDCD2DD48B75A2C3BE9AF20E4F646DA69F195`
- Fish protocol SHA-256: `2F65364DF06C139B4FE61EDE322ABAB893FBF161582051395E78DF1819948259`

### Why preregistration matters

Configuration choices, retry rules, spend caps, and the interpretation rule were frozen before outputs were seen. This prevents changing a language hint, moving a clip, or choosing a favorable metric after learning which system won. Post-run anchor judgments are stored separately and labeled as transcript-surface judgments, not audio gold.

### Limitations frozen in advance

- No complete human word-for-word verbatim reference exists.
- Chat messages identify high-value teaching moments but may be posted tens of seconds late.
- Windows overlap and are not independent samples.
- The sample overrepresents a single `b-s-6` conjugation lesson.
- Audio is mixed rather than clean Medi/Amal tracks.
- Twenty clips from one lesson cannot establish population-wide Palestinian-dialect performance.
- Arabic script count measures rendering choice, not whether a Latin spelling is phonetically correct.

## New direct test 1: Gemini 3.5 Transcribe

### Why Gemini deserved a serious test

Google’s dedicated transcription documentation advertises several features that map unusually closely to Anees: default verbatim output preserving fillers, repetitions, pauses, and false starts; automatic code-switching; custom vocabulary; diarization; and word timestamps. The model supports 85+ locales, but the only listed Arabic locale is Egyptian Arabic (`ar-EG`), not Palestinian Arabic. Google also documents that custom vocabulary cannot be combined with diarization or timestamps and warns that timestamps can reduce accuracy. [Gemini transcription guide](https://ai.google.dev/gemini-api/docs/transcribe)

The key used for this test belongs to a visibly paid Tier 1 prepaid Google AI Studio project. Google states that paid-service prompts and responses are not used to improve its products. Each temporary Files API upload was explicitly deleted after its clip completed rather than relying on the documented 48-hour expiration. [Gemini API terms](https://ai.google.dev/gemini-api/terms), [Files API](https://ai.google.dev/gemini-api/docs/files), [billing](https://ai.google.dev/gemini-api/docs/billing)

### Four frozen arms

- **G0 — automatic verbatim:** auto language detection, verbatim, no vocabulary, no timing, no diarization.
- **GH — bilingual hinted:** `ar-EG` and `en-US`, verbatim, no vocabulary.
- **GV — local vocabulary:** the two language hints plus a deterministic clip-local list of at most 100 terms from nearby chat and the frozen vocabulary snapshot.
- **GD — diarization:** the two language hints plus diarization; no vocabulary or timestamps because the API disallows that combination.

Word timestamps were not enabled in the text-quality arms because Google warns they can affect accuracy. Pause analysis remains a later milestone.

### Run integrity and cost

- Intended successful outputs: 80.
- Final successful outputs: 80.
- Historical rate-limit responses: one 429, resolved by the preregistered retry.
- Temporary upload ledger rows: 21, including the retry upload.
- Uploads with `deleted=true`: 21/21.
- Estimated audio cost: `$0.16664` using Google’s `$0.005/minute` paid blended rate.
- Mean per-clip call latency: 1.715–1.847 seconds across arms.

### Aggregate behavior

| Gemini arm | Nonempty | Tokens | Arabic tokens | Fillers | Cutoffs | Credible anchors |
|---|---:|---:|---:|---:|---:|---:|
| G0 auto | 19/20 | 429 | 52 | 7 | 0 | 5/20 |
| GH bilingual hints | 20/20 | 367 | 90 | 7 | 0 | 9/20 |
| GV local vocabulary | 20/20 | 489 | 93 | 2 | 0 | 14/20 |
| GD diarization | 20/20 | 226 | 75 | 5 | 0 | 9/20 |

Every pair of Gemini configurations changed all twenty clip texts. Mean character similarity between GH and GV was only 0.6186; between GH and GD, 0.5917. The configuration is therefore not a harmless formatting preference—it materially changes the evidence.

### High-value examples

**Clip 1, `Na7el`:** automatic mode omitted the bee exchange and began with “If I want to buy more.” The bilingual arm emitted `نحل`. The vocabulary arm produced “Oh my god, bees. What’s bees? Na7el. Na7el.” This shows vocabulary can recover a teaching target, but it does not tell us whether every supplied spelling is acoustically earned.

**Clip 3, `Basa6`:** automatic mode and vocabulary mode retained `basat`/`basa6ni`-like forms; the bilingual control omitted them and retained only the English explanation. Language hints alone did not guarantee Arabic evidence.

**Clip 14, `Buset`:** only the vocabulary arm emitted “Buset.” Earlier timing evidence shows that word was spoken about 42 seconds before the frozen window; the window contains a different `basat` discussion. This is the cleanest observed example of vocabulary poisoning: a plausible expected word is inserted at the wrong time.

**Clip 16, `Enbasa6ti fi/bi el-7afle`:** the bilingual and diarized arms retained Arabic-family material; the vocabulary arm returned the expected Arabizi phrase but also anticipated the next exercise. Again, surface recovery alone is not proof.

**Diarization failure in this run:** GD returned zero `word_info` annotations and zero speaker labels across all twenty clips. Text was also aggressively compressed—226 tokens total—and sometimes fused, such as `نحالينحالي`. This is an operational failure of the exact tested configuration, not proof that Google diarization can never work.

### Gemini decision

Gemini should not replace Scribe as the raw evidence layer. Its vocabulary mode may be useful as a **secondary hypothesis generator**, but only when the unprompted transcript and audio remain visible and supplied-word insertions receive an explicit bias warning. The current diarization result reinforces the separate-track capture decision.

## New direct test 2: CrisperWhisper 2.0 Medium

### Why this was more relevant than most screenshot vendors

CrisperWhisper 2.0 was released specifically to separate “what was said” from “what was meant.” It has explicit verbatim and intended modes, marks fillers/repetitions/fragments/vocal sounds, produces word timing, handles long-form audio, and runs locally. The standard weights are published under a non-commercial research license; production/commercial use requires a licensing review. [CrisperWhisper model overview](https://nyra-labs.com/crisperwhisper), [model card](https://huggingface.co/nyralabs/CrisperWhisper2.0_medium), [paper](https://arxiv.org/abs/2607.18934)

This is exactly the conceptual control the user originally wanted: “turn off correction.” Unlike a prompt on a general transcriber, CrisperWhisper was trained with an explicit output-policy signal. That justified a direct test even though no Palestinian benchmark was found.

### Frozen local setup

- Model: `nyralabs/CrisperWhisper2.0_medium`.
- Package: `crisperwhisper 2.0.2`.
- Backend: Transformers/PyTorch.
- Hardware: NVIDIA RTX 4070 Ti, CUDA available.
- PyTorch: `2.6.0+cu124`; Transformers: `4.57.6`.
- Audio uploaded to a provider: **no**.
- Arms: automatic language and forced `language="ar"`, both default verbatim with word timestamps.
- No hotwords: the standard model card documents hotword boosting only for Pro models.

### Aggregate behavior

| Arm | Tokens | Arabic tokens | Fillers | Cutoffs | Anchors | Loop clips | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| CW_AUTO | 849; 718 excluding loop | 0 | 47 | 150; 30 excluding loop | 7/20 | 1 | 3.302 s |
| CW_AR | 997; 608 excluding loops | 2 | 239; 40 excluding loops | 225; 49 excluding loops | 8/20 | 3 | 12.231 s |

The forced-Arabic and automatic outputs differed on all twenty clips, with mean character similarity 0.5979.

### What worked

- It consistently emitted canonical tags such as `[UH]`, `[UM]`, `[breath]`, and `[laughter]`.
- It preserved useful partial forms on some drills: `Babsat`, `basa-`, `basat-`, `Banbassat`, `Nabassat`, and `Bitinbissiti`-like surfaces.
- It ran locally, avoiding a new audio-data processor.
- Outside the flagged loops, it exposed more fillers/cutoff symbols than the other non-Eleven challengers.

### What failed

- Automatic mode emitted zero Arabic-script tokens; forced Arabic emitted only two. Latin output is not automatically bad for Medi, who reads Arabizi, but most spellings were English phonetic guesses rather than stable project Arabizi.
- Many Palestinian forms became English meanings. For example, clip 6 reduced the target to “it makes me happy.”
- It recovered fewer than half the anchor families in either arm.
- It hallucinated/looped on four arm-clips:
  - CW_AUTO clip 2 repeated `ba-` roughly a hundred times.
  - CW_AR clip 7 repeated alternating `b-` and `[UH]` through much of the output.
  - CW_AR clip 8 repeated `b-` through most of the output.
  - CW_AR clip 18 emitted a long `[UH]`/`[UM]` loop.
- CW_AR clip 11 emitted repeated `[fart]` sound labels where the automatic arm preserved conjugation-like surfaces—an obvious semantic failure in this lesson context.

The model advertises looping-hallucination mitigation, so this observed behavior is important. It may reflect a model/backend/language interaction or genuinely difficult audio, but the user-facing consequence is the same: raw counts from those clips cannot be trusted.

### CrisperWhisper decision

Do not make it Anees’s primary. Keep it as a research option for **selected English-heavy clips or transcript-conditioned “verbatimize” experiments**, never as unreviewed Palestinian truth. `verbatimize` could take a trusted clean transcript and attempt to reinsert audible disfluencies, but because that output is conditioned on the supplied words, it must remain an evidence-fusion arm and cannot independently validate lexical accuracy.

## Fish Audio: full finding and why no lesson audio was sent

### Product fit

Fish’s public ASR is beta `transcribe-1` through `POST /v1/asr`. Its documented inputs are the audio file, one optional language hint, and whether to return timestamped segments. The response contains one transcript, duration, segments, and one detected file-level language. [Fish STT endpoint](https://docs.fish.audio/api-reference/endpoint/openapi-v1/speech-to-text)

The public schema does **not** document:

- prompts or style instructions;
- keyterms/custom vocabulary;
- a verbatim/filler/disfluency switch;
- phonetic output or uncertain/nonword notation;
- word-level confidence or word timestamps;
- alternatives;
- diarization, speaker count, voiceprints, or named-speaker enrollment;
- a Palestinian/Levantine dialect selector;
- a simultaneous `ar,en` language hint.

That makes Fish structurally less controllable than xAI and less aligned with Anees’s evidence requirement than ElevenLabs.

### Price

Fish publishes `$0.36` per processed audio hour, billed by the second. The two frozen 20-clip arms would cost about `$0.10`. A 70-minute two-track lesson would cost about `$0.84`. [Fish pricing](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits)

### Outside verbatim evidence

Nyra’s open English benchmark reports Fish Audio ASR at 49.7% disfluency F1, 30.5% filler F1, 0% vocal-sound F1, 60.1% cutoff F1, 82.1% repetition F1, and 5.9% verbatim WER. On the identical English set, ElevenLabs Scribe v2 scored 90.3%, 95.5%, 83.4%, 80.1%, 87.9%, and 3.2%, respectively. This is relevant to error preservation but not Palestinian accuracy. [Nyra benchmark](https://nyra-labs.com/research/nyra-verbatim-speech-benchmark), [open evaluator and cached predictions](https://github.com/nyrahealth/nyra_verbatim_speech_benchmark)

### Privacy gate

Fish’s current Terms permit using uploaded Content to develop, train, or enhance Fish and third-party AI/ML models. Its privacy policy also contains broad retention language. That is a materially different question from ordinary processing of a tutoring recording. Amal’s voice is her data; “include Fish” is not the same as her informed acceptance of third-party model-training use. [Fish Terms](https://fish.audio/terms/), [Fish privacy policy](https://fish.audio/privacy/)

No `FISH_AUDIO_API_KEY` was available. More importantly, even if a key had appeared, the protocol required one of:

1. Amal explicitly agrees, after being told that Fish’s public terms permit this training use; or
2. Fish supplies a binding no-training/ZDR arrangement for the account.

Therefore no lesson audio was sent. This is not a missing-analysis excuse: the complete research, two-arm preregistration, runner, manual-recovery template, and analyzer are in the evidence bundle.

### Fish decision

Fish is not the next best bet. If the consent/key gate is later cleared, run the frozen test for completeness—but prioritize xAI first. Fish would need a surprisingly large Palestinian-specific acoustic advantage to overcome its weak verbatim controls, outside filler result, lack of word/speaker evidence, higher price than Scribe, and privacy posture.

## xAI Speech-to-Text

xAI is the most promising untested commercial challenger found in this extension.

Its current REST/streaming interface documents:

- Arabic support;
- word-level timestamps and confidence;
- speaker diarization and multichannel mode;
- up to 100 keyterms;
- explicit `filler_words=true`—the default otherwise removes fillers;
- `format=false` to avoid formatting/normalization;
- VAD threshold `0` to avoid discarding quiet audio;
- REST pricing of `$0.10/hour` and streaming pricing of `$0.20/hour`.

[xAI STT overview](https://docs.x.ai/developers/models/speech-to-text), [capability guide](https://docs.x.ai/developers/model-capabilities/audio/speech-to-text), [REST schema](https://docs.x.ai/developers/rest-api-reference/inference/speech-to-text)

xAI says API data is not used to train models without explicit permission; its security FAQ describes encrypted default audit retention and account-dependent zero-data-retention behavior. That exact account setting must be verified before production. [xAI security FAQ](https://docs.x.ai/developers/faq/security)

The Nyra English benchmark reports xAI at 73.9% disfluency F1 and 84.4% filler F1—behind ElevenLabs but ahead of Fish. Combined with explicit controls and generic Arabic support, this makes xAI the rational next `$0.03` frozen-sample test once a project key exists. The prepared runner uses no language hint, `filler_words=true`, `format=false`, diarization off, multichannel off, and `vad_threshold=0` so the base text pass is not vocabulary-contaminated.

## Inworld STT 1

Inworld exposes synchronous and WebSocket transcription with `inworld/inworld-stt-1`, word timestamps, speech events, and an optional Voice Profile describing age, pitch, emotion, style, and accent. Voice Profile is descriptive metadata, not reliable persistent enrollment of Medi versus Amal. [Inworld STT overview](https://dev.docs.inworld.ai/stt/overview), [quickstart](https://dev.docs.inworld.ai/stt/quickstart)

The critical language fact is that English is listed as available while Arabic is listed as **experimental**. No first-party filler/verbatim control comparable with xAI’s is documented for the synchronous endpoint. The two prepared arms are therefore automatic and forced generic `ar`; neither assumes Palestinian support.

The Nyra English benchmark gives Inworld 84.4% disfluency F1 and 95.2% filler F1, close to Scribe on fillers but with only 10.7% vocal-sound F1. It is useful directional evidence from English, not evidence about Medi.

Inworld’s privacy policy describes collecting content and voice recordings and using data for research/development, including model training; it also contains biometric-information retention language. Published zero-data-retention positioning is enterprise-priced. This is not an economical privacy match for a small tutoring workflow without a clearer contract. [Inworld pricing](https://inworld.ai/pricing), [privacy policy](https://inworld.ai/privacy)

No authorized key was available, so the exact reproducible two-arm runner is included but not executed.

## StepAudio and Cartesia

### StepAudio 2.5

The screenshot’s StepAudio entry is TTS. The relevant `stepaudio-2.5-asr` is a streaming recognizer whose official overview says it supports Chinese and English with inverse text normalization. It has hotwords and a default normalization behavior, but no Arabic. [StepFun model overview](https://platform.stepfun.ai/docs/en/guides/models/overview), [ASR schema](https://platform.stepfun.ai/docs/en/api-reference/audio/asr-sse)

It was correctly eliminated before upload. A low price cannot compensate for missing the target language.

### Cartesia Sonic / Ink

Sonic 3.5 is TTS. Cartesia’s current STT line is Ink. Current Ink 2 is English-focused, and the newer preview language set still excludes Arabic. The older batch `ink-whisper` endpoint accepts generic `ar`, long files, and word timestamps. [current Cartesia STT](https://docs.cartesia.ai/build-with-cartesia/stt/latest), [older STT models](https://docs.cartesia.ai/build-with-cartesia/stt/older-models), [batch endpoint](https://docs.cartesia.ai/api-reference/stt/transcribe)

The Nyra English benchmark places legacy Ink-Whisper last among the listed systems: 7.6% disfluency F1, 6.0% filler F1, 0% vocal-sound F1, 32.5% cutoff F1, 3.7% repetition F1, and 10.4% verbatim WER. That does not establish Arabic accuracy, but it is strong evidence that legacy Ink-Whisper is mismatched to Anees’s “preserve the mess” objective.

Cartesia’s public terms permit model-training use of inputs/outputs, and its documented ZDR is enterprise. No direct test was justified during this run. [Cartesia Terms](https://www.cartesia.ai/legal/terms), [privacy](https://www.cartesia.ai/legal/privacy), [ZDR](https://docs.cartesia.ai/enterprise/zero-data-retention)

## Independent outside verbatim benchmark

Nyra’s benchmark is the best directly relevant public framework found for the “do not clean my mistakes” requirement. It uses paired verbatim and intended transcripts and separately scores fillers, vocal sounds, cutoffs, repetitions, and verbatim WER. Its English set contains 4,957 clips and 6,120 typed disfluencies; German adds 202 clips and 1,385 disfluencies. Predictions and the evaluator are public. [method and results](https://nyra-labs.com/research/nyra-verbatim-speech-benchmark), [repository](https://github.com/nyrahealth/nyra_verbatim_speech_benchmark)

### English leaderboard subset

| Model | Disfluency F1 | Filler F1 | Sound F1 | Cutoff F1 | Repetition F1 | vWER ↓ |
|---|---:|---:|---:|---:|---:|---:|
| CrisperWhisper 2.0 Pro | 93.2 | 95.7 | 94.8 | 90.7 | 88.3 | 3.0 |
| CrisperWhisper 2.0 standard | 90.7 | 94.3 | 83.5 | 89.3 | 87.8 | 3.6 |
| **ElevenLabs Scribe v2** | **90.3** | **95.5** | **83.4** | **80.1** | **87.9** | **3.2** |
| Inworld STT | 84.4 | 95.2 | 10.7 | 84.8 | 86.8 | 4.0 |
| xAI Grok STT | 73.9 | 84.4 | 0.0 | 60.3 | 83.4 | 4.7 |
| Fish Audio ASR | 49.7 | 30.5 | 0.0 | 60.1 | 82.1 | 5.9 |
| Cartesia Ink-Whisper | 7.6 | 6.0 | 0.0 | 32.5 | 3.7 | 10.4 |

### Required caveats

- Nyra makes CrisperWhisper, so it has an interested-party conflict even though the artifacts are open.
- The human-labeled public sets are English and German, not Arabic.
- The ten-language average on the Crisper product page uses synthetic verbatim data for eight non-English/German languages.
- It measures transcript policy and recognition on its datasets, not beginner Palestinian speech.
- The direct Anees test contradicts any lazy inference that Crisper’s English leaderboard win automatically transfers to this lesson.

The benchmark is valuable because it independently confirms that Fish, xAI, Inworld, and Eleven differ substantially in disfluency policy. It cannot pick the Palestinian winner by itself.

## Prior direct evidence carried forward

The preceding full analysis remains part of this decision:

- ElevenLabs full-lesson extraction: 714 tokens, 82 Arabic-script tokens, 21 fillers, 19 cutoff markers, 16/20 anchors.
- ElevenLabs segmented/no-keyterm: 725, 123, 22, 25, 16/20.
- OpenAI strict prompt: 590, 98, 0, 12, 14/20.
- OpenAI vocabulary prompt: 593, 83, 0, 7, 13/20.
- Speechmatics Melia short: 511, 102, 2, 0, 14/20.
- Speechmatics Melia full-context windows: 509, 124, 3, 0, 15/20; its full lesson divided two people into six anonymous speaker clusters.

An independent 2026 commercial code-switching paper evaluated Egyptian-Arabic/English, Saudi-Arabic/English, Persian/English, and German/English and ranked ElevenLabs first overall. It does not include Palestinian learners or error-preservation scoring, but it agrees directionally with the local decision. [Abdoli et al., 2026](https://arxiv.org/abs/2605.19069)

## The core scientific conclusion: a phonetic “off switch” is only partly possible

The original intuition was right: ordinary transcription tends to repair speech. The wrong part is assuming that a prompt can fully disable this.

Modern ASR combines acoustic evidence with learned language probabilities. If Medi produces something between a known word and a nonword, the decoder may output:

- the intended correct word;
- a different plausible Arabic word;
- an English look-alike;
- a rough Latin phonetic spelling;
- a filler/fragment;
- nothing.

Gemini demonstrates that an explicit `verbatim` flag does not guarantee Anees-grade preservation. CrisperWhisper demonstrates that a model truly optimized for explicit verbatim output can expose fragments and fillers while still failing lexical recognition or hallucinating repetitions. “More phonetic-looking” is not synonymous with “more accurate.”

The safe representation is three-layered:

1. **Observed evidence:** immutable provider output, words/timestamps/confidence where available, model/config/version, source-audio hash.
2. **Phone hypothesis:** optional, only for selected known-target clips; never shown as certainty.
3. **Canonical target:** Amal-approved Palestinian Arabic plus Medi-facing Arabizi.

An error is the relationship between those layers and the audio. The canonical target must never overwrite the observation.

## Palestinian and learner-speech resources

The overnight review reconfirmed that there is no turnkey repository that solves adult Palestinian conversational learner-error detection. Useful building blocks do exist:

- **Maknuune:** open Palestinian lexicon with more than 36,000 entries, approximately 17,000 lemmas and 3,700 roots, including diacritized Arabic, English glosses, and phonological transcription. It can seed a pronunciation dictionary but cannot override Amal’s lesson-specific rules. [Maknuune](https://aclanthology.org/2022.wanlp-1.13/)
- **Open Universal Arabic ASR Leaderboard:** includes Palestinian Casablanca data among several dialect resources; reported open-model error rates remain far from “nearly perfect” and the task is ordinary orthographic ASR, not learner-error preservation. [Interspeech 2025 paper](https://www.isca-archive.org/interspeech_2025/wang25_interspeech.pdf)
- **NADI multidialect ASR:** additional evidence that cross-dialect Arabic recognition remains difficult. [NADI 2025](https://aclanthology.org/2025.arabicnlp-sharedtasks.99/)
- **Tactical Language Training System:** directly studied beginning learners of Levantine Arabic and used expected error grammars/noisy-channel reasoning plus learner history and pedagogical importance. The enduring lesson is architectural: target context and modeled learner errors belong beside ASR. [Sethy et al., 2005](https://www.isca-archive.org/interspeech_2005/sethy05b_interspeech.pdf)
- **Native/non-native Levantine comparison:** alignment/DTW between learner and reference utterances maps naturally to Medi attempting a form and Amal immediately modeling it. [Lee and Glass, 2013](https://www.isca-archive.org/slate_2013/lee13b_slate.html)
- **Montreal Forced Aligner, Kaldi GOP, CTC-based GOP, Allosaurus:** useful experimental alignment/phone components, but none is validated as an adult Palestinian free-conversation judge. [MFA](https://montreal-forced-aligner.readthedocs.io/en/v3.4.1/user_guide/index.html), [Kaldi GOP](https://github.com/kaldi-asr/kaldi/blob/master/src/bin/compute-gop.cc), [CTC-GOP](https://github.com/frank613/CTC-based-GOP), [Allosaurus](https://github.com/xinjli/allosaurus)

Language-learning repositories such as pronunciation-coach demos are useful for UI and workflow patterns, not as accuracy evidence. Anees’s defensible advantage will come from Amal-confirmed labels, exact lesson context, separate speaker tracks, and a tightly versioned Palestinian vocabulary—not from cloning a generic language-learning app.

## Recommended production design

### 1. Capture solves speaker identity

Use one Android-compatible lesson room that records synchronized **separate local tracks** named `Medi` and `Amal` and preserves chat. The prior full report recommends a five-minute Ennuicastr continuous-mode trial, then one shadow lesson. Do not ask an anonymous diarizer to rediscover identities that capture can know exactly.

Practical rules:

- headset for both speakers;
- power connected;
- browser foreground and screen awake on Android;
- one call application only, avoiding microphone/audio-focus competition;
- short verbal identity check at the start;
- backup plan documented before the first full lesson;
- verify the download contains two named tracks and machine-readable chat.

### 2. Immutable primary transcript

Transcribe each named mono track separately with ElevenLabs Scribe v2:

- `no_verbatim=false`;
- diarization off;
- word timestamps on;
- no keyterms on the primary pass;
- exact provider/model/config stored;
- raw JSON and audio hashes immutable.

Keyterms belong only in a secondary hypothesis arm. The overnight Gemini test makes the reason concrete: expected words can appear where the audio does not support them.

### 3. Merge by time, never by rewritten prose

Merge Medi and Amal tokens using timestamps. Preserve overlaps. Store silence intervals on each track for the later pause milestone. Do not have an LLM rewrite the merged evidence into a fluent dialogue before candidate extraction.

### 4. Detect learning events from interaction

Prioritize observable events:

1. Medi explicitly says he forgot a word.
2. Medi asks what a word means or how to say it.
3. Amal immediately corrects or recasts him.
4. Amal posts a form in chat near the speech.
5. Medi repeats or self-repairs a form.
6. Two unprompted ASR systems materially disagree on a high-value short window.
7. Later: an unusually long within-turn pause, after personal calibration.

A suspicious word alone is not enough to accuse Medi of an error.

### 5. Enforce the vocabulary policy after recognition

Allowed without flagging:

- exact list words;
- ordinary Palestinian clitics/inflections and productive morphology;
- English code-switches;
- names, fillers, and natural loanwords;
- forms Amal adds during the grace period.

Out-of-list forms are retained and flagged `OOV/uncertain`; they are never silently replaced. Version the vocabulary snapshot used for each lesson. Amal’s post-lesson additions should affect interpretation/review, not rewrite the primary ASR evidence.

### 6. Top-20 review inbox

Each candidate card should show:

- a 5–12 second audio clip;
- speaker name from the capture track;
- raw transcript and uncertainty;
- Amal-facing Arabic;
- Medi-facing Arabizi;
- proposed target, error type, and evidence reason;
- one-tap `correct`, `edit`, `valid variant`, `not an error`, and `skip` actions.

Keep the full evidence available, but present only the twenty highest-value events. Measure review time rather than promising it.

### 7. Pause analysis later

Pause length is only meaningful on Medi’s clean track. A silence may mean word retrieval, listening to Amal, reading chat, thinking about content, network lag, or emphasis. Label causes first, then calculate a personal threshold. Do not use a generic fluency norm to score him.

## Cost sketch for a 70-minute, two-track lesson

Approximate transcription-only costs at current listed rates:

| Engine | Two 70-minute tracks | Comment |
|---|---:|---|
| ElevenLabs Scribe v2 | about `$0.51` | Current primary |
| xAI REST STT | about `$0.23` | Best untested next candidate |
| Inworld on-demand | about `$0.35` | Privacy/language caveats |
| Fish Audio | about `$0.84` | Higher cost and consent issue |
| Gemini Transcribe | about `$0.70` | Direct result does not justify switch |
| CrisperWhisper | local compute + license | Standard weights are research-only |

Using the prior recommended continuous separate-track capture mode, the total capture-plus-Scribe estimate remains under the user’s stated `$3` per lesson ceiling. Cost is not the bottleneck; evidence quality and review efficiency are.

## The benchmark Anees must build next

### Gold set design

Start with **20 candidates from each lesson**, as requested. Do not demand 100 labels at once. After five lessons, the project will have roughly 100 high-value items plus a small sample of rejected events.

For each item, Amal should label without seeing provider identity:

- exact audible words, including fillers/repetitions/fragments;
- intended/canonical Palestinian form;
- valid variant versus error;
- error type: vocabulary gap, pronunciation, morphology, grammar, comprehension, fluency, or ASR-only error;
- pedagogical importance;
- speaker and timestamps;
- whether chat was a correction, expansion, or unrelated late note;
- confidence;
- review duration and replay count.

### Metrics that match the goal

Report separately:

- verbatim WER/CER under an agreed Arabic/Arabizi normalization;
- target-form recall;
- filler, repetition, and cutoff precision/recall;
- learner-event recall and precision;
- unsupported expected-word insertion rate;
- speaker attribution accuracy;
- fraction of candidate cards caused only by ASR error;
- top-20 recall, using a small random sample of rejected events;
- Amal median and p90 review time;
- number of plays/edits per item.

### Replacement rule

Freeze this before testing xAI or another provider:

> Replace Scribe only if the challenger improves held-out learner-event recall or verbatim accuracy without increasing unsupported insertions, speaker errors, operational failures, privacy risk, or Amal review time beyond the agreed tolerance.

Clean prose and lower cost alone do not qualify.

## Ordered next actions

1. **Run the five-minute Android separate-track capture pilot.** Verify reconnect behavior, quiet starts, continuous audio, named tracks, and chat export.
2. **Build the immutable Scribe-per-track ingestion path.** No keyterms in the primary pass.
3. **Build the top-20 evidence inbox before adding more engines.** The bottleneck is turning audio into correct learning events, not producing another full transcript.
4. **Collect 20 Amal-reviewed items from each of five lessons.** Time the review from the first lesson.
5. **Acquire an xAI project key only if a blind challenger test is still wanted.** Run the prepared frozen base arm first; do not add vocabulary until the unprompted output is scored.
6. **Treat Fish as optional, not urgent.** Proceed only after informed acceptance of its training terms or a no-training agreement.
7. **Keep Inworld behind the same privacy gate** and remember Arabic is experimental.
8. **After 30–60 minutes of exact Medi labels, test Azure `ar-PS` Custom Speech** as the personalized path; hold out evaluation clips permanently.
9. **After 30–50 known-target attempt/reference pairs, test alignment/GOP/phone hypotheses.** Ship only if they improve ranking against Amal’s labels.
10. **Add pause analysis after separate tracks and cause labels exist.**

## Questions Claude should use to challenge this report

1. Recompute every aggregate from the included JSON. Do token, filler, and cutoff regexes handle bracketed tags consistently?
2. Listen to all twenty clips blind. Which anchor-surface judgments change, and why?
3. Can any line be called “correct” without a human verbatim reference?
4. Is clip 14 Gemini `Buset` definitely vocabulary poisoning after listening and checking the full-lesson timeline?
5. Why did Gemini’s diarization request return no `word_info` objects? Was the exact client/API feature shape valid for that model release?
6. Does enabling Gemini word timestamps change text quality enough to reverse the result?
7. Why did `gemini-3.5-transcribe` report zero output tokens in its usage object despite returning text? Do not infer zero output cost without resolving this.
8. Can CrisperWhisper’s looping be reproduced with its CTranslate2 backend, another model size, or the documented hallucination thresholds?
9. Did the Crisper Transformers warning about attention masks affect reliability? Re-test one frozen copy only after preregistering the compatibility change.
10. Does Crisper forced `ar` really set the decoder language in package 2.0.2, given that it emitted almost all Latin text?
11. Does a transcript-conditioned Crisper `verbatimize` arm add real disfluencies or merely decorate Scribe’s lexical errors?
12. Is Nyra’s interested-party benchmark reproducible from cached predictions at the cited commit?
13. Do Nyra’s English/German results have any predictive value for Palestinian code-switching beyond transcript-policy direction?
14. Is xAI’s `format=false` behavior truly non-normalizing for Arabic, or only punctuation/ITN control?
15. Can xAI auto-detect language within a single utterance, or only return one file-level language?
16. What exact retention/ZDR flag will the xAI response/account expose before Amal’s audio is sent?
17. Does Inworld’s experimental Arabic preserve code-switches, or does forcing `ar` damage English?
18. Can Inworld provide a no-training agreement at a price consistent with this personal project?
19. Are Fish’s Terms still identical on the date of any future test? Capture the accepted version and consent record.
20. Is Fish segment timing sufficiently precise to link corrections when it lacks word timing?
21. Does legacy Cartesia Ink-Whisper’s Arabic accuracy justify even a low-priority test despite its disfluency policy?
22. Are there any current Arabic-capable CrisperWhisper Pro hosting/licensing terms that materially change the local result?
23. Does Ennuicastr reliably export named tracks and chat from Medi’s exact Android device after reconnect or browser suspension?
24. What prevents the vocabulary grace-period update from contaminating raw transcript evidence?
25. How are legitimate Palestinian variants represented when Amal, the learned list, and Maknuune disagree?
26. What sample of rejected events is reviewed so top-20 recall can be measured rather than assumed?
27. What transaction boundary prevents a job from publishing/emailing “success” before audio, transcript, review data, and GitHub deployment are durable?
28. Can Amal actually complete twenty decisions in five minutes on her usual device? Report median and p90, not anecdotes.
29. What privacy/consent message do Medi and Amal see, and how does either person delete a lesson?
30. What objective held-out threshold would falsify the current ElevenLabs recommendation?

## Final conclusion

The overnight evidence strengthens rather than weakens the prior recommendation.

Gemini’s new dedicated transcription model had the right documentation but did not preserve this lesson nearly as well as Scribe. Vocabulary bias recovered more expected forms, yet also demonstrated the exact failure Anees must avoid: inserting a lesson word because it was expected rather than because it was present. CrisperWhisper’s explicit verbatim training proved that filler/fragment control is technically possible, but on this Palestinian-English lesson it lost most target forms and produced dangerous repetition loops. Fish offers fewer useful controls, weaker outside verbatim behavior, higher per-hour cost than Scribe, and unacceptable default training-use ambiguity for Amal’s voice. StepAudio and current Cartesia fail the target-language gate. xAI is the only newly surveyed commercial option that deserves priority over Fish for the next controlled run; Inworld is second, subject to privacy and experimental-Arabic caveats.

The project should stop searching for a magical transcript that is simultaneously exact, phonetic, pedagogically correct, speaker-aware, dialect-constrained, and fully automatic. Build an evidence-preserving system:

> Separate named tracks + chat → Scribe raw evidence → ranked correction interactions → short audio-linked review → Amal-confirmed Palestinian target → Medi-facing Arabizi → accumulating personal gold set.

That system can reach the practical goal even before an engine reaches “nearly perfect.” It also creates the only dataset capable of proving when a future engine actually becomes better.

## Evidence bundle contents

The companion ZIP contains:

- frozen manifests and protocol hashes;
- Gemini runner, raw result JSON, comparison JSON, all clip texts, and upload-deletion ledger;
- CrisperWhisper preregistration, runner, raw local results, analysis, and all clip texts;
- xAI and Inworld ready-to-run scripts;
- Fish research notes, preregistration, runner, analyzer, and manual-recovery template;
- the combined comparison and evidence-gap matrix;
- claim-to-source ledger;
- SHA-256 inventory.

The earlier 2026-09-04 full deep-research report remains the detailed source for the project audit, Android capture survey, prior OpenAI/ElevenLabs/Speechmatics clip appendix, and implementation findings.
