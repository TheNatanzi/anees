# Lesson audit — every lesson, 2026-09-23

Built by `scripts/audit_lessons.py` (re-runnable). ✅ pass · ❌ fail · — cannot be measured here.

| Lesson | Coverage | Speakers | Page + audio | 5 lines vs audio | Database | Word Bank | Chat merged | Reliability |
|---|---|---|---|---|---|---|---|---|
| 2026-08-25 | — | — ok | ✅ opens + audio | — | ✅ 293 events | ✅ transcript source not on this PC; published = live: True | ✅ no chat file | ✅ 0 |
| 2026-09-04 | — | — from voice pitch: ElevenLabs merged the two voices, so each word was labeled by pitch (Medi low, Amal high); ? = unclear | ✅ opens + audio | — | ✅ 147 events | ✅ transcript source not on this PC; published = live: True | ✅ 47/47 | ✅ 0 |
| 2026-09-05 | ✅ 62.3/62.7 min | ✅ tracks | ✅ opens + audio | ✅ 5/5 | ✅ 364 events | ✅ events built from an older transcript of this lesson; published = live: True | ✅ 55/55 | ✅ 0 |
| 2026-09-10 | — | — participant_tracks | ✅ opens + audio | — | ✅ 488 events | ✅ transcript source not on this PC; published = live: True | ✅ 33/33 | ✅ 0 |
| 2026-09-11 | ✅ 61.9/62.6 min | ✅ tracks | ✅ opens + audio | ❌ 4/5 | ✅ 327 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ no chat file | ✅ 0 |
| 2026-09-14 | ✅ 62.6/62.8 min | ✅ tracks | ✅ opens + audio | ✅ 5/5 | ✅ 331 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 45/45 | ✅ 0 |
| 2026-09-15 | ✅ 66.5/67.1 min | ✅ tracks | ✅ opens + audio | ✅ 5/5 | ✅ 222 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 72/72 | ✅ 0 |
| 2026-09-16 | ✅ 68.1/69.7 min | ✅ tracks | ✅ opens + audio | ✅ 5/5 | ✅ 251 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 69/69 | ✅ 0 |
| 2026-09-17 | ✅ 63.3/63.8 min | ✅ tracks | ✅ opens + audio | ✅ 5/5 | ✅ 311 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 41/41 | ✅ 0 |
| 2026-09-18 | ✅ 62.9/63.8 min | ✅ estimated, 0.0% unlabeled | ✅ opens + audio | ✅ 5/5 | ✅ 86 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 66/66 | ✅ 0 |
| 2026-09-19 | ✅ 62.1/62.1 min | ✅ tracks | ✅ opens + audio | ❌ 4/5 | ✅ 197 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 78/78 | ✅ 0 |
| 2026-09-21 | ✅ 72.1/72.2 min | ✅ tracks | ✅ opens + audio | ✅ 5/5 | ✅ 766 events | ✅ 20/20 bound to Medi's own words, 0 credited over silence | ✅ 57/57 | ✅ 0 |

## Details

