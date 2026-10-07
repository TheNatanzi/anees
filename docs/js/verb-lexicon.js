/* Progress & Stats › Verbal Lexicon tab (Medi 2026-09-27: "implement the lexicon").
   Nine angles on the verbs (A–I), spec = the approved mockup (verbal-lexicon-proposal.html).
   Everything is computed here, at runtime, from the Word Bank rows vocabulary-progress.js already
   built with the Word Bank's own model and scoring (AneesWordBank.models: each verb row, its tense
   entries, entry.observations = who said it when, entry.speaking = the status ladder), plus
   grammar-console.json (hand-checked family-B corrections), grammar-usage.json (per-bucket use
   counts) and lessons.json (lesson dates, taught verb pairs). Names are the Word Bank's own display
   spelling (house_spelling / her Doc arabizi via models(), rule S1); Arabic is her Doc's Arabic.
   Nothing is re-spelled, nothing is hardcoded; missing data renders "—" with the reason. */
(function(root){
'use strict';
const NODE=typeof module!=='undefined'&&module.exports;
const C=NODE?require('./word-bank-core.js'):root.AneesWordBank;
if(!C)return;
const N=C.normalize;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const short=d=>{const [,m,dd]=String(d).split('-');return `${Number(m)}/${Number(dd)}`;};
const pretty=d=>{if(!d)return '—';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const dayDiff=(a,b)=>{const p=a.split('-').map(Number),q=b.split('-').map(Number);return Math.round((Date.UTC(q[0],q[1]-1,q[2])-Date.UTC(p[0],p[1]-1,p[2]))/86400000);};
const TENSES=['Present','Past','Command','Future'];
const PERSONS=['I','You (m)','You (f)','You (pl)','He','She','We','They'];
const KNOWN=new Set(['Good','Mastered']);
const PRON_LAT=/^(ana|inta|inti|huwwe|heyye|i7na|intu|humme)\s+/i;
const PRON_AR=/^(أنا|إنت|إنتي|هو|هي|إحنا|إنتو|هم)\s+/;
const inc=(m,k,by=1)=>m.set(k,(m.get(k)||0)+by);

/* ---------- forms of one tense entry: [normalized text, person|null, engine guess?] ---------- */
function formsOf(f){
 const out=[],g=f.provenance==='inferred';
 for(const s of [f.word,f.arabic])if(s)out.push([N(s),null,g]);
 for(const p of f.persons||[]){const pg=p.provenance==='inferred';
  for(const s of [String(p.word||'').replace(PRON_LAT,''),String(p.arabic||'').replace(PRON_AR,'')])if(s)out.push([N(s),p.person,pg]);
  for(const s of [p.word,p.arabic])if(s&&/\s/.test(String(s).trim()))out.push([N(s),p.person,pg]);}   // with the pronoun too, for person detection
 return out.filter(x=>x[0]);
}
// Person is inferred: the one person whose form (from Amal's Doc or the engine's guess) appears in the sentence, else none.
function personOf(forms,text){const t=' '+N(text)+' ',ps=new Set();for(const [s,p] of forms)if(p&&t.includes(' '+s+' '))ps.add(p);return ps.size===1?[...ps][0]:null;}
// grammar-usage hits carry no person; read it off the prefix / ending (approximate by design).
function personPresent(h){const w=N(h).split(' ')[0]||'';return w.startsWith('بت')?'you/she':w.startsWith('بن')?'we':w.startsWith('بي')?'he/they':w.startsWith('ب')?'I':'?';}
function personPast(h){const ws=N(h).split(' '),w=ws[ws.length-1]||'';return w.endsWith('تي')?'you (f)':w.endsWith('تو')||w.endsWith('توا')?'you (pl)':w.endsWith('نا')?'we':w.endsWith('وا')?'they':w.endsWith('ت')?'I / you (m) / she':'he (bare)';}

/* ---------- the numbers ---------- */
function compute(rows,{lessons=null,gc=null,gu=null}={}){
 const vrows=rows.filter(r=>r.type==='Verb');
 /* 1. per verb: what you said (Medi spoken events), what Amal said, per tense */
 const verbs=vrows.map(r=>{
  const medi=new Map(),amal=new Set(),amalDates=new Set(),tenses={},status={},heardT={},doc={},scored={},persons=new Map(),homographs=new Set();
  const byLabel=new Map(r.entries.map(f=>[f.label,f]));
  for(const f of r.entries){
   const forms=formsOf(f);
   for(const e of f.observations){
    if(e.speaker==='Medi'){if(!medi.has(e.id))medi.set(e.id,{date:C.date(e),tense:f.label,person:personOf(forms,e.text),text:e.text||'',entry:f});}
    else if(e.speaker==='Amal'&&!e.immediate_repeat&&!e.is_echo){amal.add(C.date(e)+':'+(e.sentence_id||e.row_id));amalDates.add(C.date(e));}
   }
  }
  // Events the Word Bank could not file under one tense still count as the verb said / heard.
  for(const e of r.unassigned||[]){
   if(!Number.isFinite(e.t_start))continue;
   if(e.speaker==='Medi'&&e.spoken!==false){if(!medi.has(e.id))medi.set(e.id,{date:C.date(e),tense:null,person:null,text:e.text||'',entry:null});}
   else if(e.speaker==='Amal'&&!e.immediate_repeat&&!e.is_echo){amal.add(C.date(e)+':'+(e.sentence_id||e.row_id));amalDates.add(C.date(e));}
  }
  const M=[...medi.values()].sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:0);
  for(const t of TENSES){const f=byLabel.get(t);tenses[t]=M.filter(m=>m.tense===t).length;status[t]=f?f.speaking.status:'Untested';scored[t]=f?f.speaking.count:0;heardT[t]=f?f.heard:0;doc[t]=f?(f.persons||[]).filter(p=>p.provenance==='document').length:0;}
  for(const m of M)if(m.person)inc(persons,m.person);
  // Homograph: a command form spelled exactly like a past form of the same verb (unvocalized Arabic).
  const cmd=byLabel.get('Command'),past=byLabel.get('Past');
  if(cmd&&past){const pastAr=new Set([past.arabic,...(past.persons||[]).map(p=>String(p.arabic||'').replace(PRON_AR,''))].filter(Boolean).map(N));
   for(const p of [{arabic:cmd.arabic,word:cmd.word,provenance:cmd.provenance},...(cmd.persons||[])])if(p.arabic&&pastAr.has(N(p.arabic)))homographs.add(JSON.stringify([N(p.arabic),p.arabic,p.provenance==='document'?p.word:'']));}
  const attempts=r.entries.flatMap(f=>f.speaking.attempts.map(a=>({date:C.date(a),p:a.p})));
  return {row:r,id:r.id,name:r.name,arabic:r.arabic||'',english:r.english||'',topic:r.topic,medi:M,said:M.length,dates:new Set(M.map(m=>m.date)),heard:amal.size,amalKeys:amal,amalDates,
   tenses,status,scored,heardT,doc,persons,attempts,homographs:[...homographs].map(s=>JSON.parse(s)),
   tensesSaid:TENSES.filter(t=>tenses[t]>0),known:TENSES.filter(t=>KNOWN.has(status[t])),first:M.length?M[0].date:null};
 });
 const byId=new Map(verbs.map(v=>[v.id,v]));
 const said=verbs.filter(v=>v.said),heardOnly=verbs.filter(v=>!v.said&&v.heard).sort((a,b)=>b.heard-a.heard),never=verbs.filter(v=>!v.said&&!v.heard);
 const docForms=verbs.reduce((s,v)=>s+TENSES.reduce((x,t)=>x+v.doc[t],0),0),docT=Object.fromEntries(TENSES.map(t=>[t,verbs.reduce((s,v)=>s+v.doc[t],0)]));

 /* strip: every verb × tense you said, by its Word Bank status */
 const pairs=[];for(const v of verbs)for(const t of TENSES)if(v.tenses[t]||v.scored[t])pairs.push({v,t,status:v.status[t]});
 const pairStatus={Mastered:0,Good:0,Shaky:0,Wrong:0,Untested:0};for(const p of pairs)pairStatus[p.status]=(pairStatus[p.status]||0)+1;

 /* A: the ladder */
 const oneKnown=verbs.filter(v=>v.known.length>=1),twoKnown=verbs.filter(v=>v.known.length>=2);
 const events=said.reduce((s,v)=>s+v.said,0),lessonDates=new Set(said.flatMap(v=>[...v.dates]));
 const A={list:verbs.length,docForms,touched:said.length+heardOnly.length,heardOnly:heardOnly.length,said:said.length,events,lessons:lessonDates.size,oneKnown,twoKnown,oneTense:said.filter(v=>v.tensesSaid.length===1).length};

 /* B: tense and person spread */
 const tenseEvents=Object.fromEntries(TENSES.map(t=>[t,verbs.reduce((s,v)=>s+v.tenses[t],0)])),tensed=TENSES.reduce((s,t)=>s+tenseEvents[t],0);
 const untensed=verbs.reduce((s,v)=>s+v.medi.filter(m=>!m.tense).length,0);
 const personHits=new Map();for(const v of verbs)for(const m of v.medi)if(m.tense&&m.person)inc(personHits,m.person);
 const personTotal=[...personHits.values()].reduce((a,b)=>a+b,0);
 let pp=null,pq=null;
 if(gu&&gu.uses){pp=new Map();for(const u of gu.uses.B1||[])inc(pp,personPresent(u.hit));pq=new Map();for(const u of gu.uses.B5||[])inc(pq,personPast(u.hit));}
 const B={tenseEvents,tensed,untensed,personHits,personTotal,pp,pq,never:PERSONS.filter(p=>!personHits.get(p))};

 /* C: coverage matrix = every verb said or heard in a lesson, most present first (Medi 2026-10-02: "there should be
    more verbs"; it used to stop at the top 24) */
 const core=verbs.slice().sort((a,b)=>b.said-a.said||b.heard-a.heard).sort((a,b)=>(b.said+b.heard)-(a.said+a.heard)).filter(v=>v.said+v.heard>0);
 const cell=(v,t)=>{const st=v.status[t],k=v.tenses[t];return KNOWN.has(st)||(k||v.scored[t])?(st==='Untested'?'U':st[0]):v.heardT[t]?'H':v.doc[t]?'D':'-';};
 const cmdEvents=[],homoEvents=[];
 for(const v of verbs)for(const m of v.medi)if(m.tense==='Command'){cmdEvents.push({v,m});const t=' '+N(m.text)+' ';if(v.homographs.some(h=>t.includes(' '+h[0]+' ')))homoEvents.push({v,m});}
 const homoVerbs=new Map();for(const h of homoEvents)inc(homoVerbs,h.v);
 const Cc={core,cell,cmdEvents:cmdEvents.length,homoEvents:homoEvents.length,homoVerbs:[...homoVerbs].sort((a,b)=>b[1]-a[1]),docT};

 /* D: verbs said per lesson, new vs repeat; Amal's distinct verbs per lesson */
 const dates=(lessons&&lessons.length?lessons.map(l=>l.date):[...new Set([...lessonDates,...verbs.flatMap(v=>[...v.amalDates])])]).filter(Boolean).sort();
 const seen=new Set(),perLesson=dates.map(d=>{const vs=said.filter(v=>v.dates.has(d)),nw=vs.filter(v=>!seen.has(v.id));vs.forEach(v=>seen.add(v.id));return {date:d,said:vs.length,new:nw.length,repeat:vs.length-nw.length,amal:verbs.filter(v=>v.amalDates.has(d)).length,newNames:nw.map(v=>v.name)};});
 const tail=perLesson.slice(-8);
 const D={series:perLesson,tail:tail.length,zeroNew:tail.filter(p=>!p.new).length,cumulative:seen.size,lessonsFrom:dates.length&&lessons&&lessons.length?'lessons.json':'evidence dates'};

 /* E: corrections per verb. A family-B correction maps to the Doc verb whose form (longest first) is in its fixed or wrong text. */
 const formIndex=[];for(const v of verbs)for(const f of v.row.entries)for(const [s] of formsOf(f))if(s.length>=3)formIndex.push([s,v]);
 formIndex.sort((a,b)=>b[0].length-a[0].length);
 const findVerb=text=>{const nt=N(text);if(!nt)return null;const t=' '+nt+' ';for(const [s,v] of formIndex)if(t.includes(' '+s+' '))return v;
  for(const tok of nt.split(' ')){const base=tok.replace(/^(ما|ب|بت|بي|بن|ت|ي|ن|ا|ات)?/,'');if(base.length<3)continue;for(const [s,v] of formIndex)if(!s.includes(' ')&&(s.endsWith(base)||base.endsWith(s)))return v;}return null;};
 let E=null;
 if(gc&&gc.rules){
  const ruleName=new Map(gc.rules.map(r=>[r.id,r.name]));const corr=new Map(),buckets=new Map();let total=0,mapped=0;
  for(const r of gc.rules){if(r.family!=='B')continue;for(const c of r.candidates||[]){total++;const v=findVerb(c.right||'')||findVerb(c.wrong||'');if(!v)continue;mapped++;inc(corr,v);if(!buckets.has(v))buckets.set(v,new Map());inc(buckets.get(v),r.id);}}
  const pts=verbs.filter(v=>v.said||corr.get(v)).map(v=>({v,said:v.said,corr:corr.get(v)||0,buckets:[...(buckets.get(v)||new Map())].sort((a,b)=>b[1]-a[1])}));
  const worst=pts.filter(p=>p.said&&p.corr>p.said).sort((a,b)=>b.corr-a.corr||a.said-b.said)[0]||null;
  const clean=pts.filter(p=>!p.corr).sort((a,b)=>b.said-a.said)[0]||null;
  E={total,mapped,verbs:corr.size,pts,worst,clean,ruleName,updated:gc.updated||''};
 }

 /* F: taught pairs (lessons.json) to the first lesson you said the verb */
 let F=null;
 if(lessons&&lessons.some(l=>Array.isArray(l.taught))){
  const ar2v=new Map(),lat2v=new Map();
  for(const v of verbs){if(v.arabic)ar2v.set(N(v.arabic),v);const pres=v.row.entries.find(f=>f.label==='Present');for(const p of pres?pres.persons||[]:[])if(p.person==='I'&&p.arabic&&!ar2v.has(N(String(p.arabic).replace(PRON_AR,''))))ar2v.set(N(String(p.arabic).replace(PRON_AR,'')),v);}
  for(const v of verbs)for(const s of [v.name,v.row.key,(v.row.entries.find(f=>f.label==='Present')||{}).word])if(s){const k=N(String(s).replace(/^ana\s+/i,''));if(k&&!lat2v.has(k))lat2v.set(k,v);}
  const clean=s=>String(s||'').replace(/\(.*?\)/g,' ');
  const taught=new Map(),reviews=new Map(),unmatched=new Map();let items=0;
  for(const l of lessons)for(const t of l.taught||[]){
   const ar=clean(t.arabic).split('/').map(x=>x.trim().replace(PRON_AR,'')).filter(Boolean),la=clean(t.latin).split('/').map(x=>x.trim().replace(/^ana\s+/i,'')).filter(Boolean);
   ar.forEach((a,i)=>{items++;const v=ar2v.get(N(a))||(la[i]?lat2v.get(N(la[i])):null);
    if(!v){const k=N(a);if(!unmatched.has(k))unmatched.set(k,{latin:la[i]||'',arabic:a});return;}
    if(!taught.has(v))taught.set(v,l.date);if(t.review)inc(reviews,v);});
  }
  const rowsF=[...taught].sort((a,b)=>a[1]<b[1]?-1:a[1]>b[1]?1:0).map(([v,d0])=>{
   const after=v.medi.filter(m=>m.date>=d0),first=after.length?after[0].date:null;
   return {v,taught:d0,first,days:first?dayDiff(d0,first):null,saidAfter:after.length,lessonsAfter:new Set(after.map(m=>m.date)).size,
    indep:v.attempts.filter(a=>a.p===1&&a.date>=d0).length,tenses:[...new Set(after.map(m=>m.tense).filter(Boolean))],before:v.medi.length-after.length,
    heardSince:[...v.amalKeys].filter(k=>k.slice(0,10)>=d0).length,reviews:reviews.get(v)||0};});
  const teachDays=[...new Set(rowsF.map(r=>r.taught))].sort(),recentDays=teachDays.slice(-4),recent=rowsF.filter(r=>recentDays.includes(r.taught));
  F={rows:rowsF,items,saidAfter:rowsF.filter(r=>r.first).length,sameDay:rowsF.filter(r=>r.days===0).length,recentDays,recent:recent.length,recentSaid:recent.filter(r=>r.first).length,unmatched:[...unmatched.values()],dates};
 }

 /* H: the thin forms (grammar-usage buckets) and how many Doc verbs carry each */
 let H=null;
 if(gu&&gu.totals){
  const T=gu.totals,U=gu.uses||{},distinct=list=>{const s=new Set();for(const u of list){const v=findVerb(u.hit);if(v)s.add(v);}return s;};
  const ma=(U.C4||[]).filter(u=>N(u.hit).startsWith('ما '));const maVerbs=new Set();for(const u of ma){const v=findVerb(String(u.hit).replace(/^\s*ما\s*/,''));if(v)maVerbs.add(v);}
  const withVerbs=new Set(['B1','B5','B10','B11','B13']);
  const spec=[['B1','present with b-'],['B5','past'],['B6','kaan (was)'],['C4ma','ma + verb (negation)'],['B11','negative command'],['B3','bare after time word'],['B2','bare after modal'],['B8','ykoon'],['B10','command'],['B13','future with ra7']];
  const rowsH=spec.map(([id,label])=>{if(id==='C4ma')return {id:'C4',label,count:ma.length,verbs:maVerbs.size,verbList:[...maVerbs]};const s=withVerbs.has(id)?distinct(U[id]||[]):null;return {id,label,count:T[id]||0,verbs:s?s.size:null,verbList:s?[...s]:[]};}).sort((a,b)=>b.count-a.count);
  const fut=rowsH.find(r=>r.id==='B13');
  H={rows:rowsH,max:Math.max(1,...rowsH.map(r=>r.count)),lessons:Object.keys(gu.lessons||{}).length,future:fut,present:T.B1||0,command:T.B10||0,docCmd:docT.Command,docFut:docT.Future,updated:gu.updated||''};
 }

 /* I: next verb drill, picked from C, E and G */
 const I=[];
 const oneT=said.filter(v=>v.tensesSaid.length===1&&KNOWN.has(v.status[v.tensesSaid[0]])).map(v=>{const has=v.tensesSaid[0],target=['Past','Present','Command'].find(t=>t!==has&&v.doc[t]>0);return {v,has,target};}).filter(o=>o.target).sort((a,b)=>b.v.said-a.v.said)[0];
 if(oneT)I.push({kind:'one tense only',v:oneT.v,why:`Said ${n(oneT.v.said)} times, always ${oneT.has.toLowerCase()}, ${oneT.v.status[oneT.has]}. Her Doc has ${n(oneT.v.doc[oneT.target])} ${oneT.target.toLowerCase()} form${oneT.v.doc[oneT.target]===1?'':'s'}${oneT.target!=='Command'&&oneT.v.doc.Command&&!oneT.v.tenses.Command?` and ${n(oneT.v.doc.Command)} command${oneT.v.doc.Command===1?'':'s'}`:''}; you have never said one.`,pill:`Drill the ${oneT.target.toLowerCase()}`,cls:'warn'});
 const ho=heardOnly[0];
 if(ho){const withDoc=TENSES.filter(t=>ho.doc[t]>0).map(t=>t.toLowerCase());I.push({kind:'heard only',v:ho,why:`The tutor said it in ${n(ho.heard)} sentence${ho.heard===1?'':'s'} over the lessons; you never have.${withDoc.length?` Her Doc has ${withDoc.join(', ')} forms.`:' Her Doc lists the present only.'}`,pill:'Never said',cls:'bad'});}
 if(E&&E.worst){const w=E.worst;I.push({kind:'most corrected per use',v:w.v,why:`${n(w.said)} saying${w.said===1?'':'s'}, ${n(w.corr)} corrections: ${w.buckets.map(([id,k])=>`${E.ruleName.get(id)||id} ${k}`).join(', ')}.`,pill:w.corr>=w.said?'Every use corrected':'Often corrected',cls:'bad'});}

 return {verbs,byId,said,heardOnly,never,pairs,pairStatus,docForms,A,B,C:Cc,D,E,F,G:{list:heardOnly,never:never.length,rank:v=>1+verbs.filter(x=>x.heard>v.heard).length},H,I,topic:mode(vrows.map(r=>r.topic))};
}
function mode(a){const m=new Map();for(const x of a)if(x)inc(m,x);return [...m].sort((p,q)=>q[1]-p[1])[0]?.[0]||'';}

if(NODE){module.exports={compute};return;}

/* ================= rendering (browser only) ================= */
const $=id=>document.getElementById(id);
const W=640,H=250,PAD={l:38,r:14,t:18,b:34};
const STATUS=[['Mastered','vl-st-M'],['Good','vl-st-G'],['Shaky','vl-st-S'],['Wrong','vl-st-W'],['Untested','vl-st-U']];
const STLABEL={Mastered:'Mastered',Good:'Good',Shaky:'Shaky',Wrong:'Wrong',Untested:'said, not scorable yet'};
const frame=(inner,label,h=H,w=W)=>`<svg class="vp-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${inner}</svg>`;
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v)));const r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
function grid(y,maxY,steps=null){steps=steps||[4,5,2,1].find(k=>maxY%k===0&&Number.isInteger(maxY/k))||4;let s='';for(let i=0;i<=steps;i++){const v=maxY*i/steps;s+=`<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text x="${PAD.l-6}" y="${(y(v)+3.5).toFixed(1)}" text-anchor="end">${n(Math.round(v*10)/10)}</text>`;}return s;}
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
const verbName=(v,en=true)=>`<span class="vl-az">${esc(v.name)}</span> <span class="vl-ar" lang="ar" dir="rtl">${esc(v.arabic)}</span>${en&&v.english?` <span class="vl-en">${esc(v.english)}</span>`:''}`;
const big=(num,small)=>`<div class="vl-big"><b>${num}</b><span>${small}</span></div>`;
function panel(id,title,sub,body,{wide=false,head='',foot='',src=''}={}){
 return `<section class="vp-panel ${wide?'vl-wide':''}" aria-labelledby="vl-h-${id}"><div class="vp-panelhead"><div><span class="vl-key">${id.toUpperCase()}</span><h2 id="vl-h-${id}">${esc(title)}</h2><p class="ab-sub">${sub}</p></div></div>${head}${body}${foot||src?`<p class="vl-foot"><span class="vl-why">${foot}</span>${src?`<span>${src}</span>`:''}</p>`:''}</section>`;
}
const hrow=(label,title,w,num,cls='',labelHtml=null)=>`<div class="vl-row" title="${esc(title)}"><span class="vl-label">${labelHtml===null?esc(label):labelHtml}</span><span class="vl-track"><i class="${cls}" style="width:${Math.max(0,Math.min(100,w)).toFixed(1)}%"></i></span><span class="vl-n">${num}</span></div>`;

