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
// Audit fixes 2026-09-27. A trend against the previous period needs at least this many lessons in that period.
const MIN_TREND_LESSONS=3;
// Retention points from fewer tested known words than this are drawn faded and never drive the "Current" callout.
const MIN_RETENTION_TESTED=5;
// A form type (Past, Plural, Future …) counts as exercised by the lessons once at least this share of its forms has
// been said — the same threshold the New angles panel G uses. Future / Command / Plural slots said once in 14
// lessons stay unexercised, so "of forms any lesson has used" is not padded by them.
const EXERCISED_TYPE_SHARE=.02;
const iso=n=>new Date(n*86400000).toISOString().slice(0,10);
const share=(a,b)=>b?Math.round(a/b*1000)/10:null;
function forms(rows){return rows.filter(r=>!r.grammar_only).flatMap(r=>r.entries.map(f=>({row:r,form:f})));}
const said=f=>f.speaking.attempts.length>0;
const heard=f=>(f.heard||0)>0||(f.observations||[]).some(e=>e.speaker==='Amal'&&!e.immediate_repeat&&!e.is_echo);
// Forms any lesson has used: said or heard themselves, or of a form type the lessons exercise. Known ⊂ said ⊂ used.
function exercised(F){
 const byType=new Map();
 for(const x of F){const v=byType.get(x.form.label)||{total:0,said:0};v.total++;if(said(x.form))v.said++;byType.set(x.form.label,v);}
 const typeUsed=label=>{const v=byType.get(label);return !!v&&v.said/v.total>=EXERCISED_TYPE_SHARE;};
 return new Set(F.filter(x=>said(x.form)||heard(x.form)||typeUsed(x.form.label)).map(x=>x.form));
}
// Add dates. Supabase words.first_seen is the day the sync first saw a word (mapped onto row.added by the page).
// The first date, when it holds most of the list, is the import: those words were on the list before tracking
// began and are never shown as additions. Tracking starts the day after.
function addDates(rows){
 const dated=rows.filter(r=>!r.grammar_only&&M.day(r.added)!==null).map(r=>({row:r,day:M.day(r.added)}));
 if(!dated.length)return {dated,imported:null,tracked:[],since:null};
 const byDay=new Map();for(const d of dated)byDay.set(d.day,(byDay.get(d.day)||0)+1);
 const first=Math.min(...byDay.keys()),bulk=byDay.get(first)*2>dated.length,onDay=dated.filter(d=>d.day===first);
 const imported=bulk?{date:iso(first),day:first,words:listWords(onDay),rows:onDay.length,forms:formsOf(onDay)}:null;
 return {dated,imported,tracked:bulk?dated.filter(d=>d.day>first):dated,since:iso(bulk?first+1:first)};
}
// A Word Bank row is one word, or one verb group standing for its person rows in Amal's list (row.keys).
const listWords=list=>list.reduce((n,d)=>n+(d.row.keys||[d.row.key]).length,0),formsOf=list=>list.reduce((n,d)=>n+d.row.entries.length,0);
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
 const w=range(now,period),L=lessons(events),F=forms(rows),E=exercised(F);
 const pick=(a,b)=>L.filter(l=>within(l.day,a,b));
 const cur=pick(w.start,w.end),prev=pick(w.prevStart,w.prevEnd),week=pick(w.end-6,w.end),lastWeek=pick(w.end-13,w.end-7);
 const hours=ls=>Math.round(ls.reduce((s,l)=>s+l.seconds,0)/360)/10;
 const known=F.filter(x=>KNOWN.has(x.form.speaking.status)).length,mastered=F.filter(x=>x.form.speaking.status==='Mastered').length;
 const knownWeekAgo=F.filter(x=>KNOWN.has(statusAt(x.form,w.end-7))).length;
 return {
  lessons:{count:cur.length,previous:prev.length,week:week.length,lastWeek:lastWeek.length,loaded:L.length,latest:L.at(-1)?.date||null},
  hours:{total:hours(cur),previous:hours(prev),week:hours(week),avgMinutes:cur.length?Math.round(cur.reduce((s,l)=>s+l.seconds,0)/cur.length/60):null},
  known:{count:known,total:F.length,pct:share(known,F.length),exercised:E.size,pctExercised:share(known,E.size),mastered,week:known-knownWeekAgo}
 };
}
function vocabCards(rows,events,now,period,documentRows){
 const w=range(now,period),L=lessons(events),F=forms(rows),E=exercised(F);
 const status=Object.fromEntries(Object.keys(C.WEIGHTS).map(k=>[k,F.filter(x=>x.form.speaking.status===k).length]));
 const A=addDates(rows);
 const added=A.dated.length?formsOf(A.tracked.filter(d=>within(d.day,w.start,w.end))):null;
 const sinceStart=Number.isFinite(w.start)?w.start-1:-Infinity;
 const masteredBefore=Number.isFinite(sinceStart)?F.filter(x=>statusAt(x.form,sinceStart)==='Mastered').length:0;
 const perLesson=lessonSeries(F,L.filter(l=>within(l.day,w.start,w.end))),prevLessons=lessonSeries(F,L.filter(l=>within(l.day,w.prevStart,w.prevEnd)));
 const avg=s=>s.length?Math.round(s.reduce((n,l)=>n+l.unique,0)/s.length*10)/10:null;
 const peak=perLesson.reduce((best,l)=>!best||l.unique>best.unique?l:best,null);
 const cur=counts(attemptsIn(F,w.start,w.end)),prev=counts(attemptsIn(F,w.prevStart,w.prevEnd));
 return {
  studied:{count:F.length,documentRows:documentRows??null,added,sinceTracking:A.dated.length?formsOf(A.tracked):null,trackingSince:A.since,imported:A.imported},
  mastered:{count:status.Mastered,pct:share(status.Mastered,F.length),exercised:E.size,pctExercised:share(status.Mastered,E.size),status,trend:status.Mastered-masteredBefore},
  perLesson:{avg:avg(perLesson),previous:avg(prevLessons),previousLessons:prevLessons.length,peak:peak?{count:peak.unique,date:peak.date}:null,lessons:perLesson.length},
  ratio:{...cur,rate:rate(cur),previousRate:rate(prev),previousLessons:prevLessons.filter(l=>l.total).length}
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
 // avgRate is the mean of per-lesson rates (a 2-attempt lesson weighs as much as a 150-attempt one). The page draws
 // pooledRate: all correct attempts over all attempts in the shown lessons.
 const avgRate=scored.length?Math.round(scored.reduce((n,l)=>n+l.rate,0)/scored.length*10)/10:null;
 const pooled=scored.reduce((c,l)=>({correct:c.correct+l.correct,total:c.total+l.total}),{correct:0,total:0});
 const avgUnique=scored.length?Math.round(scored.reduce((n,l)=>n+l.unique,0)/scored.length*10)/10:null;
 const best=scored.reduce((b,l)=>!b||l.rate>b.rate?l:b,null),peak=scored.reduce((b,l)=>!b||l.unique>b.unique?l:b,null);
 return {series:scored,avgRate,pooledRate:rate(pooled),pooled,avgUnique,baseline:scored[0]?.rate??null,best:best?{rate:best.rate,date:best.date}:null,peak:peak?{count:peak.unique,date:peak.date}:null};
}
// With {exercised:true} each section also carries `exercised`: its forms any lesson has used (see exercised()).
function sections(rows,{exercised:withExercised=false}={}){
 const F=forms(rows),E=withExercised?exercised(F):null,map=new Map();
 for(const x of F){const name=x.row.topic||'Other',v=map.get(name)||(E?{name,total:0,known:0,exercised:0}:{name,total:0,known:0});v.total++;if(KNOWN.has(x.form.speaking.status))v.known++;if(E&&E.has(x.form))v.exercised++;map.set(name,v);}
 return [...map.values()].sort((a,b)=>b.total-a.total||a.name.localeCompare(b.name));
}
// Bars = forms added per week since tracking began; the import-day bulk is reported in `imported`, never as bars.
function newWords(rows,now,period){
 const A=addDates(rows);
 if(!A.dated.length)return null;
 const w=range(now,period),weekOf=d=>d-((d+3)%7); // Monday-start weeks (1970-01-01 was a Thursday)
 const buckets=new Map();
 for(const d of A.tracked){if(!within(d.day,w.start,w.end))continue;const k=weekOf(d.day);buckets.set(k,(buckets.get(k)||0)+d.row.entries.length);}
 const weeks=[...buckets].sort((a,b)=>a[0]-b[0]);let running=0;
 const series=weeks.map(([k,n])=>({week:iso(k),added:n,cumulative:(running+=n)}));
 const inRange=A.tracked.filter(d=>within(d.day,w.start,w.end));
 const total=series.reduce((n,x)=>n+x.added,0),peak=series.reduce((b,x)=>!b||x.added>b.added?x:b,null);
 const stillKnown=inRange.flatMap(d=>d.row.entries).filter(f=>KNOWN.has(f.speaking.status)).length,addedForms=inRange.reduce((n,d)=>n+d.row.entries.length,0);
 return {series,total,words:listWords(inRange),perWeek:series.length?Math.round(total/series.length*10)/10:null,peak:peak?{week:peak.week,added:peak.added}:null,stillKnownPct:share(stillKnown,addedForms),imported:A.imported,trackingSince:A.since};
}
const api={PERIODS,MIN_TREND_LESSONS,MIN_RETENTION_TESTED,EXERCISED_TYPE_SHARE,range,lessons,forms,exercised,addDates,statusAt,topCards,vocabCards,funnel,perLesson,sections,newWords};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesVocabularyStats=api;
})(typeof window!=='undefined'?window:globalThis);
