# Reader brief - full vocab + grammar audit (one lesson, one reader)

You are ONE independent reader. You read ONE lesson transcript from start to end and write every error you can
defend from context. Another reader does the same lesson without seeing your work; a third settles disagreements.
Be complete: a miss is worse than a low-confidence row (confidence is a field). Never guess a fact you cannot see.

## Read ONLY these files
- `data/lesson-work/full-audit/<date>.txt` - the transcript. `[mm:ss] Medi:` / `Amal:` / `CHAT Amal:` (typed in Meet chat;
  chat lines lag the voice by 30-120 s, they usually spell out a fix she just said or that he just said wrong).
- `data/lesson-work/full-audit/buckets.md` - the 60 grammar rules with their ids (A12, C11, C12 added 2026-10-02: Medi approved
  GR-18 proposals - A12 pronoun matches who you mean (humma / heyye for the real person), C11 noun not verb after a
  preposition (bi el-tabe5), C12 a doing verb says what was done (3amalna tamreen kteer). File such fixes there, not PROPOSE).
- `data/lesson-work/full-audit/amal-sheet.txt` - her vocabulary Doc (english | arabizi | arabic | key). grep it.
- `RULES.md` - S1..S6.
Do NOT open: `data/grammar-sweep-*.json`, `plan/GRAMMAR-CORRECTION-SWEEP-*.md`, `docs/data/lessons/*.json`,
any other reader's `.r1.json` / `.r2.json` / `.r3.json`. Independence is the point.

## What to catch (Medi 2026-09-25: "I am SURE I have made WAY more vocab errors")
Walk every turn in order. For EVERY Amal turn that follows a Medi turn, ask: is she fixing something he said?
For EVERY Medi turn with Arabic in it, ask: is there a wrong word / wrong form / English filler she let pass?

