# Lesson inventory — every recorded call, 2026-09-23

Built overnight 2026-09-22 → 23 from five sources. One row per recorded call.

- **Recall** = Recall.ai bot list read from the API (not the ledger). Tracks = one audio file per person.
- **Drive** = Meet recording in `G:/My Drive/Meet Recordings` (before 09-10) or `G:/My Drive/Google Meet/<code> - <date>` (from 09-10: Meet now makes one folder per call — the hourly job never looked there).
- **Gemini** = "Notes by Gemini" doc (read through the Drive connector) — used to decide lesson vs other meeting.
- **Local** = raw archive `C:\dev\anees\data\lessons\<date>`.
- **Site** = `docs/lessons/<date>.html` on master + `lessons` row in Supabase.

| Date | Recall | Drive | Gemini notes say | Local raw | Site before tonight | Verdict |
|---|---|---|---|---|---|---|
| 06-17 | – | ctn-wxzy-oms | SEO / ClickUp meeting | – | – | not a lesson |
| 06-26 | – | ejv-zzah-mai | SEO / PR meeting (chat: Ahmad Shahzad) | – | – | not a lesson |
| 07-01 | – | pxf-capc-hct | infrastructure / inventory meeting | – | – | not a lesson |
| 07-06 | – | nfe-frub-byu | Supabase / Claude co-work meeting | – | – | not a lesson |
| 07-23 | – | tmp-bmys-oap | AI strategy / WordPress meeting | – | – | not a lesson |
| 08-03 | – | yfe-ebxi-beq (2 files) | database / web-app meeting | – | – | not a lesson |
| 08-19 | – | wec-txfn-pbs | inventory / Shopify meeting | – | – | not a lesson |
| 08-22 | – | szh-hwnn-vxj | image metadata meeting (Akram) | audio + scribe (English only) | – | not a lesson |
| 08-23 | – | asj-zoww-pjq | image workflow meeting (Akram) | audio + scribe (English only) | – | not a lesson |
| **08-25** | – | vzq-tryv-mdw | Arabic lesson | yes | yes | lesson |
| 09-01 | – | vbu-dzsj-bpy | inventory / barcode meeting (chat: Akram Taha) | audio + scribe (English only) | – | not a lesson |
| **09-04** | – | jir-hcex-xzd + chat | Arabic lesson | yes | yes | lesson |
| **09-05** | 0a24c69c | mcy-upvb-dfn + chat | Arabic lesson | tracks + scribe per person | yes | lesson |
| **09-10** | 2ea4999a | ooi-ynnk-qsj + chat | Arabic lesson | tracks (3) | yes | lesson |
| 09-11 09:32 | – | hsu-zwfm-nhd + chat | meeting with Akram Taha | – | – | not a lesson |
| **09-11** | 7d02817b | none | (no notes) | tracks + scribe per person | yes | lesson |
| **09-14** | 6de5ab99 (was unledgered) | amx-vvgb-byj + chat | Arabic lesson | tracks + scribe per person | DB yes, page only on branch | lesson |
| **09-15** | b21296a5 | jgn-xdbs-yyq + chat | Arabic lesson | tracks + scribe per person | yes | lesson |
| **09-16** | e8a95e84 | rib-xzub-hou + chat | Arabic lesson | tracks + scribe per person | yes | lesson |
| **09-17** | f8e8ab78 | mac-ibio-kfx + chat | Arabic lesson | tracks + scribe per person | yes | lesson |
| **09-18** | **no bot** | **pki-dqkp-kyn + chat** | Arabic lesson (causative verbs, commands) | – | **no** | lesson — **found tonight** (earlier chats only searched the old folder) |
| **09-19** | 9fea328f | cuv-feor-sou + chat | Arabic lesson | tracks + scribe per person | yes | lesson |
| **09-21** | **0a2e82e1 (unledgered)** | kht-vfaq-bxh + chat | Arabic lesson (café role-play, cooking) | – | **no** | lesson — **found tonight**, tracks downloaded inside Recall's 7-day window |
| 09-21 15:03 | – | mqp-zwfh-wby | Akram: images + Shopify | – | – | not a lesson |

## Dates with no recording

- **Before 2026-08-25**: WhatsApp shows lessons with Amal since late 2025 (Medi asks "lesson today?" most weekdays), but none were recorded. Nothing to load.
- **09-06 → 09-09, 09-12, 09-13, 09-20, 09-22**: no Recall bot, no Drive recording, no Gemini notes. No evidence a lesson happened.
- **Calendar**: the connected Google Calendar (mahdiadibnatanzi@gmail.com) has no events at all, so it cannot show missing lessons. Lessons are booked on WhatsApp.

## Why lessons were missed (fixed tonight, part A4)

1. The hourly job only knows bots written in `recall_bots.json`. Bots made another way (09-14, 09-21) were never fetched.
2. The hourly job only scans `G:/My Drive/Meet Recordings`. Since 09-10 Meet saves every call in its own folder under `G:/My Drive/Google Meet/`, so 09-18 (no bot that day) was never seen.
3. The hourly job runs from the stale clone `C:\dev\anees` and has failed every hour since 09-16 ("unknown participant 'Ray Adib'" = the host account wc@adibs.com; then `git push` rejected).
