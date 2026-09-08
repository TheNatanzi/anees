'use strict';
const assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const path = require('node:path');
const {createPlayer, verifyFile, mount} = require(path.resolve(process.argv[2] || './transcript-player.js'));
class Element {
  constructor() { this.events = {}; this.attrs = {}; this.dataset = {}; this.textContent = ''; this.classList = {toggle() {}}; }
  addEventListener(name, fn) { (this.events[name] ||= new Set()).add(fn); }
  removeEventListener(name, fn) { this.events[name]?.delete(fn); }
  emit(name, event = {}) { for (const fn of [...(this.events[name] || [])]) fn(event); }
  setAttribute(k, v) { this.attrs[k] = v; }
  removeAttribute(k) { delete this.attrs[k]; if (k === 'src') this.src = ''; }
  click() { this.clicks = (this.clicks || 0) + 1; this.emit('click'); }
}
class Audio extends Element {
  constructor() { super(); this.readyState = 1; this.duration = 3764.109; this.currentTime = 0; this.paused = true; this.calls = 0; }
  load() { this.loads = (this.loads || 0) + 1; }
  pause() { this.paused = true; this.emit('pause'); }
  play() { this.calls++; this.paused = false; return this.nextPlay ? this.nextPlay() : Promise.resolve(); }
}
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  const a = new Audio(), log = {status: '', active: null, picks: 0};
  const p = createPlayer({audio: a, status: t => log.status = t, active: b => log.active = b, needFile: () => log.picks++});
  p.setSource('blob:verified');
  return {a, p, log};
}
(async function () {
  let checks = 0;
  let {a, p, log} = setup();
  await p.playFrom('A', 519.985);
  assert.equal(a.currentTime, 519.635); assert.equal(log.active, 'A'); checks++;
  await p.playFrom('A', 519.985); assert.equal(a.paused, true); assert.equal(log.active, null); checks++;
  await p.playFrom('A', 0); assert.equal(a.currentTime, 0); checks++;
  a.pause(); assert.equal(log.active, null);
  await p.playFrom('A', 1); assert.equal(log.active, 'A'); checks++; p.destroy();
  ({a, p, log} = setup()); a.readyState = 0;
  const old = p.playFrom('A', 10), latest = p.playFrom('B', 20);
  a.readyState = 1; a.emit('loadedmetadata'); await Promise.all([old, latest]);
  assert.equal(a.currentTime, 19.65); assert.equal(a.calls, 1); assert.equal(log.active, 'B'); checks++; p.destroy();
  ({a, p, log} = setup()); a.readyState = 0;
  const cancelled = p.playFrom('A', 10); await p.playFrom('A', 10);
  a.readyState = 1; a.emit('loadedmetadata'); await cancelled;
  assert.equal(a.calls, 0); assert.equal(log.active, null); checks++; p.destroy();
  ({a, p, log} = setup());
  let completeOld; a.nextPlay = () => new Promise(resolve => { completeOld = resolve; });
  const delayed = p.playFrom('A', 10); await flush();
  a.nextPlay = null; await p.playFrom('B', 20); completeOld(); await delayed;
  assert.equal(log.active, 'B'); assert.equal(a.currentTime, 19.65); checks++; p.destroy();
  ({a, p, log} = setup());
  a.nextPlay = () => Promise.reject(Object.assign(new Error('gesture'), {name: 'NotAllowedError'}));
  await p.playFrom('A', 10); assert.match(log.status, /Tap a line/); assert.equal(log.active, null); checks++;
  a.nextPlay = null; await p.playFrom('A', 10); assert.equal(log.active, 'A'); checks++;
  a.emit('ended'); assert.equal(log.active, null); assert.match(log.status, /ended/); checks++;
  await p.playFrom('B', 5000); assert.match(log.status, /outside/); checks++;
  const calls = a.calls; await p.playFrom('C', NaN); assert.equal(a.calls, calls); checks++;
  p.setSource(null); await p.playFrom('A', 10); assert.equal(log.picks, 1); checks++; p.destroy();
  ({a, p, log} = setup()); a.readyState = 0;
  const errored = p.playFrom('A', 10); a.emit('error'); await errored;
  assert.equal(log.active, null); assert.match(log.status, /could not load/); checks++; p.destroy();
  const bytes = Uint8Array.from([1, 2, 3]).buffer;
  const sha256 = Buffer.from(await webcrypto.subtle.digest('SHA-256', bytes)).toString('hex');
  const file = {size: 3, arrayBuffer: async () => bytes};
  const digest = webcrypto.subtle.digest.bind(webcrypto.subtle);
  assert.equal(await verifyFile(file, {bytes: 3, sha256}, digest), true); checks++;
  await assert.rejects(verifyFile(file, {bytes: 4, sha256}, digest), /wrong-file/); checks++;
  await assert.rejects(verifyFile(file, {bytes: 3, sha256: '0'.repeat(64)}, digest), /wrong-file/); checks++;
  // Actual UI binding: no network API exists in this fake browser.
  const elements = Object.fromEntries(['lesson-audio-panel', 'lesson-audio-file', 'lesson-audio-choose', 'lesson-audio-status'].map(id => [id, new Element()]));
  elements['lesson-audio'] = new Audio();
  Object.assign(elements['lesson-audio-panel'].dataset, {bytes: '3', sha256});
  const button = new Element(); Object.assign(button.dataset, {start: '20', label: 'Medi at 00:20'});
  const urls = [], revoked = [], win = new Element();
  Object.assign(win, {crypto: webcrypto, URL: {createObjectURL: () => { const u = 'blob:' + urls.length; urls.push(u); return u; }, revokeObjectURL: u => revoked.push(u)}});
  const ui = mount({getElementById: id => elements[id], querySelectorAll: () => [button]}, win);
  button.click(); assert.equal(elements['lesson-audio-file'].clicks, 1); checks++;
  elements['lesson-audio-file'].files = [file]; elements['lesson-audio-file'].emit('change');
  for (let i = 0; i < 20 && !urls.length; i++) await flush();
  assert.equal(urls.length, 1); assert.equal(elements['lesson-audio'].src, 'blob:0'); checks++;
  button.click(); await flush(); assert.equal(button.attrs['aria-pressed'], 'true'); checks++;
  elements['lesson-audio-file'].files = []; elements['lesson-audio-file'].emit('change');
  await flush(); assert.equal(elements['lesson-audio'].src, 'blob:0'); checks++;
  elements['lesson-audio-file'].files = [file]; elements['lesson-audio-file'].emit('change');
  for (let i = 0; i < 20 && urls.length < 2; i++) await flush();
  assert.deepEqual(revoked, ['blob:0']); checks++;
  ui.cleanup(); assert.deepEqual(revoked, ['blob:0', 'blob:1']); checks++;
  console.log(checks + ' transcript playback checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
