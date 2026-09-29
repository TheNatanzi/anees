/* Newest Amal wins (Medi M1, 2026-09-29): apply docs/data/quizlet/amal-newer-spellings.json to her Quizlet sets when
   they are loaded. Returns new objects; the imported data is never changed. Browser: window.AneesAmalNewest; node: require. */
(function (root) {
  function apply(sets, doc) {
    const reps = (doc && doc.replace) || [];
    if (!reps.length) return sets || [];
    return (sets || []).map(s => {
      const mine = reps.filter(r => !r.set || r.set === s.title);
      if (!mine.length) return s;
      const terms = (s.terms || []).map(t => {
        if (!Array.isArray(t)) return t;
        let z = String(t[0]);
        for (const r of mine) if (z.includes(r.from)) z = z.split(r.from).join(r.to);
        return z === t[0] ? t : [z, ...t.slice(1)];
      });
      return Object.assign({}, s, { terms });
    });
  }
  const api = { apply };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.AneesAmalNewest = api;
})(typeof window !== 'undefined' ? window : null);
