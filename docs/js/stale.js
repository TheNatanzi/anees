// Out-of-date banner. The page checks data/build.json every 60 s and when the tab comes back to the front; when the live
// stamp differs from the one this page LOADED WITH, a flashing bar says so.
// Fix 2026-09-26 (Medi: "it keeps telling me the version is out of date even though I keep refreshing"): the loaded-with
// stamp used to come from js/build.js, which GitHub Pages lets the browser cache for 10 minutes, so a refresh kept the
// old stamp and the bar came straight back. Now the stamp is read fresh (no-store) when the page opens; a refresh
// always clears the bar, and it only appears when a new version lands while the page is open.
// Silent-stall alarm (PG-01, Medi 2026-10-10 "MAKE A SYSTEM"): the hourly job could not publish for ~29 h and no page
// said so. data/pipeline-health.json (scripts/pipeline_health.py, written by the publish guard and the hourly job) says
// when the robot last published and why it is blocked; while it is stalled every page shows one line at the top:
// "The hourly robot has not published for N h: <reason>". The hours count on from last_publish_utc in the viewer's clock
// (a stalled robot cannot publish a new file). Fails quiet: no file or a bad file shows nothing.
function stallText(h, now) {
  if (!h || !h.last_publish_utc && !h.stalled) return null;
  const t = h.last_publish_utc ? new Date(h.last_publish_utc) : null;
  const live = t && !isNaN(t) ? ((now || new Date()) - t) / 3600000 : null;
  const hrs = Math.max(Number(h.hours_since_publish) || 0, live || 0);
  const waiting = (h.pending || []).length > 0;
  if (!(h.stalled || (waiting && hrs > 2))) return null;
  const why = String(h.plain_reason || h.last_block_reason || h.first_block_reason || (h.open_failures || []).join('; ') || ('waiting: ' + (h.pending || []).join('; ')))
    .replace(/\s+/g, ' ').trim();
  return 'The hourly robot has not published for ' + Math.round(hrs) + ' h: ' + (why.length > 220 ? why.slice(0, 217) + '...' : why);
}
if (typeof module !== 'undefined' && module.exports) module.exports = { stallText };
(function () {
  if (typeof window === 'undefined') return;
  let mine = '';                                   // set from a fresh read of data/build.json on load (see above)
  const base = (function () { const s = document.querySelector('script[src*="js/stale.js"]'); return s ? s.getAttribute('src').replace(/js\/stale\.js.*$/, '') : ''; })();
  if (!document.querySelector('script[src*="js/brand.js"]')) {
    const branding = document.createElement('script');
    branding.src = base + 'js/brand.js';
    document.head.appendChild(branding);
  }
  let bar = null;
  function show(theirs) {
    if (bar) return;
    bar = document.createElement('div');
    bar.id = 'stale-bar';
    bar.setAttribute('role', 'status');
    bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99;display:flex;gap:10px;align-items:center;justify-content:center;padding:10px 14px;background:#B26F0E;color:#fff;font:600 15px system-ui;animation:stale-flash 1.2s ease-in-out infinite';
    bar.innerHTML = 'This page is out of date (new version ' + String(theirs).slice(0, 12) + '). <button id="stale-reload" style="min-height:44px;border:0;border-radius:999px;padding:8px 16px;background:#fff;color:#7a4a05;font:600 15px system-ui;cursor:pointer">Reload</button>';
    const st = document.createElement('style');
    st.textContent = '@keyframes stale-flash{0%,100%{opacity:1}50%{opacity:.55}}';
    document.head.appendChild(st);
    document.body.appendChild(bar);
    // cache-busting reload: a new URL makes the browser fetch the page (and its versioned scripts) again
    document.getElementById('stale-reload').onclick = () => { const u = new URL(location.href); u.searchParams.set('v', String(theirs).slice(-7)); location.replace(u.toString()); };
  }
  async function check() {
    try {
      const r = await fetch(base + 'data/build.json?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return null;
      const j = await r.json();
      if (!mine) { mine = j.build || ''; return j.build; }        // first read = the version this page opened with
      if (mine && j.build && j.build !== mine) show(j.build);
      return j.build;
    } catch (e) { return null; }
  }
  async function checkStall() {
    try {
      const r = await fetch(base + 'data/pipeline-health.json?t=' + Date.now(), { cache: 'no-store' });
      const line = r.ok ? stallText(await r.json()) : null;
      let el = document.getElementById('stall-bar');
      if (!line) { if (el) el.remove(); return null; }
      if (!el) {
        el = document.createElement('div');
        el.id = 'stall-bar'; el.setAttribute('role', 'alert');
        el.style.cssText = 'margin:0;padding:10px 14px;background:#B26F0E;color:#fff;font:600 14px/1.4 system-ui;text-align:center';
        document.body.insertBefore(el, document.body.firstChild);
      }
      el.textContent = line;
      return line;
    } catch (e) { return null; }
  }
  setInterval(check, 60000);
  setInterval(checkStall, 600000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { check(); checkStall(); } });
  check();                                         // baseline now; later checks compare against it
  checkStall();
  window.AneesStale = { check, checkStall, stallText, get build() { return mine; } };
})();
