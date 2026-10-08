// Homework + Amal's uploads: the pure rules (docs/js/homework-core.js). Medi 2026-10-05 and the grill answers of the same day:
// AM-22 assign homework (3 kinds + cards for a lesson), AI first, Amal confirms / overrules, her overrule is a rule (S6);
// PG-29 homework has its own number (Amal's verdicts only); FC-13 her uploads are card sets + the Shaky words set.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const H = require('../docs/js/homework-core.js');

const T = (id, kind, extra) => ({ id, kind, created_at: '2026-10-05T10:00:00Z', prompt: 'p', ...extra });
const R = (id, task_id, ai, at) => ({ id, task_id, answer: 'ana bas7a', ai, created_at: at || '2026-10-05T11:00:00Z' });
const V = (id, reply_id, verdict, agrees, at, extra) => ({ id, reply_id, kind: 'verdict', verdict, agrees, created_at: at || '2026-10-05T12:00:00Z', ...extra });

test('AM-22 undo is a new row, never a delete: an undone task is gone, an undone undo brings it back, a replayed id is one row', () => {
  const a = T('a', 'translate'), u = { id: 'u', kind: 'undo', undoes: 'a', created_at: '2026-10-05T10:01:00Z' }, u2 = { id: 'u2', kind: 'undo', undoes: 'u', created_at: '2026-10-05T10:02:00Z' };
  assert.deepEqual(H.effective([a, u]).map(r => r.id), []);
  assert.deepEqual(H.effective([a, u, u2]).map(r => r.id), ['a']);
  assert.deepEqual(H.effective([a, a]).map(r => r.id), ['a']);
});

test('AM-22 a task is to do, then checking, then waiting for Amal once the AI spoke, then done only when SHE has a verdict', () => {
  const t = T('t1', 'translate', { direction: 'en_ar' });
  assert.equal(H.taskState(t, [], []).state, 'todo');
  assert.equal(H.taskState(t, [R('r1', 't1', null)], []).state, 'checking');
  const ai = { verdict: 'close', reason: 'say bas7a' };
  assert.equal(H.taskState(t, [R('r1', 't1', ai)], []).state, 'waiting');
  const s = H.taskState(t, [R('r1', 't1', ai)], [V('v1', 'r1', 'right', false, undefined, { note: 'bas7a is fine here' })]);
  assert.equal(s.state, 'done'); assert.equal(s.final, 'right'); assert.equal(s.verdict.agrees, false);     // her overrule wins over the AI
  // her undo of the verdict puts the answer back on her list
  assert.equal(H.taskState(t, [R('r1', 't1', ai)], [V('v1', 'r1', 'right', false), { id: 'x', reply_id: 'r1', kind: 'undo', undoes: 'v1', created_at: '2026-10-05T12:05:00Z' }]).state, 'waiting');
});

test('PG-29 the homework number counts Amal\'s verdicts only - right 1, close 1/2, wrong 0 - never the AI\'s; no verdict = no number', () => {
  const tasks = [T('t1', 'translate'), T('t2', 'create', { words: ['Jumle'] }), T('t3', 'question'), T('t4', 'cards', { set_ref: 'q:1', n_cards: 10 })];
  const ai = { verdict: 'right' };
  const replies = [R('r1', 't1', ai), R('r2', 't2', ai), R('r3', 't3', ai)];
  assert.equal(H.score(tasks, replies, []).pct, null);                     // the AI said right three times: still no number
  const sc = H.score(tasks, replies, [V('v1', 'r1', 'right', true), V('v2', 'r2', 'close', false), V('v3', 'r3', 'wrong', false)]);
  assert.equal(sc.done, 3); assert.equal(sc.pct, 50); assert.equal(sc.total, 3);   // the cards task is not a text task
  assert.equal(sc.overruled, 2); assert.equal(sc.agreed, 1);
});

test('FC-13 an upload is a card set keyed u:<upload>:<n> with her spelling as written; a PERMANENT set is a Doc reminder until the Doc has the word', () => {
  const up = { id: 'abcdefgh', kind: 'upload', title: 'Function words', keep: 'permanent', created_at: '2026-10-05T09:00:00Z',
               rows: [{ arabizi: 'Awal', arabic: 'أول', english: 'First / beginning' }, { arabizi: 'Mayy', arabic: 'مي', english: 'water' }, { arabizi: '', arabic: '', english: 'nothing' }] };
  const sets = H.uploadSets([up]);
  assert.equal(sets.length, 1); assert.equal(sets[0].id, 'u:abcdefgh'); assert.equal(sets[0].n, 2);
  assert.deepEqual(sets[0].cards.map(c => c.key), ['u:abcdefgh:1', 'u:abcdefgh:2']);
  assert.equal(sets[0].cards[0].arabizi, 'Awal');
  const rem = H.permanentReminder(sets, [{ key: 'maI', arabizi: 'Mayy', arabic: 'مي', english: 'water' }]);
  assert.deepEqual(rem.map(c => [c.arabizi, c.in_doc]), [['Awal', false], ['Mayy', true]]);
  assert.deepEqual(H.permanentReminder(H.uploadSets([{ ...up, keep: 'temporary' }]), []), []);   // temporary = cards only
  assert.deepEqual(H.uploadSets([up, { id: 'undo1234', kind: 'undo', undoes: 'abcdefgh', created_at: '2026-10-05T09:30:00Z' }]), []);
});

