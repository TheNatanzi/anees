// Grip buckets — JS port of scripts/buckets.py (the Python file is the reference; tests/test_m5_cards.py checks parity).
// Speaking and Flashcards are isolated. Mastered: 5 successes in that lane on >=3 dates.
// Missed recovery: two consecutive independent successes, first -> Shaky, second -> Good.
// shaky: prompted / right on second try. missed: corrected / wrong twice in a row on cards. never: no Medi signal.
(function (root) {
  // Display names only: keep stored IDs and scoring rules compatible with saved progress.
  const DISPLAY_LABELS = Object.freeze({ cold: 'Good', ice_cold: 'Mastered' });
  function label(bucket) { return Object.prototype.hasOwnProperty.call(DISPLAY_LABELS, bucket) ? DISPLAY_LABELS[bucket] : String(bucket ?? '').replace(/_/g, ' '); }
  const RECENT_LESSONS = 3, NEW_DRILL_RIGHTS = 5, NEW_DRILL_DAYS = 2;
  const GRAMMAR_KINDS = ['article', 'gender', 'tense', 'plural'];
  function signalFromEvent(e) {
    if (e.speaker !== 'Medi' || e.prompted === null || e.prompted === undefined) return null;
    if (e.correction && GRAMMAR_KINDS.includes(e.miss_kind) && !e.asked) return e.prompted ? 'shaky' : 'cold';
    if (e.miss_kind === 'choice') return 'shaky';
    if (e.correction || e.asked) return 'missed';
    if (e.prompted) return 'shaky';
    return 'cold';
  }
  function wasIce(cards) { return cards.length ? signalFromCards(cards)[0] === 'ice_cold' : false; }
  function signalFromCards(cards) {
    if (!cards.length) return [null, 0, []];
    let streak = 0; const days = [];
    for (let i = cards.length - 1; i >= 0; i--) {
      const c = cards[i];
      if (c.result === 'got' && (parseInt(c.attempt || 1) === 1)) { streak++; const d = String(c.ts).slice(0, 10); if (!days.includes(d)) days.push(d); }
      else break;
    }
    const last = cards[cards.length - 1];
    if (streak >= 5 && days.length >= 3) return ['ice_cold', streak, days];
    if (last.result === 'missed') {
      if (cards.slice(-3).filter(c => c.result === 'missed').length >= 2) return ['missed', 0, []];   // wrong twice within the last three
      return [wasIce(cards.slice(0, -1)) ? 'cold' : 'shaky', 0, []];
    }
    if (parseInt(last.attempt || 1) > 1) return ['shaky', streak, days];
    return ['cold', streak, days];
  }
  function independentUse(e) {
    return e.speaker === 'Medi' && e.prompted === false && e.correction === false && e.asked === false && !['choice','unclear'].includes(e.miss_kind);
  }
  function isSpoken(e) { return e.speaker==='Medi' && typeof e.t_start==='number' && Number.isFinite(e.t_start) && e.t_start>=0 && !String(e.text||'').toLowerCase().startsWith('homework:'); }
  function trackProgress(context,lane) {
    const cards=(lane==='flashcards'?context.cards:[]).slice().sort((a,b)=>String(a.ts).localeCompare(String(b.ts)) || String(a.id||'').localeCompare(String(b.id||'')));
    const timeline=cards.map((c,i)=>({day:String(c.ts).slice(0,10),rank:0,ts:String(c.ts),i,source:'card',value:c}));
    for(const [i,[day,signal,qualifies]] of (lane==='speaking'?context.lessons:[]).entries()) timeline.push({day,rank:1,ts:'',i,source:'lesson',value:[signal,qualifies]});
    timeline.sort((a,b)=>a.day.localeCompare(b.day)||a.rank-b.rank||a.ts.localeCompare(b.ts)||a.i-b.i);
    let bucket='never', masteryStreak=0, masteryDays=[], recoveryLeft=0; const lastCards=[];
    for(const event of timeline) {
      const wasMastered=bucket==='ice_cold'; let signal, success;
      if(event.source==='card') {
        const c=event.value; lastCards.push(c);
        success=c.result==='got' && parseInt(c.attempt||1)===1;
        signal=c.result==='missed' ? (wasMastered?'cold':(lastCards.slice(-3).filter(c=>c.result==='missed').length>=2?'missed':'shaky')) : (success?'cold':'shaky');
      } else { const [s,qualifies]=event.value; if(qualifies===null) continue; signal=s; success=s==='cold' && qualifies; }
      if(success) {
        masteryStreak++; if(!masteryDays.includes(event.day)) masteryDays.push(event.day);
        if(recoveryLeft) { recoveryLeft--; signal=recoveryLeft?'shaky':'cold'; }
      } else {
        masteryStreak=0; masteryDays=[];
        if(signal==='missed'||recoveryLeft) { recoveryLeft=2; if(signal==='cold') signal='shaky'; }
      }
      bucket=masteryStreak>=5 && masteryDays.length>=3?'ice_cold':signal;
    }
    return {bucket,streak:masteryStreak,streak_days:masteryDays,mastery_streak:masteryStreak,mastery_days:masteryDays,recovery_left:recoveryLeft};
  }
  function progressFromContext(context) {
    if(context.version!==3) throw new Error('Speaking provenance must be rebuilt before scoring old mixed contexts');
    const speaking={...trackProgress(context,'speaking'),...context.speaking}, rawSpeaking=speaking.bucket;
    if(context.new && speaking.intro_uses<5) speaking.bucket='new';
    speaking.intro_target=context.new?5:0; speaking.weight=['new','missed'].includes(speaking.bucket)?3:1;
    const cards=context.cards.slice().sort((a,b)=>String(a.ts).localeCompare(String(b.ts))||String(a.id||'').localeCompare(String(b.id||'')));
    const flashcards=trackProgress(context,'flashcards');
    if(context.new && !(flashcards.streak>=NEW_DRILL_RIGHTS && flashcards.streak_days.length>=NEW_DRILL_DAYS)) flashcards.bucket='new';
    Object.assign(flashcards,{last_reviewed:cards.length?String(cards[cards.length-1].ts):null,attempts:cards.length,
      card_right:cards.filter(c=>c.result==='got').length,times_missed:cards.filter(c=>c.result==='missed').length,
      first_try_right:cards.filter(c=>c.result==='got'&&parseInt(c.attempt||1)===1).length});
    flashcards.weight=['new','missed'].includes(flashcards.bucket)?3:1;
    return {...Object.fromEntries(['bucket','streak','streak_days','mastery_streak','mastery_days','last_reviewed','times_missed','weight'].map(k=>[k,speaking[k]])),
      lesson_signal:rawSpeaking,card_right:flashcards.card_right,card_wrong:flashcards.times_missed,
      progress_scores:{version:1,speaking,flashcards}};
  }
  function mergeProgress(stats, log) {
    // Merge durable server card records and unsynced local IDs, not activity dates used as sync cursors.
    const source=stats.progress_context, cards=source.cards.map(c=>({...c}));
    const ids=new Set(cards.filter(c=>c.id).map(c=>c.id));
    for(const c of log) {
      if(c.id ? ids.has(c.id) : cards.some(old=>!old.id && old.ts===c.ts && old.result===c.result && (old.attempt||1)===(c.attempt||1))) continue;
      cards.push({...c}); if(c.id) ids.add(c.id);
    }
    cards.sort((a,b)=>String(a.ts).localeCompare(String(b.ts))||String(a.id||'').localeCompare(String(b.id||'')));
    const context={...source,cards};
    return {...stats,...progressFromContext(context),progress_context:context};
  }
  function emptyStats(key) {
    const context={version:3,new:false,lessons:[],cards:[],speaking:{times_seen:0,independent_uses:0,times_missed:0,last_reviewed:null,seen_lessons:0,intro_uses:0,new_since:null}};
    return {word_key:key,bucket:'never',recent:false,times_seen:0,independent_uses:0,times_missed:0,seen_lessons:0,
      last_lesson:null,last_reviewed:null,card_right:0,card_wrong:0,
      ...progressFromContext(context),progress_context:context};
  }
  function mergeStats(stats, log) {
    const out=Object.fromEntries(Object.entries(stats).filter(([,s])=>s.progress_context?.version===3).map(([key,s])=>[key,mergeProgress(s,[])])), by=new Map();
    for(const row of log||[]) {
      if(!row.word_key || !['got','missed'].includes(row.result) || !row.ts) continue;
      if(!by.has(row.word_key)) by.set(row.word_key,[]); by.get(row.word_key).push(row);
    }
    for(const [key,rows] of by) {
      const s=out[key]||emptyStats(key);
      if(s.progress_context?.version!==3) continue; // Never reinterpret legacy mixed scores as Speaking.
      const merged=mergeProgress(s,rows);
      out[key]={...merged,weight:['missed','new'].includes(merged.bucket)?3:1};
    }
    return out;
  }
  function compute(wordEvents, cardResults, lessonDates, confirmedNew, docBefore) {
    // confirmedNew: Set of `${lesson_date}|${word_key}` marked new by Amal/Medi; docBefore: {lesson_date: Set(word_key)} in the Doc before that lesson
    confirmedNew = confirmedNew || new Set(); docBefore = docBefore || {};
    const markedKeys = new Set([...confirmedNew].map(x => x.split('|').slice(1).join('|')));
    const dates = [...new Set(lessonDates.map(String))].sort();
    const recent = new Set(dates.slice(-RECENT_LESSONS));
    const evBy = {}, cdBy = {};
    for (const e of wordEvents) (evBy[e.word_key] = evBy[e.word_key] || []).push(e);
    for (const c of cardResults) (cdBy[c.word_key] = cdBy[c.word_key] || []).push(c);
    const out = {};
    for (const key of new Set([...Object.keys(evBy), ...Object.keys(cdBy), ...markedKeys])) {
      const evs = (evBy[key] || []).slice().sort((a, b) => String(a.lesson_date).localeCompare(String(b.lesson_date)) || ((a.t_start || 0) - (b.t_start || 0)));
      const cards = (cdBy[key] || []).slice().sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
      const medi=evs.filter(isSpoken), independent=medi.filter(independentUse);
      const qualifyingDates=new Set(independent.map(e=>String(e.lesson_date)));
      const helpedDates=new Set(medi.filter(e=>e.prompted===true||e.correction===true||e.asked===true||e.miss_kind==='choice').map(e=>String(e.lesson_date)));
      const byDay = new Map();
      for (const e of medi) { const s = signalFromEvent(e); if (s) { const d = String(e.lesson_date); if (!byDay.has(d)) byDay.set(d, []); byDay.get(d).push(s); } }
      const lessonSignals = [...byDay.entries()].map(([d, sigs]) => [d, sigs.includes('missed') ? 'missed' : (sigs.includes('cold') ? 'cold' : 'shaky')]);   // one signal per lesson: unprompted use beats a later echo
      const firstLesson = medi.length ? String(medi[0].lesson_date) : null;
      const seenDates = [...new Set(medi.map(e => String(e.lesson_date)))].sort();
      const marked = markedKeys.has(key);
      const byDoc = evs.some(e => docBefore[String(e.lesson_date)] && !docBefore[String(e.lesson_date)].has(key));
      const newDates=[...[...confirmedNew].filter(x=>x.split('|').slice(1).join('|')===key).map(x=>x.split('|')[0]),
        ...evs.filter(e=>docBefore[String(e.lesson_date)]&&!docBefore[String(e.lesson_date)].has(key)).map(e=>String(e.lesson_date))].sort();
      const newSince=newDates[0]||null;
      const speaking={times_seen:medi.length,independent_uses:independent.length,times_missed:medi.filter(e=>signalFromEvent(e)==='missed').length,
        last_reviewed:seenDates[seenDates.length-1]||null,seen_lessons:seenDates.length,intro_uses:medi.filter(e=>!newSince||String(e.lesson_date)>=newSince).length,new_since:newSince};
      const context={version:3,new:marked||byDoc,speaking,lessons:lessonSignals.map(([d,s])=>[d,s,qualifyingDates.has(d)?true:(helpedDates.has(d)?false:null)]),
        cards:cards.map(c=>Object.fromEntries(['id','ts','result','attempt'].filter(k=>k in c).map(k=>[k,c[k]])))};
      const progress=progressFromContext(context), bucket=progress.bucket;
      const lastReviewed = seenDates[seenDates.length - 1] || null;
      const isRecent = firstLesson ? recent.has(firstLesson) : false;
      out[key] = { word_key: key, bucket, last_reviewed: lastReviewed, last_lesson:seenDates[seenDates.length-1]||null, seen_lessons: seenDates.length, times_seen: medi.length, independent_uses:independent.length,
        times_missed: medi.filter(e => signalFromEvent(e)==='missed').length,
        card_right: cards.filter(c => c.result === 'got').length, card_wrong: cards.filter(c => c.result === 'missed').length,
        ...progress,progress_context:context,recent: isRecent, weight: (bucket === 'missed' || bucket === 'new') ? 3 : 1,
        grammar_misses:medi.filter(e=>e.correction&&GRAMMAR_KINDS.includes(e.miss_kind)).length,
        grammar_kinds:[...new Set(medi.filter(e=>e.correction&&GRAMMAR_KINDS.includes(e.miss_kind)).map(e=>e.miss_kind))].sort() };
    }
    return out;
  }
  root.AneesBuckets = { compute, signalFromCards, signalFromEvent, label, independentUse, progressFromContext, mergeProgress, emptyStats, mergeStats };
})(typeof window !== 'undefined' ? window : globalThis);
