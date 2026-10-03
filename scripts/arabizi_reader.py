# -*- coding: utf-8 -*-
"""Read the Arabic Medi says in Latin letters (Arabizi) as Arabic script, so the grammar use counter sees it.

Problem (Medi 2026-10-01, the 09-30 el- review): Scribe often writes his Arabic in Latin letters ("bab al-ghurfa",
"hadol el swat", "kundara el Chanel"). scripts/detect_grammar_usage.py only read Arabic-script turns, so a drill done in
Latin letters counted 0 uses while its slips still counted (A2 on 09-30: 0 uses, 4 slips).

to_arabic(text) rewrites every Latin run of a line, word by word, and leaves the Arabic-script part untouched:
  - a closed list of short words (hada / hadi / hadol, ana, min, fi, mish, kan ...) -> their Arabic spelling;
  - el- / al- / il- glued to the next Arabic word (el bab, al-ghurfa -> الباب, الغرفة);
  - any other word -> Amal's own Arabic for it when it matches one of her Doc words (scripts/arabizi.Matcher, strict
    tiers only - no fuzzy guess), or the feminine -et / -it form of one of her -a nouns (shantet -> شنطت, read by the
    counter's existing feminine -t rule);
  - English words and words that match nothing become a break ("."), so two Arabic words are never glued across them;
  - fillers (uh, um) and commas are see-through, as Medi pauses mid-phrase ("Hadi el, uh, shanta").
Nothing is guessed: a Latin word that is neither on the closed list nor one of Amal's words is never turned into Arabic.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from arabizi import Matcher  # noqa: E402
from xscript import is_english  # noqa: E402

DOCS = os.path.join(os.path.dirname(HERE), "docs")

# Short words a Doc match cannot be trusted with (too short, or English look-alikes). Spellings match the counter's patterns.
FUNC = {}
for ar, lat in [
    ("هذا", "hada hatha hadha haza"), ("هادي", "hadi hadhi hathi hayde haydi hadee"), ("هدول", "hadol hadool hadhol hathol hadoul hadul haddol"),
    ("هداك", "hadak hadaak hadhak"), ("هديك", "hadik hadeek hadhik"), ("هاي", "hay"),
    ("أنا", "ana"), ("انت", "inta enta"), ("انتي", "inti enti"), ("احنا", "i7na e7na ihna ehna"),
    ("هو", "huwe huwwe howe hoowe"), ("هي", "hiye hiyye heye heyye"),
    ("من", "min men"), ("في", "fi fee"), ("على", "3ala ala"), ("مع", "ma3 maa"), ("عن", "3an"),
    ("مش", "mish mesh mush"), ("كان", "kan kaan"), ("كانت", "kanat kaanat kanet"), ("كنت", "kunt kont kunet"),
    ("شو", "shu shoo"), ("وين", "wein wen wain"), ("ليش", "lesh leish laish"), ("كيف", "keef kif kaif"),
    ("إذا", "iza itha eza"), ("لما", "lamma lama"), ("اللي", "illi ili elli eli"), ("كم", "kam"),
    ("بس", "bas bass"), ("و", "w wa"), ("كتير", "kteer ktir kteir"), ("هون", "hon hoon"), ("هناك", "honak hunak"),
    ("كل", "kul kol"), ("رح", "ra7 rah"),
    ("الساعة", "elsa elsaa elsa3a elsaa3a"),
    ("غير", "qayr ghair ghayr 8air"),        # TR-23 (Medi 2026-10-03 "8air"): the engine writes his 8air as 'qayr'    # TR-23 (Medi 2026-10-03 "I was trying to say el Sa3aa"): the engine's 'Elsa ("بدي", "baddi bidi biddi badi"), ("لازم", "lazem lazim"), ("ممكن", "mumken mumkin momken"),
]:
    for w in lat.split():
        FUNC[w] = ar

ARTICLE = {"el", "al", "il"}                     # not a lone "L": "the L rule" is English
FILLER = {"uh", "um", "umm", "uhm", "mm", "hmm", "er", "eh", "ah", "like"}
LAT = re.compile(r"[A-Za-z0-9'’`]+")
TOKEN = re.compile(r"[A-Za-z0-9'’`]+(?:-[A-Za-z0-9'’`]+)*(?:--|—|-)?|[؀-ۿ]+(?:--|—)?|[.?!؟;:]|[,،]|\S")
SUFFIX = (("hom", "هم"), ("kom", "كم"), ("ha", "ها"), ("na", "نا"), ("ak", "ك"), ("ik", "ك"), ("i", "ي"), ("o", "ه"), ("u", "ه"))
_CH = [("sh", "ش"), ("ch", "ش"), ("kh", "خ"), ("gh", "غ"), ("th", "ث"), ("dh", "ذ"), ("aa", "ا"), ("ee", "ي"), ("ii", "ي"), ("oo", "و"), ("uu", "و"),
       ("2", "ء"), ("3", "ع"), ("5", "خ"), ("6", "ط"), ("7", "ح"), ("8", "غ"), ("9", "ص"), ("b", "ب"), ("t", "ت"), ("j", "ج"),
       ("d", "د"), ("r", "ر"), ("z", "ز"), ("s", "س"), ("f", "ف"), ("q", "ق"), ("k", "ك"), ("l", "ل"), ("m", "م"), ("n", "ن"),
       ("h", "ه"), ("w", "و"), ("y", "ي"), ("g", "ج"), ("v", "ف"), ("p", "ب"), ("c", "ك"), ("x", "كس")]


def spell(w):
    """Letter-by-letter Arabic for a word that follows el- but is not one of Amal's words (a name, a brand: el Chanel).
    Only used where the article already proves a noun stands there; it never decides a rule by itself."""
    lw, out, i = w.lower(), "", 0
    while i < len(lw):
        for a, b in _CH:
            if lw.startswith(a, i):
                out += b
                i += len(a)
                break
        else:
            out += "ا" if i == 0 and lw[i] in "aeiou" else ""
            i += 1
    return out or None
STRICT = ("arabic", "exact", "fold", "short")   # no consonant-skeleton tier: English words hit it (based -> بزيد)

_matcher, _ar_of = None, None


def _load():
    global _matcher, _ar_of
    if _matcher is None:
        items = json.load(open(os.path.join(DOCS, "data", "words.json"), encoding="utf-8"))["items"]
        _matcher = Matcher(items)
        _ar_of = {}
        for x in items:
            first = re.split(r"\s*/\s*", (x.get("arabic") or "").strip())[0]
            first = re.sub(r"\(.*?\)", "", first).strip()
            if first and " " not in first:          # one Arabic word for one Latin word; a phrase entry is not used
                _ar_of[x["key"]] = first
    return _matcher, _ar_of


def word(w):
    """Arabic script for one Latin word, or None (English, or not one of Amal's words)."""
    lw = w.lower().strip("'’`")
    if not lw:
        return None
    if lw in FUNC:
        return FUNC[lw]
    if is_english(lw) or len(lw) < 3 or lw.isdigit():
        return None
    m, ar = _load()
    hit = m.match_tier(lw, fuzzy=False)
    if hit and hit[1] in STRICT and hit[0] in ar:
        return ar[hit[0]]
    vf = verb_form(lw)
    if vf:
        return vf
    # one of her nouns + a possessive ending: jari -> جار + ي (my neighbour), beiti -> بيت + ي
    for end, ar_end in SUFFIX:
        if lw.endswith(end) and len(lw) - len(end) >= 3:
            hit = m.match_tier(lw[: -len(end)], fuzzy=False)
            if hit and hit[1] in STRICT and hit[0] in ar and ar[hit[0]][-1:] not in "ةاى":
                return ar[hit[0]] + ar_end
    # the feminine -t form before an owner: shantet / kundret / ghurfet -> one of her -a nouns with ة -> ت
    for end in ("et", "it", "at"):
        if lw.endswith(end) and len(lw) > 4:
            for base in (lw[:-2] + "a", lw[:-2] + "e", lw[:-2] + "eh", lw[:-2] + "ah"):
                hit = m.match_tier(base, fuzzy=False)
                if hit and hit[1] in STRICT and ar.get(hit[0], "").endswith("ة"):
                    return ar[hit[0]][:-1] + "ت"
    return None


def _sk(w):
    """Consonant skeleton of a Latin spelling, with the English-ear spellings undone (TR-23): mb -> nb (he says nenbisit,
    the engine hears nimbisit), 6 -> t, 7 -> h, vowels dropped, doubles collapsed."""
    w = w.lower().replace("kh", "5").replace("sh", "$").replace("gh", "8")
    w = re.sub(r"(?<=[aeiou])h$", "", re.sub(r"[^a-z0-9$]", "", w)).replace("mb", "nb")   # 3ashrah = 3ashra (-ah is the ة)
    w = w.translate(str.maketrans({"6": "t", "7": "h", "9": "s", "q": "k", "a": "", "e": "", "i": "", "o": "", "u": "", "y": "", "w": ""}))
    return re.sub(r"(.)\1+", r"\1", w)


PERSON = (("bn", "بن"), ("bt", "بت"), ("by", "بي"), ("n", "ن"), ("t", "ت"), ("y", "ي"))
_stems = None


def _verb_stems():
    """Her b-present verbs (Banbese6 = بنبسط) by the skeleton of the stem after b-: one skeleton -> one Arabic stem."""
    global _stems
    if _stems is None:
        m, ar = _load()
        seen = {}
        for x in json.load(open(os.path.join(DOCS, "data", "words.json"), encoding="utf-8"))["items"]:
            a = re.sub(r"^أنا\s+", "", (x.get("arabic") or "").split("/")[0].strip())
            z = re.sub(r"^ana\s+", "", (x.get("arabizi") or "").strip().lower())
            if " " in a or " " in z or not a.startswith("ب") or not z.startswith("b") or len(a) < 4:
                continue
            k = _sk(z[1:])
            if len(k) >= 4:
                seen.setdefault(k, set()).add(a[1:])
        _stems = {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}     # ambiguous skeletons are never used
    return _stems


def verb_form(lw):
    """TR-23 (Medi 2026-10-03 "why no credit here ... this should be nenbisit"; engine wrote 'Rah nimbisit'): another
    person of one of her b-present verbs, in the engine's English-ear spelling - nimbisit -> ننبسط (we'll have fun,
    her Banbese6 = بنبسط). Only her own verbs, only a stem skeleton of 4+ consonants that points at exactly one of them."""
    st = _verb_stems()
    for pre, ar_pre in PERSON:
        if lw.startswith(pre) and len(lw) - len(pre) >= 4:
            k = _sk(lw[len(pre):])
            if k in st:
                return ar_pre + st[k]
    return None


def to_arabic(text):
    """The line with every Latin run read as Arabic (see module doc). Arabic-script text passes through unchanged."""
    if not LAT.search(text or ""):
        return text
    out, pend_al, last_latin, weak = [], False, False, set()
    for tok in TOKEN.findall(text):
        if tok.endswith(("--", "—", "-")):
            continue                                       # a word he broke off ("al-mufta-- Al-maftuh", "hade-") is no attempt
        parts = [p for p in tok.split("-") if p] if LAT.match(tok) else [tok]
        # "saf-safrat": a piece that the next piece starts with is a stutter
        parts = [p for k, p in enumerate(parts) if not (k + 1 < len(parts) and p.lower() not in ARTICLE
                                                       and parts[k + 1].lower().startswith(p.lower()))]
        for p in parts:
            lp = p.lower()
            if LAT.fullmatch(p):
                if lp in FILLER:
                    continue
                if lp in ARTICLE:
                    pend_al = True
                    continue
                a = word(p)
                if a is None and pend_al and not is_english(lp) and len(lp) >= 3:
                    a = spell(p)                           # el + a name / brand: still a noun with the article
                if a is None:
                    if pend_al:
                        out.append("الـ")
                        pend_al = False
                    out.append(".")
                    continue
                if pend_al:
                    a = "ال" + re.sub(r"^ال", "", a)
                    pend_al = False
                elif lp not in FUNC and not re.search(r"[235789]", lp):
                    weak.add(len(out))                     # a plain Doc match: an English look-alike is possible (hate -> هات)
                out.append(a)
                last_latin = True
            elif p in (",", "،") and (last_latin or pend_al):
                continue                                   # a pause after a Latin word, not a break ("Hadi el, uh, shanta")
            else:
                last_latin = False
                if pend_al:
                    out.append("الـ")
                    pend_al = False
                out.append(p)
    if pend_al:
        out.append("الـ")
    # A lone Doc match in the middle of an English sentence is an English word that looks like one of hers ("I hate
    # Arabic", "based on"): kept only when another Arabic word stands next to it, or the line is a short answer.
    if len(LAT.findall(text)) > 3:
        def lone(k):
            return all(j < 0 or j >= len(out) or not re.search(r"[ء-ي]", out[j]) for j in (k - 1, k + 1))
        out = ["." if k in weak and lone(k) else w for k, w in enumerate(out)]
    s = " ".join(out)
    s = re.sub(r"(?:\s*\.)+", " .", s)                      # one break for a run of English
    return s.strip(" .") if not re.search(r"[ء-ي]", s) else s.strip()


if __name__ == "__main__":
    for line in sys.argv[1:]:
        print(line, "->", to_arabic(line))
