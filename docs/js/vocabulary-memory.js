/* Memory estimates are separate from demonstrated vocabulary grades. */
(function(root){
'use strict';
const C=typeof module!=='undefined'&&module.exports?require('./word-bank-core.js'):root.AneesWordBank;
const LABELS=['Strong','Fading','At risk','High risk','Not yet checked','No successful recall'];
const KEYS=['strong','fading','risk','high','unchecked','no-recall'];
function day(value){
 const s=String(value||'').slice(0,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(s))return null;
 const [y,m,d]=s.split('-').map(Number),n=Date.UTC(y,m-1,d);
 return new Date(n).toISOString().slice(0,10)===s?n/86400000:null;
}
function today(now=new Date()){return day(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`);}
function assess(score,now=new Date()){
 const current=today(now),attempts=(score?.attempts||[]).filter(e=>day(C.date(e))!==null&&day(C.date(e))<=current);
 let last=null,bridge=null,gaps=[],floor=0,latest=null;
 for(const e of attempts){
  const p=e.p??e.vocab_points,when=day(C.date(e));latest=e;
  if(p===1){
   if(bridge&&String(bridge.lesson_id||C.date(bridge))!==String(e.lesson_id||C.date(e))){const gap=when-day(C.date(bridge));if(gap>0)gaps.push(gap);}
   last=e;bridge=e;floor=0;
  }else if(p===0){gaps=[];bridge=null;floor=2;}
  else if(p===.5){bridge=null;floor=Math.max(floor,1);}
 }
 // Conservative product heuristic, not a calibrated probability: two long
 // successful gaps support an extension, limited to twice the starting bands.
 const supportedGap=gaps.slice().sort((a,b)=>b-a)[1]||0;
 const scale=Math.min(2,Math.max(1,supportedGap/14));
 const thresholds=[14,21,35].map(n=>Math.round(n*scale));
 const age=last?current-day(C.date(last)):null;
 const timeTier=age===null?null:age<thresholds[0]?0:age<thresholds[1]?1:age<thresholds[2]?2:3;
 const tier=age===null?(attempts.length?5:4):Math.max(timeTier,floor);
 const reason=age===null?(attempts.length?'No full-credit recall is recorded yet.':'Studied vocabulary; no scored recall evidence yet.'):
  floor>timeTier?(floor===2?'A miss followed the last successful recall.':'A hinted answer followed the last successful recall.'):
  scale>1?'Window extended after two successful recalls across longer gaps.':'Starting memory window; based on days since full-credit recall.';
 return {key:KEYS[tier],label:LABELS[tier],tier,age,last,latest,thresholds,scale,reason,supportedGap};
}
function entries(rows,now=new Date()){
 return rows.filter(r=>!r.grammar_only).flatMap(r=>r.entries.map(f=>({row:r,form:f,memory:assess(f.speaking,now)})));
}
function summary(rows,now=new Date(),period=30){
 const all=entries(rows,now),current=today(now);
 const recent=e=>{const d=day(C.date(e));return d!==null&&d<=current&&d>current-period;};
 const eligible=rows.filter(r=>!r.grammar_only),dated=eligible.filter(r=>day(r.added)!==null);
 return {all,total:all.length,known:all.filter(x=>['Good','Mastered'].includes(x.form.speaking.status)).length,
 mastered:all.filter(x=>x.form.speaking.status==='Mastered').length,practised:all.filter(x=>x.form.speaking.attempts.some(recent)).length,
 newCount:eligible.length&&dated.length===eligible.length?dated.filter(r=>recent({date:r.added})).reduce((n,r)=>n+r.entries.length,0):null,
 atRisk:all.filter(x=>['risk','high'].includes(x.memory.key)).length,unchecked:all.filter(x=>x.form.speaking.status==='Untested').length,
 memoryCounts:Object.fromEntries(KEYS.map(k=>[k,all.filter(x=>x.memory.key===k).length])),
 statusCounts:Object.fromEntries(Object.keys(C.WEIGHTS).map(k=>[k,all.filter(x=>x.form.speaking.status===k).length]))};
}
function growth(rows,now=new Date(),period=30){
 const forms=rows.filter(r=>!r.grammar_only).flatMap(r=>r.entries),end=today(now);
 const first=Math.min(...forms.flatMap(f=>f.speaking.attempts.map(e=>day(C.date(e))).filter(d=>d!==null&&d<=end)));
 if(!Number.isFinite(first))return [];
 const start=Math.max(first,end-period+1),result=[];
 for(let d=start;d<=end;d++){
  const date=new Date(d*86400000).toISOString().slice(0,10);let known=0,mastered=0;
  for(const f of forms){const s=C.score(f.speaking.attempts.filter(e=>day(C.date(e))<=d)).status;if(['Good','Mastered'].includes(s))known++;if(s==='Mastered')mastered++;}
  result.push({date,known,mastered});
 }
 return result;
}
const api={LABELS,KEYS,day,today,assess,entries,summary,growth};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesVocabularyMemory=api;
})(typeof window!=='undefined'?window:globalThis);
