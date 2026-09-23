# -*- coding: utf-8 -*-
"""Compare one Arabic word across the three ways a lesson writes it.

  Arabic script             بيحطوا       (Scribe, most turns)
  Latin, Scribe-style       yita'assif / kharabit / ma ba'dar   (Scribe when it gives up on Arabic letters)
  Amal's Arabizi (chat)     bey7uttu / 5arrabti / 3indek

key(w)   one Latin spelling with vowels, Arabizi digits resolved, shadda doubled  -> for classifying
skel(w)  consonant skeleton: no vowels, no ع ء ق, no w y, no final -h            -> for "is it the same word?"

Matching only. Nothing here is ever shown to Medi (rule S1: Amal's spelling is
the only spelling). scripts/arabizi.py is the Doc-word matcher; this is the
looser cross-script comparison the grammar auditor needs.
"""
import re
from difflib import SequenceMatcher
from statistics import median

from english_stop import ENGLISH_STOP

AR = re.compile(r"[؀-ۿ]")
DIAC = re.compile(r"[ً-ِْ-ٰٟـ]")  # every mark except shadda

AR2L = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ٱ": "a", "ء": "'", "ؤ": "'", "ئ": "'",
    "ب": "b", "ت": "t", "ث": "t", "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "z",
    "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z",
    "ع": "'", "غ": "gh", "ف": "f", "ق": "'", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "ة": "a", "و": "u", "ي": "i", "ى": "a", "ڤ": "v", "پ": "p", "چ": "ch", "گ": "g",
}

ENGLISH = set(ENGLISH_STOP) | set("""
feminine masculine pointer preposition apologize apology everyone anything nothing mean meant
sausage rice pizza water coffee shirt trip plans plan movie scary boring fun happy annoyed upset
photo move hurt break broke broken ruin ruined fix fixes breaks restaurant restaurants food
chef chefs customer customers told tell hot dog word hold wait sorry right okay
guys guy fire department ambulance sirens trucks crispy fried rice cooker spoon pastry croissant chocolate
mm-hmm mhm mmhmm uhhuh uh-huh uh-uh hmm-hmm mmm oops whoops daisy gonna wanna gotta kinda
arab arabs arabic persian iranian iranians farsi
full empty whole half part verb verbs noun nouns bit fun funny quiz card cards plan plans
""".split())

_LAT = [
    ("’", "'"), ("`", "'"), ("2", "'"), ("3", "'"), ("5", "kh"), ("7", "h"), ("6", "t"), ("9", "s"),
    ("8", "gh"), ("x", "kh"), ("ch", "sh"), ("th", "t"), ("q", "'"), ("c", "k"),
    ("ee", "i"), ("oo", "u"), ("ou", "u"), ("o", "u"), ("e", "i"), ("y", "i"),
]


def is_ar(w):
    return bool(AR.search(w or ""))


def key(w):
    """One Latin spelling. Arabic script: letters mapped, shadda doubles.
    Latin: Arabizi digits resolved, e->i o->u (the transcripts use both)."""
    w = (w or "").strip()
    if is_ar(w):
        out = []
        for ch in DIAC.sub("", w):
            if ch == "ّ":
                if out and out[-1]:
                    out.append(out[-1][-1])
                continue
            out.append(AR2L.get(ch, ""))
        return "".join(out)
    k = w.lower()
    k = re.sub(r"[^a-z0-9'’`]", "", k)
    for a, b in _LAT:
        k = k.replace(a, b)
    return k


def skel(w, keep_double=False, ayn=False):
    """Consonant skeleton. ayn=True keeps ع / ' as a letter (Q): weak roots
    like ب-ي-ع are all vowels and ع otherwise."""
    k = key(w).replace("sh", "S").replace("kh", "K").replace("gh", "G").replace("g", "G")
    if ayn:
        k = k.replace("'", "Q")
    ends_h = k.endswith("h")
    s = "".join(ch for ch in k if ch not in "aeiou'wiy")
    s = s[:-1] if ends_h and len(s) > 2 else s
    if not keep_double:
        s = re.sub(r"(.)\1+", r"\1", s)
    return s


def has_al(w):
    if is_ar(w):
        return w.startswith("ال") and len(w) > 3 and w not in ("اللي", "الّي", "إللي")
    lw = (w or "").lower()
    return bool(re.match(r"^(el|il|al|l)[-'][a-z0-9]{2}", lw) or
                re.match(r"^[aei](t|th|d|dh|r|z|s|sh|n|l)-(t|th|d|dh|r|z|s|sh|n|l)[a-z]", lw))


def bare(w, ayn=False):
    """Skeleton without the article (taken off before letters collapse, so
    العالم stays 'lm', not 'm')."""
    if has_al(w):
        rest = w[2:] if is_ar(w) else re.sub(r"^((el|il|al|l)[-']|[aei](t|th|d|dh|r|z|s|sh|n|l)-)", "", w, flags=re.I)
        return skel(rest, ayn=ayn)
    return skel(w, ayn=ayn)


def is_english(w):
    raw = (w or "").lower()
    lw = re.sub(r"[^a-z']", "", raw)
    return raw in ENGLISH or lw in ENGLISH or (len(lw) > 3 and lw.endswith("s") and lw[:-1] in ENGLISH)


def sim(a, b):
    return SequenceMatcher(a=a, b=b, autojunk=False).ratio()


TOK = re.compile(r"[ء-غـ-ْٰ-ۓ]+|[A-Za-z0-9'’`]+(?:-[A-Za-z0-9'’`]+)*")


