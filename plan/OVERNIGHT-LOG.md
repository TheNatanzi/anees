# Anees overnight build log — night of 2026-09-04 → 2026-09-05

Every gate output, Codex finding, council score and paid call is pasted here, per milestone, in run order.
Budget caps: ElevenLabs ≤ $10, OpenAI ≤ $10 (stop paid calls at 90%). Running totals at the bottom.

## Setup (23:45)

- Supabase: no `anees` project existed. Both existing orgs were at the 2-free-project limit ($10/mo for a third), so a new
  free org `anees` (`ugbqljkqitaagitjefmn`) was created through the management API with the existing `SUPABASE_ACCESS_TOKEN`,
  then project `anees` = `yljcbdxvnkfrwvelypfu`, region us-west-1, free plan, $0. Keys stored in User env
  (`ANEES_SUPABASE_URL`, `ANEES_SUPABASE_ANON_KEY`, `ANEES_SUPABASE_SERVICE_KEY`, `ANEES_DB_PASSWORD`), never printed.
- Google Doc `1inA6ZeETtqJZHQYiZxtubWytsN5xh8_klQH50yRyrjw` ("Arabic Full Vocabulary list", owner amalabusrour@, modified
  2026-09-04 20:34) exported read-only through the Drive connector → `data/vocab/doc_markdown_2026-09-04.md` (2,871 lines,
  2,251 table rows, 24 H1 / 35 H2 / 12 H3 headings). The Doc was not written to.
- Unattended hourly fetch: no Google credential exists on this PC (no rclone/gcloud/clasp; the unauthenticated export URL
  returns 401, confirmed by Codex in wiki/16). See M0 for how the hourly job is wired and what is BLOCKED.

## Paid calls

| time | service | what | cost |
|---|---|---|---|

Running total: ElevenLabs $0.00 · OpenAI $0.00

## M0 — Data spine  (BUILD 23:50 → TEST 00:40)

Built: Supabase project + `supabase/migrations/001_spine.sql` (8 tables, RLS: public read, anon insert on card_results,
token-scoped read/write on amal_links/amal_rules via the X-Anees-Token header), `scripts/db.py`, `scripts/arabizi.py`
(loose / fold / short / skeleton forms + tiered Matcher that answers None on ties), `scripts/import_vocab.py` (markdown or
Google-Docs-HTML parser, one-way idempotent sync, mass-deactivate guard), `scripts/run_import_vocab.ps1` + Task Scheduler
"Anees vocab import" hourly at :35 (separate from "Anees lesson pipeline", untouched).

Gate output (`python -m pytest -q tests/test_m0_vocab.py tests/test_m0_harden.py -s`):
```
source: data/vocab/doc_markdown_2026-09-04.md
rows: 2206  words: 2120  merged duplicates: 86  topics: 20  subtopics: 41
MISSED  ishi               -> None               expected eshi
MISSED  akhui              -> None               expected a5
right 55/57  missed 2  wrong 0
test_import_counts PASSED            (2120 >= 2100; every word has arabizi/arabic/english/topic/subtopic; 0 duplicate keys)
test_spot_check_20_against_doc PASSED (random.Random(20260905) sample, 20/20 arabizi AND arabic strings found in the Doc export)
test_loose_matcher_fixture PASSED     (57 spellings: 55 right, 2 missed = None, 0 wrong; fixture tests/fixtures/medi_spellings.json)
test_sync_is_idempotent PASSED        (second sync: inserted 0 updated 0 deactivated 0; 2120 active rows in Supabase)
test_rls_token_isolation PASSED       (token A sees only A, B only B, no header sees nothing; A cannot insert a rule for B)
tests/test_m0_harden.py: 5 passed     (empty doc, broken fetch refuses to mass-deactivate, missing source is loud, swapped columns, headerless table)
10 passed in 8.17s
```

Notes / deviations:
- "2,100 words": 2,206 Doc rows → 2,120 unique words (86 rows are the same word listed in two tabs, e.g. Kteer, Marhaba; merged, both topics kept in english/aliases).
- Matcher misses (None, never wrong): "ishi" (Eshi: e/i handled but 'ishi' skeleton ties with other v-sh words), "akhui" (A5 / A5u: ratio floor). Left as None on purpose.
- Hourly import: Task Scheduler entry exists and runs, but there is NO unattended Google credential on this PC → the job re-reads the saved snapshot and logs "no live source configured". Live hourly fetch needs Medi to set `ANEES_DOC_PUBLISHED_URL` (Doc → File → Share → Publish to web) — on the morning checklist. Marked PARTIAL, not BLOCKED (the parser for the published-HTML path is written; tested on the Docs HTML export structure only).

## M1 — Lesson understanding  (00:05 → 00:35)

Built: `scripts/understand_lesson.py` (+ `scripts/english_stop.py`): reuses the pipeline's own speaker labels (pitch fallback),
finds every Doc-word occurrence (1-3-word n-grams; Latin tokens only when Arabizi-looking and not common English; Arabic script
exact), flags prompted / correction (recast or la/no/meta cue within 5 s, rules from tutor_reaction_exp.py) / uptake, locates
Amal's typed chat forms in the transcript within ±120 s by Arabic consonant family (Arabic OR Latin tokens; chat lags speech),
ranks topics per word FAMILY (a past-tense paradigm counts once), cuts shared clips ≤ 25 s (3 s before, 4 s after) into
docs/lessons/<date>/clips, applies the speaker-label floor (> 15 % unlabeled → speaker '?' and prompted/correction/uptake = None).

