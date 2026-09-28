/* AI Reports › Robot blind spots › Listening: "How far to trust the labeller" (moved from Progress › Fluency panel E,
   Medi 2026-09-28: "make sure all the robot stuff goes in the ai reports and everything else is correctly in the
   progress"). How well the machine labels Amal's sentences: the blind hand check, the precision of its "breakdown"
   label, its unknown share, its agreement with Medi's swipes and how strong each "understood" label is.
   Same numbers as the old panel: reads docs/data/sentence-ladder.json (labels, evidence, hand_check) and Medi's swipes
   the way fluency-ladder.js overlays them (sentence_labels rows cached on this device + the local answer log; latest
   row per sentence_id wins). Never changes a label.
   API: window.AneesFluencyLabeller.mount(host) loads its own data; html(summary, swipes) renders from loaded data. */
(function(){
'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const P=v=>v===null||v===undefined||Number.isNaN(v)?'—':Math.round(v)+'%';
const share=(a,b)=>b?a/b*100:null;
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
const LS=k=>{try{return JSON.parse(localStorage.getItem(k)||'null');}catch(e){return null;}};
// Spec section 9 hand check. Not in sentence-ladder.json yet; used only while summary.hand_check is absent.
const HAND_CHECK_SPEC={source:'spec §9 (2026-09-27)',all:{agree:21,n:30,before_fix:19},breakdown_precision:{ok:16,n:20},unknown_in_sample:{k:12,n:30}};
// Medi's swipes, overlaid exactly as fluency-ladder.js allLabels() + overlay() do (server cache, then the local log).
function swipes(){
 const m=new Map();for(const r of (LS('anees-sentence-label-server')||[]).concat(LS('anees-sentence-label-log')||[]))if(r&&r.id)m.set(r.id,Object.assign({},m.get(r.id)||{},r));
 const ov=new Map();for(const r of [...m.values()].sort((a,b)=>String(a.ts).localeCompare(String(b.ts))||String(a.created_at||'').localeCompare(String(b.created_at||''))))ov.set(r.sentence_id,r);
 return [...ov.values()].filter(r=>r.side!=='speak');
}
function html(S,sw){
 const hc=S.hand_check||HAND_CHECK_SPEC,src=S.hand_check?'sentence-ladder.json':HAND_CHECK_SPEC.source;
 const lab=(S.labels||{}).listen||{},tot=(lab.understood||0)+(lab.breakdown||0)+(lab.unknown||0);
 const ev=((S.evidence||{}).understood)||{},evTot=Object.values(ev).reduce((a,b)=>a+b,0),weak=ev['content reply only']||0;
 // agreement with Medi's swipes: only where the machine said understood / breakdown and he did not say "not sure"
 const cmp=sw.filter(r=>(r.machine_label==='understood'||r.machine_label==='breakdown')&&r.label!=='not_sure'),agree=cmp.filter(r=>r.label===r.machine_label).length;
 const unk=sw.filter(r=>r.machine_label==='unknown'),unkU=unk.filter(r=>r.label==='understood').length,unkB=unk.filter(r=>r.label==='breakdown').length;
 const tile=(big,lab2,sub)=>`<div class="fl-tile"><b>${big}</b><span>${lab2}</span>${sub?`<small>${sub}</small>`:''}</div>`;
 const body=`<div class="fl-tiles">
 ${tile(hc.all?`${n(hc.all.agree)}/${n(hc.all.n)}`:'—','labels right on a blind hand check',`${P(hc.all?share(hc.all.agree,hc.all.n):null)} · ${esc(src)}`)}
 ${tile(hc.breakdown_precision?`${n(hc.breakdown_precision.ok)}/${n(hc.breakdown_precision.n)}`:'—','the labeller’s “breakdown” was a real miss','precision of the misses')}
 ${tile(P(share(lab.unknown||0,tot)),'labelled unknown',`${n(lab.unknown)} of ${n(tot)} · bare aywa / ok = unknown`)}
 ${tile(sw.length?(cmp.length?`${n(agree)}/${n(cmp.length)}`:'—'):'—','labels that agree with Medi’s swipes',sw.length?`${n(sw.length)} swiped${unk.length?` · of ${n(unk.length)} “unknown”: Medi understood ${n(unkU)}, missed ${n(unkB)}`:''}`:'no swipes on this device yet: the swipe check is on <a href="progress.html?tab=fluency">Progress › Fluency</a>')}
 </div>
 <div class="fl-sub2">How strong is each “understood” label?</div>
 ${evTot?`<div class="fl-stack" title="${esc(Object.entries(ev).map(([k,v])=>k+': '+v).join(' · '))}"><i class="fl-b-ok" style="width:${(evTot-weak)/evTot*100}%"></i><i class="fl-b-weak" style="width:${weak/evTot*100}%"></i></div><div class="fl-legend"><span><i class="fl-b-ok"></i>direct evidence ${n(evTot-weak)}</span><span><i class="fl-b-weak"></i>content reply only ${n(weak)} (${P(share(weak,evTot))})</span></div>`:empty('No evidence counts in the data.')}`;
 return `<section class="vp-panel fl-wide" aria-labelledby="fl-h-honesty"><div class="vp-panelhead"><div><span class="fl-key">L1</span><h2 id="fl-h-honesty">How far to trust the labeller</h2><p class="ab-sub">Each listening label is the labeller’s first guess. Medi’s swipes are the fix.</p></div></div>${body}<p class="fl-foot">What Medi understood, and how sure each of his numbers is, lives on <a href="progress.html?tab=fluency">Progress › Fluency</a>.</p></section>`;
}
async function mount(host){
 if(!host)return;host.innerHTML='<div class="vp-notice">Loading the sentence ladder…</div>';
 try{
  const r=await fetch('data/sentence-ladder.json?v='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('HTTP '+r.status);
  const S=await r.json();host.innerHTML=`<div class="vp-grid">${html(S,swipes())}</div><p class="vp-footer">Sentence ladder ${esc(S.version||'')} · built ${esc(String(S.generated||'').replace('T',' '))} · swipes: the ones saved on this device.</p>`;
 }catch(e){host.innerHTML=`<div class="vp-notice">The sentence ladder could not load (${esc(e.message)}). Refresh to retry.</div>`;}
}
window.AneesFluencyLabeller={mount,html,swipes};
})();
