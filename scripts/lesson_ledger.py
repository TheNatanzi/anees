# -*- coding: utf-8 -*-
"""One lesson ledger: the marked transcript is the one source of every judgment (LS-11).

Medi 2026-10-02: "what is the main source of all of errors on the lessons? I think the transcription page of the lessons
should be no?" - then "yes" to making the marked transcript the ONE source of every judgment.

    python scripts/lesson_ledger.py check        # BLOCK check (publish guard): every page number = a count over the ledger
    python scripts/lesson_ledger.py show DATE    # the lesson's conflicts and counts, one line each

Built by scripts/build_lessons_page_data.py (build_all() below), which already gathers every producer's items:
  word-bank    the Word Bank matcher's scored events (right / partial / wrong)
  readers      the AI readers' slips (data/full-audit-2026-09-26.json sweep_compat; Amal's taps folded in by
               scripts/apply_amal_audit_rulings.py, her notes by scripts/amal_grammar_notes.py)
  use-counter  grammar uses (docs/data/grammar-usage.json; data/grammar-usage-rulings.json)
  sheet        list membership (data/lesson-work/sheet-verdicts.json by hand, else the automatic sheet match)
  type-read    off-lesson stretches (data/lesson-work/lesson-types/<date>.json)
  medi         his answers to needs-Medi moments (data/lesson-work/ledger-rulings.json, hand-made)
Every producer item becomes exactly one mark on one transcript turn (or folded into the mark of the same moment).
Where two producers judged the same moment differently, PRECEDENCE (existing rules only) decides; a moment no rule
decides is a "Medi?" mark + a needs-Medi entry and is counted as before until he answers. Never a silent pick.

Output: data/lesson-work/ledger/<date>.json (generated: rebuilt, never merged, never edited by hand) and the
before -> after table data/lesson-work/ledger/_diff.md. No timestamp inside: a ledger changes only when a judgment does.
"""
import collections, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import transcript_marks as TM  # noqa: E402

LEDGER_DIR = os.path.join(REPO, "data", "lesson-work", "ledger")
RULINGS_P = os.path.join(REPO, "data", "lesson-work", "ledger-rulings.json")
NO_USAGE = {"F1", "F2", "F3"}

PRODUCERS = {
    "word-bank": "Word Bank matcher (scripts/speaking_evidence.py -> docs/data/word-bank-evidence.json + word-bank-review.json)",
    "readers": "AI readers r1/r2/r3 (data/full-audit-2026-09-26.json sweep_compat)",
    "amal-tap": "Amal's tap on her review page (apply_amal_audit_rulings.py, signal amal-ruling)",
    "amal-notes": "Amal's grammar notes (scripts/amal_grammar_notes.py)",
    "use-counter": "grammar use counter (scripts/detect_grammar_usage.py -> docs/data/grammar-usage.json)",
    "use-rulings": "ruled-out / automatic not-a-use rows (data/grammar-usage-rulings.json, detect_grammar_usage.py)",
    "sheet": "list membership (data/lesson-work/sheet-verdicts.json, else the automatic sheet match)",
    "medi": "Medi's answer to a needs-Medi moment (data/lesson-work/ledger-rulings.json)",
}

# The conflict kinds and the existing rule that decides each (design: C:\Claude\reports\anees-one-ledger-design-2026-10-02.md)
PRECEDENCE = {
    "C1": {"rules": ["S3", "WS-07"], "decides": "a Word Bank Correct on the very word Amal flagged (her voiced signal, high-confidence row): "
           "the slip counts; the Word Bank event becomes 'said here, another word intended' (WB rule 5) or 'same attempt, counted once'"},
    "C1p": {"rules": ["WS-07"], "decides": "the slip is a phrase and her fix keeps this word: both stand (WB rule 1, the whole exchange)"},
    "C1a": {"rules": ["WS-07"], "decides": "he asked for another word: asking is not a wrong use of the word he said (WB rule 1)"},
    "C1q": {"rules": [], "decides": None},        # needs Medi: which word of the phrase was wrong
    "C1r": {"rules": ["WS-07"], "decides": "the Word Bank's hand context review of this moment already weighed Amal's fix: its call stands (WB rule 1)"},
    "C2": {"rules": ["WS-06", "WS-09"], "decides": "a wrong-FORM vocab copy of a counted grammar slip on the same word: the grammar slip counts"},
    "C2b": {"rules": ["WS-09"], "decides": "a different word AND a wrong form in one word: two errors, both stand"},
    "C2q": {"rules": [], "decides": None},        # needs Medi: the same fix filed as a word slip and as a grammar slip
    "C2w": {"rules": ["WS-06", "WS-07"], "decides": "a Word Bank Wrong on a counted grammar slip's word: grammar counts (WB rule 7)"},
    "C3": {"rules": ["GR-14"], "decides": "a use and a slip of the same rule on one turn are one attempt, Wrong (build_grammar_console.use_verdict)"},
    "C4": {"rules": [], "decides": "a reader slip and a Word Bank miss on the same word within 5 s are one mark (one judgment = one mark)"},
    "CR": {"rules": [], "decides": None},         # needs Medi: his own Word Bank edit vs the ledger
}
MEDI_ANSWERS = {"C1q": "a word of the phrase = that word was the wrong one; keep = both stand",
                "C2q": "grammar = the grammar slip only; both = both count",
                "CR": "ledger = the ledger's call; keep = his Word Bank edit stands"}


# ------------------------------------------------------------------ small helpers
def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def sha(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read().replace(b"\r\n", b"\n"))     # a git checkout may turn LF into CRLF: same content, same hash
    return h.hexdigest()[:16]


def norm(s):
    return TM.normalise(re.sub(r"[.…,،؟?!:;\"“”()\-]+", " ", s or ""))[0].strip()


def base(t):
    """A token without the 'and' prefix (وعشرين = عشرين) - only that one: ال / ب / ل change the word's grammar."""
    return t[1:] if len(t) > 3 and t.startswith("و") else t


def toks(s):
    return [base(t) for t in norm(s).split() if t]


ENGLISH = re.compile(r"\b(is|the|a|an|of|for|word|forgot|meant|means|said|not|or|and|like|instead)\b", re.I)


def is_gloss(s):
    """A reader's 'wrong' that is a description, not his words ('مغني is song', 'storm (forgot the word)'). His own
    Latin-letter (Arabizi) words are words."""
    s = s or ""
    return bool(re.search(r"[A-Za-z]", s) and re.search(r"[؀-ۿ]", s)) or "(" in s or " = " in s or bool(ENGLISH.search(s))


def strength(m):
    """How strong a reader row's evidence is: Amal's own tap 3, both readers (high) 2, one reader (medium) 1, low 0."""
    if m.get("signal") == "amal-ruling" or m["by"]["producer"] == "amal-tap":
        return 3
    return {"high": 2, "medium": 1}.get(m.get("confidence"), 0)


def hand_patch(review_patches, event_id):
    """A Word Bank review patch that is Medi's own ruling (it names him) is never overridden silently: a conflict with it
    goes to him. The patches carry no author today (1,718 on 2026-10-02, 186 marked auto_rule): they are the Word Bank
    producer's reviewed output, so the ledger treats them as the Word Bank's judgment, not as his ruling."""
    p = review_patches.get(event_id) or {}
    return "medi" in (str(p.get("by") or "") + str((p.get("changes") or {}).get("by") or "")).lower()


