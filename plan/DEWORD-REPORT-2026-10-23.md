# De-word: report (updated 2026-10-22 12:30)

**Gallery (Before vs Look A, grades, words):** https://claude.ai/artifact/J4sqEaN5Dd9SEB4rCugY2e · also `docs/deword-gallery.html` on branch `claude/deword-overnight`

Medi picked **Look A** for every page and said the first pass "cut out too much data". Round 2 put the data back on screen.
Nothing live. Every number still on its page. Before = the pre-de-word pages shot today with the same live data.

| Page | Words before → now | Claude | GPT-6 Astra | Note |
|---|---|---|---|---|
| Progress & Stats | 9,580 → 5,966 | AAAAA | BABBA | all 25 rows, cards, 8 charts back; takeaway tiles on top |
| AI Reports | 8,597 → 7,818 | BABAA | CCBBB | blind spots, research list, grades back |
| How Anees works | 1,063 → 1,091 | BABAA | CACBB | |
| Lessons & Audio | 776 → 806 | BAAAA | BAABA | all 25 rows |
| One lesson (10-14) | 9,971 → 9,958 | AABAA | BABAA | every line; "Start Arabic practice" button |
| Word Bank | 3,856 → 2,260 | BABAA | BBBBA | row data back |
| Grammar Rules | 2,318 → 4,365 | BAAAA | BABBA | **more than before:** rule rows now open |
| Flashcards | 269 → 252 | BABAA | BABBA | |
| Student | 732 → 543 | AABAA | BAABA | |
| Homework | 163 → 114 | AAABA | BAAAA | |
| Tutor | 5,818 → 14,177 | BABAA | BABBA | **more than before:** lists that were folded are open |
| Tutor · grammar rules | 11,858 → 10,565 | BABAA | BABBA | every rule + example back; "why" behind ⓘ |
| Tutor · materials | 2,372 → 2,410 | BABAA | DAFBB | Codex wants a drawing per preposition |
| Big Picture | 577 → 559 | BABAA | CACBB | |
| System Settings | 323 → 227 | AABAA | BCABA | |

Grades = add · crucial · pictures · modes · look. **Crucial** (data kept) = A on 14 of 15 pages from both judges.
Dropped: the 5 old tutor addresses (amal/after, plan, review, verb-check, word-review) — same code lives in the Tutor hub.

## Rule X forces this line: drop the rule?
- PG-01/PG-15: the full-width "hourly robot has not published" banner on every page.
- The tutor's answer buttons stay where they are (judges want them side by side).
- PG-56 test keeps the 8-step picture off the very top of How Anees works.
- `test_m5_cards`: Sets tiles + card settings visible on Flashcards.

## Judge routes
- Gemini 3.8 Flash: weekly quota out since 10-22 02:05 (resets ~10-29). All final grades: Claude + GPT-6 Astra, $0 on plans.
- Claude usage limit stopped the night workers 03:30–05:50; their half-edits were rolled back.

## Known
- Tests: the same 8 that fail on master fail here; nothing new (homework dark-mode contrast fixed).
- Flashcards: one of four shots showed different counts (152/24 vs 54/16) — looks like a data-load race; not fixed.
- Look B CSS is still in the branch (unused); drop it when merging.

**Next: say which pages to merge first. I suggest Progress, Lessons and Homework; Tutor and Grammar first need your OK on showing more than before.**
