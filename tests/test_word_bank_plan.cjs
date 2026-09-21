const test=require('node:test'),assert=require('node:assert/strict'),C=require('../docs/js/word-bank-core.js');
test('spoken mastery counts distinct lessons while cards require distinct review days',()=>{
 const events=[0,1].map(i=>({id:String(i),speaker:'Medi',lesson_date:'2026-09-18',lesson_id:'lesson-'+i,t_start:i,vocab_points:1}));
 assert.equal(C.score(events).status,'Mastered');assert.equal(C.score(events,'flashcards').status,'Good');
 const ten=Array.from({length:10},(_,i)=>({...events[i%2],id:String(i),t_start:i}));
 assert.equal(C.score(ten).status,'Mastered');assert.equal(C.score(ten,'flashcards').status,'Good');
});
test('documented alternate spellings are searchable without adding score entries',()=>{
 const words=[{key:'k',arabizi:'Primary',arabic:'كلمة',english:'Meaning',aliases:['Alternative','بديل']}];
 const [row]=C.models(words,{groups:[]},[],[]);
 for(const q of ['Alternative','بديل','Meaning'])assert.equal(C.filter([row],{q}).rows.length,1);
 assert.equal(row.entries.length,1);assert.equal(row.spoke,0);
});
test('plural Arabic is secondary while original source and independent scores are preserved',()=>{
 const word={key:'trip',arabizi:'Safra',arabic:'سفرة',english:'Trip',plural:'safraat (سفرات)'};const saved=JSON.stringify(word);
 const [r]=C.models([word],{groups:[]},[{id:'e',word_key:'trip',form:'plural',speaker:'Medi',text:'سفرات',lesson_date:'2026-09-17',t_start:1,vocab_points:1}],[]);
 assert.equal(r.entries[1].word,'safraat');assert.equal(r.entries[1].arabic,'سفرات');
 assert.equal(r.entries[0].speaking.status,'Untested');assert.equal(r.entries[1].speaking.status,'Good');assert.equal(JSON.stringify(word),saved);
});
test('usage and last-said remain distinct when only Amal has used a form',()=>{
 const [r]=C.models([{key:'k',arabizi:'Test',english:'Test'}],{groups:[]},[{id:'a',word_key:'k',speaker:'Amal',text:'Test',lesson_date:'2026-09-17',t_start:1,row_id:'r'}],[]);
 assert.equal(r.last,null);assert.equal(r.used,1);assert.equal(r.heard,1);assert.equal(r.spoke,0);assert.equal(C.filter([r],{usage:'none'}).rows.length,0);
});
