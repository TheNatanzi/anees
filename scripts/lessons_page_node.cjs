// Helper for scripts/build_lessons_page_data.py. Runs the Word Bank page's own code (word-bank-core.js,
// word-bank-review.js, word-bank-arabizi.js) on the published data so per-lesson word scores count
// exactly the way the Word Bank page counts them. Read-only: prints JSON to the file given.
//   node scripts/lessons_page_node.cjs <in.json> <out.json>
//   in.json = {"arabic": ["...", ...]}  strings to render in Amal's spelling
'use strict';
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', 'docs');
const J = f => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'));
const C = require(path.join(ROOT, 'js', 'word-bank-core.js'));
const Rv = require(path.join(ROOT, 'js', 'word-bank-review.js'));
const Az = require(path.join(ROOT, 'js', 'word-bank-arabizi.js'));

const inp = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const house = J('house_spelling.json').items || {};
const words = (J('words.json').items || []).map(w => { const h = house[w.match_loose]; return h && h.house ? { ...w, house_spelling: h.house } : w; });
const catalog = J('word-bank-catalog.json');
const clips = J('word-bank-clips.json').clips || {};
const review = J('word-bank-review.json');
let events = J('word-bank-evidence.json').events || [];

// Same steps, same order as docs/js/word-bank.js load().
const reviewed = Rv.apply(events, review);
events = C.prepareEvidence(reviewed.events.map(e => reviewed.stale.includes(e.id) ? { ...e, needs_review: true } : e));
events = events.map(e => { const clip = clips[e.id]; const bound = clip && clip.source_sha256 === e.source_sha256 && clip.lesson === e.lesson_date && clip.start <= e.t_start && clip.end >= e.t_end && (e.context || []).every(r => Number.isFinite(r.timeline_start) && Number.isFinite(r.timeline_end) && r.timeline_start >= clip.start && r.timeline_end <= clip.end); return bound ? { ...e, sentence_audio_url: clip.sentence_audio_url } : e; });
const rows = C.models(words, catalog, events, []);

// Same label as word-bank.js outcome().
function outcome(e) { const p = C.points(e); if (e.grammar_only || e.classification === 'grammar') return 'Grammar · not vocabulary'; return e.self_corrected && p === 1 ? 'Correct · self-corrected' : e.confusion_pair && p === 0 ? 'Wrong · linked word confusion' : e.ignored && !e.immediate_repeat && !e.is_echo ? 'Not scored' : e.observation_only ? 'Said here · another word intended' : e.scored_in_event ? 'Same attempt · counted once' : p === 1 ? 'Correct' : p === .5 ? 'Partial' : p === 0 ? 'Wrong' : e.immediate_repeat || e.is_echo ? 'Repeat · not scored' : 'Ignored pending review'; }

const byKey = new Map(words.map(w => [w.key, w]));
const scored = [];
for (const r of rows) for (const f of r.entries) for (const e of f.events) {
  if (e.speaker !== 'Medi') continue;
  const p = C.points(e);
  if (p === null) continue;
  const said = C.sentence(e);
  const w = byKey.get(e.word_key) || {};
  scored.push({
    id: e.id, date: C.date(e), row: r.id, entry: f.id, entry_label: f.label, word_key: e.word_key,
    arabic: f.arabic || w.arabic || r.arabic || '', english: r.english || w.english || '',
    name: r.name, points: p, label: outcome(e), t_start: e.t_start, t_end: e.t_end, text: e.text,
    said, said_html: Rv.mark(said, p === 0 ? [e.text] : [], p === .5 ? [e.text] : []),
    reason: e.reason || null, adjudication: e.adjudication || null, intended: e.intended_meaning || null,
    sentence_audio_url: e.sentence_audio_url || null, legacy_clip: e.clip || null, audio_url: e.audio_url || null,
    source_sha256: e.source_sha256 || null, row_id: e.row_id,
  });
}

// Amal-side first appearances of each list word (any speaker), for the new-words list.
const firstSeen = {};
for (const e of events) {
  if (!e.word_key || !byKey.has(e.word_key)) continue;
  const d = C.date(e); if (!d) continue;
  const k = e.word_key;
  if (!firstSeen[k] || d < firstSeen[k].date) firstSeen[k] = { date: d, amal: [], medi: 0 };
  if (firstSeen[k].date === d) { if (e.speaker === 'Amal') firstSeen[k].amal.push(e.t_start); else if (e.speaker === 'Medi') firstSeen[k].medi++; }
}

const render = Az.create(words, catalog, J('arabizi-extra.json'));
const arabizi = {};
for (const s of inp.arabic || []) { const r = render(s); arabizi[s] = { text: r.text, approximate: !!r.approximate }; }
// the said-sentences of scored misses too, so the per-lesson file can show them in her spelling
for (const s of scored) if (s.points < 1 && s.said && !arabizi[s.said]) { const r = render(s.said); arabizi[s.said] = { text: r.text, approximate: !!r.approximate }; }
const wordInfo = {};
for (const k of new Set([...Object.keys(firstSeen), ...scored.map(s => s.word_key).filter(k => byKey.has(k))])) { const w = byKey.get(k); wordInfo[k] = { arabic: w.arabic, english: w.english, house: w.house_spelling || null, doc_arabizi: w.arabizi, subtopic: w.subtopic }; }

fs.writeFileSync(process.argv[3], JSON.stringify({ scored, firstSeen, wordInfo, arabizi, stale_reviews: reviewed.stale.length }));
console.log('scored', scored.length, 'stale reviews', reviewed.stale.length);
