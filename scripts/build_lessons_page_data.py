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

Word scores run the Word Bank page's own JS (scripts/lessons_page_node.cjs) so they count exactly like it.
Grammar mistakes = the 2026-09-24 hand sweep (data/grammar-sweep-2026-09-24.json), speaking rows in an
approved bucket (docs/data/grammar-buckets.json) + unfiled rows in NEW-B18 (approved as B18).
Grammar uses = docs/data/grammar-usage.json (owned by another worker; read at build time).
Lesson types are Claude's reading of each lesson (LESSON_TYPES), marked type_source 'claude-read'.
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
def _confirmed_new():
    try:
        import db
        return sorted({(str(r["lesson_date"]), r["word_key"]) for r in db.select("amal_rules", {"select": "lesson_date,word_key,kind", "kind": "eq.new"}) if r.get("word_key")})
    except Exception:
        return [("2026-09-04", "ana babse6"), ("2026-09-04", "banbese6")]   # last read 2026-09-25
CONFIRMED_NEW = _confirmed_new()
# Claude's reading of what each lesson drilled (from LESSON_TYPES notes); shown as a reading, never scored.
TAUGHT = {   # [her-style Arabizi (built from her Doc/chat forms), Arabic]
    "2026-09-04": [["babse6 / banbese6", "بسط / انبسط"]],
    "2026-09-05": [["baz3ej / banze3ej", "زعج / انزعج"], ["babse6 / banbese6 (review)", "بسط / انبسط"]],
    "2026-09-10": [["bakser / bankeser", "كسر / انكسر"], ["baz3ej / banze3ej (review)", "زعج / انزعج"]],
    "2026-09-11": [["5arab / 5arrab", "خرب / خرّب"]],
    "2026-09-14": [["baz3ej / banze3ej", "زعج / انزعج"], ["bakser / bankeser", "كسر / انكسر"], ["babse6 / banbese6", "بسط / انبسط"]],
    "2026-09-15": [["8ayyar / t8ayyar", "غيّر / تغيّر"], ["sawwar / tsawwar", "صوّر / تصوّر"], ["zakkar / tzakkar", "ذكّر / تذكّر"], ["bakser / bankeser (review)", "كسر / انكسر"]],
    "2026-09-16": [["7ammas / t7ammas", "حمّس / تحمّس"], ["wajja3 / twajja3", "وجّع / توجّع"], ["daaya2 / tdaaya2", "ضايق / تضايق"], ["7arrak / t7arrak", "حرّك / تحرّك"]],
    "2026-09-17": [["t2assaf (la / min)", "تأسف (لـ / من)"], ["5awwaf", "خوّف"], ["da77ak", "ضحّك"], ["5arab / 5arrab (review)", "خرب / خرّب"]],
    "2026-09-18": [["zahha2 / zehe2", "زهّق / زهق"], ["ta33ab / te3eb", "تعّب / تعب"], ["za33al / ze3el", "زعّل / زعل"], ["5awwaf / 5aaf", "خوّف / خاف"], ["da77ak / de7ek", "ضحّك / ضحك"], ["3assab", "عصّب"]],
    "2026-09-19": [["the verb pairs, as listening", "—"]],
}
DATES = ["2026-08-25", "2026-09-04", "2026-09-05", "2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15",
         "2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-21", "2026-09-23"]
GLUE = 1.2          # s: words closer than this are one turn
LAT_MAX = 15.0      # s: a reply later than this is not a reply
WORD_MAX = 2.0      # s: one word counts at most this long (the engine sometimes stretches a word over a silence;
                    #    on 09-05 / 09-11 / 09-15 that alone would add ~10 min of "talk")
AR = re.compile(r"[\u0621-\u064A\u0671-\u06D3]")

