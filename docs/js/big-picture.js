/* Big Picture idea dump (pure, no DOM). Table: big_picture_ideas (migration 017).
   One line typed = one idea; blank lines and bullets are ignored. */
(function(root){
'use strict';
const STATUSES=Object.freeze([
 {id:'idea',label:'Ideas',one:'Idea'},{id:'picked',label:'Picked',one:'Picked'},{id:'building',label:'Building',one:'Building'},
 {id:'done',label:'Done',one:'Done'},{id:'dropped',label:'Dropped',one:'Dropped'}]);
const SOURCE={medi:'You',claude:'Claude',legacy:'Old list'};
// "- idea", "• idea", "1. idea" and "[ ] idea" all become "idea"; titles over 300 characters keep the rest as the note.
function split(text){
 const out=[],seen=new Set();
 for(const raw of String(text||'').split(/\r?\n/)){
  const line=raw.replace(/^\s*(?:[-*•–]|\d+[.)]|\[\s?\])\s*/,'').replace(/\s+/g,' ').trim();
  if(!line||seen.has(line.toLowerCase()))continue;seen.add(line.toLowerCase());
  out.push(line.length<=300?{title:line,note:null}:{title:line.slice(0,297).trimEnd()+'…',note:line});
 }
 return out;
}
// Newest first inside each status; empty statuses are kept so every column shows.
function group(ideas){
 const by=new Map(STATUSES.map(s=>[s.id,[]]));
 for(const i of ideas||[])(by.get(i.status)||by.get('idea')).push(i);
 for(const list of by.values())list.sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at)));
 return STATUSES.map(s=>({...s,ideas:by.get(s.id)}));
}
const api={STATUSES,SOURCE,split,group};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesBigPicture=api;
})(typeof window!=='undefined'?window:globalThis);
