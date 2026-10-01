// Flashcard audit (docs/flashcard-rules.md). Runs INSIDE docs/cards.html (it uses the page's own faces / enFull / hasPl),
// so it checks exactly what Medi sees. Paste into the browser console on the Flashcards page, or run through the preview
// tool, after the page has loaded. Returns {total, issues}; issues should be {} (empty). Last run 2026-10-01: 6,048 cards, {}.
(async () => {
  for (let i = 0; i < 40 && !(serverLog.length && quizlet.length); i++) await new Promise(r => setTimeout(r, 500));
  const T = window.AneesTest, W = T.words, el = h => { const d = document.createElement('div'); d.innerHTML = h; return d; };
  const qOnly = quizlet.flatMap(s => SEL.quizletCards(s, SEL.matcher(W))).filter(c => SEL.isQuizletOnly(c.key));
  const drills = VD.round(selection().drills, { mode: 'full', count: 500, tense: 'All', level: 1 });
  const cards = [...W.map(w => ({ w, src: 'Doc' })), ...qOnly.map(w => ({ w, src: 'Quizlet' })), ...drills.map(w => ({ w, src: 'Drill' }))];
  const issues = {}, add = (k, ex) => (issues[k] = issues[k] || []).push(ex), mode0 = T.pref.mode;
  for (const { w, src } of cards) {
    for (const m of ['ar_first', 'en_first']) { T.pref.mode = m; try { faces(w); } catch (e) { add('card crashes', w.key + ' ' + e.message); } }
    T.pref.mode = 'ar_first'; const [af, ef] = faces(w), A = el(af).querySelector('.big').innerText, E = el(ef).querySelector('.en').innerText;
    if (src === 'Drill' && (A + E).includes(' · ')) add('F11 drill shows " · "', E);
    if (/^\s*\d+\s*$/.test(w.arabizi || '')) add('F9 number-only front', w.arabizi);
    if (hasPl(w) && !A.includes(' · ')) add('F1 plural missing on the Arabic side', w.arabizi);
    // F1 vs F5: a real English plural exists when every "/" part pluralizes AND differs from the singular (sheep, help: said once)
    const parts = String(w.english || '').split('/').map(x => x.trim()).filter(Boolean), ps = parts.map(x => enPlural(x));
    const real = ps.length && ps.every(Boolean) && ps.join('/').toLowerCase() !== parts.map(x => x.toLowerCase().replace(/^(a|an|the) /, '')).join('/');
    if (hasPl(w) && real && !isCmd(w) && !/\s[–-]\s/.test(w.english) && !E.includes(' · ')) add('F1 plural missing on the English side', w.english);
    if (isCmd(w) && !/!/.test(E)) add('F8 command not marked', w.english);
    if (/somethings|onlies|happies|stomaches|day offs|homeworks|weathers/.test(E)) add('F4 bad English plural', E);
  }
  T.pref.mode = mode0;
  return { total: cards.length, issues: Object.fromEntries(Object.entries(issues).map(([k, v]) => [k, { n: v.length, ex: v.slice(0, 10) }])) };
})();
