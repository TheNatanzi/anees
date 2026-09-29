// System Settings "Publish guard" line (docs/js/publish-guard-status.js, Medi decision 7, 2026-09-29).
const test = require('node:test'), assert = require('node:assert/strict');
const { guardLine, when } = require('../docs/js/publish-guard-status.js');

const pass = {
  updated: '2026-09-30T16:32:10-07:00', result: 'pass', source: 'hourly lessons 2026-09-30',
  checks: [{ id: 'accuracy_gates', required: true, ok: true, what: 'pages agree' },
           { id: 'check_numbers', required: true, ok: true },
           { id: 'review_freshness', required: false, ok: false }],
  warnings: ['review_freshness: 2026-09-23: transcript changed after the readers read it'],
  last_block: { at: '2026-09-30T15:15:40-07:00', source: 'tutor_refresh', reason: 'check_numbers: Word Bank 312 != Lessons 309' },
  blocks_before_this_pass: 3,
};

test('a pass says when and how many required checks passed', () => {
  const l = guardLine(pass);
  assert.equal(l.state, 'pass');
  assert.match(l.text, /Sep 30, 16:32/);
  assert.match(l.text, /2 of 2 checks passed/);
});

test('the last block reaches Medi once a later run passes', () => {
  const d = guardLine(pass).details.join('\n');
  assert.match(d, /Last block: Sep 30, 15:15 \(tutor_refresh\) - check_numbers: Word Bank 312 != Lessons 309/);
  assert.match(d, /3 blocked runs before this pass/);
  assert.match(d, /Warning \(does not block\): review_freshness/);
});

test('no file or no pass is never shown as a pass', () => {
  assert.equal(guardLine(null).state, 'unknown');
  assert.equal(guardLine({ result: 'blocked' }).state, 'unknown');
  assert.match(guardLine(null).text, /no passing check/);
});

test('times are read from the text, not re-zoned', () => {
  assert.equal(when('2026-01-05T09:03:00+00:00'), 'Jan 5, 09:03');
  assert.equal(when(''), 'an unknown time');
});
