// Eng audit 2026-09-29 (decision 6): a word slip from the full audit, once in docs/data/word-bank-audit-slips.json, is
// scored by the Word Bank's own code exactly like any lesson attempt; a preposition slip is not (grammar, standing
// decision 2026-09-21). Before: the Lessons page counted 211 on-list slips the Word Bank never saw (e.g. 09-28:
// Lessons 15 wrong vs Word Bank 0), and re-rated words with its own bands. node tests/test_word_slips.cjs
'use strict';
const assert = require('node:assert/strict'), path = require('path');
const C = require(path.join(__dirname, '..', 'docs', 'js', 'word-bank-core.js'));
const Rv = require(path.join(__dirname, '..', 'docs', 'js', 'word-bank-review.js'));
assert.equal(typeof Rv.withSlips, 'function', 'word-bank-review.js has no withSlips(): pages cannot load the audit slips');
const words = [{ key: 'ftUr', arabizi: 'Ftoor', arabic: 'فطور', english: 'Breakfast', topic: 'Food' }, { key: 'ma3', arabizi: 'ma3', arabic: 'مع', english: 'With', topic: 'Prepositions' }];
const right = { id: 'e1', word_key: 'ftUr', lesson_date: '2026-09-21', t_start: 10, t_end: 11, speaker: 'Medi', assessment: 'independent', text: 'فطور' };
const slip = { id: 'audit:FA-1', word_key: 'ftUr', entry_id: 'ftUr:word', lesson_date: '2026-09-23', t_start: 20, t_end: 20, speaker: 'Medi', spoken: true,
  review_locked: true, classification: 'lexical', assessment: 'incorrect', vocab_points: 0, text: 'فطر', source: 'audit-2026-09-26' };
const prep = { ...slip, id: 'audit:FA-2', word_key: 'ma3', entry_id: 'ma3:word' };
const events = Rv.apply(Rv.withSlips([right], { events: [slip, prep, slip] }), {}).events;   // a repeated id is added once
assert.equal(events.length, 3);
const rows = C.models(words, { groups: [] }, C.prepareEvidence(events), []);
const f = rows.find(r => r.key === 'ftUr').entries[0];
assert.equal(f.speaking.count, 2, 'the slip is a scored attempt');
assert.equal(f.speaking.status, 'Shaky', 'right then wrong = Shaky (the Word Bank streak rule)');
assert.equal(rows.find(r => r.key === 'ma3').entries[0].speaking.count, 0, 'a preposition slip is grammar, not a vocabulary attempt');
console.log('word slips: ok');
