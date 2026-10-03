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
            rows = rows + MC.text_rows() + MC.rule_text_rows()
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


def apply(date, turns, rows=None, sort=True):
    """turns: [{t, who, text, ...}] -> new list; a fixed turn gets text = heard version, engine = the engine's text,
    heard = [{engine_wrote, heard, rule}]. A row that matches no turn is reported in unmatched()."""
    rows = [r for r in (load() if rows is None else rows) if r.get("date") == date or r.get("pattern")]
    out = []
    for u in turns:
        u = dict(u)
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
    return [r for r in rows if not any((u.get("engine_who") or u.get("who")) in (r.get("who"), r.get("set_who"))
                                       and abs(float(r["t"]) - float(u.get("engine_t", u["t"]))) <= 1.0
                                       and r["engine_wrote"] in (u.get("engine") or u.get("text") or "") for u in turns)]


def apply_tracks(date, T, rows=None):
    """The same overlay on scripts/lesson_turns.py turns ({speaker, start, end, text}): the grammar use counter and
    the console read the heard text too (TR-18: every builder reads what was said)."""
    conv = [{"t": u["start"], "who": u.get("speaker"), "text": u.get("text")} for u in T]
    out = apply(date, conv, rows, sort=False)
    res = []
    for u, v in zip(T, out):
        if v.get("engine"):
            u = dict(u, text=v["text"], engine=v["engine"], heard=v["heard"])
        if v.get("engine_who") and v["who"] != u.get("speaker"):
            u = dict(u, speaker=v["who"], engine_speaker=u.get("speaker"))
        if v.get("engine_t") is not None and float(v["t"]) != float(u["start"]):     # PR-15 time fix (Codex audit 2026-10-03)
            d = float(v["t"]) - float(u["start"])
            u = dict(u, start=float(v["t"]), end=(float(u["end"]) + d) if u.get("end") is not None else None, engine_start=u["start"])
        res.append(u)
    return res