SCORE_KEYS = ("observation_only", "scored_in_event", "grammar_only", "classification", "vocab_points", "ignored")


def reviewed(review_patches, event_id):
    """'hand' when a Word Bank context review (word-bank-review.json, not an automatic re-read) already set this event's
    score - it weighed the whole exchange, Amal's fix included (09-23 51:51 tazkara: "the miss was حجز") - 'auto' when an
    automatic patch set it (the ledger's override could not apply under it), else None."""
    ch = (review_patches.get(event_id) or {}).get("changes") or {}
    if not any(k in ch for k in SCORE_KEYS):
        return None
    # a context review (contextual_audit) weighed the whole exchange even when a script ran it (review_new_lessons)
    return "hand" if ch.get("contextual_audit") or not ch.get("auto_rule") else "auto"


def word_core(arabic):
    a = str(arabic or "").split(" = ")[0]
    a = re.sub(r"\([^)]*\)", " ", a)
    return " ".join(re.sub(r"[^؀-ۿ ]", " ", a).split())


def same_word(card, v):
    """C4: is the reader's row v about the same word as the Word Bank miss card (the word he said, or the word Amal gave
    = the card's word, after normalising)? Before 2026-10-02 any miss within 5 s swallowed the row (09-26 10:13 مساعد
    was lost to a لازم miss at 10:09; 7 rows in all)."""
    mine = {norm(card.get("wrong")), norm(card.get("tok"))} | {norm(f) for f in re.split(r"[/،,]", card.get("arabic") or "")}
    mine.discard("")
    theirs = {norm(v.get("wrong")), norm(word_core(v.get("amal_gave"))), norm(v.get("right"))}
    theirs.discard("")
    toks_t = {t for x in theirs for t in x.split()}
    return bool(mine & theirs) or any(m in toks_t for m in mine if " " not in m)


def hid(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]


def mmss(t):
    if t is None:
        return "?"
    t = int(round(t))
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def item_ids(items, prefix, key):
    """Stable producer ids for a list: '<prefix><id>', a repeat of the same id (one Word Bank event scored as two
    attempts: the said and the intended word) gets '#2', '#3'."""
    seen, out = collections.Counter(), []
    for e in items:
        k = str(e.get(key))
        seen[k] += 1
        out.append(prefix + k + ("" if seen[k] == 1 else "#%d" % seen[k]))
    return out


def mode(repo=REPO):
    """'on', or 'shadow' (the kill switch): ANEES_LEDGER=shadow, or "mode": "shadow" in data/lesson-work/ledger-rulings.json."""
    p = os.path.join(repo, "data", "lesson-work", "ledger-rulings.json")
    return os.environ.get("ANEES_LEDGER") or ((J(p) or {}).get("mode") if os.path.exists(p) else None) or "on"


AMAL_P = os.path.join(REPO, "data", "lesson-work", "ledger-amal.json")


def load_rulings(path=RULINGS_P, amal_path=None):
    """{conflict id: ruling}. Medi's answers (ledger-rulings.json, hand-made) and Amal's taps on her Tutor hub
    (ledger-amal.json, pulled from amal_rules by scripts/apply_amal_audit_rulings.py). LS-12 (Medi 2026-10-02 "1-6 put for
    amal on her list"): a question about whether / which Arabic word was wrong is hers - her answer wins over his."""
    R = J(path, {"rulings": []}) or {"rulings": []}
    out = {r["conflict"]: dict(r, by=r.get("by") or "medi") for r in R.get("rulings", []) if r.get("conflict")}
    if amal_path is None:
        amal_path = os.path.join(os.path.dirname(os.path.abspath(path)), "ledger-amal.json")
    A = J(amal_path, {"rulings": []}) or {"rulings": []}
    out.update({r["conflict"]: dict(r, by="amal") for r in A.get("rulings", []) if r.get("conflict") and r.get("answer")})
    return out


# LS-12: who answers an open question. Whether / which Arabic word was wrong is Amal's call (her teaching); only a
# question about the app itself (a process question, none yet) goes to Medi.
ASK = {"C1q": "amal", "C2q": "amal", "CR": "amal"}
AMAL_WORDS = {   # the question and the choices in plain words, for her card (no rule ids, no app words)
    "C1q": "Which of Medi's words was wrong here?",
    "C1q1": "Was «%s» wrong here?",
    "C2q": "Was this the wrong word, or the right word with a grammar mistake?",
    "CR": "Was «%s» wrong here?",
}
LABELS = {"none": "Nothing was wrong", "wrong": "Yes, it was wrong", "ledger": "Yes, it was wrong",
          "word": "Wrong word", "grammar": "Grammar mistake", "both": "Both"}


