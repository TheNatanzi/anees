// Rule AM-25 (Medi 2026-10-06 "...create an index for yourself to use as a secondary data source..." / "ingest"):
// docs/js/reference-lexicon.js is a pure lookup over the secondary reference lexicon - glosses, roots, plurals,
// examples, verb-preposition hints. It is never a spelling (RULES.md S1) and never a score. Tiny fixture, no DOM.
const test = require('node:test'), assert = require('node:assert/strict');
const R = require('../docs/js/reference-lexicon.js');
const NORM = require('./fixtures/reference-lexicon-norm.json');

const FIXTURE = {
  built: '2026-10-06',
  licenses: { 'kaikki-ajp': 'CC BY-SA 3.0', maknuune: 'CC BY-SA 4.0' },
  sources: { 'kaikki-ajp': 2, maknuune: 5 },
  records: {
    'كتب': { arabic: 'كَتَب', pos: 'verb', gloss: ['to write', 'write'], root: 'ك.ت.ب', plural: '',
             forms: { past: 'كَتَب', present: 'بكتب' }, examples: [{ ar: 'كتبت لأهلي.', en: 'I wrote to my parents.' }],
             preps: ['ل'], sources: [{ src: 'kaikki-ajp', license: 'CC BY-SA 3.0' }, { src: 'maknuune', license: 'CC BY-SA 4.0' }] },
    'بيت': { arabic: 'بيت', pos: 'noun', gloss: ['house, home'], root: 'ب.ي.ت', plural: 'بيوت', forms: {}, examples: [], preps: [],
             sources: [{ src: 'kaikki-ajp', license: 'CC BY-SA 3.0' }] },
    'خاف': { arabic: 'خاف', pos: 'verb', gloss: ['to be afraid'], root: 'خ.و.ف', plural: '', forms: { past: 'خاف', present: 'بخاف' },
             examples: [], preps: ['من'], sources: [{ src: 'maknuune', license: 'CC BY-SA 4.0' }] }
  },
  index: { 'بيوت': 'بيت', 'بكتب': 'كتب', 'بخاف': 'خاف', 'كتبت': 'كتب', 'ghost': 'nowhere' }
};

test('AM-25 normalisation agrees with the builder on the shared fixture', () => {
  for (const [input, want] of NORM.pairs) assert.equal(R.normalise(input), want, JSON.stringify(input));
  assert.equal(R.normalise(null), '');
  assert.equal(R.normalise(undefined), '');
});

test('AM-25 load() reports the sources and licenses; find() reads records and the form index', () => {
  const meta = R.load(FIXTURE);
  assert.equal(meta.record_count, 3);
  assert.equal(meta.licenses.maknuune, 'CC BY-SA 4.0');
  assert.equal(R.size(), 3);
  const exact = R.find('كَتَبَ');
  assert.equal(exact.key, 'كتب'); assert.equal(exact.how, 'exact'); assert.equal(exact.record.root, 'ك.ت.ب');
  const viaForm = R.find('بيوت');
  assert.equal(viaForm.key, 'بيت'); assert.equal(viaForm.how, 'form'); assert.equal(viaForm.record.plural, 'بيوت');
  assert.equal(R.find('كتبت').key, 'كتب');                       // a conjugated form listed in the index
  assert.equal(R.find('ghost'), null);                             // an index row pointing nowhere is not a hit
  assert.equal(R.find('مش موجود'), null);
  assert.equal(R.find(''), null);
});

test('AM-25 a leading pronoun or ال is not part of the lemma', () => {
  R.load(FIXTURE);
  const p = R.find('أنا بخاف');
  assert.equal(p.key, 'خاف'); assert.equal(p.how, 'pronoun');
  const al = R.find('البيت');
  assert.equal(al.key, 'بيت'); assert.equal(al.how, 'al');
  assert.equal(R.find('هم كتبوا'), null);                          // no guessing beyond the listed forms
  assert.equal(R.stripPronoun('انا'), 'انا');                      // a pronoun alone stays
});

test('AM-25 glossFor() gives a copy of the glosses, or nothing - never a spelling or a score', () => {
  R.load(FIXTURE);
  const g = R.glossFor('كتب');
  assert.deepEqual(g, ['to write', 'write']);
  g.push('mutated');
  assert.deepEqual(R.glossFor('كتب'), ['to write', 'write']);
  assert.deepEqual(R.glossFor('مش موجود'), []);
  const rec = R.find('كتب').record;
  for (const k of ['arabizi', 'house_spelling', 'score', 'grade']) assert.equal(k in rec, false, k);
});

test('AM-25 load() with nothing or junk leaves an empty, working lexicon', () => {
  assert.equal(R.load(null).record_count, 0);
  assert.equal(R.find('كتب'), null);
  assert.equal(R.load({ records: 'junk', index: 5 }).record_count, 0);
  assert.deepEqual(R.glossFor('كتب'), []);
});

test('AM-25 the published reference-lexicon.json (when built) loads and has the promised shape', () => {
  const fs = require('fs'), path = require('path');
  const p = path.join(__dirname, '..', 'docs', 'data', 'reference-lexicon.json');
  if (!fs.existsSync(p)) return;                                    // the raw dumps are not in git; the hourly job builds it
  const d = JSON.parse(fs.readFileSync(p, 'utf8'));
  const meta = R.load(d);
  assert.ok(meta.record_count > 1000, 'record_count ' + meta.record_count);
  assert.ok(fs.statSync(p).size <= 6.5e6, 'size ' + fs.statSync(p).size);
  for (const rec of Object.values(d.records).slice(0, 200)) {
    for (const k of ['arabic', 'pos', 'gloss', 'root', 'plural', 'forms', 'examples', 'preps', 'sources']) assert.ok(k in rec, k);
    assert.ok(rec.examples.length <= 3);
    for (const s of rec.sources) assert.ok(/^CC BY-SA/.test(s.license), s.license);
  }
});
