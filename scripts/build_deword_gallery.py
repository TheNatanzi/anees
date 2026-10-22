# -*- coding: utf-8 -*-
"""De-word overnight: build the before / Look A / Look B gallery.

    python scripts/build_deword_gallery.py <scratch_deword_dir> [--artifact <out.html>]

Reads <dir>/before/ (scripts/deword_capture.py) and every <dir>/<group>/status.json the page workers wrote
(final capture dirs per look + each judge's last grades). Writes
  docs/deword/<page>-<before|flat|kurz>-<light|dark>-<desktop|phone>.jpg   (small JPEGs, top of the page)
  docs/deword-gallery.html                                                (one row per page)
and, with --artifact, the same page as a claude.ai Artifact body (images referenced as deword/...).
"""
import argparse, html, json, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deword_capture import PAGES  # noqa: E402

OUT = ROOT / 'docs' / 'deword'
STATES = [('before', 'Before'), ('flat', 'Look A · flat'), ('kurz', 'Look B · bright')]
MODES = [(t, d) for t in ('light', 'dark') for d in ('desktop', 'phone')]
JUDGES = [('claude', 'Claude'), ('codex', 'GPT-6 Astra'), ('gemini', 'Gemini 3.8 Flash')]
NAMES = {'progress': 'Progress & Stats', 'ai-reports': 'AI Reports', 'flow': 'How Anees works', 'lessons': 'Lessons & Audio',
         'lesson': 'One lesson (10-14)', 'word-bank': 'Word Bank', 'grammar': 'Grammar Rules', 'cards': 'Flashcards & Review',
         'student': 'Student', 'homework': 'Homework', 'tutor': 'Tutor', 'amal-grammar-rules': 'Tutor · grammar rules',
         'amal-materials': 'Tutor · materials', 'amal-after': 'Tutor · after lesson', 'amal-plan': 'Tutor · plan',
         'amal-review': 'Tutor · review', 'amal-verb-check': 'Tutor · verb check', 'amal-word-review': 'Tutor · word review',
         'big-picture': 'Big Picture', 'settings': 'System Settings'}


def shrink(src, dst):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    if w > 600:
        im = im.crop((0, 0, w, min(h, 2000))).resize((1000, int(min(h, 2000) * 1000 / w)), Image.LANCZOS)
    else:
        im = im.crop((0, 0, w, min(h, 2000)))  # phone: full 390 px width, sharp when zoomed
    im.save(dst, 'JPEG', quality=60, optimize=True, progressive=True)


def words(d, page):
    p = Path(d) / f'{page}.words.json'
    if not p.exists():
        return None
    return sum(json.loads(p.read_text(encoding='utf-8')).values())


def letters(g):
    """'AAAAB' or {'add':'A',...} -> 'AAAAB'"""
    if isinstance(g, dict):
        if 'grades' in g:
            g = g['grades']
        return ''.join(str(g.get(k, '?'))[:1] for k in ('add', 'crucial', 'pictures', 'modes', 'look'))
    return str(g or '')


def collect(base):
    pages = {}
    final = base / 'final' / 'status.json'
    for st in ([final] if final.exists() else sorted(base.glob('*/status.json'))):
        try:
            s = json.loads(st.read_text(encoding='utf-8'))
        except Exception as e:
            print('bad status', st, e)
            continue
        for page, v in (s.get('pages') or {}).items():
            pages[page] = dict(v, group=st.parent.name)
    return pages


def grade_cell(look):
    if not look:
        return '<span class="g none">not run</span>'
    gr = look.get('grades') or {}
    out = []
    for k, label in JUDGES:
        g = letters(gr.get(k))
        cls = 'a' if g and set(g) == {'A'} else ('fail' if not g or '?' in g else 'b')
        out.append(f'<span class="g {cls}" title="{label}: add · crucial · pictures · modes · look">'
                   f'<i>{label}</i><b>{html.escape(g or "—")}</b></span>')
    done = '<span class="chip ok">all A</span>' if look.get('done') else '<span class="chip warn">not all A</span>'
    rnd = f'<span class="rnd">{"final" if look.get("round") == "final" else "round " + str(look.get("round", "?"))}</span>'
    return done + rnd + ''.join(out)


