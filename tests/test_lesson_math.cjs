// Eng audit 2026-09-29: decision 4 ("≈" on scores from unverified lessons, with the reasons) and decision 6 (one pooled
// average for the Lessons page and the Overview). node tests/test_lesson_math.cjs
'use strict';
const assert = require('node:assert/strict'), path = require('path'), fs = require('fs');
const LM = require(path.join(__dirname, '..', 'docs', 'js', 'lesson-math.js'));
const V = { date: '2026-09-01', release: { status: 'verified', reasons: [] }, words: { right: 90, partial: 0, wrong: 10, scored: 100 }, grammar: { uses: 100, mistakes: 10, scored_mistakes: 10 } };
const U = { date: '2026-09-18', release: { status: 'not verified', reasons: ['reader agreement: pass 1 58.7 %', 'checks: 26 rows'] }, words: { right: 2, partial: 3, wrong: 7, scored: 12 }, grammar: { uses: 62, mistakes: 45, scored_mistakes: 40, unscored_mistakes: 5 } };

// decision 4: verified -> exact; not verified -> "≈" + reasons; an average is "≈" when any input is
assert.equal(LM.mark('74%', [V]).text, '74%');
assert.equal(LM.mark('74%', [U]).text, '≈74%');
assert.match(LM.why([U]), /reader agreement: pass 1 58\.7 %/);
assert.equal(LM.mark('80%', [V, U]).approx, true);
assert.match(LM.why([V, U]), /1 of 2 lessons/);
assert.equal(LM.approx([{ date: 'x' }]), true, 'no release state = not verified, never exact');
assert.match(LM.html('74%', [U]), /class="rel-approx"[^>]*title="Not verified/);

// decision 6: pooled, not a mean of lesson percentages (the Lessons page showed a plain mean: 76 % vs the Overview's 80.0 %)
const w = LM.pooledWords([V, U]);
assert.equal(w.scored, 112); assert.equal(w.points, 93.5);
assert.equal(Math.round(w.pct * 10) / 10, 83.5);            // a mean of 90 % and 29.2 % would say 59.6 %
const g = LM.pooledGrammar([V, U]);
assert.equal(g.uses, 162); assert.equal(g.slips, 50); assert.equal(g.n, 2, 'no lesson is left out');

// both pages use this one function (the check scripts/check_numbers.py also runs)
for (const f of ['lessons-page.js', 'lesson-overview.js']) {
  const src = fs.readFileSync(path.join(__dirname, '..', 'docs', 'js', f), 'utf8');
  assert.ok(src.includes('pooledWords(') && src.includes('pooledGrammar(') && src.includes('pooledFillers('), f + ' must use docs/js/lesson-math.js');
}
// every page that shows a lesson-derived score loads lesson-math.js
for (const [page, needle] of [['lessons.html', "'lesson-math'"], ['progress.html', "'lesson-math'"], ['word-bank.html', "'lesson-math'"], ['grammar.html', 'js/lesson-math.js']]) {
  assert.ok(fs.readFileSync(path.join(__dirname, '..', 'docs', page), 'utf8').includes(needle), page + ' does not load lesson-math.js');
}
// talk share and filled pauses pooled the same way on every page (Lessons showed plain means: 57 % / 9.5 vs 56.9 % / 10.1)
const T1 = { talk: { medi_s: 600, amal_s: 400 }, fillers: { count: 100, comparable: true } }, T2 = { talk: { medi_s: 60, amal_s: 540 }, fillers: { count: 50, comparable: false } };
assert.equal(LM.pooledTalk([T1, T2]).pct, 100 * 660 / 1600);
assert.equal(LM.pooledFillers([T1, T2]).perMin, 10, 'a lesson whose turns lost the fillers is left out');
// the one filled-pause test = scripts/build_lessons_page_data.py is_filler(): آه at the start of a turn is "yes"
assert.equal(LM.countFillers('آه uh امم كتير آه'), 3);
console.log('lesson-math: ok');
