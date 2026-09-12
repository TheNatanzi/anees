// Display-only lesson evidence. Never merges draft matches into either score.
(function(root){
  function valid(data){
    if(data?.schema_version!==1||!Array.isArray(data.lessons))throw Error('Draft data unavailable');
    for(const l of data.lessons){
      if(!/^\d{4}-\d{2}-\d{2}$/.test(l.date)||l.status!=='draft'||l.transcript_url!==`lessons/${l.date}.html`||!l.words||typeof l.words!=='object')throw Error('Invalid draft lesson');
      let count=0;
      for(const w of Object.values(l.words)){
        if(!Array.isArray(w.events)||w.count!==w.events.length||!Number.isInteger(w.count)||w.count<1)throw Error('Invalid draft count');
        for(const e of w.events){
          if(typeof e.row_id!=='string'||!Number.isFinite(e.timeline_start)||e.timeline_start<0||e.status!=='unreviewed')throw Error('Invalid draft evidence');
          if(e.clip!==undefined&&(!/^\d{4}-\d{2}-\d{2}_\d{6}_\d{6}\.mp3$/.test(e.clip)||!Number.isFinite(e.clip_offset)||e.clip_offset<0))throw Error('Invalid draft clip');
        }
        count+=w.count;
      }
      if(l.word_count!==Object.keys(l.words).length||l.occurrence_count!==count)throw Error('Draft summary mismatch');
    }
    return data;
  }
  async function load(){const r=await fetch('data/lesson-word-drafts.json',{cache:'no-store'});if(!r.ok)throw Error('Draft data unavailable');return valid(await r.json());}
  function latest(data){return data?.lessons?.slice().sort((a,b)=>b.date.localeCompare(a.date))[0]||null;}
  function word(lesson,key){return lesson&&Object.prototype.hasOwnProperty.call(lesson.words,key)?lesson.words[key]:null;}
  function link(lesson,event){return lesson.transcript_url+'#'+encodeURIComponent(event.row_id);}
  root.AneesWordDrafts={valid,load,latest,word,link};
})(typeof window!=='undefined'?window:globalThis);
