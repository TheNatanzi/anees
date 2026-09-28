# Decisions log: `data/decisions/YYYY-MM.jsonl`

One JSON line per human verdict (Medi or Amal), plus machine-audit verdicts marked `who: "Claude audit"`, `channel: "audit"` (e.g. `scripts/audit_vocab_unresolved.py`) so a dashboard can show them apart from Medi's and Amal's. Written by `scripts/decisions.py`. Filled hourly by `scripts/pull_decisions.py`, which the hourly job runs after the publish. Design: [AI engineering review, Tracking design §2](../../plan/AI-ENGINEERING-REVIEW-2026-09-27.md#tracking-design-three-append-only-logs-feed-one-dashboard-file).

**Rules**
- Append-only. A changed verdict is a new line, and its `supersedes` names the old line. `decisions.latest()` gives the current view.
- Public repo: ids, enums and short Latin values only. Arabic or text over 200 characters is stored as `sha256:<16 hex>`.
- The month file comes from `ts`, the moment of the verdict (UTC).
- Two machines can append the same pulled row before they sync. The `merge=union` driver keeps both copies, so readers de-duplicate by `decision_id`.

**Fields**: `decision_id, ts, who (Medi|Amal|Claude audit), channel, about_type, about_id, ai_run_id, ai_value, answer, corrected_value, confidence, reason, latency_ms, sampling (random|uncertain|repeat), supersedes, applied_commit, source_row`

- `channel`: swipe, tutor_page, chat, commit, plus `review_page` and `app` (Medi's own pages), and `audit` (machine audit verdicts, who = Claude audit).
- `about_type`: rule, audit_row, pattern, word, arabizi, label, plus `homework` (Amal's after-lesson homework taps), `plan` (her lesson-plan choices) and `change` (a yes/no on a whole commit).

**Sources** (read-only, public anon key from `docs/js/config.js`; `decision_id` = source row, so a re-pull is idempotent)

| source | who / channel | about_type |
|---|---|---|
| `amal_rules_public` (review / after / planner / medi) | Amal, tutor_page (Medi, app for `medi`) | pattern, word, audit_row, homework, plan |
| `sentence_labels` | Medi, swipe | label (`ai_value` = machine label) |
| `draft_word_reviews` | Medi, review_page | word |
| git subjects ending `Medi\|Amal YYYY-MM-DD: yes\|no` | commit | change |

- **Skipped:** `amal_rules` source `flashcards`. The cards page files these automatically after two misses, so they are not verdicts.
- **Not reachable with the anon key:** `payload.reason` / `payload.rows`, and the token-gated answer tables (`verb_check_links`, `transcript_review_links`, `amal_links.answers`).
