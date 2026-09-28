/* Names & places layer, browser twin of scripts/names.py (Medi 2026-09-28: "yes"). Proper names are recognised before
   any word matching, longest match first: "Bait La7em", "بيت لحم", "رام الله", "رام Allah" are each ONE place.
   Same data (data/names.json), same normalisation, same results as Python: tests/test_names_parity.cjs checks both on
   one fixture. People are stored only as salted SHA-256 fingerprints; this file hashes each candidate (sync SHA-256
   below) and never shows a fingerprint - a person's name is shown as said, with a "(person)" chip.
   API (window.AneesNames, also module.exports for node):
     load(url?) -> Promise<matcher>      create(data) -> matcher {find(text), mask(text)}      fp(key)
     markup(text, matcher, esc?) -> HTML with every name wrapped in a chip: "رام الله · Ramallah (place)"
     chipText(span) -> the chip label       css() -> injects the chip style once (pages need no extra stylesheet) */
(function(root){
'use strict';
if(root&&root.AneesNames)return;   // loaded twice (tabs + a module): keep the first
const SALT='anees-names-v1|2026-09-28|public-salt';
const MAXN=4;
const TOKEN=/[ء-غـ-ٰٟ-ۓ]+|[A-Za-z0-9À-ɏ'’]+/g;
const AR_TEST=/[ء-غف-يٱ-ۓ]/;
const MARKS=/[ً-ٰٟـ]/g, MARK1=/^[ً-ٰٟـ]$/;
const LAT_MARKS=/[̀-ͯ]/g;
const GAP_OK=/^[\s\-ـ]*$/;
const LAT_ART=new Set(['il','el','al','l','ul']);
const AR_PREFIXES=['وبال','وفال','ولل','وال','بال','فال','عال','لل','وب','ول','وف','و','ب','ل','ف'];
const PERSON_PREFIXES=['و','ل'];
const AR_MAP=[['أ','ا'],['إ','ا'],['آ','ا'],['ٱ','ا'],['ة','ه'],['ى','ي'],['ؤ','و'],['ئ','ي'],['ء',''],['ک','ك'],['ی','ي'],['ۀ','ه']];

function arNorm(s){s=String(s||'').replace(MARKS,'');for(const [a,b] of AR_MAP)s=s.split(a).join(b);return s;}
function latNorm(s){return String(s||'').normalize('NFKD').replace(LAT_MARKS,'').toLowerCase().replace(/['’ʼ`]/g,'');}
const isAr=t=>AR_TEST.test(t||'');
function tokens(text){const out=[];text=String(text||'');TOKEN.lastIndex=0;let m;while((m=TOKEN.exec(text)))out.push([m.index,m.index+m[0].length,m[0],isAr(m[0])?'ar':'lat']);return out;}
const normTok=(raw,sc)=>sc==='ar'?arNorm(raw):latNorm(raw);
function variantKey(v){const out=[];for(const [,,raw,sc] of tokens(v)){const n=normTok(raw,sc);if(!n||(sc==='lat'&&LAT_ART.has(n)))continue;out.push(n);}return out;}
function variantScripts(v){return tokens(v).filter(t=>!(t[3]==='lat'&&LAT_ART.has(latNorm(t[2])))).map(t=>t[3]);}
function arForms(n){
 const out=[[n,0]];
 for(const p of AR_PREFIXES){
  if(n.startsWith(p)&&n.length-p.length>=2){
   const rest=n.slice(p.length);
   if(p.endsWith('ال'))out.push(['ال'+rest,p.length-2]);
   else if(p.endsWith('لل'))out.push(['ال'+rest,p.length-1]);
   else out.push([rest,p.length]);
  }
 }
 return out;
}
function rawOffset(raw,k){
 if(k<=0)return 0;let seen=0;const cs=[...raw];let pos=0;
 for(let i=0;i<cs.length;i++){const ch=cs[i];if(MARK1.test(ch)){pos+=ch.length;continue;}seen++;pos+=ch.length;
  if(seen===k){let j=i+1;while(j<cs.length&&MARK1.test(cs[j])){pos+=cs[j].length;j++;}return pos;}}
 return raw.length;
}
const isUpper=ch=>!!ch&&ch===ch.toUpperCase()&&ch!==ch.toLowerCase();

/* ---------- SHA-256 (sync, UTF-8) ---------- */
const K=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
function sha256hex(str){
 const bytes=new TextEncoder().encode(str),l=bytes.length,n=((l+9+63)>>6)<<6,m=new Uint8Array(n);m.set(bytes);m[l]=0x80;
 const bits=l*8;for(let i=0;i<8;i++)m[n-1-i]=Math.floor(bits/Math.pow(2,8*i))&255;
 const H=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]),W=new Uint32Array(64);
 const r=(x,k)=>(x>>>k)|(x<<(32-k));
 for(let o=0;o<n;o+=64){
  for(let i=0;i<16;i++)W[i]=(m[o+4*i]<<24)|(m[o+4*i+1]<<16)|(m[o+4*i+2]<<8)|m[o+4*i+3];
  for(let i=16;i<64;i++){const s0=r(W[i-15],7)^r(W[i-15],18)^(W[i-15]>>>3),s1=r(W[i-2],17)^r(W[i-2],19)^(W[i-2]>>>10);W[i]=(W[i-16]+s0+W[i-7]+s1)>>>0;}
  let [a,b,c,d,e,f,g,h]=H;
  for(let i=0;i<64;i++){const S1=r(e,6)^r(e,11)^r(e,25),ch=(e&f)^(~e&g),t1=(h+S1+ch+K[i]+W[i])>>>0,S0=r(a,2)^r(a,13)^r(a,22),mj=(a&b)^(a&c)^(b&c),t2=(S0+mj)>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}
  H[0]+=a;H[1]+=b;H[2]+=c;H[3]+=d;H[4]+=e;H[5]+=f;H[6]+=g;H[7]+=h;
 }
 return [...H].map(x=>x.toString(16).padStart(8,'0')).join('');
}
function fp(key){if(typeof key==='string')key=variantKey(key);return sha256hex(SALT+'|'+key.join(' ')).slice(0,32);}

/* ---------- matcher ---------- */
function create(data){
 const entries=(data&&data.entries)||[],index=new Map(),people=new Set(((data&&data.people)||[]).map(p=>p.fp));
 const kk=k=>k.join('\u0001');
 const add=(key,ei,flag)=>{if(!key.length||key.length>MAXN)return;const s=kk(key),cur=index.get(s);if(cur===undefined)index.set(s,[ei,flag]);else if(cur[0]===ei&&flag<cur[1])index.set(s,[ei,flag]);};
 entries.forEach((e,ei)=>{
  for(const v of e.v||[])add(variantKey(v),ei,0);
  for(const v of e.cap||[])add(variantKey(v),ei,(v.toUpperCase()===v&&/[A-Z]/.test(v))?2:1);
  const ars=(e.v||[]).filter(v=>variantScripts(v).every(s=>s==='ar')).map(variantKey);
  const lats=(e.v||[]).filter(v=>variantScripts(v).every(s=>s==='lat')).map(variantKey);
  for(const a of ars)for(const l of lats){
   if(a.length!==l.length||a.length<2||a.length>3)continue;
   const n=a.length;
   for(let code=0;code<(1<<n);code++){
    const pick=[];for(let i=0;i<n;i++)pick.push((code>>(n-1-i))&1);   // itertools.product((0,1), repeat=n) order
    const sum=pick.reduce((x,y)=>x+y,0);if(sum>0&&sum<n)add(pick.map((p,i)=>p?l[i]:a[i]),ei,0);
   }
  }
 });
 function caseOk(flag,raws){
  if(flag===0)return true;
  for(const [raw,sc] of raws){if(sc!=='lat')continue;const letters=raw.replace(/[^A-Za-zÀ-ɏ]/g,'');if(!letters)continue;
   if(flag===2&&letters.toUpperCase()!==letters)return false;if(flag===1&&!isUpper(letters[0]))return false;}
  return true;
 }
 function adjacent(text,toks,idxs){
  for(let q=0;q+1<idxs.length;q++){const a=idxs[q],b=idxs[q+1];
   for(let j=a;j<b;j++)if(!GAP_OK.test(text.slice(toks[j][1],toks[j+1][0])))return false;
   for(let j=a+1;j<b;j++)if(!(toks[j][3]==='lat'&&LAT_ART.has(latNorm(toks[j][2]))))return false;}
  return true;
 }
 function find(text){
  text=String(text||'');const toks=tokens(text),content=[],norms={};
  toks.forEach((t,i)=>{if(!(t[3]==='lat'&&LAT_ART.has(latNorm(t[2])))){content.push(i);norms[i]=normTok(t[2],t[3]);}});
  const out=[];let p=0;
  while(p<content.length){
   let best=null;
   for(let n=Math.min(MAXN,content.length-p);n>=1;n--){
    const idxs=content.slice(p,p+n);if(!adjacent(text,toks,idxs))continue;
    const first=toks[idxs[0]],rest=idxs.slice(1).map(i=>norms[i]);
    const forms=first[3]==='ar'?arForms(norms[idxs[0]]):[[norms[idxs[0]],0]];
    const raws=idxs.map(i=>[toks[i][2],toks[i][3]]);
    for(const [form,k] of forms){const hit=index.get(kk([form,...rest]));if(hit&&caseOk(hit[1],raws)){best=[n,'entry',hit[0],k];break;}}
    if(best)break;
    if(n<=3&&people.size&&raws.every(([raw,sc])=>sc==='ar'||isUpper(raw[0]))){
     const pforms=forms.filter(([f,k])=>k===0||(k===1&&PERSON_PREFIXES.includes(norms[idxs[0]][0])));
     for(const [form,k] of pforms)if(people.has(fp([form,...rest]))){best=[n,'person',null,k];break;}
    }
    if(best)break;
   }
   if(!best){p++;continue;}
   const [n,what,ei,k]=best,idxs=content.slice(p,p+n),first=toks[idxs[0]];
   let s=first[0]+(first[3]==='ar'?rawOffset(first[2],k):0);const e=toks[idxs[idxs.length-1]][1];
   if(k===0&&first[3]==='lat'&&idxs[0]>0){
    const j=idxs[0]-1,pt=toks[j];
    if(pt[3]==='lat'&&LAT_ART.has(latNorm(pt[2]))&&GAP_OK.test(text.slice(pt[1],first[0]))&&
       (j===0||!(toks[j-1][3]==='lat'&&toks[j-1][1]===pt[0]-1&&text[pt[0]-1]==='-')))s=pt[0];
   }
   const sp={s,e,text:text.slice(s,e)};
   if(what==='entry'){const en=entries[ei];sp.kind=en.kind;sp.id=en.id;sp.en=en.en==null?null:en.en;sp.ar=en.ar==null?null:en.ar;if(en.sub)sp.sub=en.sub;}
   else sp.kind='person';
   if(new Set(idxs.map(i=>toks[i][3])).size>1)sp.mixed=true;
   out.push(sp);p+=n;
  }
  return out;
 }
 function mask(text,repl){repl=repl||'فلان';const spans=find(text).filter(sp=>isAr(sp.text));if(!spans.length)return [text,[]];let out='',last=0;const back=[];for(const sp of spans){out+=text.slice(last,sp.s)+repl;back.push(sp.text);last=sp.e;}return [out+text.slice(last),back];}
 return {find,mask,entries,size:index.size};
}

/* ---------- display ---------- */
const escHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function chipText(sp){
 if(sp.kind==='person')return '(person)';
 const what=sp.kind==='country'?(sp.sub==='nationality'?'nationality':'country'):sp.kind==='place'?'place':'name';
 const en=sp.en||'',ar=sp.ar&&arNorm(sp.ar)!==arNorm(sp.text)?sp.ar:'';
 return (ar?ar+' · ':'')+(en?en+' ':'')+'('+what+')';
}
function markup(text,m,esc){
 esc=esc||escHtml;text=String(text??'');if(!m)return esc(text);
 const spans=m.find(text);if(!spans.length)return esc(text);
 let out='',last=0;
 for(const sp of spans){out+=esc(text.slice(last,sp.s))+`<span class="nm-name nm-${sp.kind}" title="A name, not a word: never scored">${esc(sp.text)}<span class="nm-chip" dir="auto">${esc(chipText(sp))}</span></span>`;last=sp.e;}
 return out+esc(text.slice(last));
}
// Arabizi line (S1: Amal's spelling on top): every non-name piece goes through az(piece); a name stays a name, shown as
// said (Arabic script or English) with its chip - never spelled word by word ("Bait La7em" = house + meat).
function azLine(text,m,az,esc){
 esc=esc||escHtml;text=String(text??'');const spans=m?m.find(text):[];
 const conv=seg=>{if(!seg)return '';let r=null;try{r=az?az(seg):null;}catch(e){r=null;}return esc(r==null?seg:r);};
 if(!spans.length)return conv(text);
 let out='',last=0;
 for(const sp of spans){out+=conv(text.slice(last,sp.s))+nameHtml(sp,esc);last=sp.e;}
 return out+conv(text.slice(last));
}
const nameHtml=(sp,esc)=>`<span class="nm-name nm-${sp.kind}" title="A name, not a word: never scored">${esc(sp.text)}<span class="nm-chip" dir="auto">${esc(chipText(sp))}</span></span>`;
// DOM version for pages that build nodes: wraps names found inside each text node (skips text already inside a name).
function nameEl(sp){const w=document.createElement('span');w.className='nm-name nm-'+sp.kind;w.title='A name, not a word: never scored';w.append(sp.text);const c=document.createElement('span');c.className='nm-chip';c.dir='auto';c.textContent=chipText(sp);w.append(c);return w;}
function decorate(rootEl,m){
 if(!m||!rootEl||typeof document==='undefined')return rootEl;
 const walk=document.createTreeWalker(rootEl,NodeFilter.SHOW_TEXT,null),nodes=[];let t;while((t=walk.nextNode()))nodes.push(t);
 for(const node of nodes){
  if(inName(node))continue;
  const text=node.nodeValue,spans=m.find(text);if(!spans.length)continue;
  const frag=document.createDocumentFragment();let last=0;
  for(const sp of spans){if(sp.s>last)frag.append(text.slice(last,sp.s));frag.append(nameEl(sp));last=sp.e;}
  if(last<text.length)frag.append(text.slice(last));
  node.parentNode.replaceChild(frag,node);
 }
 return rootEl;
}
const inName=node=>{const p=node&&node.parentNode;return !!(p&&p.closest&&p.closest('.nm-name'));};
function css(){
 if(typeof document==='undefined'||document.getElementById('nm-style'))return;
 const st=document.createElement('style');st.id='nm-style';
 st.textContent='.nm-name{border-bottom:1px dotted currentColor;unicode-bidi:isolate}.nm-chip{display:inline-block;margin-inline-start:.3em;padding:0 .4em;border-radius:.6em;font-size:.72em;line-height:1.5;vertical-align:.1em;background:var(--ab-raised,rgba(127,127,127,.14));color:var(--ab-muted,inherit);border:1px solid var(--ab-line,rgba(127,127,127,.3));white-space:nowrap;unicode-bidi:isolate;font-family:var(--sabz-font-sans,inherit)}';
 document.head.append(st);
}
let loading=null;
function load(url){
 if(!loading)loading=fetch(url||'data/names.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(Error('names.json '+r.status))).then(d=>{const m=create(d);api.matcher=m;css();return m;});
 loading.catch(()=>{loading=null;});
 return loading;
}
const api={load,create,fp,markup,azLine,decorate,inName,chipText,css,arNorm,latNorm,tokens,sha256hex,matcher:null,SALT};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
if(root)root.AneesNames=api;
})(typeof window!=='undefined'?window:null);
