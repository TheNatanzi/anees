/* Source-bound review overlays. Raw transcripts and flashcard results stay intact. */
(function(root){
'use strict';
function matches(e,expected){return !!e&&Object.entries(expected||{}).every(([k,v])=>JSON.stringify(e[k]??null)===JSON.stringify(v));}
function apply(events,review={}){
 const originals=new Map(events.map(e=>[e.id,e])),stale=[];
 let result=events.map(e=>{const p=review.patches?.[e.id];if(!p)return {...e};if(!matches(e,p.expected)){stale.push(e.id);return {...e};}return {...e,...p.changes};});
 for(const a of review.additions||[]){const anchor=originals.get(a.anchor_id);if(anchor?.source_sha256===a.expected_source&&!originals.has(a.event.id))result.push({...a.event});else if(!originals.has(a.event.id))stale.push(a.event.id);}
 result=result.map(e=>({...e,context:(e.context||[]).map(r=>{const edit=review.transcript_rows?.[r.row_id];return edit&&edit.original===r.text&&edit.source_sha256===e.source_sha256?{...r,reviewed_text:edit.display,reviewed_arabizi:edit.arabizi,transcript_note:edit.reason}:r;})}));
 return {events:result,stale};
}
function escape(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function mark(text,parts=[],partial=[],correct=[],feedback=[]){
 text=String(text??'');const ranges=[];
 for(const [kind,list] of [["wrong",parts],["partial",partial],["correct",correct],["feedback",feedback]])for(const part of list.filter(Boolean)){const re=new RegExp(String(part).replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'giu');let m;while((m=re.exec(text))){const left=text[m.index-1]||'',right=text[m.index+m[0].length]||'';if(!/[\p{L}\p{N}]/u.test(left)&&!/[\p{L}\p{N}]/u.test(right))ranges.push([m.index,m.index+m[0].length,kind]);}}
 ranges.sort((a,b)=>a[0]-b[0]);let out='',at=0;for(const [a,b,kind] of ranges){if(a<at)continue;out+=escape(text.slice(at,a))+'<mark class="ab-'+kind+'" title="'+(kind==='feedback'?'Tutor correction or confirmation':kind==='correct'?'Correct word':kind==='partial'?'Partial credit':'Incorrect word or pronunciation')+'">'+escape(text.slice(a,b))+'</mark>';at=b;}return out+escape(text.slice(at));
}
const api={apply,matches,mark};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesWordBankReview=api;
})(typeof globalThis!=='undefined'?globalThis:this);
