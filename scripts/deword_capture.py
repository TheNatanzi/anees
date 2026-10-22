# -*- coding: utf-8 -*-
"""De-word overnight (plan/OVERNIGHT-DEWORD-2026-10-22.md): capture every page the job touches.

    python scripts/deword_capture.py <out_dir> [--pages progress,tutor] [--look flat|kurz] [--no-shots]
    python scripts/deword_capture.py <after_dir> --compare <before_dir> [--pages ...]   # number check

For each page: serve docs/ locally, load it in Playwright, click through every tab, and save
  <page>.numbers.json  every number token on the page per tab (page text, scripts/styles removed)
  <page>.words.json    visible word count per tab
  <page>-<light|dark>-<desktop|phone>.png  default tab, top 2400 px
Outside requests are blocked, except GET reads of the app's own Supabase rows (no writes).
Nothing is sent anywhere.
"""
import argparse, functools, http.server, json, os, re, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'

PAGES = {
    'progress': 'progress.html', 'ai-reports': 'ai-reports.html', 'flow': 'reports/anees-flow.html',
    'lessons': 'lessons.html', 'lesson': 'lessons/2026-10-14.html', 'word-bank': 'word-bank.html',
    'grammar': 'grammar.html', 'cards': 'cards.html', 'student': 'student.html', 'homework': 'homework.html',
    'tutor': 'tutor.html', 'amal-grammar-rules': 'amal/grammar-rules.html', 'amal-materials': 'amal/materials.html',
    'big-picture': 'big-picture.html', 'settings': 'settings.html',
}
TABS = '[role=tab], .vp-tab, [data-artab]'
CONFIGS = [('light', 'desktop', 1280, 900), ('dark', 'desktop', 1280, 900),
           ('light', 'phone', 390, 844), ('dark', 'phone', 390, 844)]
NUM = re.compile(r'\d[\d,.:%/]*\d%?|\d%?')

TEXT_JS = """() => { const c = document.body.cloneNode(true);
  c.querySelectorAll('script,style,noscript,template').forEach(e => e.remove());
  return {all: c.textContent, vis: document.body.innerText}; }"""


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def tokens(text):
    return sorted(set(t.rstrip('.,:/') for t in NUM.findall(text or '') if t.rstrip('.,:/')))


def words(text):
    return len(re.findall(r"[A-Za-z؀-ۿ][\w'؀-ۿ-]*", text or ''))


SUPA = 'https://yljcbdxvnkfrwvelypfu.supabase.co/'


def _outside(route):
    # Live rows (Big Picture ideas, card sets, homework) come from Supabase: let the page READ them (GET only),
    # so a page is not judged on an empty "Offline" state. Every write (POST/PATCH/DELETE) and every other host is blocked.
    r = route.request
    if r.url.startswith(SUPA) and r.method in ('GET', 'HEAD', 'OPTIONS') and not os.environ.get('DEWORD_OFFLINE'):
        return route.continue_()
    return route.abort()


def open_page(ctx, url, look, theme):
    p = ctx.new_page()
    js = f"try{{localStorage.setItem('anees-theme','{theme}');"
    if look:
        js += f"localStorage.setItem('anees-look','{look}');"
    p.add_init_script(js + "}catch(e){}")
    p.route(re.compile(r'^https?://(?!127\.0\.0\.1).*'), _outside)
    p.goto(url, wait_until='load', timeout=60000)
    try:
        p.wait_for_load_state('networkidle', timeout=60000)
        # pages that hold their content until the live rows arrive (Progress: #vp-content)
        p.wait_for_function("!document.getElementById('vp-content') || !document.getElementById('vp-content').hidden", timeout=60000)
    except Exception:
        pass
    p.wait_for_timeout(1200)
    return p


def capture(out, names, look, shots):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    srv = serve()
    base = f'http://127.0.0.1:{srv.server_address[1]}/'
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name in names:
            url = base + PAGES[name]
            ctx = b.new_context(viewport={'width': 1280, 'height': 900}, color_scheme='light')
            p = open_page(ctx, url, look, 'light')
            per, wc, texts = {}, {}, {}
            t = p.evaluate(TEXT_JS)
            per['default'], wc['default'], texts['default'] = tokens(t['all']), words(t['vis']), t['vis']
            n = p.locator(TABS).count()
            for i in range(n):
                el = p.locator(TABS).nth(i)
                try:
                    if not el.is_visible():
                        continue
                    label = (el.inner_text() or f'tab{i}').strip()[:40] or f'tab{i}'
                    el.click(timeout=3000)
                    try:  # a tab may fetch its own live rows (slow Supabase days: 10-30 s)
                        p.wait_for_load_state('networkidle', timeout=45000)
                    except Exception:
                        pass
                    p.wait_for_timeout(900)
                    t = p.evaluate(TEXT_JS)
                    per[label], wc[label], texts[label] = tokens(t['all']), words(t['vis']), t['vis']
                except Exception as e:
                    per[f'tab{i}-error'] = [str(e)[:80]]
            ctx.close()
            (out / f'{name}.numbers.json').write_text(json.dumps(per, ensure_ascii=False), encoding='utf-8')
            (out / f'{name}.words.json').write_text(json.dumps(wc, ensure_ascii=False), encoding='utf-8')
            (out / f'{name}.text.txt').write_text('\n\n=== TAB ===\n'.join(f'[{k}]\n{v}' for k, v in texts.items()),
                                                   encoding='utf-8')
            if shots:
                for theme, dev, w, h in CONFIGS:
                    ctx = b.new_context(viewport={'width': w, 'height': h}, color_scheme=theme,
                                        is_mobile=(dev == 'phone'), has_touch=(dev == 'phone'), device_scale_factor=1)
                    p = open_page(ctx, url, look, theme)
                    if dev == 'phone':
                        # A full-page shot paints position:fixed bars in the middle of the page (over rows that a
                        # real phone scrolls past). Hide the phone menu bar for the still; the judges are told.
                        p.add_style_tag(content='.pn-bar{display:none!important}')
                    full = p.evaluate('document.documentElement.scrollHeight')
                    p.screenshot(path=str(out / f'{name}-{theme}-{dev}.png'), full_page=True,
                                 clip={'x': 0, 'y': 0, 'width': w, 'height': min(full, 2400)})
                    ctx.close()
            print(name, 'words', sum(wc.values()), 'tabs', len(per) - 1, flush=True)
        b.close()
    srv.shutdown()


def compare(before, after, names):
    """Every number on a page before must still be on it after (any tab). Returns {page: [missing]}."""
    bad = {}
    for name in names:
        b = json.loads((before / f'{name}.numbers.json').read_text(encoding='utf-8'))
        a = json.loads((after / f'{name}.numbers.json').read_text(encoding='utf-8'))
        have = set(x for v in a.values() for x in v)
        miss = sorted(set(x for k, v in b.items() if not k.endswith('-error') for x in v) - have)
        if miss:
            bad[name] = miss
    return bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--pages')
    ap.add_argument('--look')
    ap.add_argument('--no-shots', action='store_true')
    ap.add_argument('--compare', help='before dir: check numbers of <out> against it')
    a = ap.parse_args()
    names = a.pages.split(',') if a.pages else list(PAGES)
    if a.compare:
        bad = compare(Path(a.compare), Path(a.out), names)
        print(json.dumps(bad, ensure_ascii=False) if bad else 'numbers OK')
        sys.exit(1 if bad else 0)
    capture(Path(a.out), names, a.look, not a.no_shots)
