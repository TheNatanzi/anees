# -*- coding: utf-8 -*-
"""AM-36 - when the tutor's answer needs clarification (the clip was not enough, she is not sure, she asks something, or she
tapped "can't tell"), the card goes back to her with more of the recording BEFORE her answer is used for any grading
(Medi 2026-10-20: "make a rule when she's asking for more info like adding more recording send it back to her before
grading", then "Not just too short. Anything that needs clarification").

Reads her latest answer on every card of the blind checking lists (docs/data/amal-check-key-check-disputes.json, AM-33;
docs/data/amal-check-key-check-judges.json, AM-35). A card NEEDS MORE when she tapped "can't tell" or her note says the
clip was not enough or shows doubt or a question (MORE_RE). Each such card is re-built with the WHOLE EXCHANGE around his line from the lesson audio
(exchange(): back and forward while the lines follow each other with no long silence), every transcript line in it (both
speakers), and her own note from last time, into
docs/data/amal-check-key-check-more.json (list 'key-check-more', same question). Her answer there is stored under word_key
'disputecheck:<card id>-more'; if that answer needs clarification again, the card comes back once more ('-more2', reaching
further back, then '-more3').

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
MORE_RE = re.compile(r"(?i)too short|not enough|not sufficient|insufficient|need(s)? more|more (of the )?(audio|context|recording|clip)"
                     r"|longer|can'?t hear|cannot hear|clip (is|was) (cut|short)"
                     # Medi 2026-10-20: "Not just too short. Anything that needs clarification" - any doubt or question in her note
                     r"|not sure|unsure|i don'?t know|not clear|unclear|can'?t tell|cannot tell|hard to (tell|say|hear)|depends|i think|maybe|seems|\?"
                     # 2026-10-21: 'clip is still short', 'my note is still the same' (= the clip was still not enough)
                     r"|still (too )?short|note is still the same|still not (enough|sufficient)")
DECIDED_RE = re.compile(r"(?i)half (a )?point|partial (credit|point)")   # a scoring instruction ('maybe half a point'), not a question


def needs_more(payload):
    """Her answer needs clarification: she tapped "can't tell", or her note asks for more of the recording or shows any
    doubt or question (MORE_RE)."""
    p = payload or {}
    typed = str(p.get("typed") or "")
    if p.get("answer") != "cant_tell" and DECIDED_RE.search(typed) and not re.search(r"(?i)too short|not enough|not sufficient|still short", typed):
        return False                       # she decided and said how to score it (e.g. half a point): nothing to clarify
    return p.get("answer") == "cant_tell" or bool(MORE_RE.search(typed))


def latest(rows):
    """amal_rules rows (id order) -> {word_key: payload} of her latest answer per card ('undo' removes it)."""
    out = {}
    for r in rows:
        if r.get("kind") == "undo":
            out.pop(r.get("word_key"), None)
        else:
            out[r.get("word_key")] = r.get("payload") or {}
    return out


ROUNDS = 3                        # a card is asked at most this many more times; her last answer then counts as she gave it
GAP_S = 8.0                       # a silence this long between lines ends the exchange
BACK_MAX = (90.0, 150.0, 240.0)   # how far back the exchange may reach, per round (round 2 and 3 reach further)
AFTER_MAX = 45.0


def suffix(k):
    """Round k (1, 2, 3) -> the card id suffix: '-more', '-more2', '-more3'."""
    return SUFFIX if k == 1 else "%s%d" % (SUFFIX, k)


def final_answer(card_id, answers, prefix=DC.PREFIX):
    """The answer grading may use for one card: the first answer that needs no clarification, walking the re-ask rounds
    ('-more', '-more2', '-more3'); after the last round her answer counts as given. None = pending (no answer yet, or she
    asked for clarification and has not answered the next round)."""
    cur = answers.get("%s:%s" % (prefix, card_id))
    k = 0
    while cur is not None and needs_more(cur) and k < ROUNDS:
        k += 1
        cur = answers.get("%s:%s%s" % (prefix, card_id, suffix(k)))
    return cur


def exchange(page, t, end, k=1):
    """The whole back-and-forth around a line (2026-10-21: the 40 s window started in the middle of it - the task she set
    and the sentence he was building came before it): walk back while the lines follow each other with less than GAP_S of
    silence, at most BACK_MAX[k-1] s; forward the same way, at most AFTER_MAX s."""
    turns = sorted((u for u in page.get("turns") or [] if u.get("who") in ("Medi", "Amal") and str(u.get("text") or "").strip()),
                   key=lambda u: float(u.get("t") or 0))

    def e(u):
        return float(u.get("end") or float(u.get("t") or 0) + 2.0)
    a, b = float(t), float(end)
    back = BACK_MAX[min(k, len(BACK_MAX)) - 1]
    for u in reversed([u for u in turns if float(u["t"]) < a]):
        if a - e(u) > GAP_S or float(t) - float(u["t"]) > back:
            break
        a = float(u["t"])
    for u in [u for u in turns if float(u["t"]) > b]:
        if float(u["t"]) - b > GAP_S or e(u) - float(end) > AFTER_MAX:
            break
        b = max(b, e(u))
    return max(0.0, a - 1.0), b + 1.0


def widen(x, page, note, k=1):
    """The card again (round k): the whole exchange around the line from the lesson audio, every line in it, her note."""
    a, b = exchange(page, x["t"], x["end"], k)
    lesson = "%s/audio/lesson.mp3#t=%.2f,%.2f" % (x["date"], a, b)
    y = json.loads(json.dumps(x))
    y["id"] = x["id"] + suffix(k)
    y["round"] = k
    y["clips"] = [{"label": "The whole exchange (%s - %s, %d s)" % (BK.mmss(a), BK.mmss(b), round(b - a)), "src": lesson, "fallback": lesson}] + \
        list(x.get("clips") or [])
    rows = [r for r in (x.get("rows") or []) if not str(r.get("label", "")).startswith("You, just")]
    ctx = []
    for u in page.get("turns") or []:
        tu = float(u.get("t") or 0)
        if a <= tu <= b and u.get("who") in ("Medi", "Amal") and str(u.get("text") or "").strip():
            ctx.append({"label": "%s · %s" % ("The student" if u["who"] == "Medi" else "You", BK.mmss(tu)), "ar": u["text"],
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
            cur = ans.get("%s:%s" % (DC.PREFIX, x["id"]))
            for k in range(1, ROUNDS + 1):        # round k exists when the answer before it asked for clarification
                if not needs_more(cur):
                    break
                pages.setdefault(x["date"], BK.J(os.path.join(REPO, "docs", "data", "lessons", x["date"] + ".json")) or {})
                items.append(widen(x, pages[x["date"]], str(cur.get("typed") or "").strip(), k))
                cur = ans.get("%s:%s%s" % (DC.PREFIX, x["id"], suffix(k)))
    items.sort(key=lambda x: (x["date"], x["t"]))
    left = [x for x in items if ("%s:%s" % (DC.PREFIX, x["id"])) not in ans]
    n = len(items)
    mins = max(1, round(n * 60 / 60))
    D = {"set": "tutor-more-check", "list": LIST, "kind": DC.KIND, "prefix": DC.PREFIX, "date": "2026-10-20",
         "title": "%d moments to look at again, with the whole exchange (about %d minutes)" % (n, mins), "unit": "moments", "mins": mins,
         "intro": "Last time you were not sure about these moments, or said the clip was not enough. Each one now plays the whole "
                  "exchange from the lesson, from where it starts to where it ends, with every line said in it and your note. Your "
                  "earlier answer is not used until you answer again.",
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
