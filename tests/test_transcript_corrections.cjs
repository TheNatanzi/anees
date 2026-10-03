// PG-24 correction mode on the Lessons transcript (docs/js/transcript-corrections.js). Medi 2026-10-03: "do a hand off
// chip where I can make all the corrections. Have it make rules for every correction if possible".
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const C=require('../docs/js/transcript-corrections.js');
const DOCS=path.join(__dirname,'..','docs');

test('PG-24 the fix lives inside the chip: ✗ Not a mistake, ✓ vocab Was wrong, ✓ grammar Not a use, her fix Not a correction',()=>{
 assert.deepEqual(C.chipOffer({k:'vocab',s:'wrong'}),['not-slip']);
 assert.deepEqual(C.chipOffer({k:'grammar',s:'wrong'}),['not-slip']);
 assert.deepEqual(C.chipOffer({k:'vocab',s:'correct'}),['was-wrong']);
 assert.deepEqual(C.chipOffer({k:'grammar',s:'correct'}),['not-use']);
 assert.deepEqual(C.chipOffer({k:'fix',s:'fix'}),['not-correcting']);
 assert.deepEqual(C.chipOffer({k:'medi',s:'medi'}),[]);
 // "Not a mistake" asks why in one tap; only "my Arabic was right" is Amal's
 assert.deepEqual(C.REASONS.map(r=>r[0]),['not-correcting','fixed-first','both-fine','asking','wrong-moment','right']);
});

test('PG-24 undo is a new row; undoing the undo restores the correction',()=>{
 const a={id:'a',kind:'text',ts:'2026-10-03T10:00:00Z'},u={id:'u',kind:'undo',undoes:'a',ts:'2026-10-03T10:01:00Z'},u2={id:'u2',kind:'undo',undoes:'u',ts:'2026-10-03T10:02:00Z'};
 assert.deepEqual(C.effective([a,u]).map(r=>r.id),[]);
 assert.deepEqual(C.effective([a,u,u2]).map(r=>r.id),['a']);
 assert.deepEqual(C.effective([a,a]).map(r=>r.id),['a']);   // a queue replay is one row
});

test('PG-24 "What did you say?" guesses come from her chat, her next line and the word list, most alike first',()=>{
 const g=C.guesses('العشاء',{chat:['3ala','el-3ashara'],amal:['العشرة','طيب'],list:[{arabic:'عشرة',arabizi:'3ashra'},{arabic:'بيت',arabizi:'beit'}]},s=>({text:'el-3asha'}));
 assert.ok(g.length>=2&&g.length<=3);
 assert.ok(g.some(x=>x.w==='العشرة'&&x.from==="Amal's next line"));
 assert.ok(!g.some(x=>x.w==='بيت'));
});

test('PG-24 his correction shows on the line at once and is not applied twice after the rebuild',()=>{
 const r={id:'r1',kind:'text',payload:{engine_wrote:'العشاء',heard:'عشرة'}};
 const t=C.overlay({t:454,who:'Medi',text:'على العشاء'},[r]);
 assert.equal(t.text,'على عشرة');assert.equal(t.engine,'على العشاء');
 const built={t:454,who:'Medi',text:'على عشرة',engine:'على العشاء',heard:[{engine_wrote:'العشاء',heard:'عشرة',correction:'r1'}]};
 assert.equal(C.overlay(built,[r]).text,'على عشرة');
 assert.equal(C.overlay({t:1,who:'Medi',text:'x'},[{id:'s',kind:'speaker',payload:{who:'Amal'}}]).who,'Amal');
 assert.equal(C.parseTime('7:31'),451);assert.equal(C.parseTime('1:02:03'),3723);assert.equal(C.parseTime('soon'),null);
});

test('PG-24 the Lessons page loads the module, and every control is 44 px',()=>{
 const html=fs.readFileSync(path.join(DOCS,'lessons.html'),'utf8');
 assert.match(html,/'transcript-marks','transcript-corrections','lessons-page'/);
 const css=fs.readFileSync(path.join(DOCS,'css','lessons.css'),'utf8');
 assert.match(css,/\.tc-big,#anees-bank \.tc-reason,#anees-bank \.tc-word\{min-height:44px;min-width:44px/);
 assert.match(css,/\.tc-small,#anees-bank \.tc-tag,#anees-bank \.tc-more,#anees-bank \.tc-play,#anees-bank \.tc-undo\{min-height:44px/);
 const js=fs.readFileSync(path.join(DOCS,'js','transcript-corrections.js'),'utf8');
 assert.match(js,/counts update within 15 min/);
 assert.doesNotMatch(js,/confirm\(/);      // no "are you sure"
});
