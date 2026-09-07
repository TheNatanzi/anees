# 02 — Current implementation (as of 2026-09-07 14:40 PT)

## Repository

- Path `C:\dev\anees`, branch `master`, HEAD `22a14a4` (2026-09-05 "plan: process audit…"), remote `origin https://github.com/TheNatanzi/anees.git` (**public**), GitHub Pages serves `docs/` at `https://thenatanzi.github.io/anees/`.
- Working tree: modified `data/m4_stand_in_timing.json` (test residue, discard), `data/vocab/words.json` + `docs/data/words.json` (hourly Doc import re-export 2026-09-07 14:35, harmless); untracked `data/lessons/2026-09-05/{email.json, scribe_Amal.json, scribe_Medi.json, scribe_meet_mixed_1615.json, summary_meet_mixed_1615.json}` — **raw engine outputs, keep them** (no lesson's raw `scribe.json` is tracked; they live only on this PC).
- 70 commits from 2026-09-03 to 09-05; the "Lesson <date>: transcript page / report page + clips" commits are made by the pipeline itself (`git_publish`).
- Runtimes: Python 3.12.8 (`requests 2.34`, `librosa 1.0`, `numpy 2.5`, `openai 1.50`, `playwright 1.62`, `pytest 8.3`), Node v24.18 (email sender), ffmpeg 8.1.2 (on PATH). No `requirements.txt` / `package.json` exists; install by hand: `pip install requests librosa numpy pytest playwright` (+ `python -m playwright install chromium` for the planner test), `npm i` nothing (the .mjs uses Node built-ins + a local mail config: see `scripts/send_lesson_email.mjs`).

## Annotated tree (what matters)

```
C:\dev\anees
├─ scripts/                      59 files, all Python unless noted
│  ├─ recall_bot.py              Recall.ai bot: join / status / fetch → data/lessons/<date>/tracks/*.mp3 + tracks.json
│  ├─ ingest_tracks.py           tracks → per-track Scribe → merged scribe.json (speaker = track) → audio.mp3 mix → lesson_pipeline.process
│  ├─ lesson_pipeline.py         the Meet-recording path: extract_audio → is_arabic_lesson (3-min sample) → transcribe → build (runs, labels) → transcript.txt/html → publish (git push) → email → pipeline_ext.post_process
│  ├─ pipeline_ext.py            Scribe retries + USD ledger (data/budget.json, caps $10, stop at 90 %) + failure email + post_process chain
│  ├─ lesson_text.py             FILLER / CONFIRM regexes; words → speaker runs with (pause) items
│  ├─ understand_lesson.py       Doc-word events (matcher tiers), prompted/correction/asked/elicited flags, chat anchoring, clips (ffmpeg), false-start rule, understanding.json
│  ├─ arabizi.py                 Arabizi/Arabic normalisation; Matcher tiers exact > fold > short > skeleton > fuzzy
│  ├─ miss_kind.py               miss classifier v2 (word/choice/article/gender/tense/plural/preposition/pronunciation/unclear)
│  ├─ build_report.py            understanding.json → Supabase rows + docs/lessons/<date>-report.html + report_email.json (M11 Medi-only)
│  ├─ after_questions.py / amal_links.py / apply_rules.py   Amal's after link (5 questions, clips), secret-token links, re-scoring from her taps
│  ├─ suggest.py / homework.py / house_spelling.py / chat_ground_truth.py / whatsapp_chat.py   planner sentences, typed homework loop, WhatsApp-derived spelling (M10)
│  ├─ buckets.py                 word buckets (new / missed / shaky / cold / ice_cold) from word_events + card_results (Medi events only)
│  ├─ build_tally.py             data/tally.json (hand-curated slips) → docs/data/tally.json, cuts tally clips
│  ├─ import_vocab.py            Google Doc → words table (one way; snapshot mode until a publish-to-web URL exists)
│  ├─ build_grammar.py / build_ai_reports.py / build_engine_report.py / build_check_02.py / build_check_03.py / build_recipe1_page.py   static pages
│  ├─ engine_*.py, *_aug25.py, whisper_*.py, diarize_*.py, turns_*.py, tutor_reaction_exp.py   Aug-25 engine experiments (see 06)
│  ├─ db.py / apply_migrations.py / anees_env.py / write_build.py / write_config.py / morning_check.py
│  ├─ send_lesson_email.mjs      rich HTML email to Medi only (Node)
│  └─ run_lesson_pipeline.ps1, run_import_vocab.ps1   the two Task Scheduler entry points
├─ data/
│  ├─ lessons/<date>/            per lesson (see "Storage"); processed.json (Meet recordings seen), recall_bots.json, pipeline.log, budget.json (ledger, tracked)
│  ├─ aug25/                     Aug-25 experiment set: aug25.mp3 (62 min mixed), 57 gold clips, engine outputs, Check 02/03 keys + Amal's results
│  ├─ vocab/                     words.json (2,120 words from the Doc, export 2026-09-07), grammar_materials_2026-09-05.md, doc_markdown snapshots
│  ├─ whatsapp/                  WhatsApp export with Amal (git-ignored, private), house spelling samples
│  ├─ tally.json                 the slips tally (curated)
│  └─ amal_links.json            minted links (git-ignored)
├─ docs/  (GitHub Pages)
│  ├─ index.html                 10 tabs: Today · Lessons · Words · Flashcards · Amal · Grammar · AI reports · System rules · Word & grammar rules · Future
│  ├─ lessons/<date>.html        transcript page (runs, pauses, ✓, chat lines)      ← the "latest usable interface" for transcription work
│  ├─ lessons/<date>-report.html after-lesson report (misses, grammar, nailed, new, reused, heard-from-Amal, moments with ▶)
│  ├─ lessons/<date>/clips/*.mp3 clips (force-added; *.mp3 is git-ignored)
│  ├─ slips.html                 Medi's mistake tally per learned rule
│  ├─ cards.html, homework.html, amal/plan.html, amal/after.html   flashcards, typed homework, Amal's two links (token in URL)
│  ├─ check02-amal.html, check03.html, recipe1.html, engine-report.html, reports/*.html   experiment pages and research reports
│  ├─ js/ (config.js = Supabase URL + anon key, arabizi.js, buckets.js, build.js, stale.js, cards-core.js) · data/ (words, grammar, ai_rules, ai_reports, house_spelling, tally, build)
├─ supabase/migrations/001–010.sql (words, lessons, lesson_events, word_events, card_results, word_stats, amal_links, amal_rules, chat_lines, homework_items/answers, api_spend, RLS, token guard) · functions/grade (Deno edge fn: OpenAI pre-grade of typed homework, $0.50/day cap)
├─ tests/  14 files, 104 tests (pytest); playwright used by test_m3/m4 stand-ins
├─ wiki/   00–17 research pages (engines 07, two-channel 13, learner-voice workarounds 14, speaker separation 15, tutor reaction 15, Codex test 16, teacher brain 17)
├─ plan/   blueprint, constants (contracts), overnight build prompt + log, handoff 09-05, audit 09-05, teacher-brain prompts
└─ models/ (local model cache from the Aug-25 experiments; not needed)
```

## Feature → implementation map

| Visible feature (URL) | Built by | Data |
|---|---|---|
| Lesson transcript page `lessons/<date>.html` | `lesson_pipeline.render` (+ `build`, `lesson_text.runs_from_words`) | `data/lessons/<date>/scribe.json`, `summary.json`, `transcript.txt` |
| Report page `lessons/<date>-report.html` | `build_report.build` ← `understand_lesson.understand` ← `miss_kind.classify_all` | `understanding.json`, `report_rows.json`, Supabase `lesson_events`, `word_events` |
| ▶ clip buttons | `understand_lesson.cut_clips` (ffmpeg from `audio.mp3`), `build_tally.find_or_cut_clip` | `docs/lessons/<date>/clips/` |
| Today / Lessons / Words tabs | `docs/index.html` + `js/buckets.js` reading Supabase via anon key; `docs/data/words.json` | `word_stats`, `word_events`, `card_results` |
| Flashcards `cards.html` | `js/cards-core.js`, `buckets.js` | `card_results` (anon insert: open P1) |
| Amal planner `amal/plan.html?t=` | `suggest.py` payload + `amal_links.create('before')` | `amal_links`, `amal_rules` |
| Amal after link `amal/after.html?t=` | `after_questions.payload` + `amal_links.create('after')`; her taps → `apply_rules.py` | same |
| Homework `homework.html` | `homework.py`, edge fn `grade` | `homework_items/answers`, `api_spend` |
| Slips `slips.html` | `build_tally.py` | `data/tally.json` → `docs/data/tally.json` |
| Grammar tab | `build_grammar.py` from `data/vocab/grammar_materials_*.md` | `docs/data/grammar.json` |
| Rules tabs | `docs/data/ai_rules.json` (hand-edited) | — |
| Engine report, Check 02/03, recipe 1, AI reports | `build_engine_report.py`, `build_check_0*.py`, `build_recipe1_page.py`, `build_ai_reports.py` | `data/aug25/*`, `docs/data/ai_reports.json` |
| Out-of-date banner | `write_build.py` (pre-commit hook) + `js/stale.js` | `docs/data/build.json` |

## Commands

```powershell
# tests (≈3 min; 1 known failure test_m3_planner::test_stand_in_completes_planner_on_phone_under_2_min — planner screen shows 9 buttons, rule allows 4; other session's M10 change)
python -m pytest -q

# a lesson captured by the bot (paid Scribe call only when scribe_<Name>.json is missing)
python scripts\recall_bot.py join "https://meet.google.com/xxx-yyyy-zzz" --date 2026-09-12      # before the lesson (host admits "Anees notes")
python scripts\recall_bot.py fetch <bot_id> --date 2026-09-12                                    # after: tracks/*.mp3 + tracks.json
python scripts\ingest_tracks.py 2026-09-12 --hhmm 1419 --src "G:/My Drive/Meet Recordings/<code> (<date> <time> GMT-7)" [--send]
#   = per-track Scribe → merge → audio.mp3 → transcript page (pushed) → understanding → report (pushed) → after link minted (OpenAI ≈ $0.30) ; --send emails Medi

# a lesson from a Meet recording only (the hourly job does this)
python scripts\lesson_pipeline.py                                   # every new file in G:/My Drive/Meet Recordings (env MEET_RECORDINGS)
python scripts\lesson_pipeline.py --reuse <scribe.json> --file "<recording>"

# re-derive without paying
python scripts\understand_lesson.py 2026-09-05            # events + clips
python -c "import sys;sys.path.insert(0,'scripts');import build_report;build_report.build('2026-09-05',use_db=True,send=False)"
python -c "import sys;sys.path.insert(0,'scripts');import lesson_pipeline as lp;lp.publish_report('2026-09-05')"   # git push + wait for 200
python scripts\build_tally.py

# email (Medi only)
node scripts\send_lesson_email.mjs "Anees: lesson report 2026-09-05" data\lessons\2026-09-05\report_email.json

# Doc import (snapshot mode), DB migrations, morning checklist
python scripts\import_vocab.py ; python scripts\apply_migrations.py ; python scripts\morning_check.py
```

## Background jobs and deployment

| Job | Trigger | Does | Risk |
|---|---|---|---|
| Task Scheduler "Anees lesson pipeline" | hourly at :15 (`scripts/run_lesson_pipeline.ps1`) | scans `G:/My Drive/Meet Recordings` for files not in `data/lessons/processed.json`; pre-checks Arabic on a 3-min sample ($0.01); transcribes, publishes, emails Medi, post-processes | re-processed the bot lesson on 2026-09-05 16:15; now guarded by "reuse existing scribe.json", but a date with bot tracks and no scribe.json would still be transcribed from the mixed file |
| Task Scheduler "Anees vocab import" | hourly at :35 (`run_import_vocab.ps1`) | re-reads the Doc snapshot → `words.json` + Supabase `words` | live Doc fetch needs a publish-to-web URL (never provided) |
| GitHub Pages | every push to `master` | serves `docs/` in ≈ 1 min | site = repo; nothing else deployed |
| Supabase project `anees` (ref `yljcbdxvnkfrwvelypfu`, us-west-1, free tier) | — | tables above, RLS, edge function `grade` | anon key public by design; P1: anon can insert `card_results` |

Local code vs deployed site: identical at HEAD except the raw scribe files (never published) and `data/whatsapp` (git-ignored). The site shows a "page out of date" bar when `docs/data/build.json` differs from the page's build stamp.

## Storage map

| What | Where |
|---|---|
| Original bot tracks | `data/lessons/<date>/tracks/<Participant>.mp3` + `tracks.json` (offsets, durations) — only 2026-09-05 so far |
| Original Meet recordings (host account, Google Drive desktop sync) | `G:\My Drive\Meet Recordings\<code> (<date> <time> GMT-7)` (+ ` - Chat Transcript` sidecar when Amal typed) |
| Lesson audio used for clips | `data/lessons/<date>/audio.mp3` (16 kHz mono 48 kbps from the recording; 24 kHz mono 64 kbps amix for 09-05); git-ignored |
| Raw ASR | `data/lessons/<date>/scribe.json` (mixed path) or `scribe_Medi.json` + `scribe_Amal.json` + merged `scribe.json` (tracks path); git-ignored, this PC only; Aug 25 raw = `data/aug25/eleven_scribe_auto.json` |
| Labeled word stream | `words_labeled.json` (`s, e, spk, w`) |
| Transcript | `transcript.txt` (`[mm:ss] Speaker: text (pause Ns)`), `transcript.html`, `docs/lessons/<date>.html` |
| Events, clips | `understanding.json`, `docs/lessons/<date>/clips/*.mp3` |
| Vocabulary | `data/vocab/words.json`, Supabase `words`; grammar `data/vocab/grammar_materials_2026-09-05.md` |
| Speaker labels | inside `scribe.json` (`speaker_id`), `summary.json.speaker_split`, `understanding.json.label_confidence` |
| Corrections / feedback | Amal: `amal_rules` (none yet), Check 02 results `data/aug25/check02_results_amal.json`; Medi: chat only (this session) + `data/tally.json` |
| Learning data | Supabase `word_events`, `lesson_events`, `card_results`, `word_stats`, `homework_*` |
| Costs | `data/budget.json` (ElevenLabs 0.6885 USD, OpenAI 1.9122 USD to date), `api_spend` table |
