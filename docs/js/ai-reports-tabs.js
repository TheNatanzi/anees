/* AI Reports tabs (Medi 2026-09-27: "these are system issues and should go into the AI reports. Maybe we need to create
   some tabs to organize"). Unknowns = what the robot doesn't know yet (listening, vocabulary, grammar), each module loads
   its own data and opens to the exact sentences. Research & audits = the report cards (ai-reports.js).
   2026-09-28 (Medi: "make sure all the robot stuff goes in the ai reports and everything else is correctly in the progress"):
   the Unknowns tab is labelled "Robot blind spots" (key stays 'unknowns' for old links) and shows only the machine's
   panels: Listening L1 (labeller accuracy, from Progress › Fluency), Vocabulary V1 V3 V5, Grammar G1 G2 G5. The personal
   panels (V2 V4, G1b G3 G4) render on Progress › Vocab / Grammar from the same modules.
   Tab choice: ?tab=flow|unknowns|research|grades, else the last one used on this device, else Unknowns. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const TABS=['unknowns','research','grades','flow'];   // flow: the whole process as a flowchart (PG-56, Medi 2026-10-22 'make a new tab')
const build=()=>encodeURIComponent(window.ANEES_BUILD||'')+'&v=20260928-rb3';   // v: robot/progress split + vocab audit bins (2026-09-28)
function loadScript(src){return new Promise((res,rej)=>{if(document.querySelector('script[data-src="'+src+'"]'))return res();const s=document.createElement('script');s.src=src+'?build='+build();s.dataset.src=src;s.onload=res;s.onerror=()=>rej(Error('missing '+src));document.body.append(s);});}
async function chain(list){for(const s of list)await loadScript(s);}
const notice=(host,t)=>{if(host)host.innerHTML=`<div class="vp-notice">${t}</div>`;};
let mounted=false;
async function mountUnknowns(){
 if(mounted)return;mounted=true;
 const V=$('air-unknowns-vocab'),G=$('air-unknowns-grammar'),L=$('air-unknowns-listen');
 notice(V,'Loading…');notice(G,'Loading…');notice(L,'Loading…');
 try{await loadScript('js/word-bank-arabizi.js');}catch(e){}   // Amal's spellings (RULES S1); pages fall back to Arabic without it
 // Listening: only the labeller's accuracy (what Medi understood stays on Progress › Fluency, Medi 2026-09-28)
 chain(['js/fluency-labeller.js']).then(()=>{if(!window.AneesFluencyLabeller)throw Error('not built yet');return window.AneesFluencyLabeller.mount(L);})
  .catch(()=>notice(L,'The labeller report could not load.'));
 // Grammar: fetches its own JSON
 chain(['js/grammar-unknowns.js']).then(()=>{if(!window.AneesGrammarUnknowns)throw Error('not built yet');return window.AneesGrammarUnknowns.render(G,{panels:window.AneesGrammarUnknowns.ROBOT});})
  .catch(()=>notice(G,'The grammar unknowns report is being built.'));
 // Names: possible names, one tap each (names & places layer, 2026-09-28; loads its own data and stylesheet)
 const PN=$('air-possible-names');notice(PN,'Loading…');
 chain(['js/names.js','js/possible-names.js']).then(()=>{if(!window.AneesPossibleNames)throw Error('not built yet');return window.AneesPossibleNames.mount(PN);})
  .catch(()=>notice(PN,'Possible names could not load.'));
 // Vocabulary: needs the Word Bank scoring stack first
 chain(['js/config.js','js/speaking-snapshot.js','js/word-bank-review.js','js/word-bank-core.js','js/word-bank-context.js','js/vocabulary-memory.js','js/vocabulary-stats.js','js/vocab-unknowns.js'])
  .then(()=>{if(!window.AneesVocabUnknowns)throw Error('not built yet');return window.AneesVocabUnknowns.render(V,{panels:window.AneesVocabUnknowns.ROBOT});})
  .catch(()=>notice(V,'The vocabulary unknowns report is being built.'));
}
// Grades (PG-46, Medi 2026-10-10): the grade book of the robot against his full reviews
let gradesMounted=false;
function mountGrades(){
 if(gradesMounted)return;gradesMounted=true;
 const H=$('air-grades');notice(H,'Loading…');
 chain(['js/review-grades.js?v=20261015-pr25']).then(()=>window.AneesReviewGrades.mount(H)).catch(()=>notice(H,'The grade book could not load.'));
}
function show(tab){
 if(!TABS.includes(tab))tab='unknowns';
 document.querySelectorAll('.vp-tab[data-artab]').forEach(b=>b.setAttribute('aria-current',b.dataset.artab===tab?'page':'false'));
 TABS.forEach(t=>{const el=$('ar-tab-'+t);if(el)el.hidden=t!==tab;});
 try{localStorage.setItem('anees-ai-reports-tab',tab);}catch(e){}
 const url=new URL(location.href);url.searchParams.set('tab',tab);history.replaceState(null,'',url);
 if(tab==='unknowns')mountUnknowns();
 if(tab==='grades')mountGrades();
}
// De-word round 2 (Medi 2026-10-22: "you cut out too much data"): every number, table, list and chart stays in view.
// Only explanation prose goes behind a small ⓘ on its heading, and only when it holds no number (a sentence with a
// number in it is data and stays on screen). The modules are shared with Progress, so the move happens on this page only.
const DW_PROSE=['.vp-panelhead p.ab-sub','.vu-head p.ab-sub','.gu-head p.ab-sub','.pn-panel .vp-panelhead p','p.rb-link','p.fl-foot',
 'p.vu-foot','p.gu-foot','p.pn-foot','p.vp-footer','p.gu-src','.rg-detail > p.ab-sub','#air-grades p.ar-foot','.ov-head > p.ab-sub','.ab-header .ab-sub'].join(',');
function dwHeading(el){
 const h=el.previousElementSibling;if(h&&/^H[1-4]$/.test(h.tagName))return h;
 for(let p=el.parentElement;p&&p.id!=='anees-bank';p=p.parentElement){
  if(p.matches('.vp-panel,section,.ov-head,.ab-header')){const x=p.querySelector(':scope > .vp-panelhead h3, :scope > .vp-panelhead h2, :scope > h2, :scope > h3, :scope h1, :scope .vp-panelhead h3');if(x)return x;}
 }
 const tab=el.closest('[id^="ar-tab-"]');return tab?tab.querySelector('.ov-h2'):null;
}
function dwInfo(el){
 if(/\d/.test(el.textContent))return;   // holds a number: stays in view
 const h=dwHeading(el),have=h&&h.querySelector(':scope > details.dw-info');
 const wrap=document.createElement('p');while(el.firstChild)wrap.append(el.firstChild);wrap.append(' ');
 if(have){have.lastChild.append(wrap);el.remove();return;}
 const d=document.createElement('details');d.className='dw-info';d.innerHTML='<summary aria-label="More about this">ⓘ</summary><div></div>';d.lastChild.append(wrap);
 if(h){h.append(' ',d);el.remove();}else{d.classList.add('dw-info-line');el.replaceWith(d);}
}
function dwClip(){document.querySelectorAll('#ar-tab-unknowns .vu-split i, #ar-tab-unknowns .gu-split i').forEach(i=>{if(i.classList.contains('dw-clip')||!i.textContent.trim()||!i.clientWidth)return;
 if(i.scrollWidth>i.clientWidth+1){i.classList.add('dw-clip');i.title=i.textContent.trim();}});}   // a slice too thin for its words: no cut-off label
function dwPass(){dwClip();document.querySelectorAll(DW_PROSE).forEach(el=>{if(!el.closest('details.dw-info')){try{dwInfo(el);}catch(e){}}});}
{let k=0;const iv=setInterval(()=>{dwPass();if(++k>40)clearInterval(iv);},500);}   // modules finish at their own pace
document.querySelectorAll('.vp-tab[data-artab]').forEach(b=>b.onclick=()=>show(b.dataset.artab));
let first=new URLSearchParams(location.search).get('tab');
if(!first){try{first=localStorage.getItem('anees-ai-reports-tab');}catch(e){}}
show(first||'unknowns');
})();
document.addEventListener('click',()=>setTimeout(()=>{try{dwClip();}catch(e){}},400));
