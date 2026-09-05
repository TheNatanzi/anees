// Out-of-date banner: every page carries window.ANEES_BUILD (js/build.js, stamped at commit time). The page checks
// data/build.json every 60 s and when the tab comes back to the front; when the stamps differ, a flashing bar says so.
(function () {
  if (typeof window === 'undefined') return;
  const mine = window.ANEES_BUILD || '';
  const base = (function () { const s = document.querySelector('script[src*="js/stale.js"]'); return s ? s.getAttribute('src').replace(/js\/stale\.js.*$/, '') : ''; })();
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
    document.getElementById('stale-reload').onclick = () => location.reload();
  }
  async function check() {
    try {
      const r = await fetch(base + 'data/build.json?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return null;
      const j = await r.json();
      if (mine && j.build && j.build !== mine) show(j.build);
      return j.build;
    } catch (e) { return null; }
  }
  setInterval(check, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(); });
  setTimeout(check, 5000);
  window.AneesStale = { check, get build() { return mine; } };
})();
