// AM-19: words Amal taught -> her New words card (docs/js/hub/new-words-task.js) and the Word Bank promised list
// (docs/js/promised-words.js): older cards fold past the limit, every lesson is cited, "still waiting" after 7 days.
const test = require('node:test'), assert = require('node:assert/strict');
require('../docs/js/hub/new-words-task.js');
require('../docs/js/promised-words.js');
const T = globalThis.AneesNewWordsTask, P = globalThis.AneesPromised;
const card = (id, date, source) => ({ id, date, source: source || 'taught' });
test('AM-19 older lesson cards fold under From older lessons only past older_fold', () => {
  const data = { older_before: '2026-10-01', older_fold: 2 };
  const few = [card('a', '2026-10-02', null), card('b', '2026-09-26'), card('c', '2026-09-28')];
  assert.deepEqual(T.split(few, data), { newest: few, older: [] });
  const many = few.concat([card('d', '2026-09-16'), card('g', '2026-10-02', 'glue')]);
  const s = T.split(many, data);
  assert.deepEqual(s.older.map(x => x.id), ['b', 'c', 'd']);
  assert.deepEqual(s.newest.map(x => x.id), ['a', 'g']);
});
test('AM-19 a card cites the other lessons it was taught in', () => {
  assert.equal(T.alsoOf({ also: [{ date: '2026-09-28', mmss: '10:00' }] }), ' · also Sep 28 10:00');
  assert.equal(T.alsoOf({}), '');
});
test('AM-19 still waiting after 7 days: a mark on her list and one line for Medi', () => {
  assert.equal(T.stillWaiting({ state: 'waiting', still_waiting: true, waiting_days: 8 }), ' · still waiting (8 days)');
  assert.equal(T.stillWaiting({ state: 'waiting', still_waiting: false }), '');
  const late = { id: 'x', arabizi: 'laffe', arabic: 'لفة', date: '2026-10-01', state: 'waiting', still_waiting: true, waiting_days: 9 };
  const h = P.html({ promised: [late, { id: 'y', arabic: 'ممتاز', state: 'waiting' }] });
  assert.match(h, /1 word Amal said she'd add still not in the Doc after 7 days: laffe\./);
  assert.match(P.label(late), /Waiting · still waiting \(9 days\)/);
  assert.equal(P.note([{ state: 'in_doc', still_waiting: false }]), '');
});
