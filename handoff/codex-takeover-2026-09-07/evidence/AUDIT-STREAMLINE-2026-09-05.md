# Process audit + the streamlined correction session (2026-09-05, after lesson 3)

One line: **the pipeline now gets the words and the speakers right; what is still slow is the correction loop (Medi's verdicts arrive by chat, Amal's notes do not arrive at all).**

## 1. Audit: every stage, what broke today, what holds now

| # | Stage | Today (Sep 5) | Status | Open risk |
|---|---|---|---|---|
| 1 | **Capture** – Recall bot, one mp3 per person | worked first time: Medi 62:43, Amal 62:17, 0 % unlabeled | DONE | bot joined by hand (`recall_bot.py join`); no calendar auto-join yet; files leave Recall after 7 days |
| 2 | **Meet chat sidecar** – Amal's typed lines | 55 lines found (via the host's Meet recording folder) | DONE, but only when `ingest_tracks --src <Meet recording>` is given | the bot run and the Meet recording are two separate paths; must be joined by hand |
| 3 | **WhatsApp lines** (M10, other session) | merged as ground truth for spelling | DONE | export is manual (WhatsApp → `data/whatsapp`); goes stale |
| 4 | **Transcription** – Scribe v2 per track, full track, no keyterms | 0.46 USD, ~40 s; Latin output for Arabizi words (banza'aj, shaban) | DONE | engine spelling of new words stays messy until Amal's Doc has them |
| 5 | **E1 write-once** | VIOLATED at 16:15: hourly task re-transcribed the mixed Meet audio, overwrote scribe/transcript/summary, emailed Medi twice, republished a worse page | FIXED (process() now reuses an existing scribe.json) | the hourly task still looks for Meet recordings; a bot lesson + a Meet recording = two candidates for one lesson |
| 6 | **Word matching** (Doc words in the transcript) | 4 false words from stumbles: موز- → Moz, biz'a- → Besse, za'aj → Joaz, heyye → 7ayye | FIXED (M10: false starts, 2-consonant guard, pronoun shapes) | short Doc words (3 letters) remain the most likely false hits; a fuzzy tier still exists |
| 7 | **Miss classifier** (word / choice / article / gender / tense / plural / preposition / pronunciation) | el- on العاصفة flagged as a slip (wrong); ya3ni picked as "wanted word" (wrong) | FIXED both; 'preposition' kind added (M8) | b-drop, ykoon, pointer, agreement patterns (wiki 17 G1–G15) are not built: the tally is hand-curated |
| 8 | **Report page** | counted 40 Amal-only words as new / reused | FIXED (M11: only Medi's words count; "heard from Amal" listed apart) | "possible misses" still need a human tap; 7 open for Sep 5 |
| 9 | **Clips** | 103 of 106 never reached the site (`*.mp3` git-ignored) | FIXED (`git add -f` in publish) | none |
| 10 | **Slips tally** (rule → slips → review due) | 14 slips / 7 rules / 3 lessons, all verified against the transcript | DONE, hand-curated | updates only when Claude reads the transcript; not yet automatic |
| 11 | **Amal's links** (planner before, after-link after) | after link minted twice today, sent 0 times; planner link not sent this morning | BUILT, unused | her verdicts are the only thing that turns "possible miss" into fact; without them every council score stays < 8 |
| 12 | **Medi's corrections** | 5 today, all typed into this chat | WORKS, but costs a chat each time | no page where Medi taps "I didn't say this / that was a pause / preposition error" |
| 13 | **Amal's notes** | none exist | MISSING | her lesson plan and her view of what went wrong never enter the system |
| 14 | **Emails** | 3 report emails for one lesson (16:0x by hand, 16:15 and 16:18 by the task) | noisy | one email per lesson, only after the human check (see §2) |
| 15 | **Scheduling** | hourly task = Meet-recording watcher; bot = manual | split | one lesson entry point needed (§3) |

Costs today: Scribe 0.69 USD (0.46 tracks + 0.23 wasted on the re-run), OpenAI 0.60 USD (two after-link generations), Recall ≈ 0.65 USD. Budget cap 10 USD, fine.

## 2. The streamlined session: one 15-minute "Check this lesson" pass, one page, one order

Today the corrections arrived in five chat messages over an hour. Replace that with **one page, one token, one sitting**, in the order that removes the most noise first:

```
report email (one, after the pipeline)  →  Medi: check.html (15 min, phone)  →  Amal: after.html (5 min, only what Medi left open)  →  tally + buckets re-score  →  Slips page + cards update
```

`docs/check.html?t=<Medi's token>` (same link mechanism as Amal's; also closes the P1 "anon can insert" hole), five screens, one tap per row:

1. **Not my word** – every "possible miss" and every "new / reused" row with ▶ audio: *I said it · I did not say it (pause / stumble / Amal) · wrong word matched*. (Today: Moz, Besse, Joaz, 7ayye would have been four taps.)
2. **What kind of slip** – each miss: *Right · Wrong word · Wrong grammar (el- / gender / tense / plural / preposition) · Pronunciation · Not sure*. Medi's tap sets `miss_kind` as a `medi_verdict`; Amal's later tap overrides (A2).
3. **Slips tally** – the lesson's rows from `data/tally.json`: *Yes, that was the slip · No · It was a pause (M7)*.
4. **New words** – Medi confirms which words Amal actually introduced (N1): the "new" bucket is fed only from here or from Amal's after link.
5. **Note to Amal** – optional one line ("I could not do the N in biz3ejni"); it lands at the top of her after link.

What it writes: `amal_rules`-style rows with `kind='medi_verdict'` (event id, verdict, time); `apply_rules.py` already re-scores by event id. Everything Medi settles disappears from Amal's link, so hers stays ≤ 5 questions (A3).

Then the pipeline sends **one** report email, after Medi's pass, with the corrected numbers.

## 3. Amal's notes: three ways in, ranked by how little she has to change

| Way | What she does | What we get | Effort for her | Verdict |
|---|---|---|---|---|
| **A. After-link notes box + voice memo** | on the after link she already gets: one free-text box "Anything you want Medi to review?" and a hold-to-talk button (Scribe transcribes, 15 s cap) | her view of the lesson, in her words, tied to the lesson date, stored with her verdicts | 30 s, no new tool | **do first** (2 h of work: textarea + audio upload to Supabase + Scribe call through the ledger) |
| **B. "Lesson notes" heading in her own Materials Doc** | she types 2–3 lines under a dated heading in the Doc she already owns; the hourly Doc import reads it (needs the publish-to-web URL Medi still owes) | durable notes she controls, versioned by date, no link needed | 1 min, in a Doc she already edits | **do second** (blocked on the Doc URL; 1 h once unblocked) |
| **C. WhatsApp after-lesson message** | she sends a text or voice note to the same WhatsApp chat right after the lesson | already exported for M10; voice notes need Scribe | 30 s, but the export is manual and lags days | keep as fallback, not the system |

Not recommended: asking her to fill the planner **and** the after link **and** notes as three separate things. One link after the lesson, notes inside it.

## 4. Corrections still open from the last lesson (Sep 5)

- 7 possible misses need a tap: 5alli, kulshi, Ziaadeh ×2, Mabsoo6, maz3ooj, ana baz3ej, bsur3a, shab3an ×3 (some are one word said three times).
- "Heard from Amal, not said by you" (37 words): Medi to skim once; any word he did say is a speaker-label or matcher bug worth a note.
- Tally rows to confirm: R10 (بيزعجوني, subject ending), R1 self-repair at 59:17, R2 rights at 55:16 / 55:32, R7 right at 43:17.
- Sound candidates (audio only): nitla, Luka, أزآن, شبعان-heard-as-hot.
- Amal's after link: minted (`data/lessons/pipeline.log`, latest token), never sent. Send it tonight; her five verdicts are worth more than everything above.
- WhatsApp export: refresh after her reply.

## 5. Order of work (next chat, fresh)

1. `check.html` + Medi token + `medi_verdict` rows + re-score (the correction session, §2). 
2. One lesson entry point: `ingest_tracks --src` becomes the default path; the hourly task skips a date that already has `scribe.json` (done) **and** skips a Meet recording whose date has bot tracks (todo, 20 lines).
3. Amal notes way A on the after link.
4. Calendar auto-join for the bot (Recall API + Google Calendar connector).
5. Classifier rows G1–G3, G5–G6 on the transcript so the tally fills itself; Medi's verdicts become the test set.
