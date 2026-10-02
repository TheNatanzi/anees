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

**Amended by Medi 2026-09-23 ("these are all no brainers"):** a word that is not on her list whole may be
shown in Arabizi when it is built from her own spellings and fits the sentence. Kept in
`docs/data/arabizi-extra.json`, one row per word with its method and source:

| Method | What it is | Example |
|---|---|---|
| `sound` | the transcript or his accent swapped a similar letter; her word fits the sentence | دلت → her ضلت **dallat** |
| `pieces` | her word + her prefixes/endings, with the real vowel change | بيزعجني → **byez3ejni** (her baz3ej); شغلي → **shu8li** (her Shu8ul) |
| `her-chat` | she typed it in WhatsApp, even once | مقلاة → **Ma2la** |
| `guess` | no piece of hers exists; natural Levantine in her style | country names |

Target: 95 of 100 correct on a random hand check. Fragments and unclear words stay in Arabic.

**Extended by Medi 2026-09-26 ("why no arabizi again. How do we stop you from doing this?"):** on the Lessons page
error cards nothing stays Arabic-only - his own wrong or cut-off forms included, spelled as they sound in her letters
(method `as-said`). Guard: `scripts/arabizi_gaps.cjs` lists every card word without Arabizi (exit 1 when any);
`scripts/review_lesson.py` step 6b runs it on every new lesson and fills the gaps before the lesson counts as done.

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

---

## S6 — Every correction becomes a rule (Medi 2026-10-02)

When Medi (or Amal) finds an error, fixing that one moment is not enough. Two things happen, every time:

1. **The moment** is fixed through the existing ruling files — never by deleting a row; the ruling stays visible with
   its reason (`data/lesson-work/full-audit/rejected.json`, `duplicates.json`, `data/grammar-usage-rulings.json`,
   Amal's notes in `scripts/amal_grammar_notes.py`).
2. **The general rule** is written where the next lesson will meet it, so the same correction is never needed twice:
   code (e.g. the automatic not-a-use rules in `scripts/detect_grammar_usage.py`, the repeat-slip rule in
   `scripts/full_audit_build.py`, the homograph list in `docs/js/word-bank-arabizi.js`), the AI readers' brief
   (`data/lesson-work/full-audit/READER-BRIEF.md`), or this file.

The agent tells Medi which rule it added and how many past moments the rule changed. If a correction cannot be made
general (a true one-off), the agent says so instead of staying silent.

---

## S7 — A page is never older than its source (Medi 2026-10-02)

"Ensure the data is getting populated as soon as it's available." Five rules, each enforced in code and tests:

| Id | Rule | Where it lives |
|---|---|---|
| G1 | A generated file is rebuilt, never merged: a rebase conflict in built data keeps master's copy, re-stamps the build and queues the rebuild; only a hand-made file waits for a person | `scripts/publish_guard.py` (resolve_generated_conflicts), `tests/test_publish_guard.py` |
| R3 | Each AI reader file is checked against its own shape (the third reader writes rulings, not rows) | `scripts/review_lesson.py` (valid_reader_file), `tests/test_review_lesson.py` |
| P1 | A snapshot that grows with every lesson is read in pages, never in one request | `scripts/speaking_snapshot.py`, `tests/test_speaking_snapshot_paged.py` |
| L1 | A page that reads live data re-reads it when the tab comes back into view, or says why it must not | `docs/js/live-reread.js`, `tests/test_live_reread.py` |
| F1 | When the database or the raw archive has a newer lesson than the pages, the pages say so, and the publish guard warns when Amal's answers or publishing fall behind | `docs/js/lesson-behind.js`, `check_data_freshness` in `scripts/publish_guard.py` |
