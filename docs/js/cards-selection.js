// Flashcards selection screen (pure, no DOM): the labelled sections of
// plan/FLASHCARDS-SELECTION-SPEC-2026-09-21.md. Every section returns word-shaped
// cards ({key, arabizi, arabic, english, topic, subtopic}) for the same swipe round.
(function (root) {
  'use strict';
  const AR = /[\u0600-\u06FF]/;
  const TYPES = ['Verb', 'Noun', 'Adjective', 'Other'];
  const TYPE_LABEL = { Verb: 'Verbs', Noun: 'Nouns', Adjective: 'Adjectives', Other: 'Other' };
  const TENSES = [
    { id: 'Present', name: 'Present', topic: 'Verbs List' },
    { id: 'Past', name: 'Past', topic: 'Past Tense' },
    { id: 'Command', name: 'Command', topic: 'Command Tense' },
  ];
  const COLLOCATION_SETS = [
    { id: 'verb-prep', test: t => /verb\s*\+\s*preposition/i.test(t) },
    { id: 'pronoun-obj', test: t => /pronoun objects? with verbs/i.test(t) },
  ];
  const SET_GROUPS = [
    { id: 'dated', name: 'Dated lessons', test: t => /audio homework/i.test(t) || (/\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)\b/i.test(t) && /\d/.test(t)) },
    { id: 'plurals', name: 'Plurals', test: t => /plur/i.test(t) },
    { id: 'possession', name: 'Possession & pronouns', test: t => /pronoun|possess|conjugation/i.test(t) },
    { id: 'verbs', name: 'Verbs', test: t => /verb|command/i.test(t) },
    { id: 'topics', name: 'Topics', test: () => true },
  ];
  const norm = s => (root.AneesWordBank ? root.AneesWordBank.normalize(s) : String(s || '').toLowerCase().trim());
  const live = log => (log || []).filter(r => r && r.word_key && !r.undone && !r.undone_at && r.kind !== 'flag' && r.kind !== 'undo');

  // Row type as word-bank-core models it: catalog Verb / Adjective, Noun = has a plural, else Other.
  function typeOf(row) { return TYPES.includes(row && row.type) ? row.type : 'Other'; }

  // Shaky / Wrong in lessons (speaking) and on cards (flashcards), each split by word type.
  // One card per scored form: the form's first active word key.
  function statusSplit(rows, words) {
    const byKey = new Map(words.map(w => [w.key, w]));
    const out = {};
    for (const lane of ['speaking', 'flashcards']) for (const st of ['Shaky', 'Wrong']) for (const t of TYPES) out[[st, lane, t].join('|')] = [];
    for (const r of rows || []) {
      if (r.grammar_only) continue;
      for (const f of r.entries || []) {
        const key = (f.keys || []).find(k => byKey.has(k)); if (!key) continue;
        for (const lane of ['speaking', 'flashcards']) {
          const st = f[lane] && f[lane].status; if (st !== 'Shaky' && st !== 'Wrong') continue;
          const list = out[[st, lane, typeOf(r)].join('|')];
          if (!list.some(w => w.key === key)) list.push(byKey.get(key));
        }
      }
    }
    return out;
  }

  // New from Amal: the existing "new" bucket (words Amal marked newly taught).
  function newFromAmal(words, stats) {
    return words.filter(w => { const s = stats && stats[w.key]; return !!(s && ((s.progress_context && s.progress_context.new === true) || s.bucket === 'new')); });
  }

  function answeredKeys(log) { return new Set(live(log).map(r => r.word_key)); }
  function neverTested(words, log) { const seen = answeredKeys(log); return words.filter(w => !seen.has(w.key)); }

  // Present / Past / Command: the Doc topic plus every catalog form of that tense.
  function tenses(words, catalog) {
    const byKey = new Map(words.map(w => [w.key, w]));
    return TENSES.map(t => {
      const keys = new Set(words.filter(w => w.topic === t.topic).map(w => w.key));
      for (const g of (catalog && catalog.groups) || []) for (const f of g.entries || []) {
        if (f.label !== t.id) continue;
        for (const k of (f.keys || []).concat((f.persons || []).map(p => p.key).filter(Boolean))) if (byKey.has(k)) keys.add(k);
        if (t.id === 'Present' && byKey.has(g.key)) keys.add(g.key);
      }
      return { id: t.id, name: t.name, words: words.filter(w => keys.has(w.key)) };
    });
  }

  function topics(words) {
    const m = new Map();
    for (const w of words) {
      const t = w.topic || 'Other'; if (!m.has(t)) m.set(t, { name: t, words: [], subs: new Map() });
      const e = m.get(t); e.words.push(w);
      if (w.subtopic) { if (!e.subs.has(w.subtopic)) e.subs.set(w.subtopic, []); e.subs.get(w.subtopic).push(w); }
    }
    return [...m.values()].map(e => ({ name: e.name, words: e.words, subs: [...e.subs.entries()].map(([name, ws]) => ({ name, words: ws })) }));
  }

  // "Arabizi | Arabic" or "Arabic | Arabizi": split on | and detect the Arabic side.
  function splitTerm(text) {
    const parts = String(text || '').split('|').map(s => s.trim()).filter(Boolean);
    let arabic = '', arabizi = '';
    for (const p of parts) { if (AR.test(p) && !arabic) arabic = p; else if (!AR.test(p) && !arabizi) arabizi = p; }
    return { arabic, arabizi };
  }

  // Match on house spelling / Arabizi / aliases first, then the Arabic; only a unique match counts.
  function matcher(words) {
    const latin = new Map(), arabic = new Map();
    const add = (m, s, w) => { const k = norm(s); if (!k) return; if (!m.has(k)) m.set(k, new Set()); m.get(k).add(w); };
    for (const w of words) { for (const s of [w.arabizi, w.house_spelling].concat(w.aliases || [])) add(latin, s, w); add(arabic, w.arabic, w); }
    const one = (m, s) => { const hit = m.get(norm(s)); return hit && hit.size === 1 ? [...hit][0] : null; };
    return (term) => (term.arabizi && one(latin, term.arabizi)) || (term.arabic && one(arabic, term.arabic)) || null;
  }

  // A Quizlet set as cards. Matched terms reuse the Doc word (shared history); the rest are
  // their own cards keyed q:<set id>:<rank>. Terms with a blank side are skipped.
  function quizletCards(set, match) {
    const out = [], seen = new Set();
    (set.terms || []).forEach((pair, i) => {
      const [a, b] = pair || [];
      if (!String(a || '').trim() || !String(b || '').trim()) return;
      const aIsTarget = AR.test(a) || /\|/.test(a) || !(AR.test(b) || /\|/.test(b));
      const target = aIsTarget ? a : b, english = String(aIsTarget ? b : a).trim();
      const t = splitTerm(target); if (!t.arabizi && !t.arabic) t.arabizi = String(target).trim();
      const w = match(t);
      const card = w || { key: 'q:' + set.id + ':' + (i + 1), arabizi: t.arabizi || t.arabic, arabic: t.arabizi ? t.arabic : '', english, topic: set.title, quizlet: set.id };
      if (seen.has(card.key)) return; seen.add(card.key); out.push(card);
    });
    return out;
  }

  function quizletGroups(sets) {
    const groups = SET_GROUPS.map(g => ({ id: g.id, name: g.name, sets: [] }));
    for (const s of sets || []) groups[SET_GROUPS.findIndex(g => g.test(s.title || ''))].sets.push(s);
    return groups;
  }
  function collocationSets(sets) { return COLLOCATION_SETS.map(c => (sets || []).find(s => c.test(s.title || ''))).filter(Boolean); }

  function isQuizletOnly(key) { return /^q:/.test(String(key || '')); }

  root.AneesCardSelection = { TYPES, TYPE_LABEL, TENSES, statusSplit, newFromAmal, neverTested, answeredKeys, tenses, topics, splitTerm, matcher, quizletCards, quizletGroups, collocationSets, isQuizletOnly, typeOf };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.AneesCardSelection;
})(typeof window !== 'undefined' ? window : globalThis);