function pA(d){
 const a=d.A;if(!a.list)return empty('The verb list has not synced (no Verb rows in the Word Bank).');
 const rungs=[['On the tutor’s list',a.list,`${n(a.list)} verbs, ${n(a.docForms)} forms written in her Doc`],['Heard or said in a lesson',a.touched,`${n(a.said)} said by you + ${n(a.heardOnly)} heard from the tutor only`],['Said by you',a.said,`${n(a.events)} spoken events over ${n(a.lessons)} lessons`],['One tense Good or Mastered',a.oneKnown.length,`${n(a.oneKnown.length)} verbs with at least one known tense`],['Two tenses Good or Mastered',a.twoKnown.length,`${n(a.twoKnown.length)} verbs with two known tenses`]];
 return `<div class="vl-ladder">${rungs.map((r,i)=>hrow(r[0],`${r[0]}: ${r[2]}`,r[1]/a.list*100,`<b>${n(r[1])}</b>`,`vl-rung-${i}`)).join('')}</div>`;
}
function stack(label,note,segs,ramp){
 const total=segs.reduce((s,x)=>s+x[1],0);if(!total)return `<div class="vl-stackhead"><b>${esc(label)}</b><span>${esc(note)}</span></div>${empty('No uses yet.')}`;
 return `<div class="vl-stackhead"><b>${esc(label)}</b><span>${esc(note)}</span></div><div class="vl-stack" role="img" aria-label="${esc(label)}">${segs.filter(x=>x[1]).map((x,i)=>{const p=x[1]/total*100;return `<i class="${ramp[segs.indexOf(x)%ramp.length]}" style="flex:${x[1]} 1 0" title="${esc(x[0])}: ${n(x[1])} (${Math.round(p)}%)">${p>=13?`${esc(x[0])} ${n(x[1])}`:''}</i>`;}).join('')}</div><div class="vl-legend">${segs.map((x,i)=>!x[1]?'':`<span><i class="${ramp[i%ramp.length]}"></i>${esc(x[0])} ${n(x[1])}</span>`).join('')}</div>`;
}
function pB(d){
 const b=d.B,te=b.tenseEvents,R=['vl-seg-1','vl-seg-2','vl-seg-3','vl-seg-4','vl-seg-5','vl-seg-6'],RA=['vl-seg-a','vl-seg-2','vl-seg-3','vl-seg-4','vl-seg-1','vl-seg-6'];
 let s=stack(`Tense of your ${n(b.tensed)} tensed verb events`,'Word Bank evidence',TENSES.map(t=>[t.toLowerCase(),te[t]]),R);
 if(b.pp){const g=k=>b.pp.get(k)||0,tot=[...b.pp.values()].reduce((x,y)=>x+y,0);s+=stack(`Person on ${n(tot)} present uses (b- prefix)`,'grammar-usage B1',[['I',g('I')],['we (bn-)',g('we')],['you / she (bt-)',g('you/she')],['he / they (by-)',g('he/they')],['unreadable',g('?')]],RA);}
 else s+=`<div class="vl-stackhead"><b>Person on present uses</b></div>${empty('— grammar-usage.json did not load, so present uses have no person split.')}`;
 if(b.pq){const g=k=>b.pq.get(k)||0,tot=[...b.pq.values()].reduce((x,y)=>x+y,0);s+=stack(`Person on ${n(tot)} past uses (ending)`,'grammar-usage B5',[['I / you (m) / she (-t)',g('I / you (m) / she')],['he (bare)',g('he (bare)')],['you (f) -ti',g('you (f)')],['we -na',g('we')],['you (pl) -tu',g('you (pl)')],['they -u',g('they')]],RA);}
 return s;
}
function pC(d){
 const c=d.C,core=c.core;if(!core.length)return empty('Appears once a verb from the tutor’s list has been said or heard in a lesson.');
 const per=Math.ceil(core.length/2),cw=34,ch=22,gap=3,labW=150,w=labW+TENSES.length*(cw+gap)+4,hh=22+per*(ch+gap);
 const fill={M:'vl-st-M',G:'vl-st-G',S:'vl-st-S',W:'vl-st-W',U:'vl-st-U',H:'vl-cell-heard',D:'vl-cell-doc','-':'vl-cell-none'};
 const words={M:'Mastered',G:'Good',S:'Shaky',W:'Wrong',U:'said, not scorable yet',H:'heard from the tutor only',D:'in the Doc, never used','-':'no form from the tutor, engine guess only'};
 const block=list=>{let s=`<defs><pattern id="vl-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect class="vl-hatch-bg" width="5" height="5"/><line class="vl-hatch-line" x1="0" y1="0" x2="0" y2="5"/></pattern></defs>`;
  TENSES.forEach((t,j)=>s+=`<text x="${labW+j*(cw+gap)+cw/2}" y="13" text-anchor="middle">${t.slice(0,4)}</text>`);
  list.forEach((v,i)=>{const y=20+i*(ch+gap);
   s+=`<text class="vl-svg-name" x="0" y="${y+15}"><title>${esc(v.name)} · ${esc(v.english)} · said ${n(v.said)} · heard ${n(v.heard)}</title>${esc(v.name.length>13?v.name.slice(0,12)+'…':v.name)}</text><text class="vl-svg-ar" x="${labW-8}" y="${y+16}" text-anchor="end">${esc(v.arabic)}</text>`;
   TENSES.forEach((t,j)=>{const code=c.cell(v,t),x=labW+j*(cw+gap),k=v.tenses[t];
    const detail=`${words[code]}${k?` · said ${n(k)}`:''}${v.heardT[t]?` · heard ${n(v.heardT[t])}`:''}${v.doc[t]?` · ${n(v.doc[t])} Doc person${v.doc[t]===1?'':'s'}`:''}`;
    s+=`<rect class="${fill[code]}" x="${x}" y="${y}" width="${cw}" height="${ch}" rx="3"${code==='H'?' fill="url(#vl-hatch)"':''}><title>${esc(v.name)} (${esc(v.english)}) · ${t}: ${esc(detail)}</title></rect>${k&&'MGSWU'.includes(code)?`<text class="vl-cell-num ${code==='U'?'vl-cell-num-dark':''}" x="${x+cw/2}" y="${y+15}" text-anchor="middle">${n(k)}</text>`:''}`;});});
  return `<svg class="vp-chart" viewBox="0 0 ${w} ${hh}" role="img" aria-label="Coverage matrix: verbs by tense">${s}</svg>`;};
 const legend=`<div class="vl-legend">${[['vl-st-M','Mastered'],['vl-st-G','Good'],['vl-st-S','Shaky'],['vl-st-W','Wrong'],['vl-st-U','said, not scorable'],['vl-cell-heard','heard from the tutor only'],['vl-cell-doc','in the Doc, untouched'],['vl-cell-none','no Doc form']].map(([k,l])=>`<span><i class="${k}"></i>${l}</span>`).join('')}</div>`;
 return `<div class="vl-matrix">${block(core.slice(0,per))}${block(core.slice(per))}</div>${legend}`;
}
function pD(d){
 const s=d.D.series;if(!s.length)return empty('No lessons loaded yet.');
 const maxY=niceMax(Math.max(4,...s.map(p=>Math.max(p.said,p.amal)))*1.05),y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/maxY,slot=(W-PAD.l-PAD.r)/s.length,bw=Math.min(30,slot*.62);
 let g=grid(y,maxY);
 s.forEach((p,i)=>{const cx=PAD.l+slot*i+slot/2,x=cx-bw/2;
  g+=`<rect class="vl-bar-repeat" x="${x.toFixed(1)}" y="${y(p.repeat).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(p.repeat)).toFixed(1)}" rx="2"><title>${pretty(p.date)}: ${n(p.repeat)} repeat verbs</title></rect>`;
  if(p.new)g+=`<rect class="vl-bar-new" x="${x.toFixed(1)}" y="${y(p.said).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y(p.repeat)-y(p.said)).toFixed(1)}" rx="2"><title>${pretty(p.date)}: ${n(p.new)} new verbs: ${esc(p.newNames.join(', '))}</title></rect>`;
  g+=`<circle class="vl-dot-amal" cx="${cx.toFixed(1)}" cy="${y(p.amal).toFixed(1)}" r="4.5"><title>${pretty(p.date)}: the tutor said ${n(p.amal)} distinct verbs</title></circle>`;
  const step=Math.ceil(s.length/8);if(i%step===0||i===s.length-1)g+=`<text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${H-10}" text-anchor="middle">${short(p.date)}</text>`;});
 return frame(g,`Verbs said per lesson, new versus repeat, across ${s.length} lessons`)+`<div class="vl-legend"><span><i class="vl-bar-new"></i>new</span><span><i class="vl-bar-repeat"></i>repeat</span><span><i class="vl-dot-amal vl-round"></i>The tutor</span></div>`;
}
function pE(d){
 const e=d.E;if(!e)return empty('— grammar-console.json did not load, so corrections cannot be mapped to verbs.');
 const p=e.pts;if(!p.length)return empty('No verbs said or corrected yet.');
 const mx=niceMax(Math.max(...p.map(q=>q.said),1)),my=niceMax(Math.max(...p.map(q=>q.corr),1)),x=v=>PAD.l+(W-PAD.l-PAD.r)*v/mx,y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/my;
 let s=grid(y,my)+[0,.25,.5,.75,1].map(f=>`<text x="${x(mx*f).toFixed(1)}" y="${H-10}" text-anchor="middle">${n(Math.round(mx*f))}</text>`).join('')+`<text x="${W-PAD.r}" y="${H-22}" text-anchor="end">times you said it →</text><text x="${PAD.l+4}" y="${PAD.t-4}">↑ corrections</text>`;
 const label=new Set(),placed=[];for(const q of p.slice().sort((a,b)=>b.said-a.said).slice(0,5).concat(p.slice().sort((a,b)=>b.corr-a.corr).slice(0,5))){const px=x(q.said),py=y(q.corr);if(label.has(q)||placed.some(([qx,qy])=>Math.abs(qx-px)<70&&Math.abs(qy-py)<12))continue;label.add(q);placed.push([px,py]);}
 for(const q of p.slice().sort((a,b)=>(a.said+a.corr)-(b.said+b.corr))){const rate=q.corr/(q.said+q.corr),cls=rate<.1?'vl-pt-good':rate<.3?'vl-pt-ok':rate<.5?'vl-pt-warn':'vl-pt-bad';
  s+=`<g><circle class="vl-pt ${cls}" cx="${x(q.said).toFixed(1)}" cy="${y(q.corr).toFixed(1)}" r="6"><title>${esc(q.v.name)} (${esc(q.v.english)}): said ${n(q.said)}, corrected ${n(q.corr)}${q.buckets.length?' · '+esc(q.buckets.map(([id,k])=>`${id} ${k}`).join(', ')):''}</title></circle>${label.has(q)?`<text class="vp-callout" x="${(x(q.said)+9).toFixed(1)}" y="${(y(q.corr)+4).toFixed(1)}">${esc(q.v.name)}</text>`:''}</g>`;}
 return frame(s,'Times said versus corrections per verb')+`<div class="vl-legend"><span><i class="vl-pt-good"></i>under 10%</span><span><i class="vl-pt-ok"></i>10–30%</span><span><i class="vl-pt-warn"></i>30–50%</span><span><i class="vl-pt-bad"></i>over 50%</span><span>corrections ÷ (said + corrections)</span></div>`;
}
// Counts only since 2026-10-02 (Medi: no word lists on Progress); the verbs themselves are in the Word Bank.
function pF(d){
 const f=d.F;if(!f)return empty('— lessons.json did not load (or has no taught list), so there are no taught pairs to follow.');
 if(!f.rows.length)return empty('No taught verb matches a verb on the tutor’s list yet.');
 const never=f.rows.filter(r=>!r.first).length,days=f.rows.filter(r=>r.first).map(r=>r.days).sort((x,y)=>x-y),med=days.length?days[days.length>>1]:null;
 return `<div class="vl-kv"><span><b>${n(never)}</b>taught, never said</span><span><b>${med===null?'—':n(med)+' d'}</b>median from taught to first said</span></div><p class="vl-more"><a href="word-bank.html?topic=${encodeURIComponent(d.topic||'Verbs List')}">The verbs are in the Word Bank →</a></p>`;
}
function pG(d){
 const g=d.G.list;if(!g.length)return empty('Every verb the tutor has said, you have said too.');
 return `<p class="vl-more"><a href="word-bank.html?topic=${encodeURIComponent(d.topic||'Verbs List')}">The verbs are in the Word Bank →</a></p>`;
}
function pH(d){
 const h=d.H;if(!h)return empty('— grammar-usage.json did not load, so verb shapes cannot be counted.');
 return `<div class="vl-ladder vl-thin">${h.rows.map(r=>hrow(r.label,`${r.id} ${r.label}: ${r.count} uses${r.verbs!==null?` on ${r.verbs} Doc verb${r.verbs===1?'':'s'}`:''}`,r.count/h.max*100,`${n(r.count)}${r.verbs!==null?` · ${n(r.verbs)} verb${r.verbs===1?'':'s'}`:''}`,r.count<=h.max*.1?'vl-fill-accent':'vl-fill-sage')).join('')}</div>`;
}
function pI(d){
 if(!d.I.length)return empty('Appears once there are verbs to pick from.');
 return `<div class="vl-focus">${d.I.map(f=>`<div class="vl-fcard"><div class="vl-fid">${esc(f.kind)}</div><div class="vl-fname">${verbName(f.v)}</div><div class="vl-fwhy">${esc(f.why)}</div><span class="vl-pill vl-pill-${f.cls}">${esc(f.pill)}</span></div>`).join('')}</div>`;
}

