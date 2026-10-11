# Detecting and scoring a learner's spoken errors (vocab, grammar, pronunciation) from lesson transcripts and audio

Context: Anees pipeline (Farsi-native learner of Levantine Arabic, one-to-one tutor lessons). Transcript to Claude Opus readers for vocab/grammar slips, then Python rules mark every Arabic word (credit / half / repeat-of-tutor / new / mistake / not-scored+reason). A mistake counts only with a signal (tutor recast/correction, or learner asked). Pronunciation must never count as a missed word. Grade book v1: 25.6% of 442 words right; 236 untracked/wrong credit, 79 misheard words, 13 missed slips, 3 fake slips.

Research budget note: the web-search account was low on credits, so a few planned lookups (LLM-as-annotator agreement on learner errors, Farsi-to-Arabic transfer, Speak & Improve 2025 top-system numbers) got only search snippets or nothing. Those are listed under Gaps instead of being filled from memory.

## Spoken GEC / error detection for learner speech, and for Arabic / dialectal Arabic (benchmarks, LLM performance, LLM weaknesses)

### Takeaway
Spoken GEC is much harder than written GEC. The official Speak & Improve 2025 cascade baseline (Whisper ASR, then disfluency removal, then BART GEC) gets only P 0.37 / R 0.08 / F0.5 0.22 on feedback edits. In Arabic, few-shot ChatGPT/GPT-4 reached about 64-68 F0.5 on written MSA (QALB). There is no dialectal Arabic GEC benchmark, and LLMs drop sharply on dialects. Opus "finding slips" in Levantine speech transcripts is therefore an unbenchmarked, low-precision task. It needs a project-specific gold set and should be tuned for precision (F0.5).

