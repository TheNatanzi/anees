/* Level-2 verb tags -> docs/data/verb-addons.json: {verb id: {object, preps, geminate, source}}.
   Seeds: Amal's Quizlet "verb + preposition collocations" and "Pronoun Objects With Verbs" (source 'amal-quizlet');
   every other verb is tagged by rule (source 'claude'). Every verb gets ma3 + la (spec ruling 4). Amal's check answers
   (data/vocab/amal_addon_checks.json, when present) win over both. Usage: node scripts/build_verb_addon_tags.cjs */
const fs=require('fs'),path=require('path'),root=path.resolve(__dirname,'..');
const D=require('../docs/js/verb-drills.js');
const cat=require('../docs/data/word-bank-catalog.json'),words=require('../docs/data/words.json').items,sets=require('../docs/data/quizlet/amal-quizlet-sets.json').sets;
const V=D.verbs(cat,words);
const skel=w=>String(w).toLowerCase().replace(/^(ana|inta|inti|huwwe|heyye|humme|intu|i7na|e7na)\s+/,'').replace(/^b[aeiou]?(t|y|n)?/,'').replace(/[^a-z0-9]/g,'').replace(/[aeiouy]/g,'');
const INTRANS=/^(go|come|sleep|sit|wake|walk|shower|get up|travel|laugh|cry|stay|arrive|return|live|swim|fly|run|smile|be |get |worry|rest|dance|hurry|wait)\b/;
const bySkel=new Map();for(const v of V){const k=skel(v.name);if(!bySkel.has(k))bySkel.set(k,[]);bySkel.get(k).push(v);}
const nm=w=>String(w).toLowerCase().replace(/^v/,'b').replace(/aa/g,'a').replace(/ee/g,'i').replace(/oo/g,'u').replace(/[^a-z0-9]/g,'');
const find=w=>{const exact=V.filter(v=>nm(v.name)===nm(w)||nm(v.name).startsWith(nm(w))&&nm(w).length>=5);if(exact.length===1)return exact[0];const k=skel(w.replace(/^v/i,'b'));for(let n=k.length;n>=2;n--){const hit=[...bySkel.entries()].filter(([s])=>s.slice(0,n)===k.slice(0,n));if(hit.length===1&&hit[0][1].length===1)return hit[0][1][0];}return null;};
const tags={},seen={};
const set=(t)=>sets.find(s=>t.test(s.title||''));
const PREPS=[['ma3',/\bma3\b/],['la',/\bla-?(?=\s|\)|$|\/)/],['fi',/\bfi\b/],['3ala',/\b3ala\b/],['min',/\bmin\b/],['3an',/\b3an\b/]];
const unmatched=[];
for(const [term] of (set(/verb\s*\+\s*preposition/i)||{terms:[]}).terms){
 const z=term.split('|')[0].trim(),m=z.match(/^(?:ana\s+)?(\S+(?:\s+baali)?)\s*(.*)$/i),v=m&&find(m[1]);if(!v){unmatched.push(z);continue;}
 const t=tags[v.verb]=tags[v.verb]||{object:false,preps:[],source:'amal-quizlet'};
 if(/\(x\)/i.test(m[2]))t.object=true;
 for(const [p,re] of PREPS)if(re.test(m[2].toLowerCase())&&!t.preps.includes(p))t.preps.push(p);
}
for(const [term] of (set(/pronoun objects? with verbs/i)||{terms:[]}).terms){const z=term.split('|')[0].trim().split(/\s+/)[1],v=find(z);if(v){const t=tags[v.verb]=tags[v.verb]||{object:false,preps:[],source:'amal-quizlet'};t.object=true;}else unmatched.push(z);}
const checks=path.join(root,'data/vocab/amal_addon_checks.json'),amal=fs.existsSync(checks)?JSON.parse(fs.readFileSync(checks,'utf8')):{};
const out={};
for(const v of V){
 const base=D.base(v.english),t=tags[v.verb];
 const forms=Object.values(v.tenses).flat().map(c=>c.arabizi.split(/\s+/).pop().toLowerCase());
 const phrase=/\s/.test(String(v.name).trim());   // verb + noun: prepositions only
 out[v.verb]={object:!phrase&&(t&&t.object?true:!INTRANS.test(base)),preps:[...new Set(['ma3','la',...((t&&t.preps)||[])])],
  geminate:forms.some(f=>/([^aeiou0-9])\1/.test(f.slice(-3))),source:t?'amal-quizlet':'claude',english:v.english,name:v.name,};
 const a=amal[v.verb];if(a){if('object' in a)out[v.verb].object=a.object;out[v.verb].preps=out[v.verb].preps.filter(p=>!(a.preps_off||[]).includes(p));if(a.forms)out[v.verb].amal_forms=a.forms;}
 if(amal[v.verb])out[v.verb].source='amal';
}
fs.writeFileSync(path.join(root,'docs/data/verb-addons.json'),JSON.stringify({version:'2026-09-23',rules:'every verb: ma3 + la; object endings when the verb takes an object; Amal wins',verbs:out},null,1)+'\n');
const n=Object.values(out);console.log(JSON.stringify({verbs:n.length,from_amal_quizlet:n.filter(x=>x.source==='amal-quizlet').length,object:n.filter(x=>x.object).length,geminate:n.filter(x=>x.geminate).length,extra_preps:n.filter(x=>x.preps.length>2).length,unmatched}));
