# -*- coding: utf-8 -*-
"""AM-28: which lessons the tutor's portal asks about (Medi 2026-10-10: "For now, I know we've only done 10, 8, and 10-9.
Let's put a pause on everything before that until we can get the process honed down a little bit, and then we'll go
back and clean everything up").

TUTOR_FROM is the ONE line to change. Lift the pause = set it to an earlier date (or "") and rebuild
(python scripts/build_tutor_data.py re-scopes every file below; nothing has to be re-made).

What "paused" means:
  * an OPEN question about a lesson before TUTOR_FROM is not shown on the Tutor page: it moves from the file's shown
    list (items / patterns / new_words) to the same file's "paused" block, unchanged - never deleted;
  * an item she already answered stays where it was (her Completed / Done history is hers, AM-17 Undo still works);
  * an item with no lesson date (verb forms, grammar notes, materials, uploads, homework, the student's questions, the
    Grammar / Vocab / Decay tabs) is not lesson-specific and keeps showing;
  * a slip pattern is dated by its NEWEST example: a pattern that also happened on/after TUTOR_FROM keeps showing;
  * the hourly job makes no new question for a lesson before TUTOR_FROM: no after-lesson link (scripts/amal_links.py
    create), no new-words read (review_lesson.py step 7d), no pattern read (step 7); the files that list her questions
    are scoped every time they are written.
Every scoped file carries "tutor_from" so docs/js/tutor.js reads the same date instead of hard-coding it.

    python scripts/tutor_scope.py            -> re-scope every Tutor data file now and print shown / paused per lesson
    python scripts/tutor_scope.py --report   -> print only (writes nothing)
"""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

TUTOR_FROM = "2026-10-08"      # AM-28: the Tutor page asks only about lessons on/after this date. Change this line to lift the pause.
WHY = ("AM-28 (Medi 2026-10-10): questions about lessons before " + TUTOR_FROM + " are paused until the process is honed; "
       "kept here unchanged, shown again when TUTOR_FROM moves back. Answered ones stay in her history.")


def in_scope(date, start=None):
    """True when a lesson date is on/after the start (TUTOR_FROM); no date = not lesson-specific = shown."""
    start = TUTOR_FROM if start is None else start
    d = str(date or "")[:10]
    return not d or not start or d >= start


def pattern_date(p):
    """A slip pattern (or a not-on-sheet word) is as new as its newest example / moment."""
    ds = [str(e.get("date") or "")[:10] for e in (p.get("examples") or p.get("moments") or []) if e.get("date")]
    return max(ds) if ds else (max(p.get("lessons") or [""]) or None)


def split(items, date_of=lambda x: x.get("date"), answered=lambda x: False, start=None):
    """-> (shown, paused). Paused = an open item of a lesson before the start; answered and undated items stay shown."""
    shown, paused = [], []
    for x in items or []:
        (shown if in_scope(date_of(x), start) or answered(x) else paused).append(x)
    return shown, paused


def all_items(doc, key="items"):
    """Every item of a scoped file, shown and paused (for readers that are not the Tutor page)."""
    doc = doc or {}
    return list(doc.get(key) or []) + list(((doc.get("paused") or {}).get("lists") or {}).get(key) or [])


def scope_doc(doc, key, date_of=lambda x: x.get("date"), answered=lambda x: False, start=None):
    """In place: re-merge what an earlier run paused, then split again (so lifting the pause brings items back).
    Returns the number paused in `key`."""
    start = TUTOR_FROM if start is None else start
    P = doc.get("paused") if isinstance(doc.get("paused"), dict) else {}
    lists = dict(P.get("lists") or {})
    seen, merged = set(), []
    for x in list(doc.get(key) or []) + list(lists.get(key) or []):
        i = x.get("id") if isinstance(x, dict) else None
        if i is not None and i in seen:
            continue
        seen.add(i)
        merged.append(x)
    shown, paused = split(merged, date_of, answered, start)
    doc[key] = shown
    if paused:
        lists[key] = paused
    else:
        lists.pop(key, None)
    doc["tutor_from"] = start
    if lists:
        doc["paused"] = {"why": WHY.replace(TUTOR_FROM, start) if start else WHY, "from": start, "lists": lists,
                         "counts": {k: len(v) for k, v in lists.items()}}
    else:
        doc.pop("paused", None)
    return len(paused)


