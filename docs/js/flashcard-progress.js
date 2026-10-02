/* Progress & Stats — TAB 2 Flashcards. Spec: plan/PROGRESS-STATS-FLASHCARDS-SPEC-2026-09-22.md.
   Numbers come from AneesFlashcardStats over card_results replayed through AneesFSRS.
   Read-only (Medi 2026-10-02: "We shouldnt have words in the que here, they should be in the flashcard tab"):
   grading, the queue and the leech words live only on cards.html. This tab reads the same live answer store
   cards.html writes (Supabase card_results + this device's unsynced anees-card-log) and re-reads it whenever the
   page comes back into view or cards.html saves an answer in another tab, so a finished set shows at once. */
(function(){
'use strict';
const F=window.AneesFSRS,S=window.AneesFlashcardStats,$=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LS=(k,v)=>{try{if(v===undefined)return JSON.parse(localStorage.getItem(k)||'null');localStorage.setItem(k,JSON.stringify(v));return true;}catch(e){return v===undefined?null:false;}};
const H={apikey:ANEES.anon,Authorization:'Bearer '+ANEES.anon,'Content-Type':'application/json'};
const GOALS={weekly:50,monthly:200};
let words=[],serverLog=[],loaded=false,loading=null,offline=false;
let futureRange=30;
const pref=()=>{const p=Object.assign({mode:'ar_first',retention:0.9},LS('anees-cards-pref')||{});if(!F.RETENTIONS.includes(p.retention))p.retention=0.9;return p;};
/* ---------- data ---------- */
async function get(url){const r=await fetch(url,{headers:H,cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
// card_results columns. tz_offset_min / tz arrive with supabase/migrations/019_card_results_timezone.sql; until it is
// applied the select falls back without them and writes drop them (tzColumn), so nothing breaks either way.
// A failed probe is remembered on this device for a day (anees-tz-col) so the 400 happens once, not on every load.
const LOG_COLS='id,word_key,ts,result,attempt,mode,undone_at,flip_ms,answer_ms';let tzColumn=!((LS('anees-tz-col')||{}).off>Date.now()-86400000);
const noTzColumn=()=>{tzColumn=false;LS('anees-tz-col',{off:Date.now()});};
async function fetchLog(){
 const rows=[];
 for(let off=0;;off+=1000){
  let p;
  try{p=await get(ANEES.url+'/rest/v1/card_results?select='+LOG_COLS+(tzColumn?',tz_offset_min':'')+'&order=ts.asc,id.asc&limit=1000&offset='+off);}
  catch(e){if(!tzColumn||!/HTTP 400/.test(String(e.message)))throw e;noTzColumn();off-=1000;continue;}
  rows.push(...p);if(p.length<1000)break;
 }
 return rows;
}
async function load(){
 if(!words.length){
  try{const all=[];for(let off=0;;off+=1000){const p=await get(ANEES.url+'/rest/v1/words?select=key,arabizi,arabic,english,plural,topic,subtopic,doc_order,house_spelling,aliases&active=eq.true&order=doc_order&limit=1000&offset='+off);all.push(...p);if(p.length<1000)break;}if(all.length){words=all;LS('anees-words',all);}}catch(e){}
  if(!words.length){words=LS('anees-words')||[];if(!words.length){try{words=(await (await fetch('data/words.json')).json()).items||[];}catch(e){}}}
 }
 await loadLog();
 loaded=true;
}
// The live answer store: every row cards.html has synced, fetched fresh (never a built snapshot).
async function loadLog(){
 try{serverLog=await fetchLog();LS('anees-card-server-log',serverLog);offline=false;}
 catch(e){serverLog=LS('anees-card-server-log')||[];offline=true;}
}
// Same merge as cards.html: durable rows plus this device's unsynced rows, by id; an undo on either copy wins.
function fullLog(){const m=new Map(),undone=new Set();for(const r of serverLog.concat(LS('anees-card-log')||[])){if(!r||!r.id)continue;m.set(r.id,{...(m.get(r.id)||{}),...r});if(r.undone||r.undone_at)undone.add(r.id);}return [...m.values()].map(r=>undone.has(r.id)?{...r,undone:true}:r);}
// Re-read the answers when the page comes back into view (Medi 2026-10-02: "this should update immediately after a
// card set is done") or when cards.html, open in another tab, saves an answer (anees-card-log changes).
let refreshing=null,lastRefresh=0;
function refresh(){
 if(!loaded||refreshing)return refreshing;
 lastRefresh=Date.now();
 refreshing=loadLog().then(()=>{if(!$('vp-tab-flash').hidden)render();document.dispatchEvent(new CustomEvent('anees:card-log-refreshed'));}).finally(()=>{refreshing=null;});
 return refreshing;
}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&Date.now()-lastRefresh>3000)refresh();});
window.addEventListener('pageshow',e=>{if(e.persisted)refresh();});
window.addEventListener('focus',()=>{if(Date.now()-lastRefresh>3000)refresh();});
window.addEventListener('storage',e=>{if(e.key==='anees-card-log'||e.key==='anees-card-queue'){if(!$('vp-tab-flash').hidden)render();clearTimeout(refresh.t);refresh.t=setTimeout(refresh,4000);}});   // local rows show now; synced copy follows
/* ---------- formatting ---------- */
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const pct=v=>v===null||v===undefined?'—':v+'%';
const secs=ms=>{if(!Number.isFinite(ms))return '—';const s=ms/1000;if(s<60)return s.toFixed(1)+' s';const m=Math.floor(s/60);return m+' m '+Math.round(s-m*60)+' s';};
const short=d=>{const [,m,dd]=d.split('-');return `${Number(m)}/${Number(dd)}`;};
const plural=(k,one,many)=>`${n(k)} ${k===1?one:many||one+'s'}`;
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
function card({label,icon='',value,unit='',sub='',bar='',extra='',id='',cls=''}){
 const inner=`<div class="vp-card-label"><span>${esc(label)}</span><i aria-hidden="true">${icon}</i></div>${extra}${value!==undefined?`<div class="vp-card-value"><span class="vp-num">${value}</span>${unit?`<span class="vp-card-unit">${esc(unit)}</span>`:''}</div>`:''}${sub?`<div class="vp-card-sub">${sub}</div>`:''}${bar}`;
 return `<div class="vp-card ${cls}"${id?` id="${id}"`:''}>${inner}</div>`;
}
const barLine=p=>`<div class="vp-card-bar"><span style="width:${Math.min(100,p)}%;background:var(--vp-forest)"></span></div>`;
const panel=(id,title,sub,body,{side='',wide=false,cls=''}={})=>`<section class="vp-panel ${wide?'fp-wide':''} ${cls}" aria-labelledby="fp-h-${id}"><div class="vp-panelhead"><div><h2 id="fp-h-${id}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div>${side}</div>${body}</section>`;
/* ---------- SVG ---------- */
const W=640,PAD={l:38,r:14,t:18,b:30};
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
function bars(series,{h=220,w=W,label,max,labelEvery=1,valueLabels=true,cls=''}){
 const W=w,top=max||niceMax(Math.max(1,...series.map(s=>s.v))),slot=(W-PAD.l-PAD.r)/series.length,bw=Math.max(2,Math.min(42,slot*.66)),y=v=>h-PAD.b-(h-PAD.b-PAD.t)*v/top;
 const grid=[0,.5,1].map(f=>`<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(top*f).toFixed(1)}" y2="${y(top*f).toFixed(1)}"/><text x="${PAD.l-6}" y="${(y(top*f)+3.5).toFixed(1)}" text-anchor="end">${n(Math.round(top*f*10)/10)}</text>`).join('');
 const b=series.map((s,i)=>{const x=PAD.l+slot*i+(slot-bw)/2,cx=x+bw/2;return `<g><title>${esc(s.title||s.x+': '+n(s.v))}</title>${s.v?`<rect class="fp-bar ${s.cls||''}" x="${x.toFixed(1)}" y="${y(s.v).toFixed(1)}" width="${bw.toFixed(1)}" height="${(h-PAD.b-y(s.v)).toFixed(1)}" rx="2"/>`:''}${valueLabels&&s.v?`<text class="vp-callout" x="${cx.toFixed(1)}" y="${(y(s.v)-4).toFixed(1)}" text-anchor="middle">${n(s.v)}</text>`:''}${i%labelEvery===0?`<text class="vp-lesson-label" x="${cx.toFixed(1)}" y="${h-10}" text-anchor="middle">${esc(s.x)}</text>`:''}</g>`;}).join('');
 return `<svg class="vp-chart ${cls}" viewBox="0 0 ${W} ${h}" role="img" aria-label="${esc(label)}">${grid}${b}</svg>`;
}
/* ---------- sections ---------- */
function build(){
 const p=pref(),now=new Date(),log=fullLog(),h=S.history(log,{desiredRetention:p.retention}),cards=h.cards;
 const keys=words.map(w=>w.key),byKey=new Map(words.map(w=>[w.key,w]));
 return {p,now,log,h,cards,keys,byKey,
  goals:S.goals(h,now,GOALS),work:S.workload(cards,now,p.retention),tr:S.trueRetention(h),leeches:S.leeches(cards),watch:S.leechWatch(cards),
  curve:S.curve(h,now,30),seg:S.segmentation(h,keys),today:S.today(h,now),
  heat:S.heatmap(h,now),table:S.retentionTable(h,now),due:S.futureDue(cards,now,futureRange),hist:S.histograms(cards,now),
  time:S.timing(h)};
}
function topRow(d){
 const r=d.p.retention,g=d.goals;
 return [
  card({label:'Target retention',icon:'◎',value:Math.round(r*100),unit:'%',sub:'Drives reviews needed, required passes and the forecasts. <a href="cards.html">Set it in Flashcards →</a>'}),
  card({label:'Weekly goal',icon:'▦',value:n(g.week.n),unit:`of ${g.week.goal} words`,sub:`<b>${g.week.pct}%</b> met · distinct cards answered Mon–Sun`,bar:barLine(g.week.pct)}),
  card({label:'Monthly goal',icon:'▤',value:n(g.month.n),unit:`of ${g.month.goal} words`,sub:`<b>${g.month.pct}%</b> met · distinct cards answered this month`,bar:barLine(g.month.pct)}),
  card({label:'Due today',icon:'↻',value:n(d.work.needed),unit:'cards',sub:d.work.needed?`Due by tonight${d.work.unfinished?` · <b>${n(d.work.unfinished)}</b> of them never finished their first day (still on a learning step)`:''}.`:'Nothing is due by tonight.'}),
  card({label:'Expected right',icon:'✓',value:n(d.work.passes),unit:d.work.needed?`of ${n(d.work.needed)}`:'',sub:d.work.needed?`What your ${Math.round(r*100)}% target predicts for today's ${n(d.work.needed)}. A yardstick, not a quota.`:'Appears once something is due.'}),
  card({label:'True retention',icon:'◑',value:pct(d.tr.pct),sub:d.tr.n?`Actual historical performance on mature cards · <b>${n(d.tr.right)}</b> of ${n(d.tr.n)} answers`:'No answer on a mature card yet (interval of 21+ days).'}),
  card({label:'Leech words',icon:'⚑',value:n(d.leeches.length),sub:leechSub(d)})
 ].join('');
}
// Leech = missed leechMisses (3) times in any phase, learning misses included (rule FC-07, Medi 2026-10-02).
// Counts only (Medi 2026-10-02: no word lists on Progress); the leech words themselves are listed on Flashcards.
function leechSub(d){
 const o=F.DEFAULTS,rule=`missed ${o.leechMisses}× in any phase`;
 const all=[...d.cards.values()].filter(c=>c.reps&&(c.misses||0)>0),near=all.filter(c=>!F.isLeech(c)&&(c.misses||0)===o.leechMisses-1).length;
 return `<b>${n(all.length)}</b> cards missed at least once · <b>${n(near)}</b> one miss from the line. Rule: ${rule}. <a href="cards.html">The words are in Flashcards →</a>`;
}
function forgetting(d){
 const c=d.curve;if(!c.length)return empty('The curve appears after your first flashcard answer.');
 const h=250,x=i=>PAD.l+(W-PAD.l-PAD.r)*(c.length===1?.5:i/(c.length-1)),y=v=>h-PAD.b-(h-PAD.b-PAD.t)*v/100,target=d.p.retention*100;
 const path=list=>list.map((p,i)=>`${i?'L':'M'}${x(p.i).toFixed(1)},${y(p.r).toFixed(1)}`).join(' ');
 const pts=c.map((p,i)=>({...p,i})).filter(p=>p.r!==null),past=pts.filter(p=>!p.future),future=pts.filter((p,i)=>p.future||i===past.length-1);
 const grid=[0,25,50,75,100].map(v=>`<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${PAD.l-6}" y="${y(v)+3.5}" text-anchor="end">${v}%</text>`).join('');
 const step=Math.ceil(c.length/7),labels=c.map((p,i)=>i%step===0||i===c.length-1?`<text class="vp-lesson-label" x="${x(i).toFixed(1)}" y="${h-10}" text-anchor="middle">${short(p.date)}</text>`:'').join('');
 const bumps=pts.filter(p=>p.bump).map(p=>`<circle class="fp-bump" cx="${x(p.i).toFixed(1)}" cy="${y(p.r).toFixed(1)}" r="4"><title>${p.date}: memory bumped by a correct review · ${p.r}% average recall</title></circle>`).join('');
 const hover=pts.map(p=>`<rect x="${(x(p.i)-3).toFixed(1)}" y="${PAD.t}" width="6" height="${h-PAD.t-PAD.b}" fill="transparent"><title>${p.date}${p.future?' (forecast)':''}: ${p.r}% average recall across ${p.cards} cards</title></rect>`).join('');
 const todayI=past.length?past.at(-1).i:0,last=past.at(-1);
 return `<svg class="vp-chart" viewBox="0 0 ${W} ${h}" role="img" aria-label="Forgetting curve">${grid}<line class="fp-target" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(target)}" y2="${y(target)}"/><text class="fp-target-label" x="${W-PAD.r}" y="${y(target)-5}" text-anchor="end">target ${target}%</text><line class="vp-axis" x1="${x(todayI)}" x2="${x(todayI)}" y1="${PAD.t}" y2="${h-PAD.b}"/><text x="${x(todayI)+4}" y="${PAD.t+8}">today</text><path class="vp-line" d="${path(past)}"/><path class="vp-line fp-future" d="${path(future)}"/>${bumps}${hover}${labels}${last?`<text class="vp-callout" x="${x(last.i)-6}" y="${y(last.r)-10}" text-anchor="end">Now: ${last.r}%</text>`:''}</svg>`;
}
function segmentation(d){
 const s=d.seg;
 return [
  card({label:'New',icon:'○',value:n(s.new.count),unit:'cards',sub:`Never answered · first-answer pass rate <b>${pct(s.new.pass)}</b>${s.new.firstAnswers?` over ${plural(s.new.firstAnswers,'card')}`:' · no answers yet'}`}),
  card({label:'Learning',icon:'◐',value:n(s.learning.count),unit:'cards',sub:`Interval under 21 days · pass rate <b>${pct(s.learning.pass)}</b>${s.learning.answers?` over ${plural(s.learning.answers,'answer')}`:' · no answers while learning yet'}`}),
  card({label:'Mature',icon:'●',value:n(s.mature.count),unit:'cards',sub:`Interval 21+ days · <b>${n(s.mature.lapses)}</b> total lapses (times forgotten)`})
 ].join('');
}
function todayBlock(d){
 const t=d.today;if(!t.n)return empty('No cards studied today.');
 const min=t.ms/60000,time=t.timed?`${min<1?'<1':Math.round(min)} min`:'— min';
 return `<p class="fp-today">Studied <b>${plural(t.cards,'card')}</b> in <b>${time}</b> · <b>${pct(t.pct)}</b> right</p><div class="vp-foot"><div>Answers<b>${n(t.n)}</b></div><div>New<b>${n(t.split.new)}</b></div><div>Learning<b>${n(t.split.learning)}</b></div><div>Review<b>${n(t.split.review)}</b></div></div>`;
}
// This month and the eleven after it (Medi 2026-10-02: "since we just started this its useless to look backwards. lets
// show this month and the forward months"). Days up to today = reviews done; later days are outlined, with the cards
// FSRS has due that day in the hover. Streaks and days studied still count the whole history (S.heatmap).
function heatmap(d){
 const now=new Date(d.now),y0=now.getFullYear(),m0=now.getMonth(),start=new Date(y0,m0,1),end=new Date(y0,m0+12,1),todayK=S.iso(now);
 const per=new Map();for(const a of d.h.answers){const k=S.iso(a.t);per.set(k,(per.get(k)||0)+1);}
 const span=Math.round((end-start)/86400000),fc=F.forecast([...d.cards.values()],now,span+1),due=new Map(fc.map(x=>[x.date,x.due]));
 const days=[];for(let x=new Date(start);x<end;x.setDate(x.getDate()+1)){const k=S.iso(x);days.push({date:k,n:per.get(k)||0,future:k>todayK,today:k===todayK,due:due.get(k)||0,weekday:(x.getDay()+6)%7});}
 const max=Math.max(0,...days.map(p=>p.n)),cell=11,gap=2,first=days[0].weekday,cols=Math.ceil((days.length+first)/7),w=cols*(cell+gap)+26,h=7*(cell+gap)+18;
 const shade=v=>!v?0:max<=1?4:Math.min(4,1+Math.floor((v-1)/Math.max(1,(max-1)/3)));
 let months='';
 const sq=days.map((p,i)=>{const k=i+first,cx=26+Math.floor(k/7)*(cell+gap),cy=14+(k%7)*(cell+gap);
  if(p.date.endsWith('-01'))months+=`<text x="${cx}" y="9">${new Date(p.date+'T12:00').toLocaleDateString(undefined,{month:'short'})}</text>`;
  const tip=p.future?`${p.date}: ${plural(p.due,'card')} due`:`${p.date}: ${plural(p.n,'review')}${p.today&&p.due?` · ${plural(p.due,'card')} still due today`:''}`;
  return `<rect class="fp-heat ${p.future?'fp-heat-future':'fp-heat-'+shade(p.n)}${p.today?' fp-heat-today':''}" x="${cx}" y="${cy}" width="${cell}" height="${cell}" rx="2"><title>${tip}</title></rect>`;}).join('');
 const wd=['Mon','','Wed','','Fri','',''].map((l,i)=>l?`<text x="0" y="${14+i*(cell+gap)+9}">${l}</text>`:'').join('');
 return `<div class="fp-heatwrap"><svg class="vp-chart fp-heatmap" viewBox="0 0 ${w} ${h}" role="img" aria-label="Reviews per day, this month and the next eleven">${months}${wd}${sq}</svg></div>`;
}
function retentionTable(d){
 const t=d.table;
 return `<div class="fp-tablewrap"><table class="fp-table fp-rt"><thead><tr><th></th>${t.periods.map(p=>`<th>${esc(p.label)}</th>`).join('')}</tr></thead><tbody>${t.rows.map(r=>`<tr><th>${esc(r.label)}${r.id==='young'?' <small>&lt; 21 d</small>':r.id==='mature'?' <small>≥ 21 d</small>':''}</th>${r.cells.map(c=>`<td>${c.n?`<b>${pct(c.pct)}</b><small>${n(c.right)} / ${n(c.n)}</small>`:'—'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${t.rows.at(-1).cells.at(-1).n?'':'<p class="ab-sub">No review answers yet: a card counts here once it has passed its learning steps and comes back for review.</p>'}`;
}
function futureDue(d){
 const f=d.due;if(!f.total&&!f.overdue)return empty('No cards scheduled.');
 const every=futureRange>30?7:3;if(!f.total)return empty(`No cards scheduled in the next ${futureRange===30?'month':'3 months'}; the ${plural(f.overdue,'overdue card')} are waiting now.`);
 return bars(f.days.map((p,i)=>({x:i?short(p.date):'Today',v:p.due,title:`${p.date}: ${n(p.due)} cards due`})),{label:`Cards due over the next ${futureRange} days`,labelEvery:every,valueLabels:futureRange<=30,h:220});
}
function histograms(d){
 const x=d.hist;if(!x)return empty('— until one review exists.');
 const one=(title,part,unit,cls)=>`<div class="fp-hist"><div class="fp-hist-head"><b>${esc(title)}</b><span>avg <b>${n(part.avg)}${unit}</b></span></div>${bars(part.bins.map(b=>({x:b.label,v:b.n,title:`${b.range||b.label}: ${plural(b.n,'card')}`})),{label:title,w:320,h:200,cls})}</div>`;
 return `<div class="fp-hists">${one('Stability',x.stability,' d','')}${one('Difficulty (1–10)',x.difficulty,'','')}${one('Retrievability now',x.retrievability,'%','')}</div><p class="vp-foot">${plural(x.n,'reviewed card')} · FSRS default parameters, not fitted to you</p>`;
}
function render(){
 const host=$('vp-tab-flash');if(!host)return;
 if(!loaded){host.innerHTML='<div class="vp-notice">Loading your flashcard answers…</div>';return;}
 const d=build(),scrollY=window.scrollY;
 host.innerHTML=`<div class="vp-notice" id="fp-sync" role="status">${offline?'Card history is offline: numbers use this device’s saved answers.':`${plural(d.h.answers.length,'answer')} on ${plural(d.cards.size,'card')} · FSRS default parameters, not fitted to you.`}</div>
 <section class="vp-cards" aria-label="Goals and workload">${topRow(d)}</section>
 <div class="vp-grid">
 ${panel('curve','Forgetting curve & retention threshold','Average recall of every card you have answered, from your first answer to 30 days ahead. Dots = days a correct review bumped memory.',forgetting(d),{wide:true,side:d.curve.length?`<div class="vp-legend"><span class="vp-key-mastered">━ Recall</span><span class="vp-key-avg">┅ Target ${Math.round(d.p.retention*100)}%</span><span class="fp-key-bump">● Bumped</span></div>`:''})}
 </div>
 <h2 class="fp-h">Memory segmentation</h2>
 <section class="vp-cards fp-three" aria-label="New, learning and mature cards">${segmentation(d)}</section>
 <div class="vp-grid" id="fp-grid">
 ${panel('today','Today','',todayBlock(d))}
 ${panel('rt','True retention','Review answers only: % right (passed / answered).',retentionTable(d))}
 ${panel('heat','Reviews calendar','One square per day, from this month forward. Filled = reviews done; outlined = days still ahead (hover for cards due).',heatmap(d),{wide:true,side:`<div class="vp-foot fp-streak"><div>Current streak<b>${plural(d.heat.current,'day')}</b></div><div>Longest<b>${plural(d.heat.longest,'day')}</b></div><div>Days studied<b>${n(d.heat.active)}</b></div></div>`})}
 ${panel('due','Future due','Cards due per day at your target retention. Today includes anything overdue.',futureDue(d),{side:`<div class="fp-dueside"><div class="vp-minipills" role="group" aria-label="Range"><button class="fp-minipill" data-range="30" aria-pressed="${futureRange===30}">1 month</button><button class="fp-minipill" data-range="90" aria-pressed="${futureRange===90}">3 months</button></div><span>Overdue backlog: <b>${plural(d.due.overdue,'card')}</b></span></div>`})}
 ${panel('hist','FSRS memory states','Stability = days until recall drops to 90%. Difficulty 1 (easy) to 10 (hard). Retrievability = chance you recall it right now.',histograms(d),{wide:true})}
 ${angles(d)}
 </div>`;
 bind();window.scrollTo(0,scrollY);
}
// One section (Medi 2026-10-02: "fully combine the old and the new"): flashcard-angles.js returns its panels as HTML
// and they sit in the same grid as the panels above, with no separate header.
function angles(d){try{return window.AneesFlashcardAngles?window.AneesFlashcardAngles.panels(d):'';}catch(e){console.error('flashcard angles',e);return `<div class="vp-notice">Some flashcard panels could not be drawn (${esc(e.message)}).</div>`;}}
function bind(){
 const host=$('vp-tab-flash');
 host.querySelectorAll('[data-range]').forEach(b=>b.onclick=()=>{futureRange=Number(b.dataset.range);render();});
}
/* ---------- tabs ---------- */
function show(tab){
 if(!['overview','vocab','flashcards','grammar','lexicon','fluency'].includes(tab))tab='overview';           // Overview is the home tab (Medi 2026-09-26)
 const flash=tab==='flashcards';
 document.querySelectorAll('.vp-tab[data-tab]').forEach(b=>b.setAttribute('aria-current',b.dataset.tab===tab?'page':'false'));
 const ov=$('vp-tab-overview');if(ov)ov.hidden=tab!=='overview';
 $('vp-tab-vocab').hidden=tab!=='vocab';$('vp-tab-flash').hidden=!flash;
 const gr=$('vp-tab-grammar');if(gr)gr.hidden=tab!=='grammar';if(tab==='grammar'&&window.AneesGrammarProgress)window.AneesGrammarProgress.show();   // Grammar tab (2026-09-27)
 for(const [id,mod] of [['lexicon','AneesVerbLexicon'],['fluency','AneesFluencyLadder']]){const el=$('vp-tab-'+id);if(el)el.hidden=tab!==id;if(tab===id&&window[mod]&&window[mod].show)window[mod].show();}   // Verbal Lexicon + Fluency tabs (2026-09-27)
 const hz=document.querySelector('.vp-horizon');if(hz)hz.hidden=tab!=='vocab';
 const url=new URL(location.href);if(tab==='overview')url.searchParams.delete('tab');else url.searchParams.set('tab',tab);history.replaceState(null,'',url);
 if(flash){if(!loaded){render();loading=loading||load().then(render);}else{render();refresh();}}
 document.dispatchEvent(new CustomEvent('anees:progress-tab',{detail:{tab}}));   // progress-sure.js mounts "How sure are these numbers?" (2026-09-28)
}
document.querySelectorAll('.vp-tab[data-tab]').forEach(b=>b.onclick=()=>show(b.dataset.tab));
window.addEventListener('online',()=>refresh());
window.AneesFlashcardProgress={show,reload:async()=>{loaded=false;loading=null;await load();render();},build:()=>build(),get loaded(){return loaded;},refresh};
show(new URLSearchParams(location.search).get('tab')||'overview');
})();