### Cited Findings
- **Speak & Improve Challenge 2025 task definition:** spoken GEC (SGEC) means producing a grammatically corrected transcription from audio and/or ASR text. The baseline is a cascade: Whisper-small ASR, then a disfluency-detection module (bert-base-uncased, binary fluent/disfluent token tagging, trained on Switchboard Reannotated), then a text GEC model (bart-large fine-tuned on BEA-2019) — [S&I Challenge 2025 Tasks & Baselines, arXiv 2412.11985](https://arxiv.org/html/2412.11985v1)
- **Baseline numbers (dev):** ASR WER 10.4 (sub 4.9, del 4.0, ins 1.5); SGEC output WER 17.3. Feedback-edit scoring (ERRANT F0.5 against M2 files built from fluent manual transcripts plus manual GEC) gave overall **P 0.37, R 0.08, F0.5 0.22**. By error type: R:PREP F0.5 0.416, U:DET 0.376, M:DET 0.282, R:NOUN:NUM 0.277, R:VERB:TENSE 0.166, R:VERB 0.087, R:NOUN 0.087. Lexical substitutions (R:VERB, R:NOUN) are the worst-detected class — [arXiv 2412.11985](https://arxiv.org/html/2412.11985v1)
- **References are built on fluent text:** disfluencies (false starts, repetitions, fillers) are removed before grammar is judged. Disfluency handling is a separate first stage, not part of "error" — [arXiv 2412.11985](https://arxiv.org/html/2412.11985v1)
- **Arabic GEC with LLMs (QALB, written MSA):**
  - ChatGPT 5-shot expert prompting on QALB-2014: P 66.53 / R 61.62 / F0.5 65.49.
  - GPT-4 5-shot CoT: P 69.46 / R 61.96 / F0.5 67.82.
  - On the L2-learner set QALB-2015, ChatGPT 3-shot: P 52.33 / R 47.57 / F0.5 54.10, so learner text is much harder.
  - Fine-tuned models reached SOTA of about 73.3 F1.
  - Shot count matters: 1-shot to 3-shot CoT went from F0.5 56.55 to 63.71, with no gain at 5-shot.
  - Source: [Kwon et al., "Beyond English: Evaluating LLMs for Arabic GEC", ArabicNLP 2023](https://aclanthology.org/2023.arabicnlp-1.9.pdf)
- **Same paper, LLM weaknesses:** over-correction, low precision, extraneous explanations needing post-processing. The study covers only MSA, not dialectal Arabic — [ArabicNLP 2023](https://aclanthology.org/2023.arabicnlp-1.9.pdf)
- **Over-correction is a general LLM GEC failure:** LLMs do well on fluency edits but fail to keep to minimal edits, rewriting correct text — [Goto et al., Edit-level Majority Voting, arXiv 2605.13624](https://arxiv.org/html/2605.13624v1); the same pattern is shown for learner Chinese — [PMC11524451](https://pmc.ncbi.nlm.nih.gov/articles/PMC11524451/)
- **Edit-level self-consistency fixes much of it:** sample k=8 corrections, extract edits with ERRANT, and keep only edits that appear in at least tau of the 8 (tau tuned on dev data).
  - BEA-19: Qwen3-8B F0.5 56.3 to 68.7 (P 54.8 to 73.8, R 62.9 to 53.7); Llama-3.1-8B 54.0 to 63.1.
  - Korean learner set: +34.6 to +47.1 F0.5.
  - It **hurt** on fluency-oriented JFLEG (-1.9 to -2.3) and German Falko-Merlin (-0.7 to -6.8).
  - Source: [arXiv 2605.13624](https://arxiv.org/html/2605.13624v1)
- **LLMs are weak on Arabic dialects:** DialectalArabicMMLU (19 open LLMs, 1B-13B) averaged 60.2% on MSA vs 18.4% on dialects. Syrian (the closest to Levantine) averaged 15.4%. Performance "consistently declines across all dialects compared to MSA", and explicit dialect conditioning did not reliably help. The models tested were open-weight; frontier models (Claude Opus) were not — [DialectalArabicMMLU, arXiv 2510.27543](https://arxiv.org/html/2510.27543v1)
- **Dialect translation lags MSA too:** models translate to MSA better than to non-standardized dialects — [Cultural Benchmarking of LLMs in MSA and Arabic Dialectal Dialogue, ACL 2026](https://aclanthology.org/2026.acl-long.963.pdf)

### Inferences
- An MSA-trained "grammar sense" will flag correct Levantine forms as errors. Examples: b- imperfect prefix, negation ma/mish, ha- demonstratives, dropped case endings, colloquial lexicon. These likely feed the "fake slips" and "wrong credit" buckets. **Test:** a fixed regression set of correct Levantine utterances that differ from MSA. Opus must flag 0 of them; track the false-positive rate per rule.
- Tune for precision (F0.5), since a fake slip costs more than a missed one. **Test:** score Opus slips against Medi's manual review with ERRANT-style span matching and report P, R and F0.5 per lesson. Track 13 missed vs 3 fake as R and P explicitly rather than a single accuracy number.
- **Test (self-consistency):** run the Opus slip-reader N times (e.g. 5-8 samples) and keep slips found in at least tau runs. Tune tau on graded lessons, and expect a precision gain at some recall cost, as in Goto et al.
- Disfluency should be its own stage. A false start or self-repair ("ana ruht... rihit") must be tagged disfluent and not scored as a mistake or as two words. **Test:** fixture utterances containing repetitions, fillers and self-repairs. Assert no mistake marks and no double credit.
- Because the S&I baseline's lexical-substitution F0.5 is under 0.1, vocab slips should probably be confirmed by the tutor signal rather than detected open-loop. That matches Anees's "signal required" design.

### Gaps
- No public benchmark exists for GEC on dialectal or spoken Arabic. ZAEBUC (Emirati university essays) is written, mostly MSA. I could not retrieve ZAEBUC or Arabic learner-corpus LLM numbers within budget.
- I did not retrieve the top Speak & Improve 2025 systems' SGEC F0.5 (e.g. Interspeech 2025 end-to-end papers such as [Qian et al.](https://www.isca-archive.org/interspeech_2025/qian25_interspeech.pdf)) beyond the baseline.
- There are no published numbers for Claude Opus on Levantine grammar judgment.

## Corrective feedback taxonomy (Lyster & Ranta) and automatic detection of recasts / corrections / uptake

### Takeaway
Recasts are the most common tutor move (55%) and the least likely to show learner repair. So "tutor recast" is the main signal, but it is easy to miss. Also, a supplied word in tutoring talk is ambiguous: it can be a correction, help, a confirmation check, or a continuation. A 2026 study on ASR-transcribed online tutoring found humans agree on whether a corrective-feedback episode exists at only kappa .18. Automatic signal detection therefore needs a narrow, operational definition and its own gold set.

### Cited Findings
- **Lyster & Ranta (1997) taxonomy and distribution** (18.3 h, 27 lessons, 3,268 student turns, 1,104 erroneous or needing repair): recast 55%, elicitation 14%, clarification request 11%, metalinguistic 8%, explicit correction 7%, repetition 5% — [Lyster & Ranta 1997, SSLA](https://l2aquisition.wordpress.com/wp-content/uploads/2017/06/corrective-feedback-and-learner-uptake-negotiation-of-form-in-communicative-classrooms.pdf)
- **Uptake and repair by feedback type:**

  | Type | n | Repair | Needs-repair | No uptake | Kind of repair |
  |---|---|---|---|---|---|
  | Recast | 375 | 18% | 13% | 69% | all repetition/incorporation |
  | Explicit correction | 50 | 36% | 14% | 50% | |
  | Elicitation | 94 | 46% | 54% | 0% | all learner-generated |
  | Metalinguistic | 58 | 45% | 41% | 14% | |
  | Clarification request | 73 | 28% | 60% | 12% | |
  | Repetition | 36 | 31% | 47% | 22% | |

  Source: [Lyster & Ranta 1997](https://l2aquisition.wordpress.com/wp-content/uploads/2017/06/corrective-feedback-and-learner-uptake-negotiation-of-form-in-communicative-classrooms.pdf)
- **Definitions** (same source):
  - Uptake: a learner utterance immediately after feedback that reacts to it.
  - Repair: a correct reformulation in a single learner turn (repetition, incorporation, self-repair, peer-repair).
  - Needs-repair: acknowledgment, same error, different error, off target, hesitation, partial repair.
- **Reliability of finding CF episodes in ASR-transcribed online tutoring** (2026): two coders screened 1,004 predefined learner turns (6 adult lessons) with a frozen manual.
  - One flagged 12 turns, the other 19; only 3 overlapped.
  - Raw agreement .975 but Cohen's kappa .182 (95% CI -.011 to .377); positive specific agreement .194; Gwet's AC1 .974; PABAK .950. Leave-one-lesson-out kappa ranged .086-.240.
  - Among the 3 shared positives, classification fields matched 20/20, 11/20 and 18/20 (the perfect one was the manual's worked example).
  - Source: [Abdelaty & Jebril, Frontiers in Education 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full)
- **Same study, why coders disagree:**
  - A supplied word may be a correction, lexical help, a confirmation check, or an ordinary continuation.
  - A deviant learner form may be an error, a false start, or an ASR substitution.
  - Tutors may address meaning but not form.
  - Coders linked different tutor turns to the same learner turn.
  - ASR flattens intonation, misrenders morphology, and turns target forms into other words.

  Their recommendations: define the candidate universe; separate identification from classification; publish the confusion matrix and prevalence; report class-specific agreement; keep coders independent before adjudication — [Frontiers 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full)
- **CF episodes are rare:** about 1.2-1.9% of learner turns in naturalistic online tutoring — [Frontiers 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full). Classroom CF was much denser in Lyster & Ranta (1,104 of 3,268 turns needed repair) — [Lyster & Ranta 1997](https://l2aquisition.wordpress.com/wp-content/uploads/2017/06/corrective-feedback-and-learner-uptake-negotiation-of-form-in-communicative-classrooms.pdf)
- **LLM dialogue-act tagging exists:** generative-AI classification of tutor dialogue acts has been studied as an easier alternative to trained classifiers. Numbers were not retrieved — [Automated Classification of Tutors' Dialogue Acts Using Generative AI, arXiv 2509.09125](https://arxiv.org/pdf/2509.09125)

### Inferences
- Do not use raw accuracy for signal detection; most turns are negatives. Report positive-class P/R and positive specific agreement. **Test:** for each graded lesson, compute the confusion matrix of "signal present" (Opus vs Medi) over a predefined unit set (each learner turn plus the next tutor turn).
- Split the pipeline as the Frontiers authors recommend:
  - Stage 1 identifies a candidate episode (learner turn plus linked tutor turn).
  - Stage 2 classifies it: recast / explicit / elicitation / clarification request / metalinguistic / repetition / learner-asked / lexical-help-not-correction / confirmation / continuation.
  - **Test:** gold-label both stages separately so failures can be attributed.
- Add the confusable "not a correction" classes explicitly: tutor supplies a word the learner was searching for (lexical help, i.e. a new word, not a mistake); tutor confirmation echo; tutor continuation. **Test:** fixtures where the tutor repeats the learner's correct word must give "repeat/confirm", never "mistake".
- Recasts show repair only 18% of the time, so the learner repeating the corrected form cannot be required to confirm a recast. Use uptake/repair as extra evidence and for scoring the next encounter. **Test:** a recast with no uptake must still yield a mistake mark (if the learner form differs from the recast); a recast followed by a correct learner repeat yields mistake plus a "repaired" annotation; the repeated word is credited as a repeat-of-tutor, not as fresh production.
- A recast is detected by aligning the learner turn with the following tutor turn: high overlap with one or two changed tokens. That can be computed deterministically (edit distance on normalized Arabic tokens) before Opus is asked.
  - **Test:** a unit test for the aligner, and an "ASR-noise guard": if the changed token is a near-homophone (differs only in emphatic/plain, length, or pharyngeal), route it to pronunciation/not-scored, not to grammar/vocab.

### Gaps
- I found no published numeric benchmark for automatic recast detection in L2 tutoring dialogue (2023-2026) within budget. LLM performance numbers on Lyster-Ranta categories were not retrieved.

## Separating pronunciation from lexical/grammar errors: MDD, GOP, Arabic, L1 Farsi transfer

### Takeaway
State-of-the-art Arabic MDD (IQRA 2026, MSA and Qur'anic) reaches only about 0.72 phoneme-level F1, with a 30% false-accept rate even for the best system. The baseline had 0.30 precision. Phoneme-level judgments are therefore too noisy to score automatically, and pronunciation should be quarantined from word scoring. Practically, the 79 "misheard words" bucket is mostly ASR/accent noise and should go to a not-scored(pronunciation/ASR) mark, never to a mistake.

### Cited Findings
- **IQRA 2026 Interspeech challenge (MSA MDD):** predict the pronounced phoneme sequence given audio and a vowelized reference; ranked by phoneme-level F1. Training data:
  - Iqra_train: 74k utterances, about 79 h (Common Voice Arabic plus Qur'an).
  - Iqra_TTS: 55.4k synthetic utterances.
  - Iqra_Extra_IS26: 1,333 real mispronounced utterances from native speakers told to make substitutions.
  - Test set QuranMB.v2: 1,643 utterances, about 2.5 h.
  - Source: [IQRA 2026, arXiv 2603.29087](https://arxiv.org/html/2603.29087v2)
- **IQRA 2026 results:**
  - Baseline (mHuBERT): F1 0.441, P 0.304, R 0.771, PER 0.131.
  - 1st place: F1 0.720, P 0.742, R 0.700, false-reject 1.75%, false-accept 30.0%, correct diagnosis 81.9%, PER 0.037.
  - Top six systems: F1 0.67-0.72.
  - Systems that used real mispronounced speech beat synthetic-only augmentation.
  - Source: [arXiv 2603.29087](https://arxiv.org/html/2603.29087v2)
- **Domain caveat:** MSA is acquired by dialect speakers whose L1-interference errors differ from those of foreign learners, so benchmark data are native-dialect speakers reading Qur'an/MSA, not L2 conversational Levantine — [arXiv 2603.29087](https://arxiv.org/html/2603.29087v2); the precursor Iqra'Eval 2025 was the first open MDD benchmark for Qur'anic recitation — [ArabicNLP 2025 shared task](https://aclanthology.org/2025.arabicnlp-sharedtasks.61/)
- **ASR recognizes L2 speech worse than L1 speech:** a ReCALL study comparing L1 listeners and ASR on L2 intelligibility cites earlier work finding about 24-26% fewer words recognized for L2 speakers. This is a search-snippet figure; the exact comparison was not verified — [ReCALL, Cambridge](https://www.cambridge.org/core/journals/recall/article/assessment-of-l2-intelligibility-comparing-l1-listeners-and-automatic-speech-recognition/7E499AD990383AC65A9688BB5BE17887)
- **L2 learners differ on several axes at once:** they make pronunciation errors, use different words and grammar from natives, and produce more disfluencies, all of which degrade ASR — [Radboud repository, ASR for L2 pronunciation](https://repository.ubn.ru.nl/bitstream/handle/2066/190153/1/190153.pdf)
- **Emphatic and pharyngeal consonants are hard for learners whose L1 lacks them:** in English speakers they involve pharyngeal constriction that learners tend to under-produce — [PMC9932739](https://pmc.ncbi.nlm.nih.gov/articles/PMC9932739/); [JALTA, English speakers' acquisition of Arabic emphatics/pharyngeals](https://scholarworks.iu.edu/iupjournals/index.php/jalta/article/download/7834/758)

### Inferences
- The likely Farsi-to-Arabic confusions follow from phoneme inventories. Persian has no pharyngeals or emphatics and merges several Arabic letters in loanwords (s/ṣ/θ, z/ð/ḍ/ẓ, t/ṭ, h/ḥ, ʔ/ʕ). This is my inference from phonology; no source was retrieved.
  - These merges are exactly the contrasts where ASR may output a different real word (e.g. ḥ vs h, ʕ vs ʔ, ṣ vs s minimal pairs).
  - **Test:** a "pronunciation-equivalence" normalizer that collapses these pairs plus vowel length, and a rule: if learner token ≈ target token under that normalizer, mark it pron/ASR (not scored), never a mistake.
- **Test:** for every word currently marked "mistake", assert there is a non-phonetic difference (different root, wrong morphology/agreement, wrong lexeme) after pronunciation-equivalence normalization. Otherwise downgrade it.
- Audio-level GOP/MDD is not reliable enough (around 0.7 F1, 30% false accepts at best, on native MSA reading) to produce learner-facing pronunciation scores for conversational Levantine. If used at all, use it to flag "likely ASR mishearing" (low ASR confidence plus low GOP), which justifies not-scored.
  - **Test:** word-level ASR confidence thresholds; words below the threshold get a not-scored(low-confidence) mark. Measure what share of the 79 misheard words this catches.
- Keep tutor pronunciation corrections ("not 'hamam', ḥammām") as a separate signal class, "pron-correction". It must never feed vocab/grammar mistake counts, per the Anees rule. **Test:** fixture where the tutor corrects only a sound; assert the word gets credit (or pron-note) and no mistake.

### Gaps
- No retrieved study gives Persian-L1 learners' Arabic pronunciation error rates. I found no MDD or GOP work on Levantine or L2 conversational Arabic, and no Arabic GOP numbers specifically.

## Vocabulary tracking from speech: productive vocab, lexical diversity, crediting words vs repeats/echoes, spaced repetition

### Takeaway
Repeating a word the interlocutor just said (lexical alignment/priming) is a well-documented and pervasive dialogue phenomenon, and L2 speakers align more with some interlocutors than others. So a word used right after the tutor said it is weaker evidence of productive knowledge than a spontaneous use. The pipeline's "repeat-of-tutor" mark is well-founded. The 236 untracked/wrong-credit errors suggest the window, normalization or lemma matching for "repeat" vs "credit" is the biggest fix.

### Cited Findings
- **Lexical alignment** is interlocutors adopting the same terms for the same concepts; a systematic review covers how to measure and implement it — [Measuring and implementing lexical alignment: systematic review, Computer Speech & Language 2024](https://www.sciencedirect.com/science/article/pii/S0885230824001141)
- **Alignment is computable and predictive:** lexical and syntactic repetition between dialogue partners are "reliable and computationally exploitable predictors" of task success — [Reitter & Moore 2014, JML](https://david-reitter.com/pub/reitter2014JML-alignment.pdf)
- **L2 alignment depends on the partner:** L2 speakers' lexical alignment varies with the interlocutor's linguistic competence — [Bilingualism: Language and Cognition](https://www.cambridge.org/core/journals/bilingualism-language-and-cognition/article/effects-of-interlocutors-linguistic-competence-on-l2-speakers-lexical-alignment/D002BECCFFCDFF560EB50A4AC437FC70)
- **Repetition is the operational measure:** lexical alignment is measured as word repetition between interlocutors (A's word reused by B) — [PMC11831868, linguistic alignment in collaborative dialogue](https://pmc.ncbi.nlm.nih.gov/articles/PMC11831868/)
- **Recast repairs are repetition by definition:** all repairs after recasts and explicit corrections were "repetition/incorporation" (0% learner-generated) — [Lyster & Ranta 1997](https://l2aquisition.wordpress.com/wp-content/uploads/2017/06/corrective-feedback-and-learner-uptake-negotiation-of-form-in-communicative-classrooms.pdf)

### Inferences
- Credit tiers should reflect the evidence:
  - spontaneous use (the word has not appeared in the tutor's last N turns, or in this lesson): full credit;
  - delayed reuse later in the lesson: credit, a "consolidating" signal;
  - immediate echo of the tutor (within 1-2 turns): repeat-of-tutor, no productive credit;
  - repair after a recast: repeat-of-tutor plus a note that the mistake was repaired.
  - **Test:** parameterize the echo window and unit-test the boundaries (same turn, next turn, 3+ turns, earlier lesson).
- Matching must be at lemma/root level with Levantine normalization (clitics such as b-, ha-, -ak/-ik, w-, l-; spelling variants of taa marbuta / alef / hamza; Arabizi or Farsi-script rendering). Otherwise inflected echoes escape the repeat detector and get wrongly credited, which is probably part of the 236.
  - **Test:** a golden table of (tutor form, learner form) pairs that must count as the same lexeme, and pairs that must not (different roots sharing letters).
- Track a per-word state history (first exposure, tutor-supplied, echoed, spontaneous use, mistake with signal, repaired) instead of a single mark. Spaced-repetition scheduling should use only spontaneous-use and signaled-mistake events as recall outcomes; echoes are exposures, not successful recalls. **Test:** an SRS fixture asserting echoes don't advance the interval.
- Lexical diversity metrics (MTLD/MATTR) on learner turns are possible as trend indicators. They need a minimum token count and must exclude echoes and disfluent repetitions, or they will inflate. **Test:** exclude repeat-of-tutor tokens and disfluencies before computing; assert stable output under fixture reordering.

### Gaps
- I did not retrieve quantitative studies on the right echo window (in turns or seconds) for separating priming from productive knowledge in L2 tutoring. Concrete MTLD/MATTR reliability numbers for short spoken L2 samples were also not retrieved this round.

## LLM-as-annotator reliability for learner corpora (agreement, prompting, self-consistency, adjudication, rubric, few-shot)

### Takeaway
Human annotators themselves agree only modestly on what counts as a learner error: NUCLE kappa was 0.39 for identification and 0.55 for classification. CF-episode identification in tutoring was kappa .18. So "LLM vs one human" agreement has a low ceiling, and a single manual review is a noisy gold standard. Self-consistency (majority voting over samples at the edit level) and few-shot gold examples are the best-evidenced levers for raising LLM precision.

### Cited Findings
- **NUCLE inter-annotator agreement** (3 annotators, token-level kappa): error identification averaged 0.388 (pairs 0.323-0.478); error-type classification 0.548; exact correction 0.484 — [Dahlmeier, Ng & Wu 2013, BEA](https://aclanthology.org/W13-1703.pdf)
- **CF identification agreement** in naturalistic tutoring: kappa .182, positive agreement .194 (details in the corrective-feedback section) — [Frontiers 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full)
- **Few-shot gold examples help, with a plateau:** for ChatGPT on QALB-2014, F0.5 rose from 56.55 (1-shot CoT) to 63.71 (3-shot) and stayed flat at 5-shot (63.61). Expert-persona prompting gave 58.42, 64.90 and 65.49 — [ArabicNLP 2023](https://aclanthology.org/2023.arabicnlp-1.9.pdf)
- **Edit-level majority voting** (k=8 samples, threshold tau) raised precision by 6-19 points and F0.5 by up to 12.4 on BEA-19, but hurt fluency-oriented sets — [arXiv 2605.13624](https://arxiv.org/html/2605.13624v1)
- **LLM agreement vs human-human agreement:** in MT-quality annotation (2026), LLM agreement with human annotators exceeds human-human agreement for some tasks, but both vary by task — [LLMs for MT Quality Annotation, arXiv 2610.10918](https://arxiv.org/html/2610.10918v1)
- **Multi-LLM disagreement flags human label errors:** human error rates rose as LLM agreement fell, from 0% at full agreement to 76% at the lowest score, and the lowest-agreement stratum held only 6.5% of annotations. So disagreement focuses review on a small slice — [medRxiv 2026, Multi-LLM Disagreement as a Detector of Human Annotation Errors](https://www.medrxiv.org/content/10.64898/2026.05.04.26352392v1.full-text)
- **Alt-test protocol:** to validate an LLM annotator against at least 3 humans, leave one human out, compare the LLM and the held-out human to the remaining humans' collective labels, and check whether the LLM falls on the parity line — [GovTech Singapore blog](https://blog.ai.gov.sg/validating-annotation-agreement-between-humans-and-llms/)

### Inferences
- Medi's full manual review is the gold standard, but annotation research shows a single annotator misses some errors. **Test:** when Opus and Medi disagree, log the disagreement for adjudication rather than auto-counting it as a pipeline error. Track the share of grade-book "errors" that Medi reverses on second look (the 3 fake and 13 missed slips are small enough to adjudicate one by one).
- Use multi-run or multi-reader disagreement as a review-routing signal: high-agreement items auto-accept; low-agreement items go to Medi/Amal. **Test:** measure precision in the high-agreement stratum versus the low-agreement stratum on graded lessons.
- Few-shot with gold examples drawn from Medi's corrections (the medi-corrections / correction-rules data) should be the main prompt lever. Expect diminishing returns after about 3 well-chosen examples per error class. **Test:** an ablation of 0/1/3/5 gold examples on held-out graded lessons.
- Rubric/checklist prompting maps directly onto Anees's mark set. Make the LLM output one decision per word with a required reason code and the evidence turn ID (tutor recast turn, or learner question turn). Then Python can verify the evidence exists. **Test:** schema validation that every "mistake" cites a tutor-turn or learner-ask turn ID present in the transcript, and that the cited turn actually contains the corrected form (string check).
- Keep identification and classification separate in evaluation, so the low agreement on "is there an error/episode" doesn't hide good agreement on "what type".

### Gaps
- No retrieved study measures LLM-vs-human agreement specifically on learner error annotation of speech transcripts, or on Arabic learner data. Rubric-vs-free-form prompting comparisons for GEC annotation were not retrieved.

## Error taxonomy and metrics: P/R/F0.5, span- vs token-level, kappa

### Takeaway
GEC convention is ERRANT-style edit (span) matching scored with F0.5, which weights precision twice as much as recall, broken down by error type. Agreement should be reported with class-specific statistics because errors are rare. Anees's single "25.6% tracked right" figure should be broken into per-mark confusion matrices, plus P/R/F0.5 on slips and positive-class agreement on signals.

### Cited Findings
- **Scoring convention:** S&I 2025 scores feedback with ERRANT F0.5 on M2 edit files, per error type (R:PREP, M:DET, R:VERB:TENSE, ...). It scores ASR separately with WER (NIST sclite) and full SGEC output with WER — [arXiv 2412.11985](https://arxiv.org/html/2412.11985v1)
- **ERRANT is the standard edit extractor for LLM GEC output** (also JP-ERRANT for Japanese), and edits are counted at span level — [arXiv 2605.13624](https://arxiv.org/html/2605.13624v1). Edit-based GEC evaluation research continues (TACL) — [TACL, GEC Evaluation by Optimally...](https://direct.mit.edu/tacl/article/doi/10.1162/TACL.a.747/137437/Grammatical-Error-Correction-Evaluation-by)
- **MDD metrics:** phoneme-level F1 plus true-accept, false-reject, false-accept, correct-diagnosis, PER — [arXiv 2603.29087](https://arxiv.org/html/2603.29087v2)
- **NUCLE measured three levels separately** with token-level kappa: identification, classification, exact correction — [W13-1703](https://aclanthology.org/W13-1703.pdf)
- **Rare-event agreement:** overall agreement (.975) and AC1/PABAK (.95-.97) can look excellent while kappa (.18) and positive specific agreement (.19) show the positive class is not reproducible. Report the full 2x2 table, prevalence, and class-specific agreement — [Frontiers 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1949267/full)

### Inferences
- Proposed Anees grade-book metrics:
  1. **Per-word mark confusion matrix** (gold vs pipeline over credit / half / repeat / new / mistake / not-scored), with per-class P/R. The 236 wrong-credit errors will then show which off-diagonal cells dominate (e.g. gold repeat, pipeline credit).
  2. **Slip detection:** span-level P/R/F0.5, where a slip matches if it covers the same learner token(s) and the same error class.
  3. **Signal detection:** positive specific agreement plus kappa over predefined learner-turn units.
  4. **ASR layer:** WER of learner Arabic tokens against Medi's corrected transcript, reported separately so the 79 misheard words aren't blamed on scoring rules.
  5. **Error-type breakdown** (lexical / morphological agreement / verb form / preposition / pronunciation-only / disfluency), as S&I does with ERRANT types.
- **Test:** a CI check that fails if per-class precision for "mistake" drops below a set threshold on frozen graded lessons, or if any "mistake" lacks a signal, or if any pronunciation-only difference is scored as a mistake. This turns the Anees rules into regression tests.
- Use separate frozen dev and test lessons. Tune thresholds (tau, echo window, ASR confidence) on dev only, and report on test, to avoid overfitting to the one fully reviewed lesson.

### Gaps
- There is no ERRANT-equivalent for Levantine Arabic. An Arabic edit extractor and type classifier would need to be built or adapted (e.g. on CAMeL Tools morphology). Not researched this round.
