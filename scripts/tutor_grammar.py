# -*- coding: utf-8 -*-
"""AM-31 'Add grammar' on the Tutor page (Medi 2026-10-12: "lets do a handoff chip to create a way for amal to add grammar.
Shes jsut going to put the lesson and you give it a letter# and rewrite it and have her approve" / "make it an option in the
tutor portal "add grammar"").

The tutor writes a grammar lesson in her own words (docs/js/hub/grammar-add-task.js). This is the server half:

  pull      read her rows (amal_rules source 'tutor_grammar', raw history, undo rows too) into
            data/lesson-work/tutor-grammar/rows.json (read-only mirror), give every submission that needs one a proposal
            (ONE Claude read through `claude -p`, scripts/tutor_grammar_prompt.md, logged like every paid call: scripts/track.py
            run line + data/budget.json 'anthropic'), then `build`
  build     no network: docs/data/tutor-grammar.json (what her page shows) from the mirror + the proposal store
  check     the store and the page file agree with the mirror (no AI call)

Her rows (no migration: amal_rules has no CHECK on kind / source; lesson_date null; written with the hub's grammar-notes
link token like her rule notes):
  tgram:<sid>          kind 'grammar_submit'  payload {text, example}          (an undo row on this key withdraws it)
  tgram:<sid>:answer   kind 'grammar_yes' | 'grammar_change' | 'grammar_no' | 'undo', payload {v, id, what}
The latest row per key wins (AM-17). An answer counts only for the proposal version it names (payload.v): 'Change it' on
version 2 makes version 3, and version 3 is unanswered until she taps again.

The proposal store data/lesson-work/tutor-grammar/proposals.json keeps every version (paid AI output, never rebuilt) and
every rule id ever handed out ('ids_given'). A rule id is the next free number in its letter group: one more than the
highest number any bucket, any GR-18 proposal or any id ever handed out here has used - so a retired id is never reused.

Only her 'Yes, add it' on the current version adds the rule: approved_buckets() is read by scripts/build_grammar_buckets.py
(a new bucket, added_by 'tutor', detector None). The AI never writes a detector: scripts/detect_grammar_usage.py lists such
a rule under 'no_automatic_detection' and it is counted only from the readers and the tutor's and the student's notes
until a person adds one. Past lessons are re-scored only on Medi's yes (PR-05). Code never contacts her (AM-01).

AM-32 (Medi 2026-10-12: "it would be nice to have you detect new grammar and suggest it if you hear it in our convo" /
"cant we tell from the transcript about the grammar rules?"):
  hear      after a lesson is reviewed (scripts/review_lesson.py; `pull` retries a lesson whose read failed), ONE lean
            `claude -p` read of the lesson TRANSCRIPT (scripts/tutor_grammar_heard_prompt.md, about $0.05, logged in
            data/runs + data/budget.json) finds grammar the tutor TAUGHT or explained that fits no rule. Each finding is
            checked here, never trusted: her quote must be on one of her own lines at that time (the line and the
            student's line before it are copied from the transcript, never from the AI); a GR-18 proposal within 30 s in
            the same lesson, or a rule / proposal with the same name, drops it (GR-18 already turns uncategorised
            corrections into proposals). A kept finding becomes a card on her 'Add grammar' list - the same proposal
            shape, the same id assignment (next_id, ids_given) and the same Yes / Change it / Not a rule rows - marked
            'Claude heard this in the <date> lesson at mm:ss'. Its sid is heard-<yyyymmdd>-<mmss>; there is no submit row:
            store['heard'][sid] holds the moment, store['heard_runs'][date] the one read per lesson."""
import datetime as dt
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

SOURCE = "tutor_grammar"
SUBMIT, YES, CHANGE, NO, UNDO = "grammar_submit", "grammar_yes", "grammar_change", "grammar_no", "undo"
FAMILIES = ("A", "B", "C", "D", "E")
MODEL = "claude-sonnet-5-5"
CLAUDE = os.environ.get("ANEES_CLAUDE_BIN") or "claude"
MAX_PER_RUN = 10
MAX_TEXT = 3000
PROMPT_P = os.path.join(HERE, "tutor_grammar_prompt.md")
WORK = os.path.join("data", "lesson-work", "tutor-grammar")
ROWS_REL = os.path.join(WORK, "rows.json")
STORE_REL = os.path.join(WORK, "proposals.json")
PAGE_REL = os.path.join("docs", "data", "tutor-grammar.json")
NO_DETECTOR = "no automatic detection yet"


