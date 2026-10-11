// Arabizi for the tutor's key-check cards (scripts/build_tutor_key_check.py; RULES.md S1, PG-44: Arabizi first, the Arabic
// small after). The ONE shared renderer (docs/js/word-bank-arabizi.js) with her Doc + house spellings + catalog +
// arabizi-extra, the Lessons page's options (scope 'lessons', AZ-snap) - the same Arabizi the Lessons page shows.
//   echo '["مرحبا", "أنا شوي عيان"]' | node scripts/tutor_key_check_arabizi.cjs   -> [{"text": "...", "approximate": false}, ...]
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..'), DOCS = path.join(ROOT, 'docs');
const J = (p, d) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return d; } };
const az = require(path.join(DOCS, 'js', 'word-bank-arabizi.js'));
const house = (J(path.join(DOCS, 'data', 'house_spelling.json'), {}).items) || {};
const words = ((J(path.join(DOCS, 'data', 'words.json'), {}).items) || []).map(w => { const h = house[w.match_loose]; return h && h.house ? Object.assign({}, w, { house_spelling: h.house }) : w; });
const render = az.create(words, J(path.join(DOCS, 'data', 'word-bank-catalog.json'), {}), J(path.join(DOCS, 'data', 'arabizi-extra.json'), {}), { scope: 'lessons', snap: true });
const lines = JSON.parse(fs.readFileSync(0, 'utf8') || '[]');
process.stdout.write(JSON.stringify(lines.map(s => { try { const r = render(String(s || '')); return { text: r.text, approximate: !!r.approximate }; } catch (e) { return { text: null, approximate: true }; } })));
