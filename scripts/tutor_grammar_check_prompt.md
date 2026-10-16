You check ONE grammar rule card that Claude made from something a Levantine Arabic tutor (Amal) taught her student. Answer
with ONE JSON object and nothing else:

{"new": true | false,
 "covered_by": "<the id of the existing rule or proposal that already says this>" | null,
 "why": "<one short sentence>",
 "examples": [{"line": "<a line id like L3>", "arabic": "<words copied EXACTLY from that line>", "english": "<meaning>"}]}

1. Is the card really NEW? "new": false only when one rule or proposal below already teaches the same thing (the same
   words, the same choice for the learner) - then give its id in "covered_by". A rule that is only near (same topic,
   different choice) is new: "new": true, "covered_by": null.
2. Examples: up to 4 sentences of HERS from the lines below that USE this rule (not just mention a word in it). Copy the
   Arabic exactly as the line has it - a whole short sentence, or the part of a long line that shows the rule. Use L0 (the
   line she taught it on) only if it holds a real sentence. No line fits: "examples": []. Never write an example yourself.

The card: {card}
She said (her words): {quote}
Her whole line: {line}

The existing rules (id, name, one line):
{rules}

Already proposed:
{proposed}

Her lines from all lessons ([id] date mm:ss: words):
{lines}
