/* Grammar rule ids explain themselves (Medi 2026-10-02: "anytime we have a reference to a Letter# (B5) lets have a
   hover over that tells us which one"). One shared script for every page: loads data/grammar-buckets.json once and
   turns each rule id it finds in the page text (A2, A10b, B18, E1 ... only ids that exist in that file) into a small
   span with a tooltip "<id> · <name> — <one_line>". Hover or keyboard focus shows it; on a phone a tap shows it and a
   tap anywhere else hides it. Content drawn later by other scripts is picked up by a MutationObserver.
   Never touched: inputs, textareas, selects, scripts, styles, editable text, Arabic text ([lang=ar], [dir=rtl]),
   anything marked data-rn-skip, and ids already wrapped. Inside an SVG the id's <text> gets a <title> instead.
   Pure helpers (find, label) are exported for tests/test_rule_names.cjs. */
(function(root){
'use strict';
const RX=/\b([A-H]\d{1,2}[a-z]?)\b/g;
// The ids in a string that are real rules, with their positions.
function find(text,rules){
 const out=[];if(!text||!rules)return out;RX.lastIndex=0;let m;
 while((m=RX.exec(text)))if(Object.prototype.hasOwnProperty.call(rules,m[1]))out.push({id:m[1],start:m.index,end:m.index+m[1].length});
 return out;
}
function label(id,r){const one=String(r&&r.one_line||'').replace(/`/g,'');return `${id} · ${r&&r.name||''}${one?' — '+one:''}`;}
if(typeof module!=='undefined'&&module.exports){module.exports={find,label};return;}

const doc=root.document;if(!doc)return;
const SKIP='script,style,noscript,textarea,input,select,option,code,pre,[contenteditable=""],[contenteditable="true"],[lang="ar"],[dir="rtl"],[data-rn-skip],.rn-id,.rn-tip';
let rules=null,tip=null,pinned=null,queued=false;
const src=(doc.currentScript&&doc.currentScript.src)||'js/rule-names.js';
const url=new URL('data/grammar-buckets.json',new URL('../',new URL(src,location.href))).href;   // docs/ root = one level above js/

function style(){
 if(doc.getElementById('rn-style'))return;
 const s=doc.createElement('style');s.id='rn-style';
 s.textContent='.rn-id{text-decoration:underline dotted;text-underline-offset:2px;cursor:help}'+
  '.rn-tip{position:fixed;z-index:9999;max-width:min(320px,calc(100vw - 24px));padding:8px 10px;border-radius:8px;'+
  'font:500 12.5px/1.4 var(--sabz-font-sans,system-ui,sans-serif);background:var(--ab-text,#1D2521);color:var(--ab-bg,#fff);'+
  'box-shadow:0 4px 18px rgba(0,0,0,.18);pointer-events:none}.rn-tip[hidden]{display:none}';
 doc.head.append(s);
}
function show(el){
 const r=rules&&rules[el.dataset.rn];if(!r)return;
 if(!tip){tip=doc.createElement('div');tip.className='rn-tip';tip.id='rn-tip';tip.setAttribute('role','tooltip');doc.body.append(tip);}
 tip.textContent=label(el.dataset.rn,r);tip.hidden=false;el.setAttribute('aria-describedby','rn-tip');
 const b=el.getBoundingClientRect(),w=tip.offsetWidth,h=tip.offsetHeight,vw=root.innerWidth;
 const left=Math.max(12,Math.min(vw-w-12,b.left+b.width/2-w/2)),top=b.top-h-8>8?b.top-h-8:b.bottom+8;
 tip.style.left=left+'px';tip.style.top=top+'px';
}
function hide(){if(tip)tip.hidden=true;pinned=null;}
function wrapText(node){
 const hits=find(node.nodeValue,rules);if(!hits.length)return;
 const frag=doc.createDocumentFragment();let at=0;const t=node.nodeValue;
 for(const h of hits){
  if(h.start>at)frag.append(t.slice(at,h.start));
  const s=doc.createElement('span');s.className='rn-id';s.dataset.rn=h.id;s.textContent=h.id;
  if(!node.parentElement.closest('a,button,label,summary'))s.tabIndex=0;
  frag.append(s);at=h.end;
 }
 if(at<t.length)frag.append(t.slice(at));
 node.parentNode.replaceChild(frag,node);
}
function svgTitle(node){
 const el=node.parentElement;if(!el||el.querySelector(':scope > title'))return;
 const hits=find(node.nodeValue,rules);if(!hits.length)return;
 const ttl=doc.createElementNS('http://www.w3.org/2000/svg','title');ttl.textContent=hits.map(h=>label(h.id,rules[h.id])).join('\n');
 el.append(ttl);
}
function scan(rootEl){
 if(!rules||!rootEl)return;
 const w=doc.createTreeWalker(rootEl,NodeFilter.SHOW_TEXT,{acceptNode:n=>{
  const p=n.parentElement;if(!p||!/[A-H]\d/.test(n.nodeValue))return NodeFilter.FILTER_REJECT;
  if(p.closest(SKIP))return NodeFilter.FILTER_REJECT;
  return NodeFilter.FILTER_ACCEPT;}});
 const list=[];while(w.nextNode())list.push(w.currentNode);
 for(const n of list){if(n.parentElement.closest('svg')){if(n.parentElement.tagName.toLowerCase()==='text'||n.parentElement.tagName.toLowerCase()==='tspan')svgTitle(n);}else wrapText(n);}
}
function queue(){if(queued)return;queued=true;setTimeout(()=>{queued=false;scan(doc.body);},60);}   // a timer, not rAF: rAF never fires in a background tab
async function start(){
 try{const r=await fetch(url,{cache:'no-cache'});if(!r.ok)return;const j=await r.json();
  rules={};for(const b of j.buckets||[])if(b&&b.id)rules[b.id]={name:b.name,one_line:b.one_line};}catch(e){return;}
 style();scan(doc.body);
 new MutationObserver(ms=>{for(const m of ms){if(m.target&&m.target.closest&&m.target.closest('.rn-tip'))continue;if(m.addedNodes.length||m.type==='characterData'){queue();return;}}})
  .observe(doc.body,{childList:true,subtree:true,characterData:true});
 doc.addEventListener('mouseover',e=>{const el=e.target.closest&&e.target.closest('.rn-id');if(el&&!pinned)show(el);});
 doc.addEventListener('mouseout',e=>{const el=e.target.closest&&e.target.closest('.rn-id');if(el&&!pinned)hide();});
 doc.addEventListener('focusin',e=>{const el=e.target.closest&&e.target.closest('.rn-id');if(el)show(el);});
 doc.addEventListener('focusout',e=>{if(e.target.closest&&e.target.closest('.rn-id'))hide();});
 doc.addEventListener('click',e=>{const el=e.target.closest&&e.target.closest('.rn-id');
  if(el&&!el.closest('a,button,summary')){if(pinned===el){hide();return;}show(el);pinned=el;return;}
  if(pinned)hide();});
 root.addEventListener('scroll',()=>{if(tip&&!tip.hidden)hide();},{passive:true});
 doc.addEventListener('keydown',e=>{if(e.key==='Escape')hide();});
}
root.AneesRuleNames={find,label,scan:()=>scan(doc.body)};
if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start);else start();
})(typeof window!=='undefined'?window:globalThis);
