# -*- coding: utf-8 -*-
"""The Student tab's data + the Flashcards sets Amal gives (Medi 2026-10-05: "Lets start whatever she uploads and the shaky
words from the previous lessons in flashcards"; "create a new tab 'student' below tutor"; grill Q2: storage = Supabase like
her taps, the hourly job rebuilds the pages).

Writes three files, all read by the pages with the live tables first and these as the offline copy:
  docs/data/uploads.json      the amal_uploads table as is (rows) + the effective sets (uploadSets, same rule as homework-core.js)
  docs/data/homework.json     homework_tasks / homework_replies / homework_verdicts as is + the homework score (Amal's
                              verdicts only: right 1, close 1/2, wrong 0; Q5) + her overrules (S6: each is a correction rule)
  docs/data/shaky-words.json  Q3: the LAST 2 lessons' wrong / partly wrong words and the words Medi asked for
                              (docs/data/lessons/<date>.json vocab_errors kind wrong / asked; sheet_key = the Doc key, else sh:<date>:<t>)

    python scripts/build_student_data.py            -> rewrites the three files (needs the service key; offline it keeps the old copies)
    python scripts/build_student_data.py --offline  -> only shaky-words.json (no database)
"""
import datetime, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE); DOCS = os.path.join(REPO, "docs")
sys.path.insert(0, HERE)
DATA = os.path.join(DOCS, "data")
LESSONS_DIR = os.path.join(DATA, "lessons")
SHAKY_LESSONS = 2
POINTS = {"right": 1.0, "close": 0.5, "wrong": 0.0}
TEXT_KINDS = ("translate", "create", "question")


