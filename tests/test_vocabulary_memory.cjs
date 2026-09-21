const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../docs/js/word-bank-core.js'),M=require('../docs/js/vocabulary-memory.js');
const attempt=(date,p,id=date,extra={})=>({id,speaker:'Medi',lesson_date:date,lesson_id:date,t_start:10,vocab_points:p,...extra});
const at=(events,now)=>M.assess(C.score(events),new Date(now+'T12:00:00'));
test('approved starting bands use calendar days and exact boundaries',()=>{
 for(const [date,label] of [['2026-09-14','Strong'],['2026-09-15','Fading'],['2026-09-21','Fading'],['2026-09-22','At risk'],['2026-10-05','At risk'],['2026-10-06','High risk']])assert.equal(at([attempt('2026-09-01',1)],date).label,label);
});
test('untested differs from attempted without a successful recall',()=>{
 assert.equal(at([],'2026-09-21').key,'unchecked');
 assert.equal(at([attempt('2026-09-20',0)],'2026-09-21').key,'no-recall');
 assert.equal(at([attempt('2026-09-20',.5)],'2026-09-21').key,'no-recall');
});
test('misses and hints keep last success and cannot look freshly remembered',()=>{
 const first=attempt('2026-09-01',1);
 for(const [p,tier] of [[0,2],[.5,1]]){const m=at([first,attempt('2026-09-03',p)],'2026-09-03');assert.equal(m.age,2);assert.equal(m.last.id,first.id);assert.equal(m.tier,tier);}
 assert.equal(at([first,attempt('2026-10-08',0)],'2026-10-08').key,'high');
});
test('self-correction earns a fresh clock but repetitions, tutor speech and grammar do not',()=>{
 const first=attempt('2026-09-01',1);
 for(const extra of [{immediate_repeat:true},{is_echo:true},{grammar_only:true},{speaker:'Amal'},{needs_review:true},{scored_in_event:'old'}])assert.equal(at([first,attempt('2026-09-21',1,'new',extra)],'2026-09-21').age,20);
 const m=at([first,attempt('2026-09-21',1,'self',{self_corrected:true})],'2026-09-21');assert.equal(m.age,0);assert.equal(m.key,'strong');
});
test('two longer successful gaps support extension, bounded at twice baseline',()=>{
 const es=[attempt('2026-09-01',1),attempt('2026-09-22',1),attempt('2026-10-13',1)];
 assert.equal(at(es.slice(0,2),'2026-09-22').scale,1);
 assert.deepEqual(at(es,'2026-10-13').thresholds,[21,32,53]);
 assert.equal(at(es,'2026-10-30').key,'strong');
 assert.equal(at([attempt('2026-01-01',1),attempt('2026-04-01',1),attempt('2026-07-01',1)],'2026-07-01').scale,2);
});
test('a miss removes an extension immediately; a later full-credit answer restarts at baseline',()=>{
 const es=[attempt('2026-09-01',1),attempt('2026-09-22',1),attempt('2026-10-13',1),attempt('2026-10-14',0)];
 const m=at(es,'2026-10-14');assert.equal(m.key,'risk');assert.equal(m.scale,1);assert.equal(m.age,1);
 es.push(attempt('2026-10-15',1));assert.equal(at(es,'2026-10-15').key,'strong');assert.equal(at(es,'2026-10-15').scale,1);
});
test('same lesson attempts and intervening hints cannot manufacture long-gap evidence',()=>{
 const es=[attempt('2026-09-01',1),attempt('2026-09-22',.5),attempt('2026-09-23',1),attempt('2026-10-14',1)];
 assert.equal(at(es,'2026-10-14').scale,1);
 const same=[attempt('2026-09-01',1),attempt('2026-09-22',1),attempt('2026-09-22',1,'third')];assert.equal(at(same,'2026-09-22').scale,1);
});
test('memory calculation never changes demonstrated grades or flashcard histories',()=>{
 const events=Array.from({length:10},(_,i)=>attempt('2026-09-'+String(i+1).padStart(2,'0'),i===9?0:1,'e'+i));
 const score=C.score(events),before=JSON.stringify(score);assert.equal(score.status,'Mastered');assert.equal(M.assess(score,new Date('2026-09-10T12:00:00')).key,'risk');assert.equal(JSON.stringify(score),before);
 const cards=C.score([{id:'card',result:'got',ts:'2026-09-20'}],'flashcards');assert.equal(M.assess(cards,new Date('2026-09-21T12:00:00')).age,1);assert.equal(M.assess(score,new Date('2026-09-21T12:00:00')).age,12);
});
test('growth and current totals agree, grammar excluded, unknown addition dates remain unknown',()=>{
 const words=[{key:'a',arabizi:'A',english:'A'},{key:'b',arabizi:'B',english:'B'},{key:'min',arabizi:'min',english:'From'}];
 const rows=C.models(words,{},[attempt('2026-09-01',1,'a1',{word_key:'a'}),attempt('2026-09-02',1,'a2',{word_key:'a'}),attempt('2026-09-03',0,'b1',{word_key:'b'}),attempt('2026-09-03',1,'g1',{word_key:'min'})],[]);
 const now=new Date('2026-09-21T12:00:00'),m=M.summary(rows,now),g=M.growth(rows,now);
 assert.equal(m.total,2);assert.equal(m.known,1);assert.equal(m.mastered,1);assert.equal(m.newCount,null);assert.equal(g.at(-1).known,m.known);assert.equal(g.at(-1).mastered,m.mastered);assert.equal(g[0].date,'2026-09-01');
 assert.equal(Object.values(m.memoryCounts).reduce((a,b)=>a+b,0),m.total);
});
test('original-date corrections replay history; reviewed duplicates do not create extra recall',()=>{
 const words=[{key:'a',arabizi:'A',english:'A'}],es=[attempt('2026-09-01',0,'one',{word_key:'a'}),attempt('2026-09-01',1,'one',{word_key:'a'})];
 const rows=C.models(words,{},es,[]),now=new Date('2026-09-21T12:00:00');assert.equal(rows[0].entries[0].speaking.count,1);assert.equal(M.growth(rows,now)[0].known,1);assert.equal(M.summary(rows,now).all[0].memory.age,20);
});
test('invalid and future dates cannot create a memory clock',()=>{
 assert.equal(M.day('2026-02-30'),null);assert.equal(M.day(''),null);
 assert.equal(at([attempt('2026-09-22',1)],'2026-09-21').key,'unchecked');
});
