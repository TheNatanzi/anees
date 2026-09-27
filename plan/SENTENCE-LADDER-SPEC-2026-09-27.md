# Sentence-length ladder: build contract (2026-09-27)

Medi approved every decision below in a grilling session on 2026-09-27 ("let's do all of these").
This file is the contract between the data pipeline (`scripts/build_sentence_ladder.py`, built) and the front-end
builds that come next (Fluency tab, swipe-check screen, Amal's recipe card, flashcard boost, Grammar Console
"hear it / say it"). The front end reads only the JSON described here. It never re-derives labels.

| Piece | File | Status |
|---|---|---|
| Pipeline | `scripts/build_sentence_ladder.py` | built, runs in about 8 s over 14 lessons |
| Summary data | `docs/data/sentence-ladder.json` | about 0.37 MB |
| Per-lesson sentences | `docs/data/sentence-ladder/<date>.json` | 0.18 to 0.67 MB each |
| Farsi cognates seed | `docs/data/farsi-cognates.json` | 162 entries, **unverified, seed** |
| Swipe labels table | `supabase/migrations/020_sentence_labels.sql` | written, **not applied** |
| Tests | `tests/test_sentence_ladder.py` | 12 tests |
| Hook | `scripts/hourly_lessons.py` → `refresh_published()` | failure-tolerant, runs after `build_lessons_page_data.py` |

Standing rules that bind this feature: S1 (Arabizi only from Amal; this pipeline prints **no** Arabizi of its own; the
page renders Arabic through `word-bank-arabizi.js`), S2 (transcripts are read, never edited), S3 (a miss needs a
signal: every breakdown carries its signal and source), and S5 (a pause is not an error: Medi's pieces join into one
sentence across pauses of up to 15 s).

---

## 1. Approved decisions

1. **Goal.** Comprehension and production length go up while the success rate goes up. The ladder is a scoreboard
   for Medi and a lever for Amal, who may see his numbers.
2. **Ladder.** The ladder climbs one Arabic word at a time. "Good at N" means ≥ 80% understood on the last 20 scored
   sentences of length N, spread over ≥ 2 lessons. The target is N + 1. Speaking uses the same rule, with "success"
   meaning his sentence was not corrected by Amal.
3. **Five non-understanding signals.** Each is stored separately and they are combined: (1) repeat request,
   (2) meaning question, (3) "I don't understand", (4) rescue (machine guess), (5) wrong answer (machine guess).
   A bare aywa / ok / yes / mm reply is `unknown`, not understood. The labels are `understood`, `breakdown` and
   `unknown`.
4. **Scored unit.** The unit is Amal's last Arabic sentence before a Medi reply. Only Arabic words are counted, and
   clitics stay inside their word (بيتي = 1). Mostly-English sentences are skipped. **Look-back:** if his breakdown
   asks about a word from up to 3 sentences or 60 s earlier, the miss is charged to that earlier sentence.
