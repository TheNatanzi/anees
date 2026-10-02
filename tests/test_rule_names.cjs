// Rule-id tooltips (docs/js/rule-names.js, Medi 2026-10-02): only ids that exist in docs/data/grammar-buckets.json are
// picked up, whole tokens only, and the label is "<id> · <name> — <one_line>". Every page that draws rule ids loads it.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const R=require('../docs/js/rule-names.js');
const DOCS=path.join(__dirname,'..','docs');
const B=JSON.parse(fs.readFileSync(path.join(DOCS,'data','grammar-buckets.json'),'utf8')).buckets;
const rules=Object.fromEntries(B.map(b=>[b.id,b]));
test('finds only real rule ids, as whole tokens',()=>{
 const ids=R.find('Lessons with B5, D2 and A10b; not Z9, not B99, not xB5, not B5x, ana ba7ki A2.',rules).map(h=>h.id);
 assert.deepEqual(ids,['B5','D2','A10b','A2']);
 assert.deepEqual(R.find('ma fi ishi',rules),[]);
});
test('positions slice back to the id',()=>{
 const s='rule B18 here';for(const h of R.find(s,rules))assert.equal(s.slice(h.start,h.end),h.id);
});
test('label = id · name — one line, without markdown backticks',()=>{
 const l=R.label('A1',rules.A1);
 assert.ok(l.startsWith('A1 · '+rules.A1.name+' — '));assert.ok(!l.includes('`'));
});
test('pages that show rule ids load the script',()=>{
 for(const f of ['progress.html','grammar.html','tutor.html','ai-reports.html','lessons.html','cards.html','word-bank.html','amal/grammar-rules.html','amal/review.html']){
  const t=fs.readFileSync(path.join(DOCS,f),'utf8');assert.match(t,/js\/rule-names\.js/,f);
 }
});
