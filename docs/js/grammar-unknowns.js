/* AI Reports › Unknowns › Grammar: "What the robot doesn't know" (Medi 2026-09-27: "What are the reports for unknown
   grammar?" then "these should have accordions with the exact sentence, similar to our grammar and word bank").
   Same look and honesty as docs/js/fluency-unknowns.js. Five panels:
   G1 rules the app can't score, G2 slips the machine can't see, G3 thin evidence per rule,
   G4 listening-side unknowns, G5 levers. Every category row is a <details> accordion that opens (lazily, 25 at a
   time) to the exact sentences behind it, drawn like the Grammar Console's use cards (Arabizi on top via
   window.AneesWordBankArabizi, Arabic under; RULES.md S1).
   Loads its own data: data/grammar-console.json (rules, 558 hand-verified corrections with machine_audit),
   data/grammar-usage.json (machine-counted uses), data/grammar-audit.json (which lessons the machine read),
   data/amal-review.json (slips with no signal, waiting for Amal; S3), data/sentence-ladder.json (+ per-lesson files
   for her sentences). Numbers that exist only in plan/PROCESS-AUDIT-2026-09-26.md are shown as sourced static facts.
   Public API: window.AneesGrammarUnknowns.render(host). Never changes a score. */
(function(){
'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const P=(a,b)=>b?Math.round(100*a/b)+'%':'—';
const pretty=d=>{if(!d)return '';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const mmss=t=>{if(typeof t!=='number')return '';const h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=Math.floor(t%60);return (h?h+':'+String(m).padStart(2,'0'):m)+':'+String(s).padStart(2,'0');};
const isArabic=s=>/[؀-ۿ]/.test(s||'');
const PAGE=25,FLOOR_DEFAULT=30;
const STATUS_COL={Mastered:'var(--ab-green)',Good:'var(--ab-blue)',Shaky:'var(--ab-orange)',Wrong:'var(--ab-red)',Unscored:'var(--ab-muted)',NotTaught:'var(--ab-raised)',Untested:'var(--ab-line)'};
const SIG={recast:'she re-said it','prompt-then-fix':'she nudged, then fixed','explicit-no':'she said no','named-rule':'she named the rule','chat-fix':'typed in chat only','finished-sentence':'she finished his sentence',asked:'he asked'};
// Numbers that live only in the process audit (plan/PROCESS-AUDIT-2026-09-26.md, counted over data/full-audit-2026-09-26.json,
// which is outside docs/ and so not published). Shown with their source, never mixed into live counts.
const AUDIT={src:'plan/PROCESS-AUDIT-2026-09-26.md',rows:961,caught:104,latinRows:416,latinMisses:127,wrongBucket:34,hitsComparable:101,rules:18,amalPatterns:7,amalRows:16};

/* ---------- data ---------- */
async function json(url,opt){try{const r=await fetch(url+'?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}catch(e){if(opt)return null;throw Error(url+': '+e.message);}}
let D=null,loading=null;
const LESSON=Object.create(null);
function lessonFile(date){
 if(LESSON[date])return LESSON[date];
 const path=D&&D.ladder&&D.ladder.files&&D.ladder.files[date];
 LESSON[date]=path?fetch(path,{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null):Promise.resolve(null);
 return LESSON[date];
}
async function load(){
 const [gc,usage,audit,review,ladder]=await Promise.all([json('data/grammar-console.json'),json('data/grammar-usage.json',1),json('data/grammar-audit.json',1),json('data/amal-review.json',1),json('data/sentence-ladder.json',1)]);
 D=build(gc,usage,audit,review,ladder);
}
const HOLE=/\[(speaking|medi track missing|inaudible|foreign|crosstalk)/i;
function build(gc,usage,audit,review,ladder){
 const rules=gc.rules||[],byId=new Map(rules.map(r=>[r.id,r]));
 const cands=[];for(const r of rules)for(const c of r.candidates||[])cands.push(Object.assign({rule:r.id,ruleName:r.name},c));
 const auditDates=new Set(((audit&&audit.lessons)||[]).map(l=>l.date));
 const hasAudit=auditDates.size>0;

 /* G1: rules without a score */
 const noScore=rules.filter(r=>r.status==='Unscored'||r.status==='Untested'||r.status==='NotTaught').map(r=>{
  let why,cls;
  if(r.family==='F'){why='A sound, never grammar (rule S4). Pronunciation is scored elsewhere.';cls='sound';}
  else if(r.status==='NotTaught'){why=`${r.not_taught_why||'Not taught yet.'} No score until Amal teaches it; ${n(r.not_counted_count||0)} of her corrections are shown but not counted.`;cls='nottaught';}
  else if(r.status==='Untested'){why='You never used it in a recorded lesson.';cls='unused';}
  else if(!r.usage_total&&(r.uses||0)>=10){why=`No detector counts Medi’s right uses, so the ${n(r.uses)} on record are all Amal’s fixes. A % would read 0 for lack of a counter, not skill.`;cls='nodetector';}
  else {why=`No detector for Medi’s right uses, and only ${n(r.uses)} use${r.uses===1?'':'s'} on record (all fixes).`;cls='few';}
  return {r,why,cls};
 }).sort((a,b)=>(b.r.uses||0)-(a.r.uses||0));

 /* G2: the hand-found slips vs the machine. One primary reason per missed slip, first that applies. */
 const gapOf=c=>{
  if(hasAudit&&!auditDates.has(c.date))return 'never';
  if(HOLE.test(c.said||''))return 'hole';
  if(!isArabic(c.said))return 'latin';
  return ({'chat-fix':'chat','named-rule':'named','prompt-then-fix':'prompt','explicit-no':'no',recast:'recast'})[c.signal]||'other';
 };
 for(const c of cands)c.gap=gapOf(c);
 const caught=cands.filter(c=>c.machine_audit===true),missed=cands.filter(c=>c.machine_audit!==true);
 const neverDates=[...new Set(cands.filter(c=>c.gap==='never').map(c=>c.date))].sort();
 const latinSeen=cands.filter(c=>c.gap!=='never'&&c.gap!=='hole'&&!isArabic(c.said)),latinCaught=latinSeen.filter(c=>c.machine_audit===true).length;
 const GAPS=[
  ['latin','His line came out in Latin letters','The transcription engine wrote Medi’s Arabic in English letters. The use counter skips these lines; the slip finder matches few.',`It caught ${n(latinCaught)} of ${n(latinSeen.length)} such lines in the lessons it read.`],
  ['never','Lesson the machine never read',`No machine pass on ${neverDates.map(pretty).join(', ')||'—'}. An operations gap, not a detector gap.`,''],
  ['recast','She re-said it, the match failed','Her recast came within 25 s but the word shapes did not line up (ة/ه, ق/ء, a dropped ع).',''],
  ['prompt','She nudged first, fixed later','شو؟ / كمان مرة, then the fix a few turns on. The pairing window is too short.',''],
  ['hole','His line is a hole in the transcript','[speaking Arabic] or a missing track. Only the clip shows what you said.',''],
  ['chat','Fixed in the Meet chat only','Her typed fix lands up to minutes later; the chat pairing fails.',''],
  ['no','Her “no” was not matched','لا / مش and a re-said word, but the echo anchors were weak.',''],
  ['named','She named the rule in English','“it’s feminine”, “with the b”: the cue list is too short.',''],
  ['other','Other','She finished your sentence, or you asked.','']
 ].map(([key,label,sub,note])=>({key,label,sub,note,items:missed.filter(c=>c.gap===key)})).filter(g=>g.items.length).sort((a,b)=>b.items.length-a.items.length);
 const noSignal=[];for(const p of ((review&&review.patterns)||[]).filter(p=>p.kind==='grammar'))for(const e of p.examples||[])noSignal.push(Object.assign({pattern:p.title,bucket:p.bucket,bucketName:p.bucket_name,rightAll:p.right},e));
 noSignal.sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:String(a.mmss).localeCompare(String(b.mmss)));

 /* G3: thin evidence per scored rule */
 const scored=rules.filter(r=>['Mastered','Good','Shaky','Wrong'].includes(r.status)).map(r=>{
  const us=(r.usage||[]).length>=(r.usage_total||0)?(r.usage||[]):((usage&&usage.uses&&usage.uses[r.id])||[]);
  const dates=new Set(us.map(u=>u.date).concat((r.candidates||[]).map(c=>c.date)));
  const added=Math.max(0,(r.uses||0)-(r.usage_total||0));
  const band=(r.uses||0)<10||dates.size<=2?'thin':(r.uses||0)<30||dates.size<=3?'fair':'solid';
  return {r,lessons:dates.size,added,band};
 });
 const bands={thin:scored.filter(x=>x.band==='thin'),fair:scored.filter(x=>x.band==='fair'),solid:scored.filter(x=>x.band==='solid')};
 bands.thin.sort((a,b)=>(a.r.uses-b.r.uses)||(a.lessons-b.lessons));
 const addedAll=scored.reduce((s,x)=>s+x.added,0),usesAll=scored.reduce((s,x)=>s+(x.r.uses||0),0);

 /* G4: listening side, from the sentence ladder */
 const floor=(ladder&&ladder.thresholds&&ladder.thresholds.effect_floor)||FLOOR_DEFAULT;
 const hear=Object.entries((ladder&&ladder.rules)||{}).filter(([id])=>!/^F/.test(id)).map(([id,x])=>{const h=x.hear||{};const k=(h.understood||0)+(h.breakdown||0);return {id,name:x.name||(byId.get(id)||{}).name||'',h,k,show:!!h.show};});
 const known=hear.filter(x=>x.show),collecting=hear.filter(x=>!x.show&&x.h.n>0).sort((a,b)=>b.k-a.k),never=hear.filter(x=>!x.h.n);
 const hearUnknown=hear.reduce((s,x)=>s+(x.h.unknown||0),0),hearAll=hear.reduce((s,x)=>s+(x.h.n||0),0);

 const unscoredFixes=noScore.filter(x=>x.cls==='nodetector'||x.cls==='few').reduce((s,x)=>s+(x.r.mistakes||0),0);
 return {gc,rules,byId,cands,caught,missed,GAPS,neverDates,latinSeen,latinCaught,noSignal,reviewPatterns:((review&&review.patterns)||[]).filter(p=>p.kind==='grammar').length,
  noScore,scored,bands,addedAll,usesAll,floor,hear,known,collecting,never,hearUnknown,hearAll,ladder,unscoredFixes,hasAudit};
}

/* ---------- sentence cards (the Grammar Console's use card, rebuilt) ---------- */
let AZ;
const az=()=>{if(AZ===undefined)AZ=window.AneesWordBankArabizi?window.AneesWordBankArabizi.create():null;return AZ;};
function el(tag,cls,text){const x=document.createElement(tag);if(cls)x.className=cls;if(text!=null)x.textContent=text;return x;}
// One spoken line: her Arabizi on top, the Arabic small underneath (S1). html carries the audit's own <mark> spans.
// Names & places (2026-09-28, js/names.js): each name gets its chip on both lines and is never converted word by word.
const namesReady=()=>window.AneesNames?window.AneesNames.load().catch(()=>null):new Promise(res=>{const s=document.createElement('script');s.src='js/names.js';s.onload=()=>window.AneesNames.load().then(res,()=>res(null));s.onerror=()=>res(null);document.head.append(s);});
function speech(cls,html,text){
 const box=el('div','gu-speech '+(cls||'')),src=el('span');
 if(html)src.innerHTML=html;else src.textContent=text||'—';
 const N=window.AneesNames;if(N&&N.matcher)N.decorate(src,N.matcher);
 const conv=az();
 if(!conv||!isArabic(src.textContent)){const only=el('div','gu-latin');only.setAttribute('dir','auto');only.appendChild(src);box.appendChild(only);return box;}
 const latin=src.cloneNode(true);let approx=false;
 const walk=document.createTreeWalker(latin,NodeFilter.SHOW_TEXT,null),nodes=[];let t;while((t=walk.nextNode()))nodes.push(t);
 nodes.forEach(t=>{if(!isArabic(t.nodeValue)||(N&&N.inName(t)))return;const r=conv(t.nodeValue);if(r.approximate)approx=true;t.nodeValue=r.text;});
 const top=el('div','gu-latin');top.setAttribute('dir','auto');top.appendChild(latin);box.appendChild(top);
 const ar=el('div','gu-arabic');ar.setAttribute('dir','auto');ar.setAttribute('lang','ar');ar.appendChild(src);box.appendChild(ar);
 if(approx)box.appendChild(el('div','gu-spellnote','Unverified spelling stays in Arabic'));
 return box;
}
// Mark a word inside a plain line (escaped first, so the only markup is ours).
function markIn(text,word,cls){const t=esc(text||'');if(!word)return t;const w=esc(word),i=t.indexOf(w);return i<0?t:t.slice(0,i)+`<mark class="${cls}">`+w+'</mark>'+t.slice(i+w.length);}
function card(kind,tags,when,parts,clip){
 const c=el('div','gu-use gu-use-'+kind),hd=el('div','gu-usehead'),left=el('span','gu-tags');
 tags.filter(Boolean).forEach(([txt,cl])=>left.appendChild(el('span','gu-tag'+(cl?' gu-tag-'+cl:''),txt)));
 hd.appendChild(left);hd.appendChild(el('span','gu-when',when));c.appendChild(hd);
 parts.forEach(p=>p&&c.appendChild(p));
 if(clip){const a=document.createElement('audio');a.controls=true;a.preload='none';a.src='lessons/'+clip;const mm=/(\d+:\d{2}(?::\d{2})?)\s*$/.exec(String(when||''));if(mm)a.dataset.mmss=mm[1];c.appendChild(a);}   // clip-fallback.js
 return c;
}
function labelled(label,node,cls){const w=el('div','gu-fixline '+(cls||''));w.appendChild(el('span','gu-fixlab',label));w.appendChild(node);return w;}
function ruleLine(id,name,why){const p=el('div','gu-rule');p.innerHTML=`<b>${esc(id)}</b> ${esc(name||'')}${why?` · <span>${esc(why)}</span>`:''}`;return p;}
// A hand-verified correction (grammar-console.json candidate).
function corrCard(c,opt={}){
 const r=D.byId.get(c.rule)||{};
 return card('slip',[[opt.tag||'Amal corrected you','bad'],c.signal?[SIG[c.signal]||c.signal]:null,opt.machine!==false?(c.machine_audit?['machine caught it','ok']:['machine missed it','warn']):null],
  pretty(c.date)+(c.mmss?' · '+c.mmss:''),
  [speech('gu-said',c.said_html,c.said),
   (c.recast||c.recast_html)?labelled('Amal said'+(c.recast_at?' ('+c.recast_at+')':''),speech('gu-fix',c.recast_html,c.recast)):null,
   c.chat?labelled('Typed in chat',speech('gu-fix',null,c.chat)):null,
   ruleLine(c.rule,r.name||c.ruleName,c.why)],c.clip);
}
// A machine-counted use (grammar-console.json rule.usage).
function useCard(u,rid){
 return card('right',[['Counted use','ok']],pretty(u.date)+(u.mmss?' · '+u.mmss:''),[speech('gu-said',u.said_html,u.said),u.hit?ruleLine(rid,(D.byId.get(rid)||{}).name,'the word that triggered it: '+u.hit):null],u.clip);
}
// A slip Amal let pass (amal-review.json example): no signal, so not a slip yet (S3).
function noSigCard(e){
 return card('nosig',[['No signal from Amal','warn'],[e.bucket,'']],pretty(e.date)+(e.mmss?' · '+e.mmss:''),
  [speech('gu-said',markIn(e.medi_said,e.wrong,'ab-wrong'),e.medi_said),
   e.amal_said?labelled('Amal said',speech('gu-fix',null,e.amal_said)):null,
   e.right?labelled('The form a reader expected',speech('gu-fix',null,e.right)):null,
   ruleLine(e.bucket,e.bucketName,e.pattern)],e.clip);
}
const LAB={understood:['You understood','ok'],breakdown:['You missed it','bad'],unknown:['Unknown','']};
function hearCard(u){
 const l=LAB[u.label]||[u.label||'—',''];
 return card('hear-'+(u.label||'x'),[l,u.why_unknown?[u.why_unknown]:u.evidence&&u.label==='understood'?[u.evidence]:null],pretty(u.date)+' · '+mmss(u.t),
  [labelled('Amal said',speech('gu-said',null,u.text)),u.reply&&u.reply.text?labelled('You replied',speech('gu-reply',null,u.reply.text)):null]);
}

/* ---------- accordions: lazy, PAGE at a time ---------- */
const ACC=new Map();let accSeq=0;
// items: array, or a function returning a Promise of an array. make: item -> node.
function acc(key,label,sub,right,items,make,opt={}){
 const id='gu-acc-'+(++accSeq);ACC.set(id,{items,make,empty:opt.empty||'No sentences on record.',note:opt.note||''});
 return `<details class="gu-acc ${opt.cls||''}" data-acc="${id}"><summary><span class="gu-sumlab"><b>${label}</b>${sub?`<small>${sub}</small>`:''}</span>${opt.bar||''}<span class="gu-v">${right}</span><span class="gu-chev" aria-hidden="true"></span></summary><div class="gu-accbody"></div></details>`;
}
function fillAcc(det){
 const spec=ACC.get(det.dataset.acc);if(!spec||det.dataset.filled)return;det.dataset.filled='1';
 const body=det.querySelector('.gu-accbody');
 const go=list=>{
  body.textContent='';
  if(spec.note)body.appendChild(el('p','gu-accnote',spec.note));
  if(!list||!list.length){body.appendChild(el('div','gu-empty',spec.empty));return;}
  const box=el('div','gu-cards');body.appendChild(box);let shown=0;
  const more=el('button','gu-more');more.type='button';
  const page=()=>{list.slice(shown,shown+PAGE).forEach(x=>{const node=spec.make(x);if(node)box.appendChild(node);});shown=Math.min(list.length,shown+PAGE);
   if(shown<list.length){more.textContent=`Show ${Math.min(PAGE,list.length-shown)} more · ${n(shown)} of ${n(list.length)}`;if(!more.parentNode)body.appendChild(more);}else more.remove();};
  more.addEventListener('click',page);page();
 };
 if(typeof spec.items==='function'){body.appendChild(el('div','gu-empty','Loading the sentences…'));Promise.resolve(spec.items()).then(go).catch(()=>{body.textContent='';body.appendChild(el('div','gu-empty','The sentences could not load. Refresh to retry.'));});}
 else go(spec.items);
}

/* ---------- panels ---------- */
const panel=(key,title,sub,body,foot)=>`<section class="vp-panel gu-panel" aria-labelledby="gu-h-${key}"><div class="vp-panelhead"><div><span class="gu-key">${key}</span><h3 class="gu-h" id="gu-h-${key}">${esc(title)}</h3>${sub?`<p class="ab-sub">${sub}</p>`:''}</div></div>${body}${foot?`<p class="gu-foot">${foot}</p>`:''}</section>`;
const track=(parts,max)=>`<span class="gu-track">${parts.map(([v,cls,t])=>v?`<i class="${cls}" style="width:${max?Math.max(1.5,100*v/max):0}%"${t?` title="${esc(t)}"`:''}></i>`:'').join('')}</span>`;

function g1(d){
 const tot=d.rules.length,sc=d.rules.reduce((m,r)=>(m[r.status]=(m[r.status]||0)+1,m),{});
 const scoredN=tot-(sc.Unscored||0)-(sc.Untested||0)-(sc.NotTaught||0);
 const strip=`<div class="gu-split" role="img" aria-label="${n(scoredN)} scored, ${n(sc.Unscored||0)} unscored, ${n(sc.Untested||0)} untested"><i class="gu-okf" style="width:${100*scoredN/tot}%">${n(scoredN)} scored</i><i class="gu-mutedf" style="width:${Math.max(12,100*(sc.Unscored||0)/tot)}%">${n(sc.Unscored||0)} unscored</i><i class="gu-linef" style="width:${Math.max(12,100*(sc.Untested||0)/tot)}%">${n(sc.Untested||0)} untested</i>${sc.NotTaught?`<i class="gu-linef" style="width:${Math.max(12,100*sc.NotTaught/tot)}%">${n(sc.NotTaught)} not taught</i>`:''}</div>`;
 const robot=d.noScore.filter(x=>x.cls!=='unused'),mine=d.noScore.filter(x=>x.cls==='unused');
 const max=Math.max(1,...d.noScore.map(x=>x.r.uses||0));
 const rows=g1rows(robot,max);
 return panel('G1','Rules the app can’t score',`${n((sc.Unscored||0)+(sc.Untested||0)+(sc.NotTaught||0))} of ${n(tot)} rules have no % yet${sc.NotTaught?` (${n(sc.NotTaught)} not taught yet)`:''}. Open one to see every sentence behind it.`,strip+`<div class="gu-list">${rows}</div>`+(mine.length?`<p class="rb-link">${n(mine.length)} of them ${mine.length===1?'is a rule':'are rules'} Medi never used in a recorded lesson. That is about him, not the robot, so ${mine.length===1?'it lives':'they live'} on <a href="progress.html?tab=grammar#gp-sure-wrap">Progress › Grammar</a>.</p>`:''),
  `${n(d.unscoredFixes)} hand-verified fixes sit on the unscored rules. They count in Medi’s totals, but the rule itself shows no %.`);
}
function g1rows(list,max){
 return list.map(x=>{const r=x.r;return acc('g1-'+r.id,`${esc(r.id)} ${esc(r.name)}`,`<span class="gu-pill gu-pill-${x.cls}">${r.status}</span> ${esc(x.why)}`,`${n(r.uses||0)} <small>use${r.uses===1?"":"s"}</small>`,
  ()=>Promise.resolve((r.candidates||[]).slice().sort((a,b)=>a.date<b.date?1:-1)),c=>corrCard(c,{machine:false}),
  {bar:track([[r.uses||0,'gu-mid']],max),empty:x.cls==='sound'?'Sounds are never filed as grammar, so there is nothing to show here.':'Never used in a recorded lesson.'});}).join('');
}
// Personal half of G1 (Medi 2026-09-28): rules with no % because Medi never used them. Lives on Progress › Grammar.
function g1b(d){
 const mine=d.noScore.filter(x=>x.cls==='unused'),max=Math.max(1,...d.noScore.map(x=>x.r.uses||0));
 return panel('G1b','Rules you haven’t used yet',`${n(mine.length)} of ${n(d.rules.length)} rules never came up in your recorded lessons, so they have no % yet.`,
  mine.length?`<div class="gu-list">${g1rows(mine,max)}</div>`:'<div class="gu-empty">Every rule has come up at least once.</div>',
  `Rules with no % because the robot has no detector for them are on <a href="ai-reports.html?tab=unknowns#ar-unk-grammar">AI Reports › Robot blind spots</a>.`);
}
function g2(d){
 const all=d.cands.length,cN=d.caught.length,mN=d.missed.length;
 const split=`<div class="gu-split" role="img" aria-label="${n(cN)} caught, ${n(mN)} missed"><i class="gu-okf" style="width:${Math.max(14,100*cN/all)}%">${n(cN)} caught</i><i class="gu-warnf" style="width:${100*mN/all}%">${n(mN)} missed · ${P(mN,all)}</i></div>`;
 const max=Math.max(1,...d.GAPS.map(g=>g.items.length),d.noSignal.length);
 const rows=d.GAPS.map(g=>acc('g2-'+g.key,esc(g.label),esc(g.sub)+(g.note?` <em>${esc(g.note)}</em>`:''),`${n(g.items.length)} <small>${P(g.items.length,mN)}</small>`,
  g.items.slice().sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:(b.t||0)-(a.t||0)),c=>corrCard(c),{bar:track([[g.items.length,'gu-warnbar']],max)})).join('');
 const nosig=d.noSignal.length?acc('g2-nosig','Amal gave no signal',`A reader saw a slip but she let it pass, so it is not a slip yet (rule S3). ${n(d.reviewPatterns)} patterns wait for her tap.`,`${n(d.noSignal.length)} <small>rows</small>`,
  d.noSignal,noSigCard,{bar:track([[d.noSignal.length,'gu-softbar']],max),cls:'gu-acc-soft'}):'';
 const caughtRow=acc('g2-caught','Caught by the machine','For comparison: what it already sees.',`${n(cN)} <small>${P(cN,all)}</small>`,d.caught.slice().sort((a,b)=>a.date<b.date?1:-1),c=>corrCard(c),{bar:track([[cN,'gu-okbar']],max),cls:'gu-acc-ok'});
 const wrong=`<div class="gu-static"><span class="gu-sumlab"><b>Caught, but filed under the wrong rule</b><small>Static: sentences are in data/full-audit-2026-09-26.json, not published.</small></span>${track([[AUDIT.wrongBucket,'gu-warnbar'],[AUDIT.hitsComparable-AUDIT.wrongBucket,'gu-okbar']],AUDIT.hitsComparable)}<span class="gu-v">${n(AUDIT.wrongBucket)} <small>of ${n(AUDIT.hitsComparable)}</small></span></div>`;
 return panel('G2','Slips the machine can’t see',`Of the ${n(all)} slips found by hand, the automatic slip finder caught ${n(cN)}. Each missed slip is listed under the first reason that applies.`,
  `<div class="gu-callout"><b>Today’s grammar numbers are safe.</b> They use the ${n(all)} hand-verified corrections, not the machine. These misses matter for the next lesson, before a hand sweep reads it.</div>`+split+`<div class="gu-list">${rows}${nosig}${caughtRow}</div>`+wrong,
  `Whole hand audit, incl. vocab and listening rows: the machine caught ${n(AUDIT.caught)} of ${n(AUDIT.rows)} (${P(AUDIT.caught,AUDIT.rows)}). ${n(AUDIT.latinRows)} of ${n(AUDIT.rows)} rows (${P(AUDIT.latinRows,AUDIT.rows)}) had Medi’s line in Latin letters. Source: ${AUDIT.src}.`);
}
function g3(d){
 const B=d.bands,tot=d.scored.length;
 const split=`<div class="gu-split" role="img" aria-label="${n(B.thin.length)} thin, ${n(B.fair.length)} fair, ${n(B.solid.length)} solid"><i class="gu-warnf" style="width:${Math.max(12,100*B.thin.length/tot)}%">${n(B.thin.length)} thin</i><i class="gu-midf" style="width:${Math.max(12,100*B.fair.length/tot)}%">${n(B.fair.length)} fair</i><i class="gu-okf" style="width:${Math.max(12,100*B.solid.length/tot)}%">${n(B.solid.length)} solid</i></div>
 <div class="gu-legend"><span><i class="gu-warnf"></i>thin: under 10 uses or 1–2 lessons</span><span><i class="gu-midf"></i>fair: 10–29 uses or 3 lessons</span><span><i class="gu-okf"></i>solid: 30+ uses in 4+ lessons</span></div>`;
 const max=Math.max(1,...B.thin.map(x=>x.r.uses||0));
 const rows=B.thin.map(x=>{const r=x.r;return acc('g3-'+r.id,`${esc(r.id)} ${esc(r.name)}`,`<span class="gu-dot" style="background:${STATUS_COL[r.status]}"></span>${esc(r.status)} ${r.pct==null?'':r.pct+'%'} · ${n(x.lessons)} lesson${x.lessons===1?'':'s'}${x.added?` · ${n(x.added)} use${x.added===1?'':'s'} added from fixes`:''}`,`${n(r.uses)} <small>use${r.uses===1?"":"s"}</small>`,
  ()=>Promise.resolve((r.candidates||[]).map(c=>({k:'c',c,date:c.date,t:c.t})).concat((r.usage||[]).map(u=>({k:'u',u,date:u.date,t:u.t}))).sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:(b.t||0)-(a.t||0))),
  x2=>x2.k==='c'?corrCard(x2.c):useCard(x2.u,r.id),{bar:track([[r.mistakes||0,'gu-badbar',`${n(r.mistakes)} fixes`],[Math.max(0,(r.uses||0)-(r.mistakes||0)),'gu-okbar',`${n((r.uses||0)-(r.mistakes||0))} not corrected`]],max)});}).join('');
 return panel('G3','Thin evidence per rule',`How much each scored rule’s % rests on. Open a thin one to read every use and fix behind it. Green = not corrected, red = Amal fixed it.`,split+`<div class="gu-list">${rows}</div>`,
  `Uses are machine-counted; ${n(d.addedAll)} of ${n(d.usesAll)} (${P(d.addedAll,d.usesAll)}) were added back from hand-found fixes on lines the counter could not read. Fixes are hand-verified.`);
}
function g4(d){
 const tot=d.hear.length,F=d.floor;
 const split=`<div class="gu-split" role="img" aria-label="${n(d.known.length)} measured, ${n(d.collecting.length)} collecting, ${n(d.never.length)} never heard"><i class="gu-okf" style="width:${Math.max(12,100*d.known.length/tot)}%">${n(d.known.length)} measured</i><i class="gu-midf" style="width:${Math.max(12,100*d.collecting.length/tot)}%">${n(d.collecting.length)} collecting</i><i class="gu-linef" style="width:${Math.max(12,100*d.never.length/tot)}%">${n(d.never.length)} never heard</i></div>`;
 const rows=d.collecting.map(x=>acc('g4-'+x.id,`${esc(x.id)} ${esc(x.name)}`,`collecting, ${n(x.k)} of ${n(F)} scored · ${n(x.h.unknown||0)} unknown`,`${n(x.k)}<small>/${n(F)}</small>`,
  ()=>examples(x.h.examples||[]),hearCard,{bar:track([[x.h.understood||0,'gu-okbar','understood'],[x.h.breakdown||0,'gu-badbar','missed'],[x.h.unknown||0,'gu-softbar','unknown']],F),
   note:`Up to 6 of Amal’s ${n(x.h.n)} sentences with this rule, misses first (the ladder keeps 6 examples per rule).`,empty:'The example sentences could not be found in the lesson files.'})).join('');
 const neverRow=d.never.length?`<div class="gu-static gu-never"><span class="gu-sumlab"><b>Amal never used these in a scored sentence</b><small>${d.never.map(x=>`<span class="gu-chip" title="${esc(x.name)}">${esc(x.id)} ${esc(x.name)}</span>`).join(' ')}</small></span></div>`:'';
 return panel('G4','Listening side: when Amal uses the rule',`“Hear it” shows a % only from ${n(F)} scored sentences (understood or missed). Unknowns sit out.`,split+`<div class="gu-list">${rows}</div>`+neverRow,
  `${n(d.hearUnknown)} of ${n(d.hearAll)} rule-tagged sentences (${P(d.hearUnknown,d.hearAll)}) are unknown. Why: <a href="progress.html?tab=fluency">Progress › Fluency</a>, “What the ladder can’t tell yet”. Sounds (F) are left out.`);
}
async function examples(ids){
 const dates=[...new Set(ids.map(id=>id.split(':')[0]))];
 const files=await Promise.all(dates.map(lessonFile)),by=new Map();
 files.forEach((f,i)=>((f&&f.listen)||[]).forEach(u=>by.set(u.id,Object.assign({date:dates[i]},u))));
 return ids.map(id=>by.get(id)).filter(Boolean);
}
function g5(d){
 const latin=d.GAPS.find(g=>g.key==='latin'),never=d.GAPS.find(g=>g.key==='never');
 const b18=d.noScore.filter(x=>x.cls==='nodetector'),few=d.noScore.filter(x=>x.cls==='few');
 const L=[
  {n:latin?latin.items.length:0,unit:'missed slips',what:'Read Latin-letter lines as Arabic',how:`Skeleton-match the lines the engine wrote in English letters. The process audit’s single biggest grammar fix (${n(AUDIT.latinMisses)} misses in the whole audit). Also lets the use counter see those turns.`,who:'Robot'},
  {n:never?never.items.length:0,unit:'missed slips',what:'Run the slip finder on every lesson',how:`${d.neverDates.map(pretty).join(', ')||'—'} were never machine-read. Rule R1.`,who:'Robot'},
  {n:d.noSignal.length,unit:'rows',what:'Amal answers the pattern cards',how:`${n(d.reviewPatterns)} grammar patterns wait for her tap. Her yes scores every row in a pattern. The audit says she must rule on only ${n(AUDIT.amalPatterns)} (${n(AUDIT.amalRows)} rows); the rest settle from her sheet.`,who:'Amal'},
  {n:b18.reduce((s,x)=>s+(x.r.mistakes||0),0)+few.reduce((s,x)=>s+(x.r.mistakes||0),0),unit:'fixes get a %',what:`A detector for ${b18.map(x=>x.r.id).join(', ')||'B18'}${few.length?' (and '+few.map(x=>x.r.id).join(', ')+')':''}`,how:`Count Medi’s right uses, so ${n(b18.length+few.length)} unscored rules can show a %. ${b18.map(x=>x.r.id+' alone has '+n(x.r.mistakes)+' fixes').join('; ')}.`,who:'Robot'},
  {n:AUDIT.rules,unit:'decisions',what:'Medi’s yes / no on the 18 audit rules',how:`R1–R18 in ${AUDIT.src}: each closes one gap (Latin lines, chat pairing, cue list, “no” matching, wrong bucket…).`,who:'Medi'},
  {n:d.collecting.length,unit:'listening rules',what:'More lessons where Amal uses the rule',how:`Each needs ${n(d.floor)} scored sentences before “hear it” shows a %. Nothing to build; it fills as you talk.`,who:'Time'}
 ].sort((a,b)=>b.n-a.n);
 const max=Math.max(1,...L.map(x=>x.n));
 return panel('G5','What would shrink the unknowns','Each lever and how much it would unlock. Longest bar first.',
  `<div class="gu-levers">${L.map(x=>`<div class="gu-lever"><div class="gu-lvtop"><span class="gu-who gu-who-${x.who.toLowerCase()}">${esc(x.who)}</span><b>${esc(x.what)}</b></div><div class="gu-lvbar">${track([[x.n,'gu-accbar']],max)}<span class="gu-v">${n(x.n)} <small>${esc(x.unit)}</small></span></div><small>${esc(x.how)}</small></div>`).join('')}</div>`,
  'The decisions are Medi’s; nothing here changes a score by itself.');
}

/* ---------- render ---------- */
// Two homes (Medi 2026-09-28: "all the robot stuff goes in the ai reports and everything else is correctly in the progress"):
//  AI Reports › Robot blind spots = G1 rules with no detector, G2 slips the robot can't see, G5 levers (the machine);
//  Progress › Grammar "How sure are these numbers?" = G1b rules Medi never used, G3 thin evidence, G4 hear-it collecting.
// render(host,{panels:[...]}) draws any subset; the numbers are always computed over the full data.
const ROBOT=['G1','G2','G5'],MEDI=['G1b','G3','G4'],DRAW={G1:g1,G1b:g1b,G2:g2,G3:g3,G4:g4,G5:g5},ORDER=['G1','G1b','G2','G3','G4','G5'];
function paint(host,keys){
 const d=D,B=d.bands,mN=d.missed.length,latin=d.GAPS.find(g=>g.key==='latin'),has=k=>keys.includes(k);
 const tile=(v,l,s)=>`<div class="gu-tile"><b>${v}</b><span>${esc(l)}</span>${s?`<small>${esc(s)}</small>`:''}</div>`;
 const mine=keys.every(k=>MEDI.includes(k)),robot=keys.every(k=>ROBOT.includes(k));
 const intro=mine?`<div class="gu-head"><span class="vp-eyebrow">How sure are these numbers?</span><h2 class="ov-h2">What your grammar numbers rest on</h2><p class="ab-sub">Rules you haven’t used yet, rules whose % rests on thin evidence, and rules still collecting a “hear it” %. Open any row for the exact sentences.</p><p class="rb-link">Rules the robot has no detector for, and the slips its slip finder can’t see, are robot issues, so they live on <a href="ai-reports.html?tab=unknowns#ar-unk-grammar">AI Reports › Robot blind spots</a>.</p></div>`
  :robot?`<div class="gu-head"><p class="ab-sub">Where the grammar numbers stop because of the robot: rules it has no detector for, slips its slip finder can’t see, and what would fix them. Open any row for the exact sentences.</p><p class="rb-link">Rules Medi hasn’t used yet, thin evidence per rule and rules still collecting a “hear it” % are about him, so they live on <a href="progress.html?tab=grammar#gp-sure-wrap">Progress › Grammar</a>.</p></div>`
  :`<div class="gu-head"><span class="vp-eyebrow">What the robot doesn’t know</span><p class="ab-sub">Where the grammar numbers stop: rules with no %, slips the robot can’t see, thin evidence, and the listening side. Open any row for the exact sentences.</p></div>`;
 const tiles=[has('G1')&&tile(n(d.noScore.length),'rules with no %','G1 · of '+n(d.rules.length)),
  has('G1b')&&tile(n(d.noScore.filter(x=>x.cls==='unused').length),d.noScore.filter(x=>x.cls==='unused').length===1?'rule you haven’t used yet':'rules you haven’t used yet','G1b · of '+n(d.rules.length)),
  has('G2')&&tile(P(mN,d.cands.length),'hand-found slips the robot missed','G2 · '+n(mN)+' of '+n(d.cands.length)),
  has('G3')&&tile(n(B.thin.length),'rules on thin evidence','G3 · under 10 uses or 1–2 lessons'),
  has('G4')&&tile(n(d.collecting.length+d.never.length),'rules with no “hear it” %','G4 · of '+n(d.hear.length)),
  has('G5')&&tile(latin?n(latin.items.length):'—','slips the biggest robot fix unlocks','G5 · Latin-letter lines')].filter(Boolean).join('');
 ACC.clear();
 host.innerHTML=`${intro}
 <div class="gu-tiles">${tiles}</div>
 <div class="gu-stack">${keys.map(k=>DRAW[k](d)).join('')}</div>
 <p class="gu-src">Corrections: ${n(d.cands.length)} hand-verified (grammar-console.json, ${esc(d.gc.updated||'')}) · uses machine-counted (grammar-usage.json) · machine hits: machine_audit on each correction · listening: sentence-ladder.json${d.ladder&&d.ladder.generated?' ('+esc(String(d.ladder.generated).slice(0,10))+')':''} · static facts: ${AUDIT.src}</p>`;
 host.querySelectorAll('details.gu-acc').forEach(det=>det.addEventListener('toggle',()=>{if(det.open)fillAcc(det);}));
}
function render(host,opts={}){
 if(!host)return;
 const keys=ORDER.filter(k=>opts.panels?opts.panels.includes(k):k!=='G1b');
 host.classList.add('gu-root');
 if(D){paint(host,keys);return;}
 host.innerHTML='<div class="vp-notice">Loading the grammar evidence…</div>';
 loading=loading||Promise.all([load(),namesReady()]);
 loading.then(()=>paint(host,keys)).catch(e=>{loading=null;host.innerHTML=`<div class="vp-notice">The grammar evidence could not load (${esc(e.message)}). Refresh to retry.</div>`;});
}
window.AneesGrammarUnknowns={render,ROBOT,MEDI,get data(){return D;}};
})();
