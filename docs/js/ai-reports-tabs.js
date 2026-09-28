/* AI Reports tabs (Medi 2026-09-27: "these are system issues and should go into the AI reports. Maybe we need to create
   some tabs to organize"). Unknowns = what the robot doesn't know yet (listening, vocabulary, grammar), each module loads
   its own data and opens to the exact sentences. Research & audits = the report cards (ai-reports.js).
   Tab choice: ?tab=unknowns|research, else the last one used on this device, else Unknowns. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const TABS=['unknowns','research'];
const build=()=>encodeURIComponent(window.ANEES_BUILD||'');
function loadScript(src){return new Promise((res,rej)=>{if(document.querySelector('script[data-src="'+src+'"]'))return res();const s=document.createElement('script');s.src=src+'?build='+build();s.dataset.src=src;s.onload=res;s.onerror=()=>rej(Error('missing '+src));document.body.append(s);});}
async function chain(list){for(const s of list)await loadScript(s);}
const notice=(host,t)=>{if(host)host.innerHTML=`<div class="vp-notice">${t}</div>`;};
let mounted=false;
async function mountUnknowns(){
 if(mounted)return;mounted=true;
 const V=$('air-unknowns-vocab'),G=$('air-unknowns-grammar');
 notice(V,'Loading…');notice(G,'Loading…');
 try{await loadScript('js/word-bank-arabizi.js');}catch(e){}   // Amal's spellings (RULES S1); pages fall back to Arabic without it
 // Listening moved to Progress › Fluency (Medi 2026-09-28: personal progress, not an AI report)
 // Grammar: fetches its own JSON
 chain(['js/grammar-unknowns.js']).then(()=>{if(!window.AneesGrammarUnknowns)throw Error('not built yet');return window.AneesGrammarUnknowns.render(G);})
  .catch(()=>notice(G,'The grammar unknowns report is being built.'));
 // Vocabulary: needs the Word Bank scoring stack first
 chain(['js/config.js','js/speaking-snapshot.js','js/word-bank-review.js','js/word-bank-core.js','js/word-bank-context.js','js/vocabulary-memory.js','js/vocabulary-stats.js','js/vocab-unknowns.js'])
  .then(()=>{if(!window.AneesVocabUnknowns)throw Error('not built yet');return window.AneesVocabUnknowns.render(V);})
  .catch(()=>notice(V,'The vocabulary unknowns report is being built.'));
}
function show(tab){
 if(!TABS.includes(tab))tab='unknowns';
 document.querySelectorAll('.vp-tab[data-artab]').forEach(b=>b.setAttribute('aria-current',b.dataset.artab===tab?'page':'false'));
 TABS.forEach(t=>{const el=$('ar-tab-'+t);if(el)el.hidden=t!==tab;});
 try{localStorage.setItem('anees-ai-reports-tab',tab);}catch(e){}
 const url=new URL(location.href);url.searchParams.set('tab',tab);history.replaceState(null,'',url);
 if(tab==='unknowns')mountUnknowns();
}
document.querySelectorAll('.vp-tab[data-artab]').forEach(b=>b.onclick=()=>show(b.dataset.artab));
let first=new URLSearchParams(location.search).get('tab');
if(!first){try{first=localStorage.getItem('anees-ai-reports-tab');}catch(e){}}
show(first||'unknowns');
})();
