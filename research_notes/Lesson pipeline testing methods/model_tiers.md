# Comparing LLM model tiers for annotation/judging in the Anees lesson pipeline

Research date: 2026-10-10. Scope: Fable 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5 (plus OpenAI and Google tiers) as "readers", adjudicators and translators of Levantine-Arabic lesson transcripts (Farsi-native learner, English/Arabic code-switching, Arabizi). Runs go through `claude -p` on a subscription, not API billing.

Labels used below: **[Documented]** means a cited source states it. **[Inferred]** means it is my reasoning from the sources. **[Not fetched]** means a well-known paper cited from memory with its arXiv ID; its exact numbers were not checked in this session.

---

## Q1. What do current model cards and benchmarks (2025-2026) say about the Claude tiers and competitors on multilingual and Arabic tasks?

### Takeaway
All four Claude 5.5-generation tiers are officially documented, with dates, prices and effort defaults. None of their public pages report Arabic or dialect scores. The nearest Arabic evidence is HELM Arabic, where Claude 4.7 Opus scored 0.841 and Claude 4.6 Sonnet 0.815, and older leaderboards such as BALSAM. These show a small gap between flagship and mid tiers on mostly-MSA tasks, and say nothing about Levantine learner speech. Anthropic's own vendor benchmarks show a large Haiku-to-Sonnet gap on agentic tasks.

