/* AI Reports › Grades (PG-46, Medi 2026-10-10: "make a tab in the AI reports area for the grades ... How much of the vocab
   it keeps track of; How many mistakes it made ... so that we can see if our process is actually improving").
   Reads docs/data/review-grades.json (scripts/review_grades.py). One row per lesson Medi reviewed; only full reviews are
   graded. Numbers are shown as built, nothing is recomputed here. Click a graded row to see every mistake. */
(function () {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pct = v => (v === null || v === undefined) ? '–' : Number(v).toFixed(1) + '%';
  const num = v => (v === null || v === undefined) ? '–' : String(v);
  const ORDER = ['missed_slip', 'fake_slip', 'untracked', 'misheard'];
  const SHORT = { missed_slip: 'Missed slip', fake_slip: 'Fake slip', untracked: 'Untracked / wrong credit', misheard: 'Misheard word' };
  const STATE = { credit: '✓ credit', half: '◐ half credit', repeat: '↻ repeat (no credit)', new: '★ new word', slip: '✗ mistake' };
  const said = v => esc(STATE[v] || String(v || '').replace(/^grey: /, 'grey · '));
  // "now" in the JSON is shown as Drift (overnight brief 2026-10-10): never read as an accuracy score
  const DRIFT_TIP = "today's page vs the key: a regression check only, never an accuracy score";
  // PG-50 fast review mode: his measured minutes and the share of his Arabic lines he answered (null = not reviewed that way)
  function timeCov(r) {
    const bits = [];
    if (r.minutes_medi !== null && r.minutes_medi !== undefined) bits.push(`${esc(r.minutes_medi)} min of the student's time`);
    if (r.coverage_medi !== null && r.coverage_medi !== undefined) bits.push(`${esc(r.lines_checked)} of ${esc(r.lines_total)} lines checked (${pct(100 * r.coverage_medi)})`);
    // AM-29 (Medi 2026-10-11 "mix 30-20"): the tutor's blind check of the exam's moments vs his fast-review answers
    const ac = r.amal_check;
    if (ac) bits.push(`Tutor checked ${esc(ac.answered)} of ${esc(ac.total)} moments` + (ac.compared_n
      ? ` · Tutor and student agree on ${esc(ac.agree_with_student_n)} of ${esc(ac.compared_n)} lines (${pct(ac.agreement_pct)})` : ''));
    return bits.length ? `<div class="ab-tiny rg-time">${bits.join(' · ')}</div>` : '';
  }

  function word(e) {
    const ar = e.az && e.az !== e.word ? ` <span class="rg-ar" lang="ar" dir="rtl">${esc(e.word)}</span>` : '';
    return `<b>${esc(e.az || e.word)}</b>${ar}`;
  }
  function mistakes(side) {
    const by = {}; for (const e of side.list || []) (by[e.type] = by[e.type] || []).push(e);
    return ORDER.filter(t => by[t]).map(t => `<details class="rg-type"><summary>${esc(SHORT[t])} <span class="rg-n">${by[t].length}</span></summary>
      <table class="rg-tbl"><thead><tr><th>Time</th><th>Word</th><th>The robot had</th><th>Right answer</th></tr></thead><tbody>${
        by[t].map(e => `<tr><td>${esc(e.t)}</td><td>${word(e)}</td><td>${said(e.was)}</td><td>${said(e.is)}</td></tr>`).join('')
      }</tbody></table></details>`).join('') || '<p class="ab-sub">No mistakes.</p>';
  }
  function cells(side) {
    if (!side) return '<td colspan="6">–</td>';
    const m = side.mistakes || {};
    return `<td>${pct(side.tracked_pct)}</td>${ORDER.map(t => `<td>${num(m[t])}</td>`).join('')}<td>${num(side.per_100)}</td>`;
  }
  // PR-25: a pipeline change that lost on the next exam is flagged here, never rolled back silently
  function flags(d) {
    const bad = (d.experiments || []).filter(x => x.flag);
    return bad.map(x => `<div class="vp-notice rg-flag" role="alert">⚠ ${esc(x.flag)}</div>`).join('');
  }
  function experiments(d) {
    const ex = d.experiments || [];
    if (!ex.length) return '';
    const row = x => x.both_agree
      ? `<tr><td>${esc(x.date)}</td><td>${esc(x.kind)}</td><td>both readers agree: F0.5 ${esc(x.both_agree.f05)} vs Opus alone ${esc(x.opus_alone.f05)}</td><td>${x.won ? '✓ won' : '✗ lost'}</td></tr>`
      : `<tr><td>${esc(x.date)}</td><td>hearing test ${esc((x.lessons || []).join(' + '))}</td><td>winner: ${esc((x.winner || ['none (today’s way stays)']).join(', '))}</td><td>${x.adopted ? 'adopted' : 'not adopted'}</td></tr>`;
    return `<details class="rg-type rg-exp"><summary>Pipeline tests <span class="rg-n">${ex.length}</span></summary>
      <table class="rg-tbl"><thead><tr><th>Date</th><th>Test</th><th>Result</th><th>Outcome</th></tr></thead><tbody>${ex.map(row).join('')}</tbody></table></details>`;
  }
  // PR-25: slips only one of the two readers flagged - held, never a mistake chip
  function held(d) {
    const h = d.reader_held || [];
    if (!h.length) return '';
    return `<details class="rg-type rg-held"><summary>Held: one reader only <span class="rg-n">${h.length}</span></summary>
      <p class="ab-sub">Only one of the two slip readers flagged these, so they are not shown as mistakes.</p>
      <table class="rg-tbl"><thead><tr><th>Lesson</th><th>Time</th><th>Kind</th><th>He said</th><th>Right form</th><th>Flagged by</th></tr></thead><tbody>${
        h.map(x => `<tr><td>${esc(x.date)}</td><td>${esc(x.t)}</td><td>${esc(x.kind)}</td><td lang="ar" dir="auto">${esc(x.wrong)}</td><td lang="ar" dir="auto">${esc(x.right)}</td><td>${esc(x.flagged_by)}</td></tr>`).join('')
      }</tbody></table></details>`;
  }
  function render(host, d) {
    const rows = d.lessons || [];
    const graded = rows.filter(r => r.status === 'graded');
    const last = graded[graded.length - 1];
    const kpi = (v, l, n) => `<div class="ar-kpi"><div class="ab-number">${esc(v)}</div><div class="ab-metric-label">${esc(l)}</div>${n ? `<div class="ab-tiny">${esc(n)}</div>` : ''}</div>`;
    const kpis = last ? [
      kpi(pct(last.before.tracked_pct), 'Words tracked', `${last.before.tracked} of ${last.before.words} Arabic words · ${last.date}, the robot's first version`),
      kpi(num(last.before.per_100), 'Mistakes per 100 words', `${last.before.mistakes_total} mistakes · ${last.date}, first version`),
      kpi(pct(last.now.tracked_pct), 'Drift', `${DRIFT_TIP}; ${last.now.mistakes_total} differences from the key`),
      kpi(graded.length, 'Lessons graded', 'full reviews only')
    ].join('') : '';
    const trend = graded.length > 1
      ? `<div class="ar-bars"><span class="vp-eyebrow">Words tracked, first version, by lesson</span>${graded.map(r => `<div class="ar-brow"><span>${esc(r.date)}</span><div class="ar-track"><div class="ar-fill" style="width:${Math.max(2, Math.round(r.before.tracked_pct || 0))}%"></div></div><span class="ar-bv">${pct(r.before.tracked_pct)}</span></div>`).join('')}</div>`
      : '<p class="ab-sub rg-note">Trend: starts with the next full review (one graded lesson so far).</p>';
    const head = `<tr><th>Lesson</th><th>Version</th><th>Arabic words</th><th>Tracked</th>${ORDER.map(t => `<th>${esc(SHORT[t])}</th>`).join('')}<th>Per 100 words</th></tr>`;
    const body = rows.slice().reverse().map(r => {
      if (r.status !== 'graded') return `<tr class="rg-partial"><td>${esc(r.date)}${timeCov(r)}</td><td colspan="${3 + ORDER.length + 1}">${esc(r.status)}${r.note ? ' · ' + esc(r.note) : ''}</td></tr>`;
      return `<tr class="rg-row" data-date="${esc(r.date)}" data-side="before" tabindex="0"><td rowspan="2"><b>${esc(r.date)}</b>${timeCov(r)}</td><td>First version <span class="ab-tiny">${esc(r.before_commit)}</span></td><td>${num(r.before.words)}</td>${cells(r.before)}</tr>
        <tr class="rg-row" data-date="${esc(r.date)}" data-side="now" tabindex="0" title="${esc(DRIFT_TIP)}"><td>Drift <span class="ab-tiny">${esc(DRIFT_TIP)}</span></td><td>${num(r.now.words)}</td>${cells(r.now)}</tr>`;
    }).join('');
    host.innerHTML = `${kpis ? `<div class="ar-kpis">${kpis}</div>` : ''}${flags(d)}${trend}
      <div class="ar-tbl"><table>${head}${body}</table></div>${experiments(d)}${held(d)}
      <div id="rg-detail" class="rg-detail"><p class="ab-sub">Click a row to see every mistake, with its time and word.</p></div>
      <p class="ar-foot">Only Arabic words of the student's own lines count: English, fillers, sounds and the pronouns ana / inta / heyye are out; Arabic he said in English letters counts; cut-off words and prepositions (graded as grammar) are out. The answer key is the lesson after his review. Only lessons he reviewed in full get a grade.</p>`;
    const open = tr => {
      const r = rows.find(x => x.date === tr.dataset.date); const side = r && r[tr.dataset.side];
      if (!side) return;
      host.querySelectorAll('.rg-row').forEach(x => x.classList.toggle('rg-on', x === tr));
      document.getElementById('rg-detail').innerHTML = `<h3 class="rg-h3">${esc(r.date)} · ${tr.dataset.side === 'now' ? 'drift (' + esc(DRIFT_TIP) + ')' : 'first version'}: ${side.mistakes_total} ${tr.dataset.side === 'now' ? 'differences from the key' : 'mistakes'} in ${side.words} Arabic words</h3>${mistakes(side)}`;
    };
    host.querySelectorAll('.rg-row').forEach(tr => {
      tr.onclick = () => open(tr);
      tr.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(tr); } };
    });
  }
  async function mount(host) {
    try {
      const d = await fetch('data/review-grades.json?build=' + encodeURIComponent(window.ANEES_BUILD || ''), { cache: 'no-store' }).then(x => x.ok ? x.json() : Promise.reject(x.status));
      render(host, d);
    } catch (e) { host.innerHTML = '<div class="vp-notice">The grade book could not load.</div>'; }
  }
  window.AneesReviewGrades = { mount, render };
})();
