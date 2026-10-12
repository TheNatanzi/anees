# -*- coding: utf-8 -*-
"""English under every Arabic line of the lesson transcript (PG-40, Medi 2026-10-09: "Lets add all the english transaltions
below the arabic writing" -> "Whole sentence").

Every line with Arabic in it (Arabic script, or his Latin-letter Arabic that scripts/word_coverage.word_tokens reads) gets
one natural English sentence, made by Claude Haiku through the Claude command line (the same path as the AI readers,
logged in data/runs by scripts/track.py). Cached per line text in data/lesson-work/translations/<date>.json, so a line
is translated once and again only when its text changes (a second-listen or his own fix). Display only: nothing is
scored from it. scripts/build_lessons_page_data.py puts it on the turn as "en"; docs/js/lessons-page.js shows it small
under the line.

    python scripts/translate_lines.py 2026-10-08            # one lesson
    python scripts/translate_lines.py all                    # every published lesson (missing lines only)
ANEES_TRANSLATE=off = kill switch (tests and local builds that must not call the model).
"""
import concurrent.futures, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(REPO, "data", "lesson-work", "translations")
MODEL = os.environ.get("ANEES_TRANSLATE_MODEL", "claude-haiku-5-5")
CLAUDE = os.environ.get("ANEES_CLAUDE", "claude")
BATCH = 60
AR = re.compile(r"[ء-ي]")
PROMPT = """You translate lines from a one-to-one Levantine (Palestinian / Jordanian) Arabic lesson into English.
The student is learning; the tutor teaches. Each line below starts with who said it; never write that label in the English. Lines mix English, Arabic script and Arabic in Latin letters
(Arabizi: 2=hamza, 3=ain, 5=kh, 6=ta, 7=ha, 8=ghain, 9=sad). For each line give ONE short, natural English sentence of
what was said, ALL in English: when a line mixes Arabic and English, give the full sentence in English - translate every
Arabic and Arabizi word, never copy an Arabic letter into the English. When the line talks ABOUT an Arabic word ("آخر
المرة means..."), write that word in Latin letters in quotes ('aakher el-marra' means...). Keep the English parts as
they are. Translate what the student meant, even when his Arabic has a mistake. Fillers (um, آآآ) and cut-off words
are left out (a line that is only a filler gets ""). Return ONLY a JSON object {"<id>": "<english>", ...} with every id below and nothing else.

Lines:
"""


# Medi 2026-10-12 (task B3): the English never carries the speaker label the prompt gives ("Tutor: ...", "Student: ...") or a
# "(filler)" tag; such a cache row is dropped (load) and the line is translated again; a line that is only a filler keeps
# "" (no English shown, never asked again).
LABEL = re.compile(r"^\s*(?:Tutor|Student|Line|Teacher)\s*:\s*", re.I)
FILLER = re.compile(r"\s*\((?:filler|fillers)\)\s*", re.I)


def labelled(v):
    """True when an English still carries a speaker label or a (filler) tag."""
    return bool(LABEL.search(v or "") or FILLER.search(v or ""))


def clean(v):
    """The English without a speaker label or a (filler) tag ('' when nothing is left)."""
    v = LABEL.sub("", str(v or "").strip())
    v = FILLER.sub(" ", v).strip()
    return re.sub(r"\s{2,}", " ", v).strip(" ,")


