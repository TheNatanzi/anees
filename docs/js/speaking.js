// The ledger that produces word_stats also supplies filtering, summaries and history.
(function(root){
  const labels={independent:'Independent success · provisional',helped:'Helped practice · provisional',recall_failure:'Recall failure · provisional',incorrect:'Incorrect attempt · provisional',unresolved:'Unresolved'};
  function label(e){return e.assessment_status==='human_reviewed'?String(e.assessment).replace('_',' ')+' · Amal reviewed':labels[e.assessment]||'Not assessed';}
  function lessons(events){
    const by=new Map();
    for(const e of events){if(e.speaker!=='Medi')continue;if(!by.has(e.lesson_date))by.set(e.lesson_date,[]);by.get(e.lesson_date).push(e);}
    return [...by].map(([date,ev])=>({date,events:ev,practice_occurrences:ev.filter(e=>e.spoken).length,
      vocabulary_entries:new Set(ev.filter(e=>e.spoken).map(e=>e.word_key)).size,
      independent_successes:ev.filter(e=>e.spoken&&e.assessment==='independent').length,
      helped_uses:ev.filter(e=>e.spoken&&e.assessment==='helped').length,
      unresolved:ev.filter(e=>e.assessment==='unresolved').length})).sort((a,b)=>b.date.localeCompare(a.date));
  }
  function forWord(events,key){return events.filter(e=>e.speaker==='Medi'&&(e.word_key===key||(!e.word_key&&e.candidate_keys.includes(key))));}
  function recentByWord(events){
    const result=new Map();
    for(const e of events){
      if(e.speaker!=='Medi'||!e.word_key)continue;
      const current=result.get(e.word_key);
      const rank=[String(e.lesson_date||''),Number.isFinite(e.t_start)?e.t_start:-1];
      if(!current||rank[0]>current[0]||(rank[0]===current[0]&&rank[1]>current[1]))result.set(e.word_key,rank);
    }
    return result;
  }
  function audio(e){if(!/^lessons\/\d{4}-\d{2}-\d{2}\/(?:audio\/(?:Medi|Amal)\.mp3|clips\/[A-Za-z0-9_.-]+\.mp3)$/.test(e.audio_url||''))return null;return e.audio_url;}
  function link(e){return /^lessons\/\d{4}-\d{2}-\d{2}\.html$/.test(e.transcript_url||'')&&typeof e.row_id==='string'?e.transcript_url+'#'+encodeURIComponent(e.row_id):null;}
  root.AneesSpeaking={label,lessons,forWord,recentByWord,audio,link};
})(typeof window!=='undefined'?window:globalThis);
