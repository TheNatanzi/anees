# Council final approval: re-hear backfill

Date: 2026-10-05. Branch: engine-bench (not published).

**Question:** Is this backfilled data good enough to replace the ElevenLabs-based numbers everywhere on the Anees site?

**VERDICT: APPROVE WITH CONDITIONS**

**Confidence: 7/10.** A pass on the listen in condition 1 would raise it to 8–9.

How it was run: five advisors, each its own agent, each read the audit files directly. Three rounds: independent answers, anonymous critique, revision. All five are the same underlying model, so they share its blind spots; Codex is the independent second approver.

## Chairman's synthesis

**Recommendation.** Publish once, after a ten-minute listen by Medi passes, and with the numbers labelled as a method change. Nothing goes out before the listen.

**Where all five agree**
- The new transcript is much better than ElevenLabs: 52 of 63 right against 4 on the 10-02 key.
- It can be undone: 319 raw files unchanged, the 121 earlier overlay rows identical, 3,169 new rows removable.
- The drop in slips and the jump in Grammar % are mostly not caused by the re-hear:
  - The three lessons with no microphone track got one word change in total, yet fell from 217 to 167 rows. 09-18 went from 62.9 to 79.3 on one changed word.
  - The five lessons that never had the retired reader pass (09-26 to 10-02) went from 201 to 202 rows.
  - Counted uses rose from 3,225 to 3,714 while mistakes fell from 630 to 543. On 09-16 the +15 points is about +3 to +7 if the use count is held at its old value.
- So the old and new numbers cannot be compared, and the site must say so.

**Strongest argument of the whole discussion**
- 25 of the 42 slips that Amal confirmed no longer show in the new text. About 9 to 12 of those lines now read exactly as her correction (09-05 `انزعجتم` to `انزعجتوا`; 09-10 `انكسرتم` to `انكسرتوا`; 09-28 `الولاد بيكون ولاد` to `الولد بيكون ولد`).
- Either ElevenLabs invented those slips, or the new hearing smooths his speech toward the correct form. Nobody has listened.
- If it is smoothing, "1 slip hidden" understates the problem and some of the 323 removed rows are real slips. The only evidence against it comes from one lesson (1 of 24 slips hidden) and a blind check judged by the same model.
- All five advisors named a human listen on these lines as the most important condition.

**Where they disagreed**
- Text and scores published separately? Three said the text can go first; two said no, because slip rows would point at text that contradicts them. Chairman: one publish, after the listen. The listen is short, and a half-publish leaves the site inconsistent.
- The listen threshold ranged from "3 of 9" to "10 of 25". Chairman's rule is in condition 1.
- Whether the cross-lesson trend survives. One advisor said yes because all 18 were re-judged; three showed it is bent (13 lessons lost a reader pass, 5 did not; 3 were not re-heard; 5 have a partly old use count). Chairman: bent, hence conditions 2 and 3.

**Risks to watch**
- The runbook's step 20 says `amal-diff` must print "ADDED for Amal 0" before any push. The file shows 142 added and 128 removed. The owner later asked for checks to go to Amal's portal, but that override is not written down.
- The delivered 52 of 63 is below the 54 pass mark the audit set for the Gemini-only test (which scored 53 and is marked NOT PASSED). No pass mark was set for the delivered recipe.
- The blind check prefers the old text on 11 of 60 changed lines (18%; 6 of 20 on 09-21). Applied to 1,591 word-changed lines that is roughly 290 lines that may be worse, and the judge is the same model.
- 217 applied lines are word-by-word blends that no single run produced (09-21 26:31 `By كما ما.` became `By come again?`).
- "Alphabet-only" changes in the sampled plans include real word swaps ("term" to "turn", "was" to "is").
- Three of Amal's "confirm" rulings did not come back as confirmed (09-04 26:19, 09-10 12:44, 09-23 25:24).
- Spend is $43.99 of the $45 limit, so there is no room for a re-run.

