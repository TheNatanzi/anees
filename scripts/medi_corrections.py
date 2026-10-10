# -*- coding: utf-8 -*-
"""Medi's corrections on the Lessons page transcript (PR-15, Medi 2026-10-02: "i am going to make some corrections to the
transcript. try and make rule and patterns with my corrections."; 2026-10-03: "do a hand off chip where I can make all
the corrections. Have it make rules for every correction if possible").

    python scripts/medi_corrections.py pull        # table -> data/lesson-work/medi-corrections.json, then propose (never fails)
    python scripts/medi_corrections.py propose     # patterns -> docs/data/correction-proposals.json + correction-rules.json
    python scripts/medi_corrections.py register    # his yes -> rules/registry.json entry + generated guard test + rule book
    python scripts/medi_corrections.py show        # the effective corrections, one line each

The page (docs/js/transcript-corrections.js) writes one row per correction (migration 022, append-only; Undo = a new row
with `undoes`). The effective set (rows not undone) enters UPSTREAM of every page, where the other human rulings enter:
  text / speaker / time / missing        transcript_fixes.load()  -> page turns + lesson_turns (TR-18 overlay)
  not-slip / was-wrong / classify / add  apply_rows() in full_audit_build.py  -> the reader rows every page reads
  not-use                                use_rulings() in detect_grammar_usage.load_rulings()
Target = the producer id on the chip (reader row FA-uid, Word Bank event, use bucket+t) with a fingerprint fallback
(date, time, wrong piece, kind class); a correction that matches nothing is ORPHANED: listed, never a failed build.

Precedence (council 2): Amal on Arabic correctness, Medi on everything else.
  - "My Arabic was right" (reason 'right') is Amal's: a card on her Tutor hub ('ledger:MC-<id>', LS-12); the slip keeps
    counting until she taps. A voiced recast is her answer already (the card says so); a row she ruled is never changed.
  - "Was wrong" / "add" without her voiced fix in the next 15 s = tier B (her review page); with it = tier A (counted).
  - Every other reason (she wasn't correcting, I fixed it first, both fine, I was asking, wrong speaker/time) is his call.
ANEES_CORRECTIONS=off = kill switch.
"""
import hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(REPO, "data", "lesson-work", "medi-corrections.json")
RULES_P = os.path.join(REPO, "data", "lesson-work", "correction-rules.json")
HAND_P = os.path.join(REPO, "data", "lesson-work", "medi-corrections-hand.json")   # his corrections typed in chat, same row shape
QUAR_P = os.path.join(REPO, "data", "lesson-work", "medi-corrections-quarantine.json")
QUEUE_P = os.path.join(REPO, "data", "lesson-work", "code-rule-queue.json")
PROPOSALS_P = os.path.join(REPO, "docs", "data", "correction-proposals.json")
AMAL_P = os.path.join(REPO, "data", "lesson-work", "ledger-amal.json")
GEN_TEST = "tests/test_correction_rules_generated.py"
KINDS = ("text", "speaker", "time", "missing", "not-slip", "was-wrong", "classify", "add", "not-use", "undo", "rule-answer", "note")   # note: PG-37 his words, read later
TEXT_KINDS = ("text", "speaker", "time", "missing")
ROW_KINDS = ("not-slip", "was-wrong", "classify", "add")
REASONS = {   # "Not a mistake" asks why in one tap; only 'right' is Amal's
    "not-correcting": "she wasn't correcting me", "fixed-first": "I fixed it first", "both-fine": "she said both are fine",
    "asking": "I was asking", "wrong-moment": "wrong speaker or time", "right": "my Arabic was right"}
SIGNAL = "medi-correction"
HOLD_OVER = 50          # council 5: more new rows than this in one pull = hold + warning
BURST_S = 600           # PR-19 (Medi 2026-10-09): ...only when they were written inside 10 minutes (a runaway, not a person);
                        # a fresh checkout pulled his 58 rows on 10-08 (54 minutes of typing) at once and held them for good
YES_MAX = 15            # council 3: "Make it a rule" is disabled when it would change more than this
VOICED = {"recast", "explicit-no", "prompt-then-fix", "named-rule", "finished-sentence"}


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def off():
    return os.environ.get("ANEES_CORRECTIONS", "").lower() == "off"


def sec(s):
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return float(s)
    try:
        p = [float(x) for x in str(s).split(":")]
    except ValueError:
        return None
    return p[-1] + 60 * p[-2] + (3600 * p[0] if len(p) == 3 else 0) if len(p) > 1 else p[0]


def mmss(t):
    t = int(t or 0)
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def h(obj):
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:10]


# ------------------------------------------------------------------ the log
def all_rows(path=OUT, hand=HAND_P):
    """The table mirror plus the corrections he gave in chat (hand file, same row shape, by: 'medi (chat)')."""
    return ((J(path) or {}).get("rows") or []) + (((J(hand) or {}).get("rows") or []) if hand else [])


def effective(rows=None):
    """Rows not undone, oldest first (ts, then created_at); an undo of an undo puts the row back."""
    rows = all_rows() if rows is None else rows
    rows = sorted(rows, key=lambda r: (str(r.get("ts")), str(r.get("created_at") or ""), r["id"]))
    undone = set()
    for r in rows:
        if r.get("kind") == "undo" and r.get("undoes"):
            if r["undoes"] in undone:
                undone.discard(r["undoes"])
            else:
                undone.add(r["undoes"])
    live_undo = {r["id"] for r in rows if r.get("kind") == "undo"} - undone
    gone = {r["undoes"] for r in rows if r.get("kind") == "undo" and r["id"] in live_undo}
    return [r for r in rows if r.get("kind") != "undo" and r["id"] not in gone]


def lesson_dates(repo=REPO):
    d = os.path.join(repo, "docs", "data", "lessons")
    return {f[:10] for f in os.listdir(d)} if os.path.isdir(d) else set()


def bad_row(r, dates):
    """Why a pulled row cannot be used (quarantined, shown, never applied) - or None."""
    if not isinstance(r, dict) or not isinstance(r.get("id"), str):
        return "no id"
    if r.get("kind") not in KINDS:
        return "unknown kind %r" % r.get("kind")
    if r.get("kind") == "undo":
        return None if r.get("undoes") else "undo without undoes"
    if r.get("kind") == "rule-answer":
        return None if r.get("proposal") and r.get("answer") in ("yes", "one") else "rule answer without proposal/answer"
    if str(r.get("lesson_date")) not in dates:
        return "unknown lesson %s" % r.get("lesson_date")
    if sec(r.get("turn_t")) is None:
        return "no line time"
    return None