def J(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def P(repo, rel):
    return os.path.join(repo, rel)


# ------------------------------------------------------------------ her rows -> submissions
def sid_of(key):
    m = re.match(r"^tgram:([A-Za-z0-9_-]{4,64})(:answer)?$", str(key or ""))
    return (m.group(1), bool(m.group(2))) if m else (None, False)


def _order(r):
    return (str(r.get("created_at") or ""), int(r.get("id") or 0) if str(r.get("id") or "").isdigit() else 0)


def heard_sub(sid, h):
    """AM-32: a moment Claude heard her teach, as a submission: her quote is the text, her own words near it the example
    (so an example she said is 'hers', S1); no submit row exists, so it is never withdrawn."""
    return {"sid": sid, "text": h.get("quote") or "", "example": h.get("hers") or "", "at": h.get("at"), "withdrawn": False,
            "heard": {k: h.get(k) for k in ("date", "t", "quote", "line", "before")}}


def reduce_rows(rows, heard=None):
    """Her rows (any order) -> {sid: {sid, text, example, at, withdrawn, answer}}; latest row per key wins (AM-17).
    heard (store['heard'], AM-32): the moments Claude heard her teach join as submissions with no submit row."""
    subs, answer = {}, {}
    for r in sorted((x for x in rows or [] if x and x.get("source", SOURCE) == SOURCE), key=_order):
        sid, is_answer = sid_of(r.get("word_key"))
        if not sid:
            continue
        p = r.get("payload") or {}
        if is_answer:
            answer[sid] = None if r.get("kind") == UNDO else {"kind": r.get("kind"), "v": p.get("v"), "what": str(p.get("what") or "")[:MAX_TEXT],
                                                               "at": r.get("created_at"), "id": r.get("id")}
        elif r.get("kind") == SUBMIT:
            subs[sid] = {"sid": sid, "text": str(p.get("text") or "").strip()[:MAX_TEXT], "example": str(p.get("example") or "").strip()[:600],
                         "at": r.get("created_at"), "withdrawn": False}
        elif r.get("kind") == UNDO and sid in subs:
            subs[sid]["withdrawn"] = True
    for sid, h in (heard or {}).items():
        subs.setdefault(sid, heard_sub(sid, h))
    for sid, s in subs.items():
        s["answer"] = answer.get(sid)
    return subs


def current(versions):
    return versions[-1] if versions else None


def answer_for(sub, versions):
    """Her live answer on the CURRENT version, or None (an answer on an older version was used to make this one)."""
    cur, a = current(versions), sub.get("answer")
    return a if (cur and a and a.get("v") == cur.get("v")) else None


def state(sub, versions):
    """waiting (Claude has not rewritten it yet, or is re-writing after 'Change it') | proposed | added | not_rule |
    not_grammar (Claude read it as no grammar rule) | withdrawn."""
    if sub.get("withdrawn"):
        return "withdrawn"
    cur, a = current(versions), answer_for(sub, versions)
    if not cur:
        return "waiting"
    if a and a["kind"] == CHANGE:
        return "waiting"
    if a and a["kind"] == YES:
        return "added"
    if a and a["kind"] == NO:
        return "not_rule"
    return "not_grammar" if cur.get("grammar") is False else "proposed"


def needs_proposal(sub, versions):
    """No version yet, or her 'Change it' on the current one (and the text is not empty)."""
    if sub.get("withdrawn") or not sub.get("text"):
        return False
    a = answer_for(sub, versions)
    return not versions or bool(a and a["kind"] == CHANGE and a.get("what"))


# ------------------------------------------------------------------ rule ids
def _num(rid, fam):
    m = re.match(r"^(?:P-)?%s(\d+)[a-z]?$" % fam, str(rid or ""))
    return int(m.group(1)) if m else None


def taken_ids(repo=REPO, store=None):
    """Every rule id ever used: the buckets, the GR-18 proposals (P-A13 -> A13, and their 'bucket'), and every id this
    store ever handed out (ids_given - an id she said no to, or undid, stays taken: never reused)."""
    out = set()
    B = J(P(repo, os.path.join("docs", "data", "grammar-buckets.json")), {}) or {}
    out |= {b.get("id") for b in B.get("buckets", [])}
    for rel in (os.path.join("docs", "data", "grammar-proposals.json"), os.path.join("data", "lesson-work", "full-audit", "proposed-buckets.json")):
        for p in (J(P(repo, rel), {}) or {}).get("proposals", []):
            out.add(str(p.get("id") or "").replace("P-", "", 1))
            if p.get("bucket"):
                out.add(p["bucket"])
    out |= set((store or {}).get("ids_given") or [])
    return {x for x in out if x}


def next_id(family, taken):
    """The next free number in the letter group: highest used + 1 (gaps are never filled - a gap may be a retired id)."""
    fam = str(family or "").upper()
    if fam not in FAMILIES:
        raise ValueError("family must be one of %s" % ", ".join(FAMILIES))
    nums = [n for n in (_num(t, fam) for t in taken) if n is not None]
    return "%s%d" % (fam, (max(nums) if nums else 0) + 1)


# ------------------------------------------------------------------ the AI read -> one proposal
def prompt_text():
    with open(PROMPT_P, encoding="utf-8") as f:
        return f.read()


def fill(sub, buckets, asked=None, prev=None):
    text = sub.get("text") or ""
    if sub.get("heard"):
        h = sub["heard"]
        text = ("Claude heard the tutor teach this in the %s lesson at %s. Her words: \u00ab%s\u00bb. Her line: \u00ab%s\u00bb. "
                "The student's line before it: \u00ab%s\u00bb." % (h.get("date"), h.get("t"), h.get("quote"), h.get("line"), h.get("before") or ""))
    rules = "\n".join("- %s %s: %s" % (b["id"], b.get("name", ""), str(b.get("one_line") or "").replace("`", "")) for b in buckets if b.get("family") in FAMILIES)
    ask = ""
    if asked and prev:
        ask = ("\nShe already saw this card and asked for a change. Keep everything she did not ask to change.\n"
               "The card she saw: " + json.dumps({k: prev.get(k) for k in ("family", "name", "one_line", "formula", "examples", "why", "overlaps")}, ensure_ascii=False) +
               "\nWhat she wants changed: " + asked + "\n")
    return (prompt_text().replace("{asked}", ask).replace("{rules}", rules).replace("{text}", text)
            .replace("{example}", sub.get("example") or ""))


def _words(s):
    return {w for w in re.findall(r"[0-9a-zء-ي]+", str(s or "").lower()) if w}


def clean(ai, sub, buckets, taken, prev=None):
    """The AI's JSON -> a proposal the page can show, checked here, never trusted: family A-E, the id from next_id() (the
    same id as the version before when the family is unchanged), 1-4 examples, an example is 'hers' only when every word
    of it is in her own text or example (S1: anything else is marked unverified), an overlap only with a real rule id."""
    if not isinstance(ai, dict):
        return None
    if ai.get("grammar") is False:
        return {"grammar": False, "why": str(ai.get("why") or "")[:300]}
    fam = str(ai.get("family") or "").strip().upper()[:1]
    if fam not in FAMILIES:
        return None
    rid = prev["id"] if prev and prev.get("family") == fam and prev.get("id") else next_id(fam, taken)
    hers = _words(sub.get("text")) | _words(sub.get("example"))
    ex = []
    for e in (ai.get("examples") or [])[:4]:
        if isinstance(e, (list, tuple)):
            e = {"arabizi": e[0] if e else "", "english": e[1] if len(e) > 1 else ""}
        if not isinstance(e, dict) or not str(e.get("arabizi") or e.get("arabic") or "").strip():
            continue
        az, ar = str(e.get("arabizi") or "").strip()[:200], str(e.get("arabic") or "").strip()[:200]
        own = _words(az or ar)
        ex.append({"arabizi": az, "arabic": ar, "english": str(e.get("english") or "").strip()[:200], "hers": bool(own) and own <= hers})
    ids = {b["id"]: b for b in buckets}
    ov = ai.get("overlaps") if isinstance(ai.get("overlaps"), dict) else None
    ov = {"id": ov["id"], "name": ids[ov["id"]].get("name", ""), "why": str(ov.get("why") or "")[:300]} if ov and ov.get("id") in ids else None
    name = re.sub(r"\s+", " ", str(ai.get("name") or "")).strip()[:60]
    one = re.sub(r"\s+", " ", str(ai.get("one_line") or "")).strip()[:300]
    if not name or not one or not ex:
        return None
    return {"grammar": True, "id": rid, "family": fam, "name": name, "one_line": one,
            "formula": str(ai.get("formula") or "").strip()[:200], "examples": ex, "why": str(ai.get("why") or "").strip()[:300],
            "overlaps": ov}


# One bare model call, not a Claude Code session: no project files, no tools, no MCP servers, a one-line system prompt, run
# outside the repo. Measured 2026-10-12: the default `claude -p` carried ~68K tokens of session context ($0.55-0.64 a read);
# lean, a test call cost $0.007.
import tempfile  # noqa: E402
LEAN_DIR = os.path.join(tempfile.gettempdir(), "anees-tutor-grammar")


ARG_MAX = 8000           # a longer prompt (a lesson transcript, AM-32) goes on stdin: Windows caps a command line at 32,767 chars


def lean_cmd(prompt, model=MODEL, effort=None):
    """The lean command; a prompt longer than ARG_MAX is left out of it (claude_read sends it on stdin)."""
    os.makedirs(LEAN_DIR, exist_ok=True)
    mcp = os.path.join(LEAN_DIR, "no-mcp.json")
    if not os.path.exists(mcp):
        with open(mcp, "w", encoding="utf-8") as f:
            f.write('{"mcpServers": {}}')
    return [CLAUDE, "-p"] + ([prompt] if len(prompt) <= ARG_MAX else []) + ["--output-format", "json", "--model", model, "--system-prompt", "You answer with one JSON object and nothing else.",
            "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--mcp-config", mcp] + (["--effort", effort] if effort else [])


def claude_read(prompt, runner=None, log=print, spend=None, sid="", step="tutor_grammar.propose", prompt_file="scripts/tutor_grammar_prompt.md",
                lesson_date=None, what=None, model=MODEL, effort=None):
    """ONE Claude read through `claude -p` (scripts/track.py logs model, tokens, cost; the cost goes to data/budget.json
    'anthropic'). runner(prompt) -> stdout is injectable for tests. Returns (parsed JSON or None, cost_usd)."""
    import track
    cmd = lean_cmd(prompt, model, effort)
    with open(os.path.join(REPO, prompt_file), encoding="utf-8") as f:
        template = f.read()
    with track.run(step, lesson_date, kind="inference", provider="anthropic", request_model=model,
                   prompt_file=prompt_file, prompt_sha=track.sha256_text(template),
                   params={"sid": sid, "prompt_arg_sha": track.sha256_text(prompt)}) as run:
        try:
            if runner:
                stdout = runner(prompt)
            else:
                r = subprocess.run(cmd, cwd=LEAN_DIR, capture_output=True, text=True, encoding="utf-8", timeout=420,
                                   input=None if len(prompt) <= ARG_MAX else prompt,
                                   env={**os.environ, "DISABLE_PROMPT_CACHING": "1"})     # a one-off read: writing a cache costs 1.25x
                stdout = r.stdout
                if r.returncode:
                    run.set(status="error", error_type="exit_%d" % r.returncode)
                    log("tutor_grammar: claude exit %d: %s" % (r.returncode, (r.stderr or "")[-200:]))
                    return None, None
        except Exception as e:  # noqa: BLE001
            run.set(status="error", error_type=type(e).__name__)
            log("tutor_grammar: claude failed: %s" % type(e).__name__)
            return None, None
        parsed = track.parse_claude_output(stdout)
        run.claude(parsed)
        cost = parsed.get("cost_usd")
        if cost is not None:
            try:
                if spend is None:
                    import pipeline_ext as PE
                    spend = PE.spend
                spend("anthropic", float(cost), what or "tutor-grammar proposal %s (%s)" % (sid[:8], model))
            except Exception:  # noqa: BLE001
                pass
        m = re.search(r"\{[\s\S]*\}", parsed.get("text") or "")
        try:
            return (json.loads(m.group(0)) if m else None), cost
        except ValueError:
            run.set(status="empty_output")
            return None, cost


def propose(rows, store, buckets, taken, runner=None, log=print, spend=None, now=None, limit=MAX_PER_RUN):
    """Every submission that needs one gets a new proposal version in the store (in place). Returns the sids done."""
    now = now or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    store.setdefault("subs", {})
    store.setdefault("ids_given", [])
    done = []
    for sid, sub in sorted(reduce_rows(rows, store.get("heard")).items(), key=lambda kv: str(kv[1].get("at"))):
        versions = store["subs"].get(sid, [])
        if len(done) >= limit or not needs_proposal(sub, versions):
            continue
        prev = current(versions)
        asked = (answer_for(sub, versions) or {}).get("what") if prev else None
        ai, cost = claude_read(fill(sub, buckets, asked, prev), runner=runner, log=log, spend=spend, sid=sid)
        p = clean(ai, sub, buckets, taken | set(store["ids_given"]), prev if prev and prev.get("grammar") else None)
        if not p:
            log("tutor_grammar: no usable proposal for %s (kept waiting; retried next run)" % sid)
            continue
        p.update({"v": (prev["v"] + 1) if prev else 1, "made_at": now, "model": MODEL, "cost_usd": cost, "asked": asked})
        if p.get("id") and p["id"] not in store["ids_given"]:
            store["ids_given"].append(p["id"])
        store["subs"].setdefault(sid, []).append(p)
        done.append(sid)
    return done


# ------------------------------------------------------------------ AM-32: grammar Claude heard her teach in a lesson
HEARD_PROMPT_REL = os.path.join("scripts", "tutor_grammar_heard_prompt.md")
# Measured 2026-10-12: the whole transcript is ~31K tokens; one read cost $0.30 on Sonnet 5.5 (10-09) and $0.34 on Haiku
# 5.5 (10-08: 10K thinking tokens). So the read keeps Sonnet, sends only the lesson window, runs at low effort and with
# no prompt cache; the input (~30K tokens) is the floor, so a read costs about $0.15 (10-10: $0.145), not the $0.05 of a short AM-31 read.
HEAR_MODEL = os.environ.get("ANEES_HEAR_MODEL") or MODEL
MAX_HEARD = 5            # cards from one lesson, at most
HEAR_TRIES = 3           # a lesson whose read fails this often is not read again by `pull` (cost cap; `hear <date>` still can)
NEAR_S = 30              # a GR-18 proposal this close (same lesson) is the same moment
QUOTE_WINDOW_S = 20      # her quote must be on her line within this many seconds of the time the AI gave
BEFORE_S = 90            # the student's line before hers, at most this long before


def mmss(sec):
    t = int(round(float(sec))); h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)


