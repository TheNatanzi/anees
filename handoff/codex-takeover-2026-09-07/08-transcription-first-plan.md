# 08 — Transcription-first takeover plan

## 1. Reproduce the worst problems (no paid calls; ≈ 20 minutes)

```powershell
cd C:\dev\anees
# F5 script drift: same engine, same minute, two scripts
python - <<'EOF'
import json
def w(p,a,b): return ' '.join(x['text'] for x in json.load(open(p,encoding='utf-8'))['words'] if x.get('type')=='word' and a<=x['start']<=b)
print('tracks (Medi):', w('data/lessons/2026-09-05/scribe_Medi.json',1229,1243))
print('mixed Meet   :', w('data/lessons/2026-09-05/scribe_meet_mixed_1615.json',1229,1243))
EOF
# F1–F4 false words: the raw tokens are still there
grep -n "موز-\|Biz'a-\|za'aj?\|Hiya betin" data\lessons\2026-09-05\transcript.txt
# F12 merged voices on a mixed recording
python -c "import json;print(json.load(open('data/lessons/2026-09-04/summary.json',encoding='utf-8'))['speaker_split'])"
# F7/F8 tag spans: list audio events longer than 5 s on each track
python - <<'EOF'
import json
for who in ('Medi','Amal'):
    s=json.load(open(f'data/lessons/2026-09-05/scribe_{who}.json',encoding='utf-8'))
    print(who,[(x['text'],round(x['start']),round(x['end']-x['start'])) for x in s['words'] if x.get('type')=='audio_event' and x['end']-x['start']>5])
EOF
# then listen: ffmpeg -ss 1651 -t 34 -i data/lessons/2026-09-05/tracks/Amal.mp3 -y amal_laugh.mp3
```
Compare raw (`scribe_*.json`) with displayed (`docs/lessons/2026-09-05.html`): the only differences are dropped tags, `(pause)` for fillers and ✓ for confirmations (`03-…md` Stage 4).

## 2. Smallest useful transcript interface that already exists

`docs/lessons/<date>.html` (built by `lesson_pipeline.render`): speaker runs with mm:ss, pauses, ✓, Amal's typed chat lines, stats. It lacks: per-line audio play, per-line "wrong / fix" controls, the raw filler text, and audio-event markers. The report page already has the ▶ play mechanism (`<button class="play" data-clip data-off>` + one `<audio>`) and per-lesson clips. The Amal link pages already have the token mechanism (`amal_links`, `apply_rules`). **Completing the transcript page = add ▶ per run (clip cut from `audio.mp3` at the run's time), show fillers verbatim with a toggle, show event tags, and a per-run "fix" box (token-gated) writing to a `transcript_fixes` table.** That is a few hundred lines on top of existing code, not a rewrite.

## 3. Park while transcript quality improves

Report pages, buckets/flashcards, Slips tally, planner and after links, homework loop and `grade` edge function, WhatsApp house spelling, emails. Keep them building (tests) but stop tuning them; do not send Amal anything except the transcript review.

## 4. Reuse

`recall_bot.py` (capture), `ingest_tracks.py` (per-track ASR + merge + mix), `pipeline_ext` (retries, ledger), `lesson_text` (runs), `lesson_pipeline.render/publish` (page + push + 200 check), `understand_lesson.cut_clips` (ffmpeg clips), `amal_links` + Supabase RLS (review tokens), `tests/` (104), the Check 02 page pattern (blind A/B with tap answers) for human review.

## 5. Pipeline changes supported by evidence

