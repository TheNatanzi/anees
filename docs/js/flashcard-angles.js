/* Progress & Stats › Flashcards tab › New angles (Medi 2026-09-27: "all of these").
   Nine panels A–I from the flashcard stats mockup, drawn under the Review queue.
   Same answer log as the tab (card_results + this device's unsynced rows, the
   fullLog() merge, handed over in d.log) replayed through AneesFSRS, keeping
   the card state BEFORE each answer so every answer knows its gap, predicted
   recall and kind. Nothing is hardcoded: missing data renders "—" with a reason.
   Called by flashcard-progress.js at the end of render(), so it redraws after a grade or undo. */
(function(){
'use strict';
const F=window.AneesFSRS;
const DAY=86400000,MIN=60000,SESSION_GAP=30*MIN,COLD_DAYS=7,WINDOW_DAYS=28,CULL=4,CAP_NEW=8,CAP_REVIEWS=40,SLOW_FLIP=6000;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const pc=(r,t)=>t?Math.round(r/t*100):null;
const P=v=>v===null||v===undefined?'—':v+'%';
const f1=v=>v===null||v===undefined||Number.isNaN(v)?'—':(Math.round(v*10)/10).toFixed(1);
const secs=v=>v===null||v===undefined?'—':(v/1000).toFixed(1)+' s';
const median=a=>{if(!a.length)return null;const s=a.slice().sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;};
const plural=(k,one,many)=>`${n(k)} ${k===1?one:many||one+'s'}`;
const pad=x=>String(x).padStart(2,'0');
const ms=t=>t instanceof Date?t.getTime():typeof t==='string'?Date.parse(t):Number(t);
const dayStart=t=>{const d=new Date(ms(t));return new Date(d.getFullYear(),d.getMonth(),d.getDate()).getTime();};
const addDays=(t,k)=>{const d=new Date(dayStart(t));d.setDate(d.getDate()+k);return d.getTime();};
const iso=t=>{const d=new Date(ms(t));return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;};
const dm=t=>new Date(ms(t)).toLocaleDateString(undefined,{day:'numeric',month:'short'});
const clock=t=>{const d=new Date(ms(t));return pad(d.getHours())+':'+pad(d.getMinutes());};
const when=t=>new Date(ms(t)).toLocaleDateString(undefined,{weekday:'short',day:'numeric',month:'short'})+' '+clock(t);
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
const isRight=r=>{const g=String(r.grade??r.result).toLowerCase();return g==='got'||g==='good';};
const num=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)&&x>0?x:null;};

/* ---------- replay (same filter and order as AneesFlashcardStats.history) ---------- */
function clean(log){
 const seen=new Set(),out=[];
 for(const r of log||[]){
  if(!r||r.kind==='flag'||r.kind==='undo'||r.undone||r.undone_at||!(r.word_key||r.key)||!Number.isFinite(ms(r.ts)))continue;
  if(r.id!=null){if(seen.has(r.id))continue;seen.add(r.id);}
  try{F.rating(r.grade??r.result);}catch(e){continue;}
  out.push(r);
 }
 return out.sort((a,b)=>ms(a.ts)-ms(b.ts));
}
function replay(log,retention){
 const cards=new Map(),answers=[],opts={desiredRetention:retention};
 for(const r of clean(log)){
  const key=r.word_key||r.key,before=cards.get(key)||F.newCard(key),t=ms(r.ts);
  cards.set(key,F.schedule(before,r.grade??r.result,t,opts));
  answers.push({key,t,right:isRight(r),kind:!before.reps?'new':before.state==='review'?'review':'learning',
   gap:before.last_review===null||before.last_review===undefined?null:(t-ms(before.last_review))/DAY,
   R:before.reps?F.retrievability(before,t):null,mode:r.mode||null,flip:num(r.flip_ms),ans:num(r.answer_ms)});
 }
 return {cards,answers};
}
// A new session starts after 30 minutes without an answer.
function sessionsOf(answers){
 const out=[];
 for(const a of answers){const s=out[out.length-1];if(s&&a.t-s.end<=SESSION_GAP){s.end=a.t;s.a.push(a);}else out.push({start:a.t,end:a.t,a:[a]});}
 for(const s of out){
  const seen=new Set();s.n=s.a.length;s.right=s.a.filter(x=>x.right).length;s.min=(s.end-s.start)/MIN;s.parts={new:[0,0],back:[0,0],old:[0,0]};s.oldGaps=[];
  for(const x of s.a){const p=x.kind==='new'?'new':seen.has(x.key)?'back':'old';s.parts[p][0]++;if(x.right)s.parts[p][1]++;if(p==='old')s.oldGaps.push(x.gap);seen.add(x.key);}
  s.words=seen.size;
 }
 return out;
}

