// AM-30 (Medi 2026-10-12 "wait I want amal to look at my notes on 10-9 before grading and clearing it"): the tutor's card of
// the student's notes - one tap = one amal_rules row of the table and kind her other checking lists use (source
// 'listen-check', kind 'note_check', word_key notecheck:<id>, lesson_date null), the box of "partly right" / "wrong" kept in
// payload.typed, and the shared Undo (AM-17: a new 'undo' row, never a delete).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), path = require('path');
globalThis.AneesUndo = require('../docs/js/amal-undo.js');
require('../docs/js/hub/check-task.js');
const C = globalThis.AneesCheckTask;
const D = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'data', 'amal-check-note-check-2026-10-09.json'), 'utf8'));
const x = D.items[0];

test('AM-30 each choice -> the row shape her other checking lists save', () => {
  const r = C.tapBody(D, x, 'TOK', {}, 'answer', 'right');
  assert.deepEqual(Object.keys(r).sort(), ['kind', 'lesson_date', 'payload', 'source', 'token', 'word_key']);
  assert.equal(r.source, 'listen-check'); assert.equal(r.kind, 'note_check'); assert.equal(r.lesson_date, null);
  assert.equal(r.word_key, 'notecheck:' + x.id); assert.equal(r.token, 'TOK');
  assert.equal(r.payload.answer, 'right'); assert.equal(r.payload.done, true); assert.equal(r.payload.list, 'note-check-2026-10-09');
  for (const v of ['right', 'partly', 'wrong', 'not_sure']) assert.equal(C.tapBody(D, x, 'TOK', {}, 'answer', v).payload.answer, v);
});

test('AM-30 the boxes: what is right / why, kept only with their own choice', () => {
  const q = D.questions[0];
  assert.ok(C.boxOf(q, 'partly') && C.boxOf(q, 'wrong')); assert.equal(C.boxOf(q, 'right'), null); assert.equal(C.boxOf(q, 'not_sure'), null);
  assert.equal(C.boxOf(q, 'partly').placeholder, 'What is right?'); assert.equal(C.boxOf(q, 'wrong').placeholder, 'Why? (optional)');
  const saved = C.tapBody(D, x, 'TOK', { answer: 'partly' }, 'answer', 'partly', 'the tomi part');
  assert.equal(saved.payload.typed, 'the tomi part');
  assert.equal(C.tapBody(D, x, 'TOK', { answer: 'partly', typed: 'the tomi part' }, 'answer', 'right').payload.typed, null);
});

test('AM-30 Undo is a new row, and the count follows the latest action', () => {
  const u = C.undoBody(D, x, 'TOK', globalThis.AneesUndo);
  assert.equal(u.kind, 'undo'); assert.equal(u.word_key, 'notecheck:' + x.id); assert.equal(u.source, 'listen-check');
  const k = 'notecheck:' + x.id;
  assert.equal(C.count(D, [{ word_key: k, kind: 'note_check', payload: { answer: 'wrong' } }]).done, 1);
  assert.equal(C.count(D, [{ word_key: k, kind: 'note_check', payload: { answer: 'wrong' } }, { word_key: k, kind: 'undo', payload: {} }]).done, 0);
  assert.equal(C.count(D, []).total, D.items.length);
});
