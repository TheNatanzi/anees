/* Progress & Stats — Flashcards tab (pure, no DOM). Spec: plan/PROGRESS-STATS-FLASHCARDS-SPEC-2026-09-22.md.
   Everything is derived from the card_results answer log replayed through AneesFSRS;
   nothing here stores FSRS state. Local calendar days, weeks start on Monday.
   A value with no data is null, never 0 dressed up as a result. */
(function(root){
'use strict';
const F=root.AneesFSRS||(typeof require==='function'?require('./fsrs.js'):null);
const DAY=86400000,MATURE=21;
const ms=t=>t instanceof Date?t.getTime():typeof t==='string'?Date.parse(t):Number(t);
const pad=n=>String(n).padStart(2,'0');
const dayStart=t=>{const d=new Date(ms(t));return new Date(d.getFullYear(),d.getMonth(),d.getDate()).getTime();};
const addDays=(t,n)=>{const d=new Date(dayStart(t));d.setDate(d.getDate()+n);return d.getTime();};
const iso=t=>{const d=new Date(ms(t));return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;};
const weekStart=t=>{const d=new Date(dayStart(t));return addDays(d,-((d.getDay()+6)%7));};
const monthStart=t=>{const d=new Date(ms(t));return new Date(d.getFullYear(),d.getMonth(),1).getTime();};
const rate=(right,n)=>n?Math.round(right/n*1000)/10:null;
const correct=r=>String(r.grade??r.result).toLowerCase()==='got'||String(r.grade??r.result).toLowerCase()==='good';

// Durable answers only: no flags, no undone rows, one row per id, time order.
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
const preKind=c=>!c.reps?'new':c.state==='review'?'review':'learning';
const prePhase=c=>!c.reps?'new':c.state==='review'&&c.interval>=MATURE?'mature':'learning';
// Replay with the card state BEFORE each answer kept, so every answer knows its phase.
function history(log,options){
 const cards=new Map(),states=new Map(),answers=[];
 for(const r of clean(log)){
  const key=r.word_key||r.key,before=cards.get(key)||F.newCard(key),t=ms(r.ts);
  const after=F.schedule(before,r.grade??r.result,t,options);
  cards.set(key,after);
  if(!states.has(key))states.set(key,[]);states.get(key).push(after);
  const answer_ms=Number(r.answer_ms);
  answers.push({key,t,right:correct(r),kind:preKind(before),phase:prePhase(before),interval:before.reps?before.interval:null,answer_ms:Number.isFinite(answer_ms)&&answer_ms>0&&r.answer_ms!==null?answer_ms:null});
 }
 return {cards,states,answers};
}
// Goals: distinct cards answered this calendar week (Mon–Sun) and month.
function goals(h,now,{weekly=50,monthly=200}={}){
 const count=from=>new Set(h.answers.filter(a=>a.t>=from&&a.t<=ms(now)).map(a=>a.key)).size;
 const one=(n,goal)=>({n,goal,pct:Math.min(100,Math.round(n/goal*100))});
 return {week:one(count(weekStart(now)),weekly),month:one(count(monthStart(now)),monthly)};
}
// Reviewed cards (learning included) due by the end of today, and the passes that keeps the target.
function workload(cards,now,retention){
 const end=addDays(now,1);let needed=0;
 for(const c of cards.values())if(c.reps&&c.due<end)needed++;
 return {needed,passes:Math.ceil(needed*retention)};
}
const trueRetention=h=>{const m=h.answers.filter(a=>a.phase==='mature'),r=m.filter(a=>a.right).length;return {n:m.length,right:r,pct:rate(r,m.length)};};
const leeches=cards=>[...cards.values()].filter(c=>F.isLeech(c));
// Average retrievability of every card answered so far, per day, from the first answer to today + `ahead`.
function curve(h,now,ahead=30){
 if(!h.answers.length)return [];
 const bumps=new Set(h.answers.filter(a=>a.right).map(a=>iso(a.t))),out=[],today=dayStart(now),t0=ms(now);
 for(let d=dayStart(h.answers[0].t);d<=addDays(today,ahead);d=addDays(d,1)){
  const at=d===today?t0:addDays(d,1)-1;
  let sum=0,n=0;
  for(const list of h.states.values()){
   let s=null;for(const c of list){if(c.last_review<=at)s=c;else break;}
   if(!s)continue;sum+=F.retrievability(s,Math.max(at,s.last_review));n++;
  }
  out.push({date:iso(d),r:n?Math.round(sum/n*1000)/10:null,cards:n,bump:bumps.has(iso(d)),future:d>today});
 }
 return out;
}
// New / Learning / Mature, from the current cards and the phase of each past answer.
function segmentation(h,wordKeys){
 const first=new Map();for(const a of h.answers)if(!first.has(a.key))first.set(a.key,a);
 const firsts=[...first.values()],learnA=h.answers.filter(a=>a.phase==='learning');
 let learning=0,mature=0,lapses=0;
 for(const c of h.cards.values()){const p=F.phase(c);if(p==='mature'){mature++;lapses+=c.lapses;}else if(p==='learning')learning++;}
 const unseen=(wordKeys||[]).filter(k=>!h.cards.has(k)).length;
 return {new:{count:unseen,firstAnswers:firsts.length,pass:rate(firsts.filter(a=>a.right).length,firsts.length)},
  learning:{count:learning,answers:learnA.length,pass:rate(learnA.filter(a=>a.right).length,learnA.length)},
  mature:{count:mature,lapses}};
}
function today(h,now){
 const from=dayStart(now),a=h.answers.filter(x=>x.t>=from&&x.t<=ms(now)),right=a.filter(x=>x.right).length;
 const timed=a.filter(x=>x.answer_ms!==null),split={new:0,learning:0,review:0};for(const x of a)split[x.kind]++;
 return {n:a.length,cards:new Set(a.map(x=>x.key)).size,right,pct:rate(right,a.length),ms:timed.reduce((s,x)=>s+x.answer_ms,0),timed:timed.length,split};
}
// One square per day for the last 12 months; streaks count consecutive days with any answer.
function heatmap(h,now){
 const per=new Map();for(const a of h.answers){const k=iso(a.t);per.set(k,(per.get(k)||0)+1);}
 const today=dayStart(now),start=addDays(today,-364),days=[];
 for(let d=start;d<=today;d=addDays(d,1))days.push({date:iso(d),n:per.get(iso(d))||0,weekday:(new Date(d).getDay()+6)%7});
 let current=0;for(let d=per.has(iso(today))?today:addDays(today,-1);per.has(iso(d));d=addDays(d,-1))current++;
 let longest=0,run=0,prev=null;
 for(const k of [...per.keys()].sort()){const t=dayStart(new Date(k+'T12:00'));run=prev!==null&&addDays(prev,1)===t?run+1:1;longest=Math.max(longest,run);prev=t;}
 return {days,current,longest,max:Math.max(0,...days.map(d=>d.n)),active:days.filter(d=>d.n).length};
}
// Anki's true-retention table: review answers only, split by the interval before the answer.
function retentionTable(h,now){
 const today=dayStart(now),t=ms(now);
 const periods=[['today','Today',today,t],['yesterday','Yesterday',addDays(today,-1),today-1],['week','Last week',addDays(today,-6),t],['month','Last month',addDays(today,-29),t],['year','Last year',addDays(today,-364),t]];
 const rows=[['young','Young',a=>a.interval<MATURE],['mature','Mature',a=>a.interval>=MATURE],['total','Total',()=>true]];
 const rev=h.answers.filter(a=>a.kind==='review');
 return {periods:periods.map(([id,label])=>({id,label})),rows:rows.map(([id,label,test])=>({id,label,cells:periods.map(([pid,,from,to])=>{const a=rev.filter(x=>x.t>=from&&x.t<=to&&test(x)),r=a.filter(x=>x.right).length;return {period:pid,n:a.length,right:r,pct:rate(r,a.length)};})}))};
}
// Cards due on each of the next `days` days; overdue cards are a separate backlog.
function futureDue(cards,now,days){
 const today=dayStart(now),out=[];let overdue=0;
 for(let i=0;i<days;i++)out.push({date:iso(addDays(today,i)),due:0});
 for(const c of cards.values()){
  if(!c.reps)continue;
  if(c.due<today){overdue++;continue;}
  const i=Math.round((dayStart(c.due)-today)/DAY);if(i<days)out[i].due++;
 }
 return {days:out,overdue,total:out.reduce((s,d)=>s+d.due,0)};
}
const STAB=[[0,1,'<1d'],[1,3,'1–2d'],[3,7,'3–6d'],[7,14,'1–2w'],[14,30,'2–4w'],[30,90,'1–3mo'],[90,Infinity,'3mo+']];
function histograms(cards,now){
 const list=[...cards.values()].filter(c=>c.reps&&c.stability!==null);
 if(!list.length)return null;
 const avg=v=>Math.round(v.reduce((s,x)=>s+x,0)/v.length*10)/10;
 const st=list.map(c=>c.stability),df=list.map(c=>c.difficulty),rt=list.map(c=>F.retrievability(c,Math.max(ms(now),c.last_review))*100);
 return {n:list.length,
  stability:{avg:avg(st),bins:STAB.map(([lo,hi,label])=>({label,n:st.filter(s=>s>=lo&&s<hi).length}))},
  difficulty:{avg:avg(df),bins:Array.from({length:10},(_,i)=>({label:String(i+1),n:df.filter(d=>Math.min(10,Math.floor(d))===i+1).length}))},
  retrievability:{avg:avg(rt),bins:Array.from({length:10},(_,i)=>({label:`${i*10}%`,range:`${i*10}–${i*10+10}%`,n:rt.filter(r=>Math.min(9,Math.floor(r/10))===i).length}))}};
}
// Visible answer time only (flip + answer); slow answers never change a grade.
function timing(h,top=10){
 const t=h.answers.filter(a=>a.answer_ms!==null);
 if(!t.length)return null;
 const v=t.map(a=>a.answer_ms).sort((a,b)=>a-b),mid=Math.floor(v.length/2);
 const per=new Map();for(const a of t){const p=per.get(a.key)||{key:a.key,n:0,sum:0,max:0};p.n++;p.sum+=a.answer_ms;p.max=Math.max(p.max,a.answer_ms);per.set(a.key,p);}
 return {n:t.length,avg:v.reduce((s,x)=>s+x,0)/v.length,median:v.length%2?v[mid]:(v[mid-1]+v[mid])/2,
  slowest:[...per.values()].map(p=>({key:p.key,n:p.n,avg:p.sum/p.n,max:p.max})).sort((a,b)=>b.avg-a.avg).slice(0,top)};
}
function hourly(h,minimum=100){
 const hours=Array.from({length:24},(_,hour)=>({hour,n:0,right:0,pct:null}));
 for(const a of h.answers){const x=hours[new Date(a.t).getHours()];x.n++;if(a.right)x.right++;}
 for(const x of hours)x.pct=rate(x.right,x.n);
 return {hours,total:h.answers.length,faded:h.answers.length<minimum};
}
const api={MATURE,clean,history,goals,workload,trueRetention,leeches,curve,segmentation,today,heatmap,retentionTable,futureDue,histograms,timing,hourly,iso,dayStart,weekStart,monthStart,addDays};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesFlashcardStats=api;
})(typeof window!=='undefined'?window:globalThis);