/* ---------- numbers ---------- */
function compute(d){
 const now=ms(d.now),{cards,answers}=replay(d.log,d.p.retention),byKey=d.byKey;
 const ses=sessionsOf(answers),today=dayStart(now);
 const topic=k=>(byKey.get(k)||{}).topic||null;
 const topTopic=keys=>{const c=new Map();for(const k of keys){const t=topic(k);if(t)c.set(t,(c.get(t)||0)+1);}let best=null;for(const [t,v] of c)if(!best||v>best.v)best={t,v};return best&&best.v/keys.length>=.5?best.t:null;};

 // A: first answer of the day, 7+ days after the last one; trailing 28 days; latest per word
 const cold=[],seenDay=new Set();
 for(const a of answers){const dk=a.key+'|'+iso(a.t);if(seenDay.has(dk))continue;seenDay.add(dk);if(a.gap!==null&&a.gap>=COLD_DAYS)cold.push(a);}
 const coldWin=new Map();for(const a of cold)if(a.t>=now-WINDOW_DAYS*DAY)coldWin.set(a.key,a);
 const A={all:cold,list:[...coldWin.values()].sort((x,y)=>x.t-y.t)};
 A.right=A.list.filter(a=>a.right).length;A.expected=A.list.reduce((s,a)=>s+(a.R||0),0);A.gap=median(A.list.map(a=>a.gap));A.days=[...new Set(A.list.map(a=>iso(a.t)))];

 // B: flip time, right vs wrong
 const fl=answers.filter(a=>a.flip!==null),flR=fl.filter(a=>a.right),flW=fl.filter(a=>!a.right);
 const bins=Array.from({length:16},(_,i)=>({i,got:0,miss:0}));for(const a of fl)bins[Math.min(15,Math.floor(a.flip/1000))][a.right?'got':'miss']++;
 const B={n:fl.length,untimed:answers.length-fl.length,medR:median(flR.map(a=>a.flip)),medW:median(flW.map(a=>a.flip)),nR:flR.length,nW:flW.length,bins,slowRight:flR.filter(a=>a.flip>=SLOW_FLIP).length};

 // C: sessions on the clock + % right per local hour with first-sight dot
 const hours=new Map();
 for(const a of answers){const h=new Date(a.t).getHours();if(!hours.has(h))hours.set(h,{h,n:0,right:0,nn:0,nr:0,newKeys:[]});const x=hours.get(h);x.n++;if(a.right)x.right++;if(a.kind==='new'){x.nn++;if(a.right)x.nr++;x.newKeys.push(a.key);}}
 const band=h=>h<6?'night':h<12?'morning':h<18?'afternoon':'evening',bands={night:0,morning:0,afternoon:0,evening:0};
 for(const s of ses)bands[band(new Date(s.start).getHours())]++;
 const C={ses,hours:[...hours.values()].sort((x,y)=>x.h-y.h),bands,topTopic};

 // D: new cards per study day vs the caps, and the backlog they leave
 const firstDay=new Map();for(const a of answers)if(a.kind==='new'){const k=iso(a.t);firstDay.set(k,(firstDay.get(k)||0)+1);}
 let dueToday=0,dueTomorrow=0,overdue=0;const later=new Map();
 for(const c of cards.values()){if(!c.reps)continue;const due=ms(c.due);if(due<today)overdue++;if(due<addDays(today,1))dueToday++;else if(due<addDays(today,2))dueTomorrow++;else if(due<addDays(today,31)){const k=iso(due);later.set(k,(later.get(k)||0)+1);}}
 const nextBig=[...later].sort((x,y)=>x[0]<y[0]?-1:1)[0]||null;
 const D={days:[...firstDay].map(([date,v])=>({date,v})).sort((x,y)=>x.date<y.date?-1:1),dueToday,dueTomorrow,overdue,nextBig};

 // E: the ladder
 const Rnow=c=>F.retrievability(c,Math.max(now,ms(c.last_review)));
 const rungs=[
  {id:'mature',label:`${F.DEFAULTS.matureDays}+ day interval · Mature`,cls:'good',test:c=>c.state==='review'&&c.interval>=F.DEFAULTS.matureDays},
  {id:'r7',label:'7–20 day interval',cls:'ok',test:c=>c.state==='review'&&c.interval>=7&&c.interval<F.DEFAULTS.matureDays},
  {id:'r3',label:'3–6 day interval',cls:'ok',test:c=>c.state==='review'&&c.interval>=3&&c.interval<7},
  {id:'r1',label:'1–2 day interval',cls:'ok',test:c=>c.state==='review'&&c.interval<3},
  {id:'learning',label:'Learning step unfinished',cls:'warn',test:c=>c.state==='learning'},
  {id:'relearning',label:'Relearning after a lapse',cls:'bad',test:c=>c.state==='relearning'}
 ].map(r=>{const list=[...cards.values()].filter(c=>c.reps&&r.test(c));return {...r,count:list.length,R:list.length?list.reduce((s,c)=>s+Rnow(c),0)/list.length*100:null};});
 const missCount=new Map(),answerCount=new Map();for(const a of answers){answerCount.set(a.key,(answerCount.get(a.key)||0)+1);if(!a.right)missCount.set(a.key,(missCount.get(a.key)||0)+1);}
 const restarted=[...cards.values()].filter(c=>missCount.get(c.id)&&c.stability!==null&&c.stability<1);
 const E={rungs,total:[...cards.values()].filter(c=>c.reps).length,unseen:[...byKey.keys()].filter(k=>!cards.has(k)).length,
  restarted:{count:restarted.length,R:restarted.length?restarted.reduce((s,c)=>s+Rnow(c),0)/restarted.length*100:null},medSession:median(ses.map(s=>s.min))};

 // F: chronic misses vs the 4-miss cull line
 const Fm={list:[...missCount].map(([key,m])=>{const c=cards.get(key);return {key,m,answers:answerCount.get(key)||0,difficulty:c?c.difficulty:null,lapses:c?c.lapses:0};}).sort((x,y)=>y.m-x.m||y.answers-x.answers||(y.difficulty||0)-(x.difficulty||0)),leechLapses:F.DEFAULTS.leechLapses};

 // G: retention by gap since the last answer
 const GB=[['first sight',a=>a.gap===null],['same day',a=>a.gap!==null&&a.gap<1],['1–2 d',a=>a.gap>=1&&a.gap<3],['3–6 d',a=>a.gap>=3&&a.gap<7],['7–13 d',a=>a.gap>=7&&a.gap<14],['14 d+',a=>a.gap>=14]];
 const G={bins:GB.map(([label,test])=>{const l=answers.filter(a=>test(a));return {label,n:l.length,right:l.filter(a=>a.right).length};})};
 const spaced=answers.filter(a=>a.gap!==null&&a.gap>=1);G.spaced={n:spaced.length,right:spaced.filter(a=>a.right).length};

 // H: recognition (Arabic first) vs production (English first)
 const mode=m=>{const l=answers.filter(a=>a.mode===m);return {n:l.length,right:l.filter(a=>a.right).length,flip:median(l.filter(a=>a.flip!==null).map(a=>a.flip)),dates:[...new Set(l.map(a=>iso(a.t)))]};};
 const firstBy=new Map();for(const a of answers){if(a.mode!=='ar_first'&&a.mode!=='en_first')continue;if(!firstBy.has(a.key))firstBy.set(a.key,{});const o=firstBy.get(a.key);if(!(a.mode in o))o[a.mode]=a.right;}
 const both=[...firstBy.values()].filter(o=>'ar_first' in o&&'en_first' in o);
 const H={ar:mode('ar_first'),en:mode('en_first'),other:answers.filter(a=>a.mode!=='ar_first'&&a.mode!=='en_first').length,both:both.length,bothRight:both.filter(o=>o.ar_first&&o.en_first).length,arOnly:both.filter(o=>o.ar_first&&!o.en_first).length,enOnly:both.filter(o=>o.en_first&&!o.ar_first).length};

 // I: what is inside a session score (sessions of 10+ answers, latest four)
 const I={ses:ses.filter(s=>s.n>=10).slice(-4)};
 I.pool={all:[0,0],new:[0,0],back:[0,0],old:[0,0]};for(const s of I.ses){I.pool.all[0]+=s.n;I.pool.all[1]+=s.right;for(const k of ['new','back','old']){I.pool[k][0]+=s.parts[k][0];I.pool[k][1]+=s.parts[k][1];}}
 I.oldGap=median(I.ses.flatMap(s=>s.oldGaps));

 return {now,answers,cards,A,B,C,D,E,F:Fm,G,H,I};
}