Gate output:
```
== 2026-09-04 (scribe.json reused, $0) ==
  "unlabeled_share": 0.136,
  "per_speaker_ok": true,
  "reason": "ElevenLabs merged the two voices; words were labeled by voice pitch, 14% stayed unlabeled"
  "doc_events": 236,
  "medi_events": 87,
  "medi_unprompted": 62,
  "medi_prompted": 18,
  "medi_corrected": 13,
  topic   60       typed family: Mabsoo6 / Basa6 / Babse6 / Btebse6 / Btebse6i / Btebse6u / Byebse6 / Byebse6u / Bnebse6 / Bnebse6o / Basa6u / Banbese6 /  ['بست ×23', 'بستن ×7', 'بست، ×6', 'بستت ×5', 'بتبست ×5']
  topic   54       Verbs List › Verbs List  ['Ana banbese6 ×80', 'Ana baq3ud ×9', 'Ana ba3mal ×8', 'Ana 3endi ×6', 'Ana ba9eer ×5']
  topic   25       typed family: Basa6at / Basa6eet / Basa6ti / Basa6tu / Basa6tek? / Enbas6at / Enbasa6et / Enbasa6ti / Enbasa6tu / Enbasa6ti bi/fi el-7  ['بستت ×5', 'Basa6at ×1', 'Basa6eet ×1', 'Basa6ti ×1', 'Basa6tu ×1']
  topic   23       Command Tense › Command Tense  ['E3mel ×8', 'Ta3aal ×4', 'E3ref ×3', 'efham ×3', 'Ektub ×2']
  topic   21       Grammar Termonology & Causative Verbs › Grammar Termonology  ['Mudaare3 ×8', 'Kelme ×4', 'Maadi ×3', 'Ma3na ×2', 'Jumle ×2']
  topic   21       Adjectives › General Adjectives  ['a7san ×12', 'Nafs ×9', '8air ×3', 'ma3roof ×3', '8ala6 ×2']
  chat found (family) 47 / 47  exact form 44  clips 76
== 2026-08-25 (data/aug25/eleven_scribe_auto.json reused, $0) ==
  "doc_events": 433,
  "medi_events": 207,
  "medi_unprompted": 152,
  "medi_prompted": 32,
  "medi_corrected": 27,
  topic   97       Verbs List › Verbs List  ['Ana ba3mal ×22', 'Laazem ×21', 'Ana banbese6 ×16', 'Ana bazbut ×12', 'Ana ba7ki ×11']
  topic   61       Past Tense › How Do We Turn Normal Verbs to Past?  ['Ana 3melet ×23', 'huwwe 6alab ×11', 'i7na 3melna ×8', 'Ana shta8alet ×6', 'Ana 5a66atet ×6']
  topic   56       Command Tense › Command Tense  ['E3mel ×24', 'etlob ×17', 'Eshte8el ×10', 'E7ki ×7', '5a66et ×6']
  topic   48       Adjectives › General Adjectives  ['Mut3eb ×23', '8ala6 ×10', 'Bey7uk ×10', 'Malyaan ×8', 'kaamel ×7']
  topic   39       Numbers › Numbers  ['Tamanyah ×11', 'tamanya u tes3in ×8', 'talatin ×7', '5amsah ×6', 'tamanin ×4']
  topic   29       Grammar Termonology & Causative Verbs › Grammar Termonology  ['Jumle ×11', 'Ma3na ×5', 'Kelme ×5', 'Bil8ala6 ×4', '7arf ×3']
python -m pytest -q tests/test_m1_understand.py
.........                                                                [100%]
9 passed in 0.86s
20 passed in 9.80s
```
- Sep 4: topic #1 = the typed babse6 / banbese6 / basa6 family (23 × بست, 7 × بستن …) ✔; 47/47 typed forms located within ±120 s
  (44 with the exact affixes; the 3 family-only ones are Hasa6to, "Enbasa6ti bi/fi el-7afle", "Enbasa6u bisafrethom").
- Aug 25 (no chat sidecar exists for it): top topic = **Verbs List (present-tense verbs: Ana ba3mal, Laazem, Ana banbese6, Ana bazbut,
  Ana ba7ki)** — why: Amal's own most frequent Arabic content words in the transcript are verb forms (ببسطها ×5, بتعبك ×4, بتزعل ×3,
  بتاسف ×3, لازم ×5, احكي ×4), and ranks 2-3 are the past-tense paradigm and the command tense: the lesson was verbs and their tenses.
- Clips: Sep 4 76 clips (4.9 MB), Aug 25 119 clips; 20 random clips ffprobe-checked in the test (duration = clip_end − clip_start ± 0.5 s; event offset exact).
- Label floor unit test: forced one-voice transcript → per-speaker fields None ✔; Sep 4 pitch fallback = 13.6 % unlabeled ≤ 15 % → published with the reason shown.

## M2 — After-lesson report  (00:45 → 01:45)

Built: `scripts/buckets.py` (grip buckets, one reference implementation), `scripts/build_report.py` (understanding →
Supabase lessons / word_events / lesson_events / word_stats → `docs/lessons/<date>-report.html` → rich email), `send_lesson_email.mjs`
extended with table-bar chart + log (house rule; Medi-only recipient hard-coded). Pages: https://thenatanzi.github.io/anees/lessons/2026-08-25-report.html
and …/2026-09-04-report.html. Clips force-added to git (`*.mp3` stays ignored for full recordings).

