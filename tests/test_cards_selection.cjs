const test=require('node:test'),assert=require('node:assert/strict');
const WB=require('../docs/js/word-bank-core.js');
const S=require('../docs/js/cards-selection.js');
const sets=require('../docs/data/quizlet/amal-quizlet-sets.json').sets;
const catalog=require('../docs/data/word-bank-catalog.json');

const words=[
 {key:'ana batbu5',arabizi:'ana batbu5',arabic:'بطبخ',english:'I cook',topic:'Verbs List',doc_order:1},
 {key:'inta taba5et',arabizi:'inta taba5et',arabic:'إنت طبخت',english:'you cooked',topic:'Past Tense',doc_order:2},
 {key:'bait',arabizi:'bait',arabic:'بيت',english:'house',plural:'byoot',topic:'Household Items',subtopic:'Rooms',doc_order:3},
 {key:'marhaba',arabizi:'marhaba',arabic:'مرحبا',english:'hello',plural:'—',topic:'Introductions and Pleasantries',doc_order:4},
 {key:'7elu',arabizi:'7elu',arabic:'حلو',english:'sweet',topic:'Adjectives',doc_order:5},
];
const cat={groups:[{id:'ana batbu5',key:'ana batbu5',keys:['ana batbu5','inta taba5et'],type:'Verb',name:'Batbu5',arabic:'بطبخ',english:'I cook',topic:'Verbs List',
 entries:[{id:'v:present',label:'Present',word:'batbu5',arabic:'بطبخ',keys:['ana batbu5'],persons:[]},{id:'v:past',label:'Past',word:'taba5et',arabic:'طبخت',keys:['inta taba5et'],persons:[]}]},
 {id:'7elu',key:'7elu',keys:['7elu'],type:'Adjective',name:'7elu',arabic:'حلو',english:'sweet',topic:'Adjectives',entries:[{id:'a:w',label:'Word',word:'7elu',arabic:'حلو',keys:['7elu'],persons:[]}]}]};
const card=(k,r,d,id)=>({id,word_key:k,ts:`2026-09-${d}T10:00:00Z`,result:r,attempt:1});