/* ---------- drawing ---------- */
const W=520;
const frame=(inner,label,h,w=W)=>`<svg class="vp-chart fa-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${inner}</svg>`;
const empty=t=>`<div class="vp-empty">— ${esc(t)}</div>`;
const panel=(key,title,sub,body,{wide=false,why='',note=''}={})=>`<section class="vp-panel fa-panel ${wide?'fp-wide':''}" aria-labelledby="fa-h-${key}"><div class="vp-panelhead"><div><span class="fa-key">${key.toUpperCase()}</span><h2 id="fa-h-${key}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div></div>${body}${why||note?`<div class="fa-foot">${why?`<span class="fa-why">${why}</span>`:''}${note?`<span>${note}</span>`:''}</div>`:''}</section>`;
function wordLabel(k,byKey){
 const w=byKey.get(k);
 if(!w)return `<span class="fa-w"><b>${esc(/^q:/.test(k)?'Quizlet card '+k.split(':').slice(1).join(' #'):k)}</b></span>`;
 return `<a class="fa-w" href="word-bank.html?word=${encodeURIComponent(k)}"><b>${esc(w.arabizi||'')}</b>${w.arabic?`<span lang="ar" dir="rtl">${esc(w.arabic)}</span>`:''}${w.english?`<small>${esc(w.english)}</small>`:''}</a>`;
}
const row=(label,width,cls,right,title='')=>`<div class="fa-row"${title?` title="${esc(title)}"`:''}><span class="fa-id">${label}</span><span class="fa-track"><i class="fa-fill-${cls}" style="width:${Math.max(width>0?2:0,Math.min(100,width)).toFixed(1)}%"></i></span><span class="fa-n">${right}</span></div>`;
const big=(v,sub)=>`<div class="fa-big"><b>${v}</b><small>${sub}</small></div>`;
const isNice=v=>{const p=Math.pow(10,Math.floor(Math.log10(v))),r=Math.round(v/p*100)/100;return [1,2,2.5,5].includes(r);};
const niceSteps=top=>[4,5,3,2].find(k=>isNice(top/k))||4;
const roomy=v=>{const top=niceMax(v);for(const t of [top*.6,top*.7,top*.8])if(t>=v&&isNice(t/niceSteps(t)))return t;return top;};
function yGrid(y,top,L,R,fmt,steps=niceSteps(top)){let s='';for(let i=0;i<=steps;i++){const v=top*i/steps;s+=`<line class="vp-gridline" x1="${L}" x2="${W-R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text x="${L-6}" y="${(y(v)+3.5).toFixed(1)}" text-anchor="end">${fmt(v)}</text>`;}return s;}

