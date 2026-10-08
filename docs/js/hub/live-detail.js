/* Done tab: her answers come from the database the moment she taps (Medi 2026-10-06 "a universal system that completes it
   right away"). The built detail (data/tutor.json, scripts/build_tutor_data.py link_detail) carries the QUESTIONS - the
   moment, the clip, Medi's line - and a snapshot of the answers at build time. overlay() replaces that snapshot with the
   live link row {payload, answers, done_at} read with the link's own token, so the Done tab never waits for a build or a
   publish. Real case 2026-10-06: Amal answered all 5 moments of the Oct 2 link on Oct 3; the hourly publish was blocked
   for three days, so the Done tab said "finished" (live) and "0 of 5 answered · not answered" (the stale file) at once.
   A link that has expired cannot be read any more (RLS: expires_at > now()), so the built snapshot stays the record then.
   Pure functions; node tests in tests/test_live_detail.cjs. */
(function (root) {
  'use strict';
  const TABLE = { after: 'amal_links', before: 'amal_links', verb_check: 'verb_check_links', word_review: 'transcript_review_links' };
  // what an answer on an "after the lesson" moment changes (mirror of effect_after in build_tutor_data.py)
  // AM-24 (Medi 2026-10-06 "she doesnt understand the word slip"): "mistake", never "slip", on her page (2026-10-07 audit)
  const RESULT_AFTER = { 'Right': 'not counted as a mistake', 'Wrong': 'counted as a mistake for the student', 'Wrong word': 'counted as a mistake for the student (word)',
    'Wrong grammar': 'counted as a mistake for the student (grammar)', 'Not Medi': 'dropped - it was not the student', 'Skip': 'no change',
    'Medi, right': 'not counted as a mistake', 'Medi, wrong': 'counted as a mistake for the student' };
  const HEARD = { yes: 'Yes, that is what I hear', inaudible: 'Cannot hear clearly' };
  const day = s => s ? String(s).slice(0, 10) : null;
  const pick = (m, k) => { m = m || {}; return m[String(k)] !== undefined ? m[String(k)] : m[k]; };
  const copy = x => Object.assign({}, x);

  // one asked row with the live answer written over the built one. `when` = the tap's own date when the row has one,
  // else the link's last update. An answer that is gone (an undo) opens the row again: no answer, no date, no result.
  function put(x, ans, when, result) {
    x.answer = ans || null;
    x.at = ans ? (when || null) : null;
    if (ans) { if (result !== undefined) x.result = result; }
    else if (x.result && !/^not asked/i.test(String(x.result))) x.result = null;
    return x;
  }

  function overlay(kind, detail, row) {
    if (!row || !detail || !Array.isArray(detail.asked)) return detail;
    const a = row.answers || {}, p = row.payload || {}, at = day(a.updated || row.done_at);
    const asked = detail.asked.map(copy);
    let total = asked.length;
    if (kind === 'after') {
      const nQ = (p.questions || []).length, nH = (p.homework || []).length, pr = (p.prompts || []).map(it => it.id);
      if (!row.payload || asked.length !== nQ + nH + pr.length) return detail;   // the built list and the link disagree: keep the record
      asked.forEach((x, i) => {
        if (i < nQ) { const ans = pick(a.q, i); put(x, ans, at, ans ? (RESULT_AFTER[ans] || null) : undefined); }
        else if (i < nQ + nH) put(x, pick(a.hw, i - nQ), at);
        else put(x, pick(a.pr, pr[i - nQ - nH]), at);
      });
    } else if (kind === 'before') {
      const n = (p.sentences || []).length;
      if (!row.payload || asked.length !== 2 + n) return detail;
      put(asked[0], a.topic, at);
      put(asked[1], (a.repeat || []).join(', ') || null, at);
      for (let i = 0; i < n; i++) put(asked[2 + i], pick(a.sentences, i), at);
    } else if (kind === 'word_review') {
      const items = p.items || [], ans = a.answers || {};
      if (!row.payload || asked.length !== items.length) return detail;
      items.forEach((it, i) => {
        const x = ans[it.id] || {};
        const got = HEARD[x.choice] || (x.choice ? 'Different: ' + (x.text || '') : null);
        put(asked[i], got, day(x.updated_at) || at);
      });
    } else if (kind === 'verb_check') {
      // the built list holds only the forms she answered; rebuild it from the live answers over the link's forms
      const items = p.items || {}, ans = a.answers || {};
      if (!row.payload) return detail;
      asked.length = 0;
      Object.entries(ans).sort((u, v) => String(u[1].updated_at || '').localeCompare(String(v[1].updated_at || ''))).forEach(([iid, x]) => {
        const it = items[iid] || {};
        asked.push({ ask: `${it.tense || ''} · ${it.person || ''}`, word: it.word,
          answer: x.choice === 'yes' ? 'Right' : 'Fixed: ' + String(x.word || ''), at: day(x.updated_at) || at });
      });
      total = Object.keys(items).length;
    } else return detail;
    const out = Object.assign({}, detail, { asked, total, answered: asked.filter(x => x.answer).length, live: true });
    return out;
  }

  // the REST path that reads the link row for a kind (null = this kind has no link row to read)
  function path(kind, token) {
    const t = TABLE[kind];
    return t && token ? `${t}?select=payload,answers,done_at&token=eq.${encodeURIComponent(token)}` : null;
  }

  // read the row and overlay; `rest(path, token)` is the page's fetch; any failure = the built detail, never a blank
  async function live(kind, item, rest) {
    const pth = path(kind, item && item.token);
    if (!pth || !item.detail) return item ? item.detail : null;
    try { const rows = await rest(pth, item.token); return overlay(kind, item.detail, rows && rows[0]); }
    catch (e) { return item.detail; }
  }

  const API = { overlay, path, live, TABLE, RESULT_AFTER };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  root.AneesLiveDetail = API;
})(typeof globalThis !== 'undefined' ? globalThis : this);