CUT = re.compile(r"(\S+?)(--|—|–|-)(?=\s|$|[،,.?؟])")
FILLER = {"uh", "um", "umm", "uhm", "mm", "hmm", "er", "ah", "آآآ", "امم", "اه", "ممم"}


def tokens(text):
    """Words of a line. The transcript writes the article apart ("الـ دنيا",
    "il roz"); glue it back so a split article is not read as a missing one.
    A word cut off mid-way ("أمريك--") is a stutter and is dropped."""
    text = text or ""

    def _cut(mt):
        w = mt.group(1)
        rest = text[mt.end():].lstrip(" ،,.")
        nxt = re.match(r"\S+", rest)
        # a stutter: a fragment, or he restarts the same word right after
        if len(re.sub(r"[^\w]", "", w)) <= 2 or (nxt and nxt.group(0)[:2] == w[:2]):
            return " "
        return w + " "
    text = CUT.sub(_cut, text)
    text = re.sub(r"(?<!\S)(?!الـ)[؀-ۿ]+ـ(?=\s|$|[،,.])", " ", text)  # بيـ cut before the word (not the article الـ)
    out, pend = [], None
    for w in TOK.findall(text):
        if pend is not None and w.lower() in FILLER:
            continue
        if pend is not None:
            if is_ar(pend) and is_ar(w):
                out.append("ال" + w)
                pend = None
                continue
            if not is_ar(pend) and not is_ar(w) and not is_english(w):
                out.append(pend.lower() + "-" + w)
                pend = None
                continue
            out.append(pend)
            pend = None
        if w in ("ال", "الـ", "ٱل") or w.lower() in ("il", "el", "al"):
            pend = w
            continue
        out.append(w)
    if pend is not None:
        out.append(pend)
    return [w for w in out if w not in ("ال", "الـ")]


def arabic_tokens(text, lexicon=None):
    """Arabic words of a line in any script. A Latin token counts when it is not
    English and (when a lexicon is given) its skeleton is a known Arabic word, or
    it carries an Arabizi digit / apostrophe."""
    out = []
    for w in tokens(text):
        if is_ar(w):
            out.append(w)
            continue
        if re.fullmatch(r"[A-Za-z](-[A-Za-z])+", w):
            continue  # spelling letters out
        if (is_english(w) and w.lower() not in LATIN_AR) or len(w) < 2:
            continue
        if lexicon is None or looks_arabic_latin(w, lexicon):
            out.append(w)
    return out


# Short Arabic words Scribe writes in Latin that no rule below would catch.
LATIN_AR = set("""
ana inti inta intu ihna e7na huwe huwwe hiye hiyye humme ma mish mush fi bas u wa la lal hon hoon shu
kif keef lesh laish iza lamma lama kaan kan kanu kanit kunt kunet ya yalla shway shwai kteer katir
anna andi andak andik andna andu andhum fih fiha fihom fihum ili illi ilak ilik
saa saa3a sa3a yom yoam youm sane sana shahr marra hek heik hayk
""".split())
AR_PREFIX = re.compile(r"^(bi|ba|bt|bn|by|ma|mi|ya|yi|ta|ti|il|el|al|fi|wa|mu)[a-z']{2,}")
AR_SUFFIX = re.compile(r"[a-z']{2,}(ik|ak|ek|na|hom|hum|kom|kum|it|et|ti|ni|ha|tu|li|lu|lak|lik|u|o)$")


def looks_arabic_latin(w, lexicon=None):
    """Is this Latin token Arabic said aloud (not English)?"""
    lw = (w or "").lower().strip("-'")
    if lw in LATIN_AR:
        return True
    if not lw or is_english(lw) or len(lw) < 2:
        return False
    if re.search(r"[a-z][235789]|[235789][a-z]|[a-z]'[a-z]", lw):
        return True
    s = skel(lw)
    if lexicon is not None and len(s) >= 2 and (s in lexicon or bare(lw) in lexicon):
        return True
    return bool(AR_PREFIX.match(lw) or AR_SUFFIX.match(lw)) and len(s) >= 2


# ---------------------------------------------------------------- chat clock
def chat_offset(chat, turns, local=600.0):
    """Seconds to add to each Meet-chat stamp to put it on the recording clock.

    Amal usually reads out what she just typed, or types what Medi just said.
    Pair each typed line with the voice turn around it that shares most of its
    skeleton. The chat clock drifts during a lesson, so each line takes the
    median gap of the pairs within `local` seconds of it (the whole-lesson
    median when none are near). Returns one offset per chat line.
    """
    voice = [t for t in turns if not t.get("chat")]
    vs = [(t["start"], {skel(w) for w in tokens(t["text"]) if not is_english(w) and len(skel(w)) >= 2}) for t in voice]
    gaps = []
    for c in chat:
        cs = {skel(w) for w in tokens(c["text"]) if not is_english(w) and len(skel(w)) >= 2}
        if len(cs) < 3:
            continue
        best = None
        for t0, s in vs:
            if abs(t0 - c["start"]) > 240 or not s:
                continue
            ov = len(cs & s) / len(cs)
            if ov >= 0.5 and (best is None or ov > best[0]):
                best = (ov, t0 - c["start"])
        if best:
            gaps.append((c["start"], best[1]))
    if len(gaps) < 3:
        return [0.0] * len(chat)
    whole = float(median(g for _, g in gaps))
    out = []
    for c in chat:
        near = [g for t, g in gaps if abs(t - c["start"]) <= local]
        out.append(float(median(near)) if len(near) >= 2 else whole)
    return out
