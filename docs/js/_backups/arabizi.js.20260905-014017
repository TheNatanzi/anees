// JS port of scripts/arabizi.py normalisation (loose / fold / short / skeleton / arabicNorm) for the Words search.
// Python stays the reference; tests/test_m7_index.py compares 40 forms across both.
(function (root) {
  const ACC = { 'â': 'a', 'á': 'a', 'à': 'a', 'ä': 'a', 'ê': 'e', 'é': 'e', 'è': 'e', 'î': 'i', 'í': 'i', 'ô': 'o', 'ó': 'o', 'û': 'u', 'ú': 'u', 'ü': 'u' };
  const ARABIC = /[؀-ۿ]/;
  function ascii(s) { s = String(s || '').toLowerCase().trim(); s = [...s].map(c => ACC[c] || c).join(''); return s.normalize('NFKD').replace(/[̀-ͯ]/g, ''); }
  function loose(s) {
    s = ascii(s);
    s = s.replace(/[’'`ʼ]/g, '2');
    s = s.replace(/[^a-z0-9 ]+/g, ' ');
    s = s.replace(/kh/g, '5').replace(/gh/g, '8').replace(/th/g, 's').replace(/dh/g, 'd').replace(/sh/g, 'S').replace(/ch/g, 'S');
    s = s.replace(/q/g, '2').replace(/x/g, '5').replace(/c/g, 'k').replace(/v/g, 'f').replace(/p/g, 'b');
    s = s.replace(/\b(el|il|al)[ -]+(?=[a-z0-9])/g, 'al');
    s = s.replace(/\b(el|il)(?=[a-z]{3})/g, 'al');
    s = s.replace(/y(?![aeiou])/g, 'i');
    s = s.replace(/ee+/g, 'I').replace(/oo+/g, 'U').replace(/aa+/g, 'A').replace(/ii+/g, 'I').replace(/uu+/g, 'U');
    s = s.replace(/(.)\1+/g, '$1');
    s = s.replace(/S/g, 'sh');
    return s.replace(/\s+/g, ' ').trim();
  }
  function fold(s) {
    let l = loose(s);
    l = l.replace(/6/g, 't').replace(/7/g, 'h').replace(/9/g, 's').replace(/8/g, 'g').replace(/5/g, 'x').replace(/z/g, 's');
    l = l.replace(/2/g, '').replace(/3/g, '');
    l = l.replace(/e/g, 'i').replace(/o/g, 'u');
    l = l.replace(/([aiuAIU])h\b/g, '$1');
    l = l.replace(/(.)\1+/g, '$1');
    return l.replace(/\s+/g, ' ').trim();
  }
  function short(s) { return fold(s).replace(/A/g, 'a').replace(/I/g, 'i').replace(/U/g, 'u').replace(/(.)\1+/g, '$1'); }
  function skeleton(s) {
    return fold(s).split(' ').filter(Boolean).map(w => { const lead = 'aeiouAIU'.includes(w[0]); const core = w.replace(/[aeiouAIU]/g, ''); return core ? (lead ? 'v' : '') + core : w; }).join(' ');
  }
  function arabicNorm(s, stripAl) {
    s = String(s || '').trim().replace(/[ً-ْٰـٓ-ٟ]/g, '');
    s = s.replace(/[أإآٱ]/g, 'ا').replace(/ة/g, 'ه').replace(/ى/g, 'ي').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي').replace(/ء/g, '');
    s = s.replace(/[^؀-ۿ ]+/g, ' ').replace(/\s+/g, ' ').trim();
    if (stripAl && s.startsWith('ال') && s.length > 4) s = s.slice(2);
    return s;
  }
  root.AneesArabizi = { loose, fold, short, skeleton, arabicNorm, ARABIC };
})(typeof window !== 'undefined' ? window : globalThis);