# ---------------------------------------------------------------------------------------------------- her answers
def answered_keys(rows=None):
    """word_keys she answered on the Tutor page (amal_rules source review / listen-check; db.select leaves undone taps
    out, AM-17). None when the database cannot be read (the caller then keeps what an earlier run kept)."""
    if rows is None:
        try:
            import db
            rows = db.select("amal_rules", {"select": "word_key,kind", "source": "in.(review,listen-check)"})
        except Exception as e:  # noqa: BLE001 - offline: scope with what the files themselves know
            print("tutor_scope: her answers not read (%s); files scoped with what they record" % type(e).__name__)
            return None
        if not rows:                     # she has answered hundreds of items: an empty read is a failed read, not "nothing answered"
            print("tutor_scope: her answers read as empty; files scoped with what they record")
            return None
    return {str(r.get("word_key")) for r in rows if r.get("word_key") and r.get("kind") != "undo"}


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save(p, doc):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def _was_shown(doc, key):
    """Ids the file showed before this run (offline fallback: an item an earlier SCOPED run kept shown stays shown; a file
    a builder just wrote from scratch has no such record, so only what it says is answered stays)."""
    if "tutor_from" not in doc:
        return set()
    return {x.get("id") for x in doc.get(key) or [] if isinstance(x, dict)}


def scope_file(path, answers=None, start=None):
    """Scope one Tutor data file in place (by its name). Returns {list key: paused n} or None for an unknown file."""
    name = os.path.basename(path)
    if not os.path.exists(path):
        return None
    doc = _load(path)
    A = answers
    shown_before = {}

    def ans(key_of, key="items", extra=lambda x: False):
        if A is None:                      # offline: keep shown what was shown, plus what the file says is answered
            keep = shown_before.setdefault(key, _was_shown(doc, key))
            return lambda x: extra(x) or x.get("id") in keep
        return lambda x: extra(x) or key_of(x) in A
    out = {}
    if name == "amal-review.json":
        out["patterns"] = scope_doc(doc, "patterns", pattern_date, ans(lambda x: str(x.get("id")), "patterns"), start)
        out["new_words"] = scope_doc(doc, "new_words", pattern_date, ans(lambda x: str(x.get("id")), "new_words"), start)
        c = doc.setdefault("counts", {})
        c["patterns"] = len(doc["patterns"])
        c["vocab"] = sum(1 for p in doc["patterns"] if p.get("kind") == "vocab")
        c["grammar"] = sum(1 for p in doc["patterns"] if p.get("kind") == "grammar")
        c["new_words"] = len(doc["new_words"])
        c["paused_patterns"], c["paused_new_words"] = out["patterns"], out["new_words"]
    elif name == "amal-listen.json":
        out["items"] = scope_doc(doc, "items", answered=ans(lambda x: "listen:" + str(x.get("id"))), start=start)
        doc["n"] = len(doc["items"])
    elif name.startswith("amal-check-"):
        pre = doc.get("prefix") or ""
        out["items"] = scope_doc(doc, "items", answered=ans(lambda x: pre + ":" + str(x.get("id"))), start=start)
        doc["n"] = len(doc["items"])
    elif name in ("amal-verify.json", "amal-ledger.json"):
        out["items"] = scope_doc(doc, "items", answered=ans(lambda x: str(x.get("id"))), start=start)
        if name == "amal-verify.json":
            doc["count"] = len(doc["items"])
    elif name == "amal-new-words.json":
        out["items"] = scope_doc(doc, "items", answered=ans(lambda x: str(x.get("id")), extra=lambda x: x.get("status") not in (None, "open")), start=start)
        c = doc.setdefault("counts", {})
        c["open"] = sum(1 for x in doc["items"] if x.get("status") == "open")
        c["older_open"] = sum(1 for x in doc["items"] if x.get("status") == "open" and str(x.get("date") or "") < str(doc.get("older_before") or ""))
        c["paused_open"] = out["items"]
    else:
        return None
    _save(path, doc)
    return out


def check_files(repo=REPO):
    return sorted(glob.glob(os.path.join(repo, "docs", "data", "amal-check-*.json")))


def tutor_files(repo=REPO):
    d = os.path.join(repo, "docs", "data")
    return [os.path.join(d, n) for n in ("amal-review.json", "amal-listen.json", "amal-verify.json", "amal-ledger.json", "amal-new-words.json")] + check_files(repo)


