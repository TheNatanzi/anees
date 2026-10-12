# -*- coding: utf-8 -*-
"""AM-30 - the tutor checks the student's notes on a lesson before it is graded (Medi 2026-10-12: "wait I want amal to
look at my notes on 10-9 before grading and clearing it", then "go").

    python scripts/build_tutor_note_check.py               # build the card list(s) (default: every lesson in DATES)
    python scripts/build_tutor_note_check.py pull          # her answers -> data/lesson-work/review-grades/tutor-note-check-answers.json
    python scripts/build_tutor_note_check.py 2026-10-09    # one lesson
    python scripts/build_tutor_note_check.py status        # per lesson: notes, answered, held or not

One card per DISTINCT note the student wrote on the lesson's transcript (data/lesson-work/medi-corrections.json, the
mirror scripts/medi_corrections.py pull writes, plus his chat corrections): medi_corrections.effective() first, so an
undone or edited note collapses to the latest live one; then the rows of one note (the note row, the rows the parser
read out of it, its done marker) are grouped by line time + his raw words, and the same words written again on a line
within 10 s are one note. Kinds: every kind he writes (note, text, add, missing, not-use, not-slip, speaker, time, ...);
the fast-review trace rows (kind rule-answer, proposal review:fast / review:relisten) and undo rows are never a note.

Each card (docs/js/hub/check-task.js, the AM-29 module): the moment's clip (the lesson page's clip of the line, else the
lesson audio from 1 s before to 4 s after it), the line he wrote on (Arabizi first, the Arabic small after, the English
under - S1, PG-44, PG-48), the other speaker's line just before and after, then "The student's note" - his own words as a
quote, with the names on screen as PG-33 has them (Amal -> the tutor, Medi -> the student; his 'I' stays his) - and four
plain sentences (AM-23): 'The student is right' / 'The student is partly right' (a box: what is right) / 'The student is
wrong' (a box: why, optional) / 'Not sure'. Undo (AM-17), the note box (AM-27), '12 of 80 answered', and one To do row
'Check the student's notes on Oct 9 (about N min)'.

Her taps: amal_rules rows of her checking lists (source 'listen-check', kind 'note_check', word_key 'notecheck:<id>', her
review link's token; no migration). `pull` mirrors them read-only into data/. They change nothing: no page, no score, no
row of his. They HOLD the lesson: while the list has a card she has not answered, scripts/review_grades.py neither
freezes nor grades the lesson (status 'waiting for the tutor to check the student's notes'), and nothing in the code
clears or undoes his notes (the only code that writes his table, scripts/correction_parse.py, only appends). No AI call;
nothing is written to Supabase."""
import hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DATES = ["2026-10-09"]                 # Medi 2026-10-12: "look at my notes on 10-9 before grading and clearing it"
KIND, PREFIX, SOURCE = "note_check", "notecheck", "listen-check"
SECS_EACH = 20.0                       # listen, read his note, one tap
SAME_NOTE_S = 10.0                     # the same words written again on a line within 10 s = one note
CONTEXT_S = 30.0
QUOTE = "wait I want amal to look at my notes on 10-9 before grading and clearing it"
WAITING = "waiting for the tutor to check the student's notes"
NOT_NOTES = ("undo",)                  # never a note of his
TRACE = ("review:fast", "review:relisten")

QUESTION = {"field": "answer", "ask": "Listen, then read the student's note. Is the student right?", "type": "options",
            "options": [{"v": "right", "label": "The student is right"},
                        {"v": "partly", "label": "The student is partly right", "box": "What is right?"},
                        {"v": "wrong", "label": "The student is wrong", "box": "Why? (optional)"},
                        {"v": "not_sure", "label": "Not sure"}]}
ANSWERS = [o["v"] for o in QUESTION["options"]]


def J(p, d=None):
    if not p or not os.path.exists(p):
        return d
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


def list_name(date):
    return "note-check-" + date


