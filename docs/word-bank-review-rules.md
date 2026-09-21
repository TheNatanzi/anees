# Word Bank review rules

These rules preserve Medi’s corrections and apply to every occurrence, not just examples.

1. Assess the complete exchange and intended vocabulary target. A matching token alone proves neither correct usage nor an error.
2. Keep immutable Arabic/English source text, recording fingerprint, speaker and times. A transcript repair must name its source row and evidence. Never put a repair on a nearby row merely because the word is missing.
3. Derive display Arabizi from Arabic and Amal’s documented spellings. Preserve explicitly confirmed learner mispronunciations. Unknown unvowelled words remain Arabic rather than invented consonant strings. Transcription alternatives are evidence to compare, not automatic replacements.
4. One retrieval episode gets one count. Repetition, stuttering, rehearsal, quoting a correction and a comment about the just-supplied word do not create another success.
5. Wrong-word substitutions assess both actual and intended words through one linked event. Only the actually spoken word affects last-said dates.
6. Self-correction before assistance gets one correct attempt with a note. A repair after a hint earns partial credit. Repeating the supplied answer earns no new attempt. An overlapping tutor/learner repair stays unscored when its timing cannot establish which rule applies.
7. Grammar corrections—prepositions, agreement, person, tense and word order—do not become vocabulary failures. Other words in the sentence keep their own assessments. Prepositions are outside the default vocabulary view.
8. Asking shu ya3ni ree7a assesses ree7a, not shu/ya3ni. A clarification such as uh, shu? is not failed vocabulary recall.
9. Tutor use of a word in a question does not by itself prove assistance. Prepared homework does not automatically lose credit. English translation prompts alone are not hints.
10. Distinguish homographs and false ASR matches: he versus air, white versus eggs, a verb suffix versus and, and break fragments versus unrelated nouns.
11. Pending means a specific unresolved question, not a blanket provisional label. State what evidence is missing. Missing tutor audio cannot establish whether an answer was prompted.
12. Render consecutive speech as readable speaker turns while preserving source rows/times. Mark assessed learner words green, partial orange and wrong red; mark supported tutor corrections/confirmations blue. Keep ordinary transcript text neutral.
13. Every available excerpt uses native seekable audio controls. Do not reset paused playback or collapse context on an automatic data timer. Load code and styles with the current build version.

## Regression and audit

Run the Word Bank test files and `scripts/audit_word_bank_reliability.cjs` with the immutable speaking snapshot and pre-review baseline. The three global checks cover source identity, scoring/form attribution and rendering/audio binding. Pending cases additionally receive wider-context, alternative-identity/source and counterexample checks. These checks are not a claim of independent human audio verification.

Known source limit: the available September 15 tutor track starts at lesson time 22:02.868. Keep partial-coverage audio clearly identified. September 14 and 18 are not in this published release.