def J(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def ts(r):
    return str((r or {}).get("created_at") or (r or {}).get("ts") or "")


def effective(rows):
    """Same rule as docs/js/homework-core.js effective(): an undo row (kind 'undo', undoes) hides its row; undo of an undo puts
    it back; a replayed queue (same id twice) is one row."""
    by = {}
    for r in rows or []:
        if isinstance(r, dict) and r.get("id") and r["id"] not in by:
            by[r["id"]] = r
    rows = sorted(by.values(), key=lambda r: (ts(r), str(r["id"])))
    undone = set()
    for r in rows:
        if r.get("kind") == "undo" and r.get("undoes"):
            if r["undoes"] in undone:
                undone.discard(r["undoes"])
            else:
                undone.add(r["undoes"])
    live_undo = {r["id"] for r in rows if r.get("kind") == "undo" and r["id"] not in undone}
    gone = {r["undoes"] for r in rows if r.get("kind") == "undo" and r["id"] in live_undo}
    return [r for r in rows if r.get("kind") != "undo" and r["id"] not in gone]


def upload_sets(rows):
    out = []
    for u in effective(rows):
        if u.get("kind") != "upload":
            continue
        cards = []
        for i, c in enumerate(u.get("rows") or []):
            if not isinstance(c, dict):
                continue
            az, ar, en = str(c.get("arabizi") or c.get("arabic") or ""), str(c.get("arabic") or "") if c.get("arabizi") else "", str(c.get("english") or "")
            if not (az or ar) or not (en or (az and ar)):
                continue
            cards.append({"key": f"u:{u['id']}:{i + 1}", "arabizi": az, "arabic": ar, "english": en, "plural": str(c.get("plural") or ""), "notes": str(c.get("notes") or "")})
        out.append({"id": "u:" + u["id"], "upload_id": u["id"], "title": u.get("title") or "From Amal", "keep": u.get("keep") or "temporary",
                    "source": u.get("source") or "file", "source_ref": u.get("source_ref") or "", "created_at": u.get("created_at") or "", "n": len(cards), "cards": cards})
    return sorted(out, key=lambda s: s["created_at"], reverse=True)


def task_state(task, replies, verdicts):
    reps = sorted([r for r in replies if r.get("task_id") == task["id"]], key=ts, reverse=True)
    reply = reps[0] if reps else None
    ai = reply.get("ai") if reply and isinstance(reply.get("ai"), dict) and reply["ai"].get("verdict") in POINTS else None
    verdict = None
    if reply:
        vs = sorted([v for v in effective(verdicts) if v.get("reply_id") == reply["id"] and v.get("kind") == "verdict" and v.get("verdict") in POINTS], key=ts, reverse=True)
        verdict = vs[0] if vs else None
    state = "todo" if not reply else "done" if verdict else "waiting" if reply.get("ai") else "checking"
    return {"state": state, "reply": reply, "ai": ai, "verdict": verdict, "final": verdict["verdict"] if verdict else None}


def score(tasks, replies, verdicts):
    text = [t for t in effective(tasks) if t.get("kind") in TEXT_KINDS]
    out = {"total": len(text), "done": 0, "right": 0, "close": 0, "wrong": 0, "points": 0.0, "pct": None, "waiting": 0, "checking": 0, "todo": 0, "agreed": 0, "overruled": 0}
    for t in text:
        s = task_state(t, replies, verdicts)
        out[s["state"]] += 1
        if s["state"] == "done":
            out[s["final"]] += 1
            out["points"] += POINTS[s["final"]]
            if s["verdict"].get("agrees") is True:
                out["agreed"] += 1
            if s["verdict"].get("agrees") is False:
                out["overruled"] += 1
    out["pct"] = round(1000 * out["points"] / out["done"]) / 10 if out["done"] else None
    return out


def overrules(tasks, replies, verdicts):
    """S6: every overrule is a correction rule - what the AI said, what Amal says, her note / fix (the checker reads these back)."""
    T = {t["id"]: t for t in effective(tasks)}
    R = {r["id"]: r for r in replies}
    out = []
    for v in effective(verdicts):
        if v.get("kind") != "verdict" or v.get("agrees") is not False:
            continue
        r = R.get(v.get("reply_id")); t = r and T.get(r.get("task_id"))
        if not r or not t:
            continue
        out.append({"id": v["id"], "date": v.get("created_at"), "kind": t.get("kind"), "prompt": t.get("prompt"), "direction": t.get("direction"), "words": t.get("words"),
                    "answer": r.get("answer"), "ai_said": (r.get("ai") or {}).get("verdict"), "amal_says": v.get("verdict"), "fix": v.get("fix"), "note": v.get("note"), "rule": "HW-overrule"})
    return out


def lesson_dates(d=LESSONS_DIR):
    return sorted(os.path.basename(p)[:10] for p in glob.glob(os.path.join(d, "20??-??-??.json")))


STOP = {"the", "a", "an", "to", "of", "is", "i", "you", "my", "we", "they", "he", "she", "it", "and", "or", "in", "on", "with", "this", "that", "for", "at", "be", "am", "are", "was"}


def meaning_tokens(s):
    return {t for t in re.split(r"[^a-z]+", str(s or "").lower()) if len(t) > 1 and t not in STOP}


def key_fits(row, doc):
    """Medi 2026-10-05 ('Miskey sounds like a mistake'): the lesson audit sometimes ties a slip to the WRONG Doc word (the slip
    'the last ten minutes' keyed to tesbah 'ala kheir = good night). The key is trusted only when the Doc word's meaning shares a
    word with the slip's meaning; otherwise the row is left out of the set and listed, never dealt as the wrong card."""
    w = doc.get(row.get("sheet_key") or row.get("word_key") or "")
    if not w:
        return True, None
    if meaning_tokens(w.get("english")) & meaning_tokens(row.get("english")):
        return True, None
    ar = lambda x: re.sub(r"[ً-ٟـ]", "", str(x or "")).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    if w.get("arabic") and ar(w["arabic"]) and ar(w["arabic"]) in ar((row.get("fix") or "") + " " + (row.get("arabic") or "")):
        return True, None      # same Arabic word (حدا = حدا): the key fits even when the English glosses differ
    return False, f"audit keyed it to the Doc word {w.get('arabizi')} = {w.get('english')}, which is not what the slip was about"


def doc_words(repo=REPO):
    d = J(os.path.join(repo, "docs", "data", "words.json"), {}) or {}
    return {w["key"]: w for w in d.get("items") or [] if w.get("key")}


def shaky_words(dates=None, lessons_dir=LESSONS_DIR, n=SHAKY_LESSONS, doc=None):
    """Q3 (Medi 2026-10-05 'Let's go back 2 lessons'): wrong / partly wrong words and words he asked for, from the last n lessons.
    A row whose Doc key does not fit its meaning (key_fits) goes to left_out with the reason - a mistake is never kept."""
    dates = (dates or lesson_dates(lessons_dir))[-n:]
    doc = doc_words() if doc is None else doc
    words, seen, left_out = [], set(), []
    for d in dates:
        L = J(os.path.join(lessons_dir, d + ".json"), {}) or {}
        for e in L.get("vocab_errors") or []:
            kind = e.get("kind")
            if kind not in ("wrong", "asked", "partial"):
                continue
            key = e.get("sheet_key") or e.get("word_key") or f"sh:{d}:{e.get('t')}"
            if key in seen:
                continue
            seen.add(key)
            arabic = str(e.get("fix") or e.get("arabic") or "").split(" (")[0].strip()
            ok, why = key_fits(e, doc)
            if not ok:
                left_out.append({"key": key, "date": d, "mmss": e.get("mmss") or "", "english": e.get("english") or "", "arabic": arabic, "reason": why})
                continue
            if not re.search(r"[؀-ۿ]", arabic) and not (e.get("arabizi") or e.get("sheet_key")):
                continue   # no Arabic and no spelling of hers: an English-only row from the audit is not a card
            words.append({"key": key, "arabizi": e.get("arabizi") or e.get("sheet_key") or "", "arabic": arabic, "english": e.get("english") or "", "kind": kind, "label": e.get("label") or "",
                          "date": d, "mmss": e.get("mmss") or "", "t": e.get("t"), "on_sheet": bool(e.get("on_sheet")), "said": e.get("said_arabizi") or e.get("said") or ""})
    return {"built": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "lessons": dates, "rule": "Q3 2026-10-05: last 2 lessons, wrong / partly wrong / asked for; a word leaves after two right card answers (homework-core.js shakyCards)", "n": len(words), "words": words, "left_out": left_out}


def pull():
    import db
    get = lambda t: db.select(t, {"select": "*", "order": "created_at.asc"})
    return get("amal_uploads"), get("homework_tasks"), get("homework_replies"), get("homework_verdicts")


def build(uploads, tasks, replies, verdicts, now=None):
    now = now or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    up = {"built": now, "rows": uploads, "sets": upload_sets(uploads)}
    sc = score(tasks, replies, verdicts)
    hw = {"built": now, "tasks": tasks, "replies": replies, "verdicts": verdicts, "score": sc, "overrules": overrules(tasks, replies, verdicts),
          "cards": [{"id": t["id"], "lesson_date": t.get("lesson_date"), "set_ref": t.get("set_ref"), "set_title": t.get("set_title"), "n_cards": t.get("n_cards"), "created_at": t.get("created_at")}
                    for t in effective(tasks) if t.get("kind") == "cards"],
          "note": "Homework has its own number (Q5): Amal's verdicts only, right 1 / close 1/2 / wrong 0 over the answers she checked. Lesson Words % / Grammar % never include it."}
    return up, hw


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    W(os.path.join(DATA, "shaky-words.json"), shaky_words())
    if "--offline" in argv:
        print("shaky-words.json written (offline)"); return 0
    try:
        uploads, tasks, replies, verdicts = pull()
    except Exception as e:   # keep the last copies: a page is never older than its source, but never blank either
        print(f"build_student_data: database not reachable ({type(e).__name__}: {str(e)[:120]}); kept the old uploads.json / homework.json")
        return 0
    up, hw = build(uploads, tasks, replies, verdicts)
    W(os.path.join(DATA, "uploads.json"), up)
    W(os.path.join(DATA, "homework.json"), hw)
    print(f"uploads: {len(up['sets'])} sets · homework: {hw['score']['total']} tasks, {hw['score']['done']} checked by Amal, {hw['score']['waiting']} waiting · shaky: {J(os.path.join(DATA, 'shaky-words.json'))['n']} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
