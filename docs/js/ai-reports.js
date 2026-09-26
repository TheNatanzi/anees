/* AI Reports page (Medi 2026-09-26): one card per research report from data/ai_reports.json,
   in the Word Bank skin. Numbers shown are the ones the report recorded; nothing is recomputed here. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const badge = a => `<span class="ar-badge${a === 'Claude' ? ' ar-badge-claude' : ''}">${esc(a)}</span>`;

  function metrics(r) {
    const reps = r.reports || [], by = {};
    for (const p of reps) by[p.author] = (by[p.author] || 0) + 1;
    const latest = reps.map(p => p.date).sort().pop() || '—';
    const m = [
      ['Reports', reps.length, 'Research write-ups'],
      ['By Claude', by.Claude || 0, 'Adversarial audits'],
      ['By Codex', by.Codex || 0, 'Tests and bake-offs'],
      ['Latest', latest, 'Newest report'],
      ['Engine we use', 'ElevenLabs', 'Scribe v2 · the teal bars'],
      ['Frozen clips', '20', 'Same audio for every test']
    ];
    $('#ab-metrics').innerHTML = m.map(([l, v, n]) => `<div class="ab-metric"><div class="ab-metric-label">${esc(l)}</div><div class="ab-number">${esc(v)}</div><div class="ab-tiny">${esc(n)}</div></div>`).join('');
  }

  function card(p) {
    const link = (p.links || [])[0];
    const title = link ? `<a href="${esc(link.url)}">${esc(p.title)}</a>` : esc(p.title);
    const kpis = (p.numbers || []).map(n => `<div class="ar-kpi"><div class="ab-number">${esc(n.value)}</div><div class="ab-metric-label">${esc(n.label)}</div>${n.note ? `<div class="ab-tiny">${esc(n.note)}</div>` : ''}</div>`).join('');
    const bars = (p.bars && p.bars.length) ? `<div class="ar-bars"><span class="vp-eyebrow">${esc(p.bars_title || '')}</span>${p.bars.map(b => `<div class="ar-brow"><span>${esc(b.label)}</span><div class="ar-track"><div class="ar-fill${b.tone ? ' ' + esc(b.tone) : ''}" style="width:${Math.max(2, Math.round(100 * b.value / (b.max || 1)))}%"></div></div><span class="ar-bv">${esc(b.text ?? b.value)}</span></div>`).join('')}</div>` : '';
    const links = (p.links || []).map(l => `<a class="ar-btn" href="${esc(l.url)}">${esc(l.label)}</a>`).join('');
    return `<article class="ar-rep"><div class="ar-top">${badge(p.author)}<span class="ar-date">${esc(p.date)}</span></div><h2 class="ar-title">${title}</h2><p class="ar-q">${esc(p.question)}</p><p class="ar-verdict">${esc(p.verdict)}</p>${kpis ? `<div class="ar-kpis">${kpis}</div>` : ''}${bars}<div class="ar-links">${links}</div></article>`;
  }

  async function main() {
    let r = null;
    try { r = await (await fetch('data/ai_reports.json', { cache: 'no-store' })).json(); } catch (e) {}
    const el = $('#ar-list');
    if (!r) { el.innerHTML = '<div class="vp-notice">ai_reports.json could not load. Refresh to retry.</div>'; return; }
    metrics(r);
    const reps = (r.reports || []).slice().sort((a, b) => String(b.date).localeCompare(String(a.date)));
    el.innerHTML = reps.map(card).join('') || '<div class="vp-notice">No reports yet.</div>';
    $('#ar-foot').textContent = `Updated ${r.updated}. Numbers are counts on frozen clips, not accuracy; no word-perfect transcript exists yet.`;
    $('#ab-source').textContent = 'Source: data/ai_reports.json';
  }
  main();
})();
