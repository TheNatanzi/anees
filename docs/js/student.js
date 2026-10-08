/* STUDENT tab (Medi 2026-10-05: "create a new tab 'student' below tutor" - "Homework and the cards she assigns me for the
   next lessons"). Medi's side of what Amal does on the Tutor page: (a) his homework - to do / done, typed answers in Arabizi
   or Arabic letters (Q4), the AI's first check at once (right / close / wrong + reason, Q1), then "waiting for Amal" until her
   confirm or overrule, which is the word that counts; (b) the card sets she assigned for a lesson date, each a link into
   Flashcards on that set with N cards / M done; (c) the shaky words of the last 2 lessons (Q3). The homework number here and
   on Progress is Amal's verdicts only (Q5); lesson Words % / Grammar % are untouched.
   Live rows from Supabase (migration 023) with docs/data/homework.json (hourly mirror) as the offline fallback. Rule L1:
   re-read when the tab comes back, never while an answer is being typed. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'r' + Date.now().toString(36) + Math.random().toString(36).slice(2));
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  const H = window.AneesHomework, SAY = { right: 'Right', close: 'Close', wrong: 'Wrong' };
  const HD = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json' };
  const QK = 'anees-student-q';
  let D = { tasks: [], replies: [], verdicts: [], log: [], shaky: null, live: false }, typing = false, busyIds = new Set(), msg = {};

  async function rest(path) { const r = await fetch(ANEES.url + '/rest/v1/' + path, { headers: HD, cache: 'no-store' }); if (!r.ok) throw new Error(r.status); return r.json(); }
  async function page(path) { const out = []; for (let off = 0; ; off += 1000) { const p = await rest(path + '&limit=1000&offset=' + off); out.push(...p); if (p.length < 1000) return out; } }
  async function load() {
    const J = u => fetch(u, { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null);
    const mirror = await J('data/homework.json'), shaky = await J('data/shaky-words.json');
    try {
      const [T, R, V, L, A] = await Promise.all([page('homework_tasks?select=*&order=created_at.asc'), page('homework_replies?select=*&order=created_at.asc'),
        page('homework_verdicts?select=*&order=created_at.asc'), page('card_results?select=word_key,result,ts,subject,undone_at&order=ts.asc'), page('card_attention?select=*&order=created_at.asc').catch(() => [])]);
      D = { tasks: T, replies: R, verdicts: V, log: L, attention: A, shaky, live: true, built: mirror && mirror.built };
    } catch (e) {
      D = { tasks: (mirror && mirror.tasks) || [], replies: (mirror && mirror.replies) || [], verdicts: (mirror && mirror.verdicts) || [], log: [], shaky, live: false, built: mirror && mirror.built };
    }
    for (const j of LS(QK) || []) if (!D.replies.some(r => r.id === j.body.id)) D.replies.push(j.body);   // my answers still waiting to be sent
    $('#ab-source').textContent = D.live ? 'Live · ' + new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : 'Offline copy' + (D.built ? ' · built ' + pretty(D.built) : '');
    route();
  }

  // ---- answering ----------------------------------------------------------------------------------------------------
  async function post(table, body) { return fetch(ANEES.url + '/rest/v1/' + table, { method: 'POST', headers: { ...HD, Prefer: 'return=minimal' }, body: JSON.stringify(body) }); }
  async function check(replyId) {
    try {
      const r = await fetch(ANEES.url + '/functions/v1/check-homework', { method: 'POST', headers: HD, body: JSON.stringify({ reply_id: replyId }) });
      const j = await r.json().catch(() => ({}));
      if (r.ok && j.ai) { const rep = D.replies.find(x => x.id === replyId); if (rep) { rep.ai = j.ai; rep.ai_at = new Date().toISOString(); } return true; }
      msg[replyId] = 'The AI check did not run (' + (j.error || r.status) + '). Your teacher will still see your answer.'; return false;
    } catch (e) { msg[replyId] = 'The AI check did not run (offline). Your teacher will still see your answer.'; return false; }
  }
  async function answer(task, text) {
    const t = String(text || '').trim(); if (!t) return;
    const body = { id: uuid(), task_id: task.id, answer: t.slice(0, 2000), script: H.scriptOf(t), created_at: new Date().toISOString() };
    D.replies.push(body); busyIds.add(task.id); typing = false; render();
    let sent = false;
    try { const r = await post('homework_replies', body); sent = r.ok || r.status === 409; } catch (e) { sent = false; }
    if (!sent) { const q = LS(QK) || []; q.push({ id: body.id, body }); LS(QK, q); msg[body.id] = 'Saved on this phone, will be sent when online. Your teacher sees it then.'; }
    else await check(body.id);
    busyIds.delete(task.id); render();
  }
  async function flush() {
    const q = LS(QK) || []; if (!q.length) return;
    for (const j of q) { try { const r = await post('homework_replies', j.body); if (r.ok || r.status === 409) { LS(QK, (LS(QK) || []).filter(x => x.id !== j.id)); delete msg[j.body.id]; await check(j.body.id); } } catch (e) {} }
    render();
  }

  // ---- views --------------------------------------------------------------------------------------------------------
  function kindOf(t) { return t.kind === 'translate' ? 'Translate · ' + (H.DIRECTIONS[t.direction] || '') : t.kind === 'create' ? 'Make a sentence with these words' : 'Answer the question'; }
  function head(t) {
    return `<p class="st-kind">${esc(kindOf(t))}${t.lesson_date ? ' · for the lesson on ' + esc(pretty(t.lesson_date)) : ''} · assigned ${esc(pretty(t.created_at))}</p>
      ${t.kind === 'create' ? `<div class="st-chips">${(t.words || []).map(w => `<span class="hb-chip" dir="auto">${esc(w)}</span>`).join('')}</div>` : ''}
      <p class="st-prompt" dir="auto">${esc(t.prompt)}</p>${t.context ? `<p class="st-ctx" dir="auto">${esc(t.context)}</p>` : ''}`;
  }
  const verdictHtml = (v, who) => v ? `<span class="st-v ${v}">${who}: ${SAY[v]}</span>` : '';
  function todoCard(t, s) {
    const r = s.reply, busy = busyIds.has(t.id);
    if (!r) return `<div class="st-task" data-task="${esc(t.id)}">${head(t)}
      <textarea class="hb-input" data-answer rows="2" dir="auto" placeholder="${t.direction === 'ar_en' ? 'Your English' : 'Your answer in Arabizi (6=ط 7=ح 3=ع 2=ء 5=خ) or Arabic letters'}" ${busy ? 'disabled' : ''}></textarea>
      <button type="button" class="hb-ans primary st-go" data-send ${busy ? 'disabled' : ''}>${busy ? 'Checking…' : 'Check my answer'}</button></div>`;
    return `<div class="st-task">${head(t)}<p class="st-ans" dir="auto">You: ${esc(r.answer)}</p>
      ${s.ai ? `<p>${verdictHtml(s.ai.verdict, 'AI')} <span class="st-why">${esc(s.ai.reason || '')}${s.ai.fixed && s.ai.fixed !== r.answer ? ' · <span dir="auto">' + esc(s.ai.fixed) + '</span>' : ''}</span></p>` : (busy ? '<p class="st-wait">AI check running…</p>' : `<p class="st-wait">${esc(msg[r.id] || (r.ai && r.ai.reason) || 'AI check pending')}</p>`)}
      <p class="st-wait">Waiting for your teacher - that word is the one that counts.</p></div>`;
  }
  function doneCard(t, s) {
    const v = s.verdict;
    return `<div class="st-task">${head(t)}<p class="st-ans" dir="auto">You: ${esc(s.reply.answer)}</p>
      <p>${verdictHtml(v.verdict, 'Teacher')} ${s.ai ? `<span class="st-wait">AI said ${SAY[s.ai.verdict]}${v.agrees === false ? ' - she overruled it' : ''}</span>` : ''}</p>
      ${v.fix ? `<p class="st-why" dir="auto">Say: <b>${esc(v.fix)}</b></p>` : ''}${v.note ? `<p class="st-why">${esc(v.note)}</p>` : ''}${s.ai && s.ai.reason && v.agrees !== false ? `<p class="st-why">${esc(s.ai.reason)}</p>` : ''}
      <p class="st-wait">${esc(pretty(v.created_at))}</p></div>`;
  }
  function states() { return H.effective(D.tasks).map(t => ({ t, s: t.kind === 'cards' ? null : H.taskState(t, D.replies, D.verdicts) })); }
  function scoreHtml() {
    const sc = H.score(D.tasks, D.replies, D.verdicts);
    const tile = (l, v, sub) => `<div class="vp-card"><div class="vp-card-label"><span>${l}</span></div><div class="vp-card-value"><span class="vp-num">${v}</span></div><div class="vp-card-sub">${sub}</div></div>`;
    return tile('Homework', sc.pct === null ? '—' : sc.pct + '%', sc.done ? `${sc.done} checked by your teacher · right 1, close ½` : 'nothing checked by your teacher yet - only that verdict counts')
      + tile('To do', sc.todo, 'not answered yet') + tile('Waiting', sc.waiting + sc.checking, 'answered, waiting for your teacher') + tile('Overruled', sc.overruled, sc.done ? `of ${sc.done} the AI check was corrected by your teacher` : '');
  }
  function setTab(tab) { document.querySelectorAll('.hb-tab').forEach(a => a.setAttribute('aria-selected', String(a.dataset.tab === tab))); }
  function cardsView() {
    setTab('cards');
    const C = H.effective(D.tasks).filter(t => t.kind === 'cards').sort((a, b) => String(a.lesson_date).localeCompare(String(b.lesson_date)));
    if (!C.length) { $('#st-view').innerHTML = '<p class="hb-empty">No card set assigned for a lesson yet.</p>'; return; }
    const today = new Date().toISOString().slice(0, 10);
    $('#st-view').innerHTML = `<p class="hb-sub">Card sets your teacher wants done before a lesson. Tap one to open it on Flashcards; every answer counts there as usual.</p><div class="hb-list">${C.map(t => { const done = H.cardsDone(t, D.log), n = t.n_cards || 0, past = t.lesson_date && t.lesson_date < today;
      return `<a class="hb-row" href="cards.html?tile=${encodeURIComponent(t.set_ref)}" style="display:block;text-decoration:none"><p class="hb-row-t">For ${esc(pretty(t.lesson_date))}: ${esc(t.set_title)}</p><p class="hb-row-s">${n} cards · ${done} done${done >= n && n ? ' · all done' : ''}${past ? ' · lesson passed' : ''}</p><div class="hb-bar" aria-hidden="true"><i style="width:${n ? Math.min(100, Math.round(100 * done / n)) : 0}%"></i></div></a>`; }).join('')}</div>`;
  }
  function shakyView() {
    setTab('shaky');
    const S = D.shaky, open = S ? H.shakyCards(S, D.log) : [];
    if (!S) { $('#st-view').innerHTML = '<p class="hb-empty">The shaky-words list has not been built yet (it comes from the hourly job).</p>'; return; }
    $('#st-view').innerHTML = `<p class="hb-sub">Words you got wrong, partly wrong, or had to ask for in the last 2 lessons (${(S.lessons || []).map(pretty).join(' and ')}). A word leaves this list after two right answers on Flashcards. <a href="cards.html?tile=shaky">Open them as cards →</a></p>
      ${open.length ? `<ul class="hb-done">${open.map(w => `<li><b>${esc(w.arabizi || w.arabic)}</b>${w.arabizi && w.arabic ? ` <span lang="ar">${esc(w.arabic)}</span>` : ''} <span>· ${esc(w.english || '')} · ${w.kind === 'asked' ? 'you asked for it' : w.kind === 'partial' ? 'partly wrong' : 'wrong'} · ${esc(pretty(w.date))}${w.right_since ? ' · 1 right since' : ''}</span></li>`).join('')}</ul>` : '<p class="hb-empty">Nothing shaky left from the last 2 lessons.</p>'}`;
  }
  // Medi 2026-10-05 "get rid of cards for lesson and have Todo be for all assignments": card sets for a lesson are To do rows too
  function openCards(t) { return H.effective(D.tasks).filter(x => x.kind === 'cards' && !(x.n_cards && H.cardsDone(x, D.log) >= x.n_cards)); }
  function cardsCard(t) {
    const done = H.cardsDone(t, D.log), n = t.n_cards || 0, today = new Date().toISOString().slice(0, 10), past = t.lesson_date && t.lesson_date < today;
    return `<a class="st-task st-cards" href="cards.html?tile=${encodeURIComponent(t.set_ref)}" style="display:block;text-decoration:none;color:inherit"><p class="st-kind">Cards for the lesson on ${esc(pretty(t.lesson_date))} · assigned ${esc(pretty(t.created_at))}</p>
      <p class="st-prompt">${esc(t.set_title)}</p><p class="st-wait">${n} cards · ${done} done${done >= n && n ? ' · all done' : ''}${past ? ' · lesson passed' : ''} · tap to open on Flashcards</p>
      <div class="hb-bar" aria-hidden="true"><i style="width:${n ? Math.min(100, Math.round(100 * done / n)) : 0}%"></i></div></a>`;
  }
  // Medi 2026-10-06: the questions he sent from a flashcard (the attention button) and her replies
  function attn() { return (window.AneesAttentionTask || { view: () => ({ all: [], open: [], answered: [] }) }).view(D.attention || []); }
  const attnCard = n => `<div class="st-task st-attn"><p class="st-kind">Your question from a flashcard · ${esc(pretty(n.created_at))}</p><p class="st-prompt" dir="auto">${esc(n.arabizi || n.arabic || '')}${n.english ? ` <span class="st-ctx" style="display:inline">· ${esc(n.english)}</span>` : ''}</p><p class="st-ans" dir="auto">You: ${esc(n.text)}</p>
    ${n.replies.length ? n.replies.map(r => `<p class="st-why" dir="auto"><b>Teacher:</b> ${esc(r.text)} <span class="st-wait">${esc(pretty(r.created_at))}</span></p>`).join('') : '<p class="st-wait">Waiting for your teacher.</p>'}</div>`;
  function todoView() {
    setTab('todo');
    const L = states().filter(x => x.s && x.s.state !== 'done'), C = openCards(), Q = attn().open;
    if (!L.length && !C.length && !Q.length) { $('#st-view').innerHTML = '<p class="hb-empty">No homework waiting. It is assigned on the Tutor page.</p>'; return; }
    const order = { todo: 0, checking: 1, waiting: 2 };
    $('#st-view').innerHTML = C.sort((a, b) => String(a.lesson_date).localeCompare(String(b.lesson_date))).map(cardsCard).join('')
      + L.sort((a, b) => order[a.s.state] - order[b.s.state] || String(b.t.created_at).localeCompare(String(a.t.created_at))).map(x => todoCard(x.t, x.s)).join('')
      + Q.slice().reverse().map(attnCard).join('');
    $('#st-view').querySelectorAll('[data-task]').forEach(box => {
      const ta = box.querySelector('[data-answer]'), go = box.querySelector('[data-send]'), t = D.tasks.find(x => x.id === box.dataset.task);
      ta.oninput = () => { typing = !!ta.value.trim(); };
      go.onclick = () => answer(t, ta.value);
      ta.onkeydown = e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) answer(t, ta.value); };
    });
  }
  function doneView() {
    setTab('done');
    const L = states().filter(x => x.s && x.s.state === 'done').sort((a, b) => String(b.s.verdict.created_at).localeCompare(String(a.s.verdict.created_at)));
    const Qa = attn().answered.slice().reverse();
    $('#st-view').innerHTML = (L.length || Qa.length) ? L.map(x => doneCard(x.t, x.s)).join('') + Qa.map(attnCard).join('') : '<p class="hb-empty">Nothing checked by your teacher yet.</p>';
  }
  function counts() {
    const S = states(), sc = H.score(D.tasks, D.replies, D.verdicts);
    $('#st-n-todo').textContent = (sc.todo + sc.waiting + sc.checking + openCards().length + attn().open.length) || '';
    $('#st-n-shaky').textContent = D.shaky ? (H.shakyCards(D.shaky, D.log).length || '') : '';
    $('#st-n-done').textContent = (sc.done + attn().answered.length) || '';
    $('#st-score').innerHTML = scoreHtml();
    $('#st-hello').textContent = sc.todo ? `${sc.todo} to do · ${sc.waiting + sc.checking} waiting for your teacher` : 'Homework your teacher assigned, and the cards to do before the next lesson.';
  }
  function route() { counts(); const tab = (location.hash.slice(1) || 'todo').split('/')[0]; ({ cards: todoView, shaky: shakyView, done: doneView })[tab] ? ({ cards: todoView, shaky: shakyView, done: doneView })[tab]() : todoView(); }   // #cards = old links -> To do
  // AM-27: notes the tutor wrote on her screens (docs/data/tutor-notes.json, rebuilt by the hourly job and her every tap)
  async function notes() {
    const el = document.getElementById('st-notes'); if (!el) return;
    let N = null; try { N = await (await fetch('data/tutor-notes.json', { cache: 'no-store' })).json(); } catch (e) { N = null; }
    const L = (N && N.notes) || [];
    el.innerHTML = L.length ? `<h2 class="hb-h">Notes from the tutor <span class="hb-n">${L.length}</span></h2>` + L.slice(0, 50).map(n => `<article class="hb-moment st-note"><p class="hb-sub">${esc(String(n.at || '').slice(0, 10))} · ${esc(n.list_title || n.list || '')}${n.item && n.item !== 'list' ? ' · ' + esc(n.context || n.item) : ''}</p><p dir="auto">${esc(n.note || '')}</p></article>`).join('') : '';
  }
  function render() { route(); notes(); }
  window.addEventListener('hashchange', route);
  load().then(flush);
  window.AneesLive && AneesLive.onReturn(load, { busy: () => typing || busyIds.size > 0 });
})();
