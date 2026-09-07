# 01 — Product history and decisions

Sources I can see: the repo (`plan/blueprint.md`, `plan/constants.md`, `plan/OVERNIGHT-LOG.md`, `plan/HANDOFF-2026-09-05.md`, `plan/AUDIT-STREAMLINE-2026-09-05.md`, `wiki/00–17`, `docs/data/ai_rules.json`), Claude's memory notes for this project (dated facts Medi stated), git history (70 commits 2026-09-03 → 09-05), and Codex's reports. **Not accessible:** the chat transcripts themselves before this session (2026-09-03 and 09-04 chats, the overnight build chat, the M10 chat run in parallel on 09-05). Where a decision below has no date or quote, it is reconstructed from a file, not from the conversation, and is marked *(file)*.

## 1. The original problem

Medi takes voice-only Palestinian Arabic lessons with Amal over Google Meet (60–70 min, ~weekly now; 3–4×/week was the target in early September). Amal keeps a Google Doc vocabulary list (~1,370 words on 2026-09-03, 2,120 by 09-05) and a grammar Doc; Quizlet did not record wrong answers; **nothing recorded which words Medi actually produced or missed in class** (`plan/blueprint.md` "Context"). Google Meet's own transcript renders Arabic as gibberish ("Camel" = kammel, "Buzzbot" = mazbout), so re-transcription from the recording was required from day one.

## 2. How the vision evolved (dated)

| Date | Step | Evidence |
|---|---|---|
| 2026-09-03 | Grill with Medi → "settled facts": both Medi and Amal use it; error signal = recordings first (+ manual add); struggle types = Amal corrected me · "how do you say" gaps · hesitation · grammar slips; Amal OK with cloud STT; web dashboard; #1 metric = words produced cold; Amal's time 5 min after class; **kill risk = "transcripts too wrong to trust"**; build our own | `plan/blueprint.md` "Grill results" |
| 2026-09-03 | Blueprint approved: 3 lanes (Medi 7-min practice / Amal after-lesson email with fixable transcript + suggestions / lesson) and milestones M1–M8; research wiki 01–13 written; engine research says ElevenLabs Scribe v2 primary, "verify in Phase 0" | `plan/blueprint.md`, `wiki/07`, `wiki/13` |
| 2026-09-03/04 | Trust test on the Aug 25 recording: local Whisper variants, Speechmatics, ElevenLabs auto/ara; Check 02 built for Amal (blind 20 clips) | `data/aug25/*`, `docs/check02-amal.html` |
| 2026-09-04 | Amal rates Check 02: ElevenLabs family 15/20, Speechmatics 5, local 2 → **ElevenLabs Scribe v2 confirmed as the engine** | `data/aug25/check02_results_amal.json` |
| 2026-09-04 | Codex independent test on the new Sep 4 lesson (OpenAI prompts vs ElevenLabs, then Speechmatics Melia): keep ElevenLabs, capture separate tracks (Zencastr → later Ennuicastr recommended), evidence layer vs display layer | Codex reports in `outputs/` |
| 2026-09-04 → 05 night | Overnight build M0–M8: Supabase spine, lesson understanding, report + email, Amal planner and after links, flashcards, homework, one site, hardening; Codex audits and "councils" at each milestone | `plan/OVERNIGHT-LOG.md` |
| 2026-09-05 morning | Medi checks the Sep 4 report word by word → miss classifier v2, 'new' bucket redefined three times until "ONLY words marked new" | log §"Miss classifier v2", memory |
| 2026-09-05 | Codex overnight ASR bake-off (Gemini, CrisperWhisper; xAI/Fish/Inworld researched) → keep ElevenLabs; Claude's adversarial audit softens three of its numbers | `outputs/anees-overnight-asr-bakeoff-report-2026-09-05.md`, `outputs/claude-adversarial-audit-2026-09-05.md` |
| 2026-09-05 | M10 (parallel chat): WhatsApp chat export as second source (house spelling, typed homework loop, `grade` edge function); Codex says NO-GO on privacy, Medi keeps lines public | log §M10 |
| 2026-09-05 | Recall.ai bot captures the lesson as two clean tracks (first success); `ingest_tracks.py` built the same evening | memory "Recall bot works", commit 67bce16 |
| 2026-09-05 | Teacher-brain wiki 17 (Claude + Codex blind reports merged); Medi redirects: **"keep a tally of my mistakes, don't write Amal plans"**; Slips page built; then four false words found on the Sep 5 report → rules M10; **"only count the words I say"** → rule M11 | commits 563c9a2 … 66a10e8 |
| 2026-09-05 | Process audit + streamlined correction session proposed (`check.html`, Amal notes) — **not built** | `plan/AUDIT-STREAMLINE-2026-09-05.md` |
| 2026-09-07 | Medi: **transcription quality first; everything else later** (this handoff) | this package |

