# Fix word crediting first, then test hearing

**Answer in one line:** 71% of the 331 errors on 10-08 come from Python word crediting, not from hearing. Test the crediting rules first (they cost nothing to run). Then measure how often each hearing setup "fixes" Medi's mistakes. Leave model-tier shopping for last.

---

## Where the 331 errors on 10-08 come from

| Bucket | Count | Share (own calc) | Layer that owns it | Cost to test |
|---|---|---|---|---|
| Untracked / wrong credit | 236 | 71% | Python rules (repeat vs credit, matching) | Free: no API calls |
| Misheard | 79 | 24% | ASR + Gemini re-hear | Low: audio re-runs |
| Missed slips | 13 | 4% | Opus readers + signal rule | Medium |
| Fake slips | 3 | 1% | Opus readers / dialect sense | Medium |

- Your gain is in the 236. Fixing every slip error, with perfect readers, moves the score by at most ~5%.
- Dialogue research backs the "repeat-of-tutor" idea: people reuse the words their partner just said all the time ([Reitter & Moore](https://david-reitter.com/pub/reitter2014JML-alignment.pdf)). So the idea is sound. The matching is what's broken.

---

## Terms used below (defined once)

| Term | Plain meaning |
|---|---|
| ASR | Speech-to-text engine (ElevenLabs, Deepgram, Gemini) |
| False-correction rate (FCR) | Share of Medi's real mistakes that the system writes down in the correct form (hiding them) |
| Hit rate | Share of the corrected moments the system heard right |
| Dev / held-out | Dev = lesson you tune on (10-08). Held-out = lesson you only score, never read error by error |
| Discordant items | Words where version A and version B disagree on right/wrong |
| McNemar / sign test | Paired test that only counts discordant items |
| MDE | Smallest change a test set can reliably detect |
| P / R / F0.5 | Precision (flags that are real) / recall (real ones caught) / score that weights precision 2x |
| Recast | Tutor repeats the learner's line with the error fixed |
| Lemma | Dictionary form of a word (strip b-, -ak, w-, l-, etc.) |
| Forced alignment | Tool that puts timestamps on text you already have |
| Krippendorff's alpha | Agreement score between two labelers (0.667 = minimum, 0.8 = trusted) |
| Effort | Claude's thinking level (low to max) |

---

## Prioritized test plan

Dev key = 10-08 (442 words, ~30 slips). Held-out = next fully reviewed lesson, hash-frozen on arrival. Claude $ = list-price equivalent, assuming ~30K tokens in / 5K out per reader call (own assumption; check against real logs).

| # | Test | Hypothesis | Setup | Metric | Sample | Pass bar | Cost |
|---|---|---|---|---|---|---|---|
| 1 | Mark confusion table | Most of the 236 sit in a few cells (e.g. gold repeat → pipeline credit) | Gold mark vs pipeline mark for each word, 6x6 table | Per-mark P/R | 442 words (10-08) | Table exists; top 3 cells named | 0 API; ~1 h code |
| 2 | Paired stats in grade book | Without it, wins under ~4 pts are noise | Add McNemar b/c, diff + 95% CI, "n words / k lessons" | Report fields present | All runs | Every report shows CI + discordant counts | 0 API; ~2 h |
| 3 | Lemma/clitic repeat matcher + echo window | Inflected echoes get credited by mistake | Root/lemma match with Levantine clitics; sweep echo window 1/2/3/5 turns | % words tracked right | 442 dev → held-out | +4 pts on dev (sign test p<.05) AND ≥ -1 pt on held-out | 0 API |
| 4 | Golden pairs + rule fixtures | Rules break on edge cases | Table of (tutor form, learner form) same/not-same; echo, recast-no-uptake, self-repair, disfluency fixtures | Fixture pass rate | ~50–100 fixtures | 100% in CI | 0 API; ~3 h |
| 5 | Pronunciation guard | Some "mistakes" are only Farsi-accent sounds | Collapse ḥ/h, ʕ/ʔ, ṣ/s, ḍ/ẓ/z/ð, ṭ/t, long/short vowels; equal → pron/not-scored | Pron-only mistakes; fake slips | 10-08 slips + all "mistake" marks | 0 pron-only mistakes; fake slips ≤1 | 0 API |
| 6 | Tutor second labeler | Medi's key has blind spots | Tutor relabels 30–50 moments from 10-08 | Alpha per error type | 30–50 moments | alpha ≥ 0.667 before a type gets a pass bar | ~15–25 tutor min |
| 7 | Context ablation (FCR) | Tutor-word context hides errors | Gemini with (a) no context, (b) own turns, (c) full, (d) full with tutor's form masked; 3 runs each | Hit rate + FCR | 63 moments (10-02) + 27 checked | FCR ≤10% with hits ≥45/63 (now 12/27 = 44% FCR, 53/63 hits) | ~750 short Gemini Flash calls |
| 8 | Two-listen review flag | Disagreements toward tutor form = hidden errors | Context-free listen vs context listen; if context copy matches tutor word → human queue | Hidden errors caught; lines sent to review | Same as #7 | ≥10 of 12 known hidden errors caught; ≤30 review lines/lesson | Reuses #7 runs |
| 9 | "Verbatim, keep errors" prompt | Wording cuts FCR | Neutral vs explicit keep-errors prompt; optional Arabizi line next to the Arabic | FCR, hits | 63 + 27 | FCR down ≥10 pts, hits down ≤3 | ~200 calls |
| 10 | Vote calibration | 2-of-3 can't see a shared bias | Accuracy at 3/3, 2/3, split; cross-engine disagreement flag | Accuracy per stratum; flag P/R | 63 moments + 100 random lines | 3/3 stratum ≥95% right, or else stop auto-accepting it | Reuses runs |
| 11 | Multi-hypothesis fusion | Gemini fuses better given 3 ASR guesses | Give Gemini ElevenLabs + Deepgram + gpt-audio text, disagreement marks, audio; edits allowed only where engines disagree. Baseline: plain word-vote (no LLM) | Hits, FCR | 63 + 27 | Hits ≥ current AND FCR ≤ #7 best | Deepgram + gpt-audio runs on 63 clips |
| 12 | Slip reader: tier × effort | Cheaper tier at higher effort may match Opus | Fable 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5, same frozen prompt, 3 runs; plus Haiku×3 vote; plus Claude+GPT-5.5 mix | Slip P/R/F0.5; fake-span rate; schema failures | ~30 slips dev; 90+ before any verdict | Descriptive only until 3 lessons keyed; then winner beats Opus by CI not crossing 0 | Per lesson ~$0.55 Fable, $0.22 Opus, $0.11 Sonnet, <$0.01 Haiku per run (own calc) |
| 13 | Edit-level self-consistency | Voting on slips raises precision | Opus reader k=5–8 runs; keep slips found in ≥tau runs; tune tau on dev | P, R, F0.5 | 10-08 → held-out | Precision +10 pts, recall drop ≤10 pts | 5–8x reader cost (~$1–2/lesson) |
| 14 | Few-shot from Medi's corrections | 3 gold examples per error class is the sweet spot | 0 / 1 / 3 / 5 examples from medi-corrections.json | F0.5 | Held-out only | 3-shot ≥ 0-shot by CI | ~4x reader cost once |
| 15 | Signal detector split | One step does too much | Python aligner finds recast (1–2 changed tokens); LLM only classifies type | Positive-class agreement vs Medi | All learner turns, 10-08 | Positive agreement ≥0.6 | Low |
| 16 | Judge hygiene (Codex) | Judge sides with whoever flagged | Neutral question, no reader names, order swapped | Agreement with gold; "sides with flagger" rate | All disputes on 10-08 | Side-with-flagger ≤ gold rate + 10 pts | 2x judge calls |
| 17 | Timestamps | Gemini text loses ElevenLabs timing | Hand-mark 30–50 lines; compare ElevenLabs transfer, MMS_FA, Arabic CTC aligner, WhisperX | % boundaries within 50/100 ms | 30–50 lines | ≥90% within 100 ms | ~2 h marking |
| 18 | New engines | Open Levantine model or "low-LM" model finds errors others hide | Add Cohere Transcribe Arabic; Whisper small / CTC wav2vec2 as error detector | Hits, FCR | 63 + 27 | Beats ElevenLabs on FCR; any hit gain | Local GPU or cheap API |
| 19 | Audio padding | Audio context helps without text bias | Clip alone, ±0.5 s, ±2 s, ±2 s + tutor's previous turn | Hits, FCR | 63 | Hits up, FCR flat | ~250 calls |
| 20 | Freshness + drift alerts | A stalled pipeline hurts more than 2 pts | Heartbeat per stage; alert on 0-slip/0-word runs; flag jumps >2 SD on slips/100 words, agreement rate, cost | Alerts fire on test fault | Each lesson | 95% of lessons scored within 6 h | ~2 h code |

- Order logic: 1–6 make every later number trustworthy. 3–5 attack the 71%. 7–11 attack the 24%. 12–16 attack the 5%.
- One lesson can detect ~3–6 pts on word tracking but only ~23–32 pts on slip recall (own calc from [Miller](https://arxiv.org/html/2411.00640v1)). So treat #12–14 as exploratory until 3 lessons are keyed.

---

## All factors worth testing

### Hearing (ASR) order and fusion

| Factor | What evidence says | Anees angle |
|---|---|---|
| ASR first, LLM fuses | 2025 work favors a speech LLM fusing several ASR outputs instead of voting ([2506.11089](https://arxiv.org/abs/2506.11089)) | Gemini sees only ElevenLabs, the weakest guess (4/63) → test #11 |
| Text-only LLM correction | Pushes toward fluent, written language ([Pu et al.](https://arxiv.org/html/2409.09554v2)) | That is the "hides mistakes" problem |
| Correct only where unsure | Phoneme-aware, error-only edits curb over-correction ([PMF-CEC](https://arxiv.org/pdf/2506.11064), [Hitachi](https://arxiv.org/pdf/2505.17410)) | Lock words all engines agree on |
| Pick-from-list rescoring | LLM picks a candidate, can't invent a form | Safer for learner errors; Deepgram gives alternatives |
| Run-to-run drift | Two Gemini runs on one audio differed in 441 places ([GDELT](https://blog.gdeltproject.org/from-lsms-to-lmms-for-asr-evaluating-geminis-performance-at-transcribing-an-evening-news-broadcast)) | Keep 3 runs; average per item |

### Learner and dialect speech

| Factor | Evidence | Anees angle |
|---|---|---|
| Levantine is hard | Best open Levantine WER 39.8%; Whisper v3 58.6% ([Cohere](https://huggingface.co/blog/CohereLabs/cohere-transcribe-arabic-07-2026-release)) | Expect high base error |
| Native benchmarks mislead | ElevenLabs tops native code-switch (13.2% WER) ([Perle](https://arxiv.org/abs/2605.19069)) yet got 4/63 on your moments | Your 63-moment set is the real benchmark |
| Big models normalize learners | Whisper medium "heard what a native hears"; tiny gave error candidates ([Ballier](https://www.archives-ouvertes.fr/hal-04547597v1)) | Test #18 low-LM detector |
| Code-switch scoring | WER blew gaps up ~3x from script choices ([Perle](https://arxiv.org/pdf/2605.19069)) | Accept English words in either script |
| No L2-Arabic benchmark | None found for Farsi-L1 learners | Build yours |

### Context biasing

| Factor | Evidence | Anees angle |
|---|---|---|
| Bias lists help rare words | Up to 30.7% fewer entity errors ([Microsoft](https://arxiv.org/html/2506.06252)) | Lesson vocab as keyterms |
| Bias lists cause false hits | Track "false-acceptance rate" ([2509.09197](https://arxiv.org/pdf/2509.09197)) | = your FCR |
| Long lists hallucinate | Speech LLM got worse as list grew ([SJTU](https://audiocc.sjtu.edu.cn/user/pages/03.research/02.publications/2024/Contextual@Biasing@Speech@Recognition@in@Speech-enhanced@Large@Language@Model/paper.pdf)) | Keep context short |
| Tutor words = worst-case bias list | Inference: they hold the correct form of exactly what Medi got wrong | Tests #7, #8 |

### Timestamps, confidence, segmentation

- Keep LLM text, get timing from a forced aligner; no Arabic accuracy numbers exist, so mark your own ([WhisperX](https://arxiv.org/abs/2303.00747)).
- MMS_FA weights are non-commercial (CC-BY-NC) ([model page](https://www.promptlayer.com/models/mms-300m-1130-forced-aligner)).
- Cheap hybrid: keep ElevenLabs times on unchanged words; align only changed spans.
- Per-speaker tracks already remove speaker-mixing errors; check tutor bleed into Medi's track.
- Agreement is not truth: 3 Gemini runs can all pull to the tutor's word and pass 2-of-3.

### Pronunciation vs word errors

- Best Arabic mispronunciation detector: F1 0.72, 30% false accepts, on native MSA reading ([IQRA 2026](https://arxiv.org/html/2603.29087v2)).
- So sound-level scoring is too noisy. Quarantine pronunciation; never let it make a mistake mark.
- Farsi lacks pharyngeals and emphatics (inference from phonology, not sourced) → test #5 merge list.

### Learner error detection and tutor signals

| Factor | Evidence | Anees angle |
|---|---|---|
| Spoken grammar checking is weak | Baseline P 0.37 / R 0.08; word-choice errors F0.5 <0.1 ([S&I 2025](https://arxiv.org/html/2412.11985v1)) | Keep "signal required" for vocab slips |
| LLMs on Arabic grammar | GPT-4 F0.5 67.8 on written MSA; learner text much lower (54.1) ([Kwon](https://aclanthology.org/2023.arabicnlp-1.9.pdf)) | Expect lower on spoken Levantine |
| MSA sense flags dialect | Open LLMs: 60% on MSA, 18% on dialects ([DialectalArabicMMLU](https://arxiv.org/html/2510.27543v1)) | Fixtures: correct Levantine forms → 0 flags |
| Recasts rarely get repeats | Recast 55% of tutor moves; learner repairs only 18% ([Lyster & Ranta](https://l2aquisition.wordpress.com/wp-content/uploads/2017/06/corrective-feedback-and-learner-uptake-negotiation-of-form-in-communicative-classrooms.pdf)) | Don't require uptake to confirm a recast |
| Humans disagree on signals | Two coders: kappa .18 on finding feedback moments ([Frontiers 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full)) | Narrow definition; split find vs classify |
| Disfluency | Grammar keys are built after removing false starts ([S&I](https://arxiv.org/html/2412.11985v1)) | Self-repair ≠ mistake, ≠ two words |

### LLM-as-judge reliability

- Biases: position, length, self/family preference, siding with the user, over-reasoning ([Zheng](https://arxiv.org/abs/2306.05685), [self-pref](https://arxiv.org/pdf/2410.21819)).
- Prompt wording moved GPT-4 judge kappa 0.52 → 0.73 ([PoLL](https://arxiv.org/html/2404.18796v2)). Prompt can matter more than tier.
- Keep Codex as a cross-family judge. Score every judge against Medi's gold, not against other models.
- Multi-model disagreement points to human label errors: 0% errors at full agreement, 76% at lowest ([medRxiv](https://www.medrxiv.org/content/10.64898/2026.05.04.26352392v1.full-text)).

### Model tiers

| Tier | List $/M tokens (in/out) | Default effort | Docs' advice |
|---|---|---|---|
| Fable 5.1 | $10 / $50 | high | Use when Opus at higher effort still falls short |
| Opus 5.5 | $4 / $20 | medium | Start here |
| Sonnet 5.5 | $2 / $10 | high | Fast mid tier |
| Haiku 5.5 | $0.10 / $0.50 | medium | Classification, routing |

Source: [Claude models overview](https://platform.claude.com/docs/en/models/overview).

- No Arabic or dialect scores exist for any 5.x tier. Nearest: HELM Arabic Opus 4.7 0.841 vs Sonnet 4.6 0.815 ([HELM](https://crfm.stanford.edu/helm/arabic/latest/)).
- Opus 5.5 beats Fable 5.1 on every listed vendor benchmark ([announcement](https://www.anthropic.com/claude-opus-5-5)). Don't assume Fable wins.
- Defaults differ by tier, so pin effort or you compare effort, not tier.
- Temperature can't be set on Sonnet/Haiku 5.5 → always 3+ runs.
- Three small mixed-family judges beat GPT-4 alone at 1/7 cost ([PoLL](https://arxiv.org/html/2404.18796v2)). Mixing families was part of the gain; Haiku×3 is one family.
- More votes can hurt: accuracy can rise then fall as calls increase ([Chen](https://arxiv.org/html/2403.02419v2)). Test k = 1, 3, 5.
- Under `claude -p` the real cost is usage limit + wall time. Log tokens anyway as "API-equivalent $".

### Evaluation design and statistics

| Rule | Why |
|---|---|
| Always pair (same words, both versions) | Correlation between versions cuts noise for free ([Miller](https://arxiv.org/html/2411.00640v1)) |
| McNemar / exact sign test for right-wrong | With 10 discordant words you need ≥9 to favor v2 (own calc) |
| Block bootstrap over 2–5 min segments for words | Words cluster; naive error bars can be 3x too small ([Miller](https://arxiv.org/html/2411.00640v1)) |
| No bootstrap on ~30 slips | Small-set bootstrap is flagged as wrong ([Dror](https://aclanthology.org/P18-1128.pdf)); use exact test |
| Dev win = candidate; confirm once on held-out | 10 variants at p<.05 → 40% chance of a fake win (own calc) |
| Pre-register each change | Metric, direction, min gain, max regression, written before running |
| Spend runs on lessons, not repeats | 3 runs is near the ceiling; more lessons beat more runs ([Miller](https://arxiv.org/html/2411.00640v1)) |
| Gate, don't average | All bars must pass, so one metric can't hide another's drop |
| Version the key | Any key edit = new key version; re-score old versions on it |
| Check rule firing on other lessons | A rule that fires only on 10-08 is overfit |

### Human in the loop (tutor's ~10 min/lesson)

- About 20–30 yes/no moments per lesson (20–30 s each; time not measured yet).
- Split: ~60% engine disagreement / low confidence, ~25% flagged slips, ~15% random.
- The random 15% is required. Weight results by sampling odds; never report raw % from the uncertain pile ([active testing](https://proceedings.mlr.press/v139/kossen21a.html), [PPI++](https://arxiv.org/pdf/2311.01453)).
- Always queue changes that move toward the tutor's form (known 12/27 risk).

### Cost and ops

- Cache engine outputs by (audio hash, engine, model version, prompt hash); re-run only touched stages.
- Pin model versions in tests; vendors drift ([promptfoo notes](https://tessl.io/registry/testland/promptfoo-evaluation/files)).
- Freshness, not uptime, is the right health measure for a data pipeline ([Google SRE](https://sre.google/resources/book-update/data-processing-pipelines/)).

---

## Method improvements backed by evidence

| Change | Evidence | Expected effect |
|---|---|---|
| Lemma + clitic matching for repeat-of-tutor; credit tiers (spontaneous / delayed reuse / echo / repair) | Word reuse from partner is constant ([alignment review](https://www.sciencedirect.com/science/article/pii/S0885230824001141)) | Shrinks the 236 bucket |
| Echoes never advance spaced repetition | Recast repairs are 100% repetition ([Lyster & Ranta](https://l2aquisition.wordpress.com/wp-content/uploads/2017/06/corrective-feedback-and-learner-uptake-negotiation-of-form-in-communicative-classrooms.pdf)) | Honest review schedule |
| Report FCR next to hit rate for every hearing setup | False-acceptance metric in biasing work ([2509.09197](https://arxiv.org/pdf/2509.09197)) | Stops trading Medi's errors for "accuracy" |
| Context-free listen + context listen; route tutor-ward changes to review | Text correction drifts toward correct forms ([Pu](https://arxiv.org/html/2409.09554v2)) | Targets the 12/27 |
| Feed Gemini 3 engine guesses; allow edits only where they disagree | Fusion beats voting ([2506.11089](https://arxiv.org/abs/2506.11089)); selective edits ([2506.11064](https://arxiv.org/pdf/2506.11064)) | More hits, less over-fixing |
| Pronunciation-equivalence guard before any mistake mark | Sound-level detection too noisy ([IQRA](https://arxiv.org/html/2603.29087v2)) | Fewer fake slips |
| Reader must cite line ID + exact span + evidence turn; Python checks they exist | Over-correction and invented edits are the main LLM failure ([Goto](https://arxiv.org/html/2605.13624v1)) | Unverifiable flags = auto-reject |
| Edit-level voting (k=8, keep ≥tau) on slips | Precision +6 to +19 pts on learner sets ([Goto](https://arxiv.org/html/2605.13624v1)) | Fewer fake slips |
| 3 gold examples per error class from Medi's corrections | 1→3 shots +7 F0.5, no gain at 5 ([Kwon](https://aclanthology.org/2023.arabicnlp-1.9.pdf)) | Cheap precision gain |
| Python recast aligner first; LLM only classifies | Split find vs classify ([Frontiers 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full)) | Failures you can pin to a stage |
| Arabic normalizer, versioned with key; score strict + lenient | Normalizing choices swing Arabic scores ([2607.18946](https://arxiv.org/pdf/2607.18946)) | Map ی→ي, ک→ك; keep ق/ك/غ distinct |
| Neutral, anonymous, order-swapped judge prompts | Position + family bias ([PoLL](https://arxiv.org/html/2404.18796v2)) | Fairer disputes |

---

## Unknowns (no source found)

- No published FCR numbers for any audio LLM on learner speech. Your 12/27 may be the only data.
- No Levantine learner or Farsi-L1 Arabic benchmark; no Levantine-English code-switch benchmark.
- No Claude 5.x Arabic or dialect scores; no effort-level effect data on annotation tasks.
- No study on the right echo window (turns or seconds).
- Gemini, ElevenLabs, Deepgram prices weren't researched; ASR costs above are in call counts.

---

**Most important action: build the 10-08 mark confusion table (test #1), then fix repeat-vs-credit matching (test #3) and judge it on a held-out lesson. That one change targets 71% of today's errors at zero API cost.**