def J(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def key(who, text):
    return hashlib.sha1(("%s|%s" % (who, (text or "").strip())).encode("utf-8")).hexdigest()[:12]


def wants(u):
    """A line that holds Arabic: Arabic script, or Latin letters the Arabizi reader reads as her words."""
    t = u.get("text") or ""
    if AR.search(t):
        return True
    if u.get("who") == "Medi" and re.search(r"[A-Za-z]", t):
        try:
            import word_coverage as WC
            return bool(WC.word_tokens(t))
        except Exception:  # noqa: BLE001
            return False
    return False


def path(date):
    return os.path.join(OUT, date + ".json")


def load(date):
    """The cache; an English that still holds Arabic letters is dropped (PG-40: Medi 2026-10-09 "if we are speaking arabic and
    english in the same sentence, just put the full english sentence for the translatuion"), so it is translated again."""
    return {k: v for k, v in ((J(path(date), {}) or {}).get("lines") or {}).items() if not AR.search(v or "") and not labelled(v)}


def attach(date, turns):
    """turns get "en" from the cache (the page builder's call). -> how many got one."""
    c = load(date)
    n = 0
    for u in turns:
        en = c.get(key(u.get("typed_by") or u.get("who"), u.get("text")))
        if en and wants(u):
            u["en"] = en
            n += 1
    return n


def _call(lines):
    """{id: english} for one batch through `claude -p` (Haiku); {} on any failure (the lines wait for the next run)."""
    import track
    body = "\n".join("%s\t%s: %s" % (i, who, text) for i, who, text in lines)
    prompt = PROMPT + body
    cmd = [CLAUDE, "-p", prompt, "--output-format", "json", "--model", MODEL]
    try:
        with track.run("translate_lines", None, kind="inference", provider="anthropic", request_model=MODEL,
                       params={"lines": len(lines), "prompt_arg_sha": track.sha256_text(prompt)}) as run:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=600)
            parsed = track.parse_claude_output(r.stdout)
            run.claude(parsed)
            txt = parsed.get("text") or ""
    except Exception as e:  # noqa: BLE001
        print("translate_lines: batch failed (%s)" % type(e).__name__)
        return {}
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}
    return {str(k): clean(v) for k, v in out.items() if isinstance(v, (str, int, float)) and not AR.search(str(v))}


def run(date, workers=4, log=print):
    if os.environ.get("ANEES_TRANSLATE") == "off":
        log("translate_lines: off (ANEES_TRANSLATE=off)")
        return 0
    d = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"), {}) or {}
    cache = load(date)
    todo, seen = [], set()
    for u in d.get("turns") or []:
        who = u.get("typed_by") or u.get("who")
        k = key(who, u.get("text"))
        if k in cache or k in seen or not wants(u):
            continue
        seen.add(k)
        todo.append((k, "Tutor" if who == "Amal" else "Student" if who == "Medi" else who, (u.get("text") or "").strip()))
    if not todo:
        log("translate_lines %s: nothing new" % date)
        return 0
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    got = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_call, batches):
            got.update(res)
    cache.update({k: v for k, v in got.items() if k in seen})
    os.makedirs(OUT, exist_ok=True)
    with open(path(date), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"about": "English of each Arabic line of the lesson transcript, by line text (scripts/translate_lines.py, "
                            "PG-40). Display only.", "model": MODEL, "lines": dict(sorted(cache.items()))}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    log("translate_lines %s: %d of %d new lines translated" % (date, len([k for k in got if k in seen]), len(todo)))
    return len(got)


# ------------------------------------------------------------------ the tutor's cards (PG-48)
# Medi 2026-10-10 "lets add the english translations for the transcript for Amal as well": every transcript line her Tutor
# page shows (the student's and her lines on her cards, the lines around a moment, the two versions of a listen check)
# gets the same one-sentence English. The lesson's own translation is used when the card quotes the line as the page has
# it; any other line (a joined sentence, a cut piece, an older wording) is translated here once, cached by its text.
TUTOR_CACHE = os.path.join(OUT, "tutor.json")
TUTOR_MAP = os.path.join(REPO, "docs", "data", "tutor-line-en.json")
LINE_KEYS = {"medi_said": "Student", "amal_said": "Tutor", "line": "Line", "text": "Line", "a": "Line", "b": "Line",
             "example": "Tutor"}


def tnorm(s):
    """The match key docs/js/hub/line-en.js uses too: punctuation and spaces folded to one space."""
    return re.sub(r"[\s.,?!،؟…\-—:;\"'()«»\[\]]+", " ", str(s or "")).strip()


STUDENT_KEYS = ("medi_said",)


def student_latin(text):
    """His line on her cards written in Latin letters ('akli khatibti / il mufaddal'): it gets English too (Medi 2026-10-12,
    task B1; the Lessons page does the same, PG-40). On her cards every such line is sent, not only the ones the Arabizi
    reader reads (it reads neither 'akli' nor 'khatibti'): an English line comes back as itself, and docs/js/hub/line-en.js
    never shows an English the card already holds. Only the student's lines of two words or more ('Okay.' is left alone)."""
    if not text or AR.search(text):
        return False
    return len(re.findall(r"[A-Za-z][A-Za-z']+", text)) >= 2