## 3. Every material requirement or correction Medi gave (verbatim where recorded)

| # | Requirement / correction | When | Where recorded | Implementation today |
|---|---|---|---|---|
| R1 | Kill risk: "transcripts too wrong to trust" | 09-03 | blueprint grill | not resolved: no verbatim reference exists |
| R2 | Recordings are the error signal; manual add must exist | 09-03 | blueprint | recordings yes; manual add = "Future projects" |
| R3 | Repo is public; no secrets in the repo; Medi never types keys in PowerShell (clipboard → User env) | 09-03 | `plan/constants.md` "Friction rule" | followed |
| R4 | Meeting accounts HARD RULE: wc@adibs.com hosts and records; Medi joins from his phone as thenatanzi@; Amal as herself | 09-05 | `plan/constants.md`, memory | followed; consequence: two capture paths |
| R5 | Lessons are public by choice: audio, clips, transcripts on the open site; default provider retention accepted; only "train-on-uploads" providers need Amal's yes; Amal said yes to all of it (relayed by Medi) | 09-05 | rule A4 in `ai_rules.json`, memory | followed |
| R6 | Never contact Amal from code; links are minted, Medi sends them | 09-04/05 | rule A1 | followed (`send_lesson_email.mjs` hard-codes Medi) |
| R7 | No guessed number: unknown shows "–" and why | 09-05 | rule H1 | followed on pages |
| R8 | 'new' = LITERALLY only words marked new (Amal's mark, Medi's mark, or the Doc diff); no inference; Sep 4 = babse6 + banbese6 only | 09-05 | rule N1, memory | followed (`buckets.compute(confirmed_new=)`) |
| R9 | Medi's known hard grammar = ykun/akun after lamma/iza (M6); **pauses are never mistakes** (M7) | 09-05 | rules M6, M7 | M7 enforced; M6 planned pattern |
| R10 | Never ask Medi to review Arabizi spellings; best guess ships, Amal corrects | 09-05 | memory | followed |
| R11 | Grill Medi one question at a time on build-changing decisions; he states goals, not specifics | 09-05 | memory | process rule |
| R12 | Teacher brain = tally of Medi's mistakes per learned rule, for Amal to inject review into HER plans; never write plans or questions for her | 09-05 | rule M9, wiki 17 §K | followed (Slips page) |
| R13 | "ba6lub min is a preposition error, I make a lot of these" → its own kind | 09-05 | rule M8 | followed |
| R14 | "I paused here, I was trying to say maz3ooj" (Moz), same for Besse, Joaz, heyye/7ayye → cut-off tokens are never words | 09-05 | rule M10 | followed |
| R15 | "We only want to count the words I say" | 09-05 | rule M11 | followed (report new/reused Medi-only) |
| R16 | Transcription first; preserve attempts, repetitions, false starts, uncertainty; audio-linked transcript Amal and Medi can correct; measure against human-reviewed audio | 09-07 | this handoff | **the next milestone** |

## 4. Where the implementation diverges from those requirements

- R1/R16: the system ranks "possible misses" and grades grammar on top of a transcript nobody has verified; the transcript page collapses fillers into `(pause)` (raw filler text survives only in `scribe*.json`) and marks confirmations ✓, i.e. it is already a light display layer, not a verbatim one.
- R4 + bot: the HARD RULE makes the host record to Drive while the bot records tracks → the same lesson can be processed twice (happened 2026-09-05 16:15).
- "Amal's time 5 min": her links exist but were never sent; nothing has been measured with her.
- "$3/lesson": actual = Scribe 0.46 + Recall ≈ 0.65 + OpenAI ≈ 0.30 (after-link sentences) ≈ $1.4; the 16:15 re-run added 0.23 + 0.32.

## 5. Decisions Medi explicitly approved (with reference)

- Blueprint and lane flow (2026-09-03, blueprint "flow approved").
- Plan tool = visual-plan artifact (2026-09-03).
- ElevenLabs Scribe v2 as engine, via Amal's Check 02 (2026-09-04; Medi relayed her ratings).
- Public data posture A4 (2026-09-05, explicit).
- Meeting accounts rule (2026-09-05, "HARD RULE" in his words).
- 'new' definition N1 (2026-09-05, in caps).
- Rules M6–M11 (2026-09-05, each from a sentence of his).
- Spelling gate waived (2026-09-05, commit 448800a "spelling gate waived by Medi (standing rule)").
- WhatsApp lines stay public despite Codex NO-GO (2026-09-05, log §M10).
- Recall.ai bot as capture (2026-09-05; he joined from his phone and the run was accepted).

## 6. Ideas proposed by the assistants that were never approved

