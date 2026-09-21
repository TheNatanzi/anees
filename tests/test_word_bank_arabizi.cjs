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
test('unlisted Arabic gets marked approximate; rendering never mutates evidence',()=>{
 const event={text:'زغردفل',assessment:'unresolved',context:[{text:'زغردفل'}]};
 const before=JSON.stringify(event),value=A.create()(event.text);
 assert.equal(value.approximate,true);
 assert.equal(value.generated,true);
 assert(!/[\u0621-\u064A]/.test(value.text));
 assert.equal(JSON.stringify(event),before);
});
