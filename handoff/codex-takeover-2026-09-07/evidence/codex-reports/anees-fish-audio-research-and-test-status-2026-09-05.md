# Anees × Fish Audio: research findings and controlled-test status

**Date:** 2026-09-05  
**Status:** Research complete; benchmark preregistered and technically ready; audio transmission paused for informed consent and Fish account access.

## Bottom line

Fish Audio is worth a small direct test, but the evidence currently points **against** replacing ElevenLabs Scribe v2 for Anees.

The reasons are unusually aligned with Anees's hardest requirements:

1. Fish exposes no documented prompt, keyterm/vocabulary, verbatim, disfluency, phonetic, word-confidence, word-timestamp, diarization, or named-speaker control for ASR.
2. Its response has one detected language code for the file, an awkward fit for English–Palestinian-Arabic code-switching.
3. The best relevant outside benchmark found—English/German rather than Arabic—shows Fish preserving far fewer fillers and other disfluencies than ElevenLabs Scribe v2.
4. Fish is more expensive than the ElevenLabs rate used in the prior Anees analysis.
5. Most importantly, Fish's current Terms of Use explicitly permit using uploaded Content to develop, train, or enhance Fish and third-party AI/ML models. That requires a deliberate privacy decision by both Medi and Amal before their lesson audio is sent.

None of this proves Fish will be bad at Palestinian Arabic. A model can outperform its documented controls, and Fish could still surprise on raw acoustics. That is why the direct Anees test has been preregistered rather than dismissed—but no lesson audio has been uploaded without consent.

## What Fish Audio currently offers

Fish's public speech-to-text product is the beta `transcribe-1` model through `POST https://api.fish.audio/v1/asr`.

### Inputs and controls

The official endpoint accepts an audio file through multipart form data or MessagePack. JSON/base64 input is not supported. Bearer authentication is required.

The documented request fields are:

| Field | Meaning | Anees consequence |
|---|---|---|
| `audio` | Required audio file | Compatible with the existing MP3 clips |
| `language` | Optional language hint; Fish says language is auto-detected regardless | We can compare automatic mode with an Arabic hint, but cannot declare both Arabic and English |
| `ignore_timestamps` | Defaults to `true`; setting it to `false` returns precise timestamps and increases latency for clips under 30 seconds | The benchmark requests timestamps so timing quality can be inspected |

The documented response contains:

- one transcript string;
- audio duration;
- timestamped text segments;
- one detected ISO 639-1 language code and display name.

### Important missing controls

The public schema documents none of the following:

- vocabulary, keyterms, or the Anees learned-word list;
- a prompt or style instruction;
- “transcribe exactly,” verbatim, filler, or disfluency mode;
- phonetic output or an “uncertain/nonword” representation;
- word-level timestamps or confidence values;
- alternate hypotheses;
- speaker diarization, speaker count, voiceprint, or named-speaker enrollment;
- Palestinian, Levantine, or other Arabic-dialect selection;
- a multi-language hint such as `ar,en`;
- an ASR model selector.

This means Fish cannot be prompted into the Anees rules at recognition time. The learned vocabulary can still be used after ASR to flag out-of-list tokens and generate Medi/Amal review questions, but it cannot make Fish hear a difficult word differently.

## Pricing and operating cost

Fish publishes pay-as-you-go ASR pricing of **$0.36 per processed audio hour**, rounded up to the nearest second, with no API subscription or monthly minimum. The starter concurrency limit is five requests.

Approximate costs:

| Workload | Processed audio | Fish cost |
|---|---:|---:|
| One frozen benchmark arm | 20 × 25-second clips = 500 seconds | $0.05 |
| Both preregistered arms | 1,000 seconds | $0.10 |
| One mixed 60-minute track | 1 hour | $0.36 |
| One mixed 70-minute track | 1.17 hours | $0.42 |
| Two separate 60-minute speaker tracks | 2 hours | $0.72 |
| Two separate 70-minute speaker tracks | 2.33 hours | $0.84 |
| Existing 64m36s full recording, one track | 1.077 hours | about $0.39 |

Separate capture tracks remain the safer Anees design because Fish does not document diarization. At the prior ElevenLabs reference rate of $0.22/hour, Fish is about 64% more expensive for the ASR portion.

## Evidence about transcript fidelity

### No directly relevant Fish benchmark was found

The search found no official Fish evaluation for:

- Palestinian or Levantine Arabic;
- Arabic–English code-switching;
- second-language learner speech;
- preserving grammatical or pronunciation errors;
- literal disfluency transcription in Arabic.

TTS support for Arabic is not evidence of ASR quality, so it was excluded.

### Outside verbatim benchmark

Nyra Labs' open verbatim-speech benchmark evaluates 15 systems on 4,957 English clips and a smaller German set. On its English leaderboard:

| Metric | ElevenLabs Scribe v2 | Fish Audio ASR | Better direction |
|---|---:|---:|---|
| Disfluency F1 | 90.3 | 49.7 | Higher |
| Filler F1 | 95.5 | 30.5 | Higher |
| Vocal-sound F1 | 83.4 | 0.0 | Higher |
| Cut-off F1 | 80.1 | 60.1 | Higher |
| Repetition F1 | 87.9 | 82.1 | Higher |
| Verbatim WER | 3.2 | 5.9 | Lower |

This is highly relevant to the *kind* of transcript Anees needs: the missing fillers, repetitions, sounds, and false starts are part of the learning signal. But it is not a Palestinian-Arabic result and must not be presented as one. Nyra Labs also makes a competing verbatim ASR model, so this should be treated as reproducible interested-party evidence rather than neutral certification.

