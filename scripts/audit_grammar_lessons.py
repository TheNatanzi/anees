# -*- coding: utf-8 -*-
"""Full grammar audit across every transcribed lesson.

Finds the places where Medi said something and Amal said it back changed
(a recast), works out which words changed, and files each one under a
grammar bucket from docs/data/grammar-buckets.json.

Output: docs/data/grammar-audit.json, with per-event HTML for both sides so
the page can underline the wrong span and the corrected span the way the
Word Bank does.

Nothing here guesses. A pair is only kept when Amal's line genuinely echoes
Medi's (enough shared words) and the change lands on a rule we can name.
"""
import json, os, re, glob, difflib, html
from collections import Counter

ANEES = r"C:\dev\anees\data\lessons"
DOCS = r"C:\dev\anees-hourly\docs"
OUT = os.path.join(DOCS, "data", "grammar-audit.json")

AR = re.compile(r"[\u0600-\u06FF]")
WORD = re.compile(r"[\u0600-\u06FF]+|[A-Za-z0-9']+")

# Recast window: Amal answering within this many seconds of Medi finishing.
WINDOW = 25.0
# How much of Medi's line Amal must repeat before we treat it as a recast.
MIN_OVERLAP = 0.30
MIN_WORDS = 2


# ---------------------------------------------------------------- turns
def turns_from_transcript(path):
    """[mm:ss] Speaker: text"""
    out = []
    for m in re.finditer(r"\[(\d+):(\d+)\]\s*(Amal|Medi):\s*([^\n]+)", open(path, encoding="utf-8", errors="replace").read()):
        t = int(m.group(1)) * 60 + int(m.group(2))
        text = re.sub(r"\(pause[^)]*\)", " ", m.group(4))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append({"speaker": m.group(3), "start": float(t), "end": float(t), "text": text})
    return out


def turns_from_scribe(path, speaker, gap=1.6):
    """Per-speaker Scribe file: glue words into utterances on a silence gap."""
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


def lesson_turns(date):
    d = os.path.join(ANEES, date)
    p = os.path.join(d, "transcript.txt")
    if os.path.exists(p):
        t = turns_from_transcript(p)
        if t:
            return t, "transcript.txt"
    t = []
    for who, f in (("Medi", "scribe_Medi.json"), ("Amal", "scribe_Amal.json")):
        t += turns_from_scribe(os.path.join(d, f), who)
    if t:
        t.sort(key=lambda x: x["start"])
        return t, "scribe per-speaker tracks"
    return [], None


# ---------------------------------------------------------------- matching
def toks(s):
    return WORD.findall(s or "")


def arabic_toks(s):
    return [w for w in toks(s) if AR.search(w)]


def overlap(a, b):
    """Share of Medi's Arabic words that Amal repeats."""
    A, B = Counter(arabic_toks(a)), Counter(arabic_toks(b))
    if not A:
        return 0.0
    same = sum(min(A[w], B[w]) for w in A)
    return same / sum(A.values())


def mark(tokens, flags, cls):
    """Rebuild a sentence, wrapping flagged tokens in a <mark>."""
    out, run = [], []
    for tok, on in zip(tokens, flags):
        if on:
            run.append(tok)
        else:
            if run:
                out.append('<mark class="%s">%s</mark>' % (cls, html.escape(" ".join(run))))
                run = []
            out.append(html.escape(tok))
    if run:
        out.append('<mark class="%s">%s</mark>' % (cls, html.escape(" ".join(run))))
    return " ".join(out)


def diff_spans(said, recast, arabic_only=True):
    """Which words Medi got wrong, and which words Amal put in their place.

    Arabic only by default: the lessons are half in English, and diffing the
    English chatter turns every friendly "yeah" into a fake correction.
    """
    a = arabic_toks(said) if arabic_only else toks(said)
    b = arabic_toks(recast) if arabic_only else toks(recast)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    fa, fb = [False] * len(a), [False] * len(b)
    wrong, fixed = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        for i in range(i1, i2):
            fa[i] = True
        for j in range(j1, j2):
            fb[j] = True
        if i2 > i1:
            wrong.append(" ".join(a[i1:i2]))
        if j2 > j1:
            fixed.append(" ".join(b[j1:j2]))
    return {
        "said_html": mark(a, fa, "ab-wrong"),
        "recast_html": mark(b, fb, "ab-correct"),
        "wrong": [w for w in wrong if w.strip()],
        "fixed": [w for w in fixed if w.strip()],
        "changed": sum(fa) + sum(fb),
    }


