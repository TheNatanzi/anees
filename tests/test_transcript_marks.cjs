// PG-20 transcript marks render helpers (docs/js/transcript-marks.js). Medi 2026-10-02: "for the transcript lets put
// check marks and xs for incorrect correct and mark vocab or grammar with grammar rule", "mark amals signal for
// correction too", "underline the word thats wrong".
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const T=require('../docs/js/transcript-marks.js');
const DOCS=path.join(__dirname,'..','docs');
const fakeAz=s=>({text:'AZ('+s+')'});
test('chips say Wrong / Correct in words, kind and rule, Arabizi first',()=>{
 const w=T.chipModel({k:'grammar',s:'wrong',rule:'B6',name:'kan',said:'كانت',right:'كنت',sig:'says no'},fakeAz);
 assert.equal(w.sign,'✗');assert.equal(w.word,'Wrong');assert.equal(w.kind,'grammar');assert.equal(w.main,'B6 kan');
 assert.equal(w.tip,'Wrong · you said AZ(كانت) → Amal: say AZ(كنت) (she says no)');   // PG-21 wording
 const c=T.chipModel({k:'vocab',s:'correct',w:'Bass',ar:'بس'},fakeAz);
 assert.equal(c.sign,'✓');assert.equal(c.word,'Correct');assert.equal(c.main,'Bass');assert.equal(c.ar,'بس');
 const v=T.chipModel({k:'vocab',s:'wrong',ar:'لـ',said:'لسه',right:'لـ'},fakeAz);
 assert.equal(v.main,'AZ(لسه) → AZ(لـ)');   // PG-21: said → wanted
 const f=T.chipModel({k:'fix',s:'fix',of:'grammar',rule:'B6',sig:'repeats it right',said:'كانت',right:'كنت'},null);
 assert.equal(f.sign,'←');assert.equal(f.tip,"Amal's fix: she repeats it right · said كانت → Amal: كنت");
 const n=T.chipModel({k:'na',s:'na',label:'lesson',why:'off-lesson (customer call)'},null);
 assert.equal(n.word,'Not scored');assert.equal(n.main,'off-lesson (customer call)');assert.equal(n.tip,'Not scored: off-lesson (customer call)');
});
test('underlines wrap the exact span, escape the rest, skip overlaps',()=>{
 const h=T.underlined('<a> كانت هون',[[4,8,'wrong','x1','exact'],[5,7,'fix','f1','exact']]);
 assert.equal(h,'&lt;a&gt; <mark class="tm-ul tm-ul-wrong" data-chip="x1">كانت</mark> هون');
 assert.match(T.underlined('ab cd',[[3,5,'fix','f2','closest']]),/data-closest="1">cd<\/mark>$/);
});
test("filters: All, Only marked, Only ✗, Vocab, Grammar, Amal's fixes",()=>{
 assert.deepEqual(T.FILTERS.map(f=>f[0]),['all','marked','wrong','vocab','grammar','fix']);
 const m={c:[{k:'grammar',s:'wrong',rule:'B6'}]},fx={c:[{k:'fix',s:'fix',of:'grammar'}]},na={c:[{k:'na',s:'na',label:'vocab'}]};
 assert.ok(T.shows(undefined,'all'));assert.ok(!T.shows(undefined,'marked'));
 assert.ok(T.shows(m,'wrong')&&T.shows(m,'grammar')&&!T.shows(m,'vocab')&&!T.shows(m,'fix'));
 assert.ok(T.shows(fx,'fix')&&!T.shows(fx,'grammar')&&!T.shows(fx,'wrong'));
 assert.ok(T.shows(na,'vocab')&&!T.shows(na,'wrong'));
 assert.deepEqual(T.counts({0:m,1:fx,2:na}),{marked:3,wrong:1,vocab:1,grammar:1,fix:1});
 assert.ok(T.LEGEND.some(l=>l[0]==='fix')&&T.LEGEND.some(l=>l[2]==='Wrong')&&T.LEGEND.some(l=>l[2]==='Correct'));
});
test('the Lessons page loads the marks and draws them from tmarks',()=>{
 assert.match(fs.readFileSync(path.join(DOCS,'lessons.html'),'utf8'),/'transcript-marks','lessons-page'/);
 const js=fs.readFileSync(path.join(DOCS,'js','lessons-page.js'),'utf8');
 assert.match(js,/x\.tmarks/);assert.match(js,/function openChip\(list, id\)/);
});
test('every committed lesson renders its marked lines without throwing',()=>{
 for(const f of fs.readdirSync(path.join(DOCS,'data','lessons')).filter(f=>/^20\d\d-\d\d-\d\d\.json$/.test(f))){
  const x=JSON.parse(fs.readFileSync(path.join(DOCS,'data','lessons',f),'utf8'));
  assert.ok(x.tmarks,f);
  for(const [k,m] of Object.entries(x.tmarks)){
   const html=T.underlined(x.turns[+k].text,m.u);
   assert.equal((html.match(/<mark /g)||[]).length,m.u.length,f+' '+k);
   for(const c of m.c){const v=T.chipModel(c,null);assert.ok(v.word&&v.tip,f+' '+c.id);}
  }
 }
});
test('PG-21 a wrong chip says what you said, what Amal said instead, and quotes her line with its time',()=>{
 const v=T.chipModel({s:'wrong',k:'vocab',said:'هادي الصباح',right:'الصبح / بالصباح',sig:'says no',amal_line:'We never say هذا الصبح just say الصبح or بالصباح.',amal_t:540.31},null);
 assert.match(v.tip,/you said هادي الصباح → Amal: say الصبح \/ بالصباح/);
 assert.match(v.tip,/Amal at 9:00: «We never say هذا الصبح/);
});
test('PG-21 / PG-22 a wrong vocab chip names said -> wanted, and an English fix of Amal is shown as hers',()=>{
 const w=T.chipModel({s:'wrong',k:'vocab',said:'سفر',right:'أسافر',ar:'أسافر'},null);
 assert.equal(w.main,'سفر → أسافر');
 const f=T.chipModel({s:'fix',k:'fix',of:'vocab',sig:'prompts you, then gives it',said:'سفر',right:'أسافر',english:'I should travel'},null);
 assert.match(f.tip,/she said it in English: «I should travel»/);
});
