/* Amal's listening / checking lists (Medi 2026-10-05: "have amal do the 27 line check too", "did you put the 108 on amals
   list", "5 send to amal"). ONE module for every list in data/amal-checks.json (built by scripts/build_amal_checks.py):
   each list is its own data file data/amal-check-<list>.json = {kind, prefix, questions, items}. A card: the lesson and
   time, a plain note, one or two clip bars (Medi's microphone; both speakers), the line written as Version A / B / C
   (the page never says which engine or person wrote which), and one or two questions with big buttons:
     type 'versions'  the versions are the buttons, plus "Something else" (a box for what he really said)
     type 'options'   fixed choices (Yes / No / Not sure, Same slip / Two different slips ...)
   Saved the way her first listening check saves: a row in amal_rules with her link's token - source 'listen-check',
   kind = the list's kind (slip_check, own_fix, word_said, old_new, word_there, one_or_two), word_key '<prefix>:<item id>',
   payload {<field>: value for every question answered so far, typed, done, text, label, set, list} - queued in
   localStorage first. Every tap writes the card's whole answer, so the latest row is the answer; a tap can be changed,
   and the shared Undo (AM-17) writes a row of kind 'undo', never a delete.
   scripts/amal_listen_results.py reads the answers against the keys. Nothing here sends anything to anyone.
   AneesCheckTask.mount(el, {token, base, list, data?}, {onChange}) · AneesCheckTask.count(data, rows) for the hub row */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const SOURCE = 'listen-check';
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const day = d => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || ''); return m ? MONTHS[+m[2] - 1] + ' ' + (+m[3]) : String(d || ''); };
  // a line of English with his or her Arabic words inside: each piece is isolated, so the words never swap sides
  const parts = t => Array.isArray(t) ? t.map(s => `<bdi>${esc(s)}</bdi>`).join('') : esc(t);
  const UP = k => String(k || '').toUpperCase();
  const fieldsOf = D => (D.questions || []).map(q => q.field);
  const complete = (D, a) => !!a && fieldsOf(D).every(f => a[f]);
  // the hub row's count: rows = her amal_rules rows of this list's prefix, oldest first (the latest per item wins)
  function count(D, rows) {
    const lat = {}; (rows || []).forEach(r => { if (r && r.word_key != null) lat[r.word_key] = r; });
    const done = (D.items || []).filter(x => { const r = lat[D.prefix + ':' + x.id]; return r && r.kind !== 'undo' && complete(D, r.payload || {}); }).length;
    return { total: (D.items || []).length, done };
  }

  if (typeof document !== 'undefined' && !document.getElementById('ck-css')) {
    const css = document.createElement('style'); css.id = 'ck-css';
    css.textContent = `#anees-bank .ck-ver{font-size:20px;line-height:1.5;font-weight:500;min-height:56px;display:flex;gap:10px;align-items:flex-start;text-align:start}
#anees-bank .ck-ver>span:first-child,#anees-bank .ck-info>span:first-child{flex:0 0 auto;font:600 12px/26px var(--sabz-font-sans);width:26px;height:26px;margin-top:3px;border-radius:50%;border:1px solid currentColor;text-align:center;opacity:.7}
#anees-bank .ck-ver>span:last-child,#anees-bank .ck-info>span:last-child{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;text-align:start;unicode-bidi:plaintext}
#anees-bank .ck-info{display:flex;gap:10px;align-items:flex-start;font-size:19px;line-height:1.5;margin:2px 0}
#anees-bank .ck-opts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
#anees-bank .ck-opts .hb-ans{text-align:center;font-size:15px}
#anees-bank .hb-ans[aria-pressed="true"]{background:var(--vp-sage,#2E6A4E);color:#fff;border-color:transparent}
#anees-bank .hb-ans[disabled]{opacity:.55;cursor:default}
#anees-bank .ck-ask{font:600 16px var(--sabz-font-sans);margin:10px 0 2px}
#anees-bank .ck-note{font-size:15.5px;margin:2px 0;overflow-wrap:anywhere}
#anees-bank .ck-lab{font-size:12.5px;color:var(--ab-muted);margin:6px 0 0}
#anees-bank .ck-warn{color:var(--sabz-danger,#B3261E);font-weight:600}`;
    (document.head || document.documentElement).appendChild(css);
  }

  function mount(el, item, opt) {
    opt = opt || {};
    const TOKEN = item.token || '', BASE = item.base || '', LIST = String(item.list || '').replace(/[^a-z0-9-]/g, '');
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H, ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });
    const QK = 'anees-amal-check-q-' + LIST + '-' + TOKEN, AK = 'anees-amal-check-a-' + LIST + '-' + TOKEN;
    let DATA = item.data || null, answers = {}, flushing = false;
    const openBox = new Set();          // cards whose "Something else" box is open (kept open across redraws)
    el.innerHTML = '<div class="hb-task"><p class="hb-prog" data-prog>Loading…</p><div data-root></div><p class="hb-foot" data-foot>Saved as you tap · you can change an answer · stop any time</p></div>';
    const $root = el.querySelector('[data-root]'), $prog = el.querySelector('[data-prog]');

    const items = () => (DATA && DATA.items) || [], Q = () => (DATA && DATA.questions) || [];
    const key = x => DATA.prefix + ':' + x.id;
    const pending = k => (LS(QK) || []).some(j => j.body.word_key === k);
    const answerOf = x => { const a = answers[key(x)]; return a && AneesUndo.isAnswer(a) && fieldsOf(DATA).some(f => a[f]) ? a : null; };
    const label = (q, x, v) => { if (!v) return ''; if (q.type === 'versions') return v === 'other' ? (q.other || 'Something else') : 'Version ' + UP(v);
      const o = (q.options || []).find(o => o.v === v); return o ? o.label : v; };

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

    // the part of a card that changes with her answer (the clip bars above it are never redrawn, so they keep playing)
    function stateHtml(x) {
      const a = answerOf(x) || {}, off = TOKEN ? '' : ' disabled', box = openBox.has(x.id);
      const qs = Q().map((q, n) => {
        const ask = `<p class="ck-ask">${parts(n === 0 && x.ask ? x.ask : q.ask)}</p>`, cur = a[q.field] || '';
        if (q.type === 'versions') {
          return ask + `<div class="hb-btns">` + (x.versions || []).map(v => `<button type="button" class="hb-ans ck-ver" data-ck="${esc(q.field)}" data-v="${esc(v.k)}" aria-pressed="${cur === v.k}" dir="auto"${off}><span aria-hidden="true">${esc(UP(v.k))}</span><span lang="ar" dir="auto">${esc(v.text)}</span></button>`).join('')
            + (q.other ? `<button type="button" class="hb-ans" data-ck="${esc(q.field)}" data-v="other" aria-pressed="${cur === 'other'}"${off}>${esc(q.other)}</button>
            <div data-typed${box ? '' : ' hidden'}><textarea class="hb-input" dir="auto" lang="ar" placeholder="What did he say? (optional)" aria-label="What he said">${esc(box && cur === 'other' ? a.typed || '' : '')}</textarea>
            <button type="button" class="hb-ans primary" data-ck="typed-save" data-f="${esc(q.field)}"${off}>Save</button></div>` : '') + '</div>';
        }
        return ask + `<div class="ck-opts">` + (q.options || []).map(o => `<button type="button" class="hb-ans" data-ck="${esc(q.field)}" data-v="${esc(o.v)}" aria-pressed="${cur === o.v}"${off}>${esc(o.label)}</button>`).join('') + '</div>';
      }).join('');
      const any = answerOf(x), done = complete(DATA, any);
      const said = any ? Q().filter(q => any[q.field]).map(q => label(q, x, any[q.field]) + (q.type === 'versions' && any[q.field] === 'other' && any.typed ? ': ' + any.typed : '')).join(' · ') : '';
      return qs + (any ? AneesUndo.answered((pending(key(x)) ? 'Saving… ' : 'Saved · ') + said + (done ? '' : ' · one more tap on this card'), { 'data-ck': 'undo' }) : '');
    }
    function state(x) {
      const card = $root.querySelector(`[data-id="${CSS.escape(x.id)}"]`); if (!card) return;
      const wrap = card.querySelector('[data-typed]'), box = wrap && wrap.querySelector('textarea'), keep = box && !wrap.hidden && openBox.has(x.id) ? box.value : null, had = box && document.activeElement === box;
      card.querySelector('[data-state]').innerHTML = stateHtml(x);
      if (keep != null) { const t = card.querySelector('[data-typed] textarea'); if (t) { t.value = keep; if (had) t.focus(); } }
      progress();
    }
    function progress() {
      const n = items().length, done = items().filter(x => complete(DATA, answerOf(x))).length;
      $prog.textContent = n ? `${done} of ${n} answered${done === n ? ' · all done, thank you!' : ''}` : 'Nothing to check right now.';
      opt.onChange && opt.onChange({ total: n, done, finished: n > 0 && done === n });
    }
    // a clip is a cut file, or a window of the full lesson audio ("<date>/audio/lesson.mp3#t=start,end") - Medi 2026-10-06
    // "amal doesnt correct me here? why are we not including this context in all of them": both voices, a little before and after
    function bar(src) { if (!root.AneesClip) return null; const [f, frag] = String(src).split('#t='), [st, en] = (frag || '').split(',').map(Number);
      return AneesClip.bar({ src: BASE + 'lessons/' + f, start: frag ? st : 0, end: frag ? en : null }); }
    function render() {
      const versionsAreButtons = Q().some(q => q.type === 'versions');
      $root.innerHTML = items().map((x, n) => `<article class="hb-moment hb-card" data-id="${esc(x.id)}">
        <p class="hb-prog">${n + 1} of ${items().length} · lesson ${esc(day(x.date))} · ${esc(x.mmss || '')}</p>
        ${x.note ? `<p class="ck-note">${parts(x.note)}</p>` : ''}
        ${(x.clips || []).map((c, i) => `<p class="ck-lab">${esc(c.label || '')}</p><div data-bar="${i}"></div>`).join('')}
        ${(x.rows || []).map(r => `<p class="ck-lab">${esc(r.label || '')}</p><p class="ck-note">${parts(r.text || '')}</p>`).join('')}
        ${!versionsAreButtons && (x.versions || []).length ? `<p class="ck-lab">His line, written two ways</p>` + x.versions.map(v => `<div class="ck-info"><span aria-hidden="true">${esc(UP(v.k))}</span><span lang="ar" dir="auto">${esc(v.text)}</span></div>`).join('') : ''}
        <div data-state></div></article>`).join('') || '<p class="hb-empty">Nothing to check right now.</p>';
      items().forEach(x => {
        const card = $root.querySelector(`[data-id="${CSS.escape(x.id)}"]`);
        (x.clips || []).forEach((c, i) => { const b = bar(c.src); if (b) card.querySelector(`[data-bar="${i}"]`).appendChild(b); });
        state(x);
      });
      progress();
    }
    function decide(x, field, value, typed) {
      const k = key(x), was = answerOf(x) || {}, f = {};
      fieldsOf(DATA).forEach(n => { if (was[n]) f[n] = was[n]; });
      f[field] = value;
      const q = Q().find(q => q.type === 'versions'), v = q && f[q.field], ver = v && (x.versions || []).find(y => y.k === v);
      const t = q && f[q.field] === 'other' ? (typed !== undefined ? typed : was.typed) || null : null;
      // a newer tap replaces one that was not sent yet; a sent one is simply followed by this row (the latest wins)
      LS(QK, AneesUndo.unqueue(LS(QK) || [], j => j.body.word_key === k && j.body.kind !== 'undo'));
      answers[k] = { kind: DATA.kind, ...f, typed: t, at: new Date().toISOString() }; LS(AK, answers);
      push({ token: TOKEN, source: SOURCE, lesson_date: null, kind: DATA.kind, word_key: k,
             payload: { ...f, typed: t, done: complete(DATA, f), text: ver ? ver.text : null, label: x.date + ' ' + (x.mmss || ''), set: DATA.set || null, list: DATA.list || LIST } });
      state(x);
    }
    function undo(x) {   // AM-17: a new 'undo' row; a tap not sent yet leaves the queue
      const k = key(x), was = answerOf(x); if (!was) return;
      LS(QK, AneesUndo.unqueue(LS(QK) || [], j => j.body.word_key === k && j.body.kind !== 'undo'));
      answers[k] = { kind: 'undo', at: new Date().toISOString() }; LS(AK, answers);
      push(AneesUndo.row({ token: TOKEN, source: SOURCE, lesson_date: null, kind: DATA.kind, word_key: k, payload: { label: x.date + ' ' + (x.mmss || '') } }));
      openBox.delete(x.id); state(x);
    }
    el.addEventListener('click', e => {
      const b = e.target.closest('button[data-ck]'); if (!b || !TOKEN || !DATA) return;
      const card = b.closest('[data-id]'), x = items().find(i => i.id === card.dataset.id), act = b.dataset.ck; if (!x) return;
      if (act === 'undo') undo(x);
      else if (act === 'typed-save') { const v = card.querySelector('[data-typed] textarea').value.trim(); openBox.delete(x.id); decide(x, b.dataset.f, 'other', v || null); }
      else if (b.dataset.v === 'other') {      // saved at once; the box is for what he really said (optional)
        const a = answerOf(x); openBox.add(x.id);
        if (!a || a[act] !== 'other') decide(x, act, 'other'); else state(x);
        const t = card.querySelector('[data-typed] textarea'); if (t) t.focus();
      }
      else { if (Q().some(q => q.field === act && q.type === 'versions')) openBox.delete(x.id); decide(x, act, b.dataset.v); }
    });

    (async () => {
      if (!DATA) {
        try { const r = await fetch(BASE + 'data/amal-check-' + LIST + '.json', { cache: 'no-store' }); if (!r.ok) throw new Error(r.status); DATA = await r.json(); }
        catch (e) { $prog.textContent = 'The list could not load. Refresh to try again.'; return; }
      }
      answers = LS(AK) || {};
      if (!TOKEN) $prog.insertAdjacentHTML('afterend', '<p class="hb-sub ck-warn">This page was opened without the private link the student sent, so answers cannot be saved. You can still listen.</p>');
      else {
        try {   // once this browser's taps are sent, the live answers win (latest row per card; an undo = open again)
          const saved = await (await api('GET', 'amal_rules?select=kind,word_key,payload,created_at&source=eq.' + SOURCE + '&word_key=like.' + encodeURIComponent(DATA.prefix) + ':*&order=created_at.asc&token=eq.' + encodeURIComponent(TOKEN))).json();
          if (!Array.isArray(saved)) throw new Error('read');
          const server = {}, mine = new Set(items().map(key));
          saved.filter(r => mine.has(r.word_key)).forEach(r => { const p = r.payload || {}, a = { kind: r.kind, typed: p.typed || null, at: r.created_at }; fieldsOf(DATA).forEach(f => { if (p[f]) a[f] = p[f]; }); server[r.word_key] = a; });
          answers = AneesUndo.reconcile(answers, server, (LS(QK) || []).map(j => j.body.word_key), true); LS(AK, answers);
        } catch (e) {}
      }
      render(); flush();
      setInterval(() => { if ((LS(QK) || []).length) flush(); }, 3000);
    })();
  }
  root.AneesCheckTask = { mount, count, SOURCE };
})(typeof window !== 'undefined' ? window : globalThis);
