# -*- coding: utf-8 -*-
"""TR-27 - the tutor's ear decides a second-listen change that could hide a mistake (2026-10-07).

Council final approval 2026-10-05, condition 1: on the 27 lines where Amal had confirmed a mistake and the second listen
(TR-22, Gemini) changed the line so the mistake no longer showed, Amal listened: 12 of 27 "he said it wrong" (8 or more =
do not publish as is: widen the hold rule, take those lines back out). Medi 2026-10-07: "ok the questions are complete
open a chip and run the changes and the audit".

The widened hold. A Gemini change of one of Medi's lines is HELD (not applied, listed for the tutor) when
  (a) a word it puts on the line is a word the tutor says, or types in the chat, within the next 30 s and the engine
      did not have it (the change moves toward the teacher's form; before: 15 s, spoken only, released by the two-clip
      AI check - no AI check releases it any more), or
  (b) the line holds a moment the tutor confirmed as a mistake (her review / after-lesson / Tutor-page ruling).
Only her own listen releases a held line: "he said it right" / "yes, he said the word" / "the new line" = applied;
"he said it wrong" / "no" / "the old line" = the engine's text stays (taken out). "Not sure" / "something else" = still
held. Every held line not yet answered goes on ONE Tutor-portal list, "Listen: what did the student say? - part 2"
(scripts/build_amal_checks.py slip-check-2); the PG-27 chip says how many lines wait for her.

Her other answers (decision 2, AM-06: her answer wins):
  own-fix    Medi's own correction vs the AI runs: an AI run picked = a whole-line row by tutor-listen with "wins"
             (scripts/transcript_fixes.py) over his row; his row stays in the file, recorded as superseded.
  word-there a word credit the second listen no longer heard: yes = the credit stands; no = the credit is removed
             (data/lesson-work/ledger-tutor-listen.json, read by scripts/lesson_ledger.py; never a deleted row).
  one-or-two "the same mistake" = a duplicates.json pair (rule LS-16, her answer as the reason); "different" = both
             rows stand, listed in data/lesson-work/one-or-two-tutor.json so nothing asks again.

    python scripts/rehear_tutor.py pull         # amal_rules source listen-check -> data/lesson-work/rehear/tutor-answers.json (read-only pull)
    python scripts/rehear_tutor.py show         # her answers per list, as the keys read them
    python scripts/rehear_tutor.py own-fix      # the tutor-listen rows into transcript-fixes.json
    python scripts/rehear_tutor.py word-there   # -> data/lesson-work/ledger-tutor-listen.json
    python scripts/rehear_tutor.py one-or-two   # -> duplicates.json pairs + one-or-two-tutor.json
    python scripts/rehear_tutor.py report       # -> data/lesson-work/rehear/tutor-hold.json (every held / taken-out line with her words)
Nothing here calls a paid AI or writes to Supabase."""
import collections, glob, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

WORK = os.path.join(REPO, "data", "lesson-work")
REHEAR = os.path.join(WORK, "rehear")
ANSWERS_P = os.path.join(REHEAR, "tutor-answers.json")
HOLD_P = os.path.join(REHEAR, "tutor-hold.json")
LEDGER_TUTOR_P = os.path.join(WORK, "ledger-tutor-listen.json")
ONE_OR_TWO_P = os.path.join(WORK, "one-or-two-tutor.json")
DUPES_P = os.path.join(WORK, "full-audit", "duplicates.json")
FIXES_P = os.path.join(WORK, "transcript-fixes.json")
BEFORE_P = os.path.join(REHEAR, "rejudge", "before.json")
AUDIT_P = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
RULE = "TR-27"
BY = "tutor-listen"
AMAL_NEXT_S = 30.0
SOURCE = "listen-check"
QUOTE = "ok the questions are complete open a chip and run the changes and the audit"


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


def today():
    return time.strftime("%Y-%m-%d")


