/* Rule book (rule PG-16, Medi 2026-10-02: "Lets keep a parrallel document of the rules ... so I can read it and
   follow it"). Reads docs/data/rule-book.json, which scripts/build_rule_book.py builds from rules/registry.json and
   RULES.md (never edited by hand). Reading order = the life of a lesson; each rule is one plain sentence, its id
   small and grey, the words Medi or Amal said, and a badge. Search and the badge chips only hide rules, never reorder. */
(function () {
'use strict';

var BOOK = null, QUERY = '', ON = Object.create(null);
var TONE = { 'enforced': 'auto', 'written': 'written', 'moment-only': 'once', 'needs-medi': 'you' };
var $ = function (id) { return document.getElementById(id); };
function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function norm(s) { return String(s == null ? '' : s).toLowerCase(); }
function hay(x) {
  return norm([x.id, x.text, x.topic, x.badge,
    (x.said || []).map(function (p) { return p.who + ' ' + p.date + ' ' + p.quote; }).join(' '),
    x.question ? x.question.ask : '', x.replaced_by ? x.replaced_by.id + ' ' + x.replaced_by.text : ''].join(' '));
}
function filtering() { return !!(QUERY.trim() || Object.keys(ON).some(function (k) { return ON[k]; })); }
function shows(x) {
  var anyBadge = Object.keys(ON).some(function (k) { return ON[k]; });
  if (anyBadge && !ON[x.status]) return false;
  var q = norm(QUERY).trim();
  if (q && q.split(/\s+/).some(function (w) { return hay(x).indexOf(w) < 0; })) return false;
  return true;
}

function badge(x) {
  var b = el('span', 'rb-badge rb-' + (TONE[x.status] || 'old'), x.badge || 'Replaced');
  var m = (BOOK.badges || []).filter(function (y) { return y.status === x.status; })[0];
  if (m) b.title = m.means;
  return b;
}
function saidLine(x) {
  var line = el('div', 'rb-said');
  if (x.said && x.said.length) {
    x.said.forEach(function (p, k) {
      if (k) line.appendChild(el('span', 'rb-sep', ' · '));
      var s = el('span', 'rb-quote');
      s.appendChild(el('span', 'rb-who', p.who + ', ' + p.date + ': '));
      var q = /^\(/.test(p.quote) ? p.quote : '“' + p.quote + '”';
      s.appendChild(el('span', 'rb-words', q));
      line.appendChild(s);
    });
  } else if ('claude' in x) {
    line.appendChild(el('span', 'rb-who', 'Written by Claude' + (x.claude ? ', ' + x.claude : '') + ' (not Medi’s or Amal’s words)'));
  }
  return line;
}
function ruleItem(x) {
  var li = el('li', 'rb-rule rb-rule-' + (TONE[x.status] || 'old'));
  li.appendChild(el('p', 'rb-text', x.text));
  var meta = el('div', 'rb-meta');
  meta.appendChild(badge(x));
  meta.appendChild(el('span', 'rb-id', x.id));
  li.appendChild(meta);
  var said = saidLine(x);
  if (said.childNodes.length) li.appendChild(said);
  if (x.question) {
    var q = el('div', 'rb-ask');
    q.appendChild(el('strong', null, 'Your call: '));
    q.appendChild(document.createTextNode(x.question.ask + ' (' + x.question.options.join(' / ') + ')'));
    li.appendChild(q);
  }
  return li;
}
function oldItem(x) {
  var li = el('li', 'rb-rule rb-rule-old');
  li.appendChild(el('p', 'rb-text rb-struck', x.text));
  var meta = el('div', 'rb-meta');
  meta.appendChild(el('span', 'rb-id', x.id));
  li.appendChild(meta);
  if (x.replaced_by) {
    var r = el('div', 'rb-replaced');
    r.appendChild(el('strong', null, 'Replaced by ' + x.replaced_by.id + ': '));
    r.appendChild(document.createTextNode(x.replaced_by.text));
    li.appendChild(r);
  }
  var said = saidLine(x);
  if (said.childNodes.length) li.appendChild(said);
  return li;
}

function renderBadges() {
  var box = $('rb-badges');
  box.textContent = '';
  (BOOK.badges || []).forEach(function (b) {
    var c = el('button', 'ab-chip rb-chip rb-chip-' + TONE[b.status]);
    c.type = 'button';
    c.title = b.means;
    c.setAttribute('aria-pressed', ON[b.status] ? 'true' : 'false');
    c.appendChild(el('span', 'rb-dot', ''));
    c.appendChild(document.createTextNode(b.badge + ' '));
    c.appendChild(el('strong', null, String((BOOK.counts || {})[b.badge] || 0)));
    c.addEventListener('click', function () { ON[b.status] = !ON[b.status]; renderBadges(); render(); });
    box.appendChild(c);
  });
}
function renderHelp() {
  var body = $('rb-helpbody');
  body.textContent = '';
  var ul = el('ul', 'rb-legend');
  (BOOK.badges || []).forEach(function (b) {
    var li = el('li');
    li.appendChild(badge({ status: b.status, badge: b.badge }));
    li.appendChild(document.createTextNode(' ' + b.means.charAt(0).toUpperCase() + b.means.slice(1) + '.'));
    ul.appendChild(li);
  });
  body.appendChild(ul);
  var dl = el('ul', 'rb-legend');
  (BOOK.glossary || []).forEach(function (g) {
    var li = el('li');
    li.appendChild(el('strong', null, g.term + ': '));
    li.appendChild(document.createTextNode(g.means));
    dl.appendChild(li);
  });
  body.appendChild(dl);
}
function renderToc(counts) {
  var box = $('rb-toc');
  box.textContent = '';
  var a0 = el('a', 'rb-tocitem', 'The big rules');
  a0.href = '#big';
  box.appendChild(a0);
  BOOK.groups.forEach(function (g) {
    var a = el('a', 'rb-tocitem' + (counts[g.key] ? '' : ' rb-none'));
    a.href = '#' + g.key;
    a.appendChild(document.createTextNode(g.n + ' ' + g.title.replace(/:.*$/, '')));
    a.appendChild(el('span', 'ab-count', String(counts[g.key] || 0)));
    box.appendChild(a);
  });
}

function render() {
  var book = $('rb-book');
  book.textContent = '';
  var shown = 0, total = 0, counts = {};
  var q = norm(QUERY).trim();

  var big = (BOOK.big_rules || []).filter(function (b) {
    return !filtering() || (!Object.keys(ON).some(function (k) { return ON[k]; }) && q && q.split(/\s+/).every(function (w) { return norm(b.id + ' ' + b.title + ' ' + b.text + ' ' + b.rule).indexOf(w) >= 0; }));
  });
  if (big.length) {
    var sec = el('section', 'rb-group rb-big');
    sec.id = 'big';
    sec.appendChild(el('h2', 'rb-h2', 'The big rules'));
    sec.appendChild(el('p', 'rb-intro', 'The rules that sit above all the others. Only you change them, in writing.'));
    var ol = el('ol', 'rb-biglist');
    big.forEach(function (b) {
      var li = el('li');
      var t = el('p', 'rb-bigtitle');
      t.appendChild(el('span', 'rb-id', b.id));
      t.appendChild(document.createTextNode(' ' + b.title));
      li.appendChild(t);
      li.appendChild(el('p', 'rb-text', b.text));
      ol.appendChild(li);
    });
    sec.appendChild(ol);
    book.appendChild(sec);
  }

  BOOK.groups.forEach(function (g) {
    var sec = el('section', 'rb-group');
    sec.id = g.key;
    var h = el('h2', 'rb-h2');
    h.appendChild(el('span', 'rb-num', String(g.n)));
    h.appendChild(document.createTextNode(g.title));
    sec.appendChild(h);
    sec.appendChild(el('p', 'rb-intro', g.intro));
    var n = 0;
    g.sections.forEach(function (s) {
      total += s.rules.length;
      var list = s.rules.filter(shows);
      if (!list.length) return;
      n += list.length;
      sec.appendChild(el('h3', 'rb-h3 rb-kind-' + s.kind, s.heading));
      var ul = el('ul', 'rb-list');
      list.forEach(function (x) { ul.appendChild(ruleItem(x)); });
      sec.appendChild(ul);
    });
    var badgeOn = Object.keys(ON).some(function (k) { return ON[k]; });
    var old = badgeOn ? [] : (g.old || []).filter(shows);
    if (old.length) {
      var d = el('details', 'rb-oldbox');
      if (q) d.open = true;
      d.appendChild(el('summary', null, 'Old rules (replaced) · ' + old.length));
      var ol2 = el('ul', 'rb-list');
      old.forEach(function (x) { ol2.appendChild(oldItem(x)); });
      d.appendChild(ol2);
      sec.appendChild(d);
    }
    counts[g.key] = n;
    shown += n;
    if (n || old.length) book.appendChild(sec);
  });
  if (!book.childNodes.length) book.appendChild(el('div', 'ab-empty', 'No rule matches that. Try a shorter word.'));
  $('rb-results').textContent = filtering() ? shown + ' of ' + total + ' rules shown' : total + ' rules';
  $('rb-reset').hidden = !filtering();
  renderToc(counts);
}

function wire() {
  $('rb-search').addEventListener('input', function (e) { QUERY = e.target.value; render(); });
  $('rb-reset').addEventListener('click', function () {
    QUERY = ''; ON = Object.create(null); $('rb-search').value = '';
    renderBadges(); render();
  });
}

fetch('data/rule-book.json', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }).then(function (b) {
  if (!b || !b.groups) { $('rb-notice').textContent = 'The rule book could not load. Please refresh to retry.'; $('rb-updated').textContent = 'Not loaded'; return; }
  BOOK = b;
  $('rb-updated').textContent = 'Last updated ' + b.updated;
  $('rb-foot').textContent = 'Built from rules/registry.json and RULES.md by scripts/build_rule_book.py, every hour. '
    + (b.replaced || 0) + ' old rules are kept under "Old rules (replaced)". The same book on GitHub: RULE-BOOK.md.';
  renderBadges();
  renderHelp();
  wire();
  render();
  if (location.hash) { var t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); }
});
})();