def secs(t):
    try:
        parts = [float(x) for x in str(t or "").strip().split(":")]
    except ValueError:
        return None
    if not parts or len(parts) > 3:
        return None
    v = 0.0
    for x in parts:
        v = v * 60 + x
    return v


def lesson_turns(date, repo=REPO):
    return (J(P(repo, os.path.join("docs", "data", "lessons", date + ".json")), {}) or {}).get("turns", [])


def in_lesson(turns, lesson_type=None):
    """TR-05: from her first word to her last, without the off-lesson stretches the lesson-type read named (less to read,
    nothing off-lesson heard as teaching)."""
    hers = [float(x["t"]) for x in turns if is_tutor(x)]
    if not hers:
        return []
    off = [(secs(o.get("from")), secs(o.get("to"))) for o in (lesson_type or {}).get("off_lesson") or []]
    off = [(a, b) for a, b in off if a is not None and b is not None]
    return [x for x in turns if min(hers) <= float(x["t"]) <= max(hers) and not any(a <= float(x["t"]) <= b for a, b in off)]


def transcript(date, turns):
    """The same text the lesson readers read (scripts/review_lesson.py transcript_text)."""
    lines = ["# Lesson %s - %d turns on the lesson clock (mm:ss = seconds on the page audio)" % (date, len(turns)), ""]
    for t in turns:
        tag = ("CHAT %s" % (t.get("typed_by") or "")).strip() if t["who"] == "chat" else t["who"]
        lines.append("[%s] %s: %s" % (mmss(t["t"]), tag, t["text"]))
    return "\n".join(lines) + "\n"


