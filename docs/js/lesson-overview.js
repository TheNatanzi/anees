/* Progress & Stats › Overview (Medi 2026-09-26): the per-lesson numbers the hourly job already computes
   (docs/data/lessons.json), shown as recorded. Moved here from the AI Reports page the same day.
   Overview audit 2026-09-27 (Medi: "fix the bugs"): averages are pooled totals, not means of percentages;
   "≈" marks a number measured over part of the lesson or not comparable across recording set-ups, with the
   reason in the title (hover). Every number is computed from the file; missing renders "—". */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ok = v => v !== null && v !== undefined && !Number.isNaN(Number(v));
  const num = (v, d = 0, unit = '') => ok(v) ? Number(v).toFixed(d) + unit : '—';
  const mmss = s => { s = Math.round(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dm = d => { const [, m, dd] = String(d).split('-').map(Number); return `${MON[m - 1]} ${dd}`; };
  const sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
  const TYPE = { 'free-speak': 'Free speak', 'new-words': 'New words', 'new-grammar': 'New grammar', 'review-words': 'Review words' };
  const EDGE = 60;   // s: a talk window that starts later or ends earlier than this is "part of the lesson"

  // Same filled-pause test as scripts/build_lessons_page_data.py is_filler(); used only when lessons.json predates
  // fillers.comparable (the hourly job writes it now), so the mark never waits for the next hourly run.
  const FL = new Set(['uh', 'um', 'umm', 'uhm', 'uhh', 'er', 'erm', 'eh', 'mm', 'mmm', 'hmm', 'hm', 'mhm', 'ah']);
  const FA = new Set(['ام', 'امم', 'اممم', 'إم', 'إمم', 'أمم', 'أممم', 'مم', 'ممم', 'آآ', 'آآآ', 'آآآآ', 'أآ', 'أآآ', 'اا', 'ااا', 'آ', 'إه', 'اه', 'آه', 'اهه', 'آهه']);
  const YES = new Set(['اه', 'آه']);   // also "yes": counted only mid-turn
  const norm = t => String(t).toLowerCase().replace(/[^\p{L}\p{N}_؀-ۿ]+/gu, '').replace(/ـ/g, '');
  const isFiller = (tok, pos) => { const n = norm(tok); if (!n) return false; if (FL.has(n)) return true; if (/^(?:[آاأ]{2,}|[آاأ]?م{2,}|ه?م{2,})$/.test(n)) return true; return FA.has(n) && !(YES.has(n) && pos === 0); };
  const countFillers = txt => window.AneesLessonMath ? window.AneesLessonMath.countFillers(txt) : String(txt || '').replace(/،/g, ' ').split(/\s+/).filter(Boolean).reduce((s, t, i) => s + (isFiller(t, i) ? 1 : 0), 0);

  function row(l) {
    const g = (k, ...path) => path.reduce((o, p) => (o && o[p] !== undefined) ? o[p] : null, l[k]);
    const dur = ok(l.duration_min) ? l.duration_min * 60 : null;
    const win = l.talk && Array.isArray(l.talk.window) && l.talk.window.length === 2 ? l.talk.window : null;
    const partial = !!(win && dur && (win[0] > EDGE || win[1] < dur - EDGE));
    const winNote = (l.notes || []).find(n => /measured from/.test(n)) || '';
    const winTitle = partial ? `measured from ${mmss(win[0])} to ${mmss(win[1])} of the ${mmss(dur)} lesson${winNote ? ' · ' + winNote : ''}` : '';
    const test = !!(l.talk && l.talk.estimate);
    const testTitle = test ? 'estimate: the engine gave no word times, so talk is measured from each person’s own recording (silence detection)' : '';
    const fcmp = l.fillers ? l.fillers.comparable : undefined;   // true / false / undefined = not known yet
    const fTitle = fcmp === false ? `not comparable: this lesson’s page turns carry ${num(g('fillers', 'in_turns'))} of the ${num(g('fillers', 'count'))} filled pauses the engine heard, so the recording or its cleaning differs from the other lessons` : testTitle;
    const taught = (l.taught || []).filter(x => !x.review), reviewed = (l.taught || []).filter(x => x.review);
    const verbs = [taught.length ? `New verbs (${taught.length}): ${taught.map(x => x.latin).join(' · ')}` : 'New verbs: none',
      reviewed.length ? `Reviewed (${reviewed.length}): ${reviewed.map(x => x.latin).join(' · ')}` : ''].filter(Boolean).join('\n');
    return { date: l.date, type: TYPE[l.type] || l.type || '—', min: l.duration_min, speak: g('talk', 'speak_pct'), wpm: g('flow', 'wpm'),
      vocab: g('words', 'pct'), grammar: g('grammar', 'pct'), gest: !!(l.grammar && l.grammar.estimate), test, testTitle, partial, winTitle,
      // Medi's decision 4 (2026-09-29): scores from a lesson that is not verified carry "≈" and the reasons
      unver: LM.approx([l]), relTitle: LM.why([l]),
      fillers: g('fillers', 'per_min'), fcmp, fTitle, wait: g('latency', 'median_s'), verbs, page: l.page || ('lessons/' + l.date + '.html') };
  }

  const LM = window.AneesLessonMath;
  function render(L) {
    const ls = (L.lessons || []).slice().sort((a, b) => b.date.localeCompare(a.date));
    const rows = ls.map(row);
    const last = rows[0] || {};
    // Pooled averages = totals over the lessons, never a mean of per-lesson percentages (Overview audit 2026-09-27).
    // one formula for every page (docs/js/lesson-math.js, eng audit 2026-09-29)
    const PW = LM.pooledWords(ls), PG = LM.pooledGrammar(ls);
    const W = PW.lessons, wS = PW.scored, wR = PW.points, vocabAvg = PW.pct;
    const G = PG.lessons, gU = PG.uses, gM = PG.slips, grammarAvg = PG.pct;
    const gEst = ls.length - G.length - ls.filter(l => !(l.grammar && ok(l.grammar.uses) && l.grammar.uses > 0)).length;
    const lastL = ls[0];
    const F = ls.filter(l => l.flow && ok(l.flow.wpm) && l.flow.wpm > 0 && ok(l.flow.arabic_words));
    const fW = sum(F, l => l.flow.arabic_words), fMin = sum(F, l => l.flow.arabic_words / l.flow.wpm);
    const wpmAvg = fMin ? fW / fMin : null;
    const P = ls.filter(l => l.fillers && ok(l.fillers.count) && l.fillers.comparable !== false && l.talk && ok(l.talk.medi_s) && l.talk.medi_s > 0);
    const fillAvg = P.length ? sum(P, l => l.fillers.count) / (sum(P, l => l.talk.medi_s) / 60) : null;
    const hours = sum(ls.filter(l => ok(l.duration_min)), l => l.duration_min) / 60;
    const approx = (r, flag) => flag ? '≈ ' : '';
    const metrics = [
      ['Lessons tracked', String(rows.length), `lessons.json · one row per lesson · ${num(hours, 1)} h of audio`, 'The same file feeds the Lessons and Lesson hours cards at the top of the page.'],
      ['Last lesson', last.date || '—', last.type || ''],
      ['Vocab right', (last.unver ? '≈' : '') + num(last.vocab, 1, '%'), `Last lesson · pooled avg ${LM.mark(num(vocabAvg, 1, '%'), W).text} · ${W.length} of ${rows.length} lessons`, `Pooled = Σ right + ½ partial ÷ Σ scored uses (${num(wR, 1)} ÷ ${wS}), the Word Bank's own weighting. A mean of the lesson percentages would let one small lesson pull it.
${LM.why(W)}`],
      ['Grammar right', ((last.unver || last.gest) ? '≈' : '') + num(last.grammar, 1, '%'), `Last lesson · pooled avg ${LM.mark(num(grammarAvg, 1, '%'), G).text} · ${G.length} of ${rows.length} lessons`, `Pooled = Σ (uses − slips) ÷ Σ uses (${gU - gM} ÷ ${gU}), same formula as the Grammar Console. ${gEst > 0 ? gEst + ' estimated lesson' + (gEst === 1 ? '' : 's') + ' ("≈") left out.' : 'No lesson left out.'}
${LM.why(G)}`],
      // Was "Medi speaking" - the Talk time card one row up already shows it. Words per minute is not shown anywhere else.
      ['Words per minute', approx(last, last.test || last.partial) + num(last.wpm, 0), `Last lesson · pooled avg ${num(wpmAvg, 0)} · ${F.length} of ${rows.length} lessons`, `Arabic words inside your Arabic turns, per minute of those turns. Pooled = Σ Arabic words ÷ Σ minutes (${fW} ÷ ${num(fMin, 1)}).${last.partial ? ' Last lesson: ' + last.winTitle : ''}${last.test ? ' Last lesson: ' + last.testTitle : ''}`],
      ['Fillers / min', approx(last, last.test || last.fcmp === false) + num(last.fillers, 1), `"uh", "um", "آآ" per minute you spoke · pooled avg ${num(fillAvg, 1)} · ${P.length} comparable lessons`, `Pooled = Σ filled pauses ÷ Σ minutes you spoke, over the lessons whose page turns keep the fillers.${last.fcmp === false ? ' Last lesson: ' + last.fTitle : ''}`]
    ];
    $('#ov-metrics').innerHTML = metrics.map(([l, v, s, t]) => `<div class="ab-metric"${t ? ` title="${esc(t)}"` : ''}><div class="ab-metric-label">${esc(l)}</div><div class="ab-number">${esc(v)}</div><div class="ab-tiny">${esc(s)}</div></div>`).join('');

    const bandc = p => { p = Math.round(p); return p >= 90 ? 'pct-a' : p >= 80 ? 'pct-b' : p >= 70 ? 'pct-c' : 'pct-d'; };   // Medi 2026-09-27 colours
    const head = ['Lesson', 'Type', 'Min', 'Speak %', 'Words/min', 'Vocab %', 'Grammar %', 'Fillers/min', 'Wait s'];
    const td = (v, mark, title, cls = '') => `<td${cls ? ` class="${cls}"` : ''}${title && ok(v) ? ` title="${esc(title)}"` : ''}>${mark && ok(v) ? '≈ ' : ''}${v}</td>`;
    $('#ov-series').innerHTML = `<div class="ov-tbl"><table><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => {
      const tt = r.partial ? r.winTitle : r.testTitle;   // one reason per talk-timing cell
      return `<tr title="${esc(r.verbs)}"><td><a href="${esc(r.page)}">${esc(r.date)}</a></td><td>${esc(r.type)}</td><td>${num(r.min, 0)}</td>` +
        td(num(r.speak, 1), r.test || r.partial, tt) + td(num(r.wpm, 0), r.test || r.partial, tt) +
        td(num(r.vocab, 1), r.unver, r.relTitle, ok(r.vocab) ? bandc(r.vocab) : '') +
        td(num(r.grammar, 1), r.unver || r.gest, [r.relTitle, r.gest ? 'estimate: every slip Amal fixed counted as a rule use' : ''].filter(Boolean).join(' · '), ok(r.grammar) ? bandc(r.grammar) : '') +
        td(num(r.fillers, 1), r.test || r.fcmp === false, r.fTitle) +
        td(num(r.wait, 1), r.test || r.partial, tt) + '</tr>';
    }).join('')}</tbody></table></div>`;

    const partialDates = rows.filter(r => r.partial).map(r => dm(r.date)), badFill = rows.filter(r => r.fcmp === false).map(r => dm(r.date));
    const pending = rows.some(r => r.fcmp === undefined && ok(r.fillers));
    $('#ov-note').textContent = `Source: data/lessons.json · updated ${String(L.updated || '').replace('T', ' ').slice(0, 16)} · Averages are pooled totals over the lessons, not a mean of the lesson percentages: Vocab = Σ right + ½ partial ÷ Σ scored uses; Grammar = Σ (uses − slips) ÷ Σ uses, estimated lessons left out; Words/min = Σ Arabic words ÷ Σ minutes. ` +
      `"≈" Vocab % and Grammar % = that lesson is not verified yet (reader agreement under 95 %, audio or speech recognition not checked, or rows waiting for a check); hover or tap for its reasons. Averages that include such a lesson are "≈" too. ` +
      `Grammar uses = rule uses the app counted plus every fixed slip no counted use pairs with, the same formula as the Grammar Console; slips in rules no counter can score are listed on the lesson but not in the %. ` +
      `"≈" Speak %, Words/min and Wait = measured over part of the lesson (hover for the window)${partialDates.length ? ': ' + partialDates.join(', ') : ''}. Sep 10 timings come from each person's own recording (the engine gave no word times). ` +
      `"≈" Fillers/min = not comparable: that lesson's page turns carry under half the filled pauses the engine heard, so its recording or cleaning differs${badFill.length ? ' (' + badFill.join(', ') + ')' : ''}${pending ? ' — still checking the turn files' : ''}; read those against each other only. ` +
      `Wait = median seconds before Medi answers. Hover a row for the verb pairs Amal taught or reviewed that day (Sep 11 was the last new pair).`;
  }

  // lessons.json written before 2026-09-27 has no fillers.comparable: derive it here from the page turns, same rule.
  async function fillComparable(L) {
    const need = (L.lessons || []).filter(l => l.fillers && ok(l.fillers.count) && l.fillers.comparable === undefined);
    if (!need.length) return false;
    await Promise.all(need.map(async l => {
      try {
        const J = await (await fetch(l.detail || ('data/lessons/' + l.date + '.json'), { cache: 'no-store' })).json();
        const n = (J.turns || []).filter(t => t.who === 'Medi').reduce((s, t) => s + countFillers(t.text), 0);
        l.fillers.in_turns = n;
        l.fillers.comparable = l.fillers.count ? n >= l.fillers.count / 2 : true;
      } catch (e) { console.warn('lesson-overview: turn file for', l.date, 'did not load; fillers left unmarked', e); }
    }));
    return true;
  }
  async function main() {
    let L;
    try { L = await (await fetch('data/lessons.json', { cache: 'no-store' })).json(); render(L); }
    catch (e) { $('#ov-series').innerHTML = '<div class="vp-notice">lessons.json could not load. Refresh to retry.</div>'; return; }
    try { if (await fillComparable(L)) render(L); } catch (e) { console.warn('lesson-overview', e); }
  }
  window.AneesLessonOverview = { main };
  main();
})();
