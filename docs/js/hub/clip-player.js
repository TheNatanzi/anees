/* One audio bar for every moment in the Tutor hub (Medi 2026-10-01: "every single media play button has a bar with
   start, stop and progress"). AneesClip.bar({src, start, end, fallback}) returns the bar element: play / pause, stop
   (back to the start of the moment), a slider over the moment, and the time. Only one moment plays at a time.
   If the clip file is missing, the bar plays the same moment from the full lesson recording (fallback {src,start,end}),
   so a Play button never does nothing. Times are seconds; end null = to the end of the file. */
(function (root) {
  'use strict';
  let current = null;
  const fmt = s => { s = Math.max(0, s || 0); const m = Math.floor(s / 60), x = Math.floor(s % 60); return m + ':' + (x < 10 ? '0' : '') + x; };
  function bar(o) {
    const el = document.createElement('div');
    el.className = 'hb-player';
    el.innerHTML = '<button type="button" class="hb-pp" aria-label="Play">▶</button><button type="button" class="hb-stop" aria-label="Stop">■</button>' +
      '<input type="range" min="0" max="1000" step="1" value="0" aria-label="Position in the moment"><span class="hb-time">0:00</span>';
    const pp = el.querySelector('.hb-pp'), st = el.querySelector('.hb-stop'), sl = el.querySelector('input'), tm = el.querySelector('.hb-time');
    const a = new Audio(); a.preload = 'none'; a.dataset.ownBar = '1';
    let src = o.src, s = o.start || 0, e = o.end == null ? null : o.end, fellBack = false, want = false, raf = 0, failed = false;
    const end = () => (e != null ? e : (isFinite(a.duration) ? a.duration : s));
    const me = { pause: () => { want = false; a.pause(); paint(); }, el };
    function paint() {
      const len = Math.max(0, end() - s), pos = Math.min(len, Math.max(0, a.currentTime - s));
      pp.textContent = a.paused ? '▶' : '❚❚'; pp.setAttribute('aria-label', a.paused ? 'Play' : 'Pause');
      sl.value = len ? Math.round(1000 * pos / len) : 0;
      tm.textContent = failed ? 'Audio not found' : (len ? fmt(pos) + ' / ' + fmt(len) : fmt(pos));
      el.classList.toggle('on', !a.paused);
    }
    function loop() { cancelAnimationFrame(raf); const t = () => { if (!a.paused && a.currentTime >= end() - 0.02 && end() > s) { a.pause(); want = false; } paint(); if (!a.paused) raf = requestAnimationFrame(t); }; raf = requestAnimationFrame(t); }
    function load() { if (!a.src || !a.src.endsWith(src)) { a.src = src; a.load(); } }
    function seek(t) { if (a.readyState >= 1) a.currentTime = t; else a.addEventListener('loadedmetadata', () => { a.currentTime = t; }, { once: true }); }
    function play() {
      if (current && current !== me) current.pause();
      current = me; want = true; load();
      if (a.readyState >= 1 && (a.currentTime < s || a.currentTime >= end() - 0.05)) a.currentTime = s;
      else if (a.readyState < 1) seek(s);
      const p = a.play(); if (p && p.catch) p.catch(() => {});
      loop();
    }
    a.addEventListener('error', () => {
      if (o.fallback && !fellBack) { fellBack = true; src = o.fallback.src; s = o.fallback.start || 0; e = o.fallback.end == null ? null : o.fallback.end; a.src = src; a.load(); if (want) play(); }
      else { failed = true; want = false; paint(); }
    });
    ['play', 'pause', 'ended', 'loadedmetadata', 'seeked'].forEach(t => a.addEventListener(t, () => { if (t === 'play') loop(); paint(); }));
    pp.onclick = () => (a.paused ? play() : me.pause());
    st.onclick = () => { want = false; a.pause(); if (a.readyState >= 1) a.currentTime = s; paint(); };
    sl.oninput = () => { load(); const t = s + (end() - s) * sl.value / 1000; seek(t); paint(); };
    el.play = play; el.pause = me.pause;
    paint();
    return el;
  }
  function stopAll() { if (current) current.pause(); }
  root.AneesClip = { bar, stopAll };
})(window);
