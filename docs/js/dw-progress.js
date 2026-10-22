/* De-word pass for Progress & Stats only (plan/OVERNIGHT-DEWORD-2026-10-22.md).
   The tab renderers write their panels; this file then keeps on screen only numbers, actions and warnings:
   - a line under a heading goes behind a small ⓘ on the heading (opens in place),
   - notes, sources and footers go behind a ⓘ where they stood (a caveat keeps a visible warning chip),
   - the method-change box becomes one warning chip per tab (its words open from the chip),
   - long tables show their newest rows with a "Show all" button.
   Nothing is deleted: every word and number is still in the page, one tap away. Runs again whenever a
   renderer redraws (period switch, live data), so the next hourly build keeps the same look. */
(function () {
  'use strict';
  const ROOT_ID = 'vp-content';
  // lines that sit right under a heading
  const SUBS = '.ab-sub, .vp-panelhead .ab-sub, .ov2-sub';
  // notes, sources, footers, long explanations: behind a ⓘ where they stand
  const NOTES = ['.vp-card-sub', '#ov-metrics .ab-tiny', '.vp-foot', '.vp-footer', '.ov2-source', '.ov2-foot',
    '.ov2-notes', '.ov2-text', '.ov2-quote', '.va-foot', '.vu-foot', '.vl-foot', '.gp-foot', '.gu-foot', '.gu-src',
    '.fu-foot', '.fu-do', '.fl-foot', '.fl-rule', '.fl-strict', '.vl-fwhy', '.vl-kpis + small',
    '.vl-summary small', '.gp-summary small', '.vp-empty-long'].join(',');
  const WARN = /not verified|caveat|hard to trust|\bearly\b|not comparable|machine gues|offline|stale/i;
  let busy = false, queued = false;

  function info(label, warn) {
    const d = document.createElement('details');
    d.className = 'dw-info dw-p' + (warn ? ' dw-pwarn' : '');
    d.dataset.dw = '1';
    const s = document.createElement('summary');
    s.setAttribute('aria-label', 'More about this');
    // no text in the summary: the ⓘ and the chip words are drawn by CSS from data-chip, so the page text
    // (and every number in it) reads exactly as before
    s.innerHTML = warn ? '<span class="dw-chip warn"></span><span class="dw-i"></span>' : '<span class="dw-i"></span>';
    if (warn) s.firstChild.dataset.chip = label;
    if (warn) s.setAttribute('aria-label', label + ': more');
    d.append(s, document.createElement('div'));
    return d;
  }
  const textOf = el => (el.textContent || '').trim();

  // 1. the line under a heading → ⓘ at the end of that heading
  function subs(root) {
    for (const p of root.querySelectorAll(SUBS)) {
      if (p.dataset.dw || p.closest('details.dw-p') || !textOf(p)) continue;
      let h = p.previousElementSibling;
      while (h && h.matches('.vp-eyebrow, .ov2-k, span.vp-eyebrow')) h = h.previousElementSibling;
      if (!h || !/^H[1-4]$/.test(h.tagName)) h = null;
      const d = info();
      p.dataset.dw = '1';
      if (h) { h.append(d); } else { p.before(d); }
      d.lastChild.append(p);
    }
  }

  // 2. notes → ⓘ in place (a caveat keeps a visible warning chip)
  function notes(root) {
    for (const el of root.querySelectorAll(NOTES)) {
      if (el.dataset.dw || el.closest('details.dw-p') || !textOf(el) || el.hidden) continue;
      // the Good / Shaky / Wrong row of a card is a number to track: it stays out
      const keep = el.querySelector(':scope > .vp-card-status');
      const t = textOf(el);
      const warn = WARN.test(t) ? (/not verified|"≈"/.test(t) ? '≈ not verified' : /\bearly\b/i.test(t) ? 'early' : 'caveat') : '';
      el.dataset.dw = '1';
      // links are actions: they stay on screen, right after the ⓘ
      const links = [...el.querySelectorAll('a[href]')];
      // two notes side by side share one ⓘ
      const prev = el.previousElementSibling, gap = el.previousSibling;
      let d;
      if (!warn && !keep && prev && prev.matches('details.dw-p:not(.dw-pwarn)') && (gap === prev || !/\S/.test(gap.textContent || ''))) {
        d = prev;
      } else {
        d = info(warn, !!warn);
        el.before(d);
      }
      d.lastChild.append(el);
      let at = d;
      if (keep) { at.after(keep); at = keep; }
      for (const a of links) { const w = document.createElement('span'); w.className = 'dw-link'; w.dataset.dw = '1'; w.append(a); at.after(w); at = w; }
    }
  }

  // 3. method change: one chip per tab, words behind it
  function method(root) {
    for (const p of root.querySelectorAll('p.method-change')) {
      if (p.dataset.dw) continue;
      p.dataset.dw = '1';
      const pane = p.closest('#' + ROOT_ID + ' > div') || root;
      const first = pane.querySelector('details.dw-method');
      const date = p.dataset.methodChange || '';
      const d = info(`Method change · ${date}`, true);
      d.classList.add('dw-method');
      p.removeAttribute('style');
      p.before(d);
      d.lastChild.append(p);
      if (first && first !== d) d.classList.add('dw-again');   // same tab already shows the chip
    }
  }

  // 4. the lesson table (25 rows x 9 numbers) opens from one button
  function tables(root) {
    for (const tb of root.querySelectorAll('.ov-tbl > table')) {
      const body = tb.tBodies && tb.tBodies[0];
      if (!body || tb.dataset.dw || body.rows.length <= 8) continue;
      tb.dataset.dw = '1';
      tb.classList.add('dw-clip');
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'dw-more ab-control'; b.dataset.dw = '1';
      const n = body.rows.length;
      b.textContent = `Show all ${n} lessons`;
      b.addEventListener('click', () => {
        const open = tb.classList.toggle('dw-clip');
        b.textContent = open ? `Show all ${n} lessons` : 'Hide the table';
      });
      (tb.closest('.ov-tbl') || tb).after(b);
    }
  }

  // 5. the robot alert banner: one line ("… since 10-21 19:20"), the log behind ⓘ
  function alerts() {
    const box = document.getElementById('lesson-alerts');
    if (!box) return;
    for (const line of box.children) {
      if (line.dataset.dw || line.matches('details, .dw-alert-head')) continue;
      const t = line.textContent || '';
      const m = /^([\s\S]*?\d{1,2}:\d{2})(:[\s\S]+)$/.exec(t);
      if (!m || m[2].length < 30) continue;
      line.dataset.dw = '1';
      const head = document.createElement('span'); head.className = 'dw-alert-head'; head.textContent = m[1];
      const d = info(); d.lastChild.textContent = m[2];
      line.textContent = ''; line.append(head, d);
    }
    box.classList.add('dw-alerts');
    // when the site-wide stall bar already says the robot stopped, this box folds to one small chip
    const stall = document.getElementById('stall-bar') || document.getElementById('stale-bar');
    if (stall && !box.querySelector(':scope > details.dw-alllog')) {
      const d = info('robot log', true); d.classList.add('dw-alllog');
      d.lastChild.append(...box.childNodes);
      box.append(d);
    }
  }

  // 9. the "saved data / loading" status line: a small chip, its words behind it
  function notice() {
    const n = document.getElementById('vp-notice');
    if (!n || n.dataset.dw || !textOf(n)) return;
    n.dataset.dw = '1';
    const d = info('saved data', true); d.classList.add('dw-notice');
    n.before(d); d.lastChild.append(n);
  }

  // 10. one "data notes" chip under the title holds the page's status chips (robot log, saved data, method
  //     change, ≈ not verified): one warning to see, every note one tap away
  function dataNotes() {
    const main = document.querySelector('#anees-bank main');
    const head = main && main.querySelector(':scope > .vp-header');
    if (!head) return;
    let box = main.querySelector(':scope > details.dw-notes');
    if (!box) {
      box = info('', true); box.classList.add('dw-notes');
      head.after(box);
    }
    const body = box.lastChild;
    const put = (key, el) => {
      if (!el || el.parentElement === body) return;
      const old = body.querySelector(`:scope > [data-dwkey="${key}"]`);
      if (old && old !== el) old.remove();
      el.dataset.dwkey = key; body.append(el);
    };
    const alerts = document.getElementById('lesson-alerts');
    if (alerts && alerts.querySelector('details.dw-alllog')) put('alerts', alerts);
    put('notice', main.querySelector(':scope > details.dw-notice'));
    put('method', document.querySelector('#ov2 details.dw-method'));
    put('nv-b', document.querySelector('#ov2 section[aria-labelledby="ov2-h-b"] details.dw-pwarn:not(.dw-method)'));
    put('nv-t', document.querySelector('#vp-tab-overview > details.dw-pwarn:not(.dw-method)'));
    put('source', document.querySelector('#ov2 > details.dw-p:last-child:not(.dw-pwarn)'));
    const foot = document.getElementById('vp-footer');
    put('status', foot && foot.closest('details.dw-p'));
    const keys = [...body.children].map(c => c.dataset.dwkey);
    const m = body.querySelector('[data-dwkey="method"] p.method-change');
    const parts = [];
    if (keys.some(k => /^nv-/.test(k))) parts.push('≈ not verified');
    if (m) parts.push('method change ' + (m.dataset.methodChange || '').slice(5));
    if (keys.includes('alerts')) parts.push('robot log');
    if (keys.includes('notice')) parts.push('saved data');
    box.querySelector('.dw-chip').dataset.chip = parts.join(' · ') || 'data notes';
    box.hidden = !keys.length;
  }

  // 6. a tile that repeats a top card (Lessons tracked = Lessons + Lesson hours) steps aside
  function dups(root) {
    for (const m of root.querySelectorAll('#ov-metrics .ab-metric:not(.dw-dup):not(.dw-tmore)')) {
      const l = m.querySelector('.ab-metric-label');
      if (l && /^\s*Lessons tracked/.test(l.textContent)) m.classList.add('dw-dup');
      // speed, fillers and homework open with the lesson table
      if (l && /^\s*(Words per minute|Fillers|Homework)/.test(l.textContent)) m.classList.add('dw-tmore');
    }
  }

  // 7. the other tabs: every panel shows its title and headline number; the chart opens in place.
  //    The first two panels of a tab stay open, and so does any panel you answer in (the swipe check).
  const PANES = ['vp-tab-vocab', 'vp-tab-flash', 'vp-tab-lexicon', 'vp-tab-fluency', 'vp-tab-grammar'];
  function charts() {
    for (const id of PANES) {
      const pane = document.getElementById(id);
      if (!pane) continue;
      const panels = [...pane.querySelectorAll('.vp-panel')].filter(p => !p.parentElement.closest('.vp-panel'));
      panels.forEach((p, i) => {
        if (p.dataset.dwc) return;
        const kids = [...p.children];
        const h = kids.findIndex(k => k.matches('h2, h3, .vp-panelhead') || k.querySelector('h2, h3'));
        if (h < 0) return;
        let cut = h + 1;
        while (cut < kids.length && /big|side|kpi|-n\b|num/.test(kids[cut].className || '') && !kids[cut].querySelector('svg, table')) cut++;
        const rest = kids.slice(cut).filter(k => !k.matches('details.dw-p, .dw-link'));
        if (!rest.length || !rest.some(k => k.querySelector('svg, table, .gp-row, .vp-bar, [class*="row"], [class*="bar"]') || k.matches('svg, table'))) return;
        p.dataset.dwc = '1';
        const d = document.createElement('details');
        d.className = 'dw-chart'; d.dataset.dw = '1';
        if (i < 2 || p.matches('.fl-swipe-panel, .vu-panel') || p.querySelector('textarea, input[type=text]')) d.open = true;
        const s = document.createElement('summary'); s.setAttribute('aria-label', 'Chart');
        d.append(s);
        kids[cut].before(d);
        for (const k of kids.slice(cut)) d.append(k);
      });
      fold(pane, panels);
    }
  }

  // 8. a tab shows its first two panels (and any you answer in); the rest wait behind one "more views" button.
  //    Hidden by a class, not moved, so the page text keeps its order.
  function fold(pane, panels) {
    const extra = panels.filter((p, i) => i >= 2 && !p.matches('.fl-swipe-panel'));
    if (extra.length < 2) return;
    extra.forEach(p => p.classList.add('dw-extra'));
    // a block of the tab (a section heading + its panels) that holds only extra panels folds with them
    for (const c of pane.children) {
      if (c.matches('.dw-morebtn, details.dw-p')) continue;
      const ps = c.matches('.vp-panel') ? [c] : [...c.querySelectorAll('.vp-panel')];
      if (ps.length && ps.every(p => p.classList.contains('dw-extra'))) c.classList.add('dw-extra');
      else if (!ps.length && c.previousElementSibling && c.previousElementSibling.classList.contains('dw-extra')) c.classList.add('dw-extra');
    }
    let b = pane.querySelector(':scope > .dw-morebtn');
    if (!b) {
      b = document.createElement('button');
      b.type = 'button'; b.className = 'dw-morebtn'; b.dataset.dw = '1';
      b.addEventListener('click', () => { const open = pane.classList.toggle('dw-open'); b.dataset.open = open ? '1' : ''; b.setAttribute('aria-expanded', String(open)); });
      b.setAttribute('aria-expanded', 'false');
      // right after the block that holds the second panel
      let at = panels[1]; while (at.parentElement !== pane) at = at.parentElement;
      at.after(b);
    }
    b.dataset.n = String(extra.length);
    b.setAttribute('aria-label', extra.length + ' more views');
    pane.classList.add('dw-folded');
  }

  function run() {
    queued = false;
    const root = document.getElementById(ROOT_ID);
    if (!root) return;
    busy = true;
    try {
      const head = document.querySelector('.vp-header');
      method(root); subs(root); notes(root); tables(root); dups(root); alerts(); notice(); charts(); dataNotes();
      if (head) subs(head);
    } finally { busy = false; }
  }
  function soon() { if (!queued) { queued = true; requestAnimationFrame(run); } }

  // a ⓘ inside a card link opens in place instead of following the link
  document.addEventListener('click', e => {
    const s = e.target.closest && e.target.closest('details.dw-p > summary');
    if (!s || !s.closest('a')) return;
    e.preventDefault(); e.stopPropagation();
    const d = s.parentElement; d.open = !d.open;
  }, true);

  function start() {
    const root = document.getElementById(ROOT_ID);
    if (!root) return;
    new MutationObserver(() => { if (!busy) soon(); }).observe(root.closest('main') || root, { childList: true, subtree: true });
    run();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