**kind = vocab-A** - a VOCAB fix Amal said out loud - she supplied the word / form / told him it was wrong.
**kind = vocab-B** - a vocab error he made that Amal LET PASS (no signal from her). Judge from context. These are NOT
scored until Amal confirms; they go to her review page. Still write them - all of them.
**kind = grammar** - a grammar fix Amal said out loud (recast, named the rule, explicit "no", finished his sentence,
prompted him until he fixed it). File the bucket id from buckets.md (one id; a second id may go in `bucket2`).
Also write grammar errors she let pass as **kind = grammar-B** with a bucket.
**A real grammar correction that fits no bucket becomes a PROPOSED new bucket for Medi's yes/no; it is never dropped**
(GR-18, Medi 2026-09-25: "if it doesnt fall into a bucket lets figure out to make one"). Write `"bucket": "PROPOSE"` and
`"proposed_rule"`: one line, the rule Amal applied, in plain English with her example (e.g. "After bi / fi / min use
the noun of the action, not a verb: bi el-tabe5"). Never force a row into the nearest bucket and never leave it out
because no bucket fits. A PROPOSE row is listed for Medi on the Grammar Console and is unscored until his yes.

Vocab error tiers (field `tier`, vocab kinds only):
- **1** wrong word or a non-word (مغني for مغيم; a made-up word; the wrong verb for the meaning: بسط for انبسط is
  GRAMMAR B12 not vocab - vocab tier 1 is a different lexical item, e.g. قالت used for "wrong", مين for "who" meaning illi is grammar C7)
- **2** wrong form of a word he knows (verb used as a noun: اشتغلتهم for شغلهم; wrong plural pattern he invented;
  masc/fem form of a NOUN he knows) - if the fix is purely an ending/prefix rule from buckets.md, it is grammar, not tier 2
- **3** an English word dropped INTO an Arabic sentence when the Arabic word is on her sheet (grep amal-sheet.txt;
  quote the sheet row in `why`). NOT tier 3: he is plainly switching to English to make a point, ask a meta question,
  or the whole clause is English. NOT tier 3: the word is not on her sheet (then it is not an error at all - skip it).
  Amal already ruled on tier 3 she LET PASS (AR-1933, 2026-09-30: "it's ok to switch sometimes"): write such a row
  as vocab-B tier 3 if you see it, but know it is pre-ruled "do not correct" and never scored or sent to her again.
  A tier-3 fix she VOICED (vocab-A) still counts.

NOT errors (leave out, or note in `coverage_note` if it matters):
- S4 pronunciation: a dropped ع/ط/ق, a root letter slip (بنسبت for بنبسط) - never vocab, never grammar.
- S5 pauses, restarts, stutters, "umm".
- His own self-fix before she helps (write it only if she THEN corrected the fixed version) - grammar exactly like vocab
  (GR-22, Medi 2026-10-02 "looks like I corrected myself": 09-14 02:42 he said بيخلص then خل-- خلاص in the same turn).
  A self-fix needs his right word BEFORE hers. Look at when each WORD was said, not when the line starts: his line can
  start first and still hold her word said after her (GR-24, Medi 2026-10-02 "this is clearly a correction. I said
  Sme3et instead of s7eet": 10-02 07:02 أنا سمعت, his line 07:04 "متأخر اليوم. صحيت. That's right." ran to 07:08, her
  صحيت was at 07:06 - he repeated her word and said "That's right", so it is her recast and the slip counts). "That's
  right" / "yes" / "aha" right after her word, or her asking what his word was, means he is taking her fix.
- (GR-19, Medi 2026-10-02: "I think if she didnt correct me on voice dont factor it as a correction, she might just be
  cleaning up what I said") Amal's typed chat line alone is not a correction - she may be cleaning up what he said; a slip
  needs a voiced signal. Example 09-14 02:42: he said بيخلص, she said nothing about it, her chat line wrote "u 5allas
  mit2a55er" - not a slip. The chat only gives context (what he meant, her spelling). When she voiced the fix AND typed it,
  use the voiced signal (recast / prompt-then-fix ...).
- Amal teaching a new word he never attempted, or answering "how do you say X?" - that is a **didn't-know**, not an error:
  write it as kind = vocab-A with `signal = "asked"` and `tier = 0`.  (Medi's rule A counts every fix she voiced; a
  didn't-know is still "Amal supplied the word", so it goes on his page, but its tier 0 keeps it apart.)
- Listening drills where he MISREAD her Arabic aloud: write them with `mode = "listening"` (kept apart, still written).
- Chat lines that simply transcribe what he said right.
- (Medi 2026-10-01, from the 09-30 review) He is mid-sentence and Amal supplies the next word (he started with صديقة,
  she said "House", he built بيت صديقة خطيبتي, she said ممتاز): that is help on the way to a right answer, not a slip.
- (same) Amal says both forms are fine / explains that his version is also valid (الدرس العربي vs درس العربي): not a slip.
- (same) He applies the rule just drilled and Amal only re-phrases it a nicer way (Hadi el-shanta -> شنتة السفر هذه): not a slip.
- (same) A QUESTION about the rule ("when is it طاولة الكبير?", "is it X or Y?") is neither a slip nor a use.
- (same) He repeats the same wrong phrase and Amal fixes it once (عشرين سجاد at 09:49 and 10:05): ONE row, the first.
- (Medi 2026-10-02) "كم مرة؟" alone, right after Amal spoke, that she answers by repeating herself = he asked
  "kaman marra?" (again?), Scribe dropped "-an". Not كم + noun, not a slip.

Machine flags (echo match, cue words like "no", 15-second rule) are CLUES only. Your row must quote the actual
Medi line and the actual Amal line that prove it.

## Row fields (all strings unless noted; Arabic script as in the transcript; keep her Latin if the transcript is Latin)
```
{"id": "<mmdd>-<n>", "t": "mm:ss of Medi's line", "t_amal": "mm:ss of her fix or null",
 "medi_said": "his line (trim to the sentence)", "amal_said": "her line (trim) or null", "chat": "her typed line or null",
 "wrong": "the wrong piece", "right": "the right piece (her words; for B your best reading, marked in why)",
 "kind": "vocab-A|vocab-B|grammar|grammar-B", "tier": 0|1|2|3|null, "bucket": "A1..F3, PROPOSE, or null", "bucket2": null,
 "proposed_rule": "only when bucket is PROPOSE: the new rule in one line",
 "mode": "speaking|listening", "signal": "recast|named-rule|prompt-then-fix|explicit-no|finished-sentence|asked|none",
 "confidence": "high|medium|low", "why": "one sentence: what is wrong and how you know (quote the sheet row for tier 3)",
 "english": "what he meant, in English"}
```
Timestamps: use the `[mm:ss]` shown on his line (t) and her line (t_amal). Rows are matched across readers by
t (±5 s) and `wrong`, so copy the `wrong` piece exactly as it appears in the transcript.

## Output file
Write ONE valid JSON (UTF-8, ensure_ascii=False) to the path given in your task:
```
{"date": "...", "reader": "r1|r2", "read": "turns first..last you actually read",
 "coverage_note": "holes, Latin-transliterated stretches, swapped speaker labels, English-only stretches",
 "rows": [...]}
```
Before writing, count: how many Medi Arabic turns you read, how many rows. Put both in `counts`: {"medi_turns": n, "rows": n}.
Expect roughly 20-45 grammar rows and 10-40 vocab rows in an hour-long lesson; if you have far fewer, re-read.
Read the WHOLE file - do not stop at the first 300 lines. Use `sed -n` in chunks of ~250 lines with PYTHONIOENCODING=utf-8
or the Read tool; the file is 600-1400 lines.


## The engine can mishear him - trust Amal's echo (Medi 2026-09-26)
The transcript is speech-to-text, not audio. When Medi asks "what did I say?" (or Amal repeats his form back, often with a laugh or "شو يعني"), HER words show what he really said - use them for `medi_said` and `wrong`, and note "engine wrote X". Example 09-26 31:53: the engine wrote راسي جاب; he asked "What did I say?" and Amal answered دبا - he said daba (بدا with letters swapped), a wrong form, not the word جاب.

## Read the word from the context, not only from the engine (TR-18 / GR-25, Medi 2026-10-02)
"3ala 3ashrah cant you tell from context im saying a time? she corrects me and says el 3ashrah". Example 10-02 07:34:
Amal asked "ay sa3a?" (what time); the engine wrote على العشاء (dinner) - he said على عشرة (at ten). An answer to a
question must fit the question: a time answer is a number, so a near-sound word (عشاء / عشرة, ستة / ستي) is the engine
mishearing, not his wrong word - write `wrong` as what he said ("engine wrote X") and look at what she reacts to.
When her whole reply is "el" (الـ), she is prompting the missing el-: that is ONE voiced A1 grammar slip (prompt-then-fix),
never a vocab slip (the code re-files it, GR-25). She heard the rest as right.
When he repeats Amal's sentence right after her (her "إنت صحيت متأخر", his "أنا صرت متأخر" at 10-02 08:39 - he said
ana s7eet mit2a55er, Medi 2026-10-02 "I repeated ana se7eet mita55er"), one different word is EITHER his slip (09-23
أشكي for her أشتكي) OR the engine mishearing a near-sound (صرت / صحيت): decide from the sound and the context, write
"engine wrote X" when it is the engine, and never credit the engine's word as a word he used right.

## Echo check (TR-19, Medi 2026-10-02 "I repeated lissa back to her not this suck")
Read data/lesson-work/echo-candidates/<date>.json: each is a short reply of his, right after her short Arabic line, that
came out with no Arabic letters. Most are real English or his own Latin-letter Arabic - leave those. A sound-alike of
Arabic (her لسه؟ -> "This suck.", ببسط -> "babysit.", انبارح -> "imbare.") is the engine: treat the line as the Arabic
he said, and add it to your coverage_note as "echo: <engine words> = <Arabic>" so it joins data/lesson-work/transcript-fixes.json.
Also read its `take_verb` list (TR-20, Medi 2026-10-02 "aa5ud can never be followed by a command tense word?"): آخد (take)
takes a thing, so a verb right after it (أخد أطلع) usually means the engine misheard the noun (10-02 09:44: aa5ud 3otle).
And its `chat_pairs` (TR-21, Medi 2026-10-02 "aa5ud Etla3 makes no seanse"): Amal often TYPES the sentence he was
trying to say. Compare his line with her typed line word by word: a sound-alike with an unrelated meaning (أطلع ~ her
3otle) is the engine - note "engine wrote X"; a wrong form she types right (سفر -> asaafer) is his slip.
Amal may correct in ENGLISH (PG-22, Medi 2026-10-02 "she corrected me in english. This can happen"): 10-02 09:53 "Aw I
should travel. Aw." is her fix of his سفر -> أسافر. An English rephrase of his sentence is a voiced signal (prompt-then-fix).

## laazem needs a verb (GR-27, Medi 2026-10-03)

"you 'take' a day off, it cant be 3utle by itself." laazem (must) is followed by a verb (B2: laazem aa5ud 3otle). When his
sentence goes from laazem straight to a thing (ana laazem ... 3otle; laazem air conditioning) AND Amal then gives the verb
- in Arabic or in English ("laazem you should take") - it is ONE B2 grammar slip (wrong = his words, right = with the verb).
No slip when she only asks ("laazem shu?"), when he fixes it himself first (laazem... or b7taj), or when a time word sits
between (laazem kul el-yoam atlob). 'I need X' is b7taj X. scripts/echo_candidates.py lists these as laazem_noun.

## A repeat of the line Amal just fixed is the same moment (GR-28, Medi 2026-10-05)

When Medi says the SAME phrase again within 30 s after Amal spoke - the fixed version of the line she prompted on - it is
one moment with the slip, never a fresh correct use and never a second slip. Example: 10-02 07:34 Medi "على عشرة" (A1,
el- missing), Amal "الـ.", 07:38 Medi "على العشرة" -> one A1 slip at 07:34; the 07:38 line is 'repeat of the line Amal
just fixed', not scored. Code: scripts/detect_grammar_usage.py repeat_of_fixed(). His own self-fix with no Amal between is
GR-22, not this.

## A repeat of Amal's correction is a repeat, never a use or a credit (GR-32 / WS-31, Medi 2026-10-09)

"Mark as repeat if I am repeating one of amals corrections and dont give me credit for it ... for grammar errors that I
am being corrected and repeating the correctiong. THese should also be marked as repeat and uncounted." When Amal gives
him a form (she recasts his line, gives the fix, answers his 'how do I say', types it) and he says it back within 30 s,
that line is a REPEAT: never a fresh correct use, never a new slip, no word credit. Example: 10-08 03:55 Medi "هي بيوجع",
04:00 Amal "هي راسها بيوجع.", 04:04 "راسها بيوجع.", 04:06 Medi "هي راسها بيوجع" -> ONE C9 slip at 03:55; the 04:06 line
is a repeat. Code: scripts/word_coverage.py supplies() + scripts/detect_grammar_usage.py grammar_repeat(). The slip
itself still counts (his first try); if he says the WRONG form again after her fix and she fixes it again, that is its
own slip (10-08 02:21 عيان after her 02:00 عيانة?, fixed again at 02:22).

## Sound-alike words (TR-26, Medi 2026-10-05)

data/lesson-work/confusables.json lists the words the engine keeps swapping (3ala / ila / allah; el-3ashrah / el-3asha;
mitshajje3 / shuja3 / mit7ammes; s7eet / sme3et) with a cue per group. When the transcript shows one of a group where it
makes no sense, read the word from the sentence (TR-18) and say which one he meant.
