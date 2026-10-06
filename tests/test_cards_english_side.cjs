const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const S=require('../docs/js/cards-selection.js');
// FC-12 / F14: the English side of a flashcard never carries the Arabic answer in Latin letters (Medi 2026-10-05:
// "Remove the bel 3aks here from the flash card it's too much of a hint"). The Doc text is not edited; the card face strips it.
test('FC-12 stripArabiziHints cuts the Arabizi gloss and keeps the English',()=>{
  assert.equal(S.stripArabiziHints('opposite (bel-3aks = on the contrary)'),'opposite');
  assert.equal(S.stripArabiziHints('I break down / go bad (food: bye5rab = it spoils)'),'I break down / go bad');
  assert.equal(S.stripArabiziHints('the world / people (el-3aalam)'),'the world / people');
  assert.equal(S.stripArabiziHints('it / him (object: biddna iyyah = we want it)'),'it / him');
  assert.equal(S.stripArabiziHints('get well soon response (f) / Response to "Tewsal bil-salaame" or "Al-7amdellah 3al-salaame"'),'get well soon response (f)');
  assert.equal(S.stripArabiziHints('water (uncountable)'),'water (uncountable)');
  assert.equal(S.stripArabiziHints('Bird · birds (general)'),'Bird · birds (general)');
  assert.equal(S.stripArabiziHints('maqluba (upside-down rice dish)'),'maqluba (upside-down rice dish)');
});
function rows(p){const d=JSON.parse(fs.readFileSync(path.join(__dirname,'..',p),'utf8'));return Array.isArray(d)?d:(d.items||d.rows||[]);}
for (const p of ['docs/data/words.json','docs/data/amal-add-words.json']) test('FC-12 every English side of '+p+' is clean after the strip',()=>{
  const bad=rows(p).map(w=>S.stripArabiziHints(w.english)).filter(e=>S.ARABIZI.test(e));
  assert.deepEqual(bad,[]);
});
