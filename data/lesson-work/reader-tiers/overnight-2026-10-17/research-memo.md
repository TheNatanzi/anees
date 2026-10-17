# Slip reader: methods memo for raising F0.5 toward 90

Date: 2026-10-17. Scope: research memo. No code or prompts were changed.

Setup: LLM "slip readers" take a brief (~15k chars), the tutor's word list (~126k), grammar rules, and a ~50k-char code-switched Levantine/English/Arabizi STT transcript. They return slip rows. These are scored with F0.5 against a human key of 102 slips across 3 lessons (10-08: 34, 10-09: 43, 10-10: 25).

Starting point, from `attempts.jsonl` in this folder (held-out, leave-one-lesson-out):

| method | P | R | F0.5 | per-lesson F0.5 (08 / 09 / 10) |
|---|---|---|---|---|
| single opus / sonnet / gpt-5.5 | ~72 | ~73-75 | 72.5-72.8 | varies widely |
| single gemini-3.7-flash | 79.5 | 56.9 | 73.6 | 83 / 76 / 57 |
| vote opus+sonnet | 82.1 | 67.6 | 78.8 | 88 / 71 / 78 |
| vote 8-model k-of-n | 84.5 | 58.8 | 77.7 | 90 / 78 / 62 |
| stack logistic, 8 models | 83.8 | 65.7 | **79.4** | 88 / 76 / 72 |
| "search subset x k" (selection inside folds) | 73.4 | 56.9 | 69.4 | - |

The last row matters. When the subset choice is made honestly inside the folds, it drops to 69. The good subset numbers were partly picked on the test folds (see section 7).

---

## 0. The arithmetic first: 90 is roughly the measurement ceiling

- F0.5 = 1.25·P·R / (0.25·P + R). F0.5 = 90 needs about **P 93 / R 80** or **P 95 / R 74**. Today's best is P 84 / R 66.
- If the key is about 90% reliable, a *perfect* reader also scores about 90. Suppose 10% of key rows are wrong or debatable and the key misses about 10% of real slips. A perfect reader then matches 0.9K of K key rows (R = 0.9) and has P ≈ 0.9, so measured F0.5 ≈ 90. **So "90 against this key" means matching the human annotator's own noise.** Bryant & Ng (2015) found that even humans scored against other humans cannot pass ~75 F0.5 on essay GEC ([ACL P15-1068](https://aclanthology.org/P15-1068/)). A 2026 study found that 73.8% of GPT-4o corrections that differed from gold were judged equally valid or better ([arXiv 2605.07635](https://arxiv.org/abs/2605.07635)).
- The consensus-FP list (`consensus-fp.txt`) shows 14 rows that 6 or more of 8 models flagged but the key lacks. Their signals are mostly `asked`, `explicit-no`, `recast` and `prompt-then-fix`. There are also 5 key slips that no model found. Some of these are probably reader errors. Some are probably key omissions or policy edge cases ("does a learner *asking* for a word count?"). **This has not been verified. Medi has to adjudicate it, blind.** Either answer helps. If they are key errors, the measured score rises. If they are reader errors, they are a systematic, rule-fixable class (method 2 below).

Practical target: about 85-88 held-out against the current key. Reaching 90 likely needs a key-adjudication pass as well.

---

## 1. Ensembles and aggregation

