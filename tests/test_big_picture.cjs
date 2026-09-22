const test=require('node:test'),assert=require('node:assert/strict');
const B=require('../docs/js/big-picture.js');
test('split: one idea per line, bullets and numbers stripped, blanks and repeats dropped',()=>{
 assert.deepEqual(B.split('- Words into context\n\n• Sentences\n2. Audio lessons\n[ ] audio lessons\n  spaced   out  ').map(i=>i.title),['Words into context','Sentences','Audio lessons','spaced out']);
 assert.deepEqual(B.split('   \n'),[]);
});
test('split: a very long line keeps the full text as the note',()=>{
 const long='x'.repeat(350),[i]=B.split(long);
 assert.equal(i.title.length,298);assert.equal(i.note,long);
});
test('group: every status present, newest first, unknown status falls back to ideas',()=>{
 const g=B.group([{id:1,status:'idea',created_at:'2026-09-01'},{id:2,status:'idea',created_at:'2026-09-22'},{id:3,status:'done',created_at:'2026-09-02'},{id:4,status:'weird',created_at:'2026-09-03'}]);
 assert.deepEqual(g.map(s=>s.id),['idea','picked','building','done','dropped']);
 assert.deepEqual(g[0].ideas.map(i=>i.id),[2,4,1]);assert.equal(g[3].ideas.length,1);assert.equal(g[1].ideas.length,0);
});
