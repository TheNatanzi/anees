// AM-26 (Medi 2026-10-06): Amal's level-2 list is cut to the verbs where the preposition matters.
const test=require('node:test'),assert=require('node:assert');
const D=require('../docs/js/verb-drills.js'),C=require('../docs/js/verb-check-core.js');
const {build}=require('../scripts/verb_addon_short_payload.cjs');
const list=require('../data/vocab/verb-short-list.json');
const V=D.verbs(require('../docs/data/word-bank-catalog.json'),require('../docs/data/words.json').items);
const p=build(V,list);
test('AM-26 every listed verb is in the catalog and the page accepts the payload',()=>{
  assert.deepStrictEqual(p.missing,[]);assert.ok(C.validPayload(p));
  assert.strictEqual(p.verbs.length,list.verbs.length);
});
test('plain verbs Medi named are left out; the ones he named stay',()=>{
  const keys=new Set(p.verbs.map(v=>v.key));
  for(const k of ['ana batbu5','ana bakul'])assert.ok(!keys.has(k),k);
  for(const k of ['ana ba7ki','ana ba3ti','ana badfa3','ana bad7ak'])assert.ok(keys.has(k),k);
});
test('badfa3 asks 3ala and 3an with their meanings; ba3ti asks the ending',()=>{
  assert.match(p.items['ana badfa3:addon:3an'].person,/pay for someone/);
  assert.match(p.items['ana badfa3:addon:3ala'].person,/pay for something/);
  assert.ok(p.items['ana ba3ti:addon:obj']);
});
test('item keys keep the long list shape so pull() reads them unchanged',()=>{
  for(const id of Object.keys(p.items))assert.match(id,/^.+:addon:(la|ma3|obj|3ala|fi|min|3an)$/);
  assert.ok(Object.keys(p.items).length<100);
});
