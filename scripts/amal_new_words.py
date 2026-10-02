# -*- coding: utf-8 -*-
"""New words Amal used in a lesson that are not on her vocabulary Doc -> a Tutor hub item for her (Medi 2026-10-02:
"She said a new word in the lesson today that's not on our document. On the tutor hub you should bring it to her
attention if she wants to add it to the document, save it for a future lesson, or forget it" + "we should be doing this
for all new lessons").

Two stages, the same standard as every other detector (memory anees-15s-rule-is-a-clue / anees-list-by-meaning: a machine
flag is a clue, a by-meaning read decides):

  1 candidates  python scripts/amal_new_words.py --candidates 2026-10-01
                Every word Amal SAID (her track) or TYPED (her Meet chat lines) in that lesson, minus what a string check
                can already rule out: words on the Doc (docs/data/words.json: Arabic, plural and Arabizi forms, with
                و/ب/ل/ف/ال and the common endings stripped), proper names (docs/data/names.json via scripts/names.py),
                plain function words and plain English. -> data/lesson-work/amal-new-words/<date>.candidates.json
  2 verdicts    a reader (review_lesson.py step 7d, or by hand) judges each candidate BY MEANING and writes
                data/lesson-work/amal-new-words-verdicts.json [{date, key, verdict, arabic, arabizi, english, t, reason}]
                verdict: new | on_doc | name | english | function | garble | loanword (WS-15: dish names, foods,
                brands, loan words, countries - never asked; scripts/loanwords.py also drops them at both stages).  Only 'new' ever reaches Amal; other forms
                of the same new word carry dup_of=<first key> and are not shown twice.
  3 build       python scripts/amal_new_words.py            (in amal_trigger.AUDIT_CHAIN, before build_tutor_data)
                -> docs/data/amal-new-words.json: one item per 'new' word (Arabic, her spelling when she typed it -
                never a guessed Arabizi, RULES.md S1 - English, time, her line, the moment in the lesson audio) and her
                choice read back from Supabase amal_rules (source 'review', word_key 'newword:...', kind newword_add /
                newword_later / newword_forget - written by docs/js/hub/new-words-task.js on the Tutor hub).
                A chosen item leaves the To-do list; 'add' items are listed as PENDING Doc additions for Medi. Nothing
                here edits her Doc or docs/data/words.json (never edit Amal's data).

Unjudged candidates are never shown to Amal (no flooding); the build counts them so a missing read is visible.
"""
import argparse, datetime, hashlib, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import loanwords  # noqa: E402  (WS-15)
import word_marks  # noqa: E402  (AM-16)
WORDS = os.path.join(REPO, "docs", "data", "words.json")
LESSONS = os.path.join(REPO, "docs", "data", "lessons")
WORK = os.path.join(REPO, "data", "lesson-work", "amal-new-words")
VERDICTS = os.path.join(REPO, "data", "lesson-work", "amal-new-words-verdicts.json")
OUT = os.path.join(REPO, "docs", "data", "amal-new-words.json")
GLUE_DATE = "2026-10-02"     # the day Medi asked for the glue words (WS-19); their cards carry this date
START = "2026-10-01"           # Medi 2026-10-02: from today's lesson on (older lessons were never asked)
KINDS = {"newword_add": "add", "newword_add_new": "add", "newword_add_old": "add", "newword_later": "later", "newword_forget": "forget"}
# newword_add (before 2026-10-02) = add, age not said; newword_add_new / newword_add_old = AM-16 (Medi 2026-10-02: "We need a
# way for her to indicate old and new words")
VERDICT_KINDS = ("new", "on_doc", "name", "english", "function", "garble", "loanword")

