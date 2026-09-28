/* Progress & Stats › Fluency & Complexity tab (Medi 2026-09-27: "let's do all of these").
   Contract: plan/SENTENCE-LADDER-SPEC-2026-09-27.md. Reads docs/data/sentence-ladder.json (ladder, effects, rules,
   evidence, swipe picks, thresholds) and docs/data/sentence-ladder/<date>.json (every sentence). Labels are the
   pipeline's; this page never re-derives them. It only (1) overlays Medi's own swipes (latest sentence_labels row per
   sentence_id wins, spec 5.2) and (2) joins learner-state tags live from the sentences' Word Bank keys: Word Bank
   status (AneesVocabularyProgress.rows), FSRS recall and card history (the flashcard answer log replayed through
   AneesFlashcardStats / AneesFSRS) and Farsi cognates (data/farsi-cognates.json, unverified seed).
   Arabic is shown in Amal's spelling through the Word Bank converter (rule S1); the transcript text itself is never
   edited (S2). Every number comes from the files; anything missing renders "—" with the reason.
   Swipe answers go to Supabase sentence_labels (migration 020) through a localStorage queue, the same pattern as
   cards.html uses for card_results. Until the table exists the answers stay on this device. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const P=v=>v===null||v===undefined||Number.isNaN(v)?'—':Math.round(v)+'%';
const pts=v=>v===null||v===undefined?'—':(v>0?'+':v<0?'−':'')+Math.abs(Math.round(v*10)/10).toFixed(1);
const share=(a,b)=>b?a/b*100:null;
const short=d=>{const [,m,dd]=String(d).split('-');return `${Number(m)}/${Number(dd)}`;};
const pretty=d=>{if(!d)return '—';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const LS=(k,v)=>{try{if(v===undefined)return JSON.parse(localStorage.getItem(k)||'null');localStorage.setItem(k,JSON.stringify(v));return true;}catch(e){return v===undefined?null:false;}};
const uuid=()=>crypto.randomUUID?crypto.randomUUID():'s'+Date.now().toString(36)+Math.random().toString(36).slice(2);
const AR=/[؀-ۿ]/;
// The lesson audio is published with the site but not kept in this checkout (docs/lessons/ is excluded locally), so
// off GitHub Pages the same relative path is read from the live site (same pattern as js/tutor.js).
const PAGES='https://thenatanzi.github.io/anees/';
// Spec section 9 hand check. Not in sentence-ladder.json yet; used only while summary.hand_check is absent.
const HAND_CHECK_SPEC={source:'spec §9 (2026-09-27)',all:{agree:21,n:30,before_fix:19},breakdown_precision:{ok:16,n:20},unknown_in_sample:{k:12,n:30}};

let S=null,U=null,failed=[],AZ=null,WORDS=null,COG=null,FS=null,loading=null,unitsLoading=null,fsrsAsked=false;
let expanded={listen:false,speak:false};

/* ---------- data ---------- */
async function json(url){const r=await fetch(url+(url.includes('?')?'&':'?')+'v='+encodeURIComponent(window.ANEES_WORD_BANK_BUILD||Date.now()),{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('HTTP '+r.status+' '+url);return r.json();}
const optional=url=>json(url).catch(()=>null);
async function loadSummary(){S=await json('data/sentence-ladder.json');}
async function loadUnits(){
 const files=S.files||{},dates=Object.keys(files).sort();failed=[];
 const got=await Promise.all(dates.map(d=>json(files[d]).catch(()=>{failed.push(d);return null;})));
 const listen=[],speak=[],meta=new Map();
 got.forEach((f,i)=>{if(!f)return;meta.set(dates[i],{audio:f.audio,missing_side:f.missing_side});listen.push(...(f.listen||[]));speak.push(...(f.speak||[]));});
 U={listen,speak,meta,byId:new Map(listen.concat(speak).map(u=>[u.id,u]))};
}
function loadScript(src){return new Promise((res,rej)=>{const s=document.createElement('script');s.src=src;s.onload=res;s.onerror=rej;document.body.append(s);});}
// Her spellings: words.json (her Doc) with house_spelling.json (her WhatsApp typing) on top, as grammar-console.js does.
async function loadSpelling(){
 if(!window.AneesWordBankArabizi){try{await loadScript('js/word-bank-arabizi.js?build='+encodeURIComponent(window.ANEES_WORD_BANK_BUILD||''));}catch(e){return;}}
 const [w,h,cat,extra,cog]=await Promise.all([optional('data/words.json'),optional('data/house_spelling.json'),optional('data/word-bank-catalog.json'),optional('data/arabizi-extra.json'),optional('data/farsi-cognates.json')]);
 const house=(h&&h.items)||{};
 const words=((w&&w.items)||[]).map(x=>{const hh=house[x.match_loose];return hh&&hh.house?Object.assign({},x,{house_spelling:hh.house}):x;});
 WORDS=new Map(words.map(x=>[x.key,x]));COG=cog;
 if(window.AneesWordBankArabizi)AZ=window.AneesWordBankArabizi.create(words,cat||{},extra||{});
}

/* ---------- Medi's swipes: sentence_labels, offline queue (mirror of cards.html / card_results) ---------- */
const QK='anees-sentence-label-queue',LK='anees-sentence-label-log',SK='anees-sentence-label-server';
let memQueue=[],serverRows=LS(SK)||[],table='unknown',syncing=false,again=false,lastProbe=0;
const hdr=()=>({apikey:ANEES.anon,Authorization:'Bearer '+ANEES.anon,'Content-Type':'application/json'});
const readQ=()=>(LS(QK)||[]).concat(memQueue);
function allLabels(){const m=new Map();for(const r of serverRows.concat(LS(LK)||[],memQueue))if(r&&r.id)m.set(r.id,Object.assign({},m.get(r.id)||{},r));return [...m.values()];}
// Latest row per sentence_id (by ts, then created_at) wins (migration 020 comment).
function overlay(){const m=new Map();for(const r of allLabels().sort((a,b)=>String(a.ts).localeCompare(String(b.ts))||String(a.created_at||'').localeCompare(String(b.created_at||''))))m.set(r.sentence_id,r);return m;}
async function probe(){
 lastProbe=Date.now();
 if(!window.ANEES||!ANEES.url){table='offline';return false;}
 try{
  const rows=[];
  for(let off=0;;off+=1000){
   const r=await fetch(ANEES.url+'/rest/v1/sentence_labels?select=id,sentence_id,lesson_date,side,label,machine_label,ts,created_at&order=ts.asc,id.asc&limit=1000&offset='+off,{headers:hdr(),cache:'no-store',signal:AbortSignal.timeout(15000)});
   if(r.status===404||r.status===400){table='missing';return false;}   // PGRST205: migration 020 not applied yet
   if(!r.ok){table='offline';return false;}
   const p=await r.json();rows.push(...p);if(p.length<1000)break;
  }
  serverRows=rows;LS(SK,rows);table='ok';return true;
 }catch(e){table='offline';return false;}
}
function enqueue(row){
 const q=LS(QK)||[];q.push(row);const ok=LS(QK,q);
 const log=LS(LK)||[];log.push(row);LS(LK,log.slice(-2000));
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
   let r;try{r=await fetch(ANEES.url+'/rest/v1/sentence_labels?on_conflict=id',{method:'POST',headers:{...hdr(),Prefer:'resolution=ignore-duplicates,return=minimal'},body:JSON.stringify(batch),signal:AbortSignal.timeout(15000)});}
   catch(e){table='offline';break;}
   if(r.ok){removeSent(batch.map(x=>x.id));continue;}
   if(r.status===404||r.status===400){table='missing';break;}   // keep every answer queued on this device
   table='offline';break;
  }
 }finally{syncing=false;}
 syncStatus();
 if(again){again=false;sync();}
}
function syncText(){
 const k=readQ().length,a=`${n(k)} answer${k===1?'':'s'}`;
 if(table==='missing')return k?`${a} saved on this device; will sync when the labels table exists.`:'Labels table not set up yet (migration 020): answers are kept on this device until it is.';
 if(table==='offline')return k?`${a} waiting to sync (offline is fine).`:'Could not reach the labels table; answers are kept on this device.';
 if(table==='ok')return k?`${a} syncing…`:'All answers saved.';
 return 'Checking the labels table…';
}
function syncStatus(){const el=$('fl-sync');if(el){el.textContent=syncText();el.dataset.state=table;}}
window.addEventListener('online',sync);
setInterval(()=>{if(readQ().length&&(table!=='missing'||Date.now()-lastProbe>600000))sync();},60000);

