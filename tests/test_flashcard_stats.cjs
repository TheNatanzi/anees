const test=require('node:test'),assert=require('node:assert/strict');
const F=require('../docs/js/fsrs.js'),S=require('../docs/js/flashcard-stats.js');
// Local-time fixtures so the tests hold in any time zone. 2026-09-23 is a Wednesday.
const at=(m,d,h=10,min=0)=>new Date(2026,m-1,d,h,min).toISOString();
const NOW=new Date(2026,8,23,18,0);
let seq=0;const ans=(key,ts,result='got',extra={})=>({id:'r'+(++seq),word_key:key,ts,result,...extra});
const O={desiredRetention:0.9};

test('clean: drops undone, flags, duplicates and bad rows; sorts by time',()=>{
 const rows=[ans('a',at(9,2)),ans('b',at(9,1)),{...ans('c',at(9,3)),undone_at:at(9,3)},{kind:'flag',id:'f',word_key:'a',ts:at(9,4),result:'got'},ans('d','nope'),ans('e',at(9,5),'maybe')];
 rows.push({...rows[0]});
 assert.deepEqual(S.clean(rows).map(r=>r.word_key),['b','a']);
});
test('history: phase before each answer, same final cards as AneesFSRS.replay',()=>{
 const log=[ans('a',at(9,1)),ans('a',at(9,1,10,15)),ans('a',at(9,5)),ans('b',at(9,5),'missed')];
 const h=S.history(log,O),r=F.replay(log,O);
 assert.deepEqual(h.answers.map(a=>a.kind),['new','learning','review','new']);
 assert.equal(h.answers[0].interval,null);assert.equal(h.answers[2].interval,h.states.get('a')[1].interval);assert.ok(h.answers[2].interval>=1);
 assert.deepEqual(h.cards.get('a'),r.get('a'));assert.deepEqual(h.cards.get('b'),r.get('b'));
});
test('goals: distinct cards this Mon–Sun week and this month',()=>{
 const log=[ans('a',at(9,21)),ans('a',at(9,22)),ans('b',at(9,23)),ans('c',at(9,20)),ans('d',at(8,31))];
 const g=S.goals(S.history(log,O),NOW,{weekly:50,monthly:200});
 assert.deepEqual(g.week,{n:2,goal:50,pct:4});assert.equal(g.month.n,3);assert.equal(g.month.goal,200);
});
test('workload: due by end of today, passes = ceil(needed × retention)',()=>{
 const cards=new Map([['a',{reps:1,due:+NOW-1000}],['b',{reps:3,due:+new Date(2026,8,23,23,59)}],['c',{reps:2,due:+new Date(2026,8,24,1)}],['d',{reps:0,due:null}]]);
 assert.deepEqual(S.workload(cards,NOW,0.9),{needed:2,passes:2});
 assert.equal(S.workload(cards,NOW,0.8).passes,2);
});
test('true retention: only answers on cards mature at answer time; null when none',()=>{
 assert.equal(S.trueRetention(S.history([ans('a',at(9,1))],O)).pct,null);
 const h={answers:[{phase:'mature',right:true},{phase:'mature',right:false},{phase:'learning',right:false},{phase:'mature',right:true},{phase:'mature',right:true}]};
 assert.deepEqual(S.trueRetention(h),{n:4,right:3,pct:75});
});
test('leeches: 8+ lapses',()=>{
 assert.equal(S.leeches(new Map([['a',{lapses:8}],['b',{lapses:7}]])).length,1);
});
test('curve: from first answer to today + 30, 100% on the review day, then decays; bump markers',()=>{
 const h=S.history([ans('a',at(9,20)),ans('a',at(9,20,10,2)),ans('b',at(9,22),'missed')],O),c=S.curve(h,NOW,30);
 assert.equal(c[0].date,'2026-09-20');assert.equal(c.at(-1).date,'2026-10-23');assert.equal(c.length,34);
 assert.equal(c[0].r,100);assert.equal(c[0].bump,true);assert.equal(c[2].bump,false);
 assert.ok(c.at(-1).r<c[3].r);assert.equal(c.at(-1).future,true);assert.equal(c[3].cards,2);
 assert.deepEqual(S.curve(S.history([],O),NOW),[]);
});
test('segmentation: new = never answered words; pass rates on first answers and learning answers',()=>{
 const log=[ans('a',at(9,1)),ans('a',at(9,1,10,5),'missed'),ans('b',at(9,2),'missed'),ans('a',at(9,2))];
 const s=S.segmentation(S.history(log,O),['a','b','c','d']);
 assert.equal(s.new.count,2);assert.equal(s.new.pass,50);
 assert.equal(s.learning.answers,2);assert.equal(s.learning.pass,50);
 assert.equal(s.learning.count+s.mature.count,2);
});
test('today: answers, minutes from answer_ms, split by the state before the answer',()=>{
 const log=[ans('a',at(9,23,9),'got',{answer_ms:4000}),ans('a',at(9,23,9,1),'got',{answer_ms:6000}),ans('b',at(9,23,9,2),'missed',{answer_ms:null}),ans('c',at(9,22))];
 const t=S.today(S.history(log,O),NOW);
 assert.equal(t.n,3);assert.equal(t.cards,2);assert.equal(t.pct,66.7);assert.equal(t.ms,10000);assert.equal(t.timed,2);
 assert.deepEqual(t.split,{new:2,learning:1,review:0});
 assert.equal(S.today(S.history([],O),NOW).pct,null);
});
test('heatmap: 365 squares, current and longest streaks',()=>{
 const log=[at(9,1),at(9,2),at(9,3),at(9,4),at(9,21),at(9,22),at(9,22,11)].map(t=>ans('a',t));
 const m=S.heatmap(S.history(log,O),NOW);
 assert.equal(m.days.length,365);assert.equal(m.days.at(-1).date,'2026-09-23');
 assert.equal(m.current,2);assert.equal(m.longest,4);assert.equal(m.max,2);assert.equal(m.active,6);
 assert.equal(S.heatmap(S.history([],O),NOW).current,0);
});
test('retention table: review answers only, young vs mature, "—" (null) for empty cells',()=>{
 const h={answers:[{kind:'review',interval:5,right:true,t:+new Date(2026,8,23,9)},{kind:'review',interval:30,right:false,t:+new Date(2026,8,22,9)},{kind:'review',interval:3,right:false,t:+new Date(2026,8,10,9)},{kind:'learning',interval:0,right:false,t:+new Date(2026,8,23,9)}]};
 const t=S.retentionTable(h,NOW),cell=(row,p)=>t.rows.find(r=>r.id===row).cells.find(c=>c.period===p);
 assert.deepEqual(cell('young','today'),{period:'today',n:1,right:1,pct:100});
 assert.equal(cell('mature','today').pct,null);assert.equal(cell('mature','yesterday').pct,0);
 assert.deepEqual([cell('total','week').n,cell('total','month').n,cell('total','year').n],[2,3,3]);
});
test('future due: per day, overdue kept apart',()=>{
 const cards=new Map([['a',{reps:1,due:+new Date(2026,8,20)}],['b',{reps:1,due:+new Date(2026,8,23,20)}],['c',{reps:1,due:+new Date(2026,8,25,8)}],['d',{reps:1,due:+new Date(2026,11,25)}],['e',{reps:0}]]);
 const f=S.futureDue(cards,NOW,30);
 assert.equal(f.overdue,1);assert.equal(f.days.length,30);assert.equal(f.days[0].due,1);assert.equal(f.days[2].due,1);assert.equal(f.total,2);
});
test('histograms: stability, difficulty and retrievability buckets with averages; null before any review',()=>{
 assert.equal(S.histograms(new Map(),NOW),null);
 const h=S.history([ans('a',at(9,23,9)),ans('b',at(9,23,9),'missed')],O),x=S.histograms(h.cards,NOW);
 assert.equal(x.n,2);assert.equal(x.stability.bins.reduce((s,b)=>s+b.n,0),2);assert.equal(x.difficulty.bins.length,10);
 assert.equal(x.retrievability.avg,100);assert.equal(x.retrievability.bins[9].n,2);
});
test('timing: average, median, slowest cards; null without timed answers',()=>{
 assert.equal(S.timing(S.history([ans('a',at(9,1))],O)),null);
 const log=[ans('a',at(9,1),'got',{answer_ms:2000}),ans('b',at(9,1,11),'got',{answer_ms:9000}),ans('a',at(9,2),'got',{answer_ms:4000}),ans('c',at(9,2,11),'got',{answer_ms:0})];
 const t=S.timing(S.history(log,O));
 assert.equal(t.n,3);assert.equal(t.avg,5000);assert.equal(t.median,4000);assert.deepEqual(t.slowest.map(s=>s.key),['b','a']);assert.equal(t.slowest[1].avg,3000);
});
test('hourly: 24 local hours, faded under 100 answers',()=>{
 const x=S.hourly(S.history([ans('a',at(9,1,9)),ans('b',at(9,1,9,30),'missed'),ans('c',at(9,1,21))],O));
 assert.equal(x.hours.length,24);assert.deepEqual([x.hours[9].n,x.hours[9].pct],[2,50]);assert.equal(x.hours[21].pct,100);assert.equal(x.hours[0].pct,null);assert.equal(x.faded,true);
});
