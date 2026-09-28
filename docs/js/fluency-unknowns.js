/* Progress & Stats › Fluency & Complexity › "What the robot doesn't know" (Medi 2026-09-27:
   "This is definitely something we need to build reporting around, I had no idea you had so many unknowns").
   Reports the 3 uncertainties behind the listening ladder, computed from docs/data/sentence-ladder/<date>.json:
   1. why a sentence is `unknown` (why_unknown), 2. where unknowns sit by sentence length and per lesson,
   3. how strong the evidence behind each `understood` is (evidence), plus how many Medi's swipes have settled.
   Called by fluency-ladder.js at the end of render(); never changes a label (the ladder owns that). */
(function(){
'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const P=(a,b)=>b?Math.round(100*a/b)+'%':'—';
const pretty=d=>{if(!d)return '';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
// Plain-English names for the pipeline's reason strings (keys are the pipeline's own text; unknown keys show as-is).
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
const panel=(id,key,title,sub,body,foot)=>`<section class="vp-panel ${id==='len'||id==='act'?'fl-wide':''}" aria-labelledby="fu-h-${id}"><div class="vp-panelhead"><div><span class="fl-key">${key}</span><h2 id="fu-h-${id}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div></div>${body}${foot?`<p class="fu-foot">${foot}</p>`:''}</section>`;
const bar=(label,sub,v,max,cls,right)=>`<div class="fu-row" title="${esc(sub||'')}"><div class="fu-lab"><b>${esc(label)}</b>${sub?`<small>${esc(sub)}</small>`:''}</div><div class="fu-track"><i class="${cls}" style="width:${max?Math.max(1.5,100*v/max):0}%"></i></div><span class="fu-v">${right}</span></div>`;

function build(units,swipes,ladder){
 const L=units.filter(u=>u.side==='listen');
 const unk=L.filter(u=>u.label==='unknown'),und=L.filter(u=>u.label==='understood');
 const why=new Map();for(const u of unk){const k=u.why_unknown||'no reason recorded';why.set(k,(why.get(k)||[]).concat(u));}
 const ev=new Map();for(const u of und){const k=u.evidence||'content reply only';ev.set(k,(ev.get(k)||0)+1);}
 const byLen=new Map();for(const u of L){const k=Math.min(u.n||0,10);const c=byLen.get(k)||{understood:0,breakdown:0,unknown:0};c[u.label]=(c[u.label]||0)+1;byLen.set(k,c);}
 const byLesson=new Map();for(const u of L){const c=byLesson.get(u.date)||{all:0,unk:0,remark:0};c.all++;if(u.label==='unknown'){c.unk++;if(/one-word remark/.test(u.why_unknown||''))c.remark++;}byLesson.set(u.date,c);}
 const byId=new Map(L.map(u=>[u.id,u]));
 const latest=new Map();for(const r of swipes||[]){const id=r.sentence_id||r.id;if(!byId.has(id))continue;const p=latest.get(id);if(!p||String(r.ts||'')>=String(p.ts||''))latest.set(id,r);}
 const settled=[...latest.entries()].map(([id,r])=>({u:byId.get(id),r}));
 const N=ladder&&ladder.N,T=ladder&&ladder.target;
 const atRung=unk.filter(u=>u.n===N||u.n===T).length;
 const strong=und.filter(u=>STRONG.has(u.evidence)).length;
 return {L,unk,und,why,ev,byLen,byLesson,settled,N,T,atRung,strong,long:unk.filter(u=>(u.n||0)>=3).length};
}

function whyPanel(d){
 const rows=[...d.why.entries()].sort((a,b)=>b[1].length-a[1].length),max=rows.length?rows[0][1].length:0;
 const body=rows.map(([k,us])=>{const w=WHY[k]||[k,''];const ex=us.find(u=>u.text)||{};return bar(w[0],w[1],us.length,max,/one-word/.test(k)?'fu-soft':'fu-mid',`${n(us.length)} <small>${P(us.length,d.unk.length)}</small>`)+(ex.text?`<div class="fu-ex" lang="ar" dir="rtl" title="Example, ${esc(pretty(ex.date))}">${esc(ex.text)}${ex.reply&&ex.reply.text?` <span dir="ltr">→ ${esc(ex.reply.text)}</span>`:''}</div>`:'');}).join('');
 return panel('why','U1','Why sentences are unknown',`${n(d.unk.length)} of ${n(d.L.length)} listening sentences (${P(d.unk.length,d.L.length)}). Each one sits out of the score: never counted as understood or missed.`,body||'<div class="vp-empty">No unknown sentences.</div>','Her one-word remarks are the biggest group, and most were never a test of your listening.');
}
function lenPanel(d){
 const keys=[...d.byLen.keys()].sort((a,b)=>a-b);const max=Math.max(1,...keys.map(k=>{const c=d.byLen.get(k);return c.understood+c.breakdown+c.unknown;}));
 const cols=keys.map(k=>{const c=d.byLen.get(k),t=c.understood+c.breakdown+c.unknown,rung=k===d.N?'fu-rung-now':k===d.T?'fu-rung-next':'';
  const seg=(v,cls,lab)=>v?`<i class="${cls}" style="height:${100*v/max}%" title="${k===10?'10+':k} words · ${lab}: ${n(v)} of ${n(t)} (${P(v,t)})"></i>`:'';
  return `<div class="fu-col ${rung}"><div class="fu-stack">${seg(c.unknown,'fu-unk','unknown')}${seg(c.breakdown,'fu-bd','missed')}${seg(c.understood,'fu-ok','understood')}</div><span class="fu-x">${k===10?'10+':k}</span><span class="fu-pct">${P(c.unknown,t)}</span></div>`;}).join('');
 return panel('len','U2','Where the unknowns sit, by sentence length','Bar height = sentences at that length. Grey = unknown, red = missed, green = understood. The % under each bar is its unknown share.',
  `<div class="fu-cols" role="img" aria-label="Sentences by length and label">${cols}</div><div class="gp-legend fu-legend"><span><i class="fu-ok"></i>understood</span><span><i class="fu-bd"></i>missed</span><span><i class="fu-unk"></i>unknown</span>${d.N?`<span><i class="fu-now"></i>your rung (${n(d.N)})</span><span><i class="fu-next"></i>next rung (${n(d.T)})</span>`:''}</div>`,
  `${n(d.byLen.get(1)?d.byLen.get(1).unknown:0)} of the ${n(d.unk.length)} unknowns are one-word sentences. At your rungs (${n(d.N)} and ${n(d.T)} words) there are ${n(d.atRung)}, so the ladder barely feels them.`);
}
function lessonPanel(d){
 const ds=[...d.byLesson.keys()].sort(),max=Math.max(1,...ds.map(k=>d.byLesson.get(k).unk/Math.max(1,d.byLesson.get(k).all)));
 const body=ds.map(k=>{const c=d.byLesson.get(k),share=c.unk/Math.max(1,c.all),rem=c.remark/Math.max(1,c.all);
  return `<div class="fu-row fu-row-l" title="${esc(pretty(k))}: ${n(c.unk)} unknown of ${n(c.all)} (${n(c.remark)} were her one-word remarks)"><div class="fu-lab"><b>${esc(pretty(k))}</b></div><div class="fu-track"><i class="fu-soft" style="width:${100*rem/max}%"></i><i class="fu-mid fu-after" style="width:${100*(share-rem)/max}%"></i></div><span class="fu-v">${P(c.unk,c.all)}</span></div>`;}).join('');
 return panel('lesson','U3','Unknowns per lesson','Share of each lesson’s listening sentences that are unknown. Light = her one-word remarks, dark = everything else (mostly bare “aywa”).',body,'A dark bar that grows means more nodding along. That is the part worth watching.');
}
function evPanel(d){
 const rows=[...d.ev.entries()].sort((a,b)=>(STRONG.has(b[0])-STRONG.has(a[0]))||b[1]-a[1]),max=Math.max(1,...rows.map(r=>r[1]));
 const body=`<div class="fu-split" role="img" aria-label="${n(d.strong)} strong, ${n(d.und.length-d.strong)} weakest"><i class="fu-ok" style="width:${100*d.strong/Math.max(1,d.und.length)}%">${P(d.strong,d.und.length)} clear proof</i><i class="fu-weak" style="width:${100*(d.und.length-d.strong)/Math.max(1,d.und.length)}%">${P(d.und.length-d.strong,d.und.length)} weakest</i></div>`+
  rows.map(([k,v])=>bar(EV[k]||k,'',v,max,STRONG.has(k)?'fu-okbar':'fu-weakbar',n(v))).join('');
 return panel('ev','U4','How sure are the “understood” ones?',`Of ${n(d.und.length)} sentences labelled understood, how each one earned it.`,body,'“You just kept talking” means your reply fit the conversation but proved nothing specific. These are the likeliest hidden misses, and why the strict ladder reads 2 instead of 7.');
}
function actPanel(d,S){
 const sw=d.settled,onUnk=sw.filter(x=>x.u.label==='unknown'),res=onUnk.filter(x=>x.r.label==='understood'||x.r.label==='breakdown');
 const weakSw=sw.filter(x=>x.u.label==='understood'&&!STRONG.has(x.u.evidence)),weakWrong=weakSw.filter(x=>x.r.label==='breakdown').length;
 const tile=(v,l,s)=>`<div class="fu-tile"><b>${v}</b><span>${esc(l)}</span>${s?`<small>${esc(s)}</small>`:''}</div>`;
 const body=`<div class="fu-tiles">${tile(n(d.long),'unknowns at 3+ words','the ones that could move the ladder')}${tile(n(sw.length),'sentences you have swiped','your answer replaces the robot’s')}${tile(sw.length?n(res.length)+' of '+n(onUnk.length):'—','unknowns your swipes settled',sw.length?'':'swipe after your next lesson')}${tile(weakSw.length?P(weakWrong,weakSw.length):'—','of “weakest” understood you marked missed',weakSw.length?`${n(weakWrong)} of ${n(weakSw.length)} swipes`:'no swipes on these yet')}</div>
 <ol class="fu-do"><li><b>You:</b> the 10-card swipe check already aims 3 cards at unknowns. That is the fastest way to shrink this.</li><li><b>Amal:</b> after a bare “aywa”, one quick “يعني شو قلت؟” turns an unknown into a real answer. Research on hidden non-understanding suggests exactly this kind of check.</li><li><b>The robot:</b> her one-word remarks could be dropped from scoring altogether, since they rarely test you. Decision for Medi.</li></ol>`;
 return panel('act','U5','Turning unknowns into answers','What has been settled so far, and the three levers.',body,'');
}

function render(host,ctx){
 if(!host||!ctx||!ctx.summary)return;
 let sec=host.querySelector('#fu-section');
 if(!sec){sec=document.createElement('section');sec.id='fu-section';sec.setAttribute('aria-label','What the robot does not know');host.appendChild(sec);}
 const units=ctx.units&&ctx.units.listen;
 if(!units){sec.innerHTML='<div class="vp-notice">Loading every sentence…</div>';return;}
 const d=build(units,ctx.labels||[],ctx.summary.ladder&&ctx.summary.ladder.listen);
 sec.innerHTML=`<div class="fu-head"><span class="vp-eyebrow">Reporting on the gaps</span><h2 class="ov-h2">What the robot doesn’t know</h2><p class="ab-sub">${n(d.unk.length)} unknown and ${n(d.und.length-d.strong)} weakly-proven sentences behind your listening numbers: why, where, and how to shrink them.</p></div>
 <div class="vp-grid">${whyPanel(d)}${evPanel(d)}${lenPanel(d)}${lessonPanel(d)}${actPanel(d,ctx.summary)}</div>`;
}
window.AneesFluencyUnknowns={render,build};
})();