/* ---------- live learner-state join ---------- */
const KNOWN=new Set(['Good','Mastered']);
const unitTime=u=>{const t=u.tags&&u.tags.local_time;const x=Date.parse(u.date+'T'+(t||'12:00')+':00');return Number.isFinite(x)?x:Date.parse(u.date+'T12:00:00');};
const keysOf=t=>t.k?[t.k]:(t.ks||[]);
function fsrsState(){
 if(FS)return FS;
 const St=window.AneesFlashcardStats,F=window.AneesFSRS,FP=window.AneesFlashcardProgress;if(!St||!F)return null;
 // Same merge as flashcard-progress.js fullLog(): the synced copy it caches (anees-card-server-log, refreshed by its load())
 // plus this device's unsynced answers (anees-card-log), by id. Undone rows carry undone/undone_at and history() drops them.
 const m=new Map();for(const r of (LS('anees-card-server-log')||[]).concat(LS('anees-card-log')||[]))if(r&&r.id)m.set(r.id,Object.assign({},m.get(r.id)||{},r));
 const log=[...m.values()],fresh=!!(FP&&FP.loaded),src=fresh?'the card log (synced copy + this device)':'this device’s cached card log';
 if(!fresh&&FP&&FP.reload&&!fsrsAsked){fsrsAsked=true;FP.reload().then(()=>{FS=null;render();}).catch(()=>{FS=null;render();});}
 const retention=((LS('anees-cards-pref')||{}).retention)||F.DEFAULTS.desiredRetention;
 const h=St.history(log,{desiredRetention:retention});
 const firstRight=new Map();for(const a of h.answers)if(a.right&&!firstRight.has(a.key))firstRight.set(a.key,a.t);
 const out={F,h,firstRight,retention,src,answers:h.answers.length};
 if(fresh)FS=out;
 return out;
}
function learnerJoin(){
 const V=window.AneesVocabularyProgress,C=window.AneesWordBank,rows=V&&V.rows;
 if(!rows||!rows.length||!C)return null;
 const byKey=new Map();
 for(const r of rows){for(const f of r.entries||[])for(const k of f.keys||[])if(!byKey.has(k))byKey.set(k,f);for(const k of r.keys||[r.key])if(!byKey.has(k)&&r.entries&&r.entries[0])byKey.set(k,r.entries[0]);}
 const memo=new Map();
 const statusBefore=(k,date)=>{const f=byKey.get(k);if(!f)return null;const mk=f.id+'|'+date;if(!memo.has(mk))memo.set(mk,C.score((f.speaking&&f.speaking.attempts||[]).filter(a=>C.date(a)<date)).status);return memo.get(mk);};
 const fs=fsrsState();
 const R=(k,t)=>{if(!fs)return null;const st=fs.h.states.get(k);if(!st)return null;let last=null;for(const c of st){const lr=typeof c.last_review==='number'?c.last_review:c.last_review instanceof Date?c.last_review.getTime():Date.parse(c.last_review);if(Number.isFinite(lr)&&lr<=t)last=c;else break;}return last?fs.F.retrievability(last,t):null;};
 const cogBy=new Map(),cogKey=new Map();
 for(const it of (COG&&COG.items)||[]){if(it.ar_norm)cogBy.set(it.ar_norm,it.subtype);for(const k of it.word_keys||[])cogKey.set(k,it.subtype);}
 const cogOf=t=>cogBy.get(t.n)||keysOf(t).map(k=>cogKey.get(k)).find(Boolean)||null;
 function tags(u){
  const content=(u.tok||[]).filter(t=>!t.f);if(!content.length)return {};
  const date=u.date,t=unitTime(u),o={};
  let notBank=false,unknown=false,keyed=0,drilled=0,lowR=false;
  for(const tk of content){
   const ks=keysOf(tk);if(!ks.length){notBank=true;unknown=true;continue;}
   keyed++;
   if(!ks.some(k=>KNOWN.has(statusBefore(k,date))))unknown=true;
   if(fs){if(ks.some(k=>{const ft=fs.firstRight.get(k);return ft!==undefined&&ft<t;}))drilled++;const r=ks.map(k=>R(k,t)).filter(v=>v!==null);if(r.length&&Math.max(...r)<fs.retention)lowR=true;}
  }
  const cg=content.map(cogOf).filter(Boolean);
  o.lw_unknown_word=unknown;o.lw_not_in_bank=notBank;
  if(fs){o.lw_fsrs_low=lowR;o.lw_by_ear=keyed>0&&drilled===keyed;}
  if(COG){o.lw_cognate=cg.some(s=>s!=='false-friend');o.lw_false_friend=cg.includes('false-friend');}
  return o;
 }
 return {tags,fs};
}
const LW_LABELS={lw_unknown_word:'a word you had not yet said well (not Good/Mastered, or not in the Word Bank)',lw_not_in_bank:'a word not in the Word Bank',lw_fsrs_low:'a card word FSRS expected you to be forgetting',lw_by_ear:'every keyed word already recalled on a card (known by ear/card)',lw_cognate:'a Farsi cognate (seed list, unverified)',lw_false_friend:'a Farsi false friend (seed list, unverified)'};

