# -*- coding: utf-8 -*-
"""Full grammar audit across every transcribed lesson.

Finds the places where Amal corrected Medi and files each one under a grammar
bucket from docs/data/grammar-buckets.json.

Where a correction can come from (all on one clock, see lesson_turns.py):
  voice   Amal re-says his word in a different shape within 25 s
  chat    Amal types the fixed sentence into the Meet chat (Arabizi)
  english Amal names the rule in English ("it's feminine", "which preposition?")

His Arabic is compared in any script - Arabic letters, Scribe's Latin
("kharabit"), her Arabizi ("5arrabti") - through the consonant skeleton in
xscript.py. One Medi turn can hold several corrections. The same fix said
twice (he repeats, she repeats) is one event.

Output: docs/data/grammar-audit.json. Every row is a machine candidate
("verified": false). Nothing here moves a score until Amal or Medi ticks it.
UNFILED is the honest answer when no rule fits.
"""
import json, os, re, sys, difflib, html
from collections import Counter, defaultdict

SCRIPTS = r"C:\dev\anees-hourly\scripts"
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
from xscript import key, skel, bare, has_al, is_ar, is_english, tokens, arabic_tokens, sim  # noqa: E402

ANEES = r"C:\dev\anees\data\lessons"
DOCS = r"C:\dev\anees-hourly\docs"
OUT = os.path.join(DOCS, "data", "grammar-audit.json")

WINDOW = 25.0        # her voice reply within this long after he stops
CHAT_BACK = 150.0    # a typed line looks this far back for what he said
CHAT_AHEAD = 90.0    # she sometimes types the model sentence while he is still trying
ENGLISH_WINDOW = 20.0
REPEAT = 90.0        # the same fix again within this long is the same event

AR = re.compile(r"[\u0600-\u06FF]")


# ---------------------------------------------------------------- display
def mark(tokens_, flags, cls):
    """Rebuild a sentence, wrapping flagged tokens in a <mark>."""
    out, run = [], []
    for tok, on in zip(tokens_, flags):
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


def _ar_words(s):
    return [w for w in tokens(s) if is_ar(w) or not is_english(w)]


def diff_spans(said, recast, arabic_only=True, wrong_word=None, fixed_word=None):
    """Underline what changed. Words are compared by skeleton, so the same
    word in Arabic letters and in Latin letters counts as unchanged."""
    a = _ar_words(said) if arabic_only else tokens(said)
    b = _ar_words(recast) if arabic_only else tokens(recast)
    sa, sb = [skel(w) + ("L" if has_al(w) else "") for w in a], [skel(w) + ("L" if has_al(w) else "") for w in b]
    sm = difflib.SequenceMatcher(a=sa, b=sb, autojunk=False)
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
    # Always underline the pair the classifier used, even when the skeleton
    # calls it "the same word" (a vowel or an ending changed).
    if wrong_word:
        for i, w in enumerate(a):
            if w == wrong_word:
                fa[i] = True
    if fixed_word:
        for j, w in enumerate(b):
            if w == fixed_word:
                fb[j] = True
    return {
        "said_html": mark(a, fa, "ab-wrong"),
        "recast_html": mark(b, fb, "ab-correct"),
        "wrong": [w for w in wrong if w.strip()],
        "fixed": [w for w in fixed if w.strip()],
        "changed": sum(fa) + sum(fb),
    }


# ---------------------------------------------------------------- run
PRAISE = re.compile(r"✓|ممتاز|برافو|\bperfect\b|\bexactly\b|\bgood job\b|\bawesome\b|\bnice\b|\bgreat\b|\bcorrect\b", re.I)
CONTRAST = re.compile(r"\b(not|no|just|only|instead of)[,.]?\s+(the\s+)?[\u0600-\u06FF]|[\u0600-\u06FF]+[،,]?\s+(not|مش)\s|"
                      r"(^|\s)مش\s|(^|\s)لا[،,.]?\s+[\u0600-\u06FF]|\bno[,.]?\s+no\b|\bneither\b", re.I)

# Small closed word families. Two members of one family are the same word in
# a different shape; a swap between families is a different word.
FAMILY_KEYS = {
    "3ind": r"^'?[aiu]?n(d|n|a$|ak$|ik$|i$|u$|kum$|hum$)", "fi": r"^fi(h|ha|hum|hm|na|k|ki)?[a]?$|^f(ih|iha|ihum|ina|iu|ihm)$",
    "ma3": r"^ma?'a?(k|ak|ik|i|u|uh|ha|hum|na|kum)?$", "3ala": r"^('a?|a)la(i|ik|ak|iha|ihum|hum|ha|ina|kum|ih|iik)?$",
    "hada": r"^h[aei]?(d|z)[aei]?[ai]?$|^hdul|^hadul|^hadi|^haza|^hazi|^hadak|^hadik",
    "kaan": r"^k(a|aa|i|u|uu)?n(it|at|t|u|ua|tu|ti|na|tum|tu)?$",
    "koon": r"^(b|t|y|n|a)?[aiu]?k(u|uu)n(i|u|ua|a|t|ti|tu|na|u)?$",
    "neg": r"^(ma|mish|mush|mis|la)$",
    "min": r"^m(i|u)?n$",
    "li": r"^l(ak|ik|ek|u|uh|ha|hum|hm|na|kum|km|i|ii)$",
    "3an": r"^'?[aiu]?n(ak|ik|u|uh|ha|hum|hm|k|kum)?$",
    "bi": r"^bi?(k|ik|ak|u|ha|hum|na)?$",
}
PREPS = {"3ind", "fi", "ma3", "3ala", "min", "li", "3an", "bi"}
PREP_SKEL = {"b", "l", "mn", "n", "'l", "l", "f", "m'", "'n"}

GATE_MODAL = ("بدي", "بدك", "بدها", "لازم", "ممكن", "بحب", "بقدر", "biddi", "laazem", "lazim", "mumken", "ba2dar", "badi")
GATE_TIME = ("لما", "إذا", "اذا", "عشان", "قبل ما", "بعد ما", "حتى", "lamma", "lama", "iza", "3ashan", "ashan")

SUPERL = re.compile(r"أحسن|احسن|أكتر|اكتر|أحلى|احلى|أول|اول|أقل|a7san|ahsan|aktar|akthar|a7la|awwal", re.I)
DEMO = re.compile(r"هاد|هادي|هذا|هذي|هدول|haad|hadi|haadi|hada|hayy", re.I)
NUMS = re.compile(r"تلات|ثلاث|ثلث|اربع|أربع|خمس|ست|سبع|تمان|تسع|عشر|عشرين|تلاتين|ثلاثين|talat|thalath|arba3|5ams|sitt|sab3|tamaan|tis3|3ashr|3eshreen|talateen|\b\d+\b", re.I)


def family(w):
    k = key(w)
    if k in ("ana", "'ana", "an", "'na") and not is_ar(w) or re.sub(r"[\u064B-\u0652]", "", w) in ("أنا", "انا", "آنا"):
        return None
    for name, rx in FAMILY_KEYS.items():
        if re.search(rx, k):
            return name
    return None


def tail(w):
    """The last vowel of the word: a (-a / ة), u (-u / -o / وا), i (-i / ي), or ''."""
    if is_ar(w):
        w2 = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", w)
        if re.search(r"(وا|و)$", w2):
            return "u"
        if re.search(r"[أءئؤ]$", w2):
            return "?"
        if re.search(r"[اةى]$", w2):
            return "a"
        if w2.endswith("ي"):
            return "i"
        if w2.endswith("ه"):
            return "o"
        return ""
    lw = re.sub(r"[^a-z0-9]", "", w.lower())
    if re.search(r"[23]$", lw):
        return "?"
    if re.search(r"[0-9]$", lw):
        return ""
    if re.search(r"(ah|eh)$", lw):
        return "?"  # Scribe writes both ة and ح as -ah
    if re.search(r"(a|e)$", lw):
        return "a"
    if re.search(r"o$", lw):
        return "o"
    if re.search(r"(u|ou|oo)$", lw):
        return "u"
    if re.search(r"(i|ee|y)$", lw):
        return "i"
    return ""


