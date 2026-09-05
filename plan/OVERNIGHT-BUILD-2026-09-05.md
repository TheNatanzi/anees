# Anees overnight one-shot build — prompt, gates, and sign-off (run night of 2026-09-04 → morning 2026-09-05)

Paste this whole file as the first message of a fresh Claude Code chat in `C:\dev\anees`. The run loops build → test → harden per milestone. A milestone is DONE only when its gate output is pasted into `plan/OVERNIGHT-LOG.md` and the sign-off named in the gate has been obtained. No milestone may be skipped or reordered.

## 0. Facts settled with Medi (grill, 2026-09-04 evening)

- **Scope tonight = all 8 pieces built.** Pieces that can be proven on existing data (Aug 25 + Sep 4 lessons) must be battle-tested. Pieces that need Amal (4, 5, 8) are tested end to end with Medi as the stand-in.
- **Lesson tomorrow ~13:30. Medi sends Amal her link 11:00–11:30.** Morning checklist must take Medi ≤ 20 min.
- **Amal's total time ≤ 10 min per lesson** (before + after). Her training questions = 3–5 per lesson, spread over 5–10 lessons, never 20 at once.
- **Word truth = the Google Doc** `1inA6ZeETtqJZHQYiZxtubWytsN5xh8_klQH50yRyrjw` (~2,200 rows, 3 columns Arabizi | Arabic | English, 79 topic headings). Amal edits it. App imports hourly, one way, never writes to it.
- **Spelling key = Amal's Arabizi.** Medi's spelling is matched loosely (6↔t/ط, 7↔h/ح, 3↔a/ع, 2↔'/ء, 5↔kh/خ, 9↔s/ص, 8↔gh/غ, vowels ignored, doubled letters collapsed). Arabic script stored beside it and shown as a second line.
- **Grip buckets (4):** Ice cold = right 5 in a row on ≥ 3 different days; one miss → Cold. Cold = said unprompted in a lesson with no correction, or flashcard right first try. Shaky = right on second try, or said only after Amal said it. Missed = Amal corrected it, Medi asked for it, or wrong twice on cards. **Missed + words learned in the last 3 lessons appear 3× more often** in cards, sentence suggestions, and homework.
- **Live data = Supabase** (new free project `anees`). Pages = GitHub Pages (`docs/`). Amal has no login: her links carry a secret token. Medi's flashcard results sync via localStorage queue → Supabase.
- **Speaker-label floor:** per-speaker scores are published only when ElevenLabs' split is OK or the pitch fallback leaves ≤ 15% of words unlabeled; otherwise the report shows "–" and says why. Never a guessed number (standing rule).
- **Amal is included, never replaced:** every planner/homework item is a *suggestion*; her edits and rejections are stored as rules that change future suggestions.
- **Flashcards = Quizlet, exactly:** Flashcards (flip), Learn, Write, Match, Test. Subject picker = Doc headings + grammar sets (past tense, all verb tenses, plurals, …).
- **Future projects section (not built tonight, listed in the UI):** 1 deep research on language-learning studies → rules the app follows (extend wiki 02/03/04/06); 2 audio homework that listens to Medi's pronunciation (ElevenLabs TTS + STT; LearnerVoice caveat); 3 adding words inside the app; 4 Discord + Craig separate-track recording (design agreed 2026-09-04, Ennuicastr as paid fallback).

## 1. Hard limits (violating any one = stop, write handoff, do not continue)

1. Never email, message, or share anything with Amal. Only Medi (thenatanzi@gmail.com) receives email.
2. Never write to the Google Doc.
3. Spend ≤ $10 on ElevenLabs (whole balance) and ≤ $10 on OpenAI. Log every paid call with cost to `plan/OVERNIGHT-LOG.md`. Stop paid calls at 90% of either cap.
4. Never delete lesson audio or `scribe.json` files.
5. Never push a page whose test file fails. Every push must be preceded by `python -m pytest -q` green.
6. Never put a number on any page that is not computed from data; unknown = "–" with a one-line reason.
7. When a gate cannot be met after 3 loop iterations, mark the milestone BLOCKED in the log with the exact failing check, and move to the next milestone that does not depend on it.
8. Secrets stay in User env / Supabase; nothing secret in the public repo.
9. Do not modify the live hourly pipeline's Task Scheduler entry; ship changes behind tests only.

## 2. Loop protocol (every milestone)

```
BUILD  → write code + a test file that encodes the gate
TEST   → run the gate; paste raw output in plan/OVERNIGHT-LOG.md under the milestone
HARDEN → break it on purpose (bad input, missing file, API 429, empty transcript, failed speaker split); fix; re-run
REVIEW → Codex audit (codex:rescue) with the milestone's checklist; fix every P0/P1 it finds; re-run gate
SIGN   → council where required (anthropic-skills:council); record score; ≥ 8/10 with all P0 closed = DONE
```

Codex prompt template: "Audit milestone <M> of plan/OVERNIGHT-BUILD-2026-09-05.md in C:\dev\anees. Verify each gate check by running it, not by reading. Report P0/P1/P2 with file:line and a failing command. Do not change files."

## 3. Milestones and gates (strict, measurable)

### M0 — Data spine (Supabase + Doc import)
Build: Supabase project `anees`; tables `words`, `word_events`, `lessons`, `lesson_events`, `card_results`, `amal_rules`, `amal_links`; RLS so token links read/write only their rows; `scripts/import_vocab.py` (Drive → words, hourly via Task Scheduler, one-way).
Gate (all must pass):
- import yields ≥ 2,100 words, each with arabizi, arabic, english, topic, subtopic; 0 duplicate keys after normalization; second run changes 0 rows (idempotent).
- 20 random words spot-checked against the Doc by string match = 20/20.
- loose matcher test set: 40 Medi spellings (from Sep 4 transcript + chat) → ≥ 36 map to the right Amal key, 0 map to a wrong key.
- RLS test: a token for link A cannot read link B's rows (SQL test in repo).
Sign-off: Codex.

### M1 — Lesson understanding (run on Aug 25 AND Sep 4)
Build: `scripts/understand_lesson.py`: per lesson → topic words (from chat sidecar + transcript frequency + Doc match), every Doc word occurrence with time, speaker, prompted/unprompted, correction/uptake flags (reuse tutor_reaction_exp rules), label-confidence.
Gate:
- Sep 4: the babse6 / banbese6 family is in the top 2 topics; Aug 25: top topic matches Amal's chat/transcript (state which and why).
- ≥ 90% of Amal's typed chat words (47 on Sep 4) are found in the transcript within ±120 s of the chat time (Codex finding: chat lags speech).
- every detected event links to an audio clip ≤ 25 s that plays in the browser; 20 random clips checked with ffprobe: clip time = event time ± 0.5 s.
- label-confidence floor implemented and unit-tested with a forced one-voice transcript → per-speaker fields = None.
Sign-off: Codex.

### M2 — After-lesson report (both lessons, emailed to Medi)
Build: page per lesson: what you missed / what you nailed / new words / reused old words / Amal's typed words / 20-moment list with play buttons; rich email to Medi with chart + log (house rule); publish only after tests.
Gate:
- 10-check list passes on BOTH lessons: no guessed numbers; "–" where unknown; each miss has audio; counts reconcile to lesson_events rows; chart present; mobile 375 px no horizontal scroll; dark + light; loads < 3 s on Pages; email received by Medi; email links resolve 200.
- forced failure test: speaker split failed → report publishes with "–" and a plain-English reason, no per-speaker numbers.
Sign-off: Codex + council (≥ 8/10).

### M3 — Amal's before-lesson link (planner)
Build: token page, phone-first: ≤ 3 fields (today's topic, new words if any, anything to repeat), then suggestions: 8 sentences each containing ≥ 1 Missed/new word + ≥ 1 Cold word, tap to keep/drop/edit; edits saved as `amal_rules`.
Gate:
- Medi completes it as stand-in in ≤ 2 min on a phone (timed, logged).
- one question per screen, buttons ≥ 48 px, no scrolling inside a step, progress "1 of 3", works with no typing except the topic.
- each suggested sentence uses only Doc words + grammar Amal has taught (topic headings already covered) — checked by script, 0 violations.
- kept/dropped/edited decisions visibly change the next suggestion set (test: drop a word twice → it stops appearing).
Sign-off: Codex.

### M4 — Amal's after-lesson link (3–5 questions)
Build: token page; questions chosen by value: unknown words in transcript, low-confidence clips, disputed corrections; each = audio ≤ 15 s + 2–4 big buttons (Right / Wrong / Not Medi / Skip) + optional one-line box; answers → `amal_rules`, and they update word buckets and matcher aliases.
Gate:
- never more than 5 questions; total ≤ 5 min for the stand-in (timed).
- every answer produces a visible rule row and a re-scored word; test with 5 answers on Sep 4 data.
- link expires after 7 days; second open shows "already done, thank you" not the questions again.
Sign-off: Codex + council (≥ 8/10, they must attempt it as Amal on a phone-size window).

### M5 — Flashcards (Quizlet parity)
Build: Flashcards / Learn / Write / Match / Test; subject picker (Doc headings + grammar sets); 4 buckets; 3× weighting; first-try/second-try/wrong tracking; localStorage queue → Supabase; "flag to Amal" on often-wrong words feeds M3/M8.
Gate:
- all 5 modes work on phone and desktop; Match times a round; Test grades and stores.
- scheduler test: a Missed word appears ≥ 3× as often as a Cold word over 300 simulated draws (script).
- Ice-cold promotion test: 5 correct on 3 simulated days → Ice cold; one miss → Cold.
- offline test: 20 answers with network off, then on → 20 rows in Supabase, 0 duplicates.
Sign-off: Codex + council (≥ 8/10).

### M6 — Homework suggestion sheet
Build: after each lesson, ≤ 10 items (sentences to say, words to use, one mini-dialogue) built from Missed + new + reused words; Amal keeps/edits/drops on the same token page as M4 (one extra screen); her edits become rules.
Gate: 0 items using untaught words; Medi as stand-in edits in ≤ 1 min; edits persist and change the next sheet.
Sign-off: Codex.

### M7 — One interface
Build: single URL `docs/index.html` with tabs: Today · Lessons · Words (grip table, search, buckets) · Flashcards · Amal (links + rules log) · Grammar (reference from Doc grammar sections + wiki) · Future projects (the 4 items). Same design system as the lesson pages.
Gate: every tab reachable in ≤ 2 taps; Lighthouse mobile performance ≥ 80; dark/light; no dead links (crawler test); loads with Supabase down (shows cached data + banner).
Sign-off: Codex.

### M8 — Hardening, morning checklist, handoff
Build: pipeline tests (failed split, missing chat, git push failure, ElevenLabs 429 with 3 retries + failure email to Medi, empty transcript, English-only call); budget guards; `plan/MORNING-CHECKLIST.md` (10 steps, ≤ 20 min, each step has a pass/fail line and what to do if fail, including "do NOT send Amal the link"); `plan/HANDOFF-2026-09-05.md` (what shipped, what is BLOCKED and why, costs spent, next 3 actions).
Gate: `pytest` ≥ 40 tests green; the checklist executed once by the run itself with output pasted; Codex full-repo audit with 0 open P0; council final ≥ 8/10.
Sign-off: Codex + council.

## 4. Amal UX rules (apply to M3, M4, M6; violating one fails the gate)

- English UI, her Arabizi for words, Arabic script as a small second line.
- One question per screen. One tap to play audio. Buttons ≥ 48 px, ≤ 4 per screen, text on every button.
- No login, no app, no typing required except the topic field. Works on a phone in the browser.
- Progress shown ("2 of 4"), can quit any time, everything auto-saved, ≤ 5 min total.
- The page says who is asking and why in one sentence at the top: "Medi's app has 4 quick questions about today's lesson."
- The word "suggest" appears on every planner/homework screen; her choice always wins.

## 5. Morning handoff to Medi (what the run leaves)

1. `plan/MORNING-CHECKLIST.md` (≤ 20 min) with the two Amal links pre-generated but NOT sent.
2. `plan/HANDOFF-2026-09-05.md` with DONE / BLOCKED per milestone, costs, and the exact one-sentence message Medi can paste to Amal.
3. `plan/OVERNIGHT-LOG.md` with every gate output, Codex findings, council scores.
4. Reports for Aug 25 and Sep 4 already emailed to Medi.

## 6. Definition of "done" for the whole run

All eight milestones DONE, or any BLOCKED milestone has a written cause and a next action; both hard-limit budgets respected; Codex final audit has 0 open P0; council final ≥ 8/10; checklist executed once by the run.
