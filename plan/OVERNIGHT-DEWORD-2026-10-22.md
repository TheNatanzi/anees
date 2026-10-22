# Overnight: fewer words, more pictures (2026-10-22 → 7 AM 2026-10-23)

You are Claude Code, running alone overnight on the Anees app (C:\dev\anees). Medi has severe ADD.
Your job: make every page say only what matters and show it as a picture where a picture says it better,
like the "How Anees works" flowchart (docs/reports/anees-flow.html). Build it in TWO looks. Nothing goes live.

## 0. Hard rules (break one = stop and write it in the morning report)
- **Preview only.** Work in a new git worktree on branch `claude/deword-overnight` cut from origin/master.
  Never push to master, never run `scripts/publish_guard.py push`, never touch C:\dev\anees-hourly.
  You may push the branch itself (it does not deploy).
- **$0.** Use only Medi's plans: `claude -p` (Claude), `codex.cmd exec -m gpt-6-astra` (ChatGPT plan),
  `agy -p` with Gemini 3.8 Flash (AI Pro). No API key of any kind (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY…).
  Before the first batch, prove each route with one call: "Reply with exactly: ok".
  If a route refuses (quota, login), go on with the judges that work and say so in the report. Never switch a login.
- **Change the builders, not only the output.** Most pages are written by scripts (scripts/build_*.py and the
  docs/js/*.js renderers). Hand-editing a generated page is undone by the next hourly run. Change the template or the
  script, rebuild, and check the page.
- **No number may change.** Before you start, save every number each page shows (Playwright: load the page, collect
  the text of every element holding a digit). After each change, the same numbers must appear on the page
  (the label may be shorter). A missing or changed number fails the round.
- **Written rules win tonight.** If rules/registry.json or a test requires text you would cut, keep it and add it to
  the morning list "Rule X forces this line: drop the rule?". Do not edit the registry or the tests to get around it.
- **Amal's pages keep their rules:** English only, no names on screen (PG-33), everything opens in place (PG-17),
  her answer buttons and the order she works in do not move.
- The repo is public: never commit anything from research/.

## 1. Pages (in this order)
1. index.html + progress.html (Progress & Stats, every tab)
2. ai-reports.html (all 4 tabs) + docs/reports/*.html
3. lessons.html + one lesson page (docs/lessons/<latest>.html; the change goes in its builder)
4. word-bank.html
5. grammar.html
6. cards.html (Flashcards & Review)
7. student.html + homework.html
8. tutor.html (every tab and card)
9. amal/grammar-rules.html and the other docs/amal/*.html pages linked from the Tutor page
10. big-picture.html, settings.html

Use Light and Dark, desktop 1280 px and phone 390 px, for every screenshot.

## 2. The test for every section and every sentence
Ask, out loud in your notes, for each one:
1. **Is it crucial?** It stays only if it is (a) a number Medi or Amal tracks, (b) an action they take (a button, a
   choice), or (c) a warning (stall, "not verified ≈", "early · n 13", held items). Anything else is cut, or goes
   behind a small ⓘ that opens in place if it truly helps someone once.
   Example to cut: "How well the robot works, what it can't see yet, and every research report behind it. How the
   student is doing lives on Progress & Stats."
2. **Can it be a picture?** A process → a flowchart. A comparison → bars side by side. A trend → a line.
   A share of a whole → one bar split in parts. A status → a coloured chip or icon. A count → one big number with a
   2-3 word label. A list of steps → numbered icons.
3. **Is what's left plain?** 8th-grade words, at most 1 line under a heading, no paragraph over 2 lines,
   every term a reader may not know is defined in a ⓘ.

## 3. Two looks for every page
- **Look A, "Flat":** Anees's own colours and Light/Dark tokens (css/sabz-tokens.css), flat icons, bold colour
  blocks, big numbers, short captions. Same app feel, far less text.
- **Look B, "Kurzgesagt":** a deep navy ground with bright accent colours, rounded shapes, simple illustrated scenes
  and characters drawn as inline SVG, big friendly numbers. It must still read well in Light mode (a light variant
  of the palette).
- All pictures are inline SVG or CSS you write. No image generator, no images from the web, no new libraries.
- The cuts and the pictures are the SAME markup in both looks; only the styling differs. Build each look as its own
  stylesheet, switched by a `data-look="flat|kurz"` attribute on `<html>` (a small switch at the top of each page, remembered
  in localStorage). "Before" lives only in the gallery screenshots and git history on master.

## 4. The loop (per page, per look)
1. Screenshot "before" (once per page).
2. Make the change (builder → rebuild).
3. Run: the number check (§0), `python -m pytest -q` for tests touching that page, and `python -I scripts/check_pages.py`.
   All must pass.
4. Screenshot "after" (Light/Dark × desktop/phone).
5. **Three judges** grade it, each on its own plan route, blind to the others:
   Claude (`claude -p`, name the PNG paths; it reads images with its Read tool), Codex GPT-6 Astra
   (`codex.cmd exec -m gpt-6-astra -i <png> ...`),
   Gemini 3.8 Flash (`agy -p`, run unsandboxed; agy has no image flag, so name the PNG paths in the prompt and ask it
   to open them; if it cannot see them, it judges from the page text and says so).
   Note: agy's weekly quota on thenatanzi ran out on 10-19 (reset about 10-24 to 10-26). If agy refuses, go on with 2 judges.
   Give each the 4 screenshots + the page text and this rubric; ask for a letter A-F per line and ONE concrete fix,
   as JSON ({"grades":{...},"fix":"..."}). Say nothing about what the other judges said.
   - ADD-friendly: can someone with ADD get the point in 5 seconds?
   - Nothing crucial missing; nothing non-crucial left
   - Pictures say it better than the old words did
   - Reads well in Light and Dark, desktop and phone (no overflow, no clipped text)
   - The look matches its brief (A or B) and feels like one app
6. If any judge gives below A on any line, apply the fixes and go to step 2. Keep the best-graded version.
7. Commit only the files you meant to change (builders, css, js, templates, the rebuilt pages). Never commit
   docs/data/tutor-notes.json, pipeline-health.json, build.json or *.first.json. Commit after every passing round: `deword: <page> look <A|B> round <n> (grades C/X/G)`.

Check the clock (`date`) at the start of every round. After 6:30 AM start no new page or round; write §5. Hard stop
7:00 AM local time, or when every page has an A from all 3 judges in both looks, whichever comes first.
Order inside a page: Look A to an A grade first, then Look B, so a page is never left with only half a look.
Log every judge call (step `deword.judge`) with scripts/track.py log_run, as the other AI steps do.

## 5. What Medi wakes up to
1. `docs/deword-gallery.html` on the branch: one row per page with before / Look A / Look B screenshots (desktop + phone,
   Light + Dark), each judge's final grade, and the count of words before → after.
   Also publish it as a private claude.ai Artifact and put the link at the top of the report.
2. `plan/DEWORD-REPORT-2026-10-23.md`, at most one screen long:
   - one line per page: words before → after, grades, done / not done
   - "Rule X forces this line: drop the rule?" list
   - any judge route that failed overnight
   - **one bold action:** which look to approve, and how (merge the branch page by page)
3. Nothing changed on the live site.
