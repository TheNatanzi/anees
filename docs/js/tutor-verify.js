/* Tutor page · "Check these moments" (Medi's decision 5, 2026-09-29).
   Rows two AIs disagree on: the Claude readers say Medi made a mistake Amal signalled; Codex, reading an independent
   transcription of the audio, says no or cannot tell. Amal settles each one with the same buttons as her review page:
   "Correction is correct" (it becomes a scored mistake) or "Reason not to correct" + a box (it is dropped, her reason kept).
   Her taps go to Supabase amal_rules (source 'review', kind audit_confirm / audit_skip, word_key 'verify:<uid>') with the
   open review link's token from data/tutor.json; scripts/apply_amal_audit_rulings.py turns them into ledger records
   (data/accuracy/verifications.json, reviewer Amal) every hour. Taps are queued in localStorage first, so nothing is lost
   offline. Nothing here sends anything to anyone.
   AM-17 (Medi 2026-10-02 "can you add an undo button to all these tutor hub stuff"): every answered moment shows her
   answer with the shared Undo (docs/js/amal-undo.js) - a new amal_rules row of kind 'undo', never a delete - and the
   card is open again at once. Moments she answered before the last build stay listed (data/amal-verify.json 'answered'). */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const sec = s => { const p = String(s || '').split(':').map(Number); return p.some(x => !Number.isFinite(x)) ? null : p.reduce((a, x) => a * 60 + x, 0); };
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  let TOKEN = '', DATA = null, answers = {};
  const QK = () => 'anees-tutor-verify-q-' + TOKEN, AK = () => 'anees-tutor-verify-a-' + TOKEN;
  const H = () => ({ apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN });
  const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H(), ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });

  let flushing = false;
  async function flush() {
    if (flushing || !TOKEN) return; flushing = true;
    while (true) {
      const q = LS(QK()) || []; if (!q.length) break; const job = q[0]; let ok = false;
      try { const r = await api('POST', 'amal_rules', job.body, { Prefer: 'return=minimal' }); ok = r.ok || r.status === 409; } catch (e) { ok = false; }
      if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
      LS(QK(), (LS(QK()) || []).filter(x => x.id !== job.id));
    }
    flushing = false; render();
  }
  function push(body) { const q = LS(QK()) || []; q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), body }); LS(QK(), q); flush(); }

  const answerOf = x => { const a = answers[x.id]; if (a) return AneesUndo.isAnswer(a) ? a : null; return x.answered ? { kind: x.answered.kind, reason: x.answered.reason } : null; };
  function card(x) {
    const a = answerOf(x), pending = (LS(QK()) || []).some(j => j.body.word_key === x.id);
    const what = x.kind === 'grammar' ? `Grammar${x.bucket ? ' · rule ' + esc(x.bucket) : ''}` : `Word${x.tier === 0 ? ' he did not know' : ''}`;
    const play = x.audio ? `<button class="tu-btn tv-play" data-src="${esc(x.audio)}">▶ Play the moment</button>` : '<span class="tu-meta">No recording on the site for this lesson.</span>';
    return `<article class="tu-card tv-card${a ? ' tv-done' : ''}" id="tv-${esc(x.id)}">
      <div class="tu-top"><h3 class="tu-title tv-title">${esc(x.date)} · ${esc(x.t || x.t_amal || '')}</h3><span class="tu-who">${what}</span></div>
      <div class="tv-pair"><span class="tv-ar tv-wrong" lang="ar">${esc(x.wrong)}</span><span class="tv-arrow">→</span><span class="tv-ar tv-right" lang="ar">${esc(x.right)}</span></div>
      <p class="tu-meta">Student: <span lang="ar" class="tv-line">${esc(x.medi_said)}</span></p>
      ${x.amal_said ? `<p class="tu-meta">Tutor: <span lang="ar" class="tv-line">${esc(x.amal_said)}</span></p>` : ''}
      ${x.chat ? `<p class="tu-meta">The tutor typed: <span lang="ar" class="tv-line">${esc(x.chat)}</span></p>` : ''}
      <p class="tu-meta"><b>Reader AI says:</b> ${esc(x.readers_say)}</p>
      <p class="tu-meta"><b>Listening AI says:</b> ${esc(x.codex_says)}</p>
      <div>${play}</div>
      ${a ? AneesUndo.answered(`${a.kind === 'audit_confirm' ? 'The tutor said: the correction is correct · result: counted as a mistake for the student' : 'The tutor said: no correction — ' + (a.reason || '') + ' · result: dropped'}${pending ? ' · saving…' : ''}`, { 'data-tv': 'undo', 'data-id': x.id }) : ''}
      <div class="tv-btns"><button class="tu-btn tu-primary" data-tv="confirm" data-id="${esc(x.id)}">Yes, the student was wrong<small>counts as a mistake for the student</small></button>
      <button class="tu-btn" data-tv="skip" data-id="${esc(x.id)}">No, the student was fine<small>say why in a line · it is dropped</small></button>
      <div class="tv-reason" id="tvr-${esc(x.id)}" hidden><textarea id="tvx-${esc(x.id)}" placeholder="e.g. he said it right; or: I was not correcting him here"></textarea>
      <button class="tu-btn tu-primary" data-tv="skip-save" data-id="${esc(x.id)}">Save reason</button></div></div></article>`;
  }

  function render() {
    if (!DATA) return;
    const items = DATA.all || DATA.items || [];
    const done = items.filter(answerOf).length;
    $('#tv-count').textContent = items.length ? `${done} of ${items.length} answered` : 'Nothing to check right now.';
    $('#tv-list').innerHTML = items.map(card).join('');
  }

  function decide(id, kind, reason) {
    const x = (DATA.all || DATA.items || []).find(i => i.id === id); if (!x) return;
    answers[id] = { kind, reason, at: new Date().toISOString() }; LS(AK(), answers);
    push({ token: TOKEN, source: 'review', lesson_date: null, kind, word_key: id,
           payload: { label: `${x.wrong} → ${x.right}`, verify: true, uid: x.uid, date: x.date, t: x.t, reason: reason || null,
                      rows: [x.uid], codex_verdict: x.codex_verdict, list_built: DATA.built } });
    render();
  }
  function undo(id) {   // AM-17: a new 'undo' row; a tap not sent yet leaves the queue
    const x = (DATA.all || DATA.items || []).find(i => i.id === id), was = x && answerOf(x); if (!was) return;
    LS(QK(), AneesUndo.unqueue(LS(QK()) || [], j => j.body.word_key === id && j.body.kind !== 'undo'));
    answers[id] = { kind: 'undo', at: new Date().toISOString() }; LS(AK(), answers);
    push(AneesUndo.row({ token: TOKEN, source: 'review', lesson_date: null, kind: was.kind, word_key: id, payload: { label: `${x.wrong} → ${x.right}` } }));
    render();
  }

  const player = new Audio();
  document.addEventListener('click', e => {
    const p = e.target.closest('button.tv-play');
    if (p) { const [src, frag] = p.dataset.src.split('#t='); const [a, b] = (frag || '0').split(',').map(Number);
      if (!player.src.endsWith(src)) player.src = src; player.dataset.clipStart = a || 0; if (b) player.dataset.clipEnd = b; else delete player.dataset.clipEnd; player.currentTime = a || 0; player.play().catch(() => {});
      player.ontimeupdate = () => { if (b && player.currentTime >= b) player.pause(); };
      player.onerror = () => { p.textContent = '✕ No recording for this moment'; }; return; }
    const b = e.target.closest('button[data-tv]'); if (!b) return; const id = b.dataset.id;
    if (b.dataset.tv === 'undo') undo(id);
    else if (b.dataset.tv === 'confirm') decide(id, 'audit_confirm', null);
    else if (b.dataset.tv === 'skip') { const r = document.getElementById('tvr-' + id); r.hidden = false; document.getElementById('tvx-' + id).focus(); }
    else if (b.dataset.tv === 'skip-save') { const t = document.getElementById('tvx-' + id), v = t.value.trim(); if (!v) { t.focus(); return; } decide(id, 'audit_skip', v); }
  });

  async function main() {
    try { DATA = await (await fetch('data/amal-verify.json', { cache: 'no-store' })).json(); } catch (e) { $('#tv-count').textContent = 'The list could not load. Refresh to retry.'; return; }
    let T = { open: [] };
    try { T = await (await fetch('data/tutor.json', { cache: 'no-store' })).json(); } catch (e) {}
    const rv = (T.open || []).find(x => x.kind === 'review');
    TOKEN = rv ? rv.token : '';
    if (!TOKEN) { $('#tv-count').textContent = 'No open review link, so answers cannot be saved right now.'; }
    { const seen = new Set(); DATA.all = (DATA.items || []).concat(DATA.answered || []).filter(x => !seen.has(x.id) && seen.add(x.id)); }
    answers = LS(AK()) || {};
    if (TOKEN) {
      try {   // AM-17: live answers win once this browser's copy is sent (latest row per moment; an undo = open)
        const saved = await (await api('GET', 'amal_rules?select=kind,word_key,payload,created_at&source=eq.review&word_key=like.verify:*&order=created_at.asc&token=eq.' + encodeURIComponent(TOKEN))).json();
        if (!Array.isArray(saved)) throw new Error('read');
        const server = {};
        saved.forEach(r => { server[r.word_key] = { kind: r.kind, reason: (r.payload || {}).reason || null, at: r.created_at }; });
        answers = AneesUndo.reconcile(answers, server, (LS(QK()) || []).map(j => j.body.word_key), true);
        LS(AK(), answers);
      } catch (e) {}
    }
    render(); flush();
    setInterval(() => { if ((LS(QK()) || []).length) flush(); }, 3000);
    window.addEventListener('online', flush);
  }
  main();
})();
