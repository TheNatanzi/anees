const assert=require('node:assert/strict'),test=require('node:test');
const C=require('../docs/js/word-bank-core.js');
const catalog=require('../docs/data/word-bank-catalog.json');
test('adjectives retain documented M/F and plural forms in one group',()=>{const cold=catalog.groups.find(g=>g.key==='bAred');assert.equal(cold.type,'Adjective');assert.deepEqual(cold.display_forms.map(f=>f.word),['Baared','Baarda']);assert.deepEqual(cold.entries[0].keys,['bAred','bArda']);const happy=catalog.groups.find(g=>g.name==='Mabsoo6');assert(happy.display_forms.some(f=>f.person==='Feminine'&&f.word==='Mabsoo6a'));assert(happy.entries.some(f=>f.label==='Plural'&&f.word==='Mabsoo6een'));const hot=catalog.groups.find(g=>g.name==='Su5un');assert.deepEqual(hot.display_forms.map(f=>f.word),['Su5un','Su5na']);});
const events=(pts,days=[])=>pts.map((p,i)=>({id:String(i),speaker:'Medi',lesson_date:days[i]||'2026-09-01',t_start:i,vocab_points:p}));
test('starting rules and partial score',()=>{assert.equal(C.score([]).status,'Untested');assert.equal(C.score(events([1])).status,'Good');assert.equal(C.score(events([.5])).status,'Shaky');assert.equal(C.score(events([0,0])).status,'Wrong');for(const p of [0,.5])assert.equal(C.score(events([1,p])).status,'Shaky');});
test('mastery uses latest consecutive successes across lessons',()=>{assert.equal(C.score(events([1,1])).status,'Good');assert.equal(C.score(events([1,1,1],['2026-09-01','2026-09-01','2026-09-02'])).status,'Mastered');});
test('promotion resets and half points break streaks',()=>{assert.equal(C.score(events([0,0,1,1])).status,'Shaky');assert.equal(C.score(events([0,0,1,1,1,1])).status,'Good');assert.equal(C.score(events([0,.5,1,.5,1])).status,'Shaky');});
test('demotion and null neutrality',()=>{assert.equal(C.score(events([1,1,0],['2026-09-01','2026-09-02','2026-09-02'])).status,'Good');const a=events([0,0,1,0,1]);a[3].grammar_only=true;assert.equal(C.score(a).status,'Shaky');assert.equal(C.score(a).count,4);});
test('tenth attempt switches entirely to rolling window',()=>{const a=events([1,1,1,1,1,1,1,1,1,0],Array(10).fill('2026-09-01').map((d,i)=>i<5?d:'2026-09-02'));assert.equal(C.score(a).status,'Mastered');assert.equal(C.score(a).accuracy,90);a.push(...events([0,0,0]).map((e,i)=>({...e,id:'later'+i,lesson_date:'2026-09-03'})));assert.equal(C.score(a).status,'Shaky');});
test('latest ten mastery requires lessons inside window',()=>{assert.equal(C.score(events(Array(10).fill(1))).status,'Good');const a=events(Array(11).fill(1));a[0].lesson_date='2026-08-01';assert.equal(C.score(a).status,'Good');});
test('thresholds include half points',()=>{for(const [points,status] of [[9,'Mastered'],[7.5,'Good'],[5,'Shaky'],[4.5,'Wrong']]){const values=Array.from({length:10},(_,i)=>Math.max(0,Math.min(1,points-i)));assert.equal(C.score(events(values,values.map((_,i)=>i%2?'2026-09-02':'2026-09-01'))).status,status);}});
test('grammar, echoes, missing text evidence do not score; mixed can',()=>{for(const flag of ['grammar_only','immediate_repeat','ignored'])assert.equal(C.points({...events([0])[0],[flag]:true}),null);assert.equal(C.points({...events([0])[0],speaker:'Amal'}),null);assert.equal(C.points({id:'x',speaker:'Medi',assessment:'incorrect',lesson_date:'2026-09-01'}),null);assert.equal(C.points({id:'x',speaker:'Medi',assessment:'incorrect',classification:'mixed',correction:true,lesson_date:'2026-09-01',t_start:1}),0);});
test('duplicate/revised event updates original once',()=>{const a=events([0]);const corrected={...a[0],vocab_points:1};assert.equal(C.score([...a,corrected]).count,1);assert.equal(C.score([...a,corrected]).status,'Good');});
test('flashcards have separate days and retries earn half',()=>{const cards=[{id:'a',result:'got',attempt:1,ts:'2026-09-01T09:00:00Z'},{id:'b',result:'got',attempt:1,ts:'2026-09-02T09:00:00Z'}];assert.equal(C.score(cards,'flashcards').status,'Mastered');assert.equal(C.score(cards).status,'Untested');assert.equal(C.points({...cards[0],attempt:2},'flashcards'),.5);});
test('noun singular and plural map independently with parent counts',()=>{const words=[{key:'book',arabizi:'Kitaab',arabic:'كتاب',english:'Book',plural:'Kutub',topic:'Learning'}];const ev=events([1,.5]).map((e,i)=>({...e,word_key:'book',text:i?'Kutub':'Kitaab'}));const rows=C.models(words,{},ev,[]);assert.equal(rows[0].entries[0].speaking.status,'Good');assert.equal(rows[0].entries[1].speaking.status,'Shaky');assert.equal(rows[0].spoke,2);assert.equal(rows[0].cards,0);});
test('explicit form attribution resolves generated tense and partial use',()=>{const word={key:'speak',arabizi:'Ba7ki',english:'I speak',topic:'Verbs'};const catalog={groups:[{id:'speak',key:'speak',keys:['speak'],name:'Ba7ki',type:'Verb',entries:['Past','Present','Future','Command'].map(label=>({id:label,label,word:label,keys:label==='Present'?['speak']:[]}))}]};const rows=C.models([word],catalog,[{...events([1])[0],word_key:'speak',tense:'Future'}],[]);assert.equal(rows[0].entries[2].speaking.status,'Good');assert.equal(C.filter(rows,{usage:'partial',sort:'recent'}).rows.length,1);assert.equal(C.filter(rows,{usage:'none'}).rows.length,0);});
test('inactive vocabulary excluded, scores recompute after corrected attempt',()=>{const w={key:'x',arabizi:'x',english:'x',topic:'x',active:false};assert.equal(C.models([w],{},events([1]),[]).length,0);});
test('metrics are unique, status-weighted, null cannot qualify recent cohort',()=>{const fs=['Wrong','Shaky','Good','Mastered'].map(status=>({speaking:{status,attempts:[{lesson_date:'2026-09-15'}]},flashcards:{status:'Untested',attempts:[]}}));const m=C.metrics(fs,new Date('2026-09-17'));assert.equal(m.accuracy,57.5);assert.equal(m.recent,4);assert.equal(m.known,2);assert.equal(m.cards,null);});
test('OR within filters, AND between groups; noun sorting; Arabic search',()=>{const words=[{key:'a',arabizi:'Kitaab',arabic:'كتاب',english:'Book',plural:'Kutub',topic:'Learning'},{key:'b',arabizi:'Ta3aam',arabic:'طعام',english:'Food',topic:'Food'}];const rows=C.models(words,{},[{...events([0])[0],word_key:'a'}],[]);assert.equal(C.filter(rows,{q:'كِتاب',topics:['Learning'],statuses:['Wrong','Shaky']}).rows.length,1);assert.equal(C.filter(rows,{q:'كتاب',topics:['Food'],statuses:['Shaky']}).rows.length,0);assert.equal(C.filter(rows,{sort:'strong'}).rows.at(-1).key,'b');});
test('equal source key across two tenses stays unassigned',()=>{const w={key:'x',arabizi:'X',topic:'Verb'};const cat={groups:[{id:'x',key:'x',keys:['x'],name:'X',type:'Verb',entries:[{id:'p',label:'Past',keys:['x']},{id:'n',label:'Present',keys:['x']}]}]};const row=C.models([w],cat,[{...events([1])[0],word_key:'x'}],[])[0];assert.equal(row.spoke,0);assert.equal(row.unassigned.length,1);});

