const {test}=require('node:test');
const assert=require('node:assert/strict');
const A=require('../docs/js/word-bank-arabizi.js');
test('lesson display preserves false starts, repetitions and mixed English',()=>{
 const render=A.create();
 const raw='بيصلع-- بيصلح كل، كل إشي اللي،';
 const value=render(raw);
 assert.equal(value.text,'bi9la3-- bi9alle7 kul, kul ishi illi,');
 assert.equal(value.source,raw);
 assert.equal(value.approximate,false);
 assert.equal(render("اللي، so it's بيخربه.").text,"illi, so it's bi5arrbo.");
 assert.equal(render('So كل الجملة شو؟').text,'So kul el-jumle shu?');
});
test('known document spellings and explicit existing Arabizi stay readable',()=>{
 const render=A.create([{arabic:'جمبري',arabizi:'Gambari'}]);
 assert.equal(render('جمبري').text,'Gambari');
 assert.equal(render('gambari, uh...').text,'gambari, uh...');
 assert.equal(render('gambari, uh...').generated,false);
});

test('written who and from remain distinct without correcting raw ASR spelling',()=>{
 const render=A.create();
 assert.equal(render('مين').text,'meen');
 assert.equal(render('من').text,'min');
 assert.equal(render('min').text,'min');
});
test('unlisted Arabic stays in Arabic with an uncertainty label; source evidence is immutable',()=>{
 const event={text:'زغردفل',assessment:'unresolved',context:[{text:'زغردفل'}]};
 const before=JSON.stringify(event),value=A.create()(event.text);
 assert.equal(value.approximate,true);
 assert.equal(value.generated,true);
 assert.equal(value.text,event.text,'Do not invent vowels or an Arabizi consonant string');
 assert.equal(JSON.stringify(event),before);
});
test('كم shows as Amal\'s Kam (how many), never Kum (sleeve) - Medi 2026-10-02, registry AZ-08',()=>{
 const render=A.create();
 assert.equal(render('كم').text,'Kam');
 assert.notEqual(render('كم').text.toLowerCase(),'kum');
});
test('AZ-11 ثانية is taanye (another) after a noun, Saanie (a second) only after a number or kam',()=>{
 const az=require('../docs/js/word-bank-arabizi.js'),fs2=require('fs'),p2=require('path'),D=p2.join(__dirname,'..','docs','data');
 const J2=f=>JSON.parse(fs2.readFileSync(p2.join(D,f),'utf8'));
 const r=az.create(J2('words.json').items,J2('word-bank-catalog.json'),J2('arabizi-extra.json'));
 assert.equal(r('بدي بلوزة ثانية.').text,'beddi Blooze taanye.');
 assert.equal(r('مرة ثانية').text,'Marra taanye');
 assert.equal(r('خمس ثانية').text.split(' ')[1],'Saanie');
 assert.equal(r('كم ثانية؟').text,'Kam Saanie?');
});
test('AZ-11 عندنا shows as her 3indna, never 3inna',()=>{
 const az=require('../docs/js/word-bank-arabizi.js'),fs2=require('fs'),p2=require('path'),D=p2.join(__dirname,'..','docs','data');
 const J2=f=>JSON.parse(fs2.readFileSync(p2.join(D,f),'utf8'));
 const r=az.create(J2('words.json').items,J2('word-bank-catalog.json'),J2('arabizi-extra.json'));
 assert.equal(r('عندنا').text,'3indna');
});
test('AZ-11 طريق shows as her 6aree2',()=>{
 const az=require('../docs/js/word-bank-arabizi.js'),fs2=require('fs'),p2=require('path'),D=p2.join(__dirname,'..','docs','data');
 const J2=f=>JSON.parse(fs2.readFileSync(p2.join(D,f),'utf8'));
 assert.equal(az.create(J2('words.json').items,J2('word-bank-catalog.json'),J2('arabizi-extra.json'))('طريق').text,'6aree2');
});
test('AZ-11 el-marra el-taanye and her qanoon',()=>{
 const az=require('../docs/js/word-bank-arabizi.js'),fs2=require('fs'),p2=require('path'),D=p2.join(__dirname,'..','docs','data');
 const J2=f=>JSON.parse(fs2.readFileSync(p2.join(D,f),'utf8'));
 const r=az.create(J2('words.json').items,J2('word-bank-catalog.json'),J2('arabizi-extra.json'));
 assert.equal(r('المرة الثانية').text,'el-marra el-taanye'.replace('el-marra',r('المرة').text));
 assert.equal(r('القانون').text,'el-qanoon');
});
test('S1 / AZ-05 / AZ-10: an as-said row with scope "lessons" is Arabizi on the Lessons page only; elsewhere the word stays Arabic',()=>{
 // Codex final approval 2026-10-05, blocker 7: his own wrong / cut-off / unclear forms entered the converter of every page
 const extra={words:{'تز':{latin:'tez-',method:'as-said',from:'cut-off tez3ej',meaning:'(cut off)',scope:'lessons'},'دلت':{latin:'dallat',method:'sound',from:'her Dallat'}}};
 const anywhere=A.create([],{},extra),lessons=A.create([],{},extra,{scope:'lessons'});
 assert.deepEqual([anywhere('تز').text,anywhere('تز').approximate],['تز',true]);
 assert.deepEqual([lessons('تز').text,lessons('تز').approximate],['tez-',false]);
 assert.equal(anywhere('دلت').text,'dallat');assert.equal(lessons('دلت').text,'dallat');     // a row without a scope is used everywhere
 // the real file: every as-said row added with the 2026-10-04 re-read carries the scope, and no other row does
 const fs2=require('fs'),p2=require('path'),D=p2.join(__dirname,'..','docs','data');
 const W=JSON.parse(fs2.readFileSync(p2.join(D,'arabizi-extra.json'),'utf8')).words;
 const reread=Object.values(W).filter(v=>String(v.added||'').startsWith('2026-10-04 re-heard'));
 assert.equal(reread.length,430);
 assert.equal(reread.filter(v=>v.method==='as-said').length,188);
 assert.ok(reread.filter(v=>v.method==='as-said').every(v=>v.scope==='lessons'));
 assert.equal(Object.values(W).filter(v=>v.scope).length,192);   // 188 + 4 as-said rows of the 2026-10-07 re-read (TR-27 text)
 for(const f of ['scripts/arabizi_gaps.cjs','scripts/lessons_page_node.cjs','docs/js/lessons-page.js'])assert.ok(fs2.readFileSync(p2.join(__dirname,'..',f),'utf8').includes("scope: 'lessons'"),f+' must ask for the Lessons scope');
 for(const f of ['docs/js/grammar-console.js','docs/js/transcript-arabizi.js','docs/js/fluency-ladder.js','docs/js/fluency-unknowns.js','docs/js/vocab-unknowns.js'])assert.ok(!fs2.readFileSync(p2.join(__dirname,'..',f),'utf8').includes("scope: 'lessons'"),f+' is not the Lessons page');
});
