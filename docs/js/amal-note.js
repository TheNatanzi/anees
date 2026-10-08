/* AM-27 (Medi 2026-10-07 "lets add a place for notes for amal always"): every Tutor screen has a place for a note.
   One shared widget: a "✎ Note for the student" box under every card that carries an id (check lists, moments, verb forms,
   word reviews) and one for the whole list at the bottom of the panel, so there is always somewhere to write. A note is its own
   row in amal_rules (source 'note', kind 'note', word_key 'note:<list>:<card id | list>', payload {note, list, item, context}),
   saved with the list's own link token the way every tap is saved; a later note on the same card replaces it (latest wins);
   an emptied box writes an undo row (AM-17). Nothing here changes a score: Medi reads the notes on the Student tab
   ("Notes from the tutor", docs/data/tutor-notes.json, built by scripts/build_tutor_data.py) and on the Completed rows.
   AneesNote.attach(panel, {token, list, title}) — idempotent; it watches the panel and adds a box to each new card. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AneesNote = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const SOURCE = 'note', MAX = 600;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const CARD = '[data-id], [data-lq], [data-pid], [data-vid], [data-key], [data-card], [data-word-key], [data-task], article.tv-card[id]';   // every module's card: check lists, ledger moments, review patterns, verb forms, tasks

  /** The row one note writes. ctx = the card's first words (so Medi sees what the note is about without the page). */
  function body(token, list, item, note, ctx) {
    const key = 'note:' + String(list || 'page') + ':' + String(item || 'list');
    const p = { note: String(note || '').trim().slice(0, MAX), list: String(list || ''), item: String(item || ''), context: String(ctx || '').slice(0, 160), page: typeof location !== 'undefined' ? location.pathname.split('/').pop() : '' };
    return { token: token, source: SOURCE, kind: p.note ? 'note' : 'undo', word_key: key, payload: p };
  }

  /** {word_key: latest payload} from the rows read back (an undo wipes the note; latest row wins). */
  function latest(rows) {
    const out = {};
    (rows || []).slice().sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || ''))).forEach(r => {
      if (!r || !r.word_key) return;
      if (r.kind === 'undo') delete out[r.word_key]; else if (r.kind === 'note') out[r.word_key] = r.payload || {};
    });
    return out;
  }

  function attach(panel, o) {
    if (typeof document === 'undefined' || !panel || panel.dataset.anNote) return;
    panel.dataset.anNote = '1';
    o = o || {};
    const token = o.token || '', list = String(o.list || o.title || 'page'), A = (typeof ANEES !== 'undefined' && ANEES) || {};
    const H = { apikey: A.anon, Authorization: 'Bearer ' + A.anon, 'Content-Type': 'application/json', 'X-Anees-Token': token };
    const api = (m, p, b, extra) => fetch(A.url + '/rest/v1/' + p, { method: m, headers: Object.assign({}, H, extra || {}), body: b ? JSON.stringify(b) : undefined });
    const LSK = 'anees-notes-' + list + '-' + token;
    const local = () => { try { return JSON.parse(localStorage.getItem(LSK) || '{}'); } catch (e) { return {}; } };
    const setLocal = m => { try { localStorage.setItem(LSK, JSON.stringify(m)); } catch (e) { /* private window */ } };
    let saved = local();

    async function load() {
      if (!token || !A.url) return;
      try {
        const r = await api('GET', 'amal_rules?select=kind,word_key,payload,created_at&source=eq.' + SOURCE + '&word_key=like.' + encodeURIComponent('note:' + list + ':*') + '&order=created_at.asc&token=eq.' + encodeURIComponent(token));
        if (r.ok) { const m = latest(await r.json()); Object.keys(m).forEach(k => { saved[k] = m[k].note || ''; }); setLocal(saved); panel.querySelectorAll('.an-note').forEach(fill); }
      } catch (e) { /* offline: the local copy stands */ }
    }
    async function save(box, item, ctx) {
      const ta = box.querySelector('textarea'), st = box.querySelector('.an-note-st'), text = ta.value.trim();
      const b = body(token, list, item, text, ctx);
      st.textContent = 'Saving…';
      let ok = false;
      if (token && A.url) { try { const r = await api('POST', 'amal_rules', b, { Prefer: 'return=minimal' }); ok = r.ok || r.status === 409; } catch (e) { ok = false; } }
      saved[b.word_key] = text; setLocal(saved);
      st.textContent = ok ? (text ? '✓ Note saved' : '✓ Note removed') : (token ? 'Could not save - kept here, try again' : 'Open this page from the private link to save');
      box.classList.toggle('an-note-has', !!text);
    }
    function fill(box) {
      const k = 'note:' + list + ':' + (box.dataset.item || 'list'), v = saved[k] || '';
      const ta = box.querySelector('textarea'), st = box.querySelector('.an-note-st'), d = box.querySelector('details');
      if (ta && ta.value !== v && document.activeElement !== ta) ta.value = v;
      box.classList.toggle('an-note-has', !!v);
      if (v) { d.open = true; st.textContent = '✓ Note saved'; }
    }
    function make(item, ctx, forList) {
      const box = document.createElement('div'); box.className = 'an-note' + (forList ? ' an-note-list' : ''); box.dataset.item = item || 'list';
      box.innerHTML = `<details><summary>✎ ${forList ? 'Note for the student about this list' : 'Note for the student'} <span class="an-note-st"></span></summary>
        <textarea class="hb-input" rows="2" dir="auto" maxlength="${MAX}" placeholder="Anything you want the student to know${forList ? '' : ' about this one'}"></textarea>
        <button type="button" class="hb-ans an-note-save">Save note</button></details>`;
      box.querySelector('.an-note-save').onclick = () => save(box, item, ctx);
      box.querySelector('textarea').onkeydown = e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save(box, item, ctx); };
      fill(box);
      return box;
    }
    function cardId(c) { return c.dataset.id || c.dataset.lq || c.dataset.pid || c.dataset.vid || c.dataset.key || c.dataset.card || c.dataset.wordKey || c.dataset.task || (c.id && c.id.startsWith('tv-') ? c.id.slice(3) : '') || ''; }
    function sweep() {
      panel.querySelectorAll(CARD).forEach(c => {
        if (c.querySelector(':scope > .an-note') || c.closest('.an-note')) return;
        if (!/^(ARTICLE|SECTION|LI|DIV)$/.test(c.tagName) || (c.parentElement && c.parentElement.closest(CARD))) return;   // the outermost card only, never a button inside it
        const id = cardId(c); if (!id) return;
        c.appendChild(make(id, (c.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 160), false));
      });
      if (!panel.querySelector(':scope .an-note-list')) {
        const foot = panel.querySelector('.hb-foot, [data-foot]');
        const box = make('list', list, true);
        if (foot && foot.parentNode) foot.parentNode.insertBefore(box, foot); else panel.appendChild(box);
      }
    }
    if (!document.getElementById('an-note-css')) {
      const s = document.createElement('style'); s.id = 'an-note-css';
      s.textContent = '.an-note{margin:8px 0 2px;font-size:13px}.an-note summary{cursor:pointer;color:var(--ab-muted,#6b7a72)}.an-note-has summary{color:var(--ab-accent,#2f7a5a)}.an-note textarea{width:100%;margin:6px 0;box-sizing:border-box}.an-note-st{margin-left:6px;font-size:12px}.an-note-list{border-top:1px dashed var(--ab-line,#cfd8d2);padding-top:8px;margin-top:14px}';
      document.head.appendChild(s);
    }
    sweep();
    new MutationObserver(() => sweep()).observe(panel, { childList: true, subtree: true });
    load();
    // rule L1 (S7): the notes are live data - read them again when the tab comes back into view
    const AL = (typeof window !== 'undefined' && window.AneesLive) || null;
    if (AL && AL.onReturn) AneesLive.onReturn(load, { label: 'tutor notes' });
  }
  return { attach, body, latest, SOURCE };
});