# ------------------------------------------------------------------ build one lesson
def build(date, detail, uses_by_bucket, buckets, scored_rules, not_taught, ruled_out=(), not_uses=(),
          review_patches=None, rulings=None, resolve=True):
    """detail = the per-lesson dict build_lessons_page_data has assembled (turns, vocab_correct, vocab_errors with the
    readers' rows, not_errors, grammar_errors, grammar_not_counted). Returns (ledger, actions): actions = what the
    builder must apply to its lists and the Word Bank ({'move': [(list, item_id, why, rule)], 'overrides': [...],
    'fold_uses': [...]}). Nothing is applied when resolve is False (ANEES_LEDGER=shadow)."""
    turns = detail["turns"]
    review_patches = review_patches or {}
    rulings = rulings or {}
    marks, by_id = [], {}

    def add(m, needle=None):
        p = TM.place(turns, m["t"], "Medi", needle) if m.get("t") is not None else None
        m["turn"] = p[0] if p else None
        if p and p[1] == "text":
            m["placed"] = "loose"
        assert m["id"] not in by_id, "duplicate producer item " + m["id"]
        marks.append(m)
        by_id[m["id"]] = m
        return m

    # ---------------- vocab
    vc = detail.get("vocab_correct") or []
    for e, pid in zip(vc, item_ids(vc, "wb:", "event_id")):
        add({"id": pid, "kind": "vocab", "verdict": "right" if e["kind"] == "correct" else "partial",
             "t": e["t"], "word_key": e.get("word_key"), "arabic": e.get("arabic"), "tok": e.get("tok") or e.get("arabic"),
             "by": {"producer": "word-bank", "ref": e["event_id"]}}, e.get("arabic"))
    ve = detail.get("vocab_errors") or []
    wb_ids = iter(item_ids([e for e in ve if e.get("source") != "audit-2026-09-26"], "wb:", "event_id"))
    for e in ve:
        if e.get("source") == "audit-2026-09-26":
            v = ("asked" if e["kind"] == "asked" else "wrong") if e.get("on_sheet") is not False else "not-scored"
            m = {"id": "ra:" + e["audit_uid"], "kind": "vocab", "verdict": v, "t": e["t"], "word_key": e.get("sheet_key"),
                 "arabic": e.get("arabic"), "wrong": e.get("wrong"), "fix": e.get("fix"), "tier": e.get("tier"),
                 "signal": e.get("signal"), "confidence": e.get("confidence"), "row_kind": e["kind"],
                 "by": {"producer": "amal-tap" if e.get("signal") == "amal-ruling" else "readers", "ref": e["audit_uid"]}}
            if v == "not-scored":
                m["why"] = "not on her word list (left out of the Words %)"
                m["why_by"] = "sheet"
        else:
            m = {"id": next(wb_ids), "kind": "vocab", "verdict": "wrong" if e["kind"] == "wrong" else "partial",
                 "t": e["t"], "word_key": e.get("word_key"), "arabic": e.get("arabic"), "tok": e.get("wrong"),
                 "wrong": e.get("wrong"), "by": {"producer": "word-bank", "ref": e["event_id"]}}
            if e.get("folded"):
                m["folded"] = [{"id": "ra:" + u, "producer": "readers", "ref": u, "rule": "C4", "why": PRECEDENCE["C4"]["decides"]} for u in e["folded"]]
        add(m, e.get("wrong"))
    for e in detail.get("not_errors") or []:
        ref = e.get("audit_uid") or e.get("event_id")
        pid = e.get("ledger_id") or (("ra:" if e.get("audit_uid") else "wb:") + str(ref))
        if pid in by_id:
            continue
        add({"id": pid, "kind": "vocab", "verdict": "not-scored", "t": e["t"], "word_key": e.get("word_key") or e.get("sheet_key"),
             "arabic": e.get("arabic"), "wrong": e.get("wrong"), "why": e.get("verdict_reason") or "dropped on the hand check",
             "why_by": e.get("ledger_rule") or "sheet",
             "by": {"producer": "readers" if e.get("audit_uid") else "word-bank", "ref": ref}}, e.get("wrong"))

    # ---------------- grammar slips and the rows Amal's notes take out
    slips_by_b = collections.defaultdict(list)
    for g in detail.get("grammar_errors") or []:
        m = add({"id": "rg:" + g["id"], "kind": "grammar", "verdict": "slip", "t": g.get("t"), "bucket": g.get("bucket"),
                 "wrong": g.get("wrong"), "fix": g.get("right"), "signal": g.get("signal"), "confidence": g.get("confidence"),
                 "scored_rule": g.get("bucket") in scored_rules,
                 "by": {"producer": "amal-tap" if g.get("signal") == "amal-ruling" else "readers", "ref": g["id"]}}, g.get("wrong"))
        slips_by_b[g.get("bucket")].append(m)
    for g in detail.get("grammar_not_counted") or []:
        add({"id": "rg:" + g["id"], "kind": "grammar", "verdict": "not-scored", "t": g.get("t"), "bucket": g.get("bucket"),
             "wrong": g.get("wrong"), "why": g.get("not_counted_why") or "taken out by Amal's notes", "why_by": "amal-notes",
             "by": {"producer": "readers", "ref": g["id"]}}, g.get("wrong"))

    # ---------------- grammar uses: the same +-2 s pairing as scripts/grammar_math.py (a paired use is the slip's attempt)
    seen_use = collections.Counter()
    for b, us in sorted(uses_by_bucket.items()):
        if b in NO_USAGE or b not in buckets:
            continue
        mine = [u for u in us if u.get("date") == date]
        if not mine:
            continue
        free = collections.defaultdict(list)
        for u in mine:
            k = ("use", b, round(float(u["t"]), 2) if u.get("t") is not None else None, u.get("hit"))
            seen_use[k] += 1
            u = dict(u, _id="use:%s:%s" % (b, hid(*k, seen_use[k])))
            free[int(u["t"]) if u.get("t") is not None else None].append(u)
        for sm in sorted((s for s in slips_by_b.get(b, []) if s.get("t") is not None), key=lambda s: s["t"], reverse=True):
            for k in (0, -1, 1, -2, 2):
                if free.get(int(sm["t"]) + k):
                    u = free[int(sm["t"]) + k].pop()
                    sm.setdefault("folded", []).append({"id": u["_id"], "producer": "use-counter", "ref": u["_id"], "t": u.get("t"), "hit": u.get("hit"),
                                                        "why": "the use the slip pairs with (+-2 s): one attempt"})
                    break
        for u in sorted((u for v in free.values() for u in v), key=lambda u: (u.get("t") is None, u.get("t") or 0)):
            m = {"id": u["_id"], "kind": "grammar", "t": u.get("t"), "bucket": b, "said": u.get("hit"),
                 "by": {"producer": "use-counter", "ref": u["_id"]}}
            if not_taught(b):
                m.update(verdict="not-scored", why="rule not taught yet (Amal's notes)", why_by="amal-notes")
            else:
                m.update(verdict="use", scored_rule=b in scored_rules)
            add(m, u.get("hit"))
    for r in list(ruled_out) + list(not_uses):
        if r.get("date") != date:
            continue
        k = ("ruled", r.get("bucket"), r.get("t"), r.get("hit") or r.get("said"))
        seen_use[k] += 1
        add({"id": "nu:" + hid(*k, seen_use[k]), "kind": "grammar", "verdict": "not-scored", "t": r.get("t"), "bucket": r.get("bucket"),
             "said": r.get("hit"), "why": r.get("why") or "not a use", "why_by": "use-rulings",
             "by": {"producer": "use-rulings", "ref": r.get("ruling_by") or "automatic"}}, r.get("hit"))

    # ---------------- conflicts: two producers on the same moment
    conflicts, actions = [], {"move": [], "overrides": [], "fold_uses": []}
    # TR-18: a Word Bank score on a word the heard-word overlay says the engine misheard is not his use of that word
    # (10-02 08:39: the engine wrote صرت for his صحيت and the Word Bank credited 'Ana seret' Correct)
    for m in marks:
        if m["by"]["producer"] != "word-bank" or m["turn"] is None or m["verdict"] not in ("right", "partial", "wrong"):
            continue
        H = turns[m["turn"]].get("heard") or []
        tk = norm(m.get("tok"))
        hit = next((h for h in H if tk and norm(h["engine_wrote"]) and (norm(h["engine_wrote"]) == tk or set(norm(h["engine_wrote"]).split()) <= set(tk.split())
                                                                        or tk in norm(h["engine_wrote"]).split())), None)
        if hit and resolve:
            why = "the recording engine wrote %s; you said %s (%s)" % (hit["engine_wrote"], hit["heard"], hit.get("rule") or "TR-18")
            lst = "vocab_correct" if m["verdict"] in ("right", "partial") else "vocab_errors"
            m.update(verdict="not-scored", why=why, why_by="TR-18", was=m["verdict"])
            actions["move"].append((lst, m["id"], why, "TR-18"))
            actions["overrides"].append({"event_id": m["by"]["ref"], "date": date, "mark": m["id"], "was": m["was"],
                                         "changes": {"observation_only": True, "ledger": m["id"], "ledger_reason": why}})
    on_turn = collections.defaultdict(list)
    for m in marks:
        if m["turn"] is not None:
            on_turn[m["turn"]].append(m)

    def conflict(kind, a, b, extra=None):
        cid = "%s-%s" % (kind, hid(date, kind, a["id"], b["id"]))
        c = {"id": cid, "kind": kind, "turn": a["turn"], "t": a["t"], "mmss": mmss(a["t"]), "marks": [a["id"], b["id"]],
             "rules": PRECEDENCE[kind]["rules"], "decides": PRECEDENCE[kind]["decides"], **(extra or {})}
        conflicts.append(c)
        a.setdefault("conflicts", []).append(cid)
        b.setdefault("conflicts", []).append(cid)
        return c

    groups = {}

    def needs_medi(c, options, question, group=None):
        """One question per moment: several Word Bank words under the same flagged phrase share one question (group =
        the reader row), and his answer (keyed by the question's id) settles all of them."""
        if group is not None:
            lead = groups.get(group)
            if lead is None:
                groups[group] = c
            else:
                c["group"] = lead["id"]
                lead["options"] = [o for o in lead["options"] if o != "none"] + [o for o in options if o not in lead["options"] and o != "none"] + ["none"]
                c["options"], c["question"], c["ask"] = lead["options"], question, lead["ask"]
                r = rulings.get(lead["id"])
                if r:
                    c["medi"] = c["ruled"] = {"answer": r["answer"], "by": r.get("by") or "medi", "date": r.get("date") or r.get("at"), "quote": r.get("quote")}
                    return r["answer"]
                c["needs_medi"] = True
                c["counted_as_now"] = lead["counted_as_now"]
                return None
        r = rulings.get(c["id"])
        c["options"], c["question"], c["ask"] = options, question, ASK.get(c["kind"], "medi")
        if r:
            c["medi"] = c["ruled"] = {"answer": r["answer"], "by": r.get("by") or "medi", "date": r.get("date") or r.get("at"), "quote": r.get("quote")}
            return r["answer"]
        c["needs_medi"] = True       # an open question (kept under this name: it is asked of c["ask"])
        c["counted_as_now"] = "both judgments count as before until %s answers" % ("Amal" if c["ask"] == "amal" else "Medi")
        return None

    def drop_slip(r, c, ans):
        """Amal: nothing was wrong here - the reader slip leaves the count (kept, with her answer as the reason)."""
        if r["verdict"] in ("wrong", "asked") and resolve:
            why = "Amal: nothing was wrong here (her answer on the Tutor hub)" if (c.get("ruled") or {}).get("by") == "amal" else "Medi: nothing was wrong here"
            r.update(verdict="not-scored", why=why, why_by=(c.get("ruled") or {}).get("by") or "medi", _was=r["verdict"])
            actions["move"].append(("vocab_errors", r["id"], why, c["kind"]))

    def settle(c):
        """A rule decided it. In shadow mode (ANEES_LEDGER=shadow) nothing is applied, so it is only 'would settle'."""
        if resolve:
            c["resolved"] = True
        else:
            c["would_settle"] = True

    def supersede_wb(m, slip, why, same_key):
        """The Word Bank's right/wrong on this word gives way: folded into the slip's mark; its event is overridden."""
        m["verdict"], m["folded_into"], m["why"] = "folded", slip["id"], why
        slip.setdefault("folded", []).append({"id": m["id"], "producer": "word-bank", "ref": m["by"]["ref"], "was": m.get("_was"), "why": why})
        ch = ({"scored_in_event": True} if same_key else {"observation_only": True})
        actions["overrides"].append({"event_id": m["by"]["ref"], "date": date, "mark": slip["id"], "was": m.get("_was"),
                                     "changes": {**ch, "ledger": slip["id"], "ledger_reason": why}})

    for i, ms in sorted(on_turn.items()):
        wb_ok = [m for m in ms if m["by"]["producer"] == "word-bank" and m["verdict"] in ("right", "partial")]
        wb_bad = [m for m in ms if m["by"]["producer"] == "word-bank" and m["verdict"] == "wrong"]
        rv = [m for m in ms if m["kind"] == "vocab" and m["by"]["producer"] in ("readers", "amal-tap") and m.get("row_kind") in ("wrong", "asked")]
        gs = [m for m in ms if m["kind"] == "grammar" and m["verdict"] == "slip"]
        # C2 / C2b / C2q: a reader vocab slip and a counted grammar slip on the same word (run first: a vocab copy folded
        # into its grammar slip is no longer a word judgment for C1 below)
        for r in rv:
            if r["verdict"] not in ("wrong", "asked"):
                continue
            W = set(toks(r.get("wrong")))
            for g in gs:
                if not W or not (W <= set(toks(g.get("wrong")))):
                    continue
                same_fix = bool(toks(r.get("fix"))) and set(toks(r.get("fix"))) == set(toks(g.get("fix")))
                if not g.get("scored_rule"):
                    conflict("C2b", r, g, {"by": "the grammar slip is in a rule with no use counter: the word slip keeps counting"})
                elif r.get("tier") == 2:
                    c = conflict("C2", r, g, {"by": "wrong form"})
                    if resolve:
                        why = "the same slip is counted as grammar %s (a wrong form is grammar, WS-06)" % g.get("bucket")
                        r.update(verdict="not-scored", folded_into=g["id"], why=why, why_by="C2", _was="wrong")
                        g.setdefault("folded", []).append({"id": r["id"], "producer": r["by"]["producer"], "ref": r["by"]["ref"], "why": why})
                        actions["move"].append(("vocab_errors", r["id"], why, "C2"))
                    settle(c)
                elif not same_fix:
                    conflict("C2b", r, g)          # a different word AND a wrong form: two errors, both stand (WS-09)
                else:
                    c = conflict("C2q", r, g, {"why_medi": "the same fix was filed as a word slip and as a grammar slip"})
                    ans = needs_medi(c, ["word", "grammar", "both"], AMAL_WORDS["C2q"])
                    if ans:
                        c["resolved"] = True
                    if ans == "word" and resolve:
                        why = "%s: the same slip is a wrong word, not grammar %s" % ("Amal" if c["ruled"]["by"] == "amal" else "Medi", g.get("bucket"))
                        g.update(verdict="not-scored", folded_into=r["id"], why=why, why_by="medi", _was="slip")
                        r.setdefault("folded", []).append({"id": g["id"], "producer": g["by"]["producer"], "ref": g["by"]["ref"], "why": why})
                        actions["move"].append(("grammar_errors", g["id"], why, "C2q"))
                    if ans == "grammar" and resolve:
                        why = "%s: the same slip is grammar %s" % ("Amal" if c["ruled"]["by"] == "amal" else "Medi", g.get("bucket"))
                        r.update(verdict="not-scored", folded_into=g["id"], why=why, why_by="medi", _was=r["verdict"])
                        g.setdefault("folded", []).append({"id": r["id"], "producer": r["by"]["producer"], "ref": r["by"]["ref"], "why": why})
                        actions["move"].append(("vocab_errors", r["id"], why, "C2q"))
                break
        # C1 / C1p / C1a / C1q: a Word Bank Correct on a word the readers' slip covers
        for m in wb_ok:
            t = base(norm(m.get("tok")))
            if not t:
                continue
            for r in [r for r in rv if not r.get("folded_into")]:
                W, F = toks(r.get("wrong")), toks(r.get("fix"))
                if t not in W and t != norm(r.get("wrong")):
                    continue
                if m["verdict"] == "folded":
                    break
                m["_was"] = m["verdict"]
                if r["row_kind"] == "asked":
                    conflict("C1a", m, r)
                    continue
                if t in F:
                    conflict("C1p", m, r)
                    continue
                names_this = W == [t] or [w for w in W if w not in F] == [t]
                rv_state = reviewed(review_patches, m["by"]["ref"])
                if rv_state == "hand":
                    conflict("C1r", m, r)
                    continue
                patched = hand_patch(review_patches, m["by"]["ref"]) or rv_state == "auto"
                why_same = r.get("word_key") and r.get("word_key") == m.get("word_key")
                # her voiced signal on exactly this word, on a row the audit counts (one reader or both): specific beats the
                # matcher's general "provisional use"; a low-confidence row or a gloss is not enough
                # her signal on exactly this word, on a row both readers saw (or she tapped): specific beats the matcher's
                # general "provisional use"; one reader alone (medium) or low is not enough (loop audit + Codex 2026-10-02:
                # 09-23 33:17 لازم - her real fix there was أشكي -> أشتكي)
                if names_this and not is_gloss(r.get("wrong")) and strength(r) >= 2 and not patched:
                    c = conflict("C1", m, r)
                    if resolve:
                        supersede_wb(m, r, ("Same attempt, counted once: Amal %s (%s) and it counts as the slip" if why_same else
                                            ("Said here, another word intended: Amal %s (%s)" + ("" if r["verdict"] != "not-scored" else
                                            "; her word is not on her list, so neither counts"))) % (TM.SIGNAL_WORDS.get(r.get("signal"), "flagged it"), r.get("fix") or ""),
                                     bool(why_same))
                        actions["move"].append(("vocab_correct", m["id"], m["why"], "C1"))
                    settle(c)
                    continue
                kind = "CR" if patched else "C1q"
                c = conflict(kind, m, r, {"why_medi": "his Word Bank edit" if patched else "not one word" if not names_this
                                          else "a description, not his words" if is_gloss(r.get("wrong")) else "only one reader saw it"})
                orig = {base(norm(x)): x for x in re.split(r"[\s.…,،؟?!:;\"“”()\-]+", r.get("wrong") or "") if norm(x)}
                settled = {base(norm(x.get("tok"))) for x in wb_ok if reviewed(review_patches, x["by"]["ref"]) == "hand"}
                opts = (["ledger", "none"] if patched else [orig.get(w, w) for w in W if w not in F and w not in settled][:4] + ["none"])
                one = None
                if not patched and len(opts) == 2:     # one candidate: a yes/no, nobody types the word
                    one, opts = opts[0], ["wrong", "none"]
                q = (AMAL_WORDS["CR"] % (m.get("tok") or "") if patched else AMAL_WORDS["C1q1"] % one if one else AMAL_WORDS["C1q"])
                c["one"] = one
                ans = needs_medi(c, opts, q, group=r["id"])
                if ans:
                    c["resolved"] = True
                    who = "Amal" if (c.get("ruled") or {}).get("by") == "amal" else "Medi"
                    if ans == "none":
                        drop_slip(r, c, ans)
                    elif resolve and (ans in ("ledger", "wrong") or base(norm(ans)) == t):
                        supersede_wb(m, r, "%s %s: %s was the wrong word" % (who, ((c.get("ruled") or {}).get("date") or "")[:10], ans if ans not in ("ledger", "wrong") else m.get("tok")), bool(why_same))
                        actions["move"].append(("vocab_correct", m["id"], m["why"], kind))
        # C2w: a Word Bank Wrong on a counted grammar slip's word
        for m in wb_bad:
            t = base(norm(m.get("tok")))
            for g in gs:
                if t and t in toks(g.get("wrong")) and g.get("scored_rule"):
                    if reviewed(review_patches, m["by"]["ref"]) == "hand":
                        conflict("C1r", m, g)
                        break
                    if hand_patch(review_patches, m["by"]["ref"]) or reviewed(review_patches, m["by"]["ref"]) == "auto":
                        c = conflict("CR", m, g)
                        if needs_medi(c, ["ledger", "none"], AMAL_WORDS["CR"] % (m.get("tok") or "")) != "ledger":
                            break
                    else:
                        c = conflict("C2w", m, g)
                    if resolve:
                        why = "Grammar, not vocabulary: the same slip is counted as grammar %s (WS-06)" % g.get("bucket")
                        m["_was"] = "wrong"
                        m.update(verdict="not-scored", folded_into=g["id"], why=why, why_by=c["kind"])
                        g.setdefault("folded", []).append({"id": m["id"], "producer": "word-bank", "ref": m["by"]["ref"], "why": why})
                        actions["overrides"].append({"event_id": m["by"]["ref"], "date": date, "mark": g["id"], "was": "wrong",
                                                     "changes": {"grammar_only": True, "classification": "grammar",
                                                                 "ledger": g["id"], "ledger_reason": why}})
                        actions["move"].append(("vocab_errors", m["id"], why, c["kind"]))
                    settle(c)
                    break
        # C3: a use and a slip of the same rule on one turn (GR-14)
        for u in [m for m in ms if m["verdict"] == "use"]:
            g = next((g for g in gs if g.get("bucket") == u["bucket"]), None)
            if not g:
                continue
            c = conflict("C3", u, g)
            if resolve:
                u.update(verdict="folded", folded_into=g["id"], why=PRECEDENCE["C3"]["decides"], _was="use")
                g.setdefault("folded", []).append({"id": u["id"], "producer": "use-counter", "ref": u["id"], "t": u.get("t"), "hit": u.get("said"),
                                                   "why": "same turn as the slip (GR-14)"})
                actions["fold_uses"].append({"bucket": u["bucket"], "date": date, "t": u.get("t"), "hit": u.get("said"), "mark": g["id"]})
            settle(c)

    for m in marks:
        if "_was" in m:
            w = m.pop("_was")
            if m.get("verdict") in ("folded", "not-scored"):
                m["was"] = w
    led = {"date": date, "about": "One lesson ledger (LS-11): every judgment is one mark on one transcript turn. Generated by "
                                  "scripts/lesson_ledger.py via build_lessons_page_data.py; never edit by hand.",
           "resolve": bool(resolve),
           "turns": [[u["t"], u.get("end"), u["who"], u["text"]] for u in turns],
           "marks": marks, "conflicts": conflicts,
           "needs_medi": [c["id"] for c in conflicts if c.get("needs_medi") and not c.get("group")]}
    led["counts"] = counts(led, scored_rules)
    return led, actions


