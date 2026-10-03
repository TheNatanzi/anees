# -*- coding: utf-8 -*-
"""TR-19 echo check (Medi 2026-10-02: "why is it so bad at understanding me... I repeated lissa back to her not this
suck"). The engine turns his short Arabic repeat of Amal's word into English look-alikes (لسه -> "This suck", ببسط ->
"babysit", انبارح -> "imbare"). A forced Arabic setting did not help (10-02 full track, 0 of 5 fixed), so the check is a
context read: this lists every moment where Amal said a short Arabic line and his reply within 5 s came out short with no
Arabic letters. The same-day review (READER-BRIEF "echo check") reads each one; a sound-alike becomes a heard-word overlay
row (data/lesson-work/transcript-fixes.json, rule TR-19); real English and his Latin-letter Arabic stay as they are.

    python scripts/echo_candidates.py DATE      # -> data/lesson-work/echo-candidates/<date>.json
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
AR = re.compile("[ء-ي]")
FILLER = re.compile(r"(?i)\b(ok|okay|yes|yeah|no|mhm|uh|um|right|sorry|what|so|and|but|oh|ah|hmm|i|it|is|that)\b$")


TAKE = re.compile(r"(^|\s)(آخد|اخد|أخد|ناخد|تاخد|ياخد|باخد|بتاخد|بياخد|خد|خدي)\s+([^\s.,،؟?!]+)")
VERBLIKE = re.compile(r"^(أ|ا|ي|ت|ن|ب)[^\s]{2,4}$")


def take_verb(turns):
    """TR-20 (Medi 2026-10-02 "aa5ud can never be followed by a command tense word?"): 'take' (آخد) takes a thing; a
    verb-looking word right after it on his line is a red flag the engine misheard the noun (10-02 09:44 أخد أطلع = his
    aa5ud 3otle, her chat 'ana laazem aa5ud 3otle u asaafer')."""
    out = []
    for u in turns:
        if u["who"] != "Medi" or u.get("engine"):
            continue
        for m in TAKE.finditer(u["text"]):
            if VERBLIKE.match(m.group(3)) and not m.group(3).startswith("ال"):
                out.append({"t": u["t"], "engine_wrote": m.group(3), "line": u["text"], "why": "a verb right after 'take' (TR-20)"})
    return out


def candidates(turns):
    out = []
    for i, u in enumerate(turns):
        if u["who"] != "Amal" or not AR.search(u["text"]) or not (1 <= len(re.sub(r"[^\w\s]", "", u["text"]).split()) <= 3):
            continue
        for j in range(i + 1, min(len(turns), i + 4)):
            v = turns[j]
            if v["who"] == "Medi" and 0 < v["t"] - u["t"] <= 5:
                w = re.sub(r"[^\w\s]", "", v["text"]).split()
                if 1 <= len(w) <= 3 and not AR.search(v["text"]) and not v.get("engine") and not FILLER.search(v["text"].strip(" .?!")):
                    out.append({"t": v["t"], "engine_wrote": v["text"], "amal_before": u["text"],
                                "context": [{"t": x["t"], "who": x["who"], "text": x["text"]} for x in turns[max(0, i - 4):j + 4]]})
                break
    return out


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    date = (argv or sys.argv[1:])[0]
    L = json.load(open(os.path.join(REPO, "docs", "data", "lessons", date + ".json"), encoding="utf-8"))
    C = candidates(L.get("turns") or [])
    d = os.path.join(REPO, "data", "lesson-work", "echo-candidates")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, date + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"date": date, "rule": "TR-19", "candidates": C, "take_verb": take_verb(L.get("turns") or [])}, f, ensure_ascii=False, indent=1)
    print(date, len(C), "echo candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