**Majority / k-of-n voting.** This is the strongest simple baseline, and it trades recall for precision. Edit-level voting is standard in GEC system combination. Tarnavskyi et al. (2022) vote on span-level edits ([arXiv 2203.13064](https://arxiv.org/abs/2203.13064)). "Pillars of GEC" (2024) found that the best threshold is about half the number of systems: 7-system majority voting reached 81.4 F0.5 on BEA-2019 test and 71.8 on CoNLL-14. An oracle over the candidates reaches 87.2, so most of the headroom is in **which candidates you keep**, not in generating more ([arXiv 2404.14914](https://arxiv.org/abs/2404.14914)). Your results look the same: voting lifts P from 72 to 84 and cuts R from 73 to 59.

**Edit-level self-consistency, one model sampled k times (Goto, Sakai & Watanabe 2026).** Sample k=8 candidates at temperature 1.0, extract edits, and keep edits that appear in at least τ of them. On BEA-2019:
- Llama-3.1-8B: 54.0 → 63.1 (P 52 → 67, R 62 → 52)
- Qwen3-8B: 56.3 → 68.7 (P 55 → 74, R 63 → 54)
- gemma-2-9b: 59.5 → 64.0
- Largest gain: +14 on CWEB-G

Gains saturate at k=4-8. τ was set per dataset on dev and was usually high (6-8 of 8) for precision-oriented sets. The method was also robust to prompt wording ([arXiv 2605.13624](https://arxiv.org/abs/2605.13624)). This is the closest published analogue to your task: it fixes LLM over-flagging in an F0.5 setting.

**PoLL, a panel of diverse judges (Verga et al. 2024).** A panel of smaller models from different families beat a single GPT-4 judge on agreement with humans (Cohen's κ). It also showed less self-family bias and cost about 7× less ([arXiv 2404.18796](https://arxiv.org/abs/2404.18796)). The same idea applies to a *verifier* panel (method 5 below).

**Dawid-Skene and learned per-model reliability.** With LLMs used as annotators, one-coin Dawid-Skene beat majority vote in a CHI 2024 pipeline: GPT-4 alone 83.6%, GPT-4 plus crowd aggregated 87.5% ([arXiv 2402.16795](https://arxiv.org/abs/2402.16795)). The catch is that Dawid-Skene assumes independent errors, and LLM errors are strongly correlated. In Kim et al. (ICML 2025), when two models are both wrong they agree on the same wrong answer about 60% of the time against a 33% chance rate. That correlation is *higher* for stronger models, even across vendors ([arXiv 2506.07962](https://arxiv.org/abs/2506.07962)). A 2026 affect-annotation study found that majority vote, Dawid-Skene and MACE gave almost identical labels, and that Dawid-Skene *overestimated* accuracy (90.7% estimated vs 71.0% real) because of shared bias ([ACL 2026 CAS](https://aclanthology.org/2026.cas-1.11/)).
- **Implication:** your logistic stack already learns per-model weights with supervision, which is better than unsupervised Dawid-Skene. Don't expect Dawid-Skene to add anything. The 8 reads are not 8 independent votes. Treat the 6+/8 FPs as *shared bias*, and fix them with rules, not more voters.

**Stacking.** A supervised meta-classifier over candidate features is the right frame, and it is already your best at 79.4. Gains will come from **richer features** (per-model sample frequency, signal type, kind, verifier verdict, model-stated confidence), not more models. With 3 folds, keep it to fewer than about 10 features with strong L2.

**Union-then-verify.** Recall is the binding constraint: R 59-66 under voting, but single models reach 73-75. The union of all readers is likely above 85 recall. A separate verification stage then decides on each candidate (sections 4 and 5).

## 2. Multi-agent debate, adversarial roles, councils

- **Debate mostly is voting.** Choi, Zhu & Li (NeurIPS 2025) split multi-agent debate into voting plus debate. Across 7 benchmarks, majority voting accounts for most of the gain. In their model, the debate process is a martingale: it doesn't raise expected correctness unless updates are biased toward correcting errors ([arXiv 2508.17536](https://arxiv.org/abs/2508.17536)).
- Smit et al. (ICML 2024) found that debate does not reliably beat self-consistency or ensembling, and that it is hyperparameter-sensitive ([PMLR v235](https://proceedings.mlr.press/v235/smit24a.html)). Huang et al. (ICLR 2024) found the same at equal sample counts ([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)).
- **Debate can hurt.** Wynn et al. (2025) found that agents often flip from right to wrong after reading peers' reasoning, and that anti-sycophancy prompting did not stop those flips ([arXiv 2509.05396](https://arxiv.org/abs/2509.05396)). Yao et al. (2025) found that sycophancy-driven "disagreement collapse" leaves debates less accurate than single agents ([arXiv 2509.23055](https://arxiv.org/abs/2509.23055)).
- **Where adversarial roles help:** Khan et al. (ICML 2024) used two debaters arguing *opposite* fixed answers to a judge who can check quotes. LLM judges reached 76% (vs 48% naive) and humans 88% (vs 60%). Verified quotes were essential. Judges also showed verbosity, position and quote-sycophancy biases, mitigated by swapping positions ([arXiv 2402.06782](https://arxiv.org/abs/2402.06782)).
- **For this task:** don't run open debate or a council over the whole lesson. If anything, use a **structured prosecutor/defender on contested candidates only** (vote split, e.g. 3-5 of 8):
  - The prosecutor must quote the transcript line and the rule or word-list entry that was violated.
  - The defender must quote evidence that it isn't a slip: the tutor accepted it, it's an STT artifact, it's a valid dialect form, or the learner self-corrected before the tutor did.
  - A judge from a third vendor rules on the quotes alone, run twice with the order swapped.
  - Expect at most +1-2. This is a variant of method 5, not a separate idea.

## 3. Self-consistency and repeated sampling

- The original self-consistency method is majority over sampled reasoning paths. Universal Self-Consistency (Chen et al. 2023) extends it to free-form output by letting the LLM pick the most consistent sample. That matches simple voting where answers can be compared, and it suits list outputs ([arXiv 2311.17311](https://arxiv.org/abs/2311.17311)).
- For extraction or edit lists, **edit-level voting** (Goto 2026 above) is the direct method:
  - **k:** 4-8 is enough; gains flatten after that.
  - **τ:** tune it, and expect a high τ for F0.5.
  - **Temperature:** around 1.0 for diversity.
- **Threshold tuning on 3 lessons:** select τ inside each training fold, then report held-out (you already do this). Prefer a **single global τ expressed as a fraction** (e.g. "≥ 60% of samples") over a per-lesson or per-model τ. Fewer degrees of freedom means less overfitting.
- **Main value:** sample frequency gives you a *per-candidate confidence* for each model. That is a much better stacking feature than the binary "model X flagged it".

## 4. Verification steps, evidence citation, and judge biases

- **Chain-of-Verification** (Dhuliawala et al., Findings ACL 2024): draft, plan verification questions, answer them *independently* of the draft, then revise. On list-style questions, precision roughly doubled (Wikidata list QA 0.17 → 0.36). MultiSpanQA F1 went 0.39 → 0.48 ([ACL Findings 2024.findings-acl.212](https://aclanthology.org/2024.findings-acl.212/)). Answering independently is the key ingredient, because it stops the verifier copying the drafter.
- **Find-then-verify for extraction.** GPT-NER added a yes/no self-verification pass per extracted entity, aimed at LLM over-prediction ([arXiv 2304.10428](https://arxiv.org/abs/2304.10428)). A follow-up ablation found that verification raised F1 mainly through precision, with slightly lower recall ([arXiv 2606.24387](https://arxiv.org/abs/2606.24387)).
- **Intrinsic self-critique is weak.** A model re-judging its own answers without new evidence often doesn't help and can hurt ([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)). Verification should therefore:
  1. use a *different* model (self-preference: [Panickssery et al. NeurIPS 2024](https://arxiv.org/abs/2404.13076))
  2. receive *external evidence*: the exact transcript window ±30 s, the relevant word-list entries and rule text, retrieved by code
  3. answer in a fixed schema, e.g. `{is_learner_utterance, is_error_per_rule_X, tutor_reaction, stt_artifact_likely, verdict, quote}`.
- **Judge biases to control** (Zheng et al. 2023, MT-Bench: [arXiv 2306.05685](https://arxiv.org/abs/2306.05685)):
  - Position bias: GPT-4 was consistent under swapped order only about 65% of the time.
  - Verbosity bias and self-enhancement bias.
  - Mitigations: swap order, use a judge from a different family, and strip which reader proposed the item.
- **Two-stage find-then-classify** also helps the scoring itself. Let the finder be recall-oriented ("list every candidate"). A classifier then assigns kind (grammar/vocab) and the keep/drop decision, with the policy rules in its prompt.

## 5. Few-shot from gold, retrieval, prompt optimization, confidence

- **Taxonomy and rules plus few-shot raise precision a lot in LLM GEC.** In "Larger Context Window, Fewer Overcorrections" (2026, BEA-2019 dev), going from vanilla zero-shot to minimal-edit few-shot plus a taxonomy, then batching, then LLM-assisted prompt optimization gave:

  | model | vanilla F0.5 | final F0.5 | P | R |
  |---|---|---|---|---|
  | Claude Sonnet 4.6 | 50.4 | 59.5 | 49.6 → 66.9 | 53.8 → 41.2 |
  | Gemini 3-Flash | 45.1 | 59.0 | - | - |
  | GPT-4.1-mini | 46.5 | 57.4 | - | - |

  The test set reached 78.3 F0.5 ([arXiv 2609.10810](https://arxiv.org/abs/2609.10810)). Two caveats:
  - The prompt optimizer used 4,384 dev sentences, about 40× your gold.
  - Out-of-domain (CoNLL) results were mixed: two of the models dropped slightly.
- **Batching candidates acts as a regularizer** against over-correction, with dev-optimal batches of about 5-15 items. Relevant for a verifier: judge 10-15 candidates per call.
- **Retrieve examples similar by error pattern.**
  - Tang et al. (NAACL 2024): syntax-similar in-context examples beat BM25 and semantic retrieval for GEC ([arXiv 2403.19283](https://arxiv.org/abs/2403.19283)).
  - Li et al. (NAACL 2025): retrieval by *LLM-generated error explanations* beat surface retrieval across 5 languages ([arXiv 2502.08507](https://arxiv.org/abs/2502.08507)).
  - For you: build a bank of keyed slips and keyed non-slips, especially the 6+/8 FPs once Medi adjudicates them. Retrieve by `signal` + `kind` + rule ID, and show 2-4 positives and 2-4 hard negatives per verification. **Leave-one-lesson-out:** never retrieve from the lesson under test.
- **DSPy, MIPRO and GEPA with about 100 labels: high risk.**
  - Practitioners recommend MIPRO for 300 or more examples. One study with few gold labels found that no DSPy optimizer consistently improved results ([arXiv 2502.11267](https://arxiv.org/abs/2502.11267)).
  - A reported GEPA run on 20 training questions raised train accuracy from 90 to 95 while test fell from 95 to 85 ([DSPy optimizers docs](https://dspy.ai/learn/optimization/optimizers); [overview](https://tianpan.co/blog/2026/04/16/automated-prompt-optimization-dspy-mipro)).
  - Use LLM-assisted rule *writing* from FP/FN error analysis, reviewed by a human, not automated search.
- **Calibrated confidence and abstention.** For RLHF models, asking for a numeric confidence in words was better calibrated than token probabilities, often halving calibration error ([Tian et al., EMNLP 2023, arXiv 2305.14975](https://arxiv.org/abs/2305.14975)). Use stated confidence plus sample frequency as stacking features. Then set the threshold to maximize F0.5. With calibrated probabilities, the F-optimal keep threshold is p ≥ F*/(1+β²) ([Lipton et al. 2014, arXiv 1402.1892](https://arxiv.org/abs/1402.1892)). For β = 0.5 and F* ≈ 0.8 that is p ≥ ~0.64, so abstain on anything below roughly 2-in-3 confidence.

## 6. Learner-error detection: spoken, transcribed, and Arabic

- **Spoken GEC is a cascade of ASR, disfluency removal and GEC.** Errors propagate between stages, and LLMs in the last stage inherit *both* ASR errors and their own over-correction tendency. That is a poor fit for learner feedback ([Qian, Ma, Bannò, Gales, Knill 2025, arXiv 2506.18532](https://arxiv.org/abs/2506.18532)). The Speak & Improve 2025 challenge (SLaTE) added spoken GEC and *feedback* tracks on 55 h of annotated L2 speech ([arXiv 2412.11985](https://arxiv.org/abs/2412.11985)).
  - **For you:** make "STT artifact vs learner slip" an explicit field the reader must decide, with cues: odd word unattested in the word list, phonetic near-miss of a correct word, tutor didn't react. Retrieve the audio-aligned snippet or the second STT track if one exists. Disfluencies and false starts that the learner fixes *themselves* should follow a written policy. This is a likely FP source.
- **Tutor reaction is your strongest signal.** Your FP list is dominated by `asked`, `recast`, `explicit-no` and `prompt-then-fix`. In classroom-discourse research, recasts are often ambiguous: the tutor may be rephrasing, not correcting. **Write explicit inclusion rules per signal type, using Medi's adjudications.** For example: does "learner asks for a word they don't know" count as a vocab slip? Does a tutor recast count if the learner's form was acceptable dialect?
- **Arabic and dialect specifics.**
  - Arabic GEC research is mostly MSA. Alhafni et al. (EMNLP 2023) show that adding explicit **error detection** features improves correction ([ACL 2023.emnlp-main.396](https://aclanthology.org/2023.emnlp-main.396/)). Text-editing taggers are state of the art on MSA ([arXiv 2503.00985](https://arxiv.org/abs/2503.00985)).
  - Dialectal Arabic has no standard spelling (CODA is the convention). LLMs remain weaker on Levantine than on MSA and English ([AraDiCE, arXiv 2409.11404](https://arxiv.org/abs/2409.11404)). Arabizi decoding is a known weak spot ([MT Summit 2025](https://aclanthology.org/2025.mtsummit-2.4/)).
  - **For you:** normalize spelling variants before matching. ة/ه, ى/ي, hamza forms and Arabizi→Arabic transliteration should never generate or block a match. Instruct readers that orthographic variation is not a slip.
  - Expect MSA leakage: a model "correcting" a valid Levantine form toward MSA. The example "أغلب إشي → أغلب الإشي" in the FP list may be this kind of judgment call. Add a "valid in Levantine?" verifier question.
- **Learner L1 = Farsi.** Typical transfer errors are a fair source of *recall* hints in the brief, as the few-shot categories to look for: gender agreement (Farsi has no grammatical gender), definiteness and the article (Farsi has none), word order of adjectives and quantifiers, and false-friend vocabulary from shared Arabic loanwords used with Farsi meanings.

## 7. Evaluation honesty with 102 gold items

- **Noise level.**
  - A recall of 0.66 on 102 items has a standard error of about √(0.66·0.34/102) ≈ 4.7 points. F0.5 bootstrap 95% CIs on this set will be roughly ±6-8.
  - Per-lesson F0.5 swings of 20-30 points (10-10 is consistently the worst at 55-72) dominate the method differences.
  - Card et al. (EMNLP 2020) show that most small-test-set comparisons in NLP are underpowered ([arXiv 2010.06595](https://arxiv.org/abs/2010.06595)).
  - **Differences under about 4 F0.5 points on this set are not distinguishable from noise.**
- **Use paired tests.** Bootstrap over *slips and predictions* by lesson block, or run McNemar on item-level hit/miss between two methods. Paired tests are far more powerful than comparing two F0.5 numbers.
- **Selection is overfitting.** Choosing "opus+sonnet" because it scored 78.8 held-out, after looking at about 10 combinations' held-out scores, is selection on test. The honest analogue is your "search subset x k" row (69.4). Fixes:
  1. **Nested LOO.** Pick the subset, τ and threshold using only the 2 training lessons, then score the third.
  2. **Pre-register** one or two final configs.
  3. **Key a 4th and 5th lesson as a locked test set** that nobody looks at until the end. That is the single most valuable step for trustworthy numbers.
- **Annotator ceiling.** Have Medi (or a second annotator) re-key one lesson blind, or adjudicate all disagreements blind. That measures human-vs-human F0.5, the realistic ceiling: Bryant & Ng found it was ≤ 75 for essays.
  - Kasner et al. (2025) find that LLM span annotators reach only moderate agreement with humans, but make errors at about the rate of skilled crowdworkers ([arXiv 2504.08697](https://arxiv.org/abs/2504.08697)).
  - Report readers as a fraction of the human ceiling, the "ratio" metric Bryant & Ng propose.
- **Matcher audit.** Check that timestamp tolerance, one-utterance-two-slips splitting, and spelling normalization treat equivalent answers as matches. Example: `MISS 1:04:23 vocab` appears twice. Granularity mismatches between key and reader are a classic hidden source of FP/FN pairs in GEC scoring ([CLEME, arXiv 2305.10819](https://arxiv.org/abs/2305.10819)). Fixing a matcher bug is "free" F0.5, but only if done blind to which side benefits.

---

## Ranked methods: most likely to move held-out F0.5 toward 90

Expected gains are rough, held-out, against today's 79.4 stack, and **not additive**. Costs use the about $0.15 per lesson-read reference from memory.

| # | method | what to do concretely | expected gain | cost | risk |
|---|---|---|---|---|---|
| 1 | **Blind key adjudication + policy rules** | Show Medi the 14 consensus-FPs, the 5 all-miss key slips, and a sample of 2-4 of 8 split items. Present them blind: no "model said" or "key said" labels, mixed with decoys. For each, record slip / not slip / policy. Turn the decisions into written inclusion rules per `signal` type (asked, recast, explicit-no, prompt-then-fix, finished-sentence). Update the key *and* the brief. | +3 to +7 measured (part is ceiling repair, part is a real precision fix) | 1-2 h of Medi; ~$0 | Confirmation bias, mitigated by blind decoys. Rules must hold up on a *new* lesson. |
| 2 | **Union-then-verify with an evidence-bound cross-vendor verifier panel** | Candidates = union of all readers, deduplicated by time ±10 s plus a normalized form. For each candidate, code retrieves a transcript window of ±30 s, the matching word-list entries and the rule text. Three verifiers from different vendors (PoLL) answer a fixed CoVe-style checklist: learner speech? error per rule X? valid Levantine? STT artifact? tutor reaction? Each gives verdict, confidence and quote, in batches of 10-15 candidates, with the reader identity hidden. Feed the votes to the stack. | +4 to +8 (raises R from ~66 toward 75-80 at P ≥ 85) | ~150-250 candidates per lesson × 3 verifiers, batched: about $0.5-1.5 per lesson | Verifiers share bias (Kim 2025). The candidate list is long. Rules have to carry the precision. |
| 3 | **Edit-level self-consistency per reader** | Run each of 2-3 strong readers k=5 times (temp ~1). A candidate's per-model score is its frequency out of k. Use it as a stacking feature, or apply a global fractional τ. | +2 to +5 (Goto 2026: +4.5 to +14 on GEC, mostly precision) | k× read cost: about $0.75 per model-lesson at k=5 | Sampling correlated with itself. Diminishing returns if #2 is already in place. |
| 4 | **Signal-specific rules + hard negatives in the brief** (taxonomy approach) | From the error analysis, write 1-line rules plus 2 positive and 2 negative examples per signal type and per common FP pattern: MSA-leaning "corrections", orthographic variants, self-repairs, asked-for words. Retrieve them from other lessons' keys (leave-one-out). | +2 to +5 (taxonomy and few-shot gave +4 to +9 F0.5 in 2609.10810, via precision) | Writing time; slight brief growth | Over-specific rules cut recall. Validate on the held-out lesson. |
| 5 | **Windowed reading for recall** | Split the transcript into about 10-12 min windows with 1 min of overlap. Give each window only the word-list entries retrieved for that window's tokens, instead of the full 126k list. Merge, then deduplicate. | +2 to +4 (recall +5 to +10 per reader; long-context multi-item recall degrades and is worst mid-context) | About the same tokens, more calls; cheaper if the word list is trimmed | More FPs, which #2 and #3 must absorb. Context lost at window edges. |
| 6 | **Richer, regularized stacking** | Features: per-model sample frequency, verifier votes, stated confidence, `signal`, `kind`, rule ID, STT-suspect flag. L2 logistic or a depth-2 tree. Keep fewer than 10 features. Nested LOO for the threshold. | +1 to +3 over the current stack | ~$0 | Overfitting with 3 folds, which is why the feature budget is small. |
| 7 | **Calibrated confidence + abstention threshold** | Each reader and verifier gives 0-100 confidence. Calibrate it on training folds (isotonic/Platt over all models pooled). Keep items with p ≥ F*/1.25, which is about 0.6-0.7 at today's F*. | +1 to +3 | ~$0 extra | Verbalized confidence is coarse. Needs pooling to fit. |
| 8 | **Structured prosecutor/defender only on split votes** | For candidates with 3-5 of 8 votes only: quote-bound argument for and against, and a third-vendor judge run twice in swapped order. No free-form multi-round debate. | 0 to +2 | Small, few items | Sycophancy and flip-to-wrong (Wynn 2025; Choi 2025). Skip it if #2 already covers these items. |
| 9 | **Matcher and normalization audit** | Normalize Arabic orthography and Arabizi. Check timestamp tolerance and split/merged slips such as the duplicate `1:04:23` miss. Fix this blind to which side gains. | +0 to +3 | 1-2 h of code | Bias if tuned while watching the score. |
| 10 | **Evaluation infrastructure** (enables everything else) | Key 2 more lessons as a locked test set. Run nested LOO for all selection. Report paired bootstrap CIs and McNemar. Re-key one lesson blind to measure the human ceiling. | 0 direct; prevents fake gains of about 3-10 | 2-4 h of keying | None, apart from the time it takes. |

**Do not prioritize:**
- Unsupervised Dawid-Skene: correlated LLM errors break its assumptions, and the supervised stack is already better.
- Open multi-agent debate or councils: majority voting already captures their gains, and sycophancy flips hurt.
- Automated DSPy/GEPA prompt search: about 100 labels is far too few.
- Adding more vendors to the vote: the 8-model vote did not beat 2 models, a correlated-errors signature.

**Realistic projection:** #1 + #2 + #3/#4 + #6 should land around **84-88 held-out** against the current key, if the gains hold on a fresh lesson. Measured 90 probably requires the adjudicated key (#1). Beyond that point, scores are inside the human-agreement noise, which should be measured (#10) before chasing further.
