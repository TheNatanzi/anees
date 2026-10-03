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


def load(path=FIXES_P):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f).get("rows") or []


def apply(date, turns, rows=None):
    """turns: [{t, who, text, ...}] -> new list; a fixed turn gets text = heard version, engine = the engine's text,
    heard = [{engine_wrote, heard, rule}]. A row that matches no turn is reported in unmatched()."""
    rows = [r for r in (load() if rows is None else rows) if r.get("date") == date]
    out = []
    for u in turns:
        u = dict(u)
        for r in rows:
            if r.get("who") == u.get("who") and abs(float(r["t"]) - float(u["t"])) <= 1.0 and r["engine_wrote"] in (u.get("text") or ""):
                u.setdefault("engine", u["text"])
                u["text"] = u["text"].replace(r["engine_wrote"], r["heard"], 1)
                u.setdefault("heard", []).append({"engine_wrote": r["engine_wrote"], "heard": r["heard"], "rule": r.get("rule")})
        out.append(u)
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
    return [r for r in rows if not any(r.get("who") == u.get("who") and abs(float(r["t"]) - float(u["t"])) <= 1.0
                                       and r["engine_wrote"] in (u.get("engine") or u.get("text") or "") for u in turns)]


def apply_tracks(date, T, rows=None):
    """The same overlay on scripts/lesson_turns.py turns ({speaker, start, end, text}): the grammar use counter and
    the console read the heard text too (TR-18: every builder reads what was said)."""
    conv = [{"t": u["start"], "who": u.get("speaker"), "text": u.get("text")} for u in T]
    out = apply(date, conv, rows)
    res = []
    for u, v in zip(T, out):
        if v.get("engine"):
            u = dict(u, text=v["text"], engine=v["engine"], heard=v["heard"])
        res.append(u)
    return res
