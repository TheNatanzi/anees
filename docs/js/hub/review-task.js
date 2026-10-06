/* "Slips to review" - slips the app thinks Amal let pass, one card per pattern (data/amal-review.json, built by
   scripts/build_amal_review.py), plus the old "new word, not on the sheet" cards. ONE module for the Tutor hub panel and
   the old address amal/review.html. Her tap: amal_rules source 'review', word_key = the pattern id, kind audit_confirm
   ("Correction is correct") / audit_skip ("Reason not to correct" + her reason) or sheet_add / sheet_skip; queued in
   localStorage first; scripts/apply_amal_audit_rulings.py applies them.
   AM-17 (Medi 2026-10-02 "can you add an undo button to all these tutor hub stuff"): every answered card shows her answer
   with the shared Undo - a new amal_rules row of kind 'undo', never a delete - and the card is open again at once.
   Patterns she ruled before the last build stay listed (amal-review.json 'answered'), so an Undo can always reach them.
   AneesReviewTask.mount(el, {token, base}, {onChange}) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const secs = m => { const p = String(m || '').split(':').map(Number); return p.some(x => !Number.isFinite(x)) ? null : p.reduce((a, x) => a * 60 + x, 0); };
  const OWN = k => !/^(verify|newword):/.test(String(k || ''));   // the other hub lists share this token

  function mount(el, item, opt) {
    opt = opt || {};
    const TOKEN = item.token, BASE = item.base || '';
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H, ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });
    const QK = 'anees-amal-review-q-' + TOKEN, AK = 'anees-amal-review-a-' + TOKEN;
    let DATA = null, answers = {}, filter = 'all', flushing = false, shown = 20;
    el.innerHTML = '<div class="hb-task"><p class="hb-sub">One card per pattern of slip. Play a moment if you like, then tap: <b>Yes, Medi was wrong</b> counts it against him; <b>No, Medi was fine</b> (say why in a line) drops it and the app never asks about this pattern again.</p><div class="hb-chips" data-filters></div><p class="hb-prog" data-prog>Loading…</p><div data-root></div><p class="hb-foot" data-foot>Saved as you tap · stop any time</p></div>';
    const $root = el.querySelector('[data-root]'), $prog = el.querySelector('[data-prog]'), $filters = el.querySelector('[data-filters]');

    async function flush() {
      if (flushing || !TOKEN) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await api('POST', 'amal_rules', job.body, { Prefer: 'return=minimal' }); ok = r.ok || r.status === 409; } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; render();
    }
    const push = body => { const q = LS(QK) || []; q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), body }); LS(QK, q); flush(); };
    const pending = id => (LS(QK) || []).some(j => j.body.word_key === id);
    const patterns = () => (DATA.all || []);
    // her answer: live/queued tap first (an undo = open), else what the last build read
    const answerOf = p => { const a = answers[p.id]; if (a) return AneesUndo.isAnswer(a) ? a : null; return p.answered || null; };

    function bar(x) {
      if (!root.AneesClip) return null;
      // the short clip is often missing on the site (2026-09-28): fall back to the moment in the full recording, then each
      // channel of a two-channel lesson (lesson.mp3 -> Medi.mp3 -> Amal.mp3, same chain as js/clip-fallback.js)
      const t = secs(x.mmss), dir = ANEES.pages + 'lessons/' + x.date + '/audio/';
      const chain = t != null ? ['lesson.mp3', 'Medi.mp3', 'Amal.mp3'].map(n => ({ src: dir + n, start: Math.max(0, t - 3), end: t + 12 })) : [];
      return AneesClip.bar({ src: x.clip ? ANEES.pages + 'lessons/' + x.clip : (chain[0] || {}).src, start: x.clip ? 0 : Math.max(0, (t || 0) - 3), end: x.clip ? null : (t || 0) + 12,
                             fallback: x.clip ? chain : chain.slice(1) });
    }
    const pair = p => `<div class="hb-moment"><div class="tv-pair"><span class="tv-ar tv-wrong" lang="ar">${esc(p.wrong_arabic || p.wrong)}</span><span class="tv-arrow">→</span><span class="tv-ar tv-right" lang="ar">${esc(p.right_arabic || p.right)}</span></div>
      ${p.wrong_arabizi || p.right_arabizi ? `<div class="hb-en">${esc(p.wrong_arabizi || '')} → ${esc(p.right_arabizi || '')}</div>` : ''}</div>`;
    const example = (x, i) => `<div class="hb-ex" data-ex="${i}"><p class="hb-sub" style="margin:6px 0 2px">${esc(x.date)} · ${esc(x.mmss || '')}</p>
      <div>Medi: <span lang="ar">${esc(x.medi_said)}</span></div>${x.amal_said ? `<div>You: <span lang="ar">${esc(x.amal_said)}</span></div>` : ''}${x.chat ? `<div class="hb-sub">Your chat: ${esc(x.chat)}</div>` : ''}${x.english ? `<div class="hb-sub">${esc(x.english)}</div>` : ''}<div data-bar></div></div>`;
    function card(p) {
      const a = answerOf(p), n = (p.examples || []).length, wait = pending(p.id) ? ' · saving…' : '';
      return `<article class="hb-moment hb-card" data-pid="${esc(p.id)}"><p class="hb-prog">${esc(p.kind_label || '')}${p.bucket ? ` · rule ${esc(p.bucket)} ${esc(p.bucket_name || '')}` : ''}</p>
        ${pair(p)}<p class="hb-why">${esc(p.why || '')}</p>${p.english ? `<p class="hb-sub">e.g. “${esc(p.english)}”</p>` : ''}<p class="hb-sub">${n} time${n === 1 ? '' : 's'} in ${esc(p.lessons_label || '')}</p>
        ${a ? AneesUndo.answered((a.kind === 'audit_confirm' ? `You said: the correction is correct · result: ${n} slip${n === 1 ? '' : 's'} counted for Medi` : 'You said: no correction — ' + (a.reason || '') + ' · result: dropped, never asked again') + wait, { 'data-rv': 'undo', 'data-id': p.id })
            : `<div class="hb-btns"><button type="button" class="hb-ans primary" data-rv="confirm" data-id="${esc(p.id)}">Yes, Medi was wrong<small>counts as a mistake for Medi</small></button>
          <button type="button" class="hb-ans" data-rv="skip" data-id="${esc(p.id)}">No, Medi was fine<small>say why in a line · the app stops asking about this</small></button>
          <div data-reason hidden><textarea class="hb-input" placeholder="e.g. both are fine in Palestinian; or: this is what I say too" aria-label="Your reason"></textarea><button type="button" class="hb-ans primary" data-rv="skip-save" data-id="${esc(p.id)}">Save reason</button></div></div>`}
        ${n ? `<details data-exs><summary>Show ${n} example${n === 1 ? '' : 's'}</summary>${(p.examples || []).map(example).join('')}</details>` : ''}</article>`;
    }
    function wcard(w) {
      const a = answerOf(w), n = (w.moments || []).length;
      return `<article class="hb-moment hb-card" data-pid="${esc(w.id)}"><p class="hb-prog">New word · not on the sheet yet</p>
        <div class="hb-big" lang="ar">${esc(w.arabic)}</div>${w.arabizi ? `<div class="hb-en">${esc(w.arabizi)}</div>` : ''}${w.english ? `<div class="hb-en">${esc(w.english)}</div>` : ''}<p class="hb-sub">Came up ${n} time${n === 1 ? '' : 's'} in our lessons</p>
        ${a ? AneesUndo.answered(a.kind === 'sheet_add' ? 'You said: add it to the sheet · result: waiting for the sheet' : 'You said: not needed · result: stays off the sheet', { 'data-rv': 'undo', 'data-id': w.id })
            : `<div class="hb-btns"><button type="button" class="hb-ans primary" data-rv="sheet_add" data-id="${esc(w.id)}">Add it to my Doc<small>Medi learns it as one of your words</small></button>
          <button type="button" class="hb-ans" data-rv="sheet_skip" data-id="${esc(w.id)}">Not needed<small>it stays off the Doc</small></button></div>`}</article>`;
    }
    function render() {
      if (!DATA) return;
      const W = DATA.new_words || [], P = patterns();
      const list = filter === 'new' ? W : P.filter(p => filter === 'all' || p.kind === filter);
      const done = P.filter(answerOf).length;
      $prog.textContent = filter === 'new' ? `${W.filter(answerOf).length} of ${W.length} new words decided` : `${done} of ${P.length} patterns decided`;
      // open cards first, then the answered ones (each with Undo); long lists 20 at a time
      const open = list.filter(x => !answerOf(x)), ans = list.filter(answerOf), ord = open.concat(ans), page = ord.slice(0, shown);
      $root.innerHTML = (page.map(filter === 'new' ? wcard : card).join('') || '<p class="hb-empty">Nothing to review.</p>')
        + (ord.length > shown ? `<button type="button" class="hb-ans" data-more>Show the next ${Math.min(20, ord.length - shown)} (${ord.length - shown} more)</button>` : '');
      $root.querySelectorAll('details[data-exs]').forEach(d => d.addEventListener('toggle', () => {
        if (!d.open || d.dataset.wired) return; d.dataset.wired = '1';
        const p = P.find(x => x.id === d.closest('[data-pid]').dataset.pid);
        d.querySelectorAll('[data-ex]').forEach(box => { const b = bar((p.examples || [])[+box.dataset.ex] || {}); if (b) box.querySelector('[data-bar]').appendChild(b); });
      }));
      const more = $root.querySelector('[data-more]'); if (more) more.onclick = () => { shown += 20; render(); };
      opt.onChange && opt.onChange({ total: P.length, done, finished: P.length > 0 && done === P.length });
    }
    function decide(id, kind, reason) {
      const p = patterns().find(x => x.id === id); if (!p) return;
      answers[id] = { kind, reason, at: new Date().toISOString() }; LS(AK, answers);
      push({ token: TOKEN, source: 'review', lesson_date: null, kind, word_key: id, payload: { label: p.title, pattern: p.title, reason: reason || null, n: (p.examples || []).length, rows: (p.examples || []).map(x => x.uid), audit: DATA.built } });
      render();
    }
    function sheet(id, kind) {
      const w = (DATA.new_words || []).find(x => x.id === id); if (!w) return;
      answers[id] = { kind, at: new Date().toISOString() }; LS(AK, answers);
      push({ token: TOKEN, source: 'review', lesson_date: null, kind, word_key: id, payload: { label: w.arabic, arabic: w.arabic, arabizi: w.arabizi || null, english: w.english || null, moments: (w.moments || []).map(m => m.date + ' ' + (m.mmss || '')), audit: DATA.built } });
      render();
    }
    function undo(id) {   // AM-17: a new 'undo' row; a tap not sent yet leaves the queue
      const x = patterns().concat(DATA.new_words || []).find(i => i.id === id), was = x && answerOf(x); if (!was) return;
      LS(QK, AneesUndo.unqueue(LS(QK) || [], j => j.body.word_key === id && j.body.kind !== 'undo'));
      answers[id] = { kind: 'undo', at: new Date().toISOString() }; LS(AK, answers);
      push(AneesUndo.row({ token: TOKEN, source: 'review', lesson_date: null, kind: was.kind, word_key: id, payload: { label: x.title || x.arabic } }));
      render();
    }
    el.addEventListener('click', e => {
      const b = e.target.closest('button[data-rv]'); if (!b) return; const id = b.dataset.id, act = b.dataset.rv;
      const box = b.closest('[data-pid]');
      if (act === 'undo') undo(id);
      else if (act === 'confirm') decide(id, 'audit_confirm', null);
      else if (act === 'sheet_add' || act === 'sheet_skip') sheet(id, act);
      else if (act === 'skip') { const r = box.querySelector('[data-reason]'); r.hidden = false; r.querySelector('textarea').focus(); }
      else if (act === 'skip-save') { const t = box.querySelector('textarea'), v = t.value.trim(); if (!v) { t.focus(); return; } decide(id, 'audit_skip', v); }
    });
    $filters.addEventListener('click', e => { const b = e.target.closest('button[data-f]'); if (!b) return; filter = b.dataset.f; shown = 20; drawFilters(); render(); });
    function drawFilters() {
      const P = patterns(), kinds = [['all', 'All', P.length], ['vocab', 'Words', P.filter(p => p.kind === 'vocab').length], ['grammar', 'Grammar', P.filter(p => p.kind === 'grammar').length], ['new', 'New words (not on sheet)', (DATA.new_words || []).length]];
      $filters.innerHTML = kinds.filter(k => k[2] || k[0] === 'all').map(([k, l, n]) => `<button type="button" class="hb-chip" data-f="${k}" aria-pressed="${k === filter}">${esc(l)} (${n})</button>`).join('');
    }
    (async () => {
      if (!TOKEN) { $prog.textContent = 'No open review link, so answers cannot be saved right now.'; }
      try { DATA = await (await fetch(BASE + 'data/amal-review.json', { cache: 'no-store' })).json(); }
      catch (e) { $prog.textContent = 'The review list could not load. Refresh to try again.'; return; }
      { const seen = new Set(); DATA.all = (DATA.patterns || []).concat(DATA.answered || []).filter(x => !seen.has(x.id) && seen.add(x.id)); }
      answers = LS(AK) || {};
      if (TOKEN) {
        try {   // AM-17: once this browser's taps are sent, the live answers win (latest row per card; an undo = open)
          const saved = await (await api('GET', 'amal_rules?select=kind,word_key,payload,created_at&source=eq.review&order=created_at.asc&token=eq.' + encodeURIComponent(TOKEN))).json();
          if (!Array.isArray(saved)) throw new Error('read');
          const server = {};
          saved.filter(r => OWN(r.word_key)).forEach(r => { server[r.word_key] = { kind: r.kind, reason: (r.payload || {}).reason || null, at: r.created_at }; });
          answers = AneesUndo.reconcile(answers, server, (LS(QK) || []).map(j => j.body.word_key), true); LS(AK, answers);
        } catch (e) {}
        try { const l = await (await api('GET', 'amal_links?select=opened_at&token=eq.' + encodeURIComponent(TOKEN))).json(); if (l[0] && !l[0].opened_at) api('PATCH', 'amal_links?token=eq.' + encodeURIComponent(TOKEN), { opened_at: new Date().toISOString() }, { Prefer: 'return=minimal' }); } catch (e) {}
      }
      el.querySelector('[data-foot]').textContent = `${DATA.note || ''} · Built ${String(DATA.built || '').slice(0, 10)} from ${DATA.lessons || ''} lessons · saved as you tap`;
      drawFilters(); render(); flush();
      setInterval(() => { if ((LS(QK) || []).length) flush(); }, 3000);
    })();
  }
  root.AneesReviewTask = { mount };
})(typeof window !== 'undefined' ? window : globalThis);
