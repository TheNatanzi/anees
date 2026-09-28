/* Progress & Stats › "How sure are these numbers?" on the Vocab and Grammar tabs (Medi 2026-09-28: "make sure all the
   robot stuff goes in the ai reports and everything else is correctly in the progress").
   The personal panels of the two unknowns modules render here; the machine panels stay on AI Reports › Robot blind spots:
     Vocab   → AneesVocabUnknowns   V4 how sure the known words are, V2 never-checked words on his list
     Grammar → AneesGrammarUnknowns G1b rules he hasn't used yet, G3 thin evidence per rule, G4 rules collecting a hear-it %
   (Fluency has its own section, js/fluency-unknowns.js, mounted by js/fluency-ladder.js.)
   Mounts lazily when its tab is shown: flashcard-progress.js show() fires 'anees:progress-tab', grammar-progress.js
   render() fires 'anees:grammar-rendered' (it rewrites the whole tab, so the section is re-appended each time). */
(function(){
'use strict';
const $=id=>document.getElementById(id);
function vocab(){
 const tab=$('vp-tab-vocab'),body=$('vp-vocab-sure-body');
 if(!tab||tab.hidden||!body||!window.AneesVocabUnknowns)return;
 window.AneesVocabUnknowns.render(body,{panels:window.AneesVocabUnknowns.MEDI});   // no-op once drawn
}
function grammar(){
 const tab=$('vp-tab-grammar'),G=window.AneesGrammarUnknowns,P=window.AneesGrammarProgress;
 if(!tab||tab.hidden||!G||!P||!P.data)return;   // wait until the Grammar tab itself has drawn
 let w=$('gp-sure-wrap');
 if(!w){tab.insertAdjacentHTML('beforeend','<section id="gp-sure-wrap" class="vp-sure" aria-label="How sure are these numbers?"><div id="gp-sure-body"></div></section>');w=$('gp-sure-wrap');}
 G.render(w.querySelector('#gp-sure-body'),{panels:G.MEDI});
}
document.addEventListener('anees:progress-tab',()=>{vocab();grammar();});
document.addEventListener('anees:grammar-rendered',grammar);
vocab();grammar();   // the tab switch may have run before this file loaded
})();