def verbish(w):
    """Looks like a verb: a person prefix, or a past-tense ending."""
    if is_ar(w):
        w2 = re.sub(r"^(و|ف)", "", w)
        return bool(re.match(r"^(ي|ت|ن|ب|أ|ا)", w2)) and not w2.startswith("ال") or bool(re.search(r"(ت|تي|تو|نا|وا)$", w2))
    k = key(w).lstrip("'")
    return bool(re.match(r"^(b|y|t|n|a|i)", k)) or bool(re.search(r"(t|it|et|ti|tu|na|u)$", k))


def same_form(x, y):
    """The same word in the same shape, whatever the script."""
    return skel(x) == skel(y) and has_al(x) == has_al(y) and tail(x) == tail(y)


FUNC_KEYS = {"min", "mn", "fi", "ma", "mish", "la", "bi", "bas", "an", "ala", "u", "w", "ia", "ya", "hu", "hi", "ana"}
FUNCTION = {"mn", "f", "m", "l", "n", "b", "bs", "'n", "'l", "S", "hn", "k"}


def doubled(w):
    if is_ar(w):
        return "\u0651" in w
    return bool(re.search(r"([bcdfghjklmnpqrstvwxz567])\1", w.lower()))


PREFIXES = ("bt", "bn", "by", "b", "m", "t", "n", "l", "")
SUFFIXES = ("thm", "th", "hm", "km", "tk", "tn", "nk", "t", "n", "k", "m", "")


def stems(s):
    out = set()
    for p in PREFIXES:
        if not s.startswith(p):
            continue
        for q in SUFFIXES:
            if q and not s.endswith(q):
                continue
            core = s[len(p): len(s) - len(q) if q else len(s)]
            if len(core) >= 2:
                out.add(core)
    return out


# make-X / get-X pairs (bucket B12): the only words where a doubled middle
# letter is grammar. Anywhere else a double is Arabizi spelling.
B12_ROOTS = {"Krb", "Kf", "Kwf", "dhk", "dk", "zhk", "zh", "tb", "zl", "sb", "jhz", "bst", "dk", "tdk", "d", "Gr", "Gyr", "sl"}
PRON_SUFFIX = ("", "h", "m", "hm", "k", "km", "n", "t", "tk", "l", "lk", "lh", "lm")


NUMBER_PAIRS = [
    ("يوم", "ايام", "yoam", "ayyam"), ("ساعة", "ساعات", "saa3a", "saa3aat"), ("شهر", "شهور", "shahr", "shhoor"),
    ("سنة", "سنين", "sane", "sneen"), ("مرة", "مرات", "marra", "marraat"), ("دقيقة", "دقايق", "da2ee2a", "da2aye2"),
    ("اسبوع", "اسابيع", "usboo3", "asabee3"), ("مطعم", "مطاعم", "ma6am", "ma6aa3em"), ("دولة", "دول", "dawle", "duwal"),
    ("ولد", "ولاد", "walad", "wlad"), ("بنت", "بنات", "bint", "banaat"), ("كتاب", "كتب", "ktaab", "kutub"),
]


NUMWORDS = {
    "wahad": 1, "wa7ad": 1, "waa7ad": 1, "tnen": 2, "tenain": 2, "tintain": 2, "talat": 3, "talate": 3, "arba3": 4, "arba3a": 4,
    "5ams": 5, "5amse": 5, "sitt": 6, "sitte": 6, "sab3": 7, "sab3a": 7, "tamaan": 8, "tamanye": 8, "tes3": 9, "tes3a": 9,
    "3ashr": 10, "3ashara": 10, "3eshreen": 20, "talateen": 30,
    "واحد": 1, "تنين": 2, "اتنين": 2, "ثنتين": 2, "تلاتة": 3, "ثلاثة": 3, "اربعة": 4, "أربعة": 4, "خمسة": 5, "ستة": 6,
    "سبعة": 7, "تمانية": 8, "تسعة": 9, "عشرة": 10, "عشرين": 20, "وعشرين": 20, "تلاتين": 30,
}
_NUMK = {}
for _w, _n in NUMWORDS.items():
    _NUMK[key(_w)] = _n


def num_of(w):
    k = key(re.sub(r"^و", "", w) if is_ar(w) else re.sub(r"^u-?", "", w.lower()))
    return _NUMK.get(k)


def number_pair(m, a):
    """'number' when m and a are the singular and plural of one noun."""
    def nk(w):
        w = re.sub(r"^ال", "", w) if is_ar(w) else re.sub(r"^(el|il|al)-", "", w.lower())
        k = key(w).replace("'", "")
        k = re.sub(r"(.)\1+", r"\1", k)
        t = re.sub(r"[aiu]+$", "", k)
        return t if len(t) >= 2 else k

    def which(w):
        k = nk(w)
        for i, forms in enumerate(NUMBER_PAIRS):
            for j, f in enumerate(forms):
                if len(k) >= 2 and (k == nk(f) or (len(k) >= 3 and sim(k, nk(f)) >= 0.85)):
                    return i, j % 2
        return None
    wm, wa = which(m), which(a)
    if wm and wa and wm[0] == wa[0] and wm[1] != wa[1]:
        return "number"
    nm, na = num_of(m), num_of(a)
    if nm and na and nm != na:
        return "numword"
    return None


def related(m, a):
    """How Amal's word a is Medi's word m in another shape, or None.
    Tried without ع first, then with it (weak roots are only ع and vowels)."""
    r = _related(m, a, False)
    if r is None and ("'" in key(m) or "'" in key(a)):
        r = _related(m, a, True)
    return r or number_pair(m, a)


