# -*- coding: utf-8 -*-
"""Shared pieces of the speech-engine benchmark (PR-18; spec C:/Claude/reports/ANEES-ENGINE-BENCHMARK-SPEC-2026-10-03.md).

One normaliser, one alignment and one file layout for every engine (fairness rule: "same clips, same normaliser, same
alignment code for every engine"). Nothing here calls a network or writes outside data/lesson-work/bench/<date>/.

    data/lesson-work/bench/<date>/truth.json      frozen answer key (bench_freeze.py)
    data/lesson-work/bench/<date>/manifest.json   sha256 of truth, clips, prompts
    data/lesson-work/bench/<date>/prompts.json    the listeners' frozen prompt per line
    data/lesson-work/bench/<date>/clips/          16 kHz mono wav per line (git-ignored: *.wav)
    data/lesson-work/bench/<date>/<engine>/<mode>-run<n>.json   raw engine output, never hand-edited
"""
import hashlib, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = r"C:\dev\anees\data\lessons"
PAD = 0.6


def bench_dir(date):
    return os.path.join(REPO, "data", "lesson-work", "bench", date)


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ the normaliser (pure)

DIAC = re.compile("[\u064B-\u0652\u0670\u0640]")          # harakat, dagger alef, tatweel
AR_LETTER = re.compile("[\u0621-\u064A]")
FOREIGN = re.compile("[\u0400-\u04FF\u0590-\u05FF\u0900-\u097F\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF]")  # TR-25
_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ک": "ك", "ی": "ي", "گ": "ك",
                      "ث": "ت", "ذ": "د", "ظ": "ض", "ؤ": "و", "ئ": "ي", "ء": None,
                      "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"})
AR_FILLER = re.compile("^(ا+|ا*م+|ا+ه+|ه+م+|اا+ه?)$")
LAT_FILLER = {"um", "uh", "uhm", "umm", "er", "hmm", "mm", "mhm", "ah", "eh", "aaa", "oh"}
NUM = {"واحد": "1", "وحده": "1", "واحده": "1", "اتنين": "2", "تنتين": "2", "تلاته": "3", "تلات": "3", "اربعه": "4", "اربع": "4",
       "خمسه": "5", "خمس": "5", "سته": "6", "ست": "6", "سبعه": "7", "سبع": "7", "تمانيه": "8", "تمانه": "8", "تمان": "8",
       "تسعه": "9", "تسع": "9", "عشره": "10", "عشر": "10", "احدعش": "11", "اطنعش": "12", "اتنعش": "12"}


def norm_token(w):
    """One word, normalised: no harakat/tatweel, alef and hamza forms folded, ة->ه, ى->ي, dialect letter pairs folded
    (ث->ت, ذ->د, ظ->ض: the same word in MSA or Levantine spelling), a final ه/ا folded to ا (لسه = لسا = لسة), Latin
    lower-cased without apostrophes. Orthography only: never a different word."""
    w = DIAC.sub("", w).translate(_MAP).lower()
    w = re.sub("[^0-9a-z\u0621-\u064A]", "", w)
    if AR_LETTER.search(w) and len(w) > 2 and w.endswith("ه"):
        w = w[:-1] + "ا"
    return w


def tokens(text, fillers=False):
    """Normalised word list of a line. Fillers (um, آآآ) are dropped unless fillers=True (TR-07: a pause, not a word)."""
    out = []
    for raw in re.split(r"[^0-9A-Za-z\u0621-\u0652\u0660-\u0669\u0670\u06A9\u06AF\u06CC'’`]+", text or ""):
        w = norm_token(raw)
        if not w:
            continue
        if not fillers and (AR_FILLER.match(w) or w in LAT_FILLER):
            continue
        out.append(w)
    return out


def is_ar(tok):
    return bool(AR_LETTER.search(tok))


_NUMN = None


def _num(w):
    global _NUMN
    if _NUMN is None:
        _NUMN = {norm_token(k): v for k, v in NUM.items()}
    return _NUMN.get(w)


def tok_eq(a, b):
    """Equal words; a digit equals its number word (spec: numbers to digits) without making عشر = عشرة in script."""
    if a == b:
        return True
    if a.isdigit() != b.isdigit():
        d, w = (a, b) if a.isdigit() else (b, a)
        return _num(w) == d
    return False


_reader = None


def latin_to_arabic(text):
    """Arabizi -> Arabic for Latin-letter output (scripts/arabizi_reader.to_arabic; Arabic script passes through)."""
    global _reader
    if _reader is None:
        import sys
        sys.path.insert(0, HERE)
        import arabizi_reader
        _reader = arabizi_reader.to_arabic
    try:
        return _reader(text or "")
    except Exception:  # noqa: BLE001 - a reader fault must never crash a scoring run; the raw view still scores
        return text or ""


def has_foreign(text):
    return bool(FOREIGN.search(text or ""))


# ------------------------------------------------------------------ whole-file alignment (same code for every engine)

def align_words(words, lines, offset, pad=1.0):
    """Engine words with times on the TRACK clock -> text per truth line. A word belongs to the line whose window
    [t - pad, end + pad] (lesson clock = track + offset) holds its midpoint; a word in two windows goes to the line whose
    centre is nearest. Returns {line_i: text}. Lines with no word get ''."""
    out = {ln["i"]: [] for ln in lines}
    spans = [(ln["i"], ln["t"] - pad, ln["end"] + pad, (ln["t"] + ln["end"]) / 2.0) for ln in lines]
    for w in words:
        if w.get("start") is None:
            continue
        mid = (float(w["start"]) + float(w.get("end") or w["start"])) / 2.0 + offset
        best = None
        for i, a, b, c in spans:
            if a <= mid <= b and (best is None or abs(mid - c) < best[0]):
                best = (abs(mid - c), i)
        if best:
            out[best[1]].append(w["text"])
    return {i: " ".join(x).strip() for i, x in out.items()}
