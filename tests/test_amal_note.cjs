'use strict';
/* AM-27: the note widget's rows (docs/js/amal-note.js), no browser. */
const test = require('node:test'), assert = require('node:assert');
const N = require('../docs/js/amal-note.js');

test('AM-27 a note row carries the list, the card and the note under its own source; an empty note is an undo', () => {
  const b = N.body('tok', 'check-slip-check-2-1', '2026-09-05:112', '  he said it right  ', 'Student 07:34 ...');
  assert.deepEqual([b.token, b.source, b.kind, b.word_key], ['tok', 'note', 'note', 'note:check-slip-check-2-1:2026-09-05:112']);
  assert.deepEqual([b.payload.note, b.payload.list, b.payload.item, b.payload.context], ['he said it right', 'check-slip-check-2-1', '2026-09-05:112', 'Student 07:34 ...']);
  const u = N.body('tok', 'after-2026-10-06', '', '', '');
  assert.deepEqual([u.kind, u.word_key, u.payload.note], ['undo', 'note:after-2026-10-06:list', '']);
  assert.equal(N.body('t', 'l', 'i', 'x'.repeat(900), '').payload.note.length, 600);      // capped
});

test('AM-27 the latest note per card wins and an undo wipes it', () => {
  const rows = [
    { kind: 'note', word_key: 'note:l:a', payload: { note: 'one' }, created_at: '2026-10-07T20:00:00Z' },
    { kind: 'note', word_key: 'note:l:a', payload: { note: 'two' }, created_at: '2026-10-07T20:05:00Z' },
    { kind: 'note', word_key: 'note:l:list', payload: { note: 'list note' }, created_at: '2026-10-07T20:06:00Z' },
    { kind: 'undo', word_key: 'note:l:list', payload: { note: '' }, created_at: '2026-10-07T20:07:00Z' }];
  const m = N.latest(rows.slice().reverse());
  assert.deepEqual(Object.keys(m), ['note:l:a']); assert.equal(m['note:l:a'].note, 'two');
});
