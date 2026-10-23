/* Two looks for every page (de-word preview, plan/OVERNIGHT-DEWORD-2026-10-22.md).
   A "flat"  = Anees colours, flat blocks, big numbers.
   B "kurz"  = deep navy ground, bright accents, rounded shapes (a light variant in Light mode).
   Same markup in both; only css/look.css changes. Stored per browser in localStorage['anees-look'];
   nothing is sent anywhere. Loaded once by js/theme.js, so every page that has the theme switch gets it. */
(function (root) {
  if (root.AneesLook) return;
  const KEY = 'anees-look';
  const LOOKS = [['flat', 'A', 'Look A · flat'], ['kurz', 'B', 'Look B · bright']];
  const HERE = (document.currentScript && document.currentScript.src) || '';
  // Medi 2026-10-22 picked Look A for every page: the switch is gone and every page is flat (Look B CSS stays unused).
  function read() { return 'flat'; }
  function apply(look) { document.documentElement.setAttribute('data-look', look); }
  function paint() {
    const now = read();
    document.querySelectorAll('.anees-look button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.look === now)));
  }
  function set(look) { try { localStorage.setItem(KEY, look); } catch (e) {} apply(look); paint(); }
  function sheet() {
    if (document.querySelector('link[data-anees-look-css]')) return;
    const base = HERE.replace(/js\/look\.js.*$/, '');
    const link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = base + 'css/look.css?v=dw3'; link.setAttribute('data-anees-look-css', '');
    (document.head || document.documentElement).appendChild(link);
  }
  const SWITCH = false;
  function mount(tries) {
    if (!SWITCH) return;
    if (document.querySelector('.anees-look')) return paint();
    // wait (up to 2 s) for js/theme.js to mount its switch, so the look switch sits next to it instead of floating
    if (!document.querySelector('.sabz-theme') && (tries || 0) < 20) return setTimeout(() => mount((tries || 0) + 1), 100);
    const box = document.createElement('div');
    box.className = 'anees-look'; box.setAttribute('role', 'group'); box.setAttribute('aria-label', 'Page look');
    box.innerHTML = LOOKS.map(([k, s, t]) => `<button type="button" data-look="${k}" title="${t}" aria-label="${t}">${s}</button>`).join('');
    box.addEventListener('click', e => { const b = e.target.closest('button'); if (b) set(b.dataset.look); });
    const theme = document.querySelector('.sabz-theme');
    if (theme && theme.parentNode && !theme.classList.contains('sabz-theme-float')) theme.parentNode.insertBefore(box, theme.nextSibling);
    else { box.classList.add('anees-look-float'); document.body.appendChild(box); }
    paint();
  }
  apply(read()); sheet();
  // theme.js mounts its switch on DOMContentLoaded; mount after it so the look switch sits next to it.
  const later = () => setTimeout(() => mount(0), 0);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', later); else later();
  root.AneesLook = { read, set, apply, mount };
})(typeof window !== 'undefined' ? window : globalThis);
