# Measure every AI step before adding more

**Bottom line:** the research backs Anees's big bets: **Scribe v2, two separate tracks, FSRS, and the tutor's own Arabizi spelling**. The weak spot is not model choice. It is **measurement**. Today 1 of 9 AI steps has a gold set, 0 AI calls are logged, the Claude readers run on an unpinned model, and the detector's quoted 76% recall is **11% on real lessons**. The literature also flags one design that needs to change. **Free-form LLM "find the slips" readers are the step most likely to be wrong on dialect.** LLMs score **53.8 vs 88.9 F0.5** on dialect grammar correction and drift toward MSA. They should become a narrow, dialect-pinned Yes/No/Unsure judge, checked against a small stream of Amal/Medi verdicts. Build order: **run log → decisions log → frozen gold sets → health panel**. That takes about 4 evenings and 1 weekend, and it makes every later number trustworthy.

**Scale:** S = one evening · M = one weekend · L = several weekends. "Supported / Challenged" = what the evidence says about a current choice.

---

## Where Anees stands today: 1 of 9 steps is measured

| Step | What runs | How it's checked today | Latest number |
|---|---|---|---|
| Transcribe | ElevenLabs `scribe_v2`, per track | 20 clips blind-voted (Sep 4–5) | 15/20 preferred · **WER/CER never measured** |
| Speaker split | channel; mixed audio → Arabic share + pitch | none | 09-18 came out **swapped** |
| Grammar detector | rule code | 134-event gold set (105 tuned, 29 held-out) | **76% tuned → ~40% held-out → 11% real** (104/961) · precision 110/165 ≈ 67% · 34% wrong bucket |
| Readers r1/r2/r3 | `claude -p`, **no `--model`** | AI vs AI | **61.5% "agree"** (Jaccard) = **71.4% pairwise F1** |
| Arabizi fill | `claude -p` | 100 lines once | 96/100, grader not recorded |
| Word/sheet check | string match + agent | 1 hand check | **56 of 98** "new" words were already on the list |
| Amal patterns | `claude -p` | Amal's rulings (edited in place) | 116 open |
| Pages/stats | build scripts | by eye | "100% with 35 errors" shipped |
| Flashcards | FSRS-6 in browser | golden-file test | stores only got/missed |

