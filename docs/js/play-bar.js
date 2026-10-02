/* One player for every sound on the site (Medi 2026-10-02: "unify the Play bar for EVERYTHING: PLAY, PAUSE, STOP, BAR FOR
   PROGRESS, VOLUME, THREE DOT MENU" and "put it as close to the original play button, not the bottom of the screen").
   Earlier versions: 2026-10-01 a bottom-of-screen bar for button audio; <audio controls> kept the browser's own player.

   AneesPlayer.make(audio) -> the bar element for that audio: play / pause, stop (pause + back to the start of the clip, so
   the next play starts at the right spot), a slider over the clip, the time, volume (tap = mute, slider), and a ⋯ menu
   (speed, repeat the clip, download). The clip range is the audio's data-clip-start / data-clip-end (seconds), else a
   #t=start,end in its src, else the whole file. Playback stops at the clip end (a #t=a,b on the full lesson recording
   would otherwise play on to the end of the lesson); a play from outside the clip or after its end starts at its start.
   Only one sound plays at a time.

   Where the bar goes, automatically, on every page that loads this file (js/theme.js and js/transcript-arabizi.js do):
     <audio controls>           the browser's player is hidden and this bar takes its place
     a page's new Audio() / <audio> started by a button   the bar sits right under that button (moves with it when one
                                                          shared Audio serves many buttons)
     anything else              a bar at the bottom of the screen (last resort)
   Audio with data-own-bar (Tutor hub moments, js/hub/clip-player.js) gets its bar from AneesPlayer.make directly. */