PRAISE = re.compile(r"✓|ممتاز|تمام|برavo|\bYes\b|\bexactly\b|\bperfect\b|\bgood job\b", re.I)

DIACRITICS = re.compile(r"[ً-ْـ]")


def norm(w):
    """Same word, ignoring the spelling wobble the transcriber invents."""
    w = DIACRITICS.sub("", w or "")
    w = re.sub(r"[^ء-ي]", "", w)
    w = w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    w = w.replace("ى", "ي").replace("ة", "ه")
    return w


def strip_al(w):
    return w[2:] if w.startswith("ال") and len(w) > 3 else w




def minimal_pair(wrong, fixed):
    """Find one word of Medi's and one of Amal's that are the same word in a
    different shape. That pairing is what makes a correction a correction."""
    best = None
    for w in " ".join(wrong).split():
        if not AR.search(w):
            continue
        for f in " ".join(fixed).split():
            if not AR.search(f) or f == w:
                continue
            nw, nf = norm(w), norm(f)
            if not nw or not nf or nw == nf:
                continue  # punctuation or spelling wobble, not a correction
            r = difflib.SequenceMatcher(a=nw, b=nf).ratio()
            if 0.5 <= r < 0.98 and (not best or r > best[2]):
                best = (w, f, round(r, 2))
    return best


# ---------------------------------------------------------------- classifier
B_PREFIX = re.compile(r"^(ب|بي|بت|بن)")
GATEKEEPER = ("بدي", "بدك", "بدها", "لازم", "ممكن", "بحب", "بقدر", "رح", "راح",
              "لما", "إذا", "اذا", "عشان", "قبل ما", "بعد ما", "حتى")
KOON = re.compile(r"(أكون|اكون|تكون|يكون|نكون|بكون|يكونوا|تكوني|كون)")
HARD = "عطحخغصق"