5. **Tags.** Every listening sentence and every Medi sentence carries tags plus the 57 grammar rules it uses (the
   detector's own patterns, imported unchanged). Learner-state tags are not baked in. Tokens carry Word Bank keys so
   the browser joins them live.
6. **Display rule.** An effect is shown only when ≥ 30 scored sentences back it. Section 6 covers the model.
7. **Label check.** After each lesson Medi swipes 10 machine-labelled sentences (understood / didn't / not sure).
   The swipes go to Supabase `sentence_labels`.
8. **First consumers.** These are Amal's recipe card, the flashcard boost and Grammar Console "hear it / say it".
   The data they need is precomputed.
9. **Deferred.** The monthly fixed 20-sentence listening check (section 11).

---

## 2. Definitions

### 2.1 Sentences

The input is the turns in `docs/data/lessons/<date>.json`, on the **lesson clock** (seconds on the audio the lesson
page plays, see the header of `scripts/build_lessons_page_data.py`).

- A sentence ends at `. ? ! ؟ …`.
- **Amal's** pieces join across her engine fragments when they are ≤ 3 s apart and Medi only back-channelled in
  between. A back-channel is ≤ 3 tokens, all of them mm-hmm / yeah / okay / آه and similar.
- **Medi's** pieces join until Amal really speaks, with gaps of ≤ 15 s (rule S5).
- A back-channel said while the other person's sentence is still open is kept as a `mid` interjection. It is not a
  reply.
- `[speaking Arabic]` / `[speaking foreign language]` turns with no words are *holes*: speech exists but its content is
  unknown.
- **Times:**
  - word timings (`data/lessons/<date>/words_labeled.json`, which exists for 08-25, 09-04 and 09-05 only):
    `rate_src = "words"`;
  - else the turn split by characters: `"turn-split"`;
  - else the whole turn: `"turn"`.

### 2.2 Arabic words (the length)

- Arabic-script tokens, **plus** Latin tokens that are Arabic. Latin tokens are classed in this order:
  1. they contain Arabizi digits;
  2. they are on the hand list of Latin-Arabic function words;
  3. they are English, meaning in `english_stop.py` or the script's `EN_EXTRA`;
  4. they match a Word Bank `match_loose` / `fold` form;
  5. they end in an English suffix.
- A Latin token that is still unknown after that counts as Arabic when the sentence's known tokens lean Arabic. When
  the sentence has no known tokens, it counts as Arabic if ≥ 40% of the speaker's known Latin tokens within ±120 s are
  Arabic, else as English. Such tokens carry `guess: 1`.
- These do not count as words:
  - fillers (uh, um, ممم, آآآ);
  - a lone و / ب / ل / الـ, or a Latin el / il / w / u, which joins the next word;
  - a broken-off first attempt (شك-شكلو, ta-tam);
  - an immediate stutter repeat (إحنا، إحنا = 1).
- **Mostly English** means English tokens / (Arabic + English tokens) **> 0.5**. Such a sentence is skipped.
  "شو يعني for free؟" (2 / 2) is kept. This reads the brief's "> 50% Latin tokens that are English" as a share of
  *all* word tokens. Otherwise any sentence with one English word would be skipped.

### 2.3 The listening unit

For every Medi reply run, the unit is **the last qualifying Amal sentence in the run of hers just before it**. A
sentence qualifies when all of these hold:

- it has ≥ 1 Arabic word;
- it is not mostly English;
- it is not only her feedback words (ممتاز، صح، طيب، تمام، خلاص، مهم, and similar);
- it is **not her echo or recast of his own last words**: her content words all come from his last turns, or she
  says a short "لا، X" right after him. Such a sentence is feedback on his speech, not input to understand;
- Medi's audio is present at that moment (section 2.8).

Three other routes also create units. Each is marked in `unit`:

- `rescue`: signal 4, below;
- `lookback`: a sentence charged by the look-back;
- `hand`: a sentence named by the lesson audit's hand-read listening miss.

### 2.4 Signals

Each signal is stored under its own key in `signals` with `src` (`machine` or `hand`) and `guess`.

| Key | Meaning | How it is found | Guess? |
|---|---|---|---|
| `repeat_request` | (1) he asks her to say it again | His reply is only huh / what / sorry / شو / ها; or it contains "say that again", "what did you say", "what was it", "are you saying", "كمان مرة", "عيدي", and similar. Also: a ≤ 3-token question back ("Alma?", "Qwaad?") answered by her saying her sentence again. | no; the "short question" and "echo" kinds are `guess: true` |
| `meaning_question` | (2) he asks what her word means | "shu ya3ni X", "شو يعني", "what does X mean", "what's X?" (only when X is Arabic), "meaning?". `kind: "ask"`. A check of his own guess ("does it mean X?", "X means Y, right?") is kept with `kind: "confirm-guess"`, `counts_as: "unknown"`. It labels the sentence `unknown`, or `understood` when she confirms. | ask: no; confirm-guess: yes |
| `dont_understand` | (3) he says so | "I don't understand", "مش فاهم", "ما فهمت", "I'm lost", "no idea". A bare "I don't know / ما بعرف" counts only after her question or "what does it mean?" prompt. | no |
| `rescue` | (4) he is silent and she rescues him | ≥ 3 s of silence from him after her Arabic sentence, then, unasked, she either (a) switches to English *and says so*: "it means", "I said", "did you understand", "do you remember", "in English"; or (b) rephrases it (difflib similarity ≥ 0.5). Not counted when her next sentence is "No, …" (she corrects him), when her sentence has a self-repair (…, —), or when the English introduces a new Arabic word. | yes |
| `wrong_answer` | (5) he answers something else and she fixes the meaning | Her next sentence (≤ 10 s) starts with لا / no / مش, **and** repeats a content word of her sentence. When his reply was Arabic it also needs an explicit gloss ("I said", "means"). No grammar-console or audit correction may sit in the same window, since that is a grammar fix, not a meaning fix. | yes |
| `hand_audit` | the lesson audit read a listening miss by hand | `docs/data/lessons/<date>.json → vocab_errors` whose hand-written `why` says **he** misheard, decoded, did not catch, or could not place **her** word, and whose Arabic word is found in one of her sentences in the 60 s before. Events where *she* misheard him, and production misses, are excluded. | no (hand) |

### 2.5 Labels

Labels are decided in this order:

1. `breakdown`: any signal except a `confirm-guess`.
2. `unknown`:
   - there is no reply;
   - the reply is a hole;
   - **the reply is bare**: ≤ 2 tokens, all aywa / ok / yes / yeah / mm / no / تمام / صح and similar, or "I see",
     "got it", "oh okay". "تمام" after كيفك is an answer, not a nod;
   - his question was about an earlier sentence (look-back);
   - he only said her words back, as a drill echo (not after her question: جاهز؟ → جاهز. is an answer);
   - he checked a guess of the meaning and she did not confirm it;
   - a **one-word remark** of hers (not a question or prompt) got a reply that shows nothing about it.
3. `understood`: every other content reply (decision 3). `evidence` says how strong it is:

| `evidence` | Meaning |
|---|---|
| `she confirmed` | her next line starts with ممتاز / صح / mm-hmm / yes / exactly |
| `reused her word` | his reply shares a content word or Word Bank key with her sentence |
| `Arabic answer to her question` | ≥ 2 Arabic words after her question or prompt |
| `said her word's meaning in English` | his English contains the Word Bank gloss of one of her words |
| `English meaning for her 'what does it mean'` | he answered her meaning quiz in English |
| `his guess of the meaning, and she confirmed it` | confirm-guess plus her confirmation |
| `content reply only` | nothing direct: the weakest level |

`summary.ladder.listen_strict` recomputes N counting only evidence-backed `understood`, as a sensitivity view.

### 2.6 Look-back

It applies when his reply carries signal 1, 2 or 3 and the Arabic words he asks about (his reply minus function and
signal words) are **not** in the scored sentence. The pipeline then walks back through up to 3 of her earlier
sentences, no more than 60 s before his reply. It matches Arabic script with Arabic script (including proclitics),
Latin with Latin by `fold`, and across scripts by Word Bank key. On a hit:

- the earlier sentence gets the signal (`charged_from`) and `lookback.from`;
- the last sentence becomes `unknown` with `lookback.to`.

### 2.7 Speaking unit and success

- **The unit.** Every Medi sentence with ≥ 1 Arabic word.
- **Not scored.** The sentence is kept with `scored: false` and a `why_not` in three cases:
  - it is mostly English;
  - Amal's audio is missing, so no correction could be seen;
  - it echoes her sentence of the last 10 s (similarity ≥ 0.8, or all his words are hers).
- **`corrected`.** At least one of these is attached to the sentence:
  - a grammar-console hand-verified correction (`docs/data/grammar-console.json`, all 558 `verified`; includes
    recasts, prompt-then-fix, explicit-no, named-rule and chat-fix);
  - a lesson-audit grammar row (`grammar_errors`) not already in the console;
  - a lesson-audit word fix (`vocab_errors`: a wrong word, English for her word, or a word she supplied when he asked;
    listening misses are excluded).

  A correction attaches to the Medi sentence whose span contains its `t` (±3 s), with the best `said` text match.
- **`success`.** Any other scored sentence.

### 2.8 Missing audio

`missing_side` lists `{side, from, to, source}`. Two sources are used:

- `silence`: one side has no turns for ≥ 240 s while the other has ≥ 15 turns;
- `talk.window`: anything outside `lessons.json → talk.window`.

This finds Medi missing on 09-23 from 0 to 1424 s and Amal missing on 09-26 from 0 to 1217 s. No listening unit is
made where Medi is missing, and no speaking sentence is scored where Amal is missing.

---

## 3. The ladder

For each length N:

1. Take the scored sentences labelled ok or bad; `unknown` is excluded.
2. Walk back from the latest lesson, taking **at most 10 from any one lesson**, until 20 are collected. The cap is
   what makes "spread over ≥ 2 lessons" achievable. Without it, one long lesson fills the whole window and no rung can
   ever pass.
3. Give the rung a status:
   - `good`: n = 20, ≥ 80% ok, and ≥ 2 lessons;
   - `not yet`: n = 20 and < 80% ok;
   - `one lesson only`: ≥ 80% ok but from 1 lesson;
   - `not enough data`: fewer than 20.

**N** is the highest `good` length with no `not yet` / `one lesson only` below it. A length with too little data does
not block. **target = N + 1**. Listening uses understood vs breakdown. Speaking uses success vs corrected.

Current state (2026-09-27, all 14 lessons):

| | N | % at N | Target | % at target (last 20) |
|---|---|---|---|---|
| Listening | 7 | 90% | 8 | 75% |
| Listening, strict (evidence-backed understood only) | 2 | 85% | 3 | — |
| Speaking | 2 | 85% | 3 | 55% |

---

## 4. Tags

`tags` is a field on every sentence. The speaking side has the same fields except those marked L (listening only).
Every morphological tag is an **estimate** (no tagger; hand lists plus Amal's Doc lexicons).

| Field | Meaning |
|---|---|
| `len` | Arabic words (= `n`) |
| `syll` | syllable estimate: Latin = vowel groups; Arabic = letters / 2 without ال, min 1 |
| `secs`, `wps`, `rate_src` | duration, words per second (all words), and where the times came from (`words` / `turn-split` / `turn` / `mixed`) |
| `pause` | word-timed lessons only, else null: `{n, total_s, max_s, mean_run, artic_wps}`, with pauses ≥ 0.25 s |
| `tense` | list from `present, past, future, command, progressive, none`. Uses detector rules B1/B5/B6/B7/B10/B11/B13/B14, رح / عم, and Word Bank key topics for Latin words |
| `cl_max`, `cl_hist` | endings per word: object / possessive endings, dative -l- (حكيتلك), -ش, the b- prefix, +1 after عم. Articles and و are not counted. `cl_hist` = `{"0","1","2+"}` word counts |
| `fn_share`, `clitic_word_share`, `fn_or_clitic_share`, `noun_share` | function words from a closed hand list; nouns = keyed words not in the verb or adjective catalog, or unknown ال- words |
| `neg` | `ma_sh` (ما…ش), `mish` (مش), `ma` (ما + verb, not after بعد/قبل/لما/شو/اللي), `la_imperative`, or `none` |
| `persons`, `non_first` | from pronouns, b-prefixes (بت / بي / بن / ب) and past endings; `non_first` = any 2nd or 3rd person |
| `verb_forms` | catalog verbs only: `{w, group, form (I–X from Amal's present-form Arabizi), root, root_in_bank_other, tense_form}` |
| `q`, `prompt` | `wh` / `yn` / `statement`; `prompt: "meaning"` for her "شو يعني …؟" quiz |
| `en_tokens`, `en_clause`, `en_share` | English inside; `en_clause` = 3 or more English tokens in a row |
| `idioms` | fixed phrases found. The seed list is recurring n-grams in her speech (≥ 6 times in ≥ 3 lessons) plus everyday set phrases (`IDIOMS`) |
| `colloq_fn` | count of dialect-only function words (hand list of about 60) |
| `emph_density` | ص ض ط ظ ح ع ق غ خ (Latin: 9 6 7 3 8 5 q) per letter |
| `minute`, `min_since_break`, `local_time`, `hour` | a break = ≥ 30 s with nobody talking; local time = `start_local` + t |
| `turns_since_topic_shift` | shift = a break, or a transition word (طيب / يلا / okay so / let's …) with < 10% content-key overlap between the minute before and the minute after |
| `overlap_s`, `near_hole`, `noise_tag`, `near_missing_side` | audio trouble proxies |
| `new_in_lesson`, `min_since_heard_s`, `median_since_heard_s` | in-lesson recency of her content words (heard from her earlier in this lesson) |
| L `repeat_index`, `repeat_of` | 1 + earlier sentences of hers with difflib ratio ≥ 0.7 on the normalised Arabic words |
| L `chat`, `typed_in_chat` | nearest chat line typed by Amal within −20 s / +30 s: `{dt, text, overlap}`. Typed = ≥ 1 shared word. Chat exists for 09-14 … 09-23 (in the lesson JSON as `who: "chat"`); 09-26 and earlier have none |

`rules` lists the ids of the 57 buckets whose detector pattern fires on the sentence (Arabic script only). It is
computed by `rules_in()`, which runs exactly the loop in `detect_grammar_usage.py`'s `__main__`. Medi's side is
unchanged.

### 4.1 Tokens for the live learner-state join

`tok` holds one record per Arabic word:

| Field | Meaning |
|---|---|
| `w` | the word as said |
| `n` | `docs/js/word-bank-core.js normalize(w)`, byte-for-byte the same normalisation |
| `k` | the Word Bank key when unique |
| `ks` | up to 4 candidate keys when ambiguous |
| `f` | 1 for a function word |
| `c` | ending count |
| `lat` | 1 for a Latin-letter word |
| `guess` | 1 when Arabic-ness was guessed |

Keys come from `words.json` (arabic / arabizi / aliases, via `match_loose` / `fold` and `arabic_norm`) and from the
catalog forms, with proclitic and ending stripping as a fallback.

**Not baked in; the browser computes these live:**

- Word Bank status mix;
- unknown key word;
- FSRS retrievability (card log);
- days since exposure;
- known-by-ear;
- Farsi cognate: join `tok[].n` to `farsi-cognates.json → items[].ar_norm`, or `tok[].k` to `items[].word_keys`.

---

## 5. JSON schema

### 5.1 `docs/data/sentence-ladder/<date>.json`

```
{ version, date, clock, audio: ["lessons/<date>/audio/lesson.mp3"] | [Amal.mp3, Medi.mp3] | null,
  missing_side: [{side, from, to, source}],
  listen: [Unit], speak: [Unit] }
```

Every `Unit` has these fields:

| Field | Meaning |
|---|---|
| `id` | `"<date>:L:<round(t*10)>"` (listening) or `":S:"` (speaking). Stable across rebuilds while the lesson JSON is unchanged. It is the key for `sentence_labels.sentence_id` |
| `side` | `listen` or `speak` |
| `t`, `end` | lesson-clock seconds |
| `text` | the sentence as transcribed (rule S2) |
| `n` | Arabic words |
| `tok`, `tags`, `rules` | see section 4 |
| `label` | listen: `understood` / `breakdown` / `unknown`; speak: `success` / `corrected` / `unknown` |
| `scored` | whether it counts toward the ladder and the effects |
| `date` | the lesson date |

Listening units also have:

| Field | Meaning |
|---|---|
| `unit` | `last-before-reply` / `rescue` / `lookback` / `hand` |
| `signals` | section 2.4 |
| `reply` | `{t, end, text, hole, latency_s}` or null |
| `lookback` | `{from \| to, words}` or null |
| `evidence` or `why_unknown` | section 2.5 |

Speaking units also have `corrections: [{id, src: grammar-console | lesson-grammar | lesson-vocab, rule, signal,
kind}]` and `why_not` when not scored.

### 5.2 `docs/data/sentence-ladder.json` (summary)

| Key | What it holds | Consumer |
|---|---|---|
| `version`, `generated`, `spec`, `method`, `thresholds`, `cuts` | provenance; every threshold named in section 2; the data-driven cut points (75th percentile of wps, emphatic density, syllables) | all |
| `lessons[]` | per lesson: `{date, type, amal_sentences, listen_units, listen_labels, speak_sentences, speak_scored, speak_labels, word_timings, missing_side, audio, chat_lines}` | Fluency tab |
| `files` | date → per-lesson file path | all |
| `labels` | overall label counts, listen and speak | Fluency tab |
| `evidence` | counts of `evidence`, `why_unknown` and breakdown signals | Fluency tab (honesty panel) |
| `ladder.listen`, `ladder.speak` | `{N, target, pct_at_N, pct_at_target, n_at_target, rungs: [{len, n_total, n_last, ok, pct, lessons, status}]}` | Fluency tab (scoreboard), recipe card |
| `ladder.listen_strict` | `{N, target, pct_at_N}` counting only evidence-backed understood | Fluency tab (sensitivity note) |
| `effects.listen[]`, `effects.speak[]` | `{tag, label, n_with, n_without, pct_with, pct_without, rd_mh, ci95, show, or_adjusted, strata}`, sorted with the costliest shown effect first | Fluency tab ("what costs him") |
| `recipe` | `{target_len, text, items: [{lever, advice, basis, n_with, pct_with, pct_without, rd_mh}], note}` | Amal's pre-lesson recipe card |
| `boost[]` | `{key, arabizi, arabic, english, strong, weak, score, dates, last, ids}`, top 60 | flashcard boost |
| `rules{A1…}` | `{name, hear: {n, understood, breakdown, unknown, pct, show, examples: [ids]}, say: {uses, corrected_any, pct_ok, corrections_this_rule, show, examples}}` | Grammar Console "hear it / say it" |
| `swipe` | `{date, picks: [{id, t, end, text, machine_label, signals, reply_text, reply_end, audio, play_from, play_to, clip}], table}` | swipe-check screen |
| `farsi_cognates` | `{file, n, counts, status}` | Word Bank / Fluency |
| `deferred` | features that are specified but not built | — |

`boost` and `recipe` use machine labels. The page may overlay Medi's swipes, since the latest `sentence_labels` row
per `sentence_id` beats the machine label, and recompute `pct` from `rungs` and `strata`. Everything needed for that is
in the files.

---

## 6. The effect model (decision 6)

**The choice:** a Mantel-Haenszel risk difference stratified by lesson × length band (1–2, 3–4, 5–6, 7–9, 10+),
with the ≥ 30 floor applied to *each* side (with the tag and without). A ridge (L2, λ = 1) logistic regression runs
alongside it as a second column.

- **MH risk difference (`rd_mh`, percentage points of "understood").** Stratum weights are w = n₁n₀ / (n₁ + n₀). The
  95% CI uses the matching variance. Why this model:
  - it answers the question Amal asks, "same lesson, same length, how much worse with this tag?", in a unit she
    reads;
  - it controls for the two strongest confounders (the lesson and the sentence length);
  - it cannot fail to converge on 113 breakdowns;
  - **JS can recompute it** from `strata` (`"<date>|<band>": [ok_with, n_with, ok_without, n_without]`), for example
    after Medi's swipes relabel sentences.
- **`or_adjusted`.** The odds ratio from one ridge logistic model with all shown non-rule tags, standardised length
  and lesson fixed effects, precomputed in Python. This column is the answer when tags overlap: حكيتلك carries
  endings, past tense and person at once. It is null for rule tags and for tags under the floor.
- **Display.** `show` is true only if `n_with ≥ 30` and `n_without ≥ 30`. The page shows `rd_mh` with its CI, and says
  "not enough data" otherwise.
- **The research report's expectation** (Kostin 2004) is single-tag effects of r ≈ .1–.3. At 14 lessons nearly every
  CI crosses 0, so show CIs and do not rank tags as facts.

Current costliest shown effects:

- **Listening:**
  - a word with 2+ endings: −3.5 points (n = 55);
  - past tense: −3.1 (n = 145);
  - noun-heavy: −2.1 (n = 207).

  All CIs cross 0. Rule D1 (preposition + noun) is −9.2 (n = 71, CI −17.2 to −1.3).
- **Speaking:**
  - مش: −22.4 (n = 38, CI −34 to −11);
  - a pause ≥ 0.5 s inside (word-timed lessons only): −6.3 (n = 215);
  - many syllables: −5.2 (n = 675).

---

## 7. Precomputed consumers

- **Recipe card (`recipe`).** Target length = listening N + 1. Each lever takes one of two bases:
  - `data`: the lever's tag costs ≥ 5 points (`rd_mh ≤ −5`) with the floor met;
  - `default (not enough data, or no cost seen)`: otherwise.

  The levers are tense, endings, new words, speed, negation, person, derived forms, idioms, dialect words, question
  type and English clauses. Today the card reads "8 words · mostly present · ≤1 ending per word · ≤1 new word ·
  normal speed", and every lever is on its default. The card must show the basis. "New word" here means not heard
  earlier in the lesson; the page refines it live with the Word Bank.
- **Flashcard boost (`boost`).** A word key is credited when it sank a breakdown:
  - `strong` (+1): the word he asked about, or the hand-audited word;
  - `weak` (1 / k shared): when nothing was asked, the keyed content words of the missed sentence.

  The list carries `dates` and `ids` (to open the sentence). The flashcard page filters the list by card state.
- **Grammar Console "hear it / say it" (`rules`).**
  - `hear` counts the listening sentences that use the rule and the % understood (understood vs breakdown).
  - `say` counts his scored sentences that use the rule, how many were corrected (any correction), `pct_ok`, and the
    console's own count of corrections filed under that rule.
  - Both have `show` (≥ 30) and example ids.
  - Currently 13 rules clear the floor on the listening side and 12 on the speaking side.
- **Swipe picks (`swipe`).** Ten picks from the latest lesson: 4 breakdowns, 3 unknowns and 3 understood, topped up
  from the other groups when one is short. The draw is deterministic per date.
  - `clip` is the ffmpeg cut used by `build_grammar_console.cut_clip`, written to `docs/lessons/<date>/clips/sl-*.mp3`.
  - This machine has **no ffmpeg**, so `clip` is null. The page plays `audio[0]` from `play_from` to `play_to`
    (her sentence −0.4 s → the end of his reply +0.5 s).
  - Each swipe writes one `sentence_labels` row.

---

## 8. `sentence_labels` (Supabase, migration 020, not applied)

| Column | Meaning |
|---|---|
| `id` | text primary key: a client uuid, so replays are idempotent |
| `sentence_id`, `lesson_date`, `side` | which sentence was swiped |
| `label` | `understood` / `breakdown` / `not_sure` |
| `machine_label`, `machine_version`, `n_words` | what the machine said, from which build |
| `ts`, `answer_ms`, `played`, `tz_offset_min`, `tz` | timing and context |
| `subject`, `created_at` | as in `card_results` |

Access: RLS is on, with anon **select + insert** only, the same as `card_results`. Update and delete are revoked. A
relabel is a new row, and readers take the latest row per `sentence_id`. To apply, run
`python scripts/apply_migrations.py`, which applies every file not yet recorded, so only after review.

---

## 9. Hand check (2026-09-27, by Claude against the lesson transcripts)

| Check | Sample | Result |
|---|---|---|
| All labels, blind | 30 random listening units, final code | 19 / 30 agree (63%). Two rules were fixed after that check (an echo answer to her question; a confirm-guess she confirmed): 21 / 30 on the same sample |
| `breakdown` precision | 20 random breakdowns, final code | **16 / 20 = 80%** (an earlier independent sample: 16 / 20) |
| `unknown` share | the same 30 | 12 / 30. Overall: 517 of 1,704 = 30% |

- **Where the machine is wrong:**
  - mostly `understood` when the truth is unclear (he changed topic, or her line was a recast or an engine garble);
  - missed breakdowns (his "Going to help them?" misread; "Shag?").
- **Where breakdowns are wrong:**
  - rescues on her teaching turns;
  - a form question counted as a repeat request.

Medi's swipes are the fix. The machine label is a first guess.

---

## 10. Known limits

- **Recall of breakdowns is low.** Only 113 of 1,704 units (7%) are breakdowns; the hand check found about 1 missed
  breakdown per 5 "understood". The listening ladder (N = 7) is therefore optimistic. `listen_strict` (N = 2) is the
  floor.
- **Mixed evidence.** 531 of 1,074 `understood` are `content reply only`.
- **Transcript quality.** 09-04 has 351 turns with an unknown speaker (`?`), which are skipped. 09-14 … 09-18 have long
  Latin-transliterated stretches where the Arabic / English split is guessed. `[speaking Arabic]` holes hide his
  replies.
- **Few timings.** Word timings exist for 3 lessons only, so `pause` is null elsewhere and `wps` mixes sources
  (`rate_src` says which). The raw engine files for 09-11 … 09-23 are not on this machine.
- **Clitics and morphology are estimates.** An ending is stripped only when the stem is a word in Amal's Doc or
  catalog. Spellings that differ from her Doc (بتضايق vs her بدايق) are missed.
- **Chat alignment.** Chat lines are aligned by the lesson JSON's clock. Typed-in-chat means within −20 s / +30 s with
  a shared word.
- **Time of day.** All lessons start between 13:35 and 15:13, so the effect has almost no range. The research says it
  needs a chronotype questionnaire first.
- **Farsi cognates.** 162 entries, **unverified, seed** (84 transparent, 33 sound-disguised, 45 false friends), from
  Claude's general knowledge, with no Arabizi (rule S1). 84 join to a Word Bank key today.
- **Recipe card.** No listening lever clears −5 points yet, so every lever is on its default.
- **One detector change.** `scripts/detect_grammar_usage.py` hard-codes `C:\dev\anees-hourly\docs`. It now falls back
  to this repo's `docs` only when that folder does not exist. The patterns and Medi's-side output are unchanged.
- **When the files refresh.** The hook runs only when the hourly job publishes a new lesson. Later audit rulings or
  Amal's taps change `grammar-console.json` and `vocab_errors`; after those, re-run
  `python scripts/build_sentence_ladder.py`.

---

## 11. Later (not built)

- **Monthly fixed 20-sentence listening check.** The same 20 recorded Amal sentences are played once a month, with
  lengths spread over N−2 … N+3. Medi says what each means, and Amal or the machine grades it. The check is
  independent of lesson flow and chat, so it is a clean trend line against the in-lesson ladder. Scores would go in
  `sentence_labels` with `side = 'listen'` and a `monthly-<yyyy-mm>:<k>` `sentence_id`.
- **Swipe overlay in the pipeline.** Read `sentence_labels` at build time, so that `ladder`, `effects`, `boost` and
  `recipe` use Medi's labels where they exist. Today the page does this itself.
- **Learner-state tags as effects.** Word Bank status mix, FSRS min-R, known-by-ear and Farsi cognate, once the page
  has joined them.

---

## 12. Run and test

```
python scripts/build_sentence_ladder.py             # all lessons in docs/data/lessons.json
python scripts/build_sentence_ladder.py --dump D    # print lesson D's listening units, for hand checks
python -m pytest tests/test_sentence_ladder.py -q
```
