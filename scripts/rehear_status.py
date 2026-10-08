# -*- coding: utf-8 -*-
"""The "second listen" mark on every lesson (rule PG-27). No network, no paid call.

Medi 2026-10-04, after choosing the Gemini re-hear by Batch (PR-18): "just make sure to mark that its bending still on
the lessons" (pending). Until a lesson's lines are really re-heard by Gemini and the changes reviewed, its pages say so.

    python scripts/rehear_status.py build    # add every newly published lesson as pending; stamp the lesson pages
    python scripts/rehear_status.py check    # exit 1 when a published lesson has no row / a bad status / an unmarked page
    python scripts/rehear_status.py show

Source (hand-edited when a lesson moves on; `build` never changes an existing row):
    data/lesson-work/rehear-status.json   {"lessons": {"<date>": {"status", "since", "note"}}}
Statuses: pending (not re-heard) -> submitted (sent to Gemini, no answers yet) -> proposed (answers back, nothing
applied) -> applied (the changes 2 of 3 AI runs agreed on are in the transcript; no person checked them) or
applied-limited (a lesson with no separate microphone track: only alphabet-only changes went in).

Where it shows:
    the Lessons list   docs/data/lessons.json rows carry "rehear" (scripts/build_lessons_page_data.py calls chip());
                       docs/js/lessons-page.js draws the chip on the row and the sentence in the opened row
    each lesson page   docs/lessons/<date>.html gets one marked block right under its title (stamp_pages)
"""
import datetime, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join("data", "lesson-work", "rehear-status.json")
EXPLAIN = ("The second listen is a second AI (Gemini) re-hearing each of your lines from your own microphone, with the lesson around it, 3 times. "
           "A lesson is pending until that has been run on it; until then the transcript is ElevenLabs only. A change goes in only when 2 of the 3 "
           "runs agree on it - an AI agreement, not a person's check. The tutor's lines are not changed.")
# status -> (the chip's words, the one-line explanation). Each sentence says no more than the status proves.
STATUS = {
    "pending": ("Second listen: pending",
                "The second AI listen of your microphone (Gemini) has not been run for the transcript of this lesson yet. The transcript is ElevenLabs only."),
    "submitted": ("Second listen: sent, waiting",
                  "A second AI listen of your microphone (Gemini) was sent for this lesson and its answers are not back yet. The transcript is still ElevenLabs only."),
    "proposed": ("Second listen: changes to review",
                 "A second AI listen of your microphone (Gemini) was run on this lesson. Its changes are not reviewed and none is applied: the transcript is still ElevenLabs only."),
    # Codex final approval 2026-10-05 (required labels): "applied" never said who agreed - no person has checked the
    # changes, they are the ones 2 of the 3 AI runs agreed on; The tutor's lines are not changed. The per-lesson note
    # (scripts/rehear_apply.py status_row) carries the counts: lines changed, lines that wait.
    "applied": ("Second listen: applied",
                "A second AI listen of your microphone (Gemini, 3 runs) was run on this lesson. The changes agreed by 2 of 3 AI runs are in the transcript; "
                "no person has checked them. Your own corrections stayed and the tutor's lines are unchanged."),
    # a lesson with no separate microphone track: the listen heard both voices, so only alphabet-only changes went in
    "applied-limited": ("Second listen: limited (mixed recording)",
                        "This lesson has no separate microphone track for you, so the second AI listen (Gemini, 3 runs) heard a mixed recording with both voices. "
                        "Only alphabet-only changes were applied (the same words written in the other alphabet), agreed by 2 of 3 AI runs; no person has checked them. "
                        "Word changes wait for a check. The tutor's lines are unchanged."),
}
APPLIED = ("applied", "applied-limited")       # the statuses whose Gemini rows are in the overlay file
START, END = "<!--rehear:start-->", "<!--rehear:end-->"
BLOCK_RE = re.compile(re.escape(START) + ".*?" + re.escape(END), re.S)
# the lesson pages carry their own small stylesheet (not the Sabz shell), so the block styles itself: currentColor
# follows the page's light / dark text colour.
CHIP_CSS = "display:inline-block;font-size:13px;line-height:1.4;padding:2px 10px;border:1px dashed currentColor;border-radius:20px;opacity:.8;cursor:pointer"
TIP_CSS = "font-size:14px;line-height:1.5;opacity:.85;margin:6px 0 0"


def today():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def published(root=REPO):
    d = os.path.join(root, "docs", "lessons")
    return sorted(f[:-5] for f in os.listdir(d) if re.fullmatch(r"20\d\d-\d\d-\d\d\.html", f)) if os.path.isdir(d) else []


