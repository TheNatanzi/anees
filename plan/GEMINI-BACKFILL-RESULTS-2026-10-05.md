# Anees: Gemini second listen, morning report (2026-10-05)

**Everything is built on a work copy and nothing is published: both reviewers say yes if you pass one 10-minute listen check.**

- Work copy = branch `engine-bench` at `39007d3`. Live site = `master` at `df01290`, untouched.
- "Second listen" = Gemini re-hears your own microphone, with the lesson around it.
- "Slip" = one row where you said something wrong.

## 1. Where it stands

| Step | State |
|---|---|
| Re-hear all 18 lessons | Done |
| ElevenLabs' raw files | 319 checked, 0 changed |
| Your own corrections | All kept (121 earlier rows identical) |
| Codex review | Approve after 6 rounds, with a condition |
| Council review (5 AI advisors) | Approve with conditions, confidence 7 of 10 |
| The condition | Your listen check (decision 1) |
| Published | No |

The gate, set by the council before anyone listened:

| Lines where you answer "I said it wrong" | What happens |
|---|---|
| 0 to 3 | Publish |
| 4 to 7 | Those changed lines are taken back out; Grammar % marked provisional; then publish |
| 8 or more | Do not publish; widen the hold rule first |

## 2. Gemini on its own: missed by one

![Gemini-only test](../reports/img/ANEES-GEMINI-BACKFILL-CHART-1-gemini-only-test-2026-10-05.png)

