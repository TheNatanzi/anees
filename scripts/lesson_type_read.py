# -*- coding: utf-8 -*-
"""LS-01 (Medi 2026-10-02): each new lesson's TYPE and its TAUGHT words are read from context, the same day.

    python scripts/lesson_type_read.py check [date ...]   # exit 1 when a date has no valid type read (no date = every file)

Medi: "You need to tell from context when shes teaching me new words" / "This was clearly a grammar review for 'el' im
shocked you didnt detect that". Before this, the type and the taught verb pairs were hand-kept dicts in
scripts/build_lessons_page_data.py (LESSON_TYPES, TAUGHT) and every new lesson fell back to "free-speak, Not read yet".

One file per lesson: data/lesson-work/lesson-types/<date>.json, written by the same-day reader step in
scripts/review_lesson.py (a headless `claude -p` run with prompt() below) or by an agent reading the transcript by hand:

    {"date": "2026-10-01", "type": "review-grammar", "review_mode": "speaking",
     "why": "<one or two sentences that cite mm:ss times from the transcript>",
     "taught": [{"latin": "Ana ba5rab / Ana ba5arreb", "arabic": "...", "review": false}],     # verb pairs Amal taught
     "taught_words": [{"latin": "oola", "arabic": "...", "english": "first (feminine)", "t": "55:26"}],  # other words she introduced
     "read_by": "claude -p (review_lesson.py)" | "<agent>, by hand", "at": "<iso time>"}

build_lessons_page_data.py reads these files; its hand dicts stay as overrides (a date in LESSON_TYPES / TAUGHT wins).
A lesson with no valid read keeps the builder's "Not read yet" default, and the publish guard's lesson_type_read check
(required since 2026-10-02) blocks the push: the default is never shown as a reading.
taught_words are shown on the lesson page only; they are never fed to the word scorer (no score moves from them).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REL_DIR = "data/lesson-work/lesson-types"
TYPES = ("free-speak", "review-words", "new-words", "new-grammar", "review-grammar")
MODES = (None, "speaking", "listening", "both")
TIME_RE = re.compile(r"\b\d{1,2}:\d\d\b")


def path(date, repo=None):
    return os.path.join(repo or REPO, *REL_DIR.split("/"), date + ".json")


def problems(d, date):
    """[] when d is a valid read for this lesson, else what is wrong (a read that is not valid counts as not read)."""
    bad = []
    if not isinstance(d, dict):
        return ["not a JSON object"]
    if d.get("date") != date:
        bad.append(f"date {d.get('date')!r} is not {date}")
    if d.get("type") not in TYPES:
        bad.append(f"type {d.get('type')!r} is not one of {', '.join(TYPES)}")
    if d.get("review_mode") not in MODES:
        bad.append(f"review_mode {d.get('review_mode')!r} is not one of {MODES}")
    if str(d.get("type", "")).startswith("review-") and not d.get("review_mode"):
        bad.append("a review lesson needs review_mode (speaking / listening / both)")
    why = str(d.get("why") or "")
    if len(why) < 40 or not TIME_RE.search(why):
        bad.append("why must say what the lesson was and cite at least one mm:ss time from the transcript")
    if why.startswith("Not read yet"):
        bad.append("why is the builder's default, not a reading")
    for k in ("taught", "taught_words"):
        if not isinstance(d.get(k), list):
            bad.append(f"{k} must be a list (empty when nothing was taught)")
    for x in d.get("taught") or []:
        if not (isinstance(x, dict) and x.get("latin") and x.get("arabic") and isinstance(x.get("review"), bool)):
            bad.append(f"taught entry {x!r} needs latin, arabic, review (true/false)")
    for x in d.get("taught_words") or []:
        if not (isinstance(x, dict) and (x.get("latin") or x.get("arabic")) and x.get("t")):
            bad.append(f"taught_words entry {x!r} needs latin or arabic, and t (mm:ss)")
    return bad


def load(date, repo=None):
    """(read, problems): read is None when the file is missing or not valid."""
    p = path(date, repo)
    if not os.path.exists(p):
        return None, [f"no type read ({REL_DIR}/{date}.json missing)"]
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return None, [f"{REL_DIR}/{date}.json unreadable ({type(e).__name__})"]
    bad = problems(d, date)
    return (None if bad else d), bad


def load_all(repo=None):
    """{date: read} for every valid file."""
    d = os.path.join(repo or REPO, *REL_DIR.split("/"))
    out = {}
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if re.fullmatch(r"20\d\d-\d\d-\d\d\.json", f):
                r, _ = load(f[:-5], repo)
                if r:
                    out[f[:-5]] = r
    return out


def prompt(date, repo=None):
    """The same-day reader (review_lesson.py step 2b). Reads the whole transcript, writes ONE file."""
    repo = repo or REPO
    return (f"Repo: {repo}. Read the docstring of scripts/lesson_type_read.py and the 'type' and 'taught' definitions in "
            f"scripts/build_lessons_page_data.py (DEFINITIONS) and the LESSON_TYPES / TAUGHT examples there. Then read the WHOLE "
            f"transcript data/lesson-work/full-audit/{date}.txt in order (mm:ss = lesson clock; the lesson runs from Amal's first "
            f"word to her last; off-lesson talk does not count). Decide from CONTEXT what the lesson mostly was: free-speak "
            f"(conversation / role play), review-words (practising words already taught), new-words (Amal introducing vocabulary "
            f"or a new verb pair drilled in all tenses), new-grammar (Amal teaching a rule for the first time), review-grammar "
            f"(Amal drilling or testing rules already taught - e.g. a planned el- review). Listen for her own framing ('we're "
            f"repeating today', 'I'm not introducing anything new', 'this is new actually', 'we never said it before'). One main "
            f"type = the one with the most minutes; say in why when it is mixed. Write {REL_DIR}/{date}.json exactly in the shape "
            f"the docstring shows: why = one or two sentences with the minute ranges and at least two mm:ss quotes; taught = verb "
            f"pairs Amal taught or reviewed (latin in HER spelling from her chat lines or docs/data/words.json, arabic, review "
            f"true when first taught in an earlier lesson), [] when none; taught_words = other words she introduced as new in "
            f"this lesson (latin only as SHE typed it, else null; arabic; english; t), [] when none - never words Medi already "
            f"used himself. read_by \"claude -p (review_lesson.py)\", at = now (ISO). Edit no other file. Then run "
            f"`python scripts/lesson_type_read.py check {date}` and fix the file until it prints OK. "
            f"Reply with one line: type, review_mode, taught n, taught_words n.")


def check(dates, repo=None):
    bad = {}
    for d in dates:
        r, why = load(d, repo)
        if not r:
            bad[d] = why
    return bad


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] != "check":
        print(__doc__)
        return 2
    rd = os.path.join(REPO, *REL_DIR.split("/"))
    dates = a[1:] or sorted(f[:-5] for f in (os.listdir(rd) if os.path.isdir(rd) else []) if re.fullmatch(r"20\d\d-\d\d-\d\d\.json", f))
    bad = check(dates)
    for d, why in bad.items():
        print(f"{d}: " + "; ".join(why))
    if not bad:
        print(f"OK: {len(dates)} lesson(s) have a valid type read")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
