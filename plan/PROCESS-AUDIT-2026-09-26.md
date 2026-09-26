# Process audit - 2026-09-26 (step 7): why each miss was missed, and the rule that stops it

**The machine caught 104 of 961 rows (11 %); 15 gaps explain the other 857 misses, a 16th (wrong bucket) spoils a third of the hits, and 18 rules (below, one at a time) close them - Amal has to touch 7 of the 66 B patterns, the rest settle from her sheet, her own voice fixes, or the bucket text.**

Numbers are counted with Python over `data/full-audit-2026-09-26.json` (build 05:16, 961 rows), `data/lesson-work/full-audit/patterns.json` (66 patterns, 115 rows, 0 unplaced), the 26 `*.r3.json` files, the 26 `*.compare.json` files and `data/grammar-sweep-2026-09-24.json`. Nothing here is a guess; where the transcript is a hole I say so.

## 0. What the detector does today (read from the code, not the brief)

| piece | where | what it does |
|---|---|---|
| voice window | `scripts/audit_grammar_lessons.py` `WINDOW = 25.0` | her re-say must start within 25 s after his line (the brief calls this "the 15-second rule"; the code says 25 s; `understand_lesson.py` uses 5 s for a recast and 10 s for uptake) |
| chat window | `CHAT_BACK = 150`, `CHAT_AHEAD = 90` | a typed line looks 150 s back and 90 s ahead for his line |
| English cue | `ENGLISH_WINDOW = 20`, `english_cue()` | a rule she names in English within 20 s |
| echo match | `xscript.skel()` consonant skeleton, `align()` anchors | his word and her word must share a skeleton; a chat line needs anchors on half its words |
| self-drops | `keep_pair()` | drops "she-echoed-a-right-answer", "echoing-her", "chat-question-al" |
| what it never does | - | no vocab path at all; no tier-0 rows (it logs 232 `asks` and 270 `self_corrections` and files none); skips every Medi turn Scribe wrote in Latin (`detect_grammar_usage.py`: "Turns Scribe wrote in Latin letters are not counted here"); never ran on 09-10 or 09-18 (`docs/data/grammar-audit.json` has 11 lessons, 09-19 has 2 events) |

- Every one of the 104 hits is a speaking-grammar row: vocab 0 of 274, B rows 0 of 115, listening 1 of 74.
- On the 11 lessons it did run on, it caught 103 of 456 speaking-grammar fixes (23 %).
- Its own precision: 165 events, 110 confirmed, 55 rejected (false 21, chat-only 14, self-fix 7, vocab 7, pronunciation 3, echo 3).
- Of the 101 confirmed events with a comparable bucket, 34 are in the wrong bucket (34 %), e.g. 08-25 23:10 C2 -> D4, 09-05 48:15 B10 -> B12, 09-11 05:29 A8 -> A2.

## 1. Detector gaps - 857 misses, each in exactly one gap

