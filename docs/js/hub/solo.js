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
    // de-word (plan/OVERNIGHT-DEWORD-2026-10-22.md): the line for her becomes numbered steps; the old sentence opens in place (ⓘ)
    const steps = o.steps && o.steps.length
      ? `<ol class="dw-flow dw-steps">${o.steps.map(x => `<li>${esc(x)}</li>`).join('')}</ol>${o.who ? `<details class="dw-fold dw-why"><summary><span class="dw-i">i</span>More</summary><div>${esc(o.who)}</div></details>` : ''}`
      : `<p class="ab-sub">${esc(o.who || '')}</p>`;
    document.body.insertAdjacentHTML('afterbegin', `<div id="anees-bank" class="vp-sabz hb-solo"><main>
      ${app ? '<p class="hb-solo-back"><a href="../tutor.html">‹ Back to Tutor</a> <span>Preview · any tap here saves as the tutor’s answer</span></p>' : ''}
      <header class="ab-header vp-header dw-solo-head"><div><h1>${esc(o.title)}</h1>${steps}</div><div class="dw-top" data-theme-slot></div></header>
      <section class="hb-panel" id="hb-body"></section></main></div>`);
    const t = token(), el = document.getElementById('hb-body');
    if (!t && !o.noToken) { document.querySelectorAll('.dw-steps, .dw-why').forEach(x => x.remove());   // nothing to do yet but open the link
      el.innerHTML = '<div class="dw-gate"><svg class="dw-pic dw-lock" viewBox="0 0 120 80" aria-hidden="true"><path d="M8 10h62a8 8 0 0 1 8 8v30a8 8 0 0 1-8 8H30l-12 12v-12h-10a8 8 0 0 1-8-8V18a8 8 0 0 1 8-8z" fill="var(--dw-a1)"/><g fill="none" stroke="var(--sabz-bg, #fff)" stroke-width="5" stroke-linecap="round"><path d="M36 37a7 7 0 0 0 10 0l7-7a7 7 0 0 0-10-10l-2 2"/><path d="M42 29a7 7 0 0 0-10 0l-7 7a7 7 0 0 0 10 10l2-2"/></g><path d="M84 33h18" stroke="var(--dw-a2)" stroke-width="6" stroke-linecap="round"/><path d="M98 23l12 10-12 10" fill="none" stroke="var(--dw-a2)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg><form class="dw-paste"><label><b>Open the student&#39;s link</b><small>Tap it in the student&#39;s message, or paste it here.</small></label><span class="dw-paste-row"><input type="url" inputmode="url" placeholder="Paste the link" aria-label="The link the student sent"><button type="submit" class="dw-go">Open</button></span></form></div>';
      el.querySelector('.dw-paste').onsubmit = e => { e.preventDefault(); const v = el.querySelector('.dw-paste input').value.trim(); if (!v) return;
        let k = ''; try { const u = new URL(v, location.href); k = u.searchParams.get('t') || new URLSearchParams(u.hash.slice(1)).get('t') || ''; } catch (x) {}
        if (!k && !/[\/?#=]/.test(v)) k = v;   // a bare key
        if (k) location.search = '?t=' + encodeURIComponent(k); };
      return; }
    o.mount(el, { token: t, base: '../' });
    if (root.AneesNote) root.AneesNote.attach(el, { token: t, list: (location.pathname.split('/').pop() || 'page').replace('.html', '') + (new URLSearchParams(location.search).get('list') ? ':' + new URLSearchParams(location.search).get('list') : ''), title: o.title });   // AM-27
  }
  root.AneesSolo = { run, token };
})(window);
