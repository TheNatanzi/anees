/* "Amal said she will add" on the Word Bank (AM-16, Medi 2026-10-02: "Keep a tab of what she said shes going to add").
   Medi's one place for the promised Doc additions (Progress & Stats holds no word lists, PG-09). Data:
   data/amal-new-words.json `promised` (scripts/amal_new_words.py): every word Amal tapped Add (as NEW or OLD) with
   Waiting / In the Doc since <date> (it moves when the Doc import sees it in her Doc), plus Medi's own marks she has not
   answered yet ("Medi marked old · waiting for Amal"). Read-only; nothing here edits the Doc. */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pretty = d => d ? new Date(String(d).slice(0, 10) + 'T12:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
  function label(p) {
    if (p.state === 'awaiting_amal') return 'The student marked ' + (p.marks && p.marks.medi || p.age || '') + ' · waiting for the tutor';
    const age = p.age ? ' · ' + p.age : '';
    return (p.state === 'in_doc' ? 'In the Doc' + (p.in_doc_since ? ' since ' + pretty(p.in_doc_since) : '') : 'Waiting' + (p.still_waiting ? ' · still waiting' + (p.waiting_days ? ' (' + p.waiting_days + ' days)' : '') : '')) + age;
  }
  // AM-19 "make sure that she adds them": one line for Medi when a promised word is still not in the Doc after 7 days
  // (nothing is sent to Amal by the app, ai_rules A1 - Medi decides whether to remind her)
  function note(P) {
    const late = (P || []).filter(p => p.state === 'waiting' && p.still_waiting);
    return late.length ? `<p class="ab-sub" data-still-waiting>${late.length} word${late.length > 1 ? 's' : ''} the tutor said she'd add still not in the Doc after 7 days: ${late.map(p => esc(p.arabizi || p.arabic)).join(', ')}.</p>` : '';
  }
  function html(data) {
    const P = (data && data.promised) || [];
    if (!P.length) return '';
    const waiting = P.filter(p => p.state !== 'in_doc').length;
    return note(P) + `<details class="ab-promised" data-promised ${waiting ? 'open' : ''}><summary class="ab-sub"><b>The tutor said she will add (${P.length})</b> · ${waiting} waiting · words from our lessons, not on her Doc yet</summary>
      <ul>${P.map(p => `<li data-state="${esc(p.state)}"><b>${esc(p.arabizi || p.arabic)}</b>${p.arabizi && p.arabic ? ` <span lang="ar">${esc(p.arabic)}</span>` : ''} <span>· ${esc(p.english || '')} · ${esc(pretty(p.date))} lesson · ${esc(label(p))}</span></li>`).join('')}</ul></details>`;
  }
  async function mount(el) {
    if (!el) return;
    try { const D = await (await fetch('data/amal-new-words.json', { cache: 'no-store' })).json(); el.innerHTML = html(D); } catch (e) { el.innerHTML = ''; }
  }
  root.AneesPromised = { html, label, mount, note };
  if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', () => mount(document.getElementById('ab-promised')));
})(typeof window !== 'undefined' ? window : globalThis);
