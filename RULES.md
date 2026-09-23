# Anees — standing rules

Rules that outlive any one build. Everything here binds the code, the pages, the wiki, and every
agent (Claude, Codex) writing to Medi. A rule changes only when Medi says so, in writing, here.

---

## S1 — Amal's spelling is the only spelling

**The rule.** Every Arabic word Anees prints is spelled the way **Amal** writes it. Anees never invents
an Arabizi spelling, never normalises hers toward MSA, and never borrows another dialect's convention.

**Where a spelling comes from, in order.** First match wins:

| # | Source | What it is |
|---|---|---|
| 1 | `words.house_spelling` | Her own typed form, mined from her WhatsApp lines by `scripts/house_spelling.py` (seen ≥ 2 times, most frequent wins; a tie goes to the most recent and both stay in `forms`) |
| 2 | The vocabulary Doc `arabizi` column | Her Doc spelling |
| 3 | The Doc's Arabic script | Her Arabic |
| 4 | — | Nothing. The word stays in **Arabic script** on screen, labelled "Unverified spelling stays in Arabic" |

There is no step 5. If Amal has never written it, Anees does not guess it in Latin letters.

**Her letters.** `2` ء · `3` ع · `5` خ · `6` ط · `7` ح · `8` غ · `9` ص. Use these, not IPA, not MSA
transliteration, not another tutor's chart.

**Her dialect choices win over any textbook.** Example: she writes the "we" prefix as `bn-`
(bnebse6, bne2dar, benkoon). Other Levantine sources write `m-`. Anees keeps `bn-`.

**Display vs matching.** Her spelling is for **display only**. The Doc key stays the match key, so
changing a display spelling never re-scores anything.

**Who this binds.**
- every screen, card, report, drill and email Anees generates
- every wiki and plan page in this repo
- **every answer an agent writes to Medi in chat** — examples are quoted from her Doc, and anything
  not from her is marked as unverified, not presented as her spelling

**Medi never reviews Arabizi spellings.** Best guess ships, Amal corrects. (Standing rule since
2026-09-05.)

**Where it lives in code.** `scripts/house_spelling.py`, `docs/data/house_spelling.json`,
`words.house_spelling` in Supabase, and the "Unverified spelling stays in Arabic" fallback in
`docs/js/word-bank-arabizi.js`.

---

## S2 — Raw transcripts are never edited

Amal's and Medi's recorded words stay exactly as the engine wrote them. Corrections live in an
overlay (`docs/data/word-bank-review.json`), never in the source. See `docs/word-bank-review-rules.md`.

---

## S3 — A slip is only a slip when there is a signal

Nothing is scored wrong because a model thinks it sounds wrong. A grammar or word miss needs Amal
recasting it, or Medi asking. (Rule M1.)

---

## S4 — Pronunciation is never a missed word

A dropped ع or ط is logged as pronunciation, with the stumble kept. It never reduces a word's score
and never counts as "did not say it". (Rule M4.)

---

## S5 — Pauses are not errors

Medi builds a sentence before he says it. A long pause before a right answer is a right answer.
(Rule M7.)
