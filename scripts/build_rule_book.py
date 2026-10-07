# -*- coding: utf-8 -*-
"""The rule book (rule PG-16, Medi 2026-10-02: "Lets keep a parrallel document of the rules that has it in an organized
fashion so I can read it and follow it. Please make sure the orginzation makes sense for a human to follow").

    python scripts/build_rule_book.py          # writes docs/data/rule-book.json (the page docs/rules.html) + RULE-BOOK.md
    python scripts/build_rule_book.py --check  # exit 1 when either file is out of date (the guard test does the same)

Nothing here is a second copy to keep up by hand: both files are built from rules/registry.json (every rule, with its
optional plain-words `plain` sentence and `topic`) and RULES.md (the titles of S1-S7). tests/test_rule_book.py fails the
publish guard when the published book differs from what this script builds now, and the hourly job rebuilds it.

Order = the life of a lesson (recording -> spelling -> words -> grammar -> Amal -> flashcards -> pages -> how the AI
works). Inside a group: Counts / Doesn't count / Facts and records / How it's shown / How the work runs (the entry's
`kind`), then by topic so related rules sit together. Superseded rules go to "Old rules (replaced)" at the bottom of
their group. The output is deterministic (no clock): "last updated" is the newest date in the sources.
"""
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rule_registry as RR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = "rules/registry.json"
RULES_MD = "RULES.md"
OUT_JSON = "docs/data/rule-book.json"
OUT_MD = "RULE-BOOK.md"

GROUPS = [  # (key, title, one short intro line)
    ("recording", "Recording & transcript", "What gets written down from the lesson recording, and what is left out."),
    ("spelling", "Spelling (the tutor's Arabizi)", "How Arabic words are spelled on screen. Arabizi = Arabic in Latin letters and numbers (3 = ع, 7 = ح)."),
    ("words", "Words: what counts and what doesn't", "Which words you said get scored, and which don't."),
    ("grammar", "Grammar slips: what counts and what doesn't", "When a grammar mistake counts as a slip, and when it doesn't."),
    ("amal", "The tutor's say", "What the tutor decides: her Doc, her pages, her rulings, and the words she promised to add."),
    ("flashcards", "Flashcards", "How the review cards work."),
    ("pages", "Pages, audio & numbers on screen", "What each page shows, the audio clips, and keeping numbers up to date."),
    ("process", "How Claude and Codex must work", "Rules for the AI helpers that build Anees."),
]
SCOPE_GROUP = {"transcription": "recording", "arabizi": "spelling", "word-scoring": "words", "grammar-scoring": "grammar",
               "amal-data": "amal", "flashcards": "flashcards", "pages": "pages", "audio": "pages", "lessons": "pages",
               "process": "process"}
# lessons rules that are really about scoring or about how the AI works (judgment call, rule book 2026-10-02)
GROUP_OVERRIDE = {"LS-01": "words", "LS-05": "words", "LS-07": "process"}
KIND_SECTIONS = [("error", "Counts"), ("not-error", "Doesn't count"), ("data", "Facts and records"),
                 ("display", "How it's shown"), ("process", "How the work runs")]
BADGES = {  # status -> (badge, what it means)
    "enforced": ("Automatic", "the computer checks it every time"),
    "written": ("Written down", "written where the AI helpers read it; no automatic check yet"),
    "moment-only": ("Fixed once", "only one moment was fixed so far"),
    "needs-medi": ("Waiting on you", "needs your decision"),
}
WHO = {"medi": "Medi", "amal": "Amal"}
GLOSSARY = [
    ("Doc", "The tutor's vocabulary Google Doc: the master list of words."),
    ("Arabizi", "Arabic written in Latin letters and numbers, the way the tutor types it."),
    ("Slip", "a grammar mistake that counts."),
    ("Rule group", "a named grammar pattern, like B8 (also called a bucket)."),
    ("AI readers", "the AI that reads each lesson transcript and finds the moments."),
    ("Publish check", "the test that must pass before anything goes on the live site."),
]


