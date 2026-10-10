# -*- coding: utf-8 -*-
"""Data for the Lessons page: one row per lesson + a per-lesson file with the heavy parts.

    python scripts/build_lessons_page_data.py            -> docs/data/lessons.json + docs/data/lessons/<date>.json
    python scripts/build_lessons_page_data.py --dump D   -> print a condensed transcript of lesson D (for reading)

Everything is on the LESSON CLOCK = the audio the lesson page plays (docs/lessons/<date>/audio/...).
Word timings come from the raw engine files, put on that clock by calibrating against the page itself:
every page line carries data-t (its first word's time on the page audio) and data-row
(<source>:row:<index into that source's Scribe words>), so offset = data-t - words[index].start, which is
constant per track (checked: spread < 0.02 s).

Sources per lesson (C:/dev/anees/data/lessons/<date>/):
  per-speaker Scribe (scribe_Medi.json / scribe_Amal.json [+ scribe_Amal_seg33.json on 09-15])  09-11 .. 09-23 except 09-18
  one diarized Scribe (scribe.json), speaker taken from the page line each word falls in         09-18
  words_labeled.json (already on the lesson clock, speaker labelled)                              08-25, 09-04, 09-05
  nothing with word timings (page has line start times only)                                       09-10 -> timing metrics null
  + data/backfill/gapfill/<date>/gapfill_<side>.json: a side whose track was empty, recovered from the mixed Meet
    recording or the person's own late-transcribed track (scripts/fill_meet_gaps.py); its lines join the turns tagged
    gap_fill + source (+ from_meet for Meet lines), its words join the timings.

Word scores run the Word Bank page's own JS (scripts/lessons_page_node.cjs) so they count exactly like it.
Grammar mistakes = the 2026-09-24 hand sweep (data/grammar-sweep-2026-09-24.json), speaking rows in an
approved bucket (docs/data/grammar-buckets.json) + unfiled rows in NEW-B18 (approved as B18).
Grammar uses = docs/data/grammar-usage.json (owned by another worker; read at build time).
Lesson types are Claude's reading of each lesson (LESSON_TYPES by hand, else the same-day reader's
data/lesson-work/lesson-types/<date>.json - LS-01), marked type_source 'claude-read'.
No paid APIs, nothing re-transcribed. Missing data -> null + a note, never a guess.
"""
import argparse, bisect, datetime as dt, hashlib, html, json, os, re, shutil, subprocess, sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DOCS = os.path.join(REPO, "docs")
RAW = r"C:\dev\anees\data\lessons"
NODE = r"C:\dev\tools\node-v24.18.0-win-x64\node.exe"
TMP = os.path.join(__import__("tempfile").gettempdir(), "anees-lessons-page")
sys.path.insert(0, HERE)
import lesson_ledger as LL  # noqa: E402  LS-11 one lesson ledger
import transcript_fixes as TFX  # noqa: E402  TR-18 heard-word overlay
import rehear_status as RH  # noqa: E402  PG-27 the "second listen" mark per lesson
import amal_grammar_notes as AMAL  # noqa: E402  Amal's notes 2026-09-27: which grammar corrections do not count



def _secs(mmss):
    try:
        parts = [int(x) for x in str(mmss).split(":")]
    except ValueError:
        return None
    n = 0
    for x in parts:
        n = n * 60 + x
    return n


VERDICT_DRIFT_S = 120   # a re-read lesson (new tracks, a grown transcript) re-times its cards by up to ~1.5 min (09-23: 11:17 -> 09:45)


def word_core(arabic):
    """The word itself, without the reader's gloss: 'كمان نص ساعة = in half an hour (after half an hour)' and
    'كمان نص ساعة = in half an hour' -> 'كمان نص ساعة'; 'قريب من السفر (قبل السفر بشوي)' -> 'قريب من السفر'."""
    a = str(arabic or "").split(" = ")[0]
    a = re.sub(r"\([^)]*\)", " ", a)
    a = re.sub(r"[ً-ْٰ]", "", a)        # harakat / shadda: خرّبته and خربته are one word
    a = re.sub(r"[^؀-ۿ ]", " ", a)
    return " ".join(a.split())


def hand_verdicts(rows):
    """Lookup for data/lesson-work/sheet-verdicts.json: (date, mmss, arabic) -> verdict. Exact key first; else the verdict
    for the SAME word (word_core: the reader's gloss may be re-worded) on the same date whose time is nearest within
    VERDICT_DRIFT_S, each such verdict used once. Before 2026-10-02 only the exact key matched, so a same-day re-review
    that re-timed or re-glossed a card (09-23 re-read after Amal's track was added: 07:09 -> 07:04, 'كمان نص ساعة = in half
    an hour (after half an hour)' -> '... = in half an hour') silently lost the reader's on-list verdict and the string
    match flagged known list words 'Not on sheet' (the hourly job's test_sheet_v1 block, 2026-10-02)."""
    exact, by_word, by_time, used = {}, {}, {}, set()
    for x in rows:
        exact[(x["date"], x["mmss"], x["arabic"])] = x
        by_time.setdefault((x["date"], x["mmss"]), []).append(x)
        core = word_core(x["arabic"])
        if core:
            by_word.setdefault((x["date"], core), []).append(x)

    def get(date, mmss, arabic):
        x = exact.get((date, mmss, arabic))
        if x is not None:
            used.add(id(x))
            return x
        same = [y for y in by_time.get((date, mmss), []) if id(y) not in used]
        if len(same) == 1:            # the one verdict at this very moment, re-glossed by a re-read ('ashyaak / ashyaaki' ->
            used.add(id(same[0]))     # 'أشياءك (ashyaa2ek)', 09-16 1:00:25 after the TR-17 re-read)
            return same[0]
        t, core = _secs(mmss), word_core(arabic)
        if t is None or not core:
            return None
        near = [(abs(_secs(y["mmss"]) - t), y) for y in by_word.get((date, core), [])
                if id(y) not in used and _secs(y["mmss"]) is not None]
        near = [(gap, y) for gap, y in near if gap <= VERDICT_DRIFT_S]
        if not near:
            return None
        y = min(near, key=lambda p: p[0])[1]
        used.add(id(y))
        return y
    return get


def _confirmed_new():
    try:
        import db
        return sorted({(str(r["lesson_date"]), r["word_key"]) for r in db.select("amal_rules", {"select": "lesson_date,word_key,kind", "kind": "eq.new"}) if r.get("word_key")})
    except Exception as e:
        # eng audit 2026-09-29: this fallback used to be silent, so a database hiccup quietly froze "new words" at the
        # 09-25 list. It stays (offline builds need it) but now says so; ANEES_STRICT=1 (the hourly job) fails closed.
        if os.environ.get("ANEES_STRICT") == "1":
            raise
        print("WARNING new words: database unreachable (%s); using the list last read 2026-09-25" % type(e).__name__, file=sys.stderr)
        return [("2026-09-04", "ana babse6"), ("2026-09-04", "banbese6")]   # last read 2026-09-25
CONFIRMED_NEW = _confirmed_new()
# New verbs per lesson: the verb pairs Amal taught that lesson. Medi confirmed 2026-09-25 ("you don't see bat3eb and
# bata33eb as new verbs I learned?") - these ARE his new words. Spelled as her Doc writes the "Ana ba-" form.
# Pairs marked review=True were first taught in an earlier lesson (or before the recordings). Medi 2026-09-26: "new" comes
# from CONTEXT (is she introducing it?), never from the sheet; a context read of all lessons
# (data/lesson-work/new-words-context-2026-09-26.md) found the last new-word lesson is 09-11 - 09-14..09-19 are one
# planned review series, one verb group per lesson ("a lesson for each group like this N then T then middle").
V = lambda lat, ar, review=False: {"latin": lat, "arabic": ar, "review": review}
TAUGHT = {
    "2026-09-04": [V("Ana babse6 / Ana banbese6", "أنا ببسط / أنا بنبسط")],
    "2026-09-05": [V("Ana baz3ej / Ana banze3ej", "أنا بزعج / أنا بنزعج"), V("Ana babse6 / Ana banbese6", "أنا ببسط / أنا بنبسط", True)],
    "2026-09-10": [V("Ana bakser / Ana bankeser", "أنا بكسر / أنا بنكسر"), V("Ana baz3ej / Ana banze3ej", "أنا بزعج / أنا بنزعج", True)],
    "2026-09-11": [V("Ana ba5rab / Ana ba5arreb", "أنا بخرب / أنا بخرّب")],
    "2026-09-14": [V("Ana baz3ej / Ana banze3ej", "أنا بزعج / أنا بنزعج", True), V("Ana bakser / Ana bankeser", "أنا بكسر / أنا بنكسر", True), V("Ana babse6 / Ana banbese6", "أنا ببسط / أنا بنبسط", True)],
    "2026-09-15": [V("Ana ba8ayyer / Ana bat8ayyar", "أنا بغيّر / أنا بتغيّر", True), V("Ana basawwer / Ana batsawwar", "أنا بصوّر / أنا بتصوّر", True), V("Ana bazakker / Ana batzakkar", "أنا بذكّر / أنا بتذكّر", True), V("Ana bakser / Ana bankeser", "أنا بكسر / أنا بنكسر", True)],
    "2026-09-16": [V("Ana ba7ammes / Ana bat7ammas", "أنا بحمّس / أنا بتحمّس", True), V("Ana bawajje3 / Ana batwajja3", "أنا بوجّع / أنا بتوجّع", True), V("Ana badaaye2 / Ana batdaaya2", "أنا بضايق / أنا بتضايق", True), V("Ana ba7arrek / Ana bat7arrak", "أنا بحرّك / أنا بتحرّك", True)],
    "2026-09-17": [V("Ana bat2assaf (la / min)", "أنا بتأسف (لـ / من)", True), V("Ana ba5awwef", "أنا بخوّف", True), V("Ana bada77ek", "أنا بضحّك", True), V("Ana ba5rab / Ana ba5arreb", "أنا بخرب / أنا بخرّب", True)],
    "2026-09-18": [V("Ana bazha2 / Ana bazahhe2", "أنا بزهق / أنا بزهّق", True), V("Ana bat3ab / Ana bata33eb", "أنا بتعب / أنا بتعّب", True), V("Ana baz3al / Ana baza33el", "أنا بزعل / أنا بزعّل", True), V("Ana ba5aaf / Ana ba5awwef", "أنا بخاف / أنا بخوّف", True), V("Ana bad7ak / Ana bada77ek", "أنا بضحك / أنا بضحّك", True), V("Ana ba3asseb", "أنا بعصّب", True)],
}
# LS-01 (Medi 2026-10-02 "You need to tell from context when shes teaching me new words"): a new lesson's type and taught
# words come from the same-day reader (scripts/lesson_type_read.py -> data/lesson-work/lesson-types/<date>.json). The hand
# dicts below stay as overrides: a date in LESSON_TYPES / TAUGHT wins over the reader's file.
import lesson_type_read as LTR  # noqa: E402
TYPE_READS = LTR.load_all(REPO)
for _d, _r in TYPE_READS.items():
    # AM-19: union - the hand pairs stay, the reader's pairs that are not already there are added (never hidden)
    _have = {re.sub(r"\s+", "", x["arabic"]) for x in TAUGHT.get(_d, [])}
    TAUGHT.setdefault(_d, []).extend(V(x["latin"], x["arabic"], bool(x.get("review"))) for x in _r.get("taught") or []
                                     if re.sub(r"\s+", "", x["arabic"]) not in _have)
DATES = sorted(f[:-5] for f in os.listdir(os.path.join(REPO, "docs", "lessons")) if re.fullmatch(r"20\d\d-\d\d-\d\d\.html", f))  # every published lesson page, so a new lesson flows by itself
GLUE = 1.2          # s: words closer than this are one turn
LAT_MAX = 15.0      # s: a reply later than this is not a reply
WORD_MAX = 2.0      # s: one word counts at most this long (the engine sometimes stretches a word over a silence;
                    #    on 09-05 / 09-11 / 09-15 that alone would add ~10 min of "talk")
AR = re.compile(r"[\u0621-\u064A\u0671-\u06D3]")

