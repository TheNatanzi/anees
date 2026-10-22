/* AI Reports page (Medi 2026-09-26): one card per research report / audit from data/ai_reports.json.
   Numbers are shown as recorded; nothing is recomputed here. Lesson numbers live on progress.html › Overview. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const badge = a => `<span class="ar-badge${a === 'Claude' ? ' ar-badge-claude' : ''}">${esc(a)}</span>`;
  const num = (v, d = 0, unit = '') => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d) + unit;
  const TYPE = { 'free-speak': 'Free speak', 'new-words': 'New words', 'new-grammar': 'New grammar', 'review-grammar': 'Grammar review', 'review-words': 'Review words' };

  // ---- 2. report cards ----------------------------------------------------------------------
  function card(p) {
    const link = (p.links || [])[0];
    const title = link ? `<a href="${esc(link.url)}">${esc(p.title)}</a>` : esc(p.title);
    const kpis = (p.numbers || []).map(n => `<div class="ar-kpi"><div class="ab-number">${esc(n.value)}</div><div class="ab-metric-label">${esc(n.label)}</div>${n.note ? `<div class="ab-tiny">${esc(n.note)}</div>` : ''}</div>`).join('');
    const bars = (p.bars && p.bars.length) ? `<div class="ar-bars"><span class="vp-eyebrow">${esc(p.bars_title || '')}</span>${p.bars.map(b => `<div class="ar-brow"><span>${esc(b.label)}</span><div class="ar-track"><div class="ar-fill${b.tone ? ' ' + esc(b.tone) : ''}" style="width:${Math.max(2, Math.round(100 * b.value / (b.max || 1)))}%"></div></div><span class="ar-bv">${esc(b.text ?? b.value)}</span></div>`).join('')}</div>` : '';
    const links = (p.links || []).map(l => `<a class="ar-btn" href="${esc(l.url)}">${esc(l.label)}</a>`).join('');
    // PG-55 chapter links; de-word: they open from one tap
    const chapters = (p.chapters || []).length ? `<details class="dw-fold ar-chap"><summary>${p.chapters.length} chapters</summary><nav class="ar-jump ar-chapters" aria-label="Jump into the study">${p.chapters.map(c => `<a href="${esc(c.url)}">${esc(c.label)}</a>`).join('')}</nav></details>` : '';
    // De-word (2026-10-22): a short first sentence of the answer stays in view; a long one, the question and the rest open in place (ⓘ).
    const v = String(p.verdict || ''), cut = v.search(/[.!?](\s|$)/), first = cut > 0 ? v.slice(0, cut + 1) : v, long = first.split(/\s+/).length > 14;
    const head = long ? '' : first, rest = long ? v : (cut > 0 ? v.slice(cut + 1).trim() : '');
    const info = (p.question || rest) ? `<details class="dw-info"><summary aria-label="The question and the full answer">ⓘ</summary><div>${p.question ? `<p class="ar-q">${esc(p.question)}</p>` : ''}${rest ? `<p>${esc(rest)}</p>` : ''}</div></details>` : '';
    return `<article class="ar-rep"><div class="ar-top">${badge(p.author)}<span class="ar-date">${esc(p.date)}</span></div><h2 class="ar-title">${title}</h2><p class="ar-verdict${head ? '' : ' ar-verdict-min'}">${esc(head)} ${info}</p>${kpis ? `<div class="ar-kpis">${kpis}</div>` : ''}${bars}${chapters}<div class="ar-links">${links}</div></article>`;
  }
  function reports(r) {
    const reps = (r.reports || []).slice().sort((a, b) => String(b.date).localeCompare(String(a.date)));
    const by = {}; for (const p of reps) by[p.author] = (by[p.author] || 0) + 1;
    const latest = reps.map(p => p.date).sort().pop() || '—';
    $('#ab-metrics').innerHTML = [['Reports', reps.length, 'Research write-ups'], ['By Claude', by.Claude || 0, 'Audits'], ['By Codex', by.Codex || 0, 'Tests and bake-offs'], ['Latest', latest, 'Newest report'], ['Engine we use', 'ElevenLabs', 'Scribe v2 · the teal bars'], ['Frozen clips', '20', 'Same audio for every engine test']]
      .map(([l, v, n]) => `<div class="ab-metric"><div class="ab-metric-label">${esc(l)}</div><div class="ab-number">${esc(v)}</div><div class="ab-tiny">${esc(n)}</div></div>`).join('');
    const papers = reps.filter(p => p.featured);   // Medi 2026-10-19: a Research section for experiments and results, like a research paper
    if (papers.length && $('#ar-papers')) { $('#ar-papers-list').innerHTML = papers.map(card).join(''); $('#ar-papers').hidden = false; }
    const past = reps.filter(p => !p.featured);   // de-word 2026-10-22: older reports fold into one tap
    $('#ar-list').innerHTML = past.length ? `<details class="ar-past"><summary>Past reports <span class="ab-count">${past.length}</span></summary><div class="ar-list">${past.map(card).join('')}</div></details>` : '<div class="vp-notice">No reports yet.</div>';
    $('#ar-foot').innerHTML = `Updated ${esc(r.updated)} <details class="dw-info"><summary aria-label="About these numbers">ⓘ</summary><div>Engine numbers (Sept 4–5) are counts on 20 frozen clips, not accuracy; the process audit counts hand-audited rows.</div></details>`;
  }

  async function main() {
    const get = u => fetch(u, { cache: 'no-store' }).then(x => x.ok ? x.json() : Promise.reject(x.status));
    try { reports(await get('data/ai_reports.json')); } catch (e) { $('#ar-list').innerHTML = '<div class="vp-notice">ai_reports.json could not load. Refresh to retry.</div>'; }
    $('#ab-source').textContent = 'Source: data/ai_reports.json';
  }
  main();
})();
