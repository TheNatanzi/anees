# Overnight report — 2026-09-23

Page: https://claude.ai/artifact/GoTD4nQCFSkKm7UzD799D7 (private)

**All 12 recorded lessons are live with audio, and Verb drills (levels 1 and 2) are live on Flashcards.**

## Scorecard

| Part | Result |
|---|---|
| Lessons found | 12 lessons (2 were missing: **09-18** and **09-21**) |
| Lessons on the site | 12 / 12, each with playable audio |
| Lesson audit | 10 / 12 pass every check · 2 have one explained line (below) |
| Verb drills step 3 (level 1) | Live |
| Verb drills step 4 (level 2) | Live · Amal's second check link made, **not sent** |
| Tests | Same 14 old failures before and after · 0 new · 22 new tests pass |
| Second opinion (Codex) | 14 problems found → 14 fixed |
| Money | **$1.08** of the $10 cap (ElevenLabs) |
| `card_results` | 8 → 64 = your own 56 answers at 00:48–00:55 · 0 from my tests |

## Lessons

| Date | Source | On site | Audit |
|---|---|---|---|
| 08-25 | Meet recording | yes + audio (new) | pass |
| 09-04 | Meet recording | yes + audio (new) | pass |
| 09-05 | Recall (1 file per person) | yes + audio (new, no more "Choose recording") | pass |
| 09-10 | Recall | yes + Amal's 33 chat lines (new) | pass |
| 09-11 | Recall | yes + audio (new) | pass · 1 filler over silence |
| 09-14 | Recall | **yes (new)** | pass |
| 09-15 | Recall | yes + Amal's first 21 min (new) | pass |
| 09-16 | Recall | yes + audio + chat (new) | pass |
| 09-17 | Recall | yes + audio + chat (new) | pass |
| **09-18** | Meet recording only (speakers estimated) | **yes (new)** | pass |
| 09-19 | Recall | yes + audio + chat (new) | pass · 1 quiet line |
| **09-21** | Recall (bot never written down) | **yes (new)** | pass |

- **No recording:** every lesson before 08-25 (never recorded), and 09-06 → 09-09, 09-12, 09-13, 09-20.
- **Not lessons:** 11 other recordings were business meetings (Akram, SEO).
- **Why 2 went missing:** Meet now saves each call in its own Drive folder, and one bot was never written down.

## Verb drills

- **Where:** Flashcards → section 7 "Verb drills".
- **Modes:** 20 verbs random · 5 or 10 verbs with every person · tense All / Present / Past / Command · both directions.
- **Level 2:** adds "me / you / him…" endings or "with / to / from / about / on / in + person".
- **Engine hit rate (guessing a form Amal already wrote):** Present 93% · Past 98% · Command 95% · Arabic 96–99%.
- **Level 2 vs Amal's 25 examples:** 16 exact · 20 same sound · Arabic 23 (the rest are her typos).
- **Amal's answers so far:** 0 (first link, sent 09-22).
- **Level 2 check link (not sent):** https://thenatanzi.github.io/anees/amal/verb-check.html#t=zzKmq2u99YFBEq_zhVUQccr7C4v9M4rGeT0jrk_dmc0

## Fixed along the way

- **Word Bank never credits:** a word heard over silence · the same word twice in one sentence · a speaker guessed from a mixed recording.
- **Home page** said "Supabase is not reachable" even online — fixed.
- **Word Bank / Flashcards** timed out loading lesson scores after the new lessons — fixed (loads in pages).

## Still open

- **09-19 at 44:30** — "Oh, okay." is very quiet; probably real, one listen settles it.
- **09-11 at 10:15** — a filler "آآآ" was heard over silence; no word credited.
- **Hourly lesson job** — the fixed version is built but your Windows task still runs the old one.
- Money note: $0.23 of the $1.08 was one 09-18 transcription done twice by mistake.

## Your one action

**Run this once in PowerShell to switch the hourly lesson job to the fixed version (it dry-runs first, spends nothing):**

```
git -C C:\dev\anees fetch origin; git -C C:\dev\anees show origin/master:scripts/switch_hourly_job.ps1 > $env:TEMP\switch.ps1; powershell -ExecutionPolicy Bypass -File $env:TEMP\switch.ps1
```
