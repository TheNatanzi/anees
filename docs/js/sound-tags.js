/* Engine sound tags on every transcript view (PG-38, Medi 2026-10-08 on the 10-08 lesson, tutor line 00:15
   "Ahla. [tasfeer Fi el-5alfiyye] [tas3ile] keefak?": "whjat does [tasfeer Fi el-5alfiyye] [tas3ile] why is this here";
   2026-10-09 "ok do it").

   The recording engine (ElevenLabs Scribe) writes sound events in square brackets inside the text: [تصفير في الخلفية] =
   whistling in the background, [تسعلة] = a cough, [تضحك] = she laughs. The Arabizi reader used to spell them like words
   ("[tas3ile]"). Here they render as a small grey English note - (whistling), (cough), (laughs) - never Arabizi, never a
   word, never scored. Display only (RULES.md S2): the raw transcript and the built lesson JSON keep the bracket text; this
   file rewrites DOM text nodes on the page and nothing else. A bracket tag not in the closed map that holds Arabic letters
   shows as "(sound)". Square brackets with no Arabic letters and no known English tag are left alone (they are not the
   engine's sound tags; e.g. a Doc note).

   Browser: window.AneesSoundTags = { MAP, label(tag) -> english|null, isTag(text), decorate(el) -> n, inTag(node) }.
   Node (tests): module.exports = the same api, decorate takes any DOM-like element (node:test uses a tiny fake). */
