// Grip buckets — JS port of scripts/buckets.py (the Python file is the reference; tests/test_m5_cards.py checks parity).
// ice_cold: 5 first-try rights in a row on >= 3 different days; one miss -> cold. cold: unprompted in a lesson / right first try.
// shaky: prompted / right on second try. missed: corrected / wrong twice in a row on cards. never: no Medi signal.
(function (root) {
  const RECENT_LESSONS = 3, NEW_DRILL_RIGHTS = 5, NEW_DRILL_DAYS = 2;
  const GRAMMAR_KINDS = ['article', 'gender', 'tense', 'plural'];
  function signalFromEvent(e) {
    if (e.speaker !== 'Medi' || e.prompted === null || e.prompted === undefined) return null;
    if (e.correction && GRAMMAR_KINDS.includes(e.miss_kind) && !e.asked) return e.prompted ? 'shaky' : 'cold';
    if (e.miss_kind === 'choice') return 'shaky';
    if (e.correction || e.asked) return 'missed';
    if (e.prompted) return 'shaky';
    return 'cold';
  }
  function wasIce(cards) { return cards.length ? signalFromCards(cards)[0] === 'ice_cold' : false; }
  function signalFromCards(cards) {
    if (!cards.length) return [null, 0, []];
    let streak = 0; const days = [];
    for (let i = cards.length - 1; i >= 0; i--) {
      const c = cards[i];
      if (c.result === 'got' && (parseInt(c.attempt || 1) === 1)) { streak++; const d = String(c.ts).slice(0, 10); if (!days.includes(d)) days.push(d); }
      else break;
    }
    const last = cards[cards.length - 1];
    if (streak >= 5 && days.length >= 3) return ['ice_cold', streak, days];
    if (last.result === 'missed') {
      if (cards.slice(-3).filter(c => c.result === 'missed').length >= 2) return ['missed', 0, []];   // wrong twice within the last three
      return [wasIce(cards.slice(0, -1)) ? 'cold' : 'shaky', 0, []];
    }
    if (parseInt(last.attempt || 1) > 1) return ['shaky', streak, days];
    return ['cold', streak, days];
  }
  function compute(wordEvents, cardResults, lessonDates, confirmedNew, docBefore) {
    // confirmedNew: Set of `${lesson_date}|${word_key}` marked new by Amal/Medi; docBefore: {lesson_date: Set(word_key)} in the Doc before that lesson
    confirmedNew = confirmedNew || new Set(); docBefore = docBefore || {};
    const markedKeys = new Set([...confirmedNew].map(x => x.split('|').slice(1).join('|')));
    const dates = [...new Set(lessonDates.map(String))].sort();
    const recent = new Set(dates.slice(-RECENT_LESSONS));
    const evBy = {}, cdBy = {};
    for (const e of wordEvents) (evBy[e.word_key] = evBy[e.word_key] || []).push(e);
    for (const c of cardResults) (cdBy[c.word_key] = cdBy[c.word_key] || []).push(c);
    const out = {};
    for (const key of new Set([...Object.keys(evBy), ...Object.keys(cdBy)])) {
      const evs = (evBy[key] || []).slice().sort((a, b) => (String(a.lesson_date) + (a.t_start || 0)).localeCompare(String(b.lesson_date) + (b.t_start || 0)) || ((a.t_start || 0) - (b.t_start || 0)));
      const cards = (cdBy[key] || []).slice().sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
      const byDay = new Map();
      for (const e of evs) { const s = signalFromEvent(e); if (s) { const d = String(e.lesson_date); if (!byDay.has(d)) byDay.set(d, []); byDay.get(d).push(s); } }
      const lessonSignals = [...byDay.entries()].map(([d, sigs]) => [d, sigs.includes('missed') ? 'missed' : (sigs.includes('cold') ? 'cold' : 'shaky')]);   // one signal per lesson: unprompted use beats a later echo
      const [cardBucket, streak, days] = signalFromCards(cards);
      const lastLesson = lessonSignals.length ? lessonSignals[lessonSignals.length - 1] : null;
      const lastCardTs = cards.length ? String(cards[cards.length - 1].ts).slice(0, 10) : null;
      let bucket = 'never';
      if (lastLesson && (!lastCardTs || lastLesson[0] >= lastCardTs)) bucket = lastLesson[1];
      else if (cardBucket) bucket = cardBucket;
      if (cardBucket === 'ice_cold' && bucket === 'cold') bucket = 'ice_cold';
      const firstLesson = evs.length ? String(evs[0].lesson_date) : null;
      const lessonSignal = bucket;
      const drilled = streak >= NEW_DRILL_RIGHTS && days.length >= NEW_DRILL_DAYS;
      const seenDates = [...new Set(evs.map(e => String(e.lesson_date)))].sort();
      const marked = markedKeys.has(key);
      const byDoc = seenDates.some(d => docBefore[d] && !docBefore[d].has(key));
      if ((marked || byDoc) && !drilled) bucket = 'new';
      const lastReviewed = [seenDates[seenDates.length - 1], cards.length ? String(cards[cards.length - 1].ts) : null].filter(Boolean).sort().pop() || null;
      const isRecent = firstLesson ? recent.has(firstLesson) : false;
      out[key] = { word_key: key, bucket, last_reviewed: lastReviewed, seen_lessons: seenDates.length, times_seen: evs.length,
        times_missed: evs.filter(e => e.correction).length + cards.filter(c => c.result === 'missed').length,
        card_right: cards.filter(c => c.result === 'got').length, card_wrong: cards.filter(c => c.result === 'missed').length,
        streak, streak_days: days, recent: isRecent, weight: (bucket === 'missed' || bucket === 'new') ? 3 : 1, lesson_signal: lessonSignal };
    }
    return out;
  }
  root.AneesBuckets = { compute, signalFromCards, signalFromEvent };
})(typeof window !== 'undefined' ? window : globalThis);
