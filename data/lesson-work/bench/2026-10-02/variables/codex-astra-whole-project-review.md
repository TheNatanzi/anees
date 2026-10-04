# Codex (gpt-6-astra, medium) whole-project review: 53 toward 60 (2026-10-04, read-only)

Asked for by Medi ("how to get it from 53 closer to 60"; "can you tell codex to use astra medium"). Kept as returned.
Ideas and estimates, not measurements: nothing here is applied without its own test.

**Its headline:** better audio boundaries and an independent first listen come first; more reasoning is unlikely to give
seven extra hits.

**A distinction it stresses:** 53 of 63 is per-moment voting, not the transcript that would be delivered. Applying
`bench_rehear`'s proposed changes and rescoring gave it 39 of 63 (2 hidden slips); with the held pile 48 of 63. (The
re-hear baseline of 2026-10-04 counted 35 and 45 with its own rule; either way the delivered transcript is well under
53.) Whole-line disagreement throws away correct pieces, and falling back to the engine keeps its hidden slip at M027.

## The five changes, ranked

| # | Change | Moments it targets | Risk | Calls and fair test |
|---|---|---|---|---|
| 1 | Recover speech boundaries before listening: longer own-microphone windows with the target interval given by time; check track alignment; extend cuts to the nearest silence instead of trusting the engine's turn boundary +-0.6 s | M040 (its engine interval is 0.54 s and Gemini reports a missing start); M001 maybe. Not M029 / M030 (inside a 9 s line) | a longer window can import words of the neighbouring utterance | same call count, more audio; choose lines by a boundary-risk rule over ALL lines, never by the missed ids; test gain / slowing apart |
| 2 | A context-free listener as a candidate GENERATOR, not only a veto: listen with no engine text, chat or teacher text, then reconcile with the context answer | M059 (context substitution), M029 / M041 (smoothing), M020 (completion), M027 | a blind listen can lose useful context or normalise too; the production gate checks only added Arabic words (not order, repeats, deletions) | +1 call per selected line; select without truth labels; compare blind Flash and the dedicated transcribe model on the same clips |
| 3 | Combine aligned spans, then verify the disputed ones: keep 2-of-3 on each span even when the rest of the line differs; for a dispute, candidates from all runs plus the blind listener, "none / fragment" allowed | M001, M027, M040; M030 needs a new candidate source | naive word voting can build a sentence nobody heard; do not release the teacher-overlap holds automatically | alignment 0 calls; +1 verify call per disputed line; replay the cached runs first |
| 4 | General preservation rules, not corrected vocabulary: replace "must fit the question" and "the rest was right" with: keep unfinished sounds, unexpected articles / endings, separate attempts | M020, M027, M029, M041, M059; protect M003, M038 | removing the context guidance wholesale may lose M004 and other real fixes | no extra calls; test V12 alone first |
| 5 | Keep spelling credit apart from hearing: M042 has "biddo" in every baseline Arabizi answer | M042 only (a measurement point, not better hearing) | a blanket ه / و rule could erase real distinctions; never relax articles or arbitrary prefixes | 0 calls; rescore every cached recipe both ways; M025 is a fragment audit, not an automatic hit |

Fairness gate for all five: freeze the selection rules before new calls; keep all 63 moments, 24 slips, 519 lines in the
report; 3 full runs of the FINAL pipeline; look at the newly changed untouched lines instead of calling each one harm;
require no newly hidden slip ids, not only an unchanged total.

## Ceiling

- Across the baseline and every variable saved, an oracle taking any successful run reaches only 58 of 63: M020, M025,
  M029, M041, M059 never hit. Voting over the saved outputs cannot reach 60.
- Its planning estimate: 57-59 strict hits; 60 is a stretch.
- M025: all baseline runs report a cut-off; if the rest was never spoken, the key's full word would be invention.
- M030 may be unfinished too (V6 hit it once). M040 is lost only if the start is missing from the recording itself.
- The files do not establish which sounds are really absent; Gemini's explanations are not an audio audit.

## Where it disagrees

- With the earlier Codex review: an agreement-only blind veto mainly lowers recall; five similar runs cannot supply a
  candidate that is never produced. M020's scoring drops the Latin fragment: its Arabic prefix followed by nonsense
  would be accepted (scripts/bench_score.py:39) - that needs a stricter diagnostic, not looser cut-off matching.
- With Gemini: temperature 0 already scored worse; V9 argues against more thinking; "attention heads" is a guess.
- With both: V3 does not settle whether longer two-speaker audio helps (it only keeps or rejects existing answers).
  V8 gained M027 / M040 but lost M004 / M017, so "no lost moment" in the code comment was wrong (corrected).
