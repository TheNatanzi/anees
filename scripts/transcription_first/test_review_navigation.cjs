'use strict';

// Render/navigation checks using the actual template functions and an in-memory
// DOM. No browser, audio, network, localStorage, or user review files are used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const templatePath = process.argv[2]
  ? path.resolve(process.argv[2]) : path.join(__dirname, 'review_template.html');
const template = fs.readFileSync(templatePath, 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));
function sourceFunction(name) {
  const start = template.indexOf(`function ${name}(`);
  assert(start >= 0, `Missing actual ${name} function.`);
  const next = template.indexOf('\nfunction ', start + 1);
  assert(next > start, `Missing function boundary after ${name}.`);
  return template.slice(start, next);
}
function actualConstant(name) {
  const match = template.match(new RegExp(`const ${name}\\s*=\\s*([^;]+);`));
  assert(match, `Missing ${name} constant.`);
  return vm.runInNewContext(match[1], {}, { timeout: 1000 });
}

class Element {
  constructor(tag, text, className = '') {
    this.tagName = tag.toUpperCase();
    this.textContent = text == null ? '' : String(text);
    this.className = className;
    this.children = [];
    this.attributes = Object.create(null);
    this.listeners = Object.create(null);
    this.dataset = Object.create(null);
    this.style = Object.create(null);
    this.parentNode = null;
    this.value = '';
    this.open = false;
    this.classList = { add() {}, remove() {} };
  }
  append(...children) {
    for (const child of children) {
      this.children.push(child);
      if (child instanceof Element) child.parentNode = this;
    }
  }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  addEventListener(event, callback) { (this.listeners[event] ||= []).push(callback); }
  fire(event) { for (const callback of this.listeners[event] || []) callback({ target: this }); }
  pause() {}
  scrollIntoView() {}
}
function descendants(root, predicate) {
  const result = [];
  function visit(element) {
    if (!(element instanceof Element)) return;
    if (predicate(element)) result.push(element);
    element.children.forEach(visit);
  }
  visit(root); return result;
}
function closedDetailsAncestor(element) {
  for (let current = element.parentNode; current; current = current.parentNode) {
    if (current.tagName === 'DETAILS' && !current.open) return current;
  }
  return null;
}

function fixture() {
  const windows = [0, 1].map(i => ({
    id: `w${i + 1}`, start: 100 + i * 25, end: 125 + i * 25,
    category: 'test', selection_reason: 'Synthetic fixture only',
    audio: { mixed: 'data:audio/wav;base64,fixture', Medi: 'data:audio/wav;base64,fixture', Amal: 'data:audio/wav;base64,fixture' },
    candidates: ['A', 'B'].map((id, c) => ({
      id, source_kind: c === 0 ? 'separate_tracks' : 'mixed_recording',
      runs: [{ id: `${id}-${i + 1}`, speaker: c === 0 ? 'Medi' : 'Unknown',
        start: 100 + i * 25, end: 102 + i * 25, text: 'Um, b- ba7ki.', events: [] }],
    })),
  }));
  const reviewerRecord = { reviewer: 'Medi', active_seconds: 0, windows: {} };
  for (const w of windows) {
    const wr = {
      id: w.id, status: 'pending', active_seconds: 0, playback_count: 0,
      candidate_preference: null, source_names_revealed_at: null,
      notes: '', candidates: {},
    };
    for (const c of w.candidates) {
      const r = c.runs[0];
      wr.candidates[c.id] = {
        metrics: { learner_attempt_preserved: null, speaker_correct: null,
          timestamp_within_1s: null, recall_utterance_preserved: null,
          unsupported_insertions: null },
        runs: { [r.id]: { id: r.id, speaker: r.speaker, start: r.start, end: r.end,
          original_text: r.text, verdict: null, fixed_text: null,
          text_certainty: null, deliberate_error: null, active_seconds: 0, updated_at: null } },
        missing_speech: [],
      };
    }
    reviewerRecord.windows[w.id] = wr;
  }
  return { windows, reviewerRecord };
}

const helperPath = path.join(__dirname, 'review_comparison.js');
function comparisonHelper() {
  assert(fs.existsSync(helperPath), 'Automatic assessment helper is not ready yet.');
  return require(helperPath);
}

