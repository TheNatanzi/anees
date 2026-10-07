/* AI Reports › Unknowns › "What the robot doesn't know: vocabulary" (Medi 2026-09-27: "What are the reports for
   unknown vocab words?" … "These are system issues and should go into the AI reports" … "these should have accordions
   with the exact sentence, similar to our grammar and word bank").
   Vocab twin of docs/js/fluency-unknowns.js (U1–U5). Five panels, every number computed here at runtime:
   V1 why Medi's word events are unresolved · V2 never-checked forms · V3 unresolved per lesson ·
   V4 how sure the "known" (Good/Mastered) forms are · V5 what settles them, and the 3 words to check first.
   Loads its own data exactly like vocabulary-progress.js load() + word-bank.js clip binding (Supabase words, the speaking
   snapshot or data/word-bank-evidence.json, the catalog, the review overlay → AneesWordBank.models); scoring is the
   Word Bank's own (AneesWordBank.points/score). Arabizi via AneesWordBankArabizi built like grammar-console.js (S1);
   transcripts are shown as recorded (S2). Every category row is a <details> accordion that lists its exact word
   events lazily, 25 at a time. Needs (in order): config, speaking-snapshot, word-bank-review, word-bank-core,
   vocabulary-memory, vocabulary-stats, word-bank-arabizi, word-bank-context (optional: turns), then this file.
   API: window.AneesVocabUnknowns.render(host). */