### Cited Findings
**Lineup and dates [Documented]**
- Claude API IDs are `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`. All have a 1M-token context, 128K max output and a June 2026 reliable knowledge cutoff. Comparative latency runs Fable "Slower", Opus "Moderate", Sonnet "Fast", Haiku "Fastest". — [Claude models overview](https://platform.claude.com/docs/en/models/overview)
- List prices per million tokens (input/output): Fable 5.1 $10/$50; Opus 5.5 $4/$20; Sonnet 5.5 $2/$10; Haiku 5.5 $0.10/$0.50 for prompts up to 100K tokens ($0.50/$2.50 above that). Batch API is 50% off. Cache reads cost 10% of base input, but 2.5% on Fable 5.1 and 5% on Opus 5.5 and Sonnet 5.5. — [Models overview](https://platform.claude.com/docs/en/models/overview); [Haiku 5.5 page](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
- Thinking: Fable 5.1 and Opus 5.5 run adaptive thinking that is always on. Sonnet 5.5 and Haiku 5.5 run adaptive thinking that can be reduced. Default effort is `high` on Fable, `medium` on Opus, `high` on Sonnet and `medium` on Haiku. — [Models overview](https://platform.claude.com/docs/en/models/overview)
- Release dates: Fable 5.1 retirement is "not sooner than Sept 1, 2027", which implies release around 2026-09-01 (the release date itself was not fetched). Opus 5.5 was released 2026-09-22, Sonnet 5.5 on 2026-09-28 and Haiku 5.5 on 2026-10-07. — [Opus 5.5 announcement](https://www.anthropic.com/claude-opus-5-5); [Sonnet 5.5 page](https://platform.claude.com/docs/en/models/sonnet-5-5/overview); [Haiku 5.5 page](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
- On Sonnet 5.5 and Haiku 5.5, setting non-default `temperature`, `top_p` or `top_k` returns a 400 error. Haiku 5.5's docs say to omit them. — [Sonnet 5.5 page](https://platform.claude.com/docs/en/models/sonnet-5-5/overview); [Haiku 5.5 page](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
- Haiku 5.5 uses the tokenizer introduced with Claude 4.7, so the same text counts as about 30% more tokens than on Haiku 4.5. Minimum cacheable prompt is 512 tokens. — [Haiku 5.5 page](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
- Anthropic's docs say: "start with Claude Opus 5.5 for most workloads." Use Fable 5.1 "when your evals on Claude Opus 5.5 at higher effort still fall short." Haiku 5.5 is positioned for "classification, extraction, and routing." — [Models overview](https://platform.claude.com/docs/en/models/overview)

**Vendor benchmarks [Documented; vendor-reported, none Arabic-specific]**
- In the Opus 5.5 announcement (2026-09-22), Opus 5.5 beats Fable 5.1 on every listed benchmark. Examples: GDPval-AA v2.1 1846 vs 1735; HLE with tools 67.7% vs 65.6%; Terminal-Bench 4.0 66.4% vs 55.8%. The comparison columns are GPT-6 Astra and GPT-5.6 Sol. Anthropic says Opus 5.5 "performs at the level of Claude Fable 5.1 on most work" and that the gap is narrower in real use than the scores suggest. The page reports no multilingual or MMMLU row. Results use adaptive thinking at max effort. Effort levels are Low, Med, High, Xhigh and Max. — [Opus 5.5 announcement](https://www.anthropic.com/claude-opus-5-5)
- The Claude Opus 5 System Card evaluates multilingual ability on GMMLU, INCLUDE and MILU across 42 languages. A secondary aggregator lists Opus 5 at GMMLU 92.5% and Opus 5.5 at 94.3%. — [Opus 5 System Card PDF](https://www-cdn.anthropic.com/c5fbac3f0b1280a933ebd26d3cb8bb9f5bdeaf48/Claude%20Opus%205%20System%20Card.pdf); [BenchLM aggregator](https://benchlm.ai/models/claude-opus-5) (secondary)
- Haiku 5.5 versus Sonnet 5.5, at max effort and secondary-reported from Anthropic figures: OSWorld 2.1 72.4% vs 83.9%; GDPval-AA 1620 vs 1840; Terminal-Bench 4.0 39.2% vs 70.6%. At Haiku's default medium effort, GDPval-AA reportedly drops to 1277. Apidog notes that no independent lab had published Haiku 5.5 results. — [computingforgeeks](https://computingforgeeks.com/claude-haiku-5-5-released-features-benchmarks/); [apidog](https://apidog.com/blog/claude-haiku-5-5-benchmarks/) (secondary sources; release-date details conflicted between them, and the official docs say 2026-10-07)

**Arabic leaderboards (nearest generations) [Documented]**
- HELM Arabic (Stanford CRFM, search snippet; the live page did not render when fetched):
  - Arabic.AI LLM-X (2026-06-07): 0.919
  - Claude 4.7 Opus: 0.841
  - GPT-5.4 (2026-03-05): 0.825
  - GPT-5.1 (2025-11-13): 0.817
  - Claude 4.6 Sonnet: 0.815
  - GPT-4.1: 0.814

  No Claude 5.x entries were visible in the snippet. — [HELM Arabic](https://crfm.stanford.edu/helm/arabic/latest/)
- BALSAM (arXiv 2507.22603, July 2025; 78 tasks, 52K examples, blind test set; scored by LLM judge on a 0-3 scale):
  - GPT-4o: 2.05
  - Gemini 2.0 Flash: 2.02
  - Claude Sonnet 3.5: 1.99
  - DeepSeek V3: 1.99
  - Qwen-2.5 32B: 1.80
  - Gemma2 9B: 1.75
  - Command R+ (104B): 1.73 vs Command-r7b: 1.51
  - Mistral large (123B): 1.44 vs Arabic-tuned Mistral-saba (24B): 1.81

  The authors write: "model size is not a sufficient predictor of performance." The benchmark includes dialect translation and dialect ID tasks but reports no separate dialect scores. — [BALSAM](https://arxiv.org/html/2507.22603v1)

### Inferences
- [Inferred] The newest tiers have no public Arabic or dialect numbers. The documented flagship-to-mid gap on Arabic is about 0.03 on HELM Arabic (Opus 4.7 vs Sonnet 4.6), which suggests Opus and Sonnet may be close on Arabic comprehension. The Haiku gap is unmeasured on Arabic and large on Anthropic's reasoning-heavy benchmarks. Anees's own gold set is the only trustworthy evidence.
- [Inferred] Vendor benchmarks run at max effort. The `claude -p` default effort differs by tier (medium on Opus and Haiku, high on Fable and Sonnet), so an unpinned comparison mixes tier and effort.
- [Inferred] Temperature cannot be set on the 5.5 tiers, so repeated runs vary. Plan several runs per model and do not assume one run is representative.

### Gaps
- No Arabic, Levantine, Arabizi or code-switching results were found for Fable 5.1, Opus 5.5, Sonnet 5.5 or Haiku 5.5. The 5.5 system cards (linked from the docs) were not fetched and may hold GMMLU per-language rows.
- No dialect-level comparison of current OpenAI GPT-5.x and Google Gemini tiers (Pro vs Flash) was found.
- Fable 5.1's exact release date was not fetched.

---

## Q2. Do smaller models plus voting match bigger models for annotation and judging? What do LLM-jury results show?

### Takeaway
PoLL (Verga et al., Cohere, April 2024) found that a panel of three small models from different families agreed with humans better than GPT-4 alone and cost 7-8x less. A key reason was that the large judge "over-reasoned" and used outside knowledge. Repeated voting does not always help, though: Chen et al. (NeurIPS 2024) show accuracy can rise and then fall as calls increase, because hard items get worse under voting.

### Cited Findings
- **PoLL panel and agreement.** The panel was Command R, Claude 3 Haiku and GPT-3.5. Cohen's kappa against human judgments, PoLL vs GPT-4: NQ 0.763 vs 0.627; TriviaQA 0.906 vs 0.841; HotpotQA 0.867 vs 0.830. Voting was max (majority) for binary QA judgments and average pooling for 1-5 scores (Chatbot Arena Hard). — [Verga et al. 2024, arXiv 2404.18796](https://arxiv.org/html/2404.18796v2)
- **PoLL cost.** PoLL cost $1.25/$4.25 per MTok against GPT-4 Turbo's $10/$30, which the paper calls "seven to eight times less expensive." — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)
- **Why GPT-4 judged worse.** The authors hypothesize GPT-4 was "over-reasoning and injecting too much background knowledge." Its kappa was very prompt-sensitive: 0.518 zero-shot vs 0.725 with a "don't overthink" instruction. GPT-4 also showed intra-family bias, ranking a GPT-4 variant at position 2 against its Arena position of 4. — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)
- **PoLL limitations.** Only three judge settings were studied. Math and reasoning were not explored. Panel selection was left to future work. — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)
- **Voting can hurt.** Vote and Filter-Vote accuracy "can first increase but then decrease" as LM calls increase. More calls help on easy queries and hurt on hard ones, so a mixed-difficulty task can peak early. The authors give a scaling model that fits the best number of calls from a small sample. Cost was not analyzed. — [Chen et al. 2024, arXiv 2403.02419](https://arxiv.org/html/2403.02419v2)
- **Judge choice matters for Arabic.** In BALSAM, GPT-4 and Gemini as judges correlated with humans "nearly identical[ly]", and both beat GPT-4o-mini "by a sizable margin." LLM-judge vs human correlation ran 0.824-0.977 (mean 0.918). Inter-judge agreement averaged 0.750. — [BALSAM](https://arxiv.org/html/2507.22603v1)
- **Arabic error correction.** Kwon et al. (ArabicNLP 2023) found GPT-4 reached 65.49 F1 with expert prompting on Arabic GEC. Instruction-tuned LLMs "regardless of their size" were beaten by smaller fully fine-tuned models. The best synthetic-data model reached 73.29 F1 on QALB-2014 (some listings give 72.19). — [Kwon et al., arXiv 2312.08400](https://export.arxiv.org/abs/2312.08400); [ArabicNLP 2023 PDF](https://preview.aclanthology.org/fix_video/2023.arabicnlp-1.9.pdf)
- **Self-consistency.** Wang et al. 2022 introduced majority voting over sampled reasoning paths. — [arXiv 2203.11171](https://arxiv.org/abs/2203.11171) [Not fetched]

### Inferences
- [Inferred] PoLL's tasks were short-answer QA judged against a reference, which is easier than open-ended error-finding in a dialect transcript. The finding transfers best to Anees's *adjudication* step: "is this flagged item a real error? yes/no". It transfers less to the *reader* step, which is open-ended recall.
- [Inferred] The "over-reasoning" failure is directly relevant. A big reader may over-flag dialect forms as "errors" by MSA standards, or apply knowledge the teacher's standard doesn't use. Measure precision separately from recall per tier.
- [Inferred] Family diversity was part of PoLL's advantage. Three Claude tiers are one family. Mixing in Codex GPT-5.5, already in the pipeline, adds real diversity. A Haiku×3 jury does not.
- [Inferred] Following Chen et al., test k = 1, 3, 5 voting on the gold set rather than assuming more is better. The hard items (Arabizi, code-switch boundaries) are exactly where voting can lock in a shared wrong answer.

### Gaps
- No published study found that compares Claude Haiku/Sonnet/Opus tiers, with or without voting, on learner-error annotation in any Arabic variety.
- No PoLL-style study was found on low-resource or dialect judging.

---

## Q3. How many items and runs are needed to tell two models apart, and how do we avoid overfitting prompts to the test lesson?

### Takeaway
Compare models on the *same* items (paired), cluster by lesson, average several runs per item, and run a power analysis first. With one or two lessons (a few dozen gold errors), only large differences, roughly 15-20+ points of recall or precision, will be detectable. Smaller gaps need more lessons, not more runs.

### Cited Findings
Anthropic's "A statistical approach to model evaluations" (2024-11-19; paper arXiv 2411.00640 by Evan Miller) makes five recommendations — [Anthropic research post](https://www.anthropic.com/research/statistical-approach-to-model-evals); [arXiv 2411.00640](https://arxiv.org/pdf/2411.00640):
1. Report the SEM and 95% CI (mean ± 1.96·SEM), treating items as a sample from a "question universe".
2. Cluster standard errors when items share a source. On popular evals, clustered SEs were sometimes over 3x the naive ones.
3. Resample each item several times and average per item before computing statistics. Inspect's `epochs` parameter does this.
4. Use paired differences. Question-level score correlations between frontier models were about 0.3-0.7, which gives a "free" variance reduction. Report the mean difference, SE, CI and the correlation.
5. Run a power analysis to choose the number of items and resamples, and to see when an eval is too small to be worth running.

Further cited points:
- A 2025 position paper argues against CLT-based intervals with fewer than a few hundred datapoints. — [arXiv 2503.01747](https://arxiv.org/pdf/2503.01747)
- In paired and small-strata designs, clustering at the unit-of-randomization level can push false positives up to 16.5% at nominal 5%. The authors recommend clustering at the pair level. This is an econometrics result. — [de Chaisemartin & Ramirez-Cuellar](https://hal-sciencespo.archives-ouvertes.fr/hal-03873897)
- The `errorbars` PyPI package implements Miller's guidance, including pairing and power analysis. — [PyPI errorbars](https://pypi.org/project/errorbars/)

### Inferences
- [Inferred] **Test unit.** Each gold-standard learner error, with its line ID, is one binary item per model: found or missed. Each model-flagged item is one binary item: true or false error, judged against the gold set. McNemar's exact test on discordant pairs (model A right/B wrong vs the reverse) is the standard paired test for one shared item set. Because items cluster within lessons, use a **cluster bootstrap over lessons** (resample lessons, then items) for CIs on recall, precision and F1 differences. A small-n alternative to the CLT is the exact binomial on discordant pairs.
- [Inferred] **Rough power.** McNemar power depends only on discordant pairs. If two tiers disagree on about 20% of 60 gold items (12 discordant), a 9-3 split gives exact two-sided p ≈ 0.15, which is not significant. Reaching p < 0.05 needs about 10-2 or more lopsided. With n = 60, only about 15+ point differences show up reliably. Distinguishing 5-point gaps needs several hundred gold items, i.e. many lessons.
- [Inferred] **Runs vs items.** Sampling cannot be fixed (no temperature control), so run each model 3-5 times per transcript. Score each item as the fraction of runs that found it, or majority-of-runs. That shrinks within-item noise, but run count cannot replace lesson count when the question is generalization.
- [Inferred] **Avoid prompt overfitting.**
  - Freeze prompts before scoring.
  - Split gold lessons into dev (prompt tuning allowed) and held-out test (score only, never read model outputs while editing prompts).
  - Rotate in new lessons over time.
  - Do not tune per tier on the test lesson. If tiers get their own prompts, tune each on dev only.
  - Use the same prompt across tiers as the primary comparison, with tier-tuned prompts as a secondary arm.
  - Have Medi or Amal label gold blind to which model proposed each error. Otherwise the gold drifts toward one model's outputs.

### Gaps
- No source gives a validated minimum gold-set size for learner-error annotation. The numbers above are standard power arithmetic, not published guidance.

---

## Q4. What do Arabic dialect LLM benchmarks show about tier gaps?

### Takeaway
Dialect benchmarks consistently find dialects harder than MSA. Most test open models of 1-13B parameters, or older closed flagships, so they show that size and Arabic-specific training both matter. None isolates the Claude 5.x tier gap. Nothing found covers learner (non-native) Levantine or Arabizi error detection.

### Cited Findings
- **AraDiCE** (arXiv 2409.11404; COLING 2025): seven synthetic dialect datasets plus MSA, with about 45K human post-edited samples. It adds a cultural benchmark covering the Gulf, Egypt and the Levant. Arabic-specific models (Jais, AceGPT) beat multilingual models on dialect tasks. Dialect ID, generation and translation "remain significant challenges." — [arXiv](https://arxiv.org/abs/2409.11404); [ACL Anthology](https://aclanthology.org/2025.coling-main.283/)
- **DialectalArabicMMLU** (arXiv 2510.27543; LREC 2026): 3K MCQ pairs manually adapted into five dialects, including Syrian, the closest to Levantine, plus Egyptian, Emirati, Saudi and Moroccan. It evaluated 19 open models of 1B-13B and found "substantial performance variation across dialects." No closed frontier models were tested. — [arXiv](https://arxiv.org/html/2510.27543v1); [LREC 2026](https://preview.aclanthology.org/ingest-lrec/2026.lrec-main.251/)
- **BALSAM** (July 2025): see Q1 for scores. Size is "not a sufficient predictor," and an Arabic-tuned 24B Mistral beat the 123B Mistral large. — [BALSAM](https://arxiv.org/html/2507.22603v1)
- **Survey** of Arabic LLM benchmarks (arXiv 2510.13430, Oct 2025) catalogs AraDiCE and others, and lists dialect and culture coverage as an open gap. — [Survey](https://arxiv.org/html/2510.13430v1); [TII benchmark list](https://github.com/tiiuae/Arabic-LLM-Benchmarks)
- **HELM Arabic** puts the frontier models at 0.81-0.84 with a domain-specific model at 0.919. See Q1. — [HELM Arabic](https://crfm.stanford.edu/helm/arabic/latest/)

### Inferences
- [Inferred] Benchmarks measure *comprehension of native dialect*. Anees needs *detection of non-native errors inside dialect*, where a "wrong" form may be valid MSA, valid in another dialect, or Farsi interference. No benchmark tests this. Expect the tier gap to show mostly in precision: whether the model knows a Levantine form is correct rather than an error.
- [Inferred] Arabizi and code-switching are absent from these benchmarks. Include them as a stratum in the gold set and report per-stratum results.

### Gaps
- No public numbers for Palm or ArabicMMLU on current Claude tiers were retrieved in this session.
- No per-dialect Levantine scores were extracted from DialectalArabicMMLU's tables.

---

## Q5. Which techniques change the size/accuracy/cost tradeoff?

### Takeaway
The levers are effort level, self-consistency and voting, mixed-family juries, structured output and caching. Effort is the largest single lever inside one tier: one secondary report shows Haiku 5.5's GDPval-AA moving from 1277 at medium to 1620 at max. Under `claude -p` on a subscription, the cost that matters is usage-limit consumption and wall time, not dollars.

### Cited Findings
- Effort levels are Low, Med, High, Xhigh and Max, and default effort varies by tier (Q1). Anthropic's own Opus 5.5 results use max effort. — [Opus 5.5 announcement](https://www.anthropic.com/claude-opus-5-5); [Models overview](https://platform.claude.com/docs/en/models/overview)
- Effort alone moves Haiku 5.5's GDPval-AA from 1277 (medium) to 1620 (max), per a secondary report. — [apidog](https://apidog.com/blog/claude-haiku-5-5-benchmarks/)
- Prompt caching: cache reads cost 10% of base input in general, 5% on Opus and Sonnet 5.5 and 2.5% on Fable 5.1. Minimum cacheable length is 512 tokens. Batch API is 50% off. — [Models overview](https://platform.claude.com/docs/en/models/overview); [Haiku 5.5 page](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
- Jury of small mixed-family models: about 1/7 the cost of one big judge and higher kappa on QA judging (Q2). — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)
- Voting has an optimal number of calls, after which accuracy can fall (Q2). — [Chen et al. 2024](https://arxiv.org/html/2403.02419v2)
- Judge prompt wording moved GPT-4's kappa from 0.518 to 0.725 (Q2), so prompt variance can exceed tier variance. — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)

### Inferences
- [Inferred] Test a grid of tier × effort (e.g. Haiku-max vs Sonnet-medium vs Opus-medium vs Fable-high) rather than tiers at their defaults. A cheaper tier at higher effort may match a pricier tier at lower effort.
- [Inferred] Use structured output (a JSON list of {line_id, span, error_type, correction, confidence}) to make scoring automatic and runs comparable. Schema failures count as errors per tier, and small tiers tend to break schemas more (unverified for 5.5).
- [Inferred] **Accounting under `claude -p`.** Record per call: model, effort, wall-clock time, input/output tokens and cost-equivalent. The CLI's JSON output mode reports usage and duration (from memory of the Claude Code CLI; verify locally). Convert tokens to list-price dollars as a normalized "API-equivalent cost" even though the subscription does not bill per token, because it tracks usage-limit consumption. Report accuracy per API-equivalent dollar and per minute.
- [Inferred] Caching helps when the same transcript prefix and system prompt go to several readers or repeated runs. Put the transcript and instructions first and the variable part last.

### Gaps
- No published measurement of effort-level effects on multilingual or annotation tasks for the 5.5 tiers.
- Whether `claude -p` exposes an effort flag per call, and how subscription limits weight each tier, was not verified from docs here.

---

## Q6. What are the known failure modes of LLM-as-judge, and their mitigations?

### Takeaway
The documented biases are position, verbosity/length, self-preference (and family preference), prompt sensitivity, over-reasoning, and sycophancy. Mitigations: blind and shuffle the candidates, use cross-family judges, verify against references, swap order, and check judge outputs against gold.

### Cited Findings
- **Position and verbosity bias.** Zheng et al. (MT-Bench, 2023) identified position bias and verbosity bias. Their mitigation is to judge each pair in both orders and count a win only if it holds in both. — [arXiv 2306.05685](https://arxiv.org/abs/2306.05685); summarized in [Self-Preference Bias paper, arXiv 2410.21819](https://arxiv.org/pdf/2410.21819)
- **Self-preference.** Studied directly in arXiv 2410.21819, with prior work by Panickssery et al. 2024 ([arXiv 2404.13076](https://arxiv.org/abs/2404.13076) [Not fetched]). A 2026 preprint finds that labeling an output as "self" or "other" induces bias in both directions. One reported mechanism is that judges rate lower-perplexity (more familiar) text higher (secondhand, unverified). — [arXiv 2410.21819](https://arxiv.org/pdf/2410.21819); [arXiv 2608.18091](https://arxiv.org/pdf/2608.18091)
- **Survey.** "LLMs-as-Judges" defines verbosity bias as favoring longer responses regardless of content. — [arXiv 2412.05579](https://arxiv.org/pdf/2412.05579)
- **Intra-family bias.** GPT-4 ranked its own family's variant above its true position. Mixed-family panels reduce this. — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)
- **Over-reasoning.** A strong judge injects outside knowledge instead of applying the reference. — [Verga et al. 2024](https://arxiv.org/html/2404.18796v2)
- **Over-correction in GEC.** Human evaluation of GPT-4 found fewer under-corrections but more over-corrections than traditional systems (Chinese learner GEC literature review). — [PMC11524451](https://pmc.ncbi.nlm.nih.gov/articles/PMC11524451/)
- **Sycophancy.** Models shift answers toward a user's stated view. — [Sharma et al. 2023, arXiv 2310.13548](https://arxiv.org/abs/2310.13548) [Not fetched]

### Inferences
- [Inferred] Map each failure mode onto Anees:
  - **Adjudicator position bias.** Present reader A's and reader B's claims in randomized order, run twice with the order swapped, and label them anonymously (not "Opus said...").
  - **Self-preference.** A Claude adjudicator judging Claude readers, or the same tier judging itself, is at risk. Codex GPT-5.5 as re-judge is a sound cross-family check. Measure each judge's agreement with Medi/Amal gold, not with the other models.
  - **Hallucinated errors / over-correction.** The main precision risk. Require each flagged error to quote the exact transcript span and line ID, and verify mechanically that the span exists. Unverifiable flags are counted as false positives.
  - **Sycophancy.** If the adjudicator sees "Reader A flagged this as an error", it may agree. Phrase it neutrally: "Is X at line N an error for a Levantine speaker? Yes/No/Unsure." Track how often the judge simply sides with whichever reader flagged.
  - **Verbosity.** Readers with longer error lists may look better to a judge. Score readers against gold, not by judge preference.
  - **Haiku translation leakage.** If Haiku's English translations feed the readers, translation errors propagate. Test readers with and without translations as a separate factor.

### Gaps
- No study found on LLM-judge biases specifically in Arabic, dialect or learner-error settings.

---

## Implied test design (synthesis, [Inferred])
1. **Gold set.**
   - Medi/Amal label 3+ lessons blind to model outputs: each learner error with line, span, type and correction, plus the "not an error" cases where dialect forms look wrong.
   - Stratify by vocab vs grammar, and by Arabic script vs Arabizi vs code-switch.
   - Hold out at least one lesson that is never used for prompt work.
2. **Arms.**
   - Fable 5.1, Opus 5.5, Sonnet 5.5 and Haiku 5.5 as readers, with identical frozen prompts and pinned effort. First pass at documented defaults, plus a tier × effort sub-grid.
   - Add a Haiku×3 majority arm, and a mixed-family arm (Claude + GPT-5.5) as a jury check.
3. **Runs.** 3-5 runs per model per lesson, since temperature cannot be set. Report the mean and the run-to-run spread.
4. **Metrics.**
   - Recall, precision and F1 against gold.
   - Hallucinated-span rate.
   - Schema-failure rate.
   - For the adjudicator: agreement with gold (Cohen's kappa) and rate of siding with the flagging reader.
5. **Statistics.**
   - Paired comparisons on the same items: McNemar exact for per-item found/missed.
   - Cluster bootstrap over lessons for CIs on differences.
   - Report the inter-model correlation.
   - Pre-compute power, and do not declare a winner when CIs overlap. With one lesson, treat the result as exploratory.
6. **Cost and latency.** Log tokens, wall time and API-equivalent dollars per arm. Report accuracy per API-equivalent dollar.
7. **Adjudication hygiene.** Anonymous, order-swapped claims; neutral questions; span verification; cross-family re-judge (Codex) kept.
