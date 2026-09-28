/* AI Reports › Unknowns › Listening: "What the robot doesn't know" (Medi 2026-09-27: "I had no idea you had so many
   unknowns" · "these are system issues and should go into the AI reports" · "accordions with the exact sentence,
   similar to our grammar and word bank"). Reports the uncertainty behind the listening ladder from
   docs/data/sentence-ladder/<date>.json: why a sentence is `unknown`, where unknowns sit, how strong each
   `understood` is, and what Medi's swipes have settled. Every category opens to the exact sentences (lazy, 25 at a time),
   each with Amal's line (her Arabizi on top when it exists, Arabic under: RULES S1), Medi's reply and a play button.
   Never changes a label; the sentence-ladder pipeline and Medi's swipes own labels.
   API: AneesFluencyUnknowns.mount(host) loads its own data; render(host, ctx) renders from data already loaded. */
(function(){
'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const P=(a,b)=>b?Math.round(100*a/b)+'%':'—';
const pretty=d=>{if(!d)return '';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const fmtT=s=>{if(!Number.isFinite(s))return '—';s=Math.round(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');};
const AR=/[؀-ۿ]/;
const PAGES='https://thenatanzi.github.io/anees/';
const LS=k=>{try{return JSON.parse(localStorage.getItem(k)||'null');}catch(e){return null;}};
const WHY={
 'one-word remark; his reply does not show he took it in':['Her one-word remark','e.g. ممتاز or طيب, then you moved on. Often not a test at all.'],
 'bare reply (aywa/ok/yes/mm)':['Bare “aywa / ok / mm”','A nod proves nothing, so it sits out.'],
 'he only said her words back (no sign of meaning)':['You only repeated her words','Echoing shows you heard it, not that you got it.'],
 'reply not transcribed':['Your reply is missing','The recording or transcript has a gap.'],
 'he checked a guess of the meaning':['You checked a guess','She didn’t confirm it either way.'],
 'his question was about an earlier sentence':['You asked about an earlier line','The miss moved to that sentence instead.']
};
const STRONG=new Set(['she confirmed','reused her word','Arabic answer to her question',"said her word's meaning in English","English meaning for her 'what does it mean'",'his guess of the meaning, and she confirmed it','answered how-are-you']);
const EV={'she confirmed':'She confirmed (ممتاز, صح…)','reused her word':'You reused her word','Arabic answer to her question':'You answered her question in Arabic',"said her word's meaning in English":'You said the meaning in English',"English meaning for her 'what does it mean'":'You answered her meaning quiz',"his guess of the meaning, and she confirmed it":'She confirmed your guess','answered how-are-you':'You answered how-are-you','content reply only':'You just kept talking (weakest)'};

/* ---------- state ---------- */
let CTX=null,AZ=null;const GROUPS=new Map();const SHOWN=new Map();
const azText=t=>{if(!AZ||!AR.test(t||''))return null;try{const r=AZ(t);return r&&r.text&&r.text!==t?r.text:null;}catch(e){return null;}};
function speech(text,cls){
 if(!text)return `<div class="fu-said ${cls||''}">—</div>`;
 const az=azText(text);
 return `<div class="fu-said ${cls||''}">${az?`<div class="fu-az" dir="auto">${esc(az)}</div>`:''}<div class="${AR.test(text)?'fu-ar':'fu-plain'}" dir="auto"${AR.test(text)?' lang="ar"':''}>${esc(text)}</div></div>`;
}

/* ---------- audio: plays the lesson recording from her line to the end of his reply ---------- */
const player=new Audio();player.preload='none';let stopAt=null;
player.addEventListener('timeupdate',()=>{if(stopAt!==null&&player.currentTime>=stopAt){player.pause();stopAt=null;}});
function audioUrl(date){const m=CTX&&CTX.units&&CTX.units.meta&&CTX.units.meta.get(date);const rel=(m&&m.audio&&m.audio[0])||('lessons/'+date+'/audio/lesson.mp3');
 if(/^https?:/.test(rel))return rel;return /github\.io$/.test(location.hostname)?new URL(rel,location.href).href:PAGES+rel;}
function play(u,btn){
 const url=audioUrl(u.date),from=Math.max(0,(u.t||0)-0.5),to=(u.reply&&u.reply.end)||u.end||from+8;
 const go=()=>{try{player.currentTime=from;}catch(e){}stopAt=to;const r=player.play();if(r&&r.catch)r.catch(()=>{if(btn)btn.textContent='✕ could not play';});};
 if(player.src!==url){player.src=url;player.addEventListener('loadedmetadata',go,{once:true});player.load();}else go();
}

/* ---------- data ---------- */
function build(units,swipes,ladder){
 const L=units.filter(u=>u.side==='listen');
 const unk=L.filter(u=>u.label==='unknown'),und=L.filter(u=>u.label==='understood');
 const why=new Map();for(const u of unk){const k=u.why_unknown||'no reason recorded';why.set(k,(why.get(k)||[]).concat(u));}
 const ev=new Map();for(const u of und){const k=u.evidence||'content reply only';ev.set(k,(ev.get(k)||[]).concat(u));}
 const byLen=new Map();for(const u of L){const k=Math.min(u.n||0,10);const c=byLen.get(k)||{understood:0,breakdown:0,unknown:0};c[u.label]=(c[u.label]||0)+1;byLen.set(k,c);}
 const byLesson=new Map();for(const u of L){const c=byLesson.get(u.date)||{all:0,unk:[],remark:0};c.all++;if(u.label==='unknown'){c.unk.push(u);if(/one-word remark/.test(u.why_unknown||''))c.remark++;}byLesson.set(u.date,c);}
 const byId=new Map(L.map(u=>[u.id,u]));
 const latest=new Map();for(const r of swipes||[]){const id=r.sentence_id;if(!id||!byId.has(id))continue;const p=latest.get(id);if(!p||String(r.ts||'')>=String(p.ts||''))latest.set(id,r);}
 const settled=[...latest.entries()].map(([id,r])=>({u:byId.get(id),r}));
 const N=ladder&&ladder.N,T=ladder&&ladder.target;
 const atRung=unk.filter(u=>u.n===N||u.n===T);
 const strong=und.filter(u=>STRONG.has(u.evidence)).length;
 return {L,unk,und,why,ev,byLen,byLesson,settled,N,T,atRung,strong,long:unk.filter(u=>(u.n||0)>=3)};
}

/* ---------- accordions ---------- */
let gid=0;
function acc(title,sub,list,right,cls){
 const id='fu-g'+(++gid);GROUPS.set(id,list.slice().sort((a,b)=>String(b.date).localeCompare(String(a.date))||(a.t-b.t)));
 return `<details class="fu-acc" data-g="${id}"><summary><span class="fu-acc-lab"><b>${esc(title)}</b>${sub?`<small>${esc(sub)}</small>`:''}</span><span class="fu-acc-bar"><i class="${cls||'fu-mid'}" style="width:${right.w}%"></i></span><span class="fu-v">${right.text}</span></summary><div class="fu-items" id="${id}-items"></div></details>`;
}
function item(u){
 const lk=u.lookback?` · <span class="fu-chip">look-back</span>`:'';
 const why=u.label==='unknown'?(WHY[u.why_unknown]||[u.why_unknown||''])[0]:u.label==='understood'?(EV[u.evidence]||u.evidence||''):'missed';
 return `<div class="fu-item"><div class="fu-item-head"><span>${esc(pretty(u.date))} · ${fmtT(u.t)} · ${n(u.n)} word${u.n===1?'':'s'}${lk}</span><span class="fu-chip">${esc(why)}</span><button type="button" class="fu-play" data-play="${esc(u.id)}" aria-label="Play this moment from the lesson recording">▶ play</button></div>
 <div class="fu-who">Amal</div>${speech(u.text,'fu-her')}
 <div class="fu-who">You</div>${speech(u.reply&&u.reply.text,'fu-you')}</div>`;
}
function fill(g,more){
 const list=GROUPS.get(g)||[],box=document.getElementById(g+'-items');if(!box)return;
 const k=Math.min(list.length,(SHOWN.get(g)||0)+(more?25:25));SHOWN.set(g,k);
 box.innerHTML=list.slice(0,k).map(item).join('')+(k<list.length?`<button type="button" class="fu-more" data-more="${g}">Show ${n(Math.min(25,list.length-k))} more (${n(list.length-k)} left)</button>`:'')+(list.length?'':'<div class="vp-empty">No sentences.</div>');
}
function wire(sec){
 sec.querySelectorAll('details.fu-acc').forEach(d=>d.addEventListener('toggle',()=>{if(d.open&&!SHOWN.has(d.dataset.g))fill(d.dataset.g,false);}));
 sec.addEventListener('click',e=>{const m=e.target.closest('[data-more]');if(m){const g=m.dataset.more;SHOWN.set(g,SHOWN.get(g)||0);fill(g,true);return;}
  const p=e.target.closest('[data-play]');if(p){const u=CTX.units.byId.get(p.dataset.play);if(u)play(u,p);}});
}

/* ---------- panels ---------- */
const panel=(id,key,title,sub,body,foot,wide)=>`<section class="vp-panel ${wide?'fl-wide':''}" aria-labelledby="fu-h-${id}"><div class="vp-panelhead"><div><span class="fl-key">${key}</span><h2 id="fu-h-${id}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div></div>${body}${foot?`<p class="fu-foot">${foot}</p>`:''}</section>`;
function whyPanel(d){
 const rows=[...d.why.entries()].sort((a,b)=>b[1].length-a[1].length),max=rows.length?rows[0][1].length:1;
 return panel('why','U1','Why sentences are unknown',`${n(d.unk.length)} of ${n(d.L.length)} listening sentences (${P(d.unk.length,d.L.length)}). Each one sits out of the score. Open a row to see every sentence.`,
  rows.map(([k,us])=>{const w=WHY[k]||[k,''];return acc(w[0],w[1],us,{w:100*us.length/max,text:`${n(us.length)} <small>${P(us.length,d.unk.length)}</small>`},/one-word/.test(k)?'fu-soft':'fu-mid');}).join('')||'<div class="vp-empty">No unknown sentences.</div>',
  'Her one-word remarks are the biggest group, and most were never a test of your listening.',false);
}
function evPanel(d){
 const rows=[...d.ev.entries()].sort((a,b)=>(STRONG.has(b[0])-STRONG.has(a[0]))||b[1].length-a[1].length),max=Math.max(1,...rows.map(r=>r[1].length)),tot=Math.max(1,d.und.length);
 return panel('ev','U2','How sure are the “understood” ones?',`Of ${n(d.und.length)} sentences labelled understood, how each one earned it.`,
  `<div class="fu-split" role="img" aria-label="${n(d.strong)} clear proof, ${n(d.und.length-d.strong)} weakest"><i class="fu-ok" style="width:${100*d.strong/tot}%">${P(d.strong,tot)} clear proof</i><i class="fu-weak" style="width:${100*(d.und.length-d.strong)/tot}%">${P(d.und.length-d.strong,tot)} weakest</i></div>`+
  rows.map(([k,us])=>acc(EV[k]||k,'',us,{w:100*us.length/max,text:n(us.length)},STRONG.has(k)?'fu-okbar':'fu-weakbar')).join(''),
  '“You just kept talking” means your reply fit but proved nothing specific. These are the likeliest hidden misses, and why the strict ladder reads 2 instead of 7.',false);
}
function lenPanel(d){
 const keys=[...d.byLen.keys()].sort((a,b)=>a-b);const max=Math.max(1,...keys.map(k=>{const c=d.byLen.get(k);return c.understood+c.breakdown+c.unknown;}));
 const cols=keys.map(k=>{const c=d.byLen.get(k),t=c.understood+c.breakdown+c.unknown,rung=k===d.N?'fu-rung-now':k===d.T?'fu-rung-next':'';
  const seg=(v,cls,lab)=>v?`<i class="${cls}" style="height:${100*v/max}%" title="${k===10?'10+':k} words · ${lab}: ${n(v)} of ${n(t)} (${P(v,t)})"></i>`:'';
  return `<div class="fu-col ${rung}"><div class="fu-stack">${seg(c.unknown,'fu-unk','unknown')}${seg(c.breakdown,'fu-bd','missed')}${seg(c.understood,'fu-ok','understood')}</div><span class="fu-x">${k===10?'10+':k}</span><span class="fu-pct">${P(c.unknown,t)}</span></div>`;}).join('');
 return panel('len','U3','Where the unknowns sit, by sentence length','Bar height = sentences at that length. Grey = unknown, red = missed, green = understood. The % under each bar is its unknown share.',
  `<div class="fu-cols" role="img" aria-label="Sentences by length and label">${cols}</div><div class="gp-legend fu-legend"><span><i class="fu-ok"></i>understood</span><span><i class="fu-bd"></i>missed</span><span><i class="fu-unk"></i>unknown</span>${d.N?`<span><i class="fu-now"></i>your rung (${n(d.N)})</span><span><i class="fu-next"></i>next rung (${n(d.T)})</span>`:''}</div>`+
  acc('Unknowns at 3+ words','the ones long enough to matter for the ladder',d.long,{w:100,text:n(d.long.length)},'fu-mid')+
  (d.N?acc(`Unknowns at your rungs (${d.N} and ${d.T} words)`,'these are the ones that could move your ladder',d.atRung,{w:100*d.atRung.length/Math.max(1,d.long.length),text:n(d.atRung.length)},'fu-weakbar'):''),
  `${n(d.byLen.get(1)?d.byLen.get(1).unknown:0)} of the ${n(d.unk.length)} unknowns are one-word sentences.`,true);
}
function lessonPanel(d){
 const ds=[...d.byLesson.keys()].sort().reverse(),max=Math.max(0.01,...ds.map(k=>d.byLesson.get(k).unk.length/Math.max(1,d.byLesson.get(k).all)));
 return panel('lesson','U4','Unknowns per lesson','Share of each lesson’s listening sentences that are unknown. Open a lesson to see them.',
  ds.map(k=>{const c=d.byLesson.get(k);return acc(pretty(k),`${n(c.remark)} of ${n(c.unk.length)} are her one-word remarks`,c.unk,{w:100*(c.unk.length/Math.max(1,c.all))/max,text:P(c.unk.length,c.all)},'fu-mid');}).join(''),
  'A share that grows lesson after lesson means more nodding along. That is the part worth watching.',false);
}
function actPanel(d){
 const sw=d.settled,onUnk=sw.filter(x=>x.u.label==='unknown'),res=onUnk.filter(x=>x.r.label==='understood'||x.r.label==='breakdown');
 const weakSw=sw.filter(x=>x.u.label==='understood'&&!STRONG.has(x.u.evidence)),weakWrong=weakSw.filter(x=>x.r.label==='breakdown').length;
 const tile=(v,l,s)=>`<div class="fu-tile"><b>${v}</b><span>${esc(l)}</span>${s?`<small>${esc(s)}</small>`:''}</div>`;
 return panel('act','U5','Turning unknowns into answers','What has been settled so far, and the three levers.',
  `<div class="fu-tiles">${tile(n(d.long.length),'unknowns at 3+ words','the ones that could move the ladder')}${tile(n(sw.length),'sentences you have swiped','on this device; your answer replaces the robot’s')}${tile(sw.length?n(res.length)+' of '+n(onUnk.length):'—','unknowns your swipes settled',sw.length?'':'swipe after your next lesson')}${tile(weakSw.length?P(weakWrong,weakSw.length):'—','of “weakest” understood you marked missed',weakSw.length?`${n(weakWrong)} of ${n(weakSw.length)} swipes`:'no swipes on these yet')}</div>
  <ol class="fu-do"><li><b>You:</b> the 10-card swipe check (Progress › Fluency) aims 3 cards at unknowns. That is the fastest way to shrink this.</li><li><b>Amal:</b> after a bare “aywa”, one quick check question turns an unknown into a real answer. Research on hidden non-understanding suggests exactly this.</li><li><b>The robot:</b> her one-word remarks could be dropped from scoring altogether, since they rarely test you. Decision for Medi.</li></ol>`,'',true);
}

/* ---------- entry points ---------- */
function render(host,ctx){
 if(!host||!ctx||!ctx.summary)return;
 CTX=ctx;if(ctx.az)AZ=ctx.az;GROUPS.clear();SHOWN.clear();gid=0;
 let sec=host.querySelector('#fu-section');
 if(!sec){sec=document.createElement('div');sec.id='fu-section';host.appendChild(sec);}
 const units=ctx.units&&ctx.units.listen;
 if(!units){sec.innerHTML='<div class="vp-notice">Loading every sentence…</div>';return;}
 const d=build(units,ctx.labels||[],ctx.summary.ladder&&ctx.summary.ladder.listen);
 sec.innerHTML=`<p class="ab-sub fu-intro">${n(d.unk.length)} unknown and ${n(d.und.length-d.strong)} weakly-proven sentences behind the listening numbers on Progress › Fluency: why, where, and how to shrink them.</p>
 <div class="vp-grid">${whyPanel(d)}${evPanel(d)}${lenPanel(d)}${lessonPanel(d)}${actPanel(d)}</div>
 <p class="vp-footer">Sentence ladder ${esc(ctx.summary.version||'')} · built ${esc(String(ctx.summary.generated||'').replace('T',' '))} · ${n(d.L.length)} listening sentences · labels are the robot’s first guess; your swipes replace them.</p>`;
 wire(sec);
}
async function json(u){const r=await fetch(u,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status+' '+u);return r.json();}
const optional=u=>json(u).catch(()=>null);
async function spelling(){
 if(!window.AneesWordBankArabizi)return null;
 const [w,h,cat,extra]=await Promise.all([optional('data/words.json'),optional('data/house_spelling.json'),optional('data/word-bank-catalog.json'),optional('data/arabizi-extra.json')]);
 const house=(h&&h.items)||{};const words=((w&&w.items)||[]).map(x=>{const hh=house[x.match_loose];return hh&&hh.house?Object.assign({},x,{house_spelling:hh.house}):x;});
 try{return window.AneesWordBankArabizi.create(words,cat||{},extra||{});}catch(e){return null;}
}
async function mount(host){
 if(!host)return;host.innerHTML='<div class="vp-notice">Loading the sentence ladder…</div>';
 try{
  const summary=await json('data/sentence-ladder.json');
  const files=summary.files||{},dates=Object.keys(files).sort();
  const got=await Promise.all(dates.map(d=>json(files[d]).catch(()=>null)));
  const listen=[],meta=new Map();got.forEach((f,i)=>{if(!f)return;meta.set(dates[i],{audio:f.audio});listen.push(...(f.listen||[]).map(u=>Object.assign({date:dates[i]},u)));});
  const labels=[].concat(LS('anees-sentence-label-server')||[],LS('anees-sentence-label-log')||[],LS('anees-sentence-label-queue')||[]);
  const az=await spelling();
  host.innerHTML='';
  render(host,{summary,units:{listen,meta,byId:new Map(listen.map(u=>[u.id,u]))},labels,az});
 }catch(e){host.innerHTML=`<div class="vp-notice">The sentence ladder could not load (${esc(e.message)}). Refresh to retry.</div>`;}
}
window.AneesFluencyUnknowns={mount,render,build};
})();
