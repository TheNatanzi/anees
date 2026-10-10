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
The student (Medi) is learning; the tutor (Amal) teaches. Lines mix English, Arabic script and Arabic in Latin letters
(Arabizi: 2=hamza, 3=ain, 5=kh, 6=ta, 7=ha, 8=ghain, 9=sad). For each line give ONE short, natural English sentence of
what was said, ALL in English: when a line mixes Arabic and English, give the full sentence in English - translate every
Arabic and Arabizi word, never copy an Arabic letter into the English. When the line talks ABOUT an Arabic word ("آخر
المرة means..."), write that word in Latin letters in quotes ('aakher el-marra' means...). Keep the English parts as
they are. Translate what the student meant, even when his Arabic has a mistake. Fillers (um, آآآ) and cut-off words
are left out. Return ONLY a JSON object {"<id>": "<english>", ...} with every id below and nothing else.

Lines:
"""


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
    return {k: v for k, v in ((J(path(date), {}) or {}).get("lines") or {}).items() if not AR.search(v or "")}


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
    return {str(k): str(v).strip() for k, v in out.items() if isinstance(v, (str, int, float)) and str(v).strip() and not AR.search(str(v))}


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


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args == ["all"]:
        args = sorted(f[:10] for f in os.listdir(os.path.join(REPO, "docs", "data", "lessons")) if f.endswith(".json"))
    for d in args:
        run(d)
