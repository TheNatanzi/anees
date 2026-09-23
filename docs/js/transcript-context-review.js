(async function(){
'use strict';
const date=location.pathname.match(/(\d{4}-\d{2}-\d{2})\.html$/)?.[1];if(!date)return;
const response=await fetch('../data/word-bank-audit.json',{cache:'no-store'});if(!response.ok)return;const audit=await response.json(),events=audit.events.filter(e=>e.date===date),R=window.AneesWordBankReview;
const style=document.createElement('style');style.textContent='.ab-wrong{color:#b42332;background:#fee4e6;text-decoration:underline;text-decoration-thickness:2px;padding:0 2px}.context-listen{display:block;margin:8px 0;padding:8px 12px;cursor:pointer}.context-review-note{font:14px/1.5 system-ui;color:#52635c}@media(prefers-color-scheme:dark){.ab-wrong{color:#ffb3ba;background:#51242c}}';document.head.append(style);
const player=document.createElement('audio');player.controls=true;player.hidden=true;player.style.cssText='position:sticky;bottom:8px;width:100%;z-index:10';(document.querySelector('main')||document.body).append(player);
const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
const timed=[...document.querySelectorAll('p[dir]')].filter(p=>p.querySelector('small')&&p.querySelector('b')?.textContent==='Medi').map(p=>{const parts=p.querySelector('small').textContent.split(':').map(Number);return {p,start:parts[0]*60+parts[1]};});
const used=new Set();for(const e of events){
 const button=document.querySelector('[data-row="'+CSS.escape(e.row_id)+'"]');let holder=button?.closest('.turn'),body=holder?.querySelector('.words');
 if(!body){const t=timed.find(t=>Math.abs(t.start-e.row_start)<1.1&&norm(t.p.textContent).includes(norm(e.transcript_original||e.sentence)));holder=t?.p;body=holder;}
 if(!body)continue;
 if(e.transcript_original&&!body.dataset.transcriptCorrected){const walker=document.createTreeWalker(body,NodeFilter.SHOW_TEXT);const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);for(const n of nodes)if(norm(n.textContent).includes(norm(e.transcript_original))){n.textContent=n.textContent.replace(new RegExp(e.transcript_original.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s+')),e.sentence);body.dataset.transcriptCorrected='true';const note=document.createElement('span');note.className='context-review-note';note.textContent=' Transcript corrected from: '+e.transcript_original;holder.append(note);break;}}
 if(e.wrong_parts.length){const walker=document.createTreeWalker(body,NodeFilter.SHOW_TEXT);const nodes=[];while(walker.nextNode())if(!walker.currentNode.parentElement.closest('mark,button,small,b,.context-review-note'))nodes.push(walker.currentNode);for(const n of nodes){const html=R.mark(n.textContent,e.wrong_parts);if(html.includes('<mark ')){const span=document.createElement('span');span.innerHTML=html;n.replaceWith(span);}}}
 if(e.audio&&!used.has(holder)){used.add(holder);const play=document.createElement('button');play.className='context-listen';play.textContent='▶ Play';play.onclick=()=>{player.pause();player.hidden=false;player.src='../'+e.audio;player.play().catch(()=>{play.textContent='Use the audio player below';});};holder.append(play);}
}
})().catch(()=>{});