def _related(m, a, ayn):
    if ("ً" in m and key(a).endswith("an")) or ("ً" in a and key(m).endswith("an")):
        return None
    sm, sa = skel(m, ayn=ayn), skel(a, ayn=ayn)
    if not sm or not sa:
        return None
    fm, fa = family(m), family(a)
    if bool(fm) != bool(fa) and (fm in ("neg", "3ind", "fi", "min", "li", "3an", "bi", "ma3", "3ala") or
                                 fa in ("neg", "3ind", "fi", "min", "li", "3an", "bi", "ma3", "3ala")):
        return None
    if fm and fa:
        if fm == fa:
            return None if key(m) == key(a) or (sm == sa and tail(m) == tail(a)) else "family"
        if fm in PREPS and fa in PREPS:
            return "prep"
        return None
    if bare(m, ayn=is_ar(m) and is_ar(a)) == bare(a, ayn=is_ar(m) and is_ar(a)) and has_al(m) != has_al(a) and bare(m) and family(m) is None             and key(re.sub(r"^ال", "", m)).strip("'") not in FUNC_KEYS:
        return "al"
    if len(sm) < 2 and not (len(sm) == 1 and sa == "b" + sm):
        return None
    if len(sa) < 2:
        return None
    if bare(m) == bare(a) and has_al(m) != has_al(a):
        return "al" if bare(m) not in FUNCTION and len(bare(m)) >= 2 else None
    if sa.startswith("m") and not sm.startswith("m") and len(sa) >= 3 and stems(sm) & stems(sa[1:] if len(sa) > 3 else sa) \
            and len(stems(sm) & stems(sa)) and max(len(x) for x in stems(sm) & stems(sa)) >= 3:
        return "participle"
    if re.match(r"^(بال|bil-?|bel-?|bi-?el-?|bi-?il-?)", m.lower()) and not has_al(a):
        rest = m[3:] if is_ar(m) else re.sub(r"^(bi-?el-?|bi-?il-?|bil-?|bel-?)", "", m.lower())
        if skel(rest, ayn=ayn) == sa:
            return "al"
    if sa.startswith("b") and not sm.startswith("b") and len(sm) == 1 and sa == "b" + sm:
        return "b"
    if sa.startswith("b") and not sm.startswith("b") and (sa[1:] == sm or {x for x in stems(sa[1:]) & stems(sm) if len(x) >= 3}):
        return "b"
    for pre, suf in (("bn", "n"), ("bt", "t")):
        if sa.startswith(pre) and sm.endswith(suf) and len(sm) >= 3 and sa[len(pre):] == sm[:-len(suf)]:
            return "b"
    if sm.startswith("b") and not sa.startswith("b") and (sm[1:] == sa or {x for x in stems(sm[1:]) & stems(sa) if len(x) >= 3}):
        return "b"
    if sm == sa:
        if doubled(a) != doubled(m) and (sm in B12_ROOTS or any(r in sm for r in B12_ROOTS if len(r) >= 3))                 and not is_ar(m):
            return "double"
        tm_, ta_ = tail(m), tail(a)
        fem_iyye = bool(re.search(r"(ye|ya|yeh|yah|ية|يه)$", a.lower()))
        if tm_ != ta_ and "?" not in (tm_, ta_) and {tm_, ta_} != {"o", "u"} and ({tm_, ta_} != {"i", "a"} or fem_iyye):
            return "ending"
        return None
    if sa.startswith(sm) and sa[len(sm):] in PRON_SUFFIX:
        if not (sa[len(sm):] == "k" and key(m).endswith("'")):
            return "suffix"
    if sm.startswith(sa) and sm[len(sa):] in PRON_SUFFIX:
        if not (sm[len(sa):] == "k" and key(a).endswith("'")):
            return "suffix"
    if (sm == sa + "k" and key(a).endswith("'")) or (sa == sm + "k" and key(m).endswith("'")):
        return None
    core = {x for x in stems(sm) & stems(sa) if len(x) >= 3}
    if core:
        return "shape"
    core2 = stems(sm) & stems(sa)
    if core2 and len(sm) <= 4 and len(sa) <= 4 and sm[0] == sa[0]:
        return "shape"
    for p_ in ("t", "y", "n", "m"):
        if (sm == p_ + sa or sa == p_ + sm) and len(min(sm, sa, key=len)) >= 2:
            return "prefix"
    return None


def english_cue(recast, said):
    """A rule Amal named in English, with the bucket it points at."""
    r = recast.lower()
    if re.search(r"\bnot (a |the )?(pointer|feminine|masculine|present|past|plural|singular)\b", r):
        return None
    if re.search(r"\b(is|it's|its|be|for|so|was)\s+(a\s+)?(feminine|masculine|woman)\b|\b(feminine|masculine)\?|has to be (masculine|feminine)", r):
        return "A10" if DEMO.search(said + " " + recast) and re.search(r"هذ|هاد|hadi|hada|haadi", recast + said) else "A8"
    if re.search(r"\bpointer\b", r):
        return "C2"
    if re.search(r"preposition|أي حرف", r):
        return "D1"
    if re.search(r"\bnot present\b|\bis past\b|past tense", r):
        return "B5"
    if re.search(r"\bpresent\b", r) and re.search(r"\bnot\b|\bno\b|\bsay\b|\bit's\b|\bis\b", r):
        return "B1"
    if re.search(r"\bone l\b|\bthe l\b|put the l|\bone ال|the ال", r):
        return "A2"
    if re.search(r"\bplural\b|\bsingular\b", r):
        return "E1" if re.search(r"\bkam\b|\bcam\b|كم|number|\b\d+\b", r + " " + said.lower()) else "A9"
    if re.search(r"\bfirst\b.*\bthen\b|\bthe \w+ first\b", r):
        return "C3" if SUPERL.search(said) or "best" in r else "E4"
    if re.search(r"\b(it's|is|it is|needs? to be|should be) (a )?command\b", r):
        return "B10"
    return None


def looks_past(w):
    return bool(re.search(r"(ت|تي|تو|نا|وا)(ه|ها|هم|ك|كي|كم|ني)?$", w)) if is_ar(w) else bool(re.search(r"(t|it|et|ti|tu|na)(u|o|ha|hum|ak|ik|ni)?$", w.lower()))


