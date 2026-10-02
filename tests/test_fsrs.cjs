const test=require('node:test'),assert=require('node:assert/strict');
const F=require('../docs/js/fsrs.js');
// Golden rows from the official py-fsrs Scheduler (FSRS-6 defaults, fuzz off),
// generated once and checked in so the test needs no Python.
const golden=require('./fixtures/fsrs-py-golden.json');
const DAY=86400000,T0=Date.UTC(2026,8,21,15);
const close=(a,b,msg)=>assert.ok(Math.abs(a-b)<1e-9,`${msg}: ${a} vs ${b}`);

test('matches py-fsrs exactly for every sequence and retention',()=>{
 for(const [name,rows] of Object.entries(golden)){
  const ret=Number(name.split('@')[1]);let c=F.newCard('x');
  rows.forEach((r,i)=>{
   c=F.schedule(c,r.grade,r.ts,{desiredRetention:ret,learningSteps:[1,10],relearningSteps:[10]});   // py-fsrs step defaults; Anees ships shorter steps (see below)
   const at=`${name} #${i}`;
   close(c.stability,r.stability,at+' stability');close(c.difficulty,r.difficulty,at+' difficulty');
   assert.equal(c.due,r.due,at+' due');assert.equal(c.state,r.state,at+' state');assert.equal(c.step,r.step,at+' step');
  });
 }
});
test('published default parameters are FSRS-6, 21 weights',()=>{
 assert.equal(F.W.length,21);assert.equal(F.W[0],0.212);assert.equal(F.W[20],0.1542);
 assert.deepEqual(F.RETENTIONS,[0.8,0.85,0.9,0.95]);assert.equal(F.DEFAULTS.desiredRetention,0.9);
});
test('binary grades only: Hard and Easy are refused',()=>{
 for(const g of ['hard','easy','2','4',''])assert.throws(()=>F.rating(g));
 assert.equal(F.rating('got'),F.GOOD);assert.equal(F.rating('missed'),F.AGAIN);
});
test('retrievability is 90% after exactly one stability interval',()=>{
 const c={...F.newCard(),stability:10,last_review:T0};
 close(F.retrievability(c,T0+10*DAY),0.9,'R(S)');
 assert.equal(F.retrievability(c,T0),1);assert.equal(F.retrievability(F.newCard(),T0),0);
});
test('higher desired retention gives shorter intervals',()=>{
 const iv=[0.8,0.85,0.9,0.95].map(r=>F.nextInterval(20,{desiredRetention:r}));
 for(let i=1;i<iv.length;i++)assert.ok(iv[i]<iv[i-1],iv.join(','));
 assert.equal(F.nextInterval(20,{desiredRetention:0.9}),20);
});
test('phases: New, Learning under 21 days, Mature at 21',()=>{
 assert.equal(F.phase(F.newCard()),'new');
 assert.equal(F.phase({reps:1,state:'learning',interval:0}),'learning');
 assert.equal(F.phase({reps:5,state:'review',interval:20}),'learning');
 assert.equal(F.phase({reps:5,state:'review',interval:21}),'mature');
 assert.equal(F.phase({reps:9,state:'relearning',interval:0}),'learning');
});
test('lapses count only Again on a review card (misses count every Again)',()=>{
 let c=F.newCard();c=F.schedule(c,'again',T0);c=F.schedule(c,'again',T0+60000);assert.equal(c.lapses,0);assert.equal(c.misses,2);
 const rows=golden['many_lapses@0.9'];c=F.newCard();
 rows.forEach(r=>{c=F.schedule(c,r.grade,r.ts,{learningSteps:[1,10],relearningSteps:[10]});});
 assert.equal(c.lapses,9);assert.ok(c.misses>=c.lapses);
});
test('FC-07 leech at 3 misses in any phase, one rule only (Medi 2026-10-02 "actually lets make it 3")',()=>{
 let c=F.newCard('7Ades');['missed','got','missed','got'].forEach((g,i)=>{c=F.schedule(c,g,T0+i*90000);});   // the 2026-09-27 audit case
 assert.equal(c.misses,2);assert.equal(c.lapses,0);assert.equal(F.isLeech(c),false);              // 2 misses = not a leech
 assert.deepEqual(F.leechDistance(c),{misses:2,limit:3,left:1});
 c=F.schedule(c,'missed',T0+5*90000);assert.equal(c.misses,3);assert.equal(F.isLeech(c),true);   // 3 = leech (learning misses count)
 assert.equal(F.leechLabel(c),'Leech · 3 misses');
 assert.equal(F.isLeech({lapses:20,misses:2}),false);              // no lapse path: lapses alone never make a leech
 assert.equal(F.isLeech({misses:3},{leechMisses:0}),false);        // 0 turns the rule off
 assert.equal(F.DEFAULTS.leechMisses,3);                           // the default can't silently change
 assert.equal('leechLapses' in F.DEFAULTS,false);
});
test('learning ladder fits one 7-minute session: Again 1 min, second step 4 min, relearning 4 min',()=>{
 const o=F.DEFAULTS;assert.deepEqual(o.learningSteps,[1,4]);assert.deepEqual(o.relearningSteps,[4]);assert.equal(o.sessionMinutes,7);
 assert.ok(o.learningSteps.reduce((a,b)=>a+b,0)<o.sessionMinutes,'a miss plus both steps still ends inside the block');
 let c=F.schedule(F.newCard(),'again',T0);assert.equal(c.due-T0,60000);
 c=F.schedule(c,'good',T0+60000);assert.equal(c.state,'learning');assert.equal(c.due-(T0+60000),4*60000);
 c=F.schedule(c,'good',T0+5*60000);assert.equal(c.state,'review');
 const t=c.due;c=F.schedule(c,'again',t);assert.equal(c.due-t,4*60000);assert.equal(c.state,'relearning');
 c=F.schedule(c,'good',t+4*60000);assert.equal(c.state,'review');
});
test('shorter steps change only due: stability, difficulty, state and lapses match the py-fsrs step replay',()=>{
 for(const name of ['again_then_good@0.9','many_lapses@0.9','late_reviews@0.9']){
  let a=F.newCard(),b=F.newCard();
  golden[name].forEach(r=>{a=F.schedule(a,r.grade,r.ts);b=F.schedule(b,r.grade,r.ts,{learningSteps:[1,10],relearningSteps:[10]});});
  close(a.stability,b.stability,name+' stability');close(a.difficulty,b.difficulty,name+' difficulty');assert.equal(a.state,b.state);assert.equal(a.lapses,b.lapses);assert.equal(a.misses,b.misses);
 }
});
test('schedule never mutates its input',()=>{
 const c=F.newCard('k'),copy=JSON.stringify(c);F.schedule(c,'good',T0);assert.equal(JSON.stringify(c),copy);
});
test('replay sorts by time, drops undone, flags and duplicate ids',()=>{
 const rows=[{id:'b',word_key:'w',ts:T0+60000,result:'got'},{id:'a',word_key:'w',ts:T0,result:'got'},{id:'a',word_key:'w',ts:T0,result:'got'},
  {id:'u',word_key:'w',ts:T0+120000,result:'missed',undone:true},{kind:'flag',word_key:'w',ts:T0+1},{id:'z',word_key:'w',ts:'bad',result:'got'}];
 const c=F.replay(rows).get('w');
 let expect=F.schedule(F.schedule(F.newCard('w'),'good',T0),'good',T0+60000);
 assert.deepEqual(c,expect);assert.equal(c.reps,2);
});
test('forecast counts overdue in day 0 and ignores new cards',()=>{
 const now=new Date(2026,8,21,12),t=now.getTime();
 const cards=[{reps:1,due:t-5*DAY},{reps:1,due:t+60000},{reps:1,due:t+DAY},{reps:1,due:t+30*DAY},F.newCard()];
 const f=F.forecast(cards,now,7);
 assert.equal(f.length,7);assert.equal(f[0].date,'2026-09-21');assert.equal(f[0].due,2);assert.equal(f[1].due,1);
 assert.equal(f.reduce((s,d)=>s+d.due,0),3);
});
test('invalid review time is refused',()=>assert.throws(()=>F.schedule(F.newCard(),'good','nope')));

