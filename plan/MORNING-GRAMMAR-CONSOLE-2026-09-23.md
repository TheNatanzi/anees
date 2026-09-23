# Grammar Console — morning, 2026-09-23

**Not finished: the finder catches 77 of every 100 corrections on the lessons I labelled (goal 80), and 40 on a lesson it never saw.**

```
Corrections caught (recall)      before   after
  labelled lessons (09-17, 09-21)  20% ███▏        → 77% ███████████▋
  unseen lesson (09-11)            30% ████▌       → 40% ██████
Of what it flags, real (precision) 47% ███████     → 86% █████████████
Right rule named                   25% ███▊        → 85% ████████████▊
```

Live: https://thenatanzi.github.io/anees/grammar.html (pushed 82e93b1)

## Where it stopped
- **G2** (80% caught) — stopped at 77%. The misses are corrections spread over 3+ turns and ones Amal only typed in chat far from your sentence.
- **G3** (18 of 20 random finds fully right) — best was 15 of 20. About 16 of 20 are real corrections; the rest have the wrong rule.
- G0, G1, G4, G5 passed.

## Your mistakes per sentence
- Hand count, 3 lessons: **1 in 5.6** sentences has a grammar correction (1 in 4.6 with word choice).
- Your gut said 1 in 3–4. The gap is word choice plus the ones Amal lets go.
- Machine count, all 10 lessons: 1 in 8.6 — low, because it misses about 1 in 4.

## The 118 "UNFILED"
- New finder: 0 unfiled. It drops what it cannot name.
- Of the old ones in the labelled lessons (50): 13 real grammar, 4 word choice, 1 sound, 1 question, **31 not corrections at all**.

## Changes you may disagree with
- Machine finds now **count** in the numbers (they used to sit off to the side). About 85 in 100 are real.
- Your questions ("is it sarli?") feed the self-correction chart.
- Sounds (Family F) never count as grammar or as uses.
- Two gold rows relabelled: 09-17 09:39 = you fixed it yourself; 34:39 = a question.
- "Uses" come from Amal's vocabulary Doc (her verb and adjective lists).
- 8 rules show Untested: you never used them in 10 lessons (A5, B4, B7, B14, B17; F1–F3 are sounds).

## Rules I'm not sure about
- C2 vs D4 (object ending vs -la-)
- A1 / A2 / A7 (the article rules)
- B5 vs B1 (past ending vs person)
- B12, D1, D2, and Family E

**One action: open the console, tap A2 (Wrong), play 3 clips, tell me which aren't real mistakes.**
