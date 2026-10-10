# -*- coding: utf-8 -*-
"""Heard-word overlay on the lesson transcript (RULES.md S2, TR-18).

The engine's transcript is never edited. data/lesson-work/transcript-fixes.json lists lines where it wrote another word
than the one said (Medi 2026-10-02: "3ala 3ashrah cant you tell from context im saying a time?" - the engine wrote
على العشاء, dinner, as his answer to her "ay sa3a?"). apply() returns the turns with the heard word in place and the
engine's words kept on the turn as "engine", so the page shows both and every builder reads what was said.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIXES_P = os.path.join(REPO, "data", "lesson-work", "transcript-fixes.json")


def load(path=FIXES_P, medi=True):
    """The hand overlay rows, plus Medi's own page corrections (text / speaker / time / missing) and his standing text
    rules (PR-15, scripts/medi_corrections.py) - every builder reads the same overlay."""
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            rows = json.load(f).get("rows") or []
    if medi and path == FIXES_P:
        try:
            import medi_corrections as MC
            # a row that changes nothing (heard = what the engine wrote, e.g. an AI read of a note that just copied the
            # line: 10-08 08:36 'اليوم talvez' -> 'اليوم talvez') is no fix: it must not replace the second listen's
            # text (بلبس) with the engine's (TR-18, Medi's own rows only)
            rows = rows + [r for r in MC.text_rows() + MC.rule_text_rows()
                           if r.get("set_who") or r.get("set_t") is not None or r.get("heard_line") is not None
                           or " ".join(str(r.get("heard") or "").split()) != " ".join(str(r.get("engine_wrote") or "").split())]
        except Exception as e:  # noqa: BLE001 - a bad corrections file never stops a build (council 5)
            print("transcript_fixes: Medi's corrections not applied (%s)" % type(e).__name__)
    return rows


def _hit(r, u):
    """Does overlay row r belong to turn u? A standing rule (pattern) matches any line of that speaker with the same
    3-word context; a moment row matches its own line (+-1 s)."""
    if r.get("pattern"):
        import medi_corrections as MC
        src = u.get("engine") or u.get("text") or ""
        return r.get("who") == u.get("who") and r["engine_wrote"] in src and MC._ctx(src, r["engine_wrote"]) == tuple(r.get("ctx") or ())
    return r.get("who") == u.get("who") and abs(float(r["t"]) - float(u["t"])) <= 1.0


def _lands(r, u):
    """Would moment / rule row r change turn u as the engine wrote it?"""
    if r.get("heard_line") is not None:
        return _whole(r, u)
    if not _hit(r, u):
        return False
    if r.get("pattern") or r.get("set_who") or r.get("set_t") is not None:
        return True
    if not r["engine_wrote"]:
        return bool(r.get("heard"))
    return r["engine_wrote"] in (u.get("text") or "")


def _whole(r, u):
    """A WHOLE-LINE row (TR-22, the Gemini re-hear: {"line": the engine's whole line, "heard_line": the line as re-heard,
    "spans": [{"engine_wrote", "heard"}]}) names exactly one line: the same speaker, its time (+-1 s) and the engine's
    text letter for letter. It never lands on a typed chat line or on a line whose text differs by one character."""
    return (not u.get("chat") and r.get("who") == u.get("who") and abs(float(r["t"]) - float(u["t"])) <= 1.0
            and r["line"] == (u.get("text") or ""))


def whole_owners(whole, turns):
    """{turn index: row} - each whole-line row belongs to ONE turn: the nearest in time of the turns it names; when two
    turns it names start within 11 ms of the same distance (two identical lines at one moment) it belongs to none, and a
    turn takes one row only."""
    own = {}
    for r in whole:
        c = sorted((abs(float(r["t"]) - float(u["t"])), k) for k, u in enumerate(turns) if _whole(r, u))
        if c and (len(c) == 1 or c[1][0] - c[0][0] > 0.011) and c[0][1] not in own:
            own[c[0][1]] = r
    return own


def apply(date, turns, rows=None, sort=True):
    """turns: [{t, who, text, ...}] -> new list; a fixed turn gets text = heard version, engine = the engine's text,
    heard = [{engine_wrote, heard, rule}]. A row that matches no turn is reported in unmatched()."""
    rows = [r for r in (load() if rows is None else rows) if r.get("date") == date or r.get("pattern")]
    whole = [r for r in rows if r.get("heard_line") is not None]
    rows = [r for r in rows if r.get("heard_line") is None]
    out = []
    own = whole_owners(whole, turns) if whole else {}
    for k, u in enumerate(turns):
        u = dict(u)
        # A whole-line row goes in first, and ONLY on a line no correction of anyone lands on (Medi 2026-10-04: his own
        # corrections stay; a line he corrects later keeps his correction and loses the second listen's text).
        g = own.get(k)
        under = [r for r in rows if _lands(r, u)] if g is not None else []
        if g is not None and (not under or g.get("wins")):
            u["engine"] = u["text"]
            u["text"] = g["heard_line"]
            u.setdefault("heard", []).extend({"engine_wrote": x["engine_wrote"], "heard": x["heard"], "rule": g.get("rule"), "by": g.get("by")} for x in g.get("spans") or [])
            if under:
                # TR-27 (2026-10-07): the tutor listened and picked this reading over the correction on the line; her
                # answer wins (AM-06). The superseded row stays in the file and is recorded here, not applied.
                u["heard"].extend({"engine_wrote": r.get("engine_wrote") or "", "heard": r.get("heard") or "", "rule": r.get("rule"), "by": r.get("by"),
                                   "superseded_by": g.get("by"), "superseded": True} for r in under)
                out.append(u)
                continue
        for r in rows:
            if not _hit(r, u):
                continue
            if r.get("set_who") or r.get("set_t") is not None:      # PR-15: wrong speaker / wrong time on this line
                u.setdefault("engine_who", u.get("who"))
                u.setdefault("engine_t", u.get("t"))
                if r.get("set_who"):
                    u["who"] = r["set_who"]
                if r.get("set_t") is not None:
                    u["t"] = r["set_t"]
                u.setdefault("heard", []).append({"engine_wrote": "", "heard": "", "rule": r.get("rule"), "moved": True})
                continue
            if not r["engine_wrote"]:                                 # PR-15: a word the engine dropped
                if not r.get("heard"):
                    continue
                u.setdefault("engine", u["text"])
                a = r.get("insert_after") or ""
                i = u["text"].find(a) if a else -1
                u["text"] = (u["text"][:i + len(a)] + " " + r["heard"] + u["text"][i + len(a):]) if i >= 0 else (u["text"].rstrip() + " " + r["heard"])
                u.setdefault("heard", []).append({"engine_wrote": "", "heard": r["heard"], "rule": r.get("rule"),
                                                  **({"correction": r["correction"]} if r.get("correction") else {})})
                continue
            if r["engine_wrote"] in (u.get("text") or ""):
                if r["engine_wrote"] == r.get("heard"):
                    # a CONFIRMING row (Medi re-listened and the engine's word is what he said: 10-02 08:22 الصباح,
                    # 2026-10-04). It changes nothing on the line and writes no "engine wrote / you said" pair, but it
                    # lands (_lands), so the second listen's whole-line row never replaces this line.
                    continue
                u.setdefault("engine", u["text"])
                u["text"] = u["text"].replace(r["engine_wrote"], r["heard"], 1)
                u.setdefault("heard", []).append({"engine_wrote": r["engine_wrote"], "heard": r["heard"], "rule": r.get("rule"),
                                                  **({"correction": r["correction"]} if r.get("correction") else {})})
        out.append(u)
    if sort:
        out.sort(key=lambda u: float(u.get("t") or 0))
    return kaman_marra(out)


import re as _re
FILLER = _re.compile(r"^(آآآ|أأأ|اممم?|امم|uh|um|aaa|ا+)[،,.\s]*")


def kaman_marra(turns):
    """GR-11 on the transcript (Medi 2026-10-02 "10:09 aaa Kam Marra? Should be kaman marra"): his line that is only
    'كم مرة؟' (fillers aside) within 15 s after Amal spoke is 'كمان مرة؟' (again?), not 'how many times' - the engine
    drops the -an. Returns the turns with the heard words in place (engine text kept)."""
    out = []
    for i, u in enumerate(turns):
        core = FILLER.sub("", (u.get("text") or "").strip()).strip()
        before = [v for v in turns[max(0, i - 6):i] if v.get("who") == "Amal" and 0 <= float(u["t"]) - float(v["t"]) <= 15]
        after = [v for v in turns[i + 1:i + 6] if v.get("who") == "Amal" and 0 <= float(v["t"]) - float(u["t"]) <= 15]
        W = lambda v: set(_re.sub(r"[^\w\s]", " ", v.get("text") or "").split())
        repeats = any(len(W(a) & W(b)) >= max(1, len(W(b)) // 2) for b in before for a in after)   # she says it again
        if u.get("who") == "Medi" and _re.fullmatch(r"كم\s+مر[ةه]\s*[؟?]?\.?", core) and before and repeats:
            u = dict(u)
            u.setdefault("engine", u["text"])
            u["text"] = _re.sub(r"كم\s+مر", "كمان مر", u["text"], count=1)
            u.setdefault("heard", []).append({"engine_wrote": "كم مرة", "heard": "كمان مرة", "rule": "GR-11"})
        out.append(u)
    return out


def unmatched(date, turns, rows=None):
    rows = [r for r in (load() if rows is None else rows) if r.get("date") == date]
    lost = [r for r in rows if r.get("heard_line") is not None
            and not any(_whole(r, dict(u, text=u.get("engine") or u.get("text"), who=u.get("engine_who") or u.get("who"), t=u.get("engine_t", u["t"]))) for u in turns)]
    rows = [r for r in rows if r.get("heard_line") is None]
    return lost + [r for r in rows if not any((u.get("engine_who") or u.get("who")) in (r.get("who"), r.get("set_who"))
                                       and abs(float(r["t"]) - float(u.get("engine_t", u["t"]))) <= 1.0
                                       and r["engine_wrote"] in (u.get("engine") or u.get("text") or "") for u in turns)]


def apply_tracks(date, T, rows=None):
    """The same overlay on scripts/lesson_turns.py turns ({speaker, start, end, text}): the grammar use counter and
    the console read the heard text too (TR-18: every builder reads what was said)."""
    conv = [{"t": u["start"], "who": u.get("speaker"), "text": u.get("text")} for u in T]
    every = [r for r in (load() if rows is None else rows) if r.get("date") == date or r.get("pattern")]
    out = apply(date, conv, [r for r in every if r.get("heard_line") is None], sort=False)     # whole-line rows: below, one owner each
    res, touched, span0 = [], set(), {}
    for k, (u, v) in enumerate(zip(T, out)):
        span0[k] = (float(u["start"]), float(u.get("end") or u["start"]))      # the turn's own span, before any time fix
        if v.get("heard") or v.get("engine") or v.get("engine_who") or v.get("engine_t") is not None:
            touched.add(k)                                         # a correction of anyone (text, speaker or time) is on this turn
        if v.get("engine"):
            u = dict(u, text=v["text"], engine=v["engine"], heard=v["heard"])
        if v.get("engine_who") and v["who"] != u.get("speaker"):
            u = dict(u, speaker=v["who"], engine_speaker=u.get("speaker"))
        if v.get("engine_t") is not None and float(v["t"]) != float(u["start"]):     # PR-15 time fix (Codex audit 2026-10-03)
            d = float(v["t"]) - float(u["start"])
            u = dict(u, start=float(v["t"]), end=(float(u["end"]) + d) if u.get("end") is not None else None, engine_start=u["start"])
        res.append(u)
    res_engine = [(u.get("text") or "") for u in T]                # the engine's text of every turn, corrected or not
    # Whole-line rows (the second listen) on track turns. A track turn glues several page lines, so the row's line is
    # looked for as WHOLE WORDS in the ENGINE text of his turns whose span holds the row's time. Every owner is decided
    # on the engine's text before anything is replaced (a row never lands on words another row wrote); a row is applied
    # only when its line stands exactly once in all the turns that hold its time and no correction of anyone is on that
    # turn. Typed chat lines never take one.
    #   span  - a turn with a real end: start .. end, 0.3 s of slack. A lesson read from transcript.txt has [mm:ss]
    #           stamps only (whole seconds, end == start on every turn): there a turn runs to the same speaker's next
    #           stamp, plus the second the stamp cut off.
    #   text  - the line letter for letter first; if that is nowhere, the same WORDS with punctuation, spacing and
    #           sound tags ([laughs], which track turns never carry) left out - replaced at the true positions.
    win = _spans(T, span0)
    todo = {}
    for r in [x for x in every if x.get("heard_line") is not None]:
        pat = _re.compile(r"(?<!\S)" + _re.escape(r["line"]) + r"(?!\S)")
        near = [k for k in range(len(res)) if not T[k].get("chat") and T[k].get("speaker") == r.get("who") and win[k][0] <= float(r["t"]) <= win[k][1]]
        own = [(k, m.start(), m.end(), True) for k in near for m in pat.finditer(res_engine[k])]
        if not own:
            own = [(k, a0, b0, False) for k in near for a0, b0 in _find_words(r["line"], res_engine[k])]
        if len(own) == 1 and (own[0][0] not in touched or r.get("wins")):
            todo.setdefault(own[0][0], []).append(own[0][1:] + (r,))
    for k, hits in todo.items():
        hits.sort(key=lambda h: h[0])
        if any(b0[1] > a1[0] for b0, a1 in zip(hits, hits[1:])):     # two rows claim overlapping words of one turn: none
            continue
        v, text, heard = res[k], (res_engine[k] if any(h[3].get("wins") for h in hits) else res[k]["text"]), []   # TR-27: a winning row starts from the engine's text
        for a0, b0, exact, r in reversed(hits):
            new = r["heard_line"] if exact else _no_tags(r["heard_line"])
            if new == text[a0:b0]:                                   # only a sound tag differed: nothing to say here
                continue
            text = text[:a0] + new + text[b0:]
            cut = (lambda x: x) if exact else _no_tags              # track turns carry no sound tags: the record neither
            heard = [{"engine_wrote": cut(x["engine_wrote"]), "heard": cut(x["heard"]), "rule": r.get("rule"), "by": r.get("by")} for x in r.get("spans") or []
                     if cut(x["engine_wrote"]) != cut(x["heard"])] + heard
        if text != v["text"]:
            res[k] = dict(v, engine=v["text"], text=text, heard=heard, rehear=True)
    return res


import unicodedata as _ud
_TAG = _re.compile(r"\[[^\]\n]*\]")


def _no_tags(s):
    """The text without sound tags ([laughs], [ضحكة]) - track turns are words only."""
    return _re.sub(r"\s+", " ", _TAG.sub(" ", s or "")).strip()


def _words(s):
    """[(the word without punctuation / symbols, start, end)] - sound tags and bare punctuation are no words."""
    out = []
    for m in _re.finditer(r"\[[^\]\n]*\]|\S+", s or ""):
        if m.group(0).startswith("["):
            continue
        w = "".join(c for c in m.group(0) if _ud.category(c)[0] not in "PS")
        if w:
            out.append((w, m.start(), m.end()))
    return out


def _find_words(line, text):
    """Every place the line's words stand in text as a run of whole words, punctuation and spacing aside:
    [(start, end)] true character positions in text."""
    a, b = [w for w, _, _ in _words(line)], _words(text)
    if not a:
        return []
    keys = [w for w, _, _ in b]
    return [(b[i][1], b[i + len(a) - 1][2]) for i in range(len(b) - len(a) + 1) if keys[i:i + len(a)] == a]


def _spans(T, span0):
    """{turn index: (from, to)} - the time a whole-line row must fall in to belong to the turn."""
    real = [k for k, u in enumerate(T) if not u.get("chat")]
    stamps = bool(real) and all(span0[k][1] == span0[k][0] and span0[k][0] == int(span0[k][0]) for k in real)
    if not stamps:
        return {k: (a0 - 0.3, max(b0, a0) + 0.3) for k, (a0, b0) in span0.items()}
    import bisect
    starts = {}
    for k in real:
        starts.setdefault(T[k].get("speaker"), set()).add(span0[k][0])
    starts = {w: sorted(v) for w, v in starts.items()}
    out = {}
    for k, (a0, b0) in span0.items():
        s = starts.get(T[k].get("speaker")) or []
        i = bisect.bisect_right(s, a0)
        out[k] = (a0 - 0.3, (s[i] if i < len(s) else float("inf")) + 1.0)
    return out
