/* Progress & Stats (Vocab page). Layout = starred Stitch "Arabic Dashboard – Vocab
   Macro-Overview"; skin = Sabz. Spec: plan/PROGRESS-STATS-VOCAB-SPEC-2026-09-21.md.
   Aggregates only. Every figure comes from AneesVocabularyStats over the same
   reviewed evidence the Word Bank uses; unknown values render as "—" with a reason. */
(function(){
'use strict';
const C=window.AneesWordBank,S=window.AneesVocabularyStats,M=window.AneesVocabularyMemory,$=id=>document.getElementById(id);
const esc=window.AneesWordBankReview.escape||((s)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
const headers={apikey:ANEES.anon,Authorization:'Bearer '+ANEES.anon};
const cached=key=>{try{return JSON.parse(localStorage.getItem(key)||'null');}catch{return null;}};
const save=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));}catch{}};
// Funnel: the not-yet-checked band is hidden by default (it swamps the other three); the choice is kept per device.
let relLessons=null,rows=[],events=[],documentRows=null,period='month',newView='weekly',showUnchecked=cached('anees-vp-unchecked')===true,showAllSections=false,loading=false;
async function json(url,options={}){const r=await fetch(url,{...options,cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Request failed');return r.json();}
async function wordsLive(){const all=[];for(let offset=0;;offset+=1000){const p=await json(ANEES.url+'/rest/v1/words?select=key,arabizi,arabic,arabic_plural,english,plural,topic,subtopic,doc_order,aliases,house_spelling,active,first_seen&order=doc_order.asc,key.asc&limit=1000&offset='+offset,{headers});all.push(...p);if(p.length<1000)return all;}}
async function load(){
 if(loading)return;loading=true;$('vp-retry').hidden=true;
 try{
  const results=await Promise.allSettled([wordsLive(),window.AneesSnapshot.load(ANEES.url,headers),json('data/words.json'),json('data/word-bank-evidence.json'),json('data/word-bank-catalog.json'),json('data/word-bank-review.json'),json('data/lessons.json'),json('data/word-bank-audit-slips.json')]);
  const get=i=>results[i].status==='fulfilled'?results[i].value:null;
  const liveWords=get(0),savedWords=get(2),catalog=get(4),review=get(5);relLessons=(get(6)&&get(6).lessons)||null;let words=liveWords||cached('anees-bank-words-v2')||cached('anees-words')||savedWords?.items;
  // Supabase words has no introduced_at / doc_added_at (REST returns 400 for them); first_seen is the day the sync
  // first saw the word, and word-bank-core reads introduced_at as the add date. Saved words.json has neither.
  if(Array.isArray(words))words=words.map(w=>w.introduced_at||w.doc_added_at||!w.first_seen?w:{...w,introduced_at:w.first_seen});
  const live=get(1),published=get(3),snap=Array.isArray(live?.events)?live:published||cached('anees-speaking-evidence-v1');
  if(!Array.isArray(words)||!Array.isArray(snap?.events)||!catalog||!review)throw Error('Reviewed vocabulary evidence is unavailable.');
  if(liveWords)save('anees-bank-words-v2',liveWords);if(snap===live)save('anees-speaking-evidence-v1',live);
  const reviewed=window.AneesWordBankReview.apply(window.AneesWordBankReview.withSlips(snap.events,get(7)),review),stale=new Set(reviewed.stale);
  events=C.prepareEvidence(reviewed.events.map(e=>stale.has(e.id)?{...e,needs_review:true}:e));
  rows=C.models(words,catalog,events,[]);documentRows=words.length;
  const notes=[];if(!liveWords)notes.push('Saved vocabulary.');if(snap!==live)notes.push('Using published lesson evidence.');
  if(reviewed.stale.length)notes.push(`${reviewed.stale.length} changed source records are excluded pending review.`);
  notes.push('Numbers reflect the loaded recordings only.');$('vp-notice').textContent=notes.join(' ');
  $('vp-content').hidden=false;render();
 }catch(e){$('vp-content').hidden=true;$('vp-notice').textContent='The reviewed vocabulary could not load. No scores have been substituted. Please retry.';$('vp-retry').hidden=false;}
 finally{loading=false;}
}
/* ---------- formatting ---------- */
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const pct=v=>v===null||v===undefined?'—':v+'%';
// Medi's decision 4 (2026-09-29): a score built from lessons that are not verified shows "≈"; hover/tap says why.
// Unknown release state (lessons.json did not load) counts as not verified: never shown as exact.
const LM=window.AneesLessonMath;
const relSet=()=>relLessons&&relLessons.length?relLessons:[{date:'?'}];
const pctA=v=>v===null||v===undefined?'—':(LM&&LM.approx(relSet())?'≈':'')+v+'%';
const whyA=()=>LM?LM.why(relSet()):'';
const short=d=>{const [y,m,dd]=String(d).split('-');return `${Number(m)}/${Number(dd)}`;};
const periodLabel={week:'this week',month:'this month',all:'all time'}[period]||'';
const flat=(text,title)=>`<span class="vp-trend vp-trend-flat" title="${esc(title)}">${esc(text)}</span>`;
const trend=(delta,suffix,{flatText='no change'}={})=>{if(delta===null||delta===undefined||!Number.isFinite(delta))return '';if(delta===0)return `<span class="vp-trend vp-trend-flat">${esc(flatText)}</span>`;return `<span class="vp-trend ${delta<0?'vp-trend-down':''}">${delta>0?'+':'−'}${n(Math.abs(delta))}${esc(suffix)}</span>`;};
function card({label,icon,value,unit,trendHtml='',sub='',bar='',href='',parked=false,title=''}){
 const inner=`<div class="vp-card-label"><span>${esc(label)}</span><i aria-hidden="true">${icon}</i></div><div class="vp-card-value"><span class="vp-num">${value}</span>${unit?`<span class="vp-card-unit">${esc(unit)}</span>`:''}${trendHtml}</div>${sub?`<div class="vp-card-sub">${sub}</div>`:''}${bar}`;
 return href&&!parked?`<a class="vp-card" href="${esc(href)}" title="${esc(title)}">${inner}</a>`:`<div class="vp-card ${parked?'vp-card-parked':''}" title="${esc(title)}">${inner}</div>`;
}
/* ---------- cards ---------- */
function renderTop(){
 const t=S.topCards(rows,events,new Date(),period);
 const waiting=''; // No queue feed is published; nothing is shown rather than a guess.
 $('vp-top').innerHTML=[
  // Lessons + Lesson hours: totals come from data/lessons.json (one row per lesson, audio length) once it loads, so they match the
  // Overview tab's "Lessons tracked"; the "+N this week" trend stays pill-scoped from the speaking evidence (Overview audit 2026-09-27).
  `<div id="vp-lessons">${card({label:'Lessons',icon:'◷',value:n(t.lessons.count),trendHtml:trend(t.lessons.week,' this week'),sub:t.lessons.count?`<b>${n(t.lessons.loaded)}</b> loaded in total · last week ${n(t.lessons.lastWeek)}${waiting} · from speaking evidence`:'No recordings loaded yet',href:'index.html#lessons',title:'Open Lessons & Audio'})}</div>`,
  `<div id="vp-hours">${card({label:'Lesson hours',icon:'◔',value:t.lessons.count?n(t.hours.total):'0',unit:'h',trendHtml:trend(t.hours.week,' h this week'),sub:t.hours.avgMinutes!==null?`<b>${n(t.hours.avgMinutes)} min</b> per lesson on average · from speaking evidence`:'No recordings loaded yet',href:'index.html#lessons',title:'Open Lessons & Audio'})}</div>`,
  card({label:'Words known',icon:'✓',value:n(t.known.count),unit:'forms',trendHtml:trend(t.known.week,' this week'),sub:t.known.total?`<b>${pct(t.known.pct)}</b> of ${n(t.known.total)} studied forms · <b>${pct(t.known.pctExercised)}</b> of the ${n(t.known.exercised)} forms any lesson has used · Mastered <b>${n(t.known.mastered)}</b>`:'No scored lessons yet',bar:t.known.total?`<div class="vp-card-bar"><span style="width:${t.known.pct}%;background:var(--vp-forest)"></span></div>`:'',href:'word-bank.html?status=Good,Mastered',title:`Open Word Bank · Good + Mastered. Studied forms count every slot on Amal's list (each verb tense, each plural). "Used" forms were said or heard in a lesson, or belong to a form type the lessons exercise; ${n(t.known.total-t.known.exercised)} slots have never come up.`}),
  // Talk time is measured (both voices separate on every lesson, data/lessons.json talk.*) - Medi 2026-09-27 "isn't this done"
  `<div id="vp-talk">${card({label:'Talk time',icon:'◌',value:'…',sub:'Loading from the lessons…'})}</div>`
 ].join('');
 json('data/lessons.json').then(d=>{
  const all=(d.lessons||d).slice().sort((a,b)=>a.date<b.date?1:-1),r1=v=>Math.round(v*10)/10,pl={week:'this week',month:'this month',all:'all time'}[period]||period;
  // Lessons / Lesson hours from lessons.json (one row per lesson; duration_min = the audio the lesson page plays).
  const D=all.filter(l=>l.duration_min!=null),hrs=r1(D.reduce((a,l)=>a+l.duration_min,0)/60),avgMin=D.length?Math.round(D.reduce((a,l)=>a+l.duration_min,0)/D.length):null;
  const diffN=all.length!==t.lessons.loaded||t.lessons.count!==all.length,diffH=Math.abs(hrs-t.hours.total)>=.1;
  const cmpN=`lessons.json: ${all.length} lessons · speaking evidence: ${n(t.lessons.loaded)} loaded, ${n(t.lessons.count)} ${pl}`;
  const cmpH=`lessons.json: ${hrs} h of lesson audio · speaking evidence: ${n(t.hours.total)} h of speaking events ${pl}`;
  const eN=document.getElementById('vp-lessons'),eH=document.getElementById('vp-hours');
  if(eN&&all.length)eN.innerHTML=card({label:'Lessons',icon:'◷',value:n(all.length),trendHtml:trend(t.lessons.week,' this week'),sub:`<b>${n(D.length)}</b> with audio · last week ${n(t.lessons.lastWeek)} · from lessons.json (one row per lesson)${diffN?' · <span title="'+esc(cmpN)+'">differs from speaking evidence</span>':''}`,href:'index.html#lessons',title:'Open Lessons & Audio · '+cmpN});
  if(eH&&D.length)eH.innerHTML=card({label:'Lesson hours',icon:'◔',value:n(hrs),unit:'h',trendHtml:trend(t.hours.week,' h this week'),sub:`<b>${n(avgMin)} min</b> per lesson on average · from lessons.json (audio length)${diffH?' · <span title="'+esc(cmpH)+'">differs from speaking evidence</span>':''}`,href:'index.html#lessons',title:'Open Lessons & Audio · '+cmpH});
  // Talk time (kept: hours you spoke + last lesson share). Average share is pooled = Σ your seconds ÷ Σ both, not a mean of percentages.
  const L=all.filter(l=>l.talk&&l.talk.medi_s!=null);
  if(!L.length)return;
  const h=L.reduce((a,l)=>a+l.talk.medi_s,0)/3600,last=L[0].talk,both=L.reduce((a,l)=>a+l.talk.medi_s+(l.talk.amal_s||0),0),avg=both?r1(100*h*3600/both):null;
  const el=document.getElementById('vp-talk');
  if(el)el.innerHTML=card({label:'Talk time',icon:'◌',value:r1(h).toLocaleString(),unit:'h you spoke',
   sub:`Last lesson you <b>${last.speak_pct}%</b> · Amal ${last.listen_pct}% · pooled average you ${avg===null?'—':avg+'%'} over ${L.length} lessons`,href:'lessons.html',title:'Measured from each lesson: your talking time vs Amal’s. Average = your seconds ÷ everyone’s seconds over all lessons.'});
 }).catch(()=>{});
 return t;
}
function renderVocab(){
 const v=S.vocabCards(rows,events,new Date(),period,documentRows);
 const s=v.mastered.status,st=v.studied;
 // Studied forms trend: real additions since tracking began (import-day bulk excluded), or "—" with the reason.
 const addedTitle=st.imported?`${n(st.imported.words)} words were on the list at import (${st.imported.date}) and are not counted as additions; add dates are tracked since ${st.trackingSince}.`:`Add dates are tracked since ${st.trackingSince}.`;
 const addedTrend=st.sinceTracking===null?flat('added: —','The loaded word list carries no add dates: the live sync records first_seen, the saved copy does not.'):st.sinceTracking===0?flat(`none added since ${st.trackingSince}`,addedTitle):`<span class="vp-trend" title="${esc(addedTitle)}">+${n(st.sinceTracking)} since ${esc(st.trackingSince)}</span>`;
 // A "vs previous" trend is suppressed when the previous period holds fewer than MIN_TREND_LESSONS lessons.
 const few=(count,what)=>count<S.MIN_TREND_LESSONS?flat('— vs previous',`The previous period has ${n(count)} ${what}${count===1?'':'s'}; a comparison needs at least ${S.MIN_TREND_LESSONS}.`):null;
 const plTrend=v.perLesson.previous===null||v.perLesson.avg===null?'':few(v.perLesson.previousLessons,'lesson')||trend(Math.round((v.perLesson.avg-v.perLesson.previous)*10)/10,' vs previous');
 const rTrend=v.ratio.previousRate===null||v.ratio.rate===null?'':few(v.ratio.previousLessons,'scored lesson')||trend(Math.round((v.ratio.rate-v.ratio.previousRate)*10)/10,' pts vs previous');
 $('vp-vocab').innerHTML=[
  card({label:'Studied forms',icon:'≣',value:n(v.studied.count),trendHtml:addedTrend,sub:v.studied.documentRows?`<b>${n(v.studied.documentRows)}</b> words in Amal's list · verb tenses and plurals counted separately`:'Vocabulary list not synced',href:'word-bank.html',title:'Open Word Bank'}),
  card({label:'Mastered',icon:'★',value:n(v.mastered.count),trendHtml:trend(v.mastered.trend,` ${periodLabel}`),sub:`<b>${pct(v.mastered.pct)}</b> of studied forms · <b>${pct(v.mastered.pctExercised)}</b> of the ${n(v.mastered.exercised)} forms any lesson has used<div class="vp-card-status"><span>Good <b>${n(s.Good)}</b></span><span>Shaky <b>${n(s.Shaky)}</b></span><span>Wrong <b>${n(s.Wrong)}</b></span><span>Not yet checked <b>${n(s.Untested)}</b></span></div>`,href:'word-bank.html?status=Mastered',title:`Open Word Bank · Mastered. The second share leaves out the ${n(v.studied.count-v.mastered.exercised)} slots no lesson has used.`}),
  card({label:'Words per lesson',icon:'∿',value:v.perLesson.avg===null?'—':n(v.perLesson.avg),trendHtml:plTrend,sub:v.perLesson.peak?`Peak <b>${n(v.perLesson.peak.count)}</b> on ${esc(v.perLesson.peak.date)} · distinct forms you said, ${n(v.perLesson.lessons)} lessons`:'No scored lessons in this period',href:'word-bank.html?sort=recent',title:'Open Word Bank · most recent first'}),
  card({label:'Correct vs slips',icon:'◑',value:pctA(v.ratio.rate),trendHtml:rTrend,sub:v.ratio.total?`<b>${n(v.ratio.correct)}</b> correct · <b>${n(v.ratio.hinted)}</b> hinted · <b>${n(v.ratio.wrong)}</b> wrong — of the words you attempted from Amal's list, hints counted as slips<br>Same attempts as the Lessons page, audit slips included; its <b>Vocab %</b> counts a hint as half right`:'No scored attempts in this period',bar:v.ratio.total?`<div class="vp-card-bar"><span style="width:${v.ratio.correct/v.ratio.total*100}%;background:var(--ab-green)"></span><span style="width:${v.ratio.hinted/v.ratio.total*100}%;background:var(--ab-orange)"></span><span style="width:${v.ratio.wrong/v.ratio.total*100}%;background:var(--ab-red)"></span></div>`:'',href:'word-bank.html?status=Shaky,Wrong',title:"Full-credit attempts ÷ all scored attempts on words from Amal's list, hints counted as slips. Same attempts as the Lessons page (the lesson audit's word slips are in the Word Bank evidence since 2026-09-29); the Overview's Vocab % counts a hint as half right instead. Opens Word Bank · Shaky + Wrong. "+whyA()})
 ].join('');
}
/* ---------- SVG helpers ---------- */
const W=640,H=250,PAD={l:38,r:14,t:16,b:34};
const empty=text=>`<div class="vp-empty">${esc(text)}</div>`;
function frame(inner,label){return `<svg class="vp-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${inner}</svg>`;}
function scales(count,maxY){const x=i=>PAD.l+(W-PAD.l-PAD.r)*(count===1?.5:i/(count-1)),y=v=>H-PAD.b-(H-PAD.b-PAD.t)*(maxY?v/maxY:0);return {x,y};}
function grid(y,maxY,fmt=v=>n(v)){return [0,.25,.5,.75,1].map(f=>`<line class="vp-gridline" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(maxY*f).toFixed(1)}" y2="${y(maxY*f).toFixed(1)}"/><text x="${PAD.l-6}" y="${(y(maxY*f)+3.5).toFixed(1)}" text-anchor="end">${fmt(Math.round(maxY*f))}</text>`).join('');}
function xLabels(series,x){const step=Math.ceil(series.length/8);return series.map((p,i)=>i%step===0||i===series.length-1?`<text class="vp-lesson-label" x="${x(i).toFixed(1)}" y="${H-10}" text-anchor="middle">${short(p.date)}</text>`:'').join('');}
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v)));const r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
/* ---------- charts ---------- */
function renderFunnel(){
 const f=S.funnel(rows,events,new Date(),period),last=f.at(-1);
 $('vp-funnel-legend').innerHTML=last?[['mastered','Mastered'],['good','Good'],['weak','Shaky + Wrong'],['unchecked','Not yet checked']].map(([k,l])=>k==='unchecked'?`<button class="vp-key-${k}" id="vp-toggle-unchecked" aria-pressed="${showUnchecked}" title="${showUnchecked?'Hide':'Show'} the not-yet-checked band (${n(last[k])} forms). Remembered on this device.">${showUnchecked?'●':'○'} ${l} ${n(last[k])}${showUnchecked?'':' · hidden'}</button>`:`<span class="vp-key-${k}">● ${l} ${n(last[k])}</span>`).join(''):'';
 const toggle=$('vp-toggle-unchecked');if(toggle)toggle.onclick=()=>{showUnchecked=!showUnchecked;save('anees-vp-unchecked',showUnchecked);renderFunnel();};
 if(!f.length){$('vp-funnel').innerHTML=empty('The chart appears after the first scored lesson in this period.');return;}
 const bands=showUnchecked?['mastered','good','weak','unchecked']:['mastered','good','weak'];
 const totals=f.map(p=>bands.reduce((s,k)=>s+p[k],0)),maxY=niceMax(Math.max(...totals)),{x,y}=scales(f.length,maxY);
 let base=f.map(()=>0),areas='';
 for(const k of bands){const top=f.map((p,i)=>base[i]+p[k]);const d=f.map((p,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(top[i]).toFixed(1)}`).join(' ')+' '+f.map((p,i)=>`L${x(f.length-1-i).toFixed(1)},${y(base[f.length-1-i]).toFixed(1)}`).join(' ')+' Z';areas+=`<path class="vp-area-${k}" d="${d}"><title>${k}</title></path>`;base=top;}
 const hover=f.map((p,i)=>`<rect x="${(x(i)-6).toFixed(1)}" y="${PAD.t}" width="12" height="${H-PAD.t-PAD.b}" fill="transparent"><title>${p.date}: ${n(p.mastered)} mastered · ${n(p.good)} good · ${n(p.weak)} shaky/wrong · ${n(p.unchecked)} not yet checked</title></rect>`).join('');
 $('vp-funnel').innerHTML=frame(grid(y,maxY)+areas+hover+xLabels(f,x),`Vocabulary funnel across ${f.length} lessons${showUnchecked?'':' (not-yet-checked band hidden)'}`);
}
function renderRetention(p){
 // Lessons that tested fewer than MIN known words are drawn faded; "Current" is the latest lesson with enough.
 const MIN=S.MIN_RETENTION_TESTED,s=p.series.filter(l=>l.retention!==null),last=s.at(-1),cur=s.filter(l=>l.tested>=MIN).at(-1)||null;
 $('vp-retention-side').innerHTML=cur?`<b title="${esc(whyA())}">${pctA(cur.retention)}</b>${n(cur.tested)} known words tested on ${esc(cur.date)}${last&&last!==cur?`<br>latest lesson (${esc(last.date)}) tested only ${n(last.tested)}, not used`:''}`:last?`<b>—</b>no lesson has tested ${MIN}+ known words yet (latest: ${n(last.tested)} on ${esc(last.date)})`:'';
 if(!s.length){$('vp-retention').innerHTML=empty('Appears once a word you already knew is tested again in a later lesson.');return;}
 const {x,y}=scales(s.length,100);
 const line=s.map((l,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(l.retention).toFixed(1)}`).join(' ');
 const dots=s.map((l,i)=>{const faded=l.tested<MIN;return `<circle class="vp-dot${faded?' vp-dot-faded':''}" cx="${x(i).toFixed(1)}" cy="${y(l.retention).toFixed(1)}" r="3.5"><title>${l.date}: ${pct(l.retention)} · ${n(l.retained)} of ${n(l.tested)} known words recalled${faded?` · fewer than ${MIN} tested, shown faded`:''}</title></circle>`;}).join('');
 const ci=cur?s.indexOf(cur):-1;
 const callout=cur?`<text class="vp-callout" x="${x(ci).toFixed(1)}" y="${(y(cur.retention)-9).toFixed(1)}" text-anchor="${ci>=s.length/2?'end':'start'}">Current: ${pct(cur.retention)} (${short(cur.date)}, n ${n(cur.tested)})</text>`:'';
 const under=s.map((l,i)=>`<text class="vp-lesson-label" x="${x(i).toFixed(1)}" y="${H-10}" text-anchor="middle">${short(l.date)} (${n(l.tested)})</text>`).join('');
 $('vp-retention').innerHTML=frame(grid(y,100,v=>v+'%')+`<path class="vp-line" d="${line}"/>`+dots+callout+under,`Retention across ${s.length} lessons; dots from fewer than ${MIN} tested words are faded`);
}
function renderRatio(p){
 const s=p.series;
 if(!s.length){$('vp-ratio').innerHTML=empty('The chart appears after the first scored lesson in this period.');$('vp-ratio-foot').innerHTML='';return;}
 const slot=(W-PAD.l-PAD.r)/s.length,bw=Math.min(46,slot*.62),{y}=scales(s.length,100);
 const bars=s.map((l,i)=>{const x0=PAD.l+slot*i+(slot-bw)/2,h=v=>(H-PAD.b-PAD.t)*v/l.total;const cH=h(l.correct),hH=h(l.hinted),wH=h(l.wrong);let yy=H-PAD.b;const seg=(cls,hh)=>{yy-=hh;return hh>0?`<rect class="${cls}" x="${x0.toFixed(1)}" y="${yy.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" rx="2"/>`:'';};return `<g><title>${l.date}: ${n(l.correct)} correct · ${n(l.hinted)} hinted · ${n(l.wrong)} wrong</title>${seg('vp-bar-correct',cH)}${seg('vp-bar-hinted',hH)}${seg('vp-bar-wrong',wH)}<text class="vp-callout" x="${(x0+bw/2).toFixed(1)}" y="${PAD.t-4}" text-anchor="middle">${pct(l.rate)}</text><text class="vp-lesson-label" x="${(x0+bw/2).toFixed(1)}" y="${H-10}" text-anchor="middle">${short(l.date)}</text></g>`;}).join('');
 // Dashed line and foot use the pooled rate (all correct ÷ all attempts), not a mean of per-lesson rates.
 const pooledTitle=`All correct attempts ÷ all attempts across the shown lessons: ${n(p.pooled.correct)} of ${n(p.pooled.total)}. Lessons weigh by their attempts, not equally.`;
 const avg=p.pooledRate===null?'':`<line class="vp-avg" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(p.pooledRate).toFixed(1)}" y2="${y(p.pooledRate).toFixed(1)}"><title>${esc(pooledTitle)}</title></line><text x="${W-PAD.r}" y="${(y(p.pooledRate)-4).toFixed(1)}" text-anchor="end">pooled avg ${pct(p.pooledRate)}</text>`;
 $('vp-ratio').innerHTML=frame(grid(y,100,v=>v+'%')+bars+avg,`Correct versus slips across ${s.length} lessons`);
 $('vp-ratio-foot').innerHTML=`<div>Baseline (first lesson)<b>${pctA(p.baseline)}</b></div><div title="${esc(pooledTitle+' '+whyA())}">Average (pooled)<b>${pctA(p.pooledRate)}</b></div>${p.best?`<div>Best<b>${pctA(p.best.rate)} <i>on ${esc(p.best.date)}</i></b></div>`:''}`;
}
function renderUnique(p){
 const s=p.series;
 $('vp-unique-side').innerHTML=p.avgUnique!==null?`<b>${n(p.avgUnique)}</b>average per lesson`:'';
 if(!s.length){$('vp-unique').innerHTML=empty('The chart appears after the first scored lesson in this period.');$('vp-unique-foot').innerHTML='';return;}
 const maxY=niceMax(Math.max(...s.map(l=>l.unique))),{x,y}=scales(s.length,maxY);
 const line=s.map((l,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(l.unique).toFixed(1)}`).join(' ');
 const dots=s.map((l,i)=>{const peak=p.peak&&l.date===p.peak.date;return `<circle class="vp-dot ${peak?'vp-dot-peak':''}" cx="${x(i).toFixed(1)}" cy="${y(l.unique).toFixed(1)}" r="${peak?5:3.5}"><title>${l.date}: ${n(l.unique)} distinct forms</title></circle>${peak?`<text class="vp-callout" x="${x(i).toFixed(1)}" y="${(y(l.unique)-10).toFixed(1)}" text-anchor="middle">Peak: ${n(l.unique)}</text>`:''}`;}).join('');
 const avg=p.avgUnique===null?'':`<line class="vp-avg" x1="${PAD.l}" x2="${W-PAD.r}" y1="${y(p.avgUnique).toFixed(1)}" y2="${y(p.avgUnique).toFixed(1)}"/>`;
 const under=s.map((l,i)=>`<text class="vp-lesson-label" x="${x(i).toFixed(1)}" y="${H-10}" text-anchor="middle">${short(l.date)} (${n(l.unique)})</text>`).join('');
 $('vp-unique').innerHTML=frame(grid(y,maxY)+avg+`<path class="vp-line" d="${line}"/>`+dots+under,`Unique words across ${s.length} lessons`);
 $('vp-unique-foot').innerHTML=`<div>Average<b>${n(p.avgUnique)}</b></div>${p.peak?`<div>Peak<b>${n(p.peak.count)} <i>on ${esc(p.peak.date)}</i></b></div>`:''}<div>Lessons<b>${n(s.length)}</b></div>`;
}
function renderSections(){
 const s=S.sections(rows,{exercised:true}),shown=showAllSections?s:s.slice(0,8);
 $('vp-sections-side').innerHTML=s.length?`<b>${n(s.length)}</b>sections in Amal's list`:'';
 if(!s.length){$('vp-sections').innerHTML=empty('Sections appear after the vocabulary list syncs.');return;}
 $('vp-sections').innerHTML=shown.map(v=>`<a class="vp-section" href="word-bank.html?topic=${encodeURIComponent(v.name)}" title="Open Word Bank · ${esc(v.name)}. ${n(v.total-v.exercised)} of its ${n(v.total)} forms have never come up in a lesson."><div class="vp-section-head"><b>${esc(v.name)}</b><span>${n(v.known)} known / ${n(v.total)} total · ${n(v.exercised)} used</span></div><div class="vp-section-track"><div class="vp-section-fill" style="width:${v.total?v.known/v.total*100:0}%"></div></div><div class="vp-section-sub"><span>${v.total?Math.round(v.known/v.total*100):0}% known · ${v.exercised?Math.round(v.known/v.exercised*100)+'%':'—'} of forms any lesson has used</span><span>${n(v.total-v.known)} not known yet</span></div></a>`).join('')+(s.length>8?`<button class="vp-showall" id="vp-showall">${showAllSections?'Show top 8':`Show all ${s.length} sections`}</button>`:'');
 const b=$('vp-showall');if(b)b.onclick=()=>{showAllSections=!showAllSections;renderSections();};
}
function renderNew(){
 const d=S.newWords(rows,new Date(),period);
 document.querySelectorAll('.vp-minipill').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.newview===newView)));
 if(!d){$('vp-new').innerHTML=empty('No add dates in the loaded word list. The live sync records the day each word first appeared (first_seen); the saved copy does not.');$('vp-new-foot').innerHTML=`<div>Total added<b>—</b></div><div>Per week<b>—</b></div><div>Peak week<b>—</b></div><div>Still known<b>—</b></div>`;return;}
 const importNote=d.imported?`${n(d.imported.words)} words were on the list at import (${d.imported.date}) and are not shown as additions.`:'';
 let series=d.series;
 if(newView==='monthly'){const m=new Map();for(const p of series){const k=p.week.slice(0,7);m.set(k,(m.get(k)||0)+p.added);}let run=0;series=[...m].map(([k,a])=>({week:k,added:a,cumulative:(run+=a)}));}
 if(!series.length){$('vp-new').innerHTML=empty(`No words added in this period. Add dates are tracked since ${d.trackingSince}. ${importNote}`.trim());}
 else{
  const cumulative=newView==='cumulative',maxBar=niceMax(Math.max(...series.map(p=>p.added))),maxLine=niceMax(Math.max(...series.map(p=>p.cumulative))),maxY=cumulative?maxLine:maxBar,{x,y}=scales(series.length,maxY),slot=(W-PAD.l-PAD.r)/series.length,bw=Math.min(40,slot*.55);
  const bars=cumulative?'':series.map((p,i)=>`<rect class="vp-bar-new ${d.peak&&p.added===d.peak.added?'vp-bar-new-peak':''}" x="${(x(i)-bw/2).toFixed(1)}" y="${y(p.added).toFixed(1)}" width="${bw.toFixed(1)}" height="${(H-PAD.b-y(p.added)).toFixed(1)}" rx="3"><title>${p.week}: +${n(p.added)}</title></rect>`).join('');
  const line=series.map((p,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(cumulative?p.cumulative:p.cumulative*maxBar/maxLine).toFixed(1)}`).join(' ');
  const under=series.map((p,i)=>`<text class="vp-lesson-label" x="${x(i).toFixed(1)}" y="${H-10}" text-anchor="middle">${newView==='monthly'?p.week:short(p.week)} (+${n(p.added)})</text>`).join('');
  $('vp-new').innerHTML=frame(grid(y,maxY)+bars+`<path class="vp-line" d="${line}"/>`+under,`New words over ${series.length} periods`);
 }
 $('vp-new-foot').innerHTML=`<div title="Forms added since ${esc(d.trackingSince)}; a verb counts its four tenses, a noun its plural">Total added<b>${n(d.total)} <i>forms · ${n(d.words)} words</i></b></div><div>Per week<b>${n(d.perWeek)}</b></div><div>Peak week<b>${d.peak?`${n(d.peak.added)} <i>${esc(d.peak.week)}</i>`:'—'}</b></div><div>Still known<b>${pct(d.stillKnownPct)}</b></div>${d.imported?`<div title="${esc(importNote)}">On the list at import<b>${n(d.imported.words)} <i>words · ${esc(d.imported.date)}</i></b></div>`:''}`;
}
function render(){
 const t=renderTop();renderVocab();
 const p=S.perLesson(rows,events,new Date(),period);
 renderFunnel();renderRetention(p);renderRatio(p);renderUnique(p);renderSections();renderNew();
 $('vp-footer').textContent=t.lessons.loaded?`${n(t.lessons.loaded)} lessons loaded · last lesson ${t.lessons.latest} · ${n(events.filter(e=>e.speaker==='Medi'&&e.needs_review).length)} learner events awaiting review`:'No lessons loaded yet';
 document.dispatchEvent(new CustomEvent('anees:vocab-rendered')); // vocab-angles.js re-renders on load and on pill change (2026-09-27)
}
document.querySelectorAll('.vp-pill').forEach(b=>b.onclick=()=>{period=b.dataset.period;document.querySelectorAll('.vp-pill').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));render();});
document.querySelectorAll('.vp-minipill').forEach(b=>b.onclick=()=>{newView=b.dataset.newview;renderNew();});
$('vp-retry').onclick=load;
window.AneesVocabularyProgress={reload:load,get rows(){return rows;},get events(){return events;},get period(){return period;}};load();
})();
