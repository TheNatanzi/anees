# -*- coding: utf-8 -*-
"""Refresh Amal's rules page (docs/amal/grammar-rules.html) from docs/data/grammar-console.json.

The page itself is the template: its CSS, rule text, examples and lesson moments stay
exactly as they are. Only the numbers change - each rule's status pill (status + % right),
its use count, and the footer line saying what the scores are built from - so Amal's link
always shows the same numbers as the Grammar console.

Run after scripts/build_grammar_console.py.
"""
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "docs", "amal", "grammar-rules.html")
CONSOLE = os.path.join(ROOT, "docs", "data", "grammar-console.json")

g = json.load(open(CONSOLE, encoding="utf-8"))
rules = {r["id"]: r for r in g["rules"]}
s = open(PAGE, encoding="utf-8").read()


def pretty(d):
    x = datetime.date.fromisoformat(d)
    return x.strftime("%b ") + str(x.day)


seen = set()


def header(m):
    rid, head = m.group(1), m.group(2)
    r = rules.get(rid)
    if not r:
        return m.group(0)
    seen.add(rid)
    pill = r["status"] + ("" if r["pct"] is None else " &middot; %s%%" % r["pct"])
    head = re.sub(r'<span class="pill s-[^"]*">[^<]*</span>',
                  '<span class="pill s-%s">%s</span>' % (r["status"], pill), head, count=1)
    head = re.sub(r'<span class="uses">[^<]*</span>',
                  '<span class="uses">%s</span>' % (
                      "%s correction%s" % (r["mistakes"], "" if r["mistakes"] == 1 else "s") if r["status"] == "Unscored"
                      else "%s use%s" % (r["uses"], "" if r["uses"] == 1 else "s")), head, count=1)
    return '<article id="%s"><header>%s</header>' % (rid, head)


s = re.sub(r'<article id="([^"]+)"><header>(.*?)</header>', header, s, flags=re.S)
missing = sorted(set(rules) - seen)

dates = [L["date"] for L in g["lessons"]]
cov = g["coverage"]
foot = ("Scores from %d recorded lessons (%s &ndash; %s). Corrections are the ones you said aloud, checked by hand "
        "(%d, sweep of Sep 24); uses are counted by machine. Mastered = 10+ uses, 95%%+ right &middot; Good = 85%%+ "
        "&middot; Shaky = 65%%+ &middot; Wrong = below 65%% &middot; Untested = not used yet &middot; Unscored = only your corrections are counted so far, no %% yet."
        % (cov["lessons_scored"], pretty(dates[0]), pretty(dates[-1]),
           sum(r["mistakes"] for r in g["rules"])))
s, n = re.subn(r"<footer>.*?</footer>", "<footer>" + foot + "</footer>", s, count=1, flags=re.S)
assert n == 1, "footer not found"

open(PAGE, "w", encoding="utf-8", newline="").write(s)
print("updated", len(seen), "rules on", PAGE)
if missing:
    print("rules in the console with no card on the page:", ", ".join(missing))
