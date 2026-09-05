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
