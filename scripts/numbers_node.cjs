// Helper for scripts/check_numbers.py (eng audit 2026-09-29). Runs the PAGES' OWN code (word-bank-core.js,
// word-bank-review.js, vocabulary-stats.js, lesson-math.js) on the published data, offline, and prints the numbers
// those pages show, so the checker can compare them with lessons.json and with its own recompute from raw.
//   node scripts/numbers_node.cjs <docs dir> <out.json>
'use strict';
const fs = require('fs'), path = require('path');
const DOCS = path.resolve(process.argv[2] || path.join(__dirname, '..', 'docs'));
const J = f => JSON.parse(fs.readFileSync(path.join(DOCS, 'data', f), 'utf8'));
const has = f => fs.existsSync(path.join(DOCS, 'data', f));
const C = require(path.join(DOCS, 'js', 'word-bank-core.js'));
const Rv = require(path.join(DOCS, 'js', 'word-bank-review.js'));
const S = require(path.join(DOCS, 'js', 'vocabulary-stats.js'));
// A checkout from before 2026-09-29 has no lesson-math.js: fall back to the plain formulas and say so (the check fails).
const LM = fs.existsSync(path.join(DOCS, 'js', 'lesson-math.js')) ? require(path.join(DOCS, 'js', 'lesson-math.js')) : {
  missing: true, approx: () => false, why: () => '',
  pooledWords: L => { const W = L.filter(l => l.words && l.words.scored > 0), sc = W.reduce((s, l) => s + l.words.scored, 0), pt = W.reduce((s, l) => s + l.words.right + l.words.partial / 2, 0); return { pct: sc ? 100 * pt / sc : null, n: W.length, points: pt, scored: sc }; },
  pooledGrammar: L => { const G = L.filter(l => l.grammar && l.grammar.uses > 0 && !l.grammar.estimate), u = G.reduce((s, l) => s + l.grammar.uses, 0), m = G.reduce((s, l) => s + l.grammar.mistakes, 0); return { pct: u ? 100 * (u - m) / u : null, n: G.length, uses: u, slips: m }; } };

const house = has('house_spelling.json') ? (J('house_spelling.json').items || {}) : {};
const words = (J('words.json').items || []).map(w => { const h = house[w.match_loose]; return h && h.house ? { ...w, house_spelling: h.house } : w; });
const catalog = J('word-bank-catalog.json'), review = J('word-bank-review.json');
const slipsDoc = has('word-bank-audit-slips.json') ? J('word-bank-audit-slips.json') : null;
const withSlips = Rv.withSlips || ((e) => e);
// Same steps, same order as docs/js/word-bank.js load() (published-evidence path).
const raw = withSlips(J('word-bank-evidence.json').events || [], slipsDoc);
const reviewed = Rv.apply(raw, review);
const events = C.prepareEvidence(reviewed.events.map(e => reviewed.stale.includes(e.id) ? { ...e, needs_review: true } : e));
const rows = C.models(words, catalog, events, []);

