# ASR methods for a non-native learner's code-switched Levantine Arabic (Anees lesson pipeline)

Researched 2026-10-10. Scope: methods and factors to test for the transcription accuracy of Medi's speech (Farsi L1, Levantine/Palestinian Arabic L2, English code-switching, one track per speaker from Recall.ai). Project baseline, as given by the caller: ElevenLabs Scribe v2 runs first, then Gemini 3.8 Flash re-hears each line with context, 3 runs, 2-of-3 vote. On 63 learner-corrected moments, Gemini with context heard 53, Deepgram nova-3 21, gpt-audio 24 (11 of those 24 "fixed" learner errors) and ElevenLabs 4. ElevenLabs agreed with itself across runs only 36.5% of the time. In 12 of 27 checked Gemini changes, the change hid a real learner mistake.

Note on sourcing: items marked "(known reference, not fetched this session)" are well-known papers cited from prior knowledge. Their URLs are real, but I did not re-read them in this session.

## 1. Ordering and fusion: LLM first, classic ASR first, or parallel fusion; ROVER, GER, N-best, LLM tie-breaking

### Takeaway
The literature trend for 2024-2026 is to run several ASR systems in parallel and have an LLM fuse them, preferably an LLM that also hears the audio. It replaces ROVER-style voting and beats text-only correction. Text-only generative error correction (GER) has a documented over-correction failure: it pushes transcripts toward fluent, written-style language. For a learner, that is exactly the "hides real mistakes" problem Anees measured. No paper tested GER on learner speech with the goal of keeping grammatical errors, so this is a real gap that Anees has to measure itself.

