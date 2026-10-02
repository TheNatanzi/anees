/* One audio bar for every moment in the Tutor hub (Medi 2026-10-01: "every single media play button has a bar with
   start, stop and progress"; 2026-10-02: the same player as every other page - js/play-bar.js AneesPlayer).
   AneesClip.bar({src, start, end, fallback}) returns the bar element (play / pause, stop, progress, volume, ⋯ menu),
   with .play() / .pause(). Only one moment plays at a time (AneesPlayer does that for the whole site).
   If the clip file is missing, the bar plays the same moment from the full lesson recording (fallback {src,start,end}),
   so a Play button never does nothing. Times are seconds; end null = to the end of the file. */
(function (root) {
  'use strict';
  function setRange(a, s, e) {
    a.dataset.clipStart = String(s || 0);
    if (e == null) delete a.dataset.clipEnd; else a.dataset.clipEnd = String(e);
  }
  function bar(o) {
    const a = new Audio(); a.preload = 'none'; a.dataset.ownBar = '1';
    a.src = o.src; setRange(a, o.start, o.end);
    // fallback: one {src,start,end} or a chain of them (lesson.mp3 -> Medi.mp3 -> Amal.mp3), tried in order
    const chain = [].concat(o.fallback || []).filter(Boolean);
    let fellBack = 0, want = false;
    a.addEventListener('play', () => { want = true; });
    a.addEventListener('pause', () => { want = false; });
    a.addEventListener('error', () => {
      const f = chain[fellBack];
      if (f) {
        fellBack++; a.src = f.src; setRange(a, f.start, f.end); a.load();
        a.addEventListener('loadedmetadata', () => { a.currentTime = f.start || 0; if (want) a.play().catch(() => {}); }, { once: true });
      } else { a.__apbFailed = true; want = false; }
    });
    const el = root.AneesPlayer.make(a);
    el.play = () => { want = true; if (a.paused) el.querySelector('.apb-main').click(); };
    el.pause = () => { want = false; a.pause(); };
    return el;
  }
  function stopAll() { document.querySelectorAll('.apb').forEach(b => b.audio && b.audio.pause()); }
  root.AneesClip = { bar, stopAll };
})(window);
