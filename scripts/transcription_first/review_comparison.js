/* Pure, dependency-free review diagnostics and matched-reference comparison.
 * This does not adjudicate gold, guess missing words, or change reviewer data.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.AneesComparison = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const NORMALIZATION = 'NFC and lowercase; remove limited edge punctuation; preserve Arabic letters/diacritics, digits, apostrophes, hyphens, ellipses and repeated words. Whitespace tokenization.';
  const EDGE = new Set(Array.from('.,!?;:"“”«»()[]{}،؛؟'));
  const UNCLEAR = /\[\s*(unclear|inaudible|unintelligible|غير واضح|غير مسموع)\s*\]/i;
  const KEYS = ['speech_runs_total', 'exact', 'minor', 'wrong', 'cant_tell', 'unrated', 'confirmed_wording'];
  const finite = n => typeof n === 'number' && Number.isFinite(n) && n >= 0;
  const ratio = (n, d) => d ? n / d : null;
  function tokenize(text) {
    return String(text).normalize('NFC').toLowerCase().split(/\s+/u).map(token => {
      while (token && EDGE.has(token[0]) && !token.startsWith('..')) token = token.slice(1);
      while (token && EDGE.has(token[token.length - 1]) && !token.endsWith('..')) token = token.slice(0, -1);
      return token;
    }).filter(Boolean);
  }
  function levenshtein(reference, hypothesis) {
    // Cells are [total errors, substitutions, deletions, insertions]. Equal
    // cost paths choose substitution, then deletion, then insertion in order.
    let prior = Array.from({length:hypothesis.length + 1}, (_, j) => [j, 0, 0, j]);
    for (let i = 1; i <= reference.length; i++) {
      const row = [[i, 0, i, 0]];
      for (let j = 1; j <= hypothesis.length; j++) {
        if (reference[i - 1] === hypothesis[j - 1]) row.push(prior[j - 1].slice());
        else {
          const choices = [[prior[j-1],1],[prior[j],2],[row[j-1],3]].map(([cell, kind]) => {
            const v = cell.slice(); v[0]++; v[kind]++; return v;
          });
          row.push(choices.reduce((best, v) => v[0] < best[0] ? v : best));
        }
      }
      prior = row;
    }
    const [errors,S,D,I] = prior[hypothesis.length];
    return {S,D,I,errors,N:reference.length,word_error_rate:ratio(errors,reference.length)};
  }
  function diagnostic(runs, record) {
    const d = Object.fromEntries(KEYS.map(k => [k,0]));
    for (const r of runs) {
      if ((r.events || []).length) continue;
      d.speech_runs_total++;
      const rr = record?.runs?.[r.id], v = rr?.verdict;
      d[['exact','minor','wrong','cant_tell'].includes(v) ? v : 'unrated']++;
      if (['exact','minor','wrong'].includes(v) && rr.text_certainty === 'confirmed' &&
          typeof rr.fixed_text === 'string' && rr.fixed_text.trim() && !UNCLEAR.test(rr.fixed_text)) d.confirmed_wording++;
    }
    d.judgment_coverage = ratio(d.exact+d.minor+d.wrong,d.speech_runs_total);
    d.response_coverage = ratio(d.exact+d.minor+d.wrong+d.cant_tell,d.speech_runs_total);
    return d;
  }
  function prepare(w, c, record) {
    const result = {source_kind:c.source_kind,diagnostics:diagnostic(c.runs || [],record),state:'pending',reason:null};
    const fail = reason => ({...result,reason});
    const speech = (c.runs || []).filter(r => !(r.events || []).length);
    if (!speech.length) return fail('empty_speech_candidate');
    if (!record || !record.runs) return fail('missing_candidate_review');
    const allIds = new Set((c.runs || []).map(r => r.id));
    if (Object.keys(record.runs).some(id => !allIds.has(id))) return fail('unknown_run_id');
    const pieces = [], hypotheses = [];
    for (const r of speech) {
      const rr = record.runs[r.id];
      if (!rr || rr.verdict == null) return fail('speech_runs_unrated');
      if (rr.id !== r.id || rr.original_text !== r.text || rr.start !== r.start || rr.end !== r.end || rr.speaker !== (r.speaker || 'Unknown')) return fail('run_evidence_mismatch');
      if (rr.verdict === 'cant_tell') return fail('speech_contains_abstention');
      if (!['exact','minor','wrong'].includes(rr.verdict)) return fail('invalid_verdict');
      if (rr.text_certainty !== 'confirmed' || typeof rr.fixed_text !== 'string' || !rr.fixed_text.trim() || UNCLEAR.test(rr.fixed_text)) return fail('speech_wording_unconfirmed');
      if ((rr.verdict === 'exact') !== (rr.fixed_text === r.text)) return fail('verdict_correction_contradiction');
      if (!finite(r.start) || !finite(r.end) || r.end <= r.start) return fail('invalid_speech_timing');
      if (r.crosses_window_boundary || r.start < w.start || r.end > w.end) return fail('speech_crosses_window_boundary');
      const tokens = tokenize(rr.fixed_text);
      if (!tokens.length) return fail('empty_reference_tokens');
      pieces.push({id:r.id,start:r.start,end:r.end,tokens});
      hypotheses.push({id:r.id,start:r.start,end:r.end,tokens:tokenize(r.text)});
    }
    const missing = record.missing_speech || [], missingIds = new Set();
    if (!Array.isArray(missing)) return fail('invalid_missing_speech');
    for (const m of missing) {
      if (!m.id || missingIds.has(m.id)) return fail('invalid_missing_speech_id');
      missingIds.add(m.id);
      if (m.text_certainty !== 'confirmed' || typeof m.text !== 'string' || !m.text.trim() || UNCLEAR.test(m.text)) return fail('missing_speech_unconfirmed');
      if (!finite(m.start) || !finite(m.end) || m.end <= m.start || m.start < w.start || m.end > w.end) return fail('invalid_missing_speech_timing');
      const tokens = tokenize(m.text);
      if (!tokens.length) return fail('empty_missing_speech_tokens');
      pieces.push({id:m.id,start:m.start,end:m.end,tokens});
    }
    const order = (a,b) => a.start-b.start || a.end-b.end || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    pieces.sort(order); hypotheses.sort(order);
    for (let i=1;i<pieces.length;i++) if (pieces[i].start < pieces[i-1].end - 0.000001) return fail('overlapping_reference_spans');
    const reference = pieces.flatMap(p => p.tokens), hypothesis = hypotheses.flatMap(p => p.tokens);
    if (!reference.length || !hypothesis.length) return fail('empty_transcript_tokens');
    return {...result,state:'ready',reason:null,reference_tokens:reference,hypothesis_tokens:hypothesis,confirmed_missing_spans:missing.length};
  }
  function compareWindow(w, record) {
    const out = {window_id:w?.id || null,state:'pending',reason:null,winner:null,normalization:NORMALIZATION,by_candidate:{}};
    if (!w || !finite(w.start) || !finite(w.end) || w.end <= w.start || !Array.isArray(w.candidates) ||
        w.candidates.length !== 2 || new Set(w.candidates.map(c=>c.id)).size !== 2 ||
        !w.candidates.every(c=>['A','B'].includes(c.id) && Array.isArray(c.runs) && c.source_kind) ||
        new Set(w.candidates.map(c=>c.source_kind)).size !== 2) return {...out,reason:'invalid_window'};
    if (record && record.id !== w.id) return {...out,reason:'window_evidence_mismatch'};
    for (const c of w.candidates) out.by_candidate[c.id] = prepare(w,c,record?.candidates?.[c.id]);
    if (Object.values(out.by_candidate).some(c=>c.state !== 'ready')) return {...out,reason:'candidate_review_incomplete_or_ambiguous'};
    const a=out.by_candidate.A,b=out.by_candidate.B;
    if (JSON.stringify(a.reference_tokens) !== JSON.stringify(b.reference_tokens)) return {...out,reason:'human_reference_disagreement'};
    const common = a.reference_tokens;
    Object.assign(a,levenshtein(common,a.hypothesis_tokens));
    Object.assign(b,levenshtein(common,b.hypothesis_tokens));
    return {...out,state:'ready',reason:null,winner:a.errors < b.errors ? 'A' : a.errors > b.errors ? 'B' : 'tie',
      common_reference_tokens:common,scope:'One complete window, one reviewer, identical independently supplied normalized references. Not adjudicated gold.'};
  }
  function summarize(windows, person, options={}) {
    const reports=windows.map(w=>options.reviewerConflict ? {
      window_id:w.id,state:'pending',reason:'reviewer_conflict',winner:null,normalization:NORMALIZATION,
      by_candidate:Object.fromEntries(w.candidates.map(c=>[c.id,{source_kind:c.source_kind,
        diagnostics:diagnostic(c.runs,person?.windows?.[w.id]?.candidates?.[c.id]),state:'pending',reason:'reviewer_conflict'}]))
    } : compareWindow(w,person?.windows?.[w.id]));
    const sources={},included=[],excluded=[];
    for (const report of reports) {
      if(report.state==='ready') included.push(report.window_id);
      else excluded.push({window_id:report.window_id,reason:report.reason,
        candidate_reasons:Object.fromEntries(Object.entries(report.by_candidate).map(([id,c])=>[id,c.reason]))});
      for(const c of Object.values(report.by_candidate)) {
        const s=sources[c.source_kind]||(sources[c.source_kind]={diagnostics:Object.fromEntries(KEYS.map(k=>[k,0])),paired_windows:0,S:0,D:0,I:0,errors:0,N:0,word_error_rate:null});
        for(const k of KEYS)s.diagnostics[k]+=c.diagnostics[k];
        if(report.state==='ready'){s.paired_windows++;for(const k of ['S','D','I','errors','N'])s[k]+=c[k];}
      }
    }
    for(const s of Object.values(sources)) {
      const d=s.diagnostics;d.judgment_coverage=ratio(d.exact+d.minor+d.wrong,d.speech_runs_total);
      d.response_coverage=ratio(d.exact+d.minor+d.wrong+d.cant_tell,d.speech_runs_total);
      s.word_error_rate=ratio(s.errors,s.N);
      if(!s.paired_windows) for(const k of ['S','D','I','errors'])s[k]=null;
    }
    const keys=Object.keys(sources).sort();
    let lower=null;
    if(included.length && keys.length===2){const a=sources[keys[0]],b=sources[keys[1]];lower=a.errors<b.errors?keys[0]:a.errors>b.errors?keys[1]:'tie';}
    return {state:included.length?'reviewed_subset_available':'pending',
      scope:'Lower edit count on the listed jointly reviewed full windows only. Includes English context; not Arabic-specific accuracy or a statistical model winner.',
      normalization:NORMALIZATION,included_window_ids:included,excluded_windows:excluded,
      reviewed_paired_windows:included.length,total_windows:windows.length,complete_review_set:!!windows.length&&included.length===windows.length,
      lower_error_source_on_reviewed_subset:lower,by_source_kind:sources,windows:reports};
  }
  return Object.freeze({tokenize,levenshtein,compareWindow,summarize,NORMALIZATION});
});