function harness() {
  const { windows, reviewerRecord } = fixture();
  const ids = Object.create(null);
  const node = (tag, text, cls) => new Element(tag, text, cls);
  for (const id of ['window-area', 'previous', 'next', 'window-picker']) ids[id] = node('div');
  ids['window-picker'].options = windows.map(() => node('option'));
  const counters = { saves: 0, exports: 0, changes: 0, notifications: [], playback: [] };
  const context = {
    DATA: { windows }, index: 0, reviewer: 'Medi', reviewers: { Medi: reviewerRecord },
    activeRun: null, focusOnly: true, revealed: false, player: null, stopAt: null,
    lastInteraction: 0,
    window: { scrollY: 0, scrollTo() {}, confirm: () => true },
    node,
    $: id => ids[id] ||= node('div'),
    button(text, handler, cls) {
      const b = node('button', text, cls); b.addEventListener('click', handler); return b;
    },
    select(choices, value, handler, label) {
      const s = node('select'); s.value = value || ''; s.setAttribute('aria-label', label);
      s.addEventListener('change', () => handler(s.value || null)); return s;
    },
    windowRecord: () => reviewerRecord.windows[windows[context.index].id],
    renderRun: (w, c, r) => node('section', r.text, 'fixture-run'),
    renderMissing() {},
    isRelevant: () => true,
    pauseAudio() {},
    playAudio(w, track, start = w.start, end = w.end) {
      counters.playback.push({ windowId: w.id, track, start, end });
    },
    timeRange: (start, end) => `${start}-${end}`,
    duration: seconds => `${seconds}s`,
    iso: () => '2026-09-07T12:00:00.000Z',
    save() { counters.saves++; },
    markChanged() { counters.changes++; },
    updateProgress() {},
    notify(text) { counters.notifications.push(text); },
    exportReview() { counters.exports++; },
    copy: clone,
    AneesComparison: comparisonHelper(),
  };
  for (const name of ['METRIC_CHOICES', 'METRIC_KEYS']) context[name] = actualConstant(name);
  vm.createContext(context);
  const source = ['completionIssues', 'updateProgress', 'renderCandidate', 'renderWindow', 'move', 'makeExport'].map(sourceFunction).join('\n');
  new vm.Script(source, { filename: templatePath + ':navigation' })
    .runInContext(context, { timeout: 1000 });
  context.renderWindow();
  return {
    context, windows, reviewerRecord, counters,
    get tree() { return ids['window-area']; },
    render() { context.renderWindow(); },
    find(predicate) { return descendants(ids['window-area'], predicate); },
    click(pattern) {
      const choices = this.find(e => e.tagName === 'BUTTON' && pattern.test(e.textContent));
      assert.equal(choices.length, 1, `Expected one ${pattern} button.`);
      choices[0].fire('click');
    },
  };
}

