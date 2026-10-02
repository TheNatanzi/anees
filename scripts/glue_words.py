# -*- coding: utf-8 -*-
"""Glue words (shu, bas, ya3ni, tamam ...) - WS-19 as amended by Medi 2026-10-02: "the glue words should be added to the
doc, bring to her attention" + "the glue words are likely going to be old words she forgot to add".

  * a glue word is graded only once it is on Amal's Doc (the Doc is the word truth, ai_rules N2); a glue word NOT on her
    Doc is never graded (scripts/check_rules.py WS19-glue blocks a publish that grades one)
  * every glue word not on her Doc goes on her Tutor hub New words card (scripts/amal_new_words.py), nothing pre-selected,
    with the hint below; Anees marks it OLD on its side (data/word-marks.json, by Medi) so when it reaches her Doc it never
    counts as NEW on Flashcards (scripts/import_vocab.py + scripts/word_marks.py)

The keys are the old ai_rules M3 list (scripts/check_rules.GLUE = understand_lesson.GLUE_KEYS). Arabic is the meaning used
to decide 'on her Doc' (exact, by meaning: لا 'no' is not her لَ 'for/to'); it is never shown as her Arabizi (RULES S1).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import word_marks  # noqa: E402

GLUE_WORDS = {
    "shu": ("شو", "what"), "bas": ("بس", "only / but / enough"), "ai": ("أي", "which / any"), "aw": ("أو", "or"),
    "em": ("أم", "um / or"), "u": ("و", "and"), "fi": ("في", "in / there is"), "bi": ("ب", "in / at / with"),
    "min": ("من", "from"), "ya3ni": ("يعني", "I mean / like"), "iza": ("إذا", "if"), "lama": ("لما", "when"),
    "hala": ("هلا", "now / hi"), "ah": ("آه", "yes / ah"), "aha": ("آها", "I see / aha"), "tayeb": ("طيب", "okay / fine"),
    "tamam": ("تمام", "okay / perfect"), "5alas": ("خلص", "enough / done"), "sa7": ("صح", "right / correct"),
    "mashi": ("ماشي", "okay / alright"), "wala": ("ولا", "or / nor / not even"), "ma": ("ما", "not"), "ma3": ("مع", "with"),
    "la": ("لا", "no"),
}
HINT = "probably an old word you forgot to add — Medi uses it all the time"
QUOTE = "the glue words are likely going to be old words she forgot to add"
DOC = os.path.join(REPO, "docs", "data", "words.json")


def load_doc(path=DOC):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"items": []}


def on_doc(key, doc):
    """By meaning: the glue word's Arabic is an entry (or '/' part) of her Doc."""
    ar, _ = GLUE_WORDS[key]
    return word_marks.doc_has({"arabic": ar}, doc)


def not_on_doc(doc=None):
    """[(key, arabic, english)] glue words that are not on her Doc, in list order."""
    D = doc if doc is not None else load_doc()
    return [(k, a, e) for k, (a, e) in GLUE_WORDS.items() if not on_doc(k, D)]


def doc_keys(doc):
    """Lower-case Doc keys / Arabizi / aliases: a graded glue word must be one of these (WS19-glue)."""
    out = set()
    for it in (doc or {}).get("items") or []:
        for x in [it.get("key"), it.get("arabizi")] + list(it.get("aliases") or []):
            if x:
                out.add(str(x).lower())
    return out
