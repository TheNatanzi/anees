"""Out-of-date banner: a page stamped with build A shows a flashing Reload bar once data/build.json says build B."""
import io, json, re, threading, http.server, functools
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'


def test_every_page_carries_the_stamp_and_checker():
    for p in ['index.html', 'cards.html', 'amal/plan.html', 'amal/after.html', 'lessons/2026-09-04-report.html', 'lessons/2026-09-04.html']:
        s = (DOCS / p).read_text(encoding='utf-8')
        assert 'js/build.js' in s and 'js/stale.js' in s, p
    b = (DOCS / 'js' / 'build.js').read_text(encoding='utf-8')
    j = json.load(io.open(DOCS / 'data' / 'build.json', encoding='utf-8'))
    assert j['build'] in b


def test_banner_appears_when_build_changes(tmp_path):
    from playwright.sync_api import sync_playwright
    import shutil
    site = tmp_path / 'docs'
    shutil.copytree(DOCS, site, ignore=shutil.ignore_patterns('lessons', '_backups'))
    (site / 'lessons').mkdir()
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 375, 'height': 812})
        pg.goto(f'http://127.0.0.1:{port}/cards.html'); pg.wait_for_selector('#start', timeout=20000)
        assert pg.evaluate('AneesStale.check()') is not None and pg.locator('#stale-bar').count() == 0
        (site / 'data' / 'build.json').write_text('{"build": "20991231-000000-newer"}', encoding='utf-8')
        pg.evaluate('AneesStale.check()'); pg.wait_for_selector('#stale-bar', timeout=5000)
        txt = pg.text_content('#stale-bar')
        assert 'out of date' in txt and pg.locator('#stale-reload').count() == 1
        assert pg.evaluate("document.querySelector('#stale-reload').getBoundingClientRect().height") >= 44
        b.close()
