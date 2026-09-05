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
