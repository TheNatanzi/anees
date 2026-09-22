const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../docs/js/word-bank-core.js'),S=require('../docs/js/vocabulary-stats.js');
const attempt=(date,p,id=date+':'+p+':'+Math.random(),extra={})=>({id,speaker:'Medi',lesson_date:date,lesson_id:date,t_start:10,t_end:30,vocab_points:p,...extra});
const form=(id,events)=>({id,label:'Word',word:id,keys:[id],speaking:C.score(events),events});
const row=(id,forms,extra={})=>({id,key:id,keys:[id],name:id,topic:'Topic A',grammar_only:false,added:null,entries:forms,...extra});
const NOW=new Date('2026-09-21T12:00:00');
function fixture(){
 // Form A: known after 08-25 (two correct), tested again 09-10 (correct) and 09-19 (wrong).
 const a=form('a',[attempt('2026-08-25',1),attempt('2026-08-25',1,'a2',{t_start:40}),attempt('2026-09-10',1),attempt('2026-09-19',0)]);
 // Form B: first seen 09-10 with a hint, then correct 09-19.
 const b=form('b',[attempt('2026-09-10',.5),attempt('2026-09-19',1)]);
 // Form C: never tested.
 const c=form('c',[]);
 // Grammar row is excluded everywhere.
 const g=form('fi',[attempt('2026-09-19',0)]);
 const rows=[row('a',[a]),row('b',[b],{topic:'Topic B'}),row('c',[c]),row('fi',[g],{grammar_only:true,topic:'Grammar'})];
 const events=[...a.events,...b.events,...g.events,{id:'amal1',speaker:'Amal',lesson_date:'2026-09-10',t_start:100,t_end:3600}];
 return {rows,events};
}
test('lessons: one per recorded date, length = last timestamp',()=>{
 const {events}=fixture(),L=S.lessons(events);
 assert.deepEqual(L.map(l=>l.date),['2026-08-25','2026-09-10','2026-09-19']);
 assert.equal(L[1].seconds,3600);assert.equal(L[0].seconds,30);
});
test('range: week, month and all time windows with a previous window',()=>{
 const w=S.range(NOW,'week');assert.equal(w.end-w.start,6);assert.equal(w.prevEnd,w.start-1);assert.equal(w.prevStart,w.start-7);
 assert.equal(S.range(NOW,'all').start,-Infinity);
});
test('top cards: lesson counts, hours and known trend',()=>{
 const {rows,events}=fixture();
 const all=S.topCards(rows,events,NOW,'all');
 assert.equal(all.lessons.count,3);assert.equal(all.lessons.loaded,3);assert.equal(all.lessons.latest,'2026-09-19');
 assert.equal(all.hours.total,1);// 30s + 3600s + 30s ≈ 1.0 h
 assert.equal(all.known.count,1);assert.equal(all.known.total,3);// a is Good, b is Shaky, c untested; grammar excluded
 const week=S.topCards(rows,events,NOW,'week');
 assert.equal(week.lessons.count,1);assert.equal(week.lessons.previous,1);
 assert.equal(week.known.week,0);// a was already known a week ago
});
test('vocab cards: studied, mastered, words per lesson and correct vs slips (hints are slips)',()=>{
 const {rows,events}=fixture();
 const v=S.vocabCards(rows,events,NOW,'all',4);
 assert.equal(v.studied.count,3);assert.equal(v.studied.documentRows,4);assert.equal(v.studied.added,null);
 assert.equal(v.mastered.count,0);assert.equal(v.mastered.status.Untested,1);
 assert.equal(v.perLesson.lessons,3);assert.equal(v.perLesson.avg,1.7);// (1+2+2)/3assert.deepEqual(v.perLesson.peak,{count:2,date:'2026-09-10'});
 assert.deepEqual([v.ratio.correct,v.ratio.hinted,v.ratio.wrong,v.ratio.total],[4,1,1,6]);
 assert.equal(v.ratio.rate,66.7);
});
test('funnel: four bands always sum to the studied forms',()=>{
 const {rows,events}=fixture();
 const f=S.funnel(rows,events,NOW,'all');
 assert.equal(f.length,3);
 for(const p of f)assert.equal(p.mastered+p.good+p.weak+p.unchecked,3);
 assert.deepEqual(f[0],{date:'2026-08-25',mastered:0,good:1,weak:0,unchecked:2});
});
test('per lesson: retention counts only forms known before that lesson',()=>{
 const {rows,events}=fixture();
 const p=S.perLesson(rows,events,NOW,'all');
 const by=Object.fromEntries(p.series.map(l=>[l.date,l]));
 assert.equal(by['2026-08-25'].retention,null);// first appearance never counts
 assert.equal(by['2026-09-10'].tested,1);assert.equal(by['2026-09-10'].retention,100);
 assert.equal(by['2026-09-19'].tested,1);assert.equal(by['2026-09-19'].retention,0);
 assert.equal(by['2026-09-19'].unique,2);assert.equal(p.peak.count,2);
 assert.equal(p.baseline,100);assert.equal(p.avgRate,66.7);// lessons scored 100, 50, 50
});
test('sections: grouped by Amal\'s headings, grammar excluded',()=>{
 const {rows}=fixture();
 const s=S.sections(rows);
 assert.deepEqual(s,[{name:'Topic A',total:2,known:1},{name:'Topic B',total:1,known:0}]);
});
test('new words: null without document dates, weekly buckets with them',()=>{
 const {rows,events}=fixture();
 assert.equal(S.newWords(rows,NOW,'all'),null);
 rows[0].added='2026-09-14';rows[1].added='2026-09-16';rows[2].added='2026-09-08';
 const n=S.newWords(rows,NOW,'all');
 assert.deepEqual(n.series.map(x=>[x.week,x.added,x.cumulative]),[['2026-09-07',1,1],['2026-09-14',2,3]]);
 assert.equal(n.total,3);assert.equal(n.peak.week,'2026-09-14');assert.equal(n.stillKnownPct,33.3);
 assert.equal(S.newWords(rows,NOW,'week').total,1);
});