| gap | misses | what would have been needed | expected by the brief? |
|---|---|---|---|
| G1 B rows: Amal gave no signal at all | 115 | a pattern list judged from context; no detector can see a signal that is not there | new |
| G2 listening drill: he misread HER sentence | 71 | mode = listening when she says the Arabic first; 09-19 alone is 35 rows | yes (small as a trap: the machine mis-filed only 1 listening row as speaking; readers disagreed on mode 8 times) |
| G3 vocab tier 0: he asked, she supplied | 77 | write the `asks` the machine already logs (232) as tier-0 rows | new |
| G4 vocab tier 3: English word inside an Arabic sentence | 6 (+6 B rows already in G1) | English token inside a mostly-Arabic line whose sheet word exists | yes, but small: 12 rows in all, not the big gap |
| G5 vocab tier 2: wrong form of a known word | 37 (+6 B rows already in G1) | a sheet word said in another shape (plural he invented, verb as noun) | yes |
| G6 vocab tier 1: wrong word / non-word | 112 | a vocab path: his word not on her sheet, her next word on it, same English | new (the biggest vocab gap) |
| G7 lesson never machine-audited (09-10, 09-18) | 84 | run the auditor on every lesson that has a transcript | new (an operations gap, not an algorithm gap) |
| G8 fix only in chat | 37 grammar (+14 vocab counted above) | chat pairing: 53 chat-fix rows, lag median 66 s (17 under 30 s, 20 in 30-120 s, 15 over 120 s, max 334 s); the 150 s window covers most of them - the pairing fails, not the window; machine caught 1 of 37 | yes, cause is different than expected |
| G9 rule named in English | 44 | a bigger cue list ("it's feminine", "which preposition", "past", "with the b"); machine caught 9 of 53 | new |
| G11 her fix more than 25 s after his line | 10 | longer window | yes (small) |
| G12 his line is Latin-transliterated by the engine | 127 | skeleton-match Latin turns; 416 of 961 rows (43 %) have his line in Latin: 09-21 59, 09-16 54, 09-18 50, 09-04 46, 09-19 42 | yes, and it is the single biggest grammar gap |
| G13 his line is a transcript hole | 24 (55 rows overall sit on a hole marker: 09-23 31, 09-16 11, 09-11 7, 09-17 6) | anchor the row on her line, confidence low, never drop | yes |
| G14 prompt-then-fix spread over 2+ turns | 45 | pair his FIRST wrong form with her LAST form across her prompts; 91 of 536 speaking-grammar fixes have 3+ voice turns between his line and hers, the machine caught 9 of those (10 %) vs 88 of 394 with 0-1 turns (22 %) | yes ("3+ turns") |
| G15 explicit "no" within 25 s, not matched | 17 | "no / لا / مش" + a re-said word counts even when the echo anchors are weak; machine caught 14 of 63 | new |
| G16 recast within 25 s, echo match failed | 51 | looser skeleton (ة/ه, ق/ء, dropped ع), one-word diffs; machine caught 59 of 184 recasts (32 %) | new |
| wrong bucket (a hit, filed wrong - not a miss) | 34 of 101 confirmed hits | file by the changed piece, always write bucket2 | yes |

- The 15 miss rows sum to 857; G10 ("no t_amal") came out empty - every miss has her line or a chat line.

