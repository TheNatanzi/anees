/* Tutor hub · "Which word was wrong?" (LS-12, Medi 2026-10-02: "1-6 put for amal on her list").
   Moments where two of Anees' judges disagree about one of Medi's Arabic words. Amal decides: one tap per moment, the
   same pattern as "Check these moments" - the moment with both voices, Medi's line, her own next line, the question and
   the choices in plain words, Undo next to her answer (docs/js/amal-undo.js, AM-17).
   Her tap = an amal_rules row (source 'review', the open review link's token, word_key 'ledger:<question id>', kind
   'ledger_pick', payload.answer); scripts/apply_amal_audit_rulings.py reads it every hour into
   data/lesson-work/ledger-amal.json and the lesson ledger counts her answer (scripts/lesson_ledger.py). Until she answers,
   the moment is counted as it is today. Taps are queued in this browser first, so nothing is lost offline.
   AneesLedgerTask.mount(el, {token, data, answers, live}, {onChange}); AneesLedgerTask.count(data, answers). */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const all = D => { const seen = new Set(); return ((D && D.items) || []).concat((D && D.answered) || []).filter(x => !seen.has(x.id) && seen.add(x.id)); };
  const answerOf = (x, answers) => { const a = answers[x.id]; if (a) return root.AneesUndo.isAnswer(a) ? a : null; return x.answered || null; };
  function count(D, answers) {
    const items = all(D), done = items.filter(x => answerOf(x, answers || {})).length;
    return { total: items.length, done, left: items.length - done };
  }
  const pretty = d => new Date(String(d) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const labelOf = (x, v) => ((x.options || []).find(o => o.value === v) || {}).label || v;

  function mount(el, ctx, opt) {
    const D = ctx.data || { items: [] }, TOKEN = ctx.token || '';
    const QK = 'anees-tutor-ledger-q-' + TOKEN, AK = 'anees-tutor-ledger-a-' + TOKEN;
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const pendingKeys = () => (LS(QK) || []).map(j => j.body.word_key);
    let answers = root.AneesUndo.reconcile(LS(AK) || {}, ctx.answers || {}, pendingKeys(), !!ctx.live), flushing = false;
    async function flush() {
      if (flushing || !TOKEN) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await fetch(ANEES.url + '/rest/v1/amal_rules', { method: 'POST', headers: { ...H, Prefer: 'return=minimal' }, body: JSON.stringify(job.body) }); ok = r.ok || r.status === 409; } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; render();
    }
    const push = body => { const q = LS(QK) || []; q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), body }); LS(QK, q); flush(); };
    function pick(id, value) {
      const x = all(D).find(i => i.id === id); if (!x || !TOKEN) return;
      answers[id] = { kind: 'ledger_pick', answer: value, at: new Date().toISOString() }; LS(AK, answers);
      push({ token: TOKEN, source: 'review', lesson_date: x.date, kind: 'ledger_pick', word_key: id,
             payload: { answer: value, label: labelOf(x, value), question: x.question, date: x.date, t: x.t } });
      render();
    }
    function undo(id) {
      const x = all(D).find(i => i.id === id), was = x && answerOf(x, answers); if (!was) return;
      LS(QK, root.AneesUndo.unqueue(LS(QK) || [], j => j.body.word_key === id && j.body.kind !== 'undo'));
      answers[id] = { kind: 'undo', at: new Date().toISOString() }; LS(AK, answers);
      push(root.AneesUndo.row({ token: TOKEN, source: 'review', lesson_date: x.date, kind: 'ledger_pick', word_key: id, payload: { label: x.question } }));
      render();
    }
    function card(x) {
      const a = answerOf(x, answers), saving = pendingKeys().includes(x.id) ? ' · saving…' : '';
      return `<article class="tu-card tv-card${a ? ' tv-done' : ''}" data-lq="${esc(x.id)}">
        <div class="tu-top"><h3 class="tu-title tv-title">${esc(pretty(x.date))} · ${esc(x.mmss)}</h3></div>
        <div><button type="button" class="tu-btn tv-play" data-lplay="${esc(x.audio || '')}">▶ Play the moment</button></div>
        ${x.medi_said ? `<p class="tu-meta">Medi: <span lang="ar" dir="auto" class="tv-line">${esc(x.medi_said)}</span></p>` : ''}
        ${x.amal_said ? `<p class="tu-meta">You: <span lang="ar" dir="auto" class="tv-line">${esc(x.amal_said)}</span></p>` : ''}
        <p class="hb-sub"><b dir="auto">${esc(x.question)}</b></p>
        ${a ? root.AneesUndo.answered('You said: ' + labelOf(x, a.answer) + saving, { 'data-lundo': x.id }) :
          `<div class="tv-btns">${(x.options || []).map(o => `<button type="button" class="tu-btn${o.value === 'none' ? '' : ' tu-primary'}" data-lpick="${esc(o.value)}" data-id="${esc(x.id)}" dir="auto">${esc(o.label)}</button>`).join('')}</div>`}
      </article>`;
    }
    function render() {
      const c = count(D, answers);
      el.innerHTML = `<p class="hb-prog">${c.done} of ${c.total} answered</p>${TOKEN ? '' : '<p class="hb-sub">No open review link, so answers cannot be saved right now.</p>'}` +
        all(D).map(card).join('');
      opt && opt.onChange && opt.onChange({ total: c.total, done: c.done, finished: c.total > 0 && c.left === 0 });
    }
    const player = new Audio();
    el.addEventListener('click', e => {
      const p = e.target.closest('button[data-lplay]');
      if (p) { const [src, frag] = p.dataset.lplay.split('#t='); const [s, t] = (frag || '0').split(',').map(Number);
        if (!player.src.endsWith(src)) player.src = src; player.currentTime = s || 0; player.play().catch(() => {});
        player.ontimeupdate = () => { if (t && player.currentTime >= t) player.pause(); }; return; }
      const b = e.target.closest('button[data-lpick]'); if (b) { pick(b.dataset.id, b.dataset.lpick); return; }
      const u = e.target.closest('[data-lundo]'); if (u) undo(u.dataset.lundo);
    });
    render(); flush();
    setInterval(() => { if ((LS(QK) || []).length) flush(); }, 3000);
  }
  // server rows -> {word_key: answer}; the latest row per moment wins (an undo = open again, AM-17)
  function liveView(rows) {
    const out = {};
    Object.values(root.AneesUndo.latest(rows || [])).forEach(r => { out[r.word_key] = r.kind === 'undo' ? { kind: 'undo' } : { kind: r.kind, answer: (r.payload || {}).answer, at: r.created_at }; });
    return out;
  }
  root.AneesLedgerTask = { mount, count, liveView };
})(typeof self !== 'undefined' ? self : this);
