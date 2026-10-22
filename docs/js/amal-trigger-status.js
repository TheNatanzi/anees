/* System Settings: "Amal trigger" (Medi M3, 2026-09-29). Reads docs/data/amal-trigger.json (scripts/amal_trigger.py):
   each source of Amal's input, whether it can be read unattended (and exactly why not), and the last firings with the
   numbers each one moved. */
(function () {
'use strict';
function lines(d) {
  var out = { head: 'Tutor trigger: not run yet.', sources: [], firings: [] };
  if (!d || !d.sources) return out;
  var unread = d.sources.filter(function (s) { return !s.readable; });
  out.head = 'Tutor trigger: watching ' + d.sources.length + ' sources of her answers' +
             (unread.length ? ' (' + unread.length + ' not readable unattended)' : '') + '; last check ' + String(d.checked || '').slice(0, 16).replace('T', ' ') + '.';
  out.sources = d.sources.map(function (s) {
    return (s.readable ? '✓ ' : '✗ ') + s.label + (s.readable ? (s.n != null ? ' - ' + s.n + ' item(s)' : '') : ' - ' + s.why) + (s.note ? ' (' + s.note + ')' : '');
  });
  out.firings = (d.firings || []).map(function (f) {
    var moved = (f.numbers_moved || []).map(function (m) { return m.what + ' ' + (m.from == null ? '-' : m.from) + ' → ' + (m.to == null ? '-' : m.to); });
    return String(f.at || '').slice(0, 16).replace('T', ' ') + ': ' + (f.changed || []).map(function (c) { return c.label; }).join(', ') +
           ' changed' + (f.failures && f.failures.length ? ' - FAILED: ' + f.failures.join('; ') : '') +
           (moved.length ? ' - moved: ' + moved.join('; ') : ' - no headline number moved') +
           (f.published ? ' - publish: ' + f.published : '');
  });
  return out;
}
if (typeof module !== 'undefined' && module.exports) { module.exports = { lines: lines }; return; }

  // de-word: warnings gather in one 'Needs attention' card above the two robots (created by whichever script runs first);
  // each row = what is wrong (big) + the next step (one line), the raw detail behind an i that opens in place
  function attnRow(big, small, detail, first) {
    var host = document.getElementById('st-guard'); if (!host) return;
    var card = document.getElementById('st-attn');
    if (!card) { card = document.createElement('section'); card.id = 'st-attn'; card.className = 'st-attn';
      card.innerHTML = '<h2 class="st-attn-h">Needs attention</h2>'; host.parentNode.insertBefore(card, host); }
    var row = document.createElement('div'); row.className = 'st-attn-row';
    row.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M4 20L20 4"/></svg><div><b></b><small></small></div>';
    row.querySelector('b').textContent = big; row.querySelector('small').textContent = small;
    // round 2 (Medi: too much cut): the raw detail is a visible small line, not behind an i
    if (detail) { var dv = document.createElement('small'); dv.className = 'st-attn-det'; dv.textContent = detail; row.querySelector('div').appendChild(dv); }
    if (first) card.insertBefore(row, card.children[1] || null); else card.appendChild(row);
  }
function render(d) {
  var host = document.getElementById('st-guard'); if (!host) return;
  var box = document.createElement('div'); box.className = 'ab-sub st-amal'; box.id = 'st-amal';
  // de-word: chips (count, a warning when a source cannot be read, last check); the sentence and her sources open in place
  var L = lines(d), unread = d && d.sources ? d.sources.filter(function (s) { return !s.readable; }).length : 0;
  var p = document.createElement('span'); p.className = 'dw-chip' + (d && d.sources ? '' : ' muted');
  p.textContent = d && d.sources ? 'Tutor trigger ' + (unread ? 'running' : 'OK') : 'Tutor trigger · not run yet';
  box.appendChild(p);
  var tx = document.createElement('span'); tx.className = 'st-line'; tx.textContent = ' ' + L.head; box.appendChild(tx);
  if (unread) attnRow(unread + ' tutor source' + (unread === 1 ? '' : 's') + ' not readable',
    'Next: fix access to ' + d.sources.filter(function (s) { return !s.readable; }).map(function (s) { return s.label; }).join(', ') + '.',
    d.sources.filter(function (s) { return !s.readable; }).map(function (s) { return s.label + ': ' + s.why; }).join(' · '));
  var det = document.createElement('details'), sum = document.createElement('summary');
  det.className = 'dw-info'; sum.textContent = 'i'; sum.title = 'Her sources and the last recalculations'; det.appendChild(sum);
  var ul = document.createElement('ul');
  L.sources.concat(L.firings.length ? L.firings : ['No firing yet: nothing of hers has changed since the trigger started.']).forEach(function (t) {
    var li = document.createElement('li'); li.textContent = t; ul.appendChild(li); });
  var wrap = document.createElement('div'); wrap.appendChild(ul); det.appendChild(wrap); box.appendChild(det); host.insertAdjacentElement('afterend', box);
}
var build = window.ANEES_SETTINGS_BUILD || String(Date.now());
fetch('data/amal-trigger.json?build=' + encodeURIComponent(build), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(render, function () { render(null); });
})();
