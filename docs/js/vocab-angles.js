/* Progress & Stats › Vocab tab › New angles (Medi 2026-09-27: "all of these").
   Nine panels (A–I) under the six Vocab charts. Every number is computed here, at
   runtime, from the rows vocabulary-progress.js already builds with the Word Bank's
   own scoring (AneesWordBank.models → form.speaking.attempts, form.observations):
   attempts = Medi's scored tries (p 1 / 0.5 / 0), heard = Amal's observations with
   echoes removed. Names are the Word Bank's own display spelling (house_spelling /
   arabizi via models(), rule S1); nothing is re-spelled here. Missing data → "—"
   with a reason. Re-renders on the 'anees:vocab-rendered' event (data load, pills). */
(function(){
'use strict';
const C=window.AneesWordBank,S=window.AneesVocabularyStats,M=window.AneesVocabularyMemory;
if(!C||!S||!M)return;
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const pc=(a,b)=>b?Math.round(a/b*1000)/10:null;
const pct=v=>v===null||v===undefined?'—':v+'%';
const iso=d=>new Date(d*86400000).toISOString().slice(0,10);
const pretty=d=>{if(!d)return '—';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const short=d=>{const [,m,dd]=String(d).split('-');return `${Number(m)}/${Number(dd)}`;};
const median=a=>{if(!a.length)return null;const s=a.slice().sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;};
const clip=(t,k)=>t.length>k?t.slice(0,k-1)+'…':t;
const KNOWN=new Set(['Good','Mastered']);
const COLD=7,TRAIL=28;
const HORIZON={week:'Week',month:'Month',all:'All time'};

/* ---------- forms: the Word Bank's rows, flattened ---------- */
function formsOf(rows){
 return S.forms(rows).map(({row,form:f})=>{
  const t=e=>Number(e.t_start)||0;
  const att=f.speaking.attempts.map(e=>({day:M.day(C.date(e)),date:C.date(e),t:t(e),p:e.p})).filter(e=>e.day!==null);
  const amal=[],medi=[];
  for(const e of f.observations){const day=M.day(C.date(e));if(day===null)continue;
   if(e.speaker==='Amal'){if(!e.immediate_repeat&&!e.is_echo)amal.push({day,t:t(e)});}
   else if(e.speaker==='Medi')medi.push({day,t:t(e)});}
  // Exposure = Amal said it (echoes removed) or you said it (any spoken observation or scored try).
  const expo=amal.concat(medi,att).sort((a,b)=>a.day-b.day||a.t-b.t);
  // Display name exactly as the Word Bank shows it: the form's word, or the row name for adjectives.
  const base=row.type==='Adjective'||!f.word?row.name:f.word;
  const name=row.entries.length>1?`${base} (${String(f.label).toLowerCase()})`:base;
  // First try of each lesson day, with the last exposure on an earlier day.
  const tries=[],seen=new Set();
  for(const a of att){if(seen.has(a.day))continue;seen.add(a.day);let prev=null;for(const e of expo){if(e.day>=a.day)break;prev=e.day;}tries.push({...a,prev});}
  return {row,f,name,english:row.english||'',topic:row.topic||'Other',type:row.type||'Word',label:f.label,status:f.speaking.status,att,amal,medi,expo,tries,
   attDays:new Set(att.map(a=>a.day)),amalDays:new Set(amal.map(a=>a.day))};
 });
}

/* ---------- the numbers ---------- */
function compute(rows,events,now,period){
 const F=formsOf(rows),L=S.lessons(events),idx=new Map(L.map((l,i)=>[l.day,i])),w=S.range(now,period),today=M.today(now);
 const inP=d=>d>=w.start&&d<=w.end,LP=L.filter(l=>inP(l.day)),said=F.filter(x=>x.att.length);
 const out={F,L,LP,said,period,today};

 /* A: forms said cold (first try of the day right, last exposure 7+ days earlier), trailing 28 days per lesson */
 const cold=F.map(x=>({strict:x.tries.filter(t=>t.p===1&&t.prev!==null&&t.day-t.prev>=COLD).map(t=>t.day),loose:x.tries.filter(t=>t.p===1&&(t.prev===null||t.day-t.prev>=COLD)).map(t=>t.day)}));
 const A=L.map(l=>{const a=l.day-TRAIL+1,has=ds=>ds.some(d=>d>=a&&d<=l.day);let s=0,o=0;for(const c of cold){if(has(c.strict))s++;if(has(c.loose))o++;}return {date:l.date,day:l.day,cold:s,loose:o};});
 const baseP=L.length?A.filter(p=>p.day<L[0].day+14):[];
 const base=baseP.length?baseP.reduce((s,p)=>s+p.cold,0)/baseP.length:null;
 const lastA=A.at(-1)||null,weekAgo=lastA?A.filter(p=>p.day<=lastA.day-7).at(-1)||null:null;
 const trend=A.map((p,i)=>i>=3?(A[i].cold+A[i-1].cold+A[i-2].cold+A[i-3].cold)/4:null);
 out.A={series:A,base,baseN:baseP.length,last:lastA,weekAgo,trend};

 /* B: first try of the day, by gap since last exposure (period) */
 const BK=[['first','first ever'],['lt7','under 7 d'],['7','7–13 d'],['14','14–20 d'],['21','21 d+']];
 const bk=t=>t.prev===null?0:t.day-t.prev<7?1:t.day-t.prev<14?2:t.day-t.prev<21?3:4;
 const B=BK.map(([k,label])=>({k,label,n:0,right:0,hinted:0,wrong:0}));
 for(const x of F)for(const t of x.tries){if(!inP(t.day))continue;const b=B[bk(t)];b.n++;if(t.p===1)b.right++;else if(t.p===.5)b.hinted++;else b.wrong++;}
 B.forEach(b=>b.pass=pc(b.right,b.n));
 out.B={buckets:B,wrong:B.reduce((s,b)=>s+b.wrong,0),firstWrong:B[0].wrong,tries:B.reduce((s,b)=>s+b.n,0)};

 /* C: of forms first said in a lesson, the share said again within N later lessons (all lessons) */
 const lastI=L.length-1,life=said.map(x=>{const ix=[...new Set(x.att.map(a=>idx.get(a.day)))].filter(v=>v!==undefined).sort((a,b)=>a-b);return {x,ix};}).filter(o=>o.ix.length);
 const C_=[1,2,3,4,5,6,8,10].map(k=>{let elig=0,hit=0;for(const o of life){if(o.ix[0]+k>lastI)continue;elig++;if(o.ix.some(i=>i>o.ix[0]&&i<=o.ix[0]+k))hit++;}return {k,elig,hit,share:pc(hit,elig)};}).filter(c=>c.elig);
 const once=life.filter(o=>o.ix.length===1);
 out.C={series:C_,said:life.length,once:once.length,stale:once.filter(o=>o.ix[0]<=lastI-3).length,half:C_.find(c=>c.share>=50)||null};

 /* D: breadth of reuse — distinct lessons each said form appeared in (period) */
 const reuse=F.map(x=>{const days=new Set(x.att.filter(a=>inP(a.day)).map(a=>a.day));return {x,lessons:days.size,attempts:x.att.filter(a=>inP(a.day)).length};}).filter(o=>o.lessons);
 const hist=[1,2,3,4,5,6].map(k=>({k:k===6?'6+':String(k),count:reuse.filter(o=>k===6?o.lessons>=6:o.lessons===k).length}));
 out.D={hist,top:reuse.slice().sort((a,b)=>b.lessons-a.lessons||b.attempts-a.attempts||a.x.name.localeCompare(b.x.name)).slice(0,10),said:reuse.length,lessons:LP.length,wide:reuse.filter(o=>o.lessons>=6).length};

 /* E: input vs output per lesson (period) + heard, never said (all time) */
 const E=LP.map(l=>{let h=0,s=0,b=0;for(const x of F){const hh=x.amalDays.has(l.day),ss=x.attDays.has(l.day);if(hh)h++;if(ss)s++;if(hh&&ss)b++;}return {date:l.date,heard:h,said:s,both:b};});
 const heardEver=F.filter(x=>x.amal.length),inputOnly=heardEver.filter(x=>!x.att.length).map(x=>({x,lessons:x.amalDays.size,times:x.amal.length})).sort((a,b)=>b.lessons-a.lessons||b.times-a.times||a.x.name.localeCompare(b.x.name));
 out.E={series:E,heard:heardEver.length,said:said.length,inputOnly,neither:F.filter(x=>!x.amal.length&&!x.att.length).length,lessons:L.length};

 /* F: known forms by days since last said (as of today) */
 const known=F.filter(x=>KNOWN.has(x.status)&&x.att.length).map(x=>{const last=x.att.at(-1).day;return {x,last,days:today-last,count:x.att.length,amalSince:x.amal.some(a=>a.day>last)};});
 const FB=[[0,6,'0–6 d','green'],[7,13,'7–13 d','blue'],[14,20,'14–20 d','orange'],[21,34,'21–34 d','red'],[35,Infinity,'35+ d','deep']].map(([lo,hi,label,cls])=>({label,cls,lo,count:known.filter(o=>o.days>=lo&&o.days<=hi).length}));
 const red=known.filter(o=>o.days>=21),redDates=[...new Set(red.map(o=>o.last))];
 out.F={known:known.length,bands:FB,list:known.slice().sort((a,b)=>b.days-a.days||b.count-a.count||a.x.name.localeCompare(b.x.name)).slice(0,9),amalSince:known.filter(o=>o.amalSince).length,red:red.length,redDates};

 /* G: form types — said / on the list (all time) */
 const gm=new Map();for(const x of F){const k=x.label==='Word'?'Word (single form)':`${x.type} · ${String(x.label).toLowerCase()}`;const v=gm.get(k)||{k,said:0,total:0};v.total++;if(x.att.length)v.said++;gm.set(k,v);}
 const G=[...gm.values()].sort((a,b)=>b.said-a.said||b.total-a.total);
 const rare=G.filter(g=>g.total>=3&&g.said/g.total<.02),rareTotal=rare.reduce((s,g)=>s+g.total,0),rareSaid=rare.reduce((s,g)=>s+g.said,0);
 const knownAll=F.filter(x=>KNOWN.has(x.status)).length;
 out.G={types:G,rare,rareTotal,rareSaid,total:F.length,known:knownAll};

 /* H: section × lesson heat — distinct forms said (period) */
 const hm=new Map();for(const x of F){for(const l of LP){if(!x.attDays.has(l.day))continue;const v=hm.get(x.topic)||{name:x.topic,cells:new Map(),total:0};v.cells.set(l.day,(v.cells.get(l.day)||0)+1);v.total++;hm.set(x.topic,v);}}
 const secs=[...hm.values()].sort((a,b)=>b.total-a.total||a.name.localeCompare(b.name));
 out.H={sections:secs.slice(0,12),count:secs.length,lessons:LP};

 /* I: days from first exposure to first cold recall (full credit in a later lesson) */
 const I=said.map(x=>{const first=x.expo[0].day,c=x.att.find(a=>a.p===1&&a.day>first);return {x,first,days:c?c.day-first:null,sameDay:x.att.some(a=>a.p===1&&a.day===first)};});
 const crossed=I.filter(o=>o.days!==null),IB=[[0,6,'under 7 d'],[7,13,'7–13 d'],[14,20,'14–20 d'],[21,Infinity,'21 d+']].map(([lo,hi,label])=>({label,count:crossed.filter(o=>o.days>=lo&&o.days<=hi).length}));
 out.I={buckets:IB,crossed:crossed.length,median:median(crossed.map(o=>o.days)),waiting:I.length-crossed.length,sameDayOnly:I.filter(o=>o.days===null&&o.sameDay).length,sameDay:I.filter(o=>o.sameDay).length};
 return out;
}

/* ---------- SVG + HTML helpers (same frame as the Vocab charts) ---------- */
const W=640,H=250,PAD={l:38,r:14,t:18,b:34};
const frame=(inner,label,h=H)=>`<svg class="vp-chart" viewBox="0 0 ${W} ${h}" role="img" aria-label="${esc(label)}">${inner}</svg>`;
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v)));const r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
function grid(y,maxY,fmt=v=>n(v),steps=4){let s='';for(let i=0;i<=steps;i++){const v=maxY*i/steps;s+=`<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text x="${PAD.l-6}" y="${(y(v)+3.5).toFixed(1)}" text-anchor="end">${fmt(Math.round(v*10)/10)}</text>`;}return s;}
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
const side=(big,small)=>`<div class="vp-side"><b>${big}</b>${small}</div>`;
const scope=(p,follows)=>follows?`Follows the time horizon (${HORIZON[p]||p}).`:'';
function panel(id,title,sub,body,{wide=false,sideHtml='',foot='',horizon=''}={}){
 return `<section class="vp-panel ${wide?'va-wide':''}" aria-labelledby="va-h-${id}"><div class="vp-panelhead"><div><span class="va-key">${id.toUpperCase()}</span><h2 id="va-h-${id}">${esc(title)}</h2><p class="ab-sub">${sub}${horizon?` <span class="va-scope">${esc(horizon)}</span>`:''}</p></div>${sideHtml}</div>${body}${foot?`<p class="va-foot">${foot}</p>`:''}</section>`;
}
const row=(name,title,w,label,cls='',nameW='')=>`<div class="va-row"${nameW?` style="--va-name:${nameW}"`:''} title="${esc(title)}"><span class="va-id">${esc(name)}</span><span class="va-track"><i class="${cls}" style="width:${Math.max(0,Math.min(100,w)).toFixed(1)}%"></i></span><span class="va-n">${label}</span></div>`;
function xLabel(i,count,x,y,text){const step=Math.ceil(count/8);return i%step===0||i===count-1?`<text class="vp-lesson-label" x="${x.toFixed(1)}" y="${y}" text-anchor="middle">${esc(text)}</text>`:'';}

