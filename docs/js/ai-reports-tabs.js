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
// all scripts of a chain download at once and still run in order (async=false), so the slow vocabulary stack is ready sooner
function chain(list){return Promise.all(list.map(src=>new Promise((res,rej)=>{if(document.querySelector('script[data-src="'+src+'"]'))return res();
 const s=document.createElement('script');s.src=src+'?build='+build();s.dataset.src=src;s.async=false;s.onload=res;s.onerror=()=>rej(Error('missing '+src));document.body.append(s);})));}
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
// V1: the three groups as three big numbers on top (unresolved / no evidence possible / not counted); the rows stay below
function dwV1(){const V=$('air-unknowns-vocab');if(!V||$('dw-v1-bigs'))return;const subs=[...V.querySelectorAll('.vu-sub')];if(subs.length<2)return;
 const pick=t=>{const m=t.match(/^(.*?)·\s*([\d,]+)\s*·/);return m?[m[2],m[1].replace(/:.*$/,'').trim()]:null;};
 const g=subs.map(x=>pick(x.textContent.trim())).filter(Boolean);if(g.length<2)return;
 const cls=['dw-warnbig','',''];const box=document.createElement('div');box.id='dw-v1-bigs';box.className='dw-bigs';
 const VT=+((V.textContent.match(/of the student’s ([\d,]+) word events/)||[])[1]||'0').replace(/,/g,'');
 box.innerHTML=g.map((x,i)=>{const n=+x[0].replace(/,/g,''),p=VT?Math.round(100*n/VT):null;return `<div class="dw-big ${cls[i]||''}"><b>${x[0]}</b><span>${x[1].toLowerCase()}</span>${p===null?'':`<small>${100*n/VT<1?(100*n/VT).toFixed(1):p}% of ${VT.toLocaleString('en-US')} events</small><i class="dw-split dw-bigbar" aria-hidden="true"><i style="width:${Math.max(1,100*n/VT)}%"></i></i>`}</div>`;}).join('');
 const bar=V.querySelector('.vu-split'),st=bar&&bar.previousElementSibling&&bar.previousElementSibling.classList.contains('dw-stat')?bar.previousElementSibling:bar;(st||subs[0]).before(box);}
// under each split bar: its slices' labels on one line, so a thin slice never loses its number
function dwPcts(){document.querySelectorAll('#ar-tab-unknowns .vu-split').forEach(b=>{const nx=b.nextElementSibling;const t=[...b.querySelectorAll('i.dw-clip')].map(i=>i.title||i.textContent.trim()).filter(Boolean);
 if(nx&&nx.classList.contains('dw-pcts')){nx.innerHTML=t.map(x=>'<span>'+x.replace(/</g,'&lt;')+'</span>').join('');return;}if(!t.length)return;
 const d=document.createElement('div');d.className='dw-pcts';d.innerHTML=t.map(x=>'<span>'+x.replace(/</g,'&lt;')+'</span>').join('');b.after(d);});}   // only a slice too thin for its label gets it here
// V1: every slice's share as one stat row above the split bar (from the legend's own counts)
function dwStat(){document.querySelectorAll('#ar-tab-unknowns .vu-legend').forEach(lg=>{if(lg.dataset.dwStat)return;
 const it=[...lg.children].map(c=>[c,(c.textContent.trim().match(/^(.*?)\s+([\d,]+)$/)||[])[2]]).filter(x=>x[1]);const tot=it.reduce((a,x)=>a+ +x[1].replace(/,/g,''),0);if(!tot||it.length<2)return;
 lg.dataset.dwStat='1';it.forEach(([c,n])=>{const v=100*+n.replace(/,/g,'')/tot;const b=document.createElement('b');b.className='dw-share';b.textContent=' · '+(v>0&&v<1?'<1':Math.round(v))+'%';c.append(b);});});}   // each slice's share sits on its own legend entry
// Robot blind spots: the three headline numbers on top, one tap each to its section
function dwTop(){const T=$('ar-tab-unknowns');if(!T||$('dw-top-bigs'))return;const nav=T.querySelector('.ar-jump');if(!nav)return;
 const txt=id=>($(id)||{}).textContent||'';const L=((document.querySelector('#air-unknowns-listen .fl-tile b')||{}).textContent||'').trim();
 const V=(txt('air-unknowns-vocab').match(/could not settle ([\d,]+)/)||[])[1];const g=txt('air-unknowns-grammar'),G1=(g.match(/Of the ([\d,]+) slips found by hand/)||[])[1],G2=(g.match(/slip finder caught ([\d,]+)/)||[])[1];
 if(!L||!V||!G1||!G2)return;const n=x=>+String(x).replace(/,/g,'');
 const box=document.createElement('div');box.id='dw-top-bigs';box.className='dw-bigs';
 box.innerHTML=`<a class="dw-big" href="#ar-unk-listen"><b>${L}</b><span>🎧 listening labels right</span></a><a class="dw-big dw-warnbig" href="#ar-unk-vocab"><b>${V}</b><span>📚 word events unresolved</span></a><a class="dw-big dw-warnbig" href="#ar-unk-grammar"><b>${(n(G1)-n(G2)).toLocaleString('en-US')}/${G1}</b><span>✏️ grammar slips missed</span></a>`;
 nav.after(box);}
// L1: direct evidence vs content reply only as one two-part bar (both counts stay as text)
function dwL1(){const L=$('air-unknowns-listen');if(!L||L.querySelector('.dw-l1bar'))return;const t=L.textContent;
 const a=(t.match(/direct evidence ([\d,]+)/)||[])[1],b=(t.match(/content reply only ([\d,]+)/)||[])[1];if(!a||!b)return;
 const n=x=>+x.replace(/,/g,''),p=Math.round(100*n(a)/(n(a)+n(b)));
 const host=[...L.querySelectorAll('*')].find(e=>e.children.length&&/direct evidence/.test(e.textContent)&&/content reply only/.test(e.textContent)&&![...e.children].some(c=>/direct evidence/.test(c.textContent)&&/content reply only/.test(c.textContent)));if(!host)return;
 const bar=document.createElement('div');bar.className='dw-split dw-l1bar';bar.setAttribute('aria-hidden','true');bar.innerHTML=`<i style="width:${p}%"></i><i style="width:${100-p}%"></i>`;host.after(bar);}
function dwPass(){dwClip();try{dwTop();}catch(e){}try{dwStat();}catch(e){}try{dwL1();}catch(e){}try{dwV1();}catch(e){}document.querySelectorAll(DW_PROSE).forEach(el=>{if(!el.closest('details.dw-info')){try{dwInfo(el);}catch(e){}}});}
{let k=0;const iv=setInterval(()=>{dwPass();if(++k>40)clearInterval(iv);},500);}   // modules finish at their own pace
document.querySelectorAll('.vp-tab[data-artab]').forEach(b=>b.onclick=()=>show(b.dataset.artab));
let first=new URLSearchParams(location.search).get('tab');
if(!first){try{first=localStorage.getItem('anees-ai-reports-tab');}catch(e){}}
show(first||'unknowns');
})();
document.addEventListener('click',()=>setTimeout(()=>{try{dwClip();}catch(e){}},400));