AR_TOKEN = re.compile("[ء-غف-يٱ-ۓً-ٰٟ]+")
LAT_TOKEN = re.compile("[A-Za-z0-9'’]+")
MARKS = re.compile("[ً-ٰٟـ]")
PREFIXES = ("وبال", "وال", "بال", "فال", "عال", "لل", "و", "ب", "ل", "ف", "ع")
SUFFIXES = ("كم", "هم", "ها", "نا", "ين", "ات", "ون", "ك", "ه", "ي", "ت", "و")
# Particles, pronouns, demonstratives, question words, fillers: grammar, not vocabulary (Arabic, normalised).
FUNCTION_AR = set("""و او ولا يا في فيه فيها من منه منها مع عن على ع عند عنده عندي ل لا ما مش مو بس كمان هيك هيك
ان انه انا انت انتي انتو انتم هو هي هم احنا نحنا اللي الي هاد هاذا هذا هاي هذه هذي هدول هناك هون هنا كيف شو ايش
ليش وين متى قديش كم مين اذا لو لما لانه لان عشان علشان حتى يعني طيب اه اها لا ايوه اوكي اوك يلا كمان برضو بعدين
ال بال كل كله شي اشي اي هلا هلق هلأ زي متل مثل اكثر اقل قبل بعد""".split())
FUNCTION_LAT = set("""u w wa aw willa wala ya fi fe min mn ma3 3an 3ala 3a 3ind 3inde la ma mish msh bas kaman hek heik
ana inta inti into huwwe hiyye hiyya humme i7na illi hada hadi hadol hon hnak keef kif shu eish leish wein waen mata
2addesh kam meen iza law lamma la2ino 3ashaan 7atta ya3ni tayyeb aah la2 aywa okay ok yalla barde ba3dein el il al l
kol kul ishi shi ay halla2 zay mitl aktar a2al abel ba3d""".split())
EN_STOP = set("""a an the and or but so if of to in on at for from with by is are was were be been am i you he she it we
they me my your his her our their this that these those what when where why how who which not no yes yeah ok okay oh um uh
hmm sorry hi hello bye good great nice very really just like do does did have has had can could would should will
there here then than too also all some any one two three more most much many again now later today tomorrow yesterday""".split())


def _function_ar():
    return {ar_norm(w) for w in FUNCTION_AR}


def ar_norm(s):
    s = MARKS.sub("", s or "")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"), ("ء", "")):
        s = s.replace(a, b)
    return s


FUNCTION_AR_N = set()


def lat_norm(s):
    return re.sub("['’]", "", (s or "").lower())


def ar_stems(tok):
    """The token and its forms without proclitics / one common ending (all normalised). Never shorter than 2 letters."""
    n = ar_norm(tok)
    forms = {n}
    for p in PREFIXES:
        if n.startswith(p) and len(n) - len(p) >= 2:
            rest = n[len(p):]
            forms.add(rest)
            if p.endswith("ال") or p == "لل":
                forms.add("ال" + rest)
    for f in list(forms):
        if f.startswith("ال") and len(f) > 3:
            forms.add(f[2:])
    for f in list(forms):
        for s in SUFFIXES:
            if f.endswith(s) and len(f) - len(s) >= 2:
                forms.add(f[:-len(s)])
    for f in list(forms):                      # construct state: شنطت(ك) -> شنطة
        if f.endswith("ت") and len(f) >= 3:
            forms.add(f[:-1] + "ه")
    return forms


def lat_stems(tok):
    n = lat_norm(tok)
    forms = {n}
    m = re.match(r"^(?:el|il|al)-?(.+)$", n)
    if m and len(m.group(1)) >= 2:
        forms.add(m.group(1))
    for f in list(forms):                      # one ending off (shantet / shanta -> shant; madrasto -> madrast)
        for e in ("et", "it", "eh", "ah", "o", "a", "e", "i"):
            if f.endswith(e) and len(f) - len(e) >= 3:
                forms.add(f[:-len(e)])
    return forms


def doc_index(words=None):
    """{'ar': set of normalised Arabic tokens on the Doc, 'lat': set of Arabizi tokens} - every item's Arabic, plural,
    aliases and Arabizi, split into single words (a multi-word entry lists each of its words)."""
    W = words if words is not None else json.load(open(WORDS, encoding="utf-8"))
    ar, lat = set(), set()
    for it in W.get("items", []):
        for field in ("arabic", "plural", "arabic_norm"):
            for t in AR_TOKEN.findall(it.get(field) or ""):
                ar |= ar_stems(t)
        for a in it.get("aliases") or []:
            for t in AR_TOKEN.findall(str(a)):
                ar |= ar_stems(t)
            for t in LAT_TOKEN.findall(str(a)):
                lat |= lat_stems(t)
        for field in ("arabizi", "plural", "key", "match_loose"):
            for t in LAT_TOKEN.findall(it.get(field) or ""):
                lat |= lat_stems(t)
    return {"ar": {x for x in ar if len(x) >= 2}, "lat": {x for x in lat if len(x) >= 2}}


def name_spans(date):
    """[(turn index, start, end)] of proper names (scripts/names.py layer, not written to disk)."""
    try:
        import names
        return [(s["i"], s["s"], s["e"]) for s in names.layer(date, write=False)["spans"]]
    except Exception:
        return []


def in_name(spans, i, s, e):
    return any(j == i and s < ne and e > ns for j, ns, ne in spans)