/* ---------- panels ---------- */
function pA(d){
 const s=d.A.series;if(!s.length)return empty('Appears after the first scored lesson.');
 const maxY=niceMax(Math.max(...s.map(p=>p.cold),d.A.base||0,4)*1.1),y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/maxY;
 const slot=(W-PAD.l-PAD.r)/s.length,bw=Math.min(36,slot*.66),cx=i=>PAD.l+slot*i+slot/2;
 const b=d.A.base,band=b===null?'':`<rect class="va-band" x="${PAD.l}" y="${y(b*1.5).toFixed(1)}" width="${W-PAD.l-PAD.r}" height="${Math.max(2,y(b*.5)-y(b*1.5)).toFixed(1)}"><title>Baseline: ${(Math.round(b*10)/10)} cold forms, mean of the ${n(d.A.baseN)} lessons in the first two weeks (band ±50%)</title></rect><text class="va-halo" x="${W-PAD.r}" y="${(y(b*1.5)-4).toFixed(1)}" text-anchor="end">baseline ${n(Math.round(b))}, first 2 weeks</text>`;
 const bars=s.map((p,i)=>`<rect class="va-bar ${i>=s.length-4?'va-bar-recent':''}" x="${(cx(i)-bw/2).toFixed(1)}" y="${Math.min(y(p.cold),H-PAD.b-1).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1,H-PAD.b-y(p.cold)).toFixed(1)}" rx="3"><title>${pretty(p.date)}: ${n(p.cold)} forms said cold in the 28 days to this lesson (loose variant ${n(p.loose)})</title></rect>`).join('');
 const last=s.length-1,callout=`<text class="vp-callout" x="${cx(last).toFixed(1)}" y="${(y(s[last].cold)-6).toFixed(1)}" text-anchor="middle">${n(s[last].cold)}</text>`;
 const tp=d.A.trend.map((v,i)=>v===null?null:`${cx(i).toFixed(1)},${y(v).toFixed(1)}`).filter(Boolean);
 const line=tp.length>1?`<polyline class="va-trend" points="${tp.join(' ')}"><title>Four-lesson moving average</title></polyline>`:'';
 const labels=s.map((p,i)=>xLabel(i,s.length,cx(i),H-10,short(p.date))).join('');
 return frame(grid(y,maxY)+band+bars+line+callout+labels,`Forms said cold in the trailing 28 days, across ${s.length} lessons`);
}
function pB(d){
 const b=d.B.buckets;if(!d.B.tries)return empty('No scored tries in this period.');
 const y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/100,slot=(W-PAD.l-PAD.r)/b.length,bw=Math.min(84,slot*.7);
 const bars=b.map((x,i)=>{const cx=PAD.l+slot*i+slot/2;return `<g>${x.n?`<rect class="va-bar ${i===0?'va-bar-accent':''}" x="${(cx-bw/2).toFixed(1)}" y="${y(x.pass).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(x.pass)).toFixed(1)}" rx="3"><title>${esc(x.label)}: ${pct(x.pass)} right of ${n(x.n)} first tries · ${n(x.wrong)} wrong · ${n(x.hinted)} hinted</title></rect><text class="vp-callout" x="${cx.toFixed(1)}" y="${(y(x.pass)-5).toFixed(1)}" text-anchor="middle">${pct(Math.round(x.pass))}</text>`:`<text x="${cx.toFixed(1)}" y="${(H-PAD.b-6).toFixed(1)}" text-anchor="middle">—</text>`}<text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${H-19}" text-anchor="middle">${esc(x.label)}</text><text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${H-7}" text-anchor="middle">n ${n(x.n)}</text></g>`;}).join('');
 return frame(grid(y,100,v=>v+'%')+bars,'Share said right on the first try of the day, by gap since last exposure');
}
function pC(d){
 const s=d.C.series;if(!s.length)return empty('Appears once a form said in one lesson has a later lesson to come back in.');
 const y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/100,kmax=Math.max(...s.map(c=>c.k)),x=k=>PAD.l+12+(W-PAD.l-PAD.r-100)*(kmax===1?.5:(k-1)/(kmax-1));
 const line=s.length>1?`<polyline class="vp-line" points="${s.map(c=>`${x(c.k).toFixed(1)},${y(c.share).toFixed(1)}`).join(' ')}"/>`:'';
 const dots=s.map(c=>`<circle class="vp-dot" cx="${x(c.k).toFixed(1)}" cy="${y(c.share).toFixed(1)}" r="4.5"><title>Within ${c.k} later lesson${c.k>1?'s':''}: ${n(c.hit)} of ${n(c.elig)} (${pct(c.share)})</title></circle><text class="vp-callout" x="${x(c.k).toFixed(1)}" y="${(y(c.share)-9).toFixed(1)}" text-anchor="middle">${pct(Math.round(c.share))}</text><text class="vp-lesson-label" x="${x(c.k).toFixed(1)}" y="${H-10}" text-anchor="middle">${c.k}</text>`).join('');
 return frame(grid(y,100,v=>v+'%')+line+dots+`<text x="${W-PAD.r}" y="${H-10}" text-anchor="end">later lessons →</text>`,'Share of new forms said again within N later lessons');
}
function pD(d){
 const h=d.D.hist,max=Math.max(1,...h.map(x=>x.count));
 if(!d.D.said)return empty('No forms said in this period.');
 const left=h.map(x=>row(x.k,`${n(x.count)} forms said in ${x.k} lesson${x.k==='1'?'':'s'}`,x.count/max*100,`${n(x.count)} forms`,x.k==='1'?'va-fill-warn':'','34px')).join('');
 const right=d.D.top.map(o=>row(o.x.name,o.x.english,o.lessons/Math.max(1,d.D.lessons)*100,`${n(o.lessons)} of ${n(d.D.lessons)} (${n(o.attempts)})`,'va-fill-good','92px')).join('');
 return `<div class="va-two"><div><div class="va-sub">Forms by lessons said in</div>${left}</div><div><div class="va-sub">Most reused · tries in brackets</div>${right||empty('—')}</div></div>`;
}
function pE(d){
 const s=d.E.series;
 let chart;
 if(!s.length)chart=empty('No lessons in this period.');
 else{
  const maxY=niceMax(Math.max(1,...s.map(p=>Math.max(p.heard,p.said)))*1.05),y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/maxY,slot=(W-PAD.l-PAD.r)/s.length,bw=Math.min(20,(slot-6)/2);
  const bars=s.map((p,i)=>{const cx=PAD.l+slot*i+slot/2,x1=cx-bw-1,x2=cx+1;return `<rect class="va-bar" x="${x1.toFixed(1)}" y="${y(p.heard).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(p.heard)).toFixed(1)}" rx="2"><title>${pretty(p.date)}: Amal said ${n(p.heard)} distinct list forms</title></rect><rect class="va-bar-ink" x="${x2.toFixed(1)}" y="${y(p.said).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(p.said)).toFixed(1)}" rx="2"><title>${pretty(p.date)}: you said ${n(p.said)} distinct forms, ${n(p.both)} of them also said by Amal</title></rect><rect class="va-bar-accent-fill" x="${x2.toFixed(1)}" y="${y(p.both).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(p.both)).toFixed(1)}" rx="2"><title>${pretty(p.date)}: ${n(p.both)} forms both of you said</title></rect>${xLabel(i,s.length,cx,H-10,short(p.date))}`;}).join('');
  chart=frame(grid(y,maxY)+bars,`Distinct forms Amal said versus forms you said, across ${s.length} lessons`)+`<div class="va-legend"><span><i class="va-sw-sage"></i>Amal said</span><span><i class="va-sw-ink"></i>you said</span><span><i class="va-sw-accent"></i>both in the same lesson</span></div>`;
 }
 const list=d.E.inputOnly.slice(0,10).map(o=>row(o.x.name,o.x.english,o.lessons/Math.max(1,d.E.lessons)*100,`${n(o.lessons)} lessons (${n(o.times)})`,'va-fill-warn','112px')).join('');
 return `<div class="va-two va-two-e"><div>${chart}</div><div><div class="va-sub">Heard from Amal, never said by you · lessons (times) · all time</div>${list||empty('Every form Amal has said, you have said too.')}</div></div>`;
}
function pF(d){
 const k=d.F.known;if(!k)return empty('No known forms yet.');
 let x=0,s='';
 for(const b of d.F.bands){if(!b.count)continue;const w=b.count/k*W-2;s+=`<rect class="va-seg-${b.cls}" x="${x.toFixed(1)}" y="0" width="${Math.max(2,w).toFixed(1)}" height="22" rx="3"><title>${esc(b.label)} since last said: ${n(b.count)} known forms (${Math.round(b.count/k*100)}%)</title></rect>${w>26?`<text class="va-seg-label" x="${(x+6).toFixed(1)}" y="15">${n(b.count)}</text>`:''}`;x+=w+2;}
 const legend=d.F.bands.filter(b=>b.count||b.lo<35).map(b=>`<span><i class="va-sw-${b.cls}"></i>${esc(b.label)} · ${n(b.count)}</span>`).join('');
 const maxD=Math.max(35,...d.F.list.map(o=>o.days));
 const list=d.F.list.map(o=>row(o.x.name,`${o.x.english} · last said ${pretty(iso(o.last))}`,o.days/maxD*100,`${n(o.days)} d · said ${n(o.count)}×${o.amalSince?' · <b class="va-since">Amal since</b>':''}`,o.days>=21?'va-fill-bad':o.days>=14?'va-fill-warn':'','124px')).join('');
 return `<svg class="vp-chart" viewBox="0 0 ${W} 24" role="img" aria-label="Known forms by days since last said">${s}</svg><div class="va-legend">${legend}</div><div class="va-sub va-gap">Longest silent</div>${list}`;
}
function pG(d){
 const t=d.G.types;if(!t.length)return empty('Vocabulary list not synced.');
 return t.map(g=>{const p=g.said/g.total*100;return row(g.k,`${n(g.said)} of ${n(g.total)} forms ever said`,g.said?Math.max(p,1):0,`${n(g.said)} / ${n(g.total)} · ${Math.round(p)}%`,g.said/g.total<.02?'va-fill-bad':'','150px');}).join('');
}
function pH(d){
 const secs=d.H.sections,ls=d.H.lessons;if(!secs.length||!ls.length)return empty('No forms said in this period.');
 const L=128,T=26,cols=ls.length,gap=cols>20?1:3,cw=(W-L)/cols-gap,ch=18,h=T+secs.length*(ch+3)+24;
 const step=v=>v===0?0:v<3?1:v<6?2:v<10?3:4;let s='';
 secs.forEach((sec,j)=>s+=`<text x="${L-8}" y="${T+j*(ch+3)+13}" text-anchor="end"><title>${esc(sec.name)}: ${n(sec.total)} form-lessons</title>${esc(clip(sec.name,20))}</text>`);
 const every=Math.ceil(cols/8);
 ls.forEach((l,i)=>{const x=L+i*(cw+gap);if(i%every===0||i===cols-1)s+=`<text class="vp-lesson-label" x="${(x+cw/2).toFixed(1)}" y="${T-8}" text-anchor="middle">${short(l.date)}</text>`;
  secs.forEach((sec,j)=>{const v=sec.cells.get(l.day)||0;s+=`<rect class="va-heat-${step(v)}" x="${x.toFixed(1)}" y="${T+j*(ch+3)}" width="${Math.max(1,cw).toFixed(1)}" height="${ch}" rx="3"><title>${pretty(l.date)} · ${esc(sec.name)}: ${n(v)} distinct forms said</title></rect>${v>=10&&cw>=16?`<text class="va-heat-num" x="${(x+cw/2).toFixed(1)}" y="${T+j*(ch+3)+13}" text-anchor="middle">${n(v)}</text>`:''}`;});});
 let lx=L;['0','1–2','3–5','6–9','10+'].forEach((t,i)=>{s+=`<rect class="va-heat-${i}" x="${lx}" y="${h-14}" width="10" height="10" rx="2"/><text x="${lx+14}" y="${h-5}">${t}</text>`;lx+=52;});
 return frame(s,'Distinct forms said per section per lesson',h);
}
function pI(d){
 const b=d.I.buckets;if(!d.I.crossed)return empty('Appears once a form is said right, unaided, in a lesson after the one you first met it in.');
 const H2=200,maxY=niceMax(Math.max(...b.map(x=>x.count))*1.12),y=v=>H2-PAD.b-(H2-PAD.b-PAD.t)*v/maxY,slot=(W-PAD.l-PAD.r)/b.length,bw=Math.min(96,slot*.7);
 const mi=d.I.median===null?-1:b.findIndex((x,i)=>d.I.median<=[6,13,20,Infinity][i]);
 const bars=b.map((x,i)=>{const cx=PAD.l+slot*i+slot/2;return `<rect class="va-bar ${i===mi?'va-bar-accent':''}" x="${(cx-bw/2).toFixed(1)}" y="${y(x.count).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H2-PAD.b-y(x.count)).toFixed(1)}" rx="3"><title>${esc(x.label)}: ${n(x.count)} forms (${Math.round(x.count/d.I.crossed*100)}%)${i===mi?' · the median falls here':''}</title></rect><text class="vp-callout" x="${cx.toFixed(1)}" y="${(y(x.count)-5).toFixed(1)}" text-anchor="middle">${n(x.count)}</text><text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${H2-10}" text-anchor="middle">${esc(x.label)}</text>`;}).join('');
 const gy=v=>y(v);const g=[0,.25,.5,.75,1].map(f=>{const v=maxY*f;return `<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${gy(v).toFixed(1)}" y2="${gy(v).toFixed(1)}"/><text x="${PAD.l-6}" y="${(gy(v)+3.5).toFixed(1)}" text-anchor="end">${n(Math.round(v))}</text>`;}).join('');
 return frame(g+bars,'Forms by days from first exposure to first cold recall',H2);
}

