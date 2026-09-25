# -*- coding: utf-8 -*-
"""One place that turns a lesson folder into a timeline of turns.

Three sources, all put on ONE clock:
  - transcript.txt              [mm:ss] Speaker: text     (already one clock)
  - scribe_Medi / scribe_Amal   one file per speaker, each on its OWN track clock.
                                tracks/tracks.json says when each track started;
                                on 09-17 Medi's track starts 93 s after Amal's, so
                                without the offset her replies land a minute and a
                                half away from what he said.
  - docs/lessons/<date>.html     fallback: the published lesson page, when the lesson folder has
                                nothing the two readers above understand (09-10 is tracks only;
                                09-18 is one mixed scribe.json with speaker_0/speaker_1). The
                                page already carries each turn's speaker and start time.
  - meet-chat-transcript.txt    Amal typing the fixed sentence into the Meet chat.
                                The chat clock is not the recording clock, so it is
                                aligned by matching her typed Arabizi to what she
                                then says out loud (see chat_offset).
"""
import json, os, re
from statistics import median

ANEES = r"C:\dev\anees\data\lessons"


# ---------------------------------------------------------------- offsets
def track_offset(date, who):
    """Seconds from the recording start to the start of this speaker's track."""
    d = os.path.join(ANEES, date)
    try:
        tracks = json.load(open(os.path.join(d, "tracks", "tracks.json"), encoding="utf-8"))["tracks"]
    except Exception:
        return 0.0
    try:
        dur = json.load(open(os.path.join(d, "scribe_%s.provenance.json" % who), encoding="utf-8"))
        dur = dur.get("duration") or dur.get("audio_duration_secs")   # provenance files write audio_duration_secs (09-23 fix)
    except Exception:
        dur = None
    mine = [t for t in tracks if t.get("participant", "").startswith(who)]
    if not mine:
        return 0.0
    if dur:
        best = min(mine, key=lambda t: abs(t["duration_s"] - dur))
        if abs(best["duration_s"] - dur) < 2:
            return float(best["start"]["relative"])
    # A stitched file is padded from the first segment on.
    return float(min(t["start"]["relative"] for t in mine))


# ---------------------------------------------------------------- sources
def turns_from_transcript(path):
    out = []
    txt = open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"\[(\d+):(\d+)\]\s*(Amal|Medi):\s*([^\n]+)", txt):
        t = int(m.group(1)) * 60 + int(m.group(2))
        text = re.sub(r"\(pause[^)]*\)", " ", m.group(4))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append({"speaker": m.group(3), "start": float(t), "end": float(t), "text": text})
    return out


def turns_from_scribe(path, speaker, offset=0.0, gap=1.2):
    """Glue words into utterances on a silence gap, shifted onto the shared clock."""
    try:
        o = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    out, cur = [], None
    for w in o.get("words", []):
        if w.get("type") != "word":
            continue
        s, e, txt = w.get("start"), w.get("end"), (w.get("text") or "").strip()
        if not txt or s is None:
            continue
        s, e = s + offset, (e if e is not None else s) + offset
        if cur and s - cur["end"] <= gap:
            cur["words"].append(txt)
            cur["end"] = e
        else:
            if cur:
                out.append(cur)
            cur = {"speaker": speaker, "start": s, "end": e, "words": [txt]}
    if cur:
        out.append(cur)
    for c in out:
        c["text"] = re.sub(r"\s+", " ", " ".join(c.pop("words"))).strip()
    return [c for c in out if c["text"]]


PAGES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "lessons")


def _clean(h):
    import html as _h
    t = _h.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"\s+", " ", re.sub(r"\(pause[^)]*\)", " ", t)).strip()


def turns_from_page(date):
    """Read the turns off the published lesson page (two markups)."""
    p = os.path.join(PAGES, date + ".html")
    if not os.path.exists(p):
        return []
    s = open(p, encoding="utf-8", errors="replace").read()
    out = []
    # <p class="turn"><button class="t" data-t=...>...<b>Amal|Medi</b>: <span class="words">...</span></p>
    for m in re.finditer(r'<p[^>]*class="turn[^"]*"[^>]*>(.*?)</p>', s, re.S):
        body = m.group(1)
        t = re.search(r'data-t="([\d.]+)"', body)
        who = re.search(r"<b>\s*(Amal|Medi)\s*</b>", body)
        words = re.search(r'<span class="words"[^>]*>(.*?)</span>', body, re.S)
        if t and who and words:
            out.append({"speaker": who.group(1), "start": float(t.group(1)),
                        "end": float(t.group(1)), "text": _clean(words.group(1))})
    # <article class="turn" ...> ... data-start=... <strong>Amal’s recording</strong> ... <p class="words">
    for m in re.finditer(r'<article[^>]*class="turn[^"]*"[^>]*>(.*?)</article>', s, re.S):
        body = m.group(1)
        t = re.search(r'data-start="([\d.]+)"', body)
        who = re.search(r"<strong>\s*(Amal|Medi)\S*\s+recording\s*</strong>", body)
        words = re.search(r'<p[^>]*class="words"[^>]*>(.*?)</p>', body, re.S)
        if t and who and words:
            out.append({"speaker": who.group(1), "start": float(t.group(1)),
                        "end": float(t.group(1)), "text": _clean(words.group(1))})
    return [x for x in out if x["text"]]


def chat_lines(date):
    p = os.path.join(ANEES, date, "meet-chat-transcript.txt")
    if not os.path.exists(p):
        return []
    out = []
    txt = open(p, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"(\d\d):(\d\d):(\d\d)[.,]\d+,[^\n]*\n([^:\n]+):\s*([^\n]*)", txt):
        who = "Amal" if "Amal" in m.group(4) else "Medi" if ("Medi" in m.group(4) or "Natanzi" in m.group(4)) else m.group(4).strip()
        t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        text = m.group(5).strip()
        if text:
            out.append({"speaker": who, "start": float(t), "end": float(t), "text": text, "chat": True})
    return out


# ---------------------------------------------------------------- lesson
def lesson_turns(date, with_chat=False):
    """(turns sorted by time, source label). Chat lines carry "chat": True."""
    d = os.path.join(ANEES, date)
    T, src = [], None
    p = os.path.join(d, "transcript.txt")
    if os.path.exists(p):
        T = turns_from_transcript(p)
        src = "transcript.txt" if T else None
    if not T:
        for who in ("Medi", "Amal"):
            T += turns_from_scribe(os.path.join(d, "scribe_%s.json" % who), who, track_offset(date, who))
        if T:
            src = "scribe per-speaker tracks"
    if not T:
        T = turns_from_page(date)
        if T:
            src = "published lesson page docs/lessons/%s.html" % date
    if with_chat and T:
        from xscript import chat_offset
        C = chat_lines(date)
        if C:
            offs = chat_offset(C, T)
            for c, off in zip(C, offs):
                c["start"] += off
                c["end"] += off
                c["chat_offset"] = round(off, 1)
            T = T + C
    T.sort(key=lambda x: x["start"])
    return T, src
