// Flashcard audit (docs/flashcard-rules.md). Runs INSIDE docs/cards.html (it uses the page's own faces / enFull / hasPl),
// so it checks exactly what Medi sees. Paste into the browser console on the Flashcards page, or run through the preview
// tool, after the page has loaded. Returns {total, bySource, plural, issues}; issues should be {} (empty). Last run 2026-10-01: 6,048 cards (Doc 2,154 · Quizlet-only 1,158 · drills 2,736), 291 plural cards, issues {}.
// Covers all three card sources (Doc words, Quizlet-only cards, verb-drill forms) in BOTH modes (Arabic first, English first).
// 2026-10-01: plural checks P0-P5 added (every plural shows on both sides; every Quizlet way of writing a plural is caught).
(async () => {
  for (let i = 0; i < 40 && !(serverLog.length && quizlet.length); i++) await new Promise(r => setTimeout(r, 500));
  const T = window.AneesTest, W = T.words, el = h => { const d = document.createElement('div'); d.innerHTML = h; return d; };
  const match = SEL.matcher(W), qAll = quizlet.flatMap(s => SEL.quizletCards(s, match).map(c => ({ c, set: s })));
  const qOnly = qAll.filter(x => SEL.isQuizletOnly(x.c.key)).map(x => x.c);
  const drills = VD.round(selection().drills, { mode: 'full', count: 500, tense: 'All', level: 1 });
  const cards = [...W.map(w => ({ w, src: 'Doc' })), ...qOnly.map(w => ({ w, src: 'Quizlet' })), ...drills.map(w => ({ w, src: 'Drill' }))];
  const issues = {}, add = (k, ex) => (issues[k] = issues[k] || []).push(ex), mode0 = T.pref.mode;
  const plural = { cards: 0, bothSides: 0, arabicOnlyByRule: {}, quizletOnly: 0 };
  const why = k => (plural.arabicOnlyByRule[k] = (plural.arabicOnlyByRule[k] || 0) + 1);
  const txt = (h, sel) => { const n = el(h).querySelector(sel); return n ? n.innerText : ''; };
  // F5: why a plural card has no English plural (each reason is a rule; anything else is a bug).
  const noEnReason = w => {
    const e = String(enBase(w) || ''), parts = splitTop(e); if (isCmd(w)) return 'command';
    if (!parts.length) return 'no English';
    if (/\?/.test(e)) return 'question';
    if (parts.every(p => p.split(/\s+/).length > 4)) return '5+ words';
    if (parts.every(p => /\((progressive|command)\)/i.test(p))) return '(progressive)';
    if (parts.every(p => EN_SAME.has(enBare(p)) || /^(sheep|deer|fish)$/i.test(enBare(p)))) return 'uncountable / same word';
    if (parts.every(p => !enPlural(p))) return 'already plural / adjective';
    return '';
  };
  for (const { w, src } of cards) {
    const ft = {};
    for (const m of ['ar_first', 'en_first']) {
      T.pref.mode = m;
      try { const [f, b] = faces(w), [a, e] = m === 'ar_first' ? [f, b] : [b, f]; ft[m] = { A: txt(a, '.big'), E: txt(e, '.en'), front: f }; }
      catch (e) { add('card crashes', w.key + ' ' + e.message); }
    }
    if (!ft.ar_first || !ft.en_first) continue;
    const { A, E } = ft.ar_first;
    if (A !== ft.en_first.A || E !== ft.en_first.E) add('P0 modes show different faces', w.key);
    if (!el(ft.en_first.front).querySelector('.en')) add('P0 English-first front is not English', w.key);
    if (src === 'Drill' && (A + E).includes(' · ')) add('F11 drill shows " · "', E);
    if (/^\s*\d+\s*$/.test(w.arabizi || '')) add('F9 number-only front', w.arabizi);
    if (isCmd(w) && !/!/.test(E)) add('F8 command not marked', w.english);
    if (hasPl(w)) {
      // P1: every plural shows on the Arabic side as singular · plural
      plural.cards++; if (src === 'Quizlet') plural.quizletOnly++;
      if (!A.includes(' · ')) add('P1 plural missing on the Arabic side', w.arabizi);
      else if (A.split(' · ').length !== 2) add('P1 " · " used twice (Arabic)', A);
      // P2: the English side shows singular · plural too, unless an F5 rule leaves it out
      if (E.includes(' · ')) { plural.bothSides++; if (E.split(' · ').length !== 2) add('P2 " · " used twice (English)', E);
        const [sgSide, plSide] = E.split(' · '), irr = new Set(Object.values(EN_IRR));
        if (/\s[–-]\s/.test(E)) add('P2 Amal\'s "X – Xs" left half-converted', E);
        // a singular sitting on the plural side ("Letter · letters / preposition"): it would still pluralize
        const made = new Set(splitTop(sgSide).map(x => enPlural(x).toLowerCase()).concat(String(EN_PL[enBase(w).toLowerCase().replace(/\s+/g, ' ').trim()] || '').toLowerCase().split(' / ')));
        for (const p of splitTop(plSide || '')) { const last = (p.replace(/\s*\(.*$/s, '').match(/[A-Za-z]+$/) || [''])[0].toLowerCase(), g = enPlural(p);
          if (!made.has(p.toLowerCase()) && g && g.toLowerCase() !== p.toLowerCase() && ![...irr].some(v => last.endsWith(v))) add('P2 singular on the English plural side', E); }
        if (splitTop(sgSide).length < splitTop(plSide || '').length) add('P2 more English plurals than singulars', E); }
      else { const r = noEnReason(w); if (r) why(r); else add('P2 plural missing on the English side', w.arabizi + ' = ' + w.english); }
    } else if (src !== 'Drill') {
      // P3: the reverse - English shows a plural but the Arabic side has none
      if (E.includes(' · ')) add('P3 English plural without an Arabic plural', w.arabizi + ' = ' + E);
      if (A.includes(' · ')) add('P3 " · " on a card with no plural', A);
      const en = String(w.english || ''), d = en.match(/^([^/]+?)\s*[–-]\s+([^/]+)$/), gp = d && enPlural(d[1]);
      if (!w._pl && d && !/\d/.test(en) && gp && gp.toLowerCase() === d[2].trim().toLowerCase().replace(/\s*\(.*$/s, ''))
        add('P3 English writes a plural (X - Xs) but the card has no Arabic plural', w.arabizi + ' = ' + en);
    }
    // P4: a Quizlet bracket the page did not read as a plural must be a preposition, gender note or spelling
    if (src === 'Quizlet' && !hasPl(w) && SEL.quizletPlural(w.arabizi, w.english)) add('P4 Quizlet plural in brackets missed', w.arabizi + ' = ' + w.english);
    if (/(^|\s)[mfp]:\s/i.test(A)) add('F2 person forms shown as a plural', A);
    if (/somethings|onlies|happies|stomaches|day offs|homeworks|weathers|sceneries|mosquitos\b|groceries stores|\((travel|local)\) trips|pantses|glasseses|sheeps|deers/i.test(E)) add('F4 bad English plural', E);
  }
  // P5: Amal's plural sets - a back in English ("my uncles's (F) sons/kids", "Country") is not labelled Plural
  for (const { c, set } of qAll) if (/plur/i.test(set.title || '') && c._pl && (/\s(my|your|the|of)\s/i.test(' ' + c.english + ' ') || /^(country|parents|siblings|relatives)$/i.test(c.english.trim())))
    add('P5 English back labelled Plural', c.arabizi + ' = ' + c.english);
  T.pref.mode = mode0;
  const bySource = cards.reduce((o, x) => (o[x.src] = (o[x.src] || 0) + 1, o), {});
  return { total: cards.length, bySource, plural, issues: Object.fromEntries(Object.entries(issues).map(([k, v]) => [k, { n: v.length, ex: v.slice(0, 10) }])) };
})();
