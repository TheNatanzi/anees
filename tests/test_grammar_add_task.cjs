'use strict';
/* AM-31 'Add grammar': the card logic of docs/js/hub/grammar-add-task.js, no browser (same rules as scripts/tutor_grammar.py). */
const test = require('node:test'), assert = require('node:assert');
const G = require('../docs/js/hub/grammar-add-task.js');

const V1 = { v: 1, grammar: true, id: 'A18', family: 'A', name: 'hal + noun', one_line: 'x', examples: [{ arabizi: 'hal bait', english: 'this house', hers: true }] };
const V2 = Object.assign({}, V1, { v: 2, name: 'hal + el-noun' });
const sub = (sid, t, id) => ({ id, created_at: t, source: 'tutor_grammar', kind: 'grammar_submit', word_key: 'tgram:' + sid, payload: { text: 'hal is short for hada', example: 'hal bait' } });
const ans = (sid, kind, v, t, id, what) => ({ id, created_at: t, source: 'tutor_grammar', kind, word_key: 'tgram:' + sid + ':answer', payload: { v, what } });

test('AM-31 a new submission waits for Claude, then is a card to approve (counted on the tab)', () => {
  const rows = [sub('sub1', '2026-10-12T10:00:00Z', 1)];
  assert.equal(G.items(rows, { items: [] })[0].state, 'waiting');
  const L = G.items(rows, { items: [{ sid: 'sub1', versions: [V1] }] });
  assert.equal(L[0].state, 'proposed');
  assert.deepEqual(G.count(L), { toApprove: 1, waiting: 0, total: 1 });
});

test('AM-31 Change it waits for the rewrite; the new version is unanswered; yes counts only on the version it names', () => {
  const rows = [sub('sub1', '2026-10-12T10:00:00Z', 1), ans('sub1', 'grammar_change', 1, '2026-10-12T10:05:00Z', 2, 'add el-')];
  assert.equal(G.items(rows, { items: [{ sid: 'sub1', versions: [V1] }] })[0].state, 'waiting');
  assert.equal(G.items(rows, { items: [{ sid: 'sub1', versions: [V1, V2] }] })[0].state, 'proposed');
  rows.push(ans('sub1', 'grammar_yes', 2, '2026-10-12T10:20:00Z', 3));
  assert.equal(G.items(rows, { items: [{ sid: 'sub1', versions: [V1, V2] }] })[0].state, 'added');
});

test('AM-31 Undo: the latest action wins (yes -> undo -> card again; withdraw -> undo by sending again)', () => {
  const rows = [sub('sub1', '2026-10-12T10:00:00Z', 1), ans('sub1', 'grammar_yes', 1, '2026-10-12T10:05:00Z', 2), ans('sub1', 'undo', null, '2026-10-12T10:06:00Z', 3)];
  const D = { items: [{ sid: 'sub1', versions: [V1] }] };
  assert.equal(G.items(rows, D)[0].state, 'proposed');
  rows.push(ans('sub1', 'grammar_no', 1, '2026-10-12T10:07:00Z', 4));
  assert.equal(G.items(rows, D)[0].state, 'not_rule');
  const w = [sub('sub2', '2026-10-12T11:00:00Z', 5), { id: 6, created_at: '2026-10-12T11:01:00Z', source: 'tutor_grammar', kind: 'undo', word_key: 'tgram:sub2', payload: {} }];
  assert.equal(G.items(w, { items: [] })[0].state, 'withdrawn');
  w.push(sub('sub2', '2026-10-12T11:02:00Z', 7));
  assert.equal(G.items(w, { items: [] })[0].state, 'waiting');
});

test('AM-31 the rows each tap writes: submit on tgram:<sid>, answers and their undo on tgram:<sid>:answer, withdraw on tgram:<sid>', () => {
  const s = G.row(G.SUBMIT, 'abc123', 'tok', { text: 't' }), y = G.row(G.YES, 'abc123', 'tok', { v: 2, id: 'A18' });
  const u = G.row(G.UNDO, 'abc123', 'tok', { undoes: G.YES }), w = G.row(G.UNDO, 'abc123', 'tok', { undoes: G.SUBMIT });
  assert.deepEqual([s.source, s.word_key, s.lesson_date, s.token], ['tutor_grammar', 'tgram:abc123', null, 'tok']);
  assert.deepEqual([y.word_key, y.payload.v, u.word_key, w.word_key], ['tgram:abc123:answer', 2, 'tgram:abc123:answer', 'tgram:abc123']);
  assert.ok(s.payload.lid && s.payload.lid !== y.payload.lid);
});

test('AM-31 a row this browser wrote shows at once and once only (dropped when the server has it)', () => {
  const local = [Object.assign(G.row(G.SUBMIT, 'zz9999', 't', { text: 'x' }), { created_at: '2026-10-12T12:00:00Z' })];
  assert.equal(G.merge([], [], local).length, 1);
  const live = [Object.assign({ id: 9 }, local[0])];
  assert.equal(G.merge([Object.assign({}, live[0])], live, local).length, 1);
});
