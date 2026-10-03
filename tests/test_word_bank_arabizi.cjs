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
