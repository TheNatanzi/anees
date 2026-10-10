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
     "not_taught": [{"key": "mumtaz", "reason": "her praise word, not taught"}],   # LS-09: Tutor new words that are NOT taught
     "off_lesson": [{"from": "10:00", "to": "13:48", "who": "Medi", "what": "customer call (booking a rug pickup)"}],  # LS-10
     "read_by": "claude -p (review_lesson.py)" | "<agent>, by hand", "at": "<iso time>",
     "summary": {                                   # LS-13 (Medi 2026-10-05 "This is way to wordy. Please simplify it. We should be
                                                    # very clear about the exact new grammar rule with the accordian for examples and
                                                    # bulleted explanation"): what the Lessons page SHOWS instead of the why prose
       "headline": "Tool words before and after a noun: awal, aa5er, taani, 8eir, nafs, kul",   # one line, <= 120 chars, no times
       "rules": [{"title": "nafs always takes el-: nafs el-ishi",         # the exact rule, one line (her spelling, S1)
                  "pattern": "nafs + el- + noun",                         # optional: the formula
                  "bullets": ["nafs = the same", "the noun after it always has el-", "nafs el-ishi = the same thing"],   # 1-4 short lines
                  "examples": [{"t": "49:59", "line": "نفس الإشي - the same thing"}]}],   # 1-6 real moments (mm:ss + the words said)
       "also": ["Review of awal / taani from 10-01 (16:54-29:37)", "Warm-up talk 06:44-16:42: woke up late, travel, camping"]}}   # short lines
   summary is optional for old reads; a new read must have it (check fails without it since 2026-10-05).

LS-08 (Medi 2026-10-02 "there was a new word from the lesson yesterday... you didnt catch it it was like sheja3a or
something for "motivation". why didnt you catch this"): taught_words lists EVERY word Amal introduces or gives Medi - when
he asks "how do you say...", when he is stuck or forgot, or when she types "word = meaning" in the chat - even when Medi
repeats it right after. The 10-01 miss: mitshajje3 (06:36-06:52, typed "mitshajje3 = motivated") was on the Tutor
new-words list but not in taught_words; the hand reader had called 07:00-15:20 "off-lesson (a customer call)".
LS-09 cross_check(): every word on that lesson's Tutor new-words list (the reader's 'new' verdicts in
data/lesson-work/amal-new-words-verdicts.json + docs/data/amal-new-words.json) is in taught / taught_words, or in
not_taught with a reason.
LS-10 cross_check(): an off-lesson window says who and what with from/to times, and the check fails when Amal speaks
Arabic (2+ Arabic words) or types a chat line inside it - that is lesson, not off-lesson.

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
CLOCK_RE = re.compile(r"^(\d{1,2}:)?\d{1,2}:\d\d$")
OFF_RE = re.compile(r"off[- ]lesson", re.I)
AR_WORD = re.compile("[\u0621-\u064a]{2,}")
NEW_WORDS = "docs/data/amal-new-words.json"
VERDICTS = "data/lesson-work/amal-new-words-verdicts.json"


