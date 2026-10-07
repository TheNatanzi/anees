/* Payload of Amal's SHORT level-2 check list (AM-26, Medi 2026-10-06): only the 44 verbs in data/vocab/verb-short-list.json
   where the preposition changes the meaning, is needed, or the ending goes on the verb. One item per verb + preposition,
   same item shape and keys as scripts/verb_addon_payload.cjs (<verb>:addon:<kind>), so pull() and the cards read it unchanged.
   The person label carries the meaning, e.g. "+ 3ala him: pay for something". Printed as JSON. */
const A=require('../docs/js/verb-addons.js'),D=require('../docs/js/verb-drills.js');
const tags=require('../docs/data/verb-addons.json').verbs;A.useTags(tags);
const short=require('../data/vocab/verb-short-list.json');
function build(V,list){
 const byKey=new Map(V.map(v=>[v.verb,v])),items={},verbs=[],missing=[];
 for(const s of list.verbs){
  const v=byKey.get(s.verb),c=v&&(v.tenses.Present||[]).find(c=>c.person==='I');
  if(!c){missing.push(s.verb);continue;}
  const t=tags[s.verb]||{},ids=[];
  for(const a of s.asks){
   const obj='him',f=A.apply(c,{kind:a.k,obj},t.geminate),id=s.verb+':addon:'+a.k;
   const said=a.said==='bi'?'bi / fi':(a.said||a.k),label=a.k==='obj'?'+ ending on the verb (him): '+a.meaning.replace(/\s*\(ending on the verb\)/,''):'+ '+said+' '+obj+': '+a.meaning;
   items[id]={tense:'Level 2',person:label,word:f.arabizi,arabic:f.arabic,kind:s.kind};ids.push(id);
  }
  verbs.push({key:v.verb,name:v.name,arabic:v.arabic||'',english:v.english,ids});
 }
 return {schema_version:1,kind:'verb-addons',short:true,rule:'AM-26',
  what:'44 verbs where the preposition matters (changes the meaning, is needed, or the ending goes on the verb). Same taps as list 1.',
  items,verbs,missing};
}
module.exports={build};
if(require.main===module){
 const V=D.verbs(require('../docs/data/word-bank-catalog.json'),require('../docs/data/words.json').items);
 process.stdout.write(JSON.stringify(build(V,short)));
}