### Cited Findings
- HyPoradise (NeurIPS 2023): an open benchmark of over 316k–334k N-best/reference pairs (the count differs by version) for LLM generative error correction. With fine-tuning, LLM correction can beat the oracle WER of the N-best list, meaning the ceiling of any rescoring or reranking. With good prompts, the LLM can even recover tokens that appear in no hypothesis — [HyPoradise arXiv 2309.15701](https://arxiv.org/pdf/2309.15701); [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/6492267465a7ac507be1f9fd1174e78d-Abstract.html)
- Recovering tokens that are in no hypothesis is also how GER can invent the correct form. That same ability is the risk for learner speech (inference; see section 3).
- Multi-pass augmented GER (MPA GER, Japanese, 2024): combines hypotheses from several ASR systems, has several LLMs correct them, then merges the outputs. The authors note that at low error rates, conventional ROVER and earlier LLM correction stop helping — [arXiv 2408.16180](https://arxiv.org/html/2408.16180v2)
- Interspeech 2025, "Better Pseudo-labeling with Multi-ASR Fusion and Error Correction by SpeechLLM": a prompt-driven framework post-processes ensemble ASR outputs with a text LLM or a speech LLM, "replacing voting or other arbitration logic". The abstract reports significant gains over traditional methods but gives no numbers — [arXiv 2506.11089](https://arxiv.org/abs/2506.11089)
- A 2025 approach aligns the hypotheses of 3 ASR models into textual confusion networks that mark where they disagree. A fine-tuned Llama 3.2 1B then weighs them and corrects end to end, replacing hand-built ROVER heuristics (summarised in search results around [arXiv 2603.16411](https://arxiv.org/pdf/2603.16411); exact paper attribution not verified)
- Over-correction: text-only LLM correction makes many unnecessary edits and steers the transcript "more towards written language, instead of a verbatim transcript" (Pu et al., [arXiv 2409.09554](https://arxiv.org/html/2409.09554v2)). The Hitachi group links over-correction to text-only correction that ignores phonetic cues. Their fix feeds N-best hypotheses plus phonetic context to the model — [arXiv 2505.17410](https://arxiv.org/pdf/2505.17410)
- PMF-CEC (2025) adds phoneme-augmented multimodal fusion with "error-specific selective decoding", correcting only where an error is detected — [arXiv 2506.11064](https://arxiv.org/pdf/2506.11064)
- Scribie leaderboard (March 2026) uses Gemini Pro as a proofreader on top of ASR output. Its best configuration reached 6.87% normalised WER, but on only 8 English files — [Scribie leaderboard](https://scribie.com/leaderboard)
- Run-to-run instability of audio LLMs: two runs of Gemini 1.5 Pro on the same news audio differed in 441 places, from punctuation to invented or dropped passages. Gemini also "corrected" speech toward statistically likelier words — [GDELT blog](https://blog.gdeltproject.org/from-lsms-to-lmms-for-asr-evaluating-geminis-performance-at-transcribing-an-evening-news-broadcast)

### Inferences
- Anees's current order (classic ASR first, then an audio LLM with context) matches the "speech LLM as fuser" design that the 2025 work favours. The weak point is that the fuser sees only one ASR hypothesis, from ElevenLabs, which is the one least repeatable and least accurate on learner moments (4/63).
  - Test A: give Gemini the hypotheses of ElevenLabs, Deepgram nova-3 and gpt-audio, plus a ROVER-style alignment marking where they disagree, and the audio. Compare against the current single-hypothesis prompt on the 63 moments. Score two things: hits, and learner-error preservation.
- Test B (order): the context-free audio LLM transcribes first, then classic ASR serves only for timestamps and alignment. Compare with the current order. Expect the LLM-first order to keep more learner errors if no tutor context is given.
- Test C (restricted edits, the "selective decoding" idea): only let the LLM change words where the ASR systems disagree or the ASR confidence is low. That limits over-correction at places where every system already agrees.
- Test D (classic ROVER baseline): word-level majority vote of ElevenLabs, Deepgram and gpt-audio, with no LLM. This floor shows how much the LLM itself adds.
- Within N-best rescoring, the LLM picks one of the candidates and cannot invent a form. That is safer for keeping learner errors, at the cost of recall. Worth testing where an engine exposes alternatives; most commercial APIs expose only 1-best, though Deepgram exposes alternatives (vendor docs, not checked this session).

### Gaps
- No published numbers compare LLM-first vs ASR-first ordering for L2 or dialectal speech.
- No study measures how often GER erases learner errors. Anees's own 12/27 figure is likely the only data.
- I could not get the WER tables of 2506.11089 or the confusion-network paper.

## 2. State of the art: non-native/L2 ASR, dialectal Arabic (Levantine), Arabic-English code-switching

### Takeaway
Levantine is still among the hardest Arabic dialects for open models. On Cohere's July 2026 evaluation, the best Levantine WER was 39.8% and Whisper v3 scored 58.6%. Conversational multi-dialect Arabic (Casablanca) is at around 50–72% WER for open models. Code-switched AR-EN WER is around 28–41%. On a 2026 commercial code-switching benchmark, ElevenLabs Scribe v2 had the lowest overall WER (13.2%), but that benchmark covers Egyptian and Saudi Arabic, not a non-native speaker. Learner (L2) speech adds its own failure: ASR and LLMs normalise toward native, correct forms.

### Cited Findings
- Open Universal Arabic ASR Leaderboard (ELM, Dec 2024; Interspeech 2025): zero-shot multi-dialect benchmark over SADA, Common Voice, MASC clean and noisy, MGB-2 and Casablanca, reporting WER and CER — [arXiv 2412.13788](https://arxiv.org/pdf/2412.13788); [ISCA](https://www.isca-archive.org/interspeech_2025/wang25_interspeech.html)
- Leaderboard as of 2026-06-23 (zero-shot WER, average / Casablanca) — [Cohere Transcribe Arabic blog, 2026-07-07](https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release):
  - Cohere Transcribe Arabic: 25.87 / 49.71
  - OmniASR-LLM-7B: 28.32 / 56.46
  - Cohere Transcribe: 30.67 / 62.71
  - Whisper v3 Large: 36.86 / 71.81
- Cohere internal per-dialect WER (same source):
  - Levantine: Cohere Transcribe Arabic 39.78; OmniASR-LLM-7B 74.50; Whisper v3 58.64
  - Code-switched AR-EN: 27.84 / 35.37 / 36.90
  - Egyptian, for comparison: 19.16 / 21.38 / 28.25
  - Model details: 2B parameters, FastConformer encoder, Apache 2.0, RTFx 525. It requires a language tag, has no timestamps or diarization, and tends to transcribe non-speech sounds, so the vendor advises a VAD.
- Casablanca (EMNLP 2024): 8 dialects, including Jordanian and Palestinian, labelled with dialect, gender and code-switching. A model trained on news-style studio data ("whisper-mix") did worst on conversational speech, while YouTube conversational training data did better. Domain matters more than corpus size — [arXiv 2410.04527](https://arxiv.org/pdf/2410.04527)
- Commercial code-switching benchmark (Perle AI, May 2026, v3 dated 2026-05-22): Egyptian-English, Saudi-English, Persian-English and German-English, 300 samples per pair, 5 commercial providers. ElevenLabs Scribe v2 had the lowest overall WER (13.2%) and the highest BERTScore (0.936). WER and BERTScore ranked systems identically (Kendall τ = 1.0 for the Arabic and Persian pairs), but WER exaggerated the gaps about 3x because it penalises valid transliteration and script choices. Dataset: HF Perle-ai/ASR_Code_Switch — [arXiv 2605.19069](https://arxiv.org/abs/2605.19069)
- ArzEn corpus: 12 h of Egyptian-English interviews from 38 speakers. ArzEn-LLM (2024) applies Whisper plus an LLM to code-switched Egyptian ASR — [arXiv 2406.18120](https://arxiv.org/html/2406.18120v2)
- Fanar (QCRI):
  - Aura STT (2025) claims dialect support regardless of nativeness or accent, and Ar↔En plus MSA↔dialect code-switching, but handles only clips of ≤20–25 s — [arXiv 2501.13944](https://arxiv.org/pdf/2501.13944)
  - Fanar 2.0 (March 2026) adds Aura-STT-LF, a long-form bilingual model, a punctuation/orthography "Styler", and the Aura-STT-BenchLF long-form benchmark — [arXiv 2603.16397](https://arxiv.org/pdf/2603.16397)
- L2 learner speech:
  - Speak & Improve 2025: about 315 h of L2 English, 55 h transcribed verbatim with disfluencies. Fine-tuning Whisper with filled pauses kept in helped lexical accuracy — [arXiv 2506.04076](https://arxiv.org/html/2506.04076v2)
  - Ballier et al. (2023 pilot, French learners of English): Whisper medium converged with what a native listener understands, i.e. it normalised the speech, while Whisper tiny gave alternate transcriptions that are plausible candidates for learner errors — [HAL 04547597](https://www.archives-ouvertes.fr/hal-04547597v1)
  - Whisper and WhisperX make significantly more errors on non-native speakers, and GPT-4o post-processing "recovers the lost accuracy" in a clinical setting. Recovered accuracy is the opposite of what a learner transcript needs — [medRxiv, via search summary](https://www.medrxiv.org/highwire/citation/1057449/refworks-tagged)
  - Data-driven mispronunciation patterns (Choi et al. 2025): aligning non-native phones to native ones gave a 12.8% recognition gain for non-native, mostly Korean, speakers — [arXiv 2502.00583](https://arxiv.org/html/2502.00583v1)
- Vendor claim, unverified: Deepgram nova-3 Arabic is described as working across dialects, with claims of up to ~40% lower WER than competitors — [Deepgram blog](https://deepgram.com/learn/nova-3-arabic-speech-to-text-production-grade-stt)

### Inferences
- Failure modes to expect for Medi:
  - The ق/غ/ك merge from Farsi L1 makes minimal pairs ambiguous. Context-driven models resolve the ambiguity toward the lexically likely, i.e. correct, word.
  - English words inside Arabic sentences may be transliterated into Arabic script, or the reverse. That counts as errors under WER even when the transcription is right.
  - Short learner turns give little acoustic context.
- Test E: add Cohere Transcribe Arabic (open, Apache 2.0, best open Levantine score) and OmniASR-LLM-7B to the 63-moment benchmark. Cohere Transcribe Arabic requires a language tag, which is a problem for mixed AR-EN turns, so test both "ar" and "en".
- Test F: a small or "less-LM" acoustic model (Whisper small/tiny, or a CTC wav2vec2/MMS without a language model) as a learner-error detector. Those models normalise less, following Ballier, so they may surface errors that the bigger models hide.

### Gaps
- No public benchmark of non-native (L2) speakers of Arabic dialects. None found for Farsi-L1 learners of Arabic.
- No public Levantine-English code-switching benchmark. Perle covers Egyptian and Saudi only.
- Did not retrieve MGB-3/MGB-5 (Egyptian, Moroccan) or ESCWA (Levantine-English code-switched meetings) numbers.
- No independent Arabic WER found for Gemini or gpt-audio.

## 3. Contextual biasing and prompting (vocabulary lists, topic, surrounding turns) and the risk of biasing toward the correct form

### Takeaway
Context and keyterm biasing reliably improve recognition of rare words. They also have documented false-biasing and hallucination modes that get worse with long bias lists and messy, code-switched speech. Mitigations include gating which entities to attend to, filtering the lists, "spoken-form" prompts, and measuring false-acceptance rates. For Anees, the tutor's words in the context are a bias list whose entries are the correct forms of exactly the words the learner gets wrong. That is the worst case, so a context-free listen plus explicit measurement of error preservation is required.

### Cited Findings
- Whisper prompted with a plain list of entity words worked in-domain but hallucinated in code-switched conversation. A "spoken-form" prompt with disfluencies, which looks like training transcripts, reduced the hallucination — [arXiv 2309.09552](https://arxiv.org/pdf/2309.09552)
- In a speech LLM, performance dropped sharply as the bias list grew, mainly from LLM hallucination. The fix was a separate fusion network — [SJTU 2024 paper](https://audiocc.sjtu.edu.cn/user/pages/03.research/02.publications/2024/Contextual@Biasing@Speech@Recognition@in@Speech-enhanced@Large@Language@Model/paper.pdf)
- Microsoft lightweight prompt biasing: the model learns when to attend to prompt entities, and an entity filter drops irrelevant ones. That gave 30.7% and 18.0% relative entity-WER reduction for small and large lists — [arXiv 2506.06252](https://arxiv.org/html/2506.06252)
- TCPGen biasing in Whisper can overfit. A keyword-aware loss gave up to 16.6% relative WER reduction and explicitly reports a false-acceptance rate for biasing, i.e. how often a bias word is output when it was not said — [arXiv 2509.09197](https://arxiv.org/pdf/2509.09197)
- IndicContextEval (2026) is a benchmark for whether audio LLMs use context, across 8 Indic languages. It is a methodology template for testing whether context helps or misleads — [arXiv 2606.19157](https://arxiv.org/pdf/2606.19157)
- Vendor keyterm features:
  - ElevenLabs Scribe v2 keyterm prompting: batch up to 1000 terms of ≤50 chars, realtime up to 50 of ≤20 chars, extra cost. ElevenLabs says the model "relies on the context to decide whether to transcribe that term". No Arabic-specific note — [ElevenLabs docs](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting)
  - Deepgram nova-3 keyterm prompting works across Arabic dialects, up to 100 terms. Multilingual keyterms (Dec 2025) allow up to 500 tokens — [Deepgram docs](https://developers.deepgram.com/docs/keyterm); [Deepgram Arabic blog](https://deepgram.com/learn/nova-3-arabic-speech-to-text-production-grade-stt)
- LLM correction steers toward written, correct language (over-correction) — [arXiv 2409.09554](https://arxiv.org/html/2409.09554v2)

### Inferences
- The false-acceptance metric from 2509.09197 maps directly onto Anees. Define a learner-error-preservation set: moments where Medi's corrected label differs from the tutor's form. Measure the "false correction rate", meaning the share of those where the system outputs the tutor's form. Report it next to hit rate for every configuration. Anees's current figures fit this frame: Gemini 12/27 changes hid mistakes, gpt-audio fixed 11/24.
- Test G (context ablation): run the same clips with (a) no context, (b) only the learner's own previous turns, (c) the full tutor and learner context, (d) the context with the tutor's correct form masked or removed. Measure hits and the false correction rate. Expect (c) to win on hits and lose on preservation.
- Test H (two-listen protocol): a context-free verbatim listen and a context listen. Where they disagree and the context version matches the tutor's word, flag for human review instead of applying the change. This extends the existing "changes toward the tutor's words wait for the tutor" rule to cases where the context run simply wins.
- Test I (prompt wording): a "verbatim, keep learner errors, keep mispronounced forms as heard, do not correct grammar" instruction vs neutral wording. Also try asking for an Arabizi or phonetic rendering alongside the Arabic script, so ق/ك/غ realisations are visible.
- Test J: vendor keyterms (ElevenLabs, Deepgram) fed with the lesson vocabulary. Expect a gain on hard dialect words and the same correct-form bias risk, so measure the false correction rate here too.

### Gaps
- No paper measures context-induced correction of learner errors in audio LLMs. Anees's own data is the evidence.
- I found no documentation of how Gemini or gpt-audio weigh text context against audio.

## 4. Word timestamps when the best text comes from an LLM: forced alignment for Arabic

### Takeaway
Standard practice is to keep the LLM's text and get timings from a CTC forced aligner: MMS_FA in torchaudio, ctc-forced-aligner, WhisperX's wav2vec2 alignment, or an Arabic wav2vec2 CTC model. No rigorous Arabic word-boundary benchmark was found, so Anees should build a small gold set and measure itself. Watch the MMS_FA licence: CC-BY-NC.

### Cited Findings
- torchaudio MMS_FA aligns via romanisation, Viterbi over CTC emissions. One Tunisian Arabic+French captioning project claims ±50 ms timing, but publishes no evaluation method, so treat it as anecdotal — [HF space ALIGNER.md](https://huggingface.co/spaces/karchoud/srt-caption-generator/blob/main/docs/ALIGNER.md)
- An Arabic-specific CTC aligner, fine-tuned from Arabic wav2vec2, gives word or character spans via Viterbi. No benchmark is published — [parseh/aligner-ar](https://huggingface.co/parseh/aligner-ar)
- The MMS forced-aligner weights are CC-BY-NC-4.0, non-commercial — [MMS forced aligner model page](https://www.promptlayer.com/models/mms-300m-1130-forced-aligner)
- A 2026 multilingual word-level aligner with learned dynamic programming beats MMS and MFA on English, and on unseen languages at tolerances ≥50 ms. Arabic was not among its test sets — [arXiv 2606.10675](https://arxiv.org/pdf/2606.10675)
- WhisperX: VAD cut-and-merge plus wav2vec2 phoneme forced alignment for word timestamps — [arXiv 2303.00747](https://arxiv.org/abs/2303.00747) (known reference, not fetched this session)
- MMS (Meta 2023) supports over 1,100 languages and released the forced-alignment model used by torchaudio — [arXiv 2305.13516](https://arxiv.org/abs/2305.13516) (known reference, not fetched this session)
- Cohere Transcribe Arabic has no timestamps, so it would need an aligner too — [Cohere blog](https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release)

### Inferences
- Test K: hand-mark word onsets and offsets for about 30–50 learner lines, mixed Arabic and English. Compare against those marks:
  - ElevenLabs native timestamps, transferred to the Gemini text by aligning the two texts
  - MMS_FA with uroman romanisation
  - the Arabic wav2vec2 CTC aligner
  - WhisperX
  
  Metric: share of word boundaries within 50 ms and 100 ms of the marks.
- Learner mispronunciations make alignment harder. A CTC aligner forced onto the "heard" text should cope if the text really reflects what was said. A low alignment score can also serve as a flag that the text may not match the audio, i.e. an LLM hallucination (inference).
- Cheap hybrid: keep ElevenLabs timestamps for words whose text Gemini left unchanged. Run forced alignment only on the changed spans, padded to the nearest unchanged anchor words.

### Gaps
- No published Arabic word-timestamp accuracy figures for any aligner. I did not check whether ctc-forced-aligner handles mixed Arabic and Latin script in one string without romanisation trouble.

## 5. Confidence and uncertainty, self-consistency, and routing to a human (active learning)

### Takeaway
Word-level confidence estimators exist: CEM for RNN-T, and C-Whisper (2025), which fine-tunes Whisper's decoder to score words and generalises better out of domain. Agreement across sampled runs is the black-box option for API models like Gemini. I found no published study that sets thresholds for routing to human review on that basis, so Anees's 3-run vote is reasonable but needs calibration.

### Cited Findings
- C-Whisper (Feb 2025): the decoder takes audio plus a hypothesis and outputs a confidence per word (from the word's last token), trained with BCE on correct/incorrect labels from alignment to a reference. Whisper-tiny C-Whisper matched CEM in-domain and beat it out of domain — [arXiv 2502.13446](https://arxiv.org/pdf/2502.13446)
- CEM uses features including the top-N beam hypotheses, i.e. agreement among alternatives as evidence of uncertainty. Word-level aggregation of token confidence is needed for downstream use — [arXiv 2101.05525](https://arxiv.org/pdf/2101.05525)
- Audio LLM runs vary a lot run to run (441 differences between two Gemini 1.5 Pro runs) — [GDELT](https://blog.gdeltproject.org/from-lsms-to-lmms-for-asr-evaluating-geminis-performance-at-transcribing-an-evening-news-broadcast)
- A call-centre study found that lower WER after fine-tuning did not remove the errors that mattered, on unseen field values. Check the error types that matter, not only WER — [arXiv 2506.05400](https://arxiv.org/pdf/2506.05400)

### Inferences
- Test L (calibration of the vote): on the 63 moments plus a sample of unchanged lines, plot accuracy against agreement level: 3/3, 2/3 and split. Also try 5 or 7 runs at temperature >0. Estimate how much review a threshold saves at fixed accuracy. ElevenLabs' 36.5% repeatability suggests disagreement among ElevenLabs runs is itself a cheap uncertainty signal.
- Test M (cross-engine disagreement as a flag): flag the line when ElevenLabs, Deepgram, gpt-audio and Gemini disagree on a word. Measure precision and recall of these flags against Medi's corrections.
- Test N (active learning order): send humans the lines with the highest disagreement or lowest confidence first. Also always send lines where the change moves toward the tutor's form, a known high-risk category at 12/27.
- Self-consistency only measures stability, not truth. A consistent correct-form bias (all 3 Gemini runs pulling to the tutor's word) will pass a 2-of-3 vote. So the vote cannot catch the main failure mode on its own; the context ablation in Test H is needed.

### Gaps
- No study on sampling-based agreement as confidence for audio LLMs, and no published review thresholds.

## 6. Clip length and segmentation, diarization vs separate tracks, audio preprocessing

### Takeaway
Separate per-speaker tracks already avoid diarization errors and cross-talk, which is a strong position. Evidence on clip length for audio LLMs is thin. Short clips lose context, while long files raise run-to-run drift and hallucination; Fanar 1.0 was limited to ≤20–25 s and needed a separate long-form model. Some models (Cohere Transcribe Arabic) transcribe non-speech sounds, so VAD gating matters.

### Cited Findings
- Fanar Aura STT 1.0 handled only ≤20–25 s utterances. Fanar 2.0 needed a dedicated long-form model (Aura-STT-LF) built for "speaker-change robustness" on hours-long audio — [arXiv 2501.13944](https://arxiv.org/pdf/2501.13944); [arXiv 2603.16397](https://arxiv.org/pdf/2603.16397)
- Cohere Transcribe Arabic tends to transcribe non-speech sounds, and the vendor recommends a noise gate or VAD — [Cohere blog](https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release)
- WhisperX's VAD cut-and-merge segmentation reduces hallucination and repetition in long-form Whisper — [arXiv 2303.00747](https://arxiv.org/abs/2303.00747) (known reference, not fetched this session)
- Including filled pauses in training helped L2 lexical recognition. Do not strip disfluencies before the model sees them — [arXiv 2506.04076](https://arxiv.org/html/2506.04076v2)

### Inferences
- Test O (clip padding): send Gemini the learner clip alone, ±0.5 s, ±2 s, and ±2 s plus the tutor-track audio of the previous turn. Measure hits and the false correction rate. Audio context may help less with bias than text context, which is worth checking.
- Test P (whole track vs per line): send the whole learner track in one call vs per line, and compare accuracy, drift and run agreement.
- Test Q (preprocessing): loudness normalisation, a VAD gate, and resampling to 16 kHz mono vs raw Recall.ai audio. Check for Meet codec artefacts. Low priority unless audio quality varies.
- Echo and bleed: if the tutor's voice bleeds into Medi's track, ASR may transcribe tutor words as learner words. Check the track separation quality on a sample.

### Gaps
- No controlled study found on clip length vs accuracy for Gemini or GPT audio models.

## 7. Arabic evaluation details: WER vs CER, normalisation, Arabizi, code-switching metrics

### Takeaway
Arabic WER depends heavily on normalisation (diacritics, hamza and alef, taa marbuta, alef maqsura, digits) and on script choice for code-switched words. Use a fixed normaliser, report both raw and normalised scores and CER, and add a points-of-interest metric (PIER-style) over exactly the learner-error tokens. Learner-error words are a tiny fraction of tokens, so overall WER will hide everything that matters.

### Cited Findings
- Cohere's Arabic normaliser, adapted from Whisper's:
  - removes diacritics
  - collapses hamza and alef variants
  - folds alif maqsura and Persian/Urdu letters into Arabic ones (relevant: a Farsi speaker's keyboard yields ی/ک)
  - converts Eastern Arabic digits to Western
  - removes tatweel
  - applies NFKC

  Source: [Cohere blog](https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release)
- Perle 2026 deliberately skipped hamza unification, taa marbuta collapse, diacritic stripping and digit conversion, so spelling variants count as errors. WER exaggerated gaps about 3x versus BERTScore, partly from transliteration and script differences — [arXiv 2605.19069](https://arxiv.org/pdf/2605.19069)
- Diacritics: zero-shot wav2vec WER was 88.58 diacritised vs 44.02 undiacritised on ArVoice, and 58.91 vs 24.08 on ClArTTS — [arXiv 2607.18946](https://arxiv.org/pdf/2607.18946)
- Common normaliser rules (Lucene ArabicNormalizer): hamza-alef to bare alef, taa marbuta to heh, alef maqsura to yeh, strip harakat and tatweel — [Lucene source](https://code.yawk.at/org.apache.lucene/lucene-analyzers-common/8.2.0/org/apache/lucene/analysis/ar/ArabicNormalizer.java); also the [QCRI Arabic normalizer](https://alt.qcri.org/tools/arabic-normalizer)
- PIER (Ugan, Pham, Bärmann, Waibel, Jan 2025): WER computed only at "points of interest", e.g. embedded-language words. Fine-tuning on monolingual data lowered overall WER on code-switching test sets while code-switched words got worse; PIER exposed that. Formula: errors at points of interest divided by the number of points of interest — [arXiv 2501.09512](https://arxiv.org/html/2501.09512v2)

### Inferences
- Do not collapse taa marbuta/heh or alef/hamza when scoring learner errors. Some learner errors are exactly these distinctions, e.g. a wrong gender ending, so normalisation choices must be made per error type. Proposed scoring for Anees:
  - (1) normalised WER and CER on all learner lines (Cohere-style normaliser)
  - (2) PIER over learner-error tokens: hit rate on Medi-corrected moments
  - (3) false correction rate: the system output the tutor's or the correct form where Medi said otherwise
  - (4) PIER over English code-switched tokens
  - (5) run-to-run agreement
- Normalise ی→ي and ک→ك for the Farsi keyboard. Keep ق/ك/غ distinct, because the merge is the learner phenomenon being tracked.
- Accept an English word in either script, or score it via transliteration-aware matching, to avoid the inflation Perle measured.
- CER is more forgiving of the partly right forms learners produce. Report it alongside WER.

### Gaps
- No standard Arabizi-aware ASR metric found. MER (mixed error rate: CER for the Arabic part, WER for the English part) was not verified in this session.

## 8. Models worth including in a 2026 benchmark

### Takeaway
A sensible benchmark set for October 2026:
- the current engines: ElevenLabs Scribe v2, Gemini 3.x Flash and Pro, OpenAI gpt-audio, Deepgram nova-3
- the strongest open Arabic dialect model: Cohere Transcribe Arabic (Jul 2026)
- OmniASR-LLM-7B
- Whisper large-v3 as a reference point
- Fanar Aura-STT-LF, if accessible
- a phonetic/CTC model (MMS or Arabic wav2vec2) as an error-revealing, low-LM baseline

Speechmatics, SeamlessM4T v2 and Qwen3-ASR derivatives are second-tier candidates.

### Cited Findings
- Cohere Transcribe Arabic: best open Levantine WER (39.78) and best Casablanca score (49.71); 2B parameters, Apache 2.0, no timestamps — [Cohere blog](https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release); [Cohere announcement](https://cohere.com/blog/transcribe-arabic)
- OmniASR-LLM-7B: second on the leaderboard (28.32 average), weak on Levantine (74.50) — same source
- ElevenLabs Scribe v2: lowest WER in the 2026 commercial code-switching benchmark (13.2%) — [arXiv 2605.19069](https://arxiv.org/abs/2605.19069); see also [Scribe v2 upgrade blog](https://elevenlabs.io/blog/scribe-v2-just-got-an-upgrade)
- Fanar Aura-STT-LF: a long-form Arabic-English model (Fanar 2.0, March 2026). Weights and licence not confirmed — [arXiv 2603.16397](https://arxiv.org/pdf/2603.16397)
- A third-party listing names a "Gemini 3.5 Transcribe" model with AA-WER 2.6 (Aug 2026). Unverified single source — [llmreference](https://www.llmreference.com/model/gemini-3.5-transcribe). Artificial Analysis runs an AA-WER v2 speech-to-text leaderboard (about 8 h, 3 datasets, English-centric) — [Artificial Analysis](https://artificialanalysis.ai/es/speech-to-text/models/gemini)
- Clinera (JMIR preprint 2026) evaluated ElevenLabs Scribe v1, ArAZN-Whisper-S, Whisper-large-v3, SeamlessM4T v2 and Wav2Vec2-Large-AR on Egyptian-English medical code-switching (683 utterances) — [JMIR preprint](https://preprints.jmir.org/preprint/96222)
- Lemura Arabic ASR: a community Qwen3-ASR fine-tune (1.7B) listing Levantine among its dialects. Unverified — [friendli listing](https://friendli.ai/models/lemuralabs/lemura-arabic-asr-qwen3)

### Inferences
- The project's existing ranking (Gemini with context ≫ gpt-audio ≈ Deepgram ≫ ElevenLabs on learner moments) runs opposite to ElevenLabs' strong showing on native code-switching. That fits the view that learner speech is a different task: native-speech benchmarks do not predict learner-moment accuracy. Anees's own 63-moment set, grown over time, is the benchmark that matters.
- Before adding a model, check whether it has word timestamps. If it doesn't, it needs the aligner from Test K.

### Gaps
- Did not verify the exact current Gemini or OpenAI audio model names and Arabic capabilities from vendor docs.
- No Speechmatics Arabic figures retrieved.
- Jais has no ASR of its own; it is a text LLM, usable only for text GER (not verified this session).
