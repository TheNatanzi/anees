# -*- coding: utf-8 -*-
"""Step 6 of the full audit (Medi 2026-09-25, decision b): every Medi-facing page that prints a transcript line shows
her Arabizi on top and the recorded Arabic small underneath, through ONE renderer (docs/js/transcript-arabizi.js on top
of docs/js/word-bank-arabizi.js, rule S1). Amal's pages (docs/amal/*) stay Arabic-first and are never touched.

    python scripts/arabizi_everywhere.py            -> patches the static pages in place (idempotent) and prints the audit
    python scripts/arabizi_everywhere.py --audit    -> only prints which page prints Arabic lines and how it renders them

Pages already Arabizi-first through their own JS are left alone: lessons.html (lessons-page.js speech()), grammar.html
(grammar-console.js speech()), word-bank.html (word-bank.js: ab-transcript-latin then ab-transcript-original).
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE); DOCS = os.path.join(REPO, "docs")
V = "az1"
AR = re.compile(r"[ء-غف-ي]")

# page -> (relative js path, CSS selector of the elements that hold a transcript line)
TARGETS = {
    "lessons/<date>.html":        ("../js/", "p.turn .words, p.chat .words"),
    "lessons/<date>-report.html": ("../js/", "span.ar, .said, .rec"),
    "slips.html":                 ("js/",    ".moment .said .ar, .moment .rec .ar"),
    "speaking-review.html":       ("js/",    "#questions bdi, #questions .ar"),
    "speaking-audit.html":        ("js/",    ".scroll td, .scroll bdi"),
    "word-bank-audit.html":       ("js/",    "bdi"),
    "index.html":                 ("js/",    "#tab-amal bdi, #tab-words bdi"),
}
ALREADY = {"lessons.html": "lessons-page.js speech(): gc-latin over gc-arabic",
           "grammar.html": "grammar-console.js speech(): gc-latin over gc-arabic",
           "word-bank.html": "word-bank.js: ab-transcript-latin then ab-transcript-original"}


def tags(js, selector):
    return (f'<script src="{js}word-bank-arabizi.js?v={V}"></script>'
            f'<script src="{js}transcript-arabizi.js?v={V}" data-arabizi-selector="{selector}"></script>')


def patch(path, js, selector):
    s = open(path, encoding="utf-8").read()
    if "transcript-arabizi.js" in s:
        return "already"
    t = tags(js, selector)
    if "</body>" in s:
        s = s.replace("</body>", t + "</body>", 1)
    elif "</html>" in s:
        s = s.replace("</html>", t + "</html>", 1)
    else:
        s += t
    open(path, "w", encoding="utf-8").write(s)
    return "patched"


def pages():
    out = []
    for f in sorted(os.listdir(os.path.join(DOCS, "lessons"))):
        if f.endswith("-report.html"):
            out.append((os.path.join(DOCS, "lessons", f), *TARGETS["lessons/<date>-report.html"]))
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f):
            out.append((os.path.join(DOCS, "lessons", f), *TARGETS["lessons/<date>.html"]))
    for name in ("slips.html", "speaking-review.html", "speaking-audit.html", "word-bank-audit.html", "index.html"):
        p = os.path.join(DOCS, name)
        if os.path.exists(p):
            out.append((p, *TARGETS[name]))
    return out


def audit():
    rows = []
    for name in sorted(os.listdir(DOCS)):
        p = os.path.join(DOCS, name)
        if not name.endswith(".html"):
            continue
        s = open(p, encoding="utf-8").read()
        n_ar = len(AR.findall(s))
        how = ALREADY.get(name) or ("transcript-arabizi.js" if "transcript-arabizi.js" in s else ("static Arabic only" if n_ar else "no Arabic in the file (data drawn by JS)"))
        rows.append((name, n_ar, how))
    for name in sorted(os.listdir(os.path.join(DOCS, "lessons"))):
        if name.endswith(".html"):
            s = open(os.path.join(DOCS, "lessons", name), encoding="utf-8").read()
            rows.append(("lessons/" + name, len(AR.findall(s)), "transcript-arabizi.js" if "transcript-arabizi.js" in s else "static Arabic only"))
    return rows


def main():
    if "--audit" not in sys.argv:
        for path, js, sel in pages():
            print(patch(path, js, sel), os.path.relpath(path, DOCS))
    print("\npage | Arabic letters in file | how transcript lines render")
    for name, n, how in audit():
        print(f"{name} | {n} | {how}")


if __name__ == "__main__":
    main()
