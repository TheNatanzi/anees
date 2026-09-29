# Do all the numbers add up? A 7-lesson walk-through

**Bottom line:** they did not. The same slip was counted twice, two pages used two grammar formulas, and nothing checked the math before going live.
All of that is fixed on the branch `eng-audit-2026-09-29`. Nothing is live until you say yes.
Every score still shows, now with a **≈** mark: no lesson is verified yet, because no person has listened to check the transcript.

**Words used below, in plain words**

- **Transcript:** the text the speech-to-text engine wrote from the recording.
- **Reader:** an AI that reads a transcript and lists Medi's slips. Two Claude readers, then a third settles their disagreements.
- **Audit row:** one slip one reader found (a word or grammar mistake Amal corrected).
- **Verified:** both readers agree 95% of the time, and a person has listened. Today: 0 of 15 lessons.
- **≈ mark:** "this number is not verified yet". Hover or tap it to see why.
- **Pooled average:** add up all the right answers of all lessons, then divide by all the tries. Big lessons count more.
- **Codex:** OpenAI's AI (GPT-5.5). Used as a second judge that is not Claude.
- **Publish guard:** a checklist that runs every hour before anything goes live.

---

## Lesson 1 · The big picture

- A lesson travels left to right. Each box hands its output to the next.
- A red ✕ marks where the chain broke.

<div style="overflow-x:auto;-webkit-overflow-scrolling:touch"><svg viewBox="0 0 980 250" width="100%" role="img" aria-label="How a lesson becomes numbers, and where it broke" style="min-width:680px;max-width:980px;font-family:var(--sabz-font-sans)"><rect x="8" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="70.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Recording</text><text x="70.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">each person's own track</text><path d="M134 72 l12 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ar)"/><rect x="148" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="210.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Transcript</text><text x="210.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">speech-to-text</text><path d="M274 72 l12 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ar)"/><circle cx="210.0" cy="132" r="11" fill="var(--sabz-state-over)"/><text x="210.0" y="137" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">✕</text><text x="210.0" y="162" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">3 holes: 09-16,</text><text x="210.0" y="177" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">09-26, 09-28</text><rect x="288" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="350.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Readers</text><text x="350.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">2 Claude + a 3rd</text><path d="M414 72 l12 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ar)"/><circle cx="350.0" cy="132" r="11" fill="var(--sabz-state-over)"/><text x="350.0" y="137" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">✕</text><text x="350.0" y="162" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">reused old files; 0</text><text x="350.0" y="177" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">of 15 at 95%</text><rect x="428" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="490.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Audit rows</text><text x="490.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">one row per slip</text><path d="M554 72 l12 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ar)"/><circle cx="490.0" cy="132" r="11" fill="var(--sabz-state-over)"/><text x="490.0" y="137" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">✕</text><text x="490.0" y="162" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">same slip counted</text><text x="490.0" y="177" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">twice</text><rect x="568" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="630.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Builders</text><text x="630.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">turn rows into numbers</text><path d="M694 72 l12 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ar)"/><circle cx="630.0" cy="132" r="11" fill="var(--sabz-state-over)"/><text x="630.0" y="137" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">✕</text><text x="630.0" y="162" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">2 grammar formulas;</text><text x="630.0" y="177" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">failures ignored</text><rect x="708" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="770.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Pages</text><text x="770.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">what you see</text><path d="M834 72 l12 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ar)"/><circle cx="770.0" cy="132" r="11" fill="var(--sabz-state-over)"/><text x="770.0" y="137" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">✕</text><text x="770.0" y="162" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">no ≈ mark; pages</text><text x="770.0" y="177" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">disagreed</text><rect x="848" y="40" width="124" height="64" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="910.0" y="68" text-anchor="middle" font-size="15" font-weight="600" fill="var(--sabz-text)">Push</text><text x="910.0" y="89" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">goes live</text><circle cx="910.0" cy="132" r="11" fill="var(--sabz-state-over)"/><text x="910.0" y="137" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">✕</text><text x="910.0" y="162" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">no check before</text><text x="910.0" y="177" text-anchor="middle" font-size="11.5" fill="var(--sabz-text)">going live</text><text x="8" y="22" font-size="12" fill="var(--sabz-text-muted)">Red ✕ = where it broke (found tonight). All are fixed on the branch except the holes and the 95% agreement, which need people.</text><defs><marker id="ar" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="var(--sabz-text-muted)"/></marker></defs></svg></div>

