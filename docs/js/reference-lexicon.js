/* The secondary reference lexicon (rule AM-25, Medi 2026-10-06 "...create an index for yourself to use as a secondary
   data source... ingest"): glosses, roots, plurals, example sentences and verb-preposition hints from open Levantine
   sources (kaikki.org Wiktionary ajp/apc, CC BY-SA 3.0; Maknuune CAMeL Lab, CC BY-SA 4.0), built by
   scripts/build_reference_lexicon.py into docs/data/reference-lexicon.json.

   What it is NOT (RULES.md S1): a spelling, or a score. Amal's Doc is the only word truth and her spelling the only
   spelling; nothing here is ever shown AS a spelling and nothing here changes a score. Pure: no DOM, no fetch -
   the page loads the JSON and hands it to load(). Normalisation mirrors norm() in the builder and both are tested
   against tests/fixtures/reference-lexicon-norm.json. */
(function (root) {
  'use strict';
  const DIAC = /[ؐ-ًؚ-ٰٟۖ-ۭـ]/g;      // harakat, shadda, sukun, tatweel
  const PUNCT = /[؟،؛?!.,;:"'()\[\]«»]/g;              // ? , ; (Arabic and Latin marks)
  const PRONOUNS = new Set(['انا', 'انت', 'انتي', 'هو', 'هي', 'احنا', 'نحنا', 'انتو', 'انتم', 'هم', 'هني', 'هنه', 'همه']);
  let records = {}, index = {}, meta = null;

  function normalise(s) {
    s = String(s == null ? '' : s).replace(DIAC, '').replace(PUNCT, ' ');
    s = s.replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه');
    return s.replace(/[\s ]+/g, ' ').trim();
  }
  function stripPronoun(key) {
    const toks = key.split(' ');
    while (toks.length > 1 && PRONOUNS.has(toks[0])) toks.shift();
    return toks.join(' ');
  }
  function load(json) {
    const d = json && typeof json === 'object' ? json : {};
    records = d.records && typeof d.records === 'object' ? d.records : {};
    index = d.index && typeof d.index === 'object' ? d.index : {};
    meta = { built: d.built || '', licenses: d.licenses || {}, sources: d.sources || {}, record_count: Object.keys(records).length };
    return meta;
  }
  // The record for an Arabic word, or null: the exact key, a listed form (plural, past, present), then the same without
  // a leading subject pronoun ("أنا بخاف") or a leading ال. `how` says which: 'exact' | 'form' | 'pronoun' | 'al'.
  function find(arabic) {
    const key = normalise(arabic);
    if (!key) return null;
    const tries = [[key, 'exact']];
    const sp = stripPronoun(key);
    if (sp !== key) tries.push([sp, 'pronoun']);
    for (const [t, how] of tries.slice()) if (t.startsWith('ال') && t.length > 4) tries.push([t.slice(2), 'al']);
    for (const [t, how] of tries) {
      if (Object.prototype.hasOwnProperty.call(records, t)) return { key: t, how, record: records[t] };
      const via = Object.prototype.hasOwnProperty.call(index, t) ? index[t] : null;
      if (via && Object.prototype.hasOwnProperty.call(records, via)) return { key: via, how: how === 'exact' ? 'form' : how, record: records[via] };
    }
    return null;
  }
  function glossFor(arabic) {
    const hit = find(arabic);
    return hit && Array.isArray(hit.record.gloss) ? hit.record.gloss.slice() : [];
  }
  const api = { normalise, stripPronoun, load, find, glossFor, meta: () => meta, size: () => Object.keys(records).length };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AneesReference = api;
})(typeof window !== 'undefined' ? window : globalThis);
