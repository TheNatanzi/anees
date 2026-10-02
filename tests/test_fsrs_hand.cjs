// FSRS-6 hand-computed golden values (engineering audit 2026-09-29, area 7).
// Every expected number below was computed by an independent script typed from the published FSRS-6 formulas
// (open-spaced-repetition "The Algorithm", FSRS-6; default parameters), not from docs/js/fsrs.js:
//   R(t,S)=(1+F*t/S)^-w20, F=0.9^(-1/w20)-1; I(S,r)=round(S/F*(r^(-1/w20)-1)); S0(G)=w[G-1];
//   D0(G)=w4-e^(w5(G-1))+1; D'=w7*D0(4)+(1-w7)*(D+(-w6(G-3))(10-D)/9);
//   same-day S'=S*max(1,e^(w17(G-3+w18))*S^-w19) for Good; recall S'=S(1+e^w8(11-D)S^-w9(e^((1-R)w10)-1));
//   forget S'=min(w11*D^-w12((S+1)^w13-1)e^((1-R)w14), S/e^(w17*w18)).
// Due times use Anees' own steps (learning [1,4] min, relearning [4] min; see the rule conflict in
// plan/ENG-AUDIT-AREA-7-8.md) and the whole-day intervals.
const test = require('node:test'), assert = require('node:assert/strict');
const F = require('../docs/js/fsrs.js');
const MIN = 60000, DAY = 86400000, T0 = Date.parse('2026-09-01T10:00:00Z');
const close = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-9, `${msg}: ${a} vs ${b}`);

test('factor F matches 0.9^(1/decay)-1', () => close(F.FACTOR, 0.9803464944134797, 'F'));

test('new card, Good then Good 4 min later: S/D/interval and due times', () => {
  const a1 = F.schedule(F.newCard('k'), 'good', T0);
  close(a1.stability, 2.3065, 'S0(Good)'); close(a1.difficulty, 2.118103970459015, 'D0(Good)');
  assert.equal(a1.state, 'learning'); assert.equal(a1.due, T0 + 4 * MIN);
  const a2 = F.schedule(a1, 'good', T0 + 4 * MIN);
  close(a2.stability, 2.3065, 'same-day Good cannot lower S (clamped to x1)');
  close(a2.difficulty, 2.1112142357853942, 'D after Good');
  assert.equal(a2.state, 'review'); assert.equal(a2.interval, 2); assert.equal(a2.due, T0 + 4 * MIN + 2 * DAY);
  // retention changes only the interval
  assert.equal(F.schedule(a1, 'good', T0 + 4 * MIN, { desiredRetention: 0.8 }).interval, 8);
  assert.equal(F.schedule(a1, 'good', T0 + 4 * MIN, { desiredRetention: 0.95 }).interval, 1);
});

test('review on time with Good: recall stability, interval 11 days', () => {
  const a1 = F.schedule(F.newCard('k'), 'good', T0), a2 = F.schedule(a1, 'good', T0 + 4 * MIN);
  close(F.retrievability(a2, a2.due), 0.9094932559773545, 'R after 2 whole days');
  const b = F.schedule(a2, 'good', a2.due);
  close(b.stability, 10.971048263078137, 'S recall'); close(b.difficulty, 2.1043313908464474, 'D');
  assert.equal(b.interval, 11); assert.equal(b.due, a2.due + 11 * DAY); assert.equal(F.phase(b), 'learning');
  const c = F.schedule(b, 'good', b.due);
  assert.ok(c.interval >= 21); assert.equal(F.phase(c), 'mature');   // 2 on-time Goods after graduating = mature
  assert.equal(c.interval, 46);
});

test('review Again: forget stability, one lapse, relearn 4 min, back to review next day', () => {
  const a1 = F.schedule(F.newCard('k'), 'good', T0), a2 = F.schedule(a1, 'good', T0 + 4 * MIN);
  const c = F.schedule(a2, 'again', a2.due);
  close(c.stability, 0.6077016626638644, 'S forget'); close(c.difficulty, 7.392238132342694, 'D after Again');
  assert.equal(c.lapses, 1); assert.equal(c.misses, 1); assert.equal(c.state, 'relearning'); assert.equal(c.due, a2.due + 4 * MIN);
  const c2 = F.schedule(c, 'good', c.due);
  close(c2.stability, 0.6597976257475758, 'S same-day Good'); close(c2.difficulty, 7.38007426350719, 'D');
  assert.equal(c2.state, 'review'); assert.equal(c2.interval, 1); assert.equal(c2.due, c.due + DAY);
});

test('new card Again: S0=w0, D0=w4, due in 1 minute', () => {
  const d = F.schedule(F.newCard('k'), 'again', T0);
  close(d.stability, 0.212, 'S0(Again)'); close(d.difficulty, 6.4133, 'D0(Again)');
  assert.equal(d.due, T0 + MIN); assert.equal(d.lapses, 0); assert.equal(d.misses, 1);
});

test('only Again and Good exist', () => {
  assert.throws(() => F.rating('hard')); assert.throws(() => F.rating('easy'));
  assert.equal(F.rating('missed'), 1); assert.equal(F.rating('got'), 3);
});

test('replay drops a row undone on the server (undone_at) even when no client flag is set', () => {
  // card_results rows carry undone_at; fsrs.replay only looked at `undone`, relying on every caller to convert.
  const rows = [{ id: 'a', word_key: 'k', ts: new Date(T0).toISOString(), result: 'got' },
    { id: 'b', word_key: 'k', ts: new Date(T0 + 4 * MIN).toISOString(), result: 'missed', undone_at: new Date(T0 + 5 * MIN).toISOString() }];
  const c = F.replay(rows).get('k');
  assert.equal(c.reps, 1); assert.equal(c.misses, 0);
});

test('replay ignores the local undo marker rows (kind "undo")', () => {
  const rows = [{ id: 'a', word_key: 'k', ts: new Date(T0).toISOString(), result: 'got' },
    { id: 'undo-a2', kind: 'undo', word_key: 'k', ts: new Date(T0 + MIN).toISOString(), result: 'missed' }];
  assert.equal(F.replay(rows).get('k').reps, 1);
});

test('leech tag names the misses that made it a leech (3 learning misses, 0 lapses)', () => {
  let c = F.newCard('k'), t = T0;
  for (let i = 0; i < 3; i++) { c = F.schedule(c, 'again', t); t += MIN; }
  assert.equal(F.isLeech(c), true); assert.equal(c.lapses, 0);
  assert.equal(F.leechLabel(c), 'Leech · 3 misses');
  assert.equal(F.leechLabel(F.newCard('x')), '');
});