---

## Lesson 2 · Scorecard: the 9 areas

| # | Area | Grade | In one line |
|---|---|---|---|
| 1 | Numbers match across pages | ⚠ → fixed | 14 of 25 shared numbers disagreed. After the fix, all 555 checks match. |
| 2 | Score formulas | ⚠ → fixed | There were 2 grammar formulas and 2 ways to average. Now there is one of each, and the cut-offs are written on the pages. |
| 3 | Audio and transcripts | ⚠ | No speakers are swapped. 3 stretches of speech were never transcribed. Nobody has listened to check the speech-to-text. |
| 4 | Hourly job | ⚠ → fixed | Failures were ignored and old reader files were reused. Every failure now stops the publish. |
| 5 | Rules vs code | ⚠ | 35 rules checked. 27 are enforced and 21 are fully obeyed. 9 need your answer. |
| 6 | AI steps | ⚠ | 1 of 12 AI steps is measured against people. Claude is now pinned to one model version. |
| 7 | Flashcards | ⚠ | The scheduler math is right. Test runs wrote 108 fake answers into your history. |
| 8 | Amal's answers | ⚠ → mostly fixed | 688 of her 729 verb answers were never pulled. All 729 are in now. |
| 9 | Page health | ✅ | 19 pages were hard to read in dark or light mode. All fixed. 0 broken links. |

✅ good · ⚠ problem found · "→ fixed" = fixed on the branch.

---

## Lesson 3 · The problems, one at a time

### 3.1 The same slip was counted twice

- **What:** a slip found in reading pass 1 came back in pass 2 as a "new" row. Example: 09-15 at 1:02:41, grammar rule A1, rows FA-950701c8 and FA-950701c8x.
- **Why it matters:** each extra copy is one more mistake in your grammar score.
- **Fixed:** the builder now merges repeats instead of renaming them. 14 repeats removed. Grammar slips counted: **560 → 551**.
- **Still needed:** 2 near-repeats need a person to decide (08-25 مغني; 09-21 دلوا / دل).

### 3.2 Two pages, two grammar formulas

- **What:** the Lessons page counted only the uses the machine spotted. The Grammar console also counted every slip Amal fixed as a use.
- **Why it matters:** the same lesson had two grammar scores. Total uses were 1,712 on one page and 2,178 on the other.
- **Fixed:** one shared formula (`scripts/grammar_math.py`) feeds both pages. Grammar % = right uses ÷ all uses. A fixed slip counts as a use.

