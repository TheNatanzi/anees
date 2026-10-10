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


def build(verdicts=None, taps=None, previous=None, lesson_audio=None, today=None, marks=None, doc=None, glue=False,
          taught=None, taught_verdicts=None, turns_for=None):
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
    # AM-19: words she taught (every lesson) -> the same cards; `taught` = taught_entries(), None = not built here
    T_map, T_counts = None, None
    if taught is not None:
        TV = taught_verdicts if taught_verdicts is not None else (
            json.load(open(TAUGHT_VERDICTS, encoding="utf-8")) if os.path.exists(TAUGHT_VERDICTS) else [])
        T_items, T_map, T_counts = taught_build(taught, TV, W, items, taps, prev, M, lesson_audio, turns_for)
        items.extend(T_items)
    items.sort(key=lambda x: (x["date"], x["t"] or 0), reverse=False)
    items.sort(key=lambda x: x["date"], reverse=True)
    out = {"built": today or datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "about": "Words Amal used in a lesson that are not on her vocabulary Doc (judged by meaning). Her choice: add to the Doc / "
                    "save for a future lesson / forget it. 'Add' = waiting for her to add it to the Doc; nothing edits the Doc.",
           "since": START, "taps_read": taps is not None,
           "counts": {"items": len(items), "open": sum(1 for x in items if x["status"] == "open"),
                      "add": sum(1 for x in items if x["status"] == "add"), "later": sum(1 for x in items if x["status"] == "later"),
                      "forget": sum(1 for x in items if x["status"] == "forget")},
           "excluded": excl, "items": items, "older_before": START, "older_fold": OLDER_FOLD,
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
        # AM-19 "make sure that she adds them": Waiting for WAIT_DAYS or more -> still_waiting (a gentle mark on her list
        # and one line for Medi on the Word Bank; the code never messages her, ai_rules A1)
        days = None
        if state == "waiting" and x["answered_at"]:
            try:
                days = (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(str(x["answered_at"])[:10])).days
            except ValueError:
                days = None
        promised.append({"id": pid, "date": x["date"], "arabic": x["arabic"], "arabizi": x["arabizi"], "english": x["english"],
                         "age": x["age"], "age_by": x["age_by"], "marks": {"medi": x["medi_mark"], "amal": word_marks.AGE_OF_TAP.get(x["tap"])},
                         "tapped_at": x["answered_at"], "state": state, "waiting_days": days,
                         "still_waiting": bool(days is not None and days >= WAIT_DAYS),
                         "in_doc_since": (was.get("in_doc_since") or day) if state == "in_doc" else None})
    out["promised"] = promised
    out["counts"]["promised_waiting"] = sum(1 for p in promised if p["state"] == "waiting")
    out["counts"]["promised_in_doc"] = sum(1 for p in promised if p["state"] == "in_doc")
    out["counts"]["promised_still_waiting"] = sum(1 for p in promised if p.get("still_waiting"))
    out["counts"]["older_open"] = sum(1 for x in items if x["status"] == "open" and x["date"] < START)
    if T_map is not None:
        # a card whose word is in the Doc now counts as in the Doc on the lesson page too
        for rows in T_map.values():
            for r in rows:
                p = next((q for q in promised if q["id"] == r.get("card")), None)
                if p and p["state"] == "in_doc":
                    r["status"], r["status_label"] = "in_doc", TAUGHT_STATUS["in_doc"]
                elif p and p.get("still_waiting"):
                    r["still_waiting"] = True
        out["taught"], out["taught_counts"] = T_map, T_counts
    return out


# ---------------------------------------------------------------- AM-19: words Amal TAUGHT -> her New words card
# Medi 2026-10-02: "we have a process already for words like metshaje3. We need to ask amal if she wants to add them in
# the tutor hub and then make sure that she adds them." Every word the lesson-type reader found she taught
# (data/lesson-work/lesson-types/<date>.json taught_words + taught, every lesson - START does not apply) plus the hand
# verb pairs (docs/data/lessons.json `taught`) is judged BY MEANING against her Doc once
# (data/lesson-work/taught-words-verdicts.json: on_doc | new | on_card {date,key} = already on her card; dup_of = another
# form of a new word of the same lesson). A word in her Doc only shows as taught on the lesson page; a new one is one card
# (same choices, same promised list), deduped by meaning across lessons; WS-15 loanwords never reach her.
TAUGHT_VERDICTS = os.path.join(REPO, "data", "lesson-work", "taught-words-verdicts.json")
LESSONS_JSON = os.path.join(REPO, "docs", "data", "lessons.json")
OLDER_FOLD = 25        # more open cards than this from lessons before START -> folded under "From older lessons"
WAIT_DAYS = 7          # a promised word not in the Doc after this many days -> "still waiting" (no message is sent, A1)
TAUGHT_STATUS = {"in_doc": "In the Doc", "waiting_amal": "Waiting for Amal", "promised": "Amal said she'll add it",
                 "later": "Amal saved it for a later lesson", "forgotten": "Amal said forget it", "unjudged": "Not checked against the Doc yet"}


def _secs(t):
    if t is None or t == "":
        return None
    if isinstance(t, (int, float)):
        return float(t)
    p = [int(x) for x in str(t).split(":")]
    return float(p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1])


