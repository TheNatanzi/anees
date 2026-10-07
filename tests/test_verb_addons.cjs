const test=require('node:test'),assert=require('node:assert/strict');
const A=require('../docs/js/verb-addons.js'),D=require('../docs/js/verb-drills.js'),WB=require('../docs/js/word-bank-core.js');
const G=require('../scripts/verb_addons_golden.cjs');
const catalog=require('../docs/data/word-bank-catalog.json'),words=require('../docs/data/words.json').items,tags=require('../docs/data/verb-addons.json');

test('object endings follow the verb\'s last sound (Amal\'s examples)',()=>{
 assert.equal(A.attach('byesma3','me'),'byesma3ni');assert.equal(A.attach('bas2al','her'),'bas2alha');
 assert.equal(A.attach('ba3ti','you (m)'),'ba3teek');assert.equal(A.attach('basawwi','him'),'basawweeh');
 assert.equal(A.attach('bya5du','you (m)'),'bya5dook');assert.equal(A.attach('btesma3u','us'),'btesma3una');
 assert.equal(A.attach('3ata','me'),'3atani');assert.equal(A.attach('akhadet','you (m)',{tense:'Past',person:'I'}),'akhadtak');
 assert.equal(A.attach('bet7eb','him',{geminate:true}),'bet7ebbo');assert.equal(A.attach('ba7eb','them',{geminate:true}),'ba7ebhom');
 assert.equal(A.attachAr('بيعطوا','him'),'بيعطوه');assert.equal(A.attachAr('بستنى','him'),'بستناه');assert.equal(A.attachAr('بتحب','him'),'بتحبو');
});

test('golden: Amal\'s 25 "Pronoun Objects With Verbs" (floors; misses = her typos + base spellings)',()=>{
 const r=G.report;assert.equal(r.matched_verb,25);assert.ok(r.exact>=16,JSON.stringify(r));assert.ok(r.sound_alike>=20);assert.ok(r.arabic_exact>=23);
});

test('prepositions use Amal\'s own tables; no "I ... with me"',()=>{
 assert.deepEqual(A.PREP.ma3.z,['ma3i','ma3ak','ma3ek','ma3kom','ma3o','ma3ha','ma3na','ma3hom']);
 assert.equal(A.reflexive('I','me'),true);assert.equal(A.reflexive('You (f)','you (pl)'),true);assert.equal(A.reflexive('He','him'),false);
 A.useTags(tags.verbs);
 const V=D.verbs(catalog,words),card=V.find(v=>v.verb==='ana ba3raf').tenses.Past.find(c=>c.person==='I');
 const list=A.addons(card);assert.ok(list.every(a=>a.obj!=='me'));assert.ok(list.some(a=>a.kind==='3an'));   // AM-26: 3irif 3an = know about
 const c=A.apply(card,{kind:'ma3',obj:'them'});assert.equal(c.arabizi,'Ana 3refet ma3hom');assert.equal(c.english,'I · knew with them');
 const o=A.apply(card,{kind:'obj',obj:'him'});assert.equal(o.arabizi,'Ana 3refto');assert.equal(o.arabic,'أنا عرفتو');
 assert.equal(o.key,'form:ana ba3raf:past:I:obj-him');assert.equal(o.guessed,true);
});

test('AM-26 only the short-list verbs get add-ons; plain verbs never come up at level 2; answers count on the tense entry',()=>{
 A.useTags(tags.verbs);
 const short=new Set(require('../data/vocab/verb-short-list.json').verbs.map(v=>v.verb));
 for(const [k,t] of Object.entries(tags.verbs))if(!short.has(k)&&!t.amal_forms)assert.ok(!A.hasAddons(k),k);
 assert.ok(!A.hasAddons('ana batbu5')||tags.verbs['ana batbu5'].preps.length===0);assert.ok(A.hasAddons('ana badfa3'));
 const V=D.verbs(catalog,words),r=D.round(V,{mode:'random',count:20,level:2,random:D.rng(5)});
 assert.equal(r.length,20);assert.ok(r.every(c=>short.has(c.verb)));assert.ok(r.every(c=>c.level===2&&/^form:.+:.+:(obj|ma3|la|fi|3ala|min|3an)-/.test(c.key)));
 const log=[{id:'a',word_key:r[0].key,ts:'2026-09-23T10:00:00Z',result:'got',attempt:1}];
 const row=WB.models(words,catalog,[],log).find(x=>x.id===r[0].verb);
 assert.equal(row.entries.find(f=>f.label===r[0].tense).flashcards.count,1);
});

test('phrase verbs (verb + noun) never get an ending glued onto the noun',()=>{
 A.useTags(tags.verbs);const V=D.verbs(catalog,words);
 const phrase=V.filter(v=>/\s/.test(v.name.trim()));assert.ok(phrase.length>0);
 for(const v of phrase)for(const c of Object.values(v.tenses).flat())assert.ok(A.addons(c).every(a=>a.kind!=='obj'),v.name);
});
