/* "After the lesson" inside the Tutor hub (Medi 2026-10-01: nothing Amal does leaves the Tutor page). The same questions,
   the same saving and the same resume as amal/after.html (same localStorage keys, same Supabase rows: amal_rules source
   'after', amal_links answers / done_at, homework_items, homework_answers), drawn as hub moment cards with an audio bar.
   AneesAfterTask.mount(el, item, {onChange}) - item = the tutor.json entry (token, lesson_date, title). */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const timers = {};
  const KINDS = { 'Right': 'right', 'Wrong': 'wrong', 'Wrong word': 'wrong', 'Wrong grammar': 'wrong', 'Not Medi': 'not_medi', 'Skip': 'skip', 'Medi, right': 'right', 'Medi, wrong': 'wrong', 'Yes, a word': 'alias', 'No': 'no' };
  const MISS = { 'Wrong word': 'word', 'Wrong grammar': 'grammar' };

  function mount(el, item, opt) {
    opt = opt || {};
    const TOKEN = item.token;
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H, ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });
    const QK = 'anees-amal-q-' + TOKEN, AK = 'anees-amal-a-' + TOKEN;
    let link = null, answers = {}, step = 0, screens = [], flushing = false, pendingDone = false;
    el.innerHTML = '<div class="hb-task"><p class="hb-prog" data-prog></p><div data-root><p class="hb-sub">Loading…</p></div><p class="hb-foot"><a href="#" data-quit>Stop here</a> · saved as you tap</p></div>';
    const $root = el.querySelector('[data-root]'), $prog = el.querySelector('[data-prog]'), $quit = el.querySelector('[data-quit]');

    async function flush() {
      if (flushing) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try {
          let r;
          if (job.kind === 'rule') r = await api('POST', 'amal_rules', job.body, { Prefer: 'return=minimal' });
          else if (job.kind === 'item') r = await api('PATCH', 'homework_items?id=eq.' + encodeURIComponent(job.id_item), job.body, { Prefer: 'return=minimal' });
          else if (job.kind === 'item_new') r = await api('POST', 'homework_items', job.body, { Prefer: 'return=minimal' });
          else if (job.kind === 'verdict') r = await api('PATCH', 'homework_answers?id=eq.' + encodeURIComponent(job.id_answer), job.body, { Prefer: 'return=minimal' });
          else r = await api('PATCH', 'amal_links?token=eq.' + encodeURIComponent(TOKEN), job.body, { Prefer: 'return=minimal' });
          ok = r.ok || r.status === 409;
        } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2000)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false;
      if (pendingDone && !(LS(QK) || []).length) { pendingDone = false; showDone(); }
    }
    clearInterval(timers[TOKEN]); timers[TOKEN] = setInterval(() => { if ((LS(QK) || []).length) flush(); }, 3000);
    window.addEventListener('online', flush);
    const push = (kind, body, extra) => { const q = LS(QK) || []; q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), kind, body, ...(extra || {}) }); LS(QK, q); flush(); };
    const rule = (kind, word_key, payload) => push('rule', { token: TOKEN, source: 'after', lesson_date: link.lesson_date, kind, word_key, payload });
    function save(done) { answers.updated = new Date().toISOString(); LS(AK, answers); const body = { answers }; if (done) body.done_at = answers.updated; if (!link.opened_at) body.opened_at = answers.updated; push('link', body); }
    function report() { if (opt.onChange) opt.onChange({ done: Math.min(step, screens.length), total: screens.length, finished: !!answers.done }); }
    function show(i) {
      step = i; answers.step = i; LS(AK, answers); root.AneesClip && AneesClip.stopAll();
      const s = screens[i]; if (!s) { finish(); return; }
      $prog.textContent = s.prog; $root.innerHTML = s.html; s.wire && s.wire(); report();
      const top = el.getBoundingClientRect().top; if (top < 0) el.scrollIntoView({ block: 'start' });
    }
    const next = () => show(step + 1);
    function showDone() { $prog.textContent = 'Done'; $root.innerHTML = '<h3 class="hb-q">All saved. Shukran!</h3><p class="hb-sub">The app suggested; you decided.</p>'; $quit.parentElement.hidden = true; report(); }
    function finish() {
      answers.done = true; save(true); $prog.textContent = 'Saving…';
      $root.innerHTML = '<h3 class="hb-q">Saving your answers…</h3><p class="hb-sub">If you are offline this finishes by itself when you are back online.</p>'; $quit.parentElement.hidden = true;
      if (!(LS(QK) || []).length) showDone(); else { pendingDone = true; flush(); }
    }
    function playerFor(q) {
      const lesson = ANEES.pages + 'lessons/' + link.lesson_date + '/audio/lesson.mp3';
      const b = AneesClip.bar({ src: q.clip ? ANEES.pages + 'lessons/' + q.clip : lesson, start: q.clip ? 0 : Math.max(0, q.t - 3), end: q.clip ? null : q.t + 12,
        fallback: q.t != null ? { src: lesson, start: Math.max(0, q.t - 3), end: q.t + 12 } : null });
      return b;
    }
    const btn = (id, label, cls) => `<button type="button" class="hb-ans${cls ? ' ' + cls : ''}" id="${id}">${label}</button>`;
    function build(p) {
      const S = [], Q = p.questions || [], HW = p.homework || [], PR = p.prompts || [], PEND = p.pending || [];
      const total = Q.length + HW.length + PEND.length + PR.length + (PR.length ? 1 : 0);
      Q.forEach((q, i) => {
        const id = `${TOKEN.slice(0, 6)}q${i}`;
        S.push({ prog: `${i + 1} of ${total}`, html: `<h3 class="hb-q">${esc(q.ask)}</h3><p class="hb-sub">${esc(q.why)}. Your answer changes how the app scores this word.</p>
          <div class="hb-moment">${q.arabizi ? `<div class="hb-big">${esc(q.arabizi)}</div>` : ''}<div class="hb-ar" dir="auto">${esc(q.arabic || '')}</div><div class="hb-en">${esc(q.english || '')}</div><div data-player></div></div>
          ${q.typed ? `<input class="hb-input" id="${id}t" placeholder="Your spelling (optional)" aria-label="Your spelling">` : ''}
          <div class="hb-btns">${q.buttons.slice(0, 3).map((b, j) => btn(`${id}b${j}`, esc(b))).join('')}</div><a href="#" class="hb-skip" id="${id}s">Skip this one</a>`,
          wire() {
            $root.querySelector('[data-player]').appendChild(playerFor(q));
            const answer = label => {
              const kind = KINDS[label] || 'skip', typed = document.getElementById(id + 't');
              const pl = { t: q.t, ask: q.ask, label, clip: q.clip, arabic: q.arabic, arabizi: q.arabizi };
              if (typed && typed.value.trim()) pl.alias = typed.value.trim(); if (q.audit_uid) pl.audit_uid = q.audit_uid; if (MISS[label]) pl.miss_kind = MISS[label]; if (q.who) pl.who = true;
              (answers.q = answers.q || {})[i] = label; rule(kind, q.word_key, pl); save(); next();
            };
            q.buttons.slice(0, 3).forEach((b, j) => { document.getElementById(id + 'b' + j).onclick = () => answer(b); });
            document.getElementById(id + 's').onclick = e => { e.preventDefault(); answer('Skip'); };
          } });
      });
      HW.forEach((h, i) => {
        const id = `${TOKEN.slice(0, 6)}h${i}`;
        S.push({ prog: `${Q.length + i + 1} of ${total}`, html: `<h3 class="hb-q">Homework suggestion ${i + 1} of ${HW.length}</h3><p class="hb-sub">The app suggests this for Medi (${esc(h.kind === 'say' ? 'a sentence to say' : h.kind === 'use' ? 'a word to use' : 'a mini-dialogue')}). Keep, drop or edit it.</p>
          <div class="hb-moment"><div class="hb-big">${esc(h.arabizi)}</div><div class="hb-ar" dir="auto">${esc(h.arabic || '')}</div><div class="hb-en">${esc(h.english || '')}</div>${h.note ? `<div class="hb-why">${esc(h.note)}</div>` : ''}</div>
          <div class="hb-btns">${btn(id + 'k', 'Keep', 'primary')}${btn(id + 'd', 'Drop', 'drop')}${btn(id + 'e', 'Edit')}</div>
          <div id="${id}box" hidden><input class="hb-input" id="${id}v" value="${esc(h.arabizi)}" aria-label="Your version">${btn(id + 'g', 'Save my version', 'primary')}</div>`,
          wire() {
            const pl = { arabizi: h.arabizi, arabic: h.arabic, english: h.english, keys: h.keys, kind: h.kind };
            document.getElementById(id + 'k').onclick = () => { (answers.hw = answers.hw || {})[i] = 'keep'; rule('keep', null, { ...pl, source: 'homework' }); save(); next(); };
            document.getElementById(id + 'd').onclick = () => { (answers.hw = answers.hw || {})[i] = 'drop'; rule('drop', null, { ...pl, source: 'homework' }); (h.keys || []).forEach(k => rule('drop', k, { homework: h.arabizi })); save(); next(); };
            document.getElementById(id + 'e').onclick = () => { document.getElementById(id + 'box').hidden = false; };
            document.getElementById(id + 'g').onclick = () => { const v = document.getElementById(id + 'v').value.trim(); if (!v) return; (answers.hw = answers.hw || {})[i] = 'edit'; rule('edit', null, { ...pl, edited: v, source: 'homework' }); save(); next(); };
          } });
      });
      PEND.forEach((a, i) => {
        const id = `${TOKEN.slice(0, 6)}v${i}`, it = a.homework_items || {}, g = a.grade || {};
        const en = (it.status === 'edit' || it.status === 'amal') && it.edited_english ? it.edited_english : (it.english || '');
        const gtxt = g.verdict ? `The app said: <b>${esc(g.verdict === 'right' ? 'right' : g.verdict === 'close' ? 'close' : g.verdict === 'wrong' ? 'not right' : 'ungraded')}</b>${(g.notes || []).length ? ' · ' + esc((g.notes || []).map(n => n.say).join(' · ')) : ''}${g.fixed && g.verdict !== 'right' ? ' → ' + esc(g.fixed) : ''}` : 'The app has not graded this one.';
        S.push({ prog: `${Q.length + HW.length + i + 1} of ${total}`, html: `<h3 class="hb-q">Medi typed this answer. Is it right?</h3><p class="hb-sub">You have the final word; the app only suggested. Your answer scores the words.</p>
          <div class="hb-moment"><div class="hb-en">${esc(en)}</div><div class="hb-big">${esc(a.answer)}</div><div class="hb-why">${gtxt}</div></div>
          <div class="hb-btns">${btn(id + 'r', 'Correct', 'primary')}${btn(id + 'f', 'Needs a fix')}${btn(id + 's', 'Skip')}</div>
          <div id="${id}box" hidden><input class="hb-input" id="${id}v" value="${esc(g.fixed && g.verdict !== 'right' ? g.fixed : a.answer)}" aria-label="Your fix">${btn(id + 'g', 'Save my fix', 'primary')}</div>`,
          wire() {
            const done = (verdict, fix) => { (answers.v = answers.v || {})[a.id] = verdict; const body = { amal_verdict: verdict, amal_at: new Date().toISOString() }; if (fix) body.amal_fix = fix; push('verdict', body, { id_answer: a.id }); save(); next(); };
            document.getElementById(id + 'r').onclick = () => done('right'); document.getElementById(id + 's').onclick = () => done('skip');
            document.getElementById(id + 'f').onclick = () => { document.getElementById(id + 'box').hidden = false; };
            document.getElementById(id + 'g').onclick = () => { const v = document.getElementById(id + 'v').value.trim(); if (!v) return; done('fix', v); };
          } });
      });
      PR.forEach((it, i) => {
        const id = `${TOKEN.slice(0, 6)}p${i}`;
        S.push({ prog: `${Q.length + HW.length + PEND.length + i + 1} of ${total}`, html: `<h3 class="hb-q">Homework line ${i + 1} of ${PR.length}</h3><p class="hb-sub">The app suggests this English line for Medi to say in Arabic (it practises ${esc((it.keys || []).length)} of his words). Keep, drop or edit it.</p>
          <div class="hb-moment"><div class="hb-big">${esc(it.english)}</div></div>
          <div class="hb-btns">${btn(id + 'k', 'Keep', 'primary')}${btn(id + 'd', 'Drop', 'drop')}${btn(id + 'e', 'Edit')}</div>
          <div id="${id}box" hidden><input class="hb-input" id="${id}v" value="${esc(it.english)}" aria-label="Your line">${btn(id + 'g', 'Save my version', 'primary')}</div>`,
          wire() {
            const decide = (status, edited) => { (answers.pr = answers.pr || {})[it.id] = status; const body = { status, decided_at: new Date().toISOString() }; if (edited) body.edited_english = edited;
              push('item', body, { id_item: it.id }); rule(status, null, { english: it.english, edited, keys: it.keys, source: 'homework_prompt' }); save(); next(); };
            document.getElementById(id + 'k').onclick = () => decide('keep'); document.getElementById(id + 'd').onclick = () => decide('drop');
            document.getElementById(id + 'e').onclick = () => { document.getElementById(id + 'box').hidden = false; };
            document.getElementById(id + 'g').onclick = () => { const v = document.getElementById(id + 'v').value.trim(); if (!v) return; decide('edit', v); };
          } });
      });
      if (PR.length) {
        const id = `${TOKEN.slice(0, 6)}own`;
        S.push({ prog: `${total} of ${total}`, html: `<h3 class="hb-q">Your own lines?</h3><p class="hb-sub">Type any English line you want Medi to say in Arabic, one at a time, as many as you like.</p>
          <input class="hb-input" id="${id}v" placeholder="Did you call your brother yesterday?" aria-label="Your line"><div class="hb-btns">${btn(id + 'a', 'Add this line')}${btn(id + 'n', 'No more lines, finish', 'primary')}</div><p class="hb-sub" id="${id}c"></p>`,
          wire() {
            let n = 0; const inp = document.getElementById(id + 'v');
            document.getElementById(id + 'a').onclick = () => { const v = inp.value.trim(); if (!v) return; n++;
              push('item_new', { lesson_date: link.lesson_date, token: TOKEN, n: 100 + n, english: v, edited_english: v, status: 'amal', keys: [] });
              rule('keep', null, { english: v, source: 'homework_prompt', own: true }); inp.value = ''; document.getElementById(id + 'c').textContent = `${n} line${n === 1 ? '' : 's'} added. Add another or finish.`; save(); };
            document.getElementById(id + 'n').onclick = () => next();
          } });
      }
      return S;
    }
    $quit.onclick = e => { e.preventDefault(); finish(); };
    (async () => {
      let rows = []; try { rows = await (await api('GET', 'amal_links?select=*&token=eq.' + encodeURIComponent(TOKEN))).json(); } catch (e) {}
      link = Array.isArray(rows) ? rows[0] : null;
      if (!link) { $root.innerHTML = '<h3 class="hb-q">This list is closed.</h3><p class="hb-sub">Nothing to do here any more.</p>'; $prog.textContent = ''; return; }
      if (new Date(link.expires_at) < new Date()) { $root.innerHTML = '<h3 class="hb-q">This list has closed.</h3><p class="hb-sub">Lists stay open for 7 days.</p>'; $prog.textContent = ''; return; }
      if (link.done_at) { showDone(); return; }
      const payload = Object.assign({}, link.payload || {});
      try {
        const pend = await (await api('GET', 'homework_answers?select=id,answer,grade,item_id,lesson_date,homework_items(english,edited_english,status,n,lesson_date)&amal_verdict=is.null&lesson_date=lte.' + encodeURIComponent(link.lesson_date) + '&order=ts.asc&limit=20')).json();
        payload.pending = Array.isArray(pend) ? pend.filter(a => !((LS(AK) || {}).v || {})[a.id]) : [];
      } catch (e) { payload.pending = []; }
      answers = Object.assign({}, link.answers || {}, LS(AK) || {}); screens = build(payload);
      if (answers.done) { finish(); return; }
      show(typeof answers.step === 'number' ? Math.min(answers.step, screens.length) : 0); flush(); save();
    })();
  }
  root.AneesAfterTask = { mount };
})(window);
