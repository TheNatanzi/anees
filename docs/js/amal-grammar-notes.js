/* Amal's grammar notes, inside Anees (Medi 2026-10-01: nothing Amal uses may live off-site or behind a login).
   1. Her notes from her Google Doc "Mahdi's Grammar Rules notes" (data/amal-grammar-notes.json, built by
      scripts/build_amal_docs.py) show under each rule they are about.
   2. With her Tutor link's token (?t= or #t=) she writes new notes right here, under any rule. Each Save is one row in
      Supabase amal_rules (source grammar_notes, kind note, word_key rule:<id>), sent with the same X-Anees-Token header
      as her review page; offline saves wait in this browser and go out when the page is back online.
   Without a token the notes are read-only and the page says how to get a writing link. */
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const p = new URLSearchParams(location.search), h = new URLSearchParams(location.hash.slice(1));
  const TOKEN = (p.get('t') || h.get('t') || '').trim();
  const Q = 'anees-grammar-notes-q-' + TOKEN;
  const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
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
    return l.length ? `<ul class="an-saved">${l.map(x => `<li><span class="when">${x.waiting ? 'waiting to send' : day(x.at)}</span>${esc(x.text)}</li>`).join('')}</ul>` : '';
  }
  function writer(id, label) {
    return `<details class="an-write" data-rule="${esc(id)}"${(rows[id] || []).length ? ' open' : ''}><summary>✎ ${esc(label)}</summary>
      <div class="an-list">${savedHtml(id)}</div><textarea aria-label="${esc(label)}" placeholder="Write your note here"></textarea>
      <button type="button">Save note</button><span class="an-st" role="status"></span></details>`;
  }
  function refresh(id) { document.querySelectorAll(`.an-write[data-rule="${CSS.escape(id)}"] .an-list`).forEach(el => { el.innerHTML = savedHtml(id); }); }

  async function post(row) {
    const r = await fetch(ANEES.url + '/rest/v1/amal_rules', { method: 'POST', headers: { ...H, Prefer: 'return=minimal' }, body: JSON.stringify(row) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
  }
  async function flush() {
    const q = LS(Q) || []; if (!q.length) return;
    const left = [];
    for (const row of q) { try { await post(row); } catch (e) { left.push(row); } }
    LS(Q, left);
    for (const row of q) if (!left.includes(row)) { const l = rows[row.payload.rule] || []; const x = l.find(y => y.waiting && y.text === row.payload.text); if (x) x.waiting = false; refresh(row.payload.rule); }
  }
  function bind() {
    document.querySelectorAll('.an-write button').forEach(b => b.onclick = async () => {
      const box = b.closest('.an-write'), id = box.dataset.rule, ta = box.querySelector('textarea'), st = box.querySelector('.an-st'), text = ta.value.trim();
      if (!text) { st.textContent = 'Write something first.'; return; }
      const row = { token: TOKEN, source: 'grammar_notes', kind: 'note', word_key: 'rule:' + id, payload: { rule: id, text, page: 'amal/grammar-rules.html' } };
      (rows[id] = rows[id] || []).push({ text, at: new Date().toISOString(), waiting: true }); refresh(id);
      ta.value = ''; st.textContent = 'Saving…';
      try { await post(row); rows[id][rows[id].length - 1].waiting = false; refresh(id); st.textContent = 'Saved. Medi sees it in the app.'; }
      catch (e) { const q = LS(Q) || []; q.push(row); LS(Q, q); st.textContent = 'No connection: kept on this device, it sends when you are back online.'; }
    });
  }

  async function main() {
    let notes = { sections: [] };
    try { notes = await (await fetch('../data/amal-grammar-notes.json', { cache: 'no-store' })).json(); } catch (e) {}
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
          const r = await fetch(ANEES.url + '/rest/v1/amal_rules?select=word_key,payload,created_at&source=eq.grammar_notes&token=eq.' + encodeURIComponent(TOKEN) + '&order=id.asc', { headers: H, cache: 'no-store' });
          if (r.ok) for (const x of await r.json()) add((x.payload && x.payload.rule) || String(x.word_key).replace(/^rule:/, ''), { text: (x.payload || {}).text || '', at: x.created_at });
        } catch (e) {}
        for (const row of LS(Q) || []) (rows[row.payload.rule] = rows[row.payload.rule] || []).push({ text: row.payload.text, at: new Date().toISOString(), waiting: true });
      }
    }
    // her Doc notes under each rule
    for (const s of notes.sections || []) for (const id of s.rules) {
      const art = document.getElementById(id); if (!art) continue;
      const also = s.rules.filter(x => x !== id);
      art.insertAdjacentHTML('beforeend', `<div class="an-doc"><h4>Amal&#39;s notes${also.length ? ' (also on ' + also.map(esc).join(', ') + ')' : ''} · from her Doc, ${esc(notes.source && notes.source.edited ? day(notes.source.edited + 'T12:00') : '')}</h4>${s.html}</div>`);
    }
    // the ask box: where to write, and the materials page
    const ask = document.querySelector('.ask');
    const box = document.createElement('div'); box.className = 'an-box';
    box.innerHTML = canWrite
      ? `<b>Your notes now live here.</b> Write a note under any rule (✎) or below for anything general. Your notes from your Google Doc are shown under each rule. <a href="materials.html">Your Arabic Materials &rarr;</a>${writer('general', 'A general note (anything not about one rule)')}`
      : `<b>Your notes from your Google Doc are shown under each rule.</b> ${TOKEN ? 'This link has expired, so new notes cannot be saved; Medi can send a new one.' : 'To write new notes here, open this page from the Grammar rules link Medi sends you.'} <a href="materials.html">Your Arabic Materials &rarr;</a>`;
    if (ask) ask.insertAdjacentElement('afterend', box);
    if (!canWrite) for (const id of Object.keys(rows)) {
      const art = document.getElementById(id) || (id === 'general' ? box : null); if (!art || !rows[id].length) continue;
      art.insertAdjacentHTML('beforeend', `<div class="an-doc"><h4>Amal&#39;s notes written on this page</h4>${savedHtml(id)}</div>`);
    }
    if (canWrite) {
      document.querySelectorAll('article[id]').forEach(art => {
        const id = art.id, name = (art.querySelector('h3') || {}).textContent || id;
        art.insertAdjacentHTML('beforeend', writer(id, `Your note on ${id} · ${name}`));
      });
      bind(); flush(); window.addEventListener('online', flush);
    }
    // keep the token on in-page links back to this page (materials -> rules keeps working with the same link)
    if (TOKEN) document.querySelectorAll('a[href="materials.html"]').forEach(a => a.href = 'materials.html?t=' + encodeURIComponent(TOKEN));
  }
  main();
})();
