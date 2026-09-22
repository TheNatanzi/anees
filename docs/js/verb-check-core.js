// Pure logic for Amal's verb check list (docs/amal/verb-check.html). No DOM, no network.
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.AneesVerbCheck=api;})(typeof self!=='undefined'?self:this,function(){
 'use strict';
 const TENSES=['Present','Past','Command'];
 function validPayload(p){
  if(!p||p.schema_version!==1||p.kind!=='verb-forms'||!p.items||typeof p.items!=='object'||!Array.isArray(p.verbs)||!p.verbs.length)return false;
  const seen=new Set();
  for(const v of p.verbs){
   if(!v||typeof v.key!=='string'||typeof v.name!=='string'||!Array.isArray(v.ids)||!v.ids.length)return false;
   for(const id of v.ids){const it=p.items[id];if(seen.has(id)||!it||!TENSES.includes(it.tense)||typeof it.word!=='string'||typeof it.arabic!=='string'||typeof it.person!=='string')return false;seen.add(id);}
  }
  return seen.size===Object.keys(p.items).length;
 }
 function emptyState(){return {schema_version:1,revision:0,answers:{}};}
 function validState(p,s){
  if(!s||s.schema_version!==1||!Number.isSafeInteger(s.revision)||s.revision<0||!s.answers||typeof s.answers!=='object')return false;
  return Object.entries(s.answers).every(([id,a])=>p.items[id]&&a&&['yes','fix'].includes(a.choice)&&typeof a.word==='string'&&typeof a.arabic==='string'&&typeof a.updated_at==='string');
 }
 // Returns a new answers map; never mutates. choice null clears the answer.
 function answer(p,answers,id,choice,word,arabic,now){
  const it=p.items[id];if(!it)throw Error('unknown item');
  const next={...answers};
  if(choice===null){delete next[id];return next;}
  if(choice==='yes')next[id]={choice:'yes',word:it.word,arabic:it.arabic,updated_at:now};
  else if(choice==='fix')next[id]={choice:'fix',word:String(word||'').slice(0,200),arabic:String(arabic||'').slice(0,200),updated_at:now};
  else throw Error('bad choice');
  return next;
 }
 // A fix with an empty form is still a draft: saved locally, never sent.
 function sendable(answers){const out={};for(const [id,a] of Object.entries(answers))if(a.choice==='yes'||a.word.trim())out[id]=a;return out;}
 function done(answers,id){const a=answers[id];return !!a&&(a.choice==='yes'||!!a.word.trim());}
 function progress(p,answers){
  const total=Object.keys(p.items).length,finished=Object.keys(p.items).filter(id=>done(answers,id)).length;
  const verbsDone=p.verbs.filter(v=>v.ids.every(id=>done(answers,id))).length;
  return {total,finished,fixes:Object.values(answers).filter(a=>a.choice==='fix'&&a.word.trim()).length,verbs:p.verbs.length,verbsDone};
 }
 function byTense(p,verb){const out={};for(const id of verb.ids){const t=p.items[id].tense;(out[t]=out[t]||[]).push(id);}return TENSES.filter(t=>out[t]).map(t=>({tense:t,ids:out[t]}));}
 return {TENSES,validPayload,emptyState,validState,answer,sendable,done,progress,byTense};
});
