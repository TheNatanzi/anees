// PG-38 (Medi 2026-10-08 on the 10-08 lesson, tutor line 00:15 "Ahla. [tasfeer Fi el-5alfiyye] [tas3ile] keefak?":
// "whjat does [tasfeer Fi el-5alfiyye] [tas3ile] why is this here"; 2026-10-09 "ok do it"): the engine's bracketed sound
// tags render as a small grey English note, never as Arabizi, never as a word. Display only (S2).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const S=require('../docs/js/sound-tags.js');
const A=require('../docs/js/word-bank-arabizi.js');
const DOCS=path.join(__dirname,'..','docs');

// a tiny DOM: enough for decorate() (text nodes, elements, fragments, classList, dataset)
function mk(){
 const doc={};
 function node(type,props){return Object.assign({nodeType:type,parentNode:null,childNodes:[]},props);}
 function append(p,c){if(c.nodeType===11){c.childNodes.slice().forEach(x=>append(p,x));c.childNodes=[];return c;}c.parentNode=p;p.childNodes.push(c);return c;}
 function el(tag){const e=node(1,{tagName:tag,attrs:{},dataset:{},className:'',_text:null});
  e.classList={contains:c=>(' '+e.className+' ').includes(' '+c+' ')};
  e.setAttribute=(k,v)=>{e.attrs[k]=v;};e.appendChild=c=>append(e,c);
  e.replaceChild=(n,o)=>{const i=e.childNodes.indexOf(o);const kids=n.nodeType===11?n.childNodes.slice():[n];if(n.nodeType===11)n.childNodes=[];kids.forEach(k=>k.parentNode=e);e.childNodes.splice(i,1,...kids);};
  Object.defineProperty(e,'textContent',{get(){return e.childNodes.map(c=>c.nodeType===3?c.nodeValue:c.textContent).join('');},set(v){e.childNodes=[];append(e,doc.createTextNode(v));}});
  return e;}
 doc.createElement=el;
 doc.createTextNode=v=>node(3,{nodeValue:v});
 doc.createDocumentFragment=()=>{const f=node(11,{});f.appendChild=c=>append(f,c);return f;};
 return doc;
}
function line(doc,text){const e=doc.createElement('span');e.ownerDocument=doc;e.textContent=text;return e;}

test('PG-38 the closed map: the 10-08 tags and the common ones read in English',()=>{
 assert.equal(S.label('[تصفير في الخلفية]'),'whistling');
 assert.equal(S.label('[تسعلة]'),'cough');
 for(const t of ['[تضحك]','[يضحك]','[ضحك]','[ضحكة]','[laughs]','[laughter]'])assert.equal(S.label(t),'laughs',t);
 assert.equal(S.label('[يتنحنح]'),'clears throat');
 assert.equal(S.label('[يتنفس]'),'breathes');
 assert.equal(S.label('[صوت في الخلفية]'),'background noise');
 assert.equal(S.label('[background noise]'),'background noise');
 for(const t of ['[background chatter]','[background chattering]'])assert.equal(S.label(t),'background noise',t);   // 10-08 English tags
 assert.equal(S.label('[speaking Arabic]'),'speaking Arabic');
});

test('PG-38 an unknown bracket tag with Arabic letters is "(sound)"; a bracket with no Arabic and no known tag is left alone',()=>{
 assert.equal(S.label('[صوت باب]'),'sound');
 assert.equal(S.label('[1]'),null);
 assert.equal(S.label('[Doc note]'),null);
});

test('PG-38 the 00:15 tutor line: grey "(whistling) (cough)", the words around kept',()=>{
 const doc=mk(),e=line(doc,'أهلًا. [تصفير في الخلفية] [تسعلة] كيفك؟');
 assert.equal(S.decorate(e,doc),2);
 assert.equal(e.textContent,'أهلًا. (whistling) (cough) كيفك؟');
 const tags=e.childNodes.filter(c=>c.nodeType===1);
 assert.equal(tags.length,2);
 assert.ok(tags.every(t=>t.className==='snd-tag'&&t.attrs.lang==='en'));
 assert.equal(S.decorate(e,doc),0,'never twice');
});

test('PG-38 the Arabizi reader never spells a tag: the tag nodes are skipped (no "[tas3ile]")',()=>{
 const toAz=A.create([],{},{});
 const doc=mk(),e=line(doc,'أهلًا. [تصفير في الخلفية] [تسعلة] كيفك؟');
 S.decorate(e,doc);
 // the pages' walk: every text node that is not inside a tag goes through the reader
 const out=e.childNodes.map(c=>c.nodeType===3?(S.inTag(c)?c.nodeValue:toAz(c.nodeValue).text):c.textContent).join('');
 assert.ok(!/tas3ile|tasfeer|\[/.test(out),out);
 assert.match(out,/\(whistling\) \(cough\)/);
 // and the old path (no helper) really did spell them: the bug this rule fixes
 assert.match(toAz('[تسعلة]').text,/^\[.*\]$/);
});

test('PG-38 the pages load the helper and use it before the Arabizi reader',()=>{
 const html=fs.readFileSync(path.join(DOCS,'lessons.html'),'utf8');
 assert.match(html,/'sound-tags'/,'lessons.html loads js/sound-tags.js');
 assert.ok(html.indexOf("'sound-tags'")<html.indexOf("'lessons-page'"),'before lessons-page.js');
 const lp=fs.readFileSync(path.join(DOCS,'js','lessons-page.js'),'utf8');
 assert.match(lp,/SND\.decorate\(src\)/);
 assert.match(lp,/SND && SND\.inTag\(t\)/);
 const tz=fs.readFileSync(path.join(DOCS,'js','transcript-arabizi.js'),'utf8');
 assert.match(tz,/js\/sound-tags\.js/,'per-lesson pages get it through transcript-arabizi.js');
 assert.match(tz,/SND && SND\.inTag\(t\)/);
});

test('PG-38 display only: the built lesson JSON keeps the engine text (S2)',()=>{
 const L=JSON.parse(fs.readFileSync(path.join(DOCS,'data','lessons','2026-10-08.json'),'utf8'));
 assert.ok(L.turns.some(t=>t.text.includes('[تصفير في الخلفية] [تسعلة]')));
});