def _ts(r):
    import datetime as _dt
    try:
        return _dt.datetime.fromisoformat(str(r.get("ts") or r.get("created_at")).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def human_paced(rows, burst_s=None):
    """PR-19: True when the rows were written over BURST_S seconds or more (a person typing), False for a burst or no times."""
    t = [x for x in (_ts(r) for r in rows) if x is not None]
    return bool(t) and (max(t) - min(t)) >= (BURST_S if burst_s is None else burst_s)


def _span_txt(rows):
    t = [x for x in (_ts(r) for r in rows) if x is not None]
    return "%d min" % round((max(t) - min(t)) / 60) if t else "?"


def pull(path=OUT, fetch=None, dates=None, quar=QUAR_P, log=print):
    """Mirror the table. Fail-open (council 5): a missing table, a network error or bad rows never stop a run - the last
    mirror is kept. Bad rows and a too-big batch go to the quarantine file. -> {"status": ok|missing|unreachable|held, ...}"""
    try:
        if fetch is None:
            import pull_decisions as PD
            fetch = lambda: PD.http_fetch("transcript_corrections", order="ts.asc,id.asc")  # noqa: E731
        rows = fetch()
    except Exception as e:  # noqa: BLE001 - fail open by design
        log("transcript_corrections: not reachable (%s); keeping the last mirror" % type(e).__name__)
        return {"status": "unreachable", "why": "%s: %s" % (type(e).__name__, str(e)[:120])}
    if rows is None:
        log("transcript_corrections: table not set up (404); keeping the last mirror")
        return {"status": "missing"}
    dates = lesson_dates() if dates is None else dates
    old = {r["id"]: r for r in all_rows(path, hand=None)}
    Q = J(quar) or {"rows": []}
    qids = {x["row"].get("id") for x in Q["rows"] if isinstance(x.get("row"), dict)}
    # a row already quarantined or held is not 'new' again: a bad batch can never block later real corrections
    # (Codex audit 2026-10-03); ANEES_CORRECTIONS_BULK_OK=1 releases the held ones after a look
    bulk_ok = os.environ.get("ANEES_CORRECTIONS_BULK_OK") == "1"
    held_ids = {x["row"].get("id") for x in Q["rows"] if str(x.get("why", "")).startswith("held") and isinstance(x.get("row"), dict)}
    new = [r for r in rows if isinstance(r, dict) and r.get("id") not in old and (r.get("id") not in qids or (bulk_ok and r.get("id") in held_ids))]
    # PR-19: rows held earlier are looked at again every pull; written at a person's pace (over BURST_S or more) they are
    # his real corrections and go in - the hold only ever stops a burst
    reheld = [r for r in rows if isinstance(r, dict) and r.get("id") in held_ids and r.get("id") not in old]
    release = set() if bulk_ok else ({r["id"] for r in reheld} if human_paced(reheld) else set())
    if bulk_ok and held_ids:
        Q["rows"] = [x for x in Q["rows"] if not str(x.get("why", "")).startswith("held")]
        qids -= held_ids
    elif release:
        Q["rows"] = [x for x in Q["rows"] if not (isinstance(x.get("row"), dict) and x["row"].get("id") in release)]
        qids -= release
        new += [r for r in reheld if r["id"] in release]
        W(quar, dict(Q, about="Rows of transcript_corrections that were not applied (bad shape, unknown lesson, or held). Generated by scripts/medi_corrections.py pull."))
        log("transcript_corrections: released %d held rows (written over %s - a person, not a burst; PR-19)" % (len(release), _span_txt(reheld)))
    out = {"status": "ok", "new": 0, "quarantined": 0}
    if release:
        out["released"] = len(release)
    fresh = [r for r in new if r.get("id") not in release]
    if len(fresh) > HOLD_OVER and not bulk_ok and not human_paced(fresh):
        for r in fresh:
            if r.get("id") not in qids:
                Q["rows"].append({"row": r, "why": "held: %d new rows in one pull (more than %d) written within %d min; set ANEES_CORRECTIONS_BULK_OK=1 after a look" % (len(fresh), HOLD_OVER, BURST_S // 60)})
        W(quar, dict(Q, about="Rows of transcript_corrections that were not applied (bad shape, unknown lesson, or held). Generated by scripts/medi_corrections.py pull."))
        log("transcript_corrections: HELD %d new rows (more than %d in one pull, a burst) - warning, not applied" % (len(fresh), HOLD_OVER))
        if not release:
            return {"status": "held", "new": len(fresh)}
        new = [r for r in new if r.get("id") in release]
    for r in new:
        why = bad_row(r, dates)
        if why:
            if r.get("id") not in qids:
                Q["rows"].append({"row": r, "why": why})
            out["quarantined"] += 1
            continue
        old[r["id"]] = r
        out["new"] += 1
    W(path, {"about": "Mirror of Supabase transcript_corrections (migration 022): Medi's corrections on the Lessons page "
                      "transcript. Generated by scripts/medi_corrections.py pull; never edited by hand. Undo = a row with "
                      "undoes; the builders apply medi_corrections.effective().",
             "rows": sorted(old.values(), key=lambda r: (str(r.get("ts")), r["id"]))})
    if out["quarantined"] or not os.path.exists(quar):
        W(quar, dict(Q, about="Rows of transcript_corrections that were not applied (bad shape, unknown lesson, or held). Generated by scripts/medi_corrections.py pull."))
    return out


# ------------------------------------------------------------------ lessons (turns) for context checks
_TURNS = {}


def turns_of(date, repo=REPO):
    k = (repo, str(date))
    if k not in _TURNS:
        _TURNS[k] = (J(os.path.join(repo, "docs", "data", "lessons", str(date) + ".json")) or {}).get("turns") or []
    return _TURNS[k]


def _lessons(repo=REPO):
    for d in sorted(lesson_dates(repo)):
        yield d, turns_of(d, repo)


# ------------------------------------------------------------------ entry points for the builders
def text_rows(rows=None):
    """Heard-word overlay rows (transcript_fixes.json shape) from his text / speaker / time / missing corrections."""
    if off():
        return []
    out = []
    for r in effective(rows):
        if r.get("kind") not in TEXT_KINDS:
            continue
        p = r.get("payload") or {}
        base = {"date": str(r["lesson_date"]), "t": float(r["turn_t"]), "who": r["turn_who"], "rule": "PR-15", "by": "medi",
                "on": str(r.get("ts"))[:10], "quote": r.get("note"), "correction": r["id"], **({"ai": True} if p.get("from") == "ai" else {})}
        if r["kind"] == "text" and p.get("from") == "ai" and not ai_text_ok(p):
            continue                # TR-30: the note reader's row would undo the second listen or put Latin on an Arabic line
        if r["kind"] == "text" and p.get("engine_wrote") and p.get("heard") is not None:
            out.append(dict(base, engine_wrote=p["engine_wrote"], heard=p["heard"], turn_end=p.get("turn_end"),
                            **({"word_key": p["word_key"]} if p.get("word_key") else {}),     # WS-29: which Doc row he said
                            **({"credit": p["credit"]} if p.get("credit") else {})))         # WS-29: his own ruling on the credit
        elif r["kind"] == "missing" and p.get("heard"):
            out.append(dict(base, engine_wrote="", heard=p["heard"], insert_after=p.get("after") or ""))
        elif r["kind"] == "speaker" and p.get("who") in ("Medi", "Amal"):
            out.append(dict(base, engine_wrote="", heard="", set_who=p["who"]))
        elif r["kind"] == "time" and isinstance(p.get("t"), (int, float)):
            out.append(dict(base, engine_wrote="", heard="", set_t=float(p["t"])))
    return out


def ai_text_ok(p):
    """TR-30 (2026-10-10 audit of 10-08, Medi's notes read by the note reader): a heard-word row the NOTE READER made from
    his words lands only when it changes something real. Not applied: (1) a row whose heard = engine_wrote - it changes no
    word but 'confirms' the engine, so the second listen's better line is dropped (10-08 47:16 'bara' stayed Latin over the
    re-heard برّا, 08:36 'اليوم talvez' over اليوم بلبس); (2) Latin letters or his * written onto a line in Arabic script
    (16 rows: 43:04 'bye7re2*', 32:23 '8eir 3an el* aaa'): the page shows Arabic as Arabic (S1) - the agent re-writes them in
    her letters (medi-corrections-hand.json). His own typed rows (from 'typed' / the page boxes) are never filtered."""
    ew, hd = str(p.get("engine_wrote") or ""), str(p.get("heard") or "")
    if hd.strip(" .،,؟?!") == ew.strip(" .،,؟?!") and not (p.get("word_key") or p.get("credit")):
        return False
    if "*" in hd or (re.search(r"[A-Za-z]", hd) and re.search(r"[؀-ۿ]", str(p.get("line") or "") + ew)):
        return False
    return True


def _class(kind):
    return "grammar" if str(kind or "").startswith("grammar") else "vocab" if str(kind or "").startswith("vocab") else None


def _piece(s):
    return re.sub(r"[\s.…,،؟?!:;\"“”()\-]+", "", str(s or "")).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")


def matches(row, c):
    """Fingerprint fallback: same lesson, his line's time span (+-3 s), same kind class and the same wrong piece or rule."""
    if str(row.get("date")) != str(c["lesson_date"]):
        return False
    tg, p = c.get("target") or {}, c.get("payload") or {}
    t = sec(row.get("t"))
    lo, hi = float(c["turn_t"]) - 3, float(p.get("turn_end") or c["turn_t"]) + 3
    if t is None or not (lo <= t <= hi):
        return False
    if tg.get("k") and _class(row.get("kind")) != tg["k"] and row.get("kind") != "rejected":
        return False
    w = _piece(tg.get("wrong") or tg.get("said"))
    rw = _piece(row.get("wrong"))
    if w and rw and (rw in w or w in rw):
        return True
    return bool(tg.get("rule")) and row.get("bucket") == tg.get("rule")


def find(rows, c, uid_of=None, include_rejected=False):
    """-> (rows, how): the producer id first (council 1), else the fingerprint. full_audit_build applies corrections
    before assign_uids(), so a duplicate's suffixed uid (FA-...x) is its base uid plus its place among the rows sharing
    that base, in display order (Codex audit 2026-10-03). The fingerprint fallback changes ONE row only: when it matches
    several, the correction is orphaned ('re-check this one') instead of changing them all."""
    src = str((c.get("target") or {}).get("src") or "")
    pool = [r for r in rows if include_rejected or r.get("kind") != "rejected"]
    if src.startswith("FA-"):
        base, nth = src.rstrip("x"), len(src) - len(src.rstrip("x"))
        same = [r for r in pool if (r.get("uid") or "").rstrip("x") == base or (uid_of and uid_of(r) == base)]
        if any(r.get("uid") == src for r in same):
            return [r for r in same if r.get("uid") == src], "producer"
        same.sort(key=lambda r: (str(r.get("date")), sec(r.get("t")) if sec(r.get("t")) is not None else 1e9))
        if nth < len(same):
            return [same[nth]], "producer"
    hit = [r for r in pool if matches(r, c)]
    if len(hit) > 1:
        return [], "ambiguous"
    return hit, ("fingerprint" if hit else None)


def amal_voiced(c, right, repo=REPO, turns=None):
    """Her voiced fix: an Amal line within 15 s after his line that says the right word (council 2: then tier A), or says
    it in English (PG-22: payload.right_en, 10-02 09:41 'لازم you should take.' for his laazem 3utle)."""
    R = _piece(right)
    en = str((c.get("payload") or {}).get("right_en") or "").strip().lower()
    if len(R) < 2 and not en:
        return False
    t0 = float(c["turn_t"])
    for u in turns if turns is not None else turns_of(c["lesson_date"], repo):
        if u.get("who") != "Amal" or not (t0 <= float(u.get("t") or 0) <= t0 + 15):
            continue
        txt = _piece(u.get("text"))
        # her fix may be only the corrected word (10-02 45:05 'عشر' for his 'عشرة دقايق'): the words of the right form that
        # differ from his wrong form count too
        his = [_piece(x) for x in _words((c.get("payload") or {}).get("wrong") or (c.get("target") or {}).get("said"))]
        diff = [_piece(w) for w in _words(right) if _piece(w) and _piece(w) not in his]
        if (len(R) >= 2 and R in txt) or any(len(d) >= 2 and d in txt for d in diff) or (en and re.search(r"\b%s\b" % re.escape(en), (u.get("text") or "").lower())):
            return True
    return False


def amal_answers(path=AMAL_P):
    """Her taps on 'ledger:MC-<correction id>' cards (LS-12, written by apply_amal_audit_rulings.py)."""
    return {r["conflict"]: r for r in (J(path) or {}).get("rulings") or [] if str(r.get("conflict", "")).startswith("MC-")}


def _reject(r, why, rule):
    if r.get("kind") == "rejected":
        return
    r["kind_before_rejection"] = r["kind"]
    r.update(kind="rejected", rejected_why=why, rejected_rule=rule)


def apply_rows(rows, corrections=None, quote_date=None, uid_of=None, turns=None, answers=None, rules=None):
    """full_audit_build: his not-slip / was-wrong / classify / add, then his standing rules (MC-nnn), on the reader rows.
    Returns {"applied", "orphaned", "unmatched" (= orphaned), "waiting_for_amal", "tier_b", "standing"}. Nothing is
    deleted: a dropped row keeps its data with kind 'rejected' and his words."""
    rep = {"applied": [], "orphaned": [], "unmatched": [], "waiting_for_amal": [], "tier_b": [], "standing": {}}
    if off():
        return rep
    answers = amal_answers() if answers is None else answers
    for c in effective(corrections):
        k = c.get("kind")
        if k not in ROW_KINDS:
            continue
        p, tg = c.get("payload") or {}, c.get("target") or {}
        who = "Medi %s" % str(c.get("ts"))[:10]
        words = (": " + c["note"]) if c.get("note") else ""
        reason = p.get("reason")
        if k == "not-slip":
            hit, how = find(rows, c, uid_of)
            if not hit:
                rep["orphaned"].append(c["id"])
                continue
            for r in hit:
                voiced = r.get("signal") in VOICED
                if reason == "right" or r.get("signal") == "amal-ruling":
                    a = answers.get("MC-" + c["id"])
                    if reason == "right" and a and a.get("answer") == "right":
                        r.setdefault("medi_corrections", []).append(c["id"])
                        _reject(r, "Amal %s: he was right (Medi asked: my Arabic was right%s)" % (str(a.get("at"))[:10], words), "PR-15")
                        rep["waiting_for_amal"].append({"correction": c["id"], "row": r.get("uid") or r.get("id"), "kind": k,
                                                        "date": str(c["lesson_date"]), "t": float(c["turn_t"]), "said": r.get("wrong"),
                                                        "right": r.get("right"), "line": r.get("medi_said"), "voiced": voiced,
                                                        "note": c.get("note"), "answered": a})
                        continue
                    rep["waiting_for_amal"].append({"correction": c["id"], "row": r.get("uid") or r.get("id"), "kind": k,
                                                    "date": str(c["lesson_date"]), "t": float(c["turn_t"]), "said": r.get("wrong"),
                                                    "right": r.get("right"), "line": r.get("medi_said"), "voiced": voiced,
                                                    "amal_ruled": r.get("signal") == "amal-ruling", "note": c.get("note"),
                                                    "answered": a})
                    continue
                r.setdefault("medi_corrections", []).append(c["id"])
                _reject(r, "%s: not a mistake - %s%s" % (who, REASONS.get(reason, "not a mistake"), words), "PR-15")
            rep["applied"].append(c["id"])
            continue
        if k == "classify":
            hit, how = find(rows, c, uid_of)
            if not hit:
                rep["orphaned"].append(c["id"])
                continue
            for r in hit:
                if r.get("signal") == "amal-ruling":
                    rep["waiting_for_amal"].append({"correction": c["id"], "row": r.get("uid") or r.get("id"), "kind": k})
                    continue
                r.setdefault("medi_corrections", []).append(c["id"])
                _refile(r, p, "%s: %s%s" % (who, "a wrong word" if p.get("to") == "vocab" else "grammar " + str(p.get("rule")), words))
            rep["applied"].append(c["id"])
            continue
        # was-wrong / add: a row the readers dropped comes back, else a new row; tier by her voiced fix
        right = p.get("right") or ""
        if k == "was-wrong":
            hit, how = find([r for r in rows if r.get("kind") == "rejected"], c, uid_of, include_rejected=True)
            if hit:
                for r in hit:
                    voiced = r.get("signal") in VOICED or amal_voiced(c, right or r.get("right"), turns=turns)
                    r.setdefault("medi_corrections", []).append(c["id"])
                    was = r.get("kind_before_rejection") or "vocab-A"
                    r.update(kind=was if voiced else ("grammar-B" if was.startswith("grammar") else "vocab-B"),
                             confidence="high" if voiced else "medium", signal=r.get("signal") or SIGNAL)
                    r["why"] = "%s: it was a mistake%s. %s" % (who, words, r.get("why") or "")
                    r.pop("rejected_why", None)
                    if not voiced:
                        rep["tier_b"].append(c["id"])
                rep["applied"].append(c["id"])
                continue
        g = (p.get("k") or tg.get("k")) == "grammar"
        voiced = amal_voiced(c, right, turns=turns)
        new = {"id": "MC-" + c["id"][:8], "date": str(c["lesson_date"]), "t": mmss(c["turn_t"]), "t_amal": p.get("t_amal"),
               "medi_said": p.get("line"), "amal_said": p.get("amal_said"),
               "wrong": p.get("wrong") or tg.get("word") or tg.get("said"), "right": right,
               "kind": ("grammar" if voiced else "grammar-B") if g else ("vocab-A" if voiced else "vocab-B"),
               "bucket": (p.get("rule") or tg.get("rule")) if g else None, "tier": None if g else 1, "mode": "speaking",
               "signal": "recast" if voiced else SIGNAL, "confidence": "high" if voiced else "medium", "source": "audit-2026-09-26",
               "added_by": "medi-correction",
               "correction": c["id"], "agreed_by": "medi-correction",
               "why": "%s marked it a mistake%s%s" % (who, words, "" if voiced else " (Amal did not voice a fix: on her review page, tier B)")}
        rows.append(new)
        if not voiced:
            rep["tier_b"].append(c["id"])
        rep["applied"].append(c["id"])
    rep["standing"] = apply_standing(rows, rules)
    rep["unmatched"] = rep["orphaned"]
    return rep


def _refile(r, p, why):
    r["kind_before_medi"], r["bucket_before_medi"] = r.get("kind"), r.get("bucket")
    if p.get("to") == "vocab":
        r.update(kind="vocab-A" if r.get("kind") in ("grammar", "vocab-A") else "vocab-B", bucket=None)
    else:
        r.update(kind="grammar" if r.get("kind") in ("grammar", "vocab-A") else "grammar-B", bucket=p.get("rule"))
    if p.get("wrong"):
        r["wrong_before_medi"], r["wrong"] = r.get("wrong"), p["wrong"]
    if p.get("right"):
        r["right_before_medi"], r["right"] = r.get("right"), p["right"]
    r["why"] = "%s. Readers wrote: %s" % (why, r.get("why"))


def use_rulings(corrections=None, rules=None):
    """detect_grammar_usage.load_rulings: his 'not a use' on a ✓ grammar chip -> a ruled-out use row; his standing
    not-use rules (MC-nnn) -> a pattern row (any lesson, that rule + that word)."""
    if off():
        return []
    out = []
    for c in effective(corrections):
        if c.get("kind") != "not-use":
            continue
        tg = c.get("target") or {}
        out.append({"date": str(c["lesson_date"]), "t": float(c["turn_t"]), "bucket": tg.get("rule"), "hit": tg.get("said"),
                    "why": "Medi %s: not a use%s" % (str(c.get("ts"))[:10], (": " + c["note"]) if c.get("note") else ""),
                    "ruling_by": "medi-correction", "by": "medi-correction", "rule": "PR-15", "correction": c["id"],
                    "turn_end": (c.get("payload") or {}).get("turn_end")})
    for r in live_rules(rules):
        if r["kind"] == "not-use":
            out.append({"pattern": True, "bucket": r["pattern"]["rule"], "hit": r["pattern"]["hit"], "date": None, "t": None,
                        "why": "Medi's rule %s: %s" % (r["id"], r["plain"]), "ruling_by": "medi-correction", "by": "medi-correction", "rule": r["id"]})
    return out


# ------------------------------------------------------------------ patterns -> proposed rules (S6, council 3)
def _words(s):
    return [w for w in re.split(r"[\s.…,،؟?!:;\"“”()]+", str(s or "")) if w]


def _ctx(line, X):
    """The 3-word context of X in a line: (word before, X, word after), normalised; None when X is not in it."""
    ws, xs = [_piece(w) for w in _words(line)], [_piece(w) for w in _words(X)]
    for i in range(len(ws) - len(xs) + 1):
        if ws[i:i + len(xs)] == xs:
            return (ws[i - 1] if i else "", " ".join(xs), ws[i + len(xs)] if i + len(xs) < len(ws) else "")
    return None


def audit_rows(repo=REPO):
    A = J(os.path.join(repo, "data", "full-audit-2026-09-26.json")) or {}
    sc = A.get("sweep_compat") or {}
    return (sc.get("rows") or []) + (sc.get("vocab") or [])


def uses(repo=REPO):
    U = J(os.path.join(repo, "docs", "data", "grammar-usage.json")) or {}
    out = []
    for b, us in ((U.get("uses") or U.get("by_bucket") or {}).items() if isinstance(U.get("uses") or U.get("by_bucket"), dict) else []):
        for u in us:
            out.append(dict(u, bucket=b))
    return out


def _moment(date, t, before, after, amal_ruled=False):
    return {"date": date, "t": t, "mmss": mmss(t), "before": before, "after": after, "amal_ruled": bool(amal_ruled)}


def text_matches(pattern, lessons, skip=None):
    """Every line of that speaker whose engine text has the same 3-word context (council 3: a lone word never spreads)."""
    hits = []
    for d, T in lessons:
        for u in T:
            if u.get("who") != pattern["who"]:
                continue
            src = u.get("engine") or u.get("text") or ""
            if pattern["engine_wrote"] not in src:
                continue
            if _ctx(src, pattern["engine_wrote"]) != tuple(pattern["ctx"]):
                continue
            if skip and d == skip[0] and abs(float(u["t"]) - skip[1]) <= 1:
                continue
            hits.append(_moment(d, float(u["t"]), src, src.replace(pattern["engine_wrote"], pattern["heard"], 1)))
    return hits


def row_matches(pattern, rows, skip=None):
    """Counted reader rows with the same Amal signal + the same wrong piece (+ right piece when the pattern has one)."""
    hits = []
    for r in rows:
        if r.get("kind") == "rejected" or _piece(r.get("wrong")) != _piece(pattern.get("wrong")) or not _piece(r.get("wrong")):
            continue
        if pattern.get("signal") and r.get("signal") != pattern["signal"]:
            continue
        if pattern.get("right") and _piece(r.get("right")) != _piece(pattern["right"]):
            continue
        if pattern.get("not_class") and _class(r.get("kind")) != pattern["not_class"]:
            continue
        t = sec(r.get("t")) or 0
        if skip and (str(r.get("date")) == skip[0] and skip[1] - 4 <= t <= (skip[2] if len(skip) > 2 and skip[2] else skip[1]) + 4
                     or (len(skip) > 3 and skip[3] and r.get("uid") == skip[3])):
            continue                     # the corrected moment itself (his line can span several engine lines)
        after = pattern.get("after_words") or "not counted"
        hits.append(_moment(str(r.get("date")), t, "%s → %s (%s)" % (r.get("wrong"), r.get("right"), r.get("kind")), after,
                            r.get("signal") == "amal-ruling"))
    return hits


def use_matches(pattern, uses_, skip=None):
    hits = []
    for u in uses_:
        if u.get("bucket") != pattern["rule"] or _piece(u.get("hit")) != _piece(pattern["hit"]):
            continue
        if skip and str(u.get("date")) == skip[0] and skip[1] - 3 <= float(u.get("t") or 0) <= skip[2] + 3:
            continue
        hits.append(_moment(str(u.get("date")), float(u.get("t") or 0), "✓ %s use: %s" % (pattern["rule"], u.get("hit")), "not a use"))
    return hits


def propose(corrections=None, repo=REPO, rows=None, uses_=None):
    """One proposal per correction: the general pattern, its plain sentence, every other moment it would change. owner:
    medi = his yes makes it a standing rule; amal = an Arabic question (her Tutor hub); code = a shape (timing, prompts)
    queued for Claude to write a code rule; one-off = no general shape (the reason is shown)."""
    eff = effective(corrections)
    answers = {r.get("proposal"): r for r in eff if r.get("kind") == "rule-answer"}
    lessons = list(_lessons(repo))
    rows = audit_rows(repo) if rows is None else rows
    uses_ = uses(repo) if uses_ is None else uses_
    out = []
    for c in eff:
        k, p, tg = c.get("kind"), c.get("payload") or {}, c.get("target") or {}
        if k in ("rule-answer",):
            continue
        if k == "note":   # PG-37: his words the one box could not shape; scripts/correction_parse.py reads them (never a rule by itself)
            out.append({"id": "P-" + c["id"][:8], "from": c["id"], "kind": k, "date": str(c["lesson_date"]), "t": float(c["turn_t"]), "mmss": mmss(c["turn_t"]),
                        "moments": [], "n": 0, "owner": "one-off",
                        "plain": ("Your words were kept: «%s»" % ((p.get("raw") or c.get("note") or "")[:120]))
                                 + ("" if p.get("parsed_from") else " · Anees reads them within the hour.")})
            continue
        skip = (str(c["lesson_date"]), float(c["turn_t"]), float(p.get("turn_end") or c["turn_t"]), tg.get("src"))
        X = None
        prop = {"id": "P-" + c["id"][:8], "from": c["id"], "kind": k, "date": str(c["lesson_date"]), "t": float(c["turn_t"]),
                "mmss": mmss(c["turn_t"]), "moments": []}
        if k == "text" and p.get("engine_wrote"):
            X, Y = p["engine_wrote"], p["heard"]
            line = p.get("line") or next((u.get("engine") or u.get("text") for u in turns_of(c["lesson_date"], repo)
                                          if u.get("who") == c["turn_who"] and abs(float(u["t"]) - float(c["turn_t"])) <= 1), "") or ""
            ctx = _ctx(line, X)
            if not ctx or (not ctx[0] and not ctx[2] and len(_words(X)) == 1):
                prop.update(owner="one-off", plain="«%s» → «%s» stays just this one: a lone word can be a real word somewhere else." % (X, Y))
            else:
                pat = {"who": c["turn_who"], "engine_wrote": X, "heard": Y, "ctx": list(ctx)}
                prop.update(owner="medi", pattern=pat, moments=text_matches(pat, lessons, skip),
                            plain="When the recording engine writes «%s» on %s line between «%s» and «%s», %s said «%s»." % (
                                X, "your" if c["turn_who"] == "Medi" else "Amal's", ctx[0] or "start", ctx[2] or "end",
                                "you" if c["turn_who"] == "Medi" else "she", Y))
        elif k == "not-slip":
            reason, wrong = p.get("reason"), tg.get("wrong") or tg.get("said")
            sig = tg.get("signal") or p.get("signal")
            if reason == "right":
                pat = {"wrong": wrong}
                prop.update(owner="amal", pattern=pat, moments=row_matches(pat, rows, skip),
                            plain="Was «%s» right? That is Amal's call: it is on her Tutor hub, counted as before until she taps." % wrong)
            elif reason in ("not-correcting", "both-fine") and wrong:
                pat = {"wrong": wrong, "signal": sig if reason == "not-correcting" else None,
                       "right": (tg.get("right") or p.get("right")) if reason == "both-fine" else None, "after_words": "not a mistake"}
                prop.update(owner="medi", pattern=pat, moments=row_matches(pat, rows, skip),
                            plain=("When Amal %s after «%s», she is not correcting you." % (tg.get("sig") or sig or "reacts", wrong)) if reason == "not-correcting"
                            else "«%s» and «%s» are both fine (Amal said so): never a mistake." % (wrong, tg.get("right") or p.get("right")))
            elif reason in ("fixed-first", "asking"):
                prop.update(owner="code", pattern={"reason": reason, "signal": sig},
                            plain=("Shape: you fixed it yourself before Amal (%s). Claude writes this as a code rule, like GR-24." % (tg.get("sig") or sig))
                            if reason == "fixed-first" else "Shape: you were asking Amal, not trying (%s). Claude writes this as a code rule, like GR-25." % (tg.get("sig") or sig))
            else:
                prop.update(owner="one-off", plain="Wrong speaker or time: fixed on this line only.")
        elif k in ("add", "was-wrong") and (p.get("wrong") or tg.get("said") or tg.get("word")):
            Wd = p.get("wrong") or tg.get("said") or tg.get("word")
            hits = [_moment(d, float(u["t"]), u["text"], "ask Amal") for d, T in lessons for u in T
                    if u.get("who") == "Medi" and _piece(Wd) and _piece(Wd) in _piece(u.get("text"))
                    and not (d == skip[0] and abs(float(u["t"]) - skip[1]) <= 1)]
            prop.update(owner="amal", pattern={"wrong": Wd, "right": p.get("right")}, moments=hits,
                        plain="You said «%s»%s on other days too. Whether it was wrong is Amal's call: it goes to her Tutor hub." % (
                            Wd, (" for «%s»" % p["right"]) if p.get("right") else ""))
        elif k == "not-use" and tg.get("rule") and tg.get("said"):
            pat = {"rule": tg["rule"], "hit": tg["said"]}
            prop.update(owner="medi", pattern=pat, moments=use_matches(pat, uses_, skip),
                        plain="«%s» is not a use of %s%s." % (tg["said"], tg["rule"], (" " + tg["name"]) if tg.get("name") else ""))
        elif k == "classify" and (tg.get("wrong") or tg.get("said")):
            pat = {"wrong": tg.get("wrong") or tg.get("said"), "right": p.get("right"), "to": p.get("to"), "rule": p.get("rule"),
                   "not_class": tg.get("k"), "after_words": "grammar " + str(p.get("rule")) if p.get("to") == "grammar" else "a wrong word"}
            prop.update(owner="medi", pattern=pat, moments=row_matches(pat, rows, skip),
                        plain="«%s» → «%s» is %s, not %s." % (p.get("wrong") or pat["wrong"], pat["right"] or "?", pat["after_words"], "a wrong word" if tg.get("k") == "vocab" else "grammar"))
        elif k in ("speaker", "time"):
            prop.update(owner="code", pattern={"kind": k},
                        plain="Shape: the engine put this line on the wrong %s. Claude looks for the cause and writes a code rule." % ("speaker" if k == "speaker" else "time"))
        else:
            prop.update(owner="one-off", plain="Fixed on this line only (no general shape).")
        prop["hash"] = h(prop.get("pattern") or prop["plain"])
        prop["n"] = len(prop["moments"])
        prop["first"] = prop["moments"][:3]
        touches_amal = any(m.get("amal_ruled") for m in prop["moments"])
        prop["can_yes"] = prop["owner"] == "medi" and prop["n"] <= YES_MAX and not touches_amal
        if prop["owner"] == "medi" and not prop["can_yes"]:
            prop["why_not"] = ("it would change %d moments (more than %d): too many to trust from one correction" % (prop["n"], YES_MAX)
                               if prop["n"] > YES_MAX else "one of the moments is one Amal ruled herself")
        a = answers.get(prop["id"])
        if a:
            ok = (a.get("payload") or {}).get("hash") == prop["hash"]
            prop["answer"] = {"answer": a.get("answer"), "at": a.get("ts"), "note": a.get("note"), "valid": ok,
                              **({} if ok else {"why": "the pattern changed since the answer; ask again"})}
        out.append(prop)
    return out


def live_rules(rules=None):
    R = (J(RULES_P) or {}).get("rules") or [] if rules is None else rules
    return [r for r in R if not r.get("paused") and not r.get("withdrawn")]


def apply_standing(rows, rules=None):
    """His standing rules (yes) on the reader rows: not-slip / both-fine -> rejected with the rule id; classify -> re-filed.
    -> {rule id: rows changed}."""
    if off():
        return {}
    done = {}
    for R in live_rules(rules):
        k, pat = R["kind"], R["pattern"]
        if k not in ("not-slip", "classify"):
            continue
        n = 0
        for r in rows:
            if r.get("kind") == "rejected" or r.get("signal") == "amal-ruling" or not _piece(r.get("wrong")):
                continue
            if _piece(r.get("wrong")) != _piece(pat.get("wrong")):
                continue
            if pat.get("signal") and r.get("signal") != pat["signal"]:
                continue
            if pat.get("right") and _piece(r.get("right")) != _piece(pat["right"]):
                continue
            if k == "classify":
                if pat.get("not_class") and _class(r.get("kind")) != pat["not_class"]:
                    continue
                _refile(r, pat, "Medi's rule %s: %s" % (R["id"], R["plain"]))
            else:
                _reject(r, "Medi's rule %s: %s" % (R["id"], R["plain"]), R["id"])
            r.setdefault("medi_rules", []).append(R["id"])
            n += 1
        done[R["id"]] = n
    return done


def rule_text_rows(rules=None):
    """Standing text rules: every line of that speaker with the same 3-word context reads Y, in every lesson."""
    if off():
        return []
    return [{"pattern": True, "who": r["pattern"]["who"], "engine_wrote": r["pattern"]["engine_wrote"], "heard": r["pattern"]["heard"],
             "ctx": r["pattern"]["ctx"], "rule": r["id"], "by": "medi"} for r in live_rules(rules) if r.get("kind") == "text"]


def would_change(rule, repo=REPO, rows=None, uses_=None):
    """Probation count: how many moments the rule touches across every lesson right now."""
    pat, k = rule["pattern"], rule["kind"]
    if k == "text":
        return len(text_matches(pat, list(_lessons(repo))))
    if k == "not-use":
        return len(use_matches(pat, uses(repo) if uses_ is None else uses_))
    return len(row_matches(pat, audit_rows(repo) if rows is None else rows))


def write_proposals(repo=REPO, corrections=None):
    """docs/data/correction-proposals.json (the page reads it), data/lesson-work/correction-rules.json (his valid yes ->
    MC-nnn, ids stable, on probation) and data/lesson-work/code-rule-queue.json (shapes for Claude)."""
    P = propose(corrections, repo=repo)
    pp = os.path.join(repo, "docs", "data", "correction-proposals.json")
    rp = os.path.join(repo, "data", "lesson-work", "correction-rules.json")
    qp = os.path.join(repo, "data", "lesson-work", "code-rule-queue.json")
    old = (J(rp) or {}).get("rules") or []
    by_prop = {r["proposal"]: r for r in old}
    rules = [dict(r) for r in old]
    eff = {r["id"]: r for r in effective(corrections)}
    nxt = max([int(r["id"][3:]) for r in old] + [0]) + 1
    for x in P:
        a = x.get("answer") or {}
        yes = x["owner"] == "medi" and a.get("answer") == "yes" and a.get("valid") and x["can_yes"]
        r = by_prop.get(x["id"])
        if r is None and yes:
            src = eff.get(x["from"]) or {}
            r = {"id": "MC-%03d" % nxt, "proposal": x["id"], "hash": x["hash"], "from": x["from"], "kind": x["kind"], "plain": x["plain"],
                 "pattern": x["pattern"], "n_at_yes": x["n"], "on": str(a.get("at"))[:10],
                 "quote": " · ".join(q for q in (src.get("note"), a.get("note"), "Make it a rule: yes") if q),
                 "example": {"date": x["date"], "t": x["mmss"], "before_after": x["first"][:1]}}
            nxt += 1
            rules.append(r)
        elif r is not None:
            r = next(y for y in rules if y["proposal"] == x["id"])
            if not yes and not a:
                r["withdrawn"] = True          # his yes was undone: the rule stops; its registry entry stays (ratchet)
            elif yes:
                r.pop("withdrawn", None)
    for r in rules:
        if r.get("withdrawn"):
            continue
        n = would_change(r, repo)
        limit = 2 * max(int(r.get("n_at_yes") or 0), 1)
        r["would_change"] = n
        r["paused"] = n > limit
        if r["paused"]:
            r["paused_why"] = "probation: a run would change %d moments, more than 2 x %d at his yes" % (n, r.get("n_at_yes") or 0)
        x = next((p for p in P if p["id"] == r["proposal"]), None)
        if x:
            x["rule"] = r["id"]
    W(pp, {"about": "Rules proposed from Medi's transcript corrections (PR-15, scripts/medi_corrections.py propose). owner medi = "
                    "his yes makes a standing rule (MC-nnn); amal = an Arabic question for her Tutor hub; code = a shape Claude "
                    "writes as a code rule; one-off = no general shape.", "proposals": P})
    W(rp, {"about": "Medi's yes to a proposed rule (PR-15): pattern + his words, applied to every lesson (future ones too) by "
                    "transcript_fixes.load / medi_corrections.apply_rows / use_rulings. On probation: paused when a run would "
                    "change more than 2 x the moments at his yes. Generated from his answers; ids never reused.", "rules": rules})
    queue = [{"proposal": x["id"], "date": x["date"], "mmss": x["mmss"], "plain": x["plain"], "pattern": x.get("pattern"),
              "asked": bool((x.get("answer") or {}).get("answer") == "yes")} for x in P if x["owner"] == "code"]
    W(qp, {"about": "Shapes from Medi's corrections (timing, prompts, speaker/time) for Claude to write as code rules (like "
                    "GR-24/25/26). Generated by scripts/medi_corrections.py propose; asked = he tapped 'Ask Claude'.", "queue": queue})
    return P, rules


def amal_cards(rep, repo=REPO):
    """LS-12 cards for his 'my Arabic was right' (council 2). id 'ledger:MC-<correction>'; her tap 'right' drops the slip."""
    out = []
    for w in rep.get("waiting_for_amal") or []:
        if w.get("kind") != "not-slip" or not w.get("date"):
            continue
        t = float(w["t"])
        a, b = max(0, int(t) - 4), int(t) + 14
        T = turns_of(w["date"], repo)
        amal = next((u.get("text") for u in T if u.get("who") == "Amal" and t <= float(u["t"]) <= t + 30), None)
        out.append({"id": "ledger:MC-" + w["correction"], "conflict": "MC-" + w["correction"], "date": w["date"], "t": t, "mmss": mmss(t),
                    "audio": "lessons/%s/audio/lesson.mp3#t=%d,%d" % (w["date"], a, b), "medi_said": w.get("line"), "amal_said": amal,
                    "question": "Medi thinks his Arabic was right here: «%s»%s. Was it wrong?%s" % (
                        w.get("said") or "", (" (the app counts «%s»)" % w["right"]) if w.get("right") else "",
                        " You said it the other way in the lesson; that counts as wrong unless you tap 'He was right'." if w.get("voiced") else ""),
                    "options": [{"value": "wrong", "label": "It was wrong"}, {"value": "right", "label": "He was right"}],
                    **({"answered": {"kind": "ledger_pick", "answer": w["answered"]["answer"], "at": w["answered"].get("at")}} if w.get("answered") else {})})
    return out


# ------------------------------------------------------------------ his yes -> registry entry + guard test + rule book
def _scope(rule):
    if rule["kind"] == "text":
        return "TR", "data"
    if rule["kind"] == "not-use":
        return "GR", "not-error"
    if rule["kind"] == "classify":
        return "GR", "error"
    return ("GR" if (rule["pattern"].get("not_class") == "grammar") else "WS"), "not-error"


def register(repo=REPO, run_book=True, log=print):
    """Every standing rule without a registry entry gets one (his words, code anchor + a generated test the guard runs
    that names the id; not-error rules also get a READER-BRIEF line), then the rule book is rebuilt. Returns new ids."""
    import rule_registry as RR
    rp = os.path.join(repo, "data", "lesson-work", "correction-rules.json")
    D = J(rp) or {"rules": []}
    todo = [r for r in D["rules"] if not r.get("registry")]
    if not todo:
        return []
    reg_p = os.path.join(repo, "rules", "registry.json")
    reg = J(reg_p)
    used = {x["id"] for x in reg["rules"]}
    brief_p = os.path.join(repo, "data", "lesson-work", "full-audit", "READER-BRIEF.md")
    test_p = os.path.join(repo, GEN_TEST)
    new_ids = []
    for r in todo:
        pre, kind = _scope(r)
        n = 1 + max([int(x.split("-")[1]) for x in used if x.startswith(pre + "-")] + [0])
        rid = "%s-%02d" % (pre, n)
        used.add(rid)
        stmt = ("%s Medi's yes to proposal %s (standing rule %s in data/lesson-work/correction-rules.json) is applied to every "
                "lesson, future ones too, by scripts/medi_corrections.py; on probation: paused when a run would change more "
                "than 2 x %d moments (the count at his yes)." % (r["plain"], r["proposal"], r["id"], r.get("n_at_yes") or 0))
        enf = [{"type": "code", "path": "scripts/medi_corrections.py", "contains": "def apply_standing(rows, rules=None):"},
               {"type": "data", "path": "data/lesson-work/correction-rules.json", "contains": '"id": "%s"' % r["id"]}]
        if kind == "not-error":
            line = "- %s (%s): %s\n" % (r["id"], rid, r["plain"])
            body = open(brief_p, encoding="utf-8").read() if os.path.exists(brief_p) else ""
            if "## Medi's standing rules from his corrections" not in body:
                body += "\n## Medi's standing rules from his corrections (PR-15; NOT errors, applied in code too)\n\n"
            if line not in body:
                body += line
            with open(brief_p, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
            enf.append({"type": "brief", "path": "data/lesson-work/full-audit/READER-BRIEF.md", "contains": "- %s (%s): " % (r["id"], rid)})
        fn = "def test_%s_%s_standing_rule_applies" % (rid.lower().replace("-", "_"), r["id"].lower().replace("-", "_"))
        tb = open(test_p, encoding="utf-8").read() if os.path.exists(test_p) else (
            '# -*- coding: utf-8 -*-\n"""Generated by scripts/medi_corrections.py register: one test per standing rule Medi made from a\n'
            'correction (PR-15). Each names its registry id so rule_registry check can prove it. Fixtures only, no live writes."""\n'
            "import os, sys\n\nsys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), \"scripts\"))\n"
            "import medi_corrections as MC  # noqa: E402\n")
        if fn not in tb:
            tb += "\n\n%s():\n    \"\"\"%s = %s: %s\"\"\"\n    MC.check_standing_rule(%r)\n" % (fn, rid, r["id"], r["plain"].replace('"', "'"), r["id"])
            with open(test_p, "w", encoding="utf-8", newline="\n") as f:
                f.write(tb)
        quote = r.get("quote") or "Make it a rule: yes"
        entry = {"id": rid, "kind": kind, "scope": RR.SCOPES[pre], "status": "enforced", "change": "new", "statement": stmt,
                 "plain": r["plain"], "plain_for": RR.plain_hash(stmt), "topic": "your corrections",
                 "source": [{"by": "medi", "date": r.get("on") or str(r.get("example", {}).get("date")), "quote": quote}],
                 "enforcement": enf, "test": [{"path": GEN_TEST, "contains": fn}],
                 "example": {"date": r["example"]["date"], "t": r["example"]["t"], "note": "his correction %s; rule %s" % (r["from"], r["id"])}}
        reg["rules"].append(entry)
        r["registry"] = rid
        new_ids.append(rid)
    with open(reg_p, "w", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")
    W(rp, D)
    cfg_p = os.path.join(repo, "scripts", "publish_guard_config.json")
    cfg = J(cfg_p)
    cmd = cfg["commands"]["tests_py"]["cmd"]
    if GEN_TEST not in cmd:
        cmd.append(GEN_TEST)
        W(cfg_p, cfg)
    if run_book:
        subprocess.run([sys.executable, os.path.join(repo, "scripts", "build_rule_book.py")], cwd=repo, check=False)
    log("registered:", ", ".join(new_ids))
    return new_ids


def check_standing_rule(mc_id, repo=REPO):
    """The generated guard test: the rule exists, carries his words, and its pattern still does what it says on a
    planted moment (a fixture built from the rule itself - no lesson data needed)."""
    R = next((r for r in (J(os.path.join(repo, "data", "lesson-work", "correction-rules.json")) or {}).get("rules") or [] if r["id"] == mc_id), None)
    assert R is not None, mc_id + " missing from correction-rules.json"
    assert R.get("quote") and R.get("plain") and R.get("pattern"), mc_id + " needs his words, a plain sentence and a pattern"
    if R.get("withdrawn") or R.get("paused"):
        return                                   # stopped by his undo or by probation: shown, never applied
    pat, k = R["pattern"], R["kind"]
    if k == "text":
        import transcript_fixes as TF
        line = " ".join(w for w in (pat["ctx"][0], pat["engine_wrote"], pat["ctx"][2]) if w)
        out = TF.apply("2099-01-01", [{"t": 1.0, "who": pat["who"], "text": line}], [dict(x, date="2099-01-01") for x in rule_text_rows([R])])
        assert pat["heard"] in out[0]["text"] and out[0].get("engine") == line, mc_id + " text rule no longer applies"
    elif k in ("not-slip", "classify"):
        row = {"date": "2099-01-01", "t": "00:01", "kind": "grammar" if pat.get("not_class") == "grammar" else "vocab-A",
               "wrong": pat.get("wrong"), "right": pat.get("right") or "x", "signal": pat.get("signal") or "recast"}
        n = apply_standing([row], [R])
        assert n.get(mc_id) == 1, mc_id + " standing rule no longer applies"
    elif k == "not-use":
        assert any(u.get("pattern") and u["rule"] == mc_id for u in use_rulings([], [R])), mc_id + " not-use rule not emitted"


def check(repo=REPO):
    """Publish guard ADVISORY check (council 5: warnings only, never blocks): orphaned / held / quarantined corrections,
    rules paused by probation, a mirror older than 2 h. -> (ok, detail)."""
    import time
    rep = J(os.path.join(repo, "data", "lesson-work", "medi-corrections-report.json")) or {}
    Q = (J(os.path.join(repo, "data", "lesson-work", "medi-corrections-quarantine.json")) or {}).get("rows") or []
    R = (J(os.path.join(repo, "data", "lesson-work", "correction-rules.json")) or {}).get("rules") or []
    msgs = []
    if rep.get("orphaned"):
        msgs.append("%d correction(s) match nothing (shown 're-check this one'): %s" % (len(rep["orphaned"]), ", ".join(rep["orphaned"][:5])))
    held = [x for x in Q if str(x.get("why", "")).startswith("held")]
    if held:
        msgs.append("%d row(s) HELD (a big batch): look, then ANEES_CORRECTIONS_BULK_OK=1" % len(held))
    if len(Q) - len(held):
        msgs.append("%d row(s) quarantined (bad shape / unknown lesson)" % (len(Q) - len(held)))
    paused = [r["id"] for r in R if r.get("paused")]
    if paused:
        msgs.append("rule(s) paused by probation: " + ", ".join(paused))
    m = os.path.join(repo, "data", "lesson-work", "medi-corrections.json")
    if os.path.exists(m) and time.time() - os.path.getmtime(m) > 2 * 3600 and os.environ.get("ANEES_CORRECTIONS_PULLED") != "skip":
        msgs.append("mirror older than 2 h (run: python scripts/medi_corrections.py pull)")
    return (not msgs), ("; ".join(msgs) or "corrections: none orphaned, none held, no paused rule")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pull", "propose", "register", "show", "check"])
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.cmd == "pull":
        res = pull()
        print("transcript_corrections pull:", json.dumps(res))
        try:   # PG-37: read his free-words notes (one Haiku call each) and mirror the edge function's spend; fail-open
            import correction_parse as CP
            print("correction_parse:", json.dumps(CP.run(), ensure_ascii=False)[:300])
        except Exception as e:  # noqa: BLE001
            print("correction_parse failed (kept going):", type(e).__name__, str(e)[:200])
        try:
            P, R = write_proposals()
            print("%d proposals, %d standing rules" % (len(P), len(R)))
            register()
        except Exception as e:  # noqa: BLE001 - never block a publish (council 5)
            print("propose/register failed (kept the old files):", type(e).__name__, str(e)[:200])
        return 0
    if a.cmd == "propose":
        P, R = write_proposals()
        print("%d proposals, %d standing rules" % (len(P), len(R)))
        return 0
    if a.cmd == "check":
        ok, detail = check()
        print(detail)
        return 0 if ok else 1
    if a.cmd == "register":
        print(register() or "nothing new")
        return 0
    for c in effective():
        print(c["lesson_date"], mmss(c["turn_t"]), c["turn_who"], c["kind"], json.dumps(c.get("payload"), ensure_ascii=False), c.get("note") or "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
