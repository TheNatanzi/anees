**DO NOT APPROVE**

At `e27733e`, the three remaining blockers are **partly fixed, not all closed**.

1. **Disputed transcript: reverted, but scoring remains inconsistent.** FA-99795002 still scores `مع credit card`, although that wording exists only in the withheld line. Preserve its UID and original slip; apply an explicit **not-scored pending adjudication** ruling and rebuild dependent numbers. Alternatively, adjudicate the line and re-read against the accepted transcript. An advisory freshness warning is insufficient. [spot-withheld.json:213](C:/dev/anees-wt-bench/data/lesson-work/rehear/rejudge/spot-withheld.json:213)

2. **Scored removals: restoration fixes omission, but some “same slip” dispositions remain wrong.** FA-5ba734f4’s missing-preposition error is removed in favor of FA-aa03ebc5’s past-tense ending error—two different corrections. Restore the former unchanged pending review, and revalidate the other duplicate-removal dispositions. [removed-rows-by-cause.json:877](C:/dev/anees-wt-bench/data/lesson-work/rehear/rejudge/removed-rows-by-cause.json:877), [audit:30670](C:/dev/anees-wt-bench/data/full-audit-2026-09-26.json:30670)

3. **Carry matching: the strict test still has bypasses.** I reproduced `katab → katabt` matching `كاتب → كتبت`: strict word equivalence returns false, yet `same_slip`, UID carry, and removal all accept it. Shared consonants plus a matching fix remain sufficient; another fallback accepts 60% similarity. Require independently supported wrong-piece equivalence, then regenerate/revalidate carries and removals. [rehear_rejudge.py:334](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:334), [rehear_rejudge.py:341](C:/dev/anees-wt-bench/scripts/rehear_rejudge.py:341)

The council’s owner-listen gate remains required before publication, including its 0–3 / 4–7 / 8+ consequences. Held lines and the 28 explicitly unscored word marks may remain queued. [council conditions:52](C:/dev/anees-wt-bench/data/lesson-work/rehear/reviews/council-final-approval.md:52)

20 focused checks passed; they miss these counterexamples. No edits, network access, or database reads; database imports were explicitly blocked.

**DO NOT APPROVE — remaining: quarantine/adjudicate FA-99795002; correct false duplicate removals; close matcher bypasses and revalidate affected mappings; satisfy the council’s publish gate.**
