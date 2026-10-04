
### A - Plain transcribers (audio only)

| Engine | Mode | Heard right (of 63) | Real mishearings fixed (of 32) | English-letter Arabic fixed (of 31) | Slips hidden (of 24) | Lines changed of 519 (words changed, not just the alphabet) | All Arabic words right | Wrong alphabet lines | Same answer 3 of 3 | Runs | Sec / lesson | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Deepgram nova-3 (ar) | whole file | **21** (33.3%) | 10 | 11 | 1 | 244 (words: 191) | 50.0% | 0 | 100.0% | 3 | 109 | $0.83 |
| Cohere transcribe-arabic-07-2026 (local, ar) | per line | **15** (23.8%) | 5 | 10 | 1 | 308 (words: 259) | 42.0% | 0 | 100.0% | 3 | 69 | $0.00 |
| Deepgram nova-3 (ar) | per line | **13** (20.6%) | 4 | 9 | 0 | 375 (words: 329) | 42.7% | 0 | 100.0% | 3 | 302 | $0.43 |
| ElevenLabs Scribe v2 (fresh runs) | whole file | **12** (19.0%) | 7 | 5 | 0 | 33 (words: 22) | 74.3% | 3 | 36.5% | 3 | 15 | $0.47 |
| Audar ASR V1 Turbo (local, auto) | per line | **12** (19.0%) | 6 | 6 | 2 | 305 (words: 262) | 42.2% | 0 | 100.0% | 3 | 888 | $0.00 |
| Audar ASR V1 Turbo (local, forced ar) | per line | **12** (19.0%) | 7 | 5 | 3 | 404 (words: 366) | 47.3% | 0 | 100.0% | 3 | 992 | $0.00 |
| OpenAI gpt-transcribe | per line | **10** (15.9%) | 6 | 4 | 1 | 139 (words: 93) | 28.6% | 9 | 100.0% | 3 | 587 | $0.60 |
| Cohere transcribe-03-2026 (API, ar) | per line | **10** (15.9%) | 2 | 8 | 2 | 432 (words: 389) | 30.3% | 0 | 100.0% | 1 | 2903 | $0.00 |
| Speechmatics ar_en enhanced | whole file | **9** (14.3%) | 5 | 4 | 1 | 138 (words: 97) | 25.2% | 0 | 100.0% | 3 | 100 | $1.28 |
| Speechmatics ar_en enhanced | per line | **8** (12.7%) | 7 | 1 | 2 | 144 (words: 102) | 23.3% | 0 | 100.0% | 3 | 1139 | $0.66 |
| OpenAI gpt-4o-transcribe | per line | **7** (11.1%) | 5 | 2 | 0 | 141 (words: 109) | 25.0% | 31 | 98.4% | 3 | 255 | $0.60 |
| ElevenLabs Scribe v2 (fresh runs) | per line | **7** (11.1%) | 3 | 4 | 0 | 150 (words: 99) | 28.6% | 69 | 88.9% | 3 | 672 | $0.36 |
| ElevenLabs Scribe v2 (today's transcript) | per line | **4** (6.3%) | 4 | 0 | 1 | 0 (words: 0) | 83.3% | 5 | 100.0% | 1 | 0 | $0.00 |
| Deepgram nova-3 (multi) | per line | **3** (4.8%) | 1 | 2 | 0 | 150 (words: 118) | 6.1% | 2 | 100.0% | 3 | 756 | $0.52 |
| Deepgram nova-3 (multi) | whole file | **3** (4.8%) | 1 | 2 | 0 | 151 (words: 125) | 3.9% | 0 | 100.0% | 3 | 65 | $1.00 |

### A - Listeners (audio + lesson context)

| Engine | Mode | Heard right (of 63) | Real mishearings fixed (of 32) | English-letter Arabic fixed (of 31) | Slips hidden (of 24) | Lines changed of 519 (words changed, not just the alphabet) | All Arabic words right | Wrong alphabet lines | Same answer 3 of 3 | Runs | Sec / lesson | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemini 3.8 Flash + context, temperature 1 | per line | **53** (84.1%) | 27 | 26 | 1 | 96 (words: 59) | 84.5% | 0 | 90.5% | 3 | 198 | $2.02 |
| Gemini 3.8 Flash + context | per line | **51** (81.0%) | 26 | 25 | 2 | 100 (words: 62) | 83.3% | 0 | 87.3% | 3 | 676 | $2.04 |
| Gemini 3.8 Flash, context before only | per line | **49** (77.8%) | 23 | 26 | 1 | 96 (words: 61) | 83.5% | 0 | 84.1% | 3 | 310 | $1.74 |
| OpenAI gpt-audio-1.5 + context | per line | **24** (38.1%) | 14 | 10 | 11 | 310 (words: 275) | 70.1% | 0 | 95.2% | 3 | 560 | $5.47 |
| OpenAI gpt-audio-1.5, context before only | per line | **20** (31.7%) | 10 | 10 | 5 | 289 (words: 248) | 64.1% | 0 | 100.0% | 2 | 393 | $3.26 |

### B - score closeness (truth: Words 83.1%, Grammar 93.8%, 21 slips, 240 uses)

| Engine | Mode | Words % | off by | Grammar % | off by | Slips still visible | Uses counted |
|---|---|---|---|---|---|---|---|
| ElevenLabs Scribe v2 (today's transcript) | per line | 83.1 | 0.0 | 95.1 | 1.3 | 17 | 226 |
| Gemini 3.8 Flash + context, temperature 1 | per line | 83.3 | 0.2 | 95.8 | 2.0 | 17 | 264 |
| Gemini 3.8 Flash + context | per line | 83.1 | 0.0 | 96.2 | 2.4 | 16 | 266 |
| ElevenLabs Scribe v2 (fresh runs) | whole file | 81.5 | 1.6 | 95.0 | 1.2 | 16 | 200 |
| Gemini 3.8 Flash, context before only | per line | 85.6 | 2.5 | 95.8 | 2.0 | 15 | 263 |
| OpenAI gpt-4o-transcribe | per line | 81.0 | 2.1 | 97.0 | 3.2 | 5 | 101 |
| Deepgram nova-3 (ar) | whole file | 80.9 | 2.2 | 97.5 | 3.7 | 10 | 203 |
| Deepgram nova-3 (ar) | per line | 81.8 | 1.3 | 98.9 | 5.1 | 8 | 277 |
| OpenAI gpt-audio-1.5, context before only | per line | 84.3 | 1.2 | 99.0 | 5.2 | 10 | 616 |
| OpenAI gpt-audio-1.5 + context | per line | 86.0 | 2.9 | 98.6 | 4.8 | 10 | 508 |
| Cohere transcribe-arabic-07-2026 (local, ar) | per line | 80.3 | 2.8 | 99.0 | 5.2 | 6 | 304 |
| Audar ASR V1 Turbo (local, auto) | per line | 78.6 | 4.5 | 99.0 | 5.2 | 7 | 293 |
| Audar ASR V1 Turbo (local, forced ar) | per line | 77.9 | 5.2 | 98.9 | 5.1 | 12 | 535 |
| Speechmatics ar_en enhanced | whole file | 76.2 | 6.9 | 98.0 | 4.2 | 4 | 101 |
| ElevenLabs Scribe v2 (fresh runs) | per line | 75.0 | 8.1 | 97.1 | 3.3 | 6 | 103 |
| Cohere transcribe-03-2026 (API, ar) | per line | 76.1 | 7.0 | 99.6 | 5.8 | 5 | 496 |
| Speechmatics ar_en enhanced | per line | 72.2 | 10.9 | 97.9 | 4.1 | 4 | 97 |
| OpenAI gpt-transcribe | per line | 70.7 | 12.4 | 97.3 | 3.5 | 8 | 111 |
| Deepgram nova-3 (multi) | whole file | 62.5 | 20.6 | 100.0 | 6.2 | 0 | 36 |
| Deepgram nova-3 (multi) | per line | 50.0 | 33.1 | 100.0 | 6.2 | 1 | 51 |

### A by kind of mistake (moments heard right)

| Engine | Mode | el- | foreign-script | kept-slip | latin-arabic | number-time | short-repeat-english | vowel | wrong-arabic-word |
|---|---|---|---|---|---|---|---|---|---|
| Deepgram nova-3 (ar) | whole | 1/1 | 2/4 | 1/3 | 11/31 | 1/8 | 1/1 | 1/3 | 3/12 |
| Cohere transcribe-arabic-07-2026 (local, ar) | line | 1/1 | 0/4 | 1/3 | 10/31 | 0/8 | 1/1 | 0/3 | 2/12 |
| Deepgram nova-3 (ar) | line | 0/1 | 2/4 | 1/3 | 9/31 | 0/8 | 0/1 | 0/3 | 1/12 |
| ElevenLabs Scribe v2 (fresh runs) | whole | 0/1 | 2/4 | 3/3 | 5/31 | 0/8 | 0/1 | 2/3 | 0/12 |
| Audar ASR V1 Turbo (local, auto) | line | 0/1 | 1/4 | 1/3 | 6/31 | 3/8 | 0/1 | 0/3 | 1/12 |
| Audar ASR V1 Turbo (local, forced ar) | line | 0/1 | 0/4 | 1/3 | 5/31 | 4/8 | 0/1 | 1/3 | 1/12 |
| OpenAI gpt-transcribe | line | 0/1 | 1/4 | 1/3 | 4/31 | 1/8 | 0/1 | 0/3 | 3/12 |
| Cohere transcribe-03-2026 (API, ar) | line | 0/1 | 0/4 | 0/3 | 8/31 | 0/8 | 0/1 | 0/3 | 2/12 |
| Speechmatics ar_en enhanced | whole | 0/1 | 0/4 | 0/3 | 4/31 | 1/8 | 0/1 | 0/3 | 4/12 |
| Speechmatics ar_en enhanced | line | 0/1 | 1/4 | 1/3 | 1/31 | 2/8 | 0/1 | 0/3 | 3/12 |
| OpenAI gpt-4o-transcribe | line | 0/1 | 2/4 | 0/3 | 2/31 | 1/8 | 0/1 | 0/3 | 2/12 |
| ElevenLabs Scribe v2 (fresh runs) | line | 0/1 | 2/4 | 0/3 | 4/31 | 0/8 | 0/1 | 1/3 | 0/12 |
| ElevenLabs Scribe v2 (today's transcript) | line | 0/1 | 0/4 | 3/3 | 0/31 | 0/8 | 0/1 | 1/3 | 0/12 |
| Deepgram nova-3 (multi) | line | 0/1 | 0/4 | 0/3 | 2/31 | 0/8 | 0/1 | 0/3 | 1/12 |
| Deepgram nova-3 (multi) | whole | 0/1 | 0/4 | 0/3 | 2/31 | 0/8 | 0/1 | 0/3 | 1/12 |
| Gemini 3.8 Flash + context, temperature 1 | line | 0/1 | 3/4 | 3/3 | 26/31 | 6/8 | 1/1 | 3/3 | 11/12 |
| Gemini 3.8 Flash + context | line | 0/1 | 3/4 | 3/3 | 25/31 | 6/8 | 1/1 | 3/3 | 10/12 |
| Gemini 3.8 Flash, context before only | line | 0/1 | 3/4 | 1/3 | 26/31 | 6/8 | 1/1 | 3/3 | 9/12 |
| OpenAI gpt-audio-1.5 + context | line | 0/1 | 2/4 | 1/3 | 10/31 | 5/8 | 1/1 | 1/3 | 4/12 |
| OpenAI gpt-audio-1.5, context before only | line | 0/1 | 2/4 | 1/3 | 10/31 | 1/8 | 1/1 | 3/3 | 2/12 |

### Amal's 6 corrected lines (plain transcribers on her clips)

| Engine | Heard right (of 6) |
|---|---|
| Cohere transcribe-arabic-07-2026 (local, ar) | 1 |
| Deepgram nova-3 (ar) | 0 |
| Audar ASR V1 Turbo (local, auto) | 1 |
| Audar ASR V1 Turbo (local, forced ar) | 1 |
| OpenAI gpt-transcribe | 0 |
| Cohere transcribe-03-2026 (API, ar) | 0 |
| Speechmatics ar_en enhanced | 0 |
| OpenAI gpt-4o-transcribe | 1 |
| ElevenLabs Scribe v2 (fresh runs) | 0 |
| ElevenLabs Scribe v2 (today's transcript) | 0 |
| Deepgram nova-3 (multi) | 1 |
