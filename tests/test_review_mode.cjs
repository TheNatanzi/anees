// PG-50 fast review mode (docs/js/review-mode.js). Medi 2026-10-10: "It takes a lot of time to review in its current
// state, its gonna take longer in this metod" · "Is there anyway we can simplify this so that it doesnt take as much
// time for amal and i". Pure core only: key -> row, the blind block, undo, re-listen, seconds, order + end card.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const R=require('../docs/js/review-mode.js');
const ROOT=path.join(__dirname,'..');

// 60 lines: 55 unsure (order 1-55), 5 confident (order 56-60), the picker's shape
function pick(){
 const lines=[];
 for(let k=0;k<60;k++){const unsure=k<55;lines.push({i:k*2,parts:[k*2],t:10+k*10,end:14+k*10,mmss:'',unsure,why:unsure?['✗ chip on it']:[],order:k+1,blind:k<50,
  propose:{k:k%2?'grammar':'vocab',said:'بيت',right:'البيت',from:'readers'}});}
 // the unsure ones come first in `order`; the times interleave so order != time order
 return {date:'2026-10-08',all:60,unsure_n:55,confident_n:5,lines};
}
let n=0;const env=(extra)=>Object.assign({now:1e12+(n+=8000),uuid:()=>'id-'+n,line:'أنا ساكن في بيت كبير',end:null,who:'Medi'},extra||{});

test('PG-50 key 1 writes one inert trace row (rule-answer, proposal review:fast) with review_mode, secs and blind',()=>{
 const s=R.create({pick:pick(),date:'2026-10-08',now:1e12});n=0;
 const [row]=R.answer(s,{key:1},env());
 assert.equal(row.kind,'rule-answer');assert.equal(row.proposal,'review:fast');assert.equal(row.answer,'one');
 assert.equal(row.payload.review_mode,'fast');assert.equal(row.payload.verdict,'right');assert.equal(row.payload.blind,true);
 assert.equal(row.payload.secs,8);assert.equal(row.turn_t,10);assert.equal(row.turn_who,'Medi');assert.equal(row.lesson_date,'2026-10-08');
 assert.equal(row.payload.reviewed,1);assert.equal(s.pos,1);
});

test('PG-50 key 2 = a text row like the heard rows (engine_wrote -> heard, from typed); the box finds the word he means',()=>{
 const s=R.create({pick:pick(),date:'2026-10-08',now:1e12});
 assert.equal(R.targets('beit','أنا ساكن في بيت كبير',w=>({'بيت':'beit','كبير':'kbeer','ساكن':'saken','أنا':'ana','في':'fi'})[w]||w)[0],'بيت');
 assert.equal(R.targets('بيتي','أنا ساكن في بيت كبير')[0],'بيت');
 const [row]=R.answer(s,{key:2,heard:'بيتي',engine_wrote:'بيت'},env());
 assert.equal(row.kind,'text');assert.deepEqual(row.target,{word:'بيت'});
 assert.equal(row.payload.engine_wrote,'بيت');assert.equal(row.payload.heard,'بيتي');assert.equal(row.payload.from,'typed');
 assert.equal(row.payload.review_mode,'fast');assert.ok(row.payload.line.includes('بيت'));
});

test('PG-50 key 3 = an add row; the robot proposes vocab/grammar and one key flips it (no rule id asked)',()=>{
 const s=R.create({pick:pick(),date:'2026-10-08',now:1e12});
 const it=R.current(s),pr=R.proposal(it,[],'x');
 assert.equal(pr.k,'vocab');assert.equal(pr.said,'بيت');
 assert.equal(R.proposal({},[{k:'grammar',s:'wrong',said:'هادا'}],'').k,'grammar');
 const [row]=R.answer(s,{key:3,said:'بيت',k:'grammar',proposed:'vocab',flipped:true},env());
 assert.equal(row.kind,'add');assert.deepEqual(row.target,{k:'grammar',said:'بيت'});
 assert.equal(row.payload.k,'grammar');assert.equal(row.payload.wrong,'بيت');assert.equal(row.payload.flipped,true);
 assert.ok(!('rule' in row.payload)&&!('bucket' in row.payload));
});