(function(){
'use strict';
const C=window.AneesWordBank,S=window.AneesVocabularyStats;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=v=>v===null||v===undefined||Number.isNaN(v)?'—':Number(v).toLocaleString();
const P=(a,b)=>b?Math.round(100*a/b)+'%':'—';
const pretty=d=>{if(!d)return '—';const p=String(d).split('-');return new Date(+p[0],+p[1]-1,+p[2]).toLocaleDateString(undefined,{month:'short',day:'numeric'});};
const mmss=t=>{t=Math.max(0,Number(t)||0);return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');};
const AR=/[ء-غف-يٱ]/;
const PAGE=25;

/* ---------- data (same sources and order as vocabulary-progress.js load()) ---------- */
let loading=null;
async function json(url,options={}){const r=await fetch(url,{...options,cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('Request failed ('+r.status+')');return r.json();}
const cached=key=>{try{return JSON.parse(localStorage.getItem(key)||'null');}catch{return null;}};
function load(){
 if(loading)return loading;
 loading=(async()=>{
  const A=window.ANEES||{},headers={apikey:A.anon,Authorization:'Bearer '+A.anon};
  const wordsLive=async()=>{const all=[];for(let offset=0;;offset+=1000){const p=await json(A.url+'/rest/v1/words?select=key,arabizi,arabic,arabic_plural,english,plural,topic,subtopic,doc_order,aliases,house_spelling,active,first_seen&order=doc_order.asc,key.asc&limit=1000&offset='+offset,{headers});all.push(...p);if(p.length<1000)return all;}};
  const R=await Promise.allSettled([A.url?wordsLive():Promise.reject(Error('no config')),A.url&&window.AneesSnapshot?window.AneesSnapshot.load(A.url,headers):Promise.reject(Error('no snapshot')),json('data/words.json'),json('data/word-bank-evidence.json'),json('data/word-bank-catalog.json'),json('data/word-bank-review.json'),json('data/word-bank-clips.json'),json('data/house_spelling.json'),json('data/arabizi-extra.json'),json('data/word-bank-audit-slips.json')]);
  const get=i=>R[i].status==='fulfilled'?R[i].value:null;
  const saved=get(2),catalog=get(4),review=get(5),notes=[];
  let words=get(0)||cached('anees-bank-words-v2')||cached('anees-words')||saved?.items;
  if(!get(0))notes.push('Saved vocabulary (live list unavailable).');
  if(Array.isArray(words))words=words.map(w=>w.introduced_at||w.doc_added_at||!w.first_seen?w:{...w,introduced_at:w.first_seen});
  const live=get(1),snap=Array.isArray(live?.events)?live:get(3)||cached('anees-speaking-evidence-v1');
  if(snap!==live)notes.push('Using the published lesson evidence.');
  if(!Array.isArray(words)||!Array.isArray(snap?.events)||!catalog||!review)throw Error('Reviewed vocabulary evidence is unavailable.');
  const reviewed=window.AneesWordBankReview.apply(window.AneesWordBankReview.withSlips(snap.events,get(9)),review),stale=new Set(reviewed.stale);   // audit word slips (eng audit 2026-09-29)
  let events=C.prepareEvidence(reviewed.events.map(e=>stale.has(e.id)?{...e,needs_review:true}:e));
  // Sentence clips, bound exactly as word-bank.js binds them.
  const clips=get(6)?.clips||{};
  events=events.map(e=>{const clip=clips[e.id];const bound=clip&&clip.source_sha256===e.source_sha256&&clip.lesson===e.lesson_date&&clip.start<=e.t_start&&clip.end>=e.t_end&&(e.context||[]).every(r=>Number.isFinite(r.timeline_start)&&Number.isFinite(r.timeline_end)&&r.timeline_start>=clip.start&&r.timeline_end<=clip.end);return bound?{...e,sentence_audio_url:clip.sentence_audio_url}:e;});
  const rows=C.models(words,catalog,events,[]);
  // Her spellings for display (S1), built exactly like grammar-console.js.
  let arabizi=null;
  if(window.AneesWordBankArabizi){const house=get(7)?.items||{};const doc=(saved?.items||[]).map(w=>{const h=house[w.match_loose];return h&&h.house?{...w,house_spelling:h.house}:w;});arabizi=window.AneesWordBankArabizi.create(doc,catalog||{},get(8)||{});}
  return {rows,events,review,stale:reviewed.stale.length,arabizi,notes};
 })();
 loading.catch(()=>{loading=null;});
 return loading;
}

/* ---------- plain-English reasons for unresolved events ---------- */
// Keys are matched against the Word Bank's own reason text (word-bank-evidence.json + the review overlay).
const WHY={
 hold:["Scored, then put on hold","It had a verdict, but its recording changed since, so the verdict waits for a recheck."],
 isolated:["Said alone, nothing around it","One word on its own. The talk around it cannot show you knew it."],
 noamal:["The tutor’s audio is missing","Her track is missing for that stretch, so no one can tell if she prompted you."],
 wording:["Transcript unclear","The words are garbled or ambiguous, so the word itself is not certain."],
 cue:["The tutor cued or repeated it","She said or hinted it near your try. A person has to judge if it was yours."],
 old:["Old grade withheld","Graded by the old rules, before the context audit, and not re-judged yet."],
 legacy:["Old match can’t be traced","An early import that cannot be tied back to one exact word."],
 wrongword:["Matched the wrong word","A look-alike word or a speech-to-text split, not the listed word."],
 grammar:["Grammar practice, not vocab","The exchange was about tense, person or agreement, so it is no vocab test."],
 repeat:["Repeat in the same exchange","A restart or repeat of one try. That try is counted once."],
 clar:["You asked “what?”","A clarification question, not a missed word."],
 other:["One-off reviewer notes","Cases a reviewer wrote up one by one."],
 open:["Open question for a person","The audit could not settle it from the recording. Its question is on the card."],
 nc_echo:["Not counted: echo of the tutor","The student says the tutor’s words back right after her. An echo is not a recall."],
 nc_repeat:["Not counted: repeat or restart","A restart or stutter of one try in the same exchange. That try is counted once."],
 nc_grammar:["Not counted: grammar practice","The exchange was about tense, person or agreement, so it is scored as grammar."],
 nc_not_this_word:["Not counted: not this word","A look-alike word or a speech-to-text split, not the listed word."],
 nc_quote:["Not counted: quoting or reading","The student quotes, reads out or asks about the word. That is no recall."],
 nc_filler:["Not counted: filler","“u” / و used as a filler sound, not the word “and”."],
 nc_clarification:["Not counted: asking what it means","A clarification question, not a try at the word."],
 nc_form_not_on_list:["Not counted: form not on the list","The form he said is not one of the listed forms for this word."],
 nc_farsi:["Not Arabic: Farsi side conversation","The student talking to family in Farsi during the lesson. Not Arabic, so never scored."],
 nc_other:["Not counted: other","Left out of the score by the audit."],
 ne_tutor_audio_missing:["No evidence possible: the tutor’s audio missing","Her track is missing for that stretch, so no one can tell if she prompted him."],
 ne_transcript_unclear:["No evidence possible: transcript unclear","The recording is too unclear to know which word was said."],
 ne_other:["No evidence possible","The recordings cannot show whether he knew it."]
};
const FIXABLE=new Set(['open','hold','isolated','noamal','wording','cue','old','legacy','wrongword','clar','other']); // a human check could change these
// The rest (repeat, grammar) are left out of the score on purpose, not unresolved (Medi 2026-09-28: "why is this unresolved?"
// on an exact echo of Amal). They get their own V1 group and a "Not counted" badge; every count stays the same.
const BY_DESIGN={has:k=>k==='repeat'||k==='grammar'||String(k).startsWith('nc_')};   // left out on purpose
const NO_EVIDENCE={has:k=>String(k).startsWith('ne_')};                                 // the recordings cannot settle it
const isOpen=k=>!BY_DESIGN.has(k)&&!NO_EVIDENCE.has(k);
function bucket(e){
 const r=String(e.reason||''),ab=e.audit_bin,ak=String(e.audit_kind||'other');
 // The 2026-09-28 audit put every unresolved event in one bin; its bin wins over the reason-text guess.
 if(ab==='not_counted')return WHY['nc_'+ak]?'nc_'+ak:'nc_other';
 if(ab==='no_evidence')return WHY['ne_'+ak]?'ne_'+ak:'ne_other';
 if(ab==='open')return 'open';
 if(e.needs_review&&e.assessment!=='unresolved')return 'hold'; // a scored verdict paused because its recording changed
 if(/^Isolated production/i.test(r))return 'isolated';
 if(/^Tutor cue\/repetition/i.test(r))return 'cue';
 if(/^Source-bound historical/i.test(r))return 'old';
 if(/^Legacy match/i.test(r))return 'legacy';
 if(/^Ambiguous vocabulary/i.test(r))return 'wording';
 if(/tutor (recording|track|transcript)[^.]*(unavailable|missing)|missing tutor|lacks the tutor recording|tutor context (is |for the interval is )?(unavailable|missing)|microphone/i.test(r))return 'noamal';
 if(e.immediate_repeat||e.is_echo||e.scored_in_event||/\b(repeat|repeats|repeated|repetition|restates?|restart|rehears|continuation|echo)/i.test(r))return 'repeat';
 if(/homograph|false (binding|start|lexical|noun)|wrong catalog meaning|different meaning|not the |rebind|detach|\bASR\b|hallucinat|fragment|transcri/i.test(r))return 'wrongword';
 if(/clarification/i.test(r))return 'clar';
 if(/grammar|agreement|conjugat|tense|person|pronoun|possessive|morpholog|null/i.test(r))return 'grammar';
 if(/wording|ambiguous|unclear/i.test(r))return 'wording';
 return 'other';
}

/* ---------- the numbers ---------- */
function compute(D){
 const {rows,events,review}=D;
 const rowByKey=new Map();for(const r of rows)for(const k of r.keys||[r.key])if(!rowByKey.has(k))rowByKey.set(k,r);
 const formById=new Map();for(const r of rows)for(const f of r.entries)formById.set(f.id,{r,f});
 const medi=events.filter(e=>e.speaker==='Medi'),prep=medi.filter(e=>C.isGrammar(e)),M=medi.filter(e=>!C.isGrammar(e));
 const unknown=e=>e.assessment==='unresolved'||!!e.needs_review;
 const U=M.filter(unknown).map(e=>({e,b:bucket(e)})),open=U.filter(u=>isOpen(u.b)).length;
 // V1
 const AS=['independent','helped','incorrect','recall_failure','unresolved'];
 const assess=Object.fromEntries(AS.map(a=>[a,M.filter(e=>e.assessment===a).length]));
 const byWhy=new Map();for(const u of U){if(!byWhy.has(u.b))byWhy.set(u.b,[]);byWhy.get(u.b).push(u.e);}
 const notCounted=M.filter(e=>!unknown(e)&&C.points(e)===null).length;
 // V2: forms with no scored try ("Not yet checked"), split by what the lessons hold for them.
 const F=S.forms(rows),ex=S.exercised(F);
 const amalHeard=f=>(f.observations||[]).filter(e=>e.speaker==='Amal'&&!e.immediate_repeat&&!e.is_echo);
 const mediUses=f=>f.events.filter(e=>e.speaker==='Medi').concat((f.observations||[]).filter(e=>e.speaker==='Medi'&&!f.events.includes(e)));
 const unchecked=F.filter(x=>x.form.speaking.status==='Untested');
 const V2={slots:[],never:[],heard:[],said:[]};
 for(const x of unchecked){
  if(mediUses(x.form).length)V2.said.push(x);else if(amalHeard(x.form).length)V2.heard.push(x);else if(!ex.has(x.form))V2.slots.push(x);else V2.never.push(x);
 }
 const typeOf=x=>x.form.label==='Word'?'Word (one form)':x.form.label;
 const types=new Map();for(const x of unchecked){const k=typeOf(x);const v=types.get(k)||{k,all:0,slots:0,list:[]};v.all++;if(!ex.has(x.form)&&!mediUses(x.form).length&&!amalHeard(x.form).length)v.slots++;v.list.push(x);types.set(k,v);}
 const unassigned=rows.filter(r=>!r.grammar_only).reduce((s,r)=>s+r.unassigned.filter(e=>e.speaker==='Medi').length,0);
 // V3
 const byLesson=new Map();for(const e of M){const d=C.date(e);if(!d)continue;const c=byLesson.get(d)||{d,all:0,unk:[],why:new Map()};c.all++;if(unknown(e)&&isOpen(bucket(e))){c.unk.push(e);const b=bucket(e);c.why.set(b,(c.why.get(b)||0)+1);}byLesson.set(d,c);}
 const lessons=[...byLesson.values()].sort((a,b)=>a.d.localeCompare(b.d)).map(c=>{const top=[...c.why.entries()].sort((a,b)=>b[1]-a[1])[0]||null;return {...c,top:top?top[0]:null,topN:top?top[1]:0};});
 // V4: Good/Mastered forms, by the evidence under the Word Bank's own status.
 const known=F.filter(x=>['Good','Mastered'].includes(x.form.speaking.status)).map(x=>{
  const at=x.form.speaking.attempts,right=at.filter(a=>a.p===1),days=new Set(right.map(a=>C.date(a))).size;
  const helped=at.filter(a=>a.p===.5).length,echo=(x.form.observations||[]).filter(e=>e.speaker==='Medi'&&(e.immediate_repeat||e.is_echo)).length;
  const band=days>=2?'multi':(helped+echo)*2>=at.length+echo&&(helped+echo)>0?'helped':at.length===1?'single':'oneday';
  return {...x,band,right:right.length,days,helped,echo,tries:at.length};
 });
 const BANDS=[['multi','Right, unaided, in 2+ lessons','Strongest: recalled on different days.','vu-ok'],['oneday','Right in one lesson only','Several tries, all on one day. Could be short-term.','vu-mid'],['single','One right try, ever','The Word Bank marks a form Good after one right first try.','vu-weak'],['helped','Mostly helped or echoing the tutor','Half or more of your uses were hinted or repeats of her.','vu-weak']];
 // V5: what the review overlay has settled, and the words worth checking first.
 const patches=Object.values(review?.patches||{});
 const SCORED=new Set(['independent','helped','incorrect','recall_failure']);
 const settled=patches.filter(p=>p.expected?.assessment==='unresolved'&&SCORED.has(p.changes?.assessment)).length;
 const withheld=patches.filter(p=>SCORED.has(p.expected?.assessment)&&p.changes?.assessment==='unresolved').length;
 const words=new Map();for(const u of U){if(!FIXABLE.has(u.b))continue;const k=u.e.word_key;if(!k)continue;const v=words.get(k)||{k,list:[],days:new Set()};v.list.push(u.e);v.days.add(C.date(u.e));words.set(k,v);}
 const top=[...words.values()].sort((a,b)=>b.list.length-a.list.length||b.days.size-a.days.size||a.k.localeCompare(b.k)).slice(0,3).map(v=>({...v,row:rowByKey.get(v.k)}));
 return {M,prep,U,open,assess,byWhy,notCounted,unchecked,V2,types:[...types.values()].sort((a,b)=>b.all-a.all),unassigned,lessons,known,BANDS,patches:patches.length,settled,withheld,stale:D.stale,top,fixable:U.filter(u=>FIXABLE.has(u.b)).length,flagged:M.filter(e=>e.needs_review).length,rowByKey,formById,amalHeard,mediUses};
}

/* ---------- sentences: Arabizi on top (S1), Arabic under, target word marked ---------- */
let toArabizi=null;
const CTX=()=>window.AneesWordBankContext;
function rowText(r){return r.reviewed_text||r.original_text||r.text||'';}
function markHTML(text,word,cls){
 text=String(text||'');const w=String(word||'').replace(/[.,،؟?!:;"“”()]/g,'').trim();
 if(!w)return esc(text);
 const re=new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'giu');let out='',at=0,m,hit=false;
 while((m=re.exec(text))){const L=text[m.index-1]||'',R=text[m.index+m[0].length]||'';if(/[\p{L}\p{N}]/u.test(L)||/[\p{L}\p{N}]/u.test(R))continue;out+=esc(text.slice(at,m.index))+`<mark class="${cls}">`+esc(m[0])+'</mark>';at=m.index+m[0].length;hit=true;}
 return hit?out+esc(text.slice(at)):esc(text);
}
function speech(html){
 const src=document.createElement('span');src.innerHTML=html;
 if(!toArabizi||!AR.test(src.textContent))return `<span class="vu-lat" dir="auto">${html}</span>`;
 const latin=src.cloneNode(true),walk=document.createTreeWalker(latin,NodeFilter.SHOW_TEXT,null),nodes=[];let t,approx=false;
 while((t=walk.nextNode()))nodes.push(t);
 for(const node of nodes){if(!AR.test(node.nodeValue))continue;const r=toArabizi(node.nodeValue);if(r.approximate)approx=true;node.nodeValue=r.text;}
 return `<span class="vu-lat" dir="auto">${latin.innerHTML}</span><span class="vu-ar" dir="auto" lang="ar">${html}</span>${approx?'<span class="vu-spell">Unverified spelling stays in Arabic</span>':''}`;
}
function turnsOf(e){
 const X=CTX();
 if(X){const T=X.turns(e.context||[]),i=T.findIndex(t=>t.rows.some(r=>X.owns(e,r)));return {T,i};}
 const own=(e.context||[]).findIndex(r=>r.row_id===e.row_id&&r.speaker===e.speaker);
 return {T:(e.context||[]).map(r=>({speaker:r.speaker,rows:[r]})),i:own};
}
function audioOf(e){const p=e.sentence_audio_url||e.audio_url;if(!/^lessons\/\d{4}-\d{2}-\d{2}\/(?:audio\/(?:Medi|Amal)\.mp3|clips\/[A-Za-z0-9_.-]+\.mp3)$/.test(p||''))return null;return {src:p,start:e.sentence_audio_url||p.includes('/clips/')?0:Math.max(0,(Number(e.local_start??e.t_start)||0)-2)};}   // 2 s of lead-in
// A "repeat in the same exchange" is an echo of Amal when she said the word just before him (or the reviewer says so),
// otherwise a repeat of his own earlier try.
const squash=t=>String(t||'').toLowerCase().replace(/[\u064B-\u0652\u0640]/g,'').replace(/[.,،؟?!:;"“”()\-]/g,' ').replace(/\s+/g,' ').trim();
function echoOfAmal(e){
 if(e.is_echo)return true;
 if(/\b(tutor|amal|supplied)\b|echo/i.test(String(e.reason||'')))return true;
 const {T,i}=turnsOf(e),w=squash(e.text);if(!w||i<0)return false;
 for(let k=i-1;k>=0&&i-k<=3;k--)if(T[k].speaker==='Amal')return (' '+squash(T[k].rows.map(rowText).join(' '))+' ').includes(' '+w+' ');
 return false;
}
function notCounted(e){if(e.speaker!=='Medi'||e.assessment!=='unresolved')return null;const b=bucket(e);if(!isOpen(b)&&WHY[b]&&b.includes('_'))return b;return b==='grammar'?'nc_grammar':b==='repeat'?(echoOfAmal(e)?'nc_echo':'nc_repeat'):null;}
const machine=e=>/^Claude\b/i.test(String(e.reviewer||e.audit_by||''));
function outcome(e){if(e.audit_bin==='open'&&e.speaker==='Medi')return ['Open question','vu-o-hold'];if(e.needs_review)return ['On hold','vu-o-hold'];if(e.speaker!=='Medi')return ['The tutor said it','vu-o-amal'];const p=C.points(e);if(p===1)return ['Correct','vu-o-ok'];if(p===.5)return ['Partial','vu-o-part'];if(p===0)return ['Wrong','vu-o-bad'];const nc=notCounted(e);if(nc)return [NC_BADGE(nc),'vu-o-nc'];if(e.audit_bin==='open')return ['Open question','vu-o-unk'];return e.assessment==='unresolved'?['Unresolved','vu-o-unk']:['Not scored','vu-o-unk'];}
function NC_BADGE(k){return k.startsWith('ne_')?'No evidence possible':WHY[k][0];}
function wordName(e,d){const r=d.rowByKey.get(e.word_key);return r?{name:r.name,en:r.english||''}:{name:e.word_key||'?',en:''};}
function eventItem(e,d){
 const {T,i}=turnsOf(e),own=i>=0?T[i]:null;
 const said=own?own.rows.map(rowText).join(' '):(e.original_text||e.text||'');
 let prev=null;if(e.speaker==='Medi'&&i>0)for(let k=i-1;k>=0;k--){if(T[k].speaker==='Amal'){prev=T[k];break;}if(i-k>3)break;}
 const p=C.points(e),cls=p===1?'ab-correct':p===.5?'ab-partial':p===0?'ab-wrong':'vu-hit';
 const [olab,ocls]=outcome(e),w=wordName(e,d),a=audioOf(e),nc=!e.needs_review&&notCounted(e),b=nc?WHY[nc]:e.speaker==='Medi'&&(e.assessment==='unresolved'||e.needs_review)?WHY[bucket(e)]:null;
 const who=machine(e)?`<span class="vu-note">Machine verdict: ${esc(e.reviewer||e.audit_by)}. Not checked by a person yet.</span>`:'';
 const note=e.reason?`<span class="vu-note">${machine(e)?'Audit note':'Reviewer note'}: ${esc(String(e.reason).replace(/^Claude audit \d{4}-\d{2}-\d{2}:\s*/,''))}</span>`:'';
 return `<li class="vu-ev"><div class="vu-evhead"><span>${esc(pretty(C.date(e)))} · ${mmss(e.t_start)}</span><b>${esc(w.name)}</b>${w.en?`<span class="vu-en">${esc(w.en)}</span>`:''}<span class="vu-o ${ocls}">${esc(olab)}</span></div>`+
  (prev?`<div class="vu-turn vu-amal"><span class="vu-who">The tutor, just before</span>${speech(esc(prev.rows.map(rowText).join(' ')))}</div>`:'')+
  `<div class="vu-turn"><span class="vu-who">${e.speaker==='Medi'?'You said':'The tutor said'}</span>${speech(markHTML(said,e.text,cls))}</div>`+
  (b?`<div class="vu-why"><b>${esc(b[0])}.</b> ${esc(b[1])}${e.audit_question?`<span class="vu-q"><b>Question:</b> ${speech(esc(e.audit_question))}</span>`:''}${note}${who}</div>`:(who?`<div class="vu-why">${who}</div>`:''))+
  (a?`<audio class="vu-audio" controls preload="metadata" data-start="${a.start}" src="${esc(a.src)}" aria-label="Play this moment"></audio>`:'<div class="vu-note">No recording for this moment.</div>')+`</li>`;
}
function formItem(x){const f=x.form,r=x.row,name=r.type==='Adjective'||!f.word?r.name:f.word;return `<li class="vu-fm"><b>${esc(name)}</b>${f.arabic?`<span class="vu-far" lang="ar" dir="auto">${esc(f.arabic)}</span>`:''}<span class="vu-en">${esc(r.english||'')}</span><small>${esc(r.entries.length>1?String(f.label).toLowerCase():r.type||'')} · ${esc(r.topic||'')}</small></li>`;}

/* ---------- accordions (lazy, 25 at a time) ---------- */
let lists=new Map(),seq=0;
function acc(summary,items,kind,cls=''){const id='vu-l'+(++seq);lists.set(id,{items,kind,shown:0});return `<details class="vu-acc ${cls}" data-vu="${id}"><summary>${summary}</summary><div class="vu-body"></div></details>`;}
function more(det,d){
 const L=lists.get(det.dataset.vu);if(!L)return;const body=det.querySelector('.vu-body');
 if(!L.items.length){body.innerHTML='<div class="vu-note">Nothing here.</div>';return;}
 let ol=body.querySelector('ol');if(!ol){ol=document.createElement('ol');ol.className='vu-list';body.append(ol);}
 const next=L.items.slice(L.shown,L.shown+PAGE);L.shown+=next.length;
 ol.insertAdjacentHTML('beforeend',next.map(x=>L.kind==='form'?formItem(x):eventItem(x,d)).join(''));
 body.querySelector('.vu-more')?.remove();
 if(L.shown<L.items.length)body.insertAdjacentHTML('beforeend',`<button type="button" class="vu-more">Show ${Math.min(PAGE,L.items.length-L.shown)} more <small>(${n(L.shown)} of ${n(L.items.length)})</small></button>`);
}
const byTime=(a,b)=>String(C.date(b)).localeCompare(String(C.date(a)))||(Number(a.t_start)||0)-(Number(b.t_start)||0);

/* ---------- panels ---------- */
const panel=(id,key,title,sub,body,foot,wide)=>`<section class="vp-panel vu-panel ${wide?'vu-wide':''}" aria-labelledby="vu-h-${id}"><div class="vp-panelhead"><div><span class="vu-key">${key}</span><h2 id="vu-h-${id}">${esc(title)}</h2>${sub?`<p class="ab-sub">${sub}</p>`:''}</div></div>${body}${foot?`<p class="vu-foot">${foot}</p>`:''}</section>`;
const bar=(label,sub,v,max,cls,right,segs)=>`<span class="vu-row"><span class="vu-lab"><b>${esc(label)}</b>${sub?`<small>${esc(sub)}</small>`:''}</span><span class="vu-track">${segs||`<i class="${cls}" style="width:${max?Math.max(1.5,100*v/max):0}%"></i>`}</span><span class="vu-v">${right}</span></span>`;
function example(list){const e=list.find(x=>AR.test(x.text||''))||list[0];if(!e)return '';const {T,i}=turnsOf(e);let s=i>=0?T[i].rows.map(rowText).join(' '):(e.text||'');if(s.length>70){const at=Math.max(0,s.indexOf(e.text||'')-25);s=(at?'…':'')+s.slice(at,at+70)+'…';}return `<span class="vu-ex">${speech(markHTML(s,e.text,'vu-hit'))}</span>`;}

function v1(d){
 const tot=d.M.length,U=d.U.length,rows=[...d.byWhy.entries()].sort((a,b)=>b[1].length-a[1].length),max=rows.length?rows[0][1].length:0;
 const fix=rows.filter(([k])=>isOpen(k)),design=rows.filter(([k])=>BY_DESIGN.has(k)),designN=design.reduce((s,[,l])=>s+l.length,0),noev=rows.filter(([k])=>NO_EVIDENCE.has(k)),noevN=noev.reduce((s,[,l])=>s+l.length,0),openN=U-designN-noevN;
 const SEG=[['independent','vu-ok','on his own'],['helped','vu-mid','helped'],['incorrect','vu-bad','wrong'],['recall_failure','vu-bad','couldn’t recall'],['unresolved','vu-unk','unresolved or not counted']];
 const split=`<div class="vu-split" role="img" aria-label="${SEG.map(([k,,l])=>`${n(d.assess[k])} ${l}`).join(', ')}">${SEG.filter(([k])=>d.assess[k]).map(([k,c,l])=>`<i class="${c}" style="width:${100*d.assess[k]/Math.max(1,tot)}%" title="${esc(l)}: ${n(d.assess[k])} of ${n(tot)} (${P(d.assess[k],tot)})">${d.assess[k]/tot>.12?`${P(d.assess[k],tot)} ${esc(l)}`:''}</i>`).join('')}</div><div class="vu-legend">${SEG.map(([k,c,l])=>`<span><i class="${c}"></i>${esc(l)} ${n(d.assess[k])}</span>`).join('')}</div>`;
 const row=([k,list])=>{const w=WHY[k]||WHY.other;return acc(bar(w[0],w[1],list.length,max,FIXABLE.has(k)?'vu-mid':'vu-soft',`${n(list.length)} <small>${P(list.length,U)}</small>`)+example(list),list.slice().sort(byTime),'event');};
 const body=split+`<div class="vu-sub">Unresolved: a check could settle these · ${n(openN)} · tap a row for every sentence</div>`+(fix.length?fix.map(row).join(''):'<div class="vu-note">Nothing open.</div>')+
  (noev.length?`<div class="vu-sub">No evidence possible · ${n(noevN)} · the recordings cannot show it either way</div>`+noev.map(row).join(''):'')+
  (design.length?`<div class="vu-sub">Not counted by design · ${n(designN)} · echoes, repeats, fillers, grammar practice, Farsi</div>`+design.map(row).join(''):'');
 return panel('why','V1','Why the robot can’t settle these word events',`${n(U)} of the student’s ${n(tot)} word events (${P(U,tot)}) sit out of every score: never right, never wrong. Only ${n(openN)} are still unresolved. ${n(designN)} are left out on purpose, and ${n(noevN)} cannot be judged from the recordings.`,body,`“Not counted by design” rows will never count: an echo of the tutor or a repeat of one try is counted once, grammar practice is scored as grammar, and Farsi is not Arabic. Every row was checked by the Claude audit of 28 Sep 2026.${d.prep.length?` ${n(d.prep.length)} preposition events are left out: they are tracked as grammar.`:''}`);
}
function v2(d){
 const V=d.V2,tot=d.unchecked.length,G=[['never','Never heard or said','No lesson has touched this form yet.',V.never,'vu-soft'],['heard','Heard from the tutor only','She used it; you have not said it yet.',V.heard,'vu-mid'],['said','Said, but unresolved','You said it; every try is unresolved or not scored.',V.said,'vu-weak'],['slots','Form slots no lesson uses','Plural, future or command slots lessons almost never exercise.',V.slots,'vu-unk']];
 const max=Math.max(1,...G.map(g=>g[3].length));
 const items=g=>g[0]==='heard'?g[3].flatMap(x=>d.amalHeard(x.form)).sort(byTime):g[0]==='said'?g[3].flatMap(x=>d.mediUses(x.form)).sort(byTime):g[3];
 const groups=G.map(g=>acc(bar(g[1],g[2],g[3].length,max,g[4],`${n(g[3].length)} <small>${P(g[3].length,tot)}</small>`),items(g),g[0]==='heard'||g[0]==='said'?'event':'form')).join('');
 const tmax=Math.max(1,...d.types.map(t=>t.all));
 const types=d.types.map(t=>acc(bar(t.k,'',t.all,tmax,'',`${n(t.all)}${t.slots?` <small>· ${n(t.slots)} unused</small>`:''}`,`<i class="vu-mid" style="width:${100*(t.all-t.slots)/tmax}%"></i><i class="vu-unk vu-after" style="width:${100*t.slots/tmax}%"></i>`),t.list,'form','vu-acc-sm')).join('');
 return panel('never','V2','Never-checked words',`${n(tot)} studied forms are “Not yet checked”: no scored try. Here is what the lessons hold for them.`,groups+`<div class="vu-sub">By form type · dark = lessons use this type · light = slot no lesson uses</div>`+types,`${n(V.heard.length)} forms are free wins: the tutor already uses them.${d.unassigned?` ${n(d.unassigned)} of your word events hit a word but no single form (tense unclear), so they check nothing.`:''}`);
}
function v3(d){
 const L=d.lessons,max=Math.max(.01,...L.map(c=>c.unk.length/Math.max(1,c.all)));
 const body=L.map(c=>{const share=c.unk.length/Math.max(1,c.all),top=c.top?c.topN/Math.max(1,c.all):0,w=c.top?WHY[c.top][0]:'';
  return acc(`<span class="vu-row vu-row-l" title="${esc(pretty(c.d))}: ${n(c.unk.length)} of ${n(c.all)} unresolved${c.top?`; biggest reason: ${w} (${n(c.topN)})`:''}"><span class="vu-lab"><b>${esc(pretty(c.d))}</b></span><span class="vu-track"><i class="vu-mid" style="width:${100*top/max}%"></i><i class="vu-soft vu-after" style="width:${100*(share-top)/max}%"></i></span><span class="vu-v">${P(c.unk.length,c.all)} <small>${n(c.unk.length)}/${n(c.all)}</small></span></span>${c.top?`<span class="vu-top">Biggest: ${esc(w)} (${n(c.topN)})</span>`:''}`,c.unk.slice().sort(byTime),'event');}).join('');
 const worst=L.slice().sort((a,b)=>b.unk.length/Math.max(1,b.all)-a.unk.length/Math.max(1,a.all))[0];
 return panel('lesson','V3','Unresolved per lesson','Share of each lesson’s word events that are unresolved. Dark = that lesson’s biggest reason, light = the rest.',body||'<div class="vp-empty">No lessons loaded.</div>',worst?`Highest: ${esc(pretty(worst.d))}, ${P(worst.unk.length,worst.all)} unresolved (${esc(worst.top?WHY[worst.top][0].toLowerCase():'')}).`:'',true);
}
function v4(d){
 const K=d.known,tot=K.length,B=d.BANDS.map(([k,l,s,c])=>({k,l,s,c,list:K.filter(x=>x.band===k)})),max=Math.max(1,...B.map(b=>b.list.length));
 const strong=B[0].list.length;
 const split=`<div class="vu-split" role="img" aria-label="${n(strong)} proven in 2+ lessons, ${n(tot-strong)} less sure"><i class="vu-ok" style="width:${100*strong/Math.max(1,tot)}%">${P(strong,tot)} 2+ lessons</i><i class="vu-weak" style="width:${100*(tot-strong)/Math.max(1,tot)}%">${P(tot-strong,tot)} less sure</i></div>`;
 const body=split+B.map(b=>acc(bar(b.l,b.s,b.list.length,max,b.c,`${n(b.list.length)} <small>${P(b.list.length,tot)}</small>`),b.list.flatMap(x=>x.form.speaking.attempts).sort(byTime),'event')).join('');
 return panel('ev','V4','How sure are the “known” words?',`Of ${n(tot)} Good or Mastered forms, what their status rests on. Same attempts the Word Bank scores; no new rules.`,body,`“One right try, ever” is the Word Bank rule working as written: one correct first try makes a form Good. These are the likeliest hidden gaps.`);
}
function v5(d){
 const tile=(v,l,s)=>`<div class="vu-tile"><b>${v}</b><span>${esc(l)}</span>${s?`<small>${esc(s)}</small>`:''}</div>`;
 const tiles=`<div class="vu-tiles">${tile(n(d.settled),'unresolved events settled by review','word-bank-review.json overlay')}${tile(n(d.withheld),'scores pulled back to unresolved','the context audit, same overlay')}${tile(n(d.flagged),'events flagged for a recheck',d.stale?`${n(d.stale)} because their recording changed`:'set by the review overlay')}${tile('—','The tutor’s word-review answers','saved per private link; not readable here')}</div>`;
 const max=Math.max(1,...d.top.map(t=>t.list.length));
 const top=d.top.length?`<div class="vu-sub">Check these 3 first · most frequent fixable unknowns</div>`+d.top.map((t,i)=>acc(bar(`${i+1}. ${t.row?t.row.name:t.k}`,t.row?.english||'',t.list.length,max,'vu-mid',`${n(t.list.length)} <small>${n(t.days.size)} lesson${t.days.size===1?'':'s'}</small>`),t.list.slice().sort(byTime),'event')).join(''):'<div class="vp-empty">No fixable unknowns left.</div>';
 const levers=`<ol class="vu-do"><li><b>Review overlay:</b> a reviewer reads the whole exchange and writes a verdict into word-bank-review.json. Raw transcripts never change (S2).</li><li><b>Tutor:</b> her word-review page asks “what was actually said?” for unclear audio. That settles transcript-unclear rows.</li><li><b>Student:</b> there is no swipe check for words yet (the listening one is sentence-only). A 10-card word swipe aimed at the top of this list would be the fastest lever. Decision for the student.</li></ol>`;
 return panel('act','V5','Turning unknowns into answers',`What settles an unresolved event, what has been settled so far, and ${n(d.fixable)} fixable unknowns to work through.`,tiles+levers+top,'',true);
}

/* ---------- render ---------- */
// Two homes (Medi 2026-09-28: "all the robot stuff goes in the ai reports and everything else is correctly in the progress"):
//  AI Reports › Robot blind spots  = V1 why the robot can't settle word events, V3 per lesson, V5 levers (the machine);
//  Progress › Vocab "How sure are these numbers?" = V4 how sure the known words are, V2 never-checked words (Medi).
// render(host,{panels:[...]}) draws any subset; numbers are always computed over the full data.
const ROBOT=['V1','V3','V5'],MEDI=['V4','V2'],DRAW={V1:v1,V4:v4,V2:v2,V3:v3,V5:v5},ORDER=['V1','V4','V2','V3','V5'];
function head(d,keys){
 const thin=d.known.filter(x=>x.band!=='multi').length;
 if(keys.every(k=>MEDI.includes(k)))return `<div class="vu-head"><span class="vp-eyebrow">How sure are these numbers?</span><h2 class="ov-h2">What your vocab numbers rest on</h2><p class="ab-sub">${n(thin)} of your “known” forms rest on thin proof, and ${n(d.unchecked.length)} studied forms have no scored try yet. Tap any row for the exact sentences.</p><p class="rb-link">Why the robot couldn’t settle ${n(d.open)} of your word events is a robot issue, so it lives on <a href="ai-reports.html?tab=unknowns#ar-unk-vocab">AI Reports › Robot blind spots</a>.</p></div>`;
 if(keys.every(k=>ROBOT.includes(k)))return `<div class="vu-head"><p class="ab-sub">The robot could not settle ${n(d.open)} of the student’s word events: why, in which lessons, and what would settle them. Tap any row for the exact sentences.</p><p class="rb-link">How sure the student’s “known” words are and the never-checked words on his list are about him, so they live on <a href="progress.html?tab=vocab#vp-vocab-sure">Progress › Vocab</a>.</p></div>`;
 return `<div class="vu-head"><span class="vp-eyebrow">Reporting on the gaps · vocabulary</span><h2 class="ov-h2">What the robot doesn’t know: vocabulary</h2><p class="ab-sub">${n(d.open)} unresolved word events, ${n(d.unchecked.length)} never-checked forms and ${n(thin)} thinly-proven “known” forms behind the vocab numbers. Tap any row for the exact sentences.</p></div>`;
}
async function render(host,opts={}){
 if(!host)return;
 if(host.dataset.vuState==='done'||host.dataset.vuState==='loading')return;
 const keys=ORDER.filter(k=>!opts.panels||opts.panels.includes(k));
 host.dataset.vuState='loading';
 host.classList.add('vu-root');
 host.innerHTML='<div class="vp-notice" role="status">Loading every word event…</div>';
 if(!C||!S||!window.AneesWordBankReview){host.innerHTML='<div class="vp-notice">The Word Bank scripts did not load, so this report cannot be computed.</div>';host.dataset.vuState='';return;}
 let D,d;
 try{D=await load();toArabizi=D.arabizi;d=compute(D);}
 catch(e){host.innerHTML=`<div class="vp-notice">The vocabulary numbers could not be computed (${esc(e.message)}). No numbers have been substituted.</div><button type="button" class="ab-control vu-retry">Retry</button>`;host.dataset.vuState='';host.querySelector('.vu-retry').onclick=()=>render(host,opts);return;}
 const last=d.lessons.at(-1);
 host.innerHTML=`${head(d,keys)}
 <div class="vp-grid vu-grid">${keys.map(k=>DRAW[k](d)).join('')}</div>
 <p class="vu-foot vu-end">Computed live from ${n(d.M.length)} of ${keys.every(k=>MEDI.includes(k))?'your':'The student’s'} word events across ${n(d.lessons.length)} lessons${last?` (last ${esc(pretty(last.d))})`:''}, with the Word Bank’s own scoring and review overlay.${D.notes.length?' '+esc(D.notes.join(' ')):''}</p>`;
 host.addEventListener('toggle',ev=>{const det=ev.target;if(det.matches?.('details.vu-acc')&&det.open&&!det.dataset.built){det.dataset.built='1';more(det,d);}},true);
 host.addEventListener('click',ev=>{const b=ev.target.closest('.vu-more');if(b)more(b.closest('details.vu-acc'),d);});
 const seek=a=>{if(a.dataset.seeked)return;const s=Number(a.dataset.start)||0;if(s){try{a.currentTime=s;}catch{}}a.dataset.seeked='1';};
 host.addEventListener('loadedmetadata',ev=>{if(ev.target.matches?.('audio.vu-audio'))seek(ev.target);},true);
 host.addEventListener('play',ev=>{const a=ev.target;if(!a.matches?.('audio.vu-audio'))return;seek(a);for(const o of host.querySelectorAll('audio.vu-audio'))if(o!==a)o.pause();},true);
 host.dataset.vuState='done';
}
window.AneesVocabUnknowns={render,compute,load,bucket,ROBOT,MEDI};
})();
