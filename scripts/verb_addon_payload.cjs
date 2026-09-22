/* Payload of Amal's level-2 check list (kind 'verb-addons'): per verb, its present "I" form with each tagged add-on.
   Printed as JSON; scripts/verb_check_links.py create-addons stores it. */
const A=require('../docs/js/verb-addons.js'),D=require('../docs/js/verb-drills.js');
const tags=require('../docs/data/verb-addons.json').verbs;A.useTags(tags);
const V=D.verbs(require('../docs/data/word-bank-catalog.json'),require('../docs/data/words.json').items);
const items={},verbs=[],PICK={obj:'him',ma3:'them',la:'her',fi:'it',min:'him','3ala':'her','3an':'them'};
for(const v of V){const c=(v.tenses.Present||[]).find(c=>c.person==='I');if(!c)continue;const t=tags[v.verb]||{},ids=[];
 const kinds=(t.object?['obj']:[]).concat(t.preps||[]);
 for(const k of kinds){const obj=PICK[k]==='it'?'him':PICK[k],a=A.apply(c,{kind:k,obj},t.geminate),id=v.verb+':addon:'+k;
  items[id]={tense:'Level 2',person:k==='obj'?'+ '+obj+' (ending on the verb)':'+ '+A.PREP[k].en+' '+obj+' ('+k+')',word:a.arabizi,arabic:a.arabic};ids.push(id);}
 if(ids.length)verbs.push({key:v.verb,name:v.name,arabic:v.arabic||'',english:v.english,ids});}
process.stdout.write(JSON.stringify({schema_version:1,kind:'verb-addons',items,verbs}));