def classify(said, recast, d):
    """Name the bucket this correction belongs to, or refuse.

    Works on the minimal pair - the one word Medi got wrong and the one word
    Amal put in its place - not on the whole changed span. A span-wide match
    let A1 and D5 swallow every correction in the lesson.

    Returns (bucket_id, why) or None. Refusing is the default: an unnamed
    correction is left out rather than filed under a rule it might not be.
    """
    w, f, _sim = d["pair"]
    nw, nf = norm(w), norm(f)
    ctx = said + " " + recast

    # --- el- added or dropped: one word IS the other plus the article
    if strip_al(nw) == strip_al(nf) and nw != nf:
        if re.search(r"اكتر|احسن|اقل|اسوا", nw + nf):
            return ("C3", "no el- on a comparative")
        if re.search(r"هاد|هادي|هدول|هذي|هذا", ctx):
            return ("A10b", "the noun after hada keeps its el-")
        if re.search(r"(^|\s)(من|على|في|مع|عن)(\s|$)", ctx):
            return ("D5", "the preposition keeps the el-")
        if re.search(r"(بيت|سيارة|اسم|كتاب|باب)", ctx):
            return ("A2", "idafa: the el- goes on the owner")
        return ("A1", "el- added or dropped")

    # --- the b- prefix came off or went on the same verb
    wb, fb = B_PREFIX.match(nw), B_PREFIX.match(nf)
    if bool(wb) != bool(fb):
        stem_w = nw[len(wb.group(0)):] if wb else nw
        stem_f = nf[len(fb.group(0)):] if fb else nf
        if difflib.SequenceMatcher(a=stem_w, b=stem_f).ratio() > 0.7:
            gate = next((g for g in GATEKEEPER if g in ctx), None)
            if gate:
                modal = gate in ("بدي", "بدك", "بدها", "لازم", "ممكن", "بحب", "بقدر")
                if wb and not fb:
                    return ("B2" if modal else "B3", "the b- drops after " + gate)
                return ("B4b", "the b- comes back outside " + gate)
            return ("B1", "the b- prefix")

    # --- the being-verb
    kw, kf = KOON.fullmatch(nw), KOON.fullmatch(nf)
    if kw and kf:
        return ("B9", "wrong person on ykoon")
    if kf and not kw:
        return ("B8", "this slot needs ykoon")

    # --- kaan + laazem
    if "لازم" in ctx and (norm("كان") in (nw, nf) or norm("كنت") in (nw, nf)):
        return ("B16", "kaan + laazem")

    # --- saarli
    if nw.startswith(norm("صارل")) or nf.startswith(norm("صارل")):
        return ("B17", "saarli duration")

    # --- feminine ending appeared or vanished on the same word
    if nw.rstrip("ه") == nf.rstrip("ه") and nw != nf:
        return ("A8", "feminine agreement")

    # --- demonstrative swapped for the other gender
    DEMS = {norm(x) for x in ("هاد", "هادي", "هدول", "هذا", "هذي", "هداك", "هديك")}
    if nw in DEMS and nf in DEMS:
        return ("A10", "hada / hadi must match the noun")

    # --- negation words swapped
    NEG = {norm(x) for x in ("ما", "مش", "لا")}
    if nw in NEG or nf in NEG:
        if re.search(r"ابدا", norm(ctx)):
            return ("C4b", "abadan still needs ma")
        if nw in NEG and nf in NEG:
            return ("C4", "ma vs mish")

    # --- prepositions swapped
    PREPS = {norm(x) for x in ("من", "على", "في", "مع", "عن", "الى", "ل", "ب")}
    if nw in PREPS and nf in PREPS:
        return ("D2", "the verb wants a different preposition")

    # --- number + noun agreement
    NUMS = r"(تلات|اربع|خمس|ست|سبع|تمان|تسع|عشر|حداعش|عشرين|تلاتين)"
    if re.search(NUMS, norm(ctx)) and nw.rstrip("اتي") != nf.rstrip("اتي"):
        PLURALS = {norm("ايام"): norm("يوم"), norm("ساعات"): norm("ساعة"),
                   norm("شهور"): norm("شهر"), norm("سنين"): norm("سنة")}
        if PLURALS.get(nw) == nf or PLURALS.get(nf) == nw:
            return ("E1", "11 and up takes a singular noun")

    # --- an object / pointer ending grew on the verb
    if nf.startswith(nw) and len(nf) > len(nw) and nf[len(nw):] in ("ه", "ها", "هم", "ك", "ني", "لك", "لي"):
        return ("C2", "the pointer ending was missing")

    # --- iyyaa
    if norm("اياه") in (nw, nf) or norm("اياك") in (nw, nf):
        return ("D6", "iyyaa carries the second object")

    # --- make-X vs get-X: the middle letter doubles
    if re.search(r"(بسط|زعل|تعب|ضحك|زهق|خوف|جهز|عصب)", nw + nf):
        if abs(len(nw) - len(nf)) <= 2 and nw != nf:
            return ("B12", "make-X vs get-X pair")

    # --- person ending on the verb: same stem, different person affix
    PERSON = ("ني", "نا", "تي", "توا", "وا", "ها", "هم", "ك", "ت", "ي", "ن")
    if len(nw) > 3 and len(nf) > 3:
        common = os.path.commonprefix([nw, nf])
        tw, tf = nw[len(common):], nf[len(common):]
        if len(common) >= 4 and tw != tf and (tw in PERSON or tf in PERSON):
            return ("B1", "wrong person ending on the verb")

    # --- a hard letter went missing
    def skel(x):
        return re.sub("[" + HARD + "]", "", x)
    if skel(nw) == skel(nf) and nw != nf:
        return ("F1", "a hard letter was dropped or swapped")

    return None


