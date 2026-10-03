# -*- coding: utf-8 -*-
"""Marks on the Lessons page transcript (PG-20, Medi 2026-10-02: "for the transcript lets put check marks and xs for
incorrect correct and mark vocab or grammar with grammar rule", "mark amals signal for correction too", "underline the
word thats wrong").

Nothing here judges anything. Every chip is an existing scored item, placed on the turn it was said in:
  vocab   Word Bank scored events (right / partial) + the error cards (Word Bank misses, audit word slips), with the
          hand-check drops (not_errors) and off-list words shown grey with their reason
  grammar counted slips (full audit sweep_compat) + detected uses (docs/data/grammar-usage.json) that no slip pairs
          with (the same ±2 s pairing as scripts/grammar_math.py, so a ✓ is a use the % counts as right), Amal-ruled
          rows / ruled-out / automatic not-a-use rows grey with their reason
  fix     Amal's line where she gives the signal that made a ✗ count (t_amal on the slip row), linked to his ✗
  off     a Medi turn inside an off-lesson stretch (LS-10) is grey "not scored: off-lesson"
Placement is by time on the lesson clock: a Medi turn whose span [t, end] holds the item's time within SLACK seconds
(whole-second times from the audit sit up to 1 s before the turn they name); with several candidates the one whose
text holds the word wins. A miss is reported, never forced onto a turn.
Underlines are character spans in the turn text: the slip's `wrong` on his line, its `right` on her line, matched
after normalising hamza / taa marbuta / alif maqsura / diacritics / "الـ " spacing; with no exact match the closest
token window is used and flagged "closest".
"""
import collections, difflib, re

SLACK = 2.0          # s: same moment
LOOSE = 8.0          # s: a second look only when the turn text holds the word
SIGNAL_WORDS = {
    "recast": "repeats it right",
    "prompt-then-fix": "prompts you, then gives it",
    "explicit-no": "says no",
    "named-rule": "names the rule",
    "finished-sentence": "finishes your sentence",
    "asked": "you asked, she answered",
    "amal-ruling": "confirmed on her review page",
}
VOICED = set(SIGNAL_WORDS) - {"amal-ruling"}     # signals she gives in the lesson itself
NO_USAGE = {"F1", "F2", "F3"}

_AR = re.compile(r"[ء-ي]")
_DIA = re.compile(r"[ً-ْٰـ]")