def _tkey(arabic, latin=None):
    return ar_norm(re.sub(r"\s+", " ", arabic or "").strip()) or lat_norm(latin or "")


def taught_entries(reads=None, lessons=None):
    """Union per lesson of the reader's taught_words + taught verb pairs and the hand verb pairs, in date order:
    [{date, kind 'word'|'verb', latin, arabic, english, t (s), by 'reader'|'hand'}], one per (date, Arabic)."""
    import lesson_type_read as LTR
    R = reads if reads is not None else LTR.load_all(REPO)
    if lessons is None:
        lessons = json.load(open(LESSONS_JSON, encoding="utf-8")).get("lessons", []) if os.path.exists(LESSONS_JSON) else []
    out, seen = [], set()

    def add(d, kind, x, by):
        k = (d, _tkey(x.get("arabic"), x.get("latin")))
        if not k[1] or k in seen:
            return
        seen.add(k)
        out.append({"date": d, "kind": kind, "latin": x.get("latin") or None, "arabic": x.get("arabic") or None,
                    "english": x.get("english") or None, "t": _secs(x.get("t")), "review": bool(x.get("review")), "by": by})
    for L in lessons:
        for x in L.get("taught") or []:
            add(L["date"], "verb", x, "hand")
    for d, r in R.items():
        for x in r.get("taught") or []:
            add(d, "verb", x, "reader")
        for x in r.get("taught_words") or []:
            add(d, "word", x, "reader")
    return sorted(out, key=lambda e: (e["date"], e["t"] if e["t"] is not None else 1e9))


def _parts(e):
    """The entry as Doc-checkable words: the whole Arabic and each '/' part, each '/' part of her Arabizi."""
    ars = [e.get("arabic")] + [p for p in re.split(r"\s*/\s*", e.get("arabic") or "") if p]
    lats = [p for p in re.split(r"\s*/\s*", e.get("latin") or "") if len(p) > 2]
    return [{"arabic": a, "arabizi": None} for a in ars if a] + [{"arabic": None, "arabizi": l} for l in lats]


def in_doc(e, doc):
    return any(word_marks.doc_has(p, doc) for p in _parts(e))


def _taught_line(turns, e):
    """(her line, typed?) near the moment: a chat line of hers with the Arabizi, else her spoken turn with the Arabic."""
    t = e.get("t")
    if t is None:
        return None, False
    lat = [lat_norm(p) for p in re.split(r"\s*/\s*", e.get("latin") or "") if len(p) > 2]
    ar = [ar_norm(p) for p in re.split(r"\s*/\s*", e.get("arabic") or "") if p]
    for u in turns:
        ut = float(u.get("t") or 0)
        if u.get("who") == "chat" and (u.get("typed_by") or "Amal") == "Amal" and t - 10 <= ut <= t + 240 and lat \
                and any(x in lat_norm(u.get("text")) for x in lat):
            return u.get("text"), True
    for u in turns:
        ut = float(u.get("t") or 0)
        if u.get("who") == "Amal" and abs(ut - t) <= 20 and any(x and x in ar_norm(u.get("text")) for x in ar):
            return u.get("text"), False
    return None, False


