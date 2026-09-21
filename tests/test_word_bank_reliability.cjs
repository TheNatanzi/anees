const test=require('node:test'),assert=require('node:assert/strict'),T=require('../docs/js/word-bank-context.js'),C=require('../docs/js/word-bank-core.js'),R=require('../docs/js/word-bank-review.js'),A=require('../docs/js/word-bank-arabizi.js');
const row=(id,speaker,text,start,end)=>({row_id:id,speaker,text,timeline_start:start,timeline_end:end});
test('word-sized source rows become speaker turns without dropping or rewriting speech',()=>{
 const rows=[row('a','Amal','لما',1,1.2),row('b','Amal','ما',1.3,1.4),row('c','Amal','يكون',1.5,2),row('d','Medi','جواب',3,3.3),row('e','Medi','سهل',3.5,4)];const out=T.turns(rows);
 assert.equal(out.length,2);assert.equal(out[0].rows.map(T.text).join(' '),'لما ما يكون');assert.equal(out[1].rows.map(T.text).join(' '),'جواب سهل');assert.deepEqual(rows[0],row('a','Amal','لما',1,1.2));
});
test('speaker changes and real pauses separate turns, duplicated source rows do not duplicate speech',()=>{
 const r=row('a','Medi','hello',1,2);assert.equal(T.turns([r,r,row('b','Medi','next',10,11),row('c','Amal','yes',11,12)]).length,3);
});
test('legacy timestamps cannot apply another lesson’s colors',()=>{
 const e={speaker:'Medi',row_id:'legacy-word-event:1',lesson_date:'2026-08-25',t_start:10};assert(T.owns(e,row('2026-08-25:labeled:1','Medi','سهل',10,11)));assert(!T.owns(e,row('2026-09-04:labeled:1','Medi','سهل',10,11)));assert(!T.owns(e,row('2026-08-25:labeled:1','Amal','سهل',10,11)));
});
test('a linked or explicitly reviewed repeat cannot silently become another correct attempt',()=>{
 const e={id:'a',speaker:'Medi',lesson_date:'2026-09-19',t_start:1,word_key:'x',assessment:'independent',vocab_points:1,scored_in_event:'b'};assert.equal(C.points(e),null);
 const repeat={...e,scored_in_event:null,text:'شو يعني ريحة؟',review_locked:true,ignored:true,assessment:'unresolved',vocab_points:null};assert.equal(C.points(C.prepareEvidence([repeat])[0]),null);
});
test('documented Amal spelling outranks generic transliteration; unknown vowels are not invented',()=>{
 const convert=A.create([{arabic:'اليوم',arabizi:'el-yoam'},{arabic:'جواب',arabizi:'jawaab'}]);assert.equal(convert('اليوم جواب').text,'el-yoam jawaab');assert.equal(convert('كمي').text,'كمي');assert(convert('كمي').approximate);
});
test('status colors mark exact tokens and tutor feedback, never unrelated substrings',()=>{
 const h=R.mark('shu safra sahel mni7 mumtaz',['safra'],['sahel'],['mni7'],['mumtaz']);for(const c of ['wrong','partial','correct','feedback'])assert(h.includes('ab-'+c));assert(!h.includes('>shu</mark>'));
});
test('known pronunciation correction belongs to kmy, not the formal shirt sentence',()=>{
 const r=require('../docs/data/word-bank-review.json');const p=r.additions.find(a=>a.event.id.startsWith('6ee48a5af1')).event;
 assert(p.row_id.endsWith(':1071'));assert(p.t_start>625&&p.t_start<626);assert(!r.transcript_rows['anees-20260919-recall-medi:row:1045']);assert.equal(r.transcript_rows[p.row_id].arabizi,'uh, 8amee2');
});
test('all reviewed vocabulary bindings exist in the source catalog',()=>{
 const keys=new Set(require('../docs/data/words.json').items.map(w=>w.key)),r=require('../docs/data/word-bank-review.json');for(const p of Object.values(r.patches)){if(p.changes.word_key)assert(keys.has(p.changes.word_key),p.changes.word_key);if(p.changes.attempt_target)assert(keys.has(p.changes.attempt_target.word_key));}
});
test('reviewed Arabic and learner-confirmed Arabizi both retain source text',()=>{
 const e={id:'e',source_sha256:'h',context:[{row_id:'r',text:'كمي'}]};const out=R.apply([e],{transcript_rows:{r:{source_sha256:'h',original:'كمي',display:'كمي',arabizi:'8amee2'}}}).events[0];assert.equal(out.context[0].text,'كمي');assert.equal(out.context[0].reviewed_arabizi,'8amee2');
});

