# 14 — Every transcriber hides the learner's mistakes: workarounds (Codex research, 2026-09-04)

Medi's observation: all engines carry a language model that auto-corrects a learner. Codex confirmed it and ranked seven workarounds.

| Rank | Option | Detects | Misses | Cost / lesson-hour | Setup | First experiment on Aug 25 |
|---|---|---|---|---|---|---|
| 1 | **Tutor-reaction detector** (recast, "la", elicitation, repetition, learner uptake) | tutor-acknowledged pronunciation / word-choice / morphology errors | errors Amal ignores; may flag teaching repetition | $0 | 4–8 h | classify 20 corrections vs 30 controls with 2 / 5 / 10 s reaction windows; report precision + recall |
| 2 | **Allosaurus** universal phone recognition | sound substitutions hidden by word-level ASR | grammar errors that are valid sound strings; own accent errors | ~$0 local | 4–8 h | Medi–Amal phone edit distance on correction pairs vs fluent repeats |
| 3 | Greedy CTC challenger (wav2vec2 Levantine / MMS) | CTC vs Scribe grapheme disagreement | still carries priors; elgeish Levantine = one Damascene reader (mismatch); Darija model off-dialect | ~$0 local | 6–10 h | greedy-decode pre-correction Medi spans + controls; does edit distance predict labels? |
| 4 | Forced alignment / GOP | drills with a known target phrase | free conversation | ~$0 local | 12–24 h | use Amal's reformulation as target, CTC-align preceding Medi audio, GOP vs correct repeats |
| 5 | Scribe logprob + pauses | uncertainty | confidently auto-corrected morphology | $0 | 2–4 h | caution: corrections had BETTER mean logprob than controls in a rough check |
| 6 | Amal-only keyterms (two-channel) | not a detector; better tutor-side target | — | $0.25–0.49 | 4–8 h | 20 tutor slices with/without keyterms, score target-form recovery |
| 7 | Vendor verbatim modes | disfluencies | wrong conjugations | $0.13–0.40 | 2–4 h | rerun the 405 s clip set across vendors, hand-score wrong-form survival |

**Plan:** (1) build + measure the tutor-reaction detector as the primary error label; (2) run Allosaurus + greedy CTC only on Medi spans it flags, calibrated against Amal-confirmed labels.

**First experiment:** 2 / 5 / 10-second tutor-reaction classification on the 20 corrections + 30 controls already in `data/aug25/gold_selection_v2.json`.