def J(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


_SOUND = None


def sound_key(latin):
    """TR-23: the one list word whose Arabizi sounds like `latin` (arabizi_reader._sk skeleton, 3+ letters), else None."""
    global _SOUND
    import arabizi_reader as AR
    if _SOUND is None:
        idx = {}
        for w in J(os.path.join(DOCS, "data", "words.json"))["items"]:
            for f in [w.get("arabizi")] + list(w.get("aliases") or []):
                z = re.sub(r"^(ana|el-|al-)\s*", "", str(f or "").strip().lower())
                if z and " " not in z and len(AR._sk(z)) >= 3:
                    idx.setdefault(AR._sk(z), set()).add(w["key"])
        _SOUND = {k: next(iter(v)) for k, v in idx.items() if len(v) == 1}
    return _SOUND.get(AR._sk(str(latin).strip().lower()))


def mmss(t):
    if t is None:
        return None
    t = int(round(t))
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def sec(s):
    if s in (None, "", "None"):
        return None
    p = [int(x) for x in str(s).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ------------------------------------------------------------------ page turns
def page_turns(date):
    """[{t, who, text, row?, chat}] as the lesson page shows them, on the page-audio clock."""
    h = open(os.path.join(DOCS, "lessons", date + ".html"), encoding="utf-8").read()
    out = []
    # current format (09-11 on): <p class="turn|chat"><button data-t data-row>...</button><b>Who</b>: <span class="words">
    for m in re.finditer(r'<p dir="auto" class="(turn|chat)"><button class="t" data-t="([\d.]+)"(?: data-row="([^"]+)")?[^>]*>.*?</button><b>([^<]*)</b>:\s*<span class="words">(.*?)</span></p>', h):
        out.append({"t": float(m.group(2)), "who": m.group(4).strip(), "text": strip_tags(m.group(5)),
                    "row": m.group(3), "chat": m.group(1) == "chat"})
    if out:
        return out
    # 09-10: <article class="turn"> with data-source / data-start
    for m in re.finditer(r'<article class="turn" id="([^"]+)">.*?data-source="([^"]+)" data-start="([\d.]+)".*?<p class="words"[^>]*>(.*?)</p>', h, re.S):
        who = "Amal" if m.group(2).endswith("amal") else "Medi"
        out.append({"t": float(m.group(3)), "who": who, "text": strip_tags(m.group(4)), "row": m.group(1), "chat": False})
    if out:
        return out
    # 08-25 / 09-04 / 09-05: <p class="ar amal"> [button data-start] <span class="t">mm:ss</span><b class="spk">Who:</b> text
    for m in re.finditer(r'<p class="ar (\w+)" dir="auto">(?:<button[^>]*data-start="([\d.]+)"[^>]*>[^<]*</button> )?<span class="t">([\d:]+)</span><b class="spk">([^<]*)</b>(.*?)</p>', h):
        who = {"amal": "Amal", "medi": "Medi"}.get(m.group(1), "?")
        text = re.sub(r"\(pause[^)]*\)", " ", strip_tags(m.group(5)))
        text = re.sub(r"\s+", " ", text).strip()
        if not text or text == ".":
            continue
        t = float(m.group(2)) if m.group(2) else float(sec(m.group(3)))
        out.append({"t": t, "who": who, "text": text, "row": None, "chat": False, "t_whole_second": not m.group(2)})
    return out


# ------------------------------------------------------------------ Meet gap-fill layers (scripts/fill_meet_gaps.py)
GAPFILL = os.path.join(REPO, "data", "backfill", "gapfill")


def gapfill_layers(date, root=None):
    """Finished gap-fill layers of a lesson: a missing speaker's side recovered from the mixed Meet recording
    (data/backfill/gapfill/<date>/gapfill_<side>.json, a source layer - rule S2, the raw transcripts are untouched)."""
    d = os.path.join(root or GAPFILL, date)
    if not os.path.isdir(d):
        return []
    return [J(os.path.join(d, f)) for f in sorted(os.listdir(d)) if re.fullmatch(r"gapfill_(amal|medi)\.json", f)]


def with_gapfill(P, layers):
    """The page lines with the layers' lines merged in on the lesson clock (page lines keep their order and content).
    Every added line carries gap_fill + its source: 'meet_mixed' (from_meet true: speakers split by diarization on the
    Meet recording) or 'own_track' (the person's own recording, transcribed late)."""
    import heapq
    add = sorted(({"t": L["t"], "who": L["who"], "text": L["text"], "row": None, "chat": False, "gap_fill": True,
                   "from_meet": bool(L.get("from_meet", (L.get("source") or "meet_mixed") == "meet_mixed")),
                   "source": L.get("source") or "meet_mixed", "confidence": L.get("confidence")}
                  for g in layers for L in g.get("lines") or []), key=lambda p: p["t"])
    return list(heapq.merge(P, add, key=lambda p: p["t"])) if add else P


def own_spans(P):
    """{side: [(from, to)]} lesson-clock spans the page already has from a person's reconnect recording (rows of a
    '-seg<start>' source, rule TR-17)."""
    by = {}
    for p in P:
        row = p.get("row") or ""
        if "-seg" in row and not p.get("chat"):
            by.setdefault((p["who"], row.split(":row:")[0]), []).append(p["t"])
    out = {}
    for (who, _), ts in by.items():
        out.setdefault(who, []).append((min(ts), max(ts)))
    return out


def trim_layers(layers, P, margin=2.0):
    """Rule TR-17: once a person's own reconnect recording is transcribed, the Meet gap-fill lines for the same stretch
    are the same speech heard a second time (from the mixed recording): they are dropped, the rest of the layer stays.
    A layer with nothing left is dropped."""
    spans = own_spans(P)
    if not spans:
        return layers
    out = []
    for g in layers:
        sp = spans.get(g.get("side")) or []
        inside = lambda t: any(a - margin <= t <= b + margin for a, b in sp)
        lines = [L for L in g.get("lines") or [] if not inside(L["t"])]
        if not lines:
            continue
        out.append({**g, "lines": lines, "words": [w for w in g.get("words") or [] if not inside(w["s"])]})
    return out


def gapfill_words(layers):
    return [{"s": w["s"], "e": w["e"], "who": w["who"], "text": w["text"], "kind": "word",
             "from_meet": (w.get("source") or "meet_mixed") == "meet_mixed"}
            for g in layers for w in g.get("words") or []]


GAP_SOURCES = {"meet_mixed": "the Meet recording", "own_track": "own recording (transcribed late)"}


def gapfill_summary(layers):
    out = []
    for g in layers:
        pv, sm = g.get("provenance") or {}, g.get("summary") or {}
        parts = pv.get("parts") or [{"source": "meet_mixed", "window": g["window"]}]
        out.append({"side": g["side"], "from": g["window"]["from"], "to": g["window"]["to"], "from_s": g["window"]["from_s"],
                    "to_s": g["window"]["to_s"], "source": g.get("source") or "meet_mixed", "lines": len(g.get("lines") or []),
                    "parts": [{"source": x["source"], "from": x["window"].get("from"), "to": x["window"].get("to"),
                               "lines": sum(1 for L in g.get("lines") or [] if (L.get("source") or "meet_mixed") == x["source"]
                                            and x["window"]["from_s"] <= L["t"] < x["window"]["to_s"]),
                               **({"status": x["status"]} if x.get("status") else {})} for x in parts],
                    "offset_s": pv.get("offset_s"), "residual_s": pv.get("residual_s"),
                    "diarization_confidence": sm.get("diarization_confidence", (pv.get("diarization") or {}).get("confidence")),
                    "meet_file": pv.get("meet_file_name")})
    return out


def gapfill_note(fills):
    out = []
    for f in fills:
        bits = []
        for x in f["parts"]:
            if x.get("status") == "nothing_filled":
                bits.append(f"{x['from']}-{x['to']}: nothing found in the Meet recording")
            else:
                bits.append(f"{x['from']}-{x['to']} filled from {GAP_SOURCES.get(x['source'], x['source'])} ({x['lines']} lines"
                            + (f"; speakers split by the engine's diarization, confidence {f['diarization_confidence']}; lines tagged from_meet" if x["source"] == "meet_mixed" else "")
                            + ")")
        out.append(f"{f['side']}'s side " + ", ".join(bits))
    return "; ".join(out)


# ------------------------------------------------------------------ word streams on the lesson clock
def _kind(w):
    if w.get("type") == "word":
        return "word"
    if w.get("type") == "audio_event":
        txt = (w.get("text") or "").lower()
        return "speaking" if ("speaking arabic" in txt or "speaks arabic" in txt) else "event"
    return None


def words_for(date, P):
    """(words, note). words = [{s, e, who, text, kind}] sorted, on the lesson clock. None if no timings exist."""
    d = os.path.join(RAW, date)
    rows = [p for p in P if p.get("row") and ":row:" in (p["row"] or "")]
    if os.path.exists(os.path.join(d, "scribe_Medi.json")) and os.path.exists(os.path.join(d, "scribe_Amal.json")) and rows and "recall" in rows[0]["row"]:
        out, notes = [], []
        bysrc = {}
        for p in rows:
            src, n = p["row"].rsplit(":row:", 1)
            bysrc.setdefault(src, []).append((p["t"], int(n)))
        for src, L in bysrc.items():
            who = "Amal" if "-amal" in src else "Medi"
            f = os.path.join(d, "scribe_%s%s.json" % (who, "_seg33" if src.endswith("-seg33") else ""))
            W = J(f)["words"]
            offs = [t - W[n]["start"] for t, n in L if n < len(W)]
            off = median(offs)
            if max(offs) - min(offs) > 0.1:
                notes.append(f"{src}: page/engine offset spread {max(offs) - min(offs):.2f}s")
            for w in W:
                k = _kind(w)
                if k and w.get("start") is not None:
                    out.append({"s": w["start"] + off, "e": (w.get("end") or w["start"]) + off, "who": who,
                                "text": (w.get("text") or "").strip(), "kind": k})
        out.sort(key=lambda w: w["s"])
        return out, "; ".join(notes) or None
    if os.path.exists(os.path.join(d, "scribe.json")) and rows and "meet" in rows[0]["row"]:
        # one diarized stream; a word belongs to the page line it falls in (the page named speakers by pitch)
        W = [w for w in J(os.path.join(d, "scribe.json"))["words"] if _kind(w)]
        starts = sorted((p["t"], p["who"]) for p in P if not p["chat"])
        ts = [s for s, _ in starts]
        out = []
        for w in W:
            i = bisect.bisect_right(ts, w["start"] + 0.01) - 1
            if i < 0:
                continue
            out.append({"s": w["start"], "e": w.get("end") or w["start"], "who": starts[i][1],
                        "text": (w.get("text") or "").strip(), "kind": _kind(w)})
        return out, "speakers estimated by voice pitch on one mixed recording (as on the lesson page)"
    f = os.path.join(d, "words_labeled.json")
    if not os.path.exists(f):
        f = os.path.join(REPO, "data", "lessons", date, "words_labeled.json")
    if os.path.exists(f):
        out = []
        for w in J(f):
            txt = (w.get("w") or "").strip()
            if not txt:
                continue
            k = "speaking" if re.search(r"speak(ing|s) arabic", txt, re.I) else ("event" if txt.startswith("[") else "word")
            out.append({"s": w["s"], "e": w.get("e") or w["s"], "who": w.get("spk") or "?", "text": txt, "kind": k})
        out.sort(key=lambda w: w["s"])
        return out, "one mixed recording, speakers labelled by the engine's diarization (words_labeled.json)"
    vad = words_from_voice(date, P)
    if vad:
        return vad, "no word timings from the engine: talking time measured from each person's own recording (silence detection), the line's words spread over it"
    return None, "no word-level timings on disk for this lesson (the page has line start times only)"


def voiced(path, noise="-35dB", gap=0.3):
    """[(start, end)] where this one-person recording has sound (ffmpeg silencedetect)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise}:d={gap}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    total = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else None
    out, t = [], 0.0
    for a, b in zip(ss, se + [total] * (len(ss) - len(se))):
        if a > t + 0.05:
            out.append((t, a))
        t = b or t
    if total and total > t + 0.05:
        out.append((t, total))
    return out


def words_from_voice(date, P):
    """Lessons kept as one recording per person (09-10: docs/lessons/<date>/audio/Amal.mp3 + Medi.mp3, one clock) but with
    no word timings (Medi 2026-09-27: "why do we still have blanks"). Each page line's words are spread evenly over its
    speaker's voiced time between that line and the next line; a line with no voiced time gets 0.3 s per word."""
    adir = os.path.join(DOCS, "lessons", date, "audio")
    tracks = {w: os.path.join(adir, w + ".mp3") for w in ("Amal", "Medi")}
    if not all(os.path.exists(f) for f in tracks.values()) or not shutil.which("ffmpeg"):
        return None
    V = {w: voiced(f) for w, f in tracks.items()}
    L = sorted((p for p in P if not p["chat"] and p["who"] in V), key=lambda p: p["t"])
    out = []
    for i, p in enumerate(L):
        end = L[i + 1]["t"] if i + 1 < len(L) else p["t"] + 30
        segs = [(max(a, p["t"]), min(b, end)) for a, b in V[p["who"]] if b > p["t"] and a < end]
        toks = [t for t in re.split(r"\s+", p["text"].strip()) if t]
        if not toks:
            continue
        tot = sum(b - a for a, b in segs)
        if tot <= 0:
            segs, tot = [(p["t"], p["t"] + 0.3 * len(toks))], 0.3 * len(toks)
        per, k = tot / len(toks), 0
        for a, b in segs:
            x = a
            while x + per <= b + 1e-6 and k < len(toks):
                out.append({"s": x, "e": x + per, "who": p["who"], "text": toks[k], "kind": "word"}); x += per; k += 1
        while k < len(toks):
            out.append({"s": segs[-1][1], "e": segs[-1][1] + 0.01, "who": p["who"], "text": toks[k], "kind": "word"}); k += 1
    out.sort(key=lambda w: w["s"])
    return out or None


def capped(W):
    for w in W or []:
        if w["kind"] == "word" and w["e"] - w["s"] > WORD_MAX:
            w["e"] = w["s"] + WORD_MAX
    return W


def attach_words(P, W):
    """Give each page line an end time = end of the last word it owns (same speaker, latest line start <= word)."""
    if not W:
        for p in P:
            p["end"] = None
        return
    by = {}
    for i, p in enumerate(P):
        if not p["chat"]:
            by.setdefault(p["who"], []).append((p["t"], i))
    for v in by.values():
        v.sort()
    ends = {}
    for w in W:
        L = by.get(w["who"])
        if not L or w["kind"] == "event":
            continue
        ts = [t for t, _ in L]
        tol = 1.0 if P[L[0][1]].get("t_whole_second") else 0.02
        j = bisect.bisect_right(ts, w["s"] + tol) - 1
        if j < 0:
            continue
        i = L[j][1]
        ends[i] = max(ends.get(i, 0), w["e"])
    for i, p in enumerate(P):
        p["end"] = round(ends[i], 2) if i in ends and not p["chat"] else None


# ------------------------------------------------------------------ metrics
def utterances(W, who, lo, hi):
    out, cur = [], None
    for w in W:
        if w["who"] != who or w["kind"] == "event" or w["s"] < lo or w["s"] > hi:
            continue
        if cur and w["s"] - cur["e"] < GLUE:
            cur["e"] = max(cur["e"], w["e"])
            cur["w"].append(w)
        else:
            if cur:
                out.append(cur)
            cur = {"s": w["s"], "e": w["e"], "w": [w], "who": who}
    if cur:
        out.append(cur)
    return out


FILLER_LATIN = {"uh", "um", "umm", "uhm", "uhh", "er", "erm", "eh", "mm", "mmm", "hmm", "hm", "mhm", "ah"}
FILLER_AR = {"ام", "امم", "اممم", "إم", "إمم", "أمم", "أممم", "مم", "ممم", "آآ", "آآآ", "آآآآ", "أآ", "أآآ", "اا", "ااا", "آ", "إه", "اه", "آه", "اهه", "آهه"}
YES_AH = {"اه", "آه"}          # also "yes": counted only mid-turn


def norm_tok(t):
    return re.sub(r"[^\w\u0600-\u06FF]+", "", t.lower()).replace("ـ", "")


def is_filler(tok, pos):
    n = norm_tok(tok)
    if not n:
        return None
    if n in FILLER_LATIN:
        return n
    if re.fullmatch(r"[آاأ]{2,}|[آاأ]?م{2,}|ه?م{2,}", n):
        return "آآ" if n[0] in "آاأ" and "م" not in n else ("امم" if n[0] in "آاأإ" else "ممم")
    if n in FILLER_AR:
        if n in YES_AH and pos == 0:
            return None
        return n
    return None


def metrics(W, lo, hi):
    M = utterances(W, "Medi", lo, hi)
    A = utterances(W, "Amal", lo, hi)
    medi_s = sum(u["e"] - u["s"] for u in M)
    amal_s = sum(u["e"] - u["s"] for u in A)
    talk = {"medi_s": round(medi_s, 1), "amal_s": round(amal_s, 1),
            "speak_pct": round(100 * medi_s / (medi_s + amal_s), 1) if medi_s + amal_s else None,
            "listen_pct": round(100 * amal_s / (medi_s + amal_s), 1) if medi_s + amal_s else None}
    # fillers: Medi only
    counts = {}
    for u in M:
        toks = [w for w in u["w"] if w["kind"] == "word"]
        for i, w in enumerate(toks):
            for j, piece in enumerate(w["text"].replace("،", " ").split()):
                f = is_filler(piece, i + j)
                if f:
                    counts[f] = counts.get(f, 0) + 1
    n = sum(counts.values())
    fillers = {"count": n, "per_min": round(n / (medi_s / 60), 2) if medi_s else None,
               "top": sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:6]}
    # latency: end of Amal's turn -> start of Medi's next turn, when nothing else starts in between
    U = sorted(M + A, key=lambda u: u["s"])
    gaps = []
    for a, b in zip(U, U[1:]):
        if a["who"] == "Amal" and b["who"] == "Medi":
            g = b["s"] - a["e"]
            if 0 <= g <= LAT_MAX:
                gaps.append(g)
    gaps.sort()
    latency = {"median_s": round(median(gaps), 2) if gaps else None,
               "p75_s": round(gaps[int(0.75 * (len(gaps) - 1))], 2) if gaps else None, "n": len(gaps)}
    # flow: Arabic words per minute inside Medi's Arabic turns (>= 2 Arabic words; fillers not counted as words)
    words = mins = 0.0
    nt = 0
    for u in M:
        ar = [w for w in u["w"] if w["kind"] == "word" and AR.search(w["text"]) and not is_filler(w["text"], 1)]
        if len(ar) < 2:
            continue
        words += len(ar)
        mins += (u["e"] - u["s"]) / 60
        nt += 1
    flow = {"wpm": round(words / mins, 1) if mins else None, "n_turns": nt, "arabic_words": int(words)}
    return talk, fillers, latency, flow


# ------------------------------------------------------------------ misc sources
def lesson_start(date):
    d = os.path.join(RAW, date)
    tj = os.path.join(d, "tracks", "tracks.json")
    if os.path.exists(tj):
        tr = J(tj)["tracks"]
        zs = [dt.datetime.fromisoformat(t["start"]["absolute"].replace("Z", "+00:00")) - dt.timedelta(seconds=t["start"]["relative"]) for t in tr]
        z = min(zs).astimezone(dt.timezone(dt.timedelta(hours=-7)))
        return z.isoformat(timespec="seconds"), "tracks.json (recording start = page-audio 0:00)"
    sj = os.path.join(d, "source.json")
    if os.path.exists(sj):
        return J(sj)["start"], "source.json (Meet folder time, minute precision)"
    for k, v in J(os.path.join(REPO, "data", "lessons", "processed.json")).items():
        if v.get("date") == date:
            m = re.search(r"\((\d{4})-(\d\d)-(\d\d) (\d\d) (\d\d) GMT([+-]\d+)\)", k)
            if m:
                off = int(m.group(6))
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:00{off:+03d}:00", "Meet folder name in processed.json (minute precision)"
    return None, "no recording start found"


def audio_duration(date):
    adir = os.path.join(DOCS, "lessons", date, "audio")
    for f in ("lesson.mp3", "Amal.mp3"):
        p = os.path.join(adir, f)
        if os.path.exists(p) and shutil.which("ffprobe"):
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                               capture_output=True, text=True)
            try:
                return float(r.stdout.strip())
            except ValueError:
                pass
    return None


