const test=require('node:test'),assert=require('node:assert/strict'),C=require('../docs/js/word-bank-core.js'),R=require('../docs/js/word-bank-review.js');
const base={id:'a',speaker:'Medi',lesson_date:'2026-09-19',t_start:1,t_end:2,spoken:true,row_id:'r',assessment:'helped',source_sha256:'source'};
test('meaning request scores ree7a and excludes question wrapper',()=>{
 const context=[{row_id:'r',speaker:'Medi',text:'شو يعني ريحة؟'}];
 const es=C.prepareEvidence([{...base,word_key:'rI7a',text:'ريحة',context},{...base,id:'b',word_key:'shu',text:'شو',context}]);
 assert.equal(C.points(es[0]),0);assert.equal(C.points(es[1]),null);
});
test('clarification is neither partial credit nor wrong',()=>{assert.equal(C.points(C.prepareEvidence([{...base,word_key:'shu',text:'uh, shu?'}])[0]),null)});
test('self correction gets one full credit with its note',()=>{const e=C.prepareEvidence([{...base,word_key:'b',text:'b',self_corrected:true}])[0];assert.equal(C.points(e),1);assert(e.self_corrected)});
test('linked confusion scores both actual and intended words without fabricated utterance',()=>{
 const rows=C.models([{key:'safra',arabizi:'safra'},{key:'safar',arabizi:'safar'}],{},[{...base,word_key:'safra',text:'safra',assessment:'incorrect',vocab_points:0,confusion_pair:true,attempt_target:{word_key:'safar'}}],[]);
 assert.deepEqual(rows.map(r=>r.entries[0].speaking.attempts[0].p),[0,0]);assert.equal(rows.find(r=>r.id==='safar').last,null);
});
test('review refuses changed evidence and preserves originals',()=>{
 const e={...base,text:'safra',word_key:'safra'},review={patches:{a:{expected:{source_sha256:'other'},changes:{vocab_points:0}}}};
 assert.deepEqual(R.apply([e],review).stale,['a']);assert.equal(e.vocab_points,undefined);
});
test('red markers escape HTML and never mark substrings inside unrelated words',()=>{
 assert.equal(R.mark('shu safra today',['safra']),'shu <mark class="ab-wrong" title="Incorrect word or pronunciation">safra</mark> today');
 assert.equal(R.mark('<img onerror=x>',['shu']),'&lt;img onerror=x&gt;');assert.equal(R.mark('ashu',['shu']),'ashu');
});
test('all reviewed targets exist and additions retain source timing',()=>{
 const review=require('../docs/data/word-bank-review.json'),words=new Set(require('../docs/data/words.json').items.map(w=>w.key));
 for(const p of Object.values(review.patches))if(p.changes.attempt_target)assert(words.has(p.changes.attempt_target.word_key));
 for(const {event:e,expected_source:s} of review.additions){assert(words.has(e.word_key));assert.equal(e.source_sha256,s);assert(e.t_end>e.t_start);assert(e.local_start>=0);}
});