test('pending transcript review overrides an old numeric vocabulary grade',()=>{
 for(const pending of [{needs_review:true},{wording_status:'unresolved'},{assessment:'unresolved'}]){
  const e={...events([1])[0],...pending};assert.equal(C.points(e),null);assert.equal(C.score([e]).count,0);
 }
});
test('legacy helped echoes are ignored but new sentence production earns partial credit',()=>{
 const context=[{row_id:'a',speaker:'Amal',text:'Baared',timeline_start:1,timeline_end:2},{row_id:'m',speaker:'Medi',text:'Baared',timeline_start:3,timeline_end:4}];
 const e={id:'echo',speaker:'Medi',lesson_date:'2026-09-10',word_key:'cold',t_start:3,row_id:'m',text:'Baared',assessment:'helped',context};
 const [echo]=C.prepareEvidence([e]);assert.equal(C.points(echo),null);assert.equal(e.immediate_repeat,undefined,'raw source stays unchanged');
 const fresh={...e,context:[context[0],{...context[1],text:'El jaw baared el yom'}]};assert.equal(C.points(C.prepareEvidence([fresh])[0]),.5);
 const r=C.models([{key:'cold',arabizi:'Baared',english:'Cold'}],{},[e],[])[0];assert.equal(r.spoke,0);assert.equal(r.events.length,1,'retain history');
});
test('history selects the full learner sentence and preserves explicit original wording',()=>{
 const e={speaker:'Medi',row_id:'r',text:'Baared',context:[{speaker:'Amal',row_id:'other',text:'Other sentence'},{speaker:'Medi',row_id:'r',text:'El jaw baared',original_text:'El jaw baarda'}]};
 assert.equal(C.sentence(e),'El jaw baarda');assert.equal(C.sentence({...e,context:[]}),'Baared');
});