def tutor_lines(repo=REPO):
    """{norm text: (label, text)} - every transcript line on her Tutor data files that holds Arabic (Arabic script, or the
    student's Latin letters the Arabizi reader reads; the paused blocks left out). A card line object ({label, ar, az, en},
    docs/js/hub/check-task.js) without its English counts too."""
    out = {}

    def add(lab, o):
        n = tnorm(o)
        if n and n not in out:
            out[n] = (lab, o.strip())

    def walk(o, key=None):
        if isinstance(o, dict):
            if isinstance(o.get("ar"), str) and "label" in o and "az" in o and not o.get("en"):
                lab = "Student" if "student" in str(o.get("label")).lower() else "Tutor"
                if len(o["ar"]) <= 400 and (AR.search(o["ar"]) or (lab == "Student" and student_latin(o["ar"]))):
                    add(lab, o["ar"])
            for k, v in o.items():
                if k != "paused":
                    walk(v, k)
        elif isinstance(o, list):
            for x in o:
                walk(x, key)
        elif isinstance(o, str) and key in LINE_KEYS and len(o) <= 400 and (AR.search(o) or (key in STUDENT_KEYS and student_latin(o))):
            add(LINE_KEYS[key], o)
    for f in sorted(os.listdir(os.path.join(repo, "docs", "data"))):
        if f.startswith("amal-") and f.endswith(".json"):
            walk(J(os.path.join(repo, "docs", "data", f), {}) or {})
    return out


def tutor(repo=REPO, workers=4, log=print):
    """Translate her card lines that have no English yet (unless ANEES_TRANSLATE=off) and write docs/data/tutor-line-en.json."""
    lines = tutor_lines(repo)
    known = {}
    for f in os.listdir(os.path.join(repo, "docs", "data", "lessons")):
        if f.endswith(".json"):
            for u in (J(os.path.join(repo, "docs", "data", "lessons", f), {}) or {}).get("turns") or []:
                if u.get("en") and not AR.search(u["en"]) and not labelled(u["en"]):
                    for t in (u.get("text"), u.get("engine")):
                        if t:
                            known.setdefault(tnorm(t), u["en"])
    cache = {k: v for k, v in ((J(TUTOR_CACHE, {}) or {}).get("lines") or {}).items() if not AR.search(v or "") and not labelled(v)}
    ck = lambda n: hashlib.sha1(n.encode("utf-8")).hexdigest()[:12]
    todo = [(ck(n), lab, txt) for n, (lab, txt) in lines.items() if n not in known and ck(n) not in cache]
    if todo and os.environ.get("ANEES_TRANSLATE") != "off":
        got = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(_call, [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]):
                got.update(res)
        ids = {i for i, _, _ in todo}
        cache.update({k: v for k, v in got.items() if k in ids})
        os.makedirs(OUT, exist_ok=True)
        with open(TUTOR_CACHE, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"about": "English of the transcript lines on the tutor's cards that the lesson pages do not have as "
                                "they are (scripts/translate_lines.py tutor, PG-48). Display only.", "model": MODEL,
                       "lines": dict(sorted(cache.items()))}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        log("translate_lines tutor: %d of %d new lines translated" % (len([k for k in got if k in ids]), len(todo)))
    m = {}
    for n in lines:
        en = known.get(n) or cache.get(ck(n))
        if en:
            m[n] = en
    with open(TUTOR_MAP, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"about": "English under each transcript line on the Tutor page (PG-48): key = the line with punctuation "
                            "folded (docs/js/hub/line-en.js). Built by scripts/translate_lines.py tutor.",
                   "lines": dict(sorted(m.items()))}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    log("tutor-line-en: %d of %d card lines have English" % (len(m), len(lines)))
    return len(m), len(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args == ["tutor"]:
        tutor()
        args = []
    if args == ["all"]:
        args = sorted(f[:10] for f in os.listdir(os.path.join(REPO, "docs", "data", "lessons")) if f.endswith(".json"))
    for d in args:
        run(d)
