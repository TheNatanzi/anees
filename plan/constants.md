# Anees contracts (binding; supersede any conflicting wiki line)

### CONTRACTS(one `plan/constants.md`, supersedes any conflicting line elsewhere in this file)
| Contract | Value |
|---|---|
| Word status | exactly 6: 0 New · 1 Recognised · 2 Recalled · 3 Spoken · 4 Used · 5 Kept. Tutor labels map onto these (new=0-1, shaky=2-3, solid=4, known=5). No other vocab. |
| Headline metric | "Words I can say cold": **spoken** attempts only (typed does not count); first attempt on a due day; ≥7 days since last exposure; no hint; pass; trailing **28** days; dedup by item. |
| FSRS unit | per **card** = item × mode (speak / type / flip). Item status derives from its cards. |
| Retention target | 0.90. |
| Caps | 8 new items/lesson · 25/week · 40 reviews/day · session 7 min. |
| Leech | warn at 4 lapses, flag+suspend at 8. |
| Grading v1 | speak mode records audio; **self-grade** (Again/Hard/Good/Easy) or Amal grades on the sheet. Automatic ASR grading = v2. |
| Audio | required only when an item enters speak practice; source = clip from the lesson recording at the utterance timestamp; if none, Amal records 3 s from the Inbox. Never bulk-generate. |
| Secrets | ElevenLabs + Anthropic keys live in Supabase Edge Function secrets only. Static page calls Edge Functions with the user's session token. |
| Trust test M0 | stratified gold sample from Aug 25: 20 Amal corrections, 10 "how do you say" gaps, 10 hesitation/self-repair lines, 10 random Arabic lines; plus speaker labels and timestamps on all 50. Thresholds: Arabic word accuracy ≥75%; speaker label accuracy ≥90%; hesitation/self-repair preserved ≥60%; extraction precision ≥70% on corrections, ≥70% on gaps, ≥50% on hesitations; grammar-slip extraction measured at M0 for information only (no gate; gated at L2 ≥60%). Any gated miss → fallback = Amal tags live, recordings secondary. |
| Pass ↔ rating | speak/type/flip all rate Again / Hard / Good / Easy (FSRS 1-4). **Pass = Good or Easy.** Again = fail. Hard = pass for scheduling but does NOT count toward the headline metric. |
| Item status from cards | item status = the level its **weakest required card** has earned: 1 needs flip pass; 2 needs flip+type pass; 3 needs speak pass; 4 needs speak-in-sentence pass; 5 = level 4 held ≥30 days with no Again on any card. Two consecutive Again on any card drops the item one level. |
| Fallback audio | if no clip exists when an item enters speak practice, the item shows "needs audio" on Amal's Inbox **and** on the Words row; she records 3 s from either place. Manual-add items get audio the same way. |
| Retention (audio) | raw lesson audio 90 days; 3-s item clips kept while the item exists; Medi's recorded speak attempts 30 days then deleted; transcripts and review rows kept. |
| Ingestion | idempotent by Drive file id; retry 3× with backoff; failed runs email Medi only; raw audio kept 90 days then deleted, transcripts kept; Amal can request deletion of any lesson. |
| Manual add | one form (word, meaning, optional note) on the Words tab for Medi or Amal; enters at status 0 with source=manual. |
