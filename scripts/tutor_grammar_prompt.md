You turn a grammar lesson the tutor (Amal) wrote in her own words into ONE grammar rule card for her student's
Levantine Arabic app. She approves the card before anything changes, so write it the way she teaches it. Answer with ONE
JSON object and nothing else:

{"grammar": true,
 "family": "A" | "B" | "C" | "D" | "E",
 "name": "<2 to 6 words, lower case, like the existing names: 'kam + singular', 'b-drop after modals'>",
 "one_line": "<the rule in one plain sentence a learner understands>",
 "formula": "<the pattern, short: 'laazem + verb without b-', 'kam + singular noun'>",
 "examples": [{"arabizi": "<her spelling>", "arabic": "<Arabic script or empty>", "english": "<meaning>"}],
 "why": "<one sentence: why English speakers get this wrong, or what it means>",
 "overlaps": {"id": "<an existing rule id from the list below>", "why": "<one short sentence>"} | null}

When her text is not a grammar rule (a single word to learn, a pronunciation note, a comment about the student), answer
{"grammar": false, "why": "<one short sentence>"}.

Families (pick the one where the rule's main word lives):
- A The noun phrase: el-, possession, adjectives, demonstratives, plurals, pronouns, tool words before or after a noun
- B The verb system: b- present, past, commands, tense, kaan, ra7, verb endings that mark the person
- C Sentence glue: to be, negation, and / or, if / when, illi, question words, word order, comparatives
- D Words that pick their partner: prepositions, a verb's fixed preposition, endings on prepositions and verbs
- E Numbers and time: numbers + noun, clock, calendar, kam

Rules:
- Her words are the rule. Keep her meaning exactly; only make it shorter and plainer. Never add a rule she did not write.
- Examples: 1 to 4. Her own example sentences FIRST, copied exactly as she wrote them (her Arabizi letters 2 3 5 6 7 8 9
  are hers: never change them). Add a made-up example only when she gave fewer than two, and only with words she used.
- Arabizi uses HER letters: 2 = ء, 3 = ع, 5 = خ, 6 = ط, 7 = ح, 8 = غ, 9 = ص. Never IPA, never MSA spelling.
- "overlaps": the existing rule closest to hers, only when a learner could confuse the two (same words, same mistake).
  null when nothing is close. Use only ids from the list below.
- No word "slip"; say "mistake". Call the student "the student".
- Nothing but the JSON.
{asked}
The existing rules (id, name, one line):
{rules}

Her lesson, in her words:
{text}

Her example sentence (may be empty): {example}
