# Pipeline test protocol (re-run after every new fully reviewed lesson)

Medi 2026-10-10: "keep this testing method documented because we are gonna run it a few more times after we grade more
lessons." This is the standing method. Each run = the same steps, the same scores, one more lesson in the table.

Companion files: the research behind it `reports/Lesson pipeline testing methods.md` (2026-10-10, 20 tests with
sources) and its notes `research_notes/Lesson pipeline testing methods/`; the two infographics (Lesson to Grade,
Pipeline Test Plan) are claude.ai artifacts linked from the 2026-10-10 chat. The grade book: `scripts/review_grades.py`,
`docs/data/review-grades.json`, AI Reports > Grades (PG-46).

## 0. Words used here

| Word | Meaning |
|---|---|
| Key | The answer key: the lesson as it is after Medi's full review (his corrections applied) |
| Practice lesson | A lesson the rules were already tuned on. Today: 10-08. Never proves anything again |
| Exam lesson | A lesson reviewed on a frozen pipeline version, no rule tuned on it before the score is taken |
| Frozen | Saved with a hash + git SHA before any test runs; a change = a new version, old scores re-run on it |
| Hit rate | Of the Arabic words Medi really said, the share the setup wrote right |
| False-correction rate (FCR) | Of Medi's real mistakes, the share the setup wrote in the tutor's correct form (erased) |
| Paired | Both versions scored on the same words of the same lesson, compared word by word |
| Drift | "Today's page vs the key" for an old lesson: a regression check only, never an accuracy score |

## 1. Before any test: the pipeline must be alive

- The hourly job published in the last 2 hours (publish guard log / `python scripts/rehear_auto.py show`).
- The lesson has its second listen applied (PG-27 chip "Second listen: applied") BEFORE Medi reviews it. A review of
  an ElevenLabs-only page grades a broken pipeline (10-09, 2026-10-10).
- Nothing in `rules/registry.json` or the marking scripts changes between "page published" and "review done" for an
  exam lesson. If it must, the lesson becomes practice.

## 2. Making a lesson an exam (one per full review)

1. Snapshot the page the moment Medi starts: `python scripts/review_grades.py freeze <date>` after adding the line
   to `data/lesson-work/review-grades/reviews.json` (`before_commit` = the publish SHA he reviewed, `full: true`).
   The hourly job should snapshot every first publish automatically (planned: "auto-freeze"); until then, record the
   SHA by hand the same day.
2. Medi reviews **50 lines blind first** (no chips shown, blank transcript), then the rest with chips. The blind
   block measures what the chips hide from him (anchoring).
3. After his review, **key error rate**: he re-listens blind to 40 random moments (20 he corrected, 20 he did not) a
   day later. Share he changes = the key's own error rate. No pipeline difference smaller than that is reportable.
4. Ownership of the key: Medi's lines and what HE said = Medi. Amal's lines, and whether a tutor line was a
   correction = Amal (30-50 moments on her portal, blind). Do not average the two; score each field against its owner.
5. `key_commit` = the page after the review + the audit that applied it. Freeze. The exam is now closed: no rule
   gets tuned on it. The NEXT reviewed lesson is the next exam.

## 3. The scores (every setup, every lesson, always paired)

| Score | What | Where |
|---|---|---|
| Words tracked right | report 1 of the grade book | `review_grades.py` |
| Mistakes by type / 100 words | missed slip, fake slip, untracked or wrong credit, misheard | `review_grades.py` |
| Hit rate | hearing setups only, on his Arabic words | bench scorer |
| FCR | hearing setups only, on the key's slips | bench scorer (to add: `bench_score.py --fcr`) |
| Slip precision / recall / F0.5 | reader setups | to add |
| Cost + minutes | $ per lesson, Amal minutes, Medi minutes | run log (`data/runs`) |

Statistics (from the research): paired on the same words; McNemar / exact sign test for right-wrong; block bootstrap
over 2-5 min segments for word scores; NO bootstrap on ~30 slips. One lesson detects about 3-6 points on words and only
23-32 points on slips; three lessons about 2-3.5 and 13-19. So: hearing is decided per lesson; readers and model tiers
only after 3 exam lessons. 10 variants at p<.05 = 40% chance of a fake winner: a dev win is a candidate, confirmed once
on the next exam, then adopted. Pass bars written down before the run.

