// AM-29 (Medi 2026-10-11 "mix 30-20"): the tutor's key-check card on her Tutor page - one tap = one amal_rules row of the
// table and kind her other checking lists already use (source 'listen-check', kind 'key_check', word_key keycheck:<id>,
// lesson_date null), the box of "The words are not what the student said" / "The student made a mistake here" kept in
// payload.typed, and the shared Undo (AM-17: a new 'undo' row, never a delete; the latest action per card wins).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), path = require('path');
globalThis.AneesUndo = require('../docs/js/amal-undo.js');
require('../docs/js/hub/check-task.js');
const C = globalThis.AneesCheckTask;
const D = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'data', 'amal-check-key-check-2026-10-09.json'), 'utf8'));
const x = D.items[0];

test('AM-29 each choice -> the row shape her other checking lists save', () => {
  const r = C.tapBody(D, x, 'TOK', {}, 'answer', 'right');
  assert.deepEqual(Object.keys(r).sort(), ['kind', 'lesson_date', 'payload', 'source', 'token', 'word_key']);
  assert.equal(r.source, 'listen-check'); assert.equal(r.kind, 'key_check'); assert.equal(r.lesson_date, null);
  assert.equal(r.word_key, 'keycheck:' + x.id); assert.equal(r.token, 'TOK');
  assert.equal(r.payload.answer, 'right'); assert.equal(r.payload.typed, null); assert.equal(r.payload.done, true);
  assert.equal(r.payload.list, 'key-check-2026-10-09'); assert.equal(r.payload.label, '2026-10-09 ' + x.mmss);
  for (const v of ['right', 'words', 'mistake', 'cant_tell']) assert.equal(C.tapBody(D, x, 'TOK', {}, 'answer', v).payload.answer, v);
});

test('AM-29 the box: what he really said / how it should be said, kept only with its own choice', () => {
  const q = D.questions[0];
  assert.ok(C.boxOf(q, 'words') && C.boxOf(q, 'mistake')); assert.equal(C.boxOf(q, 'right'), null); assert.equal(C.boxOf(q, 'cant_tell'), null);
  const tap = C.tapBody(D, x, 'TOK', {}, 'answer', 'words');                      // the tap is saved at once, the box opens empty
  assert.equal(tap.payload.typed, null);
  const was = { answer: 'words', typed: null };
  const saved = C.tapBody(D, x, 'TOK', was, 'answer', 'words', 'ana 3ayaan');      // Save
  assert.equal(saved.payload.typed, 'ana 3ayaan'); assert.equal(saved.payload.answer, 'words');
  const again = C.tapBody(D, x, 'TOK', { answer: 'words', typed: 'ana 3ayaan' }, 'answer', 'words');   // tapping the same choice keeps it
  assert.equal(again.payload.typed, 'ana 3ayaan');
  const other = C.tapBody(D, x, 'TOK', { answer: 'words', typed: 'ana 3ayaan' }, 'answer', 'right');   // another choice drops it
  assert.equal(other.payload.typed, null);
  const mis = C.tapBody(D, x, 'TOK', { answer: 'words', typed: 'ana 3ayaan' }, 'answer', 'mistake');   // a new box starts empty
  assert.equal(mis.payload.typed, null);
  assert.equal(C.tapBody(D, x, 'TOK', { answer: 'mistake' }, 'answer', 'mistake', null).payload.typed, null);   // an emptied box saves nothing
});

test('AM-29 undo is a new row of kind undo; the latest action per card counts', () => {
  const tap = C.tapBody(D, x, 'TOK', {}, 'answer', 'mistake', 'ana 3ayyaan');
  const u = C.undoBody(D, x, 'TOK');
  assert.equal(u.kind, 'undo'); assert.equal(u.word_key, tap.word_key); assert.equal(u.source, 'listen-check');
  assert.equal(u.payload.undoes, 'key_check'); assert.equal(u.lesson_date, null);
  const y = D.items[1], t2 = C.tapBody(D, y, 'TOK', {}, 'answer', 'cant_tell');
  assert.deepEqual(C.count(D, [tap, t2]), { total: 50, done: 2 });
  assert.deepEqual(C.count(D, [tap, t2, u]), { total: 50, done: 1 });            // tap -> undo: open again
  assert.deepEqual(C.count(D, [tap, t2, u, tap]), { total: 50, done: 2 });       // tap -> undo -> tap again
});