def _norm(s):
    s = re.sub(r"[ً-ْـ]", "", str(s or "").lower())                 # harakat, tatweel
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return " ".join(re.findall(r"[0-9a-zء-ي]+", s))


def is_tutor(turn):
    return turn.get("who") == "Amal" or (turn.get("who") == "chat" and str(turn.get("typed_by") or "").lower().startswith("amal"))


def place_quote(turns, t, quote):
    """Her line that holds the quote, nearest the AI's time (within QUOTE_WINDOW_S), or None: the quote is never trusted."""
    q, at = _norm(quote), secs(t)
    if len(q) < 3 or at is None:
        return None
    hits = [x for x in turns if is_tutor(x) and abs(float(x["t"]) - at) <= QUOTE_WINDOW_S and q in _norm(x["text"])]
    return min(hits, key=lambda x: abs(float(x["t"]) - at)) if hits else None


def line_before(turns, her):
    prev = [x for x in turns if x.get("who") == "Medi" and float(her["t"]) - BEFORE_S <= float(x["t"]) < float(her["t"])]
    return prev[-1] if prev else None


def her_words_near(turns, her, span=120):
    return " ".join(x["text"] for x in turns if is_tutor(x) and abs(float(x["t"]) - float(her["t"])) <= span)[:1500]


