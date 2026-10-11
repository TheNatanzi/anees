// PG-39 (Medi 2026-10-11 "lets simplify the correct vocab and just make one pill box for all the correct words in the
// sentence" · "theres like 6 different vocab pills here"): a joined sentence shows ONE green vocab pill, one pill per
// grammar rule. Display only.
const {test}=require('node:test');const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const src=fs.readFileSync(path.join(__dirname,'..','docs','js','lessons-page.js'),'utf8');
const body=src.slice(src.indexOf('function mergeCorrect('),src.indexOf('function sentences('));
const mergeCorrect=new Function(body+'; return mergeCorrect;')();
test('PG-39 a joined sentence: one green vocab pill with every word, one pill per grammar rule',()=>{
 const cs=[{id:'a',k:'vocab',s:'correct',w:'Ana ba77eb'},{id:'b',k:'vocab',s:'correct',words:[{w:'Ana baru7'},{w:'Ana ba2dar'}]},
  {id:'g1',k:'grammar',s:'correct',rule:'A1'},{id:'g2',k:'grammar',s:'correct',rule:'A1'},{id:'g3',k:'grammar',s:'correct',rule:'B1'},
  {id:'x',k:'vocab',s:'wrong',w:'z'},{id:'n',k:'vocab',s:'na',w:'Kalifornia'}];
 const out=mergeCorrect(cs), shown=out.filter(c=>!c.hide);
 assert.equal(shown.filter(c=>c.k==='vocab'&&c.s==='correct').length,1);
 assert.deepEqual(shown.find(c=>c.id==='a').words.map(w=>w.w),['Ana ba77eb','Ana baru7','Ana ba2dar']);
 assert.equal(shown.filter(c=>c.rule==='A1').length,1);
 assert.ok(shown.find(c=>c.s==='wrong')&&shown.find(c=>c.s==='na'));     // other chips untouched
 assert.equal(cs[0].words,undefined);                                       // the page data is not changed
});
