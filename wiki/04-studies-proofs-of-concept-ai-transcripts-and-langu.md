# 04 — Studies & Proofs of Concept: AI, Transcripts, and Language Learning
*Compiled 2026-09-03. "Unverified" = recalled figure, page paywalled. "Industry" = authored/paid by the company studied.*

### 1. Duolingo research
| Study | Year / N | Result | Funding | So what |
|---|---|---|---|---|
| Settles & Meeder, Half-Life Regression ([ACL](https://aclanthology.org/P16-1174/)) | 2016; ~13M sessions | ~45% lower recall-prediction error vs baselines; +12% engagement | Industry | Per-item forgetting beats fixed intervals, but HLR is now near the bottom of the open benchmark. |
| Birdbrain ([blog](https://blog.duolingo.com/learning-how-to-help-you-learn-introducing-birdbrain)) | 2020 | IRT logistic model; no public effect size | Industry | Only the idea transfers. |
| Vesselinov & Grego ([PDF](https://theowlapp.health/wp-content/uploads/2022/04/DuolingoReport_Final-1.pdf)) | 2012; ~200 | "34 h ≈ one semester"; median gain half the mean | Industry; heavy attrition ([Krashen critique](http://sdkrashen.com/content/articles/krashen-does-duolingo-trump.pdf)) | Never repeat "34 hours" as fact. |
| Jiang et al. 2021 ([FLA](https://onlinelibrary.wiley.com/doi/full/10.1111/flan.12600)) | completers | A2 completers ≈ 4th-semester on reading/listening | Industry | No speaking. |
| DRR-24-04 ([PDF](https://duolingo-papers.s3.amazonaws.com/reports/Duolingo_whitepaper_language_read_listen_write_speak_2024.pdf)) | 2024; N=257 of 4,854 invited | After ~200 h: reading Int-High, **speaking "approaching Int-Low"** | Industry | Apps fail at speaking; that gap is ours to target. |
| Streaks ([blog](https://blog.duolingo.com/how-duolingo-streak-builds-habit/)) | internal A/B | +1.7% 7-day retention; streak-freeze +0.38% DAU | Industry | Small real nudge; the 3.6× course-finish figure is selection. |

### 2. Spaced-repetition proof
- SuperMemo history ([link](https://supermemo.guru/wiki/History_of_SuperMemo_algorithm)): started as N=1 self-study; a single-learner PoC is a respectable origin.
- Kornell 2009 ([Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1537)): spacing beat cramming for 90% of people, +31 points, yet learners predicted spacing would be 14 points worse. → Do not let felt difficulty drive the schedule.
- **Lindsey, Shroyer, Pashler & Mozer 2014**, Psych Science ([SAGE](https://journals.sagepub.com/doi/abs/10.1177/0956797613504302), [PDF](https://scottbarrykaufman.com/wp-content/uploads/2014/01/Lindsey-et-al.-2014.pdf)): semester-long Spanish class, personalized review: **+16.5% over massed, +10.0% over one-size-fits-all spacing.** Closest existing PoC to ours; expect ~10-17% gain.
- FSRS benchmark ([repo](https://github.com/open-spaced-repetition/srs-benchmark)): log loss FSRS-6 0.346, DASH 0.368, **HLR 0.469**, Ebisu 0.499; small LSTM 0.333. → Use FSRS; neural nets need more data than one learner produces.

### 3. LLM tutors 2023-2026
- Context: Bloom's 2-sigma → rigorous replication Nickow, Oreopoulos & Quan 2020 ([NBER](https://www.nber.org/papers/w27476)), 96 RCTs: **+0.37 SD**. The human tutor is the asset; AI is scaffolding.
- Frontiers in Education 2026 ([link](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1799269/full)), N=83, 16 weeks, voice agent: fluency d=0.99, accuracy d=0.56. → Voice practice moves fluency; accuracy needs explicit correction.
- Alignment drift ([arXiv 2505.08351](https://arxiv.org/pdf/2505.08351)): LLMs told to stay at A2 drift upward within a few turns. → Enforce level with a vocabulary whitelist, not a prompt.
- LLM corrective feedback: Fang et al. 2023 ([arXiv 2304.01746](https://arxiv.org/abs/2304.01746)) strong detection, **over-corrects**; Coyne 2023 ([arXiv 2303.14342](https://arxiv.org/abs/2303.14342)) rewrite-style edits. → Prompt for minimal edits citing the learner's exact words; keep the tutor-confirm gate.
- AI tutor RCTs: Kestin 2025 Sci Reports ([link](https://www.nature.com/articles/s41598-025-97652-6)) AI tutor beat active-learning class [unverified ~0.7-1.3 SD]; Bastani 2024 PNAS [unverified]: unrestricted GPT lowered exam scores ~17%, guard-railed tutor removed the harm. → AI that gives answers hurts; AI that gives hints helps. Review must force production before reveal.
- Gap: no controlled study of LLM flashcard quality or LLM error detection in learner speech transcripts.

### 4. ASR for learner speech
- **LearnerVoice 2024** ([arXiv 2407.04280](https://arxiv.org/html/2407.04280)): 50 h, 239 tutoring lessons, Korean L1 English learners. Whisper-small WER 18.4% → 10.3% after fine-tuning; **54% of errors sit on learner features** (fillers 37.6%, self-repairs 17.1%). → Stock Whisper cleans up the very hesitations we want to mine; use verbatim-mode prompting, keep audio.
- Graham & Roll 2024 ([PubMed](https://pubmed.ncbi.nlm.nih.gov/38391582/)): Whisper worse on non-native accents; Arabic L1 included.
- de Jong & Bosker 2013 ([slides](https://blog.soton.ac.uk/langsnap/files/2013/04/LANGSNAP_dejong.pdf)): silent-pause threshold 250-300 ms; articulation rate explains ~50% of fluency variance.
- **Uehara 2026** ([arXiv 2608.26137](https://arxiv.org/html/2608.26137)): de Jong composite + LLM scored ρ=0.818 with rater consensus, above a single human rater (0.621). → Speech rate + pause stats from ASR timestamps are a cheap validated progress metric.
- Azure Pronunciation Assessment ([docs](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment)): Arabic not in the supported list (verify). No independent ELSA/Speechace validity study found.
- Arabic learner speech: no Palestinian/Levantine learner corpus exists. Ours would be the first.

### 5. Transcript-mining PoCs
- NICT JLE ([site](https://alaginrc.nict.go.jp/nict_jle/index_E.html)): 1,281 interview transcripts, 167 error-tagged with **47 error tags** → taxonomy to adapt.
- LINDSEI ([UCLouvain](https://uclouvain.be/en/research-institutes/ilc/cecl/lindsei.html)): not error-annotated.
- Hobbyist pipelines with no outcome data: [52 Weeks 2023](https://52weeks.substack.com/p/week-41-speech-to-flashcards), [Traipsing About 2025](https://www.traipsingabout.com/p/how-im-using-ai-to-turbocharge-my), [Voice2Anki](https://github.com/thiswillbeyourgithub/Voice2Anki), [audio2anki](https://osteele.github.io/audio2anki/). Everyone stopped at "cards generated", never at "did it change speech".
- Preply Lesson Insights / italki Lesson Summary: **no published accuracy or effect data.**

### 6. Error correction in conversation
Lyster & Saito 2010 ([ERIC](https://eric.ed.gov/?id=EJ892626)): prompts > recasts, durable, largest on free production. Mackey & Goo 2007: d≈0.75 immediate, holds delayed [unverified]. Li, Zhu & Ellis 2016: immediate slightly better, delayed not harmful [unverified]. Error logs (Lalande 1982, Ferris) improve accuracy [written mode, unverified]. → Prompt, don't show; persistent error log; correcting after the lesson is fine.

### 7. Measurement
- Nation VST (Beglar 2010): English only. **Arabic:** Masrai & Milton 2019 ([LLJ](https://www.tandfonline.com/doi/abs/10.1080/09571736.2016.1258720)), LexArabic 2023 ([ResearchGate](https://www.researchgate.net/publication/375652524)); both MSA. **No dialect vocabulary test exists.** → LexArabic quarterly as an external anchor only.
- ACTFL OPI inter-rater ~0.9 [unverified]. → 15-min recorded monologue rated by Amal on ACTFL descriptors every 4-6 weeks.
- **Single-case design** (n=1), WWC standards ([PDF](https://ies.ed.gov/ncee/wwc/Docs/ReferenceResources/wwc_scd.pdf)): ≥5 data points per phase; multiple-baseline across error types (start correcting type A week 2, B week 5, C week 8).

### 8. Negative results and failure modes
- Duolingo funnel: 4,854 invited → 257 tested (~5%); ~200 h to finish A2; ~15% Day-30 retention for casual users [unverified].
- Anki review debt: community-documented, no peer-reviewed study; Kornell explains the mechanism.
- LLM hallucinated corrections: no study measured false-correction rate on learner transcripts → the tutor-confirm gate gives us the labels for free.
- ASR bias: Koenecke 2020 PNAS ([link](https://www.pnas.org/doi/10.1073/pnas.1915768117)) WER 0.35 vs 0.19 by speaker group [unverified].

### Evidence-based design rules (10)
1. FSRS per item, not fixed intervals or HLR (srs-benchmark).
2. Expect ~10-17% retention gain from personalized review (Lindsey 2014); design the tutor sheet around that.
3. Warn that spaced review feels worse than it works; never shorten intervals on "feels hard" (Kornell 2009).
4. Learner must say the answer before seeing it; hints never answers (Lyster & Saito; Bastani).
5. Keep the tutor-confirm gate; LLMs over-correct (Fang 2023).
6. Enforce level with a whitelist, not a prompt (alignment drift).
7. Verbatim-prompt the ASR; stock Whisper deletes fillers and self-repairs (LearnerVoice).
8. Grade spoken answers on speech rate + pause count from timestamps (Uehara 2026; de Jong).
9. Measure progress as a multiple-baseline single-case study, ≥5 points per phase (WWC).
10. Speaking is the skill apps fail at; log every claim's funding (Duolingo DRR-24-04).

**Open gaps we would be first to fill:** Levantine learner-speech corpus; ELSA/Speechace validity; Preply/italki summary effect data; LLM false-correction rate on transcripts.
