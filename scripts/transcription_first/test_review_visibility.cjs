'use strict';

// Pure renderRun regression test. It executes only that function from the actual
// template in a VM and uses an in-memory DOM substitute. No browser, network,
// localStorage, saved reviews, lesson recordings, or repository state is touched.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const templatePath = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(__dirname, 'review_template.html');
const template = fs.readFileSync(templatePath, 'utf8');
const functionStart = template.indexOf('function renderRun(');
const functionEnd = template.indexOf('\nfunction renderMissing(', functionStart);
assert(functionStart >= 0 && functionEnd > functionStart,
  'Cannot locate renderRun and its following function boundary in the template.');
const helperStart = template.indexOf('function correctionCertainty(');
assert(helperStart >= 0 && helperStart < functionStart,
  'Cannot locate actual correctionCertainty helper.');
const functionSource = template.slice(helperStart, functionEnd);
const verdictDeclaration = template.match(/const VERDICTS\s*=\s*([^;]+);/);
assert(verdictDeclaration, 'Cannot locate actual VERDICTS declaration.');
const actualVerdicts = vm.runInNewContext(verdictDeclaration[1], {}, { timeout: 1000 });

class FakeElement {
  constructor(tag, text = null, className = '') {
    this.tagName = tag.toUpperCase();
    this.textContent = text == null ? '' : String(text);
    this.className = className;
    this.children = [];
    this.attributes = Object.create(null);
    this.listeners = Object.create(null);
    this.dataset = Object.create(null);
    this.value = '';
  }
  append(...children) { this.children.push(...children); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, listener) {
    (this.listeners[name] ||= []).push(listener);
  }
  fire(name) {
    for (const listener of this.listeners[name] || []) {
      listener({ target: this, currentTarget: this });
    }
  }
}

function descendants(root, predicate) {
  const found = [];
  function visit(element) {
    if (!(element instanceof FakeElement)) return;
    if (predicate(element)) found.push(element);
    element.children.forEach(visit);
  }
  visit(root);
  return found;
}

function harness(verdict = null, role = 'Medi') {
  const run = {
    id: 'fixture-run', speaker: 'Medi', start: 100, end: 102,
    text: 'Um, b- ba7ki.', events: [],
  };
  const candidate = { id: 'A', source_kind: 'separate_tracks', runs: [run] };
  const windowData = { id: 'fixture-window', start: 100, end: 105, audio: {} };
  const record = {
    id: run.id, speaker: run.speaker, start: run.start, end: run.end,
    original_text: run.text, verdict,
    fixed_text: verdict ? run.text : null,
    text_certainty: null, deliberate_error: null,
    active_seconds: 0, updated_at: null,
  };
  const node = (tag, text, className) => new FakeElement(tag, text, className);
  let tree;
  let renders = 0;
  let changes = 0;
  let confirmationAllowed = true;
  const context = {
    VERDICTS: actualVerdicts,
    reviewer: role,
    runRecord: () => record,
    node,
    button(text, handler, className) {
      const element = node('button', text, className);
      element.addEventListener('click', handler);
      return element;
    },
    select(choices, value, handler, label) {
      const element = node('select');
      element.value = value || '';
      element.setAttribute('aria-label', label);
      element.addEventListener('change', () => handler(element.value || null));
      return element;
    },
    editLabel(labelText, control) {
      const label = node('label', labelText);
      label.append(control);
      return label;
    },
    trackLabel: () => 'Medi source track',
    timeRange: (start, end) => `${start}-${end}`,
    isTrack: () => true,
    playAudio() {},
    touchRun() {},
    iso: () => '2026-09-07T12:00:00.000Z',
    markChanged() { changes++; },
    renderWindow() { renders++; tree = context.renderRun(windowData, candidate, run); },
    window: { confirm: () => confirmationAllowed },
  };
  vm.createContext(context);
  new vm.Script(functionSource, { filename: templatePath + ':renderRun' })
    .runInContext(context, { timeout: 1000 });
  tree = context.renderRun(windowData, candidate, run);
  return {
    record, run,
    get tree() { return tree; },
    get renderCount() { return renders; },
    get changeCount() { return changes; },
    set confirmationAllowed(value) { confirmationAllowed = value; },
    render() { tree = context.renderRun(windowData, candidate, run); },
    find(predicate) { return descendants(tree, predicate); },
    correctionBoxes() {
      return this.find(e => e.tagName === 'TEXTAREA' &&
        (e.attributes['aria-label'] || '').startsWith('Verbatim correction'));
    },
    correctionLabels() {
      return this.find(e => e.tagName === 'LABEL' &&
        e.textContent.startsWith('What you actually hear'));
    },
    control(label) {
      const found = this.find(e => e.attributes['aria-label'] === label);
      assert.equal(found.length, 1, `Expected exactly one control: ${label}`);
      return found[0];
    },
    click(text) {
      const normalized = text.replace(/[’‘]/g, "'");
      const found = this.find(e => e.tagName === 'BUTTON' &&
        e.textContent.replace(/[’‘]/g, "'") === normalized);
      assert.equal(found.length, 1, `Expected exactly one button: ${text}`);
      found[0].fire('click');
    },
  };
}