/* ---------- render ---------- */
let extra=null,extraLoading=null,cache={rows:null,extra:null,d:null};
async function json(url){const r=await fetch(url+'?v='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('HTTP '+r.status+' '+url);return r.json();}
function loadExtra(){
 if(extraLoading)return extraLoading;
 const gp=root.AneesGrammarProgress&&root.AneesGrammarProgress.data;   // reuse the Grammar tab's copy when it is already loaded
 extraLoading=Promise.allSettled([json('data/lessons.json'),gp&&gp.gc?Promise.resolve(gp.gc):json('data/grammar-console.json'),json('data/grammar-usage.json')]).then(r=>{
  const v=i=>r[i].status==='fulfilled'?r[i].value:null,lj=v(0);
  extra={lessons:lj?(lj.lessons||lj).slice().sort((a,b)=>a.date<b.date?-1:1):null,gc:v(1),gu:v(2),failed:['lessons.json','grammar-console.json','grammar-usage.json'].filter((x,i)=>r[i].status!=='fulfilled')};
 });
 return extraLoading;
}
function render(){
 const host=$('vp-tab-lexicon');if(!host||host.hidden)return;
 const P=root.AneesVocabularyProgress,rows=P&&P.rows;
 if(!rows||!rows.length||!extra){host.innerHTML='<div class="vp-notice">Loading the verbs from the Word Bank…</div>';return;}
 let d;
 if(cache.rows===rows&&cache.extra===extra)d=cache.d;
 else{try{d=compute(rows,extra);cache={rows,extra,d};}catch(e){host.innerHTML=`<div class="vp-notice">The verb angles could not be computed (${esc(e.message)}). Other tabs are unaffected.</div>`;return;}}
 const a=d.A,b=d.B,c=d.C,D=d.D,E=d.E,F=d.F,G=d.G,Hh=d.H,ps=d.pairStatus,np=d.pairs.length;
 const bar=STATUS.map(([k,cls])=>ps[k]?`<i class="${cls}" style="width:${ps[k]/np*100}%" title="${n(ps[k])} ${STLABEL[k]}"></i>`:'').join('');
 const presentI=b.pp?(()=>{const tot=[...b.pp.values()].reduce((x,y)=>x+y,0);return tot?Math.round((b.pp.get('I')||0)/tot*100):null;})():null;
 const homo=c.homoVerbs[0],homoV=homo&&homo[0],homoForm=homoV&&homoV.homographs[0];
 const cFoot=`${c.cmdEvents?`Command column: ${n(c.homoEvents)} of the ${n(c.cmdEvents)} command events you said rest on a command spelled exactly like a past form${homoV?` (${homoForm&&homoForm[2]?`<span class="vl-az">${esc(homoForm[2])}</span> `:''}<span class="vl-ar" lang="ar">${esc(homoForm?homoForm[1]:'')}</span>, ${esc(homoV.name)}, ${n(homo[1])} of them)`:''}. Unvocalized, the Word Bank cannot tell “get happy!” from “he got happy” and files them as commands; they are shown as scored, not re-scored here.`:'No command events yet.'} ${c.docT.Future?'':'Future: the tutor’s Doc has no future forms, so every future cell is an engine guess.'}`;
 const Dfoot=D.series.length?(()=>{const am=D.series.map(p=>p.amal),me=D.series.map(p=>p.said),pk=D.series.reduce((x,y)=>y.said>x.said?y:x);return `The tutor says ${n(Math.min(...am))} to ${n(Math.max(...am))} distinct verbs a lesson; you say ${n(Math.min(...me))} to ${n(Math.max(...me))}. Peak: ${n(pk.said)} on ${pretty(pk.date)}.`;})():'';
 const Efoot=E?`${E.worst?`${esc(E.worst.v.name)}: ${n(E.worst.said)} saying${E.worst.said===1?'':'s'}, ${n(E.worst.corr)} corrections. `:''}${E.clean?`${esc(E.clean.v.name)}: ${n(E.clean.said)} sayings, none. `:''}Top-left is where a verb drill pays off.`:'';
 const Ffoot=F&&F.unmatched.length?`${n(F.unmatched.length)} more taught verb${F.unmatched.length===1?' is':'s are'} not on her Verbs List, so ${F.unmatched.length===1?'it has':'they have'} no forms to score.`:'';
 const gTop=G.list[0],Gfoot=gTop?`${esc(gTop.name)} (${esc(gTop.english)}) is the tutor’s no. ${n(G.rank(gTop))} most-heard verb. Her Doc has ${n(gTop.doc.Past)} past persons and ${n(gTop.doc.Command)} commands for it.`:'';
 const Hfoot=Hh?`Command ${n(Hh.command)} and future ${n(Hh.future?Hh.future.count:0)} against present ${n(Hh.present)}. The tutor’s Doc has ${n(Hh.docCmd)} command forms and ${Hh.docFut?n(Hh.docFut):'no'} future forms.`:'';
 const futV=Hh&&Hh.future&&Hh.future.verbList;
 const lessonsN=D.series.length;
 host.innerHTML=`
 <a class="vl-strip" href="word-bank.html?topic=${encodeURIComponent(d.topic||'Verbs List')}" title="Open the Word Bank on the tutor’s verbs">
  <div><div class="vl-sub">Verbal lexicon · one-line summary</div><div class="vl-kv"><span><b>${n(a.list)}</b>verbs on the tutor’s list</span><span><b>${n(a.docForms)}</b>forms in her Doc</span><span><b>${n(a.said)}</b>verbs you have said</span><span><b>${E?n(E.total):'—'}</b>verb corrections, hand-checked${E?'':' (grammar-console.json did not load)'}</span></div>
  <div class="vl-statusbar" aria-label="Status of the ${n(np)} verb and tense pairs you have said">${bar}</div>
  <small>Of the ${n(np)} verb × tense pairs you have said: ${n(ps.Mastered)} mastered · ${n(ps.Good)} good · ${n(ps.Shaky)} shaky · ${n(ps.Wrong)} wrong · ${n(ps.Untested)} said but not scorable yet. Per-form status lives in the Word Bank.</small></div>
  <span class="vl-open">Open →</span></a>
 <div class="vp-grid">
 ${panel('a','Verbs I can conjugate cold','A verb counts when two of its tenses sit at Good or Mastered on the Word Bank ladder. One ladder, from the tutor’s list down to that.',pA(d),{head:big(n(a.twoKnown.length),`of ${n(a.list)}`),foot:`${n(a.oneTense)} of your ${n(a.said)} verbs exist in one tense only. The gap between the last two rungs is this tab’s job.`,src:'Ladder = Word Bank score(), speaking lane'})}
 ${panel('b','Tense and person spread','Top: which tense your verb events land in. Below: who the subject is, read off the b- prefix and the past ending of every present and past use.',pB(d),{head:big(presentI===null?'—':presentI+'%',presentI===null?'grammar-usage.json did not load':`of your present-tense uses are “I”${b.never.length?' · '+esc(b.never.join(', ').replace(/You/g,'you').replace(/She/,'she').replace(/They/,'they').replace(/We/,'we').replace(/He/,'he'))+': never detected in the evidence':''}`),foot:`The Word Bank detects a person on ${n(b.personTotal)} of ${n(b.tensed)} tensed events; the rest are bare forms. Person is inferred, not heard: from the form's prefix or ending (bt- is “you” or “she”, -t is “I”, “you” or “she”). ${n(b.untensed)} more verb events have no tense filed.`,src:'grammar-usage hits + evidence persons'})}
 ${panel('c',`Coverage matrix: ${n(c.core.length)} verbs × 4 tenses`,'Every verb said or heard in a lesson, most present first (your voice plus the tutor’s). Filled = you said it, coloured by status. Hatched = only the tutor has said it. Outlined = the tutor’s Doc has the forms, nobody has used them. Dashed = no form from the tutor, engine guess only.',pC(d),{wide:true,foot:cFoot,src:'Hover a cell: said / heard / Doc persons'})}
 ${panel('d','Verbs said per lesson, new vs repeat','Distinct verbs in your voice each lesson. Top of each bar = verbs said for the first time ever, bottom = repeats. Orange dots = distinct verbs the tutor said in that lesson.',pD(d),{head:D.tail?big(n(D.zeroNew),`lesson${D.zeroNew===1?'':'s'} of the last ${n(D.tail)} with no new verb · ${n(D.cumulative)} cumulative`):'',foot:Dfoot,src:`evidence, your spoken events · lessons from ${D.lessonsFrom}`})}
 ${panel('e','Most corrected vs most used','Each dot a verb: how often you said it against how often the tutor corrected a verb rule on it. Colour = corrections as a share of uses.',pE(d),{head:E?big(`${n(E.mapped)} of ${n(E.total)}`,`family-B corrections map to a Doc verb · ${n(E.verbs)} verbs corrected`):'',foot:Efoot,src:'grammar-console family B, matched on the fixed form'})}
 ${panel('f','Taught to said: every verb pair the tutor introduced','Verbs from the lessons’ taught list: how many you went on to say, and how fast.',pF(d),{wide:true,head:F&&F.rows.length?big(`${n(F.saidAfter)}`,`of ${n(F.rows.length)} taught verbs said afterwards · ${n(F.sameDay)} the same day${F.recentDays.length>1?` · taught ${pretty(F.recentDays[0])}–${pretty(F.recentDays[F.recentDays.length-1])}: ${n(F.recentSaid)} of ${n(F.recent)}`:''}`):'',foot:Ffoot,src:'lessons.json taught × evidence first spoken date'})}
 ${panel('g','Verbs the tutor uses that you never do','Verbs the tutor says in lessons that have never left your mouth in a recorded lesson.',pG(d),{head:big(n(G.list.length),`verbs heard only · ${n(G.never)} never appeared at all`),foot:Gfoot,src:'The tutor’s words, echoes excluded'})}
 ${panel('h','Negation, command, future: the thin forms',`How often each verb shape shows up in your Arabic, all ${n(Hh?Hh.lessons:lessonsN)} lessons, and how many different Doc verbs carry it.`,pH(d),{head:Hh&&Hh.future?big(n(Hh.future.count),`future uses in ${n(Hh.lessons)} lessons${futV&&futV.length===1?`, all on one verb (${esc(futV[0].name)})`:futV&&futV.length?`, on ${n(futV.length)} verbs`:''}`):'',foot:Hfoot,src:'grammar-usage by bucket + hit words'})}
 ${panel('i','Next verb drill','Three verbs picked automatically from C, E and G. One card the tutor or the Flashcards randomizer could take as is.',pI(d),{wide:true,foot:'Picking rule: the most-said verb you know in one tense only (with Doc forms for another), the verb the tutor says most that you never have, the verb corrected more often than said.'})}
 </div>
 <p class="vp-footer">Verbal lexicon: computed live from ${n(a.list)} verbs on the tutor’s list, the Word Bank’s scored evidence and ${n(lessonsN)} lessons · said = your spoken events (tensed or not) · heard = the tutor’s sentences with echoes removed${extra.failed.length?` · not loaded: ${esc(extra.failed.join(', '))}`:''}${E&&E.updated?` · corrections updated ${esc(E.updated)}`:''}</p>`;
}
function show(){
 const host=$('vp-tab-lexicon');if(!host)return;
 if(!extra){render();loadExtra().then(render);}else render();
}
document.addEventListener('anees:vocab-rendered',render);
root.AneesVerbLexicon={show,render,compute,get data(){return cache.d;}};
{const h=$('vp-tab-lexicon');if(h&&!h.hidden)show();}   // the tab switch ran before this file loaded
})(typeof window!=='undefined'?window:globalThis);
