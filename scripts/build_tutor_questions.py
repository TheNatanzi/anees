# -*- coding: utf-8 -*-
"""AM-34 - plain questions for the tutor on her Tutor page (Medi 2026-10-18: "Put in the tutor hub for her to answer",
about the 'be credited' / pleasantries note). Code never contacts her (AM-01): Medi sends her the hub link.

One list per file data/lesson-work/tutor-questions/<name>.json ({name, intro, questions: [{id, ask, note?, clip?}]}) ->
docs/data/amal-check-key-check-q-<name>.json, the AM-29 check-list module's format (docs/js/hub/check-task.js picks every
amal-check-key-check-*.json up through scripts/build_tutor_data.py). Each question is one card: its own ask (x.ask), an
optional note row and an optional lesson clip; the buttons are shared - Yes / No / It depends - and No and It depends open a
box for her words. Her taps: amal_rules source 'listen-check', kind 'tutor_question', word_key 'tutorq-<name>:<id>'.
They change nothing; Medi reads them before a rule is built.

    python scripts/build_tutor_questions.py            # every list
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "data", "lesson-work", "tutor-questions")
SECS_EACH = 40.0
QUESTION = {"field": "answer", "ask": "", "type": "options",
            "options": [{"v": "yes", "label": "Yes", "box": "Anything to add? (optional)"},
                        {"v": "no", "label": "No", "box": "What should it be instead?"},
                        {"v": "depends", "label": "It depends", "box": "What does it depend on?"}]}


def out_path(name):
    return os.path.join(REPO, "docs", "data", "amal-check-key-check-q-%s.json" % name)


def mmss(t):
    t = int(t)
    return "%d:%02d" % (t // 60, t % 60)


def card(q):
    x = {"id": q["id"], "date": (q.get("clip") or {}).get("date", ""), "mmss": "", "ask": q["ask"], "clips": [], "rows": []}
    c = q.get("clip")
    if c:
        win = "%s/audio/lesson.mp3#t=%.2f,%.2f" % (c["date"], max(0.0, c["t"] - 1), c["end"] + 0.8)
        x["clips"].append({"label": "The student, %s lesson at %s" % (c["date"][5:], mmss(c["t"])), "src": win, "fallback": win})
        x["mmss"] = mmss(c["t"])
    if q.get("note"):
        x["rows"].append({"label": "Note", "text": q["note"]})
    return x


def build(path):
    S = json.load(open(path, encoding="utf-8"))
    name = S["name"]
    items = [card(q) for q in S["questions"]]
    mins = max(1, round(len(items) * SECS_EACH / 60))
    D = {"set": "tutor-questions", "list": "q-" + name, "kind": "tutor_question", "prefix": "tutorq-" + name,
         "date": S.get("source", {}).get("date", ""), "title": "%d quick questions about %s (about %d minutes)" % (len(items), name, mins),
         "unit": "questions", "mins": mins, "intro": S["intro"], "what": S["intro"], "questions": [QUESTION], "n": len(items),
         "items": items, "rule": "AM-34"}
    old = json.load(open(out_path(name), encoding="utf-8")) if os.path.exists(out_path(name)) else {}
    for k in ("tutor_from", "paused"):
        if old.get(k):
            D[k] = old[k]
    with open(out_path(name), "w", encoding="utf-8", newline="\n") as f:
        json.dump(D, f, ensure_ascii=False, indent=1); f.write("\n")
    print("tutor questions %s: %d questions -> %s" % (name, len(items), out_path(name)))
    return D


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for p in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        build(p)
