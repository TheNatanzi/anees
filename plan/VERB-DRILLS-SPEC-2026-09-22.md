# Verb drills — specification (Medi's rulings 2026-09-22)

Goal (Medi): every tense of every verb memorised. Fill the Doc's blanks, add verb
randomizers to Flashcards, and a level 2 with "to / from / with someone".

## Rulings (final; do not re-ask)

| # | Question | Ruling |
|---|---|---|
| 1 | Where missing forms come from | **Guess, Amal checks.** Fix the guessing rules, fill every blank, tag each guessed form `not checked by Amal`. Amal gets a check list; her correction always wins. |
| 2 | What one card tests | **1 verb + 1 tense + 1 person.** Front = English cue ("she · knew"), back = Arabizi + Arabic ("heyye 3irfat · هي عرفت"). |
| 3 | Level 2 add-ons | **Both kinds:** object endings on the verb (3atini, akhadtik) and a preposition + person after it (7akait ma3na, emshi ma3hom). |
| 4 | Which verbs get level 2 | **Every verb**, with only add-ons that make sense for it: every verb gets ma3 / la + person; verbs that take an object also get endings. Claude tags each verb; Amal's pairs win; Amal checks the tags. |
| 5 | Arabic script on guessed forms | **Yes, Arabic too** (Medi reversed "Arabizi only"): built from Amal's own Arabic for that verb, tagged `not checked`. If she has no Arabic for the verb, Arabizi only. |

## Defaults (Claude's, not asked; change only if Medi says)

- Tenses in drills: **Present, Past, Command.** "All" = those three. Future stays out (0 forms in the Doc).
- Persons: Present / Past = I, you (m), you (f), you (pl), he, she, we, they. Command = you (m), you (f), you (pl).
- Documented form always beats a guess. A guess never overwrites Amal's text.

## Scale today (catalog `docs/data/word-bank-catalog.json`, 144 verbs)

| Tense | From Amal | Guessed now | Known bad guess |
|---|---|---|---|
| Present | 145 | 979 (no Arabic) | `inti bti3raf` → should be `bti3rafi` |
| Past | 724 | 81 | — |
| Command | 262 | 30 | — |

## 1 · Fill the blanks (conjugation engine)

- New pure module (e.g. `docs/js/verb-forms.js` + Python twin only if a script needs it) that derives every
  person from Amal's documented forms of the same verb: present from her "I" form (`ba-` → `bti-`/`bi-`/`bni-`,
  `-i` for you (f), `-u` for plurals), past from her documented persons, command from her `/ي/وا` pattern.
- Arabic built the same way from her Arabic (بـ → بت/بي/بن, ـي, ـوا …). No Arabic for the verb → Arabizi only.
- Golden tests: every documented form must be reproduced by the engine from the other documented forms of
  that verb (hold-one-out). Report the hit rate; rules that miss get fixed before any guess ships.
- Each generated form carries `provenance: "inferred"` + `checked: false`; the Word Bank catalog build
  (`scripts/build_word_bank_catalog.py`) is the one place that writes them.

## 2 · Amal's check list

- A page or Sheet listing every guessed form (verb · tense · person · Arabizi · Arabic) with ✓ / fix fields.
  Her answers overwrite the guess and flip `checked: true`. Follow the Amal-links pattern; do not send anything
  to Amal without Medi's yes.

## 3 · Randomizers (new section on the Flashcards selection screen: **Verb drills**)

| Mode | Options | Cards |
|---|---|---|
| **20 verbs, random** | tense: All / Past / Present / Command | 20 distinct verbs, each once, random tense (from the option) + random person |
| **5 or 10 verbs, full** | verbs: 5 / 10 · tense: All / Past / Present / Command | every person of the chosen tense(s) for those verbs (5 verbs × All = up to 95 cards) |
| **Level toggle** | Level 1 / Level 2 | Level 2 = same modes, each card gets a valid add-on for that verb (ending or preposition + person) |

- Same swipe cards, same `card_results` row, same FSRS. Guessed forms show a small `not checked by Amal` tag.
- Card key: the documented word key when the form is in the Doc; else `form:<entry id>:<person>`
  (level 2: `form:<entry id>:<person>:<add-on>`). word-bank-core maps `form:` keys back to the tense entry
  (already done for `form:<entry id>` in fca058e).

## 4 · Level 2 add-ons

- Endings: -ni (me), -ak / -ik (you m/f), -o (him), -ha (her), -na (us), -kom (you pl), -hom (them), with the
  vowel / stem changes Palestinian needs (3ata → 3atani / 3atini; akhad → akhadtak / akhadtik).
- Prepositions + person: ma3 (with), la (to / for), min (from), 3an (about), 3ala (on) — la-/ma3-/min-
  forms as in Amal's Quizlet sets "Ma3 + pronouns", "La + Pronouns", "Other Prepositions + Pronouns".
- Verb tags: `object: yes/no`, `preps: [...]`. Seed from Quizlet "verb + preposition collocations" (36) and
  "Pronoun Objects With Verbs" (25); Claude tags the rest; Amal checks the tags on the same list.

## Build order

1. Engine + hold-one-out test (report hit rate to Medi before shipping guesses).
2. Catalog rebuild with guessed forms + Amal check list.
3. Verb drills section (level 1).
4. Level 2 tags + add-on engine + level toggle.

Validation as in plan/NEXT-PROMPT-flashcards-selection-2026-09-21.md (writes stubbed in browser checks,
`card_results` count unchanged after tests, Pages checked live).
