# -*- coding: utf-8 -*-
"""Page health, rendered (engineering audit 2026-09-29, area 9): pages fixed in the audit stay readable at phone width
in light and dark. Offline: a local server on a random port serves docs/; nothing leaves the machine except what a
page itself fetches (Supabase for a few pages; the checks below do not depend on it).

Each (page, theme) must have: no text under 3:1 contrast against its background (under 1.5:1 = invisible), and no
sideways scroll at 375 px. The theme is set the way Medi sets it: OS preference, or the Light/Dark switch
(localStorage 'anees-theme'), which beats the OS.
"""
import functools, http.server, threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
pw_mod = pytest.importorskip('playwright.sync_api')

PAGES = ['speaking-audit.html', 'word-bank-audit.html', 'homework.html', 'slips.html', 'check02-amal.html', 'check03.html',
         'legacy-words.html', 'cards.html', 'progress.html', 'ai-reports.html',
         'lessons/2026-08-25.html', 'lessons/2026-08-25-report.html', 'lessons/2026-09-11-report.html',
         'reports/ai-process-review-2026-09-27.html']
MODES = {'light': ('light', None), 'dark': ('dark', None), 'switch-dark': ('light', 'dark'), 'switch-light': ('dark', 'light')}

PROBE = r"""() => {
  const rgb = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1}; };
  const lum = c => { const f = x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const bgOf = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none' && !s.backgroundImage.startsWith('url')) return null;
      const c = rgb(s.backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) break; } }
    let base = {r: 255, g: 255, b: 255}; const html = rgb(getComputedStyle(document.documentElement).backgroundColor);
    if (html && html.a > 0.99 && !layers.some(l => l.a >= 0.99)) base = html;
    for (const l of layers.reverse()) base = {r: l.r * l.a + base.r * (1 - l.a), g: l.g * l.a + base.g * (1 - l.a), b: l.b * l.a + base.b * (1 - l.a)};
    return base; };
  const bad = [];
  for (const el of document.querySelectorAll('body *')) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
    const t = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!t || !/[\p{L}\p{N}]/u.test(t)) continue;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (!(r.width > 0 && r.height > 0) || s.visibility === 'hidden' || +s.opacity <= 0.05) continue;
    const fg = rgb(s.color), bg = bgOf(el); if (!fg || !bg) continue;
    const f = {r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a)};
    const L1 = lum(f), L2 = lum(bg), cr = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    if (cr < 3) bad.push(`${el.tagName.toLowerCase()}.${[...el.classList].join('.')} "${t.slice(0, 30)}" ${cr.toFixed(2)}:1 (${s.color} on rgb(${bg.r|0},${bg.g|0},${bg.b|0}))`);
  }
  return {bad, sw: document.documentElement.scrollWidth};
}"""


@pytest.fixture(scope='module')
def site():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    h.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with pw_mod.sync_playwright() as pw:
        b = pw.chromium.launch()
        yield srv.server_address[1], b
        b.close()
    srv.shutdown()


@pytest.mark.parametrize('mode', list(MODES))
@pytest.mark.parametrize('page', PAGES)
def test_page_readable_at_phone_width(site, page, mode):
    port, b = site
    scheme, switch = MODES[mode]
    ctx = b.new_context(viewport={'width': 375, 'height': 812}, color_scheme=scheme)
    if switch:
        ctx.add_init_script(f"try{{localStorage.setItem('anees-theme','{switch}')}}catch(e){{}}")
    pg = ctx.new_page()
    pg.goto(f'http://127.0.0.1:{port}/{page}', wait_until='load')
    try:
        pg.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass
    pg.wait_for_timeout(500)
    r = pg.evaluate(PROBE)
    ctx.close()
    assert r['sw'] <= 375, f'{page} [{mode}] scrolls sideways at 375 px (content is {r["sw"]} px wide)'
    assert not r['bad'], f'{page} [{mode}] {len(r["bad"])} hard-to-read text: ' + ' | '.join(r['bad'][:4])
