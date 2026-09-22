/* Aggregate statistics for Progress & Stats (Vocab page).
   Spec: plan/PROGRESS-STATS-VOCAB-SPEC-2026-09-21.md. Aggregates only — callers
   never receive per-word rows. Every number replays the same reviewed attempts
   the Word Bank scores; nothing is estimated or back-filled. */
(function(root){
'use strict';
const C=typeof module!=='undefined'&&module.exports?require('./word-bank-core.js'):root.AneesWordBank;
const M=typeof module!=='undefined'&&module.exports?require('./vocabulary-memory.js'):root.AneesVocabularyMemory;
const PERIODS={week:7,month:30,all:Infinity};
const KNOWN=new Set(['Good','Mastered']);
const iso=n=>new Date(n*86400000).toISOString().slice(0,10);
function forms(rows){return rows.filter(r=>!r.grammar_only).flatMap(r=>r.entries.map(f=>({row:r,form:f})));}
function range(now,period){
 const end=M.today(now),n=PERIODS[period]??Number(period);
 const start=Number.isFinite(n)?end-n+1:-Infinity;
 return {start,end,prevStart:Number.isFinite(n)?start-n:-Infinity,prevEnd:start-1,days:n};
}
const within=(d,a,b)=>d!==null&&d>=a&&d<=b;
function lessons(events){
 // One lesson per recorded date. Length = last transcript timestamp of that
 // recording (a lower bound on the recording, never a guess).
 const map=new Map();
 for(const e of events||[]){const d=C.date(e);if(M.day(d)===null)continue;const v=map.get(d)||{date:d,day:M.day(d),seconds:0};v.seconds=Math.max(v.seconds,Number(e.t_end)||0,Number(e.timeline_end)||0);map.set(d,v);}
 return [...map.values()].sort((a,b)=>a.day-b.day);
}
function statusAt(form,day){return C.score(form.speaking.attempts.filter(e=>M.day(C.date(e))<=day)).status;}
function attemptsIn(F,a,b){return F.flatMap(x=>x.form.speaking.attempts.filter(e=>within(M.day(C.date(e)),a,b)).map(e=>({p:e.p,day:M.day(C.date(e)),date:C.date(e),id:x.form.id})));}
function counts(list){return {correct:list.filter(e=>e.p===1).length,hinted:list.filter(e=>e.p===.5).length,wrong:list.filter(e=>e.p===0).length,total:list.length};}
const rate=c=>c.total?Math.round(c.correct/c.total*1000)/10:null;
function topCards(rows,events,now,period){
 const w=range(now,period),L=lessons(events),F=forms(rows);
 const pick=(a,b)=>L.filter(l=>within(l.day,a,b));
 const cur=pick(w.start,w.end),prev=pick(w.prevStart,w.prevEnd),week=pick(w.end-6,w.end),lastWeek=pick(w.end-13,w.end-7);
 const hours=ls=>Math.round(ls.reduce((s,l)=>s+l.seconds,0)/360)/10;
 const known=F.filter(x=>KNOWN.has(x.form.speaking.status)).length,mastered=F.filter(x=>x.form.speaking.status==='Mastered').length;
 const knownWeekAgo=F.filter(x=>KNOWN.has(statusAt(x.form,w.end-7))).length;
 return {
  lessons:{count:cur.length,previous:prev.length,week:week.length,lastWeek:lastWeek.length,loaded:L.length,latest:L.at(-1)?.date||null},
  hours:{total:hours(cur),previous:hours(prev),week:hours(week),avgMinutes:cur.length?Math.round(cur.reduce((s,l)=>s+l.seconds,0)/cur.length/60):null},
  known:{count:known,total:F.length,pct:F.length?Math.round(known/F.length*1000)/10:null,mastered,week:known-knownWeekAgo}
 };
}
function vocabCards(rows,events,now,period,documentRows){
 const w=range(now,period),L=lessons(events),F=forms(rows);
 const status=Object.fromEntries(Object.keys(C.WEIGHTS).map(k=>[k,F.filter(x=>x.form.speaking.status===k).length]));
 const dated=rows.filter(r=>!r.grammar_only&&M.day(r.added)!==null);
 const added=dated.length?dated.filter(r=>within(M.day(r.added),w.start,w.end)).reduce((n,r)=>n+r.entries.length,0):null;
 const sinceStart=Number.isFinite(w.start)?w.start-1:-Infinity;
 const masteredBefore=Number.isFinite(sinceStart)?F.filter(x=>statusAt(x.form,sinceStart)==='Mastered').length:0;
 const perLesson=lessonSeries(F,L.filter(l=>within(l.day,w.start,w.end))),prevLessons=lessonSeries(F,L.filter(l=>within(l.day,w.prevStart,w.prevEnd)));
 const avg=s=>s.length?Math.round(s.reduce((n,l)=>n+l.unique,0)/s.length*10)/10:null;
 const peak=perLesson.reduce((best,l)=>!best||l.unique>best.unique?l:best,null);
 const cur=counts(attemptsIn(F,w.start,w.end)),prev=counts(attemptsIn(F,w.prevStart,w.prevEnd));
 return {
  studied:{count:F.length,documentRows:documentRows??null,added},
  mastered:{count:status.Mastered,pct:F.length?Math.round(status.Mastered/F.length*1000)/10:null,status,trend:status.Mastered-masteredBefore},
  perLesson:{avg:avg(perLesson),previous:avg(prevLessons),peak:peak?{count:peak.unique,date:peak.date}:null,lessons:perLesson.length},
  ratio:{...cur,rate:rate(cur),previousRate:rate(prev)}
 };
}
function lessonSeries(F,L){
 return L.map(l=>{
  const seen=new Set(),tally={correct:0,hinted:0,wrong:0,total:0};let tested=0,retained=0;
  for(const x of F){
   const own=x.form.speaking.attempts.filter(e=>M.day(C.date(e))===l.day);
   if(!own.length)continue;
   seen.add(x.form.id);
   for(const e of own){tally.total++;if(e.p===1)tally.correct++;else if(e.p===.5)tally.hinted++;else tally.wrong++;}
   if(KNOWN.has(statusAt(x.form,l.day-1))){tested++;if(own[0].p===1)retained++;}
  }
  return {date:l.date,day:l.day,unique:seen.size,...tally,rate:rate(tally),tested,retained,retention:tested?Math.round(retained/tested*1000)/10:null};
 });
}
function funnel(rows,events,now,period){
 const w=range(now,period),F=forms(rows);
 return lessons(events).filter(l=>within(l.day,w.start,w.end)).map(l=>{
  const c={mastered:0,good:0,weak:0,unchecked:0};
  for(const x of F){const s=statusAt(x.form,l.day);if(s==='Mastered')c.mastered++;else if(s==='Good')c.good++;else if(s==='Untested')c.unchecked++;else c.weak++;}
  return {date:l.date,...c};
 });
}
function perLesson(rows,events,now,period){
 const w=range(now,period);
 const series=lessonSeries(forms(rows),lessons(events).filter(l=>within(l.day,w.start,w.end)));
 const scored=series.filter(l=>l.total);
 const avgRate=scored.length?Math.round(scored.reduce((n,l)=>n+l.rate,0)/scored.length*10)/10:null;
 const avgUnique=scored.length?Math.round(scored.reduce((n,l)=>n+l.unique,0)/scored.length*10)/10:null;
 const best=scored.reduce((b,l)=>!b||l.rate>b.rate?l:b,null),peak=scored.reduce((b,l)=>!b||l.unique>b.unique?l:b,null);
 return {series:scored,avgRate,avgUnique,baseline:scored[0]?.rate??null,best:best?{rate:best.rate,date:best.date}:null,peak:peak?{count:peak.unique,date:peak.date}:null};
}
function sections(rows){
 const map=new Map();
 for(const r of rows){if(r.grammar_only)continue;const name=r.topic||'Other',v=map.get(name)||{name,total:0,known:0};for(const f of r.entries){v.total++;if(KNOWN.has(f.speaking.status))v.known++;}map.set(name,v);}
 return [...map.values()].sort((a,b)=>b.total-a.total||a.name.localeCompare(b.name));
}
function newWords(rows,now,period){
 const dated=rows.filter(r=>!r.grammar_only&&M.day(r.added)!==null);
 if(!dated.length)return null;
 const w=range(now,period),weekOf=d=>d-((d+3)%7); // Monday-start weeks (1970-01-01 was a Thursday)
 const buckets=new Map();
 for(const r of dated){const d=M.day(r.added);if(!within(d,w.start,w.end))continue;const k=weekOf(d);buckets.set(k,(buckets.get(k)||0)+r.entries.length);}
 const weeks=[...buckets].sort((a,b)=>a[0]-b[0]);let running=0;
 const series=weeks.map(([k,n])=>({week:iso(k),added:n,cumulative:(running+=n)}));
 const inRange=dated.filter(r=>within(M.day(r.added),w.start,w.end));
 const total=series.reduce((n,x)=>n+x.added,0),peak=series.reduce((b,x)=>!b||x.added>b.added?x:b,null);
 const stillKnown=inRange.flatMap(r=>r.entries).filter(f=>KNOWN.has(f.speaking.status)).length,addedForms=inRange.reduce((n,r)=>n+r.entries.length,0);
 return {series,total,perWeek:series.length?Math.round(total/series.length*10)/10:null,peak:peak?{week:peak.week,added:peak.added}:null,stillKnownPct:addedForms?Math.round(stillKnown/addedForms*1000)/10:null};
}
const api={PERIODS,range,lessons,forms,statusAt,topCards,vocabCards,funnel,perLesson,sections,newWords};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesVocabularyStats=api;
})(typeof window!=='undefined'?window:globalThis);