def counts(led, scored_rules=None):
    """Every number the pages show for this lesson, counted over the marks."""
    M = led["marks"]
    v = collections.Counter(m["verdict"] for m in M if m["kind"] == "vocab")
    right, partial, wrong = v["right"], v["partial"] + v["asked"], v["wrong"]
    scored = right + partial + wrong
    words = {"right": right, "partial": partial, "wrong": wrong, "scored": scored,
             "pct": round(100 * (right + .5 * partial) / scored, 1) if scored else None,
             "audit_wrong": sum(1 for m in M if m["kind"] == "vocab" and m["id"].startswith("ra:") and m["verdict"] == "wrong"),
             "audit_partial": sum(1 for m in M if m["kind"] == "vocab" and m["id"].startswith("ra:") and m["verdict"] == "asked"),
             "not_scored": v["not-scored"], "folded": v["folded"]}
    by_rule = {}
    for m in M:
        if m["kind"] != "grammar" or m["verdict"] not in ("use", "slip"):
            continue
        r = by_rule.setdefault(m["bucket"], {"uses": 0, "mistakes": 0, "scored": bool(m.get("scored_rule"))})
        r["mistakes"] += m["verdict"] == "slip"
        r["uses"] += 1
    sc = [r for r in by_rule.values() if r["scored"]]
    uses, smis = sum(r["uses"] for r in sc), sum(r["mistakes"] for r in sc)
    grammar = {"uses": uses, "mistakes": sum(r["mistakes"] for r in by_rule.values()), "scored_mistakes": smis,
               "unscored_mistakes": sum(r["mistakes"] for r in by_rule.values() if not r["scored"]),
               "pct": round(100 * (uses - smis) / uses, 1) if uses else None, "by_rule": dict(sorted(by_rule.items()))}
    # an unscored rule (no use counter) keeps uses = its slips per rule, as the Grammar page shows; it is never in a %
    return {"words": words, "grammar": grammar, "conflicts": len(led["conflicts"]), "needs_medi": len(led["needs_medi"])}


