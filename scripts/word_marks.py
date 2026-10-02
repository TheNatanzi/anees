# -*- coding: utf-8 -*-
"""Old / new marks for words that are not (yet) on Amal's Doc (AM-16, Medi 2026-10-02: "keep it on your system that
mumtaz is an old word and wait for her to add it to the doc. Keep a tab of what she said shes going to add" + "yes have
her tap that its old").

Two voices, both kept:
  * Medi's mark  - data/word-marks.json (this repo; the app never writes Amal's Doc, rule AM-03 / ai_rules N2)
  * Amal's tap   - the Tutor hub New words card: newword_add_new / newword_add_old (amal_rules, source 'review'),
                   read back into docs/data/amal-new-words.json by scripts/amal_new_words.py
Resolution (ai_rules A2, her tap beats any other label): Amal's NEW or OLD tap wins; with no tap of hers, Medi's mark
stands. Nothing is pre-selected for her: Medi's mark is only shown on her card as a hint.

Flashcards (docs/js/cards-core.js curriculum: NEW = words.first_seen after NEW_SINCE 2026-09-30): when the Doc import
(scripts/import_vocab.py) sees a word whose resolved age is OLD, its first_seen is set to OLD_FIRST_SEEN (the NEW_SINCE
day, which counts as old) and the change is recorded on the mark (doc_seen, first_seen_backdated). No other word changes.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from arabizi import arabic_norm, loose  # noqa: E402

MARKS = os.path.join(REPO, "data", "word-marks.json")
NEW_WORDS = os.path.join(REPO, "docs", "data", "amal-new-words.json")
NEW_SINCE = "2026-09-30"                       # docs/js/cards-core.js NEW_SINCE (kept equal by tests)
OLD_FIRST_SEEN = NEW_SINCE + "T00:00:00+00:00"
HINT_OLD = "Medi already knows this — old word"
AGE_OF_TAP = {"newword_add_new": "new", "newword_add_old": "old"}


def load(path=MARKS):
    if not os.path.exists(path):
        return {"marks": []}
    return json.load(open(path, encoding="utf-8"))


def save(data, path=MARKS):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def _ar(s):
    return arabic_norm(re.sub(r"\s+", " ", s or "").strip())


def _lat(s):
    try:
        return loose(s) if s else ""
    except Exception:
        return (s or "").lower()


def same(a, b):
    """Two word-shaped dicts ({arabic, arabizi, key?, aliases?}) name the same word: same normalised Arabic, or same
    loose Arabizi (aliases included)."""
    aa, ba = _ar(a.get("arabic")), _ar(b.get("arabic"))
    if aa and ba and aa == ba:
        return True
    la = {_lat(x) for x in [a.get("arabizi"), a.get("key")] + list(a.get("aliases") or []) if x} - {""}
    lb = {_lat(x) for x in [b.get("arabizi"), b.get("key")] + list(b.get("aliases") or []) if x} - {""}
    return bool(la & lb)


def mark_for(word, marks=None):
    """Medi's mark row for a word, or None."""
    M = (marks if marks is not None else load()).get("marks") or []
    return next((m for m in M if same(m, word)), None)


def resolve(medi_mark, amal_tap):
    """(age, by): Amal's NEW/OLD tap wins; else Medi's mark; else (None, None)."""
    if amal_tap in AGE_OF_TAP:
        return AGE_OF_TAP[amal_tap], "amal"
    if medi_mark in ("old", "new"):
        return medi_mark, "medi"
    return None, None


def resolved_ages(marks=None, new_words=None):
    """[{arabic, arabizi, key, age, by}] for every word with a resolved age: Amal's add taps (from the built New words
    data) plus Medi's marks she has not overruled."""
    M = (marks if marks is not None else load()).get("marks") or []
    N = new_words if new_words is not None else (json.load(open(NEW_WORDS, encoding="utf-8")) if os.path.exists(NEW_WORDS) else {})
    out = []
    for it in N.get("items") or []:
        age, by = resolve((mark_for(it, {"marks": M}) or {}).get("mark"), it.get("tap"))
        if age:
            out.append({"arabic": it.get("arabic"), "arabizi": it.get("arabizi"), "key": it.get("key"), "age": age, "by": by})
    for m in M:
        if not any(same(m, o) for o in out) and m.get("mark") in ("old", "new"):
            out.append({"arabic": m.get("arabic"), "arabizi": m.get("arabizi"), "key": None, "age": m["mark"], "by": m.get("by")})
    return out


def old_doc_words(words, ages):
    """Doc word records (import_vocab.to_words) whose resolved age is OLD -> {key: the age row}."""
    olds = [a for a in ages if a["age"] == "old"]
    return {w["key"]: a for w in words for a in olds if same(a, w)}


def doc_has(word, doc):
    """The word is an entry of her Doc (docs/data/words.json): exact normalised Arabic of an entry or one of its '/'
    parts (article ال ignored), or the same loose Arabizi as an entry's key / Arabizi / alias. Exact on purpose: a
    stem match would call a promised word 'In the Doc' before she added it."""
    def ars(s):
        out = set()
        for part in re.split(r"\s*/\s*", s or ""):
            n = _ar(part)
            if n:
                out.add(n)
                if n.startswith("ال") and len(n) > 3:
                    out.add(n[2:])
        return out
    wa = ars(word.get("arabic"))
    wl = {_lat(x) for x in (word.get("arabizi"),) if x} - {""}
    for it in (doc or {}).get("items") or []:
        if wa & (ars(it.get("arabic")) | ars(it.get("arabic_norm")) | ars(it.get("plural"))):
            return True
        if wl & ({_lat(x) for x in [it.get("key"), it.get("arabizi")] + list(it.get("aliases") or []) if x} - {""}):
            return True
    return False
