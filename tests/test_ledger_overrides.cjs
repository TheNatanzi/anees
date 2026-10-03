// LS-11 one lesson ledger (Medi 2026-10-02: the marked transcript is the one source of every judgment). The ledger's
// decision on a Word Bank event travels in docs/data/word-bank-audit-slips.json `overrides`; every page that scores words
// goes through withSlips() -> apply(), so the Word Bank, Progress and Flashcards follow the ledger.
'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), path = require('path');
const Rv = require(path.join(__dirname, '..', 'docs', 'js', 'word-bank-review.js'));
const C = require(path.join(__dirname, '..', 'docs', 'js', 'word-bank-core.js'));

const lisa = { id: 'e-lisa', word_key: 'lisa', t_start: 92.92, t_end: 93.3, lesson_date: '2026-10-01', speaker: 'Medi', spoken: true,
  vocab_points: 1, assessment: 'independent', text: 'لسه', reason: 'provisional lexical use' };
const doc = { events: [], overrides: [{ event_id: 'e-lisa', expected: { word_key: 'lisa', t_start: 92.92 },
  changes: { observation_only: true, ledger: 'ra:FA-1', ledger_reason: 'Said here, another word intended' } }] };

test('LS-11 an override applies only while the event is the one the ledger saw', () => {
  const out = Rv.apply(Rv.withSlips([lisa], doc), {}).events;
  assert.equal(out[0].observation_only, true);
  assert.equal(C.points(out[0]), null);                         // no longer a Correct in any page's count
  const moved = Rv.apply(Rv.withSlips([{ ...lisa, t_start: 50 }], doc), {}).events;
  assert.equal(moved[0].observation_only, undefined);            // changed event: left alone (the guard fails instead)
});

test('LS-11 a review patch on the same event still matches after the override (no stale source guard)', () => {
  const review = { patches: { 'e-lisa': { expected: { word_key: 'lisa', reason: 'provisional lexical use' }, changes: { assessment: 'independent' } } } };
  const r = Rv.apply(Rv.withSlips([lisa], doc), review);
  assert.deepEqual(r.stale, []);
  assert.equal(r.events[0].observation_only, true);
});

test('LS-11 an override reaches an event the review overlay adds (additions)', () => {
  const anchor = { id: 'a1', source_sha256: 'x', speaker: 'Medi' };
  const review = { additions: [{ anchor_id: 'a1', expected_source: 'x', event: lisa }] };
  const r = Rv.apply(Rv.withSlips([anchor], doc), review);
  assert.equal(r.events.find(e => e.id === 'e-lisa').observation_only, true);
});
