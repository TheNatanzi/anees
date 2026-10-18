# The accuracy method (PR-28) - how every lesson is transcribed and graded

Medi 2026-10-18: "Moving forward create a system of rules and methods in order to have my lessons be transcribed and graded
in the most accurate way from our research method."

This is the standing method. Every agent (Claude, Codex) and every script follows it. A step changes ONLY by the change
rule at the bottom. Evidence: `reports/READER-90-OVERNIGHT-2026-10-17.pdf` (branch claude/reader-90-overnight),
`plan/PIPELINE-TEST-PROTOCOL.md` (PR-23), research memo `data/lesson-work/reader-tiers/overnight-2026-10-17/research-memo.md`.

## 1. The pipeline (in order)

| # | Step | Method (current best) | Measured | Rule |
|---|---|---|---|---|
| 1 | Hear | ElevenLabs writes both tracks; Gemini re-listens to each of his lines 3 times, 2 of 3 wins (method A) | 95% / 94% of his words right (10-09, 10-10); beat B, C, E, F | PR-23 |
| 2 | Hold | A re-heard line that moves toward the tutor's own word waits for her ear | stops hidden mistakes | TR-27 |
| 3 | Read | Mistake readers read the whole lesson with READER-BRIEF.md | see 4 | PR-25 |
| 4 | Decide | Best tested: **judge panel** - every reader's flags pooled, Claude Opus + Gemini 3.7 Flash judges rule on each | 83.5 held-out F0.5 (live Opus + Sonnet both-agree: ~80) | PR-28 (rollout) |
| 5 | Grade-book rules | "Asked for a word" = grey half-credit chip, never a mistake; no tutor reaction = never a mistake | +5 to +10 on every reader | PR-27 |
| 6 | Tutor wins | Amal's rulings (Tutor page, AM-33 dispute checks, AM-29 key checks) override every AI decision and are re-applied after every rebuild | 14 rulings, key 102 -> 99 | AM-33 |
| 7 | Grammar lists | Her uploads feed the rules (collocation sets -> D2) | D2 49 -> 63 verbs | GR-40 |
| 8 | Publish | Only through the publish guard; stalls pop up on the PC | | PR-26 |

Until the judge-panel rollout is live, step 4 runs Opus + Sonnet both-agree (PR-25).

## 2. What it may cost

- Medi's plans first: Claude through `claude -p`, OpenAI through `codex.cmd exec` (gpt-6-astra, gpt-5.6-*). AGENTS.md rule 7.
- Paid keys (Gemini, OpenAI API) only with Medi's yes to the exact spend and a dollar cap.

## 3. Every lesson, old and new

- New lessons: the hourly job runs steps 1-8 automatically.
- When a step improves, every old lesson is re-run with it (re-read, re-settle, rebuild, re-apply her rulings). No lesson
  keeps an older method, and no lesson loses a mistake the tutor confirmed.
- Reports (AI Reports, Grades tab, review-grades.json) always name the method in use and its held-out score.

## 4. How a step is allowed to change (the change rule)

1. Measured against fully graded lessons only (Medi's full review = the answer key; the tutor's rulings correct the key).
2. Scored with `scripts/reader_tiers.py` (hearing: `scripts/hearing_harness.py`), leave-one-lesson-out: tune on some
   lessons, score on a lesson it never saw. Only the held-out number counts.
3. It must beat the current method by more than the noise (~4 F0.5 with 3 lessons) AND win again on the next fully
   graded lesson (PR-23 section 6). Hidden-mistake rate (FCR) must not rise.
4. Fair test: every model gets the same input.
5. Record it: the run log in PIPELINE-TEST-PROTOCOL.md section 7, a registry rule with Medi's words, tests, the guard.

## 5. What keeps it improving

- Medi fully grades 1 lesson in 3 (lean schedule, PR-23 section 1b); each one is a fresh test.
- Disagreements between the key and the AI go to the tutor's Tutor page (AM-33), blind, with a "why" box.
- Ceiling: the key itself is ~90% reliable (the tutor agreed fully with 78 of 86 notes), so ~90 is the practical maximum.
