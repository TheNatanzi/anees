# Morning checklist — 2026-09-05 (≤ 20 min, do it before 11:00)

Rule for every step: **any FAIL → do NOT send Amal the link.** Fix it or ask Claude; nothing here is urgent enough to send a broken link.
The two links are in `data/amal_links.json` (gitignored; never in the repo or on the site). Lesson at 13:30. Send the planner link 11:00–11:30.

| # | Step (what to do) | PASS looks like | If FAIL |
|---|---|---|---|
| 1 | Open PowerShell in `C:\dev\anees` and run `python scripts/morning_check.py` (≈ 4 min, read-only + tests) | last line `ALL GOOD — 15/15 checks passed` | it prints the fix under each FAIL; do that, re-run; still FAIL → do NOT send the link |
| 2 | Open https://thenatanzi.github.io/anees/ on your PHONE | Today tab shows numbers (not "–"), tabs switch, no sideways scroll | if the amber "Supabase is not reachable" banner shows: open supabase.com → project **anees** (org "anees") → Restore/unpause; then refresh |
| 3 | Words tab: type `mabsoot` | Mabsoo6 / مبسوط / Happy is the first row, with a bucket badge | tell Claude "words search broke"; do NOT send the link (the planner used the same word data) |
| 4 | Flashcards tab → Start (default = Missed) → flip one card → tap Got it → ‹ Sets | card flips, buttons work, footer says "All answers saved." | footer says "waiting to sync" for > 1 min while online → Supabase problem (step 2 fix) |
| 5 | Open the report email "Anees: lesson report 2026-09-04", tap **Open the report**, tap one ▶ | audio plays the moment | 404 → run `git push` in `C:\dev\anees`; no sound → tell Claude "clips do not play" |
| 6 | Open `data/amal_links.json`, copy the **before** link (plan.html) and open it on your phone AS AMAL. Answer screen 1 (tap a topic) only. Close it. | the screen said "1 of 3", buttons were big, tapping saved without typing | anything confusing on that first screen → do NOT send; tell Claude what was confusing |
| 7 | Re-open the same before link | it resumes at "2 of 3" (your topic tap was saved) | if it restarts at 1 of 3 → do NOT send; tell Claude "planner does not resume" |
| 8 | Do NOT finish the planner as Amal. Instead run `python scripts/amal_links.py create --kind before --date 2026-09-05 --payload data/planner_payload_2026-09-05.json` to mint a **fresh** link (your test taps stay on the old one) | it prints a new plan.html URL and `data/amal_links.json` gained a line | error → Supabase (step 2) or keys missing; tell Claude |
| 9 | Paste the fresh link into a message to Amal (text in HANDOFF, one sentence), but **only after steps 1-8 pass**. Send at 11:00–11:30. Do not send the after-lesson link yet | Amal has one link, one sentence | — |
| 10 | After the 13:30 lesson: the hourly task runs at :15. By ~15:30 you get the transcript email and the report email; the after-lesson link for that lesson is printed in `data/lessons/pipeline.log` (grep `after_link`). Send it to Amal in the evening with the sentence from HANDOFF | two emails arrived; `pipeline.log` has `after_link` | no email by 16:00 → run `python scripts/lesson_pipeline.py` by hand and read its last lines; a failure email also arrives automatically |

Budget tonight: ElevenLabs 0.00 USD, OpenAI ≈ 0.44 USD (ceiling prices). Today's lesson will cost ≈ 1.50 USD ElevenLabs + ≈ 0.10 USD OpenAI.

Known limits (not FAILs):
- The hourly **Doc import** re-reads last night's snapshot until you publish the Doc to the web: Doc → File → Share → Publish to web → copy link → set `ANEES_DOC_PUBLISHED_URL` (Claude can store it from your clipboard). Until then new Doc words appear only after Claude re-exports.
- Per-speaker facts on a merged-voice recording (like Sep 4) come from voice pitch with ~14 % unlabeled words; the page says so. Two-track recording (Craig/Ennuicastr) is still the real fix.
