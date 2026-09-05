"""Build docs/reports/<slug>.html from the research reports listed in docs/data/ai_reports.json (entries with source_md).
The AI reports tab shows the cards from the JSON; each card links to the full report built here. Idempotent; never touches the sources.

  python scripts/build_ai_reports.py
"""
import html, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'docs' / 'data' / 'ai_reports.json'
OUT = ROOT / 'docs' / 'reports'
NAV = ('<a class="tab" href="../index.html#today">Today</a><a class="tab" href="../index.html#lessons">Lessons</a><a class="tab" href="../index.html#words">Words</a>'
       '<a class="tab" href="../index.html#cards">Flashcards</a><a class="tab" href="../index.html#amal">Amal</a><a class="tab" href="../index.html#grammar">Grammar</a>'
       '<a class="tab on" href="../index.html#ai-reports">AI reports</a><a class="tab" href="../index.html#sys-rules">System rules</a><a class="tab" href="../index.html#word-rules">Word &amp; grammar rules</a><a class="tab" href="../index.html#future">Future projects</a>')
CSS = ''':root{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E}
@media(prefers-color-scheme:dark){:root{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "Atkinson Hyperlegible",system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:14px 12px 60px} h1{font-size:26px;line-height:1.2} h2{font-size:21px;margin:30px 0 8px;border-top:1px solid var(--line);padding-top:10px} h3{font-size:17px;margin:20px 0 6px}
.top{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:5} .top .in{max-width:860px;margin:0 auto;padding:10px 12px 0}
.brand{display:flex;align-items:baseline;gap:10px} .brand b{font-size:20px} .brand span{color:var(--mute);font-size:13px}
.top nav{display:flex;gap:4px;overflow-x:auto;padding:6px 0;scrollbar-width:none} .top nav::-webkit-scrollbar{display:none}
.top .tab{flex:0 0 auto;min-height:44px;border:1px solid var(--line);background:var(--bg2);color:var(--ink);border-radius:999px;padding:8px 14px;font:600 15px system-ui;text-decoration:none;display:inline-flex;align-items:center} .top .tab.on{background:var(--teal);color:#fff;border-color:var(--teal)}
.lead{color:var(--mute);font-size:14px} .tbl{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:14px;background:var(--bg2);border:1px solid var(--line)} th,td{padding:6px 8px;border-top:1px solid var(--line);vertical-align:top;text-align:left}
code,pre{font:13px ui-monospace,Consolas,monospace} pre{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:10px;overflow-x:auto} blockquote{border-left:4px solid var(--teal);margin:10px 0;padding:4px 12px;color:var(--mute)}
img{max-width:100%} a{color:var(--teal)}'''


def page(title, body_html, source):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
<header class="top"><div class="in"><div class="brand"><b>Anees</b><span>Palestinian Arabic with Amal · Medi's companion</span></div><nav>{NAV}</nav></div></header>
<main><p class="lead">AI report · built from <code>{html.escape(source)}</code> · <a href="../index.html#ai-reports">back to AI reports</a></p>
{body_html}
</main><script src="../js/build.js"></script><script src="../js/stale.js"></script></body></html>'''


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
        if not p.exists():
            log('MISSING source', src); continue
        md = io.open(p, encoding='utf-8').read()
        body = markdown.markdown(md, extensions=['tables', 'fenced_code', 'toc'])
        body = body.replace('<table>', '<div class="tbl"><table>').replace('</table>', '</table></div>')
        out = out_dir / f"{r['slug']}.html"
        out.write_text(page(r['title'], body, p.name), encoding='utf-8')
        built.append(out.name); log('built', out.name, f'{out.stat().st_size // 1024} KB')
    return built


if __name__ == '__main__':
    sys.exit(0 if build() else 1)