# plain words for a settled conflict (lesson notes, the diff table)
KIND_WORDS = {"C1": "Word Bank said right, Amal said no to that word: her no counts",
              "C1p": "slip elsewhere in the phrase: the word stays right", "C1a": "he asked for another word: both stand",
              "C1q": "which word of the phrase was wrong: Medi", "C1r": "the Word Bank's context review already settled it: unchanged", "C2": "one slip was counted twice (word + grammar): counted once, as grammar",
              "C2b": "a different word and a wrong form in one word: both count", "C2q": "word slip or grammar slip: Medi", "C2w": "a grammar slip the Word Bank also called a wrong word: counted once, as grammar",
              "C3": "one turn was both a use and a slip of the same rule: one attempt, wrong", "CR": "a Word Bank re-read (or Medi's edit) vs Amal's no: Medi"}


def medi_item(led, c):
    """One needs-Medi moment, as the Lessons page lists it: his line, the two judgments, the candidate words."""
    turn = led["turns"][c["turn"]] if c.get("turn") is not None else None
    M = {m["id"]: m for m in led["marks"]}
    a, b = (M.get(x) or {} for x in c["marks"])
    return {"id": c["id"], "kind": c["kind"], "t": c["t"], "mmss": c["mmss"], "line": turn[3] if turn else None,
            "question": c.get("question"), "options": c.get("options"), "now": c.get("counted_as_now"),
            "also": [x["mmss"] for x in led["conflicts"] if x.get("group") == c["id"]],
            "a": {"by": a.get("by", {}).get("producer"), "verdict": a.get("verdict") if a.get("verdict") != "folded" else a.get("was"),
                  "word": a.get("tok") or a.get("wrong"), "word_key": a.get("word_key")},
            "b": {"by": b.get("by", {}).get("producer"), "verdict": b.get("verdict"), "wrong": b.get("wrong"), "fix": b.get("fix"),
                  "bucket": b.get("bucket"), "signal": b.get("signal")},
            "ask": c.get("ask") or "medi"}


