# 06 — Sticking With It: ADHD, Habit Design, and Measuring Progress
*Date 2026-09-03. Learner: adult with severe ADHD, tutor 3-4×/week, ~5 min tutor input/lesson, prior Quizlet abandonment. [unverified] = from memory or paywalled.*

### 1. What ADHD does to language learning
Terms: *working memory* = holding a few items while using them; *time blindness* = poor sense of elapsed time; *hyperfocus* = long intense absorption in an interesting task; *delay discounting* = preferring small rewards now over larger later.
- Working memory below controls in adults with ADHD (Alderson 2013 meta, https://doi.org/10.1037/a0032371) [d≈0.5 unverified]; can still prioritise valuable items (2025, https://doi.org/10.1177/10870547251330039). → Fewer items per session, more reps, nothing that depends on remembering yesterday.
- Timing deficits + delay discounting (Noreika 2013, https://doi.org/10.1016/j.neuropsychologia.2012.09.036). → Tool owns the clock; rewards immediate.
- Hyperfocus real but not on command; more in hobbies/screens (Hupfeld 2019, PMID 30267329), less in educational settings (Groen 2020, PMID 33126147). → Make Arabic feel like a hobby with Amal, not a course.
- Immediate frequent reward works better (Alsop 2016; Furukawa 2019) [child data].
- **FL learning specifically:** Sparks 2004: all 68 ADHD college students completed the FL requirement, two-thirds without accommodations (ERIC EJ694458); Sparks 2005: ADHD groups earned average-or-better grades. Marashi 2016 (N=61): ADHD correlated **positively with speaking fluency**, negatively with accuracy (ERIC EJ1127411). → ADHD is not a barrier to learning Arabic; it is a barrier to *showing up* and to *accuracy*.
- Kormos & Smith 2023: multisensory input, explicit structure, short varied tasks, immediate feedback, reduced memory load [unverified summary]. Body doubling anecdotal; Amal's lesson *is* the body double.
- **Gap:** no peer-reviewed study of ADHD adults using SRS or language apps.

### 2. Habit and engagement design
- **Fogg B=MAP**: behaviour needs Motivation, Ability, Prompt together (https://behaviormodel.org/). Motivation is the volatile term for ADHD → design for tiny ability + external prompt.
- **Implementation intentions** ("if 9 am, then open the link"): Gollwitzer & Sheeran 2006, 94 tests, **d = 0.65** (https://doi.org/10.1016/S0065-2601(06)38002-1).
- **Habit timeline**: Lally 2010, N=96, automaticity after 18-254 days, mean 66; one missed day did not matter. → Plan a 3-month runway.
- **Streaks (Duolingo)**: 7-day streak → 3.6× course completion (correlational); animations +1.7% 7-day return; two freezes +0.38% DAU (https://blog.duolingo.com/how-duolingo-streak-builds-habit/). Caution: a 3,100-day streaker admitted the app stopped teaching him in 2018 (https://leejo.github.io/2022/07/03/duolingo_streak/). Streak = attendance, not learning.
- **Notifications**: bandit reminders +0.5% DAU, +2% new-user retention (Yancey & Settles 2020, https://doi.org/10.1145/3394486.3403351).
- **Gamification often fails**: Hamari 2014, context-dependent, novelty fades (https://doi.org/10.1109/HICSS.2014.377). Avoid variable rewards in a trust-based tutor tool.
- **Base rate**: of 4,000 SRS users who did a first session, fewer than 20 did a second (https://gwern.net/spaced-repetition). Abandonment is the default.

### 3. Session design for ADHD + language
- Microlearning: Hunter 2026 meta (15 studies) SMD 0.80 (https://doi.org/10.1093/ageing/afag129) [health professions].
- Fixed timed blocks beat self-regulated breaks: Biwer 2023 (N=87), lower fatigue, equal completion (PMID 36859717). → **One 7-minute block, timer visible.**
- Review-debt caps: Anki 20 new/day ≈ 200 reviews/day (https://docs.ankiweb.net/deck-options.html); FSRS retention 90%, above 97% overwhelming; FSRS needs 20-30% fewer reviews than SM-2 (https://github.com/open-spaced-repetition/awesome-fsrs/wiki/ABC-of-FSRS). → Cap reviews/day and silently drop the rest.
- Retrieval not re-reading: Karpicke & Roediger 2008 (PMID 18276894). → Every item demands production.
- Push not pull: one email/SMS at a fixed time, one-tap link straight into the session. No home screen, no deck picker.

### 4. Metrics: one headline number
| Metric | Pro | Con |
|---|---|---|
| **Words produced cold** | Directly = "can I say it"; retrieval-based | Needs a cold test, not warm review |
| FSRS true retention | Free from logs; mature cards ≥21 d (https://docs.ankiweb.net/stats.html) | Measures the scheduler, not speaking; noisy daily |
| Corrections per lesson | Amal already produces them | Confounded by lesson difficulty |
| Speech rate / pauses per min | Drives perceived fluency (Bosker 2013, https://doi.org/10.1177/0265532212455394) | Dialect ASR unreliable; needs same-task prompts |
| Streak | Motivating | Attendance, not learning |
| Lexical coverage % | Ties to comprehension | No Palestinian frequency list yet |
| CEFR estimate | Human-meaningful (A2 ≈ 150-260 guided h) | Moves every few months |

**Headline: "Words I can say cold."** A word counts if its *first* retrieval attempt on a due day, ≥7 days since last exposure, passes (spoken or typed, no hint). Sum over trailing 28 days, deduplicated. Goes up only when learning happens.
**Secondary (5):** true retention trailing 30 d · lesson+session streak with 1 freeze/week · corrections per 10 min · hesitations per minute on a fixed 60-s prompt (3 prompts rotated weekly, weekly median) · review load (due tomorrow vs cap).
**N=1 judgement (single-case design):** 2-week baseline, then intervention; judge by level, trend, variability, immediacy, overlap (https://en.wikipedia.org/wiki/Single-subject_design); WWC ≥3 demonstrations, ≥5 points/phase; Tau-U effect size (Balikci 2026, https://doi.org/10.3390/bs16040507). Practical: aggregate weekly, 4-week trend line, call "progress" only when 3 consecutive weekly points exceed baseline.

### 5. Keeping Amal engaged
- Preply Classroom tutor tools: Notes report (errors, vocab, homework, next objectives), vocabulary flashcard push, homework tracking, talk-time tracker (https://help.preply.com/en/articles/4182374). Tutors are time-poor; 5 min is generous.
- Dashboard research (Verbert 2013, https://doi.org/10.1177/0002764213479363; Schwendimann 2017, https://doi.org/10.1109/TLT.2016.2599522): teachers act on *outliers and next actions*, not charts [unverified summary].
- Design: one inbox per lesson (voice memo or 5-line form); show her "12 of your words were spoken cold this week"; never make her browse.

### 6. Failure post-mortems
- "Skip 2 or 3 days because of life and the huge backlog is too much that I give up" (HN, https://news.ycombinator.com/item?id=39163094).
- "Anki has a way of taking over"; card-making costs more than reviewing (https://news.ycombinator.com/item?id=35209775).
- Gwern: pay-off distant, cost vivid.
- SuperMemo rule 4, minimum information: one fact per card (https://www.supermemo.com/en/blog/twenty-rules-of-formulating-knowledge).
- Cap tied to lessons: Amal's 5 min yields ~5-10 words; each new card ≈ 10 reviews over its life → **max 8 new words/lesson, ~25/week**, auto-paused when due > cap.

### Design rules for stickiness (12)
1. Daily review cap 40; overflow silently rescheduled, never shown as "150 due".
2. New-word cap 8/lesson, 25/week, auto-paused when tomorrow's due > cap.
3. One session = 7 minutes, visible countdown; stop at 0 even mid-card.
4. Push not pull: email + SMS at 9:00 with one deep link into the session.
5. One button on landing: "Start". No menus.
6. Every item requires production; no multiple choice.
7. Streak counts lessons + sessions, 1 free freeze/week auto-applied.
8. Headline = words said cold, trailing 28 days; nothing else above the fold.
9. Charts weekly, 4-week trend vs 2-week baseline.
10. Amal's input = 5-line form or voice memo per lesson; never browse.
11. Show Amal one line of impact per week.
12. Retention target 88-90%; cull any card failed 4× (leech).