- **2026-09-05**: spot checks (row start s, dBFS, speech): [(1241.9, -19.6, np.True_), (873.3, -23.3, np.True_), (208.8, -18.5, np.True_), (1557.3, -20.6, np.True_), (1544.4, -27.7, np.True_)] · row share: {'Amal': 0.41, 'Medi': 0.59}
- **2026-09-11**: spot checks (row start s, dBFS, speech): [(615.7, -106.6, np.False_), (1303.5, -20.7, np.True_), (2643.8, -19.4, np.True_), (2398.5, -14.5, np.True_), (602.9, -17.2, np.True_)] · row share: {'Amal': 0.42, 'Medi': 0.58} · 1 live Medi events not produced by today's matcher (older build or reviewed additions; kept)
- **2026-09-14**: spot checks (row start s, dBFS, speech): [(654.2, -16.2, np.True_), (1204.8, -12.0, np.True_), (2505.3, -11.0, np.True_), (2122.8, -14.3, np.True_), (621.7, -19.4, np.True_)] · row share: {'Medi': 0.63, 'Amal': 0.37}
- **2026-09-15**: spot checks (row start s, dBFS, speech): [(1136.3, -15.0, np.True_), (753.0, -17.6, np.True_), (167.9, -22.3, np.True_), (3976.2, -14.4, np.True_), (3061.0, -24.7, np.True_)] · row share: {'Amal': 0.42, 'Medi': 0.58} · 1 live Medi events not produced by today's matcher (older build or reviewed additions; kept)
- **2026-09-16**: spot checks (row start s, dBFS, speech): [(3080.4, -18.0, np.True_), (3661.5, -20.0, np.True_), (3152.4, -21.0, np.True_), (144.4, -36.7, np.True_), (1073.5, -22.8, np.True_)] · row share: {'Medi': 0.58, 'Amal': 0.42}
- **2026-09-17**: spot checks (row start s, dBFS, speech): [(2446.9, -23.4, np.True_), (352.6, -13.3, np.True_), (3514.9, -15.8, np.True_), (1825.6, -17.9, np.True_), (3224.8, -19.7, np.True_)] · row share: {'Amal': 0.43, 'Medi': 0.57} · 6 live Medi events not produced by today's matcher (older build or reviewed additions; kept)
- **2026-09-18**: spot checks (row start s, dBFS, speech): [(2033.0, -15.0, np.True_), (32.7, -21.8, np.True_), (351.4, -20.1, np.True_), (2556.0, -19.4, np.True_), (491.8, -18.3, np.True_)] · row share: {'Amal': 0.44, 'Medi': 0.56}
- **2026-09-19**: spot checks (row start s, dBFS, speech): [(148.8, -15.3, np.True_), (2670.7, -51.1, np.False_), (2980.7, -23.3, np.True_), (1283.8, -18.8, np.True_), (467.4, -14.5, np.True_)] · row share: {'Medi': 0.54, 'Amal': 0.46}
- **2026-09-21**: spot checks (row start s, dBFS, speech): [(276.4, -15.6, np.True_), (4039.4, -18.7, np.True_), (4260.8, -21.4, np.True_), (2347.8, -14.4, np.True_), (1499.2, -17.3, np.True_)] · row share: {'Medi': 0.63, 'Amal': 0.37}

## What was fixed tonight (generic fixes only)

- **09-14, 09-18, 09-21 loaded** (page + events + lesson row); 09-15 transcript now includes Amal's first 21 minutes.
- **Audio on every page**: new pages have one lesson mix with tap-a-time; 08-25, 09-04, 09-05 got a hosted audio bar (09-05 no longer asks to "Choose recording").
- **Amal's typed chat lines** on every page that has a Meet chat file (09-10 was missing all 33).
- **Speaker names for mixed recordings** come from voice pitch (the Arabic-share rule swapped Medi and Amal on 09-18).
- **Word Bank rules** (all generic, all in `scripts/review_new_lessons.py` / `review_silent_credits.py` / `word-bank-core.js`):
  - a form said with its pronoun wins ("هو انبسط" = past); else Amal's Doc form beats an engine guess (4 integrity failures on master → 0);
  - a verb form no catalog form can place is held for review (8 on 09-21);
  - one scored attempt per word per sentence (6 repeats: 4 on 09-14, 2 on 09-21);
  - speakers estimated from one recording (09-18) are never scored until a person checks (5 held);
  - a word heard while Medi's own track is silent is never counted (09-14 "shu" at 44:20).
- **Review overlay works on plain pages** (it matched nothing on 09-15..09-19 before: rows had no ids).

## Second opinion (Codex CLI, read-only, 2026-09-23)

14 findings on tonight's code. Fixed: rebase side (#1), shared audio between two calls on one day (#2), estimated speakers promoted (#3), silence rule skipped when a patch existed (#4), hourly job without clips / half-done dates forgotten (#5), new tracks never transcribed (#6), duplicate partial credits (#7), pronoun homograph (#8), review file written before its last check (#9), this audit comparing counts instead of events (#10), unaudited events counted as clean (#11), missing start/end of a recording not counted (#12), spot checks on the mix instead of Medi's own track (#13), fixed UTC-7 dates (#14).

## Still open (with date, line, time)

- **09-11 10:15** — Medi row "آآآ" is a filler the speech engine heard over digital silence (-106 dBFS). No word credited. Left in the transcript (raw evidence is never edited).
- **09-19 44:30** — Medi row "Oh, okay." is very quiet in his own track (-48 dBFS, just under this check's -45 dBFS line). Probably real speech; one listen settles it.
- **08-25, 09-04, 09-10** — their saved transcripts are not on this PC, so coverage and 5-line checks cannot be measured here; database = published file, event for event.
- **09-16, 09-17** — 1–2 short reconnect segments (38–63 s at the very start, greetings) are still not transcribed.
