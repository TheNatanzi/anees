/* "New words from our lessons" inside the Tutor hub (Medi 2026-10-02: "She said a new word in the lesson today that's
   not on our document ... bring it to her attention if she wants to add it to the document, save it for a future lesson,
   or forget it"). Words Amal used in a lesson that are not on her vocabulary Doc (judged by meaning, data from
   data/amal-new-words.json, built by scripts/amal_new_words.py). One card per word: the word, her spelling when she
   typed it, the English, the moment (audio bar) and four choices (AM-16: Add as NEW / Add as OLD / later / forget). Her tap goes to Supabase amal_rules (source 'review',
   word_key 'newword:...', kind newword_add / newword_later / newword_forget) with the open review link's token, queued in
   localStorage first so nothing is lost offline. The builder reads the taps back; nothing edits her Doc.
   AneesNewWordsTask.mount(el, {token, data}, {onChange}); AneesNewWordsTask.count(data, answers). */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LS = (k, v) => { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } };
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  // AM-16 (Medi 2026-10-02: "We need a way for her to indicate old and new words" / "yes have her tap that its old"):
  // two Add choices - NEW (Medi learns it as a new word) or OLD (Medi already knows it). Nothing is pre-selected; Medi's
  // own mark only shows as a hint on the card. newword_add (before 2026-10-02) stays readable.
  const CHOICES = [
    ['newword_add_new', 'Add to the Doc as NEW', 'a new word for Medi to learn', 'primary'],
    ['newword_add_old', 'Add to the Doc as OLD', 'Medi already knows it', 'primary'],
    ['newword_later', 'Save it for a future lesson', 'it waits for a later lesson', ''],
    ['newword_forget', 'Forget it', 'not needed - the app stops asking', 'drop'],
  ];
  const SAID = { newword_add: 'Add it to the Doc', newword_add_new: 'Add to the Doc as NEW', newword_add_old: 'Add to the Doc as OLD',
                 newword_later: 'Saved for a future lesson', newword_forget: 'Forget it' };
  const STATUS = { add: 'newword_add', later: 'newword_later', forget: 'newword_forget' };
  const isAdd = k => /^newword_add/.test(k || '');
  const AGE = { newword_add_new: 'new', newword_add_old: 'old' };

  // An item is decided when her live/queued tap says so, or the last build already read one from Supabase.
  function decided(it, answers) { return (answers && answers[it.id]) || (it.status && it.status !== 'open' ? { kind: it.tap || STATUS[it.status] } : null); }
  function count(data, answers) {
    const items = (data && data.items) || [];
    const done = items.filter(it => decided(it, answers)).length;
    return { total: items.length, done, left: items.length - done, newest: items.reduce((m, it) => (it.date > m ? it.date : m), '') };
  }

  function mount(el, ctx, opt) {
    opt = opt || {};
    const TOKEN = ctx.token || '', D = ctx.data || { items: [] };
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'Content-Type': 'application/json', 'X-Anees-Token': TOKEN };
    const api = (m, p, b, extra) => fetch(ANEES.url + '/rest/v1/' + p, { method: m, headers: { ...H, ...(extra || {}) }, body: b ? JSON.stringify(b) : undefined });
    const QK = 'anees-newwords-q-' + TOKEN, AK = 'anees-newwords-a-' + TOKEN;
    let answers = Object.assign({}, ctx.answers || {}, LS(AK) || {}), flushing = false;

    async function flush() {
      if (flushing || !TOKEN) return; flushing = true;
      while (true) {
        const q = LS(QK) || []; if (!q.length) break; const job = q[0]; let ok = false;
        try { const r = await api('POST', 'amal_rules', job.body, { Prefer: 'return=minimal' }); ok = r.ok || r.status === 409; } catch (e) { ok = false; }
        if (!ok) { await new Promise(r => setTimeout(r, 2500)); continue; }
        LS(QK, (LS(QK) || []).filter(x => x.id !== job.id));
      }
      flushing = false; render();
    }
    function decide(id, kind) {
      const it = (D.items || []).find(x => x.id === id); if (!it) return;
      answers[id] = { kind, at: new Date().toISOString() }; LS(AK, answers);
      const q = LS(QK) || [];
      q.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2), body: { token: TOKEN, source: 'review', lesson_date: null, kind, word_key: id,
        payload: { label: it.arabic || it.arabizi, new_word: true, age: AGE[kind] || null, medi_mark: it.medi_mark || null, arabic: it.arabic || null, arabizi: it.arabizi || null, english: it.english || null,
                   date: it.date, t: it.t, list_built: D.built } } });
      LS(QK, q); flush(); render();
    }

    function card(it) {
      const a = decided(it, answers), pending = (LS(QK) || []).some(j => j.body.word_key === it.id);
      const big = it.arabizi ? `<div class="hb-big">${esc(it.arabizi)}</div>${it.arabic ? `<div class="hb-ar" lang="ar">${esc(it.arabic)}</div>` : ''}`
                             : `<div class="hb-big hb-ar" lang="ar" style="color:var(--ab-text);font-size:24px">${esc(it.arabic)}</div>`;
      return `<div class="hb-moment" data-nw="${esc(it.id)}">
        <p class="hb-prog">${esc(pretty(it.date))} lesson · ${esc(it.mmss || '')}</p>${big}
        ${it.english ? `<div class="hb-en">${esc(it.english)}</div>` : ''}
        ${it.hint ? `<div class="hb-why" data-hint="old"><b>Note from Medi:</b> ${esc(it.hint)}</div>` : ''}
        ${it.line ? `<div class="hb-why">You ${it.typed ? 'typed' : 'said'}: <span lang="${it.typed ? 'en' : 'ar'}">${esc(it.line)}</span></div>` : ''}
        <div data-bar></div>
        ${a ? `<p class="hb-sub" style="color:var(--vp-sage,#2E6A4E);font-weight:600;margin:6px 0 0">✓ ${esc(SAID[a.kind] || '')}${pending ? ' · saving…' : ''}</p>`
            : `<div class="hb-btns">${CHOICES.map(([k, l, s, c]) => `<button type="button" class="hb-ans ${c}" data-nwk="${k}" data-id="${esc(it.id)}">${esc(l)}<small>${esc(s)}</small></button>`).join('')}</div>`}
      </div>`;
    }
    function render() {
      const items = D.items || [], open = items.filter(it => !decided(it, answers)), adds = items.filter(it => isAdd((decided(it, answers) || {}).kind));
      const P = {}; (D.promised || []).forEach(p => { P[p.id] = p; });
      const stateOf = it => { const p = P[it.id]; return p && p.state === 'in_doc' ? 'In the Doc' + (p.in_doc_since ? ' since ' + pretty(p.in_doc_since) : '') : 'Waiting'; };
      const ageOf = it => AGE[(decided(it, answers) || {}).kind] || (P[it.id] && P[it.id].age) || '';
      const c = count(D, answers);
      el.innerHTML = `<div class="hb-task"><p class="hb-sub">Words you used in our lessons that are not on the vocabulary Doc. For each one: add it to the Doc as a NEW word or an OLD word Medi already knows, save it for a future lesson, or forget it.</p>
        ${TOKEN ? '' : '<p class="hb-sub">No open review link, so answers cannot be saved right now.</p>'}
        <div data-root>${open.length ? open.map(card).join('') : '<p class="hb-empty">All new words decided. Shukran!</p>'}</div>
        ${adds.length ? `<p class="hb-prog" style="margin-top:14px">You said you will add these to the Doc (${adds.length})</p><ul class="hb-done" data-promised>${adds.map(it => `<li><b>${esc(it.arabizi || it.arabic)}</b>${it.arabizi && it.arabic ? ` <span lang="ar">${esc(it.arabic)}</span>` : ''} <span>· ${esc(it.english || '')}${ageOf(it) ? ' · ' + esc(ageOf(it)) : ''} · ${esc(stateOf(it))}</span></li>`).join('')}</ul>` : ''}
        <p class="hb-foot">Saved as you tap · nothing changes the Doc by itself</p></div>`;
      el.querySelectorAll('[data-nw]').forEach(box => {
        const it = items.find(x => x.id === box.dataset.nw), slot = box.querySelector('[data-bar]');
        if (it && it.clip && root.AneesClip && slot) slot.appendChild(AneesClip.bar({ src: it.clip.src, start: it.clip.start, end: it.clip.end }));
      });
      el.querySelectorAll('[data-nwk]').forEach(b => b.onclick = () => decide(b.dataset.id, b.dataset.nwk));
      opt.onChange && opt.onChange({ total: c.total, done: c.done, finished: c.total > 0 && c.left === 0 });
    }
    render(); flush();
  }
  root.AneesNewWordsTask = { mount, count, decided };
})(window);
