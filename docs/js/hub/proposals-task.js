/* "New grammar rules to approve" at the top of Amal's To do list (Medi 2026-10-05: "For the grammar additions this should be
   at the top of her todo list"). The proposed rules live on her rules page (docs/amal/grammar-rules.html, section
   id proposed-<date>, one article per rule: P-A13 ...). This item shows those cards inside the hub panel with one tap
   "Yes, this is the rule" (saves the note "Yes - this is the rule as I teach it") and the usual note box for a fix
   (docs/js/amal-grammar-notes.js: amal_rules source grammar_notes, word_key rule:P-A13, Undo as everywhere). A rule counts
   as answered when it has a note. Nothing is scored until Medi says yes too (GR-29).
   AneesProposalsTask.mount(el, {token, section}, {onChange}); AneesProposalsTask.count(ids, notes) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const YES = 'Yes - this is the rule as I teach it';
  function count(ids, notes) { const done = ids.filter(id => (notes[id] || []).length).length; return { total: ids.length, done, left: ids.length - done }; }
  async function section(base) {
    const d = await root.AneesDoc.load((base || '') + 'amal/grammar-rules.html');
    const sec = d.querySelector('section[id^="proposed-"]');
    return sec ? { id: sec.id, title: (sec.querySelector('h2') || {}).textContent || 'Proposed rules', lede: (sec.querySelector('.lede') || {}).textContent || '',
                   rules: [...sec.querySelectorAll('article[id]')].map(a => ({ id: a.id, name: (a.querySelector('h3') || {}).textContent || a.id, html: a.outerHTML })) } : null;
  }
  async function mount(el, ctx, opt) {
    opt = opt || {};
    const S = ctx.section || await section('');
    if (!S) { el.innerHTML = '<p class="hb-sub">No proposed rules right now.</p>'; return; }
    el.innerHTML = `<div class="hb-task"><p class="hb-sub">${esc(S.lede)} Tap <b>Yes</b> when the rule is right as written, or write the fix in the note box.</p>
      ${S.rules.map(r => `<div class="hb-doc hb-prop" data-rule="${esc(r.id)}">${r.html}<div class="hb-btns" data-yes-for="${esc(r.id)}"><button type="button" class="hb-ans primary" data-yes="${esc(r.id)}">Yes, this is the rule<small>saves "${esc(YES)}" as your note on ${esc(r.id)}</small></button></div></div>`).join('')}
      <p class="hb-foot">Saved as you tap · Medi still says yes before anything is scored</p></div>`;
    await root.AneesGrammarNotes.start({ token: ctx.token || '', base: '', scope: el });
    const notesOf = id => [...el.querySelectorAll(`.an-write[data-rule="${CSS.escape(id)}"] .an-saved li`)].length;
    // AM-17: an answered rule shows her answer + the shared Undo; the Undo hands over to the note's own Undo in
    // amal-grammar-notes.js, which records an amal_rules row kind 'undo' (AneesUndo.row(...)) - never a delete
    const report = () => { const ids = S.rules.map(r => r.id); const done = ids.filter(id => notesOf(id)).length;
      el.querySelectorAll('[data-yes-for]').forEach(b => { const id = b.dataset.yesFor, n = notesOf(id);
        b.innerHTML = n ? root.AneesUndo.answered('Answered · ' + n + ' note' + (n === 1 ? '' : 's') + ' saved', { 'data-prop-undo': id })
                          : `<button type="button" class="hb-ans primary" data-yes="${esc(id)}">Yes, this is the rule<small>saves "${esc(YES)}" as your note on ${esc(id)}</small></button>`; });
      el.querySelectorAll('[data-yes]').forEach(b => b.onclick = () => yes(b.dataset.yes));
      el.querySelectorAll('[data-prop-undo]').forEach(b => b.onclick = () => { const u = el.querySelector(`.an-write[data-rule="${CSS.escape(b.dataset.propUndo)}"] .an-undo`); if (u) { u.click(); setTimeout(report, 300); } });
      opt.onChange && opt.onChange({ total: ids.length, done, finished: done >= ids.length }); };
    const yes = id => { const w = el.querySelector(`.an-write[data-rule="${CSS.escape(id)}"]`); if (!w) return;
      w.open = true; const ta = w.querySelector('textarea'), save = w.querySelector('button'); if (!ta || !save) return;
      ta.value = YES; save.click(); setTimeout(report, 300); };
    el.addEventListener('click', e => { if (e.target.closest('.an-write button, .an-undo')) setTimeout(report, 300); });
    report();
  }
  root.AneesProposalsTask = { mount, count, section, YES };
})(typeof window !== 'undefined' ? window : globalThis);
