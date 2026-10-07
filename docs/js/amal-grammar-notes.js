/* Amal's grammar notes, inside Anees (Medi 2026-10-01: nothing Amal uses may live off-site or behind a login).
   1. Her notes from her Google Doc "Mahdi's Grammar Rules notes" (data/amal-grammar-notes.json, built by
      scripts/build_amal_docs.py) show under each rule they are about.
   2. With her Tutor link's token (?t= or #t=) she writes new notes right here, under any rule. Each Save is one row in
      Supabase amal_rules (source grammar_notes, kind note, word_key rule:<id>), sent with the same X-Anees-Token header
      as her review page; offline saves wait in this browser and go out when the page is back online.
   Without a token the notes are read-only and the page says how to get a writing link.
   AM-17 (Medi 2026-10-02 "can you add an undo button to all these tutor hub stuff"): every note she saved here has the
   shared Undo (js/amal-undo.js): a note still waiting to send leaves the queue; a sent one gets an amal_rules row of kind
   'undo' (same token / source / word_key, payload.match {text}) - never a delete. scripts/amal_undo.py makes every reader
   (scripts/build_amal_docs.py written_notes) leave it out; this page hides it at once.
   Medi 2026-10-02 "everything on the tutor hub do what the new words is doing": the Tutor hub's Grammar tab shows one
   rule at a time in its panel with this same code: AneesGrammarNotes.start({token, base, scope}) decorates the rule
   cards inside `scope` (the page runs it on the whole document by itself). */
