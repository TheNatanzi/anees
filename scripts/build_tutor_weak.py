# -*- coding: utf-8 -*-
"""PG-30 (Medi 2026-10-05: "the grammar and materials feel redundant. We should just have todo and completed. Instead lets
have grammar and vocab. For now lets add my worst performing 20 vocab words and 10 grammar lessons. for her"):
docs/data/tutor-weak.json = what Medi struggles with most, for Amal's Tutor page (Grammar tab = 10 rules, Vocab tab = 20
words), each with its numbers and the last real moments, so she can plan the next lessons. Read only; nothing scored here.

  words: the latest rating per Doc word from the lesson files (docs/data/lessons/<date>.json vocab_errors / vocab_correct
         `rating` = status, n, right, partial, wrong, pct), 2+ scored uses, lowest % first, 20
  rules: docs/data/grammar-console.json rules with 3+ uses and a %, lowest % first, 10 (not-taught rules left out)

    python scripts/build_tutor_weak.py
"""
import datetime, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE); DOCS = os.path.join(REPO, "docs")
N_WORDS, N_RULES, MIN_WORD_USES, MIN_RULE_USES = 20, 10, 2, 3
DECAY_DAYS = 21   # Medi 2026-10-05 "decaying (havent been said in a long time)": 3 weeks without a recorded use


def J(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def weak_words(lessons, words, n=N_WORDS, min_uses=MIN_WORD_USES):
    """lessons = [{date, vocab_errors, vocab_correct}] in date order; words = Doc words by key."""
    latest, moments = {}, {}
    for L in lessons:
        for e in (L.get("vocab_errors") or []) + (L.get("vocab_correct") or []):
            k, rt = e.get("sheet_key"), e.get("rating")
            if not k:
                continue
            if isinstance(rt, dict) and rt.get("n"):
                latest[k] = dict(rt, date=L["date"])
            if e.get("kind") in ("wrong", "asked", "partial"):
                moments.setdefault(k, []).append({"date": L["date"], "mmss": e.get("mmss") or "", "kind": e.get("kind"), "said": e.get("said_arabizi") or e.get("said") or "",
                                                  "fix": e.get("fix") or e.get("arabic") or "", "english": e.get("english") or "", "clip": e.get("clip")})
    out = []
    for k, rt in latest.items():
        if (rt.get("n") or 0) < min_uses:
            continue
        w = words.get(k) or {}
        out.append({"key": k, "arabizi": w.get("house_spelling") or w.get("arabizi") or k, "arabic": w.get("arabic") or "", "english": w.get("english") or "",
                    "status": rt.get("status"), "pct": rt.get("pct"), "n": rt.get("n"), "right": rt.get("right"), "partial": rt.get("partial"), "wrong": rt.get("wrong"),
                    "last_date": rt.get("date"), "moments": (moments.get(k) or [])[-3:][::-1]})
    out.sort(key=lambda x: ((x["pct"] if x["pct"] is not None else 101), -(x["n"] or 0), x["key"]))
    return out[:n]


def decay(lessons, words, days=DECAY_DAYS, as_of=None):
    """Medi 2026-10-05 "lets add a 5th page for decay. Words that are untested or decaying (havent been said in a long time)".
    decaying = Doc words with a rating whose LAST recorded use is `days`+ days before as_of (the newest lesson), longest ago
    first; untested = active Doc words with no recorded use in any lesson, Doc order."""
    as_of = as_of or max([L["date"] for L in lessons] or [datetime.date.today().isoformat()])
    last, moments = {}, {}
    for L in lessons:
        for e in (L.get("vocab_errors") or []) + (L.get("vocab_correct") or []):
            k = e.get("sheet_key")
            if not k:
                continue
            rt = e.get("rating") if isinstance(e.get("rating"), dict) else {}
            last[k] = dict(rt, date=L["date"])
            moments.setdefault(k, []).append({"date": L["date"], "mmss": e.get("mmss") or "", "kind": e.get("kind"), "said": e.get("said_arabizi") or e.get("said") or "", "fix": e.get("fix") or ""})
    d0 = datetime.date.fromisoformat(as_of)
    dec = []
    for k, rt in last.items():
        ago = (d0 - datetime.date.fromisoformat(rt["date"])).days
        if ago < days:
            continue
        w = words.get(k) or {}
        dec.append({"key": k, "arabizi": w.get("house_spelling") or w.get("arabizi") or k, "arabic": w.get("arabic") or "", "english": w.get("english") or "",
                    "status": rt.get("status"), "pct": rt.get("pct"), "n": rt.get("n"), "last_date": rt["date"], "days_ago": ago, "moments": (moments.get(k) or [])[-3:][::-1]})
    dec.sort(key=lambda x: (-x["days_ago"], x["key"]))
    unt = [{"key": k, "arabizi": w.get("house_spelling") or w.get("arabizi") or k, "arabic": w.get("arabic") or "", "english": w.get("english") or "", "first_seen": w.get("first_seen") or ""}
           for k, w in words.items() if k not in last and w.get("active", True) is not False]
    return {"as_of": as_of, "days": days, "decaying": dec, "untested": unt}


def weak_rules(console, n=N_RULES, min_uses=MIN_RULE_USES):
    out = []
    for r in console.get("rules") or []:
        if r.get("not_taught") or r.get("pct") is None or (r.get("uses") or 0) < min_uses:
            continue
        ev = [e for e in (r.get("events") or []) if e.get("kind") in ("wrong", "slip", "miss") or e.get("recast")]
        out.append({"id": r["id"], "family": r.get("family"), "name": r.get("name"), "one_line": r.get("one_line"), "status": r.get("status"), "pct": r.get("pct"),
                    "uses": r.get("uses"), "mistakes": r.get("mistakes"), "last_used": r.get("last_used"),
                    "moments": [{"date": e.get("date"), "mmss": e.get("mmss"), "said": e.get("said"), "recast": e.get("recast"), "clip": e.get("clip")} for e in (ev or r.get("events") or [])[-3:][::-1]]})
    out.sort(key=lambda x: (x["pct"], -(x["uses"] or 0), x["id"]))
    return out[:n]


def main():
    words = {w["key"]: w for w in (J(os.path.join(DOCS, "data", "words.json"), {}) or {}).get("items") or []}
    lessons = [J(p, {}) for p in sorted(glob.glob(os.path.join(DOCS, "data", "lessons", "20??-??-??.json")))]
    console = J(os.path.join(DOCS, "data", "grammar-console.json"), {}) or {}
    doc = {"built": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "rule": "PG-30 2026-10-05: Medi's weakest 20 Doc words (2+ scored uses, lowest % first) and 10 grammar rules (3+ uses, lowest % first), for Amal's Tutor page",
           "words": weak_words([L for L in lessons if L.get("date")], words), "rules": weak_rules(console),
           "decay": decay([L for L in lessons if L.get("date")], words)}
    p = os.path.join(DOCS, "data", "tutor-weak.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1); f.write("\n")
    print(f"tutor-weak: {len(doc['words'])} words, {len(doc['rules'])} rules, decay {len(doc['decay']['decaying'])} decaying + {len(doc['decay']['untested'])} untested -> {p}")


if __name__ == "__main__":
    main()
