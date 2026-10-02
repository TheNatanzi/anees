# -*- coding: utf-8 -*-
"""Step 8 of the full audit: same-day review of ONE new lesson, the same loop as the 13-lesson backfill.

    python scripts/review_lesson.py 2026-09-23              # full run: readers -> compare -> third reader -> pages -> Amal's items
    python scripts/review_lesson.py 2026-09-23 --dry-run    # reuse reader files that already exist, run no claude, no git
    python scripts/review_lesson.py 2026-09-23 --no-push    # everything but the push

Steps (a reader file is reused only while its inputs are unchanged - transcript, brief, rules, vocabulary, names, prompt;
hashes in <file>.inputs.json - so a crash resumes where it stopped, and a grown transcript is re-read. Fail closed: a
builder that fails, a broken reader file or Arabizi gaps left = exit 1 and no push):
  1 prep      docs/data/lessons/<date>.json -> data/lesson-work/full-audit/<date>.txt (needs build_lessons_page_data first)
  2 readers   two independent `claude -p` runs (READER-BRIEF.md) -> <date>.r1.json / <date>.r2.json   (parallel)
  2b type     one `claude -p` run (scripts/lesson_type_read.py prompt) -> data/lesson-work/lesson-types/<date>.json: the
              lesson's type + taught words read from context (LS-01); none valid = the run fails, no push
  3 compare   scripts/full_audit_compare.py compare -> <date>.compare.json + <date>.disputes.md
  4 third     one `claude -p` run (THIRD-READER-BRIEF.md) -> <date>.r3.json ; settle -> <date>.settled.json
  5 build     scripts/full_audit_build.py (all lessons) -> data/full-audit-2026-09-26.json + plan/FULL-AUDIT-2026-09-26.md
  6 pages     build_lessons_page_data.py, build_grammar_console.py, build_amal_grammar_rules.py, arabizi_everywhere.py
  6c source   source_audit.py <date> (raw audio: holes, labels) -> annotate -> codex_rejudge.py (Codex judges
              uncertain rows vs the audio; failure = rows stay pending) -> Amal's check list on the Tutor page
  6b arabizi   arabizi_gaps.cjs: any Arabic word on the error cards without Arabizi -> `claude -p` fills arabizi-extra.json
  7 Amal      `claude -p` pattern reader for this lesson's B rows (PATTERN-BRIEF.md, appends to patterns.json)
              -> build_amal_review.py -> amal_review_link.py (refreshes her hub payload) -> prints the hub link
  7d new words amal_new_words.py --candidates -> `claude -p` by-meaning reader -> amal_new_words.py (Tutor hub: words Amal
              used that are not on her Doc; add / later / forget)
  7c tutor     build_tutor_data.py -> docs/data/tutor.json (the Tutor page = Medi's menu of everything open for Amal)
  7b after     after_from_audit.py -> 3-5 "was he right here?" questions with clips -> amal_links kind after (on her hub)
  8 git       commit; push through scripts/publish_guard.py (unless --no-push / --dry-run / a failure above)
Never sends anything to Amal. Never re-transcribes. `claude` = the Claude Code CLI on PATH (2.1+).
"""
import argparse, datetime, inspect, json, os, subprocess, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
LOG = os.path.join(WORK, "review_lesson.log")
CLAUDE = os.environ.get("ANEES_CLAUDE", "claude")
NODE = r"C:\dev\tools\node-v24.18.0-win-x64\node.exe"
try:                                    # run log (data/runs, scripts/track.py); never blocks a review
    sys.path.insert(0, HERE)
    import track
except Exception:
    track = None


class _NoRun(dict):
    def set(self, **k): return self
    def claude(self, parsed): return self


