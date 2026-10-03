/* Correction mode on the Lessons page transcript (PR-15; Medi 2026-10-02 "i am going to make some corrections to the
   transcript. try and make rule and patterns with my corrections."; 2026-10-03 "do a hand off chip where I can make all
   the corrections. Have it make rules for every correction if possible").
   - The fix lives inside the chip detail: ✗ → "Not a mistake" (one tap asks why); ✓ vocab → "Was wrong"; ✓ grammar →
     "Not a use"; Amal's fix → "Not a correction"; a grey dropped word → "It was a mistake".
   - Tap a word on a line → "What did you say?" with 2-3 guesses (her chat words, Amal's next line, list words) + a box.
   - "✎ more" on each line: wrong speaker, wrong time, a missing word, add a slip.
   - Toast "Saved · Undo · counts update within 15 min"; the "✎ yours" tag on the line is the Undo (no expiry).
   - Under the transcript: "This looks like a rule: …" cards from docs/data/correction-proposals.json (built by
     scripts/medi_corrections.py propose) with the first 3 moments before → after and ▶, "Just this one" / "Make it a rule".
   Rows go to Supabase transcript_corrections (migration 022, append-only; Undo = a new row) through a localStorage queue
   (the docs/js/possible-names.js pattern). No login (PR-02). Nothing here changes a number: the 15-minute job pulls,
   recounts and publishes through the guard.
   API: window.AneesCorrections = {setup, decorate, chipActions, wordTap, mountLesson, overlay, effective}; pure helpers
   exported for tests/test_transcript_corrections.cjs. */
