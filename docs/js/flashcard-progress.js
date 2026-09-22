/* Progress & Stats — TAB 2 Flashcards. Spec: plan/PROGRESS-STATS-FLASHCARDS-SPEC-2026-09-22.md.
   Numbers come from AneesFlashcardStats over card_results replayed through AneesFSRS.
   The review queue writes the same card_results row as cards.html and shares its
   local queue (anees-card-queue / anees-card-log), so either page can finish a sync. */
(function(){
'use strict';
const F=window.AneesFSRS,S=window.AneesFlashcardStats,C=window.AneesCards,$=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LS=(k,v)=>{try{if(v===undefined)return JSON.parse(localStorage.getItem(k)||'null');localStorage.setItem(k,JSON.stringify(v));return true;}catch(e){return v===undefined?null:false;}};
const uuid=()=>crypto.randomUUID?crypto.randomUUID():'c'+Date.now().toString(36)+Math.random().toString(36).slice(2);
const H={apikey:ANEES.anon,Authorization:'Bearer '+ANEES.anon,'Content-Type':'application/json'};
const GOALS={weekly:50,monthly:200};
let words=[],siblings=null,serverLog=[],loaded=false,loading=null,offline=false;
let futureRange=30,leechOnly=false,lastAnswer=null,memQueue=[];
const reveal=new Map(); // word key -> time the English was tapped open
const pref=()=>{const p=Object.assign({mode:'ar_first',retention:0.9},LS('anees-cards-pref')||{});if(!F.RETENTIONS.includes(p.retention))p.retention=0.9;return p;};
const setRetention=r=>{const p=Object.assign({},LS('anees-cards-pref')||{},{retention:r});LS('anees-cards-pref',p);};
/* ---------- data ---------- */
async function get(url){const r=await fetch(url,{headers:H,cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
async function load(){
 try{const all=[];for(let off=0;;off+=1000){const p=await get(ANEES.url+'/rest/v1/words?select=key,arabizi,arabic,english,plural,topic,subtopic,doc_order,house_spelling,aliases&active=eq.true&order=doc_order&limit=1000&offset='+off);all.push(...p);if(p.length<1000)break;}if(all.length){words=all;LS('anees-words',all);}}catch(e){}
 if(!words.length){words=LS('anees-words')||[];if(!words.length){try{words=(await (await fetch('data/words.json')).json()).items||[];}catch(e){}}}
 let catalog=null;try{catalog=await (await fetch('data/word-bank-catalog.json')).json();}catch(e){catalog=LS('anees-cards-catalog');}
 siblings=C.siblingMap(words,catalog);
 try{const rows=[];for(let off=0;;off+=1000){const p=await get(ANEES.url+'/rest/v1/card_results?select=id,word_key,ts,result,attempt,mode,undone_at,flip_ms,answer_ms&order=ts.asc,id.asc&limit=1000&offset='+off);rows.push(...p);if(p.length<1000)break;}serverLog=rows;LS('anees-card-server-log',rows);offline=false;}
 catch(e){serverLog=LS('anees-card-server-log')||[];offline=true;}
 loaded=true;
}
// Same merge as cards.html: durable rows plus this device's unsynced rows, by id; an undo on either copy wins.
function fullLog(){const m=new Map(),undone=new Set();for(const r of serverLog.concat(LS('anees-card-log')||[])){if(!r||!r.id)continue;m.set(r.id,{...(m.get(r.id)||{}),...r});if(r.undone||r.undone_at)undone.add(r.id);}return [...m.values()].map(r=>undone.has(r.id)?{...r,undone:true}:r);}
/* ---------- writes (mirror of cards.html's offline queue) ---------- */
const readQ=()=>(LS('anees-card-queue')||[]).concat(memQueue);
function enqueue(row){const q=LS('anees-card-queue')||[];q.push(row);const ok=LS('anees-card-queue',q);
 if(row.kind!=='undo'){const log=LS('anees-card-log')||[];log.push(row);LS('anees-card-log',log.slice(-2000));}
 if(!ok||!(LS('anees-card-queue')||[]).some(x=>x.id===row.id))memQueue.push(row);sync();}
function removeSent(ids){const s=new Set(ids);LS('anees-card-queue',(LS('anees-card-queue')||[]).filter(x=>!s.has(x.id)));memQueue=memQueue.filter(x=>!s.has(x.id));}
function dropRow(row,why){removeSent([row.id]);const d=LS('anees-card-dead')||[];d.push({row,why,t:new Date().toISOString()});LS('anees-card-dead',d.slice(-200));}
const postRows=rows=>fetch(ANEES.url+'/rest/v1/card_results?on_conflict=id',{method:'POST',headers:{...H,Prefer:'resolution=ignore-duplicates,return=minimal'},body:JSON.stringify(rows.map(({kind,body,undone,...r})=>r))});
const postUndo=op=>fetch(ANEES.url+'/rest/v1/card_results?id=eq.'+encodeURIComponent(op.target)+'&undone_at=is.null',{method:'PATCH',headers:{...H,Prefer:'return=minimal'},body:JSON.stringify({undone_at:op.at})});
let syncing=false,again=false;
async function sync(){if(syncing){again=true;return;}syncing=true;
 try{while(true){const q=readQ().filter(x=>x.kind!=='flag');if(!q.length)break;const undos=q.filter(x=>x.kind==='undo'),rows=q.filter(x=>x.kind!=='undo');
  if(rows.length){const batch=rows.slice(0,50),r=await postRows(batch);
   if(r.ok)removeSent(batch.map(x=>x.id));else if(r.status===429||r.status>=500)throw Error('sync');
   else for(const row of batch){const r1=await postRows([row]);if(r1.ok)removeSent([row.id]);else if(r1.status===429||r1.status>=500)throw Error('sync');else dropRow(row,'HTTP '+r1.status);}
   continue;}
  for(const u of undos){const r=await postUndo(u);if(r.ok)removeSent([u.id]);else if(r.status===429||r.status>=500)throw Error('undo');else dropRow(u,'HTTP '+r.status);}
  break;}
  status('All answers saved.');}
 catch(e){const n=readQ().length;status(`${n} answer${n===1?'':'s'} waiting to sync (offline is fine).`);}
 syncing=false;if(again){again=false;sync();}}
function status(t){const el=$('fp-sync');if(el)el.textContent=t;}
/* ---------- formatting ---------- */
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const pct=v=>v===null||v===undefined?'—':v+'%';
const secs=ms=>{if(!Number.isFinite(ms))return '—';const s=ms/1000;if(s<60)return s.toFixed(1)+' s';const m=Math.floor(s/60);return m+' m '+Math.round(s-m*60)+' s';};
const dayName=d=>new Date(d+'T12:00').toLocaleDateString(undefined,{weekday:'short'});
const short=d=>{const [,m,dd]=d.split('-');return `${Number(m)}/${Number(dd)}`;};
const plural=(k,one,many)=>`${n(k)} ${k===1?one:many||one+'s'}`;
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
function card({label,icon='',value,unit='',sub='',bar='',extra='',id='',cls='',button=false,title=''}){
 const inner=`<div class="vp-card-label"><span>${esc(label)}</span><i aria-hidden="true">${icon}</i></div>${extra}${value!==undefined?`<div class="vp-card-value"><span class="vp-num">${value}</span>${unit?`<span class="vp-card-unit">${esc(unit)}</span>`:''}</div>`:''}${sub?`<div class="vp-card-sub">${sub}</div>`:''}${bar}`;
 return button?`<button class="vp-card fp-cardbtn ${cls}" id="${id}" title="${esc(title)}">${inner}</button>`:`<div class="vp-card ${cls}"${id?` id="${id}"`:''}>${inner}</div>`;
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
  goals:S.goals(h,now,GOALS),work:S.workload(cards,now,p.retention),tr:S.trueRetention(h),leeches:S.leeches(cards),
  curve:S.curve(h,now,30),week:F.forecast([...cards.values()],now,7),seg:S.segmentation(h,keys),today:S.today(h,now),
  heat:S.heatmap(h,now),table:S.retentionTable(h,now),due:S.futureDue(cards,now,futureRange),hist:S.histograms(cards,now),
  time:S.timing(h),hours:S.hourly(h),queue:C.queue(words,cards,log,now,{newPerDay:F.DEFAULTS.newPerDay,siblings})};
}
function topRow(d){
 const r=d.p.retention,g=d.goals;
 return [
  card({label:'Target retention',icon:'◎',extra:`<div class="fp-seg" role="group" aria-label="Target retention">${F.RETENTIONS.map(x=>`<button data-ret="${x}" aria-pressed="${x===r}">${Math.round(x*100)}%</button>`).join('')}</div>`,sub:'Drives reviews needed, required passes and both forecasts. Shared with Flashcards.'}),
  card({label:'Weekly goal',icon:'▦',value:n(g.week.n),unit:`of ${g.week.goal} words`,sub:`<b>${g.week.pct}%</b> met · distinct cards answered Mon–Sun`,bar:barLine(g.week.pct)}),
  card({label:'Monthly goal',icon:'▤',value:n(g.month.n),unit:`of ${g.month.goal} words`,sub:`<b>${g.month.pct}%</b> met · distinct cards answered this month`,bar:barLine(g.month.pct)}),
  card({label:'Reviews needed',icon:'↻',value:n(d.work.needed),unit:'today',sub:'Total reviews required today to maintain target curve.'}),
  card({label:'Required passes',icon:'✓',value:n(d.work.passes),sub:`Cards you must answer correctly to stay ahead of the curve (${Math.round(r*100)}% of ${n(d.work.needed)}).`}),
  card({label:'True retention',icon:'◑',value:pct(d.tr.pct),sub:d.tr.n?`Actual historical performance on mature cards · <b>${n(d.tr.right)}</b> of ${n(d.tr.n)} answers`:'No answer on a mature card yet (interval of 21+ days).'}),
  card({label:'Leech words',icon:'⚑',value:n(d.leeches.length),sub:d.leeches.length?'Chronically failed cards requiring intervention. Tap to list them.':'Chronically failed cards requiring intervention. None yet (8+ lapses).',button:!!d.leeches.length,id:'fp-leech',title:'Show leeches in the review table'})
 ].join('');
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
function weekForecast(d){
 if(!d.h.answers.length)return empty('No cards scheduled yet.');
 return bars(d.week.map((p,i)=>({x:i?dayName(p.date):'Today',v:p.due,title:`${p.date}: ${n(p.due)} cards due${i?'':' (includes overdue)'}`})),{label:'Review forecast, next 7 days',h:220});
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
function heatmap(d){
 const m=d.heat,cell=11,gap=2,first=m.days[0].weekday,cols=Math.ceil((m.days.length+first)/7),w=cols*(cell+gap)+26,h=7*(cell+gap)+18;
 const shade=v=>!v?0:m.max<=1?4:Math.min(4,1+Math.floor((v-1)/Math.max(1,(m.max-1)/3)));
 let months='',lastMonth='';
 const sq=m.days.map((p,i)=>{const k=i+first,cx=26+Math.floor(k/7)*(cell+gap),cy=14+(k%7)*(cell+gap),mo=p.date.slice(0,7);
  if((k%7===0||i===0)&&mo!==lastMonth){lastMonth=mo;if(i>=14||m.days[i+14]?.date.slice(0,7)===mo){months+=`<text x="${cx}" y="9">${new Date(p.date+'T12:00').toLocaleDateString(undefined,{month:'short'})}</text>`;lastMonth=mo;}}
  return `<rect class="fp-heat fp-heat-${shade(p.n)}" x="${cx}" y="${cy}" width="${cell}" height="${cell}" rx="2"><title>${p.date}: ${plural(p.n,'review')}</title></rect>`;}).join('');
 const days=['Mon','','Wed','','Fri','',''].map((l,i)=>l?`<text x="0" y="${14+i*(cell+gap)+9}">${l}</text>`:'').join('');
 return `<div class="fp-heatwrap"><svg class="vp-chart fp-heatmap" viewBox="0 0 ${w} ${h}" role="img" aria-label="Reviews per day, last 12 months">${months}${days}${sq}</svg></div>`;
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
function timing(d){
 const t=d.time;if(!t)return empty('No timed answers yet.');
 const label=k=>{const w=d.byKey.get(k);return w?`<a href="word-bank.html?word=${encodeURIComponent(k)}">${esc(w.arabizi)}</a> <span lang="ar">${esc(w.arabic||'')}</span>`:esc(/^q:/.test(k)?'Quizlet card '+k.split(':').slice(1).join(' #'):k);};
 return `<div class="vp-foot fp-foot-top"><div>Average<b>${secs(t.avg)}</b></div><div>Median<b>${secs(t.median)}</b></div><div>Timed answers<b>${n(t.n)}</b></div></div><ol class="fp-slow">${t.slowest.map(s=>`<li><span>${label(s.key)}</span><b>${secs(s.avg)}</b><small>${plural(s.n,'answer')}</small></li>`).join('')}</ol><p class="ab-sub">Visible time only. Slow answers are shown, never used to change a grade.</p>`;
}
function hourly(d){
 const x=d.hours;if(!x.total)return empty('Needs a few weeks of reviews.');
 return `<div class="${x.faded?'fp-faded':''}">${bars(x.hours.map(h=>({x:String(h.hour),v:h.n,title:`${h.hour}:00–${h.hour}:59 · ${plural(h.n,'answer')} · ${pct(h.pct)} right`,cls:h.n&&h.pct<70?'fp-bar-low':''})),{label:'Answers per hour of day',labelEvery:3,h:170})}</div>${x.faded?`<p class="ab-sub">Needs a few weeks of reviews: ${n(x.total)} of 100 answers so far.</p>`:''}`;
}
function queueTable(d){
 const list=leechOnly?d.leeches:d.queue.items;
 const head=`<div class="fp-qhead"><div class="vp-minipills" role="group" aria-label="Queue view"><button class="fp-minipill" data-q="today" aria-pressed="${!leechOnly}">Today's queue ${n(d.queue.items.length)}</button><button class="fp-minipill" data-q="leech" aria-pressed="${leechOnly}" ${d.leeches.length?'':'disabled'}>Leeches ${n(d.leeches.length)}</button></div><button class="vp-showall" id="fp-undo" ${lastAnswer?'':'disabled'}>↺ Undo last</button></div>`;
 if(!list.length)return head+empty(leechOnly?'No leech cards.':d.queue.nextLearning?`All done for now. Next learning card comes back at ${new Date(d.queue.nextLearning).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}.`:'All done for today.');
 const phaseName={new:'New',learning:'Learning',mature:'Mature'};
 const rows=list.map(c=>{const w=d.byKey.get(c.id);if(!w)return '';const ph=F.phase(c),shown=reveal.has(c.id);
  const interval=!c.reps?'—':c.state==='review'?plural(c.interval,'day'):'< 1 day';
  return `<tr data-key="${esc(c.id)}"><td class="fp-word"><b>${esc(w.arabizi)}</b><span lang="ar" dir="rtl">${esc(w.arabic||'')}</span></td><td class="fp-en">${shown?esc(w.english):`<button class="fp-reveal" data-reveal="${esc(c.id)}">Tap to show</button>`}</td><td><span class="fp-phase fp-phase-${ph}">${phaseName[ph]}</span>${F.isLeech(c)?' <span class="fp-phase fp-phase-leech">Leech</span>':''}</td><td class="fp-num">${interval}</td><td class="fp-num">${n(c.lapses)}<span class="fp-mlabel"> ${c.lapses===1?'lapse':'lapses'}</span></td><td class="fp-grade"><button class="fp-miss" data-grade="missed" aria-label="Don't know ${esc(w.arabizi)}">✗ Don't know</button><button class="fp-got" data-grade="got" aria-label="Know ${esc(w.arabizi)}">✓ Know it</button></td></tr>`;}).join('');
 return head+`<div class="fp-tablewrap"><table class="fp-table fp-queue"><thead><tr><th>Arabic word</th><th>English</th><th>Phase</th><th>Interval</th><th>Lapses</th><th><span class="fp-sr">Grade</span></th></tr></thead><tbody>${rows}</tbody></table></div><p class="ab-sub">Same queue and order as Flashcards · ${n(d.queue.counts.due)} due · ${n(d.queue.counts.new)} new · ${n(d.queue.counts.learning)} learning${d.queue.buried?` · ${n(d.queue.buried)} sibling forms held for another day`:''}</p>`;
}
function render(){
 const host=$('vp-tab-flash');if(!host)return;
 if(!loaded){host.innerHTML='<div class="vp-notice">Loading your flashcard answers…</div>';return;}
 const d=build(),scrollY=window.scrollY;
 host.innerHTML=`<div class="vp-notice" id="fp-sync" role="status">${offline?'Card history is offline: numbers use this device’s saved answers.':`${plural(d.h.answers.length,'answer')} on ${plural(d.cards.size,'card')} · FSRS default parameters, not fitted to you.`}</div>
 <section class="vp-cards" aria-label="Goals and workload">${topRow(d)}</section>
 <div class="vp-grid">
 ${panel('curve','Forgetting curve & retention threshold','Average recall of every card you have answered, from your first answer to 30 days ahead. Dots = days a correct review bumped memory.',forgetting(d),{side:d.curve.length?`<div class="vp-legend"><span class="vp-key-mastered">━ Recall</span><span class="vp-key-avg">┅ Target ${Math.round(d.p.retention*100)}%</span><span class="fp-key-bump">● Bumped</span></div>`:''})}
 ${panel('week','Review forecast (next 7 days)','Cards due each day at your target retention. Today includes anything overdue.',weekForecast(d),{side:`<div class="vp-side"><b>${n(d.week.reduce((s,x)=>s+x.due,0))}</b>this week</div>`})}
 </div>
 <h2 class="fp-h">Memory segmentation</h2>
 <section class="vp-cards fp-three" aria-label="New, learning and mature cards">${segmentation(d)}</section>
 <div class="vp-grid">
 ${panel('today','Today','',todayBlock(d))}
 ${panel('rt','True retention','Review answers only: % right (passed / answered).',retentionTable(d))}
 ${panel('heat','Reviews calendar','One square per day, last 12 months.',heatmap(d),{wide:true,side:`<div class="vp-foot fp-streak"><div>Current streak<b>${plural(d.heat.current,'day')}</b></div><div>Longest<b>${plural(d.heat.longest,'day')}</b></div><div>Days studied<b>${n(d.heat.active)}</b></div></div>`})}
 ${panel('due','Future due','Cards due per day at your target retention.',futureDue(d),{side:`<div class="fp-dueside"><div class="vp-minipills" role="group" aria-label="Range"><button class="fp-minipill" data-range="30" aria-pressed="${futureRange===30}">1 month</button><button class="fp-minipill" data-range="90" aria-pressed="${futureRange===90}">3 months</button></div><span>Overdue backlog: <b>${plural(d.due.overdue,'card')}</b></span></div>`})}
 ${panel('time','Time per card','',timing(d))}
 ${panel('hist','FSRS memory states','Stability = days until recall drops to 90%. Difficulty 1 (easy) to 10 (hard). Retrievability = chance you recall it right now.',histograms(d),{wide:true})}
 ${panel('hour','Hourly breakdown','Answers per hour of day; hover for % right.',hourly(d),{wide:true})}
 ${panel('queue','Review queue','English stays hidden until you tap it. A grade saves like a flashcard answer.',queueTable(d),{wide:true})}
 </div>`;
 bind();window.scrollTo(0,scrollY);
}
function bind(){
 const host=$('vp-tab-flash');
 host.querySelectorAll('[data-ret]').forEach(b=>b.onclick=()=>{setRetention(Number(b.dataset.ret));render();});
 host.querySelectorAll('[data-range]').forEach(b=>b.onclick=()=>{futureRange=Number(b.dataset.range);render();});
 host.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{leechOnly=b.dataset.q==='leech';render();});
 const lb=$('fp-leech');if(lb)lb.onclick=()=>{leechOnly=true;render();$('fp-h-queue').scrollIntoView({behavior:'smooth',block:'start'});};
 host.querySelectorAll('[data-reveal]').forEach(b=>b.onclick=()=>{reveal.set(b.dataset.reveal,performance.now());render();});
 host.querySelectorAll('[data-grade]').forEach(b=>b.onclick=()=>grade(b.closest('tr').dataset.key,b.dataset.grade));
 const u=$('fp-undo');if(u)u.onclick=undo;
}
// One card_results row, same shape as cards.html; answer time runs from the English reveal.
function grade(key,result){
 const opened=reveal.get(key),p=pref();
 const row={id:uuid(),word_key:key,ts:new Date().toISOString(),mode:p.mode,result,attempt:1,round_id:'fsrs-'+C.dayStart(Date.now()).toString(36),subject:'fsrs',flip_ms:null,answer_ms:opened===undefined?null:Math.round(performance.now()-opened)};
 reveal.delete(key);enqueue(row);lastAnswer=row;render();
}
function undo(){
 if(!lastAnswer)return;const row=lastAnswer;lastAnswer=null;
 LS('anees-card-log',(LS('anees-card-log')||[]).map(r=>r.id===row.id?{...r,undone:true}:r));
 removeSent([row.id]);enqueue({id:'undo-'+row.id,kind:'undo',target:row.id,at:new Date().toISOString()});render();
}
/* ---------- tabs ---------- */
function show(tab){
 const flash=tab==='flashcards';
 document.querySelectorAll('.vp-tab[data-tab]').forEach(b=>b.setAttribute('aria-current',b.dataset.tab===tab?'page':'false'));
 $('vp-tab-vocab').hidden=flash;$('vp-tab-flash').hidden=!flash;
 const hz=document.querySelector('.vp-horizon');if(hz)hz.hidden=flash;
 const url=new URL(location.href);if(flash)url.searchParams.set('tab','flashcards');else url.searchParams.delete('tab');history.replaceState(null,'',url);
 if(flash){if(!loaded){render();loading=loading||load().then(render);}else render();}
}
document.querySelectorAll('.vp-tab[data-tab]').forEach(b=>b.onclick=()=>show(b.dataset.tab));
window.addEventListener('online',sync);
window.AneesFlashcardProgress={show,reload:async()=>{loaded=false;loading=null;await load();render();},build:()=>build(),get lastAnswer(){return lastAnswer;},sync};
if(new URLSearchParams(location.search).get('tab')==='flashcards')show('flashcards');
})();