Gate (10 checks, both lessons) — `python -m pytest -q tests/test_m2_report.py`:
```
numbers = counts of stored lesson_events rows        PASS (Aug 25: missed 24 · nailed 110 · new 121 · reused 0 · typed 0 · moments 20;
                                                           Sep 4: missed 7 · nailed 34 · new 45 · reused 40 · typed 47 · moments 20)
"–" where unknown                                     PASS (forced speaker-split failure → "–" + reason, no per-speaker bars, no "Amal corrected")
each miss has audio                                  PASS (every missed + moment row has an existing clip; clips ≤ 25 s, start+end in the file name)
counts reconcile to Supabase lesson_events           PASS (SQL count per kind == page count, both dates)
chart present                                        PASS (inline SVG, Medi vs Amal Arabic words per 10 min; single amber series when floor fails)
mobile 375 px no horizontal scroll                   PASS (Playwright scrollWidth ≤ 375; play buttons ≥ 40 px)
dark + light                                         PASS (prefers-color-scheme block; body background differs under emulation)
loads < 3 s on Pages                                 PASS (200 in 0.22 s; clip HEAD 200)
email received by Medi                               PASS (Gmail INBOX: "Anees: lesson report 2026-08-25" 07:14:47Z, "… 2026-09-04" 07:14:54Z, both with chart bars + 20-line log)
email links resolve 200                              PASS
full suite: 33 passed
```
Hardening done during the loop: clip path bug on Pages (lessons/clips → lessons/<date>/clips) caught in the browser and fixed;
stale clip reuse (same start, new end) caught by the ffprobe test → names now carry start+end; Arabic glue words (شو, بس, يعني …)
were being graded as "missed" → GLUE_KEYS exclusion (Sep 4 misses 13 → 7, Aug 25 27 → 24); page + email now say "possible misses
(Amal reacted right after)" instead of "corrected by Amal", because the single-channel reaction detector is ~50 % precise (wiki 15).
The two emails already sent carry the older "corrected by Amal" wording; not re-sent (no duplicate mail).

### Council (Mode A, five advisors, three rounds — compressed)
| Advisor | Round-1 view | After critique |
|---|---|---|
| Strategic | Ship: this is the daily loop's core artifact; value comes from M4 closing the loop on possible misses | Holds. Insists the report links to the Amal question flow (M4) |
| Skeptical | "13 missed" was noise (glue words); correction detector ≈ 50 % precision; Sep 4 per-speaker facts rest on pitch labels with 14 % unlabeled | Satisfied by glue exclusion + "possible" wording + the floor banner; still wants Amal's verdicts fed back (M4) before any streak/grip claims |
| Creative | Lead with the 20 audio moments, not counts; counts are secondary for an ADD reader | Partly adopted: moments keep play buttons; big numbers stay because Medi asked for them |
| Evidence | Gate outputs are real (33 tests, counts reconcile to SQL, live 200 in 0.2 s); "new words" with 2 lessons means "first recorded", page says so | Holds |
| Audience (Medi) | One screen of big numbers, big play buttons, one caveat line: fits ADD; typed-family label was too long | Fixed (label truncated) |
Chairman: agreement = page is honest (no guessed numbers, "–" with reason) and usable on a phone; disagreement = whether "possible
misses" should show at all before Amal confirms (kept, labeled as possible, because M4 exists to confirm them); strongest argument =
evidence advisor's reconciliation to stored rows; risks = reaction-detector precision, pitch-label speakers on merged recordings.
**Score 8/10, no open P0.** Would rise with Amal's first 5 verdicts (M4) and one two-channel lesson.

## M3 — Amal's before-lesson link (planner)  (01:50 → 02:25)

Built: `scripts/amal_links.py` (secret-token rows, 7-day expiry, URL printed only locally, never sent), `scripts/suggest.py`
(candidate lists A = missed/shaky/recent-new, B = cold; OpenAI gpt-5.5 writes 12 candidates; a script validator keeps only
sentences whose every token is a Doc word / pronoun / glue AND that carry ≥ 1 A word and ≥ 1 B word; dropped-twice words are
banned; kept sentences come back first without an API call), `docs/amal/plan.html` (phone-first: 3 questions then one sentence per
screen with Keep / Drop / Edit; every tap saved immediately as an amal_rules row; "Stop here" any time; second open = "Already done").

Gate:
```
python -m pytest -q tests/test_m3_planner.py -s
test_sentences_use_only_doc_words_and_taught_topics PASS  (8/8 sentences, 0 token violations, each has an A and a B word; all topics are Doc headings)
test_drop_twice_removes_word PASS                          (1 drop keeps the word, 2 drops remove it; a kept sentence returns first with no API call)
test_stand_in_completes_planner_on_phone_under_2_min PASS  (Playwright 375×812, 0.8 s per tap: 11 screens in 12.1 s; per screen: 1 h1, ≤ 4 buttons,
                                                            every button ≥ 48 px and above the fold, "suggest" on every screen, no horizontal scroll;
                                                            typing used once (topic); rules stored: topic, new_words, repeat, keep, drop; done_at set;
                                                            second open shows "Already done, thank you Amal")
full suite: 36 passed
```
Sample of tonight's 8 suggestions (list A = kaan, 8air, Bsur3a, Bil8ala6, Ma7zooz, Mu8anni, Shoab, Ra2ey, Basee6a, Eshi):
"E7ki Jumle Bsur3a, Shukran." · "kaan Eshi 8ala6 El-youm?" · "El-jaw Shoab kteer elyom." · "huwwe Mu8anni u Banbese6 kteer."
Note: gpt-5.4-mini produced word salad ("bsur3a inti bi bukra") and 0/12 passed the validator → switched to gpt-5.5.

## Paid calls (running)
| time | service | what | cost (ceiling price) |
|---|---|---|---|
| 02:05 | OpenAI gpt-5.4-mini | planner sentences, 794 tokens, all rejected | $0.0009 |
| 02:12 | OpenAI gpt-5.5 | planner sentences, 5,433 tokens (8 accepted) | $0.0989 |
Running total: ElevenLabs $0.00 · OpenAI $0.10

## M4 — Amal's after-lesson link (3-5 questions) + M6 — Homework sheet  (02:30 → 03:05)

