/* View a card set (Medi 2026-10-28: "a view card set button that puts all the cards in a grid with front back next to each
   other and a way to edit cards, add cards, remove cards"). One module for Flashcards (the student) and the Tutor page (the
   tutor). A set she uploaded can be edited: change a card, add one, remove one. Save checks every card first (no blank
   side, no mixed-up sides: AneesHomework.checkCards) and writes ONE new amal_uploads row (kind 'edit', undoes = the upload,
   rows = the whole new list; append-only, an undo takes it back). Each card keeps its place key (cid), so its card history
   stays. A set from her vocabulary Doc is view only, with a note that its cards are changed in the Doc.
   AneesSetView.open(el, {title, cards: [{cid, arabizi, arabic, english, plural, notes}], note, back,
                          edit: {uploadId, by: 'student'|'tutor', token} | null, onSaved(row), onClose}) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const uuid = () => (root.crypto && crypto.randomUUID ? crypto.randomUUID() : 'u' + Date.now().toString(36) + Math.random().toString(36).slice(2));
  const QK = 'anees-uploads-q';           // the same offline queue the Tutor page's upload task replays (docs/js/hub/upload-task.js)
  const FIELDS = ['arabizi', 'arabic', 'english'];

  let flushing = false;
  async function flush() {
    if (flushing || !root.ANEES) return; flushing = true;
    const HD = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', Prefer: 'return=minimal' };
    try {
      for (let tries = 0; tries < 20; tries++) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false, drop = false;
        try { const r = await fetch(ANEES.url + '/rest/v1/amal_uploads', { method: 'POST', headers: HD, body: JSON.stringify(job.body) });
              ok = r.ok || r.status === 409; drop = !ok && r.status >= 400 && r.status < 500 && r.status !== 429; } catch (e) { ok = false; }
        if (ok || drop) { LS(QK, (LS(QK) || []).filter(x => x.id !== job.id)); continue; }
        await new Promise(r => setTimeout(r, 2500));
      }
    } finally { flushing = false; }
  }
  function queue(body) { const q = LS(QK) || []; q.push({ id: body.id, body }); LS(QK, q); flush(); }

  function open(el, o) {
    o = o || {};
    const H = root.AneesHomework, canEdit = !!(o.edit && o.edit.uploadId);
    let list = (o.cards || []).map(c => ({ cid: String(c.cid ?? ''), arabizi: String(c.arabizi || ''), arabic: String(c.arabic || ''), english: String(c.english || ''),
                                           plural: String(c.plural || ''), notes: String(c.notes || ''), state: 'same' }));
    const before = new Map(list.map(c => [c.cid, FIELDS.map(f => c[f]).join('\u0001')]));
    let editing = -1, msg = '', saved = '';

    const changes = () => list.filter(c => c.state !== 'same').length;
    function cardHtml(c, i) {
      if (i === editing) return `<div class="sv-row sv-editing" data-i="${i}">
          <label class="sv-lab">Front · Arabizi<input class="sv-in" data-f="arabizi" value="${esc(c.arabizi)}" autocomplete="off"></label>
          <label class="sv-lab">Front · Arabic<input class="sv-in" data-f="arabic" dir="rtl" lang="ar" value="${esc(c.arabic)}" autocomplete="off"></label>
          <label class="sv-lab">Back · English<input class="sv-in" data-f="english" value="${esc(c.english)}" autocomplete="off"></label>
          <div class="sv-btns"><button type="button" class="primary" data-done>Done</button><button type="button" data-undoedit>Cancel</button></div></div>`;
      const gone = c.state === 'removed', tag = c.state === 'new' ? 'new' : c.state === 'changed' ? 'changed' : gone ? 'removed' : '';
      return `<div class="sv-row${gone ? ' sv-gone' : ''}" data-i="${i}">
        <div class="sv-face sv-front"><span class="sv-n">${i + 1}${tag ? ' · ' + tag : ''}</span>${c.arabizi ? `<b dir="auto">${esc(c.arabizi)}</b>` : ''}${c.arabic ? `<span class="sv-ar" dir="rtl" lang="ar">${esc(c.arabic)}</span>` : ''}${!c.arabizi && !c.arabic ? '<i>blank</i>' : ''}</div>
        <div class="sv-face sv-back">${c.english ? esc(c.english) : '<i>blank</i>'}</div>
        ${canEdit ? `<div class="sv-act">${gone ? `<button type="button" data-restore aria-label="Put card ${i + 1} back" title="Put it back">↺</button>`
          : `<button type="button" data-edit aria-label="Edit card ${i + 1}" title="Edit">✎</button><button type="button" data-remove aria-label="Remove card ${i + 1}" title="Remove">✕</button>`}</div>` : ''}</div>`;
    }
    function render() {
      const n = list.filter(c => c.state !== 'removed').length, k = changes();
      el.innerHTML = `<div class="sv">
        <button type="button" class="fc-back" data-close>‹ ${esc(o.back || 'Back')}</button>
        <h1>${esc(o.title || 'Card set')}</h1><p class="mute">${n} card${n === 1 ? '' : 's'} · front and back side by side${canEdit ? ' · tap ✎ to change a card, ✕ to remove it' : ''}</p>
        ${o.note ? `<div class="sv-note" role="note">${o.note}</div>` : ''}
        ${saved ? `<p class="sv-ok">${esc(saved)}</p>` : ''}
        <div class="sv-head${canEdit ? ' sv-3' : ''}"><span>Front · Arabic</span><span>Back · English</span>${canEdit ? '<span></span>' : ''}</div>
        <div class="sv-grid${canEdit ? ' sv-can' : ''}">${list.map(cardHtml).join('')}</div>
        ${canEdit ? '<button type="button" class="sv-add" data-add>+ Add a card</button>' : ''}
        ${msg ? `<div class="sv-msg" role="alert">${msg}</div>` : ''}
        ${canEdit && k ? `<div class="sv-bar"><button type="button" class="primary" data-save>Save ${k} change${k === 1 ? '' : 's'}</button><button type="button" data-discard>Discard</button></div>` : ''}
      </div>`;
      el.querySelector('[data-close]').onclick = () => { if (changes() && !confirm('Leave without saving your ' + changes() + ' change(s)?')) return; o.onClose && o.onClose(); };
      el.querySelectorAll('.sv-row').forEach(r => {
        const i = +r.dataset.i, c = list[i], b = s => r.querySelector(s);
        if (b('[data-edit]')) b('[data-edit]').onclick = () => { editing = i; msg = ''; saved = ''; render(); const f = el.querySelector('.sv-editing .sv-in'); f && f.focus(); };
        if (b('[data-remove]')) b('[data-remove]').onclick = () => { if (c.state === 'new') list.splice(i, 1); else c.state = 'removed'; saved = ''; render(); };
        if (b('[data-restore]')) b('[data-restore]').onclick = () => { c.state = before.get(c.cid) === FIELDS.map(f => c[f]).join('\u0001') ? 'same' : 'changed'; render(); };
        if (b('[data-done]')) b('[data-done]').onclick = () => {
          r.querySelectorAll('[data-f]').forEach(x => { c[x.dataset.f] = x.value.trim(); });
          if (c.state !== 'new') c.state = before.get(c.cid) === FIELDS.map(f => c[f]).join('\u0001') ? 'same' : 'changed';
          editing = -1; render(); };
        if (b('[data-undoedit]')) b('[data-undoedit]').onclick = () => { if (c.state === 'new' && !FIELDS.some(f => c[f])) list.splice(i, 1); editing = -1; render(); };
        r.querySelectorAll('.sv-in').forEach(x => x.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); b('[data-done]').click(); } });
      });
      const add = el.querySelector('[data-add]');
      if (add) add.onclick = () => { list.push({ cid: 'n' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), arabizi: '', arabic: '', english: '', plural: '', notes: '', state: 'new' });
                                     editing = list.length - 1; saved = ''; render(); const f = el.querySelector('.sv-editing .sv-in'); f && f.focus(); };
      const sv = el.querySelector('[data-save]'); if (sv) sv.onclick = save;
      const ds = el.querySelector('[data-discard]'); if (ds) ds.onclick = () => { if (!confirm('Discard your ' + changes() + ' change(s)?')) return; open(el, o); };
    }
    function save() {
      if (editing >= 0) { const d = el.querySelector('[data-done]'); if (d) d.click(); }
      const keep = list.filter(c => c.state !== 'removed');
      // the same upfront check as her upload screen: no blank side, no mixed-up sides (Medi 2026-10-28)
      const bad = H.checkCards(keep).filter(p => !p.soft);
      if (bad.length) {
        const pos = p => list.indexOf(keep[p.i]) + 1;
        msg = `<b>Not saved: ${bad.length} card${bad.length === 1 ? '' : 's'} would show wrong.</b><ul>${bad.slice(0, 8).map(p => `<li>Card ${pos(p)}: ${esc(p.why.join('; '))}</li>`).join('')}</ul>Fix ${bad.length === 1 ? 'it' : 'them'} with ✎, or remove ${bad.length === 1 ? 'it' : 'them'} with ✕.`;
        render(); return;
      }
      if (!keep.length) { msg = '<b>Not saved:</b> a set needs at least one card. To take the whole set away, use Undo on her upload list.'; render(); return; }
      const rows = keep.map(c => ({ cid: c.cid, arabizi: c.arabizi, arabic: c.arabic, english: c.english, plural: c.plural, notes: c.notes }));
      const body = { id: uuid(), kind: 'edit', undoes: o.edit.uploadId, title: String(o.title || '').slice(0, 200), rows, n: rows.length,
                     by_who: o.edit.by || null, token: o.edit.token || null, created_at: new Date().toISOString() };
      queue(body);
      const k = changes();
      list = rows.map(c => Object.assign({}, c, { state: 'same' })); before.clear(); list.forEach(c => before.set(c.cid, FIELDS.map(f => c[f]).join('\u0001')));
      msg = ''; saved = `Saved ${k} change${k === 1 ? '' : 's'}.`;
      o.onSaved && o.onSaved(body);
      render();
    }
    if (!document.getElementById('sv-css')) {
      const s = document.createElement('style'); s.id = 'sv-css';
      s.textContent = `.sv{padding-bottom:84px}
.sv>[data-close]{min-height:44px;padding:4px 0;border:none;background:none;font-weight:700;color:var(--mute,var(--ab-muted,#777));width:auto}
.sv-note{margin:10px 0 14px;padding:12px 14px;border-radius:12px;border:2px solid var(--learn,#C0702A);background:var(--learnbg,rgba(192,112,42,.12));font-weight:600;line-height:1.45}
.sv-ok{color:var(--know,#1E7B4A);font-weight:700}
.sv-head{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0 6px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mute,var(--ab-muted,#777))}
.sv-head.sv-3{grid-template-columns:1fr 1fr 44px}
.sv-grid{display:flex;flex-direction:column;gap:8px}
.sv-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:stretch}
.sv-can .sv-row{grid-template-columns:1fr 1fr 44px}
.sv-face{border:1px solid var(--line,var(--ab-line,#ccc));border-radius:12px;padding:10px 12px;min-height:60px;background:var(--bg2,var(--ab-card,transparent));overflow-wrap:anywhere;display:flex;flex-direction:column;justify-content:center;gap:4px;font-size:16px;line-height:1.3}
.sv-face b{font-weight:600;font-size:17px}.sv-face i{color:var(--red,#B3261E);font-style:normal;font-weight:700}
.sv-ar{font:600 19px/1.5 "Noto Naskh Arabic",serif;text-align:right}
.sv-n{font-size:11px;color:var(--mute,var(--ab-muted,#777));font-weight:700}
.sv-gone .sv-face{opacity:.4;text-decoration:line-through}
.sv-act{display:flex;flex-direction:column;gap:6px}.sv-act button{width:44px;height:44px;min-height:44px;padding:0;border-radius:10px;font-size:18px}
.sv-editing{grid-template-columns:1fr!important;border:2px solid var(--know,#1E7B4A);border-radius:12px;padding:10px 12px}
.sv-lab{display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:700;color:var(--mute,var(--ab-muted,#777))}
.sv-in{font:500 17px inherit;padding:10px 12px;border-radius:10px;border:1px solid var(--line,var(--ab-line,#ccc));background:var(--bg,var(--ab-bg,#fff));color:inherit;min-height:44px}
.sv-in[dir=rtl]{font-family:"Noto Naskh Arabic",serif;font-size:19px}
.sv-btns{display:flex;gap:8px}.sv-btns button{flex:1;min-height:44px}
.sv-add{width:100%;min-height:48px;margin-top:10px;border-style:dashed}
.sv-msg{margin-top:12px;padding:10px 14px;border-radius:12px;border:2px solid var(--red,#B3261E);line-height:1.45}.sv-msg ul{margin:6px 0;padding-left:20px}
.sv-bar{position:sticky;bottom:72px;display:flex;gap:8px;margin-top:14px;padding:10px;border-radius:14px;background:var(--bg2,var(--ab-card,#fff));box-shadow:0 4px 18px rgba(0,0,0,.18)}.sv-bar button{flex:1;min-height:48px;font-weight:700}`;
      document.head.appendChild(s);
    }
    window.scrollTo && window.scrollTo(0, 0);
    render(); flush();
  }
  root.AneesSetView = { open, flush };
})(typeof window !== 'undefined' ? window : globalThis);
