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
function aggregate(){
 const now=M.today(new Date()),cut=now-period;
 const valid=rows.filter(r=>!r.grammar_only),all=stats.all;
 const topicMap=new Map();
 for(const x of all){const name=x.row.topic||'Other',v=topicMap.get(name)||{total:0,known:0,attempted:0};v.total++;v.known+=['Good','Mastered'].includes(x.form.speaking.status);v.attempted+=x.form.speaking.status!=='Untested';topicMap.set(name,v);}
 const topics=[...topicMap].map(([name,v])=>({name,...v,rate:v.attempted?Math.round(v.known/v.attempted*100):0})).sort((a,b)=>b.total-a.total||a.name.localeCompare(b.name));
 const attempts=all.flatMap(x=>x.form.speaking.attempts).filter(e=>{const d=M.day(C.date(e));return d!==null&&d<=now&&d>cut;});
 const recall={Independent:attempts.filter(e=>e.p===1).length,Assisted:attempts.filter(e=>e.p===.5).length,Missed:attempts.filter(e=>e.p===0).length};
 const typeMap=new Map();for(const r of valid){const type=r.type||'Word',v=typeMap.get(type)||{forms:0,known:0};for(const f of r.entries){v.forms++;v.known+=['Good','Mastered'].includes(f.speaking.status);}typeMap.set(type,v);}
 return {topics,recall,types:[...typeMap].map(([name,v])=>({name,...v})).sort((a,b)=>b.forms-a.forms),attempts};
}
function topicRows(items){return items.slice(0,8).map(v=>`<div class="vp-topic"><div><strong>${esc(v.name)}</strong><span>${v.known} known · ${v.total} studied forms</span></div><div class="vp-ring" style="--p:${v.rate}">${v.attempted?v.rate+'%':'—'}</div></div>`).join('')||'<p class="ab-sub">Topic totals will appear when vocabulary is available.</p>';}
function recallView(data){const total=Object.values(data).reduce((a,b)=>a+b,0);return `<div class="vp-donut" style="--ind:${total?data.Independent/total*100:0};--assist:${total?(data.Independent+data.Assisted)/total*100:0}"><span><strong>${total}</strong><small>scored attempts</small></span></div><div class="vp-key">${Object.entries(data).map(([k,n],i)=>`<div><i class="vp-dot vp-dot-${i}"></i><span>${k}</span><strong>${n}</strong></div>`).join('')}</div>`;}
function typeRows(items){const max=Math.max(1,...items.map(x=>x.forms));return items.slice(0,7).map(v=>`<div class="vp-type"><div><strong>${esc(v.name)}</strong><span>${v.known}/${v.forms} known</span></div><span class="vp-track"><span class="vp-fill" style="width:${v.forms/max*100}%"></span></span></div>`).join('');}
function milestones(series,a){
 if(!series.length)return '<p class="ab-sub">Milestones will appear after scored lesson evidence is available.</p>';
 const end=series.at(-1),first=series[0],marks=[[first.date,'First recorded vocabulary evidence']];
 for(const n of [25,50,100,250,500,1000]){const hit=series.find(x=>x.known>=n);if(hit)marks.push([hit.date,`${n} forms reached Good or Mastered`]);}
 marks.push([end.date,`${end.known} known · ${end.mastered} mastered now`]);
 return [...new Map(marks.map(x=>[x.join('|'),x])).values()].slice(-6).reverse().map(([date,label],i)=>`<div class="vp-milestone"><i>${i?'':'◆'}</i><div><strong>${esc(label)}</strong><span>${esc(date)}</span></div></div>`).join('');
}
function render(){
 stats=M.summary(rows,new Date(),period);
 const metrics=[['Words known',stats.known,'Good + Mastered'],['Mastered',stats.mastered,'Across separate lessons'],[`Practised · ${period} days`,stats.practised,'Unique scored entries'],[`Newly added · ${period} days`,stats.newCount,'Document dates '+(stats.newCount===null?'not yet recorded':'verified')],['Memory at risk',stats.atRisk,'At risk + High risk'],['Not yet checked',stats.unchecked,'No scored evidence']];
 $('vp-metrics').innerHTML=metrics.map(([title,n,desc])=>`<div class="ab-metric"><div class="ab-metric-label">${esc(title)}</div><div class="ab-number">${n===null?'—':n.toLocaleString()}</div><div class="ab-tiny">${esc(desc)}</div></div>`).join('');
 const series=M.growth(rows,new Date(),period),a=aggregate();
 $('vp-status-bars').innerHTML=bars(stats.statusCounts,'status');$('vp-memory-bars').innerHTML=bars(stats.memoryCounts,'memory');
 $('vp-growth').innerHTML=chart(series);$('vp-topics').innerHTML=topicRows(a.topics);$('vp-recall').innerHTML=recallView(a.recall);$('vp-types').innerHTML=typeRows(a.types);$('vp-milestones').innerHTML=milestones(series,a);
}
$('vp-period').onchange=e=>{period=Number(e.target.value);render();};$('vp-retry').onclick=load;
window.AneesVocabularyProgress={reload:load,get rows(){return rows;},get stats(){return stats;}};load();
})();
