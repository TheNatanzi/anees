# -*- coding: utf-8 -*-
"""AM-33 - the tutor rules on the moments where the student's answer key and the AI readers disagree (Medi 2026-10-17:
"Did you put the 9 questions in the tutor hub? Can you ask for clarification for these 6 from Amal and see if there's an
explanation that might help").

The 14 moments (one card per moment; 10-09 1:04:23 holds two key slips): the 9 strong disagreements of the overnight
reader test (data/lesson-work/tutor-dispute-check/moments.json: 6 the AI marks and the key does not, 3 the key marks and
the AI does not) + the 6 key slips no reader ever flagged. The card is the AM-29 key-check card (scripts/build_tutor_key_check.cards:
the student's clip, his line, her line before and after), BLIND to which side said what, with one question whose every
answer has a box asking WHY - the explanation is the point. Her taps: amal_rules source 'listen-check', kind
'dispute_check', word_key 'disputecheck:<item id>'. They change nothing; Medi reads them before any key change.

    python scripts/build_tutor_dispute_check.py          # writes docs/data/amal-check-key-check-disputes.json
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_tutor_key_check as BK

MOMENTS = os.path.join(REPO, "data", "lesson-work", "tutor-dispute-check", "moments.json")
OUT = os.path.join(REPO, "docs", "data", "amal-check-key-check-disputes.json")
KIND, PREFIX = "dispute_check", "disputecheck"
SECS_EACH = 45.0
QUESTION = {"field": "answer", "ask": "Listen to the student. Which is true? Please tell us why - your reason helps us most.", "type": "options",
            "options": [{"v": "right", "label": "The student said it right - no mistake here", "box": "Why is it right? (optional)"},
                        {"v": "mistake", "label": "The student made a mistake here", "box": "What is the mistake and how should it be said?"},
                        {"v": "words", "label": "The words are not what the student said", "box": "What did the student really say?"},
                        {"v": "cant_tell", "label": "Can't tell / it depends", "box": "What does it depend on? (optional)"}]}


def secs(mm):
    p = [int(x) for x in str(mm).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def chosen_for(date, moments, page):
    """Each moment -> the student's line holding it: within 15 s, the line holding his own words first, else the nearest."""
    turns = page.get("turns") or []
    out = []
    for m in moments:
        if m.get("at"):     # pinned to the line that holds the flagged words (AM-35 fix 2026-10-19)
            out.append({"t": float(m["at"][0]), "end": float(m["at"][1])}); continue
        t, said = m["time"], str(m.get("said") or "").split()
        s = secs(t)
        his = [u for u in turns if u.get("who") == "Medi" and abs(float(u.get("t") or 0) - s) <= 15]
        hit = [u for u in his if said and said[0] in str(u.get("text") or "")]
        his = hit or [u for u in his if abs(float(u.get("t") or 0) - s) <= 8]
        if not his:
            print("no student line near", date, t); continue
        u = min(his, key=lambda u: abs(float(u["t"]) - s))
        out.append({"t": float(u["t"]), "end": float(u.get("end") or float(u["t"]) + 4)})
    seen, uniq = set(), []
    for c in out:
        if c["t"] not in seen:
            seen.add(c["t"]); uniq.append(c)
    return uniq


def build(moments=MOMENTS, out=OUT, lst="key-check-disputes", date="2026-10-17", intro=None, what=None, rule="AM-33"):
    M = BK.J(moments)
    items = []
    for d in sorted({m["date"] for m in M["moments"]}):
        page = BK.J(os.path.join(REPO, "docs", "data", "lessons", d + ".json")) or {}
        ch = chosen_for(d, [m for m in M["moments"] if m["date"] == d], page)
        items += BK.cards(d, ch, page)
    items.sort(key=lambda x: (x["date"], x["t"]))
    for x in items:     # AM-35 (Medi: "the same format I asked for in the PDF"): what he said and the possible fix, each with English
        ms = [m for m in M["moments"] if m["date"] == x["date"] and m.get("said_en")]
        if ms:
            m = min(ms, key=lambda m: abs((float(m["at"][0]) if m.get("at") else secs(m["time"])) - float(x["t"])))
            x["rows"] = [{"label": "The student said", "ar": m["said"], "en": m["said_en"]},
                         {"label": "Maybe it should be", "ar": m.get("fix_ar") or "", "en": m.get("fix_en") or ""}] + list(x.get("rows") or [])
            if m.get("at"):     # the pinned window can span lines: play all of it, not a one-line clip
                x["clips"][0]["src"] = x["clips"][0]["fallback"]
    n = len(items); mins = max(1, round(n * SECS_EACH / 60))
    D = {"set": "tutor-dispute-check", "list": lst, "kind": KIND, "prefix": PREFIX, "date": date,
         "title": "%d moments we are unsure about (about %d minutes)" % (n, mins), "unit": "moments", "mins": mins,
         "intro": intro or "Short clips of the student from the Oct 8, 9 and 10 lessons. These are moments where we are not sure whether he "
                  "made a mistake. Listen, tap what is true, and if you can, write why - your reason helps us most.",
         "what": (what or "Short clips from Oct 8-10 where we are unsure if the student made a mistake. Tap what is true and say why. About %d minutes.") % mins,
         "questions": [QUESTION], "n": n, "items": items, "rule": rule}
    old = BK.J(out) or {}
    for k in ("tutor_from", "paused"):
        if old.get(k):
            D[k] = old[k]
    BK.W(out, D)
    print("tutor dispute check %s: %d moments, about %d min -> %s" % (lst, n, mins, out))
    return D


# AM-35 (Medi 2026-10-18: "Yes, build them and give to amal"): the same blind card for every moment an AI judge called a
# mistake that is not in answer key v3 (data/lesson-work/tutor-judge-check/moments.json, from the reader-90 judge test).
JUDGE_MOMENTS = os.path.join(REPO, "data", "lesson-work", "tutor-judge-check", "moments.json")
JUDGE_OUT = os.path.join(REPO, "docs", "data", "amal-check-key-check-judges.json")


def build_judges():
    return build(JUDGE_MOMENTS, JUDGE_OUT, "key-check-judges", "2026-10-18",
                 intro="More short clips from the Oct 8, 9 and 10 lessons. A computer check thinks the student may have made a "
                       "mistake in each one, but you have not checked it yet. Listen, tap what is true, and if you can, write why.",
                 what="More clips from Oct 8-10: did the student make a mistake? Tap what is true and say why. About %d minutes.",
                 rule="AM-35")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
    if os.path.exists(JUDGE_MOMENTS):
        build_judges()
