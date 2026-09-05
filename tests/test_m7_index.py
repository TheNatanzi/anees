"""M7 gate: every tab reachable in <= 2 taps; dark/light; no dead links (crawler); loads with Supabase down (cached data + banner);
Words search: 20 queries (10 Medi misspellings, 5 English, 5 Arabic) -> top 3, each < 100 ms; every row shows a bucket and a
last-reviewed value or 'never'; JS Arabizi normalisation == Python. Lighthouse mobile >= 80 is run by scripts/lighthouse.ps1 and
pasted in the log (skipped here when the CLI is missing)."""
import io, json, re, subprocess
from pathlib import Path
import pytest

import arabizi
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
NET = bool(E.ANON_KEY)
QUERIES = [('mabsoot', 'mabsU6'), ('khalas', '5alas'), ('ba3dain', 'ba3dain'), ('kteer', 'ktIr'), ('yaani', 'ya3ni'), ('shukran', 'shukran'),
           ('ankabut', '3ankabUt'), ('sabah el kheir', 'sabah al5eir'), ('mnih', 'mnIh'), ('tariqa', 'tari2a'),
           ('happy', 'mabsU6'), ('spider', '3ankabUt'), ('thank you', 'shukran'), ('later', 'ba3dain'), ('weather', 'jaw'),
           ('مبسوط', 'mabsU6'), ('شكرا', 'shukran'), ('كتير', 'ktIr'), ('بعدين', 'ba3dain'), ('عنكبوت', '3ankabUt')]


def test_js_normalisation_matches_python():
    forms = ['Mabsoo6', "tesbah 'ala kheir", 'El-jaw', 'Ana ba5aaf', 'ghayr', 'Sabah Alkheir', 'kateer', 'Qaleel', '3ankaboot', 'Ma6aar', 'Halla', 'Kelme', 'ya3ni',
             'Btenbese6i', 'Enbasa6u', 'huwwe saa2', 'Basee6a', 'Shu8ul', 'mneeh', 'akhui']
    js = "require('./arabizi.js'); const A=globalThis.AneesArabizi; const f=%s; console.log(JSON.stringify(f.map(x=>[A.loose(x),A.fold(x),A.short(x),A.skeleton(x)])));" % json.dumps(forms)
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, cwd=str(DOCS / 'js'), encoding='utf-8')
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    for f, got in zip(forms, out):
        assert got == [arabizi.loose(f), arabizi.fold(f), arabizi.short(f), arabizi.skeleton(f)], (f, got)


def test_no_dead_links():
    import requests
    seen_http = {}
    for p in DOCS.rglob('*.html'):
        html = re.sub(r'<script.*?</script>', '', p.read_text(encoding='utf-8'), flags=re.S)     # markup only, not JS templates
        for m in re.finditer(r'(?:href|src)="([^"#][^"]*)"', html):
            u = m.group(1)
            if u.startswith('javascript:') or u.startswith('data:'):
                continue
            if u.startswith('http'):
                if 'supabase.co' in u or u in seen_http:
                    continue
                try:
                    seen_http[u] = requests.head(u, timeout=15, allow_redirects=True).status_code
                except requests.RequestException as e:
                    seen_http[u] = str(e)
                assert seen_http[u] in (200, 301, 302), (p.name, u, seen_http[u])
            else:
                target = (p.parent / u.split('?')[0]).resolve()
                assert target.exists(), (p.name, u)


def test_tabs_dark_light_and_search_speed():
    from playwright.sync_api import sync_playwright
    url = (DOCS / 'index.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files']); pg = b.new_page(viewport={'width': 375, 'height': 812}); pg.goto(url)
        pg.wait_for_function('AneesIndex.words.length > 2000', timeout=30000)
        for tab in ['today', 'lessons', 'words', 'cards', 'amal', 'grammar', 'future']:
            pg.click(f'.tab[data-tab="{tab}"]')                       # 1 tap from anywhere
            assert pg.evaluate(f"document.getElementById('tab-{tab}').classList.contains('on')")
            assert pg.evaluate('document.documentElement.scrollWidth') <= 375
        light = pg.evaluate('getComputedStyle(document.body).backgroundColor'); pg.emulate_media(color_scheme='dark')
        assert pg.evaluate('getComputedStyle(document.body).backgroundColor') != light
        pg.click('.tab[data-tab="words"]')
        # every row shows a bucket badge and a last-reviewed value or 'never'
        pg.fill('#q', ''); pg.wait_for_timeout(200)
        rows = pg.evaluate("[...document.querySelectorAll('.wrow')].map(r=>[!!r.querySelector('.badge'), r.querySelector('.last').textContent])")
        assert rows and all(bad and (last == 'never' or re.match(r'\d{4}-\d{2}-\d{2}', last)) for bad, last in rows), rows[:5]
        # 20 queries, top 3, each under 100 ms (measured in the page)
        res = pg.evaluate("""(qs)=>qs.map(([q,k])=>{ const t=performance.now(); const r=AneesIndex.search(q).slice(0,3).map(w=>w.key); return [q,k,r,performance.now()-t]; })""", QUERIES)
        bad = [x for x in res if x[1] not in x[2] or x[3] >= 100]
        assert not bad, bad
        print('search:', [(q, round(ms, 1)) for q, k, r, ms in res])
        b.close()


def test_loads_with_supabase_down():
    """Served over http like GitHub Pages (a file:// fetch of data/words.json is blocked by Chromium)."""
    import threading, http.server, functools, socket
    from playwright.sync_api import sync_playwright
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{port}/index.html'
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files']); ctx = b.new_context(viewport={'width': 375, 'height': 812})
        ctx.route(re.compile(r'.*supabase\.co.*'), lambda route: route.abort())
        pg = ctx.new_page(); pg.goto(url)
        pg.wait_for_function('AneesIndex.offline === true', timeout=30000)
        assert pg.evaluate("document.getElementById('banner').classList.contains('on')")
        assert pg.evaluate('AneesIndex.words.length') >= 2000
        pg.click('.tab[data-tab="words"]'); pg.fill('#q', 'mabsoot'); pg.wait_for_timeout(200)
        assert pg.evaluate("document.querySelectorAll('.wrow').length") >= 1
        b.close()
