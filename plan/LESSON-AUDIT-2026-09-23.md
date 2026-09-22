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

- **2026-09-05**: spot checks (row start s, dBFS, speech): [(1241.9, -18.1, np.True_), (873.3, -18.3, np.True_), (208.8, -15.7, np.True_), (1557.3, -18.6, np.True_), (1544.4, -25.7, np.True_)] · row share: {'Amal': 0.41, 'Medi': 0.59}
- **2026-09-11**: spot checks (row start s, dBFS, speech): [(615.7, -105.0, np.False_), (1303.5, -15.4, np.True_), (2643.8, -16.6, np.True_), (2398.5, -11.9, np.True_), (602.9, -15.6, np.True_)] · row share: {'Amal': 0.42, 'Medi': 0.58} · 1 live Medi events not produced by today's matcher (older build or reviewed additions; kept)
- **2026-09-14**: spot checks (row start s, dBFS, speech): [(654.2, -17.3, np.True_), (1204.8, -12.6, np.True_), (2505.3, -11.3, np.True_), (2122.8, -14.7, np.True_), (621.7, -19.9, np.True_)] · row share: {'Medi': 0.63, 'Amal': 0.37}
- **2026-09-15**: spot checks (row start s, dBFS, speech): [(1136.3, -12.5, np.True_), (753.0, -15.0, np.True_), (167.9, -21.6, np.True_), (3976.2, -11.9, np.True_), (3061.0, -22.2, np.True_)] · row share: {'Amal': 0.42, 'Medi': 0.58} · 1 live Medi events not produced by today's matcher (older build or reviewed additions; kept)
- **2026-09-16**: spot checks (row start s, dBFS, speech): [(3080.4, -15.5, np.True_), (3661.5, -8.1, np.True_), (3152.4, -18.1, np.True_), (144.4, -17.4, np.True_), (1073.5, -16.6, np.True_)] · row share: {'Medi': 0.58, 'Amal': 0.42}
- **2026-09-17**: spot checks (row start s, dBFS, speech): [(2446.9, -20.8, np.True_), (352.6, -10.9, np.True_), (3514.9, -14.1, np.True_), (1825.6, -15.3, np.True_), (3224.8, -16.1, np.True_)] · row share: {'Amal': 0.43, 'Medi': 0.57} · 6 live Medi events not produced by today's matcher (older build or reviewed additions; kept)
- **2026-09-18**: spot checks (row start s, dBFS, speech): [(2033.0, -15.0, np.True_), (32.7, -21.8, np.True_), (351.4, -20.1, np.True_), (2556.0, -19.4, np.True_), (491.8, -18.3, np.True_)] · row share: {'Amal': 0.44, 'Medi': 0.56}
- **2026-09-19**: spot checks (row start s, dBFS, speech): [(148.8, -11.9, np.True_), (2670.7, -47.9, np.False_), (2980.7, -21.1, np.True_), (1283.8, -16.2, np.True_), (467.4, -11.9, np.True_)] · row share: {'Medi': 0.54, 'Amal': 0.46}
- **2026-09-21**: spot checks (row start s, dBFS, speech): [(276.4, -13.1, np.True_), (4039.4, -16.2, np.True_), (4260.8, -14.4, np.True_), (2347.8, -12.1, np.True_), (1499.2, -14.7, np.True_)] · row share: {'Medi': 0.63, 'Amal': 0.37}

## What was fixed tonight (generic fixes only)

- **09-14, 09-18, 09-21 loaded** (page + events + lesson row); 09-15 transcript now includes Amal's first 21 minutes.
- **Audio on every page**: new pages have one lesson mix with tap-a-time; 08-25, 09-04, 09-05 got a hosted audio bar (09-05 no longer asks to "Choose recording").
- **Amal's typed chat lines** on every page that has a Meet chat file (09-10 was missing all 33).
- **Speaker names for mixed recordings** come from voice pitch (the Arabic-share rule swapped Medi and Amal on 09-18).
- **Word Bank**: Doc form beats an engine guess for Arabic homographs (4 integrity failures on master → 0); verb forms no catalog form can place are held for review (8 on 09-21); words heard over silence in Medi's own track are not counted (1 new, 2 already excluded).
- **Review overlay works on plain pages** (it matched nothing on 09-15..09-19 before: rows had no ids).

## Still open (with date, line, time)

- **09-11 10:15** — Medi row "آآآ" is a filler the speech engine heard over digital silence (-106 dBFS). No word credited. Left in the transcript (raw evidence is never edited).
- **09-19 44:30** — Medi row "Oh, okay." is very quiet (-48 dBFS, just under the -45 dBFS "speech" line of this check). Probably real speech; worth one listen.
- **08-25, 09-04, 09-10** — their saved transcripts are not on this PC, so coverage and 5-line checks cannot be measured here; database = published file for all three.
- **09-16, 09-17** — 1–2 short reconnect segments (38–63 s at the very start, greetings) are still not transcribed.
