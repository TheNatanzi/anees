// Step 6 hand check: render 100 random transcript lines (Medi + Amal, Arabic) through the ONE shared renderer
// (docs/js/word-bank-arabizi.js with her Doc + house spellings + catalog + arabizi-extra) and write them out for a
// reader to grade against Amal's spelling (rule S1). Seeded so the sample is reproducible.
//   node scripts/arabizi_check.cjs [seed] -> data/lesson-work/full-audit/arabizi-check-100.md (+ .json)
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..'), DOCS = path.join(ROOT, 'docs');
const J = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const az = require(path.join(DOCS, 'js', 'word-bank-arabizi.js'));
const house = (J(path.join(DOCS, 'data', 'house_spelling.json')).items) || {};
const words = J(path.join(DOCS, 'data', 'words.json')).items.map(w => { const h = house[w.match_loose]; return h && h.house ? Object.assign({}, w, { house_spelling: h.house }) : w; });
const render = az.create(words, J(path.join(DOCS, 'data', 'word-bank-catalog.json')), J(path.join(DOCS, 'data', 'arabizi-extra.json')));
const AR = /[ء-غف-ي]/;
const DATES = ['2026-08-25', '2026-09-04', '2026-09-05', '2026-09-10', '2026-09-11', '2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19', '2026-09-21', '2026-09-23'];
let lines = [];
for (const d of DATES) for (const t of J(path.join(DOCS, 'data', 'lessons', d + '.json')).turns) {
  if (t.who === 'chat' || !AR.test(t.text)) continue;
  const ar = (t.text.match(/[ء-غف-ي]+/g) || []).length;
  if (ar >= 3) lines.push({ date: d, t: t.t, who: t.who, text: t.text });
}
let seed = parseInt(process.argv[2] || '20260926', 10);
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const pick = [];
while (pick.length < 100 && lines.length) { const i = Math.floor(rnd() * lines.length); pick.push(lines.splice(i, 1)[0]); }
const out = pick.map((l, i) => { const r = render(l.text); return { n: i + 1, date: l.date, t: Math.round(l.t), who: l.who, source: l.text, arabizi: r.text, approximate: r.approximate }; });
const md = ['# Arabizi hand check - 100 random transcript lines (seed ' + process.argv[2] + ')', '',
  'Grade each line: 1 = every Latin word is Amal\'s spelling (her Doc / chat / her letters 2 3 5 6 7 8 9, bn- for we), or the word is left in Arabic; 0 = an invented or wrong spelling appears. "approximate" = the renderer left something in Arabic on purpose.', ''];
for (const o of out) md.push(`## ${o.n} - ${o.date} ${o.t}s ${o.who}${o.approximate ? ' (approximate)' : ''}`, `- source: ${o.source}`, `- rendered: ${o.arabizi}`, '');
const dir = path.join(ROOT, 'data', 'lesson-work', 'full-audit');
fs.writeFileSync(path.join(dir, 'arabizi-check-100.md'), md.join('\n'));
fs.writeFileSync(path.join(dir, 'arabizi-check-100.json'), JSON.stringify({ seed: process.argv[2] || '20260926', lines: out }, null, 1));
console.log('wrote 100 lines,', out.filter(o => o.approximate).length, 'approximate (part left in Arabic)');
