/* "Questions from the student" on Amal's Tutor To do (Medi 2026-10-06: "For all the cards I want a third option called
   attention with the attention icon. This will send a to do message where I can ask Amal a questions or bring up a concern
   with her. This should be sent to the tutor portal"). Rows live in Supabase card_attention (migration 024, append-only):
   his note (kind note, by_who student) with the card; her reply (kind reply, ref = the note) typed here; Undo = a new row
   (kind undo) as everywhere (AM-17). A note counts as answered when it has a reply that is not undone. The Student tab
   shows her replies under his questions.
   AneesAttentionTask.mount(el, {token, rows}, {onChange}); AneesAttentionTask.view(rows) -> {open, answered} */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2));
  const pretty = d => d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  const QK = 'anees-attention-q';
  // the effective rows (undo rows hide their target; undo of an undo puts it back), then notes with their live replies
  function view(rows) {
    const H = root.AneesHomework;
    const live = H ? H.effective(rows) : (rows || []).filter(r => r.kind !== 'undo');
    const notes = live.filter(r => r.kind === 'note').sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
    const replies = live.filter(r => r.kind === 'reply');
    const out = notes.map(n => ({ ...n, replies: replies.filter(r => r.ref === n.id).sort((a, b) => String(a.created_at).localeCompare(String(b.created_at))) }));
    return { all: out, open: out.filter(n => !n.replies.length), answered: out.filter(n => n.replies.length) };
  }
  function count(rows) { const v = view(rows); return { total: v.all.length, done: v.answered.length, left: v.open.length }; }
  function mount(el, ctx, opt) {
    opt = opt || {};
    const HD = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', Prefer: 'return=minimal' };
    let rows = (ctx.rows || []).slice(), flushing = false, msg = '';
    for (const j of LS(QK) || []) if (!rows.some(r => r.id === j.body.id)) rows.push(j.body);
    async function flush() {
      if (flushing) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await fetch(ANEES.url + '/rest/v1/card_attention', { method: 'POST', headers: HD, body: JSON.stringify(job.body) }); ok = r.ok || r.status === 409; if (!ok && r.status >= 400 && r.status < 500 && r.status !== 429) { msg = 'The server refused one row (' + r.status + ').'; LS(QK, q.slice(1)); continue; } } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; render();
    }
    function save(body) { const q = LS(QK) || []; q.push({ id: body.id, body }); LS(QK, q); rows.push(body); flush(); render(); }
    function reply(note) {
      const ta = el.querySelector(`[data-reply="${CSS.escape(note.id)}"]`), text = (ta && ta.value || '').trim(); if (!text) { msg = 'Write the reply first.'; render(); return; }
      msg = ''; save({ id: uuid(), kind: 'reply', ref: note.id, card_key: note.card_key, text: text.slice(0, 2000), by_who: 'teacher', token: ctx.token || null, created_at: new Date().toISOString() });
    }
    function undo(id) { LS(QK, (LS(QK) || []).filter(j => j.body.id !== id)); save({ id: uuid(), kind: 'undo', undoes: id, by_who: 'teacher', token: ctx.token || null, created_at: new Date().toISOString() }); }
    const card = n => `<div class="hb-big">${esc(n.arabizi || '')}</div>${n.arabic ? `<div class="hb-ar" lang="ar">${esc(n.arabic)}</div>` : ''}${n.english ? `<div class="hb-en">${esc(n.english)}</div>` : ''}`;
    function render() {
      const v = view(rows), pending = new Set((LS(QK) || []).map(j => j.body.id)), c = count(rows);
      el.innerHTML = `<div class="hb-task"><p class="hb-sub">Questions and concerns the student sent from a flashcard (the ⚠ button). Reply in a line; it shows on the Student tab.</p>
        ${v.open.length ? v.open.map(n => `<div class="hb-moment"><p class="hb-prog">${esc(pretty(n.created_at))} · from the flashcard</p>${card(n)}
          <div class="hb-why"><b>Student:</b> <span dir="auto">${esc(n.text)}</span></div>
          <textarea class="hb-input" data-reply="${esc(n.id)}" rows="2" dir="auto" placeholder="Your reply"></textarea>
          <div class="hb-btns"><button type="button" class="hb-ans primary" data-send="${esc(n.id)}">Reply</button></div></div>`).join('') : '<p class="hb-empty">No open questions from the student.</p>'}
        ${msg ? `<p class="hb-sub" style="color:var(--sabz-danger,#B3261E)">${esc(msg)}</p>` : ''}
        ${v.answered.length ? `<p class="hb-prog" style="margin-top:14px">Answered (${v.answered.length})</p><ul class="hb-done">${v.answered.slice(-30).reverse().map(n => n.replies.map(r => `<li data-answered="${esc(r.id)}"><span><b>${esc(n.arabizi || n.arabic)}</b> · ${esc(n.text)}<br>You: <span dir="auto">${esc(r.text)}</span> · ${esc(pretty(r.created_at))}${pending.has(r.id) ? ' · saving…' : ''}</span>${AneesUndo.button({ 'data-aundo': r.id })}</li>`).join('')).join('')}</ul>` : ''}
        <p class="hb-foot">Saved as you tap · nothing is sent to anyone</p></div>`;
      el.querySelectorAll('[data-send]').forEach(b => b.onclick = () => { const n = v.open.find(x => x.id === b.dataset.send); if (n) reply(n); });
      el.querySelectorAll('[data-aundo]').forEach(b => b.onclick = () => undo(b.dataset.aundo));
      opt.onChange && opt.onChange({ total: c.total, done: c.done, finished: c.total > 0 && c.left === 0 });
    }
    render(); flush();
  }
  root.AneesAttentionTask = { mount, count, view };
})(typeof window !== 'undefined' ? window : globalThis);
