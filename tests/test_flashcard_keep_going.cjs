// Keep going after a round (Medi 2026-09-30): 67 cards in rounds of 20 -> 20, 20, then ask "13 + 14" or "all 27".
const test=require('node:test'),assert=require('node:assert/strict');
globalThis.AneesFSRS=require('../docs/js/fsrs.js');require('../docs/js/cards-core.js');const Q=globalThis.AneesCards;

test('67 cards in 20s: next, next, then ask 13 + 14 or all 27',()=>{
 assert.deepEqual(Q.nextChunk(47,20),{kind:'next',n:20,left:47});
 assert.deepEqual(Q.nextChunk(27,20),{kind:'ask',all:27,a:13,b:14});
 assert.deepEqual(Q.nextChunk(14,20),{kind:'last',n:14});      // after the 13 half, the 14 come next
});
test('edges: exactly two batches is a plain next; one batch or less is the last round; none left or All = nothing',()=>{
 assert.equal(Q.nextChunk(40,20).kind,'next');
 assert.deepEqual(Q.nextChunk(20,20),{kind:'last',n:20});
 assert.deepEqual(Q.nextChunk(21,20),{kind:'ask',all:21,a:10,b:11});
 assert.equal(Q.nextChunk(0,20).kind,'none');
 assert.equal(Q.nextChunk(30,0).kind,'none');
});

// Known cards go to the back of the set (Medi 2026-09-30)
test('a card whose latest swipe was Know goes to the back; order kept in each half; undo and later misses count',()=>{
 const W=['a','b','c','d','e'].map(key=>({key}));
 const log=[{word_key:'a',ts:'2026-09-30T01:00:00Z',result:'got'},
  {word_key:'b',ts:'2026-09-30T01:00:00Z',result:'got'},{word_key:'b',ts:'2026-09-30T02:00:00Z',result:'missed'},  // known, then missed -> front
  {word_key:'c',ts:'2026-09-30T01:00:00Z',result:'got',undone:true},                                                // undone -> not known
  {word_key:'e',ts:'2026-09-30T03:00:00Z',result:'got'}];
 const {rest,known}=Q.splitKnown(W,log);
 assert.deepEqual(rest.map(w=>w.key),['b','c','d']);
 assert.deepEqual(known.map(w=>w.key),['a','e']);
});

// A missed card comes back in the same round, 3 cards later, until known once; undo takes it all back (Medi 2026-09-30)
test('missed card comes back 3 cards later; counts are per card; undo removes the comeback',()=>{
 const r=Q.newRound(['a','b','c','d','e'].map(key=>({key})),{});
 Q.answer(r,'missed','2026-09-30T10:00:00Z','1');
 assert.deepEqual(r.cards.map(w=>w.key),['a','b','c','d','a','e']);
 assert.equal(r.missed,1);
 Q.undo(r); assert.deepEqual(r.cards.map(w=>w.key),['a','b','c','d','e']); assert.equal(r.i,0); assert.equal(r.wrong.length,0);
 Q.answer(r,'missed','t','1'); for(let i=0;i<5;i++) Q.answer(r,'got','t','x'+i);
 assert.ok(Q.done(r)); const s=Q.summary(r);
 assert.equal(s.n,5); assert.equal(s.got,5); assert.equal(s.missed,0); assert.equal(s.firstTry,4); assert.deepEqual(s.wrong,['a']);
});
test('a card missed near the end comes back at the end',()=>{
 const r=Q.newRound([{key:'a'},{key:'b'}],{}); Q.answer(r,'got','t','1'); Q.answer(r,'missed','t','2');
 assert.deepEqual(r.cards.map(w=>w.key),['a','b','b']); assert.ok(!Q.done(r));
});

// Singular / plural: which one was missed (Medi 2026-09-30)
test('one swipe on a two-form card writes the singular and the plural row; scheduling sees one answer, missed if either is',()=>{
 const row={id:'r1',word_key:'jumle',ts:'2026-09-30T10:00:00Z',result:'missed'};
 const pl=Q.partRows(row,'jumle','plural');
 assert.deepEqual(pl.map(r=>[r.id,r.word_key,r.result]),[['r1','jumle','got'],['r1-pl','form:jumle:plural','missed']]);
 assert.deepEqual(Q.partRows(row,'jumle','singular').map(r=>r.result),['missed','got']);
 assert.deepEqual(Q.partRows(row,'jumle','both').map(r=>r.result),['missed','missed']);
 assert.deepEqual(Q.partRows({...row,result:'got'},'jumle',null).map(r=>r.result),['got','got']);
 const s=Q.schedLog(pl); assert.equal(s.length,1); assert.equal(s[0].word_key,'jumle'); assert.equal(s[0].result,'missed');
 const knew=Q.schedLog(Q.partRows({...row,result:'got'},'jumle',null)); assert.deepEqual(knew.map(r=>r.result),['got']);
 const undone=Q.schedLog([pl[0],{...pl[1],undone:true}]); assert.equal(undone[0].result,'got');
});

// New untested words = added to the Doc after the first import; the day's amount = Amal's latest batch (Medi 2026-09-30)
test('curriculum: import day is old, later days are new, batch = the latest day; old words pass the cap',()=>{
 const W=[...Array(5)].map((_,i)=>({key:'old'+i,first_seen:'2026-09-05T10:00:00Z'})).concat(
   [...Array(3)].map((_,i)=>({key:'a'+i,first_seen:'2026-09-18T10:00:00Z'})),[...Array(2)].map((_,i)=>({key:'b'+i,first_seen:'2026-09-23T10:00:00Z'})));
 const c=Q.curriculum(W); assert.equal(c.importDay,'2026-09-05'); assert.equal(c.newKeys.size,5); assert.equal(c.batch,2);
 const cap=Q.capNew(W,[],Date.parse('2026-09-30T12:00:00Z'),{newPerDay:c.batch,isNew:k=>c.newKeys.has(k)});
 assert.equal(cap.cards.length,7); assert.equal(cap.held,3);                 // 5 old + 2 new open, 3 new wait
 assert.equal(Q.curriculum(W.map(w=>({key:w.key}))).newKeys.size,0);        // no dates -> nothing limited
});
