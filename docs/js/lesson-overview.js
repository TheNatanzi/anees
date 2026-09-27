/* Progress & Stats › Overview (Medi 2026-09-26): the per-lesson numbers the hourly job already computes
   (docs/data/lessons.json), shown as recorded. Moved here from the AI Reports page the same day. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v, d = 0, unit = '') => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d) + unit;
  const TYPE = { 'free-speak': 'Free speak', 'new-words': 'New words', 'new-grammar': 'New grammar', 'review-words': 'Review words' };

  function row(l) {
    const g = (k, ...path) => path.reduce((o, p) => (o && o[p] !== undefined) ? o[p] : null, l[k]);
    return { date: l.date, type: TYPE[l.type] || l.type || '—', min: l.duration_min, speak: g('talk', 'speak_pct'), wpm: g('flow', 'wpm'),
      vocab: g('words', 'pct'), grammar: g('grammar', 'pct'), gest: !!(l.grammar && l.grammar.estimate), test: !!(l.talk && l.talk.estimate), fillers: g('fillers', 'per_min'), wait: g('latency', 'median_s'),
      taught: (l.taught || []).filter(x => !x.review).length, reviewed: (l.taught || []).filter(x => x.review).length, page: l.page || ('lessons/' + l.date + '.html') };
  }
  function render(L) {
    const rows = (L.lessons || []).map(row).sort((a, b) => b.date.localeCompare(a.date));
    const last = rows[0] || {};
    const avg = k => { const v = rows.map(r => r[k]).filter(x => x !== null && x !== undefined); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
    $('#ov-metrics').innerHTML = [
      ['Lessons tracked', rows.length, 'Every transcript, hourly'],
      ['Last lesson', last.date || '—', last.type || ''],
      ['Vocab right', num(last.vocab, 1, '%'), 'Last lesson · avg ' + num(avg('vocab'), 1, '%')],
      ['Grammar right', num(last.grammar, 1, '%'), 'Last lesson · avg ' + num(avg('grammar'), 1, '%')],
      ['Medi speaking', num(last.speak, 1, '%'), 'Share of talk time'],
      ['Fillers / min', num(last.fillers, 1), '"uh", "um", "آآ" per minute']
    ].map(([l, v, s]) => `<div class="ab-metric"><div class="ab-metric-label">${esc(l)}</div><div class="ab-number">${esc(v)}</div><div class="ab-tiny">${esc(s)}</div></div>`).join('');
    const head = ['Lesson', 'Type', 'Min', 'Speak %', 'Words/min', 'Vocab %', 'Grammar %', 'Fillers/min', 'Wait s', 'New verbs'];
    $('#ov-series').innerHTML = `<div class="ov-tbl"><table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r =>
      `<tr><td><a href="${esc(r.page)}">${esc(r.date)}</a></td><td>${esc(r.type)}</td><td>${num(r.min, 0)}</td><td>${r.test && r.speak != null ? '≈ ' : ''}${num(r.speak, 1)}</td><td>${r.test && r.wpm != null ? '≈ ' : ''}${num(r.wpm, 0)}</td><td>${num(r.vocab, 1)}</td><td${r.gest ? ' title="estimate: every slip Amal fixed counted as a rule use"' : ''}>${r.gest && r.grammar != null ? '≈ ' : ''}${num(r.grammar, 1)}</td><td>${r.test && r.fillers != null ? '≈ ' : ''}${num(r.fillers, 1)}</td><td>${r.test && r.wait != null ? '≈ ' : ''}${num(r.wait, 2)}</td><td title="${r.reviewed ? r.reviewed + ' reviewed from earlier lessons' : ''}">${r.taught || (r.reviewed ? '0 · ' + r.reviewed + ' reviewed' : '0')}</td></tr>`).join('')}</tbody></table></div>`;
    $('#ov-note').textContent = `Source: data/lessons.json · updated ${String(L.updated || '').replace('T', ' ').slice(0, 16)} · Sep 10 timings come from each person's own recording (the engine gave no word times). "≈" Grammar % = an estimate: the app counted fewer rule uses than Amal fixed slips (it cannot read turns the speech engine wrote in Latin letters), so each fixed slip is counted as a use too. New verbs = verb pairs Amal taught for the first time (Sep 11 was the last); "reviewed" = pairs from earlier lessons. Wait = median seconds before Medi answers.`;
  }
  async function main() {
    try { render(await (await fetch('data/lessons.json', { cache: 'no-store' })).json()); }
    catch (e) { $('#ov-series').innerHTML = '<div class="vp-notice">lessons.json could not load. Refresh to retry.</div>'; }
  }
  window.AneesLessonOverview = { main };
  main();
})();