- Verified gaps the brief expected: tier 3 (12 rows, small), tier 2 (43), 3+ turns (91 rows, caught 10 %), chat lag (53 rows, median 66 s), holes (55 rows), Latin (416 rows), listening (74 rows), wrong bucket (34 of 101).
- Refuted as *detector* gaps but real as *reader* traps (the third reader's 186 drops out of 644 disputes): transcript/unverifiable 80, her "no" aimed at something else 31, pronunciation S4 28, duplicate 17, self-fix 11, Amal's echo taken as a fix 10, listening 5.
- Gaps the brief did not list: never-run lessons (G7, 84), asks not written (G3, 77), no vocab path (G6, 112), the English cue list (G9, 44), and the machine's own 33 % false-event rate.
- Could not verify: any row inside 09-23 00:00-23:45 (Medi's track is missing; 31 rows there rest on her echo alone), 09-18 19:30-31:30 (his words dropped inside his English), 09-11 18:14-22:42 and 30:30-36:36, 09-16 26:46-30:50 and 1:02:48-1:09:06, 09-17 14:11-24:07 ("[speaking Arabic]"), and 09-04 where the diarization swapped Amal/Medi labels inside the verb drill.

## 2. A rule per gap, with its one-line test

| gap | rule | test (how the code or the next reader knows it is applied) |
|---|---|---|
| G7 | R1 run on every lesson | `grammar-audit.json` lists 13 lessons incl. 09-10 and 09-18 |
| G12 | R2 Latin turns are Arabic | rerun on 09-16: machine hits > 5 (today 5 of 59) |
| G6, G5 | R3 vocab path | 09-21: machine flags >= 20 of its 41 vocab-A rows (today 0) |
| G3 | R4 asks become tier-0 rows | 77 tier-0 misses -> machine has >= 60 |
| G4 | R5 English inside Arabic | the 12 known tier-3 rows flagged; 09-10 "air conditioning" (both use it) not flagged |
| G8 | R6 chat is a fix only when it differs and she did not approve aloud | 09-18 D4/D10/D15 not flagged; 09-14's 14 chat-fix rows flagged |
| G9 | R7 cue list | named-rule rows: machine >= 30 of 61 (today 9) |
| G15 | R8 "no" + re-said word | explicit-no rows: machine >= 40 of 63 (today 14) |
| G14, G11 | R9 window runs to his next Arabic line | 3+-turn rows: machine >= 30 of 91 (today 9) |
| G13 | R10 holes anchor on her line | 55 hole rows kept, all confidence low, `medi_said` = the hole marker |
| G2 | R11 listening stretch = mode listening | 09-19 11:13-1:00:35 yields 0 speaking rows |
| reader trap | R12 echo is not a fix | the 10 r3 "echo" drops reproduce as 0 candidates |
| reader trap | R13 S4 is never a row | the 28 r3 S4 drops produce F1-F3 or nothing |
| reader trap | R14 her "no" needs a target word | the 31 r3 "not a fix" drops reproduce as 0 candidates |
| wrong bucket | R15 bucket by the changed piece | wrong-bucket rate on confirmed events < 15 % (today 34 %) |
| G1 | R16 B rows go to Amal as patterns | `amal-review.json` has 66 patterns, 0 unplaced |
| G1 | R17 same-lesson evidence (conflicts with the 09-25 decision - see below) | 53 of 78 grammar-B rows carry a same-day A row in the same bucket |
| readers | R18 fourth read only where needed; R19 r3 sees the agreed list | pass 3 exists for 09-04, 09-11, 09-16, 09-17, 09-18 only; r3 files have non-empty `added` when warranted |

## 3. What Amal must rule on once vs what the system settles from her Doc

- 66 patterns hold all 115 B rows: 41 grammar patterns (78 rows), 25 vocab (37 rows); 42 patterns are a single row.
- **Amal touches 7 patterns (16 rows).** The other 59 patterns (99 rows) settle from her sheet, her own out-loud fixes of the same rule (A rows), or the bucket text she taught.
- "A rows in bucket" = how many times she fixed that same rule aloud across the 13 lessons; the cited row is one example.

### 3a. Only Amal can settle (7)

| pattern | rows | why only she can |
|---|---|---|
| p-b-kept-after-lamma-iza (B3) | 4 | she herself kept the b- after iza three times (09-05 53:49, 09-10 22:27, 09-11 24:45 - sweep doc item 1); B3 text says drop it |
| p-ykoon-in-plain-present (C1) | 3 | only 1 A row in C1; rule M6 (ykun in lamma/iza clauses) is still "planned"; her call |
| p-english-word-for-sheet-word (tier 3) | 4 | the words are on her sheet (or / Aw, eat / Kul, rice / Ruz, iranian / Irani) and she fixed English-in-Arabic aloud 6 times (09-15 32:01 flight -> طيارة, 09-23 29:48 paper -> ورقة ...) - what only she can draw is the line "switching to English on purpose" |
| p-ya3tik-el-3afye-reply | 2 | the reply Allah y3afiki is not on her sheet (grep 3afye: nothing; sheet has "congrats response | Allah ybarek fiki", a different phrase) |
| p-3ashan-for-3an | 1 | 3an is a 2-letter key my grep cannot pin on the sheet; she says whether 3ashaan is acceptable for "about" |
| p-noa3-kind-of | 1 | "kind of" on the sheet only matches Jawwi (my kind of scene); no row for the adverb |
| p-el-arabin-invented-plural (tier 2) | 1 | sheet has 3arabi (arabic / arab) but no plural row |

### 3b. Settled without her - grammar (39 patterns, 71 rows)

| bucket | patterns (rows) | A rows in bucket | one A row that already settles it |
|---|---|---|---|
| B1 | p-present-no-b (8), p-ma-plus-bare-present (2), p-see-you-reply-clipped (2) | 26 | 08-25 50:50 ما تعصب -> ما بتعصب |
| A8 | p-fem-noun-masc-adj (6) | 16 | 08-25 28:45 معصب -> معصبة |
| A2 | p-el-on-first-idafa-word (4) | 25 | 08-25 09:12 درجة حرارة -> درجة الحرارة |
| B5 | p-i-past-as-bare-he-form (3), p-msa-tum-ending (2), p-you-f-ending-on-i-verb (1) | 51 | 08-25 27:24 أعمل غلط -> عملت إشي غلط |
| A1 | p-el-missing-known-thing (3) | 16 | 08-25 58:22 بغير الجو -> بغير جو |
| A9 | p-singular-for-plural (3), p-plural-for-singular (1) | 14 | 09-10 20:41 هدول اليوم -> أيام |
| E2 | p-clock-time-3ala-number (3) | 4 | sheet row "at 1:00 | 3ala elsaa3a wa7de | على الساعة وحدة" |
| B18 | p-masc-you-to-amal (2), p-1sg-for-you-f-question, p-i-form-for-he-form, p-mixed-masc-fem-verb-form, p-we-form-of-inkasar, p-huwwe-for-heyye (1 each) | 55 | 08-25 04:22 إحنا بدأ -> بدأنا |
| A7 | p-el-missing-on-adjective (2), p-adjective-before-noun (1) | 5 | 08-25 15:31 الـ تاني مشكلة -> المشكلة التانية |
| D1 | p-fi-for-bi (2), p-wahed-min (1), p-la-for-3ala-on (1) | 18 | sheet row "at night | billail | بالليل"; 09-10 12:44 بيتي -> بـ بيتي |
| D4 | p-object-ending-dropped (2) | 39 | 08-25 23:10 يخلصهم -> يخلصوه |
| D2 | p-rann-la-for-3ala (1), p-mit7ammes-min (1) | 44 | sheet row "excited | mit7ammes | متحمس لَ" carries the preposition; 08-25 20:20 أطلبهم -> أطلب منهم |
| B12 | p-t-form-dropped (2), p-causative-heard-as-state (1) | 49 | 09-04 03:43 بهمس -> بتحمس |
| B3 | p-b-dropped-after-enno (1) | 7 | bucket text: "KEEP it after enno" |
| A3 | p-fem-t-before-ending (1) | 2 | bucket text A3; 09-04 55:30 Safarhom -> Safartom (weak: 2 A rows) |
| A10b | p-hadol-drops-el (1) | 0 | bucket text A10b "noun after hadol keeps el-"; sheet "these | Hadoal" (weak: she never fixed it aloud) |
| C4 | p-la-for-ma (1), p-ma-for-mish-participle (1) | 8 | 09-05 1:00:38 أنا انزعجت -> أنا ما انزعجت |
| D3 | p-ma-on-pronoun-3and-lost, p-min-hom-separate, p-3andak-for-3andkom (1 each) | 13 | 08-25 38:11 Alayhom -> ala binat akhui |
| E4 | p-friday-clipped (1) | 3 | 09-10 06:47 alfayn -> ألفين ستة وعشرين (sheet row for yoam el-jum3a not checked) |
| B15 | p-participle-with-verb-ending (1) | 14 | 08-25 25:47 بتضل تعصب -> ما بتضل معصبة |
| C3 | p-el-on-comparative (1) | 4 | bucket text "never el- in front"; 09-04 02:15 الأحسن طريقة -> أحسن طريقة |

### 3c. Settled without her - vocab (20 patterns, 28 rows)

| pattern | rows | sheet row (or precedent) that settles it |
|---|---|---|
| p-kam-marra-for-kaman-marra | 5 | "one more time | Kaman marra | كمان مرة" |
| p-msa-form-for-her-word (tier 2) | 3 | her sheet is Levantine (mayy, jaaj, halla2) - my script matched the wrong line, grep each before publishing |
| p-english-word-amal-also-used (tier 3) | 2 | r3 09-21: "jacket is on her sheet but she used jacket herself, so not filed" -> drop, no ruling |
| p-eish-shnu-for-shu | 2 | "what? | shu | شو" |
| p-7awalein-for-7awali (tier 2) | 1 | "around / approximately | 7awaali | حوالي" |
| p-ya2ti-for-jab | 1 | "bring | Jeeb | جيب" |
| p-sot-tawil-for-3ali | 1 | "loud / high volume | Soat 3aali | صوت عالي" |
| p-mufrad-for-only | 1 | "only / just | Bas | بس"; mufrad is not on the sheet |
| p-far2-for-mukhtalef | 1 | "different (from) | mu5talef | مختلف" |
| p-ta3al-for-goodbye | 1 | "bye (peace) | Salam | سلام" |
| p-aktar-what-else | 1 | "also / more / too | Kamaan | كمان" |
| p-barid-for-mbare7 | 1 | "yesterday | Mbaare7 | مبارح" |
| p-fata7-for-7att | 1 | "put | 7ott | حط" |
| p-3uzurti-for-sorry | 1 | "sorry | aasef | آسف" |
| p-3ajul-for-mista3jel | 1 | "in a hurry / rushed | Mista3jel | مستعجل" |
| p-bad7ak-glossed-smile | 1 | "i laugh / i smile | Ana bad7ak" lists both -> not an error, drop |
| p-days-off-for-meetings | 1 | "meeting | Ijtemaa3 | اجتماع" |
| p-year-2026-said-wrong | 1 | r3 09-21 on the same slip: "not a language error" -> drop |
| p-zbayenna-glossed-arab | 1 | "customer | Zboon | زبون" |
| p-la-sama7ti-for-law (tier 2) | 1 | "please (f) | law samahti | لو سمحتي" |

- "Settled" here means: the rule is already hers (sheet row, bucket text, or she fixed it aloud); whether a given B *instance* is scored is still the 09-25 decision (unscored until she confirms) - rule R17 asks whether same-lesson evidence may count.

## 4. Reader-loop findings

| lesson | pass 1 agree % | pass 2 agree % | pass 1 vs 2 (rows in both / union) | sweep rows both passes missed | Latin rows | hole rows |
|---|---|---|---|---|---|---|
| 08-25 | 61.8 | 80.9 | 78.9 % (56/71) | 4 | 13 | 0 |
| 09-04 | 63.2 | 48.5 | 74.6 % (47/63) | 18 | 46 | 0 |
| 09-05 | 64.6 | 61.5 | 80.0 % (36/45) | 4 | 30 | 0 |
| 09-10 | 61.8 | 66.2 | 77.9 % (53/68) | 7 | 6 | 0 |
| 09-11 | 58.5 | 55.0 | 67.8 % (40/59) | 5 | 15 | 7 |
| 09-14 | 69.7 | 61.9 | 77.3 % (51/66) | 3 | 27 | 0 |
| 09-15 | 57.9 | 54.8 | 76.7 % (46/60) | 9 | 35 | 0 |
| 09-16 | 50.0 | 63.3 | 79.6 % (43/54) | 23 | 54 | 11 |
| 09-17 | 72.4 | 62.1 | 69.2 % (45/65) | 2 | 35 | 6 |
| 09-18 | 58.7 | 70.5 | 80.0 % (36/45) | 17 | 50 | 0 |
| 09-19 | 58.3 | 70.0 | 76.9 % (40/52) | 5 | 42 | 0 |
| 09-21 | 58.7 | 50.0 | 75.8 % (97/128) | 11 | 59 | 0 |
| 09-23 | 64.3 | 68.7 | 78.6 % (55/70) | 8 | 4 | 31 |
| all | 61.5 | 61.5 | 76.2 % (645/846) | 116 | 416 | 55 |

- Two readers agree on 61.5 % of rows in either pass; pass 2 did not raise agreement (same 61.5 %).
- What they disagree on: 461 of 644 disputes (72 %) are existence (only one reader saw it); 170 are label (tier 75, kind 62, bucket 47, A vs B 24, mode 8); 13 are the same moment cut into different pieces.
- The third reader dropped 186 of 644 disputes (29 %): 80 unverifiable transcript, 31 not a fix, 28 pronunciation, 17 duplicate, 11 self-fix, 10 echo, 5 listening, 4 other.
- Each pass alone finds about 87-89 % of the union (735 and 756 of 846); 201 rows (24 %) live in only one pass, so a third pass would still add rows.
- Both passes together still missed 116 of the 480 sweep rows (24 %); the misses sit where the transcript is Latin or holed: 09-16 (23), 09-04 (18), 09-18 (17), 09-21 (11).
- Structural flaw: the third reader cannot see the agreed rows (r3 notes on 08-25, 09-05, 09-11, 09-16, 09-17, 09-23 all say "could not add, cannot see the agreed list"), so duplicates slip in and sure adds are left out (only 2 r3-added rows in 13 lessons).
- Verdict: two passes + a third reader is enough where pass-1-vs-2 is above 75 % and the transcript is clean; a fourth read is needed on 09-04, 09-11, 09-17 (agreement below 75 %) and on 09-16, 09-18 (worst sweep-miss counts) - five lessons, not thirteen.

## 5. Proposed rules, one at a time, for Medi's yes / no

1. **R1 - run the auditor on every lesson that has a transcript.** Why: 09-10 and 09-18 were never audited, 84 grammar misses are just that. Test: `grammar-audit.json` lists 13 lessons. If yes: `audit_grammar_lessons.py` runs from the lesson list, not a hard-coded set; the hourly job re-runs it when a transcript lands.

2. **R2 - a Medi line Scribe wrote in Latin letters is Arabic, not English, unless every token passes `is_english`.** Why: 416 rows (43 %) have his line in Latin and the usage counter skips them outright; 127 speaking-grammar misses. Test: rerun on 09-16 gives > 5 hits (today 5 of 59). If yes: `detect_grammar_usage.py` stops skipping Latin turns; `audit_grammar_lessons.py` skeleton-matches them (`xscript.key`).

3. **R3 - vocab path: a Medi word not on her sheet, followed within 25 s by her word that is on the sheet with the same English gloss, is a tier-1 candidate; a sheet word said in another shape (plural, verb-as-noun) is tier 2.** Why: 112 + 37 vocab-A misses, the machine has no vocab path. Test: 09-21 flags >= 20 of its 41 vocab-A rows. If yes: new `scripts/audit_vocab_lessons.py` writing `docs/data/vocab-audit.json`, verified = false until a human ticks.

4. **R4 - every ask the machine logs whose answer is a sheet word becomes a vocab-A tier-0 row.** Why: 77 tier-0 misses while `grammar-audit.json` already holds 232 asks it files nowhere. Test: machine has >= 60 of the 77. If yes: the `asks` list is emitted as rows with `signal = asked`, `tier = 0`.

5. **R5 - an English token inside a Medi line that is at least half Arabic, whose sheet word exists, and which he did not self-fix inside the turn, is a tier-3 candidate; it is skipped when Amal used the same English word within 60 s.** Why: 12 tier-3 rows; r3 ruled 09-21 "jacket" out because she used it herself. Test: the 12 known rows flagged, 09-10 "air conditioning" not flagged. If yes: tier-3 detection lands in the vocab path of R3.

6. **R6 - a chat line is a fix only if it differs from his nearest Arabic line (skeleton, 150 s back / 90 s ahead) in at most two words AND her voice did not approve (Perfect / Nice / mm-hmm / صح) in between; in a lesson where she types most target sentences (09-16: 69 chat lines, 09-18: 66, 09-19: 78) a chat line alone is never a signal.** Why: 53 chat-fix rows, the machine caught 1; r3 dropped 09-18 D4/D10/D15 for exactly this. Test: those three not flagged, 09-14's 14 chat-fix rows flagged. If yes: `align()` keeps the anchor rule and adds the approval check.

7. **R7 - widen the English cue list to what she actually says: "it's feminine / masculine", "which preposition", "past / present", "plural", "with the b / without b", "you need", "not X, Y".** Why: 61 named-rule rows, the machine caught 9. Test: >= 30 caught. If yes: `english_cue()` in `audit_grammar_lessons.py` and `META_EN` in `understand_lesson.py` share one list in `docs/data/ai_rules.json`.

8. **R8 - "no / لا / مش" from Amal followed within 25 s by a re-said word of his counts as a fix even when the echo anchors are weak.** Why: 63 explicit-no speaking-grammar rows, the machine caught 14. Test: >= 40 caught. If yes: `keep_pair()` lowers the anchor floor when a NEG cue precedes the re-say.

9. **R9 - the pairing window runs from his first wrong form to his next Arabic line, across her prompt turns (شو؟ / كمان مرة / a question); pair his FIRST wrong form with her LAST form.** Why: 91 fixes have 3+ voice turns between his line and hers, the machine caught 9 (10 %) against 22 % for 0-1 turns; 10 more sit past 25 s. Test: >= 30 of the 91 caught. If yes: `WINDOW` becomes turn-based, `REPEAT` folds the botched immediate repeat into the same event.

10. **R10 - a Medi turn that is a hole ("[speaking Arabic]", "[speaking foreign language]", missing track) followed by an Amal fix line becomes a row anchored on her line, confidence low, `medi_said` = the hole marker; it is never dropped and never scored until the clip is heard.** Why: 55 such rows (09-23 31, 09-16 11, 09-11 7, 09-17 6); 80 of the 186 r3 drops were "cannot be verified". Test: all 55 kept with confidence low. If yes: `full_audit_build.py` and `review_lesson.py` carry `hole = true`; the page shows the clip button instead of his words.

11. **R11 - inside a stretch where Amal says the Arabic first and he repeats or translates, every row is mode = listening and never touches the speaking score.** Why: 74 listening rows; 09-19 is a 50-minute listening drill (35 rows); the sweep filed 21 listening misreads. Test: 09-19 11:13-1:00:35 yields 0 speaking rows. If yes: the detector marks a stretch as listening when Amal's Arabic precedes his in > 70 % of the pairs over 2 minutes.

12. **R12 - Amal's echo is not a fix: a line equal to his (skeleton) or carrying ✓ / ممتاز / صح / mm-hmm is approval; only a differing re-say is a fix.** Why: the code already drops "she-echoed-a-right-answer"; the readers still filed 10 echoes that r3 dropped. Test: the 10 reproduce as 0 candidates. If yes: the reader brief gets the same line as the code (M1 already says a miss needs a signal).

13. **R13 - a wrong -> right pair that differs only in ع/ح/ط/ق/ء/ث/ذ, vowel length or shadda is pronunciation (F1-F3), never a word or grammar row.** Why: 28 r3 drops were S4; the Latin engine cannot even encode a shadda (09-04 basato/basatto). Test: the 28 produce F-bucket rows or nothing. If yes: `classify()` routes those diffs to F1-F3 before any A-E bucket.

14. **R14 - her "no" needs a target: it counts only when the same or next line re-says an Arabic word of his; a "no" answering his English question, a fact (time zone, the year), or content is not a fix.** Why: 31 r3 drops were "not a fix"; 21 of the machine's 165 events were false. Test: the 31 reproduce as 0 candidates. If yes: `is_ask()` and the NEG cue require a re-said Arabic token.

15. **R15 - file the bucket by the changed piece (prefix b- -> B1/B2/B3; verb ending -> B5/B18/D4; el- -> A1/A2/A7; preposition -> D1/D2), always write `bucket2`, and a reader's bucket beats the machine's.** Why: 34 of 101 confirmed machine events sit in the wrong bucket. Test: wrong-bucket rate under 15 %. If yes: `classify()` orders its checks by the diff span, and `score_grammar_detector.py` reports bucket accuracy per run.

16. **R16 - B rows never reach Amal as rows: one pattern, one ruling, all examples folded under it; her yes scores every row in the pattern, her reason becomes a rule in `ai_rules.json` and the pattern is never asked again.** Why: 115 B rows fold into 66 patterns (42 are single rows), decision C of 09-25. Test: `amal-review.json` shows 66 patterns, 0 unplaced, and each ruling writes one `amal_rules` row. If yes: the Tutor Hub page and `review_lesson.py` build from `patterns.json`, not from rows.

17. **R17 - CONFLICTS WITH THE 09-25 DECISION, needs your call: a grammar-B row whose bucket Amal fixed out loud in the same lesson is scored without asking her.** Why: 53 of 78 grammar-B rows carry a same-day A row in the same bucket (e.g. B18: 55 A rows); asking her about a rule she corrected an hour earlier is hand-holding. The 09-25 decision says B is unscored until she confirms. Test: those 53 rows show `scored_by = same-lesson A row FA-...`. If yes: only 25 grammar-B rows plus the vocab-B rows go to her page. If no: nothing changes.

18. **R18 - reader loop: two passes and a third reader by default; a fourth read only when pass-1-vs-pass-2 is under 75 % or the sweep-miss count is over 15; and the third reader sees the agreed list read-only.** Why: agreement is 61.5 % in both passes, 24 % of rows live in one pass only, and r3 could not add or dedupe in 6 lessons because the agreed rows were hidden. Test: pass 3 exists for 09-04, 09-11, 09-16, 09-17, 09-18 only; r3 files carry non-empty `added` when warranted. If yes: `THIRD-READER-BRIEF.md` adds the agreed rows (read-only), and `review_lesson.py` triggers pass 3 from the two numbers.

## 6. Existing rules these touch (no duplicates proposed)

- M1 (a miss needs a signal) - R12 and R14 restate it for readers and the NEG cue.
- M4 (keep the stumble) and S5 - R13 draws the S4 line in code.
- M6 (ykun after lamma / iza, planned) - the C1 pattern in 3a waits on it.
- M8 (wrong preposition is its own kind, partly) - R15 keeps D1/D2 by the changed piece.
- S1 (speaker = recording channel, partly) - 09-04 and 09-18 are single mixed recordings with swapped or estimated labels; no new rule, S1 built fully would remove the swap trap.
- H1 (no guessed number) - every count above is from the JSON; the two "not checked" sheet rows in 3b/3c are marked as such.

16 gaps, 18 rules.
