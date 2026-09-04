# 15 — Tutor-reaction detector, experiment 1 (2026-09-04)

Question (wiki 14, rank-1 workaround): after a Medi turn, does what Amal does in the next 2 / 5 / 10 s tell a correction apart from a control?

**Verdict: weak signal. Not usable yet on a one-channel transcript.** Best single cue = learner uptake (Medi repeats Amal's word): precision 0.82 / recall 0.45 at 5 s. Best combined rule = 0.50 / 0.70 (F1 0.58). Flag-everything baseline precision = 0.41. Leave-one-out AUC 0.52–0.57.

## Setup
- Script `scripts/tutor_reaction_exp.py`, output `data/aug25/tutor_reaction_results.json` (per item: anchor, Amal's words in each window, cue hits).
- Data: `gold_selection_v2.json` = 20 corrections + 30 controls (10 gap, 10 hesitation, 10 random); 49 inside the lesson window (one random control fell in the pre-class span).
- Transcript: ElevenLabs Scribe v2 forced-ara word stream; speakers mapped by overlap with the dialect reference (speaker_0 = Medi, speaker_1 = Amal).
- Anchor = the Medi → Amal hand-off at the gold chunk (end of Medi's last word before Amal's first word near the chunk; dialect chunk times run 0.5–2 s late, so the search starts 2.5 s early). Window = [anchor, +W].
- Cues (Amal's words in the window unless noted): `neg` (la / no / mish), `repeat` (Amal says a content word Medi just said), `recast` (Amal says a word ≥60 % similar to one of Medi's but not identical), `meta_en` (say / instead / means / takes …), `elicit` (شو / كيف / question mark), `confirm_open` (reply opens with ممتاز / mhm …), `uptake` (Medi repeats Amal's word within the window).

## Results (precision / recall / F1, 20 corrections vs 29 controls)

| cue | 2 s | 5 s | 10 s |
|---|---|---|---|
| neg | .43 / .15 / .22 | .33 / .15 / .21 | .27 / .15 / .19 |
| repeat | .75 / .15 / .25 | .80 / .20 / .32 | .75 / .30 / .43 |
| recast | .42 / .25 / .31 | .44 / .35 / .39 | .42 / .40 / .41 |
| meta_en | .50 / .10 / .17 | .57 / .20 / .30 | .57 / .20 / .30 |
| elicit | 0 | 0 | .09 / .05 / .07 |
| **uptake** | 1.00 / .20 / .33 | **.82 / .45 / .58** | .54 / .65 / .59 |
| confirm_open | .40 / .10 / .16 | .33 / .10 / .15 | .33 / .10 / .15 |
| neg ∨ recast ∨ repeat ∨ meta_en | .52 / .60 / .56 | **.50 / .70 / .58** | .45 / .70 / .55 |
| recast ∨ uptake | .53 / .40 / .46 | .55 / .55 / .55 | .48 / .75 / .59 |
| LOO logistic regression (all cues) | .43 / .30 / .35, AUC .52 | .64 / .45 / .53, AUC .57 | .43 / .30 / .35, AUC .57 |

Removing the 5 controls that sit within 6 s of a correction (idx 379, 758, 685, 372, 696) lifts the combined rule to .56 / .70 / .62 — still weak.

Timing: Amal answers a correction faster (0.54 s vs 0.98 s at 5 s) but with the same number of words. Not separable.

## Why it misses (the useful part)
1. **Diarization steals Amal's recast.** idx 470: Amal's three "ببسطها" are labelled Medi; idx 581 / 613: the recast sits inside Medi's run and Amal's visible reply is just "ممتاز". One microphone cannot fix this.
2. **ASR erased the error span.** idx 468: "wa2t kteer → la, wa2t taweel" was transcribed as "أنا، uh, أنا، um, بس-- بس بتـ" — nothing left to detect (LearnerVoice again).
3. **Amal corrects softly.** 3 of 20 corrections contain "la / no"; most are a bare recast, so `neg` is nearly useless. `recast` misses when Amal reformulates with a different word (idx 693: "shwai sayye2" → "لازم يكون إشي سيء كتير").
4. **Controls are not clean.** 5 controls overlap or abut a correction (idx 372 is the same span as correction 375); hesitation controls 697 and 851 are followed by real corrections. The gold set needs a re-label before a second run.
5. **Uptake is the honest cue** — but it needs a 5–10 s window and it means Medi repeated the fix, so it labels *acknowledged* corrections only.

## What this decides
- Text-only tutor-reaction on the single-channel Scribe transcript: **precision ≈ 0.5, recall ≈ 0.7 at 5 s**. Too many false alarms to email Medi automatically; fine as a *candidate* filter for a human check.
- The two failure modes (1, 2) are exactly what **two-channel recording** removes. Re-run this script on the first two-channel lesson before building anything on top.
- Keep the 5 s window (precision peaks there); use 10 s only for uptake.
- Next cheapest lift: Allosaurus phone distance on the spans the 5-s rule flags (wiki 14 rank 2), calibrated against the 20 gold corrections.
