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
// De-word (plan/OVERNIGHT-DEWORD-2026-10-22.md): the panels on this page keep numbers, actions and warnings in view;
// every explanation goes behind a small ⓘ that opens in place (its text, and every number in it, stays on the page).
// The modules are shared with Progress, so the move happens here, on this page only.
const DW_INFO=['.vp-panelhead p.ab-sub','.vu-head p.ab-sub','.gu-head p.ab-sub','.pn-panel .vp-panelhead p','p.rb-link','p.fl-foot','p.vu-foot',
 'p.gu-foot','p.pn-foot','p.vp-footer','p.gu-src','.gu-callout','ol.vu-do','.rg-detail > p.ab-sub','#air-grades p.ar-foot'].join(',');
function dwHeading(el){   // the heading this text explains: right before it, else its panel's / section's heading
 const h=el.previousElementSibling;if(h&&/^H[1-4]$/.test(h.tagName))return h;
 for(let p=el.parentElement;p&&p.id!=='anees-bank';p=p.parentElement){
  if(p.matches('.vp-panel,section,.ov-head')){const x=p.querySelector(':scope > .vp-panelhead h3, :scope > .vp-panelhead h2, :scope > h2, :scope > h3, :scope .vp-panelhead h3');if(x)return x;}
 }
 return null;
}
function dwInfo(el){
 const h=dwHeading(el),have=h&&h.querySelector(':scope > details.dw-info');
 const wrap=document.createElement(el.tagName==='OL'?'ol':'p');while(el.firstChild)wrap.append(el.firstChild);wrap.append(' ');
 if(have){have.lastChild.append(wrap);el.remove();return;}   // one ⓘ per heading: later notes join it
 const d=document.createElement('details');d.className='dw-info';d.dataset.dw='1';
 d.innerHTML='<summary aria-label="More about this">ⓘ</summary><div></div>';d.lastChild.append(wrap);
 if(h){h.append(' ',d);el.remove();}
 else{d.classList.add('dw-info-line');el.replaceWith(d);}
}
// a long run of rows shows its first 3 (a run of dates: the newest 3); "Show all N" opens the rest in place
// V1: the unresolved rows stay; the groups after them (no evidence possible, not counted by design) fold into one tap
function dwGroups(){
 const subs=[...document.querySelectorAll('#air-unknowns-vocab .vu-sub')];if(subs.length<2||subs[0].closest('.dw-fold'))return;
 const first=subs[0],par=first.parentElement,later=subs.filter(s=>s.parentElement===par&&s!==first);if(!later.length)return;
 const start=later[0],move=[];for(let n=start;n;n=n.nextElementSibling){if(n.matches('.vu-sub,details,.dw-more'))move.push(n);else if(move.length&&!n.matches('.vu-sub,details'))break;}
 const counts=later.map(s=>(s.textContent.match(/·\s*([\d,]+)\s*·/)||[])[1]).filter(Boolean);
 const d=document.createElement('details');d.className='dw-fold';
 d.innerHTML=`<summary>${later.length} more groups ${counts.length?'('+counts.join(' + ')+')':''} </summary>`;
 start.before(d);move.forEach(n=>d.append(n));
}
function dwFold(root){
 const parents=new Set([...root.querySelectorAll('details:not(.dw-info)')].map(d=>d.parentElement));
 parents.forEach(par=>{
  if(par.closest('details.dw-info, details.dw-fold'))return;
  let run=[];const runs=[];
  [...par.children].forEach(c=>{if(c.tagName==='DETAILS'&&!c.classList.contains('dw-info'))run.push(c);else{if(run.length)runs.push(run);run=[];}});
  if(run.length)runs.push(run);
  runs.filter(r=>r.length>5&&!r[0].dataset.dwRun).forEach(r=>{
   r.forEach(d=>d.dataset.dwRun='1');
   const dated=/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d/.test((r[0].querySelector('summary')||r[0]).textContent.trim());
   const hide=dated?r.slice(0,-3):r.slice(3);
   hide.forEach(d=>d.classList.add('dw-fold-hid'));
   const b=document.createElement('button');b.type='button';b.className='dw-more';b.textContent=`Show all ${r.length}`;
   b.onclick=()=>{const open=b.dataset.open!=='1';hide.forEach(d=>d.classList.toggle('dw-fold-hid',!open));b.dataset.open=open?'1':'0';b.textContent=open?'Show fewer':`Show all ${r.length}`;};
   (dated?r[0]:r[r.length-1])[dated?'before':'after'](b);
  });
 });
}
// the tab's point in 5 seconds: one big number per blind spot, each a tap to its section
function dwBigs(){
 const T=$('ar-tab-unknowns');if(!T||$('dw-unk-bigs'))return;
 const txt=id=>($(id)||{}).textContent||'';
 const L=(document.querySelector('#air-unknowns-listen .fl-tile b')||{}).textContent;
 const V=(txt('air-unknowns-vocab').match(/could not settle ([\d,]+)/)||txt('air-unknowns-vocab').match(/UNRESOLVED[^·]*·\s*([\d,]+)/i)||[])[1];
 const g=txt('air-unknowns-grammar'),G1=(g.match(/Of the ([\d,]+) slips found by hand/)||[])[1],G2=(g.match(/slip finder caught ([\d,]+)/)||[])[1];
 const N=document.querySelectorAll('#air-possible-names details').length;
 if(!L||!V||!G1||!G2)return;
 const big=(href,b,s,warn)=>`<a class="dw-big${warn?' dw-warnbig':''}" href="${href}"><b>${b}</b><span>${s}</span></a>`;
 const box=document.createElement('div');box.id='dw-unk-bigs';box.className='dw-bigs';
 box.innerHTML=big('#ar-unk-listen',L,'labels right')+big('#ar-unk-vocab',V,'words to settle',1)+big('#ar-unk-grammar',`${G2}/${G1}`,'slips caught',1)+(N?big('#ar-unk-names',N,'maybe a name'):'');
 const nav=T.querySelector('.ar-jump');(nav||T.firstElementChild).after(box);if(nav)nav.hidden=true;
}
let dwT=0;
function dwPass(){dwGroups();document.querySelectorAll('#ar-tab-unknowns,#ar-tab-grades').forEach(t=>{t.querySelectorAll(DW_INFO).forEach(el=>{if(!el.closest('details.dw-info'))dwInfo(el);});dwFold(t);});dwBigs();}
new MutationObserver(()=>{clearTimeout(dwT);dwT=setTimeout(dwPass,60);}).observe(document.querySelector('main')||document.body,{childList:true,subtree:true});
document.querySelectorAll('.vp-tab[data-artab]').forEach(b=>b.onclick=()=>show(b.dataset.artab));
let first=new URLSearchParams(location.search).get('tab');
if(!first){try{first=localStorage.getItem('anees-ai-reports-tab');}catch(e){}}
show(first||'unknowns');
})();
