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
  const g = (c, d) => `<svg class="dp-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="var(${c})" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const GLYPH = { gram: g('--dw-a1', '<path d="M3 12h13M12 7l5 5-5 5"/><circle cx="20" cy="12" r="1.5"/>'), word: g('--dw-a2', '<path d="M4 7h7M4 12h5M4 17h7M14 12h6M17 9l3 3-3 3"/>'),
    new: g('--dw-a3', '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/>') };
  // the wrong / right pair: in each " / " piece only the letters that change are marked (same text, only wrapped)
  const escH = x => x.replace(/[&<>]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
  function diffMark(c) {
    const w = c.querySelector('.tv-ar.tv-wrong'), r = c.querySelector('.tv-ar.tv-right');
    if (!w || !r || w.children.length || r.children.length) return;
    const W = w.textContent.split(' / '), R = r.textContent.split(' / ');
    if (W.length !== R.length) return;
    const mark = (a, b, cls) => {
      let p = 0; while (p < a.length && p < b.length && a[p] === b[p]) p++;
      let s = 0; while (s < a.length - p && s < b.length - p && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
      const mid = a.slice(p, a.length - s);
      return mid ? escH(a.slice(0, p)) + `<mark class="${cls}">${escH(mid)}</mark>` + escH(a.slice(a.length - s)) : escH(a);
    };
    w.innerHTML = W.map((x, i) => mark(x, R[i], 'dp-del')).join(' / ');
    r.innerHTML = R.map((x, i) => mark(x, W[i], 'dp-ins')).join(' / ');
    // several pieces: one aligned row per piece (wrong | right) instead of one long slash line; the slash line stays for readers
    const pair = w.closest('.tv-pair');
    if (W.length > 1 && pair && !pair.nextElementSibling?.matches('.dp-pairs')) {
      const g = document.createElement('div'); g.className = 'dp-pairs'; g.setAttribute('aria-hidden', 'true');
      g.innerHTML = W.map((x, i) => `<span class="dp-w" lang="ar">${mark(x, R[i], 'dp-del')}</span><span class="dp-r" lang="ar">${mark(R[i], x, 'dp-ins')}</span>`).join('');
      pair.after(g); pair.classList.add('dp-sr');
    }
  }
  // 2. a mistake card: the why line and the e.g. line -> one i on the "N times in ..." line, which becomes a chip
  function cards(root) {
    root.querySelectorAll('.hb-card').forEach(c => {
      if (c.dataset.dp) return; c.dataset.dp = '1';
      c.querySelectorAll('.tv-pair ~ .hb-en').forEach(e => { if (/^\s*→|→\s*$/.test(txt(e))) e.classList.add('dp-sr'); });   // a half Arabizi pair (one side missing) is noise
      diffMark(c);
      const foot = c.closest('.hb-task') && c.closest('.hb-task').querySelector(':scope > .hb-foot');   // provenance line -> the i
      if (foot && !foot.dataset.dp && txt(foot).length > 60) { foot.dataset.dp = '1'; const row = document.createElement('p'); row.className = 'dp-footi'; foot.before(row); row.appendChild(info([foot], 'Where this list comes from')); }
      const head = c.querySelector(':scope > .hb-prog');   // a small glyph per card kind: grammar slip, word slip, new word
      if (head) { const k = /new word/i.test(txt(head)) ? 'new' : /grammar/i.test(txt(head)) ? 'gram' : 'word'; head.insertAdjacentHTML('afterbegin', GLYPH[k]); }
      const why = c.querySelector(':scope > .hb-why'), eg = [...c.querySelectorAll(':scope > p.hb-sub')].find(p => /^e\.g\./.test(txt(p)));
      const times = [...c.querySelectorAll(':scope > p.hb-sub')].find(p => /^(\d[\d,]* times? in|Came up \d)/.test(txt(p)));
      if (times) {   // "3 times in 3 lessons" -> one dot per time (up to 8) + the same words as a chip
        times.classList.add('dp-times');
        const n = Math.min(8, parseInt(txt(times).replace(/^Came up /, ''), 10) || 0);
        const m2 = /^(\d[\d,]*) times? (in .*)$/.exec(txt(times));   // the dots say "3 times"; the words stay for a screen reader
        times.innerHTML = `<span class="dp-dots" aria-hidden="true">${'<i></i>'.repeat(n)}</span>` + (m2 ? `<span class="dp-tin"><b class="dp-x">${m2[1]}×</b><span class="dp-sr"> time${m2[1] === '1' ? '' : 's'}</span> ${m2[2]}</span>` : `<span class="dw-chip muted">${times.innerHTML}</span>`);
      }
      const long = [...c.querySelectorAll(':scope > .hb-en')].filter(x => txt(x).length > 60);   // a long note in place of a meaning line
      const move = [why, eg, ...long].filter(x => x && txt(x));
      if (!move.length) return;
      const d = info(move, 'Why this is a mistake');
      if (times) times.appendChild(d); else { const h = c.querySelector(':scope > .hb-big, :scope > .hb-prog'); if (h) h.after(d); }
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
  // 5. "28 left to decide" under the filter chips -> a big number and one split bar (done / left) read from the chips
  function progress(root) {
    root.querySelectorAll('p.hb-prog[data-prog]').forEach(p => {
      const m = /^(\d[\d,]*) left to decide/i.exec(txt(p)), task = p.closest('.hb-task');
      if (!m || !task) return;
      const chip = re => { const c = [...task.querySelectorAll('.hb-chip')].find(x => re.test(txt(x))); const k = c && /\((\d+)\)/.exec(txt(c)); return k ? +k[1] : null; };
      const all = chip(/^All\b/), left = parseInt(m[1].replace(/,/g, ''), 10);
      if (!all || left > all) return;
      const key = left + '/' + all; if (p.dataset.dp === key && p.querySelector('.dp-pbar')) return; p.dataset.dp = key;
      p.classList.add('dp-prog');
      const old = p.querySelector('.dp-pbar'); if (old) old.remove();
      p.insertAdjacentHTML('beforeend', `<span class="dp-pbar" role="img" aria-label="${all - left} of ${all} done"><span class="dw-split"><i style="width:${(100 * (all - left) / all).toFixed(1)}%"></i></span><span class="dp-pdone">${all - left} of ${all} done</span></span>`);
    });
  }
  // 6. a long card list (the mistakes to review): the next 3 cards in sight, the rest of the same page (same order) opens in
  //    place; answering a card brings the next one up, so her order never changes
  const foldOpen = new WeakMap();
  function cardFold(root) {
    root.querySelectorAll('[data-root]').forEach(r => {
      if (r.querySelector(':scope > details.dp-cards')) return;
      const cs = [...r.querySelectorAll(':scope > article.hb-card')];
      if (cs.length < 3) return;
      const rest = cs.slice(1), d = document.createElement('details');
      d.className = 'dp-cards'; d.open = !!foldOpen.get(r);
      d.innerHTML = `<summary>${rest.length} more cards on this page</summary>`;
      rest[0].before(d); rest.forEach(c => d.appendChild(c));
      d.addEventListener('toggle', () => foldOpen.set(r, d.open));
    });
  }
  // 7. phone only: the filter chips fold into one "Filter: Unanswered (28)" row, and the three tools for the student into one
  //    "For the student" row; both open in place, every chip and tool is the same element with the same handler
  const phone = () => window.matchMedia('(max-width: 680px)').matches;
  function fold(el, cls, label) {
    let d = el.parentElement && el.parentElement.matches('details.' + cls) ? el.parentElement : null;
    if (!d) {
      d = document.createElement('details'); d.className = cls + ' dp-fold-row';
      const s = document.createElement('summary'); d.appendChild(s);
      el.before(d); d.appendChild(el);
    }
    const s = d.querySelector(':scope > summary'), t = label();
    if (s.textContent !== t) s.textContent = t;
    return d;
  }
  function phoneFolds(root) {
    if (!phone()) return;
    root.querySelectorAll('.hb-task [data-filters].hb-chips').forEach(f => {
      if (!f.querySelector('.hb-chip')) return;
      fold(f, 'dp-filt', () => 'Filter: ' + txt(f.querySelector('.hb-chip[aria-pressed="true"]') || f.querySelector('.hb-chip')));
    });
    const tools = document.querySelector('nav.hb-tools');
    if (tools) {
      const NM = { upload: 'Upload', homework: 'Homework', 'add-grammar': 'Grammar' };
      const d = fold(tools, 'dp-tools', () => 'For the student: ' + [...tools.querySelectorAll('.hb-tab')].map(a => { const n = txt(a.querySelector('.hb-n') || document.createElement('i')).split(' ')[0]; return (NM[a.dataset.tab] || txt(a)) + (n ? ' ' + n : ''); }).join(' · '));
      if (tools.querySelector('.hb-tab[aria-selected="true"]')) d.open = true;
    }
  }
  let busy = false;
  function run() {
    if (busy) return; busy = true;
    try { intros(view); cards(view); grammar(view); lists(view); progress(view); cardFold(view); phoneFolds(view); } finally { busy = false; }
  }
  let t = 0;
  new MutationObserver(() => { if (!busy) { clearTimeout(t); t = setTimeout(run, 30); } }).observe(view, { childList: true, subtree: true });
  run();
})();