test('term text splits on | and finds the Arabic side either way round',()=>{
 assert.deepEqual(S.splitTerm('مرحبا | marhaba'),{arabic:'مرحبا',arabizi:'marhaba'});
 assert.deepEqual(S.splitTerm('marhaba | مرحبا'),{arabic:'مرحبا',arabizi:'marhaba'});
 assert.deepEqual(S.splitTerm('keefak?'),{arabic:'',arabizi:'keefak?'});
});
test('a matching Quizlet term reuses the Doc word key; the rest get q:<set>:<rank>',()=>{
 const set={id:'9',title:'T',terms:[['مرحبا | marhaba','Hello'],['بيت | beit','house'],['','blank'],['زهرة | zahra','flower']]};
 const out=S.quizletCards(set,S.matcher(words));
 assert.deepEqual(out.map(c=>c.key),['marhaba','bait','q:9:4']);  // blank side skipped; rank = position in the set
 assert.equal(out[2].arabizi,'zahra');assert.equal(out[2].arabic,'زهرة');assert.equal(out[2].english,'flower');
 assert.ok(S.isQuizletOnly('q:9:4'));assert.ok(!S.isQuizletOnly('bait'));
});
test('ambiguous Arabic never matches a Doc word',()=>{
 const two=[{key:'a',arabizi:'huwwe',arabic:'هو'},{key:'b',arabizi:'hu',arabic:'هو'}];
 assert.equal(S.matcher(two)({arabic:'هو',arabizi:''}),null);
 assert.equal(S.matcher(two)({arabic:'هو',arabizi:'huwwe'}).key,'a');
});
test('all 106 imported sets parse; every blank-sided term (6) is skipped',()=>{
 const match=S.matcher([]);let terms=0,cards=0;
 for(const set of sets){terms+=set.terms.length;cards+=S.quizletCards(set,match).length;}
 assert.equal(sets.length,106);assert.equal(terms,2330);
 const blanks=sets.flatMap(s=>s.terms).filter(([a,b])=>!String(a||'').trim()||!String(b||'').trim()).length;
 assert.equal(blanks,6);assert.ok(cards<=terms-blanks);
});
test('Quizlet groups: named sets once each, dated sets hidden (Medi 2026-09-22); collocation sets found',()=>{
 const g=S.quizletGroups(sets);
 assert.deepEqual(g.map(x=>x.name),['Plurals','Possession & pronouns','Verbs','Topics']);
 const dated=sets.filter(s=>S.isDated(s.title));
 assert.equal(g.reduce((n,x)=>n+x.sets.length,0),106-dated.length);
 const shown=g.flatMap(x=>x.sets.map(s=>s.title));
 for(const t of ['December 12 Verbs','March 15 Audio Homework','Friday December 5, 2025','Feb 12 Emotions','May 2 Audio Homework','January 2 verbs']){assert.ok(S.isDated(t),t);assert.ok(!shown.includes(t),t);}
 for(const t of ['Colors','Command','Audio Homework','Mishwaar-Mashaweer Plural List','Pleasantries PT1','Adjectives (PT2)']) assert.ok(!S.isDated(t),t);
 const by=Object.fromEntries(g.map(x=>[x.id,x.sets.map(s=>s.title)]));
 assert.ok(by.plurals.includes('Family Plurals'));assert.ok(by.possession.includes('Possessive Forms'));assert.ok(by.verbs.includes('Command'));assert.ok(by.topics.includes('Colors'));
 const c=S.collocationSets(sets);assert.deepEqual(c.map(s=>s.terms.length),[36,25]);
});
test('Set colour counts: mastered / good / shaky / wrong / untested from the flashcard bucket',()=>{
 const b={a:'ice_cold',b:'cold',c:'shaky',d:'missed',e:'never',f:'new'};
 assert.deepEqual(S.scoreMix(Object.keys(b).map(key=>({key})),w=>b[w.key]),{mastered:1,good:1,shaky:1,wrong:1,untested:2});
 assert.deepEqual(S.MIX,['mastered','good','shaky','wrong','untested']);
 assert.deepEqual(S.scoreMix([{key:'x'},{key:'y'}],w=>({x:'Mastered',y:'Wrong'})[w.key]),{mastered:1,good:0,shaky:0,wrong:1,untested:0});
 const st=S.statusByKey([{entries:[{keys:['k1'],speaking:{status:'Shaky'},flashcards:{status:'Good'}},{keys:['k2'],speaking:{status:'Untested'},flashcards:{status:'Wrong'}},{keys:['k3'],speaking:{status:'Untested'},flashcards:{status:'Untested'}}]}]);
 assert.equal(st.get('k1'),'Shaky');assert.equal(st.get('k2'),'Wrong');assert.equal(st.has('k3'),false);   // lessons first, else cards, untested = absent
});
test('Shaky / Wrong split by lane and by word type (Verb / Noun / Adjective / Other)',()=>{
 const log=[card('bait','missed','01','c1'),card('bait','missed','02','c2'),card('bait','missed','03','c3'),card('7elu','missed','04','c4')];
 const rows=WB.models(words,cat,[],log);const out=S.statusSplit(rows,words);
 assert.equal(Object.keys(out).length,20);   // 2 statuses x 2 lanes x (All + 4 types)
 assert.deepEqual(out['Wrong|flashcards|All'].map(w=>w.key),['bait']);
 assert.deepEqual(out['Wrong|flashcards|Noun'].map(w=>w.key),['bait']);
 assert.deepEqual(out['Shaky|flashcards|Adjective'].map(w=>w.key),['7elu']);
 assert.equal(out['Wrong|speaking|Noun'].length,0);   // cards never leak into the lesson lane
 const types=Object.fromEntries(rows.map(r=>[r.key,S.typeOf(r)]));
 assert.deepEqual(types,{'ana batbu5':'Verb','7elu':'Adjective',bait:'Noun',marhaba:'Other'});
});
test('undone answers do not count as tested',()=>{
 const log=[card('bait','got','01','c1'),{...card('7elu','got','01','c2'),undone_at:'2026-09-01T10:01:00Z'}];
 assert.deepEqual(S.neverTested(words,log).map(w=>w.key),['ana batbu5','inta taba5et','marhaba','7elu']);
});
test('new from Amal = the existing new bucket',()=>{
 const stats={bait:{progress_context:{new:true}},marhaba:{bucket:'new'},'7elu':{progress_context:{new:false}}};
 assert.deepEqual(S.newFromAmal(words,stats).map(w=>w.key),['bait','marhaba']);
});
test('verb tenses = Doc topic plus the catalog forms of that tense',()=>{
 const t=Object.fromEntries(S.tenses(words,cat).map(x=>[x.id,x.words.map(w=>w.key)]));
 assert.deepEqual(t,{Present:['ana batbu5'],Past:['inta taba5et'],Command:[]});
 assert.ok(S.tenses([],catalog).every(x=>x.words.length===0));
});
test('Doc categories carry their sub-topics',()=>{
 const t=S.topics(words);const h=t.find(x=>x.name==='Household Items');
 assert.equal(t.length,5);assert.deepEqual(h.subs.map(s=>[s.name,s.words.length]),[['Rooms',1]]);
});
test('a scored form with no Doc key still gets a card, and Word Bank maps its answers back',()=>{
 const c={groups:[{id:'v',key:'v',keys:['v'],type:'Verb',name:'Basaa3ed',arabic:'بساعد',english:'I help',topic:'Verbs List',
  entries:[{id:'v:past',label:'Past',word:'saa3adet',arabic:'ساعدت',keys:[],persons:[]}]}]};
 const ws=[{key:'v',arabizi:'ana basaa3ed',arabic:'بساعد',english:'I help',topic:'Verbs List'}];
 const log=[1,2,3].map(i=>card('form:v:past','missed','0'+i,'f'+i));
 const rows=WB.models(ws,c,[],log);const past=rows[0].entries.find(f=>f.label==='Past');
 assert.equal(past.flashcards.count,3);assert.equal(past.speaking.count,0);
 const out=S.statusSplit(rows,ws);const cardFor=out['Wrong|flashcards|Verb'][0];
 assert.equal(cardFor.key,'form:v:past');assert.equal(cardFor.arabizi,'saa3adet');assert.equal(cardFor.english,'I help (past)');
 assert.ok(S.isFormCard(cardFor.key));
});
