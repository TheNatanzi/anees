- **FIXED — blocker:** `valid_first()` compacts answers per line; both callers use it. All three error positions now produce the same span proposal.
- **FIXED — retry limit:** permanent exceptions stop the pump on failure **21**, not 20 (`> 20`).
- **FIXED — manifest:** `load()` rejects model and configuration drift.
- **FIXED — classification:** `kind` uses `script_only()`; “I like it” → “I hate it” counts as words.
- **New blocker:** none found in this re-check.
- In-memory checks passed; no edits or network access.

VERDICT AMAL RUN: OK TO RUN
