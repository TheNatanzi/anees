/* AI Reports page (Medi 2026-09-26): two parts.
   1. "Tracked every hour": the per-lesson numbers the hourly job already computes (data/lessons.json).
   2. "Reports": one card per research report / audit from data/ai_reports.json.
   Numbers are shown as recorded; nothing is recomputed here. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const badge = a => `<span class="ar-badge${a === 'Claude' ? ' ar-badge-claude' : ''}">${esc(a)}</span>`;
  const num = (v, d = 0, unit = '') => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d) + unit;
  const TYPE = { 'free-speak': 'Free speak', 'new-words': 'New words', 'new-grammar': 'New grammar', 'review-words': 'Review words' };

  // ---- 1. tracked series --------------------------------------------------------------------
  function lessonRow(l) {
    const g = (k, ...path) => path.reduce((o, p) => (o && o[p] !== undefined) ? o[p] : null, l[k]);
    return {
      date: l.date, type: TYPE[l.type] || l.type || '—', min: l.duration_min,
      speak: g('talk', 'speak_pct'), wpm: g('flow', 'wpm'), vocab: g('words', 'pct'), grammar: g('grammar', 'pct'),
      fillers: g('fillers', 'per_min'), wait: g('latency', 'median_s'), taught: (l.taught || []).length,
      page: l.page || ('lessons/' + l.date + '.html')
    };
  }
  function tracked(L) {
    const rows = (L.lessons || []).map(lessonRow).sort((a, b) => b.date.localeCompare(a.date));
    const last = rows[0] || {};
    const n = rows.length, avg = k => { const v = rows.map(r => r[k]).filter(x => x !== null && x !== undefined); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
    $('#ab-metrics').innerHTML = [
      ['Lessons tracked', n, 'Every transcript, hourly'],
      ['Last lesson', last.date || '—', last.type || ''],
      ['Vocab right', num(last.vocab, 1, '%'), 'Last lesson · avg ' + num(avg('vocab'), 1, '%')],
      ['Grammar right', num(last.grammar, 1, '%'), 'Last lesson · avg ' + num(avg('grammar'), 1, '%')],
      ['Medi speaking', num(last.speak, 1, '%'), 'Share of talk time'],
      ['Fillers / min', num(last.fillers, 1), '"uh", "um", "آآ" per minute']
    ].map(([l, v, s]) => `<div class="ab-metric"><div class="ab-metric-label">${esc(l)}</div><div class="ab-number">${esc(v)}</div><div class="ab-tiny">${esc(s)}</div></div>`).join('');
    const head = ['Lesson', 'Type', 'Min', 'Speak %', 'Words/min', 'Vocab %', 'Grammar %', 'Fillers/min', 'Wait s', 'Taught'];
    $('#ar-series').innerHTML = `<div class="ar-tbl"><table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r =>
      `<tr><td><a href="${esc(r.page)}">${esc(r.date)}</a></td><td>${esc(r.type)}</td><td>${num(r.min, 0)}</td><td>${num(r.speak, 1)}</td><td>${num(r.wpm, 0)}</td><td>${num(r.vocab, 1)}</td><td>${num(r.grammar, 1)}</td><td>${num(r.fillers, 1)}</td><td>${num(r.wait, 2)}</td><td>${r.taught || '—'}</td></tr>`).join('')}</tbody></table></div>`;
    $('#ar-series-note').textContent = `Source: data/lessons.json · updated ${String(L.updated || '').replace('T', ' ').slice(0, 16)} · "—" = not measured for that lesson (missing audio track or no scored rows). Wait = median seconds before Medi answers.`;
  }

  // ---- 2. report cards ----------------------------------------------------------------------
  function card(p) {
    const link = (p.links || [])[0];
    const title = link ? `<a href="${esc(link.url)}">${esc(p.title)}</a>` : esc(p.title);
    const kpis = (p.numbers || []).map(n => `<div class="ar-kpi"><div class="ab-number">${esc(n.value)}</div><div class="ab-metric-label">${esc(n.label)}</div>${n.note ? `<div class="ab-tiny">${esc(n.note)}</div>` : ''}</div>`).join('');
    const bars = (p.bars && p.bars.length) ? `<div class="ar-bars"><span class="vp-eyebrow">${esc(p.bars_title || '')}</span>${p.bars.map(b => `<div class="ar-brow"><span>${esc(b.label)}</span><div class="ar-track"><div class="ar-fill${b.tone ? ' ' + esc(b.tone) : ''}" style="width:${Math.max(2, Math.round(100 * b.value / (b.max || 1)))}%"></div></div><span class="ar-bv">${esc(b.text ?? b.value)}</span></div>`).join('')}</div>` : '';
    const links = (p.links || []).map(l => `<a class="ar-btn" href="${esc(l.url)}">${esc(l.label)}</a>`).join('');
    return `<article class="ar-rep"><div class="ar-top">${badge(p.author)}<span class="ar-date">${esc(p.date)}</span></div><h2 class="ar-title">${title}</h2><p class="ar-q">${esc(p.question)}</p><p class="ar-verdict">${esc(p.verdict)}</p>${kpis ? `<div class="ar-kpis">${kpis}</div>` : ''}${bars}<div class="ar-links">${links}</div></article>`;
  }
  function reports(r) {
    const reps = (r.reports || []).slice().sort((a, b) => String(b.date).localeCompare(String(a.date)));
    const by = {}; for (const p of reps) by[p.author] = (by[p.author] || 0) + 1;
    $('#ar-reports-count').textContent = `${reps.length} reports · ${by.Claude || 0} Claude · ${by.Codex || 0} Codex`;
    $('#ar-list').innerHTML = reps.map(card).join('') || '<div class="vp-notice">No reports yet.</div>';
    $('#ar-foot').textContent = `Updated ${r.updated}. Engine numbers (Sept 4–5) are counts on 20 frozen clips, not accuracy; the process audit counts hand-audited rows.`;
  }

  async function main() {
    const get = u => fetch(u, { cache: 'no-store' }).then(x => x.ok ? x.json() : Promise.reject(x.status));
    const [L, R] = await Promise.allSettled([get('data/lessons.json'), get('data/ai_reports.json')]);
    if (L.status === 'fulfilled') tracked(L.value); else $('#ar-series').innerHTML = '<div class="vp-notice">lessons.json could not load. Refresh to retry.</div>';
    if (R.status === 'fulfilled') reports(R.value); else $('#ar-list').innerHTML = '<div class="vp-notice">ai_reports.json could not load. Refresh to retry.</div>';
    $('#ab-source').textContent = 'Source: lessons.json (hourly) + ai_reports.json';
  }
  main();
})();
