# Permanent decisions — September 21, 2026

This file is the permanent session record for decisions made while auditing the Word Bank and beginning Progress & Stats. It supplements `plan/word-bank-specification.md` and `docs/word-bank-review-rules.md`. When an older note conflicts with this file, this file wins.

## Progress & Stats

- The exact visual source is Stitch screen `web application/stitch/projects/7225636314948596133/screens/d36a5029632e4f8fa37eb6378f590acf`.
- Before rebuilding, interview Medi about every box, one question per message.
- Preserve the Stitch layout, section order, card structure, charts, and visual hierarchy unless Medi explicitly changes an element.
- Do not interpret “broad data stats” as permission to remove sections. It means aggregate data rather than individual-word rows.
- Specific words, their histories, and their individual decay state stay in Word Bank.
- Timing-related fluency measures belong in the Fluency area. Tutor workflows belong in Tutor Hub. Where a Stitch box conflicts with these boundaries, ask Medi rather than replacing it.
- The Progress implementations in commits `a2e9199` and `8ee0309` are rejected design interpretations. Their code may be reused only after the box-by-box specification is settled.

## Vocabulary inventory and new words

- All words already in Amal's vocabulary document are words Medi has studied.
- A “new word” is one Amal intentionally adds to that document. A transcript discovery is not automatically a new Word Bank entry.
- Amal's vocabulary document remains the source of truth. Wait 24 hours after a lesson, prepare a deduplicated missing-word review, and let Amal decide and enter approved words.

## One retrieval episode, one result

- Repetitions, stutters, rehearsal, comments about a just-supplied word, and immediate echoes do not create extra attempts.
- A repeated word after the original scored event does not receive a second success.
- Self-correction before tutor help receives one full-credit result and a self-corrected note. The abandoned form is not a second miss.
- A repair after a tutor hint receives partial credit.
- Prepared homework is not automatically assisted.
- A tutor's use of a word in a question is not automatically a hint.
- Amal may repeat a correct answer. `mm`, `mm-hmm`, `mumtaz`, `sa7`, or equivalent confirmation is evidence that the preceding answer may be correct rather than corrected.

## Context determines the target

- Determine the intended target from the full exchange, not token matching.
- In `shu ya3ni ree7a?`, the unknown target is `ree7a`; `shu` and `ya3ni` are not wrong.
- A clarification such as `uh, shu?` is not a failed recall of `shu`.
- `al2an` used while trying to say `alwan` is a lexical error established by the colors context.
- `Nejme` followed by an attempt at the plural is one plural-retrieval episode; the repeated singular/comment about the name is not another scored success.
- Keep homographs and different meanings separate. A surface match does not establish the intended sense.

## Wrong substitutions and pronunciation

- When Medi supplies one vocabulary item and Amal corrects it to a different intended item, link one incident and score both actual and intended vocabulary entries wrong. Only the actually spoken item updates Last Said.
- For the reviewed `safra` versus `safar` exchange, both are wrong in that incident. Amal's supplied correction and Medi's repetition do not add another attempt.
- A confirmed wrong pronunciation receives 0. ASR corruption by itself is not proof of wrong pronunciation.
- Medi confirmed `8amee2` versus `8aame2` should be wrong even though ASR wrote `kmy`; preserve the raw ASR alongside the repaired transcript.
- `bluz` is shirt; do not create a different vocabulary item from a broken ASR fragment.
- `el-yom` variants should not be marked wrong merely due to transcription or spelling.
- In the cited white-shirt exchange, there is no evidence that `Abyad` is wrong.

## Vocabulary versus grammar

- Standalone prepositions and prepositional constructions are grammar. Exclude them from vocabulary scoring and the default Word Bank, while retaining their evidence for grammar review.
- `ala al-yamin` corrected to `la el-yameen` is a grammar/preposition issue; `yameen` remains vocabulary.
- Agreement, person, tense, attached pronouns, and word order corrections are grammar-only unless a separate lexical error is clearly established.
- Grammar-only events are null for vocabulary: no points, no scored-attempt increment, no streak/window change, and no mastery evidence.
- A mixed incident keeps the lexical score and separately records grammar.

## Transcript, Arabic, and Arabizi

- Preserve immutable source rows, timestamps, speakers, recording fingerprints, and original ASR/transcript text.
- Establish the most accurate Arabic first, then derive the displayed Arabizi using Amal's house spelling. Do not invent Arabizi from uncertain unvowelled Arabic.
- A repair must bind to the correct original source row. Preserve the original text as evidence.
- Merge consecutive fragments from the same speaker into readable turns/sentences while retaining provenance.
- Keep Arabic script left-aligned alongside Arabizi.
- Missing evidence stays ignored/pending with a specific reason. Do not use blanket `provisional` labels.

## Transcript colors and audio

- Highlight only the assessed span, not the entire sentence.
- Correct learner span: green.
- Partial learner span: orange.
- Wrong learner span: red.
- Supported Amal correction or confirmation: blue.
- Ordinary transcript text: neutral.
- Every available excerpt uses a traditional native audio player with play/pause, seek bar, duration/time, and volume.
- A loaded audio file is not proof that every participant is present. Identify partial coverage.

## Demonstrated grades

- Independent correct recall: 1.
- Correct after a hint: 0.5.
- Confirmed wrong or failed recall: 0.
- Immediate supplied-answer repetition: excluded.
- Grammar-only or unresolved evidence: excluded/null.
- Before 10 attempts, use the approved starting/streak transitions in `plan/word-bank-specification.md`.
- From attempt 10, use the latest 10 eligible attempts. Mastered requires at least 90% and full-credit evidence across at least two lessons; 75–89% is Good, 50–74% is Shaky, and below 50% is Wrong.
- Verb tenses score separately. Noun singular and plural score separately. Masculine/feminine share the singular entry. Spoken and flashcard tracks remain separate.

## Memory estimate

- Keep memory decay separate from demonstrated vocabulary grade.
- Base bands: Strong under 14 days, Fading 14–20 days, At risk 21–34 days, High risk 35+ days.
- Only full-credit recall restarts the clock. Hints, misses, tutor speech, and echoes do not.
- No scored attempts is `Not yet checked`; attempts without a full-credit success is `No successful recall`.
- The current adaptive extension is a conservative heuristic, not a calibrated probability: two successful longer gaps can extend the window up to 2×; a miss removes the extension and applies at least At risk; a hint applies at least Fading.
- Individual memory state belongs in Word Bank. A future unified score has been discussed but is not approved yet.

## Canonical references

- Full Word Bank behavior: `plan/word-bank-specification.md`
- Concise review rules: `docs/word-bank-review-rules.md`
- Memory implementation: `docs/js/vocabulary-memory.js`
- Context scoring implementation: `docs/js/word-bank-core.js`
- Manual overlays: `docs/data/word-bank-review.json`

