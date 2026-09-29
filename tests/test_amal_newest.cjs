// Newest Amal wins (Medi M1, 2026-09-29): her newer check-list spelling replaces an older Quizlet card, on the card and in
// every check; the imported Quizlet file itself stays as she made it.
const test=require('node:test'),assert=require('node:assert/strict');
const N=require('../docs/js/amal-newest.js');
const raw=require('../docs/data/quizlet/amal-quizlet-sets.json').sets,doc=require('../docs/data/quizlet/amal-newer-spellings.json');
const checks=require('../data/vocab/amal_verb_checks.json').answers;
test('the "they take you" card shows her newer byaa5dook',()=>{
 const s=N.apply(raw,doc).find(x=>x.title==='Pronoun Objects With Verbs');
 assert.ok(s.terms.some(t=>t[0].startsWith('Humme byaa5dook')));assert.ok(!s.terms.some(t=>/bya5dook/.test(t[0])));
 assert.ok(raw.find(x=>x.title==='Pronoun Objects With Verbs').terms.some(t=>t[0].startsWith('Humme bya5dook')),'raw import untouched');
});
test('every overlay row is backed by a newer Amal answer',()=>{
 const a=checks['ana ba5ud:present:They'];assert.equal(a.choice,'fix');assert.equal(a.word,'humme byaa5du');
 for(const r of doc.replace){assert.ok(r.why&&r.source&&r.from!==r.to);}
});
