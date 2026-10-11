# Evaluation design for the Anees lesson pipeline (small-data test program)

Scope: how to build answer keys cheaply, which statistics work with one to a few lessons, how to avoid tuning to one lesson, which metrics to track, how to gate changes in CI, and how to watch for a stalled pipeline. Anees numbers used throughout: ~440 learner Arabic words and ~30 grammar slips per lesson; one fully reviewed lesson (2026-10-08); two partly reviewed ones; the tutor has under 10 minutes per lesson on the portal.

Note on numbers: figures marked "(own calc)" are arithmetic I ran myself with the standard formulas cited (Wilson interval, exact sign test, the paired MDE formula from Miller 2024). They are not quoted from a source.

## 1. Building gold sets cheaply (size, stratified sampling, active selection, tutor as second annotator)

### Takeaway
One reviewed lesson is enough for word-level tracking claims only when the change is large (about 4 points or more). It is not enough for slip-detection claims. Plan for 3 fully reviewed lessons plus small tutor-checked samples from each new lesson, chosen by the pipeline's own uncertainty but scored with a correction for that choice. Keep reliability claims tentative until two annotators agree at Krippendorff's alpha of 0.667 or higher, and treat 0.800 as the bar for a "trusted" key.

### Cited Findings
- Miller's "Adding Error Bars to Evals" treats eval items as a sample from an unseen super-population. It gives the sample-size formula n = (z_a/2 + z_b)^2 * (omega^2 + sigma_A^2/K_A + sigma_B^2/K_B) / delta^2, where omega^2 is the variance of the paired score difference. Example: detecting a 3-point difference at 80% power with omega^2 = 1/9 needs about 969 items, which is why the paper suggests at least ~1,000 questions for a new eval. — [Miller 2024, arXiv 2411.00640](https://arxiv.org/html/2411.00640v1)
- The same paper shows that when items come in clusters (e.g. several questions about one passage), the naive SE can understate uncertainty by up to ~3x (DROP: clustered SE 1.34 vs naive 0.44). It gives a clustered-SE formula and says to report the number of clusters. — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- Card et al. found that small test sets make most state-of-the-art comparisons underpowered. The smallest GLUE set, WNLI (n=147), has an estimated minimum detectable effect (MDE) of +5.26 points, against a typical claimed gain of +1.72. MRPC (n=1,725) has an MDE of +1.62. — [Card et al. 2020, EMNLP](https://aclanthology.org/2020.emnlp-main.745.pdf)
- Card et al. say power for paired classifier comparisons depends on n, the expected accuracy difference, and Pa, the share of items where both systems get the same outcome. They suggest estimating Pa from dev results, from a regression on past comparisons, or from middle-of-the-road assumptions. — [Card et al. 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)
- Active testing (Kossen, Farquhar, Gal, Rainforth, ICML 2021) chooses which test points get labeled, then removes the bias that choice creates while also lowering estimator variance. On CIFAR it estimates test loss more precisely than uniform sampling with the same label budget. — [Kossen et al. 2021, PMLR 139](https://proceedings.mlr.press/v139/kossen21a.html)
- Prediction-powered inference (PPI/PPI++) combines a small human-labeled set with a large set of model predictions, giving valid confidence intervals that correct for prediction error. PPI++ weights the predictions so its intervals adapt to prediction quality, and they are guaranteed to be no worse than labeled-only intervals, but only asymptotically. — [Angelopoulos, Duchi, Zrnic, PPI++](https://arxiv.org/pdf/2311.01453)
- A follow-up notes that this guarantee holds only as labeled n grows, which is exactly the regime that small-label users are not in. It derives exact finite-sample MSE for PPI++. — [arXiv 2505.20178](https://arxiv.org/pdf/2505.20178v1)
- A 2026 PPI tutorial warns that reusing training data for inference gives anti-conservative intervals. — [arXiv 2601.20819](https://arxiv.org/html/2601.20819v1)
- Krippendorff's alpha guidance: rely on data with alpha >= 0.800, draw only tentative conclusions when 0.667 <= alpha < 0.800, and discard data below 0.667 when the risks of a wrong conclusion are unknown. The minimum should rise with the stakes. — [Wikipedia summary of Krippendorff](https://en.wikipedia.org/wiki/Krippendorff%27s_alpha)
- Software-engineering methodologists call 0.667 a common rule of thumb for the minimum, and doubt that Landis and Koch style kappa bands are valid as fine-grained labels. — [arXiv 2008.00977](https://arxiv.org/pdf/2008.00977)
- Transcribers may follow the speech rather than the spelling guidelines, which puts errors into reference transcripts. — [Cardinal et al., Interspeech 2014](https://groups.csail.mit.edu/sls/publications/2014/cardinal-interspeech14.pdf)

### Inferences
- Words are clustered within lessons (same audio quality, topic, and tutor speed), so 440 words from one lesson are worth fewer than 440 independent items. Compute SEs clustered by lesson, or at least by 5-minute segment, and say "n words / k lessons" on every report.
- Precision on a single lesson (own calc, Wilson 95% interval): word-tracking accuracy of 85% on 440 words gives about 81.4–88.0%. With 3 lessons (1,320 words) it narrows to about 83.0–86.8%, before any clustering adjustment. Slip recall of 70% on 30 slips gives about 52–83%, which is far too wide to steer by. Even 150 slips (about 5 lessons) gives about 62–77%.
- Target gold set: 3 fully reviewed lessons (2026-10-08 plus two more chosen to differ, e.g. a noisy-audio day and a fast-speech day) for dev and held-out use, plus a running "spot gold" from every new lesson. Card et al.'s MDE logic says to decide the gold size from the smallest change you want to detect, not the reverse.
- Stratify the spot-gold moments on each lesson. Make sure every stratum gets some of the tutor's minutes, not just the most frequent ones. Strata:
  - (a) the pipeline flagged a slip
  - (b) the pipeline credited a word as correct
  - (c) the engines disagreed (fewer than 3 of 3 runs agree)
  - (d) low ASR confidence or an Arabic/English code-switch boundary
  - (e) a random control sample
- How to use the tutor's 10 minutes: at ~20–30 seconds per yes/no moment, that is roughly 20–30 moments per lesson. Put about 60% on uncertainty strata (c, d), about 25% on flagged slips (a), and about 15% on random items (e, needed for unbiased estimates). Weight results by inverse sampling probability, or use PPI-style correction, so the uncertainty-heavy sample does not inflate error rates. Do not report raw percentages from uncertainty-chosen items as pipeline accuracy.
- Second annotator: have the tutor relabel about 30–50 moments that the learner already labeled on 2026-10-08, and compute Krippendorff's alpha (nominal) per error type. Use alpha rather than kappa because it handles missing labels and more than two coders. If alpha is below 0.667 for a type (likely for "fake slip" vs dialect variant), fix the labeling guideline before using that type as a pass bar.
- The learner (Medi) is both user and annotator, so his answer key can carry his blind spots, e.g. not noticing slips he doesn't know are slips. The tutor's labels are the check on this.

### Gaps
- I found no published sample-size rule for how many items a Krippendorff's alpha estimate needs. A bootstrap CI on alpha from the first 30–50 double-coded items is the practical check.
- I did not verify tutor seconds-per-moment. The 20–30 second figure is an assumption to measure on the portal.

## 2. Statistics for small samples (paired tests, bootstrap, permutation, effect sizes, MDE, multiple comparisons)

### Takeaway
Always compare versions on the same items: paired word-by-word or moment-by-moment. Use McNemar or the exact sign test for correct/incorrect outcomes, and a paired bootstrap or approximate randomization for F1 and composite scores. Report the difference with a 95% CI rather than a bare p-value. On one lesson, only changes of roughly 3–6 points in word tracking and roughly 15–30 points in slip recall are detectable.

### Cited Findings
- Paired analysis: SE_paired = sqrt(SE_A^2 + SE_B^2 - 2*SE_A*SE_B*Corr). Any positive correlation between systems lowers variance. With correlation 0.5, variance drops by a third, which the paper calls a "free" reduction. — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- Resampling (K runs per item) cuts within-item variance to sigma^2/K. In the uniform example, K=2 cuts total variance by 1/3 and K=4 by 1/2, with a ceiling of 2/3. Compute the SE over item-level means; do not pool the K*N answers as if they were independent. With n=198, going from K=1 to K=10 lowers the MDE from 13.2% to 7.5%. — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- Miller advises not lowering sampling temperature to reduce variance, because it can shift variance into item means or add bias (summarized as "Don't touch the thermostat"). — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- Reporting: give n, the number of clusters, the SE beside each score, and for comparisons the paired difference, its SE, its CI, and the score correlation. — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- McNemar's test is the standard for paired classifier comparisons. It uses only the items where the two systems disagree: chi^2 = (p10 - p01)^2 / (p10 + p01). — [Card et al. 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)
- Typical machine-translation test sets of 2,000 sentences have only about 75% power to detect a 1 BLEU difference. — [Card et al. 2020 abstract](https://aclanthology.org/2020.emnlp-main.745/)
- Dror et al.'s test-selection decision tree:
  - If the test statistic's distribution is known, use a parametric test.
  - If not, and the data is small, use a bootstrap or randomization test.
  - For very large data, use sampling-free tests (sign test, McNemar).
  - F-score, BLEU, and similar metrics are not means, so the common practice is to treat them as non-normal.
  - Approximate randomization uses a limited number of permutations instead of all 2^n.
  - Dror et al. count three uses as inappropriate: a t-test on a non-average metric, a t-test on categorical outcomes, and a bootstrap on a small test set.
  — [Dror et al. 2018, ACL](https://aclanthology.org/P18-1128.pdf)
- Multiplicity: of 110 ACL 2017 papers that used multiple datasets, only 3 corrected for multiple comparisons, all with Bonferroni. Testing many hypotheses makes at least one false claim likely. — [Dror et al. 2018](https://aclanthology.org/P18-1128.pdf)
- Underpowered "significant" results risk Type-M (exaggerated magnitude) errors. Card et al. recommend running a power analysis before evaluating, and skipping or rethinking comparisons that are likely underpowered. — [Card et al. 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)

### Inferences
- Exact sign test / McNemar on discordant items (own calc, two-sided alpha 0.05):
  - Discordant items are the words where v1 and v2 disagree on right vs wrong.
  - With 6 discordant items, all 6 must favor v2. With 10, at least 9. With 15, at least 12. With 20, at least 15.
  - So a change that flips fewer than about 6 words can never be shown significant.
- MDE for word tracking (own calc, delta ≈ 2.8*sqrt(q/n), 80% power, q = share of words where versions disagree):
  - One lesson (n=440): about 3.0 points if q=5%, 4.2 if q=10%, 6.0 if q=20%.
  - Three lessons (n=1,320): about 1.7, 2.4, and 3.5 points.
  - These are optimistic because of clustering.
- MDE for slip detection (own calc): with 30 slips and 20–40% discordance, about 23–32 points. With 90 slips (3 lessons), about 13–19 points. Implication: on today's single key, only report slip precision and recall descriptively, with CIs, until 3+ lessons are reviewed.
- The bootstrap needs care: Dror et al. flag bootstrapping small test sets. For slips (n≈30), prefer exact McNemar or approximate randomization (10,000 shuffles of the paired labels) over a bootstrap CI. For words (n≈440+), a paired bootstrap that resamples whole 2–5 minute segments (a block bootstrap, to respect clustering) is reasonable.
- Effect sizes to report: the absolute difference in points with a 95% CI, the discordant counts (b, c), and errors per 100 Arabic words with a CI. An odds ratio b/c is a compact McNemar effect size.
- Multiple variants: testing 10 variants at alpha 0.05 gives a 40% chance of at least one false "win" (own calc: 1 - 0.95^10). For 20 variants it is 64%. Options:
  - Holm–Bonferroni across the variants in one round.
  - Treat a dev-set win only as a candidate, then confirm it once on held-out lessons. This is a two-stage design and the cheapest fix.
- Engine runs: the current 3-runs, 2-of-3-agree rule is a reasonable reducer. Per Miller, compute SEs over moment-level means (the K=3 average), not over all 3 x N outputs. Going from 3 to 5 runs buys little once item variance dominates, since the variance-reduction ceiling is 2/3.

### Gaps
- I did not retrieve sequential-testing sources (e.g. SPRT or always-valid p-values). The practical guidance below on adding lessons one at a time is my own inference: an alpha-spending rule like O'Brien–Fleming, or simply fixing the number of lessons before looking.

## 3. Avoiding overfitting to one lesson (held-out lessons, frozen keys, pre-registered pass bars, time splits)

### Takeaway
Treat 2026-10-08 as dev, which by now it effectively is, since every fix has been tuned against it. Keep at least one fully reviewed lesson that nobody looks at error-by-error, as test. Freeze keys by hash, write pass bars down before running, and split by date so future lessons are always the test.

### Cited Findings
- Card et al.: when a test set can't detect typical improvements, expand it or retire it. Repeated small wins on a small set should be met with skepticism about generalizing. — [Card et al. 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)
- Miller: the population of interest is the unseen super-population of items, not the specific test items. — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- PPI tutorial: reusing training data for inference gives anti-conservative intervals. Reusing the dev lesson as test is the same problem. — [arXiv 2601.20819](https://arxiv.org/html/2601.20819v1)
- promptfoo practitioner guidance recommends pinning a specific model snapshot in CI, because unpinned providers drift when vendors update models. — [tessl promptfoo registry entry](https://tessl.io/registry/testland/promptfoo-evaluation/files)

### Inferences
- Split by time:
  - DEV: 2026-10-08, plus the partial keys from the two older lessons.
  - TEST: the next fully reviewed lesson. Freeze its hash on arrival, run it only at milestone gates, and look at aggregate numbers only, not per-error dumps.
  - ROLLING: each new lesson's spot gold moves into DEV after it has served once as test.
- Pre-register each change in the backlog entry before running: the metric, the direction, the minimum gain, and the max allowed regression on other metrics. Example: "word tracking +3 pts on DEV and not worse than -1 pt on TEST; fake slips per 100 words not up". A change that was tuned by reading 10-08 errors counts as passing only on TEST.
- Freeze keys: keep the existing hash approach. Any edit to a key is a new versioned key (key v2) with a changelog. Re-score old pipeline versions on the new key, so comparisons always use the same key.
- Rule-registry risk: correction rules derived from 10-08 errors should be checked for firing rate on other lessons. A rule that only ever fires on 10-08 is overfit.

### Gaps
- No source directly addresses single-user, single-tutor longitudinal eval. The time-split design is an inference from general held-out practice.

## 4. Metrics design (slip P/R/F, word tracking, cost, human minutes, composite, Arabic normalization)

### Takeaway
Keep the two existing reports and add:
- slip precision, recall, and F-beta, with beta chosen deliberately
- WER/CER on a normalized and a raw track
- dollars per lesson
- tutor and learner minutes per lesson

Make the composite a gate (all bars must pass) rather than a weighted sum, so one metric can't hide a regression in another.

### Cited Findings
- Normalization is not standardized for Arabic ASR. Production pipelines usually unify hamza variants, collapse ta marbuta, strip diacritics, and convert digits. One 2026 benchmark deliberately skipped these to evaluate raw output, at the cost of counting spelling variants as errors. — [arXiv 2605.19069](https://arxiv.org/pdf/2605.19069)
- Reporting WER both diacritized and undiacritized separates diacritic errors from base-letter errors. In one model, WER fell from 40.82 to 19.94 when diacritics were removed. Apply Unicode NFC so a hamza-on-alef written as one or two code points compares equal. — [arXiv 2607.18946](https://arxiv.org/pdf/2607.18946)
- The Lucene ArabicNormalizer maps:
  - hamza-carrier alefs to bare alef
  - teh marbuta to heh
  - alef maksura to yeh
  It also removes harakat and tatweel. These rules are search-oriented and not automatically right for scoring. — [Lucene ArabicNormalizer](https://lucene.apache.org/core/5_1_0/analyzers-common/org/apache/lucene/analysis/ar/ArabicNormalizer.html)
- QCRI's normalizer exists because Arabic spelling of diacritics, alef, and ta marbuta varies by author and can strongly affect scores. It is applied to both references and system output. — [QCRI Arabic normalizer](https://alt.qcri.org/tools/arabic-normalizer)
- Dror et al. note that F-score is not a mean, so use resampling tests rather than t-tests. — [Dror et al. 2018](https://aclanthology.org/P18-1128.pdf)
- promptfoo practitioner guidance: model-graded (LLM-judge) assertions roughly double per-test cost. Judge metrics have directions: hallucination needs a ceiling, relevance needs a floor. — [tessl promptfoo entry](https://tessl.io/registry/testland/promptfoo-evaluation/files); [Comet/Heartbeat](https://heartbeat.comet.ml/how-do-you-set-up-a-regression-gate-for-prompt-changes-in-ci-1612e304f18d)

### Inferences
- Slip detection:
  - Precision = true slips / flagged slips (fake slips lower it).
  - Recall = true slips caught / all slips in the key (missed slips lower it).
  - Keep "per 100 Arabic words" rates as the main reading, since they normalize for lesson length. Also report P/R/F so changes can be compared with the literature.
  - Choose beta from product cost. If a fake slip that costs the learner trust is worse than a missed slip, use F0.5. If coverage matters more, use F2. Write the choice down once.
- Word tracking: keep "% Arabic words tracked right". Add normalized WER/CER on learner Arabic as a separate ASR-layer metric, so ASR changes and grading changes can be told apart.
- Normalization for comparison: write one normalizer function, used for both key and output, and versioned with the key:
  - NFC
  - strip tashkeel and tatweel
  - unify alef forms
  - alef maksura to yeh
  - ta marbuta to heh, only on the normalized track
  - Eastern/Western digits
  Score twice: raw (strict) and normalized (lenient). A change that helps lenient but hurts strict is probably a spelling-only effect. Dialect variants (e.g. Levantine vs MSA forms) need an explicit equivalence list built with the tutor, not blanket normalization.
- Cost per lesson: log tokens and dollars per stage per run. Human minutes per lesson: portal timestamps for the tutor, review-time logging for the learner.
- Composite: a lexicographic gate is easier to reason about than a weighted sum. The bars are illustrative, set from v1 baselines:
  - (1) no metric regresses beyond its pre-registered tolerance
  - (2) primary metric improves by at least the MDE
  - (3) cost per lesson does not exceed budget
  - (4) human minutes per lesson do not rise

### Gaps
- I found no published standard Arabic WER normalization for learner speech. Rules must be agreed locally, with the tutor.

## 5. MLOps practices (harnesses, golden datasets, CI regression gates, drift, stall alerting)

### Takeaway
A small local harness is enough: frozen keys + scorer + paired-diff report + CI gate. Inspect- or promptfoo-style tooling helps with repeats ("epochs"), caching, and PR diff comments. Add a freshness SLO ("today's lesson is processed within X hours of upload") with a heartbeat alert, since a stalled pipeline is a bigger day-to-day risk than a 2-point accuracy change.

### Cited Findings
- Inspect (UK AISI) lets eval() take `epochs` as an integer or an Epochs object with reducer functions that combine per-sample scores, defaulting to "mean". Scorers ship built-in accuracy and stderr metrics that can be overridden. — [Inspect reference](https://inspect.aisi.org.uk/reference/inspect_ai.html); [Inspect metrics](https://inspect.aisi.org.uk/metrics.html)
- promptfoo:
  - Assertions take thresholds (e.g. a model-graded check at 0.8).
  - The GitHub Action `promptfoo/promptfoo-action` can post a PR comment with a regression diff against the base branch, and caches responses for unchanged tests.
  - Pinning model snapshots is recommended.
  — [tessl promptfoo entry](https://tessl.io/registry/testland/promptfoo-evaluation/files); [Medium guide](https://medium.com/@alexrodriguesj/testing-llm-prompts-like-code-regression-evals-in-ci-cd-with-promptfoo-5242b4dcb9be) (secondary sources; I did not check the official docs)
- Google Cloud SLO guidance: for data-processing services, correctness and freshness are better SLIs than availability and latency. The SRE Workbook's chapter 13 covers data pipelines. — [Google Cloud SLO docs](https://docs.cloud.google.com/stackdriver/docs/solutions/slo-monitoring/sli-metrics/data-proc-metrics); [SRE workbook chapter](https://sre.google/resources/book-update/data-processing-pipelines/)
- A Google Cloud SRE blog says to set SLOs for pipeline health, especially freshness. Acceptable staleness ranges from seconds (forecasting) to days (spell-checkers). — [Google Cloud blog](https://cloud.google.com/blog/products/devops-sre/applying-sre-principles-to-your-mlops-pipelines)
- A common (non-Google) freshness SLI is count(data_age < threshold) / total. For batch jobs, it can be measured as completion time vs scheduled time. — [Conduktor glossary](https://conduktor.io/glossary/data-freshness-monitoring-sla-management)

### Inferences
- Harness for Anees: extend the grade book into a single CLI (`score --pipeline vN --key K@hash`) that writes:
  - per-item results as JSON
  - report 1 and report 2 with CIs
  - a paired diff vs the last accepted version (McNemar b/c, diff and CI)
  Run it in the existing publish guard. Fail the push if a pre-registered bar fails. Allow a manual override that leaves a logged reason, as the current "manual:" commits already do.
- Cost control in CI: cache engine outputs keyed by (audio hash, engine, model snapshot, prompt hash). Only re-run the stages a change touches, and re-score the rest from cache.
- Drift without gold: track label-free signals per lesson and alert on a jump beyond about 2 SD of the trailing 10 lessons. Signals:
  - slips per 100 words
  - share of words low-confidence
  - engine agreement rate (2-of-3 and 3-of-3)
  - Arabic/English word ratio
  - cost per lesson
  A jump triggers a larger tutor spot-check that day.
- Freshness SLO, illustrative:
  - 95% of lessons have scores published within 6 hours of upload.
  - Each stage writes a heartbeat timestamp.
  - Alert when no heartbeat arrives for over 2x the normal stage duration, or when a lesson upload is older than the SLO without output.
  - Also alert on silent nulls, e.g. a pipeline "succeeds" with 0 slips or 0 Arabic words.

### Gaps
- I did not confirm the exact Inspect `pass_at` reducer name or the promptfoo action inputs from official docs. LangSmith and OpenAI Evals were not researched.

## 6. Ablation and factorial designs with a tiny budget; sequential testing

### Takeaway
Use paired, one-factor-at-a-time ablations off the current best version, or a 2^k fractional factorial when factors (ordering x model x prompt) might interact. Screen on DEV, confirm one winner on TEST. Fix the number of lessons before looking, or use an explicit stopping rule.

### Cited Findings
- More runs per item (K) reduce within-item variance with diminishing returns: a ceiling of a 2/3 reduction, and the MDE at n=198 only falls from 13.2% to 7.5% between K=1 and K=10. — [Miller 2024](https://arxiv.org/html/2411.00640v1)
- Multiple comparisons sharply raise the chance of a false claim. Bonferroni is the correction usually used in NLP. — [Dror et al. 2018](https://aclanthology.org/P18-1128.pdf)
- Run a power analysis before the evaluation; underpowered comparisons don't give convincing evidence. — [Card et al. 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)

### Inferences
- A 2x2x2 design (ordering A/B x model A/B x prompt A/B) has 8 cells. A 2^(3-1) half fraction has 4 cells and still estimates the main effects, with each main effect confounded with one two-way interaction. Every cell runs on the same frozen lesson(s), so analysis is paired. With 3 runs per cell, the 4-cell version costs 12 pipeline runs per lesson vs 24 for the full factorial.
- Spend runs on items, not repeats: 3 runs x 3 lessons beats 9 runs x 1 lesson, because between-item and between-lesson variance dominate.
- Sequential: when adding gold lessons one at a time, decide in advance either:
  - "evaluate after lessons 3 and 5 only, with alpha 0.025 at each look" (a crude Bonferroni split), or
  - stop early only for harm, e.g. an exact sign test showing v2 worse at p<0.01.
  Don't peek after every lesson and stop at the first p<0.05.
- Implications for the Anees test plan, in priority order:
  1. Get 2 more fully reviewed lessons. Use one as TEST and keep it unexamined.
  2. Collect 20–30 tutor-labeled moments per lesson: stratified, uncertainty-weighted, with a 15% random share.
  3. Double-code 30–50 moments on 10-08 and compute alpha per error type.
  4. Add paired McNemar plus CIs to the grade book.
  5. Pre-register pass bars per change.
  6. Gate in the publish guard.
  7. Add a freshness SLO and heartbeat alert.
  8. Treat any claim about slip-detection differences under ~20 points as unproven until 3+ lessons are keyed.

### Gaps
- No sources were fetched on fractional factorial designs for LLM pipelines specifically, or on SPRT/always-valid inference. The design advice above is standard design-of-experiments reasoning, not cited.