const tests = [];
const test = (name, body) => tests.push({ name, body });

test('Actual template declares four verdicts including cant_tell', () => {
  assert.deepEqual(Array.from(actualVerdicts), ['exact', 'minor', 'wrong', 'cant_tell']);
});
test('Per-run timestamps remain visible without separate model-timed play buttons', () => {
  const h = harness();
  assert.equal(h.find(e => e.tagName === 'BUTTON' && e.textContent.startsWith('▶')).length, 0);
  assert.equal(h.find(e => e.textContent === '100-102').length, 1);
});

for (const role of ['Medi', 'Amal']) {
  for (const verdict of [null, 'exact', 'minor', 'wrong', 'cant_tell']) {
    test(`${role}: ${verdict || 'unjudged'} correction visibility and judgment controls`, () => {
      const h = harness(verdict, role);
      const expectedBoxes = verdict === 'minor' || verdict === 'wrong' ? 1 : 0;
      assert.equal(h.correctionBoxes().length, expectedBoxes);
      assert.equal(h.correctionLabels().length, expectedBoxes);
      assert.equal(h.find(e => e.attributes['aria-label'] === 'Wording certainty').length,
        0, 'The redundant per-run certainty dropdown must be removed.');
      assert.equal(h.find(e => e.tagName === 'BUTTON' &&
        e.textContent === 'Clear this run’s judgment').length,
        verdict ? 1 : 0, 'Clear remains available for Exact.');
      assert.equal(h.record.verdict, verdict, 'Rendering must not preapprove a verdict.');
      assert.equal(h.record.text_certainty, null, 'Rendering must not confirm wording.');
      assert.equal(h.find(e => e.tagName === 'BUTTON' &&
        e.textContent.replace(/[’‘]/g, "'") === "Can't tell").length, 1);
    });
  }
}

test('Unjudged → Minor opens correction; input is stored verbatim', () => {
  const h = harness();
  h.click('Minor');
  assert.equal(h.record.verdict, 'minor');
  assert.equal(h.record.text_certainty, null,
    'Choosing Minor alone must not confirm the prefilled raw text.');
  assert.equal(h.correctionBoxes().length, 1);
  const area = h.correctionBoxes()[0];
  area.value = 'Um, b- b- ba7ki.';
  area.fire('input');
  assert.equal(h.record.fixed_text, area.value);
  assert.equal(h.record.text_certainty, 'confirmed');
  assert(h.renderCount >= 1);
  assert(h.changeCount >= 2);
});

test('Edited Minor → Exact hides box and cannot retain an invisible correction', () => {
  const h = harness('minor');
  const area = h.correctionBoxes()[0];
  area.value = 'Um, b- b- ba7ki.';
  area.fire('input');
  assert.equal(h.record.text_certainty, 'confirmed');
  h.click('Exact');
  assert.equal(h.record.verdict, 'exact');
  assert.equal(h.correctionBoxes().length, 0);
  assert.equal(h.record.fixed_text, h.run.text,
    'Exact must refer to the raw wording, not a hidden previous correction.');
  assert.equal(h.record.text_certainty, 'confirmed',
    'An explicitly accepted Exact action now confirms the raw words.');
});

test('Exact → Wrong opens correction and Clear restores unjudged state', () => {
  const h = harness('exact');
  h.click('Exact');
  assert.equal(h.record.text_certainty, 'confirmed');
  h.click('Wrong');
  assert.equal(h.record.text_certainty, null,
    'Wrong must not retain confirmation of the unchanged raw text.');
  assert.equal(h.correctionBoxes().length, 1);
  assert.equal(h.correctionBoxes()[0].value, h.run.text);
  h.click('Clear this run’s judgment');
  assert.equal(h.record.verdict, null);
  assert.equal(h.record.fixed_text, null);
  assert.equal(h.record.text_certainty, null);
  assert.equal(h.correctionBoxes().length, 0);
});

