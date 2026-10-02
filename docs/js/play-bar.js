/* Play / pause / stop bar for every play button (Medi 2026-10-01: "add a play pause stop bar for every play button").
   One bar for the whole site, so no page has to change its own buttons: whenever any audio starts (a page's own
   new Audio() or an <audio> element), this bar appears at the bottom of the screen with play/pause, stop, a slider
   over the clip and the time. Loaded by js/theme.js and js/transcript-arabizi.js, so every page that plays sound has it.
   Clip range: the element's data-clip-start / data-clip-end (seconds), else a #t=start,end in its src, else the whole file.
   Elements that already show the browser's own controls (<audio controls>) are left alone. */
(function () {
  'use strict';
  if (typeof window === 'undefined' || window.AneesPlayBar) return;
  var bar = null, el = null, label = '', raf = 0, lastClick = null, lastClickAt = 0;
  var fmt = function (s) { s = Math.max(0, s || 0); var m = Math.floor(s / 60), x = Math.floor(s % 60); return m + ':' + (x < 10 ? '0' : '') + x; };
  function range(a) {
    var d = a.dataset || {}, s = parseFloat(d.clipStart), e = parseFloat(d.clipEnd);
    var m = String(a.currentSrc || a.src || '').match(/#t=([\d.]+)(?:,([\d.]+))?/);
    if (!isFinite(s)) s = m ? parseFloat(m[1]) : 0;
    if (!isFinite(e)) e = m && m[2] ? parseFloat(m[2]) : (isFinite(a.duration) ? a.duration : 0);
    return [s, Math.max(s, e)];
  }
  function labelFor(btn) {
    if (!btn) return 'Playing';
    var box = btn.closest('article, .row, .card, li, section, p, tr') || btn.parentElement;
    var h = box && box.querySelector('h1, h2, h3, h4, .t, .when, time, b, strong');
    var t = (h && h.textContent) || btn.getAttribute('aria-label') || btn.textContent || 'Playing';
    return t.replace(/\s+/g, ' ').replace(/^[▶■❚\s]+/, '').trim().slice(0, 60) || 'Playing';
  }
  function build() {
    if (bar) return;
    var css = document.createElement('style');
    css.textContent = '.apb{position:fixed;left:0;right:0;bottom:0;z-index:2147483000;display:flex;align-items:center;gap:8px;padding:8px 12px calc(8px + env(safe-area-inset-bottom));' +
      'background:var(--panel,#1A231F);color:var(--ink,#E4EAE5);border-top:1px solid var(--line,#2C3833);box-shadow:0 -4px 16px rgba(0,0,0,.18);font:14px/1.3 system-ui,-apple-system,"Segoe UI",sans-serif}' +
      '.apb button{flex:0 0 44px;width:44px;height:44px;border-radius:50%;border:1px solid var(--line,#2C3833);background:var(--bg,#131A17);color:inherit;font-size:16px;cursor:pointer;display:grid;place-items:center;padding:0}' +
      '.apb button.apb-main{background:var(--teal,var(--green,#2E6A4E));border-color:transparent;color:#fff}' +
      '.apb .apb-mid{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}' +
      '.apb .apb-lab{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px;opacity:.75}' +
      '.apb input[type=range]{width:100%;margin:0;accent-color:var(--teal,var(--green,#2E6A4E))}' +
      '.apb .apb-time{flex:0 0 auto;font-variant-numeric:tabular-nums;font-size:12px;opacity:.85;min-width:72px;text-align:right}' +
      '.apb button.apb-x{flex-basis:32px;width:32px;height:32px;border:0;background:none;font-size:15px;opacity:.7}' +
      'body.apb-on{padding-bottom:72px}';
    document.head.appendChild(css);
    bar = document.createElement('div'); bar.className = 'apb'; bar.setAttribute('role', 'region'); bar.setAttribute('aria-label', 'Audio player'); bar.hidden = true;
    bar.innerHTML = '<button type="button" class="apb-main" aria-label="Pause">❚❚</button><button type="button" class="apb-stop" aria-label="Stop">■</button>' +
      '<div class="apb-mid"><span class="apb-lab"></span><input type="range" min="0" max="1000" value="0" step="1" aria-label="Position in the clip"></div>' +
      '<span class="apb-time">0:00 / 0:00</span><button type="button" class="apb-x" aria-label="Close the player">✕</button>';
    document.body.appendChild(bar);
    var main = bar.querySelector('.apb-main'), slider = bar.querySelector('input');
    main.onclick = function () {
      if (!el) return;
      if (el.paused) { var r = range(el); if (el.currentTime >= r[1] - 0.05 || el.currentTime < r[0]) el.currentTime = r[0]; el.play().catch(function () {}); }
      else el.pause();
    };
    bar.querySelector('.apb-stop').onclick = function () { if (!el) return; el.pause(); el.currentTime = range(el)[0]; paint(); };
    bar.querySelector('.apb-x').onclick = function () { if (el) el.pause(); hide(); };
    slider.oninput = function () { if (!el) return; var r = range(el); el.currentTime = r[0] + (r[1] - r[0]) * slider.value / 1000; paint(); };
  }
  function paint() {
    if (!bar || !el) return;
    var r = range(el), len = r[1] - r[0], pos = Math.min(len, Math.max(0, el.currentTime - r[0]));
    var main = bar.querySelector('.apb-main');
    main.textContent = el.paused ? '▶' : '❚❚'; main.setAttribute('aria-label', el.paused ? 'Play' : 'Pause');
    bar.querySelector('input').value = len ? Math.round(1000 * pos / len) : 0;
    bar.querySelector('.apb-time').textContent = fmt(pos) + ' / ' + fmt(len);
    bar.querySelector('.apb-lab').textContent = label;
  }
  function loop() { cancelAnimationFrame(raf); var tick = function () { if (!el) return; var r = range(el);
    if (!el.paused && r[1] > r[0] && el.currentTime >= r[1]) el.pause();      // the clip ends where it ends, whatever the page does
    paint(); if (!el.paused) raf = requestAnimationFrame(tick); }; raf = requestAnimationFrame(tick); }
  function hide() { if (bar) bar.hidden = true; document.body.classList.remove('apb-on'); el = null; }
  function watch(a) {
    if (!a || a.controls || !document.body) return;
    build();
    if (el !== a) {
      el = a;
      if (!a.__apb) { a.__apb = true; ['pause', 'ended', 'seeked', 'loadedmetadata', 'durationchange'].forEach(function (t) { a.addEventListener(t, function () { if (el === a) paint(); }); });
        a.addEventListener('play', function () { if (el !== a) watch(a); loop(); }); }
    }
    label = Date.now() - lastClickAt < 4000 ? labelFor(lastClick) : (label || 'Playing');
    bar.hidden = false; document.body.classList.add('apb-on'); paint(); loop();
  }
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('button, a, [role=button]'); if (b && !(bar && bar.contains(b))) { lastClick = b; lastClickAt = Date.now(); } }, true);
  document.addEventListener('play', function (e) { if (e.target instanceof HTMLMediaElement) watch(e.target); }, true);
  var play = HTMLMediaElement.prototype.play;                    // new Audio() is never in the page, so catch it here
  HTMLMediaElement.prototype.play = function () { var p = play.apply(this, arguments); try { watch(this); } catch (e) {} return p; };
  window.AneesPlayBar = { watch: watch, hide: hide };
})();
