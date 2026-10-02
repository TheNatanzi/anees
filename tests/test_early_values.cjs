// PG-19 (Medi 2026-10-02 "show gray"): a value under the 30-sentence floor is shown grey with "early · n 13" under it,
// never blanked; at or above the floor it is unchanged. Sorting puts settled values first, then early ones, then none.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const E=require('../docs/js/early-value.js');
const DOCS=path.join(__dirname,'..','docs');
const read=f=>fs.readFileSync(path.join(DOCS,f),'utf8');
const ladder=JSON.parse(read('data/sentence-ladder.json'));

test('PG-19 under the floor a value is early, not blank; at the floor it is settled',()=>{
 assert.equal(E.state(false,91.7),'early');
 assert.equal(E.state(true,90.5),'settled');
 assert.equal(E.state(false,null),'none');
 assert.equal(E.label(13),'early · n 13');
 assert.match(E.title(13,30),/30/);
});

test('PG-19 every under-floor hear-it rule with a clear sentence has a % to show grey',()=>{
 const floor=ladder.thresholds.effect_floor;assert.equal(floor,30);
 for(const [id,x] of Object.entries(ladder.rules)){
  const h=x.hear,k=h.understood+h.breakdown;
  if(h.show)assert.ok(k>=floor,id+' settled under the floor');
  else if(k>0)assert.equal(E.state(h.show,h.pct),'early',id+' has '+k+' clear sentences but no % to show');
 }
});

test('PG-19 Hear it sort: settled first, then early, then none, by value inside each group, both directions',()=>{
 const rows=Object.entries(ladder.rules).map(([id,x])=>({id,show:!!x.hear.show,v:x.hear.pct}));
 for(const dir of ['desc','asc']){
  const s=rows.slice().sort((a,b)=>E.compare(a,b,dir));
  const tiers=s.map(r=>E.tier(r.show,r.v));
  assert.deepEqual(tiers,tiers.slice().sort((a,b)=>a-b),dir+': groups out of order');
  for(let i=1;i<s.length;i++)if(tiers[i]===tiers[i-1]&&tiers[i]<2)
   assert.ok(dir==='desc'?s[i-1].v>=s[i].v:s[i-1].v<=s[i].v,dir+': '+s[i-1].id+' before '+s[i].id);
 }
});

test('PG-19 the Grammar page and Progress › Fluency use it instead of a blank',()=>{
 const gc=read('js/grammar-console.js'),fl=read('js/fluency-ladder.js');
 assert.ok(!/'collecting, ' \+/.test(gc),'Grammar Console still blanks under the floor');
 assert.match(gc,/AneesEarly\.label\(n\)/);
 assert.match(gc,/if \(SORT\.key === 'hear'\) return hearCompare\(a, b\)/);
 assert.match(fl,/st==='early'\?`<span class="fl-gbar fl-gbar-early"/);
 assert.match(fl,/AneesEarly\.label\(n\(k\)\)/);assert.match(fl,/E\.label\(n\(ke\)\)/);
 const g=read('grammar.html');
 assert.ok(g.indexOf('js/early-value.js')>=0&&g.indexOf('js/early-value.js')<g.indexOf('js/grammar-console.js'),'grammar.html loads early-value.js first');
 const p=read('progress.html');
 assert.ok(p.indexOf("'early-value'")>=0&&p.indexOf("'early-value'")<p.indexOf("'fluency-ladder'"),'progress.html loads early-value before fluency-ladder');
 assert.match(read('css/grammar.css'),/\.gc-early\{color:var\(--ab-muted\)\}/);
});
