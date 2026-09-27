# Tag the unknown key word first

**Bottom line:** the best-supported extra tag is not a grammar tag. It is **"is a word the learner needs for the meaning unknown?"**, tracked with an unknown-word count and a known-word share. Next come **audio trouble** (overlap, low ASR confidence), **pause structure** kept apart from speech rate, **a repeat count** (instead of a second-hearing yes/no), and **whether the word was learned by ear**. Of the planned tags, second hearing, typed in chat, word-bank status, topic novelty and speech rate have real evidence. Negation and question vs statement have small but replicated effects. Tense, non-first-person, noun share and derived verb forms have **no listening evidence** and should be treated as experiments. Almost every Arabic-specific tag is a hypothesis: no peer-reviewed study measures sentence-level L2 listening in Levantine Arabic, so your own data would be new evidence. **Spoken production:** the notes found no sentence-level production studies, so any production tags are untested guesses.

**Strength key:** **Strong** = meta-analysis or several replications · **Moderate** = a few consistent studies or one large item study · **Weak** = a single small study, an analogy from another language, or mixed results · **None** = no study found.

---

## 1. Planned tags: 6 supported, 3 with no evidence at all

| Planned tag | Verdict | Evidence (study · N · effect) | Change to make |
|---|---|---|---|
| Second hearing | ✅ **Strong** | Two hearings beat one and lowered anxiety ([Holzknecht & Harding 2024](https://onlinelibrary.wiley.com/doi/full/10.1002/tesq.3249), N=306). Repetition was the 2nd-best support ([Chang & Read 2006](https://eric.ed.gov/?id=EJ753072), N=160) | Make it a **count** (`repeat_index` 1, 2, 3…) |
| Also typed in chat | ✅ **Strong** (as a confound) | Captions vs none: **g = 0.99**, 18 studies ([Montero Pérez et al. 2013](https://www.sciencedirect.com/science/article/abs/pii/S0346251X13001012)) | Analyse "by ear" and "with text" **separately**, or text will inflate your listening score |
| Word-bank status | ✅ **Strong** | Vocabulary–listening **r = .56**, >100 studies ([meta-analysis](https://eric.ed.gov/?id=EJ1342379)) | Add a per-sentence rollup (see new tag #1) |
| Topic novelty | ✅ **Moderate–strong** | Topic info was the most effective support ([Chang & Read 2006](https://eric.ed.gov/?id=EJ753072)). Topic knowledge had a direct effect ([Wallace](https://onlinelibrary.wiley.com/doi/10.1111/lang.12424), N=226). Familiar topics were easier at every level ([Schmidt-Rinehart 1994](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-4781.1994.tb02030.x)) | Add `turns_since_topic_shift`: the riskiest moment is just after a shift |
| Speech rate | ✅ **Moderate**, but split it | Low-intermediate learners did better at 100–150 wpm than at 200 wpm ([Griffiths 1990](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-1770.1990.tb00666.x)). **Slowing the speech mechanically did not help**; pauses did ([Blau 1991](https://files.eric.ed.gov/fulltext/ED340234.pdf)) | Split into **articulation rate** and **pause structure** (new tag #3) |
| Sentence length | ✅ **Moderate** | One of the top predictors in a machine-learning model of 225 test items ([Cai et al. 2025](https://academic.oup.com/applij/advance-article/doi/10.1093/applin/amaf079/8341053)). Partly just a stand-in for how much information is packed in | Also log **syllables** and **seconds** and let the data choose |
| Negation | 🟡 **Moderate, small** | 2+ negatives made items harder: **r = .125**, replicated across 3 TOEFL studies ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)). No Arabic study of ما…ش | Record the subtype: ما…ش / مش / ما alone |
| Question vs statement | 🟡 **Moderate, small** | Questions easier (**r = −.147**), statements harder (**r = .104**) ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)) | Split questions into yes/no and wh-. A yes/no question invites an "aywa" that can hide non-understanding |
| Minute of lesson | 🟡 **Moderate** (lecture studies, first-language listeners) | Self-rated attention fell from 6.0 to 4.9 out of 7 over a 40-minute lecture ([Farley et al. 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3776418/), N=21) | Add `minutes_since_break`. ADHD shows up as more random lapses, not a steeper decline ([Tucha 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5281679/)) |
| FSRS retrievability | 🟡 **Indirect** | No study links flashcard recall to catching the word in fast speech | Treat it as an **upper bound**. Use `min_R` and the number of words with R < 0.7 |
| Days since last exposure | 🟡 **Weak / redundant** | The spacing meta-analysis is about learning a word, not recognising it in the moment ([Kim & Webb 2022](https://onlinelibrary.wiley.com/doi/abs/10.1111/lang.12479), 48 experiments) | FSRS retrievability already includes elapsed time. Expect the two to overlap heavily |
| Attached-suffix count (حكيتلك) | 🟠 **Weak** | Learners do split Arabic words into root and pattern, but only priming studies show it, not listening ([Freynik et al. 2017](https://benjamins.com/catalog/ml.12.1.02fre)) | Count **enclitics per word** (0/1/2+) and include ‑ش and the ب‑/عم prefixes |
| Farsi cognates | 🟠 **Weak** | Hearing a cognate helped low-proficiency listeners but not high-proficiency ones ([Penn State](https://pure.psu.edu/en/publications/cognate-facilitation-effect-during-auditory-comprehension-of-a-se/)). No Farsi→Arabic study exists | Split into subtypes (new tag #8) |
| Derived verb forms | 🟠 **Direction unknown** | Learners split words into root + pattern ([Freynik 2017](https://benjamins.com/catalog/ml.12.1.02fre)), so a new form of a known root may be *easy* | Add a sub-flag: **known root / new root** |
| Time of day | 🔴 **Weak on its own** | Adults 18–45 did better at their preferred time of day in only **29 of 64 studies (45%)** ([Chauhan et al. 2025](https://bura.brunel.ac.uk/handle/2438/31067)) | Only meaningful alongside a one-time **chronotype** questionnaire (MEQ) |
| Tense | ⚪ **None** | No L2 Arabic listening study | Keep: it's cheap and exploratory |
| Non-first-person forms | ⚪ **None** | No study | Keep: it's cheap and exploratory |
| Noun share | ⚪ **None** (direct) | Function words are recognised worse than content words, robustly across L1s and levels ([Field 2008](https://eric.ed.gov/?id=EJ818261)) | Flip it: **function-word/clitic share** is the harder side. Noun share will also overlap with Farsi cognates, since Persian borrowed mostly nouns and adjectives |

---

## 2. New tags ranked: vocabulary and audio lead

### Tier 1: add now (best evidence, easy to compute)

| # | Tag | What to measure | How to auto-compute | Evidence (study · N · effect) | Strength |
|---|---|---|---|---|---|
| 1 | **Unknown key word** | Unknown content words (0/1/2+), known-word share, and whether the unknown word is the main verb, the question word or the word needed to answer | Lemmatise with CAMeL LEV, then look each lemma up in the word bank. "Key" = main predicate or question word, from part-of-speech tags | Coverage 90%→95%→98%→100% gave scores of **7.35→7.65→8.22→9.62 out of 10** ([van Zeeland & Schmitt 2013](https://academic.oup.com/applij/article-abstract/34/4/457/199564)). A rare word merely present: r = .059 (no effect). A rare word **needed to answer**: **r = .200** ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf), 365 items) | **Strong** |
| 2 | **Audio trouble** | Overlap between speakers (ms), lowest ASR word confidence, inaudible or garbled tokens | Overlapping word timestamps, ASR confidence scores, and mismatch with the chat text | The non-native disadvantage was **11 points in quiet, 29 points at −4 dB** signal-to-noise. Competing speech hurts L2 listeners more ([Lecumberri et al. 2010](https://www.sciencedirect.com/science/article/abs/pii/S0167639310001482)) | **Strong** direction, **none** for video calls |
| 3 | **Pause structure** | Pauses ≥250 ms, share of pauses at phrase boundaries, mean words between pauses | Gaps between word timings. Phrase boundaries come from the parser or punctuation | Pauses beat normal speech, **t(57) = 3.03**, and mechanical slowing "not a useful modification" ([Blau 1991](https://files.eric.ed.gov/fulltext/ED340234.pdf), N=61) | **Moderate** (old studies, small samples) |
| 4 | **Repeat count + in-lesson word recency** | `repeat_index`; times each word was heard this lesson; seconds since last heard | Fuzzy-match against earlier tutor turns (edit distance < 0.3); word counts within the lesson | Repeat evidence as above ([Holzknecht & Harding 2024](https://onlinelibrary.wiley.com/doi/full/10.1002/tesq.3249)). Word priming within a lesson: **no direct study** | **Strong** / **Weak** |
| 5 | **Known by ear** | Share of the sentence's words that have an audio→meaning or form-recall card | Card type from the flashcard log | Form recall correlates most with listening ([meta-analysis](https://eric.ed.gov/?id=EJ1342379)). Recognising words in speech explained **R² = .54** of listening scores ([Matthews & Cheng 2015](https://www.sciencedirect.com/science/article/abs/pii/S0346251X1500069X), N=167) | **Moderate** |
| 6 | **Idiom or fixed phrase** | Contains a set phrase whose meaning isn't the sum of its words | Phrase list, grown from n-grams that recur in the tutor transcripts | Needing to understand an idiom made items harder: **r = .245** ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)) | **Moderate** (one study) |
| 7 | **Colloquial-only words** | Count of dialect-only function words (شو، ليش، وين، هلّأ، بدّ، عم، مش، كمان، هيك، لسّا) and share of content words with no MSA cognate | A hand-made list of about 50 words, plus the MSA-gloss field in [Maknuune](https://arxiv.org/abs/2210.12985) | Learners' MSA listening ability predicted how well they understood dialects ([Trentman 2011](https://escholarship.org/uc/item/6qx1381h)). Your Farsi-loan Arabic is MSA-shaped, so it won't cover these words | **Weak** (learner-level only) |
| 8 | **Farsi-cognate subtype** | Transparent / sound-disguised (ق→ء, emphatics that merge in Persian) / false friend / verb known only through a Persian noun | Arabic-lemma × Persian-loan list (you would have to build it; none exists), plus a ق flag | About 37 loan pairs changed meaning in Persian (A'lam, via [Hashemi et al. 2014](https://ijhss.thebrpi.org/journals/Vol_4_No_6_1_April_2014/23.pdf)). Persian merges several pharyngeal and emphatic sounds ([Hashemi et al. 2014](https://ijhss.thebrpi.org/journals/Vol_4_No_6_1_April_2014/23.pdf)) | **Weak** |

### Tier 2: cheap experiments (small or indirect evidence)

| # | Tag | How to auto-compute | Evidence | Strength |
|---|---|---|---|---|
| 9 | **Key info at the end** of the sentence | Is the key word in the last clause? | Answer overlapping the last clause: **r = −.207**. Last overlapping word in the key: **r = −.326**, the strongest single predictor ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)) | Moderate–weak |
| 10 | **Said twice within the sentence** | The same content lemma appears twice | Two separate cues to the answer made items easier: **r = −.291** ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)) | Moderate–weak |
| 11 | **Paraphrase vs exact repeat** | Embedding similarity high but word overlap low | Paraphrase helped **only high-proficiency** learners ([Chiang & Dunkel 1992](https://onlinelibrary.wiley.com/doi/abs/10.2307/3587009)). At A2 expect little or no gain | Weak / mixed |
| 12 | **English inside the tutor's sentence** | Latin-script or English tokens. Separate a whole English clause from a single English word | Teacher switching to the L1 gave a short-term gain that faded ([Tian & Macaro 2012](https://eric.ed.gov/?id=EJ973565), N=80) | Weak (mainly a confound) |
| 13 | **Connected-speech blur** | Rules: ال before a sun letter; ال after a vowel; words whose spoken duration is much shorter than usual | Reduced forms hurt learners but not native speakers ([Henrichsen 1984](https://eric.ed.gov/?id=EJ306901)) | Moderate direction, size unknown |
| 14 | **Emphatic/pharyngeal density** | Count of ص ض ط ظ ح ع ق غ خ | Emphatics are the hardest Arabic sounds for L2 learners, and worse at the end of a word ([Heliyon 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC9932739/); [Wisconsin](https://minds.wisconsin.edu/handle/1793/93500)) | Weak |
| 15 | **Needs inference** | LLM label: is the meaning implied rather than stated? | **r = .158** ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)) | Weak |

### Tier 3: session covariates (log once per lesson or per minute)

| Tag | Evidence | Strength |
|---|---|---|
| `minutes_since_break` + breakdowns in the last 5 min | Attention falls and mind-wandering rises with time on task ([Risko et al. 2012](https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1814)) | Weak–moderate |
| Anxiety self-rating 1–5 at the start of the lesson | Listening anxiety **r = −.46** ([Teimouri et al. 2019](https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/second-language-anxiety-and-achievement/B140169CF7C0BB6F5CE7BB0D1F9CDFA0)). But test anxiety had **no effect** in [In'nami 2006](https://eric.ed.gov/?id=EJ800636&pg=1553&q=e-learning) | Weak–moderate |
| Cumulative minutes with this tutor | Listeners adapt to a specific speaker ([Bradlow & Bent 2008](https://pubmed.ncbi.nlm.nih.gov/17532315/); native listeners only) | Weak |
| Tutor camera on | ADHD × visual cues × noise interaction ([Int J Audiology 2014](https://www.tandfonline.com/doi/abs/10.3109/14992027.2013.866282)) | Weak |
| Hours since stimulant dose (if relevant) | No study found. An idea only | None |

**Skip for now:** language-model surprisal (no L2 listening study found), subordinate-clause count (simplifying syntax had **no effect** on listening ([Blau 1991](https://files.eric.ed.gov/fulltext/ED340234.pdf))), broken plurals (no data), and corpus frequency of known words (a text's frequency profile alone showed **small or no** correlation with comprehension ([Webb 2021](https://files.eric.ed.gov/fulltext/EJ1316858.pdf))).

---

## 3. The "understood" label matters more than any tag

- **Minimal replies hide failures.** Classroom learners often let non-understanding pass ("pretend and hope") ([Foster 1998](https://www.researchgate.net/publication/239745192_A_Classroom_Perspective_on_the_Negotiation_of_Meaning)). Some adults don't ([SAGE Open 2014](https://journals.sagepub.com/doi/10.1177/2158244014535941)). Label a lone "aywa/ok" as **unknown**, not understood.
- **Label each tutor sentence 3 ways:** understood (a relevant content reply, or reuses the tutor's words) / breakdown (شو؟, asks for English, a mismatched answer, the tutor rephrases) / unknown ([Varonis & Gass 1985](https://academic.oup.com/applij/article-abstract/6/1/71/171724)).
- **Test your own self-report.** Learners' sense of how much they understood often doesn't match their results ([PMC9986426](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9986426/)). Have the tutor sometimes ask "what did I say about X?" after an "ok". Hand-check about 200 sentences against the LLM's labels.
- **Expect small effects.** All 49 variables together explained about **40%** of difficulty, with single variables at r ≈ .1–.33 ([Kostin 2004](https://files.eric.ed.gov/fulltext/ED492925.pdf)). Use a **mixed-effects logistic model**, not one tag at a time.
- **Overlapping tags:** حكيتلك is clitics + past tense + 1st person all at once, and Farsi cognates overlap with noun share. Only the model can separate them.

---

## 4. Where the evidence runs out

| Gap | What it means for you |
|---|---|
| **No Levantine sentence-level L2 listening study** | Every Arabic tag (clitics, ما…ش, derived forms, emphatics) is a hypothesis |
| **Nearly all evidence is English L2, intermediate or advanced** | The 95% coverage target is untested at A2 ([Webb 2021](https://files.eric.ed.gov/fulltext/EJ1316858.pdf)). Calibrate thresholds on your own data |
| **Spoken production: no sentence-level studies retrieved** | Production tags are guesses. The only link found is that form-recall knowledge tracks listening ([meta-analysis](https://eric.ed.gov/?id=EJ1342379)) |
| **ADHD: no L2 listening studies** | Adults with ADHD showed more listening effort but the same scores ([JSLHR 2019](https://pubmed.ncbi.nlm.nih.gov/31747524/), N=39). Model ADHD as more random lapses |
| **Tagger accuracy** | CAMeL Levantine full-feature accuracy is **85.5%**, part of speech **92.7%** ([Camelira](https://arxiv.org/pdf/2211.16807)). Fine for coarse tags, noisy for fine ones |

---

## Conclusion

- **The biggest gains are in measurement, not grammar.** Separate "by ear" from "with text" and store unknown key words as a yes/no flag, not only as a percentage. Also refuse to count "aywa" as understood.
- **For you specifically,** the Farsi-loan bridge carries the MSA form of a word. So colloquial function words and cognates disguised by Palestinian sound changes (قلب → 2alb) are the most likely hidden blockers, even though neither has been tested.
- **Plan on 30–50 lessons** before session-level tags such as minute of lesson or time of day show a reliable signal. At that point your dataset becomes the first real evidence on sentence-level Levantine L2 listening.