def J(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def big_rule_titles(root):
    """{'S1': "Amal's spelling is the only spelling", ...} from the RULES.md headings (the date note is dropped)."""
    text = (Path(root) / RULES_MD).read_text(encoding="utf-8").replace("\r\n", "\n")
    out = {}
    for m in re.finditer(r"^## (S\d+)\s+[—-]\s+(.+)$", text, re.M):
        out[m.group(1)] = re.sub(r"\s*\((?:Medi|Amal)[^)]*\)\s*$", "", m.group(2)).strip()
    return out


def said(r):
    """Medi's / Amal's own words, newest last. Claude-only sources are labelled, never shown as Medi's words."""
    src = [s for s in r.get("source") or [] if isinstance(s, dict)]
    people = [{"who": WHO[s["by"]], "date": s.get("date", ""), "quote": s.get("quote", "")} for s in src if s.get("by") in WHO]
    if people:
        return people, None
    dates = sorted(s.get("date", "") for s in src)
    return [], (dates[0] if dates else "")


def text_of(r):
    """The plain sentence when it was written for the current statement (plain_for), else the statement itself."""
    if r.get("plain") and r.get("plain_for") == RR.plain_hash(r.get("statement") or ""):
        return r["plain"].strip()
    return (r.get("statement") or "").strip()


def one(r):
    people, claude = said(r)
    out = {"id": r["id"], "text": text_of(r), "status": r.get("status"), "topic": r.get("topic") or ""}
    if r.get("status") in BADGES:
        out["badge"] = BADGES[r["status"]][0]
    if people:
        out["said"] = people
    if claude is not None:
        out["claude"] = claude
    q = r.get("question") or {}
    if r.get("status") == "needs-medi" and q.get("ask"):
        out["question"] = {"ask": q["ask"], "options": list(q.get("options") or [])}
    return out


def group_of(r):
    return GROUP_OVERRIDE.get(r.get("id")) or SCOPE_GROUP.get(r.get("scope"), "process")


def sort_key(r):
    m = re.match(r"^([A-Z]{2})-(\d+)$", r.get("id", ""))
    return ((r.get("topic") or "~").lower(), m.group(1) if m else "", int(m.group(2)) if m else 0)


def build_book(root=ROOT):
    """The whole book as one dict (deterministic: same registry + RULES.md -> same bytes)."""
    root = Path(root)
    reg = J(root / REGISTRY)
    rules = [r for r in reg.get("rules") or [] if isinstance(r, dict) and r.get("id")]
    by_id = {r["id"]: r for r in rules}
    titles = big_rule_titles(root)

    big = []
    for sid in sorted(titles, key=lambda s: int(s[1:])):
        r = next((x for x in rules if f"RULES:{sid}" in (x.get("aliases") or []) and x.get("status") != "superseded"), None)
        big.append({"id": sid, "title": titles[sid], "text": text_of(r) if r else "", "rule": r["id"] if r else ""})

    groups = []
    for n, (key, title, intro) in enumerate(GROUPS, 1):
        mine = sorted((r for r in rules if group_of(r) == key), key=sort_key)
        live = [r for r in mine if r.get("status") != "superseded"]
        sections = []
        for kind, heading in KIND_SECTIONS:
            rows = [one(r) for r in live if r.get("kind") == kind]
            if rows:
                sections.append({"kind": kind, "heading": heading, "rules": rows})
        other = [one(r) for r in live if r.get("kind") not in dict(KIND_SECTIONS)]
        if other:
            sections.append({"kind": "other", "heading": "Other", "rules": other})
        old = []
        for r in mine:
            if r.get("status") != "superseded":
                continue
            o = one(r)
            nxt = by_id.get(r.get("superseded_by") or "")
            o["replaced_by"] = {"id": nxt["id"], "text": text_of(nxt)} if nxt else None
            old.append(o)
        groups.append({"n": n, "key": key, "title": title, "intro": intro, "count": len(live),
                       "sections": sections, "old": old})

    live_all = [r for r in rules if r.get("status") != "superseded"]
    counts = {BADGES[s][0]: sum(1 for r in live_all if r.get("status") == s) for s in BADGES}
    dates = [s.get("date", "") for r in rules for s in (r.get("source") or []) if isinstance(s, dict)]
    return {
        "about": "Built by scripts/build_rule_book.py from rules/registry.json + RULES.md (rule PG-16). Do not edit by hand.",
        "updated": max([d for d in dates if d] or [""]),
        "total": len(live_all),
        "replaced": len(rules) - len(live_all),
        "counts": counts,
        "badges": [{"status": s, "badge": b, "means": m} for s, (b, m) in BADGES.items()],
        "glossary": [{"term": t, "means": m} for t, m in GLOSSARY],
        "big_rules": big,
        "groups": groups,
    }


def _said_line(x):
    if x.get("said"):
        return " · ".join(f"{p['who']}, {p['date']}: “{p['quote']}”" for p in x["said"])
    if "claude" in x:
        return f"Written by Claude, {x['claude']}" if x["claude"] else "Written by Claude"
    return ""


def to_markdown(book):
    L = ["# Anees rule book", "",
         "Every rule Anees follows, in plain words, in the order a lesson happens.",
         "Built from `rules/registry.json` and `RULES.md` by `scripts/build_rule_book.py`. Do not edit this file by hand.",
         "Live page: https://thenatanzi.github.io/anees/rules.html", "",
         f"Last updated {book['updated']} · {book['total']} rules · "
         + " · ".join(f"{b}: {n}" for b, n in book["counts"].items()), "",
         "**What the badges mean**", ""]
    L += [f"- **{b['badge']}**: {b['means']}." for b in book["badges"]]
    L += ["", "**Words used here**", ""]
    L += [f"- **{g['term']}**: {g['means']}" for g in book["glossary"]]
    L += ["", "## The big rules", ""]
    for b in book["big_rules"]:
        L.append(f"- **{b['id']} · {b['title']}.** {b['text']}" + (f" `{b['rule']}`" if b["rule"] else ""))
    for g in book["groups"]:
        L += ["", f"## {g['n']} · {g['title']}", "", f"_{g['intro']}_"]
        for s in g["sections"]:
            L += ["", f"### {s['heading']}", ""]
            for x in s["rules"]:
                L.append(f"- {x['text']} `{x['id']}` _{x.get('badge', '')}_")
                line = _said_line(x)
                if line:
                    L.append(f"  <br><sub>{line}</sub>")
                if x.get("question"):
                    L.append(f"  <br><sub>Your call: {x['question']['ask']} ({' / '.join(x['question']['options'])})</sub>")
        if g["old"]:
            L += ["", "<details><summary>Old rules (replaced)</summary>", ""]
            for x in g["old"]:
                rb = x.get("replaced_by")
                L.append(f"- ~~{x['text']}~~ `{x['id']}`" + (f" → replaced by `{rb['id']}`: {rb['text']}" if rb else ""))
            L += ["", "</details>"]
    return "\n".join(L) + "\n"


def to_json(book):
    return json.dumps(book, ensure_ascii=False, indent=1) + "\n"


def outputs(root=ROOT):
    book = build_book(root)
    return {OUT_JSON: to_json(book), OUT_MD: to_markdown(book)}


def stale(root=ROOT):
    """Published files that differ from what the registry builds now (line endings ignored)."""
    root = Path(root)
    bad = []
    for rel, want in outputs(root).items():
        p = root / rel
        got = p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.is_file() else None
        if got != want:
            bad.append(rel)
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)
    root = Path(a.root)
    if a.check:
        bad = stale(root)
        print("rule book: " + ("OK - up to date" if not bad else "STALE - run python scripts/build_rule_book.py: " + ", ".join(bad)))
        return 1 if bad else 0
    out = outputs(root)
    for rel, text in out.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        with open(root / rel, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    book = json.loads(out[OUT_JSON])
    print(f"rule book: {book['total']} rules in {len(book['groups'])} groups (+{book['replaced']} replaced) -> {OUT_JSON}, {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
