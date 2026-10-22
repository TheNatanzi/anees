/* De-word 2026-10-22 (plan/OVERNIGHT-DEWORD-2026-10-22.md), group "people": loaded by docs/tutor.html only.
   The hub modules (docs/js/hub/*.js) are shared with docs/amal/*.html, so they stay as they are; on the Tutor page this
   script folds their long explanations behind a small i that opens in place (PG-17), after every redraw.
   Nothing is removed: every word and number stays in the page, her buttons and their order do not change. */
(function () {
  const view = document.getElementById('hb-view');
  if (!view) return;
  const LONG = 90;
  const txt = el => (el.textContent || '').replace(/\s+/g, ' ').trim();
  function info(nodes, label, cls) {
    const d = document.createElement('details');
    d.className = 'dw-info' + (cls ? ' ' + cls : '');
    const s = document.createElement('summary');
    s.textContent = 'i'; s.setAttribute('aria-label', label);
    const box = document.createElement('div');
    d.append(s, box);
    nodes[0].before(d);
    nodes.forEach(n => box.appendChild(n));
    return d;
  }
  // 1. a list's long how-to line (module intro, the item's "what") -> one i under the title
  function intros(root) {
    root.querySelectorAll('p.hb-sub, p.tu-what').forEach(p => {
      if (p.dataset.dp || p.closest('details, .hb-moment, .hb-card, article, li, .hb-ex, label')) return;
      p.dataset.dp = '1';
      if (txt(p).length < LONG || p.style.color || /could not|did not|error|failed|offline/i.test(txt(p))) return;   // a warning stays in sight
      const host = p.closest('#hb-panel') || view, have = host.querySelector('.dp-how > details > div');
      if (have) { have.appendChild(p); return; }   // one i per panel: a second how-to line joins the first
      const row = document.createElement('p'); row.className = 'dp-how';
      p.before(row);
      const d = info([p], 'How this works');
      row.appendChild(d);
      row.insertAdjacentHTML('beforeend', '<span>How it works</span>');
    });
  }
  // 2. a mistake card: the why line and the e.g. line -> one i on the "N times in ..." line, which becomes a chip
  function cards(root) {
    root.querySelectorAll('.hb-card').forEach(c => {
      if (c.dataset.dp) return; c.dataset.dp = '1';
      const why = c.querySelector(':scope > .hb-why'), eg = [...c.querySelectorAll(':scope > p.hb-sub')].find(p => /^e\.g\./.test(txt(p)));
      const times = [...c.querySelectorAll(':scope > p.hb-sub')].find(p => /^(\d[\d,]* times? in|Came up \d)/.test(txt(p)));
      if (times) { times.classList.add('dp-times'); times.innerHTML = `<span class="dw-chip muted">${times.innerHTML}</span>`; }
      const move = [why, eg].filter(x => x && txt(x));
      if (!move.length) return;
      const d = info(move, 'Why this is a mistake');
      if (times) times.appendChild(d);
    });
  }
  // 3. Add grammar cards: where Claude heard it, her quote, the why and "close to" -> one i; a card she already answered folds
  function grammar(root) {
    root.querySelectorAll('article.tg-card').forEach(c => {
      if (c.dataset.dp) return; c.dataset.dp = '1';
      const more = [...c.querySelectorAll(':scope > .tg-heard, :scope > .tg-yours, :scope > .tu-meta, :scope > .tg-over')].filter(x => !/^Rewritten after/.test(txt(x)));
      const done = c.querySelector(':scope > .an-answered') && !c.querySelector(':scope > .hb-btns');
      if (done) {
        const keep = new Set([c.querySelector(':scope > .tg-title'), c.querySelector(':scope > .an-answered')]);
        const rest = [...c.children].filter(x => !keep.has(x) && !x.matches('.an-note, details.an-note, [data-note]'));
        if (rest.length) { const d = info(rest, 'Show the rule card', 'dp-fold'); const t = c.querySelector(':scope > .tg-title'); if (t) t.appendChild(d); }
        c.classList.add('dp-done');
        return;
      }
      if (more.length) { const d = info(more, 'Where this came from'); const t = c.querySelector(':scope > .tg-title'); if (t) t.appendChild(d); }
    });
  }
  // 4. a long reminder list under a heading (Upload: "Add these to the Doc (34)") -> opens in place from its heading
  function lists(root) {
    root.querySelectorAll('p.hb-prog').forEach(h => {
      if (h.dataset.dp) return; h.dataset.dp = '1';
      let n = h.nextElementSibling; const body = [];
      if (n && n.matches('p.hb-sub')) { body.push(n); n = n.nextElementSibling; }
      if (!(n && n.matches('ul.hb-done') && n.children.length > 6)) return;
      body.push(n);
      const d = document.createElement('details'); d.className = 'dp-list';
      const s = document.createElement('summary'); s.className = 'hb-prog'; s.innerHTML = h.innerHTML;
      d.appendChild(s); h.replaceWith(d); body.forEach(x => d.appendChild(x));
    });
  }
  let busy = false;
  function run() {
    if (busy) return; busy = true;
    try { intros(view); cards(view); grammar(view); lists(view); } finally { busy = false; }
  }
  let t = 0;
  new MutationObserver(() => { if (!busy) { clearTimeout(t); t = setTimeout(run, 30); } }).observe(view, { childList: true, subtree: true });
  run();
})();