def _lesson_turns(date):
    p = os.path.join(LESSONS, date + ".json")
    try:
        return json.load(open(p, encoding="utf-8")).get("turns") or []
    except Exception:
        return []


def _tap_of(iid, taps, prev):
    if taps is not None:
        return taps.get(iid)
    p = prev.get(iid) or {}
    kk = p.get("tap") or next((kk for kk, vv in KINDS.items() if vv == p.get("status")), None)
    return (kk, p.get("answered_at"), p.get("tap_token")) if p.get("status") not in (None, "open") else None


def taught_build(entries, verdicts, doc, items, taps, prev, marks, lesson_audio=None, turns_for=None):
    """-> (new card items, {date: [taught word + status]}, counts). `items` = the cards already built (reader + glue);
    a word already on one of them (by meaning, or the verdict's on_card) links to it instead of a second card."""
    vmap = {(v.get("date"), _tkey(v.get("arabic"), v.get("latin"))): v for v in verdicts or []}
    turns_for = turns_for or _lesson_turns
    new_items, taught, counts = [], {}, {"entries": 0, "in_doc": 0, "new_cards": 0, "linked": 0, "unjudged": 0, "loanword": 0}
    by_id = {x["id"]: x for x in items}

    def status_of(it):
        if it["status"] == "open":
            return "waiting_amal"
        if it["status"] == "add":
            return "in_doc" if word_marks.doc_has(it, doc) else "promised"
        return {"later": "later", "forget": "forgotten"}.get(it["status"], "waiting_amal")

    def same_meaning(e, it):
        return any(word_marks.same(p, {"arabic": it.get("arabic"), "arabizi": it.get("arabizi")}) for p in _parts(e))

    for e in entries:
        counts["entries"] += 1
        v = vmap.get((e["date"], _tkey(e.get("arabic"), e.get("latin"))))
        row = {k: e.get(k) for k in ("kind", "latin", "arabic", "english", "by")}
        row.update(t=e.get("t"), mmss=mmss(e["t"]) if e.get("t") is not None else None, card=None)
        verdict = (v or {}).get("verdict")
        card = None
        if v is None:                                        # no by-meaning row yet: a card of the same word still links
            card = next((x for x in list(by_id.values()) if x.get("source") != "glue" and same_meaning(e, x)), None)
        elif verdict == "on_card" and v.get("card"):
            card = by_id.get(item_id(v["card"]["date"], v["card"]["key"]))
        elif verdict == "new":
            if any(loanwords.loan_entry(x) for x in (e.get("arabic"), e.get("latin")) if x):
                counts["loanword"] += 1                      # WS-15: never asked
                verdict = "loanword"
            elif v.get("dup_of"):
                card = by_id.get(item_id(e["date"], "taught:" + _tkey(v["dup_of"])))
            else:
                card = next((x for x in list(by_id.values()) if x.get("source") != "glue" and same_meaning(e, x)), None)
                if card is None:
                    iid = item_id(e["date"], "taught:" + _tkey(e.get("arabic"), e.get("latin")))
                    k = _tap_of(iid, taps, prev)
                    if not (in_doc(e, doc) and not k):       # in her Doc and never answered: nothing to ask
                        line, typed = _taught_line(turns_for(e["date"]), e)
                        t = e.get("t")
                        audio = (lesson_audio or (lambda dd: f"lessons/{dd}/audio/lesson.mp3"))(e["date"])
                        card = {"id": iid, "date": e["date"], "key": "taught:" + _tkey(e.get("arabic"), e.get("latin")),
                                "arabic": e.get("arabic"), "arabizi": e.get("latin"), "english": e.get("english"), "t": t,
                                "mmss": mmss(t) if t is not None else None, "line": line, "typed": typed, "source": "taught",
                                "reason": v.get("reason"), "also": [],
                                "clip": {"src": audio, "start": max(0.0, float(t) - 2.0), "end": float(t) + 8.0} if t is not None else None}
                        card["status"], card["answered_at"] = (KINDS[k[0]], k[1]) if k and k[0] in KINDS else ("open", None)
                        card["tap"] = k[0] if k and k[0] in KINDS else None
                        card["tap_token"] = (k[2] if len(k) > 2 else None) if card["tap"] else None
                        mk = word_marks.mark_for(card, marks)
                        card["medi_mark"] = mk.get("mark") if mk else None
                        card["hint"] = (mk.get("hint") or word_marks.HINT_OLD) if card["medi_mark"] == "old" else None
                        card["age"], card["age_by"] = word_marks.resolve(card["medi_mark"], card["tap"])
                        new_items.append(card); by_id[iid] = card
                        counts["new_cards"] += 1
                        card = dict(card, _fresh=True)
        if card is not None and not card.get("_fresh"):
            counts["linked"] += 1                            # one card per word: this lesson is cited on it too
            if card["date"] != e["date"] or card.get("t") != e.get("t"):
                by_id[card["id"]].setdefault("also", []).append({"date": e["date"], "mmss": row["mmss"]})
        if in_doc(e, doc) and (card is None or by_id.get(card["id"], card)["status"] == "open"):
            row["status"] = "in_doc"
        elif card is not None:
            row["status"], row["card"] = status_of(by_id.get(card["id"], card)), card["id"]
        elif verdict == "on_doc":
            row["status"] = "in_doc"
        elif verdict == "loanword":
            row["status"] = "in_doc" if in_doc(e, doc) else "loanword"
        else:
            row["status"] = "unjudged"
        if row["status"] == "in_doc":
            counts["in_doc"] += 1
        if row["status"] == "unjudged":
            counts["unjudged"] += 1
        row["status_label"] = TAUGHT_STATUS.get(row["status"], "Loan word: not asked (WS-15)")
        taught.setdefault(e["date"], []).append(row)
    return new_items, taught, counts


