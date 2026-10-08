/* "Student results" on Amal's Tutor To do (Medi 2026-10-08: "lets set up a system where my scores get sent back to her. If I
   do the card set 1 time send score. If I fix mistakes tell her how I did, If I do it again 30 min or however long later tell
   her how many hr/min after I tried again with new scores"). Nothing is sent: code never contacts Amal (AM-01) - the results
   are a section she reads on her Tutor page. Data = the card_results rows cards.html already writes for a set round
   (subject 'sel:<set>', round_id per round, attempt 1 = first pass, attempt 2+ = the fix-mistakes pass of that round).
   AneesResultsTask.view(log, sets) -> [{set_ref, title, n, tries:[{round_id, at, first:{got,n,pct}, fix:{got,n,pct}|null, after_min}]}]
   AneesResultsTask.mount(el, {view}); AneesResultsTask.count(view) */
(function (root) {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pct = (got, n) => n ? Math.round(100 * got / n) : null;
  const when = iso => iso ? new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '';
  // "2 h 15 min" / "35 min" / "3 days 2 h" - whole units, plain words
  function gap(min) {
    if (min == null) return '';
    const m = Math.max(0, Math.round(min)), d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), r = m % 60;
    if (d) return d + ' day' + (d > 1 ? 's' : '') + (h ? ' ' + h + ' h' : '');
    if (h) return h + ' h' + (r ? ' ' + r + ' min' : '');
    return r + ' min';
  }
  function view(log, sets) {
    const titles = new Map((sets || []).map(s => [s.id, s]));
    const bySet = new Map();
    for (const r of log || []) {
      if (!r || r.undone_at || r.undone || !/^sel:/.test(String(r.subject || ''))) continue;
      const ref = String(r.subject).slice(4);
      if (!bySet.has(ref)) bySet.set(ref, new Map());
      // cards.html gives the review pass of a round the same id plus '-2' ('-2-3' for a third pass): one try
      const rounds = bySet.get(ref), rid = String(r.round_id || ('t:' + String(r.ts).slice(0, 13))).replace(/(-\d+)+$/, '');
      if (!rounds.has(rid)) rounds.set(rid, []);
      rounds.get(rid).push(r);
    }
    const out = [];
    for (const [ref, rounds] of bySet) {
      const s = titles.get(ref) || {};
      const tries = [...rounds.entries()].map(([round_id, rows]) => {
        rows.sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
        // first pass = the first answer on each card; every later answer on a card in the same try (a missed card dealt
        // again at attempt 1, or the review pass at attempt 2+) is the fix-mistakes retry
        const seen = new Set(), f1 = [], fix = [];
        for (const r of rows) { if (seen.has(r.word_key)) fix.push(r); else { seen.add(r.word_key); f1.push(r); } }
        const got = f1.filter(r => r.result === 'got').length;
        const fixKeys = new Set(); fix.forEach(r => fixKeys.add(r.word_key));
        const fgot = [...fixKeys].filter(k => fix.filter(r => r.word_key === k).slice(-1)[0].result === 'got').length;   // last answer on the retry wins
        return { round_id, at: rows[0].ts, end: rows[rows.length - 1].ts, first: { got, n: f1.length, pct: pct(got, f1.length) },
                 fix: fix.length ? { got: fgot, n: fixKeys.size, pct: pct(fgot, fixKeys.size) } : null, after_min: null };
      }).sort((a, b) => String(a.at).localeCompare(String(b.at)));
      for (let i = 1; i < tries.length; i++) tries[i].after_min = (new Date(tries[i].at) - new Date(tries[i - 1].at)) / 60000;
      // a set the hub has no name for: 'shaky|speaking|All' = Shaky words, 'all:topic:Household Items' = Household Items
      const name = s.title || (/^shaky/.test(ref) ? 'Shaky words' : ref.replace(/^[a-z]+:[a-z]+:/, '').replace(/^(all|q|u):/, ''));
      out.push({ set_ref: ref, title: name, n: s.n || Math.max(...tries.map(t => t.first.n)), tries, last: tries[tries.length - 1].at });
    }
    return out.sort((a, b) => String(b.last).localeCompare(String(a.last)));
  }
  function count(v) { const n = (v || []).reduce((s, x) => s + x.tries.length, 0); return { total: n, done: n, left: 0 }; }
  function tryHtml(t, i, setN) {
    const head = i === 0 ? 'Try 1 · ' + esc(when(t.at)) : 'Try ' + (i + 1) + ' · ' + esc(gap(t.after_min)) + ' after try ' + i + ' · ' + esc(when(t.at));
    const f = t.first, x = t.fix;
    const first = 'first pass ' + f.got + ' of ' + f.n + ' right' + (f.pct == null ? '' : ' (' + f.pct + '%)') + (setN && f.n < setN ? ' · ' + f.n + ' of ' + setN + ' cards dealt' : '');
    const fix = x ? 'fixed mistakes: ' + x.got + ' of ' + x.n + ' right on the retry' + (x.pct == null ? '' : ' (' + x.pct + '%)') : f.got < f.n ? 'mistakes not retried' : 'nothing to fix';
    return '<li><b>' + head + '</b><span> · ' + first + ' · ' + fix + '</span></li>';
  }
  function mount(el, ctx) {
    const v = (ctx && ctx.view) || [];
    el.innerHTML = '<p class="hb-sub">What the student did on the card sets, by himself on Flashcards. One line per try: the first pass through the set, then how the retry of his mistakes went; a later try says how long after the one before.</p>'
      + (v.length ? v.map(s => '<p class="hb-prog" style="margin-top:14px">' + esc(s.title) + ' · ' + s.n + ' cards</p><ul class="hb-done">' + s.tries.map((t, i) => tryHtml(t, i, s.n)).join('') + '</ul>').join('') : '<p class="hb-empty">No card set done yet.</p>');
  }
  root.AneesResultsTask = { view, count, mount, gap };
})(typeof self !== 'undefined' ? self : this);