def classify(m, a, said, recast, change):
    """(bucket, why) for one wrong word m and her word a, or None."""
    km, ka = key(m), key(a)
    sm, sa = skel(m), skel(a)
    if len(sm) < 2 or len(sa) < 2:
        sm, sa = skel(m, ayn=True), skel(a, ayn=True)
    ctx = said + " " + recast
    fm, fa = family(m), family(a)

    if change == "family":
        if fm == "3ind":
            return ("D3", "the ending on 3ind")
        if fm == "fi":
            return ("D3", "the ending on fi")
        if fm == "hada":
            fem = lambda w: key(w).endswith("i")
            if fem(m) == fem(a):
                return None
            return ("A10", "hada / hadi must match the noun")
        if fm == "kaan":
            if re.search(r"راح|ra7|ra'ah|\bra\b", recast) and not re.search(r"راح|ra7", said.split()[0] if said.split() else ""):
                return ("B13", "kaan + ra7 = was going to")
            if re.search(r"لازم|laazem|lazim", ctx):
                return ("B16", "kaan + laazem")
            return ("B6", "kaan takes the person")
        if fm == "koon":
            mb_, ab_ = skel(m).startswith("b"), skel(a).startswith("b")
            if mb_ != ab_:
                gate = next((g for g in GATE_MODAL + GATE_TIME if g in said), None)
                if ab_ and not mb_:
                    return ("B4b", "the b- comes back" + (" outside " + gate if gate else ""))
                return ("B2" if gate in GATE_MODAL else "B3", "the b- drops after " + (gate or "the trigger"))
            return ("B9", "wrong person on ykoon")
        if fm == "neg":
            return ("C4", "ma vs mish")
    if change == "insert":
        if fa == "kaan":
            if re.search(r"راح|ra7", recast):
                return ("B13", "kaan + ra7 = was going to")
            if re.search(r"لازم|laazem|lazim", recast):
                return ("B16", "kaan + laazem")
            return ("B6", "kaan = was")
        if fa == "koon":
            return ("B8", "this slot needs ykoon")
        if fa == "neg":
            return ("B11", "the negative command needs ma") if re.match(r"^(t|w|y)", km) or re.search(r"(i|ini|u)$", km) else ("C4", "the ma was missing")
        if fa == "fi":
            return ("D1", "the preposition was missing")
        return ("C7", "illi was missing")
    if change == "prep":
        ws = tokens(said)
        if m in ws:
            i_ = ws.index(m)
            if i_ > 0 and verbish(ws[i_ - 1]) and not family(ws[i_ - 1]):
                return ("D2", "the verb wants a different preposition")
        return ("D1", "a different preposition")
    if fa == "3ind" and fm != "3ind" and fm is not None:
        return ("D1", "a different preposition")
    if fa == "koon" and fm != "koon":
        return ("B8", "this slot needs ykoon")
    if fa == "kaan" and re.search(r"راح|ra7", recast):
        return ("B13", "kaan + ra7 = was going to")

    if change == "al":
        if re.match(r"^(بال|bil-?|bel-?)", m.lower()) and not has_al(a):
            return ("A2", "idafa: the first noun takes no el-")
        if SUPERL.search(ctx):
            return ("C3", "no el- after a superlative")
        ws = tokens(recast)
        if has_al(a) and a in ws:
            i_ = ws.index(a)
            if i_ > 0 and has_al(ws[i_ - 1]):
                return ("A7", "the adjective takes el- like its noun")
        if has_al(m) and not has_al(a):
            ws = tokens(recast)
            nxt = next((ws[i + 1] for i, w in enumerate(ws[:-1]) if w == a), None)
            if nxt and has_al(nxt):
                return ("A2", "idafa: the el- goes on the owner")
            return ("A1", "el- added or dropped")
        if DEMO.search(ctx) and not has_al(m):
            return ("A10b", "the noun after hada keeps its el-")
        return ("A1", "el- added or dropped")

    if change == "b":
        if sm.startswith("b") and not sa.startswith("b") and looks_past(a):
            return ("B5", "past tense, not the present")
        root = sa[1:] if sa.startswith("b") else sa
        if (doubled(a) != doubled(m) and not is_ar(m) and any(r in root for r in B12_ROOTS if len(r) >= 2)) or \
                (root in B12_ROOTS and not is_ar(a) and re.search(r"(aw|aww|arr|all|abb)", a.lower())):
            return ("B12", "make-X vs get-X: the middle letter doubles")
        if re.match(r"^(بال|بل|bil-?|bel-?|bi-?el-?|b-?il-?)", a.lower()):
            return ("D1", "the preposition bi- was missing")
        if is_ar(a) and re.search(r"(ك|كي|ها|هم|نا|تي|تك)$", a) and re.search(r"(ik|ak|ek|ha|hum|na|ti|tik)$", key(m)):
            return ("D1", "the preposition bi- was missing")
        mb = sm.startswith("b")
        gate = next((g for g in GATE_MODAL + GATE_TIME if g in said), None)
        if gate and mb:
            return ("B2" if gate in GATE_MODAL else "B3", "the b- drops after " + gate)
        if gate and not mb:
            return ("B4b", "the b- comes back outside " + gate)
        if re.search(r"(ت|ت?و|ا|نا|وا)$", m) and not mb and is_ar(m) and re.search(r"(نا|وا|يت|ت)$", m):
            return ("B1", "present with b-, not the past")
        return ("B1", "the b- prefix")

    if change == "double":
        return ("B12", "make-X vs get-X: the middle letter doubles")

    if change == "ending":
        tm, ta = tail(m), tail(a)
        pron_a = re.search(r"(ها|هم|ك|كي|كم|نا)$", a) if is_ar(a) else re.search(r"(ha|hum|hom|ak|ik|kum|na)$", a.lower())
        pron_m = re.search(r"(و|ه|ها|هم|ك|كي|كم|نا)$", m) if is_ar(m) else re.search(r"(u|o|ha|hum|hom|ak|ik|kum|na)$", m.lower())
        if pron_a and pron_m and pron_a.group(1) != pron_m.group(1):
            return ("D4", "the ending on the verb") if verbish(m) else ("A4", "the possessive ending")
        if verbish(a) and (re.search(r"(يت|ت|تي|نا)$", a) if is_ar(a) else re.search(r"(it|et|ti|na)$", a.lower())):
            return ("B5", "the past tense ending")
        if ta in ("o", "h") and tm in ("", "a", "i", "u") and verbish(m):
            return ("C2", "the pointer ending was missing")
        if "a" in (tm, ta) and not re.search(r"^(ma|mish)\b", ka):
            return ("A8", "feminine agreement")
        if ta == "u" and tm != "u":
            return ("B1", "wrong person ending on the verb")
        if tm == "i" and ta == "" and re.match(r"^(b|t)", km.lstrip("'")):
            return ("B1", "wrong person ending on the verb")
        if ta == "i" and tm != "i":
            if re.search(r"^(ma )?t", ka) or re.search(r"^ت", a):
                return ("B10", "the command takes -i for a woman")
            return ("D4", "the ending on the verb")
        return None

    if change == "numword":
        if re.search(r"ألفين|الفين|alfain|alfein|سنة|شهر|تسعة|يوم|yoam|الساعة|saa3a", ctx):
            return ("E2", "clock time") if re.search(r"الساعة|saa3a|إلا|illa|ربع|rube3|نص|ثلث", ctx) else ("E4", "the date")
        return None
    if change == "number":
        n = NUMS.search(ctx)
        big = re.search(r"عشر|عشرين|تلاتين|ثلاثين|اربعين|خمسين|مية|3ashr|3eshreen|talateen|\b(1[1-9]|[2-9]\d)\b", ctx, re.I)
        if big:
            return ("E1", "11 and up takes a singular noun")
        if n:
            return ("E3", "three-to-ten takes the plural")
        return ("A9", "plural")
    if change == "participle":
        return ("B15", "the participle, not the verb")
    if change in ("shape", "prefix", "suffix", "ending"):
        km_, ka_ = re.sub(r"^'", "", km), re.sub(r"^'", "", ka)
        he, she = re.match(r"^(bi|by|yi|y|bii)", km_), re.match(r"^(bit|bt|ti|t|bet|bitt)", ka_)
        she2, he2 = re.match(r"^(bit|bt|ti|t|bet)", km_), re.match(r"^(bi|by|yi|y|bey|bii)[^t]", ka_)
        if (he and she and not re.match(r"^(bit|bt|ti|t)", km_)) or (she2 and he2):
            return ("A8", "the verb agrees with a feminine subject")
        if sm == "t" + sa and not sa.startswith("b"):
            if re.search(r"(na|nا|u|ua|it|at|t)$", ka) or re.search(r"(نا|وا|ت)$", a):
                return ("B5", "the past tense takes no t-")
            return ("B10", "the command drops the t-")
        if sa.startswith("m") and (sm.startswith("b") or sm.startswith("t")) and stems(sm) & stems(sa):
            return ("B15", "the participle, not the verb")

    if change in ("suffix", "shape") and any(g in said for g in GATE_MODAL) and \
            re.search(r"(ت|t|it)$", m) and not re.search(r"(ت|t)$", a) and stems(sm) & stems(sa):
        return ("B2", "after a modal the verb is the bare present, not the past")
    if change in ("suffix", "shape"):
        a_past0 = bool(re.search(r"(ت|تي|نا|وا)(ه|ها|هم|ك|كي|كم|ني)?$", a) and is_ar(a)) or \
            bool(re.search(r"(t|ti|tu|na)(u|ha|hum|ak|ik|ni)?$", key(a)) and not is_ar(a))
        m_imperf0 = bool(re.match(r"^(b|a|t|y|n)", key(m).lstrip("'"))) and not re.search(r"(t|ti|na)$", key(m))
        if a_past0 and m_imperf0 and stems(sm) & stems(sa):
            return ("B5", "past tense")
        # an ending grew on the same word: pointer on a verb, possessive on a noun
        if sa.startswith(sm) and len(sa) > len(sm) and len(sm) >= 2:
            verb = verbish(m) and not has_al(m) and len(sm) >= 3
            if has_al(m) or not verb:
                return ("A4", "the possessive ending")
            return ("C2", "the pointer ending was missing")
        if sm.startswith(sa) and sm[len(sa):].startswith("l") and len(sa) >= 2:
            return ("D3", "li is its own word with its ending")
        if sm.startswith(sa) and len(sm) > len(sa) and not sa.endswith("t") and re.match(r"^(b|t|y|n|a)", km.lstrip("'")):
            return ("D4", "the ending on the verb")
        # number + noun
        if NUMS.search(ctx):
            if re.search(r"يوم|yoam|youm|yawm", a) and re.search(r"ايام|أيام|ayyam|ayam", m):
                return ("E1", "11 and up takes a singular noun")
            if re.search(r"ساعات|sa3aat|saa3aat", a):
                return ("E3", "three-to-ten takes the plural")
            if re.search(r"ساعة|sa3a", a) and re.search(r"ساعية|ساعي", m):
                return ("E2", "clock time")
        # past vs present
        m_imperf = bool(re.match(r"^(b|a|t|y|n)", sm)) and not sm.endswith("t")
        a_past = bool(re.search(r"(t|tu|na|u)$", key(a)) or re.search(r"(ت|تي|نا|وا)$", a)
                      or re.search(r"(ت|تي|نا|وا)(ه|ها|هم|ك|كي|كم|ني)$", a) or re.search(r"(t|ti|na)(u|ha|hum|ak|ik|ni)$", key(a)))
        a_imperf = bool(re.match(r"^(b|a|t|y|n)", sa))
        if a_past and m_imperf and not a_imperf:
            return ("B5", "past tense")
        # plural of a noun (broken plural)
        if re.search(r"مطاعم|ma6aa3em|mata3em", a):
            return ("A9", "plural")
        if a_past and stems(sm) & stems(sa) and not has_al(m):
            return ("B5", "the past tense ending")
        # possessive / object ending changed on the same stem
        if stems(sm) & stems(sa):
            if sm[-1:] != sa[-1:] or len(sm) != len(sa):
                if re.match(r"^(b|t|y|n|a)", sa):
                    return ("D4", "the ending on the verb")
                return ("A4", "the possessive ending")
    return None


