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


LAAZEM_FILL = re.compile(r"^(آ+|أأ+|ا{2,}|امم+|um|uh|aaa+|so|like)$", re.I)
NOT_A_THING = re.compile(r"^(أ|ا|إ|ي|ت|ن|ب|ر[اح]|ما|مش|كمان|كل|هلأ|هلق|بس|ي?عني|كان|نـ|تـ|يـ|دايما|اليوم|بكرا)")   # verbs, negation, time words


def laazem_noun(turns):
    """GR-27 (Medi 2026-10-03: "you 'take' a day off, it cant be 3utle by itself"): laazem (must) is followed by a verb
    (B2: laazem aa5ud 3otle); laazem straight onto a thing ("ana laazem ... 3otle", "laazem air conditioning") is the B2
    slip WHEN Amal then gives the verb (in Arabic or English: 'you should take') - 'I need X' is b7taj X / laazemni X.
    His lines are joined like the page joins them (PG-23: no one else between, gap <= 6 s); fillers are skipped. A clue
    for the reader, never an automatic slip (S3: her signal decides; 10-01 04:13 she only asked 'laazem shu?')."""
    out, i = [], 0
    while i < len(turns):
        u = turns[i]
        if u.get("who") != "Medi":
            i += 1
            continue
        j, text, end = i, u["text"], u.get("end") or u["t"]
        while j + 1 < len(turns) and turns[j + 1].get("who") == "Medi" and turns[j + 1]["t"] - end <= 6:
            j += 1
            text += " " + turns[j]["text"]
            end = turns[j].get("end") or turns[j]["t"]
        ws = re.sub(r"[.,،؟?!…\-]+", " ", text).split()
        for k, w in enumerate(ws):
            if w != "لازم":
                continue
            nxt = [x for x in ws[k + 1:] if not LAAZEM_FILL.match(x)]
            if nxt and nxt[0] != "لازم" and not NOT_A_THING.match(nxt[0]) and not nxt[0].startswith("ال"):
                amal = [{"t": v["t"], "who": v["who"], "text": v["text"]} for v in turns[j + 1:j + 8]
                        if v.get("who") in ("Amal", "chat") and 0 <= v["t"] - end <= 20]
                out.append({"t": u["t"], "line": text, "thing": nxt[0], "amal_after": amal,
                            "why": "laazem straight onto a thing, no verb (GR-27): a B2 slip only if Amal then gives the verb"})
        i = j + 1
    return out


def chat_latin(turns):
    """TR-23 (Medi 2026-10-03 "she even wrote it for you"): the engine writes his Arabic in English-ear letters (13:47
    'nimbisit'); Amal TYPES it in her Arabizi in the chat (14:10 'ra7 nenbese6'). Each of his Latin words (not English, 4+
    letters) whose sound skeleton equals one of her chat words in the next 45 s is listed with her spelling, for the
    reader to confirm as a heard-word overlay row (rule TR-23). A clue: her typed word may be her CORRECTED form."""
    import arabizi_reader as R
    from xscript import is_english
    out = []
    for i, c in enumerate(turns):
        if c["who"] != "chat":
            continue
        hers = {R._sk(w): w for w in re.findall(r"[A-Za-z0-9']{4,}", c["text"]) if len(R._sk(w)) >= 3}
        for u in turns[max(0, i - 20):i]:
            if u["who"] != "Medi" or not (0 <= c["t"] - u["t"] <= 45) or AR.search(u["text"]):
                continue
            for w in re.findall(r"[A-Za-z][A-Za-z0-9']{3,}", u["text"]):
                lw = w.lower()
                if lw in R.FUNC or is_english(lw):
                    continue
                k = R._sk(lw)
                if k in hers and hers[k].lower() != lw:
                    out.append({"t": u["t"], "engine_wrote": w, "her_chat": hers[k], "chat_t": c["t"], "line": u["text"], "chat": c["text"],
                                "why": "his Latin word sounds like her typed word (TR-23)"})
    return out


FOREIGN = re.compile(r"[぀-ヿ㐀-鿿가-힯Ѐ-ӿ֐-׿ऀ-ॿ]")


def foreign_script(turns, fixed=True):
    """TR-25 (Medi 2026-10-03 "why did it switch languages here? How can we prevent this"): the engine guesses the language
    of each short piece and sometimes writes his Arabic in Chinese / Japanese / Russian / Hebrew / Hindi letters (10-02
    49:01 結局 = kul yoam, 49:41 他人 = tani - Medi re-listened 2026-10-04; his first guess from context, 8air, was wrong). Any such letter on a line is the engine, never him. Listed for every lesson's
    review, warned by the publish guard while one is left unfixed, and first in the Gemini re-hear. fixed=True reads the
    text after the heard-word overlay (what the page shows)."""
    return [{"t": u["t"], "who": u.get("who"), "text": u.get("text") if fixed else (u.get("engine") or u.get("text"))}
            for u in turns if FOREIGN.search((u.get("text") if fixed else (u.get("engine") or u.get("text"))) or "")]


def foreign_check(repo=REPO):
    """Publish guard ADVISORY (warning only): every page line still showing another script. -> (ok, detail)."""
    left = []
    d = os.path.join(repo, "docs", "data", "lessons")
    for f in sorted(os.listdir(d)):
        if re.fullmatch(r"\d{4}-\d\d-\d\d\.json", f):
            for x in foreign_script(json.load(open(os.path.join(d, f), encoding="utf-8")).get("turns") or []):
                left.append("%s %s %r" % (f[:10], x["t"], x["text"][:40]))
    return (not left), ("; ".join(left) or "no line in another script (TR-25)")


def chat_pairs(turns):
    """TR-21 (Medi 2026-10-02 "aa5ud Etla3 makes no seanse"): Amal often TYPES the sentence he was saying; each of her chat
    lines with his lines of the 45 s before it, for the reader to compare word by word (أطلع ~ her 3otle)."""
    out = []
    for i, c in enumerate(turns):
        if c["who"] != "chat":
            continue
        his = [{"t": u["t"], "text": u["text"]} for u in turns[max(0, i - 14):i] if u["who"] == "Medi" and c["t"] - u["t"] <= 45 and not u.get("engine")]
        if his:
            out.append({"chat_t": c["t"], "chat": c["text"], "medi": his})
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
    if (argv or sys.argv[1:])[:1] == ["--foreign-check"]:
        ok, detail = foreign_check()
        print(detail)
        return 0 if ok else 1
    date = (argv or sys.argv[1:])[0]
    L = json.load(open(os.path.join(REPO, "docs", "data", "lessons", date + ".json"), encoding="utf-8"))
    C = candidates(L.get("turns") or [])
    d = os.path.join(REPO, "data", "lesson-work", "echo-candidates")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, date + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"date": date, "rule": "TR-19", "candidates": C, "take_verb": take_verb(L.get("turns") or []), "laazem_noun": laazem_noun(L.get("turns") or []), "chat_latin": chat_latin(L.get("turns") or []), "foreign_script": foreign_script(L.get("turns") or []),
                   "chat_pairs": chat_pairs(L.get("turns") or [])}, f, ensure_ascii=False, indent=1)
    print(date, len(C), "echo candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
