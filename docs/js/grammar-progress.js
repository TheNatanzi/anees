/* Progress & Stats › Grammar tab (Medi 2026-09-27: "let's do all of these").
   Nine angles the Grammar Console does not show, plus time of day.
   Reads docs/data/grammar-console.json (hand-verified corrections = candidates,
   per-lesson counts), docs/data/grammar-usage.json (machine-counted uses) and
   docs/data/lessons.json (start_local, duration_min). Never invents a number:
   anything the files do not carry renders as "—" with the reason. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const f1=v=>v===null||v===undefined||Number.isNaN(v)?'—':(Math.round(v*10)/10).toFixed(1);
const short=d=>{const [,m,dd]=String(d).split('-');return `${Number(m)}/${Number(dd)}`;};
const pretty=d=>{if(!d)return '';const p=d.split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const dayDiff=(a,b)=>{const p=a.split('-').map(Number),q=b.split('-').map(Number);return Math.round((Date.UTC(q[0],q[1]-1,q[2])-Date.UTC(p[0],p[1]-1,p[2]))/86400000);};
const median=a=>{if(!a.length)return null;const s=a.slice().sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;};
const quant=(a,q)=>{if(!a.length)return null;const s=a.slice().sort((x,y)=>x-y);return s[Math.min(s.length-1,Math.floor(q*(s.length-1)))];};
const FAM={A:'Noun phrase',B:'Verb system',C:'Sentence glue',D:'Partner words',E:'Numbers, time'};
const STATUS_COL={Mastered:'var(--ab-green)',Good:'var(--ab-blue)',Shaky:'var(--ab-orange)',Wrong:'var(--ab-red)',Unscored:'var(--ab-muted)',NotTaught:'var(--ab-raised)',Untested:'var(--ab-line)'};
let D=null,loaded=false,loading=null;

/* ---------- data ---------- */
async function json(url){const r=await fetch(url+'?v='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('HTTP '+r.status+' '+url);return r.json();}
async function load(){
 const [console_,usage,lessons]=await Promise.all([json('data/grammar-console.json'),json('data/grammar-usage.json').catch(()=>null),json('data/lessons.json').catch(()=>null)]);
 D=build(console_,usage,lessons);loaded=true;
}
function build(gc,usage,lj){
 const rules=gc.rules||[],byId=new Map(rules.map(r=>[r.id,r]));
 const lessons=(gc.lessons||[]).slice().sort((a,b)=>a.date<b.date?-1:1);
 const dates=lessons.map(l=>l.date),last=dates[dates.length-1];
 const meta=new Map(((lj&&(lj.lessons||lj))||[]).map(l=>[l.date,l]));
 // every hand-verified correction, tagged with its rule
 const cands=[];for(const r of rules)for(const c of r.candidates||[])cands.push(Object.assign({rule:r.id,fam:r.family,name:r.name},c));
 // lesson length: lessons.json duration, else the last timestamp seen in that lesson
 const lastT=new Map();for(const c of cands)lastT.set(c.date,Math.max(lastT.get(c.date)||0,c.t||0));
 if(usage&&usage.uses)for(const k in usage.uses)for(const u of usage.uses[k])lastT.set(u.date,Math.max(lastT.get(u.date)||0,u.t||0));
 const minutes=d=>{const m=meta.get(d);if(m&&m.duration_min)return m.duration_min;const t=lastT.get(d);return t?t/60:null;};

 /* A: corrections per 10 minutes, per lesson; baseline = first 14 days pooled; trend = trailing 4 lessons */
 const per10=lessons.map(l=>{const m=minutes(l.date);return {date:l.date,slips:l.slips_counted||0,min:m,rate:m?(l.slips_counted||0)/(m/10):null,src:meta.get(l.date)&&meta.get(l.date).duration_min?'lessons.json':'last timestamp'};});
 const base=per10.filter(p=>p.min&&dayDiff(dates[0],p.date)<14),baseRate=base.length?base.reduce((s,p)=>s+p.slips,0)/(base.reduce((s,p)=>s+p.min,0)/10):null;
 const tail=per10.filter(p=>p.rate!==null).slice(-4),tailRate=tail.length?tail.reduce((s,p)=>s+p.slips,0)/(tail.reduce((s,p)=>s+p.min,0)/10):null;
 const trend=per10.map((p,i)=>{const w=per10.slice(Math.max(0,i-3),i+1).filter(x=>x.rate!==null);return i>=3&&w.length===4?w.reduce((s,x)=>s+x.slips,0)/(w.reduce((s,x)=>s+x.min,0)/10):null;});

 /* B: corrections by ten-minute block, averaged over lessons that reached the block */
 const blocks=[];for(let b=0;b<8;b++){const reach=lessons.filter(l=>{const m=minutes(l.date);return m&&m*60>b*600;}).length;if(!reach)break;const k=cands.filter(c=>Math.floor((c.t||0)/600)===b).length;blocks.push({b,count:k,reach,avg:k/reach});}
 const fullBlocks=blocks.filter(b=>b.reach>=lessons.length/2),peak=fullBlocks.length?fullBlocks.reduce((a,b)=>b.avg>a.avg?b:a):null;

 /* C: first half vs second half of the lessons, per rule */
 const half=dates[Math.floor(dates.length/2)];
 const movers=rules.map(r=>{const cs=r.candidates||[];const a=cs.filter(c=>c.date<half).length,b=cs.filter(c=>c.date>=half).length;return {id:r.id,name:r.name,a,b,d:b-a};}).filter(m=>m.a+m.b>=6&&m.d!==0);
 const worse=movers.filter(m=>m.d>0).sort((x,y)=>y.d-x.d).slice(0,5),better=movers.filter(m=>m.d<0).sort((x,y)=>x.d-y.d).slice(0,5);

 /* D: exposure (uses, machine-counted) vs corrections, per rule */
 const expo=rules.filter(r=>(r.uses||0)>0).map(r=>({id:r.id,name:r.name,uses:r.uses,mistakes:r.mistakes||0,status:r.status,pct:r.pct}));

 /* E: repeat offenders + clean streaks */
 const lessonsHit=rules.map(r=>({id:r.id,name:r.name,k:new Set((r.candidates||[]).map(c=>c.date)).size})).filter(x=>x.k).sort((x,y)=>y.k-x.k).slice(0,6);
 const streaks=rules.filter(r=>(r.uses||0)>=5&&(r.candidates||[]).length).map(r=>{const lastSlip=(r.candidates||[]).map(c=>c.date).sort().pop();return {id:r.id,name:r.name,days:dayDiff(lastSlip,last),uses:r.uses,lastSlip};}).sort((x,y)=>y.days-x.days).slice(0,6);

 /* F: how Amal corrects */
 const ORDER=[['recast','she re-said it'],['prompt-then-fix','she nudged, then fixed'],['explicit-no','she said no'],['named-rule','she named the rule'],['chat-fix','typed in chat only']];
 const sigCount=new Map();for(const c of cands)sigCount.set(c.signal||'other',(sigCount.get(c.signal||'other')||0)+1);
 const signals=ORDER.map(([k,l])=>({key:k,label:l,count:sigCount.get(k)||0}));
 const other=cands.length-signals.reduce((s,x)=>s+x.count,0);if(other>0)signals.push({key:'other',label:'other',count:other});
 const lat=cands.map(c=>c.recast_t!=null&&c.t!=null?c.recast_t-c.t:null).filter(v=>v!==null&&v>=0&&v<120);
 const chat=cands.filter(c=>c.chat).length;
 // named-rule share, first half vs second half
 const named=(from,to)=>{const s=cands.filter(c=>c.date>=from&&c.date<to);return s.length?s.filter(c=>c.signal==='named-rule').length/s.length:null;};
 const namedA=named('0000',half),namedB=named(half,'9999');

 /* G: rules filed together */
 const pairMap=new Map();for(const c of cands)if(c.bucket2){const k=c.rule+'|'+c.bucket2;pairMap.set(k,(pairMap.get(k)||0)+1);}
 const pairs=[...pairMap].map(([k,v])=>{const [a,b]=k.split('|');return {a,b,v,an:(byId.get(a)||{}).name||'',bn:(byId.get(b)||{}).name||''};}).sort((x,y)=>y.v-x.v).slice(0,8);

 /* H: family × lesson */
 const fams=Object.keys(FAM);
 const heat=lessons.map(l=>({date:l.date,cells:fams.map(f=>cands.filter(c=>c.date===l.date&&c.fam===f).length)}));

 /* J: time of day (lessons.json start_local, lesson clock) vs mistakes per sentence */
 const tod=lessons.map(l=>{const m=meta.get(l.date),s=m&&m.start_local;if(!s)return null;const mt=/T(\d\d):(\d\d)/.exec(s);if(!mt)return null;return {date:l.date,hour:+mt[1]+(+mt[2])/60,clock:mt[1]+':'+mt[2],mps:l.mistakes_per_sentence,slips:l.slips_counted||0,sent:l.medi_sentences||0,src:m.start_source||''};}).filter(Boolean).filter(p=>p.mps!=null);
 let todSplit=null;if(tod.length>=6){const s=tod.slice().sort((a,b)=>a.hour-b.hour),k=Math.floor(s.length/3),early=s.slice(0,k),late=s.slice(-k);const pool=g=>g.reduce((x,p)=>x+p.slips,0)/Math.max(1,g.reduce((x,p)=>x+p.sent,0));todSplit={early:pool(early),late:pool(late),earlyTo:s[k-1].clock,lateFrom:s[s.length-k].clock,k};}

 /* I: next-lesson focus, picked from C, E and G */
 const focus=[];
 if(worse[0]){const w=worse[0],tangle=pairs.find(p=>p.a===w.id||p.b===w.id);focus.push({id:w.id,name:w.name,why:`${n(w.a)} corrections in the first ${n(Math.floor(dates.length/2))} lessons, ${n(w.b)} in the last ${n(dates.length-Math.floor(dates.length/2))}.${tangle?` Tangles with ${tangle.a===w.id?tangle.b:tangle.a}.`:''}`,pill:'Getting worse',cls:'bad'});}
 const hit=lessonsHit.find(x=>!focus.some(f=>f.id===x.id));if(hit){const r=byId.get(hit.id);focus.push({id:hit.id,name:hit.name,why:`Corrected in ${n(hit.k)} of ${n(lessons.length)} lessons. ${n(r.uses)} uses, ${n(r.mistakes)} corrections.`,pill:hit.k===lessons.length?'Never a clean lesson':'Keeps coming back',cls:'warn'});}
 if(better[0]&&!focus.some(f=>f.id===better[0].id)){const b=better[0];focus.push({id:b.id,name:b.name,why:`${n(b.a)} corrections down to ${n(b.b)}.${lessonsHit[0]&&lessonsHit[0].id===b.id?' Still the most-corrected rule overall.':''}`,pill:'Improving, keep it warm',cls:'good'});}

 return {gc,rules,lessons,dates,last,cands,per10,baseRate,tailRate,trend,blocks,peak,half,worse,better,expo,lessonsHit,streaks,signals,lat,chat,namedA,namedB,pairs,heat,fams,tod,todSplit,focus,coverage:gc.coverage||{},statusCounts:rules.reduce((m,r)=>(m[r.status]=(m[r.status]||0)+1,m),{})};
}

/* ---------- SVG helpers (same frame as the Vocab tab) ---------- */
const W=640,H=250,PAD={l:38,r:14,t:18,b:34};
const frame=(inner,label,h=H)=>`<svg class="vp-chart" viewBox="0 0 ${W} ${h}" role="img" aria-label="${esc(label)}">${inner}</svg>`;
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v)));const r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
function grid(y,maxY,fmt=v=>n(v),steps=4){let s='';for(let i=0;i<=steps;i++){const v=maxY*i/steps;s+=`<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text x="${PAD.l-6}" y="${(y(v)+3.5).toFixed(1)}" text-anchor="end">${fmt(v)}</text>`;}return s;}
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
const panel=(id,title,sub,body,{wide=false,side='',foot=''}={})=>`<section class="vp-panel ${wide?'fp-wide':''}" aria-labelledby="gp-h-${id}"><div class="vp-panelhead"><div><span class="gp-key">${id.toUpperCase()}</span><h2 id="gp-h-${id}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div>${side}</div>${body}${foot?`<p class="gp-foot">${foot}</p>`:''}</section>`;

