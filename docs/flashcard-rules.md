# Flashcard rules (Medi, 2026-09-30 / 2026-10-01)

Every rule here came from a correction Medi made while studying. `docs/cards.html` follows them; the audit
(`scripts/flashcard_audit_browser.js`) checks them on every card. Card text changes are display only: Amal's Doc and
Quizlet data are never edited by the page (her wording and spelling are the rule).

## What a card shows

| # | Rule | Example |
|---|---|---|
| F1 | Singular and plural sit on one line, same size, on BOTH sides | `Jumle · jumal` ⇄ `Sentence · sentences` |
| F2 | ` · ` (middle dot) means singular · plural, and nothing else. Doc `Sentence – sentences` and Quizlet `Daif (dyoof) = Guest - Guests` are shown with ` · ` too. Every Quizlet way of writing a plural counts: `Fasel (fsool) = Season`, `Cat- cats`, `Kalb (klaab(`, `Foreigner / foreigners`. A bracket is NOT a plural when it is a preposition the word takes (`Ana bat6all3 (3ala)`, `(la-)`, `(X)`), a gender note (`(M)`, `(Feminine)`) or the same word spelled again (`Hishis (his-his)`). A Doc plural field that holds person forms (`Tewsal`: `m: Tewsal f: Tewsli`) is not a plural: it shows as a small `m: Tewsal, f: Tewsli` line; a plural spelled like the singular (`His-his · his-his`) is said once | `Daif · dyoof` ⇄ `Guest · Guests` |
| F3 | ` / ` joins words of the SAME kind: two meanings, two spellings, two ways to say it. Each ` / ` part brings its own plural, in the same order (`Adjective – adjectives / trait – traits` → `Adjective / trait · adjectives / traits`) | `Tariqa · 6uruq / 6uru2` ⇄ `Way / Method · ways / methods` |
| F4 | The English plural is made from the English singular: head noun (before ` of ` or a `( )` note), irregulars (person → people, tooth → teeth, knife → knives, mosquito → mosquitoes), acronyms kept (TV → TVs). A note in front stays on the singular only (`(Travel) trip · trips`). Titles and odd cases are hand-picked in `EN_PL` (`Mr. / Sir · gentlemen`, `Grandmother / Mrs. / Ms. · grandmothers / ladies`, `Groceries Store · grocery stores`) | `A group of people · groups of people` |
| F5 | No English plural for: questions, long phrases (5+ words), words already plural (pants, glasses), adjectives (only, formal), commands, `(progressive)`. Uncountables (weather, homework, help, scenery) are said once. When only some ` / ` parts have a plural, the plural side lists those (`Traveling (progressive) / Passenger · passengers`, `Thing / something · things`). `review` and `motivation` DO have plurals (Amal: `Motivation - motivations`) | `Weather / atmosphere / vibe` |
| F6 | Same English, more than one Arabic word: all of them show, same size, either is right; the English side says how many | `I start` · 2 ways → `Ana babda / Ana baballesh` |
| F7 | Look-alike words get a hand-picked English note (list `EN_NOTE` in cards.html; add one when Medi flags a pair) | `Bird · birds (general)` vs `Small bird / sparrow` |
| F8 | Command-tense cards read as orders: `!` + "command · telling someone to do it". Verb-drill commands read `you (m), eat!` | `Scratch!` |
| F8b | Amal's plural Quizlet sets (singular on the front, plural on the back; title has `plur`, so `Plurel` too) are labelled Singular / Plural, not Arabic / English. A back in English (`E5we \| أخوة = Siblings`, `wlaad 3ammi = my uncles's (F) sons/kids`, `Dawle/a = Country`) stays an Arabic / English card | `sadiq → Asdiqaa2` |
| F9 | Cards whose front is only a number (Quizlet "Audio Homework": the audio is the question) are not flashcards | hidden |
| F10 | The same card (same Arabizi + English) is dealt once per round, even if two Quizlet sets contain it | |
| F11 | Verb drills: no ` · ` on the card (`I excite (someone)`); the stored data keeps its own format for Amal's verb check | |
| F12 | Amal's Quizlet sets with the same title (case and spaces ignored) are ONE tile. The newest set (highest Quizlet id) is the base, with its spelling and order; an older set's card is dropped when the same card is already there (same Arabic, or same Arabizi + same English), else it is added with its own old key. A dropped card's answers count for the kept card (read only; no stored row is changed). Rule FC-10, Medi 2026-10-02 ("why are there 2 adverbs of time?"). Code: `mergeSameTitle` / `mergeAliases` in `docs/js/cards-selection.js`, read in `docs/cards.html` (`ALIAS`); test: `tests/test_cards_selection.cjs` | `Adverbs of Time` (3) + `Adverbs of time` (29) → one tile, 29 cards (`Mbaare7`, not `Mbare7`) |
| F13 | A set sits in the section of what its cards drill: a verb's conjugations are Verbs, even with pronouns on it (`ba2ul conjugations`, `Beddi + 3endi Conjugation`, `Pronoun Objects With Verbs`, `Irregular Past Tenses`, `babse6 - banbese6 group`). `verb` must be a whole word (`Adverbs of time` is Topics). Possession & pronouns = possessive endings and prepositions + pronouns only. Rule FC-11, Medi 2026-10-02 ("isnt ba2ul a verb?"). Code: `SET_GROUPS` / `sectionOf` in `docs/js/cards-selection.js`; test: `tests/test_cards_selection.cjs` | `ba2ul conjugations` → Verbs |

## What the audit checks (scripts/flashcard_audit_browser.js)

All three sources (Doc words, Quizlet-only cards, verb-drill forms), both modes (Arabic first, English first). It must return `issues: {}`.

| # | Check |
|---|---|
| P0 | Arabic-first and English-first show the same two faces, only swapped |
| P1 | Every card with a plural shows `singular · plural` on the Arabic side, ` · ` once |
| P2 | ...and on the English side, unless an F5 rule leaves it out (the audit names the rule); no half-converted `X – Xs`, no singular on the plural side |
| P3 | The reverse: no English plural (` · ` or `X - Xs`) on a card whose Arabic has none |
| P4 | No Quizlet bracket plural is missed |
| P5 | No English back in a plural set is labelled Plural |

## How answering works

| # | Rule |
|---|---|
| A1 | Swipe left / ✕ = the whole card missed. Swipe right / ✓ = known |
| A2 | Singular · plural cards: two word buttons beside ✕ / ✓ (`✕ Jumle`, `✕ jumal`). One tap = only that word missed, next card. No extra question step (it broke the one-swipe flow) |
| A3 | ↺ undo sits bottom-left, from the second card on; it takes back the last answer (both rows on a plural card) |
| A4 | A missed card comes back 3 cards later in the same round until known once; it is tagged "Again · missed earlier" |
| A5 | "back in N" under ✕ / ✓ once the card is flipped (what each answer does to its schedule) |
| A6 | Round end: "Knew first try" vs "Needed another go"; Keep going deals the next batch; between 1 and 2 batches left it asks split (e.g. 13 + 14) or all |
| A8 | "? Ask Amal" (card top-right) puts the card on a list on this phone; home tile "Questions for Amal" shows it; Send opens the share menu (Medi picks Amal and sends) |
| A7 | Every set round deals cards you don't know yet first; cards you last marked Know come last; forms of one word are spread out (one per round, a word answered today goes to the back) |

## What is new, and limits

| # | Rule |
|---|---|
| N1 | NEW = only words Amal adds to the Doc after 2026-09-30. Everything already in the Doc is an old word to retest |
| N2 | Old untested words: no daily limit. New words: per day = the size of Amal's latest batch (none yet) |
| N5 | Old untested verbs: 1 present + 1 past + 1 command form per verb is enough. Only one untested form per verb and tense counts (none once any form of it is answered). 2,017 → 1,370 on 2026-10-01 |
| N3 | No button may lead nowhere: a Start button says how many cards open today or why none can; tiles with no cards are hidden |
| N4 | Mastered (Word Bank flashcard column) = right on 3 different days |

## Leech words

| # | Rule |
|---|---|
| L1 | A card is a leech once it is missed **3 times**, in any phase (learning misses count). That is the only leech rule: review lapses never make a leech on their own. The tag says the misses (`Leech · 3 misses`). Rule FC-07, Medi 2026-10-02 ("leech should alwys be 4", then "actually lets make it 3"); replaces the 09-21 "8 lapses" decision. Code: `docs/js/fsrs.js` (DEFAULTS.leechMisses = 3), test: `tests/test_fsrs.cjs` |

## Data issues for Amal (not changed by the page)

Her Doc and Quizlet wording and spelling are the rule; the page only changes how they are shown. Only Amal can fix these:

- 276 Doc plurals are written only in Arabizi (no Arabic letters).
- `Se77iس` (Arabic letter inside the Arabizi). `Tult = Third` is in the Doc twice (#725, #819). `Kul = All / Every / Every / All`.
- Homonyms to confirm: `Salon`, `Kul` (All / Eat), `Jahhez`, `Aktar`.
- Quizlet "Irregular People Plurals": from row 8 on every pair is shifted by one (row 8 has no front, so `Sabaaya → shab`, `Shabaab → Marra`, ... `Sittat → Sayyid`; 11 wrong cards, last row has no back).
- `His-his`: the Doc plural is the singular again (`his-his`), and its Arabic is `بعوضة` (Ba3ooda's), so Quizlet `Ba3ooda (ba3ood) = Mosquito - mosquetos` lands on the His-his card.
- Plural fields that hold person forms, not plurals: `Tewsal` (`m: Tewsal f: Tewsli`), `Enbese6` (`m: … f: … p: …`), `2addaish 7a22o` (`m: 7a22o f: 7a22ha`).
- Short-hand plurals shown as written: `E5we/a`, `Mummaredoon / een`, `rasmiyeen /aat`, `Waraq / 2`, `Buqa3 / 2a3`.
- Quizlet typos: `Kalb (klaab(`, `Airplain`, `mosquetos`, `Plurel`, `Termonology`, `my aunts' s(M) ons/kids`.