/* ---------- computations ---------- */
const sideDef={listen:{ok:'understood',bad:'breakdown',unk:'unknown'},speak:{ok:'success',bad:'corrected',unk:'unknown'}};
function labelOf(u,ov){if(u.side==='listen'&&ov){const r=ov.get(u.id);if(r)return r.label==='not_sure'?'unknown':r.label;}return u.label;}
const scoredOf=u=>u.scored!==false;
function ladderJS(units,side,ov,T,rule){
 const d=sideDef[side],cap=Number((/at most (\d+) per lesson/.exec(rule||'')||[])[1])||Math.floor(T.ladder_last/2);
 const by=new Map();
 for(const u of units){if(!scoredOf(u)||u.n<1)continue;const l=labelOf(u,ov);if(l!==d.ok&&l!==d.bad)continue;if(!by.has(u.n))by.set(u.n,[]);by.get(u.n).push({u,l});}
 const rungs=[];
 for(const len of [...by.keys()].sort((a,b)=>a-b)){
  const xs=[],per=new Map();
  for(const x of by.get(len).sort((a,b)=>a.u.date<b.u.date?1:a.u.date>b.u.date?-1:b.u.t-a.u.t)){if((per.get(x.u.date)||0)<cap){xs.push(x);per.set(x.u.date,(per.get(x.u.date)||0)+1);}if(xs.length===T.ladder_last)break;}
  const ok=xs.filter(x=>x.l===d.ok).length,les=new Set(xs.map(x=>x.u.date)).size,pct=xs.length?ok/xs.length:null;
  const status=xs.length<T.ladder_last?'not enough data':pct>=T.ladder_pct&&les>=T.ladder_lessons?'good':pct>=T.ladder_pct?'one lesson only':'not yet';
  rungs.push({len,n_total:by.get(len).length,n_last:xs.length,ok,pct:pct===null?null:Math.round(pct*1000)/10,lessons:les,status});
 }
 let N=0;for(const r of rungs){if(r.status==='good')N=r.len;else if(r.status==='not yet'||r.status==='one lesson only')break;}
 const at=rungs.find(r=>r.len===N),tg=rungs.find(r=>r.len===N+1);
 return {N,target:N+1,pct_at_N:at?at.pct:null,pct_at_target:tg?tg.pct:null,n_at_target:tg?tg.n_last:0,rungs};
}
const sameLadder=(a,b)=>a&&b&&a.N===b.N&&a.rungs.length===b.rungs.length&&a.rungs.every((r,i)=>r.len===b.rungs[i].len&&r.ok===b.rungs[i].ok&&r.n_last===b.rungs[i].n_last&&r.status===b.rungs[i].status);
const band=k=>k<=2?'1-2':k<=4?'3-4':k<=6?'5-6':k<=9?'7-9':'10+';
// Mantel-Haenszel risk difference by lesson x length band, same formula as mh_effects() in the pipeline (spec 6).
function mhFromStrata(strata){
 let num=0,den=0,vr=0,n1=0,n0=0,ok1=0,ok0=0;
 for(const [a,b,c,d] of Object.values(strata)){n1+=b;n0+=d;ok1+=a;ok0+=c;if(b&&d){const w=b*d/(b+d),p1=a/b,p0=c/d;num+=w*(p1-p0);den+=w;vr+=w*w*(p1*(1-p1)/b+p0*(1-p0)/d);}}
 const rd=den?num/den:null,se=den?Math.sqrt(vr)/den:null;
 return {n_with:n1,n_without:n0,pct_with:n1?ok1/n1*100:null,pct_without:n0?ok0/n0*100:null,rd_mh:rd===null?null:rd*100,ci95:rd===null?null:[(rd-1.96*se)*100,(rd+1.96*se)*100]};
}
function liveEffects(units,side,ov,tagFn,floor){
 const d=sideDef[side],strata=new Map();
 for(const u of units){if(!scoredOf(u))continue;const l=labelOf(u,ov);if(l!==d.ok&&l!==d.bad)continue;const f=tagFn(u),key=u.date+'|'+band(u.n),ok=l===d.ok?1:0;
  for(const [tag,v] of Object.entries(f)){if(!strata.has(tag))strata.set(tag,{});const s=strata.get(tag);s[key]=s[key]||[0,0,0,0];if(v){s[key][0]+=ok;s[key][1]++;}else{s[key][2]+=ok;s[key][3]++;}}}
 return [...strata].map(([tag,st])=>{const e=mhFromStrata(st);return Object.assign({tag,label:LW_LABELS[tag]||tag,live:true,show:e.n_with>=floor&&e.n_without>=floor&&e.rd_mh!==null},e);});
}
function compute(){
 const T=S.thresholds||{},ov=overlay(),o={T,ov};
 o.swipes=[...ov.values()].filter(r=>r.side!=='speak');
 o.ladder={listen:S.ladder&&S.ladder.listen,speak:S.ladder&&S.ladder.speak,strict:S.ladder&&S.ladder.listen_strict,recomputed:false,checked:false};
 if(U){
  const rule=S.ladder&&S.ladder.rule,mine=ladderJS(U.listen,'listen',null,T,rule);
  o.ladder.checked=sameLadder(mine,S.ladder.listen);
  const ids=new Set(U.listen.map(u=>u.id)),used=o.swipes.filter(r=>ids.has(r.sentence_id));o.usedSwipes=used.length;
  if(o.ladder.checked&&used.length){o.ladder.listen=ladderJS(U.listen,'listen',ov,T,rule);o.ladder.recomputed=true;
   const strictUnits=U.listen.filter(u=>!(labelOf(u,ov)==='understood'&&u.evidence==='content reply only'&&!ov.has(u.id)));const st=ladderJS(strictUnits,'listen',ov,T,rule);o.ladder.strict={N:st.N,target:st.target,pct_at_N:st.pct_at_N};}
  // comprehension curve by length
  const maxLen=10,bucket=k=>k>=maxLen?maxLen:k;
  o.curve=[];for(let k=1;k<=maxLen;k++)o.curve.push({k,label:k===maxLen?maxLen+'+':String(k),listen:{ok:0,bad:0,unk:0},speak:{ok:0,bad:0,unk:0}});
  for(const side of ['listen','speak'])for(const u of U[side]){if(!(u.n>=1))continue;const c=o.curve[bucket(u.n)-1][side],l=labelOf(u,ov),d=sideDef[side];if(!scoredOf(u)||l===d.unk)c.unk++;else if(l===d.ok)c.ok++;else if(l===d.bad)c.bad++;else c.unk++;}
  // miss signals per lesson
  const SIG=['repeat_request','meaning_question','dont_understand','rescue','wrong_answer','hand_audit'];
  o.sigKeys=SIG;o.sig=Object.keys(S.files||{}).sort().map(date=>{const us=U.listen.filter(u=>u.date===date),c={};SIG.forEach(k=>c[k]=0);let bd=0,sc=0;
   for(const u of us){const sg=u.signals||{};if(u.label==='breakdown')for(const k of SIG)if(sg[k])c[k]++;const l=u.label;if(l==='breakdown')bd++;if(l==='breakdown'||l==='understood')sc++;}
   return {date,c,units:us.length,bd,sc,loaded:!failed.includes(date)};});
  // live learner-state effects
  const J=learnerJoin();o.join=J;
  if(J){const floor=T.effect_floor||30;o.live={listen:liveEffects(U.listen,'listen',ov,J.tags,floor),speak:liveEffects(U.speak,'speak',ov,J.tags,floor)};}
 }
 return o;
}

