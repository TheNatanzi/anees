# 01 — Repos & Apps to Learn From
*Research date 2026-09-03. "Unverified" = could not confirm this session.*

### A. Open-source repos worth studying

| Repo | Stars / License / Activity | One thing to steal |
|---|---|---|
| [Anki](https://github.com/ankitects/anki) | 30.3k, AGPL-3, release 26.08.1 (Aug 2026) | The **note → cards → revlog** split. One `notes` row, N `cards` (one per mode: speak/type/flip), append-only `revlog` (`id, cid, ease 1-4, ivl, lastIvl, factor, time_ms, type`). Schema: [AnkiDroid wiki](https://github.com/ankidroid/Anki-Android/wiki/Database-Structure). |
| [fsrs4anki](https://github.com/open-spaced-repetition/fsrs4anki) / [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) | 4.1k / 773, MIT | The **DSR state**: `difficulty (1-10), stability (days to 90% recall), retrievability`. FSRS-6 = 21 params ([algorithm](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm)). ts-fsrs drops into a Supabase stack. |
| [Lute v3](https://github.com/LuteOrg/lute-v3) | 1.5k, MIT | `words` + `wordparents`: `WoText, WoTextLC, WoStatus, WoTranslation, WoRomanization` plus parent→child so inflected form → lemma is explicit ([schema](https://deepwiki.com/LuteOrg/lute-v3/4.1-database-schema)). Status 1-5 / 98 ignored / 99 well-known. |
| [Echo-Loop](https://github.com/echo-loop/Echo-Loop) | 3.4k, AGPL-3, Flutter, active 2026 | **Listen → shadow → retell** on the learner's own audio; 8-stage/28-day review of *sentences with original audio*. Closest to "review a lesson clip". |
| [VocabSieve](https://github.com/FreeLanguageTools/vocabsieve) | 535, GPL-3 | "Known words" inferred from lookups + reviews, never typed. |
| [m98/fluent](https://github.com/m98/fluent) | 393, MIT | `mistakes-db.json`: error *patterns* with counts + example corrections, separate from vocab; `mastery-db` 0-5 per topic; `session-log`. |
| [duolingo/halflife-regression](https://github.com/duolingo/halflife-regression) | 576, MIT, 2016 | Learning-trace row: `p_recall, delta, lexeme_id, history_seen, history_correct, session_seen, session_correct`. Log per exposure. |
| [Discute](https://github.com/5uru/Discute) | 87, Apache-2 | Whisper → LLM corrections → TTS readback. Speak-mode plumbing reference. |
| [OpenPronounce](https://github.com/Halleck45/OpenPronounce) | 48, MIT | Phoneme scoring — **English-only**, useless for Arabic. |
| [vertesia/large-language-tutor](https://github.com/vertesia/large-language-tutor) | archived 2025 | Rule: deterministic app logic, LLM only for non-deterministic tasks. |
| [LibreLingo](https://github.com/LibreLingo/LibreLingo) | 2.6k, archived Jun 2026 | Lesson as YAML data, not a doc. |
| [flashcards-open-source-app](https://github.com/kirill-markin/flashcards-open-source-app) | 62, MIT | Documents FSRS logic in `docs/`, exposes SQL over MCP — copy the habit. |
| [WhisperLevantine](https://huggingface.co/HebArabNlpProject/WhisperLevantine) | — | Whisper-large-v3 on ~1,200 h Levantine. Also [Casablanca](https://arxiv.org/abs/2410.04527) multidialect benchmark. |

Gap found: **no maintained open-source tutor-side dashboard** for language learning exists (GitHub topic `language-tutor`: 7 repos, none >7 stars).

### B. Commercial apps: the one mechanic, and the evidence

| App | Mechanic | Evidence |
|---|---|---|
| Duolingo | Per-lexeme half-life model; strength bars = p_recall decay | HLR paper (Settles & Meeder ACL 2016), 13M traces. Efficacy studies company-authored ([research.duolingo.com](https://research.duolingo.com/)). |
| Anki | Note/card split + append-only revlog | 20 years of data; FSRS trained on it. Strongest engineering evidence. |
| FSRS (Anki, RemNote) | Per-learner params from the log | RemNote claims 20-40% fewer reviews at equal retention ([help](https://help.remnote.com/en/articles/9124137-the-fsrs-spaced-repetition-algorithm)) — vendor claim, consistent with open benchmarks. |
| Memrise | Learner-attached mnemonic per word | Self-reported stats; marketing. |
| LingQ | Status 1-4 + Known; blue = never seen ([support](https://lingq-support.groovehq.com/help/can-you-explain-a-lingqs-status)) | No efficacy study; good UX. |
| Clozemaster | 0/25/50/75/100% = 4 correct in a row at 1/10/30/180 days ([docs](https://docs.clozemaster.com/article/37-how-do-i-master-something)) | Fixed ladder; simple enough to explain to a tutor. |
| Speak / Praktika | Streaming ASR + roleplay | No efficacy study; no SRS (competitor-sourced). |
| Langua | Corrections + post-conversation report; saved words fed back | Vendor-described; matches our pipeline. |
| Pimsleur | Graduated-interval recall + **anticipation pause** ([method](https://www.pimsleur.com/the-pimsleur-method/)) | Pause is the transferable bit for speak mode. |
| Glossika | Sentence reps, record-yourself, daily "at-risk" list | Rhetoric, no study. |
| Migaku / Refold | Unknown/Learning/Known/Ignored/**Tracking** states ([blog](https://migaku.com/blog/youtube/the-learning-statuses-migaku-browser-extension)) | Tracking = tutor-pinned words. |
| Busuu / Babbel | Structured lessons + review | Vendor-commissioned Vesselinov studies (Babbel ~15 h ≈ one semester). |
| italki / Preply | **Preply Lesson Insights**: speaking time, vocab, grammar per lesson → Daily Exercises | Nearest commercial analogue to our loop. |
| Quizlet (current) | Learn mode; Progress buckets "Still learning" | Free tier caps Learn/Test rounds; Learn paywalled ~$2.99/mo (unverified). Confirms the pain. |

### C. Data-model patterns
- **Word vs lemma vs card.** Anki: bag of fields. Lute: surface form is the row, lemma via `wordparents`. Duolingo: `lexeme_id`. For dialect Arabic with no reliable lemmatizer: **form is primary, lemma an optional tutor-confirmed link.**
- **Learner state.** SM-2: `ivl, factor, reps, lapses, due`. FSRS: `stability, difficulty, due, state, last_review`. Ordinal status for tutors: "new / shaky / solid / known". **Recommendation: FSRS state per card + ordinal status per item for tutor display.**
- **Review events.** Everyone that works keeps an **append-only log**.

Recommended schema (9 tables):
```
lessons        id, recorded_at, meet_url, audio_url, transcript_url, duration_s, tutor_notes
utterances     id, lesson_id, speaker (learner|tutor), t_start, t_end, text_ar, text_translit, text_en
struggles      id, lesson_id, utterance_id, kind (correction|gap|hesitation|grammar),
               learner_said, target_form, note, extracted_by (llm|tutor),
               status (pending|confirmed|rejected), confirmed_by, confirmed_at
items          id, form_ar, translit, gloss_en, lemma_id→items.id NULL, pos, sense_note,
               audio_url, source_struggle_id, tutor_status (new|shaky|solid|known|ignored),
               tutor_pinned bool, created_at
item_contexts  id, item_id, utterance_id, sentence_ar, sentence_en
cards          id, item_id, mode (speak|type|flip), stability, difficulty, due, state, reps, lapses, last_review
reviews        id, card_id, reviewed_at, rating (1-4), answer_text, answer_audio_url,
               asr_text, asr_score, elapsed_days, scheduled_days, duration_ms   -- append-only
error_patterns id, label, description, count
struggle_patterns  struggle_id, pattern_id
lesson_sheets  id, lesson_id (next), created_by, items jsonb[], results jsonb, sent_at
```
`struggles` = tutor inbox; `items` exist only after confirmation; `reviews` never updates.

### D. UI patterns for a learner + tutor dashboard
- Confirm inbox with transcript line + 3-second audio clip (Preply, Migaku Tracking).
- Colored word status painted over the transcript (LingQ/Lute/Migaku).
- Four-button rating for flip; speak/type auto-rate with override (Anki/FSRS).
- Plain-word mastery ladder for the tutor (Clozemaster/LingQ).
- Card front = Amal's clip, not an isolated word (Echo-Loop/Glossika).
- Anticipation pause in speak mode (Pimsleur).
- Retest sheet as data; results logged as `reviews mode=lesson` (LibreLingo/Preply).
- Error-pattern rollup tile "top 5 recurring patterns this month" (m98/fluent).
- One chart both users see: reviews/day + retention %.
- No typed input from the learner beyond the answer.

### What we should steal (10)
1. Anki note/card/revlog split — one item, three cards, one immutable log.
2. FSRS via ts-fsrs; store `stability, difficulty, due, state` on `cards`.
3. Lute's `wordparents`: form is the row, lemma optional link.
4. Duolingo trace columns on every review row.
5. m98/fluent's separate mistakes DB: error patterns with counts.
6. Echo-Loop: review the clip, not the word.
7. Preply Lesson Insights as the tutor-side product shape.
8. Migaku's Tracking/pinned status for tutor-flagged words.
9. Clozemaster's four-rung ladder as the tutor-facing label over FSRS.
10. Pimsleur's anticipation pause; WhisperLevantine/Scribe for ASR, not OpenPronounce.
