/* Source-preserving conversation turns. Never infer words from a score. */
(function(root){
'use strict';
function text(row){return row.reviewed_text||row.original_text||row.text||'';}
function owns(event,row){
 if(event.speaker!==row.speaker)return false;
 if(event.row_id===row.row_id||(event.item_ids||[]).includes(row.row_id))return true;
 return event.row_id?.startsWith('legacy-word-event:')&&String(row.row_id).startsWith(event.lesson_date+':')&&Number.isFinite(event.t_start)&&Number.isFinite(row.timeline_start)&&event.t_start>=row.timeline_start-.04&&event.t_start<=row.timeline_end+.04;
}
function turns(rows,gap=5){
 const seen=new Set(),out=[];
 for(const row of rows||[]){
  if(!text(row).trim()||row.row_id&&seen.has(row.row_id))continue;seen.add(row.row_id);
  const prev=out.at(-1),pause=Number(row.timeline_start)-Number(prev?.end);
  if(prev&&prev.speaker===row.speaker&&Number.isFinite(pause)&&pause<=gap&&pause>=-2){prev.rows.push(row);prev.end=Math.max(prev.end,row.timeline_end);}
  else out.push({speaker:row.speaker,start:row.timeline_start,end:row.timeline_end,rows:[row]});
 }
 return out;
}
function ownTurn(event){return turns(event.context).find(t=>t.rows.some(r=>owns(event,r)));}
const api={text,owns,turns,ownTurn};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesWordBankContext=api;
})(typeof globalThis!=='undefined'?globalThis:this);
