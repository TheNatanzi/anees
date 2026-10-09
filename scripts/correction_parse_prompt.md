You read one correction the student (Medi) typed under one line of his Arabic lesson transcript and turn it into
structured rows. Answer with ONE JSON object and nothing else: {"items": [ ... ]}. Each item is one of:

- {"kind": "speaker", "who": "Amal" | "Medi"}            the line belongs to the other speaker
- {"kind": "time", "t": <seconds as a number>}            the line's time on the lesson clock is wrong
- {"kind": "missing", "word": "<word>"}                   the recording engine dropped a word he said
- {"kind": "text", "engine_wrote": "<word on the line>", "heard": "<what he really said>"}   the engine misheard
- {"kind": "add", "said": "<his wrong form>", "right": "<the right form or null>", "k": "vocab" | "grammar"}
                                                          a mistake he made that nobody marked (only on HIS lines)
- {"kind": "note", "text": "<his words>"}                 nothing above fits; keep his words

Rules:
- "engine_wrote" must be a word (or two) that appears on the line, copied exactly as it is on the line.
- Arabic script and Arabizi (2=ء 3=ع 5=خ 6=ط 7=ح 8=غ 9=ص) are both fine on either side; never change his spelling.
- "add" is his slip: "said" is what he said, "right" what it should be. "text" is the engine's error. When his words
  say "I said X" or "not Y" the engine is wrong (text); when they say "should be" with no engine words it is his slip (add).
- "k" is "grammar" only when the words point at grammar (verb, gender, plural, tense, ending, rule); else "vocab".
- One correction can carry two items (a speaker and a time). Never invent an item his words do not say.
- Nothing but the JSON.

Line (speaker {who}, at {mmss}): {line}
His correction: {text}
