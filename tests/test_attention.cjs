// FC-14 (Medi 2026-10-06: "For all the cards I want a third option called attention with the attention icon. This will send a
// to do message where I can ask Amal a questions or bring up a concern with her. This should be sent to the tutor portal").
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), path = require('path');
globalThis.AneesHomework = require('../docs/js/homework-core.js');
require('../docs/js/hub/attention-task.js');
const A = globalThis.AneesAttentionTask;
const DOCS = path.join(__dirname, '..', 'docs');

test('FC-14 a note is open until a reply that is not undone answers it; undo of the reply reopens it', () => {
  const n = { id: 'n1', kind: 'note', card_key: 'k', text: 'which one?', by_who: 'student', created_at: '2026-10-06T01:00:00Z' };
  const r = { id: 'r1', kind: 'reply', ref: 'n1', text: 'yoam tani', by_who: 'teacher', created_at: '2026-10-06T02:00:00Z' };
  const u = { id: 'u1', kind: 'undo', undoes: 'r1', by_who: 'teacher', created_at: '2026-10-06T03:00:00Z' };
  assert.deepEqual(A.count([n]), { total: 1, done: 0, left: 1 });
  assert.deepEqual(A.count([n, r]), { total: 1, done: 1, left: 0 });
  assert.deepEqual(A.count([n, r, u]), { total: 1, done: 0, left: 1 });
  assert.equal(A.view([n, r]).answered[0].replies[0].text, 'yoam tani');
});

test('FC-14 every flashcard has the ⚠ button beside ✕ / ✓, and both portals load the attention module', () => {
  const cards = fs.readFileSync(path.join(DOCS, 'cards.html'), 'utf8');
  assert.ok(/<button id="attn" class="attn"/.test(cards) && /rest\/v1\/card_attention/.test(cards));
  assert.ok(cards.indexOf('id="got"') < cards.indexOf('id="attn"'));
  for (const f of ['tutor.html', 'student.html']) assert.ok(fs.readFileSync(path.join(DOCS, f), 'utf8').includes('js/hub/attention-task.js'), f);
  assert.ok(fs.readFileSync(path.join(DOCS, 'js', 'tutor.js'), 'utf8').includes("title: 'Questions from the student'"));
});