/* ---------- SVG / layout helpers ---------- */
const W=640;
const niceMax=v=>{if(v<=0)return 1;const p=Math.pow(10,Math.floor(Math.log10(v))),r=v/p;return (r<=1?1:r<=2?2:r<=2.5?2.5:r<=5?5:10)*p;};
const empty=t=>`<div class="vp-empty">${esc(t)}</div>`;
const panel=(id,key,title,sub,body,{wide=false,side='',foot=''}={})=>`<section class="vp-panel ${wide?'fl-wide':''}" aria-labelledby="fl-h-${id}"><div class="vp-panelhead"><div><span class="fl-key">${esc(key)}</span><h2 id="fl-h-${id}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div>${side}</div>${body}${foot?`<p class="fl-foot">${foot}</p>`:''}</section>`;
const azText=t=>{if(!AZ||!AR.test(t||''))return null;const r=AZ(t);return r&&r.text!==t?r.text:null;};

/* ---------- 1. headline ladders ---------- */
const RUNG_CLS={good:'fl-r-good','not yet':'fl-r-notyet','one lesson only':'fl-r-one','not enough data':'fl-r-thin'};
function rungs(L,T){
 if(!L||!L.rungs)return empty('No ladder in the data yet.');
 const by=new Map(L.rungs.map(r=>[r.len,r])),top=Math.max(L.target+3,...L.rungs.filter(r=>r.n_last>=T.ladder_last/4).map(r=>r.len));
 let s='';
 for(let k=1;k<=top;k++){const r=by.get(k),cls=r?RUNG_CLS[r.status]||'':'fl-r-none',mark=k===L.N?'fl-r-n':k===L.target?'fl-r-target':'';
  const tip=r?`${k} words: ${n(r.ok)} of the last ${n(r.n_last)} ok (${P(r.pct)}) · ${n(r.lessons)} lessons · ${r.status} · ${n(r.n_total)} sentences in all`:`${k} words: no scored sentences yet`;
  s+=`<li class="fl-rung ${cls} ${mark}" title="${esc(tip)}"><b>${k}</b><span>${r?P(r.pct):'—'}</span>${k===L.N?'<em>N</em>':k===L.target?'<em>next</em>':''}</li>`;}
 return `<ol class="fl-rungs" aria-label="Ladder rungs by sentence length">${s}</ol>`;
}
function progressLine(L,T,okWord){
 const tg=L&&L.rungs&&L.rungs.find(r=>r.len===L.target),last=T.ladder_last,need=Math.ceil(T.ladder_pct*last-1e-9);
 if(!tg)return `<div class="fl-prog"><div class="fl-prog-t">Next rung ${n(L&&L.target)} words: no scored sentences yet.</div></div>`;
 if(tg.n_last<last)return `<div class="fl-prog"><div class="fl-prog-t">Collecting ${n(L.target)}-word sentences: <b>${n(tg.n_last)} of ${n(last)}</b></div><div class="fl-bar"><i style="width:${tg.n_last/last*100}%"></i></div></div>`;
 const more=Math.max(0,need-tg.ok),les=tg.lessons>=T.ladder_lessons;
 return `<div class="fl-prog"><div class="fl-prog-t">Next rung: <b>${n(tg.ok)} of ${n(last)}</b> ${okWord} · need ${n(need)}${more?` · ${n(more)} more to go`:''}${les?'':` · and ${n(T.ladder_lessons)}+ lessons`}</div><div class="fl-bar"><i style="width:${Math.min(100,tg.ok/need*100)}%"></i><s style="left:${need/last*100}%" title="${n(need)} of ${n(last)} = ${P(T.ladder_pct*100)}"></s></div></div>`;
}
function headline(o){
 const T=o.T,Ll=o.ladder.listen,Ls=o.ladder.speak,st=o.ladder.strict;
 const card=(title,L,okWord,extra)=>`<div class="fl-head">
  <div class="gp-sub">${esc(title)}</div>
  ${L?`<div class="fl-big"><b>${n(L.N)}</b><span>words at <strong>${P(L.pct_at_N)}</strong></span><span class="fl-arrow">→</span><span>target <strong>${n(L.target)}</strong> at ${P(L.pct_at_target)}${L.n_at_target?` <small>(last ${n(L.n_at_target)})</small>`:''}</span></div>${rungs(L,T)}${progressLine(L,T,okWord)}`:empty('No ladder in the data yet.')}${extra}</div>`;
 const strict=st?`<div class="fl-strict"><span class="fl-pill fl-pill-warn">Direct evidence only</span> <b>${n(st.N)}</b> words at ${P(st.pct_at_N)} · counts “understood” only when she confirmed, you reused her word, answered or glossed it. The ${n(Ll&&Ll.N)} above is the optimistic number; this is the floor.</div>`:'<div class="fl-strict">Direct-evidence ladder: — (not in the data)</div>';
 const note=o.ladder.recomputed?`<p class="fl-note">Listening ladder recomputed here with your ${n(o.usedSwipes)} swipe${o.usedSwipes===1?'':'s'} (your label beats the machine’s).</p>`:'';
 return `<div class="fl-heads">${card('Listening · you understand Amal',Ll,'understood',strict)}${card('Speaking · Amal lets it stand',Ls,'uncorrected','<div class="fl-strict">Success = your sentence was not corrected by Amal. Echoes of her line and mostly-English sentences are not scored.</div>')}</div>
 <p class="fl-rule"><b>Rule:</b> ${esc((S.ladder&&S.ladder.rule)||'—')} · unknowns (a bare “aywa”) never count.</p>${note}
 <div class="fl-legend"><span><i class="fl-r-good"></i>good</span><span><i class="fl-r-notyet"></i>not yet</span><span><i class="fl-r-one"></i>one lesson only</span><span><i class="fl-r-thin"></i>under ${n(T.ladder_last)} sentences</span></div>`;
}

