// Every saved flashcard set from the tutor (docs/data/uploads.json, the amal_uploads mirror) is read the way Flashcards
// shows it, and each card must have an Arabic side and an English side that match up: no blank side, no Arabic letters on
// the English side, no English or Arabizi mixed into the Arabic (Medi 2026-10-28: "create a check system everytime a card
// set is uploaded to make sure the english and arabic sides coinside and there are no blanks"). Her upload screen runs the
// same check before saving (docs/js/hub/upload-task.js); this one catches anything saved another way. Exit 1 = a problem.
//   node scripts/check_upload_cards.cjs [uploads.json]
const path = require('path');
const H = require(path.join(__dirname, '..', 'docs', 'js', 'homework-core.js'));
const file = process.argv[2] || path.join(__dirname, '..', 'docs', 'data', 'uploads.json');
const rows = (require(path.resolve(file)) || {}).rows || [];
let n = 0, bad = 0;
for (const s of H.uploadCardsRaw(rows)) {
  const probs = H.checkCards(s.cards).filter(p => !p.soft);
  n += s.cards.length; bad += probs.length;
  for (const p of probs.slice(0, 5)) console.log(JSON.stringify({ set: s.title, card: p.i + 1, arabizi: p.arabizi, arabic: p.arabic, english: p.english, why: p.why.join('; ') }));
  if (probs.length > 5) console.log(JSON.stringify({ set: s.title, more: probs.length - 5 }));
}
console.log('upload cards: %d checked, %d with a blank or mixed-up side%s', n, bad, bad ? ' (hidden on Flashcards until the tutor fixes the set)' : '');
process.exit(bad ? 1 : 0);