def J(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


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
    return None, "no word-level timings on disk for this lesson (the page has line start times only)"


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


def run_node(strings):
    os.makedirs(TMP, exist_ok=True)
    i, o = os.path.join(TMP, "node-in.json"), os.path.join(TMP, "node-out.json")
    json.dump({"arabic": sorted(set(s for s in strings if s))}, open(i, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run([NODE, os.path.join(HERE, "lessons_page_node.cjs"), i, o], check=True, capture_output=True)
    return J(o)


# ------------------------------------------------------------------ Claude's reading of each lesson
# (type, review_mode, why). Read from the lesson pages + the sweep's per-lesson coverage notes, 2026-09-25.
LESSON_TYPES = {
    "2026-08-25": ("free-speak", None, "Conversation from Amal's questions (time, clothes, weather, what tires you, fears, fiancee) with fixes as they come; ~4 min of Meet setup talk; no drill."),
    "2026-09-04": ("new-grammar", None, "28:00-1:03:00 (~35 of 63 min) is the first causative/reflexive pair: Amal teaches how بسط/انبسط conjugate (b- before a root b, past endings, command); 11:00-28:00 is mostly English about AI tools and a honey seller."),
    "2026-09-05": ("new-words", None, "Most of the lesson (~22:00-1:02) drills the new pair زعج/انزعج in past, present and command; 07:00-22:00 reviews بسط/انبسط; first 6 min is app-demo talk."),
    "2026-09-10": ("new-words", None, "27:00-57:00 teaches the new pair كسر/انكسر in every tense; before that ~25 min of conversation and a review of زعج/انزعج; ends with Amal listing the causative verbs to learn."),
    "2026-09-11": ("new-words", None, "~10:00-1:00:00 drills the new pair خرب/خرّب (past, present, command, 'rots', 'mess up'); the first 10 min is small talk plus a short review of north/darkness/stars words."),
    "2026-09-14": ("review-words", "speaking", "After ~22 min of small talk, Amal gives English sentences and Medi says them in Arabic with the verbs already taught (زعج/انزعج, كسر/انكسر, بسط/انبسط) - 'we're repeating today'; Amal types each answer in chat."),
    "2026-09-15": ("new-words", None, "28:00-1:05 (~37 min) teaches new T-verbs غيّر/تغيّر, صوّر/تصوّر, ذكّر/تذكّر; 10:00-28:00 (~18 min) reviews كسر/انكسر; first 10 min is small talk."),
    "2026-09-16": ("new-words", None, "~10:00-1:08 teaches new pairs حمّس/تحمّس, وجّع/توجّع, ضايق/تضايق, حرّك/تحرّك with English-to-Arabic sentences; first ~10 min is small talk (date, clothes)."),
    "2026-09-17": ("new-words", None, "Mixed: 14:00-32:00 teaches the new verb تأسف (with لـ/من) and 50:00-57:00 introduces the doubled-middle adjectives (خوّف, ضحّك); 32:00-50:00 (~18 min) reviews خرب/خرّب; first 14 min small talk. New material is the larger share."),
    "2026-09-18": ("new-words", None, "After ~5 min of small talk the whole lesson drills a new group of doubled-middle verb pairs (زهّق/زهق, تعّب/تعب, زعّل/زعل, خوّف/خاف, ضحّك/ضحك, عصّب) across tenses and persons; Amal: 'the best group yet'."),
    "2026-09-19": ("review-words", "listening", "After ~12 min of songs and small talk, Amal wraps up the verb pairs 'by doing some listening': she says a form, Medi says what it means in English; Medi's own Arabic is only ~06:30-10:30 and a few drill lines."),
    "2026-09-21": ("free-speak", None, "Conversation and role plays for the whole hour: stress at work, pizza, ordering at a cafe, complaining about food to a manager, how he cooks rice (tahdig), Iranian food abroad."),
    "2026-09-23": ("free-speak", None, "Conversation and role plays: coffee, stomach ache, then booking a hotel room, breakfast, paying, complaining to the manager, booking tickets and appointments, a weekend drive. Medi's first ~23 min is not transcribed (Amal's side only)."),
}

DEFINITIONS = {
    "start_local": "When the recording started, local time with offset. From the Meet recording's tracks.json, its folder name, or source.json. Null if none of these exist.",
    "duration_min": "Length of the lesson audio the page plays, in minutes.",
    "type": "Claude's reading of what the lesson mostly was: free-speak = conversation; review-words = practising words already taught; new-words = Amal teaching new vocabulary (new verb pairs drilled in all tenses count here); new-grammar = Amal teaching a rule. One main type; if mixed, the one with the most minutes, and type_why says so. type_source 'claude-read' = Medi can correct it.",
    "review_mode": "For review lessons only: listening = Amal says Arabic, Medi gives the meaning; speaking = Medi says it in Arabic; both.",
    "words.unique": "How many different Word Bank words Medi was scored on in this lesson.",
    "words.right": "Scored uses marked correct (same rules as the Word Bank page: its own code is run on docs/data/word-bank-evidence.json + word-bank-review.json).",
    "words.partial": "Scored uses marked partial (he got there with help) - worth half.",
    "words.wrong": "Scored uses marked incorrect.",
    "words.pct": "Word score for the lesson: (right + half of partial) / all scored uses, as a percent. The Word Bank's own weighting.",
    "grammar.uses": "Times Medi's Arabic exercised a grammar rule in this lesson, right or wrong (docs/data/grammar-usage.json). Turns the engine wrote in Latin letters are not counted there.",
    "grammar.mistakes": "Grammar slips Amal corrected out loud in this lesson (hand sweep 2026-09-24, speaking rows filed in an approved rule).",
    "grammar.pct": "Share of rule uses that were right: 1 - mistakes / uses, as a percent. Null when uses are missing.",
    "talk.medi_s": "Seconds Medi was talking: his words glued into turns (gaps under 1.2 s), turn lengths added up. Stretches the engine marked '[speaking Arabic]' count as talk.",
    "talk.amal_s": "Same for Amal.",
    "talk.speak_pct": "Medi's share of the talking: medi_s / (medi_s + amal_s).",
    "talk.listen_pct": "Amal's share of the talking (the time Medi was listening to her).",
    "fillers.count": "Medi's filled pauses (the technical name: filled pauses, a kind of disfluency) - uh, um, er, eh, mm, hmm, ah, and Arabic ام / امم / آآ / ممم; آه and اه only when they come mid-sentence (at the start they usually mean 'yes'). The engine drops some, so this is a floor.",
    "fillers.per_min": "Filled pauses per minute of Medi's own talk time.",
    "fillers.top": "The most frequent ones, with counts.",
    "latency.median_s": "Response latency: seconds from the end of Amal's turn to the start of Medi's reply, middle value. Only replies within 15 s; overlaps (he starts before she stops) are left out. A pause is not an error (rule S5) - this is a speed measure only.",
    "latency.p75_s": "Three quarters of his replies started within this many seconds.",
    "latency.n": "How many replies were measured.",
    "flow.wpm": "Speaking flow: Arabic words per minute inside Medi's Arabic turns (a turn = words with gaps under 1.2 s; only turns with at least 2 Arabic-script words; filled pauses not counted as words). English-only turns and Latin-script transliterations are left out.",
    "flow.n_turns": "How many of his Arabic turns went into wpm.",
    "new_words": "Only words Amal (or Medi) marked new for this lesson (amal_rules kind='new'). Never guessed from the recording (hard rule 2026-09-05).",
    "taught": "What the lesson drilled, from Claude's reading of the transcript - not Amal's mark, never scored.",
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


def build():
    sweep = J(os.path.join(REPO, "data", "grammar-sweep-2026-09-24.json"))
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
        G.setdefault(r["date"], []).append({**r, "bucket": b})

    node = run_node([])
    scored = node["scored"]
    info = node["wordInfo"]
    vocab_fix = {}
    for v in sweep.get("vocab", []):
        vocab_fix.setdefault(v["date"], []).append(v)

    lessons, per = [], {}
    # first lesson each list word shows up in: the earlier of (Word Bank evidence, plain text of any lesson page).
    # Evidence for the early lessons is sparse, so text keeps everyday words (بس, شو) from looking "new" later.
    pages = {d: page_turns(d) for d in DATES}
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
        W = capped(W)
        attach_words(P, W)
        notes = []
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
                notes.append(f"talk, fillers, latency and flow measured from {mmss(lo)} on: Medi's first recording (0:00-22:37) has no transcript, so only Amal's side exists before that.")
            talk, fillers, latency, flow = metrics(W, lo, hi)
            talk["window"] = [round(lo, 1), round(min(hi, max(w['e'] for w in W)), 1)]
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
        uses = (usage.get(date) or {}).get("uses")
        mistakes = len(rows)
        gpct = None
        if uses is None:
            notes.append("grammar uses not yet in docs/data/grammar-usage.json for this lesson; grammar.pct null until the re-run.")
        elif uses:
            gpct = round(100 * (1 - mistakes / uses), 1)
            if gpct < 0:
                notes.append(f"grammar: {mistakes} corrected slips but only {uses} detected rule uses (uses skip Latin-script turns), so grammar.pct is null.")
                gpct = None
            elif mistakes > uses / 2:
                notes.append(f"grammar.pct is low partly because uses ({uses}) are undercounted: the usage count skips turns written in Latin letters or left blank ('[speaking Arabic]'), while Amal's fixes there are still counted.")
        grammar = {"uses": uses, "mistakes": mistakes, "pct": gpct}

        # ---- new words
        typ, mode, why = LESSON_TYPES[date]
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
                  **({"typed_by": p["who"]} if p["chat"] else {}), "text": p["text"]} for p in P]
        med = sorted((p for p in P if p["who"] == "Medi" and not p["chat"]), key=lambda p: p["t"])
        mts = [p["t"] for p in med]
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
                         "wrong": tok, "fix": fix, "clip": clip, "why": s["reason"], "event_id": s["id"]})
            need_ar.add(said)
        gerr = []
        for r in rows:
            b = buckets.get(r["bucket"], {})
            gerr.append({"t": rt(r), "mmss": r.get("t") or r.get("t_amal"), "t_fix": sec(r["t_amal"]) if r.get("t_amal") else None,
                         "bucket": r["bucket"], "bucket_name": b.get("name"), "mistake": r.get("mistake"),
                         "said": r.get("medi_said"), "said_arabizi": r.get("medi_said_arabizi"),
                         "fix": r.get("amal_said"), "fix_arabizi": r.get("amal_said_arabizi"),
                         "chat": r.get("chat"), "wrong": r.get("wrong"), "wrong_arabizi": r.get("wrong_arabizi"),
                         "right": r.get("right"), "right_arabizi": r.get("right_arabizi"),
                         "confidence": r.get("confidence"), "signal": r.get("signal"), "id": r.get("id")})
        marks = sorted([{"t": v["t"], "kind": "vocab", "wrong": v["wrong"], "right": v["fix"] or v["arabic"]} for v in verr if v["kind"] == "wrong"] +
                       [{"t": g["t"], "kind": "grammar", "wrong": g["wrong"], "right": g["right"]} for g in gerr if g["wrong"]],
                       key=lambda m: m["t"])
        per[date] = {"date": date, "clock": "seconds on the lesson page audio (docs/lessons/%s/audio/...)" % date,
                     "turns": turns, "vocab_errors": verr, "grammar_errors": gerr, "marks": marks}

        lessons.append({
            "date": date, "start_local": start, "start_source": start_src,
            "duration_min": round(dur / 60, 1) if dur else None,
            "type": typ, "review_mode": mode, "type_why": why, "type_source": "claude-read",
            "words": words, "grammar": grammar, "talk": talk, "fillers": fillers, "latency": latency, "flow": flow,
            "new_words": new_words, "taught": taught, "coverage": per_lesson_cov.get(date), "notes": notes,
            "page": f"lessons/{date}.html", "detail": f"data/lessons/{date}.json",
            "counts": {"turns": sum(1 for p in P if not p["chat"]), "chat_lines": sum(1 for p in P if p["chat"]),
                       "vocab_errors": len(verr), "grammar_errors": len(gerr)},
        })

    # Amal's spelling for the new words and the said-sentences (display only, rule S1)
    az = run_node(sorted(x for x in need_ar if x))["arabizi"]
    for L in lessons:
        for x in L["new_words"]:
            wi = info.get(x["key"], {})
            x["arabizi"] = wi.get("house") or wi.get("doc_arabizi") or (az.get(x["_ar"]) or {}).get("text")
            x.pop("_ar")
    for d, v in per.items():
        for e in v["vocab_errors"]:
            r = az.get(e["said"]) or {}
            e["said_arabizi"] = r.get("text")

    os.makedirs(os.path.join(DOCS, "data", "lessons"), exist_ok=True)
    for d, v in per.items():
        with open(os.path.join(DOCS, "data", "lessons", d + ".json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, separators=(",", ":"))
    out = {"updated": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "method": __doc__.strip().split("\n\n", 1)[1] if "\n\n" in __doc__ else __doc__,
           "definitions": DEFINITIONS, "lessons": lessons}
    with open(os.path.join(DOCS, "data", "lessons.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for L in lessons:
        print(L["date"], L["type"], L["words"]["pct"], L["grammar"]["pct"],
              (L["talk"] or {}).get("speak_pct"), (L["fillers"] or {}).get("per_min"),
              (L["latency"] or {}).get("median_s"), (L["flow"] or {}).get("wpm"), len(L["new_words"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump")
    a = ap.parse_args()
    if a.dump:
        P = page_turns(a.dump)
        W, _ = words_for(a.dump, P)
        attach_words(P, capped(W))
        for p in P:
            print(f"{mmss(p['t'])} {'CHAT ' if p['chat'] else ''}{p['who']}: {p['text']}")
        return
    build()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
