(function(){
'use strict';
const C=window.AneesWordBank,M=window.AneesVocabularyMemory,$=id=>document.getElementById(id);
const esc=window.AneesWordBankReview.escape||((s)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
const headers={apikey:ANEES.anon,Authorization:'Bearer '+ANEES.anon};
let rows=[],events=[],stats=null,period=30,loading=false;
const cached=key=>{try{return JSON.parse(localStorage.getItem(key)||'null');}catch{return null;}};
const save=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));}catch{}};
async function json(url,options={}){const r=await fetch(url,{...options,cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Request failed');return r.json();}
async function wordsLive(){const all=[];for(let offset=0;;offset+=1000){const p=await json(ANEES.url+'/rest/v1/words?select=key,arabizi,arabic,arabic_plural,english,plural,topic,subtopic,doc_order,aliases,house_spelling,active&order=doc_order.asc,key.asc&limit=1000&offset='+offset,{headers});all.push(...p);if(p.length<1000)return all;}}
async function load(){
 if(loading)return;loading=true;$('vp-retry').hidden=true;
 try{
  const results=await Promise.allSettled([wordsLive(),json(ANEES.url+'/rest/v1/rpc/speaking_snapshot',{headers}),json('data/words.json'),json('data/word-bank-evidence.json'),json('data/word-bank-catalog.json'),json('data/word-bank-review.json')]);
  const get=i=>results[i].status==='fulfilled'?results[i].value:null;
  const liveWords=get(0),savedWords=get(2),catalog=get(4),review=get(5);let words=liveWords||cached('anees-bank-words-v2')||cached('anees-words')||savedWords?.items;
  const live=get(1),published=get(3),snap=Array.isArray(live?.events)?live:published||cached('anees-speaking-evidence-v1');
  if(!Array.isArray(words)||!Array.isArray(snap?.events)||!catalog||!review)throw Error('Reviewed vocabulary evidence is unavailable.');
  if(liveWords)save('anees-bank-words-v2',liveWords);if(snap===live)save('anees-speaking-evidence-v1',live);
  const reviewed=window.AneesWordBankReview.apply(snap.events,review),stale=new Set(reviewed.stale);
  events=C.prepareEvidence(reviewed.events.map(e=>stale.has(e.id)?{...e,needs_review:true}:e));
  rows=C.models(words,catalog,events,[]);
  const dates=[...new Set(events.map(C.date).filter(d=>M.day(d)!==null))].sort();
  $('vp-coverage').textContent=dates.length?`${dates.length} recorded lesson dates · ${dates[0]} – ${dates.at(-1)}`:'No recorded lessons yet';
  const notes=[];if(!liveWords)notes.push('Saved vocabulary.');if(snap!==live)notes.push('Using published lesson evidence.');
  if(reviewed.stale.length)notes.push(`${reviewed.stale.length} changed source records are excluded pending review.`);
  notes.push('Estimates reflect the available recordings.');$('vp-notice').textContent=notes.join(' ');
  $('vp-content').hidden=false;render();
 }catch(e){$('vp-content').hidden=true;$('vp-notice').textContent='The reviewed vocabulary could not load. No scores have been substituted. Please retry.';$('vp-retry').hidden=false;}
 finally{loading=false;}
}
const color=key=>({Mastered:'green',Good:'blue',Shaky:'orange',Wrong:'red',Untested:'muted',strong:'green',fading:'orange',risk:'red',high:'red',unchecked:'muted','no-recall':'muted'}[key]||'accent');
function bars(counts,type){return Object.entries(counts).map(([key,n])=>{const name=type==='memory'?M.LABELS[M.KEYS.indexOf(key)]:key;return `<div class="vp-bar" aria-label="${esc(name)}: ${n}"><span>${esc(name)}</span><span class="vp-track"><span class="vp-fill" style="width:${stats.total?n/stats.total*100:0}%;background:var(--ab-${color(key)})"></span></span><strong>${n.toLocaleString()}</strong></div>`;}).join('');}
function chart(series){
 if(!series.length)return '<p class="ab-sub">A growth chart will appear when scored lesson evidence is available.</p>';
 const max=Math.max(1,...series.map(p=>p.known)),top=Math.ceil(max/5)*5,W=940,H=245,left=40,right=18,bottom=35;
 const x=i=>left+(W-left-right)*(series.length===1?.5:i/(series.length-1)),y=n=>H-bottom-(H-bottom-15)*n/top;
 const path=key=>series.map((p,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(p[key]).toFixed(1)).join(' ');
 const label=p=>p.date.slice(5).replace('-','/');
 const grid=[0,.5,1].map(f=>`<line class="vp-gridline" x1="${left}" x2="${W-right}" y1="${y(top*f)}" y2="${y(top*f)}"/><text x="${left-8}" y="${y(top*f)+4}" text-anchor="end">${Math.round(top*f)}</text>`).join('');
 const ticks=[...new Set([0,Math.floor((series.length-1)/2),series.length-1])].map(i=>`<text x="${x(i)}" y="${H-8}" text-anchor="middle">${label(series[i])}</text>`).join('');
 const dots=series.map((p,i)=>`<circle cx="${x(i)}" cy="${y(p.known)}" r="${series.length===1?4:2}" fill="var(--ab-accent)"><title>${p.date}: ${p.known} known, ${p.mastered} mastered</title></circle>`).join('');
 return `<svg class="vp-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Recorded vocabulary growth: ${series[0].known} known on ${series[0].date}, ${series.at(-1).known} on ${series.at(-1).date}">${grid}<path class="vp-known" d="${path('known')}"/><path class="vp-mastered" d="${path('mastered')}"/>${dots}${ticks}</svg><details class="vp-method"><summary>View exact daily counts</summary><table class="vp-history-table"><thead><tr><th>Date</th><th>Known</th><th>Mastered</th></tr></thead><tbody>${series.map(p=>`<tr><td>${p.date}</td><td>${p.known}</td><td>${p.mastered}</td></tr>`).join('')}</tbody></table></details>`;
}
function render(){
 stats=M.summary(rows,new Date(),period);
 const metrics=[['Words known',stats.known,'Good + Mastered'],['Mastered',stats.mastered,'Across separate lessons'],[`Practised · ${period} days`,stats.practised,'Unique scored entries'],[`Newly added · ${period} days`,stats.newCount,'Document dates '+(stats.newCount===null?'not yet recorded':'verified')],['Memory at risk',stats.atRisk,'At risk + High risk'],['Not yet checked',stats.unchecked,'No scored evidence']];
 $('vp-metrics').innerHTML=metrics.map(([title,n,desc])=>`<div class="ab-metric"><div class="ab-metric-label">${esc(title)}</div><div class="ab-number">${n===null?'—':n.toLocaleString()}</div><div class="ab-tiny">${esc(desc)}</div></div>`).join('');
 $('vp-status-bars').innerHTML=bars(stats.statusCounts,'status');$('vp-memory-bars').innerHTML=bars(stats.memoryCounts,'memory');
 $('vp-growth').innerHTML=chart(M.growth(rows,new Date(),period));
}
$('vp-period').onchange=e=>{period=Number(e.target.value);render();};$('vp-retry').onclick=load;
window.AneesVocabularyProgress={reload:load,get rows(){return rows;},get stats(){return stats;}};load();
})();
