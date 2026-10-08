DO NOT APPROVE

The backfill improves the transcript, but it is not ready to replace the site’s numbers everywhere.

**Blockers — fix before publishing**

1. **Make grammar scoring use the delivered transcript.** Repair overlay coverage on 09-10, 09-11, 09-15, 09-19 and 09-23; rebuild uses, slips and all dependent reports together. Otherwise withhold their replacement percentages. An approximate label does not explain a denominator calculated from different text. [audit.md:26](C:/dev/anees-wt-bench/data/lesson-work/rehear/audit.md:26), [lessons.json:717](C:/dev/anees-wt-bench/docs/data/lessons.json:717)

2. **Resolve the known adverse transcript evidence.** Reconcile the 11 missed answer-key corrections and restore the hidden 08:22 slip; adjudicate the 11 sampled changes where the blind listen preferred the old text. Rebuild affected scores afterward. The 49 other word changes are not automatically errors, but agreement alone does not validate them. [audit.md:16](C:/dev/anees-wt-bench/data/lesson-work/rehear/audit.md:16), [spot.json:47](C:/dev/anees-wt-bench/data/lesson-work/rehear/2026-09-11/spot.json:47)

3. **Repair word-credit reconciliation.** `still_on_line` accepts distinct words sharing consonants; an in-memory check accepted `katab` against `كاتب`. Separately, 28 ledger marks retain an earlier review despite the scored word disappearing. Require occurrence-specific equivalence or a fresh contextual decision; reconcile added words too before claiming Words % reflects the new transcript. [lesson_ledger.py:173](C:/dev/anees-wt-bench/scripts/lesson_ledger.py:173), [lesson_ledger.py:388](C:/dev/anees-wt-bench/scripts/lesson_ledger.py:388)

4. **Tighten duplicate matching and validate all 14 merges.** I reproduced `late_sweep_pairs` merging different grammar errors, in different buckets, solely because they quote the same three-word line. Require evidence of the same error/attempt, with a regression test preserving distinct errors. [full_audit_build.py:91](C:/dev/anees-wt-bench/scripts/full_audit_build.py:91)

5. **Justify removals independently of reader omission.** Review the 127 pass-two-only rows and give each removal a substantive disposition. Replace the 22 gold-card exemptions with assertions checking their documented replacement/rejection; “readers did not write it again” is insufficient. Report transcript effects, retired-pass effects, deduplication and reader variance separately. [runbook:113](C:/dev/anees-wt-bench/plan/REHEAR-REJUDGE-RUNBOOK-2026-10-04.md:113), [test_invariants.py:128](C:/dev/anees-wt-bench/tests/test_invariants.py:128), [test_invariants.py:168](C:/dev/anees-wt-bench/tests/test_invariants.py:168)

6. **Finish ruling and evidence reconciliation.** Restore confirmation provenance for `FA-9ebdf05d`, `FA-5ded86b4`, `FA-cca6494e`; resolve all six `to_decide` entries. Give every orphaned reference an explicit mapped/retired disposition, and revalidate checks attached to materially changed carried rows—checks currently follow UID alone. [report.md:49](C:/dev/anees-wt-bench/data/lesson-work/rehear/rejudge/report.md:49), [report.md:67](C:/dev/anees-wt-bench/data/lesson-work/rehear/rejudge/report.md:67), [report.md:119](C:/dev/anees-wt-bench/data/lesson-work/rehear/rejudge/report.md:119), [preflight.json:4](C:/dev/anees-wt-bench/data/lesson-work/rehear/rejudge/preflight.json:4), [accuracy_gates.py:486](C:/dev/anees-wt-bench/scripts/accuracy_gates.py:486)

7. **Scope the Arabizi exception correctly.** My reproducible 30-of-430 sample included explicitly unclear `as-said` forms. These enter the global converter, although S1’s exception is for Lessons error cards. Keep unclear forms Arabic elsewhere; audit the remaining additions for that distinction. [arabizi-extra.json:16091](C:/dev/anees-wt-bench/docs/data/arabizi-extra.json:16091), [word-bank-arabizi.js:41](C:/dev/anees-wt-bench/docs/js/word-bank-arabizi.js:41), [RULES.md:35](C:/dev/anees-wt-bench/RULES.md:35)

**Required conditions / labels**

- Replace the mixed-recording lessons’ “your microphone / reviewed changes” wording with explicit **mixed recording, limited changes, AI agreement**. Disclose unapplied Amal changes and unresolved lines. Also reconcile 09-18’s recorded word-change exception with the “alphabet only” claim. [rehear_status.py:26](C:/dev/anees-wt-bench/scripts/rehear_status.py:26), [apply-plan.json:23](C:/dev/anees-wt-bench/data/lesson-work/rehear/2026-09-18/apply-plan.json:23)
- Preserve “not verified”/≈ across reports; add the actual coverage and scoring-method limitations. Route unresolved checks to the Tutor portal under the owner’s latest instruction.

**Notes**

- The slip decrease is **partly defensible, not yet fully attributable or validated**. Especially on mixed recordings, it cannot be presented as the re-hear’s improvement alone.
- Raw files and existing overlays are preserved; 42 Amal-confirmed rows are kept. Orphan listings establish visibility, not completed reconciliation.
- `ruled_piece`, pronunciation-use exclusion, and the GR-24/PG-25 fixture replacements look defensible. The gold-card exemption weakens its check.
- Reviewed locally at `2ec2cee`; no edits or network. Guard success does not establish transcript or scoring accuracy.