/* ---------- panels ---------- */
function perTen(d){
 const s=d.per10;if(!s.some(p=>p.rate!==null))return empty('Needs lesson lengths (lessons.json) to divide by time.');
 const maxY=niceMax(Math.max(...s.map(p=>p.rate||0),d.baseRate||0)*1.1);const y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/maxY;
 const slot=(W-PAD.l-PAD.r)/s.length,bw=Math.min(40,slot*.62);const cx=i=>PAD.l+slot*i+slot/2;
 const band=d.baseRate===null?'':`<rect class="gp-band" x="${PAD.l}" y="${y(d.baseRate*1.15).toFixed(1)}" width="${W-PAD.l-PAD.r}" height="${(y(d.baseRate*.85)-y(d.baseRate*1.15)).toFixed(1)}"/><text x="${W-PAD.r}" y="${(y(d.baseRate*1.15)-4).toFixed(1)}" text-anchor="end">baseline ${f1(d.baseRate)}</text>`;
 const bars=s.map((p,i)=>p.rate===null?'':`<rect class="gp-bar ${i>=s.length-4?'gp-bar-recent':''}" x="${(cx(i)-bw/2).toFixed(1)}" y="${y(p.rate).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(p.rate)).toFixed(1)}" rx="3"><title>${p.date}: ${f1(p.rate)} per 10 min · ${n(p.slips)} corrections in ${n(Math.round(p.min))} min (${p.src})</title></rect>`).join('');
 const tp=d.trend.map((v,i)=>v===null?null:`${cx(i).toFixed(1)},${y(v).toFixed(1)}`).filter(Boolean);
 const line=tp.length>1?`<polyline class="gp-trend" points="${tp.join(' ')}"/>`:'';
 const step=Math.ceil(s.length/8),labels=s.map((p,i)=>i%step===0||i===s.length-1?`<text class="vp-lesson-label" x="${cx(i).toFixed(1)}" y="${H-10}" text-anchor="middle">${short(p.date)}</text>`:'').join('');
 return frame(grid(y,maxY,v=>f1(v))+band+bars+line+labels,`Corrections per ten minutes across ${s.length} lessons`);
}
function fatigue(d){
 const b=d.blocks;if(!b.length)return empty('Needs the time of each correction inside the lesson.');
 const maxY=niceMax(Math.max(...b.map(x=>x.avg))*1.15);const y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/maxY;
 const slot=(W-PAD.l-PAD.r)/b.length,bw=Math.min(64,slot*.7);
 const bars=b.map((x,i)=>{const cx=PAD.l+slot*i+slot/2,partial=x.reach<d.lessons.length/2,peak=d.peak&&x.b===d.peak.b;return `<g><rect class="gp-bar ${peak?'gp-bar-peak':''} ${partial?'gp-bar-partial':''}" x="${(cx-bw/2).toFixed(1)}" y="${y(x.avg).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(x.avg)).toFixed(1)}" rx="3"><title>Minute ${x.b*10}–${x.b*10+10}: ${f1(x.avg)} corrections per lesson · ${n(x.count)} in ${n(x.reach)} lessons</title></rect>${peak?`<text class="vp-callout" x="${cx.toFixed(1)}" y="${(y(x.avg)-7).toFixed(1)}" text-anchor="middle">${f1(x.avg)}</text>`:''}${partial?`<text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${(y(x.avg)-7).toFixed(1)}" text-anchor="middle">${n(x.reach)} lessons</text>`:''}<text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${H-10}" text-anchor="middle">min ${x.b*10}–${x.b*10+10}</text></g>`;}).join('');
 return frame(grid(y,maxY,v=>f1(v))+bars,`Corrections by ten-minute block of the lesson`);
}
function movers(d){
 const rows=d.worse.concat(d.better);if(!rows.length)return empty('Appears once a rule has 6 corrections and moved between the two halves.');
 const L=170,R=150,pw=W-L-R,h=Math.max(200,rows.length*26+40),T=26,B=14,ph=h-T-B,maxV=Math.max(...rows.map(r=>Math.max(r.a,r.b)),1);
 const y=v=>T+ph-v/maxV*ph;
 const spread=items=>{items.sort((p,q)=>p.y-q.y);for(let i=1;i<items.length;i++)if(items[i].y-items[i-1].y<13)items[i].y=items[i-1].y+13;return items;};
 const left=spread(rows.map(r=>({r,y:y(r.a)}))),right=spread(rows.map(r=>({r,y:y(r.b)})));
 const nA=Math.floor(d.dates.length/2),nB=d.dates.length-nA;
 let s=`<text class="vp-callout" x="${L}" y="12" text-anchor="middle">first ${nA} lessons</text><text class="vp-callout" x="${L+pw}" y="12" text-anchor="middle">last ${nB}</text><line class="vp-axis" x1="${L}" x2="${L}" y1="${T}" y2="${T+ph}"/><line class="vp-axis" x1="${L+pw}" x2="${L+pw}" y1="${T}" y2="${T+ph}"/>`;
 for(const r of rows){const cls=r.d>0?'gp-worse':'gp-better';s+=`<g class="${cls}"><line x1="${L}" y1="${y(r.a).toFixed(1)}" x2="${L+pw}" y2="${y(r.b).toFixed(1)}"/><circle cx="${L}" cy="${y(r.a).toFixed(1)}" r="4"/><circle cx="${L+pw}" cy="${y(r.b).toFixed(1)}" r="4"/><title>${r.id} ${esc(r.name)}: ${n(r.a)} → ${n(r.b)}</title></g>`;}
 const clip=t=>t.length>24?t.slice(0,23)+'…':t;
 for(const o of left)s+=`<text class="gp-mover-label" x="${L-10}" y="${(o.y+4).toFixed(1)}" text-anchor="end">${n(o.r.a)}  ${esc(o.r.id)} ${esc(clip(o.r.name))}</text>`;
 for(const o of right)s+=`<text class="vp-callout gp-mover-label" x="${L+pw+10}" y="${(o.y+4).toFixed(1)}">${n(o.r.b)}  ${esc(o.r.id)}</text>`;
 return frame(s,'Corrections per rule, first half versus second half',h);
}
function exposure(d){
 const p=d.expo;if(!p.length)return empty('Needs rule uses (grammar-usage.json).');
 const mx=niceMax(Math.max(...p.map(x=>x.uses))),my=niceMax(Math.max(...p.map(x=>x.mistakes)));
 const x=v=>PAD.l+(W-PAD.l-PAD.r)*v/mx,y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/my;
 let s=grid(y,my)+[0,.25,.5,.75,1].map(f=>`<text x="${x(mx*f).toFixed(1)}" y="${H-10}" text-anchor="middle">${n(Math.round(mx*f))}</text>`).join('')+`<text x="${W-PAD.r}" y="${H-22}" text-anchor="end">uses →</text><text x="${PAD.l+4}" y="${PAD.t-4}">↑ corrections</text>`;
 const label=new Set(p.slice().sort((a,b)=>b.uses-a.uses).slice(0,5).concat(p.slice().sort((a,b)=>b.mistakes-a.mistakes).slice(0,5)).map(r=>r.id));
 for(const r of p)s+=`<g><circle class="gp-pt" cx="${x(r.uses).toFixed(1)}" cy="${y(r.mistakes).toFixed(1)}" r="6" style="fill:${STATUS_COL[r.status]||'var(--ab-muted)'}"><title>${r.id} ${esc(r.name)}: ${n(r.uses)} uses, ${n(r.mistakes)} corrections · ${r.pct==null?'unscored':r.pct+'% right'} · ${r.status}</title></circle>${label.has(r.id)?`<text class="vp-callout" x="${(x(r.uses)+9).toFixed(1)}" y="${(y(r.mistakes)+4).toFixed(1)}">${esc(r.id)}</text>`:''}</g>`;
 return frame(s,'Uses versus corrections per rule');
}
const barRow=(id,name,w,label,cls)=>`<div class="gp-row" title="${esc(name)}"><span class="gp-id">${esc(id)}</span><span class="gp-track"><i class="${cls}" style="width:${Math.max(2,Math.min(100,w))}%"></i></span><span class="gp-n">${label}</span></div>`;
function offenders(d){
 const L=d.lessons.length;
 return `<div class="gp-two"><div><div class="gp-sub">Lessons with a correction, of ${n(L)}</div>${d.lessonsHit.length?d.lessonsHit.map(x=>barRow(x.id,x.name,x.k/L*100,`${n(x.k)} of ${n(L)}`,'gp-fill-bad')).join(''):empty('No corrections yet.')}</div>
 <div><div class="gp-sub">Days clean since the last correction · uses in brackets</div>${d.streaks.length?d.streaks.map(x=>barRow(x.id,x.name+' · last corrected '+pretty(x.lastSlip),x.days/Math.max(1,d.streaks[0].days)*100,`${n(x.days)} d (${n(x.uses)})`,'gp-fill-good')).join(''):empty('Appears once a rule with 5 uses has gone a lesson without a correction.')}</div></div>`;
}
function howAmal(d){
 const total=d.cands.length;if(!total)return empty('No hand-checked corrections yet.');
 const ramp=['gp-seg-1','gp-seg-2','gp-seg-3','gp-seg-4','gp-seg-5','gp-seg-6'];let x=0,s='';
 d.signals.forEach((g,i)=>{if(!g.count)return;const w=g.count/total*W-2;s+=`<rect class="${ramp[i]}" x="${x.toFixed(1)}" y="0" width="${Math.max(2,w).toFixed(1)}" height="22" rx="3"><title>${esc(g.label)}: ${n(g.count)} (${Math.round(g.count/total*100)}%)</title></rect>`;if(w>40)s+=`<text class="gp-seg-label ${i>=2?'gp-seg-label-light':''}" x="${(x+6).toFixed(1)}" y="15">${Math.round(g.count/total*100)}%</text>`;x+=w+2;});
 const legend=d.signals.filter(g=>g.count).map((g,i)=>`<span><i class="${ramp[d.signals.indexOf(g)]}"></i>${esc(g.label)} ${n(g.count)}</span>`).join('');
 const lat=d.lat.length?`<b>${f1(median(d.lat))} s</b>median · half within ${f1(quant(d.lat,.25))} to ${f1(quant(d.lat,.75))} s`:'<b>—</b>no fix times recorded';
 const trendNamed=d.namedA!==null&&d.namedB!==null?`Named the rule: ${Math.round(d.namedA*100)}% of corrections in the first half, ${Math.round(d.namedB*100)}% in the second.`:'';
 return `<svg class="vp-chart gp-stack" viewBox="0 0 ${W} 24" role="img" aria-label="How corrections were delivered">${s}</svg><div class="gp-legend">${legend}</div>
 <div class="gp-two gp-stats"><div><div class="gp-sub">Time to her fix</div><div class="gp-big">${lat}</div></div><div><div class="gp-sub">Also typed in the Meet chat</div><div class="gp-big"><b>${Math.round(d.chat/total*100)}%</b>${n(d.chat)} of ${n(total)} corrections</div></div></div>${trendNamed?`<p class="ab-sub">${trendNamed}</p>`:''}`;
}
function tangles(d){
 if(!d.pairs.length)return empty('Appears when the sweep files a correction under two rules at once.');
 const max=d.pairs[0].v;
 return d.pairs.map(p=>`<div class="gp-row gp-row-pair"><span class="gp-id">${esc(p.a)} + ${esc(p.b)}</span><span class="gp-track"><i class="gp-fill" style="width:${p.v/max*100}%"></i></span><span class="gp-n">${n(p.v)} · ${esc(p.an)} ↔ ${esc(p.bn)}</span></div>`).join('');
}
function heat(d){
 const L=110,T=26,rows=d.fams.length,cols=d.heat.length;if(!cols)return empty('No scored lessons yet.');
 const cw=(W-L)/cols-3,ch=22,h=T+rows*(ch+3)+30;
 const step=v=>v===0?0:v<5?1:v<10?2:v<20?3:4;let s='';
 d.fams.forEach((f,j)=>s+=`<text x="${L-8}" y="${T+j*(ch+3)+15}" text-anchor="end">${esc(f)} · ${esc(FAM[f])}</text>`);
 d.heat.forEach((l,i)=>{const x=L+i*(cw+3);if(i%2===0||i===cols-1)s+=`<text class="vp-lesson-label" x="${(x+cw/2).toFixed(1)}" y="${T-8}" text-anchor="middle">${short(l.date)}</text>`;
  l.cells.forEach((v,j)=>{s+=`<rect class="gp-heat gp-heat-${step(v)}" x="${x.toFixed(1)}" y="${T+j*(ch+3)}" width="${cw.toFixed(1)}" height="${ch}" rx="3"><title>${l.date} · ${FAM[d.fams[j]]}: ${n(v)} corrections</title></rect>${v>=20?`<text class="gp-heat-num" x="${(x+cw/2).toFixed(1)}" y="${T+j*(ch+3)+15}" text-anchor="middle">${n(v)}</text>`:''}`;});});
 let lx=L;['0','1–4','5–9','10–19','20+'].forEach((t,i)=>{s+=`<rect class="gp-heat gp-heat-${i}" x="${lx}" y="${h-16}" width="10" height="10" rx="2"/><text x="${lx+14}" y="${h-7}">${t}</text>`;lx+=52;});
 return frame(s,'Corrections per family per lesson',h);
}
function timeOfDay(d){
 const p=d.tod;if(!p.length)return empty('No lesson start times yet (lessons.json start_local).');
 const hs=p.map(x=>x.hour),lo=Math.floor(Math.min(...hs)),hi=Math.ceil(Math.max(...hs)),span=Math.max(hi-lo,1);
 const my=niceMax(Math.max(...p.map(x=>x.mps))*1.1);
 const x=v=>PAD.l+(W-PAD.l-PAD.r)*(v-lo)/span,y=v=>H-PAD.b-(H-PAD.b-PAD.t)*v/my;
 let s=grid(y,my,v=>(Math.round(v*100)/100).toFixed(2));
 for(let hh=lo;hh<=hi;hh++)s+=`<text x="${x(hh).toFixed(1)}" y="${H-10}" text-anchor="middle">${hh}:00</text>`;
 s+=`<text x="${W-PAD.r}" y="${H-22}" text-anchor="end">lesson start, local →</text><text x="${PAD.l+4}" y="${PAD.t-4}">↑ mistakes per sentence</text>`;
 for(const q of p)s+=`<circle class="gp-pt gp-pt-tod" cx="${x(q.hour).toFixed(1)}" cy="${y(q.mps).toFixed(1)}" r="6"><title>${q.date} · started ${q.clock} · ${q.mps.toFixed(3)} mistakes per sentence (${n(q.slips)} in ${n(q.sent)}) · ${esc(q.src)}</title></circle>`;
 return frame(s,'Lesson start time versus mistakes per sentence');
}
function focus(d){
 if(!d.focus.length)return empty('Appears once there are corrections to pick from.');
 return `<div class="gp-focus">${d.focus.map(f=>`<div class="gp-fcard"><div class="gp-fid">${esc(f.id)}</div><div class="gp-fname">${esc(f.name)}</div><div class="gp-fwhy">${esc(f.why)}</div><span class="gp-pill gp-pill-${f.cls}">${esc(f.pill)}</span></div>`).join('')}</div>`;
}

/* ---------- render ---------- */
function render(){
 const host=$('vp-tab-grammar');if(!host)return;
 if(!loaded){host.innerHTML='<div class="vp-notice">Loading the grammar evidence…</div>';return;}
 const d=D,c=d.coverage,sc=d.statusCounts,total=d.rules.length;
 const strip=['Mastered','Good','Shaky','Wrong'].map(k=>`<i style="width:${(sc[k]||0)/total*100}%;background:${STATUS_COL[k]}" title="${n(sc[k]||0)} ${k}"></i>`).join('')+`<i style="width:${((sc.Unscored||0)+(sc.Untested||0))/total*100}%;background:var(--ab-line)" title="${n((sc.Unscored||0)+(sc.Untested||0))} unscored or untested"></i>`+`<i style="width:${(sc.NotTaught||0)/total*100}%;background:var(--ab-raised)" title="${n(sc.NotTaught||0)} not taught yet (the tutor)"></i>`;
 const sentences=d.lessons.reduce((s,l)=>s+(l.medi_sentences||0),0),slips=d.lessons.reduce((s,l)=>s+(l.slips_counted||0),0);
 const tail4=d.per10.filter(p=>p.rate!==null).slice(-4).length;
 const tod=d.tod,todNote=tod.length?(()=>{const hs=tod.map(t=>t.clock).sort();const spanH=(Math.max(...tod.map(t=>t.hour))-Math.min(...tod.map(t=>t.hour)));return spanH<2?`All ${n(tod.length)} lessons started between ${hs[0]} and ${hs[hs.length-1]}. That window is too narrow to test the "earlier is better" theory; book one morning lesson and this chart will answer it.`:d.todSplit?`Earliest third (up to ${d.todSplit.earlyTo}): ${d.todSplit.early.toFixed(3)} mistakes per sentence · latest third (from ${d.todSplit.lateFrom}): ${d.todSplit.late.toFixed(3)}.`:'';})():'';
 host.innerHTML=`
 <a class="gp-strip" href="grammar.html" title="Open the Grammar Console">
  <div><div class="gp-sub">Grammar Console · one-line summary</div><div class="gp-kv"><span><b>${n(total)}</b>rules</span><span><b>${n(d.cands.length)}</b>corrections, hand-checked</span><span><b>${n(d.lessons.length)}</b>lessons</span><span><b>${sentences?'1 in '+Math.round(sentences/Math.max(1,slips)):'—'}</b>sentences corrected</span></div><div class="gp-statusbar" aria-label="Rule status mix">${strip}</div><small>${n(sc.Mastered||0)} mastered · ${n(sc.Good||0)} good · ${n(sc.Shaky||0)} shaky · ${n(sc.Wrong||0)} wrong · ${n((sc.Unscored||0)+(sc.Untested||0))} unscored or untested${sc.NotTaught?` · ${n(sc.NotTaught)} not taught yet (${d.rules.filter(r=>r.status==='NotTaught').map(r=>r.id).join(', ')}, no score, out of every total)`:''}. Mistakes per sentence, self-correction, unique rules and the rule table live on the Grammar Console.</small></div>
  <span class="gp-open">Open →</span></a>
 <div class="vp-grid">
 ${panel('a','Corrections per 10 minutes','Same corrections, measured against the clock instead of sentence count. Band = your first two weeks. Dotted line = trailing four lessons.',perTen(d),{side:`<div class="vp-side"><b>${f1(d.tailRate)}</b>last ${n(tail4)} lessons · baseline ${f1(d.baseRate)}</div>`,foot:'Progress is called only when three weekly points sit under the band.'})}
 ${panel('b','When in the lesson you slip','Corrections per lesson in each ten-minute block, averaged over the lessons that reached that block.',fatigue(d),{side:d.peak?`<div class="vp-side"><b>min ${d.peak.b*10}–${d.peak.b*10+10}</b>peak · ${f1(d.peak.avg)} per lesson${d.blocks[0]&&d.blocks[0].avg?` · ${(d.peak.avg/d.blocks[0].avg).toFixed(1)}× the opening block`:''}</div>`:'',foot:'Faded bars: fewer than half the lessons ran that long.'})}
 ${panel('c','Movers: first half vs second half','Corrections per rule, split at '+pretty(d.half)+'. Green went down, red went up. Flat rules left out.',movers(d),{foot:'The rule table shows a score. This shows direction. Rules with 6+ corrections.'})}
 ${panel('d','Exposure vs errors','How often you exercise a rule against how often the tutor corrects it. Colour = the rule’s status on the Grammar Console.',exposure(d),{side:`<div class="vp-legend">${['Mastered','Good','Shaky','Wrong','Unscored'].map(k=>`<span style="color:${STATUS_COL[k]}">● ${k}</span>`).join('')}</div>`,foot:'Top-right is where drilling pays off. Bottom-left is rules you avoid. Uses are machine-counted, right or wrong.'})}
 ${panel('e','Repeat offenders and clean streaks','Left: rules corrected in the most lessons. Right: how long a rule you still use has gone without a correction.',offenders(d),{foot:`A streak that breaks is the signal to bring a rule back into drills. Counted to the last lesson, ${pretty(d.last)}.`})}
 ${panel('f','How the tutor corrects you','Lightest touch on the left, heaviest on the right. Plus how fast she steps in.',howAmal(d),{foot:'A rising “named the rule” share means she trusts you to know it.'})}
 ${panel('g','Rules that tangle together','Corrections the sweep filed under two rules at once. Each pair is one confusion, not two mistakes.',tangles(d),{foot:'Drill a tangled pair as one set.'})}
 ${panel('h','Family heat, lesson by lesson','Corrections per family per lesson. Darker = more. A fingerprint of what each lesson was about.',heat(d),{foot:'Family F (sounds) never counts as grammar.'})}
 ${panel('j','Time of day','Your theory: earlier lessons go better. Each dot is a lesson at its start time (lesson clock) against mistakes per sentence.',timeOfDay(d),{foot:todNote})}
 ${panel('i','Next lesson focus','Three rules picked from C, E and G. One card the tutor can read in ten seconds before the call.',focus(d),{wide:true,foot:'Picking rule: the fastest-worsening rule, the rule corrected in the most lessons, the most-improved rule to keep warm.'})}
 </div>
 <p class="vp-footer">Corrections: ${n(d.cands.length)} hand-verified (sweep of 2026-09-24, rule M1) · uses machine-counted · lesson lengths and start times from lessons.json · grammar-console.json updated ${esc(d.gc.updated||'')}</p>`;
 document.dispatchEvent(new CustomEvent('anees:grammar-rendered'));   // progress-sure.js re-appends "How sure are these numbers?" (2026-09-28)
}
function show(){
 if(!loaded){render();loading=loading||load().then(render).catch(e=>{const h=$('vp-tab-grammar');if(h)h.innerHTML=`<div class="vp-notice">The grammar evidence could not load (${esc(e.message)}). Refresh to retry.</div>`;});}
 else render();
}
window.AneesGrammarProgress={show,reload:async()=>{loaded=false;loading=null;await load();render();},get data(){return D;}};
})();
