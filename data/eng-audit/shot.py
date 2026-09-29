"""Element screenshot helper: python data/eng-audit/shot.py <page> <mode light|dark|toggle-dark> <css selector> <out.png> [width] [clickSelector]"""
import sys
from playwright.sync_api import sync_playwright
page, mode, sel, out = sys.argv[1:5]
w = int(sys.argv[5]) if len(sys.argv) > 5 else 375
click = sys.argv[6] if len(sys.argv) > 6 else None
scheme = 'dark' if mode == 'dark' else 'light'
with sync_playwright() as pw:
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': w, 'height': 812}, color_scheme=scheme)
    if mode == 'toggle-dark':
        ctx.add_init_script("try{localStorage.setItem('anees-theme','dark')}catch(e){}")
    pg = ctx.new_page(); pg.goto('http://127.0.0.1:8796/' + page); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(800)
    if click:
        pg.click(click); pg.wait_for_timeout(800)
    el = pg.locator(sel).first
    el.scroll_into_view_if_needed(); el.screenshot(path=out)
    b.close()
