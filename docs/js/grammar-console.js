/* Grammar Console. Reads docs/data/grammar-console.json only.
   Never invents a number: a rule with no recorded use renders as Untested. */
(function () {
'use strict';

var DATA = null, OPEN = Object.create(null), WRONGONLY = Object.create(null);
var PERIOD = 'all', FAMILY = 'all', SORT = 'order', QUERY = '';
var STATUS_ON = Object.create(null);
var STATUSES = ['Mastered', 'Good', 'Shaky', 'Wrong', 'Untested'];
var FAMILY_ORDER = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 5 };
var SHOW = 5;

var $ = function (id) { return document.getElementById(id); };
function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
// The --ab-* palette is declared on #anees-bank, not :root.
function css(name, fallback) {
  var host = $('anees-bank') || document.documentElement;
  var v = getComputedStyle(host).getPropertyValue(name).trim();
  return v || fallback;
}
function isArabic(s) { return /[؀-ۿ]/.test(s || ''); }
function pretty(d) {
  if (!d) return '';
  var p = d.split('-');
  return new Date(+p[0], +p[1] - 1, +p[2]).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/* ---------- period ---------- */
// The window is measured back from the newest lesson on record, not from
// today's clock: a gap in lessons should not silently empty the charts.
function lessonsInPeriod() {
  var all = (DATA.lessons || []).slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; });
  if (PERIOD === 'all' || !all.length) return all;
  var days = PERIOD === 'week' ? 7 : 31;
  var last = all[all.length - 1].date.split('-').map(Number);
  var end = Date.UTC(last[0], last[1] - 1, last[2]);
  return all.filter(function (L) {
    var p = L.date.split('-').map(Number);
    return (end - Date.UTC(p[0], p[1] - 1, p[2])) / 86400000 < days;
  });
}
function eventsInPeriod(rule) {
  var keep = {};
  lessonsInPeriod().forEach(function (L) { keep[L.date] = 1; });
  return (rule.events || []).filter(function (e) { return keep[e.date]; });
}

