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
until a person adds one. Past lessons are re-scored only on Medi's yes (PR-05). Code never contacts her (AM-01)."""
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


def reduce_rows(rows):
    """Her rows (any order) -> {sid: {sid, text, example, at, withdrawn, answer}}; latest row per key wins (AM-17)."""
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
    rules = "\n".join("- %s %s: %s" % (b["id"], b.get("name", ""), str(b.get("one_line") or "").replace("`", "")) for b in buckets if b.get("family") in FAMILIES)
    ask = ""
    if asked and prev:
        ask = ("\nShe already saw this card and asked for a change. Keep everything she did not ask to change.\n"
               "The card she saw: " + json.dumps({k: prev.get(k) for k in ("family", "name", "one_line", "formula", "examples", "why", "overlaps")}, ensure_ascii=False) +
               "\nWhat she wants changed: " + asked + "\n")
    return (prompt_text().replace("{asked}", ask).replace("{rules}", rules).replace("{text}", sub.get("text") or "")
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


def lean_cmd(prompt):
    os.makedirs(LEAN_DIR, exist_ok=True)
    mcp = os.path.join(LEAN_DIR, "no-mcp.json")
    if not os.path.exists(mcp):
        with open(mcp, "w", encoding="utf-8") as f:
            f.write('{"mcpServers": {}}')
    return [CLAUDE, "-p", prompt, "--output-format", "json", "--model", MODEL, "--system-prompt", "You answer with one JSON object and nothing else.",
            "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--mcp-config", mcp]


def claude_read(prompt, runner=None, log=print, spend=None, sid=""):
    """ONE Claude read through `claude -p` (scripts/track.py logs model, tokens, cost; the cost goes to data/budget.json
    'anthropic'). runner(prompt) -> stdout is injectable for tests. Returns (parsed JSON or None, cost_usd)."""
    import track
    cmd = lean_cmd(prompt)
    with track.run("tutor_grammar.propose", None, kind="inference", provider="anthropic", request_model=MODEL,
                   prompt_file="scripts/tutor_grammar_prompt.md", prompt_sha=track.sha256_text(prompt_text()),
                   params={"sid": sid, "prompt_arg_sha": track.sha256_text(prompt)}) as run:
        try:
            if runner:
                stdout = runner(prompt)
            else:
                r = subprocess.run(cmd, cwd=LEAN_DIR, capture_output=True, text=True, encoding="utf-8", timeout=240)
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
                spend("anthropic", float(cost), "tutor-grammar proposal %s (%s)" % (sid[:8], MODEL))
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
    for sid, sub in sorted(reduce_rows(rows).items(), key=lambda kv: str(kv[1].get("at"))):
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


# ------------------------------------------------------------------ approved rules -> buckets
def approved(rows, store):
    """[(sub, proposal, yes_answer)] for every rule she said 'Yes, add it' to (on the version she saw), oldest first."""
    out = []
    for sid, sub in reduce_rows(rows).items():
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
    more.append("The tutor wrote it: «%s»%s (Tutor)" % (sub["text"][:400], (" - her example: " + sub["example"]) if sub.get("example") else ""))
    if p.get("overlaps"):
        more.append("Close to %s %s: %s" % (p["overlaps"]["id"], p["overlaps"]["name"], p["overlaps"]["why"]))
    more.append("Added by the tutor on the Tutor page %s (AM-31). No automatic detection yet: counted only from the readers and "
                "the tutor's and the student's notes until a person adds a detector." % day)
    return {"id": p["id"], "family": p["family"], "name": p["name"], "one_line": p["one_line"], "examples": ex,
            "why": p.get("why") or "", "more": more, "tally_rule": None, "formula": p.get("formula") or "",
            "added_by": "tutor", "added_on": day, "detector": None, "tutor_sid": sub["sid"]}


def approved_buckets(repo=REPO):
    """What scripts/build_grammar_buckets.py appends: the approved rules from the mirror + the store (no network)."""
    rows = J(P(repo, ROWS_REL), {}) or {}
    store = J(P(repo, STORE_REL), {}) or {}
    return [bucket_row(s, p, y) for s, p, y in approved(rows.get("rows", []), store)]


# ------------------------------------------------------------------ the page file
def page(rows, store, now=None):
    """docs/data/tutor-grammar.json: one item per submission (newest first) with every proposal version + her rows (the
    page also reads her rows live; this mirror covers rows written with an older link token)."""
    subs = reduce_rows(rows)
    items = []
    for sid, sub in subs.items():
        versions = (store or {}).get("subs", {}).get(sid, [])
        items.append({"sid": sid, "text": sub["text"], "example": sub["example"], "at": sub["at"], "state": state(sub, versions),
                      "versions": versions})
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


def pull(repo=REPO, fetch=None, runner=None, log=print, spend=None):
    """Her rows -> the mirror; proposals for what needs one; the page file. Fail-open on the network (the mirror stands)."""
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
    store = J(P(repo, STORE_REL), None) or {"rule": "AM-31", "about": "Every proposal version Claude made (paid output, never rebuilt) and every rule id ever handed out.",
                                             "subs": {}, "ids_given": []}
    buckets = (J(P(repo, os.path.join("docs", "data", "grammar-buckets.json")), {}) or {}).get("buckets", [])
    done = propose(rows, store, buckets, taken_ids(repo, store), runner=runner, log=log, spend=spend)
    if done or not os.path.exists(P(repo, STORE_REL)):
        W(P(repo, STORE_REL), store)
    out = build(repo)
    return {"rows": len(rows), "proposed": done, "waiting_for_tutor": out["waiting_for_tutor"],
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
    ap.add_argument("cmd", choices=["pull", "build", "check"])
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
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
