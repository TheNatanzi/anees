# Overnight build — Grammar Console, full recall

**Written** 2026-09-23 · **Repo** `C:\dev\anees-hourly` · **Branch** `hourly`, pushes to `master`
**Live** https://thenatanzi.github.io/anees/grammar.html

Read `RULES.md` first. Then this. Then start at M0.

---

## The one thing that matters

Medi says Amal corrects him **20–30 times a lesson**. The detector currently finds
**190 across 10 lessons** — about 19 a lesson, and lopsided: 43 in one lesson, 0 in two.
He also says his mistake rate is nearer **1 in 3–4 sentences**; the page says 1 in 50.

**The job is recall.** Find the corrections that are being missed, file them in the right
bucket, and prove it with a measured number — not a feeling.

He has confirmed `B1 present with b-` at 90% **is** right. So the detector is not
uniformly wrong; it is missing whole *kinds* of correction.

---

## What already exists — do not rebuild

| File | What it does |
|---|---|
| `docs/grammar.html` | the console page |
| `docs/js/grammar-console.js` | charts, rule table, accordion, review queue, Amal's Doc panel |
| `docs/css/grammar.css` | layers on `word-bank.css`, same `#anees-bank` shell |
| `scripts/build_grammar_buckets.py` | the 55 buckets → `docs/data/grammar-buckets.json` |
| `scripts/detect_grammar_usage.py` | counts rule USES → `docs/data/grammar-usage.json` (2,149) |
| `scripts/audit_grammar_lessons.py` | finds Amal's corrections → `docs/data/grammar-audit.json` (190) |
| `scripts/build_grammar_console.py` | joins all of it → `docs/data/grammar-console.json` |
| `docs/data/tally.json` | 14 hand-verified slips, 3 lessons — the only human-checked truth today |

Lessons live in `C:\dev\anees\data\lessons\<date>\` — `transcript.txt` for six of them,
per-speaker `scribe_Medi.json` / `scribe_Amal.json` for the rest.

---

## Standing rules this build must not break

- **S1** — Amal's spelling is the only spelling. Never invent Arabizi. (`RULES.md`)
- **M1** — a slip needs Amal's recast or Medi's own ask.
- **M4** — Family F is pronunciation, never counted as a grammar mistake.
- **Never a guessed number.** A rule with no evidence stays `Untested`, blank, not zero.
- Machine finds and human-verified finds stay in **separate streams**. A guess never moves a score.

---

## M0 — Ground truth, before touching any code

Without this every later number is an opinion.

1. Pick **two** lessons: `2026-09-21` (291 Medi Arabic turns, detector found 43) and
   `2026-09-17` (91 turns, detector found **2** — the worst case).
2. Read every Medi Arabic turn and the 25 seconds after it. By hand, list every place
   Amal corrected him. Record: timestamp, what he said, what she said, which bucket.
3. Write it to `docs/data/grammar-goldset.json`. Mark `"source": "hand"`.
4. **Gate G0** — the gold set exists and has at least 40 corrections across the two lessons.
   If 09-17 genuinely has almost none, say so plainly and pick another lesson instead.

---

## M1 — Measure the detector against the gold set

1. Write `scripts/score_grammar_detector.py`: runs the auditor, compares to the gold set,
   prints **recall**, **precision**, and **bucket accuracy** (right correction, right bucket).
2. Print the missed ones grouped by *why* they were missed.
3. **Gate G1** — you can state today's recall as a number. Expect it to be low. Write it down.

---

## M2 — Fix recall, one miss-reason at a time

Work the miss list in order of size. Known gaps to check first:

- **She corrects without repeating him.** She says the right word cold. Today this only
  survives if a fuzzy minimal pair fires. Widen it: her short Arabic turn right after his
  error, where her word is a legal form of one of his.
- **She corrects in English.** "you need the ال there", "it's feminine". Match her English
  explanation to the bucket directly.
- **Several corrections in one turn.** The auditor `break`s after the first hit per Medi turn.
  Let one turn produce several.
- **Scribe lessons.** 09-16 and 09-17 find almost nothing. Check the per-speaker turn builder —
  a 1.6s gap may be gluing her correction onto her next sentence.
- **He self-corrects.** Medi fixes himself mid-turn. That is an `ask`, not a slip, and it feeds
  the self-correction chart, which currently reads 0 for most lessons.
- **The 118 UNFILED.** Real corrections with no rule named. Every one you can file is recall you
  already have and are throwing away.

After each change, re-run M1. **Gate G2** — recall ≥ 80% on the gold set with precision ≥ 70%.
Do not move on by loosening until precision collapses; if precision drops below 70, you have
traded one lie for another.

---

## M3 — Loop until it is stable

Repeat until two passes in a row change nothing:

1. Run the auditor over all 10 lessons.
2. Sample **20 random events**, read them against the transcript, mark each right or wrong.
3. Anything wrong → fix the rule that produced it → back to step 1.
4. Re-run M1 to confirm the gold-set numbers did not regress.

**Gate G3** — two consecutive passes with ≥ 18 of 20 correct, and gold-set recall still ≥ 80%.

---

## M4 — Usage counting, same treatment

`detect_grammar_usage.py` found 2,149 uses, but the patterns were written fast.

1. For each of the 55 buckets, sample 10 matched turns. Is that really the rule being used?
2. Fix the patterns that over-match. `A1` (any word starting ال) and `B5` (any word ending in a
   past-tense letter) are the most likely offenders.
3. The 12 buckets with **zero** uses — `A5 A6 A9b B4 B4b B7 B14 B15 B17 C2 C4b F2` — confirm each
   is genuinely absent from his speech rather than a pattern that never fires.
4. **Gate G4** — every bucket's use count is one you would defend if Medi asked "where?".

---

## M5 — Wire it up and ship

1. Re-run all four scripts in order: buckets → usage → audit → console.
2. Check the page: charts move with Week/Month/All, every row opens, underlines show,
   audio plays, Last used is populated, status colours are on the row.
3. Commit per milestone, not in one lump. Push `hourly:master`.
4. **Gate G5** — https://thenatanzi.github.io/anees/grammar.html is live and correct.

---

## What to write for Medi in the morning

One page, his format — one line first, then a visual, then short bullets, then his one action.
It must say:

- recall before and after, as numbers
- mistakes per sentence now, and whether it matches his 1-in-3-to-4 gut
- how many of the 118 UNFILED got filed, and what the rest are
- anything you changed that he should disagree with if he wants to
- **the buckets you are still not confident about, named**

Do not claim it is finished if the gold-set recall is under 80%. Say where it stopped and why.

---

## Things that will waste your night

- Tuning thresholds without the gold set. You will chase your tail.
- Trusting the ASR spelling. Normalise first — `norm()` in the auditor already does.
- Counting Family F as grammar. M4 forbids it.
- Filing a correction under a bucket because nothing else fit. `UNFILED` is the honest answer.
- Rebuilding the page. It works. The data behind it is the problem.
