/* Sabz theme switch (Medi 2026-09-22): Light / Dark / Phone.
   'phone' follows the device; light and dark beat it in both directions
   (docs/BRAND-SABZ.md — both modes are in the book).
   Stored per browser in localStorage['anees-theme']; nothing is sent anywhere. */
(function (root) {
    const HERE = (document.currentScript && document.currentScript.src) || '';
  const KEY = 'anees-theme';
  const ICONS = {
    light: '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.4v2.4M12 19.2v2.4M2.4 12h2.4M19.2 12h2.4M5.2 5.2l1.7 1.7M17.1 17.1l1.7 1.7M18.8 5.2l-1.7 1.7M6.9 17.1l-1.7 1.7"/>',
    dark: '<path d="M20 14.2A8.2 8.2 0 0 1 9.8 4a8.4 8.4 0 1 0 10.2 10.2Z"/>',
    auto: '<rect x="7" y="2.6" width="10" height="18.8" rx="2.4"/><path d="M10.8 18.4h2.4"/>'
  };
  const MODES = [['light', 'Light'], ['dark', 'Dark'], ['auto', 'Phone']];
  function read() { try { const v = localStorage.getItem(KEY); return v === 'light' || v === 'dark' ? v : 'auto'; } catch (e) { return 'auto'; } }
  function apply(mode) {
    const el = document.documentElement;
    if (mode === 'light' || mode === 'dark') el.setAttribute('data-sabz-theme', mode); else el.removeAttribute('data-sabz-theme');
  }
  function set(mode) { try { mode === 'auto' ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, mode); } catch (e) {} apply(mode); paint(); }
  function paint() {
    const now = read();
    document.querySelectorAll('.sabz-theme').forEach(box => box.dataset.active = now);   // CSS slides the knob to it
    document.querySelectorAll('.sabz-theme button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.theme === now)));
  }
  function control() {
    const box = document.createElement('div');
    box.className = 'sabz-theme'; box.setAttribute('role', 'group'); box.setAttribute('aria-label', 'Colour theme');
    box.innerHTML = '<span class="sabz-theme-knob" aria-hidden="true"></span>' + MODES.map(([m, label]) =>
      `<button type="button" data-theme="${m}" title="${label}" aria-label="${label}"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[m]}</svg><span class="sabz-theme-name">${label}</span></button>`).join('');
    box.addEventListener('click', e => { const b = e.target.closest('button'); if (b) set(b.dataset.theme); });
    return box;
  }
  function sheet() {
    if (document.querySelector('link[data-sabz-theme-css]')) return;
    // PG-54 (Medi 2026-10-19, screenshot: three big grey "Light / Dark / Phone" boxes): when css/theme-switch.css does not
    // load (stale cache, blocked fetch) the bare buttons showed. This minimal inline copy keeps the slider shape; the full
    // sheet below still loads on top of it.
    const fb = document.createElement('style');
    fb.setAttribute('data-sabz-theme-fallback', '');
    fb.textContent = '.sabz-theme{display:inline-grid;grid-template-columns:repeat(3,1fr);width:100%;max-width:132px;margin:14px 0 0;padding:3px;border-radius:999px;position:relative}'
      + '.sabz-theme-knob{display:none}.sabz-theme button{height:26px;min-width:0;padding:0;border:0;border-radius:999px;background:transparent;color:inherit;cursor:pointer;display:inline-flex;align-items:center;justify-content:center}'
      + '.sabz-theme button[aria-pressed=true]{background:rgba(127,127,127,.25)}.sabz-theme button svg{width:15px;height:15px}'
      + '.sabz-theme-name{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}';
    (document.head || document.documentElement).appendChild(fb);
    const base = HERE.replace(/js\/theme\.js.*$/, '');
    const link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = base + 'css/theme-switch.css'; link.setAttribute('data-sabz-theme-css', '');
    (document.head || document.documentElement).appendChild(link);
  }
  function mount() {
    sheet();
    if (document.querySelector('.sabz-theme')) return paint();
    const slot = document.querySelector('[data-theme-slot]') || document.querySelector('#anees-bank aside nav') || document.body;
    const box = control();
    if (slot === document.body) box.classList.add('sabz-theme-float');
    slot.appendChild(box); paint();
  }
  apply(read());
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
  root.AneesTheme = { read, set, apply, mount };
})(typeof window !== 'undefined' ? window : globalThis);

/* Two looks (A flat / B bright) on every page: js/look.js, loaded once (de-word preview 2026-10-22). */
(function(){try{if(typeof document==='undefined'||window.AneesLook||document.querySelector('script[data-anees-look]'))return;var me=document.currentScript||{};var src=(me.src||'').replace(/[^/]*$/,'');if(!src)return;try{document.documentElement.setAttribute('data-look',localStorage.getItem('anees-look')==='kurz'?'kurz':'flat');}catch(e){document.documentElement.setAttribute('data-look','flat');}var s=document.createElement('script');s.src=src+'look.js?v=dw1';s.setAttribute('data-anees-look','');(document.head||document.documentElement).appendChild(s);}catch(e){}})();

/* Play / pause / stop bar on every page that plays sound (Medi 2026-10-01): js/play-bar.js, loaded once. */
(function(){try{if(typeof document==='undefined'||window.AneesPlayBar||document.querySelector('script[data-apb]'))return;var me=document.currentScript||{};var src=(me.src||'').replace(/[^/]*$/,'');if(!src)return;var s=document.createElement('script');s.src=src+'play-bar.js?v=20261002-1';s.setAttribute('data-apb','');(document.head||document.documentElement).appendChild(s);}catch(e){}})();