test('PG-50 key 4 = a not-slip row on the ✗ chip with one of the four reasons; no ✗ on the line = a trace',()=>{
 assert.deepEqual(R.REASONS4.map(r=>r[0]),['not-correcting','fixed-first','both-fine','asking']);
 const T=R.slipTargets([{id:'c1',k:'vocab',s:'wrong',src:'FA-1',said:'بيت',signal:'recast'},{id:'c2',k:'vocab',s:'correct'}]);
 assert.equal(T.length,1);assert.equal(T[0].src,'FA-1');
 const s=R.create({pick:pick(),date:'2026-10-08',now:1e12});
 const [row]=R.answer(s,{key:4,reason:'fixed-first',chip:T[0]},env());
 assert.equal(row.kind,'not-slip');assert.equal(row.target.src,'FA-1');assert.equal(row.payload.reason,'fixed-first');
 const [tr]=R.answer(s,{key:4},env());
 assert.equal(tr.kind,'rule-answer');assert.equal(tr.payload.no_chip,true);
});

test('PG-50 blind block = the first 50 lines SHOWN (unsure first), rows there carry blind:true; after that chips show',()=>{
 const p=pick(),s=R.create({pick:p,date:'2026-10-08',now:1e12});
 for(let k=0;k<50;k++){const [r]=R.answer(s,{key:1},env());assert.equal(r.payload.blind,true,'line '+k);}
 const [r51]=R.answer(s,{key:1},env());
 assert.equal(r51.payload.blind,false);assert.equal(R.isBlind({order:51}),false);assert.equal(R.isBlind({order:50}),true);
});

test('PG-50 order: unsure first then confident; unsure only stops at an end card offering the confident lines',()=>{
 const s=R.create({pick:pick(),date:'2026-10-08',now:1e12});
 assert.equal(s.items.length,55);assert.equal(R.progress(s).text,'1 of 55');
 for(let k=0;k<55;k++)R.answer(s,{key:1},env());
 assert.ok(R.atEnd(s));
 const e=R.endCard(s);assert.equal(e.kind,'unsure-done');assert.equal(e.m,5);
 assert.match(e.text,/^Unsure lines done \(55\)\. For the grade book: 5 more, about \d+ min$/);
 R.setUnsureOnly(s,false,1e12);
 assert.equal(s.items.length,60);assert.equal(R.current(s).order,56);  // continues at the first confident line
 const all=R.queue(pick(),{unsureOnly:false}).map(x=>x.order);assert.deepEqual(all,all.slice().sort((a,b)=>a-b));
});

test('PG-50 u = an undo row (AM-17 style, never a delete) and the line shows again',()=>{
 const s=R.create({pick:pick(),date:'2026-10-08',now:1e12});
 const [a]=R.answer(s,{key:3,said:'بيت',k:'vocab'},env());
 assert.equal(s.pos,1);
 const [u]=R.undoLast(s,{now:1e12+99,uuid:()=>'u1'});
 assert.equal(u.kind,'undo');assert.equal(u.undoes,a.id);assert.equal(u.turn_t,a.turn_t);
 assert.equal(s.pos,0);assert.equal(s.reviewed,0);assert.ok(!s.answered[R.keyOf(10)]);
 assert.deepEqual(R.undoLast(s,{now:1}),[]);
 // the page's effective set: the undone row is gone
 const C=require('../docs/js/transcript-corrections.js');
 assert.deepEqual(C.effective([Object.assign({},a,{ts:'2026-10-11T10:00:00Z'}),Object.assign({},u,{ts:'2026-10-11T10:01:00Z'})]),[]);
});