def build(base, artifact=None):
    OUT.mkdir(parents=True, exist_ok=True)
    st = collect(base)
    rows, totals = [], [0, 0]
    for page in PAGES:
        info = st.get(page, {})
        dirs = {'before': base / 'before', 'flat': Path(info.get('final_dir_flat', '') or '-'),
                'kurz': Path(info.get('final_dir_kurz', '') or '-')}
        for k, d in dirs.items():
            if not d.is_absolute():
                dirs[k] = base / d if str(d) != '-' else d
        for k, d in dirs.items():
            for t, dv in MODES:
                src = d / f'{page}-{t}-{dv}.png'
                if src.exists():
                    shrink(src, OUT / f'{page}-{k}-{t}-{dv}.jpg')
        wb, wa = words(dirs['before'], page), words(dirs['flat'], page)
        if wb and wa:
            totals[0] += wb; totals[1] += wa
        cut = f'{round(100 * (1 - wa / wb))}% fewer' if wb and wa else 'no after capture'
        cols = []
        for k, label in STATES:
            have = (OUT / f'{page}-{k}-light-desktop.jpg').exists()
            img = (f'<img loading="lazy" data-page="{page}" data-state="{k}" src="deword/{page}-{k}-light-desktop.jpg" '
                   f'alt="{html.escape(NAMES.get(page, page))}, {label}">' if have else '<div class="miss">not built</div>')
            cols.append(f'<figure><figcaption>{label}</figcaption>{img}</figure>')
        rows.append(f'''<section class="row" id="{page}">
<header><h2>{html.escape(NAMES.get(page, page))}</h2>
<div class="words"><b>{wb or "—"}</b><span>→</span><b class="after">{wa or "—"}</b><small>words · {cut}</small></div></header>
<div class="grades"><div><span class="lk">A</span>{grade_cell(info.get('flat'))}</div><div><span class="lk b">B</span>{grade_cell(info.get('kurz'))}</div></div>
<div class="shots">{''.join(cols)}</div></section>''')
    summary = (f'<div class="total"><b>{totals[0]:,}</b><span>→</span><b class="after">{totals[1]:,}</b>'
               f'<small>words on the {len(PAGES)} pages</small></div>') if totals[0] else ''
    body = TEMPLATE.replace('%SUMMARY%', summary).replace('%ROWS%', '\n'.join(rows))
    (ROOT / 'docs' / 'deword-gallery.html').write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        + body.replace('</style>', '</style></head><body>', 1) + '</body></html>', encoding='utf-8')
    if artifact:
        Path(artifact).write_text(body, encoding='utf-8')
    print('gallery:', len(rows), 'rows,', len(list(OUT.glob('*.jpg'))), 'images')


