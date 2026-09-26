# Process audit brief (step 7) - why was each miss missed, and what rule stops it next time

Goal named by Medi (2026-09-25): "a system that doesn't need her hand holding". Every ruling Amal gives must become
a reusable rule, never a one-off. Your output: `plan/PROCESS-AUDIT-2026-09-26.md`.

Read:
- `data/full-audit-2026-09-26.json` - every error row. Fields that matter: `source` (audit-2026-09-26 = the readers found
  it; sweep-2026-09-24 = only the hand sweep had it), `machine_had` (the automatic detector had flagged it before any
  human read), `signal` (recast / named-rule / prompt-then-fix / explicit-no / finished-sentence / chat-fix / asked /
  none), `kind` (grammar, grammar-B, vocab-A, vocab-B), `tier`, `bucket`, `confidence`, `why`, `t`, `t_amal`, `chat`.
- `per_lesson[*].coverage` and `r3_note` in the same file - transcript holes, Latin-transliterated stretches, swapped
  speaker labels, lessons where Amal typed every sentence in chat.
- `data/lesson-work/full-audit/*.compare.json` - what the two readers disagreed on (`disputes[*].why`) and the third
  reader's rulings in `*.r3.json` (`rulings[*].why`, especially every "drop": those are the traps).
- `plan/GRAMMAR-CORRECTION-SWEEP-2026-09-24.md` section "Things Medi should know" and the machine-audit numbers there.
- `scripts/audit_grammar_lessons.py`, `scripts/detect_grammar_usage.py`, `scripts/understand_lesson.py` (skim: how the
  machine detector works today - cue words, echo match, the 15-second rule) and `docs/data/ai_rules.json` (rules that exist).

Write, in plain words, one idea per line, tables where there are numbers:
1. **Detector gaps** - for each gap, how many misses it explains (count from the rows: machine_had false, grouped by
   what would have been needed to catch it). Expected gaps, verify or refute each with counts:
   English word inside an Arabic sentence (tier 3) · wrong form of a known word (tier 2) · a correction spread over 3+
   turns · chat lines lagging the voice by 30-120 s · untranscribed Medi stretches / "[speaking Arabic]" · Latin-
   transliterated stretches · listening drills mistaken for speaking · Amal's echo taken as a fix · pronunciation (S4)
   taken as a word miss · her "no" aimed at something else · the machine in the wrong bucket. Add any gap you find.
2. **A rule per gap** with a ONE-LINE test (how the code or the next reader knows it is applied), e.g. "a chat line
   within 120 s AFTER Medi's Arabic line that differs from it in one word is a candidate fix; test: 09-18 rows FA-…".
3. **What Amal must rule on once vs what the system settles from her Doc**: list the B patterns
   (`docs/data/amal-review.json` -> patterns) and say for each whether her Doc / chat already settles it (cite the
   sheet row or chat line) or whether only she can. Goal: the shortest list she has to touch.
4. **Reader-loop findings**: pass-1 vs pass-2 agreement per lesson (`per_lesson[*].passes`), what the readers disagree
   on most (label vs existence), and whether a third reader plus two passes is enough or where a fourth read is needed.
5. **Every proposed rule, one at a time, numbered, for Medi's yes / no** - short: rule, why, test, what changes if yes.
Note anything you could not verify (transcript holes) rather than guessing. Reply with one line: n gaps, n rules.
