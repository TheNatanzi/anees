// Guard for rule S1 on Medi-facing error cards (Medi 2026-09-26: "why no arabizi again. How do we stop you from doing
// this?"). Renders every Arabic word shown on the Lessons page error cards (vocab + grammar: headword, what he said,
// her fix, wrong -> right) through the ONE shared renderer and lists each word that would still show "Unverified
// spelling stays in Arabic". review_lesson.py runs it after the pages are built and does not finish while gaps remain.
//   node scripts/arabizi_gaps.cjs [--json out.json]     exit 1 when any gap is left
const fs = require('fs'), path = require('path');
const DOCS = path.resolve(__dirname, '..', 'docs');
const J = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const az = require(path.join(DOCS, 'js', 'word-bank-arabizi.js'));
const house = (J(path.join(DOCS, 'data', 'house_spelling.json')).items) || {};
const words = J(path.join(DOCS, 'data', 'words.json')).items.map(w => { const h = house[w.match_loose]; return h && h.house ? Object.assign({}, w, { house_spelling: h.house }) : w; });
const render = az.create(words, J(path.join(DOCS, 'data', 'word-bank-catalog.json')), J(path.join(DOCS, 'data', 'arabizi-extra.json')));
const AR = /[\u0621-\u064A]/;
const gaps = new Map();
for (const f of fs.readdirSync(path.join(DOCS, 'data', 'lessons')).filter(f => /^20\d\d-\d\d-\d\d\.json$/.test(f))) {
  const L = J(path.join(DOCS, 'data', 'lessons', f)), d = f.slice(0, 10);
  const strs = [];
  for (const v of L.vocab_errors || []) strs.push(v.arabic, v.fix, v.said);
  for (const g of L.grammar_errors || []) strs.push(g.said, g.fix, g.wrong, g.right);
  for (const s of strs) {
    if (!s || !AR.test(s)) continue;
    for (const tok of String(s).split(/[^\u0621-\u064A\u064B-\u0652\u0670]+/)) {
      if (!tok || !AR.test(tok)) continue;
      if (!render(tok).approximate) continue;
      const g = gaps.get(tok) || { word: tok, n: 0, lessons: new Set(), example: s };
      g.n++; g.lessons.add(d); gaps.set(tok, g);
    }
  }
}
const out = [...gaps.values()].sort((a, b) => b.n - a.n).map(g => ({ word: g.word, n: g.n, lessons: [...g.lessons].sort(), example: g.example }));
const i = process.argv.indexOf('--json');
if (i > 0) fs.writeFileSync(process.argv[i + 1], JSON.stringify({ gaps: out.length, words: out }, null, 1));
console.log('arabizi gaps on error cards:', out.length, 'words,', out.reduce((a, g) => a + g.n, 0), 'uses');
process.exit(out.length ? 1 : 0);
