**DO NOT APPROVE — round-3 item 1 is closed; items 2–3 remain partly open.**

- **Item 1 closed:** FA-99795002 retains its UID/text, is rejected under TR-22, and is excluded from scoring.
- **Item 2 partly closed:** FA-5ba734f4 is restored unchanged. However, six remaining duplicate removals—including five scored rows—fail independent wrong-piece equivalence.
- **Item 3 open:** the [60% similarity fallback remains](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:357). Synthetic `katab → katabt` versus `kasab → katabt` returns `same_words=False`, yet permits both a ruled UID carry and duplicate removal.
- **Tests:** 23/23 pass, but the [mapping assertions](C:/dev/anees-wt-bench/tests/test_final_approval_2026_10_05.py:382) reuse that permissive matcher. They do not independently enforce the promised rule.
- **Double counting:** acceptable temporarily with visible uncertainty labels and unverified scores. **New blocker:** “kept until a person checks it” is internal only; 71 restored grammar cards reach page data without that marker.

**Exact remaining work:**

1. Remove the similarity bypass; independently test wrong/right equivalence and regenerate carries, removals, and dependent numbers.
2. Restore or explicitly adjudicate these six unsupported removals: FA-888a7072, FA-27e2ba45, FA-9a8a82cc, FA-00b45200, FA-e007181a, FA-737a36aa.
3. Surface the pending-review/double-count uncertainty on affected cards and scores.
4. Before publishing, satisfy the **27-line owner-listen gate**, including its 0–3 / 4–7 / 8+ consequences; retain method-change/provisional labels and pass the publish guard.

Reviewed `engine-bench` at `4248942`. Counts confirmed. No edits or network access; database imports/reads explicitly blocked.

**DO NOT APPROVE — remaining conditions are the four items above.**
