// PG-37 one box per line (docs/js/correction-parse.js). Medi 2026-10-08: "Can we turn this into just 1 box and we can
// write the correction, not try and separate into so many boxes?" The rule layer reads the obvious shapes into the same
// structured rows the seven boxes made; when it is not sure it says so (the panel then asks the AI read); the raw text
// always rides along in payload.raw.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const P=require('../docs/js/correction-parse.js');
const ROOT=path.join(__dirname,'..');

const MEDI={who:'Medi',line:'على العشاء رح نروح',t:454};
const one=(text,ctx)=>{const r=P.parse(text,ctx||MEDI);assert.equal(r.items.length,1,text+' -> '+JSON.stringify(r));return r;};

test('PG-37 speaker: "this was Amal" and its short forms become a speaker row',()=>{
 for(const s of ['this was Amal','This was amal','Amal','that\'s Amal','tutor','Amal said this','not me']){
  const r=one(s);assert.equal(r.sure,true,s);assert.equal(r.items[0].kind,'speaker');assert.equal(r.items[0].payload.who,'Amal');
 }
 const r=one('this was me',{who:'Amal',line:'طيب',t:10});assert.equal(r.items[0].payload.who,'Medi');
});

test('PG-37 time: "time 2:13", "at 2:13", bare "2:13" become a time row in seconds',()=>{
 for(const s of ['time 2:13','at 2:13','2:13','the time is 2:13','time should be 2:13']){
  const r=one(s);assert.equal(r.sure,true,s);assert.equal(r.items[0].kind,'time');assert.equal(r.items[0].payload.t,133);
 }
 assert.equal(one('1:02:13').items[0].payload.t,3733);
});

test('PG-37 missing word: "missing word X", "dropped X", "add X" (Arabic or Arabizi) become a missing row',()=>{
 for(const [s,w] of [['missing word ya3ni','ya3ni'],['missing يعني','يعني'],['dropped the word kteer','kteer'],['add ya3ni','ya3ni'],['forgot "ya3ni"','ya3ni'],['ya3ni is missing','ya3ni']]){
  const r=one(s);assert.equal(r.sure,true,s);assert.equal(r.items[0].kind,'missing');assert.equal(r.items[0].payload.heard,w);
 }
});

test('PG-37 "I said X not Y": Y is the engine\'s word on the line (also when he spells it a little differently)',()=>{
 const r=one('I said el-3ashara not العشاء');
 assert.equal(r.sure,true);assert.equal(r.items[0].kind,'text');assert.deepEqual([r.items[0].payload.engine_wrote,r.items[0].payload.heard],['العشاء','el-3ashara']);
 const r2=one('said العشرة, not العشا');     // near spelling of the line's word
 assert.equal(r2.sure,true);assert.equal(r2.items[0].payload.engine_wrote,'العشاء');
 const r3=one('not العشاء, العشرة');
 assert.equal(r3.sure,true);assert.equal(r3.items[0].payload.heard,'العشرة');
});

test('PG-37 a Latin fix finds the Arabic word on the line through the Arabizi reader of the page',()=>{
 const ctx={who:'Medi',line:'مرحبا. Can you hear me?',t:10,toArabizi:w=>w==='مرحبا'?'marhaba':w};
 const r=P.parse('I said marhaban not marhaba',ctx);
 assert.equal(r.sure,true);assert.equal(r.items[0].kind,'text');assert.deepEqual([r.items[0].payload.engine_wrote,r.items[0].payload.heard],['مرحبا','marhaban']);
 assert.equal(P.parse('I said marhaban not marhaba',{who:'Medi',line:'مرحبا. Can you hear me?',t:10}).sure,false);   // no reader: not sure, the AI reads it
});

test('PG-37 "I said X" alone: the engine\'s word is the one that sounds most like X',()=>{
 const r=one('I said عشرة');
 assert.equal(r.sure,true);assert.equal(r.items[0].kind,'text');assert.equal(r.items[0].payload.engine_wrote,'العشاء');
 const r2=P.parse('I said something completely different here',MEDI);   // nothing close on the line -> not sure
 assert.equal(r2.sure,false);
});

test('PG-37 "X should be Y" on his line is a slip (said / should / kind), wrong word unless grammar words appear',()=>{
 const r=one('ومه should be أمه');
 assert.equal(r.sure,true);assert.equal(r.items[0].kind,'add');
 assert.deepEqual([r.items[0].payload.wrong,r.items[0].payload.right,r.items[0].payload.k],['ومه','أمه','vocab']);
 assert.equal(r.items[0].label,'You said ومه, should be أمه, wrong word');
 const g=one('ra7 nenbisit should be ra7 nenbese6 (grammar)');
 assert.equal(g.items[0].payload.k,'grammar');assert.equal(g.items[0].payload.right,'ra7 nenbese6');
 const a=one('baddi -> biddi');
 assert.equal(a.items[0].kind,'add');assert.deepEqual([a.items[0].payload.wrong,a.items[0].payload.right],['baddi','biddi']);
 const v=one('katabet → katabat verb ending');
 assert.equal(v.items[0].payload.k,'grammar');
});

