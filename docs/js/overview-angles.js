/* Progress & Stats › Overview › "New angles" (Medi 2026-09-27: approved "all of these").
   Panels A–H from the mockup overview-stats-proposal.html, logic from ov_analysis.py:
   A lessons per week · B weekly pooled words vs baseline · C time of day · D rest days ·
   E who talks when · F language mix · G longest no-English stretch · H filled pauses by block.
   Reads docs/data/lessons.json and docs/data/lessons/<date>.json (turns). Every number is
   computed here at runtime; anything the files do not carry renders "—" with the reason. */
(function(){
'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ok=v=>v!==null&&v!==undefined&&!Number.isNaN(Number(v));
const f1=v=>ok(v)?(Math.round(v*10)/10).toFixed(1):'—';
const r0=v=>ok(v)?String(Math.round(v)):'—';
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DAY=864e5;
const utc=d=>{const [y,m,dd]=String(d).split('-').map(Number);return Date.UTC(y,m-1,dd);};
const iso=t=>new Date(t).toISOString().slice(0,10);
const dm=d=>{const [,m,dd]=String(d).split('-').map(Number);return `${dd} ${MON[m-1]}`;};
const dayDiff=(a,b)=>Math.round((utc(b)-utc(a))/DAY);
const monday=d=>{const t=utc(d);return t-((new Date(t).getUTCDay()+6)%7)*DAY;};
const hm=m=>`${Math.floor(m/60)}:${String(Math.round(m%60)).padStart(2,'0')}`;
const mmss=s=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
const median=a=>{if(!a.length)return null;const s=a.slice().sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;};
const sum=(a,f)=>a.reduce((s,x)=>s+(f?f(x):x),0);
const trim0=s=>String(s).replace(/\.0$/,'');
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v)));const r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
const TYPE={'free-speak':'free speak','new-words':'new words','new-grammar':'new grammar','review-words':'review'};
const tcls=t=>TYPE[t]?'ov2-t-'+t:'ov2-t-other';
const plural=(n,w)=>`${n} ${w}${n===1?'':'s'}`;
const pooledWords=ls=>{const s=sum(ls,l=>(l.words&&l.words.scored)||0);return s?sum(ls,l=>((l.words&&l.words.right)||0)+((l.words&&l.words.partial)||0)/2)/s*100:null;};
const slips10=ls=>{const m=sum(ls,l=>l.duration_min||0);return m&&ls.every(l=>l.grammar&&ok(l.grammar.mistakes))?sum(ls,l=>l.grammar.mistakes)/m*10:null;};
const TARGET=[3,4];        // lessons a week Medi and Amal agreed on (mockup A)
const STRETCH_TARGET=5;    // minutes: "stay in Arabic for 5 minutes" (mockup G)
let LJ=null,TURNS=null,turnFail=false;

