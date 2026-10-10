# -*- coding: utf-8 -*-
"""One lesson's transcript audit, the checks of the 2026-10-10 audit of 10-08 (Medi: "do a full audit of the lesson and use
the corrections I made to make final rule adjustments and corrections. Then apply it to 10-9. Audit 10-9 at least 4-5
times until you are sure that you can replicate all the steps"). Read-only: it prints what to look at; the fixes go
through the ruling files and medi-corrections-hand.json (RULES.md S6). Run it after every rebuild until it is clean.

    python scripts/lesson_audit.py 2026-10-09            # the report
    python scripts/lesson_audit.py 2026-10-09 --notes    # also every note Medi wrote on the lesson, with today's chips

Checks (each one is a mistake class Medi found on 10-08):
  1 coverage    every Arabic word of his has a mark or a grey reason (WS-30)
  2 grey        the grey chips he sees, by reason; a grey chip with no word (PG-44)
  3 off-list    'not on her word list' words that ARE her word by sound (بيد = بعيد / غير, 10-08 32:05) or are a
                place word / preposition form - read each one against the lines around it
  4 latin       Latin letters or * on a line the engine wrote in Arabic (the note reader's misreads, TR-30)
  5 nods        a tutor line that is only مهم / ممم still read as a word (PG-45)
  6 twice       the same word credited on two lines in a row (WS-36)
  7 questions   a ✓ or a grammar use on his English question about her words (WS-36)
  8 english     an Arabic line with no English under it (PG-40)
  9 her lines   her lines whose English reads like nonsense ('A flying tree' = شو جمع طيارة, 10-08 21:09): listed
                for a read, with the line of his before
 10 slips       every ✗ with her line after it, to check the signal (S3)
"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def J(p, d=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def mm(t):
    t = int(float(t or 0))
    return "%d:%02d" % (t // 60, t % 60)


AR = re.compile(r"[؀-ۿ]")
ODD_EN = re.compile(r"\b(flying tree|accepts|not\.?$|baal|whose mind)\b", re.I)


def audit(date, notes=False, out=print):
    import word_coverage as WC
    d = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"), {}) or {}
    T, tm = d.get("turns") or [], d.get("tmarks") or {}
    if not T:
        out("no page data for %s" % date)
        return 1
    flags = collections.Counter()
    words = J(os.path.join(REPO, "docs", "data", "words.json"), {}) or {}
    items = words.get("items") or []
    keys = WC.Keys(items) if items else None

    def chips(i):
        return (tm.get(str(i)) or {}).get("c", [])

    # 1 coverage
    rep = WC.report(date)
    none = [r for r in rep if not r["cut"] and not r["state"]]
    out("1 coverage: %d Arabic words of his, %d with no mark" % (len(rep), len(none)))
    for r in none[:20]:
        out("   %s %s" % (r["t"], r["word"]))
    flags["coverage"] += len(none)

    # 2 grey chips he sees
    grey = collections.defaultdict(list)
    nameless = []
    for k, v in tm.items():
        for c in v["c"]:
            if c.get("s") != "na" or c.get("hide"):
                continue
            why = c.get("why") or ""
            if c.get("ar") and why.startswith(c["ar"] + ":"):
                why = why[len(c["ar"]) + 1:].strip()
            grey[re.sub(r"\s*\(.*", "", why)[:70]].append("%s %s" % (mm(T[int(k)]["t"]), c.get("ar") or ""))
            if c.get("label") == "vocab" and not c.get("ar") and T[int(k)].get("who") == "Medi" and not c.get("rule"):
                nameless.append(mm(T[int(k)]["t"]) + " " + why[:60])
    out("2 grey chips on the page: %d (by reason)" % sum(len(x) for x in grey.values()))
    for why, l in sorted(grey.items(), key=lambda x: -len(x[1])):
        out("   %3d  %s  | %s" % (len(l), why, ", ".join(l[:6])))
    if nameless:
        out("   grey vocab chips with no word (PG-44): " + "; ".join(nameless))
        flags["nameless"] += len(nameless)

    # 3 not on her list: her word by sound? (the engine's بيد for his بعيد / غير)
    out("3 'not on her word list' - read each against the lines around it:")
    for k, v in tm.items():
        for c in v["c"]:
            if c.get("hide") or "not on her word list" not in (c.get("why") or "") or not c.get("ar"):
                continue
            i = int(k)
            w = c["ar"]
            near = []
            if keys:
                for key in keys.keys:
                    a = WC.jsnorm((keys.words[key].get("arabic") or ""))
                    if a and len(a) <= len(w) + 2 and WC.similar(a, w) and a != WC.jsnorm(w):
                        near.append("%s %s" % (keys.words[key].get("arabizi"), keys.words[key].get("arabic")))
            prev = next((T[j]["text"] for j in range(i - 1, max(-1, i - 4), -1) if T[j]["who"] == "Amal"), "")
            nxt = next((T[j]["text"] for j in range(i + 1, min(len(T), i + 4)) if T[j]["who"] == "Amal"), "")
            out("   %s %s | line: %s | her before: %s | after: %s%s" % (mm(T[i]["t"]), w, T[i]["text"][:60], prev[:40], nxt[:40],
                                                                     (" | sounds like her: " + ", ".join(near[:3])) if near else ""))
            flags["off_list"] += 1

    # 4 Latin or * on an Arabic line
    out("4 Latin letters / * on a line in Arabic script:")
    for u in T:
        txt = u.get("text") or ""
        latin = [x for x in re.findall(r"[A-Za-z0-9'*]+", txt) if re.search(r"\d|\*", x)]
        if AR.search(txt) and latin:
            out("   %s %s: %s" % (mm(u["t"]), u["who"], txt[:90]))
            flags["latin"] += 1

    # 5 her nod
    for u in T:
        if u.get("who") == "Amal" and re.fullmatch(r"\s*(مهم|ممم|مم)\s*[.؟?،]?\s*", u.get("text") or ""):
            out("5 her nod still read as a word: %s %s" % (mm(u["t"]), u["text"]))
            flags["nod"] += 1

    # 6 the same word credited twice in a row
    last = None
    for i, u in enumerate(T):
        if u.get("who") != "Medi":
            if not WC.TUTOR_NOD.match(u.get("text") or ""):
                last = None
            continue
        ok = {WC.core(x.get("tok") or x.get("ar") or "") for c in chips(i) if c.get("k") == "vocab" and c.get("s") == "correct"
              for x in (c.get("words") or [c])}
        said = {WC.core(w) for w, cut in WC.arabic_tokens(u.get("text")) if not cut}
        ok = {x for x in ok if x in said}                 # the form he said on this line (غيوم and غيم are two tries)
        if last is not None:
            both = ok & last[1]
            if both and float(u["t"]) - float(T[last[0]].get("end") or T[last[0]]["t"]) <= 10:
                out("6 credited on two lines in a row: %s / %s %s" % (mm(T[last[0]]["t"]), mm(u["t"]), " ".join(sorted(both))))
                flags["twice"] += 1
        last = (i, ok)

    # 7 his English question about her words
    for i, u in enumerate(T):
        js = WC.question_about(T, i) if u.get("who") == "Medi" else []
        if js:
            hers = {WC.core(w) for j in js for w in WC.her_words(T, j)}
            bad = [c for c in chips(i) if c.get("s") == "correct" and not c.get("hide") and c.get("k") == "vocab"
                   and any(WC.core(x.get("tok") or x.get("ar") or "") in hers for x in (c.get("words") or [c]))]
            if bad:
                out("7 ✓ on his question about her words: %s %s | %s" % (mm(u["t"]), u["text"][:70], ", ".join(
                    (c.get("k") or "") + " " + str(c.get("rule") or c.get("w") or "") for c in bad)))
                flags["question"] += 1

    # 8 English under every Arabic line
    no_en = [u for u in T if u.get("who") in ("Medi", "Amal") and AR.search(u.get("text") or "") and not u.get("en")]
    out("8 Arabic lines with no English: %d %s" % (len(no_en), ", ".join(mm(u["t"]) for u in no_en[:12])))
    flags["english"] += len(no_en)

    # 9 her lines to read (the English sounds wrong, or her Arabic is a word on no list near his question)
    out("9 her lines to read (odd English):")
    for i, u in enumerate(T):
        if u.get("who") == "Amal" and AR.search(u.get("text") or "") and ODD_EN.search(u.get("en") or ""):
            out("   %s %s | %s" % (mm(u["t"]), u["text"][:60], u.get("en")))

    # 10 every ✗ with her line after it
    out("10 slips (✗) with her next line:")
    for i, u in enumerate(T):
        for c in chips(i):
            if c.get("s") == "wrong" and not c.get("hide") and c.get("k") in ("vocab", "grammar"):
                nxt = next((T[j] for j in range(i + 1, min(len(T), i + 5)) if T[j]["who"] == "Amal"), {})
                out("   %s %s %s: %s -> %s | she: %s" % (mm(u["t"]), c["k"], c.get("rule") or "", c.get("said") or c.get("ar") or "",
                                                     c.get("right") or "", (nxt.get("text") or "")[:50]))

    if notes:
        import medi_corrections as MC
        out("notes Medi wrote on %s:" % date)
        for r in sorted((r for r in MC.effective() if str(r.get("lesson_date")) == date and r.get("kind") == "note"),
                        key=lambda r: float(r["turn_t"])):
            i = min(range(len(T)), key=lambda k: abs(float(T[k]["t"]) - float(r["turn_t"])))
            out("   %s %s | %s | %s" % (mm(r["turn_t"]), ((r.get("payload") or {}).get("raw") or r.get("note") or "")[:90], T[i]["text"][:50],
                                        "; ".join("%s/%s %s" % (c.get("k"), c.get("s"), c.get("w") or c.get("ar") or "") for c in chips(i) if not c.get("hide"))))
    L = next((l for l in (J(os.path.join(REPO, "docs", "data", "lessons.json"), {}) or {}).get("lessons", []) if l.get("date") == date), {})
    out("summary %s: Words %s%% · Grammar %s%% · flags %s" % (date, (L.get("words") or {}).get("pct") if isinstance(L.get("words"), dict) else L.get("words_pct"),
                                                         (L.get("grammar") or {}).get("pct"), dict(flags)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sys.exit(audit(a[0] if a else "2026-10-09", notes="--notes" in sys.argv))
