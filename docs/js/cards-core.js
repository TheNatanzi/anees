// Flashcards core (pure, no DOM): subjects, weighted draw, round state machine, offline result queue shape.
// Flashcard scores alone control bucket sets and weighting. Lesson recency is only an explicit content filter.
(function (root) {
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const GRAMMAR = [
    { id: 'g-past', name: 'Past tense', test: w => w.topic === 'Past Tense' },
    { id: 'g-verbs', name: 'All verb tenses', test: w => ['Past Tense', 'Command Tense', 'Verbs List', 'Tense'].includes(w.topic) || /Tense/.test(w.topic) },
    { id: 'g-plural', name: 'Plurals', test: w => !!(w.plural && w.plural.trim()) },
    { id: 'g-command', name: 'Command tense', test: w => w.topic === 'Command Tense' },
  ];
  const BUCKET_SETS = [
    { id: 'b-new', name: 'New words (strict review)', test: (w, s) => cardScore(s).bucket === 'new' },
    { id: 'b-missed', name: 'Missed only', test: (w, s) => cardScore(s).bucket === 'missed' },
    { id: 'b-shaky', name: 'Shaky only', test: (w, s) => cardScore(s).bucket === 'shaky' },
    { id: 'b-recent', name: 'Last 3 lessons', test: (w, s) => s && s.recent },
    { id: 'b-cold', name: 'Good + Mastered (keep them)', test: (w, s) => ['cold','ice_cold'].includes(cardScore(s).bucket) },
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
  function cardScore(s) { return (s?.progress_scores?.version===1 && s.progress_scores.flashcards) || {bucket:'never',weight:1}; }
  function weightFromBucket(bucket) { return (bucket === 'missed' || bucket === 'new') ? 3 : 1; }
  // weight always follows the current bucket (a stored weight is never trusted over the bucket it was computed from)
  function weightOf(w, s) { return weightFromBucket(cardScore(s).bucket); }
  // Replay durable + local card answers by ID in their own lane; Speaking is unchanged.
  function mergeLocal(stats, log) {
    return root.AneesBuckets.mergeStats(stats,log);
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
  // ---- FSRS daily queue (scheduling only; card grade stays in word-bank-core) ----
  // Siblings = the forms of one word (tenses, persons, plural) from the Word Bank catalog.
  function siblingMap(words, catalog) {
    const group = new Map();
    for (const g of (catalog && catalog.groups) || []) for (const k of g.keys || [g.key]) if (!group.has(k)) group.set(k, 'g:' + g.key);
    for (const w of words) if (!group.has(w.key)) group.set(w.key, 'w:' + w.key);
    return group;
  }
  function dayStart(t) { const d = new Date(t); return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime(); }
  const LEARN_AHEAD = 20 * 60000;   // Anki's default: finish a session by showing learning cards due in the next 20 minutes
  // Order: learning cards due now, then reviews due today, then new cards up to the daily limit.
  // A new or review card is buried when a sibling was answered today or is already in today's queue.
  function queue(words, cards, log, now, opts) {
    const F = root.AneesFSRS, o = Object.assign({ newPerDay: 20 }, opts || {}), t = +now, today = dayStart(t), end = today + 86400000;
    const group = opts && opts.siblings || siblingMap(words, null), usedGroup = new Set();
    const live = (log || []).filter(r => r && !r.undone && !r.undone_at && r.kind !== 'flag' && r.ts);
    for (const r of live) if (Date.parse(r.ts) >= today) usedGroup.add(group.get(r.word_key) || 'w:' + r.word_key);
    const firstSeen = new Map();
    for (const r of live) { const ms = Date.parse(r.ts); if (!firstSeen.has(r.word_key) || ms < firstSeen.get(r.word_key)) firstSeen.set(r.word_key, ms); }
    const newToday = [...firstSeen.values()].filter(ms => ms >= today).length;
    const byKey = new Map(words.map(w => [w.key, w]));
    const learning = [], reviews = [], fresh = [], later = [];
    for (const [key, c] of cards) {
      const w = byKey.get(key); if (!w || !c.reps) continue;
      if (c.state !== 'review') { if (c.due <= t) learning.push(c); else if (c.due < end) later.push(c); }
      else if (c.due < end) reviews.push(c);
    }
    learning.sort((a, b) => a.due - b.due); later.sort((a, b) => a.due - b.due); reviews.sort((a, b) => a.due - b.due);
    let buried = 0;
    const take = (list, key) => list.filter(x => { const g = group.get(key(x)) || 'w:' + key(x); if (usedGroup.has(g)) { buried++; return false; } usedGroup.add(g); return true; });
    const dueReviews = take(reviews, c => c.id);
    const room = Math.max(0, o.newPerDay - newToday);
    const unseen = words.filter(w => !cards.has(w.key) || !cards.get(w.key).reps).sort((a, b) => (a.doc_order || 0) - (b.doc_order || 0));
    for (const w of unseen) { if (fresh.length >= room) break; const g = group.get(w.key) || 'w:' + w.key; if (usedGroup.has(g)) { buried++; continue; } usedGroup.add(g); fresh.push(F.newCard(w.key)); }
    const ahead = later.filter(c => c.due - t <= LEARN_AHEAD);
    const items = learning.concat(dueReviews, fresh);
    const next = items.length ? items : ahead.slice(0, 1);
    return { items: next, counts: { due: dueReviews.length, new: fresh.length, learning: learning.length + later.length }, newToday, room, buried, nextLearning: later[0] ? later[0].due : null };
  }
  root.AneesCards = { subjects, pool, draw, drawOne, shuffle, newRound, answer, done, replayWrong, summary, weightOf, weightFromBucket, cardScore, mergeLocal, mulberry32, siblingMap, queue, dayStart };
})(typeof window !== 'undefined' ? window : globalThis);