def mmss(t):
    t = int(round(t or 0))
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def candidates(date, lesson=None, index=None, spans=None):
    if not FUNCTION_AR_N:
        FUNCTION_AR_N.update(_function_ar())
    """Words Amal said or typed in the lesson that a string check cannot place on the Doc. One entry per normalised
    word: {key, word, script, source ('said'|'typed'), count, t, lines:[{t, who, text}]}. `excluded` counts what the string
    stage already removed (on_doc / name / function / english)."""
    L = lesson if lesson is not None else json.load(open(os.path.join(LESSONS, date + ".json"), encoding="utf-8"))
    idx = index if index is not None else doc_index()
    spans = name_spans(date) if spans is None else spans
    found, excluded = {}, {"on_doc": 0, "name": 0, "function": 0, "english": 0, "loanword": 0}
    for i, turn in enumerate(L.get("turns") or []):
        who = turn.get("who")
        typed = who == "chat" and (turn.get("typed_by") or "Amal") == "Amal"
        if who != "Amal" and not typed:
            continue
        text = turn.get("text") or ""
        toks = [(m.start(), m.end(), m.group(0), "ar") for m in AR_TOKEN.finditer(text)]
        if typed:      # her chat is Arabizi (Latin) with English mixed in
            toks += [(m.start(), m.end(), m.group(0), "lat") for m in LAT_TOKEN.finditer(text)]
        for s, e, raw, sc in toks:
            if in_name(spans, i, s, e):
                excluded["name"] += 1; continue
            if loanwords.loan_token(raw):          # WS-15: dishes, foods, brands, loan words never reach Amal's list
                excluded["loanword"] += 1; continue
            if sc == "ar":
                n = ar_norm(raw)
                if len(n) < 2 or n in FUNCTION_AR_N:
                    excluded["function"] += 1; continue
                if ar_stems(raw) & idx["ar"]:
                    excluded["on_doc"] += 1; continue
            else:
                n = lat_norm(raw)
                if len(n) < 2 or n.isdigit():
                    continue
                if n in FUNCTION_LAT:
                    excluded["function"] += 1; continue
                if lat_stems(raw) & idx["lat"]:
                    excluded["on_doc"] += 1; continue
                if n in EN_STOP:
                    excluded["english"] += 1; continue
            c = found.setdefault(n, {"key": n, "word": raw, "script": sc, "source": "typed" if typed else "said",
                                     "count": 0, "t": turn.get("t"), "lines": []})
            c["count"] += 1
            if len(c["lines"]) < 3 and not any(x["t"] == turn.get("t") for x in c["lines"]):
                c["lines"].append({"t": turn.get("t"), "mmss": mmss(turn.get("t")), "who": "Amal (chat)" if typed else "Amal", "text": text})
    rows = sorted(found.values(), key=lambda c: (c["t"] or 0))
    return {"date": date, "count": len(rows), "excluded_by_string_check": excluded, "candidates": rows}


