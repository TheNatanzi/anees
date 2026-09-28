/* AI Reports › Robot blind spots › "Possible names" (names & places layer, Medi 2026-09-28: "yes").
   Words the robot could not place that look like names (capitalised mid-sentence, typed capitalised by Amal in the Meet
   chat, after fi / min / 3a / la / min 3end, seen in several lessons) - built by scripts/names.py possible into
   data/possible-names.json. Each row opens (accordion, like the other blind-spot rows) to the exact sentences, and
   takes one tap: "Name" / "Not a name". Answers go to supabase name_labels (migration 021) through a localStorage queue,
   the same pattern as the Fluency swipe check (fluency-ladder.js); nothing is lost offline or before 021 is applied.
   Privacy (the site and repo are public): a "person" answer is stored ONLY as the word's fingerprint (salted sha256,
   js/names.js fp) - never its text; a place / other answer keeps the text. The next pipeline build reads the answers
   (scripts/names.py build) so a confirmed name is matched everywhere from then on.
   API: window.AneesPossibleNames.mount(host). */
(function(){
'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v==null||Number.isNaN(v)?'—':Number(v).toLocaleString();
const LS=(k,v)=>{try{if(v===undefined)return JSON.parse(localStorage.getItem(k)||'null');localStorage.setItem(k,JSON.stringify(v));return true;}catch(e){return v===undefined?null:false;}};
const pretty=d=>{if(!d)return '—';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const mmss=t=>{t=Math.max(0,Number(t)||0);return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');};
const uuid=()=>(window.crypto&&crypto.randomUUID)?crypto.randomUUID():'nl-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10);
const SIG={capital:'capitalised mid-sentence',chat_cap:'Amal typed it capitalised',after_fi_min:'after fi / min / 3a / la'};

/* ---------- answers: name_labels, offline queue (mirror of fluency-ladder.js sentence_labels) ---------- */
const QK='anees-name-label-queue',LK='anees-name-label-log',SK='anees-name-label-server';
let memQueue=[],serverRows=LS(SK)||[],table='unknown',syncing=false,again=false,host=null;
const A=()=>window.ANEES||{};
const hdr=()=>({apikey:A().anon,Authorization:'Bearer '+A().anon,'Content-Type':'application/json'});
const readQ=()=>(LS(QK)||[]).concat(memQueue);
function answers(){  // latest row per candidate (by ts, then created_at)
 const m=new Map();for(const r of serverRows.concat(LS(LK)||[],memQueue))if(r&&r.id)m.set(r.id,Object.assign({},m.get(r.id)||{},r));
 const out=new Map();for(const r of [...m.values()].sort((a,b)=>String(a.ts).localeCompare(String(b.ts))||String(a.created_at||'').localeCompare(String(b.created_at||''))))out.set(r.cand_fp,r);
 return out;
}
async function probe(){
 if(!A().url){table='offline';return false;}
 try{
  const r=await fetch(A().url+'/rest/v1/name_labels?select=id,cand_fp,label,kind,ts,created_at&order=ts.asc,id.asc&limit=1000',{headers:hdr(),cache:'no-store',signal:AbortSignal.timeout(15000)});
  if(r.status===404||r.status===400){table='missing';return false;}   // PGRST205: migration 021 not applied yet
  if(!r.ok){table='offline';return false;}
  serverRows=await r.json();LS(SK,serverRows);table='ok';return true;
 }catch(e){table='offline';return false;}
}
function enqueue(row){
 const q=LS(QK)||[];q.push(row);const ok=LS(QK,q);
 const log=LS(LK)||[];log.push(row);LS(LK,log.slice(-1000));
 if(!ok||!(LS(QK)||[]).some(x=>x.id===row.id))memQueue.push(row);
 sync();
}
function removeSent(ids){const s=new Set(ids);LS(QK,(LS(QK)||[]).filter(x=>!s.has(x.id)));memQueue=memQueue.filter(x=>!s.has(x.id));}
async function sync(){
 if(syncing){again=true;return;}syncing=true;
 try{
  if(readQ().length&&table!=='ok')await probe();
  while(table==='ok'){
   const q=readQ();if(!q.length)break;const batch=q.slice(0,50);
   let r;try{r=await fetch(A().url+'/rest/v1/name_labels?on_conflict=id',{method:'POST',headers:{...hdr(),Prefer:'resolution=ignore-duplicates,return=minimal'},body:JSON.stringify(batch),signal:AbortSignal.timeout(15000)});}
   catch(e){table='offline';break;}
   if(r.ok){removeSent(batch.map(x=>x.id));continue;}
   if(r.status===404||r.status===400){table='missing';break;}
   table='offline';break;
  }
 }finally{syncing=false;}
 status();
 if(again){again=false;sync();}
}
function statusText(){
 const k=readQ().length,a=`${n(k)} answer${k===1?'':'s'}`;
 if(table==='missing')return k?`${a} saved on this device; they sync once the name_labels table exists (migration 021).`:'The name_labels table is not set up yet (migration 021): answers stay on this device until it is.';
 if(table==='offline')return k?`${a} waiting to sync (offline is fine).`:'Could not reach the labels table; answers are kept on this device.';
 if(table==='ok')return k?`${a} syncing…`:'All answers saved. The next build treats them as names (or not).';
 return 'Checking the labels table…';
}
function status(){const el=host&&host.querySelector('.pn-sync');if(el){el.textContent=statusText();el.dataset.state=table;}}
window.addEventListener('online',sync);

/* ---------- rendering ---------- */
let DATA=null;
function mark(sentence,word){const t=esc(sentence),w=esc(word),i=t.indexOf(w);return i<0?t:t.slice(0,i)+'<mark class="pn-mark">'+w+'</mark>'+t.slice(i+w.length);}
function row(it,ans){
 const done=ans&&ans.label;
 const verdict=done?(ans.label==='name'?`Name${ans.kind?' · '+esc(ans.kind):''}`:'Not a name'):'';
 const sig=Object.keys(it.signals||{}).map(k=>SIG[k]||k).join(' · ');
 const ex=(it.examples||[]).map(x=>`<div class="pn-ex"><div class="pn-when">${esc(pretty(x.date))} · ${mmss(x.t)} · ${esc(x.chat?'typed in the Meet chat by '+(x.who||'Amal'):x.who==='?'?'speaker unclear':x.who)}</div><div class="pn-sent" dir="auto">${mark(x.sentence,x.word)}</div></div>`).join('');
 return `<details class="pn-acc${done?' pn-done':''}" data-cand="${esc(it.cand)}"><summary><span class="pn-lab"><b dir="auto">${esc(it.text)}</b><small>${n(it.lessons)} lesson${it.lessons===1?'':'s'} · ${n(it.hits)}× · ${esc(sig)}</small></span>`+
  `<span class="pn-btns" role="group" aria-label="Is “${esc(it.text)}” a name?">${done?`<span class="pn-verdict">${verdict}</span>`:''}<button type="button" class="pn-btn pn-yes" data-a="name"${done&&ans.label==='name'?' aria-pressed="true"':''}>Name</button><button type="button" class="pn-btn pn-no" data-a="not_name"${done&&ans.label==='not_name'?' aria-pressed="true"':''}>Not a name</button></span></summary>`+
  `<div class="pn-items"><p class="pn-guess">If it is a name, Anees files it as a <b>${esc(it.kind_guess)}</b>${it.kind_guess==='person'?' (stored only as a fingerprint, never the word itself)':''}.</p>${ex}</div></details>`;
}
function paint(){
 if(!host||!DATA)return;
 const ans=answers(),items=DATA.items||[];
 const open=items.filter(it=>!ans.has(it.cand)),done=items.filter(it=>ans.has(it.cand));
 host.innerHTML=`<section class="vp-panel pn-panel" aria-labelledby="pn-h"><div class="vp-panelhead"><div><span class="pn-key">N1</span><h2 id="pn-h">Possible names</h2><p class="ab-sub">Words on no names list and not on Amal’s list that look like a name. One tap each: a name is never scored, never counted as an unknown word, and the transcript engine and readers are told it is a name.</p></div></div>`+
  (items.length?`<div class="pn-count">${n(open.length)} to check${done.length?` · ${n(done.length)} answered`:''}</div>`+open.concat(done).map(it=>row(it,ans.get(it.cand))).join(''):'<div class="vp-empty">No possible names right now.</div>')+
  `<p class="pn-foot"><span class="pn-sync" aria-live="polite"></span> Found by <code>scripts/names.py possible</code> · built ${esc(String(DATA.generated||'').replace('T',' '))}.</p></section>`;
 status();
}
function answer(cand,a){
 const it=(DATA.items||[]).find(x=>x.cand===cand);if(!it)return;
 const kind=a==='name'?it.kind_guess:null;
 const ex=(it.examples||[])[0]||{};
 const d=new Date();
 enqueue({id:uuid(),cand_fp:cand,label:a,kind,text:a==='name'&&kind!=='person'?it.text:null,lesson_date:ex.date||null,
  source_version:DATA.version||null,ts:d.toISOString(),tz_offset_min:-d.getTimezoneOffset()});
 paint();
 const el=host.querySelector(`details[data-cand="${cand}"]`);if(el)el.querySelector('summary').focus();
}
function stylesheet(){if(document.querySelector('link[data-pn]'))return;const l=document.createElement('link');l.rel='stylesheet';l.href='css/possible-names.css?v=20260928-n1';l.dataset.pn='1';document.head.append(l);}
async function mount(el){
 if(!el)return;host=el;stylesheet();host.innerHTML='<div class="vp-notice">Loading possible names…</div>';
 host.addEventListener('click',e=>{const b=e.target.closest('.pn-btn');if(!b)return;e.preventDefault();e.stopPropagation();answer(b.closest('details').dataset.cand,b.dataset.a);});
 try{
  const r=await fetch('data/possible-names.json?v='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('HTTP '+r.status);
  DATA=await r.json();paint();await probe();status();sync();   // probe first so the status line says where answers go
 }catch(e){host.innerHTML=`<div class="vp-notice">Possible names could not load (${esc(e.message)}). Refresh to retry.</div>`;}
}
window.AneesPossibleNames={mount,answers,statusText};
})();
