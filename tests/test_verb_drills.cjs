const test=require('node:test'),assert=require('node:assert/strict');
const D=require('../docs/js/verb-drills.js');
const WB=require('../docs/js/word-bank-core.js');
const catalog=require('../docs/data/word-bank-catalog.json');
const words=require('../docs/data/words.json').items;
const V=D.verbs(catalog,words);
const all=V.flatMap(v=>Object.values(v.tenses).flat());

test('English cues: Amal\'s own past gloss, 3rd person -s, commands, be-phrases',()=>{
 const know=V.find(v=>v.verb==='ana ba3raf');
 assert.equal(know.tenses.Past.find(c=>c.person==='She').english,'she · knew');
 assert.equal(know.tenses.Present.find(c=>c.person==='He').english,'he · knows');
 assert.equal(know.tenses.Command.find(c=>c.person==='You (pl)').english,'you (pl) · know!');
 assert.equal(D.third('wash dishes'),'washes dishes');assert.equal(D.third('study'),'studies');assert.equal(D.third('do/make'),'does/makes');
 assert.equal(D.pastRule('stop'),'stopped');assert.equal(D.pastRule('lie'),'lied');assert.equal(D.pastRule('go out'),'went out');
 assert.ok(all.every(c=>/^(I|you \((m|f|pl)\)|he|she|we|they) · \S/.test(c.english)),'every cue starts with its person');
});

test('card keys: Doc word key when the person form is in the Doc, else form:<entry>:<person>; guesses tagged',()=>{
 const know=V.find(v=>v.verb==='ana ba3raf');
 assert.equal(know.tenses.Past.find(c=>c.person==='I').key,'ana 3refet');
 const guess=know.tenses.Present.find(c=>c.person==='You (m)');
 assert.equal(guess.key,'form:ana ba3raf:present:You (m)');assert.equal(guess.guessed,true);
 assert.equal(know.tenses.Command.find(c=>c.person==='You (f)').guessed,false);
 assert.equal(new Set(all.map(c=>c.key)).size,all.length,'no two drill cards share a key');
});

test('Amal checked forms: not a guess any more, tagged checked (check list 1, 2026-09-22)',()=>{
 const learn=V.find(v=>v.verb==='ana ba7faz');
 const she=learn.tenses.Present.find(c=>c.person==='She');
 assert.equal(she.arabizi,'heyye bte7faz');assert.equal(she.guessed,false);assert.equal(she.checked,true);
 assert.equal(learn.tenses.Command.find(c=>c.person==='You (pl)').checked,true);
 assert.equal(all.filter(c=>c.checked).length,41);
 assert.ok(all.every(c=>!(c.checked&&c.guessed)));
});

test('20 random verbs: each verb once, tense from the option',()=>{
 for(const tense of ['All','Past','Present','Command']){
  const r=D.round(V,{mode:'random',count:20,tense,random:D.rng(7)});
  assert.equal(r.length,20);assert.equal(new Set(r.map(c=>c.verb)).size,20);
  if(tense!=='All')assert.ok(r.every(c=>c.tense===tense));
 }
 const tenses=new Set(D.round(V,{mode:'random',count:144,random:D.rng(3)}).map(c=>c.tense));
 assert.deepEqual([...tenses].sort(),['Command','Past','Present']);
});

test('5 or 10 verbs full: every person of the chosen tenses',()=>{
 const five=D.round(V,{mode:'full',count:5,tense:'All',random:D.rng(1)});
 assert.equal(five.length,5*(8+8+3));
 const ten=D.round(V,{mode:'full',count:10,tense:'Command',random:D.rng(2)});
 assert.equal(ten.length,30);assert.ok(ten.every(c=>c.tense==='Command'));
});

test('a drill answer counts on the right tense in the Word Bank / Progress model',()=>{
 const know=V.find(v=>v.verb==='ana ba3raf');
 const log=[know.tenses.Command.find(c=>c.person==='You (f)'),know.tenses.Present.find(c=>c.person==='They')].map((c,i)=>({id:'d'+i,word_key:c.key,ts:'2026-09-23T10:0'+i+':00Z',result:'got',attempt:1}));
 const row=WB.models(words,catalog,[],log).find(r=>r.id==='ana ba3raf');
 const by=Object.fromEntries(row.entries.map(f=>[f.label,f.flashcards.count]));
 assert.equal(by.Command,1);assert.equal(by.Present,1);assert.equal(by.Past,0);
});
