/* Lessons & Audio. Reads docs/data/lessons.json (+ docs/data/lessons/<date>.json on expand)
   and docs/data/grammar-console.json for grammar clips. Never invents a number:
   a null in the data renders as "—" with the data's own note. */
(function () {
'use strict';

var BUILD = window.ANEES_LESSONS_BUILD || String(Date.now());
var DATA = null, DETAIL = Object.create(null), CLIPS = Object.create(null);
var OPEN = Object.create(null);
var TAB = 'all', QUERY = '', SORT = 'new', MODE_ON = Object.create(null);
var TYPES = [
  ['all', 'All'], ['free-speak', 'Free Speak'], ['review-words', 'Review of words'],
  ['new-words', 'New words'], ['new-grammar', 'New grammar']
];
var TYPE_LABEL = { 'free-speak': 'Free Speak', 'review-words': 'Review of words', 'new-words': 'New words', 'new-grammar': 'New grammar' };
var MODES = [['listening', 'Listening'], ['speaking', 'Speaking'], ['both', 'Both']];
var SORT_KEY = 'anees.lessons.sort';
try { var s = localStorage.getItem(SORT_KEY); if (/^(new|old|grammar|words|fillers)$/.test(s || '')) SORT = s; } catch (e) { /* default */ }

var $ = function (id) { return document.getElementById(id); };
function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
function isArabic(s) { return /[؀-ۿ]/.test(s || ''); }
function num(v) { return typeof v === 'number' && isFinite(v); }
function mmss(t) {
  if (!num(t)) return '';
  t = Math.max(0, Math.round(t));
  var h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : String(m).padStart(2, '0')) + ':' + String(s).padStart(2, '0');
}
function prettyDate(d) {
  var p = d.split('-');
  return new Date(+p[0], +p[1] - 1, +p[2]).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}
function startTime(L) {
  if (!L.start_local) return null;
  var m = /T(\d\d):(\d\d)/.exec(L.start_local);
  if (!m) return null;
  var h = +m[1], ap = h >= 12 ? 'pm' : 'am';
  return ((h % 12) || 12) + ':' + m[2] + ' ' + ap;
}
// Notes that explain a missing value; picked by the field they name, else all of them.
function noteFor(L, words) {
  var notes = L.notes || [];
  var hit = notes.filter(function (n) { return words.some(function (w) { return n.toLowerCase().indexOf(w) >= 0; }); });
  return (hit.length ? hit : notes).join(' ') || 'Not measured for this lesson.';
}
function dash(L, words) {
  var d = el('span', 'ls-null', '—');
  var note = noteFor(L, words);
  d.title = note;
  d.setAttribute('aria-label', 'Not measured: ' + note);
  return d;
}

/* ---------- Arabizi (rule S1): the Word Bank's own converter, loaded like the Grammar Console ---------- */
var toArabizi = window.AneesWordBankArabizi ? window.AneesWordBankArabizi.create() : null;
// Her Arabizi on top, the Arabic small underneath. html may carry our own <mark> spans.
function speech(cls, html, text) {
  var box = el('div', 'gc-speech ' + (cls || ''));
  var src = el('span');
  if (html) src.innerHTML = html; else src.textContent = text || '—';
  var source = src.textContent;
  if (!toArabizi || !isArabic(source)) {
    var only = el('div', 'gc-latin');
    only.setAttribute('dir', 'auto');
    only.appendChild(src);
    box.appendChild(only);
    return box;
  }
  var latin = src.cloneNode(true), approximate = false;
  var walk = document.createTreeWalker(latin, NodeFilter.SHOW_TEXT, null), n, nodes = [];
  while ((n = walk.nextNode())) nodes.push(n);
  nodes.forEach(function (t) {
    if (!isArabic(t.nodeValue)) return;
    var r = toArabizi(t.nodeValue);
    if (r.approximate) approximate = true;
    t.nodeValue = r.text;
  });
  var top = el('div', 'gc-latin');
  top.setAttribute('dir', 'auto');
  top.appendChild(latin);
  box.appendChild(top);
  var ar = el('div', 'gc-arabic');
  ar.setAttribute('dir', 'auto');
  ar.setAttribute('lang', 'ar');
  ar.appendChild(src);
  box.appendChild(ar);
  if (approximate) box.appendChild(el('div', 'gc-spellnote', 'Unverified spelling stays in Arabic'));
  return box;
}
// Escape text and underline the first occurrence of each needle (our own markup only).
function markText(text, needles) {
  var out = esc(text);
  (needles || []).forEach(function (nd) {
    if (!nd || !nd[0]) return;
    var needle = esc(String(nd[0]).trim());
    if (!needle) return;
    var i = out.indexOf(needle);
    if (i < 0) return;
    out = out.slice(0, i) + '<mark class="' + nd[1] + '">' + needle + '</mark>' + out.slice(i + needle.length);
  });
  return out;
}

/* ---------- audio ---------- */
function lessonAudio(date, who) {
  if (date === '2026-09-10') return 'lessons/2026-09-10/audio/' + (who === 'Amal' ? 'Amal' : 'Medi') + '.mp3';
  return 'lessons/' + date + '/audio/lesson.mp3';
}
var audio = null, pendingSeek = null;
function play(src, from, label) {
  audio = audio || $('ls-audio');
  $('ls-player').hidden = false;
  $('ls-playerlabel').textContent = label;
  var abs = new URL(src, location.href).href;
  if (audio.src !== abs) {
    audio.src = src;
    pendingSeek = num(from) ? from : null;
    audio.load();
  } else if (num(from)) {
    try { audio.currentTime = from; } catch (e) { /* not seekable yet */ }
  }
  var p = audio.play();
  if (p && p.catch) p.catch(function () { /* user can press play */ });
}
function playButton(label, onClick, title) {
  var b = el('button', 'ls-play', '▶ ' + label);
  b.type = 'button';
  if (title) b.title = title;
  b.addEventListener('click', function (e) { e.stopPropagation(); onClick(); });
  return b;
}
function timeButton(date, t, who) {
  var b = el('button', 'ls-time', mmss(t));
  b.type = 'button';
  b.title = 'Play the lesson from ' + mmss(t);
  b.addEventListener('click', function () {
    play(lessonAudio(date, who), Math.max(0, t - 1), prettyDate(date) + ' · lesson from ' + mmss(t));
  });
  return b;
}

/* ---------- data helpers ---------- */
function lessons() { return DATA.lessons || []; }
function avg(list, pick) {
  var v = list.map(pick).filter(num);
  return v.length ? { value: v.reduce(function (a, b) { return a + b; }, 0) / v.length, n: v.length } : null;
}
function matches(L) {
  if (TAB !== 'all' && L.type !== TAB) return false;
  var anyMode = MODES.some(function (m) { return MODE_ON[m[0]]; });
  if (anyMode && !MODE_ON[L.review_mode]) return false;
  var q = QUERY.trim().toLowerCase();
  if (!q) return true;
  var hay = [L.date, prettyDate(L.date), TYPE_LABEL[L.type], L.type, L.review_mode || '']
    .concat((L.new_words || []).map(function (w) { return [w.arabizi, w.arabic, w.english, w.key].join(' '); }))
    .join(' ').toLowerCase();
  return hay.indexOf(q) >= 0;
}
function sortList(list) {
  var key = function (L) { return L.date + ' ' + (L.start_local || ''); };
  var nullsLast = function (a, b, va, vb, dir) {
    if (!num(va) && num(vb)) return 1;
    if (!num(vb) && num(va)) return -1;
    if (!num(va) && !num(vb)) return key(a) < key(b) ? 1 : -1;
    return (va - vb) * dir || (key(a) < key(b) ? 1 : -1);
  };
  return list.slice().sort(function (a, b) {
    switch (SORT) {
      case 'old': return key(a) < key(b) ? -1 : 1;
      case 'grammar': return nullsLast(a, b, a.grammar && a.grammar.pct, b.grammar && b.grammar.pct, 1);
      case 'words': return nullsLast(a, b, a.words && a.words.pct, b.words && b.words.pct, 1);
      case 'fillers': return nullsLast(a, b, a.fillers && a.fillers.per_min, b.fillers && b.fillers.per_min, -1);
      default: return key(a) < key(b) ? 1 : -1;
    }
  });
}

/* ---------- metrics ---------- */
function renderMetrics() {
  var L = lessons();
  var hours = L.reduce(function (a, x) { return a + (num(x.duration_min) ? x.duration_min : 0); }, 0) / 60;
  var w = avg(L, function (x) { return x.words && x.words.pct; });
  var g = avg(L, function (x) { return x.grammar && x.grammar.pct; });
  var sp = avg(L, function (x) { return x.talk && x.talk.speak_pct; });
  var f = avg(L, function (x) { return x.fillers && x.fillers.per_min; });
  var of = function (a) { return a ? 'Average of ' + a.n + ' of ' + L.length + ' lessons' : 'Not measured'; };
  var cards = [
    ['Lessons', String(L.length), 'Recorded with Amal'],
    ['Total hours', hours.toFixed(1), 'Of lesson audio'],
    ['Avg words right', w ? Math.round(w.value) + '%' : '—', of(w)],
    ['Avg grammar right', g ? Math.round(g.value) + '%' : '—', of(g)],
    ['Avg speaking share', sp ? Math.round(sp.value) + '%' : '—', of(sp)],
    ['Avg filled pauses / min', f ? f.value.toFixed(1) : '—', of(f)]
  ];
  var box = $('ls-metrics');
  box.textContent = '';
  cards.forEach(function (c) {
    var m = el('div', 'ab-metric');
    m.appendChild(el('div', 'ab-metric-label', c[0]));
    m.appendChild(el('div', 'ab-number', c[1]));
    m.appendChild(el('div', 'ab-tiny', c[2]));
    box.appendChild(m);
  });
}

/* ---------- tabs + chips ---------- */
function renderTabs() {
  var box = $('ls-tabs');
  box.textContent = '';
  TYPES.forEach(function (t) {
    var n = t[0] === 'all' ? lessons().length : lessons().filter(function (L) { return L.type === t[0]; }).length;
    var b = el('button', 'ab-tab', t[1]);
    b.type = 'button';
    b.dataset.tab = t[0];
    b.setAttribute('aria-pressed', TAB === t[0] ? 'true' : 'false');
    b.appendChild(el('span', 'ab-count', String(n)));
    b.addEventListener('click', function () { TAB = t[0]; renderTabs(); render(); });
    box.appendChild(b);
  });
}
function renderModes() {
  var box = $('ls-modes');
  box.textContent = '';
  MODES.forEach(function (m) {
    var n = lessons().filter(function (L) { return L.review_mode === m[0]; }).length;
    var b = el('button', 'ab-chip', 'Review · ' + m[1] + ' ' + n);
    b.type = 'button';
    b.setAttribute('aria-pressed', MODE_ON[m[0]] ? 'true' : 'false');
    b.addEventListener('click', function () { MODE_ON[m[0]] = !MODE_ON[m[0]]; renderModes(); render(); });
    box.appendChild(b);
  });
}

/* ---------- collapsed row ---------- */
function typeTags(L) {
  var box = el('div', 'ls-tags');
  box.appendChild(el('span', 'ls-type ls-type-' + L.type, TYPE_LABEL[L.type] || L.type));
  if (L.review_mode) box.appendChild(el('span', 'ls-mode', L.review_mode.charAt(0).toUpperCase() + L.review_mode.slice(1)));
  return box;
}
function wordsCell(L) {
  var c = el('div', 'ls-cell');
  var w = L.words || {};
  var top = el('div', 'ls-big');
  if (num(w.pct)) top.textContent = Math.round(w.pct) + '%'; else top.appendChild(dash(L, ['words']));
  c.appendChild(top);
  c.appendChild(el('div', 'ls-small', (num(w.unique) ? w.unique : '—') + ' words'));
  var rw = el('div', 'ls-small');
  rw.innerHTML = '<span class="ls-ok">' + (w.right || 0) + ' right</span> · <span class="ls-bad">' + (w.wrong || 0) + ' wrong</span>' + (w.partial ? ' · <span class="ls-part">' + w.partial + ' partial</span>' : '');
  c.appendChild(rw);
  return c;
}
function grammarCell(L) {
  var c = el('div', 'ls-cell');
  var g = L.grammar || {};
  var top = el('div', 'ls-big');
  if (num(g.pct)) top.textContent = Math.round(g.pct) + '%'; else top.appendChild(dash(L, ['grammar']));
  c.appendChild(top);
  c.appendChild(el('div', 'ls-small', (num(g.mistakes) ? g.mistakes : '—') + ' slips / ' + (num(g.uses) ? g.uses : '—') + ' uses'));
  return c;
}
function talkCell(L) {
  var c = el('div', 'ls-cell');
  var t = L.talk;
  if (!t || !num(t.speak_pct)) {
    c.appendChild(dash(L, ['talk', 'timing']));
    c.appendChild(el('div', 'ls-small', 'No word timings'));
    return c;
  }
  var bar = el('div', 'ls-bar');
  bar.setAttribute('role', 'img');
  bar.setAttribute('aria-label', 'You speak ' + Math.round(t.speak_pct) + '%, Amal speaks ' + Math.round(t.listen_pct) + '%');
  var a = el('i', 'ls-bar-you'); a.style.width = t.speak_pct + '%';
  var b = el('i', 'ls-bar-amal'); b.style.width = t.listen_pct + '%';
  bar.appendChild(a); bar.appendChild(b);
  c.appendChild(bar);
  var lab = el('div', 'ls-small ls-barlab');
  lab.innerHTML = '<span><i class="ls-dot ls-bar-you"></i>You ' + Math.round(t.speak_pct) + '%</span><span><i class="ls-dot ls-bar-amal"></i>Amal ' + Math.round(t.listen_pct) + '%</span>';
  c.appendChild(lab);
  return c;
}
function row(L) {
  var wrap = el('article', 'ab-row ls-row ls-row-' + L.type);
  wrap.dataset.date = L.date;
  var head = el('button', 'ab-grid ls-grid ab-rowhead ls-rowhead');
  head.type = 'button';
  head.setAttribute('aria-expanded', OPEN[L.date] ? 'true' : 'false');
  var c1 = el('div', 'ls-when');
  var d = el('div', 'ls-date');
  d.appendChild(el('span', 'ab-chevron', OPEN[L.date] ? '▾' : '▸'));
  d.appendChild(el('span', null, prettyDate(L.date)));
  c1.appendChild(d);
  var st = startTime(L);
  c1.appendChild(el('div', 'ls-small ls-indent', (st || 'start time unknown') + (num(L.duration_min) ? ' · ' + Math.round(L.duration_min) + ' min' : '')));
  head.appendChild(c1);
  head.appendChild(typeTags(L));
  head.appendChild(wordsCell(L));
  head.appendChild(grammarCell(L));
  head.appendChild(talkCell(L));
  head.addEventListener('click', function () {
    OPEN[L.date] = !OPEN[L.date];
    var fresh = row(L);
    wrap.replaceWith(fresh);
  });
  wrap.appendChild(head);
  if (OPEN[L.date]) wrap.appendChild(detail(L));
  return wrap;
}

/* ---------- expanded row ---------- */
function statBox(title, value, sub, def, L, nullWords) {
  var b = el('div', 'ls-stat');
  b.appendChild(el('div', 'ab-metric-label ls-statlabel', title));
  var v = el('div', 'ab-number ls-statnum');
  if (value == null) v.appendChild(dash(L, nullWords)); else v.textContent = value;
  b.appendChild(v);
  if (sub) b.appendChild(el('div', 'ls-small', sub));
  var dd = el('div', 'ls-def', def[0]);
  if (def[1]) dd.title = def[1];
  b.appendChild(dd);
  return b;
}
function statStrip(L) {
  var D = DATA.definitions || {};
  var strip = el('div', 'ls-strip');
  var f = L.fillers, lt = L.latency, fl = L.flow;
  // each filler in its own isolate so an Arabic one never flips its count to the other side
  var top = f && f.top ? f.top.slice(0, 4).map(function (p) { return '⁨' + p[0] + '⁩ ' + p[1]; }).join(' · ') : '';
  strip.appendChild(statBox('Filled pauses (um/uh)', f && num(f.count) ? String(f.count) : null,
    f && num(f.per_min) ? f.per_min + ' per min' + (top ? ' · ' + top : '') : null,
    ['Uh, um, آآ sounds while you talk (a floor: the engine drops some).', D['fillers.count']], L, ['filler', 'timing']));
  strip.appendChild(statBox('Response speed', lt && num(lt.median_s) ? lt.median_s.toFixed(1) + ' s' : null,
    lt && num(lt.p75_s) ? '3 in 4 replies within ' + lt.p75_s.toFixed(1) + ' s · ' + lt.n + ' replies' : null,
    ['Time from Amal finishing to you starting (middle value). A pause is not an error.', D['latency.median_s']], L, ['latency', 'timing']));
  strip.appendChild(statBox('Flow', fl && num(fl.wpm) ? fl.wpm.toFixed(0) + ' wpm' : null,
    fl && num(fl.n_turns) ? fl.n_turns + ' Arabic turns' : null,
    ['Arabic words per minute inside your Arabic turns.', D['flow.wpm']], L, ['flow', 'timing']));
  return strip;
}
function acc(title, fill) {
  var d = el('details', 'gc-doc ls-acc');
  var s = el('summary', 'ab-control', title);
  d.appendChild(s);
  var body = el('div', 'gc-doc-body ls-accbody');
  d.appendChild(body);
  var done = false;
  d.addEventListener('toggle', function () {
    if (!d.open || done) return;
    done = true;
    body.appendChild(el('div', 'ab-mini', 'Loading…'));
    loadDetail(d.closest('.ls-row').dataset.date).then(function (x) {
      body.textContent = '';
      fill(body, x);
    }).catch(function (err) { body.textContent = 'Could not load this lesson: ' + err.message; done = false; });
  });
  return d;
}
function loadDetail(date) {
  if (DETAIL[date]) return Promise.resolve(DETAIL[date]);
  return fetch('data/lessons/' + date + '.json?build=' + encodeURIComponent(BUILD))
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (j) { DETAIL[date] = j; return j; });
}
function itemHead(tagText, tagCls, date, t) {
  var head = el('div', 'gc-usehead');
  var left = el('span');
  left.appendChild(el('span', 'gc-tag ' + (tagCls || ''), tagText));
  head.appendChild(left);
  var right = el('span');
  right.appendChild(timeButton(date, t, 'Medi'));
  head.appendChild(right);
  return head;
}
function vocabList(body, x) {
  var list = x.vocab_errors || [];
  if (!list.length) { body.appendChild(el('div', 'gc-empty', 'No word misses scored in this lesson.')); return; }
  list.forEach(function (v) {
    var card = el('div', 'gc-use ' + (v.kind === 'partial' ? 'ls-use-partial' : 'gc-use-slip'));
    card.appendChild(itemHead(v.label || v.kind, null, x.date, v.t));
    var word = el('div', 'ls-word');
    word.appendChild(el('strong', null, v.arabizi || v.arabic));
    if (v.arabizi) { var ar = el('span', 'ls-ar', v.arabic); ar.setAttribute('lang', 'ar'); word.appendChild(ar); }
    word.appendChild(el('span', 'ls-en', v.english || ''));
    card.appendChild(word);
    card.appendChild(speech('gc-said', v.said_html, v.said));
    if (v.fix) {
      var rc = el('div', 'gc-recast');
      rc.appendChild(el('span', null, 'Amal: '));
      rc.appendChild(speech('gc-fix', markText(v.fix, [[v.arabic, 'ab-correct']]), null));
      card.appendChild(rc);
    }
    if (v.why) card.appendChild(el('p', 'ab-mini ls-why', v.why));
    var bar = el('div', 'ls-plays');
    if (v.clip) bar.appendChild(playButton('Play clip', function () { play(v.clip, 0, prettyDate(x.date) + ' · ' + v.mmss + ' · ' + (v.arabizi || v.arabic)); }));
    else bar.appendChild(playButton('Play from ' + v.mmss, function () { play(lessonAudio(x.date, 'Medi'), Math.max(0, v.t - 2), prettyDate(x.date) + ' · lesson from ' + v.mmss); }));
    card.appendChild(bar);
    body.appendChild(card);
  });
}
function grammarClip(date, e) {
  var c = CLIPS[e.id] || CLIPS[date + ' ' + e.mmss];
  return c && c.clip ? 'lessons/' + c.clip : null;
}
function grammarList(body, x) {
  var list = x.grammar_errors || [];
  if (!list.length) { body.appendChild(el('div', 'gc-empty', 'No grammar slips Amal corrected in this lesson.')); return; }
  list.forEach(function (e) {
    var card = el('div', 'gc-use gc-use-slip');
    card.appendChild(itemHead((e.bucket ? e.bucket + ' · ' : '') + (e.bucket_name || 'grammar'), null, x.date, e.t));
    if (e.mistake) card.appendChild(el('div', 'ls-mistake', e.mistake));
    card.appendChild(speech('gc-said', markText(e.said, [[e.wrong, 'ab-wrong']]), null));
    if (e.fix) {
      var rc = el('div', 'gc-recast');
      rc.appendChild(el('span', null, 'Amal' + (num(e.t_fix) ? ' (' + mmss(e.t_fix) + ')' : '') + ': '));
      rc.appendChild(speech('gc-fix', markText(e.fix, [[e.right, 'ab-correct']]), null));
      card.appendChild(rc);
    }
    if (e.chat) card.appendChild(el('p', 'ab-mini', 'Chat: ' + e.chat));
    if (e.wrong && e.right) {
      // wrong → right reads left to right on both lines; each side isolated so its own words stay in order
      var pair = speech('gc-pairline', null, '⁨' + e.wrong + '⁩  →  ⁨' + e.right + '⁩');
      Array.prototype.forEach.call(pair.querySelectorAll('[dir]'), function (n) { n.setAttribute('dir', 'ltr'); });
      card.appendChild(pair);
    }
    var bar = el('div', 'ls-plays');
    var clip = grammarClip(x.date, e);
    if (clip) bar.appendChild(playButton('Play clip', function () { play(clip, 0, prettyDate(x.date) + ' · ' + e.mmss + ' · ' + (e.bucket || 'grammar')); }));
    else bar.appendChild(playButton('Play from ' + e.mmss, function () { play(lessonAudio(x.date, 'Medi'), Math.max(0, e.t - 2), prettyDate(x.date) + ' · lesson from ' + e.mmss); }, 'No clip cut yet: plays the lesson audio from this time'));
    card.appendChild(bar);
    body.appendChild(card);
  });
}
// Marks on the transcript: his wrong words in the Medi turn at the slip, her fix in the next Amal turns.
function transcriptMarks(x) {
  var turns = x.turns || [], out = turns.map(function () { return []; });
  (x.marks || []).forEach(function (m) {
    var cls = m.kind === 'vocab' ? 'ab-partial' : 'ab-wrong';
    var said = -1;
    for (var i = 0; i < turns.length; i++) {
      var t = turns[i];
      if (t.t < m.t - 6) continue;
      if (t.t > m.t + 20) break;
      if (t.who === 'Medi' && m.wrong && t.text.indexOf(m.wrong) >= 0) { out[i].push([m.wrong, cls]); said = i; break; }
    }
    var from = said >= 0 ? said + 1 : 0;
    for (var j = from; j < turns.length; j++) {
      var u = turns[j];
      if (u.t < m.t - 2) continue;
      if (u.t > m.t + 40) break;
      if (u.who === 'Amal' && m.right && u.text.indexOf(m.right) >= 0) { out[j].push([m.right, 'ab-correct']); break; }
    }
  });
  return out;
}
function transcript(body, x) {
  var turns = x.turns || [];
  if (!turns.length) { body.appendChild(el('div', 'gc-empty', 'No transcript for this lesson.')); return; }
  var L = lessons().filter(function (l) { return l.date === x.date; })[0];
  if (L && L.coverage) body.appendChild(el('p', 'ab-mini', 'Coverage: ' + L.coverage));
  var marks = transcriptMarks(x);
  var list = el('div', 'ls-transcript');
  turns.forEach(function (t, i) {
    var r = el('div', 'ls-turn ls-turn-' + (t.who === 'Medi' ? 'medi' : t.who === 'chat' ? 'chat' : 'amal'));
    var h = el('div', 'ls-turnhead');
    h.appendChild(timeButton(x.date, t.t, t.who));
    h.appendChild(el('span', 'ls-who', t.who === 'Medi' ? 'You' : t.who === 'chat' ? 'Chat' : t.who === '?' ? 'Unknown' : t.who));
    r.appendChild(h);
    r.appendChild(speech('ls-turntext', markText(t.text, marks[i]), null));
    list.appendChild(r);
  });
  body.appendChild(list);
}
function newWords(L) {
  var box = el('div', 'ls-newwords');
  var words = L.new_words || [];
  box.appendChild(el('h3', 'gc-secttitle', 'New words in this lesson (' + words.length + ')'));
  if (!words.length) { box.appendChild(el('div', 'gc-empty', 'No new words on Amal’s list first appeared in this lesson.')); return box; }
  var grid = el('div', 'ls-nwgrid');
  words.forEach(function (w) {
    var c = el('div', 'ls-nw');
    var top = el('div', 'ls-nwtop');
    top.appendChild(el('strong', 'ls-nwlatin', w.arabizi || w.arabic));
    if (num(w.t)) top.appendChild(timeButton(L.date, w.t, 'Amal'));
    c.appendChild(top);
    var ar = el('div', 'ls-ar', w.arabic);
    ar.setAttribute('lang', 'ar'); ar.setAttribute('dir', 'rtl');
    c.appendChild(ar);
    if (!w.arabizi) c.appendChild(el('div', 'gc-spellnote', 'Unverified spelling stays in Arabic'));
    c.appendChild(el('div', 'ls-en', w.english || ''));
    grid.appendChild(c);
  });
  box.appendChild(grid);
  return box;
}
function detail(L) {
  var d = el('div', 'ab-detail ls-detail');
  var why = el('p', 'ls-typewhy');
  why.appendChild(el('strong', null, 'Why this type: '));
  why.appendChild(document.createTextNode((L.type_why || '—') + ' '));
  why.appendChild(el('span', 'ls-muted', L.type_source === 'claude-read' ? '(Claude’s reading — tell Claude to change it)' : ''));
  d.appendChild(why);
  (L.notes || []).forEach(function (n) { d.appendChild(el('p', 'ab-mini ls-note', 'Note: ' + n)); });
  d.appendChild(statStrip(L));
  if (L.type === 'new-words') {
    d.appendChild(newWords(L));
  } else {
    var c = L.counts || {};
    d.appendChild(acc('Vocab errors (' + (num(c.vocab_errors) ? c.vocab_errors : '…') + ')', vocabList));
    d.appendChild(acc('Grammar errors (' + (num(c.grammar_errors) ? c.grammar_errors : '…') + ')', grammarList));
    d.appendChild(acc('Full transcript' + (num(c.turns) ? ' (' + c.turns + ' turns' + (c.chat_lines ? ' + ' + c.chat_lines + ' chat lines' : '') + ')' : ''), transcript));
  }
  var links = el('p', 'ab-mini');
  links.innerHTML = '<a class="ls-link" href="' + esc(L.page) + '">Open the full lesson page</a>';
  d.appendChild(links);
  return d;
}