- Two-channel PC recording (mic + WASAPI loopback) — `plan/constants.md` "Recording (added 2026-09-03)"; superseded by the bot after PC recorders could not split voices.
- Zencastr (Codex 09-04) and Ennuicastr (Codex 09-04 later, Claude 09-05 as fallback) as the lesson call — never used; Meet + bot won.
- Speechmatics / Soniox as "clean words" engine with wav2vec2 CTC as "raw learner form" (`constants.md` "Engines (revised)") — never built; wav2vec2 parked.
- A learned-word whitelist for ASR — rejected by Codex and Claude; Medi's R16 now forbids it.
- FSRS scheduler, 6 word statuses, leech rules, retention targets (`constants.md`) — designed, only partly built (buckets, not FSRS).
- Ten lesson plans for Amal (wiki 17 §E) — Medi: internal only, never for her.
- Council "scores" (8/10 etc.) as gates — assistant device, no Medi ruling.
- `check.html` correction page and Amal notes box (`plan/AUDIT-STREAMLINE-2026-09-05.md`) — proposed 09-05, Medi said "Yes" to the audit direction on 09-07 but redirected to transcription first.

## 7. Abandoned approaches and why (concrete)

| Approach | Reason abandoned | Evidence |
|---|---|---|
| Google Meet Gemini transcript | no Arabic ("Camel", "Buzzbot") | blueprint findings |
| Whisper large-v3 local | Standard-Arabic bias, drops dialect words; 857 s per lesson | engine report |
| Dialect Whisper (oddadmix) + ECAPA/pyannote speaker split | invents words in silence ("إيه ده!"); lost 13-0 to ElevenLabs in Amal's vote | engine report, check02 |
| whisperx alignment | never ran (torchvision / nltk errors) | engine report |
| Speechmatics ar+en | 5/20 vs 15/20; turned Medi's Arabic into English ("But Anna Cartier") | check02, engine report |
| OpenAI gpt-4o-transcribe(-diarize) | German hallucination for Medi; refuses prompt; 0 fillers with strict prompt | engine report, Codex 09-04 test |
| 25-s clip chunking for ElevenLabs | lost 3 of 8 learner events vs full track (Claude audit) | `claude-adversarial-audit-2026-09-05.md` |
| Gemini 3.5 Transcribe, CrisperWhisper 2.0 | did not beat Scribe on preservation; CrisperWhisper loops | Codex bake-off |
| Fish Audio | terms allow training on uploads; no verbatim controls | Codex Fish report |
| Pitch-based speaker labels | fallback only (13.6 % unlabeled on Sep 4); replaced by tracks | `summary.json` Sep 4 |
| Tutor-reaction detector on one channel | precision 0.50 / recall 0.70 at best: "weak, not usable" | wiki 15 |
| Note-takers (Fireflies, Otter, Wispr…) | clean transcripts, no Arabic dialect, auto-correct learners | wiki 13 |

## 8. Outstanding decisions and assumptions

- **Language hint per track** (force `ara` on Medi's track?) — untested; today Medi's Arabic comes out in Latin on his own track.
- **Which capture path is canonical** when both exist (bot vs host recording) — assumed bot; the hourly job still runs.
- **Display of fillers**: `(pause Ns)` vs verbatim "um / آآ" — assumed pause display (M7 says pauses are never errors); R16 may want verbatim.
- **Amal's review surface**: her after link (5 taps) vs a full transcript with per-line fix — R16 implies the latter; nothing built for line-level fixing.
- **Retention**: constants say raw audio 90 days; nothing deletes anything today (rule "lesson audio never deleted").
- **Who is the reference**: "expected wording" needs Amal; her time is the scarce resource.
- **Budget**: $3/lesson stated by Medi as acceptable (his prompt 09-07); ledger caps are $10 total per service.

## 9. Diagrams and plans (all preserved in the repo)

- `plan/blueprint.md`: 5 Mermaid diagrams (flow chart, word cycle, milestones, mind map, tech stack) and the M1–M8 milestone graph; `plan/graph.yaml` task graph.
- `wiki/09-codex-reviews.md`: wiki mind map (Mermaid); `wiki/16-codex-independent-test-2026-09-04.md`: architecture diagram; `wiki/16-…pdf`: Codex research & architecture PDF; `outputs/anees-research-and-architecture.pdf`.
- `plan/OVERNIGHT-BUILD-2026-09-05.md` (the 8-milestone build prompt), `plan/OVERNIGHT-LOG.md` (what happened), `plan/HANDOFF-2026-09-05.md`, `plan/MORNING-CHECKLIST.md`, `plan/AUDIT-STREAMLINE-2026-09-05.md`.
- `docs/data/ai_rules.json`: the 30 standing rules (E1–E6, S1–S3, M1–M11, N1–N5, A1–A4, H1–H4, R1–R2) shown on the site's rules tabs — the closest thing to a decision log.
- Live plan artifact (claude.ai) referenced in `README.md`; Medi's account only.
