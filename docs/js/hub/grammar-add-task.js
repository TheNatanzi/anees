/* AM-31 'Add grammar' on the Tutor page (Medi 2026-10-12: "lets do a handoff chip to create a way for amal to add grammar.
   Shes jsut going to put the lesson and you give it a letter# and rewrite it and have her approve" / "make it an option in
   the tutor portal "add grammar"").

   She writes a grammar lesson in her own words (one box) + an optional example sentence. Claude gives it the next free
   letter-number and rewrites it as a rule card (scripts/tutor_grammar.py, run by the 15-minute trigger and the hourly job;
   docs/data/tutor-grammar.json). She sees "Rule A18 · <name> · <rule> · <examples>" and taps Yes, add it · Change it (one
   box: what to change -> Claude rewrites it) · Not a rule. Undo on every answer (AM-17), a note box on every card (AM-27).
   Only her yes adds the rule (a new bucket, no automatic detection until a person adds one).

   Her rows: amal_rules source 'tutor_grammar' (no migration), written with the hub's grammar-notes link token:
     tgram:<sid>          kind grammar_submit  payload {text, example}     (undo row = withdrawn; a new submit = back)
     tgram:<sid>:answer   kind grammar_yes | grammar_change | grammar_no | undo, payload {v, id, what}
   The latest row per key wins; an answer counts only for the proposal version it names (payload.v).
   The same rules as scripts/tutor_grammar.py (reduce_rows / answer_for / state); tests/test_grammar_add_task.cjs.

   AM-32 (Medi 2026-10-12: "it would be nice to have you detect new grammar and suggest it if you hear it in our convo"):
   a card can also come from a lesson - Claude read the transcript and heard her teach grammar that fits no rule
   (scripts/tutor_grammar.py hear). It has no submit row: data.items[].heard = {date, t, quote, line, before}; it reads
   'Claude heard this in the Oct 9 lesson at 14:15' with her words and the student's line, and takes the same answers.

   AneesGrammarAdd.mount(el, {token, data}, {onChange}); AneesGrammarAdd.count(items) */