def gr18_moments(repo=REPO):
    """(date, seconds) of every GR-18 proposal moment: grammar-proposals.json moments + proposed-buckets.json rows."""
    out = []
    for rel, key in ((os.path.join("docs", "data", "grammar-proposals.json"), "moments"),
                     (os.path.join("data", "lesson-work", "full-audit", "proposed-buckets.json"), "rows")):
        for p in (J(P(repo, rel), {}) or {}).get("proposals", []):
            for m in p.get(key) or []:
                for k in ("t", "t_amal"):
                    s = secs(m.get(k))
                    if m.get("date") and s is not None:
                        out.append((m["date"], s))
    return out


def known_names(repo, store, buckets):
    """Normalised names of every rule, GR-18 proposal and tutor-grammar card so far (a finding with one of them is not new)."""
    names = {b.get("name") for b in buckets}
    for rel in (os.path.join("docs", "data", "grammar-proposals.json"), os.path.join("data", "lesson-work", "full-audit", "proposed-buckets.json")):
        names |= {p.get("name") for p in (J(P(repo, rel), {}) or {}).get("proposals", [])}
    for vs in (store.get("subs") or {}).values():
        names |= {v.get("name") for v in vs}
    return {_norm(n) for n in names if n}


def heard_prompt(date, text, buckets, repo, store):
    with open(P(repo, HEARD_PROMPT_REL), encoding="utf-8") as f:
        tpl = f.read()
    rules = "\n".join("- %s %s: %s" % (b["id"], b.get("name", ""), str(b.get("one_line") or "").replace("`", "")) for b in buckets if b.get("family") in FAMILIES)
    props = []
    for rel in (os.path.join("docs", "data", "grammar-proposals.json"), os.path.join("data", "lesson-work", "full-audit", "proposed-buckets.json")):
        props += ["- %s %s: %s" % (p.get("id"), p.get("name"), p.get("proposed_rule") or "") for p in (J(P(repo, rel), {}) or {}).get("proposals", [])]
    for vs in (store.get("subs") or {}).values():
        c = current(vs)
        if c and c.get("grammar"):
            props.append("- %s %s: %s" % (c.get("id"), c.get("name"), c.get("one_line")))
    lt = J(P(repo, os.path.join("data", "lesson-work", "lesson-types", date + ".json")), {}) or {}
    hint = "\n".join("- %s (%s)" % (r.get("title"), r.get("pattern") or "") for r in ((lt.get("summary") or {}).get("rules") or []))
    return (tpl.replace("{rules}", rules).replace("{proposed}", "\n".join(dict.fromkeys(props)) or "(none)")
            .replace("{taught}", hint or "(none)").replace("{max}", str(MAX_HEARD)).replace("{transcript}", text))


