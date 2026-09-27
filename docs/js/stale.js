// Out-of-date banner. The page checks data/build.json every 60 s and when the tab comes back to the front; when the live
// stamp differs from the one this page LOADED WITH, a flashing bar says so.
// Fix 2026-09-26 (Medi: "it keeps telling me the version is out of date even though I keep refreshing"): the loaded-with
// stamp used to come from js/build.js, which GitHub Pages lets the browser cache for 10 minutes, so a refresh kept the
// old stamp and the bar came straight back. Now the stamp is read fresh (no-store) when the page opens; a refresh
// always clears the bar, and it only appears when a new version lands while the page is open.
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
  setInterval(check, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(); });
  check();                                         // baseline now; later checks compare against it
  window.AneesStale = { check, get build() { return mine; } };
})();
