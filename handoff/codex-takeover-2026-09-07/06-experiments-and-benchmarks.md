# 06 — Every experiment and benchmark (what ran, how it was judged, what it supports)

Legend: **RAN** = a request actually executed and raw output is on disk; **DOC** = documentation / vendor research only; **PLANNED** = designed, not run. Ground truth: **no human verbatim transcript exists**; the only human judgement is Amal's Check 02 preference vote. Numbers marked ⟂ were recomputed by Claude's audit from raw JSON; others are as reported by their author.

## A. Aug 25 lesson (mixed 62-min mp3) — Claude, 2026-09-03/04

| Arm | Status | Config | Raw output | Judged by | Result | Limits |
|---|---|---|---|---|---|---|
| Whisper large-v3 local | RAN | `scripts/whisper_aug25.py`, chunked | `data/aug25/…` | machine counts | 695 chunks in 857 s; Standard-Arabic bias | no reference |
| Dialect Whisper (oddadmix whisper-turbo dialectal) + ECAPA voices / pyannote 3.1 | RAN | `dialectal_aug25*.py`, `diarize_*_aug25.py` | `data/aug25/turns*.json` | Amal (Check 02) | 445 turns / 3,446 words; invents "إيه ده!" in silence; **2/20 in the vote, 0–13 vs ElevenLabs** | speaker split by k-means |
| whisperx alignment | FAILED | torchvision / nltk errors | — | — | never ran | — |
| wav2vec2 Levantine CTC (elgeish) | PLANNED | — | — | — | parked (single-reader model) | — |
| Speechmatics ar_en bilingual, enhanced, diarization | RAN ×3 | `engine_speechmatics.py` (`SPEECHMATICS_API_KEY`) | `data/aug25/speechmatics_*` | Amal (Check 02) | 815 turns / 2,907 words; 3 repeat runs identical; 78 fillers; "But Anna Cartier"; **5/20, lost 11–1** | — |
| Speechmatics Arabic-only | RAN | same | — | machine | drops the English half (1,420 words) | — |
| **ElevenLabs Scribe v2 auto** | RAN | `engine_eleven.py` (scribe_v2, diarize, 2 speakers, word timestamps, audio events) | `data/aug25/eleven_scribe_auto.json` | Amal (Check 02) | 1,024 turns / 3,544 words in 33 s; ~200 fillers kept; lang `ara` 0.958; **15/20 with the ara run** | the pipeline's reference run for the 08-25 pages |
| ElevenLabs Scribe v2 forced `ara` | RAN | same + `language_code=ara` | `eleven_scribe_ara.json` | Amal | 986 turns / 3,532 words; tied with auto (same family in scoring) | — |
| OpenAI gpt-4o-transcribe-diarize | RAN (20 clips) | `engine_openai_clips.py` | `data/aug25/openai_*` | machine + eyeballing | German hallucination for Medi; refuses prompt | Check 03 built, **never rated** |
| OpenAI chat-with-audio (gpt-audio, -mini, 1.5) | RAN (clips + full) | `engine_openai_chat_audio.py` | `data/aug25/openai_chat_*` | machine | see `docs/engine-report.html`; "wins on words kept and speaker labels, not on a human accuracy score" (report's own words) | — |
| Codex Recipe 1 (ElevenLabs speaker slices → gpt-transcribe) | RAN | `engine_openai_recipe1.py` | `docs/recipe1.html` | machine counts | 333 vs 420 words: fewer words than ElevenLabs | second opinion only |
| Tutor-reaction detector | RAN (offline analysis) | `tutor_reaction_exp.py` on `gold_selection_v2.json` (20 corrections, 30 controls) | `data/aug25/tutor_reaction_results.json` | Claude-chosen gold set | best rule precision 0.50 / recall 0.70 (F1 0.58); uptake cue 0.82 / 0.45 | one channel; wiki 15 |

**Check 02 (the "15/20"), exactly:** 20 clips from Aug 25 (hard rows first; selection = `gold_selection` chunks), four transcripts per clip (A–D shuffled per row): local dialect Whisper, Speechmatics ar_en, ElevenLabs auto, ElevenLabs ara. Amal was asked (page text): *"Play the clip, then tap the letter that matches what was said best. If 2 or 3 are equally close, tap all of them. 'All same' if all four tie, 'All wrong' if none is close."* Fillers were shown as `(pause)`, ✓ marked her confirmations. Scoring rule pre-registered 2026-09-03 23:58: each picked engine scores 1 per row, ties 0.5, "all wrong" 0; ElevenLabs auto+ara count as one family; verdict pairwise on differing rows, ElevenLabs loses only if beaten on ≥ 60 % of them. Her raw string: `0:tie,1:CD,2:A,3:C,4:A,5:none,6:B,7:AB,8:none,9:C,10:none,11:BD,12:C,13:D,14:BD,15:AB,16:BC,17:tie,18:AC,19:AD`. Per engine: dialect 2, Speechmatics 5, eleven_auto 10, eleven_ara 10 → family ElevenLabs 15, Speechmatics 5, Local 2. **It supports:** "on these 20 clips Amal preferred ElevenLabs' rendering most often." **It does not support:** any word-error rate, any claim about learner-error preservation, or ChatGPT (not in the vote). The scoring doc itself says: "Separate question NOT measured here: which engine keeps Medi's mistakes instead of auto-correcting them."

## B. Sep 4 lesson — Codex independent test, 2026-09-04 (`outputs/anees-independent-test-report.md`, bundle `anees-independent-test-bundle.zip`, work dir `…\do\work\independent-test-2026-09-04`)

- Pre-registered; 20 frozen windows (≈ 25 s) from the Sep 4 lesson; arms: ElevenLabs full lesson (E), ElevenLabs on the 20 clips (ES, + keyterm variants EKG/EKL), OpenAI strict prompt (O1), OpenAI vocabulary-constrained prompts. Then Speechmatics Melia 1 as a second challenger.
- Reported: E/ES 725 tokens, 22 fillers on 20 clips; O1 590 tokens, 0 fillers; vocabulary prompt slightly worse; Melia did not win. Verdict: keep ElevenLabs, capture separate tracks, two layers (evidence / display).
- ⟂ Claude's audit (`outputs/claude-adversarial-audit-2026-09-05.md`): the ES "16/20 anchors" was **copied from E** (`analyze_results.py:114 judgment["ES"] = judgment["E"]`), never judged; ES token count includes tag tokens that replace speech (`[speaking Arabic]` ×3); 25-s chunking kept 5/8 learner events vs 8/8 full-track; "cutoff markers" for OpenAI were ellipses. Codex's recommendation survives; the numbers are softer.
- Who judged "anchors": Codex itself (LLM reading), not Amal.

## C. Sep 4 clips — Codex overnight bake-off, 2026-09-05 (`outputs/anees-overnight-asr-bakeoff-report-2026-09-05.md`, evidence zip + SHA256SUMS, work dir `…\do\work\overnight-asr-bakeoff-2026-09-05`)

| Arm | Status | Calls / cost | Judged by | Result (as reported) |
|---|---|---|---|---|
| Gemini 3.5 Transcribe, 4 configs (incl. `verbatim`) | RAN | 80 × HTTP 200 (+ ≥ 7 retried attempts not persisted ⟂), 1 × 429 | machine counts + Codex reading | did not beat Scribe on preservation |
| CrisperWhisper 2.0 Medium local (auto / forced ar) | RAN | 40/40 on RTX 4070 Ti | machine | emits fillers/fragments but **loops** on 4 clips; worse Arabic |
| xAI STT | DOC | no credential | — | "highest-priority challenger not yet run" |
| Inworld STT 1 | DOC | no credential | — | Arabic experimental; data terms concern |
| Fish Audio transcribe-1 | DOC + PLANNED (kit ready) | 0 — paused for consent | — | terms allow training on uploads; no verbatim controls |
| StepAudio 2.5, Cartesia | DOC | — | — | not applicable |
| Outside benchmark (May 2026 code-switch paper, English verbatim leaderboard) | DOC | — | — | supports ElevenLabs on AR-EN; not Palestinian |

Preregistration and hashes verified by Claude's audit (protocol before results; 20/20 clip hashes; upload ledger 21 rows deleted). Discrepancies: runner edited after the run (mtime), attempt counters, two filler regexes (±1).

## D. Codex research reports (DOC)

- `outputs/anees-full-deep-research-report-2026-09-04.md` (162 KB): Ennuicastr capture recommendation, ElevenLabs per track with diarization off and `no_verbatim=false`, no whitelist, evidence vs pedagogical layer, 20-moment review cap; Android correction. Sources in its claim-to-source ledger (`data/codex-2026-09-04/claim-to-source-ledger.md`).
- `outputs/anees-fish-audio-research-and-test-status-2026-09-05.md`; `anees-research-and-architecture.pdf`; `teacher-brain-codex-2026-09-05.md` (grammar research, not ASR).
- Claude's wiki research: `wiki/07` (engine table, 2026-09-03), `wiki/13` (live/two-channel), `wiki/14` (LearnerVoice workarounds), `wiki/15` (speaker separation, tutor reaction), `wiki/16`.

## E. What was never measured

- Word error rate or learner-form recall against a human transcript — for any engine, any lesson.
- `language_code=ara` vs auto on a **single-person** track (the F5 problem).
- `no_verbatim` explicitly false vs default; `diarize=false` on tracks; `num_speakers=1`.
- Amal's opinion of any transcript page (she has only seen Check 02 clips).
- Whether `[laughs]` / `[audio cuts out]` spans hide speech.

## F. Reproduce the analyses

- Aug 25 engines: `scripts/engine_eleven.py [auto|ara]`, `engine_speechmatics.py`, `engine_openai_*.py`, `run_paid_engines.ps1` (keys in User env; each run is a paid call). Pages: `build_check_02.py`, `build_check_03.py`, `build_recipe1_page.py`, `build_engine_report.py`.
- Codex bundles: `…\do\work\independent-test-2026-09-04\`, `…\do\work\overnight-asr-bakeoff-2026-09-05\` (72 MB total, scripts `run_gemini.py`, `analyze_results.py`, `build_bundle.py`, SHA256SUMS), `data/codex-2026-09-04/` (copy of the independent test bundle + `analyze_results.py`, `comparison.json`, `manifest.json`).
- Claude's audit reproduction: `outputs/claude-adversarial-audit-2026-09-05.md` §1 lists every recount and the regexes used.
