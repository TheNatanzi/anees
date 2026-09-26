# Pattern reader brief - group Amal's B rows into patterns (decision C)

Input: `data/full-audit-2026-09-26.json` -> `rows` where `kind` is `vocab-B` or `grammar-B` (the app thinks Medi
slipped and Amal let it pass). Medi's rule (2026-09-25): Amal rules ONCE per pattern, all examples folded under it.
Also read `docs/data/grammar-buckets.json` (bucket names) and grep `data/lesson-work/full-audit/amal-sheet.txt`
for her spellings (rule S1: her Arabizi only - if a word is not on her sheet, leave `*_arabizi` null).

Group the rows so that ONE ruling from Amal settles every row in the group:
- same wrong lemma -> same right lemma (e.g. every ماء for مي; every قالت used for "wrong"; every "customers" inside an
  Arabic sentence) = one pattern, even across lessons;
- same grammar rule applied the same way (e.g. "b- kept after lamma", "ما without b- on a plain present verb",
  "he-form for I") = one pattern per bucket + shape, NOT one pattern per bucket blindly - if a bucket has two clearly
  different shapes, make two patterns;
- a row that fits nothing stays alone (its own pattern).
A row goes in exactly one pattern. Use the row `uid` values (FA-0001 ...). Do not drop rows; do not invent rows.

Per pattern write:
```
{"id": "p-<short-slug>", "kind": "vocab|grammar", "bucket": "B3 or null", "tier": 1|2|3|null,
 "title": "one line Amal reads first, e.g. 'قالت used for wrong (8alat -> 8ala6)'",
 "wrong": "the wrong piece as he says it", "right": "what we think is right",
 "wrong_arabic": "Arabic script", "right_arabic": "Arabic script",
 "wrong_arabizi": "her spelling or null", "right_arabizi": "her spelling or null",
 "why": "ONE plain sentence for Amal: what he does and why we think it is wrong",
 "english": "an English gloss of a typical sentence", "rows": ["FA-0012", "FA-0208"]}
```
Order: biggest patterns first. Output ONE valid JSON (UTF-8) to `data/lesson-work/full-audit/patterns.json`:
`{"built": "<date>", "patterns": [...], "unplaced": []}` (unplaced must be empty - every B row is in a pattern).
Reply with one line: n patterns from n rows (n vocab, n grammar).