The directional warning is still strong: Fish's largest deficit is filler preservation—the exact behavior ordinary transcription systems tend to erase and Anees needs to retain.

## Privacy and consent finding

This is the immediate blocker to a live test with the real lesson.

Fish's privacy policy classifies file uploads and environmental recordings as personal data. It says user content may be disclosed to several categories of partners and may be used for service improvement, testing, research, internal analytics, and product development. Its retention rule is purpose-based, not a short fixed window: content is retained as long as Fish says it needs it for its systems.

Fish's Terms of Use are more explicit. In the section titled “Usage Data and Content,” Fish says Usage Data and Content may be used to **develop, train, or enhance artificial-intelligence or machine-learning models**, including third-party components, and that the user authorizes this processing.

The public terms do not visibly exempt API uploads. Therefore:

- the benchmark clips should be uploaded only after Medi confirms Amal knowingly agrees to this Fish-specific processing;
- production use should require the same consent, or a separate written Fish enterprise/data-processing commitment that excludes training and narrows retention;
- an anonymous third-party “free Fish” demo is not an acceptable workaround because it adds another processor and makes provenance less certain.

## Preregistered direct Anees test

The benchmark was frozen before any Fish output was seen.

### Audio

- The same 20 existing 25-second MP3 clips used for ElevenLabs, OpenAI, and Speechmatics.
- Total: 500 seconds per arm.
- Each clip is checked against the SHA-256 hash in the original manifest before upload.
- The clips were selected around lesson-chat anchors, giving a target word family to look for without pretending the chat is a full gold transcript.

### Fish arms

| Arm | Language field | Timestamp field | Purpose |
|---|---|---|---|
| `F0_auto` | omitted | `ignore_timestamps=false` | Test Fish's native code-switch behavior |
| `FA_ar_hint` | `ar` | `ignore_timestamps=false` | Test whether an Arabic hint helps or damages the mixed transcript |

No undocumented tuning will be introduced after results are visible.

### Measurements

The harness records:

- successful/nonempty clips;
- Latin/Arabic surface token counts;
- conservative filler counts;
- conservative cut-off/ellipsis counts;
- unexpected writing systems;
- Fish-reported language-code distribution;
- timestamp segment counts and duration summaries;
- request latency;
- exact output changes caused by the Arabic hint;
- side-by-side text against ElevenLabs, both OpenAI arms, and Speechmatics;
- manual chat-anchor-family visibility for all 20 clips.

The last measure is deliberately called **family visibility**, not accuracy. Without a complete human verbatim reference, this test cannot honestly report WER/CER or “percent accurate.”

### Full-lesson gate

The 64m36s full file will not be sent by default. It adds roughly $0.39, does not solve speaker identity, and increases the privacy exposure. The preregistered gate permits that run only if the best 20-clip arm recovers at least 16/20 target families and appears competitive on learner-error preservation.

## Current execution status

The Fish API dashboard in the user's Chrome session is logged out, and no `FISH_API_KEY`, OpenRouter key, Vercel AI Gateway credential, or other Fish-compatible credential was found in the available environment.

The following have been completed locally:

- official and outside-evidence research;
- privacy/terms review;
- frozen protocol and hash registration;
- input-hash verification logic;
- two-arm API runner with five-worker concurrency and bounded retries;
- mechanical comparison script and manual-review template;
- a successful Python syntax check;
- a dry run confirming it stops safely when `FISH_API_KEY` is absent.

No audio has been uploaded to Fish and no Fish transcript has been observed.

## Preliminary recommendation

1. **Do not replace ElevenLabs yet.** Fish has neither direct Anees evidence nor the controls needed for error-preserving transcription, and outside verbatim evidence favors Scribe v2 by a wide margin.
2. **Run only the $0.10 two-arm test if both Medi and Amal consent to Fish's stated training/content terms.** This is cheap enough to settle the Palestinian-Arabic question empirically.
3. **Do not upload a full lesson unless Fish passes the frozen short-clip gate.**
4. **Keep speaker separation in capture, not ASR.** Continue designing around separate Medi and Amal tracks; Fish does not solve identity.
5. **Treat ASR as evidence, not correction.** Even if Fish wins raw recognition, vocabulary enforcement, Arabizi rendering, error classification, pause analysis, and Amal confirmation remain downstream stages.

## Reproducibility files

The working directory contains:

- `protocol.md` — frozen design and decision rules;
- `preregistration.json` — protocol/manifest hashes recorded before results;
- `run_fish.py` — API runner;
- `analyze_fish.py` — side-by-side and mechanical analysis;
- `manual-recovery.json` — unfilled 20-clip review form;
- `research-notes.md` — source notes and caveats.

## Sources

- [Fish Audio speech-to-text endpoint](https://docs.fish.audio/api-reference/endpoint/openapi-v1/speech-to-text)
- [Fish Audio pricing and rate limits](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits)
- [Fish Audio quick start and API-key requirements](https://docs.fish.audio/developer-guide/getting-started/quickstart)
- [Fish Audio official Python SDK](https://github.com/fishaudio/fish-audio-python)
- [Fish Audio documentation index](https://docs.fish.audio/llms.txt)
- [Fish Audio Privacy Policy](https://fish.audio/privacy/)
- [Fish Audio Terms of Use](https://fish.audio/terms/)
- [Nyra Labs verbatim-speech benchmark](https://nyra-labs.com/research/nyra-verbatim-speech-benchmark)