def secs(clock):
    """'06:52' / '1:02:59' -> seconds."""
    p = [int(x) for x in str(clock).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


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
    for k in ("not_taught", "off_lesson"):
        if k in d and not isinstance(d[k], list):
            bad.append(f"{k} must be a list")
    for x in d.get("not_taught") or []:          # LS-09: a Tutor new word that was not taught says why
        if not (isinstance(x, dict) and x.get("key") and len(str(x.get("reason") or "")) >= 10):
            bad.append(f"not_taught entry {x!r} needs key and a reason (10+ characters)")
    off = d.get("off_lesson") if isinstance(d.get("off_lesson"), list) else []
    for x in off:                                # LS-10: an off-lesson window cites who and what, with its times
        if not (isinstance(x, dict) and CLOCK_RE.match(str(x.get("from") or "")) and CLOCK_RE.match(str(x.get("to") or ""))
                and str(x.get("who") or "").strip() and len(str(x.get("what") or "").strip()) >= 5):
            bad.append(f"off_lesson entry {x!r} needs from, to (mm:ss), who and what")
        elif secs(x["to"]) <= secs(x["from"]):
            bad.append(f"off_lesson entry {x!r}: to is not after from")
    if OFF_RE.search(why) and not off:
        bad.append("why calls a stretch off-lesson but off_lesson is empty: say who, what, from and to (LS-10)")
    bad += summary_problems(d.get("summary"), required=str(d.get("at") or "") >= SUMMARY_SINCE)
    return bad


SUMMARY_SINCE = "2026-10-05T12:00"   # LS-13: reads from this time on must carry the structured summary


def summary_problems(s, required=False):
    """LS-13: the structured summary the Lessons page shows (headline, rules with bullets + examples, also). [] when fine."""
    if s is None:
        return ["summary missing: headline, rules (title, bullets, examples), also (LS-13)"] if required else []
    bad = []
    if not isinstance(s, dict):
        return ["summary must be an object (LS-13)"]
    h = str(s.get("headline") or "").strip()
    if not (10 <= len(h) <= 120) or TIME_RE.search(h):
        bad.append("summary.headline must be one plain line, 10-120 characters, no mm:ss times")
    rules = s.get("rules")
    if not isinstance(rules, list):
        bad.append("summary.rules must be a list (empty when no rule was taught)")
    for r in rules or []:
        if not isinstance(r, dict) or not (3 <= len(str(r.get("title") or "")) <= 140):
            bad.append(f"summary rule {r!r} needs a one-line title"); continue
        b = r.get("bullets")
        if not (isinstance(b, list) and 1 <= len(b) <= 4 and all(isinstance(x, str) and 3 <= len(x) <= 160 for x in b)):
            bad.append(f"summary rule {r.get('title')!r}: bullets = 1-4 short lines")
        ex = r.get("examples")
        if not (isinstance(ex, list) and 1 <= len(ex) <= 6 and all(isinstance(x, dict) and CLOCK_RE.match(str(x.get("t") or "")) and len(str(x.get("line") or "")) >= 3 for x in ex)):
            bad.append(f"summary rule {r.get('title')!r}: examples = 1-6 real moments with t (mm:ss) and line")
    also = s.get("also")
    if also is not None and not (isinstance(also, list) and all(isinstance(x, str) and len(x) <= 160 for x in also)):
        bad.append("summary.also must be a list of short lines")
    return bad


def _norm(w):
    return re.sub("[\u064b-\u0652\u0640]", "", str(w or "")).strip().lower()


def tutor_new_words(date, repo=None):
    """{key: {arabic, arabizi, english}}: the lesson's words on the Tutor new-words list (the reader's 'new' verdicts and
    the built Tutor items; glue words, which do not come from a lesson, are left out)."""
    repo = repo or REPO
    out = {}
    vp = os.path.join(repo, *VERDICTS.split("/"))
    if os.path.exists(vp):
        for v in json.load(open(vp, encoding="utf-8")):
            if v.get("date") == date and v.get("verdict") == "new" and not v.get("dup_of") and v.get("key"):
                out[v["key"]] = {"arabic": v.get("arabic"), "arabizi": v.get("arabizi"), "english": v.get("english")}
    np_ = os.path.join(repo, *NEW_WORDS.split("/"))
    if os.path.exists(np_):
        N = json.load(open(np_, encoding="utf-8"))
        for it in list(N.get("items") or []) + list(((N.get("paused") or {}).get("lists") or {}).get("items") or []):   # AM-28: paused cards too
            if it.get("date") == date and it.get("source") not in ("glue", "taught") and it.get("key"):   # AM-19: taught cards come FROM the read
                out.setdefault(it["key"], {"arabic": it.get("arabic"), "arabizi": it.get("arabizi"), "english": it.get("english")})
    return out


def _turns(date, repo):
    p = os.path.join(repo, "docs", "data", "lessons", date + ".json")
    return (json.load(open(p, encoding="utf-8")).get("turns") or []) if os.path.exists(p) else []


def cross_check(date, repo=None, read=None):
    """LS-09 + LS-10 for one lesson's read: [] when it agrees with the Tutor list and the transcript, else the problems."""
    repo = repo or REPO
    if read is None:
        read, why = load(date, repo)
        if not read:
            return why
    bad, have = [], set()
    for x in (read.get("taught_words") or []) + (read.get("taught") or []):
        for f in ("latin", "arabic", "key"):
            for part in re.split(r"\s*/\s*", str(x.get(f) or "")):
                if part:
                    have.add(_norm(part))
    skip = {_norm(x.get("key")) for x in read.get("not_taught") or [] if isinstance(x, dict)}
    for key, w in sorted(tutor_new_words(date, repo).items()):
        forms = {_norm(key), _norm(w.get("arabic")), _norm(w.get("arabizi"))} - {""}
        if not (forms & have) and not (forms & skip):
            bad.append(f"LS-09: {key} ({w.get('arabic') or ''} = {w.get('english') or ''}) is on the Tutor new-words list "
                       f"for {date} but not in taught_words (or in not_taught with a reason)")
    turns = _turns(date, repo)
    for x in read.get("off_lesson") or []:
        try:
            lo, hi = secs(x["from"]), secs(x["to"])
        except Exception:
            continue
        hits = [t for t in turns if lo <= float(t.get("t") or 0) <= hi and (
            t.get("who") == "chat" or (t.get("who") == "Amal" and len(AR_WORD.findall(str(t.get("text") or ""))) >= 2))]
        if hits:
            h = hits[0]
            bad.append(f"LS-10: off-lesson {x['from']}-{x['to']} ({x.get('what')}) has Amal teaching inside it: "
                       f"{int(h['t'] // 60):02d}:{int(h['t'] % 60):02d} {h.get('who')}: {str(h.get('text'))[:60]!r}"
                       + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""))
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
            f"this lesson (latin only as SHE typed it, else null; arabic; english; t), [] when none. LS-08: list EVERY word Amal "
            f"introduces or gives him - when he asks 'how do you say...', when he is stuck or forgot a word, or when she types "
            f"'word = meaning' in the chat (CHAT Amal lines) - even when he repeats it right after. Real miss: 10-01 06:36-06:52 "
            f"he reached for 'motivated', said \u0645\u0634\u062c\u0639, and she typed 'mitshajje3 = motivated' -> taught_words "
            f"mitshajje3 at 06:52. Leave out only words he used himself before she gave them. LS-10: a stretch you call "
            f"off-lesson goes in off_lesson [{{from, to, who, what}}] (e.g. who Medi, what 'customer call'), only where Amal "
            f"neither speaks Arabic nor types; a stretch where her voice is just missing from the transcript is NOT off-lesson "
            f"(say 'her audio is missing' in why instead). LS-09: not_taught [{{key, reason}}] is for words on the Tutor "
            f"new-words list (data/lesson-work/amal-new-words-verdicts.json, verdict new, this date) that were not taught. "
            f"summary (LS-13, what the page shows instead of why): headline = ONE plain line (<= 120 chars, no times) saying what "
            f"was taught; rules = every grammar rule or word pattern Amal taught or drilled, each {{title (the exact rule in one "
            f"line, her spelling), pattern (optional formula), bullets (1-4 short plain lines explaining it), examples (1-6 real "
            f"moments {{t mm:ss, line = the words said, Arabic or her Arabizi + English}})}}; also = short lines for the rest "
            f"(review of earlier lessons, warm-up talk, off-lesson stretches) - no sentence over 160 chars. "
            f"read_by \"claude -p (review_lesson.py)\", at = now (ISO). Edit no other file. Then run "
            f"`python scripts/lesson_type_read.py check {date}` and fix the file until it prints OK (it also runs the LS-09 / "
            f"LS-10 cross-check). "
            f"Reply with one line: type, review_mode, taught n, taught_words n.")


def reconcile_prompt(date, issues, repo=None):
    """review_lesson.py step 7e: the Tutor new-words list is built after the type read (step 7d), so a word on it that the
    type read missed goes back to the reader with the cross-check's own lines."""
    repo = repo or REPO
    return (f"Repo: {repo}. Read the docstring of scripts/lesson_type_read.py. {REL_DIR}/{date}.json fails the LS-09 / LS-10 "
            f"cross-check:\n- " + "\n- ".join(issues) + f"\nRe-read data/lesson-work/full-audit/{date}.txt around each time. "
            f"For each Tutor word: if Amal gave or introduced it (LS-08), add it to taught_words with its time (latin as she "
            f"typed it); if not, add {{key, reason}} to not_taught. For an off-lesson window with Amal teaching inside, shrink "
            f"or drop it and fix why. Edit only that file, then run `python scripts/lesson_type_read.py check {date}` until OK. "
            f"Reply with one line.")


def check(dates, repo=None, cross=True):
    bad = {}
    for d in dates:
        r, why = load(d, repo)
        if not r:
            bad[d] = why
        elif cross:
            x = cross_check(d, repo, r)
            if x:
                bad[d] = x
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