/* ---------- turn classification (same rules as scratchpad/ov_analysis.py) ---------- */
const AR=/[\u0600-\u06FF]/;
const EN=new Set('the i you it is so yeah okay that what like and to of in a my we he she they this was are but do not no yes have can just because think know right oh'.split(' '));
const FILL=/(?<![\p{L}\p{N}_])(?:uh|um|umm|er|eh|mm|mmm|hmm|ah)(?![\p{L}\p{N}_])|آآ+|امم+|ممم+|ام(?![\p{L}\p{N}_])/giu;
const words=t=>(String(t).match(/[\p{L}\p{N}_\u0600-\u06FF']+/gu)||[]).filter(w=>!/^\p{Nd}+$/u.test(w));
const kind=t=>{if(AR.test(t))return 'ar';const ws=words(t).map(w=>w.toLowerCase());if(!ws.length)return 'none';const en=ws.filter(w=>EN.has(w)).length;return en>=1&&en/ws.length>=.15?'en':'lat';};
const fillers=t=>window.AneesLessonMath?window.AneesLessonMath.countFillers(t):(String(t).match(FILL)||[]).length;   // the builder's own test (docs/js/lesson-math.js), eng audit 2026-09-29

function perLesson(l,J){
 const T=[];
 for(const t of J.turns||[]){
  if(t.who!=='Medi'&&t.who!=='Amal')continue;
  const txt=String(t.text||'').replace(/\(pause [\d.]+s\)/g,'').trim();if(!txt)continue;
  const dur=Math.max(0,(t.end!==null&&t.end!==undefined?t.end:t.t+.5)-t.t);
  T.push({who:t.who,t:t.t,dur,txt,k:t.who==='Medi'?kind(txt):null});
 }
 if(!T.length)return null;
 const medi=T.filter(t=>t.who==='Medi');
 const win=(l.talk&&l.talk.window)||[0,Infinity],end=Math.max(...T.map(t=>t.t)),nb=Math.floor(end/600)+1,blocks=[];
 for(let b=0;b<nb;b++){
  const b0=b*600,b1=b0+600;if(b1<=win[0]||b0>=win[1])continue;
  const ov=who=>sum(T.filter(t=>t.who===who&&t.t<b1&&t.t+t.dur>b0),t=>Math.min(t.t+t.dur,b1)-Math.max(t.t,b0));
  const ms=ov('Medi'),as=ov('Amal');if(ms+as<60)continue;
  blocks.push({b,ms,as,fill:sum(medi.filter(t=>t.t>=b0&&t.t<b1),t=>fillers(t.txt))});
 }
 const msec=sum(medi,t=>t.dur)||1,by=k=>medi.filter(t=>t.k===k);
 const arw=by('ar').map(t=>words(t.txt).filter(w=>AR.test(w)).length);
 // longest run of Medi turns without an English turn (time from its first turn's start to its last turn's end)
 let best={s:0,at:null,n:0},rs=null,last=null,n=0;
 for(const t of medi){
  if(t.k==='en'){if(rs!==null&&last!==null&&last-rs>best.s)best={s:last-rs,at:rs,n};rs=null;n=0;continue;}
  if(rs===null)rs=t.t;last=t.t+t.dur;n++;
 }
 if(rs!==null&&last!==null&&last-rs>best.s)best={s:last-rs,at:rs,n};
 const enSec=sum(by('en'),t=>t.dur);
 return {date:l.date,type:l.type,blocks,ar:by('ar').length,lat:by('lat').length,en:by('en').length,msec,enSec,enShare:enSec/msec*100,
  medArw:median(arw),stretch:best,turnFill:sum(medi,t=>fillers(t.txt)),medi:(J.turns||[]).filter(t=>t.who==='Medi')};
}

/* ---------- SVG helpers (same frame as the Grammar tab) ---------- */
const W=640;
const frame=(inner,label,h,w=W)=>`<svg class="vp-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${inner}</svg>`;
const hline=(x1,x2,y)=>`<line class="vp-gridline" x1="${x1}" x2="${x2}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
const tx=(x,y,t,a='',cls='')=>`<text${cls?` class="${cls}"`:''} x="${(+x).toFixed(1)}" y="${(+y).toFixed(1)}"${a?` text-anchor="${a}"`:''}>${esc(t)}</text>`;
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
const big=(v,s)=>`<div class="ov2-big">${esc(v)}<small>${s}</small></div>`;
const panel=(key,title,sub,body,{wide=false,head='',why='',src=''}={})=>`<section class="vp-panel ${wide?'ov2-wide':''}" aria-labelledby="ov2-h-${key}"><div class="vp-panelhead"><div><span class="ov2-key">${key.toUpperCase()}</span><h2 id="ov2-h-${key}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div></div>${head}${body}${why||src?`<p class="ov2-foot"><span class="ov2-why">${why}</span>${src?`<span class="ov2-src">${esc(src)}</span>`:''}</p>`:''}</section>`;
const loadingTurns=()=>turnFail?empty('The turn files could not load. Refresh to retry.'):empty('Loading the turn files…');

/* ---------- A: lessons per week ---------- */
function panelA(ls){
 const title='Showing up: lessons per week',sub='One square per lesson day, one bar per week. Band = the 3 to 4 lessons a week you and Amal agreed on.';
 if(!ls.length)return panel('a',title,sub,empty('No lessons yet.'));
 const now=new Date(),today=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
 const first=monday(ls[0].date),lastW=monday(ls[ls.length-1].date),weeks=[];
 for(let t=first;t<=lastW;t+=7*DAY)weeks.push({t,key:iso(t),days:[],n:0,open:iso(t+6*DAY)>=today});
 for(const l of ls){const w=weeks[Math.round((monday(l.date)-first)/(7*DAY))];w.days.push((new Date(utc(l.date)).getUTCDay()+6)%7);w.n++;}
 const full=weeks.filter(w=>!w.open),base=full.length?full:weeks,avg=sum(base,w=>w.n)/base.length;
 const inBand=full.filter(w=>w.n>=TARGET[0]&&w.n<=TARGET[1]).length,top=weeks.reduce((a,w)=>w.n>a.n?w:a);
 let gap={d:0};for(let i=1;i<ls.length;i++){const d=dayDiff(ls[i-1].date,ls[i].date);if(d>gap.d)gap={d,a:ls[i-1].date,b:ls[i].date};}
 const show=weeks.slice(-10),L=58,T=26,cell=20,gc=4,cal=7*(cell+gc),bx=L+cal+28,bw=W-bx-60,maxN=Math.max(7,...show.map(w=>w.n)),h=T+show.length*(cell+gc)+22;
 let s='';['M','T','W','T','F','S','S'].forEach((d,i)=>s+=tx(L+i*(cell+gc)+cell/2,T-9,d,'middle'));
 const x0=bx+TARGET[0]/maxN*bw,x1=bx+TARGET[1]/maxN*bw;
 s+=`<rect class="ov2-band" x="${x0.toFixed(1)}" y="${T-5}" width="${(x1-x0).toFixed(1)}" height="${show.length*(cell+gc)+1}"/>`+tx((x0+x1)/2,T-9,`${TARGET[0]} to ${TARGET[1]}`,'middle');
 show.forEach((w,r)=>{
  const y=T+r*(cell+gc);s+=tx(L-8,y+cell/2+4,dm(w.key),'end');
  for(let d=0;d<7;d++){const on=w.days.includes(d);s+=`<rect class="${on?'ov2-cell-on':'ov2-cell'}" x="${L+d*(cell+gc)}" y="${y}" width="${cell}" height="${cell}" rx="4">${on?`<title>Lesson · ${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d]} ${dm(iso(w.t+d*DAY))}</title>`:''}</rect>`;}
  const col=w.n>=TARGET[0]&&w.n<=TARGET[1]?'ov2-f-good':w.n>TARGET[1]?'ov2-f-warn':'ov2-f-bad';
  s+=`<rect class="${col}" x="${bx}" y="${y+3}" width="${Math.max(2,w.n/maxN*bw).toFixed(1)}" height="${cell-6}" rx="3"><title>Week of ${dm(w.key)}: ${plural(w.n,'lesson')}${w.open?' so far (week still running)':''}</title></rect>`+tx(bx+w.n/maxN*bw+6,y+cell/2+4,w.n+(w.open?' so far':''),'','ov2-lbl');
 });
 s+=tx(bx,h-4,'lessons that week');
 const why=`${inBand} of ${plural(full.length,'full week')} landed in the band. Most in one week: ${top.n} (week of ${dm(top.key)}).${gap.d?` Longest break: ${gap.d} days (${dm(gap.a)} to ${dm(gap.b)}).`:''}${weeks.length>show.length?` Showing the last ${show.length} of ${weeks.length} weeks.`:''}${weeks[weeks.length-1].open?' The current week is still running and is left out of the average.':''}`;
 return panel('a',title,sub,frame(s,'Lessons per week calendar',h),{head:big(f1(avg),`lessons a week on average over ${plural(base.length,full.length?'full week':'week')} · target ${TARGET[0]} to ${TARGET[1]}`),why,src:'lessons.json dates'});
}

/* ---------- B: weekly pooled words vs baseline ---------- */
function panelB(ls){
 const title='Weekly words right, against your baseline',sub='All scored word uses in a week, pooled (so a 12-use lesson cannot drag the week down). Line = your first two weeks, band = ±2 points. Progress is called only when three weekly points sit above the band.';
 const map=new Map();for(const l of ls){const k=iso(monday(l.date));if(!map.has(k))map.set(k,[]);map.get(k).push(l);}
 const wk=[...map].map(([k,g])=>({k,g,pct:pooledWords(g),scored:sum(g,l=>(l.words&&l.words.scored)||0),slips:slips10(g)})).filter(w=>w.pct!==null);
 if(wk.length<3)return panel('b',title,sub,empty('Needs a third week of lessons after the two baseline weeks.'),{head:big('—','needs three weeks with scored words')});
 const base=pooledWords(wk[0].g.concat(wk[1].g)),after=wk.slice(2),above=after.filter(w=>w.pct>base+2).length;
 const called=after.length>=3&&after.slice(-3).every(w=>w.pct>base+2);
 const H=220,L=40,R=78,T=18,B=30,pw=W-L-R,ph=H-T-B;
 const vals=wk.map(w=>w.pct).concat([base]),lo=Math.max(0,Math.floor((Math.min(...vals)-6)/10)*10),hi=Math.min(100,Math.ceil((Math.max(...vals)+6)/10)*10);
 const y=v=>T+ph-(v-lo)/(hi-lo)*ph,x=i=>L+pw*(i+.5)/wk.length,maxS=niceMax(Math.max(...wk.map(w=>w.slips||0),1));
 let s='';for(let v=lo;v<=hi;v+=10)s+=hline(L,W-R,y(v))+tx(L-6,y(v)+4,v+'%','end');
 const bt=y(Math.min(hi,base+2)),bb=y(Math.max(lo,base-2));
 s+=`<rect class="ov2-band" x="${L}" y="${bt.toFixed(1)}" width="${pw}" height="${(bb-bt).toFixed(1)}"/><line class="ov2-base" x1="${L}" x2="${W-R}" y1="${y(base).toFixed(1)}" y2="${y(base).toFixed(1)}"/>`+tx(W-R+5,y(base)+4,`baseline ${f1(base)}`);
 wk.forEach((w,i)=>{if(w.slips===null)return;const h=w.slips/maxS*ph*.5;s+=`<rect class="ov2-f-sage" fill-opacity=".45" x="${(x(i)-9).toFixed(1)}" y="${(T+ph-h).toFixed(1)}" width="18" height="${h.toFixed(1)}" rx="3"><title>Week of ${dm(w.k)}: ${f1(w.slips)} grammar slips per 10 min</title></rect>`;});
 s+=`<polyline class="ov2-line" points="${wk.map((w,i)=>x(i).toFixed(1)+','+y(w.pct).toFixed(1)).join(' ')}"/>`;
 wk.forEach((w,i)=>{s+=`<circle class="ov2-pt ${w.pct>base+2?'ov2-f-good':'ov2-f-accent'}" cx="${x(i).toFixed(1)}" cy="${y(w.pct).toFixed(1)}" r="${i>=2?6:5}"><title>Week of ${dm(w.k)}: ${f1(w.pct)}% of ${w.scored} scored uses · ${plural(w.g.length,'lesson')}${i<2?' · baseline week':''}</title></circle>`+tx(x(i),y(w.pct)-10,f1(w.pct),'middle','ov2-lbl')+tx(x(i),H-10,dm(w.k),'middle');});
 s+=tx(L+4,T+ph-4,'bars: grammar slips / 10 min');
 const allP=pooledWords(ls),wl=ls.filter(l=>l.words&&ok(l.words.pct)),mean=wl.length?sum(wl,l=>l.words.pct)/wl.length:null;
 const small=wl.slice().sort((a,b)=>a.words.scored-b.words.scored)[0];
 const AX=(window.AneesLessonMath&&window.AneesLessonMath.approx(ls))?'≈':'';   // Medi's decision 4 (2026-09-29): unverified lessons -> "≈"
 const why=`${AX?'Every number here is "≈": it comes from lessons that are not verified yet (hover a lesson score on the table above for why). ':''}Pooled over every scored use: ${AX}${f1(allP)}%. A plain mean of the lesson percentages, ${f1(mean)}%, would weight every lesson the same${small&&mean!==null&&allP!==null&&mean<allP&&small.words.pct<mean?`, so a small lesson (${dm(small.date)}: ${small.words.scored} uses, ${f1(small.words.pct)}%) pulls it down`:''}.${called?' Progress called: the last three weeks all sit above the band.':''}`;
 return panel('b',title,sub,frame(s,'Weekly pooled words right with baseline',H),{head:big(`${above} of ${after.length}`,`weeks above the ${AX}${f1(base)}% baseline so far`),why,src:'words.right, partial, scored by ISO week'});
}

/* ---------- C: time of day ---------- */
function panelC(ls){
 const title='Time of day vs how the lesson went',sub='Each dot is a lesson at its real start time (from the Meet recording). Top: words right. Bottom: grammar slips per 10 minutes. Dot size = how many word uses were scored.';
 const pts=ls.map(l=>{const m=/T(\d\d):(\d\d)/.exec(l.start_local||'');if(!m)return null;return {l,date:l.date,min:+m[1]*60+(+m[2]),words:l.words&&ok(l.words.pct)?l.words.pct:null,scored:(l.words&&l.words.scored)||0,slips:slips10([l]),type:l.type};}).filter(Boolean);
 if(!pts.length)return panel('c',title,sub,empty('No lesson start times yet (lessons.json start_local).'),{wide:true});
 const mins=pts.map(p=>p.min),lo=Math.min(...mins),hi=Math.max(...mins),span=hi-lo,missing=ls.length-pts.length;
 // slots: a 30-minute window centred on the median start (rounded to the quarter hour), before it, after it
 const c=Math.round(median(mins)/15)*15,a=c-15,b=c+15;
 const slots=[{label:`Before ${hm(a)}`,f:p=>p.min<a},{label:`${hm(a)} to ${hm(b)}`,f:p=>p.min>=a&&p.min<b},{label:`${hm(b)} or later`,f:p=>p.min>=b}]
  .map(s=>{const g=pts.filter(s.f);return {label:s.label,n:g.length,words:pooledWords(g.map(p=>p.l)),slips:slips10(g.map(p=>p.l))};});
 const filled=slots.filter(s=>s.n&&s.words!==null);
 const rows=slots.map(s=>`<div class="ov2-row"><b>${esc(s.label)}</b><span class="ov2-track"><i style="width:${s.words===null?0:Math.max(2,s.words)}%"></i></span><span class="ov2-n">${s.n?`${plural(s.n,'lesson')} · ${r0(s.words)}% words · ${f1(s.slips)} slips/10 min`:'no lessons'}</span></div>`).join('');
 const early=slots[0],others=slots.slice(1).filter(s=>s.n&&s.words!==null);
 const earlyWins=!!(early.n&&others.length&&others.every(s=>early.words>s.words&&early.slips!==null&&s.slips!==null&&early.slips<s.slips));
 const verdict=filled.map(s=>`${s.label} (${plural(s.n,'lesson')}): ${r0(s.words)}% words right, ${f1(s.slips)} slips per 10 min.`).join(' ')+' '
  +(span<180?(earlyWins?`The earliest slot leads on both, but with ${pts.length} lessons inside ${span} minutes treat it as a hint, not a finding.`:`With ${pts.length} lessons all inside ${span} minutes, nothing here supports "earlier is better" yet.`)+` One lesson two hours either side of ${hm(lo)} to ${hm(hi)} would test it.`
   :(earlyWins?'Earlier lessons lead on both words and grammar.':'Earlier lessons do not lead on both words and grammar.'));
 // quote: Medi's own words about the lesson time, if a turn file carries them
 let quote='';
 if(TURNS){let hit=null;for(const p of TURNS)for(const t of p.medi)if(/o'?clock meetings?|affecting me/i.test(t.text||''))hit={date:p.date,t};
  if(hit){const nextL=ls.filter(l=>l.date>hit.date).slice(0,3).map(l=>{const m=/T(\d\d:\d\d)/.exec(l.start_local||'');return m?m[1]:'—';});
   quote=`<div class="ov2-quote">"${esc(String(hit.t.text).trim())}"<small>Medi to Amal, ${dm(hit.date)}, minute ${mmss(hit.t.t)}.${nextL.length?` The next ${nextL.length===1?'lesson':nextL.length+' lessons'} started ${nextL.join(', ')}.`:''}</small></div>`;}}
 const Wc=1040,H=300,L=40,R=20,T=18,pw=Wc-L-R,x0=Math.floor((lo-10)/30)*30,x1=Math.ceil((hi+10)/30)*30,xs=m=>L+(m-x0)/(x1-x0)*pw;
 const wv=pts.filter(p=>p.words!==null).map(p=>p.words),wlo=wv.length?Math.max(0,Math.floor((Math.min(...wv)-5)/20)*20):0;
 const r1T=T,r1H=120,ya=v=>r1T+r1H-(v-wlo)/(100-wlo)*r1H;
 const r2T=T+r1H+34,r2H=100,smax=niceMax(Math.max(1,...pts.map(p=>p.slips||0))*1.1),yb=v=>r2T+r2H-v/smax*r2H;
 let s='';
 for(let m=x0;m<=x1;m+=30)s+=`<line class="vp-gridline" x1="${xs(m).toFixed(1)}" x2="${xs(m).toFixed(1)}" y1="${T}" y2="${H-26}"/>`+tx(xs(m),H-8,hm(m),'middle');
 for(let v=wlo;v<=100;v+=20)s+=hline(L,Wc-R,ya(v))+tx(L-6,ya(v)+4,v+'%','end');
 for(let i=0;i<=2;i++){const v=smax*i/2;s+=hline(L,Wc-R,yb(v))+tx(L-6,yb(v)+4,trim0(f1(v)),'end');}
 s+=tx(L+4,r1T+10,'words right','','ov2-lbl')+tx(L+4,r2T+10,'grammar slips per 10 min (lower is better)','','ov2-lbl');
 const lab=new Set(),pick=(arr,f)=>{if(arr.length)lab.add(arr.reduce((q,p)=>f(p)<f(q)?p:q).date);};
 const wp=pts.filter(p=>p.words!==null);pick(wp,p=>p.words);pick(wp,p=>-p.words);pick(pts,p=>p.min);pick(pts,p=>-p.min);
 for(const p of pts){
  const cx=xs(p.min),rad=3+Math.sqrt(p.scored)/2.2,tip=`${dm(p.date)} (${TYPE[p.type]||p.type||'—'}) · started ${hm(p.min)} · ${p.words===null?'—':f1(p.words)+'%'} of ${p.scored} uses · ${f1(p.slips)} slips/10 min`;
  if(p.words!==null){s+=`<circle class="ov2-pt ${tcls(p.type)}" cx="${cx.toFixed(1)}" cy="${ya(p.words).toFixed(1)}" r="${rad.toFixed(1)}" fill-opacity=".85"><title>${esc(tip)}</title></circle>`;if(lab.has(p.date))s+=tx(cx+rad+3,ya(p.words)+4,dm(p.date));}
  if(p.slips!==null)s+=`<circle class="ov2-pt ${tcls(p.type)}" cx="${cx.toFixed(1)}" cy="${yb(p.slips).toFixed(1)}" r="5" fill-opacity=".85"><title>${esc(tip)}</title></circle>`;
 }
 const legend=`<div class="ov2-legend">${Object.entries(TYPE).map(([k,v])=>`<span><i class="ov2-t-${k}"></i>${esc(v)}</span>`).join('')}</div>`;
 const body=`<div class="ov2-two">${big(`${hm(lo)} to ${hm(hi)}`,`${missing?`${pts.length} of ${ls.length} lessons have a start time; they all`:'every lesson'} started inside this ${span}-minute window`)}${quote||'<div></div>'}</div>
 <div class="ov2-scroll">${frame(s,'Lesson start time against words right and grammar slips',H,Wc)}</div>${legend}
 <div class="ov2-two" style="margin-top:12px"><div><div class="ov2-sub">Pooled by start slot</div>${rows}</div><div><div class="ov2-sub">Verdict</div><div class="ov2-text">${esc(verdict)}</div></div></div>`;
 return panel('c',title,sub,body,{wide:true,why:`Start times exist for ${pts.length} of ${ls.length} lessons (lessons.json start_local, minute precision or better).${missing?' Lessons without one are left out.':''}`,src:'start_local · words.pct · grammar.mistakes ÷ duration_min'});
}

/* ---------- D: rest days ---------- */
function panelD(ls){
 const title='Rest days before a lesson',sub='Days since the previous lesson. Bars = every word use after that gap, pooled; dots = each lesson. Grammar slips per 10 minutes on hover.';
 const pts=[];for(let i=1;i<ls.length;i++)pts.push({l:ls[i],gap:dayDiff(ls[i-1].date,ls[i].date)});
 const withW=pts.filter(p=>p.l.words&&ok(p.l.words.pct)&&p.l.words.scored);
 if(!withW.length)return panel('d',title,sub,empty('Needs two lessons with word scores.'));
 const gm=new Map();for(const p of withW){if(!gm.has(p.gap))gm.set(p.gap,[]);gm.get(p.gap).push(p.l);}
 const groups=[...gm].sort((a,b)=>a[0]-b[0]).map(([gap,g])=>({gap,g,pooled:pooledWords(g),slips:slips10(g)}));
 const multi=groups.filter(g=>g.g.length>=2),bestG=(multi.length?multi:groups).reduce((a,g)=>g.pooled>a.pooled?g:a),one=groups.find(g=>g.gap===1);
 const H=220,L=40,R=14,T=18,B=30,pw=W-L-R,ph=H-T-B,wv=withW.map(p=>p.l.words.pct),lo=Math.max(0,Math.floor((Math.min(...wv)-5)/20)*20),ya=v=>T+ph-(v-lo)/(100-lo)*ph;
 const xs=gap=>L+pw*(groups.findIndex(g=>g.gap===gap)+.5)/groups.length,bw=Math.min(52,pw/groups.length*.6);
 let s='';for(let v=lo;v<=100;v+=20)s+=hline(L,W-R,ya(v))+tx(L-6,ya(v)+4,v+'%','end');
 for(const g of groups){const x=xs(g.gap);s+=`<rect class="ov2-f-wash" x="${(x-bw/2).toFixed(1)}" y="${ya(g.pooled).toFixed(1)}" width="${bw.toFixed(1)}" height="${(T+ph-ya(g.pooled)).toFixed(1)}" rx="4"><title>${g.gap} day gap · ${plural(g.g.length,'lesson')} · pooled ${f1(g.pooled)}% words right · ${f1(g.slips)} slips/10 min</title></rect>`+tx(x,T+ph-6,f1(g.pooled)+'%','middle','ov2-lbl')+tx(x,H-10,plural(g.gap,'day'),'middle');}
 const seen={};for(const p of withW){seen[p.gap]=(seen[p.gap]||0)+1;const jit=((seen[p.gap]%3)-1)*9;s+=`<circle class="ov2-pt ov2-f-ink" cx="${(xs(p.gap)+jit).toFixed(1)}" cy="${ya(p.l.words.pct).toFixed(1)}" r="5"><title>${dm(p.l.date)}: ${p.gap} day gap · ${f1(p.l.words.pct)}% words · ${f1(slips10([p.l]))} slips/10 min</title></circle>`;}
 const longest=pts.reduce((a,p)=>p.gap>a.gap?p:a),gl=ls.filter(l=>l.grammar&&ok(l.grammar.pct)).sort((a,b)=>a.grammar.pct-b.grammar.pct),rank=gl.indexOf(longest.l)+1;
 const mids=groups.filter(g=>g.gap>1&&g.gap<=7);
 const why=`${one&&mids.length&&mids.every(g=>g.pooled>=one.pooled-2)?`No drop in words after a gap of up to ${Math.max(...mids.map(g=>g.gap))} days. `:''}The longest break (${longest.gap} days, before ${dm(longest.l.date)}) led into a ${TYPE[longest.l.type]||longest.l.type||'—'} lesson: ${f1(longest.l.words&&longest.l.words.pct)}% words, ${f1(longest.l.grammar&&longest.l.grammar.pct)}% grammar right${rank?` (${rank===1?'the lowest':'number '+rank+' from the bottom'} of ${gl.length} on grammar)`:''}.`;
 const head=big(`${r0(bestG.pooled)}%`,bestG.gap===1||!one?`words right after ${bestG.gap===1?'back-to-back days':`a ${bestG.gap}-day gap`}`:`words right after a ${bestG.gap}-day gap · ${r0(one.pooled)}% after back-to-back days`);
 return panel('d',title,sub,frame(s,'Days since previous lesson against words right',H),{head,why,src:'gap = days between lessons.json dates'});
}

/* ---------- blocks (E, H) ---------- */
function blockAgg(list,val){
 const m=new Map();
 for(const p of list)for(const b of p.blocks){if(!m.has(b.b))m.set(b.b,{b:b.b,ms:0,as:0,fill:0,reach:0});const e=m.get(b.b);e.ms+=b.ms;e.as+=b.as;e.fill+=b.fill;e.reach++;}
 const all=[...m.values()].sort((a,b)=>a.b-b.b).map(e=>Object.assign(e,{v:val(e)})),need=list.length/2;
 return {shown:all.filter(e=>e.reach>=need),dropped:all.filter(e=>e.reach<need)};
}
const blk=b=>`${b*10}–${b*10+10}`;

/* ---------- E: who talks when ---------- */
function panelE(){
 const title='Who talks when',sub='Your share of the talking in each ten-minute block, over the lessons that reached that block. The card shows one number for the whole hour; this shows the shape.';
 if(!TURNS)return panel('e',title,sub,loadingTurns());
 const {shown,dropped}=blockAgg(TURNS,e=>e.ms/(e.ms+e.as)*100);if(!shown.length)return panel('e',title,sub,empty('No turn timings to split into blocks.'));
 const H=210,L=40,R=10,T=14,B=30,pw=W-L-R,ph=H-T-B,gap=10,bw=(pw-gap*(shown.length-1))/shown.length;
 let s='';[0,25,50,75,100].forEach(v=>{const yy=T+ph-v/100*ph;s+=hline(L,W-R,yy)+tx(L-6,yy+4,v+'%','end');});
 shown.forEach((e,i)=>{
  const x=L+i*(bw+gap),h=e.v/100*ph;
  s+=`<rect class="ov2-f-seq2" x="${x.toFixed(1)}" y="${T}" width="${bw.toFixed(1)}" height="${ph}" rx="3"><title>Minute ${blk(e.b)}: Amal ${f1(100-e.v)}% of the talking</title></rect>`;
  s+=`<rect class="${i===0?'ov2-f-accent':'ov2-f-ink'}" x="${x.toFixed(1)}" y="${(T+ph-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="3"><title>Minute ${blk(e.b)}: Medi ${f1(e.v)}% of the talking, ${e.reach} lessons</title></rect>`;
  s+=tx(x+bw/2,T+ph-h+14,r0(e.v)+'%','middle','ov2-inbar')+tx(x+bw/2,H-10,'min '+blk(e.b),'middle','vp-lesson-label');
 });
 s+=`<line class="ov2-half" x1="${L}" x2="${W-R}" y1="${T+ph/2}" y2="${T+ph/2}"/>`+tx(W-R,T+ph/2-4,'50 / 50','end');
 const rest=shown.slice(1).map(e=>e.v),amal=shown.reduce((a,e)=>e.v<a.v?e:a);
 const why=`Amal's biggest share: minute ${blk(amal.b)} (she talks ${r0(100-amal.v)}%).${dropped.length?` Left out: minute ${dropped.map(e=>`${blk(e.b)} (${plural(e.reach,'lesson')})`).join(', ')}, reached by fewer than half the lessons.`:''}`;
 return panel('e',title,sub,frame(s,'Medi talk share per ten-minute block',H),{head:big(`${r0(shown[0].v)}%`,`in the first 10 minutes${rest.length?` · ${r0(Math.min(...rest))} to ${r0(Math.max(...rest))}% after that`:''}`),why,src:'turn t and end, talk.window respected'});
}

/* ---------- F: language mix ---------- */
function panelF(){
 const title='What language your turns were in',sub='Your turns per lesson split three ways: Arabic script, Arabic the engine wrote in Latin letters, and English. Bar length = turns. The number is the share of your talk time spent in English turns.';
 if(!TURNS)return panel('f',title,sub,loadingTurns());
 const P=TURNS,rh=15,step=19,L=52,R=50,T=6,h=T+P.length*step+14,pw=W-L-R,max=Math.max(1,...P.map(p=>p.ar+p.lat+p.en));
 let s='';
 P.forEach((p,i)=>{
  const y=T+i*step;let x=L;s+=tx(L-6,y+rh-3,dm(p.date),'end');
  [[p.ar,'ov2-f-ink','Arabic script'],[p.lat,'ov2-f-seq2','Arabic in Latin letters'],[p.en,'ov2-f-warn','English']].forEach(([v,c,lab])=>{const w=v/max*pw;s+=`<rect class="${c}" x="${x.toFixed(1)}" y="${y}" width="${Math.max(w-1,0).toFixed(1)}" height="${rh}" rx="2"><title>${dm(p.date)} · ${lab}: ${v} turns</title></rect>`;x+=w;});
  s+=tx(x+5,y+rh-3,r0(p.enShare)+'%','',p.enShare>=50?'ov2-bad-txt':'ov2-lbl');
 });
 s+=tx(W-4,h-2,'% = English share of talk time','end');
 const top=P.reduce((a,p)=>p.enShare>a.enShare?p:a),l3=P.slice(-3),l3s=sum(l3,p=>p.enSec)/sum(l3,p=>p.msec)*100;
 const byT=new Map();for(const p of P){if(!byT.has(p.type))byT.set(p.type,[]);byT.get(p.type).push(p);}
 const why='English share by lesson type (talk time, pooled): '+[...byT].map(([t,g])=>`${TYPE[t]||t} ${r0(sum(g,p=>p.enSec)/sum(g,p=>p.msec)*100)}% (${plural(g.length,'lesson')})`).join(' · ')+'.';
 const legend=`<div class="ov2-legend"><span><i class="ov2-sq ov2-k-ink"></i>Arabic script</span><span><i class="ov2-sq ov2-k-seq2"></i>Arabic in Latin letters</span><span><i class="ov2-sq ov2-k-warn"></i>English</span></div>`;
 return panel('f',title,sub,frame(s,'Medi turns per lesson by language',h)+legend,{head:big(`${r0(top.enShare)}%`,`of your talk time on ${dm(top.date)} was English turns · ${r0(l3s)}% in the last ${l3.length} lessons`),why,src:'Caveat: English vs Latin-letter Arabic is a stopword heuristic on engine text'});
}

/* ---------- G: longest no-English stretch ---------- */
function panelG(){
 const title='Longest stretch with no English',sub='Per lesson, the longest run of your turns without a single English turn, in minutes. Where it happened is on hover.';
 if(!TURNS)return panel('g',title,sub,loadingTurns());
 const P=TURNS,H=210,L=40,R=10,T=14,B=30,pw=W-L-R,ph=H-T-B,max=Math.max(STRETCH_TARGET+2,Math.ceil(Math.max(...P.map(p=>p.stretch.s/60))+1)),gap=6,bw=(pw-gap*(P.length-1))/P.length;
 let s='';for(let v=0;v<=max;v+=2){const yy=T+ph-v/max*ph;s+=hline(L,W-R,yy)+tx(L-6,yy+4,v+' min','end');}
 const ty=T+ph-STRETCH_TARGET/max*ph;s+=`<line class="ov2-target" x1="${L}" x2="${W-R}" y1="${ty.toFixed(1)}" y2="${ty.toFixed(1)}"/>`+tx(W-R,ty-4,`${STRETCH_TARGET}-minute target`,'end');
 const rec=P.reduce((a,p)=>p.stretch.s>a.stretch.s?p:a),ri=P.indexOf(rec),stepL=Math.ceil(P.length/7);
 P.forEach((p,i)=>{
  const m=p.stretch.s/60,hh=m/max*ph,x=L+i*(bw+gap),y=T+ph-hh;
  s+=`<rect class="${m>=STRETCH_TARGET?'ov2-f-good':m>=3?'ov2-f-ink':'ov2-f-sage'}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" rx="3"><title>${dm(p.date)}: ${f1(m)} min without English, ${p.stretch.n} turns${p.stretch.at!==null?', from minute '+mmss(p.stretch.at):''}</title></rect>`;
  if(i%stepL===0||i===P.length-1)s+=tx(x+bw/2,H-10,dm(p.date),'middle','vp-lesson-label');
  if(i===0||i===ri||i===P.length-1)s+=tx(x+bw/2,y-5,f1(m),'middle','ov2-lbl');
 });
 const since=P.slice(ri+1),sinceBest=since.length?since.reduce((a,p)=>p.stretch.s>a.stretch.s?p:a):null,hitT=P.filter(p=>p.stretch.s/60>=STRETCH_TARGET).length;
 const meds=P.map(p=>p.medArw).filter(ok),mlo=meds.length?Math.min(...meds):null,mhi=meds.length?Math.max(...meds):null;
 const turnLen=!meds.length?'':mlo===mhi?` Turn length itself is flat: median ${trim0(f1(mlo))} Arabic words per turn in all ${meds.length} lessons, so it is not charted.`:` Turn length: median ${trim0(f1(mlo))} to ${trim0(f1(mhi))} Arabic words per turn across lessons.`;
 const why=`${hitT} of ${plural(P.length,'lesson')} reached the ${STRETCH_TARGET}-minute mark. The record (${dm(rec.date)}) started at minute ${rec.stretch.at===null?'—':mmss(rec.stretch.at)}.${turnLen}`;
 return panel('g',title,sub,frame(s,'Longest stretch without English per lesson, minutes',H),{head:big(`${f1(rec.stretch.s/60)} min`,`on ${dm(rec.date)}${sinceBest?` · best since: ${f1(sinceBest.stretch.s/60)} min (${dm(sinceBest.date)}) · last lesson ${f1(P[P.length-1].stretch.s/60)} min`:''}`),why,src:'Medi turns, kind ≠ English'});
}

/* ---------- H: filled pauses by block ---------- */
function panelH(ls){
 const title='Filled pauses through the hour';
 if(!TURNS)return panel('h',title,'Your "uh", "um", "آآ" per minute of your own talking, by ten-minute block.',loadingTurns(),{wide:true});
 const meta=new Map(ls.map(l=>[l.date,l])),cnt=p=>{const f=(meta.get(p.date)||{}).fillers;return f&&ok(f.count)?f.count:null;};
 // keep lessons whose turn files carry at least half the fillers the hourly job counted: fillers.comparable when the
 // hourly job wrote it (build_lessons_page_data.py, 2026-09-27), the same ratio computed here otherwise
 const inc=TURNS.filter(p=>{const c=cnt(p),f=(meta.get(p.date)||{}).fillers;return c&&(typeof f.comparable==='boolean'?f.comparable:p.turnFill/c>=.5);}),exc=TURNS.filter(p=>!inc.includes(p)&&cnt(p));
 const sub=`Your "uh", "um", "آآ" per minute of your own talking, by ten-minute block, over the ${inc.length} lessons${inc.length?` from ${dm(inc[0].date)}`:''} whose turn files keep the fillers.`;
 const perMin=ls.filter(l=>l.fillers&&ok(l.fillers.per_min)),hiL=perMin.length?perMin.reduce((a,l)=>l.fillers.per_min>a.fillers.per_min?l:a):null;
 const notes=[];
 if(hiL)notes.push(`The card shows <b>${f1(hiL.fillers.per_min)} / min</b> for ${dm(hiL.date)}, the highest of ${perMin.length} lessons. How clearly the recording catches you changes the count, so a jump can mean more was heard, not necessarily more was said.`);
 if(exc.length)notes.push(`The turn files for ${exc.map(p=>dm(p.date)).join(', ')} carry almost no fillers (${exc.map(p=>`${p.turnFill} in the ${dm(p.date)} turns vs ${cnt(p)} in its fillers.count`).join('; ')}), so the blocks leave them out.`);
 if(TURNS.length<ls.length){const k=ls.length-TURNS.length;notes.push(`${plural(k,'turn file')} could not load and ${k===1?'is':'are'} left out.`);}
 notes.push('Counts from lessons recorded different ways are not directly comparable; read a lesson against lessons recorded the same way.');
 const side=`<div><div class="ov2-sub">Why the card's number is hard to trust</div><div class="ov2-notes">${notes.map(t=>`<div>${t}</div>`).join('')}</div></div>`;
 if(!inc.length)return panel('h',title,sub,`<div class="ov2-two">${empty('No turn file keeps enough fillers to chart.')}${side}</div>`,{wide:true});
 const {shown,dropped}=blockAgg(inc,e=>e.ms?e.fill/(e.ms/60):null),sv=shown.filter(e=>e.v!==null);
 if(!sv.length)return panel('h',title,sub,`<div class="ov2-two">${empty('No blocks with talk time.')}${side}</div>`,{wide:true});
 const Wh=520,H=200,L=30,R=10,T=14,B=30,pw=Wh-L-R,ph=H-T-B,max=niceMax(Math.max(...sv.map(e=>e.v))*1.1),gap=10,bw=(pw-gap*(sv.length-1))/sv.length;
 const peak=sv.reduce((a,e)=>e.v>a.v?e:a),low=sv.reduce((a,e)=>e.v<a.v?e:a);
 let s='';for(let i=0;i<=4;i++){const v=max*i/4,yy=T+ph-v/max*ph;s+=hline(L,Wh-R,yy)+tx(L-6,yy+4,trim0(f1(v)),'end');}
 sv.forEach((e,i)=>{
  const hh=e.v/max*ph,x=L+i*(bw+gap),y=T+ph-hh;
  s+=`<rect class="${e===peak?'ov2-f-accent':e===low?'ov2-f-good':'ov2-f-sage'}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" rx="3"><title>Minute ${blk(e.b)}: ${f1(e.v)} filled pauses per minute of your talk (${e.fill} in ${f1(e.ms/60)} min), ${e.reach} lessons</title></rect>`+tx(x+bw/2,H-10,'min '+blk(e.b),'middle','vp-lesson-label');
  if(e===peak||e===low||i===0)s+=tx(x+bw/2,y-6,f1(e.v),'middle','ov2-lbl');
 });
 const first=sv[0];
 const left=`<div>${big(f1(first.v),`per minute in the first block · ${low===first?'the lowest':`low of ${f1(low.v)} at minute ${blk(low.b)}`}`)}${frame(s,'Filled pauses per minute by ten-minute block',H,Wh)}</div>`;
 const why=`Most hesitant: minute ${blk(peak.b)} (${f1(peak.v)} / min). Smoothest: minute ${blk(low.b)} (${f1(low.v)} / min).${dropped.length?` Left out: minute ${dropped.map(e=>blk(e.b)).join(', ')}, reached by fewer than half these lessons.`:''}`;
 return panel('h',title,sub,`<div class="ov2-two">${left}${side}</div>`,{wide:true,why,src:`Turns t, end, text · ${dm(inc[0].date)} to ${dm(inc[inc.length-1].date)}`});
}

/* ---------- render ---------- */
function host(){
 let h=document.getElementById('ov2');if(h)return h;
 const tab=document.getElementById('vp-tab-overview');if(!tab)return null;
 h=document.createElement('section');h.id='ov2';h.className='ov2';h.setAttribute('aria-label','New angles on the lesson numbers');tab.append(h);return h;
}
function render(){
 const h=host();if(!h)return;
 if(!LJ){h.innerHTML='<div class="vp-notice">Loading the new angles…</div>';return;}
 const ls=(LJ.lessons||[]).slice().sort((a,b)=>a.date<b.date?-1:1);
 const one=f=>{try{return f();}catch(e){console.error('overview-angles',e);return `<section class="vp-panel">${empty('This panel could not be drawn ('+e.message+').')}</section>`;}};
 h.innerHTML=`<div class="ov-head ov2-head"><span class="vp-eyebrow">New angles</span><h2 class="ov-h2">What the lesson numbers add up to</h2><p class="ab-sub">Eight views the table cannot show: cadence, weekly baseline, time of day, rest days, talk shape, language mix, Arabic stretches and hesitation. Hover any mark for its numbers.</p></div>
 <div class="vp-grid">${[()=>panelA(ls),()=>panelB(ls),()=>panelC(ls),()=>panelD(ls),panelE,panelF,panelG,()=>panelH(ls)].map(one).join('')}</div>
 <p class="ov2-source">Source: data/lessons.json${TURNS?` + ${TURNS.length} turn files (data/lessons/&lt;date&gt;.json)`:''} · updated ${esc(String(LJ.updated||'').replace('T',' ').slice(0,16))}</p>`;
}
async function json(url){const r=await fetch(url+(url.includes('?')?'&':'?')+'v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status+' '+url);return r.json();}
async function main(){
 render();
 try{LJ=await json('data/lessons.json');}catch(e){const h=host();if(h)h.innerHTML=`<div class="vp-notice">lessons.json could not load (${esc(e.message)}). Refresh to retry.</div>`;return;}
 render();
 const ls=(LJ.lessons||[]).slice().sort((a,b)=>a.date<b.date?-1:1);
 const res=await Promise.allSettled(ls.map(l=>json(l.detail||('data/lessons/'+l.date+'.json'))));
 const out=[];
 res.forEach((r,i)=>{if(r.status!=='fulfilled')return;try{const p=perLesson(ls[i],r.value);if(p)out.push(p);}catch(e){console.warn('overview-angles',ls[i].date,e);}});
 if(!out.length){turnFail=true;render();return;}
 TURNS=out;render();
}
window.AneesOverviewAngles={main,get turns(){return TURNS;}};
main().catch(e=>console.error('overview-angles',e));
})();