const tests = [];
const test = (name, body) => tests.push({ name, body });
test('Manual preference and finish panel are absent from the rendered footer', () => {
  const h = harness();
  assert.equal(h.find(e => e.attributes['aria-label'] === 'Window candidate preference').length, 0);
  assert.equal(h.find(e => /Your judgment for this window|Mark this window reviewed|Mark as still pending/.test(e.textContent)).length, 0);
  assert.equal(h.find(e => e.tagName === 'BUTTON' && /Next clip/i.test(e.textContent)).length, 1);
});
test('Next clip accepts wholly unjudged answers and does not approve or vote', () => {
  const h = harness();
  const before = JSON.stringify(h.reviewerRecord);
  h.click(/Next clip/i);
  assert.equal(h.context.index, 1);
  assert.equal(JSON.stringify(h.reviewerRecord), before);
  assert.equal(h.counters.notifications.length, 0);
  assert(h.counters.saves >= 1);
});
test('Next clip accepts partial correction and unfinished missing speech', () => {
  const h = harness();
  const wr = h.reviewerRecord.windows.w1;
  wr.candidates.A.runs['A-1'].verdict = 'minor';
  wr.candidates.A.runs['A-1'].fixed_text = 'Unfinished draft';
  wr.candidates.A.missing_speech.push({ id: 'draft', speaker: 'Unknown', start: 102, end: 103, text: '', text_certainty: null });
  const before = JSON.stringify(h.reviewerRecord);
  h.click(/Next clip/i);
  assert.equal(h.context.index, 1);
  assert.equal(JSON.stringify(h.reviewerRecord), before);
  assert.equal(h.counters.notifications.length, 0);
});
test('Last clip offers download without requiring ratings or a winner', () => {
  const h = harness();
  h.context.index = h.windows.length - 1; h.render();
  const before = JSON.stringify(h.reviewerRecord);
  assert.equal(h.find(e => e.tagName === 'BUTTON' && /Next clip/i.test(e.textContent)).length, 0);
  h.click(/Download review JSON/i);
  assert.equal(h.counters.exports, 1);
  assert.equal(JSON.stringify(h.reviewerRecord), before);
});
test('Notes are optional and collapsed, retain old text, and persist explicit edits', () => {
  const h = harness();
  h.reviewerRecord.windows.w1.notes = 'Old note stays.'; h.render();
  const areas = h.find(e => e.tagName === 'TEXTAREA');
  assert.equal(areas.length, 1, 'Run editors are stubbed; only optional notes should remain.');
  assert(closedDetailsAncestor(areas[0]), 'Notes must be inside collapsed details.');
  assert.equal(areas[0].value, 'Old note stays.');
  areas[0].value = 'Amended optional note.'; areas[0].fire('input');
  assert.equal(h.reviewerRecord.windows.w1.notes, 'Amended optional note.');
  h.click(/Next clip/i); h.context.move(0);
  assert.equal(h.find(e => e.tagName === 'TEXTAREA')[0].value, 'Amended optional note.');
});
test('Advanced whole-window checks are all behind collapsed details', () => {
  const h = harness();
  const advanced = h.find(e => e.tagName === 'FIELDSET');
  assert.equal(advanced.length, 2);
  for (const fieldset of advanced) assert(closedDetailsAncestor(fieldset), 'Advanced checks must not be default questions.');
});
test('One shared play button uses the same mixed clip bounds for both candidates', () => {
  const h = harness();
  const buttons = h.find(e => e.tagName === 'BUTTON' && /Play shared clip/i.test(e.textContent));
  assert.equal(buttons.length, 1);
  assert.equal(closedDetailsAncestor(buttons[0]), null, 'Shared playback should be the main visible action.');
  buttons[0].fire('click'); buttons[0].fire('click');
  const expected = { windowId: 'w1', track: 'mixed', start: 100, end: 125 };
  assert.deepEqual(h.counters.playback, [expected, expected]);
});
test('Solo-speaker playback remains optional behind collapsed details', () => {
  const h = harness();
  const solo = h.find(e => e.tagName === 'BUTTON' && /Medi|Amal/.test(e.textContent));
  assert.equal(solo.length, 2);
  for (const button of solo) assert(closedDetailsAncestor(button), 'Solo tracks should not compete with shared playback by default.');
});
test('Rendering and navigating retain historical preference, status, and metrics', () => {
  const h = harness();
  const wr = h.reviewerRecord.windows.w1;
  wr.candidate_preference = 'B'; wr.status = 'reviewed';
  wr.candidates.A.metrics.speaker_correct = 'uncertain';
  const before = JSON.stringify(h.reviewerRecord);
  h.render(); h.click(/Next clip/i); h.context.move(0);
  assert.equal(JSON.stringify(h.reviewerRecord), before);
});
test('Read-only progress counts answered clips without requiring a manual preference', () => {
  const h = harness();
  const wr = h.reviewerRecord.windows.w1;
  for (const candidate of Object.values(wr.candidates)) {
    for (const record of Object.values(candidate.runs)) {
      record.verdict = 'exact'; record.fixed_text = record.original_text;
      record.text_certainty = 'confirmed';
    }
  }
  assert.equal(wr.candidate_preference, null);
  const before = JSON.stringify(h.reviewerRecord);
  h.context.updateProgress();
  assert.match(h.context.$('progress-copy').textContent, /1\/2 clips answered/);
  assert.equal(JSON.stringify(h.reviewerRecord), before,
    'Progress must not mark a window reviewed or create a vote.');
});
test('Automatic assessment functions are read-only, including historical manual votes', () => {
  const { windows, reviewerRecord } = fixture();
  reviewerRecord.windows.w1.candidate_preference = 'B';
  for (const wr of Object.values(reviewerRecord.windows)) {
    for (const candidate of Object.values(wr.candidates)) {
      for (const record of Object.values(candidate.runs)) {
        record.verdict = 'exact';
        record.fixed_text = record.original_text;
        record.text_certainty = 'confirmed';
      }
    }
  }
  const inputs = { windows, reviewerRecord };
  const before = JSON.stringify(inputs);
  const comparison = comparisonHelper();
  const paired = comparison.compareWindow(windows[0], reviewerRecord.windows.w1);
  const overall = comparison.summarize(windows, reviewerRecord);
  assert(paired && overall, 'Assessment returns derived information.');
  assert.equal(paired.state, 'ready', 'Completed synthetic ratings should be comparable.');
  assert.equal(paired.winner, 'tie', 'Identical exact transcripts tie regardless of the historical B vote.');
  assert.equal(JSON.stringify(inputs), before, 'Derived results cannot change answers, certainty, or manual preferences.');
});
test('Export attaches derived assessment without mutating or overwriting historical answers', () => {
  const h = harness();
  h.reviewerRecord.windows.w1.candidate_preference = 'B';
  const before = JSON.stringify(h.reviewerRecord);
  const output = h.context.makeExport();
  assert(output.automatic_comparison.Medi, 'Export should include the automatically computed summary.');
  assert.equal(output.reviewers.Medi.windows.w1.candidate_preference, 'B');
  assert.equal(JSON.stringify(h.reviewerRecord), before);
  assert.notEqual(output.reviewers.Medi, h.reviewerRecord, 'Exported answers must be a separate copy.');
});
test('Assessment failure never blocks exporting the unchanged human answers', () => {
  const h = harness();
  h.reviewerRecord.windows.w1.notes = 'Keep this note even if assessment fails.';
  h.reviewerRecord.windows.w1.candidate_preference = 'B';
  const before = JSON.stringify(h.reviewerRecord);
  h.context.AneesComparison = { summarize() { throw new Error('Synthetic comparison failure'); } };
  const output = h.context.makeExport();
  assert.equal(JSON.stringify(output.reviewers.Medi), before);
  assert.equal(JSON.stringify(h.reviewerRecord), before);
  assert.match(JSON.stringify(output.automatic_comparison.Medi), /comparison_unavailable/);
});

let failures = 0;
for (const { name, body } of tests) {
  try { body(); console.log(`PASS ${name}`); }
  catch (error) { failures++; console.error(`FAIL ${name}\n  ${error.stack || error.message}`); }
}
console.log(`${tests.length - failures}/${tests.length} navigation/assessment regression tests passed.`);
process.exitCode = failures ? 1 : 0;