/* ---------- render ---------- */
function render() {
  var rows = $('ls-rows');
  rows.textContent = '';
  var list = sortList(lessons().filter(matches));
  if (!list.length) rows.appendChild(el('div', 'ab-empty', 'No lesson matches those filters.'));
  list.forEach(function (L) { rows.appendChild(row(L)); });
  $('ls-results').textContent = list.length + ' of ' + lessons().length + ' lessons';
  $('ls-reset').hidden = !(QUERY || TAB !== 'all' || MODES.some(function (m) { return MODE_ON[m[0]]; }));
}
function wire() {
  $('ls-search').addEventListener('input', function (e) { QUERY = e.target.value; render(); });
  $('ls-sort').value = SORT;
  $('ls-sort').addEventListener('change', function (e) {
    SORT = e.target.value;
    try { localStorage.setItem(SORT_KEY, SORT); } catch (err) { /* not saved */ }
    render();
  });
  $('ls-reset').addEventListener('click', function () {
    QUERY = ''; TAB = 'all'; MODE_ON = Object.create(null);
    $('ls-search').value = '';
    renderTabs(); renderModes(); render();
  });
  $('ls-playerclose').addEventListener('click', function () {
    var a = $('ls-audio'); a.pause(); $('ls-player').hidden = true;
  });
  $('ls-audio').addEventListener('loadedmetadata', function () {
    if (pendingSeek != null) { try { this.currentTime = pendingSeek; } catch (e) { /* ignore */ } pendingSeek = null; }
  });
}

