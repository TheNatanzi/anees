// Names & places layer: docs/js/names.js must give exactly what scripts/names.py gives (tests/fixtures/names_parity.json,
// written by `python tests/test_names.py --fixture` from the same docs/data/names.json; tests/test_names.py checks the
// Python side against the same file).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const N=require('../docs/js/names.js');
const ROOT=path.join(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(ROOT,'docs/data/names.json'),'utf8'));
const fx=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/names_parity.json'),'utf8'));
const m=N.create(data);
test('JS spans equal Python spans on every fixture text',()=>{
 const bad=[];for(const c of fx.cases){const got=JSON.stringify(m.find(c.text)),want=JSON.stringify(c.spans);if(got!==want)bad.push(c.text);}
 assert.deepEqual(bad,[],'a names.json change moved a span: re-check it, then python tests/test_names.py --fixture');
 assert.ok(fx.cases.length>=40);
});
test('fingerprints (sync sha256) equal Python',()=>{
 for(const [k,v] of Object.entries(fx.fp))assert.equal(N.fp(k.split(' ')),v);
 assert.equal(N.sha256hex('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
test('Medi example: one place token each, chip keeps the name whole',()=>{
 const t='Bass ma, ma bazonn fih Irani. yemken fih رام Allah, Bass Bait La7em, la.';
 assert.deepEqual(m.find(t).map(s=>[s.text,s.id]),[['رام Allah','ramallah'],['Bait La7em','bethlehem']]);
 const html=N.markup(t,m);
 assert.match(html,/رام Allah<span class="nm-chip" dir="auto">رام الله · Ramallah \(place\)<\/span>/);
 assert.match(html,/Bait La7em<span class="nm-chip" dir="auto">بيت لحم · Bethlehem \(place\)<\/span>/);
 const az=N.azLine('يمكن فيه رام الله، بس بيت لحم، لا.',m,s=>s.replace(/[؀-ۿ]+/g,'X'));
 assert.ok(az.includes('رام الله<span class="nm-chip"')&&az.includes('بيت لحم<span class="nm-chip"')&&!/Bait|La7em/.test(az));
 assert.equal(N.chipText({kind:'person',text:'Amal'}),'(person)');
});