(function (root) {
  'use strict';
  var AR = /[؀-ۿ]/;
  // Closed map: the engine's Arabic tag (brackets off, spaces squeezed) -> the English note. English tags the same engine
  // writes on English stretches are mapped too, so one tag never shows two ways.
  var MAP = {
    'تصفير في الخلفية': 'whistling', 'تصفير': 'whistling', 'تصفير حنجرة': 'clears throat',
    'تسعلة': 'cough', 'سعال': 'cough', 'يسعل': 'cough', 'تسعل': 'cough',
    'تضحك': 'laughs', 'يضحك': 'laughs', 'ضحك': 'laughs', 'ضحكة': 'laughs', 'يضحكون': 'laughs', 'يضحكان': 'laughs',
    'يتنحنح': 'clears throat', 'تتنحنح': 'clears throat',
    'يتنفس': 'breathes', 'تتنفس': 'breathes', 'تنفس عميق': 'breathes', 'تنفس': 'breathes', 'تنهد': 'sighs', 'تتنهد': 'sighs', 'يتنهد': 'sighs',
    'صوت في الخلفية': 'background noise', 'صوت من behind الكاميرا': 'background noise', 'ضجيج في الخلفية': 'background noise', 'ضجيج': 'background noise',
    'صوت تعجب': 'gasp', 'تصفق': 'clapping', 'تقبيل': 'kissing sound', 'صوت قطة': 'cat', 'صوت قرمشة': 'crunching', 'موسيقى': 'music',
    'حديث غير مفهوم': 'unclear speech', 'يتلعثم': 'stumbles', 'يتعثّر': 'stumbles', 'يتعثر': 'stumbles', 'مقطوع': 'cut off', 'هزغورة': 'sound',
    // English tags the same engine writes
    'laughs': 'laughs', 'laughing': 'laughs', 'laughter': 'laughs', 'laugh': 'laughs', 'chuckles': 'laughs', 'giggles': 'laughs',
    'coughs': 'cough', 'cough': 'cough', 'coughing': 'cough', 'clears throat': 'clears throat', 'sighs': 'sighs', 'sigh': 'sighs',
    'breathes': 'breathes', 'breathing': 'breathes', 'inhales': 'breathes', 'exhales': 'breathes', 'sniffs': 'sniffs',
    'background noise': 'background noise', 'noise': 'background noise', 'music': 'music', 'applause': 'clapping', 'clapping': 'clapping',
    'speaking arabic': 'speaking Arabic', 'speaks arabic': 'speaking Arabic', 'speaking in arabic': 'speaking Arabic',
    'speaking foreign language': 'speaking another language', 'speaking in foreign language': 'speaking another language',
    'speaking farsi': 'speaking Farsi', 'speaking persian': 'speaking Farsi', 'inaudible': 'unclear speech', 'unintelligible': 'unclear speech', 'crosstalk': 'crosstalk'
  };
  var TAG = /\[([^\[\]]{1,60})\]/g;
  function key(inner) { return String(inner || '').replace(/[ً-ٰٟـ]/g, '').replace(/\s+/g, ' ').trim().toLowerCase(); }
  // English note for one tag ("[تضحك]" or "تضحك"); null when the brackets are not an engine sound tag.
  function label(tag) {
    var inner = String(tag == null ? '' : tag).replace(/^\s*\[/, '').replace(/\]\s*$/, '');
    var k = key(inner);
    if (!k) return null;
    if (Object.prototype.hasOwnProperty.call(MAP, k)) return MAP[k];
    if (AR.test(k)) return 'sound';                      // unknown Arabic tag: still never spelled as a word
    return null;                                         // "[1]", "[Doc note]": not a sound tag, left alone
  }
  function isTag(text) { return label(text) !== null && /^\s*\[[^\[\]]+\]\s*$/.test(String(text || '')); }
  function inTag(node) {
    var p = node && (node.nodeType === 1 ? node : node.parentNode);
    while (p && p.nodeType === 1) { if (p.classList && p.classList.contains('snd-tag')) return true; p = p.parentNode; }
    return false;
  }
  // Replace every sound tag inside the element's text nodes with <span class="snd-tag" lang="en" dir="ltr">(laughs)</span>.
  // Marks and other spans around the tag are kept (the text node is split, not the element). Returns how many were drawn.
  function decorate(el, doc) {
    if (!el || el.dataset && el.dataset.snd === '1') return 0;
    doc = doc || (el.ownerDocument) || (typeof document !== 'undefined' ? document : null);
    if (!doc) return 0;
    var nodes = [], n = 0;
    (function walk(x) {
      var kids = x.childNodes || [];
      for (var i = 0; i < kids.length; i++) {
        var c = kids[i];
        if (c.nodeType === 3) { if (c.nodeValue && c.nodeValue.indexOf('[') >= 0) nodes.push(c); }
        else if (c.nodeType === 1 && !(c.classList && c.classList.contains('snd-tag'))) walk(c);
      }
    })(el);
    nodes.forEach(function (t) {
      var s = t.nodeValue, m, last = 0, frag = null;
      TAG.lastIndex = 0;
      while ((m = TAG.exec(s))) {
        var en = label(m[1]);
        if (en === null) continue;
        if (!frag) frag = doc.createDocumentFragment();
        if (m.index > last) frag.appendChild(doc.createTextNode(s.slice(last, m.index)));
        var sp = doc.createElement('span');
        sp.className = 'snd-tag';
        sp.setAttribute('lang', 'en'); sp.setAttribute('dir', 'ltr');
        sp.setAttribute('title', 'Sound the recording engine heard: ' + m[0] + ' (not a word, not scored)');
        sp.textContent = '(' + en + ')';
        frag.appendChild(sp);
        last = m.index + m[0].length;
        n++;
      }
      if (frag) {
        if (last < s.length) frag.appendChild(doc.createTextNode(s.slice(last)));
        t.parentNode.replaceChild(frag, t);
      }
    });
    if (el.dataset) el.dataset.snd = '1';
    return n;
  }
  var api = { MAP: MAP, label: label, isTag: isTag, decorate: decorate, inTag: inTag, TAG: TAG };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  // small grey note, same muted token the pages use; never bold, never underlined
  if (typeof document !== 'undefined' && !document.getElementById('snd-tag-css')) {
    var st = document.createElement('style'); st.id = 'snd-tag-css';
    st.textContent = '.snd-tag{font-size:.8em;color:var(--ab-muted,#60746e);opacity:.85;font-style:italic;unicode-bidi:isolate;white-space:nowrap;cursor:help}' +
                     'mark .snd-tag{background:none;text-decoration:none}';
    (document.head || document.documentElement).appendChild(st);
  }
  root.AneesSoundTags = api;
})(typeof window !== 'undefined' ? window : this);
