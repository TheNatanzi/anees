'use strict';

// Real template import-validation functions, synthetic in-memory evidence.
// This test never reads browser storage, human review files, or lesson audio.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const templatePath = process.argv[2]
  ? path.resolve(process.argv[2]) : path.join(__dirname, 'review_template.html');
const template = fs.readFileSync(templatePath, 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));
function section(startText, endText) {
  const start = template.indexOf(startText);
  const end = template.indexOf(endText, start);
  assert(start >= 0 && end > start, `Cannot extract ${startText}`);
  return template.slice(start, end);
}
function actualConstant(name) {
  const declaration = template.match(new RegExp(`const ${name}\\s*=\\s*([^;]+);`));
  assert(declaration, `Missing actual ${name} declaration.`);
  return vm.runInNewContext(declaration[1], {}, { timeout: 1000 });
}
const run = {
  id: 'r1', speaker: 'Medi', start: 100, end: 102,
  text: 'Um, b- ba7ki.', events: [],
};
const windowData = {
  id: 'w1', start: 100, end: 105,
  candidates: [
    { id: 'A', source_kind: 'separate_tracks', runs: [run] },
    { id: 'B', source_kind: 'mixed_recording', runs: [] },
  ],
};
const data = {
  schema_version: '1.0', lesson: 'test-lesson',
  review_set_id: 'test-review-set', manifest_sha256: 'test-manifest',
  windows: [windowData],
};
const context = {
  DATA: data,
  isRelevant: () => true,
  iso: () => '2026-09-07T12:00:00.000Z',
};
for (const name of ['METRIC_CHOICES', 'VERDICTS', 'CERTAINTIES',
  'METRIC_KEYS', 'VALID_PREFS', 'ROLES']) context[name] = actualConstant(name);
vm.createContext(context);
const functions = [
  section('function emptyMetrics(', '\nfunction windowRecord('),
  section('function assert(', '\nfunction importFile('),
].join('\n');
new vm.Script(functions, { filename: templatePath + ':review-validation' })
  .runInContext(context, { timeout: 1000 });

function record(overrides = {}) {
  return {
    id: run.id, speaker: run.speaker, start: run.start, end: run.end,
    original_text: run.text, verdict: null, fixed_text: null,
    text_certainty: null, deliberate_error: null,
    active_seconds: 3, updated_at: '2026-09-07T11:00:00.000Z', ...overrides,
  };
}
function windowRecord(runRecord) {
  return {
    id: 'w1', status: 'pending', active_seconds: 10, playback_count: 1,
    candidate_preference: 'A', source_names_revealed_at: null, notes: '',
    candidates: {
      A: { metrics: clone(context.emptyMetrics()), runs: { r1: runRecord }, missing_speech: [] },
      B: { metrics: clone(context.emptyMetrics()), runs: {}, missing_speech: [] },
    },
  };
}
function payload(runRecord) {
  return {
    schema_version: '1.0', kind: 'anees-human-review', lesson: data.lesson,
    review_set_id: data.review_set_id, manifest_sha256: data.manifest_sha256,
    exported_at: '2026-09-07T11:00:00.000Z',
    reviewers: {
      Medi: {
        reviewer: 'Medi', updated_at: '2026-09-07T11:00:00.000Z',
        active_seconds: 10, windows: { w1: windowRecord(runRecord) },
      },
    },
  };
}
function importedRun(input) {
  return context.validateImport(input).Medi.windows.w1.candidates.A.runs.r1;
}
const tests = [];
const test = (name, body) => tests.push({ name, body });

test('cant_tell import is accepted, preserves draft and uncertainty, and does not mutate input', () => {
  const input = payload(record({
    verdict: 'cant_tell', fixed_text: 'Possible old draft', text_certainty: 'unclear',
  }));
  const before = JSON.stringify(input);
  const imported = importedRun(input);
  assert.equal(imported.verdict, 'cant_tell');
  assert.equal(imported.fixed_text, 'Possible old draft');
  assert.equal(imported.text_certainty, 'unclear');
  assert.equal(JSON.stringify(input), before);
});