def amal_item(date, led, c, answered=None):
    """One card on Amal's Tutor hub (LS-12): the moment (both voices), Medi's line, her own next line, the question and the
    choices in plain words. id = 'ledger:<question id>' = the amal_rules word_key her tap is saved under."""
    T = led["turns"]
    i = c.get("turn")
    medi = T[i][3] if i is not None else None
    amal = next((u[3] for u in T[(i or 0) + 1:(i or 0) + 14] if u[2] in ("Amal", "chat") and u[0] <= c["t"] + 30), None) if i is not None else None
    opts = c.get("options") or []
    lab = lambda o: LABELS.get(o) or o
    a, b = max(0, int(c["t"]) - 4), int(c["t"]) + 14
    return {"id": "ledger:" + c["id"], "conflict": c["id"], "date": date, "t": c["t"], "mmss": c["mmss"],
            "audio": ("lessons/%s/audio/lesson.mp3#t=%d,%d" % (date, a, b)) if date != "2026-09-10" else ("lessons/%s/audio/Medi.mp3#t=%d,%d" % (date, a, b)),
            "medi_said": medi, "amal_said": amal, "question": c.get("question"),
            "options": [{"value": o, "label": lab(o)} for o in opts],
            **({"answered": answered} if answered else {})}


def uses_minus(uses_by_bucket, folds):
    """grammar-usage.json uses without the ones the ledger folded into a slip on the same turn (C3, GR-14)."""
    drop = collections.Counter((f["bucket"], f["date"], f.get("t"), f.get("hit")) for f in folds)
    out = {}
    for b, us in uses_by_bucket.items():
        keep = []
        for u in us:
            k = (b, u.get("date"), u.get("t"), u.get("hit"))
            if drop[k]:
                drop[k] -= 1
                continue
            keep.append(u)
        out[b] = keep
    return out


def all_fold_uses(repo=REPO):
    """Every ledger's folded uses (the Grammar page applies the same ones, so its per-rule numbers are the ledger's)."""
    d = os.path.join(repo, "data", "lesson-work", "ledger")
    out = []
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if re.fullmatch(r"\d{4}-\d\d-\d\d\.json", f):
            out += J(os.path.join(d, f)).get("fold_uses") or []
    return out


