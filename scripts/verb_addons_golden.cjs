/* Golden check of the level-2 add-on engine against Amal's Quizlet sets. Usage: node scripts/verb_addons_golden.cjs [--misses] */
const A=require('../docs/js/verb-addons.js'),D=require('../docs/js/verb-drills.js');
const cat=require('../docs/data/word-bank-catalog.json'),words=require('../docs/data/words.json').items,sets=require('../docs/data/quizlet/amal-quizlet-sets.json').sets;
const V=D.verbs(cat,words);
const SUBJ={ana:'I',inta:'You (m)',inti:'You (f)',intu:'You (pl)',huwwe:'He',heyye:'She',e7na:'We',i7na:'We',humme:'They'};
const OBJ=[[/\bme\b/i,'me'],[/you \(m\)/i,'you (m)'],[/you \(f\)/i,'you (f)'],[/you \(g\)/i,'you (pl)'],[/\bhim\b|it \(m\)/i,'him'],[/\bher\b|it \(f\)/i,'her'],[/\bus\b/i,'us'],[/\bthem\b/i,'them']];
const strict=s=>String(s).toLowerCase().replace(/\s+/g,' ').trim();
const loose=s=>strict(s).replace(/aa+/g,'a').replace(/ee+|y$/g,'i').replace(/oo+/g,'u').replace(/e/g,'i').replace(/o/g,'u').replace(/(.)\1+/g,'$1').replace(/h$/,'');
const arN=s=>String(s).replace(/[ً-ْ]/g,'').replace(/[أإآ]/g,'ا').replace(/\s+/g,' ').trim();
const lev=(a,b)=>{const d=[...Array(b.length+1).keys()];for(let i=1;i<=a.length;i++){let p=d[0];d[0]=i;for(let j=1;j<=b.length;j++){const t=d[j];d[j]=Math.min(d[j]+1,d[j-1]+1,p+(a[i-1]===b[j-1]?0:1));p=t;}}return d[b.length];};
const base=w=>strict(w).replace(/^b[aeiou]?(t|y|n)?/,'').replace(/[aeiouy]/g,'').slice(0,2);
function golden(){
 const set=sets.find(s=>/pronoun objects? with verbs/i.test(s.title)),out=[];
 for(const [term,en] of set.terms){
  const [z,ar]=term.split('|').map(x=>x.trim()),[pron,form]=[z.split(/\s+/)[0].toLowerCase(),z.split(/\s+/).slice(1).join(' ')],person=SUBJ[pron];
  const tail=en.replace(/^\s*(i|you \((m|f|g)\)|he|she|we|they)\s+/i,'');const obj=(OBJ.map(([re,o])=>{const m=tail.match(new RegExp(re.source,'gi'));return m?[tail.toLowerCase().lastIndexOf(m[m.length-1].toLowerCase()),o]:null;}).filter(Boolean).sort((a,b)=>b[0]-a[0])[0]||[])[1];if(!person||!obj){out.push({term,skip:'unparsed'});continue;}
  let best=null;
  for(const v of V){const c=(v.tenses.Present||[]).find(c=>c.person===person);if(!c)continue;
   const verb=c.arabizi.split(/\s+/).slice(1).join(' ');if(base(verb)!==base(form))continue;
   const gem=V.find(x=>x.verb===v.verb)&&Object.values(v.tenses).flat().some(x=>/([^aeiou])\1/i.test(x.arabizi.split(' ').pop()));
   const got=A.attach(verb,obj,{tense:'Present',person,geminate:gem}),gotAr=A.attachAr(c.arabic.split(' ').slice(1).join(' '),obj);
   const score=(strict(got)===strict(form)?2:loose(got)===loose(form)?1:0),dist=lev(loose(got),loose(form));
   if(!best||score>best.score||(score===best.score&&dist<best.dist))best={verb:v.verb,base:verb,got,gotAr,score,dist,arOk:arN(gotAr)===arN(ar.split(' ').slice(1).join(' '))};}
  out.push({term,en,person,obj,...(best||{skip:'verb not found'})});
 }
 return out;
}
const r=golden(),scored=r.filter(x=>!x.skip);
const report={examples:r.length,matched_verb:scored.length,exact:scored.filter(x=>x.score===2).length,sound_alike:scored.filter(x=>x.score>=1).length,arabic_exact:scored.filter(x=>x.arOk).length};
if(require.main===module){console.log(JSON.stringify(report));if(process.argv.includes('--misses'))for(const x of r)if(x.skip||x.score<2||!x.arOk)console.log(x.skip||'', x.term,'|',x.en,'->',x.got,x.gotAr,'(base',x.base+')');}
module.exports={golden,report};