(function (root) {
'use strict';

var QK = 'anees-correction-queue', LK = 'anees-correction-log', SK = 'anees-correction-server';
var REASONS = [['not-correcting', "She wasn't correcting me"], ['fixed-first', 'I fixed it first'], ['both-fine', 'She said both are fine'],
  ['asking', 'I was asking'], ['wrong-moment', 'Wrong speaker or time'], ['right', 'My Arabic was right (Amal decides)']];
var KIND_WORDS = { text: 'heard word', speaker: 'speaker', time: 'time', missing: 'missing word', 'not-slip': 'not a mistake',
  'was-wrong': 'was wrong', classify: 'vocab ↔ grammar', add: 'added a slip', 'not-use': 'not a use', 'rule-answer': 'rule answer' };

/* ---------- pure helpers (tested) ---------- */
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
function words(s) { return String(s || '').split(/[\s.…,،؟?!:;"“”()]+/).filter(Boolean); }
// The newest-wins effective set: rows not undone (an undo of an undo restores), oldest first. Mirrors medi_corrections.effective.
function effective(rows) {
  var seen = {}, list = [];
  (rows || []).forEach(function (r) { if (r && r.id && !seen[r.id]) { seen[r.id] = 1; list.push(r); } });
  list.sort(function (a, b) { return String(a.ts).localeCompare(String(b.ts)) || String(a.created_at || '').localeCompare(String(b.created_at || '')) || String(a.id).localeCompare(String(b.id)); });
  var undone = {};
  list.forEach(function (r) { if (r.kind === 'undo' && r.undoes) { if (undone[r.undoes]) delete undone[r.undoes]; else undone[r.undoes] = 1; } });
  var gone = {};
  list.forEach(function (r) { if (r.kind === 'undo' && !undone[r.id]) gone[r.undoes] = 1; });
  return list.filter(function (r) { return r.kind !== 'undo' && !gone[r.id]; });
}
// 2-3 guesses for "What did you say?": her chat words, Amal's next line, list words - most like the engine's word first.
function guesses(word, ctx, toArabizi) {
  var az = toArabizi && /[؀-ۿ]/.test(word) ? toArabizi(word).text : word;
  var pool = [];
  (ctx.chat || []).forEach(function (w) { pool.push({ w: w, from: 'her chat', s: Math.max(sim(az, w), sim(word, w)) + 0.05 }); });
  (ctx.amal || []).forEach(function (w) { pool.push({ w: w, from: "Amal's next line", s: sim(word, w) }); });
  (ctx.list || []).forEach(function (x) { pool.push({ w: x.arabic, az: x.arabizi, from: 'your word list', s: Math.max(sim(word, x.arabic), sim(az, x.arabizi)) - 0.05 }); });
  var out = [], seen = {};
  seen[norm(word)] = 1;
  pool.sort(function (a, b) { return b.s - a.s; }).forEach(function (g) {
    var k = norm(g.w);
    if (out.length >= 3 || !k || seen[k] || g.s < 0.34) return;
    seen[k] = 1; out.push(g);
  });
  return out;
}
// The local overlay (shown at once, before the 15-minute rebuild): his text / speaker / time / missing rows on one turn.
// A row the build already applied (its id is on turn.heard) is not applied twice.
function overlay(turn, rows) {
  var t = Object.assign({}, turn), applied = {};
  (turn.heard || []).forEach(function (h) { if (h.correction) applied[h.correction] = 1; });
  (rows || []).forEach(function (r) {
    if (applied[r.id]) return;
    var p = r.payload || {};
    if (r.kind === 'text' && p.engine_wrote && t.text.indexOf(p.engine_wrote) >= 0) {
      t.engine = t.engine || turn.text; t.text = t.text.replace(p.engine_wrote, p.heard);
      t.heard = (t.heard || []).concat([{ engine_wrote: p.engine_wrote, heard: p.heard, rule: 'yours', correction: r.id }]);
    } else if (r.kind === 'missing' && p.heard) {
      t.engine = t.engine || turn.text; t.text = t.text.replace(/\s*$/, '') + ' ' + p.heard;
      t.heard = (t.heard || []).concat([{ engine_wrote: '', heard: p.heard, rule: 'yours', correction: r.id }]);
    } else if (r.kind === 'speaker' && p.who) { t.engine_who = turn.who; t.who = p.who; }
    else if (r.kind === 'time' && typeof p.t === 'number') { t.engine_t = turn.t; t.t = p.t; }
  });
  return t;
}
function mmss(t) { t = Math.max(0, Math.floor(Number(t) || 0)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); }
function parseTime(s) {
  var m = String(s || '').trim().match(/^(?:(\d+):)?(\d{1,2}):(\d{2})$/);
  if (!m) return null;
  return (+(m[1] || 0)) * 3600 + (+m[2]) * 60 + (+m[3]);
}
// Which actions a chip offers (the fix lives inside the chip detail, council 4)
function chipOffer(c) {
  if (!c) return [];
  if (c.s === 'wrong' || c.s === 'asked' || c.s === 'partial') return ['not-slip'];
  if (c.k === 'vocab' && c.s === 'correct') return ['was-wrong'];
  if (c.k === 'grammar' && c.s === 'correct') return ['not-use'];
  if (c.k === 'fix') return ['not-correcting'];
  if (c.k === 'na' && c.label === 'vocab') return ['was-wrong'];
  return [];
}

var api = { norm: norm, sim: sim, effective: effective, guesses: guesses, overlay: overlay, parseTime: parseTime, chipOffer: chipOffer, REASONS: REASONS };
if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }

/* ---------- storage: transcript_corrections, offline queue ---------- */
var doc = root.document;
var LS = function (k, v) { try { if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null'); localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return v === undefined ? null : false; } };
var uuid = function () { return (root.crypto && crypto.randomUUID) ? crypto.randomUUID() : 'tc-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10); };
var A = function () { return root.ANEES || {}; };
var hdr = function () { return { apikey: A().anon, Authorization: 'Bearer ' + A().anon, 'Content-Type': 'application/json' }; };
var memQueue = [], serverRows = LS(SK) || [], table = 'unknown', syncing = false, again = false, H = {}, PROPOSALS = null, WORDS = null;
var readQ = function () { return (LS(QK) || []).concat(memQueue); };
function allRows() { return serverRows.concat(LS(LK) || [], memQueue); }
function rowsFor(date) { return effective(allRows()).filter(function (r) { return String(r.lesson_date) === String(date); }); }
async function probe() {
  if (!A().url) { table = 'offline'; return false; }
  try {
    var r = await fetch(A().url + '/rest/v1/transcript_corrections?select=*&order=ts.asc,id.asc&limit=5000', { headers: hdr(), cache: 'no-store', signal: AbortSignal.timeout(15000) });
    if (r.status === 404 || r.status === 400) { table = 'missing'; return false; }
    if (!r.ok) { table = 'offline'; return false; }
    serverRows = await r.json(); LS(SK, serverRows); table = 'ok'; return true;
  } catch (e) { table = 'offline'; return false; }
}
function enqueue(row) {
  var q = LS(QK) || []; q.push(row); var ok = LS(QK, q);
  var log = LS(LK) || []; log.push(row); LS(LK, log.slice(-2000));
  if (!ok || !(LS(QK) || []).some(function (x) { return x.id === row.id; })) memQueue.push(row);
  sync();
}
function removeSent(ids) { var s = {}; ids.forEach(function (i) { s[i] = 1; }); LS(QK, (LS(QK) || []).filter(function (x) { return !s[x.id]; })); memQueue = memQueue.filter(function (x) { return !s[x.id]; }); }
async function sync() {
  if (syncing) { again = true; return; }
  syncing = true;
  try {
    if (readQ().length && table !== 'ok') await probe();
    while (table === 'ok') {
      var q = readQ(); if (!q.length) break;
      var batch = q.slice(0, 50), r;
      try { r = await fetch(A().url + '/rest/v1/transcript_corrections?on_conflict=id', { method: 'POST', headers: Object.assign(hdr(), { Prefer: 'resolution=ignore-duplicates,return=minimal' }), body: JSON.stringify(batch), signal: AbortSignal.timeout(15000) }); }
      catch (e) { table = 'offline'; break; }
      if (r.ok) { removeSent(batch.map(function (x) { return x.id; })); continue; }
      if (r.status === 404) { table = 'missing'; break; }
      if (r.status === 400 || r.status === 409) {           // a row the table refuses: kept on this device, never retried in a loop
        var bad = batch[0]; removeSent([bad.id]); var dead = LS(QK + '-refused') || []; dead.push(bad); LS(QK + '-refused', dead.slice(-200)); continue;
      }
      table = 'offline'; break;
    }
  } finally { syncing = false; }
  status();
  if (again) { again = false; sync(); }
}
function statusText() {
  var k = readQ().length;
  if (table === 'missing') return k + ' correction' + (k === 1 ? '' : 's') + ' saved on this device; the table is not set up yet.';
  if (table === 'offline') return k ? k + ' waiting to sync (offline is fine).' : 'Corrections are kept on this device until the table is reachable.';
  if (table === 'ok') return k ? 'Syncing ' + k + '…' : 'All corrections saved · counts update within 15 min.';
  return 'Checking the corrections table…';
}
function status() { Array.prototype.forEach.call(doc.querySelectorAll('.tc-sync'), function (n) { n.textContent = statusText(); n.dataset.state = table; }); }
root.addEventListener('online', sync);
// L1 / PG-14: back on the tab -> re-read the table (a correction made on the phone shows here), resend the queue, redraw
if (root.AneesLive) root.AneesLive.onReturn(function () { return probe().then(function () { status(); sync(); if (H.redraw) H.redraw(); }); },
  { busy: function () { return !!doc.querySelector('.tc-panel, .tc-why'); } });   // never wipe a half-typed correction

/* ---------- small DOM helpers ---------- */
function el(tag, cls, text) { var n = doc.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
function btn(cls, text, on, title) {
  var b = el('button', 'tc-btn ' + (cls || ''), text); b.type = 'button'; if (title) b.title = title;
  b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); on(b); }); return b;
}
function arabic(n) { n.setAttribute('lang', 'ar'); n.setAttribute('dir', 'auto'); return n; }

/* ---------- saving + toast + undo ---------- */
var toastTimer = null;
function save(x, turn, kind, target, payload, note, extra) {
  var d = new Date();
  var row = Object.assign({ id: uuid(), lesson_date: x.date, turn_t: Math.round(Number(turn.t) * 100) / 100, turn_who: turn.who || 'Medi',
    kind: kind, target: target || null, payload: Object.assign({ turn_end: turn.end != null ? turn.end : null, line: (turn.engine || turn.text || '').slice(0, 400) }, payload || {}),
    note: note || null, ts: d.toISOString(), tz_offset_min: -d.getTimezoneOffset() }, extra || {});
  enqueue(row);
  toast(row);
  if (H.redraw) H.redraw();
  return row;
}
function undo(row) {
  var d = new Date();
  enqueue({ id: uuid(), lesson_date: row.lesson_date, turn_t: row.turn_t, turn_who: row.turn_who, kind: 'undo', undoes: row.id, ts: d.toISOString(), tz_offset_min: -d.getTimezoneOffset() });
  if (H.redraw) H.redraw();
}
function toast(row) {
  var t = doc.getElementById('tc-toast');
  if (!t) { t = el('div', 'tc-toast'); t.id = 'tc-toast'; t.setAttribute('role', 'status'); (doc.getElementById('anees-bank') || doc.body).appendChild(t); }
  t.textContent = '';
  t.appendChild(el('span', '', 'Saved · ' + (KIND_WORDS[row.kind] || row.kind) + ' · '));
  t.appendChild(btn('tc-undo', 'Undo', function () { undo(row); t.hidden = true; }));
  t.appendChild(el('span', '', ' · counts update within 15 min'));
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { t.hidden = true; }, 8000);
}

/* ---------- which of his rows belong to a line / a chip ---------- */
function lineRows(date, parts) {
  return rowsFor(date).filter(function (r) {
    return r.kind !== 'rule-answer' && (parts || []).some(function (p) { return Math.abs(Number(r.turn_t) - Number(p.t)) <= 1 && (!r.turn_who || r.turn_who === p.who || r.kind === 'speaker' || r.kind === 'time'); });
  });
}
// A chip's id is renumbered on every build, so his row finds it by the producer id (src) - or, for a chip without one, by
// the same line time (+-3 s), kind and words.
function chipRows(date, c, turn) {
  return rowsFor(date).filter(function (r) {
    var tg = r.target || {};
    if (c.src) return tg.src === c.src;
    return !tg.src && turn && Math.abs(Number(r.turn_t) - Number(turn.t)) <= 3 && (tg.said || '') === (c.said || '') && (tg.rule || null) === (c.rule || null)
      && ['not-slip', 'was-wrong', 'not-use'].indexOf(r.kind) >= 0;
  });
}

/* ---------- chip detail: the fix lives here ---------- */
function chipActions(d, c, x, turn, link) {
  var offer = chipOffer(c);
  if (!offer.length) return;
  var mine = chipRows(x.date, c, turn);
  var box = el('div', 'tc-actions');
  if (mine.length) {
    var r = mine[mine.length - 1];
    box.appendChild(el('span', 'tc-yours-note', '✎ yours: ' + (KIND_WORDS[r.kind] || r.kind) + ((r.payload || {}).reason ? ' (' + (REASONS.filter(function (q) { return q[0] === r.payload.reason; })[0] || [])[1] + ')' : '') + ' · '));
    box.appendChild(btn('tc-small', 'Undo', function () { undo(r); }));
    d.appendChild(box);
    return;
  }
  var tg = { chip: c.id, src: c.src || null, k: c.k === 'fix' ? c.of : c.k, rule: c.rule || null, said: c.said || null, wrong: c.said || null,
    right: c.right || null, signal: c.signal || null, sig: c.sig || null, word: c.ar || null, name: c.name || null, amal_ruled: !!c.amal_ruled };
  if (offer[0] === 'not-slip') {
    var b = btn('tc-big', 'Not a mistake', function () {
      b.remove();
      var why = el('div', 'tc-why');
      why.appendChild(el('div', 'tc-q', 'Why?'));
      REASONS.forEach(function (q) {
        why.appendChild(btn('tc-reason' + (q[0] === 'right' ? ' tc-amal' : ''), q[1], function () { save(x, turn, 'not-slip', tg, { reason: q[0], signal: c.signal || null }); },
          q[0] === 'right' ? "Amal decides whether your Arabic was right: it goes to her Tutor hub and keeps counting until she taps" : ''));
      });
      box.appendChild(why);
    });
    box.appendChild(b);
  } else if (offer[0] === 'was-wrong') {
    box.appendChild(btn('tc-big', c.k === 'na' ? 'It was a mistake' : 'Was wrong', function () {
      save(x, turn, 'was-wrong', Object.assign(tg, { k: 'vocab' }), { right: c.ar || null, k: 'vocab' });
    }, "Counted when Amal voiced the fix; otherwise it goes to her review page (tier B)"));
  } else if (offer[0] === 'not-use') {
    box.appendChild(btn('tc-big', 'Not a use', function () { save(x, turn, 'not-use', tg, {}); }));
  } else if (offer[0] === 'not-correcting') {
    // Amal's fix chip: "she was not correcting me" is about the linked ✗ (his line)
    box.appendChild(btn('tc-big', 'Not a correction', function () {
      var slip = link || {}, sturn = (link && link._turn) || turn;
      save(x, sturn, 'not-slip', Object.assign(tg, { chip: slip.id || c.link, src: slip.src || null, k: c.of, said: c.said, wrong: c.said }), { reason: 'not-correcting', signal: c.signal || null });
    }));
  }
  d.appendChild(box);
}

/* ---------- tap a word: "What did you say?" ---------- */
function ctxFor(x, turn) {
  var T = x.turns || [], t0 = Number(turn.t), chat = [], amal = [];
  T.forEach(function (u) {
    if (u.who === 'chat' && u.t >= t0 - 10 && u.t <= t0 + 60) chat = chat.concat(words(u.text));
    if (u.who === 'Amal' && u.t > t0 && u.t <= t0 + 20) amal = amal.concat(words(u.text));
  });
  return { chat: chat, amal: amal, list: WORDS || [] };
}
function wordTap(ev, x, row, turn, parts) {
  var hit = null, box = ev.target.closest('.gc-latin, .gc-arabic');
  if (!box) return false;
  var r = doc.caretRangeFromPoint ? doc.caretRangeFromPoint(ev.clientX, ev.clientY) : null;
  if (!r && doc.caretPositionFromPoint) { var cp = doc.caretPositionFromPoint(ev.clientX, ev.clientY); r = cp && { startContainer: cp.offsetNode, startOffset: cp.offset }; }
  var full = box.textContent, at = 0;
  if (r && r.startContainer && r.startContainer.nodeType === 3) {
    var walk = doc.createTreeWalker(box, NodeFilter.SHOW_TEXT, null), n;
    while ((n = walk.nextNode())) { if (n === r.startContainer) { at += r.startOffset; break; } at += n.nodeValue.length; }
    var a = at, b = at;
    while (a > 0 && !/\s/.test(full[a - 1])) a--;
    while (b < full.length && !/\s/.test(full[b])) b++;
    hit = full.slice(a, b).replace(/^[.…,،؟?!:;"“”()]+|[.…,،؟?!:;"“”()]+$/g, '');
    if (box.classList.contains('gc-latin') && /[؀-ۿ]/.test(turn.text)) {      // Arabizi line: map by word position
      var li = words(full.slice(0, a)).length, aw = words(turn.text), lw = words(full);
      hit = aw.length === lw.length ? aw[li] : null;
    }
  }
  openWordPanel(row, x, turn, parts, hit);
  return true;
}
function partFor(parts, word) {
  var p = (parts || []).filter(function (q) { return word && q.text.indexOf(word) >= 0; })[0];
  return p || (parts || [])[0];
}
function closePanels(row) { Array.prototype.forEach.call(row.querySelectorAll('.tc-panel'), function (n) { n.remove(); }); }
function openWordPanel(row, x, turn, parts, word) {
  closePanels(row);
  var P = el('div', 'tc-panel'), main = row.querySelector('.tm-main') || row;
  P.setAttribute('role', 'group');
  if (!word) {
    P.appendChild(el('div', 'tc-q', 'Which word did the engine get wrong?'));
    var ws = el('div', 'tc-row');
    words(turn.text).forEach(function (w) { ws.appendChild(arabic(btn('tc-word', w, function () { openWordPanel(row, x, turn, parts, w); }))); });
    P.appendChild(ws);
  } else {
    var part = partFor(parts, word);
    var q = el('div', 'tc-q'); q.appendChild(document.createTextNode('What did you say? The engine wrote '));
    if (H.toArabizi && /[؀-ۿ]/.test(word)) q.appendChild(el('b', '', H.toArabizi(word).text + ' '));
    q.appendChild(arabic(el('small', '', word)));
    P.appendChild(q);
    var g = guesses(word, ctxFor(x, part), H.toArabizi), gr = el('div', 'tc-row');
    g.forEach(function (o) {
      var b = btn('tc-big tc-guess', '', function () { save(x, part, 'text', { word: word }, { engine_wrote: word, heard: o.w, from: o.from }); });
      // S1: Arabizi big, Arabic small
      var isAr = /[؀-ۿ]/.test(o.w), big = o.az || (isAr && H.toArabizi ? H.toArabizi(o.w).text : o.w);
      b.appendChild(el('span', 'tc-g', big)); if (isAr) b.appendChild(arabic(el('small', '', ' ' + o.w))); b.appendChild(el('small', 'tc-from', ' · ' + o.from));
      gr.appendChild(b);
    });
    P.appendChild(gr);
    var f = el('form', 'tc-type'), inp = el('input'); inp.type = 'text'; inp.placeholder = 'Type what you said'; inp.setAttribute('dir', 'auto'); inp.setAttribute('aria-label', 'What you said');
    f.appendChild(inp); f.appendChild(btn('tc-big', 'Save', function () { if (inp.value.trim()) save(x, part, 'text', { word: word }, { engine_wrote: word, heard: inp.value.trim(), from: 'typed' }); }));
    f.addEventListener('submit', function (e) { e.preventDefault(); if (inp.value.trim()) save(x, part, 'text', { word: word }, { engine_wrote: word, heard: inp.value.trim(), from: 'typed' }); });
    P.appendChild(f);
  }
  P.appendChild(btn('tc-small tc-close', 'Close', function () { P.remove(); }));
  main.appendChild(P);
  var i = P.querySelector('input'); if (i && !g_len(P)) i.focus();
}
function g_len(P) { return P.querySelectorAll('.tc-guess').length; }

/* ---------- "✎ more": speaker, time, missing word, add a slip ---------- */
function moreMenu(row, x, turn, parts) {
  closePanels(row);
  var P = el('div', 'tc-panel'), main = row.querySelector('.tm-main') || row, part = (parts || [])[0] || turn;
  var other = part.who === 'Medi' ? 'Amal' : 'Medi';
  var r1 = el('div', 'tc-row');
  r1.appendChild(btn('tc-big', 'This was ' + other, function () { save(x, part, 'speaker', null, { who: other }); }));
  var tf = el('form', 'tc-type'), ti = el('input'); ti.placeholder = 'Right time, e.g. ' + mmss(part.t); ti.setAttribute('aria-label', 'Right time');
  var tsave = function () { var v = parseTime(ti.value); if (v == null) { ti.setCustomValidity('Use m:ss'); ti.reportValidity(); return; } save(x, part, 'time', null, { t: v }); };
  tf.appendChild(ti); tf.appendChild(btn('tc-big', 'Fix time', tsave)); tf.addEventListener('submit', function (e) { e.preventDefault(); tsave(); });
  var mf = el('form', 'tc-type'), mi = el('input'); mi.placeholder = 'A word the engine dropped'; mi.setAttribute('dir', 'auto'); mi.setAttribute('aria-label', 'Missing word');
  var msave = function () { if (mi.value.trim()) save(x, part, 'missing', null, { heard: mi.value.trim() }); };
  mf.appendChild(mi); mf.appendChild(btn('tc-big', 'Add word', msave)); mf.addEventListener('submit', function (e) { e.preventDefault(); msave(); });
  P.appendChild(el('div', 'tc-q', 'Fix this line'));
  P.appendChild(r1); P.appendChild(tf); P.appendChild(mf);
  if (part.who === 'Medi') {
    P.appendChild(el('div', 'tc-q', 'A mistake nobody marked'));
    var sf = el('form', 'tc-type tc-slip'), sw = el('input'), sr = el('input'), sk = el('select');
    sw.placeholder = 'What you said'; sr.placeholder = 'What it should be'; sw.setAttribute('dir', 'auto'); sr.setAttribute('dir', 'auto');
    sw.setAttribute('aria-label', 'What you said'); sr.setAttribute('aria-label', 'What it should be'); sk.setAttribute('aria-label', 'Word or grammar');
    [['vocab', 'Wrong word'], ['grammar', 'Grammar']].forEach(function (o) { var op = el('option', '', o[1]); op.value = o[0]; sk.appendChild(op); });
    var ssave = function () {
      if (!sw.value.trim()) { sw.focus(); return; }
      save(x, part, 'add', { k: sk.value, said: sw.value.trim() }, { k: sk.value, wrong: sw.value.trim(), right: sr.value.trim() || null });
    };
    sf.appendChild(sw); sf.appendChild(sr); sf.appendChild(sk); sf.appendChild(btn('tc-big', 'Add slip', ssave)); sf.addEventListener('submit', function (e) { e.preventDefault(); ssave(); });
    P.appendChild(sf);
    P.appendChild(el('div', 'ab-mini', 'Counted when Amal voiced the fix right after; otherwise it goes to her review page.'));
  }
  P.appendChild(btn('tc-small tc-close', 'Close', function () { P.remove(); }));
  main.appendChild(P);
}

/* ---------- each line: "✎ more" + "✎ yours" (= Undo) ---------- */
function decorate(row, x, turn, parts) {
  var head = row.querySelector('.ls-turnhead');
  if (!head || turn.who === 'chat') return;
  var mine = lineRows(x.date, parts || [turn]);
  if (mine.length) {
    var last = mine[mine.length - 1];
    head.appendChild(btn('tc-tag', '✎ yours' + (mine.length > 1 ? ' ×' + mine.length : ''), function () { undo(last); },
      'Your correction (' + (KIND_WORDS[last.kind] || last.kind) + '). Tap to undo the last one.'));
    row.classList.add('tc-has');
  }
  head.appendChild(btn('tc-more', '✎ more', function () { moreMenu(row, x, turn, parts); }, 'Wrong speaker, wrong time, a missing word, or a mistake nobody marked'));
  if (turn.engine_who) row.appendChild(el('div', 'ab-mini ls-heard', 'Recording engine put this on ' + turn.engine_who));
  if (turn.engine_t != null) row.appendChild(el('div', 'ab-mini ls-heard', 'Recording engine time: ' + mmss(turn.engine_t)));
}

/* ---------- "This looks like a rule" cards under the transcript ---------- */
function answerOf(pid) {
  return effective(allRows()).filter(function (r) { return r.kind === 'rule-answer' && r.proposal === pid; }).pop() || null;
}
// S1: Arabizi big, Arabic small - for the plain sentence and each before/after
function azText(text) {
  var span = el('span', 'tc-az');
  var t = String(text || ''), hasAr = /[؀-ۿ]/.test(t);
  span.appendChild(el('span', '', hasAr && H.toArabizi ? t.replace(/[؀-ۿ][؀-ۿ\s]*/g, function (m) { return H.toArabizi(m.trim()).text + (/\s$/.test(m) ? ' ' : ''); }) : t));
  if (hasAr) span.appendChild(arabic(el('small', 'tc-ar', (t.match(/[؀-ۿ][؀-ۿ\s]*/g) || []).map(function (m) { return m.trim(); }).join(' · '))));
  return span;
}
function proposalCard(x, p) {
  var card = el('div', 'tc-prop tc-owner-' + p.owner);
  var mine = answerOf(p.id);
  if (p.owner === 'one-off') { card.appendChild(el('div', 'tc-plain', p.plain)); return card; }
  var head = el('div', 'tc-plain');
  head.appendChild(el('b', '', p.owner === 'medi' ? 'This looks like a rule: ' : p.owner === 'amal' ? "Amal's call: " : 'A shape for a code rule: '));
  head.appendChild(azText(p.plain));
  card.appendChild(head);
  if (p.owner === 'medi') card.appendChild(el('div', 'ab-mini', 'It would change ' + p.n + ' other moment' + (p.n === 1 ? '' : 's') + (p.n ? ':' : ' today (and every future lesson).')));
  var list = el('ul', 'tc-moments');
  (p.first || []).forEach(function (m) {
    var li = el('li');
    li.appendChild(btn('tc-play', '▶ ' + m.date.slice(5) + ' ' + m.mmss, function (b) { if (H.play) H.play(m.date, m.t, b); }, 'Play this moment'));
    var bf = azText(m.before); bf.classList.add('tc-before'); li.appendChild(bf);
    li.appendChild(el('span', '', ' → '));
    var af = azText(m.after); af.classList.add('tc-after'); li.appendChild(af);
    list.appendChild(li);
  });
  if (p.n > 3) { var more = el('li', 'ab-mini', 'and ' + (p.n - 3) + ' more'); list.appendChild(more); }
  card.appendChild(list);
  var bar = el('div', 'tc-row');
  if (mine) {
    var said = mine.answer === 'yes' ? (p.owner === 'code' ? 'You asked Claude to write it' : 'You made it a rule' + (p.rule ? ' (' + p.rule + ')' : ' · it starts within 15 min')) : 'Kept as just this one';
    bar.appendChild(el('span', 'tc-yours-note', '✎ ' + said + ' · '));
    bar.appendChild(btn('tc-small', 'Undo', function () { undo(mine); }));
  } else if (p.owner === 'amal') {
    bar.appendChild(el('span', 'ab-mini', 'Whether your Arabic was right is Amal\'s call: it goes to her Tutor hub. Nothing for you to do.'));
  } else {
    var ans = function (a) { return function () { save(x, { t: p.t, who: 'Medi' }, 'rule-answer', null, { hash: p.hash }, null, { proposal: p.id, answer: a }); }; };
    bar.appendChild(btn('tc-big tc-primary', 'Just this one', ans('one')));
    var yes = btn('tc-big', p.owner === 'code' ? 'Ask Claude to write a rule' : 'Make it a rule', ans('yes'));
    if (p.owner === 'medi' && !p.can_yes) { yes.disabled = true; yes.title = 'Not offered: ' + (p.why_not || ''); bar.appendChild(yes); bar.appendChild(el('div', 'ab-mini', 'Not offered: ' + (p.why_not || ''))); }
    else bar.appendChild(yes);
  }
  card.appendChild(bar);
  return card;
}
async function loadProposals() {
  if (PROPOSALS) return PROPOSALS;
  try { var r = await fetch('data/correction-proposals.json?v=' + Date.now(), { cache: 'no-store', signal: AbortSignal.timeout(15000) }); PROPOSALS = r.ok ? ((await r.json()).proposals || []) : []; }
  catch (e) { PROPOSALS = []; }
  return PROPOSALS;
}
async function loadWords() {
  if (WORDS) return;
  try { var r = await fetch('data/words.json', { signal: AbortSignal.timeout(20000) }); WORDS = r.ok ? ((await r.json()).items || []).filter(function (w) { return w.arabic; }).map(function (w) { return { arabic: w.arabic, arabizi: w.arabizi }; }) : []; }
  catch (e) { WORDS = []; }
}
function mountLesson(body, x) {
  var box = el('section', 'tc-box');
  box.setAttribute('aria-label', 'Your corrections');
  var intro = el('p', 'ab-mini tc-intro', 'Correct anything: tap a chip (Not a mistake / Was wrong / Not a use), tap a word the engine got wrong, or ✎ more on a line. ');
  intro.appendChild(el('span', 'tc-sync', statusText()));
  box.appendChild(intro);
  var props = el('div', 'tc-props');
  box.appendChild(props);
  body.appendChild(box);
  function paint() {
    props.textContent = '';
    var ps = (PROPOSALS || []).filter(function (p) { return p.date === x.date; });   // his page taps + the ones he gave in chat
    var pending = rowsFor(x.date).filter(function (r) { return r.kind !== 'rule-answer' && !(PROPOSALS || []).some(function (p) { return p.from === r.id; }); }).length;
    if (pending) props.appendChild(el('div', 'ab-mini tc-wait', pending + ' new correction' + (pending === 1 ? '' : 's') + ': Anees looks for the rule behind ' + (pending === 1 ? 'it' : 'them') + ' within 15 min.'));
    ps.forEach(function (p) { props.appendChild(proposalCard(x, p)); });
  }
  paint();
  loadProposals().then(paint);
  probe().then(function () { status(); sync(); paint(); if (H.redraw) H.redraw(); });
  loadWords();
  return { paint: paint };
}
function setup(h) { H = Object.assign(H, h || {}); }
function label(r) {
  var why = (REASONS.filter(function (q) { return q[0] === (r.payload || {}).reason; })[0] || [])[1];
  return (KIND_WORDS[r.kind] || r.kind) + (why ? ' (' + why + ')' : '');
}

root.AneesCorrections = Object.assign(api, { setup: setup, decorate: decorate, chipActions: chipActions, wordTap: wordTap, mountLesson: mountLesson,
  rowsFor: rowsFor, lineRows: lineRows, chipRows: chipRows, label: label, statusText: statusText, sync: sync });
})(this);
