- **(a) FIXED:** `touched` excludes text-, speaker-, and time-corrected turns; time matching uses each turn’s original `span0`. Round-4 counterexample is now a passing regression test.
- **(b) FIXED:** `check()` covers published lessons plus every Gemini-row date; an in-memory test confirmed unpublished dates are checked.
- **New blockers:** None found within the requested scope.
- Read-only, offline checks passed; no edits or network access.

**VERDICT APPLY: OK TO RUN**