def taught_unjudged(date, repo=None):
    """AM-19, review_lesson step 7d: the lesson's taught words (lesson-types read) with no row in
    taught-words-verdicts.json that are not plainly in the Doc - the by-meaning reader judges them."""
    import lesson_type_read as LTR
    repo = repo or REPO
    r, _ = LTR.load(date, repo)
    if not r:
        return []
    vp = os.path.join(repo, "data", "lesson-work", "taught-words-verdicts.json")
    have = {_tkey(v.get("arabic"), v.get("latin")) for v in (json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else [])
            if v.get("date") == date}
    wp = os.path.join(repo, "docs", "data", "words.json")
    W = json.load(open(wp, encoding="utf-8")) if os.path.exists(wp) else {"items": []}
    out = []
    for x in (r.get("taught_words") or []) + (r.get("taught") or []):
        e = {"arabic": x.get("arabic"), "latin": x.get("latin")}
        if _tkey(e["arabic"], e["latin"]) not in have and not in_doc(e, W):
            out.append(x)
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
    if prev and (prev.get("paused") or {}).get("lists"):     # AM-28: cards an earlier build paused are still cards (statuses kept)
        import tutor_scope
        prev = {**prev, "items": tutor_scope.all_items(prev)}
    taps = None if a.offline else load_taps()
    if taps is None and os.environ.get("ANEES_STRICT") == "1" and not a.offline:
        print("FAILED: Amal's taps could not be read (ANEES_STRICT)"); return 1
    out = build(V, taps, prev, glue=True, taught=taught_entries())
    out["unjudged"] = unjudged(V)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import tutor_scope       # AM-28: open cards of lessons before TUTOR_FROM are paused (kept in the file's paused block)
    tutor_scope.scope_file(OUT, None if a.offline else tutor_scope.answered_keys())
    out = json.load(open(OUT, encoding="utf-8"))
    print("amal-new-words", out["counts"], "excluded", out["excluded"], "unjudged", out["unjudged"], "taught", out.get("taught_counts"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