def person_swap(m, a):
    """I-form -> you-form of the same verb: she is talking to him, not fixing him."""
    km, ka = key(m), key(a)
    km = re.sub(r"^'", "", km)
    ka = re.sub(r"^'", "", ka)
    for p1, p2 in (("a", "t"), ("ba", "bt"), ("n", "t"), ("bn", "bt")):
        if km.startswith(p1) and ka.startswith(p2) and skel(km[len(p1):]) == skel(ka[len(p2):]):
            return True
    return False


ASK = re.compile(r"\bdo i (just |still |only )?say\b|شو يعني|شو معنى|what was|what does .* mean|what's the word|"
                 r"(would|wouldn't|does|doesn't|will|won't|can|could)\s+(it|that|this)\s+work|can i use|could i use|"
                 r"\b(is it|isn't it|would it be|would i say|do i say|do you say|can i say|how do i say|should it be|"
                 r"or is it|what's|what is|is there a difference|is that)\b|,?\s*right\s*\?", re.I)
CONFIRM = re.compile(r"^\W*(صح|صحيح|آه صح|اه صح|yes|yeah|yep|exactly|mm-hmm|mhm|ممتاز|perfect|right)\b", re.I)
INSTRUCT = re.compile(r"(^|\s)(احكي|احكيلي|قول|قولي|جرب|اسأل|خلينا|يلا|يلّا)(\s|$|[،,.])")
ALTERNATIVE = re.compile(r"another (term|way|word)|you (can|could) (also )?say|some people say|^\s*(or|أو)\b", re.I)


def is_ask(M):
    """Medi asking which form is right - rule M1 counts it as an ask."""
    if M.get("ask_tail"):
        return True
    t = M["text"]
    eng = sum(1 for w in tokens(t) if is_english(w))
    if re.search(r"^\W*(hold on\.?\s*|so\s+|okay\.?\s*|oh,?\s*)?(is|does|do|can|should|would|are|was|did|isn't|doesn't)\b[^.]*[?؟]", t, re.I):
        return True
    first = tokens(t)[:1]
    if first and not is_english(first[0]) and re.match(r"^\W*\S+\s+(is|means|meant|was)\b", t, re.I):
        return True
    return bool(ASK.search(t))


TRACE = [] if os.environ.get("AUDIT_TRACE") else None
CUR_DATE = [None]


def _drop(M, m, a, ch, A, why):
    if TRACE is not None:
        TRACE.append({"date": CUR_DATE[0], "t": round(M["start"], 1), "A_t": round(A["start"], 1), "m": m, "a": a,
                      "change": ch, "dropped": why, "said": M["text"][:80], "recast": A["text"][:80]})
    return False


def keep_pair(M, m, a, ch, A, question, window):
    """Last checks on one candidate. False = not a correction."""
    # he is only repeating a word she just said (a one-word turn): she is
    # teaching him the word, not fixing a sentence of his
    if ch != "insert" and len(M["ar"]) <= 1 and any(
            B["speaker"] == "Amal" and not B.get("chat") and M["start"] - 30 <= B["start"] < M["start"]
            and any(same_form(m, w) and sim(key(m), key(w)) >= 0.75 for w in B["ar"]) for B in A.get("_T", [])):
        return _drop(M, m, a, ch, A, "echoing-her")
    # her prompt for the next drill, or her question about meaning
    if re.search(r"what about|how about|what does|what's .* mean|شو يعني|شو معنى|put it in a sentence|another one", A["text"], re.I):
        return _drop(M, m, a, ch, A, "her-prompt")
    if ch == "ending" and a in A["ar"]:
        j = A["ar"].index(a)
        if j > 0 and re.sub(r"[\u064B-\u0652]", "", A["ar"][j - 1]) in ("أنا", "انا", "ana"):
            return _drop(M, m, a, ch, A, "about-herself")
    if INSTRUCT.search(A["text"]) and ch in ("prep", "al", "ending", "suffix", "shape"):
        return _drop(M, m, a, ch, A, "her-instruction")
    if CONFIRM.search(A["text"]) and not re.search(r"\b(no|not|but)\b|مش|(^|\s)بس(\s|$)|\bbas\b", A["text"], re.I) \
            and not A.get("chat"):
        return _drop(M, m, a, ch, A, "she-confirmed")
    # "في or ب": she offers his form as one of the right ones
    if re.search(r"(\bor\b|\sأو\s)", A["text"]) and any(same_form(m, w) for w in A["ar"]):
        return _drop(M, m, a, ch, A, "his-form-is-an-option")
    # vowel marks on her word: she is teaching the sound, not the grammar
    if ch in ("al", "ending") and re.search(r"[\u064B-\u0650]", a):
        return _drop(M, m, a, ch, A, "pronunciation")
    if ALTERNATIVE.search(A["text"]):
        return _drop(M, m, a, ch, A, "alternative")  # she offers another way to say it, not a fix
    if any(same_form(w, a) for w in M["ar"]) and ch not in ("insert",) and not CONTRAST.search(A["text"]):
        return _drop(M, m, a, ch, A, "said-her-form-same-turn")  # he said her form in the same breath (unless she says "not X")
    if question and A.get("chat") and ch == "al":
        return _drop(M, m, a, ch, A, "chat-question-al")
    if ch in ("shape", "suffix", "ending") and person_swap(m, a):
        return _drop(M, m, a, ch, A, "her-you-form")
    if ch == "b" and skel(m).startswith("b") and not skel(a).startswith("b") and not looks_past(a):
        # she took the b- off: only a rule after a trigger word (B2/B3)
        if re.match(r"^(بال|bil|bel|bi-?el|bi-?il)", m.lower()):
            return _drop(M, m, a, ch, A, "bi-preposition")  # that b- is the preposition bi-, not the verb prefix
        if not any(g in M["text"] for g in GATE_MODAL + GATE_TIME):
            return _drop(M, m, a, ch, A, "b-drop-no-gate")
    if ch == "al" and question and not A.get("chat"):
        return _drop(M, m, a, ch, A, "question-al")  # she is asking her own question with the word in it
    # he said her form himself before she spoke: that is his own fix
    for N in A.get("_medi_all", window):
        if M["start"] < N["start"] < A["start"] and any(same_form(w, a) for w in N["ar"]):
            return _drop(M, m, a, ch, A, "self-fixed-before-her")
        if M["start"] - 30 <= N["start"] < M["start"] and ch == "b" and \
                any(same_form(w, a) and sim(key(w), key(a)) >= 0.8 for w in N["ar"]):
            return _drop(M, m, a, ch, A, "he-knew-it")
    return True