test('source tenses survive English inflection and internal Arabizi alternatives',()=>{
 const draw=catalog.groups.find(g=>g.key==='ana barsem');assert.equal(draw.entries[0].word,'rasamet');assert.equal(draw.entries[0].provenance,'document');
 const think=catalog.groups.find(g=>g.key==='ana bafaker');assert.equal(think.entries[0].word,'fakkaret');assert.equal(think.entries[0].provenance,'inferred');
 const fight=catalog.groups.find(g=>g.name==='baqaatel');assert(fight);assert.equal(fight.entries[2].word,'ra7 aqaatel');
 const meet=catalog.groups.find(g=>g.name==='balte2i');assert(meet);assert.equal(meet.entries[2].word,'ra7 alte2i');
});

test('Last said and default recency use only actual Medi speech; Heard stays independent',()=>{
 const words=[{key:'a',arabizi:'A'},{key:'b',arabizi:'B'},{key:'c',arabizi:'C'}];
 const ev=[
  {id:'a1',word_key:'a',speaker:'Medi',lesson_date:'2026-09-01',t_start:1,spoken:true,assessment:'independent'},
  {id:'b1',word_key:'b',speaker:'Medi',lesson_date:'2026-09-02',t_start:2,spoken:true,grammar_only:true},
  {id:'a2',word_key:'a',speaker:'Amal',lesson_date:'2026-09-03',t_start:3,row_id:'teacher'},
  {id:'a3',word_key:'a',speaker:'Medi',lesson_date:'2026-09-04',t_start:4,spoken:false,assessment:'recall_failure'},
  {id:'c1',word_key:'c',speaker:'Amal',lesson_date:'2026-09-05',t_start:5,row_id:'teacher2'}];
 const rows=C.models(words,{},ev,[]),a=rows.find(r=>r.key==='a'),b=rows.find(r=>r.key==='b'),c=rows.find(r=>r.key==='c');
 assert.equal(a.last.id,'a1');assert.equal(a.heard,1);assert.equal(c.last,null);assert.equal(c.heard,1);
 assert.equal(b.last.id,'b1');assert.equal(b.spoke,0,'grammar-only use can be last said without scoring');
 assert.deepEqual(C.filter(rows,{sort:'recent'}).rows.map(r=>r.key),['b','a','c']);
});
test('an unvocalized homograph goes to the Doc form, never to an engine guess',()=>{
 const word={key:'happy',arabizi:'Banbese6',arabic:'بنبسط',english:'I get happy',topic:'Verbs'};
 const catalog={groups:[{id:'happy',key:'happy',keys:['happy'],name:'Banbese6',type:'Verb',entries:[
  {id:'happy:past',label:'Past',word:'inbasa6',arabic:'انبسطت',keys:[],persons:[{person:'He',word:'huwwe inbasa6',arabic:'هو انبسط',provenance:'inferred',checked:false}]},
  {id:'happy:command',label:'Command',word:'Enbese6',arabic:'انبسط',keys:['happy'],provenance:'document',persons:[{person:'You (m)',word:'Enbese6',arabic:'انبسط',provenance:'document'}]}]}]};
 const said={...events([1])[0],word_key:'happy',text:'انبسط.'};
 const rows=C.models([word],catalog,[said],[]);
 assert.equal(rows[0].entries[1].speaking.count,1,'command (Doc) gets the attempt');
 assert.equal(rows[0].entries[0].speaking.count,0,'guessed past does not');
 // two guesses tie: nobody gets it (held, not guessed)
 catalog.groups[0].entries[1].persons[0].provenance='inferred';catalog.groups[0].entries[1].provenance='inferred';
 const tie=C.models([word],catalog,[said],[]);assert.equal(tie[0].entries.reduce((n,f)=>n+f.speaking.count,0),0);
});
