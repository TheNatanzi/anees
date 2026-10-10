/* English under every transcript line on the Tutor page (PG-48, Medi 2026-10-10: "lets add the english translations for
   the transcript for Amal as well"). The lesson transcript already has one English sentence under each Arabic line
   (PG-40); her cards quote the same lines (the student's line, her line, the lines around a moment, the two versions of a
   listen check), so every element whose whole text is one of those lines gets its English, small, right under it.
   Data: data/tutor-line-en.json (scripts/translate_lines.py tutor) - key = the line with punctuation folded (tnorm()).
   Works on any page that loads it (tutor.html, amal/*.html): it watches the page and adds the English as cards render. */
(function () {
  'use strict';
  const src = (document.currentScript && document.currentScript.src) || location.href;
  const URL_ = new URL('../../data/tutor-line-en.json', src).href;
  const AR = /[ء-ي]/;
  const norm = s => String(s || '').replace(/[\s.,?!،؟…\-—:;"'()«»\[\]]+/g, ' ').trim();
  const PICK = 'span,p,div,td,li,q,blockquote,em,i,b,button,label';
  let MAP = null, queued = false;

  function style() {
    if (document.getElementById('hb-line-en-style')) return;
    const st = document.createElement('style'); st.id = 'hb-line-en-style';
    st.textContent = '.hb-line-en{display:block;font-size:12px;line-height:1.35;color:var(--ab-muted,#6f7a72);font-style:normal;font-weight:400;direction:ltr;text-align:left;margin:2px 0 0;unicode-bidi:isolate}';
    document.head.appendChild(st);
  }
  function decorate(root) {
    if (!MAP) return;
    for (const el of (root || document).querySelectorAll(PICK)) {
      if (el.dataset.en || el.classList.contains('hb-line-en') || el.closest('.hb-line-en')) continue;
      const t = el.textContent;
      if (!t || t.length > 420 || !AR.test(t)) continue;
      const k = norm(t), en = MAP[k];
      if (!en) continue;
      // the innermost element holding the line: a child with the same line gets it instead
      if ([...el.children].some(c => norm(c.textContent) === k)) continue;
      // the card already gives this English (a review example's own translation): never twice
      const card = el.closest('.hb-ex, .hb-card, article, li');
      if (card && norm(card.textContent).toLowerCase().includes(norm(en).toLowerCase())) { el.dataset.en = 'has'; continue; }
      el.dataset.en = '1';
      const e = document.createElement('span'); e.className = 'hb-line-en'; e.lang = 'en'; e.textContent = en;
      el.insertAdjacentElement('afterend', e);
    }
  }
  function later() {
    if (queued) return; queued = true;
    requestAnimationFrame(() => { queued = false; decorate(document); });
  }
  fetch(URL_ + '?build=' + encodeURIComponent(window.ANEES_BUILD || ''), { cache: 'no-store' })
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (!d || !d.lines) return;
      MAP = d.lines; style(); later();
      new MutationObserver(later).observe(document.body, { childList: true, subtree: true });
    })
    .catch(() => {});
  window.AneesLineEn = { norm, decorate };
})();
