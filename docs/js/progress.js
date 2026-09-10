// Durable card_results are the source of truth; local rows only cover not-yet-synced answers.
(function(root) {
  const CACHE_KEY='anees-stats-medi-recovery-v1';
  function requireCurrent(stats) {
    if(!stats || typeof stats!=='object' || Array.isArray(stats) || Object.values(stats).some(s=>s?.progress_context?.version!==2)) throw new Error('Progress recalculation is not ready');
    return stats;
  }
  function cached(stats) { try { return requireCurrent(stats); } catch(e) { return {}; } }
  async function load(stats, url, headers, localRows) {
    requireCurrent(stats);
    const rows=[];
    for(let offset=0;;offset+=1000) {
      const response=await fetch(url+'/rest/v1/card_results?select=id,word_key,ts,result,attempt&order=ts.asc,id.asc&limit=1000&offset='+offset,{headers});
      if(!response.ok) throw new Error('Card progress unavailable');
      const page=await response.json(); rows.push(...page);
      if(page.length<1000) break;
    }
    return root.AneesBuckets.mergeStats(stats,rows.concat(localRows||[]));
  }
  root.AneesProgress={load,CACHE_KEY,requireCurrent,cached};
})(typeof window!=='undefined'?window:globalThis);
