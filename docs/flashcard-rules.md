# Flashcard rules (Medi, 2026-09-30 / 2026-10-01)

Every rule here came from a correction Medi made while studying. `docs/cards.html` follows them; the audit
(`scripts/flashcard_audit_browser.js`) checks them on every card. Card text changes are display only: Amal's Doc and
Quizlet data are never edited by the page (her wording and spelling are the rule).

## What a card shows

| # | Rule | Example |
|---|---|---|
| F1 | Singular and plural sit on one line, same size, on BOTH sides | `Jumle · jumal` ⇄ `Sentence · sentences` |
| F2 | ` · ` (middle dot) means singular · plural, and nothing else. Doc `Sentence – sentences` and Quizlet `Daif (dyoof) = Guest - Guests` are shown with ` · ` too | `Daif · dyoof` ⇄ `Guest · Guests` |
| F3 | ` / ` joins words of the SAME kind: two meanings, two spellings, two ways to say it | `Tariqa · 6uruq / 6uru2` ⇄ `Way / Method · ways / methods` |
| F4 | The English plural is made from the English singular: head noun (before ` of ` or a `( )` note), irregulars (person → people, tooth → teeth, knife → knives), acronyms kept (TV → TVs) | `A group of people · groups of people` |
| F5 | No English plural for: questions, long phrases (5+ words), words already plural (pants, glasses), adjectives (only, formal), commands, `(progressive)`. Uncountables (weather, homework, help) are said once | `Weather / atmosphere / vibe` |
| F6 | Same English, more than one Arabic word: all of them show, same size, either is right; the English side says how many | `I start` · 2 ways → `Ana babda / Ana baballesh` |
| F7 | Look-alike words get a hand-picked English note (list `EN_NOTE` in cards.html; add one when Medi flags a pair) | `Bird · birds (general)` vs `Small bird / sparrow` |
| F8 | Command-tense cards read as orders: `!` + "command · telling someone to do it". Verb-drill commands read `you (m), eat!` | `Scratch!` |
| F8b | Amal's plural Quizlet sets (singular on the front, plural on the back) are labelled Singular / Plural, not Arabic / English | `sadiq → Asdiqaa2` |
| F9 | Cards whose front is only a number (Quizlet "Audio Homework": the audio is the question) are not flashcards | hidden |
| F10 | The same card (same Arabizi + English) is dealt once per round, even if two Quizlet sets contain it | |
| F11 | Verb drills: no ` · ` on the card (`I excite (someone)`); the stored data keeps its own format for Amal's verb check | |

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
| N3 | No button may lead nowhere: a Start button says how many cards open today or why none can; tiles with no cards are hidden |
| N4 | Mastered (Word Bank flashcard column) = right on 3 different days |

## Data issues for Amal (not changed by the page)

See the audit report: `Se77iس` (Arabic letter in Arabizi), `Tult = Third` listed twice, `Kul = All / Every / Every / All`,
276 plurals written only in Arabizi (no Arabic letters), homonyms to confirm (`Salon`, `Kul`, `Jahhez`, `Aktar`).