/* A */
function panelA(x,d){
 const A=x.A;
 const sub='A word counts when its first answer of the day, at least 7 days after you last saw it, passes. Trailing 28 days. Bar = what FSRS predicted before you answered.';
 if(!A.all.length)return panel('a','Words I can say cold',sub,empty('No card has come back after a gap of 7+ days yet. The first one to do so starts this count.'));
 if(!A.list.length)return panel('a','Words I can say cold',sub,big('—',`none tested cold in the last 28 days · last cold test ${dm(A.all[A.all.length-1].t)}`)+empty('Nothing came back after 7+ days in the last four weeks.'));
 const k=A.list.length,shown=A.list.slice(-10);
 const on=A.days.length===1?`on ${dm(A.list[0].t)}`:`in the last 28 days`;
 const rows=shown.map(a=>{const p=Math.round((a.R||0)*100);return row(wordLabel(a.key,d.byKey),p,'sage',`<span class="${a.right?'fa-ok':'fa-bad'}">${a.right?'✓ said cold':'✗ missed'}</span> · ${p}% predicted`,`${dm(a.t)} · ${f1(a.gap)} days since last seen · FSRS predicted ${p}%`);}).join('');
 const diff=A.right-A.expected,verdict=diff>=.5?'The defaults underrate you so far':diff<=-.5?'The defaults overrate you so far':'Right on the prediction so far';
 return panel('a','Words I can say cold',sub,big(n(A.right),`of ${n(k)} tested cold ${on} · median gap ${f1(A.gap)} days`)+`<div class="fa-rows">${rows}</div>${k>shown.length?`<p class="ab-sub">Showing the latest 10 of ${n(k)}.</p>`:''}`,
  {why:`FSRS expected ${f1(A.expected)} of ${n(k)}. You got ${n(A.right)}. ${verdict} (n=${n(k)}).`,note:'Predicted = retrievability at answer time'});
}
/* B */
function panelB(x){
 const B=x.B,sub='Seconds you looked at the card before flipping, split by whether you then knew it. <code>flip_ms</code> is stored on every timed answer and shown nowhere else.';
 if(!B.n)return panel('b','Hesitation before the flip',sub,empty('No flip times yet: answers from the review queue on this page carry none.'));
 const h=190,L=30,R=10,T=14,Bt=30,pw=W-L-R,ph=h-T-Bt,top=niceMax(Math.max(1,...B.bins.map(b=>Math.max(b.got,b.miss)))),y=v=>T+ph-v/top*ph;
 const gap=6,slot=(pw-gap*15)/16,bw=(slot-2)/2;
 let s=yGrid(y,top,L,R,v=>n(Math.round(v)),top>=4?undefined:top);
 for(const b of B.bins){const x0=L+b.i*(slot+gap),lab=b.i===15?'15+':String(b.i),range=b.i===15?'15 s or more':`${b.i}–${b.i+1} s`;
  if(b.got)s+=`<rect class="fa-got" x="${x0.toFixed(1)}" y="${y(b.got).toFixed(1)}" width="${bw.toFixed(1)}" height="${(T+ph-y(b.got)).toFixed(1)}" rx="2"><title>${range} before the flip: knew it ${n(b.got)}</title></rect>`;
  if(b.miss)s+=`<rect class="fa-miss" x="${(x0+bw+2).toFixed(1)}" y="${y(b.miss).toFixed(1)}" width="${bw.toFixed(1)}" height="${(T+ph-y(b.miss)).toFixed(1)}" rx="2"><title>${range} before the flip: missed ${n(b.miss)}</title></rect>`;
  if(b.i%2===1||b.i===15)s+=`<text x="${(x0+slot/2).toFixed(1)}" y="${h-10}" text-anchor="middle">${lab}</text>`;}
 s+=`<text x="${W-R}" y="${T-4}" text-anchor="end">seconds before the flip →</text>`;
 return panel('b','Hesitation before the flip',sub,`<div class="fa-big"><b>${secs(B.medR)}</b><small>median when right</small><span class="fa-vs">vs</span><b>${secs(B.medW)}</b><small>when wrong${B.nW?'':' · no timed miss yet'}</small></div>`+frame(s,'Seconds before flipping, knew versus missed',h)+`<div class="fa-legend"><span><i class="fa-got"></i>knew it ${n(B.nR)}</span><span><i class="fa-miss"></i>missed ${n(B.nW)}</span></div>`,
  {why:B.slowRight?`${plural(B.slowRight,'“Know it” answer')} took 6 s or more: shaky, but FSRS files ${B.slowRight===1?'it as a clean pass':'them as clean passes'}.`:'No “Know it” answer took 6 s or more.',note:`${plural(B.n,'timed answer')}${B.untimed?` · ${n(B.untimed)} without a flip time`:''}`});
}
/* C */
function panelC(x,d){
 const C=x.C,ses=C.ses,sub='Each session is a bubble at its local start hour; size = cards, label = % right. Right: % right per hour, with first-sight accuracy (new cards only) as the dot.';
 if(!ses.length)return panel('c','Sessions on the clock',sub,empty('No answers yet.'),{wide:true});
 const h=170,L=14,R=14,cy=78,pw=W-L-R,many=ses.length>6;
 let s=`<line class="vp-axis" x1="${L}" x2="${W-R}" y1="${cy}" y2="${cy}"/>`;
 for(const hh of [0,6,12,18,24]){const xx=L+hh/24*pw;s+=`<line class="vp-axis" x1="${xx}" x2="${xx}" y1="${cy-4}" y2="${cy+4}"/><text x="${xx}" y="${h-8}" text-anchor="${hh===0?'start':hh===24?'end':'middle'}">${pad(hh%24===0&&hh?24:hh)}:00</text>`;}
 for(const q of ses){const st=new Date(q.start),hr=st.getHours()+st.getMinutes()/60,xx=L+hr/24*pw,r=Math.min(34,6+Math.sqrt(q.n)*2.2),p=pc(q.right,q.n),lab=C.topTopic(q.a.map(a=>a.key));
  s+=`<circle class="fa-bubble" cx="${xx.toFixed(1)}" cy="${cy}" r="${r.toFixed(1)}"><title>${when(q.start)}: ${plural(q.n,'answer')} on ${plural(q.words,'card')}, ${p}% right, ${f1(q.min)} min · ${q.parts.new[0]} new + ${q.parts.back[0]} back in session + ${q.parts.old[0]} older${lab?` · mostly ${esc(lab)}`:''}</title></circle>`;
  if(!many){s+=`<text class="vp-callout" x="${xx.toFixed(1)}" y="${(cy-r-8).toFixed(1)}" text-anchor="middle">${p}%</text>`;
   if(q.n<10&&xx<W-90)s+=`<text x="${(xx+r+6).toFixed(1)}" y="${cy-1}">${n(q.n)} · ${f1(q.min)} min</text><text x="${(xx+r+6).toFixed(1)}" y="${cy+11}">${esc(dm(q.start))}</text>`;
   else{const anchor=xx<60?'start':xx>W-60?'end':'middle';s+=`<text x="${xx.toFixed(1)}" y="${(cy+r+14).toFixed(1)}" text-anchor="${anchor}">${n(q.n)} · ${f1(q.min)} min</text><text x="${xx.toFixed(1)}" y="${(cy+r+26).toFixed(1)}" text-anchor="${anchor}">${esc(dm(q.start))}</text>`;}}}
 const left=frame(s,`${ses.length} study sessions by local start hour`,h);
 // % right per hour
 const hs=C.hours,L2=34,R2=10,T2=16,B2=30,ph=h-T2-B2,pw2=W-L2-R2,y=v=>T2+ph-v/100*ph,gap=hs.length>8?4:hs.length>4?14:40,bw=Math.min(90,(pw2-gap*(hs.length-1))/hs.length),x0=L2+(pw2-(bw*hs.length+gap*(hs.length-1)))/2;
 let s2=yGrid(y,100,L2,R2,v=>Math.round(v)+'%',2);
 hs.forEach((o,i)=>{const xx=x0+i*(bw+gap),p=pc(o.right,o.n),np=pc(o.nr,o.nn);
  s2+=`<rect class="fa-sage" x="${xx.toFixed(1)}" y="${y(p).toFixed(1)}" width="${bw.toFixed(1)}" height="${(T2+ph-y(p)).toFixed(1)}" rx="3"><title>${pad(o.h)}:00–${pad(o.h)}:59: ${p}% right over ${plural(o.n,'answer')}${o.nn?` · first sight ${np}% over ${plural(o.nn,'new card')}`:' · no first sight'}</title></rect>`;
  if(hs.length<=8)s2+=`<text class="vp-callout" x="${(xx+bw/2).toFixed(1)}" y="${(y(p)-6).toFixed(1)}" text-anchor="middle">${p}%</text>`;
  if(o.nn)s2+=`<circle class="fa-dot" cx="${(xx+bw/2).toFixed(1)}" cy="${y(np).toFixed(1)}" r="5"><title>First sight of a new card at ${pad(o.h)}:00: ${np}% (${plural(o.nn,'card')})</title></circle>`;
  s2+=`<text x="${(xx+bw/2).toFixed(1)}" y="${h-10}" text-anchor="middle">${pad(o.h)}${hs.length<=5?`:00 · n=${n(o.n)}`:''}</text>`;});
 const right=frame(s2,'Percent right by local hour of day',h);
 // honest note
 const ps=hs.map(o=>pc(o.right,o.n)),spread=Math.max(...ps)-Math.min(...ps);
 let why=hs.length<2?`All answers so far fall in one hour (${pad(hs[0].h)}:00), so the hour cannot be compared yet.`:
  spread<=10?`Flat so far: ${ps.join(' / ')}% by hour.`:`Spread so far: ${Math.min(...ps)}% to ${Math.max(...ps)}% by hour.`;
 const fs=hs.filter(o=>o.nn>=10);
 if(fs.length>=2){const lo=fs.reduce((a,b)=>pc(b.nr,b.nn)<pc(a.nr,a.nn)?b:a),hi=fs.reduce((a,b)=>pc(b.nr,b.nn)>pc(a.nr,a.nn)?b:a);
  if(lo!==hi){const tl=C.topTopic(lo.newKeys),th=C.topTopic(hi.newKeys);why+=` First-sight ${pc(lo.nr,lo.nn)}% at ${pad(lo.h)}:00 vs ${pc(hi.nr,hi.nn)}% at ${pad(hi.h)}:00`;
   why+=tl&&th&&tl!==th?`, but ${pad(lo.h)}:00 drilled mostly “${esc(tl)}” words and ${pad(hi.h)}:00 mostly “${esc(th)}”, so the words differ as well as the hour.`:tl&&th?`, on the same kind of words (“${esc(tl)}”).`:', on different word sets, so the words differ as well as the hour.';}}
 const b=C.bands,need=Object.values(b).filter(v=>v>=5).length;
 why+=need>=2?' Two time bands now have 5+ sessions each: the comparison starts to mean something.':` A verdict needs about 5 sessions per time band (night ${b.night} · morning ${b.morning} · afternoon ${b.afternoon} · evening ${b.evening}).`;
 let tz='';try{tz=Intl.DateTimeFormat().resolvedOptions().timeZone||'';}catch(e){}
 return panel('c','Sessions on the clock',sub,`<div class="fa-two"><div><div class="fa-sub">${plural(ses.length,'session')} · 30 min without an answer starts a new one</div>${left}</div><div><div class="fa-sub">% right by local hour · dot = first sight only</div>${right}</div></div>`,{wide:true,why,note:`Hours in local time${tz?` (${esc(tz)})`:''}`});
}
/* D */
function panelD(x){
 const D=x.D,sub=`Cards seen for the first time each study day. Lines = the ${CAP_NEW}-per-lesson cap from the habit design (wiki 06) and the ${F.DEFAULTS.newPerDay}-per-day FSRS default. Topic drills bypass both.`;
 if(!D.days.length)return panel('d','New cards per day vs the cap',sub,empty('No card has been seen yet.'));
 const days=D.days.slice(-14),last=D.days[D.days.length-1],times=last.v/CAP_NEW;
 const h=190,L=30,R=10,T=14,B=30,pw=W-L-R,ph=h-T-B,top=roomy(Math.max(F.DEFAULTS.newPerDay,...days.map(o=>o.v))*1.08),y=v=>T+ph-v/top*ph;
 const room=pw-140,gap=days.length>6?8:40,bw=Math.min(110,(room-gap*(days.length-1))/days.length),x0=L+(room-(bw*days.length+gap*(days.length-1)))/2;
 let s=yGrid(y,top,L,R,v=>n(Math.round(v)));
 days.forEach((o,i)=>{const xx=x0+i*(bw+gap);s+=`<rect class="${o.v>CAP_NEW?'fa-miss':'fa-sage'}" x="${xx.toFixed(1)}" y="${y(o.v).toFixed(1)}" width="${bw.toFixed(1)}" height="${(T+ph-y(o.v)).toFixed(1)}" rx="3"><title>${o.date}: ${plural(o.v,'card')} seen for the first time</title></rect><text class="vp-callout" x="${(xx+bw/2).toFixed(1)}" y="${(y(o.v)-6).toFixed(1)}" text-anchor="middle">${n(o.v)}</text>${days.length<=8||i%2===days.length%2?`<text x="${(xx+bw/2).toFixed(1)}" y="${h-10}" text-anchor="middle">${esc(dm(o.date+'T12:00'))}</text>`:''}`;});
 s+=`<line class="fa-cap" x1="${L}" x2="${W-R}" y1="${y(CAP_NEW).toFixed(1)}" y2="${y(CAP_NEW).toFixed(1)}"/><text class="fa-cap-label" x="${W-R}" y="${(y(CAP_NEW)-4).toFixed(1)}" text-anchor="end">cap ${CAP_NEW} per lesson (wiki 06)</text>`;
 s+=`<line class="fa-def" x1="${L}" x2="${W-R}" y1="${y(F.DEFAULTS.newPerDay).toFixed(1)}" y2="${y(F.DEFAULTS.newPerDay).toFixed(1)}"/><text x="${W-R}" y="${(y(F.DEFAULTS.newPerDay)-4).toFixed(1)}" text-anchor="end">FSRS default ${F.DEFAULTS.newPerDay} per day</text>`;
 const over=D.dueToday>CAP_REVIEWS;
 const why=`${plural(D.dueToday,'card')} due today${D.overdue?` (${n(D.overdue)} overdue)`:''} against a ${CAP_REVIEWS}-a-day review cap.${over?' This is the backlog spiral the post-mortems warn about.':' Within the cap.'}`;
 return panel('d','New cards per day vs the cap',sub,big(n(last.v),`new cards on ${dm(last.date+'T12:00')} · ${times>1?`${f1(times).replace(/\.0$/,'')}× the cap`:'within the cap'}`)+frame(s,'New cards per study day against the caps',h),
  {why,note:`Backlog: ${n(D.dueToday)} due today, ${n(D.dueTomorrow)} tomorrow${D.nextBig?`, ${n(D.nextBig[1])} on ${dm(D.nextBig[0]+'T12:00')}`:''}`});
}
/* E */
function panelE(x){
 const E=x.E,sub=`Where each of the ${n(E.total)} answered cards sits, as rungs a tutor can read. Right-hand number = average chance you still recall it right now.`;
 if(!E.total)return panel('e','The ladder',sub,empty('No card answered yet.'));
 const max=Math.max(1,...E.rungs.map(r=>r.count));
 const rows=E.rungs.map(r=>row(`<span class="fa-rung${r.count?'':' fa-dim'}">${esc(r.label)}</span>`,r.count/max*100,r.cls,`<b>${n(r.count)}</b> ${r.count===1?'card':'cards'}${r.count?` · ${Math.round(r.R)}% recall now`:''}`)).join('');
 const rs=E.restarted,learn=E.rungs.find(r=>r.id==='learning').count;
 const restartedRow=`<div class="fa-rows fa-split">${row('<span class="fa-rung" title="Missed at least once and FSRS stability under a day">Missed, restarted</span>',rs.count/max*100,'bad',`<b>${n(rs.count)}</b> ${rs.count===1?'card':'cards'}${rs.count?` · ${Math.round(rs.R)}% recall now`:''}`)}</div><p class="ab-sub">Top rungs = every answered card by FSRS state. Bottom row = cards missed at least once whose stability is now under a day, drawn from the rungs above.</p>`;
 const why=learn?`${plural(learn,'card')} ${learn===1?'is':'are'} still on a learning step${E.medSession!==null&&E.medSession<10?`: the 10-minute second step is longer than your ${f1(E.medSession)}-minute median session`:': they left the session before the 10-minute step came round'}.`:'No card is stuck on a learning step.';
 return panel('e','The ladder',sub,`<div class="fa-rows">${rows}</div>${restartedRow}`,{why,note:`${n(E.unseen)} words never seen, not drawn`});
}
/* F */
function panelF(x,d){
 const L=x.F.list,sub=`Misses per card, all time. The tab’s leech counter needs ${x.F.leechLapses} lapses and a lapse only counts once a card is in review, so early misses score zero there.`;
 if(!L.length)return panel('f','Chronic misses (leech watch)',sub,empty('No card missed yet.'));
 const top=L.filter(o=>o.m>=2).concat(L.filter(o=>o.m<2)).slice(0,8),rest=L.slice(top.length);
 const rows=top.map(o=>row(wordLabel(o.key,d.byKey),o.m/CULL*100,o.m>=3?'bad':o.m===2?'warn':'sage',`${n(o.m)} of ${n(o.answers)} · difficulty ${f1(o.difficulty)}`,`missed ${o.m} of ${o.answers} answers · FSRS difficulty ${f1(o.difficulty)} of 10 · lapses ${o.lapses}`)).join('');
 const restNames=rest.map(o=>{const w=d.byKey.get(o.key);return w?w.arabizi:o.key;});
 const worst=L[0],ww=d.byKey.get(worst.key),name=esc(ww?ww.arabizi:worst.key);
 const why=worst.m>=CULL?`${name} has reached the “failed ${CULL}×, cull it” line (${n(worst.m)} misses, difficulty ${f1(worst.difficulty)} / 10).`:worst.m===CULL-1?`${name} is one miss from the “failed ${CULL}×, cull it” rule and FSRS already rates it ${f1(worst.difficulty)} / 10 difficulty.`:`No card is near the ${CULL}-miss cull line yet; the worst has ${n(worst.m)}.`;
 return panel('f','Chronic misses (leech watch)',sub,`<div class="fa-rows">${rows}</div><p class="ab-sub">${rest.length?`Also missed: ${esc(restNames.slice(0,12).join(', '))}${rest.length>12?` and ${n(rest.length-12)} more`:''}. `:''}Bar = misses against the ${CULL}-miss cull line.</p>`,
  {why,note:`${plural(L.length,'card')} missed at least once`});
}
/* G */
function panelG(x){
 const G=x.G,sub='% right grouped by how long since you last saw the card. The tab’s retention table only counts cards in FSRS “review” state.';
 if(!x.answers.length)return panel('g','Retention by gap',sub,empty('No answers yet.'));
 const h=190,L=34,R=10,T=16,B=30,pw=W-L-R,ph=h-T-B,y=v=>T+ph-v/100*ph,gap=12,bw=(pw-gap*5)/6;
 let s=yGrid(y,100,L,R,v=>Math.round(v)+'%',2);
 G.bins.forEach((o,i)=>{const xx=L+i*(bw+gap),cx=(xx+bw/2).toFixed(1);
  if(o.n){const p=pc(o.right,o.n);s+=`<rect class="${i===0?'fa-accent':'fa-sage'}" x="${xx.toFixed(1)}" y="${y(p).toFixed(1)}" width="${bw.toFixed(1)}" height="${(T+ph-y(p)).toFixed(1)}" rx="3"><title>${o.label}: ${p}% right, ${n(o.right)} of ${n(o.n)}</title></rect><text class="vp-callout" x="${cx}" y="${(y(p)-6).toFixed(1)}" text-anchor="middle">${p}%</text><text x="${cx}" y="${h-10}" text-anchor="middle">${o.label} · ${n(o.n)}</text>`;}
  else s+=`<rect class="fa-hollow" x="${xx.toFixed(1)}" y="${(T+ph*.5).toFixed(1)}" width="${bw.toFixed(1)}" height="${(ph*.5).toFixed(1)}" rx="3"><title>${o.label}: no answers yet</title></rect><text x="${cx}" y="${(T+ph*.75+4).toFixed(1)}" text-anchor="middle">—</text><text x="${cx}" y="${h-10}" text-anchor="middle">${o.label}</text>`;});
 const sp=G.spaced;
 return panel('g','Retention by gap',sub,frame(s,'Percent right by gap since last answer',h),
  {why:sp.n?`After a gap of a day or more: ${pc(sp.right,sp.n)}% right (${n(sp.right)} of ${n(sp.n)}). This answers “am I retaining?” before the first 21-day interval.`:'No card has come back after a day or more yet: every answer so far is first sight or same day.',note:'Hollow = no answers in that gap yet'});
}
/* H */
function panelH(x){
 const H=x.H,tot=H.ar.n+H.en.n,sub='Arabic first = recognise it. English first = produce it, the direction closest to speaking. <code>mode</code> is stored on every answer.';
 if(!tot)return panel('h','Recognition vs production',sub,empty('No answer with a card direction yet.'));
 const one=(label,m)=>`<div><div class="fa-sub">${label}</div>${big(P(pc(m.right,m.n)),m.n?`${n(m.right)} of ${n(m.n)} · flip ${secs(m.flip)}`:'no answers this way yet')}</div>`;
 const seg=(m,cls,label)=>m.n?`<span class="${cls}" style="flex:0 0 calc(${(m.n/tot*100).toFixed(2)}% - ${H.ar.n&&H.en.n?1:0}px)" title="${esc(`${label}: ${m.n} answers (${pc(m.n,tot)}%), ${m.right} right`)}"><em>${esc(label)} · ${pc(m.n,tot)}%</em></span>`:'';
 const strip=`<div class="fa-sbar fa-strip" role="img" aria-label="${esc(`Arabic first ${H.ar.n} answers, English first ${H.en.n}`)}">${seg(H.ar,'fa-seq3','Arabic first')}${seg(H.en,'fa-accent','English first')}</div>`;
 const share=pc(H.en.n,tot);
 const why=H.both?`${H.both===1?'Only 1 word was':`${share<50?'Only ':''}${n(H.both)} words were`} tested both ways (${n(H.bothRight)} of ${n(H.both)} right both ways${H.arOnly?`, ${n(H.arOnly)} recognised but not produced`:''}${H.enOnly?`, ${n(H.enOnly)} produced but not recognised`:''}).${share<50?' Worth a toggle so the English-first share grows.':''}`:'No word has been tested in both directions yet.';
 return panel('h','Recognition vs production',sub,`<div class="fa-two fa-two-tight">${one('Arabic shown first',H.ar)}${one('English shown first',H.en)}</div>`+strip+`<p class="ab-sub">Production is the direction that matches speaking; it is ${share<25?'under a quarter':share<50?'under half':'at least half'} of the log (${share}%).</p>`,
  {why,note:H.en.dates.length?`English-first answers on ${H.en.dates.slice(-3).map(t=>dm(t+'T12:00')).join(', ')}${H.other?` · ${n(H.other)} with no direction`:''}`:''});
}
/* I */
function panelI(x){
 const I=x.I,sub='Recent sessions of 10+ answers, split into first sight of a new card, the same card coming back later in the session, and cards seen in an earlier session.';
 if(!I.ses.length)return panel('i','What is inside a session score',sub,empty('Appears after a session of 10 or more answers.'),{wide:true});
 const max=Math.max(...I.ses.map(s=>s.n));
 const segs=[['new','first sight','fa-accent'],['back','back within the session','fa-seq3'],['old','seen in an earlier session','fa-seq5']];
 const rows=I.ses.map(q=>{const lab=x.C.topTopic(q.a.map(a=>a.key));
  const parts=segs.map(([k,label,cls])=>{const [cnt,r]=q.parts[k];if(!cnt)return '';const p=pc(r,cnt);
   return `<span class="${cls}" style="flex:0 0 calc(${(cnt/max*100).toFixed(2)}% - 2px)" title="${esc(`${label}: ${r} of ${cnt} right (${p}%)${k==='old'&&q.oldGaps.length?` · last seen a median ${f1(median(q.oldGaps))} days before`:''}`)}"><em>${n(cnt)} · ${p}%</em></span>`;}).join('');
  return `<div class="fa-srow"><div class="fa-slabel"><b>${esc(when(q.start))}</b> · ${pc(q.right,q.n)}% of ${n(q.n)}${lab?` · ${esc(lab)}`:''}</div><div class="fa-sbar" role="img" aria-label="${esc(`${when(q.start)}: ${q.parts.new[0]} first sight, ${q.parts.back[0]} back within the session, ${q.parts.old[0]} from earlier sessions`)}">${parts}</div></div>`;}).join('');
 const pl=I.pool,pA=pc(pl.all[1],pl.all[0]),pN=pc(pl.new[1],pl.new[0]),pB=pc(pl.back[1],pl.back[0]),pO=pc(pl.old[1],pl.old[0]);
 const why=`${I.ses.length>1?`Across these ${n(I.ses.length)} sessions, the`:'The'} ${pA}% headline ${pl.new[0]?`hides a ${pN}% first-sight rate.`:'has no first-sight answers in it.'}${pl.back[0]?` Same-session re-steps run at ${pB}%; they are rehearsal, not retention.`:''}${pl.old[0]?` Cards from earlier sessions: ${pO}%.`:''}`;
 return panel('i','What is inside a session score',sub,`<div class="fa-sessions">${rows}<div class="fa-scale"><span>0</span><span>${n(max)} answers</span></div></div><div class="fa-legend"><span><i class="fa-accent"></i>first sight</span><span><i class="fa-seq3"></i>back within the session</span><span><i class="fa-seq5"></i>seen in an earlier session${I.oldGap!==null?` (median ${f1(I.oldGap)} d before)`:''}</span></div>`,
  {wide:true,why,note:'Today block and hourly bars mix all three'});
}