(function () {
  'use strict';
  if (typeof window === 'undefined' || window.AneesPlayBar) return;
  var fmt = function (s) { s = Math.max(0, s || 0); var m = Math.floor(s / 60), x = Math.floor(s % 60); return m + ':' + (x < 10 ? '0' : '') + x; };
  var SPEEDS = [0.75, 1, 1.25, 1.5];
  var lastClick = null, lastClickAt = 0, playing = null, dock = null;

  function range(a) {
    var d = a.dataset || {}, s = parseFloat(d.clipStart), e = parseFloat(d.clipEnd);
    var m = String(a.currentSrc || a.src || '').match(/#t=([\d.]+)(?:,([\d.]+))?/);
    if (!isFinite(s)) s = m ? parseFloat(m[1]) : 0;
    if (!isFinite(e)) e = m && m[2] ? parseFloat(m[2]) : (isFinite(a.duration) ? a.duration : 0);
    return [s, Math.max(s, e)];
  }

  function css() {
    if (document.getElementById('apb-css')) return;
    var st = document.createElement('style'); st.id = 'apb-css';
    st.textContent =                                         // the browser's own player look (Medi: "just like the example")
      '.apb{display:flex;align-items:center;gap:4px;margin:6px 0;padding:4px 10px;height:44px;border-radius:999px;background:var(--apb-bg,#3a3f3d);color:var(--apb-ink,#f1f3f4);font:13px/1 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;position:relative;width:100%;max-width:100%;box-sizing:border-box;flex-basis:100%}' +
      '@media (prefers-color-scheme:light){:root:not([data-theme=dark]) .apb{--apb-bg:#f1f3f4;--apb-ink:#202124}}:root[data-theme=light] .apb{--apb-bg:#f1f3f4;--apb-ink:#202124}' +
      '.apb button{flex:0 0 32px;width:32px;height:32px;border:0;border-radius:50%;background:none;color:inherit;font-size:15px;cursor:pointer;display:grid;place-items:center;padding:0}' +
      '.apb button:hover{background:rgba(127,127,127,.22)}' +
      '.apb .apb-time{flex:0 0 auto;font-variant-numeric:tabular-nums;font-size:13px;padding:0 6px;white-space:nowrap}' +
      '.apb input[type=range]{-webkit-appearance:none;appearance:none;height:4px;border-radius:2px;margin:0;cursor:pointer;background:linear-gradient(to right,currentColor var(--apb-p,0%),rgba(127,127,127,.45) var(--apb-p,0%))}' +
      '.apb input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:currentColor}' +
      '.apb input[type=range]::-moz-range-thumb{width:12px;height:12px;border:0;border-radius:50%;background:currentColor}' +
      '.apb .apb-pos{flex:1;min-width:60px;margin:0 6px}' +
      '.apb .apb-vol{flex:0 0 0;width:0;opacity:0;transition:flex-basis .15s,width .15s,opacity .15s}' +
      '.apb .apb-volbox{display:flex;align-items:center}' +
      '.apb .apb-volbox:hover .apb-vol,.apb .apb-volbox:focus-within .apb-vol{flex-basis:64px;width:64px;opacity:1;margin-right:4px}' +
      '.apb-menu{position:absolute;right:6px;bottom:calc(100% + 4px);z-index:2147483001;min-width:180px;padding:6px;border-radius:10px;background:var(--apb-bg,#3a3f3d);color:var(--apb-ink,#f1f3f4);box-shadow:0 6px 20px rgba(0,0,0,.3)}' +
      '.apb-menu[hidden]{display:none}' +
      '.apb-menu .apb-row{display:flex;gap:4px;align-items:center;flex-wrap:wrap;padding:4px}' +
      '.apb-menu .apb-row span{font-size:11px;opacity:.7;width:100%}' +
      '.apb-menu button{flex:0 0 auto;width:auto;height:28px;border-radius:999px;padding:0 10px;font-size:12px;border:1px solid rgba(127,127,127,.4)}' +
      '.apb-menu button.on{color:inherit;outline:2px solid currentColor;background:rgba(127,127,127,.3)}' +
      '.apb-menu a{display:block;padding:8px;color:inherit;font-size:12px;text-decoration:none}' +
      '.apb-dock{position:fixed;left:8px;right:8px;bottom:8px;z-index:2147483000;margin:0;width:auto}' +
      'body.apb-on{padding-bottom:64px}' +
      '@media (max-width:520px){.apb .apb-volbox{display:none}.apb .apb-time{font-size:12px;padding:0 2px}}';
    (document.head || document.documentElement).appendChild(st);
  }

  /* the bar for one audio element (one bar per element, created once) */
  function make(a) {
    if (a.__apbBar) return a.__apbBar;
    css();
    var el = document.createElement('div');
    el.className = 'apb'; el.setAttribute('role', 'group'); el.setAttribute('aria-label', 'Audio player');
    el.innerHTML =
      '<button type="button" class="apb-main" aria-label="Play">▶</button>' +
      '<button type="button" class="apb-stop" aria-label="Stop and go back to the start">■</button>' +
      '<span class="apb-time">0:00 / 0:00</span>' +
      '<input class="apb-pos" type="range" min="0" max="1000" step="1" value="0" aria-label="Position in the clip">' +
      '<span class="apb-volbox"><input class="apb-vol" type="range" min="0" max="100" step="1" value="100" aria-label="Volume">' +
      '<button type="button" class="apb-mute" aria-label="Mute">🔊</button></span>' +
      '<button type="button" class="apb-more" aria-label="More options" aria-haspopup="true">⋮</button>' +
      '<div class="apb-menu" hidden><div class="apb-row"><span>Speed</span></div><div class="apb-row apb-loop-row"></div><a class="apb-dl" download>Download this recording</a></div>';
    var q = function (s) { return el.querySelector(s); };
    var main = q('.apb-main'), pos = q('.apb-pos'), time = q('.apb-time'), mute = q('.apb-mute'), vol = q('.apb-vol'),
      menu = q('.apb-menu'), raf = 0, loopOn = false;
    SPEEDS.forEach(function (sp) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = sp + '×'; b.dataset.sp = sp;
      b.onclick = function () { a.playbackRate = sp; paint(); };
      menu.querySelector('.apb-row').appendChild(b);
    });
    var lb = document.createElement('button'); lb.type = 'button'; lb.textContent = 'Repeat the clip';
    lb.onclick = function () { loopOn = !loopOn; paint(); };
    q('.apb-loop-row').appendChild(lb);

    function paint() {
      var r = range(a), len = r[1] - r[0], p = Math.min(len, Math.max(0, a.currentTime - r[0]));
      main.textContent = a.paused ? '▶' : '❚❚'; main.setAttribute('aria-label', a.paused ? 'Play' : 'Pause');
      pos.value = len ? Math.round(1000 * p / len) : 0;
      pos.style.setProperty('--apb-p', (pos.value / 10) + '%');
      time.textContent = a.__apbFailed ? 'Audio not found' : fmt(p) + ' / ' + fmt(len);
      mute.textContent = a.muted || a.volume === 0 ? '🔇' : '🔊';
      vol.value = a.muted ? 0 : Math.round(a.volume * 100);
      vol.style.setProperty('--apb-p', vol.value + '%');
      [].forEach.call(menu.querySelectorAll('[data-sp]'), function (b) { b.classList.toggle('on', +b.dataset.sp === (a.playbackRate || 1)); });
      lb.classList.toggle('on', loopOn);
      q('.apb-dl').href = String(a.currentSrc || a.src || '').replace(/#.*$/, '');
    }
    function tick() {
      cancelAnimationFrame(raf);
      var t = function () {
        var r = range(a);
        if (!a.paused && r[1] > r[0] && a.currentTime >= r[1]) {
          if (loopOn) a.currentTime = r[0]; else { a.pause(); a.__apbDone = true; }
        }
        paint(); if (!a.paused) raf = requestAnimationFrame(t);
      };
      raf = requestAnimationFrame(t);
    }
    function start() {
      var r = range(a);
      if (a.__apbDone || a.currentTime < r[0] - 0.25 || (r[1] > r[0] && a.currentTime >= r[1] - 0.05)) {
        try { a.currentTime = r[0]; } catch (e) {}
      }
      a.__apbDone = false;
    }
    main.onclick = function () {
      if (a.paused) { if (a.readyState < 1 && a.load && !a.src && a.dataset.clipSrc) a.src = a.dataset.clipSrc; start(); var p = a.play(); if (p && p.catch) p.catch(function () {}); }
      else a.pause();
    };
    q('.apb-stop').onclick = function () { a.pause(); try { a.currentTime = range(a)[0]; } catch (e) {} a.__apbDone = false; paint(); };
    pos.oninput = function () { var r = range(a); try { a.currentTime = r[0] + (r[1] - r[0]) * pos.value / 1000; } catch (e) {} a.__apbDone = false; paint(); };
    mute.onclick = function () { a.muted = !a.muted; if (!a.muted && a.volume === 0) a.volume = 1; paint(); };
    vol.oninput = function () { a.volume = vol.value / 100; a.muted = vol.value == 0; paint(); };
    q('.apb-more').onclick = function (e) { e.stopPropagation(); menu.hidden = !menu.hidden; paint(); };
    document.addEventListener('click', function (e) { if (!el.contains(e.target)) menu.hidden = true; });
    a.addEventListener('play', function () { start(); if (playing && playing !== a && !playing.paused) playing.pause(); playing = a; tick(); paint(); });
    ['pause', 'seeked', 'loadedmetadata', 'durationchange', 'volumechange', 'ratechange'].forEach(function (t) { a.addEventListener(t, paint); });
    a.addEventListener('ended', function () { a.__apbDone = true; paint(); });
    a.addEventListener('error', function () { setTimeout(paint, 0); });
    a.__apbBar = el; el.audio = a; el.paint = paint;
    paint();
    return el;
  }

  function place(a) {
    if (!a || (a.dataset && a.dataset.ownBar) || !document.body) return;
    if (a.isConnected && a.controls) {                         // the browser's own player -> ours, in the same spot
      a.controls = false; a.dataset.apbWasControls = '1';
      var b = make(a); if (b.previousElementSibling !== a) a.insertAdjacentElement('afterend', b);
      return;
    }
    if (a.dataset.apbWasControls) return;
    var bar = make(a), btn = Date.now() - lastClickAt < 4000 ? lastClick : null;
    if (btn && btn.isConnected) {                              // right under the button that started it
      undock(bar);
      if (bar.previousElementSibling !== btn) btn.insertAdjacentElement('afterend', bar);
    } else if (!bar.isConnected) {
      if (!dock) dock = true;
      bar.classList.add('apb-dock'); document.body.appendChild(bar); document.body.classList.add('apb-on');
    }
  }
  function undock(bar) {
    if (bar.classList.contains('apb-dock')) { bar.classList.remove('apb-dock'); document.body.classList.remove('apb-on'); }
  }
  function scan(root) {
    if (root && root.querySelectorAll) [].forEach.call(root.querySelectorAll('audio[controls]'), place);
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button, a, [role=button]');
    if (b && !b.closest('.apb')) { lastClick = b; lastClickAt = Date.now(); }
  }, true);
  document.addEventListener('play', function (e) { if (e.target instanceof HTMLMediaElement) place(e.target); }, true);
  var play = HTMLMediaElement.prototype.play;                    // new Audio() is never in the page, so catch it here
  HTMLMediaElement.prototype.play = function () { try { place(this); } catch (e) {} return play.apply(this, arguments); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { scan(document); });
  else scan(document);
  if (window.MutationObserver) new MutationObserver(function (ms) {
    ms.forEach(function (m) { [].forEach.call(m.addedNodes, function (n) {
      if (n.nodeType !== 1) return; if (n.tagName === 'AUDIO' && n.controls) place(n); else scan(n);
    }); });
  }).observe(document.documentElement, { childList: true, subtree: true });

  window.AneesPlayer = { make: make, range: range };
  window.AneesPlayBar = { watch: place, hide: function () { if (playing) playing.pause(); } };
})();