- **Separate tracks are necessary** (Sep 4 merged voices vs Sep 5 0 % unlabeled; Codex 09-04 "high confidence").
- **Full-track ASR, not 25-s chunks** (Claude audit: 8/8 vs 5/8 learner events; tags replaced speech in chunk mode).
- **No vocabulary whitelist / keyterms on the primary pass** (Codex tests: vocabulary prompt worse; Medi's R16).
- **Never re-transcribe a date that already has raw output** (F9) and make the bot path the single entry point; the Meet recording is a chat-sidecar source only.
- **Raw evidence layer must be immutable and complete**: keep `spacing`/`audio_event` items and fillers in the stored stream; only the display collapses them.

## 6. Questions that need experiments, not discussion (each ≈ $0.25 on the Sep 5 tracks)

1. `language_code=ara` vs auto on Medi's track: does Arabic come out in Arabic script, and does English survive? (F5)
2. `diarize=false` / `num_speakers=1` on a single-person track: any change in words?
3. `no_verbatim=false` explicit vs default: identical output or not? (`tag_audio_events` off as a fourth arm.)
4. Do long `[laughs]` / `[audio cuts out]` spans hide words? (listen; then re-run the span as a clip)
5. Per-track Scribe vs the mixed recording on the **same** 20 windows, judged by Amal on a Check-02-style page — the first human error count.

## 7. Human review of the first 20 examples (protocol)

- Freeze 20 windows (20–25 s) from 2026-09-05 before looking at outputs: 8 Medi corrections (Amal recasts), 4 "I forgot / how do you say", 4 self-repairs or false starts (F1–F3 spans included), 4 random Arabic-heavy windows. Hash the clips.
- Page = Check-02 style, one window per screen, audio ▶, the two-track transcript for that window with editable text per run; reviewer (Amal for Arabic, Medi for his own attempts) taps "exact / minor / wrong" per run and types the fix. Store per run: reviewer, verdict, fixed text, seconds.
- Amal reviews Arabic runs; Medi reviews his own runs and confirms which attempts were deliberate errors. Time both (target ≤ 5 min for Amal on 20 windows).
- Score: per run, exact / minor / wrong; per window, learner-attempt preserved yes/no (Medi's call); speaker correct yes/no; timestamp within 1 s yes/no; inserted words not in audio (count). Keep the fixed text as the first **gold set**; every later engine or setting is measured against it.

## 8. Acceptance criteria for the milestone (measured on the gold set)

| Quality | Metric | Target for "trustworthy" |
|---|---|---|
| Completeness | runs marked "wrong" or missing words | ≤ 10 % of runs |
| Speaker attribution | runs with the wrong speaker | 0 with tracks; report unlabeled share |
| Learner attempts preserved | Medi-confirmed attempts present verbatim (not the target word) | ≥ 90 % |
| "I forgot / what does X mean" utterances | present | 100 % |
| Timestamps | ▶ lands within 1 s of the run | ≥ 95 % |
| Unsupported insertions | words/tags not in the audio | 0 tags replacing speech; ≤ 1 inserted word per 10 min |
| Script | Arabic said by either speaker rendered consistently (Arabic script, or Arabizi for Medi's page by transliteration of the Arabic — never engine-chosen) | decided by experiment 1 |
| Cost | per lesson, ledger | ≤ $3 |

Do not claim a percentage without the gold set; publish the gold set and the scoring script next to the number.

## 9. Not a rewrite

The capture, ASR call, ledger, merge, page build, publish, clip and token mechanisms work and are tested. The needed changes are: (a) keep the full raw stream (tags, fillers) in storage; (b) per-run audio + fix UI on the transcript page; (c) one entry point (bot) with the Meet folder as sidecar only; (d) the language-hint experiment; (e) the gold set. A rewrite would throw away the only parts that are proven.

---

## Paste for Codex

> You are taking over Anees (`C:\dev\anees`, branch master, HEAD 22a14a4). Read `handoff\codex-takeover-2026-09-07\START-HERE.md` first, then `03-transcription-pipeline-trace.md` and `04-failure-inventory.md`. Medi's priority is a trustworthy, audio-linked, speaker-certain transcript that he and Amal can correct; everything downstream is parked. Start by reproducing lesson 2026-09-05 from `data\lessons\2026-09-05\scribe_Medi.json` / `scribe_Amal.json` (no paid call), comparing them with `scribe_meet_mixed_1615.json` and with the displayed `docs\lessons\2026-09-05.html`, and locating where errors enter (script drift on Medi's track, audio-event spans, dropped fillers). Then run the five experiments in `08-transcription-first-plan.md` §6 on the Sep 5 tracks (≈ $0.25 each, ledger in `data\budget.json`, keys in the Windows User env, never in the repo) and build the 20-window human review page (§7) so the first gold set exists. Do not change downstream features, do not send Amal anything except the review page via Medi, and do not send audio to any provider whose terms allow training on uploads.
