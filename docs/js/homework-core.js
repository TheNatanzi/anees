/* Homework + Amal's uploads: the pure rules (no DOM, no network), shared by the Tutor page (her side), the STUDENT tab
   (Medi's side), Flashcards and the hourly builder's node checks. Medi 2026-10-05: "we need add a student tab now where she
   can assign me work. Lets start whatever she uploads and the shaky words from the previous lessons in flashcards. lets also
   create a box for her 'assign homework'. Give her three options. Translate Sentence, Create Sentence with (she will
   provide words), and answer question (she may want to give context)".
   Grill answers (2026-10-05): the AI checks first (right / close / wrong + reason), Amal confirms or overrules and nothing
   counts until she does; her overrule is a correction rule (S6); homework has ITS OWN number, Words % / Grammar % stay
   lesson-only; shaky words = wrong / partly wrong words AND words he asked for, from the LAST 2 lessons, dropped after two
   right answers on cards; an upload is PERMANENT (reminder: add these to the Doc) or TEMPORARY (cards only).

   AneesHomework.effective(rows)                 -> rows not undone (kind 'undo' + undoes), oldest first
   AneesHomework.uploadSets(uploadRows)          -> [{id:'u:<id>', title, keep, source, cards:[{key:'u:<id>:<n>', ...}], created_at}]
   AneesHomework.permanentReminder(sets, docWords)-> the permanent cards not yet in the Doc (matched by Arabic or Arabizi)
   AneesHomework.shakyCards(shaky, log)          -> the shaky words still open (two 'got' answers after the lesson drop one)
   AneesHomework.taskState(task, replies, verdicts) -> {state:'todo'|'checking'|'waiting'|'done', reply, ai, verdict}
   AneesHomework.score(tasks, replies, verdicts) -> {done, right, close, wrong, points, pct|null, waiting, todo}
   AneesHomework.cardsDone(task, log)            -> distinct cards answered in that set since it was assigned
   AneesHomework.KINDS, DIRECTIONS, VERDICTS */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api; else root.AneesHomework = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const KINDS = { translate: 'Translate a sentence', create: 'Make a sentence with these words', question: 'Answer a question', cards: 'Cards for a lesson' };
  const DIRECTIONS = { en_ar: 'English → Arabic', ar_en: 'Arabic → English' };
  const VERDICTS = ['right', 'close', 'wrong'];
  const POINTS = { right: 1, close: 0.5, wrong: 0 };
  const AR = /[؀-ۿ]/;
  const norm = s => String(s || '').normalize('NFKD').replace(/[ً-ٰٟـ]/g, '').replace(/[أإآ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const ts = r => String((r && (r.created_at || r.ts)) || '');

  // append-only tables: an undo is a row {kind:'undo', undoes:<id>}; an undo of an undo puts the row back; a replayed
  // queue (same id twice) is one row
  function effective(rows) {
    const byId = new Map();
    for (const r of rows || []) if (r && r.id && !byId.has(r.id)) byId.set(r.id, r);
    const all = [...byId.values()].sort((a, b) => ts(a).localeCompare(ts(b)) || String(a.id).localeCompare(String(b.id)));
    const undone = new Set();
    for (const r of all) if (r.kind === 'undo' && r.undoes) { if (undone.has(r.undoes)) undone.delete(r.undoes); else undone.add(r.undoes); }
    const liveUndo = new Set(all.filter(r => r.kind === 'undo' && !undone.has(r.id)).map(r => r.id));
    const gone = new Set(all.filter(r => r.kind === 'undo' && liveUndo.has(r.id)).map(r => r.undoes));
    return all.filter(r => r.kind !== 'undo' && !gone.has(r.id));
  }

  // ---- her uploads as card sets -------------------------------------------------------------------------------
  function uploadSets(rows) {
    return effective(rows).filter(r => r.kind === 'upload').map(u => {
      const cards = (Array.isArray(u.rows) ? u.rows : []).map((c, i) => ({
        key: 'u:' + u.id + ':' + (i + 1), arabizi: String(c.arabizi || c.arabic || ''), arabic: c.arabizi ? String(c.arabic || '') : '',
        english: String(c.english || ''), plural: String(c.plural || ''), notes: String(c.notes || ''), topic: u.title || 'From the tutor', upload: u.id,
      })).filter(c => (c.arabizi || c.arabic) && (c.english || (c.arabizi && c.arabic)));
      return { id: 'u:' + u.id, uploadId: u.id, title: u.title || 'From the tutor', keep: u.keep || 'temporary', source: u.source || 'file', source_ref: u.source_ref || '',
               created_at: u.created_at || '', cards, n: cards.length };
    }).sort((a, b) => ts(b).localeCompare(ts(a)));
  }
  // Q7: a permanent upload is a reminder "add these to the Doc"; a card counts as in the Doc only once the Doc import sees it
  function docIndex(words) {
    const idx = { ar: new Set(), lat: new Set() };
    for (const w of words || []) { if (w.arabic) idx.ar.add(norm(w.arabic)); for (const s of [w.arabizi, w.house_spelling].concat(w.aliases || [])) if (s) idx.lat.add(norm(s)); }
    return idx;
  }
  function inDoc(card, idx) {
    if (card.arabic && idx.ar.has(norm(card.arabic))) return true;
    const a = card.arabizi && !AR.test(card.arabizi) ? norm(card.arabizi) : '';
    return !!a && idx.lat.has(a);
  }
  function permanentReminder(sets, docWords) {
    const idx = docIndex(docWords), out = [];
    for (const s of sets || []) if (s.keep === 'permanent') for (const c of s.cards) out.push({ ...c, set: s.title, uploadId: s.uploadId, in_doc: inDoc(c, idx) });
    return out;
  }

  // ---- shaky words (Q3) ----------------------------------------------------------------------------------------
  // shaky = {lessons:[d1, d2], words:[{key, arabizi, arabic, english, kind:'wrong'|'asked', date, mmss}]} (scripts/build_student_data.py);
  // log = card_results rows ({word_key, result, ts, undone}). A word leaves the set once it has two right answers on cards
  // after the lesson it slipped in ("drop a word once he gets it right twice").
  function shakyCards(shaky, log) {
    const live = (log || []).filter(r => r && r.word_key && r.result === 'got' && !r.undone && !r.undone_at);
    return ((shaky && shaky.words) || []).map(w => {
      const n = live.filter(r => r.word_key === w.key && String(r.ts) > w.date + 'T23:59:59').length;
      return { ...w, topic: 'Shaky words', right_since: n };
    }).filter(w => w.right_since < 2);
  }

  // ---- one task's state -----------------------------------------------------------------------------------------
  function latestReply(task, replies) {
    return (replies || []).filter(r => r.task_id === task.id).sort((a, b) => ts(b).localeCompare(ts(a)))[0] || null;
  }
  function latestVerdict(reply, verdicts) {
    if (!reply) return null;
    const live = effective(verdicts).filter(v => v.reply_id === reply.id && v.kind === 'verdict' && VERDICTS.includes(v.verdict));
    return live.sort((a, b) => ts(b).localeCompare(ts(a)))[0] || null;
  }
  function taskState(task, replies, verdicts) {
    const reply = latestReply(task, replies), ai = reply && reply.ai && VERDICTS.includes(reply.ai.verdict) ? reply.ai : null, verdict = latestVerdict(reply, verdicts);
    const state = !reply ? 'todo' : verdict ? 'done' : (reply.ai ? 'waiting' : 'checking');
    return { state, reply, ai, verdict, final: verdict ? verdict.verdict : null };
  }
  // Q5: homework's own number = Amal's verdicts only (right 1, close ½, wrong 0); the AI's word never counts
  function score(tasks, replies, verdicts) {
    const text = effective(tasks).filter(t => t.kind in KINDS && t.kind !== 'cards');
    const out = { total: text.length, done: 0, right: 0, close: 0, wrong: 0, points: 0, pct: null, waiting: 0, checking: 0, todo: 0, agreed: 0, overruled: 0 };
    for (const t of text) {
      const s = taskState(t, replies, verdicts);
      out[s.state]++;
      if (s.state === 'done') { out[s.final]++; out.points += POINTS[s.final]; if (s.verdict.agrees === true) out.agreed++; if (s.verdict.agrees === false) out.overruled++; }
    }
    out.pct = out.done ? Math.round(1000 * out.points / out.done) / 10 : null;
    return out;
  }
  // a cards assignment: distinct cards of that set answered since it was assigned (cards.html rounds carry subject 'sel:<tile>')
  function cardsDone(task, log) {
    const since = task.created_at || '', keys = new Set();
    for (const r of log || []) if (r && !r.undone && !r.undone_at && r.subject === 'sel:' + task.set_ref && String(r.ts) >= since) keys.add(r.word_key);
    return keys.size;
  }
  // PG-35 (Medi 2026-10-08 "see why amal uploaded two card sets but the student page only shows one"): every set she
  // uploads is the student's to do, assigned or not. An upload with no live cards task pointing at it becomes a cards row
  // of its own (set_ref u:<upload>, no lesson date, upload:true); once she assigns it for a lesson that task takes over.
  function unassignedUploads(uploads, tasks) {
    const assigned = new Set(effective(tasks).filter(t => t.kind === 'cards').map(t => t.set_ref));
    return uploadSets(uploads).filter(s => !assigned.has(s.id)).map(s => ({
      id: 'up:' + s.uploadId, kind: 'cards', upload: true, set_ref: s.id, set_title: s.title, keep: s.keep,
      n_cards: s.n || (uploads || []).filter(u => u.id === s.uploadId).map(u => u.n | 0)[0] || 0, lesson_date: null, created_at: s.created_at,
    }));
  }
  const scriptOf = s => { const t = String(s || ''); const ar = AR.test(t), lat = /[A-Za-z]/.test(t); return ar && lat ? 'mixed' : ar ? 'arabic' : /[235678]/.test(t) ? 'arabizi' : 'english'; };

  return { KINDS, DIRECTIONS, VERDICTS, POINTS, effective, uploadSets, permanentReminder, docIndex, inDoc, shakyCards, latestReply, latestVerdict, taskState, score, cardsDone, unassignedUploads, scriptOf, norm };
});
