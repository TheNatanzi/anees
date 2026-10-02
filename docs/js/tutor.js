/* Tutor hub (Medi 2026-10-01): one page for Amal and Medi. Tabs: To do · Grammar · Materials · Done.
   To do = every list waiting on Amal, ranked (what holds up Medi's scores first: newest lesson, older lessons, the
   moments to check, slip patterns, then the long verb list). A task opens INSIDE the hub (laptop: list left, task right;
   phone: the task replaces the list). Facts come from data/tutor.json (scripts/build_tutor_data.py); done counts are
   read live from Supabase with each list's own token. Address: tutor.html#todo/<task id>, #grammar, #materials, #done. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = n => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('en-US');
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  let T = { open: [], closed: [] }, tasks = [], verifyN = null, NW = null;

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
          .filter(r => !/^(verify|newword):/.test(String(r.word_key || '')));
        return { ok: true, done: Object.values(AneesUndo.latest(rows)).filter(AneesUndo.isAnswer).length };
      }
    } catch (e) { return { ok: false, done: 0 }; }
    return { ok: true, done: 0 };
  }

  // ---- the task list -------------------------------------------------------------------------------------------
  const MIN_EACH = { after: 0.7, before: 0.7, verify: 0.4, review: 1.2, verb_check: 0.1, word_review: 0.3, newwords: 0.3 };
  function taskOf(it, L) {
    const total = it.total || 0, d = Math.min(total, (L && L.done) || 0), left = Math.max(0, total - d);
    const unit = { after: 'moments', before: 'questions', review: 'slip patterns', verb_check: 'verb forms', word_review: 'lines' }[it.kind] || 'items';
    const title = it.kind === 'after' ? 'After the lesson · ' + pretty(it.lesson_date)
      : it.kind === 'review' ? 'Slips to review' : it.kind === 'verb_check' ? it.title.replace('Verb check', 'Verb forms') : it.title;
    const rank = it.kind === 'before' ? 0 : it.kind === 'after' ? 1 : it.kind === 'review' ? 3 : it.kind === 'word_review' ? 4 : 5;
    return { id: it.id, kind: it.kind, item: it, title, total, done: d, left, unit, rank, date: it.lesson_date || '', finished: (L && L.finished) || (total > 0 && left === 0) };
  }
  function rankAll(list) { return list.sort((a, b) => a.rank - b.rank || String(b.date).localeCompare(String(a.date))); }
  const sub = t => t.finished ? 'Done · thank you' : `${fmt(t.left)} ${t.unit} left · about ${Math.max(1, Math.round(t.left * (MIN_EACH[t.kind] || 0.5)))} min`;
  const bar = t => `<div class="hb-bar" aria-hidden="true"><i style="width:${t.total ? Math.round(100 * t.done / t.total) : 0}%"></i></div>`;
  const rowHtml = (t, cur) => `<button type="button" class="hb-row" data-task="${esc(t.id)}"${cur ? ' aria-current="true"' : ''}><p class="hb-row-t">${esc(t.title)}</p><p class="hb-row-s">${esc(sub(t))}</p>${bar(t)}</button>`;

  // ---- views ---------------------------------------------------------------------------------------------------
  function setTab(tab) { document.querySelectorAll('.hb-tab').forEach(a => a.setAttribute('aria-selected', String(a.dataset.tab === tab))); }
  function todo(openId) {
    setTab('todo');
    const open = tasks.filter(t => !t.finished);
    if (!open.length) { $('#hb-view').innerHTML = '<p class="hb-empty">Nothing to check right now. Shukran!</p>'; return; }
    const wide = window.matchMedia('(min-width:960px)').matches, sel = open.find(t => t.id === openId) || (wide ? open[0] : null);
    $('#hb-view').innerHTML = `<div class="hb-wrap${openId && sel ? ' hb-open' : ''}"><div class="hb-list" role="list">${open.map(t => rowHtml(t, sel && t.id === sel.id)).join('')}</div>
      <div class="hb-panel" id="hb-panel"></div></div>`;
    document.querySelectorAll('.hb-row').forEach(b => b.onclick = () => { location.hash = 'todo/' + b.dataset.task; });
    if (sel) panel(sel);
  }
  function panel(t) {
    const p = $('#hb-panel');
    p.innerHTML = `<button type="button" class="hb-back">‹ To do</button><h2 class="hb-ptitle">${esc(t.title)}</h2><p class="hb-pnote">${esc(sub(t))}</p><div id="hb-body"></div>`;
    p.querySelector('.hb-back').onclick = () => { location.hash = 'todo'; };
    const body = $('#hb-body');
    const update = () => {
      const row = document.querySelector(`.hb-row[data-task="${CSS.escape(t.id)}"]`);
      if (row) { row.querySelector('.hb-row-s').textContent = sub(t); row.querySelector('.hb-bar i').style.width = (t.total ? Math.round(100 * t.done / t.total) : 0) + '%'; }
      p.querySelector('.hb-pnote').textContent = sub(t); count();
    };
    if (t.kind === 'after') {
      AneesAfterTask.mount(body, t.item, { onChange: s => { t.total = s.total; t.done = Math.min(s.done, s.total); t.left = s.total - t.done; t.finished = s.finished; update(); } });
    } else if (t.kind === 'verify') {
      body.appendChild($('#tv'));
    } else if (t.kind === 'newwords') {
      AneesNewWordsTask.mount(body, NW, { onChange: s => { t.total = s.total; t.done = s.done; t.left = s.total - s.done; t.finished = s.finished; update(); } });
    } else {
      // Not rebuilt inside the hub yet (Medi 2026-10-01 plan: one task at a time, shown before the next).
      body.innerHTML = `<p class="hb-sub">${esc(t.item.what || '')}</p><a class="hb-ans primary" style="display:block;text-decoration:none;text-align:center" href="go.html?to=${
        t.kind === 'review' ? 'review' : t.kind === 'word_review' ? 'word-review' : t.kind === 'before' ? 'before' : (t.id.endsWith('-2') ? 'verb-check-2' : 'verb-check')}">Open this list</a>`;
    }
  }
  function hold() { const tv = $('#tv'); if (tv && tv.parentElement.id !== 'hb-hold') $('#hb-hold').appendChild(tv); }
  function frame(tab, url) {
    setTab(tab);
    $('#hb-view').innerHTML = `<iframe class="hb-frame" title="${tab === 'grammar' ? 'Grammar rules' : 'Arabic Materials'}" src="${esc(url)}"></iframe>`;
    const f = $('.hb-frame');
    f.onload = () => { try { const d = f.contentDocument; d.documentElement.style.overflow = 'hidden'; const fit = () => { f.style.height = d.documentElement.scrollHeight + 'px'; }; fit(); new ResizeObserver(fit).observe(d.body); } catch (e) {} };
  }
  function doneView() {
    setTab('done');
    const fin = tasks.filter(t => t.finished);
    $('#hb-view').innerHTML = (fin.length || (T.closed || []).length)
      ? `<ul class="hb-done">${fin.map(t => `<li><b>${esc(t.title)}</b> <span>· ${fmt(t.total)} ${esc(t.unit)} answered</span></li>`).join('')}${(T.closed || []).map(c => `<li><b>${esc(c.title)}</b> <span>· ${esc(c.why)}</span></li>`).join('')}</ul>`
      : '<p class="hb-empty">Nothing finished yet.</p>';
  }
  function count() {
    $('#hb-n-todo').textContent = tasks.filter(t => !t.finished).length || '';
    $('#hb-n-done').textContent = (tasks.filter(t => t.finished).length + (T.closed || []).length) || '';
  }
  function route() {
    hold(); window.AneesClip && AneesClip.stopAll();
    const [tab, id] = (decodeURIComponent(location.hash.slice(1)) || 'todo').split('/');
    const g = T.open.find(x => x.kind === 'grammar_notes'), m = T.open.find(x => x.kind === 'materials');
    if (tab === 'grammar') return frame('grammar', (g ? g.url + '&' : 'amal/grammar-rules.html?') + 'in=hub');
    if (tab === 'materials') return frame('materials', (m ? m.url : 'amal/materials.html') + '?in=hub');
    if (tab === 'done') return doneView();
    todo(id);
  }

  let wired = false;
  async function main() {
    try { T = await (await fetch('data/tutor.json', { cache: 'no-store' })).json(); }
    catch (e) { $('#hb-view').innerHTML = '<div class="vp-notice">The Tutor list could not load. Refresh to try again.</div>'; return; }
    const work = T.open.filter(x => ['after', 'before', 'review', 'verb_check', 'word_review'].includes(x.kind));
    const lives = await Promise.all(work.map(live));
    tasks = work.map((it, i) => taskOf(it, lives[i]));
    try {   // the moments to check (tutor-verify): answers are amal_rules rows word_key verify:<uid> on the review token
      const V = await (await fetch('data/amal-verify.json', { cache: 'no-store' })).json(), rv = T.open.find(x => x.kind === 'review');
      const ans = rv ? await rest('amal_rules?select=kind,word_key&source=eq.review&word_key=like.verify:*&order=created_at.asc&token=eq.' + encodeURIComponent(rv.token), rv.token) : [];
      // AM-17: the moments she already answered stay listed (with Undo); latest action per moment wins
      const lat = AneesUndo.latest(ans), seen = new Set(), items = (V.rows || V.items || []).concat(V.answered || []).filter(r => !seen.has(r.id) && seen.add(r.id));
      const isDone = r => { const a = lat[r.id]; return a ? AneesUndo.isAnswer(a) : !!r.answered; };
      verifyN = { total: items.length, done: items.filter(isDone).length };
      if (items.length) tasks.push({ id: 'verify', kind: 'verify', title: 'Check these moments', total: verifyN.total, done: verifyN.done, left: verifyN.total - verifyN.done, unit: 'moments', rank: 2, date: '', finished: verifyN.done >= verifyN.total });
    } catch (e) {}
    try {   // new words Amal used that are not on her Doc (Medi 2026-10-02): taps = amal_rules word_key newword:* on the review token
      const N = await (await fetch('data/amal-new-words.json', { cache: 'no-store' })).json(), rv = T.open.find(x => x.kind === 'review');
      const ans = {};
      let live = false;   // AM-17: the latest row per word wins (an undo row = open again); live = the read worked
      if (rv) { (await rest('amal_rules?select=kind,word_key,created_at&source=eq.review&word_key=like.newword:*&order=created_at.asc&token=eq.' + encodeURIComponent(rv.token), rv.token))
        .forEach(r => { ans[r.word_key] = { kind: r.kind, at: r.created_at }; }); live = true; }
      NW = { token: rv ? rv.token : '', data: N, answers: ans, live };
      const c = AneesNewWordsTask.count(N, AneesNewWordsTask.liveView(N, ans, NW.token, live));
      if (c.total) tasks.push({ id: 'newwords', kind: 'newwords', title: 'New words from our lessons', total: c.total, done: c.done, left: c.left, unit: 'words', rank: 1.5, date: c.newest, finished: c.left === 0 });
    } catch (e) {}
    rankAll(tasks); count();
    const open = tasks.filter(t => !t.finished), mins = Math.max(1, Math.round(open.reduce((s, t) => s + t.left * (MIN_EACH[t.kind] || 0.5), 0)));
    $('#hb-hello').textContent = open.length ? `Marhaba Amal · ${open.length} thing${open.length === 1 ? '' : 's'} to check, about ${mins} min` : 'Marhaba Amal · nothing to check right now';
    $('#ab-source').textContent = 'Live · ' + new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    if (!wired) { wired = true; window.addEventListener('hashchange', route); route(); }
    else if (onList()) route();
  }
  // rule L1 (2026-10-02): her list, counts and answers are re-read when the tab comes back; the view is re-drawn only on
  // the bare to-do list, so an open task (or the grammar / materials frame) is never reset under her.
  function onList() { const h = decodeURIComponent(location.hash.slice(1)); return !h || h === 'todo' || h === 'done'; }
  main();
  window.AneesLive && AneesLive.onReturn(main, { busy: () => !onList() });
})();