def pending_lessons(repo, store):
    """Reviewed lessons (a lesson-type read exists) on/after TUTOR_FROM (AM-28) never read here, oldest first."""
    import glob
    import tutor_scope
    runs = store.get("heard_runs") or {}
    out = []
    for p in sorted(glob.glob(P(repo, os.path.join("data", "lesson-work", "lesson-types", "20??-??-??.json")))):
        d = os.path.basename(p)[:10]
        r = runs.get(d) or {}
        if tutor_scope.in_scope(d) and not r.get("done") and int(r.get("tries") or 0) < HEAR_TRIES and os.path.exists(P(repo, os.path.join("docs", "data", "lessons", d + ".json"))):
            out.append(d)
    return out


def hear(date, store, repo=REPO, runner=None, log=print, spend=None, now=None, force=False):
    """AM-32: ONE Claude read of the lesson transcript -> new cards on her 'Add grammar' list (in the store, in place).
    Returns {"date", "kept": [sid], "dropped": [{name, why}], "cost_usd"} or None when the lesson needs no read."""
    import tutor_scope
    now = now or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    store.setdefault("subs", {}); store.setdefault("ids_given", []); store.setdefault("heard", {}); store.setdefault("heard_runs", {})
    run = store["heard_runs"].get(date) or {}
    if not tutor_scope.in_scope(date) or (run.get("done") and not force):
        return None
    turns = in_lesson(lesson_turns(date, repo), J(P(repo, os.path.join("data", "lesson-work", "lesson-types", date + ".json")), {}) or {})
    if not turns:
        log("tutor_grammar hear: no transcript for %s" % date)
        return None
    buckets = (J(P(repo, os.path.join("docs", "data", "grammar-buckets.json")), {}) or {}).get("buckets", [])
    text = transcript(date, turns)
    run = {"tries": int(run.get("tries") or 0) + 1, "at": now, "model": HEAR_MODEL}
    store["heard_runs"][date] = run
    ai, cost = claude_read(heard_prompt(date, text, buckets, repo, store), runner=runner, log=log, spend=spend, sid="heard-" + date,
                           step="tutor_grammar.hear", prompt_file=HEARD_PROMPT_REL.replace(os.sep, "/"), lesson_date=date,
                           what="tutor-grammar heard %s (%s)" % (date, HEAR_MODEL), model=HEAR_MODEL, effort="low")
    run["cost_usd"] = cost
    found = ai.get("found") if isinstance(ai, dict) else None
    if not isinstance(found, list):
        run["error"] = "no usable answer"
        log("tutor_grammar hear: no usable answer for %s (try %d of %d)" % (date, run["tries"], HEAR_TRIES))
        return {"date": date, "kept": [], "dropped": [], "cost_usd": cost}
    near = [s for d, s in gr18_moments(repo) if d == date]
    names = known_names(repo, store, buckets)
    taken = taken_ids(repo, store)
    kept, dropped = [], []
    for f in found[:MAX_HEARD * 2]:
        if not isinstance(f, dict):
            continue
        name = str(f.get("name") or "")
        her = place_quote(turns, f.get("t"), f.get("quote"))
        why = None
        if not her:
            why = "her quote is not on her line at that time"
        elif any(abs(float(her["t"]) - s) <= NEAR_S for s in near):
            why = "a GR-18 proposal already has this moment"
        elif _norm(name) in names:
            why = "a rule or proposal with this name exists"
        elif any(h.get("date") == date and abs(float(h.get("sec") or 0) - float(her["t"])) <= NEAR_S for h in store["heard"].values()):
            why = "already heard at this moment"
        elif len(kept) >= MAX_HEARD:
            why = "more than %d in one lesson" % MAX_HEARD
        if why:
            dropped.append({"t": f.get("t"), "name": name[:60], "why": why})
            continue
        before = line_before(turns, her)
        h = {"date": date, "t": mmss(her["t"]), "sec": float(her["t"]), "quote": str(f.get("quote")).strip()[:400],
             "line": her["text"][:600], "before": before["text"][:600] if before else "", "hers": her_words_near(turns, her), "at": now}
        sid = "heard-%s-%s" % (date.replace("-", ""), re.sub(r"\D", "", h["t"]))
        while sid in store["heard"] or sid in store["subs"]:
            sid += "b"
        p = clean(f, heard_sub(sid, h), buckets, taken | set(store["ids_given"]))
        if not p or not p.get("grammar"):
            dropped.append({"t": f.get("t"), "name": name[:60], "why": "not a usable rule card"})
            continue
        p.update({"v": 1, "made_at": now, "model": HEAR_MODEL, "cost_usd": None, "asked": None, "heard_run": date})
        store["heard"][sid] = h
        store["ids_given"].append(p["id"])
        store["subs"][sid] = [p]
        names.add(_norm(p["name"]))
        kept.append(sid)
    run.update({"done": True, "found": len(found), "kept": kept, "dropped": dropped})
    run.pop("error", None)
    log("tutor_grammar hear %s: %d found, %d new cards (%s), %d dropped" % (date, len(found), len(kept), ", ".join(store["subs"][s][0]["id"] for s in kept) or "-", len(dropped)))
    return {"date": date, "kept": kept, "dropped": dropped, "cost_usd": cost}


