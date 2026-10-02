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
  // A dated set is named after a lesson day ("December 12 Verbs", "March 15 Audio Homework").
  // Medi 2026-09-22: dated sets are hidden; only sets with a real name are shown.
  const DATED = /\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)\b\.?\s*\d/i;
  function isDated(title) { return DATED.test(String(title || '')); }
  const SET_GROUPS = [
    { id: 'plurals', name: 'Plurals', test: t => /plur/i.test(t) },
    { id: 'possession', name: 'Possession & pronouns', test: t => /pronoun|possess|conjugation/i.test(t) },
    { id: 'verbs', name: 'Verbs', test: t => /verb|command/i.test(t) },
    { id: 'topics', name: 'Topics', test: () => true },
  ];
  const norm = s => (root.AneesWordBank ? root.AneesWordBank.normalize(s) : String(s || '').toLowerCase().trim());
  const live = log => (log || []).filter(r => r && r.word_key && !r.undone && !r.undone_at && r.kind !== 'flag' && r.kind !== 'undo');

  // Row type as word-bank-core models it: catalog Verb / Adjective, Noun = has a plural, else Other.
  function typeOf(row) { return TYPES.includes(row && row.type) ? row.type : 'Other'; }

  // The card for one scored form: its first Doc word key, else a documented person form,
  // else the form itself as "form:<entry id>" (word-bank-core maps it back to that form).
  function formCard(r, f, byKey) {
    const key = (f.keys || []).concat((f.persons || []).map(p => p.key).filter(Boolean)).find(k => byKey.has(k));
    if (key) return byKey.get(key);
    if (!f.id || !(f.word || f.arabic)) return null;
    return { key: 'form:' + f.id, arabizi: f.word || f.arabic, arabic: f.word ? (f.arabic || '') : '', english: [r.english, f.label ? '(' + String(f.label).toLowerCase() + ')' : ''].filter(Boolean).join(' '), topic: r.topic, form: f.id };
  }
  // Shaky / Wrong in lessons (speaking) and on cards (flashcards), each split by word type.
  // Counts equal the Word Bank status chips: one card per scored form.
  function statusSplit(rows, words) {
    const byKey = new Map(words.map(w => [w.key, w]));
    const out = {};
    for (const lane of ['speaking', 'flashcards']) for (const st of ['Shaky', 'Wrong']) { out[[st, lane, 'All'].join('|')] = []; for (const t of TYPES) out[[st, lane, t].join('|')] = []; }
    for (const r of rows || []) {
      if (r.grammar_only) continue;
      for (const f of r.entries || []) {
        for (const lane of ['speaking', 'flashcards']) {
          const st = f[lane] && f[lane].status; if (st !== 'Shaky' && st !== 'Wrong') continue;
          const card = formCard(r, f, byKey); if (!card) continue;
          for (const bucket of [typeOf(r), 'All']) { const list = out[[st, lane, bucket].join('|')]; if (!list.some(w => w.key === card.key)) list.push(card); }
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
    useWords(words);
    const latin = new Map(), arabic = new Map();
    const add = (m, s, w) => { const k = norm(s); if (!k) return; if (!m.has(k)) m.set(k, new Set()); m.get(k).add(w); };
    for (const w of words) { for (const s of [w.arabizi, w.house_spelling].concat(w.aliases || [])) add(latin, s, w); add(arabic, w.arabic, w); }
    const one = (m, s) => { const hit = m.get(norm(s)); return hit && hit.size === 1 ? [...hit][0] : null; };
    return (term) => (term.arabizi && one(latin, term.arabizi)) || (term.arabic && one(arabic, term.arabic)) || null;
  }

  // A Quizlet set as cards. Matched terms reuse the Doc word (shared history); the rest are
  // their own cards keyed q:<set id>:<rank>. Terms with a blank side are skipped.
  // A bracket after a Quizlet word is a plural unless it is a preposition the word takes ("Ana bat6all3 (3ala)", "(la-)",
  // "(X)"), a gender note ("(M)", "(Feminine)"), the same word spelled again ("Hishis (his-his)"), or the card is a verb /
  // pattern ("I look", "+ (no b) verb").
  const PREP = /^(3ala|3al|la|la-|ma3|fi|bi|b|min|mn|3an|3and|X|m|f|g|p|d|m&f|male|female|masc(uline)?|fem(inine?)?|no b|-|\s|\/)+$/i;
  function quizletPlural(arabizi, english) {
    const m = String(arabizi || '').match(/^([^()]+?)\s*\(([^()]+)[()]?\s*$/); if (!m) return null;
    const singular = m[1].trim(), plural = m[2].trim(), en = String(english || '').trim(), key = x => String(x).toLowerCase().replace(/[^a-z0-9]/g, '');
    if (!singular || !plural || /\+/.test(arabizi) || /\d/.test(en) || PREP.test(plural.replace(/-$/, '')) || key(plural) === key(singular)) return null;
    if (/^(I|you|he|she|it|we|they)/i.test(en) || /\((command|progressive)\)/i.test(en)) return null;
    return { singular, plural };
  }
  // The back of a plural-set card is English when every word of it is an English word Amal uses in the Doc (and not Arabizi).
  function looksEnglish(text, en) {
    const toks = String(text || '').toLowerCase().replace(/[()'’.,!?]/g, ' ').split(/[\s/]+/).filter(Boolean);
    if (!toks.length || /\d/.test(text)) return false;
    if (/\s(the|a|an|to|of|is|i|you|my|your)\s/i.test(' ' + text + ' ')) return true;
    return toks.every(t => en.english.has(t) && !en.arabizi.has(t));
  }
  let englishWords = { english: new Set(), arabizi: new Set() };
  function useWords(words) {
    const e = new Set(), a = new Set(), tok = s => String(s || '').toLowerCase().replace(/[()'’.,!?]/g, ' ').split(/[\s/]+/).filter(Boolean);
    for (const w of words || []) { for (const t of tok(w.english)) e.add(t); for (const t of tok(w.arabizi).concat(tok(w.plural))) a.add(t); }
    englishWords = { english: e, arabizi: a };
  }

  function quizletCards(set, match) {
    const out = [], seen = new Set();
    (set.terms || []).forEach((pair, i) => {
      const [a, b] = pair || [];
      if (!String(a || '').trim() || !String(b || '').trim()) return;
      const aIsTarget = AR.test(a) || /\|/.test(a) || !(AR.test(b) || /\|/.test(b));
      const target = aIsTarget ? a : b, english = String(aIsTarget ? b : a).trim();
      const t = splitTerm(target); if (!t.arabizi && !t.arabic) t.arabizi = String(target).trim();
      const w = match(t);
      const card = w || { key: 'q:' + set.id + ':' + (i + 1), arabizi: t.arabizi || t.arabic, arabic: t.arabizi ? t.arabic : '', english, topic: set.title, quizlet: set.id,
        // Rule F8b (Medi 2026-10-01): in Amal's plural sets the back is the Arabic PLURAL, not English -> label Singular / Plural.
        // A back that is English (Parents, Siblings, Country, "my uncles's (F) sons/kids") stays an Arabic / English card: the
        // front has Arabic letters ("E5we | أخوة = Siblings") or every back word is English Amal uses in the Doc.
        ...(/plur/i.test(set.title || '') && !AR.test(target) && !looksEnglish(english, englishWords) ? { _pl: true } : {}) };
      // Rule F2: Quizlet writes a plural in brackets: "Daif (dyoof) = Guest - Guests", "Fasel (fsool) = Season",
      // even "Kalb (klaab( = Dog - dogs". Show it like the Doc: Daif · dyoof / Guest · guests.
      const pm = !w && !card.plural && quizletPlural(card.arabizi, card.english);
      if (pm) { card.arabizi = pm.singular; card.plural = pm.plural; }
      if (seen.has(card.key)) return; seen.add(card.key); out.push(card);
    });
    return out;
  }

  function quizletGroups(sets) {
    const groups = SET_GROUPS.map(g => ({ id: g.id, name: g.name, sets: [] }));
    for (const s of sets || []) if (!isDated(s.title)) groups[SET_GROUPS.findIndex(g => g.test(s.title || ''))].sets.push(s);
    return groups.filter(g => g.sets.length);
  }
  // Colour counts for a set: mastered, good, shaky, wrong, untested. bucketOf may return a Word Bank
  // status (Mastered / Good / Shaky / Wrong) or a flashcard bucket (ice_cold / cold / shaky / missed).
  const MIX = ['mastered', 'good', 'shaky', 'wrong', 'untested'];
  const MIX_OF = { ice_cold: 'mastered', cold: 'good', shaky: 'shaky', missed: 'wrong', Mastered: 'mastered', Good: 'good', Shaky: 'shaky', Wrong: 'wrong' };
  // Word Bank status per card key: the lesson status when tested in lessons, else the flashcard status.
  function statusByKey(rows) {
    const out = new Map();
    for (const r of rows || []) for (const f of r.entries || []) {
      const sp = f.speaking && f.speaking.status, fc = f.flashcards && f.flashcards.status;
      const st = sp && sp !== 'Untested' ? sp : fc && fc !== 'Untested' ? fc : null;
      if (!st) continue;
      for (const k of (f.keys || []).concat((f.persons || []).map(p => p.key).filter(Boolean), f.id ? ['form:' + f.id] : [])) if (!out.has(k)) out.set(k, st);
    }
    return out;
  }
  function scoreMix(words, bucketOf) {
    const out = Object.fromEntries(MIX.map(k => [k, 0]));
    for (const w of words || []) out[MIX_OF[bucketOf(w)] || 'untested']++;
    return out;
  }
  function collocationSets(sets) { return COLLOCATION_SETS.map(c => (sets || []).find(s => c.test(s.title || ''))).filter(Boolean); }

  function isQuizletOnly(key) { return /^q:/.test(String(key || '')); }
  function isFormCard(key) { return /^form:/.test(String(key || '')); }

  root.AneesCardSelection = { TYPES, TYPE_LABEL, TENSES, statusSplit, newFromAmal, neverTested, answeredKeys, tenses, topics, splitTerm, matcher, quizletCards, quizletGroups, collocationSets, isDated, MIX, scoreMix, statusByKey, isQuizletOnly, isFormCard, formCard, typeOf, quizletPlural, looksEnglish, useWords };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.AneesCardSelection;
})(typeof window !== 'undefined' ? window : globalThis);