def scope_all(repo=REPO, answers="read", start=None):
    """Scope every Tutor data file; fix the check-list index totals. -> {file: {list: paused n}}."""
    A = answered_keys() if answers == "read" else answers
    res = {}
    for p in tutor_files(repo):
        r = scope_file(p, A, start)
        if r is not None:
            res[os.path.basename(p)] = r
    idx = os.path.join(repo, "docs", "data", "amal-checks.json")
    if os.path.exists(idx):
        I = _load(idx)
        for L in I.get("lists") or []:
            p = os.path.join(repo, "docs", "data", "amal-check-%s.json" % L.get("list"))
            if os.path.exists(p):
                D = _load(p)
                L.setdefault("total_all", L.get("total"))
                L["total"] = len(D.get("items") or [])
                L["paused"] = len(all_items(D)) - L["total"]
        I["tutor_from"] = TUTOR_FROM if start is None else start
        _save(idx, I)
    return res


def link_paused(kind, lesson_date, start=None):
    """AM-28: the hourly job makes no new after / before link for a lesson before TUTOR_FROM."""
    return bool(lesson_date) and not in_scope(lesson_date, start)


# ---------------------------------------------------------------------------------------------------- report
def report(repo=REPO, answers="read"):
    """{type: {date: [open shown, open paused]}} - open = not answered (by the file or her live taps)."""
    A = answered_keys() if answers == "read" else answers
    A = A or set()
    d = os.path.join(repo, "docs", "data")
    out = {}

    def add(kind, date, shown):
        r = out.setdefault(kind, {}).setdefault(str(date or "no date")[:10], [0, 0])
        r[0 if shown else 1] += 1

    def walk(path, kind, key, date_of, key_of, done=lambda x: False):
        if not os.path.exists(path):
            return
        D = _load(path)
        shown_ids = {id(x) for x in D.get(key) or []}
        for x in all_items(D, key):
            if done(x) or key_of(x) in A:
                continue
            add(kind, date_of(x), id(x) in shown_ids)
    walk(os.path.join(d, "amal-review.json"), "slip patterns", "patterns", pattern_date, lambda x: str(x.get("id")))
    walk(os.path.join(d, "amal-review.json"), "not-on-sheet words", "new_words", pattern_date, lambda x: str(x.get("id")))
    walk(os.path.join(d, "amal-listen.json"), "listen check", "items", lambda x: x.get("date"), lambda x: "listen:" + str(x.get("id")))
    for p in check_files(repo):
        pre = _load(p).get("prefix") or ""
        walk(p, "check " + os.path.basename(p)[11:-5], "items", lambda x: x.get("date"), lambda x, pre=pre: pre + ":" + str(x.get("id")))
    walk(os.path.join(d, "amal-verify.json"), "moments to check", "items", lambda x: x.get("date"), lambda x: str(x.get("id")))
    walk(os.path.join(d, "amal-ledger.json"), "which word was wrong", "items", lambda x: x.get("date"), lambda x: str(x.get("id")))
    walk(os.path.join(d, "amal-new-words.json"), "new words", "items", lambda x: x.get("date"), lambda x: str(x.get("id")),
         done=lambda x: x.get("status") not in (None, "open"))
    T = os.path.join(d, "tutor.json")
    if os.path.exists(T):
        D = _load(T)
        for x in D.get("open") or []:
            if x.get("lesson_date"):
                add("lesson links", x["lesson_date"], True)
        for x in (D.get("paused") or {}).get("links") or []:
            add("lesson links", x.get("lesson_date"), False)
    return out


def print_report(rep):
    tot = {}
    for kind, by in sorted(rep.items()):
        s = sum(v[0] for v in by.values()); p = sum(v[1] for v in by.values())
        print(f"{kind:28} shown {s:4}  paused {p:4}   " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items())))
        for k, v in by.items():
            t = tot.setdefault(k, [0, 0]); t[0] += v[0]; t[1] += v[1]
    print("per lesson (open shown / open paused):", ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(tot.items())))


def main():
    if "--report" not in sys.argv:
        res = scope_all()
        print("tutor_scope: TUTOR_FROM", TUTOR_FROM, "| paused:", {k: v for k, v in res.items() if any(v.values())})
    print_report(report())


if __name__ == "__main__":
    main()