// per lesson date: scored attempts by points, split Word Bank vs audit slips, distinct forms
const byDate = {};
const F = S.forms(rows);
for (const x of F) for (const a of x.form.speaking.attempts) {
  const d = C.date(a), b = byDate[d] || (byDate[d] = { p1: 0, p05: 0, p0: 0, slips_p0: 0, slips_p05: 0, forms: new Set() });
  if (a.p === 1) b.p1++; else if (a.p === .5) { b.p05++; if (a.source === 'audit-2026-09-26') b.slips_p05++; } else { b.p0++; if (a.source === 'audit-2026-09-26') b.slips_p0++; }
  b.forms.add(x.form.id);
}
for (const d in byDate) { byDate[d].unique_forms = byDate[d].forms.size; delete byDate[d].forms; }
// Progress › Vocab per-lesson series, all lessons (the page's own function)
const series = S.perLesson(rows, events, new Date('2100-01-01T12:00:00'), 'all').series.map(l => ({ date: l.date, correct: l.correct, hinted: l.hinted, wrong: l.wrong, total: l.total, unique: l.unique }));
// status counts (Word Bank headline, Progress Words known / Mastered)
const status = {}; for (const x of F) status[x.form.speaking.status] = (status[x.form.speaking.status] || 0) + 1;
const entries = rows.filter(r => !r.grammar_only).flatMap(r => r.entries);
const m = C.metrics(entries, new Date('2100-01-01T12:00:00'));
// status points check (spec: Mastered 10 · Good 8 · Shaky 5 · Wrong 0; accuracy = Σ points ÷ (tested × 10))
const tested = entries.filter(e => e.speaking.status !== 'Untested');
const pts = tested.reduce((s, e) => s + C.WEIGHTS[e.speaking.status], 0);
// every scored form's status against the written rules (plan/word-bank-specification.md §4): from 10 attempts the
// latest-10 bands; below 10 the streak rules (not re-derived here: the page's own score() is the rule)
const bandProblems = [];
for (const x of F) { const sp = x.form.speaking; if (sp.count >= 10) { const acc = sp.latest.reduce((s, e) => s + e.p, 0) * 10;
  const days = new Set(sp.latest.filter(e => e.p === 1).map(e => String(e.lesson_id || C.date(e))));
  const want = acc >= 90 ? (days.size >= 2 ? 'Mastered' : 'Good') : acc >= 75 ? 'Good' : acc >= 50 ? 'Shaky' : 'Wrong';
  if (want !== sp.status || Math.abs(acc - sp.accuracy) > 1e-9) bandProblems.push({ form: x.form.id, count: sp.count, accuracy: sp.accuracy, status: sp.status, want }); } }
const L = J('lessons.json').lessons;
// filled pauses in each lesson's own turns, by the pages' one test (lesson-math countFillers)
const fillersInTurns = {};
if (LM.countFillers) for (const l of L) { try { const D = J(path.join('lessons', l.date + '.json'));
  fillersInTurns[l.date] = (D.turns || []).filter(t => t.who === 'Medi').reduce((s, t) => s + LM.countFillers(t.text), 0); } catch (e) { fillersInTurns[l.date] = null; } }
const pw = LM.pooledWords(L), pg = LM.pooledGrammar(L), ptk = LM.pooledTalk ? LM.pooledTalk(L) : { pct: null, n: 0 }, pfl = LM.pooledFillers ? LM.pooledFillers(L) : { perMin: null, n: 0 };
const out = {
  wb_by_date: byDate, vocab_series: series, status, forms: F.length,
  wb_accuracy: m.accuracy, wb_known: m.known, wb_points_accuracy: tested.length ? pts * 10 / tested.length : null,
  band_problems: bandProblems.slice(0, 20), band_problem_count: bandProblems.length,
  slips: slipsDoc ? { events: (slipsDoc.events || []).length, unplaced: (slipsDoc.unplaced || []).map(x => ({ date: x.date, uid: x.uid, kind: x.kind })) } : null,
  slips_in_models: F.reduce((n, x) => n + x.form.speaking.attempts.filter(a => a.source === 'audit-2026-09-26').length, 0),
  pooled_words: { pct: pw.pct, n: pw.n, points: pw.points, scored: pw.scored },
  pooled_grammar: { pct: pg.pct, n: pg.n, uses: pg.uses, slips: pg.slips },
  pooled_talk: { pct: ptk.pct, n: ptk.n }, pooled_fillers: { perMin: pfl.perMin, n: pfl.n },
  approx: L.map(l => ({ date: l.date, approx: LM.approx([l]), why: LM.why([l]) })),
  fillers_in_turns: fillersInTurns, stale_reviews: reviewed.stale.length, lesson_math_missing: !!LM.missing,
};
fs.writeFileSync(process.argv[3], JSON.stringify(out));