def run_node(strings, sheet=(), slips=None, overrides=None):
    os.makedirs(TMP, exist_ok=True)
    i, o = os.path.join(TMP, "node-in.json"), os.path.join(TMP, "node-out.json")
    json.dump({"arabic": sorted(set(s for s in strings if s)), "sheet": sorted(set(s for s in sheet if s)),
               "taught": [x for v in TAUGHT.values() for x in v], **({"slips": slips} if slips is not None else {}),
               **({"overrides": overrides} if overrides is not None else {})},
              open(i, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run([NODE, os.path.join(HERE, "lessons_page_node.cjs"), i, o], check=True, capture_output=True)
    return J(o)


# ------------------------------------------------------------------ Claude's reading of each lesson
# (type, review_mode, why). Read from the lesson pages + the sweep's per-lesson coverage notes, 2026-09-25.
LESSON_TYPES = {
    "2026-08-25": ("free-speak", None, "Conversation from the tutor's questions (time, clothes, weather, what tires you, fears, fiancee) with fixes as they come; ~4 min of Meet setup talk; no drill."),
    "2026-09-04": ("new-grammar", None, "28:00-1:03:00 (~35 of 63 min) is the first causative/reflexive pair: the tutor teaches how بسط/انبسط conjugate (b- before a root b, past endings, command); 11:00-28:00 is mostly English about AI tools and a honey seller."),
    "2026-09-05": ("new-words", None, "Most of the lesson (~22:00-1:02) drills the new pair زعج/انزعج in past, present and command; 07:00-22:00 reviews بسط/انبسط; first 6 min is app-demo talk."),
    "2026-09-10": ("new-words", None, "27:00-57:00 teaches the new pair كسر/انكسر in every tense; before that ~25 min of conversation and a review of زعج/انزعج; ends with the tutor listing the causative verbs to learn."),
    "2026-09-11": ("new-words", None, "~10:00-1:00:00 drills the new pair خرب/خرّب (past, present, command, 'rots', 'mess up'); the first 10 min is small talk plus a short review of north/darkness/stars words."),
    "2026-09-14": ("review-words", "speaking", "After ~22 min of small talk, the tutor gives English sentences and the student says them in Arabic with the verbs already taught (زعج/انزعج, كسر/انكسر, بسط/انبسط) - 'we're repeating today'; the tutor types each answer in chat."),
    "2026-09-15": ("review-words", "speaking", "Review of the T-verb group (غيّر/تغيّر, صوّر/تصوّر, ذكّر/تذكّر), part of the planned one-group-per-lesson review series; the student already knew them (29:05 he answers what بغير/بتغير mean; T-verb flashcards existed); first 10 min small talk, 10:00-28:00 reviews كسر/انكسر."),
    "2026-09-16": ("review-words", "speaking", "Review series continues: حمّس/تحمّس, وجّع/توجّع, ضايق/تضايق, حرّك/تحرّك in English-to-Arabic sentences (10:36 he had studied the flashcards; 33:25 'just wanted to make sure you remember all of these'); first ~10 min small talk."),
    "2026-09-17": ("review-words", "speaking", "Review: the rest of the T group (تأسف with لـ/من, already used on 08-25), خرب/خرّب (31:57 'we reviewed this a lot') and the doubled-middle verbs (56:02 'I know you know them'); first 14 min small talk."),
    "2026-09-18": ("review-words", "speaking", "Review of the doubled-middle group (زهّق/زهق, تعّب/تعب, زعّل/زعل, خوّف/خاف, ضحّك/ضحك, عصّب) across tenses and persons - all already in his speech on 08-25 (04:42 'رجعت الـ cards؟'); the tutor: 'the best group yet'."),
    "2026-09-19": ("review-words", "listening", "After ~12 min of songs and small talk, the tutor wraps up the verb pairs 'by doing some listening': she says a form, the student says what it means in English; the student's own Arabic is only ~06:30-10:30 and a few drill lines."),
    "2026-09-21": ("free-speak", None, "Conversation and role plays for the whole hour: stress at work, pizza, ordering at a cafe, complaining about food to a manager, how he cooks rice (tahdig), Iranian food abroad."),
    "2026-09-23": ("free-speak", None, "Conversation and role plays: coffee, stomach ache, then booking a hotel room, breakfast, paying, complaining to the manager, booking tickets and appointments, a weekend drive. The student's first ~23 min is not transcribed (the tutor's side only)."),
    "2026-09-28": ("review-words", "speaking", "After ~15 min of app/flashcard talk and a gym story (15:40-25:50), the tutor reviews the people/family/professions cards she gave him (25:55 'شو الـ cards اللي أعطيتك إياهم؟'): family members and their jobs, cousins, relatives, siblings, ages (بنت/صبية/مرة/ختيارة), who works in a company, hospital, salon, school; at 64:57 she plans a grammar review next time and the student asks for 'the L again'."),
    "2026-09-30": ("review-grammar", "speaking", "16:00-65:30 (~50 of 66 min) is the planned el- review (16:52 'حكينا بدنا نراجع ال'; 58:02 'I'm not introducing anything new... just testing'): general nouns (A1), noun + adjective (A7), hada/hadol + el (A10/A10b), idafa with feminine -t and chains (A2/A3/A5), ending with the student explaining the rule back; first 5 min app talk, 05:35-15:50 small talk about yesterday's rug customers."),
    "2026-09-26": ("review-words", "speaking", "Role plays that review words already taught: after small talk (his knee, the app, the date) and a ~2 min drop-out at 18:00, a doctor visit (types of doctor, head ache, medicine, body and face parts, feminine/dual body words, 'my hands' = إيدي) then a clothes shop for a wedding (suit, shirt, shoes, colours, socks, sunglasses). No new verb pair taught. The tutor's first recording (00:00-18:33) is transcribed since 2026-10-02 (TR-17); 18:33-20:17 she was reconnecting (filled from the Meet recording)."),
}

DEFINITIONS = {
    "start_local": "When the recording started, local time with offset. From the Meet recording's tracks.json, its folder name, or source.json. Null if none of these exist.",
    "duration_min": "Length of the lesson audio the page plays, in minutes.",
    "type": "Claude's reading of what the lesson mostly was: free-speak = conversation; review-words = practising words already taught; new-words = the tutor teaching new vocabulary (new verb pairs drilled in all tenses count here); new-grammar = the tutor teaching a rule; review-grammar = the tutor drilling rules already taught (Medi 2026-10-01: Sep 30 was an el- review). One main type; if mixed, the one with the most minutes, and type_why says so. type_source 'claude-read' = the student can correct it.",
    "review_mode": "For review lessons only: listening = the tutor says Arabic, the student gives the meaning; speaking = the student says it in Arabic; both.",
    "words.unique": "How many different Word Bank forms (a verb tense or a plural counts on its own) the student was scored on in this lesson, the lesson audit's word slips included - the same count as Progress > Vocab 'Unique words per lesson'. words.unique_rows = the same by Word Bank row.",
    "words.right": "Scored uses marked correct (same rules as the Word Bank page: its own code is run on docs/data/word-bank-evidence.json + word-bank-review.json).",
    "words.partial": "Scored uses marked partial (he got there with help) - worth half. Includes the audit's 'asked the tutor for the word' rows.",
    "words.wrong": "Scored uses marked incorrect, plus the full audit's word slips (wrong word, wrong form, English for a word she taught).",
    "words.pct": "Word score for the lesson: (right + half of partial) / all scored uses, as a percent. The Word Bank's own weighting.",
    "grammar.uses": "Times the student's Arabic exercised a scored grammar rule in this lesson, right or wrong: the uses docs/data/grammar-usage.json counted, plus every slip the tutor fixed that no counted use within 2 s pairs with (he tried the rule; the counter cannot read turns written in Latin letters). Same formula as the Grammar Console (scripts/grammar_math.py).",
    "grammar.mistakes": "Grammar slips the tutor fixed (voiced or typed) in this lesson: full audit 2026-09-26 speaking rows filed in an approved rule, minus the rows the tutor's notes take out. Includes slips in rules no counter can score (unscored_mistakes).",
    "grammar.scored_mistakes": "The slips that are in scored rules (rules with a usage counter, taught, not a sound).",
    "grammar.unscored_mistakes": "Slips in rules no counter can see his right uses of (e.g. B18): listed and counted as slips, left out of grammar.pct.",
    "grammar.pct": "Share of rule uses that were right: 1 - scored_mistakes / uses, as a percent. Never an estimate: mistakes <= uses by construction.",
    "talk.medi_s": "Seconds the student was talking: his words glued into turns (gaps under 1.2 s), turn lengths added up. Stretches the engine marked '[speaking Arabic]' count as talk.",
    "talk.amal_s": "Same for the tutor.",
    "talk.speak_pct": "The student's share of the talking: medi_s / (medi_s + amal_s).",
    "talk.listen_pct": "The tutor's share of the talking (the time the student was listening to her).",
    "fillers.count": "The student's filled pauses (the technical name: filled pauses, a kind of disfluency) - uh, um, er, eh, mm, hmm, ah, and Arabic ام / امم / آآ / ممم; آه and اه only when they come mid-sentence (at the start they usually mean 'yes'). The engine drops some, so this is a floor.",
    "fillers.per_min": "Filled pauses per minute of the student's own talk time.",
    "fillers.top": "The most frequent ones, with counts.",
    "fillers.in_turns": "How many of those filled pauses the lesson page's own turns (docs/data/lessons/<date>.json) still carry. The early pages (08-25, 09-04, 09-05) were cleaned of fillers, so their turns hold almost none.",
    "fillers.comparable": "True when in_turns is at least half of count, i.e. the page transcript and the engine words agree on how much hesitation was heard. False = a different recording set-up or cleaning step: read per_min against lessons recorded the same way only (shown with '≈' on the Overview tab).",
    "latency.median_s": "Response latency: seconds from the end of the tutor's turn to the start of the student's reply, middle value. Only replies within 15 s; overlaps (he starts before she stops) are left out. A pause is not an error (rule S5) - this is a speed measure only.",
    "latency.p75_s": "Three quarters of his replies started within this many seconds.",
    "latency.n": "How many replies were measured.",
    "flow.wpm": "Speaking flow: Arabic words per minute inside the student's Arabic turns (a turn = words with gaps under 1.2 s; only turns with at least 2 Arabic-script words; filled pauses not counted as words). English-only turns and Latin-script transliterations are left out.",
    "flow.n_turns": "How many of his Arabic turns went into wpm.",
    "new_words": "Only words the tutor (or the student) marked new for this lesson (amal_rules kind='new'). Never guessed from the recording (hard rule 2026-09-05).",
    "taught": "New verbs: the verb pairs the tutor taught in this lesson (the student confirmed 2026-09-25). review = first taught in an earlier lesson. From the hand list TAUGHT, else the same-day reader (LS-01, data/lesson-work/lesson-types/<date>.json).",
    "taught_words": "Other words the tutor introduced as new in this lesson, read from context by the same-day reader (LS-01): shown on the lesson page, never fed to any score.",
    "type_read_by": "Who read the type: hand (LESSON_TYPES in the builder) or the same-day reader (claude -p in review_lesson.py, or an agent by hand). null = not read; the publish guard blocks.",
    "gap_fill": "Stretches where one person's side was missing and was recovered later (scripts/fill_meet_gaps.py): side, lesson-clock window, parts by source, lines added, clock offset + residual, diarization confidence. Those turns carry gap_fill: true and a source: own_track = the person's own recording transcribed late; meet_mixed = Google Meet's mixed recording, also from_meet: true - speakers there are split by the engine, not by separate microphones.",
}


def esc(s):
    return html.escape(str(s or ""), quote=False)


def ar_norm(s):
    s = re.sub(r"[ً-ٰٟـ]", "", s or "")
    return re.sub(r"[أإآ]", "ا", s).replace("ى", "ي").replace("ة", "ه")


def tok_clean(s):
    return re.sub(r"[^\w\u0600-\u06FF\s]+", " ", s or "")


def wrong_token(text, arabic):
    """The token of `text` that is the attempt at `arabic` (closest Arabic-script token)."""
    from difflib import SequenceMatcher
    toks = [t.strip("،؟.,!?-'") for t in re.findall(r"[\w\u0600-\u06FF'-]+", text or "") if AR.search(t)]
    toks = [t for t in toks if t]
    if len(toks) <= 1:
        return toks[0] if toks else (text or "").strip()
    forms = [f.strip() for f in re.split(r"[/،,]", arabic or "") if f.strip()] or [arabic or ""]
    return max(toks, key=lambda t: max(SequenceMatcher(None, ar_norm(t), ar_norm(f)).ratio() for f in forms))


def mark_html(said, token, cls):
    s = said or ""
    i = s.find(token) if token else -1
    if i < 0:
        return esc(s)
    return esc(s[:i]) + f'<mark class="{cls}">' + esc(token) + "</mark>" + esc(s[i + len(token):])


GRAMMAR_PROVISIONAL_MIXED = "re-read, but the recording has no separate microphone track, so almost no line was re-heard"
# Codex final approval round 4: a slip restored from the first read is counted, but nobody has checked it - the card says so
FIRST_READ_NOTE = "From the first read; the new read did not write this slip again. Counted until someone checks it."


def first_read_mark(row):
    """Card fields for a slip that scripts/rehear_rejudge.py kept restored from the first read (audit row "kept":
    "first-read slip ..."): needs_check + the sentence the card shows."""
    return {"first_read": True, "needs_check": True, "check_note": FIRST_READ_NOTE} if str(row.get("kept") or "").startswith("first-read slip") else {}


def first_read_summary(detail):
    """(cards from the first read: grammar, words; how many of them may be the same slip as another card, written in the
    other alphabet). The second number comes from a deliberately LOOSE detector (rehear_rejudge.maybe_same_slip_loose)
    that is used for this label only - never for a score, a uid or a removal."""
    import rehear_rejudge as RR
    g = [dict(e, kind="grammar", t=RR.sec_mmss(e.get("mmss"))) for e in detail.get("grammar_errors") or []]
    w = [dict(e, kind="vocab-A", right=e.get("fix") or e.get("arabic"), t=RR.sec_mmss(e.get("mmss"))) for e in detail.get("vocab_errors") or []]
    twice = 0
    for pool in (g, w):
        for e in pool:
            if e.get("first_read") and any(o is not e and RR.maybe_same_slip_loose(e, o) for o in pool):
                twice += 1
    return sum(1 for e in g if e.get("first_read")), sum(1 for e in w if e.get("first_read")), twice


def method_change(repo=REPO):
    """The newest dated change in how the lesson numbers are counted (data/lesson-work/method-changes.json), or None."""
    p = os.path.join(repo, "data", "lesson-work", "method-changes.json")
    rows = (J(p).get("changes") or []) if os.path.exists(p) else []
    rows = sorted((r for r in rows if r.get("date") and r.get("text")), key=lambda r: r["date"])
    return {k: rows[-1][k] for k in ("date", "text", "why") if rows[-1].get(k)} if rows else None


def build():
    RH.build(REPO)                                 # PG-27: a newly published lesson joins as pending; lesson pages get their mark
    rehear_doc = RH.load(REPO)
    # Full audit 2026-09-26 (two readers + third reader per lesson, reconciled with the 09-24 sweep) is the source of
    # grammar AND vocab errors; it carries a sweep-shaped view so the rest of this builder is unchanged. Falls back to
    # the 09-24 sweep only while the audit file does not exist.
    audit_p = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
    sweep = J(audit_p)["sweep_compat"] if os.path.exists(audit_p) else J(os.path.join(REPO, "data", "grammar-sweep-2026-09-24.json"))
    buckets = {b["id"]: b for b in J(os.path.join(DOCS, "data", "grammar-buckets.json"))["buckets"]}
    usage_p = os.path.join(DOCS, "data", "grammar-usage.json")
    usage = J(usage_p).get("lessons", {}) if os.path.exists(usage_p) else {}
    per_lesson_cov = {p["date"]: p["coverage"] for p in sweep.get("per_lesson", [])}

    # grammar mistakes: speaking rows in an approved bucket; unfiled NEW-B18 rows are B18 (approved 2026-09-24)
    G = {}
    for r in sweep["rows"] + sweep.get("unfiled", []):
        if r.get("mode") != "speaking":
            continue
        b = r.get("bucket") or ("B18" if r.get("new_bucket_group") == "NEW-B18" else None)
        if b not in buckets:
            continue
        # Amal's notes 2026-09-27 (scripts/amal_grammar_notes.py): not taught yet, or not a mistake -> shown, not counted
        G.setdefault(r["date"], []).append({**r, "bucket": b, "_ruling": AMAL.ruling({**r, "bucket": b})})

    import grammar_math
    GT = grammar_math.table((J(usage_p).get("uses", {}) if os.path.exists(usage_p) else {}),
                            [{"bucket": r["bucket"], "date": r["date"], "t": (sec(r.get("t")) if r.get("t") else sec(r.get("t_amal")))}
                             for rs in G.values() for r in rs if not r.get("_ruling")],
                            list(buckets), AMAL.not_taught)
    node = run_node([])
    scored = node["scored"]
    info = node["wordInfo"]
    vocab_fix = {}
    for v in sweep.get("vocab", []):
        vocab_fix.setdefault(v["date"], []).append(v)

    lessons, per = [], {}
    # first lesson each list word shows up in: the earlier of (Word Bank evidence, plain text of any lesson page).
    # Evidence for the early lessons is sparse, so text keeps everyday words (بس, شو) from looking "new" later.
    gap = {d: trim_layers(gapfill_layers(d), page_turns(d)) for d in DATES}   # Meet gap fills (fill_meet_gaps.py), merged as lines
    # TR-18 heard-word overlay (RULES.md S2: the engine's text is kept on the line as "engine", never edited)
    pages = {d: TFX.apply(d, with_gapfill(page_turns(d), gap[d])) for d in DATES}
    for d in DATES:
        for r in TFX.unmatched(d, pages[d]):
            raise SystemExit(f"transcript-fixes.json: {d} {r['t']} {r['who']} '{r['engine_wrote']}' matches no line (the transcript changed?)")
    text_all = {d: " " + " ".join(ar_norm(tok_clean(p["text"])) for p in pages[d] if not p["chat"]) + " " for d in DATES}
    text_amal = {d: " " + " ".join(ar_norm(tok_clean(p["text"])) for p in pages[d] if p["who"] == "Amal" and not p["chat"]) + " " for d in DATES}

    def forms(arabic):
        out = []
        for f in re.split(r"[/،,]", arabic or ""):
            f = re.sub(r"^(أنا|انا|إنت|إنتي|هو|هي|إحنا|إنتو|هم)\s+", "", f.strip())
            f = ar_norm(tok_clean(f)).strip()
            if f:
                out.append(f)
        return out

    def first_text(arabic, where):
        fs = forms(arabic)
        for d in DATES:
            if any(" " + f + " " in where[d] for f in fs):
                return d
        return None
    need_ar = set()
    for date in DATES:
        P = pages[date]
        W, wnote = words_for(date, P)
        fills = gapfill_summary(gap[date])
        if W is not None and gap[date]:                             # the filled side's words join the word stream
            W = sorted(W + gapfill_words(gap[date]), key=lambda w: w["s"])
        W = capped(W)
        attach_words(P, W)
        notes = []
        if fills:
            notes.append("gap fill: " + gapfill_note(fills) + ".")
        dur = audio_duration(date)
        start, start_src = lesson_start(date)
        if start is None:
            notes.append("start time unknown: " + start_src)

        # ---- timing metrics
        talk = fillers = latency = flow = None
        if W:
            lo, hi = 0.0, dur or 1e9
            if date == "2026-09-23":
                # Medi's first recording (0:00-22:37) was never transcribed; measure only where both sides exist
                tr = J(os.path.join(RAW, date, "tracks", "tracks.json"))["tracks"]
                lo = max(t["start"]["relative"] for t in tr if t["participant"].startswith("Medi"))
                mf = [f for f in fills if f["side"] == "Medi" and f["from_s"] <= 1 and f["to_s"] >= lo - 5]
                if mf:                                              # his side of 0:00-23:45 now comes from the Meet recording
                    lo = 0.0
                    notes.append(f"talk, fillers, latency and flow measured over the whole lesson: Medi's side {mf[0]['from']}-{mf[0]['to']} is filled ({gapfill_note(mf)}).")
                else:
                    notes.append(f"talk, fillers, latency and flow measured from {mmss(lo)} on: Medi's first recording (0:00-22:37) has no transcript, so only Amal's side exists before that.")
            talk, fillers, latency, flow = metrics(W, lo, hi)
            talk["window"] = [round(lo, 1), round(min(hi, max(w['e'] for w in W)), 1)]
            if wnote and "silence detection" in wnote:
                talk["estimate"] = True   # no engine word times: speak %, words/min, fillers, wait are estimates
            if wnote:
                notes.append("timings: " + wnote)
            holes = sum(1 for w in W if w["kind"] == "speaking" and w["who"] == "Medi" and w["s"] >= lo)
            if holes:
                notes.append(f"{holes} stretches of Medi's Arabic are '[speaking Arabic]' (engine heard speech, wrote no words): counted as talk time, but their fillers and words are missing from fillers and flow.")
        else:
            notes.append("talk, fillers, latency and flow are null: " + wnote + ".")

        # ---- words (Word Bank rules)
        S = [s for s in scored if s["date"] == date]
        right = sum(1 for s in S if s["points"] == 1)
        part = sum(1 for s in S if s["points"] == .5)
        wrong = sum(1 for s in S if s["points"] == 0)
        n = len(S)
        words = {"unique": len({s["row"] for s in S}), "right": right, "wrong": wrong, "partial": part,
                 "pct": round(100 * (right + .5 * part) / n, 1) if n else None, "scored": n}
        if not n:
            notes.append("no scored word uses for this lesson in the Word Bank evidence (its events are all pending review), so words.pct is null.")

        # ---- grammar
        rt = lambda r: sec(r.get("t")) if r.get("t") else sec(r.get("t_amal"))
        rows = sorted(G.get(date, []), key=lambda r: rt(r) or 0)
        # One formula with the Grammar Console (scripts/grammar_math.py, eng audit 2026-09-29): a fix with no counted use
        # within 2 s is itself a use, rules with no usage counter are shown but kept out of the %, and rules Amal has not
        # taught yet (B14, B15) are out of every total. Replaces uses = detected only / "estimate" = uses / (uses + slips).
        mistakes = sum(1 for r in rows if not r.get("_ruling"))
        gpct = None
        if date not in usage:
            uses = None
            notes.append("grammar uses not yet in docs/data/grammar-usage.json for this lesson; grammar.pct null until the re-run.")
        else:
            gl = grammar_math.lesson(GT, date)
            uses, gpct = gl["uses"], gl["pct"]
            if gl["unscored_mistakes"]:
                notes.append(f"grammar: {gl['unscored_mistakes']} of the {mistakes} slips are in rules no counter can see his right uses of "
                             f"(the console's Unscored rules, e.g. B18); they are listed and counted as slips but left out of grammar.pct.")
        grammar = {"uses": uses, "mistakes": mistakes, "pct": gpct, "estimate": False,
                   **({"scored_mistakes": gl["scored_mistakes"], "unscored_mistakes": gl["unscored_mistakes"]} if uses is not None else {})}
        # Codex / council final approval 2026-10-05: a lesson with no separate microphone track was re-read by the readers
        # but almost none of its lines was re-heard - its Grammar % is provisional and says so wherever it shows.
        if RH.chip(date, rehear_doc)["status"] == "applied-limited":
            grammar["provisional"] = GRAMMAR_PROVISIONAL_MIXED
            notes.append("Grammar % is provisional: " + GRAMMAR_PROVISIONAL_MIXED + ".")

        # ---- new words
        rd = TYPE_READS.get(date)
        typ, mode, why = LESSON_TYPES.get(date) or ((rd["type"], rd.get("review_mode"), rd["why"]) if rd else
                                                     ("free-speak", None, "Not read yet: default until the same-day reader (review_lesson.py, scripts/lesson_type_read.py) reads this lesson. The publish guard blocks while this shows."))
        type_read_by = "hand (LESSON_TYPES)" if date in LESSON_TYPES else (rd.get("read_by") or "reader") if rd else None
        type_summary = (rd or {}).get("summary") if isinstance((rd or {}).get("summary"), dict) else None   # LS-13: the structured reading the page shows
        # AM-19: the reader's taught words show on every lesson it read, hand LESSON_TYPES / TAUGHT dates too (union)
        taught_words = list(rd.get("taught_words") or []) if rd else []
        # HARD RULE (Medi 2026-09-05): "new" = only words Amal (or Medi) marked new for this lesson
        # (amal_rules kind='new') or a Doc diff. Never inferred from "first time on the recording" -
        # that listed words Medi already knew (Medi 2026-09-25).
        new_words = []
        for d_, k in CONFIRMED_NEW:
            if d_ == date:
                wi = info.get(k, {})
                new_words.append({"key": k, "arabic": wi.get("arabic"), "english": wi.get("english"), "t": None, "_ar": wi.get("arabic")})
                need_ar.add(wi.get("arabic"))
        taught = TAUGHT.get(date, [])
        # ---- per-lesson heavy parts
        turns = [{"t": round(p["t"], 2), "end": p["end"], "who": "chat" if p["chat"] else p["who"],
                  **({"typed_by": p["who"]} if p["chat"] else {}), "text": p["text"],
                  **({"engine": p["engine"], "heard": p["heard"]} if p.get("engine") else {}),
                  **({"gap_fill": True, "source": p["source"], "confidence": p.get("confidence"),
                      **({"from_meet": True} if p.get("from_meet") else {})} if p.get("gap_fill") else {})} for p in P]
        med = sorted((p for p in P if p["who"] == "Medi" and not p["chat"]), key=lambda p: p["t"])
        mts = [p["t"] for p in med]
        if fillers is not None:
            # Overview audit 2026-09-27: fillers.count comes from the engine words, but the early lesson pages were cleaned of
            # fillers, so their turns carry almost none (08-25: 16 of 167). A lesson whose turns hold under half the count was
            # recorded or cleaned differently and its per_min is not comparable with the rest.
            in_turns = sum(1 for p in med for i, tok in enumerate(p["text"].replace("،", " ").split()) if is_filler(tok, i))
            fillers["in_turns"] = in_turns
            fillers["comparable"] = (in_turns >= fillers["count"] / 2) if fillers["count"] else True
            if not fillers["comparable"]:
                notes.append(f"fillers: the page turns carry {in_turns} of the {fillers['count']} filled pauses the engine words hold, so fillers.per_min is not comparable with lessons whose pages keep them.")
        verr = []
        for s in sorted((s for s in S if s["points"] == 0), key=lambda s: s["t_start"]):  # Medi 2026-09-25: "helped" (Amal said the word first) is not an error
            i = bisect.bisect_right(mts, s["t_start"] + 0.05) - 1
            said = med[i]["text"] if i >= 0 and s["t_start"] - med[i]["t"] < 60 else (s["said"] or s["text"])
            tok = wrong_token(s["text"], s["arabic"])
            if tok not in said:
                said = s["said"] or s["text"]
            fix = None
            cands = [v for v in vocab_fix.get(date, []) if sec(v.get("t")) is not None and abs(sec(v["t"]) - s["t_start"]) <= 30 and v.get("amal_gave")]
            if cands:
                fix = min(cands, key=lambda v: abs(sec(v["t"]) - s["t_start"]))["amal_gave"]
            clip = s["sentence_audio_url"] or (f"lessons/{date}/clips/{s['legacy_clip']}" if s["legacy_clip"] else None)
            wi = info.get(s["word_key"], {})
            verr.append({"t": round(s["t_start"], 2), "mmss": mmss(s["t_start"]), "kind": "wrong" if s["points"] == 0 else "partial",
                         "label": s["label"], "word_key": s["word_key"], "arabic": s["arabic"],
                         "arabizi": wi.get("house") or wi.get("doc_arabizi"), "english": s["english"],
                         "said": said, "said_html": mark_html(said, tok, "ab-wrong" if s["points"] == 0 else "ab-partial"),
                         "wrong": tok, "tok": s["text"], "fix": fix, "clip": clip, "why": s["reason"], "event_id": s["id"]})
            need_ar.add(said)
        # Words he got right (Medi 2026-09-26: a slider "Errors, Correct, All" on the vocab list). Word Bank uses scored
        # 1 (right) or 0.5 (partial = got there with help), same moment rules as the misses above.
        vok = []
        for s_ in sorted((s_ for s_ in S if s_["points"] >= .5), key=lambda s_: s_["t_start"]):
            said = s_["said"] or s_["text"]
            wi = info.get(s_["word_key"], {})
            vok.append({"t": round(s_["t_start"], 2), "mmss": mmss(s_["t_start"]), "kind": "correct" if s_["points"] == 1 else "partial",
                        "label": "Correct" if s_["points"] == 1 else "Partial · got there with help", "word_key": s_["word_key"],
                        "arabic": s_["arabic"], "arabizi": wi.get("house") or wi.get("doc_arabizi"), "english": s_["english"],
                        "said": said, "said_html": mark_html(said, s_["text"], "ab-correct" if s_["points"] == 1 else "ab-partial"),
                        "clip": s_["sentence_audio_url"] or (f"lessons/{date}/clips/{s_['legacy_clip']}" if s_["legacy_clip"] else None),
                        "why": s_["reason"], "event_id": s_["id"], "tok": s_["text"]})
            need_ar.add(said)
        # Medi 2026-09-25 (decision A): every vocab fix Amal voiced or typed is an error on his page. The audit's vocab-A
        # rows join the Word Bank's scored misses. LS-11 (one ledger, C4): a row within 5 s of a Word Bank miss of the SAME
        # word is the same moment and is folded into that card (its uid kept on it); a different word is its own card.
        # Before 2026-10-02 any miss within 5 s swallowed the row (09-26 10:13 مساعد was lost to a لازم miss at 10:09).
        # The slip's time is `t` (his line), `t_amal` only when `t` is missing.
        for v in sorted(vocab_fix.get(date, []), key=lambda v: sec(v.get("t")) or sec(v.get("t_amal")) or 0):
            tv = sec(v.get("t")) if v.get("t") else sec(v.get("t_amal"))
            if tv is None or v.get("source") != "audit-2026-09-26":
                continue
            # (kill switch ANEES_LEDGER=shadow: the old rule, any miss within 5 s)
            same = next((e for e in verr if not e.get("source") and abs(e["t"] - tv) <= 5 and (LL.same_word(e, v) or LL.mode(REPO) == "shadow")), None)
            if same:
                same.setdefault("folded", []).append(v.get("uid"))
                continue
            asked = v.get("tier") == 0
            verr.append({"t": round(tv, 2), "mmss": v.get("t"), "kind": "asked" if asked else "wrong",
                         "label": ("Asked the tutor for the word" if asked else {1: "Wrong word", 2: "Wrong form", 3: "English for a word she taught"}.get(v.get("tier"), "Word slip")),
                         "word_key": None, "arabic": v.get("amal_gave"), "arabizi": v.get("amal_gave_arabizi"), "english": v.get("english"),
                         "said": v.get("medi_said"), "said_html": mark_html(v.get("medi_said") or "", v.get("wrong") or "", "ab-wrong") if v.get("wrong") else esc(v.get("medi_said") or ""),
                         "wrong": v.get("wrong"), "fix": v.get("amal_gave"), "clip": None, "why": v.get("why"), "event_id": None,
                         "tier": v.get("tier"), "signal": v.get("signal"), "confidence": v.get("confidence"), "source": "audit-2026-09-26", "audit_uid": v.get("uid"),
                         "t_fix": sec(v.get("t_amal")) if v.get("t_amal") else None,
                         **first_read_mark(v),
                         **({"correction": v["correction"]} if v.get("correction") else {})})
            need_ar.add(v.get("medi_said") or "")
        verr.sort(key=lambda e: e["t"])
        # The audit's slips count in the word score too (Medi 2026-09-26: "35 errors ... 0 wrong?"). Tiers 1-3 = wrong;
        # "asked Amal for the word" = partial (he got there with help). Word Bank misses are already in the counts.
        aw = sum(1 for e in verr if e.get("source") == "audit-2026-09-26" and e["kind"] == "wrong")
        ap = sum(1 for e in verr if e.get("source") == "audit-2026-09-26" and e["kind"] == "asked")
        if aw or ap:
            words["wrong"] += aw; words["partial"] += ap; words["scored"] += aw + ap
            words["audit_wrong"], words["audit_partial"] = aw, ap
            words["pct"] = round(100 * (words["right"] + .5 * words["partial"]) / words["scored"], 1)
        gerr = []
        for r in rows:
            b = buckets.get(r["bucket"], {})
            gerr.append({"t": rt(r), "mmss": r.get("t") or r.get("t_amal"), "t_fix": sec(r["t_amal"]) if r.get("t_amal") else None,
                         "bucket": r["bucket"], "bucket_name": b.get("name"), "mistake": r.get("mistake"),
                         "said": r.get("medi_said"), "said_arabizi": r.get("medi_said_arabizi"),
                         "fix": r.get("amal_said"), "fix_arabizi": r.get("amal_said_arabizi"),
                         "chat": r.get("chat"), "wrong": r.get("wrong"), "wrong_arabizi": r.get("wrong_arabizi"),
                         "right": r.get("right"), "right_arabizi": r.get("right_arabizi"),
                         "confidence": r.get("confidence"), "signal": r.get("signal"), "id": r.get("id"),
                         **first_read_mark(r),
                         **({"correction": r["correction"]} if r.get("correction") else {}),
                         **({"counted": False, "not_counted_kind": r["_ruling"]["kind"],
                             "not_counted_why": r["_ruling"]["why"]} if r.get("_ruling") else {})})
        # Amal's notes 2026-09-27: rows her notes take out of the count get their own list (shown, never counted)
        gnc = [g for g in gerr if g.get("counted") is False]
        gerr = [g for g in gerr if g.get("counted") is not False]
        marks = sorted([{"t": v["t"], "kind": "vocab", "wrong": v["wrong"], "right": v["fix"] or v["arabic"]} for v in verr if v["kind"] == "wrong" and v.get("wrong")] +
                       [{"t": g["t"], "kind": "grammar", "wrong": g["wrong"], "right": g["right"]} for g in gerr if g["wrong"]],
                       key=lambda m: m["t"])
        try:                                # PG-40 (Medi 2026-10-09): the English of each Arabic line, under it
            import translate_lines as TRL
            TRL.attach(date, turns)
        except Exception as e:  # noqa: BLE001 - a missing translation never stops a build
            print("translate_lines: not attached (%s)" % type(e).__name__)
        per[date] = {"date": date, "clock": "seconds on the lesson page audio (docs/lessons/%s/audio/...)" % date,
                     "turns": turns, "vocab_errors": verr, "vocab_correct": vok, "grammar_errors": gerr,
                     "grammar_not_counted": gnc, "marks": marks}

        # how the speakers and word times were obtained (scripts/accuracy_gates.py: pitch-guessed or diarized speakers
        # and estimated timings keep a lesson out of the verified totals)
        wn = wnote or ""
        source = {"attribution": "pitch-guess" if "voice pitch" in wn else "diarized-mixed" if "diarization" in wn else "per-speaker-tracks",
                  "timing": "estimated" if "silence detection" in wn else "none" if not W else "engine"}
        lessons.append({
            "date": date, "start_local": start, "start_source": start_src, "source": source,
            "duration_min": round(dur / 60, 1) if dur else None,
            "type": typ, "review_mode": mode, "type_why": why, "type_source": "claude-read", "type_read_by": type_read_by,
            **({"summary": type_summary} if type_summary else {}),
            "words": words, "grammar": grammar, "talk": talk, "fillers": fillers, "latency": latency, "flow": flow,
            "new_words": new_words, "taught": taught, "taught_words": taught_words, "coverage": ((per_lesson_cov.get(date) + " / ") if per_lesson_cov.get(date) and fills else (per_lesson_cov.get(date) or "")) + (gapfill_note(fills) + "." if fills else "") or None,
            **({"gap_fill": fills} if fills else {}), "notes": notes,
            "page": f"lessons/{date}.html", "detail": f"data/lessons/{date}.json",
            "rehear": RH.chip(date, rehear_doc),          # PG-27: second listen pending / sent / to review / applied
            "counts": {"turns": sum(1 for p in P if not p["chat"]), "chat_lines": sum(1 for p in P if p["chat"]),
                       **({"gap_fill": sum(1 for p in P if p.get("gap_fill")), "from_meet": sum(1 for p in P if p.get("from_meet"))} if fills else {}),
                       "vocab_errors": len(verr), "vocab_correct": len(vok),
                       "grammar_errors": len(gerr), "grammar_not_counted": len(gnc)},
        })

    # Amal's spelling for the new words and the said-sentences (display only, rule S1)
    NO = run_node(sorted(x for x in need_ar if x), [e["arabic"] + "" + (e.get("english") or "") for v in per.values() for e in v["vocab_errors"] if not e.get("word_key")])
    az = NO["arabizi"]
    for L in lessons:
        for x in L["new_words"]:
            wi = info.get(x["key"], {})
            x["arabizi"] = wi.get("house") or wi.get("doc_arabizi") or (az.get(x["_ar"]) or {}).get("text")
            x.pop("_ar")
    for d, v in per.items():
        for e in v["vocab_correct"]:
            e["said_arabizi"] = (az.get(e["said"]) or {}).get("text")
            e["on_sheet"], e["rating"] = True, NO["ratings"].get(e["word_key"])
        for e in v["vocab_errors"]:
            r = az.get(e["said"]) or {}
            e["said_arabizi"] = r.get("text")
            # sheet + rating: a Word Bank miss is a sheet word by definition; an audit row is looked up by the word Amal gave
            if e.get("word_key"):
                e["on_sheet"], e["rating"] = True, NO["ratings"].get(e["word_key"])
            else:
                sh = NO["sheet"].get((e.get("arabic") or "") + "" + (e.get("english") or "")) or {}
                e["on_sheet"], e["rating"], e["sheet_key"] = bool(sh.get("on_sheet")), sh.get("rating"), sh.get("key")
                e["keyed_by"] = "auto-" + str(sh.get("match")) if sh.get("key") else None
                # TR-23 (Medi 2026-10-03 "ashar3a (i got wrong and amal corrected)"): a reader row whose word Amal gave is in
                # LATIN letters ('3ashara') never matched her Arabic list; match it by sound against her own Arabizi spellings
                # (3ashrah) - one list word only, never a guess between two
                if not sh.get("key") and re.fullmatch(r"[A-Za-z0-9' -]+", e.get("arabic") or ""):
                    k = sound_key(e["arabic"])
                    if k:
                        e["on_sheet"], e["sheet_key"], e["rating"], e["keyed_by"] = True, k, NO["ratings"].get(k), "auto-sound"
    # Hand verdicts win over the automatic sheet check (Medi 2026-09-27 "use context and meanings both ways"): a reader
    # judged each word against his list by meaning -> data/lesson-work/sheet-verdicts.json [{date, mmss, arabic, verdict}].
    vp = os.path.join(REPO, "data", "lesson-work", "sheet-verdicts.json")
    VD = hand_verdicts(J(vp) if os.path.exists(vp) else [])
    # 2026-09-27 overnight audit: every card judged (on_list / new / not_an_error). on_list carries the list word's key,
    # which the rating uses. not_an_error = the transcript shows he said it right (or it was not his slip): the card leaves
    # vocab_errors and the Words %, and is kept under "not_errors" with the reason.
    for d, v in per.items():
        keep, dropped = [], []
        for e in v["vocab_errors"]:
            x = VD(d, e.get("mmss"), e.get("arabic"))
            if x and x.get("verdict") in ("not_an_error", "duplicate"):   # duplicate = the same slip already counted once
                e["verdict_reason"] = x.get("reason")
                dropped.append(e)
                continue
            if x and x.get("verdict") in ("on_list", "new"):
                e["on_sheet"] = x["verdict"] == "on_list"
                e["sheet_reason"] = x.get("reason")
                if x["verdict"] == "new":
                    e["rating"] = None
                elif x.get("list_key") and not e.get("word_key") and x["list_key"] != e.get("sheet_key"):
                    e["sheet_key"], e["rating"] = x["list_key"], NO["ratings"].get(x["list_key"])
                if x["verdict"] == "on_list" and x.get("list_key") and not e.get("word_key"):
                    e["keyed_by"] = "reader"
            keep.append(e)
        v["vocab_errors"], v["not_errors"] = keep, dropped
        v["marks"] = [m for m in v["marks"] if m["kind"] != "vocab" or any(abs(m["t"] - e["t"]) < .01 for e in keep)]
        L = next(L for L in lessons if L["date"] == d)
        L["counts"]["vocab_errors"] = len(keep)
        if dropped:
            w = L["words"]
            for e in dropped:
                if e.get("source") == "audit-2026-09-26":
                    if e["kind"] == "wrong":
                        w["wrong"] -= 1; w["audit_wrong"] = w.get("audit_wrong", 0) - 1
                    else:
                        w["partial"] -= 1; w["audit_partial"] = w.get("audit_partial", 0) - 1
                else:
                    w["wrong"] -= 1
                w["scored"] -= 1
            w["not_an_error"] = len(dropped)
            w["pct"] = round(100 * (w["right"] + .5 * w["partial"]) / w["scored"], 1) if w["scored"] else None
            L["notes"].append(f"{len(dropped)} word card(s) dropped after the 2026-09-27 hand check (he said it right, it was not his slip, or it repeats a slip already counted): "
                              + "; ".join(f"{e['mmss']} {e.get('arabic')}" for e in dropped) + ".")
    # WS-28 (Medi 2026-10-02 "its a new word but I still got mitshaje3a wrong here"): a word Amal taught in an EARLIER
    # lesson (that lesson's taught words, LS-08) is a word he has been given: a slip on it is scored even before she adds it
    # to her Doc. A word taught the same day stays new (WS-18).
    import transcript_marks as _TMW

    def _tn(s):
        return _TMW.normalise(re.sub(r"\([^)]*\)", " ", str(s or "")))[0].replace("ال", "", 1).strip()
    for d, v in per.items():
        earlier = [(dd, w) for dd, tr in TYPE_READS.items() if dd < d for w in ((tr or {}).get("taught_words") or (tr or {}).get("taught") or [])
                   if isinstance(w, dict) and w.get("arabic")]
        for e in v["vocab_errors"]:
            if e.get("on_sheet") is not False or e.get("sheet_reason"):
                continue
            want = {_tn(x) for x in re.split(r"\s*/\s*", str(e.get("fix") or e.get("arabic") or "")) if _tn(x)}
            hit = next(((dd, w) for dd, w in earlier if _tn(w["arabic"]) in want), None)
            if hit:
                e["on_sheet"], e["keyed_by"] = True, "taught-earlier"
                e["sheet_reason"] = "The tutor taught %s (%s) on %s - scored as a word you were given (WS-28)" % (
                    hit[1].get("latin") or hit[1]["arabic"], hit[1].get("english") or "", hit[0])
    # A word not on her sheet is not his miss (Medi 2026-09-26: "a new word that's not on the document") - it is listed,
    # tagged "Not on sheet", sent to Amal's review, and left out of the Words %.
    for L in lessons:
        V = per[L["date"]]["vocab_errors"]
        off = [e for e in V if e.get("on_sheet") is False]
        offa = [e for e in off if e.get("source") == "audit-2026-09-26"]
        w = L["words"]
        if off:
            w["wrong"] -= sum(1 for e in off if e["kind"] == "wrong"); w["partial"] -= sum(1 for e in off if e["kind"] == "asked")
            w["scored"] -= len(off); w["not_on_sheet"] = len(off)
            w["audit_wrong"] = w.get("audit_wrong", 0) - sum(1 for e in offa if e["kind"] == "wrong")
            w["audit_partial"] = w.get("audit_partial", 0) - sum(1 for e in offa if e["kind"] == "asked")
            w["pct"] = round(100 * (w["right"] + .5 * w["partial"]) / w["scored"], 1) if w["scored"] else None


    # ---- LS-11 one lesson ledger (Medi 2026-10-02: the marked transcript is the one source of every judgment). Every
    # producer's items above become marks on the transcript turns (scripts/lesson_ledger.py); where two producers judged
    # the same moment differently the existing rules decide (lesson_ledger.PRECEDENCE) or it is a "Medi?" moment counted
    # as before. The lists below are then rewritten from the ledger and every number on the page is the ledger's count.
    # ANEES_LEDGER=shadow builds the ledger and its diff but applies no resolution (the old counts), for a bad hour.
    # the kill switch: ANEES_LEDGER=shadow, or "mode": "shadow" in data/lesson-work/ledger-rulings.json (one line anyone
    # can commit, read by the hourly job too)
    LMODE = LL.mode(REPO)
    U0 = J(usage_p) if os.path.exists(usage_p) else {}
    try:                                    # WS-29: the Doc words of his own corrections are Word Bank events too
        import heard_credits as HC
        HC.refresh(log=lambda *a: print(*a))
    except Exception as e:  # noqa: BLE001 - never stops a build; the credits wait for the next one
        print("heard_credits: not refreshed (%s)" % type(e).__name__)
    COVER = {}
    try:   # WS-30 / WS-31 (Medi 2026-10-09): every Arabic word of his judged; a repeat of the tutor's fix is not credited
        import word_coverage as WC
        _toks = WC.tokens_for_sheet(per)
        _SH = run_node([], sheet=[t + "" for t in _toks])["sheet"] if _toks else {}
        _offs = {d: [(sec(o.get("from")), sec(o.get("to"))) for o in ((TYPE_READS.get(d) or {}).get("off_lesson") or [])
                     if isinstance(o, dict) and sec(o.get("from")) is not None and sec(o.get("to")) is not None] for d in per}
        COVER = WC.refresh(per, {t: _SH.get(t + "") or {} for t in _toks}, _offs, log=lambda *a: print(*a))
        WC.ensure_clips(log=lambda *a: print(*a))     # the Word Bank audit needs a playable clip for every word event
    except Exception as e:  # noqa: BLE001 - never stops a build; the words wait for the next one (the guard's coverage test fails)
        import traceback
        traceback.print_exc()
        print("word_coverage: not refreshed (%s)" % type(e).__name__)
    patches = (J(os.path.join(DOCS, "data", "word-bank-review.json")).get("patches") or {})
    EV = {e["id"]: e for e in J(os.path.join(DOCS, "data", "word-bank-evidence.json")).get("events", [])}
    for _a in J(os.path.join(DOCS, "data", "word-bank-review.json")).get("additions", []):
        EV.setdefault(_a["event"]["id"], _a["event"])        # events the review overlay adds
    rulings = LL.load_rulings()
    scored_rules = {b for b, r in GT.items() if r["scored"]}
    # "before" = what the live site shows (origin/master's lessons.json), else the last local build
    prev_p = os.path.join(DOCS, "data", "lessons.json")
    try:
        _live = subprocess.run(["git", "show", "origin/master:docs/data/lessons.json"], cwd=REPO, capture_output=True,
                               encoding="utf-8", check=True).stdout
        published = {x["date"]: x for x in json.loads(_live).get("lessons", [])}
    except Exception:
        published = {x["date"]: x for x in (J(prev_p).get("lessons", []) if os.path.exists(prev_p) else [])}
    ledgers, fold_uses_all = {}, []
    word_credit_conflicts = []
    _orp = os.path.join(REPO, "data", "lesson-work", "rehear", "rejudge", "owner-review.json")
    OWNER_REVIEW = (J(_orp).get("items") or []) if os.path.exists(_orp) else []
    for L in lessons:
        d, v = L["date"], per[L["date"]]
        led, act = LL.build(d, v, U0.get("uses", {}), buckets, scored_rules, AMAL.not_taught, U0.get("ruled_out", []),
                            U0.get("not_uses_auto", []), patches, rulings, resolve=LMODE != "shadow")
        ids = {"vocab_correct": dict(zip(LL.item_ids(v["vocab_correct"], "wb:", "event_id"), v["vocab_correct"])),
               "vocab_errors": {**dict(zip(LL.item_ids([e for e in v["vocab_errors"] if e.get("source") != "audit-2026-09-26"], "wb:", "event_id"),
                                           [e for e in v["vocab_errors"] if e.get("source") != "audit-2026-09-26"])),
                                **{"ra:" + e["audit_uid"]: e for e in v["vocab_errors"] if e.get("source") == "audit-2026-09-26"}}}
        ids["grammar_errors"] = {"rg:" + g["id"]: g for g in v["grammar_errors"]}
        for lst, mid, why, rule in act["move"]:
            if mid not in ids[lst] and lst in ("vocab_correct", "vocab_errors"):      # a Word Bank partial lives in either list
                lst = "vocab_errors" if lst == "vocab_correct" else "vocab_correct"
            e = ids[lst][mid]
            if lst == "grammar_errors":          # Medi said the slip is a word slip: the grammar card is shown apart, not counted
                v[lst] = [x for x in v[lst] if x is not e]
                e.update(counted=False, not_counted_kind="ledger", not_counted_why=why, ledger_rule=rule)
                v["grammar_not_counted"].append(e)
                continue
            v[lst] = [x for x in v[lst] if x is not e]
            e.update(verdict_reason=why, ledger_rule=rule, ledger_id=mid)
            v.setdefault("not_errors", []).append(e)
        led["overrides"] = []
        for o in act["overrides"]:
            ev = EV.get(o["event_id"]) or {}
            led["overrides"].append({**o, "expected": {"word_key": ev.get("word_key"), "t_start": ev.get("t_start")}})
        led["fold_uses"] = act["fold_uses"]
        fold_uses_all += act["fold_uses"]
        ledgers[d] = led
        c = led["counts"]
        w = L["words"]
        old = dict(w)
        for k in ("right", "partial", "wrong", "scored", "pct", "audit_wrong", "audit_partial"):
            w[k] = c["words"][k]
        # Codex final approval 2026-10-05, blocker 3: Word Bank marks an earlier review had scored on a word the second
        # listen no longer hears - their own state, scored neither way, listed one by one (word_credit_conflicts below)
        owner = [x for x in OWNER_REVIEW if x["date"] == d]
        if owner:
            L["owner_review"] = [{"mmss": x["mmss"], "earlier_uid": x["earlier"]["uid"], "amal": x["earlier"]["amal"], "new": [n["uid"] for n in x["new_rows"]]} for x in owner]
            L["notes"].append(f"{sum(len(x['new_rows']) for x in owner)} question(s) of the new read sit at a moment Amal already ruled on "
                              f"({', '.join(x['mmss'] for x in owner)}): they wait for Medi, not for her (owner-review.json).")
        fg, fw, twice = first_read_summary(v)
        if fg or fw:
            g_, w_ = L["grammar"], L["words"]
            g_["first_read_cards"], w_["first_read_cards"] = fg, fw
            L["notes"].append(f"{fg + fw} slip(s) here come from the first read only ({fg} grammar, {fw} word): the new read did not write them "
                              f"again. They are counted until someone checks them, so Grammar % and Words % are not exact.")
            if fg:
                why = f"{fg} of its slips come from the first read only and wait for a check"
                g_["provisional"] = (g_["provisional"] + "; " + why) if g_.get("provisional") else why
            if twice:
                g_["maybe_counted_twice"] = twice
                L["notes"].append(f"{twice} slips may be counted twice (same slip written in Arabic and in English letters).")
        held = [m for m in led["marks"] if m.get("state") == LL.REHEAR_CONFLICT]
        w["rehear_word_conflicts"] = len(held)
        for m in held:
            word_credit_conflicts.append({"date": d, "t": m["t"], "mmss": LL.mmss(m["t"]), "word": m.get("tok"), "word_key": m.get("word_key"),
                                          "list_word": m.get("arabic"), "was": m.get("was"), "state": "not scored (needs a look)",
                                          "old_line": (m.get("rehear") or {}).get("old_line"), "new_line": (m.get("rehear") or {}).get("new_line"),
                                          "engine_wrote": (m.get("rehear") or {}).get("engine_wrote"), "second_listen": (m.get("rehear") or {}).get("heard"),
                                          "earlier_review": (m.get("rehear") or {}).get("review"), "event_id": m["by"]["ref"], "mark": m["id"]})
        if held:
            L["notes"].append(f"{len(held)} word mark(s) an earlier review had scored are not scored now: the second listen no longer hears "
                              f"the word on that line, and nobody has looked yet ({', '.join(LL.mmss(m['t']) for m in held)}).")
        if LMODE == "shadow" and any(old[k] != w[k] for k in ("right", "partial", "wrong", "scored")):
            raise SystemExit(f"{d}: the ledger in shadow mode counts {w} but the lists give {old} (a producer item has no mark)")
        g = L["grammar"]
        g["mistakes"] = c["grammar"]["mistakes"]
        if g.get("uses") is not None:
            g.update(uses=c["grammar"]["uses"], pct=c["grammar"]["pct"], scored_mistakes=c["grammar"]["scored_mistakes"],
                     unscored_mistakes=c["grammar"]["unscored_mistakes"])
        res = [x for x in led["conflicts"] if x.get("resolved")]
        L["ledger"] = {"file": f"data/lesson-work/ledger/{d}.json", "marks": len(led["marks"]), "conflicts": len(led["conflicts"]),
                       "resolved": len(res), "needs_medi": len(led["needs_medi"]), "mode": LMODE,
                       "items": [LL.medi_item(led, x) for x in led["conflicts"] if x["id"] in led["needs_medi"]]}
        for it in L["ledger"]["items"]:                 # the rule's plain name, not its code (Medi reads it)
            if it["b"].get("bucket"):
                it["b"]["bucket_name"] = (buckets.get(it["b"]["bucket"]) or {}).get("name")
        if res:
            L["notes"].append(f"one ledger (LS-11): {len(res)} moment(s) where two judges disagreed were settled by the existing rules: "
                              + "; ".join(f"{x['mmss']} {LL.KIND_WORDS[x['kind']]}" for x in res) + ".")
        if led["needs_medi"]:
            L["notes"].append(f"{len(led['needs_medi'])} moment(s) wait for Medi (counted as before until he picks): "
                              + "; ".join(x["mmss"] for x in led["conflicts"] if x["id"] in led["needs_medi"]) + ".")
        L["counts"]["vocab_errors"], L["counts"]["vocab_correct"] = len(v["vocab_errors"]), len(v["vocab_correct"])
        v["marks"] = [m for m in v["marks"] if m["kind"] != "vocab" or any(abs(m["t"] - e["t"]) < .01 for e in v["vocab_errors"])]
    _wcc = os.path.join(REPO, "data", "lesson-work", "rehear", "rejudge", "word-credit-conflicts.json")
    if os.path.isdir(os.path.dirname(_wcc)):
        with open(_wcc, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"about": "Word Bank marks that an earlier review (word-bank-review.json) had scored, on a word the second listen "
                                "(TR-22) no longer hears on that line. Each is its own ledger state (rehear-word-conflict): scored neither "
                                "right nor wrong, left out of Words %, until someone looks. Generated by scripts/build_lessons_page_data.py "
                                "(scripts/lesson_ledger.py); never edit by hand.",
                       "count": len(word_credit_conflicts), "rows": word_credit_conflicts}, f, ensure_ascii=False, indent=1)
            f.write("\n")
    # self-check: the console's formula with the same folded uses gives the ledger's grammar numbers
    GT2 = grammar_math.table(LL.uses_minus(J(usage_p).get("uses", {}) if os.path.exists(usage_p) else {}, fold_uses_all),
                             [{"bucket": r["bucket"], "date": r["date"], "t": (sec(r.get("t")) if r.get("t") else sec(r.get("t_amal")))}
                              for rs in G.values() for r in rs if not r.get("_ruling")], list(buckets), AMAL.not_taught)
    for L in lessons:
        if L["grammar"].get("uses") is None:
            continue
        gl = grammar_math.lesson(GT2, L["date"])
        if (gl["uses"], gl["pct"]) != (L["grammar"]["uses"], L["grammar"]["pct"]):
            raise SystemExit(f"{L['date']}: ledger grammar {L['grammar']['uses']} uses / {L['grammar']['pct']}% but grammar_math gives {gl['uses']} / {gl['pct']}%")

    # Eng audit 2026-09-29 (Medi's decision 6, one truth). The audit's on-list word slips join the Word Bank evidence as
    # events (docs/data/word-bank-audit-slips.json, loaded by the Word Bank, Progress and this builder), so every page
    # scores the same attempts. Ratings on the cards are the Word Bank's own status with those slips in it. This replaces
    # the builder's private re-rating (merged(): bands without the Word Bank's streak rules), which made 249 words show
    # one status on the Lessons page and another on the Word Bank (Medi 2026-09-26: the rating must count the slips).
    slips = []
    for L in lessons:
        for e in per[L["date"]]["vocab_errors"]:
            if e.get("source") == "audit-2026-09-26" and e.get("on_sheet"):
                slips.append({"uid": e.get("audit_uid"), "date": L["date"], "t": e["t"], "key": e.get("sheet_key") or e.get("word_key"),
                              "kind": "wrong" if e["kind"] == "wrong" else "asked", "said": e.get("said"), "wrong": e.get("wrong"),
                              "why": e.get("why"), "keyed_by": e.get("keyed_by")})
    overrides = [o for led in ledgers.values() for o in led["overrides"]]
    NO2 = run_node([], slips=slips, overrides=overrides)
    SL = NO2["slips"]
    unplaced = {x["uid"]: x["why"] for x in SL["unplaced"]}
    # RULE CONFLICT (eng audit 2026-09-29, for Medi): a slip whose list word is a preposition (7: مع, عند, قبل, زي, فوق)
    # counts in the Lessons Words % (decision A 2026-09-25 + on-list verdicts 2026-09-27: every on-list error card is in
    # the %), but the Word Bank never scores a preposition (SESSION-DECISIONS 2026-09-21: prepositions are grammar). Not
    # picked silently: the card stays counted here, the Word Bank leaves it out, and the slips file lists it (counted).
    for v in per.values():
        for e in v["vocab_errors"] + v["vocab_correct"]:
            k = e.get("sheet_key") or e.get("word_key")
            if e.get("on_sheet") is False:
                continue
            e["rating"] = NO2["ratings"].get(k) if k else None
            if e.get("audit_uid") in unplaced:
                e["word_bank_note"] = "not in the Word Bank: " + unplaced[e["audit_uid"]]
    # "N words" on the Lessons page = distinct Word Bank forms he was scored on, slips included: the same count as
    # Progress › Vocab "Unique words per lesson" (it counted forms, the Lessons page counted rows: 09-10 64 vs 63).
    for L in lessons:
        S2 = [x for x in NO2["scored"] if x["date"] == L["date"]]
        L["words"]["unique"] = len({x["entry"] for x in S2})
        L["words"]["unique_rows"] = len({x["row"] for x in S2})
    with open(os.path.join(DOCS, "data", "word-bank-audit-slips.json"), "w", encoding="utf-8") as f:
        json.dump({"updated": dt.datetime.now().astimezone().isoformat(timespec="seconds"), **SL}, f, ensure_ascii=False, indent=1)
    print("word slips into the Word Bank:", len(SL["events"]), "| not placed:", len(SL["unplaced"]), [(x["date"], x["uid"], x["why"]) for x in SL["unplaced"]])

    # PG-20 transcript marks (scripts/transcript_marks.py): every scored item on the turn it was said in, Amal's fix
    # line linked to it, the wrong / right words underlined. Precomputed here so the page stays fast.
    import transcript_marks as TM
    U = J(usage_p) if os.path.exists(usage_p) else {}
    for d, v in per.items():
        v["tmarks"], v["marks_report"] = TM.build(d, v, U.get("uses", {}), buckets, AMAL.not_taught,
                                                  U.get("ruled_out", []), U.get("not_uses_auto", []),
                                                  (TYPE_READS.get(d) or {}).get("off_lesson") or [], ledger=ledgers.get(d))
        if d in COVER:
            v["tmarks"] = TM.add_coverage_one(v["tmarks"], v["marks_report"],
                                              WC.chips(d, v, COVER[d], [x for x in NO2.get("unscored") or [] if x.get("date") == d]), v["turns"])
        r = v["marks_report"]
        print(f"transcript marks {d}: {r['placed']}/{r['scored']} placed ({r['rate']}%), Amal fixes {r['fix_placed']}/{r['fix_wanted']}, "
              f"underlines {r['ul_exact']} exact + {len(r['ul_closest'])} closest + {len(r['ul_none'])} none of {r['ul_wanted']}"
              + (f", {r['quiet']} quiet grey kept off the page (PG-43)" if r.get("quiet") else ""))
    for d, led in ledgers.items():
        LL.write(led)
    # LS-12 (Medi 2026-10-02 "1-6 put for amal on her list"): the open questions about Arabic words are cards on Amal's
    # Tutor hub (docs/js/hub/ledger-task.js); the ones she answered stay listed with Undo
    amal_q = J(LL.AMAL_P).get("rulings", []) if os.path.exists(LL.AMAL_P) else []
    amal_by = {r["conflict"]: r for r in amal_q}
    cards, done_cards = [], []
    # the hold (scripts/amal_hold.py): a question that rests on a row the 2026-10-04 re-read created, or that was not on
    # her list before it, is not put on Amal's hub until Medi's OK; it stays open in the ledger. No hold file = no skip.
    import amal_hold
    HOLD = amal_hold.Hold()
    RULED = amal_hold.AlreadyRuled()      # round 5: a card resting on a re-read row at a moment she already ruled on goes to the owner, not to her
    held_card = lambda c, d: HOLD.blocks("ledger", c["id"], date=d) or any(HOLD.uid(str(m).split(":", 1)[-1]) for m in c.get("marks") or [])
    _held_by_hold = held_card
    held_card = lambda c, d: _held_by_hold(c, d) or any(RULED.uid(str(m).split(":", 1)[-1]) for m in c.get("marks") or [])  # noqa: E731
    for d, led in sorted(ledgers.items()):
        for c in led["conflicts"]:
            if c.get("ask") != "amal" or c.get("group"):
                continue
            if c["id"] in led["needs_medi"]:
                if held_card(c, d):
                    continue
                cards.append(LL.amal_item(d, led, c))
            elif c["id"] in amal_by:
                r = amal_by[c["id"]]
                done_cards.append(LL.amal_item(d, led, c, {"kind": "ledger_pick", "answer": r["answer"], "at": r.get("at")}))
    # PR-15 council 2: Medi's "my Arabic was right" is Amal's call - one card each, counted as before until she taps
    import medi_corrections as MC
    for card in MC.amal_cards(MC.J(os.path.join(REPO, "data", "lesson-work", "medi-corrections-report.json")) or {}):
        (done_cards if card.get("answered") else cards).append(card)
    with open(os.path.join(DOCS, "data", "amal-ledger.json"), "w", encoding="utf-8") as f:
        json.dump({"about": "Moments where two of Anees' judges disagree about one of the student's Arabic words (LS-11/LS-12). The tutor's tap "
                            "settles each: amal_rules source 'review', word_key = the item id, kind 'ledger_pick', payload.answer.",
                   "items": cards, "answered": done_cards}, f, ensure_ascii=False, indent=1)
    import tutor_scope       # AM-28 (Medi 2026-10-10): open cards of lessons before TUTOR_FROM are paused, never deleted
    tutor_scope.scope_file(os.path.join(DOCS, "data", "amal-ledger.json"), tutor_scope.answered_keys())
    LL.write_diff(published, lessons, ledgers)
    os.makedirs(os.path.join(DOCS, "data", "lessons"), exist_ok=True)
    for d, v in per.items():
        with open(os.path.join(DOCS, "data", "lessons", d + ".json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, separators=(",", ":"))
    out = {"updated": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "method": __doc__.strip().split("\n\n", 1)[1] if "\n\n" in __doc__ else __doc__,
           "definitions": DEFINITIONS, **({"method_change": method_change()} if method_change() else {}), "lessons": lessons}
    with open(os.path.join(DOCS, "data", "lessons.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    # release layer (Medi 2026-09-27): reader agreement, source coverage, checks, grammar denominator -> verified or not,
    # with the reasons; lessons.json gains release / coverage_by_person / eligible-excluded-pending (scripts/accuracy_gates.py)
    sys.path.insert(0, HERE)
    # the Word Bank audit applies the ledger's overrides too (LS-11): re-run it so its counts follow this build
    wa = subprocess.run([NODE, os.path.join(HERE, "audit_word_bank_reliability.cjs"), os.path.join(DOCS, "data", "word-bank-evidence.json")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if wa.returncode:
        raise SystemExit("Word Bank audit (audit_word_bank_reliability.cjs) failed after the ledger build: " + (wa.stderr or wa.stdout)[-800:])
    import accuracy_gates
    accuracy_gates.run_annotate(REPO)
    for L in lessons:
        print(L["date"], L["type"], L["words"]["pct"], L["grammar"]["pct"],
              (L["talk"] or {}).get("speak_pct"), (L["fillers"] or {}).get("per_min"),
              (L["latency"] or {}).get("median_s"), (L["flow"] or {}).get("wpm"), len(L["new_words"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump")
    a = ap.parse_args()
    if a.dump:
        P = TFX.apply(a.dump, page_turns(a.dump))
        W, _ = words_for(a.dump, P)
        attach_words(P, capped(W))
        for p in P:
            print(f"{mmss(p['t'])} {'CHAT ' if p['chat'] else ''}{p['who']}: {p['text']}")
        return
    build()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
