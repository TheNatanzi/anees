/* Clip fallback (Medi 2026-09-28: "The audio clips aren't working here"). The grammar tools cut short clips
   (lessons/<date>/clips/gc-*.mp3) on another machine and most were never published (*.mp3 is git-ignored).
   When such a clip fails to load, play the same moment from the full lesson recording instead:
   lessons/<date>/audio/lesson.mp3 with a media fragment #t=<start>,<end> (3 s before the moment, 12 s after).
   The moment comes from the element's data-t (seconds) or data-mmss ("mm:ss" / "h:mm:ss"). Anything else is left alone.
   Also exposes AneesClipFallback.url(src, seconds) for pages that drive one shared player (amal/review.html).
   2026-09-29 (engineering audit, area 9): a two-channel lesson (2026-09-10) has audio/Medi.mp3 + audio/Amal.mp3 and
   no audio/lesson.mp3, so the single fallback 404'd and the note said "No recording". The fallback now walks
   lesson.mp3 -> Medi.mp3 -> Amal.mp3 and stops with that note only when none of them loads.
   AneesClipFallback.url(src, seconds, failedUrl) gives the next recording after failedUrl (null when none is left). */
(function(){
'use strict';
const CLIP=/(lessons\/\d{4}-\d{2}-\d{2})\/clips\/[^/?#]+\.mp3/;
const FULL=['lesson.mp3','Medi.mp3','Amal.mp3'];
function secs(el){
 const t=parseFloat(el.dataset.t);if(Number.isFinite(t))return t;
 const m=String(el.dataset.mmss||'').trim().split(':').map(Number);if(!m.length||m.some(x=>!Number.isFinite(x)))return null;
 return m.reduce((a,x)=>a*60+x,0);
}
function urls(src,t){
 const m=CLIP.exec(src||'');if(!m||!Number.isFinite(t))return [];
 const base=src.slice(0,m.index)+m[1]+'/audio/',frag='#t='+Math.max(0,Math.floor(t-3))+','+Math.ceil(t+12);
 return FULL.map(n=>base+n+frag);
}
function url(src,t,failed){
 const u=urls(src,t);if(!u.length)return null;
 if(!failed)return u[0];
 const i=u.indexOf(failed);return i>=0&&i+1<u.length?u[i+1]:null;
}
function label(u){return /\/lesson\.mp3#/.test(u)?'Playing from the full lesson recording (the short clip is missing).':'Playing the '+(/\/Medi\.mp3#/.test(u)?'student':'tutor')+'’s channel of the lesson recording (the short clip is missing).';}
document.addEventListener('error',e=>{
 const a=e.target;if(!a||a.tagName!=='AUDIO')return;
 const orig=a.dataset.clipSrc||a.currentSrc||a.getAttribute('src')||'';
 const next=url(orig,secs(a),a.dataset.fellBack?a.getAttribute('src'):null);
 let note=a.nextElementSibling&&a.nextElementSibling.classList&&a.nextElementSibling.classList.contains('clip-fallback-note')?a.nextElementSibling:null;
 if(!next){ if(note)note.textContent='No recording is available for this moment.'; return; }
 if(!note){ note=document.createElement('div');note.className='clip-fallback-note';note.style.cssText='font-size:11px;opacity:.75;margin-top:2px';a.insertAdjacentElement('afterend',note); }
 note.textContent=label(next);
 a.dataset.clipSrc=orig;a.dataset.fellBack='lesson';
 a.src=next;a.load();
},true);
window.AneesClipFallback={url,urls,secs};
})();