/* ---------- charts ---------- */
function sparkline(values, opts) {
  opts = opts || {};
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  var W = 100, H = 40;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('role', 'img');
  if (opts.label) svg.setAttribute('aria-label', opts.label);
  var nums = values.filter(function (v) { return typeof v === 'number'; });
  if (!nums.length) return null;
  var max = opts.max != null ? opts.max : Math.max.apply(null, nums);
  var lo = 0, hi = max > 0 ? max : 1;
  var n = values.length;

  if (opts.bars) {
    var gap = n > 1 ? 3 : 0;
    var w = (W - gap * (n - 1)) / n;
    values.forEach(function (v, i) {
      if (typeof v !== 'number') return;
      var h = Math.max(1.5, (v - lo) / (hi - lo) * (H - 4));
      var r = document.createElementNS(svg.namespaceURI, 'rect');
      r.setAttribute('x', (i * (w + gap)).toFixed(2));
      r.setAttribute('y', (H - h).toFixed(2));
      r.setAttribute('width', w.toFixed(2));
      r.setAttribute('height', h.toFixed(2));
      r.setAttribute('rx', '1.5');
      r.setAttribute('class', 'gc-bar' + (i === n - 1 ? ' gc-bar-last' : ''));
      svg.appendChild(r);
    });
  } else {
    var pts = [];
    values.forEach(function (v, i) {
      if (typeof v !== 'number') return;
      var x = n === 1 ? W / 2 : (i / (n - 1)) * W;
      var y = H - 2 - ((v - lo) / (hi - lo)) * (H - 4);
      pts.push([x, y]);
    });
    if (pts.length > 1) {
      var path = document.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute('d', 'M' + pts.map(function (p) { return p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' L'));
      path.setAttribute('class', 'gc-line');
      svg.appendChild(path);
    }
    pts.forEach(function (p, i) {
      var c = document.createElementNS(svg.namespaceURI, 'circle');
      c.setAttribute('cx', p[0].toFixed(1));
      c.setAttribute('cy', p[1].toFixed(1));
      c.setAttribute('r', i === pts.length - 1 ? '3' : '2');
      c.setAttribute('class', 'gc-dot');
      svg.appendChild(c);
    });
  }
  return svg;
}

function donut(slices) {
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 42 42');
  svg.setAttribute('role', 'img');
  var total = slices.reduce(function (a, s) { return a + s.value; }, 0);
  if (!total) return null;
  svg.setAttribute('aria-label', slices.map(function (s) { return s.value + ' ' + s.label; }).join(', '));
  var R = 15.9155, C = 2 * Math.PI * R, offset = 0;
  slices.forEach(function (s) {
    if (!s.value) return;
    var len = (s.value / total) * C;
    var c = document.createElementNS(svg.namespaceURI, 'circle');
    c.setAttribute('cx', '21'); c.setAttribute('cy', '21'); c.setAttribute('r', String(R));
    c.setAttribute('fill', 'none');
    c.setAttribute('stroke', s.color);
    c.setAttribute('stroke-width', '7');
    c.setAttribute('stroke-dasharray', len.toFixed(2) + ' ' + (C - len).toFixed(2));
    c.setAttribute('stroke-dashoffset', (C - offset + C / 4).toFixed(2));
    svg.appendChild(c);
    offset += len;
  });
  return svg;
}

function blank(msg) { return el('div', 'gc-blank', msg); }

function renderCharts() {
  var L = lessonsInPeriod();
  var range = PERIOD === 'week' ? 'last 7 days' : PERIOD === 'month' ? 'last month' : 'all lessons';

  function fill(box, value, node, foot) {
    var v = $('gc-' + box + '-value'), b = $('gc-' + box + '-body'), f = $('gc-' + box + '-foot');
    if (v) v.textContent = value;
    b.textContent = '';
    b.appendChild(node || blank('No lessons scored in this range'));
    f.textContent = '';
    if (foot) f.appendChild(foot);
  }
  function foot(text, delta) {
    var w = el('span', null, text);
    if (delta) {
      var d = el('span', delta.good ? 'gc-delta-good' : 'gc-delta-bad', ' ' + delta.text);
      w.appendChild(d);
    }
    return w;
  }

  function sum(key) {
    return L.reduce(function (a, x) { return a + (typeof x[key] === 'number' ? x[key] : 0); }, 0);
  }
  var latest = L.length ? pretty(L[L.length - 1].date) : '';

  // 1 - grammar mistakes per sentence, pooled over the range (not a mean of ratios)
  var mps = L.map(function (x) { return x.mistakes_per_sentence; });
  var sentences = sum('medi_sentences');
  var rate = sentences ? sum('slips_counted') / sentences : null;
  fill('c1', rate == null ? '—' : rate.toFixed(3),
    L.length ? sparkline(mps, { label: 'Mistakes per sentence by lesson' }) : null,
    L.length ? foot(sum('slips_counted') + ' slips in ' + sentences + ' sentences · ' +
      L.length + ' lessons · latest ' + latest) : null);

  // 2 - self-correction rate, pooled over the range
  var sc = L.map(function (x) { return x.self_correction_rate; });
  var caught = sum('asks'), missed = sum('slips_counted');
  var scPct = (caught + missed) ? Math.round(100 * caught / (caught + missed)) : null;
  fill('c2', scPct == null ? '—' : scPct + '%',
    L.length ? sparkline(sc, { bars: true, max: 100, label: 'Self-correction rate by lesson' }) : null,
    L.length ? foot(caught + ' asked or caught by you · ' + missed + ' corrected by Amal') : null);

  // 3 - unique rules per lesson, averaged over the range
  var uq = L.map(function (x) { return x.unique_rules; });
  var avg = L.length ? sum('unique_rules') / L.length : null;
  fill('c3', avg == null ? '—' : (Math.round(avg * 10) / 10).toFixed(1),
    L.length ? sparkline(uq, { bars: true, label: 'Unique rules used by lesson' }) : null,
    L.length ? foot('Average per lesson · out of ' + DATA.coverage.buckets_total +
      ' buckets · latest ' + latest) : null);

  // 4 - status mix across every bucket
  var counts = {};
  STATUSES.forEach(function (s) { counts[s] = 0; });
  DATA.rules.forEach(function (r) { counts[r.status] = (counts[r.status] || 0) + 1; });
  var colors = {
    Mastered: css('--ab-green', '#5B8C6E'), Good: css('--ab-blue', '#4E7FA8'),
    Shaky: css('--ab-orange', '#C98A3E'), Wrong: css('--ab-red', '#C4573C'),
    Untested: css('--ab-line', '#CFC9BC')
  };
  var slices = STATUSES.map(function (s) { return { label: s, value: counts[s], color: colors[s] }; });
  var body = $('gc-c4-body');
  body.textContent = '';
  var d = donut(slices);
  if (d) body.appendChild(d);
  var legend = el('div', 'gc-legend');
  slices.forEach(function (s) {
    var row = el('div');
    var sw = el('span', 'gc-swatch'); sw.style.background = s.color;
    row.appendChild(sw);
    row.appendChild(el('span', null, s.value + ' ' + s.label));
    legend.appendChild(row);
  });
  body.appendChild(legend);
  $('gc-c4-foot').textContent = 'Status never moves on its own — it needs a recorded use.';
}

/* ---------- rule rows ---------- */
function visibleRules() {
  var q = QUERY.trim().toLowerCase();
  var out = DATA.rules.filter(function (r) {
    if (FAMILY !== 'all' && r.family !== FAMILY) return false;
    var anyStatus = STATUSES.some(function (s) { return STATUS_ON[s]; });
    if (anyStatus && !STATUS_ON[r.status]) return false;
    if (!q) return true;
    var hay = [r.id, r.name, r.one_line, r.why].concat(
      (r.examples || []).map(function (e) { return e.join(' '); }),
      r.more || []
    ).join(' ').toLowerCase();
    return hay.indexOf(q) >= 0;
  });
  out.sort(function (a, b) {
    if (SORT === 'weak') return (a.pct == null ? 999 : a.pct) - (b.pct == null ? 999 : b.pct) || a.id.localeCompare(b.id);
    if (SORT === 'used') return b.uses - a.uses || a.id.localeCompare(b.id);
    if (SORT === 'recent') return String(b.last_used || '').localeCompare(String(a.last_used || '')) || a.id.localeCompare(b.id);
    if (SORT === 'mistakes') return b.mistakes - a.mistakes || a.id.localeCompare(b.id);
    return FAMILY_ORDER[a.family] - FAMILY_ORDER[b.family] || (+a.id.slice(1)) - (+b.id.slice(1));
  });
  return out;
}

function useCard(e) {
  var card = el('div', 'gc-use gc-use-' + e.kind);
  var head = el('div', 'gc-usehead');
  var left = el('span');
  var tag = el('span', 'gc-tag', e.kind === 'slip' ? 'Amal corrected you' : e.kind === 'right' ? 'Correct' : 'You asked');
  left.appendChild(tag);
  head.appendChild(left);
  head.appendChild(el('span', null, pretty(e.date) + (e.mmss ? ' · ' + e.mmss : '')));
  card.appendChild(head);

  // said_html / recast_html carry <mark> spans from the audit. They are built
  // by our own script from the transcript, so the markup is ours, not a page's.
  var said = el('p', 'gc-said');
  if (e.said_html) said.innerHTML = e.said_html; else said.textContent = e.said || '—';
  if (isArabic(e.said)) { said.setAttribute('dir', 'rtl'); said.setAttribute('lang', 'ar'); }
  card.appendChild(said);

  if (e.recast || e.recast_html) {
    var rc = el('p', 'gc-recast');
    rc.appendChild(el('span', null, e.kind === 'slip' ? 'Amal said: ' : 'Amal: '));
    var b = el('b');
    if (e.recast_html) b.innerHTML = e.recast_html; else b.textContent = e.recast;
    if (isArabic(e.recast)) { b.setAttribute('dir', 'rtl'); b.setAttribute('lang', 'ar'); }
    rc.appendChild(b);
    if (e.recast_at) rc.appendChild(el('span', null, '  (' + e.recast_at + ')'));
    card.appendChild(rc);
  }

  if (e.clip) {
    var a = document.createElement('audio');
    a.controls = true;
    a.preload = 'none';
    a.src = 'lessons/' + e.clip;
    card.appendChild(a);
  } else if (e.audio_note) {
    card.appendChild(el('div', 'gc-noaudio', e.audio_note));
  }
  return card;
}

function detail(r) {
  var d = el('div', 'gc-detail');

  d.appendChild(el('h3', 'gc-secttitle', 'What the rule is'));
  d.appendChild(el('p', 'gc-why', r.why));

  if (r.examples && r.examples.length) {
    d.appendChild(el('h3', 'gc-secttitle', 'Examples'));
    var grid = el('div', 'gc-examples');
    r.examples.forEach(function (ex) {
      var c = el('div', 'gc-example');
      c.appendChild(el('div', 'gc-ex-ar', ex[0]));
      c.appendChild(el('div', 'gc-ex-en', ex[1]));
      grid.appendChild(c);
    });
    d.appendChild(grid);
  }

  if (r.more && r.more.length) {
    d.appendChild(el('h3', 'gc-secttitle', 'The detail'));
    var ul = el('ul', 'gc-more');
    r.more.forEach(function (m) { ul.appendChild(el('li', null, m)); });
    d.appendChild(ul);
  }

  // recorded uses
  var all = eventsInPeriod(r);
  var head = el('div', 'gc-useshead');
  head.appendChild(el('h3', 'gc-secttitle', 'Your last ' + SHOW + ' uses'));
  var toggle = el('button', 'gc-toggle', 'Only show wrong');
  toggle.type = 'button';
  toggle.setAttribute('aria-pressed', WRONGONLY[r.id] ? 'true' : 'false');
  toggle.addEventListener('click', function () {
    WRONGONLY[r.id] = !WRONGONLY[r.id];
    render();
  });
  head.appendChild(toggle);
  d.appendChild(head);

  var list = WRONGONLY[r.id] ? all.filter(function (e) { return e.kind === 'slip'; }) : all;
  if (!list.length && !WRONGONLY[r.id] && r.usage && r.usage.length) {
    // no hand-checked uses: show where the usage pass saw him use the rule
    r.usage.slice(0, SHOW).forEach(function (u) {
      var card = el('div', 'gc-use');
      var hd = el('div', 'gc-usehead');
      hd.appendChild(el('span', 'gc-tag', 'You used it'));
      hd.appendChild(el('span', null, pretty(u.date) + ' · ' + u.mmss));
      card.appendChild(hd);
      var p = el('p', 'gc-said');
      p.textContent = u.said || '';
      if (isArabic(u.said)) { p.setAttribute('dir', 'auto'); }
      card.appendChild(p);
      if (u.hit) card.appendChild(el('div', 'gc-pairline', u.hit));
      d.appendChild(card);
    });
    if (r.usage_total > SHOW) d.appendChild(el('p', 'ab-mini', 'Showing ' + SHOW + ' of ' + r.usage_total + ' uses.'));
  } else if (!list.length) {
    d.appendChild(el('div', 'gc-empty', all.length
      ? 'No wrong uses on record for this rule in this range.'
      : r.tally_rule
        ? 'Nothing recorded in this range. Widen the range to All.'
        : 'No detector for this rule yet, so nothing is counted. It stays Untested until one lands.'));
  } else {
    list.slice(0, SHOW).forEach(function (e) { d.appendChild(useCard(e)); });
    if (list.length > SHOW) {
      d.appendChild(el('p', 'ab-mini', 'Showing ' + SHOW + ' of ' + list.length + ' recorded uses.'));
    }
  }

  // Machine-found candidates. Never scored - they wait for a human tick.
  var cand = r.candidates || [];
  if (cand.length) {
    var ch = el('div', 'gc-useshead');
    ch.appendChild(el('h3', 'gc-secttitle', 'Found by the audit — machine, not yet checked (' + cand.length + ')'));
    d.appendChild(ch);
    d.appendChild(el('p', 'ab-mini gc-candnote',
      'The machine spotted these in your transcripts and they count in the numbers above. ' +
      'Checked against hand-labelled lessons, about 85 in 100 are real corrections and about 7 in 10 sit in the right rule.'));
    cand.slice(0, SHOW).forEach(function (c) {
      var card = el('div', 'gc-use gc-cand gc-conf-' + c.confidence);
      var head = el('div', 'gc-usehead');
      var left = el('span');
      left.appendChild(el('span', 'gc-tag gc-conf-tag', c.confidence + ' confidence'));
      left.appendChild(el('span', 'gc-tag', c.why));
      head.appendChild(left);
      head.appendChild(el('span', null, pretty(c.date) + ' · ' + c.mmss));
      card.appendChild(head);

      var m = el('p', 'gc-said');
      m.innerHTML = c.said_html;
      m.setAttribute('dir', 'rtl'); m.setAttribute('lang', 'ar');
      card.appendChild(m);

      var a = el('p', 'gc-recast');
      a.appendChild(el('span', null, 'Amal: '));
      var bb = el('b');
      bb.innerHTML = c.recast_html;
      bb.setAttribute('dir', 'rtl'); bb.setAttribute('lang', 'ar');
      a.appendChild(bb);
      card.appendChild(a);

      card.appendChild(el('div', 'gc-pairline',
        c.pair_wrong + '  →  ' + c.pair_fixed));
      if (c.clip) {
        // a short clip cut from just before he spoke to a few seconds after her fix
        var au = document.createElement('audio');
        au.controls = true;
        au.preload = 'none';
        au.src = 'lessons/' + c.clip;
        card.appendChild(au);
      }
      d.appendChild(card);
    });
    if (cand.length > SHOW) {
      d.appendChild(el('p', 'ab-mini', 'Showing ' + SHOW + ' of ' + cand.length + ' candidates.'));
    }
  }
  return d;
}


function row(r) {
  var wrap = el('div', 'gc-row gc-row-' + r.status);
  var head = el('button', 'gc-grid gc-rowhead');
  head.type = 'button';
  head.setAttribute('aria-expanded', OPEN[r.id] ? 'true' : 'false');

  var c1 = el('div');
  var name = el('div', 'gc-name');
  name.appendChild(el('span', 'gc-id', r.id));
  name.appendChild(el('span', null, r.name));
  c1.appendChild(name);
  c1.appendChild(el('div', 'gc-oneline', r.one_line.replace(/`/g, '')));
  head.appendChild(c1);

  var used = el('div', 'gc-num', r.uses ? String(r.uses) : '—');
  used.appendChild(el('small', null, r.uses ? 'times used' : 'never used'));
  head.appendChild(used);

  var miss = el('div', 'gc-num', r.uses ? String(r.mistakes) : '—');
  miss.appendChild(el('small', null, r.verified_slips
    ? r.verified_slips + ' confirmed' : 'corrections'));
  head.appendChild(miss);

  var score = el('div', 'gc-num', r.pct == null ? '—' : r.pct + '%');
  var meter = el('div', 'gc-meter');
  var bar = el('i');
  bar.style.width = (r.pct == null ? 0 : r.pct) + '%';
  bar.style.background = css('--ab-' + (r.status === 'Mastered' ? 'green' : r.status === 'Good' ? 'blue' : r.status === 'Shaky' ? 'orange' : 'red'), '#999');
  meter.appendChild(bar);
  score.appendChild(meter);
  head.appendChild(score);

  var st = el('div');
  st.appendChild(el('div', 'gc-pill gc-pill-' + r.status, r.status));
  head.appendChild(st);

  var last = el('div', 'gc-last');
  if (r.last_used) {
    last.appendChild(el('div', null, pretty(r.last_used)));
    last.appendChild(el('small', null, r.last_used_mmss || ''));
  } else {
    last.appendChild(el('div', 'gc-muted', '—'));
  }
  head.appendChild(last);

  head.addEventListener('click', function () { OPEN[r.id] = !OPEN[r.id]; render(); });
  wrap.appendChild(head);
  if (OPEN[r.id]) wrap.appendChild(detail(r));
  return wrap;
}

/* ---------- render ---------- */
function render() {
  renderCharts();
  var rows = $('gc-rows');
  rows.textContent = '';
  var list = visibleRules();
  if (!list.length) {
    rows.appendChild(el('div', 'gc-empty', 'No rule matches those filters.'));
  } else {
    list.forEach(function (r) { rows.appendChild(row(r)); });
  }
  $('gc-results').textContent = list.length + ' of ' + DATA.rules.length + ' rules';
  var filtered = QUERY || FAMILY !== 'all' || STATUSES.some(function (s) { return STATUS_ON[s]; });
  $('gc-reset').hidden = !filtered;
}

function buildStatusChips() {
  var box = $('gc-statuses');
  var counts = {};
  DATA.rules.forEach(function (r) { counts[r.status] = (counts[r.status] || 0) + 1; });
  STATUSES.forEach(function (s) {
    var b = el('button', 'ab-chip', s + ' ' + (counts[s] || 0));
    b.type = 'button';
    b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', function () {
      STATUS_ON[s] = !STATUS_ON[s];
      b.setAttribute('aria-pressed', STATUS_ON[s] ? 'true' : 'false');
      render();
    });
    box.appendChild(b);
  });
}

function wire() {
  Array.prototype.forEach.call(document.querySelectorAll('.gc-period'), function (b) {
    b.addEventListener('click', function () {
      PERIOD = b.dataset.period;
      Array.prototype.forEach.call(document.querySelectorAll('.gc-period'), function (o) {
        o.setAttribute('aria-pressed', o === b ? 'true' : 'false');
      });
      render();
    });
  });
  $('gc-search').addEventListener('input', function (e) { QUERY = e.target.value; render(); });
  $('gc-family').addEventListener('change', function (e) { FAMILY = e.target.value; render(); });
  $('gc-sort').addEventListener('change', function (e) { SORT = e.target.value; render(); });
  $('gc-reset').addEventListener('click', function () {
    QUERY = ''; FAMILY = 'all';
    $('gc-search').value = ''; $('gc-family').value = 'all';
    STATUSES.forEach(function (s) { STATUS_ON[s] = false; });
    Array.prototype.forEach.call($('gc-statuses').children, function (b) { b.setAttribute('aria-pressed', 'false'); });
    render();
  });
}

/* Amal's own grammar tabs, carried over from the retired index.html#grammar. */
function renderDoc() {
  var box = $('gc-doc-body');
  fetch('data/grammar.json?v=' + Date.now())
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (g) {
      box.textContent = '';
      var tab = null;
      (g.sections || []).forEach(function (s) {
        if (s.tab !== tab) {
          tab = s.tab;
          box.appendChild(el('h3', 'gc-doc-tab', tab));
        }
        box.appendChild(el('h4', 'gc-doc-head', s.heading));
        var ul = el('ul', 'gc-doc-list');
        (s.lines || []).forEach(function (line) { ul.appendChild(el('li', null, line)); });
        box.appendChild(ul);
      });
      box.appendChild(el('p', 'ab-mini', 'Source: ' + (g.source || 'Amal’s Doc')));
    })
    .catch(function (err) { box.textContent = 'Could not load Amal’s notes: ' + err.message; });
}

fetch('data/grammar-console.json?v=' + Date.now())
  .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  .then(function (json) {
    DATA = json;
    var c = DATA.coverage;
    $('gc-source').textContent = c.buckets_scored + ' of ' + c.buckets_total + ' rules scored';
    $('gc-notice').textContent =
      'Scored from ' + c.lessons_scored + ' of ' + c.lessons_recorded +
      ' recorded lessons. ' + c.note;
    $('gc-coverage').textContent = 'Source: ' + DATA.source + ' · updated ' + DATA.updated;
    buildStatusChips();
    wire();
    render();
    renderDoc();
  })
  .catch(function (err) {
    $('gc-notice').textContent = 'Could not load the grammar data: ' + err.message;
    $('gc-source').textContent = 'Failed to load';
  });
})();