test('PG-50 secs: seconds on each line go with its row and add up for the session',()=>{
 const s=R.create({pick:pick(),date:'2026-10-08',now:1000});
 const [a]=R.answer(s,{key:1},{now:6000,uuid:()=>'a',line:'x'});
 const [b]=R.answer(s,{key:1},{now:18500,uuid:()=>'b',line:'x'});
 assert.equal(a.payload.secs,5);assert.equal(b.payload.secs,12.5);assert.equal(b.payload.session_secs,18);
 const [c]=R.answer(s,{key:1},{now:18500+3600e3,uuid:()=>'c',line:'x'});
 assert.equal(c.payload.secs,600);   // a line left open (a break) is capped
});

test('PG-50 re-listen: 15 answered lines picked by the date (stable), his earlier answer hidden, only inert rows',()=>{
 const p=pick(),rows=p.lines.slice(0,40).map((x,k)=>({id:'r'+k,kind:'rule-answer',proposal:'review:fast',turn_t:x.t,payload:{review_mode:'fast',verdict:'right',key:1}}));
 const ans=R.answeredFrom(rows,p);assert.equal(Object.keys(ans).length,40);
 const a=R.relistenPick(p,ans).map(x=>x.t),b=R.relistenPick(pick(),ans).map(x=>x.t);
 assert.equal(a.length,15);assert.deepEqual(a,b);assert.deepEqual(a,a.slice().sort((x,y)=>x-y));
 assert.notDeepEqual(R.relistenPick(Object.assign(pick(),{date:'2026-10-09'}),ans).map(x=>x.t),a);
 const s=R.create({pick:p,date:'2026-10-08',rows,now:1e12});
 assert.equal(s.pos,40);           // resumes at the first unanswered line
 R.startRelisten(s,1e12);assert.equal(s.items.length,15);assert.equal(s.pos,0);
 const [r]=R.answer(s,{key:3,said:'بيت',k:'vocab'},env());
 assert.equal(r.kind,'rule-answer');assert.equal(r.proposal,'review:relisten');assert.equal(r.payload.relisten,true);
 assert.equal(r.payload.would.kind,'add');assert.equal(r.payload.earlier.key,1);assert.equal(r.payload.same,false);
 // relisten rows never count as fast answers again
 assert.equal(Object.keys(R.answeredFrom(rows.concat([r]),p)).length,40);
});

test('PG-50 the page wires it: lessons.html loads review-mode.js, the transcript has the Review button; PG-33 names',()=>{
 const html=fs.readFileSync(path.join(ROOT,'docs','lessons.html'),'utf8');
 assert.match(html,/<script src="js\/review-mode\.js[^"]*" defer><\/script>/);
 assert.match(fs.readFileSync(path.join(ROOT,'docs','js','lessons-page.js'),'utf8'),/window\.AneesReview\.button\(x,/);
 assert.match(fs.readFileSync(path.join(ROOT,'docs','css','lessons.css'),'utf8'),/body\.rv-on \.pn-bar/);   // PG-31 bar hidden in review
 const js=fs.readFileSync(path.join(ROOT,'docs','js','review-mode.js'),'utf8');
 const strings=(js.split('/* ---------- the page (DOM)')[1]||'').match(/'[^'\n]*'/g)||[];
 const bad=strings.filter(s=>/\b(Medi|Amal)\b/.test(s)&&s!=="'Medi'");   // 'Medi' alone = the internal speaker id
 assert.deepEqual(bad,[],'a visible string names Medi or Amal');
 assert.ok(/enqueueRow: enqueue/.test(fs.readFileSync(path.join(ROOT,'docs','js','transcript-corrections.js'),'utf8')));
});

test('PG-50 key 2 never offers an English filler as the word the engine wrote on an Arabic line',()=>{
 assert.deepEqual(R.targets('keefak','Uh, okay كيفك اليوم'),['كيفك','اليوم']);
 assert.equal(R.targets('keefak','Uh, okay كيفك اليوم',w=>({'كيفك':'keefak','اليوم':'el-yom'})[w])[0],'كيفك');
});
