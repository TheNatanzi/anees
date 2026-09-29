# Engineering audit 2026-09-29 · Areas 7 (Flashcards) and 8 (Amal's inputs)

Worker E · branch `eng-audit-e` (from `eng-audit-2026-09-29` @ 3c2835c) · worktree C:\dev\anees-eng-e.
Nothing published, nothing sent, nothing deleted. Supabase: reads only.

## Scorecard
- **7 Flashcards ⚠** FSRS-6 math is right (hand golden values match to 1e-9) and Progress & Stats numbers equal an
  independent recompute. But a test run is writing fake answers into Medi's live history tonight (90 rows so far),
  and two of the settings no longer match Medi's written 09-21 decisions (new cards/day, leech rule).
- **8 Amal's inputs ⚠** Verb check list 1 is now fully in (41 → 729). Still missing: 7 of 11 word-review answers,
  26 of 132 Quizlet sets (see below), and her 97 verb fixes left the Arabic as the app's guess.

## Area 7 · Flashcards

### FSRS-6 check (docs/js/fsrs.js)
Checked line by line against the published FSRS-6 formulas (py-fsrs 6 defaults):
| Piece | Code | Published | OK |
|---|---|---|---|
| 21 default weights | w[0..20] | py-fsrs DEFAULT_PARAMETERS | ✅ |
| decay / factor | −w20, 0.9^(1/decay)−1 | same | ✅ |
| R(t,S) | (1+F·t/S)^decay, t = whole days | same (timedelta.days) | ✅ |
| interval | round(S/F·(r^(1/decay)−1)), 1..36500 | same (py uses banker's round; only differs at exact .5) | ✅ |
| S0, D0 | w[G−1]; w4−e^(w5(G−1))+1 clamped | same | ✅ |
| D update | linear damping + mean reversion to D0(Easy) unclamped | same | ✅ |
| same-day S | S·e^(w17(G−3+w18))·S^−w19, ≥1 for Good | same | ✅ |
| recall / forget S | as published; forget capped at S/e^(w17·w18) | same | ✅ |
| learning / relearning ladder | py-fsrs step logic | same | ✅ |
| Again / Good only | rating() rejects hard/easy | spec 09-21 | ✅ |
| retention 80/85/90/95, default 90 | DEFAULTS | spec 09-21 | ✅ |
| phases New / Learning / Mature ≥ 21 d | phase() | spec 09-21 | ✅ |
| state replayed from card_results, never stored | replay() / history() | spec 09-21 | ✅ |
| undo = undone_at | readers drop undone rows | spec 09-21 | ✅ (hole closed, see fix 3) |

Golden tests with hand-computed values: `tests/test_fsrs_hand.cjs` (9). Independent script typed from the formulas
(scratch `hand_fsrs.py`), not from fsrs.js. Examples: new→Good S 2.3065 D 2.118103970459015 due +4 min; Good 4 min
later → review, interval 2 d; on-time Good → S 10.971048263078137, interval 11 d; review Again → S 0.6077016626638644,
D 7.392238132342694, relearn +4 min, then interval 1 d; mature (interval 46 d) after 2 on-time Goods. All matched.

**Rule conflicts (not changed; Medi decides):**
| Setting | Medi's 09-21 decisions (SESSION-DECISIONS, NEXT-PROMPT-flashcards-fsrs) | Code since af4d629 (09-27 "fix the bugs") |
|---|---|---|
| New cards a day | 20 | 8 (cites wiki 06 rule 2, which says "max 8 new words **per lesson**, ~25/week") |
| Learning steps | Anki/py-fsrs 1 m, 10 m; relearn 10 m | 1 m, 4 m; relearn 4 m (fits the 7-minute session) |
| Leech | 8 lapses | 4 misses in any phase **or** 8 lapses (wiki 06 rule 12) |
Progress & Stats spec (09-22) also says "Leech words = cards with ≥ 8 lapses".

### Sets (Quizlet) reconciliation
| Quantity | JSON (docs/data/quizlet/amal-quizlet-sets.json) | tests | Flashcards page | Progress & Stats |
|---|---|---|---|---|
| sets | 107 | 107 ✅ | 71 tiles + 36 dated hidden (Medi 09-22) = 107 ✅ | not shown |
| terms | 2,406 (every set's n = its term count) | 2,406 ✅ | — | — |
| blank-sided terms | 6 | 6 ✅ | skipped | — |
| cards | 2,364 = 2,406 − 6 blank − 36 repeats of one Doc word inside a set | ≤ 2,400 ✅ | 1,191 Doc words + 1,173 q: cards | q: cards named "Quizlet card …" |
Memory's "1,139 / 1,148" is from before Body Parts & Clothing (09-26); today's numbers are above. No duplicate set ids.
Amal sent 132 set links; 106 of them are imported (+ Body Parts, pasted by Medi). **26 were never imported** (Quizlet
blocked the 09-21 reader). See area 8.

### Review history (card_results) kept?
- Kept: RLS on, no DELETE policy, the page's key may only set undone_at once within 1 h ✅
  (`tests/test_card_history.py::test_history_cannot_be_deleted_from_the_app` passes). Note: table grants still list
  DELETE/TRUNCATE for anon/authenticated; RLS makes DELETE a no-op and PostgREST has no TRUNCATE. Tidy-up (optional):
  `revoke delete, truncate on card_results from anon, authenticated;`.
- Undone rows ignored everywhere: buckets.js, cards-core (queue, capNew, newToday, boostMap), cards-selection,
  flashcard-stats, flashcard-angles, word-bank-core, progress.js ✅. fsrs.replay itself only looked at `undone`
  (callers convert undone_at first, so no live number moved) → fixed.
- ❌ **Test rows in Medi's history.** tests/test_m5_cards.py drives cards.html against the LIVE table and deleted its rows
  only if every in-browser check passed. Tonight (09:14–09:54 UTC, still growing while I watched) it left **90 rows in
  10 Animals rounds**, median 237 ms per card (Medi's real rounds: 3.8–4.8 s). Real history = 111 rows
  (09-05: 7, 09-22: 104). The test also files "often wrong on flashcards" flags into amal_rules (never cleaned up;
  23 such flags sit on days with no real answers: 09-06, 09-12, 09-23, 09-27, 09-29); pull_decisions skips flags, so Amal
  never sees them.

### Progress & Stats flashcard numbers vs an independent recompute
Recomputed in Python from card_results + words.json (own FSRS code, LA local days, now = 2026-09-29 10:00 UTC) and
compared with flashcard-stats.js over the same rows. **Every number matched** (both with and without the test rows):
| Number | Real history (111 rows) | Shown now (with 81 test rows at the time) |
|---|---|---|
| answers / cards seen | 111 / 63 | 192 / 71 |
| weekly goal (distinct cards) | 0 | 9 |
| monthly goal | 63 | 71 |
| due today / unfinished first day / expected right | 57 / 32 / 52 | 59 / 35 / 54 |
| true retention (mature answers) | — (0) | — (0) |
| leeches | 0 | **2 (bese, na7el — made by the test)** |
| New (never answered) / first-answer pass | 2,091 / 77.8% (49/63) | 2,083 / 77.5% (55/71) |
| Learning cards / pass rate | 57 / 93.8% (45/48) | 65 / **76.9%** (93/121) |
| Mature cards / lapses | 6 / 0 | 6 / 0 |
| today | 0 answers | 81 answers, 66.7% |
| new cards left today (cap 8) | 8 | 0 (test used them) |
Nothing to fix in the stats code; the numbers are wrong only because the input has test rows.

## Area 8 · Amal's inputs

`python scripts/amal_inputs_check.py` prints this table live (new, read-only).
| Input | Given | Stored | Shown | Gap | Fixed? |
|---|---|---|---|---|---|
| Verb check list 1 (sTAWVw, 09-22..09-25) | 729 (632 right, 97 fixed) | 41 → **729** | 41 → **729** (Word Bank "Checked by Amal", drill tag) | 688 → **0** | ✅ cf4de48 |
| Verb check list 2 (zzKmq2, 410 forms) | 0 | 0 | 0 | 0 | ✅ nothing given; pull would have **lost** her answers → fixed 26a9fa9 |
| Slips-by-pattern review (WcvsRL, 81 patterns) | 0 (opened 09-26, nothing answered) | 0 | 0 | 0 | — |
| Word review 09-05 (zMtbHB, 14 items) | 11 | 11 (Supabase) | 4 (Word Bank rows marked human-reviewed) | **7** | ❌ not done (below) |
| Grammar-rule notes (her Doc, merged tonight) | 20 rulings (+11 rows read and kept) | 20 (data/amal-grammar-notes-2026-09-29.json) | 20 (console 20/20, lesson files 20/20) | 0 | ✅ |
| After-lesson links (09-23, 09-26, 09-28 open) | 0 | 0 | 0 | 0 | — |
| Homework verdicts | 1 | 1 | 1 (applied 09-05) | 0 | ✅ |
| Quizlet sets she sent | 132 | 106 → **125** | 106 → **125** | 26 → **7** | ✅ 19 imported (see below); 7 over-100-card sets still partial |

Verb check list 1 detail: engine vs Amal (her 729 answers): Present 535/601 = 89.0%, Past 68/84 = 81.0%,
Command 29/44 = 65.9%, all 632/729 = 86.7%. (The 09-22 hold-out numbers 93/98/95 were measured on her Doc forms, not on
her check-list answers.) Her 97 fixes changed the Latin spelling only; **all 97 left the Arabic as the app's guess**
(e.g. she fixed "byesta5dem / byesta3mel" but the Arabic still reads بيسخدم, itself a typo for بيستخدم).

Word review 09-05, the 7 not shown: u002 "yes" انبسطتي, u014 أزعجتوه, 062 ما متزجيني, 082 بشوفك (3 replacements),
u009 inaudible, u012 note "أزعج and أحرج are more used than زعج and حرج" (a rule note), medi-uncertain-001 English
sentence. They are applied only by the Speaking release rebuild (build_speaking_release.py → review_overlay), which
needs a private snapshot and data/speaking/review-interpretations.json that are not in the repo. Not done here.

Test runs that look like Amal: tests/test_m4_after.py stands in for Amal on a fresh 2026-09-04 after-link
(e.g. 7gLRzU 09:38, fDQA_q 09:55 tonight: "right"/"wrong" verdicts applied to word_events, then deleted and restored in
its finally). While it runs, those rows look like hers. amal_inputs_check excludes 09-04 links made after 09-12.

## Fixes and commits (branch eng-audit-e)
| # | Problem | Fix | Test (fails before → passes after) | Commit |
|---|---|---|---|---|
| 1 | 688 of Amal's 729 verb answers never pulled | pull + catalog rebuild (pre-pull rebuild reproduced the committed catalog byte for byte) | test_amal_inputs::test_nothing_she_answered_is_left_unpulled: "688 of 729 not pulled" → pass | cf4de48 |
| 2 | pull() built her list-2 answers and never wrote them | write data/vocab/amal_addon_checks.json (the file build_verb_addon_tags.cjs reads) | test_pull_keeps_level_2_answers: fail → pass | 26a9fa9 |
| 3 | a "yes" fell back to an unchecked guess, silently, if the engine changed later | her approved form wins | test_a_yes_survives_an_engine_change: fail → pass | 26a9fa9 |
| 4 | fsrs.replay scheduled rows with undone_at / kind "undo" if a caller forgot to convert | filter both | test_fsrs_hand.cjs (2): fail → pass | bf6d3e4 |
| 5 | leech tag "Leech · 0 lapses" on a 4-miss leech | AneesFSRS.leechLabel → "Leech · 4 misses" | test_fsrs_hand.cjs: fail → pass | bf6d3e4 |
| 6 | e2e flashcard tests left rows in Medi's live history when they failed | cleanup wraps the whole run | test_card_history::test_no_machine_speed_test_rounds_in_medis_history: FAILS until the rows are removed (Medi's OK) | f27764d |
Tests updated because Amal's answers changed the data (no threshold touched): test_catalog_gloss (basta5dem command
persons now checked by her), test_verb_drills (41 → read from her answers file).

## Changed numbers (old → new, why)
- Verb forms checked by Amal: 41 → 729 (pulled her 09-22..25 answers). Unchecked guesses: 1,564 → 876.
- Verb drill cards tagged "Checked by Amal": 41 → 729 of 2,736.
- 97 verb forms now show her spelling instead of the guess (e.g. huwwe beyaji → huwwe byiji, qaatel → 2aatel).
- verb-addons golden (Amal's 25 "Pronoun Objects With Verbs"): exact 16 → 15. Cause: her check-list fix
  humme bya5du → humme byaa5du, while her Quizlet card says "Humme bya5dook". Floor 16 **not lowered**; the test
  now fails (test_verb_addons.cjs) until Amal says which spelling is hers.
- Tutor page "Verb check · list 1 · pulled": still says 41 (see "for the coordinator").

## Decisions
For Medi (yes/no each):
1. Delete the 90 test rows (card_results, subject 'sel:all:topic:Animals', created 2026-09-29 09:14–09:55 UTC, answer_ms median 237) and the test-made "often wrong on flashcards" flags on 09-06/09-12/09-23/09-27/09-29? 
2. New cards a day: keep 8 (09-27) instead of 20 (your 09-21 decision)?
3. Leech: keep "4 misses in any phase or 8 lapses" instead of "8 lapses" (09-21)?
4. Learning steps: keep 1 m / 4 m (fits the 7-minute session) instead of 1 m / 10 m?
5. Run the flashcard/after-link e2e tests against a test copy of the database from now on, never the live one?
6. Import Amal's 26 missing Quizlet sets (list below)?
For Amal (yes/no each):
1. Your 97 verb fixes changed the Latin letters only; is the Arabic under them right too (e.g. بيسخدم)?
2. "They take you": is it bya5dook (your Quizlet) or byaa5dook (your check list)?

## For the coordinator (files I do not own)
- scripts/build_tutor_data.py line ~87 keeps `"pulled": old.get("pulled", 0)` forever, so tutor.json says 41. Compute it:
  `pulled = sum(1 for k in json.load(open(ROOT/'data/vocab/amal_verb_checks.json'))['answers'] if k in r['payload']['items'])`
  for verb-forms links (and for verb-addons links, count answers present in data/vocab/amal_addon_checks.json). Expected
  now: list 1 → 729, list 2 → 0.
- tutor.json "grammar-doc" status still reads "Not pulled into the app yet"; tonight's merge applied her notes
  (20 not counted, 11 kept) — update the status line in build_tutor_data.py if that Doc is the one the notes came from.
- Nothing I changed needs a regenerated data file other than docs/data/word-bank-catalog.json (committed, as with the
  first 41). Rebuild sentence-ladder / verb-addons in the normal order after merging if you want them fresh.

## Not done
- Word review: 7 of 11 answers not shown (needs the Speaking release rebuild with the private snapshot).
- The 90 test rows are still in the live history (need Medi's yes); test_card_history fails until then.
- test_verb_addons golden fails (16 → 15) pending Amal's answer; not lowered.
- Quizlet: 7 of Amal's sets are still missing because their public page shows only the first 100 cards:
  Broken Plurals (170), Past Tense Group 1 (507), Past Tense Group 2 (144), Past Tense Group 3 (256), normal verbs that
  get "a" (374), Normal verbs that take "e" (104), zehe2-beyzahhe2 group (89; two cards fused on the page). They need
  Medi's Chrome (logged-in Quizlet, the 09-21 __NEXT_DATA__ recipe) or a "See more" click. Not imported partially.

## Quizlet: 19 more of Amal's sets imported (2026-09-29)
Read with Firecrawl (the 09-26 recipe), complete term counts only: Daily Expressions PT1 13, Irregular Past Tenses 24,
ba2ul conjugations 37, Past Multifunctional Verbs 21, Travel PT1 14, Travel PT2 25, July 21 words 10, Weather 33,
Weather complementary phrases 16, July 27 Words 6, Everyday expressions PT2 24, PT3 9, Animals 19, Animals PT2 + Randoms 18,
babse6-banbese6 group 97, August 11 Words 9, Doubled middle (shadda) Causitive Verbs 15, Grammar Termonology 29,
T causative Verbs 16. Sets 107 → 126, terms 2,406 → 2,841, cards 2,364 → 2,797 (Doc words 1,191 → 1,427, q: cards
1,173 → 1,370), set tiles 71 → 87 (3 dated sets hidden: July 21, July 27, August 11). Blank-sided terms still 6.
Terms kept exactly as she wrote them (typos included).

## Hand-check of 5 findings
1. 688 unpulled: the online test printed "688 of 729 answers not pulled" on the pre-pull file ✅
2. 41 → 729 shown: verb-drills.js over the old / new catalog counted 41 / 729 checked cards ✅
3. Test rows: 10 rounds with median answer 237 ms, all created 09:14–09:54 UTC while Medi's rounds are 3.8–4.8 s ✅
4. Stats: 17 numbers from flashcard-stats.js equal the independent Python recompute, both inputs ✅
5. 97 fixes kept the guessed Arabic: re-counted against the pre-pull catalog (not the link payload) → 97 of 97 ✅
5 of 5 held up.
