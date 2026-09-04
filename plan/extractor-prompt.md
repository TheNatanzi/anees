# Anees miss-finder prompt (v0, for M0 trust test and Phase 2)

## Inputs
1. Diarized transcript: list of {t_start, t_end, speaker: tutor|learner, text_ar (script), text_translit (canonical Arabizi), text_en (if English)}.
2. Known words: rows from `words` (form_ar, translit, gloss_en, topic, status).
3. Rules: the 11 grammar rules from Amal's "Arabic Materials" doc.
4. Amal profile: qaf variant (2/g/k), kaf variant (k/ch).

## Rules for the model (from lesson-lens ideas, re-typed; Codex: minimal edits, cite exact words)
- Never invent content. Every candidate must quote the learner's exact transcript words and the tutor's exact words, with t_start.
- Preserve tutor corrections verbatim. Do not "improve" them.
- Prefer minimal edits: what changed, one word or one ending, not a rewrite.
- If the transcript line looks garbled (ASR noise), output kind=uncertain with confidence <= 0.4 instead of guessing.
- Output only the four kinds below. Nothing else counts as a struggle.

## Output: JSON array of candidates
{ kind: correction | gap | hesitation | grammar_slip | uncertain,
  t_start, learner_said (verbatim), tutor_said (verbatim or null),
  target_form_ar, target_form_translit (Amal's spelling if the word is known),
  gloss_en, rule_id (for grammar_slip; one of the 11), word_id (if matched to a known word),
  feedback_type: recast | prompt | explicit | none,
  uptake: true|false (did the learner repeat the fixed form within 30 s),
  confidence 0-1, note (<= 12 words) }

## Kinds
- correction: tutor supplies a different form right after the learner's attempt.
- gap: learner asks "how do you say / shu ya3ni / what's X" or switches to English for a content word.
- hesitation: >1.5 s pause, "um/uh/eh", or a restart before an Arabic content word the learner does know (status >= 2).
- grammar_slip: learner's form breaks one of the 11 rules even if the tutor let it pass (b-prefix, pointer pronoun, possessive el-, adjective agreement, kul, time, prepositions, bakoon...).

## M0 scoring (see plan/constants.md, Trust test M0)
- Gold sheet = 20 corrections, 10 gaps, 10 hesitations, 10 random Arabic lines, all with speaker + timestamp + 3-s clip.
- Gates: word accuracy >= 75%; speaker labels >= 90%; DER <= 15%; hesitations preserved >= 60%; extraction precision corrections >= 70%, gaps >= 70%, hesitations >= 50%. Grammar slips: measured, not gated (gate at L2 >= 60%).