def _norm_char(c):
    c = c.lower()
    return {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي", "’": "'", "‘": "'"}.get(c, c)


def normalise(text):
    """(normalised string, index map back into text). Drops diacritics/tatweel; 'الـ ' + word reads as 'ال' + word."""
    out, idx = [], []
    text = text or ""
    i = 0
    while i < len(text):
        c = text[i]
        if _DIA.match(c):
            i += 1
            continue
        out.append(_norm_char(c))
        idx.append(i)
        i += 1
    s = "".join(out)
    # "ال " (el- written apart) -> "ال": remove the space after a standalone ال
    s2, idx2 = [], []
    for k, ch in enumerate(s):
        if ch == " " and k >= 2 and s[k - 2:k] == "ال" and (k == 2 or not _word(s[k - 3])) and k + 1 < len(s) and _AR.match(s[k + 1]):
            continue
        s2.append(ch)
        idx2.append(idx[k])
    return "".join(s2), idx2


def _word(ch):
    return ch.isalnum() or "ء" <= ch <= "ي"


def _tail(text, end):
    """Carry a span over the tatweel / diacritics that follow its last letter (الـ, كتابٌ)."""
    while end < len(text) and _DIA.match(text[end]):
        end += 1
    return end


def _clean_needle(n):
    n = re.sub(r"\([^)]*\)", " ", n or "")          # "something else (for تاني إشي)" -> "something else"
    n = re.sub(r"[.…,،؟?!:;\"“”]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def find_span(text, needle, _reading=False):
    """[start, end, how] in text for needle, how = exact | closest; None when nothing is close."""
    nd = _clean_needle(needle)
    if not nd or not text:
        return None
    s, idx = normalise(text)
    n, _ = normalise(nd)
    n = n.strip()
    if not n:
        return None
    pos = 0
    while True:
        k = s.find(n, pos)
        if k < 0:
            break
        a, b = k, k + len(n)
        if (a == 0 or not _word(s[a - 1])) and (b >= len(s) or not _word(s[b])):
            return [idx[a], _tail(text, idx[b - 1] + 1), "exact"]
        pos = k + 1
    # a fix written in Amal's Arabizi ("kaan laazem") on a line the engine wrote in Arabic: read it as Arabic first
    # (scripts/arabizi_reader.py, her Doc words only, nothing guessed) and look again
    if not _AR.search(nd) and _AR.search(text) and not _reading:
        try:
            import arabizi_reader
            ar = arabizi_reader.to_arabic(nd)
        except Exception:
            ar = None
        if ar and "." not in ar.strip(" .") and _AR.search(ar):
            sp = find_span(text, ar.strip(" ."), _reading=True)
            if sp and sp[2] == "exact":
                return sp
    # closest token window of the same length
    toks = [(m.start(), m.end()) for m in re.finditer(r"[^\s.…,،؟?!:;\"“”()\-]+", s)]
    want = len(n.split())
    best = None
    for w in range(max(1, want - 1), want + 2):
        for i in range(0, max(0, len(toks) - w + 1)):
            a, b = toks[i][0], toks[i + w - 1][1]
            r = difflib.SequenceMatcher(None, s[a:b], n).ratio()
            if best is None or r > best[0]:
                best = (r, a, b)
    if best and best[0] >= 0.67:
        return [idx[best[1]], _tail(text, idx[best[2] - 1] + 1), "closest"]
    return None


def _speaker(turn, who):
    if who == "Medi":
        return turn["who"] == "Medi"
    return turn["who"] == "Amal" or (turn["who"] == "chat" and turn.get("typed_by") == "Amal")


def place(turns, t, who, needle=None):
    """Index of the turn this item was said in, or None. (index, how) with how = time | text."""
    if t is None:
        return None
    cand = []
    for i, u in enumerate(turns):
        if not _speaker(u, who):
            continue
        a, b = u["t"], u.get("end") if u.get("end") is not None else u["t"]
        d = 0.0 if a - SLACK <= t <= b + SLACK else min(abs(t - a), abs(t - b))
        if d <= LOOSE:
            cand.append((d, i))
    if not cand:
        return None
    has = (lambda i: bool(needle) and find_span(turns[i]["text"], needle) is not None)
    near = [c for c in cand if c[0] == 0.0]
    if near:
        # a turn that ENDED before the item's time is the least likely home (whole-second reader times sit up to 1 s
        # BEFORE the line they name, never after it: 09-10 43:35 "كانت." was placed on the 43:32 question - loop audit
        # 2026-10-02), then the turn whose text holds the word, then the nearest start
        whole = float(t).is_integer()          # only the readers' whole-second times (final council 2026-10-02)
        ended = lambda i: whole and turns[i].get("end") is not None and turns[i]["end"] < t - 0.01
        near.sort(key=lambda c: (ended(c[1]), not has(c[1]), abs(turns[c[1]]["t"] - t)))
        return near[0][1], "time"
    loose = sorted((c for c in cand if has(c[1])), key=lambda c: c[0])
    return (loose[0][1], "text") if loose else None


def _sec(s):
    if s in (None, ""):
        return None
    if isinstance(s, (int, float)):
        return float(s)
    p = [int(x) for x in str(s).split(":")]
    return float(p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1])


def _in_off(t, off):
    return next((o for o in off if o[0] <= t <= o[1]), None)


def build(date, detail, uses_by_bucket, buckets, not_taught, ruled_out=(), not_uses=(), off_lesson=(), ledger=None):
    """detail = the per-lesson JSON (turns, vocab_errors, vocab_correct, grammar_errors, grammar_not_counted, not_errors).
    Returns (tmarks, report): tmarks = {turn index: {"c": [chips], "u": [underlines]}}."""
    turns = detail["turns"]
    off = [(_sec(o.get("from")), _sec(o.get("to")), o.get("what") or "off-lesson") for o in off_lesson or []
           if _sec(o.get("from")) is not None and _sec(o.get("to")) is not None]
    tm = {}
    rep = {"scored": 0, "placed": 0, "loose": 0, "missed": [],
           "fix_wanted": 0, "fix_placed": 0, "fix_missed": [],
           "ul_wanted": 0, "ul_exact": 0, "ul_shared": 0, "ul_closest": [], "ul_none": [],
           "grey": 0, "grey_missed": 0}
    n = [0]

    def nid(p):
        n[0] += 1
        return f"{p}{n[0]}"

    def put(i, chip):
        tm.setdefault(i, {"c": [], "u": []})["c"].append(chip)

    def underline(i, needle, cls, chip_id, what):
        if not needle:
            return
        rep["ul_wanted"] += 1
        sp = find_span(turns[i]["text"], needle)
        if not sp or sp[2] != "exact":
            # the words may sit in the same speaker's next line (her fix often follows the 'no'), or his line just before
            who = "Medi" if turns[i]["who"] == "Medi" else "Amal"
            if who == "Amal":    # her words after the signal line, up to 30 s on
                near = [j for j in range(i + 1, min(len(turns), i + 12)) if _speaker(turns[j], who) and turns[j]["t"] <= turns[i]["t"] + 30]
            else:                # his line just before or after (a phrase split over two turns)
                near = [j for j in range(max(0, i - 3), min(len(turns), i + 3)) if j != i and _speaker(turns[j], who)
                        and turns[i]["t"] - 10 <= turns[j]["t"] <= turns[i]["t"] + 6]
            for j in near:
                sj = find_span(turns[j]["text"], needle)
                if sj and sj[2] == "exact":
                    i, sp = j, sj
                    break
        if not sp:
            rep["ul_none"].append({"t": turns[i]["t"], "what": what, "needle": needle, "text": turns[i]["text"]})
            return
        if any(sp[0] < x[1] and x[0] < sp[1] for x in tm.get(i, {}).get("u", [])):
            rep["ul_shared"] += 1          # the same word already carries another chip's underline (two slips, one word)
            return
        if sp[2] == "exact":
            rep["ul_exact"] += 1
        else:
            rep["ul_closest"].append({"t": turns[i]["t"], "what": what, "needle": needle, "got": turns[i]["text"][sp[0]:sp[1]]})
        tm.setdefault(i, {"c": [], "u": []})["u"].append([sp[0], sp[1], cls, chip_id, sp[2]])

    def scored_item(t, chip, needle=None, what=""):
        rep["scored"] += 1
        p = place(turns, t, "Medi", needle)
        if not p:
            rep["missed"].append({"t": t, "what": what})
            return None
        rep["placed"] += 1
        if p[1] == "text":
            rep["loose"] += 1
        put(p[0], chip)
        return p[0]

    def grey(t, reason, label, needle=None):
        p = place(turns, t, "Medi", needle)
        if not p:
            rep["grey_missed"] += 1
            return
        rep["grey"] += 1
        put(p[0], {"id": nid("g"), "k": "na", "s": "na", "label": label, "why": reason})

    def amal_fix(slip_chip, medi_i, t_amal, signal, right, what):
        if signal not in VOICED or t_amal is None:
            return
        rep["fix_wanted"] += 1
        p = place(turns, t_amal, "Amal", right)
        # her fix comes at or after his line (a recast never comes before the slip)
        if p and medi_i is not None and p[0] < medi_i:
            p = None
        if not p:
            rep["fix_missed"].append({"t": t_amal, "what": what})
            return
        rep["fix_placed"] += 1
        fid = nid("f")
        slip_chip["link"] = fid
        put(p[0], {"id": fid, "k": "fix", "s": "fix", "signal": signal, "sig": SIGNAL_WORDS[signal],
                   "of": slip_chip["k"], "rule": slip_chip.get("rule"), "w": slip_chip.get("w"), "ar": slip_chip.get("ar"),
                   "said": slip_chip.get("said"), "right": right, "link": slip_chip["id"]})
        underline(p[0], right, "fix", fid, what + " fix")

    # ---------------- vocab
    for e in detail.get("vocab_correct") or []:
        s = "correct" if e.get("kind") == "correct" else "partial"
        scored_item(e["t"], {"id": nid("v"), "k": "vocab", "s": s, "w": e.get("arabizi"), "ar": e.get("arabic"),
                             "en": e.get("english"), "said": e.get("said")}, e.get("arabic"), "vocab " + str(e.get("word_key")))
    for e in detail.get("vocab_errors") or []:
        if e.get("on_sheet") is False:
            grey(e["t"], "not on her word list (left out of the Words %)", "vocab", e.get("wrong"))
            continue
        s = "asked" if e.get("kind") == "asked" else "wrong"
        sig = e.get("signal")
        chip = {"id": nid("v"), "k": "vocab", "s": s, "w": e.get("arabizi"), "ar": e.get("arabic"), "en": e.get("english"),
                "said": e.get("wrong") or e.get("said"), "right": e.get("fix") or e.get("arabic"),
                "signal": sig, "sig": SIGNAL_WORDS.get(sig)}
        i = scored_item(e["t"], chip, e.get("wrong"), "vocab " + str(e.get("arabic")))
        if i is not None:
            if s == "wrong":
                underline(i, e.get("wrong"), "wrong", chip["id"], "vocab " + str(e.get("arabic")))
            amal_fix(chip, i, e.get("t_fix"), sig, e.get("fix"), "vocab " + str(e.get("arabic")))
    for e in detail.get("not_errors") or []:
        grey(e["t"], e.get("verdict_reason") or "dropped on the hand check", "vocab", e.get("wrong"))

    # ---------------- grammar slips (counted) and the rows Amal's notes take out
    slips_by_b = {}
    for g in detail.get("grammar_errors") or []:
        t = g.get("t")
        chip = {"id": nid("x"), "k": "grammar", "s": "wrong", "rule": g.get("bucket"), "name": g.get("bucket_name"),
                "said": g.get("wrong") or g.get("said"), "said_az": g.get("wrong_arabizi"),
                "right": g.get("right") or g.get("fix"), "right_az": g.get("right_arabizi"),
                "signal": g.get("signal"), "sig": SIGNAL_WORDS.get(g.get("signal"))}
        i = scored_item(t, chip, g.get("wrong"), "grammar " + str(g.get("id")))
        slips_by_b.setdefault(g.get("bucket"), []).append(t)
        if i is not None:
            underline(i, g.get("wrong"), "wrong", chip["id"], "grammar " + str(g.get("id")))
            amal_fix(chip, i, g.get("t_fix"), g.get("signal"), g.get("right"), "grammar " + str(g.get("id")))
    for g in detail.get("grammar_not_counted") or []:
        grey(g.get("t"), g.get("not_counted_why") or "taken out by Amal's notes", "grammar · " + str(g.get("bucket")), g.get("wrong"))

    # ---------------- grammar uses: detected uses no counted slip pairs with (grammar_math.pair's ±2 s window)
    for b, us in sorted(uses_by_bucket.items()):
        if b in NO_USAGE or b not in buckets:
            continue
        mine = [u for u in us if u.get("date") == date and u.get("t") is not None]
        if not mine:
            continue
        free = {}
        for u in mine:
            free.setdefault(int(u["t"]), []).append(u)
        for st in sorted((x for x in slips_by_b.get(b, []) if x is not None), reverse=True):
            for k in (0, -1, 1, -2, 2):
                if free.get(int(st) + k):
                    free[int(st) + k].pop()
                    break
        folded = collections.Counter((f["bucket"], f.get("t"), f.get("hit")) for f in (ledger or {}).get("fold_uses") or [])
        for u in sorted((u for v in free.values() for u in v), key=lambda u: u["t"]):
            if folded[(b, u.get("t"), u.get("hit"))]:          # LS-11 C3: the same turn's slip is this attempt (GR-14)
                folded[(b, u.get("t"), u.get("hit"))] -= 1
                continue
            if not_taught(b):
                grey(u["t"], "rule not taught yet (Amal's notes)", "grammar · " + b, u.get("hit"))
                continue
            scored_item(u["t"], {"id": nid("r"), "k": "grammar", "s": "correct", "rule": b, "name": buckets[b].get("name"),
                                 "said": u.get("hit")}, u.get("hit"), "use " + b)
    for r in list(ruled_out) + list(not_uses):
        if r.get("date") == date:
            grey(r.get("t"), r.get("why") or "not a use", "grammar" + (" · " + r["bucket"] if r.get("bucket") else ""), r.get("hit"))

    # ---------------- LS-11: a moment two judges disagree on and no rule decides: an orange "Medi?" chip, counted as before
    for c in (ledger or {}).get("conflicts") or []:
        if c.get("needs_medi") and c.get("turn") is not None:
            who = "Amal" if c.get("ask") == "amal" else "Medi"
            put(c["turn"], {"id": nid("q"), "k": "medi", "s": "medi", "label": who + "?", "conflict": c["id"],
                            "why": (c.get("question") or "") + " · waiting for " + who + ", counted as before until answered"})
            rep["medi"] = rep.get("medi", 0) + 1

    # ---------------- off-lesson stretches: grey on his unmarked turns inside them
    for i, u in enumerate(turns):
        if u["who"] != "Medi" or i in tm:
            continue
        o = _in_off(u["t"], off)
        if o:
            tm[i] = {"c": [{"id": nid("g"), "k": "na", "s": "na", "label": "lesson", "why": "off-lesson (" + o[2] + ")"}], "u": []}
            rep["grey"] += 1
    for v in tm.values():
        v["u"].sort(key=lambda x: x[0])
    rep["rate"] = round(100 * rep["placed"] / rep["scored"], 1) if rep["scored"] else None
    rep["fix_rate"] = round(100 * rep["fix_placed"] / rep["fix_wanted"], 1) if rep["fix_wanted"] else None
    return {str(k): v for k, v in sorted(tm.items())}, rep