test('PG-37 "X should be Y" with engine words is a heard-word fix, not a slip',()=>{
 const r=one('engine wrote العشاء should be العشرة');
 assert.equal(r.items[0].kind,'text');assert.equal(r.items[0].payload.engine_wrote,'العشاء');assert.equal(r.items[0].payload.heard,'العشرة');
 const r2=one('the engine heard العشاء, I said el 3ashara');
 assert.equal(r2.sure,true);assert.equal(r2.items[0].kind,'text');assert.equal(r2.items[0].payload.heard,'el 3ashara');
});

test('PG-37 "wrong word: X" / "X is wrong" is a slip with no right form yet',()=>{
 const r=one('wrong word: العشاء');
 assert.equal(r.sure,true);assert.equal(r.items[0].kind,'add');assert.equal(r.items[0].payload.wrong,'العشاء');assert.equal(r.items[0].payload.right,null);
 const r2=one('نروح is wrong');assert.equal(r2.items[0].kind,'add');assert.equal(r2.items[0].payload.wrong,'نروح');
});

test('PG-37 on the tutor\'s line a slip shape is not sure (slips are his), speaker and time still parse',()=>{
 const A={who:'Amal',line:'لا، بنقول العشرة',t:460};
 assert.equal(P.parse('العشرة should be العشاء',A).sure,false);
 assert.equal(P.parse('this was me',A).items[0].payload.who,'Medi');
 assert.equal(P.parse('time 7:41',A).items[0].payload.t,461);
});

test('PG-37 free words nobody can shape: not sure, one note item, raw kept',()=>{
 for(const s of ['she laughed here, I think she liked it','the whole sentence is garbage','??']){
  const r=P.parse(s,MEDI);assert.equal(r.sure,false,s);assert.equal(r.items.length,1);assert.equal(r.items[0].kind,'note');assert.equal(r.items[0].payload.raw,s);
 }
 assert.deepEqual(P.parse('',MEDI),{sure:false,items:[],why:'empty'});
});

test('PG-37 every item carries payload.raw = exactly what he typed',()=>{
 for(const s of ['this was Amal','time 2:13','missing word ya3ni','I said عشرة','ومه should be أمه','wrong word: العشاء']){
  const r=P.parse(s,MEDI);r.items.forEach(it=>assert.equal(it.payload.raw,s));
 }
});

test('PG-37 the AI answer is checked against the line and becomes the same items; junk becomes a note',()=>{
 const items=P.fromAI({items:[{kind:'text',engine_wrote:'العشاء',heard:'العشرة'},{kind:'add',said:'نروح',right:'منروح',k:'grammar'},{kind:'speaker',who:'Nobody'},{kind:'time',t:'2:13'}]},'raw words',MEDI);
 assert.deepEqual(items.map(i=>i.kind),['text','add','time']);
 assert.equal(items[0].payload.raw,'raw words');assert.equal(items[0].payload.from,'ai');assert.equal(items[2].payload.t,133);
 const junk=P.fromAI({items:[{kind:'text',engine_wrote:'nothing-like-this',heard:'x'}]},'raw words',MEDI);
 assert.deepEqual(junk.map(i=>i.kind),['note']);assert.equal(junk[0].payload.raw,'raw words');
 assert.deepEqual(P.fromAI(null,'raw words',MEDI).map(i=>i.kind),['note']);
});

test('PG-37 the prompt file the AI read uses exists and names every kind the parser accepts',()=>{
 const p=fs.readFileSync(path.join(ROOT,'scripts','correction_parse_prompt.md'),'utf8');
 for(const k of ['speaker','time','missing','text','add','note']) assert.ok(p.includes('"'+k+'"'),'prompt names '+k);
 // the edge function ships the same prompt (generated copy)
 const ts=fs.readFileSync(path.join(ROOT,'supabase','functions','parse-correction','prompt.ts'),'utf8');
 assert.ok(ts.includes(p.trim().slice(0,80)),'prompt.ts carries the prompt file');
});

test('PG-37 the panel is one box: transcript-corrections.js has no time / missing / slip inputs left',()=>{
 const js=fs.readFileSync(path.join(ROOT,'docs','js','transcript-corrections.js'),'utf8');
 assert.ok(!js.includes("'Fix time'")&&!js.includes("'Add word'")&&!js.includes("'Add slip'"),'old boxes gone');
 assert.ok(js.includes('Write the fix in your own words'),'the one box');
 assert.ok(js.includes("'This was '"),'the one-tap speaker button stays');
 assert.ok(/raw:\s*raw|payload\.raw|raw: *text/.test(js),'raw saved with the row');
 assert.ok(fs.readFileSync(path.join(ROOT,'docs','lessons.html'),'utf8').includes("'correction-parse'"),'lessons.html loads the parser');
});

test('PG-37 after Send his words stay on the line with Edit (reopens the box prefilled, replaces the rows) and Undo',()=>{
 const js=fs.readFileSync(path.join(ROOT,'docs','js','transcript-corrections.js'),'utf8');
 assert.ok(js.includes("'Your fix: '"),'his words shown under the line');
 assert.ok(js.includes("'Edit', function () { moreMenu(row, x, turn, parts, raw, same); }"),'Edit reopens the box with his words');
 assert.ok(js.includes('(replaces || []).forEach(function (r) { undo(r); });'),'an edit undoes the old rows (append-only) before the new ones');
 assert.ok(fs.readFileSync(path.join(ROOT,'docs','css','lessons.css'),'utf8').includes('.tc-note-line'),'styled');
});
