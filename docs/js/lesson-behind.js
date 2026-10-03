// "This lesson is recorded but not on these pages yet" (rule F1, freshness audit 2026-10-02).
// The 2026-10-01 lesson was in the database (the hourly job loaded it at 00:17) while every page still ended at 09-30,
// and nothing on the site said so: the publish was blocked for 32 h and only a log on the PC knew. This compares the
// newest lesson in the live `lessons` table with the newest one the pages were built with (data/lessons.json) and, when
// the database is ahead, says so at the top of the page. Re-checked when the tab comes back. Read-only; anon key.
// Rule LS-04 (2026-10-02, Medi: "Why didn't today's get loaded"): the 10-01 lesson failed to load for 9 h (voice-to-text
// credits ran out) and only a log on the PC knew. The hourly job writes every problem it hits to data/lesson-alerts.json;
// each one shows here as one line, e.g. "10-01 lesson not loaded: voice-to-text credits ran out (since 15:15)".
function alertLines(doc, now) {
  const today = (now || new Date());
  const pad = function (n) { return String(n).padStart(2, '0'); };
  const ymd = function (d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
  return ((doc && doc.problems) || []).filter(function (p) { return p && p.text; }).map(function (p) {
    const t = p.since ? new Date(p.since) : null;
    if (!t || isNaN(t)) return p.text.replace(' since {since}', '');
    const hm = pad(t.getHours()) + ':' + pad(t.getMinutes());
    const when = ymd(t) === ymd(today) ? hm : pad(t.getMonth() + 1) + '-' + pad(t.getDate()) + ' ' + hm;
    // rule AM-20: "Amal's word Doc not synced since {since}: <reason>" carries the time inside the line
    if (p.text.indexOf('{since}') >= 0) return p.text.replace('{since}', when);
    return p.text + ' (since ' + when + ')';
  });
}
if (typeof module !== 'undefined' && module.exports) module.exports = { alertLines };
(function () {
  if (typeof window === 'undefined' || window.AneesLessonBehind) return;
  const base = (function () { const s = document.querySelector('script[src*="js/lesson-behind.js"]'); return s ? s.getAttribute('src').replace(/js\/lesson-behind\.js.*$/, '') : ''; })();
  function newer(live, built) { return live.filter(function (d) { return !built.includes(d); }).sort(); }
  function show(missing) {
    let el = document.getElementById('lesson-behind');
    if (!missing.length) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('div');
      el.id = 'lesson-behind'; el.setAttribute('role', 'status');
      el.style.cssText = 'margin:0 0 12px;padding:10px 14px;border-radius:10px;border-left:4px solid #B26F0E;background:rgba(178,111,14,.12);font:500 14px/1.4 system-ui';
      const main = document.querySelector('main') || document.body;
      main.insertBefore(el, main.firstChild);
    }
    const list = missing.join(', ');
    el.textContent = 'Lesson ' + list + (missing.length === 1 ? ' is' : ' are') + ' recorded but not on these pages yet. '
      + 'The hourly job adds ' + (missing.length === 1 ? 'it' : 'them') + ' once the publish checks pass; the numbers below stop at the last published lesson.';
  }
  async function check() {
    if (!window.ANEES || !ANEES.url) return null;
    try {
      const h = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon };
      const [live, built] = await Promise.all([
        fetch(ANEES.url + '/rest/v1/lessons?select=date&order=date.desc&limit=5', { headers: h, cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : []; }),
        fetch(base + 'data/lessons.json', { cache: 'no-store' }).then(function (r) { return r.json(); })
      ]);
      const builtDates = (built.lessons || []).map(function (x) { return x.date; });
      const newestBuilt = builtDates.slice().sort().pop() || '';
      const missing = newer(live.map(function (x) { return x.date; }).filter(function (d) { return d > newestBuilt; }), builtDates);
      show(missing);
      return missing;
    } catch (e) { return null; }
  }
  function showAlerts(lines) {
    let el = document.getElementById('lesson-alerts');
    if (!lines.length) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('div');
      el.id = 'lesson-alerts'; el.setAttribute('role', 'alert');
      el.style.cssText = 'margin:0 0 12px;padding:10px 14px;border-radius:10px;border-left:4px solid #B26F0E;background:rgba(178,111,14,.18);font:600 14px/1.4 system-ui';
      const main = document.querySelector('main') || document.body;
      main.insertBefore(el, main.firstChild);
    }
    el.innerHTML = '';
    lines.forEach(function (l) { const d = document.createElement('div'); d.textContent = l; el.appendChild(d); });
  }
  async function checkAlerts() {
    try {
      const r = await fetch(base + 'data/lesson-alerts.json?t=' + Date.now(), { cache: 'no-store' });
      const lines = r.ok ? alertLines(await r.json()) : [];
      showAlerts(lines);
      return lines;
    } catch (e) { return null; }
  }
  function both() { checkAlerts(); return check(); }
  window.AneesLessonBehind = { check: check, newer: newer, checkAlerts: checkAlerts, alertLines: alertLines };
  if (window.AneesLive) AneesLive.onReturn(both);
  both();
})();
