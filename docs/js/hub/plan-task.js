/* "Before the lesson" planner: what today's lesson is about, the words to use, the suggested sentences (keep / drop /
   edit). ONE module for the Tutor hub panel and the old address amal/plan.html. Same saving as before: amal_rules source
   'planner' (kind topic / new_words / repeat / keep / drop / edit) and the link's answers in amal_links, queued in
   localStorage first (keys anees-amal-q-/a-<token>).
   AM-17 (Medi 2026-10-02 "can you add an undo button to all these tutor hub stuff"): every answered step is listed under
   "Your answers" with the shared Undo: the step leaves the link's answers (logged in answers.undone), each of its taps
   gets an amal_rules row of kind 'undo' (never a delete), and the step opens again at once.
   AneesPlanTask.mount(el, item, {onChange}) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };

  function mount(el, item, opt) {
    opt = opt || {};
    const TOKEN = item.token;
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H, ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });
    const QK = 'anees-amal-q-' + TOKEN, AK = 'anees-amal-a-' + TOKEN;
    let link = null, answers = {}, step = 0, screens = [], flushing = false, pendingDone = false;
    el.innerHTML = '<div class="hb-task"><p class="hb-prog" data-prog></p><div data-root><p class="hb-sub">Loading…</p></div><div data-answers></div><p class="hb-foot"><a href="#" data-quit>Stop here</a> · saved as you tap</p></div>';
    const $root = el.querySelector('[data-root]'), $prog = el.querySelector('[data-prog]'), $quit = el.querySelector('[data-quit]'), $ans = el.querySelector('[data-answers]');
    async function flush() {
      if (flushing) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = job.kind === 'rule' ? await api('POST', 'amal_rules', job.body, { Prefer: 'return=minimal' }) : await api('PATCH', 'amal_links?token=eq.' + encodeURIComponent(TOKEN), job.body, { Prefer: 'return=minimal' }); ok = r.ok || r.status === 409; } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2000)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; if (pendingDone && !(LS(QK) || []).length) { pendingDone = false; showDone(); }
    }
    setInterval(() => { if ((LS(QK) || []).length) flush(); }, 3000);
    const push = (kind, body) => { const q = LS(QK) || []; q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), kind, body }); LS(QK, q); flush(); };
    const tap = (kind, word_key, payload) => ({ token: TOKEN, source: 'planner', lesson_date: link.lesson_date, kind, word_key, payload });
    const rule = (kind, word_key, payload) => push('rule', tap(kind, word_key, payload));
    const unrule = (kind, word_key, payload, match) => push('rule', AneesUndo.row(tap(kind, word_key, payload), match));
    function save(flag) { answers.updated = new Date().toISOString(); LS(AK, answers); const body = { answers }; if (flag === 'done') body.done_at = answers.updated; if (flag === 'reopen') body.done_at = null; if (!link.opened_at) body.opened_at = answers.updated; push('link', body); }
    const isDone = s => s.answered();
    function report() { if (opt.onChange) opt.onChange({ done: screens.filter(isDone).length, total: screens.length, finished: !!answers.done }); }
    function answeredList() {
      const S = screens.filter(isDone);
      $ans.innerHTML = S.length ? `<p class="hb-prog" style="margin-top:16px">Your answers (${S.length})</p><ul class="hb-done">${S.map((s, j) => `<li data-answered="${esc(s.key)}"><span><b>${esc(s.title)}</b> · ${esc(s.said())}</span>${AneesUndo.button({ 'data-undo': s.key })}</li>`).join('')}</ul>` : '';
      $ans.querySelectorAll('[data-undo]').forEach(b => b.onclick = () => undo(b.dataset.undo));
    }
    function show(i) { step = i; answers.step = i; LS(AK, answers); const s = screens[i]; if (!s) { finish(); return; } $prog.textContent = s.prog; $root.innerHTML = s.html; s.wire && s.wire(); report(); answeredList(); }
    const next = () => { let i = step + 1; while (screens[i] && isDone(screens[i])) i++; show(i); };
    function showDone() { $prog.textContent = 'Done'; $root.innerHTML = '<h3 class="hb-q">All saved. Have a good lesson!</h3><p class="hb-sub">Medi\'s app suggested; you decided. Tap Undo on any answer to change it.</p>'; $quit.parentElement.hidden = true; report(); answeredList(); }
    function finish() { answers.done = true; save('done'); $prog.textContent = 'Saving…'; $root.innerHTML = '<h3 class="hb-q">Saving your answers…</h3>'; $quit.parentElement.hidden = true; if (!(LS(QK) || []).length) showDone(); else { pendingDone = true; flush(); } }
    function undo(key) {
      const i = screens.findIndex(s => s.key === key), s = screens[i]; if (!s || !isDone(s)) return;
      answers.undone = AneesUndo.log(answers.undone, key, s.said()); s.undo();
      const reopen = !!answers.done; answers.done = false; pendingDone = false; $quit.parentElement.hidden = false;
      save(reopen ? 'reopen' : null); show(i);
    }
    const btn = (label, sub, cls, id) => `<button type="button" id="${id}" class="hb-ans${cls ? ' ' + cls : ''}">${esc(label)}${sub ? `<small>${esc(sub)}</small>` : ''}</button>`;
    function build(p) {
      const S = [], P = TOKEN.slice(0, 6);
      const MENU = (p.topics && p.topics.length > 3) ? p.topics : ["Last week's lessons", 'Grammar', 'New verbs', 'New nouns', 'New adjectives', 'Common sayings', 'Review listening', 'Review conversation', 'Other topic'];
      const total = 2 + (p.sentences || []).length;
      S.push({ key: 'topic', title: "Today's lesson", answered: () => !!answers.topic, said: () => answers.topic || '', prog: `1 of ${total}`,
        undo() { unrule('topic', null, { topic: answers.topic }, { topic: answers.topic }); unrule('new_words', null, { from: 'topics' }, { from: 'topics' }); delete answers.topic; delete answers.topics; delete answers.new_words_expected; },
        html: `<h3 class="hb-q">What is today's lesson about?</h3><p class="hb-sub">Tap everything that applies, then Next.</p><div class="hb-btns">
          ${MENU.map((t, i) => btn(t, (i === 0 && p.last_words) ? ('last time: ' + p.last_words) : (t === 'Review listening' ? 'Amal speaks, Medi listens and translates' : (t === 'Review conversation' ? 'back-and-forth practice on the last lessons' : '')), null, P + 't' + i)).join('')}</div>
          <div id="${P}typebox" hidden><input class="hb-input" id="${P}topic" placeholder="Which topic?" aria-label="Other topic"></div>${btn('Next', '', 'primary', P + 'tnext')}`,
        wire() {
          const sel = new Set(), nb = document.getElementById(P + 'tnext'); nb.hidden = true;
          MENU.forEach((t, i) => { const b = document.getElementById(P + 't' + i); b.onclick = () => { if (sel.has(t)) sel.delete(t); else sel.add(t); b.setAttribute('aria-pressed', String(sel.has(t))); b.classList.toggle('primary', sel.has(t));
            if (t === 'Other topic') { document.getElementById(P + 'typebox').hidden = !sel.has(t); } nb.hidden = !sel.size; }; });
          nb.onclick = () => { const typed = document.getElementById(P + 'topic').value.trim(); const topics = [...sel].filter(t => t !== 'Other topic').concat(typed ? [typed] : []); if (!topics.length) return;
            answers.topic = topics.join(' + '); answers.topics = topics; const expectNew = topics.some(t => /^New /.test(t)); answers.new_words_expected = expectNew;
            rule('topic', null, { topic: answers.topic, topics, typed: typed || null, source: 'menu' }); rule('new_words', null, { expected: expectNew, from: 'topics' }); save(); next(); };
        } });
      const rep = p.repeat || [], menu = p.menu || null, GROUPS = [['verbs', 'Verbs'], ['nouns', 'Nouns'], ['adjectives', 'Adjectives'], ['sayings', 'Sayings']];
      const pool = menu ? Object.fromEntries(GROUPS.map(([g]) => [g, (menu[g] || [])])) : { nouns: rep.slice(0, 3) };
      const byKey = {}; Object.values(pool).flat().forEach(w => { byKey[w.key] = w; });
      S.push({ key: 'repeat', title: 'Words for today', answered: () => Array.isArray(answers.repeat_sent), said: () => (answers.repeat_sent || []).length ? (answers.repeat_sent || []).map(k => (byKey[k] || {}).arabizi || k).join(', ') : 'none', prog: `2 of ${total}`,
        undo() { const ks = answers.repeat_sent || []; ks.forEach(k => unrule('repeat', k, { arabizi: (byKey[k] || {}).arabizi })); if (!ks.length) unrule('repeat', null, { none: true }, { none: true }); delete answers.repeat_sent; },
        html: `<h3 class="hb-q">Words for today</h3><p class="hb-sub">Tap the ones you want to use today, then Next.</p><div id="${P}groups"></div>${btn('Next', '', 'primary', P + 'rgo')}`,
        wire() {
          const sel = new Set(answers.repeat || []);
          document.getElementById(P + 'groups').innerHTML = GROUPS.map(([g, label]) => { const all = pool[g] || []; if (!all.length) return '';
            return `<p class="hb-prog" style="margin-top:10px">${label} (${all.length})</p><div class="hb-btns">${all.map(w => `<button type="button" class="hb-ans${sel.has(w.key) ? ' primary' : ''}" data-k="${esc(w.key)}"><b>${esc(w.arabizi)}</b><small>${esc(w.arabic || '')} · ${esc(w.english || '')}${w.why ? ' · ' + esc(w.why) : ''}</small></button>`).join('')}</div>`; }).join('');
          document.querySelectorAll('#' + P + 'groups [data-k]').forEach(b => b.onclick = () => { const k = b.dataset.k; if (sel.has(k)) sel.delete(k); else sel.add(k); b.classList.toggle('primary', sel.has(k)); answers.repeat = [...sel]; LS(AK, answers); });
          document.getElementById(P + 'rgo').onclick = () => { answers.repeat = [...sel]; answers.repeat_sent = [...sel]; [...sel].forEach(k => rule('repeat', k, { picked: true, arabizi: (byKey[k] || {}).arabizi })); if (!sel.size) rule('repeat', null, { none: true }); save(); next(); };
        } });
      (p.sentences || []).forEach((s, i) => {
        const n = p.sentences.length, pl = { arabizi: s.arabizi, arabic: s.arabic, english: s.english, keys: (s.words || []).map(w => w.key) };
        S.push({ key: 's' + i, title: s.arabizi, answered: () => !!(answers.sentences || {})[i], said: () => ({ keep: 'Keep', drop: 'Drop', edit: 'Your version' })[(answers.sentences || {})[i]] || '', prog: `${3 + i} of ${total}`,
          undo() { const was = answers.sentences[i]; unrule(was, null, { arabizi: s.arabizi }, { arabizi: s.arabizi }); if (was === 'drop') (s.words || []).forEach(w => unrule('drop', w.key, { sentence: s.arabizi }, { sentence: s.arabizi })); delete answers.sentences[i]; },
          html: `<h3 class="hb-q">Keep this sentence?</h3><p class="hb-sub">One of ${n} suggestions for today. Keep, drop, or edit it.</p>
            <div class="hb-moment"><div class="hb-big">${esc(s.arabizi)}</div><div class="hb-ar" dir="auto">${esc(s.arabic || '')}</div><div class="hb-en">${esc(s.english || '')}</div><div class="hb-why">words: ${(s.words || []).map(w => esc(w.arabizi)).join(', ')}</div></div>
            <div class="hb-btns">${btn('Keep', '', 'primary', P + 'k' + i)}${btn('Drop', '', 'drop', P + 'd' + i)}${btn('Edit', '', null, P + 'e' + i)}</div>
            <div id="${P}ebox${i}" hidden><input class="hb-input" id="${P}ev${i}" value="${esc(s.arabizi)}" aria-label="Your version">${btn('Save my version', '', 'primary', P + 'eg' + i)}</div>`,
          wire() {
            const set = v => { (answers.sentences = answers.sentences || {})[i] = v; };
            document.getElementById(P + 'k' + i).onclick = () => { set('keep'); rule('keep', null, pl); save(); next(); };
            document.getElementById(P + 'd' + i).onclick = () => { set('drop'); rule('drop', null, pl); (s.words || []).forEach(w => rule('drop', w.key, { sentence: s.arabizi })); save(); next(); };
            document.getElementById(P + 'e' + i).onclick = () => { document.getElementById(P + 'ebox' + i).hidden = false; };
            document.getElementById(P + 'eg' + i).onclick = () => { const v = document.getElementById(P + 'ev' + i).value.trim(); if (!v) return; set('edit'); rule('edit', null, { ...pl, edited: v }); save(); next(); };
          } });
      });
      return S;
    }
    $quit.onclick = e => { e.preventDefault(); finish(); };
    (async () => {
      let rows = []; try { rows = await (await api('GET', 'amal_links?select=*&token=eq.' + encodeURIComponent(TOKEN))).json(); } catch (e) {}
      link = Array.isArray(rows) ? rows[0] : null;
      if (!link) { $root.innerHTML = '<h3 class="hb-q">This list is closed.</h3><p class="hb-sub">Ask Medi for a fresh link.</p>'; $prog.textContent = ''; return; }
      if (new Date(link.expires_at) < new Date()) { $root.innerHTML = '<h3 class="hb-q">This list has closed.</h3><p class="hb-sub">Links work for 7 days.</p>'; $prog.textContent = ''; return; }
      const local = LS(AK), queued = (LS(QK) || []).length;   // AM-17: the server copy wins once nothing waits to be sent
      answers = Object.assign({}, link.answers || {}, queued && local ? local : {});
      if (answers.repeat && !answers.repeat_sent && (answers.step || 0) > 1) answers.repeat_sent = answers.repeat;   // lists answered before 2026-10-02
      screens = build(link.payload || {});
      if (link.done_at || answers.done) { answers.done = true; LS(AK, answers); showDone(); flush(); return; }
      const first = screens.findIndex(s => !isDone(s)); show(first < 0 ? screens.length : first); flush(); save();
    })();
  }
  root.AneesPlanTask = { mount };
})(typeof window !== 'undefined' ? window : globalThis);
