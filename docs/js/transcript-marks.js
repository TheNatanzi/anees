/* Transcript marks on the Lessons page (PG-20, Medi 2026-10-02: "for the transcript lets put check marks and xs for
   incorrect correct and mark vocab or grammar with grammar rule"; "mark amals signal for correction too"; "underline
   the word thats wrong"). The data is precomputed by scripts/transcript_marks.py into docs/data/lessons/<date>.json
   (tmarks: {turn index: {c: chips, u: underlines}}); this file only draws it. Pure helpers are exported for
   tests/test_transcript_marks.cjs. Nothing here judges anything. */
(function (root) {
'use strict';

var FILTERS = [['all', 'All'], ['marked', 'Only marked'], ['wrong', 'Only ✗'], ['vocab', 'Vocab'], ['grammar', 'Grammar'], ['fix', "Amal's fixes"]];
var LEGEND = [
  ['correct', '✓', 'Correct'], ['partial', '◐', 'Partial · got there with help'], ['asked', '◐', 'Asked Amal for the word'],
  ['wrong', '✗', 'Wrong'], ['fix', '←', "Amal's fix (how she flagged it)"], ['na', '–', 'Not scored (reason on the chip)'],
  ['medi', '?', 'Open question · two judges disagree; Amal decides on her Tutor hub, counted as before until she answers']
];
var WORD = { correct: 'Correct', partial: 'Partial', asked: 'Asked', wrong: 'Wrong', fix: "Amal's fix", na: 'Not scored', medi: 'Open question' };
var SIGN = { correct: '✓', partial: '◐', asked: '◐', wrong: '✗', fix: '←', na: '–', medi: '?' };

function isArabic(s) { return /[؀-ۿ]/.test(s || ''); }
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
// Arabizi for display (rule S1): her spelling when the data has it, else the page's converter, else the Arabic as is.
function az(text, given, toArabizi) {
  if (given) return given;
  if (!text) return '';
  if (toArabizi && isArabic(text)) return toArabizi(text).text;
  return text;
}
// What a chip is about: "vocab · <word>" or "grammar · <rule> <name>"
function subject(c, toArabizi) {
  // PG-21 (Medi 2026-10-02 "you marked the correct word wrong for safar"): a ✗ names what he said → what Amal wanted,
  // never the right word alone (a ✗ beside asaafer read as "asaafer is wrong")
  if (c.k === 'vocab' && c.s === 'wrong' && c.said) return { kind: 'vocab', main: az(c.said, null, toArabizi) + ' → ' + az(c.right || c.ar, c.w, toArabizi), ar: isArabic(c.ar) ? c.ar : '' };
  if (c.k === 'vocab') return { kind: 'vocab', main: az(c.ar, c.w, toArabizi), ar: isArabic(c.ar) ? c.ar : '' };
  if (c.k === 'grammar') return { kind: 'grammar', main: (c.rule || '') + (c.name ? ' ' + c.name : ''), ar: '' };
  if (c.k === 'fix') {
    if (c.of === 'grammar') return { kind: 'grammar', main: c.rule || '', ar: '' };
    return { kind: 'vocab', main: az(c.ar, c.w, toArabizi), ar: isArabic(c.ar) ? c.ar : '' };
  }
  return { kind: /^grammar/.test(c.label || '') ? 'grammar' : /^vocab/.test(c.label || '') ? 'vocab' : 'lesson', main: '', ar: '' };
}
// "said X → Amal: Y" in Arabizi, the Arabic kept for the small line
function pair(said, right, toArabizi) {
  var p = [];
  if (said) p.push('said ' + az(said, null, toArabizi));
  if (right) p.push('Amal: ' + az(right, null, toArabizi));
  return p.join(' → ');
}
// The chip's words: {sign, word, kind, main, ar, tip}
function clock(t) { t = Math.max(0, Math.floor(Number(t) || 0)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); }
function chipModel(c, toArabizi) {
  var s = subject(c, toArabizi), tip = '';
  if (c.s === 'wrong') tip = 'Wrong · ' + [c.said ? 'you said ' + az(c.said, null, toArabizi) : '', c.right ? 'Amal: say ' + az(c.right, null, toArabizi) : ''].filter(Boolean).join(' → ') + (c.sig ? ' (she ' + c.sig + ')' : '') +
    (c.amal_line ? ' · Amal at ' + clock(c.amal_t) + ': «' + c.amal_line + '»' : '');
  else if (c.s === 'asked') tip = 'Asked Amal for the word' + (c.right ? ' → Amal: ' + az(c.right, null, toArabizi) : '');
  else if (c.s === 'partial') tip = 'Partial · got there with help' + (c.said ? ' · said ' + az(c.said, null, toArabizi) : '');
  else if (c.s === 'correct') tip = 'Correct' + (c.said ? ' · said ' + az(c.said, null, toArabizi) : '');
  else if (c.s === 'fix') tip = "Amal's fix: she " + c.sig + (c.said || c.right ? ' · ' + pair(c.said, c.right, toArabizi) : '') +
    (c.english ? ' · she said it in English: «' + c.english + '»' : '');
  else if (c.s === 'medi') tip = (c.label || 'Open question') + ' ' + (c.why || '');
  else tip = 'Not scored: ' + (c.why || '');
  var arSrc = [c.said, c.right].filter(isArabic).join(' → ');
  return {
    sign: SIGN[c.s] || '', word: WORD[c.s] || '', kind: s.kind, main: c.s === 'na' || c.s === 'medi' ? (c.why || '') : s.main,
    ar: s.ar, tip: tip, tipAr: arSrc, sig: c.s === 'fix' ? c.sig : ''
  };
}
// Escape the text and wrap each underline [start, end, cls, chipId, how] (overlaps skipped) in our own <mark>.
function underlined(text, ul) {
  text = String(text == null ? '' : text);
  var out = '', at = 0;
  (ul || []).slice().sort(function (a, b) { return a[0] - b[0]; }).forEach(function (u) {
    if (u[0] < at || u[1] > text.length || u[1] <= u[0]) return;
    out += esc(text.slice(at, u[0])) + '<mark class="tm-ul tm-ul-' + u[2] + '" data-chip="' + esc(u[3]) + '"' +
      (u[4] === 'closest' ? ' data-closest="1"' : '') + '>' + esc(text.slice(u[0], u[1])) + '</mark>';
    at = u[1];
  });
  return out + esc(text.slice(at));
}
// Does a turn show under this filter?
function shows(m, filter) {
  if (filter === 'all') return true;
  var c = (m && m.c) || [];
  if (!c.length) return false;
  if (filter === 'marked') return true;
  if (filter === 'wrong') return c.some(function (x) { return x.s === 'wrong'; });
  if (filter === 'fix') return c.some(function (x) { return x.k === 'fix'; });
  return c.some(function (x) { return x.k !== 'fix' && subject(x, null).kind === filter; });
}
function counts(tmarks) {
  var n = { marked: 0, wrong: 0, vocab: 0, grammar: 0, fix: 0 };
  Object.keys(tmarks || {}).forEach(function (k) {
    var m = tmarks[k];
    ['marked', 'wrong', 'vocab', 'grammar', 'fix'].forEach(function (f) { if (shows(m, f)) n[f]++; });
  });
  return n;
}

var api = { FILTERS: FILTERS, LEGEND: LEGEND, chipModel: chipModel, underlined: underlined, shows: shows, counts: counts };
if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
root.AneesTranscriptMarks = api;
})(this);
