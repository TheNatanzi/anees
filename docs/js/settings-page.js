/* System Settings. Reads docs/data/standing-rules.json (built from RULES.md by
   scripts/build_standing_rules.py), docs/data/ai_rules.json and docs/data/ai_reports.json.
   Same shell as the Word Bank / Lessons pages. Nothing here is paraphrased: every rule,
   report and project is shown as its source writes it. */
(function () {
'use strict';

var BUILD = window.ANEES_SETTINGS_BUILD || String(Date.now());
var STANDING = null, RULES = null, REPORTS = null;
var TAB = 'standing', QUERY = '', STATUS_ON = Object.create(null), OPEN = Object.create(null);
var STATUSES = [['enforced', 'Enforced'], ['partly', 'Partly'], ['planned', 'Planned']];
var TABS = [
  ['standing', 'Standing rules'], ['system', 'System rules'], ['words', 'Word & grammar rules'],
  ['reports', 'AI reports'], ['future', 'Future projects']
];
// Kept word for word from the old Future projects tab (index.html#future).
var FUTURE = [
  ['Deep research → rules.', 'Language-learning studies turned into rules the app follows (extends wiki 02 / 03 / 04 / 06).'],
  ['Voice homework answers.', 'Hold-to-talk on the homework page, transcribed by ElevenLabs Scribe (the chosen engine); typed answers only for now (Medi, 2026-09-05).'],
  ['Audio homework that listens.', 'Medi records a sentence, the app compares pronunciation (ElevenLabs TTS + STT; the LearnerVoice caveat: ASR auto-corrects learners, so grading needs Amal’s ear or a phone-level model).'],
  ['Adding words inside the app.', 'Today the Google Doc is the only truth; a form for Medi or Amal would feed a review inbox, never the Doc directly.'],
  ['Discord + Craig separate-track recording.', 'One audio track per person makes speaker labels exact (design agreed 2026-09-04; Ennuicastr as the paid fallback if Amal is on her phone).']
];
var SYS_NOTE = 'The mechanics: how lessons are recorded, transcribed, who spoke, what gets published and how numbers are shown.';
var WORD_NOTE = 'How the AI decides what counts as a mistake, what is a new word, and how Amal’s taps win.';
var REPORT_NOTE = 'Every research report so far, one card each: the question, the verdict, the numbers that decided it. Teal bars = the engine we use. Open the full report for the evidence.';

var $ = function (id) { return document.getElementById(id); };
function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

/* ---------- tiny Markdown (RULES.md uses paragraphs, **bold**, `code`, lists and tables) ---------- */
function inline(s) {
  return esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}
function md(src) {
  var out = [], lines = String(src || '').split('\n'), i = 0;
  while (i < lines.length) {
    var l = lines[i];
    if (!l.trim()) { i++; continue; }
    if (/^\s*\|/.test(l)) {
      var rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(lines[i]); i++; }
      var cells = function (r) { return r.trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); }); };
      var body = rows.filter(function (r, k) { return k !== 1 || !/^[\s|:-]+$/.test(r); });
      var h = cells(body[0]);
      out.push('<div class="st-tablewrap"><table class="st-table"><thead><tr>' + h.map(function (c) { return '<th>' + inline(c) + '</th>'; }).join('') + '</tr></thead><tbody>'
        + body.slice(1).map(function (r) { return '<tr>' + cells(r).map(function (c) { return '<td>' + inline(c) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>');
      continue;
    }
    if (/^\s*- /.test(l)) {
      var items = [];
      while (i < lines.length && /^\s*- |^\s{2,}\S/.test(lines[i]) && lines[i].trim()) {
        if (/^\s*- /.test(lines[i])) items.push(lines[i].replace(/^\s*- /, '')); else items[items.length - 1] += ' ' + lines[i].trim();
        i++;
      }
      out.push('<ul>' + items.map(function (t) { return '<li>' + inline(t) + '</li>'; }).join('') + '</ul>');
      continue;
    }
    var para = [];
    while (i < lines.length && lines[i].trim() && !/^\s*\||^\s*- /.test(lines[i])) { para.push(lines[i].trim()); i++; }
    out.push('<p>' + inline(para.join(' ')) + '</p>');
  }
  return out.join('');
}

/* ---------- data shaping ---------- */
function rulesFor(tab) {
  if (!RULES) return [];
  var list = [];
  RULES.groups.forEach(function (g) {
    g.rules.forEach(function (r) { if ((r.tab || g.tab) === tab) list.push(Object.assign({ group: g.title }, r)); });
  });
  return list;
}
function items(tab) {
  if (tab === 'standing') return ((STANDING && STANDING.rules) || []).map(function (r) { return { kind: 'standing', key: 's:' + r.id, r: r }; });
  if (tab === 'system' || tab === 'words') return rulesFor(tab).map(function (r) { return { kind: 'rule', key: 'r:' + r.id, r: r }; });
  if (tab === 'reports') return ((REPORTS && REPORTS.reports) || []).map(function (p, k) { return { kind: 'report', key: 'p:' + (p.slug || k), r: p }; });
  return FUTURE.map(function (f, k) { return { kind: 'future', key: 'f:' + k, r: { n: k + 1, title: f[0], text: f[1] } }; });
}
function hasStatus(tab) { return tab === 'system' || tab === 'words'; }
function haystack(it) {
  var r = it.r;
  if (it.kind === 'standing') return [r.id, r.title, r.body_md].join(' ');
  if (it.kind === 'rule') return [r.id, r.rule, r.why, r.where, r.group, r.status].join(' ');
  if (it.kind === 'report') return [r.title, r.author, r.date, r.question, r.verdict, r.bars_title,
    (r.numbers || []).map(function (n) { return [n.value, n.label, n.note].join(' '); }).join(' '),
    (r.bars || []).map(function (b) { return b.label; }).join(' ')].join(' ');
  return [r.title, r.text].join(' ');
}
function matches(it) {
  if (hasStatus(TAB) && STATUSES.some(function (s) { return STATUS_ON[s[0]]; }) && !STATUS_ON[it.r.status]) return false;
  if (QUERY && haystack(it).toLowerCase().indexOf(QUERY.toLowerCase().trim()) < 0) return false;
  return true;
}

/* ---------- metrics, tabs, chips ---------- */
function renderMetrics() {
  var all = rulesFor('system').concat(rulesFor('words'));
  var n = function (s) { return all.filter(function (r) { return r.status === s; }).length; };
  var leg = (RULES && RULES.legend) || {};
  var cards = [
    ['Rules total', String(all.length), rulesFor('system').length + ' system · ' + rulesFor('words').length + ' word & grammar'],
    ['Enforced', String(n('enforced')), leg.enforced || 'code + test'],
    ['Partly', String(n('partly')), leg.partly || 'fallback or half'],
    ['Planned', String(n('planned')), leg.planned || 'agreed, not built'],
    ['AI reports', String(((REPORTS && REPORTS.reports) || []).length), 'Research behind the rules'],
    ['Standing rules', String(((STANDING && STANDING.rules) || []).length), 'From RULES.md, change only on Medi’s word']
  ];
  var box = $('st-metrics');
  box.textContent = '';
  cards.forEach(function (c) {
    var m = el('div', 'ab-metric');
    m.appendChild(el('div', 'ab-metric-label', c[0]));
    m.appendChild(el('div', 'ab-number', c[1]));
    m.appendChild(el('div', 'ab-tiny', c[2]));
    box.appendChild(m);
  });
}
function renderTabs() {
  var box = $('st-tabs');
  box.textContent = '';
  TABS.forEach(function (t) {
    var b = el('button', 'ab-tab', t[1]);
    b.type = 'button';
    b.dataset.tab = t[0];
    b.setAttribute('aria-pressed', TAB === t[0] ? 'true' : 'false');
    b.appendChild(el('span', 'ab-count', String(items(t[0]).length)));
    b.addEventListener('click', function () { TAB = t[0]; renderTabs(); renderChips(); render(); });
    box.appendChild(b);
  });
  var note = $('st-tabnote');
  note.textContent = '';
  if (TAB === 'standing') note.textContent = (STANDING && STANDING.intro_md || '').replace(/\s+/g, ' ');
  else if (TAB === 'system') note.textContent = SYS_NOTE;
  else if (TAB === 'words') note.textContent = WORD_NOTE;
  else if (TAB === 'reports') note.textContent = REPORT_NOTE;
  else note.textContent = 'Ideas agreed for later, in order.';
}
function renderChips() {
  var box = $('st-chips');
  box.textContent = '';
  var show = hasStatus(TAB);
  box.parentNode.hidden = !show;
  if (!show) return;
  var list = items(TAB), leg = (RULES && RULES.legend) || {};
  STATUSES.forEach(function (s) {
    var b = el('button', 'ab-chip st-chip-' + s[0], s[1] + ' ' + list.filter(function (it) { return it.r.status === s[0]; }).length);
    b.type = 'button';
    b.title = leg[s[0]] || '';
    b.setAttribute('aria-pressed', STATUS_ON[s[0]] ? 'true' : 'false');
    b.addEventListener('click', function () { STATUS_ON[s[0]] = !STATUS_ON[s[0]]; renderChips(); render(); });
    box.appendChild(b);
  });
}

/* ---------- rows ---------- */
var HEADS = {
  standing: ['Id', 'Rule', 'Source', 'Kind'],
  system: ['Id', 'Rule', 'Group', 'Status'],
  words: ['Id', 'Rule', 'Group', 'Status'],
  reports: ['Date', 'Report', 'Author', 'Headline number'],
  future: ['#', 'Project', 'Source', 'Status']
};
function chip(cls, text, title) { var c = el('span', 'st-status ' + cls, text); if (title) c.title = title; return c; }
function cells(it) {
  var r = it.r;
  if (it.kind === 'standing') return [r.id, r.title, 'RULES.md', chip('st-standing', 'Standing', 'Changes only when Medi says so, in writing')];
  if (it.kind === 'rule') return [r.id, r.rule, r.group, chip('st-' + r.status, r.status, ((RULES && RULES.legend) || {})[r.status])];
  if (it.kind === 'report') {
    var n0 = (r.numbers || [])[0];
    var num = el('div');
    if (n0) { num.appendChild(el('div', 'st-kpinum', n0.value)); num.appendChild(el('div', 'ls-small st-small', n0.label)); } else num.textContent = '—';
    return [r.date, r.title, chip(r.author === 'Claude' ? 'st-claude' : 'st-codex', r.author), num];
  }
  return [String(r.n), r.title, 'index.html (old tab)', chip('st-planned', 'future')];
}
function row(it) {
  var wrap = el('article', 'ab-row st-row st-row-' + (it.r.status || it.kind));
  var head = el('button', 'ab-grid st-grid ab-rowhead st-rowhead');
  head.type = 'button';
  head.setAttribute('aria-expanded', OPEN[it.key] ? 'true' : 'false');
  var c = cells(it);
  var id = el('div', 'st-id');
  id.appendChild(el('span', 'ab-chevron', OPEN[it.key] ? '▾' : '▸'));
  id.appendChild(el('span', null, c[0]));
  head.appendChild(id);
  head.appendChild(el('div', 'st-title', c[1]));
  var grp = el('div', 'st-group');
  if (typeof c[2] === 'string') grp.textContent = c[2]; else grp.appendChild(c[2]);
  head.appendChild(grp);
  var last = el('div', 'st-last');
  if (typeof c[3] === 'string') last.textContent = c[3]; else last.appendChild(c[3]);
  head.appendChild(last);
  head.addEventListener('click', function () { OPEN[it.key] = !OPEN[it.key]; render(); });
  wrap.appendChild(head);
  if (OPEN[it.key]) wrap.appendChild(detail(it));
  return wrap;
}
function field(label, text) {
  var p = el('p', 'st-field');
  p.appendChild(el('strong', null, label + ' '));
  p.appendChild(document.createTextNode(text || '—'));
  return p;
}
function detail(it) {
  var r = it.r, d = el('div', 'ab-detail st-detail');
  if (it.kind === 'standing') {
    var body = el('div', 'st-md');
    body.innerHTML = md(r.body_md);
    d.appendChild(body);
  } else if (it.kind === 'rule') {
    d.appendChild(field('Why:', r.why));
    d.appendChild(field('Where:', r.where));
  } else if (it.kind === 'report') {
    d.appendChild(field('Question:', r.question));
    d.appendChild(field('Verdict:', r.verdict));
    if ((r.numbers || []).length) {
      var k = el('div', 'st-kpis');
      r.numbers.forEach(function (n) {
        var box = el('div', 'ab-metric st-kpi');
        box.appendChild(el('div', 'ab-number', n.value));
        box.appendChild(el('div', 'ab-tiny', n.label));
        if (n.note) box.appendChild(el('div', 'ab-tiny', n.note));
        k.appendChild(box);
      });
      d.appendChild(k);
    }
    if ((r.bars || []).length) {
      var bars = el('div', 'st-bars');
      bars.appendChild(el('div', 'ab-tiny st-barstitle', r.bars_title || ''));
      r.bars.forEach(function (b) {
        var line = el('div', 'st-brow');
        line.appendChild(el('span', 'st-blabel', b.label));
        var track = el('div', 'st-track'), fill = el('div', 'st-fill' + (b.tone ? ' st-' + b.tone : ''));
        fill.style.width = Math.max(2, Math.round(100 * b.value / (b.max || 1))) + '%';
        track.appendChild(fill);
        line.appendChild(track);
        line.appendChild(el('span', 'st-bv', b.text != null ? b.text : String(b.value)));
        bars.appendChild(line);
      });
      d.appendChild(bars);
    }
    if ((r.links || []).length) {
      var links = el('p', 'st-links');
      r.links.forEach(function (l) { var a = el('a', 'st-link', l.label); a.href = l.url; links.appendChild(a); });
      d.appendChild(links);
    }
    if (r.source_md) d.appendChild(el('p', 'ab-mini', 'Source notes: ' + r.source_md));
  } else {
    d.appendChild(el('p', 'st-field', r.text));
  }
  return d;
}

/* ---------- render ---------- */
function render() {
  var head = $('st-head');
  head.textContent = '';
  HEADS[TAB].forEach(function (h) { head.appendChild(el('div', null, h)); });
  var rows = $('st-rows');
  rows.textContent = '';
  var all = items(TAB), list = all.filter(matches);
  if (!list.length) rows.appendChild(el('div', 'ab-empty', 'Nothing matches those filters.'));
  list.forEach(function (it) { rows.appendChild(row(it)); });
  $('st-results').textContent = list.length + ' of ' + all.length + ' shown';
  var leg = (RULES && RULES.legend) || {};
  $('st-legend').textContent = hasStatus(TAB) ? 'Enforced = ' + (leg.enforced || '') + ' · Partly = ' + (leg.partly || '') + ' · Planned = ' + (leg.planned || '') : 'Tap a row to open it';
  var cov = $('st-coverage');
  if (TAB === 'standing') cov.textContent = 'Updated ' + ((STANDING && STANDING.updated) || '—') + '. Source: RULES.md (a rule changes only when Medi says so, in writing, there). Rebuilt by scripts/build_standing_rules.py.';
  else if (hasStatus(TAB)) cov.textContent = 'Updated ' + ((RULES && RULES.updated) || '—') + '. Source: docs/data/ai_rules.json (edit there, the page follows).';
  else if (TAB === 'reports') cov.textContent = 'Updated ' + ((REPORTS && REPORTS.updated) || '—') + '. Numbers are counts on frozen clips, not accuracy; no word-perfect transcript exists yet.';
  else cov.textContent = '';
  $('st-reset').hidden = !(QUERY || STATUSES.some(function (s) { return STATUS_ON[s[0]]; }));
}
function wire() {
  $('st-search').addEventListener('input', function (e) { QUERY = e.target.value; render(); });
  $('st-reset').addEventListener('click', function () {
    QUERY = ''; STATUS_ON = Object.create(null);
    $('st-search').value = '';
    renderChips(); render();
  });
}

function load(url) {
  return fetch(url + '?build=' + encodeURIComponent(BUILD)).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
}
Promise.all([load('data/standing-rules.json'), load('data/ai_rules.json'), load('data/ai_reports.json')]).then(function (res) {
  STANDING = res[0]; RULES = res[1]; REPORTS = res[2];
  var missing = [['standing-rules.json', STANDING], ['ai_rules.json', RULES], ['ai_reports.json', REPORTS]].filter(function (x) { return !x[1]; }).map(function (x) { return x[0]; });
  if (missing.length) $('st-notice').textContent = 'Missing: ' + missing.join(', ') + '. Those tabs are empty.';
  var dates = [STANDING && STANDING.updated, RULES && RULES.updated, REPORTS && REPORTS.updated].filter(Boolean).sort();
  $('st-source').textContent = dates.length ? 'Updated ' + dates[dates.length - 1] : 'Not loaded';
  try { var h = (location.hash || '').slice(1); if (TABS.some(function (t) { return t[0] === h; })) TAB = h; } catch (e) { /* default tab */ }
  renderMetrics();
  renderTabs();
  renderChips();
  wire();
  render();
});
})();