def load_store(repo=REPO):
    return J(P(repo, STORE_REL), None) or {"rule": "AM-31", "about": "Every proposal version Claude made (paid output, never rebuilt) and every rule id ever handed out.",
                                           "subs": {}, "ids_given": []}


def hear_and_save(date, repo=REPO, runner=None, log=print, spend=None, force=False):
    """scripts/review_lesson.py's step: hear one lesson, save the store, rebuild the page file. Never raises."""
    try:
        store = load_store(repo)
        res = hear(date, store, repo, runner=runner, log=log, spend=spend, force=force)
        if res is not None:
            W(P(repo, STORE_REL), store)
            build(repo)
        return res
    except Exception as e:  # noqa: BLE001
        log("tutor_grammar hear %s failed: %s: %s" % (date, type(e).__name__, e))
        return None


# ------------------------------------------------------------------ approved rules -> buckets
def approved(rows, store):
    """[(sub, proposal, yes_answer)] for every rule she said 'Yes, add it' to (on the version she saw), oldest first."""
    out = []
    for sid, sub in reduce_rows(rows, (store or {}).get("heard")).items():
        versions = (store or {}).get("subs", {}).get(sid, [])
        if state(sub, versions) == "added":
            out.append((sub, current(versions), answer_for(sub, versions)))
    return sorted(out, key=lambda x: str(x[2].get("at")))


def bucket_row(sub, p, yes):
    """The grammar-buckets.json row of one approved rule (same fields as the rest; examples are [arabizi, english] pairs,
    an example not from her marked 'spelling unverified' - S1)."""
    day = str(yes.get("at") or "")[:10]
    ex = [[e["arabizi"] or e["arabic"], (e["english"] or "") + ("" if e["hers"] else " (example by Claude, spelling unverified)")] for e in p["examples"]]
    more = []
    if p.get("formula"):
        more.append("Formula: " + p["formula"])
    if sub.get("heard"):
        h = sub["heard"]
        more.append("Claude heard the tutor teach it in the %s lesson at %s: «%s» (AM-32)" % (h.get("date"), h.get("t"), (h.get("quote") or "")[:400]))
    else:
        more.append("The tutor wrote it: «%s»%s (Tutor)" % (sub["text"][:400], (" - her example: " + sub["example"]) if sub.get("example") else ""))
    if p.get("overlaps"):
        more.append("Close to %s %s: %s" % (p["overlaps"]["id"], p["overlaps"]["name"], p["overlaps"]["why"]))
    more.append("Added by the tutor on the Tutor page %s (AM-31). No automatic detection yet: counted only from the readers and "
                "the tutor's and the student's notes until a person adds a detector." % day)
    return {"id": p["id"], "family": p["family"], "name": p["name"], "one_line": p["one_line"], "examples": ex,
            "why": p.get("why") or "", "more": more, "tally_rule": None, "formula": p.get("formula") or "",
            "added_by": "tutor", "added_on": day, "detector": None, "tutor_sid": sub["sid"],
            **({"heard_in": {"date": sub["heard"].get("date"), "t": sub["heard"].get("t")}} if sub.get("heard") else {})}


def approved_buckets(repo=REPO):
    """What scripts/build_grammar_buckets.py appends: the approved rules from the mirror + the store (no network)."""
    rows = J(P(repo, ROWS_REL), {}) or {}
    store = J(P(repo, STORE_REL), {}) or {}
    return [bucket_row(s, p, y) for s, p, y in approved(rows.get("rows", []), store)]


# ------------------------------------------------------------------ the page file
def page(rows, store, now=None):
    """docs/data/tutor-grammar.json: one item per submission (newest first) with every proposal version + her rows (the
    page also reads her rows live; this mirror covers rows written with an older link token)."""
    subs = reduce_rows(rows, (store or {}).get("heard"))
    items = []
    for sid, sub in subs.items():
        versions = (store or {}).get("subs", {}).get(sid, [])
        it = {"sid": sid, "text": sub["text"], "example": sub["example"], "at": sub["at"], "state": state(sub, versions), "versions": versions}
        if sub.get("heard"):
            it["heard"], it["example"] = sub["heard"], ""
        items.append(it)
    items.sort(key=lambda x: str(x["at"]), reverse=True)
    mirror = [{k: r.get(k) for k in ("id", "created_at", "kind", "word_key", "payload")} for r in sorted(rows or [], key=_order)
              if r.get("source", SOURCE) == SOURCE and sid_of(r.get("word_key"))[0]]
    n = sum(1 for x in items if x["state"] == "proposed")
    return {"rule": "AM-31", "updated": now or dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "about": "Grammar the tutor added on her Tutor page: her words, Claude's rewrite as a rule with a letter-number, and her "
                     "answer. Only her 'Yes, add it' adds the rule (scripts/tutor_grammar.py).",
            "waiting_for_tutor": n, "items": items, "rows": mirror}


