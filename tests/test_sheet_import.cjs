// AM-21 "Upload flashcards" on the Tutor page (Medi 2026-10-05: "upload flashcards where she can give a google link like this
// one or she can upload a file"): the browser reads her list, guesses the columns, keeps her text as written (S1).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const SI = require('../docs/js/sheet-import.js');

test('AM-21 a Google Sheets / Docs link is recognised and read as CSV / text in the background; anything else is refused', () => {
  const s = SI.linkInfo('https://docs.google.com/spreadsheets/d/1tBx8jWOLYMtsGdaqgWviyS_5Rfjp6cT2WBUTu4TfVQA/edit?pli=1&gid=0#gid=0');
  assert.equal(s.kind, 'sheet'); assert.equal(s.id, '1tBx8jWOLYMtsGdaqgWviyS_5Rfjp6cT2WBUTu4TfVQA'); assert.equal(s.gid, '0');
  assert.match(s.csvUrl, /gviz\/tq\?tqx=out:csv&gid=0$/);
  const d = SI.linkInfo('https://docs.google.com/document/d/1SCYeIEu-N-wxqGe7Y_M4dKTwAPICQKM-_3SgbF4whME/edit');
  assert.equal(d.kind, 'doc'); assert.match(d.txtUrl, /export\?format=txt$/);
  assert.equal(SI.linkInfo('https://quizlet.com/123/x'), null);
  assert.equal(SI.linkInfo(''), null);
});

test('AM-21 the sample sheet (Transliteration / Arabic / English header) gives Arabizi, Arabic, English columns and 22 cards as written', () => {
  const csv = 'Transliteration,Arabic,English\nAwal,أول,First / beginning\n"Awal + noun",أول + اسم,First / the first…\nEl-kul,الكل,Everybody / all\nShu el-farq,شو الفرق,"What’s the difference"\n';
  const rows = SI.parseText(csv);
  const cols = SI.detectColumns(rows);
  assert.deepEqual([cols.arabizi, cols.arabic, cols.english, cols.header], [0, 1, 2, true]);
  const cards = SI.toCards(rows, cols);
  assert.equal(cards.length, 4);
  assert.deepEqual(cards[0], { arabizi: 'Awal', arabic: 'أول', english: 'First / beginning', plural: '', notes: '' });
  assert.equal(cards[3].english, 'What’s the difference');       // her text, untouched (S1)
});

test('AM-21 no header: the Arabic column is found by its letters, her Arabizi by the 2/3/5/6/7/8/9 digits, English is the rest', () => {
  const rows = SI.parseText('water\tMayy\tمي\nI woke up\tana bas7a\tصحيت\nappointment\tmaw3ed\tموعد');
  const cols = SI.detectColumns(rows);
  assert.deepEqual([cols.english, cols.arabizi, cols.arabic, cols.header], [0, 1, 2, false]);
  assert.equal(SI.toCards(rows, cols)[1].arabizi, 'ana bas7a');
});

test('AM-21 a pasted or Doc list reads one card per line: "a | b | c", "a = b", "a - b", "b (a)"', () => {
  const rows = SI.parseText('1. Awal | أول | first\nMaw3ed = appointment\nMayy - water\nsick (3ayAn)\n\njust a line with nothing');
  assert.deepEqual(rows, [['Awal', 'أول', 'first', ''], ['Maw3ed', '', 'appointment', ''], ['Mayy', '', 'water', ''], ['3ayAn', '', 'sick', '']]);   // laid out by script: word, Arabic, English
  const cols = SI.detectColumns(rows);
  const cards = SI.toCards(rows, cols);
  assert.equal(cards.length, 4);
  assert.ok(cards.every(c => c.arabizi && c.english), JSON.stringify(cards));
});

test('AM-21 a plural / notes column is named when the header says so; rows without a word or without a second side are dropped', () => {
  const rows = SI.parseText('Arabizi;Arabic;English;Plural;Notes\nJumle;جملة;sentence;jumal;grammar word\n;;only english;;\nKalb;كلب;;klaab;');
  const cols = SI.detectColumns(rows);
  assert.deepEqual([cols.arabizi, cols.arabic, cols.english, cols.plural, cols.notes], [0, 1, 2, 3, 4]);
  const cards = SI.toCards(rows, cols);
  assert.equal(cards.length, 2);                                   // "only english" has no word; Kalb has Arabic + Arabizi (two sides) and stays
  assert.equal(cards[0].plural, 'jumal'); assert.equal(cards[0].notes, 'grammar word');
});

test('AM-21 the module never holds a Google address a rule check could read as sending Amal off-site (AM-13)', () => {
  const src = require('fs').readFileSync(require.resolve('../docs/js/sheet-import.js'), 'utf8');
  assert.ok(!/docs\.google\.com/.test(src));
  for (const f of ['../docs/js/hub/upload-task.js', '../docs/js/hub/homework-task.js']) assert.ok(!/docs\.google\.com\//.test(require('fs').readFileSync(require.resolve(f), 'utf8')), f);
});