<svg viewBox="0 0 760 450" width="100%" role="img" aria-label="Grammar percent per lesson, before and after one formula" style="max-width:760px;font-family:var(--sabz-font-sans)"><rect x="70" y="8" width="12" height="10" fill="var(--sabz-text-muted)"/><text x="86" y="17" font-size="12" fill="var(--sabz-text)">before (live site)</text><rect x="220" y="8" width="12" height="10" fill="var(--sabz-state-calm)"/><text x="236" y="17" font-size="12" fill="var(--sabz-text)">after (one formula, duplicates out)</text><text x="62" y="44" text-anchor="end" font-size="12" fill="var(--sabz-text)">08-25</text><rect x="70" y="30" width="545.6" height="9" fill="var(--sabz-text-muted)"/><text x="619.6" y="38" font-size="10" fill="var(--sabz-text-muted)">86.6</text><rect x="70" y="40" width="567.6" height="9" fill="var(--sabz-state-calm)"/><text x="641.6" y="48" font-size="10" fill="var(--sabz-text)">≈90.1</text><text x="62" y="70" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-04</text><rect x="70" y="56" width="207.3" height="9" fill="var(--sabz-text-muted)"/><text x="281.3" y="64" font-size="10" fill="var(--sabz-text-muted)">32.9</text><rect x="70" y="66" width="420.2" height="9" fill="var(--sabz-state-calm)"/><text x="494.2" y="74" font-size="10" fill="var(--sabz-text)">≈66.7</text><text x="62" y="96" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-05</text><rect x="70" y="82" width="335.2" height="9" fill="var(--sabz-text-muted)"/><text x="409.2" y="90" font-size="10" fill="var(--sabz-text-muted)">53.2</text><rect x="70" y="92" width="451.1" height="9" fill="var(--sabz-state-calm)"/><text x="525.1" y="100" font-size="10" fill="var(--sabz-text)">≈71.6</text><text x="62" y="122" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-10</text><rect x="70" y="108" width="532.4" height="9" fill="var(--sabz-text-muted)"/><text x="606.4" y="116" font-size="10" fill="var(--sabz-text-muted)">84.5</text><rect x="70" y="118" width="560.1" height="9" fill="var(--sabz-state-calm)"/><text x="634.1" y="126" font-size="10" fill="var(--sabz-text)">≈88.9</text><text x="62" y="148" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-11</text><rect x="70" y="134" width="411.4" height="9" fill="var(--sabz-text-muted)"/><text x="485.4" y="142" font-size="10" fill="var(--sabz-text-muted)">65.3</text><rect x="70" y="144" width="482.6" height="9" fill="var(--sabz-state-calm)"/><text x="556.6" y="152" font-size="10" fill="var(--sabz-text)">≈76.6</text><text x="62" y="174" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-14</text><rect x="70" y="160" width="350.9" height="9" fill="var(--sabz-text-muted)"/><text x="424.9" y="168" font-size="10" fill="var(--sabz-text-muted)">55.7</text><rect x="70" y="170" width="442.9" height="9" fill="var(--sabz-state-calm)"/><text x="516.9" y="178" font-size="10" fill="var(--sabz-text)">≈70.3</text><text x="62" y="200" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-15</text><rect x="70" y="186" width="287.9" height="9" fill="var(--sabz-text-muted)"/><text x="361.9" y="194" font-size="10" fill="var(--sabz-text-muted)">45.7</text><rect x="70" y="196" width="430.9" height="9" fill="var(--sabz-state-calm)"/><text x="504.9" y="204" font-size="10" fill="var(--sabz-text)">≈68.4</text><text x="62" y="226" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-16</text><rect x="70" y="212" width="294.8" height="9" fill="var(--sabz-text-muted)"/><text x="368.8" y="220" font-size="10" fill="var(--sabz-text-muted)">46.8</text><rect x="70" y="222" width="315.0" height="9" fill="var(--sabz-state-calm)"/><text x="389.0" y="230" font-size="10" fill="var(--sabz-text)">≈50</text><text x="62" y="252" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-17</text><rect x="70" y="238" width="243.2" height="9" fill="var(--sabz-text-muted)"/><text x="317.2" y="246" font-size="10" fill="var(--sabz-text-muted)">38.6</text><rect x="70" y="248" width="409.5" height="9" fill="var(--sabz-state-calm)"/><text x="483.5" y="256" font-size="10" fill="var(--sabz-text)">≈65</text><text x="62" y="278" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-18</text><rect x="70" y="264" width="204.1" height="9" fill="var(--sabz-text-muted)"/><text x="278.1" y="272" font-size="10" fill="var(--sabz-text-muted)">32.4</text><rect x="70" y="274" width="223.7" height="9" fill="var(--sabz-state-calm)"/><text x="297.6" y="282" font-size="10" fill="var(--sabz-text)">≈35.5</text><text x="62" y="304" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-19</text><rect x="70" y="290" width="493.3" height="9" fill="var(--sabz-text-muted)"/><text x="567.3" y="298" font-size="10" fill="var(--sabz-text-muted)">78.3</text><rect x="70" y="300" width="536.8" height="9" fill="var(--sabz-state-calm)"/><text x="610.8" y="308" font-size="10" fill="var(--sabz-text)">≈85.2</text><text x="62" y="330" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-21</text><rect x="70" y="316" width="425.9" height="9" fill="var(--sabz-text-muted)"/><text x="499.9" y="324" font-size="10" fill="var(--sabz-text-muted)">67.6</text><rect x="70" y="326" width="490.1" height="9" fill="var(--sabz-state-calm)"/><text x="564.1" y="334" font-size="10" fill="var(--sabz-text)">≈77.8</text><text x="62" y="356" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-23</text><rect x="70" y="342" width="437.9" height="9" fill="var(--sabz-text-muted)"/><text x="511.9" y="350" font-size="10" fill="var(--sabz-text-muted)">69.5</text><rect x="70" y="352" width="491.4" height="9" fill="var(--sabz-state-calm)"/><text x="565.4" y="360" font-size="10" fill="var(--sabz-text)">≈78</text><text x="62" y="382" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-26</text><rect x="70" y="368" width="561.3" height="9" fill="var(--sabz-text-muted)"/><text x="635.3" y="376" font-size="10" fill="var(--sabz-text-muted)">89.1</text><rect x="70" y="378" width="566.4" height="9" fill="var(--sabz-state-calm)"/><text x="640.4" y="386" font-size="10" fill="var(--sabz-text)">≈89.9</text><text x="62" y="408" text-anchor="end" font-size="12" fill="var(--sabz-text)">09-28</text><text x="74" y="402" font-size="10" fill="var(--sabz-state-over)">missing on the live site</text><rect x="70" y="404" width="553.8" height="9" fill="var(--sabz-state-calm)"/><text x="627.8" y="412" font-size="10" fill="var(--sabz-text)">≈87.9</text></svg>

