# 03 — Vocabulary Science: How Words Get Learned and Kept
*Written 2026-09-03. [unverified] = from memory; check before quoting.*

### 1. What "knowing a word" means
Nation: nine aspects — **form** (sound, spelling, parts), **meaning** (form-meaning link, concept, associations), **use** (grammar, collocations, register) — each **receptive** (recognise) and **productive** (produce) ([Nation, Routledge Handbook ch. 2](https://www.taylorfrancis.com/chapters/edit/10.4324/9780429291586-2/different-aspects-vocabulary-knowledge-paul-nation)).
**Productive lags receptive.** Laufer 1998: passive vocab grew fastest, controlled-active less, free-active not at all in a year ([Laufer 1998](https://academic.oup.com/applij/article-abstract/19/2/255/316323)). Webb 2008 confirmed in every frequency band ([Webb 2008](https://eric.ed.gov/?id=EJ784734)).

**Status ladder (up only by passing the named test; down after two fails):**

| Level | Name | Test that proves it |
|---|---|---|
| 0 | New | none |
| 1 | Recognised | Flip: hear/see Arabic → give English |
| 2 | Recalled | Type: English → type Arabizi |
| 3 | Spoken | Speak: English cue → say it; ASR/tutor accepts |
| 4 | Used | Speak: produce it inside a sentence answering a real question |
| 5 | Kept | Level-4 passed after ≥30-day gap, no lapses |

### 2. How many exposures
Webb 2007 (N=121): 1/3/7/10 encounters; 10 gave sizeable gains, still short of full knowledge ([Webb 2007](https://academic.oup.com/applij/article-abstract/28/1/46/174744)). Uchihara, Webb & Yanagisawa 2019 meta (26 studies, N=1,918): moderate positive correlation ([link](http://dx.doi.org/10.1111/lang.12343)), r ≈ .34 [unverified]. Nation: incidental ≈ 10-16 spaced meetings [unverified]; deliberate study 1-3.
**Involvement Load** (Laufer & Hulstijn 2001): need + search + evaluation ([link](https://onlinelibrary.wiley.com/doi/abs/10.1111/0023-8333.00164)). **Technique Feature Analysis** (Nation & Webb 2011): retrieval and generation score highest, which is exactly type and speak modes ([Le, Coxhead & Bui](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5431462)).

### 3. Lists vs context
Paired-associate cards work: Nakata 2011 review ([link](https://www.researchgate.net/publication/254217121)); Elgort 2011 card-learned words behaved like native words in priming [abstract unverified]. Smaller sets (~10) beat big sets ([Nakata & Webb 2016](https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/abs/does-studying-vocabulary-in-smaller-sets-increase-learning/E17B75ABAE1300734AF014C363D59FBC)).
Laufer & Shmueli 1997: English glosses retained better; single-sentence matched or beat long text ([link](https://journals.sagepub.com/doi/10.1177/003368829702800106)). → English gloss + one short example sentence.
Keyword mnemonic: fast then forgotten faster ([review](https://www.sciencedirect.com/science/article/abs/pii/S0959475207000357)) → leeches only. Pictures: learners over-estimate learning [Carpenter & Olson 2012, unverified]. **Audio is mandatory** for a spoken-only dialect.

### 4. Spaced-repetition algorithms
Terms: **retrievability** = chance you recall now; **stability** = days until retrievability hits 90%; **lapse** = failed review.
- Leitner: boxes, no time model. Pimsleur 1967: 5 s, 25 s, 2 min, 10 min, 1 h, 5 h, 1 d, 5 d, 25 d, 4 mo, 2 y; good for within-lesson drills ([link](https://artofmemory.com/blog/the-pimsleur-language-method/)).
- SM-2 (Anki classic): ease × interval, one-size-fits-all.
- Half-Life Regression (Duolingo 2016): p = 2^(−Δ/h) on 13M traces ([paper](https://research.duolingo.com/papers/settles.acl16.pdf)); replaced by Birdbrain ([blog](https://blog.duolingo.com/learning-how-to-help-you-learn-introducing-birdbrain/)).
- **FSRS**: on 349.9M reviews / 9,999 users: FSRS-6 RMSE 0.065, FSRS-5 0.074, HLR 0.128, Ebisu 0.163 ([srs-benchmark](https://github.com/open-spaced-repetition/srs-benchmark)); beats SM-2 on 99.6% of collections ([Expertium](https://expertium.github.io/Benchmark.html)).
**Recommendation:** FSRS (ts-fsrs), defaults until ~1,000 reviews, then optimise. **Desired retention 0.90** ([Anki manual](https://docs.ankiweb.net/deck-options.html)). Load ≈ 10 reviews/day per new card/day → **5-8 new items/day ceiling**.

### 5. Optimal gap and successive relearning
Nakata 2015 (N=128): small advantage for expanding gaps; spacing itself is the lever ([link](https://eric.ed.gov/?id=EJ1084789)). Cepeda 2008 (N=1,350): best gap ≈ 20-40% of a 1-week target, 5-10% of a 1-year target → the 10-20% rule ([ERIC](https://eric.ed.gov/?id=ED505660)).
**Successive relearning** (Rawson & Dunlosky): 3 correct recalls in session 1, then 1 correct in each of 3 later spaced sessions ([summary](https://journals.sagepub.com/doi/full/10.1177/09637214221100484)). Session ends when the item is produced, not shown.

### 6. Testing formats
Recognition (flip) → receptive; Arabic→English recall → receptive; **English→Arabic recall → productive, most predictive of speech**; cloze → collocation; oral Q&A → use + pronunciation + fluency.
**Transfer-appropriate processing** (Morris, Bransford & Franks 1977; Lightbown 2008): memory is best when practice matches the test ([TAP](https://en.wikipedia.org/wiki/Transfer-appropriate_processing); [Lightbown](https://www.researchgate.net/publication/292461381)). → **Speak mode must look like class:** Amal's question as Arabic audio, timed spoken answer, no text prompt.

### 7. Frequency and coverage
95% coverage minimum for reading (Laufer 1989), 98% comfortable (Hu & Nation 2000); Nation 2006: 6-7K families for 98% of spoken English ([link](https://www.lextutor.ca/cover/papers/nation_2006.pdf)). Adolphs & Schmitt 2003: 2,000 families ≈ just under 95% of everyday speech ([link](https://academic.oup.com/applij/article-abstract/24/4/425/213596)).
**What to learn next:** rank by (a) spoken-Levantine frequency, (b) appeared in last lesson, (c) tried-and-failed (error log). Two of three → queue first.

### 8. Forgetting and relearning
Murre & Dros 2015 replicated Ebbinghaus; **savings** = relearning is far faster than first learning ([PLOS](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0120644)). Lapses are normal and cheap. **Leech** = 8 lapses (Anki), re-warn every 4 ([manual](https://docs.ankiweb.net/leeches.html)) → rewrite, mnemonic, or drop.

### 9. Error logs and corrective feedback
Lyster & Ranta 1997: recasts most used, least repaired; elicitation best ([ERIC](https://eric.ed.gov/?id=EJ539354)). Lyster & Saito 2010: durable, larger for prompts ([ERIC](https://eric.ed.gov/?id=EJ892626)). Written error logs: students who could explain corrections improved accuracy in new writing ([System 2024](https://www.sciencedirect.com/science/article/abs/pii/S0346251X24001118)). → every correction becomes an item `source=error_log`, retested by speak mode within 48 h.

### 10. Chunks vs single words
Boers et al. 2006 (N=32): chunk-noticing learners rated more fluent by blind judges ([link](https://journals.sagepub.com/doi/10.1191/1362168806lr195oa)). Spoken Arabic is chunk-heavy → chunks are first-class items with audio and a situation cue.

### Design decisions this implies (10)
1. Six statuses 0-5; promotion only by passing the level's test; two fails demote one level.
2. Tests: L1 flip AR→EN, L2 type EN→AR, L3 speak word, L4 speak in sentence to a tutor-style audio question, L5 = L4 after ≥30 days.
3. Scheduler = FSRS, retention 0.90, defaults until 1,000 reviews; log every review.
4. New items: 3 correct productions in session 1; later sessions end at 1 correct.
5. First review ~1 day; first gap never > 20% of target interval.
6. New-item cap 5-8/day; warn when due > 10× new.
7. Leech = 8 lapses → tutor sheet with rewrite / mnemonic / drop; re-flag every 4.
8. `kind ∈ {word, chunk}`; chunk cards use situation cue + audio.
9. Error log is a source: tagged `error_log`, speak mode within 48 h, next lesson sheet.
10. Cards carry native audio (required), English gloss, one example sentence, frequency rank.
