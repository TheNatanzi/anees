/* The old addresses of Amal's lists (amal/after.html, plan.html, review.html, verb-check.html, word-review.html) open the
   SAME module the Tutor hub opens in its panel (Medi 2026-10-02: "everything on the tutor hub do what the new words is
   doing"). This draws the Anees shell around it: title, a line for Amal, the module, and "Back to Tutor" when Medi
   previews from the app (?from=app).
   AneesSolo.run({title, who, mount(el, item)}) - item = {token, ...} with the token from ?t= or #t=. */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function token() {
    const q = new URLSearchParams(location.search), h = new URLSearchParams(location.hash.slice(1));
    return (q.get('t') || h.get('t') || '').trim();
  }
  function run(o) {
    const app = new URLSearchParams(location.search).get('from') === 'app';
    document.body.insertAdjacentHTML('afterbegin', `<div id="anees-bank" class="vp-sabz hb-solo"><main>
      ${app ? '<p class="hb-solo-back"><a href="../tutor.html">‹ Back to Tutor</a> <span>Preview · any tap here saves as the tutor’s answer</span></p>' : ''}
      <header class="ab-header vp-header"><div><div class="vp-eyebrow">For the tutor · from the student's app</div><h1>${esc(o.title)}</h1><p class="ab-sub">${esc(o.who || '')}</p></div></header>
      <section class="hb-panel" id="hb-body"></section></main></div>`);
    const t = token(), el = document.getElementById('hb-body');
    if (!t && !o.noToken) { el.innerHTML = '<p class="hb-sub">This page needs the private link the student sent you.</p>'; return; }
    o.mount(el, { token: t, base: '../' });
  }
  root.AneesSolo = { run, token };
})(window);