def write_candidates(date):
    os.makedirs(WORK, exist_ok=True)
    C = candidates(date)
    C["how"] = ("Machine candidates only (a clue, not a verdict). A reader judges each BY MEANING against docs/data/words.json "
                "(any form, Arabic or English meaning) and writes data/lesson-work/amal-new-words-verdicts.json.")
    p = os.path.join(WORK, date + ".candidates.json")
    json.dump(C, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return p, C


def item_id(date, key):
    return "newword:" + date + ":" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def load_taps():
    """{word_key: (kind, created_at, token)} - the latest tap per item from Supabase amal_rules. None when it cannot be read.
    AM-17: db.select leaves out a tap Amal undid (scripts/amal_undo.py), so an undone item is open again."""
    try:
        import db
        rows = db.select("amal_rules", {"select": "kind,word_key,created_at,token", "source": "eq.review",
                                        "word_key": "like.newword:*", "order": "created_at.asc"}, retries=3)
    except Exception as e:
        print("amal_rules not readable:", type(e).__name__, str(e)[:120])
        return None
    out = {}
    for r in rows:
        if r.get("kind") in KINDS:
            out[r["word_key"]] = (r["kind"], r.get("created_at"), r.get("token"))
    return out


def build(verdicts=None, taps=None, previous=None, lesson_audio=None, today=None, marks=None, doc=None, glue=False):
    """Pure: verdict rows + taps -> the page data. `previous` = the last built file (statuses kept when taps is None).
    `marks` = data/word-marks.json (Medi's old/new marks, AM-16), `doc` = docs/data/words.json (her Doc: a promised word
    moves Waiting -> In the Doc when it appears there)."""
    M = marks if marks is not None else word_marks.load()
    W = doc if doc is not None else (json.load(open(WORDS, encoding="utf-8")) if os.path.exists(WORDS) else {"items": []})
    prev_promised = {x["id"]: x for x in ((previous or {}).get("promised") or [])}
    day = (today or datetime.date.today().isoformat())[:10]
    V = verdicts if verdicts is not None else (json.load(open(VERDICTS, encoding="utf-8")) if os.path.exists(VERDICTS) else [])
    prev = {x["id"]: x for x in ((previous or {}).get("items") or [])}
    items, excl = [], {}
    for v in V:
        d = v.get("date") or ""
        if d < START:
            continue
        e = excl.setdefault(d, {k: 0 for k in VERDICT_KINDS if k != "new"})
        verdict = v.get("verdict")
        if verdict == "new" and any(loanwords.loan_entry(x) for x in (v.get("arabic"), v.get("arabizi"), v.get("key")) if x):
            e["loanword"] = e.get("loanword", 0) + 1     # WS-15: a reader's 'new' on a dish / loan word / country is overruled
            continue
        if verdict == "new" and v.get("dup_of"):          # another form of a word already listed (the first key is shown)
            e["duplicate"] = e.get("duplicate", 0) + 1
            continue
        if verdict != "new":
            if verdict in e:
                e[verdict] += 1
            continue
        iid = item_id(d, v["key"])
        if any(x["id"] == iid for x in items):
            continue
        t = v.get("t")
        audio = (lesson_audio or (lambda dd: f"lessons/{dd}/audio/lesson.mp3"))(d)
        it = {"id": iid, "date": d, "key": v["key"], "arabic": v.get("arabic"), "arabizi": v.get("arabizi") or None,
              "english": v.get("english"), "t": t, "mmss": mmss(t) if t is not None else None, "line": v.get("line"),
              "typed": bool(v.get("typed")), "reason": v.get("reason"),
              "clip": {"src": audio, "start": max(0.0, float(t) - 2.0), "end": float(t) + 8.0} if t is not None else None}
        if taps is not None:
            k = taps.get(iid)
        else:
            p = prev.get(iid) or {}
            kk = p.get("tap") or next((kk for kk, vv in KINDS.items() if vv == p.get("status")), None)
            k = (kk, p.get("answered_at"), p.get("tap_token")) if p.get("status") not in (None, "open") else None
        it["status"], it["answered_at"] = (KINDS[k[0]], k[1]) if k and k[0] in KINDS else ("open", None)
        it["tap"] = k[0] if k and k[0] in KINDS else None
        # AM-17: the link the tap came from - the hub trusts a live read of that link over this build (a tap removed or
        # undone since the build shows open at once)
        it["tap_token"] = (k[2] if len(k) > 2 else None) if it["tap"] else None
        mk = word_marks.mark_for(it, M)                    # AM-16: Medi's mark is a hint on her card, never pre-selected
        it["medi_mark"] = mk.get("mark") if mk else None
        it["hint"] = (mk.get("hint") or word_marks.HINT_OLD) if it["medi_mark"] == "old" else None
        it["age"], it["age_by"] = word_marks.resolve(it["medi_mark"], it["tap"])
        items.append(it)
    # WS-19 (Medi 2026-10-02: "the glue words should be added to the doc, bring to her attention"): every glue word not on
    # her Doc is one card here too, with Medi's old-word hint; nothing pre-selected, her tap decides (same choices).
    import glue_words
    for gk, gar, gen in (glue_words.not_on_doc(W) if glue else []):
        iid = item_id(GLUE_DATE, "glue:" + gk)
        it = {"id": iid, "date": GLUE_DATE, "key": "glue:" + gk, "arabic": gar, "arabizi": None, "english": gen, "t": None,
              "mmss": None, "line": None, "typed": False, "source": "glue", "reason": "glue word Medi uses a lot; not on the Doc",
              "clip": None}
        k = taps.get(iid) if taps is not None else ((lambda p: (p.get("tap"), p.get("answered_at"), p.get("tap_token")) if p.get("status") not in (None, "open") else None)(prev.get(iid) or {}))
        it["status"], it["answered_at"] = (KINDS[k[0]], k[1]) if k and k[0] in KINDS else ("open", None)
        it["tap"] = k[0] if k and k[0] in KINDS else None
        it["tap_token"] = (k[2] if len(k) > 2 else None) if it["tap"] else None
        mk = word_marks.mark_for(it, M)
        it["medi_mark"] = mk.get("mark") if mk else None
        it["hint"] = (mk.get("hint") or word_marks.HINT_OLD) if mk and mk.get("mark") == "old" else glue_words.HINT
        it["age"], it["age_by"] = word_marks.resolve(it["medi_mark"], it["tap"])
        items.append(it)
    items.sort(key=lambda x: (x["date"], x["t"] or 0), reverse=False)
    items.sort(key=lambda x: x["date"], reverse=True)
    out = {"built": today or datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "about": "Words Amal used in a lesson that are not on her vocabulary Doc (judged by meaning). Her choice: add to the Doc / "
                    "save for a future lesson / forget it. 'Add' = waiting for her to add it to the Doc; nothing edits the Doc.",
           "since": START, "taps_read": taps is not None,
           "counts": {"items": len(items), "open": sum(1 for x in items if x["status"] == "open"),
                      "add": sum(1 for x in items if x["status"] == "add"), "later": sum(1 for x in items if x["status"] == "later"),
                      "forget": sum(1 for x in items if x["status"] == "forget")},
           "excluded": excl, "items": items,
           "pending_doc_additions": [{"id": x["id"], "date": x["date"], "arabic": x["arabic"], "arabizi": x["arabizi"], "english": x["english"]}
                                     for x in items if x["status"] == "add"]}
    # AM-16 "Keep a tab of what she said shes going to add": every word Amal tapped Add (new or old) -> Waiting, then
    # In the Doc since <date> once the Doc import shows it in her Doc. Medi's marks she has not answered yet are listed
    # as awaiting_amal ("Medi marked old - waiting for Amal").
    promised = []
    for x in items:
        if x["status"] == "add":
            pid = x["id"]
        elif x["medi_mark"] and x["status"] == "open":
            pid = x["id"]
        else:
            continue
        in_doc = word_marks.doc_has(x, W)
        was = prev_promised.get(pid) or {}
        state = ("in_doc" if in_doc else "waiting") if x["status"] == "add" else "awaiting_amal"
        promised.append({"id": pid, "date": x["date"], "arabic": x["arabic"], "arabizi": x["arabizi"], "english": x["english"],
                         "age": x["age"], "age_by": x["age_by"], "marks": {"medi": x["medi_mark"], "amal": word_marks.AGE_OF_TAP.get(x["tap"])},
                         "tapped_at": x["answered_at"], "state": state,
                         "in_doc_since": (was.get("in_doc_since") or day) if state == "in_doc" else None})
    out["promised"] = promised
    out["counts"]["promised_waiting"] = sum(1 for p in promised if p["state"] == "waiting")
    out["counts"]["promised_in_doc"] = sum(1 for p in promised if p["state"] == "in_doc")
    return out


def unjudged(verdicts):
    """{date: n} candidates of lessons since START that have no verdict yet (a read is missing)."""
    have = {(v.get("date"), v.get("key")) for v in verdicts}
    out = {}
    if not os.path.isdir(WORK):
        return out
    for f in sorted(os.listdir(WORK)):
        m = re.fullmatch(r"(20\d\d-\d\d-\d\d)\.candidates\.json", f)
        if not m or m.group(1) < START:
            continue
        C = json.load(open(os.path.join(WORK, f), encoding="utf-8"))
        n = sum(1 for c in C["candidates"] if (m.group(1), c["key"]) not in have)
        if n:
            out[m.group(1)] = n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", metavar="DATE", help="write the machine candidates of one lesson for the reader")
    ap.add_argument("--offline", action="store_true", help="do not read Supabase (keep the statuses already built)")
    a = ap.parse_args()
    if a.candidates:
        p, C = write_candidates(a.candidates)
        print("candidates", a.candidates, C["count"], "excluded", C["excluded_by_string_check"], "->", os.path.relpath(p, REPO))
        return 0
    # every lesson since START gets its candidate file (cheap, string-only), so a missing read shows up as 'unjudged'
    for f in sorted(os.listdir(LESSONS)):
        m = re.fullmatch(r"(20\d\d-\d\d-\d\d)\.json", f)
        if m and m.group(1) >= START and not os.path.exists(os.path.join(WORK, m.group(1) + ".candidates.json")):
            write_candidates(m.group(1))
    V = json.load(open(VERDICTS, encoding="utf-8")) if os.path.exists(VERDICTS) else []
    bad = [v for v in V if v.get("verdict") not in VERDICT_KINDS or not v.get("date") or not v.get("key")]
    if bad:
        print("verdict rows without date/key/known verdict:", bad[:3]); return 1
    prev = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else None
    taps = None if a.offline else load_taps()
    if taps is None and os.environ.get("ANEES_STRICT") == "1" and not a.offline:
        print("FAILED: Amal's taps could not be read (ANEES_STRICT)"); return 1
    out = build(V, taps, prev, glue=True)
    out["unjudged"] = unjudged(V)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("amal-new-words", out["counts"], "excluded", out["excluded"], "unjudged", out["unjudged"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