- 09-28 had **no grammar score on the live site**: the hourly job never ran the use counter. It does now.
- These are not real skill changes. It is the same speech with one formula.

### 3.3 The Word Bank ignored slips the Lessons page counted

- **What:** 219 word slips from the lesson audit were on the Lessons page but missing from the Word Bank and Progress.
- **Why it matters:** the Word Bank looked better than your lessons: 83.7% against about 80%.
- **Fixed:** the Word Bank, Progress and Flashcards now read the same slip file. A slip only joins a word when a reader named the word.
- **Changed:** Word Bank accuracy **83.7% → ≈71.0%**. Words known **274 → 258**. Mastered **110 → 96**. (Your yes/no is in Lesson 6.)

### 3.4 Unverified numbers looked exact

- **What:** no page said a score was unchecked.
- **Fixed:** every lesson-based score now shows **≈** with the reasons on hover or tap: Lessons, Overview, Progress › Vocab, Word Bank, Grammar console.
- **Why none is verified:**
  - the two readers agree only 48–81% of the time, and the bar is 95%;
  - nobody has listened to check the speech-to-text.
- **Still needed:** ≈ on the Fluency ladder, Progress › Grammar, Tutor and Flashcards.

### 3.5 Holes in the transcript

- **What:** the raw audio was compared with the transcript, second by second, for each person.
- **Found:**
  - **09-28:** your first 0:42–6:42 was never transcribed (174 s of your speech).
  - **09-16:** you, 26:49–28:13 (24 s).
  - **09-26:** Amal, 0:04–1:06.
  - The old 09-23 hole (0:00–22:37) is filled.
- **Fixed:** any slip inside a hole is now "unscoreable". It is not counted as right or wrong.
- **Speakers:** none swapped. 09-18 (guessed by voice pitch) agrees with Meet's own captions as well as the good lessons do.

### 3.6 Uncertain rows: a second, different AI listened

- **What:** 213 scored rows were ones the Claude readers were unsure of.
- **Done:** for each row, a clip was cut from the raw audio and written out by 2 local speech models. Then Codex (not Claude) ruled on it.
  - 173 agree with the Claude readers.
  - **40 disagree.** They are on the **Tutor page** for Amal: "Correction is correct" or "Reason not to correct" plus a box.
  - Cost: $0.
- **Her "yes" makes a row count.** Until then, those 40 rows count nowhere.

### 3.7 The hourly job hid its failures

- **What:**
  - "Never blocks" steps swallowed errors.
  - Old reader files were reused just because they existed. 09-23 grew by 266 lines and 09-26 by 149 after the readers ran, so those lines were never read.
  - 515 Grammar clips were linked but never saved.
- **Fixed:**
  - Any failed step stops the publish and is retried next hour.
  - A reader file is re-read when its transcript, briefs or rules change.
  - Clips are committed.
  - The log is now plain text with an exit code.

### 3.8 Amal's answers were lost

