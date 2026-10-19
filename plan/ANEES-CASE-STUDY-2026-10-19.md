# Finding the Learner's Mistakes: A Retrospective Case Study of Transcribing and Grading Recorded Levantine Arabic Lessons with Speech Engines and Language-Model Judges (3 September – 18 October 2026)

**Public version (from master record v10).** Names are replaced by roles, and lesson excerpts are withheld until the tutor consents.

**Project.** Anees is a personal app. It turns one learner's recorded online Arabic lessons into transcripts, mistake lists, grades and study material.

**People.**

- the student: the student and project owner.
- the tutor: his Levantine Arabic tutor.
- Engineering: AI coding agents directed by the student (Anthropic Claude via Claude Code, OpenAI Codex).

**Sources and conventions.**

- **Record.** 2,466 commits, 450 messages the student typed, 60 plan documents, the rule registry and the experiment logs.
- **Revisions used.** Production branch `origin/master` at 9bdfcf5. Test branch `claude/reader-90-overnight` (R90) at 43fa688, with the statistics of review rounds 2–4 and the final key v3 (119 slips) at 614c7a2.
- **Copied evidence.** The R90 data files, logs and scripts that the paper's numbers rest on are copied unchanged into `research/evidence/r90-43fa688/`. Raw reader runs and lesson audio are not copied.
- **Quoted chat messages.** Stored with their UTC timestamps in `research/sources/tx-excerpts.json` and `medi-messages.jsonl`.
- **Dates.** Calendar dates are Pacific local time. Timestamps ending in Z are UTC. For example, 2026-10-19T05:25Z is 18 October, 22:25 Pacific.
- **Citation markers.**
    - **[E#]** raw evidence: commits, data, logs, messages.
    - **[A#]** AI-written audit summaries (`research/era-1.md` to `era-4.md`). These are secondary sources.
    - ***[inference]*** our own interpretation.
- **Hypotheses** in Sections 4–5 are *reconstructed* from the record unless a dated document stated them in advance.

---

## Abstract

**Background.** A learner of Levantine Arabic wanted every recorded lesson turned into an accurate list of the mistakes his tutor corrected.

**Methods.**

- **Lessons.** 24 lessons, processed over 46 days, in four phases of exploratory tests.
- **Engine choice.** Speech engines were compared by the tutor's blind preference vote.
- **Hearing.** Hearing methods were scored on two lessons by approximate word coverage.
- **Mistake finding.** Readers and judge panels were scored against the student's corrected answer keys on three lessons. Judge panels were scored by threshold-cross-validated F0.5, which weights precision above recall.
- **Revisions.** The keys were revised by the tutor's blind rulings, and by the student's unblinded confirmation of one model's extra findings.

**Results.**

- **Hearing (RQ1).** A second listen by Gemini 3.8 Flash with lesson context raised word coverage to 95.0% and 94.1%, against 69.4% and 60.7% for ElevenLabs alone.
- **Mistake finding (RQ2).**
    - On key v2, the last key before any judge's extra findings were added, no judge panel was distinguishable from the production reader once five comparisons were corrected for.
    - The production reader kept the highest recall.
    - On key v3, which adds 20 slips Gemini 4 Argon proposed, the Opus + Argon panel led (F0.5 88.7 against 77.7). That lead depends on the key revision and on a re-tuned threshold.
- **Answer key (RQ3).** The student confirmed 20 Argon-proposed slips that his review had not recorded. No inter-annotator reliability was measured.

**Conclusions.**

- A context-aware AI second listen is the largest measured gain.
- No mistake-finding method is confirmed.
- Against the final key, the student's review and each evaluated model each missed recorded slips.
- The study ends with a draft decision policy, based on pooled blind adjudication by the tutor. It is pending validation of its matcher.

**Keywords:** learner speech; corrective feedback; Levantine Arabic; speech recognition; LLM-as-a-judge; pooled assessment; evaluation methodology; case study.

---

## Summary in plain words

| Question | Answer (and how sure) |
|---|---|
| Can software write down what the student says, mistakes included? | Much better after a second AI listen: about 94–95% of his Arabic words matched, against 61–69% for ElevenLabs alone. Two lessons; the measure is approximate |
| Which AI best finds the mistakes the tutor corrected? | Not settled. On the older key, Opus + Astra had the only positive paired interval among five setups tested against today's reader, but it misses more mistakes. On the newer key, Opus + Argon leads, but that key includes Argon's own finds |
| What runs today? | Opus + Sonnet. On the older key it catches more mistakes than the precise judge setups, and it flags more that aren't mistakes |
| Is the student's own review a perfect key? | No. He later confirmed 20 more that Argon proposed. Others may still be missing |
| What next? | Many AIs hunt, the tutor marks each find blind, and a winner must win again on new lessons |
| What is "F0.5"? | A 0–100 score combining "how often a flagged mistake is real" and "how many real mistakes were caught", with more weight on the first |

---

## 1. Introduction

### 1.1 Problem

the student takes one-hour online Levantine Arabic lessons with the tutor over Google Meet. He wanted an app that shows, after each lesson:

- his mistakes,
- the words he used correctly,
- his progress.

Two problems sit at its centre.

1. **ASR "fixes" learner errors.** In this case, the engines wrote some of his wrong forms as right ones. the student noticed it on day two: "its automatically fixing my errors" (registry TR-01, 2026-09-04) [E1]. This is the case's own observation. It was not measured as a rate in Phase 1.
2. **What counts as a mistake is not obvious.** A tutor reacts to only some errors. Correct Levantine can differ from Standard Arabic. Questions are often not attempts.

### 1.2 What is being measured

The unit is a **tutor-corrected learner attempt** (a *slip*), not every linguistic error. The definitions in force differ by instrument, and that difference is itself a finding.

**Answer key (the student's review; grade-book rules PR-27) [E39].**

- A slip is a moment where the student produced an Arabic form, the tutor then gave or confirmed a different one, **and** in her judgement his form was wrong. An acceptable Levantine form that she reformulates for teaching is not a slip.
- "Asked for a word" earns a grey half-credit mark, never a slip.
- A moment with no tutor reaction is never a slip.
- Pronunciation is logged separately and is never a slip or a missed word (rule S4) [E47].

**Headline judges, "plain" prompt** (`reader_judge.prompt`, which inserts the definition `DEF`) [E26].

- *Counts:* a mistake the student made in Arabic that the tutor corrected or rejected. She recast it, said no, named the rule, prompted until he fixed it, or typed the fix in chat.
- *Does not count:*
    - asking for a word he does not know, or a word he did not yet know;
    - switching to English;
    - a self-fix before she reacts;
    - a stutter or cut-off;
    - a speech-to-text error;
    - a question about a rule;
    - correct Levantine that differs from Standard Arabic;
    - anything she let pass.
- *One slip per corrected moment.*
- `reader_judge.py` also defines a longer `DEF_V2`, which explicitly counts wrong forms said inside a question ("is it X?"). In this implementation, `prompt()` inserts `DEF` for every variant (plain, fewshot, v2, defend). `DEF_V2` is sent only by the council method (`reader_judge.council`, Table 3), so every headline judge used `DEF` [E26].
- **Mismatch.** The key counts attempted forms inside questions, but the judges' definition does not mention them.
    - About 18 of the 99 key-v2 slips (6 / 11 / 1 per lesson) and 25 of the 119 key-v3 slips were said in a line containing a question mark.
    - These counts come from a heuristic run by the case study: the student's nearest line within 3 s.
    - This bounds the size of the confound for the headline judges.

**Adjudication rules: decisions evidenced in the keys, and prospective rules.**

| Case | Rule | Example (lesson, time) |
|---|---|---|
| Wrong form in answer to an elicitation | Slip | [lesson excerpt withheld pending tutor consent] |
| *Contested:* a form inside his own question that the tutor redirects | Recorded as a slip, but arguably not an error | 10-08 06:27–06:40. the student: *binqlaq?* "we are worrying?" the tutor: "No, you can use the adjective. Or I worry. Do you wanna say I worry?" the student: "No, we are not worrying… we are worried" ([lesson excerpt withheld pending tutor consent]). Recorded in key v3 at 06:27 as a grammar slip, from Argon's proposal confirmed by the student. From a Levantine point of view *binʔlaʔ* "we worry" is a well-formed verb. the tutor offers an alternative construction after negotiating his meaning. This row shows a key label that the construct's own rules would question. |
| He asks for a word without attempting it | Not a slip; grey "asked" mark (PR-27) | — |
| Elicitation: the tutor prompts, he produces a wrong form, she fixes it | Slip | — |
| Sentence completion: the tutor finishes a sentence he had not attempted | Not a slip | — |
| Acceptable Levantine variant that she reformulates for teaching | Not a slip | [lesson excerpt withheld pending tutor consent] |
| Same wrong form corrected twice | Two slips | — |
| Pronunciation only | Logged separately; never a slip (S4) | — |

**Known gaps in the construct.**

- The rows **with** an example were applied by the student while reviewing, and by the tutor in AM-33. They were never written as a codebook before the keys were made.
- The rows without an example (asking for a word, elicitation, sentence completion, repeats) are **unvalidated prospective rules**. They state the intended treatment, but no labelled instance was located in the three keys, so their past application cannot be shown.
- Recasts that may be paraphrases remain judgement calls.
- "Can't tell" rulings are left out of the key.

### 1.3 Research questions

- **RQ1 (hearing).** Which method keeps the student's actual words, errors included?
- **RQ2 (finding).** Which reader, ensemble or judge design best recovers tutor-corrected slips?
- **RQ3 (ground truth).** How reliable is the human key, and how should it be built?
- **RQ4 (process).** Which decisions were well founded, and what protocol should govern change?

### 1.4 Contribution

This is a retrospective, exploratory case study. It offers:

- an evidence-linked account of 46 days of decisions;
- measurements on real learner–tutor audio, with stated uncertainty;
- a catalogue of failure modes common to evaluating language models against small human keys.

---

## 2. Background and related work

**Corrective feedback.**

- Lyster and Ranta distinguish six tutor moves after an error: explicit correction, recast, clarification request, metalinguistic feedback, elicitation and repetition. They define learner *uptake* as the learner's response [R1].
- Anees's signal labels follow this tradition: `recast`, `explicit-no`, `named-rule`, `prompt-then-fix`, `finished-sentence`, `asked`, `none`.

**Error annotation and scoring.**

- Grammatical error correction scores systems by precision, recall and F0.5. F0.5 weights precision more, because a false correction is treated as more harmful than a miss [R2, R3].
- ERRANT standardised error types [R4].
- The Cambridge Learner Corpus showed that error taxonomies need explicit guidelines and adjudication [R5].

**Arabic dialect ASR.**

- Dialectal Arabic recognition is a recognised research challenge; the MGB-3 challenge, for example, evaluated systems on Egyptian dialectal broadcast speech [R6].
- Whisper is a general model trained on large-scale, weakly supervised web data [R7].
- Combining recognisers by voting (ROVER) reduces word errors [R8]. Anees's "two of three listens agree" rule is a within-model analogue.

**Language models as judges.**

- LLM judges show position, verbosity and self-preference biases [R9].
- In the settings tested by Verga et al., a panel of diverse models agreed with human judgments better than one large judge [R10].
- Self-consistency (sampling and voting) improves some reasoning tasks [R11].

**Pooling.**

- Information-retrieval test collections pool the candidates of many systems. Assessors judge only the pool, blind to its source [R12].
- Pooled judgments can favour contributing systems over new ones [R13, R14].

**Small-sample evaluation.**

- Picking the best of many methods on the same data inflates its score [R15].
- Leakage from test data into design choices does the same [R16].
- McNemar's test and agreement statistics such as Cohen's kappa are standard tools for paired comparisons and annotator reliability [R17–R19].

---

## 3. Setting and data

### 3.1 Recordings

- **Lessons.** 24 lessons were published from 2026-08-25 to 2026-10-12 [E2].
- **Separate tracks.** From 2026-09-05 a Recall.ai bot recorded one track per person. Words with no speaker label fell from 13.6% to 0% [E3].
- **Phone only.** the student takes lessons on his phone ("I take my lessons from my phone right now"). That ended a planned two-channel PC recorder [E4].
- **Content.** Levantine Arabic with English explanations. the student sometimes writes Arabic in Latin letters ("Arabizi"). the tutor types some corrections in the chat.

### 3.2 Answer keys

the student reviewed three lessons line by line: **10-08** ("practice"), **10-09** and **10-10** ("exams") [E5].

**How independent are the keys of AI?** Not fully.

- the student reviewed pages that the production pipeline had already built and annotated: method A text, plus the production readers' mistake marks. This invites anchoring toward production.
- The tutor's AM-33 rulings were on disagreements between his key and AI readers. They included moments AI proposed and he had not marked. The two slips she added in v2 (10-10 12:01 and 14:01) were such AI-proposed moments [E9].

| Version | Date | Change | Slips (10-08 / 10-09 / 10-10) |
|---|---|---|---|
| v1 | 10-14 | the student's review, frozen | 102 (34 / 43 / 25) |
| v2 | 10-18 | the tutor's 14 blind rulings (AM-33): 5 removed, 2 added | 99 (33 / 40 / 26) |
| v3a | 10-18 | the student confirmed 30 Argon-proposed slips, not blind | 129 (43 / 54 / 32) |
| v3 | 10-18/19 | Removed 6 label-only duplicates, 3 the tutor had ruled "not a mistake", 1 she had ruled "can't tell" | **119 (40 / 50 / 29)** |

Sources: [E6, E7, E8, E9].

Of the 119 slips:

- 97 come from the student's review;
- 2 come from the tutor;
- 20 come from Argon, confirmed by the student.

### 3.3 Production pipeline

| Step | Method | Model | Access |
|---|---|---|---|
| 1 Transcribe | Both tracks, verbatim | ElevenLabs Scribe v2 | ElevenLabs subscription |
| 2 Re-listen (method A) | Each student line heard 3 times with 40 s of context and nearby chat. Two of three wins. A change toward the tutor's own word within 30 s is held for her (TR-27) | Gemini 3.8 Flash | Paid Gemini API |
| 3 Read for slips | Two readers. A slip stands only if both flag the same family within 15 s (PR-25) | Opus 5.5 + Sonnet 5.5 | Claude plan |
| 4 Grade-book rules | PR-27 (Section 1.2) | Code | — |
| 5 Tutor wins | the tutor's rulings override AI | Code | — |

Sources: [E10, E11, E12, E34].

---

## 4. Methods

### 4.1 Phase 1 (09-03 to 09-21)

- **Trust test.** A 50-line test was required before building: Arabic word accuracy ≥75% and speaker labels ≥90% [E13].
- **Engine choice by blind vote.** the tutor compared 4 shuffled transcripts on each of 20 clips. She could pick several or none. The rule was written before rating [E14].
- **Other trials.** OpenAI transcription models, Whisper variants, and a text-only detector of tutor reactions [E15, E16].

### 4.2 Phase 2 (09-22 to 10-07)

- **Readers.** Two Claude readers × two passes, plus a third reader for disputes, against a 95% agreement target [E17].
- **Engine benchmark (PR-18).** One lesson (10-02) was corrected into a frozen key of 63 moments, then 19 configurations were run three times each [E18].
- **Backfill.** The winning listener re-heard 18 lessons [E19]. the tutor then checked, blind, 27 lines where a confirmed slip had vanished [E20].

### 4.3 Phase 3 (10-08 to 10-15)

- **Grade book (PG-46).** Scores the page as it stood before the student's review against his key [E21].
- **Protocol (PR-23).**
    - Defines practice and exam lessons, paired tests, and a rough power estimate.
    - The estimate: three lessons can reveal differences of about 13–19 points "on slips". No F0.5-specific power calculation was given.
    - Adoption rule: a change must "win on the practice lesson AND the next exam", and hidden mistakes must not rise.
    - The protocol was never marked "enforced" [E22].
- **Hearing experiment (2026-10-14) [E23].**
    - *Hit rate* is approximate word coverage. For each Arabic word the student said on a key line, the scorer looks for an unused word on the same line of the candidate text. A word counts as found when either its normalised "core" matches, or both cores have at least 3 letters and a sequence-similarity ratio of at least 0.75 (`difflib`).
    - Normalisation (`transcript_marks.normalise`, `word_coverage.core`):
        - remove diacritics and tatweel;
        - lowercase;
        - map أ إ آ ٱ → ا, ة → ه, ى → ي, ؤ → و, ئ → ي;
        - join a detached "ال " to the next word;
        - drop a leading و only when it precedes ال in a word of more than 4 letters;
        - then drop a leading ال in a word of more than 3 letters.
    - **Tokens.** For the exam keys, `hearing_harness.word_hits` scores each key line as follows.
        - **Identical lines.** If the candidate line is identical to the key line, all its words count as heard.
        - **Other lines.** Otherwise the candidate's words come from `word_coverage.word_tokens`:
            - sound tags are removed;
            - Arabic-script words are kept as written;
            - English fillers (uh, um, okay, …) are skipped;
            - a Latin word counts as Arabic only if the Arabizi reader recognises it as one of the tutor's words or closed-list words, and in a line that also contains English it must carry an Arabizi digit or be a closed-list word;
            - tokens ending in a dash (cut-offs) are **excluded**.
    - **Matching order.** Key words are matched in key order. Each takes the first unused candidate word with an exact core; failing that, the first similar one.
    - **What this can hide.** Article removal, letter conflation and fuzzy matching can count a word as heard even when the learner's own morphology differs from the candidate text — for example, a missing or extra article, ة/ه, or a one-letter ending.
    - **What FCR detects.** FCR detects exactly one failure: the tutor's correct form replacing his wrong form on a key slip. It does not detect omissions, other morphology changes or invented words.
    - The denominator is the number of key Arabic words: 543 on 10-09 and 506 on 10-10. Source: `docs/data/review-grades.json`, grade-book `before.words` for each exam.
    - Word order is ignored, extra words are not penalised, and insertions, deletions and substitutions are not reported separately. It is a coverage measure, not a word error rate.
    - *FCR* is the share of key slips where the text shows the tutor's correct form instead of his wrong one.
    - *Significance* is a paired exact sign test on words. It ignores clustering within lines and lessons.
- **Reader experiment (2026-10-15).** One read each from Opus and Sonnet on the three keyed lessons. Five aggregations were compared [E24].

### 4.4 Phase 4 (10-16 to 10-18)

**Inputs.**

- Phase 3 and 4 reader and judge scores use the **key transcripts**: the student's corrected text, with hearing errors removed [E28].
- They measure finding mistakes on an ideal transcript, not end-to-end production accuracy.

**Readers.**

- Every available Gemini and OpenAI model was run as a reader. Paid API keys were used at first. From 2026-10-18, readers ran on the student's plans [E25].
- In the "fair re-run", every model got the same pasted input, and Claude's tools were disallowed.

**Judge panel** (`reader_judge.py`, "plain" prompt) [E26]:

1. **Pool the flags.** The six "plan-pool" readers' flags are clustered into candidates (same family, within 15 s): 53 / 64 / 40 candidates on the three lessons. The six readers:
      - Opus and Sonnet, original runs with file access;
      - Gemini 3.7 Flash and 3.1 Pro, paid API, cached;
      - GPT-5.6 Terra and GPT-6 Astra, via Codex on the plan.
2. **Drop rows.** "Asked" and no-reaction rows are removed.
3. **Judge.** Each judge returns "slip" or "not" with a confidence of 0–100. This becomes an *uncalibrated* score: confidence for "slip", 100 − confidence for "not".
4. **Combine.** The panel score is the mean or the minimum across judges.
5. **Decide.** A candidate is accepted at or above a threshold. The threshold is chosen on a grid from 0.10 to 0.95 (step 0.05) by maximising F0.5 on the other two lessons.
6. **Repetition.** Each judge ran once per lesson. A missing verdict scores 0.

**Matching** [E28]:

- same family, within 15 s, one-to-one, nearest first;
- F0.5 = 1.25·P·R / (0.25·P + R), with counts pooled over the three lessons.

**Validity.**

- This is **threshold cross-validation only**. The held-out lesson was also used to develop prompts, choose models and revise the key.
- All Phase 4 scores are therefore exploratory, not unbiased estimates.

**Production comparator.**

- The production reader's output includes grey "asked" marks. These are shown as help, never as slips.
- The main comparator therefore scores its **slip output only**, with "asked" marks removed. The version that counts them is also reported.

**Uncertainty** (`case_study_stats.py`, `case_study_stats2.py`) [E45]. All intervals below are **exploratory, conditional calculations**: they take each method's chosen threshold as given.

- **Per-method bootstrap.** 95% CIs from 4,000 draws, resampling the three lessons, then the units within each (matched, false, missed).
- **Paired bootstrap of ΔF0.5.** Within a lesson, key slips are resampled jointly for both methods. False flags are Poisson-resampled.
- **McNemar.** An exact McNemar test on key slips caught by one method only.
- **What these do not account for.**
    - None of them refits the threshold, models selection among methods, or allows for dependence within a turn.
    - False flags are resampled separately for each method, so overlap between the methods' false flags is lost.
    - McNemar treats slips as independent.
    - A three-cluster bootstrap adds little between-lesson variance.
- **Their coverage is not established.** The omitted dependence and selection could distort them in either direction, and none of them establishes a unique winner.

**Configuration** (Appendix C):

- **Claude.** Ran via `claude -p` at the CLI's default effort (not recorded), tools disallowed.
- **Codex.** Ran in a read-only sandbox at its default reasoning setting (not recorded per run; a Codex log from the same night shows "medium"). Whether Codex used tools is not recorded: the archived wrapper keeps only the final answer and the route.
- **Argon.** Ran via `agy` with the "high" effort slug. Its file viewer was available.
- **Hashes.** The candidate-list, transcript and prompt hashes are in Appendix C.

**Key revision** [E29, E8, E30]:

- the tutor's blind AM-33 rulings;
- the student's non-blind review of Argon's extra findings;
- the tutor's blind AM-35 review of the other judges' extra findings (pending).

---

## 5. Results

### 5.1 Phase 1

**Table 1. the tutor's blind vote, 20 clips (2026-09-04) [E14].** Multiple picks were allowed, so totals exceed 20: 3 clips were "none", 2 were ties, and several had two winners.

| Engine family | Clip-wins (family total) |
|---|---|
| ElevenLabs Scribe v2 (two settings, 10 each) | 15 |
| Speechmatics ar_en | 5 |
| Local Whisper variants | 2 |

- The engine report (fd1d2a5) also gives head-to-head counts of 11–1 and 13–0 for ElevenLabs. The repository does not hold the per-clip map from letters to engines, so those counts cannot be re-derived here.

- This measured preference, not accuracy.
- **OpenAI models** produced wrong-language output, blank replies (30% for gpt-audio-1.5) and one runaway loop. Adding the student's vocabulary made them worse [E15].
- **The tutor-reaction detector** was weak. Its best result was P 0.50 / R 0.70, with a leave-one-out AUC of 0.52–0.57 [E16].
- **The trust test** was never scored. the student's ratings were lost [E13].

### 5.2 Phase 2

- **Reader agreement.** The two Claude readers overlapped on 61.5% of rows per pass. This is a Jaccard overlap, ranging 48.5–80.9% by lesson; the 95% target was never met [E17, A2].
- **Grammar detector.** It "passed" at 81% recall on the rows it was tuned on. Held-out recall was 45%, and on real lessons it caught 11% (104 of 961) [E31].
- **Engine benchmark** (one lesson, 63 moments heard correctly) [E18]:

| Engine | Moments heard |
|---|---|
| Gemini 3.8 Flash with context | 53 |
| Gemini 3.8 Flash, earlier context only | 49 |
| OpenAI gpt-audio-1.5 | 24 (hid 11 of 24 slips) |
| Deepgram nova-3 (best plain transcriber) | 21 |
| ElevenLabs, published text | 4 |

    - No prompt variant beat 53 by more than ±2.
    - Gemini Pro at temperature 0 lost $17.93 in a reasoning loop [E32].
- **The key was fallible.** Re-listening, the student found 2 of 4 of his own corrections wrong [E33].
- **Backfill.**
    - It changed 3,158 lines in 18 lessons ($43.99).
    - the tutor found 12 of 27 confirmed slips hidden. The do-not-publish threshold was 8 [E19, E20].
    - The hold rule was then widened from 15 s to 30 s plus chat [E34].

### 5.3 Phase 3: hearing

**Table 2. Hearing experiment (2026-10-14) [E23]**

| Cell | Description | Hit 10-09 (543 words) | Hit 10-10 (506 words) | FCR 10-09 (n=42) / 10-10 (n=25)¶ |
|---|---|---|---|---|
| **A** | ElevenLabs + Gemini ×3, 2 of 3 | **95.0%** | **94.1%** | 2.4% / 0.0% |
| E1 | Gemini once | 90.8% | 92.3% | 4.8% / 0.0% |
| C | Three-engine vote + judge | 87.8% | 89.5% | 2.4% / 0.0% |
| F† | Both engines, disagreements re-heard, judge | 86.6% | 86.8% | 7.1% / 8.0% |
| E | Gemini twice | 86.2% | 86.6% | 0.0% / 0.0% |
| B‡ | Gemini whole track, ElevenLabs line times | 81.4% | 77.9% | 7.1% / 8.0% |
| — | ElevenLabs alone | 69.4% | 60.7% | 0.0% / 0.0% |
| page* | The page as published before the student's review | 97.8% | 95.5% | 0.0% / 0.0% |

- ¶ **FCR denominators.** These are key-v1 slips that have a recorded correct form (`slips_judged`): 42 of 43 on 10-09 (one slip has no recorded right form) and 25 of 25 on 10-10.
- **Significance.** Every non-page cell is below A at sign-test p < 0.001, except E1 on 10-10 (p = 0.08). The page row is above A (p = 0.0001 on 10-09, p = 0.016 on 10-10).
- \* **The published page is advantaged.** The key *is* the student's correction of that page.
    - The page also carries production steps after the A vote, such as the misheard-word fixes (TR-32) *[inference: from the rule dates, not checked line by line]*.
    - So the "A" row is the re-listen vote alone, rebuilt from its cached runs, and the page row is the full shipped pipeline. Neither is an unbiased accuracy estimate.
- † **F was damaged.** The ElevenLabs credit ran out, so 87 (10-09) and 21 (10-10) of F's second listens failed and fell back to the first.
- ‡ **B was penalised for placement.** About half of B's misses were heard but placed on a neighbouring line. With perfect placement B scores about 90.6 / 90.7.
- **D was not run.**
- **A may be favoured.** The key was made by correcting an A-based page *[inference]*.
- **Cost.** Metered spend was $5.10. The per-cell fields sum to $7.23, because B and F share one whole-track transcription and each counts it.

### 5.4 Phase 3: readers

On key v1 (102 slips), one read per model, scored **before** the PR-27 alignment [E24]:

| Aggregation | F0.5 |
|---|---|
| Both agree | 69.6 |
| Opus | 65.0 |
| Debate | 65.0 |
| Sonnet | 61.9 |
| Either | 58.4 |

- The pair was adopted (PR-25) on a 4.6-point win, after comparing five aggregations.
- After the scoring dropped "asked" and no-reaction rows, the same pair scored 78.8 (Table 3). The two numbers are not comparable.

### 5.5 Phase 4: readers, ensembles and judges

Rows are comparable only within one key version and candidate pool. Counts in the record: 253 scored rows, 112 unique logged method strings and 156 method × key-size combinations [E27]. Logged strings are not de-duplicated experimental configurations.

**Table 3. Key v1 (102 slips), PR-27-aligned scoring, union of 8 readers [E27]**

| Method | Aggregation | F0.5 | P | R |
|---|---|---|---|---|
| Gemini 3.7 Flash reader | — | 73.6 | 79.5 | 56.9 |
| Sonnet reader: original / fair re-run | — | 72.8 / 68.0 | 72.4 / 69.1 | 74.5 / 63.7 |
| Opus reader: original / fair re-run | — | 72.5 / 72.7 | 72.5 / 73.0 | 72.5 / 71.6 |
| GPT-5.5 reader (paid API) | — | 72.4 | 72.1 | 73.5 |
| GPT-6 Astra reader (plan) | — | 66.6 | 68.5 | 59.8 |
| Opus + Sonnet (test harness) | both agree | 78.8 | 82.1 | 67.6 |
| 8 readers | majority / logistic stack | 77.7 / 79.4 | 84.5 / 83.8 | 58.8 / 65.7 |
| Opus ×3 | self-consistency | 75.3 | 78.6 | 64.7 |
| Council (5 Flash advisors + Opus chair)§ | — | 73.9 | 74.5 | 71.6 |
| **Judges: Opus + Gemini 3.7 Flash** | mean | **80.6** | 85.0 | 66.7 |
| Codex best of 12 offline combinations | — | 82.1 | 87.2 | 66.7 |

- § The council is the only method judged under `DEF_V2`, the definition that counts forms inside questions. Every other judge row used `DEF`.
- **Harness versus production (historical).** The harness's "both agree" (78.8, key v1) and the production gate's slip output (73.7, key v2) were computed on different keys, with different gate code. Those historical scores cannot establish whether the gate rules matter. No same-key comparison was made.
    - The harness drops "asked" rows.
    - The production gate keeps them as grey half-credit marks.
    - Table 4's main comparator removes those marks ("slip output"). The version that counts them is shown below it.
- **The fair re-run** lowered Sonnet by 4.8 points.

**Table 4. Plan-route judges (subscription; no additional API charge recorded; candidate pool includes two cached paid-API reader runs) over the plan pool: per-method F0.5 with bootstrap 95% CI [E26, E45]**

| Judges | Agg. | Key v2 F0.5 [CI] | v2 P / R | Key v3 F0.5 [CI] | v3 P / R | v2→v3 |
|---|---|---|---|---|---|---|
| Opus + GPT-6 Astra | mean | 83.1 [75.9–89.1] | 92.2 / 59.6 | 83.2 [76.5–89.2] | 86.1 / 73.1 | +0.1 |
| Opus + Astra | min | 81.7 [74.6–88.1] | 89.6 / 60.6 | 82.2 [75.0–88.6] | 84.6 / 73.9 | +0.5 |
| Opus + Gemini 4 Argon | mean | 79.0 [68.8–86.7] | 86.6 / 58.6 | 88.7 [82.4–93.7] | 90.7 / 81.5 | +9.7 |
| Gemini 4 Argon | — | 79.4 [69.8–87.1] | 84.2 / 64.6 | 88.4 [82.1–94.0] | 89.4 / 84.9 | +9.0 |
| Opus | — | 79.2 [70.4–86.2] | 85.7 / 60.6 | 81.7 [74.8–87.6] | 87.5 / 64.7 | +2.5 |
| GPT-6 Astra | — | 77.2 [66.3–88.6] | 82.4 / 61.6 | 81.9 [74.1–88.9] | 85.0 / 71.4 | +4.7 |
| Opus + Astra + Argon | mean | 82.6 [75.0–88.9] | 92.1 / 58.6 | 85.7 [78.8–91.4] | 88.3 / 76.5 | +3.1 |
| Gemini 3.8 Flash | — | 74.9 [64.1–84.9] | 79.2 / 61.6 | 79.8 [72.6–86.1] | 86.7 / 60.5 | +4.9 |
| GPT-OSS 120B | — | 61.4 [52.4–69.2] | 58.2 / 78.8 | 74.8 [65.8–81.7] | 72.7 / 84.9 | +13.4 |
| *Production: Opus + Sonnet both agree, slip output* | gate | 73.7 [64.9–81.7] | 73.7 / 73.7 | 77.7 [70.0–84.5] | 80.8 / 67.2 | +4.0 |
| *Production, counting "asked" marks as flags* | gate | 69.1 [61.0–76.7] | 67.6 / 75.8 | 75.5 [68.4–82.0] | 76.6 / 71.4 | +6.4 |

- **Production is in-sample.** Its rows have no tuned threshold.
- **Source.** The three rows above Production (Opus + Astra + Argon, Gemini 3.8 Flash, GPT-OSS) were computed by `replay.py`.
- **GPT-OSS gained +13.4.** It flags many moments, so the 20 Argon-proposed slips added in v3 probably overlap its existing flags *[inference]*.
- **Paid readers in the pool.** Two of the six readers whose flags form the candidate pool were paid-API runs, cached.

**Table 5. Paired comparisons with production, slip output (method − production) [E45]**

| Method | Key | ΔF0.5 [paired 95% CI] | Slips caught only by method / only by production | McNemar p |
|---|---|---|---|---|
| Opus + Astra (mean) | v2 | **+9.4 [+0.9, +17.7]** | 5 / 19 | 0.007 |
| Opus + Argon (mean) | v2 | +5.3 [−5.0, +14.1] | 5 / 20 | 0.004 |
| Argon | v2 | +5.7 [−4.6, +14.4] | 8 / 17 | 0.11 |
| Opus | v2 | +5.5 [−5.0, +14.6] | 5 / 18 | 0.011 |
| Astra | v2 | +3.5 [−7.0, +13.8] | 5 / 17 | 0.017 |
| Opus + Astra (min) | v2 | +8.0 [−1.6, +17.5]† | 5 / 18 | 0.011 |
| Opus + Argon (mean) | v3 | **+11.0 [+3.1, +18.6]** | 24 / 7 | 0.003 |
| Argon | v3 | **+10.7 [+3.0, +18.2]** | 26 / 5 | 0.0002 |
| Opus + Astra (mean) | v3 | +5.5 [−2.3, +13.9] | 19 / 12 | 0.28 |
| Opus + Astra (min) | v3 | — | 19 / 11 | 0.20 |
| Opus | v3 | +4.0 [−3.9, +11.7] | 12 / 15 | 0.70 |
| Astra | v3 | +4.2 [−4.7, +12.8] | 18 / 13 | 0.47 |

- **On key v2:** each of the five configurations compared here catches fewer key slips than production, but makes far fewer false flags. (GPT-OSS 120B, not compared here, had higher recall.)
- **On key v3:** the Argon setups catch more slips than production.
- † Computed afterwards with 10,000 draws. The other rows use 4,000 draws.
- **Multiple comparisons.** Six configurations are compared with production on each key, and none of the 95% intervals above is corrected.
    - **At the Bonferroni level for five comparisons (99%)** — the five configurations first chosen — the best v2 result, Opus + Astra (mean), is +9.4 with interval [−2.5, +20.2] (10,000 draws).
    - **No v2 configuration is distinguishable from production** at that level.

**Table 6. Key revision versus threshold re-tuning (F0.5) [E45]**

| Method | v2 thresholds, key v2 | v2 thresholds, key v3 | v3 thresholds, key v2 | v3 thresholds, key v3 |
|---|---|---|---|---|
| Opus + Argon (mean) | 79.0 | 78.8 | 75.0 | 88.7 |
| Argon | 79.4 | 81.6 | 73.5 | 88.4 |
| Opus + Astra (mean) | 83.1 | 80.0 | 71.6 | 83.2 |
| Opus | 79.2 | 78.9 | 77.6 | 81.7 |
| Astra | 77.2 | 80.7 | 72.1 | 81.9 |

- **The thresholds moved, and are unstable.** Astra alone chose 0.25 / 0.90 / 0.10 across the v3 folds. Separately: Opus + Argon's tuned threshold fell from 0.80 / 0.80 / 0.75 (v2) to 0.60 / 0.60 / 0.40 (v3). Removing one duplicate slip from the key shifted two of those folds.
- **Argon's v3 lead needs both the key change and the lower threshold.** With either alone, it scores 73.5–81.6.

**Per-lesson counts on key v3 (matched / false / missed) [E45]**

| Method | 10-08 | 10-09 | 10-10 |
|---|---|---|---|
| Production (slip output) | 29 / 6 / 11 | 31 / 8 / 19 | 20 / 5 / 9 |
| Opus + Argon | 36 / 3 / 4 | 39 / 4 / 11 | 22 / 3 / 7 |

### 5.6 The answer key

- **the student's review** contributed 97 of the 119 v3 slips.
    - He later confirmed 20 Argon-proposed slips that his review had not recorded. He confirmed them without blinding, in one reply, so whether all 20 are true tutor-corrected slips is not independently established. They are not a lower bound on what his review missed.
    - The other judges' 30 extra moments are with the tutor (AM-35).
- **No inter-annotator reliability was measured.** No kappa or other agreement statistic was computed for the keys [R18, R19 describe the standard tools].
- **AM-33** is the only human-to-human comparison. On 14 moments selected because the AI and the student's key disagreed, the tutor sided with the AI on 7, with the student's key on 6, and could not tell on 1. This is a selected set, not a reliability estimate.
- **the student's notes on 10-09.** the tutor judged 76 of the 80 notes right and 4 partly right [A3].

### 5.7 Cost

| Phase | Logged paid AI spend | Notes |
|---|---|---|
| 1 | Under $5 | [E15] |
| 2 | About $120–130 at list price | Google billed about 1.5× the logged list price [E32] |
| 3 | $5.10 metered for the hearing test | [E23] |
| 4 | OpenAI API credit exhausted, amount not recorded; Gemini API small | All judges on monthly plans from 2026-10-18 [E25] |

---

## 6. Discussion

### 6.1 RQ1: hearing

- **The largest measured gain** was a context-aware second listen, repeated three times with a vote. Approximate word coverage rose from 61–69% to 94–95% on two lessons.
- **The measure** is not a verbatim error rate.
- **The risk.** The mechanism can erase the mistakes the app exists to find: the backfill hid 12 of 27 confirmed slips before the hold rule was widened.
- **A's hidden-mistake rate** on the exams was 1 of 67 slips. That is encouraging but rests on few slips.

### 6.2 RQ2: finding mistakes

- **What helped and what did not.** Judges ruling on a pooled candidate list scored higher than larger votes, debate or a council on these lessons.
- **Where the gain comes from.** On key v2, the judges' gain over the production reader comes from precision. Production had higher recall than every judge setup with precision above 80%.
- **On key v2, no judge configuration is distinguishable from production.**
    - Uncorrected, Opus + Astra's 95% interval just excludes zero (lower bound +0.9).
    - Corrected for the comparisons made, it does not ([−2.5, +20.2] at 99%).
    - That positive interval also depends on a comparator choice made during review. With "asked" marks counted, the difference was +14.0; with slip output only, +9.4.
    - Opus + Astra would also fail the proposed adoption rule: its recall is 14.1 points below production's.
- **Argon.** Among judges with precision above 80%, Gemini 4 Argon had the highest recall on key v2 (64.6%). GPT-OSS 120B had more recall (78.8%) at 58% precision.
- **Uncertainty.** The intervals overlap widely and are conditional. The earlier "about 4 points" noise figure [E44] came from a recall standard error and is too optimistic.
- **Is F0.5 the right target?** F0.5 counts a false mistake as worse than a missed one. That comes from writing correction [R2, R3], where a false correction misleads the writer.
    - For a learner reviewing his own lessons, a missed mistake is also costly: it is never practised.
    - Precision and recall are therefore reported side by side. Section 8 adds a recall floor to the adoption rule.

### 6.3 RQ3: the answer key

- **The key moved.**
    - The tutor's blind rulings cut it by 3 net slips.
    - One model's confirmed findings added 20 (99 → 119).
- **Recall is pool-relative.** Slips no reader proposed were never judged.
- **Contributors can gain.** Methods whose candidates were adjudicated can gain when the key is revised, but it is not guaranteed (Table 6).
    - From v2 to v3, with re-tuned thresholds: the Argon setups +9.0 to +9.7; Opus +2.5; Astra +4.7; the Opus + Astra panels +0.1 and +0.5; production's slip output +4.0.
    - With thresholds frozen at v2, Opus + Argon moved −0.2 and Argon alone +2.2.
    - This pattern is *consistent with* pooling bias [R13, R14]. It is not a measurement of it: no matched set of methods was left out of the adjudication.

### 6.4 The protocol that came out of the study

On 18 October the student wrote: "I'm thinking for the testing we are always going miss errors. This is actually an ok method for us to try find as many errors as possible then review the errors it found without us and we can mark correct or not" [E35].

- **What it is.** Pooled blind adjudication, as used to build TREC collections [R12].
- **What is not yet known.** Its benefit over one careful reviewer is untested here (Section 8, H2).

---

## 7. Post-mortem

### 7.1 Gates written but not enforced

- **The trust test** was never scored, and eight modules shipped within about 27 hours [E13].
- **The PR-23 protocol** stayed "written", and no code blocked deviations [E22].
- **No reader change has met the adoption rule**, including the production reader [E36].

### 7.2 Leakage and selection

- **The grammar detector:** tuned and graded on the same rows. It scored 81% there, 45% held-out and 11% in use [E31].
- **Lesson 10-09:** audited five times with rules from the student's first review before it was named an exam [E37].
- **The production reader:** chosen as the best of five aggregations, by 4.6 points [E24].
- **Phase 4 overall:**
    - 112 logged method strings were scored on the same three lessons.
    - A nested subset search, which chose its subset inside each fold, scored 69.4 [E27]. It searched a narrower space than the whole development process, so it is not a measure of the selection effect; it is reported only for completeness [R15].
    - Thresholds also moved sharply with the key (Table 6).

### 7.3 Measurement errors found after the fact

- **Invalid 57.2.** Judge verdicts were re-scored against a different candidate list. The judges were re-run [E38].
- **Hidden "asked" marks.** A test-scoring rule copied into the display hid 103 "asked" marks. It was reverted [E39].
- **Key contamination.** A re-freeze from rebuilt pages leaked unreviewed AI output into the key. It was reverted to explicit add/remove lists [E40].
- **Label duplicates.** The family-strict matcher let 6 label-only duplicates into key v3a.
    - the student spotted the first ("It found this earlier in the PDF"); three more were found the same night.
    - The case-study audit found a fifth (10-08 36:03), and review round 4 a sixth (10-10 13:52, the same moment as the tutor's 14:01 slip) [E9].
- **Silent imports.** The test scripts import some modules from the separate hourly checkout. `vendor_read.py` adds its path to load API settings, so production's `reader_agree.py` (hourly commit 91b922d) was used to score the production gate. It is copied into the evidence folder [E45].
- **The comparator changed during review.** Between review rounds, the production comparator moved from gated output with "asked" marks to slip output only. That lowered the headline Opus + Astra gain on key v2 from +14.0 to +9.4 points. Both versions are reported in Table 4.
- **Unlogged numbers.** 83.5, 57.2 and the production reader's v3 score were not in the experiment log. They are now logged in `case-study-stats*.json` [E36, E45].

### 7.4 Circularity and asymmetry in key v3

- **Uneven review.**
    - Argon's findings were confirmed in one reply, on a page that named Argon and gave its reasons [E8].
    - The other judges' findings went to the tutor blind (AM-35) [E30].
- **Tutor rulings applied.** Three Argon additions contradicted the tutor's earlier "not a mistake" rulings; one she had ruled "can't tell". Under the project rule they were removed, with the fifth and sixth label-only duplicates (125 → 119) [E9].
- **Consequence.** Key v3 was expanded through Argon's proposals, so it *may* favour contributing methods. The construction shows unequal checking and a risk of contributor advantage, not the size or even the direction of any bias. With v2 thresholds fixed, Opus + Argon moved from 79.0 to 78.8. Key v2 is the comparison point before Argon's findings entered, but it is not independent of AI (Section 3.2).

### 7.5 Money and access

- **Uncapped API spend.** A vendor test sent every OpenAI model through a paid API key with no dollar cap from the student on record. The credit ran out mid-run [E25].
- **Missed plan route.** A plan route existed (Codex on the ChatGPT subscription, no additional API charge recorded), but the agent said twice that it did not. It also logged Codex out [E25].
- **The rule that followed.** Plans first; a paid key only with the student's yes and a dollar cap; never change a login [E41].
- **Gemini access.**
    - Google announced that the Gemini CLI would move personal plans to the Antigravity CLI [R21]. The Gemini CLI login was rejected on 18 October [E48].
    - The Antigravity CLI (`agy`) restored Gemini access through the student's Google AI Pro subscription (no additional API charge recorded) [E42, R20].
    - On 18 October a probe showed Gemini 4 Argon returning a transcription of an audio clip through `agy` [E46]. It ran on the monthly subscription, and no additional API charge was recorded; billing itself was not inspected. That one response does not establish transcription quality.
    - A full hearing test of Argon (H4) began the same night. It stopped on 2026-10-19 when the plan's weekly quota ran out ("Individual quota reached… Resets in 163h"). It had covered listen 1 (502 of 534 lines) and part of listen 2 (296) for 10-09, and nothing yet for 10-10. **On this plan, one weekly quota covers about 1.5 lesson-listens, so Argon cannot replace the paid listener at production volume.**
    - **H4 result (exploratory, paid API, 2026-10-19).** The same production requests were sent with only the model changed to Gemini 4 Argon: 3 listens × 2 lessons, 3,149 calls, $12.73. The 10-10 third listen was 486 of 532 lines; the API credit ran out mid-pass and it was not fully refilled.
        - **Hit rate, Argon 3-listen vote vs Flash 3-listen vote:** 10-09 84.0% vs 91.2%; 10-10 79.1% vs 89.7%. Sign test p < 0.001 on both.
        - **FCR:** Argon 0/40 and 1/26; Flash 0/40 and 0/26.
        - **Conclusion:** Argon hears the student worse than Flash. It is not adopted as the listener.
        - Source: `data/lesson-work/harness/argon-api-hearing-2026-10-19.json`, `scripts/hearing_argon_api.py`.

### 7.6 Human-instrument failures

- **Lost ratings.** the student's first ratings were never saved [E13].
- **Fast review mode** was built to measure review time and anchoring, but was never used for the exams ("so you messed up the test?") [E37].
- **The planned blind re-listen** of 15 key moments per exam never ran [E37].

### 7.7 Record-keeping

- **Missing transcripts.** Session transcripts from 09-06 to 10-01 are largely missing. Many decisions survive only as quotes in the rule registry [E43].
- **Mid-turn messages** were missing from the first extraction. They are now in `tx-excerpts.json`.

---

## 8. Proposed protocol for the next lessons

This section is a *proposal*: a **decision policy**, not a confirmatory statistical test. It becomes a registration once committed and frozen before the next graded lesson.

- H1–H3 use new, locked lessons, so they are free of the selection problems of this study. Their intervals still come from three lesson clusters, have no demonstrated calibration, and are treated as exploratory guides to a practical decision.
- H4 reuses old lessons and is exploratory only.

**Practical margins, and why.**

- **Recall: −10 points.** Ten points of recall is about 4 tutor-corrected mistakes in a 40-slip lesson. These are proposed margins, not derived ones. the student must confirm them before the protocol is registered.
- **Precision: −5 points.** At about 40 flags per lesson (the order of the methods' flag counts here), five points of precision is about 2 extra false "you made a mistake" marks. Flag counts differ between methods, so this is only an illustration. False marks cost the learner more trust than misses, which is the reason F0.5 is used at all.
- **Both margins are judgements.** They are stated before the data and must be confirmed by the student at registration.

### H1: judge panels beat the production reader

**Thresholds.**

- **Why a new key is needed.** Neither existing key matches how future keys will be built. Key v2 predates the judges' extra findings, and key v3 adds one model's findings, unblinded.
- **Key v4** = key v2 + every judge's extra finding, adjudicated blind by the tutor. That covers the other judges' 30 (AM-35) **and Argon's 20, sent to her blind as well**, so that no model's findings enter by a different process.
- **The frozen value.** For each panel, the threshold that maximises pooled F0.5 over all three v4 lessons (grid 0.10–0.95, step 0.05). A tie goes to the higher threshold, which gives fewer flags.
- **Stability check only.** Leave-one-lesson-out fold thresholds on v4 are reported alongside. They are not used to set the value.
- **Freeze.** Thresholds are frozen before the first test lesson is graded.
- **Why this matters.** The current fold values (Appendix C) show how unstable thresholds are: 0.80 on v2 and 0.35–0.60 on v3 for the panels, and 0.10–0.90 for Astra alone.

**Panels pre-specified (two):**

| Panel | Prompt | Aggregation | Threshold |
|---|---|---|---|
| P1: Opus 5.5 + GPT-6 Astra | plain (`DEF`) | mean | Pooled-F0.5 fit on key v4, frozen |
| P2: Opus 5.5 + Gemini 4 Argon | plain (`DEF`) | mean | Pooled-F0.5 fit on key v4, frozen |

- **Prompt.** It stays `DEF` so that results remain comparable with this study. Aligning the judge definition with the key's rules is a separate future test.
- **Test lessons.** The next **three** fully graded lessons, scored on keys built by step 3.
- **Comparison.** Δ = panel − production slip output, for F0.5, recall and precision.
- **Multiplicity.** As a conservative convention, each of the 6 intervals (2 panels × 3 metrics) is computed at 99.17%, the Bonferroni level for 6. Because the component intervals are not shown to be calibrated, this gives **no guaranteed joint coverage**.

**Decision rule for each panel**

| Outcome | Condition |
|---|---|
| **Adopt** | ΔF0.5 interval lies above 0, **and** lower bound of Δrecall ≥ −10, **and** lower bound of Δprecision ≥ −5 |
| **Reject** | ΔF0.5 interval lies below 0, **or** upper bound of Δrecall < −10, **or** upper bound of Δprecision < −5 |
| **Inconclusive** | Anything else |

- **If both panels are adopted:** the one with the larger lower bound of ΔF0.5 is deployed. If the two bounds differ by less than 1 point, P1 is deployed, because it does not include the model whose findings shaped key v3.

**How scores and intervals are computed.**

- **Reference.** Each method is scored against the *observed* adjudicated key of the test lessons. That key contains:
    - every candidate the tutor confirms;
    - every extra slip she finds inside candidate turns;
    - every slip she finds in the sampled other turns.
- **"Can't tell" moments** are removed from both the key and every method's predictions before scoring.
- **Resampling.** The unit is the student turn. Each turn's key slips and both methods' true and false flags are resampled together, keeping shared errors and dependence within a turn. Lessons are resampled first, then turns. 10,000 draws, with the seed recorded. Intervals are percentile intervals.
- **Calibration.** With three lessons these intervals are not established to have their nominal coverage. The rule is a pre-committed decision policy. A result that is not "Adopt" is reported as such, never rounded up.
- **Secondary analysis (not used for the decision).** A design-weighted recall = matched ÷ (observed key slips + estimated unsampled slips).
    - **Two sources of uncertainty, reported separately.**
        1. *Design (sampling) uncertainty within a lesson.* Let:
              - C = slips found in the candidate census;
              - S = slips found in the n sampled other turns;
              - the observed key K = C + S;
              - the estimated full total T = C + (N/n)·S.

       Then:

              - C is fixed. S, and therefore K and T, vary with the sample.
              - Var(T) is estimated by (1 − n/N) · N² · s²/n, where s² is the sample variance of slips per sampled turn. This is zero when n = N, and when N = 0 (then T = C).
              - **The matched count m is fixed under sampling.** This holds by construction.
                  - The census stratum is built from the full 15-s matching window of **every evaluated prediction**, including the production reader's flags. It is not built only from the pooled candidates.
                  - Slips outside the census therefore have no prediction that could match them, and m does not depend on the sample.
              - Design-weighted recall = m / T. By the delta method, Var(m/T) ≈ m² · Var(T) / T⁴. The 95% interval is m/T ± 1.96·SE, truncated to [0, 1].
        2. *Between-lesson uncertainty.* A bootstrap over the three lessons, with each lesson's T held at its estimate.
    - **Reporting.** Both intervals are reported. Neither is combined into a single claim of coverage.
- **Power.** No metric-specific power calculation exists. An inconclusive outcome is likely unless the true difference is large.

### H2: pooled review plus random audit finds the tutor-confirmed slips absent from the student's own key

| Element | Specification |
|---|---|
| the student's key | Step 2b: before seeing any candidate, the student keys each test lesson alone; his key is frozen with a hash |
| Measure | Share of the tutor-adjudicated slips absent from the student's frozen key. Reported in two parts: (a) found among pooled candidates; (b) found by the random audit of other turns. 95% intervals by cluster bootstrap (lessons, then turns) |
| Discovery | Lower bound above 0: the pooled, the tutor-adjudicated key contains slips absent from the student's key |
| Practical size | Lower bound above 10%: at least one slip in ten |
| Not claimed | That pooling *causes* better keys than a single reviewer. The procedure and the adjudicator both differ (the student keys; the tutor adjudicates). A causal claim would need a comparable condition, such as the tutor also keying one lesson alone |
| Scope | Pool-relative; calibration limited by three lessons |

### H3: method A hides at most 5% of confirmed slips

| Element | Specification |
|---|---|
| Measure | FCR, the share of key slips whose wrong form is replaced by the tutor's correct form in the transcript |
| Interval | 95% interval by cluster bootstrap (lessons, then turns) |
| Supported if | The upper bound is at most 5% |
| Rejected if | The lower bound is above 5% |
| Inconclusive | Otherwise, **including when no hidden slip is observed**: a cluster bootstrap cannot give a useful upper bound from zero events, and an independent-binomial bound would ignore the clustering |
| Sample | Fixed in advance: the same three locked lessons as H1. No extension is made based on the outcome |
| Zero events | Final result "inconclusive", reported with the number of slips judged and the descriptive one-sided exact bound under an explicit independence assumption, labelled as such |

### H4 (exploratory): Gemini 4 Argon via `agy` hears the student at least as well as Gemini 3.8 Flash in method A

| Element | Specification |
|---|---|
| Access | Subscription; no additional API charge recorded |
| Data | Frozen re-listen inputs for 10-09 and 10-10. These lessons are reused, so the comparison is exploratory |
| Comparison | Three listens each, the same vote |
| Measures | Hit rate and FCR, with a line-level bootstrap |
| Batching | Argon is sent 8 lines per call because of quota. This difference is reported |
| If promising | A confirmatory test on the next three graded lessons. Non-inferiority margin: hit rate −1 point; FCR must not rise above A's upper bound |

### Procedure

1. **Lock** the test lessons before any rule or prompt changes, and freeze their pages.
2. **Pool candidates.**
      - Run every plan-route reader and judge: Opus, Sonnet, Fable, GPT-6 Astra, GPT-5.6 Terra, Gemini 4 Argon, Gemini 3.8 Flash.
      - Store the candidate-list hash with every verdict file.
      - **Candidate matcher.**
          - **Tokens.** Each flag's tokens are the Arabic-script tokens of its "wrong" field (his words), split on whitespace and punctuation, normalised as in Section 4.3. Arabizi is converted to Arabic script with the project's `latin_to_arabic` first. A flag with no tokens matches on time only.
          - **Order.** Flags are sorted by time, then by reader name, then by the reader's own row order.
          - **Clustering.** A flag joins the earliest open cluster whose *first* flag is within 15 s and shares at least one token with it; otherwise it starts a new cluster. Chaining is not transitive: membership is tested only against the first flag.
          - **Representative.** A cluster's time and words are those of its first flag.
          - **Family label.** Ignored for clustering.
          - **⚑ Pre-registration to-do.** Both matchers are drafts. Before registration they must be run on the three keyed lessons of this study, and the clusters and assignments that differ from the adjudicated keys listed with examples. Section 8 cannot be registered until this is done.

   2b. **the student's own key first.** For each test lesson, the student reviews it alone before seeing any candidate list. His key is frozen with a hash.

3. **Adjudicate blind.**
      - **Who.** the tutor marks each candidate; for H2 lessons only the tutor adjudicates.
      - **Choices.** Mistake / not / wrong words / can't tell, with a reason. She never sees which AI proposed a candidate.
      - **Population.** Every student turn containing Arabic, in two strata:
          - *Candidate stratum.* Every turn within 15 s of a candidate is reviewed fully, as a census. She also counts any other corrected mistakes in the turn.
          - *Other turns.* A uniform random sample without replacement of n = min(30, N) of the N such turns per lesson (seed recorded; no sample if N = 0). Each sampled turn is reviewed fully. Inclusion probability is n/N.
      - **Estimate.**
          - She records the number of corrected slips in each sampled turn. Slips found in sampled turns enter the key directly.
          - Slips in the N − n unsampled turns are estimated as (N/n − 1) × the sampled total. The finite-population correction belongs to the variance only, not to this estimate.
          - Sampled and estimated totals are reported separately.
4. **Score matcher.**
      - **Match condition.** A prediction matches a key slip when they are within 15 s and share a normalised token, comparing the prediction's "wrong" field with the key's "said" field.
      - **Assignment.** One to one, nearest time first. Ties go to the earlier key slip, then to the earlier prediction.
      - **Attempts.** the tutor may split a candidate into separate *attempts* if it bundles more than one thing the student said. Each attempt gets a stable ID and the subset of flags she assigns to it. Unassigned flags go to the earliest attempt.
      - **Rulings are per attempt.** A judge's prediction for the candidate counts as one prediction. It matches at most one attempt that is a slip: the nearest in time, ties broken by attempt ID.
      - **Can't tell.**
          - An attempt ruled "can't tell" is removed from the key.
          - A prediction is removed only if *every* attempt of its candidate is "can't tell". Otherwise it is scored against the resolved attempts.
          - Proximity alone never removes a prediction.
      - **Tokenless flags and predictions** match on time only, in both matchers.
      - **Final ties** at identical times are broken by stable IDs: reader name + row index for flags, attempt ID for key entries.
      - **Family labels.** Scored separately, as label accuracy.
      - **Validation.** Run on the same three keyed lessons, reporting every pair this matcher decides differently from the family-and-time matcher.
5. **Score once** on the locked lessons, using the H1 rule.
6. **Measure the key.** Re-listen blind to 15 random key moments per lesson.
      - Agreement with the first pass measures consistency.
      - Agreement with the designated reference (the tutor's ruling) measures agreement with that reference.
7. **Log** for every row: key version, pool, prompt and transcript hashes, model identifiers and effort, commit, and dollar cost.
8. **Spend.** Plans first. A paid call needs a dollar cap the student has approved.

---

## 9. Limitations

- **Small sample.** Three keyed lessons, 99–119 slips, wide intervals. Interval coverage is not established (Section 4.4).
- **Anchoring.**
    - the student built keys v1 and v2 by reviewing pages that already showed production's text and mistake marks.
    - The fast review mode meant to measure anchoring was never used.
    - Anchoring could favour production on keys v1 and v2. Its direction and size for the comparison are not identified: slips only a judge found would lower the judges' recorded precision, while production-shaped keys raise production's recall.
- **Narrow setting.** One student, one tutor, one dialect.
- **Ideal transcripts.** Reader and judge scores use corrected (key) transcripts.
- **Mismatched instruments.**
    - The matcher is lenient on wording and strict on labels.
    - The judge definition (DEF) differs from the key's rules.
- **Approximate hearing measure.** Hit rate ignores order and insertions.
- **Selection.** Models, prompts and thresholds were chosen with the same three lessons.
- **Self-audit.**
    - Much of the record, and the audit summaries [A1–A4], were written by AI agents.
    - The headline judge and production numbers were recomputed from the copied files by `case_study_stats*.py`.
    - Hearing and Phase 1–3 numbers are taken from their logged records, not recomputed.
- **Reproducibility.**
    - Closed models may change. Model identifiers are as reported by the vendor tools on the stated dates.
    - **Standalone replay.** `research/evidence/r90-43fa688/replay.py` uses the Python standard library only. It reads `replay-inputs.json` (candidate lists, production flags, keys v2 and v3) and the 18 judge verdict files, and reproduces the point estimates in Tables 4 and 6 exactly. Its bootstrap intervals match the published ones to within 0.1 point: the implementations draw resamples in a different order.
        - It does not re-run any model.
        - `replay-inputs.json` was exported from R90 at 614c7a2 by the case study. It is the boundary of what can be replayed without the project.
    - **Full rebuild.** Rebuilding those inputs from raw reader runs needs the R90 directory layout. Check out 614c7a2 and run `case_study_stats.py` and `case_study_stats2.py` with `RJ_POOL=opus,sonnet,gemini-gemini-3.7-flash,gemini-gemini-3.1-pro-preview,codex-gpt-5.6-terra,codex-gpt-6-astra` and `RJ_TAG=.planpool`. This also needs the hourly checkout (`C:\dev\anees-hourly`), because `vendor_read.py` adds it to Python's path for `anees_env` and the production `reader_agree`. The full rebuild is not portable.

## Ethics, consent and data availability

- **Who owns the data.**
    - The recordings, transcripts and keys belong to the student, the project owner and an author of the decisions studied here.
    - the tutor agreed to the app's processing of the lessons, relayed by the student on 2026-09-05 ("she says yes to all of this") [E49]. That is processing consent, not publication consent.
    - **Publication consent: not yet obtained (2026-10-19).**
        - This master record is private and unpublished.
        - A shareable version with every lesson excerpt withheld and names replaced by roles is `research/case-study.public.md`, generated by `research/make_public.py`.
        - Only that version may be shared until the tutor's written consent is recorded here, with its date.
- **Shared versions.**
    - Shared versions replace names with roles and leave out personal content.
    - **The app already publishes lessons.** the student chose to make the app's lesson pages, audio and transcripts public (PR-02: "lesson audio and transcripts are public by choice") [E50].
    - **What a shared version would add.** No additional full recordings or transcripts. Its quoted lesson excerpts would themselves be a new disclosure, so they need the tutor's publication consent. Voices are identifiable, so removing names alone would not anonymise the recordings.
- **Availability.**
    - Code and aggregate results are in the project repository.
    - The paper's evidence folder holds no audio. Lesson audio and transcripts remain where the app already publishes them.

---

## 10. Conclusion

- **Hearing.** The largest measured gain came from an AI second listen with lesson context: approximate word coverage of 94–95% on two lessons, with a guard against hiding the learner's mistakes.
- **Mistake finding.** On key v2, the compared judge setups gained precision and lost recall against the production reader. On key v3, the Argon panel improved both. Which panel is best depends on the key:
    - On the earlier key, no setup was distinguishable from production once the comparisons were corrected for. Production kept the higher recall.
    - Opus + Argon led only after its own findings, and a lower threshold, entered.
- **The key.** Against the final adjudicated key, the student's review and each evaluated model each missed recorded slips. The key itself is incomplete.
- **Next step.** The study ends with a *draft* decision policy, pending validation of its matcher: pooled blind adjudication, locked test lessons, paired intervals and a spend rule.

---

## References (external)

- **[R1]** Lyster, R., & Ranta, L. (1997). Corrective feedback and learner uptake: Negotiation of form in communicative classrooms. *Studies in Second Language Acquisition*, 19(1), 37–66.
- **[R2]** Dahlmeier, D., & Ng, H. T. (2012). Better evaluation for grammatical error correction. *Proceedings of NAACL-HLT 2012*, 568–572.
- **[R3]** Ng, H. T., Wu, S. M., Briscoe, T., Hadiwinoto, C., Susanto, R. H., & Bryant, C. (2014). The CoNLL-2014 shared task on grammatical error correction. *Proceedings of CoNLL 2014: Shared Task*, 1–14.
- **[R4]** Bryant, C., Felice, M., & Briscoe, T. (2017). Automatic annotation and evaluation of error types for grammatical error correction. *Proceedings of ACL 2017*, 793–805.
- **[R5]** Nicholls, D. (2003). The Cambridge Learner Corpus: Error coding and analysis for lexicography and ELT. *Proceedings of Corpus Linguistics 2003*, 572–581.
- **[R6]** Ali, A., Vogel, S., & Renals, S. (2017). Speech recognition challenge in the wild: Arabic MGB-3. *IEEE ASRU 2017*, 316–322. arXiv:1709.07276.
- **[R7]** Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust speech recognition via large-scale weak supervision. *Proceedings of ICML 2023*.
- **[R8]** Fiscus, J. G. (1997). A post-processing system to yield reduced word error rates: Recognizer output voting error reduction (ROVER). *IEEE ASRU 1997*, 347–354.
- **[R9]** Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. *NeurIPS 2023 Datasets and Benchmarks*.
- **[R10]** Verga, P., Hofstätter, S., Althammer, S., et al. (2024). Replacing judges with juries: Evaluating LLM generations with a panel of diverse models. arXiv:2404.18796.
- **[R11]** Wang, X., Wei, J., Schuurmans, D., et al. (2023). Self-consistency improves chain of thought reasoning in language models. *ICLR 2023*.
- **[R12]** Voorhees, E. M., & Harman, D. K. (Eds.) (2005). *TREC: Experiment and Evaluation in Information Retrieval*. MIT Press.
- **[R13]** Zobel, J. (1998). How reliable are the results of large-scale information retrieval experiments? *Proceedings of ACM SIGIR 1998*, 307–314.
- **[R14]** Buckley, C., & Voorhees, E. M. (2004). Retrieval evaluation with incomplete information. *Proceedings of ACM SIGIR 2004*, 25–32.
- **[R15]** Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research*, 11, 2079–2107.
- **[R16]** Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns*, 4(9), 100804.
- **[R17]** McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153–157.
- **[R18]** Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, 20(1), 37–46.
- **[R19]** Artstein, R., & Poesio, M. (2008). Inter-coder agreement for computational linguistics. *Computational Linguistics*, 34(4), 555–596.
- **[R20]** Google (2026). Headless mode — Antigravity CLI documentation. https://antigravity.google/docs/cli/headless/ (accessed 2026-10-18).
- **[R21]** Google for Developers Blog (2026). An important update: transitioning Gemini CLI to Antigravity CLI. https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/ (accessed 2026-10-18).

## Appendix A. Evidence index

**Abbreviations.**

- **EV** = `research/evidence/r90-43fa688/`: copies of the test-branch files at 43fa688, plus the statistics of review rounds 2–4 and the final key v3 from 614c7a2 (production gate imported from hourly 91b922d).
- **TXE** = `research/sources/tx-excerpts.json`: quoted chat messages and tool output, with UTC timestamps.
- **Registry** = `rules/registry.json`.

| ID | Evidence |
|---|---|
| E1 | Registry TR-01/TR-02 (session b4922477, 2026-09-04); commit 06676ef |
| E2 | `docs/data/lessons/*.json` (24 files) |
| E3 | Commits e9abb14, 67bce16; `plan/AUDIT-STREAMLINE-2026-09-05.md` line 9 |
| E4 | `research/sources/medi-messages.jsonl`, 2026-09-05T18:36:39Z ("I take my lessons from my phone right now"); commit d5b65a9 |
| E5 | `plan/PIPELINE-TEST-PROTOCOL.md` (a0e3ad8); `data/lesson-work/review-grades/` |
| E6 | Commit 2425a70 (keys frozen) |
| E7 | Registry AM-33; commit ebc8b4c (key v2) |
| E8 | R90 377194e; TXE 2026-10-19T05:07:46Z ("All these NEW: not in your key are correct....") |
| E9 | R90 68ede84, 984b474; `key_versions` in EV `2026-10-08.json`, `2026-10-09.json`, `2026-10-10.json` |
| E10 | `plan/ACCURACY-METHOD.md` (6c901f1) |
| E11 | Registry PR-25; commits ad12f74, a13bce3; `scripts/review_lesson.py` READER_MODELS |
| E12 | `scripts/rehear_job.py` (MODEL gemini-3.8-flash); `scripts/ingest_tracks.py` (scribe_v2) |
| E13 | Commit 3dc6977; `plan/blueprint.md` lines 110–153; `plan/constants.md` line 38; commit aa775c1 |
| E14 | Commit 4c4de4d; `data/aug25/check02_results_amal.json` (raw votes, family totals); `check02_scoring.md` |
| E15 | Commits f80041a…67b786b, 932f86f; `handoff/codex-takeover-2026-09-07/05-*.md` |
| E16 | Commit 5000b07 |
| E17 | Commit 5aed7ff; `plan/PROCESS-AUDIT-2026-09-26.md` |
| E18 | Commit 5fcbe1e; `plan/ENGINE-BENCHMARK-2026-10-02.md` |
| E19 | Commit bdafbe0; `plan/GEMINI-BACKFILL-RESULTS-2026-10-05.md` |
| E20 | `data/lesson-work/rehear/amal-lines-decision.json` |
| E21 | Commit 0d093df; registry PG-46 |
| E22 | `plan/PIPELINE-TEST-PROTOCOL.md` §§1–7; registry PR-23 (status "written") |
| E23 | `docs/data/review-grades.json` → `experiments[0]` (hit rate, FCR, sign tests, per-cell cost); `data/lesson-work/harness/spend.json` (`spent_usd` 5.1008); `plan/PIPELINE-TEST-PROTOCOL.md` §7 row 3; `scripts/hearing_harness.py` `_match_words`; `scripts/word_coverage.py` `core`, `similar` |
| E24 | Commit b8b9fd8 (`runs/2026-10-0*.debate-*.json`); registry PR-25 |
| E25 | R90 `overnight-2026-10-17/fair-run.log` (`credit_balance_exhausted`); TXE 2026-10-18T08:07–08:10Z |
| E26 | EV `reader_judge.py` (`DEF`, `prompt`, `candidates`, `p_slip`, `score`); EV `judge/*.plain.planpool.json`; EV `attempts.jsonl` rows 102–162 |
| E27 | EV `attempts.jsonl` (253 rows; 112 unique method strings; 156 method × key); rows 1–101; EV `research-memo.md`; EV `CODEX-FINDINGS.md` |
| E28 | EV `reader_tiers.py` (`transcript` = key text; `MATCH_S = 15.0`; `match`; `prf`); EV `reader_ensemble.py` |
| E29 | `scripts/build_tutor_dispute_check.py`; `data/lesson-work/tutor-dispute-check/` |
| E30 | Registry AM-35; commit a9cee88; `data/lesson-work/tutor-judge-check/moments.json` |
| E31 | Commits c80cc21, 9d21143, ff95465; `plan/PROCESS-AUDIT-2026-09-26.md` |
| E32 | Commits 6571654, ab1d1d6, 66943e6 |
| E33 | Commits da397ac, 68912ef |
| E34 | Registry TR-27; commit 8eb53ff |
| E35 | TXE 2026-10-19T05:25:09Z (mid-turn message) |
| E36 | Registry PR-25 ("confirm it on the next fully reviewed lesson"); EV `attempts.jsonl` (no rows for 83.5 or 57.2) |
| E37 | Commits e5616ab, ab05143, b19d6a0; `medi-messages.jsonl` 2026-10-11T16:18Z |
| E38 | TXE 2026-10-18T20:12:10Z (tool output with 57.2) |
| E39 | Commits bbe75e6, 91b922d; registry PR-27 |
| E40 | Commit ebc8b4c |
| E41 | `AGENTS.md` rule 7 (782d736) |
| E42 | EV `vendor_read.py` (`call_agy`); R90 ae236bb |
| E43 | `research/sources/medi-messages.jsonl` (coverage by date) |
| E44 | EV `research-memo.md` §7 |
| E45 | EV `case_study_stats.py`, `case_study_stats2.py`, `case-study-stats.v2.json`, `case-study-stats.v3.json`, `case-study-stats2.json`; EV `reader_agree.production-91b922d.py` (production gate as imported) |
| E46 | `research/sources/e46-argon-audio-probe.out.jsonl` (agy `gemini-4-argon-high` transcribing `docs/lessons/2026-10-09/clips/context-c8e82c8550d2d459.mp3` via `view_file`) |
| E47 | `RULES.md` S4 ("Pronunciation is never a missed word") |
| E48 | TXE 2026-10-18T23:18–23:25Z (Gemini CLI sign-in attempts; the rejection is quoted in the session summary: "This client is no longer supported for Gemini Code Assist for individuals") |
| E49 | `research/sources/medi-messages.jsonl`, 2026-09-05T18:31:13Z ("she says yes to all of this") |
| E50 | `AGENTS.md` (PR-02 low security: "lesson audio and transcripts are public by choice") |

**AI-written audit summaries (secondary):** A1 = `research/era-1.md`, A2 = `era-2.md`, A3 = `era-3.md`, A4 = `era-4.md`.

## Appendix B. Reconstructed hypothesis register

| ID | Phase | Hypothesis (reconstructed unless noted) | Result |
|---|---|---|---|
| P1-H1 | 1 | ASR is accurate enough to be the primary error signal (stated in advance) | Never tested |
| P1-H2 | 1 | ASR keeps learner errors as spoken | Contradicted by observation |
| P1-H3/H4 | 1 | A local stack or Speechmatics beats ElevenLabs (rule in advance) | Rejected by blind preference |
| P1-H5/H6 | 1 | Prompting or vocabulary make OpenAI transcription competitive | Rejected |
| P1-H7 | 1 | A text-only tutor-reaction detector finds corrections | Weak (AUC about 0.55) |
| P1-H8 | 1 | Per-speaker tracks remove unlabeled words | Supported for labeling (13.6% → 0% unlabeled); word accuracy not measured |
| P2-H1 | 2 | Rule-based grammar detection reaches 80% recall (gate in advance) | Overfit: 45% held-out, 11% in use |
| P2-H3 | 2 | Two AI readers converge to 95% overlap | Refuted (61.5% Jaccard) |
| P2-H7 | 2 | An audio LLM with context hears the student better | Supported on one lesson (53 vs 4 of 63) |
| P2-H13 | 2 | The student's corrections are ground truth | Partly refuted (2 of 4 wrong) |
| P2-H14 | 2 | The second listen does not erase real mistakes | Refuted at scale (12 of 27) |
| P3-H4 | 3 | Another hearing cell beats A (protocol, in advance) | Not supported (F damaged; B placement-penalised) |
| P3-H5 | 3 | Two agreeing readers beat one | In-sample win of 4.6 points |
| P4-H1 | 4 | Another vendor's reader beats Claude | Not supported (top four within 1.2 points) |
| P4-H5 | 4 | Union-then-judge beats voting | Small lead, within uncertainty |
| P4-H10 | 4 | A council or debate settles borderline flags | Not supported |
| P4-H16 | 4 | Gemini 4 Argon is a better judge | Highest recall among precise judges on v2; leads on v3 (circular, re-tuned) |
| P4-H18 | 4 | Argon's "false positives" are missed key slips | 20 net confirmed (not blind) |
| P4-H19 | 4 | The production reader under-counts | Yes: it missed 26 of 99 slips on v2 (fewer misses than the compared judges) and 39 of 119 on v3 |
| P4-H20 | 4 | Pooled blind review gives a fairer key | Open (AM-35 pending) |
| P4-H21 | 4 | Gemini 4 Argon hears the student better than Gemini 3.8 Flash (exploratory H4) | Refuted: 84.0 vs 91.2% and 79.1 vs 89.7% hit rate (p < 0.001) |

## Appendix C. Configuration of the headline methods

| Item | Value |
|---|---|
| Judges | `claude-opus-5-5` (`claude -p`, default effort, tools disallowed); `gpt-6-astra` (`codex exec`, read-only sandbox, default reasoning, ChatGPT plan); `gemini-4-argon-high` (`agy`, high effort, file viewer available, Google AI Pro plan) |
| Prompt | `reader_judge.prompt(d, 'plain')`: system = instructions + `DEF` + `buckets.md`; user = candidates + key transcript. System prompt sha256/16 = d410e0e3057efe47 (all lessons) |
| User prompt hash | 10-08 509284274535b182; 10-09 73aed4381a050eb2; 10-10 23605d764ba14f78 |
| Note | Every hash in this table, including the prompt hashes above, was computed afterwards by `case_study_stats2.py` from the pinned files. They are reconstructed, not logged at run time |
| Candidate lists | 10-08 a4d16f99984531f8 (53); 10-09 7f347d285f87144d (64); 10-10 0f09319b9dc504c0 (40) |
| Key transcripts | 10-08 7503966b6db0350e; 10-09 69e435f7824ea1e4; 10-10 1bd3d1b105d6027f |
| Repetitions | 1 verdict file per judge per lesson (EV `judge/`) |
| Score | Verbal confidence → uncalibrated slip score; panel = mean or min |
| Threshold | Grid 0.10–0.95, step 0.05, F0.5 on the other two lessons. Opus + Argon: 0.80/0.80/0.75 (v2), 0.60/0.60/0.40 (v3). Opus + Astra mean: 0.80 ×3 (v2), 0.35/0.40/0.40 (v3) |
| Missing verdict | Score 0 |
| Matching | Same family, ≤15 s, one-to-one, nearest first |
| Production reader | `reader_agree.gate` (both, same family, ≤15 s) + `signal_gate` (PR-27; production code at hourly 91b922d) on one Opus and one Sonnet read of the key transcript. Main comparator = slip output ("asked" marks removed) |

## Appendix D. Response to review

| Round | Main objections | What changed |
|---|---|---|
| 1 | Argon headline circular; counts wrong; no intervals; hearing caveats missing | Headline moved to the pre-Argon key; bootstrap and McNemar added; the student's count 97, not 99; F and B damage disclosed; MGB-3 and PoLL claims narrowed |
| 2 | Prompt provenance (DEF vs DEF_V2); key v2 not independent; key change mixed with re-tuning; H1 threshold invented | Fixed-threshold table (Table 6); paired ΔF0.5; v2 described as AI-influenced; input hashes; mid-turn quotes archived |
| 3 | Production charged for "asked" marks; Bonferroni and H3 rules; sampling estimand; consent statement | Slip-output comparator; Bonferroni intervals and recall floor; Horvitz–Thompson estimate; ethics section; 6th duplicate found later |
| 4 | Duplicate at 10-10 13:52; threshold premise; tokenisation; billing language | Key 120 → 119; key v4 adjudicated by one blind process; normalisation documented |
| 5 | Replay not standalone; H2 needs the student's own key; council used DEF_V2 | `replay.py` (standard library only) reproduces Tables 4 and 6; step 2b; council row annotated |
| 6 | Precision non-inferiority; zero-event H3; tokenisation path; anchoring direction; consent status | Joint Bonferroni over 6 intervals with precision bound; H3 zero-event result is inconclusive; exam-key tokenisation documented; anchoring direction left unidentified; publication consent marked "not yet obtained" |
| 7 | Unconditional joint-coverage claim; H3 outcome-dependent extension; matcher spec; weighted-recall algorithm | Section 8 recast as a decision policy without coverage guarantees; H3 fixed sample; matcher and bootstrap specified (matcher validation pending); transcript context for examples |
| 8 | FPC misplaced; matcher ties and "can't tell" removal; full question-form exchange; H2 causal wording; key v3 bias wording | FPC moved to variance; design vs between-lesson uncertainty separated; flag-ID-based removal; full exchange quoted; H2 narrowed; "may favour" |
| 9 | Variance derived around the wrong total; cluster-level "can't tell" removal; no excerpt-free version | Variance rewritten around T = C + (N/n)S with a fixed matched count; attempt-level IDs; matcher marked as an unfinished draft; `case-study.public.md` generated |
| 10 | Abstract too long; v2 headline not corrected for comparisons; "lower bound" wording; no reliability statistic; contested example; census invariant; ordering | Abstract ~250 words; Bonferroni-5 interval (no v2 configuration distinguishable); 20 slips described as unblinded confirmations; reliability gap stated; binqlaq marked contested; census defined from every prediction's window; appendices ordered |

**Independent arithmetic check (Codex, round 6).** Six headline F0.5 values were recomputed from the archived counts and matched:

- key v2: production 73.7, Opus + Astra 83.1, Opus + Argon 79.0;
- key v3: production 77.7, Opus + Astra 83.2, Opus + Argon 88.7.

The same reviewer also reproduced:

- the log counts: 253 rows, 112 method strings and 156 method/key-size combinations;
- the hearing values: A 95.0 / 94.1, ElevenLabs 69.4 / 60.7, and E1 on 10-10 at p = 0.0784.

These checks verify the arithmetic. They do not verify how the archived inputs were produced.
