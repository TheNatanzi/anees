// PG-36 (Medi 2026-10-08: "lets set up a system where my scores get sent back to her. If I do the card set 1 time send score.
// If I fix mistakes tell her how I did, If I do it again 30 min or however long later tell her how many hr/min after I tried
// again with new scores"). Nothing is sent (AM-01): the section on her Tutor page reads the card_results rounds.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), path = require('path');
const M = require('../docs/js/hub/results-task.js');
const R = M.AneesResultsTask || globalThis.AneesResultsTask;
const DOCS = path.join(__dirname, '..', 'docs');
const row = (key, result, ts, attempt, round_id, extra) => ({ word_key: key, result, ts, attempt, round_id, subject: 'sel:u:17b0', ...extra });

test('PG-36 one try = first-pass score, the fix-mistakes retry score, and for a later try how long after the one before', () => {
  const log = [
    row('a', 'got', '2026-10-07T01:00:00Z', 1, 'r1'), row('b', 'missed', '2026-10-07T01:00:10Z', 1, 'r1'), row('c', 'missed', '2026-10-07T01:00:20Z', 1, 'r1'),
    row('b', 'got', '2026-10-07T01:01:00Z', 1, 'r1'), row('c', 'missed', '2026-10-07T01:01:10Z', 2, 'r1-2'),   // the retry: a card dealt again in the round + the review pass (round id + '-2'): 1 of 2 fixed
    row('a', 'got', '2026-10-07T03:15:00Z', 1, 'r2'), row('b', 'got', '2026-10-07T03:15:10Z', 1, 'r2'), row('c', 'got', '2026-10-07T03:15:20Z', 1, 'r2'),
    row('zz', 'got', '2026-10-07T03:20:00Z', 1, 'x', { subject: 'fsrs' }),                                        // not a set round
    row('a', 'got', '2026-10-07T04:00:00Z', 1, 'r3', { undone_at: '2026-10-07T04:00:05Z' }),                       // undone, ignored
  ];
  const v = R.view(log, [{ id: 'u:17b0', title: 'A list', n: 3 }]);
  assert.equal(v.length, 1); assert.equal(v[0].title, 'A list'); assert.equal(v[0].tries.length, 2);
  const [t1, t2] = v[0].tries;
  assert.deepEqual(t1.first, { got: 1, n: 3, pct: 33 }); assert.deepEqual(t1.fix, { got: 1, n: 2, pct: 50 }); assert.equal(t1.after_min, null);
  assert.deepEqual(t2.first, { got: 3, n: 3, pct: 100 }); assert.equal(t2.fix, null); assert.equal(t2.after_min, 135);
  assert.equal(R.gap(135), '2 h 15 min'); assert.equal(R.gap(35), '35 min'); assert.equal(R.gap(1500), '1 day 1 h');
  assert.deepEqual(R.count(v), { total: 2, done: 2, left: 0 });
  const names = R.view([row('a', 'got', '2026-10-07T01:00:00Z', 1, 'x', { subject: 'sel:shaky|speaking|All' }), row('a', 'got', '2026-10-07T01:00:00Z', 1, 'y', { subject: 'sel:all:topic:Household Items' })], []).map(x => x.title);
  assert.deepEqual(names.sort(), ['Household Items', 'Shaky words']);
});

test('PG-36 the Tutor page loads the module and nothing in it writes or sends anything (AM-01)', () => {
  assert.ok(fs.readFileSync(path.join(DOCS, 'tutor.html'), 'utf8').includes('js/hub/results-task.js'));
  const src = fs.readFileSync(path.join(DOCS, 'js', 'hub', 'results-task.js'), 'utf8');
  assert.ok(!/fetch\(|method:\s*'POST'|mailto|sms:/.test(src));
  assert.ok(fs.readFileSync(path.join(DOCS, 'js', 'tutor.js'), 'utf8').includes("id: 'results', kind: 'results'"));
});
