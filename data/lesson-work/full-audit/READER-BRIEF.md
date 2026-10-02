# Reader brief - full vocab + grammar audit (one lesson, one reader)

You are ONE independent reader. You read ONE lesson transcript from start to end and write every error you can
defend from context. Another reader does the same lesson without seeing your work; a third settles disagreements.
Be complete: a miss is worse than a low-confidence row (confidence is a field). Never guess a fact you cannot see.

## Read ONLY these files
- `data/lesson-work/full-audit/<date>.txt` - the transcript. `[mm:ss] Medi:` / `Amal:` / `CHAT Amal:` (typed in Meet chat;
  chat lines lag the voice by 30-120 s, they usually spell out a fix she just said or that he just said wrong).
- `data/lesson-work/full-audit/buckets.md` - the 57 grammar rules with their ids.
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
