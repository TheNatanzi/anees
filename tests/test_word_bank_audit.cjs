const test=require('node:test'),assert=require('node:assert/strict'),C=require('../docs/js/word-bank-core.js');
test('lesson calendar date does not become yesterday before local midnight',()=>{
 const evening=new Date(2026,8,17,23,59);assert.equal(C.daysAgo({lesson_date:'2026-09-17'},evening),0);
 assert.equal(C.daysAgo({lesson_date:'2026-09-16'},evening),1);
});
test('unknown inflection does not inherit present merely from the canonical key',()=>{
 const words=[{key:'break',arabizi:'bakser'}],catalog={groups:[{id:'break',key:'break',keys:['break'],name:'bakser',type:'Verb',entries:[{id:'past',label:'Past',keys:[]},{id:'present',label:'Present',word:'bakser',arabic:'بكسر',keys:['break']}]}]};
 const e={id:'a',word_key:'break',speaker:'Medi',lesson_date:'2026-09-17',t_start:1,text:'كسرت',assessment:'independent'};
 let r=C.models(words,catalog,[e],[])[0];assert.equal(r.spoke,0);assert.equal(r.unassigned.length,1);
 r=C.models(words,catalog,[{...e,tense:'past'}],[])[0];assert.equal(r.entries[0].speaking.status,'Good');assert.equal(r.entries[1].speaking.status,'Untested');
});
test('talk and scratch source paradigms have distinct identities',()=>{
 const c=require('../docs/data/word-bank-catalog.json'),talk=c.groups.find(g=>g.key==='ana ba7ki'),scratch=c.groups.find(g=>g.key==='ana ba7uk');
 assert(talk&&scratch);assert.equal(talk.keys.some(k=>scratch.keys.includes(k)),false);
 assert(scratch.entries[0].keys.includes('ana 7akait~scratch'));
});
test('one self-correction earns half credit on the intended word and preserves actual speech',()=>{
 const words=[{key:'annoy',arabizi:'baza3ej'},{key:'annoyed',arabizi:'banze3ej'}];
 const start={id:'wrong',word_key:'annoy',speaker:'Medi',lesson_date:'2026-09-05',t_start:1,text:'baza3ej',spoken:true,assessment:'unresolved',ignored:true,scored_in_event:'correct'};
 const end={id:'correct',word_key:'annoyed',speaker:'Medi',lesson_date:'2026-09-05',t_start:2,text:'banze3ej',spoken:true,assessment:'helped',vocab_points:.5};
 const rows=C.models(words,{},[start,end],[]),wrong=rows.find(r=>r.id==='annoy'),right=rows.find(r=>r.id==='annoyed');
 assert.equal(wrong.spoke,0);assert.equal(wrong.last.id,'wrong');
 assert.equal(right.spoke,1);assert.equal(right.entries[0].speaking.status,'Shaky');
 assert.equal(right.entries[0].speaking.attempts[0].p,.5);
});
test('wrong word scores intended retrieval once while recency belongs to actual speech',()=>{
 const words=[{key:'annoying',arabizi:'muz3ej'},{key:'annoyed',arabizi:'maz3uuj'}];
 const event={id:'a',word_key:'annoying',attempt_target:{word_key:'annoyed'},speaker:'Medi',spoken:true,lesson_date:'2026-09-10',t_start:5,text:'muz3ej',assessment:'incorrect',vocab_points:0};
 const rows=C.models(words,{},[event],[]),actual=rows.find(r=>r.id==='annoying'),intended=rows.find(r=>r.id==='annoyed');
 assert.equal(actual.spoke,0);assert.equal(actual.last.id,'a');assert.equal(actual.used,1);
 assert.equal(C.points(actual.events[0]),null);assert.equal(actual.events[0].observation_only,true);
 assert.equal(intended.spoke,1);assert.equal(intended.entries[0].speaking.status,'Shaky');
 assert.equal(intended.last,null);assert.equal(intended.used,0);
 assert.equal(rows.flatMap(r=>r.entries.flatMap(f=>f.speaking.attempts)).length,1);
 assert.equal(event.observation_only,undefined); // Evidence remains immutable.
});
test('forgotten target alone does not count as an actual lesson occurrence',()=>{
 const r=C.models([{key:'storm',arabizi:'3aasfe'}],{},[{id:'a',word_key:'storm',speaker:'Medi',spoken:false,lesson_date:'2026-09-10',t_start:1,text:'I forgot',assessment:'recall_failure'}],[])[0];
 assert.equal(r.spoke,1);assert.equal(r.used,0);assert.equal(r.last,null);
});
test('tutor exposure stays with actual wording despite an intended-target overlay',()=>{
 const words=[{key:'a',arabizi:'a'},{key:'b',arabizi:'b'}];
 const rows=C.models(words,{},[{id:'heard',word_key:'a',attempt_target:{word_key:'b'},speaker:'Amal',spoken:false,lesson_date:'2026-09-10',t_start:2,row_id:'sentence',assessment:'unresolved'}],[]);
 assert.equal(rows.find(r=>r.id==='a').heard,1);assert.equal(rows.find(r=>r.id==='b').heard,0);
 assert.equal(rows.reduce((n,r)=>n+r.spoke,0),0);
});