Built: `scripts/after_questions.py` (question candidates ranked by value: possible misses (recast first) > words whose voice was
unclear > Medi's repeated non-Doc words; hard cap 5, floor 3; each with a dedicated 15-s clip cut from the lesson audio into
docs/lessons/<date>/q/; homework ≤ 10 items = 6 validated sentences + 3 "use this word" + 1 mini-dialogue, all Doc words),
`scripts/apply_rules.py` (Right / Wrong / Not Medi patch the exact word_events row at that time; typed spelling → words.aliases;
then buckets are recomputed; idempotent via an 'applied' marker), `docs/amal/after.html` (one question per screen, ▶ once,
3 buttons + "Skip this one", optional one-line box only on unknown-word questions; homework = one item per screen Keep / Drop / Edit).

Gate:
```
python -m pytest -q tests/test_m4_after.py -s
test_questions_bounded_and_audio_short PASS                (Sep 4: 5 questions; every clip ≤ 15 s by ffprobe; 4 buttons max, text on each)
test_homework_uses_only_doc_words PASS                     (10 items: say ×6, use ×3, dialogue ×1; 0 tokens outside the Doc / pronouns / glue)
test_stand_in_answers_5_questions_and_homework_under_5_min PASS (Playwright 375×812, 0.8 s per tap: 15 screens in 16.3 s; homework part 10.6 s ≤ 1 min;
                                                            5 verdict rows in amal_rules (visible in amal_rules_public); apply_rules patched exactly the
                                                            event row at that time (rows=1 each), word_stats.updated_at advanced for every answered word;
                                                            edited homework sentence stored verbatim; dropped one stored as drop rules; done_at set;
                                                            second open = "Already done, thank you Amal")
test_link_expires_after_7_days PASS                        (expires_at = created_at + 7 d; a forced-expired link shows "This link has expired")
full suite: 40 passed
```
Sep 4 questions chosen: a7san @02:15, Ba3eed @08:37, Nafs @08:40, Aktar @61:23, Eshi @61:24 (all "possible miss" events; the
unclear-voice and unknown-word candidates ranked below them this time). Paid: gpt-5.5 homework sentences 5,821 tokens = $0.1067 (ceiling price).

### Council (Mode A) — advisors attempted the flow as Amal on the 375-px Playwright window (screens + timing above)
| Advisor | View |
|---|---|
| Strategic | This is the loop-closer: five taps from Amal turn "possible misses" into truth and re-score words. Ship. |
| Skeptical | All 5 questions are the same kind (correction) and two pairs sit 1-3 s apart (Ba3eed/Nafs, Aktar/Eshi) → the same clip twice; wants spread + kind diversity. Also "Not Medi" on a pitch-labeled lesson should flip the speaker (it does: speaker=Amal). |
| Creative | Show Amal the two words in one clip as one question ("which of these did he get?") — rejected for tonight: breaks one-question-per-screen. |
| Evidence | Every answer → rule row → patched event row → recomputed bucket, proven by SQL in the test; clips ≤ 15 s proven by ffprobe. |
| Audience (Amal) | Header says who asks and why; one ▶; three big buttons; "Skip this one" visible; under 20 s for the whole thing. The English "Did Medi say a7san right here?" is clear; Arabic line present. |
Chairman: agreement = flow is short, honest, saves every tap; disagreement = question diversity (skeptic) — accepted as a P1
for the morning (add a per-20-s dedupe so two questions never share a clip; kinds interleaved). Strongest argument = evidence
(rule → row → bucket chain proven). **Score 8/10, no open P0.** Rises when Amal's first real answers arrive.

## Codex audits M1 + M3 + M4/M6 — findings and fixes  (03:20 → 04:40)