/* ---------- render ---------- */
function render(host,d){
 if(!host||!d||!F)return;
 const old=host.querySelector('#fa-angles');if(old)old.remove();
 const sec=document.createElement('section');sec.id='fa-angles';sec.className='fa-angles';sec.setAttribute('aria-labelledby','fa-title');
 try{
  const x=compute(d);
  sec.innerHTML=`<div class="fa-head"><span class="vp-eyebrow">Flashcards · nine more angles</span><h2 class="fp-h" id="fa-title">New angles</h2><p class="ab-sub">Same ${plural(x.answers.length,'answer')} as above, replayed through the same FSRS scheduler. Each panel says what it can and cannot claim yet.</p></div>
  <div class="vp-grid">${panelA(x,d)}${panelB(x)}${panelC(x,d)}${panelD(x)}${panelE(x)}${panelF(x,d)}${panelG(x)}${panelH(x)}${panelI(x)}</div>`;
 }catch(e){console.error('flashcard angles',e);sec.innerHTML=`<div class="vp-notice">New angles could not be drawn (${esc(e.message)}).</div>`;}
 host.append(sec);
}
window.AneesFlashcardAngles={render,compute};
// This file loads after flashcard-progress.js; if the answers are already in, draw now.
const FP=window.AneesFlashcardProgress,host=document.getElementById('vp-tab-flash');
if(FP&&FP.loaded&&host&&!host.hidden&&!host.querySelector('#fa-angles'))render(host,FP.build());
})();