(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api; else root.AneesGrammarAdd = api;
})(typeof self !== 'undefined' ? self : this, function (root) {
  'use strict';
  const SOURCE = 'tutor_grammar', SUBMIT = 'grammar_submit', YES = 'grammar_yes', CHANGE = 'grammar_change', NO = 'grammar_no', UNDO = 'undo';
  const LSK = 'anees-tgram-local';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pretty = d => d ? new Date(/T/.test(String(d)) ? d : String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';   // a timestamp in her own time zone

  function sidOf(key) {
    const m = /^tgram:([A-Za-z0-9_-]{4,64})(:answer)?$/.exec(String(key || ''));
    return m ? { sid: m[1], answer: !!m[2] } : { sid: null, answer: false };
  }
  const order = r => String(r.created_at || '') + '|' + String(r.id ?? '').padStart(12, '0');

  /** her rows (any order) -> {sid: {sid, text, example, at, withdrawn, answer}}; latest row per key wins (AM-17).
      heard {sid: {date, t, quote, line, before, at}} (AM-32): moments Claude heard her teach, with no submit row */
  function reduce(rows, heard) {
    const subs = {}, ans = {};
    (rows || []).filter(r => r && (r.source || SOURCE) === SOURCE).slice().sort((a, b) => order(a).localeCompare(order(b))).forEach(r => {
      const k = sidOf(r.word_key); if (!k.sid) return;
      const p = r.payload || {};
      if (k.answer) ans[k.sid] = r.kind === UNDO ? null : { kind: r.kind, v: p.v, what: String(p.what || ''), at: r.created_at };
      else if (r.kind === SUBMIT) subs[k.sid] = { sid: k.sid, text: String(p.text || '').trim(), example: String(p.example || '').trim(), at: r.created_at, withdrawn: false };
      else if (r.kind === UNDO && subs[k.sid]) subs[k.sid].withdrawn = true;
    });
    Object.entries(heard || {}).forEach(([sid, h]) => { if (!subs[sid]) subs[sid] = { sid, text: String(h.quote || ''), example: '', at: h.at || null, withdrawn: false, heard: h }; });
    Object.values(subs).forEach(s => { s.answer = ans[s.sid] || null; });
    return subs;
  }
  const current = vs => (vs && vs.length) ? vs[vs.length - 1] : null;
  function answerFor(sub, vs) { const c = current(vs), a = sub.answer; return c && a && a.v === c.v ? a : null; }
  /** waiting | proposed | added | not_rule | not_grammar | withdrawn (same as tutor_grammar.state) */
  function state(sub, vs) {
    if (sub.withdrawn) return 'withdrawn';
    const c = current(vs), a = answerFor(sub, vs);
    if (!c) return 'waiting';
    if (a && a.kind === CHANGE) return 'waiting';
    if (a && a.kind === YES) return 'added';
    if (a && a.kind === NO) return 'not_rule';
    return c.grammar === false ? 'not_grammar' : 'proposed';
  }
  /** the cards, newest first: [{sub, versions, cur, state}] */
  function items(rows, data) {
    const V = {}, H = {};
    ((data && data.items) || []).forEach(x => { V[x.sid] = x.versions || []; if (x.heard) H[x.sid] = Object.assign({ at: x.at }, x.heard); });
    return Object.values(reduce(rows, H)).map(sub => { const vs = V[sub.sid] || []; return { sub, versions: vs, cur: current(vs), state: state(sub, vs) }; })
      .sort((a, b) => String(b.sub.at || '').localeCompare(String(a.sub.at || '')));
  }
  /** the tab's number: proposals waiting for her answer */
  function count(list) {
    const L = list || [];
    return { toApprove: L.filter(x => x.state === 'proposed' || x.state === 'not_grammar').length, waiting: L.filter(x => x.state === 'waiting').length, total: L.length };
  }
  /** the amal_rules row one action writes */
  function row(kind, sid, token, payload) {
    const answer = kind !== SUBMIT && !(kind === UNDO && payload && payload.undoes === SUBMIT);
    return { token: token || '', source: SOURCE, lesson_date: null, kind, word_key: 'tgram:' + sid + (answer ? ':answer' : ''),
             payload: Object.assign({ lid: 'l' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7) }, payload || {}) };
  }
  function newSid() {
    const a = new Uint8Array(9);
    if (root && root.crypto && root.crypto.getRandomValues) root.crypto.getRandomValues(a); else for (let i = 0; i < a.length; i++) a[i] = Math.floor(Math.random() * 256);
    return Array.from(a, b => (b % 36).toString(36)).join('');
  }
  /** mirror rows + live rows (same id once) + this browser's rows the server has not shown yet (by payload.lid) */
  function merge(mirror, live, local) {
    const out = [], ids = new Set(), lids = new Set();
    (mirror || []).concat(live || []).forEach(r => { if (r.id != null && ids.has(String(r.id))) return; if (r.id != null) ids.add(String(r.id)); out.push(r); if (r.payload && r.payload.lid) lids.add(r.payload.lid); });
    (local || []).forEach(r => { if (!lids.has((r.payload || {}).lid)) out.push(r); });
    return out;
  }

  function exHtml(e) {
    return `<li><b>${esc(e.arabizi || e.arabic)}</b>${e.arabizi && e.arabic ? ` <span lang="ar" dir="rtl" class="tg-ar">${esc(e.arabic)}</span>` : ''}${e.english ? ` · ${esc(e.english)}` : ''}${e.hers ? '' : ' <span class="tg-unv">example by Claude · spelling unverified</span>'}</li>`;
  }
  function cardHtml(x) {
    const s = x.sub, c = x.cur, U = { answered: (t, a) => root.AneesUndo.answered(t, a) };   // AM-17: the shared Undo
    const h = s.heard;
    const yours = h
      ? `<p class="tg-heard">Claude heard this in the ${esc(pretty(h.date))} lesson at ${esc(h.t)}</p>
         <p class="tg-yours"><span>You said:</span> <span dir="auto">«${esc(h.quote)}»</span></p>
         ${h.before ? `<p class="tg-yours"><span>Just before, the student said:</span> <span dir="auto">«${esc(h.before)}»</span></p>` : ''}`
      : `<p class="tg-yours"><span>Your words:</span> «${esc(s.text)}»${s.example ? ` · your example: «${esc(s.example)}»` : ''}</p>`;
    const id = `data-id="tgram-${esc(s.sid)}"`;
    if (x.state === 'withdrawn') return `<article class="tg-card tg-off" ${id}>${yours}${U.answered('You took this one back', { 'data-tg-resend': s.sid })}</article>`;
    if (x.state === 'waiting') {
      const a = answerFor(s, x.versions);
      return `<article class="tg-card" ${id}><p class="tg-wait">${a ? `Your change: «${esc(a.what)}» · Claude is rewriting it` : `Sent ${esc(pretty(s.at))} · Claude is writing it as a rule`}</p>${yours}
        <p class="tu-meta">It shows here for you to approve, usually within the hour.</p>
        ${U.answered(a ? 'Change sent' : 'Sent to Claude', a ? { 'data-tg-undo': s.sid } : { 'data-tg-withdraw': s.sid })}</article>`;
    }
    const head = c.grammar === false
      ? `<h3 class="tg-title">Claude did not find a grammar rule here</h3><p class="tg-one">${esc(c.why || '')}</p>`
      : `<h3 class="tg-title"><span class="tg-id">Rule ${esc(c.id)}</span> · ${esc(c.name)}</h3><p class="tg-one">${esc(c.one_line)}</p>
         ${c.formula ? `<p class="tg-formula"><span>Pattern:</span> ${esc(c.formula)}</p>` : ''}
         <ul class="tg-ex">${(c.examples || []).map(exHtml).join('')}</ul>
         ${c.why ? `<p class="tu-meta">${esc(c.why)}</p>` : ''}
         ${c.overlaps ? `<p class="tg-over">Close to <b>${esc(c.overlaps.id)}</b> ${esc(c.overlaps.name)}${c.overlaps.why ? ': ' + esc(c.overlaps.why) : ''}</p>` : ''}`;
    let foot;
    if (x.state === 'added') foot = U.answered(`Added as ${c.id} · it shows on the Grammar Rules pages after the next update`, { 'data-tg-undo': s.sid });
    else if (x.state === 'not_rule') foot = U.answered('You said: not a rule', { 'data-tg-undo': s.sid });
    else foot = `<div class="hb-btns">${c.grammar === false ? '' : `<button type="button" class="hb-ans primary" data-tg-yes="${esc(s.sid)}">Yes, add it<small>${esc(c.id)} becomes one of the student's grammar rules</small></button>`}
        <button type="button" class="hb-ans" data-tg-change="${esc(s.sid)}">Change it<small>say what to change; Claude rewrites it</small></button>
        <button type="button" class="hb-ans" data-tg-no="${esc(s.sid)}">Not a rule<small>nothing is added</small></button></div>
        <div class="tg-chg" data-tg-box="${esc(s.sid)}" hidden><textarea class="hb-input" rows="2" dir="auto" maxlength="1000" placeholder="What should change? (the name, the rule, an example…)"></textarea>
        <button type="button" class="hb-ans primary" data-tg-send="${esc(s.sid)}">Send the change</button></div>`;
    return `<article class="tg-card" ${id}>${c.v > 1 ? `<p class="tu-meta">Rewritten after your change (version ${esc(c.v)})</p>` : ''}${head}${yours}${foot}</article>`;
  }

  function mount(el, ctx, opt) {
    opt = opt || {};
    const A = root.ANEES || {}, token = (ctx && ctx.token) || '', data = (ctx && ctx.data) || { items: [], rows: [] };
    const local = () => { try { return JSON.parse(localStorage.getItem(LSK) || '[]'); } catch (e) { return []; } };
    const setLocal = L => { try { localStorage.setItem(LSK, JSON.stringify(L.slice(-200))); } catch (e) { /* private window */ } };
    let live = [], msg = '';
    const H = { apikey: A.anon, Authorization: 'Bearer ' + A.anon, 'Content-Type': 'application/json', 'X-Anees-Token': token };

    async function readLive() {
      if (!token || !A.url) return;
      try {
        const r = await fetch(A.url + '/rest/v1/amal_rules?select=id,created_at,source,kind,word_key,payload&source=eq.' + SOURCE + '&order=created_at.asc&token=eq.' + encodeURIComponent(token), { headers: H });
        if (r.ok) live = await r.json();
      } catch (e) { /* offline: the mirror + this browser's rows stand */ }
    }
    async function write(b) {
      b.created_at = new Date().toISOString();
      setLocal(local().concat([b]));                    // shown at once; dropped when the server has it (payload.lid)
      if (!token || !A.url) { msg = 'Open this page from your private link to save. Kept on this device for now.'; return draw(); }
      try {
        const body = Object.assign({}, b); delete body.created_at;
        const r = await fetch(A.url + '/rest/v1/amal_rules', { method: 'POST', headers: Object.assign({}, H, { Prefer: 'return=minimal' }), body: JSON.stringify(body) });
        msg = r.ok ? '✓ Saved' : 'Could not save - kept on this device, try again';
      } catch (e) { msg = 'Could not save - kept on this device, try again'; }
      await readLive(); draw();
    }
    const list = () => items(merge(data.rows, live, local()), data);
    const find = sid => list().find(x => x.sub.sid === sid);

    function draw() {
      const L = list(), c = count(L);
      const keep = el.querySelector('#tg-text'), kept = keep ? keep.value : '', keptEx = (el.querySelector('#tg-example') || {}).value || '';
      el.innerHTML = `<div class="hb-task tg">
        <p class="hb-sub">Write a grammar lesson in your own words. Claude gives it a letter-number (like A18), writes it as a rule card for the student, and you approve it here. Nothing changes until you tap <b>Yes, add it</b>.</p>
        <label class="tg-l" for="tg-text">The grammar lesson</label>
        <textarea id="tg-text" class="hb-input" rows="5" dir="auto" maxlength="3000" placeholder="For example: after laazem the verb has no b-: laazem aroo7, not laazem baroo7"></textarea>
        <label class="tg-l" for="tg-example">An example sentence (optional) · Arabic or Arabizi</label>
        <input id="tg-example" class="hb-input" dir="auto" maxlength="600">
        <button type="button" class="hb-ans primary" id="tg-send">Send to Claude<small>you will see the rule card here to approve</small></button>
        <p class="tu-meta" id="tg-msg" aria-live="polite">${esc(msg)}</p>
        ${L.length ? `<h3 class="tg-h">Your grammar (${c.toApprove ? c.toApprove + ' to approve' : 'nothing to approve'}${c.waiting ? ' · ' + c.waiting + ' with Claude' : ''})</h3>` : ''}
        <div class="tg-list">${L.map(cardHtml).join('')}</div>
        <p class="hb-foot">Saved as you tap · only your yes adds a rule · the app has no automatic detection for a new rule yet</p></div>`;
      el.querySelector('#tg-text').value = kept; el.querySelector('#tg-example').value = keptEx;
      el.querySelector('#tg-send').onclick = () => {
        const t = el.querySelector('#tg-text').value.trim(), e = el.querySelector('#tg-example').value.trim();
        if (!t) { el.querySelector('#tg-msg').textContent = 'Write the grammar lesson first.'; return; }
        el.querySelector('#tg-text').value = ''; el.querySelector('#tg-example').value = '';
        write(row(SUBMIT, newSid(), token, { text: t.slice(0, 3000), example: e.slice(0, 600) }));
      };
      const on = (sel, fn) => el.querySelectorAll(sel).forEach(b => { b.onclick = () => fn(b); });
      on('[data-tg-yes]', b => { const x = find(b.dataset.tgYes); if (x) write(row(YES, x.sub.sid, token, { v: x.cur.v, id: x.cur.id, label: 'Yes, add it' })); });
      on('[data-tg-no]', b => { const x = find(b.dataset.tgNo); if (x) write(row(NO, x.sub.sid, token, { v: x.cur.v, id: x.cur.id || null, label: 'Not a rule' })); });
      on('[data-tg-change]', b => { const box = el.querySelector(`[data-tg-box="${b.dataset.tgChange}"]`); box.hidden = !box.hidden; if (!box.hidden) box.querySelector('textarea').focus(); });
      on('[data-tg-send]', b => { const x = find(b.dataset.tgSend), what = el.querySelector(`[data-tg-box="${b.dataset.tgSend}"] textarea`).value.trim();
        if (x && what) write(row(CHANGE, x.sub.sid, token, { v: x.cur.v, id: x.cur.id || null, what: what.slice(0, 1000), label: 'Change it' })); });
      on('[data-tg-undo]', b => { const x = find(b.dataset.tgUndo), a = x && x.sub.answer; if (x) write(row(UNDO, x.sub.sid, token, { undoes: a ? a.kind : null, label: 'Undo' })); });
      on('[data-tg-withdraw]', b => write(row(UNDO, b.dataset.tgWithdraw, token, { undoes: SUBMIT, label: 'Undo' })));
      on('[data-tg-resend]', b => { const x = find(b.dataset.tgResend); if (x) write(Object.assign(row(SUBMIT, x.sub.sid, token, { text: x.sub.text, example: x.sub.example }), {})); });
      if (root.AneesNote && !el.dataset.anNote) root.AneesNote.attach(el, { token, list: 'add-grammar', title: 'Add grammar' });
      opt.onChange && opt.onChange(c);
    }
    if (typeof document !== 'undefined' && !document.getElementById('tg-css')) {
      const s = document.createElement('style'); s.id = 'tg-css';
      s.textContent = `#anees-bank .tg-l{display:block;font-size:13px;font-weight:600;color:var(--ab-muted);margin:6px 0 4px}#anees-bank .tg-h{font-size:16px;margin:22px 0 10px}
#anees-bank .tg-list{display:grid;gap:12px}#anees-bank .tg-card{border:1px solid var(--ab-line);background:var(--ab-bg);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0;overflow-wrap:anywhere}
#anees-bank .tg-off{opacity:.7}#anees-bank .tg-title{font-family:var(--sabz-font-serif);font-size:18px;font-weight:500;margin:0}#anees-bank .tg-id{color:var(--vp-sage,#2E6A4E);font-weight:600}
#anees-bank .tg-one{margin:0;font-size:15px}#anees-bank .tg-formula,#anees-bank .tg-yours,#anees-bank .tg-over{margin:0;font-size:14px}#anees-bank .tg-formula span,#anees-bank .tg-yours span{color:var(--ab-muted)}
#anees-bank .tg-ex{margin:0;padding-left:18px;display:grid;gap:3px}#anees-bank .tg-ar{font-size:15px}#anees-bank .tg-unv{font-size:12px;color:var(--ab-muted);border:1px dashed var(--ab-line);border-radius:999px;padding:0 6px}
#anees-bank .tg-wait{margin:0;font-weight:600}#anees-bank .tg-heard{margin:0;font-size:13px;font-weight:600;color:var(--vp-sage,#2E6A4E)}#anees-bank .tg-chg{display:grid;gap:6px}#anees-bank .tg-chg[hidden]{display:none}`;
      document.head.appendChild(s);
    }
    draw();
    readLive().then(draw);
    // rule L1 (S7): her rows are live data - read again when the tab comes back into view (draw keeps her typing)
    if (root.AneesLive && root.AneesLive.onReturn) root.AneesLive.onReturn(() => readLive().then(draw), { label: 'add grammar' });
    return { redraw: draw };
  }
  return { mount, count, items, reduce, state, answerFor, current, merge, row, sidOf, SOURCE, SUBMIT, YES, CHANGE, NO, UNDO };
});
