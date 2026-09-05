// Flashcards core (pure, no DOM): subjects, weighted draw, round state machine, offline result queue shape.
// Weight: Missed words and words learned in the last 3 lessons draw 3x as often (plan section 0).
(function (root) {
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const GRAMMAR = [
    { id: 'g-past', name: 'Past tense', test: w => w.topic === 'Past Tense' },
    { id: 'g-verbs', name: 'All verb tenses', test: w => ['Past Tense', 'Command Tense', 'Verbs List', 'Tense'].includes(w.topic) || /Tense/.test(w.topic) },
    { id: 'g-plural', name: 'Plurals', test: w => !!(w.plural && w.plural.trim()) },
    { id: 'g-command', name: 'Command tense', test: w => w.topic === 'Command Tense' },
  ];
  const BUCKET_SETS = [
    { id: 'b-missed', name: 'Missed only', test: (w, s) => s && s.bucket === 'missed' },
    { id: 'b-shaky', name: 'Shaky only', test: (w, s) => s && s.bucket === 'shaky' },
    { id: 'b-recent', name: 'Last 3 lessons', test: (w, s) => s && s.recent },
    { id: 'b-cold', name: 'Cold + ice cold (keep them)', test: (w, s) => s && (s.bucket === 'cold' || s.bucket === 'ice_cold') },
  ];
  function subjects(words, stats) {
    const topics = [...new Set(words.map(w => w.topic))].map(t => ({ id: 't:' + t, name: t, kind: 'topic', n: words.filter(w => w.topic === t).length }));
    const grammar = GRAMMAR.map(g => ({ id: g.id, name: g.name, kind: 'grammar', n: words.filter(g.test).length }));
    const buckets = BUCKET_SETS.map(b => ({ id: b.id, name: b.name, kind: 'bucket', n: words.filter(w => b.test(w, stats[w.key])).length }));
    return { topics, grammar, buckets };
  }
  function pool(words, stats, subjectId) {
    if (subjectId.startsWith('t:')) return words.filter(w => w.topic === subjectId.slice(2));
    const g = GRAMMAR.find(x => x.id === subjectId); if (g) return words.filter(g.test);
    const b = BUCKET_SETS.find(x => x.id === subjectId); if (b) return words.filter(w => b.test(w, stats[w.key]));
    return words;
  }
  function weightFromBucket(bucket, recent) { return (bucket === 'missed' || recent) ? 3 : 1; }
  // weight always follows the current bucket (a stored weight is never trusted over the bucket it was computed from)
  function weightOf(w, s) { return s ? weightFromBucket(s.bucket, s.recent) : 1; }
  // Merge the local answer log onto server stats: only rows NEWER than the server's last_reviewed count, and the new bucket is
  // derived from the server bucket (ice_cold + one miss -> cold; two misses in the last three -> missed; else shaky / cold).
  function mergeLocal(stats, log) {
    const out = Object.assign({}, stats);
    const by = {};
    for (const r of log || []) (by[r.word_key] = by[r.word_key] || []).push(r);
    for (const k in by) {
      const s = out[k] || { word_key: k, bucket: 'never', recent: false };
      const rows = by[k].filter(r => !s.last_reviewed || String(r.ts) > String(s.last_reviewed)).sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
      if (!rows.length) continue;
      const last = rows[rows.length - 1];
      let bucket;
      if (last.result === 'missed') {
        const recent3 = rows.slice(-3).filter(r => r.result === 'missed').length;
        bucket = recent3 >= 2 ? 'missed' : (s.bucket === 'ice_cold' ? 'cold' : 'shaky');
      } else bucket = parseInt(last.attempt || 1) > 1 ? 'shaky' : (s.bucket === 'ice_cold' ? 'ice_cold' : 'cold');
      out[k] = Object.assign({}, s, { bucket, weight: weightFromBucket(bucket, s.recent), last_reviewed: last.ts });
    }
    return out;
  }
  // Weighted draw WITHOUT replacement of n distinct words from the pool (each word at most once per round).
  function draw(words, stats, n, seed) {
    const rnd = typeof seed === 'number' ? mulberry32(seed) : Math.random;
    const items = words.map(w => ({ w, wt: weightOf(w, stats[w.key]) }));
    const out = [];
    while (out.length < n && items.length) {
      const total = items.reduce((a, it) => a + it.wt, 0);
      let r = rnd() * total, i = 0;
      while (i < items.length - 1 && r >= items[i].wt) { r -= items[i].wt; i++; }
      out.push(items[i].w); items.splice(i, 1);
    }
    return out;
  }
  // Weighted draw WITH replacement (used by the scheduler test: 300 draws -> Missed >= 3x Cold).
  function drawOne(words, stats, rnd) {
    const total = words.reduce((a, w) => a + weightOf(w, stats[w.key]), 0);
    let r = (rnd || Math.random)() * total;
    for (const w of words) { const wt = weightOf(w, stats[w.key]); if (r < wt) return w; r -= wt; }
    return words[words.length - 1];
  }
  function shuffle(arr, seed) { const rnd = typeof seed === 'number' ? mulberry32(seed) : Math.random; const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  // Round state machine: cards, answers, wrong pile, replay of the wrong pile only, until it is empty.
  function newRound(cards, opts) {
    return { id: (opts && opts.id) || ('r' + Date.now().toString(36)), cards: cards.slice(), i: 0, mode: (opts && opts.mode) || 'ar_first', subject: (opts && opts.subject) || '',
      attempt: 1, results: [], wrong: [], got: 0, missed: 0, history: [] };
  }
  function answer(round, result, nowIso, uuid) {
    const w = round.cards[round.i]; if (!w) return null;
    const row = { id: uuid, word_key: w.key, ts: nowIso, mode: round.mode, result, attempt: round.attempt, round_id: round.id, subject: round.subject };
    round.results.push(row);
    if (result === 'got') round.got++; else { round.missed++; if (!round.wrong.find(x => x.key === w.key)) round.wrong.push(w); }
    round.i++;
    return row;
  }
  function done(round) { return round.i >= round.cards.length; }
  function replayWrong(round) {
    const next = newRound(round.wrong, { mode: round.mode, subject: round.subject, id: round.id + '-' + (round.attempt + 1) });
    next.attempt = round.attempt + 1; next.history = round.history.concat([{ attempt: round.attempt, got: round.got, missed: round.missed, n: round.cards.length }]);
    return next;
  }
  function summary(round) { return { n: round.cards.length, got: round.got, missed: round.missed, wrong: round.wrong.map(w => w.key), attempt: round.attempt, history: round.history }; }
  root.AneesCards = { subjects, pool, draw, drawOne, shuffle, newRound, answer, done, replayWrong, summary, weightOf, weightFromBucket, mergeLocal, mulberry32 };
})(typeof window !== 'undefined' ? window : globalThis);
