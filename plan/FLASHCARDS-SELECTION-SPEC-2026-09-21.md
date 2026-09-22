# Flashcards selection screen — specification (approved by Medi 2026-09-21, "go")

Build contract for the first screen of `docs/cards.html`. Scheduling, card UI and
timing already shipped (d9e059d, c32a11a, da38392); nothing here changes them.

## Already live (do not rebuild)

- FSRS-6 scheduler `docs/js/fsrs.js` + daily queue `AneesCards.queue` in `docs/js/cards-core.js`.
- Quizlet-style card: tap to flip, swipe right = Know (`got`), left = Still learning (`missed`),
  grading locked until flipped, undo, donut summary. Sabz skin from `css/sabz-tokens.css`.
- Every answer is one `card_results` row; `flip_ms` / `answer_ms` = visible time to flip / to swipe.
  Slow answers are **only recorded**, never change a grade (Medi).
- The Stitch flashcards design is dropped. Do not browse Stitch.

## The screen: labelled sections, top to bottom

| # | Section | Tiles | Source |
|---|---|---|---|
| 1 | **Due for review** (never an unlabelled "today's set") | Due · New · Learning counts; tap = FSRS queue | `AneesCards.queue` |
| 2 | **New from Amal** | words Amal marked newly taught | `amal_rules` kind `new` (existing "new" bucket) |
| 3 | **Shaky** | *In lessons*: Verbs · Nouns · Adjectives · Other — *On cards*: same 4 | spoken status (word-bank-core `speaking`) and card status (`flashcards`) — **both**, as separate tiles |
| 4 | **Wrong** | same 8-way split | same |
| 5 | **Never tested** | 20 random words never answered on cards | `card_results` |
| 6 | **Verb tenses** | Present · Past · Command | Doc topics Verbs List / Past Tense / Command Tense (+ catalog verb groups) |
| 7 | **Verbs + prepositions** | "Verb + preposition collocations" (36) + "Pronoun objects with verbs" (25) | `docs/data/quizlet/amal-quizlet-sets.json` |
| 8 | **Amal's Doc categories** | 20 topics, each opening its sub-topics (41) | `words.topic` / `words.subtopic` |
| 9 | **Amal's Quizlet sets** | 106 sets grouped: Plurals · Possession & pronouns · Verbs · Topics · Dated lessons (Dec–Aug words, audio homework) | `amal-quizlet-sets.json` |

Word type for the Verbs / Nouns / Adjectives / Other split: catalog group `type`
(Verb, Adjective), noun = has a plural entry, else Other — as word-bank-core models it.

## Every tile

- Shows its count. Tap opens the same swipe cards (options: 20 / 10 / All, shuffle, card front).
- Answers from any tile write the same `card_results` row and feed FSRS (same as today's "Practice a set").
- Empty tile = count "—" with a one-line reason ("No wrong words on cards yet"), never a bare 0.
- Mobile first, single column, Sabz skin.

## Quizlet cards

- A Quizlet term that matches a Doc word (normalise Arabizi as word-bank-arabizi does, or the Arabic)
  uses that word's `word_key`, so history is shared.
- An unmatched term becomes its own card, `word_key = "q:<set id>:<rank>"`; it must not enter
  Word Bank spoken metrics. Terms with a blank side are skipped (5 exist, Amal's own blanks).
- Term text is "Arabizi | Arabic" or "Arabic | Arabizi"; split on `|` and detect the Arabic side.

## Not done yet

- 26 of Medi's 132 Quizlet sets are unread (Quizlet bot check): past-tense groups, ba2ul
  conjugations, babse6 / zehe2 groups, causative verbs, weather, animals, July/August words.
  Retry through Medi's Chrome (Claude in Chrome): same-origin `fetch` of the set page, parse
  `__NEXT_DATA__` → nested JSON strings → objects with `cardSides` (label `word` / `definition`,
  `media[].plainText`), 1–2.5 s between sets, stop at the first 403. Never solve the
  press-and-hold check. The set list is `docs/data/quizlet/sets-sent-to-medi.json`.