for (const [name, overrides] of [
  ['unjudged', {}],
  ['legacy Exact unconfirmed', { verdict: 'exact', fixed_text: run.text, text_certainty: null }],
  ['legacy edited Minor unconfirmed', { verdict: 'minor', fixed_text: 'Previously edited words', text_certainty: null }],
  ['legacy Wrong unclear', { verdict: 'wrong', fixed_text: '[unclear]', text_certainty: 'unclear' }],
]) {
  test(`Import preserves ${name} without promotion`, () => {
    const rr = record(overrides);
    const input = payload(rr);
    const before = JSON.stringify(input);
    const imported = importedRun(input);
    assert.equal(imported.verdict, rr.verdict);
    assert.equal(imported.fixed_text, rr.fixed_text);
    assert.equal(imported.text_certainty, rr.text_certainty);
    assert.equal(JSON.stringify(input), before);
  });
}

test('Unknown verdict remains invalid', () => {
  assert.throws(() => importedRun(payload(record({ verdict: 'auto_approved' }))), /verdict/i);
});
test('Contradictory cant_tell plus confirmed cannot enter through import', () => {
  assert.throws(() => importedRun(payload(record({
    verdict: 'cant_tell', fixed_text: 'Old draft', text_certainty: 'confirmed',
  }))), /unclear|confirmed|certainty|cant_tell|tell/i);
});
test('Mismatched manifest remains invalid', () => {
  const input = payload(record()); input.manifest_sha256 = 'another-manifest';
  assert.throws(() => importedRun(input), /manifest/i);
});
test('Changed raw evidence remains invalid', () => {
  const input = payload(record({ original_text: 'Changed raw words' }));
  assert.throws(() => importedRun(input), /evidence/i);
});

for (const preference of [null, 'A', 'B', 'tie', 'neither', 'uncertain']) {
  test(`Historical candidate preference ${preference} survives import without derived replacement`, () => {
    const input = payload(record());
    input.reviewers.Medi.windows.w1.candidate_preference = preference;
    const imported = context.validateImport(input);
    assert.equal(imported.Medi.windows.w1.candidate_preference, preference);
  });
}
test('Existing optional notes, advanced metrics, and historical status remain intact', () => {
  const input = payload(record());
  const wr = input.reviewers.Medi.windows.w1;
  wr.notes = 'My earlier note — retain exactly.';
  wr.status = 'reviewed';
  wr.reviewed_at = '2026-09-07T10:59:00.000Z';
  wr.candidates.A.metrics.speaker_correct = 'uncertain';
  wr.candidates.A.metrics.unsupported_insertions = 2;
  const before = JSON.stringify(input);
  const output = context.validateImport(input).Medi.windows.w1;
  assert.equal(output.notes, wr.notes);
  assert.equal(output.status, wr.status);
  assert.equal(output.reviewed_at, wr.reviewed_at);
  assert.equal(output.candidates.A.metrics.speaker_correct, 'uncertain');
  assert.equal(output.candidates.A.metrics.unsupported_insertions, 2);
  assert.equal(JSON.stringify(input), before);
});
test('Partial review and unfinished missing-speech draft can be saved and reimported', () => {
  const input = payload(record({ verdict: 'minor', fixed_text: run.text, text_certainty: null }));
  input.reviewers.Medi.windows.w1.candidate_preference = null;
  input.reviewers.Medi.windows.w1.candidates.A.missing_speech.push({
    id: 'draft-1', speaker: 'Unknown', start: 102, end: 103,
    text: '', text_certainty: null,
  });
  const output = context.validateImport(input).Medi.windows.w1;
  assert.equal(output.candidate_preference, null);
  assert.equal(output.candidates.A.runs.r1.text_certainty, null);
  assert.equal(output.candidates.A.missing_speech[0].text, '');
  assert.equal(output.candidates.A.missing_speech[0].text_certainty, null);
});

let failures = 0;
for (const { name, body } of tests) {
  try { body(); console.log(`PASS ${name}`); }
  catch (error) { failures++; console.error(`FAIL ${name}\n  ${error.message}`); }
}
console.log(`${tests.length - failures}/${tests.length} import-preservation regression tests passed.`);
process.exitCode = failures ? 1 : 0;