# ------------------------------------------------------------------ her answers
def pull():
    import db
    rows = db.select("amal_rules", {"select": "id,kind,word_key,payload,created_at,source", "source": f"eq.{SOURCE}", "order": "id.asc"})
    W(ANSWERS_P, {"about": "Amal's taps on her listening / checking lists (amal_rules source listen-check), pulled read-only by "
                           "scripts/rehear_tutor.py pull. Undone taps are already left out (scripts/db.py, AM-17); the latest tap per card wins.",
                  "pulled": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": rows})
    print("pulled %d rows" % len(rows))
    return rows


def answers(path=ANSWERS_P):
    """{word_key: (payload, created_at)} - the latest tap per card."""
    out = {}
    for r in sorted((J(path) or {}).get("rows") or [], key=lambda r: (r.get("id") or 0, str(r.get("created_at") or ""))):
        if r.get("kind") != "undo" and r.get("word_key"):
            out[r["word_key"]] = (r.get("payload") or {}, r.get("created_at"))
    return out


def _key_items(name):
    p = os.path.join(WORK, "amal-slip-check-key.json" if name == "slip-check" else f"amal-check-{name}-key.json")
    return (J(p) or {}).get("items") or []


def keys(ans=None):
    """Her answers keyed the way the hold reads them: by (date, line i), uid, event mark or pair id."""
    ans = answers() if ans is None else ans
    K = {"slip": {}, "wordsaid": {}, "oldnew": {}, "ownfix": collections.defaultdict(list), "wordthere": {}, "oneortwo": {}}
    for name in ("slip-check", "slip-check-2"):
        for it in _key_items(name):
            p, at = ans.get(it["word_key"], ({}, None))
            if p.get("mistake") in ("yes", "no", "not_sure"):
                K["slip"][(it["id"].split(":")[0], it["i"])] = {"uid": it.get("uid"), "mistake": p["mistake"], "choice": it["roles"].get(p.get("choice"), p.get("choice")), "at": at, "list": name}
    for name in ("word-said-1", "word-said-2"):
        for it in _key_items(name):
            p, at = ans.get(it["word_key"], ({}, None))
            if p.get("said") in ("yes", "no", "not_sure"):
                K["wordsaid"][(it["id"].split(":")[0], it["i"])] = {"said": p["said"], "word": it.get("word"), "at": at}
    for it in _key_items("old-new"):
        p, at = ans.get(it["word_key"], ({}, None))
        if p.get("choice"):
            K["oldnew"][(it["id"].split(":")[0], it["i"])] = {"choice": it["roles"].get(p["choice"], "other"), "at": at}
    for it in _key_items("own-fix"):
        p, at = ans.get(it["word_key"], ({}, None))
        if p.get("choice"):
            K["ownfix"][(it["id"].split(":")[0], it["i"])].append({"item": it["id"], "pick": it["roles"].get(p["choice"], "other"), "runs": it.get("runs"), "his": it.get("his"),
                                                                      "engine_wrote": it.get("engine_wrote"), "engine_line": it.get("engine_line"), "t": it["t"], "at": at})
    for it in _key_items("word-there"):
        p, at = ans.get(it["word_key"], ({}, None))
        if p.get("said") in ("yes", "no", "not_sure"):
            K["wordthere"][it["mark"]] = {"said": p["said"], "word": it.get("word"), "date": it["id"].split(":")[0], "event_id": it.get("event_id"), "at": at}
    for it in _key_items("one-or-two"):
        p, at = ans.get(it["word_key"], ({}, None))
        if p.get("same") in ("same", "different", "not_sure"):
            K["oneortwo"][it["id"]] = {"same": p["same"], "ids": it["ids"], "first_read": it.get("first_read"), "date": it["id"].split(":")[0], "slips": it.get("slips"), "at": at}
    return K


# ------------------------------------------------------------------ the hold
def _secs(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        parts = [float(x) for x in str(v).split(":")]
    except ValueError:
        return None
    return sum(p * 60 ** n for n, p in enumerate(reversed(parts)))


def confirmed_moments():
    """{date: [(seconds, uid)]} - every audit row the tutor confirmed as a mistake: the snapshot before the re-read
    (rehear/rejudge/before.json) and the live audit's rulings (data/full-audit-2026-09-26.json amal_ruling confirm)."""
    out = collections.defaultdict(list)
    seen = set()

    def add(d, t, uid):
        s = _secs(t)
        if s is not None and (d, uid) not in seen:
            seen.add((d, uid))
            out[d].append((s, uid))
    for d, x in ((J(BEFORE_P) or {}).get("lessons") or {}).items():
        for r in x.get("rows") or []:
            if r.get("amal") == "confirmed":
                add(d, r.get("t"), r.get("uid"))
    for r in (J(AUDIT_P) or {}).get("rows") or []:
        ar = r.get("amal_ruling") or {}
        if ar.get("kind") == "confirm" or r.get("amal") == "confirmed":
            add(r.get("date"), r.get("t"), r.get("uid"))
    return out


def her_lines(date, amal_all):
    """The tutor's spoken lines (the re-hear's own list) plus her typed chat lines from the lesson page data."""
    out = [{"t": a["t"], "end": a.get("end", a["t"]), "text": a.get("text") or ""} for a in amal_all or []]
    T = (J(os.path.join(REPO, "docs", "data", "lessons", date + ".json")) or {}).get("turns") or []
    out += [{"t": float(u["t"]), "end": float(u["t"]), "text": u.get("text") or "", "chat": True} for u in T if u.get("who") == "Amal" and u.get("chat")]
    return out


def words_next(line, hers, within=AMAL_NEXT_S):
    w = set()
    for a in hers:
        if line["t"] < a["t"] <= line["end"] + within:
            w |= set(BC.tokens(a["text"]))
    return w


def added_words(engine, heard):
    """The Arabic words of `heard` the engine's line did not have: not the same word, not the same word in the other
    alphabet (same consonant skeleton: basattee / انبسطتي), not the Arabizi reader's reading of it."""
    eng = BC.tokens(engine)
    old = set(eng) | set(BC.tokens(BC.latin_to_arabic(engine)))
    latin_skels = {BC.skel(e) for e in eng if not BC.is_ar(e) and BC.skel(e)}      # his Arabic in English letters: the same consonants = the same word
    return [w for w in BC.tokens(heard) if BC.is_ar(w) and w not in old and BC.skel(w) not in latin_skels]


def toward_tutor(line, engine, heard, hers, kind=None):
    """TR-27 (a): a WORD change (an alphabet-only change moves toward nobody) that puts the tutor's own word on his line."""
    if kind == "alphabet":
        return []
    return [w for w in added_words(engine, heard or "") if w in words_next(line, hers)]


def confirmed_on(date, line, confirmed, slack=1.0):
    return [uid for s, uid in confirmed.get(date, []) if line["t"] - slack <= s <= line.get("end", line["t"]) + slack]


def verdict(date, r, line, hers, confirmed, K):
    """One candidate change (a proposals row: i, engine, heard) -> {"status": apply|held|out, "why", "tutor": her answer}."""
    key = (date, r["i"])
    a = K["slip"].get(key)
    if a:
        if a["mistake"] == "yes":
            return {"status": "out", "why": "the tutor listened: he said it wrong (the second listen had hidden the mistake)", "tutor": a, "list": a.get("list", "slip-check")}
        if a["mistake"] == "no":
            return {"status": "apply", "why": "the tutor listened: he said it right", "tutor": a, "list": a.get("list", "slip-check")}
        return {"status": "held", "why": "the tutor listened and was not sure", "tutor": a, "list": a.get("list", "slip-check")}
    a = K["wordsaid"].get(key)
    if a:
        if a["said"] == "yes":
            return {"status": "apply", "why": "the tutor listened: he said the word himself", "tutor": a, "list": "word-said"}
        if a["said"] == "no":
            return {"status": "out", "why": "the tutor listened: he did not say the word", "tutor": a, "list": "word-said"}
        return {"status": "held", "why": "the tutor listened and was not sure", "tutor": a, "list": "word-said"}
    a = K["oldnew"].get(key)
    if a:
        if a["choice"] == "new":
            return {"status": "apply", "why": "the tutor listened: the new line is what he said", "tutor": a, "list": "old-new"}
        if a["choice"] == "old":
            return {"status": "out", "why": "the tutor listened: the old line is what he said", "tutor": a, "list": "old-new"}
        return {"status": "out", "why": "the tutor listened: neither line is what he said (the engine's text stays; listed for the student)", "tutor": a, "list": "old-new"}
    tw = toward_tutor(line, r["engine"], r.get("heard"), hers, r.get("kind"))
    cf = confirmed_on(date, line, confirmed)
    if tw or cf:
        why = []
        if tw:
            why.append("the change puts the tutor's own word on his line (%s, said or typed within %d s)" % (", ".join(tw), int(AMAL_NEXT_S)))
        if cf:
            why.append("the line holds a mistake the tutor confirmed (%s)" % ", ".join(cf))
        return {"status": "held", "why": "; ".join(why), "toward": tw, "confirmed": cf}
    return {"status": "apply", "why": None}


# ------------------------------------------------------------------ her other answers
def own_fix_rows(K=None):
    """The whole-line rows (by tutor-listen, wins) for the own-fix items where she picked an AI run."""
    K = K or keys()
    rows, listed = [], []
    for (date, i), items in sorted(K["ownfix"].items()):
        picks = [x for x in items if x["pick"].startswith("ai run")]
        if not picks:
            listed.append({"date": date, "i": i, "picks": [x["pick"] for x in items],
                           "why": "the tutor kept the student's own correction" if all(x["pick"] == "medi" for x in items)
                           else "the tutor: something else (neither his correction nor an AI run); the student's line stays"})
            continue
        runs = collections.Counter()
        for x in picks:
            for n in x["pick"][len("ai run "):].split(","):
                runs[int(n.strip())] += 1
        n = max(sorted(runs), key=lambda k: (runs[k], -k))
        text = picks[0]["runs"][n - 1]
        line = picks[0].get("engine_line") or ""
        rows.append({"date": date, "t": picks[0]["t"], "who": "Medi", "i": i, "line": line, "heard_line": text, "engine_wrote": line, "heard": text,
                     "spans": [{"engine_wrote": line, "heard": text}],
                     "rule": RULE, "by": BY, "wins": True, "on": today(),
                     "tutor": {"list": "own-fix", "items": [x["item"] for x in items], "picked": [x["pick"] for x in items], "his": [x["his"] for x in items],
                               "at": max(x["at"] or "" for x in items)},
                     "why": "the tutor listened to the student's own correction against the AI runs and picked AI run %d; her answer wins (AM-06, TR-27)" % n})
    return rows, listed


def write_own_fix(rows):
    """Replace this job's rows in transcript-fixes.json; nobody else's row is added or lost."""
    doc = J(FIXES_P)
    before = sum(1 for r in doc["rows"] if r.get("by") != BY)
    doc["rows"] = [r for r in doc["rows"] if r.get("by") != BY] + rows
    assert sum(1 for r in doc["rows"] if r.get("by") != BY) == before
    tmp = FIXES_P + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, FIXES_P)


def word_there_rulings(K=None):
    K = K or keys()
    out = []
    for mark, a in sorted(K["wordthere"].items()):
        out.append({"conflict": mark, "answer": a["said"], "by": "amal", "rule": RULE, "list": "word-there", "date": a["date"], "word": a["word"],
                    "event_id": a["event_id"], "at": a["at"],
                    "why": {"yes": "the tutor listened: the word is there - the credit stands", "no": "the tutor listened: the word is not there - the credit is removed",
                            "not_sure": "the tutor was not sure - the credit stays unscored"}[a["said"]]})
    return out


def write_word_there(rulings):
    W(LEDGER_TUTOR_P, {"about": "The tutor's answers on 'Check: is this word really there?' (TR-27, 2026-10-07): a word credit the second listen "
                                "no longer heard. yes = the credit stands; no = removed (not a mistake: no signal, S3); not_sure = unscored. "
                                "Read by scripts/lesson_ledger.py load_rulings; written by scripts/rehear_tutor.py word-there. Never edit by hand.",
                       "rulings": rulings})


def one_or_two(K=None):
    K = K or keys()
    D = J(DUPES_P) or {"pairs": []}
    have = {(p.get("keep"), p.get("drop")) for p in D["pairs"]} | {(p.get("drop"), p.get("keep")) for p in D["pairs"]}
    added, listed = [], []
    for pid, a in sorted(K["oneortwo"].items()):
        ids, fr = a["ids"], a.get("first_read") or [False, False]
        keep, drop = (ids[0], ids[1]) if (fr[0] or not fr[1]) else (ids[1], ids[0])
        if a["same"] == "same":
            if (keep, drop) not in have:
                row = {"date": a["date"], "keep": keep, "drop": drop, "rule": "LS-16", "by": BY, "at": a["at"],
                       "why": "the tutor's answer on 'Check: one mistake or two?' (2026-10-07): the same mistake, written twice - %s" % " || ".join(
                           "%s %s -> %s" % (s.get("mmss"), s.get("wrong"), s.get("right")) for s in a.get("slips") or [])}
                D["pairs"].append(row)
                added.append(row)
                have.add((keep, drop))
            listed.append({"pair": pid, "same": "same", "keep": keep, "drop": drop})
        else:
            listed.append({"pair": pid, "same": a["same"], "ids": ids,
                           "why": "the tutor: two different mistakes - both rows stand" if a["same"] == "different" else "the tutor was not sure - both rows stand"})
    if added:
        W(DUPES_P, D)
    W(ONE_OR_TWO_P, {"about": "The tutor's answers on 'Check: one mistake or two?' (TR-27, 2026-10-07). same = a duplicates.json pair (rule LS-16, "
                              "her answer as the reason); different / not sure = both rows stand and nothing asks again. Written by scripts/rehear_tutor.py one-or-two.",
                     "answers": listed})
    return added, listed


# ------------------------------------------------------------------ report
def report():
    """Every line the hold holds or took out, across the lessons' apply plans, with the tutor's words (S6 ruling rows)."""
    held, out_, applied = [], [], []
    for p in sorted(glob.glob(os.path.join(REHEAR, "*", "apply-plan.json"))):
        P = J(p)
        d = P.get("date")
        for x in P.get("held_tutor") or []:
            held.append(dict(x, date=d))
        for x in P.get("taken_out_by_tutor") or []:
            out_.append(dict(x, date=d))
        for x in P.get("applied_by_tutor") or []:
            applied.append(dict(x, date=d))
    doc = {"about": "TR-27 (2026-10-07): second-listen changes held for the tutor's ear, taken out on her word, or applied on her word. One row per line, "
                    "written by scripts/rehear_tutor.py report from each lesson's rehear/<date>/apply-plan.json. Medi: \"%s\"." % QUOTE,
           "rule": RULE, "made": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "counts": {"held_for_the_tutor": len(held), "taken_out_on_her_word": len(out_), "applied_on_her_word": len(applied),
                      "held_per_lesson": dict(collections.Counter(x["date"] for x in held))},
           "held": held, "taken_out": out_, "applied": applied}
    W(HOLD_P, doc)
    print("TR-27: held for the tutor %d (per lesson %s); taken out on her word %d; applied on her word %d" % (
        len(held), json.dumps(doc["counts"]["held_per_lesson"]), len(out_), len(applied)))
    return doc


def show():
    K = keys()
    c = collections.Counter(v["mistake"] for v in K["slip"].values())
    print("slip-check  %d answered: said it wrong %d, right %d, not sure %d" % (len(K["slip"]), c["yes"], c["no"], c["not_sure"]))
    c = collections.Counter(v["said"] for v in K["wordsaid"].values())
    print("word-said   %d answered: yes %d, no %d, not sure %d" % (len(K["wordsaid"]), c["yes"], c["no"], c["not_sure"]))
    c = collections.Counter(v["choice"] for v in K["oldnew"].values())
    print("old-new     %d answered: new %d, old %d, other %d" % (len(K["oldnew"]), c["new"], c["old"], c["other"]))
    rows, listed = own_fix_rows(K)
    print("own-fix     %d lines: %d get the AI run the tutor picked, %d keep the student's line" % (len(K["ownfix"]), len(rows), len(listed)))
    c = collections.Counter(v["said"] for v in K["wordthere"].values())
    print("word-there  %d answered: there %d, not there %d, not sure %d" % (len(K["wordthere"]), c["yes"], c["no"], c["not_sure"]))
    c = collections.Counter(v["same"] for v in K["oneortwo"].values())
    print("one-or-two  %d answered: same %d, different %d, not sure %d" % (len(K["oneortwo"]), c["same"], c["different"], c["not_sure"]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "pull":
        pull()
    elif cmd == "show":
        show()
    elif cmd == "own-fix":
        rows, listed = own_fix_rows()
        write_own_fix(rows)
        print("tutor-listen rows written: %d (%s); kept as is: %d" % (len(rows), ", ".join("%s %s" % (r["date"], r["i"]) for r in rows), len(listed)))
    elif cmd == "word-there":
        r = word_there_rulings()
        write_word_there(r)
        print("word-there rulings: %d (%s)" % (len(r), json.dumps(collections.Counter(x["answer"] for x in r))))
    elif cmd == "one-or-two":
        added, listed = one_or_two()
        print("one-or-two: %d pairs answered, %d new duplicates.json pairs" % (len(listed), len(added)))
    elif cmd == "report":
        report()
    else:
        raise SystemExit(__doc__)
