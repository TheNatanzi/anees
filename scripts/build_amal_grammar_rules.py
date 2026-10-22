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
    pill = (r.get("status_label") or r["status"]) + ("" if r["pct"] is None else " &middot; %s%%" % r["pct"])
    head = re.sub(r'<span class="pill s-[^"]*">[^<]*</span>',
                  '<span class="pill s-%s">%s</span>' % (r["status"], pill), head, count=1)
    head = re.sub(r'<span class="uses">[^<]*</span>',
                  '<span class="uses">%s</span>' % (
                      "%s correction%s, not counted" % (r.get("not_counted_count") or 0, "" if r.get("not_counted_count") == 1 else "s")
                      if r["status"] == "NotTaught"
                      else "%s correction%s" % (r["mistakes"], "" if r["mistakes"] == 1 else "s") if r["status"] == "Unscored"
                      else "%s use%s" % (r["uses"], "" if r["uses"] == 1 else "s")), head, count=1)
    # de-word: a small bar of the % right, in the status colour (drawn by css/dw-amal.css on the rules page)
    head = re.sub(r'<i class="dw-pct[^"]*"[^>]*></i>', "", head)
    if r["pct"] is not None:
        head += '<i class="dw-pct s-%s" style="--p:%s%%" aria-hidden="true"></i>' % (r["status"], r["pct"])
    return '<article id="%s"><header>%s</header>' % (rid, head)


# AM-31: the rules the tutor added on her Tutor page ('Add grammar', her yes) get their own section, rebuilt every run
# between two markers (never section id proposed-*: that is the GR-29 proposals list docs/js/hub/proposals-task.js reads)
import html as _html  # noqa: E402
TUTOR_START, TUTOR_END = "<!--tutor-added:start-->", "<!--tutor-added:end-->"


def tutor_section(bs):
    e = lambda x: _html.escape(str(x or ""), quote=True)  # noqa: E731
    if not bs:
        return ""
    arts = []
    for b in bs:
        ex = "".join('<tr><td class="az">%s</td><td class="en">%s</td></tr>' % (e(a), e(en)) for a, en in b.get("examples", []))
        more = "".join("<li>%s</li>" % e(m) for m in b.get("more", []))
        arts.append('<article id="%s"><header><span class="id">%s</span><h3>%s</h3><span class="pill s-Untested">Untested</span>'
                    '<span class="uses">0 uses</span></header><p class="one">%s</p><p class="why">%s</p><div class="grid"><div><h4>Examples</h4>'
                    '<table class="ext">%s</table><h4>The detail</h4><ul class="more">%s</ul></div><div><h4>From the student&#39;s lessons</h4>'
                    '<p class="none">No automatic detection yet: counted only from the AI readers and your and the student&#39;s notes.</p></div></div></article>'
                    % (e(b["id"]), e(b["id"]), e(b["name"]), e(b["one_line"]), e(b.get("why")), ex, more))
    return ('<section id="tutor-added"><h2><span class="fl">+</span>Rules you added</h2><p class="lede">Rules you added (Add grammar). No auto-check yet.</p>' + "".join(arts) + "</section>")


