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
function render(d) {
  var host = document.getElementById('st-guard'); if (!host) return;
  var box = document.createElement('div'); box.className = 'ab-sub st-amal'; box.id = 'st-amal';
  var L = lines(d), p = document.createElement('span'); p.textContent = L.head; box.appendChild(p);
  var det = document.createElement('details'), sum = document.createElement('summary');
  sum.textContent = 'Her sources and the last recalculations'; det.appendChild(sum);
  var ul = document.createElement('ul');
  L.sources.concat(L.firings.length ? L.firings : ['No firing yet: nothing of hers has changed since the trigger started.']).forEach(function (t) {
    var li = document.createElement('li'); li.textContent = t; ul.appendChild(li); });
  det.appendChild(ul); box.appendChild(det); host.insertAdjacentElement('afterend', box);
}
var build = window.ANEES_SETTINGS_BUILD || String(Date.now());
fetch('data/amal-trigger.json?build=' + encodeURIComponent(build), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(render, function () { render(null); });
})();