/* ---------- 2. comprehension curve ---------- */
function curve(o){
 if(!o.curve)return empty(U?'No sentences.':'Loading every sentence…');
 const H=250,L=40,R=14,Tp=16,B=96,T=o.T,slot=(W-L-R)/o.curve.length,x=i=>L+slot*i+slot/2,y=v=>Tp+(H-Tp-B)*(1-v/100);
 const pc=c=>c.ok+c.bad?c.ok/(c.ok+c.bad)*100:null;
 let s='';for(const v of [0,25,50,75,100])s+=`<line class="vp-gridline" x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L-6}" y="${y(v)+3.5}" text-anchor="end">${v}%</text>`;
 s+=`<line class="fl-target-line" x1="${L}" x2="${W-R}" y1="${y(T.ladder_pct*100)}" y2="${y(T.ladder_pct*100)}"/><text class="fl-tl" x="${W-R}" y="${y(T.ladder_pct*100)-4}" text-anchor="end">${P(T.ladder_pct*100)} rung line</text>`;
 const series=[['listen','fl-l-listen',c=>c.listen],['speak','fl-l-speak',c=>c.speak],['both','fl-l-both',c=>({ok:c.listen.ok+c.speak.ok,bad:c.listen.bad+c.speak.bad,unk:c.listen.unk+c.speak.unk})]];
 for(const [name,cls,get] of series){
  const pts=o.curve.map((c,i)=>{const v=get(c),p=pc(v);return p===null?null:{i,p,n:v.ok+v.bad,v};});
  let d='',seg=[];for(const q of pts){if(!q){if(seg.length>1)d+=`<polyline class="${cls}" points="${seg.join(' ')}"/>`;seg=[];continue;}seg.push(`${x(q.i).toFixed(1)},${y(q.p).toFixed(1)}`);}if(seg.length>1)d+=`<polyline class="${cls}" points="${seg.join(' ')}"/>`;
  s+=d+pts.filter(Boolean).map(q=>`<circle class="${cls} ${q.n<T.ladder_last?'fl-thin':''}" cx="${x(q.i).toFixed(1)}" cy="${y(q.p).toFixed(1)}" r="${name==='both'?3:4.5}"><title>${o.curve[q.i].label} words · ${name==='both'?'combined':name==='listen'?'listening':'speaking'}: ${P(q.p)} ok · n = ${n(q.n)} scored (${n(q.v.ok)} ok, ${n(q.v.bad)} missed) · ${n(q.v.unk)} unknown / not scored left out</title></circle>`).join('');
 }
 // unknown bands: 100% strips per length, listening and speaking
 const bandRow=(side,yy,lab)=>{let r=`<text x="${L-6}" y="${yy+9}" text-anchor="end">${lab}</text>`;o.curve.forEach((c,i)=>{const v=c[side],t=v.ok+v.bad+v.unk,bw=slot*.74,x0=x(i)-bw/2;if(!t)return;let xx=x0;for(const [k,cl,nm] of [['ok','fl-b-ok',side==='listen'?'understood':'success'],['bad','fl-b-bad',side==='listen'?'breakdown':'corrected'],['unk','fl-b-unk',side==='listen'?'unknown':'not scored']]){const w=v[k]/t*bw;if(w>0)r+=`<rect class="${cl}" x="${xx.toFixed(1)}" y="${yy}" width="${w.toFixed(1)}" height="12"><title>${c.label} words · ${side==='listen'?'listening':'speaking'} · ${nm}: ${n(v[k])} of ${n(t)} (${P(v[k]/t*100)})</title></rect>`;xx+=w;}r+=`<text class="fl-n" x="${x(i)}" y="${yy+24}" text-anchor="middle">${n(t)}</text>`;});return r;};
 s+=o.curve.map((c,i)=>`<text class="vp-lesson-label" x="${x(i)}" y="${H-B+16}" text-anchor="middle">${c.label}</text>`).join('')+`<text x="${W-R}" y="${H-B+30}" text-anchor="end">Arabic words in the sentence →</text>`;
 s+=bandRow('listen',H-B+40,'hear')+bandRow('speak',H-B+70,'say');
 return `<svg class="vp-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Percent understood by sentence length, listening and speaking">${s}</svg>
 <div class="fl-legend"><span><i class="fl-sw-listen"></i>listening</span><span><i class="fl-sw-speak"></i>speaking</span><span><i class="fl-sw-both"></i>combined</span><span><i class="fl-b-ok"></i>ok</span><span><i class="fl-b-bad"></i>missed</span><span><i class="fl-b-unk"></i>unknown / not scored (own band, never ok)</span></div>`;
}

/* ---------- 3. miss signals ---------- */
const SIG_LABEL={repeat_request:'asked her to repeat',meaning_question:'asked what it means',dont_understand:'said “I’m lost”',rescue:'she rescued (guess)',wrong_answer:'wrong answer (guess)',hand_audit:'audit, read by hand'};
function signals(o){
 if(!o.sig)return empty(U?'No lessons.':'Loading every sentence…');
 const H=240,L=34,R=14,Tp=24,B=30,rows=o.sig,max=niceMax(Math.max(1,...rows.map(r=>o.sigKeys.reduce((a,k)=>a+r.c[k],0)))),slot=(W-L-R)/rows.length,bw=Math.min(34,slot*.64),y=v=>Tp+(H-Tp-B)*(1-v/max);
 let s='';for(const f of [0,.5,1])s+=`<line class="vp-gridline" x1="${L}" x2="${W-R}" y1="${y(max*f)}" y2="${y(max*f)}"/><text x="${L-6}" y="${y(max*f)+3.5}" text-anchor="end">${n(max*f)}</text>`;
 rows.forEach((r,i)=>{const cx=L+slot*i+slot/2;let acc=0;
  o.sigKeys.forEach((k,j)=>{const v=r.c[k];if(!v)return;s+=`<rect class="fl-sig fl-sig-${j+1}" x="${(cx-bw/2).toFixed(1)}" y="${y(acc+v).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y(acc)-y(acc+v)).toFixed(1)}"><title>${r.date} · ${SIG_LABEL[k]}: ${n(v)}</title></rect>`;acc+=v;});
  if(!r.loaded)s+=`<text class="fl-n" x="${cx}" y="${y(0)-4}" text-anchor="middle">—</text>`;
  else s+=`<text class="vp-callout" x="${cx}" y="${(y(acc)-5).toFixed(1)}" text-anchor="middle"><title>${r.date}: ${n(r.bd)} breakdowns of ${n(r.sc)} scored listening sentences</title>${r.sc?P(r.bd/r.sc*100):'—'}</text>`;
  if(i%Math.ceil(rows.length/10)===0||i===rows.length-1)s+=`<text class="vp-lesson-label" x="${cx}" y="${H-10}" text-anchor="middle">${short(r.date)}</text>`;});
 const tot=k=>rows.reduce((a,r)=>a+r.c[k],0);
 return `<svg class="vp-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Non-understanding signals per lesson">${s}</svg>
 <div class="fl-legend">${o.sigKeys.map((k,j)=>`<span><i class="fl-sig fl-sig-${j+1}"></i>${esc(SIG_LABEL[k])} <b>${n(tot(k))}</b></span>`).join('')}</div>`;
}