def build(repo=REPO, now=None):
    rows = (J(P(repo, ROWS_REL), {}) or {}).get("rows", [])
    store = J(P(repo, STORE_REL), {"subs": {}, "ids_given": []})
    out = page(rows, store, now)
    W(P(repo, PAGE_REL), out)
    return out


def pull(repo=REPO, fetch=None, runner=None, log=print, spend=None, hear_limit=1):
    """Her rows -> the mirror; proposals for what needs one; AM-32: at most hear_limit reviewed lessons not read yet (a
    read that failed is retried, HEAR_TRIES at most); the page file. Fail-open on the network (the mirror stands)."""
    try:
        if fetch is None:
            import db
            fetch = lambda: db.select("amal_rules", {"select": "id,created_at,source,kind,word_key,payload", "source": "eq." + SOURCE,  # noqa: E731
                                                     "order": "id.asc"}, undo=False)
        rows = [r for r in (fetch() or []) if r.get("source", SOURCE) == SOURCE]
        W(P(repo, ROWS_REL), {"rule": "AM-31", "about": "Read-only mirror of the tutor's 'Add grammar' rows (amal_rules source tutor_grammar).",
                              "rows": [{k: r.get(k) for k in ("id", "created_at", "source", "kind", "word_key", "payload")} for r in rows]})
    except Exception as e:  # noqa: BLE001
        log("tutor_grammar: amal_rules not reachable (%s); the mirror stands" % type(e).__name__)
        rows = (J(P(repo, ROWS_REL), {}) or {}).get("rows", [])
    store = load_store(repo)
    buckets = (J(P(repo, os.path.join("docs", "data", "grammar-buckets.json")), {}) or {}).get("buckets", [])
    done = propose(rows, store, buckets, taken_ids(repo, store), runner=runner, log=log, spend=spend)
    heard = []
    for d in pending_lessons(repo, store)[:max(0, hear_limit)]:
        try:
            heard.append(hear(d, store, repo, runner=runner, log=log, spend=spend))
        except Exception as e:  # noqa: BLE001
            log("tutor_grammar hear %s failed: %s" % (d, type(e).__name__))
    if done or heard or not os.path.exists(P(repo, STORE_REL)):
        W(P(repo, STORE_REL), store)
    out = build(repo)
    return {"rows": len(rows), "proposed": done, "heard": [h for h in heard if h], "waiting_for_tutor": out["waiting_for_tutor"],
            "approved": [b["id"] for b in approved_buckets(repo)]}


def check(repo=REPO):
    """Problems (empty = OK): the page file lists what the mirror + store say; every approved rule is a bucket."""
    probs = []
    rows = (J(P(repo, ROWS_REL), {}) or {}).get("rows", [])
    store = J(P(repo, STORE_REL), {"subs": {}, "ids_given": []})
    want = page(rows, store, now="x")
    have = J(P(repo, PAGE_REL), None)
    if rows and (not have or [(i["sid"], i["state"], len(i["versions"])) for i in have.get("items", [])] !=
                 [(i["sid"], i["state"], len(i["versions"])) for i in want["items"]]):
        probs.append("docs/data/tutor-grammar.json is older than its rows: run `python scripts/tutor_grammar.py build`")
    ids = {b["id"] for b in (J(P(repo, os.path.join("docs", "data", "grammar-buckets.json")), {}) or {}).get("buckets", [])}
    miss = [b["id"] for b in approved_buckets(repo) if b["id"] not in ids]
    if miss:
        probs.append("approved by the tutor but not a bucket yet: %s (run `python scripts/build_grammar_buckets.py`)" % ", ".join(miss))
    return probs


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pull", "build", "check", "hear"])
    ap.add_argument("date", nargs="?", help="hear: the lesson date (default: every reviewed lesson not read yet)")
    ap.add_argument("--force", action="store_true", help="hear: read the lesson again even if it was read (one more paid call)")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.cmd == "hear":
        dates = [a.date] if a.date else pending_lessons(REPO, load_store())
        print(json.dumps([hear_and_save(d, force=a.force) for d in dates], ensure_ascii=False))
        return 0
    if a.cmd == "pull":
        print(json.dumps(pull(), ensure_ascii=False))
        return 0
    if a.cmd == "build":
        out = build()
        print("wrote %s: %d submissions, %d waiting for the tutor" % (PAGE_REL, len(out["items"]), out["waiting_for_tutor"]))
        return 0
    probs = check()
    print("\n".join(probs) if probs else "tutor grammar OK")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
