// Live data is re-read when the page comes back into view (rule L1, freshness audit 2026-10-02).
// Before: Progress (Vocab tab), the Word Bank and the Tutor page read Supabase ONCE at load, so a tab left open showed
// yesterday's answers until a manual refresh (precedent: the Flashcards panels, fixed in 8d730a0 the same way).
// AneesLive.onReturn(fn, {busy}) calls fn when the tab becomes visible again, on focus, and on a back/forward-cache
// restore; at most once per 5 s, never while busy() says the person is in the middle of something (audio playing,
// a task open). Every page that reads live data registers here, or is listed with its reason in tests/test_live_reread.py.
(function () {
  if (typeof window === 'undefined' || window.AneesLive) return;
  const GAP_MS = 5000;
  function onReturn(fn, opts) {
    const o = opts || {};
    let last = Date.now();
    const go = function () {
      if (document.visibilityState === 'hidden') return;
      if (Date.now() - last < (o.minGapMs || GAP_MS)) return;
      try { if (o.busy && o.busy()) return; } catch (e) { return; }
      last = Date.now();
      try { const r = fn(); if (r && r.catch) r.catch(function () {}); } catch (e) {}
    };
    document.addEventListener('visibilitychange', go);
    window.addEventListener('focus', go);
    window.addEventListener('pageshow', function (e) { if (e.persisted) go(); });
    return go;
  }
  window.AneesLive = { onReturn: onReturn };
})();
