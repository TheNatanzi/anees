// Keep going after a round (Medi 2026-09-30): 67 cards in rounds of 20 -> 20, 20, then ask "13 + 14" or "all 27".
const test=require('node:test'),assert=require('node:assert/strict');
globalThis.AneesFSRS=require('../docs/js/fsrs.js');require('../docs/js/cards-core.js');const Q=globalThis.AneesCards;

test('67 cards in 20s: next, next, then ask 13 + 14 or all 27',()=>{
 assert.deepEqual(Q.nextChunk(47,20),{kind:'next',n:20,left:47});
 assert.deepEqual(Q.nextChunk(27,20),{kind:'ask',all:27,a:13,b:14});
 assert.deepEqual(Q.nextChunk(14,20),{kind:'last',n:14});      // after the 13 half, the 14 come next
});
test('edges: exactly two batches is a plain next; one batch or less is the last round; none left or All = nothing',()=>{
 assert.equal(Q.nextChunk(40,20).kind,'next');
 assert.deepEqual(Q.nextChunk(20,20),{kind:'last',n:20});
 assert.deepEqual(Q.nextChunk(21,20),{kind:'ask',all:21,a:10,b:11});
 assert.equal(Q.nextChunk(0,20).kind,'none');
 assert.equal(Q.nextChunk(30,0).kind,'none');
});