def align(stretch, A, aw):
    """(pairs, anchors) for her words against one stretch of his, or (None, 0)
    when too few of her words sit in it to call it a re-saying."""
    out = []
    ms = [(w, M) for M in stretch for w in M["ar"]]
    sa_ = [bare(w) for w in aw]
    sm_ = [bare(w) for w, _ in ms]
    blocks = difflib.SequenceMatcher(a=sm_, b=sa_, autojunk=False).get_opcodes()
    anchors = sum(i2 - i1 for op, i1, i2, j1, j2 in blocks if op == "equal")
    short_side = min(len(aw), len(ms)) or 1
    if anchors == 0:
        return None, 0
    if A.get("chat") and (anchors / short_side < 0.5 or (anchors < 2 and len(ms) > 2)):
        return None, 0
    if not A.get("chat") and anchors / len(aw) < 0.25:
        return None, 0
    for bi, (op, i1, i2, j1, j2) in enumerate(blocks):
        if op == "equal":
            # same bare skeleton: an article or an ending may still differ
            for k in range(i2 - i1):
                (m, M), a = ms[i1 + k], aw[j1 + k]
                ch = related(m, a)
                if ch in ("al", "ending") and (i2 - i1) < 2 and len(aw) > 2:
                    continue  # one word in common is not a re-said sentence
                if ch in ("al", "ending", "double", "family"):
                    out.append((M, m, a, ch))
            continue
        anchored = (bi > 0 and blocks[bi - 1][0] == "equal") or (bi + 1 < len(blocks) and blocks[bi + 1][0] == "equal")
        both = (bi > 0 and blocks[bi - 1][0] == "equal") and (bi + 1 < len(blocks) and blocks[bi + 1][0] == "equal")
        if op == "insert" and both and (j2 - j1) <= 2 and i1 > 0:
            # she added a small grammar word he left out: kaan, ykoon, illi, a preposition
            for j in range(j1, j2):
                a = aw[j]
                fa_ = family(a)
                if fa_ in ("kaan", "koon") or re.fullmatch(r"(اللي|إللي|illi|elli|lli|يلي)", a.lower()):
                    m, M = ms[i1 - 1]
                    out.append((M, m, a, "insert"))
            continue
        if op != "replace" or (i2 - i1) > 3 or (j2 - j1) > 3 or not anchored:
            continue
        for i in range(i1, i2):
            m, M = ms[i]
            for j in range(j1, j2):
                a = aw[j]
                ch = related(m, a)
                if ch:
                    out.append((M, m, a, ch))
                    break
    return out, anchors


def pair_up(window, A):
    """The corrections in one reply of Amal's.

    Short reply (1-2 words): she said the fixed word on its own; pair it with
    his most recent turn only.
    Longer reply or a typed line: she re-said his sentence. Line the two up by
    skeleton; a changed word must sit next to words she kept (an anchor),
    otherwise it is a new sentence, not a correction.
    """
    out = []
    aw = A["ar"]
    eng_words = sum(1 for w in tokens(A["text"]) if is_english(w))
    if len(aw) <= 2 and not A.get("chat"):
        if eng_words >= 4 and (re.search(r"[?؟]", A["text"]) or not re.search(r"\b(no|not|just)\b|مش", A["text"], re.I)):
            return []  # a question or a comment with the word in it, not a fix
        qm = re.match(r"^\W*(شو|وين|كيف|ليش|مين|قديش|أي|shu|sho|wain|wein|keef|kif|laish|meen|2addaish)\b", A["text"], re.I)
        if qm and not any(bare(w) == bare(qm.group(1)) for M in window[-2:] for w in M["ar"]):
            return []  # she is asking him something ("شو فيه؟"), not re-saying his question
        last = window[-1]
        near = [M for M in window if last["start"] - M["start"] <= (12 if len(last["ar"]) <= 1 else 6)]
        for a in aw:
            for M in reversed(near):
                hit = None
                cands_ = []
                for m in M["ar"]:
                    if same_form(m, a):
                        continue
                    ch = related(m, a)
                    if ch in ("suffix", "shape", "prefix", "ending") and bare(a) in FUNCTION:
                        continue
                    if ch == "ending" and len(skel(m)) < 3:
                        continue  # too short to trust on its own
                    if ch and ch != "shape" or (ch == "shape" and len(skel(a)) >= 3):
                        # he already says her form in the same turn: not a fix
                        if any(same_form(w, a) for w in M["ar"]):
                            continue
                        cands_.append((M, m, a, ch))
                if cands_:
                    rank = {"family": 0, "prep": 0, "b": 1, "al": 1, "number": 1, "numword": 1, "double": 1,
                            "participle": 1, "prefix": 2, "suffix": 2, "ending": 3, "shape": 4}
                    hit = min(cands_, key=lambda c: rank.get(c[3], 5))
                if hit:
                    out.append(hit)
                    break
            else:
                fa_ = family(a)
                his = [w for M in near for w in M["ar"]]
                ok_neg = fa_ != "neg" or (key(a) == "ma" and re.search(r"[.?!؟]\s*$", A["text"]))
                if fa_ in ("koon", "kaan", "neg") and ok_neg and not any(family(w) == fa_ for w in his) and his and len(aw) == 1 \
                        and not A.get("prev_amal_ar"):
                    out.append((last, last["ar"][-1], a, "insert"))
        kind = "spot"
    else:
        # Line her reply up against a stretch of his speech (a turn and what he
        # said in the 12 s after it). A voice reply answers one stretch - the
        # one sharing most words with it, the latest on a tie. A typed line can
        # sum up several of his sentences, so each stretch it matches is used.
        want = {bare(w) for w in aw}
        cands = []
        for i, M0 in enumerate(window):
            st = [N for N in window[i:] if N["start"] - M0["start"] <= 12]
            n = len({bare(w) for N in st for w in N["ar"]} & want)
            if n:
                cands.append((n, M0["start"], st))
        cands.sort(key=lambda c: (-c[0], -c[1]))
        chosen, used = [], set()
        for n, t0, st in cands:
            ids = {id(N) for N in st}
            if ids & used:
                continue
            chosen.append(st)
            used |= ids
            if not A.get("chat") or len(chosen) == 3:
                break
        anchors = 0
        for st in chosen:
            got, anc = align(st, A, aw)
            if got is None:
                continue
            anchors = max(anchors, anc)
            out.extend(got)
        ms = [(w, M) for st in chosen for M in st for w in M["ar"]]
        sm_ = [bare(w) for w, _ in ms]
        # kaan / ykoon / illi she adds anywhere in a re-said sentence he never used
        his = [w for w, _ in ms]
        for j, a in enumerate(aw):
            fa_ = family(a)
            if fa_ not in ("kaan", "koon") and not re.fullmatch(r"(اللي|إللي|illi|elli|lli|يلي)", a.lower()):
                continue
            if any(family(w) == fa_ for w in his) or (fa_ is None and any(re.fullmatch(r"(اللي|إللي|illi|elli|lli)", w.lower()) for w in his)):
                continue
            # the word right after hers must be one he said (her addition sits in his sentence)
            # (said as he said it, or in the shape she fixed it to)
            nxt = aw[j + 1] if j + 1 < len(aw) else None
            if not nxt or not any(bare(w) == bare(nxt) or related(w, nxt) in ("suffix", "ending", "shape", "b") for w in his):
                continue
            if fa_ == "kaan" and not re.search(r"^(راح|ra7|ra'ah|لازم|laazem|lazim)$", nxt.lower()):
                continue
            m, M = next(((w, N) for w, N in ms if bare(w) == bare(nxt)), (None, None))
            if m is None:
                m, M = next(((w, N) for w, N in ms if related(w, nxt)), (None, None))
            if m and not any(o[2] == a for o in out):
                out.append((M, m, a, "insert"))
        kind = "chat" if A.get("chat") else "echo"
    for mt in re.finditer(r"(\S+?)[،,]?\s+(?:not|مش|mish)\s+([^\s.,،؟?]+)", A["text"]):
        right, wrong = mt.group(1), mt.group(2)
        for M in reversed(window):
            m = next((w for w in M["ar"] if skel(w) and
                      (same_form(w, wrong) or bare(w) == bare(wrong) or (family(w) and family(w) == family(wrong)))), None)
            if m and not any(o[1] == m and o[2] == right for o in out):
                ch = related(m, right)
                if ch:
                    out.append((M, m, right, ch))
                break
    res = []
    out = [o for o in out if not (o[3] == "family" and classify(o[1], o[2], o[0]["text"], A["text"], "family") is None)]
    question = bool(re.search(r"[?؟][\s\u200e\u200f\u202a-\u202e]*$", A["text"]))
    later = [w for M in window for w in M["ar"]]
    fixed_real = {a for M, m, a, ch in out if ch != "insert"}
    for M, m, a, ch in out:
        if ch == "insert" and a in fixed_real:
            continue
        if not keep_pair(M, m, a, ch, A, question, window):
            continue
        if TRACE is not None:
            TRACE.append({"date": CUR_DATE[0], "t": round(M["start"], 1), "A_t": round(A["start"], 1), "m": m, "a": a,
                          "change": ch, "dropped": "(generated)", "said": M["text"][:80], "recast": A["text"][:80]})
        res.append({"M": M, "A": A, "m": m, "a": a, "change": ch,
                    "hit": classify(m, a, M["text"], A["text"], ch), "kind": kind,
                    "overlap": 0.0 if kind == "spot" else round(anchors / len(aw), 2)})
    return res


