/* Flashcard scheduling: FSRS-6 with the published default parameters (py-fsrs
   DEFAULT_PARAMETERS), binary Again / Good, no fuzz. These parameters are not
   fitted to Medi; label them "default parameters, not fitted to you" until
   roughly 1,000 reviews exist. Card grade (Good / Mastered) is a separate track
   computed by word-bank-core from the same answers; this file only schedules. */
(function(root){
'use strict';
const W=Object.freeze([0.212,1.2931,2.3065,8.2956,6.4133,0.8334,3.0194,0.001,1.8722,0.1666,0.796,1.4835,0.0614,0.2629,1.6483,0.6014,1.8729,0.5425,0.0912,0.0658,0.1542]);
const DECAY=-W[20],FACTOR=Math.pow(0.9,1/DECAY)-1;
const DAY=86400000,MIN=60000,S_MIN=0.001;
const AGAIN=1,GOOD=3;
const DEFAULTS=Object.freeze({desiredRetention:0.9,learningSteps:[1,10],relearningSteps:[10],maximumInterval:36500,newPerDay:20,matureDays:21,leechLapses:8});
const RETENTIONS=Object.freeze([0.8,0.85,0.9,0.95]);
const opt=o=>({...DEFAULTS,...(o||{})});
const ms=t=>t instanceof Date?t.getTime():typeof t==='string'?Date.parse(t):Number(t);
const clampD=d=>Math.min(10,Math.max(1,d));
const clampS=s=>Math.max(S_MIN,s);
function rating(grade){
 const g=String(grade).toLowerCase();
 if(g==='again'||g==='missed'||g==='1')return AGAIN;
 if(g==='good'||g==='got'||g==='3')return GOOD;
 throw new Error('grade must be again or good');
}
function newCard(id){return{id:id??null,state:'learning',step:0,stability:null,difficulty:null,due:null,last_review:null,interval:0,reps:0,lapses:0};}
const initialStability=r=>clampS(W[r-1]);
const initialDifficulty=(r,clamp=true)=>{const d=W[4]-Math.exp(W[5]*(r-1))+1;return clamp?clampD(d):d;};
function nextInterval(s,o){
 const i=Math.round(s/FACTOR*(Math.pow(o.desiredRetention,1/DECAY)-1));
 return Math.min(Math.max(i,1),o.maximumInterval);
}
function shortTerm(s,r){
 let inc=Math.exp(W[17]*(r-3+W[18]))*Math.pow(s,-W[19]);
 if(r>=GOOD)inc=Math.max(inc,1);
 return clampS(s*inc);
}
function nextDifficulty(d,r){
 const delta=-(W[6]*(r-3)),damped=d+(10-d)*delta/9;
 return clampD(W[7]*initialDifficulty(4,false)+(1-W[7])*damped);
}
function forget(d,s,R){
 return Math.min(W[11]*Math.pow(d,-W[12])*(Math.pow(s+1,W[13])-1)*Math.exp((1-R)*W[14]),s/Math.exp(W[17]*W[18]));
}
const recall=(d,s,R)=>s*(1+Math.exp(W[8])*(11-d)*Math.pow(s,-W[9])*(Math.exp((1-R)*W[10])-1));
const nextStability=(d,s,R,r)=>clampS(r===AGAIN?forget(d,s,R):recall(d,s,R));
// Whole elapsed days, as py-fsrs uses (timedelta.days).
const elapsedDays=(card,now)=>card.last_review===null?null:Math.floor((ms(now)-ms(card.last_review))/DAY);
function retrievability(card,now){
 if(!card||card.stability===null||card.last_review===null)return 0;
 const t=Math.max(0,elapsedDays(card,now));
 return Math.pow(1+FACTOR*t/card.stability,DECAY);
}
function schedule(card,grade,now,options){
 const o=opt(options),r=rating(grade),t=ms(now);
 if(!Number.isFinite(t))throw new Error('review time is not a valid date');
 const c={...card},days=elapsedDays(card,t),sameDay=days!==null&&days<1;
 const update=()=>{
  if(c.stability===null||c.difficulty===null){c.stability=initialStability(r);c.difficulty=initialDifficulty(r);return;}
  c.stability=sameDay?shortTerm(c.stability,r):nextStability(c.difficulty,c.stability,retrievability(card,t),r);
  c.difficulty=nextDifficulty(c.difficulty,r);
 };
 let wait;
 const toReview=()=>{c.state='review';c.step=null;c.interval=nextInterval(c.stability,o);wait=c.interval*DAY;};
 const steps=c.state==='relearning'?o.relearningSteps:o.learningSteps;
 if(c.state==='review'){
  update();
  if(r===AGAIN){
   c.lapses++;
   if(o.relearningSteps.length){c.state='relearning';c.step=0;c.interval=0;wait=o.relearningSteps[0]*MIN;}
   else toReview();
  }else toReview();
 }else{
  update();
  if(!steps.length||(c.step>=steps.length&&r===GOOD))toReview();
  else if(r===AGAIN){c.step=0;c.interval=0;wait=steps[0]*MIN;}
  else if(c.step+1===steps.length)toReview();
  else{c.step++;c.interval=0;wait=steps[c.step]*MIN;}
 }
 c.last_review=t;c.due=t+wait;c.reps++;
 return c;
}
// New = never reviewed; Mature = review interval of 21+ days; everything else is Learning.
function phase(card,options){
 const o=opt(options);
 if(!card||!card.reps)return 'new';
 return card.state==='review'&&card.interval>=o.matureDays?'mature':'learning';
}
const isLeech=(card,options)=>!!card&&card.lapses>=opt(options).leechLapses;
const isDue=(card,now)=>!!card&&card.reps>0&&card.due<=ms(now);
function localDay(t){const d=new Date(ms(t));return new Date(d.getFullYear(),d.getMonth(),d.getDate()).getTime();}
// Reviews due on each of the next `days` calendar days; day 0 includes anything overdue.
function forecast(cards,now,days=7){
 const start=localDay(now),out=[];
 for(let i=0;i<days;i++){const d=new Date(start);d.setDate(d.getDate()+i);out.push({date:`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`,due:0});}
 for(const c of cards){
  if(!c||!c.reps)continue;
  const d=localDay(c.due),i=Math.max(0,Math.round((d-start)/DAY));
  if(i<days)out[i].due++;
 }
 return out;
}
// Replay an answer log in time order. Rows: {word_key|key, card?, ts, result|grade, undone?}.
function replay(rows,options){
 const cards=new Map(),seen=new Set();
 const list=(rows||[]).filter(e=>e&&!e.undone&&e.kind!=='flag'&&Number.isFinite(ms(e.ts))).slice().sort((a,b)=>ms(a.ts)-ms(b.ts));
 for(const e of list){
  if(e.id!=null){if(seen.has(e.id))continue;seen.add(e.id);}
  const key=e.card||e.word_key||e.key;if(!key)continue;
  let g;try{g=rating(e.grade??e.result);}catch(err){continue;}
  cards.set(key,schedule(cards.get(key)||newCard(key),g,e.ts,options));
 }
 return cards;
}
const api={W,DECAY,FACTOR,DEFAULTS,RETENTIONS,AGAIN,GOOD,rating,newCard,schedule,retrievability,nextInterval:(s,o)=>nextInterval(s,opt(o)),phase,isLeech,isDue,forecast,replay,elapsedDays};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesFSRS=api;
})(typeof window!=='undefined'?window:globalThis);
