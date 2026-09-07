# 07 — Configuration and access (no secret values anywhere in this package)

## Environment variables (Windows **User** environment; read by `scripts/anees_env.py` via shell env → winreg)

| Name | Used by | Configured on this PC? | Where to set |
|---|---|---|---|
| `ELEVENLABS_API_KEY` | `pipeline_ext.transcribe_with_retry`, `engine_eleven.py` | yes | User env (Medi's "clipboard method": Claude moves the key from clipboard to `setx`; Medi never types it) |
| `OPENAI_API_KEY` | `suggest.py`, `after_questions.py`, `miss_kind.llm_classify`, `engine_openai_*` | yes | User env |
| `RECALL_API_KEY`, `RECALL_REGION` (`us-west-2`) | `recall_bot.py` | yes | User env |
| `ANEES_SUPABASE_URL` (default `https://yljcbdxvnkfrwvelypfu.supabase.co`), `ANEES_SUPABASE_ANON_KEY` (public by design, also in `docs/js/config.js`), `ANEES_SUPABASE_SERVICE_KEY`, `ANEES_DB_PASSWORD` | `db.py`, `write_config.py`, `apply_migrations.py` | yes | User env |
| `SUPABASE_ACCESS_TOKEN` (management API, for migrations) | `apply_migrations.py`, `db.py` | yes | User env |
| `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` | `send_lesson_email.mjs` (borrows nodemailer from `C:\…\alchemy-lock\node_modules`) | yes (shared with another project) | User env / alchemy-lock `.env` |
| `SPEECHMATICS_API_KEY` | `engine_speechmatics.py` (experiments only) | was set for the Aug 25 runs | User env |
| `MEET_RECORDINGS` (default `G:/My Drive/Meet Recordings`) | `lesson_pipeline.py` | default in use | User env |
| `ANEES_DOC_PUBLISHED_URL` | `import_vocab.py` live fetch | **not set** (snapshot mode) | User env, after Medi publishes the Doc to the web |
| `HF_TOKEN` | local Whisper / pyannote experiments | maybe | User env |
| `OPENAI_STT_MODEL`, `OPENAI_PROMPT`, `OPENAI_LANG`, `OPENAI_CHUNK`, `RUN_TAG`, `ONLY_CLIPS`, `N_CLIPS`, `MOMENTS` | experiment knobs | — | shell |
| Edge function secrets (Supabase project): `OPENAI_API_KEY`, service key | `supabase/functions/grade` | set in Supabase dashboard | Supabase → Edge Functions → secrets |

Sanitized example (`.env`-style; the project does not read a file, this is for reference):
```
ELEVENLABS_API_KEY=<redacted>      OPENAI_API_KEY=<redacted>         RECALL_API_KEY=<redacted>   RECALL_REGION=us-west-2
ANEES_SUPABASE_URL=https://yljcbdxvnkfrwvelypfu.supabase.co   ANEES_SUPABASE_ANON_KEY=<public anon JWT>   ANEES_SUPABASE_SERVICE_KEY=<redacted>
SUPABASE_ACCESS_TOKEN=<redacted>   GMAIL_ADDRESS=<sender>             GMAIL_APP_PASSWORD=<redacted>
MEET_RECORDINGS=G:/My Drive/Meet Recordings                    ANEES_DOC_PUBLISHED_URL=   (unset)
```

## Accounts, integrations, limits

| Service | Account / project | Plan and limits known | Notes |
|---|---|---|---|
| ElevenLabs | Medi's key | Scribe v2 list price assumed $0.22/h in code (`ELEVEN_USD_PER_MIN`); some docs say $0.40/h; ledger cap $10, stop at 90 % | spent to date 0.69 USD (`data/budget.json`) |
| OpenAI | Medi's key | ledger cap $10; edge fn daily cap $0.50 | spent 2.21 USD (planner sentences, homework prompts, after-link sentences) |
| Recall.ai | workspace "Adibs Rugs", region us-west-2 | ≈ $0.50/h + $0.10/h for the 4-core bot; files kept 7 days | first bot 2026-09-05 |
| Google Workspace | wc@adibs.com hosts + records Meet (HARD RULE); Drive desktop sync to `G:` | — | Medi joins from his phone as thenatanzi@; Amal as herself |
| Google Docs | Amal owns both Docs; read via Drive connector snapshots | live fetch blocked until publish-to-web | `import_vocab.py` one-way |
| Supabase | org "anees", project ref `yljcbdxvnkfrwvelypfu`, us-west-1, free tier | RLS on all tables; anon key public; `amal_links` token guard | open P1: anon can insert `card_results` |
| GitHub | `TheNatanzi/anees`, public, Pages from `docs/` | — | secrets never in repo; 31 old test tokens in two early commits are dead (rows deleted) |
| Gmail | app password shared with the Alchemy project | — | emails to Medi only |
| Speechmatics, Gemini, xAI, Fish, Inworld | Speechmatics key used once; Gemini key used by Codex's bake-off (its env); xAI/Fish/Inworld none | — | — |

## Consent, data use, retention (as decided)

- **Rule A4 (Medi 2026-09-05; Amal's yes relayed the same day):** lessons are public by choice — audio, clips, transcripts on the open site; any transcription provider may receive the audio under its default retention; only providers that train on uploads (Fish Audio's terms) need Amal's explicit yes. No consent gate in code.
- Retention: constants said raw audio 90 days; **nothing is deleted today** ("lesson audio never deleted", rule). Recall deletes its copies after 7 days. Codex's uploads for its tests were deleted (its ledger: 21 rows `deleted: true`).
- WhatsApp export: private, git-ignored; 27 verbatim lines from it are inside the tracked `data/lessons/2026-08-25/understanding.json` and 12 pairs in `pairs.ts` / test fixtures (Codex NO-GO; Medi kept them).
- Unresolved: Amal has not seen any transcript page; no explicit statement from her about the public site beyond Medi's relay; Fish Audio test paused for consent.