def log(*a):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def py(*args, check=True):
    return subprocess.run([sys.executable, *args], cwd=REPO, check=check, env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def claude(prompt, label, timeout=3600, step="claude", lesson_date=None, role=None, pass_=None, brief=None, prompt_sha=None,
           inputs=(), outputs=()):
    """One headless reader. The prompt says which file to write; we only check that it appeared.
    `--output-format json` so tokens, cost and the model the CLI really used come back; the text logged below is the
    JSON's `result` (exactly what the old text output printed). One line per call goes to data/runs (scripts/track.py):
    hashes and paths only, never the prompt. --model is pinned by scripts/track.py
    (DEFAULT_CLAUDE_MODEL = claude-opus-5-5 since 2026-09-29; ANEES_CLAUDE_MODEL=<id> overrides, =cli-default unpins)."""
    log("claude start", label)
    cmd = [CLAUDE, "-p", prompt, "--output-format", "json", "--permission-mode", "bypassPermissions", "--add-dir", REPO]
    ctx, run = None, _NoRun()
    try:
        cmd += track.claude_model_args()
        ctx = track.run(step, lesson_date, kind="inference", role=role, pass_=pass_, provider="anthropic",
                        request_model=track.CLAUDE_MODEL, tool=track.tool_version(CLAUDE), prompt_file=brief,
                        prompt_sha=prompt_sha, inputs=inputs, outputs=outputs,
                        params={"prompt_arg_sha": track.sha256_text(prompt), "timeout_s": timeout,
                                "permission_mode": "bypassPermissions", "output_format": "json"})
        run = ctx.__enter__()
    except Exception:
        ctx, run = None, _NoRun()
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        try:
            parsed = track.parse_claude_output(r.stdout)
        except Exception:
            parsed = {"text": r.stdout or ""}
        log("claude done", label, (parsed.get("text") or "").strip()[-200:].replace("\n", " "))
        if r.returncode:
            log("claude stderr", label, (r.stderr or "")[-400:])
        run.claude(parsed)
        if r.returncode:
            run.set(status="error", error_type=f"exit_{r.returncode}")
        elif parsed.get("is_error"):
            run.set(status="error", error_type=str(parsed.get("subtype") or "is_error"))
    except Exception as e:
        log("claude failed", label, e)
        run.set(status="timeout" if isinstance(e, subprocess.TimeoutExpired) else "error", error_type=type(e).__name__)
    finally:
        if ctx is not None:
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                pass


def _src_sha(fn):
    """sha of an inline prompt's template (the function source), so a prompt edit shows up in the run log."""
    try:
        return track.sha256_text(inspect.getsource(fn)) if track else None
    except Exception:
        return None


def names_note(date):
    """'Names in this lesson' glossary from the names layer (scripts/names.py: places / countries as canonical + kind +
    English, people as said). Built in memory and appended to the prompt only - never written to disk (the repo is public).
    Added 2026-09-28 (names layer): every prompt below changed, so its prompt_arg_sha / prompt_sha in data/runs changes."""
    if not date:
        return ""
    try:
        import names
        g = names.glossary(date)
        return (" " + g) if g else ""
    except Exception:
        return ""


def reader_prompt(date, reader, tag=""):
    return (f"Repo: {REPO}. Read {WORK}\\READER-BRIEF.md first and follow it exactly. You are reader {reader} for lesson {date}. "
            f"Transcript: data/lesson-work/full-audit/{date}.txt. Read the WHOLE file in order. Write your JSON to "
            f"{WORK}\\{date}{tag}.{reader}.json (reader \"{reader}\"). Do not open any other reader's file, the grammar-sweep JSON, "
            f"or the sweep plan. Reply with only your counts line." + names_note(date))


def third_prompt(date, tag=""):
    return (f"Repo: {REPO}. Read {WORK}\\THIRD-READER-BRIEF.md and follow it exactly. You are the third reader for lesson {date}. "
            f"Disputes: data/lesson-work/full-audit/{date}{tag}.disputes.md. Transcript: data/lesson-work/full-audit/{date}.txt. "
            f"Write your JSON to {WORK}\\{date}{tag}.r3.json. Reply with one line: kept n, dropped n, added n." + names_note(date))


def pattern_prompt(date):
    return (f"Repo: {REPO}. Read {WORK}\\PATTERN-BRIEF.md and follow it exactly, with ONE change: only the B rows of lesson {date} "
            f"(rows in data/full-audit-2026-09-26.json with date {date} and kind vocab-B or grammar-B). First read the existing "
            f"{WORK}\\patterns.json: if a row fits one of its patterns, add the row's uid to that pattern's rows; otherwise add a "
            f"new pattern. Write the whole updated file back to {WORK}\\patterns.json (keep every existing pattern and row). "
            f"Reply with one line: n rows placed, n new patterns." + names_note(date))


def new_words_prompt(date):
    """Step 7d reader (Medi 2026-10-02): judge the lesson's new-word candidates by meaning (memory anees-list-by-meaning)."""
    return (f"Repo: {REPO}. Read the docstring of scripts/amal_new_words.py and RULES.md S1. "
            f"data/lesson-work/amal-new-words/{date}.candidates.json lists words Amal said or typed in lesson {date} that a string "
            f"check could not find on her vocabulary Doc (docs/data/words.json items: arabizi, arabic, english, plural, aliases). "
            f"Judge EVERY candidate BY MEANING (any tense, plural, gender, pronoun ending, article, one-letter transcription "
            f"difference, Arabic or English meaning) using the lesson transcript data/lesson-work/full-audit/{date}.txt for context. "
            f"Append one row per candidate to data/lesson-work/amal-new-words-verdicts.json (a JSON list; keep every existing row): "
            f'{{"date":"{date}","key":<candidate key exactly>,"verdict":"new|on_doc|name|english|function|garble|loanword","arabic":<Arabic script or null>,'
            f'"arabizi":<only the exact form SHE typed in chat, else null - never invent a spelling>,"english":<short meaning>,"t":<candidate t>,'
            f'"line":<her line>,"typed":<true if from chat>,"doc_match":<the Doc entry for on_doc, else null>,"dup_of":<for another form of a '
            f'new word already listed in this lesson: the first key, else null>,"reason":<one short sentence>}}. '
            f"new = a real content word she used that is NOT on the Doc by meaning; function = particles, pronouns, question words, "
            f"fillers; garble = speech-engine error or cut-off; loanword = a dish name, food, brand, loan word or country (rule WS-15, Medi: 'we dont need to add proper nouns like kabaab and ma2loobe and cake and countries'). Be strict: only genuinely new vocabulary is 'new'. Edit no other file. "
            f"Reply with one line: new n, on_doc n, other n." + names_note(date))


def gaps_prompt(date=None):
    return (f"Repo: {REPO}. Read RULES.md S1 (incl. the 2026-09-26 line: nothing on the error cards stays Arabic-only). "
            f"data/lesson-work/arabizi-gaps.json lists Arabic tokens the renderer cannot spell. Add every one to "
            f"docs/data/arabizi-extra.json 'words' ({{latin, method pieces|her-chat|sound|guess|as-said, from, meaning}}), her letters "
            f"and her spellings first (docs/data/words.json arabizi, house_spelling.json). Only add. Then run "
            f"`{NODE} scripts/arabizi_gaps.cjs` until it prints 0 words. Reply with one line: added n, gaps left n. "
            f"A proper name (docs/data/names.json: a place, country, nationality or person) is never spelled word by word "
            f"(بيت لحم is Bethlehem, not house + meat): give it the English name as its meaning." + names_note(date))


# ---------------------------------------------------------------- reader-file cache (engineering audit 2026-09-29, area 4)
# A reader file is reused only while everything it read is unchanged: the transcript (a Meet gap fill grew 09-23 by 266
# lines and 09-26 by 149 lines AFTER their readers ran - reuse-by-existence kept the old reading), its brief, the rules
# (RULES.md, buckets.md), the vocabulary (amal-sheet.txt), the names glossary and the prompt. Hashes sit next to the file
# in <file>.inputs.json (scripts/accuracy_gates.py write_manifest / cache_state).

def _sha_text(t):
    import hashlib
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def transcript_text(date, repo=None):
    """Exactly what full_audit_prep writes to <date>.txt for the readers (tested against it)."""
    repo = repo or REPO
    L = json.load(open(os.path.join(repo, "docs", "data", "lessons", date + ".json"), encoding="utf-8"))
    sys.path.insert(0, HERE)
    import full_audit_prep as P
    lines = [f"# Lesson {date} - {len(L['turns'])} turns on the lesson clock (mm:ss = seconds on the page audio)", ""]
    for t in L["turns"]:
        who = t["who"]
        tag = f"CHAT {t.get('typed_by','')}".strip() if who == "chat" else who
        lines.append(f"[{P.mmss(t['t'])}] {tag}: {t['text']}")
    return "\n".join(lines) + "\n"


def readers_read_current(date, repo=None):
    """None when the lesson's readers read the transcript the pages show now, else why not (for scripts/publish_guard.py
    and the hourly re-review). Uses the r1 manifest when there is one, else the .txt the readers were given."""
    repo = repo or REPO
    work = os.path.join(repo, "data", "lesson-work", "full-audit")
    fresh = transcript_text(date, repo)
    man = os.path.join(work, f"{date}.r1.json.inputs.json")
    if os.path.exists(man):
        read = json.load(open(man, encoding="utf-8")).get("inputs", {}).get(f"data/lesson-work/full-audit/{date}.txt")
        # the manifest hashes the file's bytes; full_audit_prep writes it in text mode, so on Windows it holds CRLF
        # (2026-10-02: every manifest-pinned lesson read as 'changed' on this PC)
        return None if read in (_sha_text(fresh), _sha_text(fresh.replace(chr(10), chr(13) + chr(10)))) else "transcript changed after the readers read it"
    txt = os.path.join(work, date + ".txt")
    if not os.path.exists(txt):
        return "no record of what the readers read"
    old = open(txt, encoding="utf-8").read()
    return None if old == fresh else f"transcript changed after the readers read it ({len(old.splitlines())} -> {len(fresh.splitlines())} lines)"


def _gates():
    sys.path.insert(0, HERE)
    import accuracy_gates as G
    return G


def _prompt_sha(prompt):
    return _sha_text(prompt.replace(REPO, "<REPO>"))


LEGACY = "stale: no input manifest (written before 2026-09-27 or by hand)"


def cache_decision(out, inputs, prompt, legacy_ok):
    """'fresh' | 'missing' | 'adopt' | 'stale: <why>'. 'adopt' = a file written before manifests existed whose transcript is
    unchanged: kept, and pinned by a manifest from now on."""
    G = _gates()
    st = G.cache_state(out, inputs, repo=REPO)
    if st == LEGACY and legacy_ok:
        return "adopt"
    if st == "fresh":
        man = json.load(open(G.manifest_path(out), encoding="utf-8"))
        if man.get("prompt_sha") not in (None, _prompt_sha(prompt)):
            return "stale: the prompt changed"
    return st


def pin(out, inputs, prompt, adopted=False):
    extra = {"prompt_sha": _prompt_sha(prompt)}
    if adopted:
        extra["adopted"] = "written before input manifests; its transcript was unchanged when pinned"
    _gates().write_manifest(out, inputs, repo=REPO, extra=extra)


# Each reader file is checked against ITS OWN shape (2026-10-02 freshness audit): the third reader writes
# {"rulings": [...], "added": [...], "challenges": [...]} (what full_audit_compare.settle reads), never "rows"; checking it
# for "rows" failed every new lesson's review since 2026-09-29 (09-23 and 10-01 never settled, the hourly job blocked).
READER_SHAPES = {"reader": ("rows",), "third": ("rulings",)}


def valid_reader_file(out, date, kind="reader"):
    """A reader file must be whole JSON for this lesson with its list (r1/r2: rows; r3: rulings, plus optional added /
    challenges lists); a cut-off or wrong file fails the run."""
    try:
        d = json.load(open(out, encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(d, dict) or d.get("date") not in (None, date):
        return False
    if not all(isinstance(d.get(k), list) for k in READER_SHAPES[kind]):
        return False
    return kind != "third" or all(isinstance(d.get(k, []), list) for k in ("added", "challenges"))


def drop(out, why):
    log("stale, re-reading:", os.path.basename(out), "-", why)
    for p in (out, out + ".inputs.json"):
        if os.path.exists(p):
            os.remove(p)                 # the old file stays in git history


def new_words_step(d, dry_run, failures, repo=None, reader=None, run=None):
    """Step 7d for ONE lesson (AM-11, Medi 2026-10-02: "we should be doing this for all new lessons"): string candidates
    -> one by-meaning reader for the candidates not judged yet -> docs/data/amal-new-words.json (the Tutor hub 'New
    words' task: add to the Doc / save for later / forget). Fail closed: a candidate still unjudged after the reader is a
    failure (no push; the hourly job retries), so a lesson can never silently skip Amal's new words.
    `repo` / `reader` / `run` are injectable for tests/test_amal_word_lists.py."""
    import amal_new_words
    if d < amal_new_words.START:          # Medi 2026-10-02: from the 10-01 lesson on (older lessons were never asked)
        return []
    repo = repo or REPO
    reader = reader or claude
    run = run or (lambda *args: py(*args, check=False))
    run(os.path.join(HERE, "amal_new_words.py"), "--candidates", d)
    vp = os.path.join(repo, "data", "lesson-work", "amal-new-words-verdicts.json")
    cand = os.path.join(repo, "data", "lesson-work", "amal-new-words", d + ".candidates.json")

    def unjudged():
        judged = {v.get("key") for v in (json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else []) if v.get("date") == d}
        return [c for c in (json.load(open(cand, encoding="utf-8"))["candidates"] if os.path.exists(cand) else []) if c["key"] not in judged]

    if not os.path.exists(cand):
        failures.append(f"new words: no candidate file for {d}"); log("FAILED new-word candidates for", d)
    todo = unjudged()
    if todo and not dry_run:
        reader(new_words_prompt(d), f"{d} new words", step="amal.new_words", lesson_date=d, role="new_words",
               prompt_sha=_src_sha(new_words_prompt), inputs=[cand, os.path.join(repo, "docs", "data", "words.json")], outputs=[vp])
        todo = unjudged()
        if todo:
            failures.append(f"new words: {len(todo)} candidate(s) of {d} not judged by the reader")
            log("FAILED new-word reader left", len(todo), "unjudged for", d)
    rc = run(os.path.join(HERE, "amal_new_words.py")).returncode
    if rc:
        failures.append(f"amal_new_words.py exit {rc}"); log("FAILED amal_new_words.py exit", rc)
    return todo


def taught_cross_step(d, dry_run, failures, repo=None, reader=None):
    """Step 7e, LS-09 / LS-10 (Medi 2026-10-02 "there was a new word from the lesson yesterday... you didnt catch it"):
    the Tutor new-words list (7d) is built after the type read (2b), so the two are cross-checked here. A Tutor word missing
    from taught_words (and not in not_taught with a reason), or an off-lesson window with Amal teaching inside, goes back to
    the type reader once; still failing = a failure (no push; the publish guard's taught_words_cross_check also blocks)."""
    import lesson_type_read as LTR
    repo = repo or REPO
    reader = reader or claude
    issues = LTR.cross_check(d, repo)
    if issues and not dry_run and os.path.exists(LTR.path(d, repo)):
        reader(LTR.reconcile_prompt(d, issues, repo), f"{d} taught words cross-check", step="lesson.type_reconcile",
               lesson_date=d, role="type", prompt_sha=_src_sha(LTR.reconcile_prompt), inputs=[LTR.path(d, repo)],
               outputs=[LTR.path(d, repo)])
        issues = LTR.cross_check(d, repo)
    if issues:
        failures.append("taught words cross-check (LS-09/LS-10): " + "; ".join(issues)[:300])
        log("!! TAUGHT WORDS CROSS-CHECK FAILED:", "; ".join(issues))
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--dry-run", action="store_true", help="reuse existing reader files, never call claude, no git")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    d = a.date
    os.makedirs(WORK, exist_ok=True)
    f = lambda name: os.path.join(WORK, f"{d}{name}")
    failures = []                        # fail closed: any entry = exit 1 and no push
    log("=== review_lesson", d, "dry-run" if a.dry_run else "")
    # 1 prep (one lesson): ALWAYS rewrite the transcript dump, Amal's sheet and the buckets from today's data (it used to
    # run only when <date>.txt was missing, so a grown transcript or a new rule never reached the readers)
    old_txt = open(f(".txt"), encoding="utf-8").read() if os.path.exists(f(".txt")) else None
    if old_txt is not None and old_txt != transcript_text(d):
        # legacy reader files (no manifest) read the OLD transcript: pin that fact before the dump is rewritten, so the
        # evidence survives a run that stops early (dry-run, a failed reader) and the freshness check stays right
        for r in ("r1", "r2", "r3"):
            out = f(f".{r}.json")
            if os.path.exists(out) and not os.path.exists(out + ".inputs.json"):
                _gates().write_manifest(out, [f(".txt")], repo=REPO, extra={
                    "legacy": "written before input manifests; this is the transcript it read, which has changed since"})
    sys.path.insert(0, HERE)
    import full_audit_prep as P
    P.REPO, P.OUT, P.DATES = REPO, WORK, [d]
    P.main()
    same_txt = old_txt is not None and old_txt == open(f(".txt"), encoding="utf-8").read()
    common = [os.path.join(WORK, "buckets.md"), os.path.join(REPO, "RULES.md"), os.path.join(REPO, "docs", "data", "names.json")]
    reader_in = [f(".txt"), os.path.join(WORK, "READER-BRIEF.md"), os.path.join(WORK, "amal-sheet.txt")] + common
    # 2 readers
    jobs, rerun = [], set()
    for r in ("r1", "r2"):
        out, prompt = f(f".{r}.json"), reader_prompt(d, r)
        st = cache_decision(out, reader_in, prompt, legacy_ok=same_txt)
        if st == "adopt":
            pin(out, reader_in, prompt, adopted=True); log("pinned", os.path.basename(out), "(transcript unchanged)")
        elif st != "fresh":
            if st.startswith("stale"):
                if a.dry_run:
                    log("dry-run:", os.path.basename(out), st, "- stopping"); return 2
                drop(out, st)
            jobs.append((r, out, prompt)); rerun.add(r)
    if jobs and a.dry_run:
        log("dry-run: reader files missing, stopping:", [j[1] for j in jobs]); return 2
    ts = [threading.Thread(target=claude, args=(prompt, f"{d} {r}"),
                           kwargs=dict(step="full_audit.reader", lesson_date=d, role=r, pass_=1,
                                       brief=os.path.join(WORK, "READER-BRIEF.md"), inputs=[f(".txt")], outputs=[out]))
          for r, out, prompt in jobs]
    [t.start() for t in ts]; [t.join() for t in ts]
    for r, out, prompt in jobs:
        if not os.path.exists(out):
            log("a reader wrote nothing; stopping:", r); return 1
        if not valid_reader_file(out, d):
            os.replace(out, out[:-5] + ".invalid.json"); log("a reader wrote a broken file; stopping:", r); return 1
        pin(out, reader_in, prompt)
    # 2b LS-01 (Medi 2026-10-02 "This was clearly a grammar review for 'el' im shocked you didnt detect that"): the lesson's
    # TYPE and TAUGHT words are read from context the same day -> data/lesson-work/lesson-types/<date>.json, which
    # build_lessons_page_data.py reads (its hand dicts stay as overrides). No valid read = the run fails (no push) and the
    # publish guard's required lesson_type_read check blocks: the "free-speak, Not read yet" default is never published.
    import lesson_type_read as LTR
    type_read, type_why = LTR.load(d, REPO)
    if not type_read and not a.dry_run:
        os.makedirs(os.path.dirname(LTR.path(d, REPO)), exist_ok=True)
        claude(LTR.prompt(d, REPO), f"{d} lesson type", step="lesson.type_read", lesson_date=d, role="type",
               prompt_sha=_src_sha(LTR.prompt), inputs=[f(".txt")], outputs=[LTR.path(d, REPO)])
        type_read, type_why = LTR.load(d, REPO)
    if type_read:
        log("lesson type", d, type_read["type"], type_read.get("review_mode") or "", "| taught", len(type_read["taught"]),
            "| taught_words", len(type_read["taught_words"]))
    else:
        failures.append("lesson type not read (LS-01): " + "; ".join(type_why)[:200])
        log("!! LESSON TYPE NOT READ (LS-01):", "; ".join(type_why), "- the page would show the default; not pushed")
    # 3 compare
    py(os.path.join(HERE, "full_audit_compare.py"), "compare", d)
    # 4 third reader + settle
    third_in = [f(".txt"), f(".disputes.md"), f(".r1.json"), f(".r2.json"), os.path.join(WORK, "THIRD-READER-BRIEF.md")] + common
    out3, prompt3 = f(".r3.json"), third_prompt(d)
    st = cache_decision(out3, third_in, prompt3, legacy_ok=same_txt and not rerun)
    if st == "adopt":
        pin(out3, third_in, prompt3, adopted=True)
    elif st != "fresh":
        if a.dry_run:
            log("dry-run: r3", st, "- stopping"); return 2
        if st.startswith("stale"):
            drop(out3, st)
        claude(prompt3, f"{d} r3", step="full_audit.third_reader", lesson_date=d, role="r3", pass_=2,
               brief=os.path.join(WORK, "THIRD-READER-BRIEF.md"), inputs=[f(".txt"), f(".disputes.md"), f(".r1.json"), f(".r2.json")],
               outputs=[out3])
        if not os.path.exists(out3):
            log("third reader wrote nothing; stopping"); return 1
        if not valid_reader_file(out3, d, kind="third"):
            os.replace(out3, out3[:-5] + ".invalid.json"); log("third reader wrote a broken file; stopping"); return 1
        pin(out3, third_in, prompt3)
    py(os.path.join(HERE, "full_audit_compare.py"), "settle", d)
    # 5 build the audit (all lessons) + 6 pages. A builder that fails leaves its page stale: recorded, the run fails, no push.
    py(os.path.join(HERE, "full_audit_build.py"))
    # the build rewrites the audit JSON without Amal's rulings: re-apply them before any page is built (2026-09-30)
    py(os.path.join(HERE, "apply_amal_audit_rulings.py"))
    for s in ("build_lessons_page_data.py", "build_grammar_console.py", "build_amal_grammar_rules.py", "arabizi_everywhere.py"):
        rc = py(os.path.join(HERE, s), check=False).returncode
        if rc:
            failures.append(f"{s} exit {rc}"); log("FAILED", s, "exit", rc)
    # 6c source audit + second judge (eng audit 2026-09-29, decisions 3 and 5): the raw audio decides which stretches are
    # transcribed (holes -> unscoreable rows, release reasons); then Codex (never Claude) re-judges every uncertain row
    # against the audio. The source audit is offline and must work (a failure blocks). A Codex failure does NOT block:
    # its rows simply stay "pending" (not verified, on nobody's list as settled), and the next run resumes them.
    rc = py(os.path.join(HERE, "source_audit.py"), d, check=False).returncode
    if rc:
        failures.append(f"source_audit.py {d} exit {rc}"); log("FAILED source_audit.py exit", rc)
    rc = py(os.path.join(HERE, "accuracy_gates.py"), "annotate", check=False).returncode
    if rc:
        failures.append(f"accuracy_gates.py annotate exit {rc}"); log("FAILED accuracy_gates annotate exit", rc)
    if not a.dry_run:
        rc = py(os.path.join(HERE, "codex_rejudge.py"), check=False).returncode
        log("codex_rejudge.py", "ok" if not rc else f"exit {rc}: unjudged rows stay pending (not verified); the next run resumes")
    rc = py(os.path.join(HERE, "codex_rejudge.py"), "--list", check=False).returncode or         py(os.path.join(HERE, "accuracy_gates.py"), "annotate", check=False).returncode
    if rc:
        failures.append(f"Amal's check list / release layer rebuild exit {rc}"); log("FAILED amal-verify / annotate exit", rc)
    # 6b Arabizi guard (Medi 2026-09-26: "why no arabizi again. How do we stop you from doing this?"): every Arabic word on
    # the error cards must have Arabizi. Gaps -> one claude run fills docs/data/arabizi-extra.json (RULES.md S1), re-check.
    gap = lambda: subprocess.run([NODE, os.path.join(HERE, "arabizi_gaps.cjs"), "--json", os.path.join(REPO, "data", "lesson-work", "arabizi-gaps.json")],
                                 cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    g = gap(); log(g.stdout.strip())
    if g.returncode and not a.dry_run:
        extra = os.path.join(REPO, "docs", "data", "arabizi-extra.json")
        claude(gaps_prompt(d), f"{d} arabizi gaps", step="arabizi.fill_gaps", lesson_date=d, role="arabizi",
               prompt_sha=_src_sha(gaps_prompt), inputs=[os.path.join(REPO, "data", "lesson-work", "arabizi-gaps.json"), extra],
               outputs=[extra]); g = gap(); log("after fill:", g.stdout.strip())
        if not g.returncode:
            rc = py(os.path.join(HERE, "build_lessons_page_data.py"), check=False).returncode
            if rc:
                failures.append(f"build_lessons_page_data.py (after the Arabizi fill) exit {rc}")
    if g.returncode:
        failures.append("Arabizi gaps left on the error cards: " + g.stdout.strip()[:120])
        log("!! ARABIZI GAPS LEFT on the error cards - fill data/lesson-work/arabizi-gaps.json into arabizi-extra.json before telling Medi it is done")
    # 7 Amal's items: patterns for this lesson's B rows -> review data
    A = json.load(open(os.path.join(REPO, "data", "full-audit-2026-09-26.json"), encoding="utf-8"))
    b_rows = [r["uid"] for r in A["rows"] if r["date"] == d and r.get("kind") in ("vocab-B", "grammar-B")]
    pats = json.load(open(os.path.join(WORK, "patterns.json"), encoding="utf-8")) if os.path.exists(os.path.join(WORK, "patterns.json")) else {"patterns": []}
    placed = {u for p in pats["patterns"] for u in p.get("rows", [])}
    if [u for u in b_rows if u not in placed]:
        if a.dry_run:
            log("dry-run: %d B rows of %s not yet in patterns.json; they would be grouped by claude, then shown as one-row patterns until then" % (len([u for u in b_rows if u not in placed]), d))
        else:
            claude(pattern_prompt(d), f"{d} patterns", step="amal.patterns", lesson_date=d, role="patterns",
                   brief=os.path.join(WORK, "PATTERN-BRIEF.md"),
                   inputs=[os.path.join(REPO, "data", "full-audit-2026-09-26.json"), os.path.join(WORK, "patterns.json")],
                   outputs=[os.path.join(WORK, "patterns.json")])
    # 7b Amal's after-lesson questions for THIS lesson (scripts/after_from_audit.py): 3-5 rows the readers were least
    # sure of, one clip each; her taps come back through apply_amal_audit_rulings.py. Never sent.
    for s in (("build_amal_review.py",), ("after_from_audit.py", d, "--dry-run") if a.dry_run else ("after_from_audit.py", d)):
        rc = py(os.path.join(HERE, s[0]), *s[1:], check=False).returncode
        if rc:
            failures.append(f"{s[0]} exit {rc}"); log("FAILED", s[0], "exit", rc)
    link = None
    if not a.dry_run:
        r = subprocess.run([sys.executable, os.path.join(HERE, "amal_review_link.py")], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
        # it prints "REVIEW <url>" since the Tutor Hub page was removed (2026-09-28); the old "HUB" parse always gave None
        link = next((l.split(None, 1)[1] for l in (r.stdout or "").splitlines() if l.startswith(("REVIEW", "HUB")) and len(l.split(None, 1)) > 1), None)
        log("review link", link, "" if not r.returncode else f"(amal_review_link exit {r.returncode}: database only, pages unaffected)")
    # 7d new words Amal used that are not on her Doc (Medi 2026-10-02 "we should be doing this for all new lessons"): string
    # candidates -> one by-meaning reader -> docs/data/amal-new-words.json (Tutor hub item: add to the Doc / later / forget).
    # Unjudged candidates are never shown to Amal; a reader that fails leaves them unjudged (counted) and fails the run.
    new_words_step(d, a.dry_run, failures)
    taught_cross_step(d, a.dry_run, failures)
    # 7c the Tutor page (Medi's menu) lists every open link with its total - rebuilt so the new after link shows up
    rc = py(os.path.join(HERE, "build_tutor_data.py"), check=False).returncode
    if rc:
        failures.append(f"build_tutor_data.py exit {rc}"); log("FAILED build_tutor_data.py exit", rc)
    # 8 git: the local commit is kept either way (nothing lost); the push goes through the publish guard, and only when
    # nothing above failed (scripts/publish_guard.py; Medi decision 7, 2026-09-29)
    if not a.dry_run:
        subprocess.run(["git", "add", "-A", "data/full-audit-2026-09-26.json", "plan/FULL-AUDIT-2026-09-26.md", "docs", "data/lesson-work/full-audit",
                        "data/lesson-work/amal-new-words", "data/lesson-work/amal-new-words-verdicts.json", "data/lesson-work/lesson-types"], cwd=REPO)
        subprocess.run(["git", "commit", "-q", "-m", f"Same-day review {d}: two readers + third reader, pages fed, Amal's items\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"], cwd=REPO)
        if failures:
            log("NOT PUSHED:", "; ".join(failures))
        elif not a.no_push:
            import publish_guard
            res = publish_guard.guarded_push(REPO, source=f"review_lesson {d}", log=log)
            if not res.get("pushed"):
                failures.append("publish guard: " + str(res.get("reason"))[:300])
    S = json.load(open(f(".settled.json"), encoding="utf-8"))["counts"]
    log("DONE" if not failures else "FAILED", d, "rows", S.get("final"), "agreement", S.get("agreement_pct"), "B rows for Amal", len(b_rows),
        "review link", link or ("(dry-run: not minted)" if a.dry_run else "none"), *(["|", "; ".join(failures)] if failures else []))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