_tb = [x for x in json.load(open(os.path.join(ROOT, "docs", "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"] if x.get("added_by") == "tutor"]
s = re.sub(re.escape(TUTOR_START) + ".*?" + re.escape(TUTOR_END), "", s, flags=re.S)
s = s.replace("<footer>", TUTOR_START + tutor_section(_tb) + TUTOR_END + "<footer>", 1)

s = re.sub(r'<article id="([^"]+)"><header>(.*?)</header>', header, s, flags=re.S)
missing = sorted(set(rules) - seen)


# ---- De-word (plan/OVERNIGHT-DEWORD-2026-10-22.md, Medi 2026-10-22): keep every rule line and example table on view,
# fold the prose (why + the detail) and the lesson moments behind one tap each (opens in place, PG-17). Idempotent:
# an article already folded has <div class="grid dw-g">. Same text, same numbers, nothing removed.
def dw_fold(m):
    one, why, left, right = m.group(1), m.group(2), m.group(3), m.group(4)
    ex = re.search(r'<table class="ext">.*?</table>', left, re.S)
    more = re.search(r'<ul class="more">.*?</ul>', left, re.S)
    n_more = more.group(0).count("<li>") if more else 0
    n_les = right.count('class="les"')
    body = re.sub(r"^<h4>From the student&#39;s lessons</h4>", "", right)
    info = ('<details class="dw-fold dw-more"><summary><span class="dw-i">i</span>Why%s</summary><div><p class="why">%s</p>%s</div></details>'
            % (" &middot; %d more" % n_more if n_more else "", why, ("<h4>The detail</h4>" + more.group(0)) if more else ""))
    les = ('<details class="dw-fold dw-les"><summary><b>%d</b> %s</summary><div><h4>From the student&#39;s lessons</h4>%s</div></details>'
           % (n_les, "fix heard" if n_les == 1 else "fixes heard", body)) if n_les else '<div class="dw-none">%s</div>' % body
    return ('<p class="one">%s</p>%s<div class="grid dw-g"><div class="dw-ex">%s</div><div class="dw-acts">%s%s</div></div></article>'
            % (one, dw_peek(ex.group(0) if ex else "", n_les), ex.group(0) if ex else "", info, les))


def dw_peek(table, n_les):
    """The closed card's one row (only drawn on the rules page itself, css/dw-amal.css; the Tutor hub keeps the full card):
    the first example, then how much opens on a tap."""
    first = re.search(r'<td class="az">(.*?)</td><td class="en">(.*?)</td>', table, re.S)
    n_ex = table.count("<tr>")
    bits = (['<b>%d</b> example%s' % (n_ex, "" if n_ex == 1 else "s")] if n_ex else []) + (['<b>%d</b> fix%s' % (n_les, "" if n_les == 1 else "es")] if n_les else [])
    return ('<button type="button" class="dw-peek" hidden>%s<span class="dw-more-n">%s</span></button>'
            % ('<span class="dw-ex1"><code>%s</code> = %s</span>' % first.groups() if first else "", " &middot; ".join(bits) or "Open"))


_T = r"((?:(?!</article>|<article ).)*?)"   # never across a card
s = re.sub(r'<p class="one">' + _T + r'</p><p class="why">' + _T + r'</p><div class="grid"><div>' + _T
           + r"</div><div>(<h4>From the student&#39;s lessons</h4>" + _T[1:-1] + r")</div></div></article>",
           dw_fold, s, flags=re.S)
# the approved proposals (section proposed-*): the rule list stays on view; the note and the lesson minutes fold
def dw_fold_p(m):
    why, left, right = m.group(1), m.group(2), m.group(3)
    n = right.count("<tr>")
    return ('<div class="grid dw-g"><div class="dw-ex">%s</div><div class="dw-acts"><details class="dw-fold dw-more"><summary><span class="dw-i">i</span>Your yes</summary>'
            '<div><p class="why">%s</p></div></details><details class="dw-fold dw-les"><summary><b>%d</b> lesson minute%s</summary><div>%s</div></details></div></div></article>'
            % (left, why, n, "" if n == 1 else "s", right)).replace('<div class="grid dw-g">', '<button type="button" class="dw-peek" hidden><span class="dw-ex1">%s</span>'
            '<span class="dw-more-n"><b>%d</b> lesson minute%s</span></button><div class="grid dw-g">' % (re.sub(r"<[^>]+>", "", (re.search(r"<li>(.*?)</li>", left) or re.search("(.*)", "")).group(1)), n, "" if n == 1 else "s"), 1)


s = re.sub(r'<p class="why">' + _T + r'</p><div class="grid"><div>(<h4>What it says</h4>' + _T[1:-1] + r')</div><div>(<h4>From the ' + _T[1:-1]
           + r')</div></div></article>', dw_fold_p, s, flags=re.S)
# the status of every rule as a picture: one split bar + the rule chips coloured by status (counts read off the pills)
_order = [("Mastered", "Mastered"), ("Good", "Good"), ("Shaky", "Shaky"), ("Wrong", "Wrong"), ("Untested", "Untested"),
          ("Unscored", "Unscored"), ("NotTaught", "Not taught")]
_st = {a: re.search(r'<span class="pill s-(\w+)"', b).group(1)
       for a, b in re.findall(r'<article id="([^"]+)"><header>(.*?)</header>', s, re.S) if re.search(r'<span class="pill s-(\w+)"', b)}
_cnt = {k: sum(1 for v in _st.values() if v == k) for k, _ in _order}
_tot = sum(_cnt.values()) or 1
_bar = "".join('<i class="s-%s" style="width:%.1f%%" title="%s %d"></i>' % (k, 100.0 * _cnt[k] / _tot, lab, _cnt[k]) for k, lab in _order if _cnt[k])
_key = "".join('<span class="dw-k s-%s"><b>%d</b> %s</span>' % (k, _cnt[k], lab) for k, lab in _order if _cnt[k])
DW_S, DW_E, DW_J = "<!--dw-status:start-->", "<!--dw-status:end-->", "</div></details><!--dw-jump:end-->"
_ico = {"Mastered": '<path d="M5 12.5l4.2 4.2L19 7"/>', "Good": '<path d="M12 19V5M6 11l6-6 6 6"/>',
        "Shaky": '<path d="M3 12c2.2-4 4.4-4 6.6 0s4.4 4 6.6 0 3.6-2.6 4.8-1.4"/>', "Wrong": '<path d="M6 6l12 12M18 6L6 18"/>'}
_tiles = "".join('<button type="button" class="dw-big dw-filt s-%s" data-s="%s" aria-pressed="false"><svg class="dw-ico" viewBox="0 0 24 24" '
                 'fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>'
                 '<b>%d</b><span>%s</span></button>' % (k, k, _ico[k], _cnt[k], k) for k in ("Mastered", "Good", "Shaky", "Wrong"))
_rest = " &middot; ".join("%d %s" % (_cnt[k], lab.lower()) for k, lab in _order[4:] if _cnt[k])
s = re.sub(re.escape(DW_S) + ".*?" + re.escape(DW_E), "", s, flags=re.S).replace(DW_J, "")
_toc_end = s.index("</nav>", s.index('<nav class="toc">'))
s = s[:_toc_end + 6] + DW_J + s[_toc_end + 6:]
s = s.replace('<nav class="toc">', DW_S + '<div class="dw-status"><div class="dw-sbar">%s</div><div class="dw-bigs dw-tiles">%s</div>'
              '<p class="dw-cap"><span class="dw-dots dw-leg"><i class="s-Mastered"></i>mastered <i class="s-Good"></i>good <i class="s-Shaky"></i>shaky '
              '<i class="s-Wrong"></i>wrong <i class="s-Untested"></i>no score yet</span> %s &middot; tap a box to see only those rules</p></div>'
              '<details class="dw-fold dw-jump"><summary>Jump to a rule</summary><div>' % (_bar, _tiles, _rest) + DW_E + '<nav class="toc">', 1)
DW_JS = ('<script data-dw-filter>document.addEventListener("click",function(e){var b=e.target.closest(".dw-filt");if(!b)return;'
         'var on=b.getAttribute("aria-pressed")!=="true";document.querySelectorAll(".dw-filt").forEach(function(x){x.setAttribute("aria-pressed","false")});'
         'if(on){b.setAttribute("aria-pressed","true");document.body.setAttribute("data-dw-filter",b.dataset.s)}else document.body.removeAttribute("data-dw-filter")});</script>')
DW_JS += ('<script data-dw-cards>(function(){function open(a,on){if(a)a.classList.toggle("dw-on",on)}'
          'document.addEventListener("click",function(e){var b=e.target.closest(".dw-peek, article > header");if(!b||e.target.closest("a,abbr"))return;var a=b.closest("article");open(a,!a.classList.contains("dw-on"))});'
          'function hash(){var a=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1)));if(a&&a.tagName==="ARTICLE")open(a,true)}'
          'window.addEventListener("hashchange",hash);hash()})();</script>')
if "data-dw-filter>" not in s:
    s = s.replace("</body>", DW_JS + "</body>", 1)
s = re.sub(r'<a( class="s-\w+")? href="#([^"]+)">', lambda m: '<a class="s-%s" href="#%s">' % (_st.get(m.group(2)) or _st.get(m.group(2).replace("-add", "+")) or "Untested", m.group(2))
           if m.group(2) in _st or m.group(2).replace("-add", "+") in _st else m.group(0), s)
# each family folds to one line: its rules as status dots + how many (tap the line to open; css/dw-amal.css)
s = re.sub(r'<button type="button" class="dw-fam"[^>]*>.*?</button>', "", s, flags=re.S)


def _fam(m):
    sec = m.group(0)
    ids = re.findall(r'<article id="([^"]+)">', sec)
    dots = "".join('<i class="s-%s" title="%s"></i>' % (_st.get(i, "Untested"), i) for i in ids)
    weak = sum(1 for i in ids if _st.get(i) in ("Wrong", "Shaky"))
    btn = ('<button type="button" class="dw-fam" hidden><span class="dw-dots">%s</span><span class="dw-famn"><b>%d</b> rule%s%s</span></button>'
           % (dots, len(ids), "" if len(ids) == 1 else "s", " &middot; <b>%d</b> to work on" % weak if weak else ""))
    return sec.replace("</h2>", "</h2>" + btn, 1)


s = re.sub(r"<section[^>]*>.*?</section>", _fam, s, flags=re.S)
DW_JS2 = ('<script data-dw-fams>(function(){document.addEventListener("click",function(e){var b=e.target.closest(".dw-fam, main section > h2");if(!b)return;'
          'b.closest("section").classList.toggle("dw-open")});function hash(){var a=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1)));'
          'if(a){var s=a.closest("section");if(s)s.classList.add("dw-open")}}window.addEventListener("hashchange",hash);hash()})();</script>')
if "data-dw-fams>" not in s:
    s = s.replace("</body>", DW_JS2 + "</body>", 1)
# one rule count everywhere: the headline adds up to the cards and the bar
_secs = re.findall(r"<section( id=\"([^\"]*)\")?>(.*?)</section>", s, re.S)
_core = sum(len(re.findall(r"<article id=", b)) for _, i, b in _secs if not i)
_prop = sum(len(re.findall(r"<article id=", b)) for _, i, b in _secs if i.startswith("proposed-"))
_mine = sum(len(re.findall(r"<article id=", b)) for _, i, b in _secs if i == "tutor-added")
s = re.sub(r'(<h1>.*?</h1><p class="lede">).*?(</p>)', lambda m: m.group(1) + "%d rules: %d core%s%s. Please check each one." % (
    _core + _prop + _mine, _core, " + %d approved" % _prop if _prop else "", " + %d you added" % _mine if _mine else "") + m.group(2), s, count=1, flags=re.S)
# theme + look switch (js/theme.js loads js/look.js) and the page's de-word skin
if "../js/theme.js" not in s:
    s = s.replace("</title>", '</title><script src="../js/theme.js"></script>', 1)
if "../css/dw-amal.css" not in s:
    s = s.replace("</style></head>", '</style><link rel="stylesheet" href="../css/sabz-tokens.css"><link rel="stylesheet" href="../css/dw-amal.css?v=dw1"></head>', 1)
s = s.replace("<body><main>", '<body class="dw-doc"><main>', 1)
if "data-theme-slot" not in s:   # the theme + look switches sit top right, never over a card
    s = s.replace('<body class="dw-doc"><main>', '<body class="dw-doc"><main><div class="dw-top" data-theme-slot></div>', 1)

dates = [L["date"] for L in g["lessons"]]
cov = g["coverage"]
foot = ("Scores from %d lessons (%s &ndash; %s) &middot; %d fixes checked by hand "
        '<details class="dw-fold dw-foot"><summary><span class="dw-i">i</span>How scores work</summary><div>'
        "Corrections are the ones you said aloud, checked by hand (sweep of Sep 24, with your notes of Sep 27 applied); uses are counted by machine. "
        "Mastered = 10+ uses, 95%%+ right &middot; Good = 85%%+ &middot; Shaky = 65%%+ &middot; Wrong = below 65%% &middot; Untested = not used yet "
        "&middot; Unscored = only your corrections are counted so far, no %% yet &middot; Not taught yet = your notes of Sep 27 (B14, B15): no score, "
        "and your corrections there are not counted.</div></details>"
        % (cov["lessons_scored"], pretty(dates[0]), pretty(dates[-1]),
           sum(r["mistakes"] for r in g["rules"])))
s, n = re.subn(r"<footer>.*?</footer>", "<footer>" + foot + "</footer>", s, count=1, flags=re.S)
assert n == 1, "footer not found"
# Amal writes her grammar notes on this page (scripts/build_amal_docs.py, js/amal-grammar-notes.js; Medi 2026-10-01)
assert "js/amal-grammar-notes.js" in s, "the notes script tag is missing from the page"
assert "js/amal-undo.js" in s, "the Undo script (AM-17) is missing from the page"

open(PAGE, "w", encoding="utf-8", newline="").write(s)
print("updated", len(seen), "rules on", PAGE)
if missing:
    print("rules in the console with no card on the page:", ", ".join(missing))