TEMPLATE = r'''<title>De-word Gallery</title>
<style>
/* Layout: one row per page; before | A | B side by side; switches pick Light/Dark and Desktop/Phone for every row. */
:root{--bg:#F5F2EA;--card:#FBF9F2;--ink:#1E2A22;--muted:#6E7A6B;--line:#C9C5B4;--accent:#3E5C4B;--warm:#B9631F;
--ok:#3E5C4B;--okf:#E4E8DA;--warn:#7A5A1E;--warnf:#EFE4CB;--bad:#7E3A28;--badf:#EDDCD4;--navy:#14204A;
--serif:"Iowan Old Style",Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141D1A;--card:#1B2621;--ink:#E7EDE6;--muted:#9FAEA3;--line:#2E3D36;
--accent:#8FC3A3;--warm:#E8A266;--ok:#8FC3A3;--okf:#22362B;--warn:#F0C070;--warnf:#3A2E17;--bad:#F09080;--badf:#3D2420;--navy:#A9B6E0;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141D1A;--card:#1B2621;--ink:#E7EDE6;--muted:#9FAEA3;--line:#2E3D36;--accent:#8FC3A3;--warm:#E8A266;
--ok:#8FC3A3;--okf:#22362B;--warn:#F0C070;--warnf:#3A2E17;--bad:#F09080;--badf:#3D2420;--navy:#A9B6E0;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:14px/1.45 var(--sans);margin:0}
.wrap{max-width:1180px;margin:0 auto;padding-inline:16px;padding-block:20px 60px}
h1{font:600 34px/1.1 var(--serif);margin:0 0 4px;text-wrap:balance}
.sub{color:var(--muted);margin:0 0 14px}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 0;background:var(--bg);border-bottom:1px solid var(--line)}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}
.seg button{border:0;background:transparent;color:var(--ink);padding:6px 12px;font:600 13px var(--sans);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--bg)}
.seg button:focus-visible{outline:2px solid var(--warm);outline-offset:-2px}
.total,.words{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.total b{font:600 30px/1 var(--serif);font-variant-numeric:tabular-nums}.total{margin:6px 0 12px}
.words b{font:600 22px/1 var(--serif);font-variant-numeric:tabular-nums}
.after{color:var(--accent)}small{color:var(--muted)}
.row{padding-block:18px;border-bottom:1px solid var(--line)}
.row header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:baseline}
.row h2{font:600 22px/1.2 var(--serif);margin:0}
.grades{display:grid;gap:6px;margin:8px 0 10px}
.grades>div{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.lk{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:6px;background:var(--accent);color:var(--bg);font-weight:700}
.lk.b{background:var(--navy);color:var(--bg)}
.g{display:inline-flex;gap:6px;align-items:center;padding:2px 8px;border-radius:999px;border:1px solid var(--line);font-size:12px}
.g i{font-style:normal;color:var(--muted)}.g b{font-family:var(--sans);letter-spacing:.08em;font-variant-numeric:tabular-nums}
.g.a{background:var(--okf);border-color:transparent}.g.a b{color:var(--ok)}
.g.b b{color:var(--warn)}.g.fail{background:var(--badf);border-color:transparent}.g.fail b{color:var(--bad)}
.g.none{color:var(--muted)}
.chip{padding:2px 9px;border-radius:999px;font:700 12px var(--sans)}.chip.ok{background:var(--okf);color:var(--ok)}.chip.warn{background:var(--warnf);color:var(--warn)}
.rnd{font-size:12px;color:var(--muted)}
.shots{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.phone .shots{grid-template-columns:repeat(3,minmax(0,200px))}
figure{margin:0;min-width:0}figcaption{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
figure img{display:block;width:100%;height:auto;max-height:620px;object-fit:cover;object-position:top;border:1px solid var(--line);border-radius:8px;background:var(--card);cursor:zoom-in}
.miss{display:grid;place-items:center;height:160px;border:1px dashed var(--line);border-radius:8px;color:var(--muted)}
.lb{position:fixed;inset:0;z-index:20;background:rgb(0 0 0 / .86);display:flex;flex-direction:column}
.lb[hidden]{display:none}
.lb-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:calc(10px + env(safe-area-inset-top,0px)) 16px 10px;color:#fff}
.lb-bar b{font:600 16px var(--sans)}
.lb-bar .seg{border-color:rgb(255 255 255 / .35)}.lb-bar .seg button{color:#fff}
.lb-bar .seg button[aria-pressed="true"]{background:#fff;color:#111}
.lb-close{border:0;border-radius:999px;background:#fff;color:#111;font:700 14px var(--sans);padding:7px 14px;cursor:pointer}
.lb-scroll{flex:1;overflow:auto;padding:0 16px calc(16px + env(safe-area-inset-bottom,0px));text-align:center}
.lb-scroll img{display:inline-block;max-width:100%;height:auto;border-radius:6px;background:#fff}
.lb-scroll.full img{max-width:none}
.lb-hint{font-size:12px;opacity:.75}
@media (max-width:700px){.shots,.phone .shots{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}h1{font-size:28px}}
@media (prefers-reduced-motion:no-preference){figure img{transition:opacity .15s}}
</style>
<div class="wrap">
<h1>De-word gallery</h1>
<p class="sub">Preview branch <b>claude/deword-overnight</b> · nothing is live. Grades: add · crucial · pictures · modes · look.</p>
%SUMMARY%
<div class="bar" role="toolbar" aria-label="Screenshot view">
<div class="seg" data-k="theme"><button id="sw-light" data-v="light" aria-pressed="true">Light</button><button id="sw-dark" data-v="dark" aria-pressed="false">Dark</button></div>
<div class="seg" data-k="dev"><button id="sw-desk" data-v="desktop" aria-pressed="true">Desktop</button><button id="sw-phone" data-v="phone" aria-pressed="false">Phone</button></div>
</div>
%ROWS%
</div>
<div class="lb" id="lb" hidden role="dialog" aria-modal="true" aria-labelledby="lb-title">
<div class="lb-bar"><b id="lb-title"></b>
<div class="seg" id="lb-state"><button id="lb-before" data-v="before">Before</button><button id="lb-flat" data-v="flat">Look A</button><button id="lb-kurz" data-v="kurz">Look B</button></div>
<span class="lb-hint">tap picture = full size · ← → switch</span><button class="lb-close" id="lb-close">Close</button></div>
<div class="lb-scroll" id="lb-scroll"><img id="lb-img" alt=""></div></div>
<script>
(function(){var s={theme:'light',dev:'desktop'};
function paint(){document.body.classList.toggle('phone',s.dev==='phone');
document.querySelectorAll('img[data-page]').forEach(function(i){i.src='deword/'+i.dataset.page+'-'+i.dataset.state+'-'+s.theme+'-'+s.dev+'.jpg';});}
document.querySelectorAll('.seg').forEach(function(g){g.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
s[g.dataset.k]=b.dataset.v;g.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',String(x===b));});paint();});});
var lb=document.getElementById('lb'),li=document.getElementById('lb-img'),lt=document.getElementById('lb-title'),ls=document.getElementById('lb-scroll'),cur=null;
var NAMES={before:'Before',flat:'Look A',kurz:'Look B'};
function show(){li.src=SRC(cur.page,cur.state);li.alt=cur.title+', '+NAMES[cur.state];lt.textContent=cur.title;
document.querySelectorAll('#lb-state button').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.v===cur.state));});}
function SRC(p,st){return (typeof IMG!=='undefined'?IMG[p+'-'+st+'-'+s.theme+'-'+s.dev]:'deword/'+p+'-'+st+'-'+s.theme+'-'+s.dev+'.jpg')||'';}
document.addEventListener('click',function(e){var i=e.target.closest('figure img');if(!i)return;
cur={page:i.dataset.page,state:i.dataset.state,title:i.closest('.row').querySelector('h2').textContent};ls.classList.remove('full');show();lb.hidden=false;ls.scrollTop=0;document.getElementById('lb-close').focus();});
document.getElementById('lb-state').addEventListener('click',function(e){var b=e.target.closest('button');if(b){cur.state=b.dataset.v;show();}});
document.getElementById('lb-close').addEventListener('click',function(){lb.hidden=true;});
li.addEventListener('click',function(){ls.classList.toggle('full');});
document.addEventListener('keydown',function(e){if(lb.hidden)return;if(e.key==='Escape')lb.hidden=true;
var o=['before','flat','kurz'],k=o.indexOf(cur.state);if(e.key==='ArrowRight'){cur.state=o[(k+1)%3];show();}if(e.key==='ArrowLeft'){cur.state=o[(k+2)%3];show();}});
})();
</script>
'''

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('--artifact')
    a = ap.parse_args()
    build(Path(a.base), a.artifact)
