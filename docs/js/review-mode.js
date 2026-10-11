/* Fast review mode on the Lessons page transcript (PG-50; Medi 2026-10-10 "It takes a lot of time to review in its
   current state, its gonna take longer in this metod" · "Is there anyway we can simplify this so that it doesnt take as
   much time for amal and i").
   A "Review" button on a lesson's transcript opens it: the student's lines that hold Arabic, one at a time, in the order
   of docs/data/review-pick/<date>.json (scripts/review_picker.py): tier 1 unsure, tier 2 changed by the second
   listen (2 of 3 runs agree), tier 3 confident. "Unsure only" (= tier 1) is ON by default and stops at an end card that
   offers tiers 2 + 3 together for the grade book (council 2026-10-10: the
   answer key must not inherit the pipeline's confident errors). Progress "37 of 104", a running timer, the line's clip
   plays at once (its sentence clip, else the lesson audio from 1 s before the line), Arabizi big / Arabic small / the
   English (PG-40) / the chips.
   Keys (and big buttons, no free text required):
     1 heard right · 2 wrong word (one box: the word he said) · 3 a mistake (vocab / grammar proposed by the robot; f flips)
     4 not a mistake (one of the four reasons, keys 1-4) · space replay · enter / → next · ← back · u undo · esc close
   Blind block: the first 50 lines shown carry no chips (the answer key's anchoring test, protocol §2.2).
   Re-listen (exam lessons, protocol §4): 15 lines he already answered here, picked by the date, shown again without his
   earlier answer.
   Rows: the SAME queue and table as docs/js/transcript-corrections.js (transcript_corrections, append-only, undo = a new
   row), same kinds: key 2 = text, key 3 = add, key 4 = not-slip; every row carries payload.review_mode "fast",
   payload.secs, payload.blind. Key 1 and every re-listen answer write a TRACE row (kind rule-answer, proposal
   "review:fast" / "review:relisten", answer "one"): the table already takes it, scripts/medi_corrections.py keeps it in
   the mirror and applies it nowhere (review_trace), so the grade book sees which lines he checked and nothing is
   counted twice. Pure core (no DOM) exported for tests/test_review_mode.cjs. */
