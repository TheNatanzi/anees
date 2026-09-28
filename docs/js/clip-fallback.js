/* Clip fallback (Medi 2026-09-28: "The audio clips aren't working here"). The grammar tools cut short clips
   (lessons/<date>/clips/gc-*.mp3) on another machine and most were never published (*.mp3 is git-ignored).
   When such a clip fails to load, play the same moment from the full lesson recording instead:
   lessons/<date>/audio/lesson.mp3 with a media fragment #t=<start>,<end> (3 s before the moment, 12 s after).
   The moment comes from the element's data-t (seconds) or data-mmss ("mm:ss" / "h:mm:ss"). Anything else is left alone.
   Also exposes AneesClipFallback.url(src, seconds) for pages that drive one shared player (amal/review.html). */
(function(){
'use strict';
const CLIP=/(lessons\/\d{4}-\d{2}-\d{2})\/clips\/[^/?#]+\.mp3/;
function secs(el){
 const t=parseFloat(el.dataset.t);if(Number.isFinite(t))return t;
 const m=String(el.dataset.mmss||'').trim().split(':').map(Number);if(!m.length||m.some(x=>!Number.isFinite(x)))return null;
 return m.reduce((a,x)=>a*60+x,0);
}
function url(src,t){
 const m=CLIP.exec(src||'');if(!m||!Number.isFinite(t))return null;
 const base=src.slice(0,m.index)+m[1]+'/audio/lesson.mp3';
 return base+'#t='+Math.max(0,Math.floor(t-3))+','+Math.ceil(t+12);
}
document.addEventListener('error',e=>{
 const a=e.target;if(!a||a.tagName!=='AUDIO'||a.dataset.fellBack)return;
 const src=a.currentSrc||a.getAttribute('src')||'';
 if(a.dataset.fellBack==='lesson')return;
 const next=url(src,secs(a));
 if(!next){return;}
 a.dataset.fellBack='lesson';
 a.src=next;a.load();
 const note=document.createElement('div');note.className='clip-fallback-note';note.style.cssText='font-size:11px;opacity:.75;margin-top:2px';
 note.textContent='Playing from the full lesson recording (the short clip is missing).';
 a.insertAdjacentElement('afterend',note);
 a.addEventListener('error',()=>{note.textContent='No recording is available for this moment.';},{once:true});
},true);
window.AneesClipFallback={url,secs};
})();
