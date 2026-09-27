// Flashcard boost (plan/SENTENCE-LADDER-SPEC-2026-09-27.md section 7): words that sank sentences he missed in a lesson.
const test=require('node:test'),assert=require('node:assert/strict');
const F=require('../docs/js/fsrs.js');globalThis.AneesFSRS=F;require('../docs/js/cards-core.js');const Q=globalThis.AneesCards;
const words=Array.from({length:30},(_,i)=>({key:'w'+i,doc_order:i}));
const catalog={groups:[{key:'w0',keys:['w0','w1','w2']},{key:'w3',keys:['w3','w4']}]};
const day=86400000,noon=new Date(2026,8,27,12).getTime(),iso=t=>new Date(t).toISOString();
const row=(id,k,t,result='got')=>({id,word_key:k,ts:iso(t),result});
// a card that reached review 10 days ago (due today): three Goods through the learning steps
const reviewed=(k,t)=>[row(k+'a',k,t),row(k+'b',k,t+60000),row(k+'c',k,t+700000)];
const B=(key,score,last='2026-09-26')=>({key,score,strong:0,weak:score,dates:[last],last,ids:[]});
const run=(log,boostList,n)=>{const cards=F.replay(log),boost=boostList?Q.boostMap(boostList,log):null;
 return Q.queue(words,cards,log,noon,Object.assign({siblings:Q.siblingMap(words,catalog)},n?{newPerDay:n}:{},boost?{boost}:{}));};

test('the boost weight has one home: AneesCards.BOOST',()=>{assert.equal(Q.BOOST.weight,3);assert.ok(Object.isFrozen(Q.BOOST));});

test('due boosted cards come first, highest score first; the rest keep learning -> reviews -> new',()=>{
 const log=[...reviewed('w20',noon-10*day),...reviewed('w21',noon-10*day+1000),...reviewed('w22',noon-10*day+2000),row('l1','w23',noon-120000,'missed')];
 const plain=run(log);
 assert.deepEqual(plain.items.slice(0,4).map(c=>c.id),['w23','w20','w21','w22']);
 const q=run(log,[B('w22',1),B('w21',2)]);
 assert.deepEqual(q.items.slice(0,4).map(c=>c.id),['w21','w22','w23','w20']);
 assert.deepEqual(q.boosted,['w21','w22']);assert.equal(q.counts.boosted,2);
 assert.equal(q.counts.due,plain.counts.due);assert.equal(q.counts.new,plain.counts.new);   // same cards, only the order moved
});

test('a boosted card that is not due yet stays where FSRS put it (never pulled forward)',()=>{
 const log=reviewed('w20',noon-3600000);   // reviewed an hour ago: not due today
 const q=run(log,[B('w20',5)]);assert.ok(!q.items.some(c=>c.id==='w20'));assert.equal(q.counts.boosted,0);
});

test('boosted unseen words take the new slots first, and the 8-a-day cap still holds',()=>{
 const q=run([],[B('w25',1),B('w17',3),B('w9',2)]);
 assert.equal(q.counts.new,8);assert.equal(q.room,8);
 assert.deepEqual(q.items.slice(0,3).map(c=>c.id),['w17','w9','w25']);
 assert.deepEqual(q.items.slice(3).map(c=>c.id),['w0','w3','w5','w6','w7']);   // then doc order, siblings w1 w2 w4 buried
 const full=run(Array.from({length:8},(_,i)=>row('n'+i,'w'+(10+i),noon-3600000)),[B('w25',4)]);
 assert.equal(full.counts.new,0);assert.ok(!full.items.some(c=>c.id==='w25'));   // cap used up: no room even for a boosted word
});

test('sibling burying still holds: a boosted form wins its family slot, its siblings wait',()=>{
 const q=run([],[B('w2',2)]);const keys=q.items.map(c=>c.id);
 assert.equal(keys[0],'w2');assert.ok(!keys.includes('w0')&&!keys.includes('w1'));
 const answered=run([row('a','w0',noon-3600000,'missed')],[B('w1',2)]);   // a sibling answered today buries the boosted form
 assert.ok(!answered.items.some(c=>c.id==='w1'&&!c.reps));
});

test('boostMap: a word he got right on a card after the lesson day drops out; a card miss keeps it',()=>{
 const list=[B('w1',2,'2026-09-26'),B('w2',1,'2026-09-26'),B('w3',1,'2026-09-26'),{key:'bad',score:0,last:'2026-09-26'},{key:'nodate',score:1}];
 const log=[row('g','w1',new Date(2026,8,27,9).getTime()),row('m','w2',new Date(2026,8,27,9).getTime(),'missed'),row('s','w3',new Date(2026,8,26,20).getTime())];
 const m=Q.boostMap(list,log);
 assert.deepEqual([...m.keys()],['w2','w3']);   // w1 cleared; w3's Good was the same day as the lesson, so it stays
 assert.equal(Q.boostMap(list,[{...log[0],undone:true}]).has('w1'),true);   // an undone Good never clears it
});

test('the chip names the lesson day',()=>{
 assert.equal(Q.boostLabel(B('w1',1,'2026-09-26')),'boosted: missed in lesson 26 Sep');
 assert.equal(Q.boostLabel({}),'');
});

test('practice draws weigh a boosted word BOOST.weight times more',()=>{
 const ws=[{key:'a'},{key:'b'}],boost=new Map([['a',B('a',1)]]);let a=0;
 for(let s=1;s<=400;s++)if(Q.draw(ws,{},1,s,boost)[0].key==='a')a++;
 assert.ok(a>260&&a<340,'a drawn '+a+' of 400 (expect about 300)');
 assert.equal(Q.draw(ws,{},2,7,boost).length,2);   // still without replacement
});
