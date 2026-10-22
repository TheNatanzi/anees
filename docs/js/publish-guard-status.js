/* System Settings: the publish guard's status line (Medi decision 7, 2026-09-29).
   Reads docs/data/publish-guard.json, which scripts/publish_guard.py writes on every PASSING push. When a check fails
   nothing is published, so this line keeps showing the last pass; the reason for a block is in the hourly log on the PC
   and shows here as "last block" once a later run passes. */
(function () {
'use strict';
var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// "2026-09-29T14:15:07-07:00" -> "Sep 29, 14:15" (the PC's own clock, read from the text: no time-zone surprises)
function when(iso) {
  var m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(String(iso || ''));
  return m ? MONTHS[+m[2] - 1] + ' ' + (+m[3]) + ', ' + m[4] + ':' + m[5] : 'an unknown time';
}

function guardLine(g) {
  if (!g || g.result !== 'pass') {
    return { state: 'unknown', text: 'Publish guard: no passing check has been published yet.',
             details: ['Every hourly run checks the numbers before it publishes. Until the first pass, see hourly.log on the PC.'] };
  }
  var req = (g.checks || []).filter(function (c) { return c.required; });
  var passed = req.filter(function (c) { return c.ok; }).length;
  var out = { state: 'pass', details: [],
              text: 'Publish guard: the numbers were checked before this version went live (' + when(g.updated) + ', ' +
                    passed + ' of ' + req.length + ' checks passed).' };
  if (g.last_block) {
    var n = g.blocks_before_this_pass || 0;
    out.alert = ('Last block: ' + when(g.last_block.at) + ' (' + (g.last_block.source || 'hourly job') + ') - ' +
                     (g.last_block.reason || 'no reason recorded') + (n > 1 ? ' (' + n + ' blocked runs before this pass)' : ''));
    out.details.push(out.alert);
  }
  (g.warnings || []).forEach(function (w) { out.details.push('Warning (does not block): ' + w); });
  out.details.push('If a check fails, nothing is published and this line keeps the last pass; the reason is in hourly.log on the PC.');
  out.checks = req.concat((g.checks || []).filter(function (c) { return !c.required; })).map(function (c) {
    return (c.ok ? '✓ ' : (c.required ? '✗ ' : '! ')) + c.id + (c.what ? ' - ' + c.what : '');
  });
  return out;
}

if (typeof module !== 'undefined' && module.exports) { module.exports = { guardLine: guardLine, when: when }; return; }


  // de-word: warnings gather in one 'Needs attention' card above the two robots (created by whichever script runs first);
  // each row = what is wrong (big) + the next step (one line), the raw detail behind an i that opens in place
  function attnRow(big, small, detail, first) {
    var host = document.getElementById('st-guard'); if (!host) return;
    var card = document.getElementById('st-attn');
    if (!card) { card = document.createElement('section'); card.id = 'st-attn'; card.className = 'st-attn';
      card.innerHTML = '<h2 class="st-attn-h">Needs attention</h2>'; host.parentNode.insertBefore(card, host); }
    var row = document.createElement('div'); row.className = 'st-attn-row';
    row.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/><path d="M12 15v2"/></svg><div><b></b><small></small></div>';
    row.querySelector('b').textContent = big; row.querySelector('small').textContent = small;
    if (detail) { var d = document.createElement('details'), su = document.createElement('summary'), dv = document.createElement('div');
      d.className = 'dw-info'; su.textContent = 'i'; su.title = 'Details'; dv.textContent = detail; d.appendChild(su); d.appendChild(dv); row.querySelector('b').appendChild(d); }
    if (first) card.insertBefore(row, card.children[1] || null); else card.appendChild(row);
  }
function render(g) {
  var box = document.getElementById('st-guard');
  if (!box) return;
  var line = guardLine(g);
  box.textContent = '';
  box.className = 'ab-sub st-guard st-guard-' + line.state;
  // de-word (plan/OVERNIGHT-DEWORD-2026-10-22.md): one status chip; the sentence and the checks open in place
  var req = ((g && g.checks) || []).filter(function (c) { return c.required; }), ok = req.filter(function (c) { return c.ok; }).length;
  var p = document.createElement('span'); p.className = 'dw-chip' + (line.state === 'pass' ? '' : ' muted');
  p.textContent = line.state === 'pass' ? 'Publish guard OK' : 'Publish guard · no pass yet'; p.title = ok + '/' + req.length + ' checks';
  box.appendChild(p);
  if (line.alert) {           // a block Medi could not see at the time is shown, not folded away
    attnRow('Publishing blocked',
      /^clean_tree/.test(g.last_block.reason || '') ? 'Next: commit the changed files, then publish again.' : 'Next: fix the failed check, then publish again.',
      when(g.last_block.at) + ' · ' + (g.last_block.reason || 'no reason recorded') + (g.last_block.source ? ' (' + g.last_block.source + ')' : ''), true);
  }
  if (line.details.length || (line.checks || []).length) {
    var det = document.createElement('details'), sum = document.createElement('summary');
    det.className = 'dw-info'; sum.textContent = 'i'; sum.title = 'What it checks'; det.appendChild(sum);
    var ul = document.createElement('ul');
    [line.text].concat(line.details).concat(line.checks || []).forEach(function (t) { var li = document.createElement('li'); li.textContent = t; ul.appendChild(li); });
    ul = (function (u) { var d = document.createElement('div'); d.appendChild(u); return d; })(ul);
    det.appendChild(ul); box.appendChild(det);
  }
}
var build = window.ANEES_SETTINGS_BUILD || String(Date.now());
fetch('data/publish-guard.json?build=' + encodeURIComponent(build), { cache: 'no-store' })
  .then(function (r) { return r.ok ? r.json() : null; })
  .then(render, function () { render(null); });
})();