/* ---------- 4. what costs you ---------- */
function forest(list,dom){
 const [lo,hi]=dom,X=v=>(v-lo)/(hi-lo)*100;
 return list.map(e=>{const c=e.ci95||[e.rd_mh,e.rd_mh],cls=e.rd_mh<0?(c[1]<0?'fl-e-bad':'fl-e-lean'):(c[0]>0?'fl-e-good':'fl-e-lean');
  return `<div class="fl-erow" title="${esc(`${e.label}: ${pts(e.rd_mh)} points (95% CI ${pts(c[0])} to ${pts(c[1])}) · ${P(e.pct_with)} ok with it (n ${n(e.n_with)}) vs ${P(e.pct_without)} without (n ${n(e.n_without)})${e.or_adjusted!=null?` · adjusted odds ratio ${e.or_adjusted}`:''}${e.live?' · joined live':''}`)}"><span class="fl-elab">${esc(e.label)}${e.live?' <small class="fl-live">live</small>':''}</span><span class="fl-etrack"><s style="left:${X(0)}%"></s><i class="${cls}" style="left:${X(Math.min(c[0],c[1]))}%;width:${Math.max(.8,X(Math.max(c[0],c[1]))-X(Math.min(c[0],c[1])))}%"></i><b class="${cls}" style="left:${X(e.rd_mh)}%"></b></span><span class="fl-eval">${pts(e.rd_mh)}<small> n ${n(e.n_with)}</small></span></div>`;}).join('');
}
function costs(o,side){
 const floor=o.T.effect_floor||30,all=((S.effects||{})[side]||[]).filter(e=>!String(e.tag).startsWith('rule_'));
 const shown=all.filter(e=>e.show),under=all.filter(e=>!e.show);
 const live=(o.live&&o.live[side])||[],liveShown=live.filter(e=>e.show),liveUnder=live.filter(e=>!e.show);
 const K=8,list=expanded[side]?shown:shown.slice(0,K);
 const dom=(()=>{const v=list.concat(liveShown).flatMap(e=>e.ci95||[e.rd_mh]).filter(Number.isFinite);return [Math.min(-5,...v)-2,Math.max(5,...v)+2];})();
 const collecting=arr=>arr.map(e=>`<span class="fl-chip" title="${esc(`${e.label}: ${n(e.n_with)} with, ${n(e.n_without)} without`)}">${esc(e.label)} · collecting, ${n(Math.min(e.n_with,e.n_without))} of ${n(floor)}</span>`).join('');
 const joinNote=!U?'Loading sentences…':!o.join?'Waiting for the Word Bank rows (Vocab data) to join word knowledge.':'';
 return `<div class="fl-side-h">${side==='listen'?'Hearing: % understood':'Saying: % not corrected'} <small>points vs sentences without the tag, same lesson and length</small></div>
 ${list.length?`<div class="fl-scale"><span></span><span class="fl-scale-ax"><em>${pts(dom[0])}</em><em style="left:${(0-dom[0])/(dom[1]-dom[0])*100}%">0</em><em>${pts(dom[1])}</em></span><span></span></div>${forest(list,dom)}`:empty('No tag clears the floor yet.')}
 ${shown.length>K?`<button class="fl-more" data-expand="${side}">${expanded[side]?'Show the costliest '+K:'Show all '+n(shown.length)}</button>`:''}
 <div class="fl-sub2">Your word knowledge · joined live</div>
 ${joinNote?empty(joinNote):liveShown.length?forest(liveShown,dom):''}${liveUnder.length?`<div class="fl-chips">${collecting(liveUnder)}</div>`:''}
 ${under.length?`<details class="fl-det"><summary>${n(under.length)} tags still collecting (under ${n(floor)} a side)</summary><div class="fl-chips">${collecting(under)}</div></details>`:''}`;
}

/* ---------- 5. grammar hear vs say ---------- */
function grammar(o){
 const rs=Object.entries(S.rules||{}).map(([id,r])=>Object.assign({id},r)).filter(r=>r.hear&&r.hear.n).sort((a,b)=>b.hear.n-a.hear.n).slice(0,8);
 if(!rs.length)return empty('No rule counts in the data yet.');
 const floor=o.T.effect_floor||30,bar=(p,show,k,cls)=>show&&p!=null?`<span class="fl-gbar"><i class="${cls}" style="width:${p}%"></i></span><b>${P(p)}</b><small>n ${n(k)}</small>`:`<span class="fl-coll">collecting, ${n(k)} of ${n(floor)}</span>`;
 return `<div class="fl-gtable" role="table"><div class="fl-grow fl-ghead" role="row"><span>Rule</span><span>When Amal uses it: understood</span><span>When you use it: not corrected</span><span title="Corrections filed under this rule on the Grammar Console">fixes</span></div>
 ${rs.map(r=>`<div class="fl-grow" role="row"><span class="fl-gid" title="${esc(r.name)}"><b>${esc(r.id)}</b> ${esc(r.name)}</span><span>${bar(r.hear.pct,r.hear.show,r.hear.n,'fl-fill-l')}</span><span>${r.say?bar(r.say.pct_ok,r.say.show,r.say.uses,'fl-fill-s'):'—'}</span><span>${r.say?n(r.say.corrections_this_rule):'—'}</span></div>`).join('')}</div>`;
}

/* ---------- 6. labeller honesty ---------- */
function honesty(o){
 const hc=S.hand_check||HAND_CHECK_SPEC,src=S.hand_check?'sentence-ladder.json':HAND_CHECK_SPEC.source;
 const lab=(S.labels||{}).listen||{},tot=(lab.understood||0)+(lab.breakdown||0)+(lab.unknown||0);
 const ev=((S.evidence||{}).understood)||{},evTot=Object.values(ev).reduce((a,b)=>a+b,0),weak=ev['content reply only']||0;
 // agreement with Medi's swipes: only where the machine said understood / breakdown and he did not say "not sure"
 const sw=o.swipes,cmp=sw.filter(r=>(r.machine_label==='understood'||r.machine_label==='breakdown')&&r.label!=='not_sure'),agree=cmp.filter(r=>r.label===r.machine_label).length;
 const unk=sw.filter(r=>r.machine_label==='unknown'),unkU=unk.filter(r=>r.label==='understood').length,unkB=unk.filter(r=>r.label==='breakdown').length;
 const tile=(big,lab2,sub)=>`<div class="fl-tile"><b>${big}</b><span>${lab2}</span>${sub?`<small>${sub}</small>`:''}</div>`;
 return `<div class="fl-tiles">
 ${tile(hc.all?`${n(hc.all.agree)}/${n(hc.all.n)}`:'—','labels right on a blind hand check',`${P(hc.all?share(hc.all.agree,hc.all.n):null)} · ${esc(src)}`)}
 ${tile(hc.breakdown_precision?`${n(hc.breakdown_precision.ok)}/${n(hc.breakdown_precision.n)}`:'—','“breakdown” was a real miss','precision of the misses')}
 ${tile(P(share(lab.unknown||0,tot)),'labelled unknown',`${n(lab.unknown)} of ${n(tot)} · bare aywa / ok = unknown`)}
 ${tile(sw.length?(cmp.length?`${n(agree)}/${n(cmp.length)}`:'—'):'—','agree with your swipes',sw.length?`${n(sw.length)} swiped${unk.length?` · of ${n(unk.length)} “unknown”: ${n(unkU)} you understood, ${n(unkB)} you didn’t`:''}`:'swipe the check above to start')}
 </div>
 <div class="fl-sub2">How strong is each “understood”?</div>
 ${evTot?`<div class="fl-stack" title="${esc(Object.entries(ev).map(([k,v])=>k+': '+v).join(' · '))}"><i class="fl-b-ok" style="width:${(evTot-weak)/evTot*100}%"></i><i class="fl-b-weak" style="width:${weak/evTot*100}%"></i></div><div class="fl-legend"><span><i class="fl-b-ok"></i>direct evidence ${n(evTot-weak)}</span><span><i class="fl-b-weak"></i>content reply only ${n(weak)} (${P(share(weak,evTot))})</span></div>`:empty('No evidence counts in the data.')}`;
}

