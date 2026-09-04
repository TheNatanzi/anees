# 11 — Reuse Map: What We Run As-Is vs Copy (Medi's ask 2026-09-03: reuse, don't rebuild)
| Our step | Run as-is (license) | Copy the pattern from | Saves |
|---|---|---|---|
| 1 Hear | ElevenLabs Scribe v2 API (paid); WhisperX + pyannote (BSD) as open skeleton; Cohere Transcribe Arabic (Apache-2) second opinion | LearnerVoice: verbatim prompting keeps fillers/self-repairs | writing any speech code |
| 2 Understand Arabic | CAMeL Tools (MIT): tokenize, dialect ID, morphology; Maknuune 36K Palestinian lexicon (CC-BY); CAMeL seq2seq Arabizi↔script (MIT) | Lute v3 (MIT): `words` + `wordparents` form→lemma, status 1-5 | building a dictionary or normalizer |
| 3 Find misses | **m98/fluent** (MIT, 393★): a Claude Code language kit with `mistakes-db.json` (error patterns + counts), `mastery-db`, `session-log`, SM-2 → adapt its prompts and DB shape as our extraction skill | lesson-lens (chat transcript → summary, Anki CSV, exercises, daily queue); Voice2Anki (AGPL, audio → Whisper → LLM → AnkiConnect); italki block order; NICT JLE 47 error tags / AALETA 37 | designing the extractor from scratch |
| 4 Remember + schedule | ts-fsrs / py-fsrs (MIT) | Anki schema (notes/cards/revlog); Duolingo HLR trace columns | the scheduler entirely |
| 5 Practice | **Option A:** Anki app (AnkiDroid/AnkiMobile) + AnkiConnect (GPL) — cards pushed from our DB, FSRS built in, audio on cards, self-grade; **Option B:** build our own 7-min page | Echo-Loop (AGPL): review the clip not the word; Pimsleur pause; Discute (Apache-2): mic → STT → LLM → TTS plumbing | Option A saves most of Phase 4 |
| 6 Show + nudge | our gold dashboard pattern (static page + Supabase); send_note.mjs rich emailer; BuilderIO visual-plan | Preply Lesson Insights (tutor recap shape); Migaku "Tracking" (tutor-pinned words); Clozemaster 4-rung ladder | dashboard scaffolding + email |

**DECIDED 2026-09-03 (Medi): Practice = our own page (Option B).** Quizlet rejected (no API, no results out, scraping banned in ToS; study history never exports). Anki rejected (Medi prefers one built page). Until the page exists, practice happens only in class.

### Repo deep-dive (2026-09-03) — what is actually liftable
| Repo | License | Lift | Notes |
|---|---|---|---|
| **m98/fluent** | MIT ✓ | `.claude/hooks/update-db.py` (atomic JSON write, `update_mistakes_db()` bumps frequency, keeps last 5 examples); error payload `{pattern_id, category, subcategory, description, severity, your_answer, correct_answer, context, difficulty_score, notes}`; `data-examples/mistakes-db-template.json`, `session-log-template.json`; `fluent-feedback-formatter` severity 🔴🟡🟢 + categories `grammar, formal_informal, vocabulary, spelling, prepositions, articles, missing`; `fluent-session-analyzer` "4+ occurrences = critical" | It is a chat tutor, not a transcript extractor: write our own SKILL.md that takes a diarized transcript and emits fluent's payload. SM-2 skipped (we use FSRS). |
| **lesson-lens** | none ✗ | nothing verbatim | Re-type the ideas: miss record `{learner_original, teacher_correction, reason, source_refs}`; prompt rules "never invent, preserve corrections exactly, cite source lines, flag [uncertain]"; second-pass reviewer emits `{section,item,field,current,suggested,issue,confidence}` = our Amal-confirm queue; queue order corrections-first, overdue-first; recognition→production after 2 passes; daily target ramps 5→30. Swap point: replace their LINE-chat parser with our diarized-segment adapter. |
| **Echo-Loop** | AGPL, facts only | review intervals 6h, 18h, 24h, 48h, 72h, 168h, 336h (code, not README); `Sentence{start,end,text}`; stages blind-listen → intensive → listen-and-repeat → retell | design for speak mode |
| **Voice2Anki** | AGPL | skip | Anki not in v1 |
| **ts-fsrs** | MIT ✓ | npm 5.4.2, Node ≥20: `createEmptyCard`, `fsrs(generatorParameters({request_retention:0.9}))`, `f.next(card, now, Rating.Good)` → `{card, log}`; persist both | scheduler done |
| **AnkiConnect** | GPL over HTTP | parked | only if Anki export is ever wanted |
| CAMeL Tools / Maknuune | MIT / CC-BY ✓ | install | Arabic normalizer + lexicon |