Sources: [ai-process-review.html](ai-process-review-2026-09-27.html), [PROCESS-AUDIT-2026-09-26.md](https://github.com/TheNatanzi/anees/blob/master/plan/PROCESS-AUDIT-2026-09-26.md), [review_lesson.py](https://github.com/TheNatanzi/anees/blob/master/scripts/review_lesson.py), [compare.json files](https://github.com/TheNatanzi/anees/blob/master/data/lesson-work/full-audit)

**Four engineering facts that matter most:**
- **Errors chain.** In 416 of 961 audit rows (43%), Scribe wrote Medi's Arabic in **Latin letters**, and the usage counter skips Latin turns ([PROCESS-AUDIT G12](https://github.com/TheNatanzi/anees/blob/master/plan/PROCESS-AUDIT-2026-09-26.md)).
- **No run records.** Each lesson has up to about 5 `claude -p` runs, and each keeps only a 200-character stdout tail in a gitignored log. The hourly job's logs sit on another machine ([review_lesson.py](https://github.com/TheNatanzi/anees/blob/master/scripts/review_lesson.py), [switch_hourly_job.ps1](https://github.com/TheNatanzi/anees/blob/master/scripts/switch_hourly_job.ps1)).
- **Classic ML debt.** The pipeline is 98 scripts, dated literal filenames and an unpinned model. These match Sculley's "pipeline jungle", "undeclared consumers" and "reproducibility debt" ([Sculley et al. 2015](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)).
- **ML Test Score ≈ 0.** Google's rubric takes the *minimum* across its sections, and Anees scores 0 on monitoring. That is the "more of a research project" band ([Breck et al. 2017](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)).

**Keep these good patterns:**
- sha256 provenance on all 4,809 speaking-evidence events;
- `card_results` as an append-only answer log;
- the overlay rule ("raw transcripts are never edited");
- budget caps.

---

## Transcription: Scribe v2 leads code-switching, not every dialect

| Evidence | Number | Meaning for Anees |
|---|---|---|
| Arabic–English code-switching, 5 APIs | **Scribe v2 13.2% WER**. Next: gpt-4o-transcribe 38.6, Chirp 3 39.4, Azure 43.6 ([arXiv 2605.19069](https://arxiv.org/pdf/2605.19069)) | ✅ Supports Scribe. Caveats: vendor-authored, read-aloud speech, **no Levantine pair** |
| Hardest switching quartile | Scribe **20.0%** vs Chirp 61.5% ([same](https://arxiv.org/pdf/2605.19069)) | The gap grows exactly where Medi's mixed turns sit |
| Syrian (Levantine) YouTube, monolingual | Deepgram 13.76 · Gemini 3 Flash 14.40 · **Scribe 14.73** · GPT-4o-transcribe 31.67 ([GigaSpeechBench](https://arxiv.org/abs/2606.28884)) | Scribe is mid-pack on pure dialect. Deepgram **doesn't support Arabic code-switching** |
| Saudi / Egyptian | Scribe 33.33 / 44.44 vs Deepgram 16.56 / 37.12 ([same](https://arxiv.org/abs/2606.28884)) | Rankings flip by dialect. **Only your own gold set settles it** |
| English-heavy leaderboard | MAI-Transcribe-2 2.0% at ~$0.10/h; Scribe 2.2% at ~$0.22/h ([Artificial Analysis](https://artificialanalysis.ai/speech-to-text)) | Cost doesn't separate vendors; code-switching does |
| Mixed-audio diarization | Best open model: **17–20% DER** on meetings ([pyannote](https://www.pyannote.ai/benchmark)) | ✅ Strongly supports **separate tracks** |

**What learner speech does to ASR:**
- **ASR "cleans up" learners.** Whisper rewrote "there is the uh stars" as "there are stars". Repetition retention ranged from 22.5% (AssemblyAI) to 80% (RevAI) ([McGuire 2025](https://arxiv.org/pdf/2503.06924)). Learner errors are the product, so **verbatim mode is mandatory** (Scribe `no_verbatim=false`).
- **Silence triggers hallucination.** About 1% of Whisper transcripts contain invented sentences, and long pauses raise the risk ([Careless Whisper](https://arxiv.org/abs/2402.08021)). Lessons have long thinking pauses, so use VAD plus a flag on words that fall in silent spans.
- **LLM clean-up passes erase evidence.** Prompt-only LLM post-correction "often increas[es] error rates due to over-correction" ([survey](https://arxiv.org/pdf/2508.07285)). Keep **3 layers**: raw verbatim (immutable) → logged script/segmentation fixes → a separate "intended form" field. Nothing overwrites layer 1.
- **Word timestamps:** gpt-4o-transcribe returns none, and Gemini's timestamps drift ([OpenAI docs](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize), [BLAB](https://arxiv.org/pdf/2505.03054)). Neither can be the timing source for clips or fluency.

---

## Palestinian ASR: score CER, not WER, and build your own test set

| Finding | Number | Source |
|---|---|---|
| Dialect is much harder than MSA (same speakers) | MSA 13–19% vs dialect **42–77% WER** | [BULBUL](https://arxiv.org/abs/2608.21950) |
| WER overstates Arabic errors | Whisper-v3 on Palestinian: **50.2 WER but 18.4 CER** | [Casablanca](https://arxiv.org/html/2410.04527) |
| Best dialect-trained system, Palestinian | 22.27 WER / **8.05 CER** | [NADI 2025](https://arxiv.org/abs/2509.02038) |
| Script choice inflates code-switching WER | about **3×** (English written in Arabic script counts as fully wrong) | [arXiv 2605.19069](https://arxiv.org/pdf/2605.19069) |
| qaf ↔ hamza confusion | observed directly in dialect errors | [BULBUL](https://arxiv.org/abs/2608.21950) |
| Prompt/context biasing | "little to no average-WER change" | [GigaSpeechBench](https://arxiv.org/abs/2606.28884) |
| Automatic dialect ID | 79.8% best (wrong about 1 time in 5) | [NADI 2025](https://arxiv.org/abs/2509.02038) |
| Single-speaker (tutor) adaptation | **no published evidence** | — |

**What to do:**
- **Metric:** CER after a fixed normaliser as the headline, with WER second. The NADI recipe strips diacritics, unifies hamza/madda and keeps Latin ([NADI 2025](https://arxiv.org/abs/2509.02038)). Add one Anees rule: map Latin Arabizi through the existing `xscript.skel` consonant skeleton, so the script choice is not scored as an error.
- **Spelling reference:** Maknuune gives 36K Palestinian entries under CC BY 4.0 ([arXiv 2210.12985](https://arxiv.org/abs/2210.12985)). Use it plus Amal's spellings as the normaliser's lexicon.
- **Keyterms** (up to 1,000, +$0.05/h) ([ElevenLabs](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)): try them on **Amal's track first**. On Medi's track, biasing toward correct forms could hide his mispronunciations. That risk is inferred, not measured.
- **Fine-tuning (LoRA tutor adapter): not now.** There is no evidence on hours versus gain, and the real cost is labelling. Revisit only if gold-set CER on Amal's track stays high. Training on her voice needs her explicit consent.

---

## Measuring what Medi knows: FSRS yes, free-form LLM judging no

| Question | What the research says | Verdict for Anees |
|---|---|---|
| Best memory model for one learner? | FSRS-6 log loss **0.346** vs HLR 0.469 (10k users, 350M reviews). Only a cross-user GRU beats it ([srs-benchmark](https://github.com/open-spaced-repetition/srs-benchmark)) | ✅ **FSRS supported** |
| When to fit per-user parameters? | Fitting beats the defaults after about **16 reviews**. Refit monthly or when reviews double ([Anki FAQ](https://faqs.ankiweb.net/frequently-asked-questions-about-fsrs.html)) | ⚠️ Not done. Also, `card_results` stores got/missed, not the 1–4 grade |
| Deep knowledge tracing? | Logistic/IRT matches or beats deep models unless the data is large ([Gervet 2020](https://files.eric.ed.gov/fulltext/EJ1273917.pdf)) | ❌ Don't build DKT for N=1 |
| Knowledge from lesson dialogue? | LLM-labelled turns fed into knowledge tracing (LLMKT) beat BKT/DKT ([Scarlatos, LAK 2025](https://arxiv.org/pdf/2409.16490)) | ✅ Treat each heard/said word as an extra review event |
| Auto-detect non-understanding? | Gemini found misunderstandings at **77% recall, 47% precision**. Over 40% went unnoticed by the speakers themselves ([InCroMin](https://arxiv.org/abs/2512.20204)) | ⚠️ Usable only with human checks |
| LLM judging Arabic learner grammar? | GPT-4o: **53.8 vs 88.9 F0.5** on dialect. LLMs normalise toward MSA ([Alhafni & Habash](https://arxiv.org/html/2503.00985)) | ❌ **Challenges the free-form readers** |
| How many human labels? | Prediction-powered inference gives valid confidence intervals from a small human sample plus many LLM labels, saving **>25%** of human labels ([Gligorić 2024](https://www.alphaxiv.org/abs/2408.15204)) | ✅ Amal/Medi taps become the calibration set |
| Which agreement statistic? | Kappa needs countable negatives. For "did it find the slip", pairwise F1 is the right measure ([Hripcsak 2005](https://pubmed.ncbi.nlm.nih.gov/15684123/)) | ⚠️ Relabel 61.5% as Jaccard; report F1 |
| Automatic fluency? | Mean length of run ρ **0.749**, pause ratio −0.715; rules + LLM **0.818** vs human raters ([arXiv 2608.26137](https://arxiv.org/html/2608.26137)) | ✅ Cheap from Scribe word timestamps |

**Reader redesign, based on the evidence:**
- **Narrow task:** "Is Medi's utterance acceptable Palestinian colloquial? **Yes / No / Unsure**. If No, give the minimal edit and a bucket." Pin the dialect: "dialect forms are correct; never convert to MSA."
- **2–3 votes with abstain.** Majority voting moves LLM judges closer to humans ([arXiv 2408.09235](https://arxiv.org/pdf/2408.09235)). Send "Unsure" and split votes to Amal.
- **High-recall cues first, LLM second.** Use rules for repair markers (شو؟, ma fhimt, English after a tutor turn) and echo overlap. Give the LLM only the target turn plus the tutor turn before it, because longer context hurt in the word-meaning-negotiation study ([WMN study](https://lacuna.tiptreesystems.com/work/toward-the-automatic-detection-of-word-meaning-negotiation-indicators-in/wrk_e53d3ef4aafc5067f7b7a228148f01c9)).
- **Report agreement against humans, not AI vs AI.** Kappa can sit up to **41 points** below raw agreement ([arXiv 2606.19544](https://arxiv.org/html/2606.19544v1)).
- **Listening labels** (understood / breakdown / unknown, never counting a lone "aywa" as understood) and the difficulty tags are covered in the earlier *L2 listening difficulty tags* report. This report only adds how to log and score them.

**"Words said cold":** no validated metric exists ([Ehara, AIED 2022](https://link.springer.com/chapter/10.1007/978-3-031-11644-5_71)). Define it as a word Medi produced with no tutor use in the last N turns and not in today's cards. Log it as productive evidence per lemma, and label it "new measure" on the dashboard.

---

## Translation and Arabizi: models read dialect well but write it badly

| Direction | Evidence | Use in Anees |
|---|---|---|
| Levantine → English | about **35 BLEU** (Jais 36.1, AceGPT 35.3). Levantine is the lowest of 3 dialects ([AraDiCE](https://arxiv.org/html/2409.11404v3)) | ✅ Glosses and meanings: fine with spot checks |
| English → Levantine | **0.2–3.8 BLEU**. Outputs default to MSA ([AraDiCE](https://arxiv.org/html/2409.11404v3), [AL-QASIDA](https://aclanthology.org/2025.findings-acl.1137.pdf)) | ❌ Never let a model write "correct Palestinian". Show Amal's sentences |
| Arabizi → Arabic script | best seq2seq **80.6%** word accuracy, from many-to-many spellings ([Shazal 2020](https://aclanthology.org/2020.wanlp-1.15.pdf)) | ✅ **Supports tutor-spelling-first** via a per-tutor lexicon |
| Arabizi → English (LLMs) | GPT-4o 14.3 BLEU. Claude 3.5 Sonnet 7.3 BLEU, TER 119 (verbose output) ([arXiv 2502.20973](https://arxiv.org/html/2502.20973v1)) | ⚠️ Store in Arabic script; Arabizi is a display layer. Force terse JSON output |
| Lemma / gloss | Camelira Levantine lemma accuracy **85.5%** ([Camelira](https://aclanthology.org/2022.emnlp-demos.32.pdf)) | ⚠️ About 1 in 7 lemmas wrong; flag confidence and let Amal fix |
| MT evaluation | COMET-Kiwi mis-ranked systems on dialect; an LLM judge tracked humans ([arXiv 2502.20973](https://arxiv.org/html/2502.20973v1)) | Use an LLM judge plus about 200 tutor-checked lines (≈ ±7 pts) |

**Arabizi order of trust:**
1. Amal's own spelling (lexicon)
2. Deterministic map (3=ع, 7=ح, 2=ء …)
3. LLM fill, tagged `source=generated`

Log a flag when Amal corrects a generated form, so her letter preferences are learned rather than guessed.

---

## Target pipeline: raw layers stay frozen, every step logs a run

```
Meet ─► Recall bot: 2 tracks ─► VAD ─► Scribe v2 verbatim, per track ─► merge by word time
                                              │  every call ─► runs.jsonl
L1 raw ASR (immutable, sha) ─► L2 script layer (Latin Arabizi → skeleton; English → Latin) ─► L3 "intended form" (LLM proposal only)
      │
utterances ─► cue rules (high recall) ─► LLM judge (Yes/No/Unsure ×2–3, dialect-pinned) ─► human sample ─► decisions.jsonl
      │
learner evidence: card grade 1–4 + heard/said events ─► per-lemma state (FSRS R + transcript evidence) ─► Word Bank · Grammar Console · Progress
      │
build_ai_health.py ─► docs/data/ai-health.json ─► AI Reports tab
```

---

## Current choices: what the evidence supports and what it challenges

| Choice | Verdict | Why (one line) |
|---|---|---|
| ElevenLabs Scribe v2 | ✅ **Supported** | Clear code-switching lead (13% vs 39–44%); word timestamps; verbatim flag; $0.22/h |
| …as the only engine forever | ⚠️ Challenged | Mid-pack on monolingual Levantine. Re-test MAI-Transcribe-2 and Gemini 3 Flash **on your gold set** |
| Separate per-person tracks | ✅ **Strongly supported** | Removes the 17–20% DER of mixed audio; allows per-speaker settings |
| Mixed-audio fallback (Arabic share / pitch) | ⚠️ Challenged | Caused the 09-18 swap. Mark these lessons low-trust on the dashboard |
| FSRS-6 | ✅ **Supported** | Best per-user evidence at N=1 |
| Storing only got/missed; no refit; no calibration check | ⚠️ Challenged | Log the 1–4 grade, scheduler version and state; refit when reviews double |
| Tutor-spelling-first Arabizi | ✅ **Supported** | Model ceiling is about 80%; spellings are many-to-many |
| Skipping Latin-script turns in counts | ❌ Challenged | Hides 43% of error rows. Normalise instead of skipping |
| Free-form Claude readers, unpinned | ❌ **Challenged** | LLMs weak on dialect grammar (53.8 F0.5); 61.5% AI-vs-AI agreement; nothing reproducible |
| "Agree %" shown as Jaccard | ⚠️ Challenged | Label it, or show pairwise F1 (71.4%) |
| Grading the detector on rows it was tuned on | ❌ Challenged | 76% → 11%. Freeze tuned vs held-out splits |
| 20-clip preference vote as the ASR evaluation | ⚠️ Challenged | Preference counts, not accuracy. Add CER per channel |
| LLM post-correction of transcripts | ⚠️ Keep separate | Over-correction erases learner errors. Layer 3 only |
| Committed JSON as the store (no MLflow/Langfuse) | ✅ Supported | Lightest option for a static site. Use OTel field names so it can be exported later |
| LoRA tutor fine-tune | ⏸ Not yet | No evidence on gains; labelling is the real cost |

---

## Roadmap: 14 items, ordered by impact per evening

| # | Build | Effort | Metric it moves | Why now |
|---|---|---|---|---|
| 1 | `track.py` wrapper; `claude -p --output-format json --model <pinned> --max-budget-usd`; Scribe + scorer write runs | **S** | AI calls logged **0% → 100%**; $/lesson known | Unblocks every later number ([CLI cost docs](https://code.claude.com/docs/en/agent-sdk/cost-tracking)) |
| 2 | `decisions.jsonl`: nightly pull of `amal_rules` + reviews; stop PATCHing `payload.applied` | **S** | Human-vs-AI agreement computable; age of the oldest open item | Turns Amal's taps into gold |
| 3 | Freeze gold sets + `gold/manifest.json` (sha, split, n) | **S–M** | Steps with a standing gold set **1/9 → 5/9** | Stops tuning on test rows |
| 4 | GitHub Actions: pytest floors for deterministic evals + page invariants ("100% ⇒ 0 errors") | **S** | Shipped bugs with a regression test **1/7 → 7/7** | Free for public repos |
| 5 | `build_ai_health.py` + health panel on AI Reports | **M** | Monitoring score 0 → ~1; stale steps caught in under 24 h | Makes the tab a to-do list |
| 6 | Script layer: Latin Arabizi → skeleton, so Medi's Latin turns are counted | **S–M** | Rows skipped **43% → <5%**; detector real recall | Cheapest recall win |
| 7 | ASR gold: 1–2 h verbatim, both channels, in Amal's spelling | **M** (+ about 2–6 h of labelling) | CER per channel; learner-error retention; hallucinated words | Needed before any engine or keyterm change |
| 8 | Reader → narrow judge (Yes/No/Unsure, ×2–3, dialect-pinned) + canary on 2 frozen lessons | **M** | Human-sampled precision; reader F1; % sent to humans | Replaces AI-vs-AI trust |
| 9 | `card_results`: grade 1–4, `scheduler_version`, `state_before`, `card_id`; calibration chart | **S** | Predicted R vs observed recall gap; log loss | FSRS evidence assumes this data |
| 10 | Keyterms A/B on Amal's track; challenger bake-off (MAI-2, Gemini 3 Flash) | **S** each | CER difference; $/h | Only after #7 |
| 11 | `utterance_events` + listening labeller + swipe sampling (4 uncertain / 5 random / 1 repeat) | **M** | Labeller accuracy ±7 pts after about 12 lessons | Ladder needs it |
| 12 | Fluency trends: mean length of run, pause ratio, speech rate from word timestamps | **S–M** | Per-lesson fluency trend | Best-validated automatic CAF measures |
| 13 | Per-lemma evidence model: FSRS + heard/said + "said cold", lemmas via Camelira/Maknuune | **M–L** | Known-lemma count; said-cold count | Merges transcripts and cards |
| 14 | LoRA tutor adapter | **L** | Amal-track CER | Only if #7 shows a need |

**Order:** 1 → 2 → 3 → 4 → 5 (≈ 4 evenings + 1 weekend), then 6 → 7 → 8 → 9, then the rest.

---

## Tracking design: three append-only logs feed one dashboard file

**Rules:**
- The repo is **public**, so log hashes and paths only, never transcript or prompt text.
- Never edit a line; supersede it.
- Field names follow the OpenTelemetry GenAI conventions, so the logs can move to Langfuse or MLflow later ([OTel GenAI](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md)).

### 1 · Run log: `data/runs/YYYY-MM.jsonl` (one line per AI, scorer or build call)

| Field group | Fields |
|---|---|
| identity | `run_id`, `parent_id`, `trace_id` (lesson + trigger), `kind` (inference/eval/build/ingest), `step`, `lesson_date`, `pass`, `role`, `trigger`, `host` |
| what ran | `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `tool_version`, `params`, `prompt_file`, `prompt_sha`, `code_sha` (+dirty) |
| data | `input_refs[{path,sha256}]`, `output_refs[{path,sha256,rows}]` |
| outcome | `status` (ok/error/timeout/empty_output/skipped_budget), `error_type`, `retries`, `started_at`, `duration_ms` |
| cost | `usage{input,output,cache tokens, audio_min}`, `cost_usd`, `cost_basis` (estimate/list_price) |
| quality | `metrics{dataset, version, sha, n, recall, precision, f1, cer…}`, `agreement{vs_run_id, f1_existence, jaccard, kappa_bucket}` |

### 2 · Decisions log: `data/decisions/YYYY-MM.jsonl` (one line per human verdict)

`decision_id, ts, who (Medi|Amal), channel (swipe|tutor_page|chat|commit), about_type (rule|audit_row|pattern|word|arabizi|label), about_id, ai_run_id, ai_value, answer, corrected_value, confidence, reason, latency_ms, sampling (random|uncertain|repeat), supersedes, applied_commit, source_row`

### 3 · Learner events (Supabase, where the browser already writes)

| Table | Add / create | Mirrors |
|---|---|---|
| `card_results` | `grade` 1–4, `scheduler_version`, `state_before{S,D,due,reps,lapses}`, `card_id`, `prompt_variant`, `client_version`, `session_id` | Anki revlog ([rslib](https://github.com/ankitects/anki/blob/main/rslib/src/revlog/mod.rs)) |
| `utterance_events` (new) | `id` (hash), `lesson_date, speaker, t_start, t_end, script, transcript_run_id, event (said/heard/typed), label, label_run_id, label_version, confidence` | Duolingo HLR/SLAM traces ([HLR data](https://github.com/duolingo/halflife-regression)) |

### 4 · Eval sets: `gold/manifest.json` (name@version + sha; never edited, only new versions)

| Gold set | Seed from | Metrics | Gate / cadence |
|---|---|---|---|
| `asr@v1` | M0 50 lines + 20 clips → grow to 1–2 h | CER/WER (normalised + raw on learner), script-normalised WER, learner-error retention, hallucinated words | On engine/param change |
| `speaker@v1` | M0 lines + 1 mixed lesson | speaker accuracy (target ≥ 90%) | On change; `unlabeled_share` every lesson |
| `grammar@v1-tuned / v1-heldout / v2-audit` | 105 / 29 / 1,018 rows | recall, precision, F1, bucket accuracy | pytest floor = last − 2 pts |
| `reader@v1` | 2–3 frozen lessons + human verdicts | pairwise F1, kappa on labels, human precision | Canary when model or brief sha changes |
| `arabizi@v1` | the 100-line check | accuracy (target 95) | On prompt change |
| `sheet@v1` | the 98-word check | "new word" precision | On code change |
| `gloss@v1` | 200 tutor lines + Amal's English | chrF++, judge-vs-Amal agreement | Quarterly |
| `ladder@v1` | logged swipes | confusion matrix, accuracy + 95% CI | Weekly |
| `fsrs` | the `card_results` replay | log loss, calibration | Monthly refit |

### 5 · What the AI Reports tab reads: `docs/data/ai-health.json` only (built hourly)

| Panel | Shows | Goes red when |
|---|---|---|
| Freshness grid | lessons × steps: done / failed / missing | a step is missing for a lesson older than 24 h |
| Step scorecard | metric on a named gold version, trend line, model/prompt change markers | a drop of ≥ 5 pts vs the last accepted run, or model/prompt changed with no canary |
| Agreement | reader F1, human-vs-AI agreement, share sent to humans | amber after 7 days with no human sample |
| Drift proxies | Latin share, hole rows, unlabeled share, bucket mix vs trailing mean | a proxy moves more than 2× its trailing spread |
| Cost | $/lesson per provider, tokens, audio minutes, budget used | cost is more than 2× the trailing median |
| Human queue | 18 rules, 116 Amal items, age of the oldest | oldest item older than 14 days |
| Incidents → tests | each shipped bug + whether a test exists | any bug without a test |
| Learner loop | answers/day, FSRS predicted vs observed recall | calibration gap over 10 pts |

Keep the 7 existing report cards below the panel as a **Research log**, each with `method, n, decision, status`.

---

## Conclusion

- **The next accuracy gain comes from counting correctly, not from a better model.** The Latin-script skip, the Jaccard label and the tuned-on-test detector all make Anees look worse, or better, than it is.
- **Use Amal's taps as the calibration set.** Her verdicts, logged as decisions and sampled on purpose, are the one resource no vendor has. They are what lets any AI number on this tab be trusted.
- **Open unknowns:** there is no Palestinian code-switching ASR benchmark, no study of LLM judges on learner Levantine, and no validated "said cold" metric. Once logged, Anees's own data will be the first evidence on all three.