test('Canceling edited Wrong → Exact preserves the correction and visible editor', () => {
  const h = harness('wrong');
  const area = h.correctionBoxes()[0];
  area.value = 'Um, b- b- ba7ki.';
  area.fire('input');
  const before = JSON.stringify(h.record);
  h.confirmationAllowed = false;
  h.click('Exact');
  assert.equal(JSON.stringify(h.record), before,
    'Cancel must preserve the entire judgment and correction record.');
  assert.equal(h.correctionBoxes().length, 1);
  assert.equal(h.correctionBoxes()[0].value, area.value);
});

test('Explicit Exact confirms raw wording without a correction box', () => {
  const h = harness();
  h.click('Exact');
  assert.equal(h.record.fixed_text, h.run.text);
  assert.equal(h.record.text_certainty, 'confirmed');
  assert.equal(h.correctionBoxes().length, 0);
});

test('Can’t tell is explicit uncertainty, hides correction box, and retains draft', () => {
  const h = harness('minor');
  const area = h.correctionBoxes()[0];
  area.value = 'Um, b- b- ba7ki.';
  area.fire('input');
  const draft = area.value;
  h.click('Can’t tell');
  assert.equal(h.record.verdict, 'cant_tell');
  assert.equal(h.record.text_certainty, 'unclear');
  assert.equal(h.record.fixed_text, draft);
  assert.equal(h.correctionBoxes().length, 0);
  h.click('Minor');
  assert.equal(h.record.text_certainty, null,
    'Returning to the draft does not itself confirm it.');
  assert.equal(h.correctionBoxes()[0].value, draft);
  h.correctionBoxes()[0].fire('input');
  assert.equal(h.record.text_certainty, 'confirmed');
});

test('Unjudged → Can’t tell never invents a human correction', () => {
  const h = harness();
  h.click('Can’t tell');
  assert.equal(h.record.verdict, 'cant_tell');
  assert.equal(h.record.text_certainty, 'unclear');
  assert.equal(h.record.fixed_text, null);
  assert.equal(h.correctionBoxes().length, 0);
});

test('Minor ↔ Wrong retains an already explicitly edited correction', () => {
  const h = harness('minor');
  const area = h.correctionBoxes()[0];
  area.value = 'Um, b- b- ba7ki.';
  area.fire('input');
  h.click('Wrong');
  assert.equal(h.record.text_certainty, 'confirmed');
  assert.equal(h.record.fixed_text, area.value);
  h.click('Minor');
  assert.equal(h.record.text_certainty, 'confirmed');
  assert.equal(h.record.fixed_text, area.value);
});

test('Can’t tell hides the deliberate-error control but retains its prior value', () => {
  const h = harness('minor');
  const deliberate = h.control('Deliberate learner error');
  deliberate.value = 'yes';
  deliberate.fire('change');
  h.click('Can’t tell');
  assert.equal(h.record.deliberate_error, 'yes');
  assert.equal(h.find(e => e.attributes['aria-label'] === 'Deliberate learner error').length, 0);
});

for (const [text, expected] of [
  ['', null], ['   ', null], ['Um, b- ba7ki.', null],
  ['Um, [unclear] ba7ki.', 'unclear'], ['[UNCLEAR]', 'unclear'],
  ['Um, b- b- ba7ki.', 'confirmed'],
]) {
  test(`Wrong text input ${JSON.stringify(text)} produces certainty ${expected}`, () => {
    const h = harness('wrong');
    const area = h.correctionBoxes()[0];
    area.value = text;
    area.fire('input');
    assert.equal(h.record.fixed_text, text, 'Preserve literal input.');
    assert.equal(h.record.text_certainty, expected);
  });
}

test('Rendering a legacy Exact record does not promote or rewrite it', () => {
  const h = harness('exact');
  h.record.fixed_text = 'Legacy edited draft';
  h.record.text_certainty = null;
  const before = JSON.stringify(h.record);
  h.render();
  assert.equal(JSON.stringify(h.record), before);
  assert.equal(h.correctionBoxes().length, 0);
});

let failures = 0;
for (const { name, body } of tests) {
  try { body(); console.log(`PASS ${name}`); }
  catch (error) { failures++; console.error(`FAIL ${name}\n  ${error.message}`); }
}
console.log(`${tests.length - failures}/${tests.length} renderRun regression tests passed.`);
process.exitCode = failures ? 1 : 0;