(function () {
  const root = window;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  let TOKEN = '', Q = '', H = {}, BASE = '../', SCOPE = document;
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return v === undefined ? null : false; } };
  const day = s => new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const css = document.createElement('style');
  css.textContent = `.an-doc{border-left:3px solid var(--green);background:var(--greenbg);border-radius:0 6px 6px 0;padding:8px 12px;margin:12px 0 4px}
.an-doc h4{color:var(--green);margin:0 0 4px}.an-doc ul{margin:0;padding-left:18px;display:grid;gap:3px}.an-doc p{margin:4px 0}.an-doc li.sub{list-style:none}
.an-write{margin-top:10px}.an-write summary{cursor:pointer;color:var(--green);font-weight:500;font-size:14px;min-height:32px;display:flex;align-items:center}
.an-write textarea{width:100%;min-height:84px;font:15px/1.5 inherit;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);margin:6px 0}
.an-write button{font:600 14px system-ui;background:var(--green);color:#fff;border:0;border-radius:6px;padding:9px 16px;min-height:40px;cursor:pointer}
.an-st{font-size:13px;color:var(--muted);margin-left:10px}.an-saved{font-size:14px;margin:6px 0 0;padding-left:18px;display:grid;gap:3px}
.an-saved .when{font-size:11px;color:var(--muted);margin-right:6px}.an-box{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:0 0 18px;max-width:72ch}`;
  document.head.appendChild(css);

  const rows = {};               // rule id -> saved notes [{text, at, waiting}]
  let canWrite = false;

  function savedHtml(id) {
    const l = rows[id] || [];
    const undo = (x, i) => canWrite && root.AneesUndo ? AneesUndo.button({ 'data-note-undo': id, 'data-i': i }) : '';
    return l.length ? `<ul class="an-saved">${l.map((x, i) => `<li data-answered="note"><span><span class="when">${x.waiting ? 'waiting to send' : day(x.at)}</span>${esc(x.text)}</span>${undo(x, i)}</li>`).join('')}</ul>` : '';
  }
  function writer(id, label) {
    return `<details class="an-write" data-rule="${esc(id)}"${(rows[id] || []).length ? ' open' : ''}><summary>✎ ${esc(label)}</summary>
      <div class="an-list">${savedHtml(id)}</div><textarea aria-label="${esc(label)}" placeholder="Write your note here"></textarea>
      <button type="button">Save note</button><span class="an-st" role="status"></span></details>`;
  }
  function refresh(id) { SCOPE.querySelectorAll(`.an-write[data-rule="${CSS.escape(id)}"] .an-list`).forEach(el => { el.innerHTML = savedHtml(id); }); }

  async function post(row) {
    const r = await fetch(ANEES.url + '/rest/v1/amal_rules', { method: 'POST', headers: { ...H, Prefer: 'return=minimal' }, body: JSON.stringify(row) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
  }
  async function flush() {
    const q = LS(Q) || []; if (!q.length) return;
    const left = [];
    for (const row of q) { try { await post(row); } catch (e) { left.push(row); } }
    LS(Q, left);
    for (const row of q) if (!left.includes(row) && row.kind === 'note') { const l = rows[row.payload.rule] || []; const x = l.find(y => y.waiting && y.text === row.payload.text); if (x) x.waiting = false; refresh(row.payload.rule); }
  }
  // AM-17: Undo one saved note
  function undoNote(id, i) {
    const l = rows[id] || [], x = l[i]; if (!x) return;
    l.splice(i, 1); refresh(id);
    const q = LS(Q) || [], j = q.findIndex(r => r.payload.rule === id && r.payload.text === x.text && r.kind === 'note');
    if (j >= 0 && x.waiting) { q.splice(j, 1); LS(Q, q); return; }
    const row = AneesUndo.row({ token: TOKEN, source: 'grammar_notes', lesson_date: null, kind: 'note', word_key: 'rule:' + id, payload: { rule: id, text: x.text } }, { text: x.text });
    post(row).catch(() => { const q2 = LS(Q) || []; q2.push(row); LS(Q, q2); });
  }
  document.addEventListener('click', e => { const b = e.target.closest('[data-note-undo]'); if (b) undoNote(b.dataset.noteUndo, +b.dataset.i); });
  function bind() {
    SCOPE.querySelectorAll('.an-write button').forEach(b => b.onclick = async () => {
      const box = b.closest('.an-write'), id = box.dataset.rule, ta = box.querySelector('textarea'), st = box.querySelector('.an-st'), text = ta.value.trim();
      if (!text) { st.textContent = 'Write something first.'; return; }
      const row = { token: TOKEN, source: 'grammar_notes', kind: 'note', word_key: 'rule:' + id, payload: { rule: id, text, page: 'amal/grammar-rules.html' } };
      (rows[id] = rows[id] || []).push({ text, at: new Date().toISOString(), waiting: true }); refresh(id);
      ta.value = ''; st.textContent = 'Saving…';
      try { await post(row); rows[id][rows[id].length - 1].waiting = false; refresh(id); st.textContent = 'Saved. The student sees it in the app.'; }
      catch (e) { const q = LS(Q) || []; q.push(row); LS(Q, q); st.textContent = 'No connection: kept on this device, it sends when you are back online.'; }
    });
  }

  const art = id => SCOPE.querySelector('article[id="' + CSS.escape(id) + '"]');
  let wiredOnline = false;
  async function start(o) {
    o = o || {};
    TOKEN = String(o.token || '').trim(); Q = 'anees-grammar-notes-q-' + TOKEN; BASE = o.base == null ? '../' : o.base; SCOPE = o.scope || document;
    H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    for (const k of Object.keys(rows)) delete rows[k];
    canWrite = false;
    let notes = { sections: [] };
    try { notes = await (await fetch(BASE + 'data/amal-grammar-notes.json', { cache: 'no-store' })).json(); } catch (e) {}
    // notes she already saved here (built into the data file, so they stay when her link's token changes)
    const add = (id, x) => { const l = rows[id] = rows[id] || []; if (!l.some(y => y.text === x.text)) l.push(x); };
    for (const w of notes.written || []) add(w.rule, { text: w.text, at: w.at });
    if (TOKEN) {
      try {
        const r = await fetch(ANEES.url + '/rest/v1/amal_links?select=expires_at&token=eq.' + encodeURIComponent(TOKEN), { headers: H, cache: 'no-store' });
        canWrite = r.ok && (await r.json()).length > 0;
      } catch (e) { canWrite = !!(LS(Q) || []).length; }
      if (canWrite) {
        try {
          const r = await fetch(ANEES.url + '/rest/v1/amal_rules?select=kind,word_key,payload,created_at&source=eq.grammar_notes&token=eq.' + encodeURIComponent(TOKEN) + '&order=id.asc', { headers: H, cache: 'no-store' });
          if (r.ok) for (const x of await r.json()) {
            const rid = (x.payload && x.payload.rule) || String(x.word_key).replace(/^rule:/, ''), text = (x.payload || {}).text || ((x.payload || {}).match || {}).text || '';
            if (x.kind === 'undo') { rows[rid] = (rows[rid] || []).filter(y => y.text !== text); continue; }   // AM-17: an undone note leaves
            add(rid, { text, at: x.created_at });
          }
        } catch (e) {}
        for (const row of LS(Q) || []) if (row.kind === 'note') (rows[row.payload.rule] = rows[row.payload.rule] || []).push({ text: row.payload.text, at: new Date().toISOString(), waiting: true });
      }
    }
    // her Doc notes under each rule
    for (const s of notes.sections || []) for (const id of s.rules) {
      const a = art(id); if (!a) continue;
      const also = s.rules.filter(x => x !== id);
      a.insertAdjacentHTML('beforeend', `<div class="an-doc"><h4>The tutor&#39;s notes${also.length ? ' (also on ' + also.map(esc).join(', ') + ')' : ''} · from her Doc, ${esc(notes.source && notes.source.edited ? day(notes.source.edited + 'T12:00') : '')}</h4>${s.html}</div>`);
    }
    // the ask box: where to write, and the materials page
    const ask = SCOPE.querySelector('.ask');
    const box = document.createElement('div'); box.className = 'an-box';
    // inside the Tutor hub the materials are a tab of the same page (PG-17), never another page
    const mat = SCOPE === document ? '<a href="materials.html">Your Arabic Materials &rarr;</a>' : '<a href="#materials">Your Arabic Materials &rarr;</a>';
    box.innerHTML = canWrite
      ? `<b>Your notes now live here.</b> Write a note under any rule (✎) or below for anything general. Your notes from your Google Doc are shown under each rule. ${mat}${writer('general', 'A general note (anything not about one rule)')}`
      : `<b>Your notes from your Google Doc are shown under each rule.</b> ${TOKEN ? 'This link has expired, so new notes cannot be saved; the student can send a new one.' : 'To write new notes here, open this page from the Grammar rules link the student sends you.'} ${mat}`;
    if (ask) ask.insertAdjacentElement('afterend', box);
    else if (SCOPE.querySelector('[data-general]')) SCOPE.querySelector('[data-general]').appendChild(box);
    if (!canWrite) for (const id of Object.keys(rows)) {
      const a = art(id) || (id === 'general' && box.isConnected ? box : null); if (!a || !rows[id].length) continue;
      a.insertAdjacentHTML('beforeend', `<div class="an-doc"><h4>The tutor&#39;s notes written on this page</h4>${savedHtml(id)}</div>`);
    }
    if (canWrite) {
      SCOPE.querySelectorAll('article[id]').forEach(a => {
        const id = a.id, name = (a.querySelector('h3') || {}).textContent || id;
        a.insertAdjacentHTML('beforeend', writer(id, `Your note on ${id} · ${name}`));
      });
      bind(); flush(); if (!wiredOnline) { wiredOnline = true; window.addEventListener('online', flush); }
    }
    // keep the token on in-page links back to this page (materials -> rules keeps working with the same link)
    if (TOKEN) SCOPE.querySelectorAll('a[href="materials.html"]').forEach(a => a.href = 'materials.html?t=' + encodeURIComponent(TOKEN));
    return { canWrite, notes: rows };
  }
  root.AneesGrammarNotes = { start };
  // the rules page itself (amal/grammar-rules.html): the whole document, token from ?t= / #t=
  if (/grammar-rules\.html$/.test(location.pathname)) {
    const p = new URLSearchParams(location.search), h = new URLSearchParams(location.hash.slice(1));
    start({ token: p.get('t') || h.get('t') || '', base: '../', scope: document });
  }
})();
