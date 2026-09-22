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
   c=F.schedule(c,r.grade,r.ts,{desiredRetention:ret});
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
test('lapses count only Again on a review card; leech at 8',()=>{
 let c=F.newCard();c=F.schedule(c,'again',T0);c=F.schedule(c,'again',T0+60000);assert.equal(c.lapses,0);
 const rows=golden['many_lapses@0.9'];c=F.newCard();
 rows.forEach((r,i)=>{c=F.schedule(c,r.grade,r.ts);if(i===2+2*7)assert.equal(F.isLeech(c),false);});
 assert.equal(c.lapses,9);assert.equal(F.isLeech(c),true);
 assert.equal(F.isLeech({lapses:8}),true);assert.equal(F.isLeech({lapses:7}),false);
});
test('Again re-shows in 10 minutes on a review card, 1 minute when new',()=>{
 let c=F.schedule(F.newCard(),'again',T0);assert.equal(c.due-T0,60000);
 c=F.schedule(F.schedule(F.schedule(F.newCard(),'good',T0),'good',T0+60000),'good',T0+11*60000);
 assert.equal(c.state,'review');const t=c.due;c=F.schedule(c,'again',t);assert.equal(c.due-t,600000);assert.equal(c.state,'relearning');
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
