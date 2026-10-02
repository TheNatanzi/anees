/* One Undo for every choice Amal taps on the Tutor hub and every page it opens (AM-17, Medi 2026-10-02: "can you add an
   undo button to all these tutor hub stuff"). Same button, same words, same look everywhere: "↶ Undo" next to her answer.

   Undo never deletes anything. For an amal_rules tap it queues a NEW row - same token, source, lesson_date and word_key as
   the tap, kind 'undo', payload {undoes: <kind>, match: {...}} - and the latest action per item wins (tap -> undo -> tap
   again works). scripts/amal_undo.py applies the same rule for every script that reads amal_rules (scripts/db.py does it
   on every amal_rules select). Answer maps inside a link row (verb checks, word review, after-lesson steps) drop the key
   and keep a log of what was undone next to it.

   AneesUndo.button(attrs)            -> '<button class="an-undo" ...>↶ Undo</button>'
   AneesUndo.answered(text, attrs)    -> her answer + the Undo button on one line
   AneesUndo.row(tapBody, match)      -> the amal_rules undo row for a tap row
   AneesUndo.latest(rows)             -> {word_key: last row} (a trailing undo leaves {kind:'undo'})
   AneesUndo.reconcile(local, server, pendingKeys, serverOk) -> the answers to show
   AneesUndo.unqueue(queue, pred)     -> the queue without the not-yet-sent taps pred() picks
   AneesUndo.log(list, key, was)      -> the 'undone' log of an answer map, one entry longer (kept next to the map, never lost) */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api; else root.AneesUndo = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const LABEL = 'Undo';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const attrs = a => Object.entries(a || {}).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');

  function button(a) { return `<button type="button" class="an-undo"${attrs(a)} aria-label="Undo this answer">↶ ${LABEL}</button>`; }
  function answered(text, a) { return `<p class="an-answered"><span>✓ ${esc(text)}</span>${button(a)}</p>`; }

  // the undo row for one tap row (the body that was POSTed to amal_rules)
  function row(tap, match) {
    const p = tap.payload || {};
    return { token: tap.token, source: tap.source, lesson_date: tap.lesson_date ?? null, kind: 'undo', word_key: tap.word_key ?? null,
             payload: { undoes: tap.kind, label: p.label || p.text || p.english || p.arabizi || p.topic || null, match: match || null,
                        at: new Date().toISOString() } };
  }

  // rows in created order -> {word_key: last row}; an undo as the last row leaves {kind:'undo'} (= no answer)
  function latest(rows) {
    const out = {};
    (rows || []).forEach(r => { if (r && r.word_key != null) out[r.word_key] = r; });
    return out;
  }
  const isAnswer = a => !!a && a.kind !== 'undo';

  // What the page shows. server = {key: answer} read live (an undo = {kind:'undo'}); local = this browser's saved taps;
  // pendingKeys = keys with a tap or undo still waiting in the queue. A local answer the server does not have is kept only
  // while it is still queued: once flushed, the server is the truth (2026-10-02: a removed tap stayed "answered" in one
  // browser because the old local copy was merged over the live answers).
  function reconcile(local, server, pendingKeys, serverOk) {
    const out = {}, pend = new Set(pendingKeys || []);
    if (!serverOk) { Object.assign(out, local || {}); return out; }
    Object.entries(server || {}).forEach(([k, v]) => { out[k] = v; });
    Object.entries(local || {}).forEach(([k, v]) => { if (pend.has(k)) out[k] = v; });
    return out;
  }
  function unqueue(queue, pred) { return (queue || []).filter(j => !pred(j)); }
  // answer maps inside a link row (verb checks, word review, after-lesson steps): the key is dropped, this log keeps it
  function log(list, key, was) { return (Array.isArray(list) ? list : []).concat([{ key: String(key), was: was === undefined ? null : was, at: new Date().toISOString() }]).slice(-500); }

  // one look for every page: the hub (Sabz tokens) and Amal's own pages (same tokens)
  if (typeof document !== 'undefined' && !document.getElementById('an-undo-css')) {
    const css = document.createElement('style'); css.id = 'an-undo-css';
    css.textContent = `.an-undo,#anees-bank .an-undo{display:inline-flex;align-items:center;gap:4px;font:600 14px/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;
background:transparent;color:var(--sabz-text,#1D2521);border:1px solid var(--sabz-hairline,#C9CFC6);border-radius:999px;padding:6px 14px;
min-height:36px;cursor:pointer;margin:0 0 0 10px;width:auto;flex:0 0 auto;text-align:center}
.an-undo:hover,#anees-bank .an-undo:hover{border-color:var(--sabz-text-muted,#66716B)}
.an-undo:focus-visible{outline:2px solid var(--sabz-text,#1D2521);outline-offset:2px}
.an-answered{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin:8px 0 0;font-weight:600;
color:var(--vp-sage,var(--sabz-data-ink,#2E6A4E))}.an-answered .an-undo,#anees-bank .an-answered .an-undo{margin:0}
[data-answered]{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px 8px}[data-answered]>.an-undo{margin-left:auto}`;
    (document.head || document.documentElement).appendChild(css);
  }
  return { LABEL, button, answered, row, latest, isAnswer, reconcile, unqueue, log };
});
