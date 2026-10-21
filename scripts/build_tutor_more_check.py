# -*- coding: utf-8 -*-
"""AM-36 - when the tutor's answer needs clarification (the clip was not enough, she is not sure, she asks something, or she
tapped "can't tell"), the card goes back to her with more of the recording BEFORE her answer is used for any grading
(Medi 2026-10-20: "make a rule when she's asking for more info like adding more recording send it back to her before
grading", then "Not just too short. Anything that needs clarification").

Reads her latest answer on every card of the blind checking lists (docs/data/amal-check-key-check-disputes.json, AM-33;
docs/data/amal-check-key-check-judges.json, AM-35). A card NEEDS MORE when she tapped "can't tell" or her note says the
clip was not enough or shows doubt or a question (MORE_RE). Each such card is re-built with the lesson audio from WIDEN_BEFORE s before his line to
WIDEN_AFTER s after it, every transcript line in that window (both speakers), and her own note from last time, into
docs/data/amal-check-key-check-more.json (list 'key-check-more', same question). Her answer there is stored under word_key
'disputecheck:<card id>-more'.

Grading rule (final_answer): a card that needs more counts ONLY by its '-more' answer; until she gives it, the card is
pending and is left out of every key, score and grade. Nothing here changes a lesson page; no AI call.

    python scripts/build_tutor_more_check.py          # rebuild the list from her answers (the hourly job and the trigger run it)
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_tutor_dispute_check as DC  # noqa: E402
import build_tutor_key_check as BK  # noqa: E402

SOURCES = [os.path.join(REPO, "docs", "data", "amal-check-key-check-disputes.json"),
           os.path.join(REPO, "docs", "data", "amal-check-key-check-judges.json")]
OUT = os.path.join(REPO, "docs", "data", "amal-check-key-check-more.json")
LIST, SUFFIX = "key-check-more", "-more"
WIDEN_BEFORE, WIDEN_AFTER = 25.0, 15.0
MORE_RE = re.compile(r"(?i)too short|not enough|not sufficient|insufficient|need(s)? more|more (of the )?(audio|context|recording|clip)"
                     r"|longer|can'?t hear|cannot hear|clip (is|was) (cut|short)"
                     # Medi 2026-10-20: "Not just too short. Anything that needs clarification" - any doubt or question in her note
                     r"|not sure|unsure|i don'?t know|not clear|unclear|can'?t tell|cannot tell|hard to (tell|say|hear)|depends|i think|maybe|seems|\?")


def needs_more(payload):
    """Her answer needs clarification: she tapped "can't tell", or her note asks for more of the recording or shows any
    doubt or question (MORE_RE)."""
    p = payload or {}
    return p.get("answer") == "cant_tell" or bool(MORE_RE.search(str(p.get("typed") or "")))


def latest(rows):
    """amal_rules rows (id order) -> {word_key: payload} of her latest answer per card ('undo' removes it)."""
    out = {}
    for r in rows:
        if r.get("kind") == "undo":
            out.pop(r.get("word_key"), None)
        else:
            out[r.get("word_key")] = r.get("payload") or {}
    return out


def final_answer(card_id, answers, prefix=DC.PREFIX):
    """The answer grading may use for one card: its '-more' answer when the first one asked for more, else the first.
    None = pending (no answer yet, or more was asked for and not given)."""
    first = answers.get("%s:%s" % (prefix, card_id))
    if first is None:
        return None
    if needs_more(first):
        return answers.get("%s:%s%s" % (prefix, card_id, SUFFIX))
    return first


def widen(x, page, note):
    """The card again: the lesson audio around the line, every line in that window, and her note from last time."""
    a, b = max(0.0, float(x["t"]) - WIDEN_BEFORE), float(x["end"]) + WIDEN_AFTER
    lesson = "%s/audio/lesson.mp3#t=%.2f,%.2f" % (x["date"], a, b)
    y = json.loads(json.dumps(x))
    y["id"] = x["id"] + SUFFIX
    y["clips"] = [{"label": "The lesson around it (%d s)" % round(b - a), "src": lesson, "fallback": lesson}] + list(x.get("clips") or [])
    rows = [r for r in (x.get("rows") or []) if not str(r.get("label", "")).startswith("You, just")]
    ctx = []
    for u in page.get("turns") or []:
        t = float(u.get("t") or 0)
        if a <= t <= b and u.get("who") in ("Medi", "Amal") and str(u.get("text") or "").strip():
            ctx.append({"label": "%s · %s" % ("The student" if u["who"] == "Medi" else "You", BK.mmss(t)), "ar": u["text"],
                        "en": u.get("en")})
    y["rows"] = [{"label": "Your note last time", "ar": note or "(you tapped: can't tell)", "en": None}] + rows + ctx
    return y


def build(rows=None, out=OUT, log=print):
    if rows is None:
        import db
        rows = db.select("amal_rules", {"select": "id,kind,word_key,payload", "kind": "in.(%s,undo)" % DC.KIND, "order": "id.asc"}, retries=4)
    ans = latest(rows)
    items, pages = [], {}
    for src in SOURCES:
        D = BK.J(src) or {}
        for x in D.get("items") or []:
            first = ans.get("%s:%s" % (DC.PREFIX, x["id"]))
            if not needs_more(first):
                continue
            pages.setdefault(x["date"], BK.J(os.path.join(REPO, "docs", "data", "lessons", x["date"] + ".json")) or {})
            items.append(widen(x, pages[x["date"]], str(first.get("typed") or "").strip()))
    items.sort(key=lambda x: (x["date"], x["t"]))
    left = [x for x in items if ("%s:%s" % (DC.PREFIX, x["id"])) not in ans]
    n = len(items)
    mins = max(1, round(n * 60 / 60))
    D = {"set": "tutor-more-check", "list": LIST, "kind": DC.KIND, "prefix": DC.PREFIX, "date": "2026-10-20",
         "title": "%d moments to look at again, with more of the recording (about %d minutes)" % (n, mins), "unit": "moments", "mins": mins,
         "intro": "Last time you were not sure about these moments, or said the clip was not enough. Here each one plays again with "
                  "about 40 seconds of the lesson around it, the lines said in that time, and your note. Your earlier answer is not used "
                  "until you answer again.",
         "what": "Moments you were not sure about, now with more of the recording. About %d minutes." % mins,
         "questions": [DC.JUDGE_QUESTION], "n": n, "items": items, "rule": "AM-36"}
    old = BK.J(out) or {}
    for k in ("tutor_from", "paused"):
        if old.get(k):
            D[k] = old[k]
    if n or os.path.exists(out):
        BK.W(out, D)
    log("tutor more-check: %d moments need more (%d still unanswered) -> %s" % (n, len(left), out))
    return D


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
