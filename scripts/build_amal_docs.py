# -*- coding: utf-8 -*-
"""Amal's two Google Docs as Anees pages (Medi 2026-10-01: "every page Amal is sent or linked to opens for her, fully
inside Anees"). Her Docs are private Google Docs (she owns them), so a script cannot read them; Claude reads them with
Medi's Google Drive connector and saves the text here, word for word:

    data/amal-docs/grammar-notes.md      "Mahdi's Grammar Rules notes"  (Doc 1SCYeIEu-..., edited by her 2026-09-30)
    data/amal-docs/arabic-materials.md   "Arabic Materials"            (Doc 1gStzPV9..., edited by her 2026-09-27)
    data/amal-docs/sources.json          Doc ids, titles, her last edit, when Claude read them

This builder turns them into:

    docs/data/amal-grammar-notes.json    her notes per rule -> shown under each rule on docs/amal/grammar-rules.html
                                         (js/amal-grammar-notes.js), where she now writes new notes (Supabase
                                         amal_rules, source grammar_notes, with her Tutor link's token)
    docs/amal/materials.html             "Arabic Materials" in the same look as her rules page

Her wording and spelling are never changed (only Doc layout noise: doubled headings, empty lines). Links to her other
Doc point to the Anees copy. Runs in scripts/amal_trigger.py (STEPS / AUDIT_CHAIN); safe to run any time.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "amal-docs")
DOCS = os.path.join(ROOT, "docs")
RULES_PAGE = os.path.join(DOCS, "amal", "grammar-rules.html")

# Her headings use her own numbers; where they differ from the rules page the page id wins (see amal_grammar_notes.py:
# "B13 in her headings = our B14", 3am).
HER_TO_PAGE = {"B13": ["B14"], "C4B": ["C4b"]}
LINKS = {"https://docs.google.com/document/u/0/d/1gStzPV90qvCFYzysgrMT6KOoOU4R4d0v4G8R648w8O0/edit": "materials.html",
         "https://thenatanzi.github.io/anees/amal/grammar-rules.html": "grammar-rules.html"}


def inline(s):
    """Escape, then her light markdown: [text](url), ***x***, **x**, *x*."""
    s = html.escape(s.strip(), quote=False).replace("\\-", "-").replace("\\*", "*")
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: '<a href="%s">%s</a>' % (html.escape(LINKS.get(m.group(2), m.group(2))), m.group(1)), s)
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    return s.replace("*", "")


def blocks(lines):
    """Markdown lines -> HTML: bullet lists and paragraphs."""
    out, ul = [], False
    for raw in lines:
        t = raw.rstrip()
        if not t.strip() or t.strip() in ("·", "<!-- end list -->"):
            if ul:
                out.append("</ul>"); ul = False
            continue
        m = re.match(r"^\s*-\s+(.*)$", t)
        if m:
            if not ul:
                out.append("<ul>"); ul = True
            out.append("<li>%s</li>" % inline(m.group(1)))
        elif ul and re.match(r"^\s", t):
            out.append("<li class=\"sub\">%s</li>" % inline(t))
        else:
            if ul:
                out.append("</ul>"); ul = False
            out.append("<p>%s</p>" % inline(t))
    if ul:
        out.append("</ul>")
    return "".join(out)


def page_ids():
    s = open(RULES_PAGE, encoding="utf-8").read()
    return re.findall(r'<article id="([^"]+)">', s)


def rules_of(heading, ids):
    """'A2+3. Possessive Endings' -> [A2, A3]; 'B2 -4"b" drop' -> [B2, B3, B4]; 'B13. 3am' -> [B14]."""
    m = re.match(r"^([A-F])(\d+)([a-zA-Z]?)\s*(?:[+-]\s*(\d+))?", heading.strip())
    if not m:
        return []
    letter, a, suf, b = m.group(1), int(m.group(2)), m.group(3), m.group(4)
    her = "%s%d%s" % (letter, a, suf.upper())
    if her in HER_TO_PAGE:
        return HER_TO_PAGE[her]
    got = ["%s%d" % (letter, n) for n in range(a, int(b) + 1)] if b else ["%s%d%s" % (letter, a, suf.lower())]
    return [g for g in got if g in ids]


def written_notes():
    """Notes she saved on the rules page. Read here (service key) so they stay on the page when her link's token changes;
    if the database cannot be reached, the last built list is kept."""
    path = os.path.join(DOCS, "data", "amal-grammar-notes.json")
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import db
        rows = db.select("amal_rules", {"select": "id,word_key,payload,created_at", "source": "eq.grammar_notes", "order": "id.asc"})
        return [{"rule": (r.get("payload") or {}).get("rule") or str(r.get("word_key") or "").replace("rule:", ""),
                 "text": (r.get("payload") or {}).get("text") or "", "at": r["created_at"]} for r in rows]
    except Exception as e:  # noqa: BLE001 - offline build keeps the last list
        print("written notes: database not read (%s), keeping the last list" % type(e).__name__)
        return json.load(open(path, encoding="utf-8")).get("written", []) if os.path.exists(path) else []


def grammar_notes(meta):
    ids = set(page_ids())
    lines = open(os.path.join(SRC, "grammar-notes.md"), encoding="utf-8").read().splitlines()
    sections, cur = [], None
    for ln in lines[1:]:
        h = re.match(r"^###\s+(.*)$", ln) or re.match(r"^([A-F]\d+[A-Za-z]?\.\s.*)$", ln)
        if h:
            cur = {"heading": h.group(1).strip(), "lines": []}
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
    out = []
    for s in sections:
        rules = rules_of(s["heading"], ids)
        out.append({"heading": s["heading"], "rules": rules, "html": blocks(s["lines"])})
    unplaced = [s["heading"] for s in out if not s["rules"]]
    data = {"source": meta, "note": "Amal's notes from her Google Doc, word for word, plus the notes she writes on the rules page "
                                    "(Supabase amal_rules, source grammar_notes); shown under each rule on amal/grammar-rules.html. "
                                    "Built by scripts/build_amal_docs.py from data/amal-docs/grammar-notes.md.",
            "sections": out, "written": written_notes()}
    json.dump(data, open(os.path.join(DOCS, "data", "amal-grammar-notes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("grammar notes: %d sections, %d placed on rules, %d written on the page%s" % (len(out), len(out) - len(unplaced), len(data["written"]),
                                                             (" - not placed: " + ", ".join(unplaced)) if unplaced else ""))
    assert not unplaced, "a note heading matches no rule on the page"


CSS = """:root{--bg:#F5F6F2;--panel:#fff;--ink:#1D2521;--muted:#66716B;--line:#DCE1DA;--green:#2E6A4E;--greenbg:#E3EFE7;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#131A17;--panel:#1A231F;--ink:#E4EAE5;--muted:#95A19A;--line:#2C3833;--green:#7FC29E;--greenbg:#1F3129;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 "IBM Plex Sans",system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding-inline:16px;padding-block:28px 60px}
h1{font:600 30px/1.15 Literata,Georgia,serif;margin:0 0 6px}
.lede{color:var(--muted);max-width:66ch;margin:0 0 16px}
.toc{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.toc a{font:500 12px "IBM Plex Mono",monospace;color:var(--green);text-decoration:none;border:1px solid var(--line);border-radius:4px;padding:2px 7px;background:var(--panel)}
section{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin:14px 0;scroll-margin-top:12px}
h2{font:600 22px/1.3 Literata,Georgia,serif;margin:0 0 10px}
h3{font-size:17px;margin:18px 0 6px;color:var(--green)}
h4{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:500;margin:14px 0 4px}
p{margin:6px 0;max-width:72ch}
ul{margin:4px 0 8px;padding-left:20px;display:grid;gap:3px}
li{overflow-wrap:anywhere}
a{color:var(--green)}
footer{margin-top:28px;color:var(--muted);font-size:12px}"""


def materials(meta):
    lines = open(os.path.join(SRC, "arabic-materials.md"), encoding="utf-8").read().splitlines()
    body, buf, toc, n = [], [], [], 0

    def flush():
        if buf:
            body.append(blocks(buf)); buf.clear()
    open_sec = False
    for ln in lines:
        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        if not m:
            buf.append(ln); continue
        flush()
        lvl, text = len(m.group(1)), m.group(2).strip()
        if lvl == 1:
            if open_sec:
                body.append("</section>")
            n += 1
            sid = "s%d" % n
            toc.append('<a href="#%s">%s</a>' % (sid, inline(text)))
            body.append('<section id="%s"><h2>%s</h2>' % (sid, inline(text))); open_sec = True
        else:
            body.append("<h%d>%s</h%d>" % (lvl + 1, inline(text), lvl + 1))
    flush()
    if open_sec:
        body.append("</section>")
    # de-word (plan/OVERNIGHT-DEWORD-2026-10-22.md): every section folds to its title + the names of its parts (a tap opens it in place,
    # css/dw-amal.css; the Tutor hub reads the same sections and ignores the hidden part list). Her words are untouched.
    joined = "".join(body)

    def parts(m):
        heads = [re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<h3>(.*?)</h3>", m.group(2))]
        row = ('<button type="button" class="dw-parts" hidden><b>%d</b> part%s%s</button>'
               % (len(heads), "" if len(heads) == 1 else "s", ('<span class="dw-pn">: ' + " &middot; ".join("<bdi>%s</bdi>" % h for h in heads) + "</span>") if heads else "")) if heads else '<button type="button" class="dw-parts dw-noparts" hidden>Open</button>'
        return m.group(1) + row + m.group(2)
    joined = re.sub(r'(<section id="s\d+"><h2>.*?</h2>)(.*?)(?=</section>)', parts, joined, flags=re.S)
    # one flat icon per topic (by its title; a plain dot when no word matches)
    ICONS = [("preposition", '<circle cx="12" cy="7" r="3.2"/><path d="M3 12.5h18M6 12.5V20M18 12.5V20"/>'),
             ("possess", '<path d="M2.5 12L8 6.5l5.5 5.5M4.5 10.5V18h7v-7.5"/><circle cx="18" cy="8.5" r="2.3"/><path d="M14.5 18c0-2.6 1.6-4.4 3.5-4.4s3.5 1.8 3.5 4.4"/>'),
             ("adjective def", '<path d="M3 12l8-8h9v9l-8 8z"/><circle cx="15.5" cy="8.5" r="1.5"/>'),
             ("time", '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>'),
             ("adjective", '<path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z"/>'),
             ("kul", '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
             ("prefix", '<text x="12" y="17" text-anchor="middle" font-size="15" font-family="serif" fill="currentColor" stroke="none">ب</text><path d="M4 20L20 4"/>'),
             ("pointer", '<path d="M9 11V5.5a1.6 1.6 0 0 1 3.2 0V11M12.2 10V9a1.6 1.6 0 0 1 3.2 0v2M15.4 10.5a1.6 1.6 0 0 1 3.2 0V15a6 6 0 0 1-6 6h-1a6 6 0 0 1-5-2.8l-2.3-3.8a1.5 1.5 0 0 1 2.5-1.6L9 14"/>')]

    def icon(m):
        t = re.sub(r"<[^>]+>", "", m.group(2)).lower()
        d = next((g for k, g in ICONS if k in t), '<circle cx="12" cy="12" r="5"/>')
        return ('%s<svg class="dw-tico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                'stroke-linejoin="round" aria-hidden="true">%s</svg>%s' % (m.group(1), d, m.group(2)))
    joined = re.sub(r'(<section id="s\d+"><h2>)(.*?</h2>)', icon, joined)
    # round 2 (Medi 2026-10-22: "you cut out too much data"): every section shows open, with the list of topics on top
    joined = joined.replace('<section id="s', '<section class="dw-open" id="s')
    _np = {sid: len(re.findall(r"<h3>", b)) for sid, b in re.findall(r'<section class="dw-open" id="(s\d+)">(.*?)</section>', joined, re.S)}
    tiles = '<nav class="toc dw-mtoc">%s</nav>' % "".join(
        re.sub(r'<a href="#(s\d+)">(.*?)</a>', lambda m: '<a href="#%s">%s%s</a>' % (m.group(1), m.group(2), ' <b>%d</b>' % _np[m.group(1)] if _np.get(m.group(1)) else ""), t) for t in toc)
    # round 3: each example as a two-part row (her Arabic | the English), her labels as small bold tags; every word kept
    joined = re.sub(r"<li>((?:(?!</li>).)*?) \| ((?:(?!</li>).)*?)</li>", lambda m: '<li class="dw-exr"><span class="dw-az">%s</span><span class="dw-en">%s</span></li>' % (m.group(1), m.group(2)), joined)
    joined = re.sub(r"<p>(Core [Ff]unctions?|English [Ee]quivalents?|Examples?|Use|Rule|Note)\s*:\s*", lambda m: '<p class="dw-lab"><b>%s</b> ' % m.group(1), joined)
    _unused = "".join('<a class="dw-topic" href="#%s"><b>%d</b><span>%s</span></a>' % (sid, i + 1, name)
                    for i, (sid, name) in enumerate(re.findall(r'<a href="#(s\d+)">(.*?)</a>', "".join(toc))))
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow"><title>Arabic Materials</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Literata:opsz,wght@7..72,600&family=Noto+Naskh+Arabic&display=swap">'
            '<script src="../js/theme.js"></script><style>%s</style><link rel="stylesheet" href="../css/sabz-tokens.css"><link rel="stylesheet" href="../css/dw-amal.css?v=dw1">'
            '</head><body class="dw-doc dw-mat"><main><div class="dw-top" data-theme-slot></div><h1>Arabic Materials</h1>'
            '<p class="lede dw-lede">Your Doc notes, word for word <span class="dw-chip muted">edited %s</span> <a class="dw-btn" href="grammar-rules.html">Grammar rules &rarr;</a></p>'
            '%s%s<footer>Copied from your Google Doc &ldquo;%s&rdquo; (read %s).</footer></main>'
            '<script>(function(){function sec(el){return el&&el.closest("section")}document.addEventListener("click",function(e){var b=e.target.closest(".dw-parts, main section > h2");'
            'if(b)sec(b).classList.toggle("dw-open")});function hash(){var a=location.hash&&document.getElementById(location.hash.slice(1));if(a&&sec(a))sec(a).classList.add("dw-open")}'
            'window.addEventListener("hashchange",hash);hash()})();</script>'
            # opened from the Tutor menu (go.html adds from=app): the same Back-to-Tutor bar as her other pages
            '<script>(function(){if(new URLSearchParams(location.search).get("from")!=="app")return;var b=document.createElement("div");'
            'b.setAttribute("style","position:sticky;top:0;z-index:9;background:#1D2521;color:#fff;font:600 14px system-ui;padding:9px 14px");'
            'b.innerHTML=\'<a href="../tutor.html" style="color:#fff;text-decoration:none">\\u2190 Back to Tutor</a>\';document.body.insertBefore(b,document.body.firstChild);})();</script>'
            # her writing link carries a token: keep it on the way back to the rules page
            '<script>(function(){var t=new URLSearchParams(location.search).get("t");if(!t)return;'
            'document.querySelectorAll(\'a[href="grammar-rules.html"]\').forEach(function(a){a.href="grammar-rules.html?t="+encodeURIComponent(t);});})();</script>'
            '<script src="../js/rule-names.js?v=20261002-1" defer></script>'   # rule ids explain themselves on hover/tap
            '</body></html>\n'
            % (CSS, meta["edited"], tiles, joined, html.escape(meta["title"]), meta["read"]))
    open(os.path.join(DOCS, "amal", "materials.html"), "w", encoding="utf-8", newline="").write(page)
    print("materials: %d sections -> docs/amal/materials.html" % n)


def main():
    src = json.load(open(os.path.join(SRC, "sources.json"), encoding="utf-8"))
    grammar_notes(src["grammar-notes"])
    materials(src["arabic-materials"])


if __name__ == "__main__":
    main()
