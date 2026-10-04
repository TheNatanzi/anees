# Codex (gpt-5.5) review: how to raise Gemini's score on the 10-02 benchmark (2026-10-04, read-only)

Asked with C:/Claude/reports/ANEES-CODEX-IMPROVE-GEMINI-PROMPT-2026-10-04.md. Its findings, kept as returned. Ideas, not proof:
nothing here is applied without its own test.

## (a) Scoring faults

| Fault | Where | Moments | Baseline would move |
|---|---|---|---|
| Too strict on بدو vs بده: the Arabizi field (`alt` = biddo) is read only when the truth is in Latin letters, so it cannot rescue هو بده | scripts/bench_score.py:67, :77 | M042 | 53 -> 54 if accepted |
| Too strict on a cut-off Arabic prefix: Gemini wrote المصـ--, the scorer wants the full المصاري | scripts/bench_score.py:67 | M025 | 53 -> 54 if a cut-off is accepted |
| el- strictness is mostly right: the article IS the slip in M027, M029, M038; loosening it would hide real slips | scripts/bench_common.py:141 | M027, M029, M038 | no change |
| The 2-of-3 rule is right to call unstable moments misses; the report should show "unstable" apart from a hard miss | scripts/bench_score.py:124 | M001, M027, M040 | an any-hit count would say 56 (too loose) |
| "Untouched line changed" measures review load, not pure harm: many rows look like real unflagged fixes | scripts/bench_rehear.py:94, scripts/bench_score.py:265 | untouched rows | heard unchanged; harm overstated by an unknown amount |

## (b) Failure type per missed or gained / lost moment

| Moment | Type | Finding |
|---|---|---|
| M001 | audio | 3asha / 3ashara, unstable; several prompts fix it |
| M004 | context pull | variables drift back to the engine's صرت; baseline wins 2 of 3 |
| M012 | output format | the vowel-marks task distracts; the letters get worse |
| M017, M018 | output format | some variables leave the Arabic word as Latin "Juma" |
| M020 | prompt / context pull | completes the cut-off ro-- into ربع |
| M025 | scoring | the raw answer has the cut-off المصـ--; the scorer wants the full word |
| M027 | audio / context pull | article edge: one hit, one خيرة, one copied الأخيرة |
| M029 | audio | drops ال in غير اليوم |
| M030 | audio | hears الغيـ / الـ-, not the full الغير |
| M038 | context pull | V7 pulls toward Amal's correction |
| M040 | audio | the start of إحنا is clipped or weak; the word list and accent note help |
| M041 | audio | أكلة for أكل |
| M042 | scoring | بده + alt "biddo" should count as بدو |
| M043, M048, M049, M050 | output format | the derived high-only rows drop the Arabic conversion and keep Latin |
| M055 | audio | V3 chooses عشر; baseline had عشرة |
| M059 | context pull | copies the nearby lesson word تاني; the key is غير |
| M061, M062 | scoring / output format | subset prompts lose the Arabizi signal needed for a Latin-letter truth |

## (c) Ranked experiments

1. No-call scorer audit columns (strict, cut-off-ok, spelling-ok, unstable-any-hit) beside the headline. $0.
2. Context-free verifier on proposed changes only: "Listen only to this clip. No lesson context. Write exactly what he said; keep cut-offs and mistakes." A change is accepted only when the context run and the blind run agree. Targets hidden slips and untouched-line harm. Cost: the proposed lines only.
3. Audio preprocessing on the short lines: normalise gain, pad 1.2 s instead of 0.6 s, try 0.9x playback - first on the 10 misses + the unstable lines only. Targets clipped starts and cut-offs (M001, M025, M027, M040).
4. A 5-run vote only where the 3 runs were unstable or near-miss. Needs the verifier of (2), or it gives more chances to copy context.
5. Split the task: first the uncertain Arabic spans as sounds (Arabizi) only, then a deterministic converter to Arabic. Test on the missed / gained / lost set first.

## (d) What not to trust

- Gemini's `confidence`, `heard` or `why` labels as evidence.
- Differences of 1-2 moments between recipes (run noise).
- A "best recipe" tuned on this one lesson.
- The untouched-lines count as pure harm.
- The Pro / OpenAI conclusions (Pro was partial; OpenAI may be a prompt mismatch).
- Trust only the broad pattern: short prompts beat bulky output; context helps but pulls toward Amal; protecting slips needs a blind audio check.
