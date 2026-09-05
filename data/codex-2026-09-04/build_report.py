from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "outputs"
REPORT = OUT / "anees-independent-test-report.md"


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def clean_cell(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " / ").replace("|", "\\|").strip()


def hms(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "n/a"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load("manifest.json")
    comp = load("comparison.json")
    rows = comp["rows"]
    agg = comp["aggregate"]
    diar = comp["diarization"]
    duration_s = manifest["recording"]["duration_seconds"]
    hours = duration_s / 3600
    oa_full = duration_s / 60 * 0.0045
    el_full = hours * 0.22
    el_key_full = hours * (0.22 + 0.05)
    dual_candidate = el_full + el_key_full + 500 / 60 * 0.0045
    two_track_upper = 2 * (el_full + el_key_full) + 500 / 60 * 0.0045

    result_table = []
    labels = {
        "E": "E-long: ElevenLabs, existing 64-min call; frozen windows extracted",
        "ES": "ES: ElevenLabs, same 25-s clips, no keyterms (post-hoc control)",
        "O1": "O1: OpenAI strict bilingual/verbatim prompt (pre-registered)",
        "O2": "O2: OpenAI plus learned/topic vocabulary (pre-registered)",
        "EKG": "EKG: ElevenLabs short clips plus global keyterms (post-hoc)",
        "EKL": "EKL: ElevenLabs short clips plus local ±120-s keyterms (post-hoc)",
    }
    for arm in ("E", "ES", "O1", "O2", "EKG", "EKL"):
        a = agg[arm]
        result_table.append(
            f"| {arm} | {a['successful_clips']}/20 | {a['tokens']} | {a['arabic_tokens']} | "
            f"{a['fillers']} | {a['cutoffs_or_ellipses']} | {a['chat_anchor_family_recovered']}/20 | "
            f"{a['clips_with_foreign_script']} |"
        )

    clip_sections = []
    for row in rows:
        i = row["index"]
        m = row["metrics"]
        texts = row["texts"]
        manual = row["manual_anchor_surface"]
        window = f"{hms(row['window_start'])}–{hms(row['window_end'])}"
        speaker_bits = (
            f"Meet caption speakers: {', '.join(row['meet_caption_speakers']) or 'none in window'}; "
            f"E-long clusters: {', '.join(row['eleven_speaker_ids']) or 'none'}; "
            f"ES clusters: {', '.join(row['eleven_segmented_speaker_ids']) or 'none'}."
        )
        metric_rows = []
        transcript_blocks = []
        for arm in ("E", "ES", "O1", "O2", "EKG", "EKL"):
            mm = m[arm]
            metric_rows.append(
                f"| {arm} | {mm['token_count']} | {mm['arabic_token_count']} | "
                f"{mm['filler_count']} | {mm['cutoff_or_ellipsis_count']} | "
                f"{manual[arm]} |"
            )
            transcript_blocks.append(f"**{arm} — {labels[arm]}**\n\n> {texts[arm].replace(chr(10), ' ')}")
        clip_sections.append(
            f"""### Clip {i}: chat anchor `{clean_cell(row['chat'])}`

- Frozen window: `{window}`; audio file in evidence bundle: `clips/clip-{i:02d}.mp3`.
- {speaker_bits}
- Manual surface-audit note: {manual['note']}

| Arm | Tokens | Arabic-script tokens | Fillers | Cutoffs/ellipses | Anchor family |
|---|---:|---:|---:|---:|---|
{chr(10).join(metric_rows)}

<details><summary>All six transcript outputs</summary>

{chr(10).join(transcript_blocks)}

</details>
"""
        )

    selected_rows = []
    for w in manifest["windows"]:
        selected_rows.append(
            f"| {w['index']} | {w['start_label'][:8]} | `{clean_cell(w['message'])}` | "
            f"{hms(w['window_start'])}–{hms(w['window_end'])} | `{Path(w['clip']).name}` | `{w['clip_sha256'][:12]}…` |"
        )

    report = f"""# Anees: independent transcription test, research review, and build recommendation

**Prepared:** 2026-09-04  
**Audience:** Medi, Amal, Claude, and any engineer asked to challenge or implement the plan  
**Scope:** the current `C:\\dev\\anees` project, the new 2026-09-04 lesson, the Google vocabulary source available during the test, current vendor documentation, and relevant Palestinian-Arabic/pronunciation-assessment research  
**Status:** independent analysis only. I did **not** change `C:\\dev\\anees`; it already contains uncommitted work belonging to Medi/Claude. Reproducible test artifacts are in the accompanying ZIP.

## Executive verdict

The best current solution is **not “OpenAI instead of ElevenLabs,” and not “ElevenLabs alone.”** It is a deliberately split system:

1. **Capture Medi and Amal on separate tracks.** This is the highest-leverage change and should happen before further diarization tuning. Zencastr Free currently advertises unlimited separate-track recording/download and is suitable for 60–70 minute lessons. Amal does not need to upload a file manually; Zencastr records locally and progressively uploads, but both people must keep the recording page open until upload completion.
2. **Use ElevenLabs Scribe v2 as the primary transcript evidence engine for now**, with `no_verbatim=false`, no vocabulary keyterms on the raw learner track, and word timestamps. On this independent sample it preserved more speech, fillers, and cut-off forms than either OpenAI prompt.
3. **Use OpenAI as a targeted second opinion and reasoning layer, not as the sole evidence transcript.** The strict OpenAI prompt stopped the prior wrong-language failures, but it still normalized or dropped learner evidence. Adding the learned vocabulary made the result slightly worse on this sample.
4. **Keep two transcript layers:** an immutable “observed/evidence” layer that may look messy, and a derived “canonical/display” layer using Amal’s spelling, Arabizi for Medi, Arabic for Amal, and explicit uncertainty links back to the audio.
5. **Find errors primarily from interaction evidence:** Amal’s correction/recast, Medi asking for or forgetting a word, Medi self-repairing, long within-turn pauses, and lesson chat. Generic ASR cannot be instructed to stop all correction reliably.
6. **Treat phonetic diagnosis as a later, candidate-only subsystem.** Use known target forms, Amal reference audio, a Palestinian pronunciation lexicon, forced alignment/phone posterior methods, and human calibration. Do not let an MSA or Qur’anic pronunciation model grade free Palestinian conversation as truth.

My confidence is **high** that separate tracks are necessary, **moderate** that ElevenLabs should remain the near-term primary transcription engine, and **low** for any claim about true word accuracy or “nearly perfect” transcription because there is not yet a human verbatim gold transcript.

The 20-window experiment does answer Medi’s prompt hypothesis: **better OpenAI prompting fixed language control, but vocabulary-constrained prompting did not beat the strict prompt and did not beat ElevenLabs on learner-form preservation.** O1 recovered 14/20 anchor families; O2 recovered 13/20; ElevenLabs arms recovered 16/20. O1 and O2 retained zero mechanically counted fillers, versus 22 in the short unprompted ElevenLabs control. Those counts are behavior proxies, not WER.

## What “nearly perfect” must mean

One percentage cannot represent the goal. Anees needs four separately measured qualities:

| Dimension | What is being measured | Why ordinary WER is insufficient | Proposed gate after gold labeling |
|---|---|---|---|
| Conventional transcript accuracy | Correct words and order for both languages | A clean correction can score well while erasing Medi’s actual error | WER/CER by speaker and language; set threshold only after baseline |
| Learner-form preservation | False starts, malformed words, repetitions, uncertainty, and self-repairs survive | These are normally treated as ASR noise but are the educational signal | Recall on Amal/Medi-labeled learner-form events; initial target ≥80% |
| Speaker identity | Every timed word/turn belongs to Medi or Amal | Correct words attached to the tutor would create false learner errors | Channel identity should be deterministic; fallback diarization DER measured separately |
| Learning-event detection | Corrections, gaps, hesitation, and grammar/pronunciation candidates are found without flooding Amal | A perfect transcript does not automatically identify why the learner struggled | Top-20 precision is primary; target ≥85% accepted or usefully edited, plus missed-event audit |

“Nearly perfect transcript” should therefore mean: an audio-linked transcript good enough that the **20 most valuable candidate moments** can be reviewed by Amal in 3–5 minutes, not an unsupported 99% WER claim.

## Direct answers to the central questions

### Can ASR be told to transcribe phonetically and stop auto-correcting?

Only partially. Prompting can request verbatim output, phonetic approximations, false starts, and uncertainty. It cannot turn a modern sequence-to-sequence recognizer into a neutral phonetic measurement device. The decoder still chooses likely words from linguistic context. The present test demonstrates the limit: both OpenAI arms removed every counted filler and sometimes collapsed conjugation practice into a clean phrase, even though the prompt explicitly said not to.

The practical answer is a layered one:

- preserve raw audio and word times;
- generate a no-keyterm evidence transcript;
- detect high-value moments from the interaction;
- re-run only those clips through independent hypotheses;
- use phone-level alignment/scoring only where a target word is known;
- let Amal confirm rather than pretending the machine has ground truth.

### Should the vocabulary list be a hard whitelist?

No. It should be a **prior and post-transcription validator**, never a decoder cage. A hard whitelist would hide exactly the categories Anees needs to discover: malformed learned words, ordinary inflections not stored as separate entries, fillers, proper nouns, loanwords, and genuinely new words. The correct rule is:

> English, known Palestinian forms, regular Palestinian morphology, fillers, proper nouns, and natural loanwords are allowed. Any other form is retained with audio and flagged as `OOV/uncertain`; it is never silently replaced.

### Do I agree with the public report that ElevenLabs is “much better than OpenAI”?

The conclusion is directionally supported for **transcript evidence on the two tested lessons**, but the report’s headline proof is overstated. Its `15/20` blind vote compared the ElevenLabs family against Speechmatics and a local dialect Whisper system. OpenAI was not one of the blind-vote candidates. Therefore “ElevenLabs won Amal’s blind vote 15/20” does not logically prove “nothing from ChatGPT beats it.”

This independent 2026-09-04 test does provide new direct evidence against two current OpenAI configurations: ElevenLabs preserved more material and more disfluencies, while O1/O2 recovered fewer chat-anchor families. Still, without human verbatim gold, the defensible statement is **“ElevenLabs is the better operational primary now,”** not “ElevenLabs has proven lower Palestinian-Arabic WER.”

## Independent experiment: exact design

### Preregistration and independence

The protocol was frozen before inspecting any new OpenAI output or the existing ElevenLabs transcript for this lesson. The existing project was used only to locate an already-paid Scribe response; its conclusions were not inherited. The protocol file hash recorded at test creation is `{manifest['protocol_sha256']}`.

### Frozen inputs

- Recording: `{manifest['recording']['path']}`
- Duration: `{duration_s:.6f}` seconds (`{hms(duration_s)}`)
- Recording SHA-256: `{manifest['recording']['sha256']}`
- Media structure: H.264 video, one AAC stereo stream, and one timed-text stream. The AAC stream is treated as a mixed recording because it does not provide one participant per channel.
- Meet chat SHA-256: `{manifest['chat']['sha256']}`; 21 timestamped Amal messages.
- Existing Scribe v2 response SHA-256: `{manifest['elevenlabs']['sha256']}`.
- Vocabulary used for the prompt: the selected Meet chat plus exported `Latest Topic` and `Animals` tabs from Medi’s Google document. The direct unauthenticated Google export returned 401; the signed-in browser was used read-only. Only these relevant tabs were used because further automated tab export hit rate limiting.

### Sampling

Medi requested 20 examples per lesson. All 21 chat messages were numbered chronologically; `random.Random(20260904)` selected 20 without replacement. The selected set was messages 1–19 and 21; message 20 was excluded. Each frozen clip is `[chat time − 15 s, chat time + 10 s]`, 25 seconds. Total nominal audio per arm is 500 seconds; after overlapping windows are unioned, unique audio is {comp['sampling']['unique_audio_seconds_after_overlap']:.3f} seconds.

This is a high-value lexical sample, not a representative random sample of the entire lesson. Adjacent windows are not independent.

| # | Chat time | Amal’s typed anchor | Frozen audio window | Clip | SHA-256 prefix |
|---:|---:|---|---|---|---|
{chr(10).join(selected_rows)}

### Test arms

- **E-long:** the original one-call, full-lesson ElevenLabs Scribe v2 response; words whose midpoint lies in each frozen window were extracted. It is not directly call-matched to the short-clip arms.
- **O1:** `gpt-transcribe`, Arabic + English language hints, strict verbatim bilingual prompt, no vocabulary.
- **O2:** the same request plus 41 selected chat forms and 75 Arabizi/Arabic document pairs. The prompt says the lexicon is context rather than a correction key.
- **ES (post-hoc control):** Scribe v2 on each same 25-second clip, `diarize=true`, two expected speakers, word timestamps, `no_verbatim=false`, no keyterms.
- **EKG (post-hoc):** same short ElevenLabs clips with 184 global keyterms from the selected chat and two document tabs.
- **EKL (post-hoc):** same short ElevenLabs clips with the two document tabs plus only chat terms posted within ±120 seconds of each clip; 144–161 keyterms.

O1 and O2 were pre-registered. ES, EKG, and EKL were exploratory follow-ups and must not be presented as if they were pre-registered. ES was added specifically because comparing short keyterm calls to the long baseline confounds vocabulary with chunking.

### Exact OpenAI prompts

**O1 strict**

> {manifest['openai']['strict_prompt']}

**O2 vocabulary-conditioned**

> {manifest['openai']['vocab_prompt']}

### Call controls

- Odd-numbered clips called O1 then O2; even-numbered clips called O2 then O1.
- One successful request per arm/clip; only 429 or 5xx was eligible for at most two retries with deterministic 2 s and 5 s backoff.
- Successful but poor, empty, or wrong-language outputs were outcomes, not manually “fixed.”
- All 40 OpenAI calls and all 60 new ElevenLabs calls returned HTTP 200 and nonempty text.
- The full raw response, response metadata, prompts/keyterms, clip hashes, elapsed time, and estimated audio cost are stored in the evidence bundle.

## Results

### Aggregate behavior

| Arm | Successful | Surface tokens | Arabic-script tokens | Fillers | Cutoffs/ellipses | Chat families visible | Foreign-script clips |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(result_table)}

Definitions:

- “Surface tokens” is a regex count of Latin/Arabic alphanumeric forms; it is **not accuracy**.
- “Arabic-script tokens” reflects script choice, not Arabic content; ElevenLabs often emits Arabic words in Latin/Arabizi.
- Filler and cutoff counts are mechanical lower bounds.
- “Chat family visible” is a manual surface judgment that the typed form or its relevant lexical family appears. It is not audio-grounded correctness.
- Four anchors are structurally unscorable/missed because the typed chat appeared tens of seconds after the spoken word; this is why no WER is calculated.

### Main findings

1. **The strict OpenAI prompt solved the old wrong-language failure mode in this sample.** O1/O2 produced no non-Latin/non-Arabic scripts. This is meaningful operational progress over the older report’s German/Japanese/Chinese failures.
2. **It did not preserve enough learner evidence.** O1/O2 produced 590/593 tokens versus 725 for the directly matched short unprompted ElevenLabs control. More text is not inherently better, but the missing content included conjugation attempts, fillers, and false starts that Anees explicitly needs.
3. **The vocabulary prompt did not improve OpenAI.** O1 recovered 14 anchor families; O2 recovered 13. O2 worsened clips 12 and 16 and reduced the mechanical cutoff count from 12 to 7. O1 and O2 were identical in 4 clips and changed in 16; mean character similarity was {comp['openai_prompt_effect']['mean_character_similarity']:.4f}.
4. **Both OpenAI conditions removed every counted filler.** This directly contradicts the prompt’s request to preserve them. It does not prove every hesitation was absent, but it makes OpenAI unsafe as the only pause/error evidence source.
5. **Short clipping, not keyterms, fixed ElevenLabs speaker-cluster collapse.** E-long assigned 695 of 708 extracted word records to `speaker_0` and only 13 to `speaker_1`; only 1/20 windows contained two Scribe IDs although Meet captions showed both named speakers in 19/20. ES detected at least two clusters in 19/20 with no keyterms. EKG and EKL also detected at least two in 19/20. The only defensible causal attribution is segmentation/request context, not vocabulary.
6. **Even recovered clusters are not stable identities.** A local 25-second call labeling `speaker_0` and `speaker_1` does not prove which is Medi or Amal, nor that the mapping is consistent between clips. Separate tracks make this inference unnecessary.
7. **Global future vocabulary can poison the transcript.** In clip 1 the unprompted systems and local-keyterm arm heard “Awesome”; EKG substituted the future lesson term `Mabsoo6`. This is the exact leakage risk created by waiting for the entire lesson vocabulary and then applying all of it globally.
8. **Local keyterms are useful for display but dangerous for evidence.** EKL produced readable forms such as `Babse6`, `Byebse6ni`, `Enbas6ti fi el-7afle`, and `Btenbes6i lamma ne6la3`; it also reduced fillers/cutoffs versus ES and may overwrite Medi’s malformed form. It belongs in the canonical interpretation layer only.

### High-value examples

- **Clip 2:** E-long retained `Masbu- mabsut`, an apparent false start; OpenAI produced the clean `مبسوط`. This is precisely the kind of evidence Anees must not discard.
- **Clips 8–9:** OpenAI collapsed a conjugation drill; clip 8 became only `هو. هي.` and clip 9 only “I made him happy.” ElevenLabs retained more paradigm attempts.
- **Clip 12:** O1 and ElevenLabs retained `Banbisat/Nabasat`-like attempts; O2 returned `[unclear]`, so the learned-vocabulary prompt harmed recovery.
- **Clip 16:** E-long and the short ElevenLabs arms retained the `enbasa6ti/fi el-7afle` phrase; O1 hallucinated “Airbnb” and O2 omitted most of it.
- **Clip 18:** ElevenLabs preserved `lamaaa uh nitlaaw Nitla-…`; OpenAI made the utterance cleaner and removed the counted hesitation.
- **Clip 1:** global ElevenLabs keyterms inserted `Mabsoo6` where the no-keyterm and local-context arms had “Awesome,” demonstrating temporal vocabulary leakage.

### What cannot be concluded

- No arm’s WER, CER, or learner-error recall is known.
- The 16/20 family score does not mean 80% accuracy.
- More tokens do not prove ElevenLabs is more correct.
- Meet caption speaker names are useful weak metadata, not verbatim gold.
- The sample heavily represents one verb family and tutor-typed vocabulary.
- The lesson recording is mixed, so Medi-vs-Amal identity is not audio-ground-truth.
- The result ranks tested configurations on this lesson, not every OpenAI/ElevenLabs model or future model revision.

## Why the four missing anchors matter

The frozen windows intentionally were not moved after seeing output. That exposed a design flaw in using chat timestamps as exact word times:

- `Baboos` was spoken roughly 65 seconds before its chat post.
- `Buset` was spoken roughly 42 seconds before its post.
- the full `Btenbese6i lamma ne6la3?` example was earlier than its post;
- `Enbes6i biyoamek` was spoken roughly 80 seconds before its post.

Therefore lesson chat should create a **search anchor**, not a 25-second truth window. Production should search ±120 seconds using lexical/semantic matching, preserve multiple candidates, and ask Amal only when the match is ambiguous.

## Speaker identity diagnosis

The current recording contains one mixed audio stream. The project’s Scribe full-lesson call asked for two speakers, but today it collapsed almost everything into one cluster. The fallback then labels everyone `Both`, which avoids a false identity claim but makes downstream learning metrics unusable.

The current code also creates an internal contradiction when the split fails: line 120 treats Arabic words from both voices as “Medi Arabic,” while line 122 counts pauses only in runs labeled `Medi`; after fallback, those runs are labeled `Both`. Thus the published statistics can count tutor Arabic as learner Arabic while reporting zero learner pauses. This is a P0 correctness issue, not a cosmetic one.

Recommended identity order:

1. **Separate capture tracks** named at ingestion (`medi`, `amal`) — ground truth by construction.
2. If only a mixed Meet file exists, use its embedded named captions as weak time-boundary hints, not transcript truth.
3. For fallback experiments, OpenAI’s diarization API currently accepts up to four known speaker names paired with 2–10 second reference samples. Test it on a labeled gold set before production.
4. Never assign names merely from “the speaker with more Arabic.” Amal may speak English and Medi’s Arabic share should increase over time; the heuristic is nonstationary.

## Recommended end-to-end architecture

```mermaid
flowchart TD
    A[Zencastr lesson call] --> B1[Medi local audio track]
    A --> B2[Amal local audio track]
    A --> C[Zencastr/Meet chat export]
    D[Google vocabulary document] --> E[Versioned vocabulary snapshot]
    B1 --> F[Immutable raw lesson record]
    B2 --> F
    C --> F
    F --> G[Base evidence transcript<br/>Scribe v2; no keyterms; no_verbatim=false]
    G --> H[Candidate event detector]
    C --> H
    E --> H
    H --> I[Candidate clips<br/>20 highest-value moments]
    I --> J1[ElevenLabs no-keyterm short pass]
    I --> J2[OpenAI strict short pass]
    I --> J3[Local-time keyterm interpretation pass]
    J1 --> K[Evidence fusion with uncertainty]
    J2 --> K
    J3 --> K
    E --> K
    K --> L[Dual display<br/>Medi: Arabizi; Amal: Arabic]
    L --> M[Amal 3–5 minute review]
    M --> N[Confirmed errors and vocabulary]
    N --> O[Practice cards and progress]
    M --> P[Calibration data for future thresholds]
```

### Capture workflow

- Use one Zencastr session as the call, not Zencastr plus another call simultaneously.
- The host sends Amal a link. Both wear headphones.
- Record separate tracks. The current pricing page says the free plan includes unlimited separate recording/download, up to six participants, progressive upload, and local recording.
- At the end, both keep the page open until upload confirmation. The host downloads the participant files or a ZIP. Amal does not manually send/upload audio.
- Free separate MP3 tracks are sufficient. Zencastr’s pricing page and older help center conflict on whether free WAV is available; verify the account UI before depending on WAV.
- Do not rely on Zencastr’s native transcription for Arabic: its November 2024 help article lists only English, French, German, Portuguese, and Spanish on paid plans, while the current pricing grid says “10 supported languages” without naming them. Either way, this project supplies its own ASR.
- Keep Google Meet recording/chat as a fallback only if Zencastr proves operationally annoying. Today’s Meet artifact showed why it is weaker: named captions and chat were useful, but the audio was one mixed stream.

### Grace period and vocabulary snapshots

Recommended default: **45 minutes after the lesson**, configurable to 30–60 minutes.

1. Immediately ingest and hash both audio tracks and chat; mark lesson `provisional`.
2. Start the no-keyterm evidence transcription immediately. It does not need the vocabulary update.
3. At +45 minutes, snapshot the Google document revision and chat, including tab/revision identifiers and a content hash.
4. Run OOV matching, canonical display, and candidate ranking using that frozen snapshot.
5. If Amal adds words later, create a new vocabulary-snapshot version and re-run matching/display only. Do not spend money retranscribing the entire audio.

This gives Amal time to add lesson vocabulary without letting future chat terms contaminate earlier raw ASR.

### Transcript data contract

Every token/span should preserve provenance. A minimum schema:

```json
{{
  "lesson_id": "2026-09-04",
  "source_track": "medi",
  "start_ms": 3279772,
  "end_ms": 3280410,
  "observed_surface": "en-enbas...",
  "canonical_arabizi": "Enbasa6ti",
  "canonical_arabic": "انبسطتي",
  "language": "ar-PS",
  "asr_engine": "elevenlabs/scribe_v2",
  "asr_config_hash": "...",
  "vocabulary_snapshot_id": null,
  "uncertainty": 0.42,
  "flags": ["self_repair", "possible_pronunciation_error"],
  "audio_clip_id": "...",
  "human_status": "unreviewed"
}}
```

The raw `observed_surface` is append-only. Human edits and canonical forms are separate records with author, timestamp, and reason.

### Arabizi/Arabic display policy

- Medi’s default interface: Arabizi, preserving the project’s exact numeral conventions and Amal’s forms.
- Amal’s default interface: Arabic script plus the aligned audio.
- Both can reveal the other representation.
- Automatic transliteration is a suggestion with confidence; it must never overwrite the evidence transcript.
- The project vocabulary document is authoritative for canonical spellings, but not proof of what Medi actually uttered.

## Learning-event detector

Candidate generation should be evidence-based and multi-signal. Each candidate stores all signals, not just a model conclusion.

| Event type | Strong signals | Output | Auto-confirm? |
|---|---|---|---|
| Tutor correction/recast | Medi utterance followed within ~0–8 s by Amal repeating a minimally different form; words such as “no,” “say…,” `صح`, or explicit explanation | before/after audio, observed hypothesis, tutor target | No |
| Forgotten/asked word | Medi says “I forgot,” “what does X mean?”, “how do I say…?”, long search followed by Amal supply | question + supplied word + clip | Usually candidate with high priority |
| Self-repair | same speaker restarts/changes a form (`Masbu- mabsut`) | initial and repaired spans | No; may be productive learning rather than error |
| Hesitation/retrieval gap | within-Medi-turn silence, filler chain, lengthened onset, repeated partial word | duration and neighboring words | No; pause alone is not error |
| Grammar candidate | disagreement between Medi form, tutor recast, vocabulary/morphology rules, and independent transcripts | evidence bundle and rule citation | No |
| Pronunciation candidate | known target + observable phone mismatch across repeated attempts/reference | target/observed phones, confidence, audio | No until calibrated |
| OOV/new word | surface form unmatched after allowed English, morphology, fillers, names, and loanwords | retained surface + nearest candidates | Ask/flag, never replace |

### Candidate ranking for a 20-item review

Use a transparent score, tuned later from Amal labels:

```text
score = 4*tutor_explicit_correction
      + 3*learner_explicit_gap
      + 2*tutor_recast_similarity
      + 2*chat_match
      + 1*self_repair
      + 1*long_pause
      + 1*cross_engine_disagreement
      - 2*already_confirmed_duplicate
      - 2*low_audio_quality
```

Diversify the final 20 so one conjugation drill cannot occupy the whole list. Suggested caps: at most eight examples from one lexical family and at least two candidate types when available.

### The 3–5 minute Amal review

Twenty items at an average 8–12 seconds each is 2:40–4:00 before occasional edits. Each card should have:

- tap-to-play 4–10 second audio, with one-tap “more context”;
- `Medi said` evidence field;
- `Suggested target` in Arabic and Arabizi;
- reason/type and confidence;
- buttons: **Correct error**, **Not an error**, **Edit target**, **Needs context**;
- keyboard/mobile shortcuts and automatic advance;
- bulk “these are the same conjugation pattern” grouping.

Do not ask Amal to proofread the whole hour. For the first five lessons, sample a few rejected/low-score events too; otherwise recall can never be estimated.

## Phonetic layer: feasible, but not a turnkey Palestinian model

Palestinian-specific phonetic diagnosis is possible as an engineering/research milestone, not as a prompt switch.

Recommended sequence:

1. Restrict phonetic analysis to candidate clips where a target form is known.
2. Build a pronunciation dictionary from Amal’s canonical forms and recordings. Seed it with Maknuune, an open Palestinian lexicon with more than 36,000 entries, 17,000 lemmas, 3,700 roots, diacritized Arabic, phonological transcriptions, and English glosses.
3. Use forced alignment to align the known orthographic target to audio phones. Montreal Forced Aligner defines forced alignment as producing a time-aligned transcript using a pronunciation dictionary.
4. Compute phone posterior/GOP-style features or CTC alignment disagreement. Kaldi’s GOP implementation explicitly describes GOP as a canonical-phone posterior ratio and notes classifier-based features usually outperform a raw threshold.
5. Calibrate phone-specific thresholds on Medi’s speech using Amal’s labels. Classic CALL work likewise used phone-specific thresholds and human judgments.
6. Use a universal phone recognizer such as Allosaurus only as an exploratory hypothesis source; it supports 2,000+ language inventories, but its timestamps are approximate and it is not a Palestinian learner grader.

Available Arabic mispronunciation datasets are mismatched to this task. ASMDD is Egyptian speech from children aged 2–8 on 100 frequent words. Iqra’Eval is Qur’anic/MSA read-speech assessment. Neither should be used as the truth standard for an adult’s spontaneous Palestinian conversation.

Azure and Google are worth later baseline tests because both explicitly list `ar-PS` speech recognition/adaptation. Azure’s pronunciation-assessment locale list, however, names Arabic Egypt and Saudi Arabia rather than Palestinian Arabic, and some fine-grained outputs are English-only. This supports benchmarking their ASR, not adopting their pronunciation score uncritically.

## Existing project audit

### What already exists

The repository is not empty despite the README saying “nothing built yet.” It contains:

- multiple Aug 25 engine outputs and comparison pages;
- an ElevenLabs/Meet lesson pipeline;
- generated lesson transcripts for Aug 25 and Sep 4;
- Google Meet chat extraction;
- HTML publishing to GitHub Pages;
- Gmail notification code;
- experimental speaker diarization, local Whisper, Speechmatics, OpenAI, and tutor-reaction scripts;
- extensive product/research planning documents.

There is **no implemented candidate error inbox, vocabulary-document ingestion, database/schema, review dashboard, flashcard loop, or production-grade test suite** visible in the repo.

### Severity findings

#### P0 — fix before trusting or automatically publishing learning metrics

1. **Mixed-channel capture defeats speaker-grounded learning analysis.** Today’s full Scribe call collapsed nearly all words into one cluster. Separate tracks are the remedy.
2. **No human verbatim gold exists, yet the engine report uses categorical language.** Preference votes and token counts cannot establish accuracy.
3. **The published `15/20` vote excludes OpenAI.** `build_engine_report.py` and `check02_scoring.md` show that the blind comparison was ElevenLabs vs Speechmatics vs local dialect Whisper. The headline overgeneralizes the result.
4. **Fallback metrics are internally invalid.** On failed speaker split, Arabic from both speakers is counted as Medi’s, while pauses can disappear because no run remains labeled Medi.
5. **Unvalidated transcripts are published and emailed automatically.** There is no human gate even when speaker split failed.
6. **Publish failure is suppressed.** `git commit` and `git push` use `check=False`, after which the function returns a public URL anyway. An email can therefore announce a page that was not successfully pushed.

#### P1 — required for a dependable MVP

1. No vocabulary-document synchronization, snapshotting, revision ID, or reconciliation exists.
2. No error-event extraction/review workflow exists; the current output is a transcript and coarse counts.
3. Ingestion identity uses a filename/state key, not Drive file ID as the binding contract requires.
4. The ElevenLabs request has no retry/backoff; the failure path only logs and updates state, with no failure email.
5. The 90-day raw-audio deletion contract is not implemented.
6. The pre-check samples only minutes 3–6 and runs before reading chat; a slow-English introduction could cause an Arabic lesson to be skipped even when the chat proves otherwise.
7. README, graph, blueprint, and constants disagree about what is built, which engine is primary, and whether two-channel capture is active.
8. The Python/Node dependencies are not pinned in `requirements.txt`, `pyproject.toml`, or a repo-local `package.json`; email code borrows another project’s `node_modules` and `.env` by absolute path.
9. No automated tests or CI checks cover parsing, speaker failure, idempotency, metrics, publishing, email, or deletion.
10. Provider model aliases/configurations are not captured as immutable run records in production, making later comparisons hard to reproduce.

#### P2 — cleanup and operational resilience

1. The pre-check comment still estimates `$1.50` for a full run although current Scribe pricing is $0.22/hour.
2. The Meet filename regex and minimum file-size heuristic are brittle.
3. State is written after the publish step, so the state version is not necessarily included in the same published commit.
4. The recipient address and external Alchemy path are hard-coded.
5. Public lesson transcript publishing is intentional and accepted by Medi, but the UI should still show that it is public and offer per-lesson deletion.

### Documentation reconciliation required

`plan/constants.md` says the binding design is separate channels, Drive-ID idempotency, three retries, failure email, 90-day deletion, and Supabase secrets. The current pipeline implements none of those except local secret avoidance in Git. `plan/graph.yaml` still marks early transcription/gold-sheet work as current even though later live pipeline artifacts exist. The README date/status is stale. Before additional features, turn the constants into executable acceptance tests and update the task graph from actual repository state.

## Proposed production pipeline

### Stage 0 — safe ingestion

- Unique lesson ID from provider session ID plus content hashes.
- Store both tracks, chat, recording metadata, consent/privacy status, and hashes.
- Idempotent state machine: `discovered → uploading → transcribing → provisional → awaiting_vocab → candidates_ready → tutor_reviewed → published`.
- Retry transient vendor calls three times with jittered backoff; permanent failures create a visible job and email Medi only.
- Never email/publish a success URL until the page/database transaction is verified.

### Stage 1 — evidence transcript

- Transcribe each named track separately with ElevenLabs Scribe v2, no keyterms, `no_verbatim=false`, word timestamps.
- Use 2–5 minute chunks with 1–2 second overlap for the searchable whole-lesson pass; deduplicate overlap deterministically. Twenty-five-second segmentation was useful today but has not been validated as the ideal production chunk length.
- Preserve provider response, config, model label, clip hash, and confidence/log-probability data.
- Calculate silence and pause features directly from audio/VAD, not only from text fillers.

### Stage 2 — candidate discovery

- Rule/model pass over cross-speaker temporal patterns.
- Search each chat item within ±120 seconds and attach best candidate(s).
- Allow all vocabulary/morphology; flag OOV after decoding.
- Rank/deduplicate/diversify to 20.

### Stage 3 — candidate adjudication

- Recut 4–15 second core clips plus wider context.
- Run ElevenLabs no-keyterm and OpenAI strict on the exact clips.
- Optionally run local-temporal keyterms to generate canonical Arabizi/Arabic, clearly marked non-evidence.
- Ask an LLM to produce structured hypotheses only from supplied evidence. It must cite timestamps and may return `uncertain`.

Suggested reasoning prompt:

```text
You are analyzing a Palestinian Arabic tutoring event, not rewriting a transcript.
Inputs: (1) Medi-track audio/transcript hypotheses, (2) Amal-track audio/transcript
hypotheses, (3) exact timestamps, (4) lesson chat near this moment, (5) a versioned
vocabulary/rules snapshot. Vocabulary is a prior, not a whitelist.

Return JSON only:
- event_type: correction | gap | self_repair | hesitation | grammar_candidate |
  pronunciation_candidate | oov | none
- observed_medi: preserve malformed/partial surface; never silently repair
- likely_target_arabizi
- likely_target_arabic
- amal_evidence: exact timestamped span or null
- evidence_spans: source/start/end/text
- alternatives: up to 3
- confidence: 0..1
- needs_amal_review: true/false
- explanation: one short factual sentence

Do not infer an error from accent alone. Do not call a pause an error without context.
If evidence conflicts, choose uncertain and preserve all hypotheses.
```

### Stage 4 — review and learning loop

- Amal reviews only the top 20 and a small quality-control sample.
- Confirmed events feed the vocabulary/error database and review cards.
- Cards always retain source lesson/audio and both scripts.
- Medi’s pause/retrieval metrics become a separate milestone after deterministic tracks exist.

## Human gold benchmark required next

The smallest defensible next evaluation is **100 clips accumulated as 20 per lesson across five lessons**. The current 20 are a pilot and may be reused only if Amal relabels the exact audio rather than accepting chat text as truth.

For each clip, Amal should provide:

- exact Medi words as heard, preserving malformed/partial forms;
- exact Amal words;
- speaker and word/turn boundaries to a reasonable tolerance;
- target/correction if present;
- event type;
- `not sure` where the audio is ambiguous;
- whether each machine output is acceptable for evidence and for display.

Evaluation:

- WER/CER by speaker and language on fully transcribed clips;
- learner-form event recall and precision;
- filler/cutoff/self-repair recall;
- speaker-attributed word accuracy and DER for mixed-file fallback;
- top-20 candidate precision, plus recall from a random rejected sample;
- review time median and 90th percentile;
- inter-rater check on 10–20 clips if possible, because the target dialect spelling itself can vary.

Do not tune thresholds on all 100 and report the same set. Use the first 60 for development, 20 validation, and final 20 held out—or continue collecting until there is a meaningful holdout.

## Cost analysis

Current official list prices used here are OpenAI `gpt-transcribe` at $0.0045/minute and ElevenLabs Scribe v2 at $0.22/hour, with ElevenLabs keyterms listed at $0.05/hour/20% surcharge depending on billing presentation.

For this `{duration_s/60:.2f}`-minute lesson:

| Operation | Estimate |
|---|---:|
| ElevenLabs one full-duration pass | `${el_full:.3f}` |
| ElevenLabs one full-duration keyterm pass | `${el_key_full:.3f}` |
| OpenAI one full-duration pass | `${oa_full:.3f}` |
| Recommended one-track base + one-track keyterm interpretation + 20×25 s OpenAI | `${dual_candidate:.3f}` |
| Conservative two-track version of both ElevenLabs passes + 20×25 s OpenAI | `${two_track_upper:.3f}` |
| All new API calls made for this independent experiment | `${comp['cost']['all_new_calls_estimated_usd']:.5f}` |

The recommended workflow is comfortably under Medi’s $3/lesson ceiling even under the conservative two-track calculation and before a small LLM reasoning charge. Production should meter actual invoice units because multichannel/rounding/minimum-duration rules can differ from simple arithmetic.

## Vendor and research findings

### OpenAI

- [`gpt-transcribe` model documentation](https://developers.openai.com/api/docs/models/gpt-transcribe) lists high-accuracy file/realtime transcription, unstructured context, keyword hints, multiple language hints, and $0.0045/minute.
- [`gpt-4o-transcribe-diarize`](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize) provides built-in speaker diarization.
- The [transcription API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create) documents `known_speaker_names` and 2–10 second reference samples for up to four speakers; `gpt-transcribe` supports multiple language hints and prompt/keyword guidance.

Implication: OpenAI remains worth targeted use, particularly known-speaker fallback and cross-engine adjudication. Its current strict prompt was operationally safe on language choice, but this experiment rejects the assumption that adding the full learned vocabulary automatically improves verbatim learner transcription.

### ElevenLabs

- The [Scribe request reference](https://elevenlabs.io/docs/api-reference/speech-to-text/convert) documents keyterms, up to 1,000 entries with length constraints, a 20% surcharge, `no_verbatim=false` by default, diarization, and multichannel responses.
- The [STT overview](https://elevenlabs.io/docs/overview/capabilities/speech-to-text) documents word timestamps, files up to 3 GB, up to 10 hours in standard mode, and up to five independently processed channels.
- The [API pricing page](https://elevenlabs.io/pricing/api) lists Scribe v2 at $0.22/hour, keyterm prompting at $0.05/hour, and realtime at $0.39/hour.

Implication: Scribe remains the best primary evidence engine tested. Use separate channels and no keyterms for the raw learner layer. Keyterms may improve canonical spelling but are not neutral.

### Zencastr and Google Meet

- [Zencastr pricing](https://zencastr.com/pricing) currently advertises a free plan with unlimited separate-track recording/download, local recording, progressive upload, six participants, and unlimited track storage.
- [Zencastr’s recording guide](https://support.zencastr.com/en/articles/9745874-getting-started-with-recording) says each participant has a separate track, guests join by link, and everyone must keep the page open until upload confirmation. It says free MP3 downloads and paid WAV, conflicting with the newer pricing grid on WAV.
- [How Zencastr records](https://support.zencastr.com/en/articles/5452702-how-zencastr-records) explains local browser recording and progressive upload, which means Amal does not manually upload after every lesson.
- Zencastr’s [transcript help article](https://support.zencastr.com/en/articles/9746991-getting-transcripts-for-zencastr-recordings) lists only five non-Arabic languages and paid transcription; use Zencastr for capture, not Arabic ASR.
- [Google Meet recording documentation](https://support.google.com/meet/answer/9308681?hl=en) confirms embedded captions and chat recording behavior. It does not promise downloadable per-participant audio tracks. The actual 2026-09-04 file had one mixed audio stream.

### Palestinian Arabic and pronunciation assessment

- [Maknuune](https://aclanthology.org/2022.wanlp-1.13/) is the strongest directly relevant lexical resource found: open Palestinian entries with phonological transcriptions, diacritized Arabic, and English glosses.
- [Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/en/v3.4.1/user_guide/index.html) supplies the forced-alignment framework when target text and a pronunciation dictionary are known.
- [Kaldi’s GOP implementation](https://github.com/kaldi-asr/kaldi/blob/master/src/bin/compute-gop.cc) and classic [Witt & Young CALL work](https://www.isca-archive.org/still_1998/witt98_still.html) show the appropriate phone-level direction and the need for human/phone-specific calibration.
- [Allosaurus](https://github.com/xinjli/allosaurus) is a universal phone recognizer covering more than 2,000 languages, useful for exploratory hypotheses rather than uncalibrated grading.
- [ASMDD](https://arxiv.org/abs/2111.01136) and [Iqra’Eval](https://aclanthology.org/2025.arabicnlp-sharedtasks.61/) demonstrate Arabic MDD resources but expose the domain mismatch: Egyptian children/top-100 words and Qur’anic MSA reading, respectively.
- Microsoft documents [`ar-PS` recognition/custom speech](https://learn.microsoft.com/en-us/azure/ai-services/Speech-Service/language-support), but its pronunciation-assessment locale table lists Arabic Egypt and Saudi Arabia, not Palestinian Arabic. Google likewise lists [`ar-PS` with Chirp 3/long/short and adaptation](https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages).

### Open-source projects worth learning from—not adopting as a turnkey answer

- [mcp-server-pronunciation](https://github.com/JuhongPark/mcp-server-pronunciation): local audio capture, ASR, grammar/fluency feedback; its explicit safety disclaimer is a good product pattern.
- [Cadence](https://github.com/pstepanovum/Cadence): Next.js/Supabase/Python pronunciation-coach architecture and audio-linked practice flows.
- [FluentAnyLang](https://github.com/Jim-Elijah/fluent-any-lang): local-first, sentence-level playback/shadowing and user-owned media.
- [CTC-based GOP](https://github.com/frank613/CTC-based-GOP): research implementation for phone-level pronunciation assessment.
- [Label Studio](https://github.com/HumanSignal/label-studio): possible audio annotation interface if building the 100-clip gold set quickly.
- [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs): later spaced-repetition scheduling component; not relevant to transcript truth.

None of these provides validated adult Palestinian conversational error detection out of the box. They are patterns/components.

## Implementation milestones and acceptance criteria

### M0 — capture and evidence integrity

- Complete one real 60–70 minute Zencastr lesson with separate Medi/Amal MP3s.
- Both tracks ingest automatically or through one host download action; Amal does no manual file transfer.
- Channel-to-name mapping verified from session metadata and a short listen.
- Hashes/configs stored; no transcript published on failed processing.

### M1 — 20-card candidate inbox

- Base no-keyterm transcript per channel.
- Chat ±120-second matcher and explicit-gap/correction/self-repair rules.
- Twenty candidate cards with audio, Arabic, Arabizi, and evidence.
- Amal completes one real review unaided in ≤5 minutes.

### M2 — five-lesson gold benchmark

- 100 reviewed candidate clips plus a random rejected sample.
- Report WER/CER, learner-form preservation, event precision/recall, and review time separately.
- Lock engine/config decision only from held-out labels.

### M3 — phonetic experiment

- Select 30–50 known-target words with multiple Medi attempts and Amal references.
- Build Palestinian phone dictionary entries.
- Compare forced-alignment/GOP/CTC signals to Amal labels.
- Ship only if it improves candidate ranking without increasing false accusations.

### M4 — learning loop

- Confirmed events generate cards with source audio.
- Medi sees Arabizi; Amal sees Arabic; both can reveal both.
- Existing FSRS contracts, caps, retention, and deletion rules become tested code.

## Questions Claude should attack

1. Can Claude reproduce every aggregate from `comparison.json` and identify any manual surface judgment it disputes after listening to the bundled clips?
2. Does Claude agree that its existing 15/20 vote excluded OpenAI? If not, which exact blind candidate maps to an OpenAI result?
3. Why does the current README say nothing is built while the pipeline publishes real lessons? Which document is authoritative today?
4. How will the current `Both` fallback avoid counting Amal’s Arabic as Medi’s while losing Medi’s pauses?
5. What exact mechanism turns Zencastr outputs into a Drive-ID/session-ID-idempotent job without asking Amal to upload anything?
6. What is the chosen vocabulary snapshot cutoff, and how are late edits versioned without retranscribing audio?
7. How will raw observed forms be protected from later canonical normalization and human edits?
8. What evidence proves a form is an error rather than a valid Palestinian variant, hesitation, joke, or ASR mistake?
9. How will recall be measured if Amal only reviews the top 20? What random-negative sampling rate is acceptable?
10. Is 2–5 minute base chunking appropriate, or should a controlled chunk-length test be run first? What metric decides?
11. Will ElevenLabs process two separate mono tracks or one multichannel container, and what are the actual billed units?
12. Should OpenAI known-speaker diarization be kept solely as Meet fallback? What gold threshold must it meet?
13. How does the system prevent a vocabulary item learned late in the lesson from biasing an earlier clip, as EKG did with `Mabsoo6`?
14. What is the exact Arabizi normalization policy for `2/3/5/6/7/8/9`, capitalization, vowels, and variants? Which transformations are reversible?
15. Who decides canonical Palestinian variants: Amal, Maknuune, or a model? The correct answer should preserve Amal’s local rules while documenting alternatives.
16. What is the privacy/deletion experience for a public transcript, and can Amal delete a lesson without editing Git?
17. Why are Git commit/push failures ignored before emailing a success link?
18. Where will secrets and dependencies live so Anees no longer borrows another project’s `.env` and `node_modules`?
19. What tests enforce the binding constants: retries, retention, idempotency, limits, speaker identity, and failure notifications?
20. What would falsify the recommendation that ElevenLabs remain primary? Define the held-out evidence before the next engine comparison.

## Bottom line

Medi’s intuition was half right: a much stricter OpenAI prompt makes the transcription safer and linguistically better constrained. It did **not** make OpenAI the best raw evidence engine in today’s controlled comparison, and adding the full learned vocabulary made the output slightly worse. ElevenLabs currently preserves more of the messy speech that Anees needs, but its full-lesson diarization failed dramatically on today’s mixed recording.

The decisive design move is therefore **separate participant tracks**, followed by a no-keyterm evidence transcript, targeted multi-engine adjudication, and a fast human review loop. Build that before trying to solve Palestinian phonetic grading. Once 100 clips have real labels, the project can make evidence-based engine and threshold decisions rather than relying on a persuasive-looking transcript or a preference bar chart.

## Appendix A — complete clip-by-clip comparison

All six text outputs for every selected clip are included below. Raw JSON additionally contains word timestamps, speaker IDs, confidence/log-probability fields where returned, request metadata, keyterms, elapsed time, hashes, and cost estimates.

{chr(10).join(clip_sections)}

## Appendix B — metric caveats

- Unicode Arabic and Arabizi are tokenized differently, so cross-arm token counts are approximate behavior indicators.
- A “filler” count recognizes a small spelling set (`uh`, `um`, `mm`, `mhm`, and Arabic approximations); prolonged sounds can evade it.
- Cutoff counts recognize hyphen-final fragments and ellipses; an engine may normalize a cutoff without an explicit marker.
- E-long word-window extraction uses token midpoints from the full call; ES/EKG/EKL/O1/O2 transcribed recut audio files. Boundary effects are unavoidable.
- Latency is workstation-to-vendor wall time under unknown shared load; ES had two extreme calls and is not a throughput benchmark.
- Model aliases can change. The report records vendor labels and raw response IDs but cannot recover an undisclosed backend snapshot.
- Chat text is authored by Amal and is valuable target evidence; its timestamp is a post time, not necessarily the speech time.
- Meet captions supply named speaker intervals but are themselves ASR output and may have delayed or inaccurate text.

## Appendix C — evidence bundle map

- `protocol.md` — frozen preregistration.
- `manifest.json` — hashes, selection, exact prompts, lexicon, clips.
- `comparison.json` — all computed metrics and six-arm text comparison.
- `results-openai-strict.json`, `results-openai-vocab.json` — raw O1/O2 outputs.
- `results-elevenlabs.json` — E-long frozen-window extraction.
- `results-elevenlabs-segmented.json` — ES no-keyterm control.
- `results-elevenlabs-keyterms.json` — EKG global-keyterm experiment.
- `results-elevenlabs-keyterms-local.json` — EKL local-keyterm experiment.
- `meet-captions-selected.json` — named Meet caption blocks overlapping every window.
- `clips/` — all 20 sampled MP3s.
- `source-vocabulary/` — exact relevant vocabulary/chat snapshots used by the test.
- `*.py` — generation and analysis scripts.
- `claim-to-source-ledger.md` — claim verification map.
- `SHA256SUMS.txt` — bundle file hashes.
"""

    REPORT.write_text(report, encoding="utf-8")
    (HERE / "report-source.md").write_text(report, encoding="utf-8")
    digest = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    print(f"wrote {REPORT} ({REPORT.stat().st_size} bytes, sha256={digest})")


if __name__ == "__main__":
    main()