| Her input | Given | In the app before | Now |
|---|---|---|---|
| Verb check list 1 (09-25) | 729 | 41 | **729** |
| Verb check list 2 | 0 | 0 | 0 (the pull would have lost them; fixed) |
| Grammar-rule notes (09-27) | 20 rulings | 0 | **20** |
| Quizlet sets she sent | 132 | 106 | **126** (7 are too big for the public page) |
| Word review 09-05 | 11 | 4 | 4 (7 not shown yet) |

- Her approved verb form now wins even if the machine's guess changes later.

### 3.9 Tests wrote fake answers into your flashcards

- **What:** two end-to-end tests talk to the **live** database. Tonight's test runs, including this audit's own, left **108 fake answers** in your history. That made 2 fake leeches and used up today's new cards.
- **Fixed:** those tests now run only when someone turns them on on purpose (`ANEES_E2E_LIVE=1`).
- **Still needed:** your yes to delete the 108 rows (all Animals, today 09:14–09:57 UTC).

### 3.10 Rules the data breaks

- Glue words (bas, u, shu, lama…) are scored: 158 uses, which lifts Words %.
- 22 half-credit scores come only from the machine's "Amal said it within 15 s" flag. No context read.
- 7 pairs are scored twice, although their own note says "same episode".
- There are two different "Mastered" definitions (Word Bank vs Flashcards).
- **New:** `scripts/check_rules.py` runs 20 rule checks every hour.

### 3.11 AI steps: measured or not

| Step | Model pinned | Calls logged | Measured against people |
|---|---|---|---|
| Transcribe (ElevenLabs Scribe v2) | name only | yes | 15/20 blind vote; error rate never measured |
| Readers (Claude) | **now yes** | yes | no; they agree with each other 48–81% |
| Grammar detector (code) | yes | yes | yes: catches 40% on held-out rows |
| Second judge (Codex GPT-5.5) | yes | yes | no |
| Sheet match (by meaning) | by hand | no | 42 of 98 right by the old string match |

---

## Lesson 4 · Before and after: every number that changed

**Why they changed:** one grammar formula, repeats removed, Word Bank reads the audit slips, 09-28 read by hand. Before = the live site now.

| Lesson | Words % before → after | Grammar % before → after | Grammar uses before → after |
|---|---|---|---|
| 08-25 | 76.6 (same) | **86.6 → ≈90.1** | **217 → 233** |
| 09-04 | 69.6 (same) | **32.9 → ≈66.7** | **70 → 105** |
| 09-05 | 80.4 (same) | **53.2 → ≈71.6** | **79 → 109** |
| 09-10 | 85.7 (same) | **84.5 → ≈88.9** | **232 → 244** |
| 09-11 | 84.5 (same) | **65.3 → ≈76.6** | **98 → 124** |
| 09-14 | 85.3 (same) | **55.7 → ≈70.3** | **106 → 148** |
| 09-15 | 79.8 (same) | **45.7 → ≈68.4** | **92 → 133** |
| 09-16 | 78.7 (same) | **46.8 → ≈50** | **52 → 104** |
| 09-17 | 82.5 (same) | **38.6 → ≈65** | **70 → 103** |
| 09-18 | 29.2 (same) | **32.4 → ≈35.5** | **23 → 62** |
| 09-19 | 62.9 (same) | **78.3 → ≈85.2** | **23 → 27** |
| 09-21 | 83.1 (same) | **67.6 → ≈77.8** | **216 → 266** |
| 09-23 | 71.2 (same) | **69.5 → ≈78** | **105 → 132** |
| 09-26 | **83.3 → ≈86** | **89.1 → ≈89.9** | **192 → 207** |
| 09-28 | **80.2 → ≈83.7** | **— → ≈87.9** | **— → 173** |

| Headline | Before (live) | After |
|---|---|---|
| Words average (all lessons) | 76% (plain mean) / 80.0% (Overview) | **≈80.8%** (pooled, one number) |
| Grammar average | 63% / 72.0% | **≈77.3%** |
| Grammar slips counted | 560 | **551** |
| Word Bank accuracy | 83.7% | **≈71.0%** |
| Words known | 274 | **258** |
| Mastered / Good | 110 / 164 | **96 / 162** |
| Verb forms checked by Amal | 41 | **729** |
| Quizlet sets / terms | 107 / 2,406 | **126 / 2,841** |
| Rows waiting for a check | 213 | **40** (for Amal) |
| Open word events (tonight, before the hand read) | 153 | **32** |
| Lessons verified | 0 of 15 | 0 of 15 (honest now) |

