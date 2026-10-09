You read one correction the student (Medi) typed under one line of his Arabic lesson transcript and turn it into
structured rows. Answer with ONE JSON object and nothing else: {"items": [ ... ]}. Each item is one of:

- {"kind": "speaker", "who": "Amal" | "Medi"}            the line belongs to the other speaker
- {"kind": "time", "t": <seconds as a number>}            the line's time on the lesson clock is wrong
- {"kind": "missing", "word": "<word>"}                   the recording engine dropped a word he said
- {"kind": "text", "engine_wrote": "<words on a line>", "heard": "<what was really said>", "at": "<m:ss of that line>"}
                                                          the engine misheard (one item per line it touches)
- {"kind": "add", "said": "<his wrong form>", "right": "<the right form or null>", "k": "vocab" | "grammar"}
                                                          a mistake HE made that nobody marked (only on HIS lines)
- {"kind": "credit", "word": "<the word he wants counted>"}   he says a word he said should count / he should get credit
- {"kind": "not-use", "said": "<the word>"}               he says a correct use should NOT count (he was repeating her,
                                                          reading, or asking)
- {"kind": "note", "text": "<his words>"}                 nothing above fits (e.g. "the audio cut here", "he didn't
                                                          understand her question"); keep his words

Rules:
- The recording engine often writes his Arabic as English look-alikes or nonsense ("Defect." for keefak, "and then" for
  tamam, "PTT" for khatibti, "Elsa" for el-saa3a). When the line's words are English or nonsense and he writes "X is Y",
  "X is supposed to be Y", "X = Y", "not X, Y" or just the Arabic of the line, it is the ENGINE's error: "text" items,
  never "add". "add" only when his words say HE got it wrong ("I said X but it should be Y", "my mistake", "wrong gender").
- His sentence is often split over several short lines (he pauses while building it). "The lines around it" shows them
  with their times. Give one "text" item PER LINE it changes, each with "at" = that line's m:ss and "engine_wrote" copied
  exactly from that line; never put his whole sentence into one line, never add a word that is already on another line.
- "engine_wrote" must be words that appear on the line named by "at" (or on this line when "at" is not given), copied
  exactly. Arabic script and Arabizi (2=ء 3=ع 5=خ 6=ط 7=ح 8=غ 9=ص) are both fine for "heard"; never change his spelling.
- A note ABOUT the moment (what someone understood, that audio was cut, that a word is new for the tutor's list) is a
  "note", not a text change. "should count" / "should get credit" = "credit"; "shouldn't count" = "not-use".
- "k" is "grammar" only when the words point at grammar (verb, gender, plural, tense, ending, rule); else "vocab".
- One correction can carry several items. Never invent an item his words do not say.
- Nothing but the JSON.

The lines around it (speaker, time, text):
{context}

The line he wrote under (speaker {who}, at {mmss}): {line}
His correction: {text}
