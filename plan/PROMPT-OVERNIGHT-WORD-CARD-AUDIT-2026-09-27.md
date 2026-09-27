# Overnight audit - every word card on the Lessons page (2026-09-27)

Medi 2026-09-27: "Do a full overnight audit on these ... please try and have the words on our list in mind so a single
letter off doesn't throw you off, use context and meanings both ways, Arabic and English."

## Why
The automatic sheet check matched strings (tenses, endings, plurals, Latin spellings) and kept getting it wrong: Medi
caught تستنى, أصابع, قصيرات, تنانير, بتضايقني, دكتور عام, دكتور نفسي one by one; a hand check then found 56 of 98 "new"
words were on his list. Judge by MEANING, not by listing every form.

## Scope
Every card in `docs/data/lessons/<date>.json` for all lessons: `vocab_errors` (and spot-check `vocab_correct`).

## For each vocab error card decide
1. **On the list or new?** His list = `docs/data/words.json` items (arabic, arabizi, english, plural - plural is often
   Latin only) + the verb pairs Amal taught (`TAUGHT` in `scripts/build_lessons_page_data.py`). Same word, same meaning,
   any form (tense, person, command, gender, plural incl. broken plurals, ال/ب/و, pronoun endings, one letter off in
   spelling or transcription) = `on_list`. A look-alike with a different meaning = `new` (عام general vs a list 'year'
   phrase; نفسي psychological vs نفس same; بالمية percent vs مية hundred). Check both ways: Arabic -> list, and the card's
   English -> list English.
2. **Is it really his error?** Read the transcript around the moment (`turns` in the same file). If Amal echoes what he
   said ("what did I say?" -> her answer), trust her words over the engine (09-26 31:53: engine wrote جاب, he said دبا).
   If he actually said it right, verdict `not_an_error`.
3. **Right list word** for the rating: the list word's `key` (words.json) it belongs to, or null.

## Output
`data/lesson-work/sheet-verdicts.json` - ONE list for all cards (replaces the 98-row file; keep its 98 verdicts unless
you find they are wrong): `[{date, mmss, arabic, verdict: on_list|new|not_an_error, list_key, list_match, reason}]`.
`scripts/build_lessons_page_data.py` already applies `on_list` / `new`; add `not_an_error` handling there (drop the card
from vocab_errors and from the Words %, keep a note), then run `python scripts/build_lessons_page_data.py`,
`python scripts/build_amal_review.py`, `node scripts/arabizi_gaps.cjs` (must print 0), commit + push
(`git push origin HEAD:master`, commit message ends with the Co-Authored-By line).

## Report (Medi's format)
One line, a small table (cards checked / on list / new / not an error / changed vs before), 3-5 one-line bullets with the
calls he may want to look at, one bold action. Never send anything to Amal.
