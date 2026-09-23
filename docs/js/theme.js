/* Sabz theme switch (Medi 2026-09-22): Light / Dark / Phone.
   'phone' follows the device; light and dark beat it in both directions
   (docs/BRAND-SABZ.md — both modes are in the book).
   Stored per browser in localStorage['anees-theme']; nothing is sent anywhere. */
(function (root) {
  const KEY = 'anees-theme', MODES = [['light', 'Light'], ['dark', 'Dark'], ['auto', 'Phone']];
  function read() { try { const v = localStorage.getItem(KEY); return v === 'light' || v === 'dark' ? v : 'auto'; } catch (e) { return 'auto'; } }
  function apply(mode) {
    const el = document.documentElement;
    if (mode === 'light' || mode === 'dark') el.setAttribute('data-sabz-theme', mode); else el.removeAttribute('data-sabz-theme');
  }
  function set(mode) { try { mode === 'auto' ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, mode); } catch (e) {} apply(mode); paint(); }
  function paint() {
    const now = read();
    document.querySelectorAll('.sabz-theme button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.theme === now)));
  }
  function control() {
    const box = document.createElement('div');
    box.className = 'sabz-theme'; box.setAttribute('role', 'group'); box.setAttribute('aria-label', 'Colour theme');
    box.innerHTML = MODES.map(([m, label]) => `<button type="button" data-theme="${m}">${label}</button>`).join('');
    box.addEventListener('click', e => { const b = e.target.closest('button'); if (b) set(b.dataset.theme); });
    return box;
  }
  function mount() {
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
