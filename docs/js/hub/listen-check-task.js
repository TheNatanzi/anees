/* "Which one did you say?" - Amal's listening check (Medi 2026-10-04: "make it for amal"). 40 of her OWN lines from two
   lessons, each written two ways by two listening engines (data/amal-listen.json, built by scripts/build_amal_listen.py;
   the page never says which engine wrote which). She plays her clip and taps the version that is right, or "Both wrong"
   (a box opens for what she really said), or "Same / can't tell".
   Her tap is saved the way her other pages save: a row in amal_rules with her link's token - source 'listen-check',
   kind 'listen_pick', word_key 'listen:<date>:<line>', payload {choice: a | b | both_wrong | same, typed, text} - queued
   in localStorage first, so nothing is lost offline. A tap can be changed (tap another button: the latest row wins) or
   taken back with the shared Undo (AM-17: a new row of kind 'undo', never a delete).
   scripts/amal_listen_results.py reads the answers against the key. Nothing here sends anything to anyone.
   AneesListenTask.mount(el, {token, base}, {onChange}) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const secs = m => { const p = String(m || '').split(':').map(Number); return p.some(x => !Number.isFinite(x)) ? null : p.reduce((a, x) => a * 60 + x, 0); };
  const SOURCE = 'listen-check', KIND = 'listen_pick';
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const day = d => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || ''); return m ? MONTHS[+m[2] - 1] + ' ' + (+m[3]) : String(d || ''); };
  const key = x => 'listen:' + x.id;
  const said = (x, a) => a.choice === 'a' ? 'the first version' : a.choice === 'b' ? 'the second version'
    : a.choice === 'both_wrong' ? 'both wrong' + (a.typed ? ' — you said: ' + a.typed : '') : 'same / can’t tell';

  if (typeof document !== 'undefined' && !document.getElementById('lc-css')) {
    const css = document.createElement('style'); css.id = 'lc-css';
    css.textContent = `#anees-bank .lc-ver{font-size:21px;line-height:1.5;font-weight:500;text-align:start;unicode-bidi:plaintext;min-height:56px;display:flex;gap:10px;align-items:flex-start}
#anees-bank .lc-ver>span:first-child{flex:0 0 auto;font:600 12px/26px var(--sabz-font-sans);letter-spacing:.06em;width:26px;height:26px;margin-top:3px;border-radius:50%;border:1px solid currentColor;text-align:center;opacity:.7}
#anees-bank .lc-ver>span:last-child{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;text-align:start;unicode-bidi:plaintext}
#anees-bank .lc-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#anees-bank .lc-row .hb-ans{text-align:center;font-size:15px}
#anees-bank .hb-ans[aria-pressed="true"]{background:var(--vp-sage,#2E6A4E);color:#fff;border-color:transparent}
#anees-bank .hb-ans[disabled]{opacity:.55;cursor:default}
#anees-bank .lc-warn{color:var(--sabz-danger,#B3261E);font-weight:600}
#anees-bank .lc-typed{margin:4px 0 0}`;
    (document.head || document.documentElement).appendChild(css);
  }

  function mount(el, item, opt) {
    opt = opt || {};
    const TOKEN = item.token || '', BASE = item.base || '';
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H, ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });
    const QK = 'anees-amal-listen-q-' + TOKEN, AK = 'anees-amal-listen-a-' + TOKEN;
    let DATA = null, answers = {}, flushing = false;
    const openBox = new Set();          // cards whose "Both wrong" box is open (kept open across redraws)
    el.innerHTML = '<div class="hb-task"><p class="hb-prog" data-prog>Loading…</p><div data-root></div><p class="hb-foot" data-foot>Saved as you tap · you can change an answer · stop any time</p></div>';
    const $root = el.querySelector('[data-root]'), $prog = el.querySelector('[data-prog]');

    const items = () => (DATA && DATA.items) || [];
    const pending = k => (LS(QK) || []).some(j => j.body.word_key === k);
    const answerOf = x => { const a = answers[key(x)]; return a && AneesUndo.isAnswer(a) && a.choice ? a : null; };

    async function flush() {
      if (flushing || !TOKEN) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await api('POST', 'amal_rules', job.body, { Prefer: 'return=minimal' }); ok = r.ok || r.status === 409; } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
        const x = items().find(i => key(i) === job.body.word_key); if (x) state(x);
      }
      flushing = false;
    }
    const push = body => { const q = LS(QK) || []; q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), body }); LS(QK, q); flush(); };

    function bar(x) {
      if (!root.AneesClip) return null;
      // her own clip; if the file is missing, the same moment from the full recording (her channel first)
      const t = secs(x.mmss), dir = BASE + 'lessons/' + x.date + '/audio/';
      const chain = t != null ? ['Amal.mp3', 'lesson.mp3'].map(n => ({ src: dir + n, start: Math.max(0, t - 1), end: t + 15 })) : [];
      return AneesClip.bar({ src: BASE + 'lessons/' + x.clip, start: 0, end: null, fallback: chain });
    }
    // the part of a card that changes with her answer (the clip bar above it is never redrawn, so it keeps playing)
    function stateHtml(x) {
      const a = answerOf(x), c = a ? a.choice : '', off = TOKEN ? '' : ' disabled', box = openBox.has(x.id);
      const ver = (w, n) => `<button type="button" class="hb-ans lc-ver" data-lc="${w}" aria-pressed="${c === w}" dir="auto"${off}><span aria-hidden="true">${n}</span><span lang="ar" dir="auto">${esc(x[w])}</span></button>`;
      return `<div class="hb-btns">${ver('a', 1)}${ver('b', 2)}
        <div class="lc-row"><button type="button" class="hb-ans" data-lc="both_wrong" aria-pressed="${c === 'both_wrong'}"${off}>Both wrong</button>
        <button type="button" class="hb-ans" data-lc="same" aria-pressed="${c === 'same'}"${off}>Same / can’t tell</button></div>
        <div class="lc-typed" data-typed${box ? '' : ' hidden'}><textarea class="hb-input" dir="auto" lang="ar" placeholder="What did you say? (optional)" aria-label="What you said">${esc(box && a && a.choice === 'both_wrong' ? a.typed || '' : '')}</textarea>
        <button type="button" class="hb-ans primary" data-lc="typed-save"${off}>Save</button></div></div>
        ${a ? AneesUndo.answered((pending(key(x)) ? 'Saving… ' : 'Saved · ') + said(x, a), { 'data-lc': 'undo' }) : ''}`;
    }
    function state(x) {
      const card = $root.querySelector(`[data-id="${CSS.escape(x.id)}"]`); if (!card) return;
      const wrap = card.querySelector('[data-typed]'), box = wrap && wrap.querySelector('textarea'), keep = box && !wrap.hidden && openBox.has(x.id) ? box.value : null, had = box && document.activeElement === box;
      card.querySelector('[data-state]').innerHTML = stateHtml(x);
      if (keep != null) { const t = card.querySelector('[data-typed] textarea'); t.value = keep; if (had) t.focus(); }
      card.classList.toggle('lc-done', !!answerOf(x));
      progress();
    }
    function progress() {
      const n = items().length, done = items().filter(answerOf).length;
      $prog.textContent = n ? `${done} of ${n} answered${done === n ? ' · all done, thank you!' : ''}` : 'Nothing to check right now.';
      opt.onChange && opt.onChange({ total: n, done, finished: n > 0 && done === n });
    }
    function render() {
      $root.innerHTML = items().map((x, n) => `<article class="hb-moment hb-card" data-id="${esc(x.id)}">
        <p class="hb-prog">${n + 1} of ${items().length} · lesson ${esc(day(x.date))} · ${esc(x.mmss || '')}</p><div data-bar></div><div data-state></div></article>`).join('')
        || '<p class="hb-empty">Nothing to check right now.</p>';
      items().forEach(x => {
        const card = $root.querySelector(`[data-id="${CSS.escape(x.id)}"]`), b = bar(x);
        if (b) card.querySelector('[data-bar]').appendChild(b);
        state(x);
      });
      progress();
    }
    function decide(x, choice, typed) {
      const k = key(x), text = choice === 'a' ? x.a : choice === 'b' ? x.b : null;
      // a newer tap replaces one that was not sent yet; a sent one is simply followed by this row (the latest wins)
      LS(QK, AneesUndo.unqueue(LS(QK) || [], j => j.body.word_key === k && j.body.kind !== 'undo'));
      answers[k] = { kind: KIND, choice, typed: typed || null, at: new Date().toISOString() }; LS(AK, answers);
      push({ token: TOKEN, source: SOURCE, lesson_date: null, kind: KIND, word_key: k,
             payload: { choice, typed: typed || null, text, label: x.date + ' ' + (x.mmss || ''), set: DATA.set || null } });
      state(x);
    }
    function undo(x) {   // AM-17: a new 'undo' row; a tap not sent yet leaves the queue
      const k = key(x), was = answerOf(x); if (!was) return;
      LS(QK, AneesUndo.unqueue(LS(QK) || [], j => j.body.word_key === k && j.body.kind !== 'undo'));
      answers[k] = { kind: 'undo', at: new Date().toISOString() }; LS(AK, answers);
      push(AneesUndo.row({ token: TOKEN, source: SOURCE, lesson_date: null, kind: KIND, word_key: k, payload: { label: x.date + ' ' + (x.mmss || '') } }));
      openBox.delete(x.id); state(x);
    }
    el.addEventListener('click', e => {
      const b = e.target.closest('button[data-lc]'); if (!b || !TOKEN) return;
      const card = b.closest('[data-id]'), x = items().find(i => i.id === card.dataset.id), act = b.dataset.lc; if (!x) return;
      if (act === 'undo') undo(x);
      else if (act === 'a' || act === 'b' || act === 'same') { openBox.delete(x.id); decide(x, act, null); }
      else if (act === 'both_wrong') {      // saved at once; the box is for what she really said (optional)
        const a = answerOf(x); openBox.add(x.id);
        if (!a || a.choice !== 'both_wrong') decide(x, 'both_wrong', null); else state(x);
        const t = card.querySelector('[data-typed] textarea'); if (t) t.focus();
      }
      else if (act === 'typed-save') { const v = card.querySelector('[data-typed] textarea').value.trim(); openBox.delete(x.id); decide(x, 'both_wrong', v || null); }
    });

    (async () => {
      try { DATA = await (await fetch(BASE + 'data/amal-listen.json', { cache: 'no-store' })).json(); }
      catch (e) { $prog.textContent = 'The list could not load. Refresh to try again.'; return; }
      answers = LS(AK) || {};
      if (!TOKEN) $prog.insertAdjacentHTML('afterend', '<p class="hb-sub lc-warn">This page was opened without the private link the student sent, so answers cannot be saved. You can still listen.</p>');
      else {
        try {   // once this browser's taps are sent, the live answers win (latest row per line; an undo = open again)
          const saved = await (await api('GET', 'amal_rules?select=kind,word_key,payload,created_at&source=eq.' + SOURCE + '&order=created_at.asc&token=eq.' + encodeURIComponent(TOKEN))).json();
          if (!Array.isArray(saved)) throw new Error('read');
          const server = {};
          saved.forEach(r => { const p = r.payload || {}; server[r.word_key] = { kind: r.kind, choice: p.choice || null, typed: p.typed || null, at: r.created_at }; });
          answers = AneesUndo.reconcile(answers, server, (LS(QK) || []).map(j => j.body.word_key), true); LS(AK, answers);
        } catch (e) {}
      }
      render(); flush();
      setInterval(() => { if ((LS(QK) || []).length) flush(); }, 3000);
    })();
  }
  root.AneesListenTask = { mount, SOURCE, KIND };
})(typeof window !== 'undefined' ? window : globalThis);
