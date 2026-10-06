// PG-32 (Medi 2026-10-06 "a universal system that completes it right away"): the Done tab shows her answers from the
// link's own database row, not from the built tutor.json. Real case: the Oct 2 "After the lesson" link - Amal answered
// all 5 moments on Oct 3 (Right, Right, Wrong word, Wrong word, Right), the publish was blocked for three days, and the
// Done tab said "0 of 5 answered · not answered" under a row that was already finished.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const L = require('../docs/js/hub/live-detail.js');

const BUILT = { answered: 0, total: 5, asked: [0, 1, 2, 3, 4].map(i => ({ ask: 'Did Medi get this wrong here?', word: 'w' + i, t: '08:23', answer: null, at: null, result: null })) };
const ROW = { payload: { questions: [{}, {}, {}, {}, {}] }, done_at: '2026-10-03 22:00:43.88+00',
  answers: { q: { 0: 'Right', 1: 'Right', 2: 'Wrong word', 3: 'Wrong word', 4: 'Right' }, done: true, step: 5, updated: '2026-10-03T22:00:43.880Z' } };

test('the Oct 2 link: five live answers over a built detail that had none', () => {
  const d = L.overlay('after', BUILT, ROW);
  assert.equal(d.answered, 5); assert.equal(d.total, 5); assert.equal(d.live, true);
  assert.deepEqual(d.asked.map(x => x.answer), ['Right', 'Right', 'Wrong word', 'Wrong word', 'Right']);
  assert.equal(d.asked[2].result, 'slip counted for Medi (word)');
  assert.equal(d.asked[0].at, '2026-10-03');
  assert.equal(BUILT.asked[0].answer, null, 'the built detail is never changed in place');
});

test('an undo opens the row again: no answer, no date, no result', () => {
  const built = { answered: 1, total: 1, asked: [{ ask: 'q', answer: 'Right', at: '2026-10-03', result: 'not counted as a slip' }] };
  const d = L.overlay('after', built, { payload: { questions: [{}] }, answers: { q: {} } });
  assert.deepEqual([d.asked[0].answer, d.asked[0].at, d.asked[0].result, d.answered], [null, null, null, 0]);
});

test('homework and prompt answers map after the questions, by position and by id', () => {
  const built = { answered: 0, total: 4, asked: [{ ask: 'q' }, { ask: 'q' }, { ask: 'Homework suggestion: keep, drop or edit?' }, { ask: 'Homework line: keep, drop or edit?' }] };
  const row = { payload: { questions: [{}, {}], homework: [{}], prompts: [{ id: 'p9' }] }, answers: { q: { 1: 'Skip' }, hw: { 0: 'keep' }, pr: { p9: 'drop' }, updated: '2026-10-05T01:02:03Z' } };
  const d = L.overlay('after', built, row);
  assert.deepEqual(d.asked.map(x => x.answer), [null, 'Skip', 'keep', 'drop']);
  assert.equal(d.asked[1].result, 'no change');
  assert.equal(d.answered, 3);
});

test('no row (expired link), no payload, or a list that disagrees with the link: the built record stands', () => {
  assert.equal(L.overlay('after', BUILT, null), BUILT);
  assert.equal(L.overlay('after', BUILT, { answers: { q: { 0: 'Right' } } }), BUILT);
  assert.equal(L.overlay('after', BUILT, { payload: { questions: [{}, {}] }, answers: { q: { 0: 'Right' } } }), BUILT);
  assert.equal(L.overlay('verify', BUILT, ROW), BUILT);
});

test('before the lesson: topic, words to repeat, then each sentence', () => {
  const built = { answered: 0, total: 3, asked: [{ ask: "What is today's lesson about?" }, { ask: 'Words for today' }, { ask: 'Keep this sentence?', word: 's1' }] };
  const row = { payload: { sentences: [{}] }, answers: { topic: 'colours', repeat: ['ahmar', 'akhdar'], sentences: { 0: 'keep' }, updated: '2026-10-04T10:00:00Z' } };
  const d = L.overlay('before', built, row);
  assert.deepEqual(d.asked.map(x => x.answer), ['colours', 'ahmar, akhdar', 'keep']);
  assert.equal(d.asked[0].at, '2026-10-04');
});

test('word review and verb check read their own answer shapes', () => {
  const wr = L.overlay('word_review', { answered: 0, total: 2, asked: [{ ask: 'What do you hear?', word: 'a' }, { ask: 'What do you hear?', word: 'b' }] },
    { payload: { items: [{ id: 'i1' }, { id: 'i2' }] }, answers: { answers: { i1: { choice: 'yes', updated_at: '2026-10-05T09:00:00Z' }, i2: { choice: 'different', text: 'bet' } } } });
  assert.deepEqual(wr.asked.map(x => x.answer), ['Yes, that is what I hear', 'Different: bet']);
  assert.equal(wr.asked[0].at, '2026-10-05');
  const vc = L.overlay('verb_check', { answered: 0, total: 3, asked: [] },
    { payload: { items: { f1: { tense: 'past', person: 'ana', word: 'ruht' }, f2: { tense: 'now', person: 'inta', word: 'btruh' }, f3: {} } },
      answers: { answers: { f2: { choice: 'no', word: 'bitruh', updated_at: '2026-10-05T09:01:00Z' }, f1: { choice: 'yes', updated_at: '2026-10-05T09:00:00Z' } } } });
  assert.deepEqual(vc.asked.map(x => [x.word, x.answer]), [['ruht', 'Right'], ['btruh', 'Fixed: bitruh']]);
  assert.deepEqual([vc.answered, vc.total], [2, 3]);
});

test('the REST path reads payload + answers + done_at with the link token; kinds without a link row read nothing', () => {
  assert.equal(L.path('after', 'T1'), 'amal_links?select=payload,answers,done_at&token=eq.T1');
  assert.equal(L.path('verb_check', 'T1'), 'verb_check_links?select=payload,answers,done_at&token=eq.T1');
  assert.equal(L.path('verify', 'T1'), null);
  assert.equal(L.path('after', ''), null);
});

test('live(): a failed read falls back to the built detail, never a blank', async () => {
  const item = { kind: 'after', token: 'T1', detail: BUILT };
  assert.equal(await L.live('after', item, async () => { throw new Error('401'); }), BUILT);
  const d = await L.live('after', item, async () => [ROW]);
  assert.equal(d.answered, 5);
});