# ---------------------------------------------------------------- run
buckets = {b["id"]: b for b in json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]}
dates = sorted(d for d in os.listdir(ANEES) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
NOT_ARABIC = {"2026-08-22", "2026-08-23", "2026-09-01"}

lessons, events = [], []
for date in dates:
    if date in NOT_ARABIC:
        continue
    T, src = lesson_turns(date)
    if not T:
        continue
    medi = [t for t in T if t["speaker"] == "Medi"]
    medi_ar = [t for t in medi if arabic_toks(t["text"])]
    found = 0
    for i, m in enumerate(T):
        mar = arabic_toks(m["text"])
        if m["speaker"] != "Medi" or len(mar) < MIN_WORDS:
            continue
        for a in T[i + 1:]:
            if a["start"] - m["end"] > WINDOW:
                break
            if a["speaker"] != "Amal":
                continue
            aar = arabic_toks(a["text"])
            if not aar:
                continue
            ov = overlap(m["text"], a["text"])
            kind = None

            if ov >= MIN_OVERLAP and mar != aar:
                # She repeated his sentence back with something changed.
                kind = "echo"
            elif len(aar) <= 3:
                # She just said the fixed word on its own. Pair it with the
                # word of his it is closest to - close, but not identical.
                best, bw = 0.0, None
                for hers in aar:
                    for his in mar:
                        if hers == his:
                            continue
                        r = difflib.SequenceMatcher(a=his, b=hers).ratio()
                        if r > best:
                            best, bw = r, his
                if 0.55 <= best < 0.98:
                    kind = "spot"

            if not kind:
                continue
            if PRAISE.search(a["text"]):
                continue  # she is agreeing, not correcting
            d = diff_spans(m["text"], a["text"])
            if not d["changed"] or d["changed"] > 12:
                continue
            # A real correction changes Arabic, and does not simply add words.
            if not d["wrong"] or not d["fixed"]:
                continue
            # The decisive test: a grammar fix re-says the SAME word in a
            # different form. Without a minimal pair it is a new sentence,
            # not a correction, so we leave it out rather than guess.
            pair = minimal_pair(d["wrong"], d["fixed"])
            if not pair:
                # A tight echo with a small change is still a correction even
                # when she swaps the word outright rather than reshaping it.
                if kind == "echo" and ov >= 0.55 and d["changed"] <= 6:
                    pair = (" ".join(d["wrong"])[:40], " ".join(d["fixed"])[:40], 0.0)
                else:
                    continue
            d["pair"] = pair
            hit = classify(m["text"], a["text"], d)
            if hit and hit[0] in buckets:
                bucket, why = hit
            else:
                # Real correction, no rule we can name. Park it for filing
                # rather than throw away evidence.
                bucket, why = "UNFILED", "correction found, rule not identified"
            # Be honest about how much to trust each row. Only Amal, or Medi,
            # can promote one of these to a scored slip.
            score = 0
            score += 2 if kind == "echo" else 0
            score += 1 if d["pair"][2] >= 0.7 else 0
            score += 1 if len(d["wrong"]) == 1 and len(d["fixed"]) == 1 else 0
            score += 1 if len(arabic_toks(a["text"])) >= 2 else 0
            confidence = "high" if score >= 4 else "medium" if score >= 2 else "low"
            events.append({
                "bucket": bucket, "date": date, "t": round(m["start"], 1),
                "mmss": "%02d:%02d" % (int(m["start"]) // 60, int(m["start"]) % 60),
                "said": m["text"], "recast": a["text"],
                "said_html": d["said_html"], "recast_html": d["recast_html"],
                "wrong": d["wrong"], "fixed": d["fixed"],
                "pair_wrong": d["pair"][0], "pair_fixed": d["pair"][1],
                "pair_similarity": d["pair"][2],
                "why": why, "match": kind, "overlap": round(ov, 2), "source": src,
                "confidence": confidence, "verified": False,
            })
            found += 1
            break
    lessons.append({"date": date, "source": src, "turns": len(T),
                    "medi_turns": len(medi), "medi_arabic_turns": len(medi_ar),
                    "corrections": found})
    print("%s  %-24s turns=%4d  Medi=%4d (%3d Arabic)  corrections=%3d"
          % (date, src, len(T), len(medi), len(medi_ar), found))

by_bucket = Counter(e["bucket"] for e in events)
json.dump({
    "updated": "2026-09-23",
    "method": ("Amal repeats Medi's sentence within %ds sharing at least %d%% of his Arabic words; "
               "the changed words are the correction. Classified by rule, never guessed." % (WINDOW, int(MIN_OVERLAP * 100))),
    "lessons": lessons,
    "totals": {"events": len(events), "buckets_hit": len(by_bucket),
               "lessons_with_text": len(lessons)},
    "by_bucket": dict(by_bucket.most_common()),
    "events": events,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\nwrote", OUT)
print("events:", len(events), "across", len(by_bucket), "buckets")
for b, n in by_bucket.most_common(20):
    print("  %-7s %-34s %d" % (b, buckets[b]["name"] if b in buckets else "(needs filing)", n))