Codex (rescue runs task-mto1ewgu, task-mto2ckyi, task-mto2ou9w) verified by running, not reading. Everything P0/P1 below is FIXED
and covered by a test; the full suite is 49 green after the fixes.
| # | Finding (Codex) | Fix |
|---|---|---|
| M1 P0 | English tokens (soon / sit / Aaaa) became Doc-word events at the exact tier | Latin hits must look Arabizi even at exact tier; vowel runs = fillers; 90 more English words in the stop-list; test `test_english_tokens_never_become_doc_words` |
| M1 P0 | chat location accepted 'the' / 'both' / 'Inti' and called approximations "exact form" | Latin ASR forms compared by Arabic consonant FAMILY core (same rule as Arabic tokens), exact form = equal skeletons; **honest numbers: 46/47 family, 41/47 exact form** (Codex's strict recount: 46 / 41) |
| M1 P0 | "How do you say sorry?" → Medi answers → Amal repeats was counted as a correction | elicitation rule: a tutor repeat after her own elicitation is confirmation; Medi asking ("how do you say", شو يعني) marks the word `asked` (bucket missed); test `test_elicited_answer_is_not_a_correction`. Aug 25 misses 24 → 21 |
| M1 P1 | the chat test trusted stored booleans | test recomputes from words_labeled + chat lines and compares to the stored flags |
| M3 P0 | expired holder could revive / PATCH its link; public rules view leaked payloads | migration 003: trigger blocks anon changes to token / kind / lesson_date / expires_at / created_at / payload; migration 004: expired links invisible to anon; public view = kind / word / lesson / 120-char label only |
| M3/M4 P0 | autosave was an in-memory queue; "done" rendered before the PATCH landed | both pages: localStorage queue + answers per token, reload resumes at the first unanswered screen, "Saving…" until the queue is empty |
| M4 P0 | a token could insert rules for any lesson/word; verdicts patched by ±1 s range; test mutated real rows | rules must match the link's lesson_date (RLS) and the link's own question list (apply_rules), patch by word_events.id bound at link creation; test snapshots and restores the rows |
| M4 P0 | 'who' question built from raw words (glue word shu, no event row) | unclear-voice questions come from real events, never glue words |
| M4 P1 | "wrong twice" = only consecutive; edits not reused; function tokens approved untaught glue; 3× weight unused | two misses within the last three answers (py + js parity test); edited sentences return first; glue = only Doc-present tokens (OpenAI prompt too); A-list sorted by weight |
| M4 P1/P2 | Arabic line same size as Arabizi; Skip a tiny link | Arabic 17 px muted second line; Skip is a 44-px full-width control (question screens keep ≤ 4 buttons: ▶ + 3 answers) |
Not fixed (by design): 'Right' no longer touches `prompted` (Codex was right); unknown-word "Yes, a word" with a typed spelling is kept as a rule row for the Words tab but never creates a Doc word (the Doc stays the truth).
Also: `data/amal_links.json` (token URLs) was committed at M3 → removed from git and ignored; only test tokens were ever in it and all were deleted.

## M5 — Flashcards  (03:00 → 04:45, interleaved)
Built: `docs/cards.html` (Quizlet Flashcards mode: tap/space to flip, Got it / Missed buttons or swipe, progress bar, end summary,
"Review the ones I got wrong (N)" until the pile is empty, Arabic-first / English-first, shuffle, 10/20 cards, subject picker =
Doc topics + grammar sets (past tense, all verb tenses, plurals, command) + buckets (Missed / Shaky / Last 3 lessons / Cold+ice)),
`docs/js/cards-core.js` (pure: weighted draw 3× for Missed + recent, round state machine), `docs/js/buckets.js` (JS port of
buckets.py), offline queue in localStorage → card_results (client uuid = idempotency key, duplicates ignored), "flag to Amal" after
two misses in a session (migration 002 policy), bucket badge on every card.
```
python -m pytest -q tests/test_m5_cards.py
7 passed in 34.81s
scheduler: seeded 300 draws Missed/Cold = 3.23 (≥ 3); 3,000 draws 3.06; mean over 200 seeds 3.07 (weight is exactly 3)
round of 20 with 6 misses → replay = exactly those 6 → second replay = the 2 still missed → pile empty; 28 stored rows reconcile (20 got / 8 missed)
ice-cold: 5 first-try rights on 3 days → ice_cold; one miss → cold; two misses in three → missed; Python and JS agree on 7 cases
phone 375×812 AND desktop 1280×800: flip / toggle / shuffle / replay end to end against live Supabase; buttons ≥ 48 px; no horizontal scroll
offline: 20 answers with the network off → queue 20 → online → 20 rows in Supabase; the same 20 ids replayed → still 20 (0 duplicates)
```

## M7 — One interface  (05:15 → 05:55)
Built: `docs/index.html` (tabs Today · Lessons · Words · Flashcards · Amal · Grammar · Future projects; hash routing; same design
system), `docs/js/arabizi.js` (JS port of the normaliser, parity-tested against Python on 20 forms), Words tab = search as you
type across Arabizi (loose / fold / short / skeleton / prefix), English (exact > first meaning > word > substring) and Arabic
(normalised, al- optional); every row = word · Arabic · English · topic · bucket badge · last reviewed (or "never") · seen · missed;
filters bucket + topic; sort last reviewed / times missed / Doc order; tap → history (every lesson clip with ▶ + card results);
Supabase-down = localStorage cache → docs/data/words.json + amber banner; `scripts/build_grammar.py` → Grammar tab (8 sections
of Amal's past-tense explanations) + wiki links; Future projects = the 4 items.
Gate:
```
python -m pytest -q tests/test_m7_index.py -s
4 passed in 4.01s
tabs: all 7 reachable in 1 tap (375 px, no horizontal scroll); dark + light differ
no dead links: crawler over every docs/**/*.html href/src (relative files exist; external HEAD 200)
Supabase down (route aborted, served over http): banner shown, 2,120 words from the saved copy, search still works
Words search: 20/20 queries (10 Medi spellings, 5 English, 5 Arabic) hit the right word in the top 3; slowest 8.1 ms (< 100 ms)
every row shows a bucket badge and a last-reviewed date or "never"
LIGHTHOUSE mobile performance 91 accessibility 100   (npx lighthouse 13.4.1, mobile emulation, live Pages URL)
```

## M8 — Hardening (part 1)  (05:55 → 06:10)
Built: `scripts/pipeline_ext.py` (ElevenLabs 3 retries on 429/5xx with 5/20/60 s backoff, other 4xx never retried; paid-call ledger
data/budget.json with hard caps 10 USD each and a 90 % stop; rich failure email to Medi only; guarded post_process = understanding →
report + email → after-link payload, each failure emailed, transcript never blocked). `lesson_pipeline.py` now calls these
(code only; the Task Scheduler entry "Anees lesson pipeline" was not touched).
```
python -m pytest -q tests/test_m8_pipeline.py   → 11 passed
429 ×3 → fails after exactly 3 tries, backoff 5/20/60, nothing charged · 429, 503, 200 → charged once (0.22 USD / 60 min)
401 → no retry · ledger at 8.90 USD + 0.22 → BudgetStop (90 % of 10) · failure email = rich (chart + log), recipient hard-coded thenatanzi@ only, never raises
empty transcript → RuntimeError · English-only call → arabic_share 0.0 < 0.12 cut · failed split → per-speaker None + floor false
missing chat sidecar → [] · git push failure → RuntimeError before any email · post_process: a failing step emails Medi and stops
64 passed in 137.12s (0:02:17)
```

## M8 — part 2: morning checklist executed once by the run  (06:25)
`plan/MORNING-CHECKLIST.md` (10 steps, ≤ 20 min, PASS line + what to do on FAIL, "do NOT send Amal the link" on any FAIL) and
`scripts/morning_check.py` (the automated part). Run by the build itself:
```
Anees morning check 2026-09-05 01:29
PASS  Supabase: HTTP 200
PASS  Pages index.html: HTTP 200 in 0.5s
PASS  Pages amal/plan.html: HTTP 200 in 0.4s
PASS  Pages amal/after.html: HTTP 200 in 0.4s
PASS  Pages cards.html: HTTP 200 in 0.4s
PASS  Pages lessons/2026-09-04-report.html: HTTP 200 in 0.5s
PASS  Planner link: 1 open planner link(s); newest lesson_date 2026-09-05
PASS  After-lesson link: 1 open after-lesson link(s) for 2026-09-04
PASS  Payload has 8 sentences: 8 Doc-checked sentences
PASS  Task "Anees lesson pipeline": Ready
PASS  Task "Anees vocab import": Ready
PASS  Budget: ElevenLabs 0.00 / 10 USD, OpenAI 0.44 / 10 USD (ledger)
PASS  Meet folder: G:/My Drive/Meet Recordings found
PASS  Gmail sender: alchemy-lock/.env present
PASS  Tests: 57 passed in 58.28s

ALL GOOD — 15/15 checks passed
```
Amal links minted (never sent; URLs only in the gitignored data/amal_links.json): planner for 2026-09-05, after-lesson for 2026-09-04.
`plan/HANDOFF-2026-09-05.md` written (DONE / PARTIAL per milestone, costs, the one-sentence messages, next 3 actions).

### Council M5 (flashcards) — compressed
| Advisor | View |
|---|---|
| Strategic | The daily habit lives here; Missed-first default + 3× weighting is the whole point. Ship. |
| Skeptical | Buckets come from ~50 %-precise lesson signals until Amal answers; "ice cold" needs 3 days so nothing is ice cold tonight (correct: 0 shown). Wanted the sync race fixed — it was (rows queued mid-sync are never dropped; proven by the 28-row reconciliation). |
| Creative | Swipe gestures + keyboard (space / arrows) added; "flag to Amal" after two misses feeds her link. |
| Evidence | 7 tests: scheduler ratio 3.23 / 3.06 / 3.07, replay exactness, ice-cold cases in Python AND JS, offline 20 → 20 → 20 (0 dupes), phone + desktop e2e. |
| Audience (Medi) | Quizlet feel (tap-flip card, two big buttons, progress bar, wrong-pile button) as asked; no Learn/Write/Match/Test. |
Chairman: **8/10, no open P0**. Rises when a week of card results exists (ice-cold and streaks become real).

### Council M8 (final) — compressed
| Advisor | View |
|---|---|
| Strategic | Everything Medi needs at 11:30 exists: one link, one sentence, one checklist. The loop closes only when Amal answers. |
| Skeptical | Three risks stay: (1) hourly Doc import is snapshot-only until publish-to-web; (2) merged-voice recordings give ~14 % unlabeled words; (3) the reaction detector is ~50 % precise, so "possible misses" must stay labeled possible. All three are stated on the pages / checklist, none is hidden behind a number. |
| Creative | Craig / Ennuicastr two-track recording is the single biggest quality lever left; listed in Future projects and next actions. |
| Evidence | 64 tests green; 5 Codex audits run (M0 still verifying after 1 h 36 min in its sandbox; M1, M3, M4/M6 findings all fixed with tests; M5, M7, full-repo pending at write time); Lighthouse 91; checklist 15/15; budgets 0.00 / 0.44 USD. |
| Audience | Amal's pages: one question per screen, ≤ 4 buttons ≥ 48 px, ▶ once, progress, quit, autosave that survives reload; Medi's site: big numbers, badges, ▶ everywhere. |
Chairman: **8/10**. Agreement: ship as is for tomorrow. Disagreement: none material. Blind spot to watch: Amal's real reaction to the first link (Medi's stated biggest fear) — the checklist makes Medi tap through screen 1 as Amal before sending.

## Paid calls — final
| service | calls | USD (ceiling prices) | cap |
|---|---|---|---|
| ElevenLabs | 0 (all transcripts reused) | 0.00 | 10 |
| OpenAI | 5 (gpt-5.4-mini ×1 rejected, gpt-5.5 ×4) | 0.44 | 10 |

## Codex audit M5 — findings and fixes  (06:40)
| # | Finding | Fix (all tested: tests/test_m5_cards.py now 8 green) |
|---|---|---|
| P0 | a swallowed localStorage error could drop an answer while the footer said "All answers saved" | every queue write is read back; on failure the row stays in memory, is sent immediately, and the footer says "only in memory until it syncs" |
| P0 | an old local log overwrote newer server buckets / last_reviewed | pure `mergeLocal()`: only rows newer than the server's last_reviewed count, bucket derived from the server bucket (ice cold + one miss → cold) |
| P0 | 3× weight went stale when a bucket changed | weight is always derived from the current bucket (`weightOf` ignores stored weights) |
| P0 | "flag to Amal" lost offline / 4xx ignored | flags go through the same durable queue; status checked; rejected rows parked in `anees-card-dead` |
| P1 | one permanently rejected row blocked the whole queue | on a 4xx the batch is retried row by row and the bad row is parked, the rest sync |
Cross-tab write races (two tabs answering at once) remain a P2: single-tab use is the case tonight.

## Codex audit M7 — findings and fixes  (06:50)
| # | Finding | Fix |
|---|---|---|
| P0 | `esc()` did not encode quotes → a Doc topic inside `data-s` could inject an event handler (repro confirmed) | all four pages escape `" ' > <` too; test asserts it on every page |
| P0 | 'paid' ranked baid (eggs) first: p→b folding + Arabizi tiers above English words | p and v are no longer folded (Arabic has neither; 2 Doc keys changed, re-synced); an exact English word beats every approximate Arabizi tier |
| P0 | exact Arabic with ال tied its al-stripped twin; pronoun-stripped forms tied literal entries | literal > stripped (100 > 96), exact Arabic > al-stripped (100 > 90); test: kaan, paid, الضهر |
| P0 | offline with no stats rendered "never / 0 / 0" | with no stats at all every stat shows "–" (test) |
| P1 | Grammar tab had only Past Tense prose | grammar tabs' tables included as lines → 4 tabs, 1,110 lines |
| P1 | Today's flashcards button left the one interface | it now opens the Flashcards tab (#cards) |

## Codex final full-repo audit — findings and fixes  (07:10)
Codex (task-mto4i1yz) said "P0 OPEN: yes". Each item, and what was done:
| Finding | Status |
|---|---|
| Amal token URLs were committed in two earlier commits (ddae6ed, 54c83ac; 31 tokens) | **verified dead**: all 31 were test/temporary links whose rows were deleted; SQL check now = 0 alive; the two live links (before 2026-09-05, after 2026-09-04) were minted AFTER the file left git and are not in history. No history rewrite (public repo, low risk, tokens useless without a row). Logged in the handoff. |
| standalone planner / after flows could call OpenAI without the ledger | FIXED: every OpenAI call now passes the 90 % preflight and records its cost inside suggest.ask_openai (post_process no longer double-counts) |
| ffprobe failure fell back to a guessed 65 min | FIXED: refuses to transcribe without a measured duration |
| cards.html rendered fabricated 0 / never with no stats | FIXED: bucket sets and badges show "–" when there are no stats at all |
| index.html lessons: nullable minutes / words rendered raw | FIXED: "–" with a reason tooltip |
| morning_check crashed on an inaccessible G: drive | FIXED: a FAIL line with the fix, no crash |
| dead-link test needs internet | FIXED: skips when the network is blocked |
| retry message said "3 tries" after 1 | FIXED |
| pytest not green in Codex's sandbox (no temp dir, no network, no Supabase keys) | environment: the same suite is green here (66 passed in 131.71s (0:02:11)) |
| P1: anon may insert card_results (public poisoning of buckets) | accepted for tonight, documented: the site has no login by design; a shared page secret would not stop a determined poster; fix = Medi's own token for the cards page (next chat) |
Codex M0 audit: still "verifying" after 1 h 50 min in its sandbox (10-min command limit, no keys); cancel command failed; left running, its
findings (if any) go to the next chat. M0 was covered by the full-repo audit's secret / Doc / email checks (all clean).

## Definition of done (plan §6) — status at 07:15
- All eight milestones DONE (M0 PARTIAL only for the unattended Doc fetch, cause + next action in the handoff) ✔
- Budgets: ElevenLabs 0.00 / 10, OpenAI 0.44 / 10 (ceiling prices, ledger) ✔
- Codex: M1, M3, M4/M6, M5, M7 and full-repo audits run; every P0 closed or verified dead (above) ✔ (M0 audit never finished in its sandbox)
- Council: M2 8/10, M4 8/10, M5 8/10, M8 8/10 ✔
- Checklist executed once by the run (15/15) ✔ · both Amal links minted, NOT sent ✔ · both lesson reports emailed to Medi ✔
- One flaky test noted: a live-network test failed once in a 4-minute full run and passed on every re-run (5 full runs green).

## M9 — Miss classifier + shared menu  (08:40 → 09:00, Medi's request after the checklist)
Built: `scripts/miss_kind.py` — every possible miss gets a kind: word · article (el-) · gender · tense · plural · pronunciation · unclear.
Signals: (2) Medi's spoken form vs the Doc form (الأكتر vs أكتر = extra ال → article; ة/ه swap → gender; plural suffix → plural),
(1) Amal's words in the 8 s after ("No أل", "feminine", "past", "plural", "pronounce", "means"), (3) Amal's own tap on the after
link (buttons are now Right · Wrong word · Wrong grammar · Not Medi) which always wins (apply_rules writes miss_kind). Optional
gpt-5.5 fallback only for 'unclear' with ≥ 8 English words from Amal, capped at 10 per lesson, through the budget ledger (off tonight).
Effect: a grammar-only slip no longer buckets the WORD as missed (it stays cold/shaky) and counts as a grammar slip instead
(word_stats.grammar_misses / grammar_kinds; Python and JS agree). Report pages: "Words you missed" vs "Grammar slips" with the kind
tag and why; Words tab: "Grammar slips" filter + amber tag; history rows show the kind. Migration 005 applied.
```
python -m pytest -q tests/test_m9_miss_kind.py → 6 passed
real Sep 4 61:23 Aktar (الأكتر, Amal: "No أل just أكتر إشي") → article ✔ · 02:15 a7san (الأحسن) → article ✔
Sep 4 kinds: article 4 · word 2 · unclear 2 → report: 4 word misses + 4 grammar slips (was 8 misses)
Aug 25 kinds: unclear 19 · article 1 · word 1 (Amal's reactions there are mostly plain repeats: 'unclear' stays unclear, never guessed)
full suite: 72 passed
```
UI (Medi: "the menu disappears for the report … aligning and more centered"): one shared sticky header + menu on index, cards
(standalone), report and transcript pages, all inside the same centered 820-px container; the active tab is highlighted; the
Flashcards iframe hides its own copy. Codex UI/UX audit launched (results in the next chat if still running).

## Miss classifier v2 + data audit  (09:05 → 09:55, from Medi's own checks on the Sep 4 report)
| Medi's point | What the data showed | Fix (tested, 77 green) |
|---|---|---|
| 61:29 "Eshi" tagged, but the slip was "aktar ishi" (the most) | two events 1 s apart under one Amal reaction | phrase merge: the head word (aktar) carries the slip, labeled "superlative: aktar/a7san + noun, NO el-"; eshi is not blamed |
| 61:07 a7san tagged "word" but he knows a7san; aktar was needed | Amal answered with a different Doc word (aktar) within 8 s | new kind **choice** (known word, wrong place) → bucket shaky, not missed |
| 08:37 Ba3eed / 08:40 Nafs "another el error" | transcript: "بعيد الـ نفس مشكلة" → Amal "نفس المشكلة" | dangling el- rule: a loose الـ next to the word = article slip |
| "I missed Na7el, didn't I?" | Medi: "what was bees?" → Amal "Nahl" → Medi "Nahl"; ASR wrote it in Latin so no event existed | chat-typed words (Na7el) anchor Latin ASR spellings and break matcher ties → now a word miss (asked) ✔ |
| 7ashara "reviewed yesterday" but never used | 56 card_results rows from the Playwright tests (01:33 PT) survived a failed cleanup and drove word_stats | rows purged, buckets recomputed, tests recompute after cleanup, dates shown in local time |
Sep 4 now: article 4 · choice 1 · word 1 (Na7el) · unclear 5. Sep 4 grammar slips are all the el- article (the lesson's real theme).

## 'new' bucket + report order  (10:00 → 10:25, Medi)
- New bucket **new**: first heard in one of the last 3 lessons and not yet drilled (< 3 first-try card rights on 2 different days).
  New words never mix with missed words; the lesson-only signal is kept beside it (word_stats.lesson_signal, migration 006). Python and
  JS agree; weight 3×. With only 2 lessons recorded, all 154 heard words are 'new' today — the number will settle as lessons accumulate.
- Report: "New words" is now the first section with a "Practice the new words" button (cards.html?subject=b-new); cards default to the
  New set when it is non-empty; Words tab has a New filter; Today shows new / missed as two cards.
- Classifier: "إلـ" counts as an el- cue; consecutive el- slips within 10 s fold into one discussion (aktar ishi … el) → 61:29 eshi is
  now part of the aktar slip, not "unclear". Data audit: 72 stale word_stats rows + 96 test flag rules purged; recompute is self-cleaning.

## M10 — WhatsApp chat as the second source  (2026-09-05 13:00 → 17:30, Medi's request after exporting the chat)
Source: data/whatsapp/raw (git-ignored; 12,205 lines, 98 voice notes, 54 photos). Parser: scripts/whatsapp_chat.py (narrow-nbsp header, multi-line, gloss "x = y", kind classifier that never guesses).
- **M10a house spelling** — scripts/house_spelling.py: 609 Doc words got Amal's own form (>= 2 sightings, headword only, exact tier for < 4 letters), 142 differ from the Doc (Qalqaan -> 2al2aan, Tariqa -> Tari2a, Mudeer -> Mudir). Migration 007 (words.house_spelling); Words tab shows her form (live-checked: "qalqaan" -> 2al2aan). 30-row sample: data/whatsapp/house_sample_30.json, 30/30 same word on my read; Medi's hand check pending.
- **M10b chat as transcript** — scripts/chat_ground_truth.py + hook in understand_lesson.understand(): Meet sidecar + WhatsApp lines merged, Doc words per line join Matcher.prefer, a Medi event of a typed word inside [-60 s, +150 s] becomes prompted (never an Amal event, never a corrected one). Stored in Supabase chat_lines. Aug 25: 27 WhatsApp lines, 26 events touched, 19 flag changes (said-cold 118 -> 99), 9 events re-keyed by prefer. Sep 4: 42 Meet + 3 WhatsApp lines, 16 events touched, 0 flag changes. Diff list with the causing line: understanding.json['chat_diff']; Medi's 8/10 acceptance pending.
- **M10c text homework loop** — grill decisions applied (Amal sees the grade; Anees page not WhatsApp; Anees suggests + Amal dictates + free box; typed only, voice -> Future). scripts/homework.py (prompts in her voice, 40 real prompt lines as few-shot, Doc-only model answers via suggest.validate), migrations 008-010 (homework_items / homework_answers / api_spend, RLS + guard triggers, token and model answer hidden from anon), edge function supabase/functions/grade (gpt-5.5, 12 real correction pairs as few-shot, 0.50 USD/day cap, CORS), docs/homework.html (Medi), after.html screens (verdict on Medi's answers, keep/drop/edit prompts, her own lines), apply_rules -> homework.apply_verdicts -> word_events.
  Gates: grader vs 12 real (answer, Amal fix) pairs = 12/12 agree (data/whatsapp/m10c_grader_check.json); Sep 4 sheet: 8 prompts suggested, 0 untaught words (validator), cost 0.15 USD; stand-in run through the after link: 1 verdict (fix) + 8 prompt decisions + 1 own line -> homework_items/answers/amal_rules rows, apply_verdicts -> etlob = missed, 3 words cold; homework page live: typed answer graded in ~8 s. "Sounds like Amal" 8/10 = Medi's call (pending).
- Tests: tests/test_m10_whatsapp.py (13; RLS test live). Full suite: 98 passed; test_m3 stand-in FAILS on a pre-existing rule clash (planner topic screen has 9 buttons, rule says <= 4; morning redesign, not M10); test_m4 stand-in passes after teaching it the new screens + it now deletes its own sheet.
- Spend: OpenAI 0.52 USD today (payload 0.30 incl. prompts 0.15, grading 0.22 across 14 calls). Codex audit: task-mtowmmx6-k3yry2 (see below).
