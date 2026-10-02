/* Early values (PG-19, Medi 2026-10-02 "show gray"): a % that has not reached the 30-sentence floor (effect_floor in
   docs/data/sentence-ladder.json) is shown, never blanked, in grey with "early · n 13" under it. At or above the floor
   it is unchanged. Sorting: settled values first, then early ones, then no value at all; inside each group by value.
   Used by the Grammar Console (Hear it column + hear/say pair) and Progress › Fluency (grammar hear vs say, tag chips). */
(function (root) {
'use strict';
function state(show, v) { return v == null || !isFinite(v) ? 'none' : show ? 'settled' : 'early'; }
function tier(show, v) { return { settled: 0, early: 1, none: 2 }[state(show, v)]; }
function label(n) { return 'early · n ' + n; }
function title(n, floor) { return 'Early: only ' + n + ' clear sentence' + (n === 1 ? '' : 's') + ' so far; the % settles at ' + floor + '.'; }
// a, b = {show, v}; dir 'asc' | 'desc'. Settled before early before none, whatever the direction.
function compare(a, b, dir) {
  var t = tier(a.show, a.v) - tier(b.show, b.v);
  if (t) return t;
  if (a.v == null || b.v == null) return 0;
  return (a.v < b.v ? -1 : a.v > b.v ? 1 : 0) * (dir === 'asc' ? 1 : -1);
}
var api = { state: state, tier: tier, label: label, title: title, compare: compare };
if (typeof module === 'object' && module.exports) module.exports = api;
if (root) root.AneesEarly = api;
})(typeof window !== 'undefined' ? window : null);