## 4. The layered tests (run in this order)

| Layer | Test | How | Cost |
|---|---|---|---|
| Key | Key error rate (section 2.3) | Medi blind re-listen, 40 moments | ~15 min |
| Marking alone | **Oracle marking**: run `word_coverage` + readers on the KEY transcript (hearing removed) | marks still wrong = the rules' own error | $0 |
| Readers alone | **Injected errors**: take the key text, swap ~30 words to known wrong forms + add a fake tutor recast; do the readers catch them? | text only, no new lesson needed | Claude usage |
| Readers | **Self-agreement**: Opus x5, same prompt; measure run-to-run agreement BEFORE comparing tiers | sets how many runs each tier needs | Claude usage |
| Hearing | **Harness with switches** (section 5), every cell on the same frozen clips | engine outputs cached by (audio hash, engine, model, prompt hash) | $8-15 / lesson |
| Hearing | Context given to Gemini: none / his turns / full / full with the tutor's form masked | measures the pull toward Amal's words | inside the harness |
| Readers | Tier x effort: Fable 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5, pinned effort, same frozen prompt, 3-5 runs; plus Haiku x3 vote; plus Claude + GPT-5.5 mixed panel | only after 3 exam lessons | Claude usage |
| Timing | Forced alignment for text that comes from Gemini: 30-50 hand-marked lines, % boundaries within 100 ms | needed by any Gemini-first setup | ~2 h |

## 5. The hearing harness: switches, not bespoke pipelines

One script, five switches. Every setup Medi named is a cell; the missing cells are free to add.

| Switch | Values |
|---|---|
| Who proposes the words | ElevenLabs / Gemini / Deepgram / Cohere Transcribe Arabic / several |
| Who cuts the lines | ElevenLabs word times / whole track + forced alignment |
| How disagreements are settled | none / majority vote / second listen on disputed clips only / judge |
| Who judges, and how | Gemini / another family; ALWAYS blind: "version X / version Y", order swapped, no engine names |
| Context given to the listener | none / his turns / full / tutor's form masked |
| Number of Gemini listens | 1 / 2 (keep what both agree on) / 3 (2-of-3) |

Medi's named cells (2026-10-10):

| Cell | Setting |
|---|---|
| A (today) | ElevenLabs proposes + cuts; Gemini re-hears his lines x3; 2-of-3; full context |
| B | Gemini proposes on the whole track; ElevenLabs only for timing |
| C | ElevenLabs + Deepgram + Gemini vote; Gemini rules only where they disagree |
| D | Gemini first, ElevenLabs second opinion, a third listen breaks ties |
| E | Gemini 1 listen vs 2 listens (keep words both agree on) |
| F | Gemini + ElevenLabs each do the whole lesson; where they differ, BOTH listen again to that clip; then Gemini hears it with both versions + reasons and decides (ElevenLabs cannot write reasons: its side = its second-listen version). Judge blind as above. |

Standing safety rule in every cell: a final pick that matches a word the tutor says or types within 30 s goes to
Amal's portal first (TR-27), never straight to the page.

## 6. Decision rule

Adopt a change only when ALL hold: (1) it wins on the practice lesson by more than the key error rate and the paired
test's bar; (2) it wins again on the next exam lesson (totals only, never read error by error); (3) FCR did not rise;
(4) cost and human minutes are within the written budget. Record the decision and both lessons' numbers in
`docs/data/review-grades.json` (planned field `experiments`) so the Grades tab shows the trend.

## 7. Run log (append one row per run)

| Date | Exam lesson | Key error rate | Setups run | Winner | Confirmed on | Adopted? | Notes |
|---|---|---|---|---|---|---|---|
| 2026-10-10 | 10-08 (practice only) | not measured | A only (today) | - | - | - | protocol written; 10-09 waits for its second listen to be published |