def build_lexicon(dates):
    lex = Counter()
    for d in dates:
        T, _ = lesson_turns(d, with_chat=True)
        for t in T:
            for w in tokens(t["text"]):
                if is_ar(w):
                    s = skel(w)
                    if len(s) >= 2:
                        lex[s] += 1
                        lex[bare(w)] += 1
    return {s for s, n in lex.items() if n >= 1}


from lesson_turns import lesson_turns  # noqa: E402

if __name__ == "__main__" or True:
    buckets = {b["id"]: b for b in json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]}
    dates = sorted(d for d in os.listdir(ANEES) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    NOT_ARABIC = {"2026-08-22", "2026-08-23", "2026-09-01"}
    dates = [d for d in dates if d not in NOT_ARABIC]
    LEX = build_lexicon(dates)

    def ar_of(text):
        return arabic_tokens(text, LEX)

    lessons, events, selfs, asks = [], [], [], []
    known_by_date, seen_words = {}, set()
    for d in dates:
        known_by_date[d] = set(seen_words)
        Td, _ = lesson_turns(d, with_chat=False)
        for t in Td:
            if t["speaker"] == "Medi":
                seen_words |= {bare(w) for w in arabic_tokens(t["text"], LEX)}
    for date in dates:
        CUR_DATE[0] = date
        known = known_by_date[date]
        known_stems = {x for k in known for x in stems(k) if len(x) >= 3}
        T, src = lesson_turns(date, with_chat=True)
        if not T:
            continue
        for t in T:
            t["ar"] = ar_of(t["text"])
        medi = [t for t in T if t["speaker"] == "Medi" and not t.get("chat")]
        for i, t in enumerate(medi[:-1]):
            if re.search(r"(^|\s)(الـ|ال)[\s،,.\-—]*$", t["text"].strip()) and medi[i + 1]["ar"]:
                w0 = medi[i + 1]["ar"][0]
                if is_ar(w0) and not w0.startswith("ال"):
                    medi[i + 1]["ar"][0] = "ال" + w0
        medi_ar = [t for t in medi if t["ar"]]
        for i, t in enumerate(medi):
            if is_ask(t) and not re.search(r"[?؟.]\s*$", t["text"]):
                for u in medi[i + 1:i + 2]:
                    if u["start"] - t["end"] <= 8 and not any(B["speaker"] == "Amal" and B["ar"] and t["end"] <= B["start"] < u["start"] for B in T):
                        u["ask_tail"] = True

        found = []

        # --- 1. her words re-saying his in another shape (voice + chat)
        for A in T:
            if A["speaker"] != "Amal" or not A["ar"]:
                continue
            if A.get("chat") and re.search(r"=|\+|/", A["text"]) and len(A["ar"]) <= 3 \
                    and not any(family(w) in ("kaan", "koon") for w in A["ar"]):
                continue  # a vocab note, not a recast
            if PRAISE.search(A["text"]) and not CONTRAST.search(A["text"]) and len(A["ar"]) <= 1:
                continue
            if A.get("chat"):
                window = [M for M in medi_ar if A["start"] - CHAT_BACK <= M["start"] <= A["start"] + CHAT_AHEAD]
            else:
                window = [M for M in medi_ar if M["start"] < A["start"] and A["start"] - M["end"] <= WINDOW]
            A["_T"] = T
            A["_medi_all"] = [M for M in medi_ar if abs(M["start"] - A["start"]) <= CHAT_BACK + CHAT_AHEAD]
            # his questions about a form are asks (rule M1), kept apart
            asked = [M for M in window if is_ask(M)]
            window = [M for M in window if not is_ask(M)]
            for M in asked:
                if not A.get("chat") and not any(x["date"] == date and x["t"] == round(M["start"], 1) for x in asks):
                    asks.append({"date": date, "t": round(M["start"], 1),
                                 "mmss": "%02d:%02d" % (int(M["start"]) // 60, int(M["start"]) % 60),
                                 "said": M["text"], "answer": A["text"]})
            if not window:
                continue
            if not A.get("chat"):
                last = window[-1]
                A["prev_amal_ar"] = any(B["speaker"] == "Amal" and B["ar"] and not B.get("chat")
                                        and last["end"] <= B["start"] < A["start"] for B in T)
            # the word she taught a moment ago: his try at repeating it is imitation, not a slip
            taught = {bare(w): B["start"] for B in T if B["speaker"] == "Amal" and not B.get("chat")
                      and A["start"] - 60 <= B["start"] < A["start"] for w in B["ar"]}
            for f in pair_up(window, A):
                # a word he has never used in any form (earlier lessons, or earlier
                # in this one): his try is imitation, not a slip
                earlier = {x for M0 in medi if M0["start"] < f["M"]["start"] - 30 for w in tokens(M0["text"])
                           if not is_english(w) for x in stems(bare(w)) if len(x) >= 3}
                new_word = f["a"] and len(bare(f["a"])) >= 3 and not (stems(bare(f["a"])) & (known_stems | earlier))
                if f["a"] and not A.get("chat") and f["change"] in ("shape", "suffix", "double") and new_word:
                    _drop(f["M"], f["m"], f["a"], f["change"], A, "imitating-new-word")
                    continue
                if not A.get("chat") and re.search(r"[?؟][\s\u200e\u200f\u202a-\u202e]*$", A["text"]) and f["kind"] == "echo" and f["overlap"] < 0.5 \
                        and not CONTRAST.search(A["text"]):
                    _drop(f["M"], f["m"], f["a"], f["change"], A, "her-question")
                    continue  # her own question, not a recast
                found.append(f)

        # --- 2. she named the rule in English
        for A in T:
            if A["speaker"] != "Amal" or A.get("chat"):
                continue
            cue = None
            prev = [M for M in medi if M["start"] < A["start"] and A["start"] - M["end"] <= ENGLISH_WINDOW]
            prev_ar = [M for M in prev if M["ar"]]
            if not prev_ar:
                continue
            last_real = next((P_ for P_ in reversed(prev) if P_["ar"] or len(tokens(P_["text"])) > 2), None)
            if last_real is None or not last_real["ar"]:
                continue  # she is answering something he said in English, not a slip in Arabic
            if all(re.sub(r"[^\u0600-\u06FF]", "", w) in ("صح", "اه", "آه", "أه", "تمام", "ماشي") for w in last_real["ar"]):
                continue  # his "yes" - she is explaining, not fixing
            if len(tokens(A["text"])) > 30:
                continue
            cue = english_cue(A["text"], " ".join(M["text"] for M in prev_ar[-2:]))
            if not cue:
                continue
            M = prev_ar[-1]
            if is_ask(M) or (len(prev) and is_ask(prev[-1])):
                continue  # answering his question (an ask), not fixing a slip
            if A["start"] - M["end"] > 8:
                continue  # talk about the rule, not a reply to what he just said
            found.append({"M": M, "A": A, "m": " ".join(M["ar"])[:40], "a": "", "change": "english",
                          "hit": (cue, "Amal named the rule in English"), "kind": "english", "overlap": 0.0})

        # --- one event per real fix: the same pair again soon after is a repeat,
        #     and one Medi turn files each bucket once.
        # a real word pair is kept before an inserted word for the same fix
        found.sort(key=lambda f: (f["change"] == "insert", f["M"]["start"], {"echo": 0, "spot": 1, "chat": 2, "english": 3}[f["kind"]]))
        kept, seen_pairs, seen_turn, seen_fix = [], [], set(), []
        for f in found:
            b = f["hit"][0] if f["hit"] and f["hit"][0] in buckets else "UNFILED"
            if b == "UNFILED" and f["change"] in ("ending", "shape", "suffix", "prefix"):
                _drop(f["M"], f["m"], f["a"], f["change"], f["A"], "unfiled-chat")
                continue
            pair = (bare(f["m"]) if f["a"] else None, bare(f["a"]) if f["a"] else None)
            t0 = f["M"]["start"]
            if f["a"] and any(p == pair and abs(t0 - t1) <= REPEAT for p, t1 in seen_pairs):
                _drop(f["M"], f["m"], f["a"], f["change"], f["A"], "dedupe")
                continue
            # the same fixed word under the same rule again soon after: she is repeating the fix
            if f["a"] and any(fx == (bare(f["a"]), b) and abs(t0 - t1) <= REPEAT for fx, t1 in seen_fix):
                _drop(f["M"], f["m"], f["a"], f["change"], f["A"], "dedupe")
                continue
            akey = (id(f["A"]), id(f["M"]), b)
            if akey in seen_turn:
                _drop(f["M"], f["m"], f["a"], f["change"], f["A"], "dedupe")
                continue
            seen_turn.add(akey)
            tk = (round(t0, 1), b, f["kind"] == "english")
            if (round(t0, 1), b) in {(x[0], x[1]) for x in seen_turn}:
                _drop(f["M"], f["m"], f["a"], f["change"], f["A"], "dedupe")
                continue
            # an English cue next to a paired fix of the same bucket is the same event
            if f["kind"] == "english" and any(abs(k["M"]["start"] - t0) <= ENGLISH_WINDOW and k["bucket"] == b for k in kept):
                _drop(f["M"], f["m"], f["a"], f["change"], f["A"], "dedupe")
                continue
            seen_turn.add(tk)
            if f["a"]:
                seen_pairs.append((pair, t0))
                seen_fix.append(((bare(f["a"]), b), t0))
            f["bucket"] = b
            kept.append(f)

        for f in kept:
            M, A = f["M"], f["A"]
            d = diff_spans(M["text"], A["text"], wrong_word=f["m"] if f["a"] else None, fixed_word=f["a"] or None)
            bucket = f["bucket"]
            why = f["hit"][1] if f["hit"] and bucket != "UNFILED" else "correction found, rule not identified"
            score = 0
            score += 2 if f["kind"] in ("echo", "chat") else 1 if f["kind"] == "english" else 0
            score += 1 if f["change"] in ("al", "b", "family", "prep", "double") else 0
            score += 1 if len(A["ar"]) >= 2 else 0
            score += 1 if bucket != "UNFILED" else 0
            confidence = "high" if score >= 4 else "medium" if score >= 2 else "low"
            events.append({
                "bucket": bucket, "date": date, "t": round(M["start"], 1),
                "mmss": "%02d:%02d" % (int(M["start"]) // 60, int(M["start"]) % 60),
                "said": M["text"], "recast": A["text"],
                "recast_at": "%02d:%02d" % (int(A["start"]) // 60, int(A["start"]) % 60),
                "said_html": d["said_html"], "recast_html": d["recast_html"],
                "wrong": d["wrong"], "fixed": d["fixed"],
                "pair_wrong": f["m"], "pair_fixed": f["a"],
                "pair_similarity": round(sim(skel(f["m"]), skel(f["a"])), 2) if f["a"] else 0.0,
                "change": f["change"], "why": why, "match": f["kind"], "overlap": round(f["overlap"], 2),
                "source": src + (" + Meet chat" if f["kind"] == "chat" else ""),
                "confidence": confidence, "verified": False,
            })

        # --- 3. Medi fixing himself: a word, then the same word in a new
        #        shape a few seconds later, before Amal says anything.
        for i, M in enumerate(medi_ar):
            nxt = [N for N in medi_ar[i:i + 3] if N["start"] - M["start"] <= 12]
            her = [A for A in T if A["speaker"] == "Amal" and not A.get("chat") and A["ar"]
                   and M["start"] < A["start"] < (nxt[-1]["end"] if nxt else M["end"])]
            if her:
                continue
            words = [(w, N) for N in nxt for w in N["ar"]]
            for j, (w1, N1) in enumerate(words):
                for w2, N2 in words[j + 1:j + 4]:
                    ch = related(w1, w2)
                    if ch and ch not in ("prep",):
                        selfs.append({"date": date, "t": round(N1["start"], 1),
                                      "mmss": "%02d:%02d" % (int(N1["start"]) // 60, int(N1["start"]) % 60),
                                      "said": w1, "fixed": w2, "change": ch, "text": N1["text"] if N1 is N2 else N1["text"] + " / " + N2["text"]})
                        break
        # one per moment
        n_self = len({(s["date"], s["mmss"]) for s in selfs if s["date"] == date})

        n = sum(1 for e in events if e["date"] == date)
        lessons.append({"date": date, "source": src, "turns": len(T),
                        "medi_turns": len(medi), "medi_arabic_turns": len(medi_ar),
                        "corrections": n, "self_corrections": n_self})
        print("%s  %-26s turns=%4d  Medi=%4d (%3d Arabic)  corrections=%3d  self=%3d"
              % (date, src, len(T), len(medi), len(medi_ar), n, n_self))

    # de-duplicate self-corrections to one per moment
    sc, seen = [], set()
    for s in selfs:
        k = (s["date"], s["mmss"])
        if k not in seen:
            seen.add(k)
            sc.append(s)

    by_bucket = Counter(e["bucket"] for e in events)
    json.dump({
        "updated": "2026-09-23",
        "aligned": True,
        "method": ("Amal re-says one of Medi's words in another shape (voice within %ds, or typed in the Meet chat), "
                   "or names the rule in English. Words are compared across Arabic script, Latin and Arabizi. "
                   "Scored against a hand-labelled gold set (docs/data/grammar-goldset.json). Never guessed: "
                   "UNFILED when no rule fits." % WINDOW),
        "lessons": lessons,
        "totals": {"events": len(events), "buckets_hit": len(by_bucket),
                   "lessons_with_text": len(lessons), "self_corrections": len(sc)},
        "by_bucket": dict(by_bucket.most_common()),
        "events": events,
        "self_corrections": sc,
        "asks": asks,
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if TRACE is not None:
        json.dump(TRACE, open(os.path.join(SCRIPTS, "_backups", "audit_trace.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
    print("\nwrote", OUT)
    print("events:", len(events), "across", len(by_bucket), "buckets;", len(sc), "self-corrections")
    for b, n in by_bucket.most_common(60):
        print("  %-7s %-34s %d" % (b, buckets[b]["name"] if b in buckets else "(needs filing)", n))
