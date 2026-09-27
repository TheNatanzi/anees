"""Build docs/reports/<slug>.html from the research reports listed in docs/data/ai_reports.json (entries with source_md).
docs/ai-reports.html shows the cards from the JSON; each card links to the full report built here. Idempotent; never touches the sources.

  python scripts/build_ai_reports.py
"""
import html, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'docs' / 'data' / 'ai_reports.json'
OUT = ROOT / 'docs' / 'reports'
NAV = ('<a class="ab-nav" href="../progress.html">Progress &amp; Stats</a><a class="ab-nav" href="../lessons.html">Lessons &amp; Audio</a>'
       '<a class="ab-nav" href="../word-bank.html">Word Bank</a><a class="ab-nav" href="../grammar.html">Grammar Rules</a>'
       '<a class="ab-nav" href="../cards.html">Flashcards &amp; Review</a><a class="ab-nav" href="../tutor.html">Tutor</a>'
       '<a class="ab-nav" aria-current="page" href="../ai-reports.html">AI Reports</a><a class="ab-nav" href="../big-picture.html">Big Picture</a>'
       '<a class="ab-nav" href="../settings.html">System Settings</a>')


def page(title, body_html, source, author='', date=''):
    """Word Bank skin (Medi 2026-09-26): sidebar + ab-header; the document body is styled by css/ai-reports.css."""
    eyebrow = ' · '.join(x for x in ('AI report', author, date) if x)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>{html.escape(title)} · AI Reports · Anees</title><script src="../js/theme.js"></script><link rel="stylesheet" href="../css/sabz-tokens.css"><link rel="stylesheet" href="../css/word-bank.css"><link rel="stylesheet" href="../css/vocabulary-progress.css"><link rel="stylesheet" href="../css/ai-reports.css?v=20260926-v1"></head>
<body><div id="anees-bank" class="vp-sabz" aria-label="Anees AI report"><div class="ab-shell">
<aside><div><div class="ab-logo">anees <span lang="ar">أنيس</span></div><div class="ab-tiny">Your Arabic, in progress.</div></div><nav aria-label="Main navigation">{NAV}</nav></aside>
<main>
<header class="ab-header"><div><div class="vp-eyebrow">{html.escape(eyebrow)}</div><h1>{html.escape(title)}</h1><div class="ab-sub">Built from {html.escape(source)}</div></div><a class="ab-preview" href="../ai-reports.html">‹ All AI reports</a></header>
<article class="ar-doc">
{body_html}
</article>
</main></div></div><script>if(location.hash){{const e=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(e)setTimeout(()=>e.scrollIntoView({{block:"start"}}),50);}}</script><script src="../js/build.js"></script><script src="../js/stale.js"></script></body></html>
'''


def build(data_path=DATA, out_dir=OUT, log=print):
    import markdown
    cfg = json.load(io.open(data_path, encoding='utf-8'))
    out_dir.mkdir(parents=True, exist_ok=True)
    built = []
    for r in cfg['reports']:
        src = r.get('source_md')
        if not src:
            continue
        p = Path(src)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            log('MISSING source', src); continue
        md = io.open(p, encoding='utf-8').read()
        body = markdown.markdown(md, extensions=['tables', 'fenced_code', 'toc'])
        body = body.replace('<table>', '<div class="tbl"><table>').replace('</table>', '</table></div>')
        out = out_dir / f"{r['slug']}.html"
        out.write_text(page(r['title'], body, p.name, r.get('author', ''), r.get('date', '')), encoding='utf-8')
        built.append(out.name); log('built', out.name, f'{out.stat().st_size // 1024} KB')
    return built


if __name__ == '__main__':
    sys.exit(0 if build() else 1)
