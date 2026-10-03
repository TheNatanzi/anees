// Rule LS-04 (Medi 2026-10-02: "Why didn't today's get loaded"): each problem the hourly job wrote to
// docs/data/lesson-alerts.json shows on Progress and Lessons as one line (docs/js/lesson-behind.js).
const test = require('node:test'), assert = require('node:assert/strict');
const { alertLines } = require('../docs/js/lesson-behind.js');


test('LS-04: a lesson that failed to load is one line with its start time', () => {
  const since = new Date(2026, 9, 1, 15, 15).toISOString();
  const doc = { problems: [{ key: 'load:2026-10-01', kind: 'not-loaded', text: '10-01 lesson not loaded: voice-to-text credits ran out', since }] };
  assert.deepEqual(alertLines(doc, new Date(2026, 9, 1, 20, 0)), ['10-01 lesson not loaded: voice-to-text credits ran out (since 15:15)']);
  assert.deepEqual(alertLines(doc, new Date(2026, 9, 2, 9, 0)), ['10-01 lesson not loaded: voice-to-text credits ran out (since 10-01 15:15)']);
});

test('LS-04: no file, an empty file or a bad row shows nothing', () => {
  assert.deepEqual(alertLines(null), []);
  assert.deepEqual(alertLines({ problems: [] }), []);
  assert.deepEqual(alertLines({ problems: [{ key: 'x' }] }), []);
  assert.deepEqual(alertLines({ problems: [{ text: 'Voice-to-text credits low: 133 left, a lesson needs about 1360', since: 'nonsense' }] }),
    ['Voice-to-text credits low: 133 left, a lesson needs about 1360']);
});

test("AM-20: a stale Amal Doc export reads \"Amal's word Doc not synced since <time>: <reason>\"", () => {
  const since = new Date(2026, 9, 2, 14, 5).toISOString();
  const doc = { problems: [{ key: 'doc-sync', kind: 'doc-stale', since,
    text: "Amal's word Doc not synced since {since}: the Google export failed: export HTTP 403" }] };
  assert.deepEqual(alertLines(doc, new Date(2026, 9, 2, 18, 0)), ["Amal's word Doc not synced since 14:05: the Google export failed: export HTTP 403"]);
  assert.deepEqual(alertLines(doc, new Date(2026, 9, 3, 9, 0)), ["Amal's word Doc not synced since 10-02 14:05: the Google export failed: export HTTP 403"]);
});
