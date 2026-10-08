**DO NOT APPROVE**

At `cbcd19d`, blockers **1, 3, 4 and 7 are closed**. Blockers **2, 5 and 6 are partly fixed**. Passing the council’s 27-line listen alone is insufficient.

Exact remaining list:

1. **Adjudicate or revert the 11 applied spot-check failures before replacing scores.** The hidden 08:22 slip is resolved; held lines and existing owner corrections can remain queued. But these 11 disputed replacements already affect delivered text. Routing them for later review does not resolve that adverse evidence. [rehear_listen_page.py:222](C:/dev/anees-wt-bench/scripts/rehear_listen_page.py:222)

2. **Give removed scored slips substantive dispositions.** The cause report improves attribution, but “retired pass” and “readers did not write it again” still explain disappearance rather than establish correctness. Those categories include **121 formerly `grammar`/`vocab-A` rows**. Review their evidence, restore unresolved slips, or withhold affected replacement percentages. Gold-card assertions still accept omission as sufficient. [rehear_rejudge.py:982](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:982), [test_invariants.py:178](C:/dev/anees-wt-bench/tests/test_invariants.py:178)

3. **Tighten ruled-UID carry matching and revalidate affected carries/mappings.** I reproduced a confirmed old row quoting `katab` carrying its UID onto a new row quoting `كاتب`, with different fixes: `_two_alphabets` accepts their shared consonants, and `same_slip` treats that alone as sufficient. Require evidence of the same correction/attempt, with a regression test. This helper also determines “same slip elsewhere” removal dispositions. [rehear_rejudge.py:286](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:286), [rehear_rejudge.py:334](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:334), [rehear_rejudge.py:979](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:979)

The 28 explicitly unscored word marks can remain queued. Transcript alignment, `rehear_hold` scoring exclusion, merge fixes and labels look acceptable. **21 targeted checks passed**, but they miss the carry counterexample.

No edits. A builder import unexpectedly attempted a database read; it failed and used cached data. Subsequent checks blocked connections explicitly.

**DO NOT APPROVE — remaining: resolve the 11 applied disputes; substantiate scored-row removals; repair and revalidate UID carry matching.**