/* ---------- render ---------- */
function host(){
 const tab=$('vp-tab-vocab');if(!tab)return null;
 let el=$('va-root');if(!el){el=document.createElement('div');el.id='va-root';el.className='va-root';tab.append(el);}
 return el;
}
function render(){
 const P=window.AneesVocabularyProgress,el=host();if(!P||!el)return;
 const rows=P.rows,events=P.events||[];
 if(!rows||!rows.length){el.innerHTML='';return;}
 let d;try{d=compute(rows,events,new Date(),P.period);}catch(e){el.innerHTML=`<div class="vp-notice">The new angles could not be computed (${esc(e.message)}). The charts above are unaffected.</div>`;return;}
 const p=d.period,a=d.A,B=d.B,Cc=d.C,D=d.D,E=d.E,F=d.F,G=d.G,Hh=d.H,I=d.I;
 const lastDate=d.L.at(-1)?.date;
 const bFirst=B.buckets[0],bLater=B.buckets.slice(1).filter(x=>x.n),laterPass=bLater.length?[Math.min(...bLater.map(x=>x.pass)),Math.max(...bLater.map(x=>x.pass))]:null;
 const topIn=E.inputOnly[0];
 const exercised=S.exercised?S.exercised(S.forms(rows)).size:G.total-G.rareTotal; // shared helper (vocabulary-stats.js), same figure as the cards
 const rising=Hh.sections.map(s=>{const top=[...s.cells].sort((x,y)=>y[1]-x[1])[0];return top?{name:s.name,day:top[0],v:top[1],lessons:s.cells.size}:null;}).filter(Boolean);
 const spike=rising.slice().sort((x,y)=>y.v-x.v)[0],rarest=rising.slice().sort((x,y)=>x.lessons-y.lessons)[0];
 el.innerHTML=`
 <div class="va-head"><span class="vp-eyebrow">Vocab · nine more angles</span><h2 class="va-h2">New angles</h2><p class="ab-sub">Same reviewed evidence as the charts above, read from new directions. Hover any bar or dot for its counts.</p></div>
 <div class="vp-grid">
 ${panel('a','Words I can say cold, trailing 28 days','A form counts once if you said it right on your first try of the day, 7+ days after you last heard or said it. Band = first two weeks. Dotted = four-lesson trend.',pA(d),{horizon:'All lessons; each bar is its own 28-day window.',sideHtml:a.last?side(n(a.last.cold),`as of ${pretty(a.last.date)}${a.weekAgo?` · ${n(a.weekAgo.cold)} a week earlier`:''}${a.base!==null?` · baseline ${n(Math.round(a.base))}`:''}`):'',foot:`Goes up only when learning happens. Three weekly points over the band = progress.<span>Loose variant (first-ever tries count too, no prior exposure needed): <b>${a.last?n(a.last.loose):'—'}</b></span>`})}
 ${panel('b','Where the slips happen: first sight vs recall','First try of the day per form, grouped by how long since you last heard or said it. Bar = share said right.',pB(d),{horizon:scope(p,true),sideHtml:B.wrong?side(`${n(B.firstWrong)} of ${n(B.wrong)}`,'wrong first tries were first-ever attempts'):side('0','wrong first tries in this period'),foot:laterPass&&bFirst.n?`First ever: ${pct(Math.round(bFirst.pass))} right. After a gap: ${Math.round(laterPass[0])}–${Math.round(laterPass[1])}%.<span>Caveat: you only say what you remember.</span>`:'<span>Caveat: you only say what you remember.</span>'})}
 ${panel('c','Does a new word ever come back?','Of forms first said in a lesson, the share said again within the next N lessons. Only forms with N later lessons available are counted.',pC(d),{horizon:'All lessons.',sideHtml:side(`${n(Cc.once)} of ${n(Cc.said)}`,'forms said in one lesson only'),foot:`${Cc.half?`Half of new forms come back within ${n(Cc.half.k)} lesson${Cc.half.k>1?'s':''}.`:'Fewer than half of new forms have come back yet.'} That gap is the review debt.<span>${n(Cc.stale)} forms: first said 3+ lessons ago, never again</span>`})}
 ${panel('d','Breadth of reuse',`Left: how many distinct lessons each said form appeared in. Right: the forms that travel with you most, lessons out of ${n(D.lessons)}.`,pD(d),{horizon:scope(p,true),foot:`${n(D.wide)} form${D.wide===1?' has':'s have'} shown up in six or more lessons.<span>${n(D.said)} said forms</span>`})}
 ${panel('e','Input vs output: what Amal says vs what you say','Per lesson, distinct list forms Amal spoke (echoes removed) next to distinct forms you attempted. Right: forms she keeps using that you have never said.',pE(d),{wide:true,horizon:'The chart follows the time horizon ('+(HORIZON[p]||p)+'); the list is all time.',foot:`${n(E.inputOnly.length)} forms are input-only.${topIn?` “${esc(topIn.x.name)}” (${esc(topIn.x.english)}) has come up in ${n(topIn.lessons)} of ${n(E.lessons)} lessons and you have never said it.`:''}<span>${n(E.heard)} forms ever heard · ${n(E.said)} ever said · ${n(E.neither)} neither</span>`})}
 ${panel('f','Decay watchlist',`Your ${n(F.known)} known forms by days since you last said them. Below: the longest-silent ones, marked if Amal has said them since.`,pF(d),{horizon:'As of today; ignores the time horizon.',foot:`${F.red?`${n(F.red)} known form${F.red===1?' is':'s are'} 21+ days silent${F.redDates.length&&F.redDates.length<=3?`, last said on ${F.redDates.slice().sort((x,y)=>x-y).map(v=>pretty(iso(v))).join(', ')}`:''}. `:''}${n(F.amalSince)} known forms Amal has used since you last did: free cues you did not take.<span>As of ${pretty(iso(d.today))}</span>`})}
 ${panel('g','Which form types the lessons actually exercise','Each row is one kind of scored form. Filled = ever said by you; the number is said / on the list.',pG(d),{horizon:'All time.',sideHtml:G.rare.length?side(`${n(G.rareTotal)} · ${n(G.rareSaid)} said`,esc(G.rare.map(g=>g.k.split(' · ').pop()).filter((v,i,s)=>s.indexOf(v)===i).join(', '))+' forms, ever'):'',foot:G.rare.length&&G.total?`${Math.round(G.rareTotal/G.total*100)}% of studied forms are slots lessons almost never touch (under 2% said). Words known is ${pct(pc(G.known,G.total))} of all forms; on exercised forms it is ${n(G.known)} of ${n(exercised)} = ${pct(pc(G.known,exercised))}.<span>form label per entry</span>`:'<span>form label per entry</span>'})}
 ${panel('h','Section heat, lesson by lesson','Distinct forms you said per Amal section per lesson. Darker = more. Reads as what each lesson was about.',pH(d),{horizon:scope(p,true),foot:`${spike?`Biggest spike: ${esc(spike.name)}, ${n(spike.v)} forms on ${pretty(iso(spike.day))}.`:''}${rarest&&rarest.lessons<=2?` ${esc(rarest.name)} appeared in ${n(rarest.lessons)} lesson${rarest.lessons>1?'s':''} only.`:''}<span>Top ${n(Hh.sections.length)} of ${n(Hh.count)} sections</span>`})}
 ${panel('i','Time from first exposure to first cold recall','Days between the first time a form was heard or said and the first later lesson where you said it right unaided.',pI(d),{horizon:'All time.',sideHtml:side(I.median===null?'—':`${n(I.median)} days`,I.median===null?'no form has crossed yet':`median · ${n(I.crossed)} forms have crossed the line`),foot:`${n(I.waiting)} forms you have attempted still have no cold recall in a later lesson. That is the drill list.<span>${n(I.sameDayOnly)} of them were said right on the day they were first met</span>`})}
 </div>
 <p class="vp-footer">New angles: computed live from ${n(d.F.length)} studied forms and ${n(d.L.length)} lessons${lastDate?` (last ${pretty(lastDate)})`:''} · heard = Amal's words with echoes removed · said = your scored tries.</p>`;
}
document.addEventListener('anees:vocab-rendered',render);
if(window.AneesVocabularyProgress&&(window.AneesVocabularyProgress.rows||[]).length)render();
window.AneesVocabAngles={compute,render};
})();