test('FC-13 Shaky words: the last 2 lessons\' misses stay until two right card answers AFTER the lesson', () => {
  const shaky = { lessons: ['2026-10-01', '2026-10-02'], words: [{ key: 'ana bas7a', date: '2026-10-02', kind: 'wrong' }, { key: '7ada', date: '2026-10-01', kind: 'wrong' }] };
  const got = (k, ts) => ({ word_key: k, result: 'got', ts });
  assert.deepEqual(H.shakyCards(shaky, []).map(w => w.key), ['ana bas7a', '7ada']);
  assert.deepEqual(H.shakyCards(shaky, [got('7ada', '2026-10-03T10:00:00Z')]).map(w => w.key), ['ana bas7a', '7ada']);               // one right: stays
  assert.deepEqual(H.shakyCards(shaky, [got('7ada', '2026-10-03T10:00:00Z'), got('7ada', '2026-10-04T10:00:00Z')]).map(w => w.key), ['ana bas7a']);   // two: gone
  assert.deepEqual(H.shakyCards(shaky, [got('7ada', '2026-09-20T10:00:00Z'), got('7ada', '2026-09-21T10:00:00Z')]).map(w => w.key), ['ana bas7a', '7ada']);   // before the slip: do not count
  assert.deepEqual(H.shakyCards(shaky, [{ word_key: '7ada', result: 'missed', ts: '2026-10-03T10:00:00Z' }, { ...got('7ada', '2026-10-03T11:00:00Z'), undone_at: 'x' }]).map(w => w.key), ['ana bas7a', '7ada']);
});

test('PG-28 a cards assignment counts the distinct cards answered in that set since it was assigned', () => {
  const t = T('t4', 'cards', { set_ref: 'q:1', n_cards: 10, created_at: '2026-10-05T10:00:00Z' });
  const log = [{ word_key: 'a', result: 'got', ts: '2026-10-05T11:00:00Z', subject: 'sel:q:1' }, { word_key: 'a', result: 'missed', ts: '2026-10-05T11:01:00Z', subject: 'sel:q:1' },
               { word_key: 'b', result: 'got', ts: '2026-10-04T11:00:00Z', subject: 'sel:q:1' }, { word_key: 'c', result: 'got', ts: '2026-10-05T11:00:00Z', subject: 'sel:q:2' }];
  assert.equal(H.cardsDone(t, log), 1);
});

test('AM-22 the three homework kinds and both translate directions exist; the script of an answer is told apart', () => {
  assert.deepEqual(Object.keys(H.KINDS), ['translate', 'create', 'question', 'cards']);
  assert.deepEqual(Object.keys(H.DIRECTIONS), ['en_ar', 'ar_en']);
  assert.equal(H.scriptOf('ana bas7a'), 'arabizi'); assert.equal(H.scriptOf('أنا صحيت'), 'arabic'); assert.equal(H.scriptOf('I woke up'), 'english');
});

test('PG-35 every set Amal uploads is on the Student tab: an upload with no cards task is a cards row of its own; her assignment takes over', () => {
  // Medi 2026-10-08 "see why amal uploaded two card sets but the student page only shows one"
  const up = (id, title, n, keep, at) => ({ id, kind: 'upload', title, keep, n, created_at: at, rows: Array.from({ length: n }, (_, i) => ({ arabizi: 'w' + i, arabic: '', english: 'e' + i })) });
  const uploads = [up('c95f', 'Function (tool) Words + "el"', 22, 'permanent', '2026-10-06T03:21:24Z'), up('17b0', 'A list', 40, 'temporary', '2026-10-06T23:17:40Z')];
  const tasks = [T('d9bb', 'cards', { set_ref: 'u:c95f', set_title: 'Function (tool) Words + "el"', n_cards: 22, lesson_date: '2026-10-06' })];
  const extra = H.unassignedUploads(uploads, tasks);
  assert.deepEqual(extra.map(x => [x.set_ref, x.set_title, x.n_cards, x.lesson_date, x.upload]), [['u:17b0', 'A list', 40, null, true]]);
  assert.equal(extra[0].created_at, '2026-10-06T23:17:40Z');                       // the tile link and cardsDone both key off set_ref / created_at
  assert.deepEqual(H.unassignedUploads(uploads, []).map(x => x.set_ref), ['u:17b0', 'u:c95f']);   // nothing assigned: both show, newest first
  const undone = uploads.concat([{ id: 'x', kind: 'undo', undoes: '17b0', created_at: '2026-10-07T00:00:00Z' }]);
  assert.deepEqual(H.unassignedUploads(undone, tasks), []);                         // an upload she took back is gone (AM-17)
  assert.equal(H.cardsDone(extra[0], [{ word_key: 'u:17b0:1', result: 'good', ts: '2026-10-07T01:00:00Z', subject: 'sel:u:17b0' }]), 1);
});