(function (root) {
'use strict';

var BLIND_N = 50, RELISTEN_N = 15, SECS_PER_LINE = 8;
var REASONS4 = [['not-correcting', "She wasn't correcting me"], ['fixed-first', 'I fixed it first'],
  ['both-fine', 'She said both are fine'], ['asking', 'I was asking']];
var TRACE = { fast: 'review:fast', relisten: 'review:relisten' };

/* ---------- pure core (tested) ---------- */
function hash(s) { var h = 2166136261; s = String(s); for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16).padStart(8, '0'); }
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
  for (i = 1; i <= m; i++) for (j = 1; j <= n; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[m][n];
}
function sim(a, b) { a = norm(a); b = norm(b); if (!a || !b) return 0; return 1 - lev(a, b) / Math.max(a.length, b.length); }
// The line's words he can mean when he types the word he said: most alike first (his Arabizi is read against the
// Arabizi of each Arabic word when a reader is given); the line's order breaks a tie.
function targets(typed, line, toArabizi) {
  var AR = /[؀-ۿ]/, FILL = /^(uh+|um+|mm+|hmm+|ok|okay|yeah|yes|no|and|the|a|i|so|like|oh|ah)$/i;
  var all = words(line).filter(function (w) { return AR.test(w) || /[a-z0-9]/i.test(w); });
  // an Arabic line: its Arabic words and his Arabizi (a digit 2 3 5 6 7 8 9) only; never an English filler
  var ws = all.some(function (w) { return AR.test(w); }) ? all.filter(function (w) { return AR.test(w) || /[235-9]/.test(w); }) : all.filter(function (w) { return !FILL.test(w); });
  if (!ws.length) ws = all;
  return ws.map(function (w, i) {
    var s = sim(typed, w);
    if (toArabizi && AR.test(w) && !AR.test(typed)) { try { s = Math.max(s, sim(typed, toArabizi(w))); } catch (e) { /* no reader */ } }
    return { w: w, i: i, s: s };
  }).sort(function (a, b) { return b.s - a.s || a.i - b.i; }).map(function (x) { return x.w; })
    .filter(function (w, i, a) { return a.indexOf(w) === i; });
}
// The order he sees: unsure first then confident (the picker's `order`); unsure-only stops after the unsure ones.
function queue(pick, opts) {
  opts = opts || {};
  var L = ((pick && pick.lines) || []).slice().sort(function (a, b) { return a.order - b.order; });
  if (opts.relisten) return relistenPick(pick, opts.answered || {}, opts.n);
  return opts.unsureOnly === false ? L : L.filter(function (x) { return x.unsure; });
}
function keyOf(t) { return Number(t).toFixed(2); }
// Re-listen (protocol §4): up to 15 lines he already answered in fast mode, picked by a hash of the date and the line
// time (stable for a lesson), shown in time order.
function relistenPick(pick, answered, n) {
  var date = (pick && pick.date) || '';
  return ((pick && pick.lines) || []).filter(function (x) { return answered[keyOf(x.t)]; })
    .map(function (x) { return { x: x, h: hash(date + '|' + keyOf(x.t)) }; })
    .sort(function (a, b) { return a.h < b.h ? -1 : a.h > b.h ? 1 : 0; }).slice(0, n || RELISTEN_N)
    .map(function (o) { return o.x; }).sort(function (a, b) { return a.t - b.t; });
}
function isBlind(item) { return !!item && (item.blind != null ? !!item.blind : item.order <= BLIND_N); }
// His answers already saved (server + this device): fast-mode rows not undone, by line time
function answeredFrom(rows, pick) {
  var out = {};
  (rows || []).forEach(function (r) {
    var p = r.payload || {};
    if (p.review_mode !== 'fast' || p.relisten) return;
    var it = ((pick && pick.lines) || []).filter(function (x) { return Number(r.turn_t) >= x.t - 0.6 && Number(r.turn_t) <= x.end + 0.6; })[0];
    if (it) out[keyOf(it.t)] = { key: p.key || null, verdict: p.verdict || r.kind, id: r.id };
  });
  return out;
}
function estimateMin(items) {
  var s = (items || []).reduce(function (a, x) { return a + SECS_PER_LINE + Math.max(0, (x.end - x.t) + 1.8); }, 0);
  return Math.max(1, Math.round(s / 60));
}
// One row for one answer. ans = {key: 1|2|3|4, heard?, engine_wrote?, k?, said?, right?, reason?, chip?, part?, flipped?}
// ctx = {date, item, line, end, who, secs, mode: 'fast'|'relisten', earlier?, session?, now?, uuid?}
function rowFor(ans, ctx) {
  var d = ctx.now ? new Date(ctx.now) : new Date();
  var id = ctx.uuid ? ctx.uuid() : 'rv-' + d.getTime().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  var part = ans.part || { t: ctx.item.t, end: ctx.end != null ? ctx.end : ctx.item.end, text: ctx.line };
  var base = { id: id, lesson_date: ctx.date, turn_t: Math.round(Number(part.t) * 100) / 100, turn_who: ctx.who || 'Medi',
    note: null, ts: d.toISOString(), tz_offset_min: -d.getTimezoneOffset() };
  var meta = { review_mode: 'fast', secs: Math.round((ctx.secs || 0) * 10) / 10, blind: isBlind(ctx.item), key: ans.key, order: ctx.item.order,
    turn_end: part.end != null ? part.end : null, line: String(part.text || ctx.line || '').slice(0, 400) };
  if (ctx.session) { meta.session = ctx.session.id; meta.reviewed = ctx.session.reviewed; meta.session_secs = Math.round(ctx.session.secs || 0); }
  var change = null;
  if (ans.key === 2 && ans.heard && ans.engine_wrote)
    change = { kind: 'text', target: { word: ans.engine_wrote }, payload: { engine_wrote: ans.engine_wrote, heard: ans.heard, from: 'typed', verdict: 'wrong-word' } };
  else if (ans.key === 3 && ans.said)
    change = { kind: 'add', target: { k: ans.k === 'grammar' ? 'grammar' : 'vocab', said: ans.said },
      payload: { k: ans.k === 'grammar' ? 'grammar' : 'vocab', wrong: ans.said, right: ans.right || null, verdict: 'mistake', proposed: ans.proposed || null, flipped: !!ans.flipped } };
  else if (ans.key === 4 && ans.reason && ans.chip)
    change = { kind: 'not-slip', target: ans.chip, payload: { reason: ans.reason, signal: ans.chip.signal || null, verdict: 'not-a-mistake' } };
  if (ctx.mode === 'relisten') {
    // a re-listen answer never changes the lesson a second time: one trace row with what he would have written
    return Object.assign(base, { kind: 'rule-answer', target: null, proposal: TRACE.relisten, answer: 'one',
      payload: Object.assign(meta, { relisten: true, verdict: change ? change.payload.verdict : 'right', would: change,
        earlier: ctx.earlier || null, same: ctx.earlier ? ctx.earlier.key === ans.key : null }) });
  }
  if (!change)
    return Object.assign(base, { kind: 'rule-answer', target: null, proposal: TRACE.fast, answer: 'one',
      payload: Object.assign(meta, { verdict: 'right' }, ans.key === 4 ? { no_chip: true } : {}) });
  return Object.assign(base, { kind: change.kind, target: change.target, payload: Object.assign(meta, change.payload) });
}
function undoRowFor(row, now, uuid) {
  var d = now ? new Date(now) : new Date();
  return { id: uuid ? uuid() : 'rv-u-' + d.getTime().toString(36) + Math.random().toString(36).slice(2, 8), lesson_date: row.lesson_date,
    turn_t: row.turn_t, turn_who: row.turn_who, kind: 'undo', undoes: row.id, ts: d.toISOString(), tz_offset_min: -d.getTimezoneOffset() };
}
// The ✗ chips of a line he can call 'not a mistake' (the target shape of transcript-corrections chipActions)
function slipTargets(chips) {
  return (chips || []).filter(function (c) { return c.s === 'wrong' && (c.k === 'vocab' || c.k === 'grammar'); }).map(function (c) {
    return { chip: c.id, src: c.src || null, k: c.k, rule: c.rule || null, said: c.said || null, wrong: c.said || null, right: c.right || null,
      signal: c.signal || null, sig: c.sig || null, word: c.ar || null, name: c.name || null, amal_ruled: !!c.amal_ruled };
  });
}
// Key 3: the robot's proposal (picker's propose; else the first ✗/grammar chip; else vocab + the first word)
function proposal(item, chips, line) {
  if (item && item.propose && item.propose.said) return { k: item.propose.k === 'grammar' ? 'grammar' : 'vocab', said: item.propose.said, right: item.propose.right || null, from: item.propose.from };
  var c = (chips || []).filter(function (c) { return c.k === 'vocab' || c.k === 'grammar'; })[0];
  if (c) return { k: c.k, said: c.said || c.ar, right: c.right || null, from: 'chip' };
  return { k: 'vocab', said: words(line).filter(function (w) { return /[؀-ۿ]/.test(w); })[0] || words(line)[0] || '', right: null, from: 'line' };
}

/* ---------- session state (pure: the DOM layer only draws it) ---------- */
// create({pick, date, rows, unsureOnly}) -> state; press(state, ev, env) -> {rows: [...to enqueue], panel?, done?}
function create(o) {
  var s = { date: o.date, pick: o.pick, unsureOnly: o.unsureOnly !== false, mode: o.relisten ? 'relisten' : 'fast',
    answered: answeredFrom(o.rows || [], o.pick), log: [], pos: 0, reviewed: 0, secs: 0, shownAt: o.now || 0,
    session: { id: o.sessionId || 'rs-' + hash(String(o.now || Date.now()) + Math.random()), reviewed: 0, secs: 0 } };
  s.items = queue(o.pick, { unsureOnly: s.unsureOnly, relisten: s.mode === 'relisten', answered: s.answered });
  // resume: start at the first line he has not answered (re-listen starts at the top)
  if (s.mode === 'fast') { var k = 0; while (k < s.items.length && s.answered[keyOf(s.items[k].t)]) k++; s.pos = k; }
  return s;
}
function current(s) { return s.items[s.pos] || null; }
function atEnd(s) { return s.pos >= s.items.length; }
function go(s, d, now) { s.pos = Math.max(0, Math.min(s.items.length, s.pos + d)); s.shownAt = now; }
// answer the current line. ans as rowFor; env = {now, uuid, line, end, who, part}
function answer(s, ans, env) {
  var it = current(s);
  if (!it) return [];
  var secs = Math.min(600, Math.max(0, ((env.now || 0) - (s.shownAt || 0)) / 1000));
  s.secs += secs; s.reviewed += 1; s.session.reviewed = s.reviewed; s.session.secs = s.secs;
  var earlier = s.mode === 'relisten' ? (s.relistenEarlier || s.answered)[keyOf(it.t)] || null : null;
  var row = rowFor(ans, { date: s.date, item: it, line: env.line, end: env.end, who: env.who, secs: secs, mode: s.mode, earlier: earlier,
    session: s.session, now: env.now, uuid: env.uuid });
  s.log.push({ pos: s.pos, row: row, key: ans.key, prev: s.answered[keyOf(it.t)] || null, secs: secs });
  if (s.mode === 'fast') s.answered[keyOf(it.t)] = { key: ans.key, verdict: row.payload.verdict, id: row.id };
  go(s, 1, env.now);
  return [row];
}
// u: take the last answer of this session back (an undo row, never a delete) and show that line again
function undoLast(s, env) {
  var last = s.log.pop();
  if (!last) return [];
  s.reviewed = Math.max(0, s.reviewed - 1); s.secs = Math.max(0, s.secs - last.secs);
  s.session.reviewed = s.reviewed; s.session.secs = s.secs;
  var it = s.items[last.pos];
  if (s.mode === 'fast' && it) { if (last.prev) s.answered[keyOf(it.t)] = last.prev; else delete s.answered[keyOf(it.t)]; }
  s.pos = last.pos; s.shownAt = env.now;
  return [undoRowFor(last.row, env.now, env.uuid)];
}
function setUnsureOnly(s, on, now) {
  var it = current(s);
  s.unsureOnly = !!on;
  s.items = queue(s.pick, { unsureOnly: s.unsureOnly });
  var k = it ? s.items.indexOf(it) : -1;
  if (k < 0) { k = 0; while (k < s.items.length && s.answered[keyOf(s.items[k].t)]) k++; }
  s.pos = k; s.shownAt = now;
}
function startRelisten(s, now) {
  s.mode = 'relisten'; s.relistenEarlier = Object.assign({}, s.answered);
  s.items = relistenPick(s.pick, s.answered); s.pos = 0; s.shownAt = now;
}
function progress(s) {
  return { n: Math.min(s.pos + 1, s.items.length), of: s.items.length, text: Math.min(s.pos + 1, s.items.length) + ' of ' + s.items.length };
}
function endCard(s) {
  var p = s.pick || {}, all = (p.lines || []);
  if (s.mode === 'relisten') return { kind: 'relisten-done', text: 'Re-listen done (' + s.items.length + ').' };
  if (s.unsureOnly) {
    var conf = all.filter(function (x) { return !x.unsure; });
    if (conf.length) return { kind: 'unsure-done', n: s.items.length, m: conf.length, min: estimateMin(conf),
      text: 'Unsure lines done (' + s.items.length + '). For the grade book: ' + conf.length + ' more, about ' + estimateMin(conf) + ' min' };
  }
  return { kind: 'all-done', text: 'All ' + s.items.length + ' lines done.' };
}

var api = { BLIND_N: BLIND_N, RELISTEN_N: RELISTEN_N, REASONS4: REASONS4, TRACE: TRACE, hash: hash, targets: targets, queue: queue,
  relistenPick: relistenPick, isBlind: isBlind, answeredFrom: answeredFrom, estimateMin: estimateMin, rowFor: rowFor, undoRowFor: undoRowFor,
  slipTargets: slipTargets, proposal: proposal, create: create, current: current, atEnd: atEnd, go: go, answer: answer, undoLast: undoLast,
  setUnsureOnly: setUnsureOnly, startRelisten: startRelisten, progress: progress, endCard: endCard, keyOf: keyOf };
if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }

