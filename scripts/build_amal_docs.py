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
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow"><title>Arabic Materials</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Literata:opsz,wght@7..72,600&family=Noto+Naskh+Arabic&display=swap">'
            '<style>%s</style></head><body><main><h1>Arabic Materials</h1>'
            '<p class="lede">Amal&#39;s explanations for Medi: prepositions, possession, adjectives, time, kul, the b- prefix and the pointer rule. '
            'Her words, copied from her Doc (last edited %s). <a href="grammar-rules.html">Medi&#39;s grammar rules &rarr;</a></p>'
            '<nav class="toc">%s</nav>%s<footer>Copied word for word from Amal&#39;s Google Doc &ldquo;%s&rdquo; (read %s). '
            'Built by scripts/build_amal_docs.py.</footer></main>'
            # opened from the Tutor menu (go.html adds from=app): the same Back-to-Tutor bar as her other pages
            '<script>(function(){if(new URLSearchParams(location.search).get("from")!=="app")return;var b=document.createElement("div");'
            'b.setAttribute("style","position:sticky;top:0;z-index:9;background:#1D2521;color:#fff;font:600 14px system-ui;padding:9px 14px");'
            'b.innerHTML=\'<a href="../tutor.html" style="color:#fff;text-decoration:none">\\u2190 Back to Tutor</a>\';document.body.insertBefore(b,document.body.firstChild);})();</script>'
            # her writing link carries a token: keep it on the way back to the rules page
            '<script>(function(){var t=new URLSearchParams(location.search).get("t");if(!t)return;'
            'document.querySelectorAll(\'a[href="grammar-rules.html"]\').forEach(function(a){a.href="grammar-rules.html?t="+encodeURIComponent(t);});})();</script>'
            '</body></html>\n'
            % (CSS, meta["edited"], "".join(toc), "".join(body), html.escape(meta["title"]), meta["read"]))
    open(os.path.join(DOCS, "amal", "materials.html"), "w", encoding="utf-8", newline="").write(page)
    print("materials: %d sections -> docs/amal/materials.html" % n)


def main():
    src = json.load(open(os.path.join(SRC, "sources.json"), encoding="utf-8"))
    grammar_notes(src["grammar-notes"])
    materials(src["arabic-materials"])


if __name__ == "__main__":
    main()