**Next step.** Medi listens to the 25 lines in condition 1.

## Conditions

### Must be done BEFORE publishing

1. **Medi listens to the 25 Amal-confirmed lines whose slip vanished** (from `rejudge/kept-rows.json`), marking each "I said it wrong" or "I said it right". The rule, fixed now:
   - 0–3 said wrong: publish.
   - 4–7 said wrong: remove the overlay rows on those lines, then publish, with all Grammar % marked provisional until the hold rule is widened to cover swaps toward the teacher's form.
   - 8 or more said wrong: do not publish. Widen the hold rule and re-check first.
2. **Mark the method change on every trend and progress view**, dated 2026-10-05, saying earlier numbers are not comparable. Include the plain reason: three lessons with one word changed still lost 50 rows, so most of the drop comes from the new reader set, not from better hearing. No "improvement" wording.
3. **Flag Grammar % as provisional on eight lessons**: 09-10, 09-11, 09-15, 09-19, 09-23 (use count reads partly old text) and 08-25, 09-04, 09-18 (re-judged, not re-heard).
4. **Record the owner's override of runbook step 20** for the 142 additions to Amal's portal, in writing.
5. **Restore Amal's three confirmations** that came back reclassified (09-04 26:19, 09-10 12:44, 09-23 25:24).

### May follow after publishing

6. Point the grammar-use counter at the new text on the five lessons, then remove their provisional flag.
7. Clean up the 76 verification records and 46 patterns that point at removed rows, and settle the six old rulings and possible double counts.
8. A human listen on about 40 changed lines from a second lesson (09-21 is the weakest), since the only answer key is 10-02.
9. Mark the 217 blended lines as lower confidence, and check that "alphabet" rows on the three lessons without a microphone track change no words.
10. Amal's own lines stay unapplied until her 40-line check is back.

## Advisors' final positions

**Advisor 1, strategic. APPROVE WITH CONDITIONS, 7/10.**
- The gain is large and reversible; the listen is ten minutes, so it is a gate, not a reason to refuse.
- Withdrew the claim that the trend stays usable; accepts it is bent.
- Text and scores should go together. Listen to all 25: 0–3 pass, 4–7 revert those lines and widen the hold, 8 or more do not publish.

**Advisor 2, skeptic. APPROVE WITH CONDITIONS, 7/10.**
- The text is better, but smoothing toward the teacher's form is a live risk; nothing publishes before the listen.
- Found the runbook step 20 conflict and the 201 to 202 control. Dropped the proposed hold on b-prefix changes until the listen result is in.
- Threshold on 25 lines: 0–2 publish all, 3–5 text only, 6 or more nothing.

**Advisor 3, creative. APPROVE WITH CONDITIONS, 7/10.**
- Would let the text go now and hold scores, slip lists and portal changes for the listen.
- Found the 217 blended lines. Accepts that labels alone do not test for smoothing; dropped the git tag.
- Threshold on 25 lines: 5 or fewer pass, 6–9 restore those rows, 10 or more hold scores.

**Advisor 4, evidence. APPROVE WITH CONDITIONS, 7/10.**
- Counts reconcile: 1,161 − 323 = 838, + 128 = 966; the 42 kept rows sit inside the 838.
- Most of the Grammar jump is the use count growing; moves under about 5 points are noise given 60–83% reader agreement.
- Text and scores together. Threshold: 4 or more said wrong of the roughly 12 exact-correction lines means nothing publishes.

**Advisor 5, learner and teacher view. APPROVE WITH CONDITIONS, 7/10.**
- Found the vanished confirmed slips. Medi would see a slip card on a line that shows him saying it right, and would read the jump as progress.
- Amal's portal moves more than stated: 142 added, 128 removed, including 40 new-word items.
- Text may go first; scores wait. Threshold: 3 or more said wrong of about 9 lines holds the scores.