// ---- daily queue (docs/js/cards-core.js) ----
globalThis.AneesFSRS=F;require('../docs/js/cards-core.js');const Q=globalThis.AneesCards;
const words=Array.from({length:30},(_,i)=>({key:'w'+i,doc_order:i}));
const catalog={groups:[{key:'w0',keys:['w0','w1','w2']},{key:'w3',keys:['w3','w4']}]};
const noon=new Date(2026,8,21,12).getTime(),iso=t=>new Date(t).toISOString();
const row=(id,k,t,result='got')=>({id,word_key:k,ts:iso(t),result});
const run=(log,now=noon,n=20)=>{const cards=F.replay(log);return Q.queue(words,cards,log,now,{newPerDay:n,siblings:Q.siblingMap(words,catalog)});};
test('new cards respect the daily limit and bury sibling forms',()=>{
 const q=run([]);assert.equal(q.counts.new,20);assert.equal(q.counts.due,0);
 const keys=q.items.map(c=>c.id);assert.ok(keys.includes('w0')&&!keys.includes('w1')&&!keys.includes('w2'));assert.ok(keys.includes('w3')&&!keys.includes('w4'));
 assert.equal(q.buried,3);
});
test('the queue defaults to the 8-a-day new-card cap, the one number in AneesFSRS.DEFAULTS.newPerDay',()=>{
 assert.equal(F.DEFAULTS.newPerDay,8);
 const q=Q.queue(words,F.replay([]),[],noon,{siblings:Q.siblingMap(words,catalog)});assert.equal(q.counts.new,8);assert.equal(q.room,8);
});
test('capNew: every round introduces at most the day\'s room of new cards; seen cards always pass; the rest are held',()=>{
 const log=[row('a1','w10',noon-3600000),row('a2','w11',noon-3600000),row('a3','w12',noon-3600000),row('old','w20',noon-5*86400000)];
 const c=Q.capNew(words,log,noon);   // w0..w29: w10-12 seen today, w20 seen days ago, 26 unseen
 assert.equal(Q.newToday(log,noon),3);assert.equal(c.newToday,3);assert.equal(c.room,5);assert.equal(c.cap,8);
 assert.equal(c.fresh,5);assert.equal(c.held,21);assert.equal(c.cards.length,9);
 assert.deepEqual(c.cards.map(w=>w.key),['w0','w1','w2','w3','w4','w10','w11','w12','w20']);
 const full=Q.capNew(words,Array.from({length:8},(_,i)=>row('n'+i,'w'+(20+i),noon-60000)),noon);
 assert.equal(full.room,0);assert.deepEqual(full.cards.map(w=>w.key),['w20','w21','w22','w23','w24','w25','w26','w27']);assert.equal(full.held,22);
 assert.equal(Q.capNew(words,[],noon,{newPerDay:0}).held,0);   // 0 = cap off
 assert.equal(Q.capNew(words,[{...row('u','w5',noon-60000),undone:true}],noon).newToday,0);   // undone answers never count
});
test('new cards answered today use up the limit',()=>{
 const log=Array.from({length:5},(_,i)=>row('a'+i,'w'+(10+i),noon-3600000));
 const q=run(log);assert.equal(q.newToday,5);assert.equal(q.counts.new,15);
});
test('order is learning first, then due reviews, then new',()=>{
 const day=86400000,log=[row('r1','w20',noon-10*day),row('r2','w20',noon-10*day+60000),row('r3','w20',noon-10*day+700000),row('l1','w21',noon-120000,'missed')];
 const q=run(log);assert.equal(q.items[0].id,'w21');assert.equal(q.items[0].state,'learning');
 assert.equal(q.items[1].id,'w20');assert.equal(q.items[1].state,'review');assert.equal(q.items[2].reps,0);
 assert.equal(q.counts.learning,1);assert.equal(q.counts.due,1);
});
test('a review card is buried when its sibling was answered today',()=>{
 const day=86400000,old=noon-10*day,log=[row('a','w0',old),row('b','w0',old+60000),row('c','w0',old+700000),row('d','w1',noon-3600000)];
 const q=run(log);assert.equal(q.counts.due,0);assert.ok(!q.items.some(c=>c.id==='w0'));
});
test('undone answers are ignored by the queue and the replay',()=>{
 const log=[{...row('x','w5',noon-60000),undone:true}];const q=run(log);
 assert.equal(q.newToday,0);assert.equal(q.counts.learning,0);assert.equal(F.replay(log).size,0);
});
test('word-bank-core drops undone answers, whichever copy arrives last',()=>{
 const WB=require('../docs/js/word-bank-core.js');
 const u=WB.unique([{id:'1',ts:'2026-09-21T10:00:00Z'},{id:'2',ts:'2026-09-21T10:01:00Z'},{id:'2',ts:'2026-09-21T10:01:00Z',undone_at:'2026-09-21T10:02:00Z'}]);
 assert.deepEqual(u.map(e=>e.id),['1']);
});