def data_path(date, repo=REPO):
    return os.path.join(repo, "docs", "data", "amal-check-%s.json" % list_name(date))


def answers_path(repo=REPO):
    return os.path.join(repo, "data", "lesson-work", "review-grades", "tutor-note-check-answers.json")


def mmss(t):
    t = int(max(0, float(t or 0)))
    return "%d:%02d:%02d" % (t // 3600, t // 60 % 60, t % 60) if t >= 3600 else "%02d:%02d" % (t // 60, t % 60)


def pretty(d):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)$", str(d or ""))
    return ("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(m.group(2)) - 1] + " " + str(int(m.group(3)))) if m else str(d or "")


# ------------------------------------------------------------------ his notes
def _raw(r):
    p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
    return str(p.get("raw") or r.get("note") or "").strip()


def is_note(r):
    """A row of his that belongs to a note: not an undo, not a fast-review trace, with his words."""
    if not isinstance(r, dict) or r.get("kind") in NOT_NOTES:
        return False
    if r.get("kind") == "rule-answer" and (r.get("proposal") in TRACE or not _raw(r)):
        return False
    return bool(_raw(r)) and r.get("turn_t") is not None


def notes(date, rows=None):
    """[{t, end, who, raw, kinds, line, ids}] - the distinct live notes of one lesson, in time order."""
    import medi_corrections as MC
    rows = MC.all_rows() if rows is None else rows
    live = MC.effective([r for r in rows if isinstance(r, dict) and r.get("id")])
    groups = {}
    for r in live:
        if str(r.get("lesson_date")) != date or not is_note(r):
            continue
        t = round(float(r["turn_t"]), 2)
        groups.setdefault((t, _raw(r)), []).append(r)
    out = []
    for (t, raw), rs in sorted(groups.items()):
        same = next((n for n in out if n["raw"] == raw and abs(n["t"] - t) <= SAME_NOTE_S), None)
        if same:
            same["ids"] += [r["id"] for r in rs]
            same["kinds"] = sorted(set(same["kinds"]) | {r["kind"] for r in rs})
            continue
        p = next((r.get("payload") for r in rs if isinstance(r.get("payload"), dict) and r["payload"].get("turn_end") is not None), None) or {}
        line = next((r["payload"].get("line") for r in rs if isinstance(r.get("payload"), dict) and r["payload"].get("line")), None)
        out.append({"t": t, "end": round(float(p.get("turn_end") if p.get("turn_end") is not None else t), 2),
                    "who": next((r.get("turn_who") for r in rs if r.get("turn_who")), "Medi"), "raw": raw,
                    "kinds": sorted({r["kind"] for r in rs}), "line": line, "ids": [r["id"] for r in rs]})
    return out


def item_id(date, n):
    return "%s:t%d:%s" % (date, int(round(float(n["t"]) * 100)), hashlib.sha1(n["raw"].encode("utf-8")).hexdigest()[:6])


_NAMES = [(re.compile(r"\b[Aa]mal'?s\b"), "the tutor's"), (re.compile(r"\b[Aa]mal\b"), "the tutor"),
          (re.compile(r"\bMedi'?s\b"), "the student's"), (re.compile(r"\bMedi\b"), "the student")]


def screen_quote(raw):
    """His words as he wrote them, with the names on screen as PG-33 has them (his 'I' stays his)."""
    s = str(raw or "").strip()
    for rx, b in _NAMES:
        s = rx.sub(b, s)
    return s


# ------------------------------------------------------------------ the cards
def _line(turns, idx):
    text = " ".join(str(turns[i].get("text") or "").strip() for i in idx).strip()
    en = " ".join(str(turns[i].get("en") or "").strip() for i in idx if turns[i].get("en")).strip()
    return text, en or None


def _turns_at(turns, n):
    who = n["who"] if n["who"] in ("Medi", "Amal") else None
    idx = [i for i, u in enumerate(turns) if (who is None or u.get("who") == who) and n["t"] - 0.05 <= float(u.get("t") or 0) <= n["end"] + 0.05]
    if idx:
        return idx
    near = [(abs(float(u.get("t") or 0) - n["t"]), i) for i, u in enumerate(turns) if (who is None or u.get("who") == who) and str(u.get("text") or "").strip()]
    near = [x for x in near if x[0] <= 3.0]
    return [min(near)[1]] if near else []


def cards(date, found, page, render=None, en_map=None):
    """The card for each note (see the module doc). render(texts) -> Arabizi per text; en_map {norm line: English}."""
    import build_tutor_key_check as TK
    from translate_lines import tnorm
    render = render or TK._arabizi
    en_map = en_map or {}
    turns = page.get("turns") or []
    built, texts = [], []
    for n in found:
        idx = _turns_at(turns, n)
        if idx:
            text, en = _line(turns, idx)
            who = turns[idx[0]].get("who")
            t0, t1 = float(turns[idx[0]].get("t") or n["t"]), max(n["end"], float(turns[idx[-1]].get("t") or n["t"]))
        else:
            text, en, who, t0, t1 = (n.get("line") or "").strip(), None, n["who"], n["t"], n["end"]
        other = "Amal" if who == "Medi" else "Medi"
        lo = idx[0] if idx else next((i for i, u in enumerate(turns) if float(u.get("t") or 0) >= n["t"]), len(turns))
        hi = idx[-1] if idx else lo - 1
        before = next((i for i in range(lo - 1, -1, -1) if turns[i].get("who") == other and t0 - float(turns[i].get("t") or 0) <= CONTEXT_S
                       and str(turns[i].get("text") or "").strip()), None)
        after = next((i for i in range(hi + 1, len(turns)) if turns[i].get("who") == other and float(turns[i].get("t") or 0) - t1 <= CONTEXT_S
                      and str(turns[i].get("text") or "").strip()), None)
        win = "%s/audio/lesson.mp3#t=%.2f,%.2f" % (date, max(0.0, t0 - 1), t1 + 4)
        clip = TK._clip(page, t0, t1) if who == "Medi" else None
        me = who == "Medi"
        x = {"id": item_id(date, n), "date": date, "mmss": mmss(n["t"]), "t": n["t"], "end": n["end"],
             "clips": [{"label": "The moment", "src": clip or win, "fallback": win}],
             "line": {"label": ("The student" if me else "You") + " · " + mmss(t0), "ar": text, "en": en or en_map.get(tnorm(text))},
             "rows": []}
        texts.append(text)
        lab = "You" if me else "The student"
        for name, i in (("%s, just before" % lab, before), ("%s, just after" % lab, after)):
            if i is not None:
                tx, e = _line(turns, [i])
                x["rows"].append({"label": "%s · %s" % (name, mmss(turns[i]["t"])), "ar": tx, "en": e or en_map.get(tnorm(tx))})
                texts.append(tx)
        x["rows"].append({"label": "The student's note", "text": "The student wrote: «%s»" % screen_quote(n["raw"])})
        built.append(x)
    az = render(texts)
    k = 0
    for x in built:
        for part in [x["line"]] + [r for r in x["rows"] if "ar" in r]:
            a = az[k] if k < len(az) else None
            k += 1
            part["az"] = a if a and a.strip() and a.strip() != (part["ar"] or "").strip() else None
    return built


def doc(date, items):
    n = len(items)
    mins = max(1, round(n * SECS_EACH / 60))
    return {"set": "tutor-note-check", "list": list_name(date), "kind": KIND, "prefix": PREFIX, "date": date,
            "title": "Check the student's notes on %s (about %d min)" % (pretty(date), mins), "unit": "notes", "mins": mins,
            "intro": "The student listened to the %s lesson and wrote %d notes about what the transcript or the app got wrong. "
                     "For each one: play the moment, read his note, and tap whether he is right. One tap each; Undo is next to "
                     "every answer. The lesson is not graded until you have looked at them." % (pretty(date), n),
            "what": "%d notes the student wrote on the %s lesson, each with its moment to play and the lines around it. "
                    "Is he right? One tap each. About %d minutes." % (n, pretty(date), mins),
            "questions": [QUESTION], "n": n, "items": items}


def build(date, repo=REPO, rows=None, render=None, log=print):
    page = J(os.path.join(repo, "docs", "data", "lessons", date + ".json"))
    if not page:
        log("tutor note check %s: no lesson page - skipped" % date)
        return None
    found = notes(date, rows)
    en_map = (J(os.path.join(repo, "docs", "data", "tutor-line-en.json"), {}) or {}).get("lines") or {}
    D = doc(date, cards(date, found, page, render, en_map))
    old = J(data_path(date, repo)) or {}
    if old.get("tutor_from"):
        D["tutor_from"] = old["tutor_from"]              # tutor_scope.scope_all stamps it; kept so a rebuild is a no-op
    if old.get("paused"):
        D["paused"] = old["paused"]
    W(data_path(date, repo), D)
    log("tutor note check %s: %d notes of the student, about %d min" % (date, D["n"], D["mins"]))
    return D


def build_all(repo=REPO, rows=None, render=None, log=print):
    return [build(d, repo, rows, render, log) for d in DATES]


# ------------------------------------------------------------------ her answers (read-only) + the hold
def pull(path=None, fetch=None, log=print):
    """amal_rules source listen-check, word_key notecheck:* -> data/ (db.select leaves undone taps out, AM-17)."""
    path = path or answers_path()
    if fetch is None:
        import db
        fetch = lambda: db.select("amal_rules", {"select": "id,kind,word_key,payload,created_at", "source": "eq." + SOURCE,
                                                 "word_key": "like.%s:*" % PREFIX, "order": "id.asc"})
    rows = fetch()
    old = J(path) or {}
    if old.get("rows") == rows:
        log("tutor note check: %d answer rows, unchanged" % len(rows))
        return rows
    W(path, {"about": "AM-30: the tutor's answers on the student's notes (amal_rules source listen-check, word_key notecheck:*), "
                      "pulled read-only by scripts/build_tutor_note_check.py pull. Undone taps are left out (AM-17); the latest "
                      "tap per note wins. They change nothing; while a note is unanswered the lesson is not graded.",
             "pulled": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": rows})
    log("tutor note check: pulled %d answer rows" % len(rows))
    return rows


def her_answers(rows):
    """{word_key: answer} - her latest tap per note (an undo as the latest row = no answer)."""
    out = {}
    for r in sorted(rows or [], key=lambda r: (r.get("id") or 0, str(r.get("created_at") or ""))):
        k = r.get("word_key")
        if not k:
            continue
        a = (r.get("payload") or {}).get("answer")
        if r.get("kind") == "undo" or a not in ANSWERS:
            out.pop(k, None)
        else:
            out[k] = a
    return out


def status(date, repo=REPO, rows=None):
    """{total, answered, waiting} for a lesson with a note list, else None. waiting = a card she has not answered."""
    D = J(data_path(date, repo))
    if not D:
        return None
    items = D.get("items") or []
    if rows is None:
        rows = (J(answers_path(repo), {}) or {}).get("rows") or []
    hers = her_answers(rows)
    answered = sum(1 for x in items if (PREFIX + ":" + x["id"]) in hers)
    return {"total": len(items), "answered": answered, "waiting": answered < len(items)}


def waiting(date, repo=REPO, rows=None):
    """True while the tutor has a note of this lesson still to check: the lesson is neither frozen nor graded."""
    s = status(date, repo, rows)
    return bool(s and s["waiting"])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["pull"]:
        try:
            pull()
        except Exception as e:  # noqa: BLE001 - fail open: the hold reads the last mirror
            print("tutor note check: answers not pulled (%s)" % type(e).__name__)
        return 0
    if argv[:1] == ["status"]:
        for d in DATES:
            print(d, status(d))
        return 0
    for d in (argv or DATES):
        build(d)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