/* ---------- the page (DOM) ---------- */
var doc = root.document, H = null, S = null, X = null, BOX = null, PANEL = null, TIMER = null, STOP_AT = null, OPENED = 0;
var DRY = /[?&]review_dry=1/.test(root.location ? root.location.search : '');   // dry run: rows go to window.__reviewRows only
function el(tag, cls, text) { var n = doc.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
function btn(cls, text, on, title) {
  var b = el('button', 'rv-btn ' + (cls || ''), text); b.type = 'button'; if (title) b.title = title;
  b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); on(b); }); return b;
}
function now() { return Date.now(); }
function uuid() { return (root.crypto && crypto.randomUUID) ? crypto.randomUUID() : 'rv-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10); }
function AC() { return root.AneesCorrections || {}; }
function send(rows) {
  rows.forEach(function (r) {
    if (DRY || root.ANEES_REVIEW_DRY) { (root.__reviewRows = root.__reviewRows || []).push(r); return; }
    if (AC().enqueueRow) AC().enqueueRow(r);
  });
  try { localStorage.setItem('anees-review-' + S.date, JSON.stringify({ reviewed: S.reviewed, secs: Math.round(S.secs), at: new Date().toISOString() })); } catch (e) { /* per-device note only */ }
}
function az(s) { var t = H.toArabizi(); return t && /[؀-ۿ]/.test(s || '') ? t(s).text : s; }
// the item's pieces as one display line (the page's joined sentence)
function lineOf(it) {
  var T = (X.turns || []), tm = X.tmarks || {}, parts = (it.parts || [it.i]).map(function (i) { return Object.assign({ _i: i }, T[i] || {}); });
  return { parts: parts, text: parts.map(function (p) { return p.text || ''; }).join(' '), en: parts.map(function (p) { return p.en; }).filter(Boolean).join(' '),
    engine: parts.some(function (p) { return p.engine; }) ? parts.map(function (p) { return p.engine || p.text; }).join(' ') : null,
    chips: parts.reduce(function (a, p) { return a.concat(((tm[String(p._i)] || {}).c) || []); }, []),
    end: parts.length ? (parts[parts.length - 1].end != null ? parts[parts.length - 1].end : parts[parts.length - 1].t) : it.end };
}
function clipOf(it) {
  var v = (X.vocab_errors || []).concat(X.vocab_correct || []).filter(function (v) { return v.clip && v.t >= it.t - 1 && v.t <= it.end + 1; })[0];
  return v ? v.clip : null;
}
function playLine() {
  var it = current(S); if (!it) return;
  var c = clipOf(it), label = 'Review · ' + H.prettyDate(S.date) + ' · Student ' + H.mmss(it.t);
  if (c) { STOP_AT = null; H.play(c, 0, label); }
  else { STOP_AT = it.end + 0.8; H.play(H.lessonAudio(S.date, 'Medi'), Math.max(0, it.t - 1), label); }
}
function stopAudio() { var a = doc.getElementById('ls-audio'); if (a) a.pause(); STOP_AT = null; }
function clock(ms) { var t = Math.max(0, Math.floor(ms / 1000)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); }

function draw(autoplay) {
  PANEL = null;
  BOX.textContent = '';
  var head = el('div', 'rv-head');
  var title = el('div', 'rv-title', 'Review · Student\'s lines · ' + H.prettyDate(S.date) + (S.mode === 'relisten' ? ' · Re-listen' : ''));
  head.appendChild(title);
  var pg = progress(S), bar = el('div', 'rv-progress'), fill = el('i');
  fill.style.width = (S.items.length ? Math.round(100 * Math.min(S.pos, S.items.length) / S.items.length) : 100) + '%';
  bar.appendChild(fill);
  var stat = el('div', 'rv-stat');
  stat.appendChild(el('b', 'rv-count', atEnd(S) ? S.items.length + ' of ' + S.items.length : pg.text));
  var tm = el('span', 'rv-timer', clock(now() - OPENED)); tm.title = 'Time in review mode (the seconds per line go with every row)';
  stat.appendChild(tm);
  var tg = el('label', 'rv-toggle'), cb = el('input'); cb.type = 'checkbox'; cb.checked = S.unsureOnly; cb.disabled = S.mode === 'relisten';
  cb.addEventListener('change', function () { setUnsureOnly(S, cb.checked, now()); draw(true); });
  tg.appendChild(cb); tg.appendChild(doc.createTextNode(' Unsure only (' + (S.pick.unsure_n || 0) + ' of ' + (S.pick.all || 0) + ')'));
  stat.appendChild(tg);
  var hasAns = Object.keys(S.answered).length;
  stat.appendChild(btn('rv-small', S.mode === 'relisten' ? 'Back to review' : 'Re-listen (' + Math.min(RELISTEN_N, hasAns) + ')', function () {
    if (S.mode === 'relisten') { S = create({ pick: S.pick, date: S.date, rows: AC().rowsFor ? AC().rowsFor(S.date) : [], now: now(), sessionId: S.session.id }); }
    else { if (!hasAns) return; startRelisten(S, now()); }
    draw(true);
  }, 'Exam lessons: ' + RELISTEN_N + ' lines you already answered, picked by the date, shown again without your earlier answer'));
  stat.appendChild(btn('rv-small rv-close', 'Close', close, 'Close review mode (Esc)'));
  head.appendChild(stat); head.appendChild(bar);
  BOX.appendChild(head);
  var it = current(S);
  if (!it) { drawEnd(); return; }
  var L = lineOf(it), blind = isBlind(it);
  var card = el('div', 'rv-card');
  var meta = el('div', 'rv-meta');
  meta.appendChild(el('span', 'ls-who rv-who', 'Student'));
  meta.appendChild(el('span', 'rv-time', H.mmss(it.t)));
  if (S.mode === 'fast' && S.answered[keyOf(it.t)]) meta.appendChild(el('span', 'rv-yours', '✎ you: ' + verdictWords(S.answered[keyOf(it.t)])));
  card.appendChild(meta);
  card.appendChild(H.speech('rv-line ls-turntext', null, L.text));
  if (L.en) card.appendChild(el('div', 'ls-line-en rv-en', L.en));
  if (L.engine) card.appendChild(el('div', 'ab-mini rv-engine', 'Recording engine wrote: ' + L.engine));
  if (blind) card.appendChild(el('div', 'rv-blind', 'No chips on the first ' + BLIND_N + ' lines: you judge them before you see the robot\'s marks (the answer key\'s anchoring test).'));
  else if (L.chips.length) {
    var cw = el('div', 'tm-chips rv-chips');
    L.chips.forEach(function (c) { if (!c.hide) cw.appendChild(H.chip(X, c)); });
    card.appendChild(cw);
  }
  if (S.mode === 'fast' && (it.why || []).length && !blind) card.appendChild(el('div', 'ab-mini rv-why', 'Why this line: ' + it.why.join(' · ')));
  BOX.appendChild(card);
  var keys = el('div', 'rv-keys');
  keys.appendChild(btn('rv-key rv-k1', '1 · Heard right', function () { key1(); }));
  keys.appendChild(btn('rv-key rv-k2', '2 · Wrong word', function () { key2(); }));
  keys.appendChild(btn('rv-key rv-k3', '3 · Mistake', function () { key3(); }));
  keys.appendChild(btn('rv-key rv-k4', '4 · Not a mistake', function () { key4(); }));
  BOX.appendChild(keys);
  var nav = el('div', 'rv-nav');
  nav.appendChild(btn('rv-small', '← Back', function () { go(S, -1, now()); draw(true); }));
  nav.appendChild(btn('rv-small', '␣ Replay', playLine));
  nav.appendChild(btn('rv-small', 'u · Undo', doUndo, 'Take your last answer back (a new undo row, never a delete)'));
  nav.appendChild(btn('rv-small', 'Next →', function () { go(S, 1, now()); draw(true); }, 'Next line without answering (Enter / →)'));
  nav.appendChild(el('span', 'ab-mini rv-hint', 'Keys: 1 2 3 4 · space replay · enter / → next · ← back · u undo · esc close'));
  BOX.appendChild(nav);
  if (autoplay) playLine();
}
function verdictWords(a) { return { right: 'heard right', 'wrong-word': 'wrong word', mistake: 'a mistake', 'not-a-mistake': 'not a mistake' }[a.verdict] || a.verdict || 'answered'; }
function drawEnd() {
  stopAudio();
  var e = endCard(S), card = el('div', 'rv-card rv-end');
  card.appendChild(el('p', 'rv-endtext', e.text));
  card.appendChild(el('p', 'ab-mini', 'You answered ' + S.reviewed + ' line' + (S.reviewed === 1 ? '' : 's') + ' in ' + clock(S.secs * 1000) + ' this time.'));
  var row = el('div', 'rv-keys');
  if (e.kind === 'unsure-done') {
    row.appendChild(btn('rv-key rv-primary', 'Continue (Enter)', function () { setUnsureOnly(S, false, now()); draw(true); }));
    row.appendChild(btn('rv-key', 'Stop here', close));
  } else row.appendChild(btn('rv-key rv-primary', 'Close', close));
  card.appendChild(row);
  BOX.appendChild(card);
}
function env(extra) {
  var it = current(S), L = lineOf(it);
  return Object.assign({ now: now(), uuid: uuid, line: L.text, end: L.end, who: 'Medi' }, extra || {});
}
function commit(ans, extra) { send(answer(S, ans, env(extra))); draw(true); }
function key1() { if (current(S)) commit({ key: 1 }); }
function partFor(L, w) { return L.parts.filter(function (p) { return (p.text || '').indexOf(w) >= 0; })[0] || L.parts[0]; }
function asPart(p) { return { t: p.t, end: p.end, text: p.text }; }
function panel(cls) { if (PANEL) PANEL.remove(); PANEL = el('div', 'rv-panel ' + cls); BOX.querySelector('.rv-card').appendChild(PANEL); return PANEL; }
function key2() {
  var it = current(S); if (!it) return;
  var L = lineOf(it), P = panel('rv-p2'), opts = [], k = 0;
  P.appendChild(el('div', 'rv-q', 'The word you said (Arabizi or Arabic)'));
  var inp = el('input'); inp.type = 'text'; inp.setAttribute('dir', 'auto'); inp.setAttribute('aria-label', 'The word you said');
  var rep = el('div', 'ab-mini rv-rep');
  function paint() { rep.textContent = opts.length ? 'Replaces «' + az(opts[k]) + '»' + (/[؀-ۿ]/.test(opts[k]) ? ' (' + opts[k] + ')' : '') + (opts.length > 1 ? ' · Tab: another word' : '') : 'Type the word you said'; }
  inp.addEventListener('input', function () { opts = targets(inp.value.trim(), L.text, H.toArabizi() ? function (w) { return H.toArabizi()(w).text; } : null); k = 0; paint(); });
  inp.addEventListener('keydown', function (e) {
    e.stopPropagation();
    if (e.key === 'Tab' && opts.length) { e.preventDefault(); k = (k + 1) % opts.length; paint(); }
    else if (e.key === 'Enter') { e.preventDefault(); save(); }
    else if (e.key === 'Escape') { e.preventDefault(); PANEL.remove(); PANEL = null; }
  });
  function save() {
    var heard = inp.value.trim(); if (!heard || !opts.length) { inp.focus(); return; }
    var p = partFor(L, opts[k]);
    commit({ key: 2, heard: heard, engine_wrote: opts[k], part: asPart(p) }, { end: p.end });
  }
  P.appendChild(inp); P.appendChild(rep);
  var r = el('div', 'rv-row'); r.appendChild(btn('rv-key rv-primary', 'Save (Enter)', save)); r.appendChild(btn('rv-small', 'Cancel (Esc)', function () { PANEL.remove(); PANEL = null; }));
  P.appendChild(r); paint(); inp.focus();
}
function key3() {
  var it = current(S); if (!it) return;
  var L = lineOf(it), pr = proposal(it, L.chips, L.text), k = pr.k, flipped = false, P = panel('rv-p3');
  var ws = [pr.said].concat(words(L.text).filter(function (w) { return /[؀-ۿ]/.test(w) && w !== pr.said; })), wi = 0;
  var lab = el('div', 'rv-q'), why = el('div', 'ab-mini');
  function paint() {
    lab.textContent = 'A mistake: «' + az(ws[wi]) + '»' + (/[؀-ۿ]/.test(ws[wi]) ? ' (' + ws[wi] + ')' : '') + ' · ' + (k === 'grammar' ? 'grammar' : 'wrong word');
    why.textContent = (flipped ? 'You flipped it.' : 'The robot\'s guess (' + ({ readers: 'from the readers\' rows', chip: 'from the chips', line: 'from the line' }[pr.from] || pr.from) + ').') + ' f: flip vocab / grammar · Tab: another word · Enter: save';
  }
  function flip() { k = k === 'grammar' ? 'vocab' : 'grammar'; flipped = !flipped; paint(); }
  function save() { var p = partFor(L, ws[wi]); commit({ key: 3, said: ws[wi], k: k, right: wi === 0 ? pr.right : null, proposed: pr.k, flipped: flipped, part: asPart(p) }, { end: p.end }); }
  PANEL.handle = function (e) {
    if (e.key === 'f' || e.key === 'F' || e.key === '3') { flip(); return true; }
    if (e.key === 'Tab') { wi = (wi + 1) % ws.length; paint(); return true; }
    if (e.key === 'Enter') { save(); return true; }
    return false;
  };
  P.appendChild(lab); P.appendChild(why);
  var r = el('div', 'rv-row');
  r.appendChild(btn('rv-key rv-primary', 'Save (Enter)', save)); r.appendChild(btn('rv-key', 'Flip vocab / grammar (f)', flip)); r.appendChild(btn('rv-small', 'Cancel (Esc)', function () { PANEL.remove(); PANEL = null; }));
  P.appendChild(r); paint();
}
function key4() {
  var it = current(S); if (!it) return;
  var L = lineOf(it), T = slipTargets(L.chips);
  if (!T.length) { commit({ key: 4 }); return; }                     // no ✗ on the line: nothing to take back, counted as heard right
  var P = panel('rv-p4'), ci = 0;
  var lab = el('div', 'rv-q');
  function paint() { lab.textContent = 'Not a mistake: «' + az(T[ci].word || T[ci].said || '') + '» · why?' + (T.length > 1 ? ' (Tab: the other ✗)' : ''); }
  P.appendChild(lab);
  var r = el('div', 'rv-row');
  REASONS4.forEach(function (q, n) { r.appendChild(btn('rv-key', (n + 1) + ' · ' + q[1], function () { pick(n); })); });
  function pick(n) { var c = T[ci], p = L.parts.filter(function (x) { return (((X.tmarks || {})[String(x._i)] || {}).c || []).some(function (y) { return y.id === c.chip; }); })[0] || L.parts[0]; commit({ key: 4, reason: REASONS4[n][0], chip: c, part: asPart(p) }, { end: p.end }); }
  PANEL.handle = function (e) {
    if (/^[1-4]$/.test(e.key)) { pick(+e.key - 1); return true; }
    if (e.key === 'Tab') { ci = (ci + 1) % T.length; paint(); return true; }
    return false;
  };
  r.appendChild(btn('rv-small', 'Cancel (Esc)', function () { PANEL.remove(); PANEL = null; }));
  P.appendChild(r); paint();
}
function doUndo() { var rows = undoLast(S, { now: now(), uuid: uuid }); if (rows.length) { send(rows); draw(true); } }
function onKey(e) {
  if (!S || !BOX || BOX.hidden) return;
  if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) && e.target.type !== 'checkbox') return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === 'Escape') { e.preventDefault(); if (PANEL) { PANEL.remove(); PANEL = null; } else close(); return; }
  if (PANEL && PANEL.handle) { if (PANEL.handle(e)) { e.preventDefault(); } return; }
  if (PANEL) return;
  if (atEnd(S)) { if (e.key === 'Enter') { e.preventDefault(); var ec = endCard(S); if (ec.kind === 'unsure-done') { setUnsureOnly(S, false, now()); draw(true); } else close(); } else if (e.key === 'ArrowLeft') { e.preventDefault(); go(S, -1, now()); draw(true); } else if (e.key === 'u') { e.preventDefault(); doUndo(); } return; }
  var map = { '1': key1, '2': key2, '3': key3, '4': key4, ' ': playLine, 'u': doUndo, 'U': doUndo,
    Enter: function () { go(S, 1, now()); draw(true); }, ArrowRight: function () { go(S, 1, now()); draw(true); }, ArrowLeft: function () { go(S, -1, now()); draw(true); } };
  if (map[e.key]) { e.preventDefault(); map[e.key](); }
}
function onTime() { var a = doc.getElementById('ls-audio'); if (STOP_AT != null && a && !a.paused && a.currentTime >= STOP_AT) { a.pause(); STOP_AT = null; } }
function close() {
  stopAudio();
  if (BOX) BOX.hidden = true;
  doc.body.classList.remove('rv-on');
  clearInterval(TIMER); TIMER = null;
  if (H && H.redraw) H.redraw();
}
async function open(x, hooks) {
  H = hooks; X = x;
  var pick = null;
  try { var r = await fetch('data/review-pick/' + x.date + '.json?v=' + Date.now(), { cache: 'no-store', signal: AbortSignal.timeout(15000) }); pick = r.ok ? await r.json() : null; }
  catch (e) { pick = null; }
  if (!pick || !(pick.lines || []).length) { root.alert('No review list for this lesson yet (built within the hour).'); return; }
  S = create({ pick: pick, date: x.date, rows: AC().rowsFor ? AC().rowsFor(x.date) : [], now: now() });
  if (!BOX) {
    BOX = el('section', 'rv-box'); BOX.setAttribute('role', 'dialog'); BOX.setAttribute('aria-label', 'Review the student\'s lines');
    (doc.getElementById('anees-bank') || doc.body).appendChild(BOX);
    doc.addEventListener('keydown', onKey);
    var a = doc.getElementById('ls-audio'); if (a) a.addEventListener('timeupdate', onTime);
  }
  BOX.hidden = false; OPENED = now();
  doc.body.classList.add('rv-on');
  clearInterval(TIMER); TIMER = setInterval(function () { var t = BOX.querySelector('.rv-timer'); if (t) t.textContent = clock(now() - OPENED); }, 1000);
  draw(true);
}
function button(x, hooks) {
  var b = el('button', 'ab-chip rv-open', 'Review · one line at a time');
  b.type = 'button';
  b.title = 'Fast review: the student\'s lines with Arabic, unsure first; keys 1-4 (PG-50)';
  b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); open(x, hooks); });
  return b;
}
root.AneesReview = Object.assign(api, { button: button, open: open, close: close, state: function () { return S; } });
})(this);
