/* Word Bank v2: pure, event-based scoring. Does not mutate legacy progress. */
(function(root){
'use strict';
const PREPOSITIONS=new Set(['fi','ma3','min','3an','3ala','la','bi','bidUn','zaI','3end','2udAm','wara','bein','janb','foa2','ta7t','bilnos','2bAl','7awalain','7awAlain','7awAli','juwa','bara','2abel','ba3ed','beini u beinak','3ala alyamIn']);
const isGrammar=e=>PREPOSITIONS.has(e.word_key);
const WEIGHTS={Wrong:0,Shaky:5,Good:8,Mastered:10,Untested:null};
const date=e=>String(e.lesson_date||e.ts||e.date||'').slice(0,10);
const time=e=>String(e.lesson_date||e.ts||e.date||'');
// Lesson dates are calendar days, not UTC-midnight instants.
function daysAgo(e,now=new Date()){
 const [y,m,d]=date(e).split('-').map(Number);
 return Math.floor((Date.UTC(now.getFullYear(),now.getMonth(),now.getDate())-Date.UTC(y,m-1,d))/86400000);
}
function unique(events){const m=new Map();for(const e of events||[]){if(e.id)m.set(e.id,e);}return [...m.values()].sort((a,b)=>time(a).localeCompare(time(b))||(Number(a.t_start)||0)-(Number(b.t_start)||0)||String(a.id).localeCompare(String(b.id)));}
// Preserve the source ledger; adapt its sentence context for the agreed Word Bank rules.
function sentence(e){
 const own=(e.context||[]).find(r=>r.row_id===e.row_id&&r.speaker===e.speaker);
 return own?.original_arabizi||own?.arabizi||own?.original_text||own?.text||e.arabizi||e.original_text||e.text||'';
}
function prepareEvidence(events){return unique(events).map(e=>{
 if(isGrammar(e))return {...e,grammar_only:true,classification:"grammar",vocab_points:null,contextual_audit:true,reason:"Preposition or prepositional construction: tracked as grammar, excluded from vocabulary scoring."};
 const own=(e.context||[]).find(r=>r.row_id===e.row_id&&r.speaker===e.speaker);
 const text=normalize(sentence(e)),word=normalize(e.text);
 if(e.speaker==='Medi'&&!e.grammar_only){
  const meaning=sentence(e).match(/(?:شو\s+يعني|shu\s+ya3ni|what\s+does)\s+(.+)/i);
  if(meaning&&['shu','ya3ni'].includes(e.word_key))return {...e,ignored:true,vocab_points:null};
  if(meaning&&word&&normalize(meaning[1]).includes(word))return {...e,assessment:'incorrect',vocab_points:0,ignored:false,immediate_repeat:false,is_echo:false,classification:'lexical'};
  if(e.word_key==='shu'&&/^(?:(?:uh|um|شو|shu|what|huh)\s*)+$/i.test(text))return {...e,ignored:true,vocab_points:null};
  if(e.self_corrected&&!e.is_echo&&!e.immediate_repeat&&!e.scored_in_event)return {...e,assessment:'independent',vocab_points:1,ignored:false};
 }
 const supplied=(e.context||[]).filter(r=>r.speaker==='Amal'&&Number.isFinite(r.timeline_end)&&Number.isFinite(own?.timeline_start)&&own.timeline_start>=r.timeline_end&&own.timeline_start-r.timeline_end<=15);
 // Only an exact repeated sentence or isolated supplied word establishes an echo.
 // A new sentence containing the target remains eligible for partial credit.
 const echo=e.speaker==='Medi'&&e.assessment==='helped'&&text&&supplied.some(r=>{
  const tutor=normalize(r.text),clean=text.replace(/\b(?:uh|um|yeah|okay|oh|so)\b/g,'').replace(/\s+/g,' ').trim();return text===tutor||((text===word||clean===word)&&(' '+tutor+' ').includes(' '+word+' '));
 });
 return echo?{...e,immediate_repeat:true}:e;
});}
function points(e,lane='speaking'){
 if(isGrammar(e))return null;
 if(e.observation_only||e.ignored||e.immediate_repeat||e.is_echo||e.grammar_only||e.classification==='grammar'||e.classification==='ignored')return null;
 if(lane==='speaking'&&e.speaker!=='Medi')return null;
 if(lane==='speaking'&&(!date(e)||!Number.isFinite(e.t_start)))return null;
 if(lane==='speaking'&&(e.assessment==='unresolved'||e.needs_review||e.wording_status==='unresolved'))return null;
 if([0,.5,1].includes(e.vocab_points))return e.vocab_points;
 if(lane==='flashcards')return e.result==='missed'?0:e.result==='got'?(Number(e.attempt||1)>1?.5:1):null;
 if(e.assessment==='unresolved'||e.needs_review)return null;
 // Existing evidence must explicitly distinguish grammar from lexical corrections.
 if((e.correction||e.human_correction)&&!e.classification)return null;
 return {independent:1,helped:.5,recall_failure:0,incorrect:0}[e.assessment]??null;
}
function score(events,lane='speaking'){
 const session=e=>lane==='flashcards'?date(e):String(e.lesson_id||date(e));
 const attempts=unique(events).map(e=>({...e,p:points(e,lane)})).filter(e=>e.p!==null);
 const n=attempts.length;
 if(!n)return {status:'Untested',count:0,accuracy:null,attempts,latest:[]};
 if(n>=10){const latest=attempts.slice(-10),accuracy=latest.reduce((s,e)=>s+e.p,0)*10;
 const days=new Set(latest.filter(e=>e.p===1).map(session));
 const status=accuracy>=90?(days.size>=2?'Mastered':'Good'):accuracy>=75?'Good':accuracy>=50?'Shaky':'Wrong';
 return {status,count:n,accuracy,attempts,latest};}
 let status='Untested',right=[],wrong=0;
 attempts.forEach((e,i)=>{
   const p=e.p,prev=status;
   if(i===0){status=p===1?'Good':'Shaky';right=p===1?[session(e)]:[];wrong=p===0?1:0;return;}
   if(i===1&&attempts[0].p===1&&p!==1){status='Shaky';right=[];wrong=0;return;}
   if(p===.5){right=[];wrong=0;return;}
   if(p===1){wrong=0;right.push(session(e));if(right.length>=2){if(status==='Wrong')status='Shaky';else if(status==='Shaky')status='Good';else if(status==='Good'&&new Set(right.slice(-2)).size>=2)status='Mastered';}}
   else {right=[];wrong++;if(status==='Mastered')status='Good';else if(wrong>=2){if(status==='Good')status='Shaky';else if(status==='Shaky')status='Wrong';}}
   if(status!==prev){right=[];wrong=0;}
 });
 return {status,count:n,accuracy:null,attempts,latest:attempts};
}
function weighted(entries,lane='speaking'){const s=entries.map(e=>e[lane]).filter(s=>s&&s.status!=='Untested');return s.length?s.reduce((n,s)=>n+WEIGHTS[s.status],0)*10/s.length:null;}
function metrics(entries,now=new Date()){
 const age=e=>daysAgo(e,now);
 const recent=entries.filter(e=>e.speaking.attempts.some(a=>age(a)>=0&&age(a)<30));
 return {accuracy:weighted(entries),known:entries.filter(e=>['Good','Mastered'].includes(e.speaking.status)).length,memory:weighted(recent),recent:recent.length,week:entries.filter(e=>e.flashcards.attempts.some(a=>age(a)>=0&&age(a)<7)).length,cards:weighted(entries,'flashcards')};
}
function normalize(s){return String(s||'').normalize('NFKD').replace(/[\u064B-\u065F\u0670\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();}
// Some documented plurals include the Arabic in parentheses. Separate the
// display scripts without changing the source record or inventing a form.
function pluralDisplay(w){const raw=String(w.plural||'').trim();const m=raw.match(/^(.+?)\s*\(([^()]*[\u0600-\u06ff][^()]*)\)\s*$/);return {word:m?m[1].trim():raw,arabic:w.arabic_plural||(m?m[2].trim():'')};}
function models(words,catalog,events,cards){
 const active=new Map(words.filter(w=>w.active!==false).map(w=>[w.key,w])), consumed=new Set(), rows=[];
 for(const g of catalog?.groups||[]){if(!active.has(g.key))continue;const w=active.get(g.key);const row={...g,name:String(w.house_spelling||g.name).replace(/^ana\s+/i,''),english:w.english,topic:w.topic,added:w.introduced_at||w.doc_added_at||null};for(const k of g.keys||[g.key])if(active.has(k))consumed.add(k);rows.push(row);}
 for(const w of active.values()){if(consumed.has(w.key))continue;const display=pluralDisplay(w),plural=!['—','-','–'].includes(display.word)?display.word:'';rows.push({id:w.key,key:w.key,keys:[w.key],name:w.house_spelling||w.arabizi,arabic:w.arabic,english:w.english,topic:w.topic,type:plural?'Noun':'Word',added:w.introduced_at||w.doc_added_at||null,entries:[{id:w.key+':'+(plural?'singular':'word'),label:plural?'Singular':'Word',word:w.house_spelling||w.arabizi,arabic:w.arabic,keys:[w.key],persons:[]},...(plural?[{id:w.key+':plural',label:'Plural',word:plural,arabic:display.arabic,keys:[],persons:[]}]:[])]});}
 for(const r of rows){r.grammar_only=(r.keys||[r.key]).every(k=>PREPOSITIONS.has(k));if(r.grammar_only)r.type="Grammar";}
 const byKey=new Map(), byId=new Map();
 for(const r of rows){r.entries=r.entries.map(f=>({...f,events:[],observations:[],cardEvents:[]}));for(const f of r.entries){byId.set(f.id,f);for(const k of f.keys||[]){if(!byKey.has(k))byKey.set(k,[]);byKey.get(k).push(f);}}r.unassigned=[];}
 const parents=new Map();for(const r of rows)for(const k of r.keys||[r.key]){if(!parents.has(k))parents.set(k,[]);parents.get(k).push(r);}
 function target(e,lane='speaking'){
  if(e.entry_id&&byId.has(e.entry_id))return byId.get(e.entry_id);
  const parentRows=parents.get(e.word_key)||[];let opts=byKey.get(e.word_key)||[];
  if(e.tense||e.form){opts=parentRows.flatMap(r=>r.entries).filter(f=>f.label.toLowerCase()===String(e.tense||e.form).toLowerCase());return opts.length===1?opts[0]:null;}
  if(lane==='speaking'&&e.text){
   const text=' '+normalize(e.text)+' ';
   const candidates=parentRows.flatMap(r=>r.entries).filter(f=>[f.word,f.arabic,...(f.persons||[]).flatMap(p=>[p.word.replace(/^(Ana|inta|inti|huwwe|heyye|i7na|intu|humme)\s+/i,''),p.arabic.replace(/^(أنا|إنت|إنتي|هو|هي|إحنا|إنتو|هم)\s+/, '')])].some(s=>s&&text.includes(' '+normalize(s)+' ')));
   // A future phrase contains its bare verb too; prefer its full future match.
   const future=candidates.filter(f=>f.label==='Future');
   if(future.length===1)return future[0];
   if(candidates.length===1)return candidates[0];
   if(candidates.length>1)return null;
  }
  // A lexeme key is not evidence of tense: matched inflections can share its
  // canonical present key. Require actual form evidence for spoken verbs.
  if(lane==='speaking'&&parentRows.some(r=>r.type==='Verb')&&e.text)return null;
  if(opts.length===1)return opts[0];return null;
 }
 for(const e of prepareEvidence(events)){
  // The intended retrieval and the word actually uttered can differ. Keep one
  // scored event; separate observations drive Last said, Heard and usage.
  const attempted=e.attempt_target?{...e,...e.attempt_target,entry_id:e.attempt_target.entry_id,tense:e.attempt_target.tense,form:e.attempt_target.form}:e;
  const f=target(attempted),actual=target(e);
  if(e.attempt_target&&actual&&actual!==f&&e.speaker==='Medi'&&points(e)===0)actual.events.push({...e,attempt_target:undefined});
  if(f)f.events.push({...e,use_id:e.use_id||(f.uses||[]).some(u=>u.id===attempted.word_key)?(e.use_id||attempted.word_key):undefined});
  else for(const r of parents.get(attempted.word_key)||[])r.unassigned.push(e);
  if(actual&&Number.isFinite(e.t_start)&&(e.speaker==='Amal'||e.speaker==='Medi'&&e.spoken!==false)){
   actual.observations.push(f&&f!==actual&&!(e.attempt_target&&points(e)===0)?{...e,observation_only:true}:e);
  }
 }
 for(const e of unique(cards)){const f=target(e,'flashcards');if(f)f.cardEvents.push({...e,use_id:e.use_id||(f.uses||[]).some(u=>u.id===e.word_key)?(e.use_id||e.word_key):undefined});}
 for(const r of rows){for(const f of r.entries){f.speaking=score(f.events);f.flashcards=score(f.cardEvents,'flashcards');const exposure=new Set();for(const e of f.observations)if(e.speaker==='Amal'&&!e.immediate_repeat&&!e.is_echo){const sentence=e.sentence_id||e.row_id;if(sentence)exposure.add(date(e)+':'+sentence);}f.heard=exposure.size;f.used=f.observations.length>0;f.uses=(f.uses||[]).map(u=>({...u,speaking:score(f.events.filter(e=>e.use_id===u.id)),flashcards:score(f.cardEvents.filter(e=>e.use_id===u.id),'flashcards')}));}
 const observed=unique(r.entries.flatMap(f=>f.observations).concat(r.unassigned.filter(e=>e.word_key&&(r.keys||[r.key]).includes(e.word_key))));
 r.events=unique(r.entries.flatMap(f=>f.events).concat(r.unassigned,observed));r.last=observed.filter(e=>e.speaker==='Medi'&&e.spoken!==false&&Number.isFinite(e.t_start)).at(-1)||null;r.used=r.entries.filter(f=>f.used).length;
 r.spoke=r.entries.reduce((n,f)=>n+f.speaking.count,0);r.heard=r.entries.reduce((n,f)=>n+f.heard,0);r.cards=r.entries.reduce((n,f)=>n+f.flashcards.count,0);r.search=normalize([r.name,r.arabic,r.english,...(r.keys||[r.key]).flatMap(k=>active.get(k)?.aliases||[]),...r.entries.flatMap(f=>[f.word,f.arabic,...(f.persons||[]).flatMap(p=>[p.word,p.arabic])])].join(' '));}
 return rows;
}
function filter(rows,state){const q=normalize(state.q),topic=new Set(state.topics||[]),statuses=new Set(state.statuses||[]);const statusMatch=f=>(!state.practice||['Wrong','Shaky'].includes(f.speaking.status))&&(!statuses.size||statuses.has(f.speaking.status));const base=rows.filter(r=>(state.usage==='grammar'?r.grammar_only:!r.grammar_only)&&(!q||r.search.includes(q))&&(!topic.size||topic.has(r.topic))&&(!state.newOnly||r.added&&(Date.now()-new Date(r.added))/86400000<7)&&(state.usage!=='none'||r.used===0&&!r.last)&&(state.usage!=='partial'||r.used>0&&r.used<r.entries.length));const counts=Object.fromEntries(Object.keys(WEIGHTS).map(s=>[s,base.flatMap(r=>r.entries).filter(f=>f.speaking.status===s).length]));const visible=base.filter(r=>r.entries.some(statusMatch));
 const strength=(r,high)=>{const vals=r.entries.map(f=>WEIGHTS[f.speaking.status]).filter(v=>v!==null);return vals.length?(high?Math.max(...vals):Math.min(...vals)):null;};
 visible.sort((a,b)=>{let n=0;const recent=()=>time(b.last||{}).localeCompare(time(a.last||{}))||(Number(b.last?.t_start)||0)-(Number(a.last?.t_start)||0);switch(state.sort){case'alpha':n=a.name.localeCompare(b.name);break;case'spoken':n=b.spoke-a.spoke;break;case'new':n=String(b.added||'').localeCompare(String(a.added||''));break;case'weak':case'strong':{const hi=state.sort==='strong',av=strength(a,hi),bv=strength(b,hi);if(av===null&&bv!==null)return 1;if(bv===null&&av!==null)return -1;if(av!==null&&bv!==null)n=hi?bv-av:av-bv;break;}}return n||recent()||a.name.localeCompare(b.name);});return {rows:visible,counts,entries:visible.flatMap(r=>r.entries).filter(statusMatch).length,statusMatch};}
const api={PREPOSITIONS,isGrammar,WEIGHTS,unique,points,score,metrics,models,filter,normalize,date,daysAgo,sentence,prepareEvidence};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesWordBank=api;
})(typeof window!=='undefined'?window:globalThis);
