// AM-16: Medi's promised list on the Word Bank (docs/js/promised-words.js) - Waiting / In the Doc since / Medi marked old.
const test = require('node:test'), assert = require('node:assert/strict');
require('../docs/js/promised-words.js');
const A = globalThis.AneesPromised;
test('AM-16 promised list labels: waiting old, in the Doc since, Medi marked old waiting for Amal', () => {
  assert.equal(A.label({ state: 'waiting', age: 'old' }), 'Waiting · old');
  assert.equal(A.label({ state: 'in_doc', in_doc_since: '2026-10-05', age: 'old' }), 'In the Doc since Oct 5 · old');
  assert.equal(A.label({ state: 'awaiting_amal', marks: { medi: 'old' } }), 'The student marked old · waiting for the tutor');
  const h = A.html({ promised: [{ id: 'x', arabic: 'ممتاز', english: 'excellent', date: '2026-10-01', state: 'waiting', age: 'old' }] });
  assert.match(h, /The tutor said she will add \(1\)/); assert.match(h, /ممتاز/); assert.equal(A.html({ promised: [] }), '');
});
