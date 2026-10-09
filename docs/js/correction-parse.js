/* One box for a line fix (PG-37; Medi 2026-10-08 "Can we turn this into just 1 box and we can write the correction, not
   try and separate into so many boxes?"). He writes the fix in his own words; this file reads the obvious shapes into
   the same structured rows the old boxes made (speaker / time / missing / text / add), or says it is not sure so the
   panel asks the cheap AI read (supabase/functions/parse-correction, prompt in scripts/correction_parse_prompt.md).
   Pure: no DOM, loadable in node (tests/test_correction_parse.cjs). Arabic or Arabizi on either side of every shape.
   API: parse(text, ctx) -> { sure: true|false, items: [ {kind, label, payload, target?} ], why }
     ctx = { who: 'Medi'|'Amal', line: the engine's text of the line, t: line start (s) }
   Every item the panel saves keeps the raw text in payload.raw (never lost; a misparse can be re-read later). */
(function (root) {
'use strict';

var AR = /[؀-ۿ]/;
var SPEAKERS = { amal: 'Amal', tutor: 'Amal', teacher: 'Amal', her: 'Amal', she: 'Amal', medi: 'Medi', me: 'Medi', student: 'Medi', mine: 'Medi', i: 'Medi' };
var GRAMMAR = /\b(grammar|verb|gender|plural|tense|conjugat\w*|preposition|pronoun|feminine|masculine|dual|past|present|future|rule|suffix|prefix|ending)\b/i;
var ENGINE = /\b(engine|transcri\w*|recording|heard|wrote|misheard|it wrote|it heard)\b/i;

function clean(s) { return String(s || '').trim().replace(/^[\s"'“”«»‘’:,.;-]+|[\s"'“”«»‘’:,.;!?-]+$/g, ''); }
function words(s) { return String(s || '').split(/[\s.…,،؟?!:;"“”«»()]+/).filter(Boolean); }
function norm(s) {
  return String(s || '').replace(/[ً-ْٰـ]/g, '').replace(/[أإآ]/g, 'ا').replace(/ة/g, 'ه').replace(/ى/g, 'ي')
    .toLowerCase().replace(/[^\wء-ي]+/g, '');
}
function lev(a, b) {
  if (a === b) return 0;
  var m = a.length, n = b.length, d = [], i, j;
  if (!m || !n) return m || n;
  for (i = 0; i <= m; i++) d[i] = [i];
  for (j = 0; j <= n; j++) d[0][j] = j;
  for (i = 1; i <= m; i++) for (j = 1; j <= n; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[m][n];
}
function sim(a, b) { a = norm(a); b = norm(b); if (!a || !b) return 0; return 1 - lev(a, b) / Math.max(a.length, b.length); }
// the word of the line that is (or sounds most like) `w`; null when nothing is close
// "the" prefixes do not count: العشاء ~ عشرة, el-3asha ~ 3asha
function bare(w) { return String(w || '').replace(/^(?:ال|el[- ]?|al[- ]?|il[- ]?)/i, ''); }
function sim2(a, b) { return Math.max(sim(a, b), sim(bare(a), bare(b))); }
// AZ(word) -> its Arabizi (the page's reader) lets "marhaba" find مرحبا on an Arabic line; the line's own word is returned.
var AZ = null;
function inLine(w, line, floor) {
  var best = null, bs = floor == null ? 0.999 : floor;
  words(line).forEach(function (lw) {
    var s = sim2(w, lw);
    if (AZ && AR.test(lw) && !AR.test(w)) { try { s = Math.max(s, sim2(w, AZ(lw))); } catch (e) { /* no reader */ } }
    if (s >= bs) { bs = s; best = lw; }
  });
  return best;
}
function mmss(t) { t = Math.max(0, Math.floor(Number(t) || 0)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); }
function parseTime(s) {
  var m = String(s || '').trim().match(/^(?:(\d+):)?(\d{1,2}):(\d{2})$/);
  if (!m) return null;
  return (+(m[1] || 0)) * 3600 + (+m[2]) * 60 + (+m[3]);
}
function slipKind(text) { return GRAMMAR.test(text) ? 'grammar' : 'vocab'; }
function kindWord(k) { return k === 'grammar' ? 'grammar' : 'wrong word'; }

function speakerItem(who) { return { kind: 'speaker', label: 'This was ' + who, payload: { who: who } }; }
function timeItem(t) { return { kind: 'time', label: 'Time → ' + mmss(t), payload: { t: t } }; }
function missingItem(w) { return { kind: 'missing', label: 'Missing word: ' + w, payload: { heard: w } }; }
function textItem(engine, heard) { return { kind: 'text', label: 'You said ' + heard + ', engine wrote ' + engine, target: { word: engine }, payload: { engine_wrote: engine, heard: heard, from: 'typed' } }; }
function slipItem(said, right, k) {
  return { kind: 'add', label: 'You said ' + said + (right ? ', should be ' + right : '') + ', ' + kindWord(k),
    target: { k: k, said: said }, payload: { k: k, wrong: said, right: right || null } };
}
function noteItem(text) { return { kind: 'note', label: 'Note: ' + text, payload: {} }; }
// PR-22: ctx.parts = the pieces of his joined sentence [{t, line}]; the one named by m:ss (+-1.5 s), else the one holding w
function pieceFor(ctx, w, at) {
  var parts = (ctx && ctx.parts) || [];
  if (!parts.length) return { line: (ctx && ctx.line) || '', t: null };
  var sec = at == null ? null : (typeof at === 'number' ? at : parseTime(String(at)));
  if (sec != null) { var n = parts.filter(function (p) { return Math.abs(p.t - sec) <= 1.5; })[0]; if (n) return n; }
  return parts.filter(function (p) { return p.line.indexOf(w) >= 0; })[0] || parts.filter(function (p) { return inLine(w, p.line, 0.6); })[0] || parts[0];
}

/* ---------- the rule layer ---------- */
function parse(text, ctx) {
  ctx = ctx || {};
  AZ = typeof ctx.toArabizi === 'function' ? ctx.toArabizi : null;
  var raw = String(text || '').trim(), line = ctx.line || '', who = ctx.who || 'Medi', other = who === 'Medi' ? 'Amal' : 'Medi';
  var items = [], unsure = [], m, rest = raw;
  if (!raw) return { sure: false, items: [], why: 'empty' };

  // 1. speaker: "this was Amal", "Amal", "that's me", "not me", "Amal said this", "tutor"
  m = rest.match(/^(?:(?:this|that|it)\s*(?:was|is|'s|=)?\s*|not\s+)?(amal|tutor|teacher|her|she|medi|me|mine|student|i)\b(?:\s*(?:said|says)\s*(?:this|that|it)?)?[.!]?\s*$/i)
    || rest.match(/^(?:wrong\s+)?speaker\s*[:=]?\s*(amal|tutor|teacher|medi|me|student)\b/i);
  if (m) {
    var sp = SPEAKERS[m[1].toLowerCase()];
    if (/^not\s/i.test(rest)) sp = sp === 'Medi' ? 'Amal' : 'Medi';
    items.push(speakerItem(sp)); rest = '';
  }

  // 2. time: "time 2:13", "at 2:13", "2:13", "should be 12:05"
  if (rest) {
    m = rest.match(/^(?:(?:the\s+)?time\s*(?:is|was|should be|=|:|->|→)?\s*|at\s+|should be\s+)?((?:\d+:)?\d{1,2}:\d{2})\s*$/i)
      || rest.match(/\b(?:time|at)\s*(?:is|was|should be|=|:|->|→)?\s*((?:\d+:)?\d{1,2}:\d{2})\b/i);
    if (m && parseTime(m[1]) != null) { items.push(timeItem(parseTime(m[1]))); rest = rest.replace(m[0], ' ').trim(); }
  }

  // 3. missing word: "missing word X", "missing X", "dropped X", "left out X", "add X", "forgot X", "X is missing"
  if (rest) {
    m = rest.match(/^(?:the\s+)?(?:missing|dropped|left\s*out|forgot|add|skipped|it\s+dropped|engine\s+dropped)\s*(?:the\s+)?(?:word\s*)?[:"“]?\s*(.+?)\s*$/i)
      || rest.match(/^[:"“]?\s*(.+?)\s*(?:is|was|got)\s+(?:missing|dropped|left\s*out)\s*$/i);
    if (m && clean(m[1]) && words(clean(m[1])).length <= 3 && !/\bnot\b|should|->|→/.test(m[1])) { items.push(missingItem(clean(m[1]))); rest = ''; }
  }

  // 4. "I said X not Y" / "I said X, not Y" / "not Y, X": the engine wrote Y
  if (rest) {
    m = rest.match(/^(?:i\s+)?said\s+(.+?)\s*,?\s*not\s+(.+?)\s*$/i) || rest.match(/^not\s+(.+?)\s*,\s*(?:i\s+said\s+|it'?s\s+|it\s+was\s+)?(.+?)\s*$/i);
    if (m) {
      var said = clean(/^not/i.test(rest) ? m[2] : m[1]), eng = clean(/^not/i.test(rest) ? m[1] : m[2]);
      var hit = inLine(eng, line, 0.6);
      if (said && hit) { items.push(textItem(hit, said)); rest = ''; }
      else if (said && eng) { unsure.push('«' + eng + '» is not on the line'); }
    }
  }

  // 5. "X should be Y" / "X -> Y" / "X → Y" / "X => Y" / "X instead of Y" (+ "wrong word" / "grammar")
  if (rest) {
    m = rest.match(/^(.+?)\s*(?:should\s+(?:be|have been)|->|→|=>|→|is\s+wrong,?\s*(?:it'?s|should be)?|correct(?:ion)?\s*(?:is|:))\s*(.+?)\s*$/i);
    if (m) {
      var a = clean(m[1]), b = clean(m[2]).replace(/(?:\s*[,(]?\s*(?:wrong word|word|grammar|vocab|verb|gender|plural|tense|ending|form|mistake|slip)\s*\)?)+\s*$/i, '');
      a = a.replace(/^(?:(?:the\s+)?(?:engine|it|recording|transcript)\s+(?:wrote|heard|has|says|said|got)|i\s+said|my|the word|he said)\s+/i, '');
      if (a && b) {
        if (ENGINE.test(rest)) { var h2 = inLine(a, line, 0.6); if (h2) { items.push(textItem(h2, b)); rest = ''; } else unsure.push('«' + a + '» is not on the line'); }
        else if (who === 'Medi') { items.push(slipItem(inLine(a, line, 0.75) || a, b, slipKind(rest))); rest = ''; }
        else unsure.push("a slip on the tutor's line");
      }
    }
  }

  // 6. "engine wrote X, I said Y" / "it heard X, I said Y" / "X was Y"
  if (rest) {
    m = rest.match(/^(?:the\s+)?(?:engine|it|recording|transcript)\s+(?:wrote|heard|has|says|said|got)\s+(.+?)\s*[,;:]\s*(?:i\s+said|it\s+was|it'?s|should be|i\s+meant)\s+(.+?)\s*$/i);
    if (m) {
      var e2 = inLine(clean(m[1]), line, 0.6);
      if (e2 && clean(m[2])) { items.push(textItem(e2, clean(m[2]))); rest = ''; }
      else unsure.push('«' + clean(m[1]) + '» is not on the line');
    }
  }

  // 7. "I said X" alone: the engine's word is the one on the line that sounds most like X
  if (rest) {
    m = rest.match(/^(?:i\s+)?(?:said|say|meant|was\s+saying)\s+(.+?)\s*$/i);
    if (m && words(clean(m[1])).length <= 3) {
      var s3 = clean(m[1]), e3 = inLine(s3, line, 0.5);
      if (e3 && norm(e3) !== norm(s3)) { items.push(textItem(e3, s3)); rest = ''; }
      else unsure.push('which word of the line «' + s3 + '» replaces');
    }
  }

  // 8. "wrong word: X" / "mistake: X" / "X is wrong" / "grammar: X"
  if (rest && who === 'Medi') {
    m = rest.match(/^(?:wrong\s+word|mistake|slip|grammar|error)\s*[:=]?\s*(.+?)\s*$/i) || rest.match(/^(.+?)\s+(?:is|was)\s+(?:wrong|a\s+mistake|a\s+slip)\s*$/i);
    if (m && clean(m[1]) && words(clean(m[1])).length <= 4) { items.push(slipItem(inLine(clean(m[1]), line, 0.75) || clean(m[1]), null, slipKind(rest))); rest = ''; }
  }

  var sure = items.length > 0 && !rest && !unsure.length;
  if (!items.length) items.push(noteItem(raw));
  items.forEach(function (it) { it.payload = Object.assign({}, it.payload, { raw: raw }); });
  return { sure: sure, items: items, why: unsure.length ? unsure.join('; ') : (rest && items.length ? 'left over: «' + rest + '»' : (sure ? 'rule' : 'no shape')) };
}

// The AI's answer (edge function parse-correction) -> the same item shape, checked against the line; anything odd is a note.
function fromAI(ans, text, ctx) {
  ctx = ctx || {};
  AZ = typeof ctx.toArabizi === 'function' ? ctx.toArabizi : null;
  var raw = String(text || '').trim(), out = [];
  ((ans && ans.items) || []).forEach(function (a) {
    if (!a || typeof a !== 'object') return;
    var it = null;
    if (a.kind === 'speaker' && (a.who === 'Amal' || a.who === 'Medi')) it = speakerItem(a.who);
    else if (a.kind === 'time' && typeof a.t === 'number' && a.t >= 0) it = timeItem(a.t);
    else if (a.kind === 'time' && parseTime(a.t) != null) it = timeItem(parseTime(a.t));
    else if (a.kind === 'missing' && clean(a.word)) it = missingItem(clean(a.word));
    else if (a.kind === 'text' && clean(a.engine_wrote) && clean(a.heard)) {
      // PR-22: "at" names the piece of his split sentence it changes; else the piece that holds the words
      var pc = pieceFor(ctx, clean(a.engine_wrote), a.at), ew = clean(a.engine_wrote);
      var h = pc && pc.line.indexOf(ew) >= 0 ? ew : (ew.split(/\s+/).length === 1 && pc ? inLine(ew, pc.line, 0.6) : null);
      if (h) { it = textItem(h, clean(a.heard)); if (pc.t != null) it.payload.at = pc.t; }
    }
    else if (a.kind === 'credit' && clean(a.word) && (ctx.who || 'Medi') === 'Medi') {      // WS-29: "should count"
      var cw = inLine(clean(a.word), ctx.line || '', 0.6) || clean(a.word);
      it = { kind: 'text', label: 'Count ' + cw + ' as right', target: { word: cw }, payload: { engine_wrote: cw, heard: cw, credit: 'independent' } };
    }
    else if (a.kind === 'not-use' && clean(a.said)) { it = noteItem(raw); it.label = 'Not a use: ' + clean(a.said) + ' (read within the hour)'; }
    else if (a.kind === 'add' && clean(a.said) && (ctx.who || 'Medi') === 'Medi') it = slipItem(clean(a.said), clean(a.right) || null, a.k === 'grammar' ? 'grammar' : 'vocab');
    if (it) { it.payload = Object.assign({}, it.payload, { raw: raw, from: 'ai' }); it.by = 'ai'; out.push(it); }
  });
  if (!out.length) { var n = noteItem(raw); n.payload = { raw: raw }; out.push(n); }
  return out;
}

var api = { parse: parse, fromAI: fromAI, pieceFor: pieceFor, sim: sim, inLine: inLine, parseTime: parseTime, mmss: mmss, slipKind: slipKind, words: words, AR: AR };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
else root.AneesCorrectionParse = api;
})(typeof window !== 'undefined' ? window : this);
