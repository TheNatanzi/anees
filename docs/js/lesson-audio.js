/* Hosted lesson recording for the older transcript pages (2026-08-25, 09-04, 09-05): every mm:ss / hh:mm:ss time
   (span.t) becomes a play button on the same recording clock. The page's own features are untouched. */
(function(){
 'use strict';
 const a=document.getElementById('hosted-audio');if(!a)return;
 const secs=s=>{const p=s.trim().split(':').map(Number);if(p.some(n=>!Number.isFinite(n))||p.length<2||p.length>3)return null;return p.reduce((t,n)=>t*60+n,0);};
 let on=null;
 for(const el of document.querySelectorAll('main span.t')){
  const t=secs(el.textContent);if(t===null)continue;
  el.setAttribute('role','button');el.tabIndex=0;el.title='Play from '+el.textContent.trim();el.style.cursor='pointer';el.style.textDecoration='underline dotted';
  const go=()=>{if(on)on.style.background='';on=el.closest('p,li')||el;on.style.background='rgba(20,108,84,.12)';a.currentTime=Math.max(0,t-1);const p=a.play();if(p&&p.catch)p.catch(()=>{});};
  el.addEventListener('click',go);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});
 }
})();