/* ---------- 7. after-lesson swipe check ---------- */
const player=new Audio();player.preload='none';
let stopAt=null,audioErr=null;
player.addEventListener('timeupdate',()=>{if(stopAt!==null&&player.currentTime>=stopAt){player.pause();stopAt=null;}});
player.addEventListener('error',()=>{audioErr=player.currentSrc||player.src;const el=$('fl-audio-msg');if(el)el.textContent='The recording could not load ('+audioErr+').';});
const SW={i:null,date:null,shownAt:0,hiddenMs:0,hiddenAt:null,played:false,x0:null};
document.addEventListener('visibilitychange',()=>{if(document.hidden)SW.hiddenAt=performance.now();else if(SW.hiddenAt!==null){SW.hiddenMs+=performance.now()-SW.hiddenAt;SW.hiddenAt=null;}});
const audioUrl=p=>{const rel=p&&p.audio&&p.audio[0];if(!rel)return null;if(/^https?:/.test(rel))return rel;return /github\.io$/.test(location.hostname)?new URL(rel,location.href).href:PAGES+rel;};
function play(p){
 const url=audioUrl(p);if(!url)return;audioErr=null;SW.played=true;
 const go=()=>{try{player.currentTime=p.play_from||p.t||0;}catch(e){}stopAt=p.play_to||p.end||null;const r=player.play();if(r&&r.catch)r.catch(()=>{});};
 if(player.src!==url){player.src=url;player.addEventListener('loadedmetadata',go,{once:true});player.load();}else go();
 const el=$('fl-audio-msg');if(el)el.textContent='Playing '+fmtT(p.play_from)+'–'+fmtT(p.play_to)+' of the lesson recording.';
}
const fmtT=s=>{if(!Number.isFinite(s))return '—';s=Math.round(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');};
const MACHINE={understood:['fl-pill-ok','understood'],breakdown:['fl-pill-bad','breakdown'],unknown:['fl-pill-unk','unknown']};
function swipeCard(){
 const sw=S.swipe||{},picks=sw.picks||[];
 if(!picks.length)return empty('No swipe picks in the data yet (the latest lesson has no listening sentences).');
 const ov=overlay(),mine=p=>ov.get(p.id);
 if(SW.date!==sw.date||SW.i===null){SW.date=sw.date;SW.i=picks.findIndex(p=>!mine(p));if(SW.i<0)SW.i=picks.length;SW.shownAt=performance.now();SW.hiddenMs=0;SW.played=false;}
 const done=picks.filter(mine).length,dots=picks.map((p,i)=>`<i class="${mine(p)?'fl-dot-done':''} ${i===SW.i?'fl-dot-now':''}" title="${esc(p.text)}"></i>`).join('');
 const head=`<div class="fl-sw-top"><span class="fl-sw-count">${SW.i<picks.length?`<b>${n(SW.i+1)}</b> of ${n(picks.length)}`:`<b>${n(done)}</b> of ${n(picks.length)} done`}</span><span class="fl-dots">${dots}</span><span class="fl-sw-date">Lesson ${esc(pretty(sw.date))}</span></div>`;
 if(SW.i>=picks.length){
  const cmp=picks.map(p=>({p,r:mine(p)})).filter(x=>x.r);
  return head+`<div class="fl-sw-done"><b>Done. ${n(done)} of ${n(picks.length)} checked.</b><ul>${cmp.map(({p,r})=>`<li>${azText(p.text)?`<b>${esc(azText(p.text))}</b> `:''}<span class="fl-ar" lang="ar" dir="rtl">${esc(p.text)}</span> · machine <em>${esc(p.machine_label)}</em> · you <em>${esc(r.label==='breakdown'?'didn’t':r.label==='not_sure'?'not sure':'understood')}</em></li>`).join('')}</ul><button class="fl-btn" data-sw="restart">Go through them again</button></div>`;
 }
 const p=picks[SW.i],u=U&&U.byId.get(p.id),az=azText(p.text),raz=azText(p.reply_text||'');
 const gloss=u&&WORDS?(u.tok||[]).filter(t=>!t.f&&t.k&&WORDS.get(t.k)).map(t=>{const w=WORDS.get(t.k);return `<span class="fl-gl"><b>${esc(w.house_spelling||w.arabizi||w.arabic)}</b> ${esc(w.english||'—')}</span>`;}).join(''):'';
 const [mc,ml]=MACHINE[p.machine_label]||['fl-pill-unk',p.machine_label||'—'];
 const sigs=(p.signals||[]).map(k=>SIG_LABEL[k]||k).join(', ');
 const prev=mine(p);
 return head+`<div class="fl-card" id="fl-card" tabindex="-1">
  <div class="fl-who">Amal said</div>
  ${az?`<div class="fl-az">${esc(az)}</div>`:''}<div class="fl-ar" lang="ar" dir="rtl">${esc(p.text)}</div>
  ${gloss?`<div class="fl-gloss" title="Word Bank glosses of her words (Amal’s Doc)">${gloss}</div>`:`<div class="fl-gloss fl-muted">${u?'No Word Bank gloss for these words.':'Loading the word glosses…'}</div>`}
  <div class="fl-who">You replied</div>
  <div class="fl-reply">${p.reply_text?(raz?`${esc(raz)}<div class="fl-ar fl-ar-s" lang="ar" dir="rtl">${esc(p.reply_text)}</div>`:esc(p.reply_text)):'— (no reply transcribed)'}</div>
  <div class="fl-mach">Machine says <span class="fl-pill ${mc}">${esc(ml)}</span>${sigs?` <small>${esc(sigs)}</small>`:''}${prev?` · <small>you said ${esc(prev.label)} before</small>`:''}</div>
  <div class="fl-play-row"><button class="fl-btn fl-play" data-sw="play" ${audioUrl(p)?'':'disabled'}>▶ Play ${fmtT(p.play_from)}–${fmtT(p.play_to)}</button><span id="fl-audio-msg" class="fl-muted">${audioUrl(p)?'Space plays it. Her line, then your reply.':'No recording for this lesson.'}</span></div>
 </div>
 <div class="fl-answers"><button class="fl-ans fl-ans-bad" data-sw="breakdown"><span>←</span>Didn’t</button><button class="fl-ans fl-ans-unk" data-sw="not_sure"><span>↓</span>Not sure</button><button class="fl-ans fl-ans-ok" data-sw="understood"><span>→</span>Understood</button></div>
 <div class="fl-sw-nav">${SW.i>0?'<button class="fl-link" data-sw="back">‹ back</button>':''}<span id="fl-sync" class="fl-sync" data-state="${table}">${esc(syncText())}</span></div>`;
}
function answer(label){
 const picks=(S.swipe&&S.swipe.picks)||[],p=picks[SW.i];if(!p)return;
 const u=U&&U.byId.get(p.id),now=performance.now(),vis=Math.max(0,Math.round(now-SW.shownAt-SW.hiddenMs-(SW.hiddenAt!==null?now-SW.hiddenAt:0)));
 let tz=null;try{tz=Intl.DateTimeFormat().resolvedOptions().timeZone||null;}catch(e){}
 const row={id:uuid(),sentence_id:p.id,lesson_date:S.swipe.date,side:'listen',label,machine_label:p.machine_label||null,machine_version:S.version||null,
  n_words:u&&Number.isFinite(u.n)?u.n:null,ts:new Date().toISOString(),answer_ms:vis,played:SW.played,tz_offset_min:-new Date().getTimezoneOffset(),tz,subject:'sentence-ladder'};
 player.pause();stopAt=null;
 enqueue(row);
 SW.i++;SW.shownAt=performance.now();SW.hiddenMs=0;SW.played=false;
 render();focusCard();
}
const focusCard=()=>{const c=$('fl-card');if(c)c.focus({preventScroll:true});};
function wireSwipe(){
 const host=$('fl-swipe');if(!host)return;
 host.onclick=e=>{const b=e.target.closest('[data-sw]');if(!b)return;const a=b.dataset.sw,picks=S.swipe.picks||[];
  if(a==='play')play(picks[SW.i]);
  else if(a==='back'){SW.i=Math.max(0,SW.i-1);SW.shownAt=performance.now();SW.hiddenMs=0;SW.played=false;player.pause();render();focusCard();}
  else if(a==='restart'){SW.i=0;SW.shownAt=performance.now();SW.hiddenMs=0;SW.played=false;render();focusCard();}
  else answer(a);};
 const card=$('fl-card');if(!card)return;
 card.onpointerdown=e=>{if(e.pointerType==='mouse')return;SW.x0=[e.clientX,e.clientY];};
 card.onpointerup=e=>{if(!SW.x0)return;const dx=e.clientX-SW.x0[0],dy=e.clientY-SW.x0[1];SW.x0=null;if(Math.abs(dx)>80&&Math.abs(dx)>Math.abs(dy))answer(dx>0?'understood':'breakdown');else if(dy>90&&dy>Math.abs(dx))answer('not_sure');};
}
document.addEventListener('keydown',e=>{
 const tab=$('vp-tab-fluency');if(!tab||tab.hidden||!S||!$('fl-card'))return;
 if(e.altKey||e.ctrlKey||e.metaKey||/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||'')||(e.target&&e.target.isContentEditable))return;
 const k={ArrowRight:'understood',ArrowLeft:'breakdown',ArrowDown:'not_sure'}[e.key];
 if(k){e.preventDefault();answer(k);}
 else if(e.key===' '&&!(e.target&&e.target.closest&&e.target.closest('button'))){e.preventDefault();play(S.swipe.picks[SW.i]);}
});

/* ---------- render ---------- */
function render(){
 const host=$('vp-tab-fluency');if(!host)return;
 if(!S){host.innerHTML='<div class="vp-notice">Loading the sentence ladder…</div>';return;}
 const o=compute(),lab=S.labels||{},L=lab.listen||{},Sp=lab.speak||{};
 const lastLesson=(S.lessons||[]).slice(-1)[0];
 host.innerHTML=`
 ${headline(o)}
 <div class="vp-grid">
 <section class="vp-panel fl-wide fl-swipe-panel" aria-labelledby="fl-h-swipe"><div class="vp-panelhead"><div><span class="fl-key">CHECK</span><h2 id="fl-h-swipe">After-lesson swipe check</h2><p class="ab-sub">Did you understand her? Your answer beats the machine’s label everywhere on this tab. ← didn’t · ↓ not sure · → understood.</p></div></div><div id="fl-swipe">${swipeCard()}</div></section>
 ${panel('curve','A','Comprehension by sentence length','% understood of scored sentences at each length. Faded dots: under '+n(o.T.ladder_last)+' sentences. Strips below: every sentence, unknowns in their own band.',curve(o),{side:`<div class="vp-side"><b>${P(share(L.understood,(L.understood||0)+(L.breakdown||0)))}</b>heard · ${P(share(Sp.success,(Sp.success||0)+(Sp.corrected||0)))} said</div>`,foot:`Listening: ${n(L.understood)} understood, ${n(L.breakdown)} breakdowns, ${n(L.unknown)} unknown. Speaking: ${n(Sp.success)} ok, ${n(Sp.corrected)} corrected.${o.ov.size?' Includes your swipes.':''}`})}
 ${panel('signals','B','Miss signals, lesson by lesson','Each bar: the ways you showed you did not follow. Number on top: breakdowns per scored listening sentence.',signals(o),{foot:'Rescue and wrong-answer are machine guesses (striped). A bare “aywa” is never a signal: it is unknown.'})}
 ${panel('costs-l','C','What costs you: hearing','Mantel-Haenszel difference, same lesson and same length. Bar = 95% range; most still cross 0, so read them as hints, not facts.',costs(o,'listen'),{})}
 ${panel('costs-s','C','What costs you: saying','Same model on your own sentences: how much more often Amal corrects you when the tag is present.',costs(o,'speak'),{})}
 ${panel('grammar','D','Grammar rules: hear vs say','The '+n(Math.min(8,Object.keys(S.rules||{}).length))+' rules you hear most. Left: Amal uses it. Right: you use it.',grammar(o),{foot:`Shown from ${n(o.T.effect_floor)} sentences a side. The Grammar Console has the full list.`})}
 ${panel('honesty','E','How far to trust the labeller','The labels are a machine’s first guess. Your swipes are the fix.',honesty(o),{})}
 </div>
 <p class="vp-footer">Sentence ladder ${esc(S.version||'')} · built ${esc(String(S.generated||'').replace('T',' '))} · ${n((S.lessons||[]).length)} lessons, latest ${esc(pretty(lastLesson&&lastLesson.date))}${U?` · ${n(U.listen.length)} listening + ${n(U.speak.length)} speaking sentences`:' · loading sentences'}${failed.length?` · not loaded: ${esc(failed.join(', '))}`:''}${o.ladder.checked?' · ladder re-checked in the browser':''}${o.join&&o.join.fs?` · FSRS from ${esc(o.join.fs.src)} (${n(o.join.fs.answers)} answers)`:''}${COG?` · Farsi cognates: ${esc(COG.status||'')}`:''}</p>`;
 host.querySelectorAll('[data-expand]').forEach(b=>b.onclick=()=>{expanded[b.dataset.expand]=!expanded[b.dataset.expand];render();});
 wireSwipe();syncStatus();
 host.insertAdjacentHTML('beforeend','<p class="vp-notice fl-unk-link">How sure are these labels? The unknowns, the weakly-proven “understood” sentences and every sentence behind them are on <a href="ai-reports.html?tab=unknowns">AI Reports › Unknowns</a>.</p>');   // unknowns live on AI Reports (Medi 2026-09-27)
}
function show(){
 if(!S){render();loading=loading||loadSummary().then(()=>{render();
   unitsLoading=unitsLoading||loadUnits().then(render);
   loadSpelling().then(render).catch(()=>{});
   probe().then(()=>{syncStatus();sync();});
  }).catch(e=>{const h=$('vp-tab-fluency');if(h)h.innerHTML=`<div class="vp-notice">The sentence ladder could not load (${esc(e.message)}). Refresh to retry.</div>`;loading=null;});}
 else render();
}
document.addEventListener('anees:vocab-rendered',()=>{const h=$('vp-tab-fluency');if(S&&h&&!h.hidden)render();});
window.AneesFluencyLadder={show,render,compute:()=>S&&compute(),sync,get data(){return {summary:S,units:U};},_mh:mhFromStrata,_ladder:ladderJS};
{const h=$('vp-tab-fluency');if(h&&!h.hidden)show();}   // the tab switch ran before this file loaded
})();