def write_diff(published, lessons, ledgers, repo=REPO):
    """data/lesson-work/ledger/_diff.md: last published numbers -> this build, one row per lesson, plus every conflict."""
    before = {d: {"words": x.get("words") or {}, "grammar": x.get("grammar") or {}} for d, x in published.items()}
    after = {L["date"]: {"words": L["words"], "grammar": L["grammar"], "resolved": L["ledger"]["resolved"],
                         "needs_medi": L["ledger"]["needs_medi"]} for L in lessons}
    lines = ["# One ledger: live site (origin/master) -> this build", "",
             "A cell 'a -> **b**' moved from a to b; a single number did not move.", "", diff_table(before, after), "", "## Conflicts", ""]
    for d, led in sorted(ledgers.items()):
        for c in led["conflicts"]:
            state = "Medi?" if c.get("needs_medi") else "Medi: " + c["medi"]["answer"] if c.get("medi") else "settled" if c.get("resolved") else "both stand"
            M = {m["id"]: m for m in led["marks"]}
            a, b = M[c["marks"][0]], M[c["marks"][1]]
            extra = "; her word is not on her list, so neither counts" if c["kind"] == "C1" and b.get("verdict") == "not-scored" else ""
            lines.append(f"- {d} {c['mmss']} {c['kind']} {state}: {a.get('tok') or a.get('wrong') or a.get('said') or ''} "
                         f"({a['by']['producer']} {a.get('was') or a['verdict']}) vs {b.get('wrong') or b.get('said') or ''} -> {b.get('fix') or ''} "
                         f"({b['by']['producer']} {b.get('verdict')}{' ' + b['bucket'] if b.get('bucket') else ''}) - {KIND_WORDS[c['kind']]}{extra}")
    p = os.path.join(repo, "data", "lesson-work", "ledger", "_diff.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return p


# ------------------------------------------------------------------ inputs / files
def input_files(date):
    return ["docs/lessons/%s.html" % date, "docs/data/word-bank-evidence.json", "docs/data/word-bank-review.json",
            "data/full-audit-2026-09-26.json", "docs/data/grammar-usage.json", "data/grammar-usage-rulings.json",
            "data/lesson-work/sheet-verdicts.json", "data/lesson-work/lesson-types/%s.json" % date,
            "data/lesson-work/ledger-rulings.json", "data/lesson-work/ledger-amal.json", "data/lesson-work/transcript-fixes.json", "docs/data/words.json", "docs/data/grammar-buckets.json",
            "scripts/amal_grammar_notes.py", "scripts/lesson_ledger.py", "scripts/transcript_marks.py",
            "scripts/build_lessons_page_data.py"]


def write(led, repo=REPO):
    led = dict(led, inputs={p: sha(os.path.join(repo, p)) for p in input_files(led["date"])})
    os.makedirs(os.path.join(repo, "data", "lesson-work", "ledger"), exist_ok=True)
    p = os.path.join(repo, "data", "lesson-work", "ledger", led["date"] + ".json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(led, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return p


def diff_table(before, after):
    """before/after = {date: {"words": {...}, "grammar": {...}}} -> markdown table (one row per lesson)."""
    out = ["| Lesson | Words % | Words scored | Grammar % | Slips | Uses | Conflicts (settled / Medi?) |", "|---|---|---|---|---|---|---|"]
    for d in sorted(after):
        b, a = before.get(d) or {}, after[d]
        f = lambda k, x: (b.get(k) or {}).get(x)
        g = lambda k, x: (a.get(k) or {}).get(x)
        cell = lambda k, x: (str(f(k, x)) if f(k, x) == g(k, x) else "%s -> **%s**" % (f(k, x), g(k, x)))
        out.append("| %s | %s | %s | %s | %s | %s | %s / %s |" % (d, cell("words", "pct"), cell("words", "scored"), cell("grammar", "pct"), cell("grammar", "mistakes"),
                                                           cell("grammar", "uses"), a.get("resolved", 0), a.get("needs_medi", 0)))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ the guard check
def check(repo=REPO):
    """Problems (empty = OK). Every page number = a count over the ledger."""
    probs = []
    L = J(os.path.join(repo, "docs", "data", "lessons.json"))
    slips_doc = J(os.path.join(repo, "docs", "data", "word-bank-audit-slips.json"), {}) or {}
    audit = J(os.path.join(repo, "data", "full-audit-2026-09-26.json"))
    ev = {e["id"]: e for e in (J(os.path.join(repo, "docs", "data", "word-bank-evidence.json"), {}) or {}).get("events", [])}
    for a in (J(os.path.join(repo, "docs", "data", "word-bank-review.json"), {}) or {}).get("additions", []):
        ev.setdefault(a["event"]["id"], a["event"])         # events the review overlay adds are Word Bank events too
    wba = J(os.path.join(repo, "docs", "data", "word-bank-audit.json"), {}) or {}
    wbc = collections.Counter((e.get("date"), e.get("status")) for e in wba.get("events", []))
    console = J(os.path.join(repo, "docs", "data", "grammar-console.json"), {}) or {}
    usage = J(os.path.join(repo, "docs", "data", "grammar-usage.json"), {}) or {}
    usage_uses = usage.get("uses") or {}
    usage_rows = list(usage.get("ruled_out") or []) + list(usage.get("not_uses_auto") or [])
    bucket_ids = {b["id"] for b in (J(os.path.join(repo, "docs", "data", "grammar-buckets.json"), {}) or {}).get("buckets", [])}
    all_over = []
    led_by_rule = collections.defaultdict(lambda: [0, 0])
    for Ls in L["lessons"]:
        d = Ls["date"]
        lp = os.path.join(repo, "data", "lesson-work", "ledger", d + ".json")
        if not os.path.exists(lp):
            probs.append(f"{d}: no ledger (run scripts/build_lessons_page_data.py)")
            continue
        led = J(lp)
        # stale: an input changed after the ledger was built
        changed = [p for p, h in (led.get("inputs") or {}).items() if sha(os.path.join(repo, p)) != h]
        if changed:
            probs.append(f"{d}: ledger is older than its inputs ({', '.join(changed[:3])}): rebuild (build_lessons_page_data.py)")
        c = counts(led)
        if c != led["counts"]:
            probs.append(f"{d}: ledger counts do not match its own marks")
        # every page number = a count over the ledger
        w, g = Ls["words"], Ls["grammar"]
        for k in ("right", "partial", "wrong", "scored", "pct"):
            if w.get(k) != c["words"][k]:
                probs.append(f"{d}: Lessons words.{k}={w.get(k)} but the ledger counts {c['words'][k]}")
        for k in ("uses", "mistakes", "pct") + (("scored_mistakes", "unscored_mistakes") if g.get("uses") is not None else ()):
            if g.get("uses") is None and k in ("uses", "pct"):
                continue
            if g.get(k) != c["grammar"][k]:
                probs.append(f"{d}: Lessons grammar.{k}={g.get(k)} but the ledger counts {c['grammar'][k]}")
        if (Ls.get("ledger") or {}).get("needs_medi") != len(led["needs_medi"]):
            probs.append(f"{d}: Lessons shows {(Ls.get('ledger') or {}).get('needs_medi')} Medi? moments, the ledger has {len(led['needs_medi'])}")
        # the detail lists = the ledger's marks
        D = J(os.path.join(repo, "docs", "data", "lessons", d + ".json"))
        ids_c = set(item_ids(D.get("vocab_correct", []), "wb:", "event_id"))
        led_c = {m["id"] for m in led["marks"] if m["kind"] == "vocab" and m["verdict"] in ("right", "partial")}
        if ids_c != led_c:
            probs.append(f"{d}: vocab_correct cards != ledger right/partial marks ({len(ids_c ^ led_c)} differ)")
        ids_g = {"rg:" + x["id"] for x in D.get("grammar_errors", [])}
        led_g = {m["id"] for m in led["marks"] if m["verdict"] == "slip"}
        if ids_g != led_g:
            probs.append(f"{d}: grammar cards != ledger slip marks ({len(ids_g ^ led_g)} differ)")
        # every producer item exactly one mark (its own, or folded into the mark of the same moment)
        own = collections.Counter(m["id"] for m in led["marks"])
        own_m = {m["id"]: m for m in led["marks"]}
        # a folded reference counts unless it is the back-reference of a mark that says it was folded into this one
        folded = collections.Counter(f["id"] for m in led["marks"] for f in m.get("folded") or []
                                     if not (f["id"] in own_m and own_m[f["id"]].get("folded_into") == m["id"]))
        dup = [k for k, n in (own + folded).items() if n > 1]
        if dup:
            probs.append(f"{d}: {len(dup)} producer items with two marks {dup[:3]}")
        have = set(own) | set(folded)
        need = set(item_ids(D.get("vocab_correct", []), "wb:", "event_id"))
        need |= set(item_ids([e for e in D.get("vocab_errors", []) if e.get("source") != "audit-2026-09-26"], "wb:", "event_id"))
        need |= {"ra:" + e["audit_uid"] for e in D.get("vocab_errors", []) + D.get("not_errors", []) if e.get("audit_uid")}
        need |= {"rg:" + x["id"] for x in D.get("grammar_errors", []) + D.get("grammar_not_counted", [])}
        vrows = [v for v in audit["sweep_compat"].get("vocab", []) if v["date"] == d and v.get("source") == "audit-2026-09-26"
                 and v.get("t") not in (None, "")]
        need |= {"ra:" + v["uid"] for v in vrows}
        # every grammar use the counter found (and every ruled-out / not-a-use row) is in the ledger
        n_use = sum(1 for b, us in usage_uses.items() if b not in NO_USAGE and b in bucket_ids for u in us if u.get("date") == d)
        led_use = sum(1 for k in have if str(k).startswith("use:"))
        if n_use != led_use:
            probs.append(f"{d}: the use counter found {n_use} grammar uses, the ledger holds {led_use}")
        n_nu = sum(1 for r in usage_rows if r.get("date") == d)
        if n_nu != sum(1 for k in have if str(k).startswith("nu:")):
            probs.append(f"{d}: {n_nu} ruled-out / not-a-use rows, the ledger holds a different number")
        lost = sorted(need - have)
        if lost:
            probs.append(f"{d}: {len(lost)} producer items have no mark {lost[:3]}")
        # no conflict without a needs-Medi entry or a rule that decided it
        for cf in led["conflicts"]:
            if cf.get("would_settle") and not led.get("resolve"):
                continue
            if not cf.get("resolved") and not cf.get("needs_medi") and not cf.get("medi") and cf["kind"] not in ("C1p", "C1a", "C2b", "C1r"):
                probs.append(f"{d}: conflict {cf['id']} is neither resolved by a rule nor listed for Medi")
            if cf.get("needs_medi") and (cf.get("group") or cf["id"]) not in led["needs_medi"]:
                probs.append(f"{d}: conflict {cf['id']} needs Medi but is not on the list")
        for m in led["marks"]:
            if m["by"]["producer"] not in PRODUCERS:
                probs.append(f"{d}: mark {m['id']} from unknown producer {m['by']['producer']}")
            if m["verdict"] == "not-scored" and not m.get("why"):
                probs.append(f"{d}: not-scored mark {m['id']} has no reason")
        # Word Bank: its Correct count for the lesson = the ledger's Word Bank right marks
        wb_right = sum(1 for m in led["marks"] if m["id"].startswith("wb:") and m["verdict"] == "right")
        for st, vs in (("Partial", ("partial",)), ("Wrong", ("wrong",))):
            n = len({m["by"]["ref"] for m in led["marks"] if m["id"].startswith("wb:") and m["verdict"] in vs})
            if wba and n > wbc[(d, st)]:
                probs.append(f"{d}: the ledger has {n} Word Bank {st.lower()} events, the Word Bank audit {wbc[(d, st)]}")
        if wba and wb_right != wbc[(d, "Correct")]:
            probs.append(f"{d}: Word Bank audit has {wbc[(d, 'Correct')]} Correct, the ledger {wb_right}")
        for r, x in c["grammar"]["by_rule"].items():
            led_by_rule[r][0] += x["uses"]
            led_by_rule[r][1] += x["mistakes"]
        all_over += [o["event_id"] for o in (led.get("overrides") or [])]
    # every answer Medi gave still matches a question (a changed row would otherwise drop his answer silently)
    asked = set()
    for f in os.listdir(os.path.join(repo, "data", "lesson-work", "ledger")) if os.path.isdir(os.path.join(repo, "data", "lesson-work", "ledger")) else []:
        if re.fullmatch(r"\d{4}-\d\d-\d\d\.json", f):
            asked |= {c["id"] for c in J(os.path.join(repo, "data", "lesson-work", "ledger", f)).get("conflicts", [])}
    opts, followers = {}, {}
    for f in os.listdir(os.path.join(repo, "data", "lesson-work", "ledger")) if os.path.isdir(os.path.join(repo, "data", "lesson-work", "ledger")) else []:
        if re.fullmatch(r"\d{4}-\d\d-\d\d\.json", f):
            cs = J(os.path.join(repo, "data", "lesson-work", "ledger", f)).get("conflicts", [])
            opts.update({c["id"]: c.get("options") or [] for c in cs})
            followers.update({c["id"]: c["group"] for c in cs if c.get("group")})
    for cid, r in load_rulings(os.path.join(repo, "data", "lesson-work", "ledger-rulings.json")).items():
        if r.get("by") == "amal":
            continue                 # her taps come from her own buttons (always an option); a vanished one is listed in _diff.md
        if r.get("rule") != "LS-11":
            probs.append(f"Medi's answer to {cid} has no rule 'LS-11' (AGENTS.md: every ruling row names its rule)")
        if cid in opts and r.get("answer") not in opts[cid]:
            probs.append(f"Medi's answer {r.get('answer')!r} to {cid} is not one of its options {opts[cid]}: nothing would change")
        if cid in followers:
            probs.append(f"Medi's answer is keyed to {cid}, which is part of question {followers[cid]}: key it to that question")
        if cid not in asked:
            probs.append(f"Medi's answer to {cid} matches no question any more (the moment changed): ask him again or move the answer")
    # the Word Bank overrides the pages apply = the ledgers' overrides, and each still matches its event
    over = slips_doc.get("overrides") or []
    if sorted(o["event_id"] for o in over) != sorted(all_over):
        probs.append(f"word-bank-audit-slips.json carries {len(over)} overrides, the ledgers {len(all_over)}")
    patches = (J(os.path.join(repo, "docs", "data", "word-bank-review.json"), {}) or {}).get("patches") or {}
    for o in over:
        pt = patches.get(o["event_id"]) or {}
        hit = (set(pt.get("changes", {})) | set(pt.get("expected", {}))) & set(o.get("changes") or {})
        if hit:
            probs.append(f"override {o['event_id'][:12]}: a Word Bank review patch sets {sorted(hit)} too, so the ledger's call would not show")
        e = ev.get(o["event_id"])
        if e is None:
            probs.append(f"override {o['event_id'][:12]}: no such Word Bank event")
        elif any(json.dumps(e.get(k)) != json.dumps(v) for k, v in (o.get("expected") or {}).items()):
            probs.append(f"override {o['event_id'][:12]}: the event changed since the ledger was built (expected {o.get('expected')})")
    # Grammar page (console) per rule = the sum over the ledgers
    for b in console.get("buckets", console.get("rules", [])) if isinstance(console, dict) else []:
        if not isinstance(b, dict) or not b.get("id"):
            continue
        u, mi = led_by_rule.get(b["id"], [0, 0])
        if b.get("uses") is not None and int(b.get("uses") or 0) != u:
            probs.append(f"Grammar page {b['id']}: {b.get('uses')} uses, the ledgers {u}")
        if int(b.get("mistakes") or 0) != mi:
            probs.append(f"Grammar page {b['id']}: {b.get('mistakes')} slips, the ledgers {mi}")
    return probs


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "show"])
    ap.add_argument("date", nargs="?")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.cmd == "check":
        p = check()
        for x in p[:40]:
            print("  " + x)
        print("ledger: OK" if not p else f"ledger: FAIL {len(p)} problem(s)")
        return 1 if p else 0
    led = J(os.path.join(LEDGER_DIR, a.date + ".json"))
    print(a.date, json.dumps(led["counts"], ensure_ascii=False))
    for c in led["conflicts"]:
        print(" ", c["kind"], c["mmss"], "Medi?" if c.get("needs_medi") else "resolved" if c.get("resolved") else "both stand", c.get("options") or "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
