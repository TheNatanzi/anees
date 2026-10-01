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
  // boost (optional, from boostMap): a word that sank a sentence he missed in a lesson weighs BOOST.weight times more.
  function draw(words, stats, n, seed, boost) {
    const rnd = typeof seed === 'number' ? mulberry32(seed) : Math.random;
    const items = words.map(w => ({ w, wt: weightOf(w, stats[w.key]) * (boost && boost.has(w.key) ? BOOST.weight : 1) }));
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
  // A missed card comes back later in the SAME round (Medi 2026-09-30, from Mochi / RemNote / Quizlet Learn): it is put
  // REDO_GAP cards further on (or at the end) until it is answered Know once. The round's Know / Still learning counts
  // are per card (its latest answer), so a card missed then known counts once, as Know.
  const REDO_GAP = 3;
  function answer(round, result, nowIso, uuid) {
    const w = round.cards[round.i]; if (!w) return null;
    const row = { id: uuid, word_key: w.key, ts: nowIso, mode: round.mode, result, attempt: round.attempt, round_id: round.id, subject: round.subject };
    let inserted = null;
    if (result !== 'got' && round.redo !== false) { inserted = Math.min(round.i + 1 + REDO_GAP, round.cards.length); round.cards.splice(inserted, 0, w); }
    round.results.push(row); round.inserted = (round.inserted || []).concat([inserted]);
    if (result !== 'got' && !round.wrong.find(x => x.key === w.key)) round.wrong.push(w);
    round.i++; tally(round);
    return row;
  }
  // Take back the last answer of the round (Anki / Quizlet undo): the card is shown again and any comeback copy is removed.
  function undo(round) {
    if (!round.results.length) return null;
    const row = round.results.pop(), ins = (round.inserted || []).pop();
    if (ins !== null && ins !== undefined) round.cards.splice(ins, 1);
    round.i--;
    if (!round.results.some(r => r.word_key === row.word_key && r.result !== 'got')) round.wrong = round.wrong.filter(x => x.key !== row.word_key);
    tally(round); return row;
  }
  function tally(round) {
    const last = new Map(); for (const r of round.results) last.set(r.word_key, r.result);
    round.got = [...last.values()].filter(v => v === 'got').length; round.missed = last.size - round.got;
    round.firstTry = round.results.filter((r, i) => round.results.findIndex(x => x.word_key === r.word_key) === i && r.result === 'got').length;
  }
  function unique(round) { return new Set(round.cards.map(w => w.key)).size; }
  function done(round) { return round.i >= round.cards.length; }
  function replayWrong(round) {
    const next = newRound(round.wrong, { mode: round.mode, subject: round.subject, id: round.id + '-' + (round.attempt + 1) });
    next.attempt = round.attempt + 1; next.history = round.history.concat([{ attempt: round.attempt, got: round.got, missed: round.missed, n: unique(round) }]);
    return next;
  }
  // Known cards go to the back of the set (Medi 2026-09-30): a card whose latest (not undone) swipe was Know is dealt
  // after every card that is not known yet. Order inside each half is kept. log = card_results rows (any order).
  function splitKnown(words, log) {
    const last = new Map();
    for (const r of log || []) { if (!r || !r.word_key || r.undone || r.kind) continue;
      const t = Date.parse(r.ts) || 0, p = last.get(r.word_key); if (!p || t >= p.t) last.set(r.word_key, { t, result: r.result }); }
    const known = [], rest = [];
    for (const w of words) ((last.get(w.key) || {}).result === 'got' ? known : rest).push(w);
    return { rest, known };
  }
  // Singular / plural cards (Medi 2026-09-30: "mark which one I got wrong"). One swipe writes two rows: the card's own key
  // carries the SINGULAR result, "<id>-pl" with word_key "form:<key>:plural" carries the PLURAL result, so the Word Bank
  // scores each form. For scheduling the pair is one answer: the card is missed if either part was missed (schedLog).
  const PL = '-pl';
  function partRows(row, key, part) {
    const sing = part === 'plural' ? 'got' : row.result, plur = row.result === 'got' || part === 'singular' ? 'got' : 'missed';
    return [{ ...row, result: sing }, { ...row, id: row.id + PL, word_key: 'form:' + key + ':plural', result: plur }];
  }
  function schedLog(log) {
    const list = log || [], miss = new Set(), pair = new Set();
    for (const r of list) if (r && typeof r.id === 'string' && r.id.endsWith(PL)) { pair.add(r.id.slice(0, -PL.length)); if (r.result === 'missed' && !r.undone && !r.undone_at) miss.add(r.id.slice(0, -PL.length)); }
    const out = [];
    for (const r of list) { if (r && typeof r.id === 'string' && r.id.endsWith(PL) && pair.has(r.id.slice(0, -PL.length))) continue; out.push(miss.has(r && r.id) ? { ...r, result: 'missed' } : r); }
    return out;
  }
  // Keep going (Medi 2026-09-30): after a round of `size` cards from a bigger set, what the next round offers.
  // left >= 2 batches -> the next batch; left between 1 and 2 batches -> ask: split in two halves, or all of them;
  // left <= 1 batch -> the last ones. 67 cards in 20s: 20, 20, then 27 left -> "13 + 14" or "all 27".
  function nextChunk(left, size) {
    if (!size || left <= 0) return { kind: 'none' };
    if (left <= size) return { kind: 'last', n: left };
    if (left < 2 * size) { const a = Math.floor(left / 2); return { kind: 'ask', all: left, a, b: left - a }; }
    return { kind: 'next', n: size, left };
  }
  function summary(round) { return { n: unique(round), shown: round.results.length, firstTry: round.firstTry || 0, got: round.got, missed: round.missed, wrong: round.wrong.map(w => w.key), attempt: round.attempt, history: round.history }; }
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
  // ---- Listening boost (plan/SENTENCE-LADDER-SPEC-2026-09-27.md section 7) ----
  // docs/data/sentence-ladder.json -> boost[]: word keys that sank sentences he missed in a lesson ({key, score, strong,
  // weak, dates, last, ids}). BOOST is the one place for the boost numbers: weight = how much more a boosted word weighs
  // in a weighted practice draw (the same 3x as a missed / new card). In the daily queue the boost only changes ORDER:
  // due boosted cards first, boosted unseen words first into the new-card slots. The daily new cap and sibling burying
  // are untouched, and a card never becomes due early.
  const BOOST = Object.freeze({ weight: 3 });
  const DAY = 86400000;
  const localDate = s => { const p = String(s || '').split('-').map(Number); return p.length === 3 && p.every(Number.isFinite) ? new Date(p[0], p[1] - 1, p[2]).getTime() : NaN; };
  // Map key -> boost entry. A word drops out once he has got its card right on a later day than his last miss in a
  // lesson (the boost did its job); a card miss after the lesson keeps it boosted.
  function boostMap(list, log) {
    const lastGot = new Map();
    for (const r of log || []) {
      if (!r || !r.word_key || r.undone || r.undone_at || r.kind === 'flag' || r.kind === 'undo' || r.result !== 'got') continue;
      const ms = Date.parse(r.ts); if (Number.isFinite(ms) && ms > (lastGot.get(r.word_key) || 0)) lastGot.set(r.word_key, ms);
    }
    const out = new Map();
    for (const b of list || []) {
      if (!b || !b.key || !(b.score > 0) || out.has(b.key)) continue;
      const missed = localDate(b.last); if (!Number.isFinite(missed)) continue;
      if ((lastGot.get(b.key) || 0) >= missed + DAY) continue;
      out.set(b.key, b);
    }
    return out;
  }
  // The chip text: "boosted: missed in lesson 26 Sep".
  function boostLabel(b) {
    const t = b && localDate(b.last); if (!Number.isFinite(t)) return '';
    const d = new Date(t);
    return 'boosted: missed in lesson ' + d.getDate() + ' ' + 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ')[d.getMonth()];
  }
  // Order: learning cards due now, then reviews due today, then new cards up to the daily limit.
  // A new or review card is buried when a sibling was answered today or is already in today's queue.
  // opts.boost (a boostMap): due boosted cards lead (highest score first), and boosted unseen words take the new-card
  // slots first; the cap, the burying and the due times stay exactly as without it.
  function queue(words, cards, log, now, opts) {
    const F = root.AneesFSRS, o = Object.assign({ newPerDay: F.DEFAULTS.newPerDay }, opts || {}), t = +now, today = dayStart(t), end = today + 86400000;
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
    const boost = o.boost instanceof Map ? o.boost : null, score = k => (boost && boost.has(k) ? boost.get(k).score || 0 : 0);
    const byBoost = (a, b) => score(b.id) - score(a.id) || a.due - b.due;   // boosted (score > 0) before the rest; ties keep due order
    learning.sort((a, b) => a.due - b.due); later.sort((a, b) => a.due - b.due); reviews.sort(boost ? byBoost : (a, b) => a.due - b.due);
    let buried = 0;
    const take = (list, key) => list.filter(x => { const g = group.get(key(x)) || 'w:' + key(x); if (usedGroup.has(g)) { buried++; return false; } usedGroup.add(g); return true; });
    const dueReviews = take(reviews, c => c.id);
    const room = Math.max(0, o.newPerDay - newToday);
    const unseen = words.filter(w => !cards.has(w.key) || !cards.get(w.key).reps).sort((a, b) => score(b.key) - score(a.key) || (a.doc_order || 0) - (b.doc_order || 0));
    for (const w of unseen) { if (fresh.length >= room) break; const g = group.get(w.key) || 'w:' + w.key; if (usedGroup.has(g)) { buried++; continue; } usedGroup.add(g); fresh.push(F.newCard(w.key)); }
    const ahead = later.filter(c => c.due - t <= LEARN_AHEAD);
    const isB = c => score(c.id) > 0;
    const lead = learning.concat(dueReviews).filter(isB).sort(byBoost);
    const items = lead.concat(learning.filter(c => !isB(c)), dueReviews.filter(c => !isB(c)), fresh);
    const next = items.length ? items : ahead.slice(0, 1);
    return { items: next, counts: { due: dueReviews.length, new: fresh.length, learning: learning.length + later.length, boosted: next.filter(isB).length }, newToday, room, buried, nextLearning: later[0] ? later[0].due : null, boosted: next.filter(isB).map(c => c.id) };
  }
  // ---- the new-card cap, for every path that can show a card for the first time ----
  // Cards first answered today (live rows only): the cap counts introductions, not answers.
  function newToday(log, now) {
    const today = dayStart(+now), firstSeen = new Map();
    for (const r of log || []) { if (!r || r.undone || r.undone_at || r.kind === 'flag' || r.kind === 'undo' || !r.ts || !r.word_key) continue; const ms = Date.parse(r.ts); if (!Number.isFinite(ms)) continue; if (!firstSeen.has(r.word_key) || ms < firstSeen.get(r.word_key)) firstSeen.set(r.word_key, ms); }
    return [...firstSeen.values()].filter(ms => ms >= today).length;
  }
  // Apply the daily new-card cap (wiki 06 rule 2, AneesFSRS.DEFAULTS.newPerDay) to a chosen list of word-shaped
  // cards ({key}). Already-seen cards always pass; unseen cards pass in order until the day's room is used up,
  // the rest are held (silently rescheduled: they stay unseen and come up another day). Nothing is stored.
  function capNew(list, log, now, opts) {
    const F = root.AneesFSRS, o = Object.assign({ newPerDay: F.DEFAULTS.newPerDay }, opts || {});
    const seen = new Set(); for (const r of log || []) if (r && r.word_key && !r.undone && !r.undone_at && r.kind !== 'flag' && r.kind !== 'undo') seen.add(r.word_key);
    const used = newToday(log, now), room = o.newPerDay > 0 ? Math.max(0, o.newPerDay - used) : Infinity;
    const cards = [], held = []; let fresh = 0;
    for (const w of list || []) { if (!w) continue; if (seen.has(w.key)) { cards.push(w); continue; } if (fresh < room) { fresh++; cards.push(w); } else held.push(w); }
    return { cards, held: held.length, fresh, room: room === Infinity ? null : room, newToday: used, cap: o.newPerDay };
  }
  root.AneesCards = { subjects, pool, draw, drawOne, shuffle, newRound, answer, undo, unique, REDO_GAP, done, replayWrong, summary, nextChunk, splitKnown, partRows, schedLog, PL, weightOf, weightFromBucket, cardScore, mergeLocal, mulberry32, siblingMap, queue, dayStart, newToday, capNew, BOOST, boostMap, boostLabel };
})(typeof window !== 'undefined' ? window : globalThis);
