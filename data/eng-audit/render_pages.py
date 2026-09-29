# -*- coding: utf-8 -*-
"""Area 9 (page health) headless sweep, 2026-09-29 engineering audit.

Renders every published page (docs/*.html, docs/lessons/*.html, docs/reports/*.html, docs/amal/*.html) from a local
server at 375 px in four theme set-ups and records, per page x mode:
  - same-origin requests that failed (404 / network) -> broken links to data, scripts, styles, audio
  - console errors
  - horizontal scroll at 375 px (scrollWidth > 375)
  - "blank" values: visible elements whose own text is NaN / undefined / null / Infinity / [object Object], and
    elements whose whole text is a bare dash (candidates for "a dash where a number belongs"; judged by hand)
  - text contrast: visible text whose colour vs. its effective background is under 3:1 (under 1.5:1 = invisible)
  - audio: every <audio>/<source> src on the page is fetched (HEAD); a missing one is fed an 'error' event so
    js/clip-fallback.js can swap in the full-lesson recording, and the swapped URL is fetched too.
Writes data/eng-audit/page-health.json and a few screenshots under data/eng-audit/screens/.

    python -m http.server 8796 -d docs      # in another shell
    python data/eng-audit/render_pages.py [--base http://127.0.0.1:8796] [--only progress.html,...]
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs'
OUT = ROOT / 'data' / 'eng-audit'
SHOTS = OUT / 'screens'

MODES = {                     # name -> (OS colour scheme, stored theme toggle or None)
    'light': ('light', None),
    'dark': ('dark', None),
    'toggle-dark': ('light', 'dark'),
    'toggle-light': ('dark', 'light'),
}

PROBE = r"""
async () => {
  const out = {blank: [], dash: [], lowContrast: [], invisible: [], audio: []};
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05; };
  const own = el => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
  const path = el => { const p = []; for (let e = el; e && e !== document.body && p.length < 4; e = e.parentElement)
      p.unshift(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].slice(0, 2).join('.') : '')); return p.join('>'); };
  const rgb = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1}; };
  const lum = c => { const f = x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const bgOf = el => { let layers = []; for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none' && !s.backgroundImage.startsWith('url')) return null;   // gradient: skip
      const c = rgb(s.backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) break; } }
    let base = {r: 255, g: 255, b: 255};
    const html = rgb(getComputedStyle(document.documentElement).backgroundColor); if (html && html.a > 0.99 && !layers.some(l => l.a >= 0.99)) base = html;
    for (const l of layers.reverse()) base = {r: l.r * l.a + base.r * (1 - l.a), g: l.g * l.a + base.g * (1 - l.a), b: l.b * l.a + base.b * (1 - l.a)};
    return base; };
  const BAD = /^(NaN|undefined|null|Infinity|-Infinity|\[object Object\])$|\bNaN\b|\bundefined\b|\[object Object\]/;
  for (const el of document.querySelectorAll('body *')) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'CODE', 'PRE', 'TEXTAREA'].includes(el.tagName)) continue;
    const t = own(el); if (!t) continue; if (!vis(el)) continue;
    if (BAD.test(t) && t.length < 200) out.blank.push({at: path(el), text: t.slice(0, 120)});
    if (/^[—–-]$/.test(t) || /^[—–-]\s*%$/.test(t)) out.dash.push({at: path(el), ctx: (el.parentElement ? el.parentElement.innerText : '').replace(/\s+/g, ' ').slice(0, 90)});
    const s = getComputedStyle(el); const fg = rgb(s.color); const bg = bgOf(el);
    if (fg && bg && /[\p{L}\p{N}]/u.test(t)) { const f = {r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a)};
      const L1 = lum(f), L2 = lum(bg), cr = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const rec = {at: path(el), text: t.slice(0, 50), ratio: +cr.toFixed(2), fg: s.color, bg: `rgb(${bg.r|0},${bg.g|0},${bg.b|0})`, size: s.fontSize};
      if (cr < 1.5) out.invisible.push(rec); else if (cr < 3) out.lowContrast.push(rec); }
  }
  const srcs = new Set();
  document.querySelectorAll('audio').forEach(a => { const s = a.getAttribute('src'); if (s) srcs.add(a); a.querySelectorAll('source').forEach(x => x.getAttribute('src') && srcs.add(a)); });
  const ok = async u => { try { const r = await fetch(u, {method: 'HEAD'}); return r.ok; } catch (e) { return false; } };
  let n = 0;
  for (const a of srcs) { if (n++ >= 60) break;
    const raw = a.getAttribute('src') || (a.querySelector('source') || {}).getAttribute?.('src') || '';
    if (/^(blob|data):/.test(raw)) continue;
    const abs = new URL(raw, location.href).href.split('#')[0];
    const rec = {src: raw, ok: await ok(abs)};
    if (!rec.ok) {
      rec.fallbackLoaded = !!window.AneesClipFallback; rec.hasMoment = !!(a.dataset.t || a.dataset.mmss);
      a.dispatchEvent(new Event('error'));
      await new Promise(r => setTimeout(r, 50));
      const now = a.getAttribute('src') || '';
      rec.after = now !== raw ? now : null;
      if (rec.after) { rec.afterOk = await ok(new URL(now, location.href).href.split('#')[0]);
        if (!rec.afterOk) { a.dispatchEvent(new Event('error')); await new Promise(r => setTimeout(r, 50)); const n2 = a.getAttribute('src') || '';
          if (n2 !== now) { rec.after2 = n2; rec.after2Ok = await ok(new URL(n2, location.href).href.split('#')[0]); } } }
    }
    out.audio.push(rec); }
  out.scrollWidth = document.documentElement.scrollWidth;
  out.bodyText = document.body.innerText.length;
  return out;
}
"""


def pages(only=None):
    ps = []
    for pat in ('*.html', 'lessons/*.html', 'reports/*.html', 'amal/*.html'):
        ps += sorted(p.relative_to(DOCS).as_posix() for p in DOCS.glob(pat))
    return [p for p in ps if not only or p in only]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8796')
    ap.add_argument('--only', default='')
    ap.add_argument('--modes', default=','.join(MODES))
    ap.add_argument('--shots', default='progress.html,lessons.html,grammar.html,word-bank.html,tutor.html,cards.html,ai-reports.html,settings.html')
    a = ap.parse_args(argv)
    only = set(x for x in a.only.split(',') if x)
    shots = set(a.shots.split(','))
    from playwright.sync_api import sync_playwright
    SHOTS.mkdir(parents=True, exist_ok=True)
    res = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for mode in a.modes.split(','):
            scheme, toggle = MODES[mode]
            ctx = b.new_context(viewport={'width': 375, 'height': 812}, color_scheme=scheme, device_scale_factor=1)
            if toggle:
                ctx.add_init_script(f"try{{localStorage.setItem('anees-theme','{toggle}')}}catch(e){{}}")
            for p in pages(only):
                pg = ctx.new_page()
                failed, errors = [], []
                pg.on('response', lambda r, f=failed: f.append(f'{r.status} {r.url}') if r.status >= 400 and r.url.startswith(a.base) else None)
                pg.on('requestfailed', lambda r, f=failed: f.append(f'FAILED {r.url} {r.failure}') if r.url.startswith(a.base) and not r.url.split('#')[0].endswith(('.mp3', '.m4a')) else None)
                pg.on('console', lambda m, e=errors: e.append(m.text[:200]) if m.type == 'error' else None)
                pg.on('pageerror', lambda ex, e=errors: e.append('PAGEERROR ' + str(ex)[:200]))
                t0 = time.time()
                try:
                    pg.goto(f'{a.base}/{p}', wait_until='load', timeout=45000)
                    try:
                        pg.wait_for_load_state('networkidle', timeout=15000)
                    except Exception:
                        pass
                    pg.wait_for_timeout(800)
                    r = pg.evaluate(PROBE)
                    if mode in ('light', 'dark') and p in shots:
                        pg.screenshot(path=str(SHOTS / f"{p.replace('/', '_').replace('.html', '')}-{mode}-375.png"), full_page=False)
                except Exception as ex:
                    r = {'error': str(ex)[:300]}
                r.update(failed=sorted(set(failed)), console=errors[:20], secs=round(time.time() - t0, 1))
                res.setdefault(p, {})[mode] = r
                pg.close()
                print(mode, p, 'fail', len(failed), 'err', len(errors), 'sw', r.get('scrollWidth'), 'blank', len(r.get('blank', [])),
                      'dash', len(r.get('dash', [])), 'low', len(r.get('lowContrast', [])), 'inv', len(r.get('invisible', [])), flush=True)
            ctx.close()
        b.close()
    out = OUT / ('page-health.json' if not only else 'page-health-partial.json')
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('wrote', out)


if __name__ == '__main__':
    main()
