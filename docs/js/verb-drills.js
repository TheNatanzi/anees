// Verb drills (pure, no DOM): plan/VERB-DRILLS-SPEC-2026-09-22.md step 3 (+ level 2 add-ons, step 4).
// One card = 1 verb + 1 tense + 1 person. Front/back follow the Flashcards "Front of the card" switch.
// Key: the Doc word key when that person form is in the Doc, else form:<entry id>:<person>[:<add-on>]
// (word-bank-core maps form: keys back to the tense entry by longest known prefix).
(function (root) {
  'use strict';
  const TENSES = ['Present', 'Past', 'Command'];
  const PRON = { 'I': 'I', 'You (m)': 'you (m)', 'You (f)': 'you (f)', 'You (pl)': 'you (pl)', 'He': 'he', 'She': 'she', 'We': 'we', 'They': 'they' };
  const THIRD = new Set(['He', 'She']);
  const PRON_RE = /^(i|you\s*\((?:m|f|pl)\)|he|she|we|they)\s+/i;
  const IRREG = { be: 'was', become: 'became', begin: 'began', break: 'broke', bring: 'brought', build: 'built', buy: 'bought', can: 'could', catch: 'caught',
    choose: 'chose', come: 'came', cut: 'cut', do: 'did', draw: 'drew', drink: 'drank', drive: 'drove', eat: 'ate', fall: 'fell', feel: 'felt', fight: 'fought',
    find: 'found', fly: 'flew', forget: 'forgot', get: 'got', give: 'gave', go: 'went', grow: 'grew', have: 'had', hear: 'heard', hide: 'hid', hit: 'hit', hold: 'held',
    hurt: 'hurt', keep: 'kept', know: 'knew', leave: 'left', lend: 'lent', let: 'let', lose: 'lost', make: 'made', mean: 'meant', meet: 'met', pay: 'paid',
    put: 'put', read: 'read', ride: 'rode', ring: 'rang', rise: 'rose', run: 'ran', say: 'said', see: 'saw', sell: 'sold', send: 'sent', set: 'set', shake: 'shook',
    shut: 'shut', sing: 'sang', sit: 'sat', sleep: 'slept', speak: 'spoke', spend: 'spent', stand: 'stood', steal: 'stole', swim: 'swam', take: 'took', teach: 'taught',
    tear: 'tore', tell: 'told', think: 'thought', throw: 'threw', understand: 'understood', wake: 'woke', wear: 'wore', win: 'won', write: 'wrote' };

  function base(gloss) { return String(gloss || '').trim().replace(/^I[’']m\s+/i, 'be ').replace(/^I\s+/, '').replace(/^\w/, c => c.toLowerCase()); }
  function eachWord(phrase, fn) { return phrase.split(/(\s*\/\s*)/).map((p, i) => { if (i % 2) return p; const [w, ...rest] = p.split(' '); return [fn(w), ...rest].join(' '); }).join(''); }
  function third(phrase) {
    return eachWord(phrase, w => { const l = w.toLowerCase();
      if (l === 'be') return 'is'; if (l === 'have') return 'has'; if (l === 'can') return 'can'; if (l === 'do' || l === 'go') return w + 'es';
      if (/(s|sh|ch|x|z)$/.test(l)) return w + 'es'; if (/[^aeiou]y$/.test(l)) return w.slice(0, -1) + 'ies'; return w + 's'; });
  }
  function pastRule(phrase) {
    return eachWord(phrase, w => { const l = w.toLowerCase();
      if (IRREG[l]) return IRREG[l]; if (/e$/.test(l)) return w + 'd'; if (/[^aeiou]y$/.test(l)) return w.slice(0, -1) + 'ied';
      if (/^[^aeiou]*[aeiou][bdgmnpt]$/.test(l)) return w + l.slice(-1) + 'ed'; return w + 'ed'; });
  }

  // English cue for one person form: Amal's own gloss for that tense when the Doc has one, else rules.
  function cue(group, entry, person, glossOf) {
    const pron = PRON[person] || person.toLowerCase(), b = base(group.english);
    const documented = (entry.persons || []).map(p => glossOf(p.key)).concat((entry.keys || []).map(glossOf)).filter(Boolean)
      .map(g => String(g).trim().replace(PRON_RE, '')).find(g => g && !/^\(/.test(g));
    if (entry.label === 'Command') return pron + ' · ' + (documented || b).replace(/!?$/, '!').replace(/^\w/, c => c.toLowerCase());
    if (entry.label === 'Past') {
      let verb = documented || pastRule(b);
      if (/^(was|were)\b/.test(verb)) verb = verb.replace(/^(was|were)/, (pron === 'I' || THIRD.has(person)) ? 'was' : 'were');
      return pron + ' · ' + verb;
    }
    let verb = b;
    if (/^be\b/.test(b)) verb = b.replace(/^be/, pron === 'I' ? 'am' : THIRD.has(person) ? 'is' : 'are');
    else if (THIRD.has(person)) verb = third(b);
    return pron + ' · ' + verb;
  }

  function personCards(group, entry, byKey, glossOf) {
    return (entry.persons || []).filter(p => String(p.word || '').trim()).map(p => {
      const doc = p.key && byKey.has(p.key) ? p.key : null;
      const guessed = p.provenance === 'inferred' && p.checked !== true;
      return { key: doc || 'form:' + entry.id + ':' + p.person, arabizi: p.word, arabic: p.arabic || '', english: cue(group, entry, p.person, glossOf),
        topic: 'Verb drills', verb: group.id, tense: entry.label, person: p.person, entry: entry.id, guessed, drill: true };
    });
  }

  // Every verb's drillable persons: [{verb, name, tenses: {Present: [card...], Past: [...], Command: [...]}}]
  function verbs(catalog, words) {
    const byKey = new Map((words || []).map(w => [w.key, w]));
    const glossOf = k => (k && byKey.has(k) ? byKey.get(k).english : '');
    return ((catalog && catalog.groups) || []).filter(g => g.type === 'Verb').map(g => {
      const t = {};
      for (const e of g.entries || []) if (TENSES.includes(e.label)) t[e.label] = personCards(g, e, byKey, glossOf);
      return { verb: g.id, name: g.name, english: g.english, arabic: g.arabic, tenses: t };
    }).filter(v => TENSES.some(t => (v.tenses[t] || []).length));
  }

  function rng(seed) { let s = (seed >>> 0) || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
  function shuffled(list, rand) { const a = list.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  const allowed = tense => tense && tense !== 'All' ? [tense] : TENSES;

  // mode 'random': `count` distinct verbs, each once, random allowed tense + random person.
  // mode 'full':   `count` verbs, every person of every allowed tense, verb by verb.
  function round(pool, opts) {
    const o = Object.assign({ mode: 'random', count: 20, tense: 'All', level: 1, random: Math.random }, opts || {});
    const tenses = allowed(o.tense), usable = pool.filter(v => tenses.some(t => (v.tenses[t] || []).length));
    const chosen = shuffled(usable, o.random).slice(0, o.count), out = [];
    for (const v of chosen) {
      if (o.mode === 'full') { for (const t of tenses) out.push(...(v.tenses[t] || [])); continue; }
      const ts = tenses.filter(t => (v.tenses[t] || []).length), t = ts[Math.floor(o.random() * ts.length)], ps = v.tenses[t];
      out.push(ps[Math.floor(o.random() * ps.length)]);
    }
    return o.level === 2 && root.AneesVerbAddons ? out.map(c => root.AneesVerbAddons.decorate(c, o.random)).filter(Boolean) : out;
  }

  const api = { TENSES, verbs, round, cue, third, pastRule, base, rng };
  root.AneesVerbDrills = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
