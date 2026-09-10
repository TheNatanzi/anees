# Anees contracts (binding; supersede any conflicting wiki line)

### Current app labels (Medi, 2026-09-10)

Display `cold` as **Good** and `ice_cold` as **Mastered** throughout the app. This is a naming change only: retain the stored IDs, existing links, progress and scoring thresholds. The other four current bucket labels are unchanged. “Mastered” is the category name, not a new guarantee of proficiency.

### Current separate Speaking and Flashcards scores (Medi, 2026-09-10)

- **Two scores:** Speaking and Flashcards have independent buckets, errors, dates, streaks and recovery. Neither can promote or demote the other. Generic legacy `word_stats` score fields now mean Speaking only; `progress_scores` exposes both lanes explicitly.
- **You used it:** only timed recorded word occurrences labeled Medi, excluding typed homework. Prompted attempts count as uses; Amal/unknown speakers and untimed events never count. Speaking review dates, lesson counts, recent-use flags and learner error counts follow this same source filter.
- **Without help:** Medi use with explicit `prompted=false`, `asked=false`, `correction=false`, and no `choice`/`unclear` marker. These are detected transcript signals, not audio-verified success or pronunciation grades.
- **Recovery from Missed:** two consecutive independent successes within the same score: first → Shaky, second → Good. Known help/error in that lane interrupts recovery; unknown speech is neutral. The other lane has no effect. Recovery remains active while Shaky. Both successes also count toward mastery. Ordinary Shaky, outside Missed recovery, needs one independent success to reach Good.
- **Mastered:** five consecutive qualifying successes in the same score across at least three distinct dates. Speaking earns at most one independent success per word/lesson date; Flashcards uses first-try answers. Word corrections/help requests or prompted-only lessons break the Speaking streak. Existing word-vs-grammar bucket exceptions remain; a grammar-corrected attempt is not a clean mastery success.
- No cross-lane same-day precedence. Within Flashcards only, one miss after Mastered drops to Good; two misses in the last three answers drops to Missed.
- **Speaking New:** a cumulative target of five Medi spoken uses on/after the earliest explicit New mark or Doc introduction date. They may occur in one lesson; helped uses count as practice. Before five, display New. At five, reveal the underlying Speaking score—not automatic Good or Mastered. Later errors do not restart this introduction count. The Amal tab lists unfinished targets and remaining uses; nothing is sent automatically.
- **Flashcards New:** retain five consecutive first-try successes across two dates. Speaking practice never bypasses the drill; card answers never increase the Speaking introduction count.
- Database `word_stats` is derived. Both pages replay durable `card_results` plus unsynced local answer IDs into Flashcards only. No browser write access to stats is granted. Card sets and weighting use only Flashcards; Last 3 lessons is an explicit vocabulary filter, not a score or weighting input.
- Raw lesson/card evidence stays unchanged. Old combined/all-speaker caches are rejected. Provenance context v3 is rebuilt from raw events including `text`; explicit score format v1 and a fresh browser cache prevent relabeling old combined scores.

### Other contracts and historical proposals

