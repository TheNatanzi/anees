// Verb drills level 2 (pure): an object ending on the verb (3atani, shuftak) or a preposition + person after it
// (ma3hom, elak), per plan/VERB-DRILLS-SPEC-2026-09-22.md section 4. Preposition forms are Amal's own Quizlet tables
// ("Ma3 + pronouns", "La + Pronouns", "Other Prepositions + Pronouns"). Every add-on form is an engine guess
// (not checked by Amal) until she checks it. Verb tags (object yes/no, prepositions) come from data/verb-addons.json.
(function (root) {
  'use strict';
  const OBJ = ['me', 'you (m)', 'you (f)', 'you (pl)', 'him', 'her', 'us', 'them'];
  // Amal's tables, same order as OBJ. Arabic ma3o: her card says "ةعو" (typo) -> معو.
  const PREP = {
    ma3: { en: 'with', ar: ['معي', 'معك', 'معك', 'معكم', 'معو', 'معها', 'معنا', 'معهم'], z: ['ma3i', 'ma3ak', 'ma3ek', 'ma3kom', 'ma3o', 'ma3ha', 'ma3na', 'ma3hom'] },
    la: { en: 'to', ar: ['إلي', 'إلك', 'إلك', 'إلكم', 'إلو', 'إلها', 'إلنا', 'إلهم'], z: ['eli', 'elak', 'elek', 'elkom', 'elo', 'elha', 'elna', 'elhom'] },
    min: { en: 'from', ar: ['مني', 'منك', 'منك', 'منكم', 'منو', 'منها', 'منّا', 'منهم'], z: ['minni', 'mennak', 'mennek', 'minnkom', 'minno', 'menha', 'minna', 'minnhom'] },
    '3an': { en: 'about', ar: ['عنّي', 'عنك', 'عنك', 'عنكم', 'عنو', 'عنها', 'عنا', 'عنهم'], z: ['3anni', '3annak', '3annek', '3annkom', '3anno', '3anha', '3anna', '3anhom'] },
    '3ala': { en: 'on', ar: ['عليّ', 'عليك', 'عليكي', 'عليكم', 'عليه', 'عليها', 'علينا', 'عليهم'], z: ['3alay', '3alaik', '3alaiki', '3alaikom', '3alaih', '3alaiha', '3alaina', '3alaihom'] },
    fi: { en: 'in', ar: ['فيّي', 'فيك', 'فيكي', 'فيكم', 'فيّو', 'فيها', 'فينا', 'فيهم'], z: ['fiyyi', 'feek', 'feeki', 'feekom', 'feeyo', 'feeha', 'feena', 'feehom'] },
  };
  // Endings by the verb's last sound, same order as OBJ.
  const END = {
    C: ['ni', 'ak', 'ek', 'kom', 'o', 'ha', 'na', 'hom'],          // byesma3ni, bashoofek, bas2alkom, bet7ebbo, bas2alha
    I: ['ini', 'eek', 'eeki', 'ikom', 'eeh', 'iha', 'ina', 'ihom'], // bta3tini, ba3teek, basawweeh, btetbu5iha, bet7ebbina
    U: ['uni', 'ook', 'ooki', 'ukom', 'ooh', 'uha', 'una', 'uhom'], // beyshoofuni, bya5dook, bya3tooki, bye3tooh, btesma3una
    A: ['ani', 'aak', 'aaki', 'aakom', 'aah', 'aaha', 'aana', 'aahom'], // 3atani, bastannaah, btestannaahom
    T: ['tni', 'tak', 'tek', 'tkom', 'to', 'tha', 'tna', 'thom'],   // past -et: shuftak, akhadtak, 3refto
  };
  const AR_END = ['ني', 'ك', 'ك', 'كم', 'و', 'ها', 'نا', 'هم'];
  const SUBJ = { 'I': 'me', 'We': 'us', 'You (m)': 'you', 'You (f)': 'you', 'You (pl)': 'you' };
  const PRON_WORD = /^(ana|inta|inti|intu|huwwe|huwe|heyye|heiye|hiyye|i7na|e7na|humme|hume)\s+/i;

  function klass(word, tense, person) {
    const w = word.toLowerCase();
    if (tense === 'Past' && (person === 'I' || person === 'You (m)') && /et$/.test(w)) return 'T';
    if (/(i|ee|y)$/.test(w)) return 'I';
    if (/(u|oo|o)$/.test(w)) return 'U';
    if (/(a|aa)$/.test(w)) return 'A';
    return 'C';
  }
  function stem(word, k) {
    if (k === 'T') return word.replace(/et$/i, '');
    if (k === 'I') return word.replace(/(ee|i|y)$/i, '');
    if (k === 'U') return word.replace(/(oo|u|o)$/i, '');
    if (k === 'A') return word.replace(/(aa|a)$/i, '');
    return word;
  }
  // Geminate verbs double their last consonant before a vowel ending (bet7eb -> bet7ebbo), when the verb shows the double elsewhere.
  function attach(word, obj, opts) {
    const o = opts || {}, i = OBJ.indexOf(obj), k = klass(word, o.tense, o.person), end = END[k][i];
    let s = stem(word, k);
    if (k === 'C' && o.geminate && /^[aeiou]/.test(end) && !/(.)\1$/.test(s)) s += s.slice(-1);
    return s + end;
  }
  function attachAr(arabic, obj) {
    if (!arabic) return '';
    const i = OBJ.indexOf(obj);
    let s = arabic.replace(/وا$/, 'و').replace(/ى$/, 'ا');
    const vowel = /[يوا]$/.test(s);
    return s + (i === 4 && vowel ? 'ه' : AR_END[i]);
  }
  function split(text) { const m = String(text || '').match(PRON_WORD); return m ? [m[0], text.slice(m[0].length)] : ['', String(text || '')]; }
  function reflexive(person, obj) { const s = SUBJ[person]; return !!s && (obj === s || (s === 'you' && obj.startsWith('you'))); }

  let TAGS = {};
  function useTags(tags) { TAGS = tags || {}; }
  function tagsFor(verb) { return TAGS[verb] || { object: false, preps: ['ma3', 'la'] }; }

  function addons(card) {
    const t = tagsFor(card.verb), out = [];
    const phrase = /\s/.test(split(card.arabizi)[1].trim());     // verb + noun (2addait wa2et): the ending would land on the noun
    for (const obj of OBJ) {
      if (reflexive(card.person, obj)) continue;
      if (t.object && !phrase) out.push({ kind: 'obj', obj });
      for (const p of t.preps || []) if (PREP[p]) out.push({ kind: p, obj });
    }
    return out;
  }
  function apply(card, a, geminate) {
    const [pw, verb] = split(card.arabizi);
    const arPron = card.arabic ? (card.arabic.match(/^(أنا|إنت|إنتي|إنتو|هو|هي|إحنا|هم)\s+/) || [''])[0] : '';
    const arVerb = card.arabic ? card.arabic.slice(arPron.length) : '';
    const i = OBJ.indexOf(a.obj);
    let arabizi, arabic, en;
    if (a.kind === 'obj') {
      arabizi = pw + attach(verb, a.obj, { tense: card.tense, person: card.person, geminate });
      arabic = card.arabic ? arPron + attachAr(arVerb, a.obj) : '';
      en = card.english + ' ' + a.obj;
    } else {
      const p = PREP[a.kind];
      arabizi = card.arabizi + ' ' + p.z[i];
      arabic = card.arabic ? card.arabic + ' ' + p.ar[i] : '';
      en = card.english.replace(/!$/, '') + ' ' + p.en + ' ' + a.obj + (/!$/.test(card.english) ? '!' : '');
    }
    return { ...card, key: 'form:' + card.entry + ':' + card.person + ':' + a.kind + '-' + a.obj.replace(/[^a-z]/g, ''), arabizi, arabic, english: en,
      addon: a.kind + ':' + a.obj, guessed: true, level: 2 };
  }
  function decorate(card, random) {
    const list = addons(card); if (!list.length) return null;
    const a = list[Math.floor((random || Math.random)() * list.length)];
    return apply(card, a, tagsFor(card.verb).geminate);
  }

  const api = { OBJ, PREP, END, klass, attach, attachAr, addons, apply, decorate, useTags, tagsFor, reflexive };
  root.AneesVerbAddons = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
