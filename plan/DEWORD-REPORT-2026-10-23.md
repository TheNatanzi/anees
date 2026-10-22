# De-word overnight: morning report

**Gallery (before / A / B, grades, words):** https://claude.ai/artifact/J4sqEaN5Dd9SEB4rCugY2e · also `docs/deword-gallery.html` on branch `claude/deword-overnight`

52,186 → 13,416 visible words (−74%). Every number still on its page (Playwright check). Nothing live.
0 of 20 pages all-A from both judges. Homework is the only one close (A/A). Grades = add · crucial · pictures · modes · look.

| Page | Words | Look A (Claude / Codex) | Look B (Claude / Codex) |
|---|---|---|---|
| Progress & Stats | 10,435 → 1,153 | BBBBA / CCCBB | BCBAA / CBCBB |
| AI Reports | 8,537 → 598 | BBBAA / BBBAB | ABAAA / BBBAA |
| How Anees works | 1,051 → 122 | AABAA / BBCBA | AABAB / BBCAB |
| Lessons & Audio | 764 → 110 | ABBAA / BBABA | AABAA / BBBAB |
| One lesson (10-14) | 9,959 → 7,704 | BBBAA / CCBBA | BBBAB / CCBBA |
| Word Bank | 3,841 → 260 | BBBAA / CBBBA | BBBAA / BBCBB |
| Grammar Rules | 2,306 → 227 | BBBBA / BBBBA | BBBAA / BBBBB |
| Flashcards | 217 → 135 | ABBAA / BBCBA | ABBAA / BBBAA |
| Student | 692 → 396 | ABBAA / BBAAA | AABAA / BBBAA |
| Homework | 49 → 11 | AAAAA / AAAAA | ABAAA / AAAAA |
| Tutor | 8,052 → 2,512 | BBBAA / CBCBA | BBBAA / CCCBB |
| Tutor · grammar rules | 11,858 → 131 (folded, opens in place) | BBAAA / BBBAA | AABBA / BBAAA |
| Tutor · materials | 2,372 → 52 | AABAA / BBCAA | AABAA / BBBAA |
| Tutor answer pages (5) | ~190 → ~140 | AABAA / ABBAA (typical) | AABAA / ABAAA (typical) |
| Big Picture | 80 → 76 | AABAA / BBBBA | AABAA / BBBAA |
| System Settings | 311 → 171 | BBBAA / CCBCB | BBBBA / CCCBB |

Done = both looks built + graded on every page. Not done = all-A (stopped at time).

## Rule X forces this line: drop the rule?
- **PG-01/PG-15:** the full-width "hourly robot has not published" banner on every page (judges want a small chip).
- **PG-17:** the Tutor To-do list shows every row; Codex wants one "Up next" card on phone.
- **PG-29/PG-05:** the Student Homework "—" tile stays as its own tile.
- **Tutor's answer buttons:** the sub-lines inside them stay ("counts as a mistake…").
- **PG-31:** the phone bottom bar. It was painted over rows in full-page stills; the stills now hide it.
- **Tests force lines:**
  - `test_m5_cards`: Sets tiles + card settings visible.
  - `test_tutor_grammar`: exact "Add grammar" tab text.
  - `test_build_tutor_weak`: exact "Completed" tab text.
  - `test_build_lesson_page`: "lines … typed in chat".
- **Lesson transcript:** both judges want it folded. Kept, because the lines are the lesson data.
- **Look switch on the tutor's pages:** judges ask to hide it. Drop it there once one look is picked.

## Judge routes
- **Gemini 3.8 Flash (agy):** weekly quota ran out at about 02:05 ("resets in 167 h"). Graded only the early rounds; the final grades come from 2 judges.
- **Claude + Codex (gpt-6-astra):** worked all night. $0, plans only.
- **Usage limit:** the Claude session limit stopped all 5 page workers at about 03:30 (reset 05:50). Their unchecked half-edits were rolled back to the last checked commit.

## Before merging (known)
- `test_lesson_ledger` LS-11: the 10-14 lesson page changed, so its ledger needs a rebuild (the hourly job rebuilds it). Check the lesson counts after that.
- A pre-commit hook adds `build.json` / `build.js` to commits. The last commit puts them back to master's version.
- 8 tests already fail on master (same 8 here). New failures: only the LS-11 above.

**Pick a look: open the gallery and approve A (flat) or B (bright). Then merge `claude/deword-overnight` one page at a time, starting with Homework, AI Reports and Lessons.**
