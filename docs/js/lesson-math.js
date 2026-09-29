/* One place for the lesson numbers every page shows (eng audit 2026-09-29).
   - Medi's decision 4: a score from a lesson that is not verified SHOWS with "≈" (e.g. "Words ≈74%"); hover or tap says
     why (the reasons scripts/accuracy_gates.py writes to lessons.json: lesson.release.status / .reasons). Averages still
     include it and are also "≈" when any input is "≈". Never hidden, never shown as exact.
   - Medi's decision 6: one formula per number. Averages over lessons are POOLED (Σ right + ½ partial ÷ Σ scored uses;
     Σ (uses − scored slips) ÷ Σ uses), never a mean of lesson percentages - the Lessons page used a plain mean (76 % /
     63 %) while the Overview showed the pooled 80.0 % / 72.0 % for the same thing.
   Pure functions; works in the browser (window.AneesLessonMath) and in node (module.exports) for tests and
   scripts/check_numbers.py. */
(function (root) {
  'use strict';
  const ok = v => v !== null && v !== undefined && v !== '' && !Number.isNaN(Number(v));
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dm = d => { const p = String(d || '').split('-').map(Number); return p.length === 3 ? MON[p[1] - 1] + ' ' + p[2] : String(d); };

  // ---------- decision 4: verified or not ----------
  function release(L) {
    const r = L && L.release;
    if (!r || !r.status) return { verified: false, reasons: ['no accuracy check has run on this lesson yet'] };
    return { verified: r.status === 'verified', reasons: r.status === 'verified' ? [] : (r.reasons && r.reasons.length ? r.reasons.slice() : ['not verified']) };
  }
  // The "why" for one lesson or a set of lessons (an average). Short enough for a title attribute.
  function why(lessons) {
    const list = (Array.isArray(lessons) ? lessons : [lessons]).filter(Boolean);
    const bad = list.filter(L => !release(L).verified);
    if (!bad.length) return '';
    if (list.length === 1) return 'Not verified yet, so this is not exact:\n• ' + release(bad[0]).reasons.join('\n• ');
    const first = release(bad[0]).reasons[0] || 'not verified';
    return `Not exact: ${bad.length} of ${list.length} lessons behind this number are not verified yet (${bad.slice(0, 6).map(L => dm(L.date)).join(', ')}${bad.length > 6 ? ', …' : ''}). ` +
      `Most common reason: ${commonReason(bad) || first}. Open a lesson on the Lessons page for its full list.`;
  }
  function commonReason(bad) {
    const n = new Map();
    for (const L of bad) for (const r of release(L).reasons) { const k = String(r).split(':')[0]; n.set(k, (n.get(k) || 0) + 1); }
    let best = null; for (const [k, v] of n) if (!best || v > best[1]) best = [k, v];
    return best ? `${best[0]} (${best[1]} of ${bad.length})` : '';
  }
  const approx = lessons => (Array.isArray(lessons) ? lessons : [lessons]).filter(Boolean).some(L => !release(L).verified);
  // "≈" + value, and the reason. mark(74, lessons) -> {text: '≈74', approx: true, title: '...'}
  function mark(text, lessons) {
    const a = approx(lessons);
    return { text: (a ? '≈' : '') + text, approx: a, title: a ? why(lessons) : '' };
  }
  // HTML for a marked number (the title shows on hover; tap shows it too via wireTaps()).
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function html(text, lessons) {
    const m = mark(text, lessons);
    return m.approx ? `<span class="rel-approx" tabindex="0" role="note" title="${esc(m.title)}" data-why="${esc(m.title)}">${esc(m.text)}</span>` : esc(m.text);
  }
  // Tap / Enter on a "≈" number shows its reason (title attributes do not show on phones).
  function wireTaps(doc) {
    doc = doc || (typeof document !== 'undefined' ? document : null);
    if (!doc || doc.__relWired) return; doc.__relWired = true;
    const show = el => {
      let tip = doc.getElementById('rel-tip');
      if (!tip) { tip = doc.createElement('div'); tip.id = 'rel-tip'; tip.setAttribute('role', 'status');
        tip.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:9999;max-width:560px;margin:0 auto;padding:10px 12px;border-radius:8px;background:var(--ab-ink,#222);color:var(--ab-paper,#fff);font:13px/1.4 system-ui,sans-serif;white-space:pre-line;box-shadow:0 4px 18px rgba(0,0,0,.25)';
        tip.addEventListener('click', () => { tip.hidden = true; }); doc.body.appendChild(tip); }
      tip.textContent = (el.getAttribute('data-why') || '') + '\n(tap to close)'; tip.hidden = false;
    };
    doc.addEventListener('click', e => { const el = e.target && e.target.closest && e.target.closest('.rel-approx'); if (el) show(el); });
    doc.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target && e.target.classList && e.target.classList.contains('rel-approx')) show(e.target); });
  }

  // ---------- decision 6: one pooled formula per number ----------
  // Words: Σ (right + ½ partial) ÷ Σ scored uses, over lessons with scored uses (the Word Bank's own weighting).
  function pooledWords(lessons) {
    const W = (lessons || []).filter(L => L && L.words && ok(L.words.scored) && L.words.scored > 0);
    const scored = W.reduce((s, L) => s + L.words.scored, 0);
    const points = W.reduce((s, L) => s + (L.words.right || 0) + (L.words.partial || 0) / 2, 0);
    return { pct: scored ? 100 * points / scored : null, points, scored, lessons: W, n: W.length };
  }
  // Grammar: Σ (uses − scored slips) ÷ Σ uses (scripts/grammar_math.py). Older lessons.json without scored_mistakes:
  // mistakes are used, and a lesson whose slips exceed its uses (the old "estimate") is kept out, as before.
  function pooledGrammar(lessons) {
    const sm = L => ok(L.grammar.scored_mistakes) ? L.grammar.scored_mistakes : (L.grammar.mistakes || 0);
    const G = (lessons || []).filter(L => L && L.grammar && ok(L.grammar.uses) && L.grammar.uses > 0 && !L.grammar.estimate && sm(L) <= L.grammar.uses);
    const uses = G.reduce((s, L) => s + L.grammar.uses, 0), slips = G.reduce((s, L) => s + sm(L), 0);
    return { pct: uses ? 100 * (uses - slips) / uses : null, uses, slips, lessons: G, n: G.length };
  }
  // Talk share: Σ his seconds ÷ Σ (his + her seconds). Fillers: Σ filled pauses ÷ Σ minutes he spoke, over the lessons
  // whose page turns keep the fillers (fillers.comparable). The Lessons page showed plain means (57 %, 9.5 / min) while
  // the Overview / Progress showed these pooled numbers (56.9 %, 10.1 / min).
  function pooledTalk(lessons) {
    const T = (lessons || []).filter(L => L && L.talk && ok(L.talk.medi_s) && L.talk.medi_s > 0);
    const me = T.reduce((s, L) => s + L.talk.medi_s, 0), all = T.reduce((s, L) => s + L.talk.medi_s + (L.talk.amal_s || 0), 0);
    return { pct: all ? 100 * me / all : null, medi_s: me, all_s: all, lessons: T, n: T.length };
  }
  function pooledFillers(lessons) {
    const P = (lessons || []).filter(L => L && L.fillers && ok(L.fillers.count) && L.fillers.comparable !== false && L.talk && ok(L.talk.medi_s) && L.talk.medi_s > 0);
    const n = P.reduce((s, L) => s + L.fillers.count, 0), min = P.reduce((s, L) => s + L.talk.medi_s, 0) / 60;
    return { perMin: min ? n / min : null, count: n, minutes: min, lessons: P, n: P.length };
  }
  function mean(lessons, pick) {
    const v = (lessons || []).map(pick).filter(ok).map(Number);
    return v.length ? { value: v.reduce((a, b) => a + b, 0) / v.length, n: v.length } : null;
  }
  // ---------- one filled-pause test (scripts/build_lessons_page_data.py is_filler(), which writes fillers.count /
  // in_turns). The Overview card and the "Filled pauses through the hour" panel used two different tests (25 Aug turns:
  // 16 vs 24), so the panel's note disagreed with lessons.json. Both read this one now.
  const FL = new Set(['uh', 'um', 'umm', 'uhm', 'uhh', 'er', 'erm', 'eh', 'mm', 'mmm', 'hmm', 'hm', 'mhm', 'ah']);
  const FA = new Set(['ام', 'امم', 'اممم', 'إم', 'إمم', 'أمم', 'أممم', 'مم', 'ممم', 'آآ', 'آآآ', 'آآآآ', 'أآ', 'أآآ', 'اا', 'ااا', 'آ', 'إه', 'اه', 'آه', 'اهه', 'آهه']);
  const YES = new Set(['اه', 'آه']);   // also "yes": counted only mid-turn
  const normTok = t => String(t).toLowerCase().replace(/[^\p{L}\p{N}_؀-ۿ]+/gu, '').replace(/ـ/g, '');
  const isFiller = (tok, pos) => { const n = normTok(tok); if (!n) return false; if (FL.has(n)) return true; if (/^(?:[آاأ]{2,}|[آاأ]?م{2,}|ه?م{2,})$/.test(n)) return true; return FA.has(n) && !(YES.has(n) && pos === 0); };
  const countFillers = txt => String(txt || '').replace(/،/g, ' ').split(/\s+/).filter(Boolean).reduce((s, t, i) => s + (isFiller(t, i) ? 1 : 0), 0);
  const api = { release, why, approx, mark, html, wireTaps, pooledWords, pooledGrammar, pooledTalk, pooledFillers, mean, dm, isFiller, countFillers };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AneesLessonMath = api;
})(typeof window !== 'undefined' ? window : globalThis);