def load(root=REPO):
    p = os.path.join(root, SRC)
    if not os.path.exists(p):
        return {"lessons": {}}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(doc, root=REPO):
    p = os.path.join(root, SRC)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    doc = {"about": "Per lesson: has the second AI listen (Gemini re-hear of Medi's own microphone, rule TR-22 / PR-18) been run and applied? "
                    "Written by scripts/rehear_status.py build (new lessons join as pending; existing rows are never changed by code). Rule PG-27.",
           "explain": EXPLAIN, "statuses": {k: {"label": v[0], "tip": v[1]} for k, v in STATUS.items()},
           "lessons": {d: doc["lessons"][d] for d in sorted(doc["lessons"])}}
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return doc


def chip(date, doc=None, root=REPO):
    """What the pages show for one lesson: {"status", "since", "label", "tip"[, "note"]}. A lesson with no row, or a
    row with a status nobody defined, is pending (never more than is known)."""
    row = ((doc or load(root)).get("lessons") or {}).get(date) or {}
    st = row.get("status") if row.get("status") in STATUS else "pending"
    out = {"status": st, "since": row.get("since"), "label": STATUS[st][0], "tip": STATUS[st][1]}
    if row.get("note"):
        out["note"] = row["note"]
    return out


def block(c):
    """The marked block of a lesson page: a quiet chip; tapping it opens the one-line explanation (no script needed)."""
    tip = c["tip"] + ((" " + c["note"]) if c.get("note") else "")
    return ('%s<details class="rehear" data-rehear="%s" style="margin:10px 0"><summary title="%s" style="%s">%s</summary>'
            '<div style="%s">%s</div></details>%s') % (START, c["status"], html.escape(tip, quote=True), CHIP_CSS, html.escape(c["label"]), TIP_CSS, html.escape(tip), END)


def stamp(page, c):
    """The page's HTML with the block in place: replaced where it already is, else put right after the title."""
    b = block(c)
    if BLOCK_RE.search(page):
        return BLOCK_RE.sub(lambda m: b, page, count=1)
    k = page.find("</h1>")
    if k < 0:
        return page
    return page[:k + 5] + b + page[k + 5:]


def stamp_pages(doc=None, root=REPO):
    """Every published lesson page carries its lesson's block. Returns the dates whose page changed."""
    doc = doc or load(root)
    changed = []
    for d in published(root):
        p = os.path.join(root, "docs", "lessons", d + ".html")
        with open(p, encoding="utf-8", newline="") as f:
            old = f.read()
        new = stamp(old, chip(d, doc))
        if new != old:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            changed.append(d)
    return changed


def build(root=REPO, pages=True):
    """Every published lesson has a row (a new one joins as pending, dated today); an existing row is never touched.
    Returns (dates added, dates whose page was stamped)."""
    doc = load(root)
    doc.setdefault("lessons", {})
    added = [d for d in published(root) if d not in doc["lessons"]]
    for d in added:
        doc["lessons"][d] = {"status": "pending", "since": today(), "note": ""}
    before = None
    p = os.path.join(root, SRC)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            before = f.read()
    want = {"about": None, "explain": EXPLAIN, "statuses": {k: {"label": v[0], "tip": v[1]} for k, v in STATUS.items()}}
    if added or before is None or any(json.loads(before).get(k) != v for k, v in want.items() if v is not None):
        doc = save(doc, root)
    return added, (stamp_pages(doc, root) if pages else [])


def check(root=REPO):
    """Problems, one line each (empty = OK)."""
    doc, bad = load(root), []
    rows = doc.get("lessons") or {}
    for d in published(root):
        r = rows.get(d)
        if not r:
            bad.append("%s: no row in %s (run: python scripts/rehear_status.py build)" % (d, SRC.replace(os.sep, "/")))
            continue
        if r.get("status") not in STATUS:
            bad.append("%s: status %r is not one of %s" % (d, r.get("status"), " / ".join(STATUS)))
            continue
        with open(os.path.join(root, "docs", "lessons", d + ".html"), encoding="utf-8") as f:
            page = f.read()
        if block(chip(d, doc)) not in page:
            bad.append("%s: the lesson page does not carry its mark (%s)" % (d, STATUS[r["status"]][0]))
    return bad


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "build":
        added, stamped = build()
        print("rehear status: %d lessons, %d added as pending%s, %d pages stamped" % (len(load()["lessons"]), len(added), (" (" + ", ".join(added) + ")") if added else "", len(stamped)))
    elif cmd == "check":
        problems = check()
        for x in problems:
            print(x)
        print("rehear status: " + ("OK - %d lessons marked" % len(published()) if not problems else "%d problem(s)" % len(problems)))
        sys.exit(1 if problems else 0)
    else:
        doc = load()
        for d in published():
            c = chip(d, doc)
            print(d, c["status"], c.get("since") or "-", "|", c["label"], ("| " + c["note"]) if c.get("note") else "")
