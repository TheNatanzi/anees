/* "Assign homework" on the Tutor page + Amal's check of Medi's answers (Medi 2026-10-05: "lets also create a box for her
   'assign homework'. Give her three options. Translate Sentence, Create Sentence with (she will provide words), and answer
   question (she may want to give context)"; "Homework and the cards she assigns me for the next lessons").
   One box, the pattern every classroom tool shares (plan/HOMEWORK-RESEARCH-2026-10-05.md): what to do, optional material, the
   lesson it is for. Four kinds: Translate a sentence (she picks the direction per sentence, Q4), Make a sentence with these
   words, Answer a question (optional context), Cards for a lesson (one of her uploads, a Quizlet set or the Shaky words).
   Rows go to Supabase homework_tasks (append-only, undo = a new row). His typed answers (Student tab) come back here with
   the AI's first check (right / close / wrong + reason, Q1): she taps Confirm or overrules with her own verdict and a note;
   nothing counts until she has (Q1); an overrule is a correction rule the checker learns from (S6).
   AneesHomeworkTask.mount(el, {token, tasks, replies, verdicts, sets, live}, {onChange}); AneesHomeworkTask.count(...) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'h' + Date.now().toString(36) + Math.random().toString(36).slice(2));
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  const QK = 'anees-homework-q';
  const SAY = { right: 'The student got it right', close: 'The student was close', wrong: 'The student got it wrong' };   // AM-23: plain sentences

  function count(tasks, replies, verdicts) {
    const H = root.AneesHomework, T = H.effective(tasks);
    const waiting = T.filter(t => t.kind !== 'cards' && H.taskState(t, replies, verdicts).state === 'waiting').length;
    return { total: T.length, waiting, done: T.length - waiting, left: waiting };
  }

  function mount(el, ctx, opt) {
    opt = opt || {};
    const H = root.AneesHomework, TOKEN = ctx.token || '';
    const HD = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', Prefer: 'return=minimal' };
    const api = (p, b) => fetch(ANEES.url + '/rest/v1/' + p, { method: 'POST', headers: HD, body: JSON.stringify(b) });
    let tasks = (ctx.tasks || []).slice(), verdicts = (ctx.verdicts || []).slice(), replies = ctx.replies || [], flushing = false, msg = '';
    let form = { kind: 'translate', direction: 'en_ar', prompt: '', words: '', context: '', set_ref: '', lesson_date: '' };
    const over = {};   // reply id -> the overrule verdict she picked (before the note is typed)
    for (const j of LS(QK) || []) { const L = j.table === 'homework_tasks' ? tasks : verdicts; if (!L.some(r => r.id === j.body.id)) L.push(j.body); }

    async function flush() {
      if (flushing) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await api(job.table, job.body); ok = r.ok || r.status === 409; if (!ok && r.status >= 400 && r.status < 500 && r.status !== 429) { msg = 'The server refused one row (' + r.status + ').'; LS(QK, q.slice(1)); continue; } } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; render();
    }
    function save(table, body) { const q = LS(QK) || []; q.push({ id: body.id, table, body }); LS(QK, q); (table === 'homework_tasks' ? tasks : verdicts).push(body); flush(); render(); }

    // ---- assign ------------------------------------------------------------------------------------------------------
    function assign() {
      const f = form, base = { id: uuid(), kind: f.kind, lesson_date: f.lesson_date || null, token: TOKEN || null, created_at: new Date().toISOString() };
      if (f.kind === 'cards') {
        const s = (ctx.sets || []).find(x => x.id === f.set_ref); if (!s) { msg = 'Pick a card set.'; render(); return; }
        if (!f.lesson_date) { msg = 'Pick the lesson date the cards are for.'; render(); return; }
        save('homework_tasks', { ...base, set_ref: s.id, set_title: s.title, n_cards: s.n });
      } else {
        if (!f.prompt.trim()) { msg = f.kind === 'question' ? 'Type the question.' : 'Type the sentence.'; render(); return; }
        const words = f.kind === 'create' ? f.words.split(/[,\n،]+/).map(x => x.trim()).filter(Boolean) : null;
        if (f.kind === 'create' && !words.length) { msg = 'Give the words he must use (comma-separated).'; render(); return; }
        save('homework_tasks', { ...base, prompt: f.prompt.trim().slice(0, 2000), direction: f.kind === 'translate' ? f.direction : null, words,
                                 context: f.kind === 'question' && f.context.trim() ? f.context.trim().slice(0, 2000) : null });
      }
      msg = ''; form = { ...form, prompt: '', words: '', context: '' };
    }
    function undoTask(id) { const was = tasks.find(t => t.id === id); if (!was) return; LS(QK, (LS(QK) || []).filter(j => j.body.id !== id)); save('homework_tasks', { id: uuid(), kind: 'undo', undoes: id, token: TOKEN || null, created_at: new Date().toISOString() }); }
    // ---- her verdict --------------------------------------------------------------------------------------------------
    function judge(reply, verdict, agrees) {
      const note = (el.querySelector(`[data-note="${CSS.escape(reply.id)}"]`) || {}).value || '', fix = (el.querySelector(`[data-fix="${CSS.escape(reply.id)}"]`) || {}).value || '';
      save('homework_verdicts', { id: uuid(), reply_id: reply.id, kind: 'verdict', verdict, agrees, note: note.trim().slice(0, 1000) || null, fix: fix.trim().slice(0, 1000) || null, token: TOKEN || null, created_at: new Date().toISOString() });
      delete over[reply.id];
    }
    function undoVerdict(id) { LS(QK, (LS(QK) || []).filter(j => j.body.id !== id)); save('homework_verdicts', { id: uuid(), reply_id: (verdicts.find(v => v.id === id) || {}).reply_id || '', kind: 'undo', undoes: id, token: TOKEN || null, created_at: new Date().toISOString() }); }

    // ---- view ---------------------------------------------------------------------------------------------------------
    const chip = (name, v, label, cur) => `<button type="button" class="hb-chip" data-f="${name}" data-v="${esc(v)}" aria-pressed="${String(cur) === String(v)}">${esc(label)}</button>`;
    function taskLine(t) {
      if (t.kind === 'cards') return `<b>Cards for ${esc(pretty(t.lesson_date))}</b> · ${esc(t.set_title)} (${t.n_cards} cards)`;
      const head = t.kind === 'translate' ? `Translate (${esc(H.DIRECTIONS[t.direction] || '')})` : t.kind === 'create' ? 'Make a sentence with: ' + esc((t.words || []).join(', ')) : 'Answer';
      return `<b>${head}</b> · <span dir="auto">${esc(t.prompt)}</span>${t.context ? ` <i>(${esc(t.context)})</i>` : ''}${t.lesson_date ? ` · for ${esc(pretty(t.lesson_date))}` : ''}`;
    }
    function formHtml() {
      const f = form, sets = ctx.sets || [];
      return `<div class="hb-moment" data-form><p class="hb-prog">Assign homework</p>
        <div class="hb-chips">${chip('kind', 'translate', 'Translate a sentence', f.kind)}${chip('kind', 'create', 'Make a sentence with…', f.kind)}${chip('kind', 'question', 'Answer a question', f.kind)}${chip('kind', 'cards', 'Cards for a lesson', f.kind)}</div>
        ${f.kind === 'translate' ? `<div class="hb-chips">${chip('direction', 'en_ar', 'English → Arabic', f.direction)}${chip('direction', 'ar_en', 'Arabic → English', f.direction)}</div>
          <textarea class="hb-input" data-in="prompt" rows="2" placeholder="${f.direction === 'en_ar' ? 'The sentence in English' : 'The sentence in Arabic (letters or Arabizi)'}" dir="auto">${esc(f.prompt)}</textarea>` : ''}
        ${f.kind === 'create' ? `<input class="hb-input" data-in="words" placeholder="Words he must use, comma-separated (your spelling)" dir="auto" value="${esc(f.words)}">
          <textarea class="hb-input" data-in="prompt" rows="2" placeholder="What the sentence should be about (e.g. your weekend)" dir="auto">${esc(f.prompt)}</textarea>` : ''}
        ${f.kind === 'question' ? `<textarea class="hb-input" data-in="prompt" rows="2" placeholder="The question (Arabic or English)" dir="auto">${esc(f.prompt)}</textarea>
          <textarea class="hb-input" data-in="context" rows="2" placeholder="Context, if you want (optional)" dir="auto">${esc(f.context)}</textarea>` : ''}
        ${f.kind === 'cards' ? `<select class="hb-input" data-in="set_ref"><option value="">Pick a card set…</option>${sets.map(s => `<option value="${esc(s.id)}"${s.id === f.set_ref ? ' selected' : ''}>${esc(s.title)} · ${s.n} cards${s.group ? ' · ' + esc(s.group) : ''}</option>`).join('')}</select>` : ''}
        <label class="hb-sub">For the lesson on <input type="date" class="hb-input" data-in="lesson_date" value="${esc(f.lesson_date)}" style="width:auto;display:inline-block;margin:0 0 0 6px">${f.kind === 'cards' ? '' : ' <i>(optional)</i>'}</label>
        <div class="hb-btns"><button type="button" class="hb-ans primary" data-assign>Assign<small>it shows on the Student tab at once</small></button></div></div>`;
    }
    function replyHtml(t, s) {
      const r = s.reply, ai = s.ai, pick = over[r.id];
      return `<div class="hb-moment" data-reply="${esc(r.id)}"><p class="hb-prog">${taskLine(t)}</p>
        <div class="hb-big" dir="auto" style="font-size:20px">${esc(r.answer)}</div>
        <div class="hb-why">${ai ? `<b>AI check: ${SAY[ai.verdict]}</b> · ${esc(ai.reason || '')}${ai.fixed && ai.fixed !== r.answer ? ` · <span dir="auto">${esc(ai.fixed)}</span>` : ''}` : '<b>AI check:</b> not done (' + esc((r.ai && r.ai.reason) || 'budget or error') + ')'}</div>
        <div class="hb-btns">${ai ? `<button type="button" class="hb-ans primary" data-judge="${esc(r.id)}" data-v="${ai.verdict}" data-agree="1">Yes: ${SAY[ai.verdict]}<small>the AI's first check stands</small></button>` : ''}
          <div class="hb-chips">${H.VERDICTS.filter(v => !ai || v !== ai.verdict).map(v => `<button type="button" class="hb-chip" data-over="${esc(r.id)}" data-v="${v}" aria-pressed="${pick === v}">${ai ? 'No: ' : ''}${SAY[v]}</button>`).join('')}</div>
          ${pick ? `<input class="hb-input" data-fix="${esc(r.id)}" placeholder="How he should say it (optional)" dir="auto"><textarea class="hb-input" data-note="${esc(r.id)}" rows="2" placeholder="Why - one line (becomes a rule the checker learns)"></textarea>
            <button type="button" class="hb-ans primary" data-judge="${esc(r.id)}" data-v="${pick}" data-agree="0">Save: ${SAY[pick]}</button>` : ''}</div></div>`;
    }
    function render() {
      const T = H.effective(tasks), pending = new Set((LS(QK) || []).map(j => j.body.id));
      const states = T.map(t => ({ t, s: t.kind === 'cards' ? { state: 'cards' } : H.taskState(t, replies, verdicts) }));
      const toCheck = states.filter(x => x.s.state === 'waiting'), open = states.filter(x => x.s.state === 'todo' || x.s.state === 'checking' || x.s.state === 'cards'), done = states.filter(x => x.s.state === 'done');
      const c = count(tasks, replies, verdicts);
      el.innerHTML = `<div class="hb-task">
        ${toCheck.length ? `<p class="hb-prog">Answers to check (${toCheck.length})</p><p class="hb-sub">The AI checked first. Confirm it, or say what it really is - your word is the one that counts.</p>${toCheck.map(x => replyHtml(x.t, x.s)).join('')}` : ''}
        ${formHtml()}
        ${msg ? `<p class="hb-sub" style="color:var(--sabz-danger,#B3261E)">${esc(msg)}</p>` : ''}
        ${open.length ? `<p class="hb-prog" style="margin-top:14px">Assigned, not answered yet (${open.length})</p><ul class="hb-done">${open.map(x => `<li data-answered="${esc(x.t.id)}"><span>${taskLine(x.t)} · ${esc(pretty(x.t.created_at))}${pending.has(x.t.id) ? ' · saving…' : ''}${x.s.state === 'checking' ? ' · he answered, AI check running' : ''}</span>${AneesUndo.button({ 'data-tundo': x.t.id })}</li>`).join('')}</ul>` : ''}
        ${done.length ? `<p class="hb-prog" style="margin-top:14px">Checked (${done.length})</p><ul class="hb-done">${done.slice(0, 40).map(x => `<li data-answered="${esc(x.s.verdict.id)}"><span>${taskLine(x.t)}<br>Student: <span dir="auto">${esc(x.s.reply.answer)}</span> · you: <b>${SAY[x.s.final]}</b>${x.s.verdict.agrees === false ? ' (overruled the AI' + (x.s.ai ? ': ' + SAY[x.s.ai.verdict] : '') + ')' : ''}${x.s.verdict.note ? ' · ' + esc(x.s.verdict.note) : ''}${pending.has(x.s.verdict.id) ? ' · saving…' : ''}</span>${AneesUndo.button({ 'data-vundo': x.s.verdict.id })}</li>`).join('')}</ul>` : ''}
        <p class="hb-foot">Saved as you tap · it shows on the Student tab at once · nothing is sent to anyone</p></div>`;
      el.querySelectorAll('[data-f]').forEach(b => b.onclick = () => { readForm(); form[b.dataset.f] = b.dataset.v; render(); });
      el.querySelectorAll('[data-in]').forEach(i => i.onchange = readForm);
      const as = el.querySelector('[data-assign]'); if (as) as.onclick = () => { readForm(); assign(); };
      el.querySelectorAll('[data-over]').forEach(b => b.onclick = () => { over[b.dataset.over] = b.dataset.v; render(); });
      el.querySelectorAll('[data-judge]').forEach(b => b.onclick = () => { const r = replies.find(x => x.id === b.dataset.judge); if (r) judge(r, b.dataset.v, b.dataset.agree === '1'); });
      el.querySelectorAll('[data-tundo]').forEach(b => b.onclick = () => undoTask(b.dataset.tundo));
      el.querySelectorAll('[data-vundo]').forEach(b => b.onclick = () => undoVerdict(b.dataset.vundo));
      opt.onChange && opt.onChange({ total: c.total, done: c.done, finished: false });
    }
    function readForm() { el.querySelectorAll('[data-in]').forEach(i => { form[i.dataset.in] = i.value; }); }
    render(); flush();
  }
  root.AneesHomeworkTask = { mount, count };
})(typeof window !== 'undefined' ? window : globalThis);