- **Words % moved on only 2 lessons:** 09-26 83.3 → 86.0 and 09-28 80.2 → 83.7. Both come from tonight's hand read of those lessons.

---

## Lesson 5 · The permanent guard

- Every hour, before anything goes live, 11 checks run in about 20 seconds.
- **If any check fails,** nothing is pushed and yesterday's good version stays live. The reason goes into the hourly log and onto System Settings.

<div style="overflow-x:auto;-webkit-overflow-scrolling:touch"><svg viewBox="0 0 900 330" width="100%" role="img" aria-label="The publish guard" style="min-width:680px;max-width:900px;font-family:var(--sabz-font-sans)"><defs><marker id="ag" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="var(--sabz-text-muted)"/></marker></defs><rect x="10" y="130" width="130" height="60" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="75.0" y="156.0" text-anchor="middle" font-size="14" font-weight="600" fill="var(--sabz-text)">Every hour</text><text x="75.0" y="173.0" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">new lesson? build</text><path d="M142 160 l30 0" stroke="var(--sabz-text-muted)" stroke-width="2" marker-end="url(#ag)"/><rect x="178" y="10" width="330" height="310" rx="12" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="343" y="34" text-anchor="middle" font-size="15" font-weight="700" fill="var(--sabz-text)">Publish guard: 11 checks</text><text x="196" y="60" font-size="12.5" fill="var(--sabz-text)">✓ build steps all passed</text><text x="196" y="84" font-size="12.5" fill="var(--sabz-text)">✓ nothing half-saved</text><text x="196" y="108" font-size="12.5" fill="var(--sabz-text)">✓ every data file opens</text><text x="196" y="132" font-size="12.5" fill="var(--sabz-text)">✓ new lesson on every page</text><text x="196" y="156" font-size="12.5" fill="var(--sabz-text)">✓ same-day review done</text><text x="196" y="180" font-size="12.5" fill="var(--sabz-text)">✓ accuracy gates (95% rule)</text><text x="196" y="204" font-size="12.5" fill="var(--sabz-text)">✓ numbers match (555 checks)</text><text x="196" y="228" font-size="12.5" fill="var(--sabz-text)">✓ standing rules hold</text><text x="196" y="252" font-size="12.5" fill="var(--sabz-text)">✓ pages: links + clips</text><text x="196" y="276" font-size="12.5" fill="var(--sabz-text)">✓ Arabizi on every card</text><text x="196" y="300" font-size="12.5" fill="var(--sabz-text)">✓ offline tests</text><path d="M510 110 l40 -40" stroke="var(--sabz-state-calm)" stroke-width="2" marker-end="url(#ag)"/><path d="M510 210 l40 40" stroke="var(--sabz-state-over)" stroke-width="2" marker-end="url(#ag)"/><rect x="556" y="30" width="330" height="70" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="721.0" y="61.0" text-anchor="middle" font-size="14" font-weight="600" fill="var(--sabz-text)">All pass → push</text><text x="721.0" y="78.0" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">site updates; Settings shows 'last check OK'</text><rect x="556" y="220" width="330" height="90" rx="10" fill="var(--sabz-surface)" stroke="var(--sabz-hairline)"/><text x="721.0" y="261.0" text-anchor="middle" font-size="14" font-weight="600" fill="var(--sabz-text)">Any fail → no push</text><text x="721.0" y="278.0" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">last good version stays live</text><text x="721" y="296" text-anchor="middle" font-size="11" fill="var(--sabz-text-muted)">reason → hourly log + System Settings</text></svg></div>

- **Every way to go live now goes through the guard.** There were 8 separate push points; a test fails if anyone adds a new one.
- **Today it would block on one thing:** a verb test where Amal wrote "they take you" two ways (Decision M1 below).

---

## Lesson 6 · Decisions

### For Medi: answer these before merging

- **M1** Use Amal's newer check-list spelling (byaa5dook) over her older Quizlet card, so the guard stops blocking? yes / no
- **M2** Delete the 108 fake flashcard answers the tests left today? yes / no
- **M3** Grammar % counts every fixed slip as a use, and leaves out 58 slips in 4 rules the machine can't count (they stay listed)? yes / no
- **M4** The Word Bank counts the lesson audit's word slips (accuracy 83.7% → ≈71.0%)? yes / no

### For Medi: can wait

- **M5** Only a person listening makes a lesson "verified" (so 0 of 15 today)? yes / no
- **M6** Keep both 95% checks: within each reading pass, and between the two passes? yes / no
- **M7** Re-read 09-23 and 09-26 with the readers (their transcripts grew after reading)? yes / no
- **M8** Transcribe your first 09-28 recording (about $0.03)? yes / no
- **M9** Should preposition slips (مع, عند, قبل…) count as word slips? (09-21 says prepositions are grammar) yes / no
- **M10** Keep counting fixes Amal only typed in chat (39)? yes / no
- **M11** Score glue words (bas, u, shu…) in the Word Bank? yes / no
- **M12** "Mastered" = 90% of your last 10 tries over 2 lessons, everywhere (not "5 wins on 3 days")? yes / no
- **M13** A confirmed wrong pronunciation scores 0 (09-21), even though RULES S4 says pronunciation never lowers a score? yes / no
- **M14** Repeating Amal's word right after her counts as nothing (not half credit)? yes / no
- **M15** Keep the flashcard settings changed on 09-27: 8 new a day, leech at 4 misses, 1/4-minute steps? yes / no
- **M16** Hold all publishing when a new lesson's review fails? (currently yes) yes / no
- **M17** When blocked, also push a status line so the live Settings page shows it? yes / no
- **M18** Check your manual pushes too (a pre-push hook)? yes / no
- **M19** Point the hourly "vocab import" task at the up-to-date copy (C:\dev\anees is 204 commits behind)? yes / no
- **M20** Run end-to-end tests only on a test copy of the database? yes / no
- **M21** Publish the 676 short audio clips on this PC (40 MB) so they play as real clips? yes / no
- **M22** Should ≈ mark percentages only, and not counts? yes / no
- **M23** Update the RULES letter chart: Amal writes s for ص (109 of 120), not 9? yes / no
- **M24** The Tutor check list asks Amal about grammar. Retire the old "never send her grammar questions" clause? yes / no

### For Amal (on the Tutor page; you send her the link)

- **A1** 40 moments: is each correction right? (Correction is correct / Reason not to correct)
- **A2** "They take you": bya5dook or byaa5dook?
- **A3** Your 97 verb fixes changed the Latin letters. Is the Arabic under them right too (e.g. بيسخدم)?
- **A4** Is حركة (movement) a form of حرّك on the list, or a new word?

---

## Lesson 7 · Not done yet (honest list)

- **0 of 15 lessons verified.** Reader agreement is below 95%, and no person has listened.
- **40 rows** wait for Amal. 2 of her cards can't play, because 09-10 has no single lesson recording on the site.
- **09-23 and 09-26** were not re-read (M7). **09-28's lesson type** is not read yet, and the "taught verbs" list stops at 09-18.
- **09-28:** your first 6 minutes are still untranscribed (M8).
- **The by-meaning list check is not automatic yet.** 09-28 was done by hand tonight.
- **No human answer keys** exist for speech-to-text, speaker labels or the readers.
- **≈** is missing on the Fluency ladder, Progress › Grammar, Tutor and Flashcards.
- 7 word-review answers from Amal are not shown yet. 7 big Quizlet sets are not imported.
- 108 fake flashcard rows are still in the database (M2).
- The rule breaks in 3.10 wait for your answers (M9–M14).
- The guard has not run on the live machine yet. It starts after the merge.

**When you approve** (run once, in `C:\dev\anees-hourly`):

```
git -C C:\dev\anees-hourly fetch origin
git -C C:\dev\anees-hourly merge --no-ff origin/eng-audit-2026-09-29
python C:\dev\anees-hourly\scripts\publish_guard.py check
git -C C:\dev\anees-hourly push origin HEAD:master
```

Only push if the guard prints `OK - publishable`.
