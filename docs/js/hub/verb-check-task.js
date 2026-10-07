/* "Verb forms" lists 1 and 2 (Claude guessed each person of each verb from the forms Amal taught; level 2 = endings and
   prepositions). ONE module for the Tutor hub panel and the old address amal/verb-check.html. Answers live in the link
   row (verb_check_links.answers {schema_version, revision, answers:{<id>:{choice yes|fix, word, arabic, updated_at}}}),
   saved with a revision check (another tab's answers are merged, newest per form wins); a draft stays in this browser.
   Medi 2026-10-02 "everything on the tutor hub do what the new words is doing": cards in the panel, 20 forms at a time
   ("Next 20"), a search box, the honest time left.
   AM-17 ("can you add an undo button to all these tutor hub stuff"): every answered form has the shared Undo - the form
   leaves answers (open again at once) and the undo is logged in answers.undone (never lost); scripts/verb_check_links.py
   pull honours it. AneesVerbCheckTask.mount(el, {token}, {onChange}) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const PAGE = 20, SECONDS_EACH = 6;

  function mount(el, item, opt) {
    opt = opt || {};
    const VC = root.AneesVerbCheck, token = item.token || '';
    el.innerHTML = '<div class="hb-task"><p class="hb-sub" data-intro>Opening the list…</p><input type="search" class="hb-search" data-q placeholder="Find a verb (Arabizi, Arabic or English)" aria-label="Find a verb" hidden><div class="hb-chips" data-show hidden></div><p class="hb-prog" data-prog></p><div data-root></div><p class="hb-foot"><span data-status>Saved as you tap</span> <button type="button" class="an-undo" data-retry hidden>Retry saving</button></p></div>';
    const $ = s => el.querySelector(s), $root = $('[data-root]');
    if (!/^[A-Za-z0-9_-]{43}$/.test(token) || !VC) { $('[data-intro]').textContent = 'Open the complete private link the student sent you.'; return; }
    const endpoint = ANEES.url + '/rest/v1/verb_check_links?token=eq.' + encodeURIComponent(token);
    const headers = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'X-Anees-Token': token, 'Content-Type': 'application/json', Prefer: 'return=representation' };
    async function request(url, method, body) {
      const r = await fetch(url, { method: method || 'GET', headers, body: body ? JSON.stringify(body) : undefined, cache: 'no-store', referrerPolicy: 'no-referrer' });
      if (!r.ok) throw Error('network'); return r.json();
    }
    let payload, saved, answers = {}, undone = [], timer = null, saving = false, again = false, shown = PAGE, view = opt.view === 'done' ? 'done' : 'open', q = '';
    let draftKey = 'anees-verb-check-' + token.slice(0, 16);

    function keepDraft() { try { localStorage.setItem(draftKey, JSON.stringify({ answers, undone })); } catch (e) {} }
    async function flush() {
      if (saving) { again = true; return; } saving = true; $('[data-retry]').hidden = true; $('[data-status]').textContent = 'Saving…';
      try {
        const snapshot = { schema_version: 1, revision: saved.revision + 1, answers: VC.sendable(answers), undone };
        const changed = await request(endpoint + '&answers->>revision=eq.' + saved.revision + '&select=answers', 'PATCH', { answers: snapshot, opened_at: new Date().toISOString() });
        if (!Array.isArray(changed) || changed.length !== 1) {   // someone saved first: take theirs, keep newer local answers
          const fresh = await request(endpoint + '&select=answers'); saved = fresh[0].answers; merge(saved);
          saving = false; return flush();
        }
        saved = changed[0].answers; $('[data-status]').textContent = 'Saved ✓';
      } catch (e) { $('[data-status]').textContent = 'Not saved yet — your answers are kept on this device.'; $('[data-retry]').hidden = false; }
      saving = false; if (again) { again = false; flush(); }
    }
    // newest per form wins; an undo newer than an answer removes it
    function merge(st) {
      for (const [id, a] of Object.entries(st.answers || {})) if (!answers[id] || answers[id].updated_at < a.updated_at) answers[id] = a;
      for (const u of st.undone || []) {
        if (!undone.some(x => x.key === u.key && x.at === u.at)) undone.push(u);
        const a = answers[u.key]; if (a && a.updated_at <= u.at) delete answers[u.key];
      }
    }
    function queue() { keepDraft(); $('[data-status]').textContent = '…'; clearTimeout(timer); timer = setTimeout(flush, 1200); render(); }

    const verbOf = {}; let ids = [];
    const text = id => { const it = payload.items[id], v = verbOf[id]; return [it.word, it.arabic, v.name, v.arabic, v.english].join(' ').toLowerCase(); };
    function card(id) {
      const it = payload.items[id], v = verbOf[id], a = answers[id], fix = a && a.choice === 'fix';
      const head = `<p class="hb-prog">${esc(v.name)} <span lang="ar">${esc(v.arabic)}</span> · ${esc(v.english || '')} · ${esc(it.tense)} · ${esc(it.person)}</p>`;
      const form = `<div class="hb-big">${esc(it.word)}</div>${it.arabic ? `<div class="hb-ar" lang="ar">${esc(it.arabic)}</div>` : ''}`;
      if (a && VC.done(answers, id)) return `<div class="hb-moment" data-vid="${esc(id)}">${head}${form}${AneesUndo.answered(a.choice === 'yes' ? 'You said: right · result: the guess becomes a checked form' : `You fixed it: ${a.word}${a.arabic ? ' · ' + a.arabic : ''} · result: your form replaces the guess`, { 'data-vc': 'undo', 'data-id': id })}</div>`;
      return `<div class="hb-moment" data-vid="${esc(id)}">${head}${form}
        <div class="hb-btns"><button type="button" class="hb-ans primary" data-vc="yes" data-id="${esc(id)}">✓ Right as written</button><button type="button" class="hb-ans" data-vc="fix" data-id="${esc(id)}">Needs a fix<small>type the right form${payload.kind === 'verb-addons' ? ' (or no, if the verb never takes this)' : ''}</small></button></div>
        <div data-fixbox${fix ? '' : ' hidden'}><input class="hb-input" data-f="word" placeholder="Correct Arabizi" value="${esc(fix ? a.word : it.word)}" autocomplete="off" autocapitalize="off" spellcheck="false"><input class="hb-input" data-f="arabic" dir="rtl" lang="ar" placeholder="Arabic (optional)" value="${esc(fix ? a.arabic : it.arabic)}" autocomplete="off"><button type="button" class="hb-ans primary" data-vc="fix-save" data-id="${esc(id)}">Save my form</button></div></div>`;
    }
    function render() {
      const p = VC.progress(payload, answers), left = p.total - p.finished;
      $('[data-prog]').textContent = `${p.finished.toLocaleString('en-US')} of ${p.total.toLocaleString('en-US')} forms answered · ${p.verbsDone} of ${p.verbs} verbs done · about ${Math.max(1, Math.round(left * SECONDS_EACH / 60))} min left`;
      const ql = q.trim().toLowerCase();
      const list = ids.filter(id => (view === 'open' ? !VC.done(answers, id) : VC.done(answers, id)) && (!ql || text(id).includes(ql)));
      const page = list.slice(0, shown);
      $('[data-show]').innerHTML = `<button type="button" class="hb-chip" data-view="open" aria-pressed="${view === 'open'}">To answer (${left.toLocaleString('en-US')})</button><button type="button" class="hb-chip" data-view="done" aria-pressed="${view === 'done'}">Your answers (${p.finished.toLocaleString('en-US')})</button>`;
      $root.innerHTML = (page.length ? `<p class="hb-sub">Showing ${page.length} of ${list.length.toLocaleString('en-US')}${view === 'open' ? ` · these ${page.length} take about ${Math.max(1, Math.round(page.length * SECONDS_EACH / 60))} min` : ''}</p>` + page.map(card).join('')
                                     : `<p class="hb-empty">${view === 'open' ? (ql ? 'No open form matches.' : 'All forms answered. Shukran!') : 'No answers yet.'}</p>`)
        + (list.length > shown ? `<button type="button" class="hb-ans" data-more>Next ${Math.min(PAGE, list.length - shown)} (${(list.length - shown).toLocaleString('en-US')} more)</button>` : '');
      opt.onChange && opt.onChange({ total: p.total, done: p.finished, finished: p.total > 0 && left === 0 });
    }
    el.addEventListener('click', e => {
      const v = e.target.closest('[data-view]'); if (v) { view = v.dataset.view; shown = PAGE; render(); return; }
      if (e.target.closest('[data-more]')) { shown += PAGE; render(); return; }
      if (e.target.closest('[data-retry]')) { flush(); return; }
      const b = e.target.closest('button[data-vc]'); if (!b) return;
      const id = b.dataset.id, now = new Date().toISOString(), box = b.closest('[data-vid]');
      if (b.dataset.vc === 'yes') { answers = VC.answer(payload, answers, id, 'yes', null, null, now); queue(); }
      else if (b.dataset.vc === 'fix') { box.querySelector('[data-fixbox]').hidden = false; box.querySelector('[data-f=word]').focus(); }
      else if (b.dataset.vc === 'fix-save') {
        const w = box.querySelector('[data-f=word]').value.trim(); if (!w) { box.querySelector('[data-f=word]').focus(); return; }
        answers = VC.answer(payload, answers, id, 'fix', w, box.querySelector('[data-f=arabic]').value, now); queue();
      } else if (b.dataset.vc === 'undo') {   // AM-17
        const was = answers[id]; if (!was) return;
        answers = VC.answer(payload, answers, id, null); undone = AneesUndo.log(undone, id, was); queue();
      }
    });
    $('[data-q]').addEventListener('input', e => { q = e.target.value; shown = PAGE; render(); });
    root.addEventListener && root.addEventListener('online', flush);

    (async () => {
      try {
        const rows = await request(endpoint + '&select=payload,answers');
        if (!Array.isArray(rows) || rows.length !== 1) throw Error('expired-link');
        payload = rows[0].payload;
        if (!VC.validPayload(payload) || !VC.validState(payload, rows[0].answers)) throw Error('invalid');
        saved = rows[0].answers; answers = { ...saved.answers }; undone = (saved.undone || []).slice();
        try {
          const h = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))), b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
          draftKey = 'anees-verb-check-' + h;   // the same draft key as the page before 2026-10-02
          const d = JSON.parse(localStorage.getItem(draftKey) || 'null');
          const st = d && d.answers && !d.answers.choice ? { answers: d.answers, undone: d.undone || [] } : { answers: d || {}, undone: [] };
          if (d && VC.validState(payload, { schema_version: 1, revision: 0, answers: st.answers })) merge(st);
        } catch (e) {}
        payload.verbs.forEach(v => v.ids.forEach(id => { verbOf[id] = v; }));
        ids = payload.verbs.flatMap(v => VC.byTense(payload, v).flatMap(t => t.ids));
        $('[data-intro]').innerHTML = payload.kind === 'verb-addons'
          ? 'Level 2: Claude guessed how each verb takes an ending (<i>him, me…</i>) or a small word after it (<i>ma3, la, 3ala…</i>). Tap <b>✓ Right</b>, or <b>Fix</b> and type the correct form; type <b>no</b> if the verb never takes this. Your answer always wins.'
          : 'Claude guessed these verb forms from the forms you already taught the student. Tap <b>✓ Right</b>, or <b>Fix</b> and type the correct form. Your answer always replaces the guess.';
        $('[data-q]').hidden = false; $('[data-show]').hidden = false;
        render();
        if (JSON.stringify(VC.sendable(answers)) !== JSON.stringify(saved.answers) || undone.length !== (saved.undone || []).length) queue();
      } catch (error) {
        $('[data-intro]').textContent = error.message === 'expired-link' ? 'This list has expired or was closed. Ask the student for a new link.' : 'The list could not open. Check your connection and reload.';
      }
    })();
  }
  root.AneesVerbCheckTask = { mount };
})(typeof window !== 'undefined' ? window : globalThis);
