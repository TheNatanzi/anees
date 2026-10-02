/* Amal's two reading pages inside the Tutor hub (Medi 2026-10-02: "can we have everything on the tutor hub do what the
   new words is doing where you dont have to go to an external page"). The hub reads the SAME pages the old addresses
   show (amal/grammar-rules.html, amal/materials.html - built by scripts/build_amal_grammar_rules.py and
   scripts/build_amal_docs.py) and shows one rule / one section at a time in its panel; nothing is copied by hand.
   AneesDoc.grammar(base) -> {intro, rules:[{id, title, family, status, html}]}
   AneesDoc.materials(base) -> {intro, sections:[{id, title, html}], foot} */
(function (root) {
  'use strict';
  const cache = {};
  function load(url) {
    if (!cache[url]) cache[url] = fetch(url, { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(t => new DOMParser().parseFromString(t, 'text/html'));
    return cache[url];
  }
  const txt = el => (el && el.textContent || '').trim();
  async function grammar(base) {
    const d = await load((base || '') + 'amal/grammar-rules.html');
    const rules = [];
    d.querySelectorAll('main section').forEach(sec => {
      const fam = txt(sec.querySelector('h2'));
      sec.querySelectorAll('article[id]').forEach(a => {
        const pill = a.querySelector('.pill');
        rules.push({ id: a.id, title: txt(a.querySelector('h3')), family: fam.replace(/^[A-F]\s*/, ''), status: txt(pill),
                     statusClass: pill ? (pill.className.match(/s-\w+/) || [''])[0] : '', html: a.outerHTML });
      });
    });
    return { intro: txt(d.querySelector('.lede')), foot: txt(d.querySelector('footer')), rules };
  }
  async function materials(base) {
    const d = await load((base || '') + 'amal/materials.html');
    const sections = [...d.querySelectorAll('main section[id]')].map(s => ({ id: s.id, title: txt(s.querySelector('h2')), html: s.innerHTML }));
    return { intro: txt(d.querySelector('.lede')), foot: txt(d.querySelector('footer')), sections };
  }
  root.AneesDoc = { grammar, materials, load };
})(window);
