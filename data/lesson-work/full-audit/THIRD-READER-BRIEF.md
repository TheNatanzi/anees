# Third reader brief - settle the disputes of one lesson

Two independent readers read the lesson. Rows they both found (same moment, same wrong piece, same kind) are agreed
and are NOT your job. Your job is `data/lesson-work/full-audit/<date>.disputes.md`: rows only one reader found, rows
they described differently, rows where they disagree on kind (vocab / grammar), A vs B, tier, bucket or mode.

Read first: `data/lesson-work/full-audit/READER-BRIEF.md` (the definitions: vocab-A / vocab-B / grammar / grammar-B,
tiers 0-3, what is NOT an error, S3/S4/S5). Then open the transcript `data/lesson-work/full-audit/<date>.txt` and,
for EVERY D-row, read the lines around its time (about 40 s before to 60 s after; chat lines lag 30-120 s) before ruling.
Use `data/lesson-work/full-audit/buckets.md` for bucket ids and `amal-sheet.txt` (grep) for tier-3 checks.
Do NOT open the other readers' JSON files, `data/grammar-sweep-*.json` or the sweep plan.

Rule with the transcript, not with the readers' prose. When both readers saw the same slip and only the label differs,
pick the label the transcript supports and write the full final row. When one reader found a row the other missed,
decide if it is real: keep it with a full row, or drop it and say why (not an error / S4 pronunciation / S5 pause /
self-fix before help / speaker is Amal / duplicate of D-n or of an agreed row / cannot be verified - transcript hole).
A row that is real but cannot be proven from the transcript (his line missing) is kept with confidence "low" and a why
that says so. Never invent what he said.

Output: ONE valid JSON (UTF-8, ensure_ascii=False) at the path in your task:
```
{"date": "...", "reader": "r3", "note": "anything about the lesson the merger should know",
 "rulings": [{"id": "D1", "verdict": "keep", "row": {<full row, same fields as READER-BRIEF>}, "why": "..."},
             {"id": "D2", "verdict": "drop", "why": "..."}],
 "added": [ <full rows for errors you noticed that NEITHER reader wrote - only if you are sure; usually empty> ]}
```
Every D-id in the disputes file must appear once in `rulings`. Reply with one line: kept n, dropped n, added n.
