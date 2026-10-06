/* Tutor hub (Medi 2026-10-01): one page for Amal and Medi. Tabs: To do · Grammar · Materials · Done.
   To do = every list waiting on Amal, ranked (what holds up Medi's scores first: newest lesson, older lessons, the
   moments to check, slip patterns, then the long verb lists). Facts come from data/tutor.json
   (scripts/build_tutor_data.py); done counts are read live from Supabase with each list's own token.
   PG-17 (Medi 2026-10-02 "can we have everything on the tutor hub do what the new words is doing where you dont have
   to go to an external page"): EVERY item opens and is answered inside the hub - laptop: list left, the item in the
   panel on the right; phone: the item opens right under its row. Each kind mounts the same module its old address
   (amal/*.html) mounts (MOUNT below). Grammar = one rule at a time with her notes, Materials = one section at a time.
   Medi 2026-10-02 "can you make these into accodrians so I can see what you are asking": the Done tab is accordions -
   each row opens in place with every question asked and her answer (Undo where the link is still open).
   Address: tutor.html#todo/<task id>, #grammar/<rule id>, #materials/<section id>, #done. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = n => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('en-US');
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  const today = () => new Date().toISOString().slice(0, 10);
  const PAGE = 20;
  let T = { open: [], closed: [] }, tasks = [], verifyN = null, NW = null, LG = null, UP = null, HW = null;

  async function rest(path, token) {
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'X-Anees-Token': token };
    const r = await fetch(ANEES.url + '/rest/v1/' + path, { headers: H, cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }
  async function live(item) {
    try {
      if (item.kind === 'verb_check') {
        const rows = await rest('verb_check_links?select=answers&token=eq.' + encodeURIComponent(item.token), item.token);
        const a = (rows[0] && rows[0].answers && rows[0].answers.answers) || {};
        return { ok: !!rows[0], done: Object.keys(a).length };
      }
      if (item.kind === 'after' || item.kind === 'before') {
        const rows = await rest('amal_links?select=answers,done_at&token=eq.' + encodeURIComponent(item.token), item.token);
        const a = (rows[0] && rows[0].answers) || {};
        const n = Object.keys(a.q || {}).length + Object.keys(a.hw || {}).length + Object.keys(a.v || {}).length + Object.keys(a.pr || {}).length;
        return { ok: !!rows[0], done: n, finished: !!(rows[0] && rows[0].done_at) || !!a.done };
      }
      if (item.kind === 'word_review') {
        const rows = await rest('transcript_review_links?select=answers&token=eq.' + encodeURIComponent(item.token), item.token);
        return { ok: !!rows[0], done: Object.keys((rows[0] && rows[0].answers && rows[0].answers.answers) || {}).length };
      }
      if (item.kind === 'review') {   // AM-17: the latest action per pattern counts (an undo puts it back)
        const rows = (await rest('amal_rules?select=kind,word_key&source=eq.review&order=created_at.asc&token=eq.' + encodeURIComponent(item.token), item.token))
          .filter(r => !/^(verify|newword|ledger):/.test(String(r.word_key || '')));
        return { ok: true, done: Object.values(AneesUndo.latest(rows)).filter(AneesUndo.isAnswer).length };
      }
      if (item.kind === 'listen') {   // her listening check: the latest tap per line counts (an undo puts it back)
        const rows = await rest('amal_rules?select=kind,word_key&source=eq.listen-check&word_key=like.listen:*&order=created_at.asc&token=eq.' + encodeURIComponent(item.token), item.token);
        return { ok: true, done: Object.values(AneesUndo.latest(rows)).filter(AneesUndo.isAnswer).length };
      }
      if (item.kind === 'check') {    // her other listening / checking lists: a card counts when every question on it is answered
        const D = await (await fetch('data/amal-check-' + item.list + '.json', { cache: 'no-store' })).json();
        const rows = await rest('amal_rules?select=kind,word_key,payload&source=eq.listen-check&word_key=like.' + encodeURIComponent(D.prefix) + ':*&order=created_at.asc&token=eq.' + encodeURIComponent(item.token), item.token);
        return { ok: true, done: AneesCheckTask.count(D, rows).done };
      }
    } catch (e) { return { ok: false, done: 0 }; }
    return { ok: true, done: 0 };
  }

  // ---- the task list -------------------------------------------------------------------------------------------
  const MIN_EACH = { after: 0.7, before: 0.7, verify: 0.4, ledger: 0.5, review: 1.2, verb_check: 0.1, word_review: 0.3, newwords: 0.3, listen: 0.25 };
  const UNIT = { after: 'moments', before: 'questions', review: 'slip patterns', verb_check: 'verb forms', word_review: 'lines', verify: 'moments', ledger: 'moments', newwords: 'words', listen: 'lines' };
  function taskOf(it, L) {
    const total = it.total || 0, d = Math.min(total, (L && L.done) || 0), left = Math.max(0, total - d);
    const title = it.kind === 'after' ? 'After the lesson · ' + pretty(it.lesson_date)
      : it.kind === 'review' ? 'Slips to review' : it.kind === 'verb_check' ? it.title.replace('Verb check', 'Verb forms') : it.title;
    const rank = it.kind === 'before' ? 0 : it.kind === 'after' ? 1 : it.kind === 'review' ? 3 : it.kind === 'word_review' ? 4 : it.kind === 'listen' ? 3.5 : it.kind === 'check' ? 3.6 : 5;
    return { id: it.id, kind: it.kind, item: it, title, total, done: d, left, unit: it.unit || UNIT[it.kind] || 'items', rank, date: it.lesson_date || '', finished: (L && L.finished) || (total > 0 && left === 0) };
  }
  function rankAll(list) { return list.sort((a, b) => a.rank - b.rank || String(b.date).localeCompare(String(a.date))); }
  const minEach = t => (t.item && t.item.min_each) || MIN_EACH[t.kind] || 0.5;
  const mins = t => Math.max(1, Math.round(t.left * minEach(t)));
  const sub = t => t.subText ? t.subText : t.finished ? 'Done · thank you' : `${fmt(t.left)} ${t.unit} left · about ${mins(t)} min`;
  const bar = t => `<div class="hb-bar" aria-hidden="true"><i style="width:${t.total ? Math.round(100 * t.done / t.total) : 0}%"></i></div>`;

  // ---- the one list + panel every tab uses (PG-17) ----------------------------------------------------------------
  // rows: [{id, title, sub, bar}]; laptop: panel on the right; phone: the panel opens right under its row (accordion).
  const wide = () => window.matchMedia('(min-width:960px)').matches;
  function listPanel(tab, rows, selId, fill, o) {
    o = o || {};
    const view = $('#hb-view'), sel = rows.find(r => r.id === selId) || (wide() && !o.noAuto ? rows[0] : null);
    let shown = Math.max(PAGE, sel ? rows.indexOf(sel) + 1 : 0), q = '';
    view.innerHTML = `<div class="hb-wrap">${o.head || ''}<div class="hb-list" role="list">${o.search ? `<input type="search" class="hb-search" placeholder="${esc(o.search)}" aria-label="${esc(o.search)}">` : ''}<div data-rows></div></div>
      <div class="hb-panel" id="hb-panel" hidden></div></div>`;
    const panelEl = $('#hb-panel'), $rows = view.querySelector('[data-rows]');
    function draw() {
      const ql = q.trim().toLowerCase(), list = rows.filter(r => !ql || (r.title + ' ' + (r.find || '')).toLowerCase().includes(ql)), page = list.slice(0, shown);
      $rows.innerHTML = page.map(r => `<button type="button" class="hb-row" role="listitem" data-row="${esc(r.id)}" aria-expanded="${!!(sel && r.id === sel.id)}"${sel && r.id === sel.id ? ' aria-current="true"' : ''}><p class="hb-row-t">${esc(r.title)}</p>${r.sub ? `<p class="hb-row-s">${esc(r.sub)}</p>` : ''}${r.bar || ''}</button>`).join('')
        + (list.length > shown ? `<button type="button" class="hb-ans" data-more>Next ${Math.min(PAGE, list.length - shown)} (${list.length - shown} more)</button>` : '')
        + (!list.length ? '<p class="hb-empty">Nothing matches.</p>' : '');
      $rows.querySelectorAll('[data-row]').forEach(b => b.onclick = () => { location.hash = tab + (sel && sel.id === b.dataset.row && !wide() ? '' : '/' + b.dataset.row); });
      const m = $rows.querySelector('[data-more]'); if (m) m.onclick = () => { shown += PAGE; draw(); };
      if (sel && !wide()) { const row = $rows.querySelector(`[data-row="${CSS.escape(sel.id)}"]`); if (row) row.insertAdjacentElement('afterend', panelEl); }
    }
    const s = view.querySelector('.hb-search'); if (s) s.oninput = () => { q = s.value; shown = PAGE; draw(); };
    draw();
    if (sel) { panelEl.hidden = false; fill(sel, panelEl); if (!wide()) panelEl.scrollIntoView({ block: 'nearest' }); }
  }

  // ---- To do --------------------------------------------------------------------------------------------------
  function setTab(tab) { document.querySelectorAll('.hb-tab').forEach(a => a.setAttribute('aria-selected', String(a.dataset.tab === tab))); }
  function todo(openId) {
    setTab('todo');
    const open = tasks.filter(t => !t.finished);
    if (!open.length) { $('#hb-view').innerHTML = '<p class="hb-empty">Nothing to check right now. Shukran!</p>'; return; }
    listPanel('todo', open.map(t => ({ id: t.id, title: t.title, sub: sub(t), bar: bar(t), t })), openId, (r, p) => panel(r.t, p));
  }
  // every kind of item opens here, with the same module as its old address (no link to another page)
  const MOUNT = {
    after: (b, it, on) => AneesAfterTask.mount(b, it, { onChange: on }),
    before: (b, it, on) => AneesPlanTask.mount(b, it, { onChange: on }),
    review: (b, it, on) => AneesReviewTask.mount(b, { token: it.token, base: '' }, { onChange: on }),
    verb_check: (b, it, on, o) => AneesVerbCheckTask.mount(b, { token: it.token }, { onChange: on, view: o && o.view }),
    word_review: (b, it) => AneesWordReviewTask.mount(b, { token: it.token }),
    listen: (b, it, on) => AneesListenTask.mount(b, { token: it.token, base: '' }, { onChange: on }),
    check: (b, it, on) => AneesCheckTask.mount(b, { token: it.token, base: '', list: it.list }, { onChange: on }),
    verify: b => b.appendChild($('#tv')),
    newwords: (b, it, on) => AneesNewWordsTask.mount(b, NW, { onChange: on }),
    ledger: (b, it, on) => AneesLedgerTask.mount(b, LG, { onChange: on }),
    upload: (b, it, on) => AneesUploadTask.mount(b, UP, { onChange: on }),       // Medi 2026-10-05: "upload flashcards" at the top
    homework: (b, it, on) => AneesHomeworkTask.mount(b, HW, { onChange: on }),   // Medi 2026-10-05: "assign homework" box + his answers
  };
  function panel(t, p) {
    p.innerHTML = `<h2 class="hb-ptitle">${esc(t.title)}</h2><p class="hb-pnote">${esc(sub(t))}</p>${t.item && t.item.what ? `<p class="hb-sub">${esc(t.item.what)}</p>` : ''}<div id="hb-body"></div><div data-earlier></div>`;
    const update = () => {
      const row = document.querySelector(`.hb-row[data-row="${CSS.escape(t.id)}"]`);
      if (row) { row.querySelector('.hb-row-s').textContent = sub(t); row.querySelector('.hb-bar i').style.width = (t.total ? Math.round(100 * t.done / t.total) : 0) + '%'; }
      p.querySelector('.hb-pnote').textContent = sub(t); count();
    };
    const on = s => { t.total = s.total; t.done = Math.min(s.done, s.total); t.left = s.total - t.done; t.finished = s.finished; update(); };
    (MOUNT[t.kind] || ((b) => { b.innerHTML = '<p class="hb-sub">This list cannot be shown yet.</p>'; }))($('#hb-body'), t.item, on);
    earlier(p.querySelector('[data-earlier]'), t.item);
  }
  // a lesson whose first link was replaced by a newer one: the first link's questions and answers, inside the same item
  function earlier(el, it) {
    const E = (it && it.earlier) || [];
    el.innerHTML = E.map((e, i) => `<details class="hb-acc" data-e="${i}"><summary><b>${/made again/.test(e.why) ? 'A second link for this lesson' : 'An earlier link for this lesson'}</b> · ${esc(e.why)} · ${fmt((e.detail || {}).answered)} of ${fmt((e.detail || {}).total)} answered</summary><div class="hb-acc-body"></div></details>`).join('');
    el.querySelectorAll('details').forEach(d => d.addEventListener('toggle', () => {
      if (!d.open || d.dataset.on) return; d.dataset.on = '1';
      const e = E[+d.dataset.e]; accBody(d.querySelector('.hb-acc-body'), { kind: it.kind, lesson_date: it.lesson_date, token: e.token, expires: e.expires, detail: e.detail, why: e.why });
    }));
  }

  // ---- Grammar and Materials: one rule / one section at a time ------------------------------------------------
  async function grammar(id) {
    setTab('grammar');
    $('#hb-view').innerHTML = '<div class="vp-notice">Loading…</div>';
    let G; try { G = await AneesDoc.grammar(''); } catch (e) { $('#hb-view').innerHTML = '<div class="vp-notice">The grammar rules could not load. Refresh to try again.</div>'; return; }
    const g = T.open.find(x => x.kind === 'grammar_notes'), token = g ? g.token : '';
    const rows = [{ id: 'general', title: 'A general note', sub: 'Anything not about one rule', find: 'note' }]
      .concat(G.rules.map(r => ({ id: r.id, title: `${r.id} · ${r.title}`, sub: `${r.family} · ${r.status}`, find: r.family, r })));
    listPanel('grammar', rows, id, (row, p) => {
      p.innerHTML = `<div class="hb-doc">${row.r ? row.r.html : `<h3 class="hb-q">A general note</h3><p class="hb-sub">${esc(G.intro)}</p><div data-general></div>`}</div>`;
      AneesGrammarNotes.start({ token, base: '', scope: p });
    }, { search: 'Find a rule (id, name or family)', head: `<p class="hb-sub hb-span">${esc(G.intro)} Tap a rule to read it and write a note under it.</p>` });
  }
  async function materials(id) {
    setTab('materials');
    $('#hb-view').innerHTML = '<div class="vp-notice">Loading…</div>';
    let M; try { M = await AneesDoc.materials(''); } catch (e) { $('#hb-view').innerHTML = '<div class="vp-notice">The materials could not load. Refresh to try again.</div>'; return; }
    listPanel('materials', M.sections.map(s => ({ id: s.id, title: s.title, s })), id,
      (row, p) => { p.innerHTML = `<div class="hb-doc">${row.s.html}</div><p class="hb-foot">${esc(M.foot)}</p>`; },
      { head: `<p class="hb-sub hb-span">${esc(M.intro.replace(/Medi's grammar rules →$/, ''))}</p>` });
  }

  // ---- Done: accordions -----------------------------------------------------------------------------------------
  // PG-18: what was asked (the moment: time, recording, Medi's line) and the result (her answer, date, what it changed)
  function asked(x) {
    const moment = x.t || x.medi || x.clip ? `<div class="hb-moment"><p class="hb-prog">${x.t ? 'at ' + esc(x.t) : ''}</p>${x.medi ? `<div>Medi: <span lang="ar">${esc(x.medi)}</span></div>` : ''}${x.amal ? `<div>Amal: <span lang="ar">${esc(x.amal)}</span></div>` : ''}<div data-clip="${esc(x.clip || '')}"></div></div>` : '';
    const res = x.answer ? `<p class="hb-ansline">Amal: ${esc(x.answer)}${x.at ? ` · ${esc(pretty(x.at))}` : ''}${x.carried ? ' · carried over from her earlier link' : ''}</p>${x.result ? `<p class="hb-result">Result: ${esc(x.result)}</p>` : ''}`
                         : `<p class="hb-ansline"><i>${esc(x.result || 'not answered')}</i></p>`;
    return `<li><p class="hb-askq"><b>${esc(x.ask || '')}</b>${x.word ? ` · ${esc(x.word)}` : ''}${x.english ? ` <span>(${esc(x.english)})</span>` : ''}</p>${moment}${res}</li>`;
  }
  function readOnly(el, d, why) {
    const A = (d && d.asked) || [];
    el.innerHTML = `<p class="hb-sub">${esc(why || '')}${why ? ' · ' : ''}${fmt((d || {}).answered)} of ${fmt((d || {}).total)} answered</p>`
      + (A.length > PAGE ? `<input type="search" class="hb-search" placeholder="Find a question or answer" aria-label="Find a question or answer">` : '') + '<ul class="hb-done hb-asked" data-asked></ul>';
    let shown = PAGE, q = '';
    const draw = () => {
      const L = A.filter(x => !q || JSON.stringify(x).toLowerCase().includes(q)), page = L.slice(0, shown);
      el.querySelector('[data-asked]').innerHTML = page.map(asked).join('')
        + (L.length > shown ? `<li><button type="button" class="hb-ans" data-more>Next ${Math.min(PAGE, L.length - shown)} (${L.length - shown} more)</button></li>` : '');
      el.querySelectorAll('[data-clip]').forEach(c => { const src = c.dataset.clip; if (!src || !window.AneesClip) return;
        const [f, frag] = src.split('#t='), [st, en] = (frag || '').split(',').map(Number);
        c.appendChild(AneesClip.bar({ src: ANEES.pages + f, start: frag ? st : 0, end: frag ? en : null })); });
      const m = el.querySelector('[data-more]'); if (m) m.onclick = () => { shown += PAGE; draw(); };
    };
    const s = el.querySelector('.hb-search'); if (s) s.oninput = () => { q = s.value.trim().toLowerCase(); shown = PAGE; draw(); };
    draw();
  }
  // the results always; a link that is still open also gets its live list (her answers with Undo) one tap below
  function accBody(el, x) {
    const liveLink = x.token && (!x.expires || x.expires >= today()) && MOUNT[x.kind];
    el.innerHTML = '<div data-res></div>' + (liveLink ? '<details class="hb-acc"><summary><b>Change an answer</b> <span>· Undo is here while the list is open</span></summary><div class="hb-acc-body" data-live></div></details>' : '');
    readOnly(el.querySelector('[data-res]'), x.detail, liveLink ? '' : (x.why ? 'The link has closed (' + x.why + '), so answers cannot be changed' : ''));
    const d = el.querySelector('details');
    if (d) d.addEventListener('toggle', () => { if (d.open && !d.dataset.on) { d.dataset.on = '1'; MOUNT[x.kind](d.querySelector('[data-live]'), x, () => {}, { view: 'done' }); } });
  }
  function doneView() {
    setTab('done');
    const fin = tasks.filter(t => t.finished), C = T.closed || [];
    if (!fin.length && !C.length) { $('#hb-view').innerHTML = '<p class="hb-empty">Nothing finished yet.</p>'; return; }
    const rows = fin.map(t => ({ key: 't:' + t.id, title: t.title, note: `${fmt(t.total)} ${t.unit} answered`, open: () => t }))
      .concat(C.map(c => ({ key: 'c:' + c.id, title: c.title, note: `${c.why}${c.detail ? ` · ${fmt(c.detail.answered)} of ${fmt(c.detail.total)} answered` : ''}`, c })));
    $('#hb-view').innerHTML = `<p class="hb-sub">Tap a row to see what was asked and every answer. Undo works while a list is still open.</p><div class="hb-accs">${rows.map((r, i) =>
      `<details class="hb-acc" data-i="${i}"><summary><b>${esc(r.title)}</b> <span>· ${esc(r.note)}</span></summary><div class="hb-acc-body"></div><div data-earlier></div></details>`).join('')}</div>`;
    document.querySelectorAll('.hb-accs > details').forEach(d => d.addEventListener('toggle', () => {
      if (!d.open || d.dataset.on) return; d.dataset.on = '1';
      const r = rows[+d.dataset.i], body = d.querySelector('.hb-acc-body');
      if (r.c) { accBody(body, r.c); earlier(d.querySelector('[data-earlier]'), r.c); return; }
      const t = r.open();
      if (t.item && t.item.detail) accBody(body, t.item);            // results first, the live list (Undo) one tap below
      else MOUNT[t.kind](body, t.item, () => {}, { view: 'done' });
      earlier(d.querySelector('[data-earlier]'), t.item);
    }));
  }
  function count() {
    $('#hb-n-todo').textContent = tasks.filter(t => !t.finished && !t.quiet).length || '';
    $('#hb-n-done').textContent = (tasks.filter(t => t.finished).length + (T.closed || []).length) || '';
  }
  function hold() { const tv = $('#tv'); if (tv && tv.parentElement.id !== 'hb-hold') $('#hb-hold').appendChild(tv); }
  function route() {
    hold(); window.AneesClip && AneesClip.stopAll();
    const [tab, id] = (decodeURIComponent(location.hash.slice(1)) || 'todo').split('/');
    if (tab === 'grammar') return grammar(id);
    if (tab === 'materials') return materials(id);
    if (tab === 'done') return doneView();
    todo(id);
  }

  let wired = false;
  async function main() {
    try { T = await (await fetch('data/tutor.json', { cache: 'no-store' })).json(); }
    catch (e) { $('#hb-view').innerHTML = '<div class="vp-notice">The Tutor list could not load. Refresh to try again.</div>'; return; }
    const work = T.open.filter(x => ['after', 'before', 'review', 'verb_check', 'word_review', 'listen', 'check'].includes(x.kind));
    const lives = await Promise.all(work.map(live));
    tasks = work.map((it, i) => taskOf(it, lives[i]));
    try {   // the moments to check (tutor-verify): answers are amal_rules rows word_key verify:<uid> on the review token
      const V = await (await fetch('data/amal-verify.json', { cache: 'no-store' })).json(), rv = T.open.find(x => x.kind === 'review');
      const ans = rv ? await rest('amal_rules?select=kind,word_key&source=eq.review&word_key=like.verify:*&order=created_at.asc&token=eq.' + encodeURIComponent(rv.token), rv.token) : [];
      // AM-17: the moments she already answered stay listed (with Undo); latest action per moment wins
      const lat = AneesUndo.latest(ans), seen = new Set(), items = (V.rows || V.items || []).concat(V.answered || []).filter(r => !seen.has(r.id) && seen.add(r.id));
      const isDone = r => { const a = lat[r.id]; return a ? AneesUndo.isAnswer(a) : !!r.answered; };
      verifyN = { total: items.length, done: items.filter(isDone).length };
      if (items.length) tasks.push({ id: 'verify', kind: 'verify', item: {}, title: 'Check these moments', total: verifyN.total, done: verifyN.done, left: verifyN.total - verifyN.done, unit: 'moments', rank: 2, date: '', finished: verifyN.done >= verifyN.total });
    } catch (e) {}
    try {   // new words Amal used that are not on her Doc (Medi 2026-10-02): taps = amal_rules word_key newword:* on the review token
      const N = await (await fetch('data/amal-new-words.json', { cache: 'no-store' })).json(), rv = T.open.find(x => x.kind === 'review');
      const ans = {};
      let live = false;   // AM-17: the latest row per word wins (an undo row = open again); live = the read worked
      if (rv) { (await rest('amal_rules?select=kind,word_key,created_at&source=eq.review&word_key=like.newword:*&order=created_at.asc&token=eq.' + encodeURIComponent(rv.token), rv.token))
        .forEach(r => { ans[r.word_key] = { kind: r.kind, at: r.created_at }; }); live = true; }
      NW = { token: rv ? rv.token : '', data: N, answers: ans, live };
      const c = AneesNewWordsTask.count(N, AneesNewWordsTask.liveView(N, ans, NW.token, live));
      if (c.total) tasks.push({ id: 'newwords', kind: 'newwords', item: {}, title: 'New words from our lessons', total: c.total, done: c.done, left: c.left, unit: 'words', rank: 1.5, date: c.newest, finished: c.left === 0 });
    } catch (e) {}
    try {   // LS-12: "Which word was wrong?" - taps = amal_rules word_key ledger:* on the review token
      const Q = await (await fetch('data/amal-ledger.json', { cache: 'no-store' })).json(), rv = T.open.find(x => x.kind === 'review');
      let rows = [], live = false;
      if (rv) { rows = await rest('amal_rules?select=kind,word_key,payload,created_at&source=eq.review&word_key=like.ledger:*&order=created_at.asc&token=eq.' + encodeURIComponent(rv.token), rv.token); live = true; }
      LG = { token: rv ? rv.token : '', data: Q, answers: AneesLedgerTask.liveView(rows), live };
      const c = AneesLedgerTask.count(Q, LG.answers);
      if (c.total) tasks.push({ id: 'ledger', kind: 'ledger', item: {}, title: 'Which word was wrong?', total: c.total, done: c.done, left: c.left, unit: 'moments', rank: 2.5, date: '', finished: c.left === 0 });
    } catch (e) {}
    try {   // Medi 2026-10-05: "Upload flashcards" (top) + "Assign homework" (his answers to check). Rows are plain anon tables
            // (migration 023); her Tutor link token is kept on each row for provenance only, so she is never blocked.
      const rv = T.open.find(x => x.kind === 'review'), tok = rv ? rv.token : '';
      const J = u => fetch(u, { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null);
      const [U, HT, HR, HV, W, QZ, SH, UJ] = await Promise.all([rest('amal_uploads?select=*&order=created_at.asc', tok).catch(() => null), rest('homework_tasks?select=*&order=created_at.asc', tok).catch(() => null),
        rest('homework_replies?select=*&order=created_at.asc', tok).catch(() => null), rest('homework_verdicts?select=*&order=created_at.asc', tok).catch(() => null),
        J('data/words.json'), J('data/quizlet/amal-quizlet-sets.json'), J('data/shaky-words.json'), J('data/uploads.json')]);
      const live = !!(U && HT && HR && HV);
      const uploads = U || (UJ && UJ.rows) || [];
      UP = { token: tok, uploads, words: (W && W.items) || [], live };
      const SEL = window.AneesCardSelection, H = window.AneesHomework;
      const uSets = H.uploadSets(uploads).map(s => ({ id: s.id, title: s.title, n: s.n, group: 'From Amal' }));
      const shakyN = SH && SH.words ? SH.words.length : 0;
      const qz = SEL && QZ ? SEL.mergeSameTitle((QZ.sets || []).filter(s => !SEL.isDated(s.title) && !/audio homework/i.test(s.title || ''))).sets : [];
      const sets = uSets.concat(shakyN ? [{ id: 'shaky', title: 'Shaky words (last 2 lessons)', n: shakyN, group: 'Weak spots' }] : [], qz.map(s => ({ id: 'q:' + s.id, title: s.title, n: s.n || (s.terms || []).length, group: 'Quizlet' })));
      HW = { token: tok, tasks: HT || [], replies: HR || [], verdicts: HV || [], sets, live };
      const uc = AneesUploadTask.count(uploads), hc = AneesHomeworkTask.count(HW.tasks, HW.replies, HW.verdicts);
      tasks.push({ id: 'upload', kind: 'upload', item: {}, title: 'Upload flashcards', total: uc.total, done: uc.total, left: 0, unit: 'sets', rank: -1, date: '', finished: false, quiet: true,
                   subText: (uc.total ? `${fmt(uc.total)} set${uc.total === 1 ? '' : 's'} uploaded · ` : '') + 'paste a Google link or choose a file' });
      tasks.push({ id: 'homework', kind: 'homework', item: {}, title: 'Assign homework', total: hc.total, done: hc.done, left: hc.waiting, unit: 'answers', rank: -0.5, date: '', finished: false, quiet: !hc.waiting,
                   subText: hc.waiting ? `${fmt(hc.waiting)} answer${hc.waiting === 1 ? '' : 's'} from Medi to check · about ${Math.max(1, hc.waiting)} min` : (hc.total ? `${fmt(hc.total)} assigned · nothing to check` : 'translate · make a sentence · answer a question · cards for a lesson') });
    } catch (e) {}
    rankAll(tasks); count();
    const open = tasks.filter(t => !t.finished && !t.quiet), m = open.reduce((s, t) => s + t.left * minEach(t), 0);
    $('#hb-hello').textContent = open.length ? `Marhaba Amal · ${open.length} thing${open.length === 1 ? '' : 's'} to check, about ${Math.max(1, Math.round(m))} min` : 'Marhaba Amal · nothing to check right now';
    $('#ab-source').textContent = 'Live · ' + new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    if (!wired) { wired = true; window.addEventListener('hashchange', route); route(); }
    else if (onList()) route();
  }
  // rule L1 (2026-10-02): her list, counts and answers are re-read when the tab comes back; the view is re-drawn only on
  // the bare to-do list, so an open task (or a rule, a section, an open accordion) is never reset under her.
  function onList() { const h = decodeURIComponent(location.hash.slice(1)); return !h || h === 'todo'; }
  main();
  window.AneesLive && AneesLive.onReturn(main, { busy: () => !onList() });
})();
