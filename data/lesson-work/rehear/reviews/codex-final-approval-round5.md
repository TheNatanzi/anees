**DO NOT APPROVE — items 1–3 are closed; the repeat-review blocker remains.**

- **1 closed:** strict matching replaces the similarity bypass; independent mapping checks and the `katab`/`kasab` regression pass.
- **2 closed:** all six removals have supported dispositions: three restored, two changed-line removals, one previously rejected.
- **3 closed:** 125 restored cards carry uncertainty labels; affected scores are provisional; double-count labels cover 47 possible slips.
- Confirmed: **390 carries, 18 un-carried ruled UIDs, 1,119 rows, 960 scored**.
- **Side effect is a blocker:** previously ruled moments reach Amal again under new UIDs. Small correction: I found **13 visible B rows across 12 ruled moments**, not 13 ruled UIDs.
- **Proposed fix is acceptable:** hold new B rows within **±5 seconds on the same lesson** from Amal’s review list; show them to the owner with the earlier UID, ruling, and both rows. Proximity must only route review—it must not transfer a ruling, merge rows, or change scoring.
- **Remaining implementation:** apply that hold, regenerate review data, and test that every affected row is absent from Amal’s questions and present on the owner list, including multiple matches.
- **Before publish:** satisfy the **27-line owner-listen gate** and its **0–3 / 4–7 / 8+ consequences**, retain method-change/provisional labels, and pass the publish guard.
- **Validation:** 28/28 targeted checks passed with writes, network, and database access blocked. No additional blocker found in this review.

**DO NOT APPROVE — remaining: implement and verify the review hold; satisfy the owner-listen gate and publish checks.**