function optional(url) {
  return fetch(url).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
}
var q = '?build=' + encodeURIComponent(BUILD);
Promise.all([optional('data/words.json' + q), optional('data/house_spelling.json' + q), optional('data/word-bank-catalog.json' + q), optional('data/arabizi-extra.json' + q), optional('data/grammar-console.json' + q)])
  .then(function (res) {
    if (window.AneesWordBankArabizi) {
      var house = (res[1] && res[1].items) || {};
      var words = ((res[0] && res[0].items) || []).map(function (w) {
        var h = house[w.match_loose];
        return h && h.house ? Object.assign({}, w, { house_spelling: h.house }) : w;
      });
      toArabizi = window.AneesWordBankArabizi.create(words, res[2] || {}, res[3] || {});
    }
    // Grammar clips cut from the hand sweep: joined by sweep id, else by date + mm:ss.
    ((res[4] && res[4].rules) || []).forEach(function (r) {
      (r.candidates || []).concat(r.events || []).forEach(function (c) {
        if (!c.clip) return;
        if (c.id) CLIPS[c.id] = c;
        if (c.date && c.mmss) CLIPS[c.date + ' ' + c.mmss] = c;
      });
    });
    return fetch('data/lessons.json' + q);
  })
  .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  .then(function (json) {
    DATA = json;
    var L = lessons();
    $('ls-source').textContent = L.length + ' lessons · ' + L[0].date.slice(5) + ' to ' + L[L.length - 1].date.slice(5);
    $('ls-coverage').textContent = 'Source: docs/data/lessons.json · updated ' + DATA.updated + ' · lesson types are Claude’s reading, tell Claude to change any.';
    renderMetrics();
    renderTabs();
    renderModes();
    wire();
    render();
  })
  .catch(function (err) {
    $('ls-notice').textContent = 'Could not load the lessons data: ' + err.message;
    $('ls-source').textContent = 'Failed to load';
  });
})();