| Check (lesson 10-02) | Gemini only | Result |
|---|---|---|
| Corrected moments heard right | 53 of 63 | Not passed (pass mark 54) |
| Your slips hidden | 1 | OK (same as today's way) |
| Your lines starting within 1 second | 97.4 % | OK |
| Untouched lines with a word changed | 79 (today's way: 59) | Worse |
| Cost | $2.67 | |

- It ran without Amal's typed chat, which may have cost it the one point.
- So the agreed fallback was used: Gemini's words on ElevenLabs' line timing.

## 3. What the second listen changed

![Lines changed per lesson](../reports/img/ANEES-GEMINI-BACKFILL-CHART-2-lines-changed-per-lesson-2026-10-05.png)

| What | Number |
|---|---|
| Your lines changed | 3,158 (3,169 at first, 11 taken back out) |
| With a different word | 1,580 |
| Alphabet only (same words, other alphabet) | 1,578 |
| Lines left alone because you had corrected them | 94 |
| Lines held for a check (AI runs not sure) | 84 |

On your own answer key (lesson 10-02):

| Check | Result |
|---|---|
| Your corrections right in the new transcript | 52 of 63 (ElevenLabs alone: 4) |
| Your slips hidden in the new transcript | 0 |
| Untouched lines with a word changed | 49 |

Blind spot check (a model listens without knowing which text is old or new):

| 60 changed lines | Count |
|---|---|
| New text preferred | 49 |
| Old text preferred | 11 (all 11 taken back out) |

- Three lessons have no separate microphone track: 08-25, 09-04, 09-18.
- There only alphabet changes went in. Status: "Second listen: limited (mixed recording)".

## 4. Slips after the new read

Three AI readers re-read all 18 lessons on the new transcript.

![What happened to the old slips](../reports/img/ANEES-GEMINI-BACKFILL-CHART-5-what-happened-to-old-slips-2026-10-05.png)

| | Live site | Work copy |
|---|---|---|
| Slip rows | 1,161 | 1,119 |
| Rows that count in a score | 939 | 960 |

| Label on the work copy | Count |
|---|---|
| "Needs a check" slips (first read only) | 139 rows, 125 cards on the Lessons page |
| Possible double counts (same slip in Arabic and English letters) | 47 |
| Slips Amal confirmed, kept even though not written again | 56 |
| Moments Amal already ruled on, sent to you instead of her | 15 |
| Word credits marked "needs a look" | 28 |
| Amal's portal at publish | 135 items added, 118 removed |

- Also fixed: the grammar-use counter read an older copy on five lessons. It now reads the same lines as the lesson pages.

## 5. Grammar % and Words %

Every trend chart carries the mark "method changed 2026-10-05, not comparable".

![Grammar % live vs work copy](../reports/img/ANEES-GEMINI-BACKFILL-CHART-3-grammar-pct-live-vs-work-copy-2026-10-05.png)

![Words % live vs work copy](../reports/img/ANEES-GEMINI-BACKFILL-CHART-4-words-pct-live-vs-work-copy-2026-10-05.png)

- The higher numbers are mostly the new read, not progress.
- Proof: the three lessons with almost no re-heard lines still lost 50 slip rows.
- Grammar % is provisional (≈) on 15 of 18 lessons.

## 6. Every lesson

| Lesson | Status | Lines changed (words / alphabet) | Your corrections kept | Held lines | Slips live -> work | Words % live -> work | Grammar % live -> work | Gemini $ |
|---|---|---|---|---|---|---|---|---|
| 08-25 | Limited | 12 (0 / 12) | 0 | 0 (+99 mixed) | 75 -> 74 | 76.6 -> 77.1 | 89.1 -> ≈89.4 | 1.23 |
| 09-04 | Limited | 15 (0 / 15) | 0 | 1 (+387 mixed) | 80 -> 80 | 66.7 -> 70.5 | 70.1 -> ≈71.7 | 2.78 |
| 09-05 | Applied | 206 (71 / 135) | 1 | 6 | 48 -> 51 | 78.7 -> 79.8 | 76.9 -> ≈84.3 | 1.53 |
| 09-10 | Applied | 216 (141 / 75) | 0 | 5 | 74 -> 64 | 86.4 -> 87.6 | 85.2 -> ≈86.1 | 2.19 |
| 09-11 | Applied | 192 (95 / 97) | 0 | 5 | 64 -> 64 | 83.3 -> 87.7 | 75.5 -> ≈81.1 | 1.74 |
| 09-14 | Applied | 238 (107 / 131) | 2 | 4 (+4 mixed) | 69 -> 63 | 92.9 -> 92.6 | 78.3 -> ≈81.6 | 2.12 |
| 09-15 | Applied | 233 (109 / 124) | 3 | 5 | 68 -> 63 | 79.8 -> 82.7 | 75.3 -> ≈83.9 | 1.95 |
| 09-16 | Applied | 275 (132 / 143) | 3 | 2 (+1 mixed) | 67 -> 66 | 80.4 -> 75.5 | 71.6 -> ≈84.3 | 2.51 |
| 09-17 | Applied | 223 (92 / 131) | 0 | 9 | 71 -> 65 | 85.2 -> 86.4 | 69.5 -> ≈81.7 | 2.55 |
| 09-18 | Limited | 62 (1 / 61) | 0 | 0 (+160 mixed) | 62 -> 58 | 31.8 -> 31.8 | 62.9 -> ≈73.3 | 1.72 |
| 09-19 | Applied | 126 (61 / 65) | 4 | 5 | 57 -> 49 | 62.9 -> 67.7 | 87.9 -> 95.6 | 1.35 |
| 09-21 | Applied | 311 (148 / 163) | 8 | 10 | 137 -> 125 | 83.3 -> 86.4 | 84.8 -> ≈87.7 | 3.02 |
| 09-23 | Applied | 180 (127 / 53) | 4 | 12 | 88 -> 77 | 76.0 -> 82.2 | 74.0 -> ≈86.1 | 2.39 |
| 09-26 | Applied | 243 (129 / 114) | 4 | 5 | 57 -> 60 | 87.1 -> 87.2 | 88.0 -> ≈89.2 | 2.64 |
| 09-28 | Applied | 214 (161 / 53) | 0 | 7 (+1 mixed) | 42 -> 49 | 85.7 -> 81.8 | 89.7 -> ≈90.7 | 3.03 |
| 09-30 | Applied | 173 (94 / 79) | 7 | 0 | 36 -> 37 | 86.7 -> 84.7 | 91.3 -> 91.1 | 1.83 |
| 10-01 | Applied | 127 (63 / 64) | 4 | 3 | 30 -> 31 | 92.1 -> 92.2 | 92.4 -> 93.4 | 1.60 |
| 10-02 | Applied | 112 (49 / 63) | 54 | 5 | 36 -> 43 | 84.2 -> 87.7 | 92.7 -> ≈92.5 | 1.61 |
| **All** | | **3,158 (1,580 / 1,578)** | **94** | **84 (+652 mixed)** | **1,161 -> 1,119** | | | **37.78** |

- "Limited" = no separate microphone track; "mixed" = word changes held because both voices are on one recording.
- "Your corrections kept" = lines left alone because you had already corrected them.
- 09-18's one "word" change is 01:06 مهم -> Mhm: the same word, counted by a stricter counter.

## 7. Amal's lines

| What | State |
|---|---|
| Her lines re-heard | Yes, all 18 lessons, $3.24 |
| Applied | No, none |
| Why | On lesson 09-28, 177 of her 415 lines would get a different word; many looked worse |
| What decides | She checks 40 of her own lines on her Tutor portal |
| Portal row | "Listen: which version is right?" (live on master `df01290`) |
| Results command | `python scripts/amal_listen_results.py` |

## 8. Money

![Money](../reports/img/ANEES-GEMINI-BACKFILL-CHART-6-money-2026-10-05.png)

| Gemini spend | $ |
|---|---|
| Re-hear of your lines, 18 lessons | 37.78 |
| Re-hear of Amal's lines | 3.24 |
| Gemini-only test | 2.67 |
| Blind checks and the rest | about 0.30 |
| **Total** | **43.99 of the 45 limit** |

- About 54 main Batch jobs (165 jobs in all); Google's queue took about 11 hours.
- Codex and the AI readers ran on plans already paid for.

## 9. What I got wrong

- I skipped Amal's lines against your rule, until you caught it.
- I stalled for about 11 hours after Google had finished.
- My first build let slips vanish just because the readers did not write them again. Codex caught it; they are restored.

## 10. Open decisions

**Decision 1: the 27-line council check. This is the gate.**
- About 10 minutes: https://claude.ai/artifact/W6USnaD9wc9r5ZE4YJcpHx
- These are lines where Amal confirmed a slip and the new transcript no longer shows it.
- You mark each one "I said it wrong" or "I said it right".
1. **Do it now and paste the answers back (my pick).** I apply the rule in section 1 and publish if it passes.
2. Do it later. Nothing publishes until then; the live site stays as it is.
3. Skip it and publish. Both reviewers said no to this.

**Decision 2: the 108-moment listen page. No rush.**
- https://claude.ai/artifact/PyYVoRXvQAwGsHe6dpyGBe
- 13 of your corrections that no AI run heard, 84 held lines, 11 old-or-new lines.
1. **Do it in pieces after the gate (my pick).** Paste the answers back and I apply them.
2. Leave it. The lines keep their current text and their "held" mark.

**Decision 3: Amal's lines, after her 40-line check.**
1. **Wait for her score, then choose (my pick).** Below are the three choices her score picks from.
2. Apply none: her lines stay as ElevenLabs wrote them.
3. Apply only the changes where all 3 AI runs agree.
4. Apply every change where 2 of 3 runs agree.

**Decision 4: Gemini on its own missed by one, without Amal's chat.**
1. **Drop it for now (my pick).** The fallback works and is already built.
2. Re-test with the chat, about $2. That goes past the $45 limit: only $1.01 of it is left.

**Decision 5: 28 word credits marked "needs a look" and 47 possible double counts.**
1. **Have Amal check them on her portal (my pick).** Her answer settles each one.
2. Leave them marked. The numbers stay provisional.

**Decision 6: lessons 09-11, 09-21 and 10-01 were read before 11 lines went back to the old text.**
1. **Re-read those three after the gate (my pick).** About 10 minutes of reader time, no Gemini cost.
2. Leave the advisory warning on them.

**Decision 7: Google credit.**
1. **Do not top up now (my pick).** Only needed if you want more Gemini work, such as decision 4.
2. Top up now.

## 11. Files

- Spec: `C:\Claude\reports\ANEES-GEMINI-BACKFILL-OVERNIGHT-SPEC-2026-10-04.md`
- Audit: `data/lesson-work/rehear/audit.md`
- Slips before and after: `data/lesson-work/rehear/rejudge/report.md`
- Reviewer verdicts: `data/lesson-work/rehear/reviews/`

**Your one action: do the 27-line council check and paste the answers back.**


## 12. What happened next (2026-10-07)

- The gate (decision 1) came back 12 of 27 "he said it wrong": the second listen had replaced real mistakes with the tutor's correct form. By the council rule (8 or more) the work copy was not published as it was.
- The hold rule was widened (TR-27): a change toward a word the tutor says or types within 30 s, or on a line with a mistake she confirmed, waits for her ear. Only her listen puts it in or keeps it out.
- Result on the 18 lessons: 12 gate lines back to the engine's text, 52 changes taken out on her word in all, 65 applied on her word, 223 more lines held for her new list "Listen: what did the student say? - part 2".
- Her other answers applied: 7 of the 13 own-correction lines take the AI run she picked; 14 of 28 word credits removed, 13 stand; 19 of 27 pairs are one mistake. Her own 40 lines: ElevenLabs scored higher, so none of Gemini's changes to her lines went in.
- 17 lessons were re-read by the three AI readers on the final text; the numbers on every page come from that read. Money spent today: $0.
