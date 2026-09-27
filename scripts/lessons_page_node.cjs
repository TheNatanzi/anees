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

// Sheet lookup + Word Bank rating (Medi 2026-09-26: "label it 'not on sheet'" / "add the rating (shaky, mastered) with my
// percentage correct"). A phrase is on the sheet when it is a sheet word (or one of its forms), or when every token of it
// appears in some sheet word. Rating = the Word Bank speaking status of that word + its scored tries.
const norm = s => String(s || '').replace(/[\u064B-\u0652\u0670\u0640]/g, '').replace(/[أإآ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه')
  .replace(/[^\u0621-\u064A\s]/g, ' ').replace(/\s+/g, ' ').trim();
const noAl = s => s.split(' ').map(t => t.length > 3 && t.startsWith('ال') ? t.slice(2) : t).join(' ');
const rowByKey = new Map(); for (const r of rows) for (const k of (r.keys || [r.key])) rowByKey.set(k, r);
function rating(key) {
  const r = rowByKey.get(key); if (!r) return null;
  let n = 0, right = 0, part = 0, wrong = 0, best = null;
  for (const f of r.entries) { const sp = f.speaking || {}; for (const a of sp.attempts || []) { const p = C.points(a); if (p === null) continue; n++; if (p === 1) right++; else if (p === .5) part++; else wrong++; }
    if (!best || (sp.count || 0) > (best.count || 0)) best = sp; }
  return { status: (best && best.status) || 'Untested', n, right, partial: part, wrong, pct: n ? Math.round(100 * (right + .5 * part) / n) : null };
}
const phrase = new Map(), tokens = new Map();
const addForm = (a, key) => { const p = noAl(norm(a)); if (!p) return; if (!phrase.has(p)) phrase.set(p, key);
  for (const t of p.split(' ')) { const cur = tokens.get(t); if (!cur || cur.len > p.split(' ').length) tokens.set(t, { key, len: p.split(' ').length }); } };
for (const w of words) { addForm(w.arabic, w.key); if (w.plural) addForm(w.plural, w.key); }   // her plural column too
for (const r of rows) for (const f of r.entries) addForm(f.arabic, r.key);
// every conjugated form the Word Bank knows for a word (its search text), and each b- present form without the b-
// (Medi 2026-09-26: "Testana is the command tense of bastana" - تستنى is بتستنى without b-, both are his list word)
const addTok = (t, key) => { if (!t) return; const cur = tokens.get(t); if (!cur || cur.len > 1) tokens.set(t, { key, len: 1 }); };
for (const r of rows) for (const raw of String(r.search || '').split(' ')) {
  const t = norm(raw); if (!t || /\s/.test(t) || t.length < 2) continue;
  addTok(t, r.key); if (t.length > 3 && t[0] === 'ب') addTok(t.slice(1), r.key);
}
// a pronoun ending on a known form is still that word (بتضايقني = بتضايق + ني)
const ENDS = ['كم', 'هم', 'ها', 'نا', 'ني', 'ك', 'ه', 'ات', 'ين', 'ون'];   // + adjective/plural endings: قصيرات = her 2aseer + -aat   // not a bare -i / -u: نفسي is 'psychological', not نفس + i (Medi 2026-09-27)
const tok = t => tok0(t) || ENDS.reduce((hit, e) => hit || (t.length - e.length >= 3 && t.endsWith(e) ? tok0(t.slice(0, -e.length)) : null), null);
const tok0 = t => tokens.get(t) || (t.length > 3 && t[0] === 'ا' ? tokens.get(t.slice(1)) : null) || (t.length > 3 && t[0] === 'و' ? tokens.get(t.slice(1)) : null);
const sheet = {};
// A word pair counts only when EACH word is on the list with the meaning used here (Medi 2026-09-27: دكتور عام and
// دكتور نفسي are new words - his list has عام / نفس with other meanings). Meaning check = the list word's English shares a
// word with the card's English (تستنى 'I wait' + دقيقة 'Minute' vs 'Can you wait a minute?').
const enw = t => new Set(String(t || '').toLowerCase().match(/[a-z]{3,}/g) || []);
const sameMeaning = (key, en) => { const E = enw(en); if (!E.size) return true; const w = byKey.get(key) || rowByKey.get(key) || {};
  for (const x of enw(w.english)) if (E.has(x) || E.has(x + 's') || E.has(x.replace(/s$/, ''))) return true; return false; };
// her Latin spellings too: the plural column is Latin only (أصابع = her 'Asaabe3', plural of Osba3 - Medi 2026-09-27)
const lat = t => String(t || '').toLowerCase().replace(/^ana\s+/, '').replace(/[^a-z0-9]/g, '').replace(/([aeiou])+/g, '$1');   // Tanaaneer = her Tananeer
const latIndex = new Map();
for (const w of words) for (const x of [w.arabizi, w.plural, w.house_spelling]) { const k = lat(x); if (k.length >= 3 && !latIndex.has(k)) latIndex.set(k, w.key); }
const renderLat = Az.create(words, catalog, J('arabizi-extra.json'));
for (const entry of inp.sheet || []) {
  const [s, en] = String(entry).split('');
  let hit = null, how = null;
  for (const alt of String(s).split(/\s=\s|\s-\s/)[0].replace(/\([^)]*\)/g, ' ').split('/')) {
    const p = noAl(norm(alt)); if (!p) continue;
    if (phrase.has(p)) { hit = phrase.get(p); how = 'word'; break; }
    const ts = p.split(' ').map(tok);
    if (ts.every(Boolean) && (ts.length === 1 || ts.every(x => sameMeaning(x.key, en)))) { hit = ts.slice().sort((a, b) => a.len - b.len)[0].key; how = 'part'; break; }
  }
  if (!hit) { const r = renderLat(String(s).split('/')[0]); const k = lat(r && r.text); if (k && latIndex.has(k)) { hit = latIndex.get(k); how = 'latin'; } }
  // a rating belongs to the whole word: never borrow it from one piece of a longer phrase (دكتور نفسي showed 'Good' from دكتور)
  const one = String(s).split(/\s=\s|\s-\s/)[0].replace(/\([^)]*\)/g, ' ').split('/').some(a => noAl(norm(a)).split(' ').length === 1);
  sheet[entry] = { on_sheet: !!hit, key: hit, match: how, rating: hit && (how === 'word' || how === 'latin' || one) ? rating(hit) : null };
}
const ratings = {}; for (const s of scored) if (s.word_key && !ratings[s.word_key]) ratings[s.word_key] = rating(s.word_key);

fs.writeFileSync(process.argv[3], JSON.stringify({ scored, firstSeen, wordInfo, arabizi, sheet, ratings, stale_reviews: reviewed.stale.length }));
console.log('scored', scored.length, 'stale reviews', reviewed.stale.length);