The current separate-score rules above supersede older combined/item-level progression proposals below. Unimplemented FSRS/speak/type proposals are not the current score model.
| Contract | Value |
|---|---|
| Current word scores | Two independent scores, each using New / Missed / Shaky / Good / Mastered / never assessed. Old Recognised/Recalled/Spoken/Used/Kept levels are a superseded proposal, not current UI. |
| Headline metric | "Words I can say cold": **spoken** attempts only (typed does not count); first attempt on a due day; ≥7 days since last exposure; no hint; pass; trailing **28** days; dedup by item. |
| FSRS unit (future proposal) | Per card/mode scheduling may be evaluated later; it must not derive or change the lesson Speaking score. |
| Retention target | 0.90. |
| Caps | 8 new items/lesson · 25/week · 40 reviews/day · session 7 min. |
| Leech | warn at 4 lapses, flag+suspend at 8. |
| Grading v1 | speak mode records audio; **self-grade** (Again/Hard/Good/Easy) or Amal grades on the sheet. Automatic ASR grading = v2. |
| Audio | required only when an item enters speak practice; source = clip from the lesson recording at the utterance timestamp; if none, Amal records 3 s from the Inbox. Never bulk-generate. |
| Secrets | ElevenLabs + Anthropic keys live in Supabase Edge Function secrets only. Static page calls Edge Functions with the user's session token. |
| Trust test M0 | stratified gold sample from Aug 25: 20 Amal corrections, 10 "how do you say" gaps, 10 hesitation/self-repair lines, 10 random Arabic lines; plus speaker labels and timestamps on all 50. Thresholds: Arabic word accuracy ≥75%; speaker label accuracy ≥90%; hesitation/self-repair preserved ≥60%; extraction precision ≥70% on corrections, ≥70% on gaps, ≥50% on hesitations; grammar-slip extraction measured at M0 for information only (no gate; gated at L2 ≥60%). Any gated miss → fallback = Amal tags live, recordings secondary. |
| Pass ↔ rating | speak/type/flip all rate Again / Hard / Good / Easy (FSRS 1-4). **Pass = Good or Easy.** Again = fail. Hard = pass for scheduling but does NOT count toward the headline metric. |
| Item status from cards (superseded) | The old weakest-required-card hierarchy is not implemented and is not binding. Current Speaking and Flashcards scores are independent; see the rules above. |
| Fallback audio | if no clip exists when an item enters speak practice, the item shows "needs audio" on Amal's Inbox **and** on the Words row; she records 3 s from either place. Manual-add items get audio the same way. |
| Retention (audio) | raw lesson audio 90 days; 3-s item clips kept while the item exists; Medi's recorded speak attempts 30 days then deleted; transcripts and review rows kept. |
| Ingestion | idempotent by Drive file id; retry 3× with backoff; failed runs email Medi only; raw audio kept 90 days then deleted, transcripts kept; Amal can request deletion of any lesson. |
| Manual add | one form (word, meaning, optional note) on the Words tab for Medi or Amal; enters at status 0 with source=manual. |

| Error signal (added 2026-09-03 after Medi's check) | ASR auto-corrects learner errors (LearnerVoice finding, confirmed live). Primary miss signal = **Amal's correction/repeat, gaps, hesitations**, never Medi's transcribed form. Every miss keeps its audio clip. v2 experiment: no-LM phonetic engine (wav2vec2 CTC Arabic) to capture Medi's actual form. Check 01 gets an "Auto-fixed" button to measure the rate. |

| Recording (added 2026-09-03) | From the next lesson on, record TWO channels on Medi's PC: ch1 = Medi's mic, ch2 = system loopback (Meet = Amal). Speaker labels come from channels, never from AI guessing. Meet's own recording stays as backup. |
| Engines (revised) | Clean words: Speechmatics bilingual Ar-En (Palestinian named) or Soniox; batch fallback ElevenLabs. Raw learner form: wav2vec2 Levantine CTC (no LM) on ch1. Free local dialect Whisper stays as offline fallback. |

| Friction rule (Medi, 2026-09-03) | Repo is PUBLIC. No secrets in the repo, ever. Medi never types keys in PowerShell: Claude moves keys from Medi's clipboard into User env vars with a command that never prints them. Keys needed so far: HF_TOKEN (set), ELEVENLABS_API_KEY / SPEECHMATICS key (pending, same clipboard method). |

| Meeting accounts (HARD RULE, Medi 2026-09-05) | The lesson Meet is HOSTED by the business Workspace account wc@adibs.com (it records; the pipeline reads its Drive folder). Medi JOINS from his PHONE as thenatanzi@gmail.com. Amal joins as herself. Consequence: a PC recorder hears both voices through Meet, so per-person tracks need a Meet bot (Recall.ai) or a different call tool; the host account admits the bot. |
