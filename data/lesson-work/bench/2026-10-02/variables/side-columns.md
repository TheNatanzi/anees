# Side columns for scoreboard A (2026-10-02)

Strict is the headline and is bench_score's own number (asserted). The other columns use the same runs, the same key and the same 2-of-3 rule.

| Engine | Runs | Strict | + cut-off | + ending (ه = و) | + both | At least 1 run | Cut-off adds | Ending adds |
|---|---|---|---|---|---|---|---|---|
| gemini-flash-t1 (baseline) | 3 | 53 | 54 | 54 | 55 | 56 | M025 | M042 |
| gemini-flash-v8-t1 | 3 | 53 | 55 | 54 | 56 | 55 | M025 M030 | M042 |
| gemini-flash-v7-t1 | 3 | 54 | 55 | 54 | 55 | 55 | M025 | - |
| gemini-flash-v1-t1 | 3 | 53 | 54 | 54 | 55 | 57 | M025 | M042 |
| gemini-flash-v4-t1 | 3 | 53 | 55 | 53 | 55 | 54 | M025 M030 | - |
| gemini-flash-v5-t1 | 3 | 53 | 55 | 53 | 55 | 56 | M025 M030 | - |
| gemini-flash-v0-t1 | 2 | 52 | 53 | 53 | 54 | 56 | M025 | M042 |
| gemini-flash-v12-t1 | 3 | 52 | 53 | 53 | 54 | 54 | M025 | M042 |
| gemini-flash-v3-t1 | 3 | 52 | 53 | 53 | 54 | 55 | M025 | M042 |
| gemini-flash-v2-t1 | 3 | 51 | 53 | 52 | 54 | 52 | M025 M030 | M042 |
| gemini-flash-v6-t1 | 3 | 51 | 53 | 52 | 54 | 55 | M025 M030 | M042 |
| gemini-flash | 3 | 51 | 52 | 52 | 53 | 55 | M025 | M042 |
| gemini-flash-v11-t1 | 3 | 50 | 52 | 51 | 53 | 53 | M025 M030 | M042 |
| gemini-flash-before | 3 | 49 | 51 | 50 | 52 | 52 | M025 M030 | M042 |
| gemini-flash-best-t1 | 3 | 49 | 50 | 50 | 51 | 53 | M025 | M042 |
| gemini-flash-v1h-t1 | 3 | 49 | 50 | 50 | 51 | 53 | M025 | M042 |
| gemini-flash-v4h-t1 | 3 | 49 | 51 | 49 | 51 | 51 | M025 M030 | - |
| gemini-flash-v10-t1 | 3 | 49 | 50 | 49 | 50 | 55 | M025 | - |
| gemini-flash-v9-t1 | 2 | 46 | 48 | 46 | 48 | 56 | M025 M030 | - |
| openai-audio | 3 | 24 | 24 | 24 | 24 | 25 | - | - |
| openai-audio-best | 3 | 21 | 21 | 21 | 21 | 22 | - | - |
| openai-audio-before | 2 | 20 | 20 | 20 | 20 | 20 | - | - |
| cohere-open | 3 | 15 | 15 | 15 | 15 | 15 | - | - |
| deepgram-ar | 3 | 13 | 13 | 13 | 13 | 13 | - | - |
| audar-open | 3 | 12 | 12 | 12 | 12 | 12 | - | - |
| audar-open-ar | 3 | 12 | 12 | 12 | 12 | 12 | - | - |
| cohere-api | 1 | 10 | 10 | 10 | 10 | 10 | - | - |
| openai-stt | 3 | 10 | 10 | 10 | 10 | 10 | - | - |
| speechmatics | 3 | 8 | 8 | 8 | 8 | 8 | - | - |
| eleven | 3 | 7 | 7 | 7 | 7 | 9 | - | - |
| openai-4o | 3 | 7 | 7 | 7 | 7 | 7 | - | - |
| eleven-raw | 1 | 4 | 4 | 4 | 4 | 4 | - | - |
| deepgram-multi | 3 | 3 | 3 | 3 | 3 | 3 | - | - |

## Scorer trap (reported, not patched)

- M020, truth `تنتين و ro--`: a faithful Arabic cut-off `تنتين و رو--` scores a MISS under the strict scorer (a hit in the cut-off column); the fragment finished in Latin letters `تنتين و rob3` scores a HIT under the strict scorer. 0 of 92 saved runs kept the fragment. bench_common.tokens glues a lone و to the next Arabic piece (و + رو = ورو), so the truth's '... و' is found only when Latin letters or nothing follow the و; and the Latin fragment itself is not required, so a finished Latin word still scores. Not patched: the normaliser is frozen.
