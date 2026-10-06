/* "Upload flashcards" at the top of the Tutor page (Medi 2026-10-05: "Lets add something at the top of the tutor for 'upload
   flashcards' where she can give a google link like this one or she can upload a file"). Amal pastes a Google Sheets / Docs
   link (anyone-with-the-link) or picks a file (xlsx / csv / tsv / txt), or pastes the list. The browser reads it
   (docs/js/sheet-import.js), shows the columns it found (she can change a column's meaning) and the first rows, and she taps
   PERMANENT (the words join the full list: a reminder "add these to the Doc" stays here until the Doc import sees them, Q7)
   or TEMPORARY (cards only, Q6). Saved to Supabase amal_uploads exactly as she wrote it (S1), queued in localStorage first
   so nothing is lost offline; the set appears on Flashcards as its own tile; the hourly job mirrors the table into
   docs/data/uploads.json. Undo = a new row (kind 'undo'), never a delete (AM-17).
   AneesUploadTask.mount(el, {token, uploads, words, live}, {onChange}); AneesUploadTask.count(uploads) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'u' + Date.now().toString(36) + Math.random().toString(36).slice(2));
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  const ROLES = [['arabizi', 'Arabizi'], ['arabic', 'Arabic'], ['english', 'English'], ['plural', 'Plural'], ['notes', 'Notes'], ['', 'skip']];
  const QK = 'anees-uploads-q', AK = 'anees-uploads-local';

  function count(uploads) { const H = root.AneesHomework; const sets = H ? H.uploadSets(uploads) : []; return { total: sets.length, done: sets.length, left: 0 }; }

  function mount(el, ctx, opt) {
    opt = opt || {};
    const SI = root.AneesSheetImport, H = root.AneesHomework, TOKEN = ctx.token || '';
    const HD = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', Prefer: 'return=minimal' };
    const api = (p, b) => fetch(ANEES.url + '/rest/v1/' + p, { method: 'POST', headers: HD, body: JSON.stringify(b) });
    let rows = (ctx.uploads || []).slice(), draft = null, flushing = false, msg = '';
    // rows this browser saved but the server has not shown yet (queue) are kept so her list is right at once
    for (const j of LS(QK) || []) if (!rows.some(r => r.id === j.body.id)) rows.push(j.body);

    async function flush() {
      if (flushing) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await api('amal_uploads', job.body); ok = r.ok || r.status === 409; if (!ok && r.status >= 400 && r.status < 500 && r.status !== 429) { msg = 'The server refused one upload (' + r.status + ').'; LS(QK, q.slice(1)); continue; } } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; render();
    }
    function save(body) { const q = LS(QK) || []; q.push({ id: body.id, body }); LS(QK, q); rows.push(body); flush(); render(); }

    // ---- reading her list -----------------------------------------------------------------------------------------
    async function readLink(url) {
      const info = SI.linkInfo(url);
      if (!info) { note('That is not a Google Sheets or Docs link. Paste the link from the address bar, or upload the file.'); return; }
      note('Reading…');
      const tries = info.kind === 'sheet' ? [info.csvUrl, info.altUrl] : [info.txtUrl];
      for (const u of tries) {
        try {
          const r = await fetch(u, { redirect: 'follow' });
          if (r.ok) { const text = await r.text(); if (/<html/i.test(text.slice(0, 200))) continue; preview(SI.parseText(text), { source: info.kind, source_ref: url.trim(), title: SI.titleOf(url) }); return; }
        } catch (e) { /* next */ }
      }
      note('I could not open this link from here: it is private or Google blocks the read. Two ways: in Google, Share → “Anyone with the link” can view, then try again; or File → Download → CSV (or .xlsx) and upload that file here.');
    }
    async function readFile(f) {
      if (!f) return; note('Reading…');
      try {
        const name = f.name || 'file', ext = (name.match(/\.(\w+)$/) || [])[1] || '';
        const rws = /^xlsx$|^xlsm$/i.test(ext) ? await SI.parseXlsx(await f.arrayBuffer()) : SI.parseText(await f.text());
        preview(rws, { source: 'file', source_ref: name, title: SI.titleOf('', name) });
      } catch (e) { note('I could not read that file (' + (e && e.message || 'unknown') + '). A .csv, .tsv, .txt or .xlsx works.'); }
    }
    function readPaste(text) { if (!String(text || '').trim()) return; preview(SI.parseText(text), { source: 'paste', source_ref: 'pasted list', title: 'Amal’s list' }); }
    function preview(rws, meta) {
      if (!rws || !rws.length) { note('I found no rows in it.'); return; }
      draft = { rows: rws, cols: SI.detectColumns(rws), ...meta }; msg = ''; render();
    }
    function note(t) { msg = t; render(); }

    // ---- her choice: PERMANENT / TEMPORARY ------------------------------------------------------------------------
    function commit(keep) {
      const cards = SI.toCards(draft.rows, draft.cols);
      if (!cards.length) { note('No usable rows: each needs the word and its meaning. Check the column names above.'); return; }
      const title = (el.querySelector('[data-title]') || {}).value || draft.title;
      const body = { id: uuid(), kind: 'upload', title: String(title || draft.title).trim().slice(0, 200), source: draft.source, source_ref: String(draft.source_ref || '').slice(0, 500), keep,
                     columns: { arabizi: draft.cols.arabizi, arabic: draft.cols.arabic, english: draft.cols.english, plural: draft.cols.plural, notes: draft.cols.notes, header: !!draft.cols.header },
                     rows: cards, n: cards.length, token: TOKEN || null, created_at: new Date().toISOString() };
      draft = null; save(body);
    }
    function undo(id) {
      const was = rows.find(r => r.id === id); if (!was) return;
      LS(QK, (LS(QK) || []).filter(j => j.body.id !== id));
      save({ id: uuid(), kind: 'undo', undoes: id, title: was.title, token: TOKEN || null, created_at: new Date().toISOString() });
    }

    // ---- the view ---------------------------------------------------------------------------------------------------
    function previewHtml() {
      const d = draft, width = Math.max(...d.rows.map(r => r.length)), cards = SI.toCards(d.rows, d.cols);
      const head = [...Array(width)].map((_, c) => { const role = Object.keys(d.cols).find(k => k !== 'header' && d.cols[k] === c) || '';
        return `<th><select data-col="${c}" aria-label="Column ${c + 1}">${ROLES.map(([v, l]) => `<option value="${v}"${v === role ? ' selected' : ''}>${l}</option>`).join('')}</select></th>`; }).join('');
      const body = (d.cols.header ? d.rows.slice(1) : d.rows).slice(0, 12).map(r => `<tr>${[...Array(width)].map((_, c) => `<td${/[؀-ۿ]/.test(r[c] || '') ? ' lang="ar" dir="rtl"' : ''}>${esc(r[c] || '')}</td>`).join('')}</tr>`).join('');
      return `<div class="hb-moment" data-preview>
        <p class="hb-prog">${esc(d.source === 'file' ? d.source_ref : d.source === 'paste' ? 'Pasted list' : 'From your ' + (d.source === 'sheet' ? 'Google Sheet' : 'Google Doc'))} · ${cards.length} card${cards.length === 1 ? '' : 's'}${d.cols.header ? ' · first row = column names' : ''}</p>
        <label class="hb-sub" for="up-title">Name of this set</label><input id="up-title" class="hb-input" data-title value="${esc(d.title)}" maxlength="200">
        <p class="hb-sub">Each column: what it holds (change it if I guessed wrong).</p>
        <div class="up-table"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
        ${d.rows.length > 13 ? `<p class="hb-sub">… and ${d.rows.length - 12 - (d.cols.header ? 1 : 0)} more rows</p>` : ''}
        <div class="hb-btns">
          <button type="button" class="hb-ans primary" data-keep="permanent">Save as PERMANENT<small>these words join the full list - a reminder to add them to the Doc stays here until they are in it</small></button>
          <button type="button" class="hb-ans" data-keep="temporary">Save as TEMPORARY<small>cards only, for the next lessons</small></button>
          <button type="button" class="hb-ans drop" data-cancel>Cancel</button>
        </div></div>`;
    }
    function render() {
      const sets = H.uploadSets(rows), pending = new Set((LS(QK) || []).map(j => j.body.id));
      const rem = H.permanentReminder(sets, ctx.words || []), open = rem.filter(c => !c.in_doc);
      el.innerHTML = `<div class="hb-task">
        <p class="hb-sub">Give Medi a flashcard list: paste a Google Sheets or Docs link (share it as “anyone with the link”), choose a file, or paste the words. I read the columns, you check them, then say PERMANENT or TEMPORARY. Your spelling is kept as you wrote it.</p>
        ${draft ? previewHtml() : `<div class="hb-moment">
          <label class="hb-sub" for="up-link">Google Sheets or Docs link</label>
          <div class="up-row"><input id="up-link" class="hb-input" type="url" inputmode="url" placeholder="paste the Sheets or Docs link here" data-link><button type="button" class="hb-ans primary up-go" data-read>Read it</button></div>
          <label class="hb-sub" for="up-file">…or a file (xlsx, csv, tsv, txt)</label><input id="up-file" class="hb-input" type="file" accept=".xlsx,.xlsm,.csv,.tsv,.txt,text/csv,text/plain,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" data-file>
          <label class="hb-sub" for="up-paste">…or paste the list (one card per line: word | عربي | meaning)</label><textarea id="up-paste" class="hb-input" data-paste rows="3" placeholder="Awal | أول | first"></textarea>
          <button type="button" class="hb-ans" data-readpaste>Read the pasted list</button></div>`}
        ${msg ? `<p class="hb-sub" style="color:var(--sabz-danger,#B3261E)">${esc(msg)}</p>` : ''}
        ${open.length ? `<p class="hb-prog" style="margin-top:14px">Add these to the Doc (${open.length})</p><p class="hb-sub">From your PERMANENT uploads, not yet on the vocabulary Doc. They count as on the list once the Doc has them.</p>
          <ul class="hb-done">${open.slice(0, 60).map(c => `<li><b>${esc(c.arabizi)}</b>${c.arabic ? ` <span lang="ar">${esc(c.arabic)}</span>` : ''} <span>· ${esc(c.english)} · ${esc(c.set)}</span></li>`).join('')}${open.length > 60 ? `<li><span>… and ${open.length - 60} more</span></li>` : ''}</ul>` : ''}
        ${sets.length ? `<p class="hb-prog" style="margin-top:14px">Your uploads (${sets.length})</p><ul class="hb-done">${sets.map(s => `<li data-answered="${esc(s.uploadId)}"><b>${esc(s.title)}</b> <span>· ${s.n} cards · ${s.keep === 'permanent' ? 'PERMANENT' : 'TEMPORARY'} · ${esc(pretty(s.created_at))}${pending.has(s.uploadId) ? ' · saving…' : ''} · on Flashcards as its own tile</span>${AneesUndo.button({ 'data-upundo': s.uploadId })}</li>`).join('')}</ul>` : ''}
        <p class="hb-foot">Saved as you tap · nothing changes the Doc by itself</p></div>`;
      const link = el.querySelector('[data-link]'), rd = el.querySelector('[data-read]'), f = el.querySelector('[data-file]'), rp = el.querySelector('[data-readpaste]');
      if (rd) rd.onclick = () => readLink(link.value);
      if (link) link.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); readLink(link.value); } };
      if (f) f.onchange = () => readFile(f.files && f.files[0]);
      if (rp) rp.onclick = () => readPaste(el.querySelector('[data-paste]').value);
      el.querySelectorAll('[data-col]').forEach(s => s.onchange = () => { const c = +s.dataset.col, role = s.value; for (const k of Object.keys(draft.cols)) if (k !== 'header' && draft.cols[k] === c) draft.cols[k] = null; if (role) draft.cols[role] = c; draft.title = el.querySelector('[data-title]').value; render(); });
      el.querySelectorAll('[data-keep]').forEach(b => b.onclick = () => commit(b.dataset.keep));
      const cn = el.querySelector('[data-cancel]'); if (cn) cn.onclick = () => { draft = null; render(); };
      el.querySelectorAll('[data-upundo]').forEach(b => b.onclick = () => undo(b.dataset.upundo));
      opt.onChange && opt.onChange({ total: sets.length, done: sets.length, finished: false });
    }
    if (!document.getElementById('up-css')) { const c = document.createElement('style'); c.id = 'up-css';
      c.textContent = `#anees-bank .up-row{display:flex;gap:8px;align-items:flex-start}#anees-bank .up-row .hb-input{flex:1}#anees-bank .up-go{width:auto;min-height:48px;flex:0 0 auto}
#anees-bank .up-table{overflow:auto;border:1px solid var(--ab-line);border-radius:10px;margin:0 0 10px}#anees-bank .up-table table{border-collapse:collapse;width:100%;font-size:14px}
#anees-bank .up-table th,#anees-bank .up-table td{padding:6px 8px;border-bottom:1px solid var(--ab-line);text-align:left;white-space:nowrap;max-width:260px;overflow:hidden;text-overflow:ellipsis}
#anees-bank .up-table select{font:600 13px var(--sabz-font-sans);padding:6px 8px;border-radius:8px;border:1px solid var(--ab-line);background:var(--ab-bg);color:var(--ab-text);min-height:36px}`;
      document.head.appendChild(c); }
    render(); flush();
  }
  root.AneesUploadTask = { mount, count };
})(typeof window !== 'undefined' ? window : globalThis);
