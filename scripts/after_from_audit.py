# -*- coding: utf-8 -*-
"""Amal's after-lesson questions, built from the same-day audit (2026-09-26, Medi: "questions to help tune the system").

The old builder (after_questions.py) needs understanding.json / words_labeled.json, which the current pipeline no longer
writes, so links stopped after 09-11. This one reads data/full-audit-2026-09-26.json: for ONE lesson it picks up to
MAX_Q rows the readers were least sure of (A rows with confidence low, then medium; never two inside 20 s), cuts the
clip (his line -> her reply) and writes the after.html payload. Her tap lands in amal_rules (source 'after') with the
row's audit_uid, and scripts/apply_amal_audit_rulings.py applies it: Right -> the row is dropped; Wrong word / Wrong
grammar -> the row is confirmed (confidence high); Not Medi -> dropped.

    python scripts/after_from_audit.py 2026-09-23            -> prints the after link (mints an amal_links row)
    python scripts/after_from_audit.py 2026-09-23 --dry-run  -> payload only, no DB row
"""
import argparse, datetime, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from full_audit_compare import sec  # noqa: E402
from build_amal_review import cut_clip  # noqa: E402
AUDIT = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
MAX_Q, MIN_Q, GAP = 5, 3, 20.0
RANK = {"low": 0, "medium": 1, "high": 2}


def questions(date):
    A = json.load(open(AUDIT, encoding="utf-8"))
    rows = [r for r in A["rows"] if r["date"] == date and r.get("kind") in ("grammar", "vocab-A") and r.get("mode", "speaking") == "speaking"
            and sec(r.get("t")) is not None and r.get("source") == "audit-2026-09-26"]
    rows.sort(key=lambda r: (RANK.get(r.get("confidence"), 1), 0 if r.get("kind") == "vocab-A" else 1, sec(r.get("t"))))
    out, taken = [], []
    for r in rows:
        t = sec(r["t"])
        if any(abs(t - x) < GAP for x in taken):
            continue
        taken.append(t)
        vocab = r["kind"] == "vocab-A"
        ask = ("Did the student mean this word?" if vocab and r.get("tier") == 0 else "Did the student get this wrong here?")   # PG-33 (2026-10-07)
        why = ("the app read your reply as the word he was missing" if vocab and r.get("tier") == 0 else
               "the app thinks you corrected " + ("a word" if vocab else "grammar (rule " + str(r.get("bucket")) + ")") +
               ("; the readers were not sure" if r.get("confidence") == "low" else ""))
        q = {"t": round(t, 2), "ask": ask, "why": why, "kind": "audit", "audit_uid": r["uid"], "word_key": None,
             "arabizi": r.get("right_arabizi") or "", "arabic": (r.get("wrong") or "") + "  ->  " + (r.get("right") or ""),
             "english": r.get("english") or r.get("why") or "", "clip": cut_clip(date, t, sec(r.get("t_amal"))),
             "offset": 1.0, "buttons": ["Right", "Wrong word", "Wrong grammar"], "typed": True}
        out.append(q)
        if len(out) >= MAX_Q:
            break
    for i, q in enumerate(out, 1):
        q["n"] = i
        if q["clip"]:
            q["clip"] = q["clip"]                       # 'date/clips/gc-....mp3', served under lessons/
    return out


def payload(date):
    qs = questions(date)
    return {"lesson_date": date, "built": datetime.datetime.now().isoformat(timespec="seconds"), "source": "full-audit-2026-09-26",
            "questions": qs, "homework": [], "prompts": [], "pending": [],
            "meta": {"candidates": len(qs), "note": "questions come from the same-day audit rows the readers were least sure of; homework is not suggested by this builder"}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("date"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    p = payload(a.date)
    if len(p["questions"]) < 1:
        print("no questions for", a.date); return
    if a.dry_run:
        print(json.dumps({k: v for k, v in p.items() if k != "questions"}, ensure_ascii=False)); print(len(p["questions"]), "questions"); return
    import amal_links
    token, url = amal_links.create("after", a.date, p)
    print("AFTER", url)


if __name__ == "__main__":
    main()
