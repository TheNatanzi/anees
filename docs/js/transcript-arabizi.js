/* Arabizi everywhere (Medi 2026-09-25, decision b): on every Medi-facing transcript view, her Arabizi on top, the
   Arabic small underneath. One renderer for every page: the Word Bank converter (docs/js/word-bank-arabizi.js, rule S1)
   fed with her Doc + house spellings + catalog + arabizi-extra. Fragments the converter cannot spell stay in Arabic
   and carry the "Unverified spelling stays in Arabic" note. Presentation only: nothing here scores or edits a transcript.

   <script src="../js/word-bank-arabizi.js"></script>
   <script src="../js/transcript-arabizi.js" data-arabizi-selector="p.turn .words, p.chat .words"></script>
   Amal's own pages (docs/amal/*) never load this: they stay Arabic-first. */
(function () {
  'use strict';
  if (window.AneesTranscriptArabizi) return;
  var me = document.currentScript || (function () { var s = document.getElementsByTagName('script'); return s[s.length - 1]; })();
  var src = (me && me.getAttribute('src')) || 'js/transcript-arabizi.js';
  var base = src.replace(/js\/transcript-arabizi\.js.*$/, '');          // '../' on docs/lessons/*, '' on docs/*
  var selector = (me && me.getAttribute('data-arabizi-selector')) || '.words';
  var AR = /[ء-غف-يٱ]/;
  var toArabizi = null, pending = [], approxSeen = false;

  var css = '.az-latin{display:block;direction:ltr;unicode-bidi:isolate}' +
            '.az-arabic{display:block;font-size:.82em;opacity:.72;line-height:1.5;margin-top:1px}' +
            '.az-legend{font-size:12px;opacity:.7;margin:6px 0 10px}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // One element -> [Arabizi line] + the original made small. The original node is kept untouched (other scripts, such as
  // transcript-context-review.js, still find the same .words span and the same text).
  function apply(el) {
    if (!toArabizi || el.dataset.az === '1') return;
    var text = el.textContent;
    if (!AR.test(text)) return;
    var latin = el.cloneNode(true), approx = false;
    var walk = document.createTreeWalker(latin, NodeFilter.SHOW_TEXT, null), n, nodes = [];
    while ((n = walk.nextNode())) nodes.push(n);
    nodes.forEach(function (t) {
      if (!AR.test(t.nodeValue)) return;
      var r = toArabizi(t.nodeValue);
      if (r.approximate) approx = true;
      t.nodeValue = r.text;
    });
    latin.removeAttribute('id'); latin.removeAttribute('data-row');
    latin.className = 'az-latin';
    latin.setAttribute('dir', 'ltr'); latin.setAttribute('aria-hidden', 'false');
    el.dataset.az = '1';
    el.classList.add('az-arabic');
    el.setAttribute('lang', 'ar');
    if (approx) { el.title = 'Unverified spelling stays in Arabic'; approxSeen = true; }
    el.parentNode.insertBefore(latin, el);
  }

  function applyAll(root) {
    if (!toArabizi) { pending.push(root || document); return; }
    var scope = root && root.querySelectorAll ? root : document;
    var list = scope.querySelectorAll(selector);
    for (var i = 0; i < list.length; i++) apply(list[i]);
    if (root && root.matches && root.matches(selector)) apply(root);
    if (approxSeen && !document.querySelector('.az-legend')) {
      var main = document.querySelector('main') || document.body;
      var lg = document.createElement('p'); lg.className = 'az-legend';
      lg.textContent = 'Arabizi in Amal’s spelling on top, the recorded Arabic underneath. Unverified spelling stays in Arabic.';
      main.insertBefore(lg, main.firstChild);
    }
  }

  function get(p) { return fetch(base + p, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }
  var q = '?v=' + (window.ANEES_BUILD || 'az1');
  Promise.all([get('data/words.json' + q), get('data/house_spelling.json' + q), get('data/word-bank-catalog.json' + q), get('data/arabizi-extra.json' + q)])
    .then(function (res) {
      if (!window.AneesWordBankArabizi) return;
      var house = (res[1] && res[1].items) || {};
      var words = ((res[0] && res[0].items) || []).map(function (w) {
        var h = house[w.match_loose];
        return h && h.house ? Object.assign({}, w, { house_spelling: h.house }) : w;
      });
      toArabizi = window.AneesWordBankArabizi.create(words, res[2] || {}, res[3] || {});
      var todo = pending.length ? pending : [document]; pending = [];
      todo.forEach(applyAll);
      // pages that draw their lines later (slips, speaking review, index): render what appears
      if (window.MutationObserver) {
        new MutationObserver(function (muts) {
          muts.forEach(function (m) { for (var i = 0; i < m.addedNodes.length; i++) if (m.addedNodes[i].nodeType === 1) applyAll(m.addedNodes[i]); });
        }).observe(document.body, { childList: true, subtree: true });
      }
    });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { applyAll(document); });
  else applyAll(document);
  window.AneesTranscriptArabizi = { apply: applyAll, esc: esc };
})();
